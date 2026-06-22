"""Compose video from existing frames + audio.

Uses the frames already generated in /tmp and the audio in output/
to produce the final MP4 using ffmpeg directly.
"""

import subprocess
import os

FRAMES_DIR = "/var/folders/dd/31jnd_hd3xv_h0r0yl42xqr40000gp/T/ramayan_frames_lzdujph0"
AUDIO_FILE = "output/episode_0001_audio.wav"
OUTPUT_FILE = "output/ramayan_e0001_bala_kanda_20260613.mp4"

FPS = 24
RESOLUTION = "1080x1920"


def main():
    # Create a concat file listing all scene frame sequences
    scenes = sorted(os.listdir(FRAMES_DIR))
    print(f"Found {len(scenes)} scenes: {scenes}")

    # First, encode each scene into a video clip
    scene_clips = []
    for scene_dir in scenes:
        scene_path = os.path.join(FRAMES_DIR, scene_dir)
        if not os.path.isdir(scene_path):
            continue

        frames = sorted(os.listdir(scene_path))
        num_frames = len(frames)
        print(f"  {scene_dir}: {num_frames} frames")

        # Create a clip for this scene using ffmpeg's image sequence input
        clip_path = f"/tmp/ramayan_clip_{scene_dir}.mp4"
        scene_clips.append(clip_path)

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", os.path.join(scene_path, "%*.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "23",
            clip_path,
        ]

        # Use glob pattern for frames
        # ffmpeg needs a proper pattern, so let's use a file list
        frame_list_path = f"/tmp/ramayan_framelist_{scene_dir}.txt"
        with open(frame_list_path, "w") as f:
            for frame in frames:
                f.write(f"file '{os.path.join(scene_path, frame)}'\n")
                f.write(f"duration {1.0/FPS}\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", frame_list_path,
            "-vf", f"scale={RESOLUTION.replace('x', ':')}:force_original_aspect_ratio=decrease,pad={RESOLUTION.replace('x', ':')}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "23",
            "-r", str(FPS),
            clip_path,
        ]

        print(f"  Encoding {scene_dir}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr[-500:]}")
            return
        print(f"  Done: {clip_path}")

    # Concatenate all scene clips
    concat_list = "/tmp/ramayan_concat.txt"
    with open(concat_list, "w") as f:
        for clip in scene_clips:
            f.write(f"file '{clip}'\n")

    # Concat video + mix with audio
    print("\nConcatenating scenes and adding audio...")
    concat_video = "/tmp/ramayan_concat_video.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        concat_video,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR concatenating: {result.stderr[-500:]}")
        return

    # Add audio track
    print("Adding audio track...")
    cmd = [
        "ffmpeg", "-y",
        "-i", concat_video,
        "-i", AUDIO_FILE,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        OUTPUT_FILE,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR adding audio: {result.stderr[-500:]}")
        return

    # Get file info
    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"\n✅ SUCCESS! Video generated:")
    print(f"   File: {OUTPUT_FILE}")
    print(f"   Size: {size_mb:.1f} MB")

    # Get duration
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", OUTPUT_FILE]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        duration = float(result.stdout.strip())
        print(f"   Duration: {duration:.1f}s")


if __name__ == "__main__":
    main()
