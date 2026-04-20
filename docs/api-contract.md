# Golf Trainer AI — API Contract

All endpoints are prefixed with `/api`. All request and response bodies are JSON unless noted. All timestamps ISO-8601 UTC. All IDs are UUID v4.

Authentication is **out of scope for v1.3** — add a placeholder `X-Client-Id` header that the server logs but does not enforce, so auth can be added later without breaking URLs.

---

## 1. Sessions

### `POST /api/session`

Creates a new session and enqueues the pipeline. Returns immediately with a `session_id`.

**Request** — `multipart/form-data`:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `video` | file | yes | `.mp4` or `.mov`. Max size from `MAX_UPLOAD_MB`. |
| `gender` | string | yes | `male` or `female`. |

**Response** — `202 Accepted`:

```json
{
  "session_id": "8f9c2a1e-4b3d-4a7a-9f10-cc9c7b6a1d22",
  "status": "uploaded",
  "created_at": "2026-04-18T09:32:04Z"
}
```

**Error responses:**

| Status | Reason |
|--------|--------|
| 400 | `gender` missing or not in `{male, female}` |
| 413 | File exceeds `MAX_UPLOAD_MB` |
| 415 | File extension not in `{.mp4, .mov}` |
| 422 | Video duration exceeds `MAX_VIDEO_SECONDS` |

### `GET /api/session/{session_id}/status`

Returns the session status for polling.

**Response — 200 OK:**

```json
{
  "session_id": "8f9c2a1e-4b3d-4a7a-9f10-cc9c7b6a1d22",
  "status": "phase4_running",
  "progress_pct": 55,
  "status_reason": null,
  "failed": false
}
```

`status` is any value from the lifecycle in `data-schema.md §3`. `progress_pct` is an integer 0–100. `failed` is `true` when status is `failed`.

### `GET /api/session/{session_id}`

Returns the full session JSON. Intended for the results page. Large — only request after status is `complete`.

**Response — 200 OK:** the session JSON as defined in `data-schema.md §1`.

**Error responses:**

| Status | Reason |
|--------|--------|
| 404 | Unknown `session_id` |
| 409 | Session not complete yet (recommend polling `/status`) |

---

## 2. Phase-specific endpoints (mirror of the PRD)

These are convenience endpoints used by the frontend to render specific panels without downloading the whole JSON.

### `GET /api/phase1/detection/{session_id}`

**Response — 200 OK:**

```json
{
  "total_swing_attempts": 3,
  "selected_swing_index": 2,
  "hit_confidence_score": 0.78,
  "backswing_start_frame_index": 312,
  "impact_frame_index": 398,
  "follow_through_end_frame_index": 471
}
```

### `GET /api/phase4/results/{session_id}`

**Response — 200 OK:** the `metrics` object from the session JSON.

### `GET /api/phase5/score/{session_id}`

**Response — 200 OK:** the `scores` object from the session JSON.

### `GET /api/coaching/{session_id}`

**Response — 200 OK:** the `coaching_output` array.

---

## 3. Output endpoints

### `GET /api/output/{session_id}/slowmo/status`

**Response — 200 OK:**

```json
{ "ready": true, "path": "/api/output/{session_id}/slowmo" }
```

Use this before the frontend attempts to `<video>` the MP4, to avoid showing a broken player during rendering.

### `GET /api/output/{session_id}/slowmo`

Streams the plain slow-motion MP4 (`slowmo.mp4`) with `Content-Type: video/mp4` and `Accept-Ranges: bytes`. Supports HTTP range requests so browsers can seek.

### `GET /api/output/{session_id}/annotated/status`

Same shape as `/slowmo/status`.

### `GET /api/output/{session_id}/annotated`

Streams the annotated MP4 (`annotated.mp4`). Same headers as `/slowmo`.

### `GET /api/output/{session_id}/download/{kind}`

`{kind}` in `{slowmo, annotated}`. Sets `Content-Disposition: attachment; filename="..."` so the browser triggers a download instead of inline playback.

---

## 4. Error envelope

All non-2xx responses use a common envelope:

```json
{
  "error": {
    "code": "upload_too_large",
    "message": "File exceeds the 500 MB limit.",
    "details": { "max_mb": 500, "received_bytes": 612349512 }
  }
}
```

`code` values are snake_case and stable — frontend branches on them.

## 5. CORS and headers

- Dev: allow `http://localhost:3000`.
- Prod: allow only configured frontend origin(s).
- Responses include `Cache-Control: no-store` except the two MP4 streaming endpoints, which may set `Cache-Control: private, max-age=3600` on `200` responses once rendering is complete.

## 6. Versioning

- Prefix is `/api` (unversioned) for v1.3.
- When we break the contract, move to `/api/v2`. Do not quietly change response shapes under `/api`.
