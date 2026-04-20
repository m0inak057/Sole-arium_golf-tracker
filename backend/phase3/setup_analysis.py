"""Setup metrics — Phase 3 core logic.

Calculates static metrics about the golfer's stance and posture before the swing begins.
"""

from __future__ import annotations

import math
from pathlib import Path

import pyarrow.parquet as pq
from pydantic import BaseModel

from backend.core.logging import get_logger

logger = get_logger(__name__)


class SetupMetrics(BaseModel):
    stance_width_px: float | None = None
    ball_position_ratio: float | None = None
    spine_tilt_deg_at_address: float | None = None
    grip_position: str | None = None


def run_setup_analysis(
    parquet_path: Path,
    address_range: list[int] | None,
    px_to_inches_scale: float,
    camera_angle: str,
    resolution: dict[str, int]
) -> SetupMetrics:
    """Read keypoints from Parquet and compute address setup metrics.

    Args:
        parquet_path: Path to the written keypoints parquet file.
        address_range: [start_index, end_index] of standing still frames.
        px_to_inches_scale: Pixel to inches multiplier from Agent 2.
        camera_angle: 'face_on' or 'down_the_line' from Agent 1.
        resolution: {'width': int, 'height': int} from Agent 1.

    Returns:
        Pydantic model of Phase 3 metrics.
    """
    if not parquet_path.exists() or not address_range:
        return SetupMetrics()

    try:
        table = pq.read_table(str(parquet_path))
        df = table.to_pandas()
    except Exception as e:
        logger.error(f"Failed to read parquet: {e}")
        return SetupMetrics()

    if df.empty:
        return SetupMetrics()

    start, end = min(address_range), max(address_range)
    # Filter for address frames
    df_addr = df[(df["frame_index"] >= start) & (df["frame_index"] <= end)]

    if df_addr.empty:
        return SetupMetrics()

    metrics = SetupMetrics()

    # Median positions across the address frames
    med = df_addr.groupby("landmark_name")[["x", "y", "z"]].median()
    
    width = resolution.get("width", 1000)
    height = resolution.get("height", 1000)

    if camera_angle == "face_on":
        # Stance width: distance between ankles (27, 28)
        if "left_ankle" in med.index and "right_ankle" in med.index:
            l_an = med.loc["left_ankle"]
            r_an = med.loc["right_ankle"]
            
            # Distance in pixels
            dist_px = math.hypot((l_an.x - r_an.x) * width, (l_an.y - r_an.y) * height)
            metrics.stance_width_px = round(dist_px, 2)
            
            # ball position ratio (towards front ankle = 1.0)
            metrics.ball_position_ratio = round((l_an.x + r_an.x) / 2.0, 2)

    elif camera_angle == "down_the_line":
        # Spine tilt: angle of shoulder to hip line off the vertical
        if "right_shoulder" in med.index and "right_hip" in med.index:
            r_sh = med.loc["right_shoulder"]
            r_hip = med.loc["right_hip"]
            
            # Pixel coords
            rx_sh, ry_sh = r_sh.x * width, r_sh.y * height
            rx_hip, ry_hip = r_hip.x * width, r_hip.y * height
            
            dx = rx_hip - rx_sh
            dy = ry_hip - ry_sh
            
            angle_rad = math.atan2(abs(dx), abs(dy))
            metrics.spine_tilt_deg_at_address = round(math.degrees(angle_rad), 2)

    return metrics
