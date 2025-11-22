#!/usr/bin/env python3
"""
Update only the graph data JSON file when metadata changes.

This script regenerates just the data JSON file without recreating the entire
HTML visualization. Use this when only metadata fields (like uploader_id,
available_preview_formats) have been updated without changing graph topology.

Usage:
    python scripts/visualization/update_metadata_only.py \\
        --checkpoint-dir data/freesound_library \\
        --output-file Output/graph_data.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "FollowWeb"))

from FollowWeb_Visualizor.data.checkpoint import CheckpointManager
from FollowWeb_Visualizor.data.storage.sqlite_metadata import SQLiteMetadataStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def export_graph_data(checkpoint_dir: Path, output_file: Path) -> bool:
    """
    Export graph data JSON from checkpoint.
    
    Args:
        checkpoint_dir: Path to checkpoint directory
        output_file: Path to output JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Loading checkpoint from {checkpoint_dir}")
        
        # Load checkpoint
        checkpoint_manager = CheckpointManager(checkpoint_dir)
        graph, metadata_storage = checkpoint_manager.load_checkpoint()
        
        if graph is None:
            logger.error("Failed to load graph from checkpoint")
            return False
            
        logger.info(f"Loaded graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        
        # Build nodes data
        nodes = []
        for node_id in graph.nodes():
            # Get metadata from SQLite storage
            metadata = metadata_storage.get_sample_metadata(node_id)
            
            if metadata is None:
                logger.warning(f"No metadata found for node {node_id}")
                continue
                
            node_data = {
                "id": str(node_id),
                "label": metadata.get("name", f"Sample {node_id}"),
                "size": graph.degree(node_id),
                # Include all metadata fields
                "metadata": {
                    "name": metadata.get("name"),
                    "username": metadata.get("username"),
                    "uploader_id": metadata.get("uploader_id"),
                    "duration": metadata.get("duration"),
                    "tags": metadata.get("tags", []),
                    "license": metadata.get("license"),
                    "preview_url": metadata.get("preview_url"),
                    "available_preview_formats": metadata.get("available_preview_formats", []),
                    "num_downloads": metadata.get("num_downloads"),
                    "avg_rating": metadata.get("avg_rating"),
                    "num_ratings": metadata.get("num_ratings"),
                    "description": metadata.get("description"),
                    "created": metadata.get("created"),
                }
            }
            nodes.append(node_data)
        
        # Build edges data
        edges = []
        for source, target in graph.edges():
            edge_data = {
                "source": str(source),
                "target": str(target),
            }
            edges.append(edge_data)
        
        # Create output data structure
        graph_data = {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "generated_by": "update_metadata_only.py",
            }
        }
        
        # Write to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Graph data exported to {output_file}")
        logger.info(f"   - Nodes: {len(nodes)}")
        logger.info(f"   - Edges: {len(edges)}")
        logger.info(f"   - File size: {output_file.stat().st_size / 1024:.1f} KB")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to export graph data: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Update graph data JSON with latest metadata"
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        required=True,
        help="Path to checkpoint directory"
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("Output/graph_data.json"),
        help="Path to output JSON file (default: Output/graph_data.json)"
    )
    
    args = parser.parse_args()
    
    # Validate checkpoint directory
    if not args.checkpoint_dir.exists():
        logger.error(f"Checkpoint directory not found: {args.checkpoint_dir}")
        sys.exit(1)
    
    # Export graph data
    success = export_graph_data(args.checkpoint_dir, args.output_file)
    
    if success:
        logger.info("✅ Metadata update completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Metadata update failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
