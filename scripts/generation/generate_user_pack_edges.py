#!/usr/bin/env python3
"""
Generate user and pack relationship edges for Freesound network.

This script generates edges between samples by the same user and samples in the same pack.
It uses the existing IncrementalFreesoundLoader._add_batch_user_pack_edges() method
to efficiently discover relationships using batch filtering.

Usage:
    python generate_user_pack_edges.py --checkpoint-dir data/freesound_library --output edge_stats.json

Requirements:
    - Existing checkpoint with collected samples
    - Freesound API key in environment variable FREESOUND_API_KEY
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add FollowWeb to path
sys.path.insert(0, str(Path(__file__).parent / "FollowWeb"))

from FollowWeb_Visualizor.data.loaders import IncrementalFreesoundLoader  # noqa: E402
from FollowWeb_Visualizor.output.formatters import EmojiFormatter  # noqa: E402


def setup_logging() -> logging.Logger:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


def generate_edges(checkpoint_dir: str, api_key: str, logger: logging.Logger) -> dict:
    """
    Generate user and pack relationship edges.

    Args:
        checkpoint_dir: Directory containing checkpoint files
        api_key: Freesound API key
        logger: Logger instance

    Returns:
        Dictionary with edge generation statistics:
        - user_edges_added: Number of user relationship edges added
        - pack_edges_added: Number of pack relationship edges added
        - duration_seconds: Time taken to generate edges
        - total_nodes: Total nodes in graph
        - total_edges: Total edges in graph after generation
    """
    logger.info(EmojiFormatter.format("progress", "Initializing loader..."))

    # Configure loader with edge generation enabled
    loader_config = {
        "api_key": api_key,
        "checkpoint_dir": checkpoint_dir,
        "checkpoint_interval": 1,  # Save after every change
        "include_user_edges": True,
        "include_pack_edges": True,
        "max_requests": 1950,  # Respect API quota
    }

    # Initialize loader (loads existing checkpoint)
    loader = IncrementalFreesoundLoader(loader_config)

    # Check if checkpoint exists
    if loader.graph.number_of_nodes() == 0:
        logger.error(
            EmojiFormatter.format(
                "error", f"No checkpoint found in {checkpoint_dir}"
            )
        )
        return {
            "user_edges_added": 0,
            "pack_edges_added": 0,
            "duration_seconds": 0,
            "total_nodes": 0,
            "total_edges": 0,
            "error": "No checkpoint found",
        }

    logger.info(
        EmojiFormatter.format(
            "info",
            f"Loaded checkpoint: {loader.graph.number_of_nodes()} nodes, "
            f"{loader.graph.number_of_edges()} edges",
        )
    )

    # Generate edges
    logger.info(
        EmojiFormatter.format("progress", "Generating user and pack edges...")
    )
    start_time = time.time()

    try:
        stats = loader._add_batch_user_pack_edges()
        duration = time.time() - start_time

        # Save checkpoint with new edges
        logger.info(EmojiFormatter.format("progress", "Saving checkpoint..."))
        loader._save_checkpoint(
            {
                "edge_generation_completed": True,
                "user_edges_added": stats["user_edges_added"],
                "pack_edges_added": stats["pack_edges_added"],
            }
        )

        # Prepare result statistics
        result = {
            "user_edges_added": stats["user_edges_added"],
            "pack_edges_added": stats["pack_edges_added"],
            "duration_seconds": round(duration, 2),
            "total_nodes": loader.graph.number_of_nodes(),
            "total_edges": loader.graph.number_of_edges(),
        }

        logger.info(
            EmojiFormatter.format(
                "success",
                f"Edge generation complete in {duration:.2f}s: "
                f"{stats['user_edges_added']} user edges, "
                f"{stats['pack_edges_added']} pack edges",
            )
        )

        return result

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            EmojiFormatter.format("error", f"Edge generation failed: {e}")
        )
        return {
            "user_edges_added": 0,
            "pack_edges_added": 0,
            "duration_seconds": round(duration, 2),
            "total_nodes": loader.graph.number_of_nodes(),
            "total_edges": loader.graph.number_of_edges(),
            "error": str(e),
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate user and pack relationship edges for Freesound network"
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        required=True,
        help="Directory containing checkpoint files",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output JSON file for edge statistics",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Freesound API key (defaults to FREESOUND_API_KEY env var)",
    )

    args = parser.parse_args()

    # Set up logging
    logger = setup_logging()

    # Get API key
    api_key = args.api_key or os.environ.get("FREESOUND_API_KEY")
    if not api_key:
        logger.error(
            EmojiFormatter.format(
                "error",
                "Freesound API key required. Set FREESOUND_API_KEY environment variable "
                "or use --api-key argument",
            )
        )
        sys.exit(1)

    # Validate checkpoint directory
    checkpoint_dir = Path(args.checkpoint_dir)
    if not checkpoint_dir.exists():
        logger.error(
            EmojiFormatter.format(
                "error", f"Checkpoint directory not found: {checkpoint_dir}"
            )
        )
        sys.exit(1)

    # Generate edges
    logger.info(
        EmojiFormatter.format(
            "progress", f"Starting edge generation for {checkpoint_dir}"
        )
    )
    stats = generate_edges(str(checkpoint_dir), api_key, logger)

    # Write output JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(stats, f, indent=2)

    logger.info(
        EmojiFormatter.format("success", f"Statistics written to {output_path}")
    )

    # Exit with error code if edge generation failed
    if "error" in stats:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
