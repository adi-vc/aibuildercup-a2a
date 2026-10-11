#!/bin/bash
#
# Upload Vault Assets to GCS
#
# Usage: ./upload_vault_assets.sh [dry-run]
#
# Uploads curated assets from vault_staging/ to gs://vachan_bucket/vault/
# with content-addressed filenames and immutable cache headers.
#
# Add 'dry-run' argument to preview without uploading.

set -euo pipefail

BUCKET="gs://vachan_bucket"
STAGING_DIR="app/pipeline/vault_staging"
DRY_RUN=${1:-}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if gsutil is available
if ! command -v gsutil &> /dev/null; then
    log_error "gsutil not found. Install Google Cloud SDK:"
    log_error "  https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if bucket exists
if ! gsutil ls "$BUCKET" &> /dev/null; then
    log_error "Bucket $BUCKET not accessible. Check credentials:"
    log_error "  gcloud auth application-default login"
    exit 1
fi

cd "$(dirname "$0")/.."

if [ ! -d "$STAGING_DIR" ]; then
    log_error "Staging directory not found: $STAGING_DIR"
    exit 1
fi

# Upload function
upload_assets() {
    local asset_type=$1
    local extension=$2
    
    local source_dir="$STAGING_DIR/$asset_type"
    local dest_path="$BUCKET/vault/$asset_type/"
    
    if [ ! -d "$source_dir" ]; then
        log_warn "No $asset_type directory found, skipping"
        return
    fi
    
    local count=$(find "$source_dir" -maxdepth 1 -name "*.$extension" | wc -l | tr -d ' ')
    
    if [ "$count" -eq 0 ]; then
        log_warn "No *.$extension files in $asset_type/, skipping"
        return
    fi
    
    log_info "Uploading $count $asset_type (*.$extension)..."
    
    for file in "$source_dir"/*."$extension"; do
        if [ ! -f "$file" ]; then
            continue
        fi
        
        local filename=$(basename "$file")
        local dest="$dest_path$filename"
        
        # Compute SHA-256 hash
        if command -v shasum &> /dev/null; then
            local hash=$(shasum -a 256 "$file" | cut -d' ' -f1 | cut -c1-16)
        else
            local hash=$(sha256sum "$file" | cut -d' ' -f1 | cut -c1-16)
        fi
        
        if [ "$DRY_RUN" == "dry-run" ]; then
            echo "  [DRY RUN] $filename → $dest (hash: $hash)"
        else
            # Upload with immutable cache headers
            gsutil -h "Cache-Control:public, max-age=31536000, immutable" \
                   -h "Content-Type:$(file -b --mime-type "$file")" \
                   cp "$file" "$dest"
            echo "  ✓ $filename → $dest (hash: $hash)"
        fi
    done
}

log_info "Starting vault upload..."
log_info "Bucket: $BUCKET"
log_info "Staging: $STAGING_DIR"

if [ "$DRY_RUN" == "dry-run" ]; then
    log_warn "DRY RUN MODE - no files will be uploaded"
fi

echo ""

# Upload each asset type
upload_assets "plates" "webp"
upload_assets "plates" "png"    # In case some are PNG
upload_assets "depth" "png"
upload_assets "patches" "svg"
upload_assets "patches" "png"
upload_assets "clips" "mp4"

# Audio requires subdirectories
log_info "Uploading audio files..."
for locale_dir in "$STAGING_DIR/audio"/*; do
    if [ -d "$locale_dir" ]; then
        locale=$(basename "$locale_dir")
        log_info "  Locale: $locale"
        
        for audio_file in "$locale_dir"/*.mp3; do
            if [ ! -f "$audio_file" ]; then
                continue
            fi
            
            filename=$(basename "$audio_file")
            dest="$BUCKET/vault/audio/$locale/$filename"
            
            if [ "$DRY_RUN" == "dry-run" ]; then
                echo "    [DRY RUN] $filename → $dest"
            else
                gsutil -h "Cache-Control:public, max-age=31536000, immutable" \
                       -h "Content-Type:audio/mpeg" \
                       cp "$audio_file" "$dest"
                echo "    ✓ $filename"
            fi
        done
    fi
done

echo ""

if [ "$DRY_RUN" == "dry-run" ]; then
    log_warn "DRY RUN COMPLETE - no files were uploaded"
    log_info "Run without 'dry-run' argument to upload for real"
else
    log_info "✓ Upload complete!"
    log_info "View uploaded assets:"
    log_info "  gsutil ls -r $BUCKET/vault/"
fi
