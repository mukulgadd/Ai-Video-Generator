"""Property-based tests for the config_loader module.

Tests verify:
- Property 16: Missing optional keys resolve to documented defaults
- Property 17: Invalid values raise ConfigError naming specific fields
"""

import os
import tempfile

import pytest
import yaml
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.config_loader import (
    Config,
    ConfigError,
    AnimationConfig,
    AudioConfig,
    DistributionConfig,
    NarrationConfig,
    NotificationsConfig,
    OutputConfig,
    PipelineConfig,
    PlatformConfig,
    StorageConfig,
    load_config,
)


# --- Helpers ---

def _write_yaml(data):
    """Write data to a temporary YAML file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        yaml.dump(data, f)
    return path


# Full default config as a plain dict (matches documented defaults)
FULL_DEFAULT_CONFIG = {
    "pipeline": {
        "schedule_time": "06:00",
        "target_duration_seconds": 120,
        "retry_attempts": 3,
    },
    "animation": {
        "style_reference": "indian_traditional_art",
        "resolution": [1080, 1920],
        "fps": 24,
        "model": "stable-diffusion-xl",
        "lora_path": "./models/indian_art_lora.safetensors",
    },
    "narration": {
        "default_locale": "hi",
        "narrator_voice": "narrator_v1",
        "tts_provider": "coqui",
        "character_voices": {
            "Rama": "voice_rama_01",
            "Sita": "voice_sita_01",
            "Hanuman": "voice_hanuman_01",
            "Ravana": "voice_ravana_01",
        },
    },
    "audio": {
        "music_library_path": "./assets/music/",
        "sfx_library_path": "./assets/sfx/",
        "narration_boost_db": 6,
        "crossfade_seconds": 0.75,
    },
    "output": {
        "format": "mp4",
        "video_codec": "h264",
        "audio_codec": "aac",
    },
    "storage": {
        "provider": "s3",
        "bucket": "ramayan-videos",
        "path_prefix": "episodes/",
    },
    "distribution": {
        "youtube": {
            "enabled": False,
            "credentials_path": "./credentials/youtube.json",
        },
        "instagram": {
            "enabled": False,
            "credentials_path": "./credentials/instagram.json",
        },
    },
    "notifications": {
        "provider": "email",
        "recipients": ["admin@example.com"],
    },
}

# All top-level section keys
TOP_LEVEL_KEYS = list(FULL_DEFAULT_CONFIG.keys())

# Mapping of section -> list of optional sub-keys
SECTION_KEYS = {
    section: list(fields.keys()) for section, fields in FULL_DEFAULT_CONFIG.items()
}


def _get_config_value(config: Config, section: str, key: str):
    """Get a value from a Config object by section and key name."""
    section_obj = getattr(config, section)
    if section == "distribution":
        # distribution has nested platform configs
        if key == "youtube":
            return {
                "enabled": section_obj.youtube.enabled,
                "credentials_path": section_obj.youtube.credentials_path,
            }
        elif key == "instagram":
            return {
                "enabled": section_obj.instagram.enabled,
                "credentials_path": section_obj.instagram.credentials_path,
            }
    return getattr(section_obj, key)


# --- Property 16: Missing optional keys resolve to documented defaults ---
# **Validates: Requirements 10.3**


# Strategy: pick a random subset of top-level sections to omit
@given(sections_to_omit=st.sets(st.sampled_from(TOP_LEVEL_KEYS)))
@settings(max_examples=50)
def test_missing_top_level_sections_get_defaults(sections_to_omit):
    """Property 16 (part A): Omitting entire top-level sections still produces
    a complete config with all documented defaults for those sections.

    **Validates: Requirements 10.3**
    """
    data = {k: v for k, v in FULL_DEFAULT_CONFIG.items() if k not in sections_to_omit}
    path = _write_yaml(data)
    try:
        config = load_config(path)

        # Every section must exist on the config
        for section in TOP_LEVEL_KEYS:
            section_obj = getattr(config, section)
            assert section_obj is not None, f"Section '{section}' is None"

            # Every key in the section must match the documented default
            for key in SECTION_KEYS[section]:
                actual = _get_config_value(config, section, key)
                expected = FULL_DEFAULT_CONFIG[section][key]
                assert actual == expected, (
                    f"{section}.{key}: expected {expected!r}, got {actual!r}"
                )
    finally:
        os.unlink(path)


# Strategy: for each section, pick a random subset of keys to omit
@given(
    section=st.sampled_from(TOP_LEVEL_KEYS),
    data=st.data(),
)
@settings(max_examples=80)
def test_missing_sub_keys_get_defaults(section, data):
    """Property 16 (part B): Omitting individual keys within a section still
    produces a complete config with documented defaults for those keys.

    **Validates: Requirements 10.3**
    """
    keys = SECTION_KEYS[section]
    keys_to_omit = data.draw(
        st.sets(st.sampled_from(keys), min_size=1, max_size=len(keys))
    )

    # Build config with the section present but some keys removed
    import copy
    full = copy.deepcopy(FULL_DEFAULT_CONFIG)
    for key in keys_to_omit:
        del full[section][key]

    path = _write_yaml(full)
    try:
        config = load_config(path)

        # All keys (including omitted ones) should have their default values
        for key in keys_to_omit:
            actual = _get_config_value(config, section, key)
            expected = FULL_DEFAULT_CONFIG[section][key]
            assert actual == expected, (
                f"{section}.{key}: expected default {expected!r}, got {actual!r}"
            )
    finally:
        os.unlink(path)


# --- Property 17: Invalid values raise ConfigError naming specific fields ---
# **Validates: Requirements 10.4**

# Strategies for generating invalid values by field type
INVALID_VALUE_GENERATORS = {
    # pipeline
    "pipeline.schedule_time": st.one_of(
        st.integers(),
        st.just("25:00"),
        st.just("12:99"),
        st.just("not-a-time"),
        st.lists(st.integers(), min_size=1, max_size=2),
    ),
    "pipeline.target_duration_seconds": st.one_of(
        st.just("not_int"),
        st.just(-10),
        st.just(0),
        st.just(True),
        st.lists(st.integers(), min_size=1, max_size=1),
    ),
    "pipeline.retry_attempts": st.one_of(
        st.just("not_int"),
        st.just(-1),
        st.just(True),
        st.floats(min_value=0.1, max_value=10.0),
    ),
    # animation
    "animation.fps": st.one_of(
        st.just("not_int"),
        st.just(-5),
        st.just(0),
        st.just(True),
    ),
    "animation.resolution": st.one_of(
        st.just("not_list"),
        st.just([1080]),
        st.just([1080, -1920]),
        st.just([1080, 1920, 100]),
        st.just([True, 1920]),
    ),
    "animation.style_reference": st.one_of(
        st.integers(),
        st.lists(st.text(), min_size=1, max_size=2),
    ),
    # narration
    "narration.character_voices": st.one_of(
        st.just("not_dict"),
        st.just(123),
        st.just([1, 2, 3]),
    ),
    "narration.default_locale": st.one_of(
        st.integers(),
        st.just(True),
    ),
    # audio
    "audio.crossfade_seconds": st.one_of(
        st.just("not_number"),
        st.just(-1.0),
        st.just(True),
    ),
    "audio.narration_boost_db": st.one_of(
        st.just("not_number"),
        st.just(True),
        st.lists(st.integers(), min_size=1, max_size=1),
    ),
    # output
    "output.format": st.one_of(st.integers(), st.just(True)),
    # storage
    "storage.provider": st.one_of(st.integers(), st.just(True)),
    # distribution
    "distribution.youtube.enabled": st.one_of(
        st.just("not_bool"),
        st.integers(),
    ),
    # notifications
    "notifications.recipients": st.one_of(
        st.just("not_list"),
        st.just(123),
        st.just([1, 2, 3]),
    ),
}


@given(
    field_path=st.sampled_from(list(INVALID_VALUE_GENERATORS.keys())),
    data=st.data(),
)
@settings(max_examples=100)
def test_invalid_values_raise_config_error_with_field_names(field_path, data):
    """Property 17: For any configuration with invalid values (wrong types,
    out-of-range), ConfigError is raised naming the specific invalid fields.

    **Validates: Requirements 10.4**
    """
    import copy

    invalid_value = data.draw(INVALID_VALUE_GENERATORS[field_path])

    full = copy.deepcopy(FULL_DEFAULT_CONFIG)

    # Set the invalid value at the right nesting level
    parts = field_path.split(".")
    target = full
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = invalid_value

    path = _write_yaml(full)
    try:
        with pytest.raises(ConfigError) as exc_info:
            load_config(path)

        error = exc_info.value
        assert len(error.invalid_fields) > 0, (
            f"ConfigError raised but invalid_fields is empty for {field_path}"
        )
        # The specific field should be named in the error
        assert field_path in error.invalid_fields, (
            f"Expected '{field_path}' in invalid_fields, "
            f"got {error.invalid_fields}"
        )
    finally:
        os.unlink(path)
