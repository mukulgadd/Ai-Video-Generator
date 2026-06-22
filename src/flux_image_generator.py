"""FLUX.1 Schnell Image Generator for Apple Silicon (MPS).

Free, local image generation using Black Forest Labs' FLUX.1-schnell model.
Runs on Apple M-series GPU via MPS backend. Only needs 4 inference steps.

Key advantages over SDXL:
- 256+ token prompt limit (T5 encoder) vs SDXL's 77 tokens (CLIP)
- Works correctly on MPS with float16 (no NaN issues)
- Only 4 inference steps needed (much faster)
- Better overall image quality

Requirements:
- Apple Silicon Mac (M1/M2/M3)
- ~12GB unified memory during inference
- ~12GB disk for model weights (downloaded on first run)
- HuggingFace token with access to FLUX.1-schnell (free license)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import torch
from PIL import Image

logger = logging.getLogger(__name__)


class FluxImageGenerator:
    """Image generator using FLUX.1-schnell on Apple Silicon (MPS).

    Implements the ImageGenerator Protocol from animation_engine.py.

    FLUX Schnell uses a T5-XXL text encoder that supports 256+ tokens,
    allowing much more detailed prompts than SDXL's 77-token CLIP limit.

    Args:
        num_inference_steps: Number of denoising steps. Default 4 (FLUX Schnell
            is optimized for 1-4 steps).
    """

    def __init__(self, num_inference_steps: int = 4):
        self._num_inference_steps = num_inference_steps
        self._pipe = None
        self._device = "mps" if torch.backends.mps.is_available() else "cpu"

    def _load_pipeline(self):
        """Load the FLUX pipeline (lazy, first call only)."""
        if self._pipe is not None:
            return self._pipe

        from diffusers import FluxPipeline

        logger.info(
            "Loading FLUX.1-schnell pipeline on %s (first run downloads ~12GB)...",
            self._device,
        )

        # Use HF_TOKEN from environment for gated model access
        token = os.environ.get("HF_TOKEN")

        self._pipe = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-schnell",
            torch_dtype=torch.float16,
            token=token,
        )
        self._pipe = self._pipe.to(self._device)
        self._pipe.enable_attention_slicing()

        logger.info("FLUX pipeline loaded successfully.")
        return self._pipe

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
        """Generate images using FLUX.1-schnell.

        Takes advantage of FLUX's 256+ token T5 encoder to use the
        full prompt without truncation.

        Args:
            prompt: Scene description (can be 200+ tokens — all preserved).
            negative_prompt: Ignored (FLUX Schnell doesn't use negative prompts).
            width: Target width (will generate at optimal size then resize).
            height: Target height.
            num_images: Number of images to generate.
            lora_path: Ignored for now.
            character_embeddings: Ignored for now.

        Returns:
            List of PIL Image objects at the requested resolution.
        """
        pipe = self._load_pipeline()

        # FLUX works best at certain resolutions. Generate at smaller size
        # to fit in memory on 36GB M3 Pro, then resize to target.
        gen_width = min(width, 512)
        gen_height = min(height, 896)
        # Round to multiple of 16 (FLUX requirement)
        gen_width = (gen_width // 16) * 16
        gen_height = (gen_height // 16) * 16

        images = []
        for i in range(num_images):
            logger.info(
                "Generating image %d/%d (%dx%d -> %dx%d) with FLUX...",
                i + 1, num_images, gen_width, gen_height, width, height,
            )

            with torch.no_grad():
                result = pipe(
                    prompt=prompt,
                    width=gen_width,
                    height=gen_height,
                    num_inference_steps=self._num_inference_steps,
                    guidance_scale=0.0,  # FLUX Schnell uses guidance_scale=0
                )

            img = result.images[0]

            # Resize to target resolution
            if img.size != (width, height):
                img = img.resize((width, height), Image.LANCZOS)

            images.append(img)

        return images
