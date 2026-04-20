# Golf Trainer AI — Testing

Test strategy, fixtures, and the exact test cases lifted from the PRD. These are **acceptance criteria**, not suggestions.

---

## 1. Test strategy

Three layers:

1. **Unit tests** — per phase, per agent, per overlay function. Fast, no I/O, no Anthropic calls.
2. **Integration tests** — the orchestrator runs all phases against a fixture video; verifies the session JSON and MP4 outputs.
3. **End-to-end test** — spin up the FastAPI server, POST a video, poll to completion, verify outputs. Runs in CI against 2–3 canonical fixtures.

**Agents are never tested against the real Anthropic API.** A `FakeAnthropicClient` returns canned JSON loaded from `backend/tests/fixtures/agents/`. Each agent has at least one "happy path" canned response and at least one "malformed output" canned response to exercise the retry path.

## 2. Fixtures

Location: `backend/tests/fixtures/`.

| Fixture | Purpose |
|---------|---------|
| `videos/clean_face_on_60fps.mp4` | Clean input for happy-path tests (~10 sec, 1080p, 60 fps) |
| `videos/clean_dtl_60fps.mp4` | Clean down-the-line input |
| `videos/low_fps_30.mp4` | 30 fps to exercise Agent 1's FPS adaptation |
| `videos/two_dummies_one_real.mp4` | Phase 1 hit-detection test |
| `videos/three_dummies_one_real.mp4` | Phase 1 hit-detection test |
| `videos/dummies_only.mp4` | Phase 1 negative test |
| `videos/low_quality_shaky.mp4` | Agent 1 low-quality path, Agent 4 widened thresholds |
| `expected/clean_face_on_60fps.session.json` | Golden session JSON to diff against |
| `agents/agent1_face_on.response.json` | Canned Agent 1 response for unit tests |
| `agents/agent1_malformed.response.txt` | Canned malformed response |
| `agents/agent2_happy.response.json` | Canned Agent 2 response |
| ... | ... per agent |

Fixture videos can be synthesised — a 2D animated stick figure performing a swing is enough to drive MediaPipe in many tests. Keep fixture size small (< 5 MB each).

## 3. Per-sprint test requirements

### Sprint 1 — `test_hit_detection.py`

Directly from PRD §8:

| Test case | Expected result |
|-----------|-----------------|
| 1 real swing only | `selected_index=0`, `hit_confidence_score > 0.60` |
| 1 dummy + 1 real | `selected_index=1` |
| 2 dummy + 1 real | `selected_index=2` |
| 3 dummy + 1 real | `selected_index=3`, `hit_confidence_score > 0.65` |
| Dummy swings only | `is_real=False`, session status becomes `failed` with reason `no_real_swing_detected`, no crash |

Plus for Agent 1:
- Given a face-on fixture, Agent 1 returns `camera_angle == "face_on"`.
- Given a down-the-line fixture, returns `camera_angle == "down_the_line"`.
- Given a malformed Anthropic response, the agent retries once then fails the session with `status_reason == "agent1_malformed_output"`.

### Sprint 2 — `test_biomech_metrics.py`, `test_video_processor.py`, `test_agents.py`

**Phase 4 — one test per metric.** Example shape:
- Seed synthetic keypoints where the hip line is at 20° and shoulder line is at 65°. Assert `x_factor == 45.0 ± 0.5`.
- Seed occluded lead wrist at impact (visibility 0.3). Assert `wrist_lag.value is None` and `null_reason == "lead_wrist_visibility_below_0.5_at_impact"`.

**Phase 7 — from PRD §8:**

| Test case | Expected result |
|-----------|-----------------|
| 10-second input video | Output file exists, duration longer than input |
| Backswing frame detection | Frame within first 60% of swing |
| Valid MP4 output | `cv2.VideoCapture` opens and reads frames without error |
| 0.25× speed applied | Critical section has ~4× frame count vs source |

**Agent 2:**
- Given address-frame measurements for a 6'0" male, `px_to_inches_scale` × observed shoulder width is within ±5% of 18 inches.
- Given <10 stable address frames, `calibration_low_confidence == true`.

**Agent 3:**
- Given fixture setup metrics for a driver (wide stance, forward ball), returns `detected_shot_type == "driver"`.
- Given a chip setup (narrow stance, ball back), returns `detected_shot_type == "chip_pitch"`.

### Sprint 3 — `test_overlay_renderer.py`, `test_threshold_agent.py`, `test_coaching_agent.py`

**Phase 8 — from PRD §8:**

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

Implementation tip: the colour tests are easiest to write by rendering a single frame to a numpy array and asserting the pixel colour at the known label location, not by parsing OpenCV state.

**Agent 4:**
- Given a beginner-profile input, `active_thresholds` green ranges are at least 20% wider than an advanced-profile input for the same shot type.
- Emits an entry for all 13 metrics.

**Agent 5:**
- Returns an array with length in `[2, 4]`.
- Exactly one entry has `priority == 1`.
- Any `severity == "high"` entry has an `explanation` that mentions at least two distinct metric names.
- Does not mention any metric whose session-JSON value is `null`.

## 4. CI gate

The following must all pass before merging to main:

- `pytest backend/tests -v`
- `mypy --strict backend/`
- `ruff check backend/`
- `black --check backend/`
- `cd frontend && npm run lint && npm run typecheck`
- No new `TODO` or `FIXME` in diff without an owner name and a date.

## 5. Manual smoke tests (pre-deploy)

Before each release, a human runs this checklist:

1. Upload a real phone-shot 1080p/60fps face-on video. Expect complete in < 3 min.
2. Upload a down-the-line video. Same.
3. Upload a video with 3 practice swings then one real hit. Verify `selected_swing_index == 3` (0-indexed).
4. Upload a 30 fps video. Verify thresholds widen (check `video_quality_score`, `active_thresholds`).
5. Download both MP4s. Play in VLC. Verify slow-mo window is correct and overlays are stable.
6. Confirm coaching output references specific numbers and a causal link between two faults.

If any of these fail, the release is blocked.
