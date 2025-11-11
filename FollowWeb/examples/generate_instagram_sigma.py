"""
Example script to generate Instagram network visualization using Sigma.js.

This script demonstrates how to use the unified SigmaRenderer with the Instagram template
to create interactive HTML visualizations from Instagram follower/following data.
"""

import json
import sys
from pathlib import Path

import networkx as nx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from FollowWeb_Visualizor.visualization.renderers import SigmaRenderer


def load_instagram_data(json_path: str) -> nx.DiGraph:
    """
    Load Instagram follower/following data and create a NetworkX graph.

    Args:
        json_path: Path to the Instagram JSON data file

    Returns:
        NetworkX directed graph with follower/following relationships
    """
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    # Create directed graph
    graph = nx.DiGraph()

    # Add nodes with follower/following counts
    for user_data in data:
        user = user_data['user']
        followers_count = len(user_data.get('followers', []))
        following_count = len(user_data.get('following', []))

        graph.add_node(
            user,
            followers_count=followers_count,
            following_count=following_count
        )

    # Add edges for following relationships
    for user_data in data:
        user = user_data['user']
        for followed_user in user_data.get('following', []):
            if graph.has_node(followed_user):
                graph.add_edge(user, followed_user)

    return graph


def main():
    """Generate Instagram Sigma.js visualization."""

    # Load Instagram data
    json_path = Path(__file__).parent / "followers_following.json"
    print(f"Loading Instagram data from: {json_path}")

    graph = load_instagram_data(str(json_path))
    print(f"Loaded graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")

    # Configure visualization
    vis_config = {
        "sigma_interactive": {
            "show_labels": True,
            "show_tooltips": True,
        }
    }

    # Create renderer with Instagram template
    renderer = SigmaRenderer(
        vis_config=vis_config,
        template_name="sigma_instagram.html"
    )

    # Generate visualization
    output_path = Path(__file__).parent.parent / "Output" / "instagram_network_sigma.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Generating visualization...")
    success = renderer.generate_visualization(
        graph=graph,
        output_filename=str(output_path)
    )

    if success:
        print(f"✓ Visualization saved to: {output_path}")
        print("\nOpen the file in your browser to view the interactive network!")
    else:
        print("✗ Failed to generate visualization")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
