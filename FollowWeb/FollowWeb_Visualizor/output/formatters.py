"""
Emoji formatting system for FollowWeb network analysis.

This module provides centralized emoji formatting with configurable fallback levels
for consistent emoji usage throughout the application.
"""

from typing import Dict


class EmojiFormatter:
    """
    Centralized emoji formatter with configurable fallback levels.

    This class provides a single point of control for all emoji usage in the application,
    with user-configurable fallback levels from full emojis to plain text or no emojis.

    Fallback levels:
    - "full": Full Unicode emojis (✅, ❌, 🔄, etc.)
    - "simple": Simple ASCII symbols ([✓], [✗], [~], etc.)
    - "text": Plain text descriptions (SUCCESS, ERROR, PROGRESS, etc.)
    - "none": No emoji indicators (empty strings)
    """

    # Global configuration for emoji fallback level
    _fallback_level: str = "full"

    # Centralized emoji definitions with multiple fallback levels
    EMOJIS: Dict[str, Dict[str, str]] = {
        # Status and completion emojis
        "success": {"full": "✅", "simple": "[✓]", "text": "SUCCESS", "none": ""},
        "error": {"full": "❌", "simple": "[✗]", "text": "ERROR", "none": ""},
        "warning": {"full": "⚠️", "simple": "[!]", "text": "WARNING", "none": ""},
        "skipped": {"full": "⏭️", "simple": "[>>]", "text": "SKIPPED", "none": ""},
        # Progress and activity emojis
        "progress": {"full": "🔄", "simple": "[~]", "text": "PROGRESS", "none": ""},
        "timer": {"full": "⏱️", "simple": "[T]", "text": "TIME", "none": ""},
        "completion": {"full": "🎯", "simple": "[✓]", "text": "COMPLETE", "none": ""},
        "rocket": {"full": "🚀", "simple": "[>>]", "text": "START", "none": ""},
        # Analysis and data emojis
        "search": {"full": "🔍", "simple": "[?]", "text": "SEARCH", "none": ""},
        "chart": {"full": "📊", "simple": "[#]", "text": "DATA", "none": ""},
        "lightning": {"full": "⚡", "simple": "[*]", "text": "FAST", "none": ""},
    }

    @classmethod
    def set_fallback_level(cls, level: str) -> None:
        """
        Set the global emoji fallback level.

        Args:
            level: Fallback level ("full", "simple", "text", "none")

        Raises:
            ValueError: If level is not valid
        """
        valid_levels = ["full", "simple", "text", "none"]
        if level not in valid_levels:
            raise ValueError(
                f"Invalid fallback level '{level}'. Must be one of: {valid_levels}"
            )
        cls._fallback_level = level

    @classmethod
    def get_fallback_level(cls) -> str:
        """
        Get the current emoji fallback level.

        Returns:
            Current fallback level string
        """
        return cls._fallback_level

    @classmethod
    def format(cls, emoji_key: str, message: str) -> str:
        """
        Format message with emoji based on current fallback level.

        Args:
            emoji_key: Key from EMOJIS dictionary (e.g., 'success', 'error')
            message: Message to format

        Returns:
            Formatted message string with emoji based on fallback level

        Example:
            >>> EmojiFormatter.set_fallback_level("full")
            >>> EmojiFormatter.format('success', 'Task completed')
            '✅ Task completed'
            >>> EmojiFormatter.set_fallback_level("simple")
            >>> EmojiFormatter.format('success', 'Task completed')
            '[✓] Task completed'
        """
        if emoji_key not in cls.EMOJIS:
            # If emoji key doesn't exist, just return the message
            return message

        emoji_options = cls.EMOJIS[emoji_key]
        emoji = emoji_options.get(cls._fallback_level, emoji_options.get("text", ""))

        # If emoji is empty (none level), just return the message
        if not emoji:
            return message

        return f"{emoji} {message}"

    @classmethod
    def get_emoji(cls, emoji_key: str) -> str:
        """
        Get just the emoji character (or fallback) without formatting a message.

        Args:
            emoji_key: Key from EMOJIS dictionary

        Returns:
            Emoji character based on current fallback level
        """
        if emoji_key not in cls.EMOJIS:
            return ""

        emoji_options = cls.EMOJIS[emoji_key]
        return emoji_options.get(cls._fallback_level, emoji_options.get("text", ""))

    @classmethod
    def safe_print(cls, emoji_key: str, message: str) -> None:
        """
        Print message with emoji based on current fallback level.

        Args:
            emoji_key: Key from EMOJIS dictionary
            message: Message to print
        """
        formatted_message = cls.format(emoji_key, message)
        print(formatted_message)


# Convenience functions for common emoji usage patterns
def format_success(message: str) -> str:
    """Format success message with ✅ emoji."""
    return EmojiFormatter.format("success", message)


def format_error(message: str) -> str:
    """Format error message with ❌ emoji."""
    return EmojiFormatter.format("error", message)


def format_progress(message: str) -> str:
    """Format progress message with 🔄 emoji."""
    return EmojiFormatter.format("progress", message)


def format_timer(message: str) -> str:
    """Format timer message with ⏱️ emoji."""
    return EmojiFormatter.format("timer", message)


def format_completion(message: str) -> str:
    """Format completion message with 🎯 emoji."""
    return EmojiFormatter.format("completion", message)


def safe_print_success(message: str) -> None:
    """Print success message with safe emoji handling."""
    EmojiFormatter.safe_print("success", message)


def safe_print_error(message: str) -> None:
    """Print error message with safe emoji handling."""
    EmojiFormatter.safe_print("error", message)
