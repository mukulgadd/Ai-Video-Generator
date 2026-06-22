# Tasks: Ramayan Video Generator

## Task 1: Project Setup and Configuration

- [x] 1.1 Initialize Python project structure with `main.py`, `src/` package, `tests/` directory, `assets/`, `models/`, `ramayan_db/`, `output/`, and `credentials/` directories
- [x] 1.2 Create `requirements.txt` with dependencies: openai, diffusers, torch, Pillow, pydub, librosa, ffmpeg-python, pyyaml, apscheduler, boto3, google-cloud-storage, hypothesis, pytest, jsonschema, requests
- [x] 1.3 Implement `src/config_loader.py` with `load_config(path: str) -> Config` that reads YAML config, validates all fields, applies documented defaults for missing optional keys, and raises `ConfigError` with specific field names for invalid values
- [x] 1.4 Create `config.yaml` with all default configuration values as documented in the design (schedule_time, animation settings, narration settings, audio settings, output format, storage, distribution, notifications)
- [x] 1.5 Write tests for config_loader: valid config loading, missing optional keys use defaults, invalid values produce specific errors
  - [x] 1.5.1 [PBT] Property test: for any configuration with missing optional keys, the resolved config has no missing values and all defaults match documented values (Property 16)
  - [x] 1.5.2 [PBT] Property test: for any configuration with invalid values (wrong types, out-of-range), ConfigError is raised naming the specific invalid fields (Property 17)

## Task 2: Story Manager and Ramayan Database

- [x] 2.1 Design and create the Ramayan story segment JSON schema with fields: `kanda_index`, `kanda_name`, `chapter`, `segment_index`, `title`, `content`, `characters`, `key_events`
- [x] 2.2 Create initial story database structure under `ramayan_db/` with `metadata.json` and `kandas/` directory structure for all 7 Kandas
- [x] 2.3 Populate at least 10 sample story segments across the first 2 Kandas (Bala Kanda and Ayodhya Kanda) for development and testing
- [x] 2.4 Implement `src/story_manager.py` with `StoryManager` class: `get_next_segment()`, `mark_episode_complete()`, `get_current_position()`, `is_series_complete()`, state persistence via `metadata.json`
- [x] 2.5 Implement Kanda boundary advancement: when the last segment of a Kanda is completed, automatically advance to the first segment of the next Kanda
- [x] 2.6 Implement series completion detection: when the last segment of Uttara Kanda is completed, mark series as complete
- [x] 2.7 Write tests for StoryManager
  - [x] 2.7.1 [PBT] Property test: for N calls to `get_next_segment()`, exactly N distinct segments are returned in sequential order and position reflects N segments of progress (Property 1)
  - [x] 2.7.2 [PBT] Property test: saving state then loading produces equivalent state — `load(save(state)) == state` (Property 2)
  - [x] 2.7.3 Test Kanda boundary advancement (edge case): completing last segment of Bala Kanda advances to first segment of Ayodhya Kanda
  - [x] 2.7.4 Test series completion (edge case): completing last segment of Uttara Kanda marks series complete

## Task 3: Episode Script Model, Parser, and Serializer

- [x] 3.1 Define `EpisodeScript` data model in `src/episode_script.py` with fields: `episode_number`, `kanda`, `title`, `total_duration_seconds`, `scenes[]` (each scene: `scene_number`, `duration_seconds`, `background`, `characters[]`, `action`, `narration`, `dialogue[]`, `mood`, `sound_effects[]`)
- [x] 3.2 Create JSON schema definition for episode script validation
- [x] 3.3 Implement `serialize(script: EpisodeScript) -> str` that converts an EpisodeScript to JSON string
- [x] 3.4 Implement `pretty_print(script: EpisodeScript) -> str` that converts an EpisodeScript to formatted JSON string
- [x] 3.5 Implement `parse(json_str: str) -> EpisodeScript` that parses JSON string into EpisodeScript with schema validation, returning descriptive errors for invalid input
- [x] 3.6 Write tests for episode script parser and serializer
  - [x] 3.6.1 [PBT] Property test: for any valid EpisodeScript, `parse(pretty_print(script)) == script` — round-trip preserves all fields (Property 6)
  - [x] 3.6.2 [PBT] Property test: for any invalid JSON string (malformed or schema violations), parser returns descriptive error, not a valid EpisodeScript (Property 7)
  - [x] 3.6.3 Test that serialized output is valid JSON conforming to the defined schema

## Task 4: Script Engine (LLM-based Script Generation)

- [x] 4.1 Implement `src/script_engine.py` with `ScriptEngine` class that takes a story segment and character registry, calls the configured LLM API with a structured prompt, and returns an `EpisodeScript`
- [x] 4.2 Design the LLM system prompt that defines the scriptwriter role, Indian traditional art style context, output JSON schema, and constraints (4-8 scenes, 110-130s total duration)
- [x] 4.3 Implement character registry lookup: load character names and descriptions from `models/characters/` and inject into the LLM prompt
- [x] 4.4 Implement script validation: after LLM response, validate scene count (4-8), total duration (110-130s), required fields per scene, and character name consistency against registry
- [x] 4.5 Implement segment merging: if a story segment is too short for a full episode, merge with the next segment and notify StoryManager
- [x] 4.6 Write tests for ScriptEngine
  - [x] 4.6.1 [PBT] Property test: for any generated script, total scene durations sum to 110-130 seconds (Property 3)
  - [x] 4.6.2 [PBT] Property test: for any generated script, scene count is 4-8 and each scene has non-empty required fields (Property 4)
  - [x] 4.6.3 [PBT] Property test: for any generated script, all character names exist in the provided character registry (Property 5)
  - [x] 4.6.4 Test segment merging edge case: short segment triggers merge with next segment

## Task 5: Animation Engine

- [x] 5.1 Implement `src/animation_engine.py` with `AnimationEngine` class that generates keyframes from scene descriptions using Stable Diffusion with configured LoRA and style reference
- [x] 5.2 Implement character consistency using IP-Adapter: load character reference embeddings from `models/characters/` and inject into the generation pipeline for each scene
- [x] 5.3 Implement frame interpolation between keyframes using AnimateDiff or FILM to achieve 12+ FPS smooth animation
- [x] 5.4 Implement quality validation: run CLIP-based quality scorer on each frame, regenerate frames below threshold up to 3 times, use best-scoring attempt if all fail
- [x] 5.5 Implement key frame selection for thumbnail generation: select the highest-quality frame from the episode for use as distribution thumbnail
- [x] 5.6 Write tests for AnimationEngine
  - [x] 5.6.1 [PBT] Property test: for any generated frame, width >= 1080 and height >= 1920 (Property 8)
  - [x] 5.6.2 Test frame regeneration retry logic: mock quality validator to fail, verify up to 3 retries
  - [x] 5.6.3 Test character embedding loading: verify embeddings are loaded for characters present in the scene

## Task 6: Narration Engine

- [x] 6.1 Implement `src/narration_engine.py` with `NarrationEngine` class that generates spoken audio from narration text and dialogue using a configured TTS provider
- [x] 6.2 Implement voice profile management: map character names to voice IDs from configuration, use default narrator voice for non-dialogue narration
- [x] 6.3 Implement TTS provider adapter pattern to support multiple backends (Coqui TTS, Azure Speech, ElevenLabs) via a common interface
- [x] 6.4 Implement duration synchronization: measure generated audio duration against script timing cues, adjust speech rate and regenerate if duration exceeds tolerance (±2 seconds)
- [x] 6.5 Write tests for NarrationEngine
  - [x] 6.5.1 [PBT] Property test: for any two distinct characters in voice config, assigned voice profile IDs are different (Property 9)
  - [x] 6.5.2 Test duration adjustment edge case: mock TTS to produce oversized audio, verify speech rate adjustment and regeneration
  - [x] 6.5.3 Test locale configuration: verify configured locale (default Hindi) is passed to TTS provider

## Task 7: Audio Engine

- [x] 7.1 Implement `src/audio_engine.py` with `AudioEngine` class that selects background music based on scene mood tags from the music library
- [x] 7.2 Implement audio mixing: combine narration audio with background music, applying volume ducking (narration at least 6 dB louder than music during speech)
- [x] 7.3 Implement sound effect placement: add sound effects from the SFX library at timestamps specified in the episode script
- [x] 7.4 Implement crossfade transitions between scenes (0.5-1.0 seconds configurable)
- [x] 7.5 Implement final audio export in WAV format at 44100 Hz, 16-bit
- [x] 7.6 Write tests for AudioEngine
  - [x] 7.6.1 [PBT] Property test: for any mixed audio segment with speech, narration level is at least 6 dB louder than background music (Property 10)
  - [x] 7.6.2 [PBT] Property test: for any produced audio file, sample rate is 44100 Hz and bit depth is 16 (Property 11)
  - [x] 7.6.3 Test crossfade transitions: verify transitions between scenes are 0.5-1.0 seconds

## Task 8: Video Compositor

- [x] 8.1 Implement `src/video_compositor.py` with `VideoCompositor` class that encodes frame sequences into video streams per scene using FFmpeg
- [x] 8.2 Implement visual transitions: apply crossfade/dissolve transitions between scenes with configurable duration (default 0.5s)
- [x] 8.3 Implement title card overlay: render episode title (Kanda name + episode number) at the beginning of the video for 3-5 seconds
- [x] 8.4 Implement final rendering: combine video stream with audio track, encode to MP4 (H.264 + AAC) at 1080x1920, 24 FPS
- [x] 8.5 Implement duration enforcement: validate final video is 110-130 seconds, trim final scene with fade-out if over 130 seconds, log warning
- [x] 8.6 Write tests for VideoCompositor
  - [x] 8.6.1 [PBT] Property test: for any output video, format is MP4, video codec is H.264, audio codec is AAC, resolution is 1080x1920, FPS >= 24 (Property 12)
  - [x] 8.6.2 [PBT] Property test: for any output video, duration is between 110 and 130 seconds (Property 13)
  - [x] 8.6.3 Test duration trimming edge case: provide content exceeding 130 seconds, verify trimming and warning log

## Task 9: Distribution Manager

- [x] 9.1 Implement `src/distribution_manager.py` with `DistributionManager` class that uploads video files to configured cloud storage (S3/GCS)
- [x] 9.2 Implement standardized file naming: `ramayan_e{NNNN}_{kanda_name}_{YYYYMMDD}.mp4`
- [x] 9.3 Implement optional platform publishing: upload to YouTube/Instagram with auto-generated title, description, and tags when enabled in config
- [x] 9.4 Implement thumbnail upload: upload the key frame thumbnail alongside the video
- [x] 9.5 Implement retry logic: retry failed uploads up to 3 times with exponential backoff
- [x] 9.6 Implement distribution logging: record upload status, platform, URL, and timestamp for each distribution event
- [x] 9.7 Write tests for DistributionManager
  - [x] 9.7.1 [PBT] Property test: for any episode number, Kanda name, and date, generated filename matches `ramayan_e{NNNN}_{kanda_name}_{YYYYMMDD}.mp4` (Property 14)
  - [x] 9.7.2 [PBT] Property test: for any distribution event, log entry contains upload status, platform, URL (if successful), and timestamp (Property 15)
  - [x] 9.7.3 Test retry with exponential backoff: mock upload failures, verify 3 retries with increasing delays

## Task 10: Pipeline Orchestrator and Scheduler

- [x] 10.1 Implement `src/orchestrator.py` with `VideoGeneratorOrchestrator` class that executes all pipeline stages in sequence: Story_Manager → Script_Engine → Animation_Engine → Narration_Engine → Audio_Engine → Video_Compositor → Distribution_Manager
- [x] 10.2 Implement stage retry logic: if a stage fails, retry up to 3 times before marking the episode as failed
- [x] 10.3 Implement failure notification: send notification to configured channel when all retries for a stage are exhausted
- [x] 10.4 Implement `src/notifications.py` with notification adapters (email, webhook) for pipeline failure alerts
- [x] 10.5 Implement `src/scheduler.py` with APScheduler-based daily trigger at configured time, calling the orchestrator
- [x] 10.6 Implement `main.py` entry point that loads config, initializes all components, and starts the scheduler
- [x] 10.7 Implement pipeline logging: log episode number, Kanda name, stage progress, and output file path for each run
- [x] 10.8 Write tests for orchestrator: mock all pipeline stages, verify sequential execution, retry logic, and failure notification

## Task 11: Integration and End-to-End Testing

- [x] 11.1 Create an end-to-end integration test that runs the full pipeline with mock AI services (mock LLM, mock Stable Diffusion, mock TTS) to verify the complete flow from story segment to output video file
- [x] 11.2 Verify that the pipeline produces a valid MP4 file with correct format, resolution, and duration from mock inputs
- [x] 11.3 Verify that the Story_Manager advances correctly after a successful pipeline run
- [x] 11.4 Verify that the Distribution_Manager logs the correct metadata after a successful upload (using mock storage)
- [x] 11.5 Test pipeline failure and recovery: simulate a stage failure, verify retry behavior, and confirm the pipeline can resume from the failed episode on the next run
