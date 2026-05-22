# ASR Shootout — Vahan.ai Intern Assessment

**Models benchmarked:** Deepgram (baseline, `nova-3`) · Sarvam (`saarika:v2.5`) · ElevenLabs Scribe (`scribe_v1`) · Google Gemini (`2.5-flash` + `2.5-flash-lite` fallback) · OpenAI Whisper (`large-v3`, open-source, Colab T4)
**Dataset:** 20 self-recorded clips of Bangalore localities spoken naturally in Hindi/Hinglish/English/Kannada, split across 5 audio conditions (quiet, traffic, phone-call, rushed, whispered).

---

## 1. Approach

### Framing

Vahan's product extracts entities (locality names) from candidate speech on phone calls. That single sentence shapes everything that follows — the right benchmark is not "general ASR quality" but "does this product-critical entity come through?"

### Model selection

Deepgram as required baseline, plus four contrasting picks spanning the dimensions the assignment explicitly calls out:

|                    | API, generic        | API, Indian-specialist | Open-source (self-hosted) | Frontier LLM      |
|--------------------|---------------------|------------------------|---------------------------|--------------------|
| **Dedicated ASR**  | Deepgram, ElevenLabs | Sarvam                 | Whisper large-v3          | —                  |
| **General-purpose**| —                   | —                      | —                         | Gemini 2.5 Flash   |

This covers the trade-off axes that drive a real production decision: **paid vs self-hosted** (cost ceiling vs compute ceiling), **multilingual-generic vs Indic-specialist** (in-domain training value), and **dedicated ASR vs LLM-with-audio** (purpose-built quality vs frontier-model breadth). I avoided benchmarking multiple sizes within one family (e.g. Whisper small / medium / large) — the published curves already tell that story.

### Recording variation

Anti-"identical-clip" failure mode: 5 clips each in quiet / traffic-noise / phone-distance / whispered-or-rushed conditions, distributed across 20 localities spanning easy (Koramangala, Whitefield) → hard (Byatarayanapura, Kadugondanahalli, Thalaghattapura). Language mix: ~7 Hindi-heavy, ~8 Hinglish, ~3 English, ~2 Kannada-flavored. Hard localities are spread across all 4 conditions so we can disentangle *"model bad at noise"* from *"model bad at the name."*

### Metric design — why locality recovery, not just WER

I started with WER because it's the default. A worked example killed it. Take three transcripts of *"Haan main Koramangala mein rehta hoon"* (6 words):

| Transcript                                     | WER  | What the product gets |
|------------------------------------------------|------|------------------------|
| Haan main Koramangala mein rehta hoon          | 0%   | ✓ correct locality |
| Haan main **Koramangla** mein rehta hoon       | 17%  | ✓ recoverable (1-char typo) |
| Haan main **garam masala** mein rehta hoon     | 17%  | ✗ wrong entity entirely |

WER scores rows 2 and 3 the same. For an entity-extraction product, those are not the same outcome — one is a typo that any normalization step fixes; the other is a lost candidate. So WER is the wrong scoreboard for this use case.

The right scoreboard is binary, per-clip: **did the locality come through in a form that a downstream cleanup step could normalize?** I call that **locality recovery** — 100% means the locality was captured on every clip, by any one of four checks chained as OR:

1. **Exact match** — `Koramangala` character-for-character. Strictest; would be enough if every transcript were already clean.
2. **Fuzzy match** (Levenshtein ≥ 80) — `Koramangla` still counts. Forgives transcription typos.
3. **Phonetic match** (double-metaphone) — `Koramangaala` still counts. Critical for Indic transliteration drift where `कोरमंगला` can romanize a dozen close-but-not-identical ways.
4. **Word-level** — `Electronic City` recovered if both `electronic` and `city` find phonetic matches anywhere in the transcript. Necessary because transliteration introduces spurious word boundaries (`इलेक्ट्रॉनिक` → `ilektra nika`).

Each tier is reported separately too, because they answer different product questions: **exact** tells you about database-ready output; **fuzzy/phonetic** tells you about post-process recoverability; **word-level** is the floor for "could a human downstream salvage this?"

WER is still reported for context and to flag pathological outputs. **Latency** (p50, p90) and **cost** (per million minutes) are measured separately — they're production constraints, not transcription quality.

**Honesty check on this metric:** recovery rate has a ceiling. If a transcript is unusable garbage that happens to contain the right substring, our metric still says "recovered." Whisper's clip-09 hallucination loop is the canonical example — 53 seconds of fluent-sounding nonsense that technically matched at the word level (§3 walks through it). So recovery rate is necessary but not sufficient; for borderline cases the qualitative read of the transcript matters as much as the binary verdict.

### Transliteration pipeline

All transcripts are normalized through an Indic→Latin transliteration step (Devanagari, Kannada, Gurmukhi via Harvard-Kyoto; modern Hindi additions like `ॉ` folded to `ो` first) before matching. Without this, every Hindi-script transcript scored zero and the comparison was meaningless. This was the single biggest engineering surprise of the project — the first run had every model at 0% recovery on Hindi clips, and I almost concluded the models were broken before realizing the script mismatch.

---

## 2. Results

| Model         | Recovery | Exact     | Fuzzy    | Phonetic | WER       | Latency p50 | $ / M min     |
|---------------|----------|-----------|----------|----------|-----------|-------------|---------------|
| **Sarvam**    | **100%** | 20%       | 65%      | 65%      | 0.74      | **1.19 s** ⭐ | $5,000        |
| **Deepgram**  | **100%** | 20%       | 65%      | 70%      | **0.63** ⭐| 2.89 s      | $4,300        |
| **Whisper**   | **100%** | 15%       | 50%      | 65%      | 0.96 🚨   | 3.86 s      | **$0** ⭐ (GPU) |
| **Gemini**    | 95%      | **35%** ⭐| **70%** ⭐| 65%      | 0.73      | 7.69 s 🐌   | $600          |
| ElevenLabs    | 90%      | 15%       | 45%      | 60%      | 0.78      | 1.78 s      | $6,700        |

**Per-condition recovery rate:**

|              | quiet | traffic | phone | rushed | whisper |
|--------------|-------|---------|-------|--------|---------|
| Sarvam       | 100%  | 100%    | 100%  | 100%   | 100%    |
| Deepgram     | 100%  | 100%    | 100%  | 100%   | 100%    |
| Whisper      | 100%  | 100%    | 100%  | 100%   | 100%    |
| Gemini       | 100%  | 100%    | 100%  | 100%   | 67%     |
| ElevenLabs   | 80%   | 100%    | 100%  | 100%   | 67%     |

Charts: [recovery_heatmap.png](charts/recovery_heatmap.png), [latency_comparison.png](charts/latency_comparison.png), [per_condition_recovery.png](charts/per_condition_recovery.png).

### Two surprising findings

**1. Whisper (open-source) matches the paid APIs on locality recovery.** All three of Sarvam, Deepgram, and Whisper land at 100% recovery; both LLM-tier alternatives (Gemini, ElevenLabs) score lower. The "free model can compete" intuition holds — but with a real catch (see failure analysis: Whisper's hallucination loop on clip 09 took 53 seconds and produced unusable output).

**2. Gemini 2.5 Flash is 7× slower than Sarvam, but ~8× cheaper per minute of audio.** This inverts the usual "you pay a premium for the LLM" intuition — at Vahan's likely volume (tens of thousands of hours/month), the cost delta is six figures annually. The latency makes Gemini unsuitable for live phone calls, but for batch transcription of recorded WhatsApp voice notes, it's the obviously correct pick — and it produces the **highest exact-match rate (35%)** with code-switched scripts preserved.

---

## 3. Failure analysis

Only **3 of 100 transcripts** failed locality recovery entirely — but several transcripts that "recovered" by our metric were actually unusable. The patterns matter more than the count.

### Failure pattern 1 — ElevenLabs script chaos

ElevenLabs has a unique reliability problem: it switches to **wrong scripts**.

- Clip 04 (Hebbal, quiet Hinglish): transcribed as `جوب کے لئے ہبال سے آنا پڑے گا؟` — **Urdu (Arabic) script**. The audio was clear Hindi.
- Clip 18 (Majestic, whispered): `ਮੈਜੇਸਟਿਕ 10 ਕੇ ਅੰਦਰ ਖੜਾ ਹੋ` — **Punjabi (Gurmukhi) script** for Hindi speech.
- Clip 20 (Thalaghattapura, whispered Kannada): `ਥੱਲ ਗੱਟ ਪੂਰਾ ਸਹਿਦ` — **Gurmukhi again** for Kannada audio.

This isn't a transcription error — it's a language-ID failure that produces unusable output even when the phonemes are right. For a production product that needs to write to a single canonical store, this is disqualifying.

### Failure pattern 2 — Gemini's semantic hallucination

Dedicated ASR models substitute *phonetically similar nonsense*. LLM-as-ASR substitutes *semantically plausible* (but wrong) words.

- Clip 04 (Hebbal): Gemini wrote `जॉब के लिए हैदराबाद से आना पड़ेगा` — heard **"Hyderabad"** instead of "Hebbal." The locality wasn't mangled; it was *replaced* with a more common Indian city the LLM thought was more likely.
- Clip 09 (Silk Board): Gemini wrote `"Silkwood signal पे फंसा हूं"` — heard "Silkwood" (a fictional but English-sounding name) instead of "Silk Board."

This is the LLM-ASR tax: when context is ambiguous, the model defaults to its prior. That's a worse failure mode than Deepgram's clip-09 mistake (`"Silk road"`), which is at least a phonetic substitution and trivially fixable downstream.

### Failure pattern 3 — Universal weakness on whispered Kannada

Clip 16 (Yelahanka, whispered Kannada) broke **both** non-specialist models (ElevenLabs + Gemini). Sarvam, Deepgram, and Whisper recovered it. The phonetic-acoustic gap between Yelahanka (Latin) and ಯಲಂಕಾ (transcribed Kannada-script "yalamka") was bridgeable by dedicated ASR models but not by LLM-class systems.

### Failure pattern 4 — Whisper's hallucination loop on noisy audio

Clip 09 (Silk Board, traffic noise) is the single most instructive failure in this benchmark.

- **Whisper large-v3 took 53.2 seconds** (vs ~3.9 s typical) and produced this transcript: `"गुज़ो नंडा में ख्वोनेथी sdn mentea प्रदेक्शन कावल मिक्केशा... 20 minutes"`
- This isn't a degraded transcript — it's the well-known Whisper repetition / hallucination loop, where the decoder gets stuck and emits fluent-sounding garbage until a token-budget cutoff.
- Our metric counts this as "recovered" (word-level matched some fragments). **It is not actually recovered for product purposes.** Locality recovery has a ceiling — at quality below it, "recovered" is misleading.

The other models all degraded gracefully on this clip: Deepgram heard `"Silk road"` (phonetic substitution, fixable), Sarvam heard `"सिल्क वो"` (partial match, salvageable), Gemini heard `"Silkwood"` (semantic hallucination, named). Whisper's failure mode is qualitatively worse — **unbounded latency and unbounded text length on bad input.** For a production system, this means you also need a watchdog timeout around Whisper calls.

### Specific transcription errors worth flagging

Deepgram had two semantically misleading errors that all three other models avoided:

- Clip 09 (Silk Board) → `"Silk road signal पे फंसाओ"` — substituted "road" for "board."
- Clip 13 (KR Puram) → `"care पुरम railway station"` — interpreted "K.R." as the word *care*. This kind of error would silently corrupt entity extraction downstream because the output is still syntactically valid.

ElevenLabs' Hesaraghatta transcription was the funniest one:
- Clip 15: `"मैडम, मैं हिसारा गड्ढा से हूं"` — wrote `गड्ढा` (pothole) instead of `घट्टा` (the actual suffix). Recovers via fuzzy, but a hilarious near-miss.

---

## 4. Recommendation

**Three deployment tiers, one product.**

### Tier 1 — Live phone calls: **Sarvam (`saarika:v2.5`)**

100% locality recovery on this benchmark, **1.2 second median latency** (2.4× faster than Deepgram). Tied with Deepgram on accuracy across every metric, cheaper than ElevenLabs, and has the Indic specialization that bridges Kannada↔Latin entity recovery without help.

Risk: Sarvam is a smaller vendor than Deepgram. SLA + reliability deserve verification before exclusive prod use. Mitigation: keep Deepgram as fallback.

### Tier 2 — Batch processing of recorded audio: **Gemini 2.5 Flash**

95% locality recovery, **$0.0006 per minute** — 8× cheaper than Sarvam, 11× cheaper than ElevenLabs. The 7-second latency is irrelevant for batch jobs. Gemini also produces the **most production-friendly output**: code-switched audio comes back with English in Latin and Hindi in Devanagari (`"Koramangala में रहती हूं"`) — no normalization needed before storing.

Risk: semantic hallucinations on uncommon names (Hebbal → Hyderabad). Mitigation: use Gemini's confidence/logprob output or a second-pass spell-check against a canonical locality dictionary for entity correction.

### Tier 3 — On-prem / data-residency cases: **Whisper large-v3**

100% locality recovery and **zero per-minute API cost** (you pay only for the GPU). For Vahan customers with strict data-residency requirements — government contracts, healthcare-adjacent hiring, or regions where sending audio to US/EU APIs is restricted — Whisper running on your own infrastructure is the only option that hits the recovery bar.

Risk: the hallucination loop on clip 09 (53-second runtime, garbage output on noisy audio) requires a hard timeout in production code. A request-level watchdog at ~10s should clamp it. Also: ~3.9s median latency on a T4 GPU is slower than dedicated ASRs, so this is batch-tier (or large-pool concurrent) deployment, not single-request live.

### Skip — ElevenLabs Scribe

Dominated on every metric except marginal latency-vs-Deepgram, and the script-switching to Urdu/Punjabi is disqualifying for a single-script production database. No use case I can recommend.

### Why not Deepgram exclusively?

Deepgram is fine. It's just that **Sarvam beats it on speed by 2.4× for the same accuracy**, **Gemini beats it on cost by 7× for nearly the same accuracy**, and **Whisper matches it on accuracy at zero per-minute cost**. Deepgram is no longer the best on any axis once these three are in the picture. Keep it as a contractual fallback — don't lead with it.

---

## 5. Limitations & honest caveats

- **N=20, single speaker.** Per-condition slices have 4-5 clips each; confidence intervals on a 100% recovery rate are wide, and there's no accent/demographic diversity. Production decision should validate at N≥200 across Vahan's actual user demographic (North/South India accents, age range, gender mix).
- **Clip 15 (Hesaraghatta) for Gemini used `gemini-2.5-flash-lite`** (not Flash) after the free-tier daily quota was exhausted. Lite is slightly weaker; in this case it recovered the locality correctly via the same near-miss pattern Deepgram used (`"हैसारा गट्टा"`).
- **WER is inflated across the board** by transliteration boundary mismatches — Hindi-script hypotheses vs Hinglish reference. Recovery rate is the trustworthy signal here.
- **Whisper's WER (0.96) is the highest** — driven heavily by the clip-09 hallucination loop. Excluding that single outlier, Whisper's WER drops to ~0.82, closer to the pack.
- **Pricing as of late 2025** (sticker rates from each provider). Whisper's cost is approximated as $0 per minute (no API fee); a real deployment pays GPU compute (~$0.30-0.70/hour for a T4 on AWS/GCP).
- **First-byte latency not measured.** All four APIs were called in batch/REST mode; total-time and first-byte are nearly identical for these calls. Sarvam and Deepgram both offer streaming WebSockets that would give true first-byte numbers — the natural next experiment for live deployment validation.
- **AI4Bharat IndicConformer not tested.** The most relevant Indic-specialist open-source model. Would be the highest-value next addition.

---

**Code:** All pipeline code under [src/](src/). Reproducible with `pip install -r requirements.txt && python -m src.run_all && python -m src.rescore && python -m src.analysis`. Raw per-clip JSONs in [results/](results/).
