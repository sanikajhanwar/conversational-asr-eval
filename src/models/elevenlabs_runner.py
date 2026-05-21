"""ElevenLabs Scribe ASR runner — second API-based comparison point.

ElevenLabs Scribe v1 is a recent multilingual ASR with strong claims on accuracy
across 99 languages. We use it as the "general-purpose API competing with Deepgram."

Docs: https://elevenlabs.io/docs/capabilities/speech-to-text
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

from . import TranscriptionResult

load_dotenv()

MODEL_NAME = "elevenlabs"
DEFAULT_MODEL_ID = "scribe_v1"


def _client() -> ElevenLabs:
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY missing. Sign up at elevenlabs.io and add the key to .env."
        )
    return ElevenLabs(api_key=key)


def transcribe(
    audio_path: Path,
    model_id: str = DEFAULT_MODEL_ID,
    language_code: str | None = None,   # None = auto-detect
) -> TranscriptionResult:
    """Transcribe one audio file via ElevenLabs Speech-to-Text."""
    try:
        client = _client()
    except RuntimeError as exc:
        return TranscriptionResult(transcript="", error=str(exc))

    t0 = time.perf_counter()
    try:
        with open(audio_path, "rb") as f:
            resp = client.speech_to_text.convert(
                file=f,
                model_id=model_id,
                language_code=language_code,
                tag_audio_events=False,   # we just want plain transcript
                diarize=False,
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Response shape: pydantic model with .text and .language_code
        text = getattr(resp, "text", "") or ""
        lang = getattr(resp, "language_code", None)
        raw = resp.model_dump() if hasattr(resp, "model_dump") else {"text": text}

        return TranscriptionResult(
            transcript=text,
            language_detected=lang,
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
            print(f"  Detected language: {r.language_detected}")
