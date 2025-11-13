#!/bin/bash
# Setup script for Freesound backup repository and secrets

set -e

REPO_OWNER="AlexM1010"
BACKUP_REPO_NAME="freesound-backup"
BACKUP_REPO="${REPO_OWNER}/${BACKUP_REPO_NAME}"

echo "🔧 Setting up Freesound backup infrastructure..."
echo ""

# Step 1: Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Step 2: Check authentication
echo "Checking GitHub authentication..."
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI"
    echo "Please run: gh auth login"
    exit 1
fi
echo "✅ Authenticated"
echo ""

# Step 3: Create private backup repository
echo "Creating private backup repository: ${BACKUP_REPO}..."
if gh repo view "${BACKUP_REPO}" &> /dev/null; then
    echo "✅ Repository already exists"
else
    gh repo create "${BACKUP_REPO}" \
        --private \
        --description "Private storage for Freesound pipeline checkpoints" \
        --disable-wiki \
        --disable-issues
    echo "✅ Repository created"
fi
echo ""

# Step 4: Create v-checkpoint release
echo "Creating v-checkpoint release..."
if gh release view v-checkpoint --repo "${BACKUP_REPO}" &> /dev/null; then
    echo "✅ Release already exists"
else
    gh release create v-checkpoint \
        --repo "${BACKUP_REPO}" \
        --title "Checkpoint Storage" \
        --notes "Rolling storage for pipeline checkpoints (14-day retention)" \
        --prerelease
    echo "✅ Release created"
fi
echo ""

# Step 5: Create Personal Access Token (PAT)
echo "📝 Creating Personal Access Token..."
echo ""
echo "You need to create a PAT with the following permissions:"
echo "  - repo (Full control of private repositories)"
echo ""
echo "Creating token..."

# Generate a unique token note
TOKEN_NOTE="freesound-backup-$(date +%Y%m%d-%H%M%S)"

# Create token with repo scope
PAT=$(gh auth token 2>/dev/null || echo "")

if [ -z "$PAT" ]; then
    echo "❌ Could not retrieve token automatically"
    echo ""
    echo "Please create a token manually:"
    echo "1. Go to: https://github.com/settings/tokens/new"
    echo "2. Note: ${TOKEN_NOTE}"
    echo "3. Expiration: No expiration (or 1 year)"
    echo "4. Scopes: Select 'repo' (Full control of private repositories)"
    echo "5. Click 'Generate token'"
    echo "6. Copy the token"
    echo ""
    read -p "Paste your token here: " PAT
fi

if [ -z "$PAT" ]; then
    echo "❌ No token provided"
    exit 1
fi

echo "✅ Token obtained"
echo ""

# Step 6: Set repository secret
MAIN_REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
echo "Setting BACKUP_PAT secret in ${MAIN_REPO}..."

echo "$PAT" | gh secret set BACKUP_PAT --repo "${MAIN_REPO}"
echo "✅ Secret configured"
echo ""

# Step 7: Verify FREESOUND_API_KEY
echo "Checking FREESOUND_API_KEY secret..."
if gh secret list --repo "${MAIN_REPO}" | grep -q "FREESOUND_API_KEY"; then
    echo "✅ FREESOUND_API_KEY is configured"
else
    echo "⚠️  FREESOUND_API_KEY is not configured"
    echo ""
    echo "You need to set your Freesound API key:"
    echo "1. Get your API key from: https://freesound.org/apiv2/apply/"
    echo "2. Run: gh secret set FREESOUND_API_KEY --repo ${MAIN_REPO}"
    echo ""
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Backup infrastructure setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Backup Repository: https://github.com/${BACKUP_REPO}"
echo "🔐 Secrets configured in: ${MAIN_REPO}"
echo ""
echo "Next steps:"
echo "1. Verify secrets: gh secret list --repo ${MAIN_REPO}"
echo "2. Test workflow: gh workflow run freesound-nightly-pipeline.yml --repo ${MAIN_REPO}"
echo "3. Monitor run: gh run list --workflow=freesound-nightly-pipeline.yml --repo ${MAIN_REPO}"
echo ""
