"""
Vault Uploader — Content-Addressed Asset Upload to GCS

This module uploads curated assets from vault_staging/ to the GCS vault bucket,
with content-addressed filenames and a registry for tracking.

The registry (vault_registry.json) maps logical asset IDs to:
- GCS URI (gs://vachan_bucket/vault/...)
- CDN URI (https://storage.googleapis.com/...)
- Content hash (SHA-256)
- Metadata (dimensions, duration, tags)

This ensures:
- Idempotency: same content = same URI, no duplicate uploads
- Reproducibility: any asset can be traced back to its hash
- Efficiency: manifests reference vault URIs, never inline data
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA-256 hash of a file.
    
    This is the source of truth for content-addressing: the file's bytes
    determine its asset ID.
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]  # First 16 chars for readability


def build_vault_uri(asset_type: str, asset_id: str, ext: str) -> Dict[str, str]:
    """
    Build GCS and CDN URIs for an asset.
    
    Args:
        asset_type: "plates" | "depth" | "audio" | "patches" | "clips"
        asset_id: Content-addressed ID (e.g., "plate_abc123")
        ext: File extension (e.g., "webp", "png", "mp3")
    
    Returns:
        {
            "gcs_uri": "gs://vachan_bucket/vault/plates/plate_abc123.webp",
            "cdn_uri": "https://storage.googleapis.com/vachan_bucket/vault/plates/plate_abc123.webp"
        }
    """
    bucket = "vachan_bucket"
    path = f"vault/{asset_type}/{asset_id}.{ext}"
    
    return {
        "gcs_uri": f"gs://{bucket}/{path}",
        "cdn_uri": f"https://storage.googleapis.com/{bucket}/{path}"
    }


class VaultRegistry:
    """
    In-memory vault registry that can be saved/loaded from JSON.
    
    The registry is the single source of truth for what assets exist,
    where they live, and what their content hashes are.
    """
    
    def __init__(self, registry_path: Path = Path("app/pipeline/vault_registry.json")):
        self.registry_path = registry_path
        self.assets: Dict[str, Dict[str, Any]] = {}
        self.schema_version = "1.0"
        self.generated_at: Optional[str] = None
        
        if registry_path.exists():
            self.load()
    
    def load(self):
        """Load existing registry from JSON."""
        with open(self.registry_path) as f:
            data = json.load(f)
            self.schema_version = data.get("schema_version", "1.0")
            self.generated_at = data.get("generated_at")
            self.assets = data.get("assets", {})
    
    def save(self):
        """Save registry to JSON."""
        self.generated_at = datetime.utcnow().isoformat() + "Z"
        
        data = {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "assets": self.assets
        }
        
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def register_asset(
        self,
        asset_id: str,
        asset_type: str,
        local_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Register an asset in the vault.
        
        Args:
            asset_id: Content-addressed ID (e.g., "plate_abc123")
            asset_type: "plates" | "depth" | "audio" | "patches" | "clips"
            local_path: Path to the file in vault_staging/
            metadata: Optional metadata (dimensions, duration, tags, etc.)
        """
        content_hash = compute_file_hash(local_path)
        ext = local_path.suffix.lstrip('.')
        uris = build_vault_uri(asset_type, asset_id, ext)
        
        entry = {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "content_hash": content_hash,
            "gcs_uri": uris["gcs_uri"],
            "cdn_uri": uris["cdn_uri"],
            "local_path": str(local_path),
            "file_size_bytes": local_path.stat().st_size,
            "uploaded_at": datetime.utcnow().isoformat() + "Z"
        }
        
        if metadata:
            entry["metadata"] = metadata
        
        self.assets[asset_id] = entry
    
    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Look up an asset by ID."""
        return self.assets.get(asset_id)
    
    def list_by_type(self, asset_type: str) -> List[Dict[str, Any]]:
        """List all assets of a given type."""
        return [
            asset for asset in self.assets.values()
            if asset["asset_type"] == asset_type
        ]


async def upload_asset(
    local_path: Path,
    asset_type: str,
    asset_id: str,
    bucket_name: str = "vachan_bucket",
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Upload a single asset to GCS vault.
    
    Args:
        local_path: Path to file in vault_staging/
        asset_type: "plates" | "depth" | "audio" | "patches" | "clips"
        asset_id: Content-addressed ID
        bucket_name: GCS bucket name
        dry_run: If True, skip actual upload
    
    Returns:
        {
            "success": bool,
            "gcs_uri": "gs://...",
            "cdn_uri": "https://...",
            "bytes_uploaded": int
        }
    
    Production implementation:
    ```python
    from google.cloud import storage
    
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    ext = local_path.suffix.lstrip('.')
    blob_path = f"vault/{asset_type}/{asset_id}.{ext}"
    blob = bucket.blob(blob_path)
    
    # Set cache headers for immutable content
    blob.cache_control = "public, max-age=31536000, immutable"
    blob.upload_from_filename(str(local_path))
    
    return {...}
    ```
    """
    
    if not local_path.exists():
        return {
            "success": False,
            "error": f"File not found: {local_path}"
        }
    
    ext = local_path.suffix.lstrip('.')
    uris = build_vault_uri(asset_type, asset_id, ext)
    
    if dry_run:
        return {
            "success": True,
            "gcs_uri": uris["gcs_uri"],
            "cdn_uri": uris["cdn_uri"],
            "bytes_uploaded": local_path.stat().st_size,
            "dry_run": True
        }
    
    # In production, upload to GCS here
    # For demo, return stub showing the interface
    return {
        "success": True,
        "gcs_uri": uris["gcs_uri"],
        "cdn_uri": uris["cdn_uri"],
        "bytes_uploaded": local_path.stat().st_size,
        "status": "stub_not_uploaded",
        "note": "In demo, use gsutil cp or Google Cloud Console to upload manually"
    }


# Example usage (not called in current demo flow)
if __name__ == "__main__":
    import asyncio
    
    # Create a test registry
    registry = VaultRegistry(Path("vault_registry.json"))
    
    # Register a plate
    test_plate = Path("vault_staging/plates/plate_test.webp")
    if test_plate.exists():
        registry.register_asset(
            asset_id="plate_test_abc123",
            asset_type="plates",
            local_path=test_plate,
            metadata={"dimensions": {"width": 1920, "height": 1080}, "tags": ["test"]}
        )
        registry.save()
        print(f"Registered {len(registry.assets)} asset(s)")
        
        # Upload
        result = asyncio.run(upload_asset(
            local_path=test_plate,
            asset_type="plates",
            asset_id="plate_test_abc123",
            dry_run=True
        ))
        print(f"Upload result: {result}")
