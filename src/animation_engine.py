"""Animation Engine for the Ramayan Video Generator.

Generates animated frames from scene descriptions using AI image generation
models (Stable Diffusion), with character consistency via IP-Adapter embeddings,
frame interpolation for smooth animation, and CLIP-based quality validation.

Uses Protocol-based design for all external ML dependencies to enable
dependency injection and testability.

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

from PIL import Image

from src.config_loader import AnimationConfig
from src.episode_script import EpisodeScript, Scene

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AnimationEngineError(Exception):
    """Raised when the AnimationEngine encounters an error."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class CharacterEmbedding:
    """Character reference data for IP-Adapter consistency."""

    name: str
    reference_images: List[str]
    embedding_file: str
    prompt_description: str


@dataclass
class GeneratedFrame:
    """A single generated frame with metadata."""

    path: str
    width: int
    height: int
    quality_score: float = 0.0


@dataclass
class SceneFrames:
    """All frames generated for a single scene."""

    scene_number: int
    keyframes: List[GeneratedFrame]
    interpolated_frames: List[GeneratedFrame]
    all_frames: List[GeneratedFrame] = field(default_factory=list)

    def __post_init__(self):
        if not self.all_frames:
            self.all_frames = self.keyframes + self.interpolated_frames


@dataclass
class EpisodeFrames:
    """All frames generated for an entire episode."""

    episode_number: int
    scene_frames: List[SceneFrames]
    thumbnail: Optional[GeneratedFrame] = None


# ---------------------------------------------------------------------------
# Protocols (interfaces for external ML dependencies)
# ---------------------------------------------------------------------------


class ImageGenerator(Protocol):
    """Protocol for AI image generation (e.g., Stable Diffusion)."""

    def generate(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        num_images: int,
        lora_path: Optional[str],
        character_embeddings: Optional[List[Dict[str, Any]]],
    ) -> List[Image.Image]:
        """Generate images from a text prompt.

        Args:
            prompt: The text prompt describing the image.
            negative_prompt: Negative prompt for undesired features.
            width: Output image width in pixels.
            height: Output image height in pixels.
            num_images: Number of images to generate.
            lora_path: Path to LoRA weights for style consistency.
            character_embeddings: List of character embedding dicts for
                IP-Adapter consistency.

        Returns:
            List of PIL Image objects.
        """
        ...


class QualityScorer(Protocol):
    """Protocol for CLIP-based frame quality scoring."""

    def score(self, image: Image.Image, prompt: str) -> float:
        """Score an image's quality and prompt alignment.

        Args:
            image: The PIL Image to score.
            prompt: The original generation prompt.

        Returns:
            A quality score between 0.0 and 1.0.
        """
        ...


class FrameInterpolator(Protocol):
    """Protocol for frame interpolation (e.g., AnimateDiff, FILM)."""

    def interpolate(
        self,
        frame_a: Image.Image,
        frame_b: Image.Image,
        num_intermediate_frames: int,
    ) -> List[Image.Image]:
        """Generate intermediate frames between two keyframes.

        Args:
            frame_a: The starting keyframe.
            frame_b: The ending keyframe.
            num_intermediate_frames: Number of frames to generate between
                the two keyframes.

        Returns:
            List of intermediate PIL Image objects (not including the
            input keyframes).
        """
        ...


# ---------------------------------------------------------------------------
# Default Implementations (placeholder for real ML pipelines)
# ---------------------------------------------------------------------------


class StableDiffusionGenerator:
    """Concrete image generator using Stable Diffusion via diffusers library.

    This is a placeholder that creates solid-color images at the correct
    resolution. In production, this would load the actual SD pipeline.
    """

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
        """Generate placeholder images at the specified resolution."""
        images = []
        for _ in range(num_images):
            img = Image.new("RGB", (width, height), color=(128, 100, 80))
            images.append(img)
        return images


class CLIPQualityScorer:
    """Concrete quality scorer using CLIP.

    Placeholder implementation that returns a fixed score.
    In production, this would use CLIP to evaluate prompt-image alignment.
    """

    def __init__(self, threshold: float = 0.7):
        self._threshold = threshold

    def score(self, image: Image.Image, prompt: str) -> float:
        """Return a placeholder quality score."""
        return 0.85


class FILMFrameInterpolator:
    """Concrete frame interpolator using FILM or AnimateDiff.

    Placeholder implementation that creates blended intermediate frames.
    In production, this would use actual frame interpolation models.
    """

    def interpolate(
        self,
        frame_a: Image.Image,
        frame_b: Image.Image,
        num_intermediate_frames: int,
    ) -> List[Image.Image]:
        """Generate placeholder intermediate frames by blending."""
        frames = []
        for i in range(num_intermediate_frames):
            alpha = (i + 1) / (num_intermediate_frames + 1)
            blended = Image.blend(frame_a.convert("RGB"), frame_b.convert("RGB"), alpha)
            frames.append(blended)
        return frames


# ---------------------------------------------------------------------------
# Character Embedding Loader (Task 5.2)
# ---------------------------------------------------------------------------


def load_character_embeddings(
    characters_dir: str,
    character_names: List[str],
) -> List[CharacterEmbedding]:
    """Load character reference embeddings for the specified characters.

    Looks for character subdirectories in the characters_dir. Each character
    directory should contain a `character.json` with fields:
    - name: str
    - reference_images: list of image filenames
    - embedding_file: filename of the embedding file
    - prompt_description: text description for prompt injection

    Args:
        characters_dir: Path to the models/characters/ directory.
        character_names: List of character names to load embeddings for.

    Returns:
        List of CharacterEmbedding objects for characters that have
        embedding data available.
    """
    embeddings: List[CharacterEmbedding] = []

    if not os.path.isdir(characters_dir):
        logger.warning("Characters directory not found: %s", characters_dir)
        return embeddings

    # Build a mapping of character name -> directory
    char_dirs: Dict[str, str] = {}
    for entry in os.listdir(characters_dir):
        entry_path = os.path.join(characters_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        char_json_path = os.path.join(entry_path, "character.json")
        if os.path.isfile(char_json_path):
            try:
                with open(char_json_path, "r") as f:
                    data = json.load(f)
                name = data.get("name", entry)
                char_dirs[name] = entry_path
            except (json.JSONDecodeError, OSError):
                continue

    # Load embeddings for requested characters
    for char_name in character_names:
        if char_name not in char_dirs:
            logger.debug("No embedding data found for character: %s", char_name)
            continue

        char_path = char_dirs[char_name]
        char_json_path = os.path.join(char_path, "character.json")

        try:
            with open(char_json_path, "r") as f:
                data = json.load(f)

            embedding_file = data.get("embedding_file", "")
            if embedding_file:
                embedding_file = os.path.join(char_path, embedding_file)

            reference_images = [
                os.path.join(char_path, img)
                for img in data.get("reference_images", [])
            ]

            embeddings.append(
                CharacterEmbedding(
                    name=data.get("name", char_name),
                    reference_images=reference_images,
                    embedding_file=embedding_file,
                    prompt_description=data.get("prompt_description", ""),
                )
            )
            logger.info("Loaded embedding for character: %s", char_name)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Failed to load embedding for character %s: %s", char_name, e
            )

    return embeddings


# ---------------------------------------------------------------------------
# AnimationEngine (Tasks 5.1 - 5.5)
# ---------------------------------------------------------------------------


# Style prompt prefix for Indian traditional art (kept short to leave room for scene details)
STYLE_PROMPT_PREFIX = "Rajput miniature painting style, "

NEGATIVE_PROMPT = (
    "blurry, low quality, distorted, deformed, ugly, "
    "modern style, photorealistic, 3d render, cartoon, anime, "
    "western art style, watermark, text, signature"
)

# Number of keyframes to generate per scene
KEYFRAMES_PER_SCENE = 3

# Quality threshold for frame acceptance
QUALITY_THRESHOLD = 0.6

# Maximum retry attempts for quality validation
MAX_QUALITY_RETRIES = 3

# Minimum FPS for interpolated animation
MIN_INTERPOLATION_FPS = 12


class AnimationEngine:
    """Generates animated frames from episode script scene descriptions.

    The engine:
    1. Generates keyframes for each scene using Stable Diffusion with LoRA
    2. Injects character embeddings via IP-Adapter for consistency
    3. Interpolates between keyframes for smooth animation
    4. Validates frame quality using CLIP scoring
    5. Selects the best frame as episode thumbnail

    All external ML dependencies are injectable via Protocol interfaces
    for testability.

    Args:
        config: AnimationConfig with resolution, fps, model, lora settings.
        image_generator: An object implementing the ImageGenerator protocol.
        quality_scorer: An object implementing the QualityScorer protocol.
        frame_interpolator: An object implementing the FrameInterpolator protocol.
        characters_dir: Path to the models/characters/ directory.
        quality_threshold: Minimum quality score for frame acceptance.
        max_retries: Maximum retry attempts for quality validation.
    """

    def __init__(
        self,
        config: AnimationConfig,
        image_generator: Optional[Any] = None,
        quality_scorer: Optional[Any] = None,
        frame_interpolator: Optional[Any] = None,
        characters_dir: str = "models/characters",
        quality_threshold: float = QUALITY_THRESHOLD,
        max_retries: int = MAX_QUALITY_RETRIES,
    ):
        self._config = config
        self._image_generator = image_generator or StableDiffusionGenerator()
        self._quality_scorer = quality_scorer or CLIPQualityScorer()
        self._frame_interpolator = frame_interpolator or FILMFrameInterpolator()
        self._characters_dir = characters_dir
        self._quality_threshold = quality_threshold
        self._max_retries = max_retries

    @property
    def width(self) -> int:
        """Configured output width."""
        return self._config.resolution[0]

    @property
    def height(self) -> int:
        """Configured output height."""
        return self._config.resolution[1]

    def _build_scene_prompt(
        self,
        scene: Scene,
        character_embeddings: List[CharacterEmbedding],
        total_scenes: int = 5,
    ) -> str:
        """Build the generation prompt for a scene with visual variety.

        Uses the visual_variety module to add composition directives and
        mood-specific styling based on the scene's role in the video structure.
        """
        from src.visual_variety import build_enhanced_image_prompt

        # Build base description from scene content
        base_parts = [scene.background, scene.action]
        for emb in character_embeddings:
            if emb.name in scene.characters and emb.prompt_description:
                base_parts.append(emb.prompt_description)
        base_prompt = ", ".join(base_parts)

        # Apply visual variety based on scene role
        enhanced_prompt = build_enhanced_image_prompt(
            base_prompt=base_prompt,
            scene_number=scene.scene_number,
            total_scenes=total_scenes,
            mood=scene.mood,
            characters=scene.characters,
        )

        return enhanced_prompt

    def _generate_keyframe_with_quality(
        self,
        prompt: str,
        character_embeddings: List[CharacterEmbedding],
        output_dir: str,
        frame_index: int,
    ) -> GeneratedFrame:
        """Generate a single keyframe with quality validation and retry logic.

        Generates a frame, scores its quality, and retries up to max_retries
        times if the quality is below threshold. Uses the best-scoring attempt
        if all attempts fail the threshold.

        Args:
            prompt: The generation prompt.
            character_embeddings: Character embeddings for IP-Adapter.
            output_dir: Directory to save the frame.
            frame_index: Index for filename.

        Returns:
            The best GeneratedFrame (highest quality score).
        """
        embedding_dicts = [
            {
                "name": emb.name,
                "embedding_file": emb.embedding_file,
                "reference_images": emb.reference_images,
            }
            for emb in character_embeddings
        ] if character_embeddings else None

        best_frame: Optional[GeneratedFrame] = None

        for attempt in range(self._max_retries):
            try:
                images = self._image_generator.generate(
                    prompt=prompt,
                    negative_prompt=NEGATIVE_PROMPT,
                    width=self.width,
                    height=self.height,
                    num_images=1,
                    lora_path=self._config.lora_path,
                    character_embeddings=embedding_dicts,
                )
            except Exception as e:
                logger.warning(
                    "Image generation failed (attempt %d/%d): %s",
                    attempt + 1,
                    self._max_retries,
                    e,
                )
                continue

            if not images:
                continue

            img = images[0]

            # Enforce minimum resolution
            if img.width < self.width or img.height < self.height:
                img = img.resize((self.width, self.height), Image.LANCZOS)

            # Score quality
            score = self._quality_scorer.score(img, prompt)

            frame_path = os.path.join(
                output_dir, f"keyframe_{frame_index:04d}_attempt{attempt}.png"
            )
            img.save(frame_path)

            frame = GeneratedFrame(
                path=frame_path,
                width=img.width,
                height=img.height,
                quality_score=score,
            )

            if best_frame is None or score > best_frame.quality_score:
                # Clean up previous best if it exists
                if best_frame is not None and os.path.exists(best_frame.path):
                    os.remove(best_frame.path)
                best_frame = frame
            else:
                # Clean up this attempt
                if os.path.exists(frame_path):
                    os.remove(frame_path)

            if score >= self._quality_threshold:
                logger.info(
                    "Frame %d passed quality check (score=%.3f) on attempt %d",
                    frame_index,
                    score,
                    attempt + 1,
                )
                break
            else:
                logger.info(
                    "Frame %d below quality threshold (score=%.3f, threshold=%.3f), "
                    "attempt %d/%d",
                    frame_index,
                    score,
                    self._quality_threshold,
                    attempt + 1,
                    self._max_retries,
                )

        if best_frame is None:
            raise AnimationEngineError(
                f"Failed to generate keyframe {frame_index} after "
                f"{self._max_retries} attempts"
            )

        # Rename best frame to final name
        final_path = os.path.join(output_dir, f"keyframe_{frame_index:04d}.png")
        if best_frame.path != final_path:
            os.rename(best_frame.path, final_path)
            best_frame = GeneratedFrame(
                path=final_path,
                width=best_frame.width,
                height=best_frame.height,
                quality_score=best_frame.quality_score,
            )

        return best_frame

    def _generate_scene_keyframes(
        self,
        scene: Scene,
        character_embeddings: List[CharacterEmbedding],
        output_dir: str,
        total_scenes: int = 5,
    ) -> List[GeneratedFrame]:
        """Generate keyframes for a single scene.

        Args:
            scene: The scene to generate keyframes for.
            character_embeddings: Character embeddings for consistency.
            output_dir: Directory to save frames.
            total_scenes: Total number of scenes in the episode (for visual variety).

        Returns:
            List of GeneratedFrame objects for the scene's keyframes.
        """
        prompt = self._build_scene_prompt(scene, character_embeddings, total_scenes)
        keyframes: List[GeneratedFrame] = []

        for i in range(KEYFRAMES_PER_SCENE):
            frame = self._generate_keyframe_with_quality(
                prompt=prompt,
                character_embeddings=character_embeddings,
                output_dir=output_dir,
                frame_index=i,
            )
            keyframes.append(frame)

        return keyframes

    def _interpolate_scene_frames(
        self,
        keyframes: List[GeneratedFrame],
        scene: Scene,
        output_dir: str,
    ) -> List[GeneratedFrame]:
        """Interpolate between keyframes to achieve smooth animation.

        Calculates the number of intermediate frames needed based on the
        scene duration and target FPS to achieve at least MIN_INTERPOLATION_FPS.

        Args:
            keyframes: The scene's keyframes.
            scene: The scene (for duration info).
            output_dir: Directory to save interpolated frames.

        Returns:
            List of interpolated GeneratedFrame objects.
        """
        if len(keyframes) < 2:
            return []

        # Calculate total frames needed for this scene at minimum FPS
        total_frames_needed = max(
            scene.duration_seconds * MIN_INTERPOLATION_FPS,
            len(keyframes),
        )

        # Number of gaps between keyframes
        num_gaps = len(keyframes) - 1
        # Frames per gap (excluding the keyframes themselves)
        frames_per_gap = max(
            1,
            (total_frames_needed - len(keyframes)) // num_gaps,
        )

        interpolated: List[GeneratedFrame] = []

        for gap_idx in range(num_gaps):
            kf_a = Image.open(keyframes[gap_idx].path)
            kf_b = Image.open(keyframes[gap_idx + 1].path)

            try:
                intermediate_images = self._frame_interpolator.interpolate(
                    frame_a=kf_a,
                    frame_b=kf_b,
                    num_intermediate_frames=frames_per_gap,
                )
            except Exception as e:
                logger.warning(
                    "Frame interpolation failed for gap %d: %s", gap_idx, e
                )
                continue

            for i, img in enumerate(intermediate_images):
                # Enforce resolution
                if img.width < self.width or img.height < self.height:
                    img = img.resize((self.width, self.height), Image.LANCZOS)

                frame_path = os.path.join(
                    output_dir,
                    f"interp_{gap_idx:03d}_{i:04d}.png",
                )
                img.save(frame_path)

                interpolated.append(
                    GeneratedFrame(
                        path=frame_path,
                        width=img.width,
                        height=img.height,
                        quality_score=0.0,  # Interpolated frames not scored
                    )
                )

        return interpolated

    def generate_episode_frames(
        self,
        script: EpisodeScript,
        output_dir: Optional[str] = None,
    ) -> EpisodeFrames:
        """Generate all animated frames for an episode.

        For each scene in the script:
        1. Load character embeddings for characters in the scene
        2. Generate keyframes with quality validation
        3. Interpolate between keyframes for smooth animation

        After all scenes, select the best frame as the episode thumbnail.

        Args:
            script: The episode script with scene descriptions.
            output_dir: Directory to save frames. If None, creates a
                temporary directory.

        Returns:
            EpisodeFrames containing all generated frames and thumbnail.

        Raises:
            AnimationEngineError: If frame generation fails critically.
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="ramayan_frames_")

        os.makedirs(output_dir, exist_ok=True)

        all_scene_frames: List[SceneFrames] = []

        for scene in script.scenes:
            scene_dir = os.path.join(
                output_dir, f"scene_{scene.scene_number:03d}"
            )
            os.makedirs(scene_dir, exist_ok=True)

            # Load character embeddings for this scene's characters
            character_embeddings = load_character_embeddings(
                self._characters_dir, scene.characters
            )

            logger.info(
                "Generating keyframes for scene %d (%d characters, %d embeddings)",
                scene.scene_number,
                len(scene.characters),
                len(character_embeddings),
            )

            # Generate keyframes
            keyframes = self._generate_scene_keyframes(
                scene, character_embeddings, scene_dir,
                total_scenes=len(script.scenes),
            )

            # Interpolate between keyframes
            interpolated = self._interpolate_scene_frames(
                keyframes, scene, scene_dir
            )

            # Build ordered frame list: kf0, interp0_*, kf1, interp1_*, ..., kfN
            all_frames: List[GeneratedFrame] = []
            interp_idx = 0
            frames_per_gap = (
                len(interpolated) // (len(keyframes) - 1)
                if len(keyframes) > 1 and interpolated
                else 0
            )

            for kf_idx, kf in enumerate(keyframes):
                all_frames.append(kf)
                if kf_idx < len(keyframes) - 1 and frames_per_gap > 0:
                    gap_frames = interpolated[
                        interp_idx : interp_idx + frames_per_gap
                    ]
                    all_frames.extend(gap_frames)
                    interp_idx += frames_per_gap

            # Add any remaining interpolated frames
            all_frames.extend(interpolated[interp_idx:])

            scene_frames = SceneFrames(
                scene_number=scene.scene_number,
                keyframes=keyframes,
                interpolated_frames=interpolated,
                all_frames=all_frames,
            )
            all_scene_frames.append(scene_frames)

            logger.info(
                "Scene %d: %d keyframes, %d interpolated, %d total frames",
                scene.scene_number,
                len(keyframes),
                len(interpolated),
                len(all_frames),
            )

        # Select thumbnail (Task 5.5)
        thumbnail = self._select_thumbnail(all_scene_frames)

        episode_frames = EpisodeFrames(
            episode_number=script.episode_number,
            scene_frames=all_scene_frames,
            thumbnail=thumbnail,
        )

        logger.info(
            "Episode %d: generated frames for %d scenes, thumbnail: %s",
            script.episode_number,
            len(all_scene_frames),
            thumbnail.path if thumbnail else "none",
        )

        return episode_frames

    def _select_thumbnail(
        self,
        scene_frames: List[SceneFrames],
    ) -> Optional[GeneratedFrame]:
        """Select the highest-quality frame as the episode thumbnail.

        Examines all keyframes across all scenes and returns the one
        with the highest quality score.

        Args:
            scene_frames: List of SceneFrames for the episode.

        Returns:
            The highest-quality GeneratedFrame, or None if no frames exist.
        """
        best_frame: Optional[GeneratedFrame] = None

        for sf in scene_frames:
            for kf in sf.keyframes:
                if best_frame is None or kf.quality_score > best_frame.quality_score:
                    best_frame = kf

        if best_frame is not None:
            logger.info(
                "Selected thumbnail: %s (score=%.3f)",
                best_frame.path,
                best_frame.quality_score,
            )

        return best_frame
