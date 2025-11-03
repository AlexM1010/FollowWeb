"""
Metrics calculation module for FollowWeb visualization.

This module handles the calculation and caching of visualization metrics for both HTML and PNG outputs.
It includes unified metrics calculation, node and edge metrics, and color scheme management.
"""

import logging
import sys
import time
from typing import Any, Dict, Tuple

import networkx as nx

# Conditional nx_parallel import (Python 3.11+ only)
try:
    if sys.version_info >= (3, 11):
        import nx_parallel  # noqa: F401
except ImportError:
    pass  # nx_parallel not available, use standard NetworkX

from ..core.types import ColorScheme, EdgeMetric, NodeMetric, VisualizationMetrics
from ..data.cache import (
    calculate_graph_hash,
    get_cache_manager,
    get_cached_node_attributes,
    get_cached_undirected_graph,
)
from ..output.formatters import EmojiFormatter
from ..utils import ProgressTracker
from .colors import get_community_colors, get_scaled_size


class MetricsCalculator:
    """
    Calculates and caches visualization metrics for both HTML and PNG outputs.

    This class provides a unified interface for calculating all visualization metrics
    once and reusing them across different output formats. It includes caching
    functionality to avoid recalculating metrics for the same graph.
    """

    def __init__(self, vis_config: Dict[str, Any]) -> None:
        """
        Initialize the shared metrics calculator with visualization configuration.

        Args:
            vis_config: Visualization configuration dictionary containing node size metrics,
                       scaling algorithms, colors, and other visual parameters

        Raises:
            KeyError: If required configuration keys are missing
        """
        self.vis_config = vis_config
        self.logger = logging.getLogger(__name__)

        # Use centralized cache manager instead of local caches
        self.cache_manager = get_cache_manager()

        # Cache configuration
        self.cache_enabled = vis_config.get("shared_metrics", {}).get(
            "enable_caching", True
        )
        self.cache_timeout = vis_config.get("shared_metrics", {}).get(
            "cache_timeout_seconds", 300
        )

    def clear_caches(self) -> None:
        """
        Clear all internal caches to free memory.

        This method should be called when processing multiple graphs in sequence
        to prevent memory accumulation from cached results.
        """
        # Use centralized cache clearing
        self.cache_manager.clear_all_caches()
        self.logger.debug("MetricsCalculator caches cleared")

    def calculate_all_metrics(self, graph: nx.DiGraph) -> VisualizationMetrics:
        """
        Calculate all visualization metrics for the given graph with comprehensive error handling.

        This method calculates node metrics, edge metrics, layout positions, and color schemes
        in a single pass, caching the results for reuse across different output formats.
        Analysis continues even if individual formatting operations fail.

        Args:
            graph: The analyzed graph with node and edge attributes

        Returns:
            VisualizationMetrics object containing all calculated metrics

        Raises:
            ValueError: If the graph is empty or missing required attributes
        """
        try:
            if graph.number_of_nodes() == 0:
                # Return empty metrics for empty graph
                return VisualizationMetrics(
                    node_metrics={},
                    edge_metrics={},
                    layout_positions={},
                    color_schemes=ColorScheme({}, {}, "#6e6e6e", "#c0c0c0"),
                    graph_hash="empty_graph",
                )
        except Exception:
            # If even basic graph checking fails, return minimal safe metrics
            return VisualizationMetrics(
                node_metrics={},
                edge_metrics={},
                layout_positions={},
                color_schemes=ColorScheme({}, {}, "#6e6e6e", "#c0c0c0"),
                graph_hash="error_fallback",
            )

        try:
            # Generate graph hash using centralized function
            graph_hash = calculate_graph_hash(graph)

            # For now, we'll calculate fresh metrics each time since VisualizationMetrics
            # is a complex object that would need special serialization for caching
            # This could be enhanced in the future with proper serialization

            progress_msg = EmojiFormatter.format(
                "progress", "Calculating shared visualization metrics..."
            )
            self.logger.info(f"\n{progress_msg}")
            start_time = time.perf_counter()

            # Calculate color schemes first (needed for other calculations)
            color_schemes = self._calculate_color_schemes(graph)

            # Calculate node metrics
            node_metrics = self._calculate_node_metrics(graph, color_schemes)

            # Calculate edge metrics
            edge_metrics = self._calculate_edge_metrics(graph, color_schemes)

            # Calculate layout positions (spring layout as default for consistency)
            layout_positions = self._calculate_spring_layout(graph, edge_metrics)

            # Create the complete metrics object
            metrics = VisualizationMetrics(
                node_metrics=node_metrics,
                edge_metrics=edge_metrics,
                layout_positions=layout_positions,
                color_schemes=color_schemes,
                graph_hash=graph_hash,
            )

            # Note: Complex VisualizationMetrics objects are not cached in the centralized system
            # Individual components (layouts, colors, etc.) are cached separately

            end_time = time.perf_counter()
            timer_msg = EmojiFormatter.format(
                "timer",
                f"Shared metrics calculation completed in {end_time - start_time:.2f}s",
            )
            self.logger.info(timer_msg)
            self.logger.info("")  # Add spacing after shared metrics completion

            return metrics

        except Exception as e:
            # If metrics calculation fails, create minimal fallback metrics to allow analysis to continue
            self.logger.warning(f"Metrics calculation failed, using fallback: {e}")

            # Create basic fallback metrics
            fallback_metrics = VisualizationMetrics(
                node_metrics={},
                edge_metrics={},
                layout_positions={},
                color_schemes=ColorScheme(
                    {0: "#808080"}, {0: (0.5, 0.5, 0.5, 1.0)}, "#6e6e6e", "#c0c0c0"
                ),
                graph_hash="fallback_metrics",
            )

            # Try to populate basic node metrics for visualization
            try:
                for node in graph.nodes():
                    fallback_metrics.node_metrics[node] = NodeMetric(
                        size=10.0,  # Default size
                        color_hex="#808080",  # Default gray
                        color_rgba=(0.5, 0.5, 0.5, 1.0),
                        community=0,
                        centrality_values={
                            "degree": 1,
                            "betweenness": 0.0,
                            "eigenvector": 0.0,
                        },
                    )
            except Exception:
                pass  # Continue with empty metrics if even this fails

            return fallback_metrics

    def _calculate_color_schemes(self, graph: nx.DiGraph) -> ColorScheme:
        """
        Calculate color schemes for communities and edges.

        Args:
            graph: The analyzed graph

        Returns:
            ColorScheme object with all color information
        """
        # Handle the case where analysis was skipped (attributes are missing)
        # Use cached node attributes to avoid repeated graph traversals
        communities_attr = get_cached_node_attributes(graph, "community")
        if not communities_attr:
            # Set all community IDs to 0 for fallback
            num_communities = 1
            community_colors = get_community_colors(num_communities)
        else:
            num_communities = len(set(communities_attr.values()))
            community_colors = get_community_colors(num_communities)

        return ColorScheme(
            hex_colors=community_colors["hex"],
            rgba_colors=community_colors["rgba"],
            bridge_color=self.vis_config.get("bridge_color", "#6e6e6e"),
            intra_community_color=self.vis_config.get(
                "intra_community_color", "#c0c0c0"
            ),
        )

    def _calculate_node_metrics(
        self, graph: nx.DiGraph, color_schemes: ColorScheme
    ) -> Dict[str, NodeMetric]:
        """
        Calculate node visualization metrics.

        Args:
            graph: The analyzed graph
            color_schemes: Color scheme information

        Returns:
            Dictionary mapping node names to NodeMetric objects
        """
        # Handle the case where analysis was skipped (attributes are missing)
        # Use cached node attributes to avoid repeated graph traversals
        communities_attr = get_cached_node_attributes(graph, "community")
        if not communities_attr:
            # Set all community IDs to 0
            nx.set_node_attributes(graph, dict.fromkeys(graph.nodes(), 0), "community")

            # Set all centrality/degree to 0 or 1 for visualization fallback
            for n in graph.nodes():
                graph.nodes[n]["degree"] = graph.degree(
                    n
                )  # Use actual degree for sizing fallback
                graph.nodes[n]["betweenness"] = 0.0
                graph.nodes[n]["eigenvector"] = 0.0

        node_metrics = {}
        size_metric = self.vis_config["node_size_metric"]
        base_size = self.vis_config["base_node_size"]
        multiplier = self.vis_config["node_size_multiplier"]
        scaling_alg = self.vis_config["scaling_algorithm"]

        for node, attrs in graph.nodes(data=True):
            # Use actual metric if available, otherwise fallback to degree
            metric_value = attrs.get(size_metric, attrs.get("degree", 1))
            community_id = attrs.get("community", 0)

            node_size = get_scaled_size(
                metric_value, base_size, multiplier, scaling_alg
            )

            # Get centrality values
            centrality_values = {
                "degree": attrs.get("degree", 0),
                "betweenness": attrs.get("betweenness", 0),
                "eigenvector": attrs.get("eigenvector", 0),
            }

            node_metrics[node] = NodeMetric(
                size=node_size,
                color_hex=color_schemes.hex_colors.get(community_id, "#808080"),
                color_rgba=color_schemes.rgba_colors.get(
                    community_id, (0.5, 0.5, 0.5, 1.0)
                ),
                community=community_id,
                centrality_values=centrality_values,
            )

        return node_metrics

    def _calculate_edge_metrics(
        self, graph: nx.DiGraph, color_schemes: ColorScheme
    ) -> Dict[Tuple[str, str], EdgeMetric]:
        """
        Calculate edge visualization metrics with memory optimization.

        Args:
            graph: The analyzed graph
            color_schemes: Color scheme information

        Returns:
            Dictionary mapping edge tuples to EdgeMetric objects
        """
        # OPTIMIZATION: Cache configuration values to avoid repeated dict lookups
        base_edge_width = self.vis_config.get("base_edge_width", 0.5)
        edge_width_multiplier = self.vis_config.get("edge_width_multiplier", 1.5)
        edge_width_scaling = self.vis_config.get("edge_width_scaling", "logarithmic")

        # Use cached undirected graph conversion
        graph_undirected = get_cached_undirected_graph(graph)

        # OPTIMIZATION: Pre-compute edge existence for faster lookups
        directed_edges = set(graph.edges())

        # Use cached community attributes to avoid repeated lookups
        communities_attr = get_cached_node_attributes(graph, "community")
        if not communities_attr:
            communities_attr = dict.fromkeys(graph.nodes(), 0)

        edge_metrics: Dict[Tuple[str, str], Dict[str, Any]] = {}
        edges_list = list(graph_undirected.edges())
        total_edges = len(edges_list)

        # Handle empty graph case
        if total_edges == 0:
            return edge_metrics

        with ProgressTracker(
            total=total_edges,
            title="Calculating shared edge metrics",
            logger=self.logger,
        ) as tracker:
            # OPTIMIZATION: Process edges in batches to reduce memory pressure
            batch_size = min(1000, max(100, total_edges // 10))

            for batch_start in range(0, total_edges, batch_size):
                batch_end = min(batch_start + batch_size, total_edges)
                batch_edges = edges_list[batch_start:batch_end]

                # Process batch
                for i, (u, v) in enumerate(batch_edges):
                    global_i = batch_start + i

                    # OPTIMIZATION: Use cached community lookups
                    u_comm = communities_attr.get(u, 0)
                    v_comm = communities_attr.get(v, 0)

                    # Calculate common neighbors efficiently
                    try:
                        # OPTIMIZATION: Use generator expression to avoid creating intermediate lists
                        num_common = sum(
                            1 for _ in nx.common_neighbors(graph_undirected, u, v)
                        )
                    except nx.NetworkXError:
                        num_common = 0

                    # Calculate edge width
                    edge_width = get_scaled_size(
                        num_common,
                        base_edge_width,
                        edge_width_multiplier,
                        edge_width_scaling,
                    )

                    # Determine if bridge edge
                    is_bridge = u_comm != v_comm

                    # Set edge color
                    if is_bridge:
                        edge_color = color_schemes.bridge_color
                    else:
                        edge_color = color_schemes.hex_colors.get(
                            u_comm, color_schemes.intra_community_color
                        )

                    # OPTIMIZATION: Use pre-computed edge set for faster lookups
                    has_u_v = (u, v) in directed_edges
                    has_v_u = (v, u) in directed_edges
                    is_mutual = has_u_v and has_v_u

                    if is_mutual:
                        # Add ONE entry for the mutual pair
                        edge_metrics[(u, v)] = EdgeMetric(
                            width=edge_width,
                            color=edge_color,
                            is_mutual=True,
                            is_bridge=is_bridge,
                            common_neighbors=num_common,
                            u_comm=u_comm,
                            v_comm=v_comm,
                        )
                    else:
                        # Add entries for each one-way edge that exists
                        if has_u_v:
                            edge_metrics[(u, v)] = EdgeMetric(
                                width=edge_width,
                                color=edge_color,
                                is_mutual=False,
                                is_bridge=is_bridge,
                                common_neighbors=num_common,
                                u_comm=u_comm,
                                v_comm=v_comm,
                            )

                        if has_v_u:
                            edge_metrics[(v, u)] = EdgeMetric(
                                width=edge_width,
                                color=edge_color,
                                is_mutual=False,
                                is_bridge=is_bridge,
                                common_neighbors=num_common,
                                u_comm=v_comm,
                                v_comm=u_comm,
                            )

                    tracker.update(global_i + 1)

        return edge_metrics

    def _calculate_spring_layout(
        self, graph: nx.DiGraph, edge_metrics: Dict[Tuple[str, str], EdgeMetric]
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate spring layout positions using edge weights with centralized caching.

        Args:
            graph: The analyzed graph
            edge_metrics: Edge metrics containing width information for weights

        Returns:
            Dictionary mapping node names to (x, y) position tuples
        """
        spring_config = self.vis_config.get("static_image", {}).get("spring", {})
        iterations = spring_config.get(
            "iterations", 200
        )  # Increased for better physics
        k_value = spring_config.get("k", 0.15)

        # Create params for caching
        params = {"iterations": iterations, "k": k_value, "layout_type": "spring"}

        # Check centralized cache first
        cached_positions = self.cache_manager.get_cached_layout_positions(
            graph, "spring", params
        )
        if cached_positions is not None:
            return cached_positions

        start_time = time.perf_counter()

        # Use improved spring layout with accurate progress tracking
        title = (
            f"Calculating spring layout for shared metrics ({iterations} iterations)"
        )
        with ProgressTracker(
            total=iterations,
            title=title,
            logger=self.logger,
        ) as tracker:
            # Use the chunked spring layout implementation for accurate progress
            pos = self._run_chunked_spring_layout(
                graph, k_value, iterations, 123, tracker
            )

        # Cache the results using centralized cache
        self.cache_manager.cache_layout_positions(graph, "spring", pos, params)

        end_time = time.perf_counter()
        timer_msg = EmojiFormatter.format(
            "timer",
            f"Spring layout calculation completed in {end_time - start_time:.2f}s",
        )
        self.logger.info(timer_msg)
        # Add spacing after timer message for consistent formatting
        self.logger.info("")

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
