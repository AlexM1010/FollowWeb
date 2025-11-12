"""
Pyvis renderer for interactive HTML network visualizations.

This module provides the PyvisRenderer class that implements the Renderer interface
for generating interactive HTML visualizations using the Pyvis library.
"""

import json
from typing import Any, Optional

import networkx as nx
from pyvis.network import Network

from ...core.types import VisualizationMetrics
from ...output.formatters import EmojiFormatter
from ...utils import ProgressTracker
from ..legends import LegendGenerator
from ..metrics import MetricsCalculator
from .base import Renderer


class PyvisRenderer(Renderer):
    """
    Pyvis-based renderer for interactive HTML network visualizations.

    This renderer generates standalone HTML files with embedded Pyvis library
    for interactive graph visualization with zoom, pan, and physics controls.
    """

    def __init__(
        self,
        vis_config: dict[str, Any],
        metrics_calculator: Optional[MetricsCalculator] = None,
    ) -> None:
        """
        Initialize the Pyvis renderer with visualization configuration.

        Args:
            vis_config: Visualization configuration dictionary containing Pyvis settings,
                       physics parameters, display options, and styling preferences
            metrics_calculator: Optional MetricsCalculator instance for consistent metrics

        Raises:
            KeyError: If required configuration keys are missing
        """
        super().__init__(vis_config)
        self.legend_generator = LegendGenerator(vis_config)
        self.metrics_calculator = metrics_calculator

    def generate_visualization(
        self,
        graph: nx.DiGraph,
        output_filename: str,
        metrics: Optional[VisualizationMetrics] = None,
    ) -> bool:
        """
        Generate interactive HTML visualization from graph using Pyvis.

        Args:
            graph: The analyzed NetworkX directed graph
            output_filename: Path to save the HTML file
            metrics: Optional pre-calculated visualization metrics

        Returns:
            True if successful, False otherwise
        """
        # Calculate metrics if not provided (using base class helper)
        metrics = self._ensure_metrics(graph, metrics)

        # Extract metrics from VisualizationMetrics object (using base class helpers)
        node_metrics = self._extract_node_metrics_dict(metrics)
        edge_metrics = self._extract_edge_metrics_dict(metrics)

        pyvis_config = self.vis_config.get("pyvis_interactive", {})

        # Use fallback in case the new key is missing
        width = pyvis_config.get("width", "100%")
        height = pyvis_config.get("height", "90vh")
        notebook = pyvis_config.get("notebook", False)
        show_labels = pyvis_config.get("show_labels", True)
        show_tooltips = pyvis_config.get("show_tooltips", True)
        physics_solver = pyvis_config.get("physics_solver", "forceAtlas2Based")

        net = Network(
            height=height,
            width=width,
            directed=True,
            notebook=notebook,
            cdn_resources="remote",
            select_menu=True,
        )

        # Grey out nodes not connected to selected
        net.highlight_nearest = True

        # The 'highlightNearest' object controls what happens to *unselected* items.
        options_json = {
            # Enable the GUI (equivalent to net.show_buttons)
            "configure": {
                "enabled": True,
                "filter": ["physics"],  # Only show the physics tab
            },
            # Custom 'physics' settings with updated default parameters
            "physics": {
                "solver": physics_solver,
                "forceAtlas2Based": {
                    "springConstant": 0.6,
                    "gravitationalConstant": -100,
                    "springLength": 100,
                },
            },
            "highlightNearest": {
                "enabled": True,
                "degree": 1,
                "nodes": "all",
                "edges": "all",  # Ensure edges are included in the dimming logic
                "unselectedColor": "#808080",  # Grey color for unselected edges and nodes
                "unselectedNodeOpacity": 0.3,  # Optional: Add opacity control
                "unselectedEdgeOpacity": 0.3,  # Optional: Add opacity control
                "hover": True,  # Keep edges highlighted on hover
                "hideWhenZooming": False,  # Keep dimming active when zooming
            },
            # Highlight selected edges
            "interaction": {
                "hover": True,
                "hoverConnectedEdges": True,
                "selectConnectedEdges": True,
            },
        }

        # Apply the custom options. This overrides the default highlighting behavior.
        net.set_options(json.dumps(options_json))

        # Add nodes and edges with progress tracking for large networks
        total_nodes = len(node_metrics)
        total_edges = len(edge_metrics)

        # Use more granular progress tracking for large networks
        if total_nodes > 1000:
            # For large networks, track node and edge addition separately
            with ProgressTracker(
                total=total_nodes,
                title="Adding nodes to interactive network",
                logger=self.logger,
            ) as tracker:
                # Add nodes using shared metrics
                node_count = 0
                for node, metrics_dict in node_metrics.items():
                    title_text = (
                        f"{node}\n\n"
                        f"Community ID: {metrics_dict['community']}\n"
                        f"Connections (Degree): {metrics_dict['degree']}\n"
                        f"Betweenness: {metrics_dict['betweenness']:.4f}\n"
                        f"Eigenvector (Influence): {metrics_dict['eigenvector']:.4f}"
                    )

                    node_label = node if show_labels else None
                    node_title = title_text if show_tooltips else None
                    font_config = {"size": 0} if not show_labels else {}

                    net.add_node(
                        node,
                        label=node_label,
                        size=metrics_dict["size"],
                        color=metrics_dict["color_hex"],
                        title=node_title,
                        font=font_config,
                    )

                    node_count += 1
                    if node_count % max(1, total_nodes // 20) == 0:
                        tracker.update(node_count)

                tracker.update(total_nodes)  # Ensure completion

            # Add edges with separate progress tracking for large networks
            with ProgressTracker(
                total=total_edges,
                title="Adding edges to interactive network",
                logger=self.logger,
            ) as tracker:
                # Add edges using shared metrics
                edge_count = 0
                for (u, v), metrics_dict in edge_metrics.items():
                    title = (
                        f"{u} <-> {v} (Mutual)\n"
                        if metrics_dict["is_mutual"]
                        else f"{u} -> {v} (One-way)\n"
                    )
                    title += f"Common Neighbors: {metrics_dict['common_neighbors']}\n"
                    title += (
                        f"BRIDGE: Community {metrics_dict['u_comm']} <-> {metrics_dict['v_comm']}"
                        if metrics_dict["is_bridge"]
                        else f"INTRA: Community {metrics_dict['u_comm']}"
                    )

                    edge_title = title if show_tooltips else None
                    dashes = not metrics_dict["is_mutual"]
                    arrows = "to, from" if metrics_dict["is_mutual"] else "to"

                    net.add_edge(
                        u,
                        v,
                        title=edge_title,
                        color=metrics_dict["color"],
                        width=metrics_dict["width"],
                        dashes=dashes,
                        arrows=arrows,
                    )

                    edge_count += 1
                    if edge_count % max(1, total_edges // 20) == 0:
                        tracker.update(edge_count)

                tracker.update(total_edges)  # Ensure completion
        else:
            # For smaller networks, use simple progress tracking
            with ProgressTracker(
                total=2,
                title="Building interactive network",
                logger=self.logger,
            ) as tracker:
                # Add nodes using shared metrics
                for node, metrics_dict in node_metrics.items():
                    title_text = (
                        f"{node}\n\n"
                        f"Community ID: {metrics_dict['community']}\n"
                        f"Connections (Degree): {metrics_dict['degree']}\n"
                        f"Betweenness: {metrics_dict['betweenness']:.4f}\n"
                        f"Eigenvector (Influence): {metrics_dict['eigenvector']:.4f}"
                    )

                    node_label = node if show_labels else None
                    node_title = title_text if show_tooltips else None
                    font_config = {"size": 0} if not show_labels else {}

                    net.add_node(
                        node,
                        label=node_label,
                        size=metrics_dict["size"],
                        color=metrics_dict["color_hex"],
                        title=node_title,
                        font=font_config,
                    )

                tracker.update(1)  # Nodes added

                # Add edges using shared metrics
                for (u, v), metrics_dict in edge_metrics.items():
                    title = (
                        f"{u} <-> {v} (Mutual)\n"
                        if metrics_dict["is_mutual"]
                        else f"{u} -> {v} (One-way)\n"
                    )
                    title += f"Common Neighbors: {metrics_dict['common_neighbors']}\n"
                    title += (
                        f"BRIDGE: Community {metrics_dict['u_comm']} <-> {metrics_dict['v_comm']}"
                        if metrics_dict["is_bridge"]
                        else f"INTRA: Community {metrics_dict['u_comm']}"
                    )

                    edge_title = title if show_tooltips else None
                    dashes = not metrics_dict["is_mutual"]
                    arrows = "to, from" if metrics_dict["is_mutual"] else "to"

                    net.add_edge(
                        u,
                        v,
                        title=edge_title,
                        color=metrics_dict["color"],
                        width=metrics_dict["width"],
                        dashes=dashes,
                        arrows=arrows,
                    )

                tracker.update(2)  # Edges added

        try:
            # Add spacing between building network and generating HTML
            self.logger.info("")

            # Generate and save HTML with progress tracking for large networks
            total_operations = 3  # generate HTML, create legend, save file

            with ProgressTracker(
                total=total_operations,
                title="Generating HTML visualization",
                logger=self.logger,
            ) as tracker:
                # Generate the HTML with legend
                html_string = net.generate_html()
                tracker.update(1)  # HTML generation complete

                # Create legend HTML with edge metrics for accurate scales
                legend_html = self.legend_generator.create_html_legend(
                    graph, edge_metrics, metrics
                )
                tracker.update(2)  # Legend creation complete

                # Insert legend into the HTML and save
                modified_html = self._insert_legend_into_html(html_string, legend_html)

                with open(output_filename, "w", encoding="utf-8") as f:
                    f.write(modified_html)

                tracker.update(3)  # File saving complete

            success_msg = EmojiFormatter.format(
                "success", f"Interactive HTML saved: {output_filename}"
            )
            self.logger.info(success_msg)
            return True
        except Exception as e:
            self.logger.error(f"Could not save interactive HTML: {e}")
            return False

    def _insert_legend_into_html(self, html_string: str, legend_html: str) -> str:
        """
        Insert the legend HTML into the main HTML string.

        Args:
            html_string: The main HTML content
            legend_html: The legend HTML to insert

        Returns:
            Modified HTML string with legend inserted
        """
        # Find the position to insert the legend (before the closing body tag)
        insert_position = html_string.find("</body>")

        if insert_position != -1:
            return (
                html_string[:insert_position]
                + legend_html
                + html_string[insert_position:]
            )
        else:
            # If no body tag found, append to the end
            return html_string + legend_html

    def get_file_extension(self) -> str:
        """Return file extension for Pyvis HTML output."""
        return ".html"

    def supports_large_graphs(self) -> bool:
        """
        Pyvis can handle moderately large graphs but not as efficiently as Sigma.js.

        Returns:
            False - Pyvis is not optimized for 10,000+ nodes
        """
        return False
