"""Visual Variety — Adds composition directives to image generation prompts.

Varies the visual style based on a scene's role in the explainer structure:
- Hook scenes: Dramatic close-ups, intense mood lighting
- Context scenes: Wide establishing shots showing setting
- Revelation scenes: Symbolic/philosophical imagery
- CTA scenes: Character-focused with emotional expression

This prevents all keyframes from looking identical and makes the
video more visually engaging.
"""

from typing import List


# Composition prefixes based on scene role in the explainer structure
SCENE_COMPOSITION_PREFIXES = {
    "hook": (
        "extreme close-up dramatic portrait, intense emotional expression, "
        "cinematic lighting with deep shadows, golden rim light, "
        "shallow depth of field, high contrast"
    ),
    "context_establishing": (
        "wide establishing shot, epic landscape view, "
        "grand scale showing full environment, "
        "atmospheric perspective, volumetric light rays"
    ),
    "context_action": (
        "dynamic mid-shot composition, characters in action, "
        "diagonal lines creating movement, motion blur elements, "
        "dramatic angle from below"
    ),
    "revelation": (
        "symbolic composition, centered subject with radial light, "
        "divine glow emanating outward, ethereal atmosphere, "
        "sacred geometry in background, spiritual illumination"
    ),
    "cta_engagement": (
        "warm inviting close-up, direct eye contact with viewer, "
        "gentle golden light, soft focus background, "
        "emotionally open expression"
    ),
}

# Mood-specific lighting and color palettes
MOOD_VISUAL_STYLE = {
    "devotional": "warm golden light, temple lamp glow, saffron and gold color palette, sacred atmosphere",
    "dramatic": "high contrast chiaroscuro lighting, deep shadows, storm clouds, intense reds and blacks",
    "serene": "soft diffused light, pastel dawn colors, peaceful blue-green palette, gentle mist",
    "mysterious": "moonlit scene, blue-purple shadows, fog, hidden details in darkness",
    "triumphant": "blazing golden sunlight, heroic backlit silhouette, radiant warm colors",
    "melancholy": "overcast grey-blue light, muted desaturated colors, rain or twilight",
    "intense": "fiery orange-red lighting, dramatic shadows, motion and energy",
    "hopeful": "sunrise golden hour, warm emerging light, fresh greens and golds",
    "battle": "chaotic red-orange firelight, dust and debris, dynamic motion blur",
    "divine": "ethereal white-gold light from above, celestial glow, transcendent atmosphere",
}


def get_scene_role(scene_number: int, total_scenes: int) -> str:
    """Determine a scene's compositional role based on its position.

    Args:
        scene_number: 1-indexed scene number.
        total_scenes: Total scenes in the episode.

    Returns:
        Role key for composition prefix lookup.
    """
    if scene_number == 1:
        return "hook"
    elif scene_number == total_scenes:
        return "cta_engagement"
    elif scene_number == total_scenes - 1:
        return "revelation"
    elif scene_number == 2:
        return "context_establishing"
    else:
        return "context_action"


def build_enhanced_image_prompt(
    base_prompt: str,
    scene_number: int,
    total_scenes: int,
    mood: str,
    characters: List[str],
) -> str:
    """Build an enhanced image generation prompt with visual variety.

    Combines the base scene description with composition directives and
    mood-specific styling to create more varied and cinematic keyframes.

    Args:
        base_prompt: The original scene background/description text.
        scene_number: 1-indexed scene number.
        total_scenes: Total scenes in the episode.
        mood: Scene mood tag.
        characters: Character names in the scene.

    Returns:
        Enhanced prompt string for the image generator.
    """
    role = get_scene_role(scene_number, total_scenes)
    composition = SCENE_COMPOSITION_PREFIXES.get(role, "")
    mood_style = MOOD_VISUAL_STYLE.get(mood.lower(), "warm atmospheric lighting")

    # Build character focus hint
    char_hint = ""
    if characters and role in ("hook", "cta_engagement", "revelation"):
        char_hint = f", featuring {characters[0]} prominently"

    # Assemble the enhanced prompt
    parts = [
        "Indian traditional art style, intricate details, ornate patterns",
        composition,
        base_prompt,
        mood_style,
        char_hint,
        "masterful composition, highly detailed, 8K quality",
    ]

    return ", ".join(p for p in parts if p)
