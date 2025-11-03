"""
Fame analysis module for identifying influential accounts.

This module provides the FameAnalyzer class for detecting influential accounts
based on follower-to-following ratios and connectivity patterns.
"""

# Standard library imports
import logging
import sys
from typing import Dict, List, Tuple, Union

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


class FameAnalyzer:
    """
    Class for identifying influential accounts with filtering and ranking algorithms.
    """

    def __init__(self) -> None:
        """
        Initialize the FameAnalyzer.

        The FameAnalyzer identifies influential accounts based on follower-to-following
        ratios and provides analysis of account reach and connectivity patterns.
        """
        self.logger = logging.getLogger(__name__)

    def find_famous_accounts(
        self, graph: nx.DiGraph, min_followers: int, min_ratio: float
    ) -> Tuple[
        List[Dict[str, Union[str, int, float]]], List[Dict[str, Union[str, int, float]]]
    ]:
        """
        Identify influential accounts based on follower-to-following ratio analysis.

        Analyzes the network to find accounts that meet "celebrity" criteria by having
        high follower counts and favorable follower-to-following ratios. Separates
        results into reachable (follow others) and unreachable (follow nobody) categories.

        Args:
            graph: Input directed graph representing social network connections
            min_followers: Minimum number of followers (in-degree) required for consideration
            min_ratio: Minimum follower-to-following ratio threshold for fame classification

        Returns:
            Tuple containing two lists of account dictionaries:
            - unreachable_famous: Accounts with following_in_network=0 (celebrities who follow nobody)
            - reachable_famous: Accounts with following_in_network>=1 (influential but reachable)

            Each account dictionary contains:
            - 'username': Account username (str)
            - 'followers_in_network': Number of followers in this network (int)
            - 'following_in_network': Number of accounts they follow in this network (int)
            - 'ratio': Follower-to-following ratio (float, may be inf for accounts following nobody)

        Note:
            Results are sorted by ratio (descending), then by follower count (descending).
            Accounts with zero following have infinite ratio and appear first in unreachable list.
        """
        unreachable_famous = []
        reachable_famous = []

        if graph.number_of_nodes() == 0:
            return unreachable_famous, reachable_famous

        # Get all degrees at once in bulk operations
        self.logger.info("Caching all in-degrees and out-degrees...")
        in_degree_dict = dict(graph.in_degree())
        out_degree_dict = dict(graph.out_degree())

        # Use progress tracking for fame analysis on large networks
        nodes_list = list(in_degree_dict.items())
        total_nodes = len(nodes_list)

        with ProgressTracker(
            total=total_nodes,
            title="Analyzing famous accounts",
            logger=self.logger,
        ) as tracker:
            # Use .items() to iterate over nodes and their pre-calculated in-degree
            for i, (node, in_deg) in enumerate(nodes_list):
                # 1. Filter out nodes that aren't popular enough in your network
                if in_deg < min_followers:
                    continue

                # Get the pre-calculated out-degree
                out_deg = out_degree_dict.get(node, 0)

                # 2. Calculate fame ratio (handle division by zero)
                if out_deg > 0:
                    ratio = in_deg / out_deg
                else:
                    ratio = float(
                        "inf"
                    )  # Infinite ratio for accounts that follow nobody

                # 3. Filter by ratio
                if ratio >= min_ratio:
                    account_info = {
                        "username": node,
                        "followers_in_network": in_deg,
                        "following_in_network": out_deg,
                        "ratio": ratio,
                    }

                    # Separate into unreachable (follows nobody) and reachable
                    if out_deg == 0:
                        unreachable_famous.append(account_info)
                    else:
                        reachable_famous.append(account_info)

                tracker.update(i + 1)

        # Sort by ratio (descending), then by followers (descending)
        unreachable_famous.sort(
            key=lambda x: (x["ratio"], x["followers_in_network"]), reverse=True
        )
        reachable_famous.sort(
            key=lambda x: (x["ratio"], x["followers_in_network"]), reverse=True
        )

        return unreachable_famous, reachable_famous
