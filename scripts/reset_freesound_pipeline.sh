#!/bin/bash
# Reset Freesound pipeline to start from scratch
# This script:
# 1. Deletes ALL checkpoint backups from the backup repository
# 2. Clears the local checkpoint directory
# 3. Clears GitHub Actions cache

set -e

REPO_OWNER="AlexM1010"
BACKUP_REPO="${REPO_OWNER}/freesound-backup"
MAIN_REPO="${REPO_OWNER}/FollowWeb"

echo "🔄 Freesound Pipeline Reset Script"
echo "===================================="
echo ""
echo "⚠️  WARNING: This will DELETE ALL checkpoint data!"
echo "⚠️  The pipeline will start from scratch (0 nodes, 0 edges)"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""

# Check if BACKUP_PAT is set
if [ -z "$BACKUP_PAT" ]; then
    echo "❌ ERROR: BACKUP_PAT environment variable not set"
    echo "Please set it with: export BACKUP_PAT=your_token"
    exit 1
fi

echo "📥 Step 1: Fetching checkpoint backups from repository..."
echo ""

# Get all assets from v-checkpoint release
ASSETS_JSON=$(curl -s -H "Authorization: token $BACKUP_PAT" \
  "https://api.github.com/repos/${BACKUP_REPO}/releases/tags/v-checkpoint")

if echo "$ASSETS_JSON" | grep -q "Not Found"; then
    echo "⚠️  Release v-checkpoint not found - nothing to delete"
else
    # Get all asset IDs and names
    ASSET_COUNT=$(echo "$ASSETS_JSON" | jq -r '.assets | length')
    
    if [ "$ASSET_COUNT" -eq 0 ]; then
        echo "⚠️  No checkpoint backups found - nothing to delete"
    else
        echo "Found $ASSET_COUNT checkpoint backup(s)"
        echo ""
        
        # List all assets
        echo "Checkpoint backups to delete:"
        echo "$ASSETS_JSON" | jq -r '.assets[] | "  - \(.name) (ID: \(.id), Size: \(.size | tonumber / 1024 | floor)KB)"'
        echo ""
        
        echo "🗑️  Deleting checkpoint backups..."
        
        # Delete each asset
        DELETED=0
        FAILED=0
        
        for asset_id in $(echo "$ASSETS_JSON" | jq -r '.assets[].id'); do
            asset_name=$(echo "$ASSETS_JSON" | jq -r ".assets[] | select(.id == $asset_id) | .name")
            
            DELETE_URL="https://api.github.com/repos/${BACKUP_REPO}/releases/assets/${asset_id}"
            DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE \
              -H "Authorization: token $BACKUP_PAT" \
              "$DELETE_URL")
            
            HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
            
            if [ "$HTTP_CODE" = "204" ]; then
                echo "  ✅ Deleted: $asset_name (ID: $asset_id)"
                DELETED=$((DELETED + 1))
            else
                echo "  ❌ Failed to delete: $asset_name (ID: $asset_id, HTTP: $HTTP_CODE)"
                FAILED=$((FAILED + 1))
            fi
        done
        
        echo ""
        echo "Deletion summary: $DELETED deleted, $FAILED failed"
    fi
fi

echo ""
echo "🧹 Step 2: Clearing local checkpoint directory..."
echo ""

CHECKPOINT_DIR="data/freesound_library"

if [ -d "$CHECKPOINT_DIR" ]; then
    # List files before deletion
    echo "Files in $CHECKPOINT_DIR:"
    ls -lh "$CHECKPOINT_DIR" | grep -v "^total" | grep -v "README.md" | grep -v ".gitkeep" || echo "  (empty)"
    echo ""
    
    # Delete checkpoint files but keep README.md and .gitkeep
    find "$CHECKPOINT_DIR" -type f ! -name "README.md" ! -name ".gitkeep" -delete
    
    echo "✅ Local checkpoint files deleted"
    echo ""
    echo "Remaining files:"
    ls -lh "$CHECKPOINT_DIR" | grep -v "^total" || echo "  (empty)"
else
    echo "⚠️  Checkpoint directory not found: $CHECKPOINT_DIR"
fi

echo ""
echo "🗑️  Step 3: Clearing GitHub Actions cache..."
echo ""

# List and delete caches
echo "Fetching cache list..."
CACHE_LIST=$(gh cache list --repo "$MAIN_REPO" --json id,key,sizeInBytes --limit 100)

CHECKPOINT_CACHES=$(echo "$CACHE_LIST" | jq -r '.[] | select(.key | startswith("checkpoint-")) | .id')

if [ -z "$CHECKPOINT_CACHES" ]; then
    echo "⚠️  No checkpoint caches found"
else
    CACHE_COUNT=$(echo "$CHECKPOINT_CACHES" | wc -l)
    echo "Found $CACHE_COUNT checkpoint cache(s)"
    echo ""
    
    # Show cache details
    echo "Caches to delete:"
    echo "$CACHE_LIST" | jq -r '.[] | select(.key | startswith("checkpoint-")) | "  - \(.key) (ID: \(.id), Size: \(.sizeInBytes / 1024 | floor)KB)"'
    echo ""
    
    echo "Deleting caches..."
    DELETED=0
    FAILED=0
    
    for cache_id in $CHECKPOINT_CACHES; do
        cache_key=$(echo "$CACHE_LIST" | jq -r ".[] | select(.id == $cache_id) | .key")
        
        if gh cache delete "$cache_id" --repo "$MAIN_REPO" 2>/dev/null; then
            echo "  ✅ Deleted: $cache_key (ID: $cache_id)"
            DELETED=$((DELETED + 1))
        else
            echo "  ❌ Failed to delete: $cache_key (ID: $cache_id)"
            FAILED=$((FAILED + 1))
        fi
    done
    
    echo ""
    echo "Cache deletion summary: $DELETED deleted, $FAILED failed"
fi

echo ""
echo "✅ =================================="
echo "✅ Pipeline reset completed!"
echo "✅ =================================="
echo ""
echo "Summary:"
echo "  - Backup repository: All checkpoints deleted"
echo "  - Local checkpoint: Cleared"
echo "  - GitHub Actions cache: Cleared"
echo ""
echo "Next steps:"
echo "1. The next pipeline run will start from scratch (0 nodes, 0 edges)"
echo "2. Trigger a manual run or wait for the scheduled nightly run"
echo "3. Monitor the pipeline to ensure it starts fresh"
echo ""
echo "To trigger a manual run:"
echo "  gh workflow run freesound-nightly-pipeline.yml --repo $MAIN_REPO"
echo ""
