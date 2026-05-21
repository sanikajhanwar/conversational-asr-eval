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
from metaphone import doublemetaphone
from rapidfuzz import fuzz


# --- normalization helpers -------------------------------------------------

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Lowercase + strip punctuation + collapse whitespace + Unicode NFKD.

    Used for WER, exact match, and as input to fuzzy/phonetic.
    """
    if not text:
        return ""
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
    fuzzy: bool         # Levenshtein ratio >= 0.85 on any token window
    fuzzy_score: float  # best ratio seen (0-100)
    phonetic: bool      # Metaphone code match on any window
    matched_substring: str | None  # the actual substring from hypothesis that matched best


def _tokenize(text: str) -> list[str]:
    return normalize_text(text).split()


def _candidates_for_name(name: str) -> list[str]:
    """Generate normalized variants of a locality name to match against."""
    norm = normalize_text(name)
    return [norm, norm.replace(" ", "")]


def _windows(tokens: list[str], n: int) -> list[str]:
    """Return all sliding-window joins of n consecutive tokens."""
    if n <= 0 or len(tokens) < n:
        return []
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def _best_fuzzy(target: str, hypothesis_tokens: list[str]) -> tuple[float, str]:
    """Find the substring window in hypothesis with the highest fuzzy ratio to target."""
    target_n = len(target.split())
    # Try windows of size target_n-1, target_n, target_n+1 to be lenient on token boundaries
    candidates: list[str] = []
    for n in {max(1, target_n - 1), target_n, target_n + 1}:
        candidates.extend(_windows(hypothesis_tokens, n))
    # Also consider raw joined tokens (catches concatenated transcripts)
    candidates.append("".join(hypothesis_tokens))

    if not candidates:
        return 0.0, ""
    best = max(candidates, key=lambda c: fuzz.ratio(target, c))
    return fuzz.ratio(target, best), best


def _metaphone_match(target: str, hypothesis_tokens: list[str]) -> bool:
    """True if the primary metaphone code of target appears in any hypothesis window."""
    target_code = doublemetaphone(target.replace(" ", ""))[0]
    if not target_code:
        return False
    target_n = max(1, len(target.split()))
    for n in {max(1, target_n - 1), target_n, target_n + 1}:
        for w in _windows(hypothesis_tokens, n):
            code = doublemetaphone(w.replace(" ", ""))[0]
            if code and code == target_code:
                return True
    return False


def match_locality(
    canonical: str,
    aliases: list[str],
    hypothesis: str,
    fuzzy_threshold: float = 85.0,
) -> LocalityMatch:
    """Check whether the locality name is recoverable from the hypothesis transcript.

    Returns three independent verdicts:
    - exact: canonical (or alias) appears as a substring after normalization
    - fuzzy: best Levenshtein ratio against canonical >= threshold
    - phonetic: double-metaphone code matches

    `matched_substring` is the hypothesis chunk that scored highest for fuzzy —
    useful for debugging ("model wrote 'kora mangala' instead of 'koramangala'").
    """
    hyp_norm = normalize_text(hypothesis)
    hyp_tokens = hyp_norm.split()

    # --- exact ---
    targets = [normalize_text(canonical)] + [normalize_text(a) for a in aliases]
    targets = [t for t in targets if t]
    exact = any(t in hyp_norm or t.replace(" ", "") in hyp_norm.replace(" ", "")
                for t in targets)

    # --- fuzzy --- (against canonical only; aliases are for exact-match leniency)
    canonical_norm = normalize_text(canonical)
    fuzzy_score, matched = _best_fuzzy(canonical_norm, hyp_tokens) if hyp_tokens else (0.0, "")
    fuzzy = fuzzy_score >= fuzzy_threshold

    # --- phonetic ---
    phonetic = _metaphone_match(canonical_norm, hyp_tokens) if hyp_tokens else False

    return LocalityMatch(
        exact=exact,
        fuzzy=fuzzy,
        fuzzy_score=fuzzy_score,
        phonetic=phonetic,
        matched_substring=matched or None,
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
