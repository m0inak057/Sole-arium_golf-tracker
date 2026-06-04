"""Session JSON Pydantic model — the single source of truth between phases.

Mirrors ``data-schema.md`` exactly.  Every phase and every agent reads
specific fields from this model and writes specific fields into it.

- ``schema_version`` is always ``"1.3"`` on new sessions.
- Phases do not import other phases.
- Agents do not import phases.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# ─── Sub-models ──────────────────────────────────────────────────────────────


class DualVideoMetadata(BaseModel):
    """Metadata for dual video inputs."""
    
    face_on_fps: float | None = None
    down_the_line_fps: float | None = None
    face_on_resolution: Resolution | None = None
    down_the_line_resolution: Resolution | None = None
    face_on_quality_score: float | None = None
    down_the_line_quality_score: float | None = None
    face_on_duration_seconds: float | None = None
    down_the_line_duration_seconds: float | None = None


class DualVideoProcessingStatus(BaseModel):
    """Processing status for dual video workflow."""
    
    face_on_uploaded: bool = False
    down_the_line_uploaded: bool = False
    face_on_processing_complete: bool = False
    down_the_line_processing_complete: bool = False
    dual_processing_mode: bool = False


class Resolution(BaseModel):
    """Video resolution."""

    width: int
    height: int


class MetricEntry(BaseModel):
    """Shape for every entry in ``metrics`` — see data-schema.md §2.

    Attributes:
        value: The measured value, or ``None`` if the keypoint was unusable.
        unit: Unit of measurement.
        primary: ``False`` if the current camera angle cannot measure this well.
        null_reason: Required when ``value`` is ``None``.
    """

    value: float | None = None
    unit: Literal["deg", "ratio", "inches", "cm"] = "deg"
    primary: bool = True
    null_reason: str | None = None


class SwingWindow(BaseModel):
    """One detected swing stored in all_swing_attempts."""

    index: int
    score: float
    backswing_start: int
    impact: int
    follow_through_end: int
    address_start: int
    address_end: int


class SetupMetrics(BaseModel):
    """Phase 3 output — setup geometry at address."""

    stance_width_px: float | None = None
    ball_position_ratio: float | None = None
    spine_tilt_deg_at_address: float | None = None
    grip_position: str | None = None


class ThresholdRange(BaseModel):
    """A single threshold entry.  Shape varies per metric — this is the union."""

    green: list[float] | None = None
    amber: list[float] | None = None
    red_below: float | None = None
    red_above: float | None = None
    green_max: float | None = None
    amber_max: float | None = None
    green_min: float | None = None
    amber_min: float | None = None
    green_ratio: list[float] | None = None
    amber_ratio: list[float] | None = None


class MetricScore(BaseModel):
    """Per-metric scoring result."""

    band: str | None = None
    score: float | None = None


class Scores(BaseModel):
    """Phase 5 output — performance scoring."""

    per_metric: dict[str, MetricScore] = Field(default_factory=dict)
    overall: float | None = None
    band_overall: str | None = None


class CoachingItem(BaseModel):
    """A single coaching recommendation — data-schema.md §5."""

    priority: int
    severity: Literal["high", "medium", "low"]
    title: str
    explanation: str
    drill_suggestion: str = ""


class Timings(BaseModel):
    """Pipeline timing information for observability."""

    agent1_ms: int | None = None
    phase1_ms: int | None = None
    agent2_ms: int | None = None
    phase2_ms: int | None = None
    phase3_ms: int | None = None
    agent3_ms: int | None = None
    phase4_ms: int | None = None
    agent4_ms: int | None = None
    phase5_ms: int | None = None
    agent5_ms: int | None = None  # Agent 5 IS Phase 6 — no separate phase6_ms
    phase7_ms: int | None = None
    phase8_ms: int | None = None
    total_ms: int | None = None


# ─── Status lifecycle (data-schema.md §3) ────────────────────────────────────

SESSION_STATUSES = [
    "uploaded",
    "agent1_running", "agent1_done",
    "phase1_running", "phase1_done",
    "agent2_running", "agent2_done",
    "phase2_running", "phase2_done",
    "phase3_running", "phase3_done",
    "agent3_running", "agent3_done",
    "phase4_running", "phase4_done",
    "agent4_running", "agent4_done",
    "phase5_running", "phase5_done",
    "agent5_running", "agent5_done",
    "phase7_running", "phase7_done",
    "phase8_running", "phase8_done",
    "complete",
    "failed",
]

FAILURE_REASONS = [
    "unreadable_video",
    "no_real_swing_detected",
    "agent1_malformed_output",
    "agent2_malformed_output",
    "agent3_malformed_output",
    "agent4_malformed_output",
    "agent5_malformed_output",
    "internal_error",
]

# Progress percentage per status for polling UI
STATUS_PROGRESS: dict[str, int] = {
    "uploaded": 0,
    "agent1_running": 5, "agent1_done": 10,
    "phase1_running": 12, "phase1_done": 20,
    "agent2_running": 22, "agent2_done": 25,
    "phase2_running": 27, "phase2_done": 35,
    "phase3_running": 37, "phase3_done": 40,
    "agent3_running": 42, "agent3_done": 45,
    "phase4_running": 47, "phase4_done": 55,
    "agent4_running": 57, "agent4_done": 60,
    "phase5_running": 62, "phase5_done": 65,
    "agent5_running": 67, "agent5_done": 70,
    "phase7_running": 72, "phase7_done": 80,
    "phase8_running": 82, "phase8_done": 95,
    "complete": 100,
    "failed": 0,
}


# ─── Main session model ─────────────────────────────────────────────────────


class SessionJSON(BaseModel):
    """The canonical session JSON — data-schema.md §1.

    This is the contract every phase and agent reads/writes.
    """

    # ── Set by API on upload ─────────────────────────────────────────
    schema_version: str = "1.3"
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    gender: Literal["male", "female"]
    status: str = "uploaded"
    status_reason: str | None = None

    # ── Set by Agent 1 (Video Intelligence) ──────────────────────────
    input_fps: float | None = None
    camera_angle: Literal["face_on", "down_the_line"] | None = None
    video_quality_score: float | None = None
    resolution: Resolution | None = None
    agent1_notes: str | None = None
    
    # ── Dual Video Support (Phase 2+) ────────────────────────────────
    dual_video_metadata: DualVideoMetadata | None = None
    dual_video_status: DualVideoProcessingStatus | None = None
    primary_camera_angle: Literal["face_on", "down_the_line"] | None = None

    # ── Set by Phase 1 (Hit Detection) ───────────────────────────────
    total_swing_attempts: int | None = None
    selected_swing_index: int | None = None
    hit_confidence_score: float | None = None
    backswing_start_frame_index: int | None = None
    impact_frame_index: int | None = None
    follow_through_end_frame_index: int | None = None
    address_frame_range: list[int] | None = None
    all_swing_attempts: list[SwingWindow] | None = None  # All detected real swings

    # ── Set by Agent 2 (Body Calibration) ────────────────────────────
    px_to_inches_scale: float | None = None
    calibration_low_confidence: bool | None = None
    calibration_notes: str | None = None

    # ── Set by Phase 2 (Keypoints) ───────────────────────────────────
    keypoints_path: str | None = None

    # ── Set by Phase 3 (Setup Analysis) ──────────────────────────────
    setup_metrics: SetupMetrics | None = None

    # ── Set by Agent 3 (Shot Classification) ─────────────────────────
    detected_shot_type: str | None = None
    shot_type_confidence: float | None = None
    shot_type_reasoning: str | None = None

    # ── Set by Phase 4 (Biomechanical Metrics) ───────────────────────
    metrics: dict[str, MetricEntry] | None = None

    # ── Set by Agent 4 (Threshold Adaptation) ────────────────────────
    inferred_skill_level: str | None = None
    active_thresholds: dict[str, ThresholdRange] | None = None

    # ── Set by Phase 5 (Performance Scoring) ─────────────────────────
    scores: Scores | None = None

    # ── Set by Agent 5 == Phase 6 (Coaching) ─────────────────────────
    coaching_output: list[CoachingItem] | None = None

    # ── Set by Phase 7 ───────────────────────────────────────────────
    slowmo_video_path: str | None = None
    
    # ── Dual Video Output Paths (Phase 2+) ───────────────────────────
    slowmo_face_on_path: str | None = None
    slowmo_down_the_line_path: str | None = None

    # ── Set by Phase 8 ───────────────────────────────────────────────
    annotated_video_path: str | None = None
    overlay_rendering_failed: bool = False
    
    # ── Dual Video Annotated Paths (Phase 2+) ────────────────────────
    annotated_face_on_path: str | None = None
    annotated_down_the_line_path: str | None = None

    # ── Observability ────────────────────────────────────────────────
    timings: Timings = Field(default_factory=Timings)


def create_session(gender: Literal["male", "female"]) -> SessionJSON:
    """Create a new session with a fresh UUID and timestamp.

    Args:
        gender: The golfer's gender selection.

    Returns:
        A ``SessionJSON`` initialised with schema_version 1.3, a new
        session_id, the current UTC time, and the given gender.
    """
    return SessionJSON(gender=gender)


def create_dual_video_session(gender: Literal["male", "female"]) -> SessionJSON:
    """Create a new session configured for dual video processing.

    Args:
        gender: The golfer's gender selection.

    Returns:
        A ``SessionJSON`` initialised for dual video workflow.
    """
    session = SessionJSON(gender=gender)
    session.dual_video_status = DualVideoProcessingStatus(dual_processing_mode=True)
    session.dual_video_metadata = DualVideoMetadata()
    return session


def get_progress_pct(status: str) -> int:
    """Map a session status to a 0–100 progress percentage.

    Args:
        status: A valid status string from the lifecycle.

    Returns:
        Integer progress percentage.
    """
    return STATUS_PROGRESS.get(status, 0)
