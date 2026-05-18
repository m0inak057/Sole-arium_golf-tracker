# Golf Trainer 2 — AI-Powered Golf Swing Analysis

## 🎯 Project Overview

Golf Trainer 2 is an advanced AI system that analyzes golf swing videos using computer vision and machine learning. It processes single or dual-camera video inputs through an 8-phase pipeline with 5 AI agents to provide detailed biomechanical analysis and personalized coaching feedback.

**Status**: ✅ Core functionality complete (204/204 tests passing - 100%)

---

## 📦 Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.12)
- **Video Processing**: OpenCV, FFmpeg
- **AI/ML**: Google Gemini AI, MediaPipe
- **Database/Storage**: Local filesystem with JSON sessions
- **Code Quality**: Type hints throughout, comprehensive logging

### Frontend
- **Framework**: Next.js 14 (React 18+)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Video Player**: HTML5 native player with streaming support

---

## 🏗️ Project Structure

```
golf-trainer-2/
├── backend/
│   ├── api/
│   │   ├── routers/          # API endpoints (upload, status, output, coaching)
│   │   ├── dto.py            # Data models & response schemas
│   │   └── deps.py           # Dependency injection
│   ├── core/
│   │   ├── session.py        # Session models & lifecycle
│   │   ├── storage.py        # Video & data persistence
│   │   ├── config.py         # Environment & settings
│   │   ├── logging.py        # Structured logging
│   │   ├── compression.py    # Video compression utilities
│   │   ├── performance.py    # Performance optimization
│   │   └── video_validation.py # Video format validation
│   ├── agents/               # 5 AI agents (Agent 1-5)
│   ├── phases/               # 8 processing phases
│   ├── orchestrator/         # Pipeline coordination
│   ├── tests/                # Comprehensive test suite (204 tests)
│   └── main.py               # FastAPI application entry

├── frontend/
│   ├── src/
│   │   ├── app/              # Page routes (upload, progress, results)
│   │   ├── components/       # Reusable components (VideoPlayer, etc.)
│   │   ├── hooks/            # Custom React hooks (polling, API)
│   │   └── lib/              # Utilities & API client
│   ├── package.json
│   └── tsconfig.json

├── docs/                     # Planning & documentation
├── samples/                  # Demo videos
├── storage/                  # Session storage (auto-created)
├── ALL_PHASES_COMPLETE.md    # Project completion summary
└── CLAUDE.md                 # This file
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+
- FFmpeg (for video processing)
- Google Gemini API key

### Backend Setup

```bash
# Clone repository
git clone <repo>
cd Golf-Trainer-2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Set environment variables
export GEMINI_API_KEY="your-api-key"
export STORAGE_BACKEND="local"
export STORAGE_LOCAL_PATH="./storage"

# Run backend
uvicorn backend.main:app --reload
```

Backend will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set environment variables
export NEXT_PUBLIC_API_URL="http://localhost:8000"

# Run development server
npm run dev
```

Frontend will be available at `http://localhost:3000`

---

## 📊 System Architecture

### Processing Pipeline

```
Upload Video(s) (1 or 2: face-on, down-the-line, or both)
    ↓
Agent 1: Video Intelligence (camera angle detection, quality analysis)
    ↓
Phase 1: Hit Detection (swing segmentation using optical flow)
    ↓
Agent 2: Body Calibration (skeleton calibration)
    ↓
Phase 2: Keypoints Extraction (MediaPipe 3D pose)
    ↓
Phase 3: Setup Analysis (address frame analysis)
    ↓
Agent 3: Shot Classification (shot type & club detection)
    ↓
Phase 4: Biomechanical Metrics (13 core metrics calculated)
    ↓
Agent 4: Threshold Adaptation (adaptive thresholds per golfer)
    ↓
Phase 5: Performance Scoring (metric scoring & banding)
    ↓
Agent 5: Coaching (personalized coaching feedback)
    ↓
Phase 7: Slow-Motion Rendering (0.25× speed, 4× frame duplication)
    ├─ Generates: slowmo_face_on.mp4, slowmo_down_the_line.mp4
    ↓
Phase 8: Overlay Annotation (applies metrics to slowmo videos)
    └─ Reads slowmo → applies overlays → creates final videos
    ↓
Output: 2 Final Combined Videos:
  • face_on_final.mp4 (slow-motion + metrics overlay)
  • down_the_line_final.mp4 (slow-motion + metrics overlay)
  + Coaching feedback + metrics + performance scores
```

### 13 Core Biomechanical Metrics

1. **Tempo Ratio** — Backswing/downswing timing
2. **X-Factor** — Hip/shoulder separation (power)
3. **Spine Deviation** — Spine angle shift during swing
4. **Hip Sway** — Lateral hip movement
5. **Head Sway** — Lateral head movement
6. **Hip Turn** — Hip rotation angle
7. **Shoulder Turn** — Shoulder rotation angle
8. **Side Bend** — Lateral torso bend
9. **Hips Open** — Hip rotation at impact
10. **Wrist Lag** — Wrist-to-clubhead lag
11. **Knee Flex Left** — Left knee bend consistency
12. **Knee Flex Right** — Right knee bend consistency
13. **Stance Width** — Distance between ankles

---

## 🔌 API Endpoints

### Session Management
- `POST /api/session` — Single video upload
- `POST /api/session/dual` — Dual video upload
- `POST /api/session/single-with-angle` — Single video with angle specification
- `GET /api/session/{id}/status` — Session status
- `GET /api/session/{id}/status/progress` — Processing progress

### Video Streaming
**Final Combined Videos (Slowmo + Annotated):**
- `GET /api/output/{id}/annotated/face-on` — Face-on combined video (slowmo + metrics)
- `GET /api/output/{id}/annotated/down-the-line` — Down-the-line combined video (slowmo + metrics)

**Intermediate Videos (available during processing):**
- `GET /api/output/{id}/slowmo/face-on` — Face-on slowmo video only (4× frame duplication)
- `GET /api/output/{id}/slowmo/down-the-line` — Down-the-line slowmo video only

### Metadata
- `GET /api/output/{id}/metadata` — Video metadata (duration, resolution, fps)
- `GET /api/output/{id}/download/{kind}` — Download video file

---

## 🧪 Testing

### Run All Tests
```bash
cd backend
python -m pytest -v
```

### Current Test Status
- **Total Tests**: 204
- **Passing**: 204 (100%) ✅
- **Failing**: 0
- **Coverage**: All critical paths tested, including edge cases
- **Recent Fix**: Improved Phase 4 hip sway calculation for robustness with missing data scenarios

### Test Categories
- Unit tests for individual components
- Integration tests for phase pipelines
- API endpoint tests
- Agent validation tests
- Video processor tests
- Biomechanical metrics tests

---

## 🔑 Key Features

### Dual Camera Support
- Simultaneous analysis of face-on and down-the-line angles
- Angle-specific metrics and overlays
- Parallel processing for performance

### AI-Powered Analysis
- 5 specialized agents for different analysis stages
- No hardcoded thresholds — thresholds adapt per golfer
- Causal chain reasoning in coaching feedback

### Video Features
**Final Output Videos:**
- Combined slowmo + annotated in single file (no separate rendering)
- 0.25× slow-motion playback (4× frame duplication for smooth slow-mo)
- Real-time metrics overlays synchronized to keyframes
- Angle-specific overlay rendering (face-on vs down-the-line)

**Technical:**
- HTTP range request support for in-browser streaming & seeking
- 90fps output support (frame interpolation available)
- Adaptive quality based on input resolution
- Parallel dual-angle processing for performance

### Coaching System
- Skill-level inference (beginner/intermediate/advanced/scratch)
- Priority-ordered coaching items (1-4 per session)
- Causal chain explanations (why metrics matter)
- Specific drill suggestions
- Personalized guidance based on golfer's skill

---

## 📝 Known Issues & Future Work

### Edge Case Improvements (Phase 4 & 5)
- ✅ Phase 4 metrics with missing data — handled via null_reason tracking
- ✅ Phase 5 band classification boundaries — correctly implemented
- Improved `_compute_hip_sway` to use frame-based grouping instead of nested loops for better performance and reliability

### Planned Enhancements
- GPU acceleration for overlay rendering
- Real-time processing support
- Multi-angle support (3+ cameras)
- Batch processing API
- Webhook notifications
- User authentication & rate limiting
- Analytics dashboard

---

## 🛠️ Development Workflow

### Adding a New Feature

1. **Create a branch** (or work directly for quick fixes):
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Write tests first** (TDD approach):
   ```python
   # In backend/tests/test_my_feature.py
   def test_new_feature():
       assert expected == actual
   ```

3. **Implement feature** with type hints and logging

4. **Run tests**:
   ```bash
   python -m pytest backend/tests/test_my_feature.py -v
   ```

5. **Commit changes**:
   ```bash
   git add -A
   git commit -m "Add new feature description"
   ```

### Code Standards
- **Type Hints**: Required on all functions
- **Logging**: Use structured logging via `get_logger()`
- **Error Handling**: Comprehensive exception handling with logging
- **Tests**: Minimum 80% coverage for new code
- **Comments**: Only for "why" (not "what" — code should be self-documenting)

---

## 📊 Performance

### Typical Processing Times
- **Hit Detection (Phase 1)**: ~200ms
- **Keypoint Extraction (Phase 2)**: ~800ms
- **Metrics Calculation (Phase 4)**: ~150ms
- **Overlay Rendering (Phase 8)**: ~450ms (parallel for dual video)
- **Total Pipeline**: ~3-5 seconds

### Video Streaming
- **Range Request Response**: <100ms
- **Frame Delivery**: 30fps+ smooth playback
- **Bandwidth**: Adaptive based on quality settings

---

## 🔒 Environment Variables

```bash
# AI/ML
GEMINI_API_KEY=<your-key>           # Google Gemini API key
GEMINI_MODEL=gemini-2.5-flash       # Model version

# Storage
STORAGE_BACKEND=local               # local or cloud provider
STORAGE_LOCAL_PATH=./storage        # Local storage directory

# Application
FRONTEND_URL=http://localhost:3000  # Frontend URL (CORS)
MAX_UPLOAD_MB=500                   # Max video file size
MAX_VIDEO_SECONDS=120               # Max video duration
```

---

## 📞 Support & Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

**Video not streaming in browser**
- Check HTTP range request support in `backend/api/routers/output.py`
- Verify CORS headers are set in FastAPI middleware

**Metrics not calculating**
- Check if MediaPipe keypoints were detected in Phase 2
- Verify parquet file exists in session storage

**API 422 errors**
- Check request body matches DTO schema in `backend/api/dto.py`
- Validate gender field is "male" or "female"

---

## 📚 Further Reading

- **Architecture**: See `docs/further-plans.md` for detailed implementation notes
- **API Contract**: See inline docstrings in `backend/api/routers/*.py`
- **Agent Prompts**: See `backend/agents/*.py` for LLM instructions
- **Phase Logic**: See `backend/phase*/*.py` for algorithm details

---

## ✅ Checklist for New Contributors

- [ ] Read this CLAUDE.md
- [ ] Set up virtual environment
- [ ] Run tests locally (`pytest`)
- [ ] Review existing phase implementations
- [ ] Check agent prompts for context
- [ ] Use type hints on all new code
- [ ] Add tests for new features
- [ ] Update this file if adding major features

---

**Last Updated**: May 19, 2026  
**Project Status**: ✅ Core Complete, 100% Tests Passing  
**Next Phase**: Performance optimization & advanced analytics

