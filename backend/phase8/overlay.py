"""Annotated video overlay — Phase 8 core logic.

Renders MediaPipe skeleton overlays onto the original video returning `annotated.mp4`.
"""

from __future__ import annotations

import cv2
import pyarrow.parquet as pq
from pathlib import Path
from backend.core.logging import get_logger

logger = get_logger(__name__)


def render_overlay(
    input_video: Path,
    output_video: Path,
    parquet_path: Path,
    start_frame: int,
    end_frame: int
) -> bool:
    """Render the skeleton keypoints sequentially back over the video bounds.

    Args:
        input_video: Path to input mp4.
        output_video: Path to write annotated.mp4
        parquet_path: Path to keypoints parquet file.
        start_frame: Start of segment.
        end_frame: End of segment.
        
    Returns:
        True if successfully rendered.
    """
    if not input_video.exists() or not parquet_path.exists():
        return False

    try:
        table = pq.read_table(str(parquet_path))
        df = table.to_pandas()
    except Exception as e:
        logger.error(f"Failed to read parquet for overlay: {e}")
        return False
        
    if df.empty:
        return False

    cap = cv2.VideoCapture(str(input_video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # type: ignore
    out = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    current_frame = start_frame
    
    # We define simple MediaPipe pose connections to draw
    # These are landmark indices (e.g. 11->12 is left_shoulder to right_shoulder)
    connections = [
        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
        (11, 23), (12, 24), (23, 24), (23, 25), (25, 27),
        (24, 26), (26, 28)
    ]
    
    while current_frame <= end_frame:
        ret, frame = cap.read()
        if not ret or frame is None:
            break
            
        # Get frame data
        f_df = df[df["frame_index"] == current_frame]
        
        if not f_df.empty:
            positions = {}
            for _, row in f_df.iterrows():
                if row["visibility"] > 0.5:
                    px = int(row["x"] * width)
                    py = int(row["y"] * height)
                    positions[row["landmark_id"]] = (px, py)
                    cv2.circle(frame, (px, py), 4, (0, 255, 0), -1)
                    
            for p1, p2 in connections:
                if p1 in positions and p2 in positions:
                    cv2.line(frame, positions[p1], positions[p2], (0, 0, 255), 2)
        
        out.write(frame)
        current_frame += 1

    cap.release()
    out.release()

    return output_video.exists()
