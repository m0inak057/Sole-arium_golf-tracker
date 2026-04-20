"""Pydantic request / response models for the HTTP API.

Mirrors ``api-contract.md`` exactly.  All response shapes use these DTOs
so the contract stays in one place.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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
