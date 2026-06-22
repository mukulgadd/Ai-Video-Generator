"""SFX Mood Mapper — Maps scene moods to appropriate ambient sound effects.

Provides default ambient sounds for each mood type so scenes always have
appropriate atmosphere, even when the LLM doesn't specify explicit SFX.

Sound effects are looked up by name in the SFX library.
If a clip isn't found, it's silently skipped (no crash).
"""

from typing import List

# Maps mood tags to default ambient SFX names that should play during the scene.
# These create atmosphere without competing with narration.
MOOD_AMBIENT_MAP = {
    "devotional": ["temple_bells_soft", "incense_wind"],
    "dramatic": ["thunder_distant", "wind_howl"],
    "serene": ["birds_morning", "river_gentle"],
    "mysterious": ["wind_eerie", "owl_distant"],
    "triumphant": ["drums_victory", "crowd_cheering"],
    "melancholy": ["wind_lonely", "rain_soft"],
    "intense": ["drums_war", "fire_crackling"],
    "hopeful": ["birds_morning", "flute_distant"],
    "battle": ["swords_clash", "drums_war", "arrows_flying"],
    "celebratory": ["drums_festive", "crowd_cheering", "bells_joyful"],
    "festive": ["drums_festive", "crowd_cheering", "bells_joyful"],
    "romantic": ["flute_distant", "birds_morning"],
    "sorrowful": ["wind_lonely", "rain_soft"],
    "divine": ["om_chant", "divine_light"],
    "heroic": ["conch_shell", "drums_war"],
}

# SFX that match commonly requested effects in the script's sound_effects field
EXPLICIT_SFX_ALIASES = {
    "temple_bells": "temple_bells_soft",
    "fire_crackling": "fire_crackling",
    "crowd_cheering": "crowd_cheering",
    "river_flowing": "river_gentle",
    "birds_chirping": "birds_morning",
    "thunder": "thunder_distant",
    "wind": "wind_howl",
    "rain": "rain_soft",
    "battle_sounds": "swords_clash",
    "conch_shell": "conch_shell",
    "drums": "drums_war",
    "horses_galloping": "horses_gallop",
    "arrows": "arrows_flying",
    "divine_sound": "divine_light",
    "ocean_waves": "ocean_waves",
}


def get_ambient_sfx_for_mood(mood: str) -> List[str]:
    """Get default ambient SFX names for a given mood.

    Args:
        mood: The scene's mood tag (e.g., 'devotional', 'dramatic').

    Returns:
        List of SFX clip names that provide appropriate ambience.
    """
    mood_lower = mood.lower().strip()
    return MOOD_AMBIENT_MAP.get(mood_lower, ["wind_gentle"])


def resolve_sfx_name(effect_name: str) -> str:
    """Resolve a script-specified SFX name to a library clip name.

    Handles aliases so the LLM can use natural names like 'temple_bells'
    which map to actual clip names in the library.

    Args:
        effect_name: The SFX name from the script's sound_effects field.

    Returns:
        The resolved clip name for library lookup.
    """
    return EXPLICIT_SFX_ALIASES.get(effect_name.lower(), effect_name.lower())


def get_all_sfx_for_scene(mood: str, explicit_effects: List[str]) -> List[str]:
    """Get the complete SFX list for a scene: ambient + explicit effects.

    Combines mood-based ambient sounds with any explicitly requested effects,
    deduplicating and limiting to avoid audio clutter.

    Args:
        mood: The scene's mood tag.
        explicit_effects: SFX names from the script's sound_effects field.

    Returns:
        Deduplicated list of SFX clip names (max 3 to avoid clutter).
    """
    # Start with explicit effects (these take priority)
    resolved = [resolve_sfx_name(e) for e in explicit_effects]

    # Add ambient defaults that aren't already covered
    ambient = get_ambient_sfx_for_mood(mood)
    for sfx in ambient:
        if sfx not in resolved:
            resolved.append(sfx)

    # Limit to 3 to prevent audio clutter over narration
    return resolved[:3]
