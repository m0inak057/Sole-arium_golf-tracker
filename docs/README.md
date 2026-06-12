# 📚 Golf Trainer AI — Engineering Documentation

<div align="center">

**Complete technical specification for Golf Trainer AI**  
Read the documents in order. Every document is authoritative.

[← Back to Main README](../README.md)

</div>

---

## 🎯 What This Product Is

Golf Trainer AI is a sophisticated web-based B2B/B2C platform delivering professional-grade golf swing analysis. 

**User Journey:** 
1. Golfer uploads a swing video
2. Selects gender (male/female)
3. Hits submit
4. Waits ~3-5 seconds

**System Delivers:**
- 📹 Two MP4 videos (plain slowmo + annotated with skeleton/overlays/HUD)
- 📊 Detailed metrics JSON with 13 biomechanical measurements
- 🎯 Personalized coaching text ordered by impact priority
- ⭐ Zero additional user inputs. Zero hardcoded thresholds. Zero dropdowns.

**Quality Target:** Professional coaching standard with causal-chain reasoning.

---

## 📖 How to Use This Documentation

### 👶 I'm New to This Project
**Start here:** [`architecture.md`](./architecture.md)  
Then read [`prd.md`](./prd.md) for the full requirements.

### 🚀 I'm Building a Feature
**Read in order:**
1. [`data-schema.md`](./data-schema.md) — Understand the session JSON contract
2. [`api-contract.md`](./api-contract.md) — Know the HTTP interface
3. [`agent-prompts.md`](./agent-prompts.md) — If you're building an agent
4. [`rules.md`](./rules.md) — Non-negotiable constraints

### 🧪 I'm Writing Tests
**Jump to:** [`testing.md`](./testing.md) for test fixtures and cases.

### 📐 I'm Reviewing Code
**Check:** [`rules.md`](./rules.md) and [`implementation-plan.md`](./implementation-plan.md)

---

## 📑 Complete Documentation Index

| # | Document | Answers | Time |
|---|----------|---------|------|
| **1** | [`prd.md`](./prd.md) | **What** are we building? **Why?** Who are users? What problems do we solve? | 15 min |
| **2** | [`architecture.md`](./architecture.md) | **How** is the system structured? Data flows? What lives where? Phase lifecycle? | 20 min |
| **3** | [`project-structure.md`](./project-structure.md) | **Where** are files? Folder layout? Import patterns? | 5 min |
| **4** | [`data-schema.md`](./data-schema.md) | **What** is the session JSON contract? What do phases read/write? | 15 min |
| **5** | [`api-contract.md`](./api-contract.md) | **How** do clients talk to the backend? Every endpoint? Every schema? | 10 min |
| **6** | [`agent-prompts.md`](./agent-prompts.md) | **What** do the 5 AI agents do? What are their prompts & tools? | 20 min |
| **7** | [`rules.md`](./rules.md) | **What** is non-negotiable? Coding standards? Quality bar? | 10 min |
| **8** | [`implementation-plan.md`](./implementation-plan.md) | **How** do we break this into work? Sprints? Acceptance criteria? | 15 min |
| **9** | [`testing.md`](./testing.md) | **How** do we test? Test fixtures? Exact test cases from PRD? | 15 min |

**Total time to read all:** ~2.5 hours for complete mastery.

---

## 🏆 Non-Negotiable Golden Rules

These rules apply **everywhere, always.** Violations require explicit exception & justification.

### 1. **User Input is Minimal** 
Only two inputs exist: video upload + gender selection. No dropdowns, toggles, or form fields without explicit approval. The system makes all decisions intelligently.

### 2. **No Hardcoded Thresholds**
Every threshold in analysis code comes from `active_thresholds` produced by **Agent 4**. Never hardcode values like "if angle > 45°". Adapt per golfer.

### 3. **No Hardcoded Body Measurements**
Every pixel-to-real-world conversion uses `px_to_inches_scale` from **Agent 2**. Never assume a body part is X pixels = Y inches.

### 4. **No Hardcoded Shot Type**
Shot type (driver, iron, wedge, etc.) comes from **Agent 3**, never guessed or assumed.

### 5. **Low-Confidence Keypoints are Excluded**
MediaPipe keypoints with visibility < 0.5 are never used. The affected metric is marked `null` in session JSON with a reason. Never guess or interpolate.

### 6. **Session JSON is Single Source of Truth**
Phases communicate **only** through the session JSON file. Phases never call each other directly. JSON is the contract.

### 7. **Agents Use Claude (Anthropic)**
All 5 AI agents use Claude (currently `claude-opus-4-8` or later). They return **structured JSON only** — no prose wrapping. Tool-use when needed, but always respond with JSON.

### 8. **Schema Version Bump Carefully**
`schema_version` is always `"1.3"` on every new session. Increment only on breaking changes that would break old session files.

### 9. **The MP4 is the Product**
The output annotated MP4 is the deliverable. Everything else (metrics panel, coaching text) is supporting material. Optimize the video first.

---

## ✅ What "Done" Looks Like

**Acceptance Test:**
A new user visits the web app, uploads a 15-second golf swing video, clicks a male/female radio button, hits submit, waits a few minutes, and receives:

- ✅ An annotated slow-motion MP4 with skeleton, angle overlays, and HUD panel
- ✅ A plain slow-motion MP4 (backup/comparison)
- ✅ A metrics panel showing all 13 measurements with per-metric targets
- ✅ Personalized coaching text, ordered by severity with one clear priority focus

**The system must have handled:**
- Camera-angle detection (face-on, down-the-line, or both)
- FPS detection and normalization
- Skeleton calibration per golfer
- Shot type classification
- Threshold selection (adaptive, not hardcoded)
- Fault combination reasoning (why metrics matter together)
- Skill-level inference (beginner → scratch)

**With zero additional questions asked to the user.**

---

## 🔗 Key Concepts Across Documents

### The 8-Phase Pipeline
1. **Phase 1:** Hit Detection (when does the swing start/end?)
2. **Phase 2:** Keypoints Extraction (where are the joints?)
3. **Phase 3:** Setup Analysis (what's the address position?)
4. **Phase 4:** Biomechanical Metrics (13 measurements)
5. **Phase 5:** Performance Scoring (how good are the metrics?)
6. **Phase 7:** Slow-Motion Rendering (0.25× speed)
7. **Phase 8:** Overlay Annotation (metrics on slowmo)

### The 5 AI Agents
1. **Agent 1:** Video Intelligence (camera angle, quality)
2. **Agent 2:** Body Calibration (skeleton, scale)
3. **Agent 3:** Shot Classification (shot type, club)
4. **Agent 4:** Threshold Adaptation (per-golfer thresholds)
5. **Agent 5:** Coaching (feedback & drills)

### The 13 Core Metrics
Tempo Ratio, X-Factor, Spine Deviation, Hip Sway, Head Sway, Hip Turn, Shoulder Turn, Side Bend, Hips Open, Wrist Lag, Knee Flex Left, Knee Flex Right, Stance Width.

See [`architecture.md`](./architecture.md) and [`data-schema.md`](./data-schema.md) for details.

---

## 🎬 Reading Order Recommendations

### 📖 For Product Managers
1. [`prd.md`](./prd.md) — Requirements
2. [`api-contract.md`](./api-contract.md) — What users see
3. [`rules.md`](./rules.md) — Non-negotiables

### 👨‍💻 For Backend Engineers
1. [`architecture.md`](./architecture.md) — System design
2. [`data-schema.md`](./data-schema.md) — JSON contract
3. [`implementation-plan.md`](./implementation-plan.md) — Tasks
4. [`agent-prompts.md`](./agent-prompts.md) — If building agents

### 🎨 For Frontend Engineers
1. [`api-contract.md`](./api-contract.md) — HTTP endpoints
2. [`prd.md`](./prd.md) — UI requirements
3. [`architecture.md`](./architecture.md) — Data flows

### 🧪 For Test Engineers
1. [`testing.md`](./testing.md) — Test strategy
2. [`data-schema.md`](./data-schema.md) — Fixtures
3. [`prd.md`](./prd.md) — Test cases

---

## 🚨 Quick Reference: Common Questions

**Q: Can I add a dropdown for shot type?**  
A: No. Shot type comes from Agent 3. Read rule #4.

**Q: Can I hardcode a threshold if it's smart?**  
A: No. Read rule #2. All thresholds come from Agent 4.

**Q: What if a keypoint has low visibility?**  
A: Mark the metric as `null` with reason in JSON. Read rule #5.

**Q: Can phases call each other?**  
A: No. Only communicate through session JSON. Read rule #6.

**Q: Do agents output prose?**  
A: No. JSON only. Read rule #7.

**Q: When do I bump schema_version?**  
A: Only on breaking changes. Read rule #8.

**Q: What should I optimize for?**  
A: The MP4 video quality. Everything else is secondary. Read rule #9.

---

## 📊 Current Project Status

| Component | Status | Latest Info |
|-----------|--------|-------------|
| **Core Pipeline** | ✅ Complete | All 8 phases + 5 agents |
| **Testing** | ✅ 100% | 204/204 tests passing |
| **Claude Integration** | ✅ Complete | Migrated from Gemini |
| **Video Streaming** | ✅ Complete | Range requests, dual-camera |
| **Coaching System** | ✅ Complete | Skill-adaptive feedback |
| **Frontend UI** | ✅ Complete | Error fallbacks included |

---

## 🔗 Links

- **Main README:** [../README.md](../README.md)
- **Project Root:** [../](../)
- **GitHub Issues:** (when available)
- **Live Demo:** (when available)

---

<div align="center">

**Last Updated:** June 12, 2026  
**Status:** Production Ready — 100% Test Coverage  
**Maintainer:** Golf Trainer Team

Read [`prd.md`](./prd.md) to begin. →

</div>
