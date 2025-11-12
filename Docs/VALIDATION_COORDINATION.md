# Coordinated Validation System

## Overview

The Freesound pipeline uses a two-tier coordinated validation strategy to efficiently manage API quota while ensuring data integrity.

## Validation Workflows

### Quick Validation (Weekly)
- **Schedule**: Every Sunday at 3 AM UTC
- **Mode**: `partial` (300 oldest samples by `last_existence_check_at`)
- **API Usage**: ~2 requests
- **Duration**: <5 minutes
- **Artifact Retention**: 30 days
- **Skip Logic**: Automatically skips if full validation ran the same day

### Full Validation (Monthly)
- **Schedule**: 1st of each month at 4 AM UTC
- **Mode**: `full` (all samples)
- **API Usage**: ~27 requests per 4,000 samples
- **Duration**: 5-30 minutes (depends on library size)
- **Artifact Retention**: 90 days
- **Bonus**: Zero-cost metadata refresh

## Timestamp Tracking

### `last_existence_check_at`
- Updated by both quick and full validation
- Tracks when sample existence was last verified
- Used to prioritize samples for validation (oldest first)

### `last_metadata_update_at`
- Updated by full validation only
- Tracks when metadata was last refreshed
- Includes: `num_downloads`, `avg_rating`, `num_ratings`, `num_comments`
- Zero additional API cost (piggybacks on existence check)

## Schedule Coordination

When both workflows are scheduled for the same day (e.g., 1st Sunday of month):
1. Full validation runs at 4 AM UTC
2. Quick validation runs at 3 AM UTC (1 hour earlier)
3. Quick validation checks if full validation ran today
4. If yes, quick validation skips to avoid redundancy
5. This prevents duplicate API usage

## API Quota Allocation

| Workflow | Frequency | API Requests | Annual Total |
|----------|-----------|--------------|--------------|
| Quick Validation | Weekly | ~2 | ~104 |
| Full Validation (4K) | Monthly | ~27 | ~324 |
| **Total Validation** | - | - | **~428/year** |

Validation uses <0.06% of annual API budget (2000 requests/day × 365 days).

## Benefits

1. **Frequent Checks**: Weekly validation ensures recent existence checks
2. **Comprehensive Coverage**: Monthly validation covers all samples
3. **Efficient API Usage**: Batch validation (150 samples per request)
4. **Zero-Cost Metadata**: Metadata refresh piggybacks on validation
5. **Smart Coordination**: Prevents redundant API usage
6. **Flexible Scheduling**: Easy to customize frequencies

## Related Files

- Quick Validation: `.github/workflows/freesound-quick-validation.yml`
- Full Validation: `.github/workflows/freesound-full-validation.yml`
- Validation Script: `validate_freesound_samples.py`
- Full Documentation: `Docs/FREESOUND_PIPELINE.md`
