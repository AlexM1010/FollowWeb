"""
Instagram data loader for FollowWeb social network analysis.

This module provides the InstagramLoader class for loading and parsing Instagram
follower/following JSON data with error handling and batch processing optimization.
"""

# Standard library imports
import json
import os
from typing import Any

# Third-party imports
import networkx as nx

# Local imports
from ...core.exceptions import DataProcessingError
from ...output.formatters import EmojiFormatter
from ...utils import ProgressTracker
from .base import DataLoader


class InstagramLoader(DataLoader):
    """
    Loader for Instagram follower/following JSON data.

    This loader handles Instagram network data in JSON format where each user entry
    contains their username, list of followers, and list of accounts they follow.
    It creates directed edges representing follower relationships.

    Expected JSON format:
    [
     {
       "user": "username1",
       "followers": ["user2", "user3"],
       "following": ["user4", "user5"]
     },
     ...
    ]

    Attributes:
        config: Configuration dictionary (optional)
        logger: Logger instance for this loader
        cache_manager: Centralized cache manager

    Example:
        loader = InstagramLoader()
        graph = loader.load(filepath='instagram_data.json')
    """

    def __init__(self, config: dict[str, Any] = None):
        """
        Initialize the Instagram loader.

        Args:
            config: Optional configuration dictionary. Currently unused but
                   available for future extensions.
        """
        super().__init__(config)

    def fetch_data(self, filepath: str) -> dict[str, Any]:  # type: ignore[override]
        """
        Load Instagram network data from a JSON file.

        Reads and parses a JSON file containing Instagram follower/following data.
        Validates file existence and JSON format.

        Args:
            filepath: Absolute or relative path to the JSON file containing
                     Instagram network data

        Returns:
            Dictionary with 'users' key containing the parsed JSON data list

        Raises:
            FileNotFoundError: If the specified input file does not exist
            ValueError: If JSON format is invalid or root is not a list
            PermissionError: If file cannot be read due to insufficient permissions
            DataProcessingError: If any other error occurs during file reading
        """
        # Validate file exists
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Input file not found: {filepath}")

        # Read and parse JSON file
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {filepath}: {e}") from e
        except PermissionError as e:
            raise PermissionError(f"Permission denied reading file: {filepath}") from e
        except Exception as e:
            raise DataProcessingError(f"Could not read file {filepath}: {e}") from e

        # Validate JSON structure
        if not isinstance(data, list):
            raise ValueError("JSON root must be a list")

        progress_msg = EmojiFormatter.format(
            "progress", f"Processing {len(data)} user entries..."
        )
        self.logger.info(progress_msg)

        # Handle empty data case
        if len(data) == 0:
            self.logger.info("No user entries to process")

        return {"users": data}

    def build_graph(self, data: dict[str, Any]) -> nx.DiGraph:
        """
        Build a directed graph from Instagram follower/following data.

        Creates nodes for users and directed edges representing follower relationships.
        Uses batch processing for memory efficiency with large datasets.

        Args:
            data: Dictionary with 'users' key containing list of user entries.
                 Each entry should have 'user', 'followers', and 'following' keys.

        Returns:
            NetworkX DiGraph with nodes representing users and edges representing
            follower relationships. Returns empty graph if no valid data is found.

        Raises:
            DataProcessingError: If graph construction fails
        """
        users_data = data.get("users", [])

        # Initialize graph
        graph: nx.DiGraph = nx.DiGraph()

        # Handle empty data
        if len(users_data) == 0:
            self.logger.info("No user entries to process, returning empty graph")
            return graph

        # OPTIMIZATION: Process data in batches to reduce memory pressure
        batch_size = min(1000, max(100, len(users_data) // 10))

        # OPTIMIZATION: Pre-allocate edge list to reduce memory reallocations
        edges_to_add: list[tuple] = []

        # Use progress tracking for processing user entries on large datasets
        with ProgressTracker(
            total=len(users_data),
            title="Loading network data from JSON",
            logger=self.logger,
        ) as tracker:
            # Process data in batches
            for batch_start in range(0, len(users_data), batch_size):
                batch_end = min(batch_start + batch_size, len(users_data))
                batch_data = users_data[batch_start:batch_end]

                # Process each user's data in the batch
                for i, user_entry in enumerate(batch_data):
                    global_i = batch_start + i

                    # Validate user entry is a dictionary
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

                    # Get followers and following lists
                    followers = user_entry.get("followers", [])
                    following = user_entry.get("following", [])

                    # Validate lists
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
            f"Initial graph loaded: {graph.number_of_nodes():,} nodes, "
            f"{graph.number_of_edges():,} edges",
        )
        self.logger.info(success_msg)

        return graph

    def load_from_json(self, filepath: str) -> nx.DiGraph:
        """
        Load a directed graph from a JSON file with error handling.

        This method maintains the original GraphLoader API behavior where
        exceptions are raised directly without wrapping in DataProcessingError.

        Args:
            filepath: Absolute or relative path to the JSON file containing network data

        Returns:
            NetworkX DiGraph with nodes representing users and edges representing
            follower relationships.

        Raises:
            FileNotFoundError: If the specified input file does not exist
            ValueError: If JSON format is invalid or root is not a list
            PermissionError: If file cannot be read due to insufficient permissions
        """
        # Call fetch_data and build_graph directly to preserve original exception behavior
        # (not using load() which wraps exceptions in DataProcessingError)
        data = self.fetch_data(filepath=filepath)
        graph = self.build_graph(data)
        return graph
