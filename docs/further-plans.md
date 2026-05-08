# Golf Trainer 2 - Enhancement Plan

## Current System Analysis

The current Golf Trainer system processes a single video input through an 8-phase pipeline:
1. **Agent 1**: Video Intelligence (camera angle detection, quality analysis)
2. **Phase 1**: Hit Detection (swing segmentation)
3. **Agent 2**: Body Calibration
4. **Phase 2**: Keypoints extraction
5. **Phase 3**: Setup Analysis
6. **Agent 3**: Shot Classification
7. **Phase 4**: Biomechanical Metrics
8. **Agent 4**: Threshold Adaptation
9. **Phase 5**: Performance Scoring
10. **Agent 5**: Coaching
11. **Phase 7**: Slow-Motion Rendering (0.5x speed)
12. **Phase 8**: Annotated Video Overlay

**Current Output**: Single slowmo.mp4 and annotated.mp4 files

## Issues Identified

1. **Video Streaming**: Users can only download videos, not view them in browser
2. **Single Input Limitation**: System only accepts one video, but plan requires two (face-on + down-the-line)
3. **Single Output Format**: Only produces one angle output, but requirement is for dual-angle output
4. **Slow-Motion Speed**: Currently 0.5x (2x slower), needs to be 0.25x (4x slower)
5. **Frame Rate Compatibility**: System needs 90fps output support
6. **Video Processing Flow**: Need to restructure for dual input → dual output workflow

## Enhancement Plan

### Phase 1: Video Streaming Infrastructure (Priority: High)
**Goal**: Enable in-browser video playback

#### 1.1 Update Output Router
- **File**: `backend/api/routers/output.py`
- **Changes**:
  - Add HTTP range request support for video streaming
  - Implement proper MIME type headers
  - Add video metadata endpoints (duration, resolution, fps)
  - Support for both face-on and down-the-line video streaming

#### 1.2 Frontend Integration Points
- **New Endpoints**:
  - `GET /api/output/{session_id}/slowmo/face-on` - Stream face-on slowmo
  - `GET /api/output/{session_id}/slowmo/down-the-line` - Stream down-the-line slowmo
  - `GET /api/output/{session_id}/annotated/face-on` - Stream face-on annotated
  - `GET /api/output/{session_id}/annotated/down-the-line` - Stream down-the-line annotated
  - `GET /api/output/{session_id}/metadata` - Video metadata (duration, fps, resolution)

### Phase 2: Dual Video Input System (Priority: High)
**Goal**: Accept two video inputs (face-on + down-the-line)

#### 2.1 Upload Router Enhancement
- **File**: `backend/api/routers/upload.py`
- **Changes**:
  - Modify endpoint to accept two video files
  - Add camera angle validation for each video
  - Update session creation to handle dual inputs
  - Implement video angle detection and validation

#### 2.2 Storage System Updates
- **File**: `backend/core/storage.py`
- **Changes**:
  - Support storing multiple input videos per session
  - New file naming: `input_face_on.mp4`, `input_down_the_line.mp4`
  - Update video path resolution methods
  - Add methods for dual video handling

#### 2.3 Session Model Updates
- **File**: `backend/core/session.py`
- **Changes**:
  - Add fields for dual video metadata
  - Track processing status for each angle
  - Store angle-specific metrics and results

### Phase 3: Enhanced Slow-Motion Processing (Priority: Medium)
**Goal**: Improve slow-motion speed and add 90fps support

#### 3.1 Slowmo Enhancement
- **File**: `backend/phase7/slowmo.py`
- **Changes**:
  - Change duplication factor from 4x to 8x (0.25x speed instead of 0.5x)
  - Add 90fps output support with frame interpolation
  - Implement adaptive quality settings based on input resolution
  - Add support for processing both camera angles

#### 3.2 Video Processing Pipeline
- **File**: `backend/orchestrator/pipeline.py`
- **Changes**:
  - Modify Phase 7 to process both input videos
  - Add parallel processing for dual angles
  - Update timing and progress tracking

### Phase 4: Dual Output Generation (Priority: High)
**Goal**: Generate separate face-on and down-the-line output videos

#### 4.1 Pipeline Architecture Restructure
- **File**: `backend/orchestrator/pipeline.py`
- **Changes**:
  - Process both videos through the pipeline
  - Generate angle-specific keypoints and metrics
  - Produce four output files:
    - `slowmo_face_on.mp4`
    - `slowmo_down_the_line.mp4`
    - `annotated_face_on.mp4`
    - `annotated_down_the_line.mp4`

#### 4.2 Agent Updates for Dual Processing
- **Files**: All agent files in `backend/agents/`
- **Changes**:
  - Update agents to process data from both camera angles
  - Combine insights from both perspectives
  - Generate unified coaching recommendations

#### 4.3 Overlay Rendering Updates
- **File**: `backend/phase8/overlay.py`
- **Changes**:
  - Process both camera angles separately
  - Apply angle-appropriate overlays and annotations
  - Maintain consistent styling across both outputs

### Phase 5: API Contract Updates (Priority: Medium)
**Goal**: Update API to support dual video workflow

#### 5.1 New API Endpoints Structure
```
POST /api/session
- Accept two video files: face_on_video, down_the_line_video
- Return session_id and processing status

GET /api/session/{session_id}/status
- Return processing status for both angles
- Include progress indicators for each phase

GET /api/output/{session_id}/{angle}/{type}
- angle: "face-on" | "down-the-line"
- type: "slowmo" | "annotated"
- Support streaming with range requests

GET /api/output/{session_id}/{angle}/{type}/download
- Download specific video file
```

#### 5.2 Response Model Updates
- **File**: `backend/api/dto.py`
- **Changes**:
  - Add dual video response models
  - Update status response to include both angles
  - Add metadata models for video information

### Phase 6: Performance and Quality Improvements (Priority: Low)
**Goal**: Optimize processing and improve output quality

#### 6.1 Processing Optimization
- Implement parallel processing for both video angles
- Add GPU acceleration where possible
- Optimize memory usage for large video files
- Add progress tracking and ETA calculations

#### 6.2 Quality Enhancements
- Improve video compression settings
- Add adaptive bitrate based on input quality
- Implement better error handling and recovery
- Add video validation and preprocessing

## Implementation Timeline

### Week 1: Foundation
- [ ] Phase 1: Video Streaming Infrastructure
- [ ] Update output router with streaming support
- [ ] Test in-browser video playback

### Week 2: Input System
- [ ] Phase 2: Dual Video Input System
- [ ] Update upload router and storage
- [ ] Test dual video upload and validation

### Week 3: Processing Pipeline
- [ ] Phase 3: Enhanced Slow-Motion Processing
- [ ] Phase 4: Dual Output Generation (Part 1)
- [ ] Update pipeline for dual processing

### Week 4: Output and Polish
- [ ] Phase 4: Dual Output Generation (Part 2)
- [ ] Phase 5: API Contract Updates
- [ ] Integration testing and bug fixes

### Week 5: Optimization
- [ ] Phase 6: Performance and Quality Improvements
- [ ] Load testing and optimization
- [ ] Documentation updates

## Technical Considerations

### Video Processing Challenges
1. **Memory Usage**: Processing two high-resolution videos simultaneously
2. **Storage Space**: Dual outputs will double storage requirements
3. **Processing Time**: Parallel processing vs sequential processing trade-offs
4. **Synchronization**: Ensuring both videos are processed consistently

### API Design Considerations
1. **Backward Compatibility**: Maintain support for single video uploads during transition
2. **Error Handling**: Robust error handling for partial failures
3. **Progress Tracking**: Real-time progress updates for dual video processing
4. **Rate Limiting**: Prevent system overload with large video uploads

### Quality Assurance
1. **Video Quality**: Ensure output quality meets standards at 90fps
2. **Synchronization**: Verify timing alignment between face-on and down-the-line outputs
3. **Performance**: Monitor processing times and resource usage
4. **Compatibility**: Test across different video formats and resolutions

## Success Metrics

1. **Streaming**: Users can view videos in browser without downloading
2. **Dual Input**: System accepts and processes two video inputs correctly
3. **Dual Output**: System generates four output videos (2 slowmo + 2 annotated)
4. **Speed**: Slow-motion videos play at 0.25x speed (4x slower than current)
5. **Frame Rate**: System supports 90fps output
6. **Performance**: Processing time remains reasonable despite dual processing
7. **Quality**: Output video quality maintained or improved

## Risk Mitigation

1. **Incremental Rollout**: Implement features incrementally with fallbacks
2. **Testing**: Comprehensive testing at each phase
3. **Monitoring**: Add detailed logging and monitoring
4. **Rollback Plan**: Ability to revert to single video system if needed
5. **Resource Management**: Monitor and optimize resource usage

---

This plan provides a structured approach to implementing all requested enhancements while maintaining system stability and performance.