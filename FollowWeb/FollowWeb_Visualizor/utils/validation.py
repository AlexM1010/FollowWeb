"""
Input validation utilities for FollowWeb network analysis.

This module provides comprehensive validation functions for parameters,
file paths, and configuration values used throughout the FollowWeb package.
"""

# Standard library imports
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Union

# Local imports


class ValidationErrorHandler:
    """Handles validation error patterns consistently."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """Initialize validation error handler."""
        self.logger = logger or logging.getLogger(__name__)

    def collect_validation_errors(
        self, validators: List[Callable[[], str]]
    ) -> List[str]:
        """
        Collect all validation errors.

        Args:
            validators: List of validation functions to execute

        Returns:
            List of validation error messages
        """
        errors = []

        for validator in validators:
            try:
                validator()
            except ValueError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append(f"Validation error: {e}")

        return errors

    def validate_with_context(
        self, validation_func: Callable[[], str], context: str
    ) -> Optional[str]:
        """
        Execute validation with context information.

        Args:
            validation_func: Validation function to execute
            context: Context description for error messages

        Returns:
            Error message if validation fails, None if successful
        """
        try:
            validation_func()
            return None
        except ValueError as e:
            error_msg = f"{context}: {e}"
            self.logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"{context} - unexpected error: {e}"
            self.logger.error(error_msg)
            return error_msg


class ConfigurationErrorHandler:
    """Handles configuration-related error patterns."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """Initialize configuration error handler."""
        self.logger = logger or logging.getLogger(__name__)

    def validate_configuration_section(
        self, config_dict: Dict, required_keys: List[str], section_name: str
    ) -> List[str]:
        """
        Validate that a configuration section has all required keys.

        Args:
            config_dict: Configuration dictionary to validate
            required_keys: List of required key names
            section_name: Name of the configuration section

        Returns:
            List of validation error messages
        """
        errors = []

        for key in required_keys:
            if key not in config_dict:
                errors.append(f"Missing required key '{key}' in {section_name} section")
            elif config_dict[key] is None:
                errors.append(f"Key '{key}' in {section_name} section cannot be None")

        return errors

    def handle_configuration_error(
        self, error: Exception, config_file: Optional[Optional[str]] = None
    ) -> str:
        """
        Handle configuration errors with helpful error messages.

        Args:
            error: The configuration error
            config_file: Optional configuration file path

        Returns:
            Formatted error message with suggestions
        """
        error_msg = str(error)

        if config_file:
            base_msg = f"Configuration error in {config_file}: {error_msg}"
        else:
            base_msg = f"Configuration error: {error_msg}"

        # Add helpful suggestions based on error type
        if "JSON" in error_msg or "json" in error_msg:
            base_msg += (
                "\nSuggestion: Check JSON syntax, ensure proper quotes and commas"
            )
        elif "required" in error_msg.lower():
            base_msg += (
                "\nSuggestion: Check that all required configuration parameters are set"
            )
        elif "invalid" in error_msg.lower():
            base_msg += "\nSuggestion: Check parameter values against documentation"

        self.logger.error(base_msg)
        return base_msg


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


def validate_string_format(
    value: Any, param_name: str, allowed_suffixes: Optional[Optional[List[str]]] = None
) -> str:
    """
    Validate string format with optional suffix requirements.

    Args:
        value: Value to validate
        param_name: Name of the parameter for error messages
        allowed_suffixes: Optional list of allowed suffixes (e.g., ['px', '%'])

    Returns:
        str: The validated string value

    Raises:
        ValueError: If value doesn't meet format requirements
    """
    if not isinstance(value, str):
        raise ValueError(f"{param_name} must be a string")

    if allowed_suffixes:
        if not any(value.endswith(suffix) for suffix in allowed_suffixes):
            raise ValueError(f"{param_name} must end with one of: {allowed_suffixes}")

    return value


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


def validate_filesystem_safe_string(value: Any, param_name: str) -> str:
    """
    Validate that a string is safe for filesystem usage.

    Args:
        value: Value to validate
        param_name: Name of the parameter for error messages

    Returns:
        str: The validated string value

    Raises:
        ValueError: If value contains invalid filesystem characters
    """
    # Ensure value is a string
    if not isinstance(value, str):
        raise ValueError(f"{param_name} must be a string, got {type(value).__name__}")

    if not value.strip():
        raise ValueError(f"{param_name} cannot be empty or whitespace-only")

    if not value.strip():
        raise ValueError(f"{param_name} cannot be empty or whitespace-only")

    # Invalid characters for most filesystems
    invalid_chars = '<>"|?*'
    if any(char in value for char in invalid_chars):
        raise ValueError(f"{param_name} contains invalid filesystem characters")

    return value


def validate_at_least_one_enabled(options: dict, param_name: str) -> dict:
    """
    Validate that at least one option in a dictionary is enabled (True).

    Args:
        options: Dictionary of option_name -> boolean values
        param_name: Name of the parameter group for error messages

    Returns:
        dict: The validated options dictionary

    Raises:
        ValueError: If no options are enabled
    """
    if not any(options.values()):
        enabled_options = list(options.keys())
        raise ValueError(
            f"At least one {param_name} must be enabled: {enabled_options}"
        )

    return options


def validate_k_value_dict(
    k_values: dict, param_name: str, valid_strategies: List[str]
) -> dict:
    """
    Validate a dictionary of k-values for different strategies.

    Args:
        k_values: Dictionary mapping strategy names to k-values
        param_name: Name of the parameter for error messages
        valid_strategies: List of valid strategy names

    Returns:
        dict: The validated k-values dictionary

    Raises:
        ValueError: If k-values are invalid or strategies are unknown
    """
    for strategy, k_val in k_values.items():
        if strategy not in valid_strategies:
            raise ValueError(
                f"Invalid strategy '{strategy}' in {param_name}. "
                f"Must be one of: {valid_strategies}"
            )

        validate_non_negative_integer(k_val, f"k-value for '{strategy}'")

    return k_values


def validate_ego_strategy_requirements(
    strategy: str, ego_username: Optional[str]
) -> None:
    """
    Validate requirements specific to ego-alter strategy.

    Args:
        strategy: The analysis strategy
        ego_username: The ego username (may be None)

    Raises:
        ValueError: If ego-alter strategy is used without ego_username
    """
    if strategy == "ego_alter_k-core" and not ego_username:
        raise ValueError(
            "'ego_username' must be set for 'ego_alter_k-core' strategy. "
            "Set ego_username in configuration file or use --ego-username CLI parameter"
        )


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


def validate_image_dimensions(width: int, height: int) -> tuple:
    """
    Validate image dimensions are positive integers.

    Args:
        width: Image width
        height: Image height

    Returns:
        tuple: (width, height) validated values

    Raises:
        ValueError: If dimensions are not positive
    """
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")

    return width, height


def validate_file_path(filepath: str, must_exist: bool = True) -> bool:
    """
    Validates file path and optionally checks if file exists.

    Args:
        filepath: Path to validate
        must_exist: If True, checks that file exists

    Returns:
        bool: True if valid, False otherwise

    Raises:
        ValueError: If filepath is empty
        FileNotFoundError: If must_exist=True and file doesn't exist
    """
    validate_path_string(filepath, "filepath")

    if must_exist and not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    return True
