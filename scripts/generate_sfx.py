"""Generate placeholder SFX audio clips using pydub.

Creates short ambient sound effects that provide atmosphere until
we source higher-quality royalty-free clips. These use tone generation,
noise, and filtering to approximate each sound type.

Clip names match those in src/sfx_mapper.py MOOD_AMBIENT_MAP.
"""
import os
import sys
import random
import struct
import wave
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydub import AudioSegment
from pydub.generators import Sine, WhiteNoise

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "sfx"
)

# Each SFX: (filename, duration_ms, generator_function)
# Generator functions return a pydub AudioSegment


def _temple_bells_soft():
    """Gentle temple bell resonance."""
    bell = Sine(800).to_audio_segment(duration=200, volume=-20)
    bell = bell.fade_in(10).fade_out(150)
    silence = AudioSegment.silent(duration=600)
    clip = AudioSegment.silent(duration=0)
    for _ in range(5):
        freq = random.choice([780, 800, 820, 850])
        b = Sine(freq).to_audio_segment(duration=200, volume=-18)
        b = b.fade_in(10).fade_out(180)
        clip += b + silence
    return clip.fade_out(500)


def _incense_wind():
    """Soft airy whoosh."""
    noise = WhiteNoise().to_audio_segment(duration=4000, volume=-35)
    noise = noise.low_pass_filter(800).fade_in(1000).fade_out(1000)
    return noise


def _fire_crackling():
    """Crackling fire sound approximation."""
    clip = AudioSegment.silent(duration=0)
    for _ in range(40):
        freq = random.randint(100, 400)
        dur = random.randint(30, 80)
        crackle = Sine(freq).to_audio_segment(duration=dur, volume=-25)
        crackle = crackle.fade_in(5).fade_out(dur - 10)
        gap = AudioSegment.silent(duration=random.randint(50, 150))
        clip += crackle + gap
    return clip.fade_in(200).fade_out(300)


def _birds_morning():
    """Morning birds chirping."""
    clip = AudioSegment.silent(duration=0)
    for _ in range(15):
        freq = random.randint(2000, 4000)
        dur = random.randint(80, 200)
        chirp = Sine(freq).to_audio_segment(duration=dur, volume=-22)
        chirp = chirp.fade_in(10).fade_out(dur - 20)
        gap = AudioSegment.silent(duration=random.randint(200, 600))
        clip += chirp + gap
    return clip.fade_out(500)


def _river_gentle():
    """Gentle flowing water."""
    noise = WhiteNoise().to_audio_segment(duration=5000, volume=-30)
    noise = noise.low_pass_filter(1200).high_pass_filter(200)
    return noise.fade_in(500).fade_out(500)


def _wind_howl():
    """Wind howling."""
    noise = WhiteNoise().to_audio_segment(duration=4000, volume=-28)
    noise = noise.low_pass_filter(600).fade_in(1000).fade_out(1500)
    return noise


def _wind_eerie():
    """Eerie wind."""
    noise = WhiteNoise().to_audio_segment(duration=4000, volume=-32)
    noise = noise.low_pass_filter(400).high_pass_filter(100)
    return noise.fade_in(1500).fade_out(1500)


def _wind_lonely():
    """Lonely desolate wind."""
    noise = WhiteNoise().to_audio_segment(duration=5000, volume=-34)
    noise = noise.low_pass_filter(500)
    return noise.fade_in(2000).fade_out(2000)


def _wind_gentle():
    """Gentle breeze."""
    noise = WhiteNoise().to_audio_segment(duration=4000, volume=-38)
    noise = noise.low_pass_filter(400)
    return noise.fade_in(1000).fade_out(1000)


def _thunder_distant():
    """Distant thunder rumble."""
    rumble = Sine(60).to_audio_segment(duration=2000, volume=-15)
    rumble = rumble.overlay(WhiteNoise().to_audio_segment(duration=2000, volume=-30))
    rumble = rumble.low_pass_filter(200).fade_in(200).fade_out(1500)
    return rumble


def _drums_war():
    """War drums - deep rhythmic beats."""
    clip = AudioSegment.silent(duration=0)
    for _ in range(8):
        beat = Sine(80).to_audio_segment(duration=150, volume=-12)
        beat = beat.fade_in(5).fade_out(100)
        gap = AudioSegment.silent(duration=350)
        clip += beat + gap
    return clip.fade_out(300)


def _drums_victory():
    """Triumphant drum pattern."""
    clip = AudioSegment.silent(duration=0)
    for i in range(12):
        freq = 100 if i % 3 == 0 else 150
        beat = Sine(freq).to_audio_segment(duration=100, volume=-14)
        beat = beat.fade_in(5).fade_out(80)
        gap = AudioSegment.silent(duration=200 if i % 3 == 0 else 150)
        clip += beat + gap
    return clip.fade_out(200)


def _drums_festive():
    """Festive quick drums."""
    clip = AudioSegment.silent(duration=0)
    for _ in range(16):
        freq = random.choice([120, 140, 160])
        beat = Sine(freq).to_audio_segment(duration=80, volume=-16)
        beat = beat.fade_in(5).fade_out(60)
        gap = AudioSegment.silent(duration=random.randint(100, 200))
        clip += beat + gap
    return clip.fade_out(200)


def _crowd_cheering():
    """Crowd noise."""
    noise = WhiteNoise().to_audio_segment(duration=4000, volume=-22)
    noise = noise.low_pass_filter(3000).high_pass_filter(300)
    return noise.fade_in(500).fade_out(1000)


def _conch_shell():
    """Conch shell blast."""
    tone = Sine(220).to_audio_segment(duration=3000, volume=-15)
    overtone = Sine(440).to_audio_segment(duration=3000, volume=-25)
    clip = tone.overlay(overtone)
    return clip.fade_in(300).fade_out(1000)


def _divine_light():
    """Ethereal divine sound."""
    t1 = Sine(528).to_audio_segment(duration=4000, volume=-22)
    t2 = Sine(396).to_audio_segment(duration=4000, volume=-28)
    t3 = Sine(639).to_audio_segment(duration=4000, volume=-30)
    clip = t1.overlay(t2).overlay(t3)
    return clip.fade_in(1000).fade_out(1500)


def _om_chant():
    """Om chant approximation."""
    base = Sine(136).to_audio_segment(duration=4000, volume=-18)
    overtone = Sine(272).to_audio_segment(duration=4000, volume=-28)
    clip = base.overlay(overtone)
    return clip.fade_in(1000).fade_out(1500)


def _flute_distant():
    """Distant flute melody."""
    clip = AudioSegment.silent(duration=0)
    notes = [523, 587, 659, 698, 784, 698, 659, 587]
    for note in notes:
        tone = Sine(note).to_audio_segment(duration=400, volume=-24)
        tone = tone.fade_in(50).fade_out(100)
        clip += tone
    return clip.fade_in(200).fade_out(500)


def _rain_soft():
    """Soft rain."""
    noise = WhiteNoise().to_audio_segment(duration=5000, volume=-28)
    noise = noise.low_pass_filter(4000).high_pass_filter(500)
    return noise.fade_in(1000).fade_out(1000)


def _swords_clash():
    """Swords clashing."""
    clip = AudioSegment.silent(duration=0)
    for _ in range(6):
        freq = random.randint(2000, 5000)
        clash = Sine(freq).to_audio_segment(duration=50, volume=-12)
        clash = clash.fade_out(40)
        gap = AudioSegment.silent(duration=random.randint(400, 700))
        clip += clash + gap
    return clip


def _arrows_flying():
    """Arrows whooshing."""
    clip = AudioSegment.silent(duration=0)
    for _ in range(5):
        noise = WhiteNoise().to_audio_segment(duration=200, volume=-22)
        noise = noise.high_pass_filter(2000).fade_in(20).fade_out(150)
        gap = AudioSegment.silent(duration=random.randint(500, 800))
        clip += noise + gap
    return clip


def _bells_joyful():
    """Joyful ringing bells."""
    clip = AudioSegment.silent(duration=0)
    for _ in range(10):
        freq = random.choice([1000, 1200, 1400, 1600])
        bell = Sine(freq).to_audio_segment(duration=150, volume=-18)
        bell = bell.fade_in(5).fade_out(130)
        gap = AudioSegment.silent(duration=random.randint(150, 300))
        clip += bell + gap
    return clip.fade_out(300)


def _ocean_waves():
    """Ocean waves."""
    clip = AudioSegment.silent(duration=0)
    for _ in range(3):
        wave_sound = WhiteNoise().to_audio_segment(duration=1500, volume=-26)
        wave_sound = wave_sound.low_pass_filter(800).fade_in(500).fade_out(800)
        clip += wave_sound
    return clip


def _horses_gallop():
    """Horses galloping."""
    clip = AudioSegment.silent(duration=0)
    for _ in range(12):
        beat = Sine(100).to_audio_segment(duration=60, volume=-16)
        beat = beat.fade_out(50)
        gap = AudioSegment.silent(duration=random.randint(150, 250))
        clip += beat + gap
    return clip


# All SFX to generate
SFX_LIST = [
    ("temple_bells_soft", _temple_bells_soft),
    ("incense_wind", _incense_wind),
    ("fire_crackling", _fire_crackling),
    ("birds_morning", _birds_morning),
    ("river_gentle", _river_gentle),
    ("wind_howl", _wind_howl),
    ("wind_eerie", _wind_eerie),
    ("wind_lonely", _wind_lonely),
    ("wind_gentle", _wind_gentle),
    ("thunder_distant", _thunder_distant),
    ("drums_war", _drums_war),
    ("drums_victory", _drums_victory),
    ("drums_festive", _drums_festive),
    ("crowd_cheering", _crowd_cheering),
    ("conch_shell", _conch_shell),
    ("divine_light", _divine_light),
    ("om_chant", _om_chant),
    ("flute_distant", _flute_distant),
    ("rain_soft", _rain_soft),
    ("swords_clash", _swords_clash),
    ("arrows_flying", _arrows_flying),
    ("bells_joyful", _bells_joyful),
    ("ocean_waves", _ocean_waves),
    ("horses_gallop", _horses_gallop),
]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Remove old .gitkeep
    gitkeep = os.path.join(OUTPUT_DIR, ".gitkeep")
    if os.path.exists(gitkeep):
        os.remove(gitkeep)

    print(f"Generating {len(SFX_LIST)} SFX clips in {OUTPUT_DIR}/\n")

    for name, generator in SFX_LIST:
        clip = generator()
        # Normalize to consistent format
        clip = clip.set_frame_rate(44100).set_channels(1).set_sample_width(2)
        filepath = os.path.join(OUTPUT_DIR, f"{name}.mp3")
        clip.export(filepath, format="mp3", bitrate="128k")
        duration_s = len(clip) / 1000
        size_kb = os.path.getsize(filepath) // 1024
        print(f"  {name}.mp3 ({duration_s:.1f}s, {size_kb} KB)")

    print(f"\nDone! {len(SFX_LIST)} SFX clips generated.")


if __name__ == "__main__":
    main()
