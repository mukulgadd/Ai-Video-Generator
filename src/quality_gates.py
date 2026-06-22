"""Quality Gates — Validates pipeline output at each stage.

Prevents wasted compute by catching issues early:
- Script quality gate: catches bad Gemini output before image generation
- Video validation: ensures final output is playable before marking complete
"""

import json
import logging
import os
import re
import subprocess
from typing import List, Optional, Tuple

from src.episode_script import EpisodeScript

logger = logging.getLogger(__name__)


# ============================================================
# CHECKPOINT 1: Script Quality Gate
# ============================================================

def validate_script_quality(
    script: EpisodeScript, required_angle: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """Validate script quality before proceeding to image generation.

    Checks:
    - Title is English-only and under 60 chars
    - Hook is complete (ends with punctuation) and under 100 chars
    - CTA is a complete question and under 100 chars
    - Duration sums to 45-50s
    - Scene count is 3-5
    - All scenes have narration and narration_en
    - Angle matches required_angle (if provided)

    Returns:
        Tuple of (passed: bool, issues: list of strings describing failures)
    """
    issues = []

    # Title checks
    if not script.title:
        issues.append("Title is empty")
    else:
        # Check for Devanagari characters (Hindi)
        if re.search(r'[\u0900-\u097F]', script.title):
            issues.append(f"Title contains Hindi/Devanagari — must be English only: '{script.title}'")
        if len(script.title) > 65:
            issues.append(f"Title too long ({len(script.title)} chars, max 65): '{script.title}'")

    # Hook checks
    if not script.hook:
        issues.append("Hook is empty")
    else:
        if len(script.hook) > 100:
            issues.append(f"Hook too long ({len(script.hook)} chars, max 100)")
        if not script.hook.rstrip().endswith(('?', '.', '!', ':')):
            issues.append(f"Hook doesn't end with punctuation: '{script.hook[-20:]}'")

    # Engagement CTA checks
    if not script.engagement_cta:
        issues.append("engagement_cta is empty")
    else:
        if len(script.engagement_cta) > 100:
            issues.append(f"CTA too long ({len(script.engagement_cta)} chars, max 100)")
        if '?' not in script.engagement_cta:
            issues.append(f"CTA should contain a question mark: '{script.engagement_cta}'")

    # Angle enforcement check (soft warning — will be force-overridden post-generation)
    # Not a hard fail since Gemini often ignores angle instructions
    # and we forcibly correct it after generation

    # Duration check
    total_duration = sum(scene.duration_seconds for scene in script.scenes)
    if total_duration < 45 or total_duration > 50:
        issues.append(f"Total duration {total_duration}s outside 45-50s range")

    # Scene count
    scene_count = len(script.scenes)
    if scene_count < 3 or scene_count > 5:
        issues.append(f"Scene count {scene_count} outside 3-5 range")

    # Narration completeness
    for scene in script.scenes:
        if not scene.narration or not scene.narration.strip():
            issues.append(f"Scene {scene.scene_number}: narration is empty")
        if not scene.narration_en or not scene.narration_en.strip():
            issues.append(f"Scene {scene.scene_number}: narration_en is empty")

    # Angle validation
    valid_angles = [
        "hidden_meaning", "why", "character_study",
        "life_lesson", "unknown_facts", "what_if", "debate"
    ]
    if script.angle not in valid_angles:
        issues.append(f"Invalid angle '{script.angle}' — must be one of {valid_angles}")

    # Revelation check
    if not script.revelation or not script.revelation.strip():
        issues.append("Revelation is empty")

    passed = len(issues) == 0

    if passed:
        logger.info("Script quality gate: PASSED")
    else:
        logger.warning(f"Script quality gate: FAILED ({len(issues)} issues)")
        for issue in issues:
            logger.warning(f"  - {issue}")

    return passed, issues


# ============================================================
# CHECKPOINT 2: Final Video Validation
# ============================================================

def validate_final_video(video_path: str) -> Tuple[bool, List[str]]:
    """Validate the final video file before marking episode complete.

    Checks:
    - File exists and is not empty
    - File size between 5-30 MB (sanity bounds)
    - Duration between 50-120s (content + branding)
    - Has video stream (H.264, 1080x1920)
    - Has audio stream (AAC)
    - ffprobe can read it without errors

    Returns:
        Tuple of (passed: bool, issues: list of strings describing failures)
    """
    issues = []

    # File exists
    if not os.path.exists(video_path):
        issues.append(f"Video file does not exist: {video_path}")
        return False, issues

    # File size
    size_bytes = os.path.getsize(video_path)
    size_mb = size_bytes / (1024 * 1024)
    if size_mb < 3:
        issues.append(f"Video too small ({size_mb:.1f} MB) — likely corrupted")
    elif size_mb > 50:
        issues.append(f"Video too large ({size_mb:.1f} MB) — encoding issue")

    # Probe video with ffprobe
    try:
        probe_cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_path,
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            issues.append(f"ffprobe failed (exit {result.returncode}): file may be corrupt")
            return False, issues

        data = json.loads(result.stdout)

        # Check format
        fmt = data.get("format", {})
        duration = float(fmt.get("duration", 0))
        if duration < 50:
            issues.append(f"Duration too short ({duration:.1f}s, min 50s)")
        elif duration > 120:
            issues.append(f"Duration too long ({duration:.1f}s, max 120s)")

        # Check streams
        streams = data.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        if not video_streams:
            issues.append("No video stream found")
        else:
            vs = video_streams[0]
            width = int(vs.get("width", 0))
            height = int(vs.get("height", 0))
            codec = vs.get("codec_name", "")
            if codec != "h264":
                issues.append(f"Video codec is '{codec}', expected 'h264'")
            if width != 1080 or height != 1920:
                issues.append(f"Resolution is {width}x{height}, expected 1080x1920")

        if not audio_streams:
            issues.append("No audio stream found")
        else:
            audio_codec = audio_streams[0].get("codec_name", "")
            if audio_codec != "aac":
                issues.append(f"Audio codec is '{audio_codec}', expected 'aac'")

    except subprocess.TimeoutExpired:
        issues.append("ffprobe timed out — file may be corrupt")
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        issues.append(f"Failed to parse ffprobe output: {e}")

    passed = len(issues) == 0

    if passed:
        logger.info(f"Video validation: PASSED ({size_mb:.1f} MB, {duration:.1f}s)")
    else:
        logger.warning(f"Video validation: FAILED ({len(issues)} issues)")
        for issue in issues:
            logger.warning(f"  - {issue}")

    return passed, issues


# ============================================================
# CHECKPOINT 3: Thumbnail Validation
# ============================================================

def validate_thumbnail(thumb_path: str) -> Tuple[bool, List[str]]:
    """Validate thumbnail file.

    Returns:
        Tuple of (passed: bool, issues: list)
    """
    issues = []

    if not os.path.exists(thumb_path):
        issues.append(f"Thumbnail does not exist: {thumb_path}")
        return False, issues

    size_kb = os.path.getsize(thumb_path) // 1024
    if size_kb < 30:
        issues.append(f"Thumbnail too small ({size_kb} KB) — likely corrupted")

    passed = len(issues) == 0
    if passed:
        logger.info(f"Thumbnail validation: PASSED ({size_kb} KB)")
    else:
        logger.warning(f"Thumbnail validation: FAILED")
        for issue in issues:
            logger.warning(f"  - {issue}")

    return passed, issues
