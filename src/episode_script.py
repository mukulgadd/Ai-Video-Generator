"""Episode Script model, parser, and serializer for the Ramayan Video Generator.

Provides the EpisodeScript data model using dataclasses, JSON schema
validation, and round-trip serialization/deserialization of episode scripts.

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
"""

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

import jsonschema


class EpisodeScriptError(Exception):
    """Raised when an episode script is invalid or cannot be parsed.

    Attributes:
        message: A descriptive error message identifying the issue.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


@dataclass
class DialogueLine:
    """A single line of dialogue spoken by a character."""

    character: str
    text: str


@dataclass
class Scene:
    """A single scene within an episode script."""

    scene_number: int
    duration_seconds: int
    background: str
    characters: List[str]
    action: str
    narration: str
    dialogue: List[DialogueLine]
    mood: str
    sound_effects: List[str]
    narration_en: str = ""  # English translation for subtitles


@dataclass
class EpisodeScript:
    """A complete episode script for a Ramayan video episode.

    The explainer format adds metadata fields that drive engagement:
    - hook: The scroll-stopping opening line (used in branding/thumbnails)
    - angle: Content angle type for variety tracking
    - revelation: Core insight the viewer gains (used in descriptions/SEO)
    - engagement_cta: Comment-triggering question at the end
    """

    episode_number: int
    kanda: str
    title: str
    total_duration_seconds: int
    scenes: List[Scene]
    hook: str = ""
    angle: str = ""
    revelation: str = ""
    engagement_cta: str = ""


# --- JSON Schema Definition (Task 3.2) ---

EPISODE_SCRIPT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "EpisodeScript",
    "description": "Schema for a Ramayan Video Generator episode script.",
    "type": "object",
    "required": [
        "episode_number",
        "kanda",
        "title",
        "total_duration_seconds",
        "hook",
        "angle",
        "revelation",
        "engagement_cta",
        "scenes",
    ],
    "additionalProperties": False,
    "properties": {
        "episode_number": {
            "type": "integer",
            "minimum": 1,
            "description": "Sequential episode number.",
        },
        "kanda": {
            "type": "string",
            "minLength": 1,
            "description": "Name of the Kanda (book) this episode belongs to.",
        },
        "title": {
            "type": "string",
            "minLength": 1,
            "description": "Engaging title using explainer patterns (e.g., 'The REAL reason...').",
        },
        "total_duration_seconds": {
            "type": "integer",
            "minimum": 1,
            "description": "Total duration of the episode in seconds.",
        },
        "hook": {
            "type": "string",
            "minLength": 1,
            "description": "The scroll-stopping opening line in English (used for thumbnails/branding).",
        },
        "angle": {
            "type": "string",
            "enum": [
                "hidden_meaning",
                "why",
                "character_study",
                "life_lesson",
                "unknown_facts",
                "what_if",
                "debate"
            ],
            "description": "Content angle type for this episode.",
        },
        "revelation": {
            "type": "string",
            "minLength": 1,
            "description": "The core insight or hidden truth the viewer gains from this episode.",
        },
        "engagement_cta": {
            "type": "string",
            "minLength": 1,
            "description": "Comment-triggering question asked at the end of the video.",
        },
        "scenes": {
            "type": "array",
            "minItems": 1,
            "description": "List of scenes in the episode.",
            "items": {
                "type": "object",
                "required": [
                    "scene_number",
                    "duration_seconds",
                    "background",
                    "characters",
                    "action",
                    "narration",
                    "dialogue",
                    "mood",
                    "sound_effects",
                ],
                "additionalProperties": True,
                "properties": {
                    "scene_number": {
                        "type": "integer",
                        "minimum": 1,
                    },
                    "duration_seconds": {
                        "type": "integer",
                        "minimum": 1,
                    },
                    "background": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "characters": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "action": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "narration": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "narration_en": {
                        "type": "string",
                    },
                    "dialogue": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["character", "text"],
                            "additionalProperties": False,
                            "properties": {
                                "character": {
                                    "type": "string",
                                    "minLength": 1,
                                },
                                "text": {
                                    "type": "string",
                                    "minLength": 1,
                                },
                            },
                        },
                    },
                    "mood": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "sound_effects": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
    },
}


# --- Serialization (Task 3.3) ---


def serialize(script: EpisodeScript) -> str:
    """Convert an EpisodeScript to a compact JSON string.

    Args:
        script: The EpisodeScript object to serialize.

    Returns:
        A compact JSON string representation of the script.
    """
    return json.dumps(_episode_script_to_dict(script), separators=(",", ":"))


# --- Pretty Print (Task 3.4) ---


def pretty_print(script: EpisodeScript) -> str:
    """Convert an EpisodeScript to a formatted (pretty-printed) JSON string.

    Args:
        script: The EpisodeScript object to format.

    Returns:
        A formatted JSON string with 2-space indentation.
    """
    return json.dumps(_episode_script_to_dict(script), indent=2)


# --- Parse (Task 3.5) ---


def parse(json_str: str) -> EpisodeScript:
    """Parse a JSON string into an EpisodeScript with schema validation.

    Args:
        json_str: A JSON string representing an episode script.

    Returns:
        A validated EpisodeScript object.

    Raises:
        EpisodeScriptError: If the JSON is malformed or fails schema validation,
            with a descriptive error message identifying the issue.
    """
    # Step 1: Parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise EpisodeScriptError(f"Malformed JSON: {e}")

    # Step 2: Validate against schema
    try:
        jsonschema.validate(instance=data, schema=EPISODE_SCRIPT_SCHEMA)
    except jsonschema.ValidationError as e:
        path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        raise EpisodeScriptError(
            f"Schema validation error at '{path}': {e.message}"
        )

    # Step 3: Build EpisodeScript from validated data
    return _dict_to_episode_script(data)


# --- Internal Helpers ---


def _episode_script_to_dict(script: EpisodeScript) -> Dict[str, Any]:
    """Convert an EpisodeScript to a plain dictionary."""
    return {
        "episode_number": script.episode_number,
        "kanda": script.kanda,
        "title": script.title,
        "total_duration_seconds": script.total_duration_seconds,
        "hook": script.hook,
        "angle": script.angle,
        "revelation": script.revelation,
        "engagement_cta": script.engagement_cta,
        "scenes": [
            {
                "scene_number": scene.scene_number,
                "duration_seconds": scene.duration_seconds,
                "background": scene.background,
                "characters": list(scene.characters),
                "action": scene.action,
                "narration": scene.narration,
                "narration_en": scene.narration_en,
                "dialogue": [
                    {"character": dl.character, "text": dl.text}
                    for dl in scene.dialogue
                ],
                "mood": scene.mood,
                "sound_effects": list(scene.sound_effects),
            }
            for scene in script.scenes
        ],
    }


def _dict_to_episode_script(data: Dict[str, Any]) -> EpisodeScript:
    """Convert a validated dictionary to an EpisodeScript object."""
    scenes = []
    for scene_data in data["scenes"]:
        dialogue = [
            DialogueLine(character=dl["character"], text=dl["text"])
            for dl in scene_data["dialogue"]
        ]
        scenes.append(
            Scene(
                scene_number=scene_data["scene_number"],
                duration_seconds=scene_data["duration_seconds"],
                background=scene_data["background"],
                characters=list(scene_data["characters"]),
                action=scene_data["action"],
                narration=scene_data["narration"],
                dialogue=dialogue,
                mood=scene_data["mood"],
                sound_effects=list(scene_data["sound_effects"]),
                narration_en=scene_data.get("narration_en", ""),
            )
        )
    return EpisodeScript(
        episode_number=data["episode_number"],
        kanda=data["kanda"],
        title=data["title"],
        total_duration_seconds=data["total_duration_seconds"],
        scenes=scenes,
        hook=data.get("hook", ""),
        angle=data.get("angle", ""),
        revelation=data.get("revelation", ""),
        engagement_cta=data.get("engagement_cta", ""),
    )
