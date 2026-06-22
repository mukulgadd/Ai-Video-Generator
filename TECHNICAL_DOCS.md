# Technical Documentation

Complete API reference and component documentation for the Ramayan Video Generator production pipeline.

---

## Production Pipeline (generate_episode.py)

The actual production pipeline that generates all episodes. This is the 10-step sequence that runs nightly:

```
Step 1:  StoryManager.get_next_segment()        → StorySegment
Step 2:  ScriptEngine.generate_script()          → EpisodeScript (validated)
Step 3:  AnimationEngine.generate_episode_frames() → EpisodeFrames (PNG keyframes)
Step 4:  NarrationEngine.generate_episode_audio()  → EpisodeAudio (WAV segments)
Step 5:  AudioEngine.produce_episode_audio()       → mixed WAV file
Step 6:  burn_subtitles_on_keyframes()             → modified PNGs (in-place)
Step 7:  compose_ken_burns_video()                 → MP4 (raw video)
Step 8:  add_branding_to_video()                   → MP4 (branded, replaces raw)
Step 9:  generate_thumbnail()                      → JPEG (1280x720)
Step 10: generate_youtube_metadata()               → metadata text file
```

After Step 10, the episode is marked complete and `metadata.json` is updated.

---

## Component Reference

### 1. Config Loader (`src/config_loader.py`)

**Entry point:** `load_config(path: str) -> Config`

Reads `config.yaml`, validates every field, applies documented defaults for missing keys, and raises `ConfigError` with specific field names for invalid values.

**Types:**

```python
@dataclass
class Config:
    pipeline: PipelineConfig        # schedule_time, target_duration, retry_attempts
    animation: AnimationConfig      # style_reference, resolution, fps, model, lora_path
    narration: NarrationConfig      # locale, narrator_voice, tts_provider, character_voices
    audio: AudioConfig              # music_library_path, sfx_library_path, boost_db, crossfade
    output: OutputConfig            # format, video_codec, audio_codec
    storage: StorageConfig          # provider, bucket, path_prefix
    distribution: DistributionConfig # youtube, instagram (PlatformConfig each)
    notifications: NotificationsConfig # provider, recipients

@dataclass
class PipelineConfig:
    schedule_time: str = "06:00"
    target_duration_seconds: int = 120
    retry_attempts: int = 3

@dataclass
class AnimationConfig:
    style_reference: str = "indian_traditional_art"
    resolution: List[int] = [1080, 1920]    # [width, height]
    fps: int = 24
    model: str = "stable-diffusion-xl"
    lora_path: str = "./models/indian_art_lora.safetensors"

@dataclass
class NarrationConfig:
    default_locale: str = "hi"
    narrator_voice: str = "narrator_v1"
    tts_provider: str = "coqui"             # Production uses "edge"
    character_voices: Dict[str, str]        # 14 character → voice_id mappings

@dataclass
class AudioConfig:
    music_library_path: str = "./assets/music/"
    sfx_library_path: str = "./assets/sfx/"
    narration_boost_db: int = 6
    crossfade_seconds: float = 0.75
```

**Errors:** `ConfigError(message, invalid_fields: List[str])`

---

### 2. Story Manager (`src/story_manager.py`)

**Class:** `StoryManager(db_path: str = "ramayan_db")`

Maintains the Ramayan narrative database and tracks sequential episode progression.

| Method | Returns | Description |
|---|---|---|
| `get_next_segment()` | `StorySegment` | Returns next unprocessed segment, advances position pointer |
| `mark_episode_complete(episode_id, output_path)` | None | Updates episode record status to "complete" |
| `get_current_position()` | `Position` | Current kanda/segment/video index and completion state |
| `is_series_complete()` | `bool` | True when all segments of Uttara Kanda processed |

**Data models:**

```python
@dataclass
class StorySegment:
    kanda_index: int                # 1-7
    kanda_name: str                 # "Bala Kanda"
    chapter: int
    segment_index: int
    title: str
    content: str                    # Full narrative text (200-400 words)
    characters: List[str]
    key_events: List[str]
    philosophical_themes: List[str] # Optional enrichment
    lesser_known_facts: List[str]
    debate_angles: List[str]
    modern_relevance: List[str]
    suggested_angles: List[str]     # ["hidden_meaning", "life_lesson"]

@dataclass
class Position:
    current_kanda_index: int
    current_segment_index: int
    total_episodes_completed: int
    series_complete: bool
    current_video_index: int = 0    # Sub-video within segment
```

**State persistence:** Position is stored in `ramayan_db/metadata.json`. Saved after every `get_next_segment()` call. Survives process restarts.

**Kanda boundary:** When the last segment of a Kanda is consumed, pointer advances to the first segment of the next Kanda. After Kanda 7 (Uttara), series is marked complete.

**Errors:** `StoryManagerError`

---

### 3. Episode Script Model (`src/episode_script.py`)

**Data model:**

```python
@dataclass
class EpisodeScript:
    episode_number: int
    kanda: str
    title: str                      # English explainer title (≤65 chars)
    total_duration_seconds: int     # 45-50s
    scenes: List[Scene]             # 3-5 scenes
    hook: str                       # Scroll-stopping opener (≤100 chars)
    angle: str                      # Enum: hidden_meaning|why|character_study|life_lesson|unknown_facts|what_if|debate
    revelation: str                 # Core insight
    engagement_cta: str             # Comment-triggering question (≤100 chars)

@dataclass
class Scene:
    scene_number: int
    duration_seconds: int
    background: str                 # Visual setting for image generation
    characters: List[str]
    action: str                     # Visual action for image generation
    narration: str                  # Hindi narration text (TTS input)
    dialogue: List[DialogueLine]
    mood: str                       # Music/SFX selector
    sound_effects: List[str]
    narration_en: str               # English text (subtitle input)

@dataclass
class DialogueLine:
    character: str
    text: str
```

**Functions:**

| Function | Description |
|---|---|
| `serialize(script) -> str` | Compact JSON string |
| `pretty_print(script) -> str` | Indented JSON string |
| `parse(json_str) -> EpisodeScript` | Parse + validate against `EPISODE_SCRIPT_SCHEMA`, raises `EpisodeScriptError` on failure |

**JSON Schema enforcement:**
- All top-level fields required (including `hook`, `angle`, `revelation`, `engagement_cta`)
- `angle` is an enum (7 values only)
- `additionalProperties: false` on scene objects (prevents Gemini from adding extra fields)
- `narration_en` required on every scene

**Round-trip property:** `parse(pretty_print(script)) == script` holds for all valid scripts.

---

### 4. Script Engine (`src/script_engine.py`)

**Class:** `ScriptEngine(llm_client, model="gemini-2.5-flash", temperature=0.7)`

Transforms a `StorySegment` into a validated `EpisodeScript` using Gemini.

| Method | Returns | Description |
|---|---|---|
| `generate_script(segment, episode_number, video_index, previous_titles)` | `EpisodeScript` | Full LLM → parse → validate pipeline |

**LLM Client Protocol:**
```python
class LLMClient(Protocol):
    def chat_completions_create(
        self, model: str, messages: List[Dict[str, str]], temperature: float
    ) -> str: ...
```

**Implementations:**
- `GeminiLLMClient` — Production. Wraps `google-genai` SDK. Maps OpenAI message format → Gemini Contents.
- `OpenAILLMClient` — Backup. Wraps `openai` library.

**Pipeline:**
1. Load character registry from `models/characters/`
2. Build system prompt (role, sacred guidelines, JSON schema, constraints)
3. Build user prompt (segment content, characters, video_index, previous_titles)
4. Call LLM API (5x retry with exponential backoff: 60s/120s/240s/480s on 503)
5. Strip markdown fences if present
6. `parse()` JSON response into `EpisodeScript`
7. `validate_script()` — structural checks (scene count, duration, characters in registry)
8. `validate_sacred_content()` — content safety check
9. Return validated script

**Errors:** `ScriptEngineError`, `ScriptValidationError`

**Sacred content validation** blocks:
- Disrespect patterns (Hindi): "सीता कमजोर", "सीता बेचारी", "राम ने अन्याय", "राम क्रूर"
- Divinity-questioning (English): "just a story", "just a myth", "fictional character", "merely human", "mythological figure"
- Protected divine characters + skeptical angle combinations

---

### 5. Animation Engine (`src/animation_engine.py`)

**Class:** `AnimationEngine(config, image_generator, quality_scorer=None, frame_interpolator=None, characters_dir="models/characters")`

Generates keyframes for each scene with visual variety and quality validation.

| Method | Returns | Description |
|---|---|---|
| `generate_episode_frames(script)` | `EpisodeFrames` | Generates all keyframes for the episode |

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

**Implementations:**

| Class | File | Details |
|---|---|---|
| `FluxImageGenerator` | `flux_image_generator.py` | FLUX.1-schnell on MPS. 4 steps, 256-token T5 encoder. Generates at 512x896, resizes to 1080x1920. **Production.** |
| `SDXLImageGenerator` | `sd_image_generator.py` | Stable Diffusion XL on MPS. 15 steps, 77-token CLIP. Backup (float16 NaN issues). |
| `GeminiImageGenerator` | `gemini_image_generator.py` | Gemini Imagen via API. Cloud fallback. |

**Per-scene process:**
1. Load character embeddings → `prompt_description` from `character.json`
2. Determine scene role via `visual_variety.get_scene_role(scene_number, total_scenes)`
3. Build enhanced prompt: composition prefix + mood style + characters + scene description
4. Generate 3 keyframes via `ImageGenerator.generate()`
5. Quality score each (via `QualityScorer.score()`), retry up to 3x if below threshold
6. Save as PNGs in temp directory

**Data models:**
```python
@dataclass
class GeneratedFrame:
    path: str
    quality_score: float
    prompt: str

@dataclass
class SceneFrames:
    scene_number: int
    keyframes: List[GeneratedFrame]
    all_frames: List[GeneratedFrame]    # keyframes + any interpolated

@dataclass
class EpisodeFrames:
    episode_number: int
    scene_frames: List[SceneFrames]
    thumbnail: Optional[GeneratedFrame]  # Highest quality across episode
```

---

### 6. Visual Variety (`src/visual_variety.py`)

**Function:** `build_enhanced_image_prompt(base_prompt, scene_number, total_scenes, mood, characters) -> str`

Adds composition directives and mood styling to prevent visual monotony.

**Scene roles (by position):**
```
Scene 1            → "hook" (extreme close-up, dramatic portrait)
Scene 2            → "context_establishing" (wide landscape shot)
Middle scenes      → "context_action" (dynamic mid-shot)
Second-to-last     → "revelation" (symbolic, divine glow)
Last scene         → "cta_engagement" (warm inviting close-up)
```

**Mood visual styles:**
```
devotional → warm golden light, temple lamp glow, saffron palette
dramatic   → chiaroscuro, deep shadows, reds and blacks
battle     → fiery red-orange, dust and debris, motion blur
divine     → ethereal white-gold from above, celestial glow
serene     → soft diffused light, pastel dawn, blue-green
hopeful    → sunrise golden hour, fresh greens and golds
melancholy → overcast grey-blue, muted desaturated
```

---

### 7. IP Adapter (`src/ip_adapter.py`)

**Function:** `load_character_references(characters_dir) -> Dict[str, CharacterReference]`

Loads character visual data for consistency. Currently operates in **Mode 1 (Prompt Enhancement)** — appends detailed character descriptions to prompts. Mode 2 (embedding injection) is stubbed for future implementation.

```python
@dataclass
class CharacterReference:
    name: str
    prompt_description: str
    reference_images: List[str]
```

---

### 8. Narration Engine (`src/narration_engine.py`)

**Class:** `NarrationEngine(config: NarrationConfig, tts_provider=None)`

Generates Hindi spoken audio from episode scripts with character-specific voices and duration synchronization.

| Method | Returns | Description |
|---|---|---|
| `generate_episode_audio(script)` | `EpisodeAudio` | Full episode narration + dialogue |
| `generate_scene_audio(scene)` | `SceneAudio` | Single scene audio |

**TTSProvider Protocol:**
```python
class TTSProvider(Protocol):
    def synthesize(
        self, text: str, voice_id: str, locale: str, speech_rate: float
    ) -> bytes: ...  # Returns WAV format bytes
```

**Implementations:**
| Class | File | Details |
|---|---|---|
| `EdgeTTSAdapter` | `edge_tts_adapter.py` | Free, Hindi, 2 base voices + pitch/rate variations. **Production.** |
| `CoquiTTSAdapter` | `narration_engine.py` | Local Coqui TTS |
| `AzureSpeechAdapter` | `narration_engine.py` | Azure Cognitive Services |
| `ElevenLabsAdapter` | `narration_engine.py` | ElevenLabs API |

**Voice management:** `VoiceProfileManager` maps character names → voice IDs from config. Unknown characters fall back to narrator voice.

**Duration sync:** If generated audio exceeds scene target by >2s, recalculates speech rate (up to 1.25x max) and regenerates. Up to 3 retries.

**Data models:**
```python
@dataclass
class AudioSegment:
    audio_data: bytes           # WAV bytes
    duration_seconds: float
    character: Optional[str]
    segment_type: str           # "narration" or "dialogue"

@dataclass
class SceneAudio:
    scene_number: int
    segments: List[AudioSegment]
    total_duration_seconds: float

@dataclass
class EpisodeAudio:
    scene_audio: List[SceneAudio]
    total_duration_seconds: float
```

---

### 9. Edge TTS Adapter (`src/edge_tts_adapter.py`)

**Class:** `EdgeTTSAdapter(voice_map=None)`

Microsoft Edge TTS adapter with character voice differentiation.

**Voice map (14 characters):**
```python
VOICE_MAP = {
    "narrator_v1":       ("hi-IN-MadhurNeural", "+0Hz",  "+0%"),
    "voice_rama_01":     ("hi-IN-MadhurNeural", "+10Hz", "+0%"),
    "voice_hanuman_01":  ("hi-IN-MadhurNeural", "+15Hz", "+5%"),
    "voice_ravana_01":   ("hi-IN-MadhurNeural", "-15Hz", "-3%"),
    "voice_sita_01":     ("hi-IN-SwaraNeural",  "+0Hz",  "+0%"),
    "voice_dasharatha_01": ("hi-IN-MadhurNeural", "-10Hz", "-3%"),
    "voice_lakshmana_01": ("hi-IN-MadhurNeural", "+12Hz", "+0%"),
    "voice_vishwamitra_01": ("hi-IN-MadhurNeural", "-5Hz", "+2%"),
    "voice_vasishtha_01": ("hi-IN-MadhurNeural", "-8Hz",  "-2%"),
    "voice_kausalya_01": ("hi-IN-SwaraNeural",  "-5Hz",  "-2%"),
    "voice_kaikeyi_01":  ("hi-IN-SwaraNeural",  "+5Hz",  "+0%"),
    "voice_sumitra_01":  ("hi-IN-SwaraNeural",  "-10Hz", "-3%"),
    "voice_bharata_01":  ("hi-IN-MadhurNeural", "+8Hz",  "+0%"),
    "voice_shatrughna_01": ("hi-IN-MadhurNeural", "+5Hz", "-2%"),
}
```

---

### 10. Audio Engine (`src/audio_engine.py`)

**Class:** `AudioEngine(config: AudioConfig, music_library=None, sfx_library=None)`

Mixes narration, background music, and sound effects using pydub.

| Method | Returns | Description |
|---|---|---|
| `produce_episode_audio(script, episode_audio, output_path)` | None | Full mix → WAV export |
| `mix_scene(scene, scene_audio)` | `PydubSegment` | Single scene mix |
| `mix_episode(script, episode_audio)` | `PydubSegment` | All scenes concatenated with crossfade |

**Mixing rules:**
- Music selected by mood tag (avoids repeating previous scene's track)
- Music looped if shorter than narration
- Volume ducking: music reduced by `narration_boost_db` (default 6 dB) during speech
- SFX placed at evenly distributed timestamps
- Crossfade between scenes: 0.75s (configurable 0.5-1.0s)
- Final export: 44100 Hz, 16-bit, stereo WAV

**Music library:** Auto-loaded from `assets/music/`. Tracks named `{mood}_track{N}.mp3` are indexed by mood.

**SFX library:** Auto-loaded from `assets/sfx/`. Clips indexed by name.

---

### 11. SFX Mapper (`src/sfx_mapper.py`)

Maps scene moods to ambient sound effects automatically.

```python
MOOD_AMBIENT_MAP = {
    "devotional":  ["temple_bells_soft", "incense_wind"],
    "dramatic":    ["thunder_distant", "wind_howl"],
    "serene":      ["birds_morning", "river_gentle"],
    "mysterious":  ["wind_eerie", "owl_distant"],
    "triumphant":  ["drums_victory", "crowd_cheering"],
    "battle":      ["swords_clash", "drums_war", "arrows_flying"],
    "celebratory": ["drums_festive", "crowd_cheering", "bells_joyful"],
    "divine":      ["om_chant", "divine_light"],
    "heroic":      ["conch_shell", "drums_war"],
}
```

---

### 12. Subtitle Burner (`src/subtitle_burner.py`)

**Function:** `burn_subtitles_on_keyframes(keyframe_paths: List[List[str]], narration_texts: List[str])`

Burns English narration text onto keyframe images in-place.

**Settings:**
- Font: Devanagari Sangam MN (macOS), 42px
- White text with 3px black outline
- Semi-transparent black background bar (opacity 160)
- Max 30 chars per line
- Bottom-positioned with 80px padding

Modifies PNG files in-place before Ken Burns composition.

---

### 13. Ken Burns Compositor (`src/ken_burns_compositor.py`)

**Function:** `compose_ken_burns_video(keyframe_paths, scene_durations, audio_path, output_path, width=1080, height=1920, fps=24, crossfade_seconds=0.5) -> str`

Composes final video from keyframes using zoom/pan effects.

**Effects (7 types, randomly assigned):**

| Effect | FFmpeg zoompan expression |
|---|---|
| `zoom_in` | `z='1+0.3*on/{frames}'` centered |
| `zoom_out` | `z='1.3-0.3*on/{frames}'` centered |
| `pan_left` | `z=1.2, x='iw*0.2*(1-on/{frames})'` |
| `pan_right` | `z=1.2, x='iw*0.2*on/{frames}'` |
| `pan_up` | `z=1.2, y='ih*0.2*(1-on/{frames})'` |
| `zoom_in_top` | `z='1+0.3*on/{frames}', y='ih*0.1'` |
| `zoom_in_bottom` | `z='1+0.3*on/{frames}', y='ih*0.4'` |

**Process:**
1. Per keyframe: Apply zoompan filter → encode to H.264 clip
2. Fallback if zoompan fails: static scale+pad
3. Concat all clips via FFmpeg concat demuxer
4. Mux audio: `-c:a aac -b:a 192k -shortest`
5. Cleanup temp clips

**Output:** MP4 at 1080x1920, 24fps, H.264+AAC.

---

### 14. Video Branding (`src/video_branding.py`)

**Function:** `add_branding_to_video(input_video, output_video, episode_number, episode_title, kanda_name, hook_text, engagement_cta, angle)`

Adds professional branding around the main content.

**Structure:** `[Hook ~3s] + [Title Card ~3-5s] + [Main Video] + [CTA ~3s]`

- **Hook frames:** Large hook text + channel name "सनातन रहस्य" on dark background
- **Title card:** Episode number, title, kanda name, angle badge, decorative gold border
- **End CTA:** engagement_cta question + "Comment your answer below!" + subscribe prompt

All frames generated with Pillow, composed with FFmpeg concat.

---

### 15. Thumbnail Generator (`src/thumbnail_generator.py`)

**Function:** `generate_thumbnail(hook_text, episode_number, kanda_name, angle, keyframe_path, output_path)`

Creates 1280x720 YouTube thumbnails optimized for click-through rate.

**Process:**
1. Load keyframe as background (or create dark gradient)
2. Apply gaussian blur + dark overlay
3. Draw bold hook text (massive font, 3-6 words)
4. Add gold accent elements
5. Channel branding watermark
6. Save as JPEG

**Brand colors:** Deep purple-black background, gold accents, white text.

---

### 16. YouTube Metadata (`src/youtube_metadata.py`)

**Function:** `generate_youtube_metadata(script: EpisodeScript, kanda_name: str) -> YouTubeMetadata`

**Function:** `save_metadata_to_file(metadata: YouTubeMetadata, path: str)`

```python
@dataclass
class YouTubeMetadata:
    title: str              # 60-70 chars, hook + keyword
    description: str        # hook + revelation + CTA + channel info + hashtags
    tags: List[str]         # BASE_TAGS + angle-specific + character names
    hashtags: List[str]     # 3-5 discovery hashtags
    category: str = "Education"
    privacy: str = "public"
    language: str = "hi"
    made_for_kids: bool = False
```

**Base tags (on every video):** Ramayan, Ramayana, Hindu Mythology, Indian Mythology, Spiritual, Dharma, Sanskrit, Valmiki Ramayan, Ram, Sita, Hanuman, Indian Culture, Mythology Explained, Hindu Stories

---

### 17. Quality Gates (`src/quality_gates.py`)

**Function:** `validate_script_quality(script, required_angle=None) -> Tuple[bool, List[str]]`

**Function:** `validate_final_video(video_path) -> Tuple[bool, List[str]]`

**Function:** `validate_thumbnail(thumb_path) -> Tuple[bool, List[str]]`

All return `(passed: bool, issues: List[str])`.

**Script quality checks:**
- Title: English-only (no Devanagari), ≤65 chars
- Hook: ends with punctuation, ≤100 chars
- CTA: contains '?', ≤100 chars
- Duration sum: 45-50s
- Scene count: 3-5
- All scenes: narration and narration_en non-empty
- Angle: valid enum value
- Revelation: non-empty

**Video validation checks:**
- File exists and size 3-50 MB
- Duration 50-120s (via ffprobe)
- Video stream: H.264, 1080x1920
- Audio stream: AAC
- ffprobe returns valid JSON

---

### 18. Orchestrator (`src/orchestrator.py`)

**Class:** `VideoGeneratorOrchestrator(config, story_manager, script_engine, animation_engine, narration_engine, audio_engine, video_compositor, distribution_manager, notification_sender, output_dir="output")`

Coordinates pipeline execution with per-stage retry and failure notifications.

| Method | Returns | Description |
|---|---|---|
| `run_pipeline()` | `PipelineResult` | Execute full pipeline, return success/failure |

**Stage execution:** Each stage wrapped in `_run_stage_with_retry()`:
- Retries up to `config.pipeline.retry_attempts` times
- On exhaustion: sends `PipelineFailureAlert` via notification sender
- Raises `OrchestratorError`

```python
@dataclass
class PipelineResult:
    success: bool
    episode_number: int = 0
    kanda_name: str = ""
    output_path: str = ""
    failed_stage: str = ""
    error_message: str = ""
```

Note: The orchestrator uses the legacy `VideoCompositor` (frame-sequence path). The production script (`generate_episode.py`) uses Ken Burns directly with additional branding/quality gate steps.

---

### 19. Scheduler (`src/scheduler.py`)

**Class:** `PipelineScheduler(pipeline_config, orchestrator)`

| Method | Description |
|---|---|
| `start()` | Start blocking scheduler (fires daily at configured time) |
| `stop()` | Shutdown scheduler |
| `run_once()` | Execute pipeline immediately (manual/test) |

Uses APScheduler `BlockingScheduler` with `CronTrigger`.

---

### 20. Notifications (`src/notifications.py`)

**Protocol:**
```python
class NotificationSender(Protocol):
    def send(self, alert: PipelineFailureAlert) -> bool: ...
```

**Alert model:**
```python
@dataclass
class PipelineFailureAlert:
    stage_name: str
    error_message: str
    episode_number: int
    kanda_name: str
    retry_attempts: int
```

**Adapters:**
- `EmailNotificationAdapter(recipients, smtp_host, smtp_port, sender)` — SMTP
- `WebhookNotificationAdapter(webhook_url, headers)` — HTTP POST JSON
- `MockNotificationAdapter()` — Records alerts in memory (testing)

**Factory:** `create_notification_sender(config) -> NotificationSender`

---

### 21. Distribution Manager (`src/distribution_manager.py`)

**Class:** `DistributionManager(storage_config, distribution_config, storage_uploader=None, platform_publishers=None)`

| Method | Returns | Description |
|---|---|---|
| `distribute(video_path, episode_num, kanda, title)` | `DistributionResult` | Upload + publish |
| `upload_to_storage(local_path, episode_num, kanda)` | `str` (URL) | Cloud storage upload |
| `publish_to_platforms(video_path, title, desc, tags)` | `List[DistributionLogEntry]` | Platform publishing |

**File naming:** `ramayan_e{NNNN}_{kanda_name}_{YYYYMMDD}.mp4`

**Retry:** 3 attempts, exponential backoff (1s → 2s → 4s). Sleep function injectable for testing.

**Status:** Currently disabled in config (YouTube/Instagram publishing not wired up).

---

## Gemini LLM Client (`src/gemini_llm_client.py`)

**Class:** `GeminiLLMClient(api_key=None, model_override="gemini-2.5-flash")`

Wraps the `google-genai` SDK. Maps OpenAI-style messages to Gemini format:
- `role: "system"` → `system_instruction` parameter
- `role: "user"` → `Content(role="user", parts=[Part.from_text(...)])`
- `role: "assistant"` → `Content(role="model", parts=[Part.from_text(...)])`

Reads `GEMINI_API_KEY` from environment.

---

## FLUX Image Generator (`src/flux_image_generator.py`)

**Class:** `FluxImageGenerator(num_inference_steps=4)`

FLUX.1-schnell on Apple Silicon MPS. Lazy-loads pipeline on first call.

- Model: `black-forest-labs/FLUX.1-schnell` (float16)
- Device: MPS (falls back to CPU)
- Generation size: 512x896 (rounded to multiple of 16)
- Resized to target: 1080x1920 (Lanczos)
- Guidance scale: 0.0 (FLUX Schnell doesn't use CFG)
- Negative prompt: ignored (FLUX Schnell doesn't support it)
- Attention slicing enabled for memory efficiency
- Requires `HF_TOKEN` env var for gated model access

---

## Video Compositor — Legacy (`src/video_compositor.py`)

**Class:** `VideoCompositor(output_config, animation_config, renderer=None)`

The original frame-sequence compositor used by the orchestrator path. Encodes PNG sequences into video streams, applies transitions, renders title cards, combines with audio.

**VideoRenderer Protocol:**
```python
class VideoRenderer(Protocol):
    def encode_frames_to_video(self, frame_paths, output, fps, width, height) -> str: ...
    def apply_transition(self, video_a, video_b, output, duration) -> str: ...
    def render_title_card(self, text, output, duration, fps, width, height) -> str: ...
    def combine_video_audio(self, video, audio, output) -> str: ...
    def trim_video(self, input_path, output, max_duration) -> str: ...
    def get_video_duration(self, video_path) -> float: ...
    def concatenate_videos(self, video_paths, output) -> str: ...
```

**Implementations:** `FFmpegRenderer` (production), `MockRenderer` (testing — writes JSON metadata).

Note: In the production pipeline (`generate_episode.py`), this is replaced by `ken_burns_compositor.py` + `video_branding.py`.

---

## Correctness Properties (17 Total)

Validated with Hypothesis property-based testing:

| # | Property | Component | Invariant |
|---|---|---|---|
| 1 | Sequential progress | StoryManager | N calls → N distinct segments in sequential order |
| 2 | State persistence | StoryManager | `load(save(state)) == state` |
| 3 | Duration bounds | ScriptEngine | Total scene durations sum to 45-50s |
| 4 | Structure bounds | ScriptEngine | 3-5 scenes, all required fields non-empty |
| 5 | Character registry | ScriptEngine | All character names exist in provided registry |
| 6 | Round-trip | EpisodeScript | `parse(pretty_print(script)) == script` |
| 7 | Error handling | EpisodeScript | Invalid JSON → descriptive error, never valid script |
| 8 | Resolution | AnimationEngine | Every frame ≥ 1080x1920 pixels |
| 9 | Voice uniqueness | NarrationEngine | Distinct characters → distinct voice IDs |
| 10 | Volume ducking | AudioEngine | Narration ≥ 6dB louder than music during speech |
| 11 | Audio format | AudioEngine | Output: 44100 Hz, 16-bit |
| 12 | Video format | VideoCompositor | MP4, H.264, AAC, 1080x1920, ≥24fps |
| 13 | Video duration | VideoCompositor | 110-130s |
| 14 | File naming | DistributionManager | Matches `ramayan_e{NNNN}_{kanda}_{YYYYMMDD}.mp4` |
| 15 | Log completeness | DistributionManager | Entry has status, platform, URL, timestamp |
| 16 | Default population | ConfigLoader | Missing optional keys → all defaults populated |
| 17 | Error specificity | ConfigLoader | Invalid values → ConfigError naming specific fields |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for script generation |
| `HF_TOKEN` | Yes | HuggingFace token for FLUX model access |
| `OPENAI_API_KEY` | No | OpenAI API key (backup LLM, not used) |

Loaded via `python-dotenv` from `.env` file at project root.

---

## External Dependencies

| Service | Used For | Cost | Required |
|---|---|---|---|
| Gemini 2.5 Flash | Script generation | ~₹1-2/episode | Yes |
| FLUX.1-schnell | Image generation | Free (local) | Yes |
| Edge TTS | Hindi narration | Free | Yes |
| FFmpeg | Video composition | Free (local) | Yes |
| AWS S3 / GCS | Cloud storage | Variable | No (disabled) |
| YouTube API | Auto-upload | Free | No (disabled) |
