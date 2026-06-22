"""Update the story segment schema with new analysis fields."""
import json

schema = {
    "title": "Ramayan Story Segment",
    "description": "Schema for a single story segment of the Ramayan epic, enriched with analysis fields for the explainer video format.",
    "type": "object",
    "required": [
        "kanda_index", "kanda_name", "chapter", "segment_index",
        "title", "content", "characters", "key_events"
    ],
    "properties": {
        "kanda_index": {"type": "integer", "minimum": 1, "maximum": 7, "description": "Index of the Kanda (1-7)"},
        "kanda_name": {
            "type": "string",
            "enum": ["Bala Kanda", "Ayodhya Kanda", "Aranya Kanda", "Kishkindha Kanda", "Sundara Kanda", "Yuddha Kanda", "Uttara Kanda"],
            "description": "Name of the Kanda"
        },
        "chapter": {"type": "integer", "minimum": 1, "description": "Chapter number within the Kanda"},
        "segment_index": {"type": "integer", "minimum": 1, "description": "Sequential segment index within the Kanda"},
        "title": {"type": "string", "minLength": 1, "description": "Title of the story segment"},
        "content": {"type": "string", "minLength": 1, "description": "Full narrative content of the story segment"},
        "characters": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1, "description": "List of characters appearing in this segment"},
        "key_events": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1, "description": "List of key events in this segment"},
        "philosophical_themes": {"type": "array", "items": {"type": "string", "minLength": 1}, "description": "Dharmic and philosophical themes (e.g., sacrifice, dharma, devotion, karma, truth)"},
        "lesser_known_facts": {"type": "array", "items": {"type": "string", "minLength": 1}, "description": "Details from the original Valmiki Ramayan that most retellings skip"},
        "debate_angles": {"type": "array", "items": {"type": "string", "minLength": 1}, "description": "Morally complex questions about non-divine characters choices"},
        "modern_relevance": {"type": "array", "items": {"type": "string", "minLength": 1}, "description": "How events/lessons apply to modern life"},
        "suggested_angles": {
            "type": "array",
            "items": {"type": "string", "enum": ["hidden_meaning", "why", "character_study", "life_lesson", "unknown_facts", "what_if", "debate"]},
            "description": "Which explainer video angles work best for this segment"
        }
    },
    "additionalProperties": False
}

with open("ramayan_db/schema/story_segment_schema.json", "w") as f:
    json.dump(schema, f, indent=2)
    f.write("\n")

print("Schema updated successfully")
