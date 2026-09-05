"""Audio service handling Indonesian neural TTS generation and BGM composition."""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple
import edge_tts

from config import (
    ASSETS_DIR,
    BGM_DIR,
    BGM_VOLUME,
    DEFAULT_TTS_VOICE,
    TEMP_DIR,
    TTS_PITCH,
    TTS_RATE,
    VOICEOVER_VOLUME,
)

logger = logging.getLogger(__name__)


class AudioService:
    """Service to generate speech audio with Edge-TTS and manage background music."""

    def __init__(self, voice: str = DEFAULT_TTS_VOICE) -> None:
        self.voice = voice

    async def generate_speech_file(self, text: str, output_path: Path) -> Path:
        """Generates an MP3 speech file from text using Edge-TTS."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Generating TTS for voice '{self.voice}': '{text[:40]}...' -> {output_path.name}")

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=TTS_RATE,
            pitch=TTS_PITCH,
        )
        await communicate.save(str(output_path))
        return output_path

    def generate_scene_audios(
        self, scenes_narration: List[Tuple[int, str]]
    ) -> List[Dict[str, Any]]:
        """Generates separate audio files for each scene and measures their exact durations."""
        async def _run_all() -> List[Dict[str, Any]]:
            results = []
            for scene_id, narration in scenes_narration:
                scene_audio_path = TEMP_DIR / f"scene_{scene_id}_voice.mp3"
                await self.generate_speech_file(narration, scene_audio_path)
                duration = self.get_audio_duration(scene_audio_path)
                logger.info(f"Scene {scene_id} audio generated. Duration: {duration:.2f}s")
                results.append({
                    "scene_id": scene_id,
                    "audio_path": scene_audio_path,
                    "duration": duration,
                })
            return results

        return asyncio.run(_run_all())

    @staticmethod
    def get_audio_duration(file_path: Path) -> float:
        """Measures exact audio duration in seconds using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
            return float(output)
        except (subprocess.SubprocessError, ValueError) as e:
            logger.error(f"Failed to get audio duration for {file_path}: {e}")
            return 4.5

    def ensure_background_music(self, target_duration: float) -> Path:
        """Ensures a pleasant, upbeat commercial background music track is available.

        If a custom track is in assets/bgm/, it uses it.
        Otherwise, it synthesizes a smooth, modern lo-fi chord progression using FFmpeg.
        """
        BGM_DIR.mkdir(parents=True, exist_ok=True)
        bgm_files = list(BGM_DIR.glob("*.mp3")) + list(BGM_DIR.glob("*.wav"))
        if bgm_files:
            return bgm_files[0]

        # Generate a clean, upbeat ambient/commercial groove with FFmpeg audio filters
        synth_bgm_path = TEMP_DIR / "commercial_ambient_bgm.mp3"
        logger.info(f"Synthesizing upbeat commercial background music ({target_duration:.1f}s)...")

        # Create an upbeat, warm chord layer with soft rhythmic pulse
        filter_str = (
            f"anoisesrc=d={target_duration + 2}:c=pink:r=44100:a=0.012,lowpass=f=250[bass];"
            f"aevalsrc='0.05*sin(2*PI*261.63*t)*exp(-2*mod(t,0.5)) + "
            f"0.05*sin(2*PI*329.63*t)*exp(-2*mod(t,0.5)) + "
            f"0.05*sin(2*PI*392.00*t)*exp(-2*mod(t,0.5))':d={target_duration + 2}:s=44100[keys];"
            f"[bass][keys]amix=inputs=2:dropout_transition=0,volume=0.35,"
            f"afade=t=out:st={target_duration - 1.2}:d=1.2"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", filter_str,
            "-b:a", "192k",
            str(synth_bgm_path),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return synth_bgm_path
        except subprocess.SubprocessError as e:
            logger.warning(f"Synthesized BGM failed: {e}. Generating silent fallback.")
            # Fallback to minimal silent bed
            fallback_path = TEMP_DIR / "silent_bgm.mp3"
            cmd_silent = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={target_duration}",
                "-b:a", "128k", str(fallback_path)
            ]
            subprocess.run(cmd_silent, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return fallback_path
