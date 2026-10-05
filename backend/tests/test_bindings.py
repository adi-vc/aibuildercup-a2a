"""T5a — play-time binding resolver (§24.2 rung 1, §64.7 criterion 5)."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def _resolve(city: str, keys=("price",)):
    return client.post("/v1/bindings/resolve", json={"keys": list(keys), "city": city})


@pytest.mark.parametrize("city,amount", [("mumbai", "129900"), ("Bengaluru", "127400")])
def test_price_resolves_per_city(city, amount):
    resp = _resolve(city)
    assert resp.status_code == 200
    data = resp.json()
    assert data["values"]["price"] == {"value": amount, "unit": "INR", "resolver": "offer.by_city"}
    assert data["resolved_at"]
    assert resp.headers["cache-control"] == "no-store"


def test_unknown_city_and_key_are_omitted_not_guessed():
    data = _resolve("chennai", keys=("price", "stock")).json()
    assert data["values"] == {}


def test_kill_switch_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "bindings_fail", True)
    assert _resolve("mumbai").status_code == 503
