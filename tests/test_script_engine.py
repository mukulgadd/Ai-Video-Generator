"""Tests for the script_engine module.

Tests verify:
- Property 3: Total scene durations sum to 110-130 seconds
- Property 4: Scene count is 4-8 and each scene has non-empty required fields
- Property 5: All character names exist in the provided character registry
- Segment merging edge case: short segment triggers merge
"""

import json
import os
import tempfile

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.episode_script import (
    DialogueLine,
    EpisodeScript,
    Scene,
)
from src.script_engine import (
    ScriptEngine,
    ScriptEngineError,
    ScriptValidationError,
    is_segment_too_short,
    load_character_registry,
    merge_segments,
    validate_script,
    MIN_SEGMENT_WORD_COUNT,
)
from src.story_manager import StorySegment


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_non_empty_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=60,
).filter(lambda s: s.strip() != "")

# Character names drawn from a fixed pool to test registry consistency
_character_pool = [
    "Rama", "Sita", "Lakshmana", "Hanuman", "Ravana",
    "King_Dasharatha", "Sage_Vasishtha", "Bharata",
]

_character_name = st.sampled_from(_character_pool)


def _dialogue_line_strategy(character_names_st):
    """Build a DialogueLine strategy using characters from the given strategy."""
    return st.builds(
        DialogueLine,
        character=character_names_st,
        text=_non_empty_text,
    )


def _valid_scene_strategy(
    character_names_st,
    duration_st=st.integers(min_value=15, max_value=30),
):
    """Build a Scene strategy with valid required fields."""
    return st.builds(
        Scene,
        scene_number=st.integers(min_value=1, max_value=20),
        duration_seconds=duration_st,
        background=_non_empty_text,
        characters=st.lists(character_names_st, min_size=1, max_size=4),
        action=_non_empty_text,
        narration=_non_empty_text,
        dialogue=st.lists(
            _dialogue_line_strategy(character_names_st), min_size=0, max_size=3
        ),
        mood=_non_empty_text,
        sound_effects=st.lists(_non_empty_text, min_size=0, max_size=3),
    )


def _valid_episode_script_strategy():
    """Generate EpisodeScript objects with 4-8 scenes totaling 110-130s.

    Uses a composite strategy to ensure duration constraints are met.
    """
    return st.integers(min_value=4, max_value=8).flatmap(
        lambda n_scenes: _build_script_with_n_scenes(n_scenes)
    )


@st.composite
def _build_script_with_n_scenes(draw, n_scenes):
    """Build an EpisodeScript with exactly n_scenes scenes summing to 110-130s."""
    # Distribute total duration across scenes
    total = draw(st.integers(min_value=110, max_value=130))

    # Generate n_scenes durations that sum to total
    # Use a simple approach: generate n-1 random durations, last one is remainder
    if n_scenes == 1:
        durations = [total]
    else:
        # Each scene needs at least 1 second
        remaining = total - n_scenes  # reserve 1s per scene minimum
        cuts = sorted(draw(
            st.lists(
                st.integers(min_value=0, max_value=remaining),
                min_size=n_scenes - 1,
                max_size=n_scenes - 1,
            )
        ))
        durations = []
        prev = 0
        for cut in cuts:
            durations.append(cut - prev + 1)  # +1 for the reserved minimum
            prev = cut
        durations.append(remaining - prev + 1)

    scenes = []
    for i, dur in enumerate(durations):
        scene = draw(_valid_scene_strategy(
            _character_name,
            duration_st=st.just(dur),
        ))
        # Override scene_number to be sequential
        scene = Scene(
            scene_number=i + 1,
            duration_seconds=dur,
            background=scene.background,
            characters=scene.characters,
            action=scene.action,
            narration=scene.narration,
            dialogue=scene.dialogue,
            mood=scene.mood,
            sound_effects=scene.sound_effects,
        )
        scenes.append(scene)

    return EpisodeScript(
        episode_number=draw(st.integers(min_value=1, max_value=9999)),
        kanda=draw(_non_empty_text),
        title=draw(_non_empty_text),
        total_duration_seconds=total,
        scenes=scenes,
    )


# Strategy for scripts that may violate duration constraints
@st.composite
def _arbitrary_duration_script(draw):
    """Generate scripts with arbitrary durations (may be outside 110-130s)."""
    n_scenes = draw(st.integers(min_value=1, max_value=12))
    scenes = []
    for i in range(n_scenes):
        scene = draw(_valid_scene_strategy(
            _character_name,
            duration_st=st.integers(min_value=1, max_value=60),
        ))
        scene = Scene(
            scene_number=i + 1,
            duration_seconds=scene.duration_seconds,
            background=scene.background,
            characters=scene.characters,
            action=scene.action,
            narration=scene.narration,
            dialogue=scene.dialogue,
            mood=scene.mood,
            sound_effects=scene.sound_effects,
        )
        scenes.append(scene)

    total = sum(s.duration_seconds for s in scenes)
    return EpisodeScript(
        episode_number=draw(st.integers(min_value=1, max_value=9999)),
        kanda=draw(_non_empty_text),
        title=draw(_non_empty_text),
        total_duration_seconds=total,
        scenes=scenes,
    )


# Strategy for scripts with characters potentially outside the registry
@st.composite
def _script_with_mixed_characters(draw):
    """Generate scripts where some characters may not be in the registry."""
    # Registry characters
    registry_chars = draw(st.lists(
        st.sampled_from(_character_pool),
        min_size=1,
        max_size=4,
        unique=True,
    ))
    # Extra characters not in registry
    extra_chars = ["Unknown_Sage", "Mystery_Warrior", "Phantom_King"]
    all_chars = registry_chars + extra_chars

    char_st = st.sampled_from(all_chars)

    n_scenes = draw(st.integers(min_value=4, max_value=8))
    scenes = []
    for i in range(n_scenes):
        scene = draw(_valid_scene_strategy(
            char_st,
            duration_st=st.integers(min_value=15, max_value=25),
        ))
        scene = Scene(
            scene_number=i + 1,
            duration_seconds=scene.duration_seconds,
            background=scene.background,
            characters=scene.characters,
            action=scene.action,
            narration=scene.narration,
            dialogue=scene.dialogue,
            mood=scene.mood,
            sound_effects=scene.sound_effects,
        )
        scenes.append(scene)

    total = sum(s.duration_seconds for s in scenes)
    registry = {name: f"Description of {name}" for name in registry_chars}

    return (
        EpisodeScript(
            episode_number=draw(st.integers(min_value=1, max_value=9999)),
            kanda=draw(_non_empty_text),
            title=draw(_non_empty_text),
            total_duration_seconds=total,
            scenes=scenes,
        ),
        registry,
    )


# ---------------------------------------------------------------------------
# Build the full character registry for validation tests
# ---------------------------------------------------------------------------

FULL_REGISTRY = {name: f"Description of {name}" for name in _character_pool}


# ---------------------------------------------------------------------------
# Property 3: Total scene durations sum to 110-130 seconds
# **Validates: Requirements 3.2**
# ---------------------------------------------------------------------------


@given(script=_arbitrary_duration_script())
@settings(max_examples=100)
def test_validate_script_duration_constraint(script):
    """Property 3: validate_script accepts scripts with 110-130s total duration
    and rejects scripts outside that range.

    **Validates: Requirements 3.2**
    """
    total = sum(s.duration_seconds for s in script.scenes)
    errors = validate_script(script, FULL_REGISTRY)

    duration_errors = [e for e in errors if "duration" in e.lower()]

    if 110 <= total <= 130:
        assert len(duration_errors) == 0, (
            f"Valid duration {total}s was rejected: {duration_errors}"
        )
    else:
        assert len(duration_errors) > 0, (
            f"Invalid duration {total}s was not rejected"
        )


# ---------------------------------------------------------------------------
# Property 4: Scene count is 4-8 and each scene has non-empty required fields
# **Validates: Requirements 3.3**
# ---------------------------------------------------------------------------


@given(script=_arbitrary_duration_script())
@settings(max_examples=100)
def test_validate_script_scene_count_constraint(script):
    """Property 4 (part A): validate_script accepts scripts with 4-8 scenes
    and rejects scripts outside that range.

    **Validates: Requirements 3.3**
    """
    scene_count = len(script.scenes)
    errors = validate_script(script, FULL_REGISTRY)

    scene_count_errors = [e for e in errors if "scene count" in e.lower()]

    if 4 <= scene_count <= 8:
        assert len(scene_count_errors) == 0, (
            f"Valid scene count {scene_count} was rejected: {scene_count_errors}"
        )
    else:
        assert len(scene_count_errors) > 0, (
            f"Invalid scene count {scene_count} was not rejected"
        )


@given(script=_valid_episode_script_strategy())
@settings(max_examples=100)
def test_validate_script_required_fields_non_empty(script):
    """Property 4 (part B): for valid scripts, each scene has non-empty
    background, characters, action, and narration.

    **Validates: Requirements 3.3**
    """
    errors = validate_script(script, FULL_REGISTRY)

    field_errors = [
        e for e in errors
        if any(f in e.lower() for f in ["background", "characters", "action", "narration"])
        and "character registry" not in e.lower()
    ]

    # All scenes in our valid strategy have non-empty required fields
    assert len(field_errors) == 0, (
        f"Valid script had field errors: {field_errors}"
    )


# ---------------------------------------------------------------------------
# Property 5: All character names exist in the provided character registry
# **Validates: Requirements 3.4**
# ---------------------------------------------------------------------------


@given(data=_script_with_mixed_characters())
@settings(max_examples=100)
def test_validate_script_character_consistency(data):
    """Property 5: validate_script detects characters not in the registry.

    **Validates: Requirements 3.4**
    """
    script, registry = data
    errors = validate_script(script, registry)

    registry_names = set(registry.keys())
    char_errors = [e for e in errors if "character registry" in e.lower()]

    # Collect all character names used in the script
    all_script_chars = set()
    for scene in script.scenes:
        all_script_chars.update(scene.characters)
        for dl in scene.dialogue:
            all_script_chars.add(dl.character)

    unknown_chars = all_script_chars - registry_names

    if unknown_chars:
        assert len(char_errors) > 0, (
            f"Unknown characters {unknown_chars} were not detected"
        )
    else:
        assert len(char_errors) == 0, (
            f"All characters are in registry but got errors: {char_errors}"
        )


# ---------------------------------------------------------------------------
# Task 4.6.4: Segment merging edge case
# ---------------------------------------------------------------------------


def test_short_segment_detected():
    """A segment with fewer words than the threshold is detected as too short."""
    short_segment = StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=1,
        title="Short Segment",
        content="This is a very short segment.",
        characters=["Rama"],
        key_events=["Something happened"],
    )
    assert is_segment_too_short(short_segment) is True


def test_long_segment_not_detected():
    """A segment with enough words is not detected as too short."""
    long_content = " ".join(["word"] * (MIN_SEGMENT_WORD_COUNT + 10))
    long_segment = StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=1,
        title="Long Segment",
        content=long_content,
        characters=["Rama"],
        key_events=["Something happened"],
    )
    assert is_segment_too_short(long_segment) is False


def test_merge_segments_combines_content():
    """Merging two segments combines their content, characters, and events."""
    seg_a = StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=1,
        title="Part A",
        content="Content of part A.",
        characters=["Rama", "Sita"],
        key_events=["Event A1"],
    )
    seg_b = StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=2,
        title="Part B",
        content="Content of part B.",
        characters=["Sita", "Lakshmana"],
        key_events=["Event B1", "Event B2"],
    )

    merged = merge_segments(seg_a, seg_b)

    # Metadata from segment A
    assert merged.kanda_index == 1
    assert merged.kanda_name == "Bala Kanda"
    assert merged.segment_index == 1

    # Combined title
    assert "Part A" in merged.title
    assert "Part B" in merged.title

    # Combined content
    assert "Content of part A." in merged.content
    assert "Content of part B." in merged.content

    # Combined characters (deduplicated, order preserved)
    assert merged.characters == ["Rama", "Sita", "Lakshmana"]

    # Combined events
    assert merged.key_events == ["Event A1", "Event B1", "Event B2"]


def test_merge_segments_short_triggers_merge():
    """A short segment triggers the merge workflow when detected."""
    short_seg = StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=1,
        title="Too Short",
        content="Very brief.",
        characters=["Rama"],
        key_events=["Brief event"],
    )
    next_seg = StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=2,
        title="Next Part",
        content=" ".join(["word"] * 80),
        characters=["Rama", "Hanuman"],
        key_events=["Next event"],
    )

    # Verify the short segment is detected
    assert is_segment_too_short(short_seg) is True

    # Merge and verify the result is no longer too short
    merged = merge_segments(short_seg, next_seg)
    assert is_segment_too_short(merged) is False
    assert "Too Short" in merged.title
    assert "Next Part" in merged.title


# ---------------------------------------------------------------------------
# Character registry loading
# ---------------------------------------------------------------------------


def test_load_character_registry_from_directory():
    """load_character_registry reads character.json files from subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a character directory
        char_dir = os.path.join(tmpdir, "rama")
        os.makedirs(char_dir)
        with open(os.path.join(char_dir, "character.json"), "w") as f:
            json.dump({"name": "Rama", "description": "Prince of Ayodhya"}, f)

        registry = load_character_registry(tmpdir)
        assert "Rama" in registry
        assert registry["Rama"] == "Prince of Ayodhya"


def test_load_character_registry_empty_directory():
    """load_character_registry returns empty dict for empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = load_character_registry(tmpdir)
        assert registry == {}


def test_load_character_registry_nonexistent_directory():
    """load_character_registry returns empty dict for nonexistent directory."""
    registry = load_character_registry("/nonexistent/path")
    assert registry == {}


# ---------------------------------------------------------------------------
# ScriptEngine with mock LLM client
# ---------------------------------------------------------------------------


class MockLLMClient:
    """Mock LLM client that returns a predefined response."""

    def __init__(self, response: str):
        self._response = response

    def chat_completions_create(self, model, messages, temperature):
        return self._response


class FailingLLMClient:
    """Mock LLM client that raises an exception."""

    def chat_completions_create(self, model, messages, temperature):
        raise RuntimeError("API connection failed")


def _make_valid_script_json(
    episode_number=1,
    kanda="Bala Kanda",
    title="Test Episode",
    characters=None,
):
    """Build a valid episode script JSON string."""
    if characters is None:
        characters = ["Rama", "Sita"]

    scenes = []
    durations = [20, 20, 20, 20, 20]  # 5 scenes, 100s — need to adjust
    # Make 5 scenes totaling 120s
    durations = [25, 25, 25, 25, 20]
    for i, dur in enumerate(durations):
        scenes.append({
            "scene_number": i + 1,
            "duration_seconds": dur,
            "background": f"Scene {i+1} background description",
            "characters": characters,
            "action": f"Action in scene {i+1}",
            "narration": f"Narration for scene {i+1}",
            "dialogue": [
                {"character": characters[0], "text": f"Dialogue line {i+1}"}
            ],
            "mood": "devotional",
            "sound_effects": ["temple_bells"],
        })

    data = {
        "episode_number": episode_number,
        "kanda": kanda,
        "title": title,
        "total_duration_seconds": 120,
        "scenes": scenes,
    }
    return json.dumps(data)


def test_script_engine_generate_script_success():
    """ScriptEngine.generate_script returns a valid EpisodeScript."""
    registry = {"Rama": "Prince of Ayodhya", "Sita": "Princess of Mithila"}
    response_json = _make_valid_script_json(characters=["Rama", "Sita"])
    client = MockLLMClient(response_json)
    engine = ScriptEngine(llm_client=client, model="gpt-4")

    segment = StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=1,
        title="Test",
        content="A long story about Rama and Sita in Ayodhya.",
        characters=["Rama", "Sita"],
        key_events=["Event 1"],
    )

    script = engine.generate_script(segment, character_registry=registry)
    assert script.episode_number == 1
    assert script.kanda == "Bala Kanda"
    assert len(script.scenes) == 5


def test_script_engine_llm_failure_raises_error():
    """ScriptEngine raises ScriptEngineError when LLM call fails."""
    client = FailingLLMClient()
    engine = ScriptEngine(llm_client=client, model="gpt-4")

    segment = StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=1,
        title="Test",
        content="Some content.",
        characters=["Rama"],
        key_events=["Event"],
    )

    with pytest.raises(ScriptEngineError, match="LLM API call failed"):
        engine.generate_script(segment, character_registry={"Rama": ""})


def test_script_engine_invalid_json_raises_error():
    """ScriptEngine raises ScriptEngineError when LLM returns invalid JSON."""
    client = MockLLMClient("This is not JSON at all")
    engine = ScriptEngine(llm_client=client, model="gpt-4")

    segment = StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=1,
        title="Test",
        content="Some content.",
        characters=["Rama"],
        key_events=["Event"],
    )

    with pytest.raises(ScriptEngineError, match="Failed to parse"):
        engine.generate_script(segment, character_registry={"Rama": ""})


def test_script_engine_validation_failure_raises_error():
    """ScriptEngine raises ScriptValidationError when script fails validation."""
    # Create a script with only 2 scenes (below minimum of 4)
    data = {
        "episode_number": 1,
        "kanda": "Bala Kanda",
        "title": "Test",
        "total_duration_seconds": 40,
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 20,
                "background": "bg",
                "characters": ["Rama"],
                "action": "action",
                "narration": "narration",
                "dialogue": [],
                "mood": "calm",
                "sound_effects": [],
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "background": "bg",
                "characters": ["Rama"],
                "action": "action",
                "narration": "narration",
                "dialogue": [],
                "mood": "calm",
                "sound_effects": [],
            },
        ],
    }
    client = MockLLMClient(json.dumps(data))
    engine = ScriptEngine(llm_client=client, model="gpt-4")

    segment = StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=1,
        title="Test",
        content="Some content.",
        characters=["Rama"],
        key_events=["Event"],
    )

    with pytest.raises(ScriptValidationError, match="validation failed"):
        engine.generate_script(segment, character_registry={"Rama": ""})


def test_script_engine_strips_markdown_fences():
    """ScriptEngine strips markdown code fences from LLM response."""
    registry = {"Rama": "Prince", "Sita": "Princess"}
    raw_json = _make_valid_script_json(characters=["Rama", "Sita"])
    wrapped = f"```json\n{raw_json}\n```"
    client = MockLLMClient(wrapped)
    engine = ScriptEngine(llm_client=client, model="gpt-4")

    segment = StorySegment(
        kanda_index=1,
        kanda_name="Bala Kanda",
        chapter=1,
        segment_index=1,
        title="Test",
        content="Story content here.",
        characters=["Rama", "Sita"],
        key_events=["Event"],
    )

    script = engine.generate_script(segment, character_registry=registry)
    assert script.episode_number == 1
