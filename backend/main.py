"""Golf Trainer AI — FastAPI application entrypoint.

Run with: ``uvicorn backend.main:app --reload``
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.deps import get_settings
from backend.api.routers import coaching, output, phase1, phase4, phase5, status, upload

settings = get_settings()

app = FastAPI(
    title="Golf Trainer AI",
    version="1.3.0",
    description="AI-powered golf swing analysis — 8 phases, 5 agents, zero hardcoded thresholds.",
)

# ── CORS — api-contract.md §5 ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(status.router)
app.include_router(phase1.router)
app.include_router(phase4.router)
app.include_router(phase5.router)
app.include_router(coaching.router)
app.include_router(output.router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Basic health check endpoint.

    Returns:
        Status and version info.
    """
    return {"status": "ok", "version": "1.3.0"}
