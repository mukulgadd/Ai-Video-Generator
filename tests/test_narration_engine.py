"""Tests for the Narration Engine.

Includes property-based tests (Hypothesis) and unit tests for voice
profile management, duration synchronization, locale configuration,
and TTS provider adapter pattern.
"""

import io
import wave
from typing import Dict, List, Optional
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.config_loader import NarrationConfig
from src.episode_script import DialogueLine, EpisodeScript, Scene
from src.narration_engine import (
    AudioSegment,
    AzureSpeechAdapter,
    CoquiTTSAdapter,
    ElevenLabsAdapter,
    NarrationEngine,
    NarrationEngineError,
    SceneAudio,
    TTSProvider,
    VoiceProfileManager,
    create_tts_provider,
    get_wav_duration,
    _generate_silent_wav,
    DURATION_TOLERANCE_SECONDS,
    MAX_DURATION_RETRIES,
    SPEECH_RATE_STEP,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    character_voices: Optional[Dict[str, str]] = None,
    narrator_voice: str = "narrator_v1",
    tts_provider: str = "coqui",
    default_locale: str = "hi",
) -> NarrationConfig:
    """Create a NarrationConfig for testing."""
    if character_voices is None:
        character_voices = {
            "Rama": "voice_rama_01",
            "Sita": "voice_sita_01",
            "Hanuman": "voice_hanuman_01",
            "Ravana": "voice_ravana_01",
        }
    return NarrationConfig(
        default_locale=default_locale,
        narrator_voice=narrator_voice,
        tts_provider=tts_provider,
        character_voices=character_voices,
    )


def _make_scene(
    scene_number: int = 1,
    duration_seconds: int = 20,
    narration: str = "In the ancient kingdom of Ayodhya",
    dialogue: Optional[List[DialogueLine]] = None,
) -> Scene:
    """Create a Scene for testing."""
    if dialogue is None:
        dialogue = []
    return Scene(
        scene_number=scene_number,
        duration_seconds=duration_seconds,
        background="Royal palace",
        characters=["Rama"],
        action="Rama enters the palace",
        narration=narration,
        dialogue=dialogue,
        mood="devotional",
        sound_effects=["temple_bells"],
    )


def _make_episode_script(scenes: Optional[List[Scene]] = None) -> EpisodeScript:
    """Create an EpisodeScript for testing."""
    if scenes is None:
        scenes = [_make_scene()]
    return EpisodeScript(
        episode_number=1,
        kanda="Bala Kanda",
        title="The Birth of Rama",
        total_duration_seconds=sum(s.duration_seconds for s in scenes),
        scenes=scenes,
    )


# ---------------------------------------------------------------------------
# Task 6.5.1 [PBT] Property 9: Voice Distinctness
# ---------------------------------------------------------------------------


# Strategy: generate character voice configs with distinct names and distinct IDs
@st.composite
def voice_config_strategy(draw):
    """Generate a voice configuration dict with distinct character names
    and distinct voice IDs."""
    num_chars = draw(st.integers(min_value=2, max_value=10))

    # Generate distinct character names
    char_names = draw(
        st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("L",)),
                min_size=1,
                max_size=20,
            ),
            min_size=num_chars,
            max_size=num_chars,
            unique=True,
        )
    )

    # Generate distinct voice IDs
    voice_ids = draw(
        st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("L", "N")),
                min_size=1,
                max_size=20,
            ),
            min_size=num_chars,
            max_size=num_chars,
            unique=True,
        )
    )

    return dict(zip(char_names, voice_ids))


@given(voice_config=voice_config_strategy())
@settings(max_examples=100)
def test_property_9_voice_distinctness(voice_config: Dict[str, str]):
    """**Validates: Requirements 5.2**

    Property 9: For any two distinct character names in the voice
    configuration, the assigned voice profile IDs are different.

    This tests the validation logic in VoiceProfileManager: given a
    config with distinct names and distinct IDs, the manager should
    accept it. The voice IDs for any two different characters must
    be different.
    """
    # The strategy guarantees distinct IDs, so VoiceProfileManager should accept
    manager = VoiceProfileManager(
        narrator_voice="narrator_default",
        character_voices=voice_config,
    )

    # Verify: for any two distinct character names, voice IDs differ
    names = list(voice_config.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            voice_i = manager.get_character_voice(names[i])
            voice_j = manager.get_character_voice(names[j])
            assert voice_i != voice_j, (
                f"Characters '{names[i]}' and '{names[j]}' have the same "
                f"voice ID '{voice_i}'"
            )


@st.composite
def duplicate_voice_config_strategy(draw):
    """Generate a voice config where at least two characters share a voice ID."""
    num_chars = draw(st.integers(min_value=2, max_value=8))

    char_names = draw(
        st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("L",)),
                min_size=1,
                max_size=20,
            ),
            min_size=num_chars,
            max_size=num_chars,
            unique=True,
        )
    )

    # Generate voice IDs but force at least one duplicate
    shared_voice = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=20,
        )
    )

    voice_ids = [shared_voice, shared_voice]  # First two share a voice
    for _ in range(num_chars - 2):
        voice_ids.append(
            draw(
                st.text(
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                    min_size=1,
                    max_size=20,
                )
            )
        )

    return dict(zip(char_names, voice_ids))


@given(voice_config=duplicate_voice_config_strategy())
@settings(max_examples=50)
def test_property_9_duplicate_voice_rejected(voice_config: Dict[str, str]):
    """**Validates: Requirements 5.2**

    Property 9 (negative): When two distinct characters share the same
    voice ID, VoiceProfileManager raises NarrationEngineError.
    """
    with pytest.raises(NarrationEngineError, match="Duplicate voice ID"):
        VoiceProfileManager(
            narrator_voice="narrator_default",
            character_voices=voice_config,
        )


# ---------------------------------------------------------------------------
# Task 6.5.2: Duration Adjustment Edge Case
# ---------------------------------------------------------------------------


class OversizedTTSProvider:
    """Mock TTS provider that produces audio longer than expected.

    On the first call, produces audio much longer than expected (fixed
    oversized duration). On subsequent calls, respects the speech_rate
    to simulate adjustment.
    """

    def __init__(self, oversized_duration: float = 20.0):
        self._oversized_duration = oversized_duration
        self._call_count = 0
        self.calls: List[Dict] = []

    def synthesize(
        self,
        text: str,
        voice_id: str,
        locale: str,
        speech_rate: float,
    ) -> bytes:
        self._call_count += 1
        self.calls.append({
            "text": text,
            "voice_id": voice_id,
            "locale": locale,
            "speech_rate": speech_rate,
        })

        if self._call_count == 1:
            # First call: produce oversized audio (ignore speech_rate)
            duration = self._oversized_duration
        else:
            # Subsequent calls: produce audio that shrinks with speech_rate
            base_duration = self._oversized_duration / 2.0
            duration = base_duration / max(speech_rate, 0.1)

        duration = max(duration, 0.1)
        return _generate_silent_wav(duration)


def test_duration_adjustment_oversized_audio():
    """Test that when TTS produces oversized audio, the engine adjusts
    speech rate and regenerates.

    Validates: Requirement 5.4, 5.5
    """
    # The oversized provider returns 20s on first call, then adjusts.
    # With a scene of 5s and 1 segment, target per segment is 5s.
    # 20s - 5s = 15s >> 2s tolerance, so it must retry.
    mock_tts = OversizedTTSProvider(oversized_duration=20.0)
    config = _make_config()
    engine = NarrationEngine(config=config, tts_provider=mock_tts)

    scene = _make_scene(
        duration_seconds=5,
        narration="This is a test narration with several words to synthesize",
    )

    scene_audio = engine.generate_scene_audio(scene)

    # The TTS should have been called more than once due to duration adjustment
    assert len(mock_tts.calls) > 1, (
        "Expected multiple TTS calls due to duration adjustment, "
        f"but got {len(mock_tts.calls)}"
    )

    # Verify speech rate was increased on retry calls
    first_rate = mock_tts.calls[0]["speech_rate"]
    last_rate = mock_tts.calls[-1]["speech_rate"]
    assert last_rate > first_rate, (
        f"Expected speech rate to increase from {first_rate} to handle "
        f"oversized audio, but last rate was {last_rate}"
    )

    # Verify the segment records the adjusted speech rate
    assert len(scene_audio.segments) == 1
    segment = scene_audio.segments[0]
    assert segment.speech_rate > 1.0, (
        f"Expected adjusted speech rate > 1.0, got {segment.speech_rate}"
    )


# ---------------------------------------------------------------------------
# Task 6.5.3: Locale Configuration
# ---------------------------------------------------------------------------


class LocaleCapturingTTSProvider:
    """Mock TTS provider that captures the locale passed to synthesize."""

    def __init__(self):
        self.calls: List[Dict] = []

    def synthesize(
        self,
        text: str,
        voice_id: str,
        locale: str,
        speech_rate: float,
    ) -> bytes:
        self.calls.append({
            "text": text,
            "voice_id": voice_id,
            "locale": locale,
            "speech_rate": speech_rate,
        })
        return _generate_silent_wav(1.0)


def test_locale_default_hindi():
    """Test that the default locale (Hindi) is passed to the TTS provider.

    Validates: Requirement 5.3
    """
    mock_tts = LocaleCapturingTTSProvider()
    config = _make_config(default_locale="hi")
    engine = NarrationEngine(config=config, tts_provider=mock_tts)

    scene = _make_scene(narration="Test narration text")
    engine.generate_scene_audio(scene)

    assert len(mock_tts.calls) >= 1
    for call in mock_tts.calls:
        assert call["locale"] == "hi", (
            f"Expected locale 'hi', got '{call['locale']}'"
        )


def test_locale_custom_value():
    """Test that a custom locale is passed to the TTS provider."""
    mock_tts = LocaleCapturingTTSProvider()
    config = _make_config(default_locale="en")
    engine = NarrationEngine(config=config, tts_provider=mock_tts)

    scene = _make_scene(narration="Test narration text")
    engine.generate_scene_audio(scene)

    assert len(mock_tts.calls) >= 1
    for call in mock_tts.calls:
        assert call["locale"] == "en", (
            f"Expected locale 'en', got '{call['locale']}'"
        )


# ---------------------------------------------------------------------------
# Additional Unit Tests
# ---------------------------------------------------------------------------


class TestVoiceProfileManager:
    """Tests for VoiceProfileManager."""

    def test_narrator_voice(self):
        """Narrator voice is returned correctly."""
        manager = VoiceProfileManager(
            narrator_voice="narrator_v1",
            character_voices={"Rama": "voice_rama"},
        )
        assert manager.get_narrator_voice() == "narrator_v1"

    def test_character_voice_lookup(self):
        """Known character returns assigned voice."""
        manager = VoiceProfileManager(
            narrator_voice="narrator_v1",
            character_voices={"Rama": "voice_rama", "Sita": "voice_sita"},
        )
        assert manager.get_character_voice("Rama") == "voice_rama"
        assert manager.get_character_voice("Sita") == "voice_sita"

    def test_unknown_character_falls_back_to_narrator(self):
        """Unknown character falls back to narrator voice."""
        manager = VoiceProfileManager(
            narrator_voice="narrator_v1",
            character_voices={"Rama": "voice_rama"},
        )
        assert manager.get_character_voice("Unknown") == "narrator_v1"

    def test_duplicate_voice_ids_rejected(self):
        """Duplicate voice IDs raise NarrationEngineError."""
        with pytest.raises(NarrationEngineError, match="Duplicate voice ID"):
            VoiceProfileManager(
                narrator_voice="narrator_v1",
                character_voices={
                    "Rama": "same_voice",
                    "Sita": "same_voice",
                },
            )


class TestTTSProviderFactory:
    """Tests for TTS provider creation."""

    def test_create_coqui(self):
        provider = create_tts_provider("coqui")
        assert isinstance(provider, CoquiTTSAdapter)

    def test_create_azure(self):
        provider = create_tts_provider("azure")
        assert isinstance(provider, AzureSpeechAdapter)

    def test_create_elevenlabs(self):
        provider = create_tts_provider("elevenlabs")
        assert isinstance(provider, ElevenLabsAdapter)

    def test_unknown_provider_raises(self):
        with pytest.raises(NarrationEngineError, match="Unknown TTS provider"):
            create_tts_provider("nonexistent")

    def test_case_insensitive(self):
        provider = create_tts_provider("Coqui")
        assert isinstance(provider, CoquiTTSAdapter)


class TestTTSAdapters:
    """Tests for TTS adapter placeholder implementations."""

    @pytest.mark.parametrize("adapter_cls", [CoquiTTSAdapter, AzureSpeechAdapter, ElevenLabsAdapter])
    def test_adapter_produces_valid_wav(self, adapter_cls):
        """Each adapter produces valid WAV audio."""
        adapter = adapter_cls()
        wav_data = adapter.synthesize(
            text="Hello world test",
            voice_id="test_voice",
            locale="hi",
            speech_rate=1.0,
        )
        duration = get_wav_duration(wav_data)
        assert duration > 0

    @pytest.mark.parametrize("adapter_cls", [CoquiTTSAdapter, AzureSpeechAdapter, ElevenLabsAdapter])
    def test_adapter_speech_rate_affects_duration(self, adapter_cls):
        """Higher speech rate produces shorter audio."""
        adapter = adapter_cls()
        text = "This is a longer test sentence with many words to speak"

        wav_normal = adapter.synthesize(text=text, voice_id="v1", locale="hi", speech_rate=1.0)
        wav_fast = adapter.synthesize(text=text, voice_id="v1", locale="hi", speech_rate=2.0)

        dur_normal = get_wav_duration(wav_normal)
        dur_fast = get_wav_duration(wav_fast)
        assert dur_fast < dur_normal


class TestNarrationEngine:
    """Tests for the NarrationEngine class."""

    def test_generate_scene_audio_narration_only(self):
        """Scene with only narration produces one segment."""
        config = _make_config()
        engine = NarrationEngine(config=config)
        scene = _make_scene(narration="Test narration")
        audio = engine.generate_scene_audio(scene)

        assert len(audio.segments) == 1
        assert audio.segments[0].segment_type == "narration"
        assert audio.segments[0].character is None
        assert audio.segments[0].voice_id == "narrator_v1"

    def test_generate_scene_audio_with_dialogue(self):
        """Scene with dialogue produces narration + dialogue segments."""
        config = _make_config()
        engine = NarrationEngine(config=config)
        scene = _make_scene(
            narration="Narration text",
            dialogue=[
                DialogueLine(character="Rama", text="I shall go to the forest"),
                DialogueLine(character="Sita", text="I will follow you"),
            ],
        )
        audio = engine.generate_scene_audio(scene)

        assert len(audio.segments) == 3
        assert audio.segments[0].segment_type == "narration"
        assert audio.segments[1].segment_type == "dialogue"
        assert audio.segments[1].character == "Rama"
        assert audio.segments[1].voice_id == "voice_rama_01"
        assert audio.segments[2].segment_type == "dialogue"
        assert audio.segments[2].character == "Sita"
        assert audio.segments[2].voice_id == "voice_sita_01"

    def test_generate_episode_audio(self):
        """Full episode generates audio for all scenes."""
        config = _make_config()
        engine = NarrationEngine(config=config)
        scenes = [
            _make_scene(scene_number=1, narration="Scene one narration"),
            _make_scene(scene_number=2, narration="Scene two narration"),
        ]
        script = _make_episode_script(scenes=scenes)
        episode_audio = engine.generate_episode_audio(script)

        assert episode_audio.episode_number == 1
        assert len(episode_audio.scene_audio) == 2
        assert episode_audio.total_duration_seconds > 0

    def test_locale_property(self):
        """Engine exposes the configured locale."""
        config = _make_config(default_locale="hi")
        engine = NarrationEngine(config=config)
        assert engine.locale == "hi"

    def test_custom_tts_provider(self):
        """Engine uses injected TTS provider."""
        mock_tts = LocaleCapturingTTSProvider()
        config = _make_config()
        engine = NarrationEngine(config=config, tts_provider=mock_tts)

        scene = _make_scene(narration="Test")
        engine.generate_scene_audio(scene)

        assert len(mock_tts.calls) >= 1


class TestWavUtilities:
    """Tests for WAV utility functions."""

    def test_generate_silent_wav(self):
        """Silent WAV has correct duration."""
        wav_data = _generate_silent_wav(2.0)
        duration = get_wav_duration(wav_data)
        assert abs(duration - 2.0) < 0.01

    def test_get_wav_duration_invalid(self):
        """Invalid WAV data raises NarrationEngineError."""
        with pytest.raises(NarrationEngineError, match="Failed to measure"):
            get_wav_duration(b"not a wav file")
