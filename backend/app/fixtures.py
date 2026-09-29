"""
fixtures.py — fixture data shared between the extractor stub and the tests.

FIXTURE_QUOTES maps each stub fact_id to the verbatim string that appears in
backend/fixtures/vega_v1.html.  These are the same strings the §39.1 verifier
will find by exact substring match, so the offline pipeline produces 100%
coverage — identical to the live-model result on the same source.

If you add a fact to STUB_FACTS in models/brain.py, add its quote here too.
"""

# fact_id → verbatim substring from backend/fixtures/vega_v1.html
FIXTURE_QUOTES: dict[str, str] = {
    "f_wading_depth":       "wades through water up to 30 cm deep",
    "f_range":              "certified range of 128 km per charge (IDC)",
    "f_zero_sixty":         "0–60 km/h in 8.2 seconds",
    "f_charge_time":        "0–80% in 4 hours 30 minutes",
    "f_ground_clearance":   "ground clearance of 165 mm",
    "offer_price_mumbai":   "Mumbai on-road ₹1,29,900",
    "offer_price_bengaluru":"Bengaluru on-road ₹1,27,400",
    "warranty":             "3-year or 30,000 km battery warranty",
}
