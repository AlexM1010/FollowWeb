# Backup System Comprehensive Report

## Executive Summary

FollowWeb implements a **triple-redundant backup system** with tiered retention policies across multiple storage locations. This report documents all backup locations, triggers, retention policies, and cleanup mechanisms.

---

## 1. Local Backup System (Application-Level)

### Location
```
data/freesound_library/backups/
├── frequent/     # Every 25 nodes
├── moderate/     # Every 100 nodes
├── milestone/    # Every 500 nodes
└── daily/        # One per day (future)
```

### Backup Triggers
| Trigger Type | Condition | Tier |
|--------------|-----------|------|
| **Frequent** | Every 25 nodes | `frequent` |
| **Moderate** | Every 100 nodes (4x interval) | `moderate` |
| **Milestone** | Every 500 nodes (20x interval) | `milestone` |
| **Daily** | Once per day (future) | `daily` |

### Retention Policies

#### Frequent Tier
- **Retention Period**: 14 days (rolling window)
- **Max Count**: 5 backups
- **Cleanup Trigger**: After each backup creation
- **Removal Logic**: 
  - Delete backups older than 14 days
  - Keep only last 5 backups
  - Always keep 3 most recent regardless of policy

#### Moderate Tier
- **Retention Period**: Permanent (no expiration)
- **Max Count**: 10 backups
- **Cleanup Trigger**: After each backup creation
- **Removal Logic**: 
  - No time-based deletion
  - Keep only last 10 backups
  - Always keep 3 most recent regardless of policy

#### Milestone Tier
- **Retention Period**: Permanent (no expiration)
- **Max Count**: Unlimited (-1)
- **Cleanup Trigger**: Never deleted
- **Removal Logic**: Milestone backups are never removed

#### Daily Tier (Future)
- **Retention Period**: 30 days
- **Max Count**: 30 backups
- **Cleanup Trigger**: After each backup creation
- **Removal Logic**: Delete backups older than 30 days

### Compression
- **Trigger**: Backups older than 7 days
- **Method**: gzip compression
- **Space Savings**: ~70%
- **Automatic**: Yes, runs after backup creation

### Implementation
- **File**: `FollowWeb/FollowWeb_Visualizor/data/backup_manager.py`
- **Class**: `BackupManager`
- **Manifest**: `data/freesound_library/backup_manifest.json`

---

## 2. Primary Remote Backup (GitHub Private Repository)

### Location
- **Repository**: `{owner}/freesound-backup` (private)
- **Storage**: GitHub Release Assets
- **Access**: Via `BACKUP_PAT` secret

### Backup Triggers
| Trigger | Condition | Release Tag |
|---------|-----------|-------------|
| **Frequent** | Every 25 nodes | `v-checkpoint` |
| **Moderate** | Every 100 nodes | `v-permanent` |
| **Milestone** | Every 500 nodes | `v-permanent` |
| **Recovery** | Pipeline failure | `v-checkpoint` |

### Retention Policies

#### v-checkpoint Release (Frequent Tier)
- **Retention Period**: 14 days
- **Max Count**: 10 backups
- **Cleanup Trigger**: After successful pipeline run
- **Removal Logic**:
  - Delete assets older than 14 days
  - Enforce max count of 10 backups
  - Delete oldest first when exceeding limit

#### v-permanent Release (Moderate & Milestone)
- **Retention Period**: Permanent (no expiration)
- **Max Count**: Unlimited
- **Cleanup Trigger**: Never
- **Removal Logic**: No automatic deletion

### Cleanup Implementation
- **Workflow Step**: "Cleanup old backups (retention policy)"
- **File**: `.github/workflows/freesound-nightly-pipeline.yml` (lines 966-1062)
- **Trigger**: After successful pipeline execution
- **Method**: GitHub API DELETE requests

---

## 3. Secondary Remote Backup (Disaster Recovery)

### Location
- **Repository**: `{owner}/freesound-backup-secondary` (private)
- **Storage**: GitHub Release Assets
- **Access**: Via `BACKUP_PAT_SECONDARY` secret

### Backup Triggers
| Trigger | Frequency | Release Tag |
|---------|-----------|-------------|
| **Every Run** | Daily (nightly pipeline) | `v-daily` |
| **On Failure** | Pipeline failure | `v-daily` |

### Retention Policy
- **Retention Period**: 7 days (rolling window)
- **Max Count**: No limit (time-based only)
- **Cleanup Trigger**: After each backup upload
- **Removal Logic**: Delete assets older than 7 days

### Cleanup Implementation
- **Workflow Step**: "Cleanup secondary backup repository (7-day retention)"
- **File**: `.github/workflows/freesound-nightly-pipeline.yml` (lines 900-954)
- **Trigger**: After successful secondary backup upload
- **Method**: GitHub API DELETE requests with 7-day cutoff

---

## 4. Workflow Artifacts (GitHub Actions)

### Location
- **Storage**: GitHub Actions Artifacts
- **Access**: Workflow run page

### Artifact Types

#### Checkpoint Backups
- **Name**: `checkpoint-backup-{execution_id}`
- **Contents**: 
  - `*.gpickle` (graph topology)
  - `*.db` (metadata cache)
  - `*.json` (checkpoint metadata)
- **Retention**: 7 days
- **Trigger**: Every pipeline run (success or failure)
- **Removal**: Automatic by GitHub after 7 days

#### Pipeline Logs
- **Name**: `pipeline-logs-{execution_id}`
- **Contents**:
  - `pipeline_*.log`
  - `validation.log`
  - `edge_generation.log`
  - `website.log`
  - `*.json` (status files)
- **Retention**: 30 days
- **Trigger**: Every pipeline run (always)
- **Removal**: Automatic by GitHub after 30 days

### Implementation
- **File**: `.github/workflows/freesound-nightly-pipeline.yml`
- **Checkpoint Step**: Line 955-965
- **Logs Step**: Line 1267-1284

---

## 5. CI/CD Workflow Artifacts

### Location
- **Storage**: GitHub Actions Artifacts
- **Workflow**: `.github/workflows/ci.yml`

### Artifact Types

#### Test Coverage Reports
- **Name**: `coverage-report`
- **Contents**: `coverage.xml`, `htmlcov/`
- **Retention**: 30 days
- **Trigger**: After test execution
- **Removal**: Automatic by GitHub

#### Security Reports
- **Name**: `security-reports`
- **Contents**: `bandit-report.json`, `pip-audit-report.json`
- **Retention**: 7 days
- **Trigger**: After security scan
- **Removal**: Automatic by GitHub

#### Package Distributions
- **Name**: `python-package-distributions`
- **Contents**: `dist/*.whl`, `dist/*.tar.gz`
- **Retention**: 30 days
- **Trigger**: After package build
- **Removal**: Automatic by GitHub

#### Benchmark Results
- **Name**: `benchmark-results`
- **Contents**: `.benchmarks/`
- **Retention**: 30 days
- **Trigger**: After performance tests
- **Removal**: Automatic by GitHub

### Implementation
- **File**: `.github/workflows/ci.yml`
- **Lines**: 483, 611, 783, 962

---

## 6. Documentation Workflow Artifacts

### Location
- **Storage**: GitHub Actions Artifacts
- **Workflow**: `.github/workflows/docs.yml`

### Artifact Types

#### Documentation Quality Reports
- **Name**: `documentation-quality-reports`
- **Contents**: `todo_comments.txt`, `broken_links.txt`
- **Retention**: 30 days
- **Trigger**: After documentation checks
- **Removal**: Automatic by GitHub

#### Docstring Coverage
- **Name**: `docstring-coverage`
- **Contents**: `interrogate_output.txt`
- **Retention**: 30 days
- **Trigger**: After docstring analysis
- **Removal**: Automatic by GitHub

### Implementation
- **File**: `.github/workflows/docs.yml`
- **Lines**: 244, 332

---

## 7. Validation Workflow Artifacts

### Location
- **Storage**: GitHub Actions Artifacts
- **Workflows**: 
  - `.github/workflows/freesound-full-validation.yml`
  - `.github/workflows/freesound-quick-validation.yml`

### Artifact Types

#### Validation Reports (Full)
- **Name**: `validation-report-{execution_id}`
- **Contents**: `logs/validation_*.json`
- **Retention**: 90 days
- **Trigger**: After full validation
- **Removal**: Automatic by GitHub

#### Validation Logs (Full)
- **Name**: `validation-logs-{execution_id}`
- **Contents**: `validation_*.log`, `logs/validation_*.log`
- **Retention**: 90 days
- **Trigger**: After full validation
- **Removal**: Automatic by GitHub

#### Validation Reports (Quick)
- **Name**: `validation-report-{execution_id}`
- **Contents**: `logs/validation_*.json`
- **Retention**: 30 days
- **Trigger**: After quick validation
- **Removal**: Automatic by GitHub

#### Validation Logs (Quick)
- **Name**: `validation-logs-{execution_id}`
- **Contents**: `validation_*.log`
- **Retention**: 30 days
- **Trigger**: After quick validation
- **Removal**: Automatic by GitHub

#### Checkpoint Snapshots
- **Name**: `checkpoint-snapshot-{execution_id}`
- **Contents**: `data/freesound_library/*.pkl`
- **Retention**: 7 days
- **Trigger**: After validation
- **Removal**: Automatic by GitHub

### Implementation
- **Full Validation**: Lines 252, 421, 431
- **Quick Validation**: Lines 278, 437, 447

---

## 8. Metrics Dashboard Artifacts

### Location
- **Storage**: GitHub Actions Artifacts
- **Workflow**: `.github/workflows/freesound-metrics-dashboard.yml`

### Artifact Types

#### Metrics Dashboard
- **Name**: `metrics-dashboard`
- **Contents**: `Output/metrics_dashboard.png`
- **Retention**: 90 days
- **Trigger**: After dashboard generation
- **Removal**: Automatic by GitHub

### Implementation
- **File**: `.github/workflows/freesound-metrics-dashboard.yml`
- **Line**: 91

---

## 9. Release Artifacts

### Location
- **Storage**: GitHub Actions Artifacts
- **Workflow**: `.github/workflows/release.yml`

### Artifact Types

#### Package Distributions
- **Name**: `python-package-distributions`
- **Contents**: `FollowWeb/dist/*`
- **Retention**: 90 days
- **Trigger**: After release build
- **Removal**: Automatic by GitHub

### Implementation
- **File**: `.github/workflows/release.yml`
- **Line**: 120

---

## 10. Ephemeral Cache (Workflow-Level)

### Location
- **Path**: `data/freesound_library/` (in workflow runner)
- **Lifecycle**: Single workflow run only

### Behavior
- **Created**: Downloaded from primary backup at workflow start
- **Used**: During pipeline execution
- **Destroyed**: Wiped at workflow end (always)
- **Purpose**: TOS compliance (never in public Git)

### Cleanup Implementation
- **Workflow Step**: "Cleanup ephemeral cache"
- **File**: `.github/workflows/freesound-nightly-pipeline.yml` (lines 1157-1171)
- **Trigger**: Always (success or failure)
- **Method**: `rm -rf data/freesound_library`

---

## Summary Table: All Backup Locations

| Location | Trigger | Retention | Max Lifespan | Cleanup Method |
|----------|---------|-----------|--------------|----------------|
| **Local Frequent** | Every 25 nodes | 14 days + 5 count | 14 days | Automatic after backup |
| **Local Moderate** | Every 100 nodes | Permanent + 10 count | Unlimited | Count-based only |
| **Local Milestone** | Every 500 nodes | Permanent + unlimited | Unlimited | Never deleted |
| **Primary Frequent** | Every 25 nodes | 14 days + 10 count | 14 days | Workflow step |
| **Primary Permanent** | Every 100/500 nodes | Permanent | Unlimited | Never deleted |
| **Secondary** | Every run | 7 days | 7 days | Workflow step |
| **Workflow Checkpoints** | Every run | 7 days | 7 days | GitHub automatic |
| **Workflow Logs** | Every run | 30 days | 30 days | GitHub automatic |
| **CI Coverage** | After tests | 30 days | 30 days | GitHub automatic |
| **CI Security** | After scan | 7 days | 7 days | GitHub automatic |
| **CI Packages** | After build | 30 days | 30 days | GitHub automatic |
| **CI Benchmarks** | After tests | 30 days | 30 days | GitHub automatic |
| **Docs Quality** | After checks | 30 days | 30 days | GitHub automatic |
| **Validation Full** | After validation | 90 days | 90 days | GitHub automatic |
| **Validation Quick** | After validation | 30 days | 30 days | GitHub automatic |
| **Metrics Dashboard** | After generation | 90 days | 90 days | GitHub automatic |
| **Release Packages** | After release | 90 days | 90 days | GitHub automatic |
| **Ephemeral Cache** | Every run | 0 days | Single run | Workflow step |

---

## Backup Removal Triggers

### Automatic Triggers
1. **After backup creation** (local backups)
   - Runs cleanup immediately
   - Applies tier-specific retention
   - Compresses old backups

2. **After successful pipeline** (remote backups)
   - Cleans primary repository
   - Cleans secondary repository
   - Enforces time and count limits

3. **After artifact upload** (GitHub artifacts)
   - GitHub automatically removes after retention period
   - No manual intervention needed

4. **At workflow end** (ephemeral cache)
   - Always runs (success or failure)
   - Complete directory removal

### Manual Triggers
- **None** - All cleanup is automatic

---

## Safety Mechanisms

### Protection Rules
1. **Always keep 3 most recent** (local backups)
   - Overrides all retention policies
   - Prevents accidental data loss

2. **Milestone protection** (local & remote)
   - Never automatically deleted
   - Permanent archival

3. **Permanent tier protection** (remote)
   - No time-based deletion
   - Only count-based for moderate tier

4. **Failure recovery** (remote)
   - Backups created on pipeline failure
   - Preserves partial progress

### Verification
- **Backup integrity check** (remote)
  - Verifies upload state
  - Checks file size (>1KB)
  - Runs after each upload

---

## Configuration Files

### Application-Level
- **File**: `generate_freesound_visualization.py`
- **Settings**:
  ```python
  'backup_interval_nodes': 25
  'backup_retention_count': 10
  'backup_compression': True
  'tiered_backups': True
  'compression_age_days': 7
  ```

### Workflow-Level
- **File**: `.github/workflows/freesound-nightly-pipeline.yml`
- **Settings**: Hardcoded in workflow steps
- **Secrets**: `BACKUP_PAT`, `BACKUP_PAT_SECONDARY`

### Test Configuration
- **File**: `FollowWeb/pytest.ini`
- **Setting**: `tmp_path_retention_count = 3`
- **Purpose**: Test temporary directory retention

---

## Monitoring & Auditing

### Local Backups
- **Manifest**: `data/freesound_library/backup_manifest.json`
- **Contents**: All backup metadata, timestamps, sizes
- **Updated**: After each backup operation

### Remote Backups
- **Workflow Summary**: GitHub Actions step summary
- **Contents**: Backup status, sizes, retention info
- **Location**: Workflow run page

### Logs
- **Pipeline Logs**: 30-day retention
- **Validation Logs**: 30-90 day retention
- **Location**: Workflow artifacts

---

## Recommendations

### Current State
✅ Triple-redundant backup system
✅ Tiered retention policies
✅ Automatic cleanup
✅ Compression enabled
✅ Safety mechanisms in place

### Potential Improvements
1. **Monitoring Dashboard**: Centralized backup status view
2. **Backup Verification**: Periodic restore testing
3. **Metrics Collection**: Track backup sizes and cleanup frequency
4. **Alert System**: Notify on backup failures
5. **Remote Storage**: Consider S3/GCS for long-term archival

---

## Related Documentation

- **User Guide**: `BACKUP_SYSTEM_GUIDE.md`
- **Implementation**: `BACKUP_IMPLEMENTATION_SUMMARY.md`
- **Quick Reference**: `BACKUP_QUICK_REFERENCE.md`
- **Files Manifest**: `BACKUP_FILES_MANIFEST.md`
- **Pipeline Guide**: `Docs/FREESOUND_PIPELINE.md`

---

**Report Generated**: 2025-11-13
**System Version**: FollowWeb with Freesound Pipeline
**Backup System**: Triple-Redundant with Tiered Retention
