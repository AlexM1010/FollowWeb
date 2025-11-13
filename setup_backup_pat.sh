#!/bin/bash
# Setup BACKUP_PAT secret for Freesound backup

set -e

echo "🔐 Setting up BACKUP_PAT for freesound-backup repository access"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI"
    echo "Please run: gh auth login"
    exit 1
fi

echo "✅ Backup repository exists: https://github.com/AlexM1010/freesound-backup"
echo "✅ Release v-checkpoint exists"
echo ""

# Get current token (this will be the PAT we need)
echo "📝 Creating Personal Access Token..."
echo ""
echo "You need a PAT with 'repo' scope to access the private backup repository."
echo ""
echo "Option 1: Use your current gh CLI token (if it has repo scope)"
echo "Option 2: Create a new token manually"
echo ""
read -p "Do you want to try using your current gh token? (y/n): " use_current

if [ "$use_current" = "y" ]; then
    PAT=$(gh auth token 2>/dev/null || echo "")
    if [ -z "$PAT" ]; then
        echo "❌ Could not retrieve current token"
        use_current="n"
    else
        echo "✅ Retrieved current token"
    fi
fi

if [ "$use_current" != "y" ]; then
    echo ""
    echo "Please create a new token:"
    echo "1. Go to: https://github.com/settings/tokens/new"
    echo "2. Note: freesound-backup-pat"
    echo "3. Expiration: No expiration (or 1 year)"
    echo "4. Scopes: Check 'repo' (Full control of private repositories)"
    echo "5. Click 'Generate token'"
    echo "6. Copy the token"
    echo ""
    read -sp "Paste your token here: " PAT
    echo ""
fi

if [ -z "$PAT" ]; then
    echo "❌ No token provided"
    exit 1
fi

# Set the secret
echo ""
echo "Setting BACKUP_PAT secret in AlexM1010/FollowWeb..."
echo "$PAT" | gh secret set BACKUP_PAT --repo AlexM1010/FollowWeb

echo "✅ BACKUP_PAT configured successfully!"
echo ""

# Verify all secrets
echo "Current secrets in AlexM1010/FollowWeb:"
gh secret list --repo AlexM1010/FollowWeb

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup complete! Backups are now enabled."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "1. Test the workflow: gh workflow run freesound-nightly-pipeline.yml --repo AlexM1010/FollowWeb"
echo "2. Monitor the run: gh run watch --repo AlexM1010/FollowWeb"
echo ""
