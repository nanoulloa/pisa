"""Stabilization: undo camera motion so positions are measured against the world, not the frame.

Corners in the background are followed between frames with pyramidal Lucas-Kanade optical
flow, away from the tracked objects, and a similarity transform (shift, rotation, zoom) is
fit to them with RANSAC. Chaining the transforms maps every frame onto the first frame of its
shot. A frame whose transform cannot be trusted is unreliable and its samples are dropped. A
scene cut starts a new shot: positions on either side of a cut cannot be compared.

A background with nothing to follow (a plain wall, a synthetic clip) shows no camera motion,
and the frame is kept as it is: the motion, if any, is invisible to every method.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt

from pisa_contracts import BBox, Point2, TrackedObject, TrackSample
from pisa_engine.physics.trajectory import BoolArray, FloatArray

Image = npt.NDArray[np.uint8]

# Below this largest corner displacement (full-resolution pixels) the camera is still, and
# frames are left untouched rather than nudged by estimation noise.
STATIC_CAMERA_PX = 1.0
# A transform needs this many inlier corners, and this share of the corners that tracked.
MIN_INLIERS = 15
MIN_INLIER_SHARE = 0.5
# Fewer corners than this in the background: nothing to follow.
MIN_CORNERS = MIN_INLIERS
# A failed link between frames whose 32 x 32 grayscale thumbnails differ by more than this
# (mean absolute difference, 0 to 255) is a scene cut, not a blurred frame.
CUT_MIN_DIFFERENCE = 12.0
# Object boxes grow by this share of their size, plus a margin, before masking them out.
BOX_GROWTH = 0.25
BOX_MARGIN_PX = 8.0
# An object with more of its samples on unreliable frames than this is not measured.
MAX_UNRELIABLE_SHARE = 0.2


@dataclass(frozen=True, slots=True)
class CameraPath:
    """Per frame: a 3 x 3 transform from frame pixels to the first frame of its shot."""

    to_reference: list[FloatArray]
    reliable: BoolArray
    cuts: list[int]  # First frame of every shot after the first.
    max_motion_px: float

    @property
    def static(self) -> bool:
        return self.max_motion_px < STATIC_CAMERA_PX

    @property
    def unreliable_frames(self) -> int:
        return int((~self.reliable).sum())

    def unreliable_share(self, obj: TrackedObject) -> float:
        if not obj.samples:
            return 0.0
        dropped = sum(1 for s in obj.samples if not self._reliable(s.frame))
        return dropped / len(obj.samples)

    def shot(self, frame: int) -> int:
        return sum(1 for cut in self.cuts if cut <= frame)

    def _reliable(self, frame: int) -> bool:
        return frame < self.reliable.size and bool(self.reliable[frame])


def boxes_by_frame(objects: Iterable[TrackedObject]) -> dict[int, list[BBox]]:
    boxes: dict[int, list[BBox]] = defaultdict(list)
    for obj in objects:
        for sample in obj.samples:
            boxes[sample.frame].append(sample.bbox)
    return boxes


def estimate_camera_path(
    video: Path, exclude: Mapping[int, Sequence[BBox]], *, max_side: int = 640
) -> CameraPath:
    return estimate_from_frames(_frames(video), exclude, max_side=max_side)


def estimate_from_frames(
    frames: Iterable[Image], exclude: Mapping[int, Sequence[BBox]], *, max_side: int = 640
) -> CameraPath:
    """`frames` are BGR images; `exclude` holds the tracked objects' boxes per frame index."""
    transforms: list[FloatArray] = []
    reliable: list[bool] = []
    cuts: list[int] = []
    corners_full = np.zeros((4, 2))
    anchor: _Anchor | None = None
    previous_thumb: FloatArray | None = None

    for index, frame in enumerate(frames):
        height, width = frame.shape[:2]
        scale = min(1.0, max_side / max(height, width))
        gray = _gray(frame, scale)
        thumb = _thumbnail(gray)
        corners_full = np.array([[0, 0], [width, 0], [0, height], [width, height]], np.float64)
        boxes = exclude.get(index, ())
        if anchor is None:
            anchor = _Anchor(index, gray, np.eye(3), boxes)
            transforms.append(np.eye(3))
            reliable.append(True)
            previous_thumb = thumb
            continue

        link = _link(anchor, gray, boxes, scale)
        if isinstance(link, _Featureless):
            transforms.append(anchor.to_reference)
            reliable.append(True)
        elif link is None:
            assert previous_thumb is not None
            if float(np.abs(thumb - previous_thumb).mean()) > CUT_MIN_DIFFERENCE:
                cuts.append(index)
                anchor = _Anchor(index, gray, np.eye(3), boxes)
                transforms.append(np.eye(3))
                reliable.append(True)
            else:
                transforms.append(anchor.to_reference)
                reliable.append(False)
        else:
            # current -> anchor -> reference.
            to_reference = anchor.to_reference @ np.linalg.inv(link)
            anchor = _Anchor(index, gray, to_reference, boxes)
            transforms.append(to_reference)
            reliable.append(True)
        previous_thumb = thumb

    return CameraPath(
        to_reference=transforms,
        reliable=np.array(reliable, dtype=np.bool_),
        cuts=cuts,
        max_motion_px=_max_motion(transforms, corners_full),
    )


def stabilize(obj: TrackedObject, path: CameraPath) -> list[TrackedObject]:
    """The object's samples in reference coordinates, one object per shot, unreliable dropped."""
    shots: dict[int, list[TrackSample]] = defaultdict(list)
    for sample in sorted(obj.samples, key=lambda s: s.frame):
        if not path._reliable(sample.frame):
            continue
        mapped = sample if path.static else _map_sample(sample, path.to_reference[sample.frame])
        shots[path.shot(sample.frame)].append(mapped)
    return [
        TrackedObject(phrase=obj.phrase, object_id=obj.object_id, samples=samples)
        for _, samples in sorted(shots.items())
    ]


@dataclass(frozen=True, slots=True)
class _Anchor:
    """The last frame with a trusted transform: new frames are linked to it."""

    index: int
    gray: Image
    to_reference: FloatArray
    boxes: Sequence[BBox]


class _Featureless:
    pass


_FEATURELESS = _Featureless()  # The anchor has too few corners to follow.


def _link(
    anchor: _Anchor, gray: Image, boxes: Sequence[BBox], scale: float
) -> FloatArray | _Featureless | None:
    """Full-resolution 3 x 3 transform from anchor pixels to current pixels, if trustworthy."""
    mask = _background_mask(anchor.gray.shape, anchor.boxes, scale)
    found = cv2.goodFeaturesToTrack(
        anchor.gray, maxCorners=500, qualityLevel=0.01, minDistance=8, blockSize=7, mask=mask
    )
    if found is None or len(found) < MIN_CORNERS:
        return _FEATURELESS
    start = found.astype(np.float32)
    end, ok_forward, _ = cv2.calcOpticalFlowPyrLK(
        anchor.gray, gray, start, start.copy(), winSize=(21, 21), maxLevel=3
    )
    back, ok_back, _ = cv2.calcOpticalFlowPyrLK(
        gray, anchor.gray, end, start.copy(), winSize=(21, 21), maxLevel=3
    )
    # Forward-backward check: a corner that does not track back to where it started is lost.
    round_trip = np.linalg.norm((back - start).reshape(-1, 2), axis=1)
    keep = (ok_forward.ravel() == 1) & (ok_back.ravel() == 1) & (round_trip < 0.5)
    keep &= _outside(np.asarray(end, np.float64).reshape(-1, 2), boxes, scale)
    if int(keep.sum()) < MIN_INLIERS:
        return None
    matrix, inliers = cv2.estimateAffinePartial2D(
        start[keep], end[keep], method=cv2.RANSAC, ransacReprojThreshold=1.0
    )
    if matrix is None or inliers is None:
        return None
    count = int(inliers.sum())
    if count < MIN_INLIERS or count < MIN_INLIER_SHARE * int(keep.sum()):
        return None
    small = np.vstack([matrix, [0.0, 0.0, 1.0]])
    to_small = np.diag([scale, scale, 1.0])
    return np.asarray(np.linalg.inv(to_small) @ small @ to_small, dtype=np.float64)


def _background_mask(shape: tuple[int, ...], boxes: Sequence[BBox], scale: float) -> Image:
    mask = np.full(shape[:2], 255, dtype=np.uint8)
    for x1, y1, x2, y2 in _grown(boxes, scale):
        mask[max(y1, 0) : max(y2, 0), max(x1, 0) : max(x2, 0)] = 0
    return mask


def _outside(points: FloatArray, boxes: Sequence[BBox], scale: float) -> BoolArray:
    keep = np.ones(len(points), dtype=np.bool_)
    for x1, y1, x2, y2 in _grown(boxes, scale):
        inside = (
            (points[:, 0] >= x1) & (points[:, 0] < x2) & (points[:, 1] >= y1) & (points[:, 1] < y2)
        )
        keep &= ~inside
    return keep


def _grown(boxes: Sequence[BBox], scale: float) -> Iterator[tuple[int, int, int, int]]:
    for box in boxes:
        grow_x = BOX_GROWTH * (box.x2 - box.x1) + BOX_MARGIN_PX
        grow_y = BOX_GROWTH * (box.y2 - box.y1) + BOX_MARGIN_PX
        yield (
            int((box.x1 - grow_x) * scale),
            int((box.y1 - grow_y) * scale),
            int(np.ceil((box.x2 + grow_x) * scale)),
            int(np.ceil((box.y2 + grow_y) * scale)),
        )


def _map_sample(sample: TrackSample, transform: FloatArray) -> TrackSample:
    centroid = _apply(transform, np.array([[sample.centroid.x, sample.centroid.y]]))[0]
    box = sample.bbox
    corners = _apply(
        transform,
        np.array([[box.x1, box.y1], [box.x2, box.y1], [box.x1, box.y2], [box.x2, box.y2]]),
    )
    zoom = abs(float(np.linalg.det(transform[:2, :2])))  # Area scales with the zoom squared.
    return sample.model_copy(
        update={
            "centroid": Point2(x=float(centroid[0]), y=float(centroid[1])),
            "bbox": BBox(
                x1=float(corners[:, 0].min()),
                y1=float(corners[:, 1].min()),
                x2=float(corners[:, 0].max()),
                y2=float(corners[:, 1].max()),
            ),
            "area_px": sample.area_px * zoom,
        }
    )


def _apply(transform: FloatArray, points: FloatArray) -> FloatArray:
    homogeneous = np.column_stack([points, np.ones(len(points))])
    return (homogeneous @ transform.T)[:, :2]


def _max_motion(transforms: Sequence[FloatArray], corners: FloatArray) -> float:
    if not transforms:
        return 0.0
    return max(
        float(np.linalg.norm(_apply(t, corners) - corners, axis=1).max()) for t in transforms
    )


def _gray(frame: Image, scale: float) -> Image:
    if scale < 1.0:
        frame = np.asarray(
            cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA), np.uint8
        )
    return np.asarray(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), np.uint8)


def _thumbnail(gray: Image) -> FloatArray:
    return cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float64)


def _frames(video: Path) -> Iterator[Image]:
    capture = cv2.VideoCapture(str(video))
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                return
            yield np.asarray(frame, np.uint8)
    finally:
        capture.release()
