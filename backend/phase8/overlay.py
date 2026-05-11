"""Enhanced annotated video overlay — Phase 8 core logic.

Renders MediaPipe skeleton overlays with angle metrics onto slowmo videos.
Supports both single and dual camera angle processing with angle-appropriate overlays.

Enhanced features:
- Dual camera angle support with parallel processing
- Angle-specific overlay rendering and styling
- Consistent HUD and annotation styling across outputs
- Optimized keypoint processing for different camera perspectives

Integration points:
  - Input: slowmo videos (Phase 7) and keypoints Parquet (Phase 2)
  - Output: annotated video paths written to session JSON
  - Metrics: From Phase 4 (13 metrics)
  - Thresholds: From Agent 4 (active_thresholds)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pyarrow.parquet as pq

from backend.core.logging import get_logger
from backend.orchestrator.overlay_renderer import (
    draw_skeleton,
    draw_joint_dots,
    draw_angle_overlay_xfactor,
    draw_angle_overlay_spine,
    draw_angle_overlay_wrist_lag,
    draw_angle_overlay_knee,
    draw_angle_overlay_stance,
    draw_bottom_hud,
    draw_phase_label,
)

logger = get_logger(__name__)


class OverlayConfig:
    """Configuration for overlay rendering."""
    
    def __init__(
        self,
        show_skeleton: bool = True,
        show_joint_dots: bool = True,
        show_angle_overlays: bool = True,
        show_hud: bool = True,
        show_phase_label: bool = True,
        hud_position: str = "bottom",  # "bottom", "top", "left", "right"
        overlay_opacity: float = 0.8,
        angle_specific_styling: bool = True,
    ):
        self.show_skeleton = show_skeleton
        self.show_joint_dots = show_joint_dots
        self.show_angle_overlays = show_angle_overlays
        self.show_hud = show_hud
        self.show_phase_label = show_phase_label
        self.hud_position = hud_position
        self.overlay_opacity = overlay_opacity
        self.angle_specific_styling = angle_specific_styling


def get_angle_specific_overlays(camera_angle: str, metrics: dict, thresholds: dict) -> dict:
    """Get angle-appropriate overlays based on camera perspective.
    
    Args:
        camera_angle: "face_on" or "down_the_line"
        metrics: Session metrics dictionary
        thresholds: Active thresholds dictionary
        
    Returns:
        Dictionary of overlay values optimized for the camera angle.
    """
    overlays = {}
    
    if camera_angle == "face_on":
        # Face-on view: emphasize frontal plane metrics
        overlays.update({
            "x_factor": _extract_metric_value(metrics, "x_factor"),
            "spine_deviation": _extract_metric_value(metrics, "spine_deviation_max"),
            "stance_width": _extract_metric_value(metrics, "stance_width"),
            "knee_flex": _extract_metric_value(metrics, "knee_flex_right"),
        })
    elif camera_angle == "down_the_line":
        # Down-the-line view: emphasize sagittal plane metrics
        overlays.update({
            "wrist_lag": _extract_metric_value(metrics, "wrist_lag"),
            "spine_angle": _extract_metric_value(metrics, "spine_angle_at_impact"),
            "hip_rotation": _extract_metric_value(metrics, "hip_rotation_max"),
            "shoulder_rotation": _extract_metric_value(metrics, "shoulder_rotation_max"),
        })
    else:
        # Default: show all available metrics
        overlays.update({
            "x_factor": _extract_metric_value(metrics, "x_factor"),
            "spine_deviation": _extract_metric_value(metrics, "spine_deviation_max"),
            "wrist_lag": _extract_metric_value(metrics, "wrist_lag"),
            "knee_flex": _extract_metric_value(metrics, "knee_flex_right"),
            "stance_width": _extract_metric_value(metrics, "stance_width"),
        })
    
    return overlays


def _extract_metric_value(metrics: dict, metric_name: str) -> float | None:
    """Extract metric value from metrics dictionary."""
    if not isinstance(metrics, dict):
        return None
    
    metric_obj = metrics.get(metric_name)
    if metric_obj is None:
        return None
    
    # Handle different metric object formats
    if hasattr(metric_obj, "value"):
        # Pydantic model or object with value attribute
        return metric_obj.value
    elif isinstance(metric_obj, dict):
        # Dictionary format
        return metric_obj.get("value")
    else:
        # Direct value
        return metric_obj if isinstance(metric_obj, (int, float)) else None


def render_overlay(
    input_video: Path,
    output_video: Path,
    keypoints_parquet: Path,
    session_json: Any,
    start_frame: int,
    end_frame: int,
    camera_angle: str = "face_on",
    config: OverlayConfig | None = None,
) -> bool:
    """Render annotated overlay on video with skeleton, metrics, and HUD.

    Enhanced rendering with angle-specific optimizations:
      1. Draw skeleton (limb lines) - angle-optimized
      2. Draw joint dots (circles) - visibility-based
      3. Draw angle overlays - camera-appropriate metrics
      4. Draw HUD panel - angle-specific layout
      5. Draw phase label - camera angle indicator

    Args:
        input_video: Path to input MP4 (slowmo video).
        output_video: Path to write annotated.mp4.
        keypoints_parquet: Path to Phase 2 keypoints Parquet.
        session_json: Session object with metrics and thresholds.
        start_frame: Start frame index.
        end_frame: End frame index.
        camera_angle: Camera angle ("face_on" or "down_the_line").
        config: Overlay configuration (uses defaults if None).

    Returns:
        True if successfully rendered and output file exists.
    """
    if config is None:
        config = OverlayConfig()

    # Log the input video being processed to verify it's the slowmo video
    logger.info(f"[render_overlay] Processing {camera_angle} overlay")
    logger.info(f"  Input video: {input_video}")
    logger.info(f"  Input exists: {input_video.exists()}")
    logger.info(f"  Input is slowmo: {'slowmo' in str(input_video)}")
    if input_video.exists():
        input_size = input_video.stat().st_size
        logger.info(f"  Input size: {input_size / 1_000_000:.1f}MB")
    logger.info(f"  Output path: {output_video}")

    if not input_video.exists() or not keypoints_parquet.exists():
        logger.error(f"Input files missing: video={input_video.exists()}, parquet={keypoints_parquet.exists()}")
        return False

    try:
        table = pq.read_table(str(keypoints_parquet))
        df = table.to_pandas()
    except Exception as e:
        logger.error(f"Failed to read keypoints parquet: {e}")
        return False

    if df.empty:
        logger.error("Keypoints parquet is empty")
        return False

    # Open video and get properties
    cap = cv2.VideoCapture(str(input_video))
    if not cap.isOpened():
        logger.error(f"Failed to open video: {input_video}")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Get total frame count from the input video (entire video, not just critical window)
    actual_total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # The start_frame and end_frame are for the critical window (where overlays should be applied)
    # But we need to render the ENTIRE video
    critical_window_frames = end_frame - start_frame + 1

    logger.info(
        f"Rendering {camera_angle} overlay: {actual_total_frames} total frames, critical window {start_frame}-{end_frame} ({critical_window_frames} frames), {width}x{height}, {fps}fps",
        extra={
            "phase": "phase8",
            "event": "overlay_start",
            "camera_angle": camera_angle,
            "critical_window_frames": critical_window_frames,
            "total_frames": actual_total_frames,
            "config": {
                "skeleton": config.show_skeleton,
                "overlays": config.show_angle_overlays,
                "hud": config.show_hud,
            }
        }
    )

    # Try codecs in fallback order with quality preference
    codecs = ['H264', 'avc1', 'mp4v', 'X264', 'MJPG']
    out = None

    for codec in codecs:
        try:
            fourcc = cv2.VideoWriter_fourcc(*codec)  # type: ignore
            out = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))
            if out.isOpened():
                logger.info(f"Opened VideoWriter with codec {codec} for {camera_angle}")
                break
        except Exception as e:
            logger.warning(f"Codec {codec} failed for {camera_angle}: {e}")
            continue

    if out is None or not out.isOpened():
        logger.error(f"Failed to open VideoWriter with any codec for {camera_angle}")
        cap.release()
        return False

    # Extract metrics and thresholds
    metrics = getattr(session_json, "metrics", {})
    thresholds = getattr(session_json, "active_thresholds", {})
    
    # Get angle-specific overlays
    angle_overlays = get_angle_specific_overlays(camera_angle, metrics, thresholds)

    # Seek to first frame (start of entire video, not critical window)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    current_frame = 0
    frame_count = 0

    # Main rendering loop - process ENTIRE video
    while current_frame < actual_total_frames:
        ret, frame = cap.read()
        if not ret or frame is None:
            logger.warning(f"Failed to read frame {current_frame} for {camera_angle}")
            break

        # Only apply overlays if we're in the critical window
        if start_frame <= current_frame <= end_frame:
            # Get keypoints for this frame from parquet
            frame_kpts = df[df["frame_index"] == current_frame]

            if not frame_kpts.empty:
                # Build keypoint dict: {landmark_id: (x_px, y_px, visibility)}
                keypoints_dict: dict[int, tuple[float, float, float]] = {}

                for _, row in frame_kpts.iterrows():
                    landmark_id = int(row["landmark_id"])
                    # Convert normalized coords to pixels
                    x_px = float(row["x"]) * width
                    y_px = float(row["y"]) * height
                    visibility = float(row["visibility"])

                    keypoints_dict[landmark_id] = (x_px, y_px, visibility)

                # ─── ENHANCED RENDERING ORDER (back to front) ────────────────────

                # 1. Skeleton limb lines (if enabled)
                if config.show_skeleton:
                    frame = draw_skeleton(frame, keypoints_dict)

                # 2. Joint dots (if enabled)
                if config.show_joint_dots:
                    frame = draw_joint_dots(frame, keypoints_dict)

                # 3. Angle-specific overlays (if enabled)
                if config.show_angle_overlays:
                    # Draw overlays based on camera angle optimization
                    if camera_angle == "face_on":
                        # Face-on specific overlays
                        frame = draw_angle_overlay_xfactor(frame, keypoints_dict, angle_overlays.get("x_factor"), thresholds)
                        frame = draw_angle_overlay_spine(frame, keypoints_dict, angle_overlays.get("spine_deviation"), thresholds)
                        frame = draw_angle_overlay_stance(frame, keypoints_dict, angle_overlays.get("stance_width"), thresholds)
                        frame = draw_angle_overlay_knee(frame, keypoints_dict, angle_overlays.get("knee_flex"), thresholds)
                    elif camera_angle == "down_the_line":
                        # Down-the-line specific overlays
                        frame = draw_angle_overlay_wrist_lag(frame, keypoints_dict, angle_overlays.get("wrist_lag"), thresholds)
                        # Additional DTL-specific overlays can be added here
                    else:
                        # Default: show all overlays
                        frame = draw_angle_overlay_xfactor(frame, keypoints_dict, angle_overlays.get("x_factor"), thresholds)
                        frame = draw_angle_overlay_spine(frame, keypoints_dict, angle_overlays.get("spine_deviation"), thresholds)
                        frame = draw_angle_overlay_wrist_lag(frame, keypoints_dict, angle_overlays.get("wrist_lag"), thresholds)
                        frame = draw_angle_overlay_knee(frame, keypoints_dict, angle_overlays.get("knee_flex"), thresholds)
                        frame = draw_angle_overlay_stance(frame, keypoints_dict, angle_overlays.get("stance_width"), thresholds)

            # 4. HUD panel (if enabled, only in critical window)
            if config.show_hud:
                frame = draw_bottom_hud(frame, session_json, current_frame, end_frame)

            # 5. Phase label with camera angle (if enabled, only in critical window)
            if config.show_phase_label:
                label_text = f"Phase 8: {camera_angle.replace('_', '-').title()} Overlay"
                frame = draw_phase_label(frame, label_text, camera_angle)

        # Write frame to output
        out.write(frame)
        current_frame += 1
        frame_count += 1

    # Cleanup
    cap.release()
    out.release()

    # Verify output
    if not output_video.exists():
        logger.error(f"Output file not created: {output_video}")
        return False

    # Try to open output to verify it's readable
    try:
        verify_cap = cv2.VideoCapture(str(output_video))
        if not verify_cap.isOpened():
            logger.error(f"Output file not readable: {output_video}")
            return False
        verify_cap.release()
    except Exception as e:
        logger.error(f"Failed to verify output: {e}")
        return False

    output_size = output_video.stat().st_size
    logger.info(
        f"Rendered {frame_count} frames to {output_video} ({output_size / 1_000_000:.1f}MB)",
        extra={
            "phase": "phase8",
            "event": "overlay_complete",
            "camera_angle": camera_angle,
            "frames": frame_count,
            "size_mb": output_size / 1_000_000,
        }
    )
    return True


async def render_dual_overlay(
    face_on_slowmo: Path,
    down_the_line_slowmo: Path,
    face_on_output: Path,
    down_the_line_output: Path,
    keypoints_parquet: Path,
    session_json: Any,
    start_frame: int,
    end_frame: int,
    config: OverlayConfig | None = None,
) -> tuple[bool, bool]:
    """Render annotated overlays for both camera angles in parallel.
    
    Args:
        face_on_slowmo: Path to face-on slowmo video.
        down_the_line_slowmo: Path to down-the-line slowmo video.
        face_on_output: Path for face-on annotated output.
        down_the_line_output: Path for down-the-line annotated output.
        keypoints_parquet: Path to keypoints data.
        session_json: Session object with metrics and thresholds.
        start_frame: Start frame index.
        end_frame: End frame index.
        config: Overlay configuration.
        
    Returns:
        Tuple of (face_on_success, down_the_line_success).
    """
    if config is None:
        config = OverlayConfig()
    
    logger.info(
        f"Starting dual overlay rendering: face-on + down-the-line",
        extra={"phase": "phase8", "event": "dual_overlay_start"}
    )
    
    # Create tasks for parallel processing
    face_on_task = asyncio.create_task(
        asyncio.to_thread(
            render_overlay,
            face_on_slowmo,
            face_on_output,
            keypoints_parquet,
            session_json,
            start_frame,
            end_frame,
            "face_on",
            config
        )
    )
    
    down_the_line_task = asyncio.create_task(
        asyncio.to_thread(
            render_overlay,
            down_the_line_slowmo,
            down_the_line_output,
            keypoints_parquet,
            session_json,
            start_frame,
            end_frame,
            "down_the_line",
            config
        )
    )
    
    # Wait for both tasks to complete
    face_on_success, down_the_line_success = await asyncio.gather(
        face_on_task, down_the_line_task, return_exceptions=True
    )
    
    # Handle exceptions
    if isinstance(face_on_success, Exception):
        logger.error(f"Face-on overlay failed: {face_on_success}")
        face_on_success = False
    
    if isinstance(down_the_line_success, Exception):
        logger.error(f"Down-the-line overlay failed: {down_the_line_success}")
        down_the_line_success = False
    
    logger.info(
        f"Dual overlay rendering complete: face-on={face_on_success}, down-the-line={down_the_line_success}",
        extra={
            "phase": "phase8", 
            "event": "dual_overlay_complete",
            "face_on_success": face_on_success,
            "down_the_line_success": down_the_line_success,
        }
    )
    
    return face_on_success, down_the_line_success
