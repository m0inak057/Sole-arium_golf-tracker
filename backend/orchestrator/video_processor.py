"""Video processor — slow-motion rendering and output path management.

Contains ``render_slowmo_clip()`` and ``get_output_video_path()``.
Full implementation in Sprint 2 (Phase 7).
See architecture.md §4 Phase 7.
"""

from __future__ import annotations

from pathlib import Path

from backend.phase7.slowmo import render_slowmo
from backend.core.logging import get_logger

logger = get_logger(__name__)


def render_slowmo_clip(
    input_path: Path,
    output_path: Path,
    backswing_start: int,
    follow_through_end: int,
    original_fps: float,
) -> Path:
    """Render a slow-motion MP4 from the input video.

    Frames in ``[backswing_start, follow_through_end]`` are each written 4×
    (0.25× speed).  Other frames are written once.

    Args:
        input_path: Path to the source video.
        output_path: Where to write the slow-mo MP4.
        backswing_start: Frame index where the critical window begins.
        follow_through_end: Frame index where the critical window ends.
        original_fps: FPS of the source video.

    Returns:
        Path to the rendered slow-mo file if successful, raises ValueError otherwise.

    Raises:
        ValueError: If rendering fails.
    """
    success = render_slowmo(
        input_path,
        output_path,
        backswing_start,
        follow_through_end,
        original_fps,
    )

    if not success:
        raise ValueError(
            f"Failed to render slowmo from {input_path} to {output_path} "
            f"(frames {backswing_start}-{follow_through_end} at {original_fps} fps)"
        )

    if not output_path.exists():
        raise ValueError(f"Output video not created: {output_path}")

    return output_path


def get_output_video_path(session_dir: Path, kind: str) -> Path:
    """Return the canonical output path for a video type.

    Args:
        session_dir: The session storage directory.
        kind: ``"slowmo"`` or ``"annotated"``.

    Returns:
        Path to the output file.

    Raises:
        ValueError: If kind is not recognized.
    """
    filenames = {"slowmo": "slowmo.mp4", "annotated": "annotated.mp4"}
    if kind not in filenames:
        raise ValueError(f"Unknown video kind: {kind}. Must be 'slowmo' or 'annotated'.")
    
    return session_dir / filenames[kind]
