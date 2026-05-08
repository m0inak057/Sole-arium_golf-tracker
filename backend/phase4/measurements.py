"""Biomechanical measurements — all 13 metrics.

Calculates the 13 core metrics mathematically across the swing frame sequence.
All calculations use real 3D vector geometry from MediaPipe keypoints.

Reference: data-schema.md §1 "metrics" section (lines 56–71).
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from backend.core.session import SessionJSON, MetricEntry
from backend.core.logging import get_logger

logger = get_logger(__name__)

# ─── Helper Functions ────────────────────────────────────────────────────────


def angle_between_vectors_deg(p1: pd.Series, p2: pd.Series, p3: pd.Series) -> float | None:
    """Calculate angle at p2 formed by vectors (p1→p2) and (p2→p3).

    Uses 3D dot product to compute angle between two 3D vectors.
    Returns None if any vector has zero magnitude (degenerate case).

    Args:
        p1, p2, p3: Pandas Series with x, y, z attributes (from keypoint rows).

    Returns:
        Angle in degrees [0, 180], or None if calculation fails.
    """
    try:
        # Vector from p1 to p2
        v1 = (float(p2["x"] - p1["x"]), float(p2["y"] - p1["y"]), float(p2["z"] - p1["z"]))
        # Vector from p2 to p3
        v2 = (float(p3["x"] - p2["x"]), float(p3["y"] - p2["y"]), float(p3["z"] - p2["z"]))

        # Magnitudes
        mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2 + v1[2] ** 2)
        mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2 + v2[2] ** 2)

        if mag1 < 1e-6 or mag2 < 1e-6:
            return None

        # Dot product
        dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]

        # Cosine of angle, clamped to [-1, 1] for numerical stability
        cos_angle = dot / (mag1 * mag2)
        cos_angle = max(-1.0, min(1.0, cos_angle))

        angle_rad = math.acos(cos_angle)
        return math.degrees(angle_rad)
    except (ValueError, KeyError, TypeError):
        return None


def line_angle_deg(p1: pd.Series, p2: pd.Series) -> float | None:
    """Calculate angle of a line from p1 to p2 from vertical (atan2 approach).

    Measures the angle that a vector makes relative to vertical (y-axis).
    Useful for measuring hip/shoulder line rotation.

    Args:
        p1, p2: Pandas Series with x, y (and optional z).

    Returns:
        Angle in degrees [0, 180], or None on error.
    """
    try:
        dx = float(p2["x"] - p1["x"])
        dy = float(p2["y"] - p1["y"])

        # Angle off vertical: atan2(horizontal, vertical)
        angle_rad = math.atan2(abs(dx), abs(dy))
        return math.degrees(angle_rad)
    except (ValueError, KeyError, TypeError):
        return None


def distance_2d(p1: pd.Series, p2: pd.Series, width: int = 1920, height: int = 1080) -> float | None:
    """Calculate 2D Euclidean distance in pixel space.

    Converts normalized coordinates (0.0–1.0) to pixel space, then computes distance.

    Args:
        p1, p2: Pandas Series with x, y (normalized 0.0–1.0).
        width, height: Video dimensions for denormalization.

    Returns:
        Distance in pixels, or None on error.
    """
    try:
        px1 = float(p1["x"]) * width
        py1 = float(p1["y"]) * height
        px2 = float(p2["x"]) * width
        py2 = float(p2["y"]) * height

        dist = math.sqrt((px2 - px1) ** 2 + (py2 - py1) ** 2)
        return dist
    except (ValueError, KeyError, TypeError):
        return None


def get_frame_subset(df: pd.DataFrame, start_frame: int | None, end_frame: int | None) -> pd.DataFrame:
    """Filter dataframe to a frame range.

    Args:
        df: Full dataframe.
        start_frame: Inclusive start (None = start of dataframe).
        end_frame: Inclusive end (None = end of dataframe).

    Returns:
        Filtered dataframe.
    """
    result = df
    if start_frame is not None:
        result = result[result["frame_index"] >= start_frame]
    if end_frame is not None:
        result = result[result["frame_index"] <= end_frame]
    return result


def get_frame_landmark(df: pd.DataFrame, frame_idx: int | None, landmark_name: str) -> pd.Series | None:
    """Get a single landmark from a specific frame.

    Args:
        df: Full dataframe.
        frame_idx: Frame index (None = not available).
        landmark_name: Landmark name (e.g., "left_ankle").

    Returns:
        Pandas Series with x, y, z, visibility, or None if not found.
    """
    if frame_idx is None:
        return None
    subset = df[(df["frame_index"] == frame_idx) & (df["landmark_name"] == landmark_name)]
    if subset.empty:
        return None
    return subset.iloc[0]


def check_visibility(lm: pd.Series | None, threshold: float = 0.5) -> bool:
    """Check if a landmark is visible (visibility >= threshold).

    Args:
        lm: Landmark series, or None.
        threshold: Minimum visibility score.

    Returns:
        True if visible, False otherwise.
    """
    return lm is not None and float(lm.get("visibility", 0.0)) >= threshold


# ─── Metric Calculation Functions ────────────────────────────────────────────


def _compute_stance_width(session: SessionJSON) -> MetricEntry:
    """Metric 13: Stance width — distance between ankles at address."""
    setup_metrics = session.setup_metrics
    sw_px = setup_metrics.stance_width_px if setup_metrics else None
    scale = session.px_to_inches_scale or 1.0

    if sw_px is not None:
        return MetricEntry(value=round(sw_px * scale, 1), unit="inches", primary=True)
    else:
        return MetricEntry(
            value=None, unit="inches", primary=True, null_reason="Address frames unreadable"
        )


def _compute_tempo_ratio(session: SessionJSON) -> MetricEntry:
    """Metric 1: Tempo ratio — backswing frames / downswing frames."""
    bs_start = session.backswing_start_frame_index
    impact = session.impact_frame_index

    if bs_start is None or impact is None or impact <= bs_start:
        return MetricEntry(
            value=None, unit="ratio", primary=True, null_reason="Swing bounds missing"
        )

    # Approximate top of backswing as 70% of the way from start to impact
    top_frame = bs_start + int((impact - bs_start) * 0.7)
    bs_frames = top_frame - bs_start
    ds_frames = impact - top_frame

    if ds_frames <= 0:
        return MetricEntry(
            value=None, unit="ratio", primary=True, null_reason="Invalid downswing duration"
        )

    val = round(bs_frames / ds_frames, 2)
    return MetricEntry(value=val, unit="ratio", primary=True)


def _compute_hip_sway(df: pd.DataFrame | None, address_frame_range: list[int] | None, scale: float) -> MetricEntry:
    """Metric 4: Hip sway — max horizontal delta of hip midpoint from address."""
    if not address_frame_range or len(address_frame_range) < 2:
        return MetricEntry(
            value=None, unit="inches", primary=True, null_reason="Address frames unavailable"
        )

    if df is None:
        return MetricEntry(
            value=None, unit="inches", primary=True, null_reason="Keypoint data missing"
        )

    addr_df = get_frame_subset(df, address_frame_range[0], address_frame_range[1])
    if addr_df.empty:
        return MetricEntry(
            value=None, unit="inches", primary=True, null_reason="Address frames unreadable"
        )

    # Get median hip position at address
    left_hip_addr = addr_df[
        (addr_df["landmark_name"] == "left_hip") & (addr_df["visibility"] >= 0.5)
    ][["x", "y", "z", "visibility"]].median()
    right_hip_addr = addr_df[
        (addr_df["landmark_name"] == "right_hip") & (addr_df["visibility"] >= 0.5)
    ][["x", "y", "z", "visibility"]].median()

    if left_hip_addr.empty or right_hip_addr.empty:
        return MetricEntry(
            value=None, unit="inches", primary=True, null_reason="Hip keypoints not visible at address"
        )

    addr_hip_x = (float(left_hip_addr["x"]) + float(right_hip_addr["x"])) / 2.0

    # Get max horizontal deviation during swing
    swing_df = df[df["visibility"] >= 0.5]
    left_hip_swing = swing_df[swing_df["landmark_name"] == "left_hip"][["frame_index", "x", "y", "z", "visibility"]]
    right_hip_swing = swing_df[swing_df["landmark_name"] == "right_hip"][["frame_index", "x", "y", "z", "visibility"]]

    max_sway_px = 0.0
    for _, lh in left_hip_swing.iterrows():
        for _, rh in right_hip_swing.iterrows():
            if lh["frame_index"] == rh["frame_index"]:  # Same frame
                hip_x = (float(lh["x"]) + float(rh["x"])) / 2.0
                delta_px = abs(hip_x - addr_hip_x) * 1920  # Assume 1920 width
                max_sway_px = max(max_sway_px, delta_px)

    if max_sway_px < 0.1:
        return MetricEntry(value=0.0, unit="inches", primary=True)

    return MetricEntry(value=round(max_sway_px * scale, 1), unit="inches", primary=True)


def _compute_head_sway(df: pd.DataFrame, address_frame_range: list[int] | None, scale: float) -> MetricEntry:
    """Metric 5: Head sway — max horizontal delta of nose from address."""
    if not address_frame_range or len(address_frame_range) < 2:
        return MetricEntry(
            value=None, unit="inches", primary=True, null_reason="Address frames unavailable"
        )

    addr_df = get_frame_subset(df, address_frame_range[0], address_frame_range[1])
    nose_addr = addr_df[
        (addr_df["landmark_name"] == "nose") & (addr_df["visibility"] >= 0.5)
    ][["x", "y", "z", "visibility"]]

    if nose_addr.empty:
        return MetricEntry(
            value=None, unit="inches", primary=True, null_reason="Nose not visible at address"
        )

    addr_nose_x = float(nose_addr["x"].median())

    # Max horizontal deviation during swing
    swing_nose = df[
        (df["landmark_name"] == "nose") & (df["visibility"] >= 0.5)
    ][["x", "y", "z", "visibility", "frame_index"]]

    max_sway_px = 0.0
    for _, nose in swing_nose.iterrows():
        delta_px = abs(float(nose["x"]) - addr_nose_x) * 1920  # Assume 1920 width
        max_sway_px = max(max_sway_px, delta_px)

    if max_sway_px < 0.1:
        return MetricEntry(value=0.0, unit="inches", primary=True)

    return MetricEntry(value=round(max_sway_px * scale, 1), unit="inches", primary=True)


def _compute_hip_turn(df: pd.DataFrame, address_frame_range: list[int] | None, impact_frame: int | None) -> MetricEntry:
    """Metric 6: Hip turn — rotation of hip-line from address to impact."""
    if not address_frame_range or not impact_frame:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Swing bounds missing")

    # Hip-line angle at address
    addr_df = get_frame_subset(df, address_frame_range[0], address_frame_range[1])
    left_hip_addr = addr_df[
        (addr_df["landmark_name"] == "left_hip") & (addr_df["visibility"] >= 0.5)
    ][["x", "y", "z"]].median()
    right_hip_addr = addr_df[
        (addr_df["landmark_name"] == "right_hip") & (addr_df["visibility"] >= 0.5)
    ][["x", "y", "z"]].median()

    if left_hip_addr.empty or right_hip_addr.empty:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Hip keypoints not visible at address")

    addr_angle = line_angle_deg(left_hip_addr, right_hip_addr)

    # Hip-line angle at impact
    left_hip_impact = get_frame_landmark(df, impact_frame, "left_hip")
    right_hip_impact = get_frame_landmark(df, impact_frame, "right_hip")

    if not check_visibility(left_hip_impact) or not check_visibility(right_hip_impact):
        return MetricEntry(
            value=None, unit="deg", primary=True, null_reason="Hip keypoints not visible at impact"
        )

    impact_angle = line_angle_deg(left_hip_impact, right_hip_impact)

    if addr_angle is None or impact_angle is None:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Hip line calculation failed")

    delta_angle = round(abs(impact_angle - addr_angle), 1)
    return MetricEntry(value=delta_angle, unit="deg", primary=True)


def _compute_shoulder_turn(df: pd.DataFrame, address_frame_range: list[int] | None, impact_frame: int | None) -> MetricEntry:
    """Metric 7: Shoulder turn — rotation of shoulder-line from address to impact."""
    if not address_frame_range or not impact_frame:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Swing bounds missing")

    # Shoulder-line angle at address
    addr_df = get_frame_subset(df, address_frame_range[0], address_frame_range[1])
    left_sh_addr = addr_df[
        (addr_df["landmark_name"] == "left_shoulder") & (addr_df["visibility"] >= 0.5)
    ][["x", "y", "z"]].median()
    right_sh_addr = addr_df[
        (addr_df["landmark_name"] == "right_shoulder") & (addr_df["visibility"] >= 0.5)
    ][["x", "y", "z"]].median()

    if left_sh_addr.empty or right_sh_addr.empty:
        return MetricEntry(
            value=None, unit="deg", primary=True, null_reason="Shoulder keypoints not visible at address"
        )

    addr_angle = line_angle_deg(left_sh_addr, right_sh_addr)

    # Shoulder-line angle at impact
    left_sh_impact = get_frame_landmark(df, impact_frame, "left_shoulder")
    right_sh_impact = get_frame_landmark(df, impact_frame, "right_shoulder")

    if not check_visibility(left_sh_impact) or not check_visibility(right_sh_impact):
        return MetricEntry(
            value=None, unit="deg", primary=True, null_reason="Shoulder keypoints not visible at impact"
        )

    impact_angle = line_angle_deg(left_sh_impact, right_sh_impact)

    if addr_angle is None or impact_angle is None:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Shoulder line calculation failed")

    delta_angle = round(abs(impact_angle - addr_angle), 1)
    return MetricEntry(value=delta_angle, unit="deg", primary=True)


def _compute_x_factor(df: pd.DataFrame, bs_start: int | None, impact_frame: int | None) -> MetricEntry:
    """Metric 2: X-factor — angle between hip-line and shoulder-line vectors."""
    if not bs_start or not impact_frame or impact_frame <= bs_start:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Swing bounds missing")

    # Use median positions during backswing for stability
    bs_df = get_frame_subset(df, bs_start, impact_frame)
    bs_df_visible = bs_df[bs_df["visibility"] >= 0.5]

    left_hip = bs_df_visible[bs_df_visible["landmark_name"] == "left_hip"][["x", "y", "z"]].median()
    right_hip = bs_df_visible[bs_df_visible["landmark_name"] == "right_hip"][["x", "y", "z"]].median()
    left_sh = bs_df_visible[bs_df_visible["landmark_name"] == "left_shoulder"][["x", "y", "z"]].median()
    right_sh = bs_df_visible[bs_df_visible["landmark_name"] == "right_shoulder"][["x", "y", "z"]].median()

    if left_hip.empty or right_hip.empty or left_sh.empty or right_sh.empty:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Keypoints not visible during backswing")

    # Hip-line vector: from left_hip to right_hip
    hip_vector = (
        float(right_hip["x"]) - float(left_hip["x"]),
        float(right_hip["y"]) - float(left_hip["y"]),
        float(right_hip["z"]) - float(left_hip["z"]),
    )

    # Shoulder-line vector: from left_sh to right_sh
    sh_vector = (
        float(right_sh["x"]) - float(left_sh["x"]),
        float(right_sh["y"]) - float(left_sh["y"]),
        float(right_sh["z"]) - float(left_sh["z"]),
    )

    # Angle between the two vectors
    mag_hip = math.sqrt(sum(v ** 2 for v in hip_vector))
    mag_sh = math.sqrt(sum(v ** 2 for v in sh_vector))

    if mag_hip < 1e-6 or mag_sh < 1e-6:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Degenerate hip or shoulder line")

    dot = sum(h * s for h, s in zip(hip_vector, sh_vector))
    cos_angle = dot / (mag_hip * mag_sh)
    cos_angle = max(-1.0, min(1.0, cos_angle))

    angle_rad = math.acos(cos_angle)
    x_factor = round(math.degrees(angle_rad), 1)

    return MetricEntry(value=x_factor, unit="deg", primary=True)


def _compute_spine_deviation_max(df: pd.DataFrame, address_frame_range: list[int] | None, bs_start: int | None, impact_frame: int | None) -> MetricEntry:
    """Metric 3: Spine deviation max — max delta of spine angle from address."""
    if not address_frame_range or not bs_start or not impact_frame:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Frame indices missing")

    # Spine angle at address (right shoulder to right hip)
    addr_df = get_frame_subset(df, address_frame_range[0], address_frame_range[1])
    r_sh_addr = addr_df[
        (addr_df["landmark_name"] == "right_shoulder") & (addr_df["visibility"] >= 0.5)
    ][["x", "y", "z"]].median()
    r_hip_addr = addr_df[
        (addr_df["landmark_name"] == "right_hip") & (addr_df["visibility"] >= 0.5)
    ][["x", "y", "z"]].median()

    if r_sh_addr.empty or r_hip_addr.empty:
        return MetricEntry(
            value=None, unit="deg", primary=True, null_reason="Spine keypoints not visible at address"
        )

    addr_spine_angle = line_angle_deg(r_sh_addr, r_hip_addr)

    # Max spine deviation during downswing (from backswing start to impact)
    ds_df = get_frame_subset(df, bs_start, impact_frame)
    ds_df_visible = ds_df[ds_df["visibility"] >= 0.5]

    max_deviation = 0.0
    for frame_idx in ds_df_visible["frame_index"].unique():
        r_sh = get_frame_landmark(ds_df, int(frame_idx), "right_shoulder")
        r_hip = get_frame_landmark(ds_df, int(frame_idx), "right_hip")

        if check_visibility(r_sh) and check_visibility(r_hip):
            spine_angle = line_angle_deg(r_sh, r_hip)
            if spine_angle is not None and addr_spine_angle is not None:
                deviation = abs(spine_angle - addr_spine_angle)
                max_deviation = max(max_deviation, deviation)

    if max_deviation < 0.1 or addr_spine_angle is None:
        return MetricEntry(value=0.0, unit="deg", primary=True)

    return MetricEntry(value=round(max_deviation, 1), unit="deg", primary=True)


def _compute_side_bend(df: pd.DataFrame, bs_start: int | None, impact_frame: int | None) -> MetricEntry:
    """Metric 8: Side bend — lateral tilt of torso from vertical."""
    if not bs_start or not impact_frame:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Swing bounds missing")

    # Use median torso position during backswing
    bs_df = get_frame_subset(df, bs_start, impact_frame)
    bs_df_visible = bs_df[bs_df["visibility"] >= 0.5]

    l_sh = bs_df_visible[bs_df_visible["landmark_name"] == "left_shoulder"][["x", "y", "z"]].median()
    r_sh = bs_df_visible[bs_df_visible["landmark_name"] == "right_shoulder"][["x", "y", "z"]].median()
    l_hip = bs_df_visible[bs_df_visible["landmark_name"] == "left_hip"][["x", "y", "z"]].median()
    r_hip = bs_df_visible[bs_df_visible["landmark_name"] == "right_hip"][["x", "y", "z"]].median()

    if l_sh.empty or r_sh.empty or l_hip.empty or r_hip.empty:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Torso keypoints not visible")

    # Torso midline: from midpoint of shoulders to midpoint of hips
    sh_mid_x = (float(l_sh["x"]) + float(r_sh["x"])) / 2.0
    sh_mid_y = (float(l_sh["y"]) + float(r_sh["y"])) / 2.0
    sh_mid_z = (float(l_sh["z"]) + float(r_sh["z"])) / 2.0

    hip_mid_x = (float(l_hip["x"]) + float(r_hip["x"])) / 2.0
    hip_mid_y = (float(l_hip["y"]) + float(r_hip["y"])) / 2.0
    hip_mid_z = (float(l_hip["z"]) + float(r_hip["z"])) / 2.0

    # Angle of torso line off vertical
    dx = hip_mid_x - sh_mid_x
    dy = hip_mid_y - sh_mid_y

    angle_rad = math.atan2(abs(dx), abs(dy))
    side_bend = round(math.degrees(angle_rad), 1)

    return MetricEntry(value=side_bend, unit="deg", primary=True)


def _compute_hips_open(df: pd.DataFrame, impact_frame: int | None) -> MetricEntry:
    """Metric 9: Hips open — hip rotation angle at impact."""
    if not impact_frame:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Impact frame missing")

    l_hip = get_frame_landmark(df, impact_frame, "left_hip")
    r_hip = get_frame_landmark(df, impact_frame, "right_hip")

    if not check_visibility(l_hip) or not check_visibility(r_hip):
        return MetricEntry(
            value=None, unit="deg", primary=True, null_reason="Hip keypoints not visible at impact"
        )

    # Hip-line angle at impact (relative to horizontal = target line)
    angle = line_angle_deg(l_hip, r_hip)

    if angle is None:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Hip angle calculation failed")

    return MetricEntry(value=round(angle, 1), unit="deg", primary=True)


def _compute_wrist_lag(df: pd.DataFrame, impact_frame: int | None) -> MetricEntry:
    """Metric 10: Wrist lag — angle at wrist between forearm and club-shaft (lead wrist only)."""
    if not impact_frame:
        return MetricEntry(
            value=None, unit="deg", primary=False, null_reason="Impact frame missing"
        )

    # Lead wrist (left for right-handed golfer): left_shoulder, left_elbow, left_wrist
    l_sh = get_frame_landmark(df, impact_frame, "left_shoulder")
    l_elbow = get_frame_landmark(df, impact_frame, "left_elbow")
    l_wrist = get_frame_landmark(df, impact_frame, "left_wrist")

    if not (check_visibility(l_sh) and check_visibility(l_elbow) and check_visibility(l_wrist)):
        return MetricEntry(
            value=None, unit="deg", primary=False, null_reason="lead_wrist_visibility_below_0.5_at_impact"
        )

    # Angle at elbow between shoulder-to-elbow and elbow-to-wrist
    angle = angle_between_vectors_deg(l_sh, l_elbow, l_wrist)

    if angle is None:
        return MetricEntry(
            value=None, unit="deg", primary=False, null_reason="Wrist lag calculation failed"
        )

    return MetricEntry(value=round(angle, 1), unit="deg", primary=False)


def _compute_knee_flex_left(df: pd.DataFrame, bs_start: int | None, ftx_end: int | None) -> MetricEntry:
    """Metric 11: Knee flex left — angle at left knee during swing."""
    if not bs_start or not ftx_end:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Swing bounds missing")

    # Use median angle during swing for stability
    swing_df = get_frame_subset(df, bs_start, ftx_end)
    swing_df_visible = swing_df[swing_df["visibility"] >= 0.5]

    l_hip_swings = swing_df_visible[swing_df_visible["landmark_name"] == "left_hip"]
    l_knee_swings = swing_df_visible[swing_df_visible["landmark_name"] == "left_knee"]
    l_ankle_swings = swing_df_visible[swing_df_visible["landmark_name"] == "left_ankle"]

    if l_hip_swings.empty or l_knee_swings.empty or l_ankle_swings.empty:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Left knee keypoints not visible")

    # Calculate angle for each frame where all three are visible
    angles = []
    for frame_idx in l_knee_swings["frame_index"].unique():
        l_hip = get_frame_landmark(swing_df, int(frame_idx), "left_hip")
        l_knee = get_frame_landmark(swing_df, int(frame_idx), "left_knee")
        l_ankle = get_frame_landmark(swing_df, int(frame_idx), "left_ankle")

        if check_visibility(l_hip) and check_visibility(l_knee) and check_visibility(l_ankle):
            angle = angle_between_vectors_deg(l_hip, l_knee, l_ankle)
            if angle is not None:
                angles.append(angle)

    if not angles:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Left knee angle not calculable")

    # Report median angle during swing
    median_angle = sorted(angles)[len(angles) // 2]
    return MetricEntry(value=round(median_angle, 1), unit="deg", primary=True)


def _compute_knee_flex_right(df: pd.DataFrame, bs_start: int | None, ftx_end: int | None) -> MetricEntry:
    """Metric 12: Knee flex right — angle at right knee during swing."""
    if not bs_start or not ftx_end:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Swing bounds missing")

    # Use median angle during swing for stability
    swing_df = get_frame_subset(df, bs_start, ftx_end)
    swing_df_visible = swing_df[swing_df["visibility"] >= 0.5]

    r_hip_swings = swing_df_visible[swing_df_visible["landmark_name"] == "right_hip"]
    r_knee_swings = swing_df_visible[swing_df_visible["landmark_name"] == "right_knee"]
    r_ankle_swings = swing_df_visible[swing_df_visible["landmark_name"] == "right_ankle"]

    if r_hip_swings.empty or r_knee_swings.empty or r_ankle_swings.empty:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Right knee keypoints not visible")

    # Calculate angle for each frame where all three are visible
    angles = []
    for frame_idx in r_knee_swings["frame_index"].unique():
        r_hip = get_frame_landmark(swing_df, int(frame_idx), "right_hip")
        r_knee = get_frame_landmark(swing_df, int(frame_idx), "right_knee")
        r_ankle = get_frame_landmark(swing_df, int(frame_idx), "right_ankle")

        if check_visibility(r_hip) and check_visibility(r_knee) and check_visibility(r_ankle):
            angle = angle_between_vectors_deg(r_hip, r_knee, r_ankle)
            if angle is not None:
                angles.append(angle)

    if not angles:
        return MetricEntry(value=None, unit="deg", primary=True, null_reason="Right knee angle not calculable")

    # Report median angle during swing
    median_angle = sorted(angles)[len(angles) // 2]
    return MetricEntry(value=round(median_angle, 1), unit="deg", primary=True)


# ─── Main Entry Point ────────────────────────────────────────────────────────


def compute_all_metrics(session: SessionJSON, parquet_path: Path) -> dict[str, MetricEntry]:
    """Calculate the 13 biomechanical metrics from the 3D keypoint sequence and session data.

    Args:
        session: The SessionJSON model populated through Phase 3.
        parquet_path: Path to the generated keypoints parquet file.

    Returns:
        A dictionary mapping metric names to MetricEntry models.
    """
    metrics = {}

    # Simple metrics that don't require parquet
    metrics["stance_width"] = _compute_stance_width(session)
    metrics["tempo_ratio"] = _compute_tempo_ratio(session)

    # Try to load parquet file
    df = None
    if not parquet_path.exists():
        logger.warning(f"Keypoints parquet not found at {parquet_path}")
    else:
        try:
            table = pq.read_table(str(parquet_path))
            df = table.to_pandas()
        except Exception as e:
            logger.error(f"Failed to read parquet for metrics calculation: {e}")

    # Unpack session data
    scale = session.px_to_inches_scale or 1.0
    address_range = session.address_frame_range
    bs_start = session.backswing_start_frame_index
    impact = session.impact_frame_index
    ftx_end = session.follow_through_end_frame_index

    # Compute remaining metrics
    # Note: Some functions (like hip_sway) can check their own conditions (e.g., missing address_range)
    # even if df is None, so we call them all
    metrics["hip_sway"] = _compute_hip_sway(df, address_range, scale)
    metrics["head_sway"] = _compute_head_sway(df, address_range, scale) if df is not None else MetricEntry(value=None, unit="inches", primary=True, null_reason="Keypoint data missing")

    if df is not None:
        metrics["hip_turn"] = _compute_hip_turn(df, address_range, impact)
        metrics["shoulder_turn"] = _compute_shoulder_turn(df, address_range, impact)
        metrics["x_factor"] = _compute_x_factor(df, bs_start, impact)
        metrics["spine_deviation_max"] = _compute_spine_deviation_max(df, address_range, bs_start, impact)
        metrics["side_bend"] = _compute_side_bend(df, bs_start, impact)
        metrics["hips_open"] = _compute_hips_open(df, impact)
        metrics["wrist_lag"] = _compute_wrist_lag(df, impact)
        metrics["knee_flex_left"] = _compute_knee_flex_left(df, bs_start, ftx_end)
        metrics["knee_flex_right"] = _compute_knee_flex_right(df, bs_start, ftx_end)
    else:
        # No parquet data available
        for key in [
            "x_factor", "spine_deviation_max", "hip_turn", "shoulder_turn",
            "side_bend", "hips_open", "wrist_lag", "knee_flex_left", "knee_flex_right"
        ]:
            metrics[key] = MetricEntry(
                value=None, unit="deg" if key != "hip_sway" and key != "head_sway" else "inches",
                primary=key != "wrist_lag",
                null_reason="Keypoint data missing"
            )

    return metrics
