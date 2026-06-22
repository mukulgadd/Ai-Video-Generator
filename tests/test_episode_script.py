"""Tests for the episode_script module.

Tests verify:
- Property 6: Round-trip serialization preserves all fields
- Property 7: Invalid JSON produces descriptive errors
- Serialized output conforms to the defined JSON schema
"""

import json

import jsonschema
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.episode_script import (
    DialogueLine,
    EpisodeScript,
    EpisodeScriptError,
    Scene,
    EPISODE_SCRIPT_SCHEMA,
    parse,
    pretty_print,
    serialize,
)


# ---------------------------------------------------------------------------
# Hypothesis strategies for generating valid EpisodeScript objects
# ---------------------------------------------------------------------------

_non_empty_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=60,
).filter(lambda s: s.strip() != "")

_character_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() != "")


def _dialogue_line_strategy():
    return st.builds(
        DialogueLine,
        character=_character_name,
        text=_non_empty_text,
    )


def _scene_strategy():
    return st.builds(
        Scene,
        scene_number=st.integers(min_value=1, max_value=100),
        duration_seconds=st.integers(min_value=1, max_value=300),
        background=_non_empty_text,
        characters=st.lists(_character_name, min_size=0, max_size=5),
        action=_non_empty_text,
        narration=_non_empty_text,
        dialogue=st.lists(_dialogue_line_strategy(), min_size=0, max_size=4),
        mood=_non_empty_text,
        sound_effects=st.lists(_non_empty_text, min_size=0, max_size=5),
    )


def _episode_script_strategy():
    return st.builds(
        EpisodeScript,
        episode_number=st.integers(min_value=1, max_value=9999),
        kanda=_non_empty_text,
        title=_non_empty_text,
        total_duration_seconds=st.integers(min_value=1, max_value=600),
        scenes=st.lists(_scene_strategy(), min_size=1, max_size=8),
    )


# ---------------------------------------------------------------------------
# Property 6: Round-trip preserves all fields
# **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
# ---------------------------------------------------------------------------


@given(script=_episode_script_strategy())
@settings(max_examples=100)
def test_round_trip_pretty_print_preserves_all_fields(script):
    """Property 6: For any valid EpisodeScript, parse(pretty_print(script)) == script.

    **Validates: Requirements 8.4**
    """
    json_str = pretty_print(script)
    restored = parse(json_str)

    assert restored.episode_number == script.episode_number
    assert restored.kanda == script.kanda
    assert restored.title == script.title
    assert restored.total_duration_seconds == script.total_duration_seconds
    assert len(restored.scenes) == len(script.scenes)

    for orig_scene, rest_scene in zip(script.scenes, restored.scenes):
        assert rest_scene.scene_number == orig_scene.scene_number
        assert rest_scene.duration_seconds == orig_scene.duration_seconds
        assert rest_scene.background == orig_scene.background
        assert rest_scene.characters == orig_scene.characters
        assert rest_scene.action == orig_scene.action
        assert rest_scene.narration == orig_scene.narration
        assert rest_scene.mood == orig_scene.mood
        assert rest_scene.sound_effects == orig_scene.sound_effects
        assert len(rest_scene.dialogue) == len(orig_scene.dialogue)
        for orig_dl, rest_dl in zip(orig_scene.dialogue, rest_scene.dialogue):
            assert rest_dl.character == orig_dl.character
            assert rest_dl.text == orig_dl.text


@given(script=_episode_script_strategy())
@settings(max_examples=50)
def test_round_trip_serialize_preserves_all_fields(script):
    """Round-trip via compact serialize also preserves all fields.

    **Validates: Requirements 8.1, 8.2**
    """
    json_str = serialize(script)
    restored = parse(json_str)

    assert restored.episode_number == script.episode_number
    assert restored.kanda == script.kanda
    assert restored.title == script.title
    assert restored.total_duration_seconds == script.total_duration_seconds
    assert len(restored.scenes) == len(script.scenes)


# ---------------------------------------------------------------------------
# Property 7: Invalid JSON produces descriptive errors
# **Validates: Requirements 8.5**
# ---------------------------------------------------------------------------

# Strategy: generate completely random text that is unlikely to be valid JSON
_random_text = st.text(min_size=1, max_size=200)

# Strategy: generate valid JSON but with schema violations
_wrong_type_episode_number = st.one_of(
    st.just("not_a_number"),
    st.just(-5),
    st.just(0),
    st.just(3.14),
    st.just(None),
    st.just(True),
)

_wrong_type_kanda = st.one_of(
    st.just(123),
    st.just(None),
    st.just(True),
    st.just(""),
)

_wrong_type_scenes = st.one_of(
    st.just("not_an_array"),
    st.just(123),
    st.just(None),
    st.just([]),  # empty array violates minItems: 1
)


@given(text=_random_text)
@settings(max_examples=50)
def test_malformed_json_returns_descriptive_error(text):
    """Property 7 (part A): Malformed JSON strings produce EpisodeScriptError.

    **Validates: Requirements 8.5**
    """
    # Filter out strings that happen to be valid JSON matching our schema
    try:
        data = json.loads(text)
        # If it parses as JSON, skip if it could be a valid episode script
        if isinstance(data, dict) and "episode_number" in data:
            assume(False)
    except json.JSONDecodeError:
        pass  # This is what we want — malformed JSON

    with pytest.raises(EpisodeScriptError) as exc_info:
        parse(text)

    # Error message should be descriptive (non-empty)
    assert len(exc_info.value.message) > 0


@given(bad_episode_number=_wrong_type_episode_number)
@settings(max_examples=30)
def test_schema_violation_episode_number(bad_episode_number):
    """Property 7 (part B): Wrong type for episode_number raises descriptive error.

    **Validates: Requirements 8.5**
    """
    data = {
        "episode_number": bad_episode_number,
        "kanda": "Bala Kanda",
        "title": "Test Episode",
        "total_duration_seconds": 120,
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 20,
                "background": "A palace",
                "characters": ["Rama"],
                "action": "Walking",
                "narration": "Narration text",
                "dialogue": [],
                "mood": "calm",
                "sound_effects": [],
            }
        ],
    }
    with pytest.raises(EpisodeScriptError) as exc_info:
        parse(json.dumps(data))
    assert len(exc_info.value.message) > 0


@given(bad_kanda=_wrong_type_kanda)
@settings(max_examples=20)
def test_schema_violation_kanda(bad_kanda):
    """Property 7 (part C): Wrong type for kanda raises descriptive error.

    **Validates: Requirements 8.5**
    """
    data = {
        "episode_number": 1,
        "kanda": bad_kanda,
        "title": "Test Episode",
        "total_duration_seconds": 120,
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 20,
                "background": "A palace",
                "characters": ["Rama"],
                "action": "Walking",
                "narration": "Narration text",
                "dialogue": [],
                "mood": "calm",
                "sound_effects": [],
            }
        ],
    }
    with pytest.raises(EpisodeScriptError) as exc_info:
        parse(json.dumps(data))
    assert len(exc_info.value.message) > 0


@given(bad_scenes=_wrong_type_scenes)
@settings(max_examples=20)
def test_schema_violation_scenes(bad_scenes):
    """Property 7 (part D): Wrong type for scenes raises descriptive error.

    **Validates: Requirements 8.5**
    """
    data = {
        "episode_number": 1,
        "kanda": "Bala Kanda",
        "title": "Test Episode",
        "total_duration_seconds": 120,
        "scenes": bad_scenes,
    }
    with pytest.raises(EpisodeScriptError) as exc_info:
        parse(json.dumps(data))
    assert len(exc_info.value.message) > 0


def test_missing_required_field_raises_error():
    """Schema violation: missing required field produces descriptive error.

    **Validates: Requirements 8.5**
    """
    # Missing 'title' field
    data = {
        "episode_number": 1,
        "kanda": "Bala Kanda",
        "total_duration_seconds": 120,
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 20,
                "background": "A palace",
                "characters": [],
                "action": "Walking",
                "narration": "Narration text",
                "dialogue": [],
                "mood": "calm",
                "sound_effects": [],
            }
        ],
    }
    with pytest.raises(EpisodeScriptError) as exc_info:
        parse(json.dumps(data))
    assert "title" in exc_info.value.message.lower() or "required" in exc_info.value.message.lower()


def test_extra_field_raises_error():
    """Schema violation: additional properties not allowed.

    **Validates: Requirements 8.5**
    """
    data = {
        "episode_number": 1,
        "kanda": "Bala Kanda",
        "title": "Test",
        "total_duration_seconds": 120,
        "unexpected_field": "oops",
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 20,
                "background": "A palace",
                "characters": [],
                "action": "Walking",
                "narration": "Narration text",
                "dialogue": [],
                "mood": "calm",
                "sound_effects": [],
            }
        ],
    }
    with pytest.raises(EpisodeScriptError) as exc_info:
        parse(json.dumps(data))
    assert len(exc_info.value.message) > 0


# ---------------------------------------------------------------------------
# Task 3.6.3: Serialized output conforms to the defined schema
# ---------------------------------------------------------------------------


@given(script=_episode_script_strategy())
@settings(max_examples=50)
def test_serialized_output_conforms_to_schema(script):
    """Serialized output is valid JSON conforming to the defined schema.

    **Validates: Requirements 8.1**
    """
    json_str = serialize(script)
    data = json.loads(json_str)
    # Should not raise
    jsonschema.validate(instance=data, schema=EPISODE_SCRIPT_SCHEMA)


@given(script=_episode_script_strategy())
@settings(max_examples=50)
def test_pretty_printed_output_conforms_to_schema(script):
    """Pretty-printed output is valid JSON conforming to the defined schema.

    **Validates: Requirements 8.3**
    """
    json_str = pretty_print(script)
    data = json.loads(json_str)
    # Should not raise
    jsonschema.validate(instance=data, schema=EPISODE_SCRIPT_SCHEMA)
