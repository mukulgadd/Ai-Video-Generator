# Project History

The complete evolution of the Ramayan Video Generator — from initial idea through every pivot, bug fix, and iteration to its current state.

---

## The Vision (Early June 2026)

The goal: build a fully automated system that generates one 2-minute animated YouTube Shorts video per day, telling the entire Ramayan epic sequentially. Each episode would feature:
- AI-generated artwork in Indian traditional art style
- Hindi narration with character-specific voices
- Background music and sound effects
- Professional video composition
- YouTube-ready output (thumbnail, metadata, branding)

All running locally on an Apple Silicon Mac overnight, costing about ₹3-4 per episode.

The channel: **सनातन रहस्य (Sanatan Rahasya)** — "Sanatan Secrets" — positioned as daily revelations from the epics with an explainer/secrets format designed for engagement.

---

## Phase 1: Formal Specification

The project started with a structured Kiro spec — proper requirements engineering before writing any code.

**Requirements document** — 10 user stories with detailed acceptance criteria:
1. Daily automated pipeline execution
2. Ramayan story progression (sequential across 7 Kandas)
3. Episode script generation (LLM-based)
4. AI animation generation
5. Narration and dialogue audio
6. Background music and sound effects
7. Video composition and rendering
8. Episode script parsing and serialization
9. Storage and distribution
10. Configuration and customization

**Design document** — Full system architecture:
- Sequential pipeline pattern
- Protocol-based dependency injection
- Technology stack selection
- Component interfaces and data models
- JSON schema definitions

**Task breakdown** — 11 implementation tasks with sub-tasks:
- Each task mapped to specific requirements
- Property-based tests (17 correctness properties) using Hypothesis
- All tasks completed and verified

---

## Phase 2: First Implementation (OpenAI + SDXL + Frame Interpolation)

The original technology choices:
- **OpenAI GPT-4** for script generation
- **Stable Diffusion XL** for local image generation on MPS
- **Coqui TTS / Azure Speech** for narration
- **AnimateDiff / FILM** for frame interpolation between keyframes
- **FFmpeg** (frame sequence → video) for composition

Early entry points built:
- `main.py` — APScheduler daemon with daily cron trigger
- `run_single_episode.py` — Test trigger through the orchestrator
- `compose_video.py` — Debug script to compose video from existing frames in `/tmp`

The first experimental videos appeared around **June 13-15** (found in `output/Created/` as `ramayan_e0004_bala_kanda_20260615.mp4`). These used the frame-sequence composition approach.

---

## Phase 3: The LLM Pivot (OpenAI → Gemini)

Switched from OpenAI GPT-4 to **Google Gemini 2.5 Flash** via the `google-genai` SDK.

**Why:**
- Cost reduction (Gemini Flash is cheaper for structured JSON output)
- Availability and speed
- The `GeminiLLMClient` adapter implements the same `LLMClient` Protocol — drop-in replacement

**Added:** Exponential backoff retry for Gemini's 503/overloaded errors (60s → 120s → 240s → 480s waits, 5 attempts total, ~20 min budget). Gemini was frequently returning 503 under load.

---

## Phase 4: The Image Generator Journey (SDXL → FLUX → Gemini)

The most turbulent part of development. Three different image generators were built.

### Problem: SDXL on MPS had float16 NaN issues

Stable Diffusion XL running on Apple Silicon would sometimes produce NaN values during inference, creating corrupted/black images. This was an upstream PyTorch MPS issue.

### Solution 1: FLUX.1-schnell (current production choice)

Black Forest Labs' FLUX.1-schnell model:
- Works correctly with float16 on MPS (no NaN issues)
- 256-token T5 encoder (vs SDXL's 77-token CLIP limit) — much more detailed prompts preserved
- Only 4 inference steps needed (SDXL needed 15+)
- Better overall image quality for the art style
- ~12 GB model weights, ~12 GB memory during inference

### Solution 2: Gemini Image Generation (cloud fallback)

`GeminiImageGenerator` added as a cloud alternative using Gemini's native Imagen model. Avoids all local GPU issues but costs more per episode.

**Current state:** FLUX is production, SDXL is commented out as backup, Gemini Imagen is available for cloud-only setups.

---

## Phase 5: The Composition Pivot (Frame Interpolation → Ken Burns)

### Original plan

Generate 3 keyframes per scene → interpolate with AnimateDiff/FILM to 12+ FPS → compose frame sequences into video.

### The problem

Frame interpolation was:
- Extremely slow on CPU/MPS (each scene took 10+ minutes)
- Producing uncanny/glitchy results between keyframes
- Causing episodes to exceed the 30-minute timeout in batch runs
- The June 18 batch (22:09) shows all 5 episodes timing out at 30 minutes each

### The solution: Ken Burns effects

Ditched frame interpolation entirely. Instead, apply **zoom/pan animations** to static keyframes via FFmpeg's `zoompan` filter. This:
- Creates dynamic, watchable motion from static images
- Requires zero ML inference (pure FFmpeg)
- Takes 2-3 minutes instead of 30+ for composition
- Looks better than interpolated animation for this art style

7 effect types: `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `pan_up`, `zoom_in_top`, `zoom_in_bottom`. Each keyframe gets a randomly assigned effect.

`compose_video.py` (frame-sequence approach) was superseded by `src/ken_burns_compositor.py`.

---

## Phase 6: The Narration Pivot (Coqui/Azure → Edge TTS)

The original design supported three paid/complex TTS backends. Production settled on **Microsoft Edge TTS**:
- Free, no API key required
- Good Hindi voice quality
- Two base voices: `hi-IN-MadhurNeural` (male), `hi-IN-SwaraNeural` (female)
- Character differentiation via subtle pitch/rate adjustments

14 voice profiles created by varying pitch (±15Hz) and rate (±5%) from the 2 base voices, giving the illusion of multiple voice actors.

---

## Phase 7: Content Format Pivot (Story Narration → Explainer/Secrets)

A major content strategy shift from simple narrative storytelling to an **explainer/secrets format** designed for YouTube engagement.

### Before (simple narration)
"In the ancient kingdom of Ayodhya, King Dasharatha performed a sacred fire ceremony..."

### After (explainer format)
- **Hook:** "Did you know the birth of Bhagwan Ram wasn't just a miracle, but a cosmic blueprint for dharma?"
- **Angle:** One of 7 types — `hidden_meaning`, `why`, `character_study`, `life_lesson`, `unknown_facts`, `what_if`, `debate`
- **Revelation:** Core insight the viewer gains
- **Engagement CTA:** Comment-triggering question

The `EpisodeScript` model was extended with `hook`, `angle`, `revelation`, and `engagement_cta` fields. Story segments in `ramayan_db/` were enriched with:
- `philosophical_themes`
- `lesser_known_facts`
- `debate_angles`
- `modern_relevance`
- `suggested_angles`

This drives Gemini to produce engaging content rather than flat re-tellings.

---

## Phase 8: Branding and YouTube Pipeline

The system grew from "generate video" to "generate upload-ready content":

- **`src/video_branding.py`** — Adds hook text overlay at start, title card (channel name "सनातन रहस्य", episode number, kanda name, angle badge), and end CTA with engagement prompt
- **`src/thumbnail_generator.py`** — Generates 1280x720 YouTube thumbnails with bold hook text, dramatic keyframe background, high-contrast CTR-optimized design
- **`src/youtube_metadata.py`** — Auto-generates title (60-70 chars), description with revelation and CTA, SEO tags, and discovery hashtags
- **`src/subtitle_burner.py`** — Burns English subtitle text directly onto keyframes using Pillow (avoids FFmpeg drawtext complexity)

---

## Phase 9: Quality Gates and Sacred Content Safety

Two critical guardrails added after experiencing real failures:

### Script Quality Gate

Validates LLM output before spending ~35 minutes on image generation:
- Title: English-only, ≤65 chars
- Hook: ends with punctuation, ≤100 chars
- CTA: contains a question mark
- Duration: 45-50s total
- Scene count: 3-5
- All scenes have both Hindi narration and English translation
- Valid angle from the 7 approved types
- Revelation not empty

### Sacred Content Safety

After Gemini generated content with "just a story" in narration (caught in the June 22 batch), a safety system was added:
- Blocks disrespectful patterns in Hindi ("सीता कमजोर", "राम ने अन्याय", etc.)
- Blocks divinity-questioning content ("just a story", "just a myth", "fictional character", "mythological figure")
- Prevents skeptical angles on protected divine characters
- This is non-negotiable — content must treat divine events as sacred truth

### Final Video Validation

Validates the composed video before marking the episode complete:
- File size: 3-50 MB
- Duration: 50-120s
- Video stream: H.264, 1080x1920
- Audio stream: AAC
- ffprobe reads without errors

If any gate fails, the episode is NOT marked complete — the segment stays unconsumed for automatic retry on next run.

---

## Phase 10: Batch Generation Infrastructure

Evolved from single-episode testing to production batch generation:

- **`generate_episode.py`** — The full 10-step production pipeline for a single episode
- **`generate_batch.py`** — Runs N episodes sequentially with per-episode subprocess isolation, timeouts, error handling, and logging
- **`run_nightly.sh`** — Shell wrapper using `caffeinate` to keep the Mac awake overnight

Batch features:
- Each episode in its own subprocess (crash isolation)
- 60-minute timeout per episode (kills stuck FLUX inference)
- 30-second cooldown between episodes (GPU memory release)
- Failure doesn't block next episode
- Detailed logging to `logs/batch_YYYYMMDD_HHMMSS.log`

---

## Phase 11: The Bug Fix Journey (Evidence from Batch Logs)

### June 18, Batch 1 (21:50) — 5/5 FAILED

```
Error: 'narration_en' is a required property
```

Gemini wasn't consistently generating the English narration field. Fix: Made the JSON schema stricter, added `narration_en` explicitly to the prompt requirements.

### June 18, Batch 2 (22:09) — 5/5 TIMED OUT

```
Episode 1 TIMED OUT after 1821s
Episode 2 TIMED OUT after 1805s
...all 5 timed out at ~30 minutes
```

This was during the frame interpolation era. SDXL + AnimateDiff was exceeding the 30-minute timeout per episode. Fix: The Ken Burns pivot (Phase 5) eliminated this bottleneck entirely.

### June 20 (21:52) — 1 success, 4 failures

Multiple issues in one batch:
- Episode 1 succeeded (46 min) — first successful production run!
- Episode 2: `"Duration too long (96.1s, max 75s)"` — quality gate was set to max 75s but videos were naturally ~90s with branding
- Episode 3: `"Additional properties are not allowed ('engagement_cta' was unexpected)"` — Gemini placed `engagement_cta` inside individual scenes instead of at the top level
- Episode 4: timeout (FLUX got stuck)

Fixes:
- Relaxed duration gate from 75s max to 120s max
- Tightened JSON schema with `additionalProperties: false` on scene objects

### June 21, Batch 1 (01:11) — 3 success, 2 failures

- Episode 1: `"Duration too long (92.7s, max 75s)"` — duration gate still at 75s at this point
- Episode 2: timeout (60 min — timeout already increased from 30 to 60)
- Episodes 3-5: succeeded (~42-55 min each)

This batch showed the system was getting close. Three successful episodes proved the pipeline works end-to-end.

### June 21, Batch 2 (22:25) — 5/5 SUCCESS

```
Episode 1 completed in 2672s
Episode 2 completed in 2642s
Episode 3 completed in 2776s
Episode 4 completed in 2922s
Episode 5 completed in 3220s
Total time: 3:59:13
Avg time per episode: 0:47:26
```

**The breakthrough.** First clean batch run with 100% success rate. All fixes working together: Ken Burns compositor, relaxed duration gates, strict schema, Edge TTS, FLUX.1-schnell.

### June 22 (02:27) — 4/5 success, 1 failure

```
Episode 3 FAILED:
Sacred content safety check failed:
Divinity-questioning content detected: 'just a story' found.
Content must treat divine events as sacred truth, not mythology.
```

The sacred content safety gate caught its first real violation. Gemini generated narration containing "just a story" — the safety system worked exactly as designed, preventing publication of inappropriate content. The other 4 episodes completed normally.

---

## Phase 12: Visual Polish

Additional modules added for visual variety and atmosphere:

- **`src/visual_variety.py`** — Varies image composition based on scene role (hook = dramatic close-up, context = wide establishing shot, revelation = symbolic imagery with divine glow, CTA = warm inviting close-up). Prevents all keyframes from looking identical.
- **`src/sfx_mapper.py`** — Maps scene moods to ambient sound effects automatically ("devotional" → temple bells + incense wind, "battle" → swords + drums + arrows). Ensures atmosphere even when Gemini doesn't specify explicit SFX.

---

## Phase 13: Character System

14 characters defined with visual descriptions for AI consistency:

| Character | Prompt Description Highlight |
|---|---|
| Rama | Blue-skinned prince, golden crown, bow in hand, serene compassion |
| Sita | Beautiful princess, green saree with gold, lotus in hand |
| Hanuman | Muscular monkey warrior, orange dhoti, mace, devoted expression |
| Ravana | Ten-headed demon king, dark armor, golden crown, fierce |
| Lakshmana | Young warrior, golden armor, quiver of arrows, alert |
| Bharata | Orange dhoti with gold border, humble, carrying Rama's sandals |
| King Dasharatha | Elderly king, elaborate crown, white beard, regal |
| Vishwamitra | Sage in saffron robes, matted hair, powerful staff |
| And 6 more... | |

Each `character.json` provides a `prompt_description` injected into every image generation prompt containing that character, ensuring visual consistency across episodes.

---

## Current State (June 22, 2026)

### What's Working

- **9 episodes generated** (all Bala Kanda)
- **5/5 success rate** on latest batch (June 21-22)
- **~45 min per episode** average generation time
- Full 10-step pipeline running end-to-end
- Quality gates catching bad output before marking complete
- Sacred content safety preventing inappropriate framing
- Batch generation with overnight caffeinate

### Output Per Episode

```
ramayan_e{NNNN}_{kanda}_{date}.mp4     (~13-20 MB branded video)
ramayan_e{NNNN}_thumbnail.jpg           (~110 KB YouTube thumbnail)
ramayan_e{NNNN}_metadata.txt            (title, description, tags, hashtags)
episode_{NNNN}_audio.wav                (~11 MB intermediate audio)
```

### Architecture Stats

- 27 Python source files in `src/`
- 6 entry points/scripts
- 14 character definitions
- 20 music tracks + 20 SFX clips
- 17 correctness properties (all verified)
- 10 story segments populated (Kanda 1-2)
- 7 Kanda directory stubs (3-7 need content)

### What's Not Done Yet

1. **Kandas 3-7 segments** — Only Bala Kanda and Ayodhya Kanda are populated with story content
2. **YouTube auto-upload** — Distribution is configured but disabled (needs OAuth setup)
3. **Git history** — No commits yet; the entire working state needs to be committed
4. **Orchestrator reconciliation** — `generate_episode.py` has features the orchestrator doesn't (Ken Burns, subtitles, branding, quality gates)
5. **IP-Adapter Mode 2** — Character visual consistency currently relies on prompt descriptions only; full embedding injection not yet implemented

---

## Timeline Summary

| Date | Milestone |
|---|---|
| Early June | Formal spec: requirements, design, 11 tasks |
| June 13-15 | First experimental videos (SDXL + frame sequence) |
| June 15-17 | LLM pivot: OpenAI → Gemini |
| June 17-18 | Image pivot: SDXL → FLUX.1-schnell |
| June 18 | First batch attempt — all failed (schema + timeout issues) |
| June 18-19 | Composition pivot: frame interpolation → Ken Burns |
| June 19-20 | Narration pivot: settled on Edge TTS |
| June 20 | First successful episode in batch |
| June 20-21 | Content pivot: simple narration → explainer/secrets format |
| June 21 | Branding, thumbnails, metadata, quality gates added |
| June 21 (night) | First 100% clean batch (5/5 success) |
| June 22 | Sacred content safety catches first real violation |
| June 22 | 9 total episodes generated, system stable |

---

## Lessons Learned

1. **Start with the spec** — The Kiro spec (requirements → design → tasks) gave structure to an ambiguous creative project. Without it, the pivots would have been chaos.

2. **Protocol-based DI pays off fast** — Swapping SDXL → FLUX → Gemini for image generation required changing one line in `generate_episode.py`. The animation engine didn't change at all.

3. **Quality gates save compute** — A failed script gate (2 seconds) saves 35 minutes of FLUX inference on a bad script. The gates paid for themselves immediately.

4. **Batch logs are your debugging lifeline** — Every failure was diagnosed from `logs/batch_*.log`. Without per-episode error capture, the system would be a black box.

5. **Sacred content safety is necessary** — LLMs will occasionally produce content that questions divinity or uses disrespectful framing. For a spiritual channel, this is unacceptable. The safety check proved its worth on June 22.

6. **Ken Burns > frame interpolation for this use case** — Static keyframes with zoom/pan look better than AI-interpolated animation for traditional art style. The uncanny valley of bad interpolation is worse than no animation at all.

7. **Edge TTS is surprisingly good** — Free, no API key, good Hindi quality, and pitch/rate adjustments create convincing character differentiation from just 2 base voices.

8. **Overnight batch on Mac is practical** — `caffeinate` + subprocess isolation + timeout handling makes the Mac a reliable overnight rendering farm. No cloud GPU costs.
