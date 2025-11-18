#!/usr/bin/env python3
"""
Regenerate checkpoint metadata from graph topology file.

This script is used by the freesound-data-remediation workflow to regenerate
missing checkpoint metadata files from the graph topology.
"""

import json
import pickle
from pathlib import Path
from datetime import datetime, timezone

def main():
    checkpoint_dir = Path("data/freesound_library")
    graph_file = checkpoint_dir / "graph_topology.gpickle"
    
    # Load graph
    with open(graph_file, 'rb') as f:
        graph = pickle.load(f)
    
    # Generate metadata
    metadata = {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "processed_samples": graph.number_of_nodes(),
        "version": "1.0",
        "regenerated": True,
        "regeneration_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Save metadata
    metadata_file = checkpoint_dir / "checkpoint_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Regenerated metadata: {metadata['nodes']} nodes, {metadata['edges']} edges")

if __name__ == "__main__":
    main()
