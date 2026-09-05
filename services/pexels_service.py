"""Pexels API integration service for fetching portrait stock videos."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from config import PEXELS_API_KEY, PEXELS_VIDEO_SEARCH_URL, TEMP_DIR

logger = logging.getLogger(__name__)


class PexelsService:
    """Service to search and download portrait stock videos from Pexels API."""

    def __init__(self, api_key: str = PEXELS_API_KEY) -> None:
        self.api_key = api_key
        self.headers = {"Authorization": self.api_key}

    def search_portrait_video(
        self, query: str, per_page: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Searches for portrait videos matching the given query."""
        params = {
            "query": query,
            "orientation": "portrait",
            "per_page": per_page,
            "size": "medium",
        }
        try:
            logger.info(f"Searching Pexels video for query: '{query}' (orientation: portrait)")
            response = requests.get(
                PEXELS_VIDEO_SEARCH_URL,
                headers=self.headers,
                params=params,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            videos: List[Dict[str, Any]] = data.get("videos", [])

            if not videos:
                logger.warning(f"No videos found on Pexels for '{query}'. Trying fallback.")
                return None

            # Find the best quality video file for the first video
            for video in videos:
                video_files = video.get("video_files", [])
                # Prioritize HD 1080x1920 or closest portrait file
                best_file = self._select_best_video_file(video_files)
                if best_file:
                    return {
                        "video_id": video.get("id"),
                        "duration": video.get("duration"),
                        "download_url": best_file.get("link"),
                        "width": best_file.get("width"),
                        "height": best_file.get("height"),
                        "quality": best_file.get("quality"),
                    }

            return None
        except requests.RequestException as e:
            logger.error(f"Error querying Pexels API for '{query}': {e}", exc_info=True)
            return None

    def _select_best_video_file(
        self, video_files: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Selects the best portrait video file (preferring 1080x1920 or HD portrait)."""
        portrait_files = [
            f for f in video_files
            if f.get("file_type") == "video/mp4" and f.get("height", 0) > f.get("width", 0)
        ]

        if not portrait_files:
            # If no strict portrait file is flagged, take any mp4 file
            mp4_files = [f for f in video_files if f.get("file_type") == "video/mp4"]
            if not mp4_files:
                return None
            return max(mp4_files, key=lambda f: f.get("height", 0))

        # Look for 1080x1920 or highest resolution up to 1080x1920
        # Avoid downloading 4K UHD unnecessarily to optimize rendering speed
        exact_hd = [f for f in portrait_files if f.get("width") == 1080 and f.get("height") == 1920]
        if exact_hd:
            return exact_hd[0]

        # Otherwise pick the highest resolution portrait file <= 1920 height
        hd_candidates = [f for f in portrait_files if f.get("height", 0) <= 1920]
        if hd_candidates:
            return max(hd_candidates, key=lambda f: f.get("height", 0))

        return portrait_files[0]

    def download_video(self, download_url: str, output_path: Path) -> Path:
        """Downloads a video stream from Pexels CDN to the specified output path."""
        logger.info(f"Downloading video from {download_url} to {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with requests.get(download_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
            logger.info(f"Successfully downloaded: {output_path} ({output_path.stat().st_size} bytes)")
            return output_path
        except requests.RequestException as e:
            logger.error(f"Failed to download video from {download_url}: {e}", exc_info=True)
            raise

    def fetch_footage_for_scene(
        self, scene_id: int, query: str, fallback_query: str = "korean beauty woman cosmetic"
    ) -> Path:
        """Searches and downloads footage for a specific scene."""
        result = self.search_portrait_video(query)
        if not result and fallback_query:
            logger.info(f"Retrying with fallback query: '{fallback_query}'")
            result = self.search_portrait_video(fallback_query)

        if not result:
            raise RuntimeError(f"Could not find any suitable video on Pexels for scene {scene_id} ({query})")

        output_path = TEMP_DIR / f"scene_{scene_id}_raw.mp4"
        return self.download_video(result["download_url"], output_path)
