"""Regenerate all music tracks (synthesized) for all moods."""
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
DURATION = 30000


def make_drone(base_freq, overtone_freq, vol=-22):
    base = Sine(base_freq).to_audio_segment(duration=DURATION, volume=vol)
    overtone = Sine(overtone_freq).to_audio_segment(duration=DURATION, volume=vol - 6)
    return base.overlay(overtone).fade_in(2000).fade_out(2000)


def make_rhythm(freq, pattern_ms, vol=-16):
    clip = AudioSegment.silent(duration=0)
    for _ in range(DURATION // sum(pattern_ms)):
        for dur in pattern_ms:
            beat = Sine(freq).to_audio_segment(duration=min(dur, 100), volume=vol)
            beat = beat.fade_in(5).fade_out(min(dur, 80))
            clip += beat + AudioSegment.silent(duration=max(0, dur - 100))
    return clip[:DURATION].fade_in(1000).fade_out(1000)


TRACKS = {
    "devotional_track1": lambda: make_drone(261, 392),
    "devotional_track2": lambda: make_drone(220, 330),
    "devotional_track3": lambda: make_drone(196, 294),
    "dramatic_track1": lambda: make_drone(65, 98, vol=-18).overlay(
        WhiteNoise().to_audio_segment(duration=DURATION, volume=-35).low_pass_filter(400)
    ),
    "dramatic_track2": lambda: make_drone(73, 110, vol=-18).overlay(
        WhiteNoise().to_audio_segment(duration=DURATION, volume=-36).low_pass_filter(300)
    ),
    "dramatic_track3": lambda: make_drone(55, 82, vol=-20).overlay(
        make_rhythm(80, [500, 500, 250, 250, 500], vol=-26)
    ),
    "serene_track1": lambda: make_drone(523, 784, vol=-28).overlay(
        WhiteNoise().to_audio_segment(duration=DURATION, volume=-35).low_pass_filter(1500).high_pass_filter(300)
    ),
    "serene_track2": lambda: make_drone(440, 659, vol=-28),
    "serene_track3": lambda: make_drone(392, 587, vol=-28).overlay(
        WhiteNoise().to_audio_segment(duration=DURATION, volume=-36).low_pass_filter(2000).high_pass_filter(400)
    ),
    "hopeful_track1": lambda: make_drone(329, 493, vol=-24),
    "hopeful_track2": lambda: make_drone(349, 523, vol=-24),
    "hopeful_track3": lambda: make_drone(392, 587, vol=-24),
    "mysterious_track1": lambda: make_drone(55, 58, vol=-22).overlay(
        WhiteNoise().to_audio_segment(duration=DURATION, volume=-38).low_pass_filter(300)
    ),
    "mysterious_track2": lambda: make_drone(62, 65, vol=-22).overlay(
        WhiteNoise().to_audio_segment(duration=DURATION, volume=-38).low_pass_filter(250)
    ),
    "mysterious_track3": lambda: make_drone(49, 52, vol=-24).overlay(
        WhiteNoise().to_audio_segment(duration=DURATION, volume=-40).low_pass_filter(200)
    ),
    "battle_track1": lambda: make_rhythm(80, [300, 300, 150, 150, 300], vol=-14).overlay(
        make_rhythm(120, [150, 150, 150, 150, 300, 300], vol=-18)
    ),
    "battle_track2": lambda: make_rhythm(60, [400, 200, 200, 400], vol=-14).overlay(
        WhiteNoise().to_audio_segment(duration=DURATION, volume=-30).low_pass_filter(500)
    ),
    "melancholy_track1": lambda: make_drone(196, 233, vol=-26).overlay(
        WhiteNoise().to_audio_segment(duration=DURATION, volume=-38).low_pass_filter(600)
    ),
    "celebratory_track1": lambda: make_rhythm(150, [200, 200, 100, 100, 200], vol=-16).overlay(
        make_drone(523, 659, vol=-26)
    ),
    "festive_track1": lambda: make_rhythm(140, [150, 150, 150, 150, 200, 200], vol=-16).overlay(
        make_drone(440, 554, vol=-26)
    ),
    "joyful_track1": lambda: make_drone(523, 659, vol=-22).overlay(
        make_drone(784, 988, vol=-28)
    ),
    "miraculous_track1": lambda: make_drone(528, 639, vol=-22).overlay(
        Sine(396).to_audio_segment(duration=DURATION, volume=-28)
    ).fade_in(3000).fade_out(3000),
}


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Generating {len(TRACKS)} music tracks...\n")

    for name, generator in TRACKS.items():
        clip = generator()
        clip = clip.set_frame_rate(44100).set_channels(2).set_sample_width(2)
        filepath = os.path.join(OUTPUT_DIR, f"{name}.mp3")
        clip.export(filepath, format="mp3", bitrate="192k")
        size_kb = os.path.getsize(filepath) // 1024
        print(f"  {name}.mp3 ({len(clip)/1000:.1f}s, {size_kb} KB)")

    print(f"\nDone! {len(TRACKS)} tracks. Total: {len(os.listdir(OUTPUT_DIR))} files in assets/music/")


if __name__ == "__main__":
    main()
