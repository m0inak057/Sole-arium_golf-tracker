# Golf Trainer AI — Engineering Rules

Non-negotiable rules. Apply everywhere. Violations are treated as bugs in review.

---

## 1. Product rules (the ones you will be tempted to break)

1. **Only two user inputs exist:** the uploaded video file and the `male`/`female` radio. Never add a dropdown, advanced options panel, or "power user" toggle. If a new piece of information is needed, it comes from an agent — not the user.
2. **No hardcoded thresholds in Phase 4 or Phase 5.** Every threshold is read from `active_thresholds` on the session JSON (produced by Agent 4). If you write a literal like `5.0  # spine deviation` in an analysis module, it is a bug.
3. **No hardcoded body proportions.** Every px↔inches conversion uses `px_to_inches_scale` from Agent 2. Never assume shoulder width is 17 in.
4. **No hardcoded shot type.** Shot type comes from Agent 3.
5. **Low-confidence keypoints are never used.** MediaPipe visibility < 0.5 → no line drawn, no angle computed, metric stored as `null` in the session JSON with a `null_reason`.
6. **Phases do not call each other.** Phase N reads from the session JSON and writes to the session JSON. `from backend.phase3 import ...` inside `backend/phase4/` is a bug.
7. **Agents do not call phases and phases do not call agents.** The orchestrator is the only thing that knows about sequence.
8. **`schema_version` is `"1.3"`** on every new session. Bumping it requires updating `data-schema.md` first.

## 2. Code rules (Python backend)

- Python 3.11+. Type hints everywhere. `mypy --strict` passes in CI.
- Pydantic v2 for every DTO and every agent I/O shape.
- `black` + `ruff` for formatting and linting. Line length 100.
- No circular imports. `backend/core/` depends on nothing else in `backend/`.
- Logging: use the logger from `backend/core/logging.py`. `print()` is banned outside scripts.
- Every public function has a docstring with one-line summary + `Args` + `Returns`.
- No silent exception swallowing. Either handle it with a documented recovery or let it propagate.
- No global mutable state.

## 3. Code rules (TypeScript frontend)

- TypeScript strict mode.
- No `any`. Use `unknown` + a narrowing type guard.
- Server components by default (Next.js App Router). Client components only for things that need state or effects.
- Tailwind CSS v3 for styling. No inline style objects unless dynamic.
- All network access goes through `frontend/src/lib/api.ts`. Do not `fetch` in components directly.
- TS types for the session JSON mirror `data-schema.md` exactly. A mismatch is a bug.

## 4. Agent rules

- Every agent returns a single JSON object matching a Pydantic schema. Nothing else.
- Every agent's raw prompt and response are persisted to `storage/{session_id}/agents/agent{N}.{prompt|response}.txt` for debugging.
- Retry on malformed JSON exactly once, with a stricter system-level reminder. Then fail the session.
- Agents have no side effects other than writing agent output to the session JSON and writing debug files.
- Agents do not talk to each other. They only read the session JSON and write to it.

## 5. Storage rules

- Session folder layout is fixed: `storage/{session_id}/{input.mp4, session.json, keypoints.parquet, slowmo.mp4, annotated.mp4, agents/}`.
- Do not embed large blobs (keypoints, raw frames) in the session JSON. Use a side file and reference it by path.
- Every write to `session.json` is atomic: write to `session.json.tmp` then `rename`. Never leave a partially written JSON on disk.

## 6. Rendering rules (overlay + HUD)

- Rendering layer order is strict: **skeleton lines → joint dots → angle overlays → HUD panel**. Never change this order.
- Colour constants live in `backend/core/colors.py`. **OpenCV uses BGR order, not RGB.** All constants are stored as `(B, G, R)` tuples and suffixed with `_BGR` to prevent confusion:
  - `CYAN_BGR = (255, 212, 0)` → hex `#00D4FF`
  - `YELLOW_BGR`, `GREEN_BGR`, `AMBER_BGR`, `RED_BGR`, `WHITE_BGR`, `BLACK_BGR`.
- HUD panel height is 18–20% of frame height. Always full-width. Always the last thing drawn.
- Angle label colour is driven by the session's `active_thresholds` for that metric. Do not hardcode "green = value < 5".
- Every overlay respects the visibility rule: if any keypoint feeding it has visibility < 0.5, the overlay is not drawn for that frame.

## 7. Performance rules

- End-to-end pipeline on a typical 15-second 1080p/60fps input must complete in under 3 minutes on the reference infrastructure.
- Phase 8 runs frame-by-frame — keep per-frame work under 50 ms average. Batch any per-frame Anthropic calls into one agent call before/after, never inside the render loop.
- No agent is called per-frame. Ever.

## 8. Testing rules

- Every new public function has at least one unit test.
- The test cases from the PRD (see `testing.md`) are treated as acceptance criteria — not aspirations.
- CI runs `pytest` + `mypy --strict` + `ruff` + `black --check` + frontend `tsc --noEmit` + `eslint`. All must pass before merge.
- Tests never call the Anthropic API. Agent tests use a fake Anthropic client that returns canned JSON from fixtures.

## 9. Naming

- Session field names in the JSON are `snake_case`.
- Python module and variable names are `snake_case`.
- Python class names are `PascalCase`.
- TypeScript component files and component identifiers are `PascalCase.tsx`.
- TypeScript variable and function names are `camelCase`.
- File constants: `UPPER_SNAKE_CASE`.

## 10. Commits and PRs

- One sprint deliverable = one PR (or a small stack). Keep PRs reviewable (< 800 lines of non-generated diff where possible).
- PR title format: `[Sprint N] <phase or agent name>: <what changed>`.
- PR description must include: what changed, what session JSON fields are affected, how to test.

## 11. When in doubt

- If the docs are silent or contradict each other: `prd.md` > `architecture.md` > `data-schema.md` > everything else.
- If you find yourself arguing "this hardcoded value is fine because it's just a default", stop. That's the exact pattern the agent architecture exists to eliminate.
