# Comprehensive Data Repair Implementation

## Overview

Implemented a unified, comprehensive data quality repair system that scans ALL samples, identifies ALL data quality issues, and fixes them efficiently using batch API calls.

## New Script: `comprehensive_data_repair.py`

### Location
`scripts/validation/comprehensive_data_repair.py`

### Features

✅ **Complete Data Quality Audit**
- Scans ALL samples in the checkpoint
- Checks ALL fields against expected schema
- Identifies missing fields, empty values, and invalid types

✅ **Intelligent Issue Categorization**
- Groups issues by field type
- Queues up to 150 samples per batch
- Prioritizes critical fields (uploader_id, name, duration, etc.)

✅ **Efficient Batch Processing**
- Uses Freesound batch search API: `filter=f"id:({space_separated_ids})"`
- Processes 150 samples per API request
- Respects max_requests limit

✅ **Smart Data Handling**
- Marks samples as `data_quality_checked` after processing
- Marks samples as `api_data_unavailable` if data not in API
- Adds `data_quality_repaired` flag when fixes applied
- Skips already-checked samples on subsequent runs

✅ **Comprehensive Field Coverage**
- **Critical fields**: uploader_id, name, tags, duration, username
- **Metadata**: license, created, url, category, type, channels, filesize, samplerate
- **Engagement**: num_downloads, num_ratings, avg_rating, num_comments
- **Optional**: description, pack, geotag

## Integration with GitHub Actions

### Updated Workflow: `freesound-data-repair.yml`

The repair workflow now uses the comprehensive script:

```yaml
- name: Run comprehensive data quality repair
  env:
    FREESOUND_API_KEY: ${{ secrets.FREESOUND_API_KEY }}
  run: |
    python scripts/validation/comprehensive_data_repair.py \
      --checkpoint-dir data/freesound_library \
      --api-key "$FREESOUND_API_KEY" \
      --max-requests 100
```

### Workflow Behavior

1. **Triggered automatically** after nightly collection completes
2. **Runs validation** checks first
3. **If validation fails**, runs comprehensive repair:
   - Phase 1: Scans all samples for issues
   - Phase 2: Fetches missing data in batches
   - Phase 3: Applies fixes across dataset
4. **Re-validates** after repairs
5. **Saves repaired checkpoint** to cache and backup

## Usage

### Standalone Execution

```bash
# Basic usage (uses .env for API key)
python scripts/validation/comprehensive_data_repair.py

# With custom checkpoint directory
python scripts/validation/comprehensive_data_repair.py \
  --checkpoint-dir data/freesound_library

# With API key and request limit
python scripts/validation/comprehensive_data_repair.py \
  --api-key YOUR_KEY \
  --max-requests 50
```

### In GitHub Actions

The script runs automatically as part of the repair workflow when validation fails.

## How It Works

### Phase 1: Data Quality Scan

```
Scanning 3,479 samples for data quality issues...
✓ Scan complete: 3,479 samples checked
  Total issues found: 3,479

Issues by field:
  - uploader_id: 3,479 samples
  - description: 245 samples
  - pack: 1,234 samples
```

### Phase 2: Apply Fixes

```
Processing 3,479 samples with issues...
Max API requests: 100
Batch size: 150 samples per request

[15:30:45] Batch 1/24: Fetching 150 samples...
  ✓ Fixed: 142, Unavailable: 8

[15:30:47] Batch 2/24: Fetching 150 samples...
  ✓ Fixed: 145, Unavailable: 5
...
```

### Phase 3: Report

```
📊 Statistics:
  Total samples:           3,479
  Samples checked:         3,479
  Issues found:            3,724
  Issues fixed:            3,450
  Marked unavailable:      274
  API requests used:       24/100

✅ Successfully repaired 3,450 samples
ℹ️  274 samples marked as unavailable
```

## Data Flags

The script adds metadata flags to track repair status:

### Success Case
```json
{
  "id": 12345,
  "name": "Sample Name",
  "uploader_id": 5121236,
  "data_quality_checked": "2025-11-22T16:00:00",
  "data_quality_repaired": true
}
```

### Unavailable Case
```json
{
  "id": 67890,
  "name": "Sample Name",
  "data_quality_checked": "2025-11-22T16:00:00",
  "api_data_unavailable": true
}
```

## Benefits

### Efficiency
- **Single pass**: Checks all fields in one scan
- **Batch processing**: 150 samples per API request
- **Smart caching**: Skips already-checked samples
- **Request limiting**: Respects max_requests budget

### Completeness
- **All samples**: No sample left unchecked
- **All fields**: Comprehensive field validation
- **All issues**: Identifies every data quality problem

### Maintainability
- **Single script**: One place for all repair logic
- **Clear phases**: Scan → Fix → Report
- **Extensible**: Easy to add new field checks

## Future Enhancements

Potential improvements:

1. **Priority levels**: Fix critical fields first (uploader_id, name)
2. **Incremental mode**: Only check samples modified since last run
3. **Parallel batches**: Process multiple batches concurrently
4. **Retry logic**: Exponential backoff for failed API calls
5. **Detailed reports**: JSON output with per-field statistics

## Testing

To test the script locally:

```bash
# Dry run (check only, no fixes)
python scripts/validation/comprehensive_data_repair.py --max-requests 0

# Small batch test
python scripts/validation/comprehensive_data_repair.py --max-requests 5

# Full repair
python scripts/validation/comprehensive_data_repair.py --max-requests 100
```

## Monitoring

The script outputs detailed progress:
- Real-time batch processing updates
- Issues found per field
- Fixes applied per batch
- API request usage tracking
- Final statistics summary

All output is captured in workflow logs and artifacts.
