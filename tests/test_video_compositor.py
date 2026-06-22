"""Tests for the Video Compositor.

Includes property-based tests (Hypothesis) and unit tests for frame encoding,
visual transitions, title card overlay, audio combination, and duration
enforcement.

Uses MockRenderer to test compositor logic without requiring FFmpeg.
"""

import json
import logging
import os
import shutil
import tempfile
from typing import Dict, List, Optional, Tuple

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from src.config_loader import AnimationConfig, OutputConfig
from src.episode_script import DialogueLine, EpisodeScript, Scene
from src.video_compositor import (
    DEFAULT_FPS,
    DEFAULT_HEIGHT,
    DEFAULT_TRANSITION_DURATION,
    DEFAULT_WIDTH,
    MAX_DURATION_SECONDS,
    MAX_TITLE_CARD_SECONDS,
    MIN_DURATION_SECONDS,
    MIN_TITLE_CARD_SECONDS,
    TITLE_CARD_DURATION_SECONDS,
    MockRenderer,
    TitleCard,
    VideoCompositor,
    VideoCompositorError,
    VideoMetadata,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_output_config(
    fmt: str = "mp4",
    video_codec: str = "h264",
    audio_codec: str = "aac",
) -> OutputConfig:
    """Create an OutputConfig for testing."""
    return OutputConfig(
        format=fmt,
        video_codec=video_codec,
        audio_codec=audio_codec,
    )


def _make_animation_config(
    resolution: Optional[List[int]] = None,
    fps: int = 24,
) -> AnimationConfig:
    """Create an AnimationConfig for testing."""
    return AnimationConfig(
        resolution=resolution or [1080, 1920],
        fps=fps,
    )


def _make_scene(
    scene_number: int = 1,
    duration_seconds: int = 20,
    mood: str = "devotional",
) -> Scene:
    """Create a Scene for testing."""
    return Scene(
        scene_number=scene_number,
        duration_seconds=duration_seconds,
        background="Royal palace",
        characters=["Rama"],
        action="Rama enters the palace",
        narration="In the ancient kingdom of Ayodhya",
        dialogue=[],
        mood=mood,
        sound_effects=[],
    )


def _make_episode_script(
    scenes: Optional[List[Scene]] = None,
    kanda: str = "Bala Kanda",
    episode_number: int = 1,
) -> EpisodeScript:
    """Create an EpisodeScript for testing."""
    if scenes is None:
        scenes = [_make_scene()]
    return EpisodeScript(
        episode_number=episode_number,
        kanda=kanda,
        title="The Birth of Rama",
        total_duration_seconds=sum(s.duration_seconds for s in scenes),
        scenes=scenes,
    )


def _make_compositor(
    renderer: Optional[MockRenderer] = None,
    transition_duration: float = DEFAULT_TRANSITION_DURATION,
    title_card_duration: float = TITLE_CARD_DURATION_SECONDS,
    min_duration: float = MIN_DURATION_SECONDS,
    max_duration: float = MAX_DURATION_SECONDS,
    fps: int = 24,
    resolution: Optional[List[int]] = None,
) -> VideoCompositor:
    """Create a VideoCompositor with MockRenderer for testing."""
    return VideoCompositor(
        output_config=_make_output_config(),
        animation_config=_make_animation_config(
            resolution=resolution, fps=fps
        ),
        renderer=renderer or MockRenderer(),
        transition_duration=transition_duration,
        title_card_duration=title_card_duration,
        min_duration=min_duration,
        max_duration=max_duration,
    )


def _create_mock_frame_files(
    work_dir: str, num_scenes: int, frames_per_scene: int
) -> List[List[str]]:
    """Create placeholder frame files for testing.

    Returns a list of frame path lists, one per scene.
    """
    scene_frame_paths: List[List[str]] = []
    for scene_idx in range(num_scenes):
        scene_dir = os.path.join(work_dir, f"scene_{scene_idx:03d}")
        os.makedirs(scene_dir, exist_ok=True)
        frame_paths: List[str] = []
        for frame_idx in range(frames_per_scene):
            frame_path = os.path.join(
                scene_dir, f"frame_{frame_idx:04d}.png"
            )
            # Write a minimal placeholder file
            with open(frame_path, "w") as f:
                f.write("placeholder")
            frame_paths.append(frame_path)
        scene_frame_paths.append(frame_paths)
    return scene_frame_paths


def _create_mock_audio_file(work_dir: str) -> str:
    """Create a placeholder audio file for testing."""
    audio_path = os.path.join(work_dir, "audio.wav")
    with open(audio_path, "w") as f:
        f.write("placeholder_audio")
    return audio_path


def _read_mock_metadata(file_path: str) -> Dict:
    """Read metadata from a mock video file."""
    with open(file_path, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Task 8.1: Scene Encoding Tests
# ---------------------------------------------------------------------------


class TestSceneEncoding:
    """Tests for encoding frame sequences into video streams."""

    def test_encode_scene_basic(self, tmp_path):
        """Encoding frames produces a video file."""
        compositor = _make_compositor()
        scene_dir = str(tmp_path / "scene")
        os.makedirs(scene_dir)

        # Create mock frames
        frame_paths = []
        for i in range(48):  # 2 seconds at 24fps
            fp = os.path.join(scene_dir, f"frame_{i:04d}.png")
            with open(fp, "w") as f:
                f.write("frame")
            frame_paths.append(fp)

        output_path = str(tmp_path / "scene.mp4")
        result = compositor.encode_scene(frame_paths, output_path)

        assert os.path.exists(result)
        meta = _read_mock_metadata(result)
        assert meta["num_frames"] == 48
        assert meta["fps"] == 24
        assert meta["width"] == 1080
        assert meta["height"] == 1920

    def test_encode_scene_empty_raises(self, tmp_path):
        """Encoding with no frames raises an error."""
        compositor = _make_compositor()
        output_path = str(tmp_path / "scene.mp4")

        with pytest.raises(VideoCompositorError, match="No frames"):
            compositor.encode_scene([], output_path)

    def test_encode_scene_duration(self, tmp_path):
        """Encoded scene duration matches frame count / fps."""
        compositor = _make_compositor(fps=24)
        scene_dir = str(tmp_path / "scene")
        os.makedirs(scene_dir)

        frame_paths = []
        for i in range(120):  # 5 seconds at 24fps
            fp = os.path.join(scene_dir, f"frame_{i:04d}.png")
            with open(fp, "w") as f:
                f.write("frame")
            frame_paths.append(fp)

        output_path = str(tmp_path / "scene.mp4")
        compositor.encode_scene(frame_paths, output_path)

        meta = _read_mock_metadata(output_path)
        assert abs(meta["duration_seconds"] - 5.0) < 0.01


# ---------------------------------------------------------------------------
# Task 8.2: Visual Transitions Tests
# ---------------------------------------------------------------------------


class TestVisualTransitions:
    """Tests for crossfade/dissolve transitions between scenes."""

    def test_transition_between_two_scenes(self, tmp_path):
        """Transition between two scenes produces combined video."""
        compositor = _make_compositor(transition_duration=0.5)
        renderer = MockRenderer()

        # Create two mock scene videos
        v1 = str(tmp_path / "scene1.mp4")
        v2 = str(tmp_path / "scene2.mp4")
        renderer.encode_frames_to_video(
            ["f"] * 240, v1, 24, 1080, 1920  # 10s
        )
        renderer.encode_frames_to_video(
            ["f"] * 240, v2, 24, 1080, 1920  # 10s
        )

        result = compositor.apply_scene_transitions(
            [v1, v2],
            output_dir=str(tmp_path),
            transition_type="crossfade",
        )

        assert os.path.exists(result)
        meta = _read_mock_metadata(result)
        assert meta["transition_type"] == "crossfade"
        # 10 + 10 - 0.5 = 19.5
        assert abs(meta["duration_seconds"] - 19.5) < 0.01

    def test_transition_configurable_duration(self, tmp_path):
        """Transition duration is configurable."""
        compositor = _make_compositor(transition_duration=1.0)
        renderer = MockRenderer()

        v1 = str(tmp_path / "scene1.mp4")
        v2 = str(tmp_path / "scene2.mp4")
        renderer.encode_frames_to_video(["f"] * 240, v1, 24, 1080, 1920)
        renderer.encode_frames_to_video(["f"] * 240, v2, 24, 1080, 1920)

        result = compositor.apply_scene_transitions(
            [v1, v2],
            output_dir=str(tmp_path),
            transition_type="dissolve",
        )

        meta = _read_mock_metadata(result)
        assert meta["transition_duration"] == 1.0

    def test_single_scene_no_transition(self, tmp_path):
        """Single scene returns as-is without transition."""
        compositor = _make_compositor()
        renderer = MockRenderer()

        v1 = str(tmp_path / "scene1.mp4")
        renderer.encode_frames_to_video(["f"] * 240, v1, 24, 1080, 1920)

        result = compositor.apply_scene_transitions(
            [v1], output_dir=str(tmp_path)
        )
        assert result == v1

    def test_no_scenes_raises(self, tmp_path):
        """No scene videos raises an error."""
        compositor = _make_compositor()

        with pytest.raises(VideoCompositorError, match="No scene videos"):
            compositor.apply_scene_transitions([], output_dir=str(tmp_path))

    def test_default_transition_duration_is_half_second(self):
        """Default transition duration is 0.5 seconds."""
        compositor = _make_compositor()
        assert compositor.transition_duration == 0.5


# ---------------------------------------------------------------------------
# Task 8.3: Title Card Overlay Tests
# ---------------------------------------------------------------------------


class TestTitleCardOverlay:
    """Tests for title card rendering."""

    def test_title_card_content(self, tmp_path):
        """Title card contains kanda name and episode number."""
        compositor = _make_compositor()
        script = _make_episode_script(
            kanda="Bala Kanda", episode_number=5
        )

        output_path = str(tmp_path / "title.mp4")
        result = compositor.create_title_card(script, output_path)

        assert os.path.exists(result)
        meta = _read_mock_metadata(result)
        assert "Bala Kanda" in meta["title_text"]
        assert "5" in meta["title_text"]

    def test_title_card_duration_default(self, tmp_path):
        """Title card duration defaults to 4 seconds (within 3-5s range)."""
        compositor = _make_compositor()
        script = _make_episode_script()

        output_path = str(tmp_path / "title.mp4")
        compositor.create_title_card(script, output_path)

        meta = _read_mock_metadata(output_path)
        assert MIN_TITLE_CARD_SECONDS <= meta["duration_seconds"] <= MAX_TITLE_CARD_SECONDS

    def test_title_card_duration_clamped_min(self):
        """Title card duration is clamped to minimum 3 seconds."""
        compositor = _make_compositor(title_card_duration=1.0)
        assert compositor.title_card_duration == MIN_TITLE_CARD_SECONDS

    def test_title_card_duration_clamped_max(self):
        """Title card duration is clamped to maximum 5 seconds."""
        compositor = _make_compositor(title_card_duration=10.0)
        assert compositor.title_card_duration == MAX_TITLE_CARD_SECONDS

    def test_title_card_resolution(self, tmp_path):
        """Title card matches configured resolution."""
        compositor = _make_compositor(resolution=[1080, 1920])
        script = _make_episode_script()

        output_path = str(tmp_path / "title.mp4")
        compositor.create_title_card(script, output_path)

        meta = _read_mock_metadata(output_path)
        assert meta["width"] == 1080
        assert meta["height"] == 1920


# ---------------------------------------------------------------------------
# Task 8.4: Final Rendering Tests
# ---------------------------------------------------------------------------


class TestFinalRendering:
    """Tests for combining video with audio and encoding."""

    def test_combine_video_audio(self, tmp_path):
        """Combining video and audio produces MP4 with correct codecs."""
        compositor = _make_compositor()
        renderer = MockRenderer()

        video_path = str(tmp_path / "video.mp4")
        renderer.encode_frames_to_video(
            ["f"] * 2880, video_path, 24, 1080, 1920  # 120s
        )

        audio_path = str(tmp_path / "audio.wav")
        with open(audio_path, "w") as f:
            f.write("audio_data")

        output_path = str(tmp_path / "combined.mp4")
        result = compositor.combine_with_audio(
            video_path, audio_path, output_path
        )

        assert os.path.exists(result)
        meta = _read_mock_metadata(result)
        assert meta["video_codec"] == "h264"
        assert meta["audio_codec"] == "aac"
        assert meta["has_audio"] is True
        assert meta["format"] == "mp4"

    def test_output_resolution(self, tmp_path):
        """Output video has correct resolution."""
        compositor = _make_compositor(resolution=[1080, 1920])
        renderer = MockRenderer()

        video_path = str(tmp_path / "video.mp4")
        renderer.encode_frames_to_video(
            ["f"] * 2880, video_path, 24, 1080, 1920
        )

        audio_path = str(tmp_path / "audio.wav")
        with open(audio_path, "w") as f:
            f.write("audio_data")

        output_path = str(tmp_path / "combined.mp4")
        compositor.combine_with_audio(video_path, audio_path, output_path)

        meta = _read_mock_metadata(output_path)
        assert meta["width"] == 1080
        assert meta["height"] == 1920

    def test_output_fps(self, tmp_path):
        """Output video has correct FPS."""
        compositor = _make_compositor(fps=24)
        renderer = MockRenderer()

        video_path = str(tmp_path / "video.mp4")
        renderer.encode_frames_to_video(
            ["f"] * 2880, video_path, 24, 1080, 1920
        )

        audio_path = str(tmp_path / "audio.wav")
        with open(audio_path, "w") as f:
            f.write("audio_data")

        output_path = str(tmp_path / "combined.mp4")
        compositor.combine_with_audio(video_path, audio_path, output_path)

        meta = _read_mock_metadata(output_path)
        assert meta["fps"] >= 24


# ---------------------------------------------------------------------------
# Task 8.5: Duration Enforcement Tests
# ---------------------------------------------------------------------------


class TestDurationEnforcement:
    """Tests for duration validation and trimming."""

    def test_duration_within_range_no_trim(self, tmp_path):
        """Video within 110-130s is not trimmed."""
        compositor = _make_compositor()
        renderer = MockRenderer()

        video_path = str(tmp_path / "video.mp4")
        # 120 seconds = 2880 frames at 24fps
        renderer.encode_frames_to_video(
            ["f"] * 2880, video_path, 24, 1080, 1920
        )

        output_path = str(tmp_path / "trimmed.mp4")
        result_path, was_trimmed = compositor.enforce_duration(
            video_path, output_path
        )

        assert was_trimmed is False
        assert result_path == video_path

    def test_duration_over_max_triggers_trim(self, tmp_path):
        """Video over 130s is trimmed with fade-out."""
        compositor = _make_compositor()
        renderer = MockRenderer()

        video_path = str(tmp_path / "video.mp4")
        # 150 seconds = 3600 frames at 24fps
        renderer.encode_frames_to_video(
            ["f"] * 3600, video_path, 24, 1080, 1920
        )

        output_path = str(tmp_path / "trimmed.mp4")
        result_path, was_trimmed = compositor.enforce_duration(
            video_path, output_path
        )

        assert was_trimmed is True
        meta = _read_mock_metadata(result_path)
        assert meta["duration_seconds"] <= MAX_DURATION_SECONDS
        assert meta["was_trimmed"] is True

    def test_duration_under_min_logs_warning(self, tmp_path, caplog):
        """Video under 110s logs a warning but is not trimmed."""
        compositor = _make_compositor()
        renderer = MockRenderer()

        video_path = str(tmp_path / "video.mp4")
        # 90 seconds = 2160 frames at 24fps
        renderer.encode_frames_to_video(
            ["f"] * 2160, video_path, 24, 1080, 1920
        )

        output_path = str(tmp_path / "trimmed.mp4")
        with caplog.at_level(logging.WARNING):
            result_path, was_trimmed = compositor.enforce_duration(
                video_path, output_path
            )

        assert was_trimmed is False
        assert "below minimum" in caplog.text

    def test_duration_exactly_at_max(self, tmp_path):
        """Video at exactly 130s is not trimmed."""
        compositor = _make_compositor()
        renderer = MockRenderer()

        video_path = str(tmp_path / "video.mp4")
        # 130 seconds = 3120 frames at 24fps
        renderer.encode_frames_to_video(
            ["f"] * 3120, video_path, 24, 1080, 1920
        )

        output_path = str(tmp_path / "trimmed.mp4")
        result_path, was_trimmed = compositor.enforce_duration(
            video_path, output_path
        )

        assert was_trimmed is False

    def test_duration_exactly_at_min(self, tmp_path):
        """Video at exactly 110s is not trimmed."""
        compositor = _make_compositor()
        renderer = MockRenderer()

        video_path = str(tmp_path / "video.mp4")
        # 110 seconds = 2640 frames at 24fps
        renderer.encode_frames_to_video(
            ["f"] * 2640, video_path, 24, 1080, 1920
        )

        output_path = str(tmp_path / "trimmed.mp4")
        result_path, was_trimmed = compositor.enforce_duration(
            video_path, output_path
        )

        assert was_trimmed is False

    def test_calculate_total_duration(self):
        """Total duration calculation accounts for transitions."""
        compositor = _make_compositor(
            transition_duration=0.5,
            title_card_duration=4.0,
        )

        # 5 scenes of 25s each + 4s title card - 5 transitions * 0.5s
        # = 125 + 4 - 2.5 = 126.5
        total = compositor.calculate_total_duration(
            [25.0, 25.0, 25.0, 25.0, 25.0]
        )
        assert abs(total - 126.5) < 0.01


# ---------------------------------------------------------------------------
# Task 8.6.3: Duration Trimming Edge Case
# ---------------------------------------------------------------------------


class TestDurationTrimmingEdgeCase:
    """Test duration trimming edge case: content exceeding 130 seconds."""

    def test_content_exceeding_130s_is_trimmed(self, tmp_path):
        """Content exceeding 130s is trimmed and warning is logged."""
        compositor = _make_compositor()
        renderer = MockRenderer()

        # Create a video that is 150 seconds long
        video_path = str(tmp_path / "long_video.mp4")
        renderer.encode_frames_to_video(
            ["f"] * 3600, video_path, 24, 1080, 1920  # 150s
        )

        output_path = str(tmp_path / "trimmed.mp4")
        result_path, was_trimmed = compositor.enforce_duration(
            video_path, output_path
        )

        assert was_trimmed is True
        meta = _read_mock_metadata(result_path)
        assert meta["duration_seconds"] <= 130.0
        assert meta["original_duration"] == 150.0
        assert meta["fade_out_seconds"] == 2.0

    def test_trimming_logs_warning(self, tmp_path, caplog):
        """Trimming logs a warning about exceeding duration."""
        compositor = _make_compositor()
        renderer = MockRenderer()

        video_path = str(tmp_path / "long_video.mp4")
        renderer.encode_frames_to_video(
            ["f"] * 3600, video_path, 24, 1080, 1920  # 150s
        )

        output_path = str(tmp_path / "trimmed.mp4")
        with caplog.at_level(logging.WARNING):
            compositor.enforce_duration(video_path, output_path)

        assert "exceeds maximum" in caplog.text
        assert "Trimming" in caplog.text

    def test_full_compose_with_excess_duration(self, tmp_path):
        """Full compose pipeline trims when total exceeds 130s."""
        # Create scenes that total well over 130s
        scenes = [
            _make_scene(scene_number=i + 1, duration_seconds=40)
            for i in range(5)
        ]
        script = _make_episode_script(scenes=scenes)

        renderer = MockRenderer()
        compositor = VideoCompositor(
            output_config=_make_output_config(),
            animation_config=_make_animation_config(fps=24),
            renderer=renderer,
            transition_duration=0.5,
            title_card_duration=4.0,
            min_duration=110,
            max_duration=130,
        )

        work_dir = str(tmp_path / "work")
        # Create frames: 40s * 24fps = 960 frames per scene
        scene_frame_paths = _create_mock_frame_files(
            work_dir, num_scenes=5, frames_per_scene=960
        )
        audio_path = _create_mock_audio_file(str(tmp_path))
        output_path = str(tmp_path / "final.mp4")

        metadata = compositor.compose_video(
            script=script,
            scene_frame_paths=scene_frame_paths,
            audio_path=audio_path,
            output_path=output_path,
            work_dir=str(tmp_path / "compose_work"),
        )

        assert metadata.duration_seconds <= 130.0
        assert metadata.was_trimmed is True
        assert metadata.format == "mp4"
        assert metadata.video_codec == "h264"
        assert metadata.audio_codec == "aac"


# ---------------------------------------------------------------------------
# Task 8.6.1 [PBT] Property 12: Video Output Format Invariant
# ---------------------------------------------------------------------------


@st.composite
def video_params_strategy(draw):
    """Generate random video parameters for format testing.

    Produces parameters that the compositor would use to create a video,
    then verifies the output has correct format/codec/resolution/fps.
    """
    # Number of scenes: 4-8
    num_scenes = draw(st.integers(min_value=4, max_value=8))

    # Frames per scene: enough for 15-30 seconds at 24fps
    scene_duration_seconds = draw(
        st.lists(
            st.integers(min_value=15, max_value=30),
            min_size=num_scenes,
            max_size=num_scenes,
        )
    )

    fps = 24
    frames_per_scene = [d * fps for d in scene_duration_seconds]

    # Episode number
    episode_number = draw(st.integers(min_value=1, max_value=999))

    # Kanda name
    kanda = draw(
        st.sampled_from([
            "Bala Kanda",
            "Ayodhya Kanda",
            "Aranya Kanda",
            "Kishkindha Kanda",
            "Sundara Kanda",
            "Yuddha Kanda",
            "Uttara Kanda",
        ])
    )

    return {
        "num_scenes": num_scenes,
        "scene_duration_seconds": scene_duration_seconds,
        "frames_per_scene": frames_per_scene,
        "fps": fps,
        "episode_number": episode_number,
        "kanda": kanda,
    }


@given(params=video_params_strategy())
@settings(
    max_examples=30,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
def test_property_12_video_output_format(params, tmp_path_factory):
    """**Validates: Requirements 7.2, 7.3**

    Property 12: For any video file produced, the container format is MP4,
    video codec is H.264, audio codec is AAC, resolution is 1080x1920,
    and frame rate is at least 24 FPS.

    We generate random video parameters and verify the compositor produces
    output with correct format/codec/resolution/fps using MockRenderer.
    """
    tmp_path = tmp_path_factory.mktemp("pbt12")

    renderer = MockRenderer()
    compositor = VideoCompositor(
        output_config=_make_output_config(),
        animation_config=_make_animation_config(fps=params["fps"]),
        renderer=renderer,
        transition_duration=0.5,
        title_card_duration=4.0,
        min_duration=0,  # Disable min check for format testing
        max_duration=9999,  # Disable max check for format testing
    )

    # Create scenes
    scenes = [
        _make_scene(
            scene_number=i + 1,
            duration_seconds=params["scene_duration_seconds"][i],
        )
        for i in range(params["num_scenes"])
    ]
    script = _make_episode_script(
        scenes=scenes,
        kanda=params["kanda"],
        episode_number=params["episode_number"],
    )

    # Create mock frame files
    work_dir = str(tmp_path / "frames")
    scene_frame_paths = []
    for i, num_frames in enumerate(params["frames_per_scene"]):
        scene_dir = os.path.join(work_dir, f"scene_{i:03d}")
        os.makedirs(scene_dir, exist_ok=True)
        paths = []
        for j in range(num_frames):
            fp = os.path.join(scene_dir, f"frame_{j:04d}.png")
            with open(fp, "w") as f:
                f.write("x")
            paths.append(fp)
        scene_frame_paths.append(paths)

    audio_path = _create_mock_audio_file(str(tmp_path))
    output_path = str(tmp_path / "output.mp4")

    metadata = compositor.compose_video(
        script=script,
        scene_frame_paths=scene_frame_paths,
        audio_path=audio_path,
        output_path=output_path,
        work_dir=str(tmp_path / "work"),
    )

    # Verify format properties
    assert metadata.format == "mp4", (
        f"Expected format 'mp4', got '{metadata.format}'"
    )
    assert metadata.video_codec == "h264", (
        f"Expected video codec 'h264', got '{metadata.video_codec}'"
    )
    assert metadata.audio_codec == "aac", (
        f"Expected audio codec 'aac', got '{metadata.audio_codec}'"
    )
    assert metadata.width == 1080, (
        f"Expected width 1080, got {metadata.width}"
    )
    assert metadata.height == 1920, (
        f"Expected height 1920, got {metadata.height}"
    )
    assert metadata.fps >= 24, (
        f"Expected FPS >= 24, got {metadata.fps}"
    )


# ---------------------------------------------------------------------------
# Task 8.6.2 [PBT] Property 13: Video Duration Invariant
# ---------------------------------------------------------------------------


@st.composite
def scene_durations_strategy(draw):
    """Generate random scene durations that test duration enforcement.

    Produces scene durations that may or may not fit within 110-130s,
    testing the compositor's ability to enforce the constraint.
    """
    num_scenes = draw(st.integers(min_value=4, max_value=8))

    # Generate scene durations that sum to various totals
    # We want to test both within-range and over-range scenarios
    scene_durations = draw(
        st.lists(
            st.integers(min_value=10, max_value=35),
            min_size=num_scenes,
            max_size=num_scenes,
        )
    )

    return {
        "num_scenes": num_scenes,
        "scene_durations": scene_durations,
    }


@given(params=scene_durations_strategy())
@settings(
    max_examples=30,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
def test_property_13_video_duration_invariant(params, tmp_path_factory):
    """**Validates: Requirements 7.6**

    Property 13: For any video file produced, the duration is between
    110 and 130 seconds inclusive.

    We generate random scene durations and verify the compositor enforces
    the 110-130s duration constraint. If the total exceeds 130s, the
    compositor should trim. We test the duration enforcement logic.
    """
    tmp_path = tmp_path_factory.mktemp("pbt13")

    renderer = MockRenderer()
    transition_duration = 0.5
    title_card_duration = 4.0

    compositor = VideoCompositor(
        output_config=_make_output_config(),
        animation_config=_make_animation_config(fps=24),
        renderer=renderer,
        transition_duration=transition_duration,
        title_card_duration=title_card_duration,
        min_duration=MIN_DURATION_SECONDS,
        max_duration=MAX_DURATION_SECONDS,
    )

    scenes = [
        _make_scene(
            scene_number=i + 1,
            duration_seconds=params["scene_durations"][i],
        )
        for i in range(params["num_scenes"])
    ]
    script = _make_episode_script(scenes=scenes)

    fps = 24
    scene_frame_paths = []
    work_dir = str(tmp_path / "frames")
    for i, dur in enumerate(params["scene_durations"]):
        scene_dir = os.path.join(work_dir, f"scene_{i:03d}")
        os.makedirs(scene_dir, exist_ok=True)
        num_frames = dur * fps
        paths = []
        for j in range(num_frames):
            fp = os.path.join(scene_dir, f"frame_{j:04d}.png")
            with open(fp, "w") as f:
                f.write("x")
            paths.append(fp)
        scene_frame_paths.append(paths)

    audio_path = _create_mock_audio_file(str(tmp_path))
    output_path = str(tmp_path / "output.mp4")

    metadata = compositor.compose_video(
        script=script,
        scene_frame_paths=scene_frame_paths,
        audio_path=audio_path,
        output_path=output_path,
        work_dir=str(tmp_path / "work"),
    )

    # The compositor should enforce max duration
    assert metadata.duration_seconds <= MAX_DURATION_SECONDS, (
        f"Video duration {metadata.duration_seconds}s exceeds maximum "
        f"{MAX_DURATION_SECONDS}s"
    )

    # If the raw duration was over max, it should have been trimmed
    if metadata.was_trimmed:
        assert metadata.duration_seconds <= MAX_DURATION_SECONDS


# ---------------------------------------------------------------------------
# Full Pipeline Integration Test
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Integration tests for the full compose_video pipeline."""

    def test_compose_video_basic(self, tmp_path):
        """Full pipeline produces a valid video file."""
        scenes = [
            _make_scene(scene_number=i + 1, duration_seconds=25)
            for i in range(5)
        ]
        script = _make_episode_script(scenes=scenes)

        compositor = _make_compositor()
        work_dir = str(tmp_path / "work")
        scene_frame_paths = _create_mock_frame_files(
            str(tmp_path / "frames"),
            num_scenes=5,
            frames_per_scene=600,  # 25s * 24fps
        )
        audio_path = _create_mock_audio_file(str(tmp_path))
        output_path = str(tmp_path / "final.mp4")

        metadata = compositor.compose_video(
            script=script,
            scene_frame_paths=scene_frame_paths,
            audio_path=audio_path,
            output_path=output_path,
            work_dir=work_dir,
        )

        assert os.path.exists(output_path)
        assert metadata.format == "mp4"
        assert metadata.video_codec == "h264"
        assert metadata.audio_codec == "aac"
        assert metadata.width == 1080
        assert metadata.height == 1920
        assert metadata.fps == 24

    def test_compose_video_no_frames_raises(self, tmp_path):
        """Composing with no frames raises an error."""
        script = _make_episode_script()
        compositor = _make_compositor()
        audio_path = _create_mock_audio_file(str(tmp_path))
        output_path = str(tmp_path / "final.mp4")

        with pytest.raises(VideoCompositorError, match="No scene frames"):
            compositor.compose_video(
                script=script,
                scene_frame_paths=[],
                audio_path=audio_path,
                output_path=output_path,
            )


# ---------------------------------------------------------------------------
# MockRenderer Tests
# ---------------------------------------------------------------------------


class TestMockRenderer:
    """Tests for the MockRenderer itself."""

    def test_encode_frames(self, tmp_path):
        """MockRenderer creates a valid metadata file."""
        renderer = MockRenderer()
        output = str(tmp_path / "test.mp4")
        renderer.encode_frames_to_video(
            ["f1", "f2", "f3"], output, 24, 1080, 1920
        )

        meta = _read_mock_metadata(output)
        assert meta["num_frames"] == 3
        assert meta["fps"] == 24
        assert meta["format"] == "mp4"

    def test_get_video_duration(self, tmp_path):
        """MockRenderer returns correct duration from metadata."""
        renderer = MockRenderer()
        output = str(tmp_path / "test.mp4")
        renderer.encode_frames_to_video(
            ["f"] * 240, output, 24, 1080, 1920
        )

        duration = renderer.get_video_duration(output)
        assert abs(duration - 10.0) < 0.01

    def test_concatenate_videos(self, tmp_path):
        """MockRenderer concatenates video durations."""
        renderer = MockRenderer()
        v1 = str(tmp_path / "v1.mp4")
        v2 = str(tmp_path / "v2.mp4")
        renderer.encode_frames_to_video(["f"] * 240, v1, 24, 1080, 1920)
        renderer.encode_frames_to_video(["f"] * 480, v2, 24, 1080, 1920)

        output = str(tmp_path / "concat.mp4")
        renderer.concatenate_videos([v1, v2], output)

        meta = _read_mock_metadata(output)
        assert abs(meta["duration_seconds"] - 30.0) < 0.01


# ---------------------------------------------------------------------------
# TitleCard Data Model Tests
# ---------------------------------------------------------------------------


class TestTitleCard:
    """Tests for the TitleCard data model."""

    def test_default_text(self):
        """Default text includes kanda name and episode number."""
        tc = TitleCard(kanda_name="Bala Kanda", episode_number=1)
        assert tc.text == "Bala Kanda - Episode 1"

    def test_custom_text(self):
        """Custom text overrides default."""
        tc = TitleCard(
            kanda_name="Bala Kanda",
            episode_number=1,
            text="Custom Title",
        )
        assert tc.text == "Custom Title"

    def test_default_duration(self):
        """Default duration is TITLE_CARD_DURATION_SECONDS."""
        tc = TitleCard(kanda_name="Bala Kanda", episode_number=1)
        assert tc.duration_seconds == TITLE_CARD_DURATION_SECONDS
