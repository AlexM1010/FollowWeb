"""
Partition results merger for distributed graph processing.

This module provides functionality for merging analysis results from
distributed partition processing into a coherent final graph.

Classes:
    PartitionResultsMerger: Merges results from all partitions
    MergedResults: Combined results from all partitions
"""

import logging
import math
from dataclasses import dataclass
from pathlib import Path

import networkx as nx


@dataclass
class MergedResults:
    """Merged results from all partitions."""

    global_communities: dict[str, int]
    global_centrality: dict[str, float]
    global_layout: dict[str, tuple[float, float]]
    partition_count: int
    total_nodes: int
    merge_time: float
    logs: str


class PartitionResultsMerger:
    """
    Merge results from distributed partition analysis.

    Features:
    - Community assignment merging across partitions
    - Centrality score aggregation and normalization
    - Hierarchical layout positioning
    - Boundary node handling
    - Final graph creation with merged attributes
    """

    def __init__(self):
        """Initialize partition results merger."""
        self.logger = logging.getLogger(__name__)

    def load_all_results(self, results_dir: str) -> list:
        """
        Load all partition results from artifacts.

        Args:
            results_dir: Directory containing partition result files

        Returns:
            List[PartitionResults]: List of partition results
        """
        import joblib

        results = []
        results_path = Path(results_dir)

        if not results_path.exists():
            raise FileNotFoundError(f"Results directory not found: {results_dir}")

        # Load all partition result files
        result_files = sorted(results_path.glob("partition-*-results.pkl"))

        if not result_files:
            raise FileNotFoundError(f"No partition result files found in {results_dir}")

        self.logger.info(f"Loading {len(result_files)} partition results")

        for result_file in result_files:
            self.logger.debug(f"Loading {result_file}")
            result = joblib.load(result_file)
            results.append(result)

        self.logger.info(f"Loaded {len(results)} partition results")

        return results

    def merge_communities(self, partition_results: list) -> dict[str, int]:
        """
        Merge community assignments across partitions.

        Combines local community assignments from each partition and
        renumbers them globally to avoid conflicts.

        Args:
            partition_results: List of PartitionResults from all partitions

        Returns:
            Dict[str, int]: Global mapping of node_id to community_id
        """
        self.logger.info("Merging community assignments")

        global_communities = {}
        community_offset = 0

        for result in partition_results:
            # Add offset to avoid community ID conflicts
            for node, comm_id in result.communities.items():
                global_communities[node] = comm_id + community_offset

            # Update offset for next partition
            unique_communities = len(set(result.communities.values()))
            community_offset += unique_communities

            self.logger.debug(
                f"Partition {result.partition_id}: {unique_communities} communities, "
                f"offset now {community_offset}"
            )

        self.logger.info(
            f"Merged {len(global_communities)} nodes into {community_offset} global communities"
        )

        return global_communities

    def merge_centrality(self, partition_results: list) -> dict[str, float]:
        """
        Merge centrality scores across partitions.

        Aggregates betweenness centrality scores from all partitions and
        normalizes to [0, 1] range.

        Args:
            partition_results: List of PartitionResults from all partitions

        Returns:
            Dict[str, float]: Global mapping of node_id to normalized centrality
        """
        self.logger.info("Merging centrality scores")

        all_centrality = {}

        # Aggregate centrality scores from all partitions
        for result in partition_results:
            all_centrality.update(result.centrality)

        # Normalize to [0, 1]
        if all_centrality:
            max_centrality = max(all_centrality.values())
            if max_centrality > 0:
                all_centrality = {
                    k: v / max_centrality for k, v in all_centrality.items()
                }

        self.logger.info(
            f"Merged centrality for {len(all_centrality)} nodes "
            f"(max: {max(all_centrality.values()) if all_centrality else 0:.4f})"
        )

        return all_centrality

    def merge_layouts(self, partition_results: list) -> dict[str, tuple[float, float]]:
        """
        Merge layout positions across partitions.

        Uses community-based hierarchical layout approach. Positions partitions
        in a grid and scales local layouts to fit within grid cells.

        Args:
            partition_results: List of PartitionResults from all partitions

        Returns:
            Dict[str, Tuple[float, float]]: Global mapping of node_id to (x, y)
        """
        self.logger.info("Merging layout positions")

        global_layout = {}

        # Calculate grid dimensions for partition placement
        grid_size = math.ceil(math.sqrt(len(partition_results)))
        cell_size = 100  # Size of each grid cell

        self.logger.debug(
            f"Using {grid_size}x{grid_size} grid with {cell_size} unit cells"
        )

        for i, result in enumerate(partition_results):
            # Calculate grid position for this partition
            grid_x = (i % grid_size) * cell_size
            grid_y = (i // grid_size) * cell_size

            # Scale local layout to fit within grid cell
            # Find bounds of local layout
            if result.layout:
                local_x = [pos[0] for pos in result.layout.values()]
                local_y = [pos[1] for pos in result.layout.values()]

                min_x, max_x = min(local_x), max(local_x)
                min_y, max_y = min(local_y), max(local_y)

                # Calculate scaling factors
                x_range = max_x - min_x if max_x > min_x else 1
                y_range = max_y - min_y if max_y > min_y else 1

                # Scale and translate positions
                for node, (x, y) in result.layout.items():
                    # Normalize to [0, 1]
                    norm_x = (x - min_x) / x_range if x_range > 0 else 0.5
                    norm_y = (y - min_y) / y_range if y_range > 0 else 0.5

                    # Scale to cell size (with padding)
                    padding = cell_size * 0.1
                    scaled_x = norm_x * (cell_size - 2 * padding) + padding
                    scaled_y = norm_y * (cell_size - 2 * padding) + padding

                    # Translate to grid position
                    global_layout[node] = (grid_x + scaled_x, grid_y + scaled_y)

            self.logger.debug(
                f"Partition {result.partition_id}: positioned at grid ({i % grid_size}, {i // grid_size})"
            )

        self.logger.info(f"Merged layout for {len(global_layout)} nodes")

        return global_layout

    def create_final_graph(
        self, original_graph: nx.DiGraph, merged_results: MergedResults
    ) -> nx.DiGraph:
        """
        Create final graph with merged analysis results.

        Adds community and centrality attributes to the original graph.
        Layout positions are typically stored separately for visualization.

        Args:
            original_graph: Original graph before partitioning
            merged_results: Merged results from all partitions

        Returns:
            nx.DiGraph: Graph with merged analysis attributes
        """
        self.logger.info("Creating final graph with merged results")

        # Add community attributes
        nx.set_node_attributes(
            original_graph, merged_results.global_communities, "community"
        )

        # Add centrality attributes
        nx.set_node_attributes(
            original_graph, merged_results.global_centrality, "betweenness"
        )

        # Verify attributes were added
        sample_node = next(iter(original_graph.nodes()))
        has_community = "community" in original_graph.nodes[sample_node]
        has_centrality = "betweenness" in original_graph.nodes[sample_node]

        self.logger.info(
            f"Final graph created: {original_graph.number_of_nodes()} nodes, "
            f"{original_graph.number_of_edges()} edges, "
            f"community={has_community}, centrality={has_centrality}"
        )

        return original_graph

    def merge_all(
        self, partition_results: list, original_graph: nx.DiGraph
    ) -> MergedResults:
        """
        Merge all partition results into final graph.

        Convenience method that performs all merging steps and creates
        the final graph with merged attributes.

        Args:
            partition_results: List of PartitionResults from all partitions
            original_graph: Original graph before partitioning

        Returns:
            MergedResults: Complete merged results
        """
        import time

        start_time = time.perf_counter()

        self.logger.info(f"Merging results from {len(partition_results)} partitions")

        # Merge communities
        global_communities = self.merge_communities(partition_results)

        # Merge centrality
        global_centrality = self.merge_centrality(partition_results)

        # Merge layouts
        global_layout = self.merge_layouts(partition_results)

        # Calculate total nodes
        total_nodes = len(global_communities)

        merge_time = time.perf_counter() - start_time

        # Create merged results
        merged_results = MergedResults(
            global_communities=global_communities,
            global_centrality=global_centrality,
            global_layout=global_layout,
            partition_count=len(partition_results),
            total_nodes=total_nodes,
            merge_time=merge_time,
            logs=f"Merged {len(partition_results)} partitions in {merge_time:.2f}s",
        )

        # Add attributes to original graph
        self.create_final_graph(original_graph, merged_results)

        self.logger.info(f"Merge complete: {total_nodes} nodes, {merge_time:.2f}s")

        return merged_results


__all__ = ["PartitionResultsMerger", "MergedResults"]
