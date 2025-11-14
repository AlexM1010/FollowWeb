"""
Graph partitioning system for large-scale network analysis.

This module provides graph partitioning capabilities for distributed processing
of large graphs (600K+ nodes) across GitHub Actions runners. It uses METIS
algorithm for optimal partitioning with NetworkX fallback.

Classes:
    GraphPartitioner: Partitions graphs using METIS or NetworkX fallback
    PartitionInfo: Metadata about a graph partition
"""

import logging
import math
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from ..utils.parallel import ParallelProcessingManager


@dataclass
class PartitionInfo:
    """Information about a graph partition."""

    partition_id: int
    node_count: int
    edge_count: int
    boundary_node_count: int
    artifact_path: str


class GraphPartitioner:
    """
    Partition large graphs for distributed processing.

    Uses METIS algorithm (via pymetis) for optimal partitioning with minimal
    edge cuts. Falls back to NetworkX-based partitioning if METIS unavailable.

    Features:
    - Auto-scaling partition size based on detected RAM
    - METIS partitioning for minimal edge cuts
    - NetworkX fallback for development/testing
    - Compressed partition storage with joblib
    """

    def __init__(self):
        """Initialize graph partitioner with resource detection."""
        self.logger = logging.getLogger(__name__)
        self.parallel_manager = ParallelProcessingManager()
        self.detected_cores = self.parallel_manager._cpu_count
        self.detected_ram = self._detect_available_ram()

        # Check METIS availability
        self.metis_available = self._check_metis_availability()

    def _detect_available_ram(self) -> int:
        """
        Detect available RAM in GB.

        Returns:
            int: Available RAM in GB (defaults to 7 for GitHub Actions)
        """
        try:
            import psutil

            return int(psutil.virtual_memory().available / (1024**3))
        except ImportError:
            self.logger.debug("psutil not available, using default RAM estimate")
            return 7  # Default to GitHub Actions standard

    def _check_metis_availability(self) -> bool:
        """
        Check if pymetis is available and working.

        Returns:
            bool: True if pymetis is available and functional
        """
        try:
            import pymetis  # noqa: F401

            return True
        except ImportError:
            self.logger.info(
                "pymetis not available, will use NetworkX fallback for partitioning"
            )
            return False

    def calculate_optimal_partitions(self, total_nodes: int) -> int:
        """
        Auto-calculate partition count based on detected resources.

        Partition sizes are tuned for GitHub Actions runners:
        - 50K nodes per partition for 4 cores + 7 GB RAM
        - 30K nodes per partition for 2 cores + 4 GB RAM
        - 10K nodes per partition for 1 core + 2 GB RAM

        Args:
            total_nodes: Total number of nodes in the graph

        Returns:
            int: Optimal number of partitions
        """
        if self.detected_ram >= 7:
            nodes_per_partition = 50000  # Optimal for 7 GB
        elif self.detected_ram >= 4:
            nodes_per_partition = 30000  # Conservative for 4 GB
        else:
            nodes_per_partition = 10000  # Minimal for 2 GB

        num_partitions = math.ceil(total_nodes / nodes_per_partition)

        self.logger.info(
            f"Calculated {num_partitions} partitions for {total_nodes} nodes "
            f"({nodes_per_partition} nodes/partition, {self.detected_ram} GB RAM)"
        )

        return num_partitions

    def partition_graph(
        self, graph: nx.DiGraph, num_partitions: int
    ) -> list[nx.DiGraph]:
        """
        Partition graph using METIS to minimize edge cuts.

        Uses METIS algorithm (industry standard) for optimal partitioning.
        Falls back to NetworkX-based partitioning if METIS unavailable.

        Args:
            graph: NetworkX directed graph to partition
            num_partitions: Number of partitions to create

        Returns:
            List[nx.DiGraph]: List of graph partitions
        """
        if num_partitions <= 1:
            self.logger.info("Single partition requested, returning original graph")
            return [graph]

        if self.metis_available:
            return self._partition_with_metis(graph, num_partitions)
        else:
            return self._partition_networkx_fallback(graph, num_partitions)

    def _partition_with_metis(
        self, graph: nx.DiGraph, num_partitions: int
    ) -> list[nx.DiGraph]:
        """
        Partition graph using METIS algorithm.

        METIS provides optimal partitioning with minimal edge cuts and
        balanced partition sizes.

        Args:
            graph: NetworkX directed graph to partition
            num_partitions: Number of partitions to create

        Returns:
            List[nx.DiGraph]: List of graph partitions
        """
        import pymetis

        self.logger.info(
            f"Partitioning graph with {graph.number_of_nodes()} nodes "
            f"into {num_partitions} partitions using METIS"
        )

        # Convert to undirected for partitioning
        undirected = graph.to_undirected()

        # Create node mapping (METIS requires 0-indexed nodes)
        node_list = list(undirected.nodes())
        node_to_idx = {node: idx for idx, node in enumerate(node_list)}

        # Build adjacency list for METIS
        adjacency = []
        for node in node_list:
            neighbors = [node_to_idx[n] for n in undirected.neighbors(node)]
            adjacency.append(neighbors)

        # Run METIS partitioning
        try:
            n_cuts, membership = pymetis.part_graph(num_partitions, adjacency=adjacency)

            self.logger.info(f"METIS partitioning complete with {n_cuts} edge cuts")

            # Create partition subgraphs
            partitions = []
            for partition_id in range(num_partitions):
                # Get nodes in this partition
                partition_nodes = [
                    node_list[idx]
                    for idx, part in enumerate(membership)
                    if part == partition_id
                ]

                # Create subgraph (directed)
                partition_graph = nx.DiGraph(graph.subgraph(partition_nodes))
                partitions.append(partition_graph)

                self.logger.debug(
                    f"Partition {partition_id}: {partition_graph.number_of_nodes()} nodes, "
                    f"{partition_graph.number_of_edges()} edges"
                )

            return partitions

        except Exception as e:
            self.logger.warning(
                f"METIS partitioning failed: {e}, falling back to NetworkX"
            )
            return self._partition_networkx_fallback(graph, num_partitions)

    def _partition_networkx_fallback(
        self, graph: nx.DiGraph, num_partitions: int
    ) -> list[nx.DiGraph]:
        """
        Partition graph using NetworkX-based approach (fallback).

        Uses community detection to create balanced partitions when METIS
        is unavailable. Less optimal than METIS but acceptable for development.

        Args:
            graph: NetworkX directed graph to partition
            num_partitions: Number of partitions to create

        Returns:
            List[nx.DiGraph]: List of graph partitions
        """
        self.logger.info(
            f"Partitioning graph with {graph.number_of_nodes()} nodes "
            f"into {num_partitions} partitions using NetworkX fallback"
        )

        # Convert to undirected for community detection
        undirected = graph.to_undirected()

        # Use Louvain community detection
        from networkx.algorithms import community

        communities = list(community.louvain_communities(undirected, seed=123))

        self.logger.debug(f"Detected {len(communities)} communities")

        # Ensure all nodes are accounted for
        all_community_nodes = set()
        for comm in communities:
            all_community_nodes.update(comm)

        # Add any missing nodes as singleton communities
        missing_nodes = set(graph.nodes()) - all_community_nodes
        if missing_nodes:
            self.logger.debug(
                f"Adding {len(missing_nodes)} isolated nodes as singleton communities"
            )
            for node in missing_nodes:
                communities.append({node})

        # Merge communities to reach target partition count
        if len(communities) > num_partitions:
            # Sort by size (largest first) and merge smaller communities into larger ones
            communities = sorted(communities, key=len, reverse=True)
            merged = list(communities[:num_partitions])

            # Distribute remaining communities across the partitions
            for i, comm in enumerate(communities[num_partitions:]):
                # Add to smallest partition to balance
                smallest_idx = min(range(len(merged)), key=lambda i: len(merged[i]))
                merged[smallest_idx] = merged[smallest_idx].union(comm)
        else:
            # Split largest communities if needed
            merged = list(communities)
            while len(merged) < num_partitions:
                # Find largest community
                largest_idx = max(range(len(merged)), key=lambda i: len(merged[i]))
                largest = merged[largest_idx]

                # Split in half
                nodes = list(largest)
                mid = len(nodes) // 2
                merged[largest_idx] = set(nodes[:mid])
                merged.append(set(nodes[mid:]))

        # Create partition subgraphs
        partitions = []
        for partition_id, partition_nodes in enumerate(merged):
            partition_graph = nx.DiGraph(graph.subgraph(partition_nodes))
            partitions.append(partition_graph)

            self.logger.debug(
                f"Partition {partition_id}: {partition_graph.number_of_nodes()} nodes, "
                f"{partition_graph.number_of_edges()} edges"
            )

        return partitions

    def save_partition(
        self, partition: nx.DiGraph, partition_id: int, output_dir: str
    ) -> str:
        """
        Save partition as compressed artifact.

        Uses joblib for efficient compression and serialization.

        Args:
            partition: Graph partition to save
            partition_id: Partition identifier
            output_dir: Directory to save partition

        Returns:
            str: Path to saved partition file
        """
        import joblib

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        partition_file = output_path / f"partition-{partition_id}.pkl"

        self.logger.debug(
            f"Saving partition {partition_id} to {partition_file} "
            f"({partition.number_of_nodes()} nodes)"
        )

        joblib.dump(partition, partition_file, compress=3)

        return str(partition_file)

    def load_partition(self, partition_id: int, input_dir: str) -> nx.DiGraph:
        """
        Load partition from artifact.

        Args:
            partition_id: Partition identifier
            input_dir: Directory containing partition files

        Returns:
            nx.DiGraph: Loaded graph partition
        """
        import joblib

        input_path = Path(input_dir) / f"partition-{partition_id}.pkl"

        if not input_path.exists():
            raise FileNotFoundError(f"Partition file not found: {input_path}")

        self.logger.debug(f"Loading partition {partition_id} from {input_path}")

        partition = joblib.load(input_path)

        self.logger.debug(
            f"Loaded partition {partition_id}: {partition.number_of_nodes()} nodes, "
            f"{partition.number_of_edges()} edges"
        )

        return partition

    def get_partition_info(
        self, partition: nx.DiGraph, partition_id: int, artifact_path: str
    ) -> PartitionInfo:
        """
        Get metadata about a partition.

        Args:
            partition: Graph partition
            partition_id: Partition identifier
            artifact_path: Path to partition artifact

        Returns:
            PartitionInfo: Partition metadata
        """
        # Count boundary nodes (nodes with edges to other partitions)
        # For now, we can't determine this without the full graph
        # This will be calculated during analysis
        boundary_node_count = 0

        return PartitionInfo(
            partition_id=partition_id,
            node_count=partition.number_of_nodes(),
            edge_count=partition.number_of_edges(),
            boundary_node_count=boundary_node_count,
            artifact_path=artifact_path,
        )


__all__ = ["GraphPartitioner", "PartitionInfo"]
