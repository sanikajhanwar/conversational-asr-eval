"""Orchestrator: run every ASR model on every clip, compute metrics, save results.

Usage:
    python -m src.run_all                       # all 4 models, all 20 clips
    python -m src.run_all --models deepgram     # only Deepgram
    python -m src.run_all --models deepgram sarvam   # multiple
    python -m src.run_all --skip-whisper         # skip Whisper (no GPU on your laptop)

Outputs:
    results/<model>/<clip_id>.json   – raw API response + transcript per clip
    results/scorecard.csv            – consolidated metrics across all models/clips
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.data_loader import Clip, ensure_results_dir, load_clips, RESULTS_DIR
from src.metrics import score_clip
from src.models import TranscriptionResult
from src.models import deepgram_runner, elevenlabs_runner, sarvam_runner, whisper_runner

# (name, transcribe_fn). Order matters only for display.
ALL_MODELS = {
    "deepgram":   deepgram_runner.transcribe,
    "whisper":    whisper_runner.transcribe,
    "sarvam":     sarvam_runner.transcribe,
    "elevenlabs": elevenlabs_runner.transcribe,
}


def _save_per_clip_result(model: str, clip: Clip, result: TranscriptionResult) -> None:
    """Dump raw + transcript + latency to results/<model>/<clip_id>.json."""
    out_dir = ensure_results_dir(model)
    payload = {
        "clip_id": clip.clip_id,
        "filename": clip.filename,
        "model": model,
        "transcript": result.transcript,
        "language_detected": result.language_detected,
        "latency_total_ms": result.latency_total_ms,
        "latency_first_byte_ms": result.latency_first_byte_ms,
        "error": result.error,
        "raw_response": result.raw_response,
    }
    (out_dir / f"{clip.clip_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_model(model_name: str, clips: list[Clip], retry_on_error: bool = True) -> list[dict]:
    """Run one model on all clips. Returns list of per-clip score dicts."""
    if model_name not in ALL_MODELS:
        raise ValueError(f"Unknown model: {model_name}. Known: {list(ALL_MODELS)}")
    transcribe_fn = ALL_MODELS[model_name]

    rows: list[dict] = []
    for clip in tqdm(clips, desc=f"  {model_name}", unit="clip"):
        result = transcribe_fn(clip.audio_path)

        if result.error and retry_on_error:
            time.sleep(2)
            result = transcribe_fn(clip.audio_path)

        _save_per_clip_result(model_name, clip, result)

        score = score_clip(
            reference_sentence=clip.sentence_expected,
            locality_canonical=clip.locality_canonical,
            locality_aliases=clip.locality_aliases,
            hypothesis=result.transcript,
        )
        rows.append({
            "model": model_name,
            "clip_id": clip.clip_id,
            "locality": clip.locality_canonical,
            "condition": clip.condition,
            "language": clip.language,
            "transcript": result.transcript,
            "latency_ms": result.latency_total_ms,
            "error": result.error,
            **score,
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ASR models on the locality clips.")
    parser.add_argument("--models", nargs="+", default=list(ALL_MODELS.keys()),
                        choices=list(ALL_MODELS.keys()),
                        help="Subset of models to run.")
    parser.add_argument("--skip-whisper", action="store_true",
                        help="Drop Whisper from the run (use if no GPU available locally).")
    args = parser.parse_args()

    models_to_run = list(args.models)
    if args.skip_whisper and "whisper" in models_to_run:
        models_to_run.remove("whisper")

    clips = load_clips()
    print(f"Loaded {len(clips)} clips. Running models: {models_to_run}\n")

    all_rows: list[dict] = []
    for model_name in models_to_run:
        print(f"\n== {model_name} ==")
        try:
            rows = run_model(model_name, clips)
            all_rows.extend(rows)
        except Exception as exc:
            print(f"  Model {model_name} crashed: {type(exc).__name__}: {exc}")
            continue

    if not all_rows:
        print("\nNo rows produced. Check API keys and errors above.")
        return

    df = pd.DataFrame(all_rows)
    scorecard_path = RESULTS_DIR / "scorecard.csv"
    df.to_csv(scorecard_path, index=False)
    print(f"\nScorecard written: {scorecard_path}")

    # Quick summary print
    print("\n== Quick summary (per model) ==")
    summary = (
        df.groupby("model")
          .agg(
              n=("clip_id", "count"),
              wer_mean=("wer", "mean"),
              exact_rate=("locality_exact", "mean"),
              fuzzy_rate=("locality_fuzzy", "mean"),
              phonetic_rate=("locality_phonetic", "mean"),
              latency_p50=("latency_ms", "median"),
          )
          .round(3)
    )
    print(summary.to_string())


if __name__ == "__main__":
    main()
