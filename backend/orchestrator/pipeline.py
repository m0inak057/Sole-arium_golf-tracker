"""Pipeline orchestrator — runs the 8 phases + 5 agents in sequence.

The orchestrator is the **only** module that knows about execution order.
Phases do not call each other.  Agents do not call phases.

See architecture.md §2 for the execution model.
"""

from __future__ import annotations

import time
from typing import Any

from backend.core.logging import get_logger, log_event
from backend.core.session import SessionJSON
from backend.core.storage import LocalStorage

logger = get_logger(__name__)


async def run_pipeline(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Execute the full analysis pipeline for a session.

    This is the main entry point called by the job worker.
    Updates the session JSON and persists it after every phase/agent.

    Args:
        session: The session to process (status must be ``"uploaded"``).
        storage: Storage adapter for persistence.

    Returns:
        The completed (or failed) session.
    """
    total_start = time.monotonic()

    try:
        # ── Agent 1 — Video Intelligence ─────────────────────────────
        session = await _run_step(session, storage, "agent1_running", "agent1_done", _agent1_stub)

        # ── Phase 1 — Hit Detection ─────────────────────────────────
        session = await _run_step(session, storage, "phase1_running", "phase1_done", _phase1_stub)

        # ── Agent 2 — Body Calibration ──────────────────────────────
        session = await _run_step(session, storage, "agent2_running", "agent2_done", _agent2_stub)

        # ── Phase 2 — Keypoints ─────────────────────────────────────
        session = await _run_step(session, storage, "phase2_running", "phase2_done", _phase2_stub)

        # ── Phase 3 — Setup Analysis ────────────────────────────────
        session = await _run_step(session, storage, "phase3_running", "phase3_done", _phase3_stub)

        # ── Agent 3 — Shot Classification ───────────────────────────
        session = await _run_step(session, storage, "agent3_running", "agent3_done", _agent3_stub)

        # ── Phase 4 — Biomechanical Metrics ─────────────────────────
        session = await _run_step(session, storage, "phase4_running", "phase4_done", _phase4_stub)

        # ── Agent 4 — Threshold Adaptation ──────────────────────────
        session = await _run_step(session, storage, "agent4_running", "agent4_done", _agent4_stub)

        # ── Phase 5 — Performance Scoring ───────────────────────────
        session = await _run_step(session, storage, "phase5_running", "phase5_done", _phase5_stub)

        # ── Agent 5 == Phase 6 — Coaching ───────────────────────────
        session = await _run_step(session, storage, "agent5_running", "agent5_done", _agent5_stub)

        # ── Phase 7 — Slow-Motion Rendering ─────────────────────────
        session = await _run_step(session, storage, "phase7_running", "phase7_done", _phase7_stub)

        # ── Phase 8 — Annotated Video Overlay ───────────────────────
        session = await _run_step(session, storage, "phase8_running", "phase8_done", _phase8_stub)

        # ── Done ────────────────────────────────────────────────────
        session.status = "complete"
        total_ms = int((time.monotonic() - total_start) * 1000)
        session.timings.total_ms = total_ms
        storage.save_session(session)

        log_event(
            logger,
            f"Pipeline complete in {total_ms}ms",
            session_id=session.session_id,
            event="pipeline_complete",
            duration_ms=total_ms,
        )

    except Exception as exc:
        session.status = "failed"
        reason = str(exc)
        if reason in ("unreadable_video", "no_real_swing_detected"):
            session.status_reason = reason
        else:
            session.status_reason = "internal_error"
        storage.save_session(session)
        log_event(
            logger,
            f"Pipeline failed: {exc}",
            session_id=session.session_id,
            event="pipeline_failed",
        )
        raise

    return session


async def _run_step(
    session: SessionJSON,
    storage: LocalStorage,
    status_running: str,
    status_done: str,
    step_fn: Any,
) -> SessionJSON:
    """Run a single pipeline step with status bookkeeping.

    Args:
        session: Current session state.
        storage: Storage adapter.
        status_running: Status value to set before execution.
        status_done: Status value to set after execution.
        step_fn: Async callable that takes (session, storage) and returns session.

    Returns:
        Updated session.
    """
    session.status = status_running
    storage.save_session(session)

    start = time.monotonic()
    log_event(
        logger,
        f"Starting {status_running}",
        session_id=session.session_id,
        event="step_started",
        step=status_running,
    )

    session = await step_fn(session, storage)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    session.status = status_done
    # Store timing — extract step name from status (e.g. "agent1_running" → "agent1_ms")
    timing_key = status_running.replace("_running", "_ms")
    if hasattr(session.timings, timing_key):
        setattr(session.timings, timing_key, elapsed_ms)

    storage.save_session(session)
    log_event(
        logger,
        f"Completed {status_done} in {elapsed_ms}ms",
        session_id=session.session_id,
        event="step_completed",
        step=status_done,
        duration_ms=elapsed_ms,
    )

    return session


# ── Step stubs — replaced with real implementations in Sprints 1–3 ───────────


async def _agent1_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Agent 1 — Video Intelligence."""
    from backend.agents.video_intelligence_agent import VideoIntelligenceAgent, analyze_video_intelligence

    d = storage.session_dir(session.session_id)
    videos = list(d.glob("input.*"))
    if not videos:
        raise FileNotFoundError(f"Input video not found for {session.session_id}")
    video_path = videos[0]

    try:
        session_data = analyze_video_intelligence(video_path)
    except Exception as e:
        raise RuntimeError("unreadable_video") from e

    agent = VideoIntelligenceAgent()
    agents_dir = storage.agents_dir(session.session_id)
    result = await agent.run(session_data, session.session_id, agents_dir)

    session.input_fps = result["input_fps"]
    session.camera_angle = result["camera_angle"]
    session.video_quality_score = result["video_quality_score"]
    
    # We parse the resolution dict from the raw dict representation
    from backend.core.session import Resolution
    session.resolution = Resolution(width=result["resolution"]["width"], height=result["resolution"]["height"])
    session.agent1_notes = result["agent1_notes"]

    return session


async def _phase1_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Phase 1 — Hit Detection."""
    from backend.phase1.hit_detector import run_hit_detection

    d = storage.session_dir(session.session_id)
    videos = list(d.glob("input.*"))
    if not videos:
        raise FileNotFoundError(f"Input video not found for {session.session_id}")
    video_path = videos[0]

    result = run_hit_detection(video_path)

    session.total_swing_attempts = result.total_swing_attempts
    session.selected_swing_index = result.selected_swing_index
    session.hit_confidence_score = result.hit_confidence_score
    session.backswing_start_frame_index = result.backswing_start_frame_index
    session.impact_frame_index = result.impact_frame_index
    session.follow_through_end_frame_index = result.follow_through_end_frame_index
    session.address_frame_range = result.address_frame_range

    if result.total_swing_attempts == 0 or result.selected_swing_index is None:
        raise RuntimeError("no_real_swing_detected")

    return session


async def _agent2_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Agent 2 — Body Calibration."""
    from backend.agents.body_calibration_agent import BodyCalibrationAgent, extract_address_measurements

    d = storage.session_dir(session.session_id)
    videos = list(d.glob("input.*"))
    if not videos or not session.address_frame_range:
        return session
    
    measurements = extract_address_measurements(videos[0], session.address_frame_range)
    measurements["gender"] = session.gender
    measurements["camera_angle"] = getattr(session, "camera_angle", "unknown")

    agent = BodyCalibrationAgent()
    agents_dir = storage.agents_dir(session.session_id)
    result = await agent.run(measurements, session.session_id, agents_dir)

    session.px_to_inches_scale = result.get("px_to_inches_scale", 1.0)
    session.calibration_notes = result.get("calibration_notes", "")
    return session


async def _phase2_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Phase 2 — Keypoints."""
    from backend.phase2.keypoints import extract_keypoints

    d = storage.session_dir(session.session_id)
    videos = list(d.glob("input.*"))
    if not videos or session.backswing_start_frame_index is None or session.follow_through_end_frame_index is None:
        return session

    out_pq = storage.session_dir(session.session_id) / "keypoints.parquet"
    extract_keypoints(
        videos[0],
        out_pq,
        session.backswing_start_frame_index,
        session.follow_through_end_frame_index
    )
    return session


async def _phase3_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Phase 3 — Setup Analysis."""
    from backend.phase3.setup_analysis import run_setup_analysis

    # Phase 3 reads from keypoints parquet
    out_pq = storage.session_dir(session.session_id) / "keypoints.parquet"
    
    # We pass it the address_frame_range so it can pull the static keypoints
    res = getattr(session, "resolution", None)
    res_dict = res.model_dump() if res else {"width": 1000, "height": 1000}
    
    camera = getattr(session, "camera_angle", "face_on")
    scale = getattr(session, "px_to_inches_scale", 1.0)
    
    metrics = run_setup_analysis(
        out_pq,
        session.address_frame_range,
        scale,
        camera,
        res_dict
    )
    
    # Update Session with the metrics according to data-schema
    session.setup_metrics = metrics
    
    return session


async def _agent3_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Agent 3 — Shot Classification."""
    from backend.agents.shot_classification_agent import ShotClassificationAgent

    session_data = {
        "camera_angle": getattr(session, "camera_angle", "unknown"),
        "px_to_inches_scale": getattr(session, "px_to_inches_scale", 1.0),
        "gender": session.gender,
    }
    
    setup = getattr(session, "setup_metrics", {})
    session_data.update(setup)

    agent = ShotClassificationAgent()
    agents_dir = storage.agents_dir(session.session_id)
    result = await agent.run(session_data, session.session_id, agents_dir)

    session.detected_shot_type = result.get("detected_shot_type")
    session.shot_type_confidence = result.get("shot_type_confidence")
    return session


async def _phase4_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Phase 4 — Biomechanical Metrics."""
    from backend.phase4.measurements import compute_all_metrics
    out_pq = storage.session_dir(session.session_id) / "keypoints.parquet"
    
    session.metrics = compute_all_metrics(session, out_pq)
    return session


async def _agent4_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Agent 4 — Threshold Adaptation."""
    from backend.agents.threshold_agent import ThresholdAdaptationAgent
    from backend.core.session import ThresholdRange
    
    session_data = {
        "gender": session.gender,
        "detected_shot_type": session.detected_shot_type,
        "metrics": {k: v.model_dump() for k, v in session.metrics.items()} if session.metrics else {}
    }
    
    agent = ThresholdAdaptationAgent()
    agents_dir = storage.agents_dir(session.session_id)
    result = await agent.run(session_data, session.session_id, agents_dir)
    
    session.inferred_skill_level = result.get("inferred_skill_level")
    raw_thresholds = result.get("active_thresholds", {})
    session.active_thresholds = {k: ThresholdRange(**v) for k, v in raw_thresholds.items()}
    
    return session


async def _phase5_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Phase 5 — Performance Scoring."""
    from backend.phase5.scoring import score_metrics
    session.scores = score_metrics(session)
    return session


async def _agent5_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Agent 5 — Coaching (Phase 6)."""
    from backend.agents.coaching_agent import CoachingAgent
    from backend.core.session import CoachingItem
    
    session_data = {
        "gender": session.gender,
        "detected_shot_type": session.detected_shot_type,
        "inferred_skill_level": session.inferred_skill_level,
        "scores": session.scores.model_dump() if session.scores else {},
        "metrics": {k: v.model_dump() for k, v in session.metrics.items()} if session.metrics else {}
    }
    
    agent = CoachingAgent()
    agents_dir = storage.agents_dir(session.session_id)
    result = await agent.run(session_data, session.session_id, agents_dir)
    
    raw_coaching = result.get("coaching_output", [])
    session.coaching_output = [CoachingItem(**item) for item in raw_coaching]
    
    return session


async def _phase7_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Phase 7 — Slow-Motion Rendering."""
    from backend.phase7.slowmo import render_slowmo
    
    d = storage.session_dir(session.session_id)
    videos = list(d.glob("input.*"))
    if not videos or session.backswing_start_frame_index is None or session.follow_through_end_frame_index is None:
        return session
        
    out_vid = d / "slowmo.mp4"
    fps = getattr(session, "input_fps", 30.0) or 30.0
    
    success = render_slowmo(
        videos[0],
        out_vid,
        session.backswing_start_frame_index,
        session.follow_through_end_frame_index,
        fps
    )
    
    if success:
        session.slowmo_video_path = f"/api/session/{session.session_id}/video/slowmo"
        
    return session


async def _phase8_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Phase 8 — Annotated Video Overlay."""
    from backend.phase8.overlay import render_overlay

    d = storage.session_dir(session.session_id)
    videos = list(d.glob("input.*"))
    if not videos or session.backswing_start_frame_index is None or session.follow_through_end_frame_index is None:
        return session
        
    out_vid = d / "annotated.mp4"
    out_pq = d / "keypoints.parquet"
    
    success = render_overlay(
        videos[0],
        out_vid,
        out_pq,
        session.backswing_start_frame_index,
        session.follow_through_end_frame_index
    )
    
    if success:
        session.annotated_video_path = f"/api/session/{session.session_id}/video/annotated"
    else:
        session.overlay_rendering_failed = True
        
    return session
