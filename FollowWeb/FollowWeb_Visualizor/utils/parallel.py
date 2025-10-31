"""
Parallel processing utilities for FollowWeb.

This module contains utilities for managing parallel processing configurations.
"""

import logging
from typing import Any, Dict, Optional


class ParallelConfig:
    """
    Configuration for parallel processing operations.
    """

    def __init__(self, nx_parallel_enabled: bool = False):
        """
        Initialize parallel configuration.

        Args:
            nx_parallel_enabled: Whether NetworkX parallel processing is enabled
        """
        self.nx_parallel_enabled = nx_parallel_enabled


def get_analysis_parallel_config(graph_size: int) -> ParallelConfig:
    """
    Get parallel configuration for analysis operations.

    Args:
        graph_size: Size of the graph being processed

    Returns:
        ParallelConfig instance
    """
    # For now, return a simple configuration
    return ParallelConfig(nx_parallel_enabled=False)


def log_parallel_usage(config: ParallelConfig, logger: logging.Logger) -> None:
    """
    Log parallel processing configuration.

    Args:
        config: Parallel configuration
        logger: Logger instance
    """
    if config.nx_parallel_enabled:
        logger.debug("Using parallel processing")
    else:
        logger.debug("Using sequential processing")