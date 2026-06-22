# Contributing Guide

How to work on the Ramayan Video Generator codebase — code standards, testing, and adding new components.

---

## Project Principles

1. **Protocol-based DI** — Every external dependency (LLM, image gen, TTS, FFmpeg, cloud) is behind a Python `Protocol`. New implementations are drop-in replacements.
2. **File-based persistence** — All state is JSON on disk. No databases. The system is restartable at any point.
3. **Quality gates over silent failures** — Bad output is rejected, not published. The segment stays unconsumed for the next run.
4. **Sacred content safety** — Content must treat divine figures with reverence. The safety check is non-negotiable.
5. **Local-first** — The pipeline runs on a single Mac overnight. Cloud services are optional enhancements.

---

## Code Structure

```
src/                         # Core pipeline modules
├── config_loader.py         # Config system
├── story_manager.py         # State machine
├── episode_script.py        # Data model + schema
├── script_engine.py         # LLM integration + safety
├── gemini_llm_client.py     # Gemini API adapter
├── animation_engine.py      # Image gen orchestration + Protocols
├── flux_image_generator.py  # FLUX implementation
├── sd_image_generator.py    # SDXL implementation
├── gemini_image_generator.py # Gemini Imagen implementation
├── ip_adapter.py            # Character consistency
├── visual_variety.py        # Composition directives
├── narration_engine.py      # TTS orchestration + Protocols
├── edge_tts_adapter.py      # Edge TTS implementation
├── audio_engine.py          # Audio mixing (pydub)
├── sfx_mapper.py            # Mood → SFX mapping
├── ken_burns_compositor.py  # FFmpeg zoompan video
├── subtitle_burner.py       # Pillow subtitle overlay
├── video_branding.py        # Hook/title/CTA branding
├── thumbnail_generator.py   # YouTube thumbnail
├── youtube_metadata.py      # SEO metadata
├── quality_gates.py         # Validation checkpoints
├── video_compositor.py      # Legacy frame-sequence compositor
├── distribution_manager.py  # Upload + publish
├── orchestrator.py          # Pipeline coordinator
├── scheduler.py             # APScheduler wrapper
└── notifications.py         # Failure alerts
```

---

## Code Standards

### Style

- Python 3.11+ type hints on all function signatures
- Dataclasses for data models (not dicts)
- Docstrings on all classes and public methods (Google-style)
- `logging` module for all output (no `print()`)
- Max line length: 100 characters (soft limit)

### Naming

- Modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`
- Protocol classes: named by capability (`ImageGenerator`, `TTSProvider`)

### Error Handling

- Each module defines its own `*Error(Exception)` class
- Errors carry `message` attribute with human-readable details
- Retry logic belongs in the calling layer (orchestrator/script), not the component
- Never swallow exceptions silently — log them at minimum

### Imports

- Standard library first, then third-party, then local (`src.*`)
- Use absolute imports: `from src.episode_script import EpisodeScript`
- Avoid circular imports — if needed, use `TYPE_CHECKING`

---

## Adding a New Component

### Adding a New Image Generator

1. Create `src/my_image_generator.py`
2. Implement the `ImageGenerator` Protocol:

```python
"""My Custom Image Generator."""

from typing import Any, Dict, List, Optional
from PIL import Image


class MyImageGenerator:
    """Implements ImageGenerator Protocol from animation_engine.py."""

    def __init__(self, ...):
        # Your initialization

    def generate(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        num_images: int,
        lora_path: Optional[str] = None,
        character_embeddings: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Image.Image]:
        """Generate images from prompt."""
        # Your implementation
        ...
```

3. Wire it in `generate_episode.py`:
```python
from src.my_image_generator import MyImageGenerator
animation_engine = AnimationEngine(
    config=config.animation, image_generator=MyImageGenerator(...)
)
```

4. No other changes needed — Protocol-based DI handles the rest.

### Adding a New TTS Provider

1. Create `src/my_tts_adapter.py`
2. Implement the `TTSProvider` Protocol:

```python
class MyTTSAdapter:
    """Implements TTSProvider Protocol from narration_engine.py."""

    def synthesize(
        self,
        text: str,
        voice_id: str,
        locale: str,
        speech_rate: float,
    ) -> bytes:
        """Return WAV format audio bytes."""
        # Your implementation
        ...
```

3. Register in `src/narration_engine.py`:
```python
def create_tts_provider(provider_name: str) -> Any:
    if provider_name == "my_tts":
        from src.my_tts_adapter import MyTTSAdapter
        return MyTTSAdapter()
    ...
```

4. Set in `config.yaml`:
```yaml
narration:
  tts_provider: "my_tts"
```

### Adding a New Story Segment

Create a JSON file in `ramayan_db/kandas/{N}_{kanda_name}/segments/{NNN}.json`:

```json
{
  "kanda_index": 1,
  "kanda_name": "Bala Kanda",
  "chapter": 3,
  "segment_index": 6,
  "title": "Your Segment Title",
  "content": "Full narrative paragraph (200-400 words optimal)...",
  "characters": ["Rama", "Lakshmana", "Sage Vishwamitra"],
  "key_events": [
    "Event 1 happens",
    "Event 2 happens"
  ],
  "philosophical_themes": ["dharma", "courage"],
  "lesser_known_facts": [
    "A detail often omitted from popular retellings..."
  ],
  "debate_angles": [
    "Was X's decision justified given Y?"
  ],
  "modern_relevance": [
    "This mirrors modern situation Z..."
  ],
  "suggested_angles": ["hidden_meaning", "life_lesson"]
}
```

The `StoryManager` auto-discovers segments by filename order (001.json, 002.json, ...).

### Adding a New Character

Create `models/characters/{name}/character.json`:

```json
{
  "name": "Character Name",
  "description": "Brief role description",
  "prompt_description": "Detailed visual description for AI image generation — clothing, appearance, expression, distinctive features",
  "reference_images": [],
  "embedding_file": ""
}
```

Then add their voice mapping in `config.yaml`:
```yaml
narration:
  character_voices:
    "Character Name": "voice_character_01"
```

And register the voice in `src/edge_tts_adapter.py`:
```python
VOICE_MAP = {
    ...
    "voice_character_01": ("hi-IN-MadhurNeural", "+0Hz", "+0%"),
}
```

### Adding a New Music Track

1. Place the MP3 file in `assets/music/` with naming: `{mood}_track{N}.mp3`
2. Valid moods: `devotional`, `dramatic`, `serene`, `battle`, `festive`, `hopeful`, `melancholy`, `mysterious`, `joyful`, `celebratory`, `miraculous`
3. The `MusicLibrary` auto-discovers tracks by filename prefix

### Adding a New SFX Clip

1. Place the MP3 in `assets/sfx/` with naming: `{effect_name}.mp3`
2. Optionally add to `src/sfx_mapper.py` mood mapping:
```python
MOOD_AMBIENT_MAP = {
    "your_mood": ["your_effect_name", ...],
}
```

---

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_script_engine.py -v

# Property-based tests only
pytest tests/ -v -k "hypothesis"

# With coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### Test Architecture

Tests use Hypothesis for property-based testing. The 17 properties verify invariants that must hold for ANY valid input, not just specific examples.

| Test File | Properties Covered |
|---|---|
| `test_config_loader.py` | P16: missing keys → defaults; P17: invalid → ConfigError |
| `test_story_manager.py` | P1: N calls → N distinct ordered segments; P2: save/load round-trip |
| `test_episode_script.py` | P6: parse/print round-trip; P7: invalid → descriptive error |
| `test_script_engine.py` | P3: duration 45-50s; P4: 3-5 scenes; P5: characters in registry |
| `test_animation_engine.py` | P8: frames ≥ 1080x1920 |
| `test_narration_engine.py` | P9: distinct characters → distinct voices |
| `test_audio_engine.py` | P10: narration ≥ 6dB > music; P11: 44100Hz 16-bit |
| `test_video_compositor.py` | P12: MP4/H264/AAC/1080x1920/24fps; P13: 110-130s |
| `test_distribution_manager.py` | P14: filename format; P15: log completeness |
| `test_orchestrator.py` | Sequential execution, retry, notification |
| `test_integration.py` | End-to-end with all mocks |

### Writing Tests

For a new component, write:
1. **Unit tests** — Test the component in isolation with mocked dependencies
2. **Property tests** — Define invariants that must hold for any valid input
3. **Edge case tests** — Boundary conditions, error paths, retry scenarios

Example property test:
```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=1, max_value=7))
def test_kanda_index_always_valid(kanda_index):
    """Any kanda index 1-7 should produce a valid directory path."""
    manager = StoryManager(db_path="ramayan_db")
    path = manager._get_kanda_dir(kanda_index)
    assert os.path.isdir(path)
```

### Mock Strategy

Every Protocol has a mock implementation:
- `StableDiffusionGenerator` — Returns solid-color PNGs (no ML inference)
- `CLIPQualityScorer` — Returns configurable float
- `FILMFrameInterpolator` — Returns alpha-blended images
- `MockRenderer` — Writes JSON metadata files (no FFmpeg)
- `MockStorageUploader` — Records uploads in memory
- `MockPlatformPublisher` — Records publish calls
- `MockNotificationAdapter` — Records alerts

Use these in tests to avoid needing real services:
```python
from src.animation_engine import AnimationEngine, StableDiffusionGenerator, CLIPQualityScorer

engine = AnimationEngine(
    config=animation_config,
    image_generator=StableDiffusionGenerator(),
    quality_scorer=CLIPQualityScorer(threshold=0.0),  # Accept everything
)
```

---

## Quality Gate Rules

When modifying quality gates (`src/quality_gates.py`):

- **Never weaken a gate without documenting why** — If you increase duration tolerance, note what broke at the old limit
- **Gates protect against wasted compute** — A failed script gate saves ~35 min of image generation
- **Sacred content safety is non-negotiable** — The patterns protect religious sentiments
- **Video validation prevents publishing broken files** — Users see the output

---

## Modifying the Script Engine Prompt

The LLM system prompt in `src/script_engine.py` controls script quality. When editing:

1. **Test with 5+ episodes** — Gemini is non-deterministic; one good result proves nothing
2. **Check all angle types** — Some prompts work for "hidden_meaning" but break "debate"
3. **Verify schema compliance** — Gemini loves adding extra fields or renaming things
4. **Watch for Hindi in English fields** — Title, hook, CTA must be English-only
5. **Check sacred content** — New prompt wording can accidentally trigger safety violations

---

## Batch Testing a Change

After any significant change, run a mini-batch to verify:

```bash
# Reset position to segment 1 for testing (backup first!)
cp ramayan_db/metadata.json ramayan_db/metadata_backup.json

# Run 2-3 episodes
python generate_batch.py --count 3

# Check logs
cat logs/batch_*.log | tail -30

# Restore position
cp ramayan_db/metadata_backup.json ramayan_db/metadata.json
```

---

## Common Patterns

### Adding a new pipeline step to generate_episode.py

```python
# After step N, before step N+1:
logger.info("Doing new thing...")
result = do_new_thing(
    input_from_previous_step,
    config_value=config.section.value,
)
logger.info(f"New thing done: {result}")
```

### Adding a new config field

1. Add to the dataclass in `src/config_loader.py`:
```python
@dataclass
class MyConfig:
    new_field: str = "default_value"
```

2. Add validation in `_validate_config()` if needed
3. Add to `config.yaml` with the default value
4. Update `SETUP.md` config reference

### Adding a new quality gate check

In `src/quality_gates.py`:
```python
def validate_my_thing(input) -> Tuple[bool, List[str]]:
    issues = []
    if not meets_criteria(input):
        issues.append(f"Description of what failed: {details}")
    return len(issues) == 0, issues
```

Then call it in `generate_episode.py` at the appropriate point.

---

## Commit Guidelines

- Keep commits focused: one logical change per commit
- Prefix commit messages:
  - `feat:` — New feature
  - `fix:` — Bug fix
  - `refactor:` — Code restructuring (no behavior change)
  - `docs:` — Documentation only
  - `test:` — Adding/fixing tests
  - `config:` — Configuration changes
  - `content:` — Story segments, characters, music, SFX additions

Examples:
```
feat: add Gemini image generator as cloud fallback
fix: relax video duration gate from 75s to 120s max
content: add Ayodhya Kanda segments 001-005
test: add property test for thumbnail file size validation
```

---

## Known Limitations

Things to be aware of when contributing:

1. **generate_episode.py diverged from orchestrator** — The production script has features (Ken Burns, subtitles, branding, quality gates) the orchestrator doesn't. They should eventually be reconciled.
2. **Kandas 3-7 have no segments** — Only Bala Kanda and Ayodhya Kanda are populated. More content needs writing.
3. **No git history** — The project hasn't been committed yet. First commit should capture the current working state.
4. **Edge TTS has 2 base voices only** — Character differentiation relies on subtle pitch/rate shifts. Adding more distinct voices requires a paid TTS service.
5. **FLUX.1-schnell has no negative prompt** — The `negative_prompt` parameter is ignored by FLUX Schnell. Quality relies entirely on positive prompt crafting.
6. **No YouTube auto-upload yet** — Distribution is configured but disabled. Requires OAuth setup with YouTube Data API.
