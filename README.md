# conversational-asr-eval

An evaluation of ASR systems for accurate entity extraction (Bangalore localities) in real-world Hindi/Hinglish audio.

**Models benchmarked:** Deepgram (baseline) · OpenAI Whisper · Sarvam AI · ElevenLabs Scribe
**Primary dataset:** 20 self-recorded clips spanning quiet / traffic / phone-call / whispered conditions.
**Secondary dataset:** FLEURS-Hindi (clean-speech reference, ~50 clips).

---

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API keys
cp .env.example .env
# then edit .env and paste your keys

# 3. Run the full pipeline
python -m src.run_all
```

Outputs land in `results/` (per-model JSON transcripts) and `charts/` (plots).

---

## Project structure

```
.
├── plan.md                  # detailed execution plan
├── recording_script.md      # sentence-by-sentence recording brief
├── ground_truth.csv         # what each clip actually says
├── recordings/              # 20 audio clips (.m4a)
├── src/
│   ├── data_loader.py       # ground truth + audio loading
│   ├── metrics.py           # WER + locality entity matching
│   ├── models/
│   │   ├── deepgram_runner.py
│   │   ├── whisper_runner.py
│   │   ├── sarvam_runner.py
│   │   └── elevenlabs_runner.py
│   └── run_all.py           # orchestrates all models on all clips
├── notebooks/
│   └── whisper_colab.ipynb  # Whisper inference on Colab T4 GPU
├── results/                 # per-model JSON outputs
├── charts/                  # generated plots
└── report.md                # 3-page final report
```

---

## What's being measured

| Metric                              | Why it matters                                        |
|-------------------------------------|-------------------------------------------------------|
| Word Error Rate (WER)               | Industry-standard ASR baseline                        |
| Locality exact match                | Did the locality name come through character-perfect? |
| Locality fuzzy match (Lev ≥0.85)    | Forgives minor spelling errors ("Byatarayanpura")     |
| Locality phonetic match (Metaphone) | Forgives transliteration drift                        |
| Latency (total + first-byte)        | Matters for live phone interactions                   |
| Cost @ scale                        | Production economics                                  |

Sliced by **audio condition** (quiet / traffic / phone / whispered-rushed) and **language** (Hindi / Hinglish / English / Kannada-mixed).

---

## Notes

- Audio is `.m4a` (iOS/Android default). All 4 models accept m4a directly; no conversion needed.
- Whisper large-v3 runs on Colab free tier (T4 GPU). See [notebooks/whisper_colab.ipynb](notebooks/whisper_colab.ipynb).
- API rate limits handled with retries + sleeps; full run takes ~5-10 minutes end-to-end.
