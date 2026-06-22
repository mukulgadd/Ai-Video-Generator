# Ramayan Video Generator

Automated pipeline that generates daily 2-minute animated YouTube Shorts episodes of the Ramayan epic. Each episode features AI-generated artwork in Indian traditional art style, Hindi narration, background music, sound effects, Ken Burns video composition, and YouTube-ready branding — all running locally on Apple Silicon overnight.

**Channel:** सनातन रहस्य (Sanatan Rahasya)
**Cost:** ~₹3-4 per episode
**Runtime:** ~45 minutes per episode on Apple Silicon (M3 Pro)

---

## Features

- **Full Ramayan Coverage** — Sequential progression through all 7 Kandas (Bala → Uttara), automatically advancing between books
- **AI Script Generation** — Gemini 2.5 Flash writes structured explainer-style scripts with hooks, angles, revelations, and CTAs
- **Local Image Generation** — FLUX.1-schnell on Apple Silicon MPS (no cloud GPU cost)
- **Hindi Narration** — Edge TTS with 14 character-specific voice profiles (pitch/rate differentiated)
- **Smart Audio Mixing** — Mood-matched background music, ambient SFX, volume ducking (pydub)
- **Ken Burns Video** — Dynamic zoom/pan effects on keyframes via FFmpeg zoompan filters
- **English Subtitles** — Burned directly onto keyframes before composition
- **Video Branding** — Hook overlay, title card, end CTA, channel identity
- **YouTube Thumbnails** — 1280x720 CTR-optimized thumbnails with bold hook text
- **YouTube Metadata** — Auto-generated title, description, tags, hashtags for SEO
- **Quality Gates** — Script validation, sacred content safety, final video validation
- **Batch Generation** — Run overnight with caffeinate (Mac stays awake until done)
- **Restartable** — File-based state persists across restarts; no work is lost

---

## Quick Start

### Prerequisites

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.11+
- FFmpeg installed (`brew install ffmpeg`)
- ~12 GB disk for FLUX model weights (downloaded on first run)
- ~12 GB unified memory during inference

### Setup

```bash
# Clone
git clone <repo-url>
cd Personal-Youtube-Video-Genarator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your keys:
#   GEMINI_API_KEY=your_gemini_api_key
#   HF_TOKEN=your_huggingface_token
```

### Generate a Single Episode

```bash
python generate_episode.py
```

### Generate a Batch (overnight)

```bash
# Generate 5 episodes
python generate_batch.py --count 5

# Or use the nightly wrapper (prevents Mac from sleeping)
./run_nightly.sh 5
```

### Run with Scheduler (daemon mode)

```bash
python main.py
# Pipeline triggers daily at 06:00 UTC (configurable in config.yaml)
```

---

## Usage

### Single Episode (recommended for testing)

```bash
python generate_episode.py
```

Runs the full 10-step pipeline once:
1. Gets next story segment from database
2. Generates explainer script via Gemini
3. Generates keyframes via FLUX.1-schnell
4. Generates Hindi narration via Edge TTS
5. Mixes audio (narration + music + SFX)
6. Burns English subtitles onto keyframes
7. Composes Ken Burns video with FFmpeg
8. Adds branding (hook, title card, end CTA)
9. Generates YouTube thumbnail
10. Generates YouTube metadata

Output appears in `output/`:
```
output/
├── ramayan_e0001_bala_kanda_20260621.mp4    # Final branded video
├── ramayan_e0001_thumbnail.jpg              # YouTube thumbnail
├── ramayan_e0001_metadata.txt               # Title, description, tags
└── episode_0001_audio.wav                   # Intermediate audio
```

### Batch Generation

```bash
# Generate 5 episodes with default settings
python generate_batch.py --count 5

# Dry run (shows what would be generated)
python generate_batch.py --count 3 --dry-run
```

Logs are written to `logs/batch_YYYYMMDD_HHMMSS.log`.

### Nightly Run (recommended for production)

```bash
./run_nightly.sh 5
```

This shell script:
- Uses `caffeinate` to prevent Mac from sleeping
- Activates the virtual environment
- Runs `generate_batch.py` with the specified count
- Mac sleeps normally after completion

---

## Configuration

All settings live in `config.yaml`. Every field has a default — the file can be empty and the system will run.

Key settings:

```yaml
pipeline:
  schedule_time: "06:00"          # Daily trigger (daemon mode)
  retry_attempts: 3               # Retries per stage

animation:
  style_reference: "indian_traditional_art"
  resolution: [1080, 1920]        # Vertical 9:16
  fps: 24

narration:
  default_locale: "hi"            # Hindi
  tts_provider: "edge"            # Free, no API key
  character_voices:               # 14 character → voice_id mappings
    Rama: "voice_rama_01"
    Sita: "voice_sita_01"
    ...

audio:
  narration_boost_db: 6           # Narration louder than music by 6dB
  crossfade_seconds: 0.75         # Scene transition crossfade
```

See [SETUP.md](SETUP.md) for full configuration reference.

---

## Project Structure

```
.
├── main.py                    # Daemon entry point (APScheduler)
├── generate_episode.py        # Single episode (production pipeline)
├── generate_batch.py          # Batch generation with error isolation
├── run_nightly.sh             # Caffeinate + batch wrapper
├── config.yaml                # Pipeline configuration
├── requirements.txt           # Python dependencies
│
├── src/                       # Core pipeline modules (27 files)
│   ├── config_loader.py       # YAML config → validated dataclass tree
│   ├── story_manager.py       # Story DB + sequential progression
│   ├── script_engine.py       # Gemini-based script generation + safety
│   ├── animation_engine.py    # Keyframe orchestration + Protocols
│   ├── flux_image_generator.py  # FLUX.1-schnell on Apple Silicon
│   ├── narration_engine.py    # TTS orchestration + duration sync
│   ├── edge_tts_adapter.py    # Edge TTS with voice differentiation
│   ├── audio_engine.py        # Music + SFX + narration mixing
│   ├── ken_burns_compositor.py  # FFmpeg zoompan video composition
│   ├── subtitle_burner.py     # English subtitles on keyframes
│   ├── video_branding.py      # Hook/title/CTA branding
│   ├── thumbnail_generator.py # YouTube thumbnail generation
│   ├── youtube_metadata.py    # SEO metadata generation
│   ├── quality_gates.py       # Validation checkpoints
│   └── ...                    # See ARCHITECTURE.md for full list
│
├── ramayan_db/                # Story database + state
│   ├── metadata.json          # Current position (survives restarts)
│   └── kandas/1-7_*/segments/ # Story segments (JSON)
│
├── models/characters/         # 14 character definitions
│   └── {name}/character.json  # Name + prompt_description for AI
│
├── assets/
│   ├── music/                 # 20 mood-tagged background tracks
│   └── sfx/                   # 20+ sound effect clips
│
├── output/                    # Generated videos, thumbnails, metadata
├── logs/                      # Batch run logs
└── tests/                     # Property-based tests (Hypothesis)
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file — overview and quick start |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, components, protocols, data flow |
| [SETUP.md](SETUP.md) | Detailed installation and configuration guide |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute, code standards, testing |
| [PROJECT_HISTORY.md](PROJECT_HISTORY.md) | Evolution from inception to current state |
| [TECHNICAL_DOCS.md](TECHNICAL_DOCS.md) | Component reference and API documentation |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Script Generation | Gemini 2.5 Flash (google-genai SDK) |
| Image Generation | FLUX.1-schnell (diffusers, local MPS) |
| Text-to-Speech | Microsoft Edge TTS (free, Hindi) |
| Audio Processing | pydub |
| Video Composition | FFmpeg (zoompan, concat, mux) |
| Image Processing | Pillow (subtitles, thumbnails, branding) |
| Scheduling | APScheduler |
| Configuration | PyYAML |
| Testing | pytest + Hypothesis (property-based) |
| State Management | JSON files (file-based, restartable) |

---

## Output Specs

| Property | Value |
|----------|-------|
| Resolution | 1080x1920 (vertical 9:16) |
| Frame Rate | 24 FPS |
| Video Codec | H.264 |
| Audio Codec | AAC |
| Duration | 50-120 seconds (content + branding) |
| Thumbnail | 1280x720 JPEG |
| Language | Hindi narration + English subtitles |

---

## License

Private project. Not for redistribution.
