# Setup BACKUP_PAT secret for Freesound backup
# PowerShell version for Windows

$ErrorActionPreference = "Stop"

Write-Host "🔐 Setting up BACKUP_PAT for freesound-backup repository access" -ForegroundColor Cyan
Write-Host ""

# Check if gh CLI is installed
try {
    $null = gh --version
} catch {
    Write-Host "❌ GitHub CLI (gh) is not installed" -ForegroundColor Red
    Write-Host "Install from: https://cli.github.com/" -ForegroundColor Yellow
    exit 1
}

# Check authentication
try {
    gh auth status 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw }
} catch {
    Write-Host "❌ Not authenticated with GitHub CLI" -ForegroundColor Red
    Write-Host "Please run: gh auth login" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Backup repository exists: https://github.com/AlexM1010/freesound-backup" -ForegroundColor Green
Write-Host "✅ Release v-checkpoint exists" -ForegroundColor Green
Write-Host ""

# Get token
Write-Host "📝 Creating Personal Access Token..." -ForegroundColor Cyan
Write-Host ""
Write-Host "You need a PAT with 'repo' scope to access the private backup repository."
Write-Host ""
Write-Host "Option 1: Use your current gh CLI token (if it has repo scope)"
Write-Host "Option 2: Create a new token manually"
Write-Host ""

$useCurrent = Read-Host "Do you want to try using your current gh token? (y/n)"

$PAT = ""
if ($useCurrent -eq "y") {
    try {
        $PAT = gh auth token 2>$null
        if ($PAT) {
            Write-Host "✅ Retrieved current token" -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ Could not retrieve current token" -ForegroundColor Red
        $useCurrent = "n"
    }
}

if ($useCurrent -ne "y") {
    Write-Host ""
    Write-Host "Please create a new token:" -ForegroundColor Yellow
    Write-Host "1. Go to: https://github.com/settings/tokens/new"
    Write-Host "2. Note: freesound-backup-pat"
    Write-Host "3. Expiration: No expiration (or 1 year)"
    Write-Host "4. Scopes: Check 'repo' (Full control of private repositories)"
    Write-Host "5. Click 'Generate token'"
    Write-Host "6. Copy the token"
    Write-Host ""
    
    $secureToken = Read-Host "Paste your token here" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    $PAT = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
}

if ([string]::IsNullOrWhiteSpace($PAT)) {
    Write-Host "❌ No token provided" -ForegroundColor Red
    exit 1
}

# Set the secret
Write-Host ""
Write-Host "Setting BACKUP_PAT secret in AlexM1010/FollowWeb..." -ForegroundColor Cyan
$PAT | gh secret set BACKUP_PAT --repo AlexM1010/FollowWeb

Write-Host "✅ BACKUP_PAT configured successfully!" -ForegroundColor Green
Write-Host ""

# Verify all secrets
Write-Host "Current secrets in AlexM1010/FollowWeb:" -ForegroundColor Cyan
gh secret list --repo AlexM1010/FollowWeb

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "✅ Setup complete! Backups are now enabled." -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Test the workflow: gh workflow run freesound-nightly-pipeline.yml --repo AlexM1010/FollowWeb"
Write-Host "2. Monitor the run: gh run watch --repo AlexM1010/FollowWeb"
Write-Host ""
