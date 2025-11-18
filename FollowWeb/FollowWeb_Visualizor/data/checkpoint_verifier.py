"""
Checkpoint verification utilities for fail-fast architecture.

This module provides verification functionality to ensure checkpoint saves
are successful and complete before continuing execution.
"""

import logging
from pathlib import Path
from typing import Optional


class CheckpointVerifier:
    """
    Verifies checkpoint save operations for fail-fast architecture.

    Ensures all three checkpoint files exist and are valid:
    1. graph_topology.gpickle - Graph structure
    2. metadata_cache.db - SQLite metadata database
    3. checkpoint_metadata.json - Checkpoint metadata
    """

    def __init__(self, checkpoint_dir: Path, logger: Optional[logging.Logger] = None):
        """
        Initialize checkpoint verifier.

        Args:
            checkpoint_dir: Directory containing checkpoint files
            logger: Optional logger instance
        """
        self.checkpoint_dir = checkpoint_dir
        self.logger = logger or logging.getLogger(__name__)

    def verify_checkpoint_files(self) -> tuple[bool, str]:
        """
        Verify all three checkpoint files exist and are valid.

        Returns:
            Tuple of (success: bool, message: str)
        """
        topology_path = self.checkpoint_dir / "graph_topology.gpickle"
        metadata_db_path = self.checkpoint_dir / "metadata_cache.db"
        checkpoint_meta_path = self.checkpoint_dir / "checkpoint_metadata.json"

        # Check if all files exist
        missing_files = []
        if not topology_path.exists():
            missing_files.append("graph_topology.gpickle")
        if not metadata_db_path.exists():
            missing_files.append("metadata_cache.db")
        if not checkpoint_meta_path.exists():
            missing_files.append("checkpoint_metadata.json")

        if missing_files:
            message = f"Missing checkpoint files: {', '.join(missing_files)}"
            self.logger.error(f"❌ Checkpoint verification failed: {message}")
            return False, message

        # Check if files are non-empty (no minimum size, just validate content)
        empty_files = []
        if topology_path.stat().st_size == 0:
            empty_files.append("graph_topology.gpickle (0 bytes)")

        if metadata_db_path.stat().st_size == 0:
            empty_files.append("metadata_cache.db (0 bytes)")

        if checkpoint_meta_path.stat().st_size == 0:
            empty_files.append("checkpoint_metadata.json (0 bytes)")

        if empty_files:
            message = f"Empty or too small checkpoint files: {', '.join(empty_files)}"
            self.logger.error(f"❌ Checkpoint verification failed: {message}")
            return False, message

        # Verify JSON file is valid
        try:
            import json

            with open(checkpoint_meta_path) as f:
                json.load(f)
        except Exception as e:
            message = f"Invalid checkpoint_metadata.json: {e}"
            self.logger.error(f"❌ Checkpoint verification failed: {message}")
            return False, message

        # Verify pickle file can be loaded
        try:
            import pickle

            with open(topology_path, "rb") as f:
                # Loading our own checkpoint data, not untrusted input
                graph = pickle.load(f)  # nosec B301

            # Verify it's a NetworkX graph
            import networkx as nx

            if not isinstance(
                graph, (nx.Graph, nx.DiGraph, nx.MultiGraph, nx.MultiDiGraph)
            ):
                message = f"graph_topology.gpickle contains invalid type: {type(graph)}"
                self.logger.error(f"❌ Checkpoint verification failed: {message}")
                return False, message

            # Verify graph has nodes
            if graph.number_of_nodes() == 0:
                message = "graph_topology.gpickle contains empty graph (0 nodes)"
                self.logger.error(f"❌ Checkpoint verification failed: {message}")
                return False, message

        except Exception as e:
            message = f"Invalid graph_topology.gpickle: {e}"
            self.logger.error(f"❌ Checkpoint verification failed: {message}")
            return False, message

        # Verify SQLite database is valid
        try:
            import sqlite3

            conn = sqlite3.connect(str(metadata_db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            if not tables:
                conn.close()
                message = "metadata_cache.db has no tables"
                self.logger.error(f"❌ Checkpoint verification failed: {message}")
                return False, message

            # Verify metadata table has data
            cursor.execute("SELECT COUNT(*) FROM metadata")
            count = cursor.fetchone()[0]
            conn.close()

            if count == 0:
                message = "metadata_cache.db has no data (0 rows)"
                self.logger.error(f"❌ Checkpoint verification failed: {message}")
                return False, message

        except Exception as e:
            message = f"Invalid metadata_cache.db: {e}"
            self.logger.error(f"❌ Checkpoint verification failed: {message}")
            return False, message

        # All checks passed
        self.logger.debug("✅ Checkpoint verification passed")
        return True, "All checkpoint files verified"
