"""
Centralized caching system for FollowWeb social network analysis.

This module contains the CentralizedCache class that eliminates duplicate calculations
across the entire FollowWeb package by providing a single source of truth for expensive
operations like graph hashing, community detection, centrality calculations, and layout positions.
"""

# Standard library imports
import hashlib
import json
import logging
import sys
import time
import weakref
from typing import Any, Dict, Optional, Tuple, Union

# Third-party imports
try:
    import networkx as nx
except ImportError:
    nx = None

# Third-party imports
import networkx as nx

# Conditional nx_parallel import (Python 3.11+ only)
try:
    if sys.version_info >= (3, 11):
        import nx_parallel  # noqa: F401
except ImportError:
    pass  # nx_parallel not available, use standard NetworkX

# Local imports
from ..utils.parallel import ParallelConfig


class CentralizedCache:
    """
    Centralized caching system for frequently calculated values.

    This cache eliminates duplicate calculations across the entire FollowWeb package
    by providing a single source of truth for expensive operations like graph hashing,
    community detection, centrality calculations, and layout positions.
    """

    def __init__(self, max_cache_size: int = 50, cache_timeout: float = 3600) -> None:
        """
        Initialize the centralized cache.

        Args:
            max_cache_size: Maximum number of items to cache per category
            cache_timeout: Cache timeout in seconds (default: 1 hour)
        """
        self.max_cache_size = max_cache_size
        self.cache_timeout = cache_timeout
        self.logger = logging.getLogger(__name__)

        # Separate caches for different types of data
        self._graph_hashes: Dict[str, str] = {}  # graph_id -> hash_string
        self._undirected_graphs: Dict[str, Any] = {}  # graph_hash -> undirected_graph
        self._node_attributes: Dict[
            Tuple[str, str], Dict[str, Any]
        ] = {}  # (graph_hash, attr_name) -> attributes_dict
        self._edge_attributes: Dict[
            Tuple[str, str], Dict[Tuple[str, str], Any]
        ] = {}  # (graph_hash, attr_name) -> attributes_dict
        self._community_colors: Dict[
            str, Dict[int, Union[str, Tuple[float, ...]]]
        ] = {}  # num_communities -> color_dict
        self._layout_positions: Dict[
            Tuple[str, str, str], Dict[str, Tuple[float, float]]
        ] = {}  # (graph_hash, layout_type, params_hash) -> positions
        self._centrality_results: Dict[
            Tuple[str, str, str], Dict[str, float]
        ] = {}  # (graph_hash, centrality_type, params_hash) -> results
        self._community_results: Dict[
            Tuple[str, str], Dict[str, int]
        ] = {}  # (graph_hash, params_hash) -> community_dict
        self._parallel_configs: Dict[
            Tuple[str, Optional[int]], Any
        ] = {}  # (operation_type, graph_size) -> ParallelConfig

        # Timestamps for cache expiration
        self._timestamps: Dict[str, float] = {}

        # Weak references to graphs to avoid memory leaks
        self._graph_refs: weakref.WeakValueDictionary = weakref.WeakValueDictionary()

    def calculate_graph_hash(self, graph: nx.Graph) -> str:
        """
        Calculate a standardized hash for a graph.

        This provides a consistent hashing mechanism across the entire package,
        replacing the multiple different hashing implementations.

        Args:
            graph: NetworkX graph to hash

        Returns:
            SHA-256 hash string of the graph structure
        """
        graph_id = id(graph)

        # Check if we already have the hash for this graph instance
        if graph_id in self._graph_hashes:
            return self._graph_hashes[graph_id]

        # Calculate hash based on graph structure
        try:
            graph_data = {
                "nodes": sorted(graph.nodes()),
                "edges": sorted(graph.edges()),
                "directed": graph.is_directed(),
                "node_count": graph.number_of_nodes(),
                "edge_count": graph.number_of_edges(),
            }

            # Include node attributes that affect analysis
            node_attrs = {}
            for attr in ["community", "degree", "betweenness", "eigenvector"]:
                attrs = nx.get_node_attributes(graph, attr)
                if attrs:
                    # Sort by node name for consistency
                    node_attrs[attr] = {str(k): v for k, v in sorted(attrs.items())}

            if node_attrs:
                graph_data["node_attributes"] = node_attrs

            # Convert to JSON string and hash
            graph_str = json.dumps(graph_data, sort_keys=True, default=str)
            graph_hash = hashlib.sha256(graph_str.encode()).hexdigest()

            # Cache the result
            self._graph_hashes[graph_id] = graph_hash
            self._timestamps[f"graph_hash_{graph_id}"] = time.time()

            # Store weak reference to graph
            self._graph_refs[graph_hash] = graph

            # Limit cache size
            self._limit_cache_size(self._graph_hashes, "graph_hash")

            return graph_hash

        except Exception as e:
            self.logger.warning(f"Failed to calculate graph hash: {e}")
            # Fallback to simple hash
            return hashlib.md5(
                f"{graph.number_of_nodes()}_{graph.number_of_edges()}".encode()
            ).hexdigest()

    def get_cached_undirected_graph(self, graph: nx.DiGraph) -> nx.Graph:
        """
        Get cached undirected version of a directed graph.

        This eliminates the expensive to_undirected() calls that are repeated
        throughout the codebase.

        Args:
            graph: Directed graph to convert

        Returns:
            Cached undirected version of the graph
        """
        graph_hash = self.calculate_graph_hash(graph)

        # Check cache first
        if graph_hash in self._undirected_graphs:
            if self._is_cache_valid(f"undirected_{graph_hash}"):
                return self._undirected_graphs[graph_hash]

        # Create undirected graph and cache it
        undirected_graph = graph.to_undirected()
        self._undirected_graphs[graph_hash] = undirected_graph
        self._timestamps[f"undirected_{graph_hash}"] = time.time()

        # Limit cache size
        self._limit_cache_size(self._undirected_graphs, "undirected")

        return undirected_graph

    def get_cached_node_attributes(
        self, graph: nx.Graph, attribute_name: str
    ) -> Dict[str, Any]:
        """
        Get cached node attributes to avoid repeated graph traversals.

        Args:
            graph: Graph to get attributes from
            attribute_name: Name of the attribute to retrieve

        Returns:
            Dictionary of node attributes
        """
        graph_hash = self.calculate_graph_hash(graph)
        cache_key = (graph_hash, attribute_name)

        # Check cache first
        if cache_key in self._node_attributes:
            if self._is_cache_valid(f"node_attr_{graph_hash}_{attribute_name}"):
                return self._node_attributes[cache_key]

        # Get attributes and cache them
        attributes = nx.get_node_attributes(graph, attribute_name)
        self._node_attributes[cache_key] = attributes
        self._timestamps[f"node_attr_{graph_hash}_{attribute_name}"] = time.time()

        # Limit cache size
        self._limit_cache_size(self._node_attributes, "node_attr")

        return attributes

    def get_cached_edge_attributes(
        self, graph: nx.Graph, attribute_name: str
    ) -> Dict[Tuple[str, str], Any]:
        """
        Get cached edge attributes to avoid repeated graph traversals.

        Args:
            graph: Graph to get attributes from
            attribute_name: Name of the attribute to retrieve

        Returns:
            Dictionary of edge attributes
        """
        graph_hash = self.calculate_graph_hash(graph)
        cache_key = (graph_hash, attribute_name)

        # Check cache first
        if cache_key in self._edge_attributes:
            if self._is_cache_valid(f"edge_attr_{graph_hash}_{attribute_name}"):
                return self._edge_attributes[cache_key]

        # Get attributes and cache them
        attributes = nx.get_edge_attributes(graph, attribute_name)
        self._edge_attributes[cache_key] = attributes
        self._timestamps[f"edge_attr_{graph_hash}_{attribute_name}"] = time.time()

        # Limit cache size
        self._limit_cache_size(self._edge_attributes, "edge_attr")

        return attributes

    def get_cached_community_colors(
        self, num_communities: int
    ) -> Optional[Dict[str, Dict[int, Union[str, Tuple[float, ...]]]]]:
        """
        Get cached community colors if available.

        Args:
            num_communities: Number of communities to generate colors for

        Returns:
            Dictionary with 'hex' and 'rgba' color mappings, or None if not cached
        """
        if num_communities in self._community_colors:
            if self._is_cache_valid(f"colors_{num_communities}"):
                return self._community_colors[num_communities]

        return None

    def cache_community_colors(
        self,
        num_communities: int,
        colors: Dict[str, Dict[int, Union[str, Tuple[float, ...]]]],
    ) -> None:
        """
        Cache community colors.

        Args:
            num_communities: Number of communities
            colors: Color dictionary to cache
        """
        self._community_colors[num_communities] = colors
        self._timestamps[f"colors_{num_communities}"] = time.time()

        # Limit cache size
        self._limit_cache_size(self._community_colors, "colors")

    def cache_layout_positions(
        self,
        graph: nx.Graph,
        layout_type: str,
        positions: Dict[str, Tuple[float, float]],
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Cache layout positions for reuse across different output formats.

        Args:
            graph: Graph the layout was calculated for
            layout_type: Type of layout (spring, circular, etc.)
            positions: Calculated positions
            params: Layout parameters used
        """
        graph_hash = self.calculate_graph_hash(graph)
        params_hash = self._hash_params(params or {})
        cache_key = (graph_hash, layout_type, params_hash)

        self._layout_positions[cache_key] = positions
        self._timestamps[f"layout_{graph_hash}_{layout_type}_{params_hash}"] = (
            time.time()
        )

        # Limit cache size
        self._limit_cache_size(self._layout_positions, "layout")

    def get_cached_layout_positions(
        self, graph: nx.Graph, layout_type: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Tuple[float, float]]]:
        """
        Get cached layout positions if available.

        Args:
            graph: Graph to get layout for
            layout_type: Type of layout
            params: Layout parameters

        Returns:
            Cached positions or None if not available
        """
        graph_hash = self.calculate_graph_hash(graph)
        params_hash = self._hash_params(params or {})
        cache_key = (graph_hash, layout_type, params_hash)

        if cache_key in self._layout_positions:
            if self._is_cache_valid(f"layout_{graph_hash}_{layout_type}_{params_hash}"):
                return self._layout_positions[cache_key]

        return None

    def cache_centrality_results(
        self,
        graph: nx.Graph,
        centrality_type: str,
        results: Dict[str, float],
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Cache centrality calculation results.

        Args:
            graph: Graph the centrality was calculated for
            centrality_type: Type of centrality (degree, betweenness, etc.)
            results: Calculated centrality values
            params: Calculation parameters used
        """
        graph_hash = self.calculate_graph_hash(graph)
        params_hash = self._hash_params(params or {})
        cache_key = (graph_hash, centrality_type, params_hash)

        self._centrality_results[cache_key] = results
        self._timestamps[f"centrality_{graph_hash}_{centrality_type}_{params_hash}"] = (
            time.time()
        )

        # Limit cache size
        self._limit_cache_size(self._centrality_results, "centrality")

    def get_cached_centrality_results(
        self,
        graph: nx.Graph,
        centrality_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, float]]:
        """
        Get cached centrality results if available.

        Args:
            graph: Graph to get centrality for
            centrality_type: Type of centrality
            params: Calculation parameters

        Returns:
            Cached centrality values or None if not available
        """
        graph_hash = self.calculate_graph_hash(graph)
        params_hash = self._hash_params(params or {})
        cache_key = (graph_hash, centrality_type, params_hash)

        if cache_key in self._centrality_results:
            if self._is_cache_valid(
                f"centrality_{graph_hash}_{centrality_type}_{params_hash}"
            ):
                return self._centrality_results[cache_key]

        return None

    def cache_community_results(
        self,
        graph: nx.Graph,
        communities: Dict[str, int],
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Cache community detection results.

        Args:
            graph: Graph the communities were detected for
            communities: Community assignments
            params: Detection parameters used
        """
        graph_hash = self.calculate_graph_hash(graph)
        params_hash = self._hash_params(params or {})
        cache_key = (graph_hash, params_hash)

        self._community_results[cache_key] = communities
        self._timestamps[f"community_{graph_hash}_{params_hash}"] = time.time()

        # Limit cache size
        self._limit_cache_size(self._community_results, "community")

    def get_cached_community_results(
        self, graph: nx.Graph, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, int]]:
        """
        Get cached community detection results if available.

        Args:
            graph: Graph to get communities for
            params: Detection parameters

        Returns:
            Cached community assignments or None if not available
        """
        graph_hash = self.calculate_graph_hash(graph)
        params_hash = self._hash_params(params or {})
        cache_key = (graph_hash, params_hash)

        if cache_key in self._community_results:
            if self._is_cache_valid(f"community_{graph_hash}_{params_hash}"):
                return self._community_results[cache_key]

        return None

    def cache_parallel_config(
        self, operation_type: str, graph_size: Optional[int], config: "ParallelConfig"
    ) -> None:
        """
        Cache parallel processing configurations.

        Args:
            operation_type: Type of operation
            graph_size: Size of graph being processed
            config: Parallel configuration to cache
        """
        cache_key = (operation_type, graph_size or 0)
        self._parallel_configs[cache_key] = config
        self._timestamps[f"parallel_{operation_type}_{graph_size or 0}"] = time.time()

        # Limit cache size
        self._limit_cache_size(self._parallel_configs, "parallel")

    def get_cached_parallel_config(
        self, operation_type: str, graph_size: Optional[int]
    ) -> Optional["ParallelConfig"]:
        """
        Get cached parallel configuration if available.

        Args:
            operation_type: Type of operation
            graph_size: Size of graph being processed

        Returns:
            Cached parallel configuration or None if not available
        """
        cache_key = (operation_type, graph_size or 0)

        if cache_key in self._parallel_configs:
            if self._is_cache_valid(f"parallel_{operation_type}_{graph_size or 0}"):
                return self._parallel_configs[cache_key]

        return None

    def clear_all_caches(self) -> None:
        """Clear all caches and reset the cache manager."""
        self._graph_hashes.clear()
        self._undirected_graphs.clear()
        self._node_attributes.clear()
        self._edge_attributes.clear()
        self._community_colors.clear()
        self._layout_positions.clear()
        self._centrality_results.clear()
        self._community_results.clear()
        self._parallel_configs.clear()
        self._timestamps.clear()
        self._graph_refs.clear()

        self.logger.debug("All caches cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics for monitoring and debugging.

        Returns:
            Dictionary with cache sizes for each category
        """
        return {
            "graph_hashes": len(self._graph_hashes),
            "undirected_graphs": len(self._undirected_graphs),
            "node_attributes": len(self._node_attributes),
            "edge_attributes": len(self._edge_attributes),
            "community_colors": len(self._community_colors),
            "layout_positions": len(self._layout_positions),
            "centrality_results": len(self._centrality_results),
            "community_results": len(self._community_results),
            "parallel_configs": len(self._parallel_configs),
        }

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if a cache entry is still valid based on timeout."""
        if cache_key not in self._timestamps:
            return False

        age = time.time() - self._timestamps[cache_key]
        return age < self.cache_timeout

    def _hash_params(self, params: Dict[str, Any]) -> str:
        """Create a hash of parameters for cache keys."""
        try:
            params_str = json.dumps(params, sort_keys=True, default=str)
            return hashlib.md5(params_str.encode()).hexdigest()[:8]
        except Exception:
            return "default"

    def _limit_cache_size(self, cache_dict: Dict, cache_type: str) -> None:
        """Limit cache size by removing oldest entries."""
        if len(cache_dict) > self.max_cache_size:
            # Find oldest entries to remove
            relevant_timestamps = {
                k: v for k, v in self._timestamps.items() if k.startswith(cache_type)
            }

            if relevant_timestamps:
                # Sort by timestamp and remove oldest
                sorted_items = sorted(relevant_timestamps.items(), key=lambda x: x[1])
                items_to_remove = len(cache_dict) - self.max_cache_size + 1

                for i in range(min(items_to_remove, len(sorted_items))):
                    timestamp_key = sorted_items[i][0]
                    # Extract cache key from timestamp key
                    cache_key = self._extract_cache_key_from_timestamp(
                        timestamp_key, cache_dict
                    )
                    if cache_key and cache_key in cache_dict:
                        del cache_dict[cache_key]
                        del self._timestamps[timestamp_key]

    def _extract_cache_key_from_timestamp(
        self, timestamp_key: str, cache_dict: Dict
    ) -> Any:
        """Extract the actual cache key from a timestamp key."""
        # This is a simplified approach - in practice, you might need more sophisticated mapping
        for cache_key in cache_dict.keys():
            if str(cache_key) in timestamp_key or (
                isinstance(cache_key, tuple)
                and any(str(part) in timestamp_key for part in cache_key)
            ):
                return cache_key
        return None


# Global cache manager instance
_cache_manager = None


def get_cache_manager() -> CentralizedCache:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CentralizedCache()
    return _cache_manager


def calculate_graph_hash(graph: nx.Graph) -> str:
    """
    Centralized graph hashing function.

    This replaces all the different graph hashing implementations throughout
    the codebase with a single, consistent approach.

    Args:
        graph: NetworkX graph to hash

    Returns:
        Standardized hash string for the graph
    """
    return get_cache_manager().calculate_graph_hash(graph)


def get_cached_undirected_graph(graph: nx.DiGraph) -> nx.Graph:
    """
    Get cached undirected version of a directed graph.

    This eliminates duplicate to_undirected() calls throughout the codebase.

    Args:
        graph: Directed graph to convert

    Returns:
        Cached undirected version
    """
    return get_cache_manager().get_cached_undirected_graph(graph)


def get_cached_node_attributes(graph: nx.Graph, attribute_name: str) -> Dict[str, Any]:
    """
    Get cached node attributes to avoid repeated graph traversals.

    Args:
        graph: Graph to get attributes from
        attribute_name: Name of the attribute

    Returns:
        Cached node attributes
    """
    return get_cache_manager().get_cached_node_attributes(graph, attribute_name)


def clear_all_caches() -> None:
    """Clear all caches - useful for testing and memory management."""
    get_cache_manager().clear_all_caches()


def get_cached_community_colors(
    num_communities: int,
) -> Dict[str, Dict[int, Union[str, Tuple[float, ...]]]]:
    """
    Get cached community colors, generating them if not cached.

    Args:
        num_communities: Number of communities to generate colors for

    Returns:
        Dictionary with color schemes for communities
    """
    cache_manager = get_cache_manager()
    cached_colors = cache_manager.get_cached_community_colors(num_communities)

    if cached_colors is not None:
        return cached_colors

    # Generate new colors if not cached
    from ..visualization.colors import get_community_colors

    colors = get_community_colors(num_communities)

    # Cache the generated colors
    cache_manager.cache_community_colors(num_communities, colors)

    return colors
