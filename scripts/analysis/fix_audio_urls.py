#!/usr/bin/env python3
"""
Fix audio URLs in checkpoint by fetching metadata for existing nodes.
"""

import logging
import os
import sys
import time
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Add FollowWeb to path
sys.path.insert(0, str(Path(__file__).parent / "FollowWeb"))

from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint  # noqa: E402
from FollowWeb_Visualizor.data.loaders.freesound import FreesoundLoader  # noqa: E402
from FollowWeb_Visualizor.output.formatters import EmojiFormatter  # noqa: E402


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


def main():
    """Fix audio URLs in checkpoint."""
    logger = setup_logging()

    # Load API key
    api_key = os.environ.get("FREESOUND_API_KEY")
    if not api_key:
        logger.error("FREESOUND_API_KEY not found")
        return 1

    # Find checkpoint
    checkpoint_dir = Path("checkpoints")
    checkpoints = list(checkpoint_dir.glob("freesound_*.pkl"))
    if not checkpoints:
        logger.error("No checkpoint files found")
        return 1

    checkpoint_file = max(checkpoints, key=lambda p: p.stat().st_mtime)
    logger.info(f"Loading checkpoint: {checkpoint_file}")

    # Load checkpoint
    checkpoint = GraphCheckpoint(str(checkpoint_file))
    data = checkpoint.load()

    if data is None:
        logger.error("Failed to load checkpoint")
        return 1

    graph = data["graph"]
    logger.info(f"Loaded graph: {graph.number_of_nodes()} nodes")

    # Initialize Freesound loader
    loader = FreesoundLoader({"api_key": api_key})

    # Update audio URLs for each node
    logger.info("Fetching audio URLs...")
    updated = 0

    for node_id in graph.nodes():
        try:
            # Fetch fresh metadata
            sample_data = loader._fetch_sample_metadata(int(node_id))
            audio_url = sample_data.get("audio_url", "")

            if audio_url:
                graph.nodes[node_id]["audio_url"] = audio_url
                updated += 1
                logger.info(f"Updated {node_id}: {audio_url[:50]}...")
            else:
                logger.warning(f"No audio URL for {node_id}")

            # Rate limiting
            time.sleep(1.1)  # ~60 requests per minute

        except Exception as e:
            logger.error(f"Failed to fetch metadata for {node_id}: {e}")

    logger.info(f"Updated {updated}/{graph.number_of_nodes()} nodes with audio URLs")

    # Save updated checkpoint
    checkpoint.save(graph, data.get("processed_ids", set()))
    logger.info(
        EmojiFormatter.format("success", f"Checkpoint updated: {checkpoint_file}")
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
