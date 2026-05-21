# ASR Shootout — Execution Plan

> A step-by-step plan for the Vahan.ai ASR benchmarking assignment.
> Written so you can read it once and know exactly what we're doing, why, and when.

---

## 1. The Assignment in One Paragraph

Vahan.ai runs a hiring platform where blue-collar job candidates in India apply over phone calls and WhatsApp voice notes — mostly in Hindi, Hinglish, or Kannada, often on noisy phone lines. They need software (called **ASR** — Automatic Speech Recognition) that turns this messy spoken audio into text. Many ASR systems exist. Our job is to figure out **which one works best for their specific situation**, prove it with real numbers, and recommend one. The test case is whether the ASR can correctly capture **Bangalore locality names** — because if a candidate says "I live in Byatarayanapura" and the system writes "by terror nahu," that's a broken product.

---

## 2. The Big Picture (Workflow)

Here's the entire project at a glance. Read this first; everything else is detail.

```
   ┌─────────────────────────┐
   │  STEP 1: Build dataset  │
   │                         │
   │  - Record 20 clips      │   ← you, on your phone
   │  - Write ground truth   │   ← what was actually said
   │  - Add FLEURS-Hindi     │   ← ~50 free clean clips
   └───────────┬─────────────┘
               │
               ▼
   ┌─────────────────────────┐
   │  STEP 2: Run ASR models │
   │                         │
   │   Deepgram   (API)      │   ← baseline (required)
   │   Whisper    (open src) │   ← generic open-source
   │   Sarvam AI  (API)      │   ← Indian specialist
   │   Chirp/Scribe (API)    │   ← 4th model
   └───────────┬─────────────┘
               │
               ▼
   ┌─────────────────────────┐
   │  STEP 3: Measure        │
   │                         │
   │  - WER (sentence-level) │
   │  - Locality accuracy    │   ← the metric that matters
   │  - Latency, cost        │
   │  - Slice by condition   │
   └───────────┬─────────────┘
               │
               ▼
   ┌─────────────────────────┐
   │  STEP 4: Tell the story │
   │                         │
   │  - Failure analysis     │
   │  - Charts + tables      │
   │  - 3-page report        │
   │  - 10-min walkthrough   │
   └─────────────────────────┘
```

The flow goes **left to right, top to bottom**. You can't measure before you have transcripts. You can't write the story before you have measurements.

---

## 3. The Models We're Testing (and Why)

We're testing **4 ASR systems**. The goal is to compare across two axes:

|                          | **API-based (paid)**       | **Open-source (free, self-hosted)** |
|--------------------------|----------------------------|-------------------------------------|
| **Generic (multilingual)** | Deepgram                   | OpenAI Whisper large-v3              |
| **Indian-specialized**     | Sarvam AI + Chirp/Scribe   | (skipping — too compute-heavy)       |

**Why each one:**

1. **Deepgram** — Required by the assignment. It's our baseline; everything gets compared to it. It's a popular paid API trained on mostly English/Western data. Question we're answering: *how well does a generic American ASR API handle Indian speech?*

2. **OpenAI Whisper (large-v3)** — The default open-source ASR. Free to run, multilingual, very popular. Question: *can a free model match a paid one?* Also: *does a "multilingual" model actually handle Hindi/Kannada well, or is multilingual just marketing?*

3. **Sarvam AI** — An Indian company building ASR specifically for Indian languages. Question: *does in-domain training (i.e. training on Indian audio) actually beat a bigger general-purpose model?* This is where we're most likely to find a **surprising result**, which the assignment rewards.

4. **Google Chirp 2 OR ElevenLabs Scribe** — A second API option. Gives us a comparison point on "API ecosystem maturity" — how easy to integrate, how good are docs, what's the pricing model.

**Why we're NOT testing:**
- Multiple Whisper sizes (medium, small) — we'll mention the size/accuracy tradeoff in the report but not benchmark all of them. Time better spent on failure analysis.
- AI4Bharat IndicConformer/IndicWhisper — would be great additions but Colab free tier struggles with two large models in one session. We'll cite their reported benchmarks in the report instead of running them ourselves.

---

## 4. The Dataset

### 4.1 Primary dataset: your 20 recordings

You'll record yourself saying each of the 20 Bangalore localities **inside a natural conversational sentence** — like a candidate on a real phone call. Not a clean reading of just the locality name.

**Examples of what we want:**
- "Haan bhaiya, main Koramangala mein rehta hoon, delivery yahaan tak aa sakti hai?"
- "Sir, mera ghar Whitefield ke paas hai, bus stop se 5 minute"
- "Naanu Yelahankadalli iddeene" (Kannada)

**What we DON'T want:**
- "Koramangala." (just the word, clean studio voice)
- Same sentence template for all 20

**Variation matters.** The assignment explicitly flags "all 20 recordings sound identical" as a weak submission. We'll split the 20 across 4 conditions:

| Condition          | Count | Where/how to record                               |
|--------------------|-------|---------------------------------------------------|
| Quiet room         | 5     | Closed door, no background sound                  |
| Traffic / outdoor  | 5     | Balcony, street, fan running, TV in background    |
| "Phone call" style | 5     | Hold phone slightly farther, mouth at an angle    |
| Whispered / rushed | 5     | Speak fast or low, like someone in a hurry        |

We'll also vary the **language** roughly: ~10 Hindi/Hinglish, ~5 mostly English with Hindi locality, ~5 with Kannada words. You don't need to be a linguist about it — just don't speak the same way 20 times.

### 4.2 Secondary dataset: FLEURS-Hindi (optional but doing it)

A free public dataset of clean Hindi speech (~50 short clips). We run all 4 models on these too.

**Why bother?** Because if Whisper performs badly on your recordings, we need to know: *is Whisper bad at Hindi, or is Whisper bad at noisy phone audio?* FLEURS gives us a "clean speech baseline." Compare a model's score on FLEURS vs on your recordings, and the gap tells you how much **audio quality** matters vs **language ability**.

### 4.3 Ground truth file

A CSV that says "for clip 01, the locality is Koramangala, the full sentence was X, the condition was quiet, the language was Hinglish." We need this to compute accuracy — you can't measure how wrong a transcript is unless you know what the right answer was.

---

## 5. The Metrics (and Why Each One Matters)

If we only measured WER and called it a day, that's a "weak submission" per the assignment. Here's what we're measuring and why.

### 5.1 Word Error Rate (WER)
- **What:** Standard ASR metric. Counts errors (substitutions + insertions + deletions) divided by total words.
- **Why:** It's the industry default. We have to report it.
- **Why it's not enough:** A model could correctly transcribe "Haan main ___ mein rehta hoon" but mangle the locality name, and still get a "good" WER. For our use case, the locality IS the entire point.

### 5.2 Locality Entity Accuracy (the metric we care about)
For each clip, we check: did the locality name come through correctly?

Three flavors of "correctly":
- **Exact match** — character-for-character identical. Strictest.
- **Fuzzy match (Levenshtein ≥ 0.85)** — forgives small spelling errors. "Byatarayanpura" vs "Byatarayanapura" counts as a match.
- **Phonetic match (Metaphone)** — forgives transliteration differences. "Koramangla" and "Koramangala" sound the same → match.

**Why three?** Different downstream uses care about different things. If you're filling a database field, fuzzy match is fine (you can normalize later). If you're doing exact lookup, you need strict. We'll report all three.

### 5.3 Per-Condition Slicing
For each model: what's the locality accuracy on *quiet* clips vs *noisy* vs *phone* vs *whispered*?

**Why:** Tells us *where* a model breaks. "Deepgram is 90% on quiet but 40% on phone-call audio" is far more actionable than "Deepgram is 70% on average."

### 5.4 Per-Language Slicing
Hindi/Hinglish vs Kannada-mixed. We expect every model to be worse on Kannada (less training data exists). Confirming this with data is the table-stakes finding.

### 5.5 Latency
- **First-byte latency** — for streaming models, how long until the first word appears.
- **Total latency** — how long the full transcript takes.
- **Why:** A real Vahan candidate is on a live phone call. A 3-second wait feels broken; 300ms feels instant.

### 5.6 Cost at scale
Just the sticker price from each provider's pricing page, projected to "$/hour of audio" and "$/million minutes."

**Why:** Vahan presumably processes thousands of hours/month. A model that's 2% more accurate but 10x the cost is a different decision than one that's 2% more accurate at the same price.

---

## 6. Day-by-Day Schedule (5 days)

### Day 1 — Setup & start recording

**Goal:** End the day with the project skeleton, recordings in progress, and API keys in hand.

**You do (~2-3 hrs):**
1. Sign up for Deepgram (https://console.deepgram.com/signup) — they give $200 free credit.
2. Sign up for Sarvam AI (https://www.sarvam.ai/).
3. Pick a 4th model:
   - **Google Chirp 2** (via Google Cloud Speech-to-Text) — 60 free min/month, but GCP signup is fiddly.
   - **ElevenLabs Scribe** — easier signup, ~10k free credits.
4. Paste all API keys into a `.env` file (I'll create the template).
5. Start recording. Use your phone's voice recorder app. Follow the recording script I'll create. Save as WAV or M4A.

**I do:**
- Create folder structure
- Generate recording script (sentence templates + condition assignments)
- Write `ground_truth.csv` template
- Set up `.env.example`, `requirements.txt`, `README.md`
- Write the data-loading helper module

**End state:** ~10-15 clips recorded, project skeleton ready.

---

### Day 2 — Deepgram baseline + Whisper

**Goal:** First real transcripts and first real numbers.

**You do (~30 min):**
- Finish remaining recordings.
- Drop all 20 files into `recordings/` folder.

**I do:**
- **Deepgram pipeline:** script that hits the Deepgram API with `nova-2` and `nova-3`, saves transcripts.
- **Whisper pipeline:** Colab notebook that runs Whisper large-v3 on all 20 clips locally on a free Colab T4 GPU. Saves transcripts.
- **Metrics module:** implements WER, exact/fuzzy/phonetic entity match, condition slicing.
- Run both models, generate first scorecard.

**End state:** We can already say "Deepgram scored X%, Whisper scored Y%, here's the gap." Half the project's value is here.

---

### Day 3 — Sarvam + 4th model + FLEURS dataset

**Goal:** All 4 models have transcripts on both datasets.

**I do:**
- **Sarvam pipeline:** API call with `saarika-v2` model.
- **4th model pipeline:** Chirp or Scribe, depending on what you picked.
- **FLEURS-Hindi loader:** download ~50 clips from HuggingFace, run all 4 models on them.
- **Latency wrapper:** time every API call, save timestamps.

**End state:** Complete transcript matrix. 4 models × ~70 clips = ~280 transcripts collected and saved. No more model runs after today.

---

### Day 4 — Analysis & charts

**Goal:** Turn numbers into a story.

**I do:**
- **Aggregate scorecard:** main table — model rows, metric columns, Deepgram as the reference row.
- **Failure analysis:** for each model, identify the 5 worst clips. Write down what went wrong and why. Quote the actual incorrect transcript.
- **Per-locality heatmap:** rows = locality names, columns = models, color = accuracy. Reveals which names break which models.
- **Condition slicing chart:** line chart, accuracy vs audio condition, one line per model.
- **Cost & latency table:** $/hour of audio, median + max latency per model.
- **Own-recordings vs FLEURS comparison:** how much does each model degrade on real-world audio vs clean studio audio?

**End state:** All visualizations and tables ready. We know our recommendation.

---

### Day 5 — Report + walkthrough prep

**Goal:** Submit-ready deliverables.

**I do:**
- Write the **3-page report**:
  - **Approach** (½ pg) — what we picked, what we measured, why
  - **Results** (1 pg) — scorecard + condition slicing chart
  - **Failure analysis** (1 pg) — concrete examples, with quoted incorrect transcripts
  - **Recommendation** (½ pg) — "Use model X under these conditions, model Y under those. One thing that surprised us."
- Write a **walkthrough outline** — what to say slide-by-slide for the 10-min presentation.
- Final pass on the codebase: clean docstrings, tested, runs end-to-end with one command.

**You do:**
- Read the report, push back on anything that doesn't match what you saw.
- Practice the walkthrough out loud once. Get used to the numbers.

**End state:** Ready to submit.

---

## 7. Folder Structure

This is what the project will look like by Day 1 evening:

```
assignment-vahan.ai/
│
├── plan.md                       ← this file
├── README.md                     ← how to run the code
├── requirements.txt              ← Python dependencies
├── .env.example                  ← template for API keys
├── .env                          ← your actual keys (gitignored)
│
├── recordings/                   ← your 20 audio files
│   ├── 01_koramangala_quiet_hinglish.wav
│   ├── 02_indiranagar_traffic_hindi.wav
│   └── ...
│
├── ground_truth.csv              ← what each clip actually says
├── recording_script.md           ← sentence templates + conditions
│
├── src/
│   ├── data_loader.py            ← loads audio + ground truth
│   ├── metrics.py                ← WER, entity match, slicing
│   ├── models/
│   │   ├── deepgram_runner.py
│   │   ├── whisper_runner.py
│   │   ├── sarvam_runner.py
│   │   └── fourth_runner.py
│   ├── run_all.py                ← end-to-end pipeline
│   └── analysis.py               ← failure analysis, charts
│
├── notebooks/
│   └── whisper_colab.ipynb       ← Whisper inference on Colab GPU
│
├── results/                      ← all model outputs
│   ├── deepgram/
│   ├── whisper/
│   ├── sarvam/
│   ├── fourth/
│   └── scorecard.csv             ← final consolidated numbers
│
├── charts/                       ← generated plots
│   ├── per_condition.png
│   ├── per_locality_heatmap.png
│   └── cost_latency.png
│
└── report.md                     ← the 3-page deliverable
```

---

## 8. What Could Go Wrong (and Backup Plans)

| Risk                                                | Plan B                                                                 |
|-----------------------------------------------------|------------------------------------------------------------------------|
| Sarvam free tier doesn't cover 70 clips             | Use a subset of FLEURS (20 clips instead of 50)                        |
| Colab disconnects mid-Whisper run                   | Save partial results after each clip; resume from last completed       |
| GCP signup for Chirp takes too long                 | Switch to ElevenLabs Scribe (easier signup)                            |
| Your recordings come out unusable (clipped/silent)  | We'll re-record problem clips on Day 2 morning — short, no big deal    |
| One model API is rate-limited                       | Add `time.sleep(1)` between calls; full run takes ~10 min instead of 2 |
| Time pressure on Day 5                              | Report is the priority. Code polish can be skipped if needed.          |

---

## 9. Who Does What

| Task                              | You | Me |
|-----------------------------------|-----|----|
| Record 20 audio clips             | ✅  |    |
| Sign up for API services          | ✅  |    |
| Paste API keys into `.env`        | ✅  |    |
| Drop audio into `recordings/`     | ✅  |    |
| Review report draft, push back    | ✅  |    |
| Practice walkthrough              | ✅  |    |
| Present to Vahan team             | ✅  |    |
| Folder structure, scaffolding     |     | ✅ |
| Write all pipeline code           |     | ✅ |
| Run inference on all models       |     | ✅ |
| Compute metrics                   |     | ✅ |
| Generate charts                   |     | ✅ |
| Write report draft                |     | ✅ |
| Write walkthrough outline         |     | ✅ |

**The only things only you can do** are: record the clips, sign up for APIs (the accounts need to be in your name), and actually present the work. Everything else I'll build and you review.

---

## 10. What "Done" Looks Like

By end of Day 5, you'll have:

1. **20 audio files** in `recordings/`, named clearly, covering varied conditions.
2. **A Python codebase** that anyone can clone, install (`pip install -r requirements.txt`), drop in their own `.env` keys, and reproduce all the numbers with one command.
3. **A 3-page Markdown report** with:
   - Scorecard table (4 models, all metrics)
   - Condition-slicing chart
   - At least 5 concrete failure examples with explanations
   - A clear recommendation: "Use X. Here's the surprising thing we found."
4. **A walkthrough outline** for the 10-min presentation.

That's the submission. Anything beyond this is bonus.

---

## 11. Next Step (Right Now)

If you're ready to start, the immediate next actions are:

1. **You:** Start the Deepgram signup (https://console.deepgram.com/signup) and Sarvam signup (https://www.sarvam.ai/). Tell me which 4th model you want (Chirp 2 or ElevenLabs Scribe).
2. **Me:** Scaffold the folder structure + recording script + ground-truth template so you can start recording the moment you're done with signups.

Say the word and I'll start scaffolding.
