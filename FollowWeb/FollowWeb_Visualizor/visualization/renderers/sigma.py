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
import numpy as np
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
        template_name: Optional[str] = None,
    ) -> None:
        """
        Initialize the Sigma.js renderer with visualization configuration.

        Args:
            vis_config: Visualization configuration dictionary containing Sigma settings,
                       display options, and styling preferences
            metrics_calculator: Optional MetricsCalculator instance for consistent metrics
            template_name: Name of the Jinja2 template to use. If None, reads from vis_config['template_name']
                          or defaults to 'sigma_visualization.html'
                          Options: 'sigma_visualization.html' (Freesound/audio),
                                  'sigma_instagram.html' (Instagram social network)

        Raises:
            KeyError: If required configuration keys are missing
        """
        super().__init__(vis_config)
        self.legend_generator = LegendGenerator(vis_config)
        self.metrics_calculator = metrics_calculator
        # Read template_name from config if not provided
        if template_name is None:
            template_name = vis_config.get("template_name", "sigma_visualization.html")
        self.template_name = template_name
        
        # Setup Jinja2 template environment
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            auto_reload=True,
            cache_size=0  # Disable template caching for development
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
                # Read from visualization config (primary) or sigma_interactive (fallback)
                vis_settings = self.vis_config
                sigma_config = self.vis_config.get("sigma_interactive", {})
                config = {
                    "show_labels": vis_settings.get("show_labels", sigma_config.get("show_labels", True)),
                    "show_tooltips": vis_settings.get("show_tooltips", sigma_config.get("show_tooltips", True)),
                    "enable_audio": sigma_config.get("enable_audio_player", False),
                }
                tracker.update(3)
            
            # Render HTML using Jinja2 template
            with ProgressTracker(
                total=2,
                title="Generating HTML visualization",
                logger=self.logger,
            ) as tracker:
                
                template = self.jinja_env.get_template(self.template_name)
                self.logger.info(f"Loading template: {self.template_name} from {Path(__file__).parent / 'templates'}")
                
                # Prepare template context based on template type
                if self.template_name == "sigma_instagram.html":
                    # Instagram-specific template context
                    stats = self._calculate_network_stats(graph)
                    html_content = template.render(
                        title=f"Instagram Network - {graph.number_of_nodes()} users",
                        graph_data=graph_data,
                        config=config,
                        node_count=stats["node_count"],
                        edge_count=stats["edge_count"],
                        avg_degree=stats["avg_degree"],
                        density=stats.get("density"),
                        show_centrality=any("betweenness" in m for m in node_metrics.values() if m),
                        show_community=any("community" in m for m in node_metrics.values() if m),
                        layout_iterations=100,
                        layout_gravity=1,
                        layout_scaling=10,
                        background_color="#0a0e27",
                        graph_background="linear-gradient(135deg, #0a0e27 0%, #1a1e3f 100%)"
                    )
                else:
                    # Default Freesound/audio template context
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
                
                # Copy forceatlas2.js to output directory if using Instagram template
                if self.template_name == "sigma_instagram.html":
                    self._copy_forceatlas2_script(output_filename)
                
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
        
        # Get layout positions from metrics, or calculate physics-based layout
        layout = metrics.layout_positions
        
        # If layout is empty, calculate a physics-based spring layout
        if not layout:
            self.logger.info("Calculating physics-based layout for visualization...")
            # Use spring_layout with more iterations for better physics simulation
            # k controls the optimal distance between nodes (spring length)
            # iterations controls convergence quality
            layout = nx.spring_layout(
                graph, 
                k=1/np.sqrt(graph.number_of_nodes()) if graph.number_of_nodes() > 0 else 1,
                iterations=50,
                seed=42,
                scale=100  # Scale up for better spread
            )
            self.logger.info(f"Layout calculated for {len(layout)} nodes")
        
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
            
            # Check if this is Instagram data (has followers/following counts)
            is_instagram = "followers_count" in node_attrs or "following_count" in node_attrs
            
            if is_instagram and self.template_name == "sigma_instagram.html":
                # Instagram-specific node attributes
                degree = graph.degree(node_id)
                max_degree = max(dict(graph.degree()).values()) if graph.number_of_nodes() > 0 else 1
                size = 3 + (degree / max_degree) * 15
                
                followers = node_attrs.get("followers_count", 0)
                following = node_attrs.get("following_count", 0)
                
                # Calculate color based on follower/following ratio
                ratio = followers / (following + 1)
                if ratio > 1.5:
                    color = "#ff6b9d"  # Popular
                elif ratio < 0.7:
                    color = "#4ecdc4"  # Active follower
                else:
                    color = "#6c8eff"  # Balanced
                
                sigma_node = {
                    "key": str(node_id),
                    "attributes": {
                        "label": str(node_id),
                        "x": x,
                        "y": y,
                        "size": float(size),
                        "color": color,
                        "followers": followers,
                        "following": following,
                        "degree": degree,
                    }
                }
                
                # Add centrality if available
                if node_id in node_metrics and "betweenness" in node_metrics[node_id]:
                    sigma_node["attributes"]["centrality"] = float(node_metrics[node_id]["betweenness"])
                
                # Add community if available
                if node_id in node_metrics and "community" in node_metrics[node_id]:
                    sigma_node["attributes"]["community"] = int(node_metrics[node_id]["community"])
            else:
                # Default Freesound/audio node attributes
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

    def _copy_forceatlas2_script(self, output_filename: str) -> None:
        """
        Copy the forceatlas2.js script to the same directory as the output HTML file.
        
        Args:
            output_filename: Path to the output HTML file
        """
        import shutil
        
        try:
            # Get the template directory where forceatlas2.js is located
            template_dir = Path(__file__).parent / "templates"
            source_script = template_dir / "forceatlas2.js"
            
            # Get the output directory
            output_dir = Path(output_filename).parent
            dest_script = output_dir / "forceatlas2.js"
            
            # Copy the script file
            if source_script.exists():
                shutil.copy2(source_script, dest_script)
                self.logger.debug(f"Copied forceatlas2.js to {dest_script}")
            else:
                self.logger.warning(f"forceatlas2.js not found at {source_script}")
        except Exception as e:
            self.logger.warning(f"Could not copy forceatlas2.js: {e}")

    def _calculate_network_stats(self, graph: nx.DiGraph) -> dict[str, Any]:
        """
        Calculate basic network statistics for Instagram template.
        
        Args:
            graph: NetworkX directed graph
            
        Returns:
            Dictionary with network statistics
        """
        node_count = graph.number_of_nodes()
        edge_count = graph.number_of_edges()
        
        stats = {
            "node_count": node_count,
            "edge_count": edge_count,
            "avg_degree": f"{(edge_count * 2 / node_count):.2f}" if node_count > 0 else "0.00",
        }
        
        # Calculate density for smaller graphs
        if node_count > 0 and node_count < 10000:
            try:
                density = nx.density(graph)
                stats["density"] = density
            except Exception:
                pass
        
        return stats

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
