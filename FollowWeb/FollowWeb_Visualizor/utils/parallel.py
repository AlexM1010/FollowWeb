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

    def __init__(self, nx_parallel_enabled: bool = False, cores_used: int = 1, operation_type: str = "analysis"):
        """
        Initialize parallel configuration.

        Args:
            nx_parallel_enabled: Whether NetworkX parallel processing is enabled
            cores_used: Number of cores to use
            operation_type: Type of operation being performed
        """
        self.nx_parallel_enabled = nx_parallel_enabled
        self.cores_used = cores_used
        self.operation_type = operation_type


def get_analysis_parallel_config(graph_size: int) -> ParallelConfig:
    """
    Get parallel configuration for analysis operations.

    Args:
        graph_size: Size of the graph being processed

    Returns:
        ParallelConfig instance
    """
    # For now, return a simple configuration
    return ParallelConfig(nx_parallel_enabled=False, cores_used=1, operation_type="analysis")


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


def get_nx_parallel_status_message() -> str:
    """
    Get user-friendly nx-parallel status message.
    
    Returns:
        Status message string
    """
    return "nx-parallel not available - using standard NetworkX algorithms"


def is_nx_parallel_available() -> bool:
    """
    Check if nx-parallel is available and working.
    
    Returns:
        False for now (simplified implementation)
    """
    return False