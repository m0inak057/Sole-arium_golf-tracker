# Golf Trainer AI — Project Structure

The exact folder and file layout. Create the repo to match this tree. Do not invent additional top-level folders without updating this document first.

---

```
golf-trainer-ai/
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml                    # Python project, Poetry or uv
│
├── docs/                              # These engineering docs live here
│   ├── README.md
│   ├── prd.md
│   ├── architecture.md
│   ├── project-structure.md
│   ├── data-schema.md
│   ├── api-contract.md
│   ├── agent-prompts.md
│   ├── rules.md
│   ├── implementation-plan.md
│   └── testing.md
│
├── backend/
│   ├── __init__.py
│   ├── main.py                       # FastAPI entrypoint
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py             # POST /api/session
│   │   │   ├── status.py             # GET /api/session/{id}/status
│   │   │   ├── phase1.py             # GET /api/phase1/detection/{session_id}
│   │   │   ├── phase4.py             # GET /api/phase4/results/{session_id}
│   │   │   ├── phase5.py             # GET /api/phase5/score/{session_id}
│   │   │   ├── output.py             # slowmo, annotated, status endpoints
│   │   │   └── coaching.py           # GET /api/coaching/{session_id}
│   │   ├── dto.py                    # Pydantic request/response models
│   │   └── deps.py                   # FastAPI dependencies
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── pipeline.py               # runs the 8 phases + 5 agents
│   │   ├── video_processor.py        # render_slowmo_clip, get_output_video_path
│   │   └── overlay_renderer.py       # _draw_skeleton, _draw_joint_dots,
│   │                                  # _draw_bottom_hud, _draw_phase_label,
│   │                                  # _draw_frame_counter, all 5 angle overlays
│   │
│   ├── phase1/
│   │   ├── __init__.py
│   │   ├── hit_detector.py
│   │   ├── swing_segmenter.py
│   │   ├── optical_flow_utils.py
│   │   └── models.py                 # Pydantic models for Phase 1 outputs
│   │
│   ├── phase2/                       # ALREADY EXISTS (v0.2.0) — do not rewrite
│   │   ├── __init__.py
│   │   └── keypoints.py
│   │
│   ├── phase3/                       # ALREADY EXISTS (v0.2.0) — do not rewrite
│   │   ├── __init__.py
│   │   └── setup_analysis.py
│   │
│   ├── phase4/
│   │   ├── __init__.py
│   │   └── measurements.py           # all 13 metrics
│   │
│   ├── phase5/
│   │   ├── __init__.py
│   │   └── scoring.py                # consumes active_thresholds from Agent 4
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                   # shared Anthropic client, JSON-only contract, retry
│   │   ├── video_intelligence_agent.py
│   │   ├── body_calibration_agent.py
│   │   ├── shot_classification_agent.py
│   │   ├── threshold_agent.py
│   │   └── coaching_agent.py         # Agent 5 == Phase 6
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── session.py                # SessionJSON Pydantic model + load/save
│   │   ├── storage.py                # local / S3 adapters
│   │   ├── config.py                 # env var loading
│   │   ├── logging.py                # structured JSON logger
│   │   ├── keypoints_store.py        # parquet/json.gz for keypoints blob
│   │   └── colors.py                 # constants: CYAN, YELLOW, GREEN, etc.
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── fixtures/                 # small synthetic .mp4 clips + expected JSONs
│       ├── test_hit_detection.py
│       ├── test_biomech_metrics.py
│       ├── test_video_processor.py
│       ├── test_overlay_renderer.py
│       ├── test_agents.py            # calibration + shot classification
│       ├── test_threshold_agent.py
│       ├── test_coaching_agent.py
│       └── test_end_to_end.py
│
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── globals.css
│       │   ├── page.tsx              # upload
│       │   ├── progress/
│       │   │   └── [sessionId]/
│       │   │       └── page.tsx
│       │   └── results/
│       │       └── [sessionId]/
│       │           ├── page.tsx
│       │           ├── AnnotatedVideo.tsx
│       │           ├── SlowMoTab.tsx
│       │           ├── MetricsPanel.tsx
│       │           ├── CoachingOutput.tsx
│       │           └── ScoreCard.tsx
│       ├── components/
│       │   ├── ui/                   # buttons, inputs, toasts
│       │   └── VideoPlayer.tsx
│       ├── lib/
│       │   ├── api.ts                # typed fetch wrappers
│       │   └── types.ts              # TypeScript mirror of data-schema.md
│       └── hooks/
│           └── useSessionPolling.ts
│
└── storage/                          # gitignored in dev
    └── {session_id}/
        ├── input.mp4                 # original upload
        ├── session.json              # the session JSON
        ├── keypoints.parquet         # large blob
        ├── slowmo.mp4                # Phase 7 output
        └── annotated.mp4             # Phase 8 output
```

## Naming conventions

- **Python:** `snake_case` for files, modules, functions, variables. `PascalCase` for classes.
- **TypeScript:** `camelCase` for variables and functions, `PascalCase` for components and types.
- **Files under `storage/`:** `{session_id}` is a UUID. Files inside the session folder use the short names above; the long form `{session_id}__slowmo.mp4` etc. from the PRD is used when referring to a file *outside* its session folder.
- **Session JSON file path:** always `storage/{session_id}/session.json`.

## Already-complete modules (do not rewrite)

- `backend/phase2/` — keypoint extraction. Verify its output conforms to `data-schema.md`. If it does not, write an adapter in `backend/core/keypoints_store.py`, do not modify Phase 2.
- `backend/phase3/` — setup analysis. Same rule.

## Where the 13 Phase 4 metrics live

All 13 live in `backend/phase4/measurements.py`. One function per metric, plus one `compute_all_metrics(session)` that composes them. This makes per-metric testing trivial.

## Where the overlay rendering lives

All overlay logic is in `backend/orchestrator/overlay_renderer.py`. No drawing code lives anywhere else. Each public function has a single responsibility:

- `_draw_skeleton(frame, keypoints) -> frame`
- `_draw_joint_dots(frame, keypoints) -> frame`
- `_draw_angle_overlay_xfactor(frame, keypoints, x_factor_deg, thresholds) -> frame`
- `_draw_angle_overlay_spine(frame, keypoints, spine_dev_deg, thresholds) -> frame`
- `_draw_angle_overlay_wrist_lag(frame, keypoints, wrist_lag_deg, thresholds) -> frame`
- `_draw_angle_overlay_knee(frame, keypoints, knee_flex_deg, weight_shift_vec) -> frame`
- `_draw_angle_overlay_stance(frame, keypoints, stance_cm, shot_type) -> frame`
- `_draw_bottom_hud(frame, metrics, phase_label, progress) -> frame`
- `_draw_phase_label(frame, phase_state, swing_number) -> frame`
- `_draw_frame_counter(frame, frame_index, total_frames) -> frame`

The orchestrator calls these in the order defined in `architecture.md §4` (skeleton → dots → overlays → HUD).
