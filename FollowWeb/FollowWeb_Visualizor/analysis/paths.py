"""
Path analysis module for shortest path and connectivity analysis.

This module provides the PathAnalyzer class for calculating shortest paths,
connectivity metrics, and path-finding operations.
"""

# Standard library imports
import logging
import random
import sys
import traceback
from collections import defaultdict
from typing import Any, Dict, List, Optional

# Third-party imports
import networkx as nx

# Conditional nx_parallel import (Python 3.11+ only)
try:
    if sys.version_info >= (3, 11):
        import nx_parallel  # noqa: F401
except ImportError:
    pass  # nx_parallel not available, use standard NetworkX

# Local imports
from ..utils import ProgressTracker


class PathAnalyzer:
    """
    Class for shortest path and connectivity analysis with control and performance optimization.

    Supports performance constraint validation, timing feedback, and sampling threshold
    configuration for large graph optimization.
    """

    def __init__(self, mode_manager=None, stages_controller=None) -> None:
        """
        Initialize the PathAnalyzer.

        Args:
            mode_manager: Optional AnalysisModeManager for performance optimization
            stages_controller: Optional PipelineStagesController for component control

        The PathAnalyzer handles shortest path calculations, connectivity analysis,
        and path-finding operations for social network analysis.
        """
        self.logger = logging.getLogger(__name__)
        self.mode_manager = mode_manager
        self.stages_controller = stages_controller

    def analyze_path_lengths(self, graph: nx.DiGraph) -> Dict[str, float]:
        """
        Calculates and prints "6 degrees of separation" metrics with progress tracking.

        Uses AnalysisModeManager for performance optimization and sampling threshold configuration
        for large graph optimization. Provides timing feedback and performance constraint validation.

        Args:
            graph: Input directed graph

        Returns:
            Dict[str, float]: Dictionary containing path analysis results
        """
        MIN_NODES_FOR_ANALYSIS = 2
        if graph.number_of_nodes() < MIN_NODES_FOR_ANALYSIS:
            self.logger.info(
                f"Graph has fewer than {MIN_NODES_FOR_ANALYSIS} nodes. Skipping path analysis."
            )
            return {}

        graph_size = graph.number_of_nodes()

        # Get performance configuration from mode manager
        if self.mode_manager:
            path_config = self.mode_manager.get_performance_config_for_component(
                "path_analysis", graph_size
            )

            # Check if path analysis should be skipped
            if path_config.get("skip_path_analysis", False):
                self.logger.info(
                    f"Path analysis skipped in {path_config['mode']} mode for large graph ({graph_size:,} nodes)"
                )
                return {}
        else:
            # Fallback configuration when no mode manager is provided
            path_config = {
                "sample_size": graph_size,
                "use_sampling": graph_size > 5000,
                "mode": "full",
            }

        # Validate performance constraints
        self._validate_path_analysis_constraints(graph_size, path_config)

        self.logger.info(
            "Analyzing connections (undirected) on the largest connected component..."
        )
        G_undir = graph.to_undirected()

        try:
            components = list(nx.connected_components(G_undir))
        except Exception as e:
            self.logger.error(f"Could not find connected components: {e}")
            return {}

        if not components:
            self.logger.info("Graph has no nodes.")
            return {}

        self.logger.info(f"Found {len(components)} separate component(s).")

        largest_component_nodes = max(components, key=len)
        G_largest_comp = G_undir.subgraph(largest_component_nodes).copy()

        num_nodes = G_largest_comp.number_of_nodes()
        num_edges = G_largest_comp.number_of_edges()

        self.logger.info(
            f"Largest component: {num_nodes:,} nodes, {num_edges:,} edges."
        )

        if num_nodes < MIN_NODES_FOR_ANALYSIS:
            self.logger.info(
                f"Largest component has fewer than {MIN_NODES_FOR_ANALYSIS} nodes. No paths to analyze."
            )
            return {}

        try:
            all_path_lengths_dist = defaultdict(int)
            total_pairs = 0
            sum_of_lengths = 0
            max_dist = 0

            # Use mode manager configuration for sampling decisions
            use_sampling = path_config.get("use_sampling", False)
            sample_size = path_config.get("sample_size", num_nodes)

            if use_sampling and sample_size < num_nodes:
                # Sample approach based on mode manager configuration
                actual_sample_size = min(sample_size, num_nodes)
                sample_nodes = random.sample(
                    list(G_largest_comp.nodes()), actual_sample_size
                )

                tracker_title = f"Calculating sampled shortest paths ({actual_sample_size} samples, {path_config['mode']} mode)"

                with ProgressTracker(
                    total=actual_sample_size, title=tracker_title, logger=self.logger
                ) as tracker:
                    for i, source in enumerate(sample_nodes):
                        current_node_count = i + 1
                        tracker.update(current_node_count)

                        try:
                            distances = dict(
                                nx.shortest_path_length(G_largest_comp, source=source)
                            )

                            # Process all distances from this sample node
                            for target, dist in distances.items():
                                if (
                                    dist > 0
                                    and target in sample_nodes
                                    and source < target
                                ):
                                    all_path_lengths_dist[dist] += 1
                                    total_pairs += 1
                                    sum_of_lengths += dist
                                    max_dist = max(max_dist, dist)
                        except Exception as e:
                            self.logger.warning(
                                f"Error processing sample node {source}: {e}"
                            )
                            continue

                # Scale results to estimate full graph statistics
                if total_pairs > 0:
                    scaling_factor = (num_nodes * (num_nodes - 1) // 2) / total_pairs
                    self.logger.info(
                        f"Scaling sampled results by factor {scaling_factor:.2f}"
                    )
                    for dist in all_path_lengths_dist:
                        all_path_lengths_dist[dist] = int(
                            all_path_lengths_dist[dist] * scaling_factor
                        )
                    total_pairs = int(total_pairs * scaling_factor)
            else:
                # Full calculation for smaller graphs or when sampling is disabled
                mode_info = (
                    f" ({path_config['mode']} mode)" if self.mode_manager else ""
                )
                tracker_title = f"Calculating all-pairs shortest paths{mode_info}"

                with ProgressTracker(
                    total=num_nodes, title=tracker_title, logger=self.logger
                ) as tracker:
                    for i, source in enumerate(G_largest_comp.nodes()):
                        current_node_count = i + 1
                        tracker.update(current_node_count)

                        try:
                            distances = dict(
                                nx.shortest_path_length(G_largest_comp, source=source)
                            )

                            for target, dist in distances.items():
                                if dist > 0 and source < target:
                                    all_path_lengths_dist[dist] += 1
                                    total_pairs += 1
                                    sum_of_lengths += dist
                                    max_dist = max(max_dist, dist)
                        except Exception as e:
                            self.logger.warning(f"Error processing node {source}: {e}")
                            continue

            if total_pairs == 0:
                self.logger.info(
                    "No paths found between nodes in the largest component."
                )
                return {}

            avg_path_len = sum_of_lengths / total_pairs
            diameter = max_dist

            self.logger.info(
                f"         > Average Degrees of Separation: {avg_path_len:.4f}"
            )
            self.logger.info(f"         > Maximum Degrees of Separation: {diameter}")

            self.logger.info("\n---- Path Length Distribution ----")
            self.logger.info("Separation |     # of Pairs | % of Total")
            self.logger.info("---------------------------------------")

            sorted_lengths = sorted(all_path_lengths_dist.keys())

            for length in sorted_lengths:
                count = all_path_lengths_dist[length]
                percentage = (count / total_pairs) * 100
                self.logger.info(
                    f"       {length:<8} | {count:>12,} | {percentage:6.2f}%"
                )

            return {
                "average_path_length": avg_path_len,
                "diameter": diameter,
                "total_pairs": total_pairs,
                "path_distribution": dict(all_path_lengths_dist),
            }

        except nx.NetworkXError as e:
            self.logger.error(f"NetworkX error during path analysis: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected error during path analysis: {e}")
            traceback.print_exc()
            return {}

    def get_contact_path(
        self, graph: nx.DiGraph, ego_username: str, target_username: str
    ) -> Optional[List[str]]:
        """
        Finds the shortest path from target to ego.

        Args:
            graph: Input directed graph
            ego_username: Username of the ego node
            target_username: Username of the target node

        Returns:
            Optional[List[str]]: The path (a list of nodes) if found, None otherwise
        """
        if ego_username not in graph or target_username not in graph:
            return None

        try:
            path = nx.shortest_path(graph, source=target_username, target=ego_username)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                f"Unexpected error in get_contact_path ({target_username}): {e}"
            )
            return None

    def print_detailed_contact_path(
        self, graph: nx.DiGraph, ego_username: str, target_username: str
    ) -> bool:
        """
        Finds and prints a detailed "chain of influence" from a target user back to the ego.

        Args:
            graph: Input directed graph
            ego_username: Username of the ego node
            target_username: Username of the target node

        Returns:
            bool: True if a path was found, False otherwise
        """
        logger = logging.getLogger(__name__)
        logger.info(f"\n---- Finding Path: {target_username} -> {ego_username} ----")

        if ego_username not in graph:
            logger.error(f"❌ Ego node '{ego_username}' not in the *full* graph.")
            return False
        if target_username not in graph:
            logger.error(f"❌ Target node '{target_username}' not in the *full* graph.")
            logger.info(
                "       This person might not be in your L1/L2 network, or you may have a typo."
            )
            return False

        path = self.get_contact_path(graph, ego_username, target_username)

        if path:
            logger.info("\n✅ SUCCESS: Contact path found!")

            logger.info("       Follows Chain (Target to Ego):")
            for i in range(len(path) - 1):
                logger.info(f"         {path[i]:<20} -> follows -> {path[i + 1]}")

            logger.info(f"       Path length: {len(path) - 1} step(s).")

            logger.info("       Action Plan (Read from bottom up):")
            logger.info(f"         1. You contact:         {path[-2]}")

            action_step = 2
            for i in range(len(path) - 2, 0, -1):
                logger.info(
                    f"         {action_step}. {path[i]} contacts: {path[i - 1]}"
                )
                action_step += 1

            logger.info(f"         ...who can contact '{path[0]}'.")
            return True
        else:
            logger.info(
                f"\n*** NO PATH found from '{target_username}' to '{ego_username}'. ***"
            )
            logger.info("       No 'chain of influence' exists in your network.")
            return False

    def _validate_path_analysis_constraints(
        self, graph_size: int, config: Dict[str, Any]
    ) -> None:
        """
        Validate performance constraints for path analysis and provide timing feedback.

        Args:
            graph_size: Number of nodes in the graph
            config: Path analysis configuration from mode manager
        """
        mode = config.get("mode", "unknown")

        # Provide performance warnings based on graph size and mode
        # Performance warnings for path analysis
        if mode == "fast" and graph_size > 20000:
            self.logger.warning(
                "Very large graph in FAST mode - path analysis may still be slow"
            )
        elif mode == "full" and graph_size > 5000:
            self.logger.warning(
                "Large graph in FULL mode - consider using FAST or MEDIUM mode for better performance"
            )

        # Estimate timing for very large graphs
        if graph_size > 50000:
            estimated_time = self._estimate_path_analysis_time(graph_size, config)
            if estimated_time > 300:  # More than 5 minutes
                self.logger.warning(
                    f"Path analysis estimated to take {estimated_time // 60:.0f}+ minutes for this graph size"
                )
                self.logger.warning(
                    "Consider using FAST mode or disabling path analysis for better performance"
                )

    def _estimate_path_analysis_time(
        self, graph_size: int, config: Dict[str, Any]
    ) -> float:
        """
        Estimate path analysis execution time based on graph size and configuration.

        Args:
            graph_size: Number of nodes in the graph
            config: Path analysis configuration

        Returns:
            float: Estimated time in seconds
        """
        # Base time estimation (very rough approximation)
        if config.get("use_sampling", False):
            sample_size = config.get("sample_size", graph_size)
            # Sampling reduces complexity significantly
            estimated_seconds = (sample_size**1.5) / 1000
        else:
            # Full analysis has quadratic complexity
            estimated_seconds = (graph_size**2) / 100000

        # Adjust based on mode
        mode = config.get("mode", "full")
        if mode == "fast":
            estimated_seconds *= 0.3  # Fast mode optimizations
        elif mode == "medium":
            estimated_seconds *= 0.6  # Medium mode optimizations

        return max(1.0, estimated_seconds)  # Minimum 1 second
