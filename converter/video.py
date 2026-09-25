"""
video.py
Combines each slide's still image with its narration audio into a short
clip, then concatenates all clips into the final MP4.
"""
import subprocess
import os


def get_audio_duration(audio_path: str) -> float:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path,
        ],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


# ffprobe reads duration off any media container, so this works for the
# final assembled video too.
get_video_duration = get_audio_duration


def extract_last_frame(video_path: str, out_image_path: str):
    """Grabs the final frame of a video, used to freeze-pad short videos."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-sseof", "-1", "-i", video_path,
            "-vframes", "1", out_image_path,
        ],
        check=True, capture_output=True,
    )
    return out_image_path


def make_silence_clip(image_path: str, duration_seconds: float, out_path: str):
    """A still image held on screen with silent audio, for padding out the tail."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=24000",
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                   "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-t", str(max(0.1, duration_seconds)),
            out_path,
        ],
        check=True, capture_output=True,
    )
    return out_path


def make_slide_clip(image_path: str, audio_path: str, out_path: str):
    """One slide's image, held on screen for exactly as long as its audio."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                   "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-shortest",
            out_path,
        ],
        check=True, capture_output=True,
    )
    return out_path


def concat_clips(clip_paths, out_path, list_file_path):
    with open(list_file_path, "w") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file_path, "-c", "copy", out_path,
        ],
        check=True, capture_output=True,
    )
    return out_path
