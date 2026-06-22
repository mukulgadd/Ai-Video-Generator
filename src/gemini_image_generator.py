"""Gemini Image Generator for the Ramayan Video Generator.

Uses Google's Gemini API (Imagen model) to generate images.
Implements the ImageGenerator Protocol from animation_engine.py.

This avoids the MPS float16 NaN issue with local Stable Diffusion
and produces high-quality images via API.
"""

import io
import logging
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from PIL import Image

logger = logging.getLogger(__name__)

# Style prefix for Indian traditional art
STYLE_PREFIX = (
    "Indian traditional Rajput miniature painting style, "
    "ornate details, rich vibrant colors, gold accents, "
    "stylized figures, detailed background, high quality, "
    "4k resolution, "
)


class GeminiImageGenerator:
    """Image generator using Google Gemini's image generation.

    Implements the ImageGenerator Protocol from animation_engine.py.
    Uses Gemini's native image generation capability.

    Args:
        api_key: Gemini API key. If None, reads from GEMINI_API_KEY env var.
        model: Gemini model to use for image generation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash-image",
    ):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "Gemini API key not provided. Set GEMINI_API_KEY env var."
            )
        self._client = genai.Client(api_key=key)
        self._model = model

    def generate(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        num_images: int,
        lora_path: Optional[str] = None,
        character_embeddings: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Image.Image]:
        """Generate images using Gemini's image generation.

        Args:
            prompt: Scene description to generate.
            negative_prompt: Ignored (Gemini doesn't support negative prompts).
            width: Target width (image will be resized).
            height: Target height (image will be resized).
            num_images: Number of images to generate.
            lora_path: Ignored (not applicable for API-based generation).
            character_embeddings: Ignored (not supported yet).

        Returns:
            List of PIL Image objects at the requested resolution.
        """
        full_prompt = (
            f"Generate an illustration in {STYLE_PREFIX}. "
            f"Scene: {prompt}. "
            f"The image should be vertical/portrait orientation, "
            f"suitable for a YouTube Shorts video frame."
        )

        images = []
        for i in range(num_images):
            logger.info("Generating image %d/%d via Gemini...", i + 1, num_images)

            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["image", "text"],
                    ),
                )

                # Extract image from response
                img = None
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        img_bytes = part.inline_data.data
                        img = Image.open(io.BytesIO(img_bytes))
                        break

                if img is None:
                    logger.warning(
                        "Gemini returned no image for attempt %d, using fallback",
                        i + 1,
                    )
                    img = Image.new("RGB", (width, height), color=(128, 100, 80))
                else:
                    # Resize to target dimensions
                    if img.size != (width, height):
                        img = img.resize((width, height), Image.LANCZOS)

                images.append(img)

            except Exception as e:
                logger.warning("Gemini image generation failed: %s", e)
                # Fallback to solid color
                images.append(
                    Image.new("RGB", (width, height), color=(128, 100, 80))
                )

        return images
