"""IP-Adapter Integration for Character Consistency.

Loads character reference images and uses them to influence FLUX image
generation, ensuring characters maintain consistent appearance across
all videos.

Two modes of operation:
1. Prompt Enhancement (lightweight, no extra model needed):
   - Appends detailed character descriptions from reference analysis
   - Works with any FLUX pipeline without IP-Adapter weights

2. IP-Adapter Embedding (full consistency, requires adapter weights):
   - Extracts visual embeddings from reference images
   - Injects them into the generation pipeline
   - Requires ip-adapter model (~2GB)

Currently implements Mode 1 (Prompt Enhancement) as it works immediately
without additional model downloads. Mode 2 can be added when IP-Adapter
for FLUX becomes more stable.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class CharacterReference:
    """A character's reference data for consistency."""
    name: str
    prompt_description: str
    reference_images: List[str] = field(default_factory=list)
    _loaded_images: Optional[List[Image.Image]] = field(default=None, repr=False)

    def has_reference(self) -> bool:
        """Check if this character has reference images available."""
        return len(self.reference_images) > 0 and all(
            os.path.exists(p) for p in self.reference_images
        )

    def get_reference_image(self) -> Optional[Image.Image]:
        """Load and return the first reference image."""
        if not self.has_reference():
            return None
        if self._loaded_images is None:
            self._loaded_images = []
            for path in self.reference_images:
                try:
                    img = Image.open(path).convert("RGB")
                    self._loaded_images.append(img)
                except Exception as e:
                    logger.warning(f"Failed to load reference image {path}: {e}")
        return self._loaded_images[0] if self._loaded_images else None


def load_character_references(characters_dir: str = "models/characters") -> Dict[str, CharacterReference]:
    """Load all character references from disk.

    Args:
        characters_dir: Path to the models/characters/ directory.

    Returns:
        Dict mapping character name -> CharacterReference.
    """
    references = {}

    if not os.path.isdir(characters_dir):
        return references

    for entry in sorted(os.listdir(characters_dir)):
        entry_path = os.path.join(characters_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        char_json_path = os.path.join(entry_path, "character.json")
        if not os.path.isfile(char_json_path):
            continue

        try:
            with open(char_json_path, "r") as f:
                data = json.load(f)

            name = data.get("name", entry)
            ref = CharacterReference(
                name=name,
                prompt_description=data.get("prompt_description", ""),
                reference_images=data.get("reference_images", []),
            )
            references[name] = ref

            if ref.has_reference():
                logger.debug(f"Character '{name}' has reference image")
            else:
                logger.debug(f"Character '{name}' — no reference image (text-only)")

        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load character {entry}: {e}")

    logger.info(
        f"Loaded {len(references)} characters, "
        f"{sum(1 for r in references.values() if r.has_reference())} with reference images"
    )
    return references


def enhance_prompt_with_reference(
    base_prompt: str,
    character_names: List[str],
    references: Dict[str, CharacterReference],
) -> str:
    """Enhance an image prompt with character reference descriptions.

    Mode 1 (Prompt Enhancement): Appends detailed character descriptions
    to the prompt to improve consistency without needing IP-Adapter weights.

    Args:
        base_prompt: The original scene prompt.
        character_names: Characters present in this scene.
        references: Loaded character references.

    Returns:
        Enhanced prompt with character descriptions.
    """
    # Collect descriptions for characters in this scene
    char_descriptions = []
    for name in character_names:
        ref = references.get(name)
        if ref and ref.prompt_description:
            char_descriptions.append(ref.prompt_description)

    if not char_descriptions:
        return base_prompt

    # Append character descriptions to prompt
    # Put the most important character first (first in list)
    char_text = ", ".join(char_descriptions)
    enhanced = f"{base_prompt}, {char_text}"

    return enhanced


def get_reference_images_for_scene(
    character_names: List[str],
    references: Dict[str, CharacterReference],
) -> List[Image.Image]:
    """Get reference images for characters in a scene.

    Used for future IP-Adapter Mode 2 integration.

    Args:
        character_names: Characters present in this scene.
        references: Loaded character references.

    Returns:
        List of reference PIL images (may be empty).
    """
    images = []
    for name in character_names:
        ref = references.get(name)
        if ref and ref.has_reference():
            img = ref.get_reference_image()
            if img:
                images.append(img)
    return images
