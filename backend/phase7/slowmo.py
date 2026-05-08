"""Enhanced slow-mo video rendering — Phase 7 core logic.

Generates slowed down versions of swing videos with enhanced features:
- 0.125× speed (8× frame duplication) for ultra-slow motion
- 90fps output support with frame interpolation
- Adaptive quality settings based on input resolution
- Dual camera angle support for face-on and down-the-line videos

Reference: architecture.md §4 Phase 7, PRD §8 Phase 7 tests.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from backend.core.logging import get_logger

logger = get_logger(__name__)


class SlowmoConfig:
    """Configuration for slow-motion rendering."""

    def __init__(
        self,
        duplication_factor: int = 4,  # 0.25× speed (4× slower)
        target_fps: float | None = None,  # None = use input fps, or specify target
        enable_interpolation: bool = False,  # Frame interpolation for smoother motion
        quality_preset: Literal["low", "medium", "high", "ultra"] = "high",
        enable_90fps: bool = False,  # Enable 90fps output
    ):
        self.duplication_factor = duplication_factor
        self.target_fps = target_fps
        self.enable_interpolation = enable_interpolation
        self.quality_preset = quality_preset
        self.enable_90fps = enable_90fps
    
    def get_codec_settings(self, resolution: tuple[int, int]) -> dict:
        """Get codec settings based on quality preset and resolution."""
        width, height = resolution
        total_pixels = width * height
        
        # Adaptive quality based on resolution
        if total_pixels >= 1920 * 1080:  # 1080p+
            base_quality = "ultra" if self.quality_preset == "ultra" else "high"
        elif total_pixels >= 1280 * 720:  # 720p+
            base_quality = "high" if self.quality_preset in ("high", "ultra") else "medium"
        else:  # Lower resolutions
            base_quality = self.quality_preset
        
        quality_settings = {
            "low": {
                "codecs": [("mp4v", "mp4v"), ("MJPG", "MJPEG")],
                "bitrate_factor": 1.0,
            },
            "medium": {
                "codecs": [("mp4v", "mp4v"), ("H264", "H264"), ("MJPG", "MJPEG")],
                "bitrate_factor": 1.5,
            },
            "high": {
                "codecs": [("H264", "H264"), ("avc1", "avc1"), ("mp4v", "mp4v")],
                "bitrate_factor": 2.0,
            },
            "ultra": {
                "codecs": [("H264", "H264"), ("avc1", "avc1"), ("X264", "X264")],
                "bitrate_factor": 3.0,
            },
        }
        
        return quality_settings.get(base_quality, quality_settings["medium"])


def interpolate_frame(frame1: np.ndarray, frame2: np.ndarray, alpha: float) -> np.ndarray:
    """Interpolate between two frames for smoother slow motion.
    
    Args:
        frame1: First frame.
        frame2: Second frame.
        alpha: Interpolation factor (0.0 = frame1, 1.0 = frame2).
        
    Returns:
        Interpolated frame.
    """
    if frame1.shape != frame2.shape:
        return frame1  # Fallback if frames don't match
    
    # Simple linear interpolation
    interpolated = cv2.addWeighted(frame1, 1 - alpha, frame2, alpha, 0)
    return interpolated


def get_optimal_fps(input_fps: float, config: SlowmoConfig) -> float:
    """Determine optimal output FPS based on configuration.
    
    Args:
        input_fps: Original video FPS.
        config: Slowmo configuration.
        
    Returns:
        Optimal output FPS.
    """
    if config.enable_90fps:
        return 90.0
    elif config.target_fps:
        return config.target_fps
    else:
        return input_fps


def render_slowmo(
    input_video: Path,
    output_video: Path,
    start_frame: int,
    end_frame: int,
    fps: float,
    config: SlowmoConfig | None = None,
) -> bool:
    """Render an enhanced slow-motion MP4 from the input video.

    Frames in [start_frame, end_frame] are processed with enhanced slow-motion:
    - 4× frame duplication (0.25× speed) by default
    - Optional frame interpolation for smoother motion
    - Adaptive quality settings
    - 90fps output support

    Args:
        input_video: Path to the input mp4.
        output_video: Path to write the output slow-mo mp4.
        start_frame: Starting frame index of critical window (inclusive).
        end_frame: Ending frame index of critical window (inclusive).
        fps: Original frame rate of the video.
        config: Slowmo configuration (uses defaults if None).

    Returns:
        True if successful, False otherwise.
    """
    if config is None:
        config = SlowmoConfig()

    if start_frame > end_frame or fps <= 0 or not input_video.exists():
        logger.error(
            f"Invalid params: start={start_frame}, end={end_frame}, fps={fps}, "
            f"input_exists={input_video.exists()}"
        )
        return False

    try:
        cap = cv2.VideoCapture(str(input_video))
        if not cap.isOpened():
            logger.error(f"Could not open input video: {input_video}")
            return False

        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video_fps = cap.get(cv2.CAP_PROP_FPS) or fps

        if frame_width == 0 or frame_height == 0:
            logger.error(f"Invalid frame dimensions: {frame_width}x{frame_height}")
            cap.release()
            return False

        # Determine output FPS
        output_fps = get_optimal_fps(video_fps, config)
        
        logger.info(
            f"Enhanced slowmo rendering: {total_frames} frames, {frame_width}x{frame_height}, "
            f"{video_fps}fps → {output_fps}fps, {config.duplication_factor}x duplication",
            extra={
                "phase": "phase7", 
                "event": "enhanced_video_properties",
                "config": {
                    "duplication_factor": config.duplication_factor,
                    "target_fps": output_fps,
                    "interpolation": config.enable_interpolation,
                    "quality": config.quality_preset,
                }
            },
        )

        # Get codec settings based on quality and resolution
        codec_settings = config.get_codec_settings((frame_width, frame_height))
        
        writer = None
        codec_used = None

        # Try codecs in order of preference
        for fourcc_str, display_name in codec_settings["codecs"]:
            try:
                fourcc = cv2.VideoWriter_fourcc(*fourcc_str) if len(fourcc_str) == 4 else -1
                test_writer = cv2.VideoWriter(
                    str(output_video),
                    fourcc,
                    output_fps,
                    (frame_width, frame_height),
                )
                if test_writer.isOpened():
                    writer = test_writer
                    codec_used = display_name
                    break
                test_writer.release()
            except Exception:
                continue

        if writer is None or not writer.isOpened():
            # Final fallback: use MJPEG
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            writer = cv2.VideoWriter(
                str(output_video),
                fourcc,
                output_fps,
                (frame_width, frame_height),
            )
            codec_used = "MJPEG (fallback)"

        if not writer.isOpened():
            logger.error(f"Could not open video writer for {output_video}")
            cap.release()
            return False

        logger.info(f"Using codec: {codec_used} with quality preset: {config.quality_preset}")

        frame_count = 0
        written_count = 0
        prev_frame = None

        # Process each frame
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            # Determine processing for this frame
            if start_frame <= frame_count <= end_frame:
                # Enhanced slow-motion processing for critical window
                duplication_factor = config.duplication_factor
                
                if config.enable_interpolation and prev_frame is not None:
                    # Generate interpolated frames for smoother motion
                    for i in range(duplication_factor):
                        if i == 0:
                            # Write original frame
                            writer.write(frame)
                        else:
                            # Generate interpolated frame
                            alpha = i / duplication_factor
                            interpolated = interpolate_frame(prev_frame, frame, alpha)
                            writer.write(interpolated)
                        written_count += 1
                else:
                    # Standard duplication without interpolation
                    for _ in range(duplication_factor):
                        writer.write(frame)
                        written_count += 1
            else:
                # Normal speed for non-critical frames
                writer.write(frame)
                written_count += 1

            prev_frame = frame.copy() if config.enable_interpolation else None
            frame_count += 1

        cap.release()
        writer.release()

        if not output_video.exists():
            logger.error(f"Output video was not created: {output_video}")
            return False

        output_size = output_video.stat().st_size
        if output_size < 1000:  # Less than 1KB is suspiciously small
            logger.error(f"Output video suspiciously small: {output_size} bytes")
            return False

        # Verify the output can be read
        verify_cap = cv2.VideoCapture(str(output_video))
        if not verify_cap.isOpened():
            logger.error(f"Failed to verify output video: {output_video}")
            return False

        verify_frames = int(verify_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        verify_fps = verify_cap.get(cv2.CAP_PROP_FPS)
        verify_cap.release()

        logger.info(
            f"Enhanced slowmo rendered successfully: {written_count} frames written, "
            f"{verify_frames} frames in output file at {verify_fps}fps",
            extra={
                "phase": "phase7",
                "event": "enhanced_slowmo_complete",
                "input_frames": total_frames,
                "output_frames": verify_frames,
                "critical_window": f"{start_frame}-{end_frame}",
                "duplication_factor": config.duplication_factor,
                "output_fps": verify_fps,
                "codec": codec_used,
                "quality": config.quality_preset,
            },
        )

        return True

    except Exception as e:
        logger.error(f"Enhanced Phase 7 (slowmo) failed with exception: {e}", exc_info=True)
        return False


async def render_dual_slowmo(
    face_on_video: Path,
    down_the_line_video: Path,
    face_on_output: Path,
    down_the_line_output: Path,
    start_frame: int,
    end_frame: int,
    face_on_fps: float,
    down_the_line_fps: float,
    config: SlowmoConfig | None = None,
) -> tuple[bool, bool]:
    """Render slow-motion videos for both camera angles in parallel.
    
    Args:
        face_on_video: Path to face-on input video.
        down_the_line_video: Path to down-the-line input video.
        face_on_output: Path for face-on slowmo output.
        down_the_line_output: Path for down-the-line slowmo output.
        start_frame: Starting frame index of critical window.
        end_frame: Ending frame index of critical window.
        face_on_fps: FPS of face-on video.
        down_the_line_fps: FPS of down-the-line video.
        config: Slowmo configuration.
        
    Returns:
        Tuple of (face_on_success, down_the_line_success).
    """
    if config is None:
        config = SlowmoConfig()
    
    logger.info(
        f"Starting dual slowmo rendering: face-on ({face_on_fps}fps) + down-the-line ({down_the_line_fps}fps)",
        extra={"phase": "phase7", "event": "dual_slowmo_start"}
    )
    
    # Create tasks for parallel processing
    face_on_task = asyncio.create_task(
        asyncio.to_thread(
            render_slowmo,
            face_on_video,
            face_on_output,
            start_frame,
            end_frame,
            face_on_fps,
            config
        )
    )
    
    down_the_line_task = asyncio.create_task(
        asyncio.to_thread(
            render_slowmo,
            down_the_line_video,
            down_the_line_output,
            start_frame,
            end_frame,
            down_the_line_fps,
            config
        )
    )
    
    # Wait for both tasks to complete
    face_on_success, down_the_line_success = await asyncio.gather(
        face_on_task, down_the_line_task, return_exceptions=True
    )
    
    # Handle exceptions
    if isinstance(face_on_success, Exception):
        logger.error(f"Face-on slowmo failed: {face_on_success}")
        face_on_success = False
    
    if isinstance(down_the_line_success, Exception):
        logger.error(f"Down-the-line slowmo failed: {down_the_line_success}")
        down_the_line_success = False
    
    logger.info(
        f"Dual slowmo rendering complete: face-on={face_on_success}, down-the-line={down_the_line_success}",
        extra={
            "phase": "phase7", 
            "event": "dual_slowmo_complete",
            "face_on_success": face_on_success,
            "down_the_line_success": down_the_line_success,
        }
    )
    
    return face_on_success, down_the_line_success
