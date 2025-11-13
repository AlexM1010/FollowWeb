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
