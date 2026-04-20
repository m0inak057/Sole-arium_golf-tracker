"""Video processor — slow-motion rendering.

Contains ``render_slowmo_clip()`` and ``get_output_video_path()``.
Full implementation in Sprint 2 (Phase 7).
See architecture.md §4 Phase 7.
"""

from __future__ import annotations

from pathlib import Path


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
        Path to the rendered slow-mo file.

    Raises:
        NotImplementedError: Until Sprint 2 implementation.
    """
    raise NotImplementedError("Phase 7 — Sprint 2")


def get_output_video_path(session_dir: Path, kind: str) -> Path:
    """Return the canonical output path for a video type.

    Args:
        session_dir: The session storage directory.
        kind: ``"slowmo"`` or ``"annotated"``.

    Returns:
        Path to the output file.
    """
    filenames = {"slowmo": "slowmo.mp4", "annotated": "annotated.mp4"}
    return session_dir / filenames[kind]
