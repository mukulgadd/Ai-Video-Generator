"""Generate additional background music tracks for mood variety.

Creates 2 more tracks per mood that will repeat most heavily:
devotional, dramatic, serene, mysterious, hopeful.
Uses layered sine waves and patterns to create distinct ambient loops.
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydub import AudioSegment
from pydub.generators import Sine, WhiteNoise

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "music"
)

DURATION = 30000  # 30 seconds each (will be looped by audio engine)


def _devotional_track2():
    """Devotional ambient - tanpura-like drone."""
    sa = Sine(261).to_audio_segment(duration=DURATION, volume=-22)
    pa = Sine(392).to_audio_segment(duration=DURATION, volume=-28)
    sa_low = Sine(130).to_audio_segment(duration=DURATION, volume=-25)
    clip = sa.overlay(pa).overlay(sa_low)
    return clip.fade_in(2000).fade_out(2000)


def _devotional_track3():
    """Devotional ambient - bell drone with harmonics."""
    base = Sine(220).to_audio_segment(duration=DURATION, volume=-24)
    h2 = Sine(440).to_audio_segment(duration=DURATION, volume=-30)
    h3 = Sine(660).to_audio_segment(duration=DURATION, volume=-35)
    clip = base.overlay(h2).overlay(h3)
    return clip.fade_in(3000).fade_out(3000)


def _dramatic_track2():
    """Dramatic tension - low pulsing drone."""
    clip = AudioSegment.silent(duration=0)
    for i in range(60):
        vol = -18 if i % 4 == 0 else -28
        pulse = Sine(65).to_audio_segment(duration=500, volume=vol)
        pulse = pulse.fade_in(50).fade_out(200)
        clip += pulse
    return clip.fade_in(1000).fade_out(2000)


def _dramatic_track3():
    """Dramatic atmosphere - strings-like sustain."""
    t1 = Sine(196).to_audio_segment(duration=DURATION, volume=-20)
    t2 = Sine(233).to_audio_segment(duration=DURATION, volume=-24)
    noise = WhiteNoise().to_audio_segment(duration=DURATION, volume=-38)
    noise = noise.low_pass_filter(500)
    clip = t1.overlay(t2).overlay(noise)
    return clip.fade_in(2000).fade_out(3000)


def _serene_track2():
    """Serene nature - soft flowing tones."""
    notes = [523, 659, 784, 659, 523, 392, 523, 659]
    clip = AudioSegment.silent(duration=0)
    for _ in range(4):
        for note in notes:
            tone = Sine(note).to_audio_segment(duration=900, volume=-28)
            tone = tone.fade_in(200).fade_out(400)
            clip += tone
    return clip[:DURATION].fade_in(2000).fade_out(2000)


def _serene_track3():
    """Serene water - gentle white noise with high harmonics."""
    water = WhiteNoise().to_audio_segment(duration=DURATION, volume=-32)
    water = water.low_pass_filter(2000).high_pass_filter(400)
    harmony = Sine(784).to_audio_segment(duration=DURATION, volume=-35)
    clip = water.overlay(harmony)
    return clip.fade_in(2000).fade_out(2000)


def _mysterious_track2():
    """Mysterious dark ambient."""
    low = Sine(55).to_audio_segment(duration=DURATION, volume=-22)
    dissonance = Sine(58).to_audio_segment(duration=DURATION, volume=-28)
    noise = WhiteNoise().to_audio_segment(duration=DURATION, volume=-38)
    noise = noise.low_pass_filter(300)
    clip = low.overlay(dissonance).overlay(noise)
    return clip.fade_in(3000).fade_out(3000)


def _mysterious_track3():
    """Mysterious ethereal tones."""
    t1 = Sine(311).to_audio_segment(duration=DURATION, volume=-26)
    t2 = Sine(415).to_audio_segment(duration=DURATION, volume=-30)
    t3 = Sine(155).to_audio_segment(duration=DURATION, volume=-24)
    clip = t1.overlay(t2).overlay(t3)
    return clip.fade_in(3000).fade_out(3000)


def _hopeful_track2():
    """Hopeful rising major chord progression."""
    progression = [(261, 329, 392), (293, 369, 440), (329, 415, 493), (349, 440, 523)]
    clip = AudioSegment.silent(duration=0)
    for _ in range(4):
        for chord in progression:
            layers = AudioSegment.silent(duration=1800)
            for freq in chord:
                tone = Sine(freq).to_audio_segment(duration=1800, volume=-26)
                layers = layers.overlay(tone)
            layers = layers.fade_in(200).fade_out(400)
            clip += layers
    return clip[:DURATION].fade_in(2000).fade_out(2000)


def _hopeful_track3():
    """Hopeful flute-like ascending melody."""
    notes = [392, 440, 493, 523, 587, 659, 698, 784]
    clip = AudioSegment.silent(duration=0)
    for _ in range(8):
        for note in notes:
            tone = Sine(note).to_audio_segment(duration=450, volume=-24)
            tone = tone.fade_in(50).fade_out(200)
            clip += tone
    return clip[:DURATION].fade_in(1000).fade_out(2000)


TRACKS = [
    ("devotional_track2", _devotional_track2),
    ("devotional_track3", _devotional_track3),
    ("dramatic_track2", _dramatic_track2),
    ("dramatic_track3", _dramatic_track3),
    ("serene_track2", _serene_track2),
    ("serene_track3", _serene_track3),
    ("mysterious_track2", _mysterious_track2),
    ("mysterious_track3", _mysterious_track3),
    ("hopeful_track2", _hopeful_track2),
    ("hopeful_track3", _hopeful_track3),
]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Generating {len(TRACKS)} additional music tracks in {OUTPUT_DIR}/\n")

    for name, generator in TRACKS:
        clip = generator()
        clip = clip.set_frame_rate(44100).set_channels(2).set_sample_width(2)
        filepath = os.path.join(OUTPUT_DIR, f"{name}.mp3")
        clip.export(filepath, format="mp3", bitrate="192k")
        duration_s = len(clip) / 1000
        size_kb = os.path.getsize(filepath) // 1024
        print(f"  {name}.mp3 ({duration_s:.1f}s, {size_kb} KB)")

    print(f"\nDone! {len(TRACKS)} tracks generated.")
    print(f"Total music tracks now: {len(os.listdir(OUTPUT_DIR))}")


if __name__ == "__main__":
    main()
