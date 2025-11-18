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

        # Check if files are non-empty
        empty_files = []
        if topology_path.stat().st_size == 0:
            empty_files.append("graph_topology.gpickle")
        if metadata_db_path.stat().st_size == 0:
            empty_files.append("metadata_cache.db")
        if checkpoint_meta_path.stat().st_size == 0:
            empty_files.append("checkpoint_metadata.json")

        if empty_files:
            message = f"Empty checkpoint files: {', '.join(empty_files)}"
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

        # Verify SQLite database is valid
        try:
            import sqlite3

            conn = sqlite3.connect(str(metadata_db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()

            if not tables:
                message = "metadata_cache.db has no tables"
                self.logger.error(f"❌ Checkpoint verification failed: {message}")
                return False, message
        except Exception as e:
            message = f"Invalid metadata_cache.db: {e}"
            self.logger.error(f"❌ Checkpoint verification failed: {message}")
            return False, message

        # All checks passed
        self.logger.debug("✅ Checkpoint verification passed")
        return True, "All checkpoint files verified"
