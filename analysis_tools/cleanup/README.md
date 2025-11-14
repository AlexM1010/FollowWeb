# Cleanup System Module

Comprehensive repository cleanup and reorganization system integrated into analysis_tools.

## Overview

The cleanup system provides automated tools for:
- Repository structure reorganization
- File categorization and movement with git history preservation
- Workflow updates and optimization
- Validation and rollback capabilities
- Scalable operations for repositories of any size

## Module Structure

```
analysis_tools/cleanup/
├── __init__.py          # Module exports
├── exceptions.py        # Exception hierarchy
├── models.py            # Data models and configuration
└── README.md            # This file
```

## Core Components

### Exception Classes

All cleanup exceptions inherit from `CleanupError` for unified error handling:

- **CleanupError**: Base exception with phase tracking and recoverability
- **FileOperationError**: File system operation failures
- **GitOperationError**: Git operation failures
- **ValidationError**: Validation check failures
- **WorkflowError**: Workflow operation failures

Example:
```python
from analysis_tools.cleanup import FileOperationError, CleanupPhase

try:
    # File operation
    pass
except FileOperationError as e:
    print(f"Phase: {e.phase.value}")
    print(f"Recoverable: {e.recoverable}")
    print(f"File: {e.file_path}")
```

### Data Models

#### CleanupConfig

Comprehensive configuration for cleanup operations with scalability settings:

```python
from analysis_tools.cleanup import CleanupConfig

config = CleanupConfig(
    dry_run=True,
    create_backup_branch=True,
    git_batch_size=100,              # Files per commit
    max_workers=None,                # Auto-detect CPU cores
    large_scale_threshold=10000,     # Enable streaming at 10K+ files
    checkpoint_interval=5000,        # Save state every 5K files
)
```

**Performance Settings (Always Enabled):**
- `git_batch_size`: Files per git commit (default: 100)
- `max_workers`: CPU cores for parallel operations (None = auto-detect)
- `file_batch_size`: Files per processing batch (default: 1000)
- `parallel_chunk_size`: Chunk size for parallel categorization (default: 1000)

**Large-Scale Settings (Auto-enabled for 10K+ files):**
- `large_scale_threshold`: File count threshold (default: 10000)
- `use_state_db`: Enable SQLite state tracking (auto-enabled)
- `enable_checkpoints`: Enable checkpoint/resume (auto-enabled)
- `checkpoint_interval`: Files between checkpoints (default: 5000)

#### CleanupPhase

Enumeration of all cleanup phases in execution order:

```python
from analysis_tools.cleanup import CleanupPhase

phases = [
    CleanupPhase.BACKUP,
    CleanupPhase.CACHE_CLEANUP,
    CleanupPhase.ROOT_CLEANUP,
    CleanupPhase.SCRIPT_ORGANIZATION,
    CleanupPhase.DOC_CONSOLIDATION,
    CleanupPhase.BRANCH_CLEANUP,
    CleanupPhase.WORKFLOW_UPDATE,
    CleanupPhase.WORKFLOW_OPTIMIZATION,
    CleanupPhase.CI_PARALLELIZATION,
    CleanupPhase.CODE_QUALITY,
    CleanupPhase.CODE_REVIEW_INTEGRATION,
    CleanupPhase.VALIDATION,
    CleanupPhase.DOCUMENTATION,
]
```

#### File Operation Models

- **FileMapping**: Planned file operation (source, destination, type)
- **FileOperation**: Completed operation record with timestamp
- **CategorizedFile**: File with category and destination
- **FileCategory**: Enumeration of file categories

#### Validation Models

- **ValidationResult**: Validation check outcome with errors/warnings
- **TestResult**: Test suite execution statistics
- **PhaseResult**: Complete phase execution result

#### Repository Models

- **BranchInfo**: Git branch metadata
- **WorkflowConfig**: Parsed GitHub Actions workflow
- **WorkflowRunResult**: Workflow execution outcome
- **Metrics**: Repository statistics
- **DirectoryStructure**: Directory organization
- **RollbackState**: State for phase rollback

## Command-Line Interface

The CLI uses EmojiFormatter for cross-platform emoji support. On Windows, it automatically falls back to simple ASCII symbols to avoid encoding issues.

### Analysis Commands

```bash
# Run full analysis
python -m analysis_tools

# Run optimization analysis
python -m analysis_tools --optimize
```

### Cleanup Commands

```bash
# Analyze repository for cleanup opportunities
python -m analysis_tools --cleanup-analyze

# Execute cleanup phases
python -m analysis_tools --cleanup-execute --phase root_cleanup

# Execute with dry-run (no changes)
python -m analysis_tools --cleanup-execute --phase root_cleanup --dry-run

# Validate cleanup environment
python -m analysis_tools --validate-cleanup

# Rollback a phase
python -m analysis_tools --cleanup-rollback --phase root_cleanup
```

### Options

- `--phase PHASE`: Specific cleanup phase to execute or rollback
- `--dry-run`: Simulate operations without making changes
- `--project-root PATH`: Project root directory (default: current directory)

## Usage Examples

### Import Models

```python
from analysis_tools.cleanup import (
    CleanupConfig,
    CleanupPhase,
    FileMapping,
    ValidationResult,
    CleanupError,
)

# Create configuration
config = CleanupConfig(
    dry_run=False,
    create_backup_branch=True,
    phases_to_execute=["root_cleanup", "script_organization"],
)

# Create file mapping
mapping = FileMapping(
    source="TEST_REPORT.md",
    destination="docs/reports/TEST_REPORT.md",
    operation_type="move",
)
```

### Error Handling

```python
from analysis_tools.cleanup import (
    CleanupError,
    FileOperationError,
    GitOperationError,
    ValidationError,
)

try:
    # Cleanup operations
    pass
except FileOperationError as e:
    print(f"File operation failed: {e}")
    if e.recoverable:
        # Retry logic
        pass
except GitOperationError as e:
    print(f"Git operation failed: {e}")
    # Usually not recoverable
except ValidationError as e:
    print(f"Validation failed: {e}")
    print(f"Errors: {e.errors}")
except CleanupError as e:
    print(f"Cleanup error in phase {e.phase.value}: {e}")
```

## Scalability Features

### Always-On Optimizations (All Repository Sizes)

1. **Parallel Operations**: Auto-detects CPU cores for optimal parallelization
2. **Batch Git Operations**: Groups operations (100 files per commit)
3. **Disk I/O Optimization**: Sorts operations by directory to minimize seeks
4. **Progress Tracking**: Real-time progress bars with ETA

### Automatic Large-Scale Optimizations (10K+ Files)

When file count exceeds `large_scale_threshold` (default: 10,000):

1. **Streaming Architecture**: Iterator-based processing in batches
2. **State Database**: SQLite with WAL mode for operation tracking
3. **Checkpoint/Resume**: Save state every 5,000 files for interruption recovery

### Performance Targets

- 100 files: < 1 minute
- 10,000 files: < 10 minutes
- 100,000 files: < 2 hours (I/O-bound)

## Integration with analysis_tools

The cleanup system integrates seamlessly with existing analysis_tools:

- Uses `AnalysisOrchestrator` for coordination
- Leverages `CodeAnalyzer` for import validation
- Uses `TestAnalyzer` for test suite validation
- Saves reports to `analysis_reports/` directory
- Follows existing patterns and conventions

## Next Steps

The following components need to be implemented:

1. **CleanupOrchestrator**: Phase execution and coordination
2. **FileManager**: File operations with organize-tool integration
3. **GitManager**: Git operations with GitPython and git-filter-repo
4. **WorkflowManager**: Workflow updates with PyYAML and reviewdog
5. **ValidationEngine**: Validation using existing analyzers
6. **ReportingSystem**: Report generation
7. **RollbackManager**: Rollback functionality
8. **StateDatabase**: Large-scale state tracking (10K+ files)
9. **CheckpointManager**: Checkpoint/resume (10K+ files)

## Requirements

See `.kiro/specs/repository-cleanup/requirements.md` for detailed requirements.

## Design

See `.kiro/specs/repository-cleanup/design.md` for comprehensive design documentation.


## Comprehensive CLI Guide

### Installation

The cleanup system is part of the `analysis_tools` package. Dependencies are automatically installed:

```bash
# Install with cleanup dependencies
pip install -e "FollowWeb/[cleanup]"

# Or install individual dependencies
pip install organize-tool git-filter-repo gitpython github3.py pyyaml reviewdog
```

### CLI Commands

#### analyze - Analyze Repository

Analyze repository structure and generate cleanup recommendations.

```bash
python -m analysis_tools.cleanup analyze [OPTIONS]

Options:
  --config PATH         Path to configuration file
  --project-root PATH   Project root directory (default: current directory)
```

**Example Output:**
```
============================================================
CLEANUP ANALYSIS RESULTS
============================================================

Root Directory:
  Files: 69
  Target: < 15 files
  Reduction needed: 54 files

Cache Directories:
  Size: 178.4 MB
  Directories: 4

Utility Scripts:
  Count: 29
  Uncategorized: 12

Documentation:
  Files: 45
  Duplicates: 8

Branches:
  Total: 15
  Merged: 5
  Stale: 3

Workflows:
  Total: 8
  Failing: 2
  Path updates needed: 6

============================================================
Report saved to: analysis_reports/cleanup_analysis_20241114.json
============================================================
```

#### execute - Execute Cleanup Phases

Execute cleanup phases with validation and rollback support.

```bash
python -m analysis_tools.cleanup execute [OPTIONS]

Options:
  --phase PHASE         Specific phase to execute
  --all                 Execute all phases
  --dry-run             Simulate operations without making changes
  --config PATH         Path to configuration file
  --no-backup           Skip backup branch creation
  --skip-validation     Skip validation checks
  --no-commit           Do not auto-commit changes
  --yes, -y             Skip confirmation prompts
  --project-root PATH   Project root directory
```

**Examples:**

```bash
# Dry run all phases
python -m analysis_tools.cleanup execute --all --dry-run

# Execute specific phase
python -m analysis_tools.cleanup execute --phase root_cleanup

# Execute all phases without confirmation
python -m analysis_tools.cleanup execute --all --yes

# Execute with custom config
python -m analysis_tools.cleanup execute --all --config cleanup_config.json

# Execute without backup (not recommended)
python -m analysis_tools.cleanup execute --phase cache_cleanup --no-backup
```

#### rollback - Rollback Phase

Rollback a cleanup phase to its previous state.

```bash
python -m analysis_tools.cleanup rollback [OPTIONS]

Options:
  --phase PHASE         Phase to rollback (required)
  --yes, -y             Skip confirmation prompt
  --project-root PATH   Project root directory
```

**Examples:**

```bash
# Rollback with confirmation
python -m analysis_tools.cleanup rollback --phase root_cleanup

# Rollback without confirmation
python -m analysis_tools.cleanup rollback --phase root_cleanup --yes
```

#### validate - Validate Environment

Validate cleanup environment and prerequisites.

```bash
python -m analysis_tools.cleanup validate [OPTIONS]

Options:
  --project-root PATH   Project root directory
```

**Example Output:**
```
============================================================
ENVIRONMENT VALIDATION
============================================================

Git Repository:
  Status: ✓
  Clean working tree: ✓

Required Tools:
  git: ✓
  gh: ✓
  python: ✓

Secrets:
  FREESOUND_API_KEY: ✓
  BACKUP_PAT: ✓
  BACKUP_PAT_SECONDARY: ✓

Disk Space:
  Available: 15.3 GB
  Required: 1.0 GB
  Status: ✓

============================================================
```

#### list-phases - List Available Phases

List all available cleanup phases with descriptions.

```bash
python -m analysis_tools.cleanup list-phases
```

**Output:**
```
============================================================
AVAILABLE CLEANUP PHASES
============================================================

backup
  Create backup branch before cleanup

cache_cleanup
  Remove cache directories from version control

root_cleanup
  Move documentation files to organized structure

script_organization
  Organize utility scripts by category

doc_consolidation
  Eliminate duplicate documentation

branch_cleanup
  Remove stale and merged branches

workflow_update
  Update workflow files with new paths

workflow_optimization
  Fix workflow failures and optimize schedules

ci_parallelization
  Optimize CI matrix parallelization

code_quality
  Remediate code quality issues

code_review_integration
  Integrate automated code review tools

validation
  Comprehensive validation of all changes

documentation
  Generate comprehensive documentation

============================================================
Usage:
  python -m analysis_tools.cleanup execute --phase <phase_name>
  python -m analysis_tools.cleanup execute --all
============================================================
```

#### create-config - Create Configuration File

Create a default configuration file for customization.

```bash
python -m analysis_tools.cleanup create-config OUTPUT_PATH

Example:
  python -m analysis_tools.cleanup create-config cleanup_config.json
```

### Configuration File

Create a JSON configuration file to customize cleanup behavior:

```json
{
  "dry_run": false,
  "create_backup_branch": true,
  "backup_branch_name": "backup/pre-cleanup",
  "phases_to_execute": ["all"],
  "skip_validation": false,
  "auto_commit": true,
  
  "docs_structure": {
    "reports": "docs/reports",
    "guides": "docs/guides",
    "analysis": "docs/analysis",
    "archive": "docs/archive"
  },
  
  "scripts_structure": {
    "freesound": "scripts/freesound",
    "backup": "scripts/backup",
    "validation": "scripts/validation",
    "generation": "scripts/generation",
    "testing": "scripts/testing",
    "analysis": "scripts/analysis"
  },
  
  "gitignore_patterns": [
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    "__pycache__/",
    "temp_*/",
    "_temp_*/",
    "TestOutput-*.txt",
    "*_viz_*.log"
  ],
  
  "workflow_schedule_offset_minutes": 15,
  "required_secrets": [
    "FREESOUND_API_KEY",
    "BACKUP_PAT",
    "BACKUP_PAT_SECONDARY"
  ],
  
  "git_batch_size": 100,
  "max_workers": null,
  "file_batch_size": 1000,
  "large_scale_threshold": 10000,
  "checkpoint_interval": 5000
}
```

### Rollback Procedures

#### Automatic Rollback

The cleanup system automatically rolls back on validation failures:

1. **Validation Failure Detected** - Phase validation fails
2. **Rollback Initiated** - System begins rollback process
3. **Operations Reverted** - File operations reversed
4. **Git Commits Reverted** - Git commits undone
5. **State Restored** - Repository returned to pre-phase state
6. **Report Generated** - Rollback report created

#### Manual Rollback

To manually rollback a phase:

```bash
# Rollback specific phase
python -m analysis_tools.cleanup rollback --phase <phase_name>

# Example: Rollback root cleanup
python -m analysis_tools.cleanup rollback --phase root_cleanup
```

#### Emergency Rollback

If the cleanup system fails catastrophically:

```bash
# Switch to backup branch
git checkout backup/pre-cleanup

# Force push to main (if necessary)
git checkout main
git reset --hard backup/pre-cleanup
git push --force origin main

# Or create new branch from backup
git checkout -b recovery backup/pre-cleanup
```

### Progress Tracking

The cleanup system provides real-time progress tracking:

#### Progress Bars

```
Moving files: 1234/5000 [████████░░░░░░░░] 24.7% ETA: 2m 15s
```

#### Time Estimates

- **Completion percentage** - Current progress
- **ETA** - Estimated time to completion
- **Throughput** - Files processed per second

#### Checkpoints (10K+ files)

For large-scale operations, the system automatically saves checkpoints:

```
Checkpoint saved: 5000/50000 files processed
Resume command: python -m analysis_tools.cleanup execute --phase root_cleanup
```

### Workflow Examples

#### Example 1: First-Time Cleanup

```bash
# Step 1: Analyze repository
python -m analysis_tools.cleanup analyze

# Step 2: Test with dry run
python -m analysis_tools.cleanup execute --all --dry-run

# Step 3: Execute cleanup
python -m analysis_tools.cleanup execute --all

# Step 4: Validate results
python -m analysis_tools.cleanup validate
```

#### Example 2: Incremental Cleanup

```bash
# Execute phases one at a time
python -m analysis_tools.cleanup execute --phase backup
python -m analysis_tools.cleanup execute --phase cache_cleanup
python -m analysis_tools.cleanup execute --phase root_cleanup

# Validate after each phase
python -m analysis_tools.cleanup validate
```

#### Example 3: Custom Configuration

```bash
# Create config file
python -m analysis_tools.cleanup create-config my_config.json

# Edit config file (customize directory structure, etc.)
# ...

# Execute with custom config
python -m analysis_tools.cleanup execute --all --config my_config.json
```

#### Example 4: Rollback and Retry

```bash
# Execute phase
python -m analysis_tools.cleanup execute --phase root_cleanup

# If something goes wrong, rollback
python -m analysis_tools.cleanup rollback --phase root_cleanup

# Fix issues, then retry
python -m analysis_tools.cleanup execute --phase root_cleanup
```

### Troubleshooting

#### Common Issues

**"Git repository not found"**

Solution: Run from repository root or use `--project-root`:

```bash
python -m analysis_tools.cleanup execute --all --project-root /path/to/repo
```

**"Uncommitted changes detected"**

Solution: Commit or stash changes before cleanup:

```bash
git stash
python -m analysis_tools.cleanup execute --all
git stash pop
```

**"Validation failed"**

Solution: Check validation report and fix issues:

```bash
python -m analysis_tools.cleanup validate
```

**"Disk space insufficient"**

Solution: Free up disk space (requires 1+ GB):

```bash
# Clean cache directories
rm -rf .mypy_cache .pytest_cache .ruff_cache __pycache__

# Run cleanup
python -m analysis_tools.cleanup execute --all
```

#### Debug Mode

Enable debug logging for troubleshooting:

```bash
export LOG_LEVEL=DEBUG
python -m analysis_tools.cleanup execute --all
```

#### Getting Help

```bash
# Show help
python -m analysis_tools.cleanup --help

# Show command help
python -m analysis_tools.cleanup execute --help

# List available phases
python -m analysis_tools.cleanup list-phases
```

### Best Practices

#### Before Cleanup

1. **Commit all changes** - Ensure clean working tree
2. **Run analysis** - Understand what will change
3. **Test with dry-run** - Verify operations
4. **Create backup** - Let system create backup branch
5. **Notify team** - Inform collaborators

#### During Cleanup

1. **Monitor progress** - Watch for errors or warnings
2. **Validate each phase** - Check results after each phase
3. **Review reports** - Read generated reports
4. **Test functionality** - Verify repository still works

#### After Cleanup

1. **Run tests** - Execute full test suite
2. **Check workflows** - Verify CI/CD pipelines
3. **Update documentation** - Review generated docs
4. **Notify team** - Share migration guide
5. **Delete backup** - After confirming success
