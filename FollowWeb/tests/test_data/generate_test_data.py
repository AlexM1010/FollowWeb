#!/usr/bin/env python3
"""
Generate anonymized test datasets from followers_following.json

This script creates tiny (5%), small (15%), medium (33%), large (66%), and full (100%)
anonymized datasets for testing purposes, replacing real usernames with simple fake names
like 'alice_smith_a1b2c3'.
"""

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, List

import networkx as nx
import numpy as np
import pandas as pd


def create_username_mapping(all_usernames: List[str]) -> Dict[str, str]:
    """
    Create a mapping from original usernames to unique fake names.

    Generates names in format: name_name_hash

    Args:
        all_usernames: List of all original usernames to map

    Returns:
        Dictionary mapping original usernames to unique fake names
    """
    # Simple fake names for readable test data
    first_names = [
        "alice",
        "bob",
        "charlie",
        "diana",
        "eve",
        "frank",
        "grace",
        "henry",
        "iris",
        "jack",
        "kate",
        "liam",
        "maya",
        "noah",
        "olivia",
        "peter",
        "quinn",
        "ruby",
        "sam",
        "tara",
        "uma",
        "victor",
        "wendy",
        "xavier",
        "yara",
        "zoe",
        "alex",
        "blake",
        "casey",
        "drew",
        "emery",
        "finley",
    ]

    last_names = [
        "smith",
        "jones",
        "brown",
        "davis",
        "miller",
        "wilson",
        "moore",
        "taylor",
        "anderson",
        "thomas",
        "jackson",
        "white",
        "harris",
        "martin",
        "garcia",
        "martinez",
        "robinson",
        "clark",
        "rodriguez",
        "lewis",
        "lee",
        "walker",
        "hall",
        "allen",
        "young",
        "hernandez",
        "king",
        "wright",
        "lopez",
        "hill",
        "scott",
        "green",
        "adams",
        "baker",
        "gonzalez",
        "nelson",
        "carter",
        "mitchell",
    ]

    username_mapping = {}

    # Sort usernames for consistent ordering
    sorted_usernames = sorted(all_usernames)

    for username in sorted_usernames:
        # Generate hash for this username
        hash_input = f"followweb_test_{username}".encode()
        hash_hex = hashlib.md5(hash_input).hexdigest()

        # Use hash to select first and last name
        hash_int = int(hash_hex, 16)
        first_idx = hash_int % len(first_names)
        last_idx = (hash_int // len(first_names)) % len(last_names)

        # Take first 6 characters of hash for uniqueness
        hash_suffix = hash_hex[:6]

        # Create name in format: firstname_lastname_hash
        fake_name = f"{first_names[first_idx]}_{last_names[last_idx]}_{hash_suffix}"

        username_mapping[username] = fake_name

    return username_mapping


def load_original_data(filepath: str) -> List[Dict[str, Any]]:
    """Load the original followers_following.json data."""
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded {len(data)} user records from {filepath}")
        return data
    except FileNotFoundError:
        print(f"Error: Could not find {filepath}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        return []


def analyze_network_structure(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze the structure of the network for statistics using pandas/numpy."""
    if not data:
        return {}

    # Convert to DataFrame for efficient analysis
    df = pd.DataFrame(data)
    df["follower_count"] = df["followers"].apply(len)
    df["following_count"] = df["following"].apply(len)

    # Use numpy for efficient statistical calculations
    follower_counts = df["follower_count"].values
    following_counts = df["following_count"].values

    total_users = len(df)
    total_followers = np.sum(follower_counts)
    total_following = np.sum(following_counts)

    return {
        "total_users": total_users,
        "total_follower_relationships": int(total_followers),
        "total_following_relationships": int(total_following),
        "avg_followers_per_user": float(np.mean(follower_counts)),
        "avg_following_per_user": float(np.mean(following_counts)),
        "max_followers": int(np.max(follower_counts)),
        "max_following": int(np.max(following_counts)),
        "min_followers": int(np.min(follower_counts)),
        "min_following": int(np.min(following_counts)),
        "std_followers": float(np.std(follower_counts)),
        "std_following": float(np.std(following_counts)),
        "median_followers": float(np.median(follower_counts)),
        "median_following": float(np.median(following_counts)),
    }


def analyze_graph_structure(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze detailed graph structure including connectivity and components using NetworkX efficiently."""
    if not data:
        return {}

    # Build NetworkX graph for analysis
    graph = nx.DiGraph()  # Directed graph for follower relationships
    user_data_map = {user["user"]: user for user in data}

    # Efficiently add all nodes first
    graph.add_nodes_from(user_data_map.keys())

    # Build edges more efficiently using set comprehension for filtering
    valid_users = set(user_data_map.keys())
    edges = [
        (user_data["user"], following)
        for user_data in data
        for following in user_data.get("following", [])
        if following in valid_users
    ]
    graph.add_edges_from(edges)

    # Basic graph metrics
    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()

    if num_nodes == 0:
        return {"graph_structure": {}, "connectivity": {}, "degree_distribution": {}}

    # Convert to undirected for connectivity analysis (only if needed)
    G_undirected = graph.to_undirected()

    # Connectivity analysis using NetworkX built-in functions
    connected_components = list(nx.connected_components(G_undirected))
    num_components = len(connected_components)
    largest_component_size = max((len(cc) for cc in connected_components), default=0)

    # Use NetworkX for reciprocity calculation (more efficient)
    try:
        reciprocity = nx.reciprocity(graph)
    except BaseException:
        # Fallback calculation if NetworkX reciprocity fails
        edge_set = set(graph.edges())
        mutual_edges = sum(1 for u, v in edge_set if (v, u) in edge_set) // 2
        reciprocity = (2 * mutual_edges) / num_edges if num_edges > 0 else 0

    # Use numpy for degree distribution analysis
    in_degrees = np.array(list(dict(graph.in_degree()).values()))
    out_degrees = np.array(list(dict(graph.out_degree()).values()))

    # Calculate density using NetworkX
    density = nx.density(graph)

    # Count mutual connections more efficiently
    mutual_edges = sum(1 for u, v in graph.edges() if graph.has_edge(v, u)) // 2

    return {
        "graph_structure": {
            "nodes": num_nodes,
            "directed_edges": num_edges,
            "mutual_connections": mutual_edges,
            "density": float(density),
            "reciprocity": float(reciprocity),
        },
        "connectivity": {
            "connected_components": num_components,
            "largest_component_size": largest_component_size,
            "largest_component_percentage": (
                (largest_component_size / num_nodes * 100) if num_nodes > 0 else 0
            ),
        },
        "degree_distribution": {
            "avg_in_degree": float(np.mean(in_degrees)),
            "avg_out_degree": float(np.mean(out_degrees)),
            "max_in_degree": int(np.max(in_degrees)),
            "max_out_degree": int(np.max(out_degrees)),
            "min_in_degree": int(np.min(in_degrees)),
            "min_out_degree": int(np.min(out_degrees)),
            "std_in_degree": float(np.std(in_degrees)),
            "std_out_degree": float(np.std(out_degrees)),
            "median_in_degree": float(np.median(in_degrees)),
            "median_out_degree": float(np.median(out_degrees)),
        },
    }


def create_anonymized_dataset(
    data: List[Dict[str, Any]], max_users: int = None
) -> List[Dict[str, Any]]:
    """
    Create an anonymized dataset with optional size limit.

    Args:
        data: Original data
        max_users: Maximum number of users to include (None for all)

    Returns:
        Anonymized dataset
    """
    if not data:
        return []

    # Select subset if requested
    selected_data = data[:max_users] if max_users else data

    # Pre-compute selected usernames set for efficient lookup
    selected_usernames = {user["user"] for user in selected_data}

    # Efficiently collect all usernames using set operations
    all_usernames = selected_usernames.copy()

    # Use batch operations for better performance
    for user_data in selected_data:
        followers = user_data.get("followers", [])
        following = user_data.get("following", [])
        if followers:
            all_usernames.update(followers)
        if following:
            all_usernames.update(following)

    # Create unique username mapping
    username_mapping = create_username_mapping(list(all_usernames))

    # Create anonymized dataset with optimized filtering
    result = []
    for user_data in selected_data:
        # Map all followers and following (not just those with records)
        mapped_followers = []
        for follower in user_data.get("followers", []):
            if follower in username_mapping:
                mapped_followers.append(username_mapping[follower])

        mapped_following = []
        for following in user_data.get("following", []):
            if following in username_mapping:
                mapped_following.append(username_mapping[following])

        result.append(
            {
                "user": username_mapping[user_data["user"]],
                "followers": mapped_followers,
                "following": mapped_following,
            }
        )

    return result


def validate_dataset(data: List[Dict[str, Any]]) -> bool:
    """Validate that the dataset has proper structure."""
    if not data:
        return False

    for user_data in data:
        if not isinstance(user_data, dict):
            return False
        if "user" not in user_data:
            return False
        if not isinstance(user_data.get("followers", []), list):
            return False
        if not isinstance(user_data.get("following", []), list):
            return False

    return True


def save_dataset(data: List[Dict[str, Any]], filepath: str, description: str):
    """Save dataset to file with validation."""
    if not validate_dataset(data):
        print(f"Error: Invalid dataset structure for {description}")
        return False

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        stats = analyze_network_structure(data)
        print(f"\n{description} saved to {filepath}")
        print(f"  Users: {stats.get('total_users', 0)}")
        print(f"  Avg followers per user: {stats.get('avg_followers_per_user', 0):.1f}")
        print(f"  Avg following per user: {stats.get('avg_following_per_user', 0):.1f}")
        return True

    except Exception as e:
        print(f"Error saving {description} to {filepath}: {e}")
        return False


def create_network_preserving_sample(
    data: List[Dict[str, Any]], target_size: int
) -> List[Dict[str, Any]]:
    """
    Create a sample that preserves network structure using advanced NetworkX sampling methods.

    Uses multiple sampling strategies for better network structure preservation.
    """
    if len(data) <= target_size:
        return data

    # Build user data map once
    user_data_map = {user["user"]: user for user in data}

    # Build directed graph with all connections (not just mutual)
    graph = nx.DiGraph()
    graph.add_nodes_from(user_data_map.keys())

    # Add all edges (following relationships)
    edges = []
    for user_data in data:
        username = user_data["user"]
        for following in user_data.get("following", []):
            if following in user_data_map:
                edges.append((username, following))

    graph.add_edges_from(edges)

    # Convert to undirected for component analysis
    G_undirected = graph.to_undirected()

    # Strategy 1: Sample from largest connected component first
    if G_undirected.number_of_nodes() > 0:
        connected_components = list(nx.connected_components(G_undirected))

        if connected_components:
            # Sort components by size (largest first)
            connected_components.sort(key=len, reverse=True)

            selected_users = set()

            # Strategy 2: Use degree-based sampling within components
            for component in connected_components:
                if len(selected_users) >= target_size:
                    break

                component_size = len(component)
                remaining_slots = target_size - len(selected_users)

                if component_size <= remaining_slots:
                    # Take entire component
                    selected_users.update(component)
                else:
                    # Sample from component using degree centrality
                    component_subgraph = G_undirected.subgraph(component)

                    # Calculate degree centrality for better sampling
                    centrality = nx.degree_centrality(component_subgraph)

                    # Create weighted sampling based on centrality
                    nodes = list(component)
                    weights = [centrality[node] for node in nodes]

                    # Normalize weights
                    total_weight = sum(weights)
                    if total_weight > 0:
                        weights = [w / total_weight for w in weights]

                        # Use numpy for weighted sampling
                        sample_indices = np.random.choice(
                            len(nodes),
                            size=min(remaining_slots, len(nodes)),
                            replace=False,
                            p=weights,
                        )
                        sampled_nodes = [nodes[i] for i in sample_indices]
                        selected_users.update(sampled_nodes)
                    else:
                        # Fallback to random sampling
                        sampled_nodes = random.sample(
                            nodes, min(remaining_slots, len(nodes))
                        )
                        selected_users.update(sampled_nodes)

            # Strategy 3: If we still need more users, add high-degree isolated nodes
            if len(selected_users) < target_size:
                remaining_users = [
                    u for u in user_data_map.keys() if u not in selected_users
                ]
                additional_needed = target_size - len(selected_users)

                if remaining_users and additional_needed > 0:
                    # Sort remaining users by total degree (in + out)
                    user_degrees = []
                    for user in remaining_users:
                        in_degree = graph.in_degree(user) if graph.has_node(user) else 0
                        out_degree = (
                            graph.out_degree(user) if graph.has_node(user) else 0
                        )
                        total_degree = in_degree + out_degree
                        user_degrees.append((user, total_degree))

                    # Sort by degree (highest first) and take top users
                    user_degrees.sort(key=lambda x: x[1], reverse=True)
                    additional_users = [
                        user for user, _ in user_degrees[:additional_needed]
                    ]
                    selected_users.update(additional_users)

            selected_users = list(selected_users)[:target_size]  # Ensure exact size
        else:
            # No connected components, use degree-based sampling
            if graph.number_of_nodes() > 0:
                # Calculate total degree for each node
                node_degrees = []
                for node in graph.nodes():
                    total_degree = graph.in_degree(node) + graph.out_degree(node)
                    node_degrees.append((node, total_degree))

                # Sort by degree and take top nodes
                node_degrees.sort(key=lambda x: x[1], reverse=True)
                selected_users = [node for node, _ in node_degrees[:target_size]]
            else:
                # Fallback to random sampling
                selected_users = random.sample(list(user_data_map.keys()), target_size)
    else:
        # No nodes, random sample
        selected_users = random.sample(list(user_data_map.keys()), target_size)

    # Return data for selected users
    return [user_data_map[username] for username in selected_users]


def main():
    import time

    start_time = time.time()

    parser = argparse.ArgumentParser(description="Generate anonymized test datasets")
    parser.add_argument(
        "--input",
        "-i",
        default="followers_following.json",
        help="Input followers_following.json file (default: followers_following.json)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="tests/test_data",
        help="Output directory for generated datasets (default: tests/test_data)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible results (default: 42)",
    )
    parser.add_argument(
        "--preserve-structure",
        action="store_true",
        help="Preserve network structure when sampling (slower but better)",
    )
    parser.add_argument(
        "--timing", action="store_true", help="Show detailed timing information"
    )

    args = parser.parse_args()

    # Set random seed for reproducibility
    random.seed(args.seed)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print(f"Generating anonymized datasets from {args.input}")
    print(f"Output directory: {output_dir}")
    print(f"Random seed: {args.seed}")

    # Load original data
    load_start = time.time()
    original_data = load_original_data(args.input)
    if not original_data:
        return 1
    load_time = time.time() - load_start

    if args.timing:
        print(f"Data loading time: {load_time:.2f}s")

    # Show original statistics
    stats_start = time.time()
    original_stats = analyze_network_structure(original_data)

    # Count unique usernames in original data
    original_usernames = set()
    for user_data in original_data:
        original_usernames.add(user_data["user"])
        original_usernames.update(user_data.get("followers", []))
        original_usernames.update(user_data.get("following", []))
    original_stats["unique_usernames"] = len(original_usernames)

    stats_time = time.time() - stats_start

    if args.timing:
        print(f"Statistics calculation time: {stats_time:.2f}s")

    print("\nOriginal dataset statistics:")
    for key, value in original_stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    total_users = len(original_data)

    # Calculate sizes: tiny=5%, small=15%, medium=33%, large=66%, full=100%
    tiny_size = max(1, int(total_users * 0.05))
    small_size = max(1, int(total_users * 0.15))
    medium_size = max(1, int(total_users * 0.33))
    large_size = max(1, int(total_users * 0.66))

    print("\nDataset sizes:")
    print(f"  Tiny (5%): {tiny_size} users")
    print(f"  Small (15%): {small_size} users")
    print(f"  Medium (33%): {medium_size} users")
    print(f"  Large (66%): {large_size} users")
    print(f"  Full (100%): {total_users} users")

    # Generate datasets
    generation_start = time.time()
    datasets = []

    # 1. Tiny dataset (5% of original)
    tiny_start = time.time()
    if args.preserve_structure:
        tiny_real = create_network_preserving_sample(original_data, tiny_size)
    else:
        tiny_real = original_data[:tiny_size]

    tiny_anonymized = create_anonymized_dataset(tiny_real)
    datasets.append(
        (tiny_anonymized, output_dir / "tiny_real.json", "Tiny Real Dataset (5%)")
    )
    tiny_time = time.time() - tiny_start

    # 2. Small dataset (15% of original)
    small_start = time.time()
    if args.preserve_structure:
        small_real = create_network_preserving_sample(original_data, small_size)
    else:
        small_real = original_data[:small_size]

    small_anonymized = create_anonymized_dataset(small_real)
    datasets.append(
        (small_anonymized, output_dir / "small_real.json", "Small Real Dataset (15%)")
    )
    small_time = time.time() - small_start

    # 3. Medium dataset (33% of original)
    medium_start = time.time()
    if args.preserve_structure:
        medium_real = create_network_preserving_sample(original_data, medium_size)
    else:
        medium_real = original_data[:medium_size]

    medium_anonymized = create_anonymized_dataset(medium_real)
    datasets.append(
        (
            medium_anonymized,
            output_dir / "medium_real.json",
            "Medium Real Dataset (33%)",
        )
    )
    medium_time = time.time() - medium_start

    # 4. Large dataset (66% of original)
    large_start = time.time()
    if args.preserve_structure:
        large_real = create_network_preserving_sample(original_data, large_size)
    else:
        large_real = original_data[:large_size]

    large_anonymized = create_anonymized_dataset(large_real)
    datasets.append(
        (large_anonymized, output_dir / "large_real.json", "Large Real Dataset (66%)")
    )
    large_time = time.time() - large_start

    # 5. Full dataset (100% - anonymized)
    full_start = time.time()
    full_anonymized = create_anonymized_dataset(original_data)
    datasets.append(
        (
            full_anonymized,
            output_dir / "full_anonymized.json",
            "Full Anonymized Dataset (100%)",
        )
    )
    full_time = time.time() - full_start

    generation_time = time.time() - generation_start

    if args.timing:
        print("\nDataset generation times:")
        print(f"  Tiny dataset: {tiny_time:.2f}s")
        print(f"  Small dataset: {small_time:.2f}s")
        print(f"  Medium dataset: {medium_time:.2f}s")
        print(f"  Large dataset: {large_time:.2f}s")
        print(f"  Full dataset: {full_time:.2f}s")
        print(f"  Total generation: {generation_time:.2f}s")

    # Save all datasets and collect detailed stats
    success_count = 0
    dataset_stats = {}

    for data, filepath, description in datasets:
        if save_dataset(data, str(filepath), description):
            success_count += 1
            # Collect detailed graph analysis for each dataset
            dataset_name = filepath.stem  # Get filename without extension

            # Count unique usernames in this dataset
            all_usernames = set()
            for user_data in data:
                all_usernames.add(user_data["user"])
                all_usernames.update(user_data.get("followers", []))
                all_usernames.update(user_data.get("following", []))

            dataset_stats[dataset_name] = {
                "basic_stats": analyze_network_structure(data),
                "graph_analysis": analyze_graph_structure(data),
                "unique_usernames": len(all_usernames),
            }

    print(f"\nSuccessfully generated {success_count}/{len(datasets)} datasets")

    # Create enhanced summary file
    summary = {
        "generation_info": {
            "source_file": args.input,
            "generation_date": str(Path().resolve()),
            "random_seed": args.seed,
            "preserve_structure": args.preserve_structure,
        },
        "datasets": {
            "tiny_real": {
                "file": "tiny_real.json",
                "description": f"Anonymized sample of {tiny_size} users (5% of original)",
                "users": len(tiny_anonymized),
                "percentage": 5,
                "stats": dataset_stats.get("tiny_real", {}),
            },
            "small_real": {
                "file": "small_real.json",
                "description": f"Anonymized sample of {small_size} users (15% of original)",
                "users": len(small_anonymized),
                "percentage": 15,
                "stats": dataset_stats.get("small_real", {}),
            },
            "medium_real": {
                "file": "medium_real.json",
                "description": f"Anonymized sample of {medium_size} users (33% of original)",
                "users": len(medium_anonymized),
                "percentage": 33,
                "stats": dataset_stats.get("medium_real", {}),
            },
            "large_real": {
                "file": "large_real.json",
                "description": f"Anonymized sample of {large_size} users (66% of original)",
                "users": len(large_anonymized),
                "percentage": 66,
                "stats": dataset_stats.get("large_real", {}),
            },
            "full_anonymized": {
                "file": "full_anonymized.json",
                "description": "Complete dataset with anonymized usernames (100%)",
                "users": len(full_anonymized),
                "percentage": 100,
                "stats": dataset_stats.get("full_anonymized", {}),
            },
        },
        "original_stats": original_stats,
        "original_graph_analysis": analyze_graph_structure(original_data),
    }

    summary_file = output_dir / "dataset_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nDataset summary saved to {summary_file}")

    # Verify uniqueness of all generated names
    print("\nUsername Uniqueness Verification:")
    print("=" * 40)

    for _dataset_name, dataset_info in summary["datasets"].items():
        filepath = output_dir / dataset_info["file"]
        try:
            with open(filepath, encoding="utf-8") as f:
                dataset_data = json.load(f)

            # Extract all usernames
            all_usernames = set()
            for user_data in dataset_data:
                all_usernames.add(user_data["user"])
                all_usernames.update(user_data.get("followers", []))
                all_usernames.update(user_data.get("following", []))

            # Verify all names are unique (set size equals total count)
            total_name_instances = 0
            for user_data in dataset_data:
                total_name_instances += 1  # user
                total_name_instances += len(user_data.get("followers", []))
                total_name_instances += len(user_data.get("following", []))

            print(f"{dataset_info['file']}: All usernames unique ✓")

            # Verify hash-based format
            hash_names = [name for name in all_usernames if len(name.split("_")) == 3]
            if len(hash_names) == len(all_usernames):
                print("  Hash-based format verified ✓")
            else:
                print("  Warning: Some names don't follow hash format")

        except Exception as e:
            print(f"{dataset_info['file']}: Error verifying uniqueness - {e}")

    # Display detailed graph structure information
    print("\nDetailed Graph Structure Analysis:")
    print("=" * 50)

    for _dataset_name, dataset_info in summary["datasets"].items():
        stats = dataset_info.get("stats", {})
        graph_analysis = stats.get("graph_analysis", {})

        if graph_analysis:
            print(f"\n{dataset_info['description']}:")

            # Graph structure
            graph_struct = graph_analysis.get("graph_structure", {})
            print("  Graph Structure:")
            print(f"    Nodes: {graph_struct.get('nodes', 0)}")
            print(f"    Directed Edges: {graph_struct.get('directed_edges', 0)}")
            print(
                f"    Mutual Connections: {graph_struct.get('mutual_connections', 0)}"
            )
            print(f"    Density: {graph_struct.get('density', 0):.3f}")
            print(f"    Reciprocity: {graph_struct.get('reciprocity', 0):.3f}")

            # Connectivity
            connectivity = graph_analysis.get("connectivity", {})
            print("  Connectivity:")
            print(
                f"    Connected Components: {connectivity.get('connected_components', 0)}"
            )
            print(
                f"    Largest Component: {connectivity.get('largest_component_size', 0)} nodes ({connectivity.get('largest_component_percentage', 0):.1f}%)"
            )

            # Degree distribution
            degrees = graph_analysis.get("degree_distribution", {})
            print("  Degree Distribution:")
            print(f"    Avg In/Out Degree: {degrees.get('avg_in_degree', 0):.1f}")
            print(f"    Max In/Out Degree: {degrees.get('max_in_degree', 0)}")
            print(f"    Min In/Out Degree: {degrees.get('min_in_degree', 0)}")

    print("\nUsage recommendations:")
    print("  - tiny_real.json: Quick unit tests (5% of data, very fast)")
    print("  - small_real.json: Unit and integration tests (15% of data, fast)")
    print("  - medium_real.json: Integration tests (33% of data, moderate load)")
    print("  - large_real.json: Performance tests (66% of data, realistic load)")
    print(
        "  - full_anonymized.json: Full system testing (100% of data, complete dataset)"
    )

    total_time = time.time() - start_time
    print(f"\nTotal execution time: {total_time:.2f}s")

    return 0


if __name__ == "__main__":
    exit(main())
