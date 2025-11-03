"""
Unified logging system for FollowWeb network analysis.

This module provides a unified logging system that writes to both console and text file
simultaneously, integrating with emoji formatting and user-configurable fallback levels.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, TextIO

from .formatters import EmojiFormatter


@dataclass
class OutputConfig:
    """Configuration for unified output system."""

    # Output destinations
    console_output: bool = True
    text_file_output: bool = True

    # Content organization
    merge_duplicate_content: bool = True
    organize_by_sections: bool = True
    include_emojis_in_text: bool = True

    # Logging strategy
    simultaneous_logging: bool = True  # Log to both at same time
    chunk_logging: bool = False  # Log in organized chunks
    end_logging: bool = False  # Log entire output at end

    # Content preservation
    preserve_console_formatting: bool = True
    preserve_timing_info: bool = True
    preserve_progress_updates: bool = True

    # File handling
    text_file_path: Optional[Optional[str]] = None
    append_mode: bool = False


class Logger:
    """
    Unified logging system that writes to both console and text file simultaneously.

    This class integrates with the existing emoji_utils.py system and provides
    user-configurable emoji fallback levels for both console and .txt output.
    """

    def __init__(self, config: OutputConfig) -> None:
        """
        Initialize unified logger with configuration.

        Args:
            config: OutputConfig instance with logging settings
        """
        self.config = config
        self.console_logger = logging.getLogger(__name__)
        self.text_file_handle: Optional[Optional[TextIO]] = None
        self.content_buffer: List[str] = []
        self.section_data: Dict[str, List[str]] = {}
        self.current_section: Optional[Optional[str]] = None

        # Initialize text file if enabled
        if self.config.text_file_output and self.config.text_file_path:
            self._initialize_text_file()

    def _initialize_text_file(self) -> None:
        """Initialize text file for writing."""
        if not self.config.text_file_path:
            return

        try:
            # Create directory if needed (always create directories)
            os.makedirs(os.path.dirname(self.config.text_file_path), exist_ok=True)

            # Open file in appropriate mode
            mode = "a" if self.config.append_mode else "w"
            self.text_file_handle = open(
                self.config.text_file_path, mode, encoding="utf-8"
            )

            # Write header if not appending
            if not self.config.append_mode:
                self._write_file_header()

        except Exception as e:
            self.console_logger.error(f"Failed to initialize text file: {e}")
            self.config.text_file_output = False
            # Ensure any partially opened file handle is properly closed
            if hasattr(self, "text_file_handle") and self.text_file_handle:
                try:
                    self.text_file_handle.close()
                except BaseException:
                    pass
            self.text_file_handle = None

    def _write_file_header(self) -> None:
        """Write header to text file."""
        if not self.text_file_handle:
            return

        header = f"""# FollowWeb Network Analysis - Unified Output Log
# Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}
# Emoji Level: {EmojiFormatter.get_fallback_level()}

"""
        self.text_file_handle.write(header)
        self.text_file_handle.flush()

    def _format_for_text_file(self, message: str) -> str:
        """
        Format message for text file output.

        Args:
            message: Original message

        Returns:
            Formatted message for text file
        """
        if not self.config.include_emojis_in_text:
            # Strip emojis for text file if disabled
            # This would require more complex emoji detection/removal
            # For now, we'll rely on emoji fallback levels
            pass

        # Clean up console-specific formatting
        formatted = message.replace("\r", "")  # Remove carriage returns

        # Add timestamp if preserving timing info
        if self.config.preserve_timing_info:
            timestamp = time.strftime("%H:%M:%S")
            formatted = f"[{timestamp}] {formatted}"

        return formatted

    def info(self, message: str, section: Optional[Optional[str]] = None) -> None:
        """
        Log info message to both console and text file.

        Args:
            message: Message to log
            section: Optional section name for organization
        """
        self._log_unified(message, logging.INFO, section)

    def error(self, message: str, section: Optional[Optional[str]] = None) -> None:
        """
        Log error message to both console and text file.

        Args:
            message: Error message to log
            section: Optional section name for organization
        """
        self._log_unified(message, logging.ERROR, section)

    def warning(self, message: str, section: Optional[Optional[str]] = None) -> None:
        """
        Log warning message to both console and text file.

        Args:
            message: Warning message to log
            section: Optional section name for organization
        """
        self._log_unified(message, logging.WARNING, section)

    def debug(self, message: str, section: Optional[Optional[str]] = None) -> None:
        """
        Log debug message to both console and text file.

        Args:
            message: Debug message to log
            section: Optional section name for organization
        """
        self._log_unified(message, logging.DEBUG, section)

    def _log_unified(
        self, message: str, level: int, section: Optional[Optional[str]] = None
    ) -> None:
        """
        Internal method to log to both console and text file.

        Args:
            message: Message to log
            level: Logging level
            section: Optional section name
        """
        # Log to console if enabled
        if self.config.console_output:
            self.console_logger.log(level, message)

        # Handle text file logging based on strategy
        if self.config.text_file_output:
            if self.config.simultaneous_logging:
                self._write_to_text_file(message, section)
            elif self.config.chunk_logging or self.config.end_logging:
                self._buffer_message(message, section)

    def _write_to_text_file(
        self, message: str, section: Optional[Optional[str]] = None
    ) -> None:
        """
        Write message directly to text file.

        Args:
            message: Message to write
            section: Optional section name
        """
        if not self.text_file_handle:
            return

        try:
            formatted_message = self._format_for_text_file(message)

            # Add section header if new section
            if section and section != self.current_section:
                if self.current_section is not None:
                    self.text_file_handle.write("\n")
                self.text_file_handle.write(f"## {section}\n\n")
                self.current_section = section

            self.text_file_handle.write(formatted_message + "\n")
            self.text_file_handle.flush()

        except Exception as e:
            self.console_logger.error(f"Failed to write to text file: {e}")

    def _buffer_message(
        self, message: str, section: Optional[Optional[str]] = None
    ) -> None:
        """
        Buffer message for later writing.

        Args:
            message: Message to buffer
            section: Optional section name
        """
        formatted_message = self._format_for_text_file(message)

        if section:
            if section not in self.section_data:
                self.section_data[section] = []
            self.section_data[section].append(formatted_message)
        else:
            self.content_buffer.append(formatted_message)

    def start_section(self, section_name: str) -> None:
        """
        Start a new section for organized logging.

        Args:
            section_name: Name of the section
        """
        self.current_section = section_name

        if self.config.organize_by_sections:
            section_header = f"\n{'=' * 50}\n{section_name.upper()}\n{'=' * 50}"
            self.info(section_header, section_name)

    def end_section(self) -> None:
        """End the current section."""
        if self.current_section and self.config.organize_by_sections:
            self.info("")  # Add spacing after section
        self.current_section = None

    def flush_buffer(self) -> None:
        """Flush buffered content to text file."""
        if not self.text_file_handle or not (self.content_buffer or self.section_data):
            return

        try:
            # Write buffered content
            for message in self.content_buffer:
                self.text_file_handle.write(message + "\n")

            # Write sectioned content
            for section_name, messages in self.section_data.items():
                self.text_file_handle.write(f"\n## {section_name}\n\n")
                for message in messages:
                    self.text_file_handle.write(message + "\n")

            self.text_file_handle.flush()

            # Clear buffers
            self.content_buffer.clear()
            self.section_data.clear()

        except Exception as e:
            self.console_logger.error(f"Failed to flush buffer to text file: {e}")

    def log_emoji_formatted(
        self,
        emoji_key: str,
        message: str,
        level: int = logging.INFO,
        section: Optional[Optional[str]] = None,
    ) -> None:
        """
        Log message with emoji formatting using existing emoji_utils.

        Args:
            emoji_key: Key from EmojiFormatter.EMOJIS dictionary
            message: Message to format and log
            level: Logging level
            section: Optional section name
        """
        formatted_message = EmojiFormatter.format(emoji_key, message)
        self._log_unified(formatted_message, level, section)

    def log_success(
        self, message: str, section: Optional[Optional[str]] = None
    ) -> None:
        """Log success message with emoji formatting."""
        self.log_emoji_formatted("success", message, logging.INFO, section)

    def log_error(self, message: str, section: Optional[Optional[str]] = None) -> None:
        """Log error message with emoji formatting."""
        self.log_emoji_formatted("error", message, logging.ERROR, section)

    def log_progress(
        self, message: str, section: Optional[Optional[str]] = None
    ) -> None:
        """Log progress message with emoji formatting."""
        self.log_emoji_formatted("progress", message, logging.INFO, section)

    def log_timer(self, message: str, section: Optional[Optional[str]] = None) -> None:
        """Log timer message with emoji formatting."""
        self.log_emoji_formatted("timer", message, logging.INFO, section)

    def log_completion(
        self, message: str, section: Optional[Optional[str]] = None
    ) -> None:
        """Log completion message with emoji formatting."""
        self.log_emoji_formatted("completion", message, logging.INFO, section)

    def close(self) -> None:
        """Close the unified logger and clean up resources."""
        # Flush any remaining buffered content
        if self.config.chunk_logging or self.config.end_logging:
            self.flush_buffer()

        # Close text file handle
        if self.text_file_handle:
            try:
                # Write footer
                footer = f"\n# Log completed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                self.text_file_handle.write(footer)
                self.text_file_handle.close()
            except Exception as e:
                self.console_logger.error(f"Failed to close text file: {e}")
            finally:
                self.text_file_handle = None

    def __del__(self) -> None:
        """Destructor to ensure resources are cleaned up."""
        if hasattr(self, "text_file_handle") and self.text_file_handle:
            try:
                self.text_file_handle.close()
            except BaseException:
                pass

    def __enter__(self) -> None:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
        return False
