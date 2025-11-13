"""
Abstract base class for visualization renderers.

This module defines the Renderer interface that all visualization renderers must implement.
It provides a standardized interface for generating visualizations from NetworkX graphs.

Classes:
    Renderer: Abstract base class defining the standard interface for renderers

Example:
    Creating a custom renderer::

        from FollowWeb_Visualizor.visualization.renderers.base import Renderer
        import networkx as nx

        class MyRenderer(Renderer):
            def generate_visualization(self, graph, output_filename, metrics=None):
                # Generate your visualization
                metrics = self._ensure_metrics(graph, metrics)
                # ... render logic ...
                return True

            def get_file_extension(self):
                return '.svg'

            def supports_large_graphs(self):
                return False

        # Use the renderer
        renderer = MyRenderer(vis_config={'colors': {...}})
        success = renderer.generate_visualization(graph, 'output.svg')

See Also:
    :class:`~FollowWeb_Visualizor.visualization.renderers.pyvis.PyvisRenderer`: Pyvis HTML renderer
    :class:`~FollowWeb_Visualizor.visualization.renderers.sigma.SigmaRenderer`: Sigma.js renderer
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
    - Output directory management

    Attributes
    ----------
    vis_config : dict[str, Any]
        Visualization configuration dictionary containing renderer-specific
        settings, styling preferences, and display options.
    logger : logging.Logger
        Logger instance for this renderer, named after the subclass.

    Notes
    -----
    Renderers should be stateless where possible. Configuration should be
    passed via vis_config rather than stored as mutable instance state.

    The base class provides helper methods for common operations like
    metrics calculation and validation. Subclasses should use these
    helpers to maintain consistency across different renderers.

    Examples
    --------
    Creating a simple text-based renderer::

        class TextRenderer(Renderer):
            def generate_visualization(self, graph, output_filename, metrics=None):
                if not self._validate_graph_not_empty(graph):
                    return False

                metrics = self._ensure_metrics(graph, metrics)
                node_metrics = self._extract_node_metrics_dict(metrics)

                with open(output_filename, 'w') as f:
                    f.write(f"Graph: {graph.number_of_nodes()} nodes\\n")
                    for node, attrs in node_metrics.items():
                        f.write(f"{node}: size={attrs['size']}\\n")

                return True

            def get_file_extension(self):
                return '.txt'

    See Also
    --------
    generate_visualization : Abstract method for creating visualizations
    _ensure_metrics : Helper for metrics calculation
    _validate_graph_not_empty : Helper for graph validation
    """

    def __init__(self, vis_config: dict[str, Any]) -> None:
        """
        Initialize renderer with visualization configuration.

        Parameters
        ----------
        vis_config : dict[str, Any]
            Visualization configuration dictionary containing renderer-specific
            settings, styling preferences, and display options. Common keys include:

            - 'colors': Color scheme configuration
            - 'node_size_range': Min/max node sizes
            - 'edge_width_range': Min/max edge widths
            - 'layout': Layout algorithm settings
            - 'show_labels': Whether to display node labels
            - 'show_tooltips': Whether to show hover tooltips

        Notes
        -----
        The constructor automatically initializes a logger named after
        the subclass for consistent logging across all renderers.

        Subclasses should call super().__init__(vis_config) before their
        own initialization to ensure proper setup.
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

        Parameters
        ----------
        graph : nx.DiGraph
            Analyzed NetworkX directed graph with node and edge attributes.
            Should contain analysis results like community assignments and
            centrality measures.
        output_filename : str
            Path to save the output file. The file extension should match
            the renderer's get_file_extension() return value.
        metrics : VisualizationMetrics, optional
            Pre-calculated visualization metrics containing:

            - node_metrics: Node sizes, colors, and centrality values
            - edge_metrics: Edge widths, colors, and relationship types
            - layout_positions: Node positions for layout
            - color_schemes: Community and metric color mappings

            If None, the renderer should calculate metrics internally using
            _ensure_metrics().

        Returns
        -------
        bool
            True if visualization generation was successful, False otherwise.
            Return False for recoverable errors (empty graph, file write errors).
            Raise exceptions for unrecoverable errors.

        Raises
        ------
        NotImplementedError
            If subclass does not implement this method.

        Notes
        -----
        Implementations should:

        1. Validate the graph is not empty using _validate_graph_not_empty()
        2. Ensure metrics are available using _ensure_metrics()
        3. Extract metrics to dict format using helper methods
        4. Generate the visualization in the renderer's format
        5. Ensure output directory exists using _ensure_output_directory()
        6. Write the output file
        7. Log success/failure and return appropriate boolean

        The method should handle errors gracefully and return False rather
        than raising exceptions for common failures like empty graphs or
        file write errors.

        Examples
        --------
        Basic implementation::

            def generate_visualization(self, graph, output_filename, metrics=None):
                # Validate
                if not self._validate_graph_not_empty(graph):
                    return False

                # Ensure metrics
                metrics = self._ensure_metrics(graph, metrics)
                node_metrics = self._extract_node_metrics_dict(metrics)
                edge_metrics = self._extract_edge_metrics_dict(metrics)

                # Generate visualization
                try:
                    self._ensure_output_directory(output_filename)
                    # ... rendering logic ...
                    self.logger.info(f"Saved visualization: {output_filename}")
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to generate visualization: {e}")
                    return False

        With progress tracking::

            def generate_visualization(self, graph, output_filename, metrics=None):
                if not self._validate_graph_not_empty(graph):
                    return False

                with ProgressTracker(total=3, title="Rendering") as tracker:
                    metrics = self._ensure_metrics(graph, metrics)
                    tracker.update(1)

                    data = self._convert_to_format(graph, metrics)
                    tracker.update(2)

                    self._write_output(data, output_filename)
                    tracker.update(3)

                return True
        """
        pass

    def get_file_extension(self) -> str:
        """
        Return file extension for this renderer.

        This method provides metadata about the output format produced by the renderer.
        It can be used by the pipeline to generate appropriate filenames.

        Returns
        -------
        str
            File extension string including the dot (e.g., '.html', '.png', '.svg').
            Default is '.html' for HTML-based renderers.

        Notes
        -----
        Subclasses should override this method to return their specific
        file extension. The extension should include the leading dot.

        Examples
        --------
        ::

            class PNGRenderer(Renderer):
                def get_file_extension(self):
                    return '.png'

            class SVGRenderer(Renderer):
                def get_file_extension(self):
                    return '.svg'
        """
        return ".html"

    def supports_large_graphs(self) -> bool:
        """
        Return True if renderer can handle 10,000+ nodes efficiently.

        This method provides metadata about the renderer's performance characteristics.
        It can be used by the pipeline to select appropriate renderers based on graph size.

        Returns
        -------
        bool
            True if the renderer can efficiently handle large graphs (10,000+ nodes),
            False otherwise. Default is False for safety.

        Notes
        -----
        "Efficiently" means the renderer can:

        - Generate visualizations in reasonable time (< 1 minute)
        - Produce interactive visualizations with smooth performance
        - Handle memory requirements without excessive consumption

        Renderers using WebGL (like Sigma.js) typically support large graphs.
        Renderers using DOM manipulation (like Pyvis) typically do not.

        Examples
        --------
        ::

            class SigmaRenderer(Renderer):
                def supports_large_graphs(self):
                    return True  # WebGL-based, handles 10k+ nodes

            class PyvisRenderer(Renderer):
                def supports_large_graphs(self):
                    return False  # DOM-based, struggles with 1k+ nodes
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
            performance_config = getattr(self, "performance_config", None) or {}
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
