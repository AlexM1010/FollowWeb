"""
Main module for FollowWeb - imports from __main__ for compatibility.

This module provides a standard import path for the PipelineOrchestrator
and main function, which are actually defined in __main__.py.
"""

from .__main__ import (
    PipelineOrchestrator,
    create_argument_parser,
    load_config_from_file,
    main,
    setup_logging,
)

__all__ = [
    "PipelineOrchestrator",
    "create_argument_parser",
    "load_config_from_file",
    "main",
    "setup_logging",
]
