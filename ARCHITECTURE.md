# Architecture Document

## Overview

The Ramayan Video Generator is a modular, sequential pipeline that transforms story segments from a JSON database into fully branded YouTube Shorts videos. The system is designed around Protocol-based dependency injection, file-based state persistence, and multi-layer error resilience.

The pipeline runs on a single Apple Silicon Mac, generates episodes overnight (~45 min each), and produces upload-ready MP4 videos with thumbnails and metadata.

---

## System Diagram

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                              ENTRY POINTS                                      │
├─────────────────┬──────────────────────┬────────────────────┬─────────────────┤
│  main.py        │  generate_episode.py │  generate_batch.py │  run_nightly.sh │
│  (APScheduler   │  (Single episode,    │  (N episodes,      │  (caffeinate +  │
│   daily daemon) │   production path)   │   error isolation) │   batch wrapper)│
└────────┬────────┴──────────┬───────────┴─────────┬──────────┴─────────────────┘
         │                   │                     │
         ▼                   ▼                     ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                    │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────┐                  │
│  │        VideoGeneratorOrchestrator                        │                  │
│  │  - Sequential stage execution                            │                  │
│  │  - Per-stage retry (configurable attempts)               │                  │
│  │  - Failure notifications (email/webhook)                 │                  │
│  │  - Pipeline result logging                               │                  │
│  └─────────────────────────────────────────────────────────┘                  │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────┐                  │
│  │  PipelineScheduler (APScheduler CronTrigger)             │                  │
│  │  - Fires daily at configured time (default 06:00 UTC)    │                  │
│  │  - Calls orchestrator.run_pipeline()                     │                  │
│  └─────────────────────────────────────────────────────────┘                  │
└───────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE STAGES (Sequential, 10 Steps)                      │
│                                                                               │
│  ┌─────────┐   ┌─────────┐   ┌───────────┐   ┌──────────┐   ┌─────────┐    │
│  │ Step 1  │ → │ Step 2  │ → │  Step 3   │ → │  Step 4  │ → │ Step 5  │    │
│  │ Story   │   │ Script  │   │ Keyframe  │   │Narration │   │  Audio  │    │
│  │ Manager │   │ Engine  │   │Generation │   │  (TTS)   │   │ Mixing  │    │
│  └─────────┘   └─────────┘   └───────────┘   └──────────┘   └─────────┘    │
│                                                                               │
│  ┌─────────┐   ┌───────────┐   ┌───────────┐   ┌──────────┐   ┌─────────┐  │
│  │ Step 6  │ → │  Step 7   │ → │  Step 8   │ → │  Step 9  │ → │ Step 10 │  │
│  │Subtitles│   │ Ken Burns │   │ Branding  │   │Thumbnail │   │Metadata │  │
│  │  Burn   │   │Compositor │   │(hook/CTA) │   │Generator │   │  (YT)   │  │
│  └─────────┘   └───────────┘   └───────────┘   └──────────┘   └─────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    QUALITY GATES (Validation Checkpoints)                      │
│                                                                               │
│  ┌────────────────────┐   ┌─────────────────────┐   ┌──────────────────────┐ │
│  │  Script Quality    │   │  Sacred Content     │   │  Final Video         │ │
│  │  Gate              │   │  Safety Check       │   │  Validation          │ │
│  │  (post-Step 2)     │   │  (post-Step 2)      │   │  (post-Step 7)       │ │
│  └────────────────────┘   └─────────────────────┘   └──────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         OUTPUT ARTIFACTS                                       │
│                                                                               │
│  ramayan_e{NNNN}_{kanda}_{date}.mp4    (1080x1920, H.264+AAC, branded)       │
│  ramayan_e{NNNN}_thumbnail.jpg          (1280x720, CTR-optimized)             │
│  ramayan_e{NNNN}_metadata.txt           (title, description, tags, hashtags)  │
│  episode_{NNNN}_audio.wav               (intermediate, 44100Hz 16-bit)        │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
StorySegment (JSON from ramayan_db/)
       │
       ▼
EpisodeScript (JSON — title, hook, angle, scenes[], revelation, CTA)
       │
       ├──────────────────────┐
       ▼                      ▼
Keyframe PNGs             Hindi Audio (WAV segments)
(FLUX.1-schnell)          (Edge TTS, 14 voices)
       │                      │
       │                      ▼
       │                Audio Mix (WAV)
       │                (music + SFX + narration)
       │                      │
       ▼                      │
Subtitled Keyframes           │
(Pillow text burn)            │
       │                      │
       ▼                      ▼
    Ken Burns Compositor
    (FFmpeg zoompan + concat + audio mux)
       │
       ▼
    Branded MP4
    (hook + title card + video + CTA)
       │
       ├──────────────────────┐
       ▼                      ▼
YouTube Thumbnail      YouTube Metadata
(1280x720 JPEG)        (title/desc/tags)
```

---

## Component Architecture

### 1. Config System (`src/config_loader.py`)

Loads `config.yaml` → validates → produces a tree of typed dataclasses.

```
Config
├── PipelineConfig      (schedule_time, target_duration, retry_attempts)
├── AnimationConfig     (style_reference, resolution, fps, model, lora_path)
├── NarrationConfig     (locale, narrator_voice, tts_provider, character_voices{14})
├── AudioConfig         (music_library_path, sfx_library_path, boost_db, crossfade)
├── OutputConfig        (format, video_codec, audio_codec)
├── StorageConfig       (provider, bucket, path_prefix)
├── DistributionConfig  (youtube: PlatformConfig, instagram: PlatformConfig)
└── NotificationsConfig (provider, recipients[])
```

Every field has a documented default. Invalid values produce `ConfigError` naming the exact field paths that failed (e.g., `"pipeline.schedule_time"`).

---

### 2. Story Manager (`src/story_manager.py`)

State machine managing sequential progression through the Ramayan.

**State (metadata.json):**
```json
{
  "current_kanda_index": 1,
  "current_segment_index": 1,
  "total_episodes_completed": 4,
  "series_complete": false,
  "current_video_index": 4
}
```

**State transitions:**
```
get_next_segment()
  → increment current_video_index
  → if video_index >= videos_per_segment:
      → increment current_segment_index, reset video_index
  → if segment_index >= segments_in_kanda:
      → increment current_kanda_index, reset segment_index
  → if kanda_index > 7:
      → series_complete = true
```

**StorySegment model:**
```python
@dataclass
class StorySegment:
    kanda_index: int               # 1-7
    kanda_name: str                # "Bala Kanda"
    chapter: int
    segment_index: int
    title: str
    content: str                   # Full narrative text
    characters: List[str]          # Characters in this segment
    key_events: List[str]
    # Explainer enrichment:
    philosophical_themes: List[str]
    lesser_known_facts: List[str]
    debate_angles: List[str]
    modern_relevance: List[str]
    suggested_angles: List[str]    # ["hidden_meaning", "life_lesson"]
```

---

### 3. Script Engine (`src/script_engine.py`)

Transforms StorySegments into structured EpisodeScripts via Gemini LLM.

```
StorySegment + Character Registry
         │
         ▼
┌─────────────────────────────────┐
│ SYSTEM_PROMPT                    │
│ - Scriptwriter role              │
│ - Sacred content guidelines      │
│ - JSON output schema             │
│ - Constraints (3-5 scenes,       │
│   45-50s, 7 angle types)         │
└────────────────┬────────────────┘
                 │
         ┌───────▼────────┐
         │ USER_PROMPT     │
         │ - segment.content│
         │ - characters     │
         │ - video_index    │
         │ - previous_titles│
         └───────┬─────────┘
                 │
         ┌───────▼────────────┐
         │ GeminiLLMClient     │  (5x retry with exponential backoff
         │ gemini-2.5-flash    │   60s/120s/240s/480s on 503)
         └───────┬────────────┘
                 │
         ┌───────▼────────────────────┐
         │ Post-processing:            │
         │ 1. Strip markdown fences    │
         │ 2. JSON parse + schema      │
         │ 3. validate_script()        │
         │ 4. validate_sacred_content()│
         └───────┬────────────────────┘
                 │
                 ▼
         EpisodeScript (validated)
```

**Sacred Content Safety:**
- Blocks disrespectful framing of divine characters (Hindi + English patterns)
- Blocks divinity-questioning content ("just a story", "just a myth", etc.)
- Prevents skeptical angles on protected divine characters

---

### 4. EpisodeScript (Core Data Model)

The central artifact flowing through the entire pipeline:

```python
@dataclass
class EpisodeScript:
    episode_number: int
    kanda: str
    title: str                      # Engaging explainer title
    total_duration_seconds: int     # 45-50s
    scenes: List[Scene]             # 3-5 scenes
    hook: str                       # Scroll-stopping opener
    angle: str                      # hidden_meaning|why|character_study|life_lesson|unknown_facts|what_if|debate
    revelation: str                 # Core insight
    engagement_cta: str             # Comment-triggering question

@dataclass
class Scene:
    scene_number: int
    duration_seconds: int
    background: str                 # Visual setting description
    characters: List[str]
    action: str                     # Visual action description
    narration: str                  # Hindi narration text
    dialogue: List[DialogueLine]
    mood: str                       # devotional|dramatic|serene|battle|divine|...
    sound_effects: List[str]
    narration_en: str               # English text (for subtitles)

@dataclass
class DialogueLine:
    character: str
    text: str
```

---

### 5. Animation Engine (`src/animation_engine.py`)

Generates AI keyframes for each scene with visual variety and quality validation.

**Architecture:**
```
AnimationEngine
├── ImageGenerator (Protocol)     ← FLUX / SDXL / Gemini (pluggable)
├── QualityScorer (Protocol)      ← CLIP-based scoring
├── FrameInterpolator (Protocol)  ← FILM blending (legacy, not used with Ken Burns)
├── visual_variety.py             ← Scene-role composition directives
└── ip_adapter.py                 ← Character prompt enhancement
```

**Per-scene pipeline:**
1. Load character embeddings → `prompt_description` from `models/characters/`
2. Determine scene role → `hook | context_establishing | context_action | revelation | cta_engagement`
3. Build enhanced prompt = composition prefix + mood styling + character descriptions + scene background/action
4. Generate 3 keyframes per scene via `ImageGenerator.generate()`
5. Quality score each frame, retry up to 3x if below threshold
6. Keep best-scoring attempt
7. Save PNGs to temp directory

**Visual Variety System:**
```
Scene 1 → "hook":                extreme close-up, dramatic portrait, intense emotion
Scene 2 → "context_establishing": wide establishing shot, epic landscape
Scene 3 → "context_action":      dynamic mid-shot, characters in action
Scene 4 → "revelation":          symbolic composition, divine glow, sacred geometry
Scene 5 → "cta_engagement":      warm close-up, direct eye contact
```

**Mood visual styles** (color/lighting):
```
devotional → warm golden light, temple lamp glow, saffron palette
dramatic   → high contrast chiaroscuro, deep shadows, reds and blacks
battle     → chaotic red-orange firelight, dust and debris
divine     → ethereal white-gold from above, celestial glow
serene     → soft diffused light, pastel dawn, blue-green
```

---

### 6. Image Generators (Pluggable)

| Implementation | File | Runtime | Details |
|---|---|---|---|
| **FluxImageGenerator** | `flux_image_generator.py` | Local MPS | FLUX.1-schnell, 4 steps, T5 encoder (256 tokens), generates at 512x896 → resizes to 1080x1920. **Production choice.** |
| SDXLImageGenerator | `sd_image_generator.py` | Local MPS | SDXL, 15 steps, CLIP encoder (77 tokens). Backup, has float16 NaN issues. |
| GeminiImageGenerator | `gemini_image_generator.py` | Cloud API | Google Imagen via Gemini. No local GPU needed. Cloud fallback. |

**ImageGenerator Protocol:**
```python
class ImageGenerator(Protocol):
    def generate(
        self, prompt: str, negative_prompt: str,
        width: int, height: int, num_images: int,
        lora_path: Optional[str],
        character_embeddings: Optional[List[Dict[str, Any]]],
    ) -> List[Image.Image]: ...
```

---

### 7. Narration Engine (`src/narration_engine.py`)

Generates Hindi spoken audio with character-specific voice profiles.

**Architecture:**
```
NarrationEngine
├── VoiceProfileManager          ← Maps character names → voice IDs
├── TTSProvider (Protocol)       ← Edge TTS / Coqui / Azure / ElevenLabs
└── Duration synchronization     ← Adjusts speech rate if audio exceeds target
```

**Voice differentiation (Edge TTS):**
- 2 base voices: `hi-IN-MadhurNeural` (male), `hi-IN-SwaraNeural` (female)
- 14 character variations via pitch (Hz) and rate (%) adjustments:

```
Narrator:     MadhurNeural, +0Hz,  +0%   (calm baseline)
Rama:         MadhurNeural, +10Hz, +0%   (noble, slightly higher)
Hanuman:      MadhurNeural, +15Hz, +5%   (energetic)
Ravana:       MadhurNeural, -15Hz, -3%   (deep, menacing)
Sita:         SwaraNeural,  +0Hz,  +0%   (gentle female)
Dasharatha:   MadhurNeural, -10Hz, -3%   (elderly king)
Lakshmana:    MadhurNeural, +12Hz, +0%   (young, alert)
Vishwamitra:  MadhurNeural, -5Hz,  +2%   (commanding sage)
Kausalya:     SwaraNeural,  -5Hz,  -2%   (gentle queen)
Kaikeyi:      SwaraNeural,  +5Hz,  +0%   (assertive)
...
```

**Duration sync:** If generated audio exceeds target by >2s, regenerates at up to 1.25x rate.

---

### 8. Audio Engine (`src/audio_engine.py`)

Mixes narration, mood-matched music, and sound effects.

```
┌─────────────────────────────────────────────────────────────┐
│  Per-scene mixing (pydub):                                   │
│  1. Build narration track (concatenate WAV segments)         │
│  2. Select music by mood (avoid repeating previous scene)    │
│  3. Loop music if shorter than narration                     │
│  4. Volume ducking: music = music - narration_boost_db       │
│  5. Place ambient SFX (via sfx_mapper.py mood → SFX map)    │
│  6. Overlay: narration + music + SFX                         │
├─────────────────────────────────────────────────────────────┤
│  Episode assembly:                                           │
│  1. Mix each scene independently                             │
│  2. Concatenate with crossfade (0.75s)                       │
│  3. Normalize: 44100 Hz, 16-bit, stereo                     │
│  4. Export as WAV                                            │
└─────────────────────────────────────────────────────────────┘
```

**SFX Mood Mapper** (automatic atmosphere):
```python
MOOD_AMBIENT_MAP = {
    "devotional": ["temple_bells_soft", "incense_wind"],
    "dramatic":   ["thunder_distant", "wind_howl"],
    "battle":     ["swords_clash", "drums_war", "arrows_flying"],
    "serene":     ["birds_morning", "river_gentle"],
    "divine":     ["om_chant", "divine_light"],
    "festive":    ["drums_festive", "crowd_cheering", "bells_joyful"],
}
```

---

### 9. Subtitle Burner (`src/subtitle_burner.py`)

Burns English text directly onto keyframe PNGs using Pillow (before Ken Burns composition).

- Font: Devanagari Sangam MN (macOS system font)
- Size: 42px white with 3px black outline
- Semi-transparent black background bar (opacity 160/255)
- Max 30 chars/line, text-wrapped
- In-place modification of keyframe files

---

### 10. Ken Burns Compositor (`src/ken_burns_compositor.py`)

Creates dynamic video from static keyframes using FFmpeg zoompan filters.

**7 effect types (randomly assigned per keyframe):**
```
zoom_in        — Slow zoom toward center (1.0 → 1.3)
zoom_out       — Start zoomed, pull back (1.3 → 1.0)
pan_left       — Slow pan from right to left
pan_right      — Slow pan from left to right
pan_up         — Slow pan from bottom to top
zoom_in_top    — Zoom into top portion
zoom_in_bottom — Zoom into bottom portion
```

**Pipeline:**
```
For each keyframe:
  1. Pick random effect
  2. Generate FFmpeg zoompan filter string
  3. Encode: ffmpeg -loop 1 -i keyframe.png -vf zoompan=... → clip.mp4
  4. Fallback: if zoompan fails, use static scale+pad

Assembly:
  1. Write concat.txt
  2. ffmpeg -f concat → concat_video.mp4
  3. ffmpeg -i concat_video.mp4 -i audio.wav → final.mp4 (H.264+AAC, -shortest)
```

---

### 11. Video Branding (`src/video_branding.py`)

Adds professional branding frames to the video.

```
[Hook Overlay ~3s] + [Title Card ~3-5s] + [Main Video] + [CTA ~3s]
```

- **Hook:** Large hook text + channel name "सनातन रहस्य"
- **Title Card:** Episode number, title, kanda name, angle badge, decorative border
- **End CTA:** engagement_cta question + "Comment your answer below!" + subscribe prompt

All frames generated with Pillow, composed with FFmpeg concat.

---

### 12. Thumbnail Generator (`src/thumbnail_generator.py`)

Creates CTR-optimized 1280x720 YouTube thumbnails:

1. Load first keyframe as background (or create gradient)
2. Apply gaussian blur + dark overlay for contrast
3. Draw bold hook text (3-6 words, massive font)
4. Add gold accent border
5. Add channel branding watermark
6. Save as JPEG

---

### 13. YouTube Metadata (`src/youtube_metadata.py`)

Auto-generates upload-ready metadata:

```python
@dataclass
class YouTubeMetadata:
    title: str          # "{hook pattern} | Episode {N}" (60-70 chars)
    description: str    # hook + revelation + CTA + channel info + hashtags
    tags: List[str]     # BASE_TAGS + angle-specific + character names
    hashtags: List[str] # 3-5 discovery hashtags
    category: str       # "Education"
    privacy: str        # "public"
    language: str       # "hi"
```

---

### 14. Quality Gates (`src/quality_gates.py`)

```
┌────────────────────────────────────────────────────────────────────┐
│ GATE 1: Script Quality (after LLM generation)                       │
│ ✓ Title: English-only, ≤65 chars                                    │
│ ✓ Hook: ends with punctuation, ≤100 chars                           │
│ ✓ CTA: contains '?', ≤100 chars                                     │
│ ✓ Duration: 45-50s total                                            │
│ ✓ Scenes: 3-5 count                                                │
│ ✓ All scenes have narration + narration_en                          │
│ ✓ Angle: one of 7 valid values                                      │
│ ✓ Revelation: not empty                                             │
├────────────────────────────────────────────────────────────────────┤
│ GATE 2: Sacred Content Safety (after LLM generation)                │
│ ✗ Disrespect patterns (Hindi): "सीता कमजोर", "राम ने अन्याय"       │
│ ✗ Divinity-questioning: "just a story", "fictional character"        │
│ ✗ Protected divine characters + skeptical angle combos              │
├────────────────────────────────────────────────────────────────────┤
│ GATE 3: Final Video Validation (after composition)                  │
│ ✓ File exists, size 3-50 MB                                         │
│ ✓ Duration 50-120s                                                  │
│ ✓ Video: H.264, 1080x1920                                           │
│ ✓ Audio: AAC                                                        │
│ ✓ ffprobe reads without errors                                      │
├────────────────────────────────────────────────────────────────────┤
│ GATE 4: Thumbnail Validation                                        │
│ ✓ File exists, size ≥30 KB                                          │
└────────────────────────────────────────────────────────────────────┘
```

If any gate fails → episode NOT marked complete → segment stays unconsumed → next run retries automatically.

---

### 15. Distribution Manager (`src/distribution_manager.py`)

Upload and publishing with retry logic (currently disabled for YouTube/Instagram).

**Protocols:**
```python
class StorageUploader(Protocol):
    def upload_file(self, local_path: str, bucket: str, key: str) -> str: ...

class PlatformPublisher(Protocol):
    def platform_name(self) -> str: ...
    def publish(self, video_path: str, title: str, desc: str, tags: List[str]) -> str: ...
```

- File naming: `ramayan_e{NNNN}_{kanda_name}_{YYYYMMDD}.mp4`
- Retry: 3 attempts with exponential backoff (1s → 2s → 4s)
- Distribution log: records platform, status, URL, timestamp per event

---

### 16. Notifications (`src/notifications.py`)

Alerts when pipeline stages exhaust all retries.

```python
class NotificationSender(Protocol):
    def send(self, alert: PipelineFailureAlert) -> bool: ...
```

| Adapter | Transport |
|---|---|
| `EmailNotificationAdapter` | SMTP |
| `WebhookNotificationAdapter` | HTTP POST (JSON payload) |
| `MockNotificationAdapter` | In-memory (testing) |

---

## Protocol Interface Map (Dependency Injection)

Every external dependency is abstracted behind a Python `Protocol`:

| Protocol | Production | Mock/Test |
|----------|-----------|-----------|
| `LLMClient` | `GeminiLLMClient` | Returns canned JSON |
| `ImageGenerator` | `FluxImageGenerator` | `StableDiffusionGenerator` (solid-color PNGs) |
| `QualityScorer` | `CLIPQualityScorer` | Returns configurable float |
| `FrameInterpolator` | `FILMFrameInterpolator` | Alpha-blended images |
| `TTSProvider` | `EdgeTTSAdapter` | Silent WAV bytes |
| `VideoRenderer` | `FFmpegRenderer` | `MockRenderer` (JSON metadata) |
| `StorageUploader` | S3/GCS client | `MockStorageUploader` |
| `PlatformPublisher` | YouTube/IG API | `MockPlatformPublisher` |
| `NotificationSender` | Email/Webhook | `MockNotificationAdapter` |

This enables full end-to-end pipeline testing without any real AI services, cloud accounts, or FFmpeg.

---

## Two Execution Paths

### Path A: Orchestrator (main.py)

```
main.py → build_components() → VideoGeneratorOrchestrator → PipelineScheduler
```

- Uses Protocol-based components
- Has full retry + notification infrastructure
- Designed for APScheduler daemon mode
- Includes `VideoCompositor` (frame-sequence path)

### Path B: Direct (generate_episode.py) — Production Path

```
generate_episode.py → calls components directly → Ken Burns + Branding + Quality Gates
```

- Bypasses the orchestrator
- Uses `compose_ken_burns_video()` directly
- Includes subtitle burning, video branding, thumbnails, metadata, quality gates
- **This is what runs nightly and generated all 9 episodes**

Path B evolved after the orchestrator was built, incorporating Ken Burns, subtitles, branding, and quality gates that the orchestrator doesn't have yet.

---

## Error Handling (6 Layers)

```
Layer 1: Per-image retry
  AnimationEngine → 3 retries per keyframe, keeps best quality score

Layer 2: LLM retry with exponential backoff
  ScriptEngine → 5 retries: 60s, 120s, 240s, 480s on 503/overloaded

Layer 3: Per-stage retry
  Orchestrator → 3 retries per pipeline stage, notification on exhaustion

Layer 4: Per-episode isolation
  generate_batch.py → subprocess per episode, 60-min timeout, failure doesn't block next

Layer 5: Quality gates
  Script/Video rejected → episode NOT marked complete → retried next run

Layer 6: State restartability
  metadata.json always accurate → process killable at any point → resumes correctly
```

---

## Character System

14 characters defined in `models/characters/{name}/character.json`:

```json
{
  "name": "Bharata",
  "description": "Son of Kaikeyi, devoted brother of Rama",
  "prompt_description": "young prince with fair skin, wearing orange dhoti with gold border, simple gold crown, humble devoted expression, carrying Rama's sandals reverently",
  "reference_images": [],
  "embedding_file": ""
}
```

The `prompt_description` is injected into image generation prompts for visual consistency. Reference images and embeddings support future IP-Adapter Mode 2 (full visual consistency via embedding injection).

**Current mode:** Prompt Enhancement (Mode 1) — appends detailed character descriptions to generation prompts. Works immediately without additional model downloads.

---

## Asset Libraries

### Music Library (`assets/music/`)

20 tracks tagged by mood:
```
battle_track1.mp3, celebratory_track1.mp3, devotional_track{1-3}.mp3,
dramatic_track{1-3}.mp3, festive_track1.mp3, hopeful_track{1-3}.mp3,
joyful_track1.mp3, melancholy_track1.mp3, miraculous_track1.mp3,
mysterious_track{2-3}.mp3, serene_track{1-3}.mp3
```

### SFX Library (`assets/sfx/`)

20+ clips for atmosphere:
```
arrows_flying, bells_joyful, birds_morning, conch_shell,
crowd_cheering, divine_light, drums_festive, drums_victory,
drums_war, fire_crackling, flute_distant, horses_gallop,
incense_wind, ocean_waves, om_chant, rain_soft, ...
```

---

## Storage Architecture

All inter-stage data persists to disk:

| Artifact | Location | Format | Purpose |
|---|---|---|---|
| Pipeline state | `ramayan_db/metadata.json` | JSON | Survives restarts |
| Episode records | `ramayan_db/episodes/` | JSON | Audit trail |
| Keyframes | `/tmp/ramayan_frames_*` | PNG | Input to Ken Burns |
| Intermediate audio | `output/episode_*_audio.wav` | WAV | Audio mux input |
| Final video | `output/ramayan_e*_.mp4` | MP4 | Distribution artifact |
| Thumbnail | `output/ramayan_e*_thumbnail.jpg` | JPEG | YouTube upload |
| Metadata | `output/ramayan_e*_metadata.txt` | Text | YouTube upload |
| Batch logs | `logs/batch_*.log` | Text | Debugging |

---

## Performance Profile

| Stage | Time | Bottleneck |
|---|---|---|
| Script (Gemini API) | 10-20s | Network + LLM inference |
| Keyframes (FLUX x15) | 30-35 min | **GPU inference (dominant)** |
| Narration (Edge TTS) | 30-60s | Network (async) |
| Audio mixing | 5-10s | CPU (pydub) |
| Subtitle burning | 2-5s | CPU (Pillow) |
| Ken Burns composition | 2-3 min | FFmpeg encoding |
| Branding | 30-60s | Pillow + FFmpeg |
| Thumbnail + metadata | 2-3s | CPU |
| **Total** | **~45 min** | |

Memory usage peaks at ~12 GB unified memory during FLUX inference. The pipeline is designed to release GPU memory between episodes (30s cooldown in batch mode).
