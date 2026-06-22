"""Stable Diffusion Image Generator for Apple Silicon (MPS).

Real implementation of the ImageGenerator Protocol using Stable Diffusion XL
via HuggingFace Diffusers, running on Apple M-series GPU via MPS backend.

Requirements:
- Apple Silicon Mac (M1/M2/M3)
- ~10GB disk space for SDXL model weights (downloaded on first run)
- ~8GB unified memory during inference
"""

import logging
from typing import Any, Dict, List, Optional

import torch
from diffusers import StableDiffusionXLPipeline
from PIL import Image

logger = logging.getLogger(__name__)


# Don't add extra style — the animation engine already adds style to the prompt
STYLE_PREFIX = ""

NEGATIVE_PROMPT_DEFAULT = (
    "blurry, low quality, distorted, deformed, ugly, "
    "photorealistic, 3d render, modern, western style, "
    "watermark, text, signature, cropped"
)


class SDXLImageGenerator:
    """Image generator using Stable Diffusion XL on Apple Silicon (MPS).

    Implements the ImageGenerator Protocol from animation_engine.py.

    The model is loaded lazily on first call to generate() to avoid
    blocking startup. Uses float16 precision and MPS device for
    optimal performance on M-series chips.

    Args:
        model_id: HuggingFace model ID. Defaults to SDXL base.
        num_inference_steps: Denoising steps (fewer = faster, less detail).
            Default 30 is a good balance for M3 Pro.
        guidance_scale: How strongly to follow the prompt. Default 7.5.
    """

    def __init__(
        self,
        model_id: str = "stabilityai/stable-diffusion-xl-base-1.0",
        num_inference_steps: int = 15,
        guidance_scale: float = 7.5,
    ):
        self._model_id = model_id
        self._num_inference_steps = num_inference_steps
        self._guidance_scale = guidance_scale
        self._pipe: Optional[StableDiffusionXLPipeline] = None
        self._device = "mps" if torch.backends.mps.is_available() else "cpu"

    def _load_pipeline(self) -> StableDiffusionXLPipeline:
        """Load the SDXL pipeline (lazy, first call only)."""
        if self._pipe is not None:
            return self._pipe

        logger.info(
            "Loading Stable Diffusion XL pipeline on %s (first run downloads ~6.5GB)...",
            self._device,
        )

        self._pipe = StableDiffusionXLPipeline.from_pretrained(
            self._model_id,
            torch_dtype=torch.float32,
            use_safetensors=True,
        )

        # Use CPU to avoid MPS float16 NaN issue on Apple Silicon
        # Slower (~3-4 min per image) but produces correct output
        if self._device == "mps":
            logger.info("Using CPU for SDXL (MPS has float16 NaN issue)")
            self._pipe = self._pipe.to("cpu")
        else:
            self._pipe = self._pipe.to(self._device)

        # Memory optimization
        self._pipe.enable_attention_slicing()

        logger.info("SDXL pipeline loaded successfully.")
        return self._pipe

    def _load_lora(self, lora_path: str) -> None:
        """Load LoRA weights if available."""
        try:
            self._pipe.load_lora_weights(lora_path)
            logger.info("LoRA weights loaded from %s", lora_path)
        except Exception as e:
            logger.warning("Could not load LoRA weights from %s: %s", lora_path, e)

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
        """Generate images from a text prompt using SDXL.

        Args:
            prompt: Scene description to generate.
            negative_prompt: What to avoid. Falls back to default if empty.
            width: Output width (will be rounded to nearest multiple of 8).
            height: Output height (will be rounded to nearest multiple of 8).
            num_images: Number of images to generate.
            lora_path: Optional path to LoRA weights for style.
            character_embeddings: Currently unused (IP-Adapter integration
                would go here in a future iteration).

        Returns:
            List of PIL Image objects at the requested resolution.
        """
        pipe = self._load_pipeline()

        # Load LoRA if path provided and file exists
        if lora_path:
            import os
            if os.path.isfile(lora_path):
                self._load_lora(lora_path)

        # Prepend style prefix to the prompt
        full_prompt = STYLE_PREFIX + prompt

        # Use default negative prompt if none provided
        if not negative_prompt:
            negative_prompt = NEGATIVE_PROMPT_DEFAULT

        # Round dimensions to multiples of 8 (required by SDXL)
        width = (width // 8) * 8
        height = (height // 8) * 8

        # SDXL works best at 1024x1024; scale down for generation then upscale
        # For 1080x1920, generate at 768x1344 (maintains ~9:16 ratio) then resize
        gen_width = min(width, 768)
        gen_height = min(height, 1344)
        gen_width = (gen_width // 8) * 8
        gen_height = (gen_height // 8) * 8

        images = []
        for i in range(num_images):
            logger.info(
                "Generating image %d/%d (%dx%d -> %dx%d)...",
                i + 1, num_images, gen_width, gen_height, width, height,
            )

            with torch.no_grad():
                result = pipe(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    width=gen_width,
                    height=gen_height,
                    num_inference_steps=self._num_inference_steps,
                    guidance_scale=self._guidance_scale,
                )

            img = result.images[0]

            # Resize to target resolution if generated at smaller size
            if img.size != (width, height):
                img = img.resize((width, height), Image.LANCZOS)

            images.append(img)

        return images
