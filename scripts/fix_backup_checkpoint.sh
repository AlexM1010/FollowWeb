#!/bin/bash
# Fix corrupted checkpoint in backup repository
# This script:
# 1. Downloads the latest checkpoint from backup repository
# 2. Fixes the metadata edge_count to match actual graph
# 3. Re-uploads the fixed checkpoint

set -e

REPO_OWNER="AlexM1010"
BACKUP_REPO="${REPO_OWNER}/freesound-backup"
WORK_DIR="temp_checkpoint_fix"

echo "🔧 Checkpoint Metadata Fix Script"
echo "=================================="
echo ""

# Check if BACKUP_PAT is set
if [ -z "$BACKUP_PAT" ]; then
    echo "❌ ERROR: BACKUP_PAT environment variable not set"
    echo "Please set it with: export BACKUP_PAT=your_token"
    exit 1
fi

# Clean up any previous work directory
if [ -d "$WORK_DIR" ]; then
    echo "Cleaning up previous work directory..."
    rm -rf "$WORK_DIR"
fi

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "📥 Step 1: Downloading latest checkpoint from backup repository..."
echo ""

# Get latest checkpoint from v-checkpoint release
ASSETS_JSON=$(curl -s -H "Authorization: token $BACKUP_PAT" \
  "https://api.github.com/repos/${BACKUP_REPO}/releases/tags/v-checkpoint")

if echo "$ASSETS_JSON" | grep -q "Not Found"; then
    echo "❌ ERROR: Release v-checkpoint not found"
    exit 1
fi

# Get the latest asset (most recent by created_at)
LATEST_ASSET=$(echo "$ASSETS_JSON" | jq -r '.assets | sort_by(.created_at) | reverse | .[0]')

if [ "$LATEST_ASSET" = "null" ] || [ -z "$LATEST_ASSET" ]; then
    echo "❌ ERROR: No checkpoint backups found"
    exit 1
fi

ASSET_NAME=$(echo "$LATEST_ASSET" | jq -r '.name')
ASSET_URL=$(echo "$LATEST_ASSET" | jq -r '.url')
ASSET_ID=$(echo "$LATEST_ASSET" | jq -r '.id')
ASSET_SIZE=$(echo "$LATEST_ASSET" | jq -r '.size')

echo "Found checkpoint: $ASSET_NAME"
echo "Size: $(numfmt --to=iec-i --suffix=B "$ASSET_SIZE")"
echo "Asset ID: $ASSET_ID"
echo ""

# Download the checkpoint
echo "Downloading..."
curl -L -H "Authorization: token $BACKUP_PAT" \
  -H "Accept: application/octet-stream" \
  "$ASSET_URL" -o checkpoint_backup.tar.gz

# Extract checkpoint
echo "Extracting..."
mkdir -p data
tar -xzf checkpoint_backup.tar.gz -C data/
rm checkpoint_backup.tar.gz

if [ ! -d "data/freesound_library" ]; then
    echo "❌ ERROR: Checkpoint extraction failed"
    exit 1
fi

echo "✅ Checkpoint downloaded and extracted"
echo ""

echo "🔍 Step 2: Analyzing checkpoint..."
echo ""

# Check current state
cd ..
python3 << 'PYTHON_SCRIPT'
import json
import pickle
from pathlib import Path

checkpoint_dir = Path("temp_checkpoint_fix/data/freesound_library")

# Load graph
graph_path = checkpoint_dir / "graph_topology.gpickle"
with open(graph_path, "rb") as f:
    graph = pickle.load(f)

actual_nodes = graph.number_of_nodes()
actual_edges = graph.number_of_edges()

# Load metadata
metadata_path = checkpoint_dir / "checkpoint_metadata.json"
with open(metadata_path, "r") as f:
    metadata = json.load(f)

metadata_nodes = metadata.get("nodes", 0)
metadata_edges = metadata.get("edges", 0)

print(f"Graph topology:  {actual_nodes} nodes, {actual_edges} edges")
print(f"Metadata says:   {metadata_nodes} nodes, {metadata_edges} edges")
print()

if metadata_nodes == actual_nodes and metadata_edges == actual_edges:
    print("✅ Metadata is correct - no fix needed!")
    exit(0)
else:
    print(f"❌ MISMATCH DETECTED!")
    print(f"   Nodes: {metadata_nodes} -> {actual_nodes} (diff: {actual_nodes - metadata_nodes})")
    print(f"   Edges: {metadata_edges} -> {actual_edges} (diff: {actual_edges - metadata_edges})")
    print()
    
    # Fix metadata
    print("🔧 Fixing metadata...")
    metadata["nodes"] = actual_nodes
    metadata["edges"] = actual_edges
    
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print("✅ Metadata fixed!")
    exit(1)  # Exit with 1 to indicate fix was needed
PYTHON_SCRIPT

FIX_NEEDED=$?

if [ $FIX_NEEDED -eq 0 ]; then
    echo ""
    echo "No fix needed - checkpoint is already correct!"
    cd ..
    rm -rf "$WORK_DIR"
    exit 0
fi

echo ""
echo "🔍 Step 3: Validating fixed checkpoint..."
echo ""

# Run validation
cd ..
if python scripts/validation/validate_checkpoint.py "$WORK_DIR/data/freesound_library"; then
    echo ""
    echo "✅ Validation passed!"
else
    echo ""
    echo "❌ Validation failed after fix - manual intervention needed"
    exit 1
fi

echo ""
echo "📤 Step 4: Uploading fixed checkpoint..."
echo ""

cd "$WORK_DIR"

# Create new backup archive with timestamp
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
NEW_BACKUP_NAME="checkpoint_fixed_${TIMESTAMP}.tar.gz"

echo "Creating archive: $NEW_BACKUP_NAME"
tar -czf "$NEW_BACKUP_NAME" -C data freesound_library/

BACKUP_SIZE=$(stat -f%z "$NEW_BACKUP_NAME" 2>/dev/null || stat -c%s "$NEW_BACKUP_NAME")
echo "Archive size: $(numfmt --to=iec-i --suffix=B "$BACKUP_SIZE")"
echo ""

# Get release ID
RELEASE_JSON=$(curl -s -H "Authorization: token $BACKUP_PAT" \
  "https://api.github.com/repos/${BACKUP_REPO}/releases/tags/v-checkpoint")

RELEASE_ID=$(echo "$RELEASE_JSON" | jq -r '.id')

if [ "$RELEASE_ID" = "null" ] || [ -z "$RELEASE_ID" ]; then
    echo "❌ ERROR: Could not get release ID"
    exit 1
fi

# Upload new asset
echo "Uploading to GitHub..."
UPLOAD_URL="https://uploads.github.com/repos/${BACKUP_REPO}/releases/${RELEASE_ID}/assets?name=${NEW_BACKUP_NAME}"

UPLOAD_RESPONSE=$(curl -s -X POST \
  -H "Authorization: token $BACKUP_PAT" \
  -H "Content-Type: application/gzip" \
  --data-binary "@${NEW_BACKUP_NAME}" \
  "$UPLOAD_URL")

NEW_ASSET_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.id')

if [ "$NEW_ASSET_ID" = "null" ] || [ -z "$NEW_ASSET_ID" ]; then
    echo "❌ ERROR: Upload failed"
    echo "Response: $UPLOAD_RESPONSE"
    exit 1
fi

echo "✅ Fixed checkpoint uploaded successfully!"
echo "   Asset ID: $NEW_ASSET_ID"
echo "   Name: $NEW_BACKUP_NAME"
echo ""

echo "🗑️  Step 5: Deleting old corrupted checkpoint..."
echo ""

# Delete the old corrupted asset
DELETE_URL="https://api.github.com/repos/${BACKUP_REPO}/releases/assets/${ASSET_ID}"

DELETE_RESPONSE=$(curl -s -X DELETE \
  -H "Authorization: token $BACKUP_PAT" \
  "$DELETE_URL")

if [ -z "$DELETE_RESPONSE" ]; then
    echo "✅ Old checkpoint deleted (Asset ID: $ASSET_ID)"
else
    echo "⚠️  Warning: Could not delete old checkpoint"
    echo "Response: $DELETE_RESPONSE"
fi

echo ""
echo "🧹 Cleaning up..."
cd ..
rm -rf "$WORK_DIR"

echo ""
echo "✅ =================================="
echo "✅ Checkpoint fix completed successfully!"
echo "✅ =================================="
echo ""
echo "Next steps:"
echo "1. Trigger a new validation workflow run"
echo "2. Monitor the pipeline to ensure it uses the fixed checkpoint"
echo ""
