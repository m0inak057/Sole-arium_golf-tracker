"""Output router — video streaming and download endpoints.

``GET /api/output/{session_id}/slowmo``
``GET /api/output/{session_id}/annotated``
``GET /api/output/{session_id}/slowmo/status``
``GET /api/output/{session_id}/annotated/status``
``GET /api/output/{session_id}/download/{kind}``

See api-contract.md §3.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from backend.api.deps import get_storage
from backend.api.dto import OutputStatusResponse
from backend.core.storage import LocalStorage

router = APIRouter(prefix="/api/output", tags=["output"])


@router.get(
    "/{session_id}/slowmo/status",
    response_model=OutputStatusResponse,
    summary="Check if slow-mo video is ready",
)
async def slowmo_status(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> OutputStatusResponse:
    """Check whether the slow-motion MP4 is available.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        Readiness status and path.
    """
    path = storage.get_video_path(session_id, "slowmo")
    ready = path is not None
    return OutputStatusResponse(
        ready=ready,
        path=f"/api/output/{session_id}/slowmo" if ready else None,
    )


@router.get(
    "/{session_id}/annotated/status",
    response_model=OutputStatusResponse,
    summary="Check if annotated video is ready",
)
async def annotated_status(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> OutputStatusResponse:
    """Check whether the annotated MP4 is available.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        Readiness status and path.
    """
    path = storage.get_video_path(session_id, "annotated")
    ready = path is not None
    return OutputStatusResponse(
        ready=ready,
        path=f"/api/output/{session_id}/annotated" if ready else None,
    )


@router.get(
    "/{session_id}/slowmo",
    summary="Stream slow-mo video",
)
async def stream_slowmo(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> FileResponse:
    """Stream the plain slow-motion MP4.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        ``FileResponse`` with ``video/mp4`` content type.
    """
    path = storage.get_video_path(session_id, "slowmo")
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slow-mo not ready.")
    return FileResponse(path, media_type="video/mp4")


@router.get(
    "/{session_id}/annotated",
    summary="Stream annotated video",
)
async def stream_annotated(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> FileResponse:
    """Stream the annotated MP4.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        ``FileResponse`` with ``video/mp4`` content type.
    """
    path = storage.get_video_path(session_id, "annotated")
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotated not ready.")
    return FileResponse(path, media_type="video/mp4")


@router.get(
    "/{session_id}/download/{kind}",
    summary="Download a video file",
)
async def download_video(
    session_id: str,
    kind: str,
    storage: LocalStorage = Depends(get_storage),
) -> FileResponse:
    """Download a video with ``Content-Disposition: attachment``.

    Args:
        session_id: UUID of the session.
        kind: ``"slowmo"`` or ``"annotated"``.
        storage: Injected storage adapter.

    Returns:
        ``FileResponse`` triggering a browser download.
    """
    if kind not in ("slowmo", "annotated"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid kind.")
    path = storage.get_video_path(session_id, kind)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{kind} not ready.")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{session_id}_{kind}.mp4",
    )
