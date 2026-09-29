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

    # ── Runtime environment ──────────────────────────────────────────────────────
    env: str = "local"          # local | staging | production
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── App ──────────────────────────────────────────────────────────────────────
    app_version: str = "0.1.0-p0"


settings = Settings()
