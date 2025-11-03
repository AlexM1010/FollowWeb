"""
Network analysis module for FollowWeb social network analysis.

This module contains the NetworkAnalyzer class for coordinating network analysis
operations including community detection and centrality calculations.
"""

# Standard library imports
import logging
import sys
import time
from typing import Any, Dict, Optional

# Third-party imports
import networkx as nx
from networkx.algorithms import community

# Conditional nx_parallel import (Python 3.11+ only)
try:
    if sys.version_info >= (3, 11):
        import nx_parallel  # noqa: F401
except ImportError:
    pass  # nx_parallel not available, use standard NetworkX

# Local imports
from ..core.exceptions import DataProcessingError
from ..data.cache import get_cache_manager, get_cached_undirected_graph
from ..utils.math import format_time_duration
from ..utils.parallel import (
    get_analysis_parallel_config,
    get_nx_parallel_status_message,
    log_parallel_usage,
)


class NetworkAnalyzer:
    """
    Class containing network analysis algorithms including community detection and centrality calculations.

    Supports execution of analysis components with performance optimization
    and timing feedback based on configuration settings.
    """

    def __init__(self, mode_manager=None, stages_controller=None) -> None:
        """
        Initialize the NetworkAnalyzer.

        Args:
            mode_manager: Optional AnalysisModeManager for performance optimization
            stages_controller: Optional PipelineStagesController for component control

        The NetworkAnalyzer performs community detection, centrality calculations,
        and other network structure analysis operations on social network graphs.
        """
        self.logger = logging.getLogger(__name__)
        self.mode_manager = mode_manager
        self.stages_controller = stages_controller

        # Use centralized cache manager instead of local caches
        self.cache_manager = get_cache_manager()

        # Log parallel processing status
        nx_status = get_nx_parallel_status_message()
        self.logger.debug(f"NetworkAnalyzer initialized - {nx_status}")

    def clear_caches(self) -> None:
        """
        Clear all internal caches to free memory.

        This method should be called when processing multiple graphs in sequence
        to prevent memory accumulation from cached results.
        """
        # Use centralized cache clearing
        self.cache_manager.clear_all_caches()
        self.logger.debug("NetworkAnalyzer caches cleared")

    def analyze_network(self, graph: nx.Graph) -> nx.Graph:
        """
        Perform network analysis with selective algorithm execution.

        Executes community detection and centrality calculations based on configuration
        settings with performance optimization and timing feedback. Components can be
        independently enabled/disabled through the stages controller.

        Args:
            graph: Input graph to analyze (directed or undirected NetworkX graph)

        Returns:
            nx.Graph: Graph with added node attributes based on enabled components

        Note:
            For graphs with fewer than 2 nodes, analysis is skipped and the original
            graph is returned unchanged. Uses sampling for large graphs based on mode.
        """
        MIN_NODES_FOR_ANALYSIS = 2

        if graph.number_of_nodes() < MIN_NODES_FOR_ANALYSIS:
            self.logger.warning(
                f"Graph has fewer than {MIN_NODES_FOR_ANALYSIS} nodes. Skipping analysis."
            )
            return graph

        graph_size = graph.number_of_nodes()

        # Validate performance constraints
        self._validate_performance_constraints(graph_size)

        # Determine which components to execute
        execute_community = self._should_execute_component("community_detection")
        execute_centrality = self._should_execute_component("centrality_analysis")

        if not execute_community and not execute_centrality:
            self.logger.info(
                "No analysis components enabled. Returning original graph."
            )
            return graph

        # Get performance configurations
        community_config = self._get_component_config("community_detection", graph_size)
        centrality_config = self._get_component_config(
            "centrality_analysis", graph_size
        )

        # mode_info = (
        #     f" ({centrality_config.get('mode', 'unknown')} mode)"
        #     if self.mode_manager
        #     else ""
        # )

        # Log parallel processing configuration once for the entire network analysis
        self.logger.info("")  # Add spacing before parallel notification
        parallel_config = get_analysis_parallel_config(graph_size)
        log_parallel_usage(parallel_config, self.logger)

        # Execute community detection if enabled
        if execute_community:
            self._log_component_start("community_detection")
            start_time = time.time()

            try:
                self._perform_community_detection(graph, community_config)
                duration = time.time() - start_time
                self._log_component_completion("community_detection", True, duration)
            except Exception as e:
                duration = time.time() - start_time
                self.logger.error(f"Community detection failed: {e}")
                self._log_component_completion("community_detection", False, duration)
                raise DataProcessingError(f"Community detection failed: {e}") from e
        else:
            self._log_component_skip("community_detection")
            # Set default community values when skipped
            nx.set_node_attributes(graph, 0, "community")

        # Execute centrality analysis if enabled
        if execute_centrality:
            self._log_component_start("centrality_analysis")
            centrality_start_time = time.time()

            try:
                # Import centrality functions
                from .centrality import (
                    calculate_betweenness_centrality,
                    calculate_eigenvector_centrality,
                    display_centrality_results,
                    set_default_centrality_values,
                )

                # Degree centrality (always calculated when centrality is enabled)
                degree_dict = dict(graph.degree())
                nx.set_node_attributes(graph, degree_dict, "degree")

                # Betweenness centrality
                betweenness_dict = calculate_betweenness_centrality(
                    graph, centrality_config, self.logger
                )
                nx.set_node_attributes(graph, betweenness_dict, "betweenness")

                # Eigenvector centrality (optional)
                if not centrality_config.get("skip_eigenvector", False):
                    eigenvector_dict = calculate_eigenvector_centrality(
                        graph, centrality_config, self.cache_manager, self.logger
                    )
                    nx.set_node_attributes(graph, eigenvector_dict, "eigenvector")
                else:
                    self.logger.info(
                        "Skipping eigenvector centrality calculation (optimization)"
                    )
                    eigenvector_dict = dict.fromkeys(graph.nodes(), 0)
                    nx.set_node_attributes(graph, eigenvector_dict, "eigenvector")

                centrality_duration = time.time() - centrality_start_time
                self._log_component_completion(
                    "centrality_analysis", True, centrality_duration
                )

                # Display results
                display_centrality_results(
                    degree_dict,
                    betweenness_dict,
                    eigenvector_dict,
                    centrality_config,
                    self.logger,
                )

            except Exception as e:
                centrality_duration = time.time() - centrality_start_time
                self.logger.error(f"Centrality analysis failed: {e}")
                self._log_component_completion(
                    "centrality_analysis", False, centrality_duration
                )
                raise DataProcessingError(f"Centrality analysis failed: {e}") from e
        else:
            self._log_component_skip("centrality_analysis")
            # Set default centrality values when skipped
            from .centrality import set_default_centrality_values

            set_default_centrality_values(graph)

        return graph

    def _should_execute_component(self, component_name: str) -> bool:
        """Check if a component should be executed based on configuration."""
        if self.stages_controller:
            return self.stages_controller.should_execute_analysis_component(
                component_name
            )

        # Default behavior when no stages controller is provided
        return True

    def _get_component_config(
        self, component_name: str, graph_size: int
    ) -> Dict[str, Any]:
        """Get performance configuration for a component."""
        if self.mode_manager:
            return self.mode_manager.get_performance_config_for_component(
                component_name, graph_size
            )

        # Fallback configuration
        if component_name == "community_detection":
            return {"resolution": 1.0, "use_sampling": False, "mode": "full"}
        elif component_name == "centrality_analysis":
            return {
                "sample_size": graph_size,
                "skip_eigenvector": False,
                "use_approximate_betweenness": graph_size > 5000,
                "use_sampling": False,
                "mode": "full",
            }
        else:
            return {"mode": "full"}

    def _validate_performance_constraints(self, graph_size: int) -> None:
        """Validate performance constraints and provide warnings for large graphs."""
        if self.mode_manager:
            mode = self.mode_manager.config.analysis_mode.mode
            sampling_threshold = (
                self.mode_manager.config.analysis_mode.sampling_threshold
            )

            # Log large graph detection and mode optimization in one place
            if graph_size > sampling_threshold:
                self.logger.info(
                    f"Large graph detected ({graph_size:,} nodes > {sampling_threshold:,} threshold)"
                )
                self.logger.info(
                    f"Using {mode.value} mode optimizations for performance"
                )

                # Log sampling configuration details once here
                sampling_params = self.mode_manager.get_sampling_parameters(
                    graph_size, mode
                )
                if sampling_params.get("use_sampling", False):
                    centrality_sample = sampling_params.get(
                        "centrality_sample_size", graph_size
                    )
                    path_sample = sampling_params.get("path_sample_size", graph_size)
                    self.logger.info(
                        f"  - Centrality sample size: {centrality_sample:,} nodes"
                    )
                    self.logger.info(
                        f"  - Path analysis sample size: {path_sample:,} nodes"
                    )

            # Warn about extremely large graphs
            if graph_size > 50000:
                self.logger.warning(
                    f"Very large graph ({graph_size:,} nodes). Analysis may take significant time."
                )
                if mode.value != "fast":
                    self.logger.warning(
                        "Consider using FAST mode for better performance on large graphs."
                    )
        else:
            # Basic validation without mode manager
            if graph_size > 10000:
                self.logger.warning(
                    f"Large graph ({graph_size:,} nodes). Analysis may take significant time."
                )

    def _perform_community_detection(
        self, graph: nx.Graph, config: Dict[str, Any]
    ) -> None:
        """Perform community detection with parallel processing optimization."""
        resolution = config.get("resolution", 1.0)

        # Use cached undirected graph conversion
        graph_undirected = get_cached_undirected_graph(graph)

        if graph_undirected.number_of_edges() == 0:
            self.logger.warning("Graph has no edges. Skipping community detection.")
            communities = []
        else:
            graph_size = graph_undirected.number_of_nodes()

            # Get parallel configuration for community detection (logging done at analysis level)
            get_analysis_parallel_config(graph_size)

            self.logger.debug(
                f"Running community detection with resolution={resolution} on {graph_size} nodes"
            )

            # OPTIMIZATION: Use faster algorithm for very large graphs
            try:
                if graph_size > 10000:
                    # For very large graphs, use a single pass with higher resolution
                    # to get reasonable communities faster
                    adjusted_resolution = resolution * 1.5
                    communities = community.louvain_communities(
                        graph_undirected, resolution=adjusted_resolution, seed=123
                    )
                else:
                    # Standard algorithm for smaller graphs
                    communities = community.louvain_communities(
                        graph_undirected, resolution=resolution, seed=123
                    )
            except Exception as e:
                self.logger.warning(f"Community detection failed with error: {e}")
                # Fallback to empty communities
                communities = []

        partition = {node: i for i, comm in enumerate(communities) for node in comm}

        nx.set_node_attributes(graph, partition, "community")

        self.logger.debug(
            f"Community detection completed: {len(communities)} communities found"
        )

    def _log_component_start(self, component_name: str) -> None:
        """Log the start of an analysis component."""
        if self.stages_controller:
            self.stages_controller.log_analysis_component_start(component_name)
        else:
            self.logger.debug(f"Starting {component_name}")

    def _log_component_completion(
        self, component_name: str, success: bool, duration: Optional[float] = None
    ) -> None:
        """Log the completion of an analysis component."""
        if self.stages_controller:
            self.stages_controller.log_analysis_component_completion(
                component_name, success
            )

        if success and duration is not None:
            self.logger.debug(
                f"{component_name} completed in {format_time_duration(duration)}"
            )
        elif not success:
            self.logger.error(f"{component_name} failed")

    def _log_component_skip(
        self, component_name: str, reason: Optional[str] = None
    ) -> None:
        """Log that an analysis component was skipped."""
        if self.stages_controller:
            self.stages_controller.log_analysis_component_skip(component_name, reason)
        else:
            skip_msg = f"Skipping {component_name}"
            if reason:
                skip_msg += f" - {reason}"
            self.logger.debug(skip_msg)
