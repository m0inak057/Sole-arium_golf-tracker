"""Enhanced slow-mo video rendering — Phase 7 core logic.

Generates slowed down versions of swing videos with enhanced features:
- 0.125× speed (8× frame duplication) for ultra-slow motion
- 90fps output support with frame interpolation
- Adaptive quality settings based on input resolution
- Dual camera angle support for face-on and down-the-line videos
- Resolution scaling support (portrait → landscape)
- H.264 compression with CRF settings for efficient encoding

Reference: architecture.md §4 Phase 7, PRD §8 Phase 7 tests.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from backend.core.compression import QualityLevel
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
        target_resolution: tuple[int, int] | None = None,  # Target output resolution (width, height)
        crf_quality: int | None = None,  # H.264 CRF value (0-51, lower=better). None=auto
        use_ffmpeg: bool = True,  # Use FFmpeg for encoding (better compression)
    ):
        self.duplication_factor = duplication_factor
        self.target_fps = target_fps
        self.enable_interpolation = enable_interpolation
        self.quality_preset = quality_preset
        self.enable_90fps = enable_90fps
        self.target_resolution = target_resolution
        self.crf_quality = crf_quality if crf_quality is not None else 23  # Default CRF 23 (good quality/compression)
        self.use_ffmpeg = use_ffmpeg
    
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


def calculate_landscape_resolution(
    original_width: int,
    original_height: int,
    target_width: int = 528,
    target_height: int = 480,
) -> tuple[int, int]:
    """Calculate landscape resolution, scaling from portrait if needed.

    If input is portrait (height > width), scale to landscape target.
    If input is already landscape, use it.

    Args:
        original_width: Original video width
        original_height: Original video height
        target_width: Target landscape width (default 528)
        target_height: Target landscape height (default 480)

    Returns:
        Tuple of (output_width, output_height)
    """
    is_portrait = original_height > original_width

    if is_portrait:
        # Scale portrait to landscape target
        return (target_width, target_height)
    else:
        # Already landscape or square - maintain or scale to target
        aspect = original_width / original_height if original_height > 0 else 1.0

        # Scale height to target, calculate width from aspect
        scaled_height = target_height
        scaled_width = int(scaled_height * aspect)

        # Ensure even dimensions for codec compatibility
        scaled_width = (scaled_width // 2) * 2
        scaled_height = (scaled_height // 2) * 2

        return (scaled_width, scaled_height)


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
    - Resolution scaling (portrait to landscape)
    - H.264 compression with CRF settings
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

        # Determine output resolution
        if config.target_resolution:
            output_width, output_height = config.target_resolution
        else:
            # Auto-detect landscape resolution
            output_width, output_height = calculate_landscape_resolution(
                frame_width, frame_height
            )

        # Determine output FPS
        output_fps = get_optimal_fps(video_fps, config)

        logger.info(
            f"Enhanced slowmo rendering: {total_frames} frames, {frame_width}x{frame_height} → "
            f"{output_width}x{output_height}, {video_fps}fps → {output_fps}fps, "
            f"{config.duplication_factor}x duplication, CRF={config.crf_quality}",
            extra={
                "phase": "phase7",
                "event": "slowmo_rendering_start",
                "input_resolution": f"{frame_width}x{frame_height}",
                "output_resolution": f"{output_width}x{output_height}",
                "input_fps": video_fps,
                "output_fps": output_fps,
                "duplication_factor": config.duplication_factor,
                "crf": config.crf_quality,
            },
        )

        frame_count = 0
        written_count = 0
        prev_frame = None
        frames_list = []

        # Read and process all frames in memory first
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            # Scale frame to output resolution if different
            if frame.shape[1] != output_width or frame.shape[0] != output_height:
                frame = cv2.resize(frame, (output_width, output_height), interpolation=cv2.INTER_LANCZOS4)

            # Determine processing for this frame
            if start_frame <= frame_count <= end_frame:
                # Enhanced slow-motion processing for critical window
                if config.enable_interpolation and prev_frame is not None:
                    # Add interpolated frames
                    for i in range(config.duplication_factor):
                        if i == 0:
                            frames_list.append(frame.copy())
                        else:
                            alpha = i / config.duplication_factor
                            interpolated = interpolate_frame(prev_frame, frame, alpha)
                            frames_list.append(interpolated)
                        written_count += 1
                else:
                    # Standard duplication
                    for _ in range(config.duplication_factor):
                        frames_list.append(frame.copy())
                        written_count += 1
            else:
                # Normal speed for non-critical frames
                frames_list.append(frame)
                written_count += 1

            prev_frame = frame.copy() if config.enable_interpolation else None
            frame_count += 1

        cap.release()

        # Write frames using FFmpeg for better compression
        if config.use_ffmpeg:
            success = _write_video_ffmpeg(
                frames_list,
                output_video,
                output_fps,
                output_width,
                output_height,
                config.crf_quality,
            )
        else:
            # Fallback to cv2.VideoWriter
            success = _write_video_opencv(
                frames_list,
                output_video,
                output_fps,
                output_width,
                output_height,
            )

        if not success:
            return False

        if not output_video.exists():
            logger.error(f"Output video was not created: {output_video}")
            return False

        output_size = output_video.stat().st_size
        if output_size < 1000:
            logger.error(f"Output video suspiciously small: {output_size} bytes")
            return False

        # Verify the output can be read
        verify_cap = cv2.VideoCapture(str(output_video))
        if not verify_cap.isOpened():
            logger.error(f"Failed to verify output video: {output_video}")
            return False

        verify_frames = int(verify_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        verify_fps = verify_cap.get(cv2.CAP_PROP_FPS)
        verify_size_mb = output_size / (1024 * 1024)
        verify_cap.release()

        logger.info(
            f"Enhanced slowmo rendered successfully: {written_count} frames written, "
            f"{verify_frames} frames in output, {verify_fps}fps, {verify_size_mb:.1f}MB, "
            f"CRF={config.crf_quality}",
            extra={
                "phase": "phase7",
                "event": "slowmo_complete",
                "input_frames": total_frames,
                "output_frames": verify_frames,
                "critical_window": f"{start_frame}-{end_frame}",
                "duplication_factor": config.duplication_factor,
                "output_fps": verify_fps,
                "output_size_mb": verify_size_mb,
                "crf": config.crf_quality,
            },
        )

        return True

    except Exception as e:
        logger.error(f"Enhanced Phase 7 (slowmo) failed with exception: {e}", exc_info=True)
        return False


def _write_video_ffmpeg(
    frames: list[np.ndarray],
    output_path: Path,
    fps: float,
    width: int,
    height: int,
    crf: int = 23,
) -> bool:
    """Write frames to MP4 using FFmpeg with H.264 compression.

    Args:
        frames: List of numpy arrays (BGR frames)
        output_path: Output file path
        fps: Output frame rate
        width: Output width
        height: Output height
        crf: H.264 CRF value (0-51, lower=better quality, default 23)

    Returns:
        True if successful, False otherwise
    """
    if not frames:
        logger.error("No frames to write")
        return False

    try:
        # FFmpeg command for H.264 with CRF
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "bgr24",
            "-r", str(fps),
            "-i", "-",  # Read from stdin
            "-c:v", "libx264",
            "-preset", "medium",  # Balance speed and compression
            "-crf", str(crf),  # Quality: 0-51 (lower is better)
            "-movflags", "+faststart",  # Enable streaming/seeking
            str(output_path),
        ]

        # Start FFmpeg process
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )

        # Write frames to FFmpeg stdin
        frame_bytes_written = 0
        for i, frame in enumerate(frames):
            try:
                process.stdin.write(frame.tobytes())
                frame_bytes_written += 1
            except BrokenPipeError:
                logger.error(f"FFmpeg process closed unexpectedly at frame {i}")
                process.terminate()
                return False

        # Close stdin to signal end of input
        process.stdin.close()

        # Wait for FFmpeg to complete
        stdout, stderr = process.communicate(timeout=300)  # 5-minute timeout

        if process.returncode != 0:
            stderr_str = stderr.decode("utf-8", errors="ignore") if stderr else "unknown error"
            logger.error(
                f"FFmpeg encoding failed (return code {process.returncode}): {stderr_str[:500]}"
            )
            return False

        logger.info(
            f"FFmpeg encoded {frame_bytes_written} frames to {output_path} "
            f"with CRF={crf}",
            extra={
                "phase": "phase7",
                "event": "ffmpeg_encoding_complete",
                "frames_encoded": frame_bytes_written,
                "crf": crf,
            },
        )

        return True

    except subprocess.TimeoutExpired:
        logger.error("FFmpeg process timeout (>300s)")
        process.kill()
        return False
    except FileNotFoundError:
        logger.error("FFmpeg not found. Falling back to OpenCV encoding.")
        return False
    except Exception as e:
        logger.error(f"FFmpeg encoding error: {e}", exc_info=True)
        return False


def _write_video_opencv(
    frames: list[np.ndarray],
    output_path: Path,
    fps: float,
    width: int,
    height: int,
) -> bool:
    """Write frames to MP4 using OpenCV VideoWriter (fallback).

    Args:
        frames: List of numpy arrays (BGR frames)
        output_path: Output file path
        fps: Output frame rate
        width: Output width
        height: Output height

    Returns:
        True if successful, False otherwise
    """
    if not frames:
        logger.error("No frames to write")
        return False

    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(output_path),
            fourcc,
            fps,
            (width, height),
        )

        if not writer.isOpened():
            logger.error("Could not open OpenCV VideoWriter")
            return False

        for frame in frames:
            writer.write(frame)

        writer.release()
        logger.info(
            f"OpenCV encoded {len(frames)} frames to {output_path}",
            extra={"phase": "phase7", "event": "opencv_encoding_complete"},
        )

        return True

    except Exception as e:
        logger.error(f"OpenCV encoding error: {e}", exc_info=True)
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
