"""Loads ground truth metadata and audio file paths.

Single source of truth for "what is clip N" across the whole pipeline.
Every runner and every metric consults this module.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = PROJECT_ROOT / "recordings"
GROUND_TRUTH_CSV = PROJECT_ROOT / "ground_truth.csv"
RESULTS_DIR = PROJECT_ROOT / "results"
CHARTS_DIR = PROJECT_ROOT / "charts"


@dataclass
class Clip:
    """One audio clip + everything we know about it."""
    filename: str
    audio_path: Path
    locality_canonical: str
    locality_aliases: list[str]
    sentence_expected: str
    condition: str          # quiet | traffic | phone | whisper | rushed
    language: str           # hindi | hinglish | english | kannada

    @property
    def clip_id(self) -> str:
        """Filename without extension, e.g. '01_koramangala_quiet_hinglish'."""
        return self.audio_path.stem


def load_ground_truth() -> pd.DataFrame:
    """Reads ground_truth.csv as a DataFrame, returns sorted by filename."""
    if not GROUND_TRUTH_CSV.exists():
        raise FileNotFoundError(f"ground_truth.csv missing: {GROUND_TRUTH_CSV}")
    df = pd.read_csv(GROUND_TRUTH_CSV)
    df = df.sort_values("filename").reset_index(drop=True)
    return df


def load_clips() -> list[Clip]:
    """Returns one Clip object per row of ground_truth.csv.

    Raises if an audio file referenced in the CSV doesn't actually exist on disk.
    """
    df = load_ground_truth()
    clips: list[Clip] = []
    missing: list[str] = []

    for _, row in df.iterrows():
        audio_path = RECORDINGS_DIR / row["filename"]
        if not audio_path.exists():
            missing.append(row["filename"])
            continue

        aliases = [a.strip() for a in str(row["locality_aliases"]).split(";") if a.strip()]
        clips.append(Clip(
            filename=row["filename"],
            audio_path=audio_path,
            locality_canonical=row["locality_canonical"],
            locality_aliases=aliases,
            sentence_expected=row["sentence_expected"],
            condition=row["condition"],
            language=row["language"],
        ))

    if missing:
        raise FileNotFoundError(
            f"{len(missing)} audio file(s) referenced in ground_truth.csv but missing "
            f"from recordings/: {missing[:3]}{'...' if len(missing) > 3 else ''}"
        )
    return clips


def iter_clips() -> Iterator[Clip]:
    """Generator form for memory-light iteration."""
    yield from load_clips()


def ensure_results_dir(model_name: str) -> Path:
    """Creates results/<model_name>/ if it doesn't exist, returns the path."""
    out = RESULTS_DIR / model_name
    out.mkdir(parents=True, exist_ok=True)
    return out


def ensure_charts_dir() -> Path:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    return CHARTS_DIR


if __name__ == "__main__":
    # Smoke test: print one line per clip so you can eyeball that loading works.
    clips = load_clips()
    print(f"Loaded {len(clips)} clips from ground_truth.csv\n")
    for c in clips:
        size_kb = c.audio_path.stat().st_size // 1024
        print(f"  {c.clip_id:<55} {c.condition:<8} {c.language:<8} {size_kb} KB")
