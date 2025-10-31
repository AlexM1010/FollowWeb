"""
Data loading module for FollowWeb social network analysis.

This module contains the GraphLoader class for loading and parsing JSON network data
with error handling and batch processing optimization.
"""

# Standard library imports
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

# Third-party imports
import networkx as nx

# Local imports
from ..core.exceptions import DataProcessingError
from ..output.formatters import EmojiFormatter
from ..utils.validation import ProgressTracker
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