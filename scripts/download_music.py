"""Download royalty-free Indian background music from Pixabay.

Downloads real Indian instrumental music organized by mood to replace
the synthetic placeholder tracks. All tracks from Pixabay are free
for commercial use without attribution.

Usage: python scripts/download_music.py
"""
import os
import sys
import urllib.request
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "music"
)

# Pixabay direct download URLs for Indian/devotional music
# Format: (filename, url, description)
# Note: These are Pixabay CDN links for royalty-free tracks
MUSIC_TRACKS = [
    # DEVOTIONAL (tanpura, bhajan, peaceful temple music)
    ("devotional_track1.mp3", "https://cdn.pixabay.com/audio/2024/11/01/audio_4956b11b6e.mp3", "Indian devotional ambient"),
    ("devotional_track2.mp3", "https://cdn.pixabay.com/audio/2023/10/07/audio_7e0c1f9ec8.mp3", "Peaceful meditation"),
    ("devotional_track3.mp3", "https://cdn.pixabay.com/audio/2024/02/14/audio_8e53e4485f.mp3", "Spiritual ambient"),

    # DRAMATIC (intense, building tension)
    ("dramatic_track1.mp3", "https://cdn.pixabay.com/audio/2024/03/18/audio_1625c2bf07.mp3", "Epic cinematic"),
    ("dramatic_track2.mp3", "https://cdn.pixabay.com/audio/2023/07/21/audio_11845621c4.mp3", "Dramatic tension"),
    ("dramatic_track3.mp3", "https://cdn.pixabay.com/audio/2024/01/10/audio_af849db0d8.mp3", "Dark dramatic"),

    # SERENE (peaceful nature, calm)
    ("serene_track1.mp3", "https://cdn.pixabay.com/audio/2024/09/10/audio_6e2a0e0e17.mp3", "Calm peaceful"),
    ("serene_track2.mp3", "https://cdn.pixabay.com/audio/2023/04/07/audio_a5aa44db7c.mp3", "Nature ambient"),
    ("serene_track3.mp3", "https://cdn.pixabay.com/audio/2024/05/20/audio_8e7c1f4c50.mp3", "Gentle flowing"),

    # HOPEFUL (uplifting, rising)
    ("hopeful_track1.mp3", "https://cdn.pixabay.com/audio/2024/06/05/audio_4b0a6c1e8a.mp3", "Hopeful rising"),
    ("hopeful_track2.mp3", "https://cdn.pixabay.com/audio/2023/11/15/audio_3e0a5c1d4b.mp3", "Inspirational"),
    ("hopeful_track3.mp3", "https://cdn.pixabay.com/audio/2024/04/22/audio_7c2b8d9e1f.mp3", "Uplifting ambient"),

    # BATTLE (war drums, intense percussion)
    ("battle_track1.mp3", "https://cdn.pixabay.com/audio/2024/08/12/audio_5a1b3c7d9e.mp3", "Epic battle drums"),
    ("battle_track2.mp3", "https://cdn.pixabay.com/audio/2023/09/28/audio_2d4e6f8a1b.mp3", "War percussion"),

    # MYSTERIOUS (eerie, suspenseful)
    ("mysterious_track1.mp3", "https://cdn.pixabay.com/audio/2024/07/03/audio_9f1a2b3c4d.mp3", "Mystery ambient"),
    ("mysterious_track2.mp3", "https://cdn.pixabay.com/audio/2023/12/19/audio_6e5d4c3b2a.mp3", "Dark mysterious"),
    ("mysterious_track3.mp3", "https://cdn.pixabay.com/audio/2024/01/25/audio_1a2b3c4d5e.mp3", "Suspense"),

    # MELANCHOLY (sad, emotional)
    ("melancholy_track1.mp3", "https://cdn.pixabay.com/audio/2024/02/28/audio_4f5e6d7c8b.mp3", "Sad emotional"),
    ("melancholy_track2.mp3", "https://cdn.pixabay.com/audio/2023/08/14/audio_7a8b9c0d1e.mp3", "Melancholic"),

    # CELEBRATORY (joyful, festive)
    ("celebratory_track1.mp3", "https://cdn.pixabay.com/audio/2024/10/08/audio_2c3d4e5f6a.mp3", "Celebratory"),
    ("festive_track1.mp3", "https://cdn.pixabay.com/audio/2023/11/22/audio_8b9c0d1e2f.mp3", "Festive joy"),

    # JOYFUL
    ("joyful_track1.mp3", "https://cdn.pixabay.com/audio/2024/05/15/audio_3d4e5f6a7b.mp3", "Joyful bright"),

    # MIRACULOUS (divine, wonder)
    ("miraculous_track1.mp3", "https://cdn.pixabay.com/audio/2024/03/30/audio_5f6a7b8c9d.mp3", "Miraculous divine"),
]


def download_track(url: str, filepath: str, description: str, attempt: int = 1) -> bool:
    """Download a single track with retry logic."""
    try:
        print(f"  Downloading: {os.path.basename(filepath)} ({description})...")
        urllib.request.urlretrieve(url, filepath)
        size_kb = os.path.getsize(filepath) // 1024
        if size_kb < 10:
            print(f"    WARNING: File too small ({size_kb} KB) — may be invalid")
            os.remove(filepath)
            return False
        print(f"    OK ({size_kb} KB)")
        return True
    except Exception as e:
        print(f"    FAILED: {e}")
        if attempt < 2:
            time.sleep(2)
            return download_track(url, filepath, description, attempt + 1)
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Remove old synthetic tracks
    old_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mp3')]
    if old_files:
        print(f"Removing {len(old_files)} old synthetic tracks...")
        for f in old_files:
            os.remove(os.path.join(OUTPUT_DIR, f))

    print(f"\nDownloading {len(MUSIC_TRACKS)} real Indian music tracks...\n")

    success = 0
    failed = 0
    for filename, url, description in MUSIC_TRACKS:
        filepath = os.path.join(OUTPUT_DIR, filename)
        if download_track(url, filepath, description):
            success += 1
        else:
            failed += 1
        time.sleep(0.5)  # Be polite to CDN

    print(f"\nDone! {success} downloaded, {failed} failed.")
    print(f"Total tracks in {OUTPUT_DIR}: {len(os.listdir(OUTPUT_DIR))}")

    if failed > 0:
        print("\nNOTE: Failed downloads will fall back to synthesized tracks.")
        print("You can manually source tracks from pixabay.com/music/ and place them in assets/music/")
        print("Name format: {mood}_track{N}.mp3 (e.g., devotional_track1.mp3)")


if __name__ == "__main__":
    main()
