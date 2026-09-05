"""Configuration settings for the automated commercial video generator."""

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR: Final[Path] = Path(__file__).resolve().parent
ASSETS_DIR: Final[Path] = BASE_DIR / "assets"
TEMP_DIR: Final[Path] = BASE_DIR / "temp"
OUTPUT_DIR: Final[Path] = BASE_DIR / "output"
BGM_DIR: Final[Path] = ASSETS_DIR / "bgm"

# Pexels API configuration
PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")
PEXELS_VIDEO_SEARCH_URL: str = os.getenv(
    "PEXELS_BASE_URL", "https://api.pexels.com/videos/search"
)

# LLM API configuration (Optional: for dynamic AI prompt expansion)
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Video specifications
VIDEO_WIDTH: Final[int] = 1080
VIDEO_HEIGHT: Final[int] = 1920
VIDEO_FPS: Final[int] = 30
MAX_VIDEO_DURATION: Final[float] = 20.0

# Edge-TTS Indonesian Neural Voices
# 'id-ID-GadisNeural' (Female, friendly, clear commercial delivery)
# 'id-ID-ArdiNeural' (Male, dynamic, persuasive)
DEFAULT_TTS_VOICE: Final[str] = "id-ID-GadisNeural"
TTS_RATE: Final[str] = "+15%"  # Slightly faster for upbeat commercial pace
TTS_PITCH: Final[str] = "+0Hz"

# Audio mixing levels
VOICEOVER_VOLUME: Final[float] = 1.0
BGM_VOLUME: Final[float] = 0.18
