"""Script Engine for the Ramayan Video Generator.

Transforms story segments into structured episode scripts using an LLM.
Handles character registry lookup, script validation, and segment merging.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from src.episode_script import (
    DialogueLine,
    EpisodeScript,
    Scene,
    parse,
)
from src.story_manager import StorySegment


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ScriptEngineError(Exception):
    """Raised when the ScriptEngine encounters an error."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ScriptValidationError(ScriptEngineError):
    """Raised when a generated script fails validation."""

    pass


# ---------------------------------------------------------------------------
# LLM Client Protocol (for dependency injection / testability)
# ---------------------------------------------------------------------------


class LLMClient(Protocol):
    """Protocol for an LLM API client."""

    def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
    ) -> str:
        """Send a chat completion request and return the response content.

        Args:
            model: The model identifier.
            messages: List of message dicts with 'role' and 'content'.
            temperature: Sampling temperature.

        Returns:
            The assistant's response content as a string.
        """
        ...


# ---------------------------------------------------------------------------
# OpenAI LLM Client Adapter
# ---------------------------------------------------------------------------


class OpenAILLMClient:
    """LLM client adapter wrapping the OpenAI Python library."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key. If None, uses the OPENAI_API_KEY env var.
        """
        import openai

        self._client = openai.OpenAI(api_key=api_key)

    def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
    ) -> str:
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content


# ---------------------------------------------------------------------------
# System Prompt (Task 4.2)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert scriptwriter for a viral mythology YouTube Shorts/Reels channel \
called "सनातन रहस्य" (Sanatan Rahasya). You create compelling short-form videos \
about the Ramayan epic — each video exploring ONE specific angle assigned to you.

Your videos are NOT basic retellings. They follow the "Hook → Story → Revelation" \
format that drives engagement on short-form platforms.

**CONTENT ANGLES** — You will be told EXACTLY which angle to use. Follow it precisely:
- "hidden_meaning" — Reveal deeper symbolism or philosophy behind an event
- "why" — Explain motivations and reasoning behind a character's decision
- "character_study" — Explore the complexity of a character
- "life_lesson" — Extract a timeless principle applicable to modern life
- "unknown_facts" — Surface a lesser-known detail from the original Valmiki text
- "what_if" — Explore what would have happened if events went differently
- "debate" — Present opposing viewpoints on a morally complex situation

⚠️ IMPORTANT: You MUST use the exact angle specified in the user prompt. \
The angle field in your JSON MUST match what is requested. Do NOT default to \
"hidden_meaning" unless explicitly told to use it.

**VIDEO STRUCTURE (Hook → Story → Revelation):**
- SCENE 1 — THE HOOK (6-10s): A provocative question or surprising statement \
that makes viewers stop scrolling. Must create immediate curiosity.
- SCENES 2-4 — THE STORY: Tell the relevant Ramayan event as EVIDENCE \
for your angle. Don't just narrate — analyze. Build toward the revelation.
- FINAL SCENE — THE REVELATION + CTA (8-12s): Deliver the insight. Then ask a \
thought-provoking question to trigger comments and tell viewers to follow.

**TITLE RULES** (MUST be in English only — no Hindi in title):
- Title MUST reflect the specific angle you're using
- Keep it under 60 characters
- Make it create a knowledge gap (viewer must watch to find out)
- Do NOT always use "The hidden meaning of..." — vary your title style
- No Devanagari in titles

**NARRATION TONE:**
- Conversational and passionate, like a friend telling you an incredible story
- Build curiosity: "But here's where it gets interesting..."
- Rhetorical questions: "Think about this for a moment..."
- Personal observations: "What I find most remarkable is..."
- Never dry or textbook-like. Every sentence should make the viewer want the next one.

**SACRED CONTENT GUIDELINES (MANDATORY — NEVER VIOLATE):**
Our audience is deeply devotional. Every video must be spiritually uplifting.

ALWAYS:
- Treat Rama, Sita, Hanuman, Lakshmana, and all divine characters with absolute \
reverence. They are God, not fictional characters.
- Frame analysis through the lens of dharma, devotion, and spiritual wisdom.
- Use respectful honorifics: "Bhagwan Ram", "Mata Sita", "Prabhu", "Shri".
- Present moral complexity as divine leela (play), not human weakness.
- End with a spiritual takeaway that strengthens the viewer's faith.
- Show admiration and awe toward divine actions, never skepticism.

NEVER:
- Question the divinity of Rama, Sita, Hanuman, or any avatars/deities.
- Use "Hero or Villain?" framing for Rama, Sita, Hanuman, Lakshmana, or Bharata.
- Portray Sita as helpless — she is Shakti incarnate.
- Frame Rama's actions as mistakes or errors in judgment.
- Use clickbait that implies disrespect (e.g., "Was Rama WRONG to...").
- Mock, trivialize, or satirize any sacred ritual, scripture, or divine event.
- Compare deities unfavorably to mortal characters.
- Use Western literary criticism frameworks that reduce divinity to "character flaws".
- Present rationalist/atheist interpretations of divine events.

FOR "character_study" AND "debate" ANGLES:
- Only apply moral complexity to NON-DIVINE characters (Ravana, Kaikeyi, \
Vibhishana, Maricha, Surpanakha, Manthara).
- Debates must be about the dharma DILEMMA of mortals, never about divine decisions.
- Example GOOD: "Was Vibhishana right to betray his brother for dharma?"
- Example BAD: "Was Rama right to banish Sita?"

FOR "what_if" ANGLES:
- Never frame divine events as things that "could have gone differently" — \
they are divine leela with perfect cosmic purpose.
- "What if" must only apply to mortal characters' choices.
- Example GOOD: "What if Kaikeyi never asked for the boons?"
- Example BAD: "What if Rama refused to go to the forest?"

**CONSTRAINTS:**
1. **Scene count**: 3 to 5 scenes (inclusive). Keep it tight and punchy.
2. **Total duration**: Sum of scene durations must be 45-50 seconds (inclusive). \
This is a YouTube Short — branding cards add 10s on top, so total must stay under 60s.
3. **ONE FACT ONLY**: Each video focuses on exactly ONE surprising fact, ONE insight, \
or ONE angle. Do NOT pack multiple facts into one video. Go deep on one thing.
4. **Scene fields**: Every scene MUST have non-empty `background`, `narration`, and `narration_en`.
5. **Language**: `narration` and `dialogue.text` MUST be in Hindi (Devanagari). \
`background`, `action`, `mood`, `sound_effects` stay in English.
6. **narration_en**: English translation of narration — equally engaging, not literal.
7. **hook**: A one-line English hook (the scroll-stopping opening — used for thumbnails). \
Must be COMPLETE and under 100 characters.
8. **angle**: One of the 7 angle types listed above.
9. **revelation**: One sentence summarizing the core insight (English).
10. **engagement_cta**: The comment-triggering question asked at the end (English). \
Must be a COMPLETE question under 100 characters.
11. **title**: MUST be in English only, under 60 characters. No Hindi/Devanagari in titles.

**SCENE 1 (THE HOOK) RULES:**
- Duration: 6-10 seconds
- Opens with a question or shocking statement
- Must create a "knowledge gap" — viewer NEEDS to watch to find the answer
- Example hook: "Did you know Rama's birth came at a cost that destroyed \
King Dasharatha's happiness forever?"

**FINAL SCENE RULES:**
- Duration: 8-12 seconds
- Deliver the revelation clearly
- End with the engagement_cta question in both Hindi narration and English
- Tell viewers to follow/subscribe
- Example: "Was this sacrifice worth it? Tell me in the comments. \
Follow for the next revelation from the Ramayan."

Output ONLY valid JSON (no markdown fences, no extra text):

{
  "episode_number": <integer>,
  "kanda": "<string>",
  "title": "<engaging title matching your chosen angle>",
  "total_duration_seconds": <integer, 45-50>,
  "hook": "<one-line English hook for thumbnails/branding>",
  "angle": "<one of: hidden_meaning, why, character_study, life_lesson, unknown_facts, what_if, debate>",
  "revelation": "<one sentence — the core insight in English>",
  "engagement_cta": "<the comment-triggering question in English>",
  "scenes": [
    {
      "scene_number": <integer>,
      "duration_seconds": <integer>,
      "background": "<detailed visual description for Indian traditional art style>",
      "characters": ["<character_name>", ...],
      "action": "<what happens visually in this scene>",
      "narration": "<Hindi narration — conversational, builds curiosity>",
      "narration_en": "<English translation — equally engaging, not robotic>",
      "dialogue": [
        {"character": "<name>", "text": "<spoken line IN HINDI>"}
      ],
      "mood": "<devotional|dramatic|serene|mysterious|triumphant|melancholy|intense|hopeful>",
      "sound_effects": ["<effect_name>", ...]
    }
  ]
}
"""


# ---------------------------------------------------------------------------
# Character Registry (Task 4.3)
# ---------------------------------------------------------------------------


def load_character_registry(characters_dir: str = "models/characters") -> Dict[str, str]:
    """Load character names and descriptions from the characters directory.

    Each character is expected to have a subdirectory containing a
    `character.json` file with at least `name` and `description` fields.

    Args:
        characters_dir: Path to the models/characters/ directory.

    Returns:
        A dict mapping character name -> description.
    """
    registry: Dict[str, str] = {}

    if not os.path.isdir(characters_dir):
        return registry

    for entry in sorted(os.listdir(characters_dir)):
        entry_path = os.path.join(characters_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        char_json_path = os.path.join(entry_path, "character.json")
        if not os.path.isfile(char_json_path):
            continue

        try:
            with open(char_json_path, "r") as f:
                data = json.load(f)
            name = data.get("name", entry)
            description = data.get("description", "")
            registry[name] = description
        except (json.JSONDecodeError, OSError):
            continue

    return registry


def _format_character_registry_for_prompt(registry: Dict[str, str]) -> str:
    """Format the character registry as a text block for the LLM prompt."""
    if not registry:
        return "No character registry provided. Use character names from the story segment."

    lines = ["Character Registry:"]
    for name, description in sorted(registry.items()):
        if description:
            lines.append(f"- {name}: {description}")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Script Validation (Task 4.4)
# ---------------------------------------------------------------------------


VALID_ANGLES = [
    "hidden_meaning",
    "why",
    "character_study",
    "life_lesson",
    "unknown_facts",
    "what_if",
    "debate",
]


def validate_script(
    script: EpisodeScript,
    character_registry: Dict[str, str],
) -> List[str]:
    """Validate an episode script against production constraints.

    Checks:
    - Scene count is 4-8
    - Total duration is 110-130 seconds
    - Each scene has non-empty required fields
    - Explainer metadata fields are present and valid
    - All character names exist in the registry

    Args:
        script: The EpisodeScript to validate.
        character_registry: Dict mapping character name -> description.

    Returns:
        A list of validation error messages. Empty list means valid.
    """
    errors: List[str] = []

    # Explainer metadata validation
    if not script.hook or not script.hook.strip():
        errors.append("hook is empty — must contain scroll-stopping opening line.")
    if not script.angle or script.angle not in VALID_ANGLES:
        errors.append(
            f"angle '{script.angle}' is invalid — must be one of: {', '.join(VALID_ANGLES)}."
        )
    if not script.revelation or not script.revelation.strip():
        errors.append("revelation is empty — must contain core insight.")
    if not script.engagement_cta or not script.engagement_cta.strip():
        errors.append("engagement_cta is empty — must contain comment-triggering question.")

    # Scene count: 3-5
    scene_count = len(script.scenes)
    if scene_count < 3 or scene_count > 5:
        errors.append(
            f"Scene count {scene_count} is outside the allowed range of 3-5."
        )

    # Total duration: sanity check (quality gate enforces the tighter 45-50s target)
    total_duration = sum(scene.duration_seconds for scene in script.scenes)
    if total_duration < 20 or total_duration > 90:
        errors.append(
            f"Total duration {total_duration}s is outside the sane range of 20-90s."
        )

    # Required fields per scene
    for scene in script.scenes:
        prefix = f"Scene {scene.scene_number}"
        if not scene.background or not scene.background.strip():
            errors.append(f"{prefix}: background is empty.")
        if not scene.action or not scene.action.strip():
            errors.append(f"{prefix}: action is empty.")
        if not scene.narration or not scene.narration.strip():
            errors.append(f"{prefix}: narration is empty.")
        if not scene.narration_en or not scene.narration_en.strip():
            # Not a fatal error — subtitles will use narration field as fallback
            pass

    # Hook scene duration check (scene 1 should be 8-12s)
    if script.scenes and script.scenes[0].duration_seconds > 12:
        errors.append(
            f"Scene 1 (hook) is {script.scenes[0].duration_seconds}s — should be 8-12s."
        )

    return errors


# ---------------------------------------------------------------------------
# Sacred Content Safety Validator
# ---------------------------------------------------------------------------

# Divine characters that must ALWAYS be portrayed with reverence
PROTECTED_DIVINE_CHARACTERS = {
    "Rama", "Ram", "Shri Ram", "Bhagwan Ram", "Lord Rama",
    "Sita", "Mata Sita", "Janaki", "Vaidehi",
    "Hanuman", "Bajrangbali", "Pawanputra",
    "Lakshmana", "Lakshman",
    "Bharata", "Bharat",
    "Shatrughna",
    "Vishnu", "Narayana",
    "Shiva", "Mahadev",
    "Brahma",
}

# Phrases that indicate disrespectful framing
DISRESPECT_PATTERNS = [
    # English red flags
    "rama was wrong",
    "rama's mistake",
    "rama's error",
    "sita was weak",
    "sita was helpless",
    "hero or villain",  # when applied to divine characters
    "was rama right to",
    "rama's cruelty",
    "rama's failure",
    "flawed character",
    "character flaw",
    "morally questionable",
    "was it fair",  # when about divine actions
    "rama abandoned",
    "rama banished sita",
    "unfair to sita",
    # Hindi red flags
    "राम की गलती",
    "राम गलत थे",
    "सीता कमजोर",
    "सीता बेचारी",
    "राम ने अन्याय",
    "राम क्रूर",
]

# Patterns that question divinity
DIVINITY_QUESTIONING_PATTERNS = [
    "just a story",
    "just a myth",
    "fictional character",
    "not actually divine",
    "merely human",
    "just a man",
    "just a woman",
    "was rama really god",
    "if rama was truly god",
    "mythological figure",
    "legendary figure",
    # Hindi
    "केवल एक कहानी",
    "काल्पनिक",
    "मिथक",
]


def validate_sacred_content(script: EpisodeScript) -> List[str]:
    """Validate that the script respects religious sentiments and stays spiritually inclined.

    Checks:
    - Title and hook don't use disrespectful framing for divine characters
    - Narration doesn't question divinity
    - character_study/debate angles aren't applied to protected characters
    - Overall tone is devotional, not skeptical

    Args:
        script: The EpisodeScript to validate.

    Returns:
        A list of content safety violations. Empty list means safe.
    """
    violations: List[str] = []

    # Combine all text for scanning
    title_lower = script.title.lower()
    hook_lower = script.hook.lower() if script.hook else ""
    revelation_lower = script.revelation.lower() if script.revelation else ""
    cta_lower = script.engagement_cta.lower() if script.engagement_cta else ""

    all_narration = []
    for scene in script.scenes:
        all_narration.append(scene.narration.lower())
        all_narration.append(scene.narration_en.lower() if scene.narration_en else "")
    narration_combined = " ".join(all_narration)

    # Check for disrespectful patterns in title, hook, and narration
    searchable_text = f"{title_lower} {hook_lower} {revelation_lower} {cta_lower} {narration_combined}"

    for pattern in DISRESPECT_PATTERNS:
        if pattern in searchable_text:
            violations.append(
                f"Disrespectful framing detected: '{pattern}' found in script content. "
                f"Divine characters must always be portrayed with reverence."
            )

    for pattern in DIVINITY_QUESTIONING_PATTERNS:
        if pattern in searchable_text:
            violations.append(
                f"Divinity-questioning content detected: '{pattern}' found. "
                f"Content must treat divine events as sacred truth, not mythology."
            )

    # Check character_study/debate angles aren't targeting divine characters
    if script.angle in ("character_study", "debate", "what_if"):
        # Check if the title/hook mentions protected characters in a questioning way
        for char in PROTECTED_DIVINE_CHARACTERS:
            char_lower = char.lower()
            if char_lower in title_lower:
                # Check if the title has questioning framing
                questioning_words = ["villain", "wrong", "mistake", "justify", "fair", "cruel"]
                for qw in questioning_words:
                    if qw in title_lower:
                        violations.append(
                            f"'{script.angle}' angle with questioning framing ('{qw}') "
                            f"applied to divine character '{char}'. "
                            f"Moral complexity angles must only target non-divine characters."
                        )
                        break

    # Check that "what_if" angle doesn't question divine decisions
    if script.angle == "what_if":
        what_if_divine_patterns = [
            "what if rama", "what if sita", "what if hanuman",
            "what if lakshmana", "what if bharata",
            "अगर राम", "अगर सीता", "अगर हनुमान",
        ]
        for pattern in what_if_divine_patterns:
            if pattern in title_lower or pattern in hook_lower:
                violations.append(
                    f"'what_if' angle questions divine character's actions: '{pattern}'. "
                    f"'What if' must only apply to mortal characters' choices."
                )

    return violations

# Minimum word count for a segment to be considered sufficient for a full episode
MIN_SEGMENT_WORD_COUNT = 50


def is_segment_too_short(segment: StorySegment) -> bool:
    """Check if a story segment is too short for a full episode.

    Args:
        segment: The story segment to check.

    Returns:
        True if the segment content has fewer words than the minimum threshold.
    """
    word_count = len(segment.content.split())
    return word_count < MIN_SEGMENT_WORD_COUNT


def merge_segments(
    segment_a: StorySegment,
    segment_b: StorySegment,
) -> StorySegment:
    """Merge two story segments into one combined segment.

    The merged segment takes metadata from segment_a but combines
    content, characters, and key_events from both.

    Args:
        segment_a: The primary (short) segment.
        segment_b: The next sequential segment to merge with.

    Returns:
        A new StorySegment with combined content.
    """
    combined_characters = list(
        dict.fromkeys(segment_a.characters + segment_b.characters)
    )
    combined_events = segment_a.key_events + segment_b.key_events
    combined_content = segment_a.content.rstrip() + "\n\n" + segment_b.content.lstrip()

    return StorySegment(
        kanda_index=segment_a.kanda_index,
        kanda_name=segment_a.kanda_name,
        chapter=segment_a.chapter,
        segment_index=segment_a.segment_index,
        title=f"{segment_a.title} & {segment_b.title}",
        content=combined_content,
        characters=combined_characters,
        key_events=combined_events,
    )


# ---------------------------------------------------------------------------
# ScriptEngine (Task 4.1)
# ---------------------------------------------------------------------------


class ScriptEngine:
    """Transforms story segments into structured episode scripts using an LLM.

    The engine:
    1. Loads the character registry from disk
    2. Builds a structured prompt with story segment + character info
    3. Calls the LLM API to generate a script
    4. Validates the script against production constraints
    5. Returns a validated EpisodeScript

    Args:
        llm_client: An object implementing the LLMClient protocol.
        model: The LLM model identifier (e.g. "gpt-4").
        temperature: Sampling temperature for the LLM. Default 0.7.
        characters_dir: Path to the models/characters/ directory.
    """

    def __init__(
        self,
        llm_client: Any,
        model: str = "gpt-4",
        temperature: float = 0.7,
        characters_dir: str = "models/characters",
    ):
        self._llm_client = llm_client
        self._model = model
        self._temperature = temperature
        self._characters_dir = characters_dir
        self._character_registry: Optional[Dict[str, str]] = None

    def _get_character_registry(self) -> Dict[str, str]:
        """Load and cache the character registry."""
        if self._character_registry is None:
            self._character_registry = load_character_registry(self._characters_dir)
        return self._character_registry

    def _build_user_prompt(
        self,
        segment: StorySegment,
        character_registry: Dict[str, str],
        episode_number: int,
        video_index: int = 0,
        previous_titles: Optional[List[str]] = None,
    ) -> str:
        """Build the user prompt for the LLM, including enriched analysis fields."""
        registry_text = _format_character_registry_for_prompt(character_registry)

        # If registry is empty, build a minimal registry from the segment's characters
        if not character_registry:
            char_lines = ["Character Registry (from story segment):"]
            for name in segment.characters:
                char_lines.append(f"- {name}")
            registry_text = "\n".join(char_lines)

        # Build enrichment sections (only include if data exists)
        enrichment_parts = []

        if segment.philosophical_themes:
            enrichment_parts.append(
                "Philosophical/Dharmic Themes:\n"
                + "\n".join(f"- {t}" for t in segment.philosophical_themes)
            )

        if segment.lesser_known_facts:
            enrichment_parts.append(
                "Lesser-Known Facts (from Valmiki Ramayan — use these for 'unknown_facts' angle):\n"
                + "\n".join(f"- {f}" for f in segment.lesser_known_facts)
            )

        if segment.debate_angles:
            enrichment_parts.append(
                "Debate Angles (moral questions about NON-DIVINE characters only):\n"
                + "\n".join(f"- {a}" for a in segment.debate_angles)
            )

        if segment.modern_relevance:
            enrichment_parts.append(
                "Modern Relevance (life lessons applicable today):\n"
                + "\n".join(f"- {r}" for r in segment.modern_relevance)
            )

        if segment.suggested_angles:
            enrichment_parts.append(
                f"Suggested Best Angles for This Segment: {', '.join(segment.suggested_angles)}"
            )

        enrichment_text = "\n\n".join(enrichment_parts) if enrichment_parts else ""

        prompt = (
            f"Create a mythology explainer video script for the following Ramayan story segment.\n\n"
            f"Episode Number: {episode_number}\n"
            f"Kanda: {segment.kanda_name}\n"
            f"Segment Title: {segment.title}\n\n"
            f"--- RAW STORY MATERIAL ---\n{segment.content}\n--- END STORY ---\n\n"
            f"{registry_text}\n\n"
            f"Key Events in This Segment:\n"
            + "\n".join(f"- {event}" for event in segment.key_events)
        )

        if enrichment_text:
            prompt += f"\n\n--- ANALYSIS MATERIAL (use this for deeper content) ---\n{enrichment_text}\n--- END ANALYSIS ---"

        # Determine which specific angle/fact to focus on based on video_index
        focus_instruction = self._get_focus_instruction(segment, video_index)
        required_angle = self._get_required_angle(segment, video_index)

        # Build strong enforcement block
        angle_enforcement = ""
        if required_angle != "hidden_meaning":
            angle_enforcement = (
                f"\n⚠️ CRITICAL CONSTRAINT: The 'angle' field in your JSON output MUST be "
                f"exactly \"{required_angle}\". Do NOT use 'hidden_meaning'. "
                f"Do NOT talk about deeper philosophical meanings or cosmic blueprints. "
                f"Instead, focus ONLY on the specific fact/question/lesson given below.\n"
                f"Your TITLE must NOT contain 'hidden meaning', 'cosmic', 'blueprint', or 'deeper truth'. "
                f"Use a title style that matches {required_angle} angle.\n"
            )

        # Title de-duplication
        title_constraint = ""
        if previous_titles:
            titles_list = "\n".join(f"  - \"{t}\"" for t in previous_titles[-10:])
            title_constraint = (
                f"\n⚠️ TITLE CONSTRAINT: The following titles have already been used. "
                f"Your title MUST be completely different — do NOT reuse or rephrase these:\n"
                f"{titles_list}\n"
            )

        prompt += (
            "\n\n"
            f"{'=' * 60}\n"
            f"MANDATORY ANGLE: {required_angle}\n"
            f"{'=' * 60}\n"
            f"{angle_enforcement}\n"
            f"SPECIFIC FOCUS FOR THIS VIDEO:\n{focus_instruction}\n"
            f"{title_constraint}\n"
            f"INSTRUCTIONS:\n"
            f"1. The 'angle' field MUST be exactly: \"{required_angle}\"\n"
            f"2. Craft an English-only title (under 60 chars) that matches the angle above.\n"
            f"3. Write a COMPLETE hook under 100 chars that creates a knowledge gap.\n"
            f"4. Focus on ONE single fact/insight — go deep, not broad.\n"
            f"5. Use the story as EVIDENCE for your analysis, not just a retelling.\n"
            f"6. End with a revelation that delivers genuine insight.\n"
            f"7. The engagement_cta should be a COMPLETE question under 100 chars.\n\n"
            f"Remember: output ONLY valid JSON, no markdown fences. "
            f"The 'angle' MUST be \"{required_angle}\"."
        )

        return prompt

    @staticmethod
    def _get_required_angle(segment: StorySegment, video_index: int) -> str:
        """Return the required angle string for the given video_index."""
        topics_angles = []

        # Video 0: hidden_meaning
        topics_angles.append("hidden_meaning")

        # Each lesser_known_fact → unknown_facts
        for _ in segment.lesser_known_facts:
            topics_angles.append("unknown_facts")

        # Each debate_angle → debate
        for _ in segment.debate_angles:
            topics_angles.append("debate")

        # Each modern_relevance → life_lesson
        for _ in segment.modern_relevance:
            topics_angles.append("life_lesson")

        # Additional suggested angles
        for angle in segment.suggested_angles:
            if angle != "hidden_meaning":
                topics_angles.append(angle)

        idx = video_index % len(topics_angles) if topics_angles else 0
        return topics_angles[idx]

    @staticmethod
    def _get_focus_instruction(segment: StorySegment, video_index: int) -> str:
        """Determine what specific fact/angle this video should focus on.

        Maps video_index to a specific piece of content from the segment's
        enrichment data, ensuring each video from the same segment is unique.

        Video 0 is ALWAYS the primary narrative introduction — telling the
        main story with its deeper meaning. Subsequent videos explore facts,
        debates, lessons, and alternate angles.
        """
        # Build ordered list of focus topics
        topics = []

        # Video 0: ALWAYS the primary narrative (regardless of suggested_angles)
        topics.append(
            "Use the 'hidden_meaning' angle. This is the INTRODUCTORY video for this story — "
            "narrate ALL the key events of this segment from start to finish as a complete "
            "story arc. Cover the full narrative: the setup, the main events, and the outcome. "
            "Do NOT zoom into just one sub-event. At the end, briefly mention one deeper "
            "spiritual takeaway, but the main focus is TELLING THE COMPLETE STORY clearly."
        )

        # Each lesser_known_fact gets its own video
        for fact in segment.lesser_known_facts:
            topics.append(
                f"Use the 'unknown_facts' angle. Your ENTIRE video must be about revealing "
                f"this ONE surprising fact: \"{fact}\"\n"
                f"Structure: Hook with the surprising fact → explain the context → "
                f"reveal WHY this fact matters. Do NOT discuss cosmic blueprints or "
                f"hidden philosophical meanings."
            )

        # Each debate_angle gets its own video
        for debate in segment.debate_angles:
            topics.append(
                f"Use the 'debate' angle. Your ENTIRE video must explore this ONE "
                f"debate question: \"{debate}\"\n"
                f"Structure: Present the question → show both sides → let the viewer decide. "
                f"Do NOT reveal hidden meanings. Focus on the DEBATE."
            )

        # Each modern_relevance gets its own video
        for relevance in segment.modern_relevance:
            topics.append(
                f"Use the 'life_lesson' angle. Your ENTIRE video must teach this ONE "
                f"modern life lesson: \"{relevance}\"\n"
                f"Structure: Hook with the lesson → connect to the story → show how it "
                f"applies today. Do NOT discuss cosmic symbolism. Focus on PRACTICAL WISDOM."
            )

        # Additional suggested angles (all of them, since video 0 is now fixed)
        for angle in segment.suggested_angles:
            if angle != "hidden_meaning":  # Avoid duplicate of video 0
                topics.append(
                    f"Use the '{angle}' angle. Find a DIFFERENT insight from the story "
                    f"than what previous videos covered."
                )

        # Clamp video_index to available topics
        idx = video_index % len(topics) if topics else 0
        return topics[idx]

    def generate_script(
        self,
        segment: StorySegment,
        character_registry: Optional[Dict[str, str]] = None,
        episode_number: int = 1,
        video_index: int = 0,
        previous_titles: Optional[List[str]] = None,
    ) -> EpisodeScript:
        """Generate an episode script from a story segment.

        Args:
            segment: The story segment to transform into a script.
            character_registry: Dict mapping character name -> description.
                If None, loads from the characters directory.
            episode_number: The episode number for this script.
            video_index: Which sub-video of this segment (0-based). Different
                indices focus on different facts/angles from the same segment.

        Returns:
            A validated EpisodeScript object.

        Raises:
            ScriptEngineError: If the LLM call fails or the response is invalid.
            ScriptValidationError: If the generated script fails validation.
        """
        if character_registry is None:
            character_registry = self._get_character_registry()

        # If registry is empty, build from segment characters
        effective_registry = character_registry
        if not effective_registry:
            effective_registry = {name: "" for name in segment.characters}

        user_prompt = self._build_user_prompt(
            segment, effective_registry, episode_number, video_index,
            previous_titles=previous_titles,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # Retry with exponential backoff for transient API errors (503, etc.)
        import time
        max_retries = 5
        response_text = None
        for attempt in range(max_retries):
            try:
                response_text = self._llm_client.chat_completions_create(
                    model=self._model,
                    messages=messages,
                    temperature=self._temperature,
                )
                break  # Success — exit retry loop
            except Exception as e:
                error_str = str(e)
                if ("503" in error_str or "UNAVAILABLE" in error_str or "overloaded" in error_str.lower()) and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 60  # 60s, 120s, 240s, 480s (~20 min total)
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Gemini API temporarily unavailable (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    raise ScriptEngineError(f"LLM API call failed: {e}")

        if not response_text:
            raise ScriptEngineError("LLM returned empty response.")

        # Strip markdown fences if present
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first line (```json or ```) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            cleaned = "\n".join(lines)

        # Parse the JSON response into an EpisodeScript
        try:
            script = parse(cleaned)
        except Exception as e:
            raise ScriptEngineError(
                f"Failed to parse LLM response as EpisodeScript: {e}"
            )

        # Validate the script
        validation_errors = validate_script(script, effective_registry)
        if validation_errors:
            raise ScriptValidationError(
                "Script validation failed:\n" + "\n".join(validation_errors)
            )

        # Sacred content safety check
        content_violations = validate_sacred_content(script)
        if content_violations:
            raise ScriptValidationError(
                "Sacred content safety check failed:\n" + "\n".join(content_violations)
            )

        return script
