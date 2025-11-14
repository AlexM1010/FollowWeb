#!/usr/bin/env python3
"""
Generate edges from existing checkpoint data (zero API requests).

This script generates user, pack, and tag edges from existing graph data
without making any API requests. It reads the checkpoint, generates edges
based on relationships in the metadata, and saves the updated checkpoint.

Usage:
    python generate_edges.py --checkpoint-dir data/freesound_library

Features:
- User edges: Connect samples by the same user
- Pack edges: Connect samples in the same pack
- Tag edges: Connect samples with similar tags (Jaccard similarity)
- Zero API requests (all data from existing checkpoint)
"""

import argparse
import json
import logging
import pickle
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import networkx as nx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from FollowWeb.FollowWeb_Visualizor.data.storage import MetadataCache


def setup_logging() -> logging.Logger:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


class EdgeGenerator:
    """Generate edges from existing checkpoint data."""

    def __init__(self, checkpoint_dir: str, logger: logging.Logger):
        """
        Initialize edge generator.

        Args:
            checkpoint_dir: Path to checkpoint directory
            logger: Logger instance
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.logger = logger

        # Checkpoint file paths
        self.graph_path = self.checkpoint_dir / "graph_topology.gpickle"
        self.metadata_db_path = self.checkpoint_dir / "metadata_cache.db"
        self.checkpoint_meta_path = self.checkpoint_dir / "checkpoint_metadata.json"

    def generate_all_edges(
        self,
        include_user: bool = True,
        include_pack: bool = True,
        include_tag: bool = True,
        tag_threshold: float = 0.3,
    ) -> dict[str, int]:
        """
        Generate all edge types from existing data.

        Args:
            include_user: Generate user edges
            include_pack: Generate pack edges
            include_tag: Generate tag edges
            tag_threshold: Minimum Jaccard similarity for tag edges

        Returns:
            Dictionary with edge counts by type
        """
        self.logger.info("Loading checkpoint...")
        graph = self._load_graph()
        metadata_cache = self._load_metadata_cache()
        checkpoint_meta = self._load_checkpoint_metadata()

        initial_edges = graph.number_of_edges()
        self.logger.info(
            f"Loaded checkpoint: {graph.number_of_nodes()} nodes, {initial_edges} edges"
        )

        edge_stats = {}

        # Generate user edges
        if include_user:
            self.logger.info("Generating user edges...")
            user_edges = self._add_user_edges(graph, metadata_cache)
            edge_stats["user_edges_added"] = user_edges
            self.logger.info(f"✓ Added {user_edges} user edges")

        # Generate pack edges
        if include_pack:
            self.logger.info("Generating pack edges...")
            pack_edges = self._add_pack_edges(graph, metadata_cache)
            edge_stats["pack_edges_added"] = pack_edges
            self.logger.info(f"✓ Added {pack_edges} pack edges")

        # Generate tag edges
        if include_tag:
            self.logger.info(f"Generating tag edges (threshold={tag_threshold})...")
            tag_edges = self._add_tag_edges(graph, metadata_cache, tag_threshold)
            edge_stats["tag_edges_added"] = tag_edges
            self.logger.info(f"✓ Added {tag_edges} tag edges")

        # Save updated checkpoint
        final_edges = graph.number_of_edges()
        total_added = final_edges - initial_edges
        self.logger.info(f"Total edges added: {total_added}")

        # Update checkpoint metadata
        checkpoint_meta["edge_count"] = final_edges
        checkpoint_meta["edge_generation"] = {
            "timestamp": self._get_timestamp(),
            "edges_before": initial_edges,
            "edges_after": final_edges,
            "edges_added": total_added,
            "breakdown": edge_stats,
        }

        # Save checkpoint
        self.logger.info("Saving updated checkpoint...")
        self._save_graph(graph)
        self._save_checkpoint_metadata(checkpoint_meta)
        self.logger.info("✓ Checkpoint saved")

        return edge_stats

    def _add_user_edges(
        self, graph: nx.Graph, metadata_cache: MetadataCache
    ) -> int:
        """
        Generate edges between samples by the same user.

        Args:
            graph: NetworkX graph
            metadata_cache: Metadata cache

        Returns:
            Number of edges added
        """
        # Group samples by username
        samples_by_user = defaultdict(list)

        for node_id in graph.nodes():
            metadata = metadata_cache.get(node_id)
            if metadata:
                username = metadata.get("username") or metadata.get("user")
                if username:
                    samples_by_user[username].append(node_id)

        # Create edges between all samples by same user
        edges_added = 0
        for username, samples in samples_by_user.items():
            if len(samples) > 1:
                # Create edges between all pairs
                for sample1, sample2 in combinations(samples, 2):
                    if not graph.has_edge(sample1, sample2):
                        graph.add_edge(sample1, sample2, edge_type="user")
                        edges_added += 1

        return edges_added

    def _add_pack_edges(
        self, graph: nx.Graph, metadata_cache: MetadataCache
    ) -> int:
        """
        Generate edges between samples in the same pack.

        Args:
            graph: NetworkX graph
            metadata_cache: Metadata cache

        Returns:
            Number of edges added
        """
        # Group samples by pack
        samples_by_pack = defaultdict(list)

        for node_id in graph.nodes():
            metadata = metadata_cache.get(node_id)
            if metadata:
                pack = metadata.get("pack")
                if pack:
                    samples_by_pack[pack].append(node_id)

        # Create edges between all samples in same pack
        edges_added = 0
        for pack, samples in samples_by_pack.items():
            if len(samples) > 1:
                # Create edges between all pairs
                for sample1, sample2 in combinations(samples, 2):
                    if not graph.has_edge(sample1, sample2):
                        graph.add_edge(sample1, sample2, edge_type="pack")
                        edges_added += 1

        return edges_added

    def _add_tag_edges(
        self,
        graph: nx.Graph,
        metadata_cache: MetadataCache,
        threshold: float,
    ) -> int:
        """
        Generate edges between samples with similar tags.

        Uses Jaccard similarity: |A ∩ B| / |A ∪ B|

        Args:
            graph: NetworkX graph
            metadata_cache: Metadata cache
            threshold: Minimum Jaccard similarity (0.0 to 1.0)

        Returns:
            Number of edges added
        """
        # Get all node IDs
        node_ids = list(graph.nodes())

        # Compute tag similarity for all pairs
        edges_added = 0
        total_pairs = len(node_ids) * (len(node_ids) - 1) // 2

        # For large graphs, sample pairs to avoid O(n^2) complexity
        if total_pairs > 100000:
            self.logger.warning(
                f"Large graph ({len(node_ids)} nodes, {total_pairs} pairs). "
                "Sampling 100,000 pairs for tag similarity..."
            )
            import random

            pairs = random.sample(list(combinations(node_ids, 2)), 100000)
        else:
            pairs = combinations(node_ids, 2)

        for node1, node2 in pairs:
            # Skip if edge already exists
            if graph.has_edge(node1, node2):
                continue

            # Get tags for both samples
            metadata1 = metadata_cache.get(node1)
            metadata2 = metadata_cache.get(node2)

            if not metadata1 or not metadata2:
                continue

            tags1 = set(metadata1.get("tags", []))
            tags2 = set(metadata2.get("tags", []))

            if not tags1 or not tags2:
                continue

            # Compute Jaccard similarity
            intersection = len(tags1 & tags2)
            union = len(tags1 | tags2)

            if union > 0:
                similarity = intersection / union

                if similarity >= threshold:
                    graph.add_edge(
                        node1, node2, edge_type="tag", similarity=similarity
                    )
                    edges_added += 1

        return edges_added

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
        with open(self.checkpoint_meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate edges from existing checkpoint data"
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="data/freesound_library",
        help="Checkpoint directory path",
    )
    parser.add_argument(
        "--user-edges",
        action="store_true",
        default=True,
        help="Generate user edges (default: True)",
    )
    parser.add_argument(
        "--pack-edges",
        action="store_true",
        default=True,
        help="Generate pack edges (default: True)",
    )
    parser.add_argument(
        "--tag-edges",
        action="store_true",
        default=True,
        help="Generate tag edges (default: True)",
    )
    parser.add_argument(
        "--tag-threshold",
        type=float,
        default=0.3,
        help="Minimum Jaccard similarity for tag edges (default: 0.3)",
    )
    parser.add_argument(
        "--output",
        help="Output file for edge statistics (JSON)",
    )

    args = parser.parse_args()

    # Set up logging
    logger = setup_logging()

    # Generate edges
    generator = EdgeGenerator(args.checkpoint_dir, logger)
    edge_stats = generator.generate_all_edges(
        include_user=args.user_edges,
        include_pack=args.pack_edges,
        include_tag=args.tag_edges,
        tag_threshold=args.tag_threshold,
    )

    # Save statistics if output file specified
    if args.output:
        with open(args.output, "w") as f:
            json.dump(edge_stats, f, indent=2)
        logger.info(f"Edge statistics saved to {args.output}")

    # Print summary
    print("\n" + "=" * 60)
    print("EDGE GENERATION COMPLETE")
    print("=" * 60)
    for edge_type, count in edge_stats.items():
        print(f"{edge_type}: {count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
