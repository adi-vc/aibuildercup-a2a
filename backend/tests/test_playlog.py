"""T6 — signed, chained play-log (§64.10). Every exit criterion is a test here."""

import copy
import json

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routers.manifest import manifest_etag
from app.services import playlog
from app.services.brain_store import get_store, reset_store

client = TestClient(app)

MANIFEST = {
    "manifest_id": "m_playlog_test", "schema_version": "1.0", "brain_version": "br", "bitgraph_version": "bg",
    "locales": ["en-IN", "hi-IN"],
    "beats": [
        {"id": "b_flood", "kind": "hold", "fact_ids": ["f_wading_depth"], "vault_refs": ["plate"], "text_slots": {},
         "audio_slots": {}, "bindings": [], "hinge": {"in": "w", "out": "w"}, "edges": []},
        {"id": "b_offer", "kind": "hold", "fact_ids": ["offer_price_mumbai", "offer_price_bengaluru"],
         "vault_refs": ["plate"], "text_slots": {}, "audio_slots": {}, "bindings": ["price"],
         "hinge": {"in": "w", "out": "w"}, "edges": []},
    ],
    "edges": [], "slots": [], "bindings": [{"key": "price", "resolver": "offer.by_city", "ttl_s": 300}], "vault": {},
    "accessibility": {"captions": True, "audio_description": False},
    "policy": {"kids_mode": False, "competitor_exclusions": []},
    "integrity": {
        "fact_index": {"f_wading_depth": "sp_1", "offer_price_mumbai": "sp_6", "offer_price_bengaluru": "sp_7"},
        "beat_index": {}, "asset_index": {}, "coverage": 1.0, "linted_at": "2026-10-06T00:00:00Z",
        "facts": {
            "f_wading_depth": {"value": "30", "unit": "cm", "text": "t", "quote": "wades through water up to 30 cm deep", "origin": "canon"},
            "offer_price_mumbai": {"value": "129900", "unit": "INR", "text": "t", "quote": "Mumbai on-road ₹1,29,900", "origin": "canon"},
            "offer_price_bengaluru": {"value": "127400", "unit": "INR", "text": "t", "quote": "Bengaluru on-road ₹1,27,400", "origin": "canon"},
        },
    },
}

LIVE_PRICE = {"display": "₹1,29,900", "rung": 1, "value": "129900", "unit": "INR",
              "source": {"kind": "binding", "resolver": "offer.by_city", "resolved_at": "2026-10-06T10:00:00Z"}}
PUBLISHED_PRICE = {"display": "₹1,27,400", "rung": 3, "value": "127400", "unit": "INR",
                   "source": {"kind": "fact", "fact_id": "offer_price_bengaluru", "span_id": "sp_7", "quote": "Bengaluru on-road ₹1,27,400"}}


def play(**overrides) -> dict:
    body = {
        "manifest_id": MANIFEST["manifest_id"], "manifest_version": manifest_etag(MANIFEST).strip('"'),
        "profile_hash": "h_test", "started_at": "2026-10-06T10:00:00Z", "ended_at": "2026-10-06T10:00:24Z",
        "shown": [
            {"beat_id": "b_flood", "locale": "en-IN", "city": "mumbai",
             "claims": [{"fact_id": "f_wading_depth", "span_id": "sp_1"}], "bindings": {}},
            {"beat_id": "b_offer", "locale": "en-IN", "city": "mumbai", "claims": [], "bindings": {"price": LIVE_PRICE}},
            {"beat_id": "b_offer", "locale": "hi-IN", "city": "bengaluru",
             "claims": [{"fact_id": "offer_price_bengaluru", "span_id": "sp_7"}], "bindings": {"price": PUBLISHED_PRICE}},
        ],
        "questions": [], "refusals": [],
    }
    body.update(overrides)
    # Deep copy: tests mutate bodies, and the price fixtures are shared.
    return copy.deepcopy(body)


@pytest.fixture(autouse=True)
def fresh_store():
    reset_store()
    get_store().save_manifest(copy.deepcopy(MANIFEST))
    yield
    reset_store()


def post(body: dict, content_type: str = "application/json"):
    return client.post("/v1/playlog", content=json.dumps(body, ensure_ascii=False).encode(), headers={"content-type": content_type})


# ── Criterion 1: the record is what was on screen ────────────────────────────

def test_signed_record_keeps_exactly_what_was_shown():
    resp = post(play())
    assert resp.status_code == 201, resp.text
    rec = resp.json()
    assert [s["beat_id"] for s in rec["shown"]] == ["b_flood", "b_offer", "b_offer"]
    assert rec["shown"][1]["bindings"]["price"]["display"] == "₹1,29,900"
    assert rec["shown"][2]["locale"] == "hi-IN" and rec["shown"][2]["bindings"]["price"]["rung"] == 3
    assert rec["refusals"] == []
    assert rec["seq"] == 0 and rec["prev_hash"] == playlog.GENESIS


@pytest.mark.parametrize("mutate,reason", [
    (lambda b: b["shown"][0].update(beat_id="b_ghost"), "not in the manifest"),
    (lambda b: b["shown"][0].update(locale="kn-IN"), "not declared"),
    (lambda b: b["shown"][0]["claims"][0].update(span_id="sp_999"), "resolves to span"),
    (lambda b: b["shown"][0]["claims"].append({"fact_id": "offer_price_mumbai", "span_id": "sp_6"}), "does not cite"),
    (lambda b: b["shown"][2]["bindings"]["price"].update(value="99999"), "differs from the published fact"),
    (lambda b: b["shown"][1]["bindings"]["price"]["source"].update(resolver="made.up"), "rung 1"),
    (lambda b: b["shown"][0]["bindings"].update(price=LIVE_PRICE), "has no binding"),
])
def test_impossible_screens_are_not_signed(mutate, reason):
    body = play()
    mutate(body)
    resp = post(body)
    assert resp.status_code == 422
    assert reason in json.dumps(resp.json())


def test_record_for_a_changed_manifest_is_refused():
    assert post(play(manifest_version="stale0000")).status_code == 409


def test_unknown_fields_are_rejected():
    body = play()
    body["viewer_email"] = "someone@example.com"   # no PII fields can ride along
    assert post(body).status_code == 422


def test_keepalive_text_plain_body_is_accepted():
    assert post(play(), content_type="text/plain;charset=UTF-8").status_code == 201


# ── Criterion 2: the signature verifies ──────────────────────────────────────

def test_signature_verifies_via_api():
    rec = post(play()).json()
    assert rec["signature"].startswith("hmac-sha256:")
    assert client.post("/v1/playlog/verify", json=rec).json()["ok"] is True
    assert client.get(f"/v1/playlog/{rec['play_id']}").json() == rec


# ── Criterion 3: the chain verifies across three consecutive plays ───────────

def test_three_plays_chain_and_verify():
    recs = [post(play()).json() for _ in range(3)]
    assert [r["seq"] for r in recs] == [0, 1, 2]
    assert recs[1]["prev_hash"] == playlog.record_hash(recs[0])
    assert recs[2]["prev_hash"] == playlog.record_hash(recs[1])
    chain = client.get(f"/v1/playlog/chain/{MANIFEST['manifest_id']}").json()
    assert chain["ok"] is True and chain["count"] == 3


# ── Criterion 4: tampering with any one field fails verification ─────────────

TAMPERS = {
    "price shown": lambda r: r["shown"][1]["bindings"]["price"].update(display="₹99,999"),
    "price rung": lambda r: r["shown"][2]["bindings"]["price"].update(rung=1),
    "claim": lambda r: r["shown"][0]["claims"].clear(),
    "locale": lambda r: r["shown"][2].update(locale="en-IN"),
    "refusal count": lambda r: r["refusals"].append({"type": 3}),
    "beat order": lambda r: r["shown"].reverse(),
    "manifest version": lambda r: r.update(manifest_version="other"),
    "seq": lambda r: r.update(seq=7),
    "prev_hash": lambda r: r.update(prev_hash="f" * 64),
    "signature": lambda r: r.update(signature=r["signature"][:-1] + ("0" if r["signature"][-1] != "0" else "1")),
}


@pytest.mark.parametrize("field", list(TAMPERS))
def test_tampering_one_field_fails_verification(field):
    rec = post(play()).json()
    forged = copy.deepcopy(rec)
    TAMPERS[field](forged)
    assert playlog.verify_signature(rec) is True
    assert playlog.verify_signature(forged) is False
    assert client.post("/v1/playlog/verify", json=forged).json()["ok"] is False


def test_tampering_a_stored_record_breaks_the_chain_at_that_record():
    recs = [post(play()).json() for _ in range(3)]
    stored = get_store().get_play(recs[1]["play_id"])
    stored["shown"][1]["bindings"]["price"]["display"] = "₹1"           # edit in place in the store
    chain = playlog.verify_chain(get_store().get_plays_by_manifest(MANIFEST["manifest_id"]))
    assert chain["ok"] is False
    reasons = {(f["seq"], f["reason"]) for f in chain["failures"]}
    assert (1, "signature does not verify") in reasons
    assert (2, "prev_hash does not match the previous record") in reasons


def test_dropping_a_record_breaks_the_chain():
    recs = [post(play()).json() for _ in range(3)]
    chain = playlog.verify_chain([recs[0], recs[2]])
    assert chain["ok"] is False


def test_canonical_form_is_order_independent():
    assert playlog.canonical({"b": 1, "a": [1, {"d": 2, "c": "₹"}]}) == playlog.canonical({"a": [1, {"c": "₹", "d": 2}], "b": 1})


def test_refuses_to_sign_without_a_key_outside_local(monkeypatch):
    monkeypatch.setattr(settings, "env", "production")
    monkeypatch.setattr(settings, "playlog_hmac_key", "")
    assert post(play()).status_code == 503


def test_configured_key_is_used_and_identified(monkeypatch):
    monkeypatch.setattr(settings, "playlog_hmac_key", "test-key-from-secret-manager")
    rec = post(play()).json()
    assert playlog.verify_signature(rec)
    monkeypatch.setattr(settings, "playlog_hmac_key", "a-different-key")
    assert not playlog.verify_signature(rec)   # a record only verifies under the key that signed it


def test_questions_and_refusals_are_signed_with_strict_shapes():
    """T8.1: guard outcomes ride in the signed record; unknown types or fields are refused."""
    body = play(questions=[{"q": "What's the warranty?", "a": "3-year or 30,000 km battery warranty.",
                            "facts_cited": ["warranty"]}],
                refusals=[{"q": "Is it the fastest in India?", "type": "superlative_comparative",
                           "reason": "I can only tell you what's verified: 0–60 km/h in 8.2 seconds."}])
    rec = post(body).json()
    assert rec["refusals"][0]["type"] == "superlative_comparative" and playlog.verify_signature(rec)
    bad_type = play(refusals=[{"q": "x", "type": "made_up", "reason": ""}])
    assert post(bad_type).status_code == 422
    bad_field = play(questions=[{"q": "x", "viewer_email": "a@b.c"}])
    assert post(bad_field).status_code == 422
