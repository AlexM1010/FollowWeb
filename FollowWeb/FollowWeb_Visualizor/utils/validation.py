"""
Validation utilities and progress tracking for FollowWeb.

This module contains validation functions and progress tracking utilities.
"""

import logging
import time
from typing import Optional


class ProgressTracker:
    """
    Simple progress tracker for long-running operations.
    """

    def __init__(self, total: int, title: str = "Processing", logger: Optional[logging.Logger] = None):
        """
        Initialize the progress tracker.

        Args:
            total: Total number of items to process
            title: Title for the progress display
            logger: Logger instance for output
        """
        self.total = total
        self.title = title
        self.logger = logger or logging.getLogger(__name__)
        self.current = 0
        self.start_time = None

    def __enter__(self):
        """Enter context manager."""
        self.start_time = time.time()
        self.logger.info(f"Starting {self.title}...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self.start_time:
            duration = time.time() - self.start_time
            self.logger.info(f"Completed {self.title} in {duration:.2f} seconds")

    def update(self, current: int):
        """
        Update the progress.

        Args:
            current: Current progress value
        """
        self.current = current
        if self.total > 0:
            percentage = (current / self.total) * 100
            if current % max(1, self.total // 10) == 0:  # Log every 10%
                self.logger.debug(f"{self.title}: {percentage:.1f}% ({current}/{self.total})")