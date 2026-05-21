"""Per-model inference runners.

Each runner exposes:
  - MODEL_NAME : str  (used as subfolder name in results/)
  - transcribe(audio_path: Path) -> TranscriptionResult

All runners share the TranscriptionResult shape so the orchestrator and
metrics modules don't care which model produced the transcript.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TranscriptionResult:
    """Uniform output across all 4 ASR models."""
    transcript: str
    language_detected: str | None = None
    latency_total_ms: float = 0.0          # full request → final transcript
    latency_first_byte_ms: float | None = None  # streaming only; None for batch
    raw_response: dict[str, Any] = field(default_factory=dict)
    error: str | None = None               # set if the call failed
