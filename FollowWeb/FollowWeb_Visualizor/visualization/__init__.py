"""
Visualization layer for FollowWeb network analysis.

This module provides visualization components for both interactive HTML and static PNG outputs.
It includes metric calculation, rendering, and legend generation functionality.
"""

from .color_palette import (
    NodeGroupColors,
    UIColors,
    darken_color,
    generate_extended_palette,
    hex_to_rgba,
    lighten_color,
)
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
    "NodeGroupColors",
    "UIColors",
    "darken_color",
    "lighten_color",
    "hex_to_rgba",
    "generate_extended_palette",
]
