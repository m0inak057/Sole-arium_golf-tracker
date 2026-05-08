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
    
    # Check if this is a dual video session
    input_paths = storage.get_input_video_paths(session.session_id)
    
    if not input_paths:
        raise FileNotFoundError(f"Input video not found for {session.session_id}")
    
    if storage.is_dual_video_session(session.session_id):
        # Dual video mode - process both videos and combine results
        if "face_on" not in input_paths or "down_the_line" not in input_paths:
            raise FileNotFoundError(f"Dual video session missing required videos for {session.session_id}")
        
        # Process face-on video
        try:
            face_on_data = analyze_video_intelligence(input_paths["face_on"])
        except Exception as e:
            raise RuntimeError("unreadable_video") from e
        
        # Process down-the-line video
        try:
            dtl_data = analyze_video_intelligence(input_paths["down_the_line"])
        except Exception as e:
            raise RuntimeError("unreadable_video") from e
        
        # Combine agent notes
        agent = VideoIntelligenceAgent()
        agents_dir = storage.agents_dir(session.session_id)
        
        # Create combined session data for agent
        combined_data = {
            "face_on": face_on_data,
            "down_the_line": dtl_data,
            "dual_video_mode": True,
            # Pack metadata for the prompt builder if needed
            "fps": face_on_data["fps"],
            "width": face_on_data["width"],
            "height": face_on_data["height"],
            "duration_seconds": face_on_data["duration_seconds"],
            "geometry_samples": face_on_data["geometry_samples"]
        }
        
        result = await agent.run(combined_data, session.session_id, agents_dir)
        
        # Update dual video metadata from agent result
        if session.dual_video_metadata:
            # Note: The agent currently returns a single resolution/fps. 
            # In dual mode, we use these as primary.
            session.dual_video_metadata.face_on_fps = result["input_fps"]
            session.dual_video_metadata.down_the_line_fps = result["input_fps"]
            
            from backend.core.session import Resolution
            res = Resolution(width=result["resolution"]["width"], height=result["resolution"]["height"])
            session.dual_video_metadata.face_on_resolution = res
            session.dual_video_metadata.down_the_line_resolution = res
            
            session.dual_video_metadata.face_on_quality_score = result["video_quality_score"]
            session.dual_video_metadata.down_the_line_quality_score = result["video_quality_score"]
        
        # Update primary session fields
        session.input_fps = result["input_fps"]
        session.camera_angle = result["camera_angle"]
        session.primary_camera_angle = "face_on"
        session.video_quality_score = result["video_quality_score"]
        
        from backend.core.session import Resolution
        session.resolution = Resolution(width=result["resolution"]["width"], height=result["resolution"]["height"])
        session.agent1_notes = result.get("agent1_notes", "Dual video analysis completed")
        
    else:
        # Legacy single video mode
        video_path = list(input_paths.values())[0]  # Get the first (and only) video
        
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

    # Get input video paths
    input_paths = storage.get_input_video_paths(session.session_id)
    
    if not input_paths:
        raise FileNotFoundError(f"Input video not found for {session.session_id}")
    
    if storage.is_dual_video_session(session.session_id):
        # For dual video mode, use the primary camera angle (face-on by default)
        # This can be made configurable based on requirements
        primary_angle = getattr(session, "primary_camera_angle", "face_on")
        
        if primary_angle == "face_on" and "face_on" in input_paths:
            video_path = input_paths["face_on"]
        elif primary_angle == "down_the_line" and "down_the_line" in input_paths:
            video_path = input_paths["down_the_line"]
        else:
            # Fallback to any available video
            video_path = list(input_paths.values())[0]
    else:
        # Legacy single video mode
        video_path = list(input_paths.values())[0]

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

    # Get input video paths
    input_paths = storage.get_input_video_paths(session.session_id)
    
    if not input_paths or not session.address_frame_range:
        return session
    
    if storage.is_dual_video_session(session.session_id):
        # For dual video mode, use the primary camera angle for calibration
        primary_angle = getattr(session, "primary_camera_angle", "face_on")
        
        if primary_angle == "face_on" and "face_on" in input_paths:
            video_path = input_paths["face_on"]
        elif primary_angle == "down_the_line" and "down_the_line" in input_paths:
            video_path = input_paths["down_the_line"]
        else:
            video_path = list(input_paths.values())[0]
    else:
        # Legacy single video mode
        video_path = list(input_paths.values())[0]
    
    measurements = extract_address_measurements(video_path, session.address_frame_range)
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

    # Get input video paths
    input_paths = storage.get_input_video_paths(session.session_id)
    
    if not input_paths or session.backswing_start_frame_index is None or session.follow_through_end_frame_index is None:
        return session

    if storage.is_dual_video_session(session.session_id):
        # For dual video mode, use the primary camera angle for keypoint extraction
        primary_angle = getattr(session, "primary_camera_angle", "face_on")
        
        if primary_angle == "face_on" and "face_on" in input_paths:
            video_path = input_paths["face_on"]
        elif primary_angle == "down_the_line" and "down_the_line" in input_paths:
            video_path = input_paths["down_the_line"]
        else:
            video_path = list(input_paths.values())[0]
    else:
        # Legacy single video mode
        video_path = list(input_paths.values())[0]

    out_pq = storage.session_dir(session.session_id) / "keypoints.parquet"
    extract_keypoints(
        video_path,
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
    """Implement Phase 5 — Performance Scoring.
    
    Compares all metrics against Agent 4 thresholds to produce:
    - Per-metric scores (band + score value)
    - Overall score (0-100)
    - Overall band (Beginner/Developing/Proficient)
    
    Requires:
      - session.metrics (from Phase 4)
      - session.active_thresholds (from Agent 4)
    
    Produces:
      - session.scores (Scores object with per_metric and overall)
      - session.timings.phase5_ms
    """
    from backend.phase5.scoring import score_metrics

    start_time = time.monotonic()
    
    try:
        session.scores = score_metrics(session)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        session.timings.phase5_ms = elapsed_ms
        
        if session.scores and session.scores.overall is not None:
            log_event(
                logger,
                f"Phase 5 complete (score: {session.scores.overall:.1f} / {session.scores.band_overall}, {elapsed_ms}ms)",
                session_id=session.session_id,
                phase="phase5",
                duration_ms=elapsed_ms,
                score=session.scores.overall,
                band=session.scores.band_overall,
            )
        else:
            logger.warning(f"Phase 5 produced no score")
            
    except Exception as e:
        logger.error(f"Phase 5 failed: {e}")
        session.scores = None
    
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
    """Implement Phase 7 — Enhanced Slow-Motion Rendering.
    
    Supports both single and dual video processing with enhanced features:
    - 8× frame duplication (0.125× speed) for ultra-slow motion
    - 90fps output support
    - Adaptive quality settings
    - Parallel processing for dual camera angles
    """
    from backend.phase7.slowmo import render_slowmo, render_dual_slowmo, SlowmoConfig
    
    # Check if we have the required frame indices
    if session.backswing_start_frame_index is None or session.follow_through_end_frame_index is None:
        logger.warning(f"Phase 7 skipped: missing frame indices for {session.session_id}")
        return session
    
    # Get input video paths
    input_paths = storage.get_input_video_paths(session.session_id)
    if not input_paths:
        logger.warning(f"Phase 7 skipped: no input videos found for {session.session_id}")
        return session
    
    # Create enhanced slowmo configuration
    config = SlowmoConfig(
        duplication_factor=4,  # 0.25× speed (4× frame duplication)
        enable_90fps=True,  # Enable 90fps output support
        quality_preset="high",  # High quality for better results
        enable_interpolation=False,  # Can be enabled for even smoother motion
    )
    
    session_dir = storage.session_dir(session.session_id)
    
    if storage.is_dual_video_session(session.session_id):
        # Dual video processing
        logger.info(f"Processing dual video slowmo for session {session.session_id}")
        
        if "face_on" not in input_paths or "down_the_line" not in input_paths:
            logger.error(f"Dual video session missing required videos for {session.session_id}")
            return session
        
        # Prepare output paths
        face_on_output = session_dir / "slowmo_face_on.mp4"
        dtl_output = session_dir / "slowmo_down_the_line.mp4"
        
        # Get FPS for each video
        face_on_fps = getattr(session.dual_video_metadata, "face_on_fps", None) if session.dual_video_metadata else None
        dtl_fps = getattr(session.dual_video_metadata, "down_the_line_fps", None) if session.dual_video_metadata else None
        
        # Fallback to session fps if dual metadata not available
        if face_on_fps is None:
            face_on_fps = getattr(session, "input_fps", 30.0) or 30.0
        if dtl_fps is None:
            dtl_fps = getattr(session, "input_fps", 30.0) or 30.0
        
        # Render both videos in parallel
        face_on_success, dtl_success = await render_dual_slowmo(
            input_paths["face_on"],
            input_paths["down_the_line"],
            face_on_output,
            dtl_output,
            session.backswing_start_frame_index,
            session.follow_through_end_frame_index,
            face_on_fps,
            dtl_fps,
            config
        )
        
        # Update session with results
        if face_on_success:
            session.slowmo_face_on_path = f"/api/output/{session.session_id}/slowmo/face-on"
            logger.info(f"Face-on slowmo completed: {face_on_output}")
        
        if dtl_success:
            session.slowmo_down_the_line_path = f"/api/output/{session.session_id}/slowmo/down-the-line"
            logger.info(f"Down-the-line slowmo completed: {dtl_output}")
        
        # Set legacy path to primary angle for backward compatibility
        primary_angle = getattr(session, "primary_camera_angle", "face_on")
        if primary_angle == "face_on" and face_on_success:
            session.slowmo_video_path = session.slowmo_face_on_path
        elif primary_angle == "down_the_line" and dtl_success:
            session.slowmo_video_path = session.slowmo_down_the_line_path
        elif face_on_success:
            session.slowmo_video_path = session.slowmo_face_on_path
        elif dtl_success:
            session.slowmo_video_path = session.slowmo_down_the_line_path
        
        logger.info(
            f"Dual slowmo processing complete: face_on={face_on_success}, dtl={dtl_success}",
            extra={
                "phase": "phase7",
                "event": "dual_slowmo_pipeline_complete",
                "face_on_success": face_on_success,
                "dtl_success": dtl_success,
            }
        )
        
    else:
        # Single video processing (legacy + single-with-angle)
        logger.info(f"Processing single video slowmo for session {session.session_id}")
        
        video_path = list(input_paths.values())[0]
        fps = getattr(session, "input_fps", 30.0) or 30.0
        
        # Determine output path based on camera angle
        camera_angle = getattr(session, "camera_angle", None)
        if camera_angle == "face_on":
            output_path = session_dir / "slowmo_face_on.mp4"
        elif camera_angle == "down_the_line":
            output_path = session_dir / "slowmo_down_the_line.mp4"
        else:
            # Legacy single video
            output_path = session_dir / "slowmo.mp4"
        
        success = render_slowmo(
            video_path,
            output_path,
            session.backswing_start_frame_index,
            session.follow_through_end_frame_index,
            fps,
            config
        )
        
        if success:
            # Set appropriate session paths
            if camera_angle == "face_on":
                session.slowmo_face_on_path = f"/api/output/{session.session_id}/slowmo/face-on"
                session.slowmo_video_path = session.slowmo_face_on_path
            elif camera_angle == "down_the_line":
                session.slowmo_down_the_line_path = f"/api/output/{session.session_id}/slowmo/down-the-line"
                session.slowmo_video_path = session.slowmo_down_the_line_path
            else:
                # Legacy path
                session.slowmo_video_path = f"/api/output/{session.session_id}/slowmo"
            
            logger.info(f"Single slowmo completed: {output_path}")
        else:
            logger.error(f"Single slowmo failed for {session.session_id}")
    
    return session


async def _phase8_stub(session: SessionJSON, storage: LocalStorage) -> SessionJSON:
    """Implement Phase 8 — Annotated Video Overlay with Dual Camera Support.
    
    Enhanced to support both single and dual video processing:
    - Single video: Renders one annotated video based on camera angle
    - Dual video: Renders both face-on and down-the-line annotated videos in parallel
    
    Reads:
      - slowmo video(s) from Phase 7
      - keypoints from Phase 2
      - metrics from Phase 4
      - thresholds from Agent 4
    
    Writes:
      - annotated_video_path (legacy)
      - annotated_face_on_path (dual mode)
      - annotated_down_the_line_path (dual mode)
      - Timing: phase8_ms
    """
    from backend.phase8.overlay import render_overlay, render_dual_overlay, OverlayConfig

    session_dir = storage.session_dir(session.session_id)
    
    # Check prerequisites
    if session.backswing_start_frame_index is None or session.follow_through_end_frame_index is None:
        logger.warning(f"Phase 8 skipped: missing frame indices for {session.session_id}")
        return session
    
    # Get keypoints parquet path
    keypoints_pq = session_dir / "keypoints.parquet"
    if not keypoints_pq.exists():
        logger.warning(f"Phase 8 skipped: keypoints.parquet not found for {session.session_id}")
        return session
    
    # Create overlay configuration
    config = OverlayConfig(
        show_skeleton=True,
        show_joint_dots=True,
        show_angle_overlays=True,
        show_hud=True,
        show_phase_label=True,
        angle_specific_styling=True,
    )
    
    start_time = time.monotonic()
    
    if storage.is_dual_video_session(session.session_id):
        # Dual video processing
        logger.info(f"Processing dual video overlay for session {session.session_id}")
        
        # Check for slowmo videos
        face_on_slowmo = session_dir / "slowmo_face_on.mp4"
        dtl_slowmo = session_dir / "slowmo_down_the_line.mp4"
        
        if not face_on_slowmo.exists() or not dtl_slowmo.exists():
            logger.warning(f"Phase 8 skipped: missing slowmo videos (face_on={face_on_slowmo.exists()}, dtl={dtl_slowmo.exists()})")
            return session
        
        # Prepare output paths
        face_on_output = session_dir / "annotated_face_on.mp4"
        dtl_output = session_dir / "annotated_down_the_line.mp4"
        
        try:
            # Render both overlays in parallel
            face_on_success, dtl_success = await render_dual_overlay(
                face_on_slowmo=face_on_slowmo,
                down_the_line_slowmo=dtl_slowmo,
                face_on_output=face_on_output,
                down_the_line_output=dtl_output,
                keypoints_parquet=keypoints_pq,
                session_json=session,
                start_frame=session.backswing_start_frame_index,
                end_frame=session.follow_through_end_frame_index,
                config=config
            )
            
            # Update session with results
            if face_on_success and face_on_output.exists():
                session.annotated_face_on_path = f"/api/output/{session.session_id}/annotated/face-on"
                logger.info(f"Face-on annotated video completed: {face_on_output}")
            
            if dtl_success and dtl_output.exists():
                session.annotated_down_the_line_path = f"/api/output/{session.session_id}/annotated/down-the-line"
                logger.info(f"Down-the-line annotated video completed: {dtl_output}")
            
            # Set legacy path to primary angle for backward compatibility
            primary_angle = getattr(session, "primary_camera_angle", "face_on")
            if primary_angle == "face_on" and face_on_success:
                session.annotated_video_path = session.annotated_face_on_path
            elif primary_angle == "down_the_line" and dtl_success:
                session.annotated_video_path = session.annotated_down_the_line_path
            elif face_on_success:
                session.annotated_video_path = session.annotated_face_on_path
            elif dtl_success:
                session.annotated_video_path = session.annotated_down_the_line_path
            
            # Log results
            total_size = 0
            if face_on_output.exists():
                total_size += face_on_output.stat().st_size
            if dtl_output.exists():
                total_size += dtl_output.stat().st_size
            
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            session.timings.phase8_ms = elapsed_ms
            
            if face_on_success or dtl_success:
                log_event(
                    logger,
                    f"Dual overlay complete: face_on={face_on_success}, dtl={dtl_success} ({elapsed_ms}ms, {total_size / 1_000_000:.1f}MB)",
                    session_id=session.session_id,
                    phase="phase8",
                    duration_ms=elapsed_ms,
                    face_on_success=face_on_success,
                    dtl_success=dtl_success,
                )
            else:
                logger.error(f"Phase 8 dual overlay failed completely")
                session.overlay_rendering_failed = True
        
        except Exception as e:
            logger.error(f"Phase 8 dual overlay failed: {e}")
            session.overlay_rendering_failed = True
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            session.timings.phase8_ms = elapsed_ms
    
    else:
        # Single video processing (legacy + single-with-angle)
        logger.info(f"Processing single video overlay for session {session.session_id}")
        
        # Determine camera angle and paths
        camera_angle = getattr(session, "camera_angle", "face_on")
        
        if camera_angle == "face_on":
            slowmo_video = session_dir / "slowmo_face_on.mp4"
            annotated_out = session_dir / "annotated_face_on.mp4"
        elif camera_angle == "down_the_line":
            slowmo_video = session_dir / "slowmo_down_the_line.mp4"
            annotated_out = session_dir / "annotated_down_the_line.mp4"
        else:
            # Legacy single video
            slowmo_video = session_dir / "slowmo.mp4"
            annotated_out = session_dir / "annotated.mp4"
        
        if not slowmo_video.exists():
            logger.warning(f"Phase 8 skipped: slowmo video not found ({slowmo_video})")
            return session
        
        try:
            # Render single overlay
            success = render_overlay(
                input_video=slowmo_video,
                output_video=annotated_out,
                keypoints_parquet=keypoints_pq,
                session_json=session,
                start_frame=session.backswing_start_frame_index,
                end_frame=session.follow_through_end_frame_index,
                camera_angle=camera_angle,
                config=config
            )
            
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            session.timings.phase8_ms = elapsed_ms
            
            if success and annotated_out.exists():
                # Set appropriate session paths
                if camera_angle == "face_on":
                    session.annotated_face_on_path = f"/api/output/{session.session_id}/annotated/face-on"
                    session.annotated_video_path = session.annotated_face_on_path
                elif camera_angle == "down_the_line":
                    session.annotated_down_the_line_path = f"/api/output/{session.session_id}/annotated/down-the-line"
                    session.annotated_video_path = session.annotated_down_the_line_path
                else:
                    # Legacy path
                    session.annotated_video_path = f"/api/output/{session.session_id}/annotated"
                
                log_event(
                    logger,
                    f"Single overlay complete ({camera_angle}): {elapsed_ms}ms, {annotated_out.stat().st_size / 1_000_000:.1f}MB",
                    session_id=session.session_id,
                    phase="phase8",
                    duration_ms=elapsed_ms,
                    camera_angle=camera_angle,
                )
            else:
                logger.error(f"Phase 8 single overlay failed for {camera_angle}")
                session.overlay_rendering_failed = True
        
        except Exception as e:
            logger.error(f"Phase 8 single overlay failed: {e}")
            session.overlay_rendering_failed = True
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            session.timings.phase8_ms = elapsed_ms
    
    return session
