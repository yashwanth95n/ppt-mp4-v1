"""
pipeline.py
Ties every step together for one conversion job and tracks progress so the
frontend can poll for status. Jobs run in a background thread so the
upload request returns immediately.
"""
import os
import threading
import traceback
import uuid

from . import extract, script_gen, tts, render, video

JOBS_DIR = os.path.join(os.path.dirname(__file__), "..", "jobs")

MIN_TOTAL_MINUTES = 20  # your requirement: 10 slides -> at least 20 min

# in-memory job store: {job_id: {status, progress, message, output_path, error}}
JOBS = {}


def _job_dir(job_id):
    d = os.path.join(JOBS_DIR, job_id)
    os.makedirs(d, exist_ok=True)
    return d


def start_job(pptx_path, gender, speed, tone="clear and engaging"):
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Queued",
        "output_path": None,
        "error": None,
    }
    t = threading.Thread(
        target=_run_job, args=(job_id, pptx_path, gender, speed, tone), daemon=True
    )
    t.start()
    return job_id


def _update(job_id, **kwargs):
    JOBS[job_id].update(kwargs)


def _run_job(job_id, pptx_path, gender, speed, tone):
    try:
        job_dir = _job_dir(job_id)
        _update(job_id, status="running", progress=2, message="Reading slides...")

        slides = extract.extract_slides(pptx_path)
        n = len(slides)
        if n == 0:
            raise RuntimeError("No slides found in the uploaded file.")

        # Enforce the minimum total video length, split evenly across slides.
        target_seconds_per_slide = max(120, (MIN_TOTAL_MINUTES * 60) / n)

        _update(job_id, progress=8, message=f"Rendering {n} slide images...")
        images = render.render_slides_to_images(pptx_path, os.path.join(job_dir, "images"))
        if len(images) != n:
            # Fall back to whichever is shorter rather than crashing;
            # mismatches can happen with unusual pptx master layouts.
            n = min(n, len(images))
            slides = slides[:n]
            images = images[:n]

        audio_dir = os.path.join(job_dir, "audio")
        clips_dir = os.path.join(job_dir, "clips")
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(clips_dir, exist_ok=True)

        clip_paths = []
        for i, slide in enumerate(slides):
            pct = 10 + int(70 * (i / n))
            _update(job_id, progress=pct, message=f"Writing & voicing slide {i + 1}/{n}...")

            narration = script_gen.generate_narration(
                slide, target_seconds_per_slide, speed, tone
            )
            audio_path = os.path.join(audio_dir, f"slide_{i:02d}.wav")
            tts.synthesize_to_file(narration, gender, speed, audio_path)

            clip_path = os.path.join(clips_dir, f"clip_{i:02d}.mp4")
            video.make_slide_clip(images[i], audio_path, clip_path)
            clip_paths.append(clip_path)

        _update(job_id, progress=85, message="Assembling final video...")
        output_path = os.path.join(job_dir, "output.mp4")
        video.concat_clips(clip_paths, output_path, os.path.join(job_dir, "concat_list.txt"))

        # Gemini TTS's pace is steered by instruction, not an exact numeric
        # rate, so actual narration length can undershoot the target. Pad
        # the tail with a frozen last frame + silence so the video still
        # meets the minimum total length you asked for.
        target_total_seconds = target_seconds_per_slide * n
        actual_duration = video.get_video_duration(output_path)
        if actual_duration < target_total_seconds - 1:
            _update(job_id, progress=95, message="Padding video to reach minimum length...")
            deficit = target_total_seconds - actual_duration
            last_frame = os.path.join(job_dir, "last_frame.png")
            video.extract_last_frame(output_path, last_frame)
            pad_clip = os.path.join(job_dir, "pad_clip.mp4")
            video.make_silence_clip(last_frame, deficit, pad_clip)
            padded_output = os.path.join(job_dir, "output_padded.mp4")
            video.concat_clips(
                [output_path, pad_clip], padded_output,
                os.path.join(job_dir, "concat_list_padded.txt"),
            )
            output_path = padded_output

        _update(
            job_id, status="done", progress=100,
            message="Done", output_path=output_path,
        )
    except Exception as e:
        traceback.print_exc()
        _update(job_id, status="error", message=str(e), error=str(e))


def get_job(job_id):
    return JOBS.get(job_id)
