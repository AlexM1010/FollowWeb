"""
Sigma.js renderer for high-performance interactive HTML network visualizations.

This module provides the SigmaRenderer class that implements the Renderer interface
for generating interactive HTML visualizations using the Sigma.js library with WebGL support.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import networkx as nx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ...core.types import VisualizationMetrics
from ...output.formatters import EmojiFormatter
from ...utils import ProgressTracker
from ..legends import LegendGenerator
from ..metrics import MetricsCalculator
from .base import Renderer


class SigmaRenderer(Renderer):
    """
    Sigma.js-based renderer for high-performance interactive HTML network visualizations.
    
    This renderer generates standalone HTML files with embedded Sigma.js library
    for interactive graph visualization with WebGL rendering, supporting 10,000+ nodes.
    Includes audio playback functionality using Howler.js for Freesound sample networks.
    """

    def __init__(
        self,
        vis_config: dict[str, Any],
        metrics_calculator: Optional[MetricsCalculator] = None,
    ) -> None:
        """
        Initialize the Sigma.js renderer with visualization configuration.

        Args:
            vis_config: Visualization configuration dictionary containing Sigma settings,
                       display options, and styling preferences
            metrics_calculator: Optional MetricsCalculator instance for consistent metrics

        Raises:
            KeyError: If required configuration keys are missing
        """
        super().__init__(vis_config)
        self.legend_generator = LegendGenerator(vis_config)
        self.metrics_calculator = metrics_calculator
        
        # Setup Jinja2 template environment
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def generate_visualization(
        self,
        graph: nx.DiGraph,
        output_filename: str,
        metrics: Optional[VisualizationMetrics] = None,
    ) -> bool:
        """
        Generate interactive HTML visualization from graph using Sigma.js.

        Args:
            graph: The analyzed NetworkX directed graph
            output_filename: Path to save the HTML file
            metrics: Optional pre-calculated visualization metrics

        Returns:
            True if successful, False otherwise
        """
        # Validate graph
        if not self._validate_graph_not_empty(graph):
            return False
        
        # Calculate metrics if not provided
        metrics = self._ensure_metrics(graph, metrics)

        # Extract metrics from VisualizationMetrics object
        node_metrics = self._extract_node_metrics_dict(metrics)
        edge_metrics = self._extract_edge_metrics_dict(metrics)

        try:
            # Convert graph to Sigma.js format with progress tracking
            with ProgressTracker(
                total=3,
                title="Converting graph to Sigma.js format",
                logger=self.logger,
            ) as tracker:
                
                graph_data = self._convert_to_sigma_format(
                    graph, node_metrics, edge_metrics, metrics
                )
                tracker.update(1)
                
                # Generate legend HTML
                legend_html = self.legend_generator.create_html_legend(
                    graph, edge_metrics, metrics
                )
                tracker.update(2)
                
                # Prepare configuration
                sigma_config = self.vis_config.get("sigma_interactive", {})
                config = {
                    "show_labels": sigma_config.get("show_labels", True),
                    "show_tooltips": sigma_config.get("show_tooltips", True),
                    "enable_audio": sigma_config.get("enable_audio", True),
                }
                tracker.update(3)
            
            # Render HTML using Jinja2 template
            with ProgressTracker(
                total=2,
                title="Generating HTML visualization",
                logger=self.logger,
            ) as tracker:
                
                template = self.jinja_env.get_template("sigma_visualization.html")
                
                html_content = template.render(
                    title=f"Network Visualization - {graph.number_of_nodes()} nodes",
                    graph_data=json.dumps(graph_data),
                    config=json.dumps(config),
                    legend_html=legend_html,
                    legend_html_style=""  # Legend styles are inline in the legend HTML
                )
                tracker.update(1)
                
                # Ensure output directory exists
                self._ensure_output_directory(output_filename)
                
                # Write HTML file
                with open(output_filename, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                tracker.update(2)
            
            success_msg = EmojiFormatter.format(
                "success", f"Sigma.js HTML saved: {output_filename}"
            )
            self.logger.info(success_msg)
            return True
            
        except Exception as e:
            self.logger.error(f"Could not save Sigma.js HTML: {e}", exc_info=True)
            return False

    def _convert_to_sigma_format(
        self,
        graph: nx.DiGraph,
        node_metrics: dict[str, dict[str, Any]],
        edge_metrics: dict[tuple[str, str], dict[str, Any]],
        metrics: VisualizationMetrics,
    ) -> dict[str, Any]:
        """
        Convert NetworkX graph to Sigma.js data format.
        
        Args:
            graph: NetworkX directed graph
            node_metrics: Pre-calculated node metrics
            edge_metrics: Pre-calculated edge metrics
            metrics: Full visualization metrics including layout
            
        Returns:
            Dictionary with 'nodes' and 'edges' arrays in Sigma.js format
        """
        nodes = []
        edges = []
        
        # Get layout positions from metrics, or calculate fallback
        layout = metrics.layout_positions
        
        # If layout is empty, calculate a simple spring layout
        if not layout:
            import networkx as nx
            layout = nx.spring_layout(graph, seed=42)
        
        # Convert nodes
        for node_id in graph.nodes():
            node_attrs = graph.nodes[node_id]
            node_metric = node_metrics.get(node_id, {})
            
            # Get position from layout
            pos = layout.get(node_id, (0, 0))
            
            # Handle numpy arrays from spring_layout
            if hasattr(pos, '__iter__') and len(pos) >= 2:
                x, y = float(pos[0]), float(pos[1])
            else:
                x, y = 0.0, 0.0
            
            # Build node attributes for Sigma.js
            sigma_node = {
                "key": str(node_id),
                "attributes": {
                    "label": str(node_id),
                    "x": x,
                    "y": y,
                    "size": float(node_metric.get("size", 10)),
                    "color": node_metric.get("color_hex", "#999999"),
                    "community": node_metric.get("community", 0),
                    "degree": node_metric.get("degree", 0),
                    "betweenness": node_metric.get("betweenness", 0.0),
                    "eigenvector": node_metric.get("eigenvector", 0.0),
                }
            }
            
            # Add node-specific attributes from graph
            if "name" in node_attrs:
                sigma_node["attributes"]["name"] = str(node_attrs["name"])
            
            if "tags" in node_attrs:
                # Ensure tags is a list
                tags = node_attrs["tags"]
                if isinstance(tags, str):
                    tags = [tags]
                elif not isinstance(tags, list):
                    tags = []
                sigma_node["attributes"]["tags"] = tags
            
            if "duration" in node_attrs:
                sigma_node["attributes"]["duration"] = float(node_attrs["duration"])
            
            if "user" in node_attrs:
                sigma_node["attributes"]["user"] = str(node_attrs["user"])
            
            if "audio_url" in node_attrs:
                sigma_node["attributes"]["audio_url"] = str(node_attrs["audio_url"])
            
            nodes.append(sigma_node)
        
        # Convert edges
        for (source, target) in graph.edges():
            edge_metric = edge_metrics.get((source, target), {})
            edge_attrs = graph.edges[source, target]
            
            # Build edge attributes for Sigma.js
            sigma_edge = {
                "source": str(source),
                "target": str(target),
                "attributes": {
                    "size": float(edge_metric.get("width", 1)),
                    "color": edge_metric.get("color", "#cccccc"),
                    "type": "arrow" if not edge_metric.get("is_mutual", False) else "line",
                }
            }
            
            # Add edge-specific attributes
            if "type" in edge_attrs:
                sigma_edge["attributes"]["edge_type"] = str(edge_attrs["type"])
            
            if "weight" in edge_attrs:
                sigma_edge["attributes"]["weight"] = float(edge_attrs["weight"])
            
            edges.append(sigma_edge)
        
        return {
            "nodes": nodes,
            "edges": edges
        }

    def get_file_extension(self) -> str:
        """Return file extension for Sigma.js HTML output."""
        return ".html"

    def supports_large_graphs(self) -> bool:
        """
        Sigma.js with WebGL can efficiently handle 10,000+ nodes.
        
        Returns:
            True - Sigma.js is optimized for large graphs with WebGL rendering
        """
        return True
