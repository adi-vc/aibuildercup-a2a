"""
test_manifest.py — tests for the P0 fixture manifest endpoint.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_manifest_p0_fixture():
    """The P0 fixture manifest should load and contain the expected fields."""
    resp = client.get("/v1/manifest/p0_single_beat")
    assert resp.status_code == 200
    data = resp.json()
    assert data["manifest_id"] == "p0_single_beat"
    assert data["schema_version"] == "1.0"
    assert len(data["beats"]) == 1
    beat = data["beats"][0]
    assert beat["id"] == "b_flood"
    assert "f_wading_depth" in beat["fact_ids"]
    assert "en-IN" in beat["text_slots"]
    assert "hi-IN" in beat["text_slots"]


def test_manifest_integrity_indexes():
    """The integrity indexes must be present — they are the linter's contract."""
    resp = client.get("/v1/manifest/p0_single_beat")
    assert resp.status_code == 200
    data = resp.json()
    integrity = data["integrity"]
    assert integrity["coverage"] == 1.0
    assert "f_wading_depth" in integrity["fact_index"]
    assert "f_wading_depth" in integrity["beat_index"]
    assert "f_wading_depth" in integrity["asset_index"]


def test_manifest_cors_header():
    """The manifest endpoint should include CORS headers for the player."""
    resp = client.get("/v1/manifest/p0_single_beat")
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "*"


def test_manifest_is_revalidated_with_etag():
    """T5b: stable ids + rebuilds mean no max-age; an unchanged manifest is a 304."""
    first = client.get("/v1/manifest/p0_single_beat")
    assert first.headers["cache-control"] == "no-cache"
    etag = first.headers["etag"]
    assert etag.startswith('"') and "ETag" in first.headers["access-control-expose-headers"]
    again = client.get("/v1/manifest/p0_single_beat", headers={"If-None-Match": etag})
    assert again.status_code == 304
    assert again.content == b""
    stale = client.get("/v1/manifest/p0_single_beat", headers={"If-None-Match": '"not-current"'})
    assert stale.status_code == 200


def test_manifest_etag_changes_with_content():
    from app.routers.manifest import manifest_etag
    assert manifest_etag({"a": 1, "b": 2}) == manifest_etag({"b": 2, "a": 1})
    assert manifest_etag({"a": 1}) != manifest_etag({"a": 2})
