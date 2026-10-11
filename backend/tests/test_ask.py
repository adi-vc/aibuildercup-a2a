"""
test_ask.py — Tests for the claim guard (POST /v1/ask).

Tests both the happy path (answering from facts) and the refusal path
(unsupported questions). Uses the fixture source and manifest from P0/P1.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.brain_store import get_store, reset_store
from app.models.brain import STUB_FACTS


client = TestClient(app)

# Load the P0 fixture manifest
with open("fixtures/p0_single_beat.json") as f:
    P0_MANIFEST = json.load(f)


@pytest.fixture(autouse=True)
def setup_store():
    """Reset store and load fixture data before each test."""
    reset_store()
    store = get_store()
    
    # Save stub facts (all 8 from §17)
    for fact in STUB_FACTS:
        store.save_fact(fact)
    
    # Save the P0 manifest
    manifest = P0_MANIFEST.copy()
    manifest["source_id"] = "src_demo"
    store.save_manifest(manifest)
    
    yield
    reset_store()


def test_ask_supported_question():
    """A question about wading depth should be answered from f_wading_depth."""
    response = client.post(
        "/v1/ask",
        json={
            "manifest_id": "p0_single_beat",
            "question": "Can it handle flooded streets?",
            "locale": "en-IN"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should get an answer (not a refusal)
    assert data["type"] == "answered"
    assert "answer" in data
    assert len(data["answer"]) > 0
    
    # Should cite the wading_depth fact
    assert "f_wading_depth" in data["facts_cited"]
    
    # Should include span_ids for cited facts
    assert len(data["span_ids"]) > 0
    
    # Should report model used
    assert data["model_used"]


def test_ask_warranty_question():
    """A question about warranty should cite f_warranty."""
    response = client.post(
        "/v1/ask",
        json={
            "manifest_id": "p0_single_beat",
            "question": "What's the warranty coverage?",
            "locale": "en-IN"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    if data["type"] == "answered":
        # Should cite warranty fact
        assert "warranty" in str(data.get("facts_cited", []))
    else:
        # If Gemini refuses, it should be a proper refusal
        assert data["type"] in ["unsupported", "off_topic"]
        assert "reason" in data


def test_ask_unsupported_question():
    """
    A superlative question ('fastest in India?') should be refused because
    the fixture has no comparison data.
    """
    response = client.post(
        "/v1/ask",
        json={
            "manifest_id": "p0_single_beat",
            "question": "Is this the fastest electric scooter in India?",
            "locale": "en-IN"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should be refused (either off_topic if no facts match, or unsupported if Gemini refuses)
    assert data["type"] in ["unsupported", "off_topic"]
    assert "reason" in data
    assert data["question"] == "Is this the fastest electric scooter in India?"
    assert "available_subjects" in data


def test_ask_color_question():
    """
    A question about color should be refused because the fixture doesn't
    mention colors.
    """
    response = client.post(
        "/v1/ask",
        json={
            "manifest_id": "p0_single_beat",
            "question": "Does it come in blue?",
            "locale": "en-IN"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should be refused
    assert data["type"] in ["unsupported", "off_topic"]
    assert "reason" in data


def test_ask_price_question():
    """A question about price should cite one of the price facts."""
    response = client.post(
        "/v1/ask",
        json={
            "manifest_id": "p0_single_beat",
            "question": "How much does it cost?",
            "locale": "en-IN"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    if data["type"] == "answered":
        # Should cite at least one price fact
        price_facts = [f for f in data["facts_cited"] if "price" in f]
        assert len(price_facts) > 0
    else:
        # If refused, should still be a valid refusal
        assert "reason" in data


def test_ask_manifest_not_found():
    """Asking about a nonexistent manifest should return 404."""
    response = client.post(
        "/v1/ask",
        json={
            "manifest_id": "m_nonexistent",
            "question": "What's the range?",
            "locale": "en-IN"
        }
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_ask_empty_question():
    """Empty question should be rejected by validation."""
    response = client.post(
        "/v1/ask",
        json={
            "manifest_id": "m_src_demo_standard",
            "question": "",
            "locale": "en-IN"
        }
    )
    
    assert response.status_code == 422  # Validation error


def test_ask_no_gemini_key(monkeypatch):
    """If GEMINI_API_KEY is not set, should return 503."""
    from app import config
    
    # Temporarily remove the API key
    original_key = config.settings.gemini_api_key
    monkeypatch.setattr(config.settings, "gemini_api_key", "")
    
    response = client.post(
        "/v1/ask",
        json={
            "manifest_id": "p0_single_beat",
            "question": "What's the range?",
            "locale": "en-IN"
        }
    )
    
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()
    
    # Restore
    monkeypatch.setattr(config.settings, "gemini_api_key", original_key)
