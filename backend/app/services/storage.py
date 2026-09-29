"""
storage.py — thin wrapper around Google Cloud Storage.

In local dev (ENV=local or GCS_EMULATOR_HOST set) this talks to fake-gcs-server.
In production it talks to real GCS with ADC (Application Default Credentials).

P0: only upload_bytes and get_public_url are used.
Later phases add signed-URL generation and content-addressed asset uploads.
"""

from __future__ import annotations
import os
from google.cloud import storage
from app.config import settings


def _client() -> storage.Client:
    """Return a GCS client, pointed at the emulator when GCS_EMULATOR_HOST is set."""
    emulator = settings.gcs_emulator_host
    if emulator:
        # The google-cloud-storage library honours this env var automatically.
        os.environ.setdefault("STORAGE_EMULATOR_HOST", emulator)
        return storage.Client(project=settings.google_cloud_project)
    return storage.Client()


def upload_bytes(
    data: bytes,
    destination_blob: str,
    content_type: str = "application/octet-stream",
    bucket_name: str | None = None,
) -> str:
    """
    Upload raw bytes to GCS.

    Returns the GCS URI: gs://<bucket>/<destination_blob>
    """
    bucket_name = bucket_name or settings.gcs_bucket
    client = _client()

    # Ensure the bucket exists (important for the local emulator on first run).
    bucket = _ensure_bucket(client, bucket_name)

    blob = bucket.blob(destination_blob)
    blob.upload_from_string(data, content_type=content_type)
    return f"gs://{bucket_name}/{destination_blob}"


def read_bytes(blob_path: str, bucket_name: str | None = None) -> bytes:
    """Download a blob and return its bytes."""
    bucket_name = bucket_name or settings.gcs_bucket
    client = _client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    return blob.download_as_bytes()


def _ensure_bucket(client: storage.Client, bucket_name: str) -> storage.Bucket:
    """Create the bucket if it doesn't exist (safe for local emulator; no-op on real GCS)."""
    bucket = client.bucket(bucket_name)
    if not bucket.exists():
        bucket.create()
    return bucket
