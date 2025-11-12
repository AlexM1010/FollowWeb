# Freesound Nightly Pipeline Documentation

## Overview

The Freesound Nightly Pipeline is an automated system that continuously grows the Freesound sample library by consuming the daily API request allowance (2000 requests) and generating updated interactive visualizations. The pipeline runs automatically every night via GitHub Actions, building an ever-expanding network of audio samples connected by similarity relationships.

**Key Features:**
- 🌙 **Automated Nightly Execution**: Runs at 2 AM UTC daily via GitHub Actions
- 📈 **Continuous Growth**: Adds up to 2000 new samples per day
- 💾 **Git-Persisted Checkpoints**: All data committed to version control for durability
- 🔄 **Crash-Resistant**: Saves progress after every sample
- 🎨 **Interactive Visualizations**: Generates updated HTML visualizations after each run
- 🧹 **Automatic Cleanup**: Manages backup files with configurable retention
- ✅ **Weekly Validation**: Verifies sample availability and removes deleted samples
- ♾️ **Infinite Retention**: Samples never deleted based on age, only when removed from Freesound

## Architecture

### Split Checkpoint Architecture

The pipeline uses a **split checkpoint architecture** for scalable, efficient storage:

**Components:**
1. **Graph Topology** (`graph_topology.gpickle`): NetworkX graph with edges only, no node attributes
2. **SQLite Metadata** (`metadata_cache.db`): All sample metadata stored in indexed database
3. **Checkpoint Metadata** (`checkpoint_metadata.json`): Processing state, timestamps, connectivity metrics

**Benefits:**
- **50x faster I/O**: Batch writes and WAL mode reduce disk operations
- **20-30% speed improvement**: Faster saves/loads compared to monolithic pickle
- **Scalable to millions of nodes**: SQLite handles large datasets efficiently
- **No Git bloat**: Checkpoint data stored in private repository, not main repo
- **TOS compliant**: Data never exposed publicly (Freesound requirement)

**SQLite Optimizations:**
- **WAL mode**: Concurrent reads during writes
- **Batch writes**: Queue 50 samples before flushing
- **Indexed queries**: Fast lookups by sample_id, priority_score, last_updated
- **JSON storage**: Flexible metadata without schema changes

### Storage Strategy

**Persistent Storage: Private GitHub Repository**
- Checkpoint backups stored as release assets in private repository
- 14-day rolling retention policy (14 most recent backups kept)
- Secure, TOS-compliant (data never public)
- Durable across workflow runs

**Ephemeral Storage: Workflow Cache**
- Downloaded from private repo at workflow start
- Used for fast I/O during pipeline execution
- Wiped at workflow end (does NOT persist between runs)
- Reduces workflow execution time

### Nightly Collection Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                  GitHub Actions Scheduler                    │
│              Triggers at 2 AM UTC Daily                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Download Checkpoint from Private Repository          │
│  - Authenticates with BACKUP_PAT                             │
│  - Lists assets from v-checkpoint release                    │
│  - Downloads most recent checkpoint_backup_*.tar.gz          │
│  - Extracts to data/freesound_library/ (ephemeral cache)    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              generate_freesound_visualization.py             │
│  - Loads split checkpoint (topology + SQLite + metadata)    │
│  - Fetches up to 1950 samples via Freesound API             │
│  - Saves checkpoint after every 50 samples (batch)           │
│  - Generates interactive visualization                       │
│  - Appends metrics to data/metrics_history.jsonl            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│          Upload Checkpoint to Private Repository             │
│  - Creates checkpoint_backup_<run_id>.tar.gz archive         │
│  - Uploads as asset to v-checkpoint release                  │
│  - Logs backup creation with run_id and file size            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Backup Retention Policy (14-day)                │
│  - Lists all assets from v-checkpoint release                │
│  - Sorts by creation date (oldest first)                     │
│  - Deletes oldest assets if count > 14                       │
│  - Logs deleted backup filenames                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Git Commit & Push                         │
│  - Commits ONLY visualizations (Output/*.html)               │
│  - Commits metrics history (data/metrics_history.jsonl)      │
│  - Does NOT commit checkpoint data (in private repo)         │
│  - Pushes to GitHub                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Cleanup Ephemeral Cache (Always)                │
│  - Deletes data/freesound_library/ directory                 │
│  - Runs even on failure (if: always())                       │
│  - Logs cache wipe confirmation                              │
└─────────────────────────────────────────────────────────────┘
```

### Weekly Validation Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                  GitHub Actions Scheduler                    │
│            Triggers at 3 AM UTC Every Sunday                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              validate_freesound_samples.py                   │
│  - Loads checkpoint from Git                                 │
│  - Validates each sample against Freesound API              │
│  - Removes samples that return 404 Not Found                │
│  - Cleans up orphaned edges                                  │
│  - Saves cleaned checkpoint                                  │
│  - Generates validation report JSON                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Git Commit & Push                         │
│  - Commits cleaned checkpoint (if modified)                  │
│  - Uploads validation report as artifact                     │
│  - Pushes to GitHub                                          │
└─────────────────────────────────────────────────────────────┘
```

### How Data Persists Across Runs

The pipeline achieves continuous growth through private repository backups:

**Day 1:**
```
1. GitHub Actions starts (no backup exists yet)
2. Script collects up to 1950 samples → checkpoint has ~1950 nodes
3. Script generates visualization
4. Checkpoint uploaded to private repo as checkpoint_backup_<run_id>.tar.gz
5. Git commits ONLY visualization (Output/*.html) and metrics
6. Ephemeral cache wiped
```

**Day 2:**
```
1. GitHub Actions downloads checkpoint from private repo (~1950 nodes)
2. Script loads split checkpoint → resumes from ~1950 nodes
3. Script collects up to 1950 MORE samples → checkpoint now has ~3900 nodes
4. Script generates visualization
5. Checkpoint uploaded to private repo (new backup)
6. Git commits ONLY visualization and metrics
7. Ephemeral cache wiped
```

**Day 3 and beyond:** Continues from ~3900 nodes, then ~5850, then ~7800...

**Key Differences from Legacy Architecture:**
- ✅ **No Git bloat**: Checkpoint data NOT committed to main repository
- ✅ **TOS compliant**: Data stored ONLY in private repository (never public)
- ✅ **Faster saves/loads**: Split architecture with SQLite (<1s vs 10s+)
- ✅ **Scalable**: Can handle millions of nodes without performance degradation
- ✅ **Durable**: 14-day rolling backup window in private repo
- ✅ **Clean**: Ephemeral cache wiped after each run (no persistence between runs)

## GitHub Actions Setup

### Prerequisites

1. **Freesound API Key**: Obtain from [Freesound.org](https://freesound.org/apiv2/apply/)
2. **GitHub Repository**: Fork or clone this repository
3. **Private Backup Repository**: Create a private repository for checkpoint storage (TOS requirement)
4. **Personal Access Token (PAT)**: Generate with `repo` scope for private repository access
5. **GitHub Actions Enabled**: Ensure Actions are enabled in repository settings

### Configuration Steps

#### 1. Create Private Backup Repository

**Why required:** Freesound Terms of Service prohibit public distribution of bulk data. Checkpoint data MUST be stored in a private repository.

1. Navigate to GitHub and create a new repository
2. Name: `freesound-backup` (or any name you prefer)
3. **Visibility: Private** (CRITICAL - must be private)
4. Initialize with README (optional)
5. Create a release:
   - Go to **Releases** → **Create a new release**
   - Tag: `v-checkpoint`
   - Title: `Checkpoint Storage`
   - Description: `Rolling backup storage for Freesound pipeline checkpoints`
   - Click **Publish release**

#### 2. Generate Personal Access Token (PAT)

1. Go to **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token** → **Generate new token (classic)**
3. Name: `Freesound Backup Access`
4. Expiration: **No expiration** (or set to 1 year and renew annually)
5. Scopes: Check **`repo`** (full control of private repositories)
6. Click **Generate token**
7. **Copy the token immediately** (you won't be able to see it again)

#### 3. Add Secrets to Main Repository

1. Navigate to your **main repository** (not the backup repo) on GitHub
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Add two secrets:

**Secret 1: Freesound API Key**
- Click **New repository secret**
- Name: `FREESOUND_API_KEY`
- Value: Your Freesound API key
- Click **Add secret**

**Secret 2: Backup PAT**
- Click **New repository secret**
- Name: `BACKUP_PAT`
- Value: The Personal Access Token you generated in step 2
- Click **Add secret**

#### 2. Verify Workflow File

The workflow file is located at `.github/workflows/freesound-nightly-pipeline.yml` and should already be configured. It includes:

- **Scheduled execution**: `0 2 * * *` (2 AM UTC daily)
- **Manual trigger**: Workflow dispatch with custom parameters
- **Automatic Git operations**: Commits and pushes changes
- **Comprehensive logging**: Detailed execution summaries

#### 3. Enable Workflow (if needed)

If the workflow is disabled:

1. Go to **Actions** tab in your repository
2. Find "Freesound Nightly Pipeline" in the left sidebar
3. Click **Enable workflow** if prompted

### Automatic Execution

Once configured, the pipeline runs automatically every day at 2 AM UTC Monday through Saturday (Sunday reserved for validation). No manual intervention is required.

**What happens during each run:**
1. Downloads checkpoint from private repository (ephemeral cache)
2. Sets up Python 3.11 environment
3. Installs dependencies
4. Runs data collection (up to 1950 samples)
5. Generates visualization
6. Appends execution metrics to history
7. Uploads checkpoint to private repository
8. Applies 14-day retention policy (deletes old backups)
9. Commits ONLY visualizations and metrics to Git
10. Wipes ephemeral cache
11. Uploads logs as artifacts

**Workflow Coordination:**
- **Concurrency group**: `freesound-pipeline` prevents simultaneous executions
- **No cancellation**: Running workflows complete before new ones start
- **API quota allocation**: Nightly collection uses 1950 requests, validation uses remaining quota

### Manual Execution

You can trigger the pipeline manually with custom parameters:

1. Go to **Actions** tab in your repository
2. Select **Freesound Nightly Pipeline** workflow
3. Click **Run workflow** button
4. Configure parameters (all optional):
   - **seed_sample_id**: Leave empty to use most downloaded sample, or specify a sample ID
   - **max_requests**: Maximum API requests (default: 1950, circuit breaker before 2000 limit)
   - **recursive_depth**: Depth of similar sound exploration (default: 3)
5. Click **Run workflow**

**Example use cases for manual execution:**
- Testing with fewer requests: Set `max_requests` to 100
- Exploring from a specific sample: Set `seed_sample_id` to a known ID
- Deeper exploration: Set `recursive_depth` to 4

## Seed Sample Selection

The pipeline uses a seed sample as the starting point for recursive discovery of similar sounds.

### Automatic Selection (Recommended)

**Default behavior when `seed_sample_id` is not provided:**

1. Queries Freesound API for the most downloaded sample: `GET /apiv2/search/text/?query=*&sort=downloads_desc&page_size=1`
2. Uses that sample as the seed
3. Logs the seed sample ID, name, and download count

**Benefits:**
- Starts from high-quality, widely-used content
- Ensures the network grows from popular samples
- No manual configuration needed

**Fallback:**
- If API query fails, uses sample ID 2523 (a known popular sample)

### Manual Selection

**When to override:**
- Exploring a specific genre or category
- Resuming from a particular sample
- Testing with known samples

**How to override:**
- **GitHub Actions**: Set `seed_sample_id` parameter when manually triggering
- **Command line**: Use `--seed-sample-id` flag
- **Environment variable**: Set `FREESOUND_SEED_SAMPLE_ID`

**Example:**
```bash
python generate_freesound_visualization.py --seed-sample-id 12345
```

### Checkpoint Resumption

**Important:** When a checkpoint exists (i.e., not the first run), the seed sample ID is ignored. The pipeline automatically resumes from the checkpoint's priority queue, continuing to explore samples based on the existing network structure.

## Collection Strategies

The pipeline supports two collection strategies that control how samples are collected during recursive discovery.

### Collection Modes

#### Limit Mode (Default)

**Behavior:**
- Stops collection when `max_requests` limit is reached
- Provides predictable API quota usage
- Recommended for daily automated runs

**Use cases:**
- Daily nightly pipeline execution
- Controlled API quota consumption
- Predictable execution time

**Configuration:**
```bash
# Command line
python generate_freesound_visualization.py --max-requests 1950

# GitHub Actions (default)
max_requests: 1950
```

**Example:**
- Set `max_requests: 1950`
- Pipeline stops when 1950 API requests are consumed (circuit breaker before 2000 limit)
- Stops when limit is reached, even if priority queue has more samples
- Remaining samples stay in queue for next run

#### Queue-Empty Mode

**Behavior:**
- Continues until priority queue is empty
- Enforces absolute safety limit of 10,000 samples
- Explores network more completely in single run

**Use cases:**
- One-time deep exploration
- Building comprehensive subgraphs
- Research projects requiring complete coverage

**Configuration:**
```bash
# Command line
python generate_freesound_visualization.py --max-requests 1950

# GitHub Actions (manual trigger)
max_requests: 1950
```

**Example:**
- Set `max_requests: 1950`
- Pipeline stops when 1950 API requests are consumed (circuit breaker)
- Ensures graceful exit before hitting the hard 2000 request/day limit
- Useful for controlled daily collection

**Safety Limit:**
- Hard limit: 10,000 samples
- Prevents runaway collection
- Ensures execution completes within reasonable time
- Can be adjusted in code if needed for special cases

### Recursive Depth Levels

The `recursive_depth` parameter controls how many levels deep the pipeline explores similar sounds.

**Default: 3 levels**

#### Depth Level Explanation

**Depth 0: No recursion**
- Only collects seed samples
- No similar sounds fetched
- Minimal API usage
- Use case: Testing, specific sample collection

**Depth 1: One level**
```
Seed Sample
  └─ Similar Sound 1
  └─ Similar Sound 2
  └─ Similar Sound 3
```
- Collects seed samples and their direct similar sounds
- Moderate API usage
- Use case: Quick exploration, genre sampling

**Depth 2: Two levels**
```
Seed Sample
  └─ Similar Sound 1
      └─ Similar Sound 1.1
      └─ Similar Sound 1.2
  └─ Similar Sound 2
      └─ Similar Sound 2.1
```
- Collects seed samples, their similar sounds, and similar sounds of those
- Higher API usage
- Use case: Building connected subgraphs

**Depth 3: Three levels (Default)**
```
Seed Sample
  └─ Similar Sound 1
      └─ Similar Sound 1.1
          └─ Similar Sound 1.1.1
          └─ Similar Sound 1.1.2
      └─ Similar Sound 1.2
  └─ Similar Sound 2
```
- Collects three levels of similar sound relationships
- Highest API usage
- Use case: Comprehensive network building, discovering diverse samples
- **Recommended for nightly pipeline**: Balances exploration depth with API quota

**Depth 4+: Very deep exploration**
- Exponentially more samples
- May exceed API daily limit quickly
- Use case: Special research projects only

#### Choosing Depth Level

**For daily automated runs:**
- **Depth 3** (default): Best balance of exploration and API usage
- Discovers diverse samples while staying within quota
- Builds well-connected network over time

**For manual exploration:**
- **Depth 1-2**: Quick exploration of specific samples
- **Depth 3-4**: Deep exploration of genres or categories

**API Quota Considerations:**
- Each level multiplies the number of samples explored
- Depth 3 with limit mode (2000 samples) typically uses ~1800-2000 API requests
- Depth 4 may exceed daily limit (2000 requests) quickly

### Combining Strategies

**Recommended combinations:**

**Daily automated collection (default):**
```bash
--max-requests 1950 --depth 3
```
- Predictable API usage (circuit breaker at 1950 requests)
- Comprehensive exploration
- Builds network steadily over time

**Deep genre exploration:**
```bash
--max-requests 1950 --depth 3 --seed-sample-id 12345
```
- Explores specific genre with controlled API usage
- Starts from known sample in genre
- Stops at circuit breaker limit

**Quick testing:**
```bash
--max-requests 50 --depth 1
```
- Minimal API usage
- Fast execution
- Good for development and testing

**Research project:**
```bash
--max-requests 1950 --depth 4
```
- Maximum exploration depth
- Controlled API usage with circuit breaker
- May require multiple runs for complete coverage

### Monitoring Collection Strategy

**Log messages indicate active strategy:**

```
Starting recursive processing: depth=3, max_total=2000, mode=limit
Using priority-based processing: most popular samples (by downloads) first
🔄 Limit mode: Will stop at 2000 samples
```

or

```
Starting recursive processing: depth=3, max_total=2000, mode=queue-empty
Using priority-based processing: most popular samples (by downloads) first
🔄 Queue-empty mode: Will continue until priority queue is empty (safety limit: 10000)
```

**Completion messages:**

**Limit mode:**
```
✅ Reached max_total_samples limit (2000) after 45 minutes
```

**Queue-empty mode:**
```
✅ Priority queue empty after 2 hours (collected 5,432 samples)
```

or

```
⚠️ Reached safety limit (10000) in queue-empty mode after 3 hours
```

## Manual Execution (Local)

You can run the pipeline locally for development or testing.

### Prerequisites

1. Python 3.9 or higher
2. Freesound API key
3. Dependencies installed

### Installation

```bash
# Install dependencies
pip install -r FollowWeb/requirements.txt
pip install -e FollowWeb/

# Create .env file with API key
echo "FREESOUND_API_KEY=your_api_key_here" > .env
```

### Running the Pipeline

**Basic execution (uses defaults):**
```bash
python generate_freesound_visualization.py
```

**With custom parameters:**
```bash
# Specify seed sample ID
python generate_freesound_visualization.py --seed-sample-id 12345

# Limit API requests (useful for testing)
python generate_freesound_visualization.py --max-requests 100

# Adjust recursive depth
python generate_freesound_visualization.py --depth 3

# Combine multiple parameters
python generate_freesound_visualization.py --seed-sample-id 12345 --max-requests 500 --depth 3
```

**Using environment variables:**
```bash
# Set environment variables
export FREESOUND_API_KEY=your_api_key_here
export FREESOUND_SEED_SAMPLE_ID=12345
export FREESOUND_MAX_REQUESTS=500
export FREESOUND_DEPTH=3

# Run pipeline
python generate_freesound_visualization.py
```

### Running Cleanup Script

```bash
# Use defaults (7 days retention, keep 5 backups)
python cleanup_old_backups.py --checkpoint-dir data/freesound_library

# Custom retention policy
python cleanup_old_backups.py \
  --checkpoint-dir data/freesound_library \
  --max-backups 10 \
  --retention-days 14
```

## Monitoring

### GitHub Actions Logs

**Accessing logs:**
1. Go to **Actions** tab in your repository
2. Click on a workflow run
3. Click on the job name to view detailed logs

**Log sections:**
- **Setup**: Python installation, dependency installation
- **Data Collection**: API requests, checkpoint saves, progress updates
- **Visualization**: Graph building, HTML generation
- **Cleanup**: Backup file management
- **Git Operations**: Commit and push status

### Execution Summary

Each workflow run generates a comprehensive summary visible in the GitHub Actions UI:

**Summary includes:**
- ✅ Execution status (success/failure)
- ⏱️ Execution time
- 📊 Data collection statistics (nodes/edges added, totals)
- 🌱 Seed sample information
- 🎨 Visualization output path
- 🧹 Backup cleanup summary
- 📋 Execution details (ID, trigger, commit)

### Artifacts

**Pipeline logs** are uploaded as artifacts with 30-day retention:
- `pipeline_*.log`: Main pipeline execution log
- `freesound_viz_*.log`: Visualization generation log
- `fetch_freesound_*.log`: Data fetching log

**Accessing artifacts:**
1. Go to workflow run page
2. Scroll to **Artifacts** section at bottom
3. Download `pipeline-logs-{execution_id}.zip`

### Commit History

Each successful run creates a Git commit with statistics:

**Commit message format:**
```
Nightly pipeline: 2025-11-10 - +2000 nodes, +5000 edges
```

**View commit history:**
```bash
git log --oneline --grep="Nightly pipeline"
```

### Monitoring Metrics

**Key metrics to track:**
- **API requests used per run**: Should be close to `max_requests` (1950)
- **Total nodes**: Cumulative growth over time
- **Execution time**: Should be 30-60 minutes typically
- **Failure rate**: Should be near zero with proper configuration

## Sample Validation Workflows

The validation system uses two coordinated workflows to ensure the library only contains samples that still exist on Freesound while efficiently managing API quota. This maintains data integrity by removing samples that have been deleted from the platform and refreshing metadata at zero additional cost.

### Overview

**Purpose:**
- Verify that samples in the checkpoint still exist on Freesound
- Remove samples that have been deleted from the platform
- Refresh sample metadata (downloads, ratings, comments) at zero cost
- Clean up orphaned edges and maintain graph integrity
- Generate validation reports for monitoring

**Two-Tier Validation Strategy:**

1. **Quick Validation (Weekly)**
   - **Schedule**: Every Sunday at 3 AM UTC
   - **Coverage**: 300 oldest samples (by existence check age)
   - **API Usage**: ~2 API requests
   - **Duration**: <5 minutes
   - **Purpose**: Frequent validation with minimal API cost

2. **Full Validation (Monthly)**
   - **Schedule**: 1st of each month at 4 AM UTC
   - **Coverage**: All samples in library
   - **API Usage**: ~27 requests per 4,000 samples
   - **Duration**: 5-30 minutes depending on library size
   - **Purpose**: Comprehensive validation and metadata refresh

**Coordination:**
- Quick validation automatically skips if full validation ran the same day
- Prevents redundant API usage when schedules overlap
- Ensures efficient API quota allocation

**Duration Estimates (Full Validation):**
- **4,000 samples**: ~5 minutes (~27 API requests)
- **10,000 samples**: ~10 minutes (~67 API requests)
- **50,000 samples**: ~30 minutes (~334 API requests)

### How Coordinated Validation Works

**Quick Validation (Weekly - Sunday 3 AM UTC):**

```
┌─────────────────────────────────────────────────────────────┐
│           GitHub Actions Quick Validation Workflow           │
│              Triggers Sunday 3 AM UTC                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Check if Full Validation Ran Today              │
│  - Query GitHub Actions API for full validation runs         │
│  - If full validation ran today → SKIP (avoid redundancy)    │
│  - If no full validation today → PROCEED                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         validate_freesound_samples.py --mode partial         │
│  1. Load checkpoint from Git                                 │
│  2. Select 300 oldest samples by last_existence_check_at     │
│  3. Process in batches of 150 (~2 API requests):             │
│     - Use batch API search with ID filter                    │
│     - Check up to 150 samples per API request                │
│     - Mark for deletion if 404 Not Found                     │
│     - Skip if other API error (network, rate limit)          │
│  4. Update last_existence_check_at for validated samples     │
│  5. Remove deleted sample nodes from graph                   │
│  6. Remove deleted sample IDs from processed_ids             │
│  7. Count edges removed (automatic with nodes)               │
│  8. Save checkpoint with updated timestamps                  │
│  9. Generate validation report JSON                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Git Commit & Push                         │
│  - Commits checkpoint if changes made (deletions)            │
│  - Always commits to save validation timestamps              │
│  - Uploads validation report as artifact (30-day retention)  │
│  - Pushes to GitHub                                          │
└─────────────────────────────────────────────────────────────┘
```

**Full Validation (Monthly - 1st of Month 4 AM UTC):**

```
┌─────────────────────────────────────────────────────────────┐
│           GitHub Actions Full Validation Workflow            │
│         Triggers 1st of Month 4 AM UTC                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│          validate_freesound_samples.py --mode full           │
│  1. Load checkpoint from Git                                 │
│  2. Select ALL samples in library                            │
│  3. Process in batches of 150 (~27 requests for 4K samples): │
│     - Use batch API search with ID filter                    │
│     - Include metadata fields (downloads, ratings, etc.)     │
│     - Check up to 150 samples per API request                │
│     - Mark for deletion if 404 Not Found                     │
│     - Extract metadata for valid samples (zero-cost!)        │
│     - Skip if other API error (network, rate limit)          │
│  4. Update last_existence_check_at for all samples           │
│  5. Update last_metadata_update_at for all samples           │
│  6. Refresh metadata (downloads, ratings, comments)          │
│  7. Remove deleted sample nodes from graph                   │
│  8. Remove deleted sample IDs from processed_ids             │
│  9. Count edges removed (automatic with nodes)               │
│  10. Save checkpoint with updated timestamps and metadata    │
│  11. Generate validation report JSON                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Git Commit & Push                         │
│  - Commits checkpoint if changes made (deletions/metadata)   │
│  - Always commits to save validation timestamps              │
│  - Uploads validation report as artifact (90-day retention)  │
│  - Pushes to GitHub                                          │
└─────────────────────────────────────────────────────────────┘
```

**Schedule Coordination:**
- If both workflows are scheduled for the same day (e.g., 1st Sunday of month)
- Quick validation checks if full validation ran today
- If yes, quick validation skips to avoid redundant API usage
- This ensures efficient API quota allocation

### Validation Modes and Efficiency

The validation system supports two modes with **batch API calls** for maximum efficiency:

**Validation Modes:**

1. **Partial Mode (Quick Validation)**
   - Validates 300 oldest samples by `last_existence_check_at` timestamp
   - Uses ~2 API requests (2 batches of 150 samples)
   - Runs weekly to ensure frequent checks on oldest samples
   - Ideal for maintaining freshness with minimal API cost

2. **Full Mode (Full Validation)**
   - Validates all samples in the library
   - Uses batch validation (150 samples per request)
   - Runs monthly for comprehensive coverage
   - Refreshes all metadata at zero additional cost

**Batch Validation Method:**
- Uses `GET /apiv2/search/text/?filter=id:(id1 OR id2 OR ...)&fields=id,num_downloads,avg_rating,num_ratings,num_comments&page_size=150`
- Validates up to 150 samples per API request (Freesound API maximum)
- Includes metadata fields for zero-cost refresh
- Processes samples in batches instead of individual requests

**Efficiency Gains:**
- **For 4,000 samples**: Only ~27 API requests instead of 4,000 (148x more efficient!)
- **For 10,000 samples**: Only ~67 API requests instead of 10,000 (149x more efficient!)
- **For 50,000 samples**: Only ~334 API requests instead of 50,000 (150x more efficient!)

**Benefits:**
- Dramatically reduces validation time (minutes instead of hours)
- Minimizes API quota consumption
- Reduces network overhead and latency
- Enables more frequent validation runs
- Stays well within daily API limits (2000 requests/day)
- Zero-cost metadata refresh (piggybacks on existence checks)

**Fallback Mechanism:**
- Individual sample check method (`_check_sample_exists()`) available as fallback
- Used for edge cases or when batch validation fails
- Ensures robustness even if batch API changes

### Existence Checks vs Metadata Refresh

The validation system tracks two distinct timestamps for each sample:

**1. `last_existence_check_at`**
- **Purpose**: Tracks when sample existence was last verified on Freesound
- **Updated by**: Both quick and full validation workflows
- **Use case**: Determines which samples need validation (oldest first)
- **Frequency**: Weekly (quick) + Monthly (full)
- **API cost**: Included in validation request

**2. `last_metadata_update_at`**
- **Purpose**: Tracks when sample metadata was last refreshed
- **Updated by**: Full validation workflow only (includes metadata fields)
- **Metadata fields**: `num_downloads`, `avg_rating`, `num_ratings`, `num_comments`
- **Use case**: Keeps sample statistics current for analysis
- **Frequency**: Monthly (full validation only)
- **API cost**: ZERO (piggybacks on existence check)

**Why Two Timestamps?**
- **Existence checks** are lightweight and can run frequently (weekly)
- **Metadata refresh** happens automatically during full validation at no extra cost
- Separating timestamps allows efficient scheduling:
  - Quick validation: Updates existence timestamps only
  - Full validation: Updates both existence and metadata timestamps

**Example Timeline:**
```
Day 1: Quick validation runs
  → Updates last_existence_check_at for 300 oldest samples
  → Does NOT update last_metadata_update_at (no metadata fields requested)

Day 30: Full validation runs
  → Updates last_existence_check_at for ALL samples
  → Updates last_metadata_update_at for ALL samples (zero-cost bonus!)
  → Refreshes download counts, ratings, comments

Day 37: Quick validation runs again
  → Updates last_existence_check_at for 300 oldest samples
  → Does NOT update last_metadata_update_at
```

**Benefits:**
- Frequent existence checks ensure sample availability
- Monthly metadata refresh keeps statistics current
- Zero additional API cost for metadata (included in validation query)
- Efficient API quota allocation

### Validation Process Details

**API Verification:**
- Uses **batch validation** for efficiency: `GET /apiv2/search/text/?filter=id:(id1 OR id2 OR ...)`
- Validates up to 150 samples per API request (batch size)
- Fallback to individual checks: `GET /apiv2/sounds/{id}/?fields=id` if needed
- Implements retry logic: 3 attempts with 2-second delays
- Respects rate limits: 60 requests/minute
- Progress tracking with estimated time remaining
- **Efficiency**: ~27 API requests for 4,000 samples (vs 4,000 individual requests)

**Deletion Criteria:**
- **404 Not Found**: Sample is deleted from Freesound → Remove from checkpoint
- **401 Unauthorized**: API key issue → Skip sample, log error
- **429 Rate Limited**: Too many requests → Retry with backoff
- **500 Server Error**: Freesound issue → Skip sample, log error
- **Network Timeout**: Connection issue → Skip sample, log error

**Graph Cleanup:**
- Deleted sample nodes are removed using `graph.remove_node()`
- All edges connected to deleted nodes are automatically removed
- Deleted sample IDs are removed from `processed_ids` set
- Graph integrity is maintained (no orphaned edges)

### Running Validation Manually

**Via GitHub Actions:**

**Quick Validation:**
1. Go to **Actions** tab in your repository
2. Select **Freesound Quick Validation** workflow
3. Click **Run workflow** button
4. Click **Run workflow** to confirm
5. Monitor execution in real-time

**Full Validation:**
1. Go to **Actions** tab in your repository
2. Select **Freesound Full Validation** workflow
3. Click **Run workflow** button
4. Click **Run workflow** to confirm
5. Monitor execution in real-time

**Via Command Line (Local):**

```bash
# Ensure dependencies are installed
pip install -r FollowWeb/requirements.txt
pip install -e FollowWeb/

# Set API key
export FREESOUND_API_KEY=your_api_key_here

# Run quick validation (300 oldest samples)
python validate_freesound_samples.py --mode partial

# Run full validation (all samples)
python validate_freesound_samples.py --mode full

# Default mode is full if not specified
python validate_freesound_samples.py
```

**When to run manually:**
- After noticing broken samples in visualizations
- Before important analysis or presentations
- After Freesound announces content moderation actions
- When testing validation logic changes
- To force metadata refresh outside monthly schedule

### Validation Reports

**Report Location:**
- **GitHub Actions**: Uploaded as artifact (90-day retention)
- **Local Execution**: `logs/validation_{timestamp}.json`

**Report Format:**

```json
{
  "timestamp": "2025-11-10T03:00:00Z",
  "validation_mode": "partial",
  "total_samples": 10000,
  "validated_samples": 300,
  "metadata_refreshed": 300,
  "deleted_samples": [
    {
      "id": "12345",
      "name": "example_sound.wav"
    },
    {
      "id": "67890",
      "name": "another_sound.mp3"
    }
  ],
  "api_errors": 0,
  "edges_removed": 8
}
```

**Report Fields:**
- **timestamp**: When validation started (ISO 8601 format)
- **validation_mode**: Either "partial" (quick) or "full"
- **total_samples**: Total number of samples in checkpoint
- **validated_samples**: Number of samples checked in this run
- **metadata_refreshed**: Number of samples with refreshed metadata (full mode only)
- **deleted_samples**: Array of deleted sample details
  - `id`: Freesound sample ID
  - `name`: Sample filename
- **api_errors**: Number of API errors encountered (non-404)
- **edges_removed**: Total edges removed with deleted nodes

**Differences Between Quick and Full Reports:**

**Quick Validation Report:**
```json
{
  "validation_mode": "partial",
  "validated_samples": 300,
  "metadata_refreshed": 0
}
```
- Only validates 300 oldest samples
- Does not refresh metadata (no metadata fields in query)
- Updates `last_existence_check_at` only

**Full Validation Report:**
```json
{
  "validation_mode": "full",
  "validated_samples": 10000,
  "metadata_refreshed": 10000
}
```
- Validates all samples in library
- Refreshes metadata at zero cost (includes metadata fields)
- Updates both `last_existence_check_at` and `last_metadata_update_at`

**Accessing Reports:**

**From GitHub Actions:**
1. Go to workflow run page
2. Scroll to **Artifacts** section
3. Download `validation-report-{validation_id}.zip`
4. Extract and open JSON file

**From Local Execution:**
```bash
# View latest validation report
cat logs/validation_*.json | jq '.'

# Count deleted samples
cat logs/validation_*.json | jq '.statistics.deleted_samples'

# List deleted sample IDs
cat logs/validation_*.json | jq '.deleted_samples[].id'
```

### Monitoring Validation

**GitHub Actions Summary:**

Each validation run generates a summary with:
- ✅ Validation status (success/failure)
- ⏱️ Execution time
- 📊 Validation statistics (total, validated, deleted)
- 🗑️ Deleted samples list (if any)
- 📋 Validation report artifact link

**Key Metrics to Track:**
- **Deletion rate**: Should be low (<1% typically)
- **API errors**: Should be near zero
- **Execution time**: Increases with library size
- **Validation frequency**: Weekly is recommended

**Alerts to Watch For:**
- High deletion rate (>5%): May indicate Freesound content moderation
- Many API errors: Check API key and Freesound status
- Validation failures: Check logs for root cause
- Long execution time (>4 hours): Consider optimization

### Validation Best Practices

**For Automated Execution:**
1. **Keep weekly schedule**: Balances freshness with API usage
2. **Monitor deletion reports**: Review deleted samples periodically
3. **Check for patterns**: High deletion rates may indicate issues
4. **Preserve reports**: Download and archive validation reports
5. **Verify checkpoint integrity**: Ensure cleaned checkpoint is valid

**For Manual Execution:**
1. **Run after major events**: Freesound maintenance, content moderation
2. **Test locally first**: Verify validation logic with small datasets
3. **Check API quota**: Validation consumes API requests
4. **Review reports carefully**: Understand why samples were deleted
5. **Backup before validation**: Keep a copy of checkpoint before cleaning

**For Data Quality:**
1. **Regular validation**: Don't skip weekly runs
2. **Investigate anomalies**: High deletion rates need investigation
3. **Track deletion trends**: Monitor deletion patterns over time
4. **Document findings**: Note any unusual deletion events
5. **Update documentation**: Keep this guide current with findings

### Validation Troubleshooting

**High Deletion Rate:**

**Symptom:** Many samples deleted in single validation run

**Possible Causes:**
- Freesound content moderation sweep
- Uploader deleted many samples
- API key permissions changed
- Checkpoint corruption (false positives)

**Solutions:**
1. Review deleted samples list for patterns
2. Check Freesound announcements for moderation actions
3. Verify API key has correct permissions
4. Test validation with known good samples
5. Restore from backup if corruption suspected

**Validation Failures:**

**Symptom:** Validation workflow fails with error

**Common Causes:**
- Invalid API key
- Network connectivity issues
- Checkpoint file corruption
- Rate limit exceeded
- Disk space exhausted

**Solutions:**
1. Check API key is valid and has permissions
2. Retry validation (transient network issues)
3. Restore checkpoint from backup if corrupted
4. Wait for rate limit reset (next day)
5. Free up disk space if needed

**API Errors:**

**Symptom:** Many API errors in validation report

**Possible Causes:**
- Freesound API downtime
- Network instability
- Rate limiting
- API key issues

**Solutions:**
1. Check Freesound API status
2. Retry validation later
3. Verify API key permissions
4. Review error details in report
5. Contact Freesound support if persistent

**Long Execution Time:**

**Symptom:** Validation takes >4 hours

**Causes:**
- Large library size (>50,000 samples)
- Rate limiting delays
- Network latency
- API response slowness

**Solutions:**
1. This is expected for large libraries
2. Increase GitHub Actions timeout if needed
3. Consider batch validation (future enhancement)
4. Monitor but don't intervene unless timeout occurs
5. Optimize validation logic if consistently slow

### Validation Configuration

**GitHub Actions Workflows:**

**Quick Validation:**
- **File**: `.github/workflows/freesound-quick-validation.yml`
- **Schedule**: `0 3 * * 0` (3 AM UTC every Sunday)
- **Mode**: `partial` (300 oldest samples)
- **Timeout**: 30 minutes
- **Artifact Retention**: 30 days
- **Skip Logic**: Skips if full validation ran same day

**Full Validation:**
- **File**: `.github/workflows/freesound-full-validation.yml`
- **Schedule**: `0 4 1 * *` (4 AM UTC on 1st of each month)
- **Mode**: `full` (all samples)
- **Timeout**: 3 hours (180 minutes)
- **Artifact Retention**: 90 days

**Customizing Quick Validation Schedule:**

Edit `.github/workflows/freesound-quick-validation.yml`:

```yaml
on:
  schedule:
    # Run at 3 AM UTC every Sunday
    - cron: '0 3 * * 0'
    
  # Change to run twice weekly (Sunday and Wednesday):
  # - cron: '0 3 * * 0,3'
  
  # Change to run daily at 3 AM UTC:
  # - cron: '0 3 * * *'
```

**Customizing Full Validation Schedule:**

Edit `.github/workflows/freesound-full-validation.yml`:

```yaml
on:
  schedule:
    # Run at 4 AM UTC on 1st of each month
    - cron: '0 4 1 * *'
    
  # Change to run on 1st and 15th of each month:
  # - cron: '0 4 1,15 * *'
  
  # Change to run quarterly (1st of Jan, Apr, Jul, Oct):
  # - cron: '0 4 1 1,4,7,10 *'
```

**Customizing Timeout:**

```yaml
jobs:
  quick-validate:  # or full-validate
    timeout-minutes: 30  # Change as needed
```

**Customizing Artifact Retention:**

```yaml
- name: Upload validation report
  uses: actions/upload-artifact@v4
  with:
    name: validation-report-${{ steps.params.outputs.execution_id }}
    path: logs/validation_*.json
    retention-days: 30  # Change to 60, 90, or 365
```

**API Quota Allocation:**

The coordinated validation strategy efficiently allocates the daily API quota:

| Workflow | Frequency | API Requests | Annual Total |
|----------|-----------|--------------|--------------|
| Quick Validation | Weekly | ~2 | ~104 |
| Full Validation (4K samples) | Monthly | ~27 | ~324 |
| **Total Validation** | - | - | **~428/year** |
| Nightly Pipeline | Daily | ~1950 | ~711,750 |
| **Grand Total** | - | - | **~712,178/year** |

**Benefits:**
- Quick validation provides frequent checks with minimal cost
- Full validation ensures comprehensive coverage monthly
- Coordination prevents redundant API usage
- Total validation cost is <0.06% of annual API budget

## Workflow Orchestration

The workflow orchestration system coordinates execution between the three main workflows (nightly collection, quick validation, full validation) to prevent conflicts and ensure data integrity. This is especially important for manual triggers, which can run at any time and potentially conflict with scheduled workflows.

### Overview

**Purpose:**
- Prevent concurrent execution of conflicting workflows
- Coordinate manual triggers with scheduled runs
- Ensure checkpoint integrity by avoiding simultaneous modifications
- Maximize API quota efficiency by preventing redundant operations
- Provide graceful skip behavior when conflicts are detected

**Key Features:**
- GitHub API integration for real-time workflow status checks
- 2-hour timeout with graceful skip behavior
- File-based locking as fallback mechanism
- Comprehensive logging with EmojiFormatter
- GitHub Actions step summary integration

### How Workflow Orchestration Works

**Workflow Conflict Matrix:**

| Current Workflow | Conflicts With |
|------------------|----------------|
| Nightly Collection | Quick Validation, Full Validation |
| Quick Validation | Nightly Collection, Full Validation |
| Full Validation | Nightly Collection, Quick Validation |

**Coordination Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│                  Workflow Starts (Any Trigger)               │
│         Scheduled Run or Manual Trigger                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Check for Conflicting Workflows                 │
│  - Query GitHub API for running workflows                    │
│  - Check each workflow in conflict matrix                    │
│  - Use 30-second status cache to reduce API calls           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Conflict Detected?                          │
└────────┬───────────────────────────────────────────┬────────┘
         │ No                                         │ Yes
         │                                            │
         ▼                                            ▼
┌──────────────────────┐              ┌─────────────────────────┐
│  Proceed Immediately │              │  Wait for Completion    │
│  - Set can_proceed=  │              │  - Poll every 30s       │
│    true              │              │  - Exponential backoff  │
│  - Continue to data  │              │  - Max wait: 2 hours    │
│    collection/       │              │  - Log progress         │
│    validation        │              └────────┬────────────────┘
└──────────────────────┘                       │
                                               ▼
                                    ┌──────────────────────────┐
                                    │  Completed in 2 Hours?   │
                                    └────┬──────────────────┬──┘
                                         │ Yes              │ No
                                         │                  │
                                         ▼                  ▼
                              ┌──────────────────┐  ┌─────────────────┐
                              │  Proceed with    │  │  Skip Execution │
                              │  Execution       │  │  - Set can_     │
                              │  - Set can_      │  │    proceed=false│
                              │    proceed=true  │  │  - Log warning  │
                              │  - Continue to   │  │  - Write to step│
                              │    next step     │  │    summary      │
                              └──────────────────┘  │  - Continue to  │
                                                    │    next step    │
                                                    │    (skip work)  │
                                                    └─────────────────┘
```

### Timeout Behavior and Skip Logic

**2-Hour Timeout:**
- Maximum wait time for conflicting workflows to complete
- Configurable but should be sufficient for all workflows
- Prevents indefinite blocking

**Skip Logic (When Timeout Reached):**
1. **Set skip flag**: `can_proceed=false` output variable
2. **Log warning**: Detailed message with workflow details and run URL
3. **Write to step summary**: Visible warning in GitHub Actions UI
4. **Continue to next step**: Workflow does NOT exit, but skips work steps
5. **Conditional execution**: Work steps check `if: steps.orchestration.outputs.can_proceed == 'true'`

**Benefits of Skip Approach:**
- Workflow completes successfully (not marked as failed)
- Clear visibility in GitHub Actions UI
- No wasted API quota on conflicting operations
- Automatic retry on next scheduled run
- Preserves workflow history and logs

**Example Skip Message:**
```
⚠️ SKIPPING EXECUTION

Reason: Timeout (2 hours) waiting for freesound-full-validation to complete.
Skipping execution to avoid conflicts.

Workflow run: https://github.com/owner/repo/actions/runs/12345

The workflow will retry on the next scheduled run.
```

### Manual Trigger Coordination

**Scenario:** User manually triggers a workflow while another is running

**What Happens:**
1. Manual workflow starts and checks for conflicts
2. Detects running scheduled workflow
3. Waits up to 2 hours for scheduled workflow to complete
4. If completed: Proceeds with manual execution
5. If timeout: Skips execution with clear message

**Example Timeline:**
```
2:00 AM UTC: Nightly collection starts (scheduled)
2:30 AM UTC: User manually triggers full validation
  → Orchestrator detects nightly collection is running
  → Waits for nightly collection to complete
3:00 AM UTC: Nightly collection completes
  → Full validation proceeds immediately
```

**Example Timeout Scenario:**
```
2:00 AM UTC: Nightly collection starts (scheduled)
2:30 AM UTC: User manually triggers quick validation
  → Orchestrator detects nightly collection is running
  → Waits for nightly collection to complete
4:30 AM UTC: Timeout reached (2 hours)
  → Quick validation skips execution
  → Clear message in GitHub Actions UI
  → Will retry on next scheduled run (Sunday 3 AM UTC)
```

### Force Flag for Emergency Validation (Future Enhancement)

**Planned Feature:** Force flag to bypass coordination checks

**Use Case:**
- Emergency validation needed immediately
- Known safe to run concurrently (e.g., read-only analysis)
- Debugging or testing scenarios

**Implementation (Future):**
```yaml
workflow_dispatch:
  inputs:
    force:
      description: 'Force execution (bypass coordination checks)'
      required: false
      default: 'false'
      type: choice
      options:
        - 'false'
        - 'true'
```

**Behavior:**
- When `force=true`, skips all coordination checks
- Proceeds immediately regardless of running workflows
- Logs warning about forced execution
- User assumes responsibility for potential conflicts

**Safety Considerations:**
- Should only be used by experienced users
- Risk of checkpoint corruption if workflows modify data simultaneously
- Recommended to backup checkpoint before forcing

### WorkflowOrchestrator Utility

**Location:** `workflow_orchestrator.py` (project root)

**Key Methods:**

**`check_workflow_status(workflow_name: str) -> Optional[Dict]`**
- Queries GitHub API for workflow run status
- Returns run details if workflow is running, None otherwise
- Implements 30-second status cache to reduce API calls
- Handles rate limiting gracefully (429 responses)

**`wait_for_workflow(workflow_name: str, timeout: int = 7200) -> bool`**
- Polls workflow status until completion or timeout
- Uses exponential backoff (starts at 30s, max 5 minutes)
- Logs progress with elapsed and remaining time
- Returns True if completed, False if timeout

**`check_and_wait_for_conflicts(current_workflow: str, timeout: int = 7200) -> Tuple[bool, str]`**
- Main coordination method called by all workflows
- Checks all conflicting workflows from conflict matrix
- Waits for completion if conflicts detected
- Returns (can_proceed, reason) tuple

**`acquire_lock(lock_name: str, timeout: int = 300) -> bool`**
- File-based locking as fallback mechanism
- Uses atomic file creation to prevent race conditions
- Detects and cleans up stale locks (older than 2 hours)
- Returns True if lock acquired, False if timeout

**`release_lock(lock_name: str) -> None`**
- Releases file-based lock
- Called automatically when workflow completes

**Example Usage in Workflow:**
```yaml
- name: Check for workflow conflicts
  id: orchestration
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    python -c "
    from workflow_orchestrator import WorkflowOrchestrator
    import os
    
    orchestrator = WorkflowOrchestrator(
        github_token=os.environ['GITHUB_TOKEN'],
        repository='${{ github.repository }}'
    )
    
    can_proceed, reason = orchestrator.check_and_wait_for_conflicts(
        current_workflow='freesound-nightly-pipeline',
        timeout=7200
    )
    
    print(f'can_proceed={str(can_proceed).lower()}')
    
    if not can_proceed:
        with open(os.environ.get('GITHUB_STEP_SUMMARY', '/dev/null'), 'a') as f:
            f.write(f'## ⚠️ Execution Skipped\n\n')
            f.write(f'**Reason:** {reason}\n\n')
    "
    echo "can_proceed=$?" >> $GITHUB_OUTPUT

- name: Run data collection
  if: steps.orchestration.outputs.can_proceed == 'true'
  run: python generate_freesound_visualization.py
```

### Comprehensive Metadata Refresh During Validation

**Zero-Cost Metadata Refresh:**

During validation, the system refreshes all available metadata fields at no additional API cost by including them in the existence check query.

**Metadata Fields Refreshed (29 fields):**
- `id`, `url`, `name`, `tags`, `description`
- `category`, `subcategory`, `geotag`, `created`, `license`
- `type`, `channels`, `filesize`, `bitrate`, `bitdepth`
- `duration`, `samplerate`, `username`, `pack`
- `previews`, `images`, `num_downloads`, `avg_rating`
- `num_ratings`, `num_comments`, `comments`
- `similar_sounds`, `analysis`, `ac_analysis`

**Note:** `original_filename` and `md5` are filter-only parameters and NOT included in response fields.

**How It Works:**
1. Validation query includes comprehensive fields parameter
2. API returns existence status AND all metadata in single request
3. Validation script extracts and updates all fields in graph nodes
4. Updates `last_metadata_update_at` timestamp
5. Zero additional API cost (piggybacks on existence check)

**Benefits:**
- Keeps download counts, ratings, and comments current
- No additional API requests required
- Efficient use of API quota
- Comprehensive data refresh monthly (full validation)

**Example API Query:**
```
GET /apiv2/search/text/?filter=id:(12345 OR 67890 OR ...)
  &fields=id,url,name,tags,description,category,subcategory,geotag,created,
          license,type,channels,filesize,bitrate,bitdepth,duration,samplerate,
          username,pack,previews,images,num_downloads,avg_rating,num_ratings,
          num_comments,comments,similar_sounds,analysis,ac_analysis
  &page_size=150
```

### Troubleshooting Workflow Coordination

**Workflow Stuck Waiting:**

**Symptom:** Workflow waits for 2 hours and then skips

**Possible Causes:**
- Conflicting workflow is genuinely long-running
- Conflicting workflow is stuck or failed
- GitHub API status check is incorrect

**Solutions:**
1. Check conflicting workflow status in GitHub Actions UI
2. Cancel stuck workflow if it's failed or hung
3. Retry the waiting workflow after cancellation
4. Review logs of both workflows for root cause

**Frequent Skips:**

**Symptom:** Workflows frequently skip due to conflicts

**Possible Causes:**
- Workflows scheduled too close together
- Manual triggers during scheduled runs
- Long-running workflows exceeding expected duration

**Solutions:**
1. Adjust workflow schedules to avoid overlap
2. Increase timeout if workflows legitimately take longer
3. Optimize workflow execution time
4. Avoid manual triggers during scheduled run times

**GitHub API Rate Limiting:**

**Symptom:** Orchestrator logs "GitHub API rate limited" warnings

**Possible Causes:**
- Too many status checks in short period
- Other workflows or tools consuming API quota
- Status cache not working correctly

**Solutions:**
1. Status cache (30 seconds) should prevent this
2. Verify cache is working correctly
3. Increase cache TTL if needed
4. Orchestrator falls back to file-based locking if API unavailable

**File Lock Issues:**

**Symptom:** Workflow fails to acquire file lock

**Possible Causes:**
- Stale lock from crashed workflow
- Multiple workflows trying to acquire lock simultaneously
- File system permissions issue

**Solutions:**
1. Stale locks (>2 hours) are automatically cleaned up
2. Wait for lock timeout (5 minutes) and retry
3. Manually delete `.workflow_locks/*.lock` files if needed
4. Verify workflow has write permissions to repository

**Coordination Check Failures:**

**Symptom:** Orchestration step fails with error

**Possible Causes:**
- Invalid GitHub token
- Network connectivity issues
- Python import errors
- workflow_orchestrator.py missing or corrupted

**Solutions:**
1. Verify `GITHUB_TOKEN` secret is available
2. Check workflow_orchestrator.py exists in repository
3. Verify Python dependencies are installed
4. Review error details in workflow logs
5. Test orchestrator locally with dry-run mode

### Monitoring Workflow Coordination

**GitHub Actions Step Summary:**

Each workflow run includes coordination status in the step summary:

**Successful Coordination:**
```
✅ Workflow Coordination

No conflicts detected. Safe to proceed.

Checked workflows:
- freesound-quick-validation: Not running
- freesound-full-validation: Not running
```

**Skipped Execution:**
```
⚠️ Execution Skipped

Reason: Timeout (2 hours) waiting for freesound-nightly-pipeline to complete.

Workflow run: https://github.com/owner/repo/actions/runs/12345

The workflow will retry on the next scheduled run.
```

**Waited for Completion:**
```
✅ Workflow Coordination

Detected running workflow: freesound-full-validation
Waited 45 minutes for completion.
Safe to proceed.
```

**Key Metrics to Monitor:**
- **Skip frequency**: Should be rare (<5% of runs)
- **Wait times**: Most should complete within 1 hour
- **Timeout rate**: Should be near zero
- **API errors**: Should be minimal

**Logs to Review:**
- Orchestration step output in workflow logs
- EmojiFormatter messages for coordination events
- GitHub Actions step summary for skip reasons
- Workflow run URLs for conflicting workflows

### Best Practices for Workflow Coordination

**For Scheduled Runs:**
1. **Stagger schedules**: Space workflows at least 1 hour apart
2. **Monitor execution times**: Ensure workflows complete within expected duration
3. **Review skip events**: Investigate frequent skips
4. **Keep timeout at 2 hours**: Should be sufficient for all workflows

**For Manual Triggers:**
1. **Check running workflows**: Review Actions tab before manual trigger
2. **Avoid peak times**: Don't trigger during scheduled run times
3. **Be patient**: Wait for coordination checks to complete
4. **Review step summary**: Check coordination status after trigger

**For Development:**
1. **Test locally first**: Use dry-run mode to test orchestrator
2. **Use small datasets**: Test with limited API requests
3. **Monitor coordination logs**: Verify orchestrator behavior
4. **Document changes**: Update this guide with new findings

## Troubleshooting

### API Rate Limits

**Symptom:** Pipeline stops early with "429 Too Many Requests" error

**Causes:**
- Exceeded 60 requests/minute rate limit
- Exceeded 2000 requests/day daily limit

**Solutions:**
- **Rate limit (60/min)**: The pipeline automatically handles this with exponential backoff. No action needed.
- **Daily limit (2000/day)**: This is expected behavior. The pipeline will resume the next day.
- **Multiple runs per day**: Avoid running the pipeline multiple times in the same day to prevent hitting daily limits.

**Prevention:**
- Use `max_requests` ≤ 1950 (circuit breaker before 2000 limit)
- Run pipeline once per day
- Monitor API usage in Freesound account settings

### Understanding the Circuit Breaker (max_requests)

**What is max_requests?**

The `max_requests` parameter is a **circuit breaker** that stops the pipeline gracefully before hitting the hard API limit of 2000 requests per day. The default value is 1950, providing a 50-request safety margin.

**Why use a circuit breaker?**

- **Graceful exit**: Ensures the pipeline saves its checkpoint and exits cleanly before hitting the hard limit
- **Safety margin**: Prevents unexpected API errors from exceeding the daily quota
- **Predictable behavior**: You know exactly when the pipeline will stop
- **Error prevention**: Avoids 429 errors and potential API key throttling

**How it works:**

1. Pipeline tracks API request count during execution
2. Before each API call, checks if `session_request_count < max_requests`
3. If limit reached, saves checkpoint and exits gracefully with success status
4. Logs final summary showing "API requests used: X / 1950 limit"
5. Next run resumes from checkpoint and continues collection

**Recommended values:**

- **Daily automated runs**: 1950 (default) - safe margin before 2000 limit
- **Testing**: 10-100 - minimal API usage for development
- **Manual exploration**: 500-1000 - controlled exploration without exhausting quota

**Example log output:**
```
🔄 API request count: 1948 / 1950 limit
🔄 API request count: 1949 / 1950 limit
⚠️ Approaching max_requests limit (1950), stopping collection...
✅ Checkpoint saved successfully
📊 Final summary: API requests used: 1950 / 1950 limit
```

### Checkpoint Recovery

**Symptom:** Pipeline crashes or times out mid-execution

**What happens:**
- Checkpoint is saved after every sample (checkpoint_interval=1)
- Last committed checkpoint is safe in Git
- Next run automatically resumes from last checkpoint

**Manual recovery (if needed):**
```bash
# Check checkpoint status
python -c "
import joblib
checkpoint = joblib.load('data/freesound_library/freesound_library.pkl')
print(f\"Nodes: {checkpoint['metadata']['nodes']}\")
print(f\"Edges: {checkpoint['metadata']['edges']}\")
print(f\"Timestamp: {checkpoint['metadata']['timestamp']}\")
"

# If checkpoint is corrupted, restore from backup
cp data/freesound_library/freesound_library_backup_*nodes_*.pkl \
   data/freesound_library/freesound_library.pkl
```

**Prevention:**
- Keep `checkpoint_interval: 1` for maximum safety
- Monitor GitHub Actions timeout (2 hours)
- Ensure sufficient disk space

### Failed Runs

**Symptom:** Workflow fails with error

**Common causes and solutions:**

#### 1. Invalid API Key
**Error:** `401 Unauthorized` or `API key not found`

**Solution:**
- Verify `FREESOUND_API_KEY` secret is set correctly
- Check API key is valid at [Freesound.org](https://freesound.org/home/app_permissions/)
- Regenerate API key if needed

#### 2. Network Connectivity Issues
**Error:** `Connection timeout` or `Network unreachable`

**Solution:**
- Retry the workflow (transient network issues)
- Check GitHub Actions status page
- Verify Freesound API is operational

#### 3. Checkpoint File Corruption
**Error:** `Failed to load checkpoint` or `Pickle error`

**Solution:**
- Restore from most recent backup:
  ```bash
  # Find most recent backup
  ls -lt data/freesound_library/freesound_library_backup_*.pkl | head -1
  
  # Restore it
  cp data/freesound_library/freesound_library_backup_XXXXX.pkl \
     data/freesound_library/freesound_library.pkl
  
  # Commit and push
  git add data/freesound_library/freesound_library.pkl
  git commit -m "Restore checkpoint from backup"
  git push
  ```

#### 4. Disk Space Exhausted
**Error:** `No space left on device`

**Solution:**
- Clean up old artifacts in GitHub Actions
- Increase backup retention policy (delete more aggressively)
- Archive old visualizations

#### 5. Git Push Failures
**Error:** `Failed to push` or `Permission denied`

**Solution:**
- Verify GitHub Actions has write permissions
- Check repository settings → Actions → General → Workflow permissions
- Ensure "Read and write permissions" is enabled

### Seed Sample Selection Failures

**Symptom:** Pipeline fails to determine seed sample

**Error messages:**
- `Failed to fetch most downloaded sample`
- `No samples found in search results`

**What happens:**
- Pipeline automatically falls back to sample ID 2523
- Logs warning message
- Continues execution normally

**Manual override (if needed):**
```bash
# Specify a known good sample ID
python generate_freesound_visualization.py --seed-sample-id 2523
```

**Prevention:**
- Verify Freesound API is operational
- Check API key has search permissions
- Use manual seed sample ID for critical runs

### Debugging Tips

**Enable verbose logging:**
```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG
python generate_freesound_visualization.py
```

**Check checkpoint integrity:**
```bash
python -c "
import joblib
import networkx as nx
checkpoint = joblib.load('data/freesound_library/freesound_library.pkl')
graph = checkpoint['graph']
print(f'Graph type: {type(graph)}')
print(f'Nodes: {graph.number_of_nodes()}')
print(f'Edges: {graph.number_of_edges()}')
print(f'Is directed: {graph.is_directed()}')
print(f'Processed IDs: {len(checkpoint[\"processed_ids\"])}')
"
```

**Test API connectivity:**
```bash
curl -H "Authorization: Token YOUR_API_KEY" \
  "https://freesound.org/apiv2/search/text/?query=test&page_size=1"
```

**Dry run (test without API calls):**
```bash
# Use small max_requests for testing
python generate_freesound_visualization.py --max-requests 10
```

## Configuration

### Default Configuration

Configuration defaults are defined in `configs/freesound_pipeline_defaults.json`:

```json
{
  "seed_sample_id": null,
  "recursive_depth": 3,
  "max_requests": 1950,
  "page_size": 150,
  "checkpoint_interval": 1
}
```

**See `configs/FREESOUND_PIPELINE_CONFIG.md` for detailed parameter documentation.**

### Configuration Precedence

Configuration values are resolved in this order (highest to lowest priority):

1. **Command-line arguments**: `--seed-sample-id`, `--max-requests`, `--depth`
2. **Environment variables**: `FREESOUND_SEED_SAMPLE_ID`, `FREESOUND_MAX_REQUESTS`, `FREESOUND_DEPTH`
3. **Configuration file**: `configs/freesound_pipeline_defaults.json`
4. **Hardcoded defaults**: In script source code

### Customizing Configuration

**For GitHub Actions:**
- Edit workflow inputs in `.github/workflows/freesound-nightly-pipeline.yml`
- Modify default values in workflow dispatch inputs

**For local execution:**
- Edit `configs/freesound_pipeline_defaults.json`
- Set environment variables in `.env` file
- Pass command-line arguments

## Data Storage

### Checkpoint Files

**Main checkpoint:**
- **Location**: `data/freesound_library/freesound_library.pkl`
- **Format**: Joblib-serialized dictionary
- **Contents**: NetworkX graph, processed IDs, sound cache, metadata
- **Size**: ~10 KB per sample (metadata only, no audio files)
- **Git-tracked**: Yes (committed after every run)

**Backup checkpoints:**
- **Location**: `data/freesound_library/freesound_library_backup_*nodes_*.pkl`
- **Created**: Every 100 nodes
- **Naming**: `freesound_library_backup_{nodes}nodes_{timestamp}.pkl`
- **Retention**: 7 days (configurable)
- **Max count**: 5 most recent (configurable)
- **Git-tracked**: Yes (but cleaned up periodically)

### Visualization Files

**Location**: `Output/freesound_seed{id}_depth{depth}_n{nodes}_{timestamp}.html`

**Example**: `Output/freesound_seed2523_depth2_n4000_20251110_020000.html`

**Contents:**
- Interactive Sigma.js visualization
- Embedded graph data (nodes and edges)
- Hover tooltips with sample metadata
- Physics controls for layout adjustment

**Git-tracked**: Yes (committed after every run)

### Log Files

**Location**: `logs/` (if running locally) or workflow artifacts (if running in GitHub Actions)

**Files:**
- `pipeline_*.log`: Main execution log
- `freesound_viz_*.log`: Visualization generation log
- `fetch_freesound_*.log`: Data fetching log

**Retention**: 30 days (GitHub Actions artifacts)

## Data Retention Policy

### Sample Data: Infinite Retention

**Samples are NEVER deleted based on age or retention period.**

- The main checkpoint file grows indefinitely
- All historical sample data is preserved
- The library continues to grow without data loss
- Collection timestamps are recorded in the `collected_at` field but not used for deletion
- Each sample node includes a `collected_at` timestamp (ISO 8601 format) indicating when it was first added to the library

**Purpose of `collected_at` timestamp:**
- Tracks when each sample was first discovered and added to the library
- Enables historical analysis of library growth patterns
- Preserved across all checkpoint saves and loads
- Used for informational purposes only, never for deletion decisions

### Backup Files: Time-Limited Retention

**Backup checkpoint files are deleted after 7 days (configurable).**

- Only the 5 most recent backups are kept (configurable)
- The main checkpoint file is never deleted
- Cleanup runs automatically after each pipeline execution

### API-Driven Deletion

**Samples are only removed when they no longer exist on the Freesound API.**

The validation workflow runs weekly to verify sample availability:

- **Validation Schedule**: Every Sunday at 3 AM UTC (configurable via cron)
- **Validation Method**: Checks each sample against Freesound API using `GET /apiv2/sounds/{id}/`
- **Deletion Criteria**: Only samples that return 404 (Not Found) are removed
- **Edge Cleanup**: All edges connected to deleted samples are automatically removed
- **Logging**: Deletion events are logged with sample ID, name, and reason
- **Report Generation**: Validation report saved to `logs/validation_{timestamp}.json`

**Why API-driven deletion:**
- Respects Freesound's content moderation decisions
- Removes samples that violate terms of service
- Cleans up samples deleted by their uploaders
- Maintains library integrity with only accessible samples

## Performance

### Expected Performance

**Typical execution:**
- **API Requests**: 2000 requests (API daily limit)
- **Collection Time**: 30-60 minutes (with rate limiting)
- **Visualization Time**: 1-5 minutes (depends on graph size)
- **Total Runtime**: ~1 hour per execution

**Growth rate:**
- **Daily**: +2000 nodes, +5000-10000 edges (approximate)
- **Weekly**: +14000 nodes
- **Monthly**: +60000 nodes
- **Yearly**: +730000 nodes

### Resource Requirements

**GitHub Actions runner:**
- **CPU**: Minimal (I/O bound)
- **Memory**: ~500 MB peak usage
- **Disk**: ~100 MB per 10,000 samples
- **Network**: Stable internet connection required

**Local execution:**
- **Python**: 3.9 or higher
- **Disk Space**: ~1 GB recommended for checkpoints and visualizations
- **Memory**: 1 GB recommended

## Best Practices

### For Automated Execution

1. **Use default seed selection**: Let the pipeline automatically select the most downloaded sample
2. **Maximize daily collection**: Use `max_requests: 1950` to safely utilize API allowance with circuit breaker
3. **Keep checkpoint interval at 1**: Ensures no data loss on crashes or timeouts
4. **Monitor execution summaries**: Review GitHub Actions summaries regularly
5. **Archive old visualizations**: Periodically move old HTML files to separate storage

### For Development and Testing

1. **Use small max_requests**: Test with 10-100 requests to avoid consuming API quota
2. **Test locally first**: Verify changes work locally before pushing to GitHub
3. **Use manual triggers**: Test GitHub Actions workflow with manual dispatch
4. **Check logs carefully**: Review logs for warnings and errors
5. **Validate checkpoints**: Ensure checkpoint files are not corrupted after changes

### For Data Quality

1. **Start from popular samples**: Use automatic seed selection for high-quality content
2. **Monitor growth metrics**: Track nodes/edges added per run
3. **Validate periodically**: Run validation workflow to remove deleted samples (when implemented)
4. **Review visualizations**: Periodically check generated visualizations for quality
5. **Document anomalies**: Log any unusual patterns or errors

## Related Documentation

- **Configuration Guide**: `configs/FREESOUND_PIPELINE_CONFIG.md` - Detailed parameter documentation
- **Requirements**: `.kiro/specs/freesound-nightly-pipeline/requirements.md` - System requirements
- **Design Document**: `.kiro/specs/freesound-nightly-pipeline/design.md` - Architecture details
- **Task List**: `.kiro/specs/freesound-nightly-pipeline/tasks.md` - Implementation tasks
- **Nightly Pipeline Workflow**: `.github/workflows/freesound-nightly-pipeline.yml` - GitHub Actions configuration for data collection
- **Quick Validation Workflow**: `.github/workflows/freesound-quick-validation.yml` - GitHub Actions configuration for weekly quick validation
- **Full Validation Workflow**: `.github/workflows/freesound-full-validation.yml` - GitHub Actions configuration for monthly full validation
- **Validation Coordination Guide**: `Docs/VALIDATION_COORDINATION.md` - Coordinated validation system overview
- **Validation Script**: `validate_freesound_samples.py` - Sample validation implementation with mode support

## Support

### Getting Help

**For issues with the pipeline:**
1. Check this documentation for troubleshooting steps
2. Review GitHub Actions logs for error details
3. Check Freesound API status: [https://freesound.org/docs/api/](https://freesound.org/docs/api/)
4. Open an issue in the repository with:
   - Error message and full stack trace
   - Workflow run URL
   - Steps to reproduce
   - Environment details (Python version, OS, etc.)

**For Freesound API issues:**
- Freesound API documentation: [https://freesound.org/docs/api/](https://freesound.org/docs/api/)
- Freesound forums: [https://freesound.org/forum/](https://freesound.org/forum/)
- API support: [https://freesound.org/contact/](https://freesound.org/contact/)

### Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly (locally and in GitHub Actions)
5. Submit a pull request with detailed description

## License

This project uses the Freesound API which requires attribution. See Freesound's [terms of use](https://freesound.org/help/tos_web/) for details.


## Backup Strategy and Private Repository Storage

### Overview

The pipeline uses a **private GitHub repository** for persistent checkpoint storage to comply with Freesound Terms of Service (TOS), which prohibit public distribution of bulk data. This architecture provides:

- **TOS Compliance**: Checkpoint data stored ONLY in private repository (never public)
- **Durability**: 14-day rolling backup window ensures data safety
- **Scalability**: Split checkpoint architecture handles millions of nodes
- **Speed**: Ephemeral cache provides fast I/O during workflow execution
- **Clean Git History**: Main repository only contains visualizations and metrics

### 14-Day Rolling Retention Policy

**How it works:**
1. Every successful nightly run uploads checkpoint to private repository
2. Backup filename: `checkpoint_backup_<run_id>.tar.gz`
3. Stored as release asset under `v-checkpoint` tag
4. After upload, workflow lists all assets and sorts by creation date
5. If total count > 14, deletes oldest assets until only 14 remain
6. Logs deleted backup filenames for audit trail

**Benefits:**
- **2-week recovery window**: Can restore from any of last 14 runs
- **Automatic cleanup**: No manual intervention required
- **Predictable storage**: Storage size stays constant
- **Audit trail**: Logs show which backups were deleted

**Storage estimates:**
- **4,000 samples**: ~40 MB per backup × 14 = ~560 MB total
- **10,000 samples**: ~100 MB per backup × 14 = ~1.4 GB total
- **50,000 samples**: ~500 MB per backup × 14 = ~7 GB total

### Ephemeral Cache Workflow

**Workflow Start:**
1. Authenticates to private repository using `BACKUP_PAT`
2. Lists all assets from `v-checkpoint` release
3. Sorts by creation date to find most recent
4. Downloads `checkpoint_backup_*.tar.gz`
5. Extracts to `data/freesound_library/` (ephemeral cache)
6. Logs which backup was downloaded

**Workflow Execution:**
- Pipeline uses `data/freesound_library/` for fast I/O
- Checkpoint saved to cache after every 50 samples (batch)
- Metrics appended to `data/metrics_history.jsonl`

**Workflow End:**
- Creates `.tar.gz` archive of entire `data/freesound_library/` directory
- Uploads to private repository as new backup
- Applies 14-day retention policy
- Commits ONLY visualizations and metrics to Git
- Wipes `data/freesound_library/` directory (always runs, even on failure)

**Key Point:** Cache does NOT persist between workflow runs. It's downloaded fresh each time.

### Manual Backup Operations

**Download specific backup for local testing:**

```bash
# Set your PAT
export BACKUP_PAT=your_personal_access_token

# Get your repository owner
REPO_OWNER=your_github_username
BACKUP_REPO="${REPO_OWNER}/freesound-backup"

# List all backups
curl -H "Authorization: token $BACKUP_PAT" \
  "https://api.github.com/repos/${BACKUP_REPO}/releases/tags/v-checkpoint" \
  | jq '.assets[] | {name: .name, created_at: .created_at, size: .size}'

# Download specific backup (replace ASSET_ID)
ASSET_ID=123456789
curl -L -H "Authorization: token $BACKUP_PAT" \
  -H "Accept: application/octet-stream" \
  "https://api.github.com/repos/${BACKUP_REPO}/releases/assets/${ASSET_ID}" \
  -o checkpoint_backup.tar.gz

# Extract
mkdir -p data
tar -xzf checkpoint_backup.tar.gz -C data/

# Verify
ls -lh data/freesound_library/
```

**Verify backup integrity:**

```bash
# Check split checkpoint files exist
ls -lh data/freesound_library/graph_topology.gpickle
ls -lh data/freesound_library/metadata_cache.db
ls -lh data/freesound_library/checkpoint_metadata.json

# Inspect checkpoint metadata
cat data/freesound_library/checkpoint_metadata.json | jq '.'

# Check SQLite database
sqlite3 data/freesound_library/metadata_cache.db "SELECT COUNT(*) FROM metadata;"

# Load graph topology
python -c "
import networkx as nx
graph = nx.read_gpickle('data/freesound_library/graph_topology.gpickle')
print(f'Nodes: {graph.number_of_nodes()}')
print(f'Edges: {graph.number_of_edges()}')
"
```

**Create manual backup:**

```bash
# Create archive
tar -czf checkpoint_backup_manual_$(date +%Y%m%d_%H%M%S).tar.gz -C data freesound_library/

# Upload to private repository (requires BACKUP_PAT)
# See workflow file for upload script
```

### Troubleshooting Backup Issues

**Backup download fails:**

**Symptom:** Workflow fails at "Download checkpoint from private repository" step

**Possible causes:**
- `BACKUP_PAT` not configured or expired
- Private repository doesn't exist
- Release `v-checkpoint` not created
- No backups available yet (first run)

**Solutions:**
1. Verify `BACKUP_PAT` secret is set in main repository
2. Check PAT has `repo` scope and hasn't expired
3. Verify private repository exists and is accessible
4. Create `v-checkpoint` release if missing
5. If first run, workflow will start with empty checkpoint (expected)

**Backup upload fails:**

**Symptom:** Workflow fails at "Upload checkpoint to private repository" step

**Possible causes:**
- `BACKUP_PAT` expired or lacks permissions
- Release `v-checkpoint` doesn't exist
- Network connectivity issues
- File size exceeds GitHub limits (2 GB)

**Solutions:**
1. Regenerate PAT with `repo` scope
2. Create `v-checkpoint` release in private repository
3. Retry workflow (transient network issues)
4. If file > 2 GB, consider archiving old data

**Retention cleanup fails:**

**Symptom:** Old backups not deleted, storage grows unbounded

**Possible causes:**
- `BACKUP_PAT` lacks delete permissions
- API rate limiting
- Network issues during deletion

**Solutions:**
1. Verify PAT has `repo` scope (includes delete permissions)
2. Check workflow logs for specific error messages
3. Manually delete old backups via GitHub UI if needed
4. Retry workflow

**Cache wipe fails:**

**Symptom:** Ephemeral cache persists between runs

**Impact:** Minimal - cache will be overwritten on next run

**Solutions:**
- This is a non-critical failure
- Cache will be replaced on next download
- No action needed unless disk space is constrained

## Metrics Tracking

### Metrics History File

The pipeline tracks execution metrics in `data/metrics_history.jsonl` (JSON Lines format):

**Format:**
```json
{"timestamp":"2025-11-10T02:15:30Z","nodes_added":1950,"edges_added":5850,"api_requests":1950,"duration":1800}
{"timestamp":"2025-11-11T02:15:30Z","nodes_added":1950,"edges_added":5850,"api_requests":1950,"duration":1850}
```

**Fields:**
- `timestamp`: Execution start time (ISO 8601 UTC)
- `nodes_added`: New samples collected in this run
- `edges_added`: New edges created in this run
- `api_requests`: API requests consumed
- `duration`: Execution time in seconds

**Benefits:**
- Track growth trends over time
- Monitor API usage patterns
- Identify performance regressions
- Generate dashboards and reports

### Analyzing Metrics

**View recent metrics:**
```bash
# Last 10 runs
tail -10 data/metrics_history.jsonl | jq '.'

# Total nodes collected
cat data/metrics_history.jsonl | jq -s 'map(.nodes_added) | add'

# Average API requests per run
cat data/metrics_history.jsonl | jq -s 'map(.api_requests) | add / length'

# Average execution time (minutes)
cat data/metrics_history.jsonl | jq -s 'map(.duration / 60) | add / length'
```

**Generate growth chart (requires Python):**
```python
import json
import matplotlib.pyplot as plt
from datetime import datetime

# Load metrics
with open('data/metrics_history.jsonl') as f:
    metrics = [json.loads(line) for line in f]

# Extract data
dates = [datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) for m in metrics]
cumulative_nodes = []
total = 0
for m in metrics:
    total += m['nodes_added']
    cumulative_nodes.append(total)

# Plot
plt.figure(figsize=(12, 6))
plt.plot(dates, cumulative_nodes, marker='o')
plt.xlabel('Date')
plt.ylabel('Total Nodes')
plt.title('Freesound Library Growth Over Time')
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('growth_chart.png')
print("Chart saved to growth_chart.png")
```

### Metrics Dashboard (Optional Enhancement)

See Task 25.2 in the implementation plan for creating an automated metrics dashboard generator that produces:
- Graph growth over time (nodes and edges)
- API requests used per run (with limit line)
- Cache hit ratio over time
- Execution duration over time

## Troubleshooting New Architecture

### Split Checkpoint Issues

**Symptom:** Pipeline fails to load checkpoint

**Error messages:**
- `Failed to load split checkpoint`
- `SQLite database is locked`
- `Graph topology file not found`

**Solutions:**

**Missing files:**
```bash
# Check which files exist
ls -lh data/freesound_library/

# Should see:
# - graph_topology.gpickle
# - metadata_cache.db
# - checkpoint_metadata.json

# If missing, restore from backup
```

**SQLite database locked:**
```bash
# Check for stale lock files
ls -lh data/freesound_library/*.db-*

# Remove lock files (safe if no other process is running)
rm data/freesound_library/metadata_cache.db-shm
rm data/freesound_library/metadata_cache.db-wal

# Retry pipeline
```

**Corrupted database:**
```bash
# Check database integrity
sqlite3 data/freesound_library/metadata_cache.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
# Download most recent backup from private repository
```

### Migration from Legacy Checkpoint

**Automatic migration:**
- Pipeline automatically detects legacy checkpoint (`freesound_library.pkl`)
- Migrates to split architecture on first load
- Logs migration progress
- Saves split checkpoint
- Legacy checkpoint can be deleted after successful migration

**Manual migration (if needed):**
```python
import networkx as nx
import json
from pathlib import Path
from FollowWeb_Visualizor.data.storage import MetadataCache
from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint

# Load legacy checkpoint
checkpoint = GraphCheckpoint('data/freesound_library/freesound_library.pkl')
data = checkpoint.load()

graph = data['graph']
processed_ids = data['processed_ids']

# Create split checkpoint directory
checkpoint_dir = Path('data/freesound_library')
checkpoint_dir.mkdir(parents=True, exist_ok=True)

# 1. Save graph topology (clean graph without attributes)
graph_clean = graph.copy()
for node in graph_clean.nodes():
    graph_clean.nodes[node].clear()
nx.write_gpickle(graph_clean, str(checkpoint_dir / 'graph_topology.gpickle'))

# 2. Save metadata to SQLite
metadata_cache = MetadataCache(str(checkpoint_dir / 'metadata_cache.db'))
metadata_dict = {}
for node_id in graph.nodes():
    node_data = dict(graph.nodes[node_id])
    if node_data:
        metadata_dict[int(node_id)] = node_data
metadata_cache.bulk_insert(metadata_dict)
metadata_cache.close()

# 3. Save checkpoint metadata
checkpoint_metadata = {
    'timestamp': data['metadata']['timestamp'],
    'nodes': graph.number_of_nodes(),
    'edges': graph.number_of_edges(),
    'processed_ids': list(processed_ids),
    'validation_history': data['metadata'].get('validation_history', {})
}
with open(checkpoint_dir / 'checkpoint_metadata.json', 'w') as f:
    json.dump(checkpoint_metadata, f, indent=2)

print("Migration complete!")
print(f"Nodes: {checkpoint_metadata['nodes']}")
print(f"Edges: {checkpoint_metadata['edges']}")
```

### Private Repository Access Issues

**Symptom:** Cannot access private repository

**Error messages:**
- `404 Not Found` when accessing private repository
- `401 Unauthorized` when downloading/uploading backups
- `403 Forbidden` when deleting old backups

**Solutions:**

**PAT not configured:**
1. Verify `BACKUP_PAT` secret exists in main repository
2. Go to Settings → Secrets and variables → Actions
3. Check `BACKUP_PAT` is listed
4. If missing, add it with your Personal Access Token

**PAT expired:**
1. Generate new PAT with `repo` scope
2. Update `BACKUP_PAT` secret in main repository
3. Retry workflow

**PAT lacks permissions:**
1. Verify PAT has `repo` scope (full control of private repositories)
2. Regenerate PAT if needed
3. Update `BACKUP_PAT` secret

**Private repository doesn't exist:**
1. Create private repository (e.g., `freesound-backup`)
2. Create release tagged `v-checkpoint`
3. Verify repository name matches workflow configuration

**Release doesn't exist:**
1. Go to private repository
2. Click Releases → Create a new release
3. Tag: `v-checkpoint`
4. Title: `Checkpoint Storage`
5. Click Publish release

### Workflow Coordination Issues

**Symptom:** Multiple workflows running simultaneously

**Impact:**
- API quota exhausted quickly
- Checkpoint conflicts
- Backup corruption

**Solutions:**

**Check concurrency group:**
```yaml
# In .github/workflows/freesound-nightly-pipeline.yml
concurrency:
  group: freesound-pipeline
  cancel-in-progress: false
```

**Verify no manual triggers during scheduled runs:**
- Avoid manually triggering workflow when scheduled run is active
- Check Actions tab for running workflows before manual trigger
- Wait for current run to complete

**Check for workflow collisions:**
```bash
# List recent workflow runs
gh run list --workflow=freesound-nightly-pipeline.yml --limit 10

# Check for overlapping runs
gh run view <run-id>
```

### Performance Issues

**Symptom:** Checkpoint save/load is slow

**Expected performance:**
- Save: <1 second for split checkpoint
- Load: <1 second for split checkpoint

**If slower:**

**Check SQLite optimizations:**
```bash
# Verify WAL mode is enabled
sqlite3 data/freesound_library/metadata_cache.db "PRAGMA journal_mode;"
# Should return: wal

# Verify synchronous mode
sqlite3 data/freesound_library/metadata_cache.db "PRAGMA synchronous;"
# Should return: 1 (NORMAL)
```

**Check batch write settings:**
- Batch size: 50 samples (default)
- Increase if save operations are frequent
- Decrease if memory constrained

**Check file sizes:**
```bash
# Graph topology should be small (edges only, no attributes)
ls -lh data/freesound_library/graph_topology.gpickle

# SQLite database grows with samples (~10 KB per sample)
ls -lh data/freesound_library/metadata_cache.db

# If files are unexpectedly large, investigate
```

## Best Practices

### For Production Use

1. **Always use private repository**: Never store checkpoint data publicly (TOS violation)
2. **Monitor backup retention**: Verify 14-day policy is working
3. **Track metrics history**: Commit `data/metrics_history.jsonl` to Git
4. **Review workflow logs**: Check for warnings or errors
5. **Test PAT expiration**: Set calendar reminder to renew PAT before expiration
6. **Document custom configurations**: Note any changes to default settings
7. **Archive old visualizations**: Move old HTML files to separate branch if needed

### For Development

1. **Use small max_requests**: Test with 10-100 requests to save API quota
2. **Test locally first**: Verify changes before pushing to GitHub Actions
3. **Use manual seed samples**: Test with known good samples
4. **Backup before major changes**: Download checkpoint before testing new features
5. **Monitor API usage**: Track requests to avoid hitting daily limit
6. **Use separate test repository**: Don't test on production data

### For Data Quality

1. **Run validation regularly**: Weekly quick validation + monthly full validation
2. **Review deletion reports**: Investigate high deletion rates
3. **Monitor connectivity metrics**: Track graph connectivity over time
4. **Verify metadata freshness**: Check `last_metadata_update_at` timestamps
5. **Audit backup integrity**: Periodically verify backups can be restored
6. **Document anomalies**: Note unusual events in repository wiki or issues

## Additional Resources

### Documentation

- **Freesound API Documentation**: https://freesound.org/docs/api/
- **Freesound Terms of Service**: https://freesound.org/help/tos_web/
- **GitHub Actions Documentation**: https://docs.github.com/en/actions
- **NetworkX Documentation**: https://networkx.org/documentation/stable/

### Support

- **Freesound Forum**: https://freesound.org/forum/
- **GitHub Issues**: Report bugs or request features in repository issues
- **API Support**: Contact Freesound support for API-related questions

### Related Files

- **Main Pipeline Script**: `generate_freesound_visualization.py`
- **Validation Script**: `validate_freesound_samples.py`
- **Nightly Workflow**: `.github/workflows/freesound-nightly-pipeline.yml`
- **Quick Validation Workflow**: `.github/workflows/freesound-quick-validation.yml`
- **Full Validation Workflow**: `.github/workflows/freesound-full-validation.yml`
- **Implementation Plan**: `.kiro/specs/freesound-nightly-pipeline/tasks.md`
- **Design Document**: `.kiro/specs/freesound-nightly-pipeline/design.md`
- **Requirements Document**: `.kiro/specs/freesound-nightly-pipeline/requirements.md`
