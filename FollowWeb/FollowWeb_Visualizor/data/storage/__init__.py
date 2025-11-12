"""
Storage modules for persistent data management.

This package provides storage backends for checkpoint data, including
SQLite-based metadata caching for scalable checkpoint architecture.
"""

from .metadata_cache import MetadataCache

__all__ = ["MetadataCache"]
