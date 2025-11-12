"""
Data layer components for FollowWeb Network Analysis.

This module handles data loading, processing, and graph operations:
- JSON and text file parsing with validation
- Graph filtering and transformation operations
- Caching strategies for expensive operations
- Abstract interfaces for extensible data loaders
- Checkpoint management for incremental processing

Modules:
    loaders: DataLoader abstract base class and loader implementations
    cache: CentralizedCache class and caching utilities
    processors: Graph filtering, reciprocal filtering, k-core operations
    checkpoint: GraphCheckpoint for incremental graph building
"""

from .cache import (
    CentralizedCache,
    calculate_graph_hash,
    clear_all_caches,
    get_cache_manager,
    get_cached_node_attributes,
    get_cached_undirected_graph,
)
from .checkpoint import GraphCheckpoint
from .loaders import (
    DataLoader,
    FreesoundLoader,
    IncrementalFreesoundLoader,
    InstagramLoader,
)
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
    "FreesoundLoader",
    "IncrementalFreesoundLoader",
    # Checkpoint management
    "GraphCheckpoint",
    # Graph processing
    "GraphProcessor",
]
