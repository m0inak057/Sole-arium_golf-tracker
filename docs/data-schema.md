# Golf Trainer AI — Data Schema

The session JSON is the single source of truth between phases. This document defines it exhaustively. Every phase and every agent reads specific fields from it and writes specific fields into it.

---

## 1. Session JSON — canonical shape

```jsonc
{
  // ─── Set by API on upload ────────────────────────────────────────
  "schema_version": "1.3",
  "session_id": "8f9c2a1e-4b3d-4a7a-9f10-cc9c7b6a1d22",
  "created_at": "2026-04-18T09:32:04Z",
  "gender": "male",                       // "male" | "female" — only user-provided field besides video
  "status": "complete",                   // see §3 below
  "status_reason": null,                  // string if status is "failed"

  // ─── Set by Agent 1 (Video Intelligence) ─────────────────────────
  "input_fps": 59.94,
  "camera_angle": "face_on",              // "face_on" | "down_the_line"
  "video_quality_score": 0.82,            // 0.0 – 1.0
  "resolution": { "width": 1920, "height": 1080 },
  "agent1_notes": "Clean lighting, minor camera shake in first second.",

  // ─── Set by Phase 1 (Hit Detection) ──────────────────────────────
  "total_swing_attempts": 3,
  "selected_swing_index": 2,              // 0-indexed
  "hit_confidence_score": 0.78,           // 0.0 – 1.0
  "backswing_start_frame_index": 312,
  "impact_frame_index": 398,
  "follow_through_end_frame_index": 471,
  "address_frame_range": [280, 310],      // frames the golfer was still before the selected swing

  // ─── Set by Agent 2 (Body Calibration) ───────────────────────────
  "px_to_inches_scale": 0.112,
  "calibration_low_confidence": false,
  "calibration_notes": "Derived from shoulder width (avg 182 px over 30 address frames).",

  // ─── Set by Phase 2 (Keypoints) — stored separately ──────────────
  "keypoints_path": "storage/{session_id}/keypoints.parquet",

  // ─── Set by Phase 3 (Setup Analysis) ─────────────────────────────
  "setup_metrics": {
    "stance_width_px": 246,
    "ball_position_ratio": 0.52,          // 0 = back foot, 1 = front foot
    "spine_tilt_deg_at_address": 23.4,
    "grip_position": "neutral"
  },

  // ─── Set by Agent 3 (Shot Classification) ────────────────────────
  "detected_shot_type": "mid_iron",       // driver | long_iron | mid_iron | short_iron | chip_pitch
  "shot_type_confidence": 0.74,
  "shot_type_reasoning": "Stance width ≈ shoulder width, ball roughly centred, moderate spine tilt.",

  // ─── Set by Phase 4 (Biomechanical Metrics) ──────────────────────
  "metrics": {
    "tempo_ratio":        { "value": 3.1,  "unit": "ratio",   "primary": true,  "null_reason": null },
    "x_factor":           { "value": 42.0, "unit": "deg",     "primary": true,  "null_reason": null },
    "spine_deviation_max":{ "value": 6.2,  "unit": "deg",     "primary": true,  "null_reason": null },
    "hip_sway":           { "value": 2.1,  "unit": "inches",  "primary": true,  "null_reason": null },
    "head_sway":          { "value": 1.2,  "unit": "inches",  "primary": true,  "null_reason": null },
    "hip_turn":           { "value": 48.0, "unit": "deg",     "primary": true,  "null_reason": null },
    "shoulder_turn":      { "value": 92.0, "unit": "deg",     "primary": true,  "null_reason": null },
    "side_bend":          { "value": 11.0, "unit": "deg",     "primary": true,  "null_reason": null },
    "hips_open":          { "value": 38.0, "unit": "deg",     "primary": true,  "null_reason": null },
    "wrist_lag":          { "value": null, "unit": "deg",     "primary": false, "null_reason": "lead_wrist_visibility_below_0.5_at_impact" },
    "knee_flex_left":     { "value": 28.0, "unit": "deg",     "primary": true,  "null_reason": null },
    "knee_flex_right":    { "value": 29.5, "unit": "deg",     "primary": true,  "null_reason": null },
    "stance_width":       { "value": 27.6, "unit": "inches",  "primary": true,  "null_reason": null }
  },

  // ─── Set by Agent 4 (Threshold Adaptation) ───────────────────────
  "inferred_skill_level": "intermediate",  // beginner | intermediate | advanced | scratch
  "active_thresholds": {
    "tempo_ratio":         { "green": [2.8, 3.3],  "amber": [2.5, 3.8], "red_below": 2.5, "red_above": 3.8 },
    "x_factor":            { "green": [35, 50],    "amber": [30, 55],   "red_below": 30,  "red_above": 55 },
    "spine_deviation_max": { "green_max": 5,       "amber_max": 10,     "red_above": 10 },
    "hip_sway":            { "green_max": 2.5,     "amber_max": 4,      "red_above": 4 },
    "head_sway":           { "green_max": 2,       "amber_max": 3.5,    "red_above": 3.5 },
    "hip_turn":            { "green": [40, 55],    "amber": [30, 65],   "red_below": 30,  "red_above": 65 },
    "shoulder_turn":       { "green": [85, 100],   "amber": [75, 110],  "red_below": 75,  "red_above": 110 },
    "side_bend":           { "green": [5, 15],     "amber": [0, 20],    "red_above": 20 },
    "hips_open":           { "green": [30, 45],    "amber": [20, 55],   "red_below": 20,  "red_above": 55 },
    "wrist_lag":           { "green_min": 15,      "amber_min": 10,     "red_below": 10 },
    "knee_flex":           { "green": [20, 30],    "amber": [15, 35],   "red_below": 15,  "red_above": 35 },
    "stance_width":        { "green_ratio": [0.95, 1.05], "amber_ratio": [0.85, 1.15] }
  },

  // ─── Set by Phase 5 (Performance Scoring) ────────────────────────
  "scores": {
    "per_metric": {
      "tempo_ratio":         { "band": "green", "score": 1.0 },
      "x_factor":            { "band": "green", "score": 1.0 },
      "spine_deviation_max": { "band": "amber", "score": 0.5 },
      "hip_sway":            { "band": "green", "score": 1.0 },
      "head_sway":           { "band": "green", "score": 1.0 },
      "hip_turn":            { "band": "green", "score": 1.0 },
      "shoulder_turn":       { "band": "green", "score": 1.0 },
      "side_bend":           { "band": "green", "score": 1.0 },
      "hips_open":           { "band": "green", "score": 1.0 },
      "wrist_lag":           { "band": null,    "score": null },
      "knee_flex_left":      { "band": "green", "score": 1.0 },
      "knee_flex_right":     { "band": "green", "score": 1.0 },
      "stance_width":        { "band": "green", "score": 1.0 }
    },
    "overall": 88.6,
    "band_overall": "Proficient"         // Developing | Proficient | Advanced
  },

  // ─── Set by Agent 5 == Phase 6 (Coaching) ────────────────────────
  "coaching_output": [
    {
      "priority": 1,
      "severity": "high",
      "title": "Reduce late-downswing spine deviation",
      "explanation": "Your spine drifts 6.2° from address at impact. This pairs with a slight 2.1″ hip sway earlier in the downswing — the sway forces your spine to compensate, which is costing you consistency rather than power.",
      "drill_suggestion": "Alignment-stick hip-bump drill: ..."
    },
    {
      "priority": 2,
      "severity": "medium",
      "title": "...",
      "explanation": "...",
      "drill_suggestion": "..."
    }
  ],

  // ─── Set by Phase 7 ──────────────────────────────────────────────
  "slowmo_video_path": "storage/{session_id}/slowmo.mp4",

  // ─── Set by Phase 8 ──────────────────────────────────────────────
  "annotated_video_path": "storage/{session_id}/annotated.mp4",
  "overlay_rendering_failed": false,

  // ─── Observability ───────────────────────────────────────────────
  "timings": {
    "agent1_ms": 480,
    "phase1_ms": 2240,
    "agent2_ms": 310,
    "phase2_ms": 6800,
    "phase3_ms": 180,
    "agent3_ms": 620,
    "phase4_ms": 520,
    "agent4_ms": 540,
    "phase5_ms": 80,
    "agent5_ms": 1600,                   // Agent 5 IS Phase 6 — no separate phase6_ms
    "phase7_ms": 1200,
    "phase8_ms": 5400,
    "total_ms": 19970
  }
}
```

## 2. Metric entry shape (strict)

Every entry in `metrics` uses this shape:

```jsonc
{
  "value": <number | null>,
  "unit": "deg" | "ratio" | "inches" | "cm",
  "primary": <bool>,                       // false if the current camera angle cannot measure this well
  "null_reason": <string | null>           // required if value is null
}
```

**Allowed `null_reason` values** (add new ones as needed, but use snake_case):
- `lead_wrist_visibility_below_0.5_at_impact`
- `camera_angle_incompatible_with_metric`
- `keypoint_occluded_behind_body`
- `insufficient_frames_for_calculation`
- `calibration_unavailable`

## 3. Status lifecycle

```
uploaded → agent1_running → agent1_done
        → phase1_running  → phase1_done
        → agent2_running  → agent2_done
        → phase2_running  → phase2_done
        → phase3_running  → phase3_done
        → agent3_running  → agent3_done
        → phase4_running  → phase4_done
        → agent4_running  → agent4_done
        → phase5_running  → phase5_done
        → agent5_running  → agent5_done    # == phase6_done
        → phase7_running  → phase7_done
        → phase8_running  → phase8_done
        → complete
```

Plus terminal states: `failed`.

On `failed`, `status_reason` must be one of a controlled vocabulary (add values here as they arise):

- `unreadable_video`
- `no_real_swing_detected`
- `agent1_malformed_output`
- `agent2_malformed_output`
- `agent3_malformed_output`
- `agent4_malformed_output`
- `agent5_malformed_output`
- `internal_error`

## 4. Keypoints store

Keypoints live outside the session JSON because they are large. The schema for the parquet file:

| column | type | description |
|--------|------|-------------|
| `frame_index` | int | 0-indexed frame number |
| `landmark_id` | int | MediaPipe landmark enum value |
| `x_norm` | float | 0.0–1.0 |
| `y_norm` | float | 0.0–1.0 |
| `z_norm` | float | MediaPipe depth estimate |
| `visibility` | float | 0.0–1.0 |

Any row with `visibility < 0.5` is considered unusable. Producers should still write the row so downstream debugging is possible — consumers must filter.

## 5. Coaching output entry

```jsonc
{
  "priority": <int>,                       // 1 is top priority; only 1 item has priority=1
  "severity": "high" | "medium" | "low",
  "title": "Reduce late-downswing spine deviation",
  "explanation": "...",                    // must reference at least one specific metric and at least one other metric it is causally linked to when severity=high
  "drill_suggestion": "..."                // optional but recommended
}
```

**Rules:**
- The `coaching_output` array is **ordered by priority ascending**. Index 0 is the priority-1 item.
- At most one item has `priority: 1`.
- If severity is `high`, the explanation must reference a *combination* of faults, not a single metric in isolation. This is how we avoid rule-based-if-else output.

## 6. Units and conventions

- Angles in degrees.
- Linear distances in the session JSON: `hip_sway` and `head_sway` in **inches**. `stance_width` in **inches**.
- Overlay 5 (Stance Bracket) displays stance width in **cm** on-screen (PRD §4.3). Convert at render time.
- Frame indices are absolute into the original uploaded video (not the slow-mo output).
- Timestamps in ISO-8601 UTC.

## 7. Mirroring in TypeScript

Frontend types in `frontend/src/lib/types.ts` must mirror this schema exactly. Use a codegen step if you prefer — or maintain by hand and check in CI. A mismatch between backend and frontend types is a bug.
