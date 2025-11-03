"""
Main controller and pipeline orchestration module for FollowWeb network analysis.

This module provides the primary entry point and orchestrates the complete analysis workflow
using imported modules with error handling and logging throughout the pipeline.
"""

# Standard library imports
import argparse
import json
import logging
import os
import sys
import time
import traceback
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Union

# Third-party imports
import networkx as nx

# Local imports
from .analysis.fame import FameAnalyzer
from .analysis.network import NetworkAnalyzer
from .analysis.paths import PathAnalyzer
from .core.config import (
    FollowWebConfig,
    PipelineStagesController,
    get_analysis_mode_manager,
    get_configuration_manager,
    load_config_from_dict,
)
from .data.cache import get_cache_manager
from .data.loaders import GraphLoader
from .output.formatters import EmojiFormatter
from .output.managers import OutputManager
from .utils.math import format_time_duration
from .utils.parallel import get_analysis_parallel_config, get_nx_parallel_status_message


class PipelineOrchestrator:
    """
    Class managing the analysis workflow with phase-based execution and error handling.

    This orchestrator manages the three main phases:
    1. Strategy Phase: Graph loading, filtering, and pruning
    2. Analysis Phase: Network analysis (communities, centrality, paths)
    3. Visualization Phase: HTML and PNG generation
    """

    def __init__(self, config: FollowWebConfig) -> None:
        """
        Initialize pipeline with validated configuration.

        Args:
            config: FollowWebConfig instance containing analysis parameters including
                   input/output paths, pipeline strategy, analysis settings, and
                   visualization configuration

        Raises:
            ValueError: If configuration validation fails or required keys are missing
        """
        # Configuration is already validated by the configuration manager
        self.config = config

        # Initialize pipeline stages controller
        self.stages_controller = PipelineStagesController(config)

        # Initialize analysis mode manager
        self.mode_manager = get_analysis_mode_manager(config)

        # Validate stage dependencies before proceeding
        dependency_errors = self.stages_controller.validate_stage_dependencies()
        if dependency_errors:
            error_msg = "Pipeline stage dependency validation failed:\n" + "\n".join(
                f"  - {error}" for error in dependency_errors
            )
            raise ValueError(error_msg)

        # Initialize components with mode manager and stages controller integration
        self.graph_loader = GraphLoader()
        self.network_analyzer = NetworkAnalyzer(
            mode_manager=self.mode_manager, stages_controller=self.stages_controller
        )
        self.path_analyzer = PathAnalyzer(
            mode_manager=self.mode_manager, stages_controller=self.stages_controller
        )
        self.fame_analyzer = FameAnalyzer()

        # Convert config to dictionary format for output manager
        config_dict = asdict(config)

        # Initialize unified output manager for centralized output control
        self.output_manager = OutputManager(config_dict)

        # Initialize unified logger for pipeline execution
        emoji_level = OutputManager.get_emoji_config_from_dict(config_dict)
        self.output_manager.initialize_unified_logger(
            config.output_file_prefix,
            config.strategy,
            config.k_values.strategy_k_values.get(
                config.strategy, config.k_values.default_k_value
            ),
            emoji_level,
        )
        self.logger = self.output_manager.unified_logger

        # Pipeline state
        self.pipeline_start_time = None
        self.phase_times = {}

        # Get cache manager for performance optimization
        self.cache_manager = get_cache_manager()

    def _log_timer(self, message: str, section: Optional[str] = None) -> None:
        """Log timing information with standardized format."""
        # Only log timing information if timing logs are enabled
        if self.config.output_control.enable_timing_logs:
            self.logger.log_timer(message, section)

    def _log_success(self, message: str, section: Optional[str] = None) -> None:
        """Log success information with standardized format."""
        self.logger.log_success(message, section)

    def _log_progress(self, message: str, section: Optional[str] = None) -> None:
        """Log progress information with standardized format."""
        self.logger.log_progress(message, section)

    def _log_completion(
        self, message: str, section: Optional[Optional[str]] = None
    ) -> None:
        """Log completion information with standardized format."""
        self.logger.log_completion(message, section)

    def execute_pipeline(self) -> bool:
        """
        Execute analysis pipeline with error handling.

        Returns:
            bool: True if pipeline completed successfully, False otherwise
        """
        self.pipeline_start_time = time.perf_counter()
        phase_results = {}

        try:
            # Start pipeline section
            self.logger.start_section("FOLLOWWEB NETWORK ANALYSIS PIPELINE")
            pipeline_start_msg = EmojiFormatter.format(
                "rocket", "FOLLOWWEB NETWORK ANALYSIS PIPELINE"
            )
            self.logger.info(pipeline_start_msg)

            # Log pipeline configuration
            self._log_pipeline_configuration()

            # Log parallel processing capabilities
            self._log_parallel_processing_status()

            # Phase 1: Strategy execution (loading, filtering, pruning)
            if self.stages_controller.should_execute_stage("strategy"):
                graph = self._execute_strategy_phase()
                if graph is None or graph.number_of_nodes() == 0:
                    self.logger.error(
                        "Strategy phase failed or resulted in empty graph"
                    )
                    phase_results["strategy"] = False
                    return False
                else:
                    phase_results["strategy"] = True
            else:
                self.stages_controller.log_stage_skip(
                    "strategy", "Strategy stage cannot be disabled"
                )
                self.logger.error("Strategy stage is required for pipeline execution")
                phase_results["strategy"] = False
                return False

            # Phase 2: Analysis execution (communities, centrality, paths)
            if self.stages_controller.should_execute_stage("analysis"):
                analyzed_graph = self._execute_analysis_phase(graph)
                if analyzed_graph is None:
                    self.logger.error("Analysis phase failed")
                    phase_results["analysis"] = False
                    return False
                else:
                    phase_results["analysis"] = True
            else:
                self.stages_controller.log_stage_skip(
                    "analysis", "Analysis disabled in configuration"
                )
                analyzed_graph = graph  # Use original graph for visualization
                phase_results["analysis"] = "skipped"

            # Phase 3: Visualization execution (HTML and PNG generation)
            if self.stages_controller.should_execute_stage("visualization"):
                visualization_success = self._execute_visualization_phase(
                    analyzed_graph
                )
                if not visualization_success:
                    self.logger.error("Visualization phase failed")
                    phase_results["visualization"] = False
                    return False
                else:
                    phase_results["visualization"] = True
            else:
                self.stages_controller.log_stage_skip(
                    "visualization", "Visualization disabled in configuration"
                )
                phase_results["visualization"] = "skipped"

            # Validate overall pipeline success
            enabled_phases = [
                phase
                for phase in ["strategy", "analysis", "visualization"]
                if self.stages_controller.should_execute_stage(phase)
            ]
            failed_phases = [
                phase for phase in enabled_phases if phase_results.get(phase) is False
            ]
            successful_phases = [
                phase for phase in enabled_phases if phase_results.get(phase)
            ]

            # Pipeline succeeds only if ALL enabled phases succeeded
            pipeline_success = len(failed_phases) == 0 and len(successful_phases) > 0

            if pipeline_success:
                # Pipeline completion
                self._report_pipeline_completion()

                # Clear caches after successful completion to free memory
                cache_stats = self.cache_manager.get_cache_stats()
                total_cached_items = sum(cache_stats.values())
                if total_cached_items > 0:
                    self.logger.debug(f"Clearing {total_cached_items} cached items")
                    self.cache_manager.clear_all_caches()

                self.logger.close()
                return True
            else:
                self.logger.error(
                    f"Pipeline failed: {len(failed_phases)} phase(s) failed: {', '.join(failed_phases)}"
                )
                self.logger.close()
                return False

        except Exception as e:
            self.logger.error(f"Pipeline execution failed with unexpected error: {e}")
            traceback.print_exc()
            self.logger.close()
            return False

    def _execute_strategy_phase(self) -> Optional[nx.DiGraph]:
        """
        Execute graph filtering strategy (k-core, reciprocal, ego-alter).

        Returns:
            Optional[nx.DiGraph]: Processed graph or None on failure
        """
        phase_start = time.perf_counter()

        try:
            self.stages_controller.log_stage_start("strategy")

            self.logger.start_section("PHASE 1: GRAPH LOADING AND FILTERING")
            phase1_msg = EmojiFormatter.format(
                "progress", "PHASE 1: GRAPH LOADING AND FILTERING"
            )
            self.logger.info(phase1_msg)

            # Get stage-specific configuration
            stage_config = self.stages_controller.get_stage_configuration("strategy")

            # Load initial graph
            step_msg = EmojiFormatter.format("progress", "Step 1: Loading Network Data")
            self.logger.info(f"\n{step_msg}", "STEP_1_LOADING")
            self.logger.info("-" * 30)
            try:
                graph = self.graph_loader.load_from_json(self.config.input_file)
            except Exception as e:
                self.logger.error(f"Failed to load network data: {e}")
                self.stages_controller.log_stage_completion(
                    "strategy", False, time.perf_counter() - phase_start
                )
                return None

            if graph.number_of_nodes() == 0:
                self.logger.error("Loaded graph is empty - no nodes to analyze")
                self.stages_controller.log_stage_completion(
                    "strategy", False, time.perf_counter() - phase_start
                )
                return None

            success_msg = EmojiFormatter.format(
                "success", "Successfully loaded network data"
            )
            self.logger.info(success_msg)
            self.logger.info(
                f"  Initial graph: {graph.number_of_nodes():,} nodes, {graph.number_of_edges():,} edges"
            )
            self.logger.info("")

            # Apply strategy-specific filtering
            strategy = stage_config["strategy"]
            step_msg = EmojiFormatter.format(
                "progress", "Step 2: Applying Analysis Strategy"
            )
            self.logger.info(f"\n{step_msg}")
            self.logger.info("-" * 35)
            self.logger.info(f"Selected strategy: {strategy}")

            try:
                if strategy == "reciprocal_k-core":
                    # Filter for mutual connections only
                    self.logger.info("  → Filtering for mutual connections only...")
                    graph = self.graph_loader.filter_by_reciprocity(graph)
                    success_msg = EmojiFormatter.format(
                        "success",
                        f"After reciprocal filtering: {graph.number_of_nodes():,} nodes, {graph.number_of_edges():,} edges",
                    )
                    self.logger.info(f"  {success_msg}")

                elif strategy == "ego_alter_k-core":
                    # Create ego-alter graph
                    ego_username = stage_config["ego_username"]
                    if not ego_username:
                        raise ValueError(
                            "ego_username must be specified for ego_alter_k-core strategy"
                        )
                    self.logger.info(
                        f"  → Creating ego-alter network for user: {ego_username}"
                    )
                    graph = self.graph_loader.create_ego_alter_graph(
                        graph, ego_username
                    )
                    success_msg = EmojiFormatter.format(
                        "success",
                        f"After ego-alter filtering: {graph.number_of_nodes():,} nodes, {graph.number_of_edges():,} edges",
                    )
                    self.logger.info(f"  {success_msg}")

                elif strategy == "k-core":
                    self.logger.info("  → Using full network k-core analysis")

                # Check if graph is still valid after strategy filtering
                if graph.number_of_nodes() == 0:
                    self.logger.error(
                        f"Graph became empty after applying {strategy} strategy"
                    )
                    self.stages_controller.log_stage_completion(
                        "strategy", False, time.perf_counter() - phase_start
                    )
                    return None

            except Exception as e:
                self.logger.error(f"Strategy filtering failed: {e}")
                self.stages_controller.log_stage_completion(
                    "strategy", False, time.perf_counter() - phase_start
                )
                return None

            self.logger.info("")

            # Apply k-core pruning for all strategies
            k_values = stage_config["k_values"]
            k_value = k_values.get(strategy, stage_config["default_k_value"])

            try:
                step_msg = EmojiFormatter.format(
                    "progress", "Step 3: K-Core Graph Pruning"
                )
                self.logger.info(f"\n{step_msg}")
                self.logger.info("-" * 27)
                self.logger.info(f"K-value: {k_value} (minimum connections required)")
                self.logger.info("  → Removing nodes with fewer connections...")
                graph = self.graph_loader.prune_graph(graph, k_value)

                # Final validation
                if graph.number_of_nodes() == 0:
                    self.logger.error(
                        f"Graph became empty after k-core pruning with k={k_value}"
                    )
                    self.stages_controller.log_stage_completion(
                        "strategy", False, time.perf_counter() - phase_start
                    )
                    return None

            except Exception as e:
                self.logger.error(f"K-core pruning failed: {e}")
                self.stages_controller.log_stage_completion(
                    "strategy", False, time.perf_counter() - phase_start
                )
                return None

            phase_time = time.perf_counter() - phase_start
            self.phase_times["strategy"] = phase_time

            self.stages_controller.log_stage_completion("strategy", True, phase_time)
            success_msg = EmojiFormatter.format(
                "success",
                f"Final processed graph: {graph.number_of_nodes():,} nodes, {graph.number_of_edges():,} edges",
            )
            self.logger.info(f"  {success_msg}")
            self.logger.info("")
            self._log_timer(
                f"Phase 1 completed successfully in {format_time_duration(phase_time)}"
            )

            return graph

        except Exception as e:
            phase_time = time.perf_counter() - phase_start
            self.stages_controller.log_stage_completion("strategy", False, phase_time)
            self.logger.error(f"Strategy phase failed with unexpected error: {e}")
            return None

    def _execute_analysis_phase(self, graph: nx.DiGraph) -> Optional[nx.DiGraph]:
        """
        Execute network analysis (communities, centrality, paths).

        Args:
            graph: Input graph from strategy phase

        Returns:
            Optional[nx.DiGraph]: Analyzed graph or None on failure
        """
        phase_start = time.perf_counter()

        try:
            self.stages_controller.log_stage_start("analysis")

            self.logger.info("\n" + "=" * 40)
            phase_msg = EmojiFormatter.format("progress", "PHASE 2: NETWORK ANALYSIS")
            self.logger.info(phase_msg)
            self.logger.info("=" * 40)

            # Log analysis mode configuration
            self.mode_manager.log_mode_configuration()

            # Get stage-specific configuration
            stage_config = self.stages_controller.get_stage_configuration("analysis")

            analyzed_graph = graph
            component_results = {}

            # Perform network analysis (communities and centrality) if enabled
            if self.stages_controller.should_execute_analysis_component(
                "community_detection"
            ) or self.stages_controller.should_execute_analysis_component(
                "centrality_analysis"
            ):
                try:
                    step_msg = EmojiFormatter.format(
                        "progress", "Step 1: Network Structure Analysis"
                    )
                    self.logger.info(f"\n{step_msg}")
                    self.logger.info("-" * 34)
                    self.logger.info(
                        "  → Detecting communities and calculating centrality metrics..."
                    )
                    analyzed_graph = self.network_analyzer.analyze_network(graph)
                    component_results["network_structure"] = True
                    self.logger.info("")
                except Exception as e:
                    self.logger.error(f"Network structure analysis failed: {e}")
                    component_results["network_structure"] = False
                    # Continue with original graph for other components
                    analyzed_graph = graph

            # Path analysis if enabled
            if self.stages_controller.should_execute_analysis_component(
                "path_analysis"
            ):
                self.stages_controller.log_analysis_component_start("path_analysis")

                try:
                    step_msg = EmojiFormatter.format(
                        "progress", "Step 2: Path Length Analysis"
                    )
                    self.logger.info(f"\n{step_msg}")
                    self.logger.info("-" * 26)
                    self.logger.info(
                        "  → Calculating shortest paths and connectivity metrics..."
                    )
                    self.path_analyzer.analyze_path_lengths(analyzed_graph)
                    self.stages_controller.log_analysis_component_completion(
                        "path_analysis", True
                    )
                    component_results["path_analysis"] = True
                    self.logger.info("")
                except Exception as e:
                    self.logger.error(f"Path analysis failed: {e}")
                    self.stages_controller.log_analysis_component_completion(
                        "path_analysis", False
                    )
                    component_results["path_analysis"] = False
            else:
                self.stages_controller.log_analysis_component_skip(
                    "path_analysis", "Path analysis disabled in configuration"
                )
                component_results["path_analysis"] = "skipped"

            # Fame analysis
            try:
                step_msg = EmojiFormatter.format(
                    "progress", "Step 3: Influential Account Analysis"
                )
                self.logger.info(f"\n{step_msg}")
                self.logger.info("-" * 34)
                self.logger.info(
                    "  → Identifying high-influence users and celebrities..."
                )
                min_followers = stage_config["min_followers_in_network"]
                min_ratio = stage_config["min_fame_ratio"]

                unreachable_famous, reachable_famous = (
                    self.fame_analyzer.find_famous_accounts(
                        analyzed_graph, min_followers, min_ratio
                    )
                )

                # Report fame analysis results
                self._report_fame_analysis(unreachable_famous, reachable_famous)
                component_results["fame_analysis"] = True
                self.logger.info("")
            except Exception as e:
                self.logger.error(f"Fame analysis failed: {e}")
                component_results["fame_analysis"] = False
                # Set empty lists to prevent downstream errors
                unreachable_famous, reachable_famous = [], []

            # Contact path analysis if target specified and path analysis is enabled
            contact_target = stage_config["contact_path_target"]
            ego_username = self.config.ego_username

            if (
                contact_target
                and ego_username
                and self.stages_controller.should_execute_analysis_component(
                    "path_analysis"
                )
                and component_results.get("path_analysis")
            ):
                try:
                    self.logger.info(
                        f"Analyzing contact path from {ego_username} to: {contact_target}"
                    )
                    self.path_analyzer.print_detailed_contact_path(
                        analyzed_graph, ego_username, contact_target
                    )
                    component_results["contact_path"] = True
                except Exception as e:
                    self.logger.error(f"Contact path analysis failed: {e}")
                    component_results["contact_path"] = False
            elif contact_target and not ego_username:
                self.logger.warning(
                    f"Contact path target '{contact_target}' specified but no ego_username configured. Skipping contact path analysis."
                )
                component_results["contact_path"] = "skipped"
            elif ego_username and not contact_target:
                self.logger.info(
                    f"Ego username '{ego_username}' configured but no contact_path_target specified. Skipping contact path analysis."
                )
                component_results["contact_path"] = "skipped"
            elif (
                contact_target
                and not self.stages_controller.should_execute_analysis_component(
                    "path_analysis"
                )
            ):
                self.logger.info(
                    "Contact path analysis skipped - path analysis is disabled"
                )
                component_results["contact_path"] = "skipped"
            elif contact_target and component_results.get("path_analysis") is False:
                self.logger.info("Contact path analysis skipped - path analysis failed")
                component_results["contact_path"] = "skipped"
            else:
                component_results["contact_path"] = "skipped"

            # Path analysis for famous accounts if requested and path analysis is enabled
            if (
                stage_config["find_paths_to_all_famous"]
                and self.stages_controller.should_execute_analysis_component(
                    "path_analysis"
                )
                and component_results.get("path_analysis")
            ):
                try:
                    self._analyze_famous_paths(analyzed_graph, reachable_famous)
                    component_results["famous_paths"] = True
                except Exception as e:
                    self.logger.error(f"Famous paths analysis failed: {e}")
                    component_results["famous_paths"] = False
            elif stage_config["find_paths_to_all_famous"]:
                self.logger.info(
                    "Famous path analysis skipped - path analysis is disabled or failed"
                )
                component_results["famous_paths"] = "skipped"
            else:
                component_results["famous_paths"] = "skipped"

            # Evaluate overall analysis phase success
            failed_components = [
                name for name, result in component_results.items() if result is False
            ]
            successful_components = [
                name for name, result in component_results.items() if result
            ]
            skipped_components = [
                name
                for name, result in component_results.items()
                if result == "skipped"
            ]

            phase_time = time.perf_counter() - phase_start
            self.phase_times["analysis"] = phase_time

            # Log component results summary
            self.logger.info("\nAnalysis component results:")
            success_msg = EmojiFormatter.format(
                "success",
                f"Successful: {len(successful_components)} ({', '.join(successful_components) if successful_components else 'none'})",
            )
            self.logger.info(success_msg)
            if failed_components:
                error_msg = EmojiFormatter.format(
                    "error",
                    f"Failed: {len(failed_components)} ({', '.join(failed_components)})",
                )
                self.logger.info(error_msg)
            if skipped_components:
                self.logger.info(
                    f"⏭️ Skipped: {len(skipped_components)} ({', '.join(skipped_components)})"
                )

            # Analysis phase succeeds if at least one component succeeded and no critical failures
            analysis_success = (
                len(successful_components) > 0 and len(failed_components) == 0
            )

            self.stages_controller.log_stage_completion(
                "analysis", analysis_success, phase_time
            )

            if analysis_success:
                self._log_timer(
                    f"Analysis phase completed in {format_time_duration(phase_time)}"
                )
                return analyzed_graph
            else:
                self.logger.error(
                    f"Analysis phase failed: {len(failed_components)} component(s) failed"
                )
                return None

        except Exception as e:
            phase_time = time.perf_counter() - phase_start
            self.stages_controller.log_stage_completion("analysis", False, phase_time)
            self.logger.error(f"Analysis phase failed with unexpected error: {e}")
            return None

    def _execute_visualization_phase(self, graph: nx.DiGraph) -> bool:
        """
        Execute visualization generation using OutputManager.

        Args:
            graph: Analyzed graph from analysis phase

        Returns:
            bool: True if visualization generation succeeded
        """
        phase_start = time.perf_counter()

        try:
            self.stages_controller.log_stage_start("visualization")

            self.logger.info("\n" + "=" * 50)
            phase_msg = EmojiFormatter.format(
                "progress", "PHASE 3: VISUALIZATION GENERATION"
            )
            self.logger.info(phase_msg)
            self.logger.info("=" * 50)

            # Validate output configuration
            validation_errors = self.output_manager.validate_output_configuration()
            if validation_errors:
                for error in validation_errors:
                    self.logger.error(f"Output configuration error: {error}")
                return False

            # Log enabled output formats
            enabled_formats = self.output_manager.get_enabled_formats()
            self.logger.info("GENERATING OUTPUTS")
            self.logger.info("-" * 18)
            self.logger.info(f"Enabled formats: {', '.join(enabled_formats)}")
            self.logger.info("")

            # Get strategy and k-value for output generation
            strategy = self.config.strategy
            k_values = self.config.k_values.strategy_k_values
            k_value = k_values.get(strategy, self.config.k_values.default_k_value)
            output_prefix = self.config.output_file_prefix

            # Add total time to phase times for complete timing data
            complete_timing_data = self.phase_times.copy()
            complete_timing_data["total"] = (
                time.perf_counter() - self.pipeline_start_time
            )

            # Generate all outputs using OutputManager
            output_results = self.output_manager.generate_all_outputs(
                graph, strategy, k_value, complete_timing_data, output_prefix
            )

            # Check results - only count actually attempted outputs
            successful_outputs = sum(
                1 for success in output_results.values() if success
            )
            len(output_results)
            failed_outputs = sum(
                1 for success in output_results.values() if not success
            )

            phase_time = time.perf_counter() - phase_start
            self.phase_times["visualization"] = phase_time

            # Log output generation summary
            self.logger.info("")
            self.logger.info("OUTPUT GENERATION SUMMARY")
            self.logger.info("-" * 25)
            self.logger.info(f"Generated: {successful_outputs} format(s)")
            if failed_outputs > 0:
                self.logger.info(f"Failed: {failed_outputs} format(s)")

            for format_name, success in output_results.items():
                if success:
                    status_msg = EmojiFormatter.format("success", "SUCCESS")
                else:
                    status_msg = EmojiFormatter.format("error", "FAILED")
                self.logger.info(f"  {format_name.upper()}: {status_msg}")

            # All attempted outputs must succeed for visualization phase to be considered successful
            all_successful = all(output_results.values()) and len(output_results) > 0

            self.stages_controller.log_stage_completion(
                "visualization", all_successful, phase_time
            )
            self._log_timer(
                f"Visualization phase completed in {format_time_duration(phase_time)}"
            )

            if not all_successful:
                failed_outputs = [
                    fmt for fmt, success in output_results.items() if not success
                ]
                self.logger.error(
                    f"Visualization phase failed: {len(failed_outputs)} output(s) failed: {', '.join(failed_outputs)}"
                )

            return all_successful

        except Exception as e:
            phase_time = time.perf_counter() - phase_start
            self.stages_controller.log_stage_completion(
                "visualization", False, phase_time
            )
            self.logger.error(f"Visualization phase failed: {e}")
            return False

    def _report_fame_analysis(
        self,
        unreachable_famous: List[Dict[str, Union[str, int, float]]],
        reachable_famous: List[Dict[str, Union[str, int, float]]],
    ) -> None:
        """
        Report fame analysis results.

        Args:
            unreachable_famous: List of famous accounts with no following
            reachable_famous: List of famous accounts with following
        """
        total_famous = len(unreachable_famous) + len(reachable_famous)

        if total_famous == 0:
            self.logger.info("No famous accounts found matching criteria")
            return

        self.logger.info(f"Found {total_famous} famous accounts:")
        self.logger.info(f"  - {len(unreachable_famous)} unreachable (follow nobody)")
        self.logger.info(f"  - {len(reachable_famous)} reachable (follow others)")

        # Show top 5 from each category
        if unreachable_famous:
            self.logger.info("\nTop unreachable famous accounts:")
            for i, account in enumerate(unreachable_famous[:5]):
                self.logger.info(
                    f"  {i + 1}. {account['username']} "
                    f"(followers: {account['followers_in_network']}, "
                    f"ratio: {account['ratio']:.1f})"
                )

        if reachable_famous:
            self.logger.info("\nTop reachable famous accounts:")
            for i, account in enumerate(reachable_famous[:5]):
                self.logger.info(
                    f"  {i + 1}. {account['username']} "
                    f"(followers: {account['followers_in_network']}, "
                    f"following: {account['following_in_network']}, "
                    f"ratio: {account['ratio']:.1f})"
                )

    def _analyze_famous_paths(
        self,
        graph: nx.DiGraph,
        reachable_famous: List[Dict[str, Union[str, int, float]]],
    ) -> None:
        """
        Analyze paths to famous accounts if requested.

        Args:
            graph: Analyzed graph
            reachable_famous: List of reachable famous accounts
        """
        if not reachable_famous:
            return

        ego_username = self.config.ego_username
        if not ego_username:
            self.logger.warning(
                "Cannot analyze paths to famous accounts: no ego_username configured. Skipping famous path analysis."
            )
            return

        self.logger.info(
            f"Analyzing paths from {ego_username} to {len(reachable_famous)} reachable famous accounts..."
        )

        paths_found = 0
        for account in reachable_famous[:10]:  # Limit to top 10 to avoid spam
            username = account["username"]
            path_found = self.path_analyzer.print_detailed_contact_path(
                graph, ego_username, username
            )
            if path_found:
                paths_found += 1

        self.logger.info(
            f"Found paths to {paths_found} out of {min(10, len(reachable_famous))} famous accounts"
        )

    def _log_pipeline_configuration(self) -> None:
        """Log pipeline configuration and stage execution plan."""
        self.logger.start_section("PIPELINE CONFIGURATION")
        self.logger.info(f"Strategy: {self.config.strategy}")
        self.logger.info(f"Analysis mode: {self.config.analysis_mode.mode.value}")
        self.logger.info("")

        # Log enabled stages
        stages = self.config.pipeline_stages
        self.logger.info("ENABLED STAGES")
        self.logger.info("-" * 14)
        strategy_msg = EmojiFormatter.format(
            "success", f"Graph Loading & Filtering: {stages.enable_strategy}"
        )
        analysis_msg = EmojiFormatter.format(
            "success", f"Network Analysis: {stages.enable_analysis}"
        )
        viz_msg = EmojiFormatter.format(
            "success", f"Visualization: {stages.enable_visualization}"
        )
        self.logger.info(strategy_msg)
        self.logger.info(analysis_msg)
        self.logger.info(viz_msg)
        self.logger.info("")

        # Log enabled analysis components if analysis is enabled
        if stages.enable_analysis:
            self.logger.info("ANALYSIS COMPONENTS")
            self.logger.info("-" * 19)
            community_msg = EmojiFormatter.format(
                "success", f"Community detection: {stages.enable_community_detection}"
            )
            centrality_msg = EmojiFormatter.format(
                "success", f"Centrality analysis: {stages.enable_centrality_analysis}"
            )
            path_msg = EmojiFormatter.format(
                "success", f"Path analysis: {stages.enable_path_analysis}"
            )
            self.logger.info(community_msg)
            self.logger.info(centrality_msg)
            self.logger.info(path_msg)
            self.logger.info("")

        # Log output formats
        output = self.config.output_control
        self.logger.info("OUTPUT FORMATS")
        self.logger.info("-" * 14)
        html_msg = EmojiFormatter.format(
            "success", f"Interactive HTML: {output.generate_html}"
        )
        png_msg = EmojiFormatter.format("success", f"Static PNG: {output.generate_png}")
        reports_msg = EmojiFormatter.format(
            "success", f"Text Reports: {output.generate_reports}"
        )
        timing_msg = EmojiFormatter.format(
            "success", f"Timing logs: {output.enable_timing_logs}"
        )
        self.logger.info(html_msg)
        self.logger.info(png_msg)
        self.logger.info(reports_msg)
        self.logger.info(timing_msg)
        self.logger.info("")

    def _log_parallel_processing_status(self) -> None:
        """Log parallel processing capabilities and configuration."""
        self.logger.info("PARALLEL PROCESSING")
        self.logger.info("-" * 18)

        # Get and log nx-parallel status
        nx_status = get_nx_parallel_status_message()
        self.logger.info(f"NetworkX optimization: {nx_status}")

        # Get sample parallel configuration to show capabilities
        sample_config = get_analysis_parallel_config()
        self.logger.info(f"Available cores: {sample_config.cores_available}")
        self.logger.info(f"Environment: {sample_config.environment}")

        if sample_config.cores_available > 1:
            self.logger.info(
                f"Parallel processing: Enabled (strategy: {sample_config.strategy})"
            )
        else:
            self.logger.info("Parallel processing: Single-core system")

        self.logger.info("")

    def _report_pipeline_completion(self) -> None:
        """Report overall pipeline completion statistics."""
        total_time = time.perf_counter() - self.pipeline_start_time

        self.logger.info("\n" + "=" * 70)
        self.logger.info("PIPELINE COMPLETION SUMMARY")
        self.logger.info("=" * 70)

        # Report stage execution summary
        execution_summary = self.stages_controller.get_execution_summary()
        self.logger.info("")
        self.logger.info("STAGE EXECUTION SUMMARY")
        self.logger.info("-" * 23)
        for stage_name, status in execution_summary["stages"].items():
            if status == "completed":
                status_icon = EmojiFormatter.get_emoji("success")
            elif status == "failed":
                status_icon = EmojiFormatter.get_emoji("error")
            else:
                status_icon = "○"
            self.logger.info(
                f"  {status_icon} {stage_name.replace('_', ' ').title()}: {status}"
            )

        if execution_summary["stages"]["analysis"] in ["completed", "in_progress"]:
            self.logger.info("")
            self.logger.info("ANALYSIS COMPONENTS")
            self.logger.info("-" * 19)
            for component_name, status in execution_summary[
                "analysis_components"
            ].items():
                if status == "completed":
                    status_icon = EmojiFormatter.get_emoji("success")
                elif status == "failed":
                    status_icon = EmojiFormatter.get_emoji("error")
                else:
                    status_icon = "○"
                self.logger.info(
                    f"  {status_icon} {component_name.replace('_', ' ').title()}: {status}"
                )

        # Report phase timings
        self.logger.info("")
        self.logger.info("EXECUTION TIMING")
        self.logger.info("-" * 16)
        for phase_name, phase_time in self.phase_times.items():
            percentage = (phase_time / total_time) * 100
            self._log_timer(
                f"{phase_name.replace('_', ' ').title()}: "
                f"{format_time_duration(phase_time)} ({percentage:.1f}%)"
            )

        self.logger.info("")
        self._log_timer(f"Total execution time: {format_time_duration(total_time)}")

        # Validate that all enabled phases completed successfully
        enabled_phases = [
            phase
            for phase in ["strategy", "analysis", "visualization"]
            if self.stages_controller.should_execute_stage(phase)
        ]
        completed_phases = [
            phase
            for phase in enabled_phases
            if execution_summary["stages"].get(phase) == "completed"
        ]

        self.logger.info("")
        if len(completed_phases) == len(enabled_phases):
            self._log_success("🎉 All pipeline phases completed successfully!")
        else:
            incomplete_phases = [
                phase for phase in enabled_phases if phase not in completed_phases
            ]
            self.logger.warning(
                f"⚠️  Pipeline completed with issues: {', '.join(incomplete_phases)} phases did not complete successfully"
            )

        self.logger.info("=" * 70)


def load_config_from_file(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file using the configuration manager.

    Args:
        config_path: Path to configuration JSON file

    Returns:
        Dict[str, Any]: Loaded configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid JSON or fails validation
    """
    config_manager = get_configuration_manager()
    config = config_manager.load_configuration(config_file=config_path)
    return config_manager.serialize_configuration(config)


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create command-line argument parser for the FollowWeb pipeline.

    Returns:
        argparse.ArgumentParser: Argument parser
    """
    parser = argparse.ArgumentParser(
        description="Social network analysis tool for Instagram follower/following data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  followweb --input examples/followers_following.json
  followweb --config my_config.json --fast-mode
  followweb --strategy reciprocal_k-core --k-reciprocal 15
  followweb --skip-analysis --no-png
  followweb --print-default-config > config.json
        """,
    )

    # Configuration options
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "--config",
        "-c",
        type=str,
        metavar="FILE",
        help="Path to JSON configuration file. Loads configuration with "
        "pipeline stages, analysis modes, and output control settings. "
        "CLI parameters override config file values.",
    )

    # Input/output options
    io_group = parser.add_argument_group("Input/Output")
    io_group.add_argument(
        "--input",
        "-i",
        type=str,
        metavar="FILE",
        help="Path to input JSON file containing follower/following data. "
        "Must be in FollowWeb JSON format with user relationship data.",
    )

    io_group.add_argument(
        "--output-prefix",
        "-o",
        type=str,
        metavar="PREFIX",
        help="Output file prefix (e.g., Results/Analysis)"
        'Structure: PREFIX-strategy-kN-hash.ext (e.g., "Results/Analysis-k-core-k10-abc123.html")',
    )

    # Pipeline strategy options
    strategy_group = parser.add_argument_group("Strategy")
    strategy_group.add_argument(
        "--strategy",
        "-s",
        choices=["k-core", "reciprocal_k-core", "ego_alter_k-core"],
        metavar="STRATEGY",
        help="Network analysis strategy: "
        '"k-core" (full network k-core decomposition), '
        '"reciprocal_k-core" (mutual connections only), '
        '"ego_alter_k-core" (personal network analysis)',
    )

    strategy_group.add_argument(
        "--ego-username",
        type=str,
        metavar="USERNAME",
        help="Target username for ego_alter_k-core strategy. Required when using "
        "ego_alter_k-core strategy. Analyzes the personal network centered on this user.",
    )

    # Analysis mode selection flags (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.title = "Analysis Modes"

    mode_group.add_argument(
        "--fast-mode",
        action="store_true",
        help="FAST mode: Optimized algorithms with reduced precision. "
        "Uses sampling (threshold: 1000 nodes), limited layout iterations (100), "
        "approximate algorithms, and skips expensive computations. "
        "Best for: Large networks (>10K nodes), quick exploration, performance testing.",
    )

    mode_group.add_argument(
        "--medium-mode",
        action="store_true",
        help="MEDIUM mode: Balanced analysis depth and performance. "
        "Moderate sampling (threshold: 5000 nodes), reasonable layout iterations (500), "
        "selective algorithm optimizations. "
        "Best for: Medium networks (1K-10K nodes), regular analysis, balanced quality/speed.",
    )

    mode_group.add_argument(
        "--full-mode",
        action="store_true",
        help="FULL mode: Detailed analysis with maximum precision (default). "
        "Conservative sampling (threshold: 10000 nodes), extensive layout iterations (1000), "
        "all algorithms enabled, high quality results. "
        "Best for: Research, publication-quality results, detailed analysis.",
    )

    # K-value CLI parameters for all strategies
    k_values_group = parser.add_argument_group("K-Values")
    k_values_group.add_argument(
        "--k-core",
        type=int,
        metavar="K",
        help="K-value for k-core strategy (default: 10). "
        "Minimum degree for nodes in k-core subgraph. "
        "Higher values focus on more densely connected regions. "
        "Typical range: 1-50 (1=include all, 20+=very dense cores only)",
    )

    k_values_group.add_argument(
        "--k-reciprocal",
        type=int,
        metavar="K",
        help="K-value for reciprocal_k-core strategy (default: 10). "
        "Minimum mutual connections for nodes in reciprocal k-core. "
        "Focuses on bidirectional relationships. "
        "Typical range: 1-30 (higher values = stronger mutual connections)",
    )

    k_values_group.add_argument(
        "--k-ego-alter",
        type=int,
        metavar="K",
        help="K-value for ego_alter_k-core strategy (default: 10). "
        "Minimum connections within ego network for inclusion. "
        "Controls density of personal network analysis. "
        "Typical range: 1-20 (depends on ego user's network size)",
    )

    # Output control flags
    output_group = parser.add_argument_group("Output")
    output_group.add_argument(
        "--no-png",
        action="store_true",
        help="Disable PNG static image generation. "
        "Skips matplotlib-based high-resolution network images. "
        "Use when only interactive visualization is needed or for faster execution.",
    )

    output_group.add_argument(
        "--no-html",
        action="store_true",
        help="Disable HTML interactive visualization generation. "
        "Skips Pyvis-based interactive network browser. "
        "Use for batch processing or when only static images are needed.",
    )

    output_group.add_argument(
        "--no-reports",
        action="store_true",
        help="Disable text report generation. "
        "Skips detailed metrics and statistics text files. "
        "Use when only visualizations are needed.",
    )

    output_group.add_argument(
        "--enable-timing-logs",
        action="store_true",
        help="Enable detailed timing log generation. "
        "Creates *_timing.txt files with phase-by-phase execution times. "
        "Useful for performance analysis and optimization.",
    )

    # Pipeline stage control flags
    stage_group = parser.add_argument_group("Pipeline Stages")
    stage_group.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Skip analysis phase (strategy + visualization only). "
        "Loads and filters network data, then generates visualizations without "
        "community detection, centrality analysis, or path analysis. "
        "Fastest execution for basic network visualization.",
    )

    stage_group.add_argument(
        "--skip-visualization",
        action="store_true",
        help="Skip visualization phase (strategy + analysis only). "
        "Performs complete network analysis but skips HTML/PNG generation. "
        "Useful for batch analysis or when only metrics are needed.",
    )

    stage_group.add_argument(
        "--analysis-only",
        action="store_true",
        help="Run analysis phase only (equivalent to --skip-visualization). "
        "Performs strategy and analysis phases but skips visualization. "
        "Generates text reports with network metrics and statistics.",
    )

    # Analysis component control
    analysis_group = parser.add_argument_group("Analysis Components")
    analysis_group.add_argument(
        "--skip-path-analysis",
        action="store_true",
        help="Skip path analysis component (performance improvement). "
        "Disables shortest path calculations, connectivity analysis, and contact path finding. "
        "Recommended for large networks (>5K nodes) when path information is not needed.",
    )

    analysis_group.add_argument(
        "--skip-community-detection",
        action="store_true",
        help="Skip community detection analysis. "
        "Disables Louvain algorithm for community identification. "
        "Network will be visualized without community colors/grouping.",
    )

    analysis_group.add_argument(
        "--skip-centrality-analysis",
        action="store_true",
        help="Skip centrality analysis (degree, betweenness, eigenvector, closeness). "
        "Disables node importance calculations. "
        "Visualization will use uniform node sizing instead of centrality-based sizing.",
    )

    # Performance options
    performance_group = parser.add_argument_group("Performance")
    performance_group.add_argument(
        "--max-layout-iterations",
        type=int,
        metavar="N",
        help="Maximum iterations for spring layout algorithm (default varies by mode). "
        "Higher values = better layout quality but slower execution. "
        "Typical range: 50-2000 (50=fast/rough, 1000=high quality, 2000=publication)",
    )

    performance_group.add_argument(
        "--sampling-threshold",
        type=int,
        metavar="N",
        help="Node count threshold for enabling sampling optimizations (default varies by mode). "
        "Networks larger than this use sampling for expensive algorithms. "
        "Typical range: 1000-15000 (lower=more aggressive sampling, higher=more precision)",
    )

    # Logging options
    logging_group = parser.add_argument_group("Logging")
    logging_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging with timestamps and module names. "
        "Shows progress information, algorithm parameters, and debug messages. "
        "Useful for troubleshooting and development.",
    )

    logging_group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress all console output except errors. "
        "Only critical error messages will be displayed. "
        "Useful for batch processing and automated scripts.",
    )

    # Utility options
    utility_group = parser.add_argument_group("Utilities")
    utility_group.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration file and exit without running analysis. "
        "Checks for parameter consistency, stage dependencies, and file permissions. "
        "Returns exit code 0 for valid config, 1 for invalid config.",
    )

    utility_group.add_argument(
        "--print-default-config",
        action="store_true",
        help="Print default configuration as JSON and exit. "
        "Shows available parameters with default values. "
        "Use to create custom configuration files: --print-default-config > my_config.json",
    )

    # Emoji configuration options
    emoji_group = parser.add_argument_group("Display")
    emoji_group.add_argument(
        "--emoji-level",
        choices=["full", "simple", "text", "none"],
        help="Set emoji fallback level: "
        "'full' = Unicode emojis (checkmark, X, circle), "
        "'simple' = ASCII symbols ([checkmark], [X], [~]), "
        "'text' = Plain text (SUCCESS, ERROR, PROGRESS), "
        "'none' = No emoji indicators",
    )

    return parser


# CLI overrides are handled by ConfigurationManager.load_configuration()


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """
    Setup optimized logging configuration.

    Args:
        verbose: Enable verbose (DEBUG) logging
        quiet: Suppress all output except errors
    """
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    # Simple logging setup that works with the unified emoji system
    handler = logging.StreamHandler(sys.stdout)

    # Use a simple formatter that respects the emoji configuration
    if verbose:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s: %(message)s"
        )
    else:
        formatter = logging.Formatter("%(message)s")

    handler.setFormatter(formatter)

    # Ensure UTF-8 encoding for Unicode characters on Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            # Fallback: continue with default encoding
            pass

    logging.basicConfig(level=level, handlers=[handler], force=True)


def main() -> int:
    """
    Main entry point with configuration loading and error management.

    This function provides:
    - Command-line interface handling
    - Configuration loading and validation
    - Error management with appropriate exit codes

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        # Parse command-line arguments
        parser = create_argument_parser()
        args = parser.parse_args()

        # Setup logging based on verbosity
        setup_logging(args.verbose, args.quiet)
        logger = logging.getLogger(__name__)

        # Handle utility commands first
        if args.print_default_config:
            config_manager = get_configuration_manager()
            config = config_manager.load_configuration()
            config_dict = config_manager.serialize_configuration(config)
            # Use print for utility output to stdout (not logging)
            print(json.dumps(config_dict, indent=2, default=str))
            return 0

        # Load configuration using the configuration manager
        config_manager = get_configuration_manager()

        if args.config:
            logger.info(f"Loading configuration from: {args.config}")
            config = config_manager.load_configuration(config_file=args.config)
            success_msg = EmojiFormatter.format(
                "success", "Configuration validated successfully"
            )
            logger.info(success_msg)
        else:
            logger.debug("Using default configuration")
            config = config_manager.load_configuration()
            success_msg = EmojiFormatter.format(
                "success", "Configuration validated successfully"
            )
            logger.info(success_msg)

        # Apply emoji configuration
        emoji_level = config.output_control.output_formatting.emoji.fallback_level
        EmojiFormatter.set_fallback_level(emoji_level)

        # Apply command-line overrides
        if hasattr(args, "__dict__"):
            # Convert args to dict and apply overrides
            cli_overrides = {}

            # Basic input/output overrides
            if args.input:
                cli_overrides["input_file"] = args.input
            if args.output_prefix:
                cli_overrides["output_file_prefix"] = args.output_prefix
            if args.strategy:
                cli_overrides["strategy"] = args.strategy
            if args.ego_username:
                cli_overrides["ego_username"] = args.ego_username

            # Analysis mode selection flags
            if args.fast_mode:
                cli_overrides["analysis_mode"] = {"mode": "fast"}
            elif args.medium_mode:
                cli_overrides["analysis_mode"] = {"mode": "medium"}
            elif args.full_mode:
                cli_overrides["analysis_mode"] = {"mode": "full"}

            # K-value CLI parameters for all strategies
            # When a specific k-value is provided, automatically switch to that strategy
            k_values_overrides = {}
            if args.k_core is not None:
                k_values_overrides["k-core"] = args.k_core
                # Auto-switch to k-core strategy when --k-core is specified
                if "strategy" not in cli_overrides:
                    cli_overrides["strategy"] = "k-core"
            if args.k_reciprocal is not None:
                k_values_overrides["reciprocal_k-core"] = args.k_reciprocal
                # Auto-switch to reciprocal_k-core strategy when --k-reciprocal is specified
                if "strategy" not in cli_overrides:
                    cli_overrides["strategy"] = "reciprocal_k-core"
            if args.k_ego_alter is not None:
                k_values_overrides["ego_alter_k-core"] = args.k_ego_alter
                # Auto-switch to ego_alter_k-core strategy when --k-ego-alter is specified
                if "strategy" not in cli_overrides:
                    cli_overrides["strategy"] = "ego_alter_k-core"

            if k_values_overrides:
                cli_overrides["k_values"] = {"strategy_k_values": k_values_overrides}

            # Output control flags
            output_control_overrides = {}
            if args.no_png:
                output_control_overrides["generate_png"] = False
            if args.no_html:
                output_control_overrides["generate_html"] = False
            if args.no_reports:
                output_control_overrides["generate_reports"] = False
            if args.enable_timing_logs:
                output_control_overrides["enable_timing_logs"] = True

            if output_control_overrides:
                cli_overrides["output_control"] = output_control_overrides

            # Pipeline stage control flags
            pipeline_stages_overrides = {}
            if args.skip_analysis or args.analysis_only:
                # Handle mutually exclusive stage control
                if args.skip_analysis:
                    pipeline_stages_overrides["enable_analysis"] = False
                if args.analysis_only or args.skip_visualization:
                    pipeline_stages_overrides["enable_visualization"] = False

            # Analysis component control
            if args.skip_path_analysis:
                pipeline_stages_overrides["enable_path_analysis"] = False
            if args.skip_community_detection:
                pipeline_stages_overrides["enable_community_detection"] = False
            if args.skip_centrality_analysis:
                pipeline_stages_overrides["enable_centrality_analysis"] = False

            if pipeline_stages_overrides:
                cli_overrides["pipeline_stages"] = pipeline_stages_overrides

            # Performance options
            analysis_mode_overrides = cli_overrides.get("analysis_mode", {})
            if args.max_layout_iterations is not None:
                analysis_mode_overrides["max_layout_iterations"] = (
                    args.max_layout_iterations
                )
            if args.sampling_threshold is not None:
                analysis_mode_overrides["sampling_threshold"] = args.sampling_threshold

            if analysis_mode_overrides:
                cli_overrides["analysis_mode"] = analysis_mode_overrides

            # Emoji configuration
            if args.emoji_level:
                cli_overrides["output_control"] = cli_overrides.get(
                    "output_control", {}
                )
                cli_overrides["output_control"]["output_formatting"] = cli_overrides[
                    "output_control"
                ].get("output_formatting", {})
                cli_overrides["output_control"]["output_formatting"]["emoji"] = {
                    "fallback_level": args.emoji_level
                }

            if cli_overrides:
                # Reload configuration with CLI overrides
                config_dict = asdict(config)
                merged_config = config_manager.merge_configurations(
                    config_dict, cli_overrides
                )
                config = load_config_from_dict(merged_config)

        # Validate configuration if requested
        if args.validate_config:
            try:
                validation_result = config_manager.validate_configuration(config)
                if validation_result.is_valid:
                    logger.info("Configuration validation successful")
                    if validation_result.warnings:
                        logger.info("Warnings:")
                        for warning in validation_result.warnings:
                            logger.warning(warning)
                    return 0
                else:
                    logger.error("configuration validation failed")
                    for error in validation_result.errors:
                        logger.error(f"  - {error}")
                    return 1
            except Exception as e:
                logger.error(f"Configuration validation failed: {e}")
                return 1

        # Validate input file exists before starting pipeline
        input_file = config.input_file
        if not os.path.exists(input_file):
            logger.error("input file not found")
            return 1

        # Create output directory if needed and allowed
        output_prefix = config.output_file_prefix
        output_dir = os.path.dirname(output_prefix)
        if output_dir and not os.path.exists(output_dir):
            logger.info(f"Creating default output directory: {output_dir}")
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError:
                logger.error("failed to create Output directory")
                return 1

        # Create and execute pipeline
        logger.debug("Initializing pipeline orchestrator")
        orchestrator = PipelineOrchestrator(config)

        logger.debug("Starting pipeline execution")
        success = orchestrator.execute_pipeline()

        if success:
            success_msg = EmojiFormatter.format(
                "success", "Pipeline completed successfully"
            )
            logger.info(success_msg)
            return 0
        else:
            logger.error("Pipeline execution failed")
            return 1

    except KeyboardInterrupt:
        try:
            error_msg = EmojiFormatter.format("error", "Pipeline interrupted by user")
            logger.error(error_msg)
        except NameError:
            print("ERROR: Pipeline interrupted by user")
        return 1
    except FileNotFoundError as e:
        try:
            error_msg = EmojiFormatter.format("error", f"File not found - {e}")
            logger.error(error_msg)
        except NameError:
            print(f"ERROR: File not found - {e}")
        return 1
    except ValueError as e:
        try:
            error_msg = EmojiFormatter.format("error", f"Configuration error - {e}")
            logger.error(error_msg)
            logger.info("For configuration help:")
            logger.info("  followweb --print-default-config")
            logger.info("  followweb --help")
            logger.info("  See docs/CONFIGURATION_GUIDE.md for detailed examples")
        except NameError:
            print(f"ERROR: Configuration error - {e}")
            print("For configuration help:")
            print("  followweb --print-default-config")
            print("  followweb --help")
            print("  See docs/CONFIGURATION_GUIDE.md for detailed examples")
        return 1
    except PermissionError as e:
        try:
            error_msg = EmojiFormatter.format("error", f"Permission denied - {e}")
            logger.error(error_msg)
        except NameError:
            print(f"ERROR: Permission denied - {e}")
        return 1
    except Exception as e:
        try:
            error_msg = EmojiFormatter.format(
                "error", f"FATAL: Unexpected error occurred - {e}"
            )
            logger.error(error_msg)
        except NameError:
            print(f"ERROR: FATAL: Unexpected error occurred - {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
