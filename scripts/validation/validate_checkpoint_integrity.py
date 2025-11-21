#!/usr/bin/env python3
"""
Comprehensive Checkpoint Integrity Validator.

Validates checkpoint files for:
- Empty or corrupted files
- Invalid file sizes
- Corrupted pickle/SQLite/JSON data
- Empty graphs or databases
- Samples with zero filesize
- Missing required fields

Usage:
    python validate_checkpoint_integrity.py --checkpoint-dir data/freesound_library
    python validate_checkpoint_integrity.py --checkpoint-dir data/freesound_library --fix
"""

import argparse
import logging
import pickle
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional

import networkx as nx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from FollowWeb.FollowWeb_Visualizor.data.checkpoint_verifier import CheckpointVerifier


def setup_logging() -> logging.Logger:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


class IntegrityValidator:
    """Comprehensive checkpoint integrity validator."""

    def __init__(
        self,
        checkpoint_dir: str,
        fix: bool = False,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize validator.

        Args:
            checkpoint_dir: Path to checkpoint directory
            fix: Whether to fix issues (remove invalid samples)
            logger: Logger instance
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.fix = fix
        self.logger = logger or logging.getLogger(__name__)

        # Checkpoint file paths
        self.graph_path = self.checkpoint_dir / "graph_topology.gpickle"
        self.metadata_db_path = self.checkpoint_dir / "metadata_cache.db"
        self.checkpoint_meta_path = self.checkpoint_dir / "checkpoint_metadata.json"

        # Statistics
        self.stats = {
            "total_samples": 0,
            "invalid_filesize": 0,
            "missing_fields": 0,
            "corrupted_data": 0,
            "samples_removed": 0,
            "errors": [],
        }

    def validate_all(self) -> dict[str, Any]:
        """
        Run comprehensive validation on checkpoint.

        Returns:
            Dictionary with validation statistics and results
        """
        self.logger.info("=" * 70)
        self.logger.info("COMPREHENSIVE CHECKPOINT INTEGRITY VALIDATION")
        self.logger.info("=" * 70)

        # Step 1: Use CheckpointVerifier for basic file validation
        self.logger.info("\n[1/5] Validating checkpoint files...")
        verifier = CheckpointVerifier(self.checkpoint_dir, self.logger)
        success, message = verifier.verify_checkpoint_files()

        if not success:
            self.logger.error(f"❌ Basic validation failed: {message}")
            self.stats["errors"].append(f"Basic validation: {message}")
            return self.stats

        self.logger.info("✅ Basic file validation passed")

        # Step 2: Load and validate graph
        self.logger.info("\n[2/5] Loading and validating graph...")
        try:
            graph = self._load_and_validate_graph()
            self.stats["total_samples"] = graph.number_of_nodes()
            self.logger.info(
                f"✅ Graph loaded: {graph.number_of_nodes()} nodes, "
                f"{graph.number_of_edges()} edges"
            )
        except Exception as e:
            self.logger.error(f"❌ Graph validation failed: {e}")
            self.stats["errors"].append(f"Graph validation: {e}")
            return self.stats

        # Step 3: Validate metadata database
        self.logger.info("\n[3/5] Validating metadata database...")
        try:
            self._validate_metadata_db()
            self.logger.info("✅ Metadata database validated")
        except Exception as e:
            self.logger.error(f"❌ Metadata database validation failed: {e}")
            self.stats["errors"].append(f"Metadata database: {e}")
            return self.stats

        # Step 4: Validate sample data
        self.logger.info("\n[4/5] Validating sample data...")
        invalid_samples = self._validate_samples(graph)

        if invalid_samples:
            self.logger.warning(f"⚠️  Found {len(invalid_samples)} samples with issues")

            if self.fix:
                self.logger.info("Removing invalid samples...")
                self._remove_invalid_samples(graph, invalid_samples)
                self.logger.info(
                    f"✅ Removed {self.stats['samples_removed']} invalid samples"
                )
            else:
                self.logger.warning("Run with --fix to remove invalid samples")
        else:
            self.logger.info("✅ All samples validated")

        # Step 5: Save if fixes were applied
        if self.fix and self.stats["samples_removed"] > 0:
            self.logger.info("\n[5/5] Saving repaired checkpoint...")
            self._save_graph(graph)
            self.logger.info("✅ Checkpoint saved")
        else:
            self.logger.info("\n[5/5] No changes to save")

        return self.stats

    def _load_and_validate_graph(self) -> nx.Graph:
        """Load and validate graph topology."""
        with open(self.graph_path, "rb") as f:
            graph = pickle.load(f)

        # Validate graph type
        if not isinstance(
            graph, (nx.Graph, nx.DiGraph, nx.MultiGraph, nx.MultiDiGraph)
        ):
            raise ValueError(f"Invalid graph type: {type(graph)}")

        # Validate graph has nodes
        if graph.number_of_nodes() == 0:
            raise ValueError("Graph is empty (0 nodes)")

        return graph

    def _validate_metadata_db(self) -> None:
        """Validate metadata database."""
        conn = sqlite3.connect(str(self.metadata_db_path))
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        if not tables:
            conn.close()
            raise ValueError("Database has no tables")

        # Check metadata table has data
        cursor.execute("SELECT COUNT(*) FROM metadata")
        count = cursor.fetchone()[0]

        if count == 0:
            conn.close()
            raise ValueError("Metadata table is empty (0 rows)")

        conn.close()

    def _validate_samples(self, graph: nx.Graph) -> list[str]:
        """
        Validate all samples in the graph.

        Args:
            graph: NetworkX graph

        Returns:
            List of invalid sample IDs
        """
        invalid_samples = []

        for node_id in graph.nodes():
            node_data = graph.nodes[node_id]

            # Check for zero filesize
            filesize = node_data.get("filesize", 0)
            if filesize == 0:
                sample_name = node_data.get("name", "unknown")
                self.logger.warning(
                    f"Sample {node_id} ({sample_name}): invalid filesize (0 bytes)"
                )
                invalid_samples.append(str(node_id))
                self.stats["invalid_filesize"] += 1
                continue

            # Check for missing critical fields
            critical_fields = ["name", "duration", "username"]
            missing = [f for f in critical_fields if not node_data.get(f)]

            if missing:
                sample_name = node_data.get("name", "unknown")
                self.logger.warning(
                    f"Sample {node_id} ({sample_name}): missing fields {missing}"
                )
                self.stats["missing_fields"] += 1

        return invalid_samples

    def _remove_invalid_samples(
        self, graph: nx.Graph, invalid_samples: list[str]
    ) -> None:
        """
        Remove invalid samples from graph.

        Args:
            graph: NetworkX graph
            invalid_samples: List of invalid sample IDs
        """
        for sample_id in invalid_samples:
            node_id = int(sample_id)
            if node_id in graph:
                graph.remove_node(node_id)
                self.stats["samples_removed"] += 1

    def _save_graph(self, graph: nx.Graph) -> None:
        """Save graph topology to pickle file."""
        with open(self.graph_path, "wb") as f:
            pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive checkpoint integrity validation"
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="data/freesound_library",
        help="Checkpoint directory path",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix issues by removing invalid samples",
    )

    args = parser.parse_args()

    # Set up logging
    logger = setup_logging()

    # Run validation
    validator = IntegrityValidator(args.checkpoint_dir, args.fix, logger)
    stats = validator.validate_all()

    # Print summary
    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)
    print(f"Total samples: {stats['total_samples']}")
    print(f"Invalid filesize: {stats['invalid_filesize']}")
    print(f"Missing fields: {stats['missing_fields']}")
    print(f"Samples removed: {stats['samples_removed']}")
    print(f"Errors: {len(stats['errors'])}")

    if stats["errors"]:
        print("\nErrors:")
        for error in stats["errors"]:
            print(f"  - {error}")

    print("=" * 70)

    # Exit with appropriate code
    if stats["errors"]:
        sys.exit(1)
    elif stats["invalid_filesize"] > 0 or stats["missing_fields"] > 0:
        if args.fix:
            sys.exit(0)  # Fixed successfully
        else:
            sys.exit(2)  # Issues found but not fixed
    else:
        sys.exit(0)  # All good


if __name__ == "__main__":
    main()
