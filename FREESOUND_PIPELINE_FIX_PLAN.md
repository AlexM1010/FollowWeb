# Freesound Pipeline Fix Plan

## Current Status

### Problems Identified

1. **Checkpoint Corruption**
   - Local checkpoint: 140 nodes, 0 edges
   - Backup repository checkpoint: 515 nodes, 6060 edges (but metadata says 0 edges)
   - Validation failures due to edge count mismatch
   - Multiple failed workflow runs

2. **Root Cause**
   - Checkpoint metadata `edge_count` field not matching actual graph edges
   - Graph topology file missing edges or metadata out of sync
   - Cascading failures across validation, backup, and collection workflows

3. **Impact**
   - Validation workflow: Failing (7+ consecutive failures)
   - Backup workflow: Correctly skipping due to validation failures
   - Collection workflow: Cannot proceed due to corrupted checkpoint state
   - No new data being collected

## Solution Options

### Option A: Fix Existing Checkpoint (Complex)
**Pros:**
- Preserves existing 515 nodes of collected data
- No data loss

**Cons:**
- Complex edge regeneration required
- Need to rebuild edges from metadata (user, pack, tag relationships)
- Risk of incomplete or incorrect edge reconstruction
- Time-consuming debugging

**Steps:**
1. Download checkpoint from backup repository
2. Analyze metadata cache to identify relationship data
3. Regenerate edges based on:
   - User relationships (samples by same user)
   - Pack relationships (samples in same pack)
   - Tag relationships (samples with similar tags)
4. Update checkpoint metadata with correct edge count
5. Validate fixed checkpoint
6. Re-upload to backup repository

### Option B: Start Fresh (Simple) ⭐ RECOMMENDED
**Pros:**
- Clean slate - no corruption
- Simple and fast to implement
- Guaranteed to work
- Pipeline will rebuild data correctly from scratch

**Cons:**
- Loses existing 515 nodes of data
- Will take time to rebuild (but pipeline is automated)

**Steps:**
1. Delete all checkpoint backups from backup repository
2. Clear local checkpoint directory
3. Clear GitHub Actions cache
4. Trigger new collection run
5. Monitor pipeline to ensure clean start

## Recommended Solution: Option B (Start Fresh)

### Rationale
1. **Simplicity**: Clean reset is straightforward and low-risk
2. **Reliability**: Eliminates all corruption issues
3. **Automation**: Pipeline will automatically rebuild data
4. **Time**: Fixing edges is complex and time-consuming vs. letting pipeline rebuild
5. **Data Volume**: 515 nodes is relatively small, can be rebuilt quickly

### Implementation Plan

#### Phase 1: Reset Pipeline (Immediate)
```bash
# Set environment variable
export BACKUP_PAT=<your_token>

# Run reset script
bash scripts/reset_freesound_pipeline.sh
```

**Actions:**
- ✅ Delete all checkpoint backups from `AlexM1010/freesound-backup`
- ✅ Clear `data/freesound_library/` (keep README.md and .gitkeep)
- ✅ Delete all `checkpoint-*` caches from GitHub Actions

**Expected Result:**
- No checkpoints in backup repository
- Empty local checkpoint directory
- No checkpoint caches

#### Phase 2: Trigger Fresh Collection (Immediate)
```bash
# Trigger manual collection run
gh workflow run freesound-nightly-pipeline.yml --repo AlexM1010/FollowWeb
```

**Expected Behavior:**
1. Collection workflow starts with 0 nodes, 0 edges
2. Fetches samples from Freesound API
3. Builds graph with proper edges
4. Saves checkpoint with correct metadata
5. Validation workflow validates checkpoint
6. Backup workflow uploads to repository

#### Phase 3: Monitor First Run (1-2 hours)
**Check:**
- Collection workflow completes successfully
- Checkpoint has nodes > 0 and edges > 0
- Validation workflow passes
- Backup workflow uploads checkpoint
- No error messages in logs

**Success Criteria:**
- ✅ Collection: Completes with new samples
- ✅ Validation: Passes all checks
- ✅ Backup: Uploads checkpoint successfully
- ✅ Checkpoint metadata: `nodes` and `edges` match actual graph

#### Phase 4: Verify Nightly Schedule (24 hours)
**Check:**
- Nightly scheduled run executes at 2 AM UTC
- Pipeline continues from previous checkpoint
- Data accumulates correctly
- No validation failures

**Success Criteria:**
- ✅ Scheduled runs execute on time
- ✅ Checkpoint grows incrementally
- ✅ No workflow failures
- ✅ Backup repository has recent checkpoints

### Rollback Plan

If fresh start fails:
1. Check workflow logs for errors
2. Verify API credentials (FREESOUND_API_KEY, BACKUP_PAT)
3. Check repository permissions
4. Review validation script for issues
5. Consider Option A (fix existing checkpoint) if data preservation is critical

### Prevention Measures

To prevent future corruption:

1. **Enhanced Validation** (Already implemented)
   - ✅ Checkpoint validation before caching
   - ✅ Backup validation to reject 0-node backups
   - ✅ Metadata consistency checks

2. **Monitoring** (Recommended)
   - Set up GitHub Actions notifications for workflow failures
   - Monitor checkpoint growth trends
   - Alert on validation failures

3. **Regular Audits** (Recommended)
   - Weekly validation runs
   - Monthly full validation
   - Checkpoint integrity checks

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Reset Pipeline | 5 minutes | ⏳ Ready to execute |
| Phase 2: Trigger Collection | 1 minute | ⏳ Waiting |
| Phase 3: Monitor First Run | 1-2 hours | ⏳ Waiting |
| Phase 4: Verify Schedule | 24 hours | ⏳ Waiting |

**Total Time to Resolution:** ~24-48 hours (mostly automated)

## Execution Checklist

- [ ] Review this plan
- [ ] Confirm Option B (Start Fresh) is acceptable
- [ ] Set BACKUP_PAT environment variable
- [ ] Run `scripts/reset_freesound_pipeline.sh`
- [ ] Verify all checkpoints deleted
- [ ] Trigger manual collection workflow
- [ ] Monitor first collection run
- [ ] Verify validation passes
- [ ] Verify backup uploads
- [ ] Wait for nightly scheduled run
- [ ] Confirm pipeline is healthy
- [ ] Document lessons learned
- [ ] Update runbooks if needed

## Test Results

**Test Run (2025-11-18 06:18 UTC):**
- ✅ Collection workflow: Succeeded with 1 API request
- ❌ Validation workflow: Failed (still using corrupted cached checkpoint)
- ❌ Backup workflow: Skipped (validation failed)

**Conclusion:** The corrupted checkpoint in cache/backup is blocking all progress. Fresh start is REQUIRED.

## Decision Required

**Please confirm:**
- [ ] Proceed with Option B (Start Fresh) - RECOMMENDED ⭐
- [ ] Proceed with Option A (Fix Existing) - Complex, requires more work
- [ ] Other approach (please specify)

## Notes

- Scripts are ready and tested
- All validation checks are in place
- Pipeline is designed to handle fresh starts
- Data will rebuild automatically
- No code changes required

## Questions?

If you have concerns about:
- Data loss: Pipeline will rebuild, data is from public API
- Time: Automated process, minimal manual intervention
- Risk: Clean start is lowest risk approach
- Alternative: Option A is available but complex

---

**Status:** Ready for execution
**Last Updated:** 2025-11-18
**Author:** Kiro AI Assistant
