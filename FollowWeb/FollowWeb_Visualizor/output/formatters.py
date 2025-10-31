"""
Text formatting utilities for FollowWeb output.

This module contains formatters for console output and logging.
"""

import logging


class EmojiFormatter:
    """
    Formatter for adding emojis and styling to console output.
    """

    @staticmethod
    def format(message_type: str, message: str) -> str:
        """
        Format a message with appropriate emoji and styling.

        Args:
            message_type: Type of message (progress, success, error, etc.)
            message: The message to format

        Returns:
            Formatted message string
        """
        emoji_map = {
            "progress": "🔄",
            "success": "✅", 
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
        }
        
        emoji = emoji_map.get(message_type, "")
        if emoji:
            return f"{emoji} {message}"
        return message