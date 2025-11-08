"""
Data loaders for FollowWeb network analysis.

This module provides abstract interfaces and concrete implementations for loading
network data from various sources (Instagram, Freesound, etc.) and converting
them to NetworkX graphs.

Modules:
    base: Abstract DataLoader base class defining the loader interface
    instagram: InstagramLoader for Instagram follower/following data
"""

from .base import DataLoader
from .instagram import InstagramLoader

__all__ = [
    "DataLoader",
    "InstagramLoader",
]
