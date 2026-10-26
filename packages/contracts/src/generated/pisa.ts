/* Generated from schema/pisa.schema.json by scripts/generate-ts.mjs. Do not edit by hand. */

/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Locale".
 */
export type Locale = "en" | "es" | "zh-CN" | "pt-BR";
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "JobSource".
 */
export type JobSource = "web" | "whatsapp" | "eval";
/**
 * user: a video someone submitted; never sent to a contributor-tier model. internal: our own test clips; contributor tier allowed.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "DataPolicy".
 */
export type DataPolicy = "user" | "internal";
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Stage".
 */
export type Stage = "ingest" | "plan" | "track" | "stabilize" | "measure" | "test" | "verdict" | "explain" | "render";
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "JobStatus".
 */
export type JobStatus = "queued" | "running" | "done" | "failed";
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EventType".
 */
export type EventType = "fall" | "throw" | "bounce" | "pair_drop";
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "CameraMotion".
 */
export type CameraMotion = "static" | "handheld" | "pan" | "unknown";
/**
 * Why nothing in a clip can be measured. no_free_flight: nothing falls, flies or bounces on its own (objects are carried, pushed, self-propelled, or still). too_unclear: something does, but it is too small, blurred, hidden, brief or cut to follow.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "PlanReason".
 */
export type PlanReason = "no_free_flight" | "too_unclear";
/**
 * T1 free_fall_shape, T2 galileo_pair, T3 bounce_energy, T4 implied_g, T5 time_base_consistency.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "TestId".
 */
export type TestId = "free_fall_shape" | "galileo_pair" | "bounce_energy" | "implied_g" | "time_base_consistency";
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "TestOutcome".
 */
export type TestOutcome = "pass" | "violation" | "insufficient_data" | "not_applicable";
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "VerdictLabel".
 */
export type VerdictLabel = "physically_impossible" | "consistent_with_real_physics" | "inconclusive";
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "CostUnit".
 */
export type CostUnit = "input_tokens" | "output_tokens" | "frames";
/**
 * What the ghost follows. fit: the closest constant-gravity path through the measured points. earth_gravity: Earth's gravity at the measured scale. partner: the shared acceleration two objects released together must have. elastic_bounce: the highest bounce physics allows, keeping all the arriving speed.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "GhostModel".
 */
export type GhostModel = "fit" | "earth_gravity" | "partner" | "elastic_bounce";

/**
 * Shared contracts between the Pisa engine (Python) and web app (TypeScript). Conventions: every property is required and optional values are nullable; times are in seconds, lengths in meters, image coordinates in pixels with the origin at the top-left and y pointing down.
 */
export interface PisaContracts {}
/**
 * A user-facing error. The client localizes `code`; no free text crosses the boundary.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "ErrorInfo".
 */
export interface ErrorInfo {
  code: string;
  stage: Stage | null;
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Job".
 */
export interface Job {
  id: string;
  created_at: string;
  source: JobSource;
  locale: Locale;
  data_policy: DataPolicy;
  status: JobStatus;
  /**
   * The stage running now, or the last one reached.
   */
  stage: Stage | null;
  error: ErrorInfo | null;
}
/**
 * What ffprobe reports about a video file.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "VideoProbe".
 */
export interface VideoProbe {
  /**
   * Display width after rotation.
   */
  width: number;
  /**
   * Display height after rotation.
   */
  height: number;
  duration_s: number;
  /**
   * Average frame rate numerator.
   */
  fps_num: number;
  /**
   * Average frame rate denominator.
   */
  fps_den: number;
  /**
   * True when the stream's frame rate is variable.
   */
  is_vfr: boolean;
  /**
   * Display rotation from the container, in degrees.
   */
  rotation_deg: number;
  frame_count: number | null;
  codec: string;
  has_audio: boolean;
  size_bytes: number;
}
/**
 * Maps frame indices of a constant-frame-rate clip to time: t(frame) = start_s + frame * fps_den / fps_num.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Timebase".
 */
export interface Timebase {
  fps_num: number;
  fps_den: number;
  /**
   * Time of frame 0 in the source video.
   */
  start_s: number;
  frame_count: number;
}
/**
 * Probe of the source file and of the normalized H.264 MP4 at a constant frame rate that every later stage reads.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "IngestResult".
 */
export interface IngestResult {
  source: VideoProbe;
  normalized: VideoProbe;
  timebase: Timebase;
  scene_cuts_s: number[];
}
/**
 * One physical event the planner saw in the clip.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "PlanEvent".
 */
export interface PlanEvent {
  type: EventType;
  /**
   * When the event starts, in seconds from the start of the clip.
   */
  start_s: number;
  /**
   * When the event ends, in seconds from the start of the clip.
   */
  end_s: number;
  /**
   * Short concrete noun phrases for the moving objects, one object each, for example "tennis ball". Two phrases for a pair drop.
   */
  object_phrases: string[];
}
/**
 * An object of roughly known size near the plane of motion, used to convert pixels to meters.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "ReferenceObject".
 */
export interface ReferenceObject {
  /**
   * Short concrete noun phrase, for example "door".
   */
  phrase: string;
  dimension: "height" | "width" | "diameter" | "length";
  /**
   * Smallest plausible real size in meters.
   */
  size_min_m: number;
  /**
   * Largest plausible real size in meters.
   */
  size_max_m: number;
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "CameraNotes".
 */
export interface CameraNotes {
  motion: CameraMotion;
  has_cuts: boolean;
  slow_motion_suspected: boolean;
}
/**
 * The planner's reading of a clip. Sent as a structured-output schema, so it stays inside Muse Spark's strict subset: no oneOf or allOf, every object closed, every key required.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Plan".
 */
export interface Plan {
  /**
   * False when nothing in the clip can be measured.
   */
  measurable: boolean;
  /**
   * Why nothing is measurable, when measurable is false.
   */
  reason: PlanReason | null;
  events: PlanEvent[];
  references: ReferenceObject[];
  camera: CameraNotes;
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "BBox".
 */
export interface BBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Point2".
 */
export interface Point2 {
  x: number;
  y: number;
}
/**
 * One tracked object in one frame. centroid is the mask centroid and area_px the mask area, both in pixels.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "TrackSample".
 */
export interface TrackSample {
  /**
   * Frame index in the normalized clip.
   */
  frame: number;
  /**
   * Time from the timebase.
   */
  t_s: number;
  bbox: BBox;
  centroid: Point2;
  area_px: number;
  confidence: number | null;
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "TrackedObject".
 */
export interface TrackedObject {
  phrase: string;
  /**
   * SAM's id, unique within one phrase.
   */
  object_id: number;
  samples: TrackSample[];
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "TrackSet".
 */
export interface TrackSet {
  width: number;
  height: number;
  timebase: Timebase;
  objects: TrackedObject[];
}
/**
 * A number the explainer is allowed to quote.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Measurement".
 */
export interface Measurement {
  name: string;
  value: number;
  /**
   * SI unit, or "1" when dimensionless.
   */
  unit: string;
  ci_low: number | null;
  ci_high: number | null;
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "TestResult".
 */
export interface TestResult {
  test: TestId;
  outcome: TestOutcome;
  confidence: number;
  measurements: Measurement[];
  reason_code: string | null;
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Verdict".
 */
export interface Verdict {
  label: VerdictLabel;
  policy_version: string;
  decisive_tests: TestId[];
  /**
   * Why the verdict is inconclusive, when it is.
   */
  reason_code: string | null;
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "CostEntry".
 */
export interface CostEntry {
  stage: Stage;
  model: string;
  unit: CostUnit;
  quantity: number;
  usd: number;
}
/**
 * How camera motion was handled before measuring. Unreliable frames are dropped; cuts are in the ingest result.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Stabilization".
 */
export interface Stabilization {
  /**
   * False when the camera was still, or the background had nothing to follow.
   */
  applied: boolean;
  /**
   * Largest displacement of a frame corner relative to the first frame of its shot.
   */
  max_motion_px: number;
  frames: number;
  unreliable_frames: number;
}
/**
 * A short explanation of the verdict in the job's language, written by Muse Spark from the measurements. Every number in it was checked against them; when the check fails there is no explanation and clients use their own templated copy.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Explanation".
 */
export interface Explanation {
  locale: Locale;
  text: string;
  model: string;
}
/**
 * One measured flight and its ghost at the same times, in stabilized image pixels (y points down), for charts.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvidenceSeries".
 */
export interface EvidenceSeries {
  phrase: string;
  object_id: number;
  model: GhostModel;
  t_s: number[];
  y_px: number[];
  ghost_y_px: number[];
  /**
   * Geometric mean of the scale range, when a size reference gave one.
   */
  px_per_m: number | null;
}
/**
 * The evidence clip: the original frames with the tracked object outlined, its measured points and the ghost. Served by the engine at /jobs/{id}/evidence.mp4 until expires_at, then deleted, because it shows the user's video.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvidenceVideo".
 */
export interface EvidenceVideo {
  width: number;
  height: number;
  duration_s: number;
  /**
   * 1 for real time; 0.5 when short events are slowed to half speed.
   */
  playback_rate: number;
  size_bytes: number;
  expires_at: string;
}
/**
 * What the result shows as proof: the video (while it exists) and the measured flights with their ghosts, most telling first.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Evidence".
 */
export interface Evidence {
  video: EvidenceVideo | null;
  series: EvidenceSeries[];
}
/**
 * Everything the result page and the WhatsApp reply need for one job.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "AnalysisResult".
 */
export interface AnalysisResult {
  job: Job;
  ingest: IngestResult | null;
  plan: Plan | null;
  tracks: TrackSet | null;
  stabilization: Stabilization | null;
  tests: TestResult[];
  verdict: Verdict | null;
  explanation: Explanation | null;
  evidence: Evidence | null;
  costs: CostEntry[];
}
