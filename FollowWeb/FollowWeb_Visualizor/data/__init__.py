"""
Data layer components for FollowWeb Network Analysis.

This module handles data loading, processing, and graph operations:
- JSON and text file parsing with validation
- Graph filtering and transformation operations
- Caching strategies for expensive operations
- Abstract interfaces for extensible data loaders

Modules:
    loaders: DataLoader abstract base class and loader implementations
    cache: CentralizedCache class and caching utilities
    processors: Graph filtering, reciprocal filtering, k-core operations
"""

from .cache import (
    CentralizedCache,
    calculate_graph_hash,
    clear_all_caches,
    get_cache_manager,
    get_cached_node_attributes,
    get_cached_undirected_graph,
)
from .loaders import DataLoader, InstagramLoader
from .processors import GraphProcessor

__all__ = [
    # Cache functionality
    "CentralizedCache",
    "get_cache_manager",
    "calculate_graph_hash",
    "get_cached_undirected_graph",
    "get_cached_node_attributes",
    "clear_all_caches",
    # Data loading
    "DataLoader",
    "InstagramLoader",
    # Graph processing
    "GraphProcessor",
]
