"""Audio Engine for the Ramayan Video Generator.

Selects background music based on scene mood, mixes narration with music
applying volume ducking, places sound effects at specified timestamps,
applies crossfade transitions between scenes, and exports final audio
in WAV format at 44100 Hz, 16-bit.

Uses pydub for audio processing.

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
"""

import io
import logging
import os
import struct
import wave
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pydub import AudioSegment as PydubSegment

from src.config_loader import AudioConfig
from src.episode_script import EpisodeScript, Scene
from src.narration_engine import EpisodeAudio, SceneAudio

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TARGET_SAMPLE_RATE = 44100
TARGET_BIT_DEPTH = 16  # sample width in bits
TARGET_SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
TARGET_CHANNELS = 2  # stereo

DEFAULT_CROSSFADE_SECONDS = 0.75
MIN_CROSSFADE_SECONDS = 0.5
MAX_CROSSFADE_SECONDS = 1.0


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AudioEngineError(Exception):
    """Raised when the AudioEngine encounters an error."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class MusicClip:
    """A background music clip tagged by mood."""

    name: str
    mood: str
    file_path: str


@dataclass
class SFXClip:
    """A sound effect clip."""

    name: str
    file_path: str


@dataclass
class MusicLibrary:
    """Library of background music clips organized by mood."""

    clips: List[MusicClip] = field(default_factory=list)
    _mood_index: Dict[str, List[MusicClip]] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self) -> None:
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self._mood_index = {}
        for clip in self.clips:
            mood = clip.mood.lower()
            if mood not in self._mood_index:
                self._mood_index[mood] = []
            self._mood_index[mood].append(clip)

    def add_clip(self, clip: MusicClip) -> None:
        """Add a clip to the library."""
        self.clips.append(clip)
        mood = clip.mood.lower()
        if mood not in self._mood_index:
            self._mood_index[mood] = []
        self._mood_index[mood].append(clip)

    def get_clips_for_mood(self, mood: str) -> List[MusicClip]:
        """Return clips matching the given mood tag.

        Uses fuzzy matching: checks if any word in the mood string
        matches a mood tag in the library. Falls back to all clips
        if no match is found.
        """
        mood_lower = mood.lower()

        # Try exact match first
        matches = self._mood_index.get(mood_lower, [])
        if matches:
            return matches

        # Fuzzy match: check if any mood keyword is contained in the mood string
        for mood_tag, clips in self._mood_index.items():
            if mood_tag in mood_lower:
                return clips

        # Fallback: return all clips if no mood match
        return list(self.clips) if self.clips else []

    @property
    def moods(self) -> List[str]:
        """Return all available mood tags."""
        return list(self._mood_index.keys())


@dataclass
class SFXLibrary:
    """Library of sound effect clips."""

    clips: List[SFXClip] = field(default_factory=list)
    _name_index: Dict[str, SFXClip] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self) -> None:
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self._name_index = {}
        for clip in self.clips:
            self._name_index[clip.name.lower()] = clip

    def add_clip(self, clip: SFXClip) -> None:
        """Add a clip to the library."""
        self.clips.append(clip)
        self._name_index[clip.name.lower()] = clip

    def get_clip(self, name: str) -> Optional[SFXClip]:
        """Return a clip by name (case-insensitive)."""
        return self._name_index.get(name.lower())


# ---------------------------------------------------------------------------
# Audio Utility Functions
# ---------------------------------------------------------------------------


def generate_silent_pydub(duration_ms: int) -> PydubSegment:
    """Generate a silent pydub AudioSegment of the specified duration.

    Args:
        duration_ms: Duration in milliseconds.

    Returns:
        A silent PydubSegment at the target sample rate and bit depth.
    """
    return PydubSegment.silent(
        duration=duration_ms,
        frame_rate=TARGET_SAMPLE_RATE,
    )


def wav_bytes_to_pydub(wav_data: bytes) -> PydubSegment:
    """Convert WAV bytes to a pydub AudioSegment.

    Args:
        wav_data: WAV format audio bytes.

    Returns:
        A PydubSegment.
    """
    buf = io.BytesIO(wav_data)
    return PydubSegment.from_wav(buf)


def pydub_to_wav_bytes(segment: PydubSegment) -> bytes:
    """Convert a pydub AudioSegment to WAV bytes.

    Args:
        segment: A PydubSegment.

    Returns:
        WAV format audio bytes.
    """
    buf = io.BytesIO()
    segment.export(buf, format="wav")
    return buf.getvalue()


def normalize_segment(
    segment: PydubSegment,
    sample_rate: int = TARGET_SAMPLE_RATE,
    sample_width: int = TARGET_SAMPLE_WIDTH,
    channels: int = TARGET_CHANNELS,
) -> PydubSegment:
    """Normalize a pydub segment to target sample rate, bit depth, and channels.

    Args:
        segment: The audio segment to normalize.
        sample_rate: Target sample rate in Hz.
        sample_width: Target sample width in bytes.
        channels: Target number of channels.

    Returns:
        Normalized PydubSegment.
    """
    if segment.frame_rate != sample_rate:
        segment = segment.set_frame_rate(sample_rate)
    if segment.sample_width != sample_width:
        segment = segment.set_sample_width(sample_width)
    if segment.channels != channels:
        segment = segment.set_channels(channels)
    return segment


def generate_tone_pydub(
    frequency: float = 440.0,
    duration_ms: int = 1000,
    volume_dbfs: float = -20.0,
    sample_rate: int = TARGET_SAMPLE_RATE,
) -> PydubSegment:
    """Generate a sine wave tone as a pydub AudioSegment.

    Useful for testing and as placeholder music/sfx.

    Args:
        frequency: Tone frequency in Hz.
        duration_ms: Duration in milliseconds.
        volume_dbfs: Volume in dBFS.
        sample_rate: Sample rate in Hz.

    Returns:
        A PydubSegment containing the tone.
    """
    import math

    num_samples = int(sample_rate * duration_ms / 1000)
    # Generate 16-bit PCM samples
    max_amplitude = 32767
    # Calculate amplitude from dBFS (0 dBFS = max amplitude)
    amplitude = int(max_amplitude * (10 ** (volume_dbfs / 20.0)))

    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(amplitude * math.sin(2 * math.pi * frequency * t))
        value = max(-32768, min(32767, value))
        samples.append(struct.pack("<h", value))

    raw_data = b"".join(samples)

    # Create pydub segment from raw data
    segment = PydubSegment(
        data=raw_data,
        sample_width=2,
        frame_rate=sample_rate,
        channels=1,
    )
    return segment


# ---------------------------------------------------------------------------
# Music Selection (Task 7.1)
# ---------------------------------------------------------------------------


def load_music_library(music_path: str) -> MusicLibrary:
    """Load music clips from the music library directory.

    Expects files named with mood tags, e.g., `devotional_track1.wav`.
    The mood is extracted from the filename prefix before the first underscore.

    Args:
        music_path: Path to the music library directory.

    Returns:
        A MusicLibrary with loaded clips.
    """
    library = MusicLibrary()

    if not os.path.isdir(music_path):
        logger.warning("Music library path does not exist: %s", music_path)
        return library

    for filename in sorted(os.listdir(music_path)):
        if filename.startswith("."):
            continue
        filepath = os.path.join(music_path, filename)
        if not os.path.isfile(filepath):
            continue

        # Extract mood from filename: "devotional_track1.wav" -> "devotional"
        name_without_ext = os.path.splitext(filename)[0]
        parts = name_without_ext.split("_")
        mood = parts[0] if parts else "general"

        clip = MusicClip(name=name_without_ext, mood=mood, file_path=filepath)
        library.add_clip(clip)
        logger.debug("Loaded music clip: %s (mood: %s)", filename, mood)

    logger.info(
        "Loaded %d music clips with moods: %s",
        len(library.clips),
        library.moods,
    )
    return library


def load_sfx_library(sfx_path: str) -> SFXLibrary:
    """Load sound effect clips from the SFX library directory.

    Clip names are derived from filenames without extension.

    Args:
        sfx_path: Path to the SFX library directory.

    Returns:
        An SFXLibrary with loaded clips.
    """
    library = SFXLibrary()

    if not os.path.isdir(sfx_path):
        logger.warning("SFX library path does not exist: %s", sfx_path)
        return library

    for filename in sorted(os.listdir(sfx_path)):
        if filename.startswith("."):
            continue
        filepath = os.path.join(sfx_path, filename)
        if not os.path.isfile(filepath):
            continue

        name = os.path.splitext(filename)[0]
        clip = SFXClip(name=name, file_path=filepath)
        library.add_clip(clip)
        logger.debug("Loaded SFX clip: %s", filename)

    logger.info("Loaded %d SFX clips", len(library.clips))
    return library


def select_music_for_mood(
    library: MusicLibrary, mood: str, exclude_clip: Optional[MusicClip] = None,
) -> Optional[MusicClip]:
    """Select a random music clip matching the given mood.

    Randomizes selection within matching clips for variety across scenes.
    If exclude_clip is provided (e.g. the previous scene's track), avoids
    picking the same one for consecutive-scene variety.

    Args:
        library: The music library to search.
        mood: The mood tag to match.
        exclude_clip: A clip to avoid (for scene-to-scene variety).

    Returns:
        A MusicClip or None.
    """
    import random

    clips = library.get_clips_for_mood(mood)
    if not clips:
        return None

    # If we have multiple options, try to avoid the excluded clip
    if exclude_clip and len(clips) > 1:
        candidates = [c for c in clips if c.file_path != exclude_clip.file_path]
        if candidates:
            return random.choice(candidates)

    return random.choice(clips)


# ---------------------------------------------------------------------------
# Audio Mixing with Volume Ducking (Task 7.2)
# ---------------------------------------------------------------------------


def mix_narration_with_music(
    narration: PydubSegment,
    music: PydubSegment,
    narration_boost_db: float = 6.0,
) -> PydubSegment:
    """Mix narration audio with background music, applying volume ducking.

    Ensures the narration is at least `narration_boost_db` dB louder than
    the background music during speech segments.

    The approach:
    1. Measure the narration level (dBFS).
    2. Adjust music volume so it is at least narration_boost_db below narration.
    3. Overlay the two tracks.

    Args:
        narration: The narration audio segment.
        music: The background music segment.
        narration_boost_db: Minimum dB difference (narration louder than music).

    Returns:
        Mixed PydubSegment with narration over ducked music.
    """
    # Normalize both to same format
    narration = normalize_segment(narration)
    music = normalize_segment(music)

    # Match music length to narration length
    if len(music) < len(narration):
        # Loop music to cover narration duration
        loops_needed = (len(narration) // len(music)) + 1
        music = music * loops_needed
    music = music[: len(narration)]

    # Apply volume ducking: ensure music is at least narration_boost_db
    # quieter than narration
    narration_level = narration.dBFS
    music_level = music.dBFS

    if narration_level == float("-inf") or music_level == float("-inf"):
        # One of the tracks is silent, just overlay
        return narration.overlay(music)

    # Calculate required music level
    target_music_level = narration_level - narration_boost_db
    level_adjustment = target_music_level - music_level

    if level_adjustment < 0:
        # Music is too loud, reduce it
        music = music + level_adjustment
    # If music is already quiet enough, leave it as is

    return narration.overlay(music)


# ---------------------------------------------------------------------------
# Sound Effect Placement (Task 7.3)
# ---------------------------------------------------------------------------


def place_sound_effects(
    base_audio: PydubSegment,
    sfx_segments: List[Tuple[int, PydubSegment]],
) -> PydubSegment:
    """Overlay sound effects onto the base audio at specified timestamps.

    Args:
        base_audio: The base audio track to add effects to.
        sfx_segments: List of (timestamp_ms, sfx_audio) tuples.

    Returns:
        PydubSegment with sound effects overlaid.
    """
    result = base_audio
    for timestamp_ms, sfx in sfx_segments:
        if timestamp_ms < 0:
            logger.warning("Negative SFX timestamp %d ms, skipping", timestamp_ms)
            continue
        if timestamp_ms >= len(result):
            logger.warning(
                "SFX timestamp %d ms exceeds audio length %d ms, skipping",
                timestamp_ms,
                len(result),
            )
            continue
        # Normalize SFX to match base audio format
        sfx = normalize_segment(sfx)
        result = result.overlay(sfx, position=timestamp_ms)

    return result


# ---------------------------------------------------------------------------
# Crossfade Transitions (Task 7.4)
# ---------------------------------------------------------------------------


def apply_crossfade(
    segments: List[PydubSegment],
    crossfade_ms: int,
) -> PydubSegment:
    """Concatenate audio segments with crossfade transitions.

    Args:
        segments: List of PydubSegments to concatenate.
        crossfade_ms: Crossfade duration in milliseconds.

    Returns:
        A single PydubSegment with crossfade transitions applied.

    Raises:
        AudioEngineError: If no segments are provided.
    """
    if not segments:
        raise AudioEngineError("No audio segments to concatenate")

    if len(segments) == 1:
        return segments[0]

    # Clamp crossfade to valid range
    crossfade_ms = max(
        int(MIN_CROSSFADE_SECONDS * 1000),
        min(int(MAX_CROSSFADE_SECONDS * 1000), crossfade_ms),
    )

    result = segments[0]
    for seg in segments[1:]:
        # Ensure crossfade doesn't exceed either segment's length
        effective_crossfade = min(crossfade_ms, len(result), len(seg))
        if effective_crossfade > 0:
            result = result.append(seg, crossfade=effective_crossfade)
        else:
            result = result + seg

    return result


# ---------------------------------------------------------------------------
# Final Audio Export (Task 7.5)
# ---------------------------------------------------------------------------


def export_final_audio(
    audio: PydubSegment,
    output_path: str,
) -> str:
    """Export the final mixed audio as WAV at 44100 Hz, 16-bit.

    Args:
        audio: The final mixed audio segment.
        output_path: Path to write the output WAV file.

    Returns:
        The output file path.

    Raises:
        AudioEngineError: If export fails.
    """
    # Normalize to target format
    audio = normalize_segment(audio)

    try:
        audio.export(
            output_path,
            format="wav",
            parameters=["-ar", str(TARGET_SAMPLE_RATE)],
        )
    except Exception as e:
        # Fallback: export using wave module directly
        try:
            _export_wav_raw(audio, output_path)
        except Exception as e2:
            raise AudioEngineError(f"Failed to export audio: {e2}")

    return output_path


def _export_wav_raw(audio: PydubSegment, output_path: str) -> None:
    """Export audio to WAV using the wave module directly.

    This is a fallback when pydub's export fails (e.g., no ffmpeg).
    """
    audio = normalize_segment(audio)
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(audio.channels)
        wf.setsampwidth(audio.sample_width)
        wf.setframerate(audio.frame_rate)
        wf.writeframes(audio.raw_data)


def export_to_wav_bytes(audio: PydubSegment) -> bytes:
    """Export audio to WAV bytes at 44100 Hz, 16-bit.

    Args:
        audio: The audio segment to export.

    Returns:
        WAV format bytes.
    """
    audio = normalize_segment(audio)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(audio.channels)
        wf.setsampwidth(audio.sample_width)
        wf.setframerate(audio.frame_rate)
        wf.writeframes(audio.raw_data)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# AudioEngine (Tasks 7.1 - 7.5)
# ---------------------------------------------------------------------------


class AudioEngine:
    """Mixes narration, background music, and sound effects into a final audio track.

    The engine:
    1. Selects background music per scene based on mood tags (Task 7.1)
    2. Mixes narration with music applying volume ducking (Task 7.2)
    3. Places sound effects at specified timestamps (Task 7.3)
    4. Applies crossfade transitions between scenes (Task 7.4)
    5. Exports final audio as WAV at 44100 Hz, 16-bit (Task 7.5)

    Args:
        config: AudioConfig with library paths and mixing parameters.
        music_library: Optional pre-loaded MusicLibrary. If None, loads
            from config.music_library_path.
        sfx_library: Optional pre-loaded SFXLibrary. If None, loads
            from config.sfx_library_path.
    """

    def __init__(
        self,
        config: AudioConfig,
        music_library: Optional[MusicLibrary] = None,
        sfx_library: Optional[SFXLibrary] = None,
    ):
        self._config = config
        self._crossfade_ms = int(
            max(
                MIN_CROSSFADE_SECONDS,
                min(MAX_CROSSFADE_SECONDS, config.crossfade_seconds),
            )
            * 1000
        )

        if music_library is not None:
            self._music_library = music_library
        else:
            self._music_library = load_music_library(config.music_library_path)

        if sfx_library is not None:
            self._sfx_library = sfx_library
        else:
            self._sfx_library = load_sfx_library(config.sfx_library_path)

    @property
    def music_library(self) -> MusicLibrary:
        """The loaded music library."""
        return self._music_library

    @property
    def sfx_library(self) -> SFXLibrary:
        """The loaded SFX library."""
        return self._sfx_library

    @property
    def crossfade_ms(self) -> int:
        """The crossfade duration in milliseconds."""
        return self._crossfade_ms

    def select_music_for_scene(
        self, scene: Scene, exclude_clip: Optional[MusicClip] = None
    ) -> Optional[MusicClip]:
        """Select background music for a scene based on its mood tag.

        Args:
            scene: The scene to select music for.
            exclude_clip: Previous scene's clip to avoid repetition.

        Returns:
            A MusicClip or None if no music is available.
        """
        return select_music_for_mood(self._music_library, scene.mood, exclude_clip)

    def _load_music_audio(self, clip: MusicClip) -> PydubSegment:
        """Load a music clip as a pydub AudioSegment.

        Falls back to generating a placeholder tone if the file
        cannot be loaded.
        """
        try:
            audio = PydubSegment.from_file(clip.file_path)
            return normalize_segment(audio)
        except Exception:
            logger.warning(
                "Could not load music file %s, using placeholder tone",
                clip.file_path,
            )
            return generate_tone_pydub(
                frequency=220.0, duration_ms=10000, volume_dbfs=-30.0
            )

    def _load_sfx_audio(self, clip: SFXClip) -> PydubSegment:
        """Load an SFX clip as a pydub AudioSegment.

        Falls back to generating a short placeholder tone if the file
        cannot be loaded.
        """
        try:
            audio = PydubSegment.from_file(clip.file_path)
            return normalize_segment(audio)
        except Exception:
            logger.warning(
                "Could not load SFX file %s, using placeholder tone",
                clip.file_path,
            )
            return generate_tone_pydub(
                frequency=880.0, duration_ms=500, volume_dbfs=-25.0
            )

    def _build_narration_track(
        self, scene_audio: SceneAudio
    ) -> PydubSegment:
        """Build a single narration track from all segments in a scene.

        Concatenates all narration and dialogue segments sequentially.

        Args:
            scene_audio: The SceneAudio containing narration segments.

        Returns:
            A PydubSegment of the combined narration.
        """
        if not scene_audio.segments:
            return generate_silent_pydub(1000)

        parts = []
        for segment in scene_audio.segments:
            audio = wav_bytes_to_pydub(segment.audio_data)
            audio = normalize_segment(audio)
            parts.append(audio)

        if not parts:
            return generate_silent_pydub(1000)

        combined = parts[0]
        for part in parts[1:]:
            combined = combined + part

        return combined

    def mix_scene(
        self,
        scene: Scene,
        scene_audio: SceneAudio,
        exclude_clip: Optional[MusicClip] = None,
    ) -> Tuple[PydubSegment, Optional[MusicClip]]:
        """Mix narration, music, and SFX for a single scene.

        Args:
            scene: The scene description (for mood and SFX info).
            scene_audio: The narration audio for the scene.
            exclude_clip: Previous scene's music clip to avoid repetition.

        Returns:
            Tuple of (mixed PydubSegment, music clip used or None).
        """
        # Build narration track
        narration_track = self._build_narration_track(scene_audio)

        # Select and load background music (avoiding previous scene's track)
        music_clip = self.select_music_for_scene(scene, exclude_clip=exclude_clip)
        if music_clip is not None:
            music_audio = self._load_music_audio(music_clip)
            # Mix narration with music (volume ducking)
            mixed = mix_narration_with_music(
                narration=narration_track,
                music=music_audio,
                narration_boost_db=float(self._config.narration_boost_db),
            )
        else:
            mixed = narration_track

        # Place sound effects
        sfx_segments: List[Tuple[int, PydubSegment]] = []
        if scene.sound_effects:
            scene_duration_ms = len(mixed)
            # Distribute SFX evenly across the scene duration
            num_sfx = len(scene.sound_effects)
            for i, sfx_name in enumerate(scene.sound_effects):
                sfx_clip = self._sfx_library.get_clip(sfx_name)
                if sfx_clip is not None:
                    sfx_audio = self._load_sfx_audio(sfx_clip)
                    # Place at evenly distributed timestamps
                    timestamp_ms = int(
                        (i / max(num_sfx, 1)) * scene_duration_ms
                    )
                    sfx_segments.append((timestamp_ms, sfx_audio))
                else:
                    logger.debug(
                        "SFX '%s' not found in library, skipping", sfx_name
                    )

        if sfx_segments:
            mixed = place_sound_effects(mixed, sfx_segments)

        return mixed, music_clip

    def mix_episode(
        self,
        script: EpisodeScript,
        episode_audio: EpisodeAudio,
    ) -> PydubSegment:
        """Mix all scenes of an episode with crossfade transitions.

        Args:
            script: The episode script.
            episode_audio: The narration audio for the episode.

        Returns:
            A single PydubSegment of the complete episode audio.

        Raises:
            AudioEngineError: If mixing fails.
        """
        if not script.scenes or not episode_audio.scene_audio:
            raise AudioEngineError("No scenes to mix")

        scene_tracks: List[PydubSegment] = []
        last_music_clip: Optional[MusicClip] = None

        for scene, scene_audio in zip(
            script.scenes, episode_audio.scene_audio
        ):
            logger.info(
                "Mixing scene %d (mood: %s)", scene.scene_number, scene.mood
            )
            mixed_scene, last_music_clip = self.mix_scene(
                scene, scene_audio, exclude_clip=last_music_clip
            )
            scene_tracks.append(mixed_scene)

        # Apply crossfade transitions between scenes
        final_audio = apply_crossfade(scene_tracks, self._crossfade_ms)

        logger.info(
            "Episode %d: mixed %d scenes, total duration %.2fs",
            script.episode_number,
            len(scene_tracks),
            len(final_audio) / 1000.0,
        )

        return final_audio

    def produce_episode_audio(
        self,
        script: EpisodeScript,
        episode_audio: EpisodeAudio,
        output_path: Optional[str] = None,
    ) -> PydubSegment:
        """Produce the final mixed audio for an episode.

        Mixes all scenes, applies transitions, normalizes to target
        format (44100 Hz, 16-bit), and optionally exports to file.

        Args:
            script: The episode script.
            episode_audio: The narration audio for the episode.
            output_path: Optional path to export the final WAV file.

        Returns:
            The final mixed PydubSegment.
        """
        final = self.mix_episode(script, episode_audio)

        # Normalize to target format
        final = normalize_segment(final)

        if output_path:
            export_final_audio(final, output_path)
            logger.info("Exported final audio to %s", output_path)

        return final
