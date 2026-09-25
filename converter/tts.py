"""
tts.py
Synthesizes narration audio using Gemini's native text-to-speech models
(gemini-2.5-flash-preview-tts / gemini-2.5-pro-preview-tts) - the same
Gemini API key used for script writing also drives the voice, so the whole
pipeline runs on one AI provider. Accent, tone, and pace are all steered
with a natural-language instruction, which is how Gemini TTS is designed
to be controlled (there's no separate "rate" parameter like classic TTS
engines).

gemini-2.5-flash-preview-tts works on the free tier. gemini-2.5-pro-preview-tts
is higher quality but requires a paid/billing-enabled API project - set
GEMINI_TTS_MODEL=gemini-2.5-pro-preview-tts in .env if you have that.
"""
import os
import re
import wave

from google import genai
from google.genai import types

from .retry import call_with_retry

# Official Gemini TTS voice list, gender per Google's docs. Kore and Charon
# are solid, clear narrator voices; swap freely from the full list of 30.
VOICE_MAP = {
    "female": "Kore",     # firm, clear
    "male": "Charon",     # calm, informative
}

DEFAULT_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file. "
                "Get a free key at https://aistudio.google.com/apikey"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _pace_instruction(speed: float) -> str:
    if speed >= 1.9:
        return "quickly, at a fast pace, while staying clearly understandable"
    if speed >= 1.4:
        return "at a brisk, noticeably faster-than-normal pace"
    return "at a natural, normal pace"


def _pcm_rate_from_mime(mime_type: str, default: int = 24000) -> int:
    match = re.search(r"rate=(\d+)", mime_type or "")
    return int(match.group(1)) if match else default


def synthesize_to_file(text: str, gender: str, speed: float, out_path: str):
    """
    gender: "male" or "female"
    speed: e.g. 1.0, 1.5, 2.0 (matches the UI's 1x/1.5x/2x) - steered via
    natural-language instruction since Gemini TTS has no numeric rate knob.
    Writes a WAV file to out_path.
    """
    voice_name = VOICE_MAP.get(gender, VOICE_MAP["female"])
    pace = _pace_instruction(speed)

    prompt = (
        f"Say the following in a warm, natural Indian English accent, "
        f"{pace}, in a clear and engaging narrator tone. Narrate it exactly "
        f"as written, without adding or skipping any words:\n\n{text}"
    )

    def _call():
        return _get_client().models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                ),
            ),
        )

    def _call_and_extract():
        response = _call()
        candidates = getattr(response, "candidates", None)
        if not candidates or candidates[0].content is None:
            reason = candidates[0].finish_reason if candidates else "no candidates"
            raise RuntimeError(f"EMPTY_TTS_RESPONSE: Gemini returned no audio (reason: {reason})")
        return response

    response = call_with_retry(_call_and_extract)

    part = response.candidates[0].content.parts[0]
    pcm_data = part.inline_data.data
    sample_rate = _pcm_rate_from_mime(getattr(part.inline_data, "mime_type", ""))

    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)

    return out_path