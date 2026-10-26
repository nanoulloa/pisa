"""SAM 3.1 on Meta Model API (https://dev.meta.ai/docs/sam/segmenting).

One concept phrase per request. The streamed output is decoded with Meta's
`meta_sam_parser`; we only turn its mask records into centroids and areas.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from meta_sam_parser import (
    SegmentationBoxRecord,
    SegmentationMaskRecord,
    SegmentationRecord,
    decode_mask_to_raster,
    parse_responses_stream,
    video_segmentation_format,
)

from pisa_contracts import BBox, CostEntry, DataPolicy, Point2, Timebase, TrackedObject, TrackSample
from pisa_engine.model_api.client import MetaModelApiClient
from pisa_engine.model_api.pricing import sam_billed_frames, sam_cost_usd
from pisa_engine.tracking.segmenter import frame_time


class Sam31Segmenter:
    def __init__(
        self,
        client: MetaModelApiClient,
        *,
        model: str = "sam-3.1",
        on_raw_output: Callable[[str], None] | None = None,
    ) -> None:
        """`on_raw_output` receives the full streamed text, for spikes and debugging."""
        self._client = client
        self._model = model
        self._on_raw_output = on_raw_output

    async def track(
        self, video: Path, phrase: str, timebase: Timebase, *, policy: DataPolicy
    ) -> list[TrackedObject]:
        file_id = await self._client.upload_file(video)
        body = {
            "model": self._model,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": phrase},
                        {"type": "input_video", "file_id": file_id},
                    ],
                }
            ],
            "metadata": {"include_confidence": "true", "mask_encoding": "lossless"},
        }
        cost = sam_cost_usd(timebase.frame_count)
        events = self._client.stream_response(body, policy=policy, worst_case_usd=cost)
        result = await parse_responses_stream(events, video_segmentation_format()).final_result()
        if self._on_raw_output is not None:
            self._on_raw_output(result.raw_output)
        self._client.record(
            [
                CostEntry(
                    stage="track",
                    model=self._model,
                    unit="frames",
                    quantity=sam_billed_frames(timebase.frame_count),
                    usd=cost,
                )
            ]
        )
        return tracks_from_records(result.records, phrase=phrase, timebase=timebase)


@dataclass(frozen=True, slots=True)
class _MaskStats:
    centroid: Point2
    area_px: float


def tracks_from_records(
    records: Iterable[SegmentationRecord], *, phrase: str, timebase: Timebase
) -> list[TrackedObject]:
    """Group parser records into one track per object id, using the latest mask revision."""
    boxes: dict[tuple[int, str], SegmentationBoxRecord] = {}
    masks: dict[tuple[int, str], SegmentationMaskRecord] = {}
    for record in records:
        if record.kind == "text" or record.frame is None:
            continue
        key = (record.frame.frame_index, record.object_id)
        if record.kind == "box":
            boxes[key] = record
        elif key not in masks or record.revision >= masks[key].revision:
            masks[key] = record

    samples: dict[int, list[TrackSample]] = {}
    for (frame, object_id), mask in sorted(masks.items()):
        stats = mask_stats(mask)
        if stats is None:
            continue
        box = boxes.get((frame, object_id))
        bounds = mask.bounds
        confidence = mask.confidence
        if confidence is None and box is not None:
            confidence = box.confidence
        samples.setdefault(int(object_id), []).append(
            TrackSample(
                frame=frame,
                t_s=frame_time(timebase, frame),
                bbox=BBox(
                    x1=box.left if box else bounds.left,
                    y1=box.top if box else bounds.top,
                    x2=box.right if box else bounds.right,
                    y2=box.bottom if box else bounds.bottom,
                ),
                centroid=stats.centroid,
                area_px=stats.area_px,
                confidence=confidence,
            )
        )
    return [
        TrackedObject(phrase=phrase, object_id=object_id, samples=object_samples)
        for object_id, object_samples in sorted(samples.items())
    ]


def mask_stats(record: SegmentationMaskRecord) -> _MaskStats | None:
    """Centroid and area of a box-local mask, in source-frame pixels. None for an empty mask."""
    mask = record.mask
    raster = np.frombuffer(decode_mask_to_raster(mask), dtype=np.uint8).reshape(
        mask.height, mask.width
    )
    rows, cols = np.nonzero(raster)
    if rows.size == 0:
        return None
    bounds = record.bounds
    cell_w = (bounds.right - bounds.left) / mask.width
    cell_h = (bounds.bottom - bounds.top) / mask.height
    return _MaskStats(
        centroid=Point2(
            x=bounds.left + (float(cols.mean()) + 0.5) * cell_w,
            y=bounds.top + (float(rows.mean()) + 0.5) * cell_h,
        ),
        area_px=float(rows.size) * cell_w * cell_h,
    )
