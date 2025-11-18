#!/usr/bin/env python3
"""
Visualize Freesound network from checkpoint file.
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# Add FollowWeb to path
sys.path.insert(0, str(Path(__file__).parent / "FollowWeb"))

from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint
from FollowWeb_Visualizor.visualization.renderers.sigma import SigmaRenderer
from FollowWeb_Visualizor.output.formatters import EmojiFormatter


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


def main():
    """Load checkpoint and generate visualization."""
    logger = setup_logging()

    # Find the most recent checkpoint
    checkpoint_dir = Path("checkpoints")
    if not checkpoint_dir.exists():
        logger.error("No checkpoints directory found")
        return 1

    checkpoints = list(checkpoint_dir.glob("freesound_*.pkl"))
    if not checkpoints:
        logger.error("No checkpoint files found")
        return 1

    # Use the most recent checkpoint
    checkpoint_file = max(checkpoints, key=lambda p: p.stat().st_mtime)
    logger.info(f"Loading checkpoint: {checkpoint_file}")

    # Load checkpoint
    checkpoint = GraphCheckpoint(str(checkpoint_file))
    data = checkpoint.load()

    if data is None:
        logger.error("Failed to load checkpoint")
        return 1

    graph = data["graph"]
    processed_ids = data.get("processed_ids", set())

    logger.info(
        f"Loaded graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges"
    )
    logger.info(f"Processed IDs: {len(processed_ids)}")

    # Create output directory
    output_dir = Path("Output")
    output_dir.mkdir(exist_ok=True)

    # Generate visualization
    logger.info("Generating visualization...")

    viz_config = {
        "show_labels": True,
        "show_tooltips": True,
        "node_size_range": [5, 30],
        "edge_width_range": [0.5, 3.0],
        "node_size_metric": "degree",
        "node_color_metric": "degree",
        "edge_width_metric": "weight",
        "template_name": "sigma_samples.html",
        "sigma_interactive": {
            "enable_audio_player": True,
            "show_labels": True,
            "show_tooltips": True,
        },
    }

    renderer = SigmaRenderer(vis_config=viz_config, template_name="sigma_samples.html")

    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"freesound_jungle_{timestamp}.html"

    success = renderer.generate_visualization(
        graph=graph, output_filename=str(output_path), metrics=None
    )

    if success:
        logger.info("=" * 70)
        logger.info(EmojiFormatter.format("completion", "Visualization Complete!"))
        logger.info("=" * 70)
        logger.info(EmojiFormatter.format("chart", f"Nodes: {graph.number_of_nodes()}"))
        logger.info(EmojiFormatter.format("chart", f"Edges: {graph.number_of_edges()}"))
        logger.info(EmojiFormatter.format("success", f"Output: {output_path}"))
        logger.info("=" * 70)
        print(f"\n✅ Open the file in your browser: {output_path.absolute()}")
        return 0
    else:
        logger.error("Visualization generation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
