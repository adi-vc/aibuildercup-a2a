"""
test_health.py — smoke tests for the P0 skeleton.

Run: pytest backend/tests/ -v
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Vachan API"


def test_manifest_not_found():
    resp = client.get("/v1/manifest/does_not_exist")
    assert resp.status_code == 404
