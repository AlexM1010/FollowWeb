"""
Renderers package for FollowWeb visualization.

This package provides abstract and concrete renderer implementations for generating
network visualizations in various formats (HTML, PNG, etc.).
"""

from .base import Renderer
from .matplotlib import MatplotlibRenderer
from .pyvis import PyvisRenderer

__all__ = ["Renderer", "MatplotlibRenderer", "PyvisRenderer"]
