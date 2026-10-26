# Generated from packages/contracts/schema/pisa.schema.json by `make gen`. Do not edit by hand.

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from typing import Annotated, Literal
from uuid import UUID


class PisaContracts(BaseModel):
    """
    Shared contracts between the Pisa engine (Python) and web app (TypeScript). Conventions: every property is required and optional values are nullable; times are in seconds, lengths in meters, image coordinates in pixels with the origin at the top-left and y pointing down.
    """

    model_config = ConfigDict(
        extra="forbid",
    )


type Locale = Literal["en", "es", "zh-CN", "pt-BR"]


type JobSource = Literal["web", "whatsapp", "eval"]


type DataPolicy = Literal["user", "internal"]
"""
user: a video someone submitted; never sent to a contributor-tier model. internal: our own test clips; contributor tier allowed.
"""


type Stage = Literal[
    "ingest", "plan", "track", "stabilize", "measure", "test", "verdict", "explain", "render"
]


type JobStatus = Literal["queued", "running", "done", "failed"]


class ErrorInfo(BaseModel):
    """
    A user-facing error. The client localizes `code`; no free text crosses the boundary.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    code: Annotated[str, Field(examples=["video_too_long", "unsupported_format"])]
    stage: Stage | None


class Job(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: UUID
    created_at: AwareDatetime
    source: JobSource
    locale: Locale
    data_policy: DataPolicy
    status: JobStatus
    stage: Stage | None
    """
    The stage running now, or the last one reached.
    """
    error: ErrorInfo | None


class VideoProbe(BaseModel):
    """
    What ffprobe reports about a video file.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    width: Annotated[int, Field(ge=1)]
    """
    Display width after rotation.
    """
    height: Annotated[int, Field(ge=1)]
    """
    Display height after rotation.
    """
    duration_s: Annotated[float, Field(ge=0.0)]
    fps_num: Annotated[int, Field(ge=1)]
    """
    Average frame rate numerator.
    """
    fps_den: Annotated[int, Field(ge=1)]
    """
    Average frame rate denominator.
    """
    is_vfr: bool
    """
    True when the stream's frame rate is variable.
    """
    rotation_deg: int
    """
    Display rotation from the container, in degrees.
    """
    frame_count: Annotated[int | None, Field(ge=0)]
    codec: str
    has_audio: bool
    size_bytes: Annotated[int, Field(ge=0)]


class Timebase(BaseModel):
    """
    Maps frame indices of a constant-frame-rate clip to time: t(frame) = start_s + frame * fps_den / fps_num.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    fps_num: Annotated[int, Field(ge=1)]
    fps_den: Annotated[int, Field(ge=1)]
    start_s: Annotated[float, Field(ge=0.0)]
    """
    Time of frame 0 in the source video.
    """
    frame_count: Annotated[int, Field(ge=0)]


class IngestResult(BaseModel):
    """
    Probe of the source file and of the normalized H.264 MP4 at a constant frame rate that every later stage reads.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    source: VideoProbe
    normalized: VideoProbe
    timebase: Timebase
    scene_cuts_s: list[float]


type EventType = Literal["fall", "throw", "bounce", "pair_drop"]


type CameraMotion = Literal["static", "handheld", "pan", "unknown"]


class PlanEvent(BaseModel):
    """
    One physical event the planner saw in the clip.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    type: EventType
    start_s: float
    """
    When the event starts, in seconds from the start of the clip.
    """
    end_s: float
    """
    When the event ends, in seconds from the start of the clip.
    """
    object_phrases: list[str]
    """
    Short concrete noun phrases for the moving objects, one object each, for example "tennis ball". Two phrases for a pair drop.
    """


class ReferenceObject(BaseModel):
    """
    An object of roughly known size near the plane of motion, used to convert pixels to meters.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    phrase: str
    """
    Short concrete noun phrase, for example "door".
    """
    dimension: Literal["height", "width", "diameter", "length"]
    size_min_m: float
    """
    Smallest plausible real size in meters.
    """
    size_max_m: float
    """
    Largest plausible real size in meters.
    """


class CameraNotes(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    motion: CameraMotion
    has_cuts: bool
    slow_motion_suspected: bool


type PlanReason = Literal["no_free_flight", "too_unclear"]
"""
Why nothing in a clip can be measured. no_free_flight: nothing falls, flies or bounces on its own (objects are carried, pushed, self-propelled, or still). too_unclear: something does, but it is too small, blurred, hidden, brief or cut to follow.
"""


class Plan(BaseModel):
    """
    The planner's reading of a clip. Sent as a structured-output schema, so it stays inside Muse Spark's strict subset: no oneOf or allOf, every object closed, every key required.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    measurable: bool
    """
    False when nothing in the clip can be measured.
    """
    reason: PlanReason | None
    """
    Why nothing is measurable, when measurable is false.
    """
    events: list[PlanEvent]
    references: list[ReferenceObject]
    camera: CameraNotes


class BBox(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    x1: float
    y1: float
    x2: float
    y2: float


class Point2(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    x: float
    y: float


class TrackSample(BaseModel):
    """
    One tracked object in one frame. centroid is the mask centroid and area_px the mask area, both in pixels.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    frame: Annotated[int, Field(ge=0)]
    """
    Frame index in the normalized clip.
    """
    t_s: float
    """
    Time from the timebase.
    """
    bbox: BBox
    centroid: Point2
    area_px: Annotated[float, Field(ge=0.0)]
    confidence: Annotated[float | None, Field(ge=0.0, le=1.0)]


class TrackedObject(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    phrase: str
    object_id: Annotated[int, Field(ge=0)]
    """
    SAM's id, unique within one phrase.
    """
    samples: list[TrackSample]


class TrackSet(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    width: Annotated[int, Field(ge=1)]
    height: Annotated[int, Field(ge=1)]
    timebase: Timebase
    objects: list[TrackedObject]


type TestId = Literal[
    "free_fall_shape", "galileo_pair", "bounce_energy", "implied_g", "time_base_consistency"
]
"""
T1 free_fall_shape, T2 galileo_pair, T3 bounce_energy, T4 implied_g, T5 time_base_consistency.
"""


type TestOutcome = Literal["pass", "violation", "insufficient_data", "not_applicable"]


class Measurement(BaseModel):
    """
    A number the explainer is allowed to quote.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    name: Annotated[str, Field(examples=["implied_g", "acceleration_ratio"])]
    value: float
    unit: Annotated[str, Field(examples=["m/s^2", "1"])]
    """
    SI unit, or "1" when dimensionless.
    """
    ci_low: float | None
    ci_high: float | None


class TestResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    test: TestId
    outcome: TestOutcome
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    measurements: list[Measurement]
    reason_code: str | None


type VerdictLabel = Literal["physically_impossible", "consistent_with_real_physics", "inconclusive"]


class Verdict(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    label: VerdictLabel
    policy_version: str
    decisive_tests: list[TestId]
    reason_code: str | None
    """
    Why the verdict is inconclusive, when it is.
    """


type CostUnit = Literal["input_tokens", "output_tokens", "frames"]


class CostEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    stage: Stage
    model: str
    unit: CostUnit
    quantity: Annotated[float, Field(ge=0.0)]
    usd: Annotated[float, Field(ge=0.0)]


class Stabilization(BaseModel):
    """
    How camera motion was handled before measuring. Unreliable frames are dropped; cuts are in the ingest result.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    applied: bool
    """
    False when the camera was still, or the background had nothing to follow.
    """
    max_motion_px: Annotated[float, Field(ge=0.0)]
    """
    Largest displacement of a frame corner relative to the first frame of its shot.
    """
    frames: Annotated[int, Field(ge=0)]
    unreliable_frames: Annotated[int, Field(ge=0)]


class Explanation(BaseModel):
    """
    A short explanation of the verdict in the job's language, written by Muse Spark from the measurements. Every number in it was checked against them; when the check fails there is no explanation and clients use their own templated copy.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    locale: Locale
    text: str
    model: str


type GhostModel = Literal["fit", "earth_gravity", "partner", "elastic_bounce"]
"""
What the ghost follows. fit: the closest constant-gravity path through the measured points. earth_gravity: Earth's gravity at the measured scale. partner: the shared acceleration two objects released together must have. elastic_bounce: the highest bounce physics allows, keeping all the arriving speed.
"""


class EvidenceSeries(BaseModel):
    """
    One measured flight and its ghost at the same times, in stabilized image pixels (y points down), for charts.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    phrase: str
    object_id: Annotated[int, Field(ge=0)]
    model: GhostModel
    t_s: list[float]
    y_px: list[float]
    ghost_y_px: list[float]
    px_per_m: float | None
    """
    Geometric mean of the scale range, when a size reference gave one.
    """


class EvidenceVideo(BaseModel):
    """
    The evidence clip: the original frames with the tracked object outlined, its measured points and the ghost. Served by the engine at /jobs/{id}/evidence.mp4 until expires_at, then deleted, because it shows the user's video.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    width: Annotated[int, Field(ge=1)]
    height: Annotated[int, Field(ge=1)]
    duration_s: Annotated[float, Field(ge=0.0)]
    playback_rate: Annotated[float, Field(ge=0.0)]
    """
    1 for real time; 0.5 when short events are slowed to half speed.
    """
    size_bytes: Annotated[int, Field(ge=0)]
    expires_at: AwareDatetime


class Evidence(BaseModel):
    """
    What the result shows as proof: the video (while it exists) and the measured flights with their ghosts, most telling first.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    video: EvidenceVideo | None
    series: list[EvidenceSeries]


class AnalysisResult(BaseModel):
    """
    Everything the result page and the WhatsApp reply need for one job.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    job: Job
    ingest: IngestResult | None
    plan: Plan | None
    tracks: TrackSet | None
    stabilization: Stabilization | None
    tests: list[TestResult]
    verdict: Verdict | None
    explanation: Explanation | None
    evidence: Evidence | None
    costs: list[CostEntry]
