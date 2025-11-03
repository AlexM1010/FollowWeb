"""
Centrality calculation algorithms for network analysis.

This module provides functions for calculating various centrality metrics
including degree, betweenness, and eigenvector centrality.
"""

# Standard library imports
import logging
import math
import sys
from typing import Any, Dict

# Third-party imports
import networkx as nx
import pandas as pd

# Conditional nx_parallel import (Python 3.11+ only)
try:
    if sys.version_info >= (3, 11):
        import nx_parallel  # noqa: F401
except ImportError:
    pass  # nx_parallel not available, use standard NetworkX

# Local imports
from ..utils import ProgressTracker
from ..utils.parallel import get_analysis_parallel_config


def calculate_betweenness_centrality(
    graph: nx.Graph, config: Dict[str, Any], logger: logging.Logger
) -> Dict[str, float]:
    """Calculate betweenness centrality with performance optimization."""
    graph_size = graph.number_of_nodes()

    # Get parallel configuration for centrality calculation (logging done at analysis level)
    parallel_config = get_analysis_parallel_config(graph_size)

    # Use a simulated progress tracker that shows animation during computation
    import threading
    import time as time_module

    # Create a progress tracker with multiple steps to show animation
    with ProgressTracker(
        total=100,  # Use 100 steps for smooth animation
        title=f"Calculating betweenness centrality on {graph_size} nodes",
        logger=logger,
    ) as tracker:
        # Start a background thread to animate progress
        stop_animation = threading.Event()

        def animate_progress() -> None:
            step = 0
            while not stop_animation.is_set() and step < 99:
                step += 1
                tracker.update(step)
                time_module.sleep(0.2)  # Update every 200ms

        animation_thread = threading.Thread(target=animate_progress, daemon=True)
        animation_thread.start()

        try:
            if config.get("use_approximate_betweenness", False):
                # OPTIMIZATION: Use more efficient sampling strategy
                k_sample = min(config["sample_size"], int(math.sqrt(graph_size)))
                k_sample = max(k_sample, 10)  # Minimum sample size

                # OPTIMIZATION: For very large graphs, use even more aggressive sampling
                if graph_size > 10000:
                    k_sample = min(k_sample, max(50, graph_size // 200))

                logger.debug(
                    f"Using approximate betweenness centrality with k={k_sample} samples"
                )

                # Try parallel backend first, fall back to standard if it fails
                if parallel_config.nx_parallel_enabled:
                    try:
                        betweenness_dict = nx.betweenness_centrality(
                            graph, k=k_sample, seed=123
                        )
                    except Exception as parallel_error:
                        logger.debug(
                            f"Parallel betweenness failed ({parallel_error}), using standard algorithm"
                        )
                        betweenness_dict = nx.betweenness_centrality(
                            graph, k=k_sample, seed=123
                        )
                else:
                    betweenness_dict = nx.betweenness_centrality(
                        graph, k=k_sample, seed=123
                    )
            else:
                # Full calculation for small graphs or full mode
                logger.debug("Using exact betweenness centrality calculation")

                # Try parallel backend first, fall back to standard if it fails
                if parallel_config.nx_parallel_enabled:
                    try:
                        betweenness_dict = nx.betweenness_centrality(graph)
                    except Exception as parallel_error:
                        logger.debug(
                            f"Parallel betweenness failed ({parallel_error}), using standard algorithm"
                        )
                        betweenness_dict = nx.betweenness_centrality(graph)
                else:
                    betweenness_dict = nx.betweenness_centrality(graph)

        except Exception as e:
            logger.warning(
                f"Could not calculate betweenness centrality ({e}). Defaulting to 0."
            )
            betweenness_dict = dict.fromkeys(graph.nodes(), 0)
        finally:
            # Stop animation and complete progress
            stop_animation.set()
            animation_thread.join(timeout=0.5)  # Wait briefly for thread to finish
            tracker.update(100)  # Complete the progress

    return betweenness_dict


def calculate_eigenvector_centrality(
    graph: nx.Graph, config: Dict[str, Any], cache_manager, logger: logging.Logger
) -> Dict[str, float]:
    """Calculate eigenvector centrality with centralized caching and optimization."""
    # Create params for caching
    params = {"max_iter": config.get("max_iter", 1000)}

    # Check centralized cache first
    cached_results = cache_manager.get_cached_centrality_results(
        graph, "eigenvector", params
    )
    if cached_results is not None:
        logger.debug("Using cached eigenvector centrality results")
        return cached_results

    # Eigenvector centrality calculation (parallel config already logged at analysis level)
    import threading
    import time as time_module

    # Use a simulated progress tracker that shows animation during computation
    with ProgressTracker(
        total=100,  # Use 100 steps for smooth animation
        title="Calculating eigenvector centrality",
        logger=logger,
    ) as tracker:
        # Start a background thread to animate progress
        stop_animation = threading.Event()

        def animate_progress() -> None:
            step = 0
            while not stop_animation.is_set() and step < 99:
                step += 1
                tracker.update(step)
                time_module.sleep(0.1)  # Update every 100ms (faster for eigenvector)

        animation_thread = threading.Thread(target=animate_progress, daemon=True)
        animation_thread.start()

        try:
            # OPTIMIZATION: Adaptive iteration count based on graph size
            graph_size = graph.number_of_nodes()
            if graph_size > 5000:
                max_iter = 500  # Reduced iterations for large graphs
            elif graph_size > 1000:
                max_iter = 750  # Moderate iterations for medium graphs
            else:
                max_iter = 1000  # Full iterations for small graphs

            # OPTIMIZATION: Use degree centrality as better starting point
            degree_dict = dict(graph.degree())
            max_degree = max(degree_dict.values()) if degree_dict else 1
            nstart = {n: degree_dict.get(n, 0) / max_degree for n in graph.nodes()}

            eigenvector_dict = nx.eigenvector_centrality(
                graph, max_iter=max_iter, nstart=nstart, tol=1e-4
            )
        except Exception as e:
            logger.warning(
                f"Could not calculate eigenvector centrality ({e}). Defaulting to 0."
            )
            eigenvector_dict = dict.fromkeys(graph.nodes(), 0)
        finally:
            # Stop animation and complete progress
            stop_animation.set()
            animation_thread.join(timeout=0.5)  # Wait briefly for thread to finish

            # Cache the results using centralized cache
            cache_manager.cache_centrality_results(
                graph, "eigenvector", eigenvector_dict, params
            )

            tracker.update(100)  # Complete the progress

    return eigenvector_dict


def set_default_centrality_values(graph: nx.Graph) -> None:
    """Set default centrality values when centrality analysis is skipped."""
    default_values = dict.fromkeys(graph.nodes(), 0)
    nx.set_node_attributes(
        graph, dict(graph.degree()), "degree"
    )  # Use actual degree even when skipped
    nx.set_node_attributes(graph, default_values, "betweenness")
    nx.set_node_attributes(graph, default_values, "eigenvector")


def display_centrality_results(
    degree_dict: Dict[str, int],
    betweenness_dict: Dict[str, float],
    eigenvector_dict: Dict[str, float],
    config: Dict[str, Any],
    logger: logging.Logger,
) -> None:
    """Display centrality analysis results."""
    logger.info("\n---- Top 10 Nodes by Centrality ----")
    df = pd.DataFrame(
        {
            "degree": degree_dict,
            "betweenness": betweenness_dict,
            "eigenvector": eigenvector_dict,
        }
    )

    if not df.empty:
        logger.info("# By Degree (Connections):")
        logger.info(f"{df.sort_values('degree', ascending=False).head(10)}")
        logger.info("# By Betweenness (Bridge-builder):")
        logger.info(f"{df.sort_values('betweenness', ascending=False).head(10)}")

        # Only show eigenvector results if they were calculated
        if not config.get("skip_eigenvector", False):
            logger.info("# By Eigenvector (Influence):")
            logger.info(f"{df.sort_values('eigenvector', ascending=False).head(10)}")
        else:
            logger.info("# Eigenvector centrality: Skipped (optimization)")
    else:
        logger.info("No nodes remaining to analyze.")
