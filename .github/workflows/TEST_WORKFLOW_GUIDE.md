# Freesound Pipeline Test Workflow Guide

## Quick Start

The test workflow is now available and ready to run! It's a full-featured version of the production pipeline with lower API limits, designed for incremental database growth with minimal API usage.

**Key Feature:** The test workflow uses the complete checkpoint backup/restore system, so each run continues building the database from where the previous run left off.

## How to Run

### Option 1: GitHub Web UI (Easiest)

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **Freesound Pipeline Test** from the left sidebar
4. Click **Run workflow** button (top right)
5. Configure parameters (or use defaults):
   - **Max Requests**: `50` (default)
   - **Recursive Depth**: `1` (default)
   - **Seed Sample ID**: Leave empty for auto-detect
6. Click **Run workflow**

### Option 2: GitHub CLI

```bash
# Run with defaults (50 requests, depth 1)
gh workflow run freesound-pipeline-test.yml

# Run with custom parameters
gh workflow run freesound-pipeline-test.yml \
  -f max_requests=50 \
  -f recursive_depth=1

# Run with specific seed sample
gh workflow run freesound-pipeline-test.yml \
  -f max_requests=50 \
  -f recursive_depth=1 \
  -f seed_sample_id=123456
```

## What It Does

1. **Setup** (2-3 minutes)
   - Checks out code
   - Sets up Python 3.11
   - Installs dependencies
   - Verifies FollowWeb package

2. **Checkpoint Restore** (1-2 minutes)
   - Downloads latest checkpoint from private repository
   - Restores graph topology, SQLite metadata, and JSON metadata
   - Continues from previous run's progress

3. **Workflow Conflict Check** (0-60 minutes)
   - Checks for conflicting workflows (nightly, validation)
   - Waits up to 1 hour if conflicts detected
   - Proceeds when safe to avoid checkpoint corruption

4. **Pipeline Execution** (5-15 minutes)
   - Fetches Freesound samples (max 50 API requests)
   - Builds graph with recursive discovery (depth 1)
   - Generates interactive visualization
   - Creates comprehensive logs

5. **Checkpoint Backup** (1-2 minutes)
   - Creates tar.gz archive of checkpoint data
   - Uploads to private repository release assets
   - Maintains 14-day rolling retention

6. **Git Persistence** (1 minute)
   - Commits visualizations and metrics to repository
   - Pushes changes with statistics in commit message

7. **Results & Artifacts**
   - Displays statistics in workflow summary
   - Uploads logs and visualizations (14-day retention)
   - Shows API usage vs limit

## Key Differences from Production Pipeline

| Feature | Test Workflow | Production Pipeline |
|---------|---------------|---------------------|
| **API Requests** | 50 (configurable) | 1950 (daily quota) |
| **Recursive Depth** | 1 (configurable) | 3 |
| **Checkpoint Backup** | ✅ Private repo backup | ✅ Private repo backup |
| **Checkpoint Restore** | ✅ Restored from backup | ✅ Restored from backup |
| **Git Commits** | ✅ Commits visualizations | ✅ Commits visualizations |
| **Scheduling** | ❌ Manual only | ✅ Daily at 2 AM UTC |
| **Timeout** | 60 minutes | 120 minutes |
| **Artifact Retention** | 14 days | 30 days |
| **Incremental Growth** | ✅ Continues from previous runs | ✅ Continues from previous runs |

## Expected Results

### First Run (Empty Database)
With default settings (50 requests, depth 1):

- **Nodes**: ~30-50 samples
- **Edges**: ~100-200 similarity relationships
- **API Requests**: ~40-50 (depends on seed sample)
- **Execution Time**: 10-20 minutes (includes checkpoint backup)
- **Output**: Interactive HTML visualization in `Output/` directory

### Subsequent Runs (Incremental Growth)
Each additional run with 50 requests:

- **Nodes Added**: ~20-40 new samples (some may already exist)
- **Edges Added**: ~50-150 new relationships
- **Total Growth**: Database grows incrementally with each run
- **Execution Time**: 10-20 minutes
- **Checkpoint**: Automatically restored and saved

## Troubleshooting

### "FREESOUND_API_KEY secret not configured"

**Solution:** Add your Freesound API key to repository secrets:
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `FREESOUND_API_KEY`
4. Value: Your Freesound API key
5. Click **Add secret**

### "BACKUP_PAT not configured"

**Solution:** Add a Personal Access Token for checkpoint backup:
1. Create a private repository named `freesound-backup`
2. Create a release in that repo with tag `v-checkpoint`
3. Generate a PAT with `repo` scope
4. Add to repository secrets as `BACKUP_PAT`

**Note:** Without BACKUP_PAT, the workflow will skip checkpoint backup/restore and start fresh each time.

### "API rate limit exceeded"

**Solution:** Wait 1 hour or reduce `max_requests` parameter.

### "Pipeline failed with exit code: 1"

**Solution:** Check the uploaded logs for detailed error messages:
1. Go to the failed workflow run
2. Scroll to bottom and download **test-pipeline-artifacts**
3. Open `test_pipeline_*.log` for details

## Viewing Results

### In Workflow Summary

The workflow automatically generates a summary with:
- Configuration parameters
- Execution status
- Statistics (nodes, edges, API calls)
- Seed sample information

### Downloading Artifacts

1. Go to the workflow run page
2. Scroll to **Artifacts** section at bottom
3. Download **test-pipeline-artifacts-{timestamp}**
4. Extract and open:
   - `test_pipeline_*.log` - Full execution log
   - `Output/*.html` - Interactive visualization (open in browser)

## Next Steps

After successful test:

1. **Review visualization**: Download and open the HTML file
2. **Check API usage**: Verify it stayed under 50 requests
3. **Validate data quality**: Inspect nodes and edges in visualization
4. **Run again**: Execute multiple times to see incremental growth
5. **Monitor checkpoint**: Check private repo for backup files
6. **Scale up**: Increase `max_requests` to 100-200 for faster growth
7. **Run production pipeline**: Use `freesound-nightly-pipeline.yml` for full collection (1950 requests/day)

## Configuration Options

### Max Requests

Controls the circuit breaker limit:
- **Minimum**: 10 (very small test)
- **Recommended**: 50 (good balance)
- **Maximum**: 100 (larger test, but still conservative)

### Recursive Depth

Controls how many levels of similar sounds to fetch:
- **0**: No recursion (seed samples only)
- **1**: Seed + similar sounds (recommended for testing)
- **2**: Seed + similar + similar-to-similar
- **3**: Three levels of recursion (production default)

### Seed Sample ID

Optional Freesound sample ID to start from:
- **Empty**: Auto-detect most downloaded sample (recommended)
- **Specific ID**: Use a known sample (e.g., `123456`)

## Example Runs

### Minimal Test (10 requests)
```bash
gh workflow run freesound-pipeline-test.yml -f max_requests=10 -f recursive_depth=0
```

### Standard Test (50 requests, default)
```bash
gh workflow run freesound-pipeline-test.yml
```

### Larger Test (100 requests)
```bash
gh workflow run freesound-pipeline-test.yml -f max_requests=100 -f recursive_depth=2
```

### Specific Sample Test
```bash
gh workflow run freesound-pipeline-test.yml -f seed_sample_id=414209
```

## Monitoring

Watch the workflow execution in real-time:
```bash
# List recent runs
gh run list --workflow=freesound-pipeline-test.yml

# Watch specific run
gh run watch <run-id>

# View logs
gh run view <run-id> --log
```
