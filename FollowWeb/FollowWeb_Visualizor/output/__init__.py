"""
Output system components for FollowWeb Network Analysis.

This module handles file output, logging, and reporting:
- Unified output coordination and file generation
- Console and file logging with progress tracking
- Output formatting and styling utilities

Modules:
    managers: OutputManager class and unified output coordination
    logging: Logger class and unified logging system
    formatters: EmojiFormatter and text formatting utilities
"""

from .formatters import EmojiFormatter

__all__ = [
    "EmojiFormatter",
]