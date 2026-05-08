"""Shared test fixtures and configuration.

Agents are never tested against the real Anthropic API.
See testing.md §1.
"""

from __future__ import annotations

import os
# Set env vars BEFORE any backend imports so backend.main.py -> get_settings() succeeds
os.environ["GEMINI_API_KEY"] = "test-key-not-real"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_LOCAL_PATH"] = "./storage"

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from backend.core.config import Settings
from backend.core.storage import LocalStorage


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Return settings configured for testing with a temp storage directory.

    Args:
        tmp_path: Pytest temp directory fixture.

    Returns:
        Test ``Settings`` instance.
    """
    return Settings(
        gemini_api_key="test-key-not-real",
        gemini_model="gemini-2.5-flash",
        storage_backend="local",
        storage_local_path=str(tmp_path / "storage"),
        max_upload_mb=10,
        max_video_seconds=30,
        frontend_url="http://localhost:3000",
    )


@pytest.fixture
def test_storage(test_settings: Settings) -> LocalStorage:
    """Return a storage adapter using a temp directory.

    Args:
        test_settings: Test settings fixture.

    Returns:
        ``LocalStorage`` instance.
    """
    return LocalStorage(test_settings)


@pytest.fixture
def client(test_settings: Settings) -> Generator[TestClient, None, None]:
    """Return a FastAPI test client with overridden dependencies.

    Args:
        test_settings: Test settings fixture.

    Yields:
        A ``TestClient`` instance.
    """
    from backend.api.deps import get_settings, get_storage
    from backend.main import app
    from unittest.mock import patch, MagicMock

    storage = LocalStorage(test_settings)

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_storage] = lambda: storage

    with patch("backend.orchestrator.pipeline.run_pipeline", MagicMock()):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory.

    Returns:
        Absolute path to ``backend/tests/fixtures/``.
    """
    return Path(__file__).parent / "fixtures"


# ─── Test Helpers for Biomechanical Metrics ──────────────────────────────────


def create_synthetic_keypoints(
    parquet_path: Path,
    num_frames: int = 100,
    ankles_distance_px: float = 100.0,
    visibility: float = 0.9,
    override_visibilities: dict[str, float] | None = None,
    frame_ranges: dict[str, tuple[int, int]] | None = None,
) -> None:
    """Create a synthetic keypoint parquet file for testing.

    Generates all 33 MediaPipe pose landmarks across N frames with reasonable
    default positions. Allows overriding specific landmark visibilities and
    frame-ranges for edge case testing.

    Args:
        parquet_path: Where to write the parquet file.
        num_frames: Number of frames to generate (default 100).
        ankles_distance_px: Distance between ankles in pixels (affects stance_width).
        visibility: Default visibility score (0.0–1.0). Set to 0.9 for valid landmarks.
        override_visibilities: Dict mapping landmark_name → visibility. Overrides default.
        frame_ranges: Dict mapping landmark_name → (start_frame, end_frame) for variable
                     visibility across frames (e.g., to simulate occlusion).

    Returns:
        None. Writes parquet file to parquet_path.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    override_visibilities = override_visibilities or {}
    frame_ranges = frame_ranges or {}

    # MediaPipe 33 landmarks
    landmark_names = [
        "nose", "left_eye_inner", "left_eye", "left_eye_outer",
        "right_eye_inner", "right_eye", "right_eye_outer",
        "left_ear", "right_ear", "mouth_left", "mouth_right",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_pinky", "right_pinky",
        "left_index", "right_index", "left_thumb", "right_thumb",
        "left_hip", "right_hip", "left_knee", "right_knee",
        "left_ankle", "right_ankle", "left_heel", "right_heel",
        "left_foot_index", "right_foot_index"
    ]

    data = []
    for frame_idx in range(num_frames):
        for lm_id, lm_name in enumerate(landmark_names):
            # Default positions (normalized 0.0–1.0)
            if lm_name == "left_ankle":
                x, y = 0.4, 0.95
            elif lm_name == "right_ankle":
                x, y = 0.4 + (ankles_distance_px / 1920.0), 0.95  # Assume 1920 width
            elif lm_name == "left_hip":
                x, y = 0.45, 0.65
            elif lm_name == "right_hip":
                x, y = 0.55, 0.65
            elif lm_name == "left_shoulder":
                x, y = 0.4, 0.35
            elif lm_name == "right_shoulder":
                x, y = 0.6, 0.35
            elif lm_name == "nose":
                x, y = 0.5, 0.2
            elif lm_name.startswith("left_"):
                x, y = 0.4, 0.5
            elif lm_name.startswith("right_"):
                x, y = 0.6, 0.5
            else:
                x, y = 0.5, 0.5

            # Determine visibility for this landmark in this frame
            vis = visibility
            if lm_name in override_visibilities:
                vis = override_visibilities[lm_name]
            elif lm_name in frame_ranges:
                start_frame, end_frame = frame_ranges[lm_name]
                if frame_idx < start_frame or frame_idx > end_frame:
                    vis = 0.1  # Low visibility outside range
                else:
                    vis = visibility  # High visibility in range

            data.append({
                "frame_index": frame_idx,
                "landmark_id": lm_id,
                "landmark_name": lm_name,
                "x": x,
                "y": y,
                "z": 0.0,  # Placeholder depth
                "visibility": vis,
            })

    table = pa.Table.from_pylist(data)
    pq.write_table(table, parquet_path)
