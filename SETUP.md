# Setup Guide

Complete installation and configuration guide for the Ramayan Video Generator.

---

## System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| OS | macOS 13+ (Ventura) | macOS 14+ (Sonoma) |
| Chip | Apple Silicon (M1) | M3 Pro or higher |
| RAM | 16 GB unified memory | 36 GB unified memory |
| Disk | 20 GB free | 50 GB free |
| Python | 3.11 | 3.12 |
| FFmpeg | 5.0 | 6.0+ |

The pipeline is designed for Apple Silicon Macs. FLUX.1-schnell uses the MPS (Metal Performance Shaders) backend for GPU-accelerated inference. Intel Macs can run in CPU-only mode but will be significantly slower.

---

## Step 1: Install System Dependencies

### FFmpeg

```bash
brew install ffmpeg
```

Verify:
```bash
ffmpeg -version
ffprobe -version
```

### Python 3.11+

```bash
# If you don't have Python 3.11+:
brew install python@3.12
```

Verify:
```bash
python3 --version
# Should show 3.11.x or higher
```

---

## Step 2: Clone and Create Virtual Environment

```bash
git clone <repo-url>
cd Personal-Youtube-Video-Genarator

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Verify
which python
# Should show: .../Personal-Youtube-Video-Genarator/.venv/bin/python
```

---

## Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:

| Package | Purpose |
|---|---|
| `google-genai` | Gemini API client (script generation) |
| `openai` | OpenAI API client (backup LLM) |
| `python-dotenv` | Load .env file |
| `edge-tts` | Microsoft Edge TTS (Hindi narration) |
| `diffusers` | FLUX/SDXL model loading |
| `transformers` | T5 encoder for FLUX |
| `accelerate` | Model loading optimization |
| `safetensors` | Model weight format |
| `torch` | PyTorch (MPS backend) |
| `torchvision` | Image transforms |
| `Pillow` | Image processing (subtitles, thumbnails) |
| `pydub` | Audio mixing and processing |
| `librosa` | Audio analysis |
| `ffmpeg-python` | FFmpeg Python bindings |
| `pyyaml` | YAML config parsing |
| `apscheduler` | Daily scheduling |
| `boto3` | AWS S3 uploads |
| `google-cloud-storage` | GCS uploads |
| `hypothesis` | Property-based testing |
| `pytest` | Test runner |
| `jsonschema` | JSON schema validation |
| `requests` | HTTP requests (webhooks) |

Total install size: ~3 GB (mostly PyTorch and model dependencies).

---

## Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```env
# Required: Gemini API key for script generation
GEMINI_API_KEY=your_gemini_api_key_here

# Required: HuggingFace token for FLUX model access
HF_TOKEN=your_huggingface_token_here

# Optional: OpenAI key (backup LLM, not used by default)
# OPENAI_API_KEY=your_openai_key_here
```

### Getting a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click "Create API Key"
3. Copy the key into your `.env` file

Cost: Gemini 2.5 Flash is very cheap (~₹1-2 per episode for script generation).

### Getting a HuggingFace Token

1. Go to [HuggingFace Settings](https://huggingface.co/settings/tokens)
2. Create a new token (read access is sufficient)
3. Accept the [FLUX.1-schnell license](https://huggingface.co/black-forest-labs/FLUX.1-schnell) (free, just click "Agree")
4. Copy the token into your `.env` file

---

## Step 5: Verify Configuration

```bash
# Check config loads without errors
python -c "from src.config_loader import load_config; c = load_config('config.yaml'); print('Config OK:', c.pipeline.schedule_time)"
```

Expected output:
```
Config OK: 06:00
```

---

## Step 6: First Run (Model Download)

On the first run, FLUX.1-schnell model weights (~12 GB) will be downloaded from HuggingFace. This only happens once.

```bash
# Test with a single episode
python generate_episode.py
```

First-run timeline:
```
00:00  Script generation (Gemini API) — ~15 seconds
00:15  FLUX model download — 10-30 minutes (one-time, ~12 GB)
       After download: keyframe generation — ~30 minutes
30:15  Narration (Edge TTS) — ~45 seconds
31:00  Audio mixing — ~10 seconds
31:10  Subtitles + Ken Burns + Branding — ~3 minutes
34:10  Thumbnail + metadata — ~3 seconds
34:13  Done!
```

Subsequent runs skip the download and take ~45 minutes per episode.

### Verifying the Output

After completion, check `output/`:
```bash
ls -la output/ramayan_e*.mp4
ls -la output/ramayan_e*_thumbnail.jpg
cat output/ramayan_e*_metadata.txt
```

Play the video:
```bash
open output/ramayan_e0001_bala_kanda_*.mp4
```

---

## Configuration Reference

### config.yaml — Full Options

```yaml
# ─── Pipeline Settings ───────────────────────────────────────
pipeline:
  schedule_time: "06:00"            # Daily trigger time (HH:MM, UTC)
  target_duration_seconds: 120      # Target episode duration
  retry_attempts: 3                 # Max retries per pipeline stage

# ─── Animation / Image Generation ────────────────────────────
animation:
  style_reference: "indian_traditional_art"   # Style prompt prefix
  resolution: [1080, 1920]          # [width, height] — vertical 9:16
  fps: 24                           # Output frame rate
  model: "stable-diffusion-xl"      # Model identifier (cosmetic)
  lora_path: "./models/indian_art_lora.safetensors"  # LoRA weights (optional)

# ─── Narration / TTS ─────────────────────────────────────────
narration:
  default_locale: "hi"              # Language code (Hindi)
  narrator_voice: "narrator_v1"     # Default narrator voice ID
  tts_provider: "edge"              # TTS backend: edge|coqui|azure|elevenlabs
  character_voices:                 # Character → voice_id mapping
    Rama: "voice_rama_01"
    Sita: "voice_sita_01"
    Hanuman: "voice_hanuman_01"
    Ravana: "voice_ravana_01"
    King Dasharatha: "voice_dasharatha_01"
    Lakshmana: "voice_lakshmana_01"
    Vishwamitra: "voice_vishwamitra_01"
    Sage Vishwamitra: "voice_vishwamitra_02"
    Sage Vasishtha: "voice_vasishtha_01"
    Queen Kausalya: "voice_kausalya_01"
    Queen Kaikeyi: "voice_kaikeyi_01"
    Queen Sumitra: "voice_sumitra_01"
    Bharata: "voice_bharata_01"
    Shatrughna: "voice_shatrughna_01"

# ─── Audio Mixing ────────────────────────────────────────────
audio:
  music_library_path: "./assets/music/"
  sfx_library_path: "./assets/sfx/"
  narration_boost_db: 6             # Narration louder than music by this many dB
  crossfade_seconds: 0.75           # Crossfade between scenes (0.5-1.0)

# ─── Output Format ───────────────────────────────────────────
output:
  format: "mp4"
  video_codec: "h264"
  audio_codec: "aac"

# ─── Cloud Storage (optional) ────────────────────────────────
storage:
  provider: "s3"                    # s3 or gcs
  bucket: "ramayan-videos"
  path_prefix: "episodes/"

# ─── Platform Distribution (optional) ────────────────────────
distribution:
  youtube:
    enabled: false                  # Set true to auto-upload
    credentials_path: "./credentials/youtube.json"
  instagram:
    enabled: false
    credentials_path: "./credentials/instagram.json"

# ─── Failure Notifications ───────────────────────────────────
notifications:
  provider: "email"                 # email or webhook
  recipients: ["admin@example.com"]
```

---

## Directory Setup Checklist

After cloning, your workspace should have:

```
✓ config.yaml              — Pipeline configuration
✓ .env                     — API keys (you create this)
✓ requirements.txt         — Python dependencies
✓ ramayan_db/metadata.json — Story position state
✓ ramayan_db/kandas/       — Story segments (pre-populated for Kanda 1-2)
✓ models/characters/       — 14 character definitions
✓ assets/music/            — 20 background music tracks
✓ assets/sfx/              — 20+ sound effect clips
✓ output/                  — (created automatically on first run)
✓ logs/                    — (created automatically on first batch run)
```

---

## Troubleshooting

### "Gemini API key not provided"

```
ValueError: Gemini API key not provided. Set GEMINI_API_KEY env var or pass api_key.
```

Fix: Ensure `.env` has `GEMINI_API_KEY=your_key` and you're loading it (the scripts call `load_dotenv()` automatically).

### "FLUX model download stuck"

The FLUX.1-schnell model is ~12 GB. If download stalls:
1. Check your HuggingFace token is valid
2. Ensure you've accepted the FLUX license on HuggingFace
3. Try: `huggingface-cli login` and enter your token manually
4. Check network: `ping huggingface.co`

### "MPS device not available"

```
RuntimeError: MPS device not available
```

This means you're not on Apple Silicon, or macOS is too old. Fix:
- Ensure you're on an M1/M2/M3/M4 Mac
- Update to macOS 13+ (Ventura)
- The system will fallback to CPU (much slower)

### "FFmpeg not found"

```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

Fix: `brew install ffmpeg`

### "Duration too long" (quality gate failure)

The quality gate rejects videos outside 50-120s. This can happen when:
- Gemini generates too many/few scenes
- Narration runs long

The episode is NOT marked complete — just re-run and it retries the same segment.

### "Sacred content safety check failed"

Gemini sometimes generates content that questions divinity or disrespects characters. The safety gate catches this and rejects the script. Re-running usually produces a compliant script.

### Out of Memory during FLUX inference

If you see crashes during image generation:
- Close other heavy apps (browsers with many tabs, etc.)
- FLUX needs ~12 GB unified memory
- The generator produces at 512x896 then resizes (already optimized)
- If still failing, switch to `GeminiImageGenerator` (cloud, no local memory needed)

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_config_loader.py -v

# Run property-based tests only
pytest tests/ -v -k "hypothesis"

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Production Nightly Setup

For unattended overnight generation:

### Option 1: Shell script (recommended)

```bash
# Make executable (once)
chmod +x run_nightly.sh

# Run before bed — generates 5 episodes
./run_nightly.sh 5
```

The script uses `caffeinate` to keep the Mac awake. It sleeps normally after completion.

### Option 2: macOS launchd (auto-start daily)

Create `~/Library/LaunchAgents/com.ramayan.generator.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ramayan.generator</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/mukul.gaddhyan/Git/Personal-Youtube-Video-Genarator/run_nightly.sh</string>
        <string>5</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>22</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/ramayan_generator.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/ramayan_generator_err.log</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.ramayan.generator.plist
```

This triggers every night at 10 PM automatically.

### Option 3: Daemon mode (APScheduler)

```bash
python main.py
```

Runs as a long-lived process, triggering daily at `config.pipeline.schedule_time`. Less practical than the nightly script since it requires the process to stay alive.

---

## Switching Image Generators

### Use FLUX (default, local)

In `generate_episode.py`:
```python
from src.flux_image_generator import FluxImageGenerator
animation_engine = AnimationEngine(
    config=config.animation, image_generator=FluxImageGenerator(num_inference_steps=4)
)
```

### Use SDXL (backup, local)

```python
from src.sd_image_generator import SDXLImageGenerator
animation_engine = AnimationEngine(
    config=config.animation, image_generator=SDXLImageGenerator(num_inference_steps=15)
)
```

### Use Gemini Imagen (cloud, no GPU needed)

```python
from src.gemini_image_generator import GeminiImageGenerator
animation_engine = AnimationEngine(
    config=config.animation, image_generator=GeminiImageGenerator()
)
```

Requires `GEMINI_API_KEY` in `.env`. Costs more per episode but avoids all local GPU constraints.

---

## Disk Space Management

Model weights and generated content accumulate:

| Item | Size | Location |
|---|---|---|
| FLUX model | ~12 GB | `~/.cache/huggingface/` |
| SDXL model | ~7 GB | `~/.cache/huggingface/` (if used) |
| Generated videos | ~15 MB each | `output/` |
| Audio intermediates | ~12 MB each | `output/` |
| Temp keyframes | ~50 MB/episode | `/tmp/` (auto-cleaned) |

To clean up old episodes:
```bash
# Move completed episodes to archive
mv output/ramayan_e00{01..05}_* output/archive/

# Clear HuggingFace cache (re-downloads on next run)
rm -rf ~/.cache/huggingface/hub/models--black-forest-labs--FLUX.1-schnell
```
