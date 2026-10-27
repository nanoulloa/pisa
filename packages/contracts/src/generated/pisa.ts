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
 * Pipeline stages, in order. baseline is the eval's call asking Muse Spark for its opinion; no job ever runs it.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "Stage".
 */
export type Stage =
  "ingest" | "plan" | "track" | "stabilize" | "measure" | "test" | "verdict" | "explain" | "render" | "baseline";
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
 * What a clip in the eval set really is: filmed with a camera, or made by a video generator.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvalTruth".
 */
export type EvalTruth = "real" | "generated";
/**
 * A model's answer to "Is this video real or AI-generated?"
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvalOpinion".
 */
export type EvalOpinion = "real" | "generated" | "unsure";

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
/**
 * A share of clips with its 95% Wilson interval, which stays honest on small samples. Null shares when there are no clips to count.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvalRate".
 */
export interface EvalRate {
  count: number;
  total: number;
  value: number | null;
  ci_low: number | null;
  ci_high: number | null;
}
/**
 * How many clips of one kind got each verdict: one row of the confusion matrix.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvalVerdictCounts".
 */
export interface EvalVerdictCounts {
  truth: EvalTruth;
  physically_impossible: number;
  consistent_with_real_physics: number;
  inconclusive: number;
}
/**
 * The confusion matrix restricted to clips with one tag, such as handheld or bounce.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvalGroup".
 */
export interface EvalGroup {
  tag: string;
  rows: EvalVerdictCounts[];
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvalTruthCounts".
 */
export interface EvalTruthCounts {
  real: number;
  generated: number;
}
/**
 * What one physics test contributed, counted in clips. measured: the test passed or found a violation at least once. violated: at least one violation, at any confidence. decisive: judged physically impossible with this test among the decisive ones.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvalTestStats".
 */
export interface EvalTestStats {
  test: TestId;
  measured: EvalTruthCounts;
  violated: EvalTruthCounts;
  decisive: EvalTruthCounts;
  /**
   * Highest confidence of a violation on a real clip: how close this test came to a false positive.
   */
  closest_call_real: number | null;
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvalClip".
 */
export interface EvalClip {
  id: string;
  truth: EvalTruth;
  tags: string[];
  verdict: VerdictLabel;
  /**
   * Why the verdict is inconclusive, or the error code of a job that failed.
   */
  reason_code: string | null;
  decisive_tests: TestId[];
  latency_s: number | null;
  cost_usd: number;
  baseline: EvalOpinion | null;
}
/**
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvalSummary".
 */
export interface EvalSummary {
  median: number | null;
  p90: number | null;
  max: number | null;
}
/**
 * Pisa's verdicts on a labeled set of clips, scored against what each clip really is. false_positive_rate: real clips judged physically impossible, the number that matters most. detection_rate: generated clips judged physically impossible. inconclusive_rate: all clips judged inconclusive. conclusive_accuracy: among conclusive verdicts, the share that matches the truth. latency_s: seconds per clip, end to end. baseline: Muse Spark's opinion on the same clips, when it was asked.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvalReport".
 */
export interface EvalReport {
  name: string;
  created_at: string;
  engine_version: string;
  policy_version: string;
  /**
   * True when every clip was rendered by the engine's synthetic generator rather than filmed or generated by a video model.
   */
  synthetic: boolean;
  segmenter: string;
  planner: string;
  confusion: EvalVerdictCounts[];
  false_positive_rate: EvalRate;
  detection_rate: EvalRate;
  inconclusive_rate: EvalRate;
  conclusive_accuracy: EvalRate;
  by_tag: EvalGroup[];
  tests: EvalTestStats[];
  latency_s: EvalSummary;
  /**
   * Paid API calls for the whole set.
   */
  cost_usd: number;
  cost_usd_per_clip: EvalSummary;
  clips: EvalClip[];
  baseline: EvalBaseline | null;
}
/**
 * Muse Spark asked "Is this video real or AI-generated?" about the same clips, scored like Pisa. false_positive_rate: real clips it called generated. detection_rate: generated clips it called generated. unsure_rate: all clips it would not call; failed calls count as unsure.
 *
 * This interface was referenced by `PisaContracts`'s JSON-Schema
 * via the `definition` "EvalBaseline".
 */
export interface EvalBaseline {
  model: string;
  question: string;
  false_positive_rate: EvalRate;
  detection_rate: EvalRate;
  unsure_rate: EvalRate;
  cost_usd: number;
}
