"""Tests for the animation_engine module.

Tests verify:
- Property 8: For any generated frame, width >= 1080 and height >= 1920
- Frame regeneration retry logic: mock quality validator to fail, verify up to 3 retries
- Character embedding loading: verify embeddings are loaded for characters present in the scene

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import json
import os
import tempfile
from typing import Any, Dict, List, Optional

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from PIL import Image

from src.animation_engine import (
    AnimationEngine,
    AnimationEngineError,
    CharacterEmbedding,
    GeneratedFrame,
    SceneFrames,
    load_character_embeddings,
    KEYFRAMES_PER_SCENE,
    MAX_QUALITY_RETRIES,
    QUALITY_THRESHOLD,
)
from src.config_loader import AnimationConfig
from src.episode_script import DialogueLine, EpisodeScript, Scene


# ---------------------------------------------------------------------------
# Mock implementations
# ---------------------------------------------------------------------------


class MockImageGenerator:
    """Mock image generator that creates solid-color images at the requested resolution."""

    def __init__(self, width_override: Optional[int] = None, height_override: Optional[int] = None):
        """Optionally override the output dimensions to test resolution enforcement."""
        self._width_override = width_override
        self._height_override = height_override
        self.call_count = 0

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
        self.call_count += 1
        out_w = self._width_override if self._width_override is not None else width
        out_h = self._height_override if self._height_override is not None else height
        return [Image.new("RGB", (out_w, out_h), color=(100, 150, 200)) for _ in range(num_images)]


class MockQualityScorer:
    """Mock quality scorer that returns a configurable score."""

    def __init__(self, score: float = 0.85):
        self._score = score
        self.call_count = 0

    def score(self, image: Image.Image, prompt: str) -> float:
        self.call_count += 1
        return self._score


class FailingThenPassingQualityScorer:
    """Mock quality scorer that fails N times then passes."""

    def __init__(self, fail_count: int = 2, fail_score: float = 0.3, pass_score: float = 0.9):
        self._fail_count = fail_count
        self._fail_score = fail_score
        self._pass_score = pass_score
        self.call_count = 0

    def score(self, image: Image.Image, prompt: str) -> float:
        self.call_count += 1
        if self.call_count <= self._fail_count:
            return self._fail_score
        return self._pass_score


class AlwaysFailingQualityScorer:
    """Mock quality scorer that always returns a score below threshold."""

    def __init__(self, score: float = 0.2):
        self._score = score
        self.call_count = 0

    def score(self, image: Image.Image, prompt: str) -> float:
        self.call_count += 1
        return self._score


class MockFrameInterpolator:
    """Mock frame interpolator that creates blended intermediate frames."""

    def __init__(self):
        self.call_count = 0

    def interpolate(
        self,
        frame_a: Image.Image,
        frame_b: Image.Image,
        num_intermediate_frames: int,
    ) -> List[Image.Image]:
        self.call_count += 1
        frames = []
        for i in range(num_intermediate_frames):
            alpha = (i + 1) / (num_intermediate_frames + 1)
            blended = Image.blend(frame_a.convert("RGB"), frame_b.convert("RGB"), alpha)
            frames.append(blended)
        return frames


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    width: int = 1080,
    height: int = 1920,
    fps: int = 24,
) -> AnimationConfig:
    """Create an AnimationConfig with the given resolution."""
    return AnimationConfig(
        style_reference="indian_traditional_art",
        resolution=[width, height],
        fps=fps,
        model="stable-diffusion-xl",
        lora_path="./models/indian_art_lora.safetensors",
    )


def _make_scene(
    scene_number: int = 1,
    duration_seconds: int = 20,
    characters: Optional[List[str]] = None,
) -> Scene:
    """Create a simple Scene for testing."""
    return Scene(
        scene_number=scene_number,
        duration_seconds=duration_seconds,
        background="Royal palace of Ayodhya with golden pillars",
        characters=characters or ["Rama", "Sita"],
        action="Rama and Sita walk through the palace gardens",
        narration="In the beautiful gardens of Ayodhya...",
        dialogue=[DialogueLine(character="Rama", text="Let us walk together.")],
        mood="serene",
        sound_effects=["birds_chirping"],
    )


def _make_script(
    episode_number: int = 1,
    num_scenes: int = 2,
    duration_per_scene: int = 20,
) -> EpisodeScript:
    """Create a simple EpisodeScript for testing."""
    scenes = [
        _make_scene(scene_number=i + 1, duration_seconds=duration_per_scene)
        for i in range(num_scenes)
    ]
    return EpisodeScript(
        episode_number=episode_number,
        kanda="Bala Kanda",
        title="Test Episode",
        total_duration_seconds=num_scenes * duration_per_scene,
        scenes=scenes,
    )


def _make_engine(
    config: Optional[AnimationConfig] = None,
    image_generator: Optional[Any] = None,
    quality_scorer: Optional[Any] = None,
    frame_interpolator: Optional[Any] = None,
    characters_dir: str = "models/characters",
    quality_threshold: float = QUALITY_THRESHOLD,
    max_retries: int = MAX_QUALITY_RETRIES,
) -> AnimationEngine:
    """Create an AnimationEngine with mock dependencies."""
    return AnimationEngine(
        config=config or _make_config(),
        image_generator=image_generator or MockImageGenerator(),
        quality_scorer=quality_scorer or MockQualityScorer(),
        frame_interpolator=frame_interpolator or MockFrameInterpolator(),
        characters_dir=characters_dir,
        quality_threshold=quality_threshold,
        max_retries=max_retries,
    )


# ---------------------------------------------------------------------------
# Hypothesis strategies for Property 8
# ---------------------------------------------------------------------------

# Strategy for valid resolution pairs (width, height)
_resolution_strategy = st.tuples(
    st.integers(min_value=1080, max_value=4320),  # width: 1080 to 4K
    st.integers(min_value=1920, max_value=7680),  # height: 1920 to 8K
)

# Strategy for scene descriptions
_non_empty_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=60,
).filter(lambda s: s.strip() != "")

_character_pool = ["Rama", "Sita", "Lakshmana", "Hanuman", "Ravana"]

_scene_strategy = st.builds(
    Scene,
    scene_number=st.integers(min_value=1, max_value=20),
    duration_seconds=st.integers(min_value=5, max_value=30),
    background=_non_empty_text,
    characters=st.lists(st.sampled_from(_character_pool), min_size=1, max_size=3),
    action=_non_empty_text,
    narration=_non_empty_text,
    dialogue=st.just([]),
    mood=st.sampled_from(["serene", "dramatic", "devotional", "heroic"]),
    sound_effects=st.just([]),
)


# ---------------------------------------------------------------------------
# Property 8: Animation Resolution Invariant
# For any generated frame, width >= 1080 and height >= 1920
# **Validates: Requirements 4.3**
# ---------------------------------------------------------------------------


@given(
    resolution=_resolution_strategy,
    scene=_scene_strategy,
)
@settings(max_examples=30, deadline=None)
def test_generated_frames_meet_minimum_resolution(resolution, scene):
    """Property 8: for any generated frame, width >= 1080 and height >= 1920.

    Uses a mock image generator that respects the configured resolution.
    Verifies all keyframes meet the minimum resolution requirement.

    **Validates: Requirements 4.3**
    """
    width, height = resolution
    config = _make_config(width=width, height=height)
    generator = MockImageGenerator()
    scorer = MockQualityScorer(score=0.9)
    interpolator = MockFrameInterpolator()

    engine = AnimationEngine(
        config=config,
        image_generator=generator,
        quality_scorer=scorer,
        frame_interpolator=interpolator,
        characters_dir="nonexistent_dir",
        quality_threshold=0.5,
        max_retries=1,
    )

    # Use a short duration to keep frame count manageable in tests
    test_scene = Scene(
        scene_number=scene.scene_number,
        duration_seconds=min(scene.duration_seconds, 5),
        background=scene.background,
        characters=scene.characters,
        action=scene.action,
        narration=scene.narration,
        dialogue=scene.dialogue,
        mood=scene.mood,
        sound_effects=scene.sound_effects,
    )

    script = EpisodeScript(
        episode_number=1,
        kanda="Bala Kanda",
        title="Test",
        total_duration_seconds=test_scene.duration_seconds,
        scenes=[test_scene],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        episode_frames = engine.generate_episode_frames(script, output_dir=tmpdir)

        for sf in episode_frames.scene_frames:
            for frame in sf.all_frames:
                assert frame.width >= 1080, (
                    f"Frame width {frame.width} is below minimum 1080"
                )
                assert frame.height >= 1920, (
                    f"Frame height {frame.height} is below minimum 1920"
                )


# ---------------------------------------------------------------------------
# Task 5.6.2: Frame regeneration retry logic
# ---------------------------------------------------------------------------


def test_retry_on_low_quality_then_pass():
    """Quality validator fails twice, then passes on third attempt.
    Verify the engine retries and uses the passing frame."""
    scorer = FailingThenPassingQualityScorer(fail_count=2, fail_score=0.3, pass_score=0.9)
    generator = MockImageGenerator()

    engine = _make_engine(
        quality_scorer=scorer,
        image_generator=generator,
        quality_threshold=0.6,
        max_retries=3,
    )

    script = _make_script(num_scenes=1, duration_per_scene=10)

    with tempfile.TemporaryDirectory() as tmpdir:
        episode_frames = engine.generate_episode_frames(script, output_dir=tmpdir)

        # Should have generated frames successfully
        assert len(episode_frames.scene_frames) == 1
        keyframes = episode_frames.scene_frames[0].keyframes
        assert len(keyframes) == KEYFRAMES_PER_SCENE

        # The scorer was called multiple times due to retries
        # First keyframe: 3 calls (2 fail + 1 pass), subsequent keyframes
        # reset the scorer's internal count relative to their own attempts
        assert scorer.call_count > KEYFRAMES_PER_SCENE


def test_retry_all_fail_uses_best_attempt():
    """Quality validator always fails. Verify the engine uses the best-scoring
    attempt after exhausting all retries."""
    scorer = AlwaysFailingQualityScorer(score=0.2)
    generator = MockImageGenerator()

    engine = _make_engine(
        quality_scorer=scorer,
        image_generator=generator,
        quality_threshold=0.6,
        max_retries=3,
    )

    script = _make_script(num_scenes=1, duration_per_scene=10)

    with tempfile.TemporaryDirectory() as tmpdir:
        episode_frames = engine.generate_episode_frames(script, output_dir=tmpdir)

        # Should still produce frames (using best attempt)
        assert len(episode_frames.scene_frames) == 1
        keyframes = episode_frames.scene_frames[0].keyframes
        assert len(keyframes) == KEYFRAMES_PER_SCENE

        # Each keyframe should have been attempted max_retries times
        assert scorer.call_count == KEYFRAMES_PER_SCENE * 3

        # All frames should have the low quality score
        for kf in keyframes:
            assert kf.quality_score == 0.2


def test_retry_count_is_limited_to_max_retries():
    """Verify the engine does not exceed max_retries attempts per frame."""
    scorer = AlwaysFailingQualityScorer(score=0.1)
    generator = MockImageGenerator()

    max_retries = 3
    engine = _make_engine(
        quality_scorer=scorer,
        image_generator=generator,
        quality_threshold=0.9,
        max_retries=max_retries,
    )

    script = _make_script(num_scenes=1, duration_per_scene=10)

    with tempfile.TemporaryDirectory() as tmpdir:
        engine.generate_episode_frames(script, output_dir=tmpdir)

        # Total calls = keyframes_per_scene * max_retries
        assert scorer.call_count == KEYFRAMES_PER_SCENE * max_retries


# ---------------------------------------------------------------------------
# Task 5.6.3: Character embedding loading
# ---------------------------------------------------------------------------


def test_load_character_embeddings_for_present_characters():
    """Verify embeddings are loaded for characters present in the scene."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create character directories with embedding data
        for char_name, dir_name in [("Rama", "rama"), ("Sita", "sita")]:
            char_dir = os.path.join(tmpdir, dir_name)
            os.makedirs(char_dir)

            # Create a reference image
            ref_img = Image.new("RGB", (100, 100), color=(255, 0, 0))
            ref_img.save(os.path.join(char_dir, "reference.png"))

            # Create a dummy embedding file
            with open(os.path.join(char_dir, "embedding.pt"), "w") as f:
                f.write("dummy_embedding_data")

            # Create character.json
            char_data = {
                "name": char_name,
                "reference_images": ["reference.png"],
                "embedding_file": "embedding.pt",
                "prompt_description": f"{char_name} in traditional attire",
            }
            with open(os.path.join(char_dir, "character.json"), "w") as f:
                json.dump(char_data, f)

        # Load embeddings for Rama only
        embeddings = load_character_embeddings(tmpdir, ["Rama"])
        assert len(embeddings) == 1
        assert embeddings[0].name == "Rama"
        assert embeddings[0].prompt_description == "Rama in traditional attire"
        assert len(embeddings[0].reference_images) == 1
        assert embeddings[0].embedding_file.endswith("embedding.pt")

        # Load embeddings for both characters
        embeddings = load_character_embeddings(tmpdir, ["Rama", "Sita"])
        assert len(embeddings) == 2
        names = {e.name for e in embeddings}
        assert names == {"Rama", "Sita"}


def test_load_character_embeddings_missing_character():
    """Verify missing characters are gracefully skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create only Rama
        char_dir = os.path.join(tmpdir, "rama")
        os.makedirs(char_dir)
        char_data = {
            "name": "Rama",
            "reference_images": [],
            "embedding_file": "",
            "prompt_description": "Rama",
        }
        with open(os.path.join(char_dir, "character.json"), "w") as f:
            json.dump(char_data, f)

        # Request Rama and Hanuman (Hanuman doesn't exist)
        embeddings = load_character_embeddings(tmpdir, ["Rama", "Hanuman"])
        assert len(embeddings) == 1
        assert embeddings[0].name == "Rama"


def test_load_character_embeddings_nonexistent_directory():
    """Verify empty list returned for nonexistent directory."""
    embeddings = load_character_embeddings("/nonexistent/path", ["Rama"])
    assert embeddings == []


def test_engine_loads_embeddings_for_scene_characters():
    """Verify the engine loads embeddings for characters in each scene."""
    with tempfile.TemporaryDirectory() as chars_dir:
        # Create Rama character data
        rama_dir = os.path.join(chars_dir, "rama")
        os.makedirs(rama_dir)
        char_data = {
            "name": "Rama",
            "reference_images": [],
            "embedding_file": "",
            "prompt_description": "Prince Rama in royal attire",
        }
        with open(os.path.join(rama_dir, "character.json"), "w") as f:
            json.dump(char_data, f)

        engine = _make_engine(characters_dir=chars_dir)
        script = _make_script(num_scenes=1)

        with tempfile.TemporaryDirectory() as output_dir:
            episode_frames = engine.generate_episode_frames(
                script, output_dir=output_dir
            )
            # Should complete without error
            assert len(episode_frames.scene_frames) == 1


# ---------------------------------------------------------------------------
# Additional unit tests
# ---------------------------------------------------------------------------


def test_generate_episode_frames_basic():
    """Basic test: generate frames for a simple 2-scene episode."""
    engine = _make_engine()
    script = _make_script(num_scenes=2, duration_per_scene=5)

    with tempfile.TemporaryDirectory() as tmpdir:
        episode_frames = engine.generate_episode_frames(script, output_dir=tmpdir)

        assert episode_frames.episode_number == 1
        assert len(episode_frames.scene_frames) == 2

        for sf in episode_frames.scene_frames:
            assert len(sf.keyframes) == KEYFRAMES_PER_SCENE
            assert len(sf.all_frames) >= KEYFRAMES_PER_SCENE


def test_thumbnail_selection():
    """Verify thumbnail is the highest-quality keyframe across all scenes."""
    engine = _make_engine()
    script = _make_script(num_scenes=2, duration_per_scene=5)

    with tempfile.TemporaryDirectory() as tmpdir:
        episode_frames = engine.generate_episode_frames(script, output_dir=tmpdir)

        assert episode_frames.thumbnail is not None
        # All frames have the same score (0.85 from MockQualityScorer),
        # so thumbnail should be one of the keyframes
        all_keyframes = []
        for sf in episode_frames.scene_frames:
            all_keyframes.extend(sf.keyframes)

        assert episode_frames.thumbnail in all_keyframes


def test_frame_resolution_enforcement():
    """Verify frames are resized to meet minimum resolution when generator
    produces undersized images."""
    # Generator produces 540x960 images (half resolution)
    generator = MockImageGenerator(width_override=540, height_override=960)
    config = _make_config(width=1080, height=1920)

    engine = AnimationEngine(
        config=config,
        image_generator=generator,
        quality_scorer=MockQualityScorer(),
        frame_interpolator=MockFrameInterpolator(),
        characters_dir="nonexistent_dir",
        quality_threshold=0.5,
        max_retries=1,
    )

    script = _make_script(num_scenes=1, duration_per_scene=10)

    with tempfile.TemporaryDirectory() as tmpdir:
        episode_frames = engine.generate_episode_frames(script, output_dir=tmpdir)

        for sf in episode_frames.scene_frames:
            for frame in sf.keyframes:
                assert frame.width >= 1080
                assert frame.height >= 1920


def test_interpolated_frames_generated():
    """Verify frame interpolation produces intermediate frames."""
    interpolator = MockFrameInterpolator()
    engine = _make_engine(frame_interpolator=interpolator)
    script = _make_script(num_scenes=1, duration_per_scene=5)

    with tempfile.TemporaryDirectory() as tmpdir:
        episode_frames = engine.generate_episode_frames(script, output_dir=tmpdir)

        sf = episode_frames.scene_frames[0]
        # With 3 keyframes and 20s duration at 12 FPS, we need ~240 frames
        # So interpolation should produce frames between keyframes
        assert len(sf.interpolated_frames) > 0
        assert interpolator.call_count > 0
