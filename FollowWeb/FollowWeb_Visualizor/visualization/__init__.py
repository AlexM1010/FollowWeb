"""
Visualization layer for FollowWeb network analysis.

This module provides visualization components for both interactive HTML and static PNG outputs.
It includes metric calculation, rendering, and legend generation functionality.
"""

from .colors import get_community_colors, get_scaled_size
from .legends import LegendGenerator
from .metrics import (
    ColorScheme,
    EdgeMetric,
    MetricsCalculator,
    NodeMetric,
    VisualizationMetrics,
)
from .renderers import MatplotlibRenderer, PyvisRenderer, Renderer

__all__ = [
    "MetricsCalculator",
    "NodeMetric",
    "EdgeMetric",
    "ColorScheme",
    "VisualizationMetrics",
    "Renderer",
    "PyvisRenderer",
    "MatplotlibRenderer",
    "LegendGenerator",
    "get_community_colors",
    "get_scaled_size",
]
