"""Agent 2 — Body Calibration.

Analyzes median keypoints from address frames to estimate the golfer's proportions
and returns a pixel-to-inches multiplier.
"""

from __future__ import annotations

from typing import Any
import math
from pathlib import Path
import numpy as np
import cv2
import mediapipe.python.solutions.pose as mp_pose
from pydantic import BaseModel

from backend.agents.base import BaseAgent


class Agent2Response(BaseModel):
    """Pydantic model for Agent 2's expected JSON output."""
    px_to_inches_scale: float
    calibration_low_confidence: bool
    calibration_notes: str


class BodyCalibrationAgent(BaseAgent):
    """Agent 2 implementation."""

    @property
    def agent_number(self) -> int:
        return 2

    @property
    def response_model(self) -> type[BaseModel]:
        return Agent2Response

    @property
    def system_prompt(self) -> str:
        return (
            "You are Agent 2 in the Golf Trainer AI pipeline. Your only job is to derive a\n"
            "personalised pixel-to-real-world scale for this golfer from their address-frame\n"
            "keypoint distances. Never output prose or markdown. Only one JSON object.\n\n"
            "Output JSON schema:\n"
            "{\n"
            '  "px_to_inches_scale": <number, inches per pixel>,\n'
            '  "calibration_low_confidence": <bool>,\n'
            '  "calibration_notes": "<one or two short sentences>"\n'
            "}\n\n"
            "Reasoning approach:\n"
            "- Use shoulder-width pixel distance from address frames as the primary anchor.\n"
            "- The golfer's real shoulder width is derived from their gender and the observed\n"
            "  torso proportions — use population reference points but prefer the observed\n"
            "  torso-to-shoulder ratio to refine.\n"
            "- If fewer than 10 address frames are stable, set calibration_low_confidence=true\n"
            "  and use a conservative population-mean default (male 18 in, female 16 in).\n"
            "  This is the sole permitted fallback — all downstream code still reads\n"
            "  px_to_inches_scale from the session JSON, never its own constant.\n"
            "- Return notes explaining what distance was used as the anchor."
        )

    def build_user_prompt(self, session_data: dict[str, Any]) -> str:
        """Assemble the user prompt. For Agent 2, stats come packed in session_data."""
        return (
            f"Gender: {session_data.get('gender', 'unknown')}\n"
            f"Camera angle (from Agent 1): {session_data.get('camera_angle', 'unknown')}\n\n"
            f"Address-frame keypoint measurements (N={session_data.get('n_address_frames', 0)} frames):\n"
            f"  Median shoulder-width px: {session_data.get('med_shoulder_px', 0.0)}\n"
            f"  Std shoulder-width px: {session_data.get('std_shoulder_px', 0.0)}\n"
            f"  Median torso length px: {session_data.get('med_torso_px', 0.0)}\n"
            f"  Median arm length px: {session_data.get('med_arm_px', 0.0)}"
        )


def extract_address_measurements(
    video_path: Path, address_range: list[int]
) -> dict[str, Any]:
    """Helper to extract physical measurements across address frames."
    Runs MediaPipe on valid address frames, calculating distances.
    """
    if not address_range or len(address_range) != 2:
        return {"n_address_frames": 0}

    start_frame, end_frame = address_range
    if end_frame < start_frame:
        start_frame, end_frame = end_frame, start_frame

    # Sample at most 30 frames from address range to keep it fast
    num_frames = max(1, end_frame - start_frame)
    step = 1 if num_frames <= 30 else max(1, num_frames // 30)

    cap = cv2.VideoCapture(str(video_path))
    pose = mp_pose.Pose(static_image_mode=False, model_complexity=1)

    shoulder_dists = []
    torso_dists = []
    arm_dists = []

    valid_frames = 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    # Needs width/height to convert normalized coordinates to px
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    for frame_idx in range(start_frame, end_frame + 1, step):
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = pose.process(rgb)

        if result.pose_landmarks:
            valid_frames += 1
            lms = result.pose_landmarks.landmark
            
            def ppx(idx: int) -> tuple[float, float]:
                return lms[idx].x * width, lms[idx].y * height

            # Shoulders (11 left, 12 right)
            l_sh = ppx(11)
            r_sh = ppx(12)
            sh_px = math.hypot(l_sh[0] - r_sh[0], l_sh[1] - r_sh[1])
            shoulder_dists.append(sh_px)

            # Torso (mid-shoulder to mid-hip)
            l_hip = ppx(23)
            r_hip = ppx(24)
            mid_sh = ((l_sh[0] + r_sh[0]) / 2, (l_sh[1] + r_sh[1]) / 2)
            mid_hip = ((l_hip[0] + r_hip[0]) / 2, (l_hip[1] + r_hip[1]) / 2)
            torso_px = math.hypot(mid_sh[0] - mid_hip[0], mid_sh[1] - mid_hip[1])
            torso_dists.append(torso_px)

            # Arm (shoulder to wrist approx) -> Using left arm
            l_wrist = ppx(15)
            arm_px = math.hypot(l_sh[0] - l_wrist[0], l_sh[1] - l_wrist[1])
            arm_dists.append(arm_px)
            
        if step > 1:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx + step)

    cap.release()
    pose.close()

    if not shoulder_dists:
        return {"n_address_frames": 0}

    return {
        "n_address_frames": valid_frames,
        "med_shoulder_px": round(float(np.median(shoulder_dists)), 2),
        "std_shoulder_px": round(float(np.std(shoulder_dists)), 2),
        "med_torso_px": round(float(np.median(torso_dists)), 2),
        "med_arm_px": round(float(np.median(arm_dists)), 2),
    }
