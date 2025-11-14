# Backup Failure Policy

## Critical Change: Fail-Fast on Backup Failures

**Date:** November 14, 2025  
**Status:** ✅ Implemented

## Overview

The Freesound Nightly Pipeline now implements a **fail-fast policy** for backup failures. This ensures data integrity and prevents data loss by halting the entire pipeline if any backup operation fails.

## Policy Details

### Primary Backup (REQUIRED)

- **Secret:** `BACKUP_PAT`
- **Repository:** `AlexM1010/freesound-backup`
- **Status:** **REQUIRED** - Pipeline will fail if not configured
- **Behavior:** Pipeline fails immediately if:
  - `BACKUP_PAT` is not configured
  - Backup repository releases (`v-checkpoint`, `v-permanent`) don't exist
  - Checkpoint directory is missing
  - Upload to backup repository fails
  - Backup verification fails

### Secondary Backup (OPTIONAL)

- **Secret:** `BACKUP_PAT_SECONDARY`
- **Repository:** `AlexM1010/freesound-backup-secondary`
- **Status:** Optional - Pipeline continues if not configured
- **Behavior:** Warnings only, does not fail pipeline

### Workflow Artifacts (AUTOMATIC)

- **Retention:** 7 days
- **Status:** Automatic - Always uploaded
- **Behavior:** Does not affect pipeline success/failure

## Changes Made

### 1. Smoke Test Validation

**Before:**
```yaml
# Check BACKUP_PAT (optional)
if [ -z "$BACKUP_PAT" ]; then
  echo "::warning::BACKUP_PAT not configured"
```

**After:**
```yaml
# Check BACKUP_PAT (required)
if [ -z "$BACKUP_PAT" ]; then
  echo "::error::BACKUP_PAT not configured - backups are REQUIRED"
  exit 1
```

### 2. Pipeline Secrets Validation

**Before:**
```yaml
# Check BACKUP_PAT (optional but recommended)
if [ -z "$BACKUP_PAT" ]; then
  echo "::warning::BACKUP_PAT not configured - primary checkpoint backups will be skipped"
  exit 0
```

**After:**
```yaml
# Check BACKUP_PAT (required)
if [ -z "$BACKUP_PAT" ]; then
  echo "::error::BACKUP_PAT not configured - backups are REQUIRED"
  exit 1
```

### 3. Checkpoint Download

**Before:**
```yaml
if [ -z "$BACKUP_PAT" ]; then
  echo " BACKUP_PAT not configured, starting with empty checkpoint"
  exit 0
```

**After:**
```yaml
if [ -z "$BACKUP_PAT" ]; then
  echo "::error::BACKUP_PAT not configured - cannot download checkpoint"
  exit 1
```

### 4. Checkpoint Upload - Missing Directory

**Before:**
```yaml
if [ ! -d "data/freesound_library" ]; then
  echo " Checkpoint directory not found, skipping backup"
  exit 0
```

**After:**
```yaml
if [ ! -d "data/freesound_library" ]; then
  echo "::error::Checkpoint directory not found - BACKUP FAILED"
  exit 1
```

### 5. Checkpoint Upload - Missing PAT

**Before:**
```yaml
if [ -z "$BACKUP_PAT" ]; then
  echo " BACKUP_PAT not configured, skipping backup upload"
  exit 0
```

**After:**
```yaml
if [ -z "$BACKUP_PAT" ]; then
  echo "::error::BACKUP_PAT not configured - BACKUP FAILED"
  exit 1
```

### 6. Checkpoint Upload - Missing Release

**Before:**
```yaml
if [ "$RELEASE_ID" = "null" ] || [ -z "$RELEASE_ID" ]; then
  echo "::warning::Release ${release_tag} not found"
  exit 0
```

**After:**
```yaml
if [ "$RELEASE_ID" = "null" ] || [ -z "$RELEASE_ID" ]; then
  echo "::error::Release ${release_tag} not found - BACKUP FAILED"
  exit 1
```

### 7. Checkpoint Upload - Upload Failure

**Before:**
```yaml
if [ "$ASSET_ID" = "null" ] || [ -z "$ASSET_ID" ]; then
  echo "::warning::Failed to upload backup"
  exit 0
```

**After:**
```yaml
if [ "$ASSET_ID" = "null" ] || [ -z "$ASSET_ID" ]; then
  echo "::error::Failed to upload backup - BACKUP FAILED"
  exit 1
```

## Rationale

### Why Fail-Fast?

1. **Data Integrity:** Without backups, data loss is inevitable if the workflow fails
2. **No Wasted Resources:** Don't collect data if we can't save it
3. **Clear Failure Signal:** Immediate notification of backup issues
4. **Prevents Silent Failures:** No more "successful" runs that didn't actually backup
5. **Compliance:** Ensures TOS compliance by guaranteeing backup storage

### Why Not Fail-Fast Before?

The previous implementation was designed to be "resilient" by continuing even if backups failed. However, this led to:

- Silent data loss when backups failed
- Wasted API quota collecting data that couldn't be saved
- False sense of security from "successful" workflow runs
- Difficult debugging when data went missing

## Impact

### Immediate Effects

- ✅ Pipeline will fail immediately if backup configuration is missing
- ✅ Pipeline will fail immediately if backup upload fails
- ✅ Clear error messages in workflow logs
- ✅ GitHub Actions annotations for critical failures
- ✅ No wasted API quota on unbackable data

### Required Actions

Before the next pipeline run, ensure:

1. ✅ `BACKUP_PAT` secret is configured in repository settings
2. ✅ Backup repository `AlexM1010/freesound-backup` exists
3. ✅ Release tags exist in backup repository:
   - `v-checkpoint` (for frequent backups)
   - `v-permanent` (for milestone backups)

### Migration Path

If releases don't exist, create them:

```bash
# Option 1: Use the setup script (requires BACKUP_PAT in environment)
./setup_backup_releases.ps1

# Option 2: Create manually via GitHub UI
# Go to AlexM1010/freesound-backup
# Create new release with tag "v-checkpoint"
# Create new release with tag "v-permanent"

# Option 3: Use GitHub CLI
gh release create v-checkpoint --repo AlexM1010/freesound-backup --title "Checkpoint Backups" --notes "Frequent tier backups (14-day retention)"
gh release create v-permanent --repo AlexM1010/freesound-backup --title "Permanent Backups" --notes "Milestone and moderate tier backups (permanent retention)"
```

## Testing

To test the fail-fast behavior:

1. **Test missing PAT:** Remove `BACKUP_PAT` secret temporarily
   - Expected: Pipeline fails at smoke test
   
2. **Test missing release:** Delete `v-checkpoint` release temporarily
   - Expected: Pipeline fails at backup upload
   
3. **Test successful backup:** Restore configuration
   - Expected: Pipeline completes successfully with backup

## Rollback

If this policy causes issues, revert by changing all `exit 1` back to `exit 0` in the backup-related steps. However, this is **NOT RECOMMENDED** as it reintroduces the risk of silent data loss.

## Related Files

- `.github/workflows/freesound-nightly-pipeline.yml` - Main workflow file
- `setup_backup_releases.ps1` - Script to create backup releases
- `setup_backup_releases.sh` - Linux version of setup script

## Status

- ✅ Policy implemented
- ⚠️ Backup releases need to be created before next run
- ⚠️ Current pipeline runs will fail until releases are created
