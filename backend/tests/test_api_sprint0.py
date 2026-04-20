"""Sprint 0 — API smoke tests.

Verifies the Sprint 0 definition of done:
- POST /api/session creates a session
- Status polling returns 'uploaded'
- Full session endpoint enforces completion check
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient


def _make_fake_video(size_bytes: int = 1024) -> bytes:
    """Create a minimal fake video payload for upload testing."""
    return b"\x00" * size_bytes


class TestHealthCheck:
    """Health endpoint tests."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        """GET /health returns 200 with status ok."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestUpload:
    """POST /api/session tests."""

    def test_upload_success(self, client: TestClient) -> None:
        """Valid upload returns 202 with session_id."""
        resp = client.post(
            "/api/session",
            data={"gender": "male"},
            files={"video": ("test.mp4", _make_fake_video(), "video/mp4")},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "session_id" in data
        assert data["status"] == "uploaded"
        assert "created_at" in data

    def test_upload_missing_gender(self, client: TestClient) -> None:
        """Missing gender returns 422."""
        resp = client.post(
            "/api/session",
            files={"video": ("test.mp4", _make_fake_video(), "video/mp4")},
        )
        assert resp.status_code == 422

    def test_upload_invalid_gender(self, client: TestClient) -> None:
        """Invalid gender value returns 400."""
        resp = client.post(
            "/api/session",
            data={"gender": "other"},
            files={"video": ("test.mp4", _make_fake_video(), "video/mp4")},
        )
        assert resp.status_code == 400

    def test_upload_bad_extension(self, client: TestClient) -> None:
        """Non-.mp4/.mov extension returns 415."""
        resp = client.post(
            "/api/session",
            data={"gender": "female"},
            files={"video": ("test.avi", _make_fake_video(), "video/x-msvideo")},
        )
        assert resp.status_code == 415

    def test_upload_too_large(self, client: TestClient) -> None:
        """File exceeding MAX_UPLOAD_MB returns 413.

        Test settings use max_upload_mb=10, so 11 MB should fail.
        """
        big_file = _make_fake_video(size_bytes=11 * 1024 * 1024)
        resp = client.post(
            "/api/session",
            data={"gender": "male"},
            files={"video": ("test.mp4", big_file, "video/mp4")},
        )
        assert resp.status_code == 413


class TestStatus:
    """GET /api/session/{id}/status tests."""

    def test_status_after_upload(self, client: TestClient) -> None:
        """Status returns 'uploaded' immediately after creation."""
        # Create session first
        resp = client.post(
            "/api/session",
            data={"gender": "female"},
            files={"video": ("test.mp4", _make_fake_video(), "video/mp4")},
        )
        session_id = resp.json()["session_id"]

        # Poll status
        resp = client.get(f"/api/session/{session_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert data["status"] == "uploaded"
        assert data["progress_pct"] == 0
        assert data["failed"] is False

    def test_status_404_unknown_session(self, client: TestClient) -> None:
        """Unknown session_id returns 404."""
        resp = client.get("/api/session/nonexistent-id/status")
        assert resp.status_code == 404


class TestFullSession:
    """GET /api/session/{id} tests."""

    def test_full_session_409_not_complete(self, client: TestClient) -> None:
        """Requesting full session before completion returns 409."""
        resp = client.post(
            "/api/session",
            data={"gender": "male"},
            files={"video": ("test.mp4", _make_fake_video(), "video/mp4")},
        )
        session_id = resp.json()["session_id"]

        resp = client.get(f"/api/session/{session_id}")
        assert resp.status_code == 409
