"""
Abstract base class for visualization renderers.

This module defines the Renderer interface that all visualization renderers must implement.
It provides a standardized interface for generating visualizations from NetworkX graphs.
"""

import logging
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
