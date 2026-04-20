"""Agent 1 — Video Intelligence.

Reads video metadata and a sampled keypoint geometry, classifies camera angle,
and scores video quality. See agent-prompts.md §Agent 1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import cv2
import mediapipe.python.solutions.pose as mp_pose
from pydantic import BaseModel

from backend.agents.base import BaseAgent
from backend.core.logging import get_logger

logger = get_logger(__name__)


class ResolutionModel(BaseModel):
    width: int
    height: int


class Agent1Response(BaseModel):
    """Pydantic model for Agent 1's expected JSON output."""
    input_fps: float
    camera_angle: Literal["face_on", "down_the_line"]
    video_quality_score: float
    resolution: ResolutionModel
    agent1_notes: str


class VideoIntelligenceAgent(BaseAgent):
    """Agent 1 implementation."""

    @property
    def agent_number(self) -> int:
        return 1

    @property
    def response_model(self) -> type[BaseModel]:
        return Agent1Response

    @property
    def system_prompt(self) -> str:
        return (
            "You are Agent 1 in the Golf Trainer AI pipeline. Your only job is to analyse metadata\n"
            "and sampled keypoint geometry from an uploaded golf swing video, and return a strict\n"
            "JSON object describing it. Never output prose. Never output markdown fences. Only a\n"
            "single valid JSON object matching the schema below.\n\n"
            "Output JSON schema:\n"
            "{\n"
            '  "input_fps": <number>,\n'
            '  "camera_angle": "face_on" | "down_the_line",\n'
            '  "video_quality_score": <number between 0.0 and 1.0>,\n'
            '  "resolution": { "width": <int>, "height": <int> },\n'
            '  "agent1_notes": "<one or two short sentences>"\n'
            "}\n\n"
            "How to decide camera_angle:\n"
            "- face_on: shoulders roughly horizontal in the frame; hip line roughly horizontal;\n"
            "  nose, torso, and pelvis roughly centred; both feet visible side-by-side.\n"
            "- down_the_line: golfer's torso roughly perpendicular to camera (one shoulder much\n"
            "  closer to camera than the other); ball target line recedes into the frame.\n\n"
            "How to score video_quality:\n"
            "- 1.0: 60+ fps, crisp lighting, static camera, golfer fully in frame.\n"
            "- 0.5: adequate framing, 30fps, minor camera shake, some shadow.\n"
            "- 0.0: severe camera motion, golfer partly out of frame, blurred keypoints, <24 fps."
        )

    def build_user_prompt(self, session_data: dict[str, Any]) -> str:
        """Assemble the user prompt. For Agent 1, metadata comes packed in session_data."""
        return (
            f"Metadata:\n"
            f"  FPS: {session_data.get('fps', 0)}\n"
            f"  Resolution: {session_data.get('width', 0)}x{session_data.get('height', 0)}\n"
            f"  Duration seconds: {session_data.get('duration_seconds', 0)}\n\n"
            f"Sampled keypoint geometry (5 frames spread across the video):\n"
            f"{json.dumps(session_data.get('geometry_samples', []), indent=2)}"
        )


def analyze_video_intelligence(video_path: Path, settings: Any = None) -> dict[str, Any]:
    """Helper to extract video metadata and 5 geometry samples for Agent 1.

    Args:
        video_path: Path to the input video.
        settings: Application settings.

    Returns:
        A dict matching what VideoIntelligenceAgent.build_user_prompt expects.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0 or frame_count <= 0:
        cap.release()
        raise ValueError("Unreadable video metadata")

    duration_seconds = frame_count / fps

    # Sample 5 frames
    sample_indices = [
        0,
        frame_count // 4,
        frame_count // 2,
        3 * frame_count // 4,
        frame_count - 1,
    ]

    pose = mp_pose.Pose(static_image_mode=True, model_complexity=1)

    geometry_samples = []

    for idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = pose.process(rgb)

        sample_data = {"frame_index": idx, "landmarks": {}}
        if result.pose_landmarks:
            for lm_id, lm in enumerate(result.pose_landmarks.landmark):
                # We only need the primary joints for camera angle classification
                # 11: left shoulder, 12: right shoulder, 23: left hip, 24: right hip
                # 0: nose, 27: left ankle, 28: right ankle
                if lm_id in (0, 11, 12, 23, 24, 27, 28):
                    name = mp_pose.PoseLandmark(lm_id).name.lower()
                    sample_data["landmarks"][name] = {
                        "x": round(lm.x, 3),
                        "y": round(lm.y, 3),
                        "z": round(lm.z, 3),
                        "visibility": round(lm.visibility, 3),
                    }
        geometry_samples.append(sample_data)

    cap.release()
    pose.close()

    return {
        "fps": round(fps, 2),
        "width": width,
        "height": height,
        "duration_seconds": round(duration_seconds, 2),
        "geometry_samples": geometry_samples,
    }

