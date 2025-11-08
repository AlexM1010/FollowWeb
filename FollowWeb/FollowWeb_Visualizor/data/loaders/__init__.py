"""
Data loaders for FollowWeb network analysis.

This module provides abstract interfaces and concrete implementations for loading
network data from various sources (Instagram, Freesound, etc.) and converting
them to NetworkX graphs.

Modules:
    base: Abstract DataLoader base class defining the loader interface
    instagram: InstagramLoader for Instagram follower/following data
    freesound: FreesoundLoader for Freesound audio sample data
"""

from .base import DataLoader
from .freesound import FreesoundLoader
from .instagram import InstagramLoader

__all__ = [
    "DataLoader",
    "FreesoundLoader",
    "InstagramLoader",
]
