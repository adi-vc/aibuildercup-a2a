"""
config.py — centralised settings, loaded from environment variables.

In production (Cloud Run) these are set in the service's env vars or Secret Manager.
Locally, copy .env.example → .env and fill in your values, then run with:
    uvicorn app.main:app --reload
or via docker compose (which injects them automatically).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── GCP ─────────────────────────────────────────────────────────────────────
    google_cloud_project: str = "vachan-placeholder"
    gcs_bucket: str = "vachan-vault"

    # When set, the GCS client points at the emulator instead of real GCS.
    # docker-compose sets this to http://gcs-emulator:4443.
    gcs_emulator_host: str = ""

    # ── Gemini ───────────────────────────────────────────────────────────────────
    # Set GEMINI_API_KEY for local dev using the Gemini Developer API.
    # In production on Cloud Run, leave this empty and use ADC (Vertex AI).
    gemini_api_key: str = ""

    # Model names — pulled from models.yaml at runtime but can be overridden here.
    # Keeping them in Settings means tests can swap them without touching the file.
    extraction_model: str = "gemini-2.0-flash-001"

    # ── Firestore ────────────────────────────────────────────────────────────────
    # Set FIRESTORE_EMULATOR_HOST to use the local emulator (e.g. localhost:8088).
    # docker compose will add the emulator in a future update.
    firestore_emulator_host: str = ""

    # ── Runtime environment ──────────────────────────────────────────────────────
    env: str = "local"          # local | staging | production
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── App ──────────────────────────────────────────────────────────────────────
    app_version: str = "0.1.0-p1"


settings = Settings()
