"""Tests for the Pipeline Orchestrator.

Mocks all pipeline stages and verifies:
- Sequential execution order
- Retry logic on stage failure
- Failure notification when retries exhausted
- Logging of pipeline progress

Validates: Requirements 1.2, 1.3, 1.4, 1.5
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, call, patch

import pytest

from src.config_loader import (
    AudioConfig,
    Config,
    DistributionConfig,
    NotificationsConfig,
    OutputConfig,
    PipelineConfig,
    StorageConfig,
)
from src.distribution_manager import DistributionResult
from src.episode_script import DialogueLine, EpisodeScript, Scene
from src.narration_engine import AudioSegment, EpisodeAudio, SceneAudio
from src.animation_engine import EpisodeFrames, GeneratedFrame, SceneFrames
from src.notifications import MockNotificationAdapter, PipelineFailureAlert
from src.orchestrator import (
    OrchestratorError,
    PipelineResult,
    VideoGeneratorOrchestrator,
)
from src.story_manager import Position, StorySegment
from src.video_compositor import VideoMetadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(retry_attempts: int = 3) -> Config:
    """Create a Config with the given retry attempts."""
    return Config(
        pipeline=PipelineConfig(retry_attempts=retry_attempts),
        notifications=NotificationsConfig(provider="mock"),
    )


def _make_segment() -> StorySegment:
    """Create a sample StorySegment."""
    return StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=1,
        title="The Birth of Rama",
        content="In the ancient kingdom of Ayodhya...",
        characters=["Rama", "Dasharatha"],
        key_events=["Birth of Rama"],
    )


def _make_script(episode_number: int = 1) -> EpisodeScript:
    """Create a sample EpisodeScript."""
    return EpisodeScript(
        episode_number=episode_number,
        kanda="Bala Kanda",
        title="The Birth of Rama",
        total_duration_seconds=120,
        scenes=[
            Scene(
                scene_number=1,
                duration_seconds=30,
                background="Royal palace",
                characters=["Rama"],
                action="Rama is born",
                narration="In the ancient kingdom...",
                dialogue=[DialogueLine(character="Rama", text="Hello")],
                mood="devotional",
                sound_effects=["temple_bells"],
            ),
            Scene(
                scene_number=2,
                duration_seconds=30,
                background="Garden",
                characters=["Rama"],
                action="Rama plays",
                narration="The young prince...",
                dialogue=[],
                mood="serene",
                sound_effects=[],
            ),
            Scene(
                scene_number=3,
                duration_seconds=30,
                background="Palace courtyard",
                characters=["Rama", "Dasharatha"],
                action="Dasharatha blesses Rama",
                narration="The king blessed...",
                dialogue=[],
                mood="devotional",
                sound_effects=[],
            ),
            Scene(
                scene_number=4,
                duration_seconds=30,
                background="Temple",
                characters=["Rama"],
                action="Rama prays",
                narration="At the temple...",
                dialogue=[],
                mood="devotional",
                sound_effects=[],
            ),
        ],
    )


def _make_episode_frames() -> EpisodeFrames:
    """Create sample EpisodeFrames."""
    frame = GeneratedFrame(path="/tmp/frame.png", width=1080, height=1920, quality_score=0.9)
    scene_frames = SceneFrames(
        scene_number=1,
        keyframes=[frame],
        interpolated_frames=[],
        all_frames=[frame],
    )
    return EpisodeFrames(
        episode_number=1,
        scene_frames=[scene_frames] * 4,
        thumbnail=frame,
    )


def _make_episode_audio() -> EpisodeAudio:
    """Create sample EpisodeAudio."""
    segment = AudioSegment(
        scene_number=1,
        segment_type="narration",
        character=None,
        text="Test narration",
        voice_id="narrator_v1",
        audio_data=b"\x00" * 100,
        duration_seconds=5.0,
    )
    scene_audio = SceneAudio(scene_number=1, segments=[segment])
    return EpisodeAudio(
        episode_number=1,
        scene_audio=[scene_audio] * 4,
    )


def _make_video_metadata() -> VideoMetadata:
    """Create sample VideoMetadata."""
    return VideoMetadata(
        file_path="output/episode_0001.mp4",
        format="mp4",
        video_codec="h264",
        audio_codec="aac",
        width=1080,
        height=1920,
        fps=24,
        duration_seconds=120.0,
    )


def _make_distribution_result() -> DistributionResult:
    """Create sample DistributionResult."""
    return DistributionResult(
        episode_number=1,
        kanda_name="Bala Kanda",
        filename="ramayan_e0001_bala_kanda_20240101.mp4",
        storage_url="https://s3.amazonaws.com/ramayan-videos/episodes/test.mp4",
        all_successful=True,
    )


def _build_orchestrator(
    config: Optional[Config] = None,
    story_manager: Optional[Any] = None,
    script_engine: Optional[Any] = None,
    animation_engine: Optional[Any] = None,
    narration_engine: Optional[Any] = None,
    audio_engine: Optional[Any] = None,
    video_compositor: Optional[Any] = None,
    distribution_manager: Optional[Any] = None,
    notification_sender: Optional[Any] = None,
) -> VideoGeneratorOrchestrator:
    """Build an orchestrator with mocked components."""
    cfg = config or _make_config()

    sm = story_manager or MagicMock()
    se = script_engine or MagicMock()
    ae = animation_engine or MagicMock()
    ne = narration_engine or MagicMock()
    aue = audio_engine or MagicMock()
    vc = video_compositor or MagicMock()
    dm = distribution_manager or MagicMock()
    ns = notification_sender or MockNotificationAdapter()

    return VideoGeneratorOrchestrator(
        config=cfg,
        story_manager=sm,
        script_engine=se,
        animation_engine=ae,
        narration_engine=ne,
        audio_engine=aue,
        video_compositor=vc,
        distribution_manager=dm,
        notification_sender=ns,
        output_dir="/tmp/test_output",
    )


# ---------------------------------------------------------------------------
# Tests: Sequential Execution (Task 10.1)
# ---------------------------------------------------------------------------


class TestSequentialExecution:
    """Verify that the orchestrator executes all stages in the correct order."""

    def test_all_stages_called_in_sequence(self):
        """All 7 pipeline stages plus mark_episode_complete are called in order."""
        call_order: List[str] = []

        segment = _make_segment()
        script = _make_script()
        frames = _make_episode_frames()
        audio = _make_episode_audio()
        video_meta = _make_video_metadata()
        dist_result = _make_distribution_result()

        sm = MagicMock()
        sm.get_next_segment.side_effect = lambda: (
            call_order.append("Story_Manager") or segment
        )
        sm.get_current_position.return_value = Position(
            current_kanda_index=1,
            current_segment_index=2,
            total_episodes_completed=1,
            series_complete=False,
        )
        sm.mark_episode_complete.side_effect = lambda **kwargs: (
            call_order.append("mark_complete")
        )

        se = MagicMock()
        se.generate_script.side_effect = lambda **kwargs: (
            call_order.append("Script_Engine") or script
        )

        ae = MagicMock()
        ae.generate_episode_frames.side_effect = lambda **kwargs: (
            call_order.append("Animation_Engine") or frames
        )

        ne = MagicMock()
        ne.generate_episode_audio.side_effect = lambda **kwargs: (
            call_order.append("Narration_Engine") or audio
        )

        aue = MagicMock()
        aue.produce_episode_audio.side_effect = lambda **kwargs: (
            call_order.append("Audio_Engine") or MagicMock()
        )

        vc = MagicMock()
        vc.compose_video.side_effect = lambda **kwargs: (
            call_order.append("Video_Compositor") or video_meta
        )

        dm = MagicMock()
        dm.distribute.side_effect = lambda **kwargs: (
            call_order.append("Distribution_Manager") or dist_result
        )

        orchestrator = _build_orchestrator(
            story_manager=sm,
            script_engine=se,
            animation_engine=ae,
            narration_engine=ne,
            audio_engine=aue,
            video_compositor=vc,
            distribution_manager=dm,
        )

        result = orchestrator.run_pipeline()

        assert result.success is True
        assert call_order == [
            "Story_Manager",
            "Script_Engine",
            "Animation_Engine",
            "Narration_Engine",
            "Audio_Engine",
            "Video_Compositor",
            "Distribution_Manager",
            "mark_complete",
        ]

    def test_successful_pipeline_returns_correct_result(self):
        """A successful pipeline returns episode number, kanda, and output path."""
        segment = _make_segment()
        script = _make_script()
        frames = _make_episode_frames()
        audio = _make_episode_audio()
        video_meta = _make_video_metadata()
        dist_result = _make_distribution_result()

        sm = MagicMock()
        sm.get_next_segment.return_value = segment
        sm.get_current_position.return_value = Position(
            current_kanda_index=1,
            current_segment_index=2,
            total_episodes_completed=1,
            series_complete=False,
        )

        se = MagicMock()
        se.generate_script.return_value = script

        ae = MagicMock()
        ae.generate_episode_frames.return_value = frames

        ne = MagicMock()
        ne.generate_episode_audio.return_value = audio

        aue = MagicMock()
        aue.produce_episode_audio.return_value = MagicMock()

        vc = MagicMock()
        vc.compose_video.return_value = video_meta

        dm = MagicMock()
        dm.distribute.return_value = dist_result

        orchestrator = _build_orchestrator(
            story_manager=sm,
            script_engine=se,
            animation_engine=ae,
            narration_engine=ne,
            audio_engine=aue,
            video_compositor=vc,
            distribution_manager=dm,
        )

        result = orchestrator.run_pipeline()

        assert result.success is True
        assert result.episode_number == 1
        assert result.kanda_name == "Bala Kanda"
        assert "episode_0001" in result.output_path


# ---------------------------------------------------------------------------
# Tests: Retry Logic (Task 10.2)
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """Verify that stages are retried up to the configured number of times."""

    def test_stage_retried_on_failure_then_succeeds(self):
        """A stage that fails once then succeeds should complete the pipeline."""
        segment = _make_segment()
        script = _make_script()
        frames = _make_episode_frames()
        audio = _make_episode_audio()
        video_meta = _make_video_metadata()
        dist_result = _make_distribution_result()

        sm = MagicMock()
        sm.get_next_segment.return_value = segment
        sm.get_current_position.return_value = Position(
            current_kanda_index=1,
            current_segment_index=2,
            total_episodes_completed=1,
            series_complete=False,
        )

        # Script engine fails once, then succeeds
        se = MagicMock()
        se.generate_script.side_effect = [
            RuntimeError("LLM timeout"),
            script,
        ]

        ae = MagicMock()
        ae.generate_episode_frames.return_value = frames

        ne = MagicMock()
        ne.generate_episode_audio.return_value = audio

        aue = MagicMock()
        aue.produce_episode_audio.return_value = MagicMock()

        vc = MagicMock()
        vc.compose_video.return_value = video_meta

        dm = MagicMock()
        dm.distribute.return_value = dist_result

        orchestrator = _build_orchestrator(
            story_manager=sm,
            script_engine=se,
            animation_engine=ae,
            narration_engine=ne,
            audio_engine=aue,
            video_compositor=vc,
            distribution_manager=dm,
        )

        result = orchestrator.run_pipeline()

        assert result.success is True
        assert se.generate_script.call_count == 2

    def test_stage_retried_up_to_max_attempts(self):
        """A stage that always fails should be retried exactly retry_attempts times."""
        config = _make_config(retry_attempts=3)
        segment = _make_segment()

        sm = MagicMock()
        sm.get_next_segment.return_value = segment
        sm.get_current_position.return_value = Position(
            current_kanda_index=1,
            current_segment_index=2,
            total_episodes_completed=1,
            series_complete=False,
        )

        # Script engine always fails
        se = MagicMock()
        se.generate_script.side_effect = RuntimeError("LLM unavailable")

        notification = MockNotificationAdapter()

        orchestrator = _build_orchestrator(
            config=config,
            story_manager=sm,
            script_engine=se,
            notification_sender=notification,
        )

        result = orchestrator.run_pipeline()

        assert result.success is False
        assert se.generate_script.call_count == 3

    def test_retry_with_one_attempt(self):
        """With retry_attempts=1, a failing stage is tried exactly once."""
        config = _make_config(retry_attempts=1)
        segment = _make_segment()

        sm = MagicMock()
        sm.get_next_segment.return_value = segment
        sm.get_current_position.return_value = Position(
            current_kanda_index=1,
            current_segment_index=2,
            total_episodes_completed=1,
            series_complete=False,
        )

        se = MagicMock()
        se.generate_script.side_effect = RuntimeError("fail")

        notification = MockNotificationAdapter()

        orchestrator = _build_orchestrator(
            config=config,
            story_manager=sm,
            script_engine=se,
            notification_sender=notification,
        )

        result = orchestrator.run_pipeline()

        assert result.success is False
        assert se.generate_script.call_count == 1


# ---------------------------------------------------------------------------
# Tests: Failure Notification (Task 10.3)
# ---------------------------------------------------------------------------


class TestFailureNotification:
    """Verify that failure notifications are sent when retries are exhausted."""

    def test_notification_sent_on_stage_failure(self):
        """When all retries for a stage fail, a notification is sent."""
        config = _make_config(retry_attempts=2)
        segment = _make_segment()

        sm = MagicMock()
        sm.get_next_segment.return_value = segment
        sm.get_current_position.return_value = Position(
            current_kanda_index=1,
            current_segment_index=2,
            total_episodes_completed=1,
            series_complete=False,
        )

        se = MagicMock()
        se.generate_script.side_effect = RuntimeError("LLM down")

        notification = MockNotificationAdapter()

        orchestrator = _build_orchestrator(
            config=config,
            story_manager=sm,
            script_engine=se,
            notification_sender=notification,
        )

        result = orchestrator.run_pipeline()

        assert result.success is False
        assert len(notification.sent_alerts) == 1

        alert = notification.sent_alerts[0]
        assert alert.stage_name == "Script_Engine"
        assert "LLM down" in alert.error_message
        assert alert.episode_number == 1
        assert alert.kanda_name == "Bala Kanda"
        assert alert.retry_attempts == 2

    def test_no_notification_on_success(self):
        """No notification is sent when the pipeline succeeds."""
        segment = _make_segment()
        script = _make_script()
        frames = _make_episode_frames()
        audio = _make_episode_audio()
        video_meta = _make_video_metadata()
        dist_result = _make_distribution_result()

        sm = MagicMock()
        sm.get_next_segment.return_value = segment
        sm.get_current_position.return_value = Position(
            current_kanda_index=1,
            current_segment_index=2,
            total_episodes_completed=1,
            series_complete=False,
        )

        se = MagicMock()
        se.generate_script.return_value = script

        ae = MagicMock()
        ae.generate_episode_frames.return_value = frames

        ne = MagicMock()
        ne.generate_episode_audio.return_value = audio

        aue = MagicMock()
        aue.produce_episode_audio.return_value = MagicMock()

        vc = MagicMock()
        vc.compose_video.return_value = video_meta

        dm = MagicMock()
        dm.distribute.return_value = dist_result

        notification = MockNotificationAdapter()

        orchestrator = _build_orchestrator(
            story_manager=sm,
            script_engine=se,
            animation_engine=ae,
            narration_engine=ne,
            audio_engine=aue,
            video_compositor=vc,
            distribution_manager=dm,
            notification_sender=notification,
        )

        result = orchestrator.run_pipeline()

        assert result.success is True
        assert len(notification.sent_alerts) == 0

    def test_notification_contains_correct_stage_for_later_failure(self):
        """Notification identifies the correct stage when a later stage fails."""
        config = _make_config(retry_attempts=1)
        segment = _make_segment()
        script = _make_script()
        frames = _make_episode_frames()

        sm = MagicMock()
        sm.get_next_segment.return_value = segment
        sm.get_current_position.return_value = Position(
            current_kanda_index=1,
            current_segment_index=2,
            total_episodes_completed=1,
            series_complete=False,
        )

        se = MagicMock()
        se.generate_script.return_value = script

        ae = MagicMock()
        ae.generate_episode_frames.return_value = frames

        # Narration engine fails
        ne = MagicMock()
        ne.generate_episode_audio.side_effect = RuntimeError("TTS service down")

        notification = MockNotificationAdapter()

        orchestrator = _build_orchestrator(
            config=config,
            story_manager=sm,
            script_engine=se,
            animation_engine=ae,
            narration_engine=ne,
            notification_sender=notification,
        )

        result = orchestrator.run_pipeline()

        assert result.success is False
        assert len(notification.sent_alerts) == 1
        assert notification.sent_alerts[0].stage_name == "Narration_Engine"


# ---------------------------------------------------------------------------
# Tests: Pipeline Logging (Task 10.7)
# ---------------------------------------------------------------------------


class TestPipelineLogging:
    """Verify that the pipeline logs episode number, Kanda, stage progress, and output."""

    def test_successful_pipeline_logs_completion(self, caplog):
        """A successful pipeline logs the episode number, Kanda, and output path."""
        segment = _make_segment()
        script = _make_script()
        frames = _make_episode_frames()
        audio = _make_episode_audio()
        video_meta = _make_video_metadata()
        dist_result = _make_distribution_result()

        sm = MagicMock()
        sm.get_next_segment.return_value = segment
        sm.get_current_position.return_value = Position(
            current_kanda_index=1,
            current_segment_index=2,
            total_episodes_completed=1,
            series_complete=False,
        )

        se = MagicMock()
        se.generate_script.return_value = script

        ae = MagicMock()
        ae.generate_episode_frames.return_value = frames

        ne = MagicMock()
        ne.generate_episode_audio.return_value = audio

        aue = MagicMock()
        aue.produce_episode_audio.return_value = MagicMock()

        vc = MagicMock()
        vc.compose_video.return_value = video_meta

        dm = MagicMock()
        dm.distribute.return_value = dist_result

        orchestrator = _build_orchestrator(
            story_manager=sm,
            script_engine=se,
            animation_engine=ae,
            narration_engine=ne,
            audio_engine=aue,
            video_compositor=vc,
            distribution_manager=dm,
        )

        with caplog.at_level(logging.INFO, logger="src.orchestrator"):
            result = orchestrator.run_pipeline()

        assert result.success is True

        log_text = caplog.text
        # Verify key information is logged
        assert "Episode 1" in log_text or "episode_0001" in log_text
        assert "Bala Kanda" in log_text
        assert "Pipeline complete" in log_text or "complete" in log_text.lower()

    def test_failed_pipeline_logs_failure(self, caplog):
        """A failed pipeline logs the failure details."""
        config = _make_config(retry_attempts=1)
        segment = _make_segment()

        sm = MagicMock()
        sm.get_next_segment.return_value = segment
        sm.get_current_position.return_value = Position(
            current_kanda_index=1,
            current_segment_index=2,
            total_episodes_completed=1,
            series_complete=False,
        )

        se = MagicMock()
        se.generate_script.side_effect = RuntimeError("LLM error")

        notification = MockNotificationAdapter()

        orchestrator = _build_orchestrator(
            config=config,
            story_manager=sm,
            script_engine=se,
            notification_sender=notification,
        )

        with caplog.at_level(logging.WARNING, logger="src.orchestrator"):
            result = orchestrator.run_pipeline()

        assert result.success is False
        log_text = caplog.text
        assert "Script_Engine" in log_text
        assert "failed" in log_text.lower()

    def test_stage_progress_logged(self, caplog):
        """Each stage's start and completion is logged."""
        segment = _make_segment()
        script = _make_script()
        frames = _make_episode_frames()
        audio = _make_episode_audio()
        video_meta = _make_video_metadata()
        dist_result = _make_distribution_result()

        sm = MagicMock()
        sm.get_next_segment.return_value = segment
        sm.get_current_position.return_value = Position(
            current_kanda_index=1,
            current_segment_index=2,
            total_episodes_completed=1,
            series_complete=False,
        )

        se = MagicMock()
        se.generate_script.return_value = script

        ae = MagicMock()
        ae.generate_episode_frames.return_value = frames

        ne = MagicMock()
        ne.generate_episode_audio.return_value = audio

        aue = MagicMock()
        aue.produce_episode_audio.return_value = MagicMock()

        vc = MagicMock()
        vc.compose_video.return_value = video_meta

        dm = MagicMock()
        dm.distribute.return_value = dist_result

        orchestrator = _build_orchestrator(
            story_manager=sm,
            script_engine=se,
            animation_engine=ae,
            narration_engine=ne,
            audio_engine=aue,
            video_compositor=vc,
            distribution_manager=dm,
        )

        with caplog.at_level(logging.INFO, logger="src.orchestrator"):
            result = orchestrator.run_pipeline()

        assert result.success is True
        log_text = caplog.text

        # Verify all stage names appear in logs
        for stage in [
            "Story_Manager",
            "Script_Engine",
            "Animation_Engine",
            "Narration_Engine",
            "Audio_Engine",
            "Video_Compositor",
            "Distribution_Manager",
        ]:
            assert stage in log_text, f"Stage '{stage}' not found in logs"
