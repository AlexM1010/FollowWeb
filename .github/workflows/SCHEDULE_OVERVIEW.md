# GitHub Actions Workflow Schedule Overview

This document provides a comprehensive view of all scheduled workflows to prevent conflicts and optimize resource usage.

## Schedule Timeline (UTC)

```
Time    | Mon | Tue | Wed | Thu | Fri | Sat | Sun | Workflow
--------|-----|-----|-----|-----|-----|-----|-----|---------------------------
2:00 AM |  🔵 |  🔵 |  🔵 |  🔵 |  🔵 |  🟢 |     | Freesound Nightly (Mon-Sat)
2:00 AM |     |     |     |     |     |  🟡 |     | CI (Saturday only)
2:00 AM |  🟠 |  🟠 |  🟠 |  🟠 |  🟠 |  🟠 |  🟠 | Nightly Security (Daily)
3:00 AM |     |     |     |     |     |     |  🟣 | Quick Validation (Sunday)
4:00 AM | 1st |     |     |     |     |     |     | Full Validation (Monthly)
5:00 AM |     |     |     |     |     |     |  🔴 | Metrics Dashboard (Sunday)
6:00 AM |     |     |     |     |     |     |  ⚫ | Backup Maintenance (Sunday)
```

**Legend:**
- 🔵 Freesound Nightly Pipeline
- 🟢 CI (Weekly)
- 🟡 CI (Scheduled run)
- 🟠 Nightly Security Check
- 🟣 Quick Validation
- 🔴 Metrics Dashboard
- ⚫ Backup Maintenance

## Workflow Details

### 1. CI Pipeline (`ci.yml`)
**Schedule:** `0 2 * * 6` (Saturday 2 AM UTC)
**Duration:** ~30 minutes
**Purpose:** Weekly comprehensive testing across all OS/Python combinations
**Concurrency:** Cancel in-progress runs
**Resource Usage:** High (matrix: 3 OS × 4 Python versions)

**Conflicts:** None (moved from Sunday to Saturday to avoid collision)

---

### 2. Nightly Security Check (`nightly.yml`)
**Schedule:** `0 2 * * *` (Daily 2 AM UTC)
**Duration:** ~15 minutes
**Purpose:** Daily dependency and security scanning
**Concurrency:** Not specified
**Resource Usage:** Low (single job, ubuntu-latest)

**Conflicts:** 
- Runs same time as Freesound Nightly (Mon-Sat)
- Runs same time as CI (Saturday)
- **Impact:** Minimal - different resource profiles

---

### 3. Freesound Nightly Pipeline (`freesound-nightly-pipeline.yml`)
**Schedule:** `0 2 * * 1-6` (Monday-Saturday 2 AM UTC)
**Duration:** ~120 minutes (2 hours)
**Purpose:** Daily Freesound data collection and visualization
**Concurrency:** No cancel (let complete)
**Resource Usage:** High (API calls, data processing)

**Conflicts:**
- Runs same time as Nightly Security (Mon-Sat)
- Runs same time as CI (Saturday)
- **Impact:** Moderate - uses different resources (API vs compute)
- **Mitigation:** Workflow orchestration with conflict detection

---

### 4. Quick Validation (`freesound-quick-validation.yml`)
**Schedule:** `0 3 * * 0` (Sunday 3 AM UTC)
**Duration:** ~30 minutes
**Purpose:** Weekly validation of 300 oldest samples
**Concurrency:** No cancel (let complete)
**Resource Usage:** Low (2 API requests)

**Conflicts:** None
**Special Logic:** Skips if Full Validation ran same day

---

### 5. Full Validation (`freesound-full-validation.yml`)
**Schedule:** `0 4 1 * *` (1st of month, 4 AM UTC)
**Duration:** ~180 minutes (3 hours)
**Purpose:** Monthly validation of all samples
**Concurrency:** No cancel (let complete)
**Resource Usage:** Moderate (~27 API requests for 4000 samples)

**Conflicts:** None

---

### 6. Metrics Dashboard (`freesound-metrics-dashboard.yml`)
**Schedule:** `0 5 * * 0` (Sunday 5 AM UTC)
**Duration:** ~15 minutes
**Purpose:** Weekly metrics dashboard generation
**Concurrency:** Not specified
**Resource Usage:** Low (data aggregation)

**Conflicts:** None

---

### 7. Backup Maintenance (`freesound-backup-maintenance.yml`)
**Schedule:** `0 6 * * 0` (Sunday 6 AM UTC)
**Duration:** ~10 minutes
**Purpose:** Weekly backup cleanup and maintenance
**Concurrency:** Not specified
**Resource Usage:** Low (API calls to private repo)

**Conflicts:** None

---

## Conflict Resolution Strategy

### Workflow Orchestration
All Freesound workflows use `WorkflowOrchestrator` to detect and wait for conflicts:
- 2-hour timeout for conflict resolution
- Automatic skip if conflicts persist
- Comprehensive logging

### Concurrency Groups
```yaml
# Freesound workflows
concurrency:
  group: freesound-pipeline  # or workflow-specific group
  cancel-in-progress: false  # Let validation/data collection complete

# CI workflow
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true  # Cancel old runs on new commits
```

### Schedule Staggering
- **2 AM:** High-frequency workflows (daily/weekly)
- **3 AM:** Validation workflows
- **4 AM:** Monthly maintenance
- **5-6 AM:** Reporting and cleanup

## Resource Usage Patterns

### Peak Times
- **Saturday 2 AM:** CI + Nightly Security (both lightweight)
- **Monday-Saturday 2 AM:** Freesound Nightly + Nightly Security
- **Sunday 2 AM:** Only Nightly Security (lightest day)

### API Budget Management
**Freesound API:** 2000 requests/day

| Workflow | Frequency | Requests/Run | Daily Budget |
|----------|-----------|--------------|--------------|
| Nightly Pipeline | Daily (Mon-Sat) | ~1950 | 1950 |
| Quick Validation | Weekly (Sun) | ~2 | 2 |
| Full Validation | Monthly | ~27 | ~1 (amortized) |
| **Total Daily** | - | - | **~1950** |

**Buffer:** 50 requests/day for manual runs and retries

### GitHub Actions Minutes
Estimated monthly usage (assuming 30-day month):

| Workflow | Runs/Month | Duration | Minutes/Month |
|----------|------------|----------|---------------|
| CI | 4-5 | 30 min × 12 jobs | 1440-1800 |
| Nightly Security | 30 | 15 min | 450 |
| Freesound Nightly | 26 | 120 min | 3120 |
| Quick Validation | 4 | 30 min | 120 |
| Full Validation | 1 | 180 min | 180 |
| Metrics Dashboard | 4 | 15 min | 60 |
| Backup Maintenance | 4 | 10 min | 40 |
| **Total** | - | - | **~5410-5770** |

**Note:** Free tier includes 2000 minutes/month for private repos, 3000 for Pro accounts

## Optimization Opportunities

### Immediate
- ✅ Schedule collision fixed (CI moved to Saturday)
- ✅ Artifact naming fixed (unique names per matrix job)
- ✅ Secret validation added (fail fast)

### Short-term
- [ ] Add workflow duration tracking to detect performance regressions
- [ ] Implement API quota monitoring with alerts
- [ ] Add failure notifications (Slack/email)

### Long-term
- [ ] Consider reusable workflows to reduce duplication
- [ ] Implement smart scheduling based on historical patterns
- [ ] Add cost monitoring dashboard

## Manual Trigger Guidelines

All workflows support `workflow_dispatch` for manual triggering:

```bash
# Trigger via GitHub CLI
gh workflow run ci.yml
gh workflow run freesound-nightly-pipeline.yml --field seed_sample_id=12345

# Trigger via GitHub UI
# Actions tab → Select workflow → Run workflow button
```

**Best Practices:**
- Check for running workflows before manual trigger
- Use workflow orchestration to avoid conflicts
- Monitor API budget before triggering Freesound workflows

## Monitoring and Alerts

### Health Checks
Use the workflow health check script:
```bash
# Generate health report for last 30 days
python .github/scripts/workflow_health_check.py --days 30 --output health_report.md

# Check specific workflow
python .github/scripts/workflow_health_check.py --workflow "CI" --days 7
```

### Key Metrics to Monitor
- Success rate per workflow (target: >95%)
- Average duration (detect regressions)
- Failure patterns (time of day, specific jobs)
- API quota usage (Freesound)
- GitHub Actions minutes usage

## Emergency Procedures

### Workflow Stuck/Hanging
1. Check workflow run page for status
2. Cancel run if necessary (Actions tab → Cancel workflow)
3. Check for resource contention or API issues
4. Review logs for timeout or deadlock

### API Quota Exceeded
1. Check Freesound API dashboard
2. Pause nightly pipeline if needed
3. Wait for quota reset (daily at midnight UTC)
4. Adjust `max_requests` parameter if needed

### Multiple Workflow Failures
1. Check GitHub Status page
2. Review recent commits for breaking changes
3. Check dependency updates (nightly workflow)
4. Run health check script for patterns

## Change Log

### 2024-11-12
- Fixed schedule collision: CI moved from Sunday to Saturday
- Added secret validation to all Freesound workflows
- Improved git push error handling with retry logic
- Created comprehensive documentation

### Future Updates
- Document any schedule changes here
- Note new workflows or removed workflows
- Track optimization implementations
