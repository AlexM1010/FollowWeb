"""
Abstract base class for visualization renderers.

This module defines the Renderer interface that all visualization renderers must implement.
It provides a standardized interface for generating visualizations from NetworkX graphs.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

import networkx as nx

from ...core.types import VisualizationMetrics


class Renderer(ABC):
    """
    Abstract base class for visualization renderers.
    
    This class defines the interface that all renderers must implement to generate
    visualizations from NetworkX graphs. Subclasses should implement the
    generate_visualization method to create their specific output format.
    
    The base class provides common functionality:
    - Metrics calculation with caching support
    - Empty graph validation
    - Metrics extraction to dictionary format
    """

    def __init__(self, vis_config: dict[str, Any]) -> None:
        """
        Initialize renderer with visualization configuration.

        Args:
            vis_config: Visualization configuration dictionary containing renderer-specific
                       settings, styling preferences, and display options
        """
        self.vis_config = vis_config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def generate_visualization(
        self,
        graph: nx.DiGraph,
        output_filename: str,
        metrics: Optional[VisualizationMetrics] = None,
    ) -> bool:
        """
        Generate visualization from graph.

        This is the main method that subclasses must implement to create their
        specific visualization output. The method should handle all aspects of
        visualization generation including layout, styling, and file output.

        Args:
            graph: Analyzed NetworkX directed graph with node and edge attributes
            output_filename: Path to save the output file
            metrics: Optional pre-calculated visualization metrics containing node metrics,
                    edge metrics, layout positions, and color schemes. If None, the
                    renderer should calculate metrics internally.

        Returns:
            True if visualization generation was successful, False otherwise

        Raises:
            NotImplementedError: If subclass does not implement this method
        """
        pass

    def get_file_extension(self) -> str:
        """
        Return file extension for this renderer.

        This method provides metadata about the output format produced by the renderer.
        It can be used by the pipeline to generate appropriate filenames.

        Returns:
            File extension string including the dot (e.g., '.html', '.png', '.svg')
        """
        return ".html"

    def supports_large_graphs(self) -> bool:
        """
        Return True if renderer can handle 10,000+ nodes efficiently.

        This method provides metadata about the renderer's performance characteristics.
        It can be used by the pipeline to select appropriate renderers based on graph size.

        Returns:
            True if the renderer can efficiently handle large graphs (10,000+ nodes),
            False otherwise
        """
        return False

    def _ensure_metrics(
        self, graph: nx.DiGraph, metrics: Optional[VisualizationMetrics]
    ) -> VisualizationMetrics:
        """
        Calculate metrics if not provided.
        
        This helper method ensures that visualization metrics are available, either by
        using the provided metrics or by calculating them. It checks for an existing
        metrics_calculator attribute first, otherwise creates a new one.

        Args:
            graph: The NetworkX directed graph to calculate metrics for
            metrics: Optional pre-calculated visualization metrics

        Returns:
            VisualizationMetrics object containing node metrics, edge metrics,
            layout positions, and color schemes
        """
        if metrics is not None:
            return metrics

        # Import here to avoid circular dependency
        from ..metrics import MetricsCalculator

        if hasattr(self, "metrics_calculator") and self.metrics_calculator is not None:
            self.logger.info(
                "No metrics provided - calculating using existing MetricsCalculator"
            )
            return self.metrics_calculator.calculate_all_metrics(graph)
        else:
            self.logger.info("No metrics provided - creating new MetricsCalculator")
            # Check if performance_config is available
            performance_config = (
                getattr(self, "performance_config", None) or {}
            )
            calculator = MetricsCalculator(self.vis_config, performance_config)
            return calculator.calculate_all_metrics(graph)

    def _validate_graph_not_empty(self, graph: nx.DiGraph) -> bool:
        """
        Validate that graph has nodes.
        
        This helper method checks if the graph is empty and logs a warning if so.
        Renderers should call this before attempting to generate visualizations.

        Args:
            graph: The NetworkX directed graph to validate

        Returns:
            True if graph has nodes (valid for rendering), False if empty
        """
        if graph.number_of_nodes() == 0:
            self.logger.warning("Cannot generate visualization. Graph is empty.")
            return False
        return True

    def _extract_node_metrics_dict(
        self, metrics: VisualizationMetrics
    ) -> dict[str, dict[str, Any]]:
        """
        Extract node metrics to dictionary format.
        
        This helper method converts the VisualizationMetrics node_metrics into a
        simpler dictionary format that's easier to work with in rendering code.

        Args:
            metrics: VisualizationMetrics object containing node metrics

        Returns:
            Dictionary mapping node IDs to dictionaries of metric values including
            size, community, colors, and centrality measures
        """
        node_metrics = {}
        for node, node_metric in metrics.node_metrics.items():
            node_metrics[node] = {
                "size": node_metric.size,
                "community": node_metric.community,
                "color_hex": node_metric.color_hex,
                "color_rgba": node_metric.color_rgba,
                "degree": node_metric.centrality_values["degree"],
                "betweenness": node_metric.centrality_values["betweenness"],
                "eigenvector": node_metric.centrality_values["eigenvector"],
            }
        return node_metrics

    def _extract_edge_metrics_dict(
        self, metrics: VisualizationMetrics
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """
        Extract edge metrics to dictionary format.
        
        This helper method converts the VisualizationMetrics edge_metrics into a
        simpler dictionary format that's easier to work with in rendering code.

        Args:
            metrics: VisualizationMetrics object containing edge metrics

        Returns:
            Dictionary mapping edge tuples (u, v) to dictionaries of metric values
            including width, color, mutual status, bridge status, and communities
        """
        edge_metrics: dict[tuple[str, str], dict[str, Any]] = {}
        for edge, edge_metric in metrics.edge_metrics.items():
            edge_metrics[edge] = {
                "width": edge_metric.width,
                "color": edge_metric.color,
                "is_mutual": edge_metric.is_mutual,
                "is_bridge": edge_metric.is_bridge,
                "common_neighbors": edge_metric.common_neighbors,
                "u_comm": edge_metric.u_comm,
                "v_comm": edge_metric.v_comm,
            }
        return edge_metrics

    def _ensure_output_directory(self, output_filename: str) -> None:
        """
        Ensure output directory exists.
        
        This helper method creates the output directory if it doesn't exist,
        preventing file write errors due to missing directories.

        Args:
            output_filename: Path to the output file
        """
        output_dir = os.path.dirname(output_filename)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
