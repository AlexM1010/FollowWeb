"""
Graph processing module for FollowWeb social network analysis.

This module contains graph filtering and transformation operations including
reciprocal filtering, ego-alter graph creation, and k-core pruning operations.
"""

# Standard library imports
import logging
import sys

# Third-party imports
import networkx as nx

# Conditional nx_parallel import (Python 3.11+ only)
try:
    if sys.version_info >= (3, 11):
        import nx_parallel  # noqa: F401
except ImportError:
    pass  # nx_parallel not available, use standard NetworkX

# Local imports
from ..utils.parallel import get_analysis_parallel_config, log_parallel_usage


class GraphProcessor:
    """
    Class containing graph filtering and transformation methods.
    """

    def __init__(self) -> None:
        """
        Initialize the GraphProcessor.

        The GraphProcessor handles graph filtering operations including reciprocal
        filtering, ego-alter graph creation, and k-core pruning.
        """
        self.logger = logging.getLogger(__name__)

    def filter_by_reciprocity(self, graph: nx.DiGraph) -> nx.DiGraph:
        """
        Creates a new graph containing only reciprocal edges (mutual followers).

        Args:
            graph: Input directed graph

        Returns:
            nx.DiGraph: New graph with only mutual connections, or empty graph if none exist
        """
        reciprocal_graph = nx.DiGraph()

        # Keep only edges where the reverse edge also exists
        reciprocal_edges = [
            edge for edge in graph.edges() if graph.has_edge(edge[1], edge[0])
        ]
        reciprocal_graph.add_edges_from(reciprocal_edges)

        # Remove nodes that now have 0 degree
        reciprocal_graph.remove_nodes_from(list(nx.isolates(reciprocal_graph)))

        self.logger.info(
            f"✅ Filtered for mutuals: {reciprocal_graph.number_of_nodes():,} nodes, {reciprocal_graph.number_of_edges():,} edges"
        )
        return reciprocal_graph

    def create_ego_alter_graph(
        self, graph: nx.DiGraph, ego_username: str
    ) -> nx.DiGraph:
        """
        Creates an alter graph showing connections between the ego L1 contacts.

        Args:
            graph: Input directed graph
            ego_username: Username of the central ego node

        Returns:
            nx.DiGraph: Graph of L1 contacts and their connections, or empty graph on error

        Raises:
            ValueError: If ego_username is not in the graph
        """
        if not isinstance(ego_username, str) or not ego_username.strip():
            raise ValueError("Ego username must be a non-empty string")

        if ego_username not in graph:
            raise ValueError(f"ego node '{ego_username}' not found in graph")

        # 1. Identify Alters (L1 nodes)
        try:
            followers = set(graph.predecessors(ego_username))
        except nx.NetworkXError:
            followers = set()

        try:
            following = set(graph.successors(ego_username))
        except nx.NetworkXError:
            following = set()

        alters = followers.union(following)

        if not alters:
            self.logger.warning("No alters (L1 connections) found for this ego.")
            return nx.DiGraph()

        # 2. Create a new graph containing only connections between alters
        alter_graph = graph.subgraph(alters).copy()

        # Remove isolates (alters who don't connect to any other alters)
        alter_graph.remove_nodes_from(list(nx.isolates(alter_graph)))

        self.logger.info(
            f"✅ Alter graph created: {alter_graph.number_of_nodes():,} alters, {alter_graph.number_of_edges():,} connections between them"
        )
        return alter_graph

    def prune_graph(self, graph: nx.DiGraph, min_degree: int) -> nx.DiGraph:
        """
        Uses nx.k_core function to find the maximal subgraph
        where all nodes have degree >= min_degree.

        Args:
            graph: Input directed graph
            min_degree: Minimum degree threshold for k-core pruning

        Returns:
            nx.DiGraph: Pruned graph (k-core subgraph)
        """
        if min_degree <= 0:
            self.logger.info("Pruning skipped (min_degree <= 0).")
            return graph

        # nx.k_core finds the subgraph where all nodes have at least k-degree
        # For DiGraphs, .degree() is in+out, which matches the original logic.
        # Get parallel configuration for this operation
        graph_size = graph.number_of_nodes()
        parallel_config = get_analysis_parallel_config(graph_size)

        # Log parallel usage for user awareness
        self.logger.info("")  # Add spacing before parallel notification
        log_parallel_usage(parallel_config, self.logger)

        self.logger.debug(
            f"Computing k-core decomposition for k={min_degree} on {graph_size} nodes"
        )
        pruned_graph = nx.k_core(graph, k=min_degree)

        nodes_removed = graph.number_of_nodes() - pruned_graph.number_of_nodes()

        self.logger.info(f"✅ Pruning complete. Removed {nodes_removed:,} nodes")
        self.logger.info(
            f"✅ Final pruned graph: {pruned_graph.number_of_nodes():,} nodes, {pruned_graph.number_of_edges():,} edges"
        )
        self.logger.info("")  # Add spacing after pruning completion
        return pruned_graph
