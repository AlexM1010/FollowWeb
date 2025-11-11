# Setup GitHub Secrets for Test Pipeline

## Required: FREESOUND_API_KEY

Your Freesound API key needs to be added as a GitHub secret.

### Option 1: GitHub Web UI (Recommended)

1. Go to your repository on GitHub
2. Click **Settings** tab
3. In left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Enter:
   - **Name**: `FREESOUND_API_KEY`
   - **Secret**: `your_api_key_here`
6. Click **Add secret**

### Option 2: GitHub CLI

```bash
# Set the API key as a secret
gh secret set FREESOUND_API_KEY --body "your_api_key_here"
```

### Verify Secret is Set

```bash
# List all secrets (values are hidden)
gh secret list
```

You should see:
```
FREESOUND_API_KEY  Updated YYYY-MM-DD
```

## Optional: BACKUP_PAT (For Checkpoint Persistence)

To enable checkpoint backup/restore between runs:

### Step 1: Create Private Backup Repository

```bash
gh repo create freesound-backup --private
```

### Step 2: Create Release for Checkpoints

```bash
gh release create v-checkpoint \
  --repo <your-username>/freesound-backup \
  --title "Checkpoint Storage" \
  --notes "Storage for Freesound pipeline checkpoints"
```

### Step 3: Generate Personal Access Token

1. Go to: https://github.com/settings/tokens
2. Click **Generate new token** → **Generate new token (classic)**
3. Enter note: "Freesound Checkpoint Backup"
4. Select scopes:
   - ✅ **repo** (Full control of private repositories)
5. Click **Generate token**
6. **Copy the token** (you won't see it again!)

### Step 4: Add BACKUP_PAT Secret

**GitHub Web UI:**
1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `BACKUP_PAT`
4. Secret: (paste your token)
5. Click **Add secret**

**GitHub CLI:**
```bash
gh secret set BACKUP_PAT --body "ghp_your_token_here"
```

## What Each Secret Does

### FREESOUND_API_KEY (Required)
- Authenticates with Freesound API
- Allows fetching sample data and similarity relationships
- Without this, the workflow will fail immediately

### BACKUP_PAT (Optional but Recommended)
- Enables checkpoint backup to private repository
- Allows incremental database growth between runs
- Without this:
  - ✅ Workflow still runs successfully
  - ❌ Each run starts with empty database
  - ❌ No persistence between runs

## Verification

After setting secrets, verify they're configured:

```bash
gh secret list
```

Expected output:
```
FREESOUND_API_KEY  Updated YYYY-MM-DD
BACKUP_PAT         Updated YYYY-MM-DD  (optional)
```

## Security Notes

- **Never commit API keys or tokens to Git**
- Secrets are encrypted and only accessible to GitHub Actions
- Secrets are not visible in logs or workflow outputs
- You can update secrets anytime without affecting workflows

## Ready to Run!

Once `FREESOUND_API_KEY` is set, you can run the test workflow:

```bash
gh workflow run freesound-pipeline-test.yml
```

Or via GitHub web UI:
```
Actions → Freesound Pipeline Test → Run workflow
```
