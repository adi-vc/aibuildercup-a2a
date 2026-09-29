"""
verifier.py — Mechanical span verifier (vachan-plan.md §39.1).

The guarantee: a fact is `canon` ONLY when its `quote` is located in the raw
source by a normalized string match.  No model is involved in this decision.

Algorithm (§39.1):
  1. Normalize both strings: collapse whitespace, casefold, strip runs of
     punctuation (keeps alphanumerics and single spaces).
  2. Exact substring search in the normalized source.
  3. If not found, fuzzy token-set-ratio (rapidfuzz) ≥ FUZZY_THRESHOLD.
     On a match, store the matched offsets from the normalized source.
  4. If still not found → demote origin to `inferred`; do NOT discard the fact
     (the operator sees it at gate 1 and can correct or drop it).

Returns a VerificationResult that callers attach to each fact before writing
to Firestore.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

# A fuzzy score of 95 means the strings are nearly identical after token
# reordering — enough to catch minor OCR or copy-paste drift while still
# blocking genuine paraphrases.  This is config, not magic.
FUZZY_THRESHOLD: int = 95


# ── Normalisation ─────────────────────────────────────────────────────────────

_WHITESPACE = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^\w\s]", re.UNICODE)


def _normalize(text: str) -> str:
    """
    Collapse whitespace, casefold, strip punctuation, NFC-normalize.

    "wades through water up to 30 cm deep."
      → "wades through water up to 30 cm deep"

    The normalized form is used ONLY for matching; the original source text is
    what gets stored in the Span record.
    """
    text = unicodedata.normalize("NFC", text)
    text = _NON_ALNUM.sub(" ", text)
    text = _WHITESPACE.sub(" ", text)
    return text.casefold().strip()


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class VerificationResult:
    verified: bool
    method: str          # "exact" | "fuzzy" | "failed"
    score: float         # 100.0 for exact, fuzzy score otherwise, 0.0 on failure
    # Character offsets in the *original* source text (best-effort for fuzzy).
    start: int = -1
    end: int = -1
    matched_text: str = ""   # the substring of the source that matched


# ── Public API ────────────────────────────────────────────────────────────────

def verify_span(quote: str, raw_source: str) -> VerificationResult:
    """
    Attempt to locate `quote` in `raw_source`.

    `quote` is the verbatim string the extractor copied from the source.
    `raw_source` is the full HTML/text of the ingested document.

    Returns a VerificationResult; callers set fact.origin to `canon` iff
    result.verified is True.
    """
    if not quote or not raw_source:
        return VerificationResult(verified=False, method="failed", score=0.0)

    norm_quote = _normalize(quote)
    norm_source = _normalize(raw_source)

    # ── Pass 1: exact normalized substring ───────────────────────────────────
    idx = norm_source.find(norm_quote)
    if idx != -1:
        # Map back to a rough offset in the original source.
        # We search the original for the original quote to get a clean offset.
        orig_idx = _find_original_offset(quote, raw_source)
        end = orig_idx + len(quote) if orig_idx != -1 else -1
        return VerificationResult(
            verified=True,
            method="exact",
            score=100.0,
            start=orig_idx,
            end=end,
            matched_text=quote,
        )

    # ── Pass 2: fuzzy token-set ratio ────────────────────────────────────────
    # Slide a window over the normalized source in chunks roughly the size of
    # the quote, scoring each.  Using a window avoids comparing the quote
    # against the entire document (which would inflate the score).
    best_score, best_start, best_text = _fuzzy_search(norm_quote, norm_source, raw_source)

    if best_score >= FUZZY_THRESHOLD:
        return VerificationResult(
            verified=True,
            method="fuzzy",
            score=best_score,
            start=best_start,
            end=best_start + len(best_text),
            matched_text=best_text,
        )

    # ── Failed ───────────────────────────────────────────────────────────────
    return VerificationResult(verified=False, method="failed", score=best_score)


def compute_coverage(results: list[VerificationResult]) -> float:
    """
    coverage = verified_count / total_count  (returns 1.0 for an empty list).
    """
    if not results:
        return 1.0
    verified = sum(1 for r in results if r.verified)
    return verified / len(results)


# ── Internals ─────────────────────────────────────────────────────────────────

def _find_original_offset(quote: str, source: str) -> int:
    """
    Case-insensitive substring search in the original (non-normalized) source,
    used to get a clean character offset for the Span record.
    """
    idx = source.lower().find(quote.lower())
    return idx  # -1 if not found


def _fuzzy_search(
    norm_quote: str,
    norm_source: str,
    orig_source: str,
    step_factor: float = 0.5,
) -> tuple[float, int, str]:
    """
    Slide a window of `len(norm_quote) * (1 + step_factor)` characters over
    `norm_source`, scoring each window with token_set_ratio.

    Returns (best_score, best_start_in_original, best_window_text).
    """
    q_len = len(norm_quote)
    win_len = int(q_len * (1 + step_factor))
    best_score = 0.0
    best_start = -1
    best_text = ""

    # Slide in steps of roughly half the quote length for reasonable coverage
    # without being O(n²) on large documents.
    stride = max(1, q_len // 2)

    for i in range(0, max(1, len(norm_source) - win_len + 1), stride):
        window = norm_source[i : i + win_len]
        score = fuzz.token_set_ratio(norm_quote, window)
        if score > best_score:
            best_score = score
            # Map the normalized window index back to the original source.
            best_start = _approx_original_offset(i, norm_source, orig_source)
            best_text = orig_source[best_start : best_start + len(norm_quote) + 20]

    return best_score, best_start, best_text


def _approx_original_offset(norm_idx: int, norm_source: str, orig_source: str) -> int:
    """
    Approximate the original-source character offset that corresponds to
    `norm_idx` in the normalized source.  We do this by counting how many
    original characters were consumed to produce `norm_idx` normalized chars.

    This is a best-effort mapping; the exact span text for the badge comes
    from the original source slice, not this offset.
    """
    # Walk the original source, tracking how many normalized chars we've seen.
    norm_seen = 0
    for orig_i, ch in enumerate(orig_source):
        if norm_seen >= norm_idx:
            return orig_i
        norm_ch = _normalize(ch)
        norm_seen += len(norm_ch)
    return max(0, len(orig_source) - 1)
