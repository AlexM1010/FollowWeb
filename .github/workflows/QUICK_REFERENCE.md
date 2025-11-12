# Workflow Quick Reference

## Schedule at a Glance

| Time | Day     | Workflow           | Duration |
|------|---------|--------------------|----------|
| 2 AM | Sat     | CI                 | 30 min   |
| 2 AM | Daily   | Nightly Security   | 15 min   |
| 2 AM | Mon-Sat | Freesound Nightly  | 120 min  |
| 3 AM | Sun     | Quick Validation   | 30 min   |
| 4 AM | 1st     | Full Validation    | 180 min  |
| 5 AM | Sun     | Metrics Dashboard  | 15 min   |
| 6 AM | Sun     | Backup Maintenance | 10 min   |

## Common Commands

### Trigger Workflows
```bash
gh workflow run ci.yml
gh workflow run freesound-nightly-pipeline.yml
```

### Check Workflow Status
```bash
gh run list --workflow=ci.yml --limit 5
gh run view <run-id>
```

### Health Check
```bash
python .github/scripts/workflow_health_check.py --days 7
```

## Troubleshooting

### Workflow Failed
1. Check logs in Actions tab
2. Look for secret validation errors
3. Check API quota (Freesound)
4. Review recent commits

### Secret Issues
- FREESOUND_API_KEY: Required for Freesound workflows
- BACKUP_PAT: Optional, for checkpoint backups

### Git Push Failed
- Automatic retry with rebase
- Check for conflicts in logs
- Manual intervention if retry fails

## Documentation

- Full schedule: `SCHEDULE_OVERVIEW.md`
- All fixes: `PIPELINE_FIXES.md`
- Requirements: `FollowWeb/REQUIREMENTS_GUIDE.md`
- Summary: `PIPELINE_IMPROVEMENTS_SUMMARY.md`
