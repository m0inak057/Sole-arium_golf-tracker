"""Local filesystem storage adapter.

Handles session folder layout: ``storage/{session_id}/{input.mp4, session.json, …}``
— see rules.md §5.

Writes to ``session.json`` are **atomic**: write to ``.tmp`` then rename.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from backend.core.config import Settings, get_settings
from backend.core.logging import get_logger, log_event
from backend.core.session import SessionJSON

logger = get_logger(__name__)


class LocalStorage:
    """Filesystem-backed storage for sessions, videos and artefacts."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._base = Path(self._settings.storage_local_path).resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    # ── Paths ────────────────────────────────────────────────────────

    def session_dir(self, session_id: str) -> Path:
        """Return the directory for a given session, creating it if needed.

        Args:
            session_id: UUID of the session.

        Returns:
            Absolute ``Path`` to ``storage/{session_id}/``.
        """
        d = self._base / session_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def session_json_path(self, session_id: str) -> Path:
        """Return the path to the session JSON file.

        Args:
            session_id: UUID of the session.

        Returns:
            Path to ``storage/{session_id}/session.json``.
        """
        return self.session_dir(session_id) / "session.json"

    def input_video_path(self, session_id: str, angle: str | None = None) -> Path:
        """Return the path where the uploaded video is stored.

        Args:
            session_id: UUID of the session.
            angle: Camera angle ("face_on" or "down_the_line") for dual video mode.
                  If None, returns legacy single video path.

        Returns:
            Path to the input video file.
        """
        if angle is None:
            # Legacy single video mode
            return self.session_dir(session_id) / "input.mp4"
        elif angle == "face_on":
            return self.session_dir(session_id) / "input_face_on.mp4"
        elif angle == "down_the_line":
            return self.session_dir(session_id) / "input_down_the_line.mp4"
        else:
            raise ValueError(f"Invalid angle: {angle}. Must be 'face_on' or 'down_the_line'")

    def get_input_video_paths(self, session_id: str) -> dict[str, Path]:
        """Get all available input video paths for a session.
        
        Args:
            session_id: UUID of the session.
            
        Returns:
            Dictionary mapping angle names to paths for existing videos.
        """
        paths = {}
        
        # Check for dual video files
        face_on_path = self.input_video_path(session_id, "face_on")
        if face_on_path.exists():
            paths["face_on"] = face_on_path
            
        down_the_line_path = self.input_video_path(session_id, "down_the_line")
        if down_the_line_path.exists():
            paths["down_the_line"] = down_the_line_path
            
        # Check for legacy single video
        legacy_path = self.input_video_path(session_id, None)
        if legacy_path.exists() and not paths:
            # Only use legacy if no dual videos exist
            paths["legacy"] = legacy_path
            
        return paths

    def agents_dir(self, session_id: str) -> Path:
        """Return the agents debug directory, creating it if needed.

        Args:
            session_id: UUID of the session.

        Returns:
            Path to ``storage/{session_id}/agents/``.
        """
        d = self.session_dir(session_id) / "agents"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── Session JSON ─────────────────────────────────────────────────

    def save_session(self, session: SessionJSON) -> Path:
        """Persist the session JSON atomically (write-to-tmp then rename).

        Args:
            session: The session model to persist.

        Returns:
            Path to the written ``session.json``.
        """
        path = self.session_json_path(session.session_id)
        tmp_path = path.with_suffix(".json.tmp")
        data = session.model_dump(mode="json")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        # Atomic rename (same filesystem)
        tmp_path.replace(path)
        log_event(
            logger,
            "Session JSON saved",
            session_id=session.session_id,
            event="session_saved",
        )
        return path

    def load_session(self, session_id: str) -> SessionJSON:
        """Load a session JSON from disk.

        Args:
            session_id: UUID of the session.

        Returns:
            Parsed ``SessionJSON``.

        Raises:
            FileNotFoundError: If the session JSON does not exist.
        """
        path = self.session_json_path(session_id)
        raw = json.loads(path.read_text(encoding="utf-8"))
        return SessionJSON.model_validate(raw)

    def session_exists(self, session_id: str) -> bool:
        """Check whether a session JSON exists on disk.

        Args:
            session_id: UUID of the session.

        Returns:
            ``True`` if ``session.json`` exists.
        """
        return self.session_json_path(session_id).is_file()

    # ── Video I/O ────────────────────────────────────────────────────

    async def save_upload(self, session_id: str, content: bytes, extension: str = ".mp4", angle: str | None = None) -> Path:
        """Persist an uploaded video file.

        Args:
            session_id: UUID of the session.
            content: Raw file bytes.
            extension: File extension (default ``.mp4``).
            angle: Camera angle for dual video mode ("face_on" or "down_the_line").
                  If None, saves as legacy single video.

        Returns:
            Path to the saved file.
        """
        if angle is None:
            # Legacy single video mode
            dest = self.session_dir(session_id) / f"input{extension}"
        elif angle == "face_on":
            dest = self.session_dir(session_id) / f"input_face_on{extension}"
        elif angle == "down_the_line":
            dest = self.session_dir(session_id) / f"input_down_the_line{extension}"
        else:
            raise ValueError(f"Invalid angle: {angle}. Must be 'face_on' or 'down_the_line'")
            
        dest.write_bytes(content)
        log_event(
            logger,
            f"Upload saved ({len(content)} bytes)" + (f" - {angle}" if angle else ""),
            session_id=session_id,
            event="upload_saved",
            angle=angle,
        )
        return dest

    async def save_dual_upload(self, session_id: str, face_on_content: bytes, down_the_line_content: bytes, extension: str = ".mp4") -> tuple[Path, Path]:
        """Persist both video files for dual video mode.

        Args:
            session_id: UUID of the session.
            face_on_content: Raw bytes for face-on video.
            down_the_line_content: Raw bytes for down-the-line video.
            extension: File extension (default ``.mp4``).

        Returns:
            Tuple of (face_on_path, down_the_line_path).
        """
        face_on_path = await self.save_upload(session_id, face_on_content, extension, "face_on")
        down_the_line_path = await self.save_upload(session_id, down_the_line_content, extension, "down_the_line")
        
        log_event(
            logger,
            f"Dual video upload saved (face_on: {len(face_on_content)} bytes, down_the_line: {len(down_the_line_content)} bytes)",
            session_id=session_id,
            event="dual_upload_saved",
        )
        
        return face_on_path, down_the_line_path

    def get_video_path(self, session_id: str, kind: str, angle: str | None = None) -> Path | None:
        """Return a video path if the file exists.

        Args:
            session_id: UUID of the session.
            kind: One of ``"input"``, ``"slowmo"``, ``"annotated"``.
            angle: Camera angle for dual video mode ("face_on" or "down_the_line").
                  If None, returns legacy single video path.

        Returns:
            Path if the file exists, else ``None``.
        """
        if angle is None:
            # Legacy single video mode
            filenames = {
                "input": "input.mp4",
                "slowmo": "slowmo.mp4",
                "annotated": "annotated.mp4",
            }
        else:
            # Dual video mode
            if angle == "face_on":
                filenames = {
                    "input": "input_face_on.mp4",
                    "slowmo": "slowmo_face_on.mp4",
                    "annotated": "annotated_face_on.mp4",
                }
            elif angle == "down_the_line":
                filenames = {
                    "input": "input_down_the_line.mp4",
                    "slowmo": "slowmo_down_the_line.mp4",
                    "annotated": "annotated_down_the_line.mp4",
                }
            else:
                return None
                
        name = filenames.get(kind)
        if name is None:
            return None
        path = self.session_dir(session_id) / name
        return path if path.is_file() else None

    def get_all_video_paths(self, session_id: str, kind: str) -> dict[str, Path]:
        """Get all available video paths for a specific kind across all angles.
        
        Args:
            session_id: UUID of the session.
            kind: One of ``"input"``, ``"slowmo"``, ``"annotated"``.
            
        Returns:
            Dictionary mapping angle names to paths for existing videos.
        """
        paths = {}
        
        # Check dual video files
        for angle in ["face_on", "down_the_line"]:
            path = self.get_video_path(session_id, kind, angle)
            if path is not None:
                paths[angle] = path
                
        # Check legacy single video if no dual videos found
        if not paths:
            legacy_path = self.get_video_path(session_id, kind, None)
            if legacy_path is not None:
                paths["legacy"] = legacy_path
                
        return paths

    def is_dual_video_session(self, session_id: str) -> bool:
        """Check if a session uses dual video mode.
        
        Args:
            session_id: UUID of the session.
            
        Returns:
            True if session has dual video inputs.
        """
        input_paths = self.get_input_video_paths(session_id)
        return "face_on" in input_paths and "down_the_line" in input_paths
