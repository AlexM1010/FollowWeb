"""
Progress tracking utilities for FollowWeb Network Analysis.

This module provides progress tracking functionality for long-running operations:
- Animated progress bars with time estimation
- Context manager support for automatic completion
- Intelligent update frequency based on total items
- Linear time estimation and countdown display

Classes:
    ProgressTracker: Animated progress tracking with linear time estimation
"""

import logging
import time
from typing import Optional

from ..output.formatters import EmojiFormatter
from .validation import validate_positive_integer


class ProgressTracker:
    """
    A utility class for animated progress tracking with linear time estimation.

    Features:
    - Animated progress bar with random blocks
    - Simple linear time estimation and countdown display
    - Context manager support for automatic completion
    - Intelligent update frequency based on total items

    Usage:
        # Basic usage
        tracker = ProgressTracker(total=1000, title="Processing items")
        for i in range(1000):
            tracker.update(i + 1)
        tracker.complete()

        # Context manager usage (automatic completion)
        with ProgressTracker(total=1000, title="Processing items") as tracker:
            for i in range(1000):
                tracker.update(i + 1)

        # Chunked tasks
        with ProgressTracker(total=50, title="Processing chunks") as tracker:
            for i in range(50):
                # ... do work ...
                tracker.update(i + 1)
    """

    @staticmethod
    def _format_time(seconds: float) -> str:
        """
        Convert seconds to human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            str: Formatted time string
        """
        if seconds < 60.0:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        remaining_sec = int(seconds % 60)
        if minutes < 60:
            return f"{minutes}m {remaining_sec}s"
        hours = minutes // 60
        remaining_min = minutes % 60
        return f"{hours}h {remaining_min}m"

    def __init__(
        self,
        total: int,
        title: str,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the progress tracker with animated progress and countdown.

        Args:
            total: Total number of items/chunks to process (must be positive)
            title: Descriptive title to display for the operation
            logger: Optional logger instance for centralized logging

        Raises:
            ValueError: If total <= 0
        """
        validate_positive_integer(total, "total")

        self.total = total
        self.title = title
        self.logger = logger or logging.getLogger(__name__)
        self.update_every_n = max(1, min(self.total // 10, 500))
        self.start_time = time.perf_counter()
        self.last_printed_item = -1
        self.last_animation_update = 0

        # Time estimation attributes
        self.estimated_total = None

        # Animation attributes
        self.bar_width = 30
        self.current_line_length = 0
        self.completion_message = None

        # Initialize random bar state
        import random

        self.random = random.Random()
        self.bar_state = [False] * self.bar_width

        # Log start
        self.logger.info(f"{self.title}...")

    def __enter__(self) -> "ProgressTracker":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Context manager exit with cleanup."""
        self.complete()
        return False

    def _render_animation(self) -> None:
        """Render the animated progress bar."""
        elapsed = time.perf_counter() - self.start_time

        # Randomly toggle some blocks
        num_changes = self.random.randint(1, max(1, self.bar_width // 4))
        for _ in range(num_changes):
            pos = self.random.randint(0, self.bar_width - 1)
            if self.random.random() < 0.7:
                self.bar_state[pos] = True
            else:
                self.bar_state[pos] = False

        # Create the animated bar
        bar_display = "".join("█" if is_on else "░" for is_on in self.bar_state)

        # Show percentage and countdown when estimate is available
        if self.estimated_total and self.estimated_total > elapsed:
            remaining = max(0, self.estimated_total - elapsed)
            remaining_str = self._format_time(remaining)
            percent_complete = min(100, (elapsed / self.estimated_total) * 100)
            progress_line = f"    Progress: [{percent_complete:.0f}%] [{bar_display}] - Est. {remaining_str} remaining"
        else:
            elapsed_str = self._format_time(elapsed)
            progress_line = (
                f"    Progress: [??%] [{bar_display}] - Running for {elapsed_str}"
            )

        # Clear previous line and show new animation state
        if self.current_line_length > 0:
            print("\r" + " " * self.current_line_length + "\r", end="", flush=True)

        print(progress_line, end="", flush=True)
        self.current_line_length = len(progress_line)

    def _calculate_time_estimate(self, current_item: int, elapsed: float) -> float:
        """
        Calculate time estimate for completion using linear extrapolation.

        Args:
            current_item: Current item number being processed
            elapsed: Elapsed time in seconds

        Returns:
            float: Estimated total time in seconds
        """
        if current_item <= 0:
            return elapsed

        # Linear estimation: total_time = elapsed / (current_item / total)
        rate_per_item = elapsed / current_item
        estimated_total = rate_per_item * self.total

        return estimated_total

    def update(self, current_item: int) -> None:
        """
        Call this inside the loop with the current item count (1-based).
        Shows random loading bar immediately, then adds countdown when estimate is available.

        Args:
            current_item: Current iteration number (1-based) or chunk number

        Raises:
            ValueError: If current_item is negative
        """
        if current_item < 0:
            raise ValueError("Current item cannot be negative")

        # Early return for items that won't trigger updates
        if current_item <= self.last_printed_item and current_item < self.total:
            return

        is_last_item = current_item >= self.total
        is_update_step = current_item % self.update_every_n == 0

        # Update time estimate on every significant update
        if (is_update_step and current_item > 0) or is_last_item or current_item == 1:
            elapsed = time.perf_counter() - self.start_time
            self.estimated_total = self._calculate_time_estimate(current_item, elapsed)
            self.last_printed_item = current_item

        # Update animation every 300ms
        current_time = time.perf_counter()
        if current_time - self.last_animation_update > 0.3:
            self._render_animation()
            self.last_animation_update = current_time

    def complete(self) -> None:
        """Call after the loop finishes. Shows final progress state with completion time."""
        elapsed = time.perf_counter() - self.start_time
        elapsed_str = self._format_time(elapsed)

        # Create final progress bar (all blocks filled)
        final_bar = "█" * self.bar_width
        final_progress = (
            f"    Progress: [100%] [{final_bar}] - Completed in {elapsed_str}"
        )

        # Clear previous line and print final progress with newline
        if self.current_line_length > 0:
            print("\r" + " " * self.current_line_length + "\r", end="", flush=True)

        print(final_progress, flush=True)

        # Store completion message
        try:
            self.completion_message = EmojiFormatter.format(
                "timer", f"{self.title} completed in {elapsed_str}"
            )
        except (UnicodeEncodeError, ImportError):
            self.completion_message = f"[TIME] {self.title} completed in {elapsed_str}"

        if self.completion_message:
            # Log completion message through centralized logging
            self.logger.info(self.completion_message)
            # Add spacing after timer message for consistent formatting
            self.logger.info("")

    def reset(self, total: Optional[Optional[int]] = None) -> None:
        """
        Reset the tracker to start a new task (useful for reuse).

        Args:
            total: New total count (optional, keeps existing if not provided)
        """
        if total is not None:
            if total <= 0:
                raise ValueError("Total must be positive")
            self.total = total

        # Reset all tracking variables
        self.start_time = time.perf_counter()
        self.last_printed_item = -1
        self.last_animation_update = 0
        self.update_every_n = max(1, min(self.total // 10, 100))
        self.estimated_total = None
        self.bar_state = [False] * self.bar_width
        self.current_line_length = 0
        self.completion_message = None

        # Log start
        self.logger.info(f"{self.title}...")


__all__ = ["ProgressTracker"]
