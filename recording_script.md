# Recording Script — 20 Audio Samples

> Read this whole file once before you start recording. The structure matters more than perfection — the goal is **realistic, varied speech**, not clean studio audio.

---

## How to use this file

1. Pick a quiet recording app on your phone (default Voice Recorder, or apps like **Easy Voice Recorder**, **Smart Recorder**, or even **WhatsApp voice note** then export).
2. Format: **WAV or M4A**, mono, whatever default sample rate your phone uses is fine (16 kHz or 48 kHz both work).
3. Go through the table below **row by row**. For each row:
   - Read the **"Setting"** column carefully — go to that location / set up that condition.
   - Read the sentence aloud the way the **"Style"** column describes.
   - Save with the exact filename in the **"Filename"** column.
4. **Don't read like you're reading.** Glance at the sentence once, then say it like you're actually telling someone. Pauses, "uhh," "haan," small mistakes — all welcome.

---

## Why these 20 (out of 30 listed in the PDF)

The PDF gives 30 localities but asks for 20 recordings. We're picking a deliberate mix:

| Difficulty tier | Why include them                                            | Count |
|-----------------|-------------------------------------------------------------|-------|
| **Easy / famous** (e.g. Koramangala, Whitefield) | Every ASR should get these. Baseline check.                 | 10    |
| **Medium** (e.g. Banashankari, KR Puram)         | Common but trickier phonetics.                              | 5     |
| **Hard / long Kannada** (e.g. Byatarayanapura)   | This is where models break. Best material for failure analysis. | 5     |

If every model nails the easy ones and dies on the hard ones, **that's the story** the report tells.

---

## Condition distribution

The 20 clips are split 5 × 4 across conditions, so we can slice results by audio environment:

| Condition           | Count | What to do                                                                                       |
|---------------------|-------|--------------------------------------------------------------------------------------------------|
| **Quiet**           | 5     | Closed room, no fan, no music, no TV. Sit close to phone mic.                                    |
| **Traffic / outdoor** | 5   | Balcony, near a window with traffic, or outside. You should *hear* background noise in playback. |
| **Phone-call style** | 5    | Hold the phone ~15-20 cm away from your face, slight angle. Like an actual phone call would sound. Or call yourself on another device & record from the receiving side. |
| **Whispered / rushed** | 5  | Either whisper quietly OR speak very fast (~1.5x normal speed). Like you're in a hurry or being discreet. |

---

## Language distribution

Mix it up so we test code-switching too:

| Language style    | Count | Example                                                  |
|-------------------|-------|----------------------------------------------------------|
| **Hindi-heavy**   | 7     | "Haan main Koramangala mein rehta hoon"                  |
| **Hinglish**      | 8     | "Bro, Indiranagar side hai mera flat"                    |
| **English with locality** | 3 | "I stay in HSR Layout, near the metro"                 |
| **Kannada-flavored** | 2  | "Naanu Yelahankadalli iddeene" (use if comfortable)      |

If Kannada feels forced, switch those two to Hinglish — natural-sounding wins over linguistic accuracy.

---

## The 20 Recordings

> **Filename format:** `NN_locality_condition_language.wav`
> Example: `03_whitefield_traffic_english.wav`

### 🟢 Quiet (5)

| #  | Locality            | Filename                                  | Language | Style instruction                                | Sentence to say                                                                            |
|----|---------------------|-------------------------------------------|----------|--------------------------------------------------|--------------------------------------------------------------------------------------------|
| 01 | Koramangala         | `01_koramangala_quiet_hinglish.wav`       | Hinglish | Calm, conversational, like answering a question  | "Haan bhaiya, main **Koramangala** mein rehta hoon, 5th block."                            |
| 02 | Indiranagar         | `02_indiranagar_quiet_hindi.wav`          | Hindi    | Casual, slightly slow                            | "Mera ghar **Indiranagar** mein hai, metro station ke paas."                              |
| 03 | HSR Layout          | `03_hsrlayout_quiet_english.wav`          | English  | Polite, professional tone                        | "Yes sir, I stay in **HSR Layout**, sector 2."                                            |
| 04 | Hebbal              | `04_hebbal_quiet_hinglish.wav`            | Hinglish | Confident, matter-of-fact                        | "Job ke liye **Hebbal** se aana padega, traffic kaisa hai?"                               |
| 05 | Byatarayanapura     | `05_byatarayanapura_quiet_hindi.wav`      | Hindi    | Slow, careful — this one is genuinely hard       | "Sir, mera address **Byatarayanapura** hai, paas mein bus stand hai."                     |

### 🟡 Traffic / Outdoor (5)

> Go to the balcony, a window facing the road, or step outside. There must be **audible** background noise — traffic, birds, fan, TV in another room, kids talking. Don't shout over it; speak normally and let the mic pick up both.

| #  | Locality          | Filename                                | Language | Style instruction                          | Sentence to say                                                                             |
|----|-------------------|------------------------------------------|----------|--------------------------------------------|---------------------------------------------------------------------------------------------|
| 06 | Whitefield        | `06_whitefield_traffic_english.wav`      | English  | Casual, slightly louder to be heard        | "I work in **Whitefield**, near the ITPL main road."                                       |
| 07 | Marathahalli      | `07_marathahalli_traffic_hinglish.wav`   | Hinglish | Like answering on a busy street            | "Haan, **Marathahalli** bridge ke neeche utar jaana, wahan se auto mil jaayega."           |
| 08 | Electronic City   | `08_electroniccity_traffic_hindi.wav`    | Hindi    | Slightly distracted, normal volume         | "Main **Electronic City** phase 1 mein rehta hoon, Infosys ke peeche."                     |
| 09 | Silk Board        | `09_silkboard_traffic_hinglish.wav`      | Hinglish | Slightly irritated, like stuck in traffic  | "**Silk Board** signal pe phasa hua hoon yaar, 20 minute se."                              |
| 10 | Kadugondanahalli  | `10_kadugondanahalli_traffic_hindi.wav`  | Hindi    | Stumble a little — it's a tongue-twister   | "Mera area ka naam **Kadugondanahalli** hai, KG Halli bolte hain log."                     |

### 🔵 Phone-call style (5)

> Hold the phone **15-20 cm from your face**, slightly off-angle (like you'd hold it in a real call, not pressed to your ear). Or — better — call yourself on a second phone/laptop using WhatsApp, and record the call on the receiving end. The audio should sound **slightly muffled, compressed, distant** compared to the quiet clips.

| #  | Locality          | Filename                                  | Language | Style instruction                              | Sentence to say                                                                            |
|----|-------------------|-------------------------------------------|----------|------------------------------------------------|--------------------------------------------------------------------------------------------|
| 11 | Jayanagar         | `11_jayanagar_phone_hinglish.wav`         | Hinglish | Polite, like talking to a recruiter            | "Sir mera naam Ravi hai, main **Jayanagar** 4th block se baat kar raha hoon."              |
| 12 | BTM Layout        | `12_btmlayout_phone_hindi.wav`            | Hindi    | Normal phone-call tone                         | "**BTM Layout** mein flat dekhna hai, kya aap free ho kal?"                                |
| 13 | KR Puram          | `13_krpuram_phone_hinglish.wav`           | Hinglish | Slightly louder, like reception is bad         | "Haan haan, **KR Puram** railway station ke paas, wahan ruko."                             |
| 14 | Bellandur         | `14_bellandur_phone_english.wav`          | English  | Professional phone tone                        | "I'm currently in **Bellandur**, can the delivery come here by 6?"                         |
| 15 | Hesaraghatta      | `15_hesaraghatta_phone_hindi.wav`         | Hindi    | Slow because the name is hard                  | "Madam, main **Hesaraghatta** se hoon, gaon ki taraf."                                     |

### 🔴 Whispered / Rushed (5)

> Either **whisper** quietly (like you're in a library or someone is sleeping nearby) OR **speak very fast** (like you're late and explaining quickly). Pick whichever feels natural per row.

| #  | Locality              | Filename                                       | Language       | Style instruction                       | Sentence to say                                                                          |
|----|-----------------------|------------------------------------------------|----------------|-----------------------------------------|------------------------------------------------------------------------------------------|
| 16 | Yelahanka             | `16_yelahanka_whisper_kannada.wav`             | Kannada-flavored | Whispered, soft voice                 | "Naanu **Yelahanka**dalli iddeene, airport hattira."                                     |
| 17 | Banashankari          | `17_banashankari_rushed_hinglish.wav`          | Hinglish       | Fast, like you're in a rush             | "Yaar jaldi bata, **Banashankari** se Majestic kitne kilometre hai?"                     |
| 18 | Majestic              | `18_majestic_whisper_hindi.wav`                | Hindi          | Whispered, quiet                        | "**Majestic** bus stand ke andar khada hoon, mil jaaoge?"                                |
| 19 | Rajarajeshwarinagar   | `19_rajarajeshwarinagar_rushed_hindi.wav`      | Hindi          | Fast — stumble on the name is fine     | "**Rajarajeshwarinagar** mein interview hai, address bhej raha hoon abhi."               |
| 20 | Thalaghattapura       | `20_thalaghattapura_whisper_kannada.wav`       | Kannada-flavored | Whispered, slow                       | "**Thalaghattapura** side, NICE road ke paas, samjha?"                                   |

---

## Quick checklist before you start

- [ ] Phone is **not** on silent/airplane mode (some recorders block audio on silent)
- [ ] Recorder app is set to a format you can export (WAV / M4A — not proprietary)
- [ ] You've picked a quiet room for clips 01-05
- [ ] You know which balcony/window/outdoor spot you'll use for 06-10
- [ ] You have a way to do clips 11-15 (phone at distance OR self-call)
- [ ] Phone storage has at least 100 MB free
- [ ] You have **30-40 minutes** of uninterrupted time (recording is fast, but mistakes happen)

---

## Tips for natural-sounding recordings

1. **Read the sentence once silently, then look up.** Don't read aloud while staring at the screen — it sounds wooden.
2. **It's okay to mess up.** If you say "umm" or restart mid-sentence, that's *more* realistic, not less. Don't re-record unless the locality name itself was wrong or the audio is unusable (clipped, silent, totally garbled).
3. **Vary your tone.** Some clips should sound friendly, some annoyed, some tired, some hurried. Real people aren't monotone.
4. **Don't over-enunciate the locality name.** Say it the way you'd actually say it in conversation. If you'd casually drop the last syllable of "Koramangala" → do that. We *want* that data.
5. **Length:** 3-8 seconds per clip is ideal. Anything over 15 seconds is too long; under 2 is too short.

---

## After you record

1. Transfer all 20 files to your laptop (USB cable, AirDrop, Google Drive, WhatsApp to yourself — whatever's fastest).
2. Drop them into the `recordings/` folder inside this project.
3. Make sure filenames match the table above. **Filename consistency matters** — the code reads `recordings/01_*.wav` automatically.
4. Tell me you're done — I'll verify all 20 are loadable and we move to Day 2.

---

## What if a clip turns out bad?

**Don't redo all 20.** Just redo the broken ones. A clip is "bad" if:
- It's silent or you can't hear yourself
- The locality name is missing or wrong (you said "Indiranagar" instead of "Whitefield")
- Audio is severely clipped (sounds like buzzing distortion throughout)

Background noise is **not** a reason to redo — that's literally the point of half the clips.

---

## Why this design

Three things this script is optimizing for:

1. **Real-world variation** — different conditions, different sentence shapes, different languages. A model that wins on quiet Hindi might lose on whispered Kannada.
2. **Diagnostic value** — clips are spread across the difficulty × condition grid so when we look at failures, we can isolate the cause (audio quality? language? specific name?).
3. **Honesty** — natural mistakes (stumbles, "umm"s) stay in. That's the speech these models will actually face in production at Vahan.

Now go record. It'll take you 30-40 minutes. Ping me when you're done.
