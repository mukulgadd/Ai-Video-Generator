"""YouTube Thumbnail Generator.

Creates optimized thumbnail images (1280x720) with bold hook text
overlaid on a dramatic background. Designed for maximum click-through rate.

YouTube thumbnail best practices applied:
- High contrast bold text (3-6 words max visible)
- Dramatic background
- Face/expression when possible (from keyframe)
- Brand consistency (channel colors)
"""

import logging
import os
import textwrap
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)

# YouTube thumbnail dimensions
THUMB_WIDTH = 1280
THUMB_HEIGHT = 720

# Brand colors
BG_COLOR = (15, 8, 30)  # Deep dark purple-black
ACCENT_COLOR = (255, 185, 0)  # Gold
TEXT_COLOR = (255, 255, 255)  # White
SHADOW_COLOR = (0, 0, 0)  # Black shadow

# Font paths (macOS)
FONT_PATHS_ENGLISH = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]

FONT_PATHS_DEVANAGARI = [
    "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
    "/System/Library/Fonts/Supplemental/ITFDevanagari.ttc",
]


def _get_font(size: int, devanagari: bool = False) -> ImageFont.FreeTypeFont:
    """Load appropriate font."""
    paths = FONT_PATHS_DEVANAGARI if devanagari else FONT_PATHS_ENGLISH
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_thumbnail(
    hook_text: str,
    episode_number: int,
    kanda_name: str,
    angle: str = "",
    keyframe_path: Optional[str] = None,
    output_path: str = "output/thumbnail.jpg",
) -> str:
    """Generate a YouTube-optimized thumbnail image.

    Creates a 1280x720 thumbnail with:
    - Dramatic dark background (or blurred keyframe if provided)
    - Bold hook question text in large white font
    - Gold accent elements
    - Episode/kanda info subtly placed
    - Angle badge for series branding

    Args:
        hook_text: The scroll-stopping question (displayed large).
        episode_number: Episode number for subtle branding.
        kanda_name: Kanda name for context.
        angle: Content angle for badge.
        keyframe_path: Optional path to a keyframe image to use as background.
        output_path: Where to save the thumbnail.

    Returns:
        Path to the generated thumbnail.
    """
    # Create background
    if keyframe_path and os.path.exists(keyframe_path):
        # Use keyframe as background, heavily darkened and blurred
        bg = Image.open(keyframe_path).convert("RGB")
        bg = bg.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=8))
        # Darken overlay
        dark = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0))
        bg = Image.blend(bg, dark, alpha=0.6)
    else:
        # Gradient background
        bg = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), BG_COLOR)
        draw_bg = ImageDraw.Draw(bg)
        # Subtle radial gradient
        for i in range(30):
            alpha = int(10 + i * 2)
            cx, cy = THUMB_WIDTH // 2, THUMB_HEIGHT // 2
            r = 200 + i * 15
            draw_bg.ellipse(
                [(cx - r, cy - r), (cx + r, cy + r)],
                fill=(alpha // 3, alpha // 8, alpha // 2),
            )

    draw = ImageDraw.Draw(bg)

    # Top accent bar
    draw.rectangle([(0, 0), (THUMB_WIDTH, 4)], fill=ACCENT_COLOR)

    # Angle badge (top-left)
    if angle:
        angle_labels = {
            "hidden_meaning": "HIDDEN MEANING",
            "why": "WHY?",
            "character_study": "CHARACTER STUDY",
            "life_lesson": "LIFE LESSON",
            "unknown_facts": "UNKNOWN FACTS",
            "what_if": "WHAT IF?",
            "debate": "DEBATE",
        }
        badge_text = angle_labels.get(angle, angle.upper())
        font_badge = _get_font(22)
        bbox = font_badge.getbbox(badge_text)
        badge_w = bbox[2] - bbox[0] + 24
        badge_h = bbox[3] - bbox[1] + 12
        draw.rectangle([(20, 20), (20 + badge_w, 20 + badge_h)], fill=(200, 40, 40))
        draw.text((32, 24), badge_text, font=font_badge, fill=(255, 255, 255))

    # Hook text — the main attraction (large, bold, centered)
    # Use smaller font if hook text is long to ensure it fits completely
    if len(hook_text) > 60:
        font_hook = _get_font(48)
        wrap_width = 32
        line_height = 62
    elif len(hook_text) > 40:
        font_hook = _get_font(54)
        wrap_width = 30
        line_height = 68
    else:
        font_hook = _get_font(62)
        wrap_width = 28
        line_height = 78

    lines = textwrap.wrap(hook_text, width=wrap_width)
    # Allow up to 4 lines to show complete text
    lines = lines[:4]
    total_text_height = len(lines) * line_height
    y_start = (THUMB_HEIGHT - total_text_height) // 2 - 20

    for line in lines:
        bbox = font_hook.getbbox(line)
        tw = bbox[2] - bbox[0]
        x = (THUMB_WIDTH - tw) // 2

        # Heavy shadow for readability
        for offset in [5, 4, 3, 2]:
            draw.text((x + offset, y_start + offset), line, font=font_hook, fill=SHADOW_COLOR)
        # Main text
        draw.text((x, y_start), line, font=font_hook, fill=TEXT_COLOR)
        y_start += line_height

    # Bottom bar with episode info
    draw.rectangle([(0, THUMB_HEIGHT - 50), (THUMB_WIDTH, THUMB_HEIGHT)], fill=(0, 0, 0, 180))
    font_info = _get_font(24)
    info_text = f"Ep. {episode_number} | {kanda_name} | Sanatan Rahasya"
    bbox = font_info.getbbox(info_text)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((THUMB_WIDTH - tw) // 2, THUMB_HEIGHT - 40),
        info_text, font=font_info, fill=ACCENT_COLOR,
    )

    # Bottom accent bar
    draw.rectangle([(0, THUMB_HEIGHT - 4), (THUMB_WIDTH, THUMB_HEIGHT)], fill=ACCENT_COLOR)

    # Save as JPEG (YouTube prefers JPEG thumbnails)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bg.save(output_path, "JPEG", quality=92)
    logger.info("Thumbnail generated: %s", output_path)
    return output_path
