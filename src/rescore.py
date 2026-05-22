"""Re-score saved transcripts without re-calling any APIs.

Reads every JSON in results/<model>/, looks up ground truth by clip_id, applies
the (updated) metrics module, writes a fresh results/scorecard.csv, and prints
a summary table.

Usage:
    python -m src.rescore
"""
from __future__ import annotations

import json

import pandas as pd

from src.data_loader import RESULTS_DIR, load_clips
from src.metrics import score_clip


def rescore_all() -> pd.DataFrame:
    clips_by_id = {c.clip_id: c for c in load_clips()}

    rows: list[dict] = []
    missing_clips: list[str] = []

    for model_dir in sorted(p for p in RESULTS_DIR.iterdir() if p.is_dir()):
        model_name = model_dir.name
        json_files = sorted(model_dir.glob("*.json"))
        if not json_files:
            print(f"[skip] {model_name}: no JSON transcripts found")
            continue

        for json_path in json_files:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            clip_id = data.get("clip_id") or json_path.stem
            if clip_id not in clips_by_id:
                missing_clips.append(f"{model_name}/{clip_id}")
                continue
            clip = clips_by_id[clip_id]
            transcript = data.get("transcript") or ""

            score = score_clip(
                reference_sentence=clip.sentence_expected,
                locality_canonical=clip.locality_canonical,
                locality_aliases=clip.locality_aliases,
                hypothesis=transcript,
            )
            rows.append({
                "model": model_name,
                "clip_id": clip_id,
                "locality": clip.locality_canonical,
                "condition": clip.condition,
                "language": clip.language,
                "transcript": transcript,
                "latency_ms": data.get("latency_total_ms"),
                "error": data.get("error"),
                **score,
            })

    if missing_clips:
        print(f"Warning: {len(missing_clips)} JSON(s) had no matching ground-truth row: "
              f"{missing_clips[:5]}{'...' if len(missing_clips) > 5 else ''}")

    return pd.DataFrame(rows)


def main() -> None:
    df = rescore_all()
    if df.empty:
        print("No transcripts found in results/. Run `python -m src.run_all` first.")
        return

    out_path = RESULTS_DIR / "scorecard.csv"
    df.to_csv(out_path, index=False)
    print(f"\nRescored {len(df)} rows. Wrote {out_path}\n")

    summary = (
        df.groupby("model")
          .agg(
              n=("clip_id", "count"),
              wer_mean=("wer", "mean"),
              recovered_rate=("locality_recovered", "mean"),
              exact_rate=("locality_exact", "mean"),
              fuzzy_rate=("locality_fuzzy", "mean"),
              phonetic_rate=("locality_phonetic", "mean"),
              word_level_rate=("locality_word_level", "mean"),
              latency_p50=("latency_ms", "median"),
          )
          .round(3)
    )
    print("== Per-model summary ==")
    print(summary.to_string())

    # Per-condition slicing — what does each model do under each audio condition?
    print("\n== Locality recovery rate by condition × model ==")
    pivot = (
        df.pivot_table(index="condition", columns="model",
                       values="locality_recovered", aggfunc="mean")
          .round(2)
    )
    print(pivot.to_string())

    # Which clips break every model — the "universally hard" set
    by_clip = df.groupby("clip_id")["locality_recovered"].sum()
    universally_hard = by_clip[by_clip == 0].index.tolist()
    if universally_hard:
        print(f"\n== Clips no model recovered ({len(universally_hard)}): ==")
        for cid in universally_hard:
            print(f"   {cid}")


if __name__ == "__main__":
    main()
