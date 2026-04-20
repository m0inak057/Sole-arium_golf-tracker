"""Slow-mo video rendering — Phase 7 core logic.

Generates a slowed down snippet of the real swing impact window.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from backend.core.logging import get_logger

logger = get_logger(__name__)


def render_slowmo(
    input_video: Path,
    output_video: Path,
    start_frame: int,
    end_frame: int,
    fps: float,
) -> bool:
    """Extract and slow down the swing impact portion of the video using FFmpeg.

    Args:
        input_video: Path to the input mp4.
        output_video: Path to write the output slow-mo mp4.
        start_frame: Starting frame index.
        end_frame: Ending frame index.
        fps: Original frame rate.

    Returns:
        True if successful.
    """
    if start_frame >= end_frame or fps <= 0:
        return False

    # Extract snippet and slow down by roughly 2x
    # filter: setpts=2.0*PTS
    
    start_time = max(0.0, start_frame / fps)
    duration = (end_frame - start_frame) / fps

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", str(input_video),
        "-filter:v", "setpts=2.0*PTS",
        "-r", str(fps),  # keep same fps output, just stretched frames
        "-an",  # remove audio
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        str(output_video)
    ]
    
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return output_video.exists()
    except Exception as e:
        logger.error(f"FFmpeg slowmo render failed: {e}")
        return False
