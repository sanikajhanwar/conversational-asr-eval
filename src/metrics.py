"""ASR metrics: WER + locality entity matching (exact / fuzzy / phonetic).

The locality-entity metrics are the ones that actually matter for this use case.
WER is reported because it's the industry default, but a model can have great WER
and still fumble the locality name — which is the whole point of the product.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import jiwer
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from metaphone import doublemetaphone
from rapidfuzz import fuzz


# --- normalization helpers -------------------------------------------------

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")

# Unicode codepoint ranges → indic-transliteration scheme
_SCRIPT_RANGES = [
    (0x0900, 0x097F, sanscript.DEVANAGARI),
    (0x0C80, 0x0CFF, sanscript.KANNADA),
    (0x0A00, 0x0A7F, sanscript.GURMUKHI),
    (0x0980, 0x09FF, sanscript.BENGALI),
    (0x0B80, 0x0BFF, sanscript.TAMIL),
    (0x0C00, 0x0C7F, sanscript.TELUGU),
    (0x0D00, 0x0D7F, sanscript.MALAYALAM),
    (0x0A80, 0x0AFF, sanscript.GUJARATI),
]

# Modern Hindi Devanagari additions (mostly for English loanwords) that the
# Harvard-Kyoto scheme handles poorly. Normalize them to their classical
# equivalents *before* transliteration so the loanwords come out clean.
# Example: इलेक्ट्रॉनिक (with ॉ) → इलेक्ट्रोनिक (with ो) → "ilekTronika"
_DEV_FOLD = {
    "ॉ": "ो", "ॅ": "े", "ऍ": "ए", "ऑ": "ओ",
    # Nukta-modified consonants used for Urdu/Persian loanwords
    "क़": "क", "ख़": "ख", "ग़": "ग", "ज़": "ज",
    "ड़": "ड", "ढ़": "ढ", "फ़": "फ", "य़": "य",
}


def _detect_scripts(text: str) -> set[str]:
    """Return the set of Indic scripts present in `text` (by codepoint range)."""
    found = set()
    for ch in text:
        cp = ord(ch)
        for lo, hi, scheme in _SCRIPT_RANGES:
            if lo <= cp <= hi:
                found.add(scheme)
                break
    return found


def _fold_devanagari(text: str) -> str:
    """Replace modern Hindi-only Devanagari chars with classical equivalents."""
    for src, dst in _DEV_FOLD.items():
        text = text.replace(src, dst)
    return text


def to_latin(text: str) -> str:
    """Transliterate any Indic-script segments in `text` to Latin (Harvard-Kyoto).

    Latin chars and characters in unsupported scripts (e.g. Arabic/Urdu) pass through.
    HK is chosen because it produces ASCII without diacritics — easier downstream.
    """
    if not text:
        return text
    text = _fold_devanagari(text)
    for scheme in _detect_scripts(text):
        text = transliterate(text, scheme, sanscript.HK)
    return text


def normalize_text(text: str) -> str:
    """Lowercase + transliterate Indic → Latin + strip punctuation + collapse whitespace.

    Used for WER, exact match, and as input to fuzzy/phonetic.
    Transliteration is the key new step: Devanagari "कोरमंगला" → "koramaMgalA" →
    lowercase "koramamgala" — which then fuzzy-matches "koramangala" cleanly.
    """
    if not text:
        return ""
    text = to_latin(text)
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


# --- WER -------------------------------------------------------------------

def compute_wer(reference: str, hypothesis: str) -> float:
    """Standard Word Error Rate (lower is better, 0.0 = perfect)."""
    ref = normalize_text(reference)
    hyp = normalize_text(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return jiwer.wer(ref, hyp)


# --- locality entity matching ----------------------------------------------

@dataclass
class LocalityMatch:
    exact: bool
    fuzzy: bool                       # any whole-string fuzzy strategy >= threshold
    fuzzy_score: float                # best whole-string score seen (0-100)
    phonetic: bool                    # whole-string metaphone substring/partial match
    word_level: bool                  # every target word found a fuzzy/phonetic match
    matched_substring: str | None     # winning strategy name (debugging)

    @property
    def recovered(self) -> bool:
        """Locality is considered captured if ANY of the four checks succeeded."""
        return self.exact or self.fuzzy or self.phonetic or self.word_level


def _best_fuzzy(target: str, hypothesis: str) -> tuple[float, str]:
    """Find the best fuzzy-match score for `target` inside `hypothesis`.

    Tries multiple strategies and returns the best:
      - partial_ratio:           best alignment of target as substring
      - partial_ratio collapsed: same but spaces removed (catches token-split noise)
      - token_set_ratio:         tokens of target found across hypothesis tokens
      - WRatio:                  rapidfuzz's weighted multi-strategy fallback

    Returns (score, strategy_name) where strategy_name records which one won
    — useful for debugging "why did this match?".
    """
    if not target or not hypothesis:
        return 0.0, ""

    target_collapsed = target.replace(" ", "")
    hyp_collapsed = hypothesis.replace(" ", "")

    candidates = [
        (fuzz.partial_ratio(target, hypothesis),                     "partial_ratio"),
        (fuzz.partial_ratio(target_collapsed, hyp_collapsed),        "partial_ratio_nospace"),
        (fuzz.token_set_ratio(target, hypothesis),                   "token_set_ratio"),
        (fuzz.WRatio(target, hypothesis),                            "WRatio"),
    ]
    score, strategy = max(candidates, key=lambda x: x[0])
    return float(score), strategy


def _metaphone_match(target: str, hypothesis: str, fuzz_threshold: float = 80.0) -> bool:
    """True if target's metaphone code appears in hypothesis's, allowing fuzzy match.

    Computes double-metaphone for both the target (spaces removed) and the entire
    hypothesis (spaces removed). Matches if the target's primary or secondary code
    is a substring of the hypothesis's — or a high partial-ratio fuzzy match.
    """
    if not target or not hypothesis:
        return False

    t_codes = doublemetaphone(target.replace(" ", ""))
    h_codes = doublemetaphone(hypothesis.replace(" ", ""))

    for t in t_codes:
        if not t or len(t) < 3:
            continue
        for h in h_codes:
            if not h:
                continue
            if t in h:
                return True
            if fuzz.partial_ratio(t, h) >= fuzz_threshold:
                return True
    return False


def _word_level_match(
    target: str,
    hypothesis: str,
    per_word_fuzz_threshold: float = 75.0,
    per_word_phonetic_threshold: float = 80.0,
) -> bool:
    """For multi-word localities: each word in target must find a match in hypothesis.

    A target word matches a hypothesis word if either:
      - partial_ratio >= per_word_fuzz_threshold, OR
      - metaphone codes substring-match (or partial_ratio on codes >= phonetic_threshold)

    This catches cases like "Electronic City" vs "ilektronika siti" where the whole-string
    fuzzy fails (~67%) but each word matches strongly when scored independently.
    """
    if not target or not hypothesis:
        return False

    target_words = [w for w in target.split() if w]
    hyp_words = [w for w in hypothesis.split() if w]
    if not target_words or not hyp_words:
        return False

    for tw in target_words:
        # Try fuzzy partial_ratio on each hyp word
        fuzzy_hit = any(fuzz.partial_ratio(tw, hw) >= per_word_fuzz_threshold
                        for hw in hyp_words)
        if fuzzy_hit:
            continue

        # Try phonetic match on each hyp word
        tw_codes = doublemetaphone(tw)
        phonetic_hit = False
        for hw in hyp_words:
            hw_codes = doublemetaphone(hw)
            for tc in tw_codes:
                if not tc or len(tc) < 2:
                    continue
                for hc in hw_codes:
                    if not hc:
                        continue
                    if tc in hc or hc in tc:
                        phonetic_hit = True
                        break
                    if fuzz.partial_ratio(tc, hc) >= per_word_phonetic_threshold:
                        phonetic_hit = True
                        break
                if phonetic_hit:
                    break
            if phonetic_hit:
                break

        if not phonetic_hit:
            return False   # this target word couldn't find a match → fail

    return True


def match_locality(
    canonical: str,
    aliases: list[str],
    hypothesis: str,
    fuzzy_threshold: float = 80.0,
) -> LocalityMatch:
    """Check whether the locality name is recoverable from the hypothesis transcript.

    Returns three independent verdicts:
    - exact:    canonical (or alias) appears as a substring after normalization
    - fuzzy:    best of {partial_ratio, token_set_ratio, WRatio} >= threshold
    - phonetic: double-metaphone code of target substring-matches hypothesis's
    """
    hyp_norm = normalize_text(hypothesis)

    # --- exact: canonical / alias appears as substring (with and without spaces) ---
    targets = [normalize_text(canonical)] + [normalize_text(a) for a in aliases]
    targets = [t for t in targets if t]
    hyp_collapsed = hyp_norm.replace(" ", "")
    exact = any(
        t in hyp_norm or t.replace(" ", "") in hyp_collapsed
        for t in targets
    )

    # --- fuzzy: against canonical (aliases already covered by exact) ---
    canonical_norm = normalize_text(canonical)
    fuzzy_score, strategy = _best_fuzzy(canonical_norm, hyp_norm)
    fuzzy = fuzzy_score >= fuzzy_threshold

    # --- phonetic (whole-string) ---
    phonetic = _metaphone_match(canonical_norm, hyp_norm)

    # --- word-level (handles multi-word names with transliteration noise) ---
    word_level = _word_level_match(canonical_norm, hyp_norm)

    return LocalityMatch(
        exact=exact,
        fuzzy=fuzzy,
        fuzzy_score=fuzzy_score,
        phonetic=phonetic,
        word_level=word_level,
        matched_substring=strategy or None,
    )


# --- combined per-clip scoring --------------------------------------------

def score_clip(
    reference_sentence: str,
    locality_canonical: str,
    locality_aliases: list[str],
    hypothesis: str,
) -> dict:
    """One-stop scoring: WER + all three locality matches.

    Returns a dict suitable for appending to a results DataFrame.
    """
    wer = compute_wer(reference_sentence, hypothesis)
    match = match_locality(locality_canonical, locality_aliases, hypothesis)
    return {
        "wer": wer,
        "locality_exact": match.exact,
        "locality_fuzzy": match.fuzzy,
        "locality_fuzzy_score": match.fuzzy_score,
        "locality_phonetic": match.phonetic,
        "locality_word_level": match.word_level,
        "locality_recovered": match.recovered,
        "matched_substring": match.matched_substring,
    }


if __name__ == "__main__":
    # Smoke test
    ref = "Haan bhaiya, main Koramangala mein rehta hoon, 5th block."
    cases = [
        ("perfect", "Haan bhaiya main Koramangala mein rehta hoon 5th block"),
        ("misspelled", "Haan bhaiya main Koramangla mein rehta hoon 5th block"),
        ("split", "Haan bhaiya main kora mangala mein rehta hoon 5th block"),
        ("totally wrong", "yes brother I live in chord mangle area"),
    ]
    for label, hyp in cases:
        s = score_clip(ref, "Koramangala", ["koramangla", "koramangaala"], hyp)
        print(f"{label:<15} WER={s['wer']:.2f}  exact={s['locality_exact']}  "
              f"fuzzy={s['locality_fuzzy']}({s['locality_fuzzy_score']:.0f})  "
              f"phonetic={s['locality_phonetic']}")
