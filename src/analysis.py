"""Analysis: read scorecard.csv, produce charts + failure-mode table.

Run *after* `python -m src.rescore` has produced an up-to-date scorecard.

Outputs:
    charts/recovery_heatmap.png       — locality × model matrix, color = recovered
    charts/latency_comparison.png     — p50/p90 latency per model
    charts/per_condition_recovery.png — recovery rate per condition × model
    charts/failure_examples.md        — markdown table of worst transcripts per model
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.data_loader import CHARTS_DIR, RESULTS_DIR, ensure_charts_dir

sns.set_theme(style="whitegrid", font_scale=0.95)

# Sticker pricing for "cost at scale" (as of late 2025; verify before relying).
# Units: USD per minute of audio. Sources noted alongside.
PRICING_USD_PER_MIN = {
    "deepgram":   0.0043,   # nova-3, pay-as-you-go     (deepgram.com/pricing)
    "sarvam":     0.0050,   # saarika v2.5              (sarvam.ai pricing)
    "elevenlabs": 0.0067,   # scribe_v1, $0.40/hour     (elevenlabs.io/pricing)
    "gemini":     0.0006,   # 2.5 Flash, ~32 tok/sec    (ai.google.dev/pricing)
    "whisper":    0.0000,   # open-source; user pays GPU cost separately
}

# Stable color per model so charts are consistent
MODEL_COLORS = {
    "sarvam":     "#2E7D32",  # green   (the recommendation)
    "deepgram":   "#1565C0",  # blue
    "whisper":    "#6A1B9A",  # purple  (open-source pick)
    "elevenlabs": "#C62828",  # red
    "gemini":     "#F57F17",  # amber
}
MODEL_ORDER = ["sarvam", "deepgram", "whisper", "elevenlabs", "gemini"]


def _load_scorecard() -> pd.DataFrame:
    sc = RESULTS_DIR / "scorecard.csv"
    if not sc.exists():
        raise FileNotFoundError(
            f"{sc} missing. Run `python -m src.rescore` first."
        )
    df = pd.read_csv(sc)
    return df


# --- Chart 1: locality × model recovery heatmap -----------------------------

def chart_recovery_heatmap(df: pd.DataFrame, out_dir: Path) -> Path:
    """Heatmap: rows = localities (in clip order), cols = models, color = recovered."""
    # Pivot to a Boolean matrix
    pivot = (
        df.assign(locality_label=df["clip_id"].str.extract(r"^(\d+)_")[0] + " " + df["locality"])
          .pivot_table(index="locality_label", columns="model",
                       values="locality_recovered", aggfunc="max")
    )
    # Sort rows by the clip number prefix (so 01, 02, ..., 20)
    pivot = pivot.reindex(sorted(pivot.index, key=lambda s: int(s.split()[0])))
    pivot = pivot[[m for m in MODEL_ORDER if m in pivot.columns]]

    fig, ax = plt.subplots(figsize=(7, 8))
    sns.heatmap(
        pivot.astype(float), annot=True, fmt=".0f",
        cmap=sns.color_palette(["#C62828", "#2E7D32"], as_cmap=False),
        cbar=False, linewidths=0.4, linecolor="white",
        ax=ax,
    )
    ax.set_title("Locality recovered (1 = yes, 0 = no)")
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.xticks(rotation=0)
    plt.yticks(rotation=0)
    plt.tight_layout()
    out_path = out_dir / "recovery_heatmap.png"
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# --- Chart 2: latency comparison --------------------------------------------

def chart_latency_comparison(df: pd.DataFrame, out_dir: Path) -> Path:
    """p50 and p90 latency per model — log-y because Gemini is ~6x slower."""
    succeeded = df[df["transcript"].fillna("").str.len() > 0]
    summary = (
        succeeded.groupby("model")["latency_ms"]
                 .agg(p50="median", p90=lambda x: np.percentile(x, 90))
                 .reindex([m for m in MODEL_ORDER if m in succeeded["model"].unique()])
                 .reset_index()
    )

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(summary))
    width = 0.38
    bars1 = ax.bar(x - width/2, summary["p50"], width, label="p50 (median)",
                   color=[MODEL_COLORS[m] for m in summary["model"]], alpha=0.9)
    bars2 = ax.bar(x + width/2, summary["p90"], width, label="p90",
                   color=[MODEL_COLORS[m] for m in summary["model"]], alpha=0.45,
                   edgecolor="black", linewidth=0.5)

    for bars in (bars1, bars2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f"{bar.get_height():.0f}",
                    ha="center", va="bottom", fontsize=9)

    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(summary["model"])
    ax.set_ylabel("Latency (ms, log scale)")
    ax.set_title("Per-call latency — lower is better")
    ax.legend()
    plt.tight_layout()
    out_path = out_dir / "latency_comparison.png"
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# --- Chart 3: per-condition recovery ----------------------------------------

def chart_per_condition(df: pd.DataFrame, out_dir: Path) -> Path:
    """Grouped bar chart: recovery rate per (condition, model)."""
    pivot = (
        df.pivot_table(index="condition", columns="model",
                       values="locality_recovered", aggfunc="mean")
    )
    pivot = pivot[[m for m in MODEL_ORDER if m in pivot.columns]]
    cond_order = ["quiet", "traffic", "phone", "rushed", "whisper"]
    pivot = pivot.reindex([c for c in cond_order if c in pivot.index])

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(pivot.index))
    n_models = len(pivot.columns)
    width = 0.8 / max(n_models, 1)
    offset0 = -(n_models - 1) / 2 * width
    for i, model in enumerate(pivot.columns):
        ax.bar(x + offset0 + i * width, pivot[model], width,
               label=model, color=MODEL_COLORS[model])

    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index)
    ax.set_ylabel("Recovery rate")
    ax.set_ylim(0, 1.05)
    ax.set_title("Locality recovery by audio condition")
    ax.legend(loc="lower right", ncol=4, fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out_path = out_dir / "per_condition_recovery.png"
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


# --- Failure analysis table -------------------------------------------------

def failure_table(df: pd.DataFrame, out_dir: Path) -> Path:
    """Markdown table of the worst transcripts per model — for the report."""
    # Include both unrecovered and weakly-recovered (fuzzy_score < 75) cases.
    weak = df[(~df["locality_recovered"]) | (df["locality_fuzzy_score"] < 75)].copy()
    weak = weak.sort_values(["model", "locality_fuzzy_score"])
    weak = weak.groupby("model").head(5)

    lines = ["# Failure analysis — worst transcripts per model\n"]
    for model, sub in weak.groupby("model"):
        lines.append(f"\n## {model}\n")
        lines.append("| Clip | Locality | Transcript | Fuzzy | Recovered |")
        lines.append("|---|---|---|---|---|")
        for _, row in sub.iterrows():
            tr = (str(row["transcript"]) or "")[:90].replace("|", "\\|")
            lines.append(
                f"| {row['clip_id']} | {row['locality']} | {tr} "
                f"| {row['locality_fuzzy_score']:.0f} "
                f"| {'✓' if row['locality_recovered'] else '✗'} |"
            )

    out_path = out_dir / "failure_examples.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# --- Cost & summary tables --------------------------------------------------

def cost_at_scale(df: pd.DataFrame) -> pd.DataFrame:
    """For each model, project cost per million minutes given the latency p50."""
    rows = []
    for model in [m for m in MODEL_ORDER if m in df["model"].unique()]:
        sub = df[df["model"] == model]
        recovered = sub["locality_recovered"].mean()
        latency_p50 = sub.loc[sub["transcript"].fillna("").str.len() > 0, "latency_ms"].median()
        usd_per_min = PRICING_USD_PER_MIN.get(model)
        rows.append({
            "model": model,
            "recovered_rate": round(recovered, 3),
            "latency_p50_ms": round(latency_p50, 0) if not pd.isna(latency_p50) else None,
            "usd_per_min": usd_per_min,
            "usd_per_million_min": round(usd_per_min * 1_000_000, 0) if usd_per_min is not None else None,
        })
    return pd.DataFrame(rows)


def main() -> None:
    df = _load_scorecard()
    out_dir = ensure_charts_dir()

    chart_paths = [
        chart_recovery_heatmap(df, out_dir),
        chart_latency_comparison(df, out_dir),
        chart_per_condition(df, out_dir),
    ]
    failures = failure_table(df, out_dir)

    print("Charts written:")
    for p in chart_paths:
        print(f"  {p}")
    print(f"  {failures}")

    print("\n== Cost-at-scale projection ==")
    cost = cost_at_scale(df)
    print(cost.to_string(index=False))

    # Quick text recap of who recovered what
    print("\n== Clips where any model failed ==")
    failed_any = (
        df[~df["locality_recovered"]]
          .groupby(["clip_id", "locality", "condition"])["model"]
          .apply(lambda x: ", ".join(sorted(x)))
          .reset_index(name="failed_models")
    )
    if failed_any.empty:
        print("  (none — all 80 cells recovered)")
    else:
        print(failed_any.to_string(index=False))


if __name__ == "__main__":
    main()
