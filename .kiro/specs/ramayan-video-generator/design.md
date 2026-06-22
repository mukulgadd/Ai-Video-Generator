# Design Document: Ramayan Video Generator

## Overview

The Ramayan Video Generator is a modular pipeline system that automatically produces daily 2-minute animated episodes of the Ramayan epic. The system is composed of discrete, loosely-coupled components connected through a central orchestrator. Each component handles one stage of the pipeline: story selection, script generation, animation, narration, audio mixing, video composition, and distribution.

The architecture follows a sequential pipeline pattern where each stage produces artifacts consumed by the next stage. All inter-stage data is persisted to disk as JSON or media files, enabling restartability and debugging.

## Architecture

### System Architecture Diagram

```
┌─────────────┐
│  Scheduler   │ (Cron / Cloud Scheduler)
└──────┬───────┘
       │ triggers daily
       ▼
┌──────────────────┐
│  Video_Generator  │ (Pipeline Orchestrator)
│  (orchestrator)   │
└──────┬───────────┘
       │
       ▼
┌──────────────┐    ┌───────────────┐    ┌──────────────────┐
│ Story_Manager │───▶│ Script_Engine  │───▶│ Animation_Engine  │
│ (story DB +   │    │ (LLM-based     │    │ (AI image/video   │
│  progression) │    │  scriptwriter)  │    │  generation)      │
└──────────────┘    └───────────────┘    └────────┬─────────┘
                                                   │
                    ┌───────────────┐              │
                    │Narration_Engine│◀─────────────┘
                    │ (TTS synthesis)│    (parallel with animation)
                    └───────┬───────┘
                            │
                    ┌───────▼───────┐
                    │ Audio_Engine   │
                    │ (music + SFX   │
                    │  mixing)       │
                    └───────┬───────┘
                            │
                    ┌───────▼──────────┐
                    │ Video_Compositor  │
                    │ (FFmpeg-based     │
                    │  rendering)       │
                    └───────┬──────────┘
                            │
                    ┌───────▼──────────────┐
                    │ Distribution_Manager  │
                    │ (upload + publish)    │
                    └──────────────────────┘
```

### Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Language | Python 3.11+ | Rich AI/ML ecosystem, FFmpeg bindings, scheduling libraries |
| Scheduler | APScheduler / system cron | Lightweight, reliable daily scheduling |
| Story Database | SQLite + JSON files | Simple, file-based, no external DB dependency |
| Script Generation | OpenAI GPT-4 API (or equivalent LLM) | High-quality narrative generation with structured output |
| Animation | Stable Diffusion (via ComfyUI or API) + frame interpolation | Open-source, customizable style, local or cloud |
| Video Synthesis | Deforum / AnimateDiff for motion | Smooth animation from keyframes |
| TTS | Coqui TTS / Azure Speech / ElevenLabs | Multi-voice, multi-language support |
| Audio Mixing | pydub + librosa | Python-native audio processing |
| Video Composition | FFmpeg (via ffmpeg-python) | Industry standard, handles all codecs and formats |
| Storage | AWS S3 / Google Cloud Storage | Scalable cloud storage |
| Distribution | YouTube Data API / Instagram Graph API | Direct platform publishing |
| Configuration | PyYAML | Standard Python YAML parsing |

## Component Design

### 1. Story_Manager

**Responsibility:** Maintain the Ramayan narrative database and track episode progression.

**Data Model:**
```
ramayan_db/
├── metadata.json          # Series metadata, current position
├── kandas/
│   ├── 1_bala_kanda/
│   │   ├── kanda.json     # Kanda metadata
│   │   └── segments/
│   │       ├── 001.json   # Story segment
│   │       ├── 002.json
│   │       └── ...
│   ├── 2_ayodhya_kanda/
│   └── ...
└── episodes/
    ├── episode_001.json   # Episode record (segment ref, status, output path)
    └── ...
```

**State Tracking:**
- `metadata.json` stores: `current_kanda_index`, `current_segment_index`, `total_episodes_completed`, `series_complete`
- Each episode record stores: `episode_number`, `kanda`, `segment_ids`, `status` (pending/complete/failed), `output_path`, `created_at`

**Key Methods:**
- `get_next_segment() -> StorySegment` — Returns next unprocessed segment, advances pointer
- `mark_episode_complete(episode_id, output_path)` — Updates episode record and position
- `get_current_position() -> Position` — Returns current Kanda/chapter/segment
- `is_series_complete() -> bool` — Checks if all segments are processed

### 2. Script_Engine

**Responsibility:** Transform story segments into structured episode scripts using LLM.

**Episode Script Schema:**
```json
{
  "episode_number": 1,
  "kanda": "Bala Kanda",
  "title": "The Birth of Rama",
  "total_duration_seconds": 120,
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 20,
      "background": "Royal palace of Ayodhya, ornate pillars, warm golden light",
      "characters": ["King_Dasharatha", "Queen_Kausalya"],
      "action": "King Dasharatha performs a sacred fire ceremony",
      "narration": "In the ancient kingdom of Ayodhya, King Dasharatha...",
      "dialogue": [
        {"character": "King_Dasharatha", "text": "..."}
      ],
      "mood": "devotional",
      "sound_effects": ["fire_crackling", "temple_bells"]
    }
  ]
}
```

**LLM Prompt Strategy:**
- System prompt defines the role, art style context, and output JSON schema
- User prompt provides the story segment text and character registry
- Output is validated against the JSON schema before proceeding
- Temperature set to 0.7 for creative but consistent output

**Key Methods:**
- `generate_script(segment: StorySegment, character_registry: dict) -> EpisodeScript`
- `serialize(script: EpisodeScript) -> str` — JSON serialization
- `parse(json_str: str) -> EpisodeScript` — JSON parsing with validation
- `pretty_print(script: EpisodeScript) -> str` — Formatted JSON output

### 3. Animation_Engine

**Responsibility:** Generate animated frames from scene descriptions.

**Pipeline:**
1. **Keyframe Generation:** Use Stable Diffusion with ControlNet to generate 2-3 keyframes per scene based on scene description and character references
2. **Frame Interpolation:** Use AnimateDiff or FILM to interpolate between keyframes, generating smooth motion at 12+ FPS
3. **Style Consistency:** Maintain a LoRA model fine-tuned on Indian traditional art style; use IP-Adapter for character consistency
4. **Quality Validation:** Run a CLIP-based quality scorer on each frame; reject frames below threshold

**Character Consistency:**
- Store character reference images and IP-Adapter embeddings in `characters/` directory
- Each character has: `name`, `reference_images[]`, `embedding_file`, `prompt_description`
- Embeddings are loaded and injected into the generation pipeline for each scene

**Output:** Sequence of PNG frames organized by scene in a temporary directory.

### 4. Narration_Engine

**Responsibility:** Generate spoken audio from script text.

**Voice Management:**
- Voice profiles stored in configuration: `{character_name: voice_id}`
- Default narrator voice for non-dialogue narration
- Support for multiple TTS backends via adapter pattern

**Process:**
1. Extract narration and dialogue segments from script
2. Generate audio for each segment using assigned voice profile
3. Measure duration against timing cues
4. If duration exceeds tolerance, adjust speech rate parameter and regenerate
5. Output individual WAV files per segment

### 5. Audio_Engine

**Responsibility:** Mix narration, music, and sound effects.

**Music Selection:**
- Maintain a library of royalty-free Indian classical/devotional music clips tagged by mood
- Map scene mood tags to music clips
- Support AI music generation (e.g., MusicGen) as an alternative

**Mixing Process:**
1. Load narration audio segments
2. Select/generate background music per scene based on mood
3. Apply volume ducking: reduce music by 6+ dB during speech segments
4. Add sound effects at specified timestamps
5. Apply crossfade transitions (0.5-1.0s) between scenes
6. Export final mixed audio as WAV (44100 Hz, 16-bit)

### 6. Video_Compositor

**Responsibility:** Combine animation frames and audio into final video.

**FFmpeg Pipeline:**
1. Encode frame sequences into video streams per scene
2. Apply visual transitions (crossfade/dissolve) between scenes
3. Overlay title card at the beginning (Kanda name + episode number)
4. Combine video stream with final audio track
5. Encode to MP4 (H.264 + AAC) at 1080x1920, 24 FPS
6. Validate final duration is 110-130 seconds
7. If over 130s, trim final scene with fade-out

### 7. Distribution_Manager

**Responsibility:** Store and publish finished videos.

**Naming Convention:** `ramayan_e{episode_number:04d}_{kanda_name}_{YYYYMMDD}.mp4`

**Distribution Flow:**
1. Upload to cloud storage (S3/GCS)
2. If platform publishing enabled:
   - Generate title: "Ramayan Episode {N}: {title} | {Kanda}"
   - Generate description from script narration summary
   - Generate tags: ["Ramayan", "Hindu Mythology", kanda_name, ...]
   - Upload to YouTube/Instagram via API
3. Generate thumbnail from Animation_Engine key frame
4. Log all distribution events

### 8. Configuration

**Config File:** `config.yaml`

```yaml
pipeline:
  schedule_time: "06:00"          # Daily trigger time (UTC)
  target_duration_seconds: 120     # Target video duration
  retry_attempts: 3                # Max retries per stage

animation:
  style_reference: "indian_traditional_art"
  resolution: [1080, 1920]         # width x height
  fps: 24
  model: "stable-diffusion-xl"
  lora_path: "./models/indian_art_lora.safetensors"

narration:
  default_locale: "hi"             # Hindi
  narrator_voice: "narrator_v1"
  tts_provider: "coqui"
  character_voices:
    Rama: "voice_rama_01"
    Sita: "voice_sita_01"
    Hanuman: "voice_hanuman_01"
    Ravana: "voice_ravana_01"

audio:
  music_library_path: "./assets/music/"
  sfx_library_path: "./assets/sfx/"
  narration_boost_db: 6
  crossfade_seconds: 0.75

output:
  format: "mp4"
  video_codec: "h264"
  audio_codec: "aac"

storage:
  provider: "s3"
  bucket: "ramayan-videos"
  path_prefix: "episodes/"

distribution:
  youtube:
    enabled: false
    credentials_path: "./credentials/youtube.json"
  instagram:
    enabled: false
    credentials_path: "./credentials/instagram.json"

notifications:
  provider: "email"
  recipients: ["admin@example.com"]
```

## Data Flow

```
Story Segment (JSON)
       │
       ▼
Episode Script (JSON) ──────────────────────┐
       │                                      │
       ├──────────────┐                       │
       ▼              ▼                       ▼
Animation Frames   Narration Audio      Scene Metadata
  (PNG sequence)    (WAV files)         (timing, mood)
       │              │                       │
       │              ▼                       │
       │         Audio_Engine ◀───────────────┘
       │           (mixed WAV)
       │              │
       ▼              ▼
    Video_Compositor
       │
       ▼
    Final MP4
       │
       ▼
  Distribution_Manager
       │
       ▼
  Cloud Storage + Platforms
```

## Correctness Properties

### Property 1: Story Progression Invariant (Req 2.2, 2.3)
For any sequence of N calls to `get_next_segment()`, the Story_Manager returns exactly N distinct segments in sequential narrative order, and the tracked position reflects exactly N segments of progress from the starting position.

### Property 2: Story Persistence Round-Trip (Req 2.6)
For any valid Story_Manager state (current position, episode history), saving the state to disk and loading it back produces an equivalent state object. Formally: `load(save(state)) == state`.

### Property 3: Script Duration Invariant (Req 3.2)
For any episode script produced by the Script_Engine, the sum of all scene `duration_seconds` values is between 110 and 130 seconds inclusive.

### Property 4: Script Scene Count Invariant (Req 3.3)
For any episode script produced by the Script_Engine, the number of scenes is between 4 and 8 inclusive, and each scene contains non-empty `background`, `characters`, `action`, and `narration` fields.

### Property 5: Script Character Consistency (Req 3.4)
For any episode script produced by the Script_Engine, every character name referenced in scenes and dialogue exists in the character registry provided as input.

### Property 6: Episode Script Round-Trip (Req 8.1, 8.2, 8.3, 8.4)
For any valid EpisodeScript object, `parse(pretty_print(script)) == script`. The round-trip through serialization and deserialization preserves all fields and values exactly.

### Property 7: Episode Script Error Handling (Req 8.5)
For any invalid JSON string (malformed JSON or schema violations), the Script_Engine parser returns a descriptive error rather than a valid EpisodeScript object.

### Property 8: Animation Resolution Invariant (Req 4.3)
For any frame generated by the Animation_Engine, the frame width is at least 1080 pixels and the frame height is at least 1920 pixels.

### Property 9: Narration Voice Distinctness (Req 5.2)
For any two distinct character names in the voice configuration, the assigned voice profile IDs are different.

### Property 10: Audio Mixing Level Invariant (Req 6.2)
For any mixed audio segment that contains speech, the narration audio level is at least 6 dB louder than the background music level.

### Property 11: Audio Format Invariant (Req 6.5)
For any audio file produced by the Audio_Engine, the sample rate is 44100 Hz and the bit depth is 16.

### Property 12: Video Output Format Invariant (Req 7.2, 7.3)
For any video file produced by the Video_Compositor, the container format is MP4, the video codec is H.264, the audio codec is AAC, the resolution is 1080x1920, and the frame rate is at least 24 FPS.

### Property 13: Video Duration Invariant (Req 7.6)
For any video file produced by the Video_Compositor, the duration is between 110 and 130 seconds inclusive.

### Property 14: Distribution Naming Convention (Req 9.2)
For any episode with a given episode number, Kanda name, and date, the generated filename matches the pattern `ramayan_e{NNNN}_{kanda_name}_{YYYYMMDD}.mp4`.

### Property 15: Distribution Log Completeness (Req 9.6)
For any distribution event, the log entry contains all required fields: upload status, platform name, URL (if successful), and timestamp.

### Property 16: Configuration Default Values (Req 10.3)
For any configuration file with missing optional keys, the Video_Generator uses the documented default value for each missing key. The resolved configuration is complete with no missing values.

### Property 17: Configuration Validation (Req 10.4)
For any configuration file containing invalid values (wrong types, out-of-range numbers, invalid paths), the Video_Generator reports the specific invalid fields and does not start the pipeline.

## File Structure

```
ramayan-video-generator/
├── config.yaml                    # Pipeline configuration
├── main.py                        # Entry point
├── src/
│   ├── __init__.py
│   ├── orchestrator.py            # Video_Generator pipeline orchestrator
│   ├── scheduler.py               # Daily scheduling logic
│   ├── story_manager.py           # Story database and progression
│   ├── script_engine.py           # LLM-based script generation
│   ├── episode_script.py          # EpisodeScript model, parser, serializer
│   ├── animation_engine.py        # AI animation generation
│   ├── narration_engine.py        # TTS audio generation
│   ├── audio_engine.py            # Music/SFX mixing
│   ├── video_compositor.py        # FFmpeg video rendering
│   ├── distribution_manager.py    # Upload and publishing
│   ├── config_loader.py           # YAML config loading and validation
│   └── notifications.py           # Failure notification system
├── models/
│   ├── indian_art_lora.safetensors
│   └── characters/
│       ├── rama/
│       │   ├── reference.png
│       │   └── embedding.pt
│       └── ...
├── assets/
│   ├── music/                     # Background music library
│   └── sfx/                       # Sound effects library
├── ramayan_db/                    # Story database
│   ├── metadata.json
│   └── kandas/
├── output/                        # Generated videos
├── credentials/                   # Platform API credentials
├── tests/
│   ├── __init__.py
│   ├── test_story_manager.py
│   ├── test_script_engine.py
│   ├── test_episode_script.py
│   ├── test_animation_engine.py
│   ├── test_narration_engine.py
│   ├── test_audio_engine.py
│   ├── test_video_compositor.py
│   ├── test_distribution_manager.py
│   └── test_config_loader.py
└── requirements.txt
```
