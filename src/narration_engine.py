"""Narration Engine for the Ramayan Video Generator.

Generates spoken audio from narration text and character dialogue using
configurable TTS providers. Supports voice profile management, multiple
TTS backends via adapter pattern, and duration synchronization with
script timing cues.

Uses Protocol-based design for TTS providers to enable dependency
injection and testability.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
"""

import io
import logging
import struct
import wave
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from src.config_loader import NarrationConfig
from src.episode_script import EpisodeScript, Scene

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class NarrationEngineError(Exception):
    """Raised when the NarrationEngine encounters an error."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class AudioSegment:
    """A generated audio segment with metadata."""

    scene_number: int
    segment_type: str  # "narration" or "dialogue"
    character: Optional[str]  # None for narration, character name for dialogue
    text: str
    voice_id: str
    audio_data: bytes  # WAV format bytes
    duration_seconds: float
    speech_rate: float = 1.0


@dataclass
class SceneAudio:
    """All audio segments for a single scene."""

    scene_number: int
    segments: List[AudioSegment]
    total_duration_seconds: float = 0.0

    def __post_init__(self):
        if self.segments and self.total_duration_seconds == 0.0:
            self.total_duration_seconds = sum(
                s.duration_seconds for s in self.segments
            )


@dataclass
class EpisodeAudio:
    """All audio generated for an entire episode."""

    episode_number: int
    scene_audio: List[SceneAudio]
    total_duration_seconds: float = 0.0

    def __post_init__(self):
        if self.scene_audio and self.total_duration_seconds == 0.0:
            self.total_duration_seconds = sum(
                sa.total_duration_seconds for sa in self.scene_audio
            )


# ---------------------------------------------------------------------------
# TTS Provider Protocol (Task 6.3)
# ---------------------------------------------------------------------------


class TTSProvider(Protocol):
    """Protocol for text-to-speech synthesis backends.

    Concrete implementations adapt specific TTS services (Coqui TTS,
    Azure Speech, ElevenLabs) to this common interface.
    """

    def synthesize(
        self,
        text: str,
        voice_id: str,
        locale: str,
        speech_rate: float,
    ) -> bytes:
        """Generate audio bytes (WAV format) from text.

        Args:
            text: The text to synthesize into speech.
            voice_id: The voice profile identifier to use.
            locale: The language/locale code (e.g., "hi" for Hindi).
            speech_rate: Speech rate multiplier (1.0 = normal, >1.0 = faster).

        Returns:
            WAV format audio bytes.
        """
        ...


# ---------------------------------------------------------------------------
# WAV Utility Functions
# ---------------------------------------------------------------------------


def _generate_silent_wav(duration_seconds: float, sample_rate: int = 44100) -> bytes:
    """Generate silent WAV audio of the specified duration.

    Args:
        duration_seconds: Duration of silence in seconds.
        sample_rate: Audio sample rate in Hz.

    Returns:
        WAV format bytes containing silence.
    """
    num_samples = int(sample_rate * duration_seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)
    return buf.getvalue()


def get_wav_duration(wav_data: bytes) -> float:
    """Measure the duration of WAV audio data in seconds.

    Args:
        wav_data: WAV format audio bytes.

    Returns:
        Duration in seconds.

    Raises:
        NarrationEngineError: If the WAV data is invalid.
    """
    try:
        buf = io.BytesIO(wav_data)
        with wave.open(buf, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate == 0:
                return 0.0
            return frames / rate
    except Exception as e:
        raise NarrationEngineError(f"Failed to measure WAV duration: {e}")


# ---------------------------------------------------------------------------
# TTS Provider Adapters (Task 6.3)
# ---------------------------------------------------------------------------


class CoquiTTSAdapter:
    """TTS adapter for Coqui TTS.

    Placeholder implementation that generates silent WAV audio of
    appropriate duration for testing. In production, this would call
    the Coqui TTS library.
    """

    # Approximate words per second for duration estimation
    _WORDS_PER_SECOND = 2.5

    def synthesize(
        self,
        text: str,
        voice_id: str,
        locale: str,
        speech_rate: float,
    ) -> bytes:
        """Generate placeholder WAV audio from text.

        Estimates duration based on word count and speech rate.
        """
        word_count = max(len(text.split()), 1)
        base_duration = word_count / self._WORDS_PER_SECOND
        adjusted_duration = base_duration / max(speech_rate, 0.1)
        adjusted_duration = max(adjusted_duration, 0.1)
        return _generate_silent_wav(adjusted_duration)


class AzureSpeechAdapter:
    """TTS adapter for Azure Cognitive Services Speech.

    Placeholder implementation that generates silent WAV audio of
    appropriate duration for testing. In production, this would call
    the Azure Speech SDK.
    """

    _WORDS_PER_SECOND = 2.5

    def synthesize(
        self,
        text: str,
        voice_id: str,
        locale: str,
        speech_rate: float,
    ) -> bytes:
        """Generate placeholder WAV audio from text."""
        word_count = max(len(text.split()), 1)
        base_duration = word_count / self._WORDS_PER_SECOND
        adjusted_duration = base_duration / max(speech_rate, 0.1)
        adjusted_duration = max(adjusted_duration, 0.1)
        return _generate_silent_wav(adjusted_duration)


class ElevenLabsAdapter:
    """TTS adapter for ElevenLabs API.

    Placeholder implementation that generates silent WAV audio of
    appropriate duration for testing. In production, this would call
    the ElevenLabs API.
    """

    _WORDS_PER_SECOND = 2.5

    def synthesize(
        self,
        text: str,
        voice_id: str,
        locale: str,
        speech_rate: float,
    ) -> bytes:
        """Generate placeholder WAV audio from text."""
        word_count = max(len(text.split()), 1)
        base_duration = word_count / self._WORDS_PER_SECOND
        adjusted_duration = base_duration / max(speech_rate, 0.1)
        adjusted_duration = max(adjusted_duration, 0.1)
        return _generate_silent_wav(adjusted_duration)


# ---------------------------------------------------------------------------
# TTS Provider Factory
# ---------------------------------------------------------------------------

# Registry of supported TTS provider names to adapter classes
from src.edge_tts_adapter import EdgeTTSAdapter

TTS_PROVIDER_REGISTRY: Dict[str, type] = {
    "coqui": CoquiTTSAdapter,
    "azure": AzureSpeechAdapter,
    "elevenlabs": ElevenLabsAdapter,
    "edge": EdgeTTSAdapter,
}


def create_tts_provider(provider_name: str) -> Any:
    """Create a TTS provider adapter by name.

    Args:
        provider_name: Name of the TTS provider (e.g., "coqui", "azure",
            "elevenlabs").

    Returns:
        An instance of the corresponding TTS adapter.

    Raises:
        NarrationEngineError: If the provider name is not recognized.
    """
    adapter_cls = TTS_PROVIDER_REGISTRY.get(provider_name.lower())
    if adapter_cls is None:
        supported = ", ".join(sorted(TTS_PROVIDER_REGISTRY.keys()))
        raise NarrationEngineError(
            f"Unknown TTS provider '{provider_name}'. "
            f"Supported providers: {supported}"
        )
    return adapter_cls()


# ---------------------------------------------------------------------------
# Voice Profile Manager (Task 6.2)
# ---------------------------------------------------------------------------


class VoiceProfileManager:
    """Manages voice profile assignments for characters and narrator.

    Maps character names to voice IDs from configuration. Uses the
    default narrator voice for non-dialogue narration segments.

    Args:
        narrator_voice: The voice ID for the default narrator.
        character_voices: Mapping of character names to voice IDs.
    """

    def __init__(
        self,
        narrator_voice: str,
        character_voices: Dict[str, str],
    ):
        self._narrator_voice = narrator_voice
        self._character_voices = dict(character_voices)
        self._validate_voice_uniqueness()

    def _validate_voice_uniqueness(self) -> None:
        """Validate that all character voice IDs are distinct.

        Raises:
            NarrationEngineError: If two characters share the same voice ID.
        """
        seen: Dict[str, str] = {}
        for char_name, voice_id in self._character_voices.items():
            if voice_id in seen:
                raise NarrationEngineError(
                    f"Duplicate voice ID '{voice_id}' assigned to characters "
                    f"'{seen[voice_id]}' and '{char_name}'. Each character "
                    f"must have a distinct voice profile."
                )
            seen[voice_id] = char_name

    def get_narrator_voice(self) -> str:
        """Return the default narrator voice ID."""
        return self._narrator_voice

    def get_character_voice(self, character_name: str) -> str:
        """Return the voice ID for a character.

        If the character is not in the voice configuration, falls back
        to the narrator voice.

        Args:
            character_name: The character's name.

        Returns:
            The voice ID assigned to the character, or the narrator voice
            if the character has no specific assignment.
        """
        voice_id = self._character_voices.get(character_name)
        if voice_id is None:
            logger.warning(
                "No voice profile for character '%s', using narrator voice",
                character_name,
            )
            return self._narrator_voice
        return voice_id

    @property
    def character_voices(self) -> Dict[str, str]:
        """Return a copy of the character voice mapping."""
        return dict(self._character_voices)


# ---------------------------------------------------------------------------
# Duration Synchronization Constants (Task 6.4)
# ---------------------------------------------------------------------------

# Tolerance in seconds for duration synchronization
DURATION_TOLERANCE_SECONDS = 2.0

# Maximum number of regeneration attempts for duration adjustment
MAX_DURATION_RETRIES = 3

# Speech rate adjustment step per retry
SPEECH_RATE_STEP = 0.15


# ---------------------------------------------------------------------------
# NarrationEngine (Tasks 6.1 - 6.4)
# ---------------------------------------------------------------------------


class NarrationEngine:
    """Generates spoken audio from episode script narration and dialogue.

    The engine:
    1. Extracts narration and dialogue segments from the episode script
    2. Assigns voice profiles to each segment (narrator or character)
    3. Generates audio via the configured TTS provider
    4. Measures duration against script timing cues
    5. Adjusts speech rate and regenerates if duration exceeds tolerance

    All TTS functionality is injectable via the TTSProvider protocol
    for testability.

    Args:
        config: NarrationConfig with locale, voice, and provider settings.
        tts_provider: An object implementing the TTSProvider protocol.
            If None, creates one from config.tts_provider.
    """

    def __init__(
        self,
        config: NarrationConfig,
        tts_provider: Optional[Any] = None,
    ):
        self._config = config
        self._voice_manager = VoiceProfileManager(
            narrator_voice=config.narrator_voice,
            character_voices=config.character_voices,
        )
        if tts_provider is not None:
            self._tts_provider = tts_provider
        else:
            self._tts_provider = create_tts_provider(config.tts_provider)

    @property
    def locale(self) -> str:
        """The configured locale for TTS synthesis."""
        return self._config.default_locale

    @property
    def voice_manager(self) -> VoiceProfileManager:
        """The voice profile manager."""
        return self._voice_manager

    def _synthesize_segment(
        self,
        text: str,
        voice_id: str,
        speech_rate: float = 1.0,
    ) -> bytes:
        """Synthesize a single text segment to WAV audio.

        Args:
            text: The text to synthesize.
            voice_id: The voice profile ID to use.
            speech_rate: Speech rate multiplier.

        Returns:
            WAV format audio bytes.
        """
        return self._tts_provider.synthesize(
            text=text,
            voice_id=voice_id,
            locale=self._config.default_locale,
            speech_rate=speech_rate,
        )

    def _generate_segment_with_duration_sync(
        self,
        text: str,
        voice_id: str,
        target_duration: Optional[float],
        scene_number: int,
        segment_type: str,
        character: Optional[str],
    ) -> AudioSegment:
        """Generate an audio segment, speeding up if it exceeds target duration.

        First generates at 1.0x rate. If the result exceeds target_duration,
        regenerates with a faster rate (up to 1.25x max) to fit. This keeps
        narration natural-sounding while ensuring it doesn't exceed video timing.

        Args:
            text: The text to synthesize.
            voice_id: The voice profile ID.
            target_duration: Target duration in seconds. If None, uses 1.0x.
            scene_number: The scene number for metadata.
            segment_type: "narration" or "dialogue".
            character: Character name for dialogue, None for narration.

        Returns:
            An AudioSegment with the generated audio.
        """
        MAX_SPEEDUP = 1.25  # Never go faster than 1.25x — sounds unnatural

        # First attempt at normal speed
        speech_rate = 1.0
        audio_data = self._synthesize_segment(text, voice_id, speech_rate)
        duration = get_wav_duration(audio_data)

        # If target is set and narration is too long, speed it up
        if target_duration and duration > target_duration:
            needed_rate = duration / target_duration
            speech_rate = min(needed_rate, MAX_SPEEDUP)
            audio_data = self._synthesize_segment(text, voice_id, speech_rate)
            duration = get_wav_duration(audio_data)

        return AudioSegment(
            scene_number=scene_number,
            segment_type=segment_type,
            character=character,
            text=text,
            voice_id=voice_id,
            audio_data=audio_data,
            duration_seconds=duration,
            speech_rate=speech_rate,
        )

    def generate_scene_audio(self, scene: Scene) -> SceneAudio:
        """Generate all audio segments for a single scene.

        Extracts narration and dialogue from the scene, generates audio
        for each segment using the appropriate voice profile, and
        synchronizes duration with the scene's timing cue.

        Args:
            scene: The scene to generate audio for.

        Returns:
            A SceneAudio object containing all generated segments.
        """
        segments: List[AudioSegment] = []
        target_duration = float(scene.duration_seconds)

        # Count total segments to distribute target duration
        total_segments = 1 + len(scene.dialogue)  # 1 for narration
        per_segment_target = target_duration / total_segments if total_segments > 0 else None

        # Generate narration audio
        if scene.narration:
            narrator_voice = self._voice_manager.get_narrator_voice()
            narration_segment = self._generate_segment_with_duration_sync(
                text=scene.narration,
                voice_id=narrator_voice,
                target_duration=per_segment_target,
                scene_number=scene.scene_number,
                segment_type="narration",
                character=None,
            )
            segments.append(narration_segment)

        # Generate dialogue audio
        for dialogue_line in scene.dialogue:
            char_voice = self._voice_manager.get_character_voice(
                dialogue_line.character
            )
            dialogue_segment = self._generate_segment_with_duration_sync(
                text=dialogue_line.text,
                voice_id=char_voice,
                target_duration=per_segment_target,
                scene_number=scene.scene_number,
                segment_type="dialogue",
                character=dialogue_line.character,
            )
            segments.append(dialogue_segment)

        scene_audio = SceneAudio(
            scene_number=scene.scene_number,
            segments=segments,
        )

        logger.info(
            "Scene %d: generated %d audio segments, total duration %.2fs "
            "(target: %.2fs)",
            scene.scene_number,
            len(segments),
            scene_audio.total_duration_seconds,
            target_duration,
        )

        return scene_audio

    def generate_episode_audio(self, script: EpisodeScript) -> EpisodeAudio:
        """Generate all audio for an entire episode.

        Processes each scene in the script, generating narration and
        dialogue audio with voice profiles and duration synchronization.

        Args:
            script: The episode script to generate audio for.

        Returns:
            An EpisodeAudio object containing all scene audio.

        Raises:
            NarrationEngineError: If audio generation fails critically.
        """
        scene_audio_list: List[SceneAudio] = []

        for scene in script.scenes:
            logger.info(
                "Generating audio for scene %d of episode %d",
                scene.scene_number,
                script.episode_number,
            )
            scene_audio = self.generate_scene_audio(scene)
            scene_audio_list.append(scene_audio)

        episode_audio = EpisodeAudio(
            episode_number=script.episode_number,
            scene_audio=scene_audio_list,
        )

        logger.info(
            "Episode %d: generated audio for %d scenes, total duration %.2fs",
            script.episode_number,
            len(scene_audio_list),
            episode_audio.total_duration_seconds,
        )

        return episode_audio
