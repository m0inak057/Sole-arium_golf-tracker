# Combined Slowmo + Annotated Video Pipeline — Diagnostics

## What You Should See

### If Working Correctly:

**Logs should show:**
```
Phase 7: Starting slowmo rendering for both angles...
  Face-on slowmo completed: /path/to/slowmo_face_on.mp4
  Down-the-line slowmo completed: /path/to/slowmo_down_the_line.mp4

Phase 8: Reading slowmo videos and applying overlays...
  Input (slowmo from Phase 7): /path/to/slowmo_face_on.mp4
  Input (slowmo from Phase 7): /path/to/slowmo_down_the_line.mp4
  
✓ FINAL: Face-on combined video (slowmo + overlay) created
✓ FINAL: Down-the-line combined video (slowmo + overlay) created
```

**Files created in session directory:**
```
session_123/
├── slowmo_face_on.mp4 (Phase 7 output, temporary, for Phase 8 to read)
├── slowmo_down_the_line.mp4 (Phase 7 output, temporary, for Phase 8 to read)
├── annotated_face_on.mp4 ← FINAL COMBINED VIDEO (slowmo + overlay)
└── annotated_down_the_line.mp4 ← FINAL COMBINED VIDEO (slowmo + overlay)
```

**Final Output Videos:**
- `annotated_face_on.mp4` = slowmo_face_on.mp4 + metrics overlay applied
- `annotated_down_the_line.mp4` = slowmo_down_the_line.mp4 + metrics overlay applied

### What's Currently Happening (If Not Working):

If you're seeing separate slowmo and annotated videos that are different:

**Problem 1: Phase 7 Not Creating Slowmo Videos**
- Logs show: `Phase 8 FAILED: missing slowmo videos from Phase 7`
- Check: Phase 7 rendering failed
- Fix: Debug Phase 7 (video processing, FPS, codec issues)

**Problem 2: Phase 8 Not Reading From Slowmo**
- Logs show: `✗ FINAL: combined video FAILED`
- Check: Are annotated videos being created from original input instead of slowmo?
- This would mean render_overlay is receiving wrong input_video path

**Problem 3: File Naming Issue**
- If files exist but paths don't match expected names
- Check: Session is dual_video vs single_video mode
- Verify: camera_angle is set correctly

## How to Debug

### Step 1: Check Session Status
Run this to see what Phase 7 created:
```bash
ls -la /path/to/storage/session_id/
```

Look for:
- `slowmo_face_on.mp4` ✓ (should exist)
- `slowmo_down_the_line.mp4` ✓ (should exist)

### Step 2: Check Logs for Phase 7 & 8 Messages
Look for these specific log messages:
- `Phase 7: slowmo render results:`
- `Phase 8: Overlay render results:`
- `✓ FINAL:` (success) or `✗ FINAL:` (failure)

### Step 3: Verify File Sizes
Slowmo files should be:
- Same or larger than original videos (due to frame duplication)
- Example: If original is 10MB, slowmo might be 40MB (4× frames)

Annotated files should be:
- Same size as slowmo files (just overlay added, no size change)

### Step 4: Check API Endpoints
```bash
# Check what files API is serving
curl http://localhost:8000/api/output/{session_id}/status/all

# Should show something like:
{
  "annotated": {
    "face_on": {
      "ready": true,
      "path": "/api/output/{id}/annotated/face-on"
    }
  }
}
```

## Expected Video Metadata

When you check the final combined video properties, you should see:
- **Face-on combined video:**
  - FPS: 90 or based on original (from slowmo)
  - Duration: ~4× longer than original (due to frame duplication in Phase 7)
  - Contains both skeleton overlays AND metrics HUD

- **Down-the-line combined video:**
  - Same duration as face-on
  - Angle-specific metrics overlay

## If Still Having Issues

1. **Check Phase 7 Config** (`backend/orchestrator/pipeline.py` line ~545)
   - `duplication_factor=4` (for 0.25× speed)
   - `quality_preset="high"`

2. **Verify Phase 8 Input Video Path** (`backend/orchestrator/pipeline.py` line ~715)
   - Must read from `slowmo_face_on.mp4`, NOT from original input
   - Must NOT have fallback to original input videos

3. **Run with Logging Enabled**
   ```bash
   LOG_LEVEL=DEBUG python -m uvicorn backend.main:app
   ```
   This will show detailed Phase 7 & 8 execution logs

## The Complete Flow

```
INPUT VIDEOS
    ↓
[Phase 7] Generate Slowmo
    Input: input_face_on.mp4, input_down_the_line.mp4
    Output: slowmo_face_on.mp4 (4× slower), slowmo_down_the_line.mp4 (4× slower)
    ↓
[Phase 8] Apply Overlays to Slowmo Videos
    Input: slowmo_face_on.mp4, slowmo_down_the_line.mp4
    Process: Read frame → Draw skeleton → Draw metrics → Write to output
    Output: annotated_face_on.mp4 (FINAL), annotated_down_the_line.mp4 (FINAL)
    ↓
FINAL OUTPUT
    annotated_face_on.mp4 = Slowmo video WITH metrics overlay
    annotated_down_the_line.mp4 = Slowmo video WITH metrics overlay
```

The key is: **Phase 8 must read from slowmo, not from original input.**

