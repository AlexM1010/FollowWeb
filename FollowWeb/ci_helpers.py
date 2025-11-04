#!/usr/bin/env python3
"""
CI Helper utilities for FollowWeb GitHub Actions workflow.

This module provides platform-aware emoji formatting and status reporting
for CI/CD pipelines using the existing EmojiFormatter system.
"""

import os
import platform
import sys
from pathlib import Path

# Add the FollowWeb_Visualizor package to the path
sys.path.insert(0, str(Path(__file__).parent / "FollowWeb_Visualizor"))

from FollowWeb_Visualizor.output.formatters import EmojiFormatter


def setup_ci_emoji_config():
    """
    Configure emoji fallback level based on CI environment and platform.
    
    Uses 'text' fallback for Windows to avoid encoding issues,
    'full' for other platforms.
    """
    # Detect if we're on Windows or in a CI environment that might have encoding issues
    is_windows = platform.system() == "Windows"
    is_ci = os.getenv("CI", "").lower() == "true"
    
    if is_windows and is_ci:
        # Use text fallbacks for Windows CI to avoid encoding issues
        EmojiFormatter.set_fallback_level("text")
    else:
        # Use full emojis for other platforms
        EmojiFormatter.set_fallback_level("full")


def ci_print_status(status_type: str, message: str):
    """
    Print a status message with appropriate emoji for CI environment.
    
    Args:
        status_type: Type of status ('success', 'error', 'progress', etc.)
        message: Message to display
    """
    setup_ci_emoji_config()
    formatted_message = EmojiFormatter.format(status_type, message)
    
    # Handle encoding issues on Windows by using safe printing
    try:
        print(formatted_message)
    except UnicodeEncodeError:
        # Fallback to text-only mode if encoding fails
        EmojiFormatter.set_fallback_level("text")
        formatted_message = EmojiFormatter.format(status_type, message)
        print(formatted_message)


def ci_print_success(message: str):
    """Print success message with platform-appropriate emoji."""
    ci_print_status("success", message)


def ci_print_error(message: str):
    """Print error message with platform-appropriate emoji."""
    ci_print_status("error", message)


def ci_print_progress(message: str):
    """Print progress message with platform-appropriate emoji."""
    ci_print_status("progress", message)


if __name__ == "__main__":
    # Command-line interface for CI scripts
    if len(sys.argv) < 3:
        print("Usage: python ci_helpers.py <status_type> <message>")
        print("Status types: success, error, progress, warning, etc.")
        sys.exit(1)
    
    status_type = sys.argv[1]
    message = " ".join(sys.argv[2:])
    ci_print_status(status_type, message)