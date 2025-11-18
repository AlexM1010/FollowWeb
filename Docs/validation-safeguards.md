# Checkpoint Validation Safeguards

This document describes all validation safeguards implemented to prevent storing or processing empty, corrupted, or invalid data.

## Overview

The system now has comprehensive validation at multiple levels:
1. **Input validation** - Reject invalid samples before storage
2. **File validation** - Verify checkpoint files are valid
3. **Archive validation** - Ensure tar archives are not corrupted
4. **Data validation** - Check for invalid samples in existing checkpoints

## 1. Input Validation (Loader Level)

### Location
- `FollowWeb/FollowWeb_Visualizor/data/loaders/incremental_freesound.py`

### Validations
- **Zero filesize rejection**: Samples with `filesize == 0` are rejected before being added to the graph
- **Raises ValueError**: Invalid samples trigger an exception with clear error message
- **Logging**: Warning logged for each rejected sample with sample ID and name

### Methods Protected
- `_add_node_to_graph()` - Validates before adding nodes without edges
- `_add_sample_to_graph()` - Validates before adding nodes with relationships

### Example Error
```
WARNING: Skipping sample 12345 (example.wav): invalid filesize (0 bytes)
ValueError: Sample 12345 has invalid filesize: 0 bytes
```

## 2. Checkpoint File Validation

### Location
- `FollowWeb/FollowWeb_Visualizor/data/checkpoint_verifier.py`

### Validations

#### File Existence
- Checks all three checkpoint files exist:
  - `graph_topology.gpickle`
  - `metadata_cache.db`
  - `checkpoint_metadata.json`

#### Minimum File Sizes
- **Pickle file**: Minimum 100 bytes
- **SQLite database**: Minimum 8KB (2 database pages)
- **JSON file**: Minimum 10 bytes

#### Content Validation
- **Pickle file**:
  - Can be loaded without errors
  - Contains a valid NetworkX graph object
  - Graph has at least 1 node
  
- **SQLite database**:
  - Can be opened without errors
  - Contains at least one table
  - Metadata table has at least 1 row
  
- **JSON file**:
  - Valid JSON syntax
  - Can be parsed without errors

### Usage
```python
from FollowWeb_Visualizor.data.checkpoint_verifier import CheckpointVerifier

verifier = CheckpointVerifier(checkpoint_dir, logger)
success, message = verifier.verify_checkpoint_files()
```

## 3. Archive Validation (Workflow Level)

### Location
- `.github/workflows/freesound-backup.yml`
- `.github/workflows/freesound-data-repair.yml`

### Validations

#### Before Extraction
- **Archive integrity**: `tar -tzf` succeeds without errors
- **Non-empty**: Archive contains at least 1 file
- **File count**: Archive has expected number of files
- **Directory creation**: Extraction creates expected directory

#### After Creation
- **File existence**: Backup file exists
- **Size range**: Between 100KB and 10GB
- **Archive integrity**: Can list contents without errors
- **Non-empty**: Contains at least 1 file
- **Minimum files**: Contains at least 3 files (graph, db, json)
- **Required files**: All three checkpoint files present
- **Test extraction**: Can extract to temporary directory

### Example Workflow Steps
```yaml
# Validate before extraction
- name: Validate archive
  run: |
    if ! tar -tzf checkpoint_backup.tar.gz > /dev/null 2>&1; then
      echo "::error::Archive is corrupted"
      exit 1
    fi
    
    file_count=$(tar -tzf checkpoint_backup.tar.gz | wc -l)
    if [ "$file_count" -eq 0 ]; then
      echo "::error::Archive is empty"
      exit 1
    fi
```

## 4. Sample Data Validation

### Location
- `scripts/freesound/validate_freesound_samples.py`
- `scripts/validation/repair_checkpoint.py`
- `scripts/validation/validate_checkpoint_integrity.py`

### Validations

#### Validation Script
Checks existing checkpoints for:
- **Zero filesize**: Removes samples with `filesize == 0`
- **Deleted samples**: Removes samples no longer on Freesound API
- **Invalid metadata**: Detects missing critical fields

Statistics tracked:
- `invalid_filesize_removed`: Count of samples removed for zero filesize
- `deleted_samples`: List of removed samples with reasons
- `edges_removed`: Count of edges removed with invalid samples

#### Repair Script
Prevents repairing invalid samples:
- **Zero filesize check**: Marks samples with `filesize == 0` for removal
- **API validation**: Rejects API responses with zero filesize
- **Batch removal**: Removes all invalid samples after detection

#### Integrity Validator
Comprehensive validation tool:
- **File validation**: Uses CheckpointVerifier for basic checks
- **Graph validation**: Loads and validates graph structure
- **Database validation**: Checks SQLite database integrity
- **Sample validation**: Checks all samples for invalid data
- **Fix mode**: Can automatically remove invalid samples

### Usage

#### Validation Script
```bash
# Check for invalid samples
python scripts/freesound/validate_freesound_samples.py --mode full

# Quick check (300 oldest samples)
python scripts/freesound/validate_freesound_samples.py --mode partial
```

#### Repair Script
```bash
# Repair with API fetching (max 10 requests)
python scripts/validation/repair_checkpoint.py \
  --api-key YOUR_KEY \
  --max-requests 10
```

#### Integrity Validator
```bash
# Check integrity (read-only)
python scripts/validation/validate_checkpoint_integrity.py

# Check and fix issues
python scripts/validation/validate_checkpoint_integrity.py --fix
```

## 5. Validation Flow

### Data Collection
```
API Response → Filesize Check → Add to Graph → Save Checkpoint
                     ↓ (if zero)
                  Reject & Log
```

### Checkpoint Save
```
Graph + Metadata → CheckpointVerifier → Save Files → Verify Files
                         ↓ (if invalid)
                    Fail & Report
```

### Backup Creation
```
Checkpoint Files → Create Tar → Validate Archive → Upload
                                      ↓ (if invalid)
                                 Fail & Cleanup
```

### Checkpoint Restore
```
Download Tar → Validate Archive → Extract → Verify Files → Load Data
                     ↓ (if invalid)
                Fail & Report
```

## 6. Error Handling

### Graceful Degradation
- Invalid samples are logged but don't crash the pipeline
- Partial progress is preserved even if some samples fail
- Validation failures trigger clear error messages

### Fail-Fast Architecture
- Critical validation failures stop execution immediately
- Prevents cascading failures from corrupted data
- Ensures data integrity at every step

### Recovery Mechanisms
- Validation script can clean existing checkpoints
- Repair script can fetch missing data from API
- Integrity validator can fix issues automatically

## 7. Monitoring & Logging

### Metrics Tracked
- `invalid_filesize`: Count of samples with zero filesize
- `invalid_filesize_removed`: Count removed during validation
- `samples_removed`: Total samples removed for any reason
- `api_errors`: Count of API failures during validation

### Log Messages
- **WARNING**: Invalid samples detected (with details)
- **ERROR**: Critical validation failures
- **INFO**: Validation progress and results

### Workflow Outputs
- Validation reports in JSON format
- GitHub Actions step summaries
- Detailed logs in `logs/` directory

## 8. Best Practices

### For Developers
1. Always validate input before storage
2. Use CheckpointVerifier before loading checkpoints
3. Check return values from validation functions
4. Log validation failures with context

### For Operations
1. Run integrity validator periodically
2. Monitor validation metrics in logs
3. Investigate repeated validation failures
4. Keep validation scripts up to date

### For CI/CD
1. Validate archives before upload
2. Verify checkpoints after restore
3. Fail fast on validation errors
4. Clean up invalid files immediately

## 9. Testing

### Unit Tests
- Test filesize validation in loader
- Test CheckpointVerifier with various inputs
- Test archive validation logic

### Integration Tests
- Test full validation pipeline
- Test repair with invalid data
- Test backup/restore with validation

### Performance Tests
- Validate large checkpoints efficiently
- Ensure validation doesn't slow pipeline
- Test parallel validation operations

## 10. Future Enhancements

### Potential Improvements
- Add checksum validation for files
- Implement incremental validation
- Add validation caching
- Support custom validation rules
- Add validation metrics dashboard

### Known Limitations
- Validation adds small overhead to pipeline
- Some corrupted data may pass basic checks
- API validation requires network access
- Large checkpoints take longer to validate
