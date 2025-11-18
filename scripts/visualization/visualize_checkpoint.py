#!/usr/bin/env python3
"""
Generate visualization from existing checkpoint.

This script loads a checkpoint from the split architecture (graph + metadata + checkpoint_metadata)
and generates a Sigma.js visualization.
"""

import argparse
import json
import logging
import pickle
import sys
from datetime import datetime
from pathlib import Path

# Add FollowWeb to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "FollowWeb"))

import networkx as nx
from FollowWeb_Visualizor.data.storage import MetadataCache
from FollowWeb_Visualizor.visualization.renderers.sigma import SigmaRenderer


# Checkpoint filenames
GRAPH_TOPOLOGY_FILENAME = "graph_topology.gpickle"
METADATA_CACHE_FILENAME = "metadata_cache.db"
CHECKPOINT_META_FILENAME = "checkpoint_metadata.json"


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


def load_graph(graph_path: Path) -> nx.DiGraph:
    """Load graph topology from pickle file."""
    with open(graph_path, "rb") as f:
        graph = pickle.load(f)  # nosec B301

    if not isinstance(graph, (nx.Graph, nx.DiGraph)):
        raise TypeError(
            f"Expected NetworkX Graph or DiGraph, got {type(graph).__name__}"
        )

    return graph


def main():
    """Load checkpoint and generate visualization."""
    parser = argparse.ArgumentParser(
        description="Generate visualization from checkpoint"
    )
    parser.add_argument("--checkpoint-dir", required=True, help="Checkpoint directory")
    parser.add_argument("--output-dir", default="Output", help="Output directory")
    parser.add_argument(
        "--renderer-type",
        default="sigma",
        help="Renderer type (sigma, pyvis, matplotlib)",
    )

    args = parser.parse_args()
    logger = setup_logging()

    checkpoint_dir = Path(args.checkpoint_dir)
    if not checkpoint_dir.exists():
        logger.error(f"Checkpoint directory not found: {checkpoint_dir}")
        return 2

    # Load checkpoint components
    graph_path = checkpoint_dir / GRAPH_TOPOLOGY_FILENAME
    metadata_db_path = checkpoint_dir / METADATA_CACHE_FILENAME
    checkpoint_meta_path = checkpoint_dir / CHECKPOINT_META_FILENAME

    if not graph_path.exists():
        logger.error(f"Graph topology file not found: {graph_path}")
        return 2

    if not metadata_db_path.exists():
        logger.error(f"Metadata cache file not found: {metadata_db_path}")
        return 2

    # Load graph
    logger.info(f"Loading graph from: {graph_path}")
    try:
        graph = load_graph(graph_path)
        logger.info(
            f"Loaded graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges"
        )
    except Exception as e:
        logger.error(f"Failed to load graph: {e}")
        import traceback

        traceback.print_exc()
        return 2

    # Load metadata cache to attach to nodes
    logger.info(f"Loading metadata from: {metadata_db_path}")
    try:
        with MetadataCache(str(metadata_db_path), logger) as metadata_cache:
            # Attach metadata to nodes
            for node_id in graph.nodes():
                # Convert string node ID to integer for metadata lookup
                cache_id = int(node_id)
                metadata = metadata_cache.get(cache_id)
                if metadata:
                    # Attach metadata as node attributes
                    for key, value in metadata.items():
                        graph.nodes[node_id][key] = value

            logger.info(f"Attached metadata to {graph.number_of_nodes()} nodes")
    except Exception as e:
        logger.warning(
            f"Failed to load metadata (visualization will continue without it): {e}"
        )

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # Generate visualization
    logger.info(f"Generating {args.renderer_type} visualization...")

    try:
        if args.renderer_type == "sigma":
            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"freesound_{timestamp}.html"
            output_path = output_dir / output_filename

            # Create visualization config with all required options
            vis_config = {
                # Display settings
                "show_labels": True,
                "show_tooltips": True,
                "show_legend": True,
                "enable_audio_player": True,
                # Node sizing
                "node_size_metric": "degree",
                "base_node_size": 10.0,
                "node_size_multiplier": 2.0,
                "scaling_algorithm": "logarithmic",
                # Edge styling
                "edge_thickness_metric": "weight",
                "base_edge_thickness": 1.0,
                "base_edge_width": 0.5,
                "edge_width_multiplier": 1.5,
                "edge_width_scaling": "logarithmic",
                # Colors
                "bridge_color": "#6e6e6e",
                "intra_community_color": "#c0c0c0",
                # Alpha values
                "node_alpha": 0.8,
                "edge_alpha": 0.3,
                # Font
                "font_size": 8,
            }

            # Create renderer and generate visualization
            renderer = SigmaRenderer(vis_config=vis_config)
            success = renderer.generate_visualization(
                graph=graph,
                output_filename=str(output_path),
                metrics=None,  # Let renderer calculate metrics
            )

            if success:
                logger.info(f"✅ Visualization generated: {output_path}")
                return 0
            else:
                logger.error("Failed to generate visualization")
                return 2
        else:
            logger.error(f"Unsupported renderer type: {args.renderer_type}")
            return 2
    except Exception as e:
        logger.error(f"Failed to generate visualization: {e}")
        import traceback

        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
