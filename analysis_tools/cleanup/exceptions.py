"""
Exception classes for cleanup operations.

Provides a hierarchy of exceptions for different types of cleanup failures,
enabling precise error handling and recovery strategies.
"""

from typing import Optional

from .models import CleanupPhase


class CleanupError(Exception):
    """
    Base exception for cleanup operations.
    
    All cleanup-related exceptions inherit from this class, allowing
    for catch-all error handling when needed.
    
    Attributes:
        phase: The cleanup phase where the error occurred
        message: Human-readable error description
        recoverable: Whether the error can be recovered from with retry
    """

    def __init__(
        self, phase: CleanupPhase, message: str, recoverable: bool = True
    ) -> None:
        """
        Initialize cleanup error.
        
        Args:
            phase: The cleanup phase where error occurred
            message: Error description
            recoverable: Whether error can be recovered from
        """
        self.phase = phase
        self.message = message
        self.recoverable = recoverable
        super().__init__(f"[{phase.value}] {message}")


class FileOperationError(CleanupError):
    """
    Error during file system operations.
    
    Raised when file operations (move, copy, remove, create) fail due to:
    - File not found
    - Permission denied
    - Disk space insufficient
    - Path too long
    - I/O errors
    """

    def __init__(
        self,
        phase: CleanupPhase,
        message: str,
        file_path: Optional[str] = None,
        recoverable: bool = True,
    ) -> None:
        """
        Initialize file operation error.
        
        Args:
            phase: The cleanup phase where error occurred
            message: Error description
            file_path: Path to the file that caused the error
            recoverable: Whether error can be recovered from
        """
        self.file_path = file_path
        error_msg = f"{message}"
        if file_path:
            error_msg = f"{message} (file: {file_path})"
        super().__init__(phase, error_msg, recoverable)


class GitOperationError(CleanupError):
    """
    Error during git operations.
    
    Raised when git operations fail due to:
    - Uncommitted changes
    - Merge conflicts
    - Branch already exists
    - Remote operation failures
    - History rewriting failures
    """

    def __init__(
        self,
        phase: CleanupPhase,
        message: str,
        git_command: Optional[str] = None,
        recoverable: bool = False,
    ) -> None:
        """
        Initialize git operation error.
        
        Args:
            phase: The cleanup phase where error occurred
            message: Error description
            git_command: The git command that failed
            recoverable: Whether error can be recovered from (usually False for git)
        """
        self.git_command = git_command
        error_msg = f"{message}"
        if git_command:
            error_msg = f"{message} (command: {git_command})"
        super().__init__(phase, error_msg, recoverable)


class ValidationError(CleanupError):
    """
    Error during validation checks.
    
    Raised when validation fails due to:
    - Import failures
    - Test failures
    - Workflow syntax errors
    - Secret validation failures
    - File operation verification failures
    """

    def __init__(
        self,
        phase: CleanupPhase,
        message: str,
        validation_type: Optional[str] = None,
        errors: Optional[list[str]] = None,
        recoverable: bool = True,
    ) -> None:
        """
        Initialize validation error.
        
        Args:
            phase: The cleanup phase where error occurred
            message: Error description
            validation_type: Type of validation that failed
            errors: List of specific validation errors
            recoverable: Whether error can be recovered from
        """
        self.validation_type = validation_type
        self.errors = errors or []
        error_msg = f"{message}"
        if validation_type:
            error_msg = f"{message} (validation: {validation_type})"
        if self.errors:
            error_msg = f"{error_msg}\nErrors:\n" + "\n".join(
                f"  - {err}" for err in self.errors
            )
        super().__init__(phase, error_msg, recoverable)


class WorkflowError(CleanupError):
    """
    Error during workflow operations.
    
    Raised when workflow operations fail due to:
    - YAML parsing errors
    - API rate limiting
    - Workflow run failures
    - Secret access errors
    - Path update failures
    """

    def __init__(
        self,
        phase: CleanupPhase,
        message: str,
        workflow_file: Optional[str] = None,
        recoverable: bool = True,
    ) -> None:
        """
        Initialize workflow error.
        
        Args:
            phase: The cleanup phase where error occurred
            message: Error description
            workflow_file: Path to the workflow file that caused the error
            recoverable: Whether error can be recovered from
        """
        self.workflow_file = workflow_file
        error_msg = f"{message}"
        if workflow_file:
            error_msg = f"{message} (workflow: {workflow_file})"
        super().__init__(phase, error_msg, recoverable)
