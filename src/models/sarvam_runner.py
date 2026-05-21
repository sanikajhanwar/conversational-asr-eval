"""Sarvam AI ASR runner — Indian-language specialist API.

Sarvam's `saarika` family is trained primarily on Indic speech, so this is our
in-domain comparison point against Deepgram (generic API) and Whisper (generic OSS).

Docs: https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from . import TranscriptionResult

load_dotenv()

MODEL_NAME = "sarvam"
DEFAULT_MODEL = "saarika:v2.5"   # latest Saarika as of late 2025
ENDPOINT = "https://api.sarvam.ai/speech-to-text"


def transcribe(
    audio_path: Path,
    model: str = DEFAULT_MODEL,
    language_code: str = "unknown",   # 'unknown' = auto-detect; 'hi-IN', 'kn-IN' also valid
) -> TranscriptionResult:
    """Transcribe one audio file via Sarvam REST API.

    Sarvam accepts wav / mp3 / flac / m4a as multipart form-data.
    """
    key = os.getenv("SARVAM_API_KEY")
    if not key:
        return TranscriptionResult(
            transcript="",
            error="SARVAM_API_KEY missing. Add it to your .env file.",
        )

    headers = {"api-subscription-key": key}
    data = {
        "model": model,
        "language_code": language_code,
    }

    t0 = time.perf_counter()
    try:
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/mp4")}
            resp = requests.post(ENDPOINT, headers=headers, data=data, files=files, timeout=60)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if resp.status_code != 200:
            return TranscriptionResult(
                transcript="",
                latency_total_ms=elapsed_ms,
                error=f"HTTP {resp.status_code}: {resp.text[:300]}",
            )

        body = resp.json()
        return TranscriptionResult(
            transcript=body.get("transcript", ""),
            language_detected=body.get("language_code"),
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
