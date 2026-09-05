"""Quality analysis and validation tool for generated commercial videos."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from config import MAX_VIDEO_DURATION, VIDEO_HEIGHT, VIDEO_WIDTH

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """Inspects video metadata via ffprobe and validates adherence to commercial goals."""

    def analyze(self, video_path: Path) -> Dict[str, Any]:
        """Runs ffprobe analysis and checks technical and qualitative compliance."""
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        format_info = data.get("format", {})
        streams = data.get("streams", [])

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        duration = float(format_info.get("duration", 0.0))
        size_bytes = int(format_info.get("size", 0))
        bitrate = int(format_info.get("bit_rate", 0))

        v_width = int(video_stream.get("width", 0)) if video_stream else 0
        v_height = int(video_stream.get("height", 0)) if video_stream else 0
        v_codec = video_stream.get("codec_name", "") if video_stream else ""
        v_fps = eval(video_stream.get("r_frame_rate", "0/1")) if video_stream else 0.0

        a_codec = audio_stream.get("codec_name", "") if audio_stream else ""
        a_channels = int(audio_stream.get("channels", 0)) if audio_stream else 0
        a_sample_rate = int(audio_stream.get("sample_rate", 0)) if audio_stream else 0

        # Goal Validations
        passed_duration = 0.0 < duration <= MAX_VIDEO_DURATION
        passed_resolution = (v_width == VIDEO_WIDTH) and (v_height == VIDEO_HEIGHT)
        passed_audio = audio_stream is not None and a_channels >= 1
        passed_video = video_stream is not None and v_codec in ["h264", "hevc", "av1"]

        is_success = all([
            passed_duration,
            passed_resolution,
            passed_audio,
            passed_video,
        ])

        report: Dict[str, Any] = {
            "file_name": video_path.name,
            "file_size_mb": round(size_bytes / (1024 * 1024), 2),
            "duration_seconds": round(duration, 2),
            "max_duration_allowed": MAX_VIDEO_DURATION,
            "resolution": f"{v_width}x{v_height}",
            "aspect_ratio": "9:16 (Vertical Portrait)",
            "video_codec": v_codec,
            "frame_rate_fps": round(v_fps, 2),
            "audio_codec": a_codec,
            "audio_channels": a_channels,
            "audio_sample_rate_hz": a_sample_rate,
            "overall_success": is_success,
            "checks": {
                "duration_within_20s": passed_duration,
                "resolution_portrait_1080x1920": passed_resolution,
                "audio_stream_active": passed_audio,
                "video_stream_active": passed_video,
            },
        }

        logger.info(f"Video Quality Analysis Report for '{video_path.name}':")
        logger.info(f" -> Duration: {report['duration_seconds']}s (Goal: <= {MAX_VIDEO_DURATION}s) [{'PASS' if passed_duration else 'FAIL'}]")
        logger.info(f" -> Resolution: {report['resolution']} [{'PASS' if passed_resolution else 'FAIL'}]")
        logger.info(f" -> Size: {report['file_size_mb']} MB")
        logger.info(f" -> Video Codec: {v_codec}, Audio Codec: {a_codec}")
        logger.info(f" -> Overall Goal Status: {'SUCCESS' if is_success else 'FAILED'}")

        return report
