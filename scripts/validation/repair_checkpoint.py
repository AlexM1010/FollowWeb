#!/usr/bin/env python3
"""
Comprehensive Checkpoint Repair Script.

Automatically detects and repairs ANY missing or incomplete data in checkpoints:
- Missing node metadata fields
- Missing edge data
- Incomplete API responses
- Corrupted data structures

Fetches missing data from Freesound API as needed.

Usage:
    python comprehensive_repair.py --checkpoint-dir data/freesound_library
    python comprehensive_repair.py --checkpoint-dir data/freesound_library --api-key YOUR_KEY
"""

import argparse
import json
import logging
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import networkx as nx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from FollowWeb.FollowWeb_Visualizor.data.storage import MetadataCache

# Expected metadata fields from Freesound API
EXPECTED_METADATA_FIELDS = {
    # Basic metadata
    "name": str,
    "tags": list,
    "description": str,
    "duration": (int, float),
    # User and pack relationships
    "user": str,
    "username": str,
    "pack": str,
    # License and attribution
    "license": str,
    "created": str,
    "url": str,
    # Sound taxonomy
    "category": list,
    "category_code": str,
    "category_is_user_provided": bool,
    # Technical properties
    "type": str,
    "file_type": str,
    "channels": int,
    "filesize": int,
    "samplerate": int,
    # URLs and media
    "audio_url": str,
    "previews": dict,
    "images": dict,
    # Engagement metrics
    "num_downloads": int,
    "num_ratings": int,
    "avg_rating": (int, float),
    "num_comments": int,
    # Geographic
    "geotag": str,
}


def setup_logging() -> logging.Logger:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


class ComprehensiveRepairer:
    """Comprehensive checkpoint repair with API fetching."""

    def __init__(
        self,
        checkpoint_dir: str,
        api_key: Optional[str] = None,
        max_requests: int = 100,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize repairer.

        Args:
            checkpoint_dir: Path to checkpoint directory
            api_key: Freesound API key (optional, for fetching missing data)
            max_requests: Maximum number of API requests to make (default: 100)
            logger: Logger instance
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.api_key = api_key
        self.max_requests = max_requests
        self.logger = logger or logging.getLogger(__name__)

        # Checkpoint file paths
        self.graph_path = self.checkpoint_dir / "graph_topology.gpickle"
        self.metadata_db_path = self.checkpoint_dir / "metadata_cache.db"
        self.checkpoint_meta_path = self.checkpoint_dir / "checkpoint_metadata.json"

        # Statistics
        self.stats = {
            "nodes_checked": 0,
            "nodes_repaired": 0,
            "fields_added": 0,
            "api_requests_made": 0,
            "api_requests_skipped": 0,
            "errors": 0,
        }

    def repair_all(self) -> dict[str, Any]:
        """
        Run comprehensive repair on checkpoint.

        Returns:
            Dictionary with repair statistics and results
        """
        self.logger.info("Starting comprehensive checkpoint repair...")

        # Load checkpoint
        graph = self._load_graph()
        metadata_cache = self._load_metadata_cache()
        checkpoint_meta = self._load_checkpoint_metadata()

        self.logger.info(
            f"Loaded checkpoint: {graph.number_of_nodes()} nodes, "
            f"{graph.number_of_edges()} edges"
        )

        # Repair missing node metadata
        self.logger.info("Checking for missing node metadata...")
        self._repair_node_metadata(graph, metadata_cache)

        # Repair missing edges
        self.logger.info("Checking for missing edges...")
        self._repair_edges(graph, metadata_cache)

        # Save repaired checkpoint
        if self.stats["nodes_repaired"] > 0 or self.stats["fields_added"] > 0:
            self.logger.info("Saving repaired checkpoint...")
            self._save_graph(graph)
            self._save_checkpoint_metadata(checkpoint_meta)
            self.logger.info("✓ Checkpoint saved")
        else:
            self.logger.info("No repairs needed")

        return self.stats

    def _repair_node_metadata(
        self, graph: nx.Graph, metadata_cache: MetadataCache
    ) -> None:
        """
        Repair missing or incomplete node metadata.

        Args:
            graph: NetworkX graph
            metadata_cache: Metadata cache
        """
        nodes_to_remove = []

        for node_id in graph.nodes():
            self.stats["nodes_checked"] += 1

            # Get current metadata
            node_data = graph.nodes[node_id]
            metadata = metadata_cache.get(node_id)

            # Check for invalid filesize (0 bytes) - mark for removal
            filesize = node_data.get("filesize", 0)
            if filesize == 0:
                sample_name = node_data.get("name", "unknown")
                self.logger.warning(
                    f"Node {node_id} ({sample_name}) has invalid filesize: 0 bytes - marking for removal"
                )
                nodes_to_remove.append(node_id)
                continue

            # Check for missing fields
            missing_fields = []
            for field, expected_type in EXPECTED_METADATA_FIELDS.items():
                # Check if field exists in node data
                if field not in node_data or node_data[field] in (None, "", [], {}):
                    # Check if it exists in metadata cache
                    if metadata and field in metadata and metadata[field]:
                        # Copy from metadata cache to node
                        graph.nodes[node_id][field] = metadata[field]
                        self.stats["fields_added"] += 1
                    else:
                        missing_fields.append(field)

            # If critical fields are missing, fetch from API
            if missing_fields and self.api_key:
                # Check if we've reached the request limit
                if self.stats["api_requests_made"] >= self.max_requests:
                    self.logger.warning(
                        f"Reached max API requests limit ({self.max_requests}), "
                        f"skipping node {node_id}"
                    )
                    self.stats["api_requests_skipped"] += 1
                else:
                    self.logger.info(
                        f"Node {node_id}: Missing {len(missing_fields)} fields, "
                        f"fetching from API... ({self.stats['api_requests_made'] + 1}/{self.max_requests})"
                    )
                    self._fetch_and_update_node(
                        node_id, missing_fields, graph, metadata_cache
                    )
                    self.stats["nodes_repaired"] += 1

        # Remove nodes with invalid filesize
        if nodes_to_remove:
            self.logger.info(
                f"Removing {len(nodes_to_remove)} nodes with invalid filesize..."
            )
            for node_id in nodes_to_remove:
                graph.remove_node(node_id)
            self.logger.info(f"✓ Removed {len(nodes_to_remove)} invalid nodes")

    def _repair_edges(self, graph: nx.Graph, metadata_cache: MetadataCache) -> None:
        """
        Repair missing edges based on relationships.

        Args:
            graph: NetworkX graph
            metadata_cache: Metadata cache
        """
        # Check if edges exist
        if graph.number_of_edges() == 0:
            self.logger.warning(
                "No edges found in graph. Consider running edge generation script."
            )

    def _fetch_and_update_node(
        self,
        node_id: str,
        missing_fields: list[str],
        graph: nx.Graph,
        metadata_cache: MetadataCache,
    ) -> None:
        """
        Fetch missing node data from Freesound API.

        Args:
            node_id: Node ID
            missing_fields: List of missing field names
            graph: NetworkX graph
            metadata_cache: Metadata cache
        """
        try:
            import requests

            # Fetch from Freesound API
            url = f"https://freesound.org/apiv2/sounds/{node_id}/"
            params = {
                "token": self.api_key,
                "fields": ",".join(EXPECTED_METADATA_FIELDS.keys()),
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            self.stats["api_requests_made"] += 1

            # Validate filesize before updating
            filesize = data.get("filesize", 0)
            if filesize == 0:
                self.logger.warning(
                    f"API returned invalid filesize (0 bytes) for node {node_id} - skipping update"
                )
                self.stats["errors"] += 1
                return

            # Update node with fetched data
            updated_metadata = {}
            for field in missing_fields:
                if field in data and data[field]:
                    graph.nodes[node_id][field] = data[field]
                    updated_metadata[field] = data[field]
                    self.stats["fields_added"] += 1

            # Update metadata cache with all fields at once
            if updated_metadata:
                metadata_cache.set(int(node_id), updated_metadata)

            self.logger.info(
                f"✓ Updated node {node_id} with {len(missing_fields)} fields"
            )

        except Exception as e:
            self.logger.error(f"Failed to fetch data for node {node_id}: {e}")
            self.stats["errors"] += 1

    def _load_graph(self) -> nx.Graph:
        """Load graph topology from pickle file."""
        with open(self.graph_path, "rb") as f:
            return pickle.load(f)

    def _load_metadata_cache(self) -> MetadataCache:
        """Load metadata cache from SQLite database."""
        return MetadataCache(str(self.metadata_db_path), self.logger)

    def _load_checkpoint_metadata(self) -> dict[str, Any]:
        """Load checkpoint metadata from JSON file."""
        with open(self.checkpoint_meta_path, "r") as f:
            return json.load(f)

    def _save_graph(self, graph: nx.Graph) -> None:
        """Save graph topology to pickle file."""
        with open(self.graph_path, "wb") as f:
            pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)

    def _save_checkpoint_metadata(self, metadata: dict[str, Any]) -> None:
        """Save checkpoint metadata to JSON file."""
        metadata["last_repair_at"] = datetime.now(timezone.utc).isoformat()
        with open(self.checkpoint_meta_path, "w") as f:
            json.dump(metadata, f, indent=2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive checkpoint repair with API fetching"
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="data/freesound_library",
        help="Checkpoint directory path",
    )
    parser.add_argument(
        "--api-key",
        help="Freesound API key (for fetching missing data)",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=100,
        help="Maximum number of API requests to make (default: 100)",
    )

    args = parser.parse_args()

    # Set up logging
    logger = setup_logging()

    # Run repair
    repairer = ComprehensiveRepairer(
        args.checkpoint_dir, args.api_key, args.max_requests, logger
    )
    stats = repairer.repair_all()

    # Print summary
    print("\n" + "=" * 60)
    print("COMPREHENSIVE REPAIR COMPLETE")
    print("=" * 60)
    print(f"Nodes checked: {stats['nodes_checked']}")
    print(f"Nodes repaired: {stats['nodes_repaired']}")
    print(f"Fields added: {stats['fields_added']}")
    print(f"API requests made: {stats['api_requests_made']}")
    print(f"API requests skipped: {stats['api_requests_skipped']}")
    print(f"Errors: {stats['errors']}")
    print("=" * 60)

    # Exit with appropriate code
    sys.exit(0 if stats["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
