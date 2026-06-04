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


def _draw_label_with_bg(
    frame: np.ndarray,
    text: str,
    x: int,
    y: int,
    color: tuple[int, int, int],
    font_scale: float = 0.6,
    thickness: int = 1,
) -> np.ndarray:
    """Draw a text label with a semi-transparent black background rectangle.

    Args:
        frame: BGR image array.
        text: Label text.
        x: Baseline x-coordinate of the text.
        y: Baseline y-coordinate of the text.
        color: BGR text color.
        font_scale: OpenCV font scale.
        thickness: Text thickness.

    Returns:
        Frame with label drawn.
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    pad = 3
    # Draw filled dark rectangle behind text
    cv2.rectangle(
        frame,
        (x - pad, y - th - pad),
        (x + tw + pad, y + baseline + pad),
        (0, 0, 0),
        -1,
    )
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)
    return frame


def _resolve_label_positions(
    proposals: list[tuple[int, int, str, tuple[int, int, int]]],
) -> list[tuple[int, int, str, tuple[int, int, int]]]:
    """Resolve vertical overlaps among label proposals by shifting down.

    Labels are sorted by y and then nudged downwards when they would overlap
    (within 20px of the previous label's baseline).

    Args:
        proposals: List of (x, y, text, color) tuples.

    Returns:
        Adjusted list with the same order but de-overlapped y values.
    """
    if not proposals:
        return proposals

    # Sort by y so we process top-to-bottom
    sorted_proposals = sorted(proposals, key=lambda p: p[1])
    resolved: list[tuple[int, int, str, tuple[int, int, int]]] = []
    min_gap = 20  # px

    prev_y: int | None = None
    for x, y, text, color in sorted_proposals:
        if prev_y is not None and y - prev_y < min_gap:
            y = prev_y + min_gap
        resolved.append((x, y, text, color))
        prev_y = y

    return resolved


# ─── Public Rendering Functions ──────────────────────────────────────────────
# Rendering order: skeleton → trail → dots → overlays → HUD (strict order)


def draw_club_path_trail(
    frame: np.ndarray,
    trail: list[tuple[int, int]],
    camera_angle: str = "face_on",
) -> np.ndarray:
    """Draw a fading wrist-path trail representing the club path arc.

    The trail is labelled "Wrist Path" (MediaPipe tracks the wrist, which is
    the closest available proxy to the club head).  Older points fade towards
    transparent; the newest point shows a bright dot.

    Args:
        frame: BGR image array (modified in-place, also returned).
        trail: List of (x, y) pixel positions, oldest first, newest last.
            Typically the last 30 wrist positions inside the critical window.
        camera_angle: "face_on" draws cyan; "down_the_line" draws magenta.

    Returns:
        Frame with the trail drawn.
    """
    if len(trail) < 2:
        return frame

    # Base colour: cyan for face-on, magenta for DTL
    base_color = (255, 255, 0) if camera_angle == "face_on" else (255, 0, 255)

    n = len(trail)
    overlay = frame.copy()

    for i in range(1, n):
        # Alpha ramps from 0.15 (oldest segment) to 1.0 (newest segment)
        alpha = 0.15 + 0.85 * (i / (n - 1))
        # Thickness ramps from 1 (oldest) to 3 (newest)
        thickness = max(1, int(1 + 2 * (i / (n - 1))))

        pt1 = trail[i - 1]
        pt2 = trail[i]
        cv2.line(overlay, pt1, pt2, base_color, thickness, cv2.LINE_AA)

        # Blend this segment's line into the main frame
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        # Reset overlay for the next segment
        overlay = frame.copy()

    # Bright dot at the current (newest) wrist position
    cv2.circle(frame, trail[-1], radius=5, color=base_color, thickness=-1)

    # Small "Wrist Path" label near the trail head — offset to avoid keypoint dots
    lx, ly = trail[-1]
    label_x = min(lx + 12, frame.shape[1] - 90)
    label_y = max(ly - 10, 14)
    cv2.putText(
        frame, "Wrist Path",
        (label_x, label_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        base_color,
        1,
        cv2.LINE_AA,
    )

    return frame


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
    x_factor_deg: float | None, thresholds: Any,
    label_proposals: list | None = None,
) -> np.ndarray:
    """Draw X-Factor arc overlay.

    Args:
        frame: BGR image array.
        keypoints: Landmark dict.
        x_factor_deg: Measured X-Factor in degrees, or None.
        thresholds: Active thresholds dict.
        label_proposals: Optional list to collect (x, y, text, color) instead of drawing immediately.

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
        
        # Collect label proposal for deferred drawing
        lbl_x = max(0, int(hip_x) + 30)
        lbl_y = max(20, int(hip_y) - 70)
        if label_proposals is not None:
            label_proposals.append((lbl_x, lbl_y, f"X-Factor: {x_factor_deg:.1f}deg", color))
        else:
            frame = _draw_label_with_bg(
                frame, f"X-Factor: {x_factor_deg:.1f}deg", lbl_x, lbl_y, color, font_scale=0.6, thickness=1
            )
    
    return frame


def draw_angle_overlay_spine(
    frame: np.ndarray, keypoints: dict[int, tuple[float, float, float]], 
    spine_dev_deg: float | None, thresholds: Any,
    label_proposals: list | None = None,
) -> np.ndarray:
    """Draw spine deviation axis line overlay.

    Args:
        frame: BGR image array.
        keypoints: Landmark dict.
        spine_dev_deg: Spine deviation in degrees.
        thresholds: Active thresholds dict.
        label_proposals: Optional list to collect (x, y, text, color) instead of drawing immediately.

    Returns:
        Frame with spine overlay.
    """
    if spine_dev_deg is None or 0 not in keypoints or 23 not in keypoints:
        return frame
    
    nose_x, nose_y, _ = keypoints[0]
    hip_x, hip_y, _ = keypoints[23]
    
    # Get color: green if < 5 deg, else red (per PRD §8)
    color = (0, 255, 0) if spine_dev_deg < 5.0 else (0, 0, 255)
    
    # Draw spine line
    cv2.line(frame, (int(nose_x), int(nose_y)), (int(hip_x), int(hip_y)), 
             color=color, thickness=3)
    
    # Collect label proposal — anchor LEFT of nose to keep away from X-Factor (right of hips)
    lbl_x = max(2, int(nose_x) - 120)
    lbl_y = max(20, int(nose_y) - 10)
    if label_proposals is not None:
        label_proposals.append((lbl_x, lbl_y, f"Spine: {spine_dev_deg:.1f}deg", color))
    else:
        frame = _draw_label_with_bg(
            frame, f"Spine: {spine_dev_deg:.1f}deg", lbl_x, lbl_y, color, font_scale=0.6, thickness=1
        )
    
    return frame


def draw_angle_overlay_wrist_lag(
    frame: np.ndarray, keypoints: dict[int, tuple[float, float, float]], 
    wrist_lag_deg: float | None, thresholds: Any,
    label_proposals: list | None = None,
) -> np.ndarray:
    """Draw wrist lag angle arc overlay.

    Args:
        frame: BGR image array.
        keypoints: Landmark dict.
        wrist_lag_deg: Wrist lag in degrees.
        thresholds: Active thresholds.
        label_proposals: Optional list to collect (x, y, text, color) instead of drawing immediately.

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
    
    # Collect label proposal for deferred drawing
    lbl_x = max(0, int(wrist_x) + 30)
    lbl_y = int(wrist_y) + 10
    if label_proposals is not None:
        label_proposals.append((lbl_x, lbl_y, f"Lag: {wrist_lag_deg:.1f}deg", color))
    else:
        frame = _draw_label_with_bg(
            frame, f"Lag: {wrist_lag_deg:.1f}deg", lbl_x, lbl_y, color, font_scale=0.6, thickness=1
        )
    
    return frame


def draw_angle_overlay_knee(
    frame: np.ndarray, keypoints: dict[int, tuple[float, float, float]], 
    knee_flex_deg: float | None, thresholds: Any,
    label_proposals: list | None = None,
) -> np.ndarray:
    """Draw knee flex overlay.

    Args:
        frame: BGR image array.
        keypoints: Landmark dict.
        knee_flex_deg: Knee flex in degrees.
        thresholds: Active thresholds dict.
        label_proposals: Optional list to collect (x, y, text, color) instead of drawing immediately.

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
    
    # Draw knee indicator circle
    cv2.circle(frame, (int(knee_x), int(knee_y)), radius=25, color=color, thickness=2)

    # Collect label proposal — anchor LEFT of knee to keep away from Stance (centred below)
    lbl_x = max(2, int(knee_x) - 120)
    lbl_y = int(knee_y) + 10
    if label_proposals is not None:
        label_proposals.append((lbl_x, lbl_y, f"Knee: {knee_flex_deg:.0f}deg", color))
    else:
        frame = _draw_label_with_bg(
            frame, f"Knee: {knee_flex_deg:.0f}deg", lbl_x, lbl_y, color, font_scale=0.6, thickness=1
        )
    
    return frame


def draw_angle_overlay_stance(
    frame: np.ndarray, keypoints: dict[int, tuple[float, float, float]], 
    stance_inches: float | None, thresholds: Any,
    label_proposals: list | None = None,
) -> np.ndarray:
    """Draw stance width bracket overlay.

    Args:
        frame: BGR image array.
        keypoints: Landmark dict.
        stance_inches: Stance width in inches.
        thresholds: Active thresholds dict.
        label_proposals: Optional list to collect (x, y, text, color) instead of drawing immediately.

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
    color = (100, 100, 255)  # Default blue-ish
    
    # Draw bracket lines at hips (proxy for feet)
    y_bracket = int(max(hip_left_y, hip_right_y) + 30)
    cv2.line(frame, (int(hip_left_x), y_bracket), (int(hip_left_x), y_bracket + 20), 
             color=color, thickness=2)
    cv2.line(frame, (int(hip_right_x), y_bracket), (int(hip_right_x), y_bracket + 20), 
             color=color, thickness=2)
    cv2.line(frame, (int(hip_left_x), y_bracket + 20), (int(hip_right_x), y_bracket + 20), 
             color=color, thickness=2)
    
    # Collect label proposal for deferred drawing
    mid_x = int((hip_left_x + hip_right_x) / 2)
    lbl_x = max(0, mid_x - 50)
    lbl_y = y_bracket + 45
    if label_proposals is not None:
        label_proposals.append((lbl_x, lbl_y, f"Stance: {stance_inches:.1f}\"", color))
    else:
        frame = _draw_label_with_bg(
            frame, f"Stance: {stance_inches:.1f}\"", lbl_x, lbl_y, color, font_scale=0.6, thickness=1
        )
    
    return frame


def draw_angle_overlays_with_deoverlap(
    frame: np.ndarray,
    keypoints: dict[int, tuple[float, float, float]],
    overlays: dict[str, float | None],
    thresholds: Any,
    camera_angle: str,
) -> np.ndarray:
    """Draw all angle overlays for a camera angle with label de-overlap.

    Collects all label proposals from individual overlay drawers, runs
    them through vertical de-overlap, then draws them all with background
    rectangles in one pass.

    Args:
        frame: BGR image array.
        keypoints: Landmark dict.
        overlays: Dict of metric_name → value (e.g. {"x_factor": 19.7}).
        thresholds: Active thresholds dict.
        camera_angle: "face_on" or "down_the_line".

    Returns:
        Frame with all overlays drawn, labels de-overlapped.
    """
    label_proposals: list[tuple[int, int, str, tuple[int, int, int]]] = []

    if camera_angle == "face_on":
        frame = draw_angle_overlay_xfactor(frame, keypoints, overlays.get("x_factor"), thresholds, label_proposals)
        frame = draw_angle_overlay_spine(frame, keypoints, overlays.get("spine_deviation"), thresholds, label_proposals)
        frame = draw_angle_overlay_stance(frame, keypoints, overlays.get("stance_width"), thresholds, label_proposals)
        frame = draw_angle_overlay_knee(frame, keypoints, overlays.get("knee_flex"), thresholds, label_proposals)
    elif camera_angle == "down_the_line":
        frame = draw_angle_overlay_wrist_lag(frame, keypoints, overlays.get("wrist_lag"), thresholds, label_proposals)
    else:
        frame = draw_angle_overlay_xfactor(frame, keypoints, overlays.get("x_factor"), thresholds, label_proposals)
        frame = draw_angle_overlay_spine(frame, keypoints, overlays.get("spine_deviation"), thresholds, label_proposals)
        frame = draw_angle_overlay_wrist_lag(frame, keypoints, overlays.get("wrist_lag"), thresholds, label_proposals)
        frame = draw_angle_overlay_knee(frame, keypoints, overlays.get("knee_flex"), thresholds, label_proposals)
        frame = draw_angle_overlay_stance(frame, keypoints, overlays.get("stance_width"), thresholds, label_proposals)

    # Fixed per-label colors (no background rects — text directly on frame)
    # BGR: yellow, orange, red, white, cyan
    _LABEL_COLORS: dict[str, tuple[int, int, int]] = {
        "Spine":    (0, 255, 255),   # yellow
        "X-Factor": (0, 165, 255),   # orange
        "Knee":     (0, 0, 255),     # red
        "Stance":   (255, 255, 255), # white
        "Lag":      (255, 255, 0),   # cyan
    }

    # De-overlap all label positions globally, then draw plain text
    resolved = _resolve_label_positions(label_proposals)
    for lbl_x, lbl_y, text, _unused_color in resolved:
        # Pick fixed color by matching the label prefix
        label_color = next(
            (c for prefix, c in _LABEL_COLORS.items() if text.startswith(prefix)),
            (200, 200, 200),  # fallback: light grey
        )
        cv2.putText(
            frame, text,
            (lbl_x, lbl_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,        # font scale
            label_color,
            2,           # thickness — bold for visibility without bg
        )

    return frame


def _get_swing_phase_label(
    current_frame: int,
    start_frame: int,
    end_frame: int,
) -> str:
    """Compute the current swing phase name from the frame index.

    Zones:
      - Before start_frame:                       "SETUP / ADDRESS"
      - 0%–30% of swing window:                   "SWING #1 -> BACKSWING"
      - 30%–70% of swing window:                  "SWING #1 -> DOWNSWING"
      - 70%–100% of swing window:                 "FOLLOW THROUGH"
      - After end_frame:                           "SETUP / BETWEEN SWINGS"

    Args:
        current_frame: Current slowmo frame index.
        start_frame: First frame of the critical window.
        end_frame: Last frame of the critical window.

    Returns:
        Uppercase phase label string.
    """
    if current_frame < start_frame:
        return "SETUP / ADDRESS"
    if current_frame > end_frame:
        return "SETUP / BETWEEN SWINGS"

    swing_len = max(end_frame - start_frame, 1)
    pct = (current_frame - start_frame) / swing_len

    if pct < 0.30:
        return "SWING #1 -> BACKSWING"
    elif pct < 0.70:
        return "SWING #1 -> DOWNSWING"
    else:
        return "FOLLOW THROUGH"


def draw_bottom_hud(
    frame: np.ndarray,
    session_json: Any,
    current_frame: int,
    total_frames: int,
    camera_angle: str | None = None,
    start_frame: int = 0,
    end_frame: int | None = None,
) -> np.ndarray:
    """Draw the bottom HUD panel (18–20% of frame height).

    Args:
        frame: BGR image array.
        session_json: Session object with metrics and thresholds.
        current_frame: Current frame number.
        total_frames: Total frames in sequence.
        camera_angle: Camera angle description (e.g. 'face_on' or 'down_the_line').
        start_frame: First frame of the critical (swing) window.
        end_frame: Last frame of the critical window (defaults to total_frames - 1).

    Returns:
        Frame with HUD panel drawn.
    """
    if end_frame is None:
        end_frame = max(total_frames - 1, 0)

    height, width = frame.shape[:2]
    hud_height = int(height * 0.20)  # Bottom 20%
    hud_top = height - hud_height
    
    # Draw black background for HUD
    cv2.rectangle(frame, (0, hud_top), (width, height), color=(0, 0, 0), thickness=-1)
    
    # Draw border line
    cv2.line(frame, (0, hud_top), (width, hud_top), color=(100, 100, 100), thickness=2)
    
    # Extract metrics and thresholds from session
    if isinstance(session_json, dict):
        metrics = session_json.get("metrics", {})
        thresholds = session_json.get("active_thresholds", {})
    else:
        metrics = getattr(session_json, "metrics", {})
        thresholds = getattr(session_json, "active_thresholds", {})

    left_keys = ["tempo_ratio", "x_factor", "hip_sway", "head_sway"]
    right_keys = ["hip_turn", "shoulder_turn", "side_bend", "hips_open"]
    
    metric_display_names = {
        "tempo_ratio": "Tempo Ratio",
        "x_factor": "X-Factor",
        "hip_sway": "Hip Sway",
        "head_sway": "Head Sway",
        "hip_turn": "Hip Turn",
        "shoulder_turn": "Shoulder Turn",
        "side_bend": "Side Bend",
        "hips_open": "Hips Open"
    }

    def get_metric_text_and_color(key: str) -> tuple[str, tuple[int, int, int]]:
        display_name = metric_display_names.get(key, key.replace('_', ' ').title())
        
        # Accessing metrics dict or mock attributes
        metric = metrics.get(key) if isinstance(metrics, dict) else getattr(metrics, key, None)
        
        if metric is None:
            return f"{display_name}: N/A", (150, 150, 150)
            
        if isinstance(metric, dict):
            value = metric.get("value")
            unit = metric.get("unit", "")
        else:
            value = getattr(metric, "value", None)
            unit = getattr(metric, "unit", "")
            
        if value is None:
            return f"{display_name}: N/A", (150, 150, 150)
            
        safe_unit = unit.replace("\u00b0", "deg") if unit else ""
        if safe_unit == "°":
            safe_unit = "deg"
            
        try:
            val_float = float(value)
            text = f"{display_name}: {val_float:.1f}{safe_unit}"
        except (ValueError, TypeError):
            text = f"{display_name}: {value}{safe_unit}"
            val_float = 0.0
            
        # Determine color based on threshold
        threshold_obj = thresholds.get(key) if thresholds else None
        green_range = None
        amber_range = None
        
        if threshold_obj:
            if isinstance(threshold_obj, dict):
                green_range = threshold_obj.get("green")
                amber_range = threshold_obj.get("amber")
            else:
                if hasattr(threshold_obj, "green"):
                    green_range = threshold_obj.green
                if hasattr(threshold_obj, "amber"):
                    amber_range = threshold_obj.amber
                    
        if green_range:
            green_range = tuple(green_range)
        if amber_range:
            amber_range = tuple(amber_range)
            
        color = _get_color_for_threshold(val_float, green_range, amber_range)
        return text, color

    # Calculate layout geometry
    spacing = max(12, int(hud_height * 0.15))
    font_scale = 0.45
    thickness = 1
    
    # 1. Left panel (x=10)
    for idx, key in enumerate(left_keys):
        text, color = get_metric_text_and_color(key)
        y = hud_top + spacing + idx * spacing
        cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
        
    # 2. Right panel (x = frame_width//2 + 10)
    right_x = width // 2 + 10
    for idx, key in enumerate(right_keys):
        text, color = get_metric_text_and_color(key)
        y = hud_top + spacing + idx * spacing
        cv2.putText(frame, text, (right_x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
        
    # 3. Frame counter: at x = frame_width - 160, y near bottom (never clipped)
    frame_text = f"Frame: {current_frame}/{total_frames}"
    counter_y = hud_top + spacing + 4 * spacing + 2
    cv2.putText(
        frame, frame_text,
        (width - 160, counter_y),
        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (200, 200, 200), thickness
    )
    
    # 4. Swing phase label at bottom-left — dynamic based on swing window
    phase_lbl = _get_swing_phase_label(current_frame, start_frame, end_frame)
    cv2.putText(
        frame, phase_lbl,
        (10, counter_y),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2  # Bold, white
    )
    
    # 5. Horizontal progress bar below phase label (250px wide)
    bar_x1 = 10
    bar_x2 = 260  # Extended from 200 → 260 (250px wide)
    bar_y1 = counter_y + 6
    bar_y2 = counter_y + 12  # 6px tall
    
    # Draw background bar (dark grey)
    cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (80, 80, 80), -1)
    
    # Draw filled progress bar (bright green), proportional to current_frame / total_frames
    if total_frames > 0:
        pct = min(max(current_frame / total_frames, 0.0), 1.0)
    else:
        pct = 0.0
    fill_x = int(bar_x1 + (bar_x2 - bar_x1) * pct)
    if fill_x > bar_x1:
        cv2.rectangle(frame, (bar_x1, bar_y1), (fill_x, bar_y2), (0, 255, 0), -1)
        
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
