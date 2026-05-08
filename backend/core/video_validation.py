"""Video validation and preprocessing utilities.

Provides utilities for:
- Video format validation
- Codec compatibility checking
- Video preprocessing
- Quality assessment
- Error recovery
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2

from backend.core.logging import get_logger

logger = get_logger(__name__)


class VideoValidator:
    """Validate video files for processing."""
    
    # Supported codecs
    SUPPORTED_CODECS = {
        "h264", "h265", "hevc", "avc1", "mp4v", "mjpeg", "mpeg4"
    }
    
    # Supported containers
    SUPPORTED_CONTAINERS = {".mp4", ".mov", ".avi", ".mkv"}
    
    # Quality thresholds
    MIN_RESOLUTION = (320, 240)  # Minimum 320x240
    MAX_RESOLUTION = (7680, 4320)  # Maximum 8K
    MIN_FPS = 15.0
    MAX_FPS = 120.0
    MIN_DURATION = 0.5  # Minimum 0.5 seconds
    MAX_DURATION = 3600.0  # Maximum 1 hour
    
    @staticmethod
    def validate_file(video_path: Path) -> tuple[bool, list[str]]:
        """Validate video file.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check file exists
        if not video_path.exists():
            errors.append(f"File does not exist: {video_path}")
            return False, errors
        
        # Check file extension
        if video_path.suffix.lower() not in VideoValidator.SUPPORTED_CONTAINERS:
            errors.append(f"Unsupported container: {video_path.suffix}")
        
        # Check file size
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        if file_size_mb < 1:
            errors.append("File is too small (< 1 MB)")
        elif file_size_mb > 5000:
            errors.append("File is too large (> 5 GB)")
        
        # Try to open and validate
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            errors.append("Cannot open video file")
            return False, errors
        
        try:
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Validate FPS
            if fps < VideoValidator.MIN_FPS:
                errors.append(f"FPS too low: {fps} (minimum {VideoValidator.MIN_FPS})")
            elif fps > VideoValidator.MAX_FPS:
                errors.append(f"FPS too high: {fps} (maximum {VideoValidator.MAX_FPS})")
            
            # Validate resolution
            if (width, height) < VideoValidator.MIN_RESOLUTION:
                errors.append(f"Resolution too low: {width}x{height}")
            elif (width, height) > VideoValidator.MAX_RESOLUTION:
                errors.append(f"Resolution too high: {width}x{height}")
            
            # Validate duration
            if frame_count > 0 and fps > 0:
                duration = frame_count / fps
                if duration < VideoValidator.MIN_DURATION:
                    errors.append(f"Duration too short: {duration:.1f}s")
                elif duration > VideoValidator.MAX_DURATION:
                    errors.append(f"Duration too long: {duration:.1f}s")
            
            # Try to read first frame
            ret, frame = cap.read()
            if not ret or frame is None:
                errors.append("Cannot read video frames")
        
        finally:
            cap.release()
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @staticmethod
    def get_video_info(video_path: Path) -> Optional[dict]:
        """Get detailed video information.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video information or None if error
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return None
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            duration = frame_count / fps if fps > 0 else 0
            file_size_mb = video_path.stat().st_size / (1024 * 1024)
            bitrate_mbps = (file_size_mb * 8) / duration if duration > 0 else 0
            
            return {
                "path": str(video_path),
                "fps": round(fps, 2),
                "frame_count": frame_count,
                "width": width,
                "height": height,
                "duration_seconds": round(duration, 2),
                "file_size_mb": round(file_size_mb, 2),
                "bitrate_mbps": round(bitrate_mbps, 2),
                "resolution": f"{width}x{height}",
            }
        finally:
            cap.release()


class VideoPreprocessor:
    """Preprocess videos for optimal processing."""
    
    @staticmethod
    def assess_quality(video_path: Path) -> float:
        """Assess video quality on a scale of 0.0 to 1.0.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Quality score from 0.0 to 1.0
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return 0.0
        
        try:
            score = 0.5  # Start with baseline
            
            # Check FPS (higher is better)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps >= 60:
                score += 0.2
            elif fps >= 30:
                score += 0.1
            
            # Check resolution (higher is better)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            pixels = width * height
            
            if pixels >= 2073600:  # 4K
                score += 0.2
            elif pixels >= 921600:  # 720p
                score += 0.1
            
            # Check frame count (longer is better for analysis)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if frame_count >= 300:  # At least 10 seconds at 30fps
                score += 0.1
            
            # Sample frames for sharpness
            sample_frames = [0, frame_count // 4, frame_count // 2, 3 * frame_count // 4]
            sharpness_scores = []
            
            for frame_idx in sample_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret and frame is not None:
                    sharpness = VideoPreprocessor._calculate_sharpness(frame)
                    sharpness_scores.append(sharpness)
            
            if sharpness_scores:
                avg_sharpness = sum(sharpness_scores) / len(sharpness_scores)
                if avg_sharpness > 100:
                    score += 0.2
                elif avg_sharpness > 50:
                    score += 0.1
            
            return min(1.0, score)
        
        finally:
            cap.release()
    
    @staticmethod
    def _calculate_sharpness(frame) -> float:
        """Calculate frame sharpness using Laplacian variance.
        
        Args:
            frame: OpenCV frame
            
        Returns:
            Sharpness score
        """
        try:
            import cv2
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            sharpness = laplacian.var()
            return float(sharpness)
        except Exception as e:
            logger.warning(f"Failed to calculate sharpness: {e}")
            return 0.0
    
    @staticmethod
    def check_codec_compatibility(video_path: Path) -> tuple[bool, Optional[str]]:
        """Check if video codec is compatible.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (is_compatible, codec_name)
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return False, None
        
        try:
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec_name = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
            
            is_compatible = codec_name.lower() in VideoValidator.SUPPORTED_CODECS
            return is_compatible, codec_name
        
        finally:
            cap.release()


class ErrorRecovery:
    """Error recovery utilities for video processing."""
    
    @staticmethod
    def attempt_frame_recovery(video_path: Path, frame_index: int, max_attempts: int = 5) -> bool:
        """Attempt to recover from frame read error.
        
        Args:
            video_path: Path to video file
            frame_index: Frame index that failed
            max_attempts: Maximum recovery attempts
            
        Returns:
            True if recovery successful
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return False
        
        try:
            # Try reading nearby frames
            for offset in range(-max_attempts, max_attempts + 1):
                if offset == 0:
                    continue
                
                target_frame = max(0, frame_index + offset)
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    logger.info(f"Frame recovery successful: frame {frame_index} -> {target_frame}")
                    return True
            
            return False
        
        finally:
            cap.release()
    
    @staticmethod
    def validate_output_video(video_path: Path) -> tuple[bool, list[str]]:
        """Validate output video file.
        
        Args:
            video_path: Path to output video file
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not video_path.exists():
            errors.append("Output file does not exist")
            return False, errors
        
        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        if file_size_mb < 0.1:
            errors.append("Output file is too small (< 0.1 MB)")
        
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            errors.append("Cannot open output video")
            return False, errors
        
        try:
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if frame_count == 0:
                errors.append("Output video has no frames")
            
            ret, frame = cap.read()
            if not ret or frame is None:
                errors.append("Cannot read frames from output video")
        
        finally:
            cap.release()
        
        return len(errors) == 0, errors
