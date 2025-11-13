"""
Cleanup system for repository reorganization and maintenance.

This module provides comprehensive tools for cleaning up and reorganizing
repository structure, including file operations, git history preservation,
workflow updates, and validation.
"""

from .exceptions import (
    CleanupError,
    FileOperationError,
    GitOperationError,
    ValidationError,
    WorkflowError,
)
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
from .reporting import ReportingSystem
from .rollback import RollbackManager
from .validation import ValidationEngine

__all__ = [
    # Exceptions
    "CleanupError",
    "FileOperationError",
    "GitOperationError",
    "ValidationError",
    "WorkflowError",
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
]
