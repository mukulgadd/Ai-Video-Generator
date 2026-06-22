"""YouTube Metadata Generator.

Generates optimized title, description, tags, and hashtags from the
episode script for YouTube Shorts auto-upload.

Follows YouTube SEO best practices:
- Title: 60-70 chars, hook + keyword
- Description: Story summary + engagement CTA + hashtags
- Tags: Mix of broad + specific mythology keywords
- Hashtags: 3-5 relevant hashtags for Shorts discovery
"""

import logging
from dataclasses import dataclass, field
from typing import List

from src.episode_script import EpisodeScript

logger = logging.getLogger(__name__)


@dataclass
class YouTubeMetadata:
    """Complete metadata for a YouTube Shorts upload."""

    title: str
    description: str
    tags: List[str]
    hashtags: List[str]
    category: str = "Education"  # YouTube category
    privacy: str = "public"
    made_for_kids: bool = False
    language: str = "hi"  # Hindi primary


# Base tags that go on every video for channel consistency
BASE_TAGS = [
    "Ramayan",
    "Ramayana",
    "Hindu Mythology",
    "Indian Mythology",
    "Spiritual",
    "Dharma",
    "Sanskrit",
    "Valmiki Ramayan",
    "Ram",
    "Sita",
    "Hanuman",
    "Indian Culture",
    "Mythology Explained",
    "Hindu Stories",
    "Sanatan Dharma",
]

# Angle-specific tags
ANGLE_TAGS = {
    "hidden_meaning": ["Hidden Meaning", "Symbolism", "Deep Analysis", "Secret Knowledge"],
    "why": ["Explained", "Analysis", "Reasons", "Motivation"],
    "character_study": ["Character Analysis", "Psychology", "Villain", "Hero"],
    "life_lesson": ["Life Lessons", "Wisdom", "Inspiration", "Motivation"],
    "unknown_facts": ["Unknown Facts", "Did You Know", "Surprising Facts", "Secret"],
    "what_if": ["What If", "Alternative History", "Theory", "Speculation"],
    "debate": ["Debate", "Discussion", "Moral Dilemma", "Dharma Sankat"],
}

# Kanda-specific tags
KANDA_TAGS = {
    "Bala Kanda": ["Bala Kanda", "Birth of Rama", "Ayodhya", "Prince Rama"],
    "Ayodhya Kanda": ["Ayodhya Kanda", "Exile", "Vanvas", "Kaikeyi", "Bharata"],
    "Aranya Kanda": ["Aranya Kanda", "Forest", "Dandaka", "Surpanakha", "Golden Deer"],
    "Kishkindha Kanda": ["Kishkindha Kanda", "Hanuman", "Sugriva", "Vali", "Monkey Army"],
    "Sundara Kanda": ["Sundara Kanda", "Lanka", "Hanuman Leap", "Ashoka Vatika"],
    "Yuddha Kanda": ["Yuddha Kanda", "Battle Lanka", "Ram Setu", "Ravana", "War"],
    "Uttara Kanda": ["Uttara Kanda", "Ram Rajya", "Coronation", "Return Ayodhya"],
}

# Standard hashtags for Shorts discovery
BASE_HASHTAGS = ["#Ramayan", "#HinduMythology", "#SpiritualShorts"]


def generate_youtube_metadata(script: EpisodeScript, kanda_name: str) -> YouTubeMetadata:
    """Generate optimized YouTube metadata from an episode script.

    Args:
        script: The EpisodeScript with hook, angle, revelation, engagement_cta.
        kanda_name: The Kanda name for tag generation.

    Returns:
        YouTubeMetadata ready for upload.
    """
    # Title: Use the script title (already optimized for engagement)
    # Truncate to 70 chars if needed (YouTube shows ~60 on mobile)
    title = script.title
    if len(title) > 70:
        title = title[:67] + "..."

    # Description
    description = _build_description(script, kanda_name)

    # Tags: base + angle-specific + kanda-specific + character names
    tags = list(BASE_TAGS)
    tags.extend(ANGLE_TAGS.get(script.angle, []))
    tags.extend(KANDA_TAGS.get(kanda_name, []))

    # Add character names from scenes as tags
    characters_seen = set()
    for scene in script.scenes:
        for char in scene.characters:
            characters_seen.add(char)
    tags.extend(sorted(characters_seen))

    # Deduplicate while preserving order
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            unique_tags.append(tag)
    tags = unique_tags[:30]  # YouTube allows max 500 chars, ~30 tags is safe

    # Hashtags for Shorts
    hashtags = list(BASE_HASHTAGS)
    # Add kanda-specific hashtag
    kanda_hashtag = f"#{kanda_name.replace(' ', '')}"
    hashtags.append(kanda_hashtag)
    # Add angle hashtag
    angle_hashtags = {
        "hidden_meaning": "#HiddenMeaning",
        "why": "#MythologyExplained",
        "character_study": "#CharacterAnalysis",
        "life_lesson": "#LifeLessons",
        "unknown_facts": "#DidYouKnow",
        "what_if": "#WhatIf",
        "debate": "#MoralDilemma",
    }
    if script.angle in angle_hashtags:
        hashtags.append(angle_hashtags[script.angle])
    hashtags = hashtags[:5]  # YouTube shows max 3-5 hashtags

    return YouTubeMetadata(
        title=title,
        description=description,
        tags=tags,
        hashtags=hashtags,
    )


def _build_description(script: EpisodeScript, kanda_name: str) -> str:
    """Build an SEO-optimized YouTube description."""
    parts = []

    # Hook as opening line (shows in search results)
    if script.hook:
        parts.append(script.hook)
        parts.append("")

    # Episode info
    parts.append(f"Episode {script.episode_number} | {kanda_name}")
    parts.append(f"Angle: {script.angle.replace('_', ' ').title()}")
    parts.append("")

    # Revelation (the core value proposition)
    if script.revelation:
        parts.append(f"In this episode: {script.revelation}")
        parts.append("")

    # Engagement CTA
    if script.engagement_cta:
        parts.append(f"What do you think? {script.engagement_cta}")
        parts.append("Comment your answer below!")
        parts.append("")

    # Channel info
    parts.append("---")
    parts.append("सनातन रहस्य | Sanatan Rahasya")
    parts.append("Daily revelations from the Sanatan Dharma epics.")
    parts.append("Follow for hidden meanings, forgotten facts, and life lessons from Valmiki's Ramayan.")
    parts.append("")

    # Hashtags at bottom
    parts.append(" ".join(BASE_HASHTAGS))

    return "\n".join(parts)


def save_metadata_to_file(metadata: YouTubeMetadata, output_path: str) -> str:
    """Save metadata as a text file alongside the video for upload reference.

    Args:
        metadata: The generated YouTube metadata.
        output_path: Where to save (e.g., output/episode_0001_metadata.txt).

    Returns:
        Path to the saved metadata file.
    """
    lines = [
        f"TITLE: {metadata.title}",
        "",
        "DESCRIPTION:",
        metadata.description,
        "",
        f"TAGS: {', '.join(metadata.tags)}",
        "",
        f"HASHTAGS: {' '.join(metadata.hashtags)}",
        "",
        f"CATEGORY: {metadata.category}",
        f"PRIVACY: {metadata.privacy}",
        f"LANGUAGE: {metadata.language}",
        f"MADE_FOR_KIDS: {metadata.made_for_kids}",
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info("YouTube metadata saved: %s", output_path)
    return output_path
