"""
Connectivity analysis module for network connectivity metrics.

This module provides functions for calculating connectivity metrics and validating
graph connectivity, including connected components analysis, clustering coefficients,
and graph density measurements.
"""

# Standard library imports
import logging
from typing import Any, Optional

# Third-party imports
import networkx as nx

# Local imports
from ..data.cache import get_cached_undirected_graph
from ..utils.progress import ProgressTracker


def calculate_connectivity_metrics(
    graph: nx.Graph, logger: Optional[logging.Logger] = None
) -> dict[str, Any]:
    """
    Calculate complete connectivity metrics for a graph.

    This function analyzes the connectivity structure of a graph by calculating:
    - Number of connected components
    - Size of the largest connected component
    - Percentage of nodes in the largest component
    - Average clustering coefficient (with sampling for large graphs)
    - Graph density

    Args:
        graph: NetworkX graph (directed or undirected) to analyze
        logger: Optional logger instance for progress tracking

    Returns:
        Dictionary containing connectivity metrics:
            - num_components (int): Number of connected components
            - largest_component_size (int): Number of nodes in largest component
            - largest_component_pct (float): Percentage of nodes in largest component
            - avg_clustering (float): Average clustering coefficient
            - density (float): Graph density (0 to 1)
            - is_connected (bool): Whether graph is fully connected

    Example:
        >>> metrics = calculate_connectivity_metrics(graph, logger)
        >>> print(f"Components: {metrics['num_components']}")
        >>> print(f"Largest component: {metrics['largest_component_pct']:.1f}%")
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Convert to undirected graph using cache for efficiency
    if graph.is_directed():
        graph_undirected = get_cached_undirected_graph(graph)
    else:
        graph_undirected = graph

    graph_size = graph_undirected.number_of_nodes()

    # Handle empty graph
    if graph_size == 0:
        logger.warning("Empty graph provided for connectivity analysis")
        return {
            "num_components": 0,
            "largest_component_size": 0,
            "largest_component_pct": 0.0,
            "avg_clustering": 0.0,
            "density": 0.0,
            "is_connected": False,
        }

    logger.debug(
        f"Calculating connectivity metrics for graph with {graph_size:,} nodes"
    )

    # Calculate connected components
    components = list(nx.connected_components(graph_undirected))
    num_components = len(components)

    # Find largest component
    largest_component = max(components, key=len)
    largest_component_size = len(largest_component)
    largest_component_pct = (largest_component_size / graph_size) * 100

    # Calculate graph density
    density = nx.density(graph_undirected)

    # Calculate average clustering coefficient
    # Use sampling for large graphs (>10000 nodes) to improve performance
    if graph_size > 10000:
        logger.debug(
            f"Using sampling for clustering coefficient calculation (graph size: {graph_size:,})"
        )

        # Sample approximately 10% of nodes, minimum 1000, maximum 5000
        sample_size = min(5000, max(1000, graph_size // 10))

        with ProgressTracker(
            total=sample_size,
            title=f"Calculating clustering coefficient (sampling {sample_size:,} nodes)",
            logger=logger,
        ) as tracker:
            # Use NetworkX's built-in sampling for clustering
            # Note: nx.average_clustering with nodes parameter samples specific nodes
            import random

            sample_nodes = random.sample(list(graph_undirected.nodes()), sample_size)

            # Calculate clustering for sampled nodes
            clustering_values = []
            for i, node in enumerate(sample_nodes):
                clustering_values.append(nx.clustering(graph_undirected, node))
                if (i + 1) % max(1, sample_size // 10) == 0:
                    tracker.update(i + 1)

            tracker.update(sample_size)
            avg_clustering = sum(clustering_values) / len(clustering_values)  # type: ignore[arg-type]

    else:
        # Full calculation for smaller graphs
        logger.debug("Calculating exact clustering coefficient")
        avg_clustering = nx.average_clustering(graph_undirected)

    # Determine if graph is fully connected
    is_connected = num_components == 1

    metrics = {
        "num_components": num_components,
        "largest_component_size": largest_component_size,
        "largest_component_pct": largest_component_pct,
        "avg_clustering": avg_clustering,
        "density": density,
        "is_connected": is_connected,
    }

    logger.debug(
        f"Connectivity metrics: {num_components} components, "
        f"{largest_component_pct:.1f}% in largest, "
        f"density={density:.4f}, clustering={avg_clustering:.4f}"
    )

    return metrics


def validate_connectivity(
    graph: nx.Graph, logger: Optional[logging.Logger] = None
) -> dict[str, Any]:
    """
    Validate graph connectivity and identify disconnected components.

    This function checks if a graph is fully connected and provides detailed
    information about disconnected components and isolated nodes.

    Args:
        graph: NetworkX graph (directed or undirected) to validate
        logger: Optional logger instance for logging warnings

    Returns:
        Dictionary containing validation results:
            - is_connected (bool): Whether graph is fully connected
            - num_components (int): Number of connected components
            - component_sizes (list[int]): Sizes of all components (sorted descending)
            - isolated_nodes (list): List of isolated nodes (degree = 0)
            - num_isolated_nodes (int): Count of isolated nodes
            - largest_component_pct (float): Percentage of nodes in largest component

    Example:
        >>> validation = validate_connectivity(graph, logger)
        >>> if not validation['is_connected']:
        ...     print(f"Warning: {validation['num_components']} disconnected components")
        ...     print(f"Isolated nodes: {validation['num_isolated_nodes']}")
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Convert to undirected graph using cache for efficiency
    if graph.is_directed():
        graph_undirected = get_cached_undirected_graph(graph)
    else:
        graph_undirected = graph

    graph_size = graph_undirected.number_of_nodes()

    # Handle empty graph
    if graph_size == 0:
        logger.warning("Empty graph provided for connectivity validation")
        return {
            "is_connected": False,
            "num_components": 0,
            "component_sizes": [],
            "isolated_nodes": [],
            "num_isolated_nodes": 0,
            "largest_component_pct": 0.0,
        }

    # Calculate connected components
    components = list(nx.connected_components(graph_undirected))
    num_components = len(components)

    # Sort components by size (descending)
    component_sizes = sorted([len(comp) for comp in components], reverse=True)

    # Calculate largest component percentage
    largest_component_pct = (
        (component_sizes[0] / graph_size) * 100 if component_sizes else 0.0
    )

    # Find isolated nodes (degree = 0)
    isolated_nodes = [node for node, degree in graph_undirected.degree() if degree == 0]  # type: ignore[operator]
    num_isolated_nodes = len(isolated_nodes)

    # Determine if graph is fully connected
    is_connected = num_components == 1

    validation_results = {
        "is_connected": is_connected,
        "num_components": num_components,
        "component_sizes": component_sizes,
        "isolated_nodes": isolated_nodes,
        "num_isolated_nodes": num_isolated_nodes,
        "largest_component_pct": largest_component_pct,
    }

    # Log validation results
    if is_connected:
        logger.debug("Graph is fully connected")
    else:
        logger.warning(
            f"Graph is not fully connected: {num_components} components found"
        )
        logger.warning(
            f"Largest component contains {largest_component_pct:.1f}% of nodes"
        )

        if num_isolated_nodes > 0:
            logger.warning(f"Found {num_isolated_nodes} isolated nodes (degree = 0)")

        # Log component size distribution
        if num_components <= 10:
            logger.debug(f"Component sizes: {component_sizes}")
        else:
            logger.debug(
                f"Component sizes (top 10): {component_sizes[:10]} "
                f"(+{num_components - 10} more)"
            )

    return validation_results


__all__ = [
    "calculate_connectivity_metrics",
    "validate_connectivity",
]
