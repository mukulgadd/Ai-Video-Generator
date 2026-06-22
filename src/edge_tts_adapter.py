"""Edge TTS Adapter for the Ramayan Video Generator.

Implements the TTSProvider Protocol using Microsoft Edge TTS.
Free, no API key required, supports Hindi with male/female voices.

Available Hindi voices:
- hi-IN-MadhurNeural (Male)
- hi-IN-SwaraNeural (Female)
"""

import asyncio
import io
import tempfile
import wave
from typing import Optional

import edge_tts


# Map voice IDs used in config to actual Edge TTS voice names + pitch/rate adjustments
# Each entry: (voice_name, pitch_adjustment, rate_adjustment)
# Keep pitch shifts SUBTLE (±10-20Hz max) to avoid robotic sound
VOICE_MAP = {
    # Narrator: calm, authoritative (baseline)
    "narrator_v1": ("hi-IN-MadhurNeural", "+0Hz", "+0%"),
    # Rama: young, noble, slightly higher
    "voice_rama_01": ("hi-IN-MadhurNeural", "+10Hz", "+0%"),
    # Hanuman: energetic, slightly higher
    "voice_hanuman_01": ("hi-IN-MadhurNeural", "+15Hz", "+5%"),
    # Ravana: slightly deeper, slower
    "voice_ravana_01": ("hi-IN-MadhurNeural", "-15Hz", "-3%"),
    # Sita: gentle female
    "voice_sita_01": ("hi-IN-SwaraNeural", "+0Hz", "+0%"),
    # King Dasharatha: slightly deeper, slower (elderly)
    "voice_dasharatha_01": ("hi-IN-MadhurNeural", "-10Hz", "-3%"),
    # Lakshmana: young, alert
    "voice_lakshmana_01": ("hi-IN-MadhurNeural", "+12Hz", "+0%"),
    # Vishwamitra: commanding
    "voice_vishwamitra_01": ("hi-IN-MadhurNeural", "-5Hz", "+2%"),
    # Sage Vishwamitra (alias)
    "voice_vishwamitra_02": ("hi-IN-MadhurNeural", "-5Hz", "+2%"),
    # Sage Vasishtha: calm elderly
    "voice_vasishtha_01": ("hi-IN-MadhurNeural", "-8Hz", "-2%"),
    # Queens: each slightly different
    "voice_kausalya_01": ("hi-IN-SwaraNeural", "-5Hz", "-2%"),
    "voice_kaikeyi_01": ("hi-IN-SwaraNeural", "+5Hz", "+0%"),
    "voice_sumitra_01": ("hi-IN-SwaraNeural", "-10Hz", "-3%"),
    # Bharata: young
    "voice_bharata_01": ("hi-IN-MadhurNeural", "+8Hz", "+0%"),
    # Shatrughna: young, quiet
    "voice_shatrughna_01": ("hi-IN-MadhurNeural", "+5Hz", "-2%"),
}

# Default voice if mapping not found
DEFAULT_VOICE = ("hi-IN-MadhurNeural", "+0Hz", "+0%")


class EdgeTTSAdapter:
    """TTS adapter using Microsoft Edge TTS (free, no API key).

    Implements the TTSProvider Protocol from narration_engine.py.
    Generates WAV audio from text using Edge's neural voices.

    Supports Hindi (hi-IN) with two voices:
    - MadhurNeural (male) — used for Rama, Hanuman, Ravana, narrator
    - SwaraNeural (female) — used for Sita

    Voice mapping is configurable via the VOICE_MAP dict.
    """

    _WORDS_PER_SECOND = 2.5  # Fallback for duration estimation

    def __init__(self, voice_map: Optional[dict] = None):
        """Initialize the Edge TTS adapter.

        Args:
            voice_map: Optional dict mapping voice_id -> Edge TTS voice name.
                If None, uses the default VOICE_MAP.
        """
        self._voice_map = voice_map or VOICE_MAP

    def _resolve_voice(self, voice_id: str) -> tuple:
        """Resolve a config voice_id to (Edge TTS voice name, pitch, rate_offset)."""
        return self._voice_map.get(voice_id, DEFAULT_VOICE)

    def _speech_rate_to_string(self, speech_rate: float) -> str:
        """Convert a speech rate multiplier to Edge TTS rate string.

        Edge TTS uses strings like "+20%", "-10%", "+0%".
        speech_rate=1.0 -> "+0%", speech_rate=1.2 -> "+20%", etc.
        """
        percentage = int((speech_rate - 1.0) * 100)
        if percentage >= 0:
            return f"+{percentage}%"
        return f"{percentage}%"

    def synthesize(
        self,
        text: str,
        voice_id: str,
        locale: str,
        speech_rate: float,
    ) -> bytes:
        """Generate WAV audio from text using Edge TTS.

        Args:
            text: The text to synthesize.
            voice_id: Voice profile ID (mapped to Edge TTS voice + pitch/rate).
            locale: Language/locale code (e.g., "hi"). Used as fallback.
            speech_rate: Speech rate multiplier (1.0 = normal).

        Returns:
            WAV format audio bytes (16-bit, mono, 44100 Hz).
        """
        if not text or not text.strip():
            return self._generate_silent_wav(0.1)

        voice, pitch, rate_offset = self._resolve_voice(voice_id)

        # Combine the character-specific rate offset with the requested speech_rate
        # Parse the rate_offset percentage and combine with speech_rate
        base_rate = self._speech_rate_to_string(speech_rate)
        # If character has a rate offset, combine them
        if rate_offset != "+0%":
            char_offset = int(rate_offset.replace("%", ""))
            speech_offset = int((speech_rate - 1.0) * 100)
            combined = char_offset + speech_offset
            rate = f"+{combined}%" if combined >= 0 else f"{combined}%"
        else:
            rate = base_rate

        try:
            mp3_bytes = self._run_edge_tts(text, voice, rate, pitch)
            wav_bytes = self._mp3_to_wav(mp3_bytes)
            return wav_bytes
        except Exception:
            word_count = max(len(text.split()), 1)
            duration = word_count / self._WORDS_PER_SECOND / max(speech_rate, 0.1)
            return self._generate_silent_wav(max(duration, 0.1))

    def _run_edge_tts(self, text: str, voice: str, rate: str, pitch: str = "+0Hz") -> bytes:
        """Run Edge TTS and return raw MP3 bytes."""

        async def _generate():
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            mp3_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_data += chunk["data"]
            return mp3_data

        # Handle case where we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # We're inside an async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _generate())
                return future.result(timeout=30)
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(_generate())

    def _mp3_to_wav(self, mp3_bytes: bytes) -> bytes:
        """Convert MP3 bytes to WAV bytes using pydub."""
        from pydub import AudioSegment as PydubSegment

        mp3_buf = io.BytesIO(mp3_bytes)
        audio = PydubSegment.from_mp3(mp3_buf)

        # Convert to 44100 Hz, 16-bit, mono (matches project standard)
        audio = audio.set_frame_rate(44100).set_sample_width(2).set_channels(1)

        wav_buf = io.BytesIO()
        audio.export(wav_buf, format="wav")
        return wav_buf.getvalue()

    def _generate_silent_wav(self, duration_seconds: float) -> bytes:
        """Generate silent WAV as fallback."""
        sample_rate = 44100
        num_samples = int(sample_rate * duration_seconds)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00\x00" * num_samples)
        return buf.getvalue()
