"""
Mathematical utility functions for FollowWeb.

This module contains mathematical operations and formatting functions.
"""


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
    if seconds < 0:
        raise ValueError("Duration cannot be negative")

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