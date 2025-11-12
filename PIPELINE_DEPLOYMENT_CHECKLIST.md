# Pipeline Improvements Deployment Checklist

## Pre-Deployment Verification

### 1. Review Changes
- [ ] Review all modified workflow files
- [ ] Verify schedule changes are correct
- [ ] Check artifact naming includes matrix variables
- [ ] Confirm secret validation logic is sound
- [ ] Validate git error handling syntax

### 2. Documentation Review
- [ ] Read `PIPELINE_FIXES.md`
- [ ] Review `SCHEDULE_OVERVIEW.md`
- [ ] Check `REQUIREMENTS_GUIDE.md`
- [ ] Understand `PIPELINE_IMPROVEMENTS_SUMMARY.md`

### 3. Secret Configuration
- [ ] Verify `FREESOUND_API_KEY` is configured in repository secrets
- [ ] Verify `BACKUP_PAT` is configured (optional but recommended)
- [ ] Test secret access permissions

## Deployment Steps

### 1. Commit Changes
```bash
# Stage workflow changes
git add .github/workflows/ci.yml
git add .github/workflows/freesound-nightly-pipeline.yml
git add .github/workflows/freesound-full-validation.yml
git add .github/workflows/freesound-quick-validation.yml

# Stage new files
git add .github/scripts/workflow_health_check.py
git add .github/workflows/SCHEDULE_OVERVIEW.md
git add .github/workflows/QUICK_REFERENCE.md
git add FollowWeb/REQUIREMENTS_GUIDE.md
git add PIPELINE_FIXES.md
git add PIPELINE_IMPROVEMENTS_SUMMARY.md
git add PIPELINE_DEPLOYMENT_CHECKLIST.md

# Commit
git commit -m "Fix pipeline issues: schedule collision, artifact naming, secret validation"
```

### 2. Push to Feature Branch
```bash
git push origin feature/pipeline-fixes
```

### 3. Create Pull Request
- [ ] Create PR with detailed description
- [ ] Link to pipeline review document
- [ ] Request review from team lead
- [ ] Add labels: `infrastructure`, `ci/cd`, `high-priority`

## Post-Deployment Monitoring

### Week 1: Intensive Monitoring

#### Daily Checks
- [ ] Check workflow runs in Actions tab
- [ ] Verify no schedule collisions occurred
- [ ] Confirm all artifacts are uploaded with unique names
- [ ] Check for secret validation errors
- [ ] Monitor git push operations

#### Run Health Check
```bash
python .github/scripts/workflow_health_check.py --days 7 --output week1_health.md
```

#### Key Metrics
- Success rate per workflow (target: >95%)
- Average duration (should be stable)
- Artifact upload success rate (target: 100%)
- Secret validation pass rate (target: 100%)

### Week 2-4: Regular Monitoring

#### Weekly Checks
- [ ] Run health check script
- [ ] Review workflow failure patterns
- [ ] Check API quota usage (Freesound)
- [ ] Verify backup retention policy

#### Monthly Review
- [ ] Generate comprehensive health report
- [ ] Review schedule effectiveness
- [ ] Assess resource usage
- [ ] Plan optimizations

## Rollback Procedure

If critical issues arise:

### 1. Immediate Rollback
```bash
# Revert the commit
git revert <commit-hash>
git push origin main

# Or reset to previous state
git reset --hard <previous-commit>
git push --force origin main
```

### 2. Partial Rollback

#### Revert Schedule Change Only
```yaml
# In .github/workflows/ci.yml
schedule:
  - cron: '0 2 * * 0'  # Back to Sunday
```

#### Revert Artifact Naming Only
```yaml
# In .github/workflows/ci.yml
name: coverage-reports  # Remove matrix variables
name: security-reports
```

### 3. Notify Team
- [ ] Post in team chat
- [ ] Update PR with rollback reason
- [ ] Document issues encountered
- [ ] Plan remediation

## Success Criteria

### Immediate (First Run)
- [ ] CI runs on Saturday without collision
- [ ] All artifacts uploaded with unique names
- [ ] Secret validation catches missing secrets
- [ ] No git push failures

### Short-term (1-2 Weeks)
- [ ] Zero schedule-related failures
- [ ] 100% artifact preservation rate
- [ ] All secret issues caught early
- [ ] Git retry handles conflicts successfully

### Long-term (1 Month)
- [ ] Workflow success rate >95%
- [ ] Average duration stable or improved
- [ ] Zero manual interventions needed
- [ ] Team comfortable with new documentation

## Troubleshooting Guide

### Issue: Workflow Still Colliding
**Symptoms:** Multiple workflows running simultaneously
**Check:**
1. Verify schedule in workflow file
2. Check workflow orchestration logs
3. Review concurrency settings

**Fix:**
- Adjust schedule times
- Update concurrency groups
- Increase orchestration timeout

### Issue: Artifacts Not Found
**Symptoms:** Artifact download fails in dependent jobs
**Check:**
1. Verify artifact name matches upload name
2. Check if matrix variables are resolved
3. Review artifact retention settings

**Fix:**
- Update artifact names to match
- Ensure matrix variables are available
- Check artifact expiration

### Issue: Secret Validation Failing
**Symptoms:** Workflow fails at secret validation step
**Check:**
1. Verify secret exists in repository settings
2. Check secret name spelling
3. Confirm secret has correct permissions

**Fix:**
- Add missing secret
- Correct secret name
- Update secret permissions

### Issue: Git Push Retry Failing
**Symptoms:** Push fails even after retry
**Check:**
1. Review git logs for conflict details
2. Check if multiple workflows pushing simultaneously
3. Verify git configuration

**Fix:**
- Manually resolve conflicts
- Adjust workflow schedules
- Update concurrency settings

## Communication Plan

### Before Deployment
- [ ] Notify team of upcoming changes
- [ ] Share documentation links
- [ ] Schedule deployment window
- [ ] Assign monitoring responsibilities

### During Deployment
- [ ] Post deployment start notification
- [ ] Monitor first workflow runs
- [ ] Be available for questions
- [ ] Document any issues

### After Deployment
- [ ] Post success notification
- [ ] Share health check results
- [ ] Collect team feedback
- [ ] Update documentation based on feedback

## Additional Resources

### Documentation
- Pipeline Fixes: `PIPELINE_FIXES.md`
- Schedule Overview: `.github/workflows/SCHEDULE_OVERVIEW.md`
- Requirements Guide: `FollowWeb/REQUIREMENTS_GUIDE.md`
- Quick Reference: `.github/workflows/QUICK_REFERENCE.md`

### Scripts
- Health Check: `.github/scripts/workflow_health_check.py`
- CI Helpers: `.github/scripts/ci_helpers.py`
- Workflow Orchestrator: `workflow_orchestrator.py`

### GitHub Resources
- Actions Documentation: https://docs.github.com/en/actions
- Workflow Syntax: https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions
- Secrets Management: https://docs.github.com/en/actions/security-guides/encrypted-secrets

## Sign-off

### Prepared By
- Name: _______________
- Date: _______________
- Role: _______________

### Reviewed By
- Name: _______________
- Date: _______________
- Role: _______________

### Approved By
- Name: _______________
- Date: _______________
- Role: _______________

### Deployed By
- Name: _______________
- Date: _______________
- Deployment Time: _______________
- Commit Hash: _______________

---

**Note:** Keep this checklist updated as you progress through deployment and monitoring phases.
