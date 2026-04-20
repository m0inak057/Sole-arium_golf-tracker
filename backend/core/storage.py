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

    def input_video_path(self, session_id: str) -> Path:
        """Return the path where the uploaded video is stored.

        Args:
            session_id: UUID of the session.

        Returns:
            Path to ``storage/{session_id}/input.mp4``.
        """
        return self.session_dir(session_id) / "input.mp4"

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

    async def save_upload(self, session_id: str, content: bytes, extension: str = ".mp4") -> Path:
        """Persist an uploaded video file.

        Args:
            session_id: UUID of the session.
            content: Raw file bytes.
            extension: File extension (default ``.mp4``).

        Returns:
            Path to the saved file.
        """
        dest = self.session_dir(session_id) / f"input{extension}"
        dest.write_bytes(content)
        log_event(
            logger,
            f"Upload saved ({len(content)} bytes)",
            session_id=session_id,
            event="upload_saved",
        )
        return dest

    def get_video_path(self, session_id: str, kind: str) -> Path | None:
        """Return a video path if the file exists.

        Args:
            session_id: UUID of the session.
            kind: One of ``"input"``, ``"slowmo"``, ``"annotated"``.

        Returns:
            Path if the file exists, else ``None``.
        """
        filenames = {
            "input": "input.mp4",
            "slowmo": "slowmo.mp4",
            "annotated": "annotated.mp4",
        }
        name = filenames.get(kind)
        if name is None:
            return None
        path = self.session_dir(session_id) / name
        return path if path.is_file() else None
