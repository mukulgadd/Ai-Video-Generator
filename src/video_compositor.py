"""Video Compositor for the Ramayan Video Generator.

Combines animation frames and audio into final video using FFmpeg.
Encodes frame sequences into video streams per scene, applies visual
transitions (crossfade/dissolve), overlays title cards, combines video
with audio, and enforces duration constraints.

Uses Protocol-based design for FFmpeg operations to enable dependency
injection and testability without requiring FFmpeg in the test environment.

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
"""

import io
import json
import logging
import os
import struct
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

from src.config_loader import AnimationConfig, OutputConfig
from src.episode_script import EpisodeScript, Scene

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_FPS = 24
DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920
DEFAULT_TRANSITION_DURATION = 0.5  # seconds
MIN_DURATION_SECONDS = 110
MAX_DURATION_SECONDS = 130
TITLE_CARD_DURATION_SECONDS = 4  # 3-5 seconds, default 4
MIN_TITLE_CARD_SECONDS = 3
MAX_TITLE_CARD_SECONDS = 5


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class VideoCompositorError(Exception):
    """Raised when the VideoCompositor encounters an error."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class VideoMetadata:
    """Metadata describing a produced video file."""

    file_path: str
    format: str  # e.g., "mp4"
    video_codec: str  # e.g., "h264"
    audio_codec: str  # e.g., "aac"
    width: int
    height: int
    fps: int
    duration_seconds: float
    was_trimmed: bool = False


@dataclass
class SceneVideo:
    """Video data for a single scene."""

    scene_number: int
    frame_paths: List[str]
    duration_seconds: float
    fps: int


@dataclass
class TitleCard:
    """Title card overlay configuration."""

    kanda_name: str
    episode_number: int
    duration_seconds: float = TITLE_CARD_DURATION_SECONDS
    text: str = ""

    def __post_init__(self):
        if not self.text:
            self.text = f"{self.kanda_name} - Episode {self.episode_number}"


# ---------------------------------------------------------------------------
# VideoRenderer Protocol
# ---------------------------------------------------------------------------


class VideoRenderer(Protocol):
    """Protocol for video rendering operations (e.g., FFmpeg).

    Concrete implementations handle the actual video encoding, transition
    application, title card rendering, and audio muxing. A mock
    implementation is provided for testing.
    """

    def encode_frames_to_video(
        self,
        frame_paths: List[str],
        output_path: str,
        fps: int,
        width: int,
        height: int,
    ) -> str:
        """Encode a sequence of frames into a video file.

        Args:
            frame_paths: Ordered list of frame image file paths.
            output_path: Path for the output video file.
            fps: Frames per second.
            width: Video width in pixels.
            height: Video height in pixels.

        Returns:
            Path to the encoded video file.
        """
        ...

    def apply_transition(
        self,
        video_a_path: str,
        video_b_path: str,
        output_path: str,
        transition_type: str,
        duration_seconds: float,
    ) -> str:
        """Apply a visual transition between two video clips.

        Args:
            video_a_path: Path to the first video clip.
            video_b_path: Path to the second video clip.
            output_path: Path for the output video with transition.
            transition_type: Type of transition (e.g., "crossfade", "dissolve").
            duration_seconds: Duration of the transition in seconds.

        Returns:
            Path to the output video file.
        """
        ...

    def render_title_card(
        self,
        title_text: str,
        output_path: str,
        duration_seconds: float,
        width: int,
        height: int,
        fps: int,
    ) -> str:
        """Render a title card video clip.

        Args:
            title_text: The title text to display.
            output_path: Path for the output title card video.
            duration_seconds: Duration of the title card in seconds.
            width: Video width in pixels.
            height: Video height in pixels.
            fps: Frames per second.

        Returns:
            Path to the title card video file.
        """
        ...

    def combine_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        video_codec: str,
        audio_codec: str,
    ) -> str:
        """Combine a video stream with an audio track.

        Args:
            video_path: Path to the video file.
            audio_path: Path to the audio file (WAV).
            output_path: Path for the output combined file.
            video_codec: Video codec to use (e.g., "h264").
            audio_codec: Audio codec to use (e.g., "aac").

        Returns:
            Path to the combined output file.
        """
        ...

    def trim_video(
        self,
        input_path: str,
        output_path: str,
        max_duration_seconds: float,
        fade_out_seconds: float,
    ) -> str:
        """Trim a video to a maximum duration with fade-out.

        Args:
            input_path: Path to the input video file.
            output_path: Path for the trimmed output file.
            max_duration_seconds: Maximum allowed duration in seconds.
            fade_out_seconds: Duration of the fade-out effect in seconds.

        Returns:
            Path to the trimmed output file.
        """
        ...

    def get_video_duration(self, video_path: str) -> float:
        """Get the duration of a video file in seconds.

        Args:
            video_path: Path to the video file.

        Returns:
            Duration in seconds.
        """
        ...

    def concatenate_videos(
        self,
        video_paths: List[str],
        output_path: str,
    ) -> str:
        """Concatenate multiple video files into one.

        Args:
            video_paths: Ordered list of video file paths.
            output_path: Path for the concatenated output.

        Returns:
            Path to the concatenated output file.
        """
        ...


# ---------------------------------------------------------------------------
# FFmpegRenderer (concrete implementation)
# ---------------------------------------------------------------------------


class FFmpegRenderer:
    """Concrete VideoRenderer using ffmpeg-python.

    In production, this uses the ffmpeg-python library to perform
    actual video encoding operations. This is a placeholder that
    creates minimal valid MP4 files for development.
    """

    def encode_frames_to_video(
        self,
        frame_paths: List[str],
        output_path: str,
        fps: int,
        width: int,
        height: int,
    ) -> str:
        """Encode frames to video using FFmpeg."""
        try:
            import ffmpeg

            if not frame_paths:
                raise VideoCompositorError("No frames to encode")

            # Create a temporary file list for FFmpeg concat
            list_path = output_path + ".frames.txt"
            duration_per_frame = 1.0 / fps
            with open(list_path, "w") as f:
                for frame_path in frame_paths:
                    f.write(f"file '{os.path.abspath(frame_path)}'\n")
                    f.write(f"duration {duration_per_frame}\n")

            (
                ffmpeg.input(list_path, format="concat", safe=0)
                .output(
                    output_path,
                    vcodec="libx264",
                    pix_fmt="yuv420p",
                    r=fps,
                    s=f"{width}x{height}",
                )
                .overwrite_output()
                .run(quiet=True)
            )

            if os.path.exists(list_path):
                os.remove(list_path)

            return output_path
        except ImportError:
            raise VideoCompositorError(
                "ffmpeg-python is required for FFmpegRenderer"
            )

    def apply_transition(
        self,
        video_a_path: str,
        video_b_path: str,
        output_path: str,
        transition_type: str,
        duration_seconds: float,
    ) -> str:
        """Apply transition between two videos using FFmpeg."""
        try:
            import ffmpeg

            in1 = ffmpeg.input(video_a_path)
            in2 = ffmpeg.input(video_b_path)

            (
                ffmpeg.filter([in1, in2], "xfade",
                              transition=transition_type,
                              duration=duration_seconds,
                              offset="0")
                .output(output_path, vcodec="libx264", pix_fmt="yuv420p")
                .overwrite_output()
                .run(quiet=True)
            )

            return output_path
        except ImportError:
            raise VideoCompositorError(
                "ffmpeg-python is required for FFmpegRenderer"
            )

    def render_title_card(
        self,
        title_text: str,
        output_path: str,
        duration_seconds: float,
        width: int,
        height: int,
        fps: int,
    ) -> str:
        """Render a title card using FFmpeg drawtext filter."""
        try:
            import ffmpeg

            (
                ffmpeg.input(
                    f"color=c=black:s={width}x{height}:d={duration_seconds}:r={fps}",
                    f="lavfi",
                )
                .drawtext(
                    text=title_text,
                    fontsize=48,
                    fontcolor="white",
                    x="(w-text_w)/2",
                    y="(h-text_h)/2",
                )
                .output(output_path, vcodec="libx264", pix_fmt="yuv420p")
                .overwrite_output()
                .run(quiet=True)
            )

            return output_path
        except ImportError:
            raise VideoCompositorError(
                "ffmpeg-python is required for FFmpegRenderer"
            )

    def combine_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        video_codec: str,
        audio_codec: str,
    ) -> str:
        """Combine video and audio using FFmpeg."""
        try:
            import ffmpeg

            video = ffmpeg.input(video_path)
            audio = ffmpeg.input(audio_path)

            codec_map = {"h264": "libx264", "aac": "aac"}
            v_codec = codec_map.get(video_codec, video_codec)
            a_codec = codec_map.get(audio_codec, audio_codec)

            (
                ffmpeg.output(
                    video, audio, output_path,
                    vcodec=v_codec,
                    acodec=a_codec,
                    shortest=None,
                )
                .overwrite_output()
                .run(quiet=True)
            )

            return output_path
        except ImportError:
            raise VideoCompositorError(
                "ffmpeg-python is required for FFmpegRenderer"
            )

    def trim_video(
        self,
        input_path: str,
        output_path: str,
        max_duration_seconds: float,
        fade_out_seconds: float,
    ) -> str:
        """Trim video with fade-out using FFmpeg."""
        try:
            import ffmpeg

            fade_start = max_duration_seconds - fade_out_seconds

            (
                ffmpeg.input(input_path, t=max_duration_seconds)
                .filter("fade", type="out", start_time=fade_start,
                        duration=fade_out_seconds)
                .output(output_path, vcodec="libx264", pix_fmt="yuv420p")
                .overwrite_output()
                .run(quiet=True)
            )

            return output_path
        except ImportError:
            raise VideoCompositorError(
                "ffmpeg-python is required for FFmpegRenderer"
            )

    def get_video_duration(self, video_path: str) -> float:
        """Get video duration using FFmpeg probe."""
        try:
            import ffmpeg

            probe = ffmpeg.probe(video_path)
            duration = float(probe["format"]["duration"])
            return duration
        except ImportError:
            raise VideoCompositorError(
                "ffmpeg-python is required for FFmpegRenderer"
            )

    def concatenate_videos(
        self,
        video_paths: List[str],
        output_path: str,
    ) -> str:
        """Concatenate videos using FFmpeg."""
        try:
            import ffmpeg

            list_path = output_path + ".concat.txt"
            with open(list_path, "w") as f:
                for vp in video_paths:
                    f.write(f"file '{os.path.abspath(vp)}'\n")

            (
                ffmpeg.input(list_path, format="concat", safe=0)
                .output(output_path, c="copy")
                .overwrite_output()
                .run(quiet=True)
            )

            if os.path.exists(list_path):
                os.remove(list_path)

            return output_path
        except ImportError:
            raise VideoCompositorError(
                "ffmpeg-python is required for FFmpegRenderer"
            )


# ---------------------------------------------------------------------------
# MockRenderer (for testing without FFmpeg)
# ---------------------------------------------------------------------------


class MockRenderer:
    """Mock VideoRenderer that creates placeholder files with metadata.

    Stores video metadata as JSON inside placeholder files so that tests
    can verify the compositor's logic (duration enforcement, transitions,
    title cards) without requiring FFmpeg.

    Each "video" file is a JSON document containing metadata about what
    the real renderer would have produced.
    """

    def _write_mock_video(
        self,
        output_path: str,
        metadata: Dict[str, Any],
    ) -> str:
        """Write a mock video file containing JSON metadata."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=2)
        return output_path

    def _read_mock_video(self, video_path: str) -> Dict[str, Any]:
        """Read metadata from a mock video file."""
        try:
            with open(video_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def encode_frames_to_video(
        self,
        frame_paths: List[str],
        output_path: str,
        fps: int,
        width: int,
        height: int,
    ) -> str:
        """Create a mock video from frame paths."""
        num_frames = len(frame_paths)
        duration = num_frames / fps if fps > 0 else 0.0
        metadata = {
            "type": "scene_video",
            "num_frames": num_frames,
            "fps": fps,
            "width": width,
            "height": height,
            "duration_seconds": duration,
            "format": "mp4",
            "video_codec": "h264",
            "audio_codec": "none",
        }
        return self._write_mock_video(output_path, metadata)

    def apply_transition(
        self,
        video_a_path: str,
        video_b_path: str,
        output_path: str,
        transition_type: str,
        duration_seconds: float,
    ) -> str:
        """Create a mock video with transition metadata."""
        meta_a = self._read_mock_video(video_a_path)
        meta_b = self._read_mock_video(video_b_path)
        dur_a = meta_a.get("duration_seconds", 0.0)
        dur_b = meta_b.get("duration_seconds", 0.0)
        # Transition overlaps by duration_seconds
        total_duration = dur_a + dur_b - duration_seconds
        metadata = {
            "type": "transition_video",
            "transition_type": transition_type,
            "transition_duration": duration_seconds,
            "duration_seconds": max(total_duration, 0.0),
            "fps": meta_a.get("fps", DEFAULT_FPS),
            "width": meta_a.get("width", DEFAULT_WIDTH),
            "height": meta_a.get("height", DEFAULT_HEIGHT),
            "format": "mp4",
            "video_codec": "h264",
            "audio_codec": meta_a.get("audio_codec", "none"),
        }
        return self._write_mock_video(output_path, metadata)

    def render_title_card(
        self,
        title_text: str,
        output_path: str,
        duration_seconds: float,
        width: int,
        height: int,
        fps: int,
    ) -> str:
        """Create a mock title card video."""
        metadata = {
            "type": "title_card",
            "title_text": title_text,
            "duration_seconds": duration_seconds,
            "fps": fps,
            "width": width,
            "height": height,
            "format": "mp4",
            "video_codec": "h264",
            "audio_codec": "none",
        }
        return self._write_mock_video(output_path, metadata)

    def combine_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        video_codec: str,
        audio_codec: str,
    ) -> str:
        """Create a mock combined video+audio file."""
        video_meta = self._read_mock_video(video_path)
        metadata = {
            "type": "combined_video",
            "duration_seconds": video_meta.get("duration_seconds", 0.0),
            "fps": video_meta.get("fps", DEFAULT_FPS),
            "width": video_meta.get("width", DEFAULT_WIDTH),
            "height": video_meta.get("height", DEFAULT_HEIGHT),
            "format": "mp4",
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            "has_audio": True,
        }
        return self._write_mock_video(output_path, metadata)

    def trim_video(
        self,
        input_path: str,
        output_path: str,
        max_duration_seconds: float,
        fade_out_seconds: float,
    ) -> str:
        """Create a mock trimmed video."""
        input_meta = self._read_mock_video(input_path)
        original_duration = input_meta.get("duration_seconds", 0.0)
        trimmed_duration = min(original_duration, max_duration_seconds)
        metadata = dict(input_meta)
        metadata["type"] = "trimmed_video"
        metadata["duration_seconds"] = trimmed_duration
        metadata["original_duration"] = original_duration
        metadata["fade_out_seconds"] = fade_out_seconds
        metadata["was_trimmed"] = original_duration > max_duration_seconds
        return self._write_mock_video(output_path, metadata)

    def get_video_duration(self, video_path: str) -> float:
        """Get duration from mock video metadata."""
        meta = self._read_mock_video(video_path)
        return meta.get("duration_seconds", 0.0)

    def concatenate_videos(
        self,
        video_paths: List[str],
        output_path: str,
    ) -> str:
        """Create a mock concatenated video."""
        total_duration = 0.0
        fps = DEFAULT_FPS
        width = DEFAULT_WIDTH
        height = DEFAULT_HEIGHT
        audio_codec = "none"
        for vp in video_paths:
            meta = self._read_mock_video(vp)
            total_duration += meta.get("duration_seconds", 0.0)
            fps = meta.get("fps", fps)
            width = meta.get("width", width)
            height = meta.get("height", height)
            audio_codec = meta.get("audio_codec", audio_codec)
        metadata = {
            "type": "concatenated_video",
            "num_segments": len(video_paths),
            "duration_seconds": total_duration,
            "fps": fps,
            "width": width,
            "height": height,
            "format": "mp4",
            "video_codec": "h264",
            "audio_codec": audio_codec,
        }
        return self._write_mock_video(output_path, metadata)


# ---------------------------------------------------------------------------
# VideoCompositor (Tasks 8.1 - 8.5)
# ---------------------------------------------------------------------------


class VideoCompositor:
    """Combines animation frames and audio into final video.

    The compositor orchestrates the video rendering pipeline:
    1. Encodes frame sequences into video streams per scene (Task 8.1)
    2. Applies visual transitions between scenes (Task 8.2)
    3. Overlays title card at the beginning (Task 8.3)
    4. Combines video stream with audio track (Task 8.4)
    5. Enforces duration constraints (110-130s) (Task 8.5)

    All rendering operations are delegated to a VideoRenderer, which
    can be swapped for testing (MockRenderer) or production (FFmpegRenderer).

    Args:
        output_config: OutputConfig with format, codec settings.
        animation_config: AnimationConfig with resolution, fps settings.
        renderer: An object implementing the VideoRenderer protocol.
            If None, uses FFmpegRenderer.
        transition_duration: Duration of transitions between scenes in seconds.
        title_card_duration: Duration of the title card in seconds (3-5s).
        min_duration: Minimum allowed video duration in seconds.
        max_duration: Maximum allowed video duration in seconds.
        fade_out_seconds: Duration of fade-out when trimming in seconds.
    """

    def __init__(
        self,
        output_config: OutputConfig,
        animation_config: AnimationConfig,
        renderer: Optional[Any] = None,
        transition_duration: float = DEFAULT_TRANSITION_DURATION,
        title_card_duration: float = TITLE_CARD_DURATION_SECONDS,
        min_duration: float = MIN_DURATION_SECONDS,
        max_duration: float = MAX_DURATION_SECONDS,
        fade_out_seconds: float = 2.0,
    ):
        self._output_config = output_config
        self._animation_config = animation_config
        self._renderer = renderer or FFmpegRenderer()
        self._transition_duration = transition_duration
        self._title_card_duration = max(
            MIN_TITLE_CARD_SECONDS,
            min(MAX_TITLE_CARD_SECONDS, title_card_duration),
        )
        self._min_duration = min_duration
        self._max_duration = max_duration
        self._fade_out_seconds = fade_out_seconds

    @property
    def width(self) -> int:
        """Configured video width."""
        return self._animation_config.resolution[0]

    @property
    def height(self) -> int:
        """Configured video height."""
        return self._animation_config.resolution[1]

    @property
    def fps(self) -> int:
        """Configured frames per second."""
        return self._animation_config.fps

    @property
    def transition_duration(self) -> float:
        """Transition duration in seconds."""
        return self._transition_duration

    @property
    def title_card_duration(self) -> float:
        """Title card duration in seconds."""
        return self._title_card_duration

    @property
    def min_duration(self) -> float:
        """Minimum allowed video duration in seconds."""
        return self._min_duration

    @property
    def max_duration(self) -> float:
        """Maximum allowed video duration in seconds."""
        return self._max_duration

    def encode_scene(
        self,
        frame_paths: List[str],
        output_path: str,
    ) -> str:
        """Encode a sequence of frames into a video stream for one scene.

        Args:
            frame_paths: Ordered list of frame image file paths.
            output_path: Path for the output video file.

        Returns:
            Path to the encoded scene video.

        Raises:
            VideoCompositorError: If encoding fails.
        """
        if not frame_paths:
            raise VideoCompositorError("No frames provided for scene encoding")

        return self._renderer.encode_frames_to_video(
            frame_paths=frame_paths,
            output_path=output_path,
            fps=self.fps,
            width=self.width,
            height=self.height,
        )

    def apply_scene_transitions(
        self,
        scene_video_paths: List[str],
        output_dir: str,
        transition_type: str = "crossfade",
    ) -> str:
        """Apply visual transitions between scene videos.

        Concatenates scene videos with crossfade/dissolve transitions
        of configurable duration.

        Args:
            scene_video_paths: Ordered list of scene video file paths.
            output_dir: Directory for intermediate and output files.
            transition_type: Type of transition ("crossfade" or "dissolve").

        Returns:
            Path to the combined video with transitions.

        Raises:
            VideoCompositorError: If no scene videos are provided.
        """
        if not scene_video_paths:
            raise VideoCompositorError("No scene videos to combine")

        if len(scene_video_paths) == 1:
            return scene_video_paths[0]

        # Apply transitions pairwise
        current_path = scene_video_paths[0]
        for i, next_path in enumerate(scene_video_paths[1:], start=1):
            transition_output = os.path.join(
                output_dir, f"transition_{i:03d}.mp4"
            )
            current_path = self._renderer.apply_transition(
                video_a_path=current_path,
                video_b_path=next_path,
                output_path=transition_output,
                transition_type=transition_type,
                duration_seconds=self._transition_duration,
            )

        return current_path

    def create_title_card(
        self,
        script: EpisodeScript,
        output_path: str,
    ) -> str:
        """Render a title card for the episode.

        Displays the Kanda name and episode number for the configured
        duration (3-5 seconds).

        Args:
            script: The episode script (for kanda name and episode number).
            output_path: Path for the output title card video.

        Returns:
            Path to the title card video.
        """
        title_card = TitleCard(
            kanda_name=script.kanda,
            episode_number=script.episode_number,
        )

        return self._renderer.render_title_card(
            title_text=title_card.text,
            output_path=output_path,
            duration_seconds=self._title_card_duration,
            width=self.width,
            height=self.height,
            fps=self.fps,
        )

    def combine_with_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
    ) -> str:
        """Combine video stream with audio track.

        Encodes to MP4 with H.264 video and AAC audio.

        Args:
            video_path: Path to the video file.
            audio_path: Path to the audio file (WAV).
            output_path: Path for the output combined file.

        Returns:
            Path to the combined output file.
        """
        return self._renderer.combine_video_audio(
            video_path=video_path,
            audio_path=audio_path,
            output_path=output_path,
            video_codec=self._output_config.video_codec,
            audio_codec=self._output_config.audio_codec,
        )

    def enforce_duration(
        self,
        video_path: str,
        output_path: str,
    ) -> Tuple[str, bool]:
        """Enforce video duration constraints (110-130 seconds).

        If the video exceeds max_duration, trims the final scene with
        a fade-out effect and logs a warning.

        Args:
            video_path: Path to the video file to check.
            output_path: Path for the trimmed output (if needed).

        Returns:
            Tuple of (output_path, was_trimmed). If no trimming was needed,
            returns the original video_path with was_trimmed=False.
        """
        duration = self._renderer.get_video_duration(video_path)

        if duration > self._max_duration:
            logger.warning(
                "Video duration %.2fs exceeds maximum %.2fs. "
                "Trimming final scene with fade-out.",
                duration,
                self._max_duration,
            )
            trimmed_path = self._renderer.trim_video(
                input_path=video_path,
                output_path=output_path,
                max_duration_seconds=self._max_duration,
                fade_out_seconds=self._fade_out_seconds,
            )
            return trimmed_path, True

        if duration < self._min_duration:
            logger.warning(
                "Video duration %.2fs is below minimum %.2fs.",
                duration,
                self._min_duration,
            )

        return video_path, False

    def calculate_total_duration(
        self,
        scene_durations: List[float],
        title_card_duration: Optional[float] = None,
    ) -> float:
        """Calculate the expected total video duration.

        Accounts for scene durations, transitions between scenes,
        and the title card.

        Args:
            scene_durations: List of scene durations in seconds.
            title_card_duration: Title card duration. If None, uses
                the configured default.

        Returns:
            Expected total duration in seconds.
        """
        if not scene_durations:
            return 0.0

        tc_dur = title_card_duration if title_card_duration is not None else self._title_card_duration

        # Sum of all scene durations
        total = sum(scene_durations)

        # Add title card duration
        total += tc_dur

        # Subtract transition overlaps (one transition between each pair of scenes,
        # plus one transition between title card and first scene)
        num_transitions = len(scene_durations)  # title->scene1, scene1->scene2, ...
        total -= num_transitions * self._transition_duration

        return max(total, 0.0)

    def compose_video(
        self,
        script: EpisodeScript,
        scene_frame_paths: List[List[str]],
        audio_path: str,
        output_path: str,
        work_dir: Optional[str] = None,
    ) -> VideoMetadata:
        """Compose the final video from frames and audio.

        Full pipeline:
        1. Encode each scene's frames into a video stream
        2. Render title card
        3. Concatenate title card + scene videos with transitions
        4. Combine with audio track
        5. Enforce duration constraints

        Args:
            script: The episode script.
            scene_frame_paths: List of frame path lists, one per scene.
            audio_path: Path to the final mixed audio file (WAV).
            output_path: Path for the final output video file.
            work_dir: Working directory for intermediate files. If None,
                creates a temporary directory.

        Returns:
            VideoMetadata describing the produced video.

        Raises:
            VideoCompositorError: If composition fails.
        """
        if not scene_frame_paths:
            raise VideoCompositorError("No scene frames provided")

        if work_dir is None:
            work_dir = tempfile.mkdtemp(prefix="ramayan_video_")
        os.makedirs(work_dir, exist_ok=True)

        # Step 1: Encode each scene's frames into video (Task 8.1)
        scene_video_paths: List[str] = []
        for i, frame_paths in enumerate(scene_frame_paths):
            scene_output = os.path.join(work_dir, f"scene_{i:03d}.mp4")
            logger.info(
                "Encoding scene %d: %d frames", i + 1, len(frame_paths)
            )
            self.encode_scene(frame_paths, scene_output)
            scene_video_paths.append(scene_output)

        # Step 2: Render title card (Task 8.3)
        title_card_path = os.path.join(work_dir, "title_card.mp4")
        logger.info(
            "Rendering title card: %s - Episode %d (%.1fs)",
            script.kanda,
            script.episode_number,
            self._title_card_duration,
        )
        self.create_title_card(script, title_card_path)

        # Step 3: Apply transitions between all segments (Task 8.2)
        all_video_paths = [title_card_path] + scene_video_paths
        logger.info(
            "Applying transitions between %d segments (%.1fs each)",
            len(all_video_paths),
            self._transition_duration,
        )
        combined_video_path = self.apply_scene_transitions(
            all_video_paths,
            output_dir=work_dir,
            transition_type="crossfade",
        )

        # Step 4: Combine with audio (Task 8.4)
        muxed_path = os.path.join(work_dir, "muxed.mp4")
        logger.info("Combining video with audio track")
        self.combine_with_audio(combined_video_path, audio_path, muxed_path)

        # Step 5: Enforce duration (Task 8.5)
        trimmed_path = os.path.join(work_dir, "trimmed.mp4")
        final_path, was_trimmed = self.enforce_duration(muxed_path, trimmed_path)

        # Copy/move to final output path if needed
        if final_path != output_path:
            import shutil
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            shutil.copy2(final_path, output_path)

        # Get final duration
        final_duration = self._renderer.get_video_duration(output_path)

        metadata = VideoMetadata(
            file_path=output_path,
            format=self._output_config.format,
            video_codec=self._output_config.video_codec,
            audio_codec=self._output_config.audio_codec,
            width=self.width,
            height=self.height,
            fps=self.fps,
            duration_seconds=final_duration,
            was_trimmed=was_trimmed,
        )

        logger.info(
            "Video composition complete: %s (%.2fs, trimmed=%s)",
            output_path,
            final_duration,
            was_trimmed,
        )

        return metadata
