"""
Data loading module for FollowWeb social network analysis.

This module contains the GraphLoader class for loading and parsing JSON network data
with error handling and batch processing optimization.
"""

# Standard library imports
import json
import logging
import os
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
from ..core.exceptions import DataProcessingError
from ..output.formatters import EmojiFormatter
from ..utils import ProgressTracker
from ..utils.parallel import get_analysis_parallel_config, log_parallel_usage


class GraphLoader:
    """
    Class for loading and parsing JSON network data with error handling.
    """

    def __init__(self) -> None:
        """
        Initialize the GraphLoader.

        The GraphLoader handles loading network data from JSON files and provides
        methods for filtering and preprocessing graphs based on different strategies.
        """
        self.logger = logging.getLogger(__name__)

    def load_from_json(self, filepath: str) -> nx.DiGraph:
        """
        Load a directed graph from a JSON file with error handling.

        Parses social network data from JSON format where each user entry contains
        their username, list of followers, and list of accounts they follow. Creates
        directed edges representing follower relationships.

        Expected JSON format:
        [
         {
           "user": "username1",
           "followers": ["user2", "user3"],
           "following": ["user4", "user5"]
         },
         ...
        ]

        Args:
            filepath: Absolute or relative path to the JSON file containing network data

        Returns:
            nx.DiGraph: Loaded directed graph with nodes representing users and edges
                       representing follower relationships. Returns empty graph if no
                       valid data is found.

        Raises:
            FileNotFoundError: If the specified input file does not exist
            ValueError: If JSON format is invalid, root is not a list, or file is corrupted
            PermissionError: If file cannot be read due to insufficient permissions
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Input file not found: {filepath}")

        # OPTIMIZATION: Initialize graph with estimated capacity for better memory allocation
        graph = nx.DiGraph()

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {filepath}: {e}") from e
        except PermissionError as e:
            raise PermissionError(f"Permission denied reading file: {filepath}") from e
        except Exception as e:
            raise DataProcessingError(f"Could not read file {filepath}: {e}") from e

        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")

        progress_msg = EmojiFormatter.format(
            "progress", f"Processing {len(data)} user entries..."
        )
        self.logger.info(progress_msg)

        # Handle empty data case
        if len(data) == 0:
            self.logger.info("No user entries to process, returning empty graph")
            return nx.DiGraph()

        # OPTIMIZATION: Process data in batches to reduce memory pressure for large datasets
        batch_size = min(1000, max(100, len(data) // 10))

        # OPTIMIZATION: Pre-allocate edge list to reduce memory reallocations
        edges_to_add = []

        # Use progress tracking for processing user entries on large datasets
        with ProgressTracker(
            total=len(data),
            title="Loading network data from JSON",
            logger=self.logger,
        ) as tracker:
            # Process data in batches
            for batch_start in range(0, len(data), batch_size):
                batch_end = min(batch_start + batch_size, len(data))
                batch_data = data[batch_start:batch_end]

                # Process each user's data in the batch
                for i, user_entry in enumerate(batch_data):
                    global_i = batch_start + i

                    if not isinstance(user_entry, dict):
                        self.logger.warning(
                            "Skipping item in list - data is not a dict"
                        )
                        continue

                    # Get username from the 'user' key
                    username = user_entry.get("user")
                    if not username:
                        self.logger.warning(
                            "Skipping item in list - 'user' key is missing or empty."
                        )
                        continue

                    # Validate required keys
                    if "followers" not in user_entry or "following" not in user_entry:
                        self.logger.warning(
                            f"User '{username}' missing 'followers' or 'following' key"
                        )
                        continue

                    followers = user_entry.get("followers", [])
                    following = user_entry.get("following", [])

                    if not isinstance(followers, list):
                        self.logger.warning(
                            f"User '{username}' - 'followers' is not a list"
                        )
                        followers = []
                    if not isinstance(following, list):
                        self.logger.warning(
                            f"User '{username}' - 'following' is not a list"
                        )
                        following = []

                    # OPTIMIZATION: Collect edges in batch instead of adding one by one
                    for follower in followers:
                        if follower:  # Skip empty strings
                            edges_to_add.append(
                                (follower, username)
                            )  # Follower -> User

                    for followee in following:
                        if followee:  # Skip empty strings
                            edges_to_add.append(
                                (username, followee)
                            )  # User -> Followee

                    tracker.update(global_i + 1)

                # OPTIMIZATION: Add edges in batch for better performance
                if edges_to_add:
                    graph.add_edges_from(edges_to_add)
                    edges_to_add.clear()  # Clear for next batch

        # OPTIMIZATION: Add any remaining edges
        if edges_to_add:
            graph.add_edges_from(edges_to_add)

        success_msg = EmojiFormatter.format(
            "success",
            f"Initial graph loaded: {graph.number_of_nodes():,} nodes, {graph.number_of_edges():,} edges",
        )
        self.logger.info(success_msg)
        return graph

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
