"""
Mathematical utility functions for FollowWeb network analysis.

This module provides mathematical operations, scaling algorithms, and
numerical utilities used throughout the FollowWeb package.
"""

# Standard library imports
import math

# Local imports
from .validation import validate_choice, validate_multiple_non_negative


def scale_value(
    value: float, base_size: float, multiplier: float, algorithm: str
) -> float:
    """
    Applies logarithmic or linear scaling to numeric values.

    Args:
        value: The value to scale
        base_size: Base size to add to the scaled result
        multiplier: Scaling multiplier
        algorithm: Scaling algorithm - 'logarithmic' or 'linear'

    Returns:
        float: Scaled value

    Raises:
        ValueError: If algorithm is not 'logarithmic' or 'linear'
        ValueError: If value, base_size, or multiplier is negative
    """
    validate_multiple_non_negative(
        (value, "value"), (base_size, "base_size"), (multiplier, "multiplier")
    )

    if algorithm == "logarithmic":
        # Use log1p (log(1+x)) to handle 0 values gracefully
        return base_size + math.log1p(value) * multiplier
    elif algorithm == "linear":
        return base_size + value * multiplier
    else:
        validate_choice(algorithm, "scaling algorithm", ["logarithmic", "linear"])


def get_scaled_size(
    value: float, base_size: float, multiplier: float, algorithm: str
) -> float:
    """
    Helper to calculate node/edge size based on a metric's value.

    Args:
        value: The metric value to scale
        base_size: Base size to add to the scaled result
        multiplier: Scaling multiplier
        algorithm: Scaling algorithm - 'logarithmic' or 'linear'

    Returns:
        float: Scaled size value

    Raises:
        ValueError: If algorithm is not 'logarithmic' or 'linear'
    """
    if algorithm == "logarithmic":
        # Use log1p (log(1+x)) to handle 0 values gracefully
        return base_size + math.log1p(value) * multiplier
    else:  # linear
        return base_size + value * multiplier


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divides two numbers, returning default value for division by zero.

    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Value to return if denominator is zero

    Returns:
        float: Result of division or default value
    """
    if denominator == 0:
        return default
    return numerator / denominator


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """
    Clamps a value between minimum and maximum bounds.

    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        float: Clamped value

    Raises:
        ValueError: If min_val > max_val
    """
    if min_val > max_val:
        raise ValueError("Minimum value cannot be greater than maximum value")

    return max(min_val, min(value, max_val))


def format_number_clean(value: float) -> str:
    """
    Format numbers without unnecessary decimal places using Python's built-in formatting.

    Uses the :g format specifier for most numbers, but keeps large integers
    in regular format for better readability in UI contexts.

    Args:
        value: Number to format

    Returns:
        str: Formatted number string
    """
    try:
        # Handle special values first
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"

        # For large whole numbers, use regular integer formatting for readability
        if abs(value) >= 1000000 and value == int(value):
            return str(int(value))

        # Use Python's built-in :g formatter which automatically:
        # - Removes trailing zeros
        # - Removes unnecessary decimal points
        # - Uses the shorter of %f and %e formats for smaller numbers
        return f"{value:g}"
    except (ValueError, TypeError, OverflowError):
        # Fallback for invalid input
        return "0"


def format_time_duration(seconds: float) -> str:
    """
    Format time duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted time string (e.g., "45.2 seconds" or "1 minute 8 seconds")

    Raises:
        ValueError: If seconds is negative
    """
    from .validation import validate_non_negative_number

    validate_non_negative_number(seconds, "duration")

    # For durations under 60 seconds, display in seconds with one decimal place
    if seconds < 60.0:
        return f"{seconds:.1f} seconds"

    # For durations over 60 seconds, display as "X minutes Y seconds"
    total_seconds = round(seconds)
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60

    if remaining_seconds == 0:
        if minutes == 1:
            return "1 minute"
        else:
            return f"{minutes} minutes"
    else:
        if minutes == 1:
            return f"1 minute {remaining_seconds} seconds"
        else:
            return f"{minutes} minutes {remaining_seconds} seconds"
