"""Video composition engine using FFmpeg for assembling commercial videos."""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from config import (
    BGM_VOLUME,
    MAX_VIDEO_DURATION,
    OUTPUT_DIR,
    TEMP_DIR,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
    VOICEOVER_VOLUME,
)

logger = logging.getLogger(__name__)


class VideoComposer:
    """Composes scenes, applies vertical 9:16 formatting, and mixes voiceover and BGM."""

    def __init__(self) -> None:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def prepare_scene_clip(
        self,
        scene_id: int,
        raw_video_path: Path,
        target_duration: float,
    ) -> Path:
        """Trims, loops if needed, scales, and centers-crops raw footage to exact 1080x1920."""
        processed_path = TEMP_DIR / f"scene_{scene_id}_processed.mp4"
        logger.info(
            f"Processing Scene {scene_id} clip: target_duration={target_duration:.2f}s, "
            f"resolution={VIDEO_WIDTH}x{VIDEO_HEIGHT}"
        )

        # Video filter chain:
        # 1. Scale keeping aspect ratio until both dimensions match or exceed 1080x1920
        # 2. Crop centered to exact 1080x1920
        # 3. Force 30fps and square pixel aspect ratio (SAR 1)
        vf_filter = (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(in_w-{VIDEO_WIDTH})/2:(in_h-{VIDEO_HEIGHT})/2,"
            f"setsar=1,fps={VIDEO_FPS}"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop", "-1",  # Loop clip if it is shorter than target duration
            "-i", str(raw_video_path),
            "-t", f"{target_duration:.3f}",
            "-vf", vf_filter,
            "-an",  # Strip original raw stock audio
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "veryfast",
            "-crf", "22",
            str(processed_path),
        ]

        logger.debug(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg error processing scene {scene_id}: {result.stderr}")
            raise RuntimeError(f"FFmpeg failed on scene {scene_id}: {result.stderr}")

        return processed_path

    def assemble_commercial(
        self,
        scene_data: List[Dict[str, Any]],
        bgm_path: Path,
        output_filename: str = "commercial_lipstik_korea_50rb.mp4",
    ) -> Path:
        """Assembles all processed scenes, mixes speech audio and background music."""
        output_path = OUTPUT_DIR / output_filename
        logger.info(f"Assembling final commercial video -> {output_path}")

        # 1. Create concat list for video clips and audio clips
        video_concat_list_file = TEMP_DIR / "video_concat_list.txt"
        with open(video_concat_list_file, "w", encoding="utf-8") as f:
            for item in scene_data:
                f.write(f"file '{item['video_path'].resolve().as_posix()}'\n")

        audio_concat_list_file = TEMP_DIR / "audio_concat_list.txt"
        with open(audio_concat_list_file, "w", encoding="utf-8") as f:
            for item in scene_data:
                f.write(f"file '{item['audio_path'].resolve().as_posix()}'\n")

        # 2. Concat video stream
        concatenated_video = TEMP_DIR / "concatenated_video.mp4"
        cmd_concat_v = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(video_concat_list_file),
            "-c", "copy",
            str(concatenated_video),
        ]
        subprocess.run(cmd_concat_v, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 3. Concat speech audio stream seamlessly using filter_complex
        concatenated_speech = TEMP_DIR / "concatenated_speech.wav"
        audio_inputs: List[str] = []
        audio_filter_labels: List[str] = []
        for idx, item in enumerate(scene_data):
            audio_inputs.extend(["-i", str(item["audio_path"])])
            audio_filter_labels.append(f"[{idx}:a]")

        audio_concat_filter = f"{''.join(audio_filter_labels)}concat=n={len(scene_data)}:v=0:a=1[outa]"
        cmd_concat_a = [
            "ffmpeg", "-y",
            *audio_inputs,
            "-filter_complex", audio_concat_filter,
            "-map", "[outa]",
            str(concatenated_speech),
        ]
        subprocess.run(cmd_concat_a, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Calculate total speech duration
        total_duration = sum(item["duration"] for item in scene_data)
        final_duration = min(total_duration, MAX_VIDEO_DURATION)
        fade_out_start = max(0.0, final_duration - 1.2)

        logger.info(
            f"Merging video and audio. Duration: {final_duration:.2f}s "
            f"(Cap: {MAX_VIDEO_DURATION}s, Fade start: {fade_out_start:.2f}s)"
        )

        # 4. Final multiplexing with audio ducking and synchronized fade out
        filter_complex = (
            f"[1:a]volume={VOICEOVER_VOLUME},apad=whole_dur={final_duration:.3f}[voice];"
            f"[2:a]volume={BGM_VOLUME}[bgm];"
            f"[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2,afade=t=out:st={fade_out_start:.2f}:d=1.2[aout];"
            f"[0:v]fade=t=out:st={fade_out_start:.2f}:d=1.2[vout]"
        )

        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(concatenated_video),
            "-i", str(concatenated_speech),
            "-i", str(bgm_path),
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-t", f"{final_duration:.3f}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "21",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path),
        ]

        logger.debug(f"Executing final render: {' '.join(cmd_final)}")
        result = subprocess.run(cmd_final, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg error during final render: {result.stderr}")
            raise RuntimeError(f"Final render failed: {result.stderr}")

        logger.info(f"Commercial video successfully rendered: {output_path} ({output_path.stat().st_size} bytes)")
        return output_path
