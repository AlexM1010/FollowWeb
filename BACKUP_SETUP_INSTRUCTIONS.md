# Backup Setup Instructions

## Current Issue

The Freesound Nightly Pipeline is failing because the backup repository releases are not configured.

**Error:** `Release v-permanent not found in AlexM1010/freesound-backup`

## Quick Fix

You need to create two release tags in your backup repository:

### Option 1: Using PowerShell Script (Recommended)

```powershell
# Set your BACKUP_PAT environment variable
$env:BACKUP_PAT = "your_github_pat_here"

# Run the setup script
.\setup_backup_releases.ps1
```

### Option 2: Using GitHub CLI

```bash
# Create v-checkpoint release (frequent tier, 14-day retention)
gh release create v-checkpoint \
  --repo AlexM1010/freesound-backup \
  --title "Checkpoint Backups (Frequent Tier)" \
  --notes "Frequent tier backups with 14-day retention. Created every 25 nodes."

# Create v-permanent release (milestone tier, permanent retention)
gh release create v-permanent \
  --repo AlexM1010/freesound-backup \
  --title "Permanent Backups (Milestone Tier)" \
  --notes "Milestone and moderate tier backups with permanent retention. Created every 100 and 500 nodes."
```

### Option 3: Using GitHub Web UI

1. Go to https://github.com/AlexM1010/freesound-backup
2. Click "Releases" in the right sidebar
3. Click "Create a new release"
4. For the first release:
   - Tag: `v-checkpoint`
   - Title: `Checkpoint Backups (Frequent Tier)`
   - Description: `Frequent tier backups with 14-day retention. Created every 25 nodes.`
   - Click "Publish release"
5. Repeat for the second release:
   - Tag: `v-permanent`
   - Title: `Permanent Backups (Milestone Tier)`
   - Description: `Milestone and moderate tier backups with permanent retention. Created every 100 and 500 nodes.`
   - Click "Publish release"

## Verification

After creating the releases, verify they exist:

```bash
# Check releases in backup repository
gh release list --repo AlexM1010/freesound-backup

# Expected output:
# v-permanent    Permanent Backups (Milestone Tier)    Latest    ...
# v-checkpoint   Checkpoint Backups (Frequent Tier)    ...       ...
```

## Next Steps

Once the releases are created:

1. The next pipeline run will succeed
2. Backups will be uploaded to the appropriate release based on node count:
   - Every 25 nodes → `v-checkpoint` (frequent tier)
   - Every 100 nodes → `v-permanent` (moderate tier)
   - Every 500 nodes → `v-permanent` (milestone tier)

## Backup Tiers Explained

### Frequent Tier (v-checkpoint)
- **Interval:** Every 25 nodes
- **Retention:** 14 days
- **Purpose:** Regular checkpoints for recent progress
- **Example:** 25, 50, 75, 125, 150, 175, 225, 250, 275, etc.

### Moderate Tier (v-permanent)
- **Interval:** Every 100 nodes
- **Retention:** Permanent
- **Purpose:** Important milestones for long-term recovery
- **Example:** 100, 200, 300, 400, 600, 700, 800, 900, etc.

### Milestone Tier (v-permanent)
- **Interval:** Every 500 nodes
- **Retention:** Permanent
- **Purpose:** Major milestones for historical reference
- **Example:** 500, 1000, 1500, 2000, etc.

## Troubleshooting

### "BACKUP_PAT not configured"

The `BACKUP_PAT` secret is not set in your repository settings.

**Fix:**
1. Go to https://github.com/AlexM1010/FollowWeb/settings/secrets/actions
2. Click "New repository secret"
3. Name: `BACKUP_PAT`
4. Value: Your GitHub Personal Access Token with `repo` scope
5. Click "Add secret"

### "Release not found"

The release tags don't exist in the backup repository.

**Fix:** Follow the instructions above to create the releases.

### "Failed to upload backup"

The `BACKUP_PAT` token doesn't have the correct permissions.

**Fix:**
1. Go to https://github.com/settings/tokens
2. Find your token or create a new one
3. Ensure it has the `repo` scope (full control of private repositories)
4. Update the `BACKUP_PAT` secret in your repository settings

## Related Documentation

- `BACKUP_FAILURE_POLICY.md` - Detailed explanation of the fail-fast policy
- `setup_backup_releases.ps1` - PowerShell script to create releases
- `setup_backup_releases.sh` - Bash script to create releases
