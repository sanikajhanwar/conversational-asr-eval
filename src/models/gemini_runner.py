"""Gemini 2.5 Flash as ASR — frontier LLM with native audio input.

Unlike Deepgram/Sarvam/ElevenLabs which are dedicated speech-recognition systems,
Gemini is a general-purpose multimodal LLM. Including it here answers an interesting
question: does a frontier LLM with audio input beat dedicated ASR on Indian speech?

Docs: https://ai.google.dev/gemini-api/docs/audio
Get key: https://aistudio.google.com/apikey
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from . import TranscriptionResult

load_dotenv()

MODEL_NAME = "gemini"
# Default is overridable via env var GEMINI_MODEL_ID — useful when the free-tier
# quota on `gemini-2.5-flash` is exhausted; `gemini-2.5-flash-lite` has higher RPM
# and a separate daily bucket.
DEFAULT_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash")

# Minimum spacing between calls so we don't trip per-minute rate limits.
# flash:      5 RPM free   → 13s spacing
# flash-lite: 15 RPM free  → 5s spacing
_MIN_INTERVAL_S = float(os.getenv("GEMINI_MIN_INTERVAL_S", "5"))
_last_call_ts: float = 0.0

_TRANSCRIBE_PROMPT = (
    "Transcribe this audio clip verbatim, in whatever language(s) the speaker uses. "
    "If the speaker code-switches between Hindi, English, Kannada or any other "
    "language, preserve that exactly as spoken. Use the original script for each "
    "language (Devanagari for Hindi, Latin for English, Kannada script for Kannada). "
    "Output ONLY the transcript text — no preamble, no commentary, no language tags."
)

_MIME = {
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
}


def _throttle() -> None:
    """Sleep so consecutive calls respect _MIN_INTERVAL_S spacing (per-process)."""
    global _last_call_ts
    now = time.perf_counter()
    wait = _MIN_INTERVAL_S - (now - _last_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_call_ts = time.perf_counter()


def transcribe(
    audio_path: Path,
    model_id: str = DEFAULT_MODEL_ID,
    max_retries: int = 2,
) -> TranscriptionResult:
    """Transcribe one audio file via Gemini (default: gemini-2.5-flash).

    Honors per-minute rate-limit spacing via _MIN_INTERVAL_S, and retries once
    on 429 quota errors using the server-suggested retryDelay.
    """
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return TranscriptionResult(
            transcript="",
            error="GEMINI_API_KEY missing. Get one at https://aistudio.google.com/apikey",
        )

    audio_path = Path(audio_path)
    mime = _MIME.get(audio_path.suffix.lower(), "audio/mp4")

    t0 = time.perf_counter()
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            _throttle()
            client = genai.Client(api_key=key)
            audio_bytes = audio_path.read_bytes()

            resp = client.models.generate_content(
                model=model_id,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                    _TRANSCRIBE_PROMPT,
                ],
            )
            break  # success
        except Exception as exc:
            last_exc = exc
            msg = str(exc)
            # 429 quota error — try to honor the retryDelay if present and we have retries left
            if "429" in msg and attempt < max_retries:
                # crude extraction: look for "retry in <N>s"
                import re as _re
                m = _re.search(r"retry in (\d+(?:\.\d+)?)s", msg)
                delay = float(m.group(1)) if m else 30.0
                # cap at 60s so we don't hang forever
                time.sleep(min(delay + 1, 60))
                continue
            # non-retryable error
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return TranscriptionResult(
                transcript="",
                latency_total_ms=elapsed_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
    else:
        # all retries exhausted
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return TranscriptionResult(
            transcript="",
            latency_total_ms=elapsed_ms,
            error=f"{type(last_exc).__name__} after {max_retries} retries: {last_exc}",
        )

    try:
        elapsed_ms = (time.perf_counter() - t0) * 1000

        transcript = (resp.text or "").strip()
        # Pull the language hint if the model included one in any candidate metadata
        raw = {
            "text": transcript,
            "model": model_id,
            "usage": getattr(resp, "usage_metadata", None) and {
                "input_tokens": resp.usage_metadata.prompt_token_count,
                "output_tokens": resp.usage_metadata.candidates_token_count,
            },
        }

        return TranscriptionResult(
            transcript=transcript,
            language_detected=None,   # Gemini doesn't return a language code separately
            latency_total_ms=elapsed_ms,
            raw_response=raw,
        )
    except Exception as exc:
        return TranscriptionResult(
            transcript="",
            latency_total_ms=(time.perf_counter() - t0) * 1000,
            error=f"{type(exc).__name__}: {exc}",
        )


if __name__ == "__main__":
    from src.data_loader import load_clips
    clips = load_clips()
    if not clips:
        print("No clips found.")
    else:
        c = clips[0]
        print(f"Testing on {c.clip_id} ...")
        r = transcribe(c.audio_path)
        if r.error:
            print(f"  ERROR: {r.error}")
        else:
            print(f"  Transcript: {r.transcript!r}")
            print(f"  Latency: {r.latency_total_ms:.0f} ms")
