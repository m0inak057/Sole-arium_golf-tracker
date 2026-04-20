"""Application configuration loaded from environment variables.

All config is read via ``pydantic-settings``.  Required variables
will cause a startup crash if missing, which is intentional —
see architecture.md §9.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Immutable application-wide settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── LLM config ───────────────────────────────────────────────────
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"

    # ── Storage ──────────────────────────────────────────────────────
    storage_backend: str = "local"  # "local" | "s3"
    storage_local_path: str = "./storage"

    # S3 (only required when storage_backend == "s3")
    s3_bucket: str = ""
    s3_region: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # ── Upload limits ────────────────────────────────────────────────
    max_upload_mb: int = 500
    max_video_seconds: int = 30

    # ── Server ───────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    @property
    def max_upload_bytes(self) -> int:
        """Return the upload limit in bytes."""
        return self.max_upload_mb * 1024 * 1024


def get_settings() -> Settings:
    """Create and return a ``Settings`` instance.

    Returns:
        Validated settings drawn from env vars / ``.env``.
    """
    return Settings()  # type: ignore[call-arg]
