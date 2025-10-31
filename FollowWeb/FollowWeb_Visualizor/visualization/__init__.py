"""
Visualization layer for FollowWeb network analysis.

This module provides visualization components for both interactive HTML and static PNG outputs.
It includes metric calculation, rendering, and legend generation functionality.
"""

from .metrics import MetricsCalculator, NodeMetric, EdgeMetric, ColorScheme, VisualizationMetrics
from .renderers import InteractiveRenderer, StaticRenderer
from .legends import LegendGenerator
from .colors import get_community_colors, get_scaled_size

__all__ = [
    "MetricsCalculator",
    "NodeMetric", 
    "EdgeMetric",
    "ColorScheme",
    "VisualizationMetrics",
    "InteractiveRenderer",
    "StaticRenderer", 
    "LegendGenerator",
    "get_community_colors",
    "get_scaled_size",
]