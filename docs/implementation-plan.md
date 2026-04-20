# Golf Trainer AI — Implementation Plan

Three sprints. Total 5.5–7 weeks with a 2-person team running parallel workstreams in Sprint 2 and Sprint 3. Phases 2 and 3 are already complete from v0.2.0 and are not re-scoped.

---

## Sprint 0 — Foundations (0.5 week, before Sprint 1)

Before any phase work starts, stand up the skeleton so Sprint 1 can plug into it.

| Deliverable | Location |
|-------------|----------|
| Repo layout per `project-structure.md` | whole repo |
| FastAPI skeleton + `/api/session`, `/status` stubs | `backend/main.py`, `backend/api/routers/upload.py`, `status.py` |
| Session JSON Pydantic model | `backend/core/session.py` |
| Storage adapter (local FS) | `backend/core/storage.py` |
| Structured logger | `backend/core/logging.py` |
| Anthropic client wrapper | `backend/agents/base.py` |
| Next.js frontend skeleton (upload + progress + results pages with placeholders) | `frontend/src/app/...` |
| CI: pytest + mypy + ruff + black + eslint + tsc | `.github/workflows/` |

**Definition of done:** A user can POST a video + gender to `/api/session`, the file is persisted, a session JSON is created, status polling returns `uploaded`, and the progress page renders.

---

## Sprint 1 — Phase 1 + Agent 1 (1.5–2 weeks)

Goal: detect the real hit, and make the pipeline adaptive to video metadata before any analysis happens.

| # | Deliverable | File / location |
|---|-------------|-----------------|
| 1.1 | **Agent 1 — Video Intelligence** | `backend/agents/video_intelligence_agent.py` |
| 1.2 | **Phase 1 — Hit Detection** modules | `backend/phase1/{hit_detector.py, swing_segmenter.py, optical_flow_utils.py, models.py}` |
| 1.3 | Orchestrator updated to call Agent 1 then Phase 1 | `backend/orchestrator/pipeline.py` |
| 1.4 | API endpoint | `GET /api/phase1/detection/{session_id}` in `backend/api/routers/phase1.py` |
| 1.5 | Unit tests for hit detection | `backend/tests/test_hit_detection.py` |

**Agent 1 acceptance:**
- Emits `input_fps`, `camera_angle`, `video_quality_score`, `resolution`, `agent1_notes` to the session JSON.
- Correctly classifies the 10 provided fixture videos into face-on vs down-the-line (at least 9/10).

**Phase 1 acceptance (from PRD §8):**

| Test case | Expected result |
|-----------|-----------------|
| 1 real swing only | `selected_index=0`, confidence > 0.60 |
| 1 dummy + 1 real | `selected_index=1` |
| 2 dummy + 1 real | `selected_index=2` |
| 3 dummy + 1 real | `selected_index=3`, confidence > 0.65 |
| Dummy swings only | `is_real=False`, no crash |

**Status transitions added this sprint:** `agent1_running → agent1_done → phase1_running → phase1_done`.

---

## Sprint 2 — Phases 4 + 7 + Agents 2 + 3 (2 weeks)

Goal: full biomechanical measurement and the slow-motion video. Two engineers can split this:
- Engineer A: Agent 2 + Agent 3 + Phase 4.
- Engineer B: Phase 7 video processor.

| # | Deliverable | File / location |
|---|-------------|-----------------|
| 2.1 | **Agent 2 — Body Calibration** | `backend/agents/body_calibration_agent.py` |
| 2.2 | **Agent 3 — Shot Classifier** | `backend/agents/shot_classification_agent.py` |
| 2.3 | **Phase 4 — Biomechanical Metrics** (all 13) | `backend/phase4/measurements.py` |
| 2.4 | **Phase 7 — Slow-Motion Rendering** | `backend/orchestrator/video_processor.py` with `render_slowmo_clip()` and `get_output_video_path()` |
| 2.5 | API endpoints | `GET /api/phase4/results/{session_id}`, `GET /api/output/{session_id}/slowmo`, `.../slowmo/status` |
| 2.6 | Tests | `backend/tests/{test_biomech_metrics.py, test_video_processor.py, test_agents.py}` |

**Agent 2 acceptance:**
- For a fixture with known real-world shoulder width, `px_to_inches_scale` is within ±5% of ground truth.
- Sets `calibration_low_confidence=true` when given fewer than 10 stable address frames.

**Agent 3 acceptance:**
- Correctly classifies at least 8/10 of the fixture setups across driver / mid iron / short iron / chip.
- Returns a `shot_type_confidence` field that is reasonable (high for obvious driver, lower for ambiguous setups).

**Phase 4 acceptance:**
- All 13 metrics are computed for a clean fixture with no `null` values.
- When keypoints are occluded at impact (synthetic test frame), `wrist_lag` is `null` with `null_reason` set.
- Each metric has its own unit test that seeds synthetic keypoints and asserts an expected value within tolerance.

**Phase 7 acceptance (from PRD §8):**

| Test case | Expected result |
|-----------|-----------------|
| 10-second input video | Output file exists, duration longer than input |
| Backswing frame detection | Frame within first 60% of swing |
| Valid MP4 output | `cv2.VideoCapture` opens and reads frames without error |
| 0.25× speed applied | Critical section has ~4× frame count vs source |

**Status transitions added:** `agent2_running`, `agent2_done`, `phase2_running`, `phase2_done`, `phase3_running`, `phase3_done` *(Phase 2 and Phase 3 code already exists from v0.2.0; these transitions are wired into the orchestrator for the first time here)*, `agent3_running`, `agent3_done`, `phase4_running`, `phase4_done`, `phase7_running`, `phase7_done`.

---

## Sprint 3 — Phases 5 + 6 + 8 + Agents 4 + 5 (2–3 weeks)

Goal: session scoring, coaching, and the annotated output. The pipeline is feature-complete by the end of this sprint.

| # | Deliverable | File / location |
|---|-------------|-----------------|
| 3.1 | **Agent 4 — Threshold Adaptation** | `backend/agents/threshold_agent.py` |
| 3.2 | **Phase 5 — Performance Scoring** (consumes `active_thresholds`, no hardcoded ranges) | `backend/phase5/scoring.py` |
| 3.3 | **Agent 5 — Coaching (Phase 6)** | `backend/agents/coaching_agent.py` |
| 3.4 | **Phase 8 — Annotated Video Overlay** | `backend/orchestrator/overlay_renderer.py` — `_draw_skeleton`, `_draw_joint_dots`, `_draw_bottom_hud`, 5 angle overlays, `_draw_phase_label`, `_draw_frame_counter` |
| 3.5 | API endpoints | `GET /api/phase5/score/{session_id}`, `GET /api/coaching/{session_id}`, `GET /api/output/{session_id}/annotated`, `.../annotated/status` |
| 3.6 | Frontend results page | `frontend/src/app/results/[sessionId]/` — annotated video primary, slow-mo tab, metrics panel, coaching output, score card |
| 3.7 | Tests | `backend/tests/{test_overlay_renderer.py, test_threshold_agent.py, test_coaching_agent.py}` |

**Agent 4 acceptance:**
- Emits an `active_thresholds` entry for every one of the 13 metrics.
- For a beginner profile (low X-factor, high sway, variable tempo), widens green and amber ranges relative to an advanced profile.
- Narrows ranges for scratch-level input.

**Phase 5 acceptance:**
- Zero hardcoded thresholds in the file. `grep -n "5.0\|35\|50" backend/phase5/scoring.py` returns nothing meaningful.
- Produces a per-metric score + overall score + band.

**Agent 5 acceptance:**
- Returns 2–4 items in `coaching_output`, ordered by priority, with exactly one `priority: 1`.
- For any `severity: "high"` item, the `explanation` references at least two metrics and names a causal link between them.
- Does not reference metrics whose value is `null` in the session JSON.

**Phase 8 acceptance (from PRD §8):**

| Test case | Expected result |
|-----------|-----------------|
| Skeleton on test frame | All limb lines at correct keypoint positions |
| Joint dots present | Concentric circles at all keypoints |
| HUD panel visible | Black panel bottom 18–20%; all metric labels present |
| Spine within 5° | Spine line drawn green |
| Spine beyond 5° | Spine line drawn red |
| Tempo 3.0:1 male | HUD tempo label green |
| Tempo 5.0:1 male | HUD tempo label red |
| Valid annotated MP4 | `cv2.VideoCapture` opens and reads correctly |

**Frontend acceptance:**
- Annotated video is the hero on the results page.
- Slow-mo tab plays the plain slow-mo video.
- Metrics panel shows all 13 metrics with target ranges from `active_thresholds`.
- Coaching output shows the priority-1 item prominently, with supporting items beneath.
- Score card shows `scores.overall` and `scores.band_overall`.

---

## Cross-sprint definition of done

A session run end-to-end on a fresh 15-second / 60fps / 1080p video satisfies all of:

1. Two MP4s produced: `slowmo.mp4` (plain) and `annotated.mp4` (with skeleton + overlays + HUD).
2. All 13 metrics populated in `session.json` (or explicitly `null` with `null_reason`).
3. `coaching_output` is a valid array with a priority-1 item.
4. `scores.overall` is a number in [0, 100].
5. `status = "complete"`.
6. Pipeline total time < 3 minutes on reference infrastructure.
7. No file outside `storage/{session_id}/` is written.

## Parallelisation notes

- Sprint 2 splits cleanly: Phase 7 (engineer B) has zero overlap with Agents 2/3/Phase 4 (engineer A). They only meet at the session JSON contract, which is frozen after Sprint 0.
- Sprint 3 splits less cleanly because Phase 8 depends on Agent 4's thresholds (for colour coding), Phase 5's scores, and Agent 5's coaching. Build Phase 8's renderer against mock JSON first, then wire the real inputs last.

## Timeline

| Sprint | Weeks | Running total |
|--------|-------|---------------|
| Sprint 0 | 0.5 | 0.5 |
| Sprint 1 | 1.5–2 | 2–2.5 |
| Sprint 2 | 2 | 4–4.5 |
| Sprint 3 | 2–3 | 6–7.5 |

Target: **6 calendar weeks** with a 2-person team. **7.5 weeks** realistic with buffer for fixture creation and polish.
