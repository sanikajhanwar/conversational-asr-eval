"""Deepgram ASR runner — the baseline that every other model is compared against.

Uses plain HTTP against Deepgram's REST API to dodge SDK-version churn.
Model: `nova-3` with multilingual language detection.

Docs: https://developers.deepgram.com/reference/listen-file
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from . import TranscriptionResult

load_dotenv()

MODEL_NAME = "deepgram"
DEFAULT_MODEL = "nova-3"
ENDPOINT = "https://api.deepgram.com/v1/listen"

# Map common audio extensions to MIME types Deepgram accepts
_MIME = {
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
}


def transcribe(
    audio_path: Path,
    model: str = DEFAULT_MODEL,
    language: str = "multi",      # multilingual auto-detect; covers Hindi+English+code-switch
    smart_format: bool = True,
) -> TranscriptionResult:
    """Transcribe one audio file via Deepgram REST API."""
    key = os.getenv("DEEPGRAM_API_KEY")
    if not key:
        return TranscriptionResult(
            transcript="",
            error="DEEPGRAM_API_KEY missing. Add it to your .env file.",
        )

    audio_path = Path(audio_path)
    mime = _MIME.get(audio_path.suffix.lower(), "audio/mp4")

    headers = {
        "Authorization": f"Token {key}",
        "Content-Type": mime,
    }
    params = {
        "model": model,
        "language": language,
        "smart_format": "true" if smart_format else "false",
    }

    t0 = time.perf_counter()
    try:
        with open(audio_path, "rb") as f:
            resp = requests.post(ENDPOINT, headers=headers, params=params, data=f, timeout=60)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if resp.status_code != 200:
            return TranscriptionResult(
                transcript="",
                latency_total_ms=elapsed_ms,
                error=f"HTTP {resp.status_code}: {resp.text[:300]}",
            )

        body = resp.json()
        transcript = ""
        detected_lang = None
        try:
            channel = body["results"]["channels"][0]
            transcript = channel["alternatives"][0].get("transcript", "")
            detected_lang = channel.get("detected_language")
        except (KeyError, IndexError):
            pass

        return TranscriptionResult(
            transcript=transcript,
            language_detected=detected_lang,
            latency_total_ms=elapsed_ms,
            raw_response=body,
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
            print(f"  Detected language: {r.language_detected}")
