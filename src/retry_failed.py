"""Re-run a single model only on the clips whose previous result errored out.

Use case: Gemini free-tier hit a daily quota mid-run; we got 15/20.
Set GEMINI_MODEL_ID=gemini-2.5-flash-lite in the environment to swap to the
lighter model for the retry, then:

    python -m src.retry_failed gemini

Reads results/<model>/*.json, picks the ones with non-empty `error`, re-runs
those clips via the model's runner, overwrites the JSONs. After this, run
`python -m src.rescore` to regenerate the consolidated scorecard.
"""
from __future__ import annotations

import argparse
import json
import sys

from src.data_loader import RESULTS_DIR, ensure_results_dir, load_clips
from src.models import deepgram_runner, elevenlabs_runner, gemini_runner, sarvam_runner

RUNNERS = {
    "deepgram":   deepgram_runner.transcribe,
    "sarvam":     sarvam_runner.transcribe,
    "elevenlabs": elevenlabs_runner.transcribe,
    "gemini":     gemini_runner.transcribe,
}


def find_failed_clip_ids(model_name: str) -> list[str]:
    out_dir = RESULTS_DIR / model_name
    if not out_dir.exists():
        return []
    failed = []
    for jp in sorted(out_dir.glob("*.json")):
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("error"):
            failed.append(data.get("clip_id") or jp.stem)
    return failed


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry failed clips for one ASR model.")
    parser.add_argument("model", choices=list(RUNNERS.keys()),
                        help="Which model to retry.")
    args = parser.parse_args()

    failed_ids = find_failed_clip_ids(args.model)
    if not failed_ids:
        print(f"No failed clips found for {args.model}. Nothing to do.")
        return

    print(f"[{args.model}] retrying {len(failed_ids)} failed clip(s): {failed_ids}")

    clips_by_id = {c.clip_id: c for c in load_clips()}
    runner = RUNNERS[args.model]
    out_dir = ensure_results_dir(args.model)

    successes = 0
    for cid in failed_ids:
        clip = clips_by_id.get(cid)
        if clip is None:
            print(f"  [skip] {cid}: not in ground_truth.csv")
            continue

        print(f"  -> {cid}", end=" ", flush=True)
        result = runner(clip.audio_path)
        if result.error:
            print(f"STILL FAILED: {result.error[:100]}")
        else:
            successes += 1
            print(f"OK ({result.latency_total_ms:.0f} ms)")

        # Save (or overwrite) the JSON
        payload = {
            "clip_id": clip.clip_id,
            "filename": clip.filename,
            "model": args.model,
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

    print(f"\nDone. {successes}/{len(failed_ids)} recovered. "
          f"Now run: python -m src.rescore")
    if successes < len(failed_ids):
        sys.exit(1)


if __name__ == "__main__":
    main()
