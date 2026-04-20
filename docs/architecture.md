# Golf Trainer AI — Architecture

This document defines how the system is structured. If you're writing code, this is the shape of the thing you're writing it inside.

---

## 1. High-level architecture

Three tiers:

1. **Frontend** — Next.js (App Router) + TypeScript + Tailwind CSS v3. Three screens: upload, progress, results. Calls the backend REST API.
2. **Backend API** — FastAPI (Python 3.11+). Thin HTTP layer in front of the Orchestrator. Stateless.
3. **Orchestrator + Pipeline** — Python worker. Runs the 8 phases and 5 agents in sequence. Reads/writes the session JSON and two MP4 artifacts.

```
┌────────────────┐      ┌─────────────────┐      ┌────────────────────────┐
│   Next.js UI   │ HTTP │   FastAPI API   │      │      Orchestrator      │
│ upload/results │◄────►│  thin handlers  │◄────►│  8 phases + 5 agents   │
└────────────────┘      └─────────────────┘      └─────────┬──────────────┘
                                                            │
                                            ┌───────────────┴───────────────┐
                                            ▼                               ▼
                                    ┌────────────────┐            ┌───────────────────┐
                                    │ Object storage │            │   Anthropic API   │
                                    │  (S3 / local)  │            │  (claude-sonnet)  │
                                    │ .mp4 + .json   │            │    for agents     │
                                    └────────────────┘            └───────────────────┘
```

**Why this shape:**
- Pipeline is slow and CPU/GPU-bound. It runs async in a worker, not inline with HTTP.
- Session JSON is the single source of truth between phases — it makes debugging trivial and testing straightforward.
- Agents only talk to the pipeline, never the user.

## 2. Execution model

- Upload → creates a session, enqueues a job, returns `session_id` + `202 Accepted`.
- Frontend polls `GET /api/session/{id}/status` for phase progress (`uploaded`, `agent1_done`, `phase1_done`, … , `complete`, `failed`).
- Worker process executes the pipeline. It updates the session JSON after every phase/agent.
- When `complete`, frontend fetches the result endpoints and renders the results page.

**Queue:** Start with an in-process thread pool + SQLite-backed job table for v1. Swap to Redis + RQ/Celery when concurrency > 1 machine. The orchestrator must not care.

## 3. Session JSON — the contract

Full schema is in [`data-schema.md`](./data-schema.md). The essentials:

- Every phase and every agent reads fields from the session JSON and writes new fields into it.
- Phases do not import other phases. Agents do not import phases.
- `schema_version` is always `"1.3"`.
- The session JSON is persisted to `{session_id}__session.json` at every phase boundary.

**Ownership of fields:**

| Field | Written by |
|-------|------------|
| `schema_version`, `session_id`, `created_at`, `gender` | API (on upload) |
| `input_fps`, `camera_angle`, `video_quality_score` | Agent 1 |
| `total_swing_attempts`, `selected_swing_index`, `hit_confidence_score`, `impact_frame_index`, `backswing_start_frame_index`, `follow_through_end_frame_index`, `address_frame_range` | Phase 1 |
| `px_to_inches_scale`, `calibration_notes` | Agent 2 |
| `keypoints_per_frame` (or path to it) | Phase 2 |
| `setup_metrics` (stance width px, ball position, spine tilt at address) | Phase 3 |
| `detected_shot_type`, `shot_type_confidence` | Agent 3 |
| all 13 Phase 4 metrics (see `data-schema.md`) | Phase 4 |
| `active_thresholds` | Agent 4 |
| `scores` (per-metric + overall) | Phase 5 |
| `coaching_output` (array, ordered by severity) | Agent 5 (== Phase 6) |
| `slowmo_video_path` | Phase 7 |
| `annotated_video_path` | Phase 8 |

## 4. Pipeline — phase-by-phase

### Agent 1 — Video Intelligence *(before Phase 1)*
- **Input:** Uploaded video file, file metadata.
- **Does:** Reads video metadata (FPS, resolution). Samples a few frames, runs MediaPipe, inspects keypoint geometry to classify camera angle (`face_on` vs `down_the_line`). Produces a 0.0–1.0 video quality score.
- **Output on JSON:** `input_fps`, `camera_angle`, `video_quality_score`, `resolution`, `notes`.
- **Failure mode:** If the video is unreadable, mark session as `failed` with reason `unreadable_video`.

### Phase 1 — Hit Detection
- **Input:** Video file, Agent 1 outputs.
- **Does:** Runs MediaPipe across all frames. For every candidate swing motion, computes the three signals (wrist-snap, hip-drop, optical-flow) with weights 0.5 / 0.3 / 0.2. Scores each attempt. Any attempt with score > 0.65 is REAL. The highest-scoring REAL becomes `selected_swing_index`.
- **Output on JSON:** `total_swing_attempts`, `selected_swing_index`, `hit_confidence_score`, `impact_frame_index`, `backswing_start_frame_index`, `follow_through_end_frame_index`, `address_frame_range`.
- **Failure mode:** If no REAL swing detected, mark `failed` with reason `no_real_swing_detected`.

### Agent 2 — Body Calibration *(between Phase 1 and Phase 2)*
- **Input:** Address frames from Phase 1 (golfer standing still before swing), Agent 1 outputs.
- **Does:** Runs MediaPipe on the address frames, measures stable keypoint distances (shoulder-width, torso length, arm length), derives a `px_to_inches_scale` personal to this golfer.
- **Output on JSON:** `px_to_inches_scale`, `calibration_notes` (what distances were used, what the assumed real-world anchor was).
- **Failure mode:** If address frames are too few or too noisy, fall back to a conservative population-mean scale and flag `calibration_low_confidence: true`. Downstream metrics that depend on calibration are still produced but flagged.

### Phase 2 — Keypoints *(already complete, carried over from v0.2.0)*
- **Input:** Video file + REAL swing frame range + Agent 2 calibration.
- **Does:** Extracts MediaPipe keypoints for every frame in the swing. Stores `(x_norm, y_norm, visibility)` per landmark per frame. Any landmark with visibility < 0.5 is marked unusable but not dropped.
- **Output on JSON:** `keypoints_per_frame_path` (separate file — keypoints are large).

### Phase 3 — Setup Analysis *(already complete, carried over from v0.2.0)*
- **Input:** Phase 2 keypoints, Agent 1 camera angle.
- **Does:** On the address frame, measures stance width (px), ball position relative to feet (estimated from lowest-foreground points), spine tilt at setup, grip position.
- **Output on JSON:** `setup_metrics` object.

### Agent 3 — Shot Classification *(between Phase 3 and Phase 4)*
- **Input:** Phase 3 `setup_metrics`, Agent 2 `px_to_inches_scale`, Agent 1 `camera_angle`.
- **Does:** Classifies shot type as one of `driver`, `long_iron`, `mid_iron`, `short_iron`, `chip_pitch` using stance-width-to-shoulder ratio, ball position relative to feet, spine tilt, and camera angle context.
- **Output on JSON:** `detected_shot_type`, `shot_type_confidence`, `shot_type_reasoning`.
- **Failure mode:** If confidence < 0.5, set `detected_shot_type` to best guess with `shot_type_confidence` recorded. Do not block.

### Phase 4 — Biomechanical Metrics
- **Input:** Phase 2 keypoints, Agent 2 calibration, Agent 1 camera angle.
- **Does:** Computes all 13 metrics (see PRD §8). Every metric calculation respects the visibility < 0.5 rule — write `null` if keypoints are unusable.
- **Output on JSON:** `metrics` object with the 13 fields.
- **Note:** Camera angle drives which metrics are primary vs secondary. E.g. swing-plane angles are only reliable on down-the-line. Metrics that are camera-inappropriate are still emitted but flagged `primary: false`.

### Agent 4 — Threshold Adaptation *(between Phase 4 and Phase 5)*
- **Input:** `detected_shot_type` (Agent 3), `camera_angle` (Agent 1), `video_quality_score` (Agent 1), `gender` (user input), and an inferred skill level (from metric variance / tempo consistency — rules in `agent-prompts.md`).
- **Does:** Produces `active_thresholds` — a JSON object giving green/amber/red ranges for every metric for this session.
- **Output on JSON:** `active_thresholds`, `inferred_skill_level`.

### Phase 5 — Performance Scoring
- **Input:** Phase 4 metrics + Agent 4 `active_thresholds`.
- **Does:** For each metric, scores the golfer's value against the session thresholds (green/amber/red → 1.0 / 0.5 / 0.0 weighted). Produces a weighted overall score 0–100.
- **Note on `stance_width`:** Unlike other metrics that use absolute ranges, `stance_width` thresholds are ratio-based (`green_ratio`, `amber_ratio`). Phase 5 must compute `observed_width / shot_type_target_width` and compare the resulting ratio against these ranges. The shot-type target width is derived from the `detected_shot_type` and `gender`.
- **Output on JSON:** `scores.per_metric`, `scores.overall`, `scores.band` (e.g. "Developing", "Proficient", "Advanced").

### Phase 6 — AI Coaching *(IS Agent 5)*
- **Input:** The full session JSON after Phase 5.
- **Does:** Reads the combination of faults, identifies causal chains (e.g. "early hip sway causes spine compensation causes reduced X-factor"), and writes coaching text ordered by severity. Returns **one priority focus** and 2–4 supporting items.
- **Output on JSON:** `coaching_output` array (each item: `priority`, `title`, `explanation`, `drill_suggestion`).

### Phase 7 — Slow-Motion Rendering
- **Input:** Original video + Phase 1 frame markers.
- **Does:** Writes an MP4 where frames in `[backswing_start, follow_through_end]` are each written 4× (0.25× speed) and other frames are written once. H.264 at original FPS.
- **Output on JSON:** `slowmo_video_path` → `{session_id}__slowmo.mp4`.

### Phase 8 — Annotated Video Overlay
- **Input:** The Phase 7 slow-mo MP4 + Phase 2 keypoints + Phase 4 metrics + Agent 4 thresholds + Agent 5 coaching + Phase 1 frame markers.
- **Does:** For every frame in the slow-mo video, draws the three layers (skeleton → joint dots → angle overlays → HUD panel) in that order. Writes the result as `{session_id}__annotated.mp4`.
- **Output on JSON:** `annotated_video_path`.

**Rendering layer order (strict):**

| Order | Layer | Rationale |
|-------|-------|-----------|
| 1st | Skeleton limb lines (`cv2.line`) | Must be underneath everything else |
| 2nd | Joint dots (`cv2.circle`) | On top of lines so dots appear clean |
| 3rd | Angle overlay labels | On top of skeleton |
| 4th | Bottom HUD panel | Always last, always on top |

## 5. Backend module layout

See [`project-structure.md`](./project-structure.md) for the full tree. Summary:

```
backend/
├── api/                        # FastAPI app, routers, DTOs
├── orchestrator/               # pipeline runner, video_processor, overlay_renderer
├── phase1/                     # hit_detector, swing_segmenter, optical_flow_utils, models
├── phase2/                     # keypoints extraction (already exists)
├── phase3/                     # setup analysis (already exists)
├── phase4/                     # measurements.py — all 13 metrics
├── phase5/                     # scoring
├── agents/                     # video_intelligence, body_calibration, shot_classification, threshold, coaching
├── core/                       # session JSON model, storage, config, logging
└── tests/
```

Every agent gets its own module and only imports from `core/` and the Anthropic SDK. No agent imports any phase. No phase imports any agent.

## 6. Frontend structure

```
frontend/src/app/
├── page.tsx                    # upload page
├── progress/[sessionId]/       # polling UI
└── results/[sessionId]/        # annotated video primary, slow-mo tab, metrics, coaching, score
```

Results page is the most important UI surface. The annotated video is the hero. Metrics and coaching sit beneath the video.

## 7. Storage

- **Videos and JSON** — Object storage. Local filesystem in dev (`./storage/{session_id}/`). S3 in production.
- **Sessions table** — SQLite in dev, Postgres in production. Stores `session_id`, status, timestamps, path to session JSON.
- **Keypoints** — Stored in a separate `{session_id}__keypoints.parquet` (or json.gz) because they are large and we should not inline them in the session JSON.

## 8. Observability

- Structured JSON logs (stdout). Every log entry has `session_id`, `phase`, `agent`, and `event`.
- Time every phase and every agent. Emit `duration_ms` in the session JSON under `timings`.
- If an agent returns malformed JSON, log the raw response and retry once with a stricter prompt; then fail the session with reason `agent_{n}_malformed_output`.

## 9. Configuration

All config via environment variables. See `.env.example` in the repo. Required:

- `ANTHROPIC_API_KEY`
- `ANTHROPIC_MODEL` — default `claude-sonnet-4-5`
- `STORAGE_BACKEND` — `local` | `s3`
- `STORAGE_LOCAL_PATH` or S3 bucket/region/keys
- `MAX_UPLOAD_MB` — default 500
- `MAX_VIDEO_SECONDS` — default 30

## 10. Error handling philosophy

- Fail fast on unrecoverable problems (unreadable video, no swing detected, agent permanent failure). Mark session `failed` with a machine-readable reason and a human-readable message.
- Degrade gracefully on soft problems (low-quality video, low-confidence calibration, low-confidence shot type). Annotate the JSON with `*_low_confidence: true` and proceed.
- Never produce a broken MP4. If Phase 8 cannot render, fall back to returning the Phase 7 plain slow-mo as `annotated_video_path` and mark `overlay_rendering_failed: true`.

---

*See [`data-schema.md`](./data-schema.md) for the full session JSON. See [`agent-prompts.md`](./agent-prompts.md) for what each agent actually asks Claude.*
