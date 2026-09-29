"""
test_verifier.py — unit tests for the §39.1 mechanical span verifier.

These tests run fully offline (no Gemini, no GCS, no Firestore).
They directly test the guarantee: canon only when string-verified.
"""

import pytest
from app.services.verifier import verify_span, compute_coverage, FUZZY_THRESHOLD

# ── Fixtures ──────────────────────────────────────────────────────────────────

FIXTURE_SOURCE = open(
    __import__("pathlib").Path(__file__).parent.parent / "fixtures" / "vega_v1.html",
    encoding="utf-8",
).read()

# All 8 verbatim quotes from the fixture (§17)
VERBATIM_QUOTES = [
    "wades through water up to 30 cm deep",
    "certified range of 128 km per charge (IDC)",
    "0–60 km/h in 8.2 seconds",
    "0–80% in 4 hours 30 minutes",
    "ground clearance of 165 mm",
    "Mumbai on-road ₹1,29,900",
    "Bengaluru on-road ₹1,27,400",
    "3-year or 30,000 km battery warranty",
]


# ── Pass 1: exact matches ─────────────────────────────────────────────────────

@pytest.mark.parametrize("quote", VERBATIM_QUOTES)
def test_exact_match_all_fixture_quotes(quote: str) -> None:
    """Every verbatim quote from the fixture must verify as canon (exact method)."""
    result = verify_span(quote, FIXTURE_SOURCE)
    assert result.verified, f"Expected exact match for: {quote!r}"
    assert result.method == "exact"
    assert result.score == 100.0
    assert result.start >= 0


def test_exact_match_returns_correct_offset() -> None:
    """The returned start offset must point to the actual text in the source."""
    quote = "wades through water up to 30 cm deep"
    result = verify_span(quote, FIXTURE_SOURCE)
    assert result.verified
    # The character at offset `start` in the source should contain the quote
    assert FIXTURE_SOURCE[result.start : result.start + len(quote)].lower() == quote.lower()


# ── Pass 2: fuzzy matches ─────────────────────────────────────────────────────

def test_fuzzy_match_minor_punctuation_difference() -> None:
    """A quote with minor punctuation difference should still pass (fuzzy ≥ 95)."""
    # Remove a hyphen — still nearly identical
    quote = "3 year or 30,000 km battery warranty"
    result = verify_span(quote, FIXTURE_SOURCE)
    assert result.verified, "Minor punctuation variant should fuzzy-match"
    assert result.score >= FUZZY_THRESHOLD


def test_fuzzy_match_extra_whitespace() -> None:
    """Extra spaces in the quote normalize away and still match."""
    quote = "certified  range  of  128  km  per  charge"
    result = verify_span(quote, FIXTURE_SOURCE)
    assert result.verified, "Whitespace-bloated quote should still match"


# ── Deliberate failures: paraphrase → demote to inferred ─────────────────────

def test_paraphrase_fails_verification() -> None:
    """
    A paraphrase (not a verbatim quote) must NOT verify.
    This is the key safety test: the model paraphrasing instead of quoting
    must result in origin=inferred, not canon.
    """
    paraphrase = "The scooter can handle up to thirty centimetres of water"
    result = verify_span(paraphrase, FIXTURE_SOURCE)
    assert not result.verified, (
        "A paraphrase must fail — the guarantee is verbatim, not semantic."
    )
    assert result.method == "failed"


def test_invented_claim_fails_verification() -> None:
    """A claim not in the source at all must fail."""
    invented = "fastest electric scooter in India with 200 km range"
    result = verify_span(invented, FIXTURE_SOURCE)
    assert not result.verified


def test_empty_quote_fails() -> None:
    result = verify_span("", FIXTURE_SOURCE)
    assert not result.verified
    assert result.method == "failed"


def test_empty_source_fails() -> None:
    result = verify_span("some claim", "")
    assert not result.verified


# ── Coverage calculation ──────────────────────────────────────────────────────

def test_coverage_all_verified() -> None:
    results = [verify_span(q, FIXTURE_SOURCE) for q in VERBATIM_QUOTES]
    coverage = compute_coverage(results)
    assert coverage == 1.0, f"Expected 100% coverage, got {coverage:.2%}"


def test_coverage_partial() -> None:
    good = verify_span(VERBATIM_QUOTES[0], FIXTURE_SOURCE)
    bad = verify_span("not in the source at all", FIXTURE_SOURCE)
    coverage = compute_coverage([good, bad])
    assert coverage == 0.5


def test_coverage_empty_list() -> None:
    assert compute_coverage([]) == 1.0
