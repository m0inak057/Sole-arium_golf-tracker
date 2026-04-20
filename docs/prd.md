# Golf Trainer AI — Product Requirements Document

**Version:** 1.3 (engineering-ready)
**Status:** Ready for development
**Product type:** Web-based B2B/B2C software platform
**Only user input:** Video upload + gender selection

---

## 1. Product definition

Golf Trainer AI takes a raw video of a golf swing shot from one of two standard angles and automatically produces:

- A slow-motion annotated MP4 with a connected skeleton, biomechanical angle overlays, and a live HUD panel.
- A plain slow-motion MP4 (no overlays).
- A metrics JSON with 13 biomechanical measurements.
- Personalised coaching text written by an AI coach.

The product is delivered as a web app accessible in a browser. The target buyers are golf academies, training centres, coaches, and serious amateur/professional golfers on subscription or per-session pricing. **Output quality must be professional coaching grade.**

## 2. In scope vs out of scope

**In scope (v1.3):**
- Two supported camera angles: Face-On and Down-the-Line.
- Auto-detection of camera angle, FPS, video quality, golfer's body proportions, and shot type.
- 8 analysis phases + 5 AI agents.
- Full-swing, impact-only, and setup measurements.
- Web UI: upload page, progress page, results page.
- Two MP4 outputs, one JSON, one coaching block.

**Out of scope (v1.3):**
- Club tracking (we do not require a club-mounted sensor).
- 3D reconstruction.
- Multi-golfer videos.
- Comparison with another golfer's swing.
- Mobile native apps (iOS/Android). The web app must work on mobile browsers, but native apps are a later phase.
- Live streaming / real-time analysis. Only uploaded videos.

## 3. User flow (end to end)

1. User opens the web app.
2. User uploads a video (MP4, MOV — max size and duration enforced by API, see `api-contract.md`).
3. User selects **Male** or **Female** (radio, required, default unset).
4. User clicks **Analyse**.
5. Backend runs the full pipeline (see `architecture.md`). Typical time: a few minutes.
6. Frontend polls status endpoints and shows a progress view.
7. When complete, the results page displays: annotated video (primary), plain slow-mo video (secondary tab), metrics panel, coaching text, score card.
8. User can download both MP4s.

## 4. Camera angles

| Angle | What it captures best |
|-------|------------------------|
| Face-On | Hip sway, head sway, stance width, weight shift, spine tilt |
| Down-the-Line | Swing plane, spine angle, wrist lag, club path, shoulder turn |

The system auto-detects which angle was uploaded using keypoint geometry (Agent 1). The correct measurement set and thresholds are then applied automatically. Users **do not** select the angle.

## 5. Pipeline overview

The pipeline is 8 sequential phases connected by 5 AI agents. Phases contain deterministic code. Agents replace all decision-making that would otherwise be hardcoded.

```
[Video + Gender]
        │
        ▼
   Agent 1 (Video Intelligence)
        │
        ▼
   Phase 1 (Hit Detection)
        │
        ▼
   Agent 2 (Body Calibration)
        │
        ▼
   Phase 2 (Keypoints) — already complete (v0.2.0)
        │
        ▼
   Phase 3 (Setup Analysis) — already complete (v0.2.0)
        │
        ▼
   Agent 3 (Shot Classifier)
        │
        ▼
   Phase 4 (Biomechanical Metrics)
        │
        ▼
   Agent 4 (Threshold Adaptation)
        │
        ▼
   Phase 5 (Performance Scoring)
        │
        ▼
   Agent 5 (Coaching) — this agent IS Phase 6
        │
        ▼
   Phase 7 (Slow-Motion Rendering)
        │
        ▼
   Phase 8 (Annotated Video Overlay)
        │
        ▼
[annotated.mp4 + slowmo.mp4 + session.json + coaching_output]
```

**Key principle:** Phases do not call each other directly. Every phase reads from the session JSON and writes back to the session JSON. Agents sit between phases and transform the JSON.

Full phase-by-phase contracts are in [`architecture.md`](./architecture.md).

## 6. The five AI agents (summary)

| Agent | Replaces | Inserted between |
|-------|----------|------------------|
| 1. Video Intelligence | FPS warnings + manual camera angle input | Upload and Phase 1 |
| 2. Body Calibration | Hardcoded 17–18 in shoulder width | Phase 1 and Phase 2 |
| 3. Shot Classification | Shot-type dropdown in UI | Phase 3 and Phase 4 |
| 4. Threshold Adaptation | Hardcoded thresholds (spine=5°, X-factor=35–50°, etc.) | Phase 4 and Phase 5 |
| 5. Coaching Recommendation | Rule-based if/else feedback | IS Phase 6 |

Full prompt templates and I/O schemas are in [`agent-prompts.md`](./agent-prompts.md).

## 7. Core features

### 7.1 Real Hit Detection (Phase 1)

Detects every swing attempt in the uploaded video, classifies each as REAL or DUMMY (practice), and passes only the real swing frames to downstream phases. **Users never trim their video.**

Signals and weights:

| Signal | Method | Weight |
|--------|--------|--------|
| Wrist-snap velocity | Wrist keypoint velocity spike then sharp drop at real impact (ball resistance). Absent/weak in dummies. | 0.5 |
| Hip drop | Sharp downward shift of lead hip at impact — stronger on real hits. | 0.3 |
| Ball motion (optional) | `cv2.calcOpticalFlowPyrLK` detects sudden large displacement in lower-centre of frame. | 0.2 |

**Decision rule:** Weighted sum > 0.65 = REAL. Highest-scoring real swing is the one analysed.

### 7.2 Smart Slow-Motion (Phase 7)

Produces an MP4 where the critical window (backswing-start through follow-through-end) plays at 0.25× speed. The rest plays at normal speed.

| Frame marker | How detected |
|--------------|--------------|
| Backswing start | Lead-wrist velocity changes direction — detected in Phase 2 |
| Impact frame | Identified by Phase 1 |
| Follow-through end | 3 seconds after impact, OR wrist keypoints reach max height and decelerate — whichever first |

**Rendering:** Each frame in the critical window is written 4× to output. Simple, hardware-agnostic, no interpolation. H.264 at original FPS.

### 7.3 Annotated Overlay Video (Phase 8)

The primary deliverable. Takes the Phase 7 slow-mo MP4 and burns three rendering layers onto it.

**Layer 1 — Connected skeleton**

| Body region | Keypoints connected | Colour |
|-------------|---------------------|--------|
| Lower body (both legs) | Hip → Knee → Ankle → Foot | Cyan `#00D4FF` |
| Hip line | Left Hip ↔ Right Hip | Cyan |
| Upper body (torso + arms) | Shoulders ↔ Shoulders, Shoulder → Elbow → Wrist | Yellow `#FFD700` |
| Torso sides | Left Shoulder → Left Hip, Right Shoulder → Right Hip | Yellow |
| Joint dots | Every keypoint: white inner circle + coloured outer ring | Cyan or Yellow |

**Layer 2 — Angle overlays**

| Overlay | What is drawn | When shown |
|---------|---------------|------------|
| X-Factor arc | Arc between hip line and shoulder line at torso mid, with degree value. Green 35–50°, amber outside, red at extremes. | Backswing → follow-through |
| Spine axis line | Line hip-mid → shoulder-mid, degree label. Green < 5° deviation, red > 5°. | Downswing to impact (most critical) |
| Wrist lag angle | Arc at lead wrist. Green > 15°, amber 10–15°, red < 10°. | Impact frame ±5 frames only |
| Knee flex + weight shift | Angle label at each knee. Arrow showing transfer direction + speed. | Full swing |
| Stance bracket | Double-headed arrow between ankles, width in cm. Colour-coded by detected shot type. | Setup / address only |

> **Note:** The colour ranges above (e.g. "Green 35–50°") are reference defaults for illustration. At runtime, overlay colours are driven by `active_thresholds` from Agent 4 — never hardcoded.

**Layer 3 — Bottom HUD panel**

A full-width solid black panel at the bottom (~18–20% of frame height). Three sections:

- **Left:** Swing phase label (yellow, large) + orange progress bar + Tempo Ratio + X-Factor + Hip Sway + Head Sway.
- **Centre:** Logo / branding.
- **Right:** Hip Turn + Shoulder Turn + Side Bend + Hips Open.

**Swing phase labels:**

| State | Label text | Colour |
|-------|-----------|--------|
| Idle / between | `SETUP / BETWEEN SWINGS` | White |
| Address | `>>> ADDRESS <<<` | White bold |
| Backswing | `SWING #N — BACKSWING` | Yellow |
| Downswing | `SWING #N — DOWNSWING` | Yellow |
| Impact | `SWING #N — IMPACT` | Green |
| Follow-through | `SWING #N — FOLLOW-THROUGH` | Yellow |

## 8. Biomechanical metrics

All calculated in Phase 4. Agent 4 sets the acceptable range for each per session.

| Metric | Calculation | Displayed in |
|--------|-------------|--------------|
| Tempo Ratio | Backswing duration / downswing duration. Target: 3:1 male, 4:1 female. | HUD + Phase 5 score |
| X-Factor | Angle between hip-line and shoulder-line vectors at mid-torso. | Overlay A + HUD |
| Spine Deviation | Delta between setup spine angle and current-frame spine angle. | Overlay B, per frame |
| Hip Sway | Horizontal delta of mid-hip from address frame. Inches via Agent 2. | HUD |
| Head Sway | Horizontal delta of nose keypoint from address frame. Inches via Agent 2. | HUD |
| Hip Turn | Rotation of hip line from address angle, degrees. | HUD right |
| Shoulder Turn | Rotation of shoulder line from address angle, degrees. | HUD right |
| Side Bend | Lateral tilt of torso vector from vertical, degrees. | HUD right |
| Hips Open | Hip rotation angle relative to target line at impact. | HUD right |
| Wrist Lag | Angle at lead wrist between forearm direction and club-shaft direction. | Overlay D |
| Knee Flex (L/R) | Angle at each knee between thigh and shin keypoints. | Overlay E |
| Stance Width | Pixel distance between ankle keypoints, converted via Agent 2. | Overlay C |

**Low-confidence rule:** MediaPipe returns a visibility score per landmark. Any keypoint with visibility < 0.5 is **skipped** — no line drawn, no angle calculated, metric stored as `null` in the session JSON. Critical for frames where arms cross behind the body at top of backswing.

## 9. Deliverables to the golfer

| Deliverable | Description |
|-------------|-------------|
| Annotated slow-motion MP4 | **Primary output.** Skeleton + angles + HUD panel + slow-mo at critical moment. Downloadable. |
| Plain slow-motion MP4 | Same video without overlays. Downloadable. |
| Metrics panel | All 13 biomechanical measurements with per-metric targets (from Agent 4). |
| Personalised coaching text | Written by Agent 5. Explains fault *combinations*, prioritised by severity, one clear focus item. |

## 10. Success criteria

- Annotated video renders at original aspect ratio with zero keypoint jitter on clean 60 fps input.
- All 13 metrics populate (or are explicitly `null`) for a clean input.
- Agent 3 shot-type classification matches PGA definitions for the clubs used in test fixtures.
- Agent 5 coaching text references *combinations* of faults, not just isolated ones.
- End-to-end turnaround on a typical 15-second input is under 3 minutes on the reference infrastructure.
- Test suite in [`testing.md`](./testing.md) passes in CI before any deploy.

## 11. Non-goals / anti-patterns (read before coding)

- **Do not add dropdowns.** Shot type comes from Agent 3. Camera angle comes from Agent 1. Skill level comes from Agent 4 inputs. If you feel the urge to ship a dropdown, the answer is a new agent or a richer agent input — not a UI element.
- **Do not hardcode thresholds in Phase 4 or Phase 5 code.** Read from `active_thresholds` on the session JSON.
- **Do not hardcode body proportions.** Read from `px_to_inches_scale` on the session JSON.
- **Do not skip low-confidence keypoints silently.** Emit `null` in the JSON and log a reason.
- **Do not couple phases to each other.** Phase N reads/writes the session JSON. Phase N does not import Phase N−1.

---

*See [`architecture.md`](./architecture.md) for how this is implemented.*
