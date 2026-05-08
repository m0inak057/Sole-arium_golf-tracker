"""Performance optimization utilities for video processing.

Provides utilities for:
- Memory-efficient video processing
- Progress tracking and ETA calculations
- Resource monitoring
- Adaptive quality settings
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from backend.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessingMetrics:
    """Metrics for processing performance tracking."""
    
    total_frames: int
    processed_frames: int = 0
    start_time: float = field(default_factory=time.time)
    last_update_time: float = field(default_factory=time.time)
    
    # Performance metrics
    frames_per_second: float = 0.0
    estimated_remaining_seconds: float = 0.0
    progress_percentage: float = 0.0
    
    # Resource metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    def update(self, frames_processed: int) -> None:
        """Update metrics with new frame count.
        
        Args:
            frames_processed: Number of frames processed since last update.
        """
        current_time = time.time()
        self.processed_frames += frames_processed
        
        # Calculate FPS
        elapsed_since_last = current_time - self.last_update_time
        if elapsed_since_last > 0:
            self.frames_per_second = frames_processed / elapsed_since_last
        
        # Calculate progress
        self.progress_percentage = (self.processed_frames / self.total_frames) * 100
        
        # Calculate ETA
        total_elapsed = current_time - self.start_time
        if self.processed_frames > 0 and self.frames_per_second > 0:
            remaining_frames = self.total_frames - self.processed_frames
            self.estimated_remaining_seconds = remaining_frames / self.frames_per_second
        
        self.last_update_time = current_time
    
    def get_summary(self) -> dict:
        """Get summary of current metrics.
        
        Returns:
            Dictionary with current metrics.
        """
        return {
            "total_frames": self.total_frames,
            "processed_frames": self.processed_frames,
            "progress_percentage": round(self.progress_percentage, 1),
            "frames_per_second": round(self.frames_per_second, 2),
            "estimated_remaining_seconds": round(self.estimated_remaining_seconds, 1),
            "memory_usage_mb": round(self.memory_usage_mb, 1),
            "cpu_usage_percent": round(self.cpu_usage_percent, 1),
        }


class AdaptiveQualitySettings:
    """Adaptive quality settings based on input characteristics."""
    
    def __init__(self):
        """Initialize quality settings."""
        self.preset = "medium"  # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
        self.crf = 23  # Quality (0-51, lower is better)
        self.bitrate = None  # None for CRF mode
        self.enable_interpolation = False
        self.frame_duplication_factor = 8
    
    @staticmethod
    def from_input_quality(
        video_quality_score: float,
        resolution_width: int,
        resolution_height: int,
        available_memory_mb: float,
    ) -> AdaptiveQualitySettings:
        """Create quality settings based on input characteristics.
        
        Args:
            video_quality_score: Quality score from 0.0 to 1.0
            resolution_width: Video width in pixels
            resolution_height: Video height in pixels
            available_memory_mb: Available memory in MB
            
        Returns:
            AdaptiveQualitySettings configured for the input.
        """
        settings = AdaptiveQualitySettings()
        
        # Adjust preset based on available memory
        if available_memory_mb < 2048:  # < 2GB
            settings.preset = "ultrafast"
        elif available_memory_mb < 4096:  # < 4GB
            settings.preset = "superfast"
        elif available_memory_mb < 8192:  # < 8GB
            settings.preset = "veryfast"
        else:
            settings.preset = "fast"
        
        # Adjust CRF based on input quality
        if video_quality_score > 0.8:
            settings.crf = 18  # High quality
            settings.enable_interpolation = True
        elif video_quality_score > 0.6:
            settings.crf = 23  # Medium quality
        else:
            settings.crf = 28  # Lower quality (more compression)
        
        # Adjust for resolution
        pixels = resolution_width * resolution_height
        if pixels > 2073600:  # 4K (3840x2160)
            # For 4K, use faster preset to save time
            if settings.preset not in ("ultrafast", "superfast"):
                settings.preset = "veryfast"
            settings.crf = min(settings.crf + 2, 28)
        elif pixels < 921600:  # < 720p
            settings.crf = max(settings.crf - 2, 18)
        
        return settings
    
    def to_ffmpeg_args(self) -> list[str]:
        """Convert settings to FFmpeg arguments.
        
        Returns:
            List of FFmpeg command-line arguments.
        """
        args = [
            "-preset", self.preset,
            "-c:v", "libx264",
        ]
        
        if self.bitrate:
            args.extend(["-b:v", self.bitrate])
        else:
            args.extend(["-crf", str(self.crf)])
        
        return args


class MemoryOptimizer:
    """Utilities for memory-efficient video processing."""
    
    # Chunk size for streaming processing (in frames)
    DEFAULT_CHUNK_SIZE = 30
    
    @staticmethod
    def calculate_optimal_chunk_size(
        frame_width: int,
        frame_height: int,
        available_memory_mb: float,
        bytes_per_pixel: int = 3,  # RGB
    ) -> int:
        """Calculate optimal chunk size for memory-efficient processing.
        
        Args:
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels
            available_memory_mb: Available memory in MB
            bytes_per_pixel: Bytes per pixel (3 for RGB, 4 for RGBA)
            
        Returns:
            Optimal chunk size in frames.
        """
        # Reserve 50% of available memory for processing
        usable_memory_bytes = (available_memory_mb * 0.5) * 1024 * 1024
        
        # Calculate bytes per frame
        bytes_per_frame = frame_width * frame_height * bytes_per_pixel
        
        # Calculate chunk size (with 2x buffer for processing)
        chunk_size = int(usable_memory_bytes / (bytes_per_frame * 2))
        
        # Ensure minimum and maximum bounds
        chunk_size = max(1, min(chunk_size, 100))
        
        return chunk_size
    
    @staticmethod
    def get_available_memory_mb() -> float:
        """Get available system memory in MB.
        
        Returns:
            Available memory in MB.
        """
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.available / (1024 * 1024)
        except ImportError:
            # Fallback if psutil not available
            logger.warning("psutil not available, using default memory estimate")
            return 4096.0  # Default to 4GB


class ResourceMonitor:
    """Monitor resource usage during processing."""
    
    def __init__(self):
        """Initialize resource monitor."""
        self.start_time = time.time()
        self.peak_memory_mb = 0.0
        self.peak_cpu_percent = 0.0
    
    def update(self) -> dict:
        """Update resource metrics.
        
        Returns:
            Dictionary with current resource usage.
        """
        try:
            import psutil
            
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            cpu_percent = process.cpu_percent(interval=0.1)
            
            self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
            self.peak_cpu_percent = max(self.peak_cpu_percent, cpu_percent)
            
            return {
                "current_memory_mb": round(memory_mb, 1),
                "peak_memory_mb": round(self.peak_memory_mb, 1),
                "current_cpu_percent": round(cpu_percent, 1),
                "peak_cpu_percent": round(self.peak_cpu_percent, 1),
            }
        except ImportError:
            logger.warning("psutil not available for resource monitoring")
            return {
                "current_memory_mb": 0.0,
                "peak_memory_mb": 0.0,
                "current_cpu_percent": 0.0,
                "peak_cpu_percent": 0.0,
            }
    
    def get_summary(self) -> dict:
        """Get summary of resource usage.
        
        Returns:
            Dictionary with resource usage summary.
        """
        elapsed_seconds = time.time() - self.start_time
        
        return {
            "elapsed_seconds": round(elapsed_seconds, 1),
            "peak_memory_mb": round(self.peak_memory_mb, 1),
            "peak_cpu_percent": round(self.peak_cpu_percent, 1),
        }


class ProgressTracker:
    """Track and report processing progress."""
    
    def __init__(self, total_items: int, name: str = "Processing"):
        """Initialize progress tracker.
        
        Args:
            total_items: Total number of items to process
            name: Name of the operation for logging
        """
        self.total_items = total_items
        self.name = name
        self.processed_items = 0
        self.start_time = time.time()
        self.last_report_time = self.start_time
        self.report_interval_seconds = 5.0  # Report every 5 seconds
    
    def update(self, items_processed: int = 1) -> Optional[dict]:
        """Update progress.
        
        Args:
            items_processed: Number of items processed since last update
            
        Returns:
            Progress report if report interval exceeded, None otherwise
        """
        self.processed_items += items_processed
        current_time = time.time()
        
        # Check if we should report
        if current_time - self.last_report_time >= self.report_interval_seconds:
            report = self._generate_report(current_time)
            self.last_report_time = current_time
            return report
        
        return None
    
    def finish(self) -> dict:
        """Mark processing as finished and return final report.
        
        Returns:
            Final progress report.
        """
        return self._generate_report(time.time())
    
    def _generate_report(self, current_time: float) -> dict:
        """Generate progress report.
        
        Args:
            current_time: Current time for calculations
            
        Returns:
            Progress report dictionary.
        """
        elapsed_seconds = current_time - self.start_time
        progress_percent = (self.processed_items / self.total_items) * 100
        
        # Calculate rate and ETA
        if elapsed_seconds > 0:
            items_per_second = self.processed_items / elapsed_seconds
            remaining_items = self.total_items - self.processed_items
            eta_seconds = remaining_items / items_per_second if items_per_second > 0 else 0
        else:
            items_per_second = 0
            eta_seconds = 0
        
        return {
            "name": self.name,
            "processed": self.processed_items,
            "total": self.total_items,
            "progress_percent": round(progress_percent, 1),
            "items_per_second": round(items_per_second, 2),
            "elapsed_seconds": round(elapsed_seconds, 1),
            "eta_seconds": round(eta_seconds, 1),
        }
