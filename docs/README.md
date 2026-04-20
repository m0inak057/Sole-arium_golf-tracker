# Golf Trainer AI — Engineering Documentation

This folder contains the complete specification for building **Golf Trainer AI** from scratch. Read the documents in the order listed below. Every document is authoritative — if any of them conflict with assumptions you are tempted to make, the document wins.

## What this product is (one paragraph)

Golf Trainer AI is a web-based B2B/B2C platform. A golfer uploads a swing video and selects their gender. The backend runs an 8-phase pipeline orchestrated by 5 AI agents, and returns two MP4s (plain slow-motion + annotated slow-motion with skeleton, angle overlays and a HUD panel), a metrics JSON, and personalised coaching text. No other user input exists. No hardcoded thresholds. No dropdowns. Target quality is professional coaching standard.

## Read these documents in order

| # | Document | What it answers |
|---|----------|-----------------|
| 1 | [`prd.md`](./prd.md) | What are we building and why |
| 2 | [`architecture.md`](./architecture.md) | How the system is structured, how data flows, what lives where |
| 3 | [`project-structure.md`](./project-structure.md) | Exact folder/file layout for the monorepo |
| 4 | [`data-schema.md`](./data-schema.md) | Session JSON schema — the contract every phase and agent reads/writes |
| 5 | [`api-contract.md`](./api-contract.md) | Every HTTP endpoint, request and response shape |
| 6 | [`agent-prompts.md`](./agent-prompts.md) | Prompt templates and tool contracts for all 5 AI agents |
| 7 | [`rules.md`](./rules.md) | Non-negotiable coding rules, agent rules, and quality bar |
| 8 | [`implementation-plan.md`](./implementation-plan.md) | Sprint-by-sprint work breakdown with acceptance criteria |
| 9 | [`testing.md`](./testing.md) | Test strategy, fixtures, and the exact test cases from the PRD |

## Golden rules (applies everywhere, do not violate)

1. **Only two user inputs exist: the uploaded video, and the gender radio selection.** Never add a dropdown, form field, or required toggle to the UI without explicit approval.
2. **No hardcoded thresholds anywhere in analysis code.** Every threshold comes from `active_thresholds` produced by Agent 4.
3. **No hardcoded body measurements.** Every pixel-to-real-world conversion uses `px_to_inches_scale` produced by Agent 2.
4. **No hardcoded shot type.** The shot type comes from Agent 3.
5. **Low-confidence keypoints (visibility < 0.5) are never used.** The affected metric is written as `null` in the session JSON. Never guess.
6. **Session JSON is the single source of truth between phases.** Phases do not call each other directly.
7. **All 5 agents use Claude (`claude-sonnet-4-5` or later). They return structured JSON only — no prose wrapping the JSON.**
8. **schema_version is always `"1.3"` on every new session.** Bump on breaking changes only.
9. **The output annotated MP4 is the product.** Everything else (metrics panel, coaching text) is supporting material.

## What "done" looks like

A new user visits the web app, uploads a 15-second swing video, clicks a male/female radio button, hits submit, waits a few minutes, and receives (a) an annotated slow-motion MP4 with skeleton + overlays + HUD, (b) a plain slow-motion MP4, (c) a metrics panel with all 13 measurements and per-metric targets, (d) personalised coaching text ordered by severity with one clear priority focus. The system handled FPS detection, camera-angle detection, calibration, shot classification, threshold selection, and fault combination reasoning without asking the user a single additional question.
