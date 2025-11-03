"""
Rendering module for FollowWeb visualization.

This module handles both interactive HTML and static PNG generation for network visualizations.
It includes Pyvis-based interactive rendering and matplotlib-based static rendering.
"""

import json
import logging
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
from pyvis.network import Network

# Conditional nx_parallel import (Python 3.11+ only)
try:
    if sys.version_info >= (3, 11):
        import nx_parallel  # noqa: F401
except ImportError:
    pass  # nx_parallel not available, use standard NetworkX

from ..core.types import VisualizationMetrics
from ..data.cache import get_cached_undirected_graph
from ..output.formatters import EmojiFormatter
from ..utils import ProgressTracker
from .colors import get_community_colors
from .legends import LegendGenerator
from .metrics import MetricsCalculator


class InteractiveRenderer:
    """
    Handles Pyvis HTML generation for interactive network visualizations.
    """

    def __init__(
        self,
        vis_config: Dict[str, Any],
        metrics_calculator: Optional[Optional[MetricsCalculator]] = None,
    ) -> None:
        """
        Initialize the interactive renderer with visualization configuration.

        Args:
            vis_config: Visualization configuration dictionary containing Pyvis settings,
                       physics parameters, display options, and styling preferences
            metrics_calculator: Optional MetricsCalculator instance for consistent metrics

        Raises:
            KeyError: If required configuration keys are missing
        """
        self.vis_config = vis_config
        self.legend_generator = LegendGenerator(vis_config)
        self.logger = logging.getLogger(__name__)
        self.metrics_calculator = metrics_calculator

    def generate_html(
        self,
        graph: nx.DiGraph,
        output_filename: str,
        shared_metrics: Optional[Optional[VisualizationMetrics]] = None,
    ) -> bool:
        """
        Generates an interactive HTML file to visualize the network graph.

        Args:
            graph: The analyzed graph
            output_filename: Path to save the HTML file
            shared_metrics: VisualizationMetrics object from MetricsCalculator

        Returns:
            True if successful, False otherwise
        """
        # Calculate metrics if not provided
        if shared_metrics is None:
            if self.metrics_calculator is not None:
                self.logger.info(
                    "No metrics provided - calculating using existing MetricsCalculator"
                )
                shared_metrics = self.metrics_calculator.calculate_all_metrics(graph)
            else:
                self.logger.info("No metrics provided - creating new MetricsCalculator")
                calculator = MetricsCalculator(self.vis_config)
                shared_metrics = calculator.calculate_all_metrics(graph)

        # Extract metrics from VisualizationMetrics object
        node_metrics = {}
        edge_metrics: Dict[Tuple[str, str], Dict[str, Any]] = {}

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

        for edge, edge_metric in shared_metrics.edge_metrics.items():
            edge_metrics[edge] = {
                "width": edge_metric.width,
                "color": edge_metric.color,
                "is_mutual": edge_metric.is_mutual,
                "is_bridge": edge_metric.is_bridge,
                "common_neighbors": edge_metric.common_neighbors,
                "u_comm": edge_metric.u_comm,
                "v_comm": edge_metric.v_comm,
            }

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
                for node, metrics in node_metrics.items():
                    title_text = (
                        f"{node}\n\n"
                        f"Community ID: {metrics['community']}\n"
                        f"Connections (Degree): {metrics['degree']}\n"
                        f"Betweenness: {metrics['betweenness']:.4f}\n"
                        f"Eigenvector (Influence): {metrics['eigenvector']:.4f}"
                    )

                    node_label = node if show_labels else None
                    node_title = title_text if show_tooltips else None
                    font_config = {"size": 0} if not show_labels else {}

                    net.add_node(
                        node,
                        label=node_label,
                        size=metrics["size"],
                        color=metrics["color_hex"],
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
                for (u, v), metrics in edge_metrics.items():
                    title = (
                        f"{u} <-> {v} (Mutual)\n"
                        if metrics["is_mutual"]
                        else f"{u} -> {v} (One-way)\n"
                    )
                    title += f"Common Neighbors: {metrics['common_neighbors']}\n"
                    title += (
                        f"BRIDGE: Community {metrics['u_comm']} <-> {metrics['v_comm']}"
                        if metrics["is_bridge"]
                        else f"INTRA: Community {metrics['u_comm']}"
                    )

                    edge_title = title if show_tooltips else None
                    dashes = not metrics["is_mutual"]
                    arrows = "to, from" if metrics["is_mutual"] else "to"

                    net.add_edge(
                        u,
                        v,
                        title=edge_title,
                        color=metrics["color"],
                        width=metrics["width"],
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
                for node, metrics in node_metrics.items():
                    title_text = (
                        f"{node}\n\n"
                        f"Community ID: {metrics['community']}\n"
                        f"Connections (Degree): {metrics['degree']}\n"
                        f"Betweenness: {metrics['betweenness']:.4f}\n"
                        f"Eigenvector (Influence): {metrics['eigenvector']:.4f}"
                    )

                    node_label = node if show_labels else None
                    node_title = title_text if show_tooltips else None
                    font_config = {"size": 0} if not show_labels else {}

                    net.add_node(
                        node,
                        label=node_label,
                        size=metrics["size"],
                        color=metrics["color_hex"],
                        title=node_title,
                        font=font_config,
                    )

                tracker.update(1)  # Nodes added

                # Add edges using shared metrics
                for (u, v), metrics in edge_metrics.items():
                    title = (
                        f"{u} <-> {v} (Mutual)\n"
                        if metrics["is_mutual"]
                        else f"{u} -> {v} (One-way)\n"
                    )
                    title += f"Common Neighbors: {metrics['common_neighbors']}\n"
                    title += (
                        f"BRIDGE: Community {metrics['u_comm']} <-> {metrics['v_comm']}"
                        if metrics["is_bridge"]
                        else f"INTRA: Community {metrics['u_comm']}"
                    )

                    edge_title = title if show_tooltips else None
                    dashes = not metrics["is_mutual"]
                    arrows = "to, from" if metrics["is_mutual"] else "to"

                    net.add_edge(
                        u,
                        v,
                        title=edge_title,
                        color=metrics["color"],
                        width=metrics["width"],
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
                    graph, edge_metrics, shared_metrics
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
        Inserts the legend HTML into the main HTML string.

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


class StaticRenderer:
    """
    Handles matplotlib PNG generation for static network visualizations.
    """

    def __init__(
        self,
        vis_config: Dict[str, Any],
        performance_config: Optional[Optional[Dict[str, Any]]] = None,
    ) -> None:
        """
        Initialize the static renderer with visualization configuration.

        Args:
            vis_config: Visualization configuration dictionary containing matplotlib settings,
                       layout parameters, image dimensions, and styling options
            performance_config: Optional performance configuration for optimizations

        Raises:
            KeyError: If required configuration keys are missing, particularly 'static_image'
        """
        self.vis_config = vis_config
        self.static_config = vis_config["static_image"]
        self.performance_config = performance_config or {}
        self.logger = logging.getLogger(__name__)

    def generate_png(
        self,
        graph: nx.DiGraph,
        output_filename: str,
        node_metrics: Dict[str, Dict[str, Any]],
        edge_metrics: Dict[Tuple[str, str], Dict[str, Any]],
        shared_metrics: Optional[Optional[VisualizationMetrics]] = None,
    ) -> bool:
        """
        Generates a static PNG image of the network graph using matplotlib.

        Args:
            graph: The analyzed graph
            output_filename: Path to save the PNG file
            node_metrics: Pre-calculated node size/color metrics
            edge_metrics: Pre-calculated edge width/color metrics
            shared_metrics: Optional shared metrics containing layout positions

        Returns:
            True if successful, False otherwise
        """
        if graph.number_of_nodes() == 0:
            self.logger.warning("Cannot generate static graph. Graph is empty.")
            return False

        # Setup figure - ensure perfect 1:1 aspect ratio (square)
        default_size = 1200  # Square dimensions for network display

        # Force square dimensions regardless of config
        size_pixels = max(
            self.static_config.get("width", default_size),
            self.static_config.get("height", default_size),
        )
        dpi = self.static_config.get("dpi", 300)

        # Calculate square dimensions in inches
        size_inches = size_pixels / dpi
        width_inches = size_inches
        height_inches = size_inches

        fig, ax = plt.subplots(figsize=(width_inches, height_inches))

        # Set transparent background
        ax.set_facecolor("none")  # Transparent axes background
        fig.patch.set_facecolor("none")  # Transparent figure background
        ax.axis("off")  # Turn off axes
        fig.patch.set_visible(False)  # Hide figure patch completely

        # Use shared layout positions if available, otherwise calculate layout
        if shared_metrics and shared_metrics.layout_positions:
            self.logger.info("Using shared layout positions for PNG generation")
            pos = shared_metrics.layout_positions
        else:
            # Calculate layout using the configured or default layout type
            layout_type = self._get_effective_layout_type()
            G_undirected = get_cached_undirected_graph(graph)

            # Add edge weights to undirected graph for all layout types
            self._add_edge_weights_for_layout(G_undirected, edge_metrics)

            # Calculate layout with unified method
            pos = self._calculate_layout(graph, G_undirected, layout_type)

        # Use progress tracking for edge preparation and drawing operations
        total_operations = (
            4  # prepare edges, draw mutual edges, draw oneway edges, draw nodes
        )

        with ProgressTracker(
            total=total_operations,
            title="Rendering static visualization",
            logger=self.logger,
        ) as tracker:
            # Step 1: Prepare edge batches
            mutual_edges = []
            mutual_colors_rgb = []
            mutual_widths_mpl = []

            oneway_edges = []
            oneway_colors_rgb = []
            oneway_widths_mpl = []

            alpha = self.static_config.get("edge_alpha", 0.7)

            # Use shared metrics for edge rendering
            if shared_metrics:
                edge_source = shared_metrics.edge_metrics
            else:
                edge_source = edge_metrics

            for (u, v), metrics in edge_source.items():
                # Handle shared metrics (EdgeMetric objects)
                if shared_metrics:
                    hex_color = metrics.color.lstrip("#")
                    mpl_width = metrics.width * 0.8
                    is_mutual = metrics.is_mutual
                else:
                    hex_color = metrics["color"].lstrip("#")
                    mpl_width = metrics["width"] * 0.8
                    is_mutual = metrics["is_mutual"]

                # Convert hex color to RGB tuple
                rgb_color = tuple(
                    int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)
                )

                if is_mutual:
                    mutual_edges.append((u, v))
                    mutual_colors_rgb.append(rgb_color)
                    mutual_widths_mpl.append(mpl_width)
                else:
                    oneway_edges.append((u, v))
                    oneway_colors_rgb.append(rgb_color)
                    oneway_widths_mpl.append(mpl_width)

            tracker.update(1)  # Edge preparation complete

            # Step 2: Draw mutual edges
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=mutual_edges,
                width=[w * 0.4 for w in mutual_widths_mpl],  # Make edges much thinner
                alpha=alpha,
                edge_color=mutual_colors_rgb,
                style="-",
                arrows=True,
                arrowsize=self.static_config.get(
                    "edge_arrow_size", 6
                ),  # Smaller arrows
                arrowstyle="<|-|>",
                ax=ax,
                node_size=0,  # Prevent overlap issues
                connectionstyle="arc3,rad=0.1",  # Add edge curves
            )

            tracker.update(2)  # Mutual edges drawing complete

            # Step 3: Draw one-way edges
            nx.draw_networkx_edges(
                graph,
                pos,
                edgelist=oneway_edges,
                width=[w * 0.2 for w in oneway_widths_mpl],
                alpha=alpha,
                edge_color=oneway_colors_rgb,
                style="--",
                arrows=True,
                arrowsize=self.static_config.get("edge_arrow_size", 3),
                arrowstyle="-|>",
                ax=ax,
                node_size=0,  # Prevent overlap issues
                connectionstyle="arc3,rad=0.05",  # Add edge curves
            )

            tracker.update(3)  # One-way edges drawing complete

            # Step 4: Draw nodes
            if shared_metrics:
                # Use shared metrics for node properties
                node_colors = [
                    shared_metrics.node_metrics[node].color_rgba
                    for node in graph.nodes()
                ]
                node_sizes = [
                    shared_metrics.node_metrics[node].size for node in graph.nodes()
                ]
            else:
                # Use node_metrics format
                node_colors = [
                    node_metrics[node]["color_rgba"] for node in graph.nodes()
                ]
                node_sizes = [node_metrics[node]["size"] for node in graph.nodes()]

            nx.draw_networkx_nodes(
                graph,
                pos,
                node_color=node_colors,
                node_size=node_sizes,
                alpha=self.static_config.get("node_alpha", 1.0),
                ax=ax,
            )

            tracker.update(4)  # Node drawing complete

        # Add labels if requested
        if self.static_config.get("with_labels", False):
            nx.draw_networkx_labels(
                graph,
                pos,
                font_size=self.static_config.get("font_size", 8),
                font_color="black",
                ax=ax,
            )

        # Scale the graph with 1:1 aspect ratio (square)
        if pos:
            # Get the bounds of the layout
            x_values = [pos[node][0] for node in pos]
            y_values = [pos[node][1] for node in pos]

            if x_values and y_values:
                x_min, x_max = min(x_values), max(x_values)
                y_min, y_max = min(y_values), max(y_values)

                # Calculate the graph dimensions
                x_range = x_max - x_min
                y_range = y_max - y_min
                margin_x = x_range * 0.05 if x_range > 0 else 0.1
                margin_y = y_range * 0.05 if y_range > 0 else 0.1

                # For 1:1 aspect ratio, make both dimensions equal
                graph_width = x_range + 2 * margin_x
                graph_height = y_range + 2 * margin_y

                # Use the larger dimension for both to maintain 1:1 ratio
                max_dimension = max(graph_width, graph_height)

                # Center the graph in the square
                if graph_width < max_dimension:
                    # Expand width to match height
                    width_increase = (max_dimension - graph_width) / 2
                    x_min -= width_increase
                    x_max += width_increase

                if graph_height < max_dimension:
                    # Expand height to match width
                    height_increase = (max_dimension - graph_height) / 2
                    y_min -= height_increase
                    y_max += height_increase

                # Set axis limits for perfect square
                ax.set_xlim(x_min - margin_x, x_max + margin_x)
                ax.set_ylim(y_min - margin_y, y_max + margin_y)

                # Force 1:1 aspect ratio (square)
                ax.set_aspect("equal")

        plt.axis("off")
        plt.tight_layout()

        # Save PNG file
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_filename)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Save with explicit flushing
            # bbox_inches="tight" ensures legend outside plot area is included
            plt.savefig(
                output_filename,
                dpi=self.static_config["dpi"],
                bbox_inches="tight",
                facecolor="none",  # Transparent background
                edgecolor="none",
                pad_inches=0.0,  # No padding for clean borderless output
                transparent=True,  # Enable transparency
            )

            # Force matplotlib to flush and close file handles
            plt.draw()

            success_msg = EmojiFormatter.format(
                "success", f"Static PNG saved: {output_filename}"
            )
            self.logger.info(success_msg)
            return True
        except Exception as e:
            self.logger.error(f"Could not save static PNG: {e}")
            return False
        finally:
            # Ensure all matplotlib resources are properly cleaned up
            try:
                plt.close(fig)  # Close specific figure
            except BaseException:
                pass
            try:
                plt.close("all")  # Close all figures as fallback
            except BaseException:
                pass

    def _get_effective_layout_type(self) -> str:
        """
        Get the effective layout type, defaulting to spring layout.

        This method implements the requirement to use spring layout as default
        and provides configuration options to force spring layout usage.

        Returns:
            str: The layout type to use for PNG generation
        """
        # Check if spring layout is forced in PNG configuration
        png_config = self.vis_config.get("png_layout", {})
        force_spring = png_config.get("force_spring_layout", False)

        if force_spring:
            self.logger.info(
                "Force spring layout enabled - using spring layout for PNG"
            )
            return "spring"

        # Get configured layout type, defaulting to spring (changed from circular)
        layout_type = self.static_config.get("layout", "spring")

        # Log if we're changing from circular to spring as default
        if layout_type == "circular":
            self.logger.info(
                "Circular layout configured, but spring is now the default for better network representation"
            )
            # Allow circular if explicitly configured, but warn about the change

        return layout_type

    def _add_edge_weights_for_layout(
        self,
        G_undirected: nx.Graph,
        edge_metrics: Dict[Tuple[str, str], Dict[str, Any]],
    ) -> None:
        """
        Add edge weights to undirected graph for layout calculation.

        Args:
            G_undirected: Undirected version of the graph
            edge_metrics: Pre-calculated edge metrics containing width information
        """
        # Set edge weights based on edge metrics (width represents relationship strength)
        for (u, v), metrics in edge_metrics.items():
            if G_undirected.has_edge(u, v):
                # Use edge width as weight (higher width = stronger connection = higher weight)
                weight = metrics.get("width", 1.0)
                G_undirected[u][v]["weight"] = weight

        # Set default weight for edges without metrics
        for u, v in G_undirected.edges():
            if "weight" not in G_undirected[u][v]:
                G_undirected[u][v]["weight"] = 1.0

    def _calculate_layout(
        self, graph: nx.DiGraph, G_undirected: nx.Graph, layout_type: str
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate layout positions for all supported layout types with edge weights and progress tracking.
        Enhanced with adaptive node spacing to reduce overlap.

        Args:
            graph: Original directed graph
            G_undirected: Undirected version of the graph with edge weights
            layout_type: Type of layout to calculate

        Returns:
            Dictionary mapping node names to (x, y) positions
        """
        self.logger.info(f"\nCalculating '{layout_type}' layout...")
        start_layout_time = time.perf_counter()

        if layout_type == "spring":
            pos = self._calculate_spring_layout(G_undirected, graph)
        elif layout_type == "kamada_kawai":
            pos = self._calculate_kamada_kawai_layout(G_undirected)
        elif layout_type == "circular":
            pos = self._calculate_circular_layout(G_undirected, graph)
        elif layout_type == "shell":
            pos = self._calculate_shell_layout(G_undirected, graph)
        else:
            self.logger.warning(
                f"Unknown layout '{layout_type}'. Defaulting to 'spring'."
            )
            pos = self._calculate_spring_layout(G_undirected, graph)

        # Single timing logic for all layout types
        end_layout_time = time.perf_counter()
        timer_msg = EmojiFormatter.format(
            "timer",
            f"Layout '{layout_type}' completed in {end_layout_time - start_layout_time:.2f}s",
        )
        self.logger.info(timer_msg)
        # Add spacing after timer message for consistent formatting
        self.logger.info("")
        return pos

    def _calculate_spring_layout(
        self, G_undirected: nx.Graph, graph: nx.DiGraph
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate spring layout with comprehensive physics parameters and progress tracking.

        Args:
            G_undirected: Undirected version of the graph for layout calculation
            graph: Original directed graph for metadata

        Returns:
            Dictionary mapping node names to (x, y) positions
        """
        num_nodes = G_undirected.number_of_nodes()
        num_edges = G_undirected.number_of_edges()

        # Calculate graph density for adaptive spacing
        max_possible_edges = num_nodes * (num_nodes - 1) / 2
        density = num_edges / max_possible_edges if max_possible_edges > 0 else 0

        # Get spring configuration
        png_config = self.vis_config.get("png_layout", {})
        if isinstance(png_config, dict) and "spring" in png_config:
            spring_config = png_config["spring"]
        else:
            # Default fallback
            spring_config = {
                "k": 0.15,
                "iterations": 200,
                "enable_multistage": True,
                "initial_k_multiplier": 1.5,
                "final_k_multiplier": 0.8,
            }

        # Check for performance configuration override
        performance_config = getattr(self, "performance_config", {})
        max_iterations_override = performance_config.get("max_layout_iterations")
        fast_mode = performance_config.get("fast_mode", False)

        if max_iterations_override:
            total_iterations = max_iterations_override
            k_value = self._get_spring_k_value(spring_config, num_nodes, density)
            self.logger.info(
                f"Performance override: Using {total_iterations} iterations"
            )
        elif fast_mode:
            total_iterations = max(10, spring_config.get("iterations", 200) // 10)
            k_value = self._get_spring_k_value(spring_config, num_nodes, density) * 2
            self.logger.info(
                f"Fast mode: Using {total_iterations} iterations with enhanced spacing"
            )
        elif num_nodes > 10000:
            total_iterations = max(50, spring_config.get("iterations", 200) // 4)
            k_value = self._get_spring_k_value(spring_config, num_nodes, density) * 1.5
            self.logger.info(
                f"Large graph: Using {total_iterations} iterations with enhanced spacing"
            )
        elif num_nodes > 5000:
            total_iterations = max(100, spring_config.get("iterations", 200) // 2)
            k_value = self._get_spring_k_value(spring_config, num_nodes, density) * 1.2
            self.logger.info(
                f"Medium graph: Using {total_iterations} iterations with adaptive spacing"
            )
        else:
            total_iterations = spring_config.get("iterations", 200)
            k_value = self._get_spring_k_value(spring_config, num_nodes, density)

        # Get additional physics parameters
        spring_length = spring_config.get("spring_length", 1.0)
        center_gravity = spring_config.get("center_gravity", 0.01)
        enable_multistage = spring_config.get("enable_multistage", True)
        initial_k_multiplier = spring_config.get("initial_k_multiplier", 1.5)
        final_k_multiplier = spring_config.get("final_k_multiplier", 0.8)

        seed_value = 123

        # Log physics parameters
        self.logger.info(
            f"Spring physics: k={k_value:.3f}, length={spring_length:.2f}, "
            f"gravity={center_gravity:.3f}, multistage={enable_multistage}"
        )

        # Create progress tracker for the entire spring layout operation
        title = f"Calculating spring layout ({total_iterations} iterations)"
        with ProgressTracker(
            total=total_iterations,
            title=title,
            logger=self.logger,
        ) as tracker:
            if not enable_multistage or total_iterations <= 10:
                # Simple single-stage layout with chunked progress tracking
                pos = self._run_chunked_spring_layout(
                    G_undirected, k_value, total_iterations, seed_value, tracker
                )
            else:
                # Multi-stage progressive refinement with progress tracking
                # Stage 1: Initial separation (30% iterations, higher k)
                initial_iterations = max(10, int(total_iterations * 0.3))
                initial_k = k_value * initial_k_multiplier

                pos = nx.spring_layout(
                    G_undirected,
                    k=initial_k,
                    iterations=initial_iterations,
                    seed=seed_value,
                    weight="weight",
                )
                tracker.update(initial_iterations)

                # Stage 2: Refinement (50% iterations, normal k)
                refinement_iterations = max(10, int(total_iterations * 0.5))
                pos = nx.spring_layout(
                    G_undirected,
                    k=k_value,
                    iterations=refinement_iterations,
                    seed=seed_value,
                    pos=pos,
                    weight="weight",
                )
                tracker.update(initial_iterations + refinement_iterations)

                # Stage 3: Fine-tuning (remaining iterations, lower k)
                final_iterations = (
                    total_iterations - initial_iterations - refinement_iterations
                )
                if final_iterations > 0:
                    final_k = k_value * final_k_multiplier
                    pos = nx.spring_layout(
                        G_undirected,
                        k=final_k,
                        iterations=final_iterations,
                        seed=seed_value,
                        pos=pos,
                        weight="weight",
                    )
                tracker.update(total_iterations)

        return pos

    def _run_chunked_spring_layout(
        self,
        G: nx.Graph,
        k: float,
        iterations: int,
        seed: int,
        tracker: ProgressTracker,
    ) -> Dict[str, Tuple[float, float]]:
        """
        Run spring layout in chunks to provide progress updates.

        Args:
            G: NetworkX graph
            k: Spring constant
            iterations: Number of iterations
            seed: Random seed
            tracker: Progress tracker to update

        Returns:
            Dictionary of node positions
        """
        # Break into chunks for progress updates
        chunk_size = max(1, iterations // 10)  # Update progress every 10%
        remaining_iterations = iterations

        # Start with random positions
        pos = nx.spring_layout(G, k=k, iterations=0, seed=seed, weight="weight")

        completed_iterations = 0
        while remaining_iterations > 0:
            current_chunk = min(chunk_size, remaining_iterations)

            # Run spring layout for this chunk
            pos = nx.spring_layout(
                G,
                k=k,
                iterations=current_chunk,
                pos=pos,  # Continue from previous positions
                weight="weight",
            )

            completed_iterations += current_chunk
            remaining_iterations -= current_chunk

            # Update progress
            tracker.update(completed_iterations)

        return pos

    def _calculate_kamada_kawai_layout(
        self, G_undirected: nx.Graph
    ) -> Dict[str, Tuple[float, float]]:
        """Calculate Kamada-Kawai layout with comprehensive parameters."""
        png_config = self.vis_config.get("png_layout", {})
        kamada_config = (
            png_config.get("kamada_kawai", {}) if isinstance(png_config, dict) else {}
        )

        max_iterations = kamada_config.get("max_iterations", 1000)
        distance_scale = kamada_config.get("distance_scale", 1.0)

        self.logger.info(
            f"Kamada-Kawai: max_iter={max_iterations}, scale={distance_scale:.2f}"
        )

        with ProgressTracker(
            total=1,
            title="Calculating Kamada-Kawai layout",
            logger=self.logger,
        ) as tracker:
            # Note: NetworkX doesn't expose all Kamada-Kawai parameters, but we can scale the result
            pos = nx.kamada_kawai_layout(G_undirected, weight="weight")

            # Apply distance scaling
            if distance_scale != 1.0:
                pos = {
                    node: (x * distance_scale, y * distance_scale)
                    for node, (x, y) in pos.items()
                }

            tracker.update(1)

        return pos

    def _calculate_circular_layout(
        self, G_undirected: nx.Graph, graph: nx.DiGraph
    ) -> Dict[str, Tuple[float, float]]:
        """Calculate circular layout with community grouping and spacing options."""
        png_config = self.vis_config.get("png_layout", {})
        circular_config = (
            png_config.get("circular", {}) if isinstance(png_config, dict) else {}
        )

        radius = circular_config.get("radius")
        center = circular_config.get("center")
        start_angle = circular_config.get("start_angle", 0.0)
        group_by_community = circular_config.get("group_by_community", True)
        community_separation = circular_config.get("community_separation", 0.2)

        self.logger.info(
            f"Circular: radius={radius}, community_grouping={group_by_community}"
        )

        with ProgressTracker(
            total=1,
            title="Calculating circular layout",
            logger=self.logger,
        ) as tracker:
            if group_by_community:
                communities_dict = nx.get_node_attributes(graph, "community")
                if communities_dict:
                    # Group nodes by community and arrange in circular segments
                    pos = self._circular_layout_by_community(
                        G_undirected,
                        communities_dict,
                        radius,
                        center,
                        start_angle,
                        community_separation,
                    )
                else:
                    pos = nx.circular_layout(
                        G_undirected, scale=radius or 1.0, center=center
                    )
            else:
                pos = nx.circular_layout(
                    G_undirected, scale=radius or 1.0, center=center
                )

            tracker.update(1)

        return pos

    def _calculate_shell_layout(
        self, G_undirected: nx.Graph, graph: nx.DiGraph
    ) -> Dict[str, Tuple[float, float]]:
        """Calculate shell layout with community-based or centrality-based shells."""
        png_config = self.vis_config.get("png_layout", {})
        shell_config = (
            png_config.get("shell", {}) if isinstance(png_config, dict) else {}
        )

        arrange_by_community = shell_config.get("arrange_by_community", True)
        arrange_by_centrality = shell_config.get("arrange_by_centrality", False)
        centrality_metric = shell_config.get("centrality_metric", "degree")
        max_shells = shell_config.get("max_shells", 10)

        self.logger.info(
            f"Shell: community={arrange_by_community}, centrality={arrange_by_centrality}"
        )

        with ProgressTracker(
            total=1,
            title="Calculating shell layout",
            logger=self.logger,
        ) as tracker:
            if arrange_by_community:
                communities_dict = nx.get_node_attributes(graph, "community")
                if communities_dict:
                    # Create shells based on communities
                    nodelist = self._create_community_shells(
                        communities_dict, max_shells
                    )
                    pos = nx.shell_layout(G_undirected, nlist=nodelist)
                else:
                    pos = nx.shell_layout(G_undirected)
            elif arrange_by_centrality:
                # Create shells based on centrality values
                nodelist = self._create_centrality_shells(
                    graph, centrality_metric, max_shells
                )
                pos = nx.shell_layout(G_undirected, nlist=nodelist)
            else:
                pos = nx.shell_layout(G_undirected)

            tracker.update(1)

        return pos

    def _circular_layout_by_community(
        self,
        G: nx.Graph,
        communities_dict: Dict[str, int],
        radius: Optional[float],
        center: Optional[Tuple[float, float]],
        start_angle: float,
        community_separation: float,
    ) -> Dict[str, Tuple[float, float]]:
        """Create circular layout with communities grouped together."""
        # Group nodes by community
        communities: Dict[str, int] = {}
        for node, comm in communities_dict.items():
            if comm not in communities:
                communities[comm] = []
            communities[comm].append(node)

        # Calculate positions
        pos = {}
        total_nodes = len(G.nodes())
        current_angle = start_angle

        if radius is None:
            radius = 1.0
        if center is None:
            center = (0, 0)

        for _comm_id, nodes in communities.items():
            # Calculate angular space for this community
            comm_size = len(nodes)
            comm_angle_space = (2 * math.pi * comm_size / total_nodes) * (
                1 - community_separation
            )

            # Position nodes in this community
            for i, node in enumerate(nodes):
                angle = current_angle + (i * comm_angle_space / comm_size)
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                pos[node] = (x, y)

            # Move to next community with separation
            current_angle += comm_angle_space + (
                2 * math.pi * community_separation / len(communities)
            )

        return pos

    def _create_community_shells(
        self, communities_dict: Dict[str, int], max_shells: int
    ) -> List[List[str]]:
        """Create shell node lists based on communities."""
        communities: Dict[str, int] = {}
        for node, comm in communities_dict.items():
            if comm not in communities:
                communities[comm] = []
            communities[comm].append(node)

        # Distribute communities across shells
        nodelist = [[] for _ in range(min(max_shells, len(communities)))]
        for i, (_comm_id, nodes) in enumerate(communities.items()):
            shell_idx = i % len(nodelist)
            nodelist[shell_idx].extend(nodes)

        return [shell for shell in nodelist if shell]  # Remove empty shells

    def _create_centrality_shells(
        self, graph: nx.DiGraph, centrality_metric: str, max_shells: int
    ) -> List[List[str]]:
        """Create shell node lists based on centrality values."""
        # Get centrality values
        if centrality_metric == "degree":
            centrality = dict(graph.degree())
        elif centrality_metric == "betweenness":
            centrality = nx.get_node_attributes(graph, "betweenness")
        elif centrality_metric == "eigenvector":
            centrality = nx.get_node_attributes(graph, "eigenvector")
        else:
            centrality = dict(graph.degree())  # Fallback

        # Sort nodes by centrality
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)

        # Distribute into shells (highest centrality in center)
        nodelist = [[] for _ in range(max_shells)]
        nodes_per_shell = len(sorted_nodes) // max_shells + 1

        for i, (node, _) in enumerate(sorted_nodes):
            shell_idx = min(i // nodes_per_shell, max_shells - 1)
            nodelist[shell_idx].append(node)

        return [shell for shell in nodelist if shell]  # Remove empty shells

    def _get_spring_k_value(
        self, spring_config: Dict[str, Any], num_nodes: int, density: float
    ) -> float:
        """
        Get spring k-value with physics parameters and adaptive scaling.

        Args:
            spring_config: Spring configuration dictionary
            num_nodes: Number of nodes
            density: Graph density

        Returns:
            Effective k-value for spring layout
        """
        base_k = spring_config.get("k", 0.15)
        repulsion_strength = spring_config.get("repulsion_strength", 1.0)

        # Apply adaptive scaling
        adaptive_k = self._calculate_adaptive_k_value_from_base(
            base_k, num_nodes, density
        )

        # Apply repulsion strength multiplier
        effective_k = adaptive_k * repulsion_strength

        return effective_k

    def _calculate_adaptive_k_value_from_base(
        self, base_k: float, num_nodes: int, density: float
    ) -> float:
        """Calculate adaptive k-value from a given base value."""
        # Node count factor
        if num_nodes < 50:
            node_factor = 1.0
        elif num_nodes < 200:
            node_factor = 1.5
        elif num_nodes < 500:
            node_factor = 2.0
        elif num_nodes < 1000:
            node_factor = 2.5
        else:
            node_factor = 3.0

        # Density factor
        if density < 0.1:
            density_factor = 1.0
        elif density < 0.3:
            density_factor = 1.3
        elif density < 0.5:
            density_factor = 1.6
        else:
            density_factor = 2.0

        adaptive_k = base_k * node_factor * density_factor
        return min(max(adaptive_k, 0.1), 2.0)  # Bounds checking

    def _add_legend(self, graph: nx.DiGraph, ax) -> None:
        """
        Add legend to the matplotlib plot.

        Args:
            graph: The analyzed graph
            ax: Matplotlib axes object
        """
        # Only show legend if community detection was run
        communities_attr = nx.get_node_attributes(graph, "community")
        if communities_attr:
            num_communities = len(set(communities_attr.values()))
            color_maps = get_community_colors(num_communities)

            legend_elements = [
                mpatches.Patch(
                    facecolor=color_maps["rgba"][i],
                    edgecolor="black",
                    label=f"Community {i}",
                )
                for i in range(min(num_communities, 10))  # Limit legend entries
            ]
        else:
            # Add a single default legend element if analysis skipped
            legend_elements = [
                mpatches.Patch(
                    facecolor="#808080", edgecolor="black", label="Default/Unanalyzed"
                )
            ]

        # Add edge type indicators
        legend_elements.extend(
            [
                mpatches.Patch(
                    facecolor="none",
                    edgecolor="black",
                    linestyle="-",
                    label="Mutual Connection",
                ),
                mpatches.Patch(
                    facecolor="none",
                    edgecolor="black",
                    linestyle="--",
                    label="One-way Connection",
                ),
            ]
        )

        # Position legend outside the plot area to avoid covering the network
        ax.legend(
            handles=legend_elements,
            bbox_to_anchor=(1.02, 1),
            loc="upper left",
            framealpha=0.9,
            fontsize=10,  # Reduced from 30 to reasonable size
            borderaxespad=0,
        )
