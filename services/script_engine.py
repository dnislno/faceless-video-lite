"""Script generation engine for Indonesian commercial videos."""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CommercialScene:
    """Represents a single scene in the commercial video."""

    scene_id: int
    phase: str
    narration: str
    pexels_query: str
    target_duration: float


@dataclass
class CommercialScript:
    """Represents the complete commercial script consisting of multiple scenes."""

    product_title: str
    target_market: str
    scenes: List[CommercialScene]

    @property
    def total_estimated_duration(self) -> float:
        """Returns the sum of estimated durations of all scenes."""
        return sum(scene.target_duration for scene in self.scenes)

    @property
    def full_narration(self) -> str:
        """Returns concatenated narration for the entire video."""
        return " ".join(scene.narration for scene in self.scenes)


class ScriptEngine:
    """Generates viral Indonesian commercial scripts tailored for short-form video."""

    def __init__(self) -> None:
        pass

    def generate_script(self, user_prompt: str) -> CommercialScript:
        """Generates a structured 4-scene commercial script based on user prompt.

        The structure follows the viral AIDA (Attention, Interest, Desire, Action)
        formula standard in Indonesian TikTok and Shopee Video commerce.
        """
        logger.info(f"Generating commercial script for prompt: '{user_prompt}'")

        # Extract price if mentioned (e.g. 50rb, 50 ribu, 50.000)
        price_str = "50 ribuan"
        price_match = re.search(r"(\d+)\s*(rb|ribu|k|\.000)", user_prompt, re.IGNORECASE)
        if price_match:
            price_str = f"{price_match.group(1)} ribuan"

        # Check for cosmetic / lipstick keywords
        is_lipstick_or_cosmetic = any(
            kw in user_prompt.lower()
            for kw in ["lipstik", "lipstick", "lip tint", "kosmetik", "ombre"]
        )

        if is_lipstick_or_cosmetic:
            scenes = [
                CommercialScene(
                    scene_id=1,
                    phase="Hook / Attention",
                    narration="Mau ombre lips ala cewek Korea yang fresh seharian?",
                    pexels_query="korean woman beauty face smiling",
                    target_duration=3.6,
                ),
                CommercialScene(
                    scene_id=2,
                    phase="Problem & Agitation",
                    narration="Gak usah takut bibir kering atau pecah-pecah lagi!",
                    pexels_query="woman face makeup mirror close up",
                    target_duration=3.5,
                ),
                CommercialScene(
                    scene_id=3,
                    phase="Solution & USP",
                    narration="Korean Velvet Tint, teksturnya super lembut, ringan, dan transferproof!",
                    pexels_query="applying lipstick beautiful lips macro",
                    target_duration=5.5,
                ),
                CommercialScene(
                    scene_id=4,
                    phase="CTA & Scarcity",
                    narration=f"Flash sale cuma {price_str}! Buruan klik keranjang kuning sekarang!",
                    pexels_query="happy smiling woman shopping portrait",
                    target_duration=5.5,
                ),
            ]
            product_title = "Korean Velvet Lip Tint"
        else:
            # General viral commercial template
            scenes = [
                CommercialScene(
                    scene_id=1,
                    phase="Hook / Attention",
                    narration="Stop scroll! Ini rahasia viral yang wajib kamu punya!",
                    pexels_query="person looking surprised mobile phone portrait",
                    target_duration=3.5,
                ),
                CommercialScene(
                    scene_id=2,
                    phase="Problem & Agitation",
                    narration="Gak perlu bayar mahal untuk dapetin kualitas terbaik!",
                    pexels_query="frustrated person thinking portrait",
                    target_duration=3.5,
                ),
                CommercialScene(
                    scene_id=3,
                    phase="Solution & USP",
                    narration="Praktis digunakan, super awet, dan hasilnya langsung kelihatan nyata!",
                    pexels_query="product presentation aesthetic closeup",
                    target_duration=5.0,
                ),
                CommercialScene(
                    scene_id=4,
                    phase="CTA & Scarcity",
                    narration=f"Harga spesial promo cuma {price_str}! Checkout sekarang sebelum kehabisan!",
                    pexels_query="happy customer celebrating portrait",
                    target_duration=5.0,
                ),
            ]
            product_title = "Trending Product"

        script = CommercialScript(
            product_title=product_title,
            target_market="Indonesia (TikTok & Shopee Video)",
            scenes=scenes,
        )
        logger.info(
            f"Commercial script generated with {len(scenes)} scenes. "
            f"Total estimated duration: {script.total_estimated_duration:.1f}s"
        )
        return script
