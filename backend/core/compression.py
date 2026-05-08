"""Video compression and bitrate optimization utilities.

Provides utilities for:
- Adaptive bitrate selection
- Compression preset optimization
- Quality-based encoding
- Bandwidth-efficient streaming
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from backend.core.logging import get_logger

logger = get_logger(__name__)


class CompressionPreset(Enum):
    """Video compression presets."""
    
    ULTRAFAST = "ultrafast"  # Fastest, lowest compression
    SUPERFAST = "superfast"
    VERYFAST = "veryfast"
    FASTER = "faster"
    FAST = "fast"
    MEDIUM = "medium"  # Default
    SLOW = "slow"
    SLOWER = "slower"
    VERYSLOW = "veryslow"  # Slowest, highest compression


class QualityLevel(Enum):
    """Video quality levels."""
    
    LOW = 28  # CRF value for low quality
    MEDIUM = 23  # CRF value for medium quality
    HIGH = 18  # CRF value for high quality
    VERY_HIGH = 12  # CRF value for very high quality


@dataclass
class BitrateProfile:
    """Bitrate profile for adaptive streaming."""
    
    name: str
    bitrate_kbps: int
    max_resolution: tuple[int, int]
    preset: CompressionPreset
    quality_level: QualityLevel
    
    def to_ffmpeg_args(self) -> list[str]:
        """Convert to FFmpeg arguments.
        
        Returns:
            List of FFmpeg command-line arguments.
        """
        args = [
            "-preset", self.preset.value,
            "-crf", str(self.quality_level.value),
            "-b:v", f"{self.bitrate_kbps}k",
            "-maxrate", f"{int(self.bitrate_kbps * 1.5)}k",
            "-bufsize", f"{int(self.bitrate_kbps * 2)}k",
        ]
        return args


class BitrateOptimizer:
    """Optimize bitrate based on input characteristics."""
    
    # Predefined bitrate profiles
    PROFILES = {
        "mobile_low": BitrateProfile(
            name="Mobile Low",
            bitrate_kbps=500,
            max_resolution=(640, 480),
            preset=CompressionPreset.FAST,
            quality_level=QualityLevel.LOW,
        ),
        "mobile_medium": BitrateProfile(
            name="Mobile Medium",
            bitrate_kbps=1500,
            max_resolution=(1280, 720),
            preset=CompressionPreset.MEDIUM,
            quality_level=QualityLevel.MEDIUM,
        ),
        "mobile_high": BitrateProfile(
            name="Mobile High",
            bitrate_kbps=3000,
            max_resolution=(1920, 1080),
            preset=CompressionPreset.SLOW,
            quality_level=QualityLevel.HIGH,
        ),
        "desktop_medium": BitrateProfile(
            name="Desktop Medium",
            bitrate_kbps=5000,
            max_resolution=(1920, 1080),
            preset=CompressionPreset.MEDIUM,
            quality_level=QualityLevel.HIGH,
        ),
        "desktop_high": BitrateProfile(
            name="Desktop High",
            bitrate_kbps=8000,
            max_resolution=(3840, 2160),
            preset=CompressionPreset.SLOW,
            quality_level=QualityLevel.VERY_HIGH,
        ),
        "archive": BitrateProfile(
            name="Archive",
            bitrate_kbps=15000,
            max_resolution=(7680, 4320),
            preset=CompressionPreset.VERYSLOW,
            quality_level=QualityLevel.VERY_HIGH,
        ),
    }
    
    @staticmethod
    def select_profile(
        input_quality_score: float,
        resolution_width: int,
        resolution_height: int,
        target_bitrate_kbps: Optional[int] = None,
    ) -> BitrateProfile:
        """Select optimal bitrate profile.
        
        Args:
            input_quality_score: Input quality score (0.0-1.0)
            resolution_width: Input resolution width
            resolution_height: Input resolution height
            target_bitrate_kbps: Target bitrate in kbps (optional)
            
        Returns:
            Selected BitrateProfile
        """
        if target_bitrate_kbps:
            return BitrateOptimizer._create_custom_profile(
                target_bitrate_kbps,
                resolution_width,
                resolution_height,
                input_quality_score,
            )
        
        # Select based on resolution and quality
        pixels = resolution_width * resolution_height
        
        if pixels <= 307200:  # 640x480
            if input_quality_score > 0.7:
                return BitrateOptimizer.PROFILES["mobile_high"]
            else:
                return BitrateOptimizer.PROFILES["mobile_low"]
        
        elif pixels <= 921600:  # 1280x720
            if input_quality_score > 0.8:
                return BitrateOptimizer.PROFILES["mobile_high"]
            else:
                return BitrateOptimizer.PROFILES["mobile_medium"]
        
        elif pixels <= 2073600:  # 1920x1080
            if input_quality_score > 0.8:
                return BitrateOptimizer.PROFILES["desktop_high"]
            else:
                return BitrateOptimizer.PROFILES["desktop_medium"]
        
        else:  # 4K and above
            return BitrateOptimizer.PROFILES["archive"]
    
    @staticmethod
    def _create_custom_profile(
        bitrate_kbps: int,
        resolution_width: int,
        resolution_height: int,
        quality_score: float,
    ) -> BitrateProfile:
        """Create custom bitrate profile.
        
        Args:
            bitrate_kbps: Target bitrate in kbps
            resolution_width: Resolution width
            resolution_height: Resolution height
            quality_score: Quality score (0.0-1.0)
            
        Returns:
            Custom BitrateProfile
        """
        # Select preset based on bitrate
        if bitrate_kbps < 1000:
            preset = CompressionPreset.FAST
        elif bitrate_kbps < 3000:
            preset = CompressionPreset.MEDIUM
        else:
            preset = CompressionPreset.SLOW
        
        # Select quality level based on score
        if quality_score > 0.8:
            quality_level = QualityLevel.HIGH
        elif quality_score > 0.6:
            quality_level = QualityLevel.MEDIUM
        else:
            quality_level = QualityLevel.LOW
        
        return BitrateProfile(
            name="Custom",
            bitrate_kbps=bitrate_kbps,
            max_resolution=(resolution_width, resolution_height),
            preset=preset,
            quality_level=quality_level,
        )
    
    @staticmethod
    def calculate_bitrate_for_quality(
        quality_level: QualityLevel,
        resolution_width: int,
        resolution_height: int,
        fps: float,
    ) -> int:
        """Calculate bitrate for desired quality level.
        
        Args:
            quality_level: Desired quality level
            resolution_width: Resolution width
            resolution_height: Resolution height
            fps: Frames per second
            
        Returns:
            Recommended bitrate in kbps
        """
        pixels = resolution_width * resolution_height
        
        # Base bitrate calculation: pixels * fps * quality_factor
        quality_factors = {
            QualityLevel.LOW: 0.05,
            QualityLevel.MEDIUM: 0.08,
            QualityLevel.HIGH: 0.12,
            QualityLevel.VERY_HIGH: 0.15,
        }
        
        quality_factor = quality_factors.get(quality_level, 0.08)
        bitrate_kbps = int((pixels * fps * quality_factor) / 1000)
        
        # Clamp to reasonable range
        bitrate_kbps = max(500, min(bitrate_kbps, 50000))
        
        return bitrate_kbps


class CompressionOptimizer:
    """Optimize compression settings for different scenarios."""
    
    @staticmethod
    def get_preset_for_speed(
        available_time_seconds: float,
        target_duration_seconds: float,
    ) -> CompressionPreset:
        """Get compression preset based on available processing time.
        
        Args:
            available_time_seconds: Available processing time
            target_duration_seconds: Target video duration
            
        Returns:
            Recommended CompressionPreset
        """
        # Calculate available time per second of video
        time_per_second = available_time_seconds / target_duration_seconds if target_duration_seconds > 0 else 0
        
        if time_per_second < 0.5:
            return CompressionPreset.ULTRAFAST
        elif time_per_second < 1.0:
            return CompressionPreset.SUPERFAST
        elif time_per_second < 2.0:
            return CompressionPreset.VERYFAST
        elif time_per_second < 5.0:
            return CompressionPreset.FAST
        elif time_per_second < 10.0:
            return CompressionPreset.MEDIUM
        elif time_per_second < 20.0:
            return CompressionPreset.SLOW
        else:
            return CompressionPreset.VERYSLOW
    
    @staticmethod
    def get_crf_for_quality(quality_score: float) -> int:
        """Get CRF value for quality score.
        
        Args:
            quality_score: Quality score (0.0-1.0)
            
        Returns:
            CRF value (0-51, lower is better)
        """
        # Map quality score to CRF
        # 0.0 -> CRF 51 (worst)
        # 1.0 -> CRF 0 (best)
        crf = int(51 * (1.0 - quality_score))
        return max(0, min(51, crf))
    
    @staticmethod
    def get_audio_bitrate_for_quality(quality_level: QualityLevel) -> str:
        """Get audio bitrate for quality level.
        
        Args:
            quality_level: Quality level
            
        Returns:
            Audio bitrate string (e.g., "128k")
        """
        audio_bitrates = {
            QualityLevel.LOW: "64k",
            QualityLevel.MEDIUM: "128k",
            QualityLevel.HIGH: "192k",
            QualityLevel.VERY_HIGH: "256k",
        }
        return audio_bitrates.get(quality_level, "128k")


class StreamingOptimizer:
    """Optimize video for streaming scenarios."""
    
    @staticmethod
    def get_streaming_args(
        bitrate_kbps: int,
        quality_level: QualityLevel,
        enable_hls: bool = False,
    ) -> list[str]:
        """Get FFmpeg arguments for streaming optimization.
        
        Args:
            bitrate_kbps: Target bitrate in kbps
            quality_level: Quality level
            enable_hls: Enable HLS optimization
            
        Returns:
            List of FFmpeg arguments
        """
        args = [
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", str(quality_level.value),
            "-b:v", f"{bitrate_kbps}k",
            "-maxrate", f"{int(bitrate_kbps * 1.5)}k",
            "-bufsize", f"{int(bitrate_kbps * 2)}k",
            "-c:a", "aac",
            "-b:a", "128k",
        ]
        
        if enable_hls:
            args.extend([
                "-hls_time", "10",
                "-hls_list_size", "0",
                "-f", "hls",
            ])
        
        return args
