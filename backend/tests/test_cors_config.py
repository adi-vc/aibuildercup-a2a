"""
test_cors_config.py — verify CORS origins are environment-aware.
"""
from app.config import Settings


def test_local_cors_origins():
    """Local env should include localhost ports."""
    s = Settings(env="local", cors_origins=None)
    origins = s.effective_cors_origins
    assert "http://localhost:5173" in origins
    assert "http://localhost:4173" in origins
    assert len(origins) > 0


def test_production_cors_origins():
    """Production env should include Firebase Hosting URLs."""
    s = Settings(env="production", cors_origins=None)
    origins = s.effective_cors_origins
    assert "https://a2a-ghostrider-511215.web.app" in origins
    assert "https://a2a-ghostrider-511215.firebaseapp.com" in origins
    assert "http://localhost" not in " ".join(origins)


def test_explicit_cors_override():
    """CORS_ORIGINS env var should override defaults."""
    custom_origins = ["https://example.com", "https://custom.org"]
    s = Settings(env="production", cors_origins=custom_origins)
    origins = s.effective_cors_origins
    assert origins == custom_origins
