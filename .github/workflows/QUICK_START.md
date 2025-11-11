# Quick Start: Test Pipeline

## Run Now (GitHub Web UI)

1. Go to **Actions** tab
2. Select **Freesound Pipeline Test**
3. Click **Run workflow**
4. Use defaults or customize:
   - Max Requests: `50` (default)
   - Recursive Depth: `1` (default)
5. Click **Run workflow**

## Run Now (GitHub CLI)

```bash
gh workflow run freesound-pipeline-test.yml
```

## What Happens

### First Run
- Downloads checkpoint (if exists) from private repo
- Fetches ~30-50 samples with 50 API requests
- Generates visualization
- Backs up checkpoint to private repo
- Commits visualization to repository
- **Time**: ~15-20 minutes

### Subsequent Runs
- Restores checkpoint from previous run
- Adds ~20-40 new samples with 50 API requests
- Updates visualization with new data
- Backs up updated checkpoint
- Commits updated visualization
- **Time**: ~15-20 minutes

## Incremental Growth Example

| Run | API Requests | Total Nodes | Total Edges | Time |
|-----|--------------|-------------|-------------|------|
| 1   | 50           | ~40         | ~150        | 15m  |
| 2   | 50           | ~70         | ~280        | 15m  |
| 3   | 50           | ~95         | ~400        | 15m  |
| 4   | 50           | ~115        | ~510        | 15m  |
| 5   | 50           | ~135        | ~615        | 15m  |

After 5 runs (250 requests total): ~135 nodes, ~615 edges

## Prerequisites

### Required Secrets

1. **FREESOUND_API_KEY** (required)
   - Your Freesound API key
   - Get from: https://freesound.org/apiv2/apply

2. **BACKUP_PAT** (optional but recommended)
   - Personal Access Token with `repo` scope
   - Enables checkpoint persistence between runs
   - Without this, each run starts fresh

### Setup BACKUP_PAT

```bash
# 1. Create private backup repository
gh repo create freesound-backup --private

# 2. Create release for checkpoints
gh release create v-checkpoint --repo <your-username>/freesound-backup --title "Checkpoint Storage" --notes "Storage for pipeline checkpoints"

# 3. Generate PAT
# Go to: Settings → Developer settings → Personal access tokens → Tokens (classic)
# Generate new token with 'repo' scope

# 4. Add to repository secrets
gh secret set BACKUP_PAT --repo <your-username>/<your-repo>
```

## Monitoring Progress

### View Run Status
```bash
gh run list --workflow=freesound-pipeline-test.yml
```

### Watch Live
```bash
gh run watch <run-id>
```

### View Summary
Check the workflow run page for:
- Nodes/edges added
- API requests used
- Seed sample information
- Checkpoint backup status

## Scaling Up

### Faster Growth (100 requests)
```bash
gh workflow run freesound-pipeline-test.yml -f max_requests=100
```

### Deeper Discovery (depth 2)
```bash
gh workflow run freesound-pipeline-test.yml -f recursive_depth=2
```

### Aggressive Testing (200 requests, depth 2)
```bash
gh workflow run freesound-pipeline-test.yml -f max_requests=200 -f recursive_depth=2
```

## Viewing Results

### View on GitHub Pages (Easiest!)
After workflow completes, visit:
```
https://<your-username>.github.io/<your-repo>/
```

**First-time setup (one-time only):**
1. Go to **Settings** → **Pages**
2. Under **Source**, select **GitHub Actions**
3. Save

The visualization will be live and interactive in your browser!

### View in Repository
After workflow completes, visualization is committed to `Output/` directory (download HTML file to view locally).

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "FREESOUND_API_KEY not configured" | Add secret in Settings → Secrets |
| "BACKUP_PAT not configured" | Add secret or workflow will skip backup |
| "API rate limit exceeded" | Wait 1 hour or reduce max_requests |
| "Workflow conflicts detected" | Wait for other workflows to complete |

## Full Documentation

See [TEST_WORKFLOW_GUIDE.md](./TEST_WORKFLOW_GUIDE.md) for complete documentation.
