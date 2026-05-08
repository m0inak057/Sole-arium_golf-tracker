"""Output router — video streaming and download endpoints.

Enhanced with HTTP range request support for in-browser video streaming.

Endpoints:
- ``GET /api/output/{session_id}/slowmo`` - Stream slowmo video
- ``GET /api/output/{session_id}/annotated`` - Stream annotated video  
- ``GET /api/output/{session_id}/slowmo/status`` - Check slowmo status
- ``GET /api/output/{session_id}/annotated/status`` - Check annotated status
- ``GET /api/output/{session_id}/metadata`` - Get video metadata
- ``GET /api/output/{session_id}/download/{kind}`` - Download video file

Future dual-angle endpoints:
- ``GET /api/output/{session_id}/{angle}/{type}`` - Stream specific angle/type
- ``GET /api/output/{session_id}/{angle}/{type}/status`` - Check specific status

See api-contract.md §3.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO

import cv2
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse, FileResponse

from backend.api.deps import get_storage
from backend.api.dto import OutputStatusResponse, VideoMetadataResponse
from backend.core.storage import LocalStorage
from backend.core.logging import get_logger

router = APIRouter(prefix="/api/output", tags=["output"])
logger = get_logger(__name__)


def get_video_metadata(video_path: Path) -> dict:
    """Extract video metadata using OpenCV.
    
    Args:
        video_path: Path to the video file.
        
    Returns:
        Dictionary with video metadata.
    """
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {}
            
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        file_size = video_path.stat().st_size
        
        cap.release()
        
        return {
            "duration_seconds": duration,
            "fps": fps,
            "width": width,
            "height": height,
            "file_size_bytes": file_size,
            "format": "mp4"
        }
    except Exception as e:
        logger.error(f"Failed to extract video metadata: {e}")
        return {}


def parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    """Parse HTTP Range header.
    
    Args:
        range_header: Range header value (e.g., "bytes=0-1023").
        file_size: Total file size in bytes.
        
    Returns:
        Tuple of (start_byte, end_byte).
    """
    try:
        range_match = range_header.replace("bytes=", "")
        start, end = range_match.split("-")
        
        if start and end:
            # Normal range: bytes=start-end
            start = int(start)
            end = int(end)
        elif start and not end:
            # Suffix range: bytes=start-
            start = int(start)
            end = file_size - 1
        elif not start and end:
            # Prefix range: bytes=-end (last N bytes)
            end_bytes = int(end)
            start = max(0, file_size - end_bytes)
            end = file_size - 1
        else:
            # Invalid range
            start = 0
            end = file_size - 1
        
        # Ensure valid range
        start = max(0, min(start, file_size - 1))
        end = max(start, min(end, file_size - 1))
        
        return start, end
    except (ValueError, AttributeError):
        return 0, file_size - 1


def create_video_stream(file_path: Path, start: int, end: int, chunk_size: int = 8192):
    """Create a generator for streaming video content.
    
    Args:
        file_path: Path to the video file.
        start: Start byte position.
        end: End byte position.
        chunk_size: Size of each chunk to read.
        
    Yields:
        Chunks of video data.
    """
    with open(file_path, "rb") as video_file:
        video_file.seek(start)
        remaining = end - start + 1
        
        while remaining > 0:
            chunk_size_to_read = min(chunk_size, remaining)
            chunk = video_file.read(chunk_size_to_read)
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def stream_video_response(request: Request, file_path: Path) -> StreamingResponse:
    """Create a streaming response for video with range request support.
    
    Args:
        request: FastAPI request object.
        file_path: Path to the video file.
        
    Returns:
        StreamingResponse with appropriate headers.
    """
    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")
    
    if range_header:
        start, end = parse_range_header(range_header, file_size)
        content_length = end - start + 1
        
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": "video/mp4",
        }
        
        return StreamingResponse(
            create_video_stream(file_path, start, end),
            status_code=206,  # Partial Content
            headers=headers,
        )
    else:
        # Full file response
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": "video/mp4",
        }
        
        return StreamingResponse(
            create_video_stream(file_path, 0, file_size - 1),
            status_code=200,
            headers=headers,
        )


@router.get(
    "/{session_id}/metadata",
    response_model=VideoMetadataResponse,
    summary="Get video metadata",
)
async def get_video_metadata_endpoint(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> VideoMetadataResponse:
    """Get metadata for the session's videos.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        Video metadata including duration, fps, resolution, and file size.
    """
    # Try to get metadata from slowmo video first, fallback to annotated
    slowmo_path = storage.get_video_path(session_id, "slowmo")
    annotated_path = storage.get_video_path(session_id, "annotated")
    
    video_path = slowmo_path or annotated_path
    if video_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No video files found for session"
        )
    
    metadata = get_video_metadata(video_path)
    return VideoMetadataResponse(**metadata)


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
        Readiness status and streaming path.
    """
    # Check for dual videos first
    face_on = storage.get_video_path(session_id, "slowmo", "face_on")
    dtl = storage.get_video_path(session_id, "slowmo", "down_the_line")
    legacy = storage.get_video_path(session_id, "slowmo", None)
    
    ready = any([face_on, dtl, legacy])
    
    # If it's a dual session, return the dual status path
    if storage.is_dual_video_session(session_id):
        return OutputStatusResponse(
            ready=ready,
            path=f"/api/output/{session_id}/status/slowmo" if ready else None,
        )
    
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
        Readiness status and streaming path.
    """
    # Check for dual videos first
    face_on = storage.get_video_path(session_id, "annotated", "face_on")
    dtl = storage.get_video_path(session_id, "annotated", "down_the_line")
    legacy = storage.get_video_path(session_id, "annotated", None)
    
    ready = any([face_on, dtl, legacy])
    
    # If it's a dual session, return the dual status path
    if storage.is_dual_video_session(session_id):
        return OutputStatusResponse(
            ready=ready,
            path=f"/api/output/{session_id}/status/annotated" if ready else None,
        )
    
    return OutputStatusResponse(
        ready=ready,
        path=f"/api/output/{session_id}/annotated" if ready else None,
    )


@router.get(
    "/{session_id}/slowmo",
    summary="Stream slow-mo video with range request support",
)
async def stream_slowmo(
    request: Request,
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> StreamingResponse:
    """Stream the slow-motion MP4 with HTTP range request support for in-browser playback.

    Args:
        request: FastAPI request object (for range headers).
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        StreamingResponse with video content and appropriate headers.
    """
    path = storage.get_video_path(session_id, "slowmo")
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Slow-mo video not ready"
        )
    
    return stream_video_response(request, path)


@router.get(
    "/{session_id}/annotated",
    summary="Stream annotated video with range request support",
)
async def stream_annotated(
    request: Request,
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> StreamingResponse:
    """Stream the annotated MP4 with HTTP range request support for in-browser playback.

    Args:
        request: FastAPI request object (for range headers).
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        StreamingResponse with video content and appropriate headers.
    """
    path = storage.get_video_path(session_id, "annotated")
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Annotated video not ready"
        )
    
    return stream_video_response(request, path)


@router.get(
    "/{session_id}/download/{kind}",
    summary="Download a video file",
)
async def download_video(
    session_id: str,
    kind: str,
    angle: str | None = None,
    storage: LocalStorage = Depends(get_storage),
) -> FileResponse:
    """Download a video with ``Content-Disposition: attachment``.

    Args:
        session_id: UUID of the session.
        kind: ``"slowmo"`` or ``"annotated"``.
        angle: Camera angle ("face-on" or "down-the-line").
        storage: Injected storage adapter.

    Returns:
        ``FileResponse`` triggering a browser download.
    """
    if kind not in ("slowmo", "annotated"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid kind. Must be 'slowmo' or 'annotated'"
        )
    
    # Normalize angle for storage
    storage_angle = angle.replace("-", "_") if angle else None
    
    path = storage.get_video_path(session_id, kind, storage_angle)
    if path is None and storage_angle:
        # Fallback to single video if angle requested but not found
        path = storage.get_video_path(session_id, kind, None)
        
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"{kind} video ({angle or 'primary'}) not ready"
        )
    
    filename = f"{session_id}_{kind}"
    if angle:
        filename += f"_{angle}"
    filename += ".mp4"
    
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=filename,
    )


# ── Comprehensive Status Endpoints (Must come before generic routes) ────────


@router.get(
    "/{session_id}/status/all",
    summary="Get status for all video types and angles",
)
async def get_all_video_status(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> dict:
    """Get comprehensive status for all video types and angles.
    
    This endpoint provides a single call to check all video availability,
    useful for frontend dashboards and status displays.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        Dictionary with status for all video combinations.
    """
    # Check if this is a dual video session
    is_dual = storage.is_dual_video_session(session_id)
    
    if is_dual:
        # Dual video mode - check each angle separately
        slowmo_face_on = storage.get_video_path(session_id, "slowmo", "face_on")
        slowmo_dtl = storage.get_video_path(session_id, "slowmo", "down_the_line")
        annotated_face_on = storage.get_video_path(session_id, "annotated", "face_on")
        annotated_dtl = storage.get_video_path(session_id, "annotated", "down_the_line")
        
        return {
            "session_id": session_id,
            "dual_video_mode": True,
            "slowmo": {
                "face_on": {
                    "ready": slowmo_face_on is not None,
                    "path": f"/api/output/{session_id}/slowmo/face-on" if slowmo_face_on else None,
                },
                "down_the_line": {
                    "ready": slowmo_dtl is not None,
                    "path": f"/api/output/{session_id}/slowmo/down-the-line" if slowmo_dtl else None,
                }
            },
            "annotated": {
                "face_on": {
                    "ready": annotated_face_on is not None,
                    "path": f"/api/output/{session_id}/annotated/face-on" if annotated_face_on else None,
                },
                "down_the_line": {
                    "ready": annotated_dtl is not None,
                    "path": f"/api/output/{session_id}/annotated/down-the-line" if annotated_dtl else None,
                }
            },
            "metadata_available": any([slowmo_face_on, slowmo_dtl, annotated_face_on, annotated_dtl]),
            "metadata_path": f"/api/output/{session_id}/metadata" if any([slowmo_face_on, slowmo_dtl, annotated_face_on, annotated_dtl]) else None,
        }
    else:
        # Legacy single video mode
        slowmo_path = storage.get_video_path(session_id, "slowmo", None)
        annotated_path = storage.get_video_path(session_id, "annotated", None)
        
        slowmo_ready = slowmo_path is not None
        annotated_ready = annotated_path is not None
        
        return {
            "session_id": session_id,
            "dual_video_mode": False,
            "slowmo": {
                "face_on": {
                    "ready": slowmo_ready,
                    "path": f"/api/output/{session_id}/slowmo/face-on" if slowmo_ready else None,
                },
                "down_the_line": {
                    "ready": slowmo_ready,
                    "path": f"/api/output/{session_id}/slowmo/down-the-line" if slowmo_ready else None,
                }
            },
            "annotated": {
                "face_on": {
                    "ready": annotated_ready,
                    "path": f"/api/output/{session_id}/annotated/face-on" if annotated_ready else None,
                },
                "down_the_line": {
                    "ready": annotated_ready,
                    "path": f"/api/output/{session_id}/annotated/down-the-line" if annotated_ready else None,
                }
            },
            "metadata_available": slowmo_ready or annotated_ready,
            "metadata_path": f"/api/output/{session_id}/metadata" if (slowmo_ready or annotated_ready) else None,
        }


@router.get(
    "/{session_id}/status/{video_type}",
    summary="Get status for specific video type (both angles)",
)
async def get_video_type_status(
    session_id: str,
    video_type: str,
    storage: LocalStorage = Depends(get_storage),
) -> dict:
    """Get status for a specific video type across both angles.

    Args:
        session_id: UUID of the session.
        video_type: "slowmo" or "annotated".
        storage: Injected storage adapter.

    Returns:
        Dictionary with status for both angles of the specified video type.
    """
    if video_type not in ("slowmo", "annotated"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video_type. Must be 'slowmo' or 'annotated'"
        )
    
    path = storage.get_video_path(session_id, video_type)
    ready = path is not None
    
    return {
        "session_id": session_id,
        "video_type": video_type,
        "face_on": {
            "ready": ready,
            "path": f"/api/output/{session_id}/{video_type}/face-on" if ready else None,
        },
        "down_the_line": {
            "ready": ready,
            "path": f"/api/output/{session_id}/{video_type}/down-the-line" if ready else None,
        }
    }


# ── Frontend Integration Endpoints ──────────────────────────────────────────


@router.get(
    "/{session_id}/slowmo/face-on",
    summary="Stream face-on slowmo video",
)
async def stream_slowmo_face_on(
    request: Request,
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> StreamingResponse:
    """Stream the face-on slow-motion MP4 with range request support."""
    path = storage.get_video_path(session_id, "slowmo", "face_on")
    if path is None:
        path = storage.get_video_path(session_id, "slowmo", None)
    
    if path is None:
        raise HTTPException(status_code=404, detail="Face-on slowmo not ready")
    return stream_video_response(request, path)


@router.get(
    "/{session_id}/slowmo/down-the-line",
    summary="Stream down-the-line slowmo video",
)
async def stream_slowmo_down_the_line(
    request: Request,
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> StreamingResponse:
    """Stream the down-the-line slow-motion MP4 with range request support."""
    path = storage.get_video_path(session_id, "slowmo", "down_the_line")
    if path is None:
        path = storage.get_video_path(session_id, "slowmo", None)
    
    if path is None:
        raise HTTPException(status_code=404, detail="Down-the-line slowmo not ready")
    return stream_video_response(request, path)


@router.get(
    "/{session_id}/annotated/face-on",
    summary="Stream face-on annotated video",
)
async def stream_annotated_face_on(
    request: Request,
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> StreamingResponse:
    """Stream the face-on annotated MP4 with range request support."""
    path = storage.get_video_path(session_id, "annotated", "face_on")
    if path is None:
        path = storage.get_video_path(session_id, "annotated", None)
    
    if path is None:
        raise HTTPException(status_code=404, detail="Face-on annotated not ready")
    return stream_video_response(request, path)


@router.get(
    "/{session_id}/annotated/down-the-line",
    summary="Stream down-the-line annotated video",
)
async def stream_annotated_down_the_line(
    request: Request,
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> StreamingResponse:
    """Stream the down-the-line annotated MP4 with range request support."""
    path = storage.get_video_path(session_id, "annotated", "down_the_line")
    if path is None:
        path = storage.get_video_path(session_id, "annotated", None)
    
    if path is None:
        raise HTTPException(status_code=404, detail="Down-the-line annotated not ready")
    return stream_video_response(request, path)


# ── Status Endpoints for Frontend Integration ────────────────────────────────


@router.get(
    "/{session_id}/slowmo/face-on/status",
    response_model=OutputStatusResponse,
    summary="Check face-on slowmo video status",
)
async def slowmo_face_on_status(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> OutputStatusResponse:
    """Check whether the face-on slow-motion MP4 is available."""
    path = storage.get_video_path(session_id, "slowmo", "face_on")
    if path is None:
        path = storage.get_video_path(session_id, "slowmo", None)
        
    ready = path is not None
    return OutputStatusResponse(
        ready=ready,
        path=f"/api/output/{session_id}/slowmo/face-on" if ready else None,
    )


@router.get(
    "/{session_id}/slowmo/down-the-line/status",
    response_model=OutputStatusResponse,
    summary="Check down-the-line slowmo video status",
)
async def slowmo_down_the_line_status(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> OutputStatusResponse:
    """Check whether the down-the-line slow-motion MP4 is available."""
    path = storage.get_video_path(session_id, "slowmo", "down_the_line")
    if path is None:
        path = storage.get_video_path(session_id, "slowmo", None)
        
    ready = path is not None
    return OutputStatusResponse(
        ready=ready,
        path=f"/api/output/{session_id}/slowmo/down-the-line" if ready else None,
    )


@router.get(
    "/{session_id}/annotated/face-on/status",
    response_model=OutputStatusResponse,
    summary="Check face-on annotated video status",
)
async def annotated_face_on_status(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> OutputStatusResponse:
    """Check whether the face-on annotated MP4 is available."""
    path = storage.get_video_path(session_id, "annotated", "face_on")
    if path is None:
        path = storage.get_video_path(session_id, "annotated", None)
        
    ready = path is not None
    return OutputStatusResponse(
        ready=ready,
        path=f"/api/output/{session_id}/annotated/face-on" if ready else None,
    )


@router.get(
    "/{session_id}/annotated/down-the-line/status",
    response_model=OutputStatusResponse,
    summary="Check down-the-line annotated video status",
)
async def annotated_down_the_line_status(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> OutputStatusResponse:
    """Check whether the down-the-line annotated MP4 is available."""
    path = storage.get_video_path(session_id, "annotated", "down_the_line")
    if path is None:
        path = storage.get_video_path(session_id, "annotated", None)
        
    ready = path is not None
    return OutputStatusResponse(
        ready=ready,
        path=f"/api/output/{session_id}/annotated/down-the-line" if ready else None,
    )


# ── Generic Dual-Angle Endpoints (Alternative Pattern) ───────────────────────


@router.get(
    "/{session_id}/{angle}/{video_type}",
    summary="Stream video by angle and type (alternative pattern)",
)
async def stream_video_by_angle(
    request: Request,
    session_id: str,
    angle: str,
    video_type: str,
    storage: LocalStorage = Depends(get_storage),
) -> StreamingResponse:
    """Stream video by camera angle and type with range request support.
    
    This endpoint is prepared for future dual-angle support.
    Currently falls back to single video behavior.

    Args:
        request: FastAPI request object (for range headers).
        session_id: UUID of the session.
        angle: Camera angle ("face-on" or "down-the-line").
        video_type: Video type ("slowmo" or "annotated").
        storage: Injected storage adapter.

    Returns:
        StreamingResponse with video content.
    """
    # Validate parameters
    if angle not in ("face-on", "down-the-line"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid angle. Must be 'face-on' or 'down-the-line'"
        )
    
    if video_type not in ("slowmo", "annotated"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video_type. Must be 'slowmo' or 'annotated'"
        )
    
    # For now, fall back to single video (Phase 2+ will implement dual videos)
    # Future: storage.get_video_path(session_id, f"{video_type}_{angle.replace('-', '_')}")
    path = storage.get_video_path(session_id, video_type)
    
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{video_type} video ({angle}) not ready"
        )
    
    return stream_video_response(request, path)


@router.get(
    "/{session_id}/{angle}/{video_type}/status",
    response_model=OutputStatusResponse,
    summary="Check video status by angle and type (future dual-angle support)",
)
async def video_status_by_angle(
    session_id: str,
    angle: str,
    video_type: str,
    storage: LocalStorage = Depends(get_storage),
) -> OutputStatusResponse:
    """Check video readiness by camera angle and type.
    
    This endpoint is prepared for future dual-angle support.
    Currently falls back to single video behavior.

    Args:
        session_id: UUID of the session.
        angle: Camera angle ("face-on" or "down-the-line").
        video_type: Video type ("slowmo" or "annotated").
        storage: Injected storage adapter.

    Returns:
        Readiness status and streaming path.
    """
    # Validate parameters
    if angle not in ("face-on", "down-the-line"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid angle. Must be 'face-on' or 'down-the-line'"
        )
    
    if video_type not in ("slowmo", "annotated"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video_type. Must be 'slowmo' or 'annotated'"
        )
    
    # For now, fall back to single video (Phase 2+ will implement dual videos)
    path = storage.get_video_path(session_id, video_type)
    ready = path is not None
    
    return OutputStatusResponse(
        ready=ready,
        path=f"/api/output/{session_id}/{angle}/{video_type}" if ready else None,
    )
