"""Generate a single Ramayan episode.

Runs the full pipeline:
  Gemini (script) → SDXL (keyframes) → Edge TTS (Hindi narration) 
  → Audio mix → Ken Burns composition → Final MP4

Output goes to the output/ directory. Cost: ~₹3-4 per episode.
"""

import logging
import os
import subprocess
import sys
from datetime import date

# ─── Caffeinate: prevent Mac from sleeping during generation ─────────
if sys.platform == "darwin" and not os.environ.get("CAFFEINATED"):
    os.environ["CAFFEINATED"] = "1"
    os.execvp("caffeinate", ["caffeinate", "-is"] + [sys.executable] + sys.argv)

from dotenv import load_dotenv
load_dotenv()

from src.config_loader import load_config
from src.gemini_llm_client import GeminiLLMClient
from src.flux_image_generator import FluxImageGenerator
# from src.sd_image_generator import SDXLImageGenerator  # Commented out — using FLUX instead
from src.animation_engine import AnimationEngine
from src.narration_engine import NarrationEngine
from src.audio_engine import AudioEngine
from src.script_engine import ScriptEngine
from src.story_manager import StoryManager
from src.ken_burns_compositor import compose_ken_burns_video
from src.subtitle_burner import burn_subtitles_on_keyframes
from src.video_branding import add_branding_to_video
from src.thumbnail_generator import generate_thumbnail
from src.youtube_metadata import generate_youtube_metadata, save_metadata_to_file
from src.quality_gates import validate_script_quality, validate_final_video, validate_thumbnail


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    config = load_config("config.yaml")

    # Components
    story_manager = StoryManager(db_path="ramayan_db")
    script_engine = ScriptEngine(
        llm_client=GeminiLLMClient(), model="gemini-2.5-flash", temperature=0.7
    )
    animation_engine = AnimationEngine(
        config=config.animation, image_generator=FluxImageGenerator(num_inference_steps=4)
    )
    # # SDXL fallback:
    # animation_engine = AnimationEngine(
    #     config=config.animation, image_generator=SDXLImageGenerator(num_inference_steps=15)
    # )
    narration_engine = NarrationEngine(config=config.narration)
    audio_engine = AudioEngine(config=config.audio)

    # 1. Get story segment
    logger.info("Getting next story segment...")
    video_index = story_manager.get_current_position().current_video_index
    segment = story_manager.get_next_segment()
    episode_num = story_manager.get_current_position().total_episodes_completed + 1
    logger.info(f"Episode {episode_num}: {segment.title} (Kanda: {segment.kanda_name}, Video {video_index + 1})")

    # 2. Generate script (with quality gate retry)
    logger.info("Generating script via Gemini...")
    required_angle = script_engine._get_required_angle(segment, video_index)
    logger.info(f"Required angle: {required_angle}")

    # Collect previous episode titles to avoid repetition
    import glob
    previous_titles = []
    for meta_file in sorted(glob.glob("output/ramayan_e*_metadata.txt")):
        try:
            with open(meta_file) as f:
                first_line = f.readline().strip()
                if first_line.startswith("TITLE:"):
                    previous_titles.append(first_line[6:].strip())
        except Exception:
            pass

    script = None
    for script_attempt in range(3):
        candidate = script_engine.generate_script(
            segment, episode_number=episode_num, video_index=video_index,
            previous_titles=previous_titles,
        )
        passed, issues = validate_script_quality(candidate, required_angle=required_angle)
        if passed:
            script = candidate
            break
        else:
            logger.warning(f"Script attempt {script_attempt + 1}/3 failed quality gate. Retrying...")
            if script_attempt == 2:
                logger.error("All 3 script attempts failed quality gate. Using last attempt.")
                script = candidate

    # Force-override the angle to match what was required (Gemini often ignores this)
    if script.angle != required_angle:
        logger.warning(f"Forcing angle from '{script.angle}' to '{required_angle}'")
        script.angle = required_angle

    logger.info(f"Script: {len(script.scenes)} scenes, {script.total_duration_seconds}s")
    logger.info(f"Angle: {script.angle} | Title: {script.title}")
    logger.info(f"Hook: {script.hook}")
    logger.info(f"Revelation: {script.revelation}")
    logger.info(f"CTA: {script.engagement_cta}")

    # 3. Generate keyframes (SDXL on CPU — free, ~4 min per image)
    logger.info("Generating keyframes via SDXL (this takes a while on CPU)...")
    episode_frames = animation_engine.generate_episode_frames(script)
    frames_dir = os.path.dirname(episode_frames.scene_frames[0].keyframes[0].path)
    frames_dir = os.path.dirname(frames_dir)
    logger.info(f"Keyframes generated in: {frames_dir}")

    # 4. Generate Hindi narration (Edge TTS — free)
    logger.info("Generating Hindi narration via Edge TTS...")
    episode_audio = narration_engine.generate_episode_audio(script)
    logger.info(f"Narration: {episode_audio.total_duration_seconds:.1f}s")

    # 5. Mix audio
    logger.info("Mixing audio...")
    audio_path = f"output/episode_{episode_num:04d}_audio.wav"
    audio_engine.produce_episode_audio(script, episode_audio, audio_path)
    logger.info(f"Audio exported: {audio_path}")

    # 6. Burn English subtitles onto keyframes
    logger.info("Burning English subtitles onto keyframes...")
    narration_texts = [scene.narration_en or scene.narration for scene in script.scenes]

    # Collect keyframe paths per scene
    keyframe_paths = []
    for sf in episode_frames.scene_frames:
        keyframe_paths.append([kf.path for kf in sf.keyframes])

    burn_subtitles_on_keyframes(keyframe_paths, narration_texts)

    # 7. Compose video with Ken Burns effects
    logger.info("Composing Ken Burns video...")

    # Scene durations — use actual narration lengths (not script targets)
    # so video always matches audio. Narration engine already speed-adjusts
    # to stay close to targets, but actual duration is what matters for sync.
    scene_durations = [
        sa.total_duration_seconds for sa in episode_audio.scene_audio
    ]

    # Output filename
    kanda_slug = segment.kanda_name.lower().replace(" ", "_")
    today = date.today().strftime("%Y%m%d")
    output_path = f"output/ramayan_e{episode_num:04d}_{kanda_slug}_{today}.mp4"

    compose_ken_burns_video(
        keyframe_paths=keyframe_paths,
        scene_durations=scene_durations,
        audio_path=audio_path,
        output_path=output_path,
    )

    # 8. Add branding (hook + title card + end CTA)
    logger.info("Adding branding (hook, title card, end CTA)...")
    # Use the dedicated hook field from the explainer script (falls back to scene 1 narration)
    hook_text = script.hook or (script.scenes[0].narration_en[:80] if script.scenes[0].narration_en else segment.title)
    first_keyframe = keyframe_paths[0][0] if keyframe_paths and keyframe_paths[0] else None
    branded_path = output_path.replace(".mp4", "_branded.mp4")
    add_branding_to_video(
        input_video=output_path,
        output_video=branded_path,
        episode_number=episode_num,
        episode_title=script.title,  # Use the engaging explainer title
        kanda_name=segment.kanda_name,
        hook_text=hook_text,
        engagement_cta=script.engagement_cta or "",
        angle=script.angle or "",
        first_keyframe_path=first_keyframe,
    )
    # Replace original with branded version
    os.remove(output_path)
    os.rename(branded_path, output_path)

    # 9. Generate YouTube thumbnail
    logger.info("Generating YouTube thumbnail...")
    thumb_path = f"output/ramayan_e{episode_num:04d}_thumbnail.jpg"
    generate_thumbnail(
        hook_text=hook_text,
        episode_number=episode_num,
        kanda_name=segment.kanda_name,
        angle=script.angle or "",
        keyframe_path=first_keyframe,
        output_path=thumb_path,
    )
    logger.info(f"   Thumbnail: {thumb_path}")

    # 10. Generate YouTube metadata (title, description, tags)
    logger.info("Generating YouTube metadata...")
    yt_metadata = generate_youtube_metadata(script, segment.kanda_name)
    meta_path = f"output/ramayan_e{episode_num:04d}_metadata.txt"
    save_metadata_to_file(yt_metadata, meta_path)
    logger.info(f"   Metadata: {meta_path}")
    logger.info(f"   YT Title: {yt_metadata.title}")

    # Final info
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", output_path],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip())

    logger.info(f"✅ Episode {episode_num} generated!")
    logger.info(f"   Title: {segment.title}")
    logger.info(f"   File: {output_path}")
    logger.info(f"   Size: {size_mb:.1f} MB")
    logger.info(f"   Duration: {duration:.1f}s")

    # Validate final video before marking complete
    video_passed, video_issues = validate_final_video(output_path)
    if not video_passed:
        logger.error("Final video validation FAILED — not marking episode complete")
        for issue in video_issues:
            logger.error(f"  - {issue}")
        sys.exit(1)

    # Validate thumbnail
    thumb_passed, _ = validate_thumbnail(thumb_path)
    if not thumb_passed:
        logger.warning("Thumbnail validation failed — video is fine, thumbnail may need regen")

    # Mark episode complete (only advances counter on success)
    try:
        story_manager.mark_episode_complete(
            episode_id=episode_num,
            output_path=output_path,
        )
        logger.info(f"   Story position advanced to next segment.")
    except Exception as e:
        logger.warning(f"   Could not update episode record: {e} (video is fine)")


if __name__ == "__main__":
    main()
