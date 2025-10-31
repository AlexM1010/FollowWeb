"""
Core foundation components for FollowWeb Network Analysis.

This module contains essential functionality required for basic package operation:
- Custom exception classes and error hierarchy
- Type definitions and data structures
- Configuration management and validation

Modules:
    exceptions: Custom exception classes (FollowWebError hierarchy)
    types: Type definitions (NodeMetric, EdgeMetric, ColorScheme, etc.)
    config: Configuration management (FollowWebConfig and related classes)
"""

# Import all core components for easy access
from .exceptions import (
    FollowWebError,
    ConfigurationError,
    DataProcessingError,
    VisualizationError,
)

from .types import (
    NodeMetric,
    EdgeMetric,
    ColorScheme,
    VisualizationMetrics,
)

from .config import (
    AnalysisMode,
    PipelineStagesConfig,
    AnalysisModeConfig,
    EmojiConfig,
    OutputFormattingConfig,
    OutputControlConfig,
    KValueConfig,
    SpringLayoutConfig,
    KamadaKawaiLayoutConfig,
    CircularLayoutConfig,
    ShellLayoutConfig,
    PngLayoutConfig,
    StaticImageConfig,
    PyvisInteractiveConfig,
    PipelineConfig,
    AnalysisConfig,
    FameAnalysisConfig,
    OutputConfig,
    VisualizationConfig,
    FollowWebConfig,
    load_config_from_dict,
)

__all__ = [
    # Exceptions
    "FollowWebError",
    "ConfigurationError", 
    "DataProcessingError",
    "VisualizationError",
    # Types
    "NodeMetric",
    "EdgeMetric", 
    "ColorScheme",
    "VisualizationMetrics",
    # Config classes
    "AnalysisMode",
    "PipelineStagesConfig",
    "AnalysisModeConfig",
    "EmojiConfig",
    "OutputFormattingConfig",
    "OutputControlConfig",
    "KValueConfig",
    "SpringLayoutConfig",
    "KamadaKawaiLayoutConfig",
    "CircularLayoutConfig",
    "ShellLayoutConfig",
    "PngLayoutConfig",
    "StaticImageConfig",
    "PyvisInteractiveConfig",
    "PipelineConfig",
    "AnalysisConfig",
    "FameAnalysisConfig",
    "OutputConfig",
    "VisualizationConfig",
    "FollowWebConfig",
    "load_config_from_dict",
]