"""Keypoints extraction — Phase 2 core logic.

Carried over from v0.2.0.  If output does not conform to
data-schema.md §4, write an adapter in ``backend/core/keypoints_store.py``
instead of modifying this file.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe.python.solutions.pose as mp_pose
import pyarrow as pa
import pyarrow.parquet as pq

from backend.core.logging import get_logger

logger = get_logger(__name__)


def extract_keypoints(
    video_path: Path, output_parquet: Path, start_frame: int, end_frame: int
) -> int:
    """Run MediaPipe on bounding frames and save 33 landmarks + v as Parquet.

    Args:
        video_path: Path to the input video.
        output_parquet: Destination for the parquet file.
        start_frame: Start of the target segment (e.g. backswing start).
        end_frame: End of the target segment (e.g. follow through end).

    Returns:
        Number of valid rows written.
    """
    cap = cv2.VideoCapture(str(video_path))
    pose = mp_pose.Pose(static_image_mode=False, model_complexity=1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    
    # 10 frame margin on both sides per the spec
    eff_start = max(0, start_frame - 10)
    eff_end = min(total_frames - 1, end_frame + 10)

    data = []
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, eff_start)
    for frame_idx in range(eff_start, eff_end + 1):
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = pose.process(rgb)

        if result.pose_landmarks:
            for lm_id, lm in enumerate(result.pose_landmarks.landmark):
                name = mp_pose.PoseLandmark(lm_id).name.lower()
                data.append({
                    "frame_index": frame_idx,
                    "landmark_id": lm_id,
                    "landmark_name": name,
                    "x": lm.x,
                    "y": lm.y,
                    "z": lm.z,
                    "visibility": lm.visibility
                })

    cap.release()
    pose.close()

    if not data:
        logger.warning(f"No keypoints extracted between {eff_start} and {eff_end}")
        return 0

    table = pa.Table.from_pylist(data)
    pq.write_table(table, output_parquet)
    logger.info(f"Wrote {len(data)} keypoints rows to {output_parquet.name}")

    return len(data)

