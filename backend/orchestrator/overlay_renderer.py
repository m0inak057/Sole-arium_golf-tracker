"""Overlay renderer — annotated video rendering.

All overlay logic lives here.  No drawing code lives anywhere else.
Full implementation in Sprint 3 (Phase 8).
See architecture.md §4 Phase 8 and project-structure.md §overlay.

Rendering order is STRICT (from back to front):
  1. Skeleton limb lines
  2. Joint dots (circles)
  3. Angle overlays
  4. HUD panel (always last, always on top)
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


# ─── MediaPipe 33-Landmark Skeleton Connections ──────────────────────────────
# These are the standard limb connections for MediaPipe Pose
SKELETON_CONNECTIONS = [
    # Face & torso
    (0, 1), (1, 2), (2, 3), (3, 7),  # Face outline
    # Left arm
    (11, 13), (13, 15),  # shoulder → elbow → wrist
    # Right arm
    (12, 14), (14, 16),  # shoulder → elbow → wrist
    # Torso
    (11, 12),  # shoulders
    (11, 23), (12, 24),  # shoulders → hips
    # Hips
    (23, 24),  # left hip → right hip
    # Left leg
    (23, 25), (25, 27),  # hip → knee → ankle
    # Right leg
    (24, 26), (26, 28),  # hip → knee → ankle
]

# Key landmark indices for angle measurement
LANDMARK_NAMES = {
    0: "nose", 1: "left_eye", 2: "right_eye", 3: "left_ear", 4: "right_ear",
    5: "left_shoulder", 6: "right_shoulder", 11: "left_shoulder", 12: "right_shoulder",
    13: "left_elbow", 14: "right_elbow", 15: "left_wrist", 16: "right_wrist",
    23: "left_hip", 24: "right_hip", 25: "left_knee", 26: "right_knee",
    27: "left_ankle", 28: "right_ankle",
}


# ─── Helper Functions ────────────────────────────────────────────────────────


def _get_color_for_threshold(value: float, green_range: tuple[float, float] | None, 
                             amber_range: tuple[float, float] | None) -> tuple[int, int, int]:
    """Get BGR color (green/amber/red) based on value against thresholds.
    
    Args:
        value: The measured value.
        green_range: (min, max) for green zone, or None.
        amber_range: (min, max) for amber zone, or None.
        
    Returns:
        BGR tuple (blue, green, red).
    """
    # Green (0, 255, 0)
    if green_range and green_range[0] <= value <= green_range[1]:
        return (0, 255, 0)
    
    # Amber (0, 165, 255)
    if amber_range and amber_range[0] <= value <= amber_range[1]:
        return (0, 165, 255)
    
    # Red (0, 0, 255)
    return (0, 0, 255)


def _draw_arc_degrees(frame: np.ndarray, center: tuple[int, int], radius: int, 
                      start_angle: float, end_angle: float, color: tuple[int, int, int],
                      thickness: int = 2) -> np.ndarray:
    """Draw an arc on the frame (approximated using polylines).
    
    Args:
        frame: BGR image array.
        center: (x, y) center of arc.
        radius: Radius in pixels.
        start_angle: Start angle in degrees.
        end_angle: End angle in degrees.
        color: BGR color tuple.
        thickness: Line thickness.
        
    Returns:
        Frame with arc drawn.
    """
    # Generate points along the arc
    angles = np.linspace(np.radians(start_angle), np.radians(end_angle), 30)
    points = []
    for angle in angles:
        x = int(center[0] + radius * np.cos(angle))
        y = int(center[1] + radius * np.sin(angle))
        points.append([x, y])
    
    if len(points) > 1:
        pts = np.array(points, dtype=np.int32)
        cv2.polylines(frame, [pts], isClosed=False, color=color, thickness=thickness)
    
    return frame


# ─── Public Rendering Functions ──────────────────────────────────────────────
# Rendering order: skeleton → dots → overlays → HUD (strict order)


def draw_skeleton(frame: np.ndarray, keypoints: dict[int, tuple[float, float, float]]) -> np.ndarray:
    """Draw connected skeleton limb lines on the frame.

    Args:
        frame: BGR image array.
        keypoints: Dict mapping landmark_id → (x_px, y_px, visibility).

    Returns:
        Frame with skeleton drawn.
    """
    for start_idx, end_idx in SKELETON_CONNECTIONS:
        if start_idx in keypoints and end_idx in keypoints:
            x1, y1, vis1 = keypoints[start_idx]
            x2, y2, vis2 = keypoints[end_idx]
            
            # Only draw if both keypoints have visibility > 0.5
            if vis1 > 0.5 and vis2 > 0.5:
                cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), 
                         color=(0, 255, 0), thickness=2)
    
    return frame


def draw_joint_dots(frame: np.ndarray, keypoints: dict[int, tuple[float, float, float]]) -> np.ndarray:
    """Draw concentric circles at each keypoint.

    Args:
        frame: BGR image array.
        keypoints: Dict mapping landmark_id → (x_px, y_px, visibility).

    Returns:
        Frame with joint dots drawn.
    """
    for landmark_id, (x, y, visibility) in keypoints.items():
        if visibility > 0.5:
            x_int, y_int = int(x), int(y)
            # Outer circle (white)
            cv2.circle(frame, (x_int, y_int), radius=8, color=(255, 255, 255), thickness=2)
            # Inner circle (red/magenta)
            cv2.circle(frame, (x_int, y_int), radius=4, color=(255, 0, 255), thickness=-1)
    
    return frame


def draw_angle_overlay_xfactor(
    frame: np.ndarray, keypoints: dict[int, tuple[float, float, float]], 
    x_factor_deg: float | None, thresholds: Any
) -> np.ndarray:
    """Draw X-Factor arc overlay.

    Args:
        frame: BGR image array.
        keypoints: Landmark dict.
        x_factor_deg: Measured X-Factor in degrees, or None.
        thresholds: Active thresholds dict.

    Returns:
        Frame with X-Factor overlay.
    """
    if x_factor_deg is None or 11 not in keypoints or 23 not in keypoints:
        return frame
    
    # Get hip center (average of left and right hip)
    if 23 in keypoints and 24 in keypoints:
        hip_x = (keypoints[23][0] + keypoints[24][0]) / 2
        hip_y = (keypoints[23][1] + keypoints[24][1]) / 2
        center = (int(hip_x), int(hip_y))
        
        # Get color based on threshold
        threshold_obj = thresholds.get("x_factor", {}) if thresholds else {}
        green_range = None
        amber_range = None
        
        if hasattr(threshold_obj, "green"):
            green_range = tuple(threshold_obj.green) if threshold_obj.green else None
        if hasattr(threshold_obj, "amber"):
            amber_range = tuple(threshold_obj.amber) if threshold_obj.amber else None
        
        color = _get_color_for_threshold(x_factor_deg, green_range, amber_range)
        
        # Draw arc (rough visualization of X-Factor)
        radius = 60
        frame = _draw_arc_degrees(frame, center, radius, 0, int(x_factor_deg), color, thickness=3)
        
        # Draw text label
        cv2.putText(frame, f"X-Factor: {x_factor_deg:.1f}°", 
                   (int(hip_x) - 80, int(hip_y) - 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
    
    return frame


def draw_angle_overlay_spine(
    frame: np.ndarray, keypoints: dict[int, tuple[float, float, float]], 
    spine_dev_deg: float | None, thresholds: Any
) -> np.ndarray:
    """Draw spine deviation axis line overlay.

    Args:
        frame: BGR image array.
        keypoints: Landmark dict.
        spine_dev_deg: Spine deviation in degrees.
        thresholds: Active thresholds dict.

    Returns:
        Frame with spine overlay.
    """
    if spine_dev_deg is None or 0 not in keypoints or 23 not in keypoints:
        return frame
    
    nose_x, nose_y, _ = keypoints[0]
    hip_x, hip_y, _ = keypoints[23]
    
    # Get color: green if < 5°, else red (per PRD §8)
    color = (0, 255, 0) if spine_dev_deg < 5.0 else (0, 0, 255)
    
    # Draw spine line
    cv2.line(frame, (int(nose_x), int(nose_y)), (int(hip_x), int(hip_y)), 
             color=color, thickness=3)
    
    # Draw label
    cv2.putText(frame, f"Spine: {spine_dev_deg:.1f}°", 
               (int(nose_x) - 60, int(nose_y) - 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    
    return frame


def draw_angle_overlay_wrist_lag(
    frame: np.ndarray, keypoints: dict[int, tuple[float, float, float]], 
    wrist_lag_deg: float | None, thresholds: Any
) -> np.ndarray:
    """Draw wrist lag angle arc overlay.

    Args:
        frame: BGR image array.
        keypoints: Landmark dict.
        wrist_lag_deg: Wrist lag in degrees.
        thresholds: Active thresholds.

    Returns:
        Frame with wrist lag overlay.
    """
    if wrist_lag_deg is None or 15 not in keypoints or 16 not in keypoints:
        return frame
    
    # Use right wrist (impact side for most golfers)
    wrist_x, wrist_y, vis = keypoints[16]
    
    if vis < 0.5:
        return frame
    
    # Get color based on threshold
    threshold_obj = thresholds.get("wrist_lag", {}) if thresholds else {}
    green_min = getattr(threshold_obj, "green_min", 15) if threshold_obj else 15
    
    color = (0, 255, 0) if wrist_lag_deg >= green_min else (0, 0, 255)
    
    # Draw arc at wrist location
    radius = 40
    frame = _draw_arc_degrees(frame, (int(wrist_x), int(wrist_y)), radius, 
                              0, min(int(wrist_lag_deg), 90), color, thickness=2)
    
    cv2.putText(frame, f"Lag: {wrist_lag_deg:.1f}°", 
               (int(wrist_x) - 50, int(wrist_y) + 60),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    return frame


def draw_angle_overlay_knee(
    frame: np.ndarray, keypoints: dict[int, tuple[float, float, float]], 
    knee_flex_deg: float | None, thresholds: Any
) -> np.ndarray:
    """Draw knee flex overlay.

    Args:
        frame: BGR image array.
        keypoints: Landmark dict.
        knee_flex_deg: Knee flex in degrees.
        thresholds: Active thresholds dict.

    Returns:
        Frame with knee overlay.
    """
    if knee_flex_deg is None or 25 not in keypoints or 26 not in keypoints:
        return frame
    
    # Use right knee (lead knee for most golfers)
    knee_x, knee_y, vis = keypoints[26]
    
    if vis < 0.5:
        return frame
    
    # Get color based on threshold
    threshold_obj = thresholds.get("knee_flex", {}) if thresholds else {}
    green_range = None
    
    if hasattr(threshold_obj, "green"):
        green_range = tuple(threshold_obj.green) if threshold_obj.green else None
    
    color = _get_color_for_threshold(knee_flex_deg, green_range, None)
    
    # Draw knee indicator
    cv2.circle(frame, (int(knee_x), int(knee_y)), radius=25, color=color, thickness=2)
    cv2.putText(frame, f"Knee: {knee_flex_deg:.0f}°", 
               (int(knee_x) - 50, int(knee_y)),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    return frame


def draw_angle_overlay_stance(
    frame: np.ndarray, keypoints: dict[int, tuple[float, float, float]], 
    stance_inches: float | None, thresholds: Any
) -> np.ndarray:
    """Draw stance width bracket overlay.

    Args:
        frame: BGR image array.
        keypoints: Landmark dict.
        stance_inches: Stance width in inches.
        thresholds: Active thresholds dict.

    Returns:
        Frame with stance bracket overlay.
    """
    if stance_inches is None or 23 not in keypoints or 24 not in keypoints:
        return frame
    
    hip_left_x, hip_left_y, vis_l = keypoints[23]
    hip_right_x, hip_right_y, vis_r = keypoints[24]
    
    if vis_l < 0.5 or vis_r < 0.5:
        return frame
    
    # Get color based on threshold
    threshold_obj = thresholds.get("stance_width", {}) if thresholds else {}
    
    # For stance width, use ratio-based coloring if available
    color = (100, 100, 255)  # Default orange
    
    # Draw bracket lines at feet
    y_bracket = int(max(hip_left_y, hip_right_y) + 30)
    cv2.line(frame, (int(hip_left_x), y_bracket), (int(hip_left_x), y_bracket + 20), 
             color=color, thickness=2)
    cv2.line(frame, (int(hip_right_x), y_bracket), (int(hip_right_x), y_bracket + 20), 
             color=color, thickness=2)
    cv2.line(frame, (int(hip_left_x), y_bracket + 20), (int(hip_right_x), y_bracket + 20), 
             color=color, thickness=2)
    
    # Draw label
    mid_x = int((hip_left_x + hip_right_x) / 2)
    cv2.putText(frame, f"Stance: {stance_inches:.1f}\"", 
               (mid_x - 60, y_bracket + 45),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    return frame


def draw_bottom_hud(
    frame: np.ndarray, session_json: Any, current_frame: int, total_frames: int
) -> np.ndarray:
    """Draw the bottom HUD panel (18–20% of frame height).

    Args:
        frame: BGR image array.
        session_json: Session object with metrics and thresholds.
        current_frame: Current frame number.
        total_frames: Total frames in sequence.

    Returns:
        Frame with HUD panel drawn.
    """
    height, width = frame.shape[:2]
    hud_height = int(height * 0.20)  # Bottom 20%
    hud_top = height - hud_height
    
    # Draw black background for HUD
    cv2.rectangle(frame, (0, hud_top), (width, height), color=(0, 0, 0), thickness=-1)
    
    # Draw border line
    cv2.line(frame, (0, hud_top), (width, hud_top), color=(100, 100, 100), thickness=2)
    
    # Metrics to display (13 metrics per spec)
    metrics = getattr(session_json, "metrics", {})
    thresholds = getattr(session_json, "active_thresholds", {})
    
    metric_keys = [
        "tempo_ratio", "x_factor", "spine_deviation_max", "hip_sway", "head_sway",
        "hip_turn", "shoulder_turn", "side_bend", "hips_open", "wrist_lag",
        "knee_flex_left", "knee_flex_right", "stance_width"
    ]
    
    # Display first 4 metrics in HUD (space-limited)
    y_pos = hud_top + 25
    x_pos = 20
    col_width = width // 4
    
    for i, key in enumerate(metric_keys[:4]):
        if i > 0 and i % 4 == 0:
            y_pos += 30
            x_pos = 20
        
        metric = metrics.get(key, {}) if isinstance(metrics, dict) else None
        
        if metric and hasattr(metric, "value") and metric.value is not None:
            value = metric.value
            unit = getattr(metric, "unit", "")
            
            # Determine color based on threshold
            threshold_obj = thresholds.get(key) if thresholds else None
            green_range = None
            amber_range = None
            
            if threshold_obj:
                if hasattr(threshold_obj, "green"):
                    green_range = tuple(threshold_obj.green) if threshold_obj.green else None
                if hasattr(threshold_obj, "amber"):
                    amber_range = tuple(threshold_obj.amber) if threshold_obj.amber else None
            
            color = _get_color_for_threshold(value, green_range, amber_range)
            
            # Format value
            text = f"{key.replace('_', ' ')[:10]}: {value:.1f}{unit}"
            cv2.putText(frame, text, (x_pos + (i % 4) * col_width, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    # Display frame counter on right side
    frame_text = f"Frame: {current_frame}/{total_frames}"
    cv2.putText(frame, frame_text, (width - 200, hud_top + 25),
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
    
    # Display score if available
    scores = getattr(session_json, "scores", {})
    if scores and hasattr(scores, "overall") and scores.overall is not None:
        score_text = f"Score: {scores.overall:.0f}"
        cv2.putText(frame, score_text, (width - 200, hud_top + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
    
    return frame


def draw_phase_label(
    frame: np.ndarray, phase_name: str, camera_angle: str
) -> np.ndarray:
    """Draw the phase label in corner of frame.
    
    Args:
        frame: BGR image array.
        phase_name: Phase name (e.g., "Phase 8: Annotated Overlay").
        camera_angle: Camera angle for reference (face_on or down_the_line).
        
    Returns:
        Frame with phase label drawn.
    """
    height, width = frame.shape[:2]
    
    # Draw text in bottom-left corner above HUD
    text = f"{phase_name} | {camera_angle}"
    cv2.putText(frame, text, (20, height - 25),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
    
    return frame
