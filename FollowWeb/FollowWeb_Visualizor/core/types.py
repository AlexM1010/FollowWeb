"""
Type definitions and data structures for FollowWeb network analysis.

This module contains dataclass definitions for visualization metrics,
color schemes, and other data structures used throughout the package.

Copied from Package/FollowWeb_Visualizor/visualization.py and config.py
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypeAlias

# Type alias for position coordinates (NetworkX uses numpy arrays)
PositionArray: TypeAlias = NDArray[np.floating]
PositionDict: TypeAlias = dict[str, PositionArray]


@dataclass
class NodeMetric:
    """
    Data structure for individual node visualization metrics.

    Attributes:
        size: Calculated node size for visualization
        color_hex: Hex color string for HTML visualization
        color_rgba: RGBA tuple for matplotlib visualization
        community: Community ID for the node
        centrality_values: Dictionary of centrality metrics (degree, betweenness, eigenvector)
    """

    size: float
    color_hex: str
    color_rgba: tuple[float, float, float, float]
    community: int
    centrality_values: dict[str, float]


@dataclass
class EdgeMetric:
    """
    Data structure for individual edge visualization metrics.

    Attributes:
        width: Calculated edge width for visualization
        color: Edge color (hex string)
        is_mutual: Whether the edge represents a mutual connection
        is_bridge: Whether the edge connects different communities
        common_neighbors: Number of common neighbors between the nodes
        u_comm: Community ID of the source node
        v_comm: Community ID of the target node
    """

    width: float
    color: str
    is_mutual: bool
    is_bridge: bool
    common_neighbors: int
    u_comm: int
    v_comm: int


@dataclass
class ColorScheme:
    """
    Data structure for color scheme information.

    Attributes:
        hex_colors: Dictionary mapping community ID to hex color
        rgba_colors: Dictionary mapping community ID to RGBA tuple
        bridge_color: Color for bridge edges
        intra_community_color: Color for intra-community edges
    """

    hex_colors: dict[int, str]
    rgba_colors: dict[int, tuple[float, float, float, float]]
    bridge_color: str
    intra_community_color: str


@dataclass
class VisualizationMetrics:
    """
    Complete visualization metrics for both HTML and PNG outputs.

    Attributes:
        node_metrics: Dictionary mapping node names to NodeMetric objects
        edge_metrics: Dictionary mapping edge tuples to EdgeMetric objects
        layout_positions: Dictionary mapping node names to (x, y) position tuples
        color_schemes: ColorScheme object with all color information
        graph_hash: Hash of the graph structure for cache validation
    """

    node_metrics: dict[str, NodeMetric]
    edge_metrics: dict[tuple[str, str], EdgeMetric]
    layout_positions: PositionDict
    color_schemes: ColorScheme
    graph_hash: str
