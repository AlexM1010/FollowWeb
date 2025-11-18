#!/usr/bin/env python3
"""Check if checkpoint has audio URLs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "FollowWeb"))

from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint

checkpoint_dir = Path("checkpoints")
checkpoints = list(checkpoint_dir.glob("freesound_*.pkl"))

if checkpoints:
    checkpoint_file = max(checkpoints, key=lambda p: p.stat().st_mtime)
    print(f"Loading: {checkpoint_file}")

    checkpoint = GraphCheckpoint(str(checkpoint_file))
    data = checkpoint.load()

    if data:
        graph = data["graph"]
        print(
            f"\nGraph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges"
        )

        # Check first 3 nodes for audio URLs
        for i, (node_id, attrs) in enumerate(list(graph.nodes(data=True))[:3]):
            audio_url = attrs.get("audio_url", "")
            print(f"\nNode {node_id}:")
            print(f"  Name: {attrs.get('name', 'N/A')}")
            print(f"  Audio URL: {audio_url[:80] if audio_url else 'EMPTY'}")

            if i >= 2:
                break
else:
    print("No checkpoints found")
