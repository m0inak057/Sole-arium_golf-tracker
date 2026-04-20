"""FastAPI dependency injection — shared instances.

Provides ``get_storage()`` and ``get_settings()`` as FastAPI dependencies
so routers stay thin and testable.
"""

from __future__ import annotations

from functools import lru_cache

from backend.core.config import Settings, get_settings as _get_settings
from backend.core.storage import LocalStorage


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings.

    Returns:
        Application-wide ``Settings`` instance.
    """
    return _get_settings()


@lru_cache(maxsize=1)
def get_storage() -> LocalStorage:
    """Return the cached storage adapter.

    Returns:
        A ``LocalStorage`` instance.
    """
    return LocalStorage(get_settings())
