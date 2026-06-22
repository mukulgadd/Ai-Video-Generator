"""Video Branding — Adds hook, title card, end CTA, and transitions.

Creates branded intro/outro frames using Pillow, then prepends/appends
them to the video using FFmpeg.
"""

import logging
import os
import subprocess
import tempfile
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Brand settings
CHANNEL_NAME = "सनातन रहस्य"
CHANNEL_NAME_EN = "Sanatan Rahasya"
WIDTH = 1080
HEIGHT = 1920
FPS = 24

# Font paths
FONT_PATHS_DEVANAGARI = [
    "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
    "/System/Library/Fonts/Supplemental/ITFDevanagari.ttc",
]
FONT_PATHS_ENGLISH = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]


def _get_font(size: int, devanagari: bool = True) -> ImageFont.FreeTypeFont:
    """Load appropriate font."""
    paths = FONT_PATHS_DEVANAGARI if devanagari else FONT_PATHS_ENGLISH
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _create_title_card(
    episode_number: int,
    episode_title: str,
    kanda_name: str,
    output_path: str,
    angle: str = "",
) -> str:
    """Create a title card with episode info, channel branding, and angle badge."""
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(20, 10, 5))
    draw = ImageDraw.Draw(img)

    # Decorative border
    border = 40
    draw.rectangle(
        [(border, border), (WIDTH - border, HEIGHT - border)],
        outline=(180, 140, 60),
        width=3,
    )
    draw.rectangle(
        [(border + 10, border + 10), (WIDTH - border - 10, HEIGHT - border - 10)],
        outline=(180, 140, 60),
        width=1,
    )

    # Channel name at top
    font_channel = _get_font(42, devanagari=True)
    bbox = font_channel.getbbox(CHANNEL_NAME)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 200), CHANNEL_NAME, font=font_channel, fill=(255, 215, 0))

    # English channel name below
    font_en = _get_font(28, devanagari=False)
    bbox = font_en.getbbox(CHANNEL_NAME_EN)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 260), CHANNEL_NAME_EN, font=font_en, fill=(200, 180, 120))

    # Divider line
    draw.line([(200, 350), (WIDTH - 200, 350)], fill=(180, 140, 60), width=2)

    # Angle badge (if provided)
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
        font_badge = _get_font(26, devanagari=False)
        bbox = font_badge.getbbox(badge_text)
        badge_w = bbox[2] - bbox[0] + 40
        badge_h = bbox[3] - bbox[1] + 20
        badge_x = (WIDTH - badge_w) // 2
        badge_y = 420
        # Badge background (rounded rect approximation)
        draw.rectangle(
            [(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)],
            fill=(180, 50, 50),
        )
        draw.text(
            (badge_x + 20, badge_y + 8), badge_text,
            font=font_badge, fill=(255, 255, 255),
        )

    # Kanda name
    font_kanda = _get_font(34, devanagari=False)
    bbox = font_kanda.getbbox(kanda_name)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 550), kanda_name, font=font_kanda, fill=(200, 180, 120))

    # Episode number
    font_ep = _get_font(48, devanagari=False)
    ep_text = f"Episode {episode_number}"
    bbox = font_ep.getbbox(ep_text)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 620), ep_text, font=font_ep, fill=(255, 255, 255))

    # Episode title — the engaging explainer title (English, larger and prominent)
    import textwrap
    font_title = _get_font(46, devanagari=False)
    lines = textwrap.wrap(episode_title, width=24)
    y = 780
    for line in lines:
        bbox = font_title.getbbox(line)
        tw = bbox[2] - bbox[0]
        # Shadow
        draw.text(((WIDTH - tw) // 2 + 2, y + 2), line, font=font_title, fill=(0, 0, 0))
        # Main text in gold
        draw.text(((WIDTH - tw) // 2, y), line, font=font_title, fill=(255, 215, 0))
        y += 62

    # Bottom decoration
    draw.line([(200, HEIGHT - 350), (WIDTH - 200, HEIGHT - 350)], fill=(180, 140, 60), width=2)

    # Spiritual tagline at bottom
    font_tagline = _get_font(28, devanagari=True)
    tagline = "जय श्री राम"
    bbox = font_tagline.getbbox(tagline)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, HEIGHT - 280), tagline, font=font_tagline, fill=(200, 180, 120))

    img.save(output_path)
    return output_path


def _create_hook_card(
    hook_text: str,
    output_path: str,
    keyframe_path: Optional[str] = None,
) -> str:
    """Create a hook/teaser frame with bold question text that stops the scroll.

    Uses large text over a darkened/blurred keyframe background (or dramatic
    gradient if no keyframe) to create a visually striking first frame.
    """
    if keyframe_path and os.path.exists(keyframe_path):
        # Use first keyframe as background — darkened and slightly blurred
        bg = Image.open(keyframe_path).convert("RGB")
        bg = bg.resize((WIDTH, HEIGHT), Image.LANCZOS)
        from PIL import ImageFilter
        bg = bg.filter(ImageFilter.GaussianBlur(radius=4))
        # Dark overlay (60% opacity)
        dark = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        img = Image.blend(bg, dark, alpha=0.55)
    else:
        img = Image.new("RGB", (WIDTH, HEIGHT), color=(5, 2, 15))
        # Dramatic radial gradient effect (dark edges, warm center glow)
        draw_temp = ImageDraw.Draw(img)
        for i in range(40):
            alpha = int(15 + i * 2)
            y_center = HEIGHT // 2
            spread = 300 + i * 15
            draw_temp.rectangle(
                [(50 + i * 5, y_center - spread), (WIDTH - 50 - i * 5, y_center + spread)],
                fill=(alpha // 2, alpha // 6, alpha // 3),
            )

    draw = ImageDraw.Draw(img)

    # Subtle top accent line (golden)
    draw.rectangle([(200, 500), (WIDTH - 200, 504)], fill=(255, 185, 0))

    # Hook text — large, bold, centered, with heavy shadow for readability
    import textwrap
    font_hook = _get_font(56, devanagari=False)
    lines = textwrap.wrap(hook_text, width=22)
    line_height = 72
    total_height = len(lines) * line_height
    y = (HEIGHT - total_height) // 2 - 40

    for line in lines:
        bbox = font_hook.getbbox(line)
        tw = bbox[2] - bbox[0]
        x = (WIDTH - tw) // 2

        # Heavy shadow (multiple layers for glow effect)
        for offset in [4, 3, 2]:
            draw.text((x + offset, y + offset), line, font=font_hook, fill=(0, 0, 0))
        # Main text in white
        draw.text((x, y), line, font=font_hook, fill=(255, 255, 255))
        y += line_height

    # Bottom accent line
    draw.rectangle([(200, HEIGHT - 520), (WIDTH - 200, HEIGHT - 516)], fill=(255, 185, 0))

    # "Find out in this video" teaser below hook
    font_teaser = _get_font(30, devanagari=False)
    teaser = "▶ Find out in this video..."
    bbox = font_teaser.getbbox(teaser)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, HEIGHT - 420), teaser, font=font_teaser, fill=(255, 215, 0))

    # Channel watermark at bottom
    font_ch = _get_font(24, devanagari=True)
    bbox = font_ch.getbbox(CHANNEL_NAME)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, HEIGHT - 200), CHANNEL_NAME, font=font_ch, fill=(120, 100, 70))

    img.save(output_path)
    return output_path


def _create_end_card(output_path: str, engagement_cta: str = "") -> str:
    """Create an end card with engagement question and follow CTA.

    Shows the debate/thought question prominently to drive comments,
    then the subscribe/follow CTA below.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(20, 10, 5))
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([(40, 40), (WIDTH - 40, HEIGHT - 40)], outline=(180, 140, 60), width=3)

    # "What do you think?" header
    font_header = _get_font(38, devanagari=False)
    header = "WHAT DO YOU THINK?"
    bbox = font_header.getbbox(header)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 500), header, font=font_header, fill=(255, 185, 0))

    # Accent line below header
    draw.rectangle([(300, 560), (WIDTH - 300, 563)], fill=(180, 140, 60))

    # Engagement CTA question (the main focus of the card)
    if engagement_cta:
        import textwrap
        font_cta_q = _get_font(44, devanagari=False)
        lines = textwrap.wrap(engagement_cta, width=24)
        y = 640
        for line in lines:
            bbox = font_cta_q.getbbox(line)
            tw = bbox[2] - bbox[0]
            # Shadow
            draw.text(((WIDTH - tw) // 2 + 2, y + 2), line, font=font_cta_q, fill=(0, 0, 0))
            draw.text(((WIDTH - tw) // 2, y), line, font=font_cta_q, fill=(255, 255, 255))
            y += 58

    # "Comment below" nudge
    font_comment = _get_font(30, devanagari=False)
    comment_text = "Comment your answer below"
    bbox = font_comment.getbbox(comment_text)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 950), comment_text, font=font_comment, fill=(200, 180, 120))

    # Hindi comment nudge
    font_hi = _get_font(32, devanagari=True)
    text_hi = "अपना जवाब कमेंट में बताइए"
    bbox = font_hi.getbbox(text_hi)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 1010), text_hi, font=font_hi, fill=(200, 180, 120))

    # Divider
    draw.rectangle([(250, 1120), (WIDTH - 250, 1123)], fill=(180, 140, 60))

    # Follow/Subscribe CTA
    font_follow = _get_font(42, devanagari=False)
    follow_text = "FOLLOW FOR MORE"
    bbox = font_follow.getbbox(follow_text)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 1200), follow_text, font=font_follow, fill=(255, 80, 80))

    # "Next revelation tomorrow"
    font_next = _get_font(30, devanagari=False)
    next_text = "Next revelation tomorrow"
    bbox = font_next.getbbox(next_text)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 1280), next_text, font=font_next, fill=(200, 180, 120))

    # Channel name at bottom
    font_ch = _get_font(36, devanagari=True)
    bbox = font_ch.getbbox(CHANNEL_NAME)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 1420), CHANNEL_NAME, font=font_ch, fill=(255, 215, 0))

    # Jai Shri Ram
    font_jsr = _get_font(28, devanagari=True)
    jsr = "जय श्री राम 🙏"
    bbox = font_jsr.getbbox(jsr)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 1490), jsr, font=font_jsr, fill=(200, 180, 120))

    img.save(output_path)
    return output_path


def add_branding_to_video(
    input_video: str,
    output_video: str,
    episode_number: int,
    episode_title: str,
    kanda_name: str,
    hook_text: str,
    engagement_cta: str = "",
    angle: str = "",
    hook_duration: float = 3.0,
    title_duration: float = 4.0,
    end_duration: float = 3.0,
    first_keyframe_path: Optional[str] = None,
) -> str:
    """Add hook, title card, and end CTA to a video.

    Args:
        input_video: Path to the main content video (with Ken Burns + subtitles).
        output_video: Where to save the branded video.
        episode_number: Episode number for title card.
        episode_title: Engaging explainer title for title card.
        kanda_name: Kanda name for title card.
        hook_text: English hook text for the opening card.
        engagement_cta: Comment-triggering question for the end card.
        angle: Content angle type for title card badge.
        hook_duration: How long to show the hook (seconds).
        title_duration: How long to show the title card (seconds).
        end_duration: How long to show the end CTA (seconds).

    Returns:
        Path to the output branded video.
    """
    temp_dir = tempfile.mkdtemp(prefix="branding_")

    # Create card images
    hook_img = os.path.join(temp_dir, "hook.png")
    title_img = os.path.join(temp_dir, "title.png")
    end_img = os.path.join(temp_dir, "end.png")

    _create_hook_card(hook_text, hook_img, keyframe_path=first_keyframe_path)
    _create_title_card(episode_number, episode_title, kanda_name, title_img, angle=angle)
    _create_end_card(end_img, engagement_cta=engagement_cta)

    # Create video clips from static images
    hook_clip = os.path.join(temp_dir, "hook.mp4")
    title_clip = os.path.join(temp_dir, "title.mp4")
    end_clip = os.path.join(temp_dir, "end.mp4")

    for img_path, clip_path, duration in [
        (hook_img, hook_clip, hook_duration),
        (title_img, title_clip, title_duration),
        (end_img, end_clip, end_duration),
    ]:
        # Create video clip with background music (devotional track at low volume)
        music_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "music", "devotional_track1.mp3"
        )
        if os.path.exists(music_path):
            # Use devotional music as background for intro/outro
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", img_path,
                "-i", music_path,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-af", "volume=0.3,afade=t=in:st=0:d=1,afade=t=out:st=" + str(duration - 1) + ":d=1",
                "-preset", "fast", "-crf", "20",
                "-t", str(duration), "-r", str(FPS),
                "-shortest",
                clip_path,
            ]
        else:
            # Fallback: silent audio
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", img_path,
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-preset", "fast", "-crf", "20",
                "-t", str(duration), "-r", str(FPS),
                "-shortest",
                clip_path,
            ]
        subprocess.run(cmd, capture_output=True, check=True)

    # Concatenate: hook + title + main content + end
    concat_list = os.path.join(temp_dir, "concat.txt")
    abs_input = os.path.abspath(input_video)
    with open(concat_list, "w") as f:
        f.write(f"file '{hook_clip}'\n")
        f.write(f"file '{title_clip}'\n")
        f.write(f"file '{abs_input}'\n")
        f.write(f"file '{end_clip}'\n")

    # Concat (copy streams — faster and preserves quality)
    audio_path = os.path.join(temp_dir, "audio.aac")  # unused but needed for cleanup
    concat_video = output_video
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        concat_video,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Concat failed: %s", result.stderr[-200:])
        # Fallback: just copy input
        import shutil
        shutil.copy(input_video, output_video)

    # Cleanup
    for f in [hook_img, title_img, end_img, hook_clip, title_clip, end_clip,
              concat_list]:
        if os.path.exists(f):
            os.remove(f)
    if os.path.exists(audio_path):
        os.remove(audio_path)
    os.rmdir(temp_dir)

    size_mb = os.path.getsize(output_video) / (1024 * 1024)
    logger.info("Branded video: %s (%.1f MB)", output_video, size_mb)
    return output_video
