"""Keypoints store — read/write keypoint data in Parquet format.

Keypoints live outside the session JSON because they are large.
See data-schema.md §4 for the schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from backend.core.logging import get_logger, log_event

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def keypoints_path(session_dir: Path) -> Path:
    """Return the canonical path for the keypoints Parquet file.

    Args:
        session_dir: The session's storage directory.

    Returns:
        Path to ``keypoints.parquet`` inside the session directory.
    """
    return session_dir / "keypoints.parquet"


# Placeholder — full implementation in Sprint 2 when Phase 2 is wired.
# The parquet schema is:
#   frame_index (int), landmark_id (int),
#   x_norm (float), y_norm (float), z_norm (float), visibility (float)
