#!/usr/bin/env python3
"""Verify that checkpoint contains complete API data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "FollowWeb"))

from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint

# Check old checkpoint
checkpoint = GraphCheckpoint('checkpoints/freesound_1762742088.pkl')
data = checkpoint.load()

if data:
    graph = data['graph']
    print(f"Checkpoint loaded: {graph.number_of_nodes()} nodes")
    
    if graph.number_of_nodes() > 0:
        # Get first node
        node_id, attrs = list(graph.nodes(data=True))[0]
        
        print(f"\nSample Node: {node_id}")
        print(f"Total fields: {len(attrs)}")
        print("\nAll fields:")
        for key in sorted(attrs.keys()):
            value = attrs[key]
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            elif isinstance(value, dict):
                value = f"dict with {len(value)} keys"
            elif isinstance(value, list) and len(value) > 3:
                value = f"list with {len(value)} items"
            print(f"  - {key}: {value}")
else:
    print("No checkpoint found")
