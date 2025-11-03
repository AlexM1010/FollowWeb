"""
Legend generation module for FollowWeb visualization.

This module creates visualization legends for both HTML and PNG outputs,
including community colors, edge types, and scaling information.
"""

from typing import Any, Dict, Optional, Tuple

import networkx as nx

from ..core.types import VisualizationMetrics
from ..data.cache import get_cached_node_attributes
from .colors import get_community_colors
from .metrics import MetricsCalculator


class LegendGenerator:
    """
    Creates visualization legends for both HTML and PNG outputs.
    """

    def __init__(self, vis_config: Dict[str, Any]) -> None:
        """
        Initialize the legend generator with visualization configuration.

        Args:
            vis_config: Visualization configuration dictionary containing color schemes,
                       community settings, and legend display options

        Raises:
            KeyError: If required configuration keys are missing
        """
        self.vis_config = vis_config

    def _safe_format_number(self, value: float) -> str:
        """
        Safely format a number for display, handling edge cases gracefully.

        Args:
            value: Number to format

        Returns:
            Formatted number string
        """
        try:
            from ..utils.math import format_number_clean

            return format_number_clean(value)
        except Exception:
            # Fallback formatting if the utility function fails
            try:
                if isinstance(value, (int, float)) and not (
                    value != value
                ):  # Check for NaN
                    return f"{value:g}"
                else:
                    return "0"
            except Exception:
                return "0"

    def _format_edge_thickness_legend(
        self, edge_metrics: Dict[Tuple[str, str], Dict[str, Any]]
    ) -> str:
        """
        Create formatted edge thickness legend with actual weight ranges and thickness values for HTML files only.

        Args:
            edge_metrics: Pre-calculated edge metrics containing width and weight information

        Returns:
            HTML string for edge thickness legend section
        """
        if not edge_metrics:
            return '<div style="color: #666; font-style: italic;">No edge data available</div>'

        # Extract width and common neighbor data directly from pre-calculated metrics
        widths = [metrics["width"] for metrics in edge_metrics.values()]
        common_neighbor_counts = [
            metrics["common_neighbors"] for metrics in edge_metrics.values()
        ]

        # Calculate ranges directly without separate method
        min_width, max_width = min(widths), max(widths)
        (min_width + max_width) / 2
        min_weight, max_weight = (
            min(common_neighbor_counts),
            max(common_neighbor_counts),
        )
        (min_weight + max_weight) / 2

        legend_html = f"""
        <div style="margin-bottom: 5px;">
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <div style="width: 40px; height: {min_width:.1f}px; background: #c0c0c0; margin-right: 10px;"></div>
                <span style="font-size: 12px;">Thin: {self._safe_format_number(min_weight)} common neighbors</span>
            </div>
            <div style="display: flex; align-items: center;">
                <div style="width: 40px; height: {max_width:.1f}px; background: #c0c0c0; margin-right: 10px;"></div>
                <span style="font-size: 12px;">Thick: {self._safe_format_number(max_weight)} common neighbors</span>
            </div>
        </div>
        """

        return legend_html

    def _format_node_size_legend(
        self,
        graph: nx.DiGraph,
        shared_metrics: Optional[Optional[VisualizationMetrics]] = None,
    ) -> str:
        """
        Create formatted node size legend with actual diameter measurements and centrality ranges for HTML files only.

        Args:
            graph: The analyzed graph with node attributes
            shared_metrics: Pre-calculated metrics to avoid recalculation

        Returns:
            HTML string for node size legend section
        """
        if graph.number_of_nodes() == 0:
            return '<div style="color: #666; font-style: italic;">No node data available</div>'

        # Use provided shared metrics or calculate if not provided
        if shared_metrics is None:
            calculator = MetricsCalculator(self.vis_config)
            shared_metrics = calculator.calculate_all_metrics(graph)

        # Extract node metrics from shared metrics
        node_metrics = {}
        for node, node_metric in shared_metrics.node_metrics.items():
            node_metrics[node] = {
                "size": node_metric.size,
                "community": node_metric.community,
                "color_hex": node_metric.color_hex,
                "color_rgba": node_metric.color_rgba,
                "degree": node_metric.centrality_values["degree"],
                "betweenness": node_metric.centrality_values["betweenness"],
                "eigenvector": node_metric.centrality_values["eigenvector"],
            }

        if not node_metrics:
            return '<div style="color: #666; font-style: italic;">No node data available</div>'

        # Extract sizes and centrality values from calculated metrics
        sizes = [metrics["size"] for metrics in node_metrics.values()]
        node_size_metric = self.vis_config.get("node_size_metric", "degree")

        # Get centrality values based on the metric being used
        centrality_values = []
        for node in graph.nodes():
            attrs = graph.nodes[node]
            metric_value = attrs.get(node_size_metric, attrs.get("degree", 1))
            centrality_values.append(metric_value)

        # Calculate ranges directly
        min_size, max_size = min(sizes), max(sizes)
        (min_size + max_size) / 2
        min_centrality, max_centrality = min(centrality_values), max(centrality_values)
        (min_centrality + max_centrality) / 2

        # Get the metric name for display
        metric_display_name = node_size_metric.replace("_", " ").title()

        legend_html = f"""
        <div style="margin-bottom: 5px;">
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <div style="width: {min_size:.0f}px; height: {min_size:.0f}px; background: #808080; border-radius: 50%; margin-right: 10px;"></div>
                <span style="font-size: 12px;">Small: {metric_display_name} {self._safe_format_number(min_centrality)}</span>
            </div>
            <div style="display: flex; align-items: center;">
                <div style="width: {max_size:.0f}px; height: {max_size:.0f}px; background: #808080; border-radius: 50%; margin-right: 10px;"></div>
                <span style="font-size: 12px;">Large: {metric_display_name} {self._safe_format_number(max_centrality)}</span>
            </div>
        </div>
        """

        return legend_html

    def create_html_legend(
        self,
        graph: nx.DiGraph,
        edge_metrics: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None,
        shared_metrics: Optional[Optional[VisualizationMetrics]] = None,
    ) -> str:
        """
        Creates an HTML legend for the interactive visualization.

        Args:
            graph: The analyzed graph with node attributes
            edge_metrics: Pre-calculated edge metrics for accurate thickness scale
            shared_metrics: Pre-calculated metrics to avoid recalculation

        Returns:
            HTML string for the legend
        """
        # Get community information using cached attributes
        communities_attr = get_cached_node_attributes(graph, "community")
        if communities_attr:
            num_communities = len(set(communities_attr.values()))
        else:
            # Fallback if analysis was skipped
            num_communities = 0

        color_maps = get_community_colors(num_communities)
        color_map_hex = color_maps["hex"]

        # Check if a metric was calculated or defaulted
        node_size_metric = self.vis_config["node_size_metric"]
        if not communities_attr or node_size_metric == "degree":
            # Default metric for degree, or if analysis was skipped (will default to actual degree)
            pass
        else:
            node_size_metric.capitalize()

        # Create community legend items
        community_items = ""
        if num_communities > 0:
            for i in range(min(num_communities, 10)):  # Limit to first 10 communities
                color = color_map_hex.get(i, "#808080")
                community_items += f"""
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <div style="width: 20px; height: 20px; background-color: {color}; margin-right: 10px; border: 1px solid #ccc;"></div>
                    <span>Community {i}</span>
                </div>
                """

            if num_communities > 10:
                community_items += f'<div style="color: #666; font-style: italic;">...and {num_communities - 10} more communities</div>'
        else:
            community_items = '<div style="color: #666; font-style: italic;">(Community detection skipped or failed)</div>'

        legend_html = f"""
        <div id="legend" style="
            position: absolute;
            bottom: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid #ddd;
            padding: 18px;
            border-radius: 8px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 13px;
            max-width: 320px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            line-height: 1.4;
        ">
            <h3 style="margin-top: 0; margin-bottom: 16px; font-size: 17px; font-weight: 600; color: #333; border-bottom: 2px solid #f0f0f0; padding-bottom: 6px;">Legend</h3>

            <div style="margin-bottom: 16px;">
                <h4 style="margin-bottom: 8px; font-size: 14px; font-weight: 600; color: #444;">Communities</h4>
                {community_items}
            </div>

            <div style="margin-bottom: 16px;">
                <h4 style="margin-bottom: 8px; font-size: 14px; font-weight: 600; color: #444;">Edge Types</h4>
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <div style="width: 40px; height: 6px; background: #c0c0c0; margin-right: 10px;"></div>
                    <span>Mutual Connection</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <div style="width: 40px; height: 2px; background: #c0c0c0; margin-right: 10px; border: 1px dashed #666;"></div>
                    <span>One-way Connection</span>
                </div>
                <div style="display: flex; align-items: center;">
                    <div style="width: 40px; height: 2px; background: {self.vis_config.get("bridge_color", "#6e6e6e")}; margin-right: 10px;"></div>
                    <span>Bridge Connection</span>
                </div>
            </div>

            <div style="margin-bottom: 16px;">
                <h4 style="margin-bottom: 8px; font-size: 14px; font-weight: 600; color: #444;">Edge Thickness Scale</h4>
                {self._format_edge_thickness_legend(edge_metrics) if edge_metrics else '<div style="color: #666; font-style: italic;">Edge thickness data not available</div>'}
            </div>

            <div style="margin-bottom: 16px;">
                <h4 style="margin-bottom: 8px; font-size: 14px; font-weight: 600; color: #444;">Node Size Scale</h4>
                {self._format_node_size_legend(graph, shared_metrics)}
            </div>

            <div style="font-size: 12px; color: #666; border-top: 1px solid #f0f0f0; padding-top: 12px; margin-top: 4px;">
                <h4 style="margin: 0 0 6px 0; font-size: 13px; font-weight: 600; color: #555;">Interactions</h4>
                <div style="line-height: 1.3;">
                    • Click and drag to move nodes<br>
                    • Scroll to zoom in/out<br>
                    • Hover for node details<br>
                    • Drag background to pan
                </div>
            </div>
        </div>
        """

        return legend_html
