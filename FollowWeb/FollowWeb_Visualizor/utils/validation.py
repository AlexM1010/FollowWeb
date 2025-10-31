"""
Validation utilities and progress tracking for FollowWeb.

This module contains validation functions and progress tracking utilities.
"""

import logging
import time
from typing import Any, List, Optional, Union


class ProgressTracker:
    """
    Simple progress tracker for long-running operations.
    """

    def __init__(self, total: int, title: str = "Processing", logger: Optional[logging.Logger] = None):
        """
        Initialize the progress tracker.

        Args:
            total: Total number of items to process
            title: Title for the progress display
            logger: Logger instance for output
        """
        self.total = total
        self.title = title
        self.logger = logger or logging.getLogger(__name__)
        self.current = 0
        self.start_time = None

    def __enter__(self):
        """Enter context manager."""
        self.start_time = time.time()
        self.logger.info(f"Starting {self.title}...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self.start_time:
            duration = time.time() - self.start_time
            self.logger.info(f"Completed {self.title} in {duration:.2f} seconds")

    def update(self, current: int):
        """
        Update the progress.

        Args:
            current: Current progress value
        """
        self.current = current
        if self.total > 0:
            percentage = (current / self.total) * 100
            if current % max(1, self.total // 10) == 0:  # Log every 10%
                self.logger.debug(f"{self.title}: {percentage:.1f}% ({current}/{self.total})")


def validate_non_empty_string(value: Any, param_name: str) -> str:
    """
    Validate that a parameter is a non-empty string.

    Args:
        value: Value to validate
        param_name: Name of the parameter for error messages

    Returns:
        str: The validated string value

    Raises:
        ValueError: If value is not a non-empty string
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{param_name} must be a non-empty string")
    return value


def validate_positive_integer(value: Any, param_name: str) -> int:
    """
    Validate that a parameter is a positive integer.

    Args:
        value: Value to validate
        param_name: Name of the parameter for error messages

    Returns:
        int: The validated integer value

    Raises:
        ValueError: If value is not a positive integer
    """
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{param_name} must be a positive integer")
    return value


def validate_non_negative_integer(value: Any, param_name: str) -> int:
    """
    Validate that a parameter is a non-negative integer.

    Args:
        value: Value to validate
        param_name: Name of the parameter for error messages

    Returns:
        int: The validated integer value

    Raises:
        ValueError: If value is not a non-negative integer
    """
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{param_name} cannot be negative")
    return value


def validate_positive_number(value: Any, param_name: str) -> Union[int, float]:
    """
    Validate that a parameter is a positive number (int or float).

    Args:
        value: Value to validate
        param_name: Name of the parameter for error messages

    Returns:
        Union[int, float]: The validated number value

    Raises:
        ValueError: If value is not a positive number
    """
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{param_name} must be positive")
    return value


def validate_non_negative_number(value: Any, param_name: str) -> Union[int, float]:
    """
    Validate that a parameter is a non-negative number (int or float).

    Args:
        value: Value to validate
        param_name: Name of the parameter for error messages

    Returns:
        Union[int, float]: The validated number value

    Raises:
        ValueError: If value is not a non-negative number
    """
    if not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{param_name} cannot be negative")
    return value


def validate_range(
    value: Any, param_name: str, min_val: Union[int, float], max_val: Union[int, float]
) -> Union[int, float]:
    """
    Validate that a parameter is within a specified range.

    Args:
        value: Value to validate
        param_name: Name of the parameter for error messages
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)

    Returns:
        Union[int, float]: The validated value

    Raises:
        ValueError: If value is not within the specified range
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"{param_name} must be a number")

    if not (min_val <= value <= max_val):
        raise ValueError(f"{param_name} must be between {min_val} and {max_val}")

    return value


def validate_choice(value: Any, param_name: str, valid_choices: List[Any]) -> Any:
    """
    Validate that a parameter is one of the allowed choices.

    Args:
        value: Value to validate
        param_name: Name of the parameter for error messages
        valid_choices: List of valid choices

    Returns:
        Any: The validated value

    Raises:
        ValueError: If value is not in the list of valid choices
    """
    if value not in valid_choices:
        raise ValueError(
            f"Invalid {param_name} '{value}'. Must be one of: {valid_choices}"
        )
    return value


def validate_multiple_non_negative(*values_and_names) -> None:
    """
    Validate that multiple values are non-negative.

    Args:
        *values_and_names: Pairs of (value, name) tuples

    Raises:
        ValueError: If any value is negative
    """
    for value, name in values_and_names:
        if value < 0:
            raise ValueError(f"{name} cannot be negative")


def validate_path_string(value: Any, param_name: str) -> str:
    """
    Validate that a parameter is a valid path string.

    Args:
        value: Value to validate
        param_name: Name of the parameter for error messages

    Returns:
        str: The validated path string

    Raises:
        ValueError: If value is not a valid path string
    """
    if not value:
        raise ValueError(f"{param_name} cannot be empty")

    if not isinstance(value, str):
        raise ValueError(f"{param_name} must be a string")

    return value