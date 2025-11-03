"""
Exception classes for FollowWeb network analysis.

This module contains custom exception classes for different types of errors
that can occur during FollowWeb analysis operations.

Copied from Package/FollowWeb_Visualizor/utils.py
"""


class FollowWebError(Exception):
    """Base exception class for FollowWeb-specific errors."""

    pass


class ConfigurationError(FollowWebError):
    """Raised when configuration validation fails."""

    pass


class DataProcessingError(FollowWebError):
    """Raised when data processing operations fail."""

    pass


class VisualizationError(FollowWebError):
    """Raised when visualization generation fails."""

    pass
