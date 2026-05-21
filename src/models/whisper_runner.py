"""OpenAI Whisper ASR runner — open-source multilingual baseline.

Runs locally; uses GPU if available (Colab T4 recommended for `large-v3`).
On CPU, falls back to `medium` automatically to keep latency reasonable.

Docs: https://github.com/openai/whisper
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from . import TranscriptionResult

MODEL_NAME = "whisper"
DEFAULT_SIZE = "large-v3"   # best accuracy; ~3 GB, needs GPU
CPU_FALLBACK_SIZE = "medium"

_model_cache: dict[str, object] = {}


def _load_model(size: str):
    """Lazy-load and cache a Whisper model. First call downloads weights."""
    import whisper
    import torch

    if size in _model_cache:
        return _model_cache[size]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu" and size == "large-v3":
        print(f"[whisper] No GPU detected; downgrading {size} -> {CPU_FALLBACK_SIZE}")
        size = CPU_FALLBACK_SIZE

    print(f"[whisper] Loading {size} on {device} ...")
    model = whisper.load_model(size, device=device)
    _model_cache[size] = model
    return model


def transcribe(
    audio_path: Path,
    size: str = DEFAULT_SIZE,
    language: str | None = None,    # None = auto-detect; "hi" forces Hindi
) -> TranscriptionResult:
    """Transcribe one audio file with Whisper.

    Whisper uses ffmpeg under the hood to decode m4a — make sure ffmpeg is on PATH.
    """
    try:
        model = _load_model(size)
    except Exception as exc:
        return TranscriptionResult(
            transcript="",
            error=f"Model load failed: {type(exc).__name__}: {exc}",
        )

    t0 = time.perf_counter()
    try:
        # task='transcribe' keeps original language; 'translate' would force English
        result = model.transcribe(
            str(audio_path),
            language=language,
            task="transcribe",
            fp16=False,   # set True on GPU for ~2x speedup; False is safer cross-platform
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        return TranscriptionResult(
            transcript=result.get("text", "").strip(),
            language_detected=result.get("language"),
            latency_total_ms=elapsed_ms,
            raw_response={
                "text": result.get("text"),
                "language": result.get("language"),
                "segments": [
                    {k: s[k] for k in ("id", "start", "end", "text") if k in s}
                    for s in result.get("segments", [])
                ],
            },
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
