"""
retry.py
Gemini's preview models (especially the TTS ones) periodically return
503 UNAVAILABLE / "high demand" errors that clear up within seconds. This
wraps a call with a few retries and exponential backoff instead of failing
the whole conversion job over a transient blip.
"""
import time

TRANSIENT_MARKERS = ("503", "UNAVAILABLE", "high demand", "429", "RESOURCE_EXHAUSTED", "EMPTY_TTS_RESPONSE")


def is_transient(error: Exception) -> bool:
    text = str(error)
    return any(marker in text for marker in TRANSIENT_MARKERS)


def call_with_retry(fn, *args, max_attempts=7, base_delay=5, on_retry=None, **kwargs):
    """
    Calls fn(*args, **kwargs). If it raises a transient-looking error,
    waits (base_delay * 2^attempt) seconds and tries again, up to
    max_attempts total tries. Re-raises the last error if all attempts fail.
    on_retry(attempt, wait_seconds, error), if given, is called before each wait
    (handy for updating a job's progress message).
    """
    last_error = None
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            if not is_transient(e) or attempt == max_attempts - 1:
                raise
            wait_seconds = base_delay * (2 ** attempt)
            if on_retry:
                on_retry(attempt + 1, wait_seconds, e)
            time.sleep(wait_seconds)
    raise last_error
