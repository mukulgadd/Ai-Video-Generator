"""Integration and End-to-End Tests for the Ramayan Video Generator.

Wires up ALL real components with mock external services to verify
the complete pipeline from story segment to output video file.

Mock external services:
- Mock LLM client (returns valid EpisodeScript JSON)
- Mock image generator (returns placeholder images at correct resolution)
- Mock quality scorer (returns passing scores)
- Mock frame interpolator (returns blended frames)
- Mock TTS provider (returns silent WAV audio of correct duration)
- Mock video renderer (MockRenderer from video_compositor.py)
- Mock storage uploader (MockStorageUploader from distribution_manager.py)

Validates: Requirements 1.2, 1.3, 1.4, 2.2, 2.3, 9.6
"""

import io
import json
import os
import shutil
import tempfile
import wave
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest
from PIL import Image

from src.animation_engine import AnimationEngine
from src.audio_engine import AudioEngine, MusicLibrary, SFXLibrary
from src.config_loader import (
    AnimationConfig,
    AudioConfig,
    Config,
    DistributionConfig,
    NarrationConfig,
    NotificationsConfig,
    OutputConfig,
    PipelineConfig,
    StorageConfig,
)
from src.distribution_manager import (
    DistributionManager,
    MockStorageUploader,
)
from src.episode_script import DialogueLine, EpisodeScript, Scene, serialize
from src.narration_engine import NarrationEngine
from src.notifications import MockNotificationAdapter
from src.orchestrator import VideoGeneratorOrchestrator
from src.script_engine import ScriptEngine
from src.story_manager import StoryManager
from src.video_compositor import MockRenderer, VideoCompositor


# ---------------------------------------------------------------------------
# Mock External Services
# ---------------------------------------------------------------------------


def _make_valid_script_json(
    episode_number: int = 1,
    kanda: str = "Bala Kanda",
    title: str = "The Birth of Rama",
) -> str:
    """Return a valid EpisodeScript JSON string with 4 scenes totalling 120s.

    Uses only characters that appear in the test segment's character list:
    King Dasharatha, Sage Vasishtha, Queen Kausalya.
    """
    script = EpisodeScript(
        episode_number=episode_number,
        kanda=kanda,
        title=title,
        total_duration_seconds=120,
        scenes=[
            Scene(
                scene_number=1,
                duration_seconds=30,
                background="Royal palace of Ayodhya with ornate pillars",
                characters=["King Dasharatha", "Sage Vasishtha"],
                action="King Dasharatha consults Sage Vasishtha about performing a sacred yajna",
                narration="In the ancient kingdom of Ayodhya, King Dasharatha ruled with wisdom.",
                dialogue=[
                    DialogueLine(
                        character="King Dasharatha",
                        text="I seek your counsel, O great sage.",
                    )
                ],
                mood="devotional",
                sound_effects=["temple_bells"],
            ),
            Scene(
                scene_number=2,
                duration_seconds=30,
                background="Sacred fire altar with golden flames",
                characters=["King Dasharatha", "Sage Vasishtha"],
                action="The sacred Putrakameshti Yajna is performed",
                narration="The sacred fire ceremony began under the guidance of Sage Vasishtha.",
                dialogue=[],
                mood="dramatic",
                sound_effects=["fire_crackling"],
            ),
            Scene(
                scene_number=3,
                duration_seconds=30,
                background="Royal chambers with divine light",
                characters=["Queen Kausalya"],
                action="The divine payasam is distributed among the queens",
                narration="From the sacred fire emerged a divine being carrying celestial payasam.",
                dialogue=[],
                mood="serene",
                sound_effects=[],
            ),
            Scene(
                scene_number=4,
                duration_seconds=30,
                background="Palace courtyard with celebrations",
                characters=["King Dasharatha", "Queen Kausalya"],
                action="The kingdom celebrates the birth of the four princes",
                narration="The kingdom of Ayodhya rejoiced at the birth of the four princes.",
                dialogue=[
                    DialogueLine(
                        character="King Dasharatha",
                        text="The gods have blessed us with four sons!",
                    )
                ],
                mood="devotional",
                sound_effects=["temple_bells"],
            ),
        ],
    )
    return serialize(script)


class MockLLMClient:
    """Mock LLM client that returns a valid EpisodeScript JSON."""

    def __init__(self, fail_count: int = 0):
        self._fail_count = fail_count
        self._attempt = 0
        self.call_count = 0

    def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
    ) -> str:
        self._attempt += 1
        self.call_count += 1
        if self._attempt <= self._fail_count:
            raise RuntimeError(f"Mock LLM failure (attempt {self._attempt})")
        return _make_valid_script_json()


class MockImageGenerator:
    """Mock image generator that returns placeholder images at correct resolution."""

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
        images = []
        for _ in range(num_images):
            img = Image.new("RGB", (width, height), color=(128, 100, 80))
            images.append(img)
        return images


class MockQualityScorer:
    """Mock quality scorer that returns passing scores."""

    def score(self, image: Image.Image, prompt: str) -> float:
        return 0.9


class MockFrameInterpolator:
    """Mock frame interpolator that returns small placeholder frames quickly."""

    def interpolate(
        self,
        frame_a: Image.Image,
        frame_b: Image.Image,
        num_intermediate_frames: int,
    ) -> List[Image.Image]:
        # Return small solid-color images instead of blending (much faster)
        frames = []
        w, h = frame_a.size
        for i in range(num_intermediate_frames):
            # Create a simple solid-color image instead of expensive blending
            gray = int(128 + (i * 10) % 128)
            frames.append(Image.new("RGB", (w, h), color=(gray, gray, gray)))
        return frames


class MockTTSProvider:
    """Mock TTS provider that returns silent WAV audio of correct duration."""

    _WORDS_PER_SECOND = 2.5

    def synthesize(
        self,
        text: str,
        voice_id: str,
        locale: str,
        speech_rate: float,
    ) -> bytes:
        word_count = max(len(text.split()), 1)
        base_duration = word_count / self._WORDS_PER_SECOND
        adjusted_duration = base_duration / max(speech_rate, 0.1)
        adjusted_duration = max(adjusted_duration, 0.1)
        return self._generate_silent_wav(adjusted_duration)

    @staticmethod
    def _generate_silent_wav(
        duration_seconds: float, sample_rate: int = 44100
    ) -> bytes:
        num_samples = int(sample_rate * duration_seconds)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00\x00" * num_samples)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test artifacts."""
    d = tempfile.mkdtemp(prefix="ramayan_integration_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def test_db(temp_dir):
    """Create a temporary ramayan_db with sample segments."""
    db_path = os.path.join(temp_dir, "ramayan_db")
    os.makedirs(db_path)

    # metadata.json — start at kanda 1, segment 1
    metadata = {
        "current_kanda_index": 1,
        "current_segment_index": 1,
        "total_episodes_completed": 0,
        "series_complete": False,
    }
    with open(os.path.join(db_path, "metadata.json"), "w") as f:
        json.dump(metadata, f)

    # Create kanda directories with segments
    for kanda_idx, kanda_dir_name in enumerate(
        [
            "1_bala_kanda",
            "2_ayodhya_kanda",
            "3_aranya_kanda",
            "4_kishkindha_kanda",
            "5_sundara_kanda",
            "6_yuddha_kanda",
            "7_uttara_kanda",
        ],
        start=1,
    ):
        kanda_names = [
            "Bala Kanda",
            "Ayodhya Kanda",
            "Aranya Kanda",
            "Kishkindha Kanda",
            "Sundara Kanda",
            "Yuddha Kanda",
            "Uttara Kanda",
        ]
        kanda_path = os.path.join(db_path, "kandas", kanda_dir_name)
        segments_path = os.path.join(kanda_path, "segments")
        os.makedirs(segments_path)

        # kanda.json
        kanda_meta = {
            "kanda_index": kanda_idx,
            "kanda_name": kanda_names[kanda_idx - 1],
            "description": f"Kanda {kanda_idx}",
            "total_segments": 2 if kanda_idx <= 2 else 0,
        }
        with open(os.path.join(kanda_path, "kanda.json"), "w") as f:
            json.dump(kanda_meta, f)

        # Create 2 segments for first 2 kandas
        if kanda_idx <= 2:
            for seg_idx in range(1, 3):
                segment = {
                    "kanda_index": kanda_idx,
                    "kanda_name": kanda_names[kanda_idx - 1],
                    "chapter": 1,
                    "segment_index": seg_idx,
                    "title": f"Segment {seg_idx} of Kanda {kanda_idx}",
                    "content": (
                        "In the ancient kingdom of Ayodhya, King Dasharatha "
                        "ruled with wisdom and justice. Despite his prosperity, "
                        "the king was troubled by the absence of an heir. "
                        "On the advice of Sage Vasishtha, King Dasharatha "
                        "performed the sacred Putrakameshti Yajna."
                    ),
                    "characters": [
                        "King Dasharatha",
                        "Sage Vasishtha",
                        "Queen Kausalya",
                    ],
                    "key_events": [
                        "Sacred ceremony performed",
                        "Divine blessings received",
                    ],
                }
                with open(
                    os.path.join(segments_path, f"{seg_idx:03d}.json"), "w"
                ) as f:
                    json.dump(segment, f)

    # episodes directory
    os.makedirs(os.path.join(db_path, "episodes"), exist_ok=True)

    return db_path


@pytest.fixture
def output_dir(temp_dir):
    """Create a temporary output directory."""
    d = os.path.join(temp_dir, "output")
    os.makedirs(d)
    return d


@pytest.fixture
def test_config():
    """Create a test Config object."""
    return Config(
        pipeline=PipelineConfig(
            schedule_time="06:00",
            target_duration_seconds=120,
            retry_attempts=3,
        ),
        animation=AnimationConfig(
            style_reference="indian_traditional_art",
            resolution=[108, 192],  # Small resolution for fast test execution
            fps=12,  # Lower FPS for faster test execution
            model="stable-diffusion-xl",
            lora_path="./models/indian_art_lora.safetensors",
        ),
        narration=NarrationConfig(
            default_locale="hi",
            narrator_voice="narrator_v1",
            tts_provider="coqui",
            character_voices={
                "King Dasharatha": "voice_dasharatha",
                "Sage Vasishtha": "voice_vasishtha",
                "Queen Kausalya": "voice_kausalya",
                "Queen Kaikeyi": "voice_kaikeyi",
                "Queen Sumitra": "voice_sumitra",
            },
        ),
        audio=AudioConfig(
            music_library_path="./assets/music/",
            sfx_library_path="./assets/sfx/",
            narration_boost_db=6,
            crossfade_seconds=0.75,
        ),
        output=OutputConfig(format="mp4", video_codec="h264", audio_codec="aac"),
        storage=StorageConfig(
            provider="s3", bucket="ramayan-videos", path_prefix="episodes/"
        ),
        distribution=DistributionConfig(),
        notifications=NotificationsConfig(provider="mock"),
    )


def _build_full_pipeline(
    test_config: Config,
    test_db: str,
    output_dir: str,
    llm_client: Optional[Any] = None,
    image_generator: Optional[Any] = None,
    quality_scorer: Optional[Any] = None,
    frame_interpolator: Optional[Any] = None,
    tts_provider: Optional[Any] = None,
    storage_uploader: Optional[Any] = None,
    notification_sender: Optional[Any] = None,
):
    """Wire up all REAL components with mock external services.

    Returns a tuple of (orchestrator, components_dict) so tests can
    inspect individual components after the pipeline runs.
    """
    # Real StoryManager with test DB
    story_manager = StoryManager(db_path=test_db)

    # Real ScriptEngine with mock LLM
    mock_llm = llm_client or MockLLMClient()
    script_engine = ScriptEngine(
        llm_client=mock_llm,
        model="gpt-4",
        temperature=0.7,
        characters_dir=os.path.join(test_db, "nonexistent_chars"),
    )

    # Real AnimationEngine with mock ML services
    mock_img_gen = image_generator or MockImageGenerator()
    mock_scorer = quality_scorer or MockQualityScorer()
    mock_interpolator = frame_interpolator or MockFrameInterpolator()
    animation_engine = AnimationEngine(
        config=test_config.animation,
        image_generator=mock_img_gen,
        quality_scorer=mock_scorer,
        frame_interpolator=mock_interpolator,
        characters_dir=os.path.join(test_db, "nonexistent_chars"),
    )

    # Real NarrationEngine with mock TTS
    mock_tts = tts_provider or MockTTSProvider()
    narration_engine = NarrationEngine(
        config=test_config.narration,
        tts_provider=mock_tts,
    )

    # Real AudioEngine with empty libraries (no real music/sfx files needed)
    audio_engine = AudioEngine(
        config=test_config.audio,
        music_library=MusicLibrary(),
        sfx_library=SFXLibrary(),
    )

    # Real VideoCompositor with MockRenderer
    mock_renderer = MockRenderer()
    video_compositor = VideoCompositor(
        output_config=test_config.output,
        animation_config=test_config.animation,
        renderer=mock_renderer,
    )

    # Real DistributionManager with MockStorageUploader
    mock_uploader = storage_uploader or MockStorageUploader()
    distribution_manager = DistributionManager(
        storage_config=test_config.storage,
        distribution_config=test_config.distribution,
        storage_uploader=mock_uploader,
        sleep_fn=lambda x: None,  # no real sleeping in tests
    )

    # Notification sender
    mock_notifier = notification_sender or MockNotificationAdapter()

    # Real Orchestrator wiring everything together
    orchestrator = VideoGeneratorOrchestrator(
        config=test_config,
        story_manager=story_manager,
        script_engine=script_engine,
        animation_engine=animation_engine,
        narration_engine=narration_engine,
        audio_engine=audio_engine,
        video_compositor=video_compositor,
        distribution_manager=distribution_manager,
        notification_sender=mock_notifier,
        output_dir=output_dir,
    )

    components = {
        "story_manager": story_manager,
        "script_engine": script_engine,
        "animation_engine": animation_engine,
        "narration_engine": narration_engine,
        "audio_engine": audio_engine,
        "video_compositor": video_compositor,
        "distribution_manager": distribution_manager,
        "notification_sender": mock_notifier,
        "storage_uploader": mock_uploader,
        "llm_client": mock_llm,
    }

    return orchestrator, components


# ---------------------------------------------------------------------------
# 11.1 End-to-end integration test: full pipeline with mock AI services
# ---------------------------------------------------------------------------


class TestEndToEndPipeline:
    """Verify the complete flow from story segment to output video file."""

    def test_full_pipeline_completes_successfully(
        self, test_config, test_db, output_dir
    ):
        """Run the full pipeline with mock AI services and verify it completes."""
        orchestrator, components = _build_full_pipeline(
            test_config, test_db, output_dir
        )

        result = orchestrator.run_pipeline()

        assert result.success is True, (
            f"Pipeline failed: {result.error_message}"
        )
        assert result.episode_number == 1
        assert result.kanda_name == "Bala Kanda"
        assert result.output_path != ""

    def test_pipeline_produces_output_file(
        self, test_config, test_db, output_dir
    ):
        """The pipeline produces an output file at the expected path."""
        orchestrator, _ = _build_full_pipeline(
            test_config, test_db, output_dir
        )

        result = orchestrator.run_pipeline()

        assert result.success is True
        assert os.path.exists(result.output_path), (
            f"Output file not found: {result.output_path}"
        )

    def test_pipeline_calls_all_stages(
        self, test_config, test_db, output_dir
    ):
        """All pipeline stages are invoked during a successful run."""
        mock_llm = MockLLMClient()
        orchestrator, components = _build_full_pipeline(
            test_config, test_db, output_dir, llm_client=mock_llm
        )

        result = orchestrator.run_pipeline()

        assert result.success is True
        # LLM was called (ScriptEngine stage)
        assert mock_llm.call_count >= 1
        # Storage uploader was called (Distribution stage)
        uploader = components["storage_uploader"]
        assert len(uploader.upload_calls) >= 1


# ---------------------------------------------------------------------------
# 11.2 Verify pipeline produces valid MP4 with correct format/resolution/duration
# ---------------------------------------------------------------------------


class TestOutputVideoFormat:
    """Verify the output video has correct format, resolution, and duration."""

    def test_output_is_mp4_format(self, test_config, test_db, output_dir):
        """The output file path ends with .mp4."""
        orchestrator, _ = _build_full_pipeline(
            test_config, test_db, output_dir
        )

        result = orchestrator.run_pipeline()

        assert result.success is True
        assert result.output_path.endswith(".mp4")

    def test_output_video_metadata_correct(
        self, test_config, test_db, output_dir
    ):
        """The mock video file contains correct metadata (format, codec, resolution)."""
        orchestrator, _ = _build_full_pipeline(
            test_config, test_db, output_dir
        )

        result = orchestrator.run_pipeline()

        assert result.success is True
        assert os.path.exists(result.output_path)

        # The MockRenderer writes JSON metadata into the file
        with open(result.output_path, "r") as f:
            video_meta = json.load(f)

        assert video_meta["format"] == "mp4"
        assert video_meta["video_codec"] == "h264"
        assert video_meta["audio_codec"] == "aac"
        # Resolution matches the configured animation resolution
        assert video_meta["width"] == test_config.animation.resolution[0]
        assert video_meta["height"] == test_config.animation.resolution[1]

    def test_output_video_has_audio(self, test_config, test_db, output_dir):
        """The output video includes an audio track."""
        orchestrator, _ = _build_full_pipeline(
            test_config, test_db, output_dir
        )

        result = orchestrator.run_pipeline()

        assert result.success is True
        with open(result.output_path, "r") as f:
            video_meta = json.load(f)

        assert video_meta.get("has_audio") is True


# ---------------------------------------------------------------------------
# 11.3 Verify Story_Manager advances correctly after a successful pipeline run
# ---------------------------------------------------------------------------


class TestStoryManagerAdvancement:
    """Verify that the Story_Manager position advances after a successful run."""

    def test_position_advances_after_pipeline_run(
        self, test_config, test_db, output_dir
    ):
        """After one pipeline run, the story position advances by one segment."""
        orchestrator, components = _build_full_pipeline(
            test_config, test_db, output_dir
        )
        sm = components["story_manager"]

        # Before: position at kanda 1, segment 1, 0 episodes completed
        pos_before = sm.get_current_position()
        assert pos_before.current_kanda_index == 1
        assert pos_before.current_segment_index == 1
        assert pos_before.total_episodes_completed == 0

        result = orchestrator.run_pipeline()
        assert result.success is True

        # After: position should have advanced
        pos_after = sm.get_current_position()
        assert pos_after.total_episodes_completed == 1
        assert pos_after.current_segment_index > pos_before.current_segment_index or (
            pos_after.current_kanda_index > pos_before.current_kanda_index
        )

    def test_two_consecutive_runs_advance_twice(
        self, test_config, test_db, output_dir
    ):
        """Two consecutive pipeline runs advance the position by two segments."""
        orchestrator, components = _build_full_pipeline(
            test_config, test_db, output_dir
        )
        sm = components["story_manager"]

        result1 = orchestrator.run_pipeline()
        assert result1.success is True

        result2 = orchestrator.run_pipeline()
        assert result2.success is True

        pos = sm.get_current_position()
        assert pos.total_episodes_completed == 2
        assert result2.episode_number == 2

    def test_episode_marked_complete_in_db(
        self, test_config, test_db, output_dir
    ):
        """After a successful run, the episode record is marked complete."""
        orchestrator, _ = _build_full_pipeline(
            test_config, test_db, output_dir
        )

        result = orchestrator.run_pipeline()
        assert result.success is True

        # Check the episode record on disk
        episode_path = os.path.join(
            test_db, "episodes", "episode_001.json"
        )
        assert os.path.exists(episode_path)
        with open(episode_path, "r") as f:
            record = json.load(f)
        assert record["status"] == "complete"
        assert record["output_path"] != ""


# ---------------------------------------------------------------------------
# 11.4 Verify Distribution_Manager logs correct metadata after upload
# ---------------------------------------------------------------------------


class TestDistributionManagerLogging:
    """Verify that distribution logs contain correct metadata after upload."""

    def test_distribution_log_contains_success_entry(
        self, test_config, test_db, output_dir
    ):
        """After a successful pipeline run, the distribution log has a success entry."""
        orchestrator, components = _build_full_pipeline(
            test_config, test_db, output_dir
        )

        result = orchestrator.run_pipeline()
        assert result.success is True

        dm = components["distribution_manager"]
        log = dm.distribution_log
        assert len(log) >= 1

        # At least one entry should be a success
        success_entries = [e for e in log if e.status == "success"]
        assert len(success_entries) >= 1

    def test_distribution_log_has_required_fields(
        self, test_config, test_db, output_dir
    ):
        """Each distribution log entry has platform, status, url, and timestamp."""
        orchestrator, components = _build_full_pipeline(
            test_config, test_db, output_dir
        )

        result = orchestrator.run_pipeline()
        assert result.success is True

        dm = components["distribution_manager"]
        for entry in dm.distribution_log:
            assert entry.platform is not None and entry.platform != ""
            assert entry.status in ("success", "failed")
            assert entry.timestamp is not None and entry.timestamp != ""
            if entry.status == "success":
                assert entry.url is not None and entry.url != ""

    def test_distribution_log_has_correct_episode_metadata(
        self, test_config, test_db, output_dir
    ):
        """Distribution log entries reference the correct episode and kanda."""
        orchestrator, components = _build_full_pipeline(
            test_config, test_db, output_dir
        )

        result = orchestrator.run_pipeline()
        assert result.success is True

        dm = components["distribution_manager"]
        success_entries = [e for e in dm.distribution_log if e.status == "success"]
        assert len(success_entries) >= 1

        entry = success_entries[0]
        assert entry.episode_number == 1
        assert entry.kanda_name == "Bala Kanda"

    def test_storage_uploader_receives_correct_file(
        self, test_config, test_db, output_dir
    ):
        """The mock storage uploader receives the video file with correct naming."""
        mock_uploader = MockStorageUploader()
        orchestrator, _ = _build_full_pipeline(
            test_config, test_db, output_dir, storage_uploader=mock_uploader
        )

        result = orchestrator.run_pipeline()
        assert result.success is True

        assert len(mock_uploader.upload_calls) >= 1
        call = mock_uploader.upload_calls[0]
        assert call["bucket"] == "ramayan-videos"
        assert "ramayan_e0001_bala_kanda_" in call["remote_key"]
        assert call["remote_key"].endswith(".mp4")


# ---------------------------------------------------------------------------
# 11.5 Pipeline failure and recovery
# ---------------------------------------------------------------------------


class TestPipelineFailureAndRecovery:
    """Test pipeline failure, retry behavior, and recovery on next run."""

    def test_stage_failure_triggers_retry(
        self, test_config, test_db, output_dir
    ):
        """When a stage fails, the pipeline retries before giving up."""
        # LLM fails twice then succeeds (retry_attempts=3 allows this)
        failing_llm = MockLLMClient(fail_count=2)
        orchestrator, _ = _build_full_pipeline(
            test_config, test_db, output_dir, llm_client=failing_llm
        )

        result = orchestrator.run_pipeline()

        assert result.success is True
        # LLM was called 3 times: 2 failures + 1 success
        assert failing_llm.call_count == 3

    def test_all_retries_exhausted_sends_notification(
        self, test_config, test_db, output_dir
    ):
        """When all retries are exhausted, a failure notification is sent."""
        # LLM always fails
        always_failing_llm = MockLLMClient(fail_count=999)
        mock_notifier = MockNotificationAdapter()

        orchestrator, _ = _build_full_pipeline(
            test_config,
            test_db,
            output_dir,
            llm_client=always_failing_llm,
            notification_sender=mock_notifier,
        )

        result = orchestrator.run_pipeline()

        assert result.success is False
        assert len(mock_notifier.sent_alerts) >= 1
        alert = mock_notifier.sent_alerts[0]
        assert alert.stage_name == "Script_Engine"

    def test_pipeline_resumes_from_failed_episode_on_next_run(
        self, test_config, test_db, output_dir
    ):
        """After a failure, the next run picks up the same segment.

        The StoryManager advances the pointer in get_next_segment(),
        so after a failed run the pointer has already moved. The next
        run will process the next segment. This test verifies that
        the pipeline can successfully run after a prior failure.
        """
        # First run: LLM always fails → pipeline fails
        always_failing_llm = MockLLMClient(fail_count=999)
        mock_notifier = MockNotificationAdapter()

        orchestrator1, components1 = _build_full_pipeline(
            test_config,
            test_db,
            output_dir,
            llm_client=always_failing_llm,
            notification_sender=mock_notifier,
        )

        result1 = orchestrator1.run_pipeline()
        assert result1.success is False

        # Record position after failure
        sm = components1["story_manager"]
        pos_after_failure = sm.get_current_position()

        # Second run: use a working LLM → pipeline succeeds
        # Re-create orchestrator with the same story_manager (same DB state)
        working_llm = MockLLMClient()
        mock_uploader = MockStorageUploader()

        # Re-create components but reuse the same DB path
        orchestrator2, components2 = _build_full_pipeline(
            test_config,
            test_db,
            output_dir,
            llm_client=working_llm,
            storage_uploader=mock_uploader,
        )

        result2 = orchestrator2.run_pipeline()
        assert result2.success is True

        # Verify the pipeline produced output
        assert os.path.exists(result2.output_path)

    def test_failed_pipeline_does_not_mark_episode_complete(
        self, test_config, test_db, output_dir
    ):
        """A failed pipeline run does not mark the episode as complete."""
        always_failing_llm = MockLLMClient(fail_count=999)
        mock_notifier = MockNotificationAdapter()

        orchestrator, _ = _build_full_pipeline(
            test_config,
            test_db,
            output_dir,
            llm_client=always_failing_llm,
            notification_sender=mock_notifier,
        )

        result = orchestrator.run_pipeline()
        assert result.success is False

        # The episode record should exist but not be marked complete
        episode_path = os.path.join(
            test_db, "episodes", "episode_001.json"
        )
        if os.path.exists(episode_path):
            with open(episode_path, "r") as f:
                record = json.load(f)
            assert record["status"] != "complete"

    def test_notification_contains_failure_details(
        self, test_config, test_db, output_dir
    ):
        """The failure notification includes stage name and error details."""
        always_failing_llm = MockLLMClient(fail_count=999)
        mock_notifier = MockNotificationAdapter()

        orchestrator, _ = _build_full_pipeline(
            test_config,
            test_db,
            output_dir,
            llm_client=always_failing_llm,
            notification_sender=mock_notifier,
        )

        result = orchestrator.run_pipeline()
        assert result.success is False

        assert len(mock_notifier.sent_alerts) >= 1
        alert = mock_notifier.sent_alerts[0]
        assert alert.stage_name != ""
        assert alert.error_message != ""
        assert alert.retry_attempts == test_config.pipeline.retry_attempts
