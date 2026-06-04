"""Pydantic request / response models for the HTTP API.

Mirrors ``api-contract.md`` exactly.  All response shapes use these DTOs
so the contract stays in one place.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.core.session import SwingWindow


# ─── Session ─────────────────────────────────────────────────────────────────


class SessionCreateResponse(BaseModel):
    """Response for ``POST /api/session`` — api-contract.md §1."""

    session_id: str
    status: str
    created_at: str


class SessionStatusResponse(BaseModel):
    """Response for ``GET /api/session/{session_id}/status``."""

    session_id: str
    status: str
    progress_pct: int
    status_reason: str | None = None
    failed: bool = False
    total_swing_attempts: int | None = None
    all_swing_attempts: list[SwingWindow] | None = None


# ─── Error ───────────────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    """Inner error detail."""

    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error envelope — api-contract.md §4."""

    error: ErrorDetail


# ─── Phase-specific convenience responses ────────────────────────────────────


class Phase1DetectionResponse(BaseModel):
    """Response for ``GET /api/phase1/detection/{session_id}``."""

    total_swing_attempts: int | None = None
    selected_swing_index: int | None = None
    hit_confidence_score: float | None = None
    backswing_start_frame_index: int | None = None
    impact_frame_index: int | None = None
    follow_through_end_frame_index: int | None = None


class OutputStatusResponse(BaseModel):
    """Response for ``GET /api/output/{session_id}/{kind}/status``."""

    ready: bool
    path: str | None = None


class VideoMetadataResponse(BaseModel):
    """Response for ``GET /api/output/{session_id}/metadata``."""

    duration_seconds: float | None = None
    fps: float | None = None
    width: int | None = None
    height: int | None = None
    file_size_bytes: int | None = None
    format: str | None = None


class DualVideoStatusResponse(BaseModel):
    """Response for dual video status endpoints."""

    face_on: OutputStatusResponse
    down_the_line: OutputStatusResponse


class DualVideoSessionCreateResponse(BaseModel):
    """Response for dual video session creation."""
    
    session_id: str
    status: str
    created_at: str
    dual_video_mode: bool = True
    face_on_uploaded: bool = False
    down_the_line_uploaded: bool = False


# ─── Dual Video Support Models ───────────────────────────────────────────────


class AngleVideoStatus(BaseModel):
    """Status for a specific camera angle video."""
    
    ready: bool
    path: str | None = None
    file_size_bytes: int | None = None
    duration_seconds: float | None = None


class DualVideoOutputStatus(BaseModel):
    """Complete output status for dual video session."""
    
    session_id: str
    dual_video_mode: bool
    slowmo: dict[str, AngleVideoStatus] = Field(
        default_factory=lambda: {
            "face_on": AngleVideoStatus(ready=False),
            "down_the_line": AngleVideoStatus(ready=False),
        }
    )
    annotated: dict[str, AngleVideoStatus] = Field(
        default_factory=lambda: {
            "face_on": AngleVideoStatus(ready=False),
            "down_the_line": AngleVideoStatus(ready=False),
        }
    )
    metadata_available: bool = False
    metadata_path: str | None = None


class DualVideoMetadataResponse(BaseModel):
    """Metadata for dual video outputs."""
    
    face_on: VideoMetadataResponse | None = None
    down_the_line: VideoMetadataResponse | None = None
    combined_duration_seconds: float | None = None


class DualVideoSessionStatusResponse(BaseModel):
    """Comprehensive status response for dual video sessions."""
    
    session_id: str
    status: str
    progress_pct: int
    dual_video_mode: bool = True
    
    # Processing status for each angle
    face_on_processing_complete: bool = False
    down_the_line_processing_complete: bool = False
    
    # Output availability
    slowmo_face_on_ready: bool = False
    slowmo_down_the_line_ready: bool = False
    annotated_face_on_ready: bool = False
    annotated_down_the_line_ready: bool = False
    
    # Paths
    slowmo_face_on_path: str | None = None
    slowmo_down_the_line_path: str | None = None
    annotated_face_on_path: str | None = None
    annotated_down_the_line_path: str | None = None
    
    # Error info
    status_reason: str | None = None
    failed: bool = False
    overlay_rendering_failed: bool = False
    total_swing_attempts: int | None = None
    all_swing_attempts: list[SwingWindow] | None = None


class VideoStreamingResponse(BaseModel):
    """Response metadata for video streaming endpoints."""
    
    session_id: str
    video_type: str  # "slowmo" or "annotated"
    camera_angle: str  # "face_on" or "down_the_line"
    streaming_url: str
    download_url: str
    metadata: VideoMetadataResponse | None = None


class DualVideoDownloadResponse(BaseModel):
    """Response for dual video download request."""
    
    session_id: str
    face_on_download_url: str | None = None
    down_the_line_download_url: str | None = None
    combined_zip_url: str | None = None


class ProcessingProgressResponse(BaseModel):
    """Detailed processing progress for frontend display."""
    
    session_id: str
    overall_progress_pct: int
    current_phase: str
    current_phase_progress_pct: int
    
    # Phase-specific progress
    phases: dict[str, dict[str, object]] = Field(
        default_factory=dict,
        description="Progress for each phase"
    )
    
    # Dual video specific
    dual_video_mode: bool = False
    face_on_progress_pct: int | None = None
    down_the_line_progress_pct: int | None = None
    
    # Timing info
    elapsed_seconds: float | None = None
    estimated_remaining_seconds: float | None = None
    
    # Status
    status: str
    failed: bool = False
    error_message: str | None = None
