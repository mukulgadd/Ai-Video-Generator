"""Pipeline Orchestrator for the Ramayan Video Generator.

Coordinates all pipeline stages in sequence to produce a finished
animated video from a story segment. Implements stage retry logic,
failure notification, and pipeline logging.

Validates: Requirements 1.2, 1.3, 1.4, 1.5
"""

import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

from src.animation_engine import AnimationEngine, EpisodeFrames
from src.audio_engine import AudioEngine
from src.config_loader import Config
from src.distribution_manager import DistributionManager, DistributionResult
from src.episode_script import EpisodeScript
from src.narration_engine import EpisodeAudio, NarrationEngine
from src.notifications import (
    MockNotificationAdapter,
    NotificationSender,
    PipelineFailureAlert,
)
from src.script_engine import ScriptEngine
from src.story_manager import StoryManager, StorySegment
from src.video_compositor import VideoCompositor, VideoMetadata

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class OrchestratorError(Exception):
    """Raised when the orchestrator encounters an unrecoverable error."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class PipelineResult:
    """Result of a single pipeline run."""

    success: bool
    episode_number: int = 0
    kanda_name: str = ""
    output_path: str = ""
    failed_stage: str = ""
    error_message: str = ""


# ---------------------------------------------------------------------------
# VideoGeneratorOrchestrator
# ---------------------------------------------------------------------------


class VideoGeneratorOrchestrator:
    """Orchestrates the full video generation pipeline.

    Executes all pipeline stages in sequence:
    1. Story_Manager.get_next_segment() → StorySegment
    2. ScriptEngine.generate_script(segment, registry) → EpisodeScript
    3. AnimationEngine.generate_episode_frames(script) → EpisodeFrames
    4. NarrationEngine.generate_episode_audio(script) → EpisodeAudio
    5. AudioEngine.produce_episode_audio(script, episode_audio) → final audio
    6. VideoCompositor.compose_video(script, frames, audio, output) → VideoMetadata
    7. DistributionManager.distribute(video, episode_num, kanda, title) → DistributionResult
    8. StoryManager.mark_episode_complete(episode_id, output_path)

    Implements retry logic per stage and failure notifications when all
    retries are exhausted.

    Args:
        config: The pipeline configuration.
        story_manager: StoryManager instance.
        script_engine: ScriptEngine instance.
        animation_engine: AnimationEngine instance.
        narration_engine: NarrationEngine instance.
        audio_engine: AudioEngine instance.
        video_compositor: VideoCompositor instance.
        distribution_manager: DistributionManager instance.
        notification_sender: Notification sender for failure alerts.
        output_dir: Directory for output video files.
    """

    def __init__(
        self,
        config: Config,
        story_manager: StoryManager,
        script_engine: ScriptEngine,
        animation_engine: AnimationEngine,
        narration_engine: NarrationEngine,
        audio_engine: AudioEngine,
        video_compositor: VideoCompositor,
        distribution_manager: DistributionManager,
        notification_sender: Optional[Any] = None,
        output_dir: str = "output",
    ):
        self._config = config
        self._story_manager = story_manager
        self._script_engine = script_engine
        self._animation_engine = animation_engine
        self._narration_engine = narration_engine
        self._audio_engine = audio_engine
        self._video_compositor = video_compositor
        self._distribution_manager = distribution_manager
        self._notification_sender = notification_sender or MockNotificationAdapter()
        self._output_dir = output_dir
        self._retry_attempts = config.pipeline.retry_attempts

    def _run_stage_with_retry(
        self,
        stage_name: str,
        stage_fn: Any,
        episode_number: int,
        kanda_name: str,
    ) -> Any:
        """Execute a pipeline stage with retry logic.

        If the stage fails, retries up to retry_attempts times.
        If all retries fail, sends a failure notification and raises
        OrchestratorError.

        Args:
            stage_name: Human-readable name of the stage.
            stage_fn: Callable that executes the stage. Takes no arguments.
            episode_number: Current episode number (for logging/notification).
            kanda_name: Current Kanda name (for logging/notification).

        Returns:
            The return value of stage_fn.

        Raises:
            OrchestratorError: If all retry attempts fail.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self._retry_attempts + 1):
            try:
                logger.info(
                    "Episode %d (%s): Running stage '%s' (attempt %d/%d)",
                    episode_number,
                    kanda_name,
                    stage_name,
                    attempt,
                    self._retry_attempts,
                )
                result = stage_fn()
                logger.info(
                    "Episode %d (%s): Stage '%s' completed successfully",
                    episode_number,
                    kanda_name,
                    stage_name,
                )
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    "Episode %d (%s): Stage '%s' failed (attempt %d/%d): %s",
                    episode_number,
                    kanda_name,
                    stage_name,
                    attempt,
                    self._retry_attempts,
                    e,
                )

        # All retries exhausted — send failure notification
        error_msg = str(last_error) if last_error else "Unknown error"
        alert = PipelineFailureAlert(
            stage_name=stage_name,
            error_message=error_msg,
            episode_number=episode_number,
            kanda_name=kanda_name,
            retry_attempts=self._retry_attempts,
        )
        self._notification_sender.send(alert)

        logger.error(
            "Episode %d (%s): Stage '%s' failed after %d retries. "
            "Notification sent.",
            episode_number,
            kanda_name,
            stage_name,
            self._retry_attempts,
        )

        raise OrchestratorError(
            f"Stage '{stage_name}' failed after {self._retry_attempts} "
            f"retries: {error_msg}"
        )

    def run_pipeline(self) -> PipelineResult:
        """Execute the full video generation pipeline.

        Runs all stages in sequence with retry logic. On success, logs
        the episode number, Kanda name, and output file path. On failure,
        logs the failure details and sends a notification.

        Returns:
            PipelineResult indicating success or failure.
        """
        episode_number = 0
        kanda_name = ""

        try:
            # Stage 1: Get next story segment
            segment: StorySegment = self._run_stage_with_retry(
                stage_name="Story_Manager",
                stage_fn=lambda: self._story_manager.get_next_segment(),
                episode_number=episode_number,
                kanda_name=kanda_name,
            )

            episode_number = self._story_manager.get_current_position().total_episodes_completed
            kanda_name = segment.kanda_name

            logger.info(
                "Pipeline started: Episode %d, Kanda: %s, Segment: %s",
                episode_number,
                kanda_name,
                segment.title,
            )

            # Stage 2: Generate script
            script: EpisodeScript = self._run_stage_with_retry(
                stage_name="Script_Engine",
                stage_fn=lambda: self._script_engine.generate_script(
                    segment=segment,
                    episode_number=episode_number,
                ),
                episode_number=episode_number,
                kanda_name=kanda_name,
            )

            logger.info(
                "Episode %d (%s): Script generated — %d scenes, %ds total",
                episode_number,
                kanda_name,
                len(script.scenes),
                script.total_duration_seconds,
            )

            # Stage 3: Generate animation frames
            episode_frames: EpisodeFrames = self._run_stage_with_retry(
                stage_name="Animation_Engine",
                stage_fn=lambda: self._animation_engine.generate_episode_frames(
                    script=script,
                ),
                episode_number=episode_number,
                kanda_name=kanda_name,
            )

            logger.info(
                "Episode %d (%s): Animation frames generated — %d scenes",
                episode_number,
                kanda_name,
                len(episode_frames.scene_frames),
            )

            # Stage 4: Generate narration audio
            episode_audio: EpisodeAudio = self._run_stage_with_retry(
                stage_name="Narration_Engine",
                stage_fn=lambda: self._narration_engine.generate_episode_audio(
                    script=script,
                ),
                episode_number=episode_number,
                kanda_name=kanda_name,
            )

            logger.info(
                "Episode %d (%s): Narration audio generated — %.2fs",
                episode_number,
                kanda_name,
                episode_audio.total_duration_seconds,
            )

            # Stage 5: Produce final audio (mix narration + music + SFX)
            audio_output_path = os.path.join(
                self._output_dir, f"episode_{episode_number:04d}_audio.wav"
            )
            os.makedirs(self._output_dir, exist_ok=True)

            final_audio = self._run_stage_with_retry(
                stage_name="Audio_Engine",
                stage_fn=lambda: self._audio_engine.produce_episode_audio(
                    script=script,
                    episode_audio=episode_audio,
                    output_path=audio_output_path,
                ),
                episode_number=episode_number,
                kanda_name=kanda_name,
            )

            logger.info(
                "Episode %d (%s): Final audio produced — %s",
                episode_number,
                kanda_name,
                audio_output_path,
            )

            # Stage 6: Compose video
            video_output_path = os.path.join(
                self._output_dir, f"episode_{episode_number:04d}.mp4"
            )

            # Collect frame paths per scene
            scene_frame_paths: List[List[str]] = [
                [f.path for f in sf.all_frames]
                for sf in episode_frames.scene_frames
            ]

            video_metadata: VideoMetadata = self._run_stage_with_retry(
                stage_name="Video_Compositor",
                stage_fn=lambda: self._video_compositor.compose_video(
                    script=script,
                    scene_frame_paths=scene_frame_paths,
                    audio_path=audio_output_path,
                    output_path=video_output_path,
                ),
                episode_number=episode_number,
                kanda_name=kanda_name,
            )

            logger.info(
                "Episode %d (%s): Video composed — %s (%.2fs)",
                episode_number,
                kanda_name,
                video_output_path,
                video_metadata.duration_seconds,
            )

            # Stage 7: Distribute
            thumbnail_path = (
                episode_frames.thumbnail.path
                if episode_frames.thumbnail
                else None
            )

            distribution_result: DistributionResult = self._run_stage_with_retry(
                stage_name="Distribution_Manager",
                stage_fn=lambda: self._distribution_manager.distribute(
                    video_path=video_output_path,
                    episode_number=episode_number,
                    kanda_name=kanda_name,
                    title=script.title,
                    thumbnail_path=thumbnail_path,
                ),
                episode_number=episode_number,
                kanda_name=kanda_name,
            )

            logger.info(
                "Episode %d (%s): Distribution complete — storage=%s",
                episode_number,
                kanda_name,
                distribution_result.storage_url,
            )

            # Stage 8: Mark episode complete
            self._story_manager.mark_episode_complete(
                episode_id=episode_number,
                output_path=video_output_path,
            )

            logger.info(
                "Pipeline complete: Episode %d, Kanda: %s, Output: %s",
                episode_number,
                kanda_name,
                video_output_path,
            )

            return PipelineResult(
                success=True,
                episode_number=episode_number,
                kanda_name=kanda_name,
                output_path=video_output_path,
            )

        except OrchestratorError as e:
            logger.error(
                "Pipeline failed: Episode %d, Kanda: %s, Error: %s",
                episode_number,
                kanda_name,
                e.message,
            )
            return PipelineResult(
                success=False,
                episode_number=episode_number,
                kanda_name=kanda_name,
                failed_stage=e.message.split("'")[1] if "'" in e.message else "",
                error_message=e.message,
            )
        except Exception as e:
            logger.error(
                "Pipeline failed with unexpected error: Episode %d, "
                "Kanda: %s, Error: %s",
                episode_number,
                kanda_name,
                e,
            )
            return PipelineResult(
                success=False,
                episode_number=episode_number,
                kanda_name=kanda_name,
                error_message=str(e),
            )
