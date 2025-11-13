"""
Data models for cleanup operations.

Defines all data structures used throughout the cleanup system, including
configuration, phase results, file operations, and validation results.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class CleanupPhase(Enum):
    """
    Cleanup phases in execution order.
    
    Each phase represents a discrete set of operations that can be
    executed independently with validation and rollback support.
    """

    BACKUP = "backup"
    CACHE_CLEANUP = "cache_cleanup"
    ROOT_CLEANUP = "root_cleanup"
    SCRIPT_ORGANIZATION = "script_organization"
    DOC_CONSOLIDATION = "doc_consolidation"
    BRANCH_CLEANUP = "branch_cleanup"
    WORKFLOW_UPDATE = "workflow_update"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    CI_PARALLELIZATION = "ci_parallelization"
    CODE_QUALITY = "code_quality"
    CODE_REVIEW_INTEGRATION = "code_review_integration"
    VALIDATION = "validation"
    DOCUMENTATION = "documentation"


class FileCategory(Enum):
    """
    Categories for file organization.
    
    Used to classify files for appropriate directory placement
    during repository reorganization.
    """

    REPORT = "report"
    GUIDE = "guide"
    ANALYSIS = "analysis"
    SUMMARY = "summary"
    STATUS = "status"
    COMPLETE = "complete"
    FREESOUND_SCRIPT = "freesound"
    BACKUP_SCRIPT = "backup"
    VALIDATION_SCRIPT = "validation"
    GENERATION_SCRIPT = "generation"
    TESTING_SCRIPT = "testing"
    ANALYSIS_SCRIPT = "analysis"
    CACHE = "cache"
    TEMP = "temp"
    LOG = "log"
    OBSOLETE = "obsolete"


@dataclass
class CleanupConfig:
    """
    Configuration for cleanup operations.
    
    Provides complete configuration for all aspects of the cleanup
    process, including directory structure, performance settings, and
    scalability options.
    """

    # Execution settings
    dry_run: bool = False
    create_backup_branch: bool = True
    backup_branch_name: str = "backup/pre-cleanup"
    phases_to_execute: list[str] = field(default_factory=lambda: ["all"])
    skip_validation: bool = False
    auto_commit: bool = True

    # Directory structure
    docs_structure: dict[str, str] = field(
        default_factory=lambda: {
            "reports": "docs/reports",
            "guides": "docs/guides",
            "analysis": "docs/analysis",
            "archive": "docs/archive",
        }
    )

    scripts_structure: dict[str, str] = field(
        default_factory=lambda: {
            "freesound": "scripts/freesound",
            "backup": "scripts/backup",
            "validation": "scripts/validation",
            "generation": "scripts/generation",
            "testing": "scripts/testing",
            "analysis": "scripts/analysis",
        }
    )

    # Files to remove
    empty_files: list[str] = field(default_factory=list)
    obsolete_files: list[str] = field(default_factory=list)

    # Gitignore patterns
    gitignore_patterns: list[str] = field(
        default_factory=lambda: [
            ".mypy_cache/",
            ".pytest_cache/",
            ".ruff_cache/",
            "__pycache__/",
            "temp_*/",
            "_temp_*/",
            "TestOutput-*.txt",
            "*_viz_*.log",
            "test_output.log",
        ]
    )

    # Workflow settings
    workflow_schedule_offset_minutes: int = 15
    required_secrets: list[str] = field(
        default_factory=lambda: [
            "FREESOUND_API_KEY",
            "BACKUP_PAT",
            "BACKUP_PAT_SECONDARY",
        ]
    )

    # Performance settings (always enabled)
    git_batch_size: int = 100  # Files per git commit
    max_workers: Optional[int] = None  # CPU cores for parallel ops (None = auto-detect)
    file_batch_size: int = 1000  # Files per processing batch
    parallel_chunk_size: int = 1000  # Chunk size for parallel categorization

    # Large-scale settings (10K+ files only, auto-enabled)
    large_scale_threshold: int = 10000  # Enable streaming/state DB above this
    use_state_db: bool = False  # Auto-enabled for 10K+ files
    enable_checkpoints: bool = False  # Auto-enabled for 10K+ files
    checkpoint_interval: int = 5000  # Save checkpoint every N files


@dataclass
class FileMapping:
    """
    Mapping for file move operations.
    
    Represents a planned file operation with source, destination,
    and operation type.
    """

    source: str
    destination: str
    operation_type: str  # 'move', 'copy', 'remove'


@dataclass
class FileOperation:
    """
    Record of completed file operation.
    
    Tracks the result of a file operation for reporting and rollback.
    """

    operation: str
    source: str
    destination: Optional[str]
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None


@dataclass
class CategorizedFile:
    """
    File with category and destination.
    
    Represents a file that has been categorized for organization
    with its target destination.
    """

    path: str
    category: FileCategory
    destination: str
    size_bytes: int
    last_modified: datetime


@dataclass
class BranchInfo:
    """
    Information about a git branch.
    
    Contains metadata about a branch for cleanup decision-making.
    """

    name: str
    last_commit_date: datetime
    has_pr: bool
    pr_number: Optional[int]
    is_merged: bool
    commit_count: int


@dataclass
class WorkflowConfig:
    """
    Parsed workflow configuration.
    
    Represents a GitHub Actions workflow with its key properties.
    """

    name: str
    path: str
    triggers: list[str]
    schedule: Optional[str]
    jobs: list[str]
    file_references: list[str]


@dataclass
class WorkflowRunResult:
    """
    Result of workflow execution.
    
    Contains the outcome of a workflow test run.
    """

    workflow_name: str
    run_id: str
    status: str  # 'success', 'failure', 'cancelled'
    duration: timedelta
    logs: str


@dataclass
class ValidationResult:
    """
    Result of validation check.
    
    Contains the outcome of a validation operation with any
    errors or warnings encountered.
    """

    phase: str
    validation_type: str
    success: bool
    errors: list[str]
    warnings: list[str]
    timestamp: datetime


@dataclass
class TestResult:
    """
    Result of test suite execution.
    
    Contains test execution statistics and failed test details.
    """

    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration: timedelta
    failed_tests: list[str]


@dataclass
class Metrics:
    """
    Repository metrics.
    
    Tracks key repository statistics for before/after comparison.
    """

    root_file_count: int
    total_size_mb: float
    cache_size_mb: float
    documentation_files: int
    utility_scripts: int
    test_pass_rate: float


@dataclass
class DirectoryStructure:
    """
    Repository directory structure.
    
    Describes the organization of directories with their purposes
    and file counts.
    """

    directories: dict[str, list[str]]
    purposes: dict[str, str]
    file_counts: dict[str, int]


@dataclass
class PhaseResult:
    """
    Result of phase execution.
    
    Contains complete information about a phase execution including
    operations performed, validation results, and any errors.
    """

    phase: CleanupPhase
    success: bool
    operations: list[FileOperation]
    validation_result: Optional[ValidationResult]
    duration: timedelta
    errors: list[str]
    warnings: list[str]
    rollback_available: bool


@dataclass
class RollbackState:
    """
    State for rolling back a phase.
    
    Contains all information needed to revert a phase to its
    previous state.
    """

    phase: CleanupPhase
    operations: list[FileOperation]
    git_commits: list[str]
    created_directories: list[str]
    modified_files: dict[str, str]  # file -> backup content
    timestamp: datetime
