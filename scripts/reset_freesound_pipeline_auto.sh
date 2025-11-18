#!/bin/bash
# Automated reset of Freesound pipeline (no confirmation prompt)
# Use this for CI/automation or when you're absolutely sure

set -e

REPO_OWNER="AlexM1010"
BACKUP_REPO="${REPO_OWNER}/freesound-backup"
MAIN_REPO="${REPO_OWNER}/FollowWeb"

echo "🔄 Freesound Pipeline Reset (Automated)"
echo "========================================"
echo ""

# Check if BACKUP_PAT is set
if [ -z "$BACKUP_PAT" ]; then
    echo "❌ ERROR: BACKUP_PAT environment variable not set"
    exit 1
fi

echo "🗑️  Deleting all checkpoint backups from repository..."

# Get all assets from v-checkpoint release
ASSETS_JSON=$(curl -s -H "Authorization: token $BACKUP_PAT" \
  "https://api.github.com/repos/${BACKUP_REPO}/releases/tags/v-checkpoint")

if ! echo "$ASSETS_JSON" | grep -q "Not Found"; then
    ASSET_COUNT=$(echo "$ASSETS_JSON" | jq -r '.assets | length')
    
    if [ "$ASSET_COUNT" -gt 0 ]; then
        echo "Deleting $ASSET_COUNT backup(s)..."
        
        for asset_id in $(echo "$ASSETS_JSON" | jq -r '.assets[].id'); do
            curl -s -X DELETE \
              -H "Authorization: token $BACKUP_PAT" \
              "https://api.github.com/repos/${BACKUP_REPO}/releases/assets/${asset_id}" \
              > /dev/null
            echo "  ✅ Deleted asset ID: $asset_id"
        done
    else
        echo "  ⚠️  No backups found"
    fi
else
    echo "  ⚠️  Release not found"
fi

echo ""
echo "🧹 Clearing local checkpoint directory..."

CHECKPOINT_DIR="data/freesound_library"
if [ -d "$CHECKPOINT_DIR" ]; then
    find "$CHECKPOINT_DIR" -type f ! -name "README.md" ! -name ".gitkeep" -delete
    echo "  ✅ Local checkpoint cleared"
else
    echo "  ⚠️  Directory not found"
fi

echo ""
echo "🗑️  Clearing GitHub Actions cache..."

CHECKPOINT_CACHES=$(gh cache list --repo "$MAIN_REPO" --json id,key --limit 100 | \
  jq -r '.[] | select(.key | startswith("checkpoint-")) | .id')

if [ -n "$CHECKPOINT_CACHES" ]; then
    CACHE_COUNT=$(echo "$CHECKPOINT_CACHES" | wc -l)
    echo "Deleting $CACHE_COUNT cache(s)..."
    
    for cache_id in $CHECKPOINT_CACHES; do
        gh cache delete "$cache_id" --repo "$MAIN_REPO" 2>/dev/null && \
          echo "  ✅ Deleted cache ID: $cache_id" || \
          echo "  ⚠️  Failed to delete cache ID: $cache_id"
    done
else
    echo "  ⚠️  No caches found"
fi

echo ""
echo "✅ Reset complete! Pipeline will start from scratch on next run."
echo ""
