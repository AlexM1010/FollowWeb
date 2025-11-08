"""
Data loaders for FollowWeb network analysis.

This module provides abstract interfaces and concrete implementations for loading
network data from various sources (Instagram, Freesound, etc.) and converting
them to NetworkX graphs.

Modules:
    base: Abstract DataLoader base class defining the loader interface
    instagram: InstagramLoader for Instagram follower/following data
    freesound: FreesoundLoader for Freesound audio sample data
    incremental_freesound: IncrementalFreesoundLoader with checkpoint support
"""

from .base import DataLoader
from .freesound import FreesoundLoader
from .incremental_freesound import IncrementalFreesoundLoader
from .instagram import InstagramLoader

__all__ = [
    "DataLoader",
    "FreesoundLoader",
    "IncrementalFreesoundLoader",
    "InstagramLoader",
]
