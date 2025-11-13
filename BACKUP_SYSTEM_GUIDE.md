# Freesound Pipeline Backup System

## Overview

The Freesound pipeline now includes an intelligent tiered backup system that creates persistent backups at configurable intervals. This provides granular recovery options and protects against data loss during long-running collection operations.

## Key Features

### ✅ Configurable Backup Intervals
- **Default**: Every 25 nodes (4x more frequent than previous 100-node backups)
- **Customizable**: Adjust via `backup_interval_nodes` configuration
- **Checkpoint-aware**: Integrates seamlessly with existing checkpoint system

### ✅ Multi-Tier Retention Strategy
- **Frequent**: Every 25 nodes → keeps last 5 backups
- **Moderate**: Every 100 nodes → keeps last 10 backups  
- **Milestone**: Every 500 nodes → keeps indefinitely
- **Daily**: One per day → keeps last 30 days

### ✅ Automatic Cleanup
- Removes old backups based on retention policy
- Always keeps at least 3 most recent backups
- Milestone backups never deleted

### ✅ Compression Support
- Automatically compresses backups older than 7 days
- Uses gzip compression to save disk space
- Transparent decompression during restore

### ✅ Backup Manifest
- Tracks all backups with metadata (timestamp, nodes, edges, size)
- JSON format for easy inspection
- Located at `data/freesound_library/backup_manifest.json`

## Configuration

### Basic Configuration

Add these parameters to your loader configuration:

```python
loader_config = {
    'api_key': api_key,
    'checkpoint_dir': 'data/freesound_library',
    
    # Backup configuration
    'backup_interval_nodes': 25,      # Backup every 25 nodes
    'backup_retention_count': 10,     # Keep last 10 backups per tier
    'backup_compression': True,       # Enable compression
    'tiered_backups': True,           # Enable tiered strategy
    'compression_age_days': 7,        # Compress after 7 days
}
```

### Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `backup_interval_nodes` | 25 | Nodes between backups |
| `backup_retention_count` | 10 | Max backups to keep per tier |
| `backup_compression` | True | Enable gzip compression |
| `tiered_backups` | True | Use multi-tier strategy |
| `compression_age_days` | 7 | Days before compression |

## Directory Structure

```
data/freesound_library/
├── graph_topology.gpickle              # Current checkpoint
├── metadata_cache.db                   # Current metadata
├── checkpoint_metadata.json            # Current metadata
├── backup_manifest.json                # Backup tracking
└── backups/
    ├── frequent/                       # Every 25 nodes
    │   ├── graph_topology_backup_25nodes_20251113_143022.gpickle
    │   ├── metadata_cache_backup_25nodes_20251113_143022.db
    │   ├── graph_topology_backup_50nodes_20251113_144530.gpickle
    │   └── metadata_cache_backup_50nodes_20251113_144530.db
    ├── moderate/                       # Every 100 nodes
    │   ├── graph_topology_backup_100nodes_20251113_150045.gpickle
    │   └── metadata_cache_backup_100nodes_20251113_150045.db
    ├── milestone/                      # Every 500 nodes
    │   ├── graph_topology_backup_500nodes_20251113_160022.gpickle
    │   └── metadata_cache_backup_500nodes_20251113_160022.db
    └── daily/                          # Daily backups (future)
```

## Usage

### Automatic Backups

Backups are created automatically during pipeline execution:

```python
from FollowWeb_Visualizor.data.loaders.incremental_freesound import IncrementalFreesoundLoader

loader = IncrementalFreesoundLoader(loader_config)
data = loader.fetch_data(
    query="",
    max_samples=1000,
    recursive_depth=2,
    max_total_samples=1000
)
```

Backups are created:
- Every 25 nodes (frequent tier)
- Every 100 nodes (moderate tier)
- Every 500 nodes (milestone tier)

### List Available Backups

```bash
# List all backups
python restore_from_backup.py --list

# List backups for specific tier
python restore_from_backup.py --list --tier milestone

# Show backup statistics
python restore_from_backup.py --stats
```

### Restore from Backup

```bash
# Restore from most recent backup
python restore_from_backup.py --restore latest

# Restore from specific backup (by timestamp)
python restore_from_backup.py --restore 20251113_143022

# Restore from most recent milestone backup
python restore_from_backup.py --restore latest --tier milestone
```

### Programmatic Access

```python
from FollowWeb_Visualizor.data.backup_manager import BackupManager

# Initialize manager
manager = BackupManager(
    backup_dir='data/freesound_library',
    config={'backup_interval_nodes': 25},
    logger=logger
)

# List backups
backups = manager.list_backups(tier='milestone')
for backup in backups:
    print(f"{backup['timestamp']}: {backup['nodes']} nodes")

# Get statistics
stats = manager.get_backup_stats()
print(f"Total backups: {stats['total_backups']}")
print(f"Total size: {stats['total_size_mb']:.2f} MB")
```

## Backup Tiers Explained

### Frequent Tier (Every 25 nodes)
- **Purpose**: Granular recovery for recent work
- **Retention**: Last 5 backups
- **Use case**: Recover from recent errors or interruptions

### Moderate Tier (Every 100 nodes)
- **Purpose**: Medium-term recovery points
- **Retention**: Last 10 backups
- **Use case**: Recover from issues discovered after some time

### Milestone Tier (Every 500 nodes)
- **Purpose**: Long-term archival
- **Retention**: Unlimited (never deleted)
- **Use case**: Major collection milestones, long-term reference

### Daily Tier (Future)
- **Purpose**: Time-based recovery
- **Retention**: Last 30 days
- **Use case**: Recover to specific date

## Benefits

### 🎯 Granular Recovery
- Restore from more frequent checkpoints (every 25 nodes vs 100)
- Minimize data loss in case of interruption
- Multiple recovery points to choose from

### 💾 Space Efficient
- Compression reduces disk usage by ~70%
- Retention policies prevent disk bloat
- Automatic cleanup of old backups

### 🔄 Flexible
- Tiered strategy balances frequency with storage
- Configurable intervals and retention
- Easy to adjust for different use cases

### 🛡️ Resilient
- Multiple backup tiers provide redundancy
- Milestone backups never deleted
- Always keeps 3 most recent backups

### 📊 Auditable
- Manifest file tracks all backups with metadata
- Easy to inspect backup history
- Detailed statistics available

## Monitoring

### Check Backup Status

```python
# View backup manifest
import json
with open('data/freesound_library/backup_manifest.json') as f:
    manifest = json.load(f)
    print(f"Total backups: {len(manifest['backups'])}")
```

### Monitor Disk Usage

```bash
# Check backup directory size
du -sh data/freesound_library/backups/

# Check compressed vs uncompressed
find data/freesound_library/backups/ -name "*.gz" | wc -l
find data/freesound_library/backups/ -name "*.gpickle" | wc -l
```

## Troubleshooting

### Backup Not Created

**Symptom**: No backup files in `backups/` directory

**Solutions**:
1. Check if `backup_interval_nodes` is set correctly
2. Verify node count is multiple of interval
3. Check disk space availability
4. Review logs for backup errors

### Restore Failed

**Symptom**: Restore command fails with error

**Solutions**:
1. Verify backup files exist and are not corrupted
2. Check file permissions
3. Ensure sufficient disk space
4. Try restoring from different backup

### Disk Space Issues

**Symptom**: Backups consuming too much disk space

**Solutions**:
1. Enable compression: `backup_compression: True`
2. Reduce retention: `backup_retention_count: 5`
3. Increase compression age: `compression_age_days: 3`
4. Manually delete old backups from non-milestone tiers

## Best Practices

### 1. Regular Monitoring
- Check backup manifest periodically
- Monitor disk usage
- Verify backups are being created

### 2. Test Restores
- Periodically test restore process
- Verify restored data integrity
- Document restore procedures

### 3. Adjust Configuration
- Tune intervals based on collection speed
- Adjust retention based on disk space
- Enable compression for long-term storage

### 4. Milestone Backups
- Milestone backups (every 500 nodes) are never deleted
- Use these for long-term archival
- Consider copying to external storage

### 5. Git Integration
- Backup manifest is Git-tracked
- Backup files are in `.gitignore`
- Commit manifest changes to track backup history

## Migration from Old System

The new backup system is backward compatible with the old checkpoint system:

1. **Existing checkpoints**: Automatically detected and used
2. **Old backups**: Still accessible in `backups/` directory
3. **No migration needed**: System works with existing data

## Future Enhancements (Phase 3 & 4)

### Phase 3: Daily Backups
- Implement time-based backup tier
- One backup per day, keep last 30
- Useful for date-based recovery

### Phase 4: Advanced Features
- Backup verification and integrity checks
- Incremental backups (delta compression)
- Remote backup storage (S3, GCS)
- Backup encryption for sensitive data
- Automated backup testing

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review backup manifest: `data/freesound_library/backup_manifest.json`
3. Use `--stats` flag to view backup statistics
4. Consult this guide for troubleshooting steps

## Summary

The tiered backup system provides:
- ✅ **4x more frequent backups** (every 25 nodes vs 100)
- ✅ **Intelligent retention** (5 frequent, 10 moderate, unlimited milestone)
- ✅ **Automatic compression** (saves ~70% disk space)
- ✅ **Easy restoration** (simple CLI tool)
- ✅ **Full auditability** (manifest tracking)

This ensures your Freesound collection data is protected with minimal manual intervention.
