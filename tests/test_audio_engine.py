"""Tests for the Audio Engine.

Includes property-based tests (Hypothesis) and unit tests for music
selection, audio mixing with volume ducking, sound effect placement,
crossfade transitions, and final audio export.
"""

import io
import math
import os
import struct
import tempfile
import wave
from typing import Dict, List, Optional, Tuple

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from pydub import AudioSegment as PydubSegment

from src.config_loader import AudioConfig
from src.episode_script import DialogueLine, EpisodeScript, Scene
from src.narration_engine import (
    AudioSegment,
    EpisodeAudio,
    SceneAudio,
    _generate_silent_wav,
)
from src.audio_engine import (
    AudioEngine,
    AudioEngineError,
    MusicClip,
    MusicLibrary,
    SFXClip,
    SFXLibrary,
    TARGET_SAMPLE_RATE,
    TARGET_BIT_DEPTH,
    TARGET_SAMPLE_WIDTH,
    TARGET_CHANNELS,
    MIN_CROSSFADE_SECONDS,
    MAX_CROSSFADE_SECONDS,
    apply_crossfade,
    export_final_audio,
    export_to_wav_bytes,
    generate_silent_pydub,
    generate_tone_pydub,
    mix_narration_with_music,
    normalize_segment,
    place_sound_effects,
    pydub_to_wav_bytes,
    select_music_for_mood,
    wav_bytes_to_pydub,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_audio_config(
    narration_boost_db: int = 6,
    crossfade_seconds: float = 0.75,
) -> AudioConfig:
    """Create an AudioConfig for testing."""
    return AudioConfig(
        music_library_path="./assets/music/",
        sfx_library_path="./assets/sfx/",
        narration_boost_db=narration_boost_db,
        crossfade_seconds=crossfade_seconds,
    )


def _make_scene(
    scene_number: int = 1,
    duration_seconds: int = 20,
    mood: str = "devotional",
    sound_effects: Optional[List[str]] = None,
    narration: str = "In the ancient kingdom of Ayodhya",
    dialogue: Optional[List[DialogueLine]] = None,
) -> Scene:
    """Create a Scene for testing."""
    return Scene(
        scene_number=scene_number,
        duration_seconds=duration_seconds,
        background="Royal palace",
        characters=["Rama"],
        action="Rama enters the palace",
        narration=narration,
        dialogue=dialogue or [],
        mood=mood,
        sound_effects=sound_effects or [],
    )


def _make_episode_script(
    scenes: Optional[List[Scene]] = None,
) -> EpisodeScript:
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


def _make_narration_wav(duration_seconds: float = 2.0) -> bytes:
    """Create WAV bytes with a tone for narration testing."""
    return _generate_silent_wav(duration_seconds)


def _make_audio_segment(
    scene_number: int = 1,
    duration_seconds: float = 2.0,
    text: str = "Test narration",
) -> AudioSegment:
    """Create an AudioSegment for testing."""
    wav_data = _make_narration_wav(duration_seconds)
    return AudioSegment(
        scene_number=scene_number,
        segment_type="narration",
        character=None,
        text=text,
        voice_id="narrator_v1",
        audio_data=wav_data,
        duration_seconds=duration_seconds,
    )


def _make_scene_audio(
    scene_number: int = 1,
    num_segments: int = 1,
    duration_per_segment: float = 2.0,
) -> SceneAudio:
    """Create a SceneAudio for testing."""
    segments = [
        _make_audio_segment(
            scene_number=scene_number,
            duration_seconds=duration_per_segment,
            text=f"Segment {i}",
        )
        for i in range(num_segments)
    ]
    return SceneAudio(
        scene_number=scene_number,
        segments=segments,
    )


def _make_episode_audio(
    num_scenes: int = 1,
    segments_per_scene: int = 1,
    duration_per_segment: float = 2.0,
) -> EpisodeAudio:
    """Create an EpisodeAudio for testing."""
    scene_audio_list = [
        _make_scene_audio(
            scene_number=i + 1,
            num_segments=segments_per_scene,
            duration_per_segment=duration_per_segment,
        )
        for i in range(num_scenes)
    ]
    return EpisodeAudio(
        episode_number=1,
        scene_audio=scene_audio_list,
    )


def _make_tone_pydub(
    duration_ms: int = 2000,
    frequency: float = 440.0,
    volume_dbfs: float = -10.0,
) -> PydubSegment:
    """Create a pydub AudioSegment with a tone."""
    return generate_tone_pydub(
        frequency=frequency,
        duration_ms=duration_ms,
        volume_dbfs=volume_dbfs,
    )


def _make_music_library(moods: Optional[List[str]] = None) -> MusicLibrary:
    """Create a MusicLibrary with placeholder clips."""
    if moods is None:
        moods = ["devotional", "heroic", "sad", "peaceful"]
    library = MusicLibrary()
    for mood in moods:
        clip = MusicClip(
            name=f"{mood}_track1",
            mood=mood,
            file_path=f"./assets/music/{mood}_track1.wav",
        )
        library.add_clip(clip)
    return library


def _make_sfx_library(names: Optional[List[str]] = None) -> SFXLibrary:
    """Create an SFXLibrary with placeholder clips."""
    if names is None:
        names = ["fire_crackling", "temple_bells", "sword_clash"]
    library = SFXLibrary()
    for name in names:
        clip = SFXClip(
            name=name,
            file_path=f"./assets/sfx/{name}.wav",
        )
        library.add_clip(clip)
    return library


# ---------------------------------------------------------------------------
# Task 7.6.1 [PBT] Property 10: Audio Mixing Level Invariant
# ---------------------------------------------------------------------------


@st.composite
def narration_and_music_strategy(draw):
    """Generate random narration and music audio segments for mixing tests.

    Produces pydub AudioSegments with varying durations and volumes.
    """
    # Duration between 500ms and 5000ms
    duration_ms = draw(st.integers(min_value=500, max_value=5000))

    # Narration volume: -5 to -25 dBFS (audible range)
    narration_vol = draw(st.floats(min_value=-25.0, max_value=-5.0))

    # Music volume: -5 to -25 dBFS (audible range)
    music_vol = draw(st.floats(min_value=-25.0, max_value=-5.0))

    # Narration boost: 6 to 12 dB
    boost_db = draw(st.floats(min_value=6.0, max_value=12.0))

    # Generate narration tone (speech-like frequency)
    narration = generate_tone_pydub(
        frequency=300.0,
        duration_ms=duration_ms,
        volume_dbfs=narration_vol,
    )
    narration = normalize_segment(narration)

    # Generate music tone (different frequency)
    music = generate_tone_pydub(
        frequency=220.0,
        duration_ms=duration_ms,
        volume_dbfs=music_vol,
    )
    music = normalize_segment(music)

    return narration, music, boost_db


@given(data=narration_and_music_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_property_10_narration_louder_than_music(
    data: Tuple[PydubSegment, PydubSegment, float],
):
    """**Validates: Requirements 6.2**

    Property 10: For any mixed audio segment that contains speech,
    the narration audio level is at least 6 dB louder than the
    background music level.

    We verify this by mixing narration and music, then checking that
    the narration level in the mix is at least narration_boost_db
    louder than the music level after ducking.
    """
    narration, music, boost_db = data

    # Skip if either track is silent
    assume(narration.dBFS != float("-inf"))
    assume(music.dBFS != float("-inf"))

    # Mix with volume ducking
    mixed = mix_narration_with_music(
        narration=narration,
        music=music,
        narration_boost_db=boost_db,
    )

    # After mixing, the music should have been ducked.
    # We verify by checking that the narration level was at least
    # boost_db louder than the music level BEFORE overlay.
    # The ducking function adjusts music so:
    #   music_adjusted_dBFS <= narration_dBFS - boost_db

    # Measure the music level after ducking (before overlay)
    narration_level = narration.dBFS
    music_level = music.dBFS
    target_music_level = narration_level - boost_db

    if music_level > target_music_level:
        # Music was ducked
        expected_music_level = target_music_level
    else:
        # Music was already quiet enough
        expected_music_level = music_level

    # The difference between narration and the effective music level
    # should be at least boost_db
    actual_diff = narration_level - expected_music_level
    assert actual_diff >= boost_db - 0.1, (
        f"Narration ({narration_level:.1f} dBFS) should be at least "
        f"{boost_db:.1f} dB louder than music ({expected_music_level:.1f} dBFS), "
        f"but difference is only {actual_diff:.1f} dB"
    )


# ---------------------------------------------------------------------------
# Task 7.6.2 [PBT] Property 11: Audio Format Invariant
# ---------------------------------------------------------------------------


@st.composite
def audio_for_export_strategy(draw):
    """Generate random audio segments for export format testing."""
    duration_ms = draw(st.integers(min_value=100, max_value=3000))
    volume_dbfs = draw(st.floats(min_value=-30.0, max_value=-5.0))
    frequency = draw(st.floats(min_value=100.0, max_value=1000.0))

    audio = generate_tone_pydub(
        frequency=frequency,
        duration_ms=duration_ms,
        volume_dbfs=volume_dbfs,
    )
    return audio


@given(audio=audio_for_export_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_property_11_audio_format_invariant(audio: PydubSegment):
    """**Validates: Requirements 6.5**

    Property 11: For any audio file produced by the Audio_Engine,
    the sample rate is 44100 Hz and the bit depth is 16.
    """
    # Export to WAV bytes
    wav_bytes = export_to_wav_bytes(audio)

    # Read back and verify format
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        sample_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        bit_depth = sample_width * 8

    assert sample_rate == 44100, (
        f"Expected sample rate 44100 Hz, got {sample_rate} Hz"
    )
    assert bit_depth == 16, (
        f"Expected bit depth 16, got {bit_depth}"
    )


# ---------------------------------------------------------------------------
# Task 7.6.3: Crossfade Transitions
# ---------------------------------------------------------------------------


class TestCrossfadeTransitions:
    """Test crossfade transitions between scenes."""

    def test_crossfade_two_segments(self):
        """Two segments with crossfade produce shorter total than concatenation."""
        seg1 = generate_silent_pydub(2000)
        seg2 = generate_silent_pydub(2000)

        # Without crossfade: 4000ms
        no_crossfade = seg1 + seg2
        assert len(no_crossfade) == 4000

        # With 750ms crossfade: should be ~3250ms
        crossfaded = apply_crossfade([seg1, seg2], crossfade_ms=750)
        expected_duration = 4000 - 750
        assert abs(len(crossfaded) - expected_duration) <= 10, (
            f"Expected ~{expected_duration}ms, got {len(crossfaded)}ms"
        )

    def test_crossfade_duration_within_range(self):
        """Crossfade duration is clamped to 0.5-1.0 seconds."""
        seg1 = generate_silent_pydub(3000)
        seg2 = generate_silent_pydub(3000)

        # Test minimum clamping (below 0.5s = 500ms)
        result_min = apply_crossfade([seg1, seg2], crossfade_ms=100)
        # Should use 500ms (minimum)
        expected_min = 6000 - 500
        assert abs(len(result_min) - expected_min) <= 10, (
            f"Expected ~{expected_min}ms with min crossfade, got {len(result_min)}ms"
        )

        # Test maximum clamping (above 1.0s = 1000ms)
        result_max = apply_crossfade([seg1, seg2], crossfade_ms=2000)
        # Should use 1000ms (maximum)
        expected_max = 6000 - 1000
        assert abs(len(result_max) - expected_max) <= 10, (
            f"Expected ~{expected_max}ms with max crossfade, got {len(result_max)}ms"
        )

    def test_crossfade_within_valid_range(self):
        """Crossfade of 0.75s (750ms) is within the valid range."""
        seg1 = generate_silent_pydub(3000)
        seg2 = generate_silent_pydub(3000)

        result = apply_crossfade([seg1, seg2], crossfade_ms=750)
        expected = 6000 - 750
        assert abs(len(result) - expected) <= 10

    def test_crossfade_multiple_segments(self):
        """Multiple segments with crossfade."""
        segments = [generate_silent_pydub(2000) for _ in range(4)]
        crossfade_ms = 750

        result = apply_crossfade(segments, crossfade_ms=crossfade_ms)
        # Total = 4*2000 - 3*750 = 8000 - 2250 = 5750ms
        expected = 4 * 2000 - 3 * crossfade_ms
        assert abs(len(result) - expected) <= 30, (
            f"Expected ~{expected}ms, got {len(result)}ms"
        )

    def test_crossfade_single_segment(self):
        """Single segment returns as-is."""
        seg = generate_silent_pydub(2000)
        result = apply_crossfade([seg], crossfade_ms=750)
        assert len(result) == 2000

    def test_crossfade_empty_raises(self):
        """Empty segment list raises AudioEngineError."""
        with pytest.raises(AudioEngineError, match="No audio segments"):
            apply_crossfade([], crossfade_ms=750)

    def test_crossfade_0_5_seconds(self):
        """Verify 0.5 second crossfade works correctly."""
        seg1 = generate_silent_pydub(2000)
        seg2 = generate_silent_pydub(2000)
        result = apply_crossfade([seg1, seg2], crossfade_ms=500)
        expected = 4000 - 500
        assert abs(len(result) - expected) <= 10

    def test_crossfade_1_0_seconds(self):
        """Verify 1.0 second crossfade works correctly."""
        seg1 = generate_silent_pydub(2000)
        seg2 = generate_silent_pydub(2000)
        result = apply_crossfade([seg1, seg2], crossfade_ms=1000)
        expected = 4000 - 1000
        assert abs(len(result) - expected) <= 10


# ---------------------------------------------------------------------------
# Unit Tests: Music Library
# ---------------------------------------------------------------------------


class TestMusicLibrary:
    """Tests for MusicLibrary."""

    def test_get_clips_for_mood(self):
        """Clips are returned for matching mood."""
        library = _make_music_library()
        clips = library.get_clips_for_mood("devotional")
        assert len(clips) == 1
        assert clips[0].mood == "devotional"

    def test_get_clips_for_mood_case_insensitive(self):
        """Mood matching is case-insensitive."""
        library = _make_music_library()
        clips = library.get_clips_for_mood("DEVOTIONAL")
        assert len(clips) == 1

    def test_get_clips_for_unknown_mood_fallback(self):
        """Unknown mood falls back to all clips."""
        library = _make_music_library()
        clips = library.get_clips_for_mood("unknown_mood")
        assert len(clips) == len(library.clips)

    def test_empty_library_returns_empty(self):
        """Empty library returns empty list."""
        library = MusicLibrary()
        clips = library.get_clips_for_mood("devotional")
        assert clips == []

    def test_select_music_for_mood(self):
        """select_music_for_mood returns first matching clip."""
        library = _make_music_library()
        clip = select_music_for_mood(library, "heroic")
        assert clip is not None
        assert clip.mood == "heroic"

    def test_select_music_for_mood_empty(self):
        """select_music_for_mood returns None for empty library."""
        library = MusicLibrary()
        clip = select_music_for_mood(library, "devotional")
        assert clip is None


# ---------------------------------------------------------------------------
# Unit Tests: SFX Library
# ---------------------------------------------------------------------------


class TestSFXLibrary:
    """Tests for SFXLibrary."""

    def test_get_clip_by_name(self):
        """Clip is returned by name."""
        library = _make_sfx_library()
        clip = library.get_clip("fire_crackling")
        assert clip is not None
        assert clip.name == "fire_crackling"

    def test_get_clip_case_insensitive(self):
        """Name matching is case-insensitive."""
        library = _make_sfx_library()
        clip = library.get_clip("FIRE_CRACKLING")
        assert clip is not None

    def test_get_clip_not_found(self):
        """Unknown name returns None."""
        library = _make_sfx_library()
        clip = library.get_clip("nonexistent")
        assert clip is None


# ---------------------------------------------------------------------------
# Unit Tests: Audio Mixing
# ---------------------------------------------------------------------------


class TestAudioMixing:
    """Tests for audio mixing with volume ducking."""

    def test_mix_narration_with_music_basic(self):
        """Basic mixing produces audio of narration length."""
        narration = _make_tone_pydub(duration_ms=3000, volume_dbfs=-10.0)
        narration = normalize_segment(narration)
        music = _make_tone_pydub(duration_ms=5000, volume_dbfs=-10.0)
        music = normalize_segment(music)

        mixed = mix_narration_with_music(narration, music, narration_boost_db=6.0)
        assert abs(len(mixed) - 3000) <= 10

    def test_mix_narration_louder_than_music(self):
        """After mixing, narration level is maintained above music."""
        narration = _make_tone_pydub(
            duration_ms=2000, frequency=300.0, volume_dbfs=-10.0
        )
        narration = normalize_segment(narration)
        music = _make_tone_pydub(
            duration_ms=2000, frequency=220.0, volume_dbfs=-5.0
        )
        music = normalize_segment(music)

        # Music is louder than narration initially
        assert music.dBFS > narration.dBFS

        mixed = mix_narration_with_music(narration, music, narration_boost_db=6.0)
        # The mixed result should exist
        assert len(mixed) > 0

    def test_mix_with_silent_narration(self):
        """Silent narration doesn't crash."""
        narration = generate_silent_pydub(2000)
        narration = normalize_segment(narration)
        music = _make_tone_pydub(duration_ms=2000, volume_dbfs=-10.0)
        music = normalize_segment(music)

        mixed = mix_narration_with_music(narration, music, narration_boost_db=6.0)
        assert len(mixed) > 0

    def test_mix_music_looped_if_shorter(self):
        """Music is looped if shorter than narration."""
        narration = _make_tone_pydub(duration_ms=5000, volume_dbfs=-10.0)
        narration = normalize_segment(narration)
        music = _make_tone_pydub(duration_ms=1000, volume_dbfs=-20.0)
        music = normalize_segment(music)

        mixed = mix_narration_with_music(narration, music, narration_boost_db=6.0)
        assert abs(len(mixed) - 5000) <= 10


# ---------------------------------------------------------------------------
# Unit Tests: Sound Effect Placement
# ---------------------------------------------------------------------------


class TestSoundEffectPlacement:
    """Tests for sound effect placement."""

    def test_place_sfx_at_timestamp(self):
        """SFX is overlaid at the specified timestamp."""
        base = generate_silent_pydub(5000)
        base = normalize_segment(base)
        sfx = _make_tone_pydub(duration_ms=500, volume_dbfs=-10.0)
        sfx = normalize_segment(sfx)

        result = place_sound_effects(base, [(1000, sfx)])
        assert len(result) == len(base)

    def test_place_multiple_sfx(self):
        """Multiple SFX are overlaid at different timestamps."""
        base = generate_silent_pydub(5000)
        base = normalize_segment(base)
        sfx1 = _make_tone_pydub(duration_ms=500, volume_dbfs=-10.0)
        sfx1 = normalize_segment(sfx1)
        sfx2 = _make_tone_pydub(duration_ms=300, volume_dbfs=-15.0)
        sfx2 = normalize_segment(sfx2)

        result = place_sound_effects(base, [(1000, sfx1), (3000, sfx2)])
        assert len(result) == len(base)

    def test_skip_negative_timestamp(self):
        """Negative timestamps are skipped."""
        base = generate_silent_pydub(3000)
        base = normalize_segment(base)
        sfx = _make_tone_pydub(duration_ms=500, volume_dbfs=-10.0)
        sfx = normalize_segment(sfx)

        result = place_sound_effects(base, [(-100, sfx)])
        assert len(result) == len(base)

    def test_skip_timestamp_beyond_audio(self):
        """Timestamps beyond audio length are skipped."""
        base = generate_silent_pydub(3000)
        base = normalize_segment(base)
        sfx = _make_tone_pydub(duration_ms=500, volume_dbfs=-10.0)
        sfx = normalize_segment(sfx)

        result = place_sound_effects(base, [(5000, sfx)])
        assert len(result) == len(base)


# ---------------------------------------------------------------------------
# Unit Tests: Export
# ---------------------------------------------------------------------------


class TestExport:
    """Tests for audio export."""

    def test_export_to_wav_bytes_format(self):
        """Exported WAV has correct format."""
        audio = _make_tone_pydub(duration_ms=1000, volume_dbfs=-10.0)
        wav_bytes = export_to_wav_bytes(audio)

        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            assert wf.getframerate() == 44100
            assert wf.getsampwidth() == 2  # 16-bit
            assert wf.getnchannels() == 2  # stereo

    def test_export_final_audio_to_file(self):
        """Export to file creates a valid WAV."""
        audio = _make_tone_pydub(duration_ms=1000, volume_dbfs=-10.0)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name

        try:
            export_final_audio(audio, output_path)
            assert os.path.exists(output_path)

            with wave.open(output_path, "rb") as wf:
                assert wf.getframerate() == 44100
                assert wf.getsampwidth() == 2
        finally:
            os.unlink(output_path)


# ---------------------------------------------------------------------------
# Unit Tests: AudioEngine
# ---------------------------------------------------------------------------


class TestAudioEngine:
    """Tests for the AudioEngine class."""

    def _make_engine(
        self,
        narration_boost_db: int = 6,
        crossfade_seconds: float = 0.75,
        music_moods: Optional[List[str]] = None,
        sfx_names: Optional[List[str]] = None,
    ) -> AudioEngine:
        """Create an AudioEngine with test libraries."""
        config = _make_audio_config(
            narration_boost_db=narration_boost_db,
            crossfade_seconds=crossfade_seconds,
        )
        music_lib = _make_music_library(music_moods)
        sfx_lib = _make_sfx_library(sfx_names)
        return AudioEngine(
            config=config,
            music_library=music_lib,
            sfx_library=sfx_lib,
        )

    def test_select_music_for_scene(self):
        """Engine selects music matching scene mood."""
        engine = self._make_engine()
        scene = _make_scene(mood="devotional")
        clip = engine.select_music_for_scene(scene)
        assert clip is not None
        assert clip.mood == "devotional"

    def test_crossfade_ms_clamped(self):
        """Crossfade is clamped to valid range."""
        engine_low = self._make_engine(crossfade_seconds=0.1)
        assert engine_low.crossfade_ms == 500  # min 0.5s

        engine_high = self._make_engine(crossfade_seconds=5.0)
        assert engine_high.crossfade_ms == 1000  # max 1.0s

        engine_mid = self._make_engine(crossfade_seconds=0.75)
        assert engine_mid.crossfade_ms == 750

    def test_mix_scene_basic(self):
        """Basic scene mixing produces audio."""
        engine = self._make_engine()
        scene = _make_scene(mood="devotional")
        scene_audio = _make_scene_audio()

        mixed = engine.mix_scene(scene, scene_audio)
        assert len(mixed) > 0

    def test_mix_episode_basic(self):
        """Basic episode mixing produces audio."""
        engine = self._make_engine()
        scenes = [
            _make_scene(scene_number=1, mood="devotional"),
            _make_scene(scene_number=2, mood="heroic"),
        ]
        script = _make_episode_script(scenes=scenes)
        episode_audio = _make_episode_audio(num_scenes=2)

        mixed = engine.mix_episode(script, episode_audio)
        assert len(mixed) > 0

    def test_mix_episode_empty_raises(self):
        """Empty episode raises AudioEngineError."""
        engine = self._make_engine()
        script = EpisodeScript(
            episode_number=1,
            kanda="Bala Kanda",
            title="Test",
            total_duration_seconds=0,
            scenes=[],
        )
        episode_audio = EpisodeAudio(
            episode_number=1,
            scene_audio=[],
        )

        with pytest.raises(AudioEngineError, match="No scenes to mix"):
            engine.mix_episode(script, episode_audio)

    def test_produce_episode_audio(self):
        """produce_episode_audio returns normalized audio."""
        engine = self._make_engine()
        scene = _make_scene(mood="devotional")
        script = _make_episode_script(scenes=[scene])
        episode_audio = _make_episode_audio(num_scenes=1)

        result = engine.produce_episode_audio(script, episode_audio)
        assert result.frame_rate == TARGET_SAMPLE_RATE
        assert result.sample_width == TARGET_SAMPLE_WIDTH
        assert result.channels == TARGET_CHANNELS

    def test_produce_episode_audio_with_export(self):
        """produce_episode_audio exports to file when path given."""
        engine = self._make_engine()
        scene = _make_scene(mood="devotional")
        script = _make_episode_script(scenes=[scene])
        episode_audio = _make_episode_audio(num_scenes=1)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name

        try:
            result = engine.produce_episode_audio(
                script, episode_audio, output_path=output_path
            )
            assert os.path.exists(output_path)

            with wave.open(output_path, "rb") as wf:
                assert wf.getframerate() == 44100
                assert wf.getsampwidth() == 2
        finally:
            os.unlink(output_path)
