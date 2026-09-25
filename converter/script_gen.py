"""
script_gen.py
Turns a slide's raw title/body/notes into a spoken narration script long
enough to fill its target on-screen duration, using the Google Gemini API
free tier (no credit card required - see README for how to get a key).

Why word count depends on speed: the video's total minimum length (e.g. 20
minutes for a 10-slide deck) must hold regardless of which playback speed
the user picks. If the voice will speak faster (2x), the script needs MORE
words so it still takes the same number of seconds to say out loud.
"""
import os
from google import genai

from .retry import call_with_retry

BASE_WORDS_PER_MINUTE = 140  # average natural speaking pace at 1x
MODEL_NAME = "gemini-3.5-flash"  # fast + generous free-tier quota

client = None


def _get_client():
    global client
    if client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file. "
                "Get a free key at https://aistudio.google.com/apikey"
            )
        client = genai.Client(api_key=api_key)
    return client


def words_needed(target_seconds: float, speed: float) -> int:
    minutes = target_seconds / 60.0
    return max(60, round(minutes * BASE_WORDS_PER_MINUTE * speed))


def generate_narration(slide, target_seconds, speed, tone="clear and engaging"):
    """
    slide: dict from extract.extract_slides()
    target_seconds: how long this slide's audio should run
    speed: the playback speed multiplier the user picked (1.0, 1.5, 2.0 ...)
    Returns: narration text (plain sentences, no stage directions).
    """
    target_words = words_needed(target_seconds, speed)

    source = f"Slide title: {slide['title']}\n"
    if slide["body_text"]:
        source += f"On-slide bullet points:\n{slide['body_text']}\n"
    if slide["notes"]:
        source += f"Speaker notes from the author:\n{slide['notes']}\n"
    if not slide["body_text"] and not slide["notes"]:
        source += "(No extra detail was provided beyond the title - " \
                   "expand on what a presenter would plausibly say here.)\n"

    prompt = f"""You are writing a voiceover script for one slide of a narrated
presentation video. Write in a {tone} tone, in plain natural spoken
sentences (no bullet points, no "slide 1", no stage directions, no markdown).

Target length: approximately {target_words} words. This is important -
the audio needs to run about {round(target_seconds)} seconds, so stay close
to the target word count (do not undershoot by more than 10%).

Slide content to narrate:
{source}

Write only the narration text itself, nothing else."""

    def _call():
        return _get_client().models.generate_content(model=MODEL_NAME, contents=prompt)

    resp = call_with_retry(_call)
    return resp.text.strip()
