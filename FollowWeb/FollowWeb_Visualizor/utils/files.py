"""
File system operations and utilities for FollowWeb network analysis.

This module provides file I/O operations, path handling, and directory management
utilities used throughout the FollowWeb package.
"""

# Standard library imports
import hashlib
import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Callable, Optional

# Local imports
from ..core.exceptions import DataProcessingError
from .validation import validate_non_empty_string, validate_path_string


class ErrorRecoveryManager:
    """Manages error recovery patterns and retry logic."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """Initialize error recovery manager."""
        self.logger = logger or logging.getLogger(__name__)

    def with_retry(
        self,
        func: Callable,
        max_attempts: int = 3,
        delay: float = 1.0,
        exceptions: tuple = (Exception,),
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: Function to execute
            max_attempts: Maximum number of attempts
            delay: Delay between attempts in seconds
            exceptions: Tuple of exceptions to catch and retry

        Returns:
            Function result if successful

        Raises:
            Last exception if all attempts fail
        """
        last_exception = None

        for attempt in range(max_attempts):
            try:
                return func()
            except exceptions as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"All {max_attempts} attempts failed. Last error: {e}"
                    )

        raise last_exception

    def safe_execute(
        self,
        func: Callable,
        default_return: Optional[Any] = None,
        log_errors: bool = True,
    ) -> Any:
        """
        Execute a function safely, returning default value on error.

        Args:
            func: Function to execute
            default_return: Value to return on error
            log_errors: Whether to log errors

        Returns:
            Function result or default_return on error
        """
        try:
            return func()
        except Exception as e:
            if log_errors:
                self.logger.error(f"Safe execution failed: {e}")
            return default_return


class FileOperationHandler:
    """Handles common file operation error patterns."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """Initialize file operation handler."""
        self.logger = logger or logging.getLogger(__name__)

    def safe_file_write(
        self, filepath: str, content: str, encoding: str = "utf-8"
    ) -> bool:
        """
        Safely write content to a file with standardized error handling.

        Args:
            filepath: Path to the file
            content: Content to write
            encoding: File encoding

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, "w", encoding=encoding) as f:
                f.write(content)

            self.logger.debug(f"Successfully wrote file: {filepath}")
            return True

        except PermissionError as e:
            self.logger.error(f"Permission denied writing to {filepath}: {e}")
            return False
        except OSError as e:
            self.logger.error(f"Failed to write file {filepath}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error writing file {filepath}: {e}")
            return False

    def safe_file_read(self, filepath: str, encoding: str = "utf-8") -> Optional[str]:
        """
        Safely read content from a file with standardized error handling.

        Args:
            filepath: Path to the file
            encoding: File encoding

        Returns:
            File content if successful, None otherwise
        """
        try:
            with open(filepath, encoding=encoding) as f:
                content = f.read()

            self.logger.debug(f"Successfully read file: {filepath}")
            return content

        except FileNotFoundError:
            self.logger.error(f"File not found: {filepath}")
            return None
        except PermissionError as e:
            self.logger.error(f"Permission denied reading {filepath}: {e}")
            return None
        except OSError as e:
            self.logger.error(f"Failed to read file {filepath}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error reading file {filepath}: {e}")
            return None

    def safe_file_delete(self, filepath: str, max_retries: int = 3) -> bool:
        """
        Safely delete a file with retry logic.

        Args:
            filepath: Path to the file to delete
            max_retries: Maximum number of retry attempts

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(filepath):
            return True  # File doesn't exist, consider it successfully "deleted"

        for attempt in range(max_retries):
            try:
                os.unlink(filepath)
                self.logger.debug(f"Successfully deleted file: {filepath}")
                return True
            except PermissionError:
                if attempt < max_retries - 1:
                    # Brief delay to allow file handles to be released
                    time.sleep(0.1)
                    self.logger.warning(
                        f"Permission denied deleting {filepath}, retrying..."
                    )
                else:
                    self.logger.error(
                        f"Failed to delete {filepath} after {max_retries} attempts"
                    )
                    return False
            except Exception as e:
                # Other errors (file not found, etc.) - consider cleanup successful
                self.logger.debug(f"File deletion completed with exception: {e}")
                return True

        return False


@contextmanager
def error_context(
    operation_name: str, logger: Optional[logging.Logger] = None, reraise: bool = True
):
    """
    Context manager for standardized error handling and logging.

    Args:
        operation_name: Name of the operation for logging
        logger: Logger instance to use
        reraise: Whether to reraise exceptions

    Yields:
        None

    Example:
        with error_context("file processing"):
            process_file(filename)
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    try:
        logger.debug(f"Starting {operation_name}")
        yield
        logger.debug(f"Completed {operation_name}")
    except Exception as e:
        logger.error(f"Error in {operation_name}: {e}")
        if reraise:
            raise


def handle_common_exceptions(func: Callable) -> Callable:
    """
    Decorator for handling common exceptions with standardized logging.

    Args:
        func: Function to decorate

    Returns:
        Decorated function that handles common exceptions
    """

    def wrapper(*args, **kwargs) -> None:
        logger = logging.getLogger(func.__module__)

        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logger.error(f"File not found in {func.__name__}: {e}")
            return None
        except PermissionError as e:
            logger.error(f"Permission denied in {func.__name__}: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid value in {func.__name__}: {e}")
            raise  # Re-raise ValueError as it's usually a programming error
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            return None

    return wrapper


def generate_output_filename(
    prefix: str,
    strategy: str,
    k_value: int,
    extension: str,
    run_id: Optional[str] = None,
) -> str:
    """
    Generates a descriptive and unique output filename based on config and time.

    Args:
        prefix: Base filename prefix (e.g., "Output/FollowWeb")
        strategy: Analysis strategy name (e.g., "k-core", "reciprocal_k-core")
        k_value: K-value used for pruning
        extension: File extension (e.g., "html", "png")
        run_id: Optional run identifier to ensure all files from same run have same hash

    Returns:
        str: Formatted filename with format: {prefix}-{strategy}-k{k_value}-{config_hash}.{extension}

    Raises:
        ValueError: If any parameter is empty, invalid, or contains illegal characters
        DataProcessingError: If filename generation fails due to system constraints
    """
    # Input validation using shared utilities
    validate_non_empty_string(prefix, "prefix")
    validate_non_empty_string(strategy, "strategy")
    validate_non_empty_string(extension, "extension")

    from .validation import validate_non_negative_integer

    validate_non_negative_integer(k_value, "k_value")

    # Validate characters for filesystem compatibility
    # Note: For prefix, we need to be more careful about colons since they're valid in drive letters
    invalid_chars_general = '<>"|?*'

    # Check strategy and extension for all invalid characters
    for param_name, param_value in [("strategy", strategy), ("extension", extension)]:
        if any(char in param_value for char in invalid_chars_general + ":"):
            raise ValueError(f"{param_name} contains invalid filesystem characters")

    # For prefix, check invalid characters but allow colons in drive letters (Windows)
    if any(char in prefix for char in invalid_chars_general):
        raise ValueError("prefix contains invalid filesystem characters")

    # Check for invalid colons in prefix (not part of drive letter)
    if os.name == "nt":  # Windows
        # Allow colon only as second character (drive letter like C:)
        colon_positions = [i for i, char in enumerate(prefix) if char == ":"]
        for pos in colon_positions:
            if pos != 1:  # Not a drive letter colon
                raise ValueError(f"prefix contains invalid colon at position {pos}")
    else:
        # On non-Windows systems, no colons allowed in prefix
        if ":" in prefix:
            raise ValueError("prefix contains invalid filesystem character: :")

    # Additional validation for Windows reserved names and path separators
    if os.name == "nt":  # Windows
        # Replace forward slashes with backslashes for Windows
        prefix = prefix.replace("/", os.sep)

        # Check for reserved names in the filename part
        filename_part = os.path.basename(prefix)
        reserved_names = (
            ["CON", "PRN", "AUX", "NUL"]
            + [f"COM{i}" for i in range(1, 10)]
            + [f"LPT{i}" for i in range(1, 10)]
        )
        if filename_part.upper() in reserved_names:
            raise ValueError(f"filename contains reserved name: {filename_part}")

    try:
        with error_context("filename generation"):
            # Create a unique hash based on strategy, k_value, and run_id
            # If no run_id provided, generate one based on current time
            if run_id is None:
                run_id = str(int(time.time() * 1000))  # Millisecond precision

            config_str = f"{strategy}-{k_value}-{run_id}"
            config_hash = hashlib.md5(config_str.encode()).hexdigest()[:6]

            filename = f"{prefix}-{strategy}-k{k_value}-{config_hash}.{extension}"

            # Validate final filename length (most filesystems have 255 char limit)
            if len(os.path.basename(filename)) > 255:
                raise DataProcessingError("generated filename exceeds maximum length")

            return filename

    except Exception as e:
        if isinstance(e, (ValueError, DataProcessingError)):
            raise
        raise DataProcessingError(f"Failed to generate output filename: {e}") from e


def ensure_output_directory(output_path: str, create_if_missing: bool = True) -> str:
    """
    Ensure output directory exists and is writable with cross-platform path handling.

    Args:
        output_path: Absolute or relative path to output directory or file
        create_if_missing: Whether to create directory if it doesn't exist

    Returns:
        Validated absolute path to output directory

    Raises:
        ValueError: If path is invalid or not writable
        OSError: If directory creation fails
    """
    validate_path_string(output_path, "output path")

    # Handle both file paths and directory paths
    if os.path.splitext(output_path)[1]:  # Has file extension
        directory = os.path.dirname(output_path)
    else:
        directory = output_path

    # Convert to absolute path for consistency
    try:
        if directory:
            abs_directory = os.path.abspath(directory)
        else:
            # If no directory specified, use current working directory
            abs_directory = os.getcwd()
    except Exception as e:
        raise ValueError(f"Invalid path format '{output_path}': {e}") from e

    # Validate path format
    try:
        # Test if path is valid by attempting to normalize it
        normalized_path = os.path.normpath(abs_directory)

        # Check for invalid characters based on platform
        if os.name == "nt":  # Windows
            invalid_chars = '<>"|?*'
            if any(char in normalized_path for char in invalid_chars):
                raise ValueError("path contains invalid characters")

            # Check for reserved names
            path_parts = normalized_path.split(os.sep)
            reserved_names = (
                ["CON", "PRN", "AUX", "NUL"]
                + [f"COM{i}" for i in range(1, 10)]
                + [f"LPT{i}" for i in range(1, 10)]
            )
            for part in path_parts:
                if part.upper() in reserved_names:
                    raise ValueError(f"path contains reserved name: {part}")

        # Check path length limits
        if len(normalized_path) > 260 and os.name == "nt":  # Windows path limit
            raise ValueError("path exceeds maximum length")
        elif len(normalized_path) > 4096:  # General Unix limit
            raise ValueError("path exceeds maximum length")

    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Invalid path format '{output_path}': {e}") from e

    # Check if directory exists
    if os.path.exists(abs_directory):
        if not os.path.isdir(abs_directory):
            raise ValueError("path exists but is not a directory")

        # Check if directory is writable
        if not os.access(abs_directory, os.W_OK):
            raise ValueError("directory is not writable")

    elif create_if_missing:
        # Create directory with proper error handling
        try:
            os.makedirs(abs_directory, exist_ok=True)

            # Verify creation was successful and directory is writable
            if not os.path.exists(abs_directory):
                raise OSError("directory creation failed")

            if not os.access(abs_directory, os.W_OK):
                raise OSError("created directory is not writable")

        except PermissionError as e:
            raise OSError("permission denied creating directory") from e
        except FileExistsError:
            # This shouldn't happen with exist_ok=True, but handle it gracefully
            if not os.path.isdir(abs_directory):
                raise OSError(
                    "cannot create directory, file exists with same name"
                ) from None
        except OSError as e:
            # Provide more specific error messages based on common issues
            if "No space left on device" in str(e):
                raise OSError("insufficient disk space") from e
            elif "Read-only file system" in str(e):
                raise OSError("cannot create directory on read-only filesystem") from e
            else:
                raise OSError("failed to create directory") from e

    else:
        # Directory doesn't exist and we're not supposed to create it
        raise ValueError("Output directory does not exist")

    return abs_directory


def safe_file_cleanup(file_path: str, max_retries: int = 3, delay: float = 0.1) -> bool:
    """
    Safely remove a file with Windows-compatible retry logic.

    This function handles Windows-specific file locking issues that can occur
    when matplotlib or other libraries don't immediately release file handles.

    Args:
        file_path: Path to the file to remove
        max_retries: Maximum number of retry attempts
        delay: Delay between retry attempts in seconds

    Returns:
        bool: True if file was successfully removed, False otherwise

    Raises:
        ValueError: If file_path is empty or invalid
    """
    validate_non_empty_string(file_path, "file_path")

    if not os.path.exists(file_path):
        return True  # File doesn't exist, consider it "cleaned up"

    file_handler = FileOperationHandler()
    return file_handler.safe_file_delete(file_path, max_retries)
