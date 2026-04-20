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

    storage = LocalStorage(test_settings)

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_storage] = lambda: storage

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
