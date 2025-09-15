import networkx as nx
from pyvis.network import Network
import pandas as pd
from networkx.algorithms import community
import matplotlib.pyplot as plt
import math
import argparse
import yaml
import json

# ============================ FUNCTIONS ============================

def load_graph_from_json(filepath: str) -> nx.DiGraph:
    """
    Loads network data from the specified JSON file into a NetworkX DiGraph.
    The file is expected to be a list of objects, each with a 'user', 'followers', and 'following' key.
    """
    print(f"Attempting to load graph data from '{filepath}'...")
    G = nx.DiGraph()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: The file '{filepath}' was not found.")
        return G
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from '{filepath}'.")
        return G

    if not isinstance(data, list):
        print("ERROR: JSON data is not a list of users.")
        return G

    for user_data in data:
        user = user_data.get("user")
        followers = user_data.get("followers", [])
        followees = user_data.get("following", [])

        if not user:
            print("WARNING: 'user' not found in one of the JSON objects.")
            continue

        # Add follower edges (follower -> user)
        for follower in followers:
            G.add_edge(follower, user)

        # Add followee edges (user -> followee)
        for followee in followees:
            G.add_edge(user, followee)

    print(f"Graph loaded successfully with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    return G

def prune_graph(G: nx.DiGraph, min_degree: int) -> nx.DiGraph:
    """
    Iteratively removes nodes with a degree less than min_degree until no more nodes can be removed.
    This helps to focus on the core structure of the network.
    """
    if min_degree <= 0:
        return G
        
    print(f"\nPruning graph: removing nodes with fewer than {min_degree} connections...")
    G_pruned = G.copy()
    nodes_removed_total = 0
    while True:
        nodes_to_remove = [node for node, degree in dict(G_pruned.degree()).items() if degree < min_degree]
        
        if not nodes_to_remove:
            break # No more nodes to remove, exit loop
        
        G_pruned.remove_nodes_from(nodes_to_remove)
        nodes_removed_total += len(nodes_to_remove)

    print(f"Pruning complete. Removed {nodes_removed_total} nodes.")
    print(f"   The pruned graph has {G_pruned.number_of_nodes()} nodes and {G_pruned.number_of_edges()} edges.")
    return G_pruned

def analyze_network(G: nx.Graph):
    """
    Performs network analysis, including community detection and centrality calculations.
    It adds 'community', 'degree', 'betweenness', and 'eigenvector' as attributes to each node.
    """
    print("\nAnalyzing network structure...")
    
    # 1. Community Detection using the Louvain method
    G_undirected = G.to_undirected()
    communities = community.louvain_communities(G_undirected, seed=123)
    num_communities = len(communities)
    print(f"   Detected {num_communities} communities.")
    
    partition = {node: i for i, comm in enumerate(communities) for node in comm}
    nx.set_node_attributes(G, partition, 'community')
    
    # 2. Centrality Measures
    degree_dict = dict(G.degree())
    betweenness_dict = nx.betweenness_centrality(G) 
    eigenvector_dict = nx.eigenvector_centrality(G, max_iter=1000)

    nx.set_node_attributes(G, degree_dict, 'degree')
    nx.set_node_attributes(G, betweenness_dict, 'betweenness')
    nx.set_node_attributes(G, eigenvector_dict, 'eigenvector')

    # 3. Print Top 10 Influential Nodes
    print("\n--- Top 10 Most Influential Nodes ---")
    df = pd.DataFrame({
        'degree': degree_dict,
        'betweenness': betweenness_dict,
        'eigenvector': eigenvector_dict
    })
    
    print("\nBy Degree (Connections):")
    print(df.sort_values('degree', ascending=False).head(10))
    print("\nBy Betweenness (Bridge between communities):")
    print(df.sort_values('betweenness', ascending=False).head(10))
    print("\nBy Eigenvector (Influence):")
    print(df.sort_values('eigenvector', ascending=False).head(10))
    
    print("\nAnalysis complete.")
    return G

def visualize_network(G: nx.DiGraph, output_filename: str, config: dict):
    """
    Creates an interactive HTML visualization of the graph using PyVis.
    Nodes are sized by degree and colored by community.
    """
    print(f"\nCreating visualization... this may take a moment.")
    
    vis_config = config['visualization']['visualization_settings']
    
    net = Network(
        height=vis_config['height'], 
        width=vis_config['width'],
        directed=True, 
        notebook=vis_config['notebook'],
        cdn_resources='remote' # Use remote CDN to ensure JS libraries load
    )

    # Generate a color palette for communities
    num_communities = len(set(nx.get_node_attributes(G, 'community').values()))
    palette = plt.cm.get_cmap('viridis', num_communities)
    color_map = {i: f'#{int(c[0]*255):02x}{int(c[1]*255):02x}{int(c[2]*255):02x}' for i, c in enumerate(palette.colors)}

    # Add nodes to PyVis network with custom attributes
    for node, attrs in G.nodes(data=True):
        degree = attrs.get('degree', 1)
        community_id = attrs.get('community', 0)
        
        # Node Size Calculation
        # Calculate node size based on the selected algorithm in CONFIG
        if vis_config['scaling_algorithm'] == 'logarithmic':
            # Use log scaling to reduce size of massive nodes. math.log(max(1, degree)) prevents log(0) error.
            node_size = vis_config['base_node_size'] + math.log(max(1, degree)) * vis_config['node_size_multiplier']
        else: # Default to linear scaling
            node_size = vis_config['base_node_size'] + degree * vis_config['node_size_multiplier']

        net.add_node(
            node,
            label=node,
            size=node_size,
            color=color_map.get(community_id, '#808080'), # Default to grey
            title=( 
                f"{node} |"
                f"Connections (Degree): {degree} |"
                f"Community ID: {community_id}"
            )
        )

    # Add edges from the original graph
    net.add_edges(G.edges())

    # Enable interactive physics controls in the browser, this adds a GUI to the HTML file for tweaking physics settings.
    net.show_buttons(filter_=['physics'])

    # Generate the HTML file
    try:
        net.save_graph(output_filename)
        print(f"Interactive graph saved to '{output_filename}'. Open this file in your browser.")
    except Exception as e:
        print(f"ERROR: Failed to save the graph. {e}")


# ============================ MAIN EXECUTION ============================ 

def main():
    parser = argparse.ArgumentParser(description="Visualize Instagram follower network.")
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to the config file.')
    parser.add_argument('--input_file', type=str, help='Path to the JSON file containing scraped data. Overrides config.yaml.')
    parser.add_argument('--min_connections', type=int, help='Minimum number of connections for nodes to be included in visualization. Overrides config.yaml.')
    args = parser.parse_args()
 
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
 
    vis_config = config['visualization']
 
    # Load from the JSON file
    input_file = args.input_file if args.input_file else vis_config['input_file']
    graph = load_graph_from_json(input_file)
    
    if graph.number_of_nodes() > 0:
        # Prune the graph to focus on the core network
        min_connections = args.min_connections if args.min_connections is not None else vis_config["pruning"]["min_connections"]
        pruned_graph = prune_graph(graph, min_connections)
        
        # Analyze the network to find communities and influential nodes
        analyzed_graph = analyze_network(pruned_graph)
        
        # Create the interactive visualization
        # Dynamically create the output filename
        output_filename = f"FollowWeb_Visualization_{min_connections}.html"
        visualize_network(analyzed_graph, output_filename, config)

if __name__ == "__main__":
    main()
