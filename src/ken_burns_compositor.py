"""Ken Burns Video Compositor.

Composes final video from keyframes using zoom/pan effects via FFmpeg.
Each keyframe gets a slow zoom or pan animation, creating dynamic motion
from static images. No frame interpolation needed.

This replaces the frame-sequence approach with a much more watchable result.
"""

import logging
import os
import random
import subprocess
import tempfile
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Ken Burns effect types
EFFECTS = [
    "zoom_in",       # Slow zoom toward center
    "zoom_out",      # Start zoomed, pull back
    "pan_left",      # Slow pan from right to left
    "pan_right",     # Slow pan from left to right
    "pan_up",        # Slow pan from bottom to top
    "zoom_in_top",   # Zoom into top portion
    "zoom_in_bottom",  # Zoom into bottom portion
]


def _get_zoompan_filter(
    effect: str,
    duration_seconds: float,
    width: int = 1080,
    height: int = 1920,
    fps: int = 24,
) -> str:
    """Generate FFmpeg zoompan filter string for a given effect.

    The zoompan filter works on a per-frame basis:
    - z: zoom level (1.0 = no zoom)
    - x, y: top-left corner of the visible area
    - d: total number of frames
    - s: output size
    """
    total_frames = int(duration_seconds * fps)
    s = f"{width}x{height}"

    if effect == "zoom_in":
        # Zoom from 1.0 to 1.3 centered
        return (
            f"zoompan=z='1+0.3*on/{total_frames}':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={s}:fps={fps}"
        )
    elif effect == "zoom_out":
        # Zoom from 1.3 to 1.0 centered
        return (
            f"zoompan=z='1.3-0.3*on/{total_frames}':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={s}:fps={fps}"
        )
    elif effect == "pan_left":
        # Pan from right to left (x decreases)
        return (
            f"zoompan=z=1.2:"
            f"x='iw*0.2*(1-on/{total_frames})':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={s}:fps={fps}"
        )
    elif effect == "pan_right":
        # Pan from left to right (x increases)
        return (
            f"zoompan=z=1.2:"
            f"x='iw*0.2*on/{total_frames}':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={s}:fps={fps}"
        )
    elif effect == "pan_up":
        # Pan from bottom to top
        return (
            f"zoompan=z=1.2:"
            f"x='iw/2-(iw/zoom/2)':y='ih*0.2*(1-on/{total_frames})':"
            f"d={total_frames}:s={s}:fps={fps}"
        )
    elif effect == "zoom_in_top":
        # Zoom into top third
        return (
            f"zoompan=z='1+0.3*on/{total_frames}':"
            f"x='iw/2-(iw/zoom/2)':y='ih*0.1':"
            f"d={total_frames}:s={s}:fps={fps}"
        )
    elif effect == "zoom_in_bottom":
        # Zoom into bottom third
        return (
            f"zoompan=z='1+0.3*on/{total_frames}':"
            f"x='iw/2-(iw/zoom/2)':y='ih*0.4':"
            f"d={total_frames}:s={s}:fps={fps}"
        )
    else:
        # Default: gentle zoom in
        return (
            f"zoompan=z='1+0.2*on/{total_frames}':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={s}:fps={fps}"
        )


def compose_ken_burns_video(
    keyframe_paths: List[List[str]],
    scene_durations: List[float],
    audio_path: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    fps: int = 24,
    crossfade_seconds: float = 0.5,
) -> str:
    """Compose a video with Ken Burns effects from keyframes.

    Args:
        keyframe_paths: List of lists — each inner list contains keyframe
            file paths for one scene.
        scene_durations: Duration in seconds for each scene.
        audio_path: Path to the final mixed audio WAV.
        output_path: Where to save the final MP4.
        width: Output video width.
        height: Output video height.
        fps: Output frame rate.
        crossfade_seconds: Crossfade duration between clips.

    Returns:
        The output file path.
    """
    logger.info("Composing Ken Burns video: %d scenes", len(keyframe_paths))

    scene_clips = []
    temp_dir = tempfile.mkdtemp(prefix="ken_burns_")

    for scene_idx, (keyframes, duration) in enumerate(
        zip(keyframe_paths, scene_durations)
    ):
        if not keyframes:
            continue

        # Split scene duration equally among keyframes
        num_kf = len(keyframes)
        per_kf_duration = duration / num_kf

        for kf_idx, kf_path in enumerate(keyframes):
            # Pick a random effect (different for each keyframe)
            effect = random.choice(EFFECTS)
            clip_path = os.path.join(
                temp_dir, f"scene_{scene_idx:03d}_kf_{kf_idx:02d}.mp4"
            )

            # Build FFmpeg command with zoompan filter
            zp_filter = _get_zoompan_filter(
                effect, per_kf_duration, width, height, fps
            )

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", kf_path,
                "-vf", zp_filter,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "fast",
                "-crf", "24",
                "-t", str(per_kf_duration),
                clip_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(
                    "FFmpeg zoompan failed for scene %d kf %d: %s",
                    scene_idx, kf_idx, result.stderr[-200:]
                )
                # Fallback: static image for duration
                cmd_fallback = [
                    "ffmpeg", "-y",
                    "-loop", "1", "-i", kf_path,
                    "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-preset", "fast", "-crf", "24",
                    "-t", str(per_kf_duration),
                    "-r", str(fps),
                    clip_path,
                ]
                subprocess.run(cmd_fallback, capture_output=True)

            scene_clips.append(clip_path)
            logger.info(
                "  Scene %d, keyframe %d: %s effect, %.1fs",
                scene_idx + 1, kf_idx + 1, effect, per_kf_duration,
            )

    # Concatenate all clips
    concat_list_path = os.path.join(temp_dir, "concat.txt")
    with open(concat_list_path, "w") as f:
        for clip in scene_clips:
            f.write(f"file '{clip}'\n")

    concat_video = os.path.join(temp_dir, "concat_video.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        concat_video,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Concat failed: %s", result.stderr[-300:])
        raise RuntimeError(f"Video concat failed: {result.stderr[-200:]}")

    # Add audio
    cmd = [
        "ffmpeg", "-y",
        "-i", concat_video,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Audio mux failed: %s", result.stderr[-300:])
        raise RuntimeError(f"Audio mux failed: {result.stderr[-200:]}")

    # Get final info
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", output_path],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
    size_mb = os.path.getsize(output_path) / (1024 * 1024)

    logger.info("✅ Ken Burns video complete: %s (%.1f MB, %.1fs)", output_path, size_mb, duration)

    # Cleanup temp clips
    for clip in scene_clips:
        os.remove(clip)
    os.remove(concat_list_path)
    os.remove(concat_video)
    os.rmdir(temp_dir)

    return output_path
