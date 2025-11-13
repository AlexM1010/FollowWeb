"""
Cleanup system for repository reorganization and maintenance.

This module provides comprehensive tools for cleaning up and reorganizing
repository structure, including file operations, git history preservation,
workflow updates, and validation.
"""

from .checkpoint import CheckpointManager
from .exceptions import (
    CleanupError,
    FileOperationError,
    GitOperationError,
    ValidationError,
    WorkflowError,
)
from .file_manager import FileManager
from .git_manager import GitManager
from .models import (
    BranchInfo,
    CategorizedFile,
    CleanupConfig,
    CleanupPhase,
    DirectoryStructure,
    FileCategory,
    FileMapping,
    FileOperation,
    Metrics,
    PhaseResult,
    RollbackState,
    TestResult,
    ValidationResult,
    WorkflowConfig,
    WorkflowRunResult,
)
from .orchestrator import CleanupOrchestrator
from .reporting import ReportingSystem
from .rollback import RollbackManager
from .state_db import CleanupStateDB
from .validation import ValidationEngine
from .workflow_manager import WorkflowManager

__all__ = [
    # Exceptions
    "CleanupError",
    "FileOperationError",
    "GitOperationError",
    "ValidationError",
    "WorkflowError",
    # Orchestrator
    "CleanupOrchestrator",
    # Managers
    "FileManager",
    "GitManager",
    "WorkflowManager",
    # Models
    "BranchInfo",
    "CategorizedFile",
    "CleanupConfig",
    "CleanupPhase",
    "DirectoryStructure",
    "FileCategory",
    "FileMapping",
    "FileOperation",
    "Metrics",
    "PhaseResult",
    "RollbackState",
    "TestResult",
    "ValidationResult",
    "WorkflowConfig",
    "WorkflowRunResult",
    # Components
    "ReportingSystem",
    "RollbackManager",
    "ValidationEngine",
    # Scalability Components (10K+ files)
    "CleanupStateDB",
    "CheckpointManager",
]
