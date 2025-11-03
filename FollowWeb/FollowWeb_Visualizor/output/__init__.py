"""
Output system for FollowWeb network analysis.

This module provides unified output management including:
- Output managers for coordinating all output generation
- Unified logging system for console and file output
- Emoji formatters for consistent message formatting
"""

from .formatters import EmojiFormatter, format_error, format_progress, format_success
from .logging import Logger, OutputConfig
from .managers import MetricsReporter, OutputManager

__all__ = [
    "EmojiFormatter",
    "format_success",
    "format_error",
    "format_progress",
    "Logger",
    "OutputConfig",
    "OutputManager",
    "MetricsReporter",
]
