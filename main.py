"""Main entry point for generating automated 20-second commercial videos."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from config import DEFAULT_TTS_VOICE, OUTPUT_DIR, PEXELS_API_KEY
from services.audio_service import AudioService
from services.pexels_service import PexelsService
from services.script_engine import ScriptEngine
from services.video_analyzer import VideoAnalyzer
from services.video_composer import VideoComposer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("CommercialVideoApp")


def run_pipeline(prompt: str, pexels_key: str, voice: str) -> Dict[str, Any]:
    """Runs the end-to-end commercial video generation pipeline."""
    logger.info("==========================================================")
    logger.info("  STARTING AUTOMATED COMMERCIAL VIDEO GENERATION PIPELINE  ")
    logger.info("==========================================================")
    logger.info(f"User Prompt: '{prompt}'")
    logger.info(f"TTS Voice: '{voice}'")

    # Step 1: Initialize Services
    script_engine = ScriptEngine()
    pexels_service = PexelsService(api_key=pexels_key)
    audio_service = AudioService(voice=voice)
    video_composer = VideoComposer()
    video_analyzer = VideoAnalyzer()

    # Step 2: Generate Commercial Script
    logger.info("\n--- STEP 1: SCRIPT GENERATION (INDONESIAN MARKET) ---")
    script = script_engine.generate_script(user_prompt=prompt)
    for scene in script.scenes:
        logger.info(f"Scene {scene.scene_id} [{scene.phase}]:")
        logger.info(f"  Narration: \"{scene.narration}\"")
        logger.info(f"  Pexels Query: \"{scene.pexels_query}\"")

    # Step 3: Generate Voiceover Audios per Scene
    logger.info("\n--- STEP 2: NEURAL TTS SYNTHESIS (EDGE-TTS) ---")
    scenes_narration = [(s.scene_id, s.narration) for s in script.scenes]
    scene_audios = audio_service.generate_scene_audios(scenes_narration)
    total_audio_duration = sum(item["duration"] for item in scene_audios)
    logger.info(f"Total Speech Duration: {total_audio_duration:.2f}s (Budget: <= 20.0s)")

    # Step 4: Fetch Pexels Footage and Prepare Clips
    logger.info("\n--- STEP 3: ASSET SOURCING & PROCESSING (PEXELS API) ---")
    scene_data: List[Dict[str, Any]] = []
    num_scenes = len(script.scenes)
    for idx, (scene, audio_info) in enumerate(zip(script.scenes, scene_audios)):
        logger.info(f"Fetching footage for Scene {scene.scene_id}...")
        # Add 0.8s buffer to final scene so the video CTA lingers naturally
        pad = 0.8 if idx == num_scenes - 1 else 0.0
        scene_clip_duration = audio_info["duration"] + pad

        raw_video_path = pexels_service.fetch_footage_for_scene(
            scene_id=scene.scene_id,
            query=scene.pexels_query,
        )
        processed_clip_path = video_composer.prepare_scene_clip(
            scene_id=scene.scene_id,
            raw_video_path=raw_video_path,
            target_duration=scene_clip_duration,
        )
        scene_data.append({
            "scene_id": scene.scene_id,
            "video_path": processed_clip_path,
            "audio_path": audio_info["audio_path"],
            "duration": scene_clip_duration,
        })

    # Step 5: Prepare Background Music
    logger.info("\n--- STEP 4: PREPARING BACKGROUND MUSIC ---")
    bgm_path = audio_service.ensure_background_music(target_duration=total_audio_duration)
    logger.info(f"Background music track ready: {bgm_path}")

    # Step 6: Assemble Final Commercial Video
    logger.info("\n--- STEP 5: FINAL VIDEO COMPOSITION (FFMPEG) ---")
    output_filename = "commercial_lipstik_korea_50rb.mp4"
    final_video_path = video_composer.assemble_commercial(
        scene_data=scene_data,
        bgm_path=bgm_path,
        output_filename=output_filename,
    )

    # Step 7: Analyze & Validate Video Against Goals
    logger.info("\n--- STEP 6: QUALITY INSPECTION & GOAL VERIFICATION ---")
    analysis_report = video_analyzer.analyze(final_video_path)
    analysis_report["video_path"] = str(final_video_path.resolve())

    return analysis_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated Commercial Video Generator")
    parser.add_argument(
        "--prompt",
        type=str,
        default="buat video iklan untuk lipstik korea saya harga 50rb buat agar viral",
        help="User prompt describing the commercial ad",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=PEXELS_API_KEY,
        help="Pexels API Key",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=DEFAULT_TTS_VOICE,
        help="Edge-TTS voice identifier",
    )

    args = parser.parse_args()
    if not args.api_key:
        logger.error(
            "PEXELS_API_KEY is missing! Please provide it via '--api-key YOUR_KEY' "
            "or set PEXELS_API_KEY in your '.env' file. You can get a free key from https://www.pexels.com/api/"
        )
        sys.exit(1)

    try:
        report = run_pipeline(prompt=args.prompt, pexels_key=args.api_key, voice=args.voice)
        logger.info("\n==========================================================")
        logger.info("  PIPELINE EXECUTION COMPLETED SUCCESSFULLY!              ")
        logger.info(f"  Output Video: {report['video_path']}")
        logger.info(f"  Duration: {report['duration_seconds']} seconds (Goal: <= 20s)")
        logger.info(f"  Resolution: {report['resolution']}")
        logger.info(f"  Overall Status: {'PASSED' if report['overall_success'] else 'FAILED'}")
        logger.info("==========================================================")
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
