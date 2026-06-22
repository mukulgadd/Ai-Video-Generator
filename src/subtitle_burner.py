"""Subtitle Burner — Burns Hindi text onto keyframe images using Pillow.

Adds narration text as subtitles at the bottom of each keyframe image
before Ken Burns composition. This avoids needing FFmpeg's drawtext filter.
"""

import logging
import os
import textwrap
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Font settings
FONT_SIZE = 42
LINE_SPACING = 12
MAX_CHARS_PER_LINE = 30  # English characters per line
PADDING_BOTTOM = 80
PADDING_SIDES = 40
BG_OPACITY = 160  # Semi-transparent black background (0-255)
TEXT_COLOR = (255, 255, 255)  # White text
OUTLINE_COLOR = (0, 0, 0)  # Black outline
OUTLINE_WIDTH = 3

# Devanagari font path on macOS
FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
    "/System/Library/Fonts/Supplemental/ITFDevanagari.ttc",
    "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",
    "/Library/Fonts/NotoSansDevanagari-Regular.ttf",
]


def _get_font(size: int = FONT_SIZE) -> ImageFont.FreeTypeFont:
    """Load a Devanagari-capable font."""
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Fallback to default (won't render Hindi properly but won't crash)
    logger.warning("No Devanagari font found, using default")
    return ImageFont.load_default()


def burn_subtitle_on_image(
    image_path: str,
    text: str,
    output_path: Optional[str] = None,
    max_chars_per_line: int = MAX_CHARS_PER_LINE,
) -> str:
    """Burn subtitle text onto an image.

    Adds a semi-transparent black bar at the bottom with white Hindi text.

    Args:
        image_path: Path to the source image.
        text: The subtitle text (Hindi/Devanagari).
        output_path: Where to save. If None, overwrites the source.
        max_chars_per_line: Max characters per line before wrapping.

    Returns:
        Path to the output image.
    """
    if not text or not text.strip():
        return image_path

    if output_path is None:
        output_path = image_path

    img = Image.open(image_path).convert("RGBA")
    width, height = img.size

    # Wrap text
    lines = textwrap.wrap(text, width=max_chars_per_line)
    if not lines:
        return image_path

    # Load font
    font = _get_font(FONT_SIZE)

    # Calculate text block dimensions
    line_heights = []
    line_widths = []
    for line in lines:
        bbox = font.getbbox(line)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    total_text_height = sum(line_heights) + LINE_SPACING * (len(lines) - 1)
    max_line_width = max(line_widths)

    # Draw semi-transparent background bar (lower third area)
    bar_height = total_text_height + PADDING_BOTTOM
    bar_top = height - bar_height - 60  # Positioned in lower third

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(
        [(0, bar_top - 10), (width, bar_top + bar_height + 10)],
        fill=(0, 0, 0, BG_OPACITY),
    )

    # Draw text with outline for better readability
    y = bar_top + (bar_height - total_text_height) // 2
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2

        # Draw outline (draw text in black slightly offset in all directions)
        for dx in range(-OUTLINE_WIDTH, OUTLINE_WIDTH + 1):
            for dy in range(-OUTLINE_WIDTH, OUTLINE_WIDTH + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font,
                              fill=OUTLINE_COLOR + (255,))

        # Draw main text
        draw.text((x, y), line, font=font, fill=TEXT_COLOR + (255,))
        y += line_heights[i] + LINE_SPACING

    # Composite
    result = Image.alpha_composite(img, overlay)
    result = result.convert("RGB")
    result.save(output_path)

    return output_path


def burn_subtitles_on_keyframes(
    keyframe_paths: List[List[str]],
    narration_texts: List[str],
) -> List[List[str]]:
    """Burn subtitles onto all keyframes for each scene.

    Each scene's narration text is burned onto all keyframes of that scene.
    Modifies images in-place.

    Args:
        keyframe_paths: List of lists of keyframe paths per scene.
        narration_texts: List of narration text per scene.

    Returns:
        Same keyframe_paths (modified in-place).
    """
    for scene_idx, (keyframes, narration) in enumerate(
        zip(keyframe_paths, narration_texts)
    ):
        if not narration:
            continue

        # Split narration among keyframes (each keyframe shows a portion)
        words = narration.split()
        words_per_kf = max(1, len(words) // len(keyframes))

        for kf_idx, kf_path in enumerate(keyframes):
            start = kf_idx * words_per_kf
            end = start + words_per_kf if kf_idx < len(keyframes) - 1 else len(words)
            subtitle_text = " ".join(words[start:end])

            burn_subtitle_on_image(kf_path, subtitle_text)
            logger.debug(
                "Burned subtitle on scene %d, keyframe %d: '%s'",
                scene_idx + 1, kf_idx + 1, subtitle_text[:40],
            )

    logger.info("Burned subtitles on %d scenes", len(keyframe_paths))
    return keyframe_paths
