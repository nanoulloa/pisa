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
  reason: string | null;
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
  tests: TestResult[];
  verdict: Verdict | null;
  costs: CostEntry[];
}
