/**
 * TypeScript mirror of data-schema.md — the session JSON contract.
 *
 * This must match the backend Pydantic model exactly.
 * A mismatch between these types and the backend is a bug.
 */

// ─── Sub-types ──────────────────────────────────────────────────────────────

export interface Resolution {
  width: number;
  height: number;
}

export interface MetricEntry {
  value: number | null;
  unit: "deg" | "ratio" | "inches" | "cm";
  primary: boolean;
  nullReason: string | null;
}

export interface SetupMetrics {
  stanceWidthPx: number | null;
  ballPositionRatio: number | null;
  spineTiltDegAtAddress: number | null;
  gripPosition: string | null;
}

export interface ThresholdRange {
  green?: [number, number];
  amber?: [number, number];
  redBelow?: number;
  redAbove?: number;
  greenMax?: number;
  amberMax?: number;
  greenMin?: number;
  amberMin?: number;
  greenRatio?: [number, number];
  amberRatio?: [number, number];
}

export interface MetricScore {
  band: string | null;
  score: number | null;
}

export interface Scores {
  perMetric: Record<string, MetricScore>;
  overall: number | null;
  bandOverall: string | null;
}

export interface CoachingItem {
  priority: number;
  severity: "high" | "medium" | "low";
  title: string;
  explanation: string;
  drillSuggestion: string;
}

export interface Timings {
  agent1Ms: number | null;
  phase1Ms: number | null;
  agent2Ms: number | null;
  phase2Ms: number | null;
  phase3Ms: number | null;
  agent3Ms: number | null;
  phase4Ms: number | null;
  agent4Ms: number | null;
  phase5Ms: number | null;
  agent5Ms: number | null;
  phase7Ms: number | null;
  phase8Ms: number | null;
  totalMs: number | null;
}

// ─── Main session type ──────────────────────────────────────────────────────

export interface SessionJSON {
  // Set by API on upload
  schema_version: string;
  session_id: string;
  created_at: string;
  gender: "male" | "female";
  status: string;
  status_reason: string | null;

  // Set by Agent 1
  input_fps: number | null;
  camera_angle: "face_on" | "down_the_line" | null;
  video_quality_score: number | null;
  resolution: Resolution | null;
  agent1_notes: string | null;

  // Set by Phase 1
  total_swing_attempts: number | null;
  selected_swing_index: number | null;
  hit_confidence_score: number | null;
  backswing_start_frame_index: number | null;
  impact_frame_index: number | null;
  follow_through_end_frame_index: number | null;
  address_frame_range: [number, number] | null;

  // Set by Agent 2
  px_to_inches_scale: number | null;
  calibration_low_confidence: boolean | null;
  calibration_notes: string | null;

  // Set by Phase 2
  keypoints_path: string | null;

  // Set by Phase 3
  setup_metrics: SetupMetrics | null;

  // Set by Agent 3
  detected_shot_type: string | null;
  shot_type_confidence: number | null;
  shot_type_reasoning: string | null;

  // Set by Phase 4
  metrics: Record<string, MetricEntry> | null;

  // Set by Agent 4
  inferred_skill_level: string | null;
  active_thresholds: Record<string, ThresholdRange> | null;

  // Set by Phase 5
  scores: Scores | null;

  // Set by Agent 5 (Phase 6)
  coaching_output: CoachingItem[] | null;

  // Set by Phase 7
  slowmo_video_path: string | null;

  // Set by Phase 8
  annotated_video_path: string | null;
  overlay_rendering_failed: boolean;

  // Observability
  timings: Timings;
}

// ─── API response types ─────────────────────────────────────────────────────

export interface SessionCreateResponse {
  session_id: string;
  status: string;
  created_at: string;
}

export interface SessionStatusResponse {
  session_id: string;
  status: string;
  progress_pct: number;
  status_reason: string | null;
  failed: boolean;
}

export interface Phase1DetectionResponse {
  total_swing_attempts: number | null;
  selected_swing_index: number | null;
  hit_confidence_score: number | null;
  backswing_start_frame_index: number | null;
  impact_frame_index: number | null;
  follow_through_end_frame_index: number | null;
}

export interface OutputStatusResponse {
  ready: boolean;
  path: string | null;
}
