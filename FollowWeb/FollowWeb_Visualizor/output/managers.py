"""
Output management system for FollowWeb network analysis.

This module provides unified control over all output generation including:
- HTML, PNG, TXT analysis files
- Unified logging to console and text files
- Single consistent system for all output operations
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from .formatters import EmojiFormatter
from .logging import Logger, OutputConfig


class OutputManager:
    """
    Unified output manager that consolidates all output generation.

    This class provides unified control over all output generation including:
    - HTML, PNG, TXT analysis files
    - Unified logging to console and text files
    - Single consistent system for all output operations
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the unified output manager with configuration.

        Args:
            config: Complete configuration dictionary containing output control settings
        """
        self.config = config
        self.output_control = config.get("output_control", {})
        self.logger = logging.getLogger(__name__)

        # Initialize visualization components
        vis_config = config.get("visualization", {})

        # Import here to avoid circular imports
        from ..visualization.metrics import MetricsCalculator
        from ..visualization.renderers import InteractiveRenderer, StaticRenderer

        self.metrics_calculator = MetricsCalculator(vis_config)
        self.interactive_renderer = InteractiveRenderer(
            vis_config, self.metrics_calculator
        )

        # Initialize static renderer with performance config
        performance_config = vis_config.get("performance", {})
        analysis_mode = config.get("analysis_mode", {})
        if analysis_mode.get("max_layout_iterations") is not None:
            performance_config["max_layout_iterations"] = analysis_mode[
                "max_layout_iterations"
            ]
        if analysis_mode.get("enable_fast_algorithms") is not None:
            performance_config["fast_mode"] = analysis_mode["enable_fast_algorithms"]

        self.static_renderer = StaticRenderer(vis_config, performance_config)
        self.metrics_reporter = MetricsReporter(vis_config)

        # Initialize unified logger for this pipeline run
        self.unified_logger = None
        self._current_run_id = None

    def initialize_unified_logger(
        self, output_prefix: str, strategy: str, k_value: int, emoji_level: str = "full"
    ) -> None:
        """
        Initialize unified logger for pipeline execution.

        Args:
            output_prefix: Base output file prefix
            strategy: Analysis strategy
            k_value: K-value for analysis
            emoji_level: Emoji fallback level
        """
        # Set emoji level
        EmojiFormatter.set_fallback_level(emoji_level)

        # Generate run ID and text file path
        self._current_run_id = str(int(time.time() * 1000))
        from ..utils.files import generate_output_filename

        text_file_path = generate_output_filename(
            output_prefix, strategy, k_value, "txt", self._current_run_id
        )

        # Create configuration for unified logging
        config = OutputConfig(
            console_output=True,
            text_file_output=True,  # Enable unified output system
            simultaneous_logging=True,
            organize_by_sections=True,
            include_emojis_in_text=True,
            preserve_timing_info=True,
            text_file_path=text_file_path,
        )

        self.unified_logger = Logger(config)

    def generate_all_outputs(
        self,
        graph,
        strategy: str,
        k_value: int,
        timing_data: Dict[str, float],
        output_prefix: str,
    ) -> Dict[str, bool]:
        """
        Generate all enabled output formats using unified system.

        Args:
            graph: Analyzed graph to visualize
            strategy: Analysis strategy used
            k_value: K-value used for analysis
            timing_data: Timing information for different phases
            output_prefix: Base output file prefix

        Returns:
            Dict[str, bool]: Success status for each output format
        """
        results = {}

        # Use existing run_id if available, otherwise generate new one
        run_id = self._current_run_id or str(int(time.time() * 1000))

        # Calculate shared metrics once for all visualizations
        if self.unified_logger:
            self.unified_logger.log_progress("Calculating visualization metrics...")
        else:
            progress_msg = EmojiFormatter.format(
                "progress", "Calculating visualization metrics..."
            )
            self.logger.info(f"\n{progress_msg}")

        shared_metrics = self.metrics_calculator.calculate_all_metrics(graph)

        # Extract metrics for PNG renderer (which still needs dict format)
        node_metrics = {}
        edge_metrics: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for node, node_metric in shared_metrics.node_metrics.items():
            node_metrics[node] = {
                "size": node_metric.size,
                "community": node_metric.community,
                "color_hex": node_metric.color_hex,
                "color_rgba": node_metric.color_rgba,
                "degree": node_metric.centrality_values["degree"],
                "betweenness": node_metric.centrality_values["betweenness"],
                "eigenvector": node_metric.centrality_values["eigenvector"],
            }

        for edge, edge_metric in shared_metrics.edge_metrics.items():
            edge_metrics[edge] = {
                "width": edge_metric.width,
                "color": edge_metric.color,
                "is_mutual": edge_metric.is_mutual,
                "is_bridge": edge_metric.is_bridge,
                "common_neighbors": edge_metric.common_neighbors,
                "u_comm": edge_metric.u_comm,
                "v_comm": edge_metric.v_comm,
            }

        # Generate output filenames with shared run_id
        from ..utils.files import ensure_output_directory, generate_output_filename

        html_filename = generate_output_filename(
            output_prefix, strategy, k_value, "html", run_id
        )
        png_filename = generate_output_filename(
            output_prefix, strategy, k_value, "png", run_id
        )
        txt_filename = generate_output_filename(
            output_prefix, strategy, k_value, "txt", run_id
        )

        # Ensure output directories exist
        try:
            for filename in [html_filename, png_filename, txt_filename]:
                ensure_output_directory(filename, create_if_missing=True)
        except (ValueError, OSError) as e:
            # Directory creation failed - return failure for all outputs
            if self.unified_logger:
                self.unified_logger.error(f"Failed to create output directories: {e}")
            else:
                self.logger.error(f"Failed to create output directories: {e}")
            return {"html": False, "png": False, "txt": False}

        # Generate HTML visualization if enabled
        if self.should_generate_html():
            if self.unified_logger:
                self.unified_logger.log_progress(
                    "Generating interactive HTML visualization..."
                )
            else:
                progress_msg = EmojiFormatter.format(
                    "progress", "Generating interactive HTML visualization..."
                )
                self.logger.info(progress_msg)
            results["html"] = self.interactive_renderer.generate_html(
                graph, html_filename, shared_metrics
            )
        else:
            if self.unified_logger:
                self.unified_logger.info(
                    "ℹ️  Interactive HTML generation disabled in configuration"
                )
            else:
                self.logger.info(
                    "ℹ️  Interactive HTML generation disabled in configuration"
                )

        # Generate PNG visualization if enabled
        if self.should_generate_png():
            if self.unified_logger:
                self.unified_logger.log_progress(
                    "Generating static PNG visualization..."
                )
            else:
                progress_msg = EmojiFormatter.format(
                    "progress", "Generating static PNG visualization..."
                )
                self.logger.info(progress_msg)
            results["png"] = self.static_renderer.generate_png(
                graph, png_filename, node_metrics, edge_metrics, shared_metrics
            )
        else:
            if self.unified_logger:
                self.unified_logger.info(
                    "ℹ️  Static PNG generation disabled in configuration"
                )
            else:
                self.logger.info("ℹ️  Static PNG generation disabled in configuration")

        # Generate metrics report if enabled
        if self.should_generate_reports():
            if self.unified_logger:
                self.unified_logger.log_progress("Generating metrics report...")
            else:
                progress_msg = EmojiFormatter.format(
                    "progress", "Generating metrics report..."
                )
                self.logger.info(progress_msg)

            report_content = self.metrics_reporter.generate_analysis_report(
                graph, self.config, strategy, k_value, timing_data
            )

            results["report"] = self.metrics_reporter.save_metrics_file(
                report_content, txt_filename
            )
        else:
            if self.unified_logger:
                self.unified_logger.info(
                    "ℹ️  Metrics report generation disabled in configuration"
                )
            else:
                self.logger.info(
                    "ℹ️  Metrics report generation disabled in configuration"
                )

        # Generate timing log if enabled
        if self.should_generate_timing_logs():
            if self.unified_logger:
                self.unified_logger.log_progress("Saving timing log...")
            else:
                progress_msg = EmojiFormatter.format("progress", "Saving timing log...")
                self.logger.info(progress_msg)
            timing_base_filename = txt_filename.replace(".txt", "")
            results["timing"] = self._save_timing_log(timing_base_filename, timing_data)
        else:
            if self.unified_logger:
                self.unified_logger.info("ℹ️  Timing logs disabled in configuration")
            else:
                self.logger.info("ℹ️  Timing logs disabled in configuration")

        return results

    def should_generate_html(self) -> bool:
        """Check if HTML generation is enabled."""
        return self.output_control.get("generate_html", True)

    def should_generate_png(self) -> bool:
        """Check if PNG generation is enabled."""
        return self.output_control.get("generate_png", True)

    def should_generate_reports(self) -> bool:
        """Check if report generation is enabled."""
        return self.output_control.get("generate_reports", True)

    def should_generate_timing_logs(self) -> bool:
        """Check if timing log generation is enabled."""
        return self.output_control.get("enable_timing_logs", False)

    def get_enabled_formats(self) -> List[str]:
        """Get list of enabled output formats."""
        enabled = []
        if self.should_generate_html():
            enabled.append("HTML")
        if self.should_generate_png():
            enabled.append("PNG")
        if self.should_generate_reports():
            enabled.append("Reports")
        if self.should_generate_timing_logs():
            enabled.append("Timing Logs")
        return enabled

    def validate_output_configuration(self) -> List[str]:
        """Validate output configuration and return any errors."""
        errors = []

        # Check that at least one output format is enabled
        if not any(
            [
                self.should_generate_html(),
                self.should_generate_png(),
                self.should_generate_reports(),
            ]
        ):
            errors.append(
                "At least one output format (HTML, PNG, or Reports) must be enabled"
            )

        # Check output directory permissions
        from ..core.config import _get_default_output_prefix

        output_prefix = self.config.get(
            "output_file_prefix", _get_default_output_prefix()
        )
        output_dir = os.path.dirname(output_prefix)
        if (
            output_dir
            and os.path.exists(output_dir)
            and not os.access(output_dir, os.W_OK)
        ):
            errors.append(f"Output directory is not writable: {output_dir}")

        return errors

    def _save_timing_log(self, output_path: str, timing_data: Dict[str, float]) -> bool:
        """Save detailed timing information to a log file."""
        try:
            # Create timing log filename with same base as other outputs
            timing_filename = f"{output_path}_timing.txt"

            # Ensure output directory exists
            from ..utils.files import ensure_output_directory

            ensure_output_directory(timing_filename, create_if_missing=True)

            # Generate detailed timing report
            timing_report = self._generate_detailed_timing_report(timing_data)

            # Write timing log to file
            with open(timing_filename, "w", encoding="utf-8") as f:
                f.write(timing_report)

            if self.unified_logger:
                self.unified_logger.log_success(f"Timing log saved: {timing_filename}")
            else:
                success_msg = EmojiFormatter.format(
                    "success", f"Timing log saved: {timing_filename}"
                )
                self.logger.info(success_msg)
            return True

        except Exception as e:
            if self.unified_logger:
                self.unified_logger.warning(f"Failed to save timing log: {e}")
            else:
                self.logger.warning(f"Failed to save timing log: {e}")
            return False

    def _generate_detailed_timing_report(self, timing_data: Dict[str, float]) -> str:
        """Generate a detailed timing report with structured formatting."""
        # Calculate total time
        phase_times = {k: v for k, v in timing_data.items() if k != "total"}
        total_time = timing_data.get("total", sum(phase_times.values()))

        # Create detailed timing log content
        log_lines = []
        log_lines.append("=" * 80)
        log_lines.append("FOLLOWWEB PIPELINE DETAILED TIMING LOG")
        log_lines.append("=" * 80)
        log_lines.append(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        log_lines.append("")

        # Configuration summary
        log_lines.append("CONFIGURATION SUMMARY:")
        log_lines.append("-" * 40)
        log_lines.append(f"Strategy: {self.config.get('strategy', 'Unknown')}")

        # Analysis mode information
        analysis_mode = self.config.get("analysis_mode", {})
        mode_value = analysis_mode.get("mode", "Unknown")
        log_lines.append(f"Analysis Mode: {mode_value}")

        # Pipeline stages
        pipeline_stages = self.config.get("pipeline_stages", {})
        log_lines.append("Enabled Stages:")
        log_lines.append(
            f"  - Strategy: {pipeline_stages.get('enable_strategy', True)}"
        )
        log_lines.append(
            f"  - Analysis: {pipeline_stages.get('enable_analysis', True)}"
        )
        log_lines.append(
            f"  - Visualization: {pipeline_stages.get('enable_visualization', True)}"
        )

        # Output formats
        enabled_formats = self.get_enabled_formats()
        log_lines.append(
            f"Output Formats: {', '.join(enabled_formats) if enabled_formats else 'None'}"
        )
        log_lines.append("")

        # Detailed phase breakdown
        log_lines.append("DETAILED PHASE BREAKDOWN:")
        log_lines.append("-" * 40)

        from ..utils.math import format_time_duration

        for phase_name, phase_time in phase_times.items():
            percentage = (phase_time / total_time * 100) if total_time > 0 else 0
            log_lines.append(f"{phase_name.capitalize()} Phase:")
            log_lines.append(f"  Duration: {format_time_duration(phase_time)}")
            log_lines.append(f"  Percentage: {percentage:.1f}% of total time")
            log_lines.append(f"  Start-to-end: {phase_time:.3f} seconds")
            log_lines.append("")

        # Performance summary
        log_lines.append("PERFORMANCE SUMMARY:")
        log_lines.append("-" * 40)
        log_lines.append(f"Total Pipeline Duration: {format_time_duration(total_time)}")
        log_lines.append(f"Total Seconds: {total_time:.3f}")

        return "\n".join(log_lines)

    @staticmethod
    def get_emoji_config_from_dict(config_dict: Dict[str, Any]) -> str:
        """
        Extract emoji configuration from config dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Emoji fallback level string
        """
        try:
            return (
                config_dict.get("output_control", {})
                .get("output_formatting", {})
                .get("emoji", {})
                .get("fallback_level", "full")
            )
        except (KeyError, AttributeError):
            return "full"


class MetricsReporter:
    """
    Metrics reporter that integrates with unified output system.

    This class captures detailed analysis results from graph attributes and
    generates reports that include all the information previously
    only available in console output.
    """

    def __init__(
        self, vis_config: Dict[str, Any], logger: Optional[Logger] = None
    ) -> None:
        """
        Initialize metrics reporter.

        Args:
            vis_config: Visualization configuration dictionary
            logger: Optional logger for coordinated output
        """
        self.vis_config = vis_config
        self.logger = logger

    def generate_analysis_report(
        self,
        graph: nx.DiGraph,
        config: Dict[str, Any],
        strategy: str,
        k_value: int,
        timing_data: Dict[str, float],
        initial_graph_stats: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Generate analysis report with all console information.

        Args:
            graph: The analyzed graph with node and edge attributes
            config: Complete configuration dictionary
            strategy: Analysis strategy used
            k_value: K-value used for pruning
            timing_data: Complete timing information including all phases
            initial_graph_stats: Optional initial graph statistics

        Returns:
            Formatted text report
        """
        report_lines = []

        # Header with emoji support
        header_msg = EmojiFormatter.format(
            "completion", "FOLLOWWEB NETWORK ANALYSIS REPORT"
        )
        report_lines.append("=" * 80)
        report_lines.append(header_msg)
        report_lines.append("=" * 80)
        report_lines.append("")

        # Pipeline Configuration Section
        report_lines.extend(
            self._generate_pipeline_configuration_section(config, strategy, k_value)
        )

        # Graph Processing Summary
        report_lines.extend(
            self._generate_graph_processing_section(
                graph, initial_graph_stats, strategy, k_value
            )
        )

        # Detailed Analysis Results
        report_lines.extend(self._generate_detailed_analysis_section(graph))

        # Path Analysis Results
        report_lines.extend(self._generate_path_analysis_section(graph))

        # Famous Accounts Analysis
        report_lines.extend(self._generate_famous_accounts_section(graph))

        # Community Analysis Details
        report_lines.extend(self._generate_community_analysis_section(graph))

        # Centrality Analysis Details
        report_lines.extend(self._generate_centrality_analysis_section(graph))

        # Complete Timing Information
        report_lines.extend(self._generate_complete_timing_section(timing_data))

        # Output Generation Summary
        report_lines.extend(self._generate_output_summary_section(config))

        # Footer
        report_lines.append("=" * 80)
        footer_msg = EmojiFormatter.format(
            "timer", f"Report generated: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        report_lines.append(footer_msg)
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def _generate_pipeline_configuration_section(
        self, config: Dict[str, Any], strategy: str, k_value: int
    ) -> List[str]:
        """Generate pipeline configuration section."""
        lines: List[str] = []

        config_msg = EmojiFormatter.format("progress", "PIPELINE CONFIGURATION")
        lines.append(config_msg)
        lines.append("-" * 40)
        lines.append(f"Strategy: {strategy}")

        # Analysis mode information
        analysis_mode = config.get("analysis_mode", {})
        mode = analysis_mode.get("mode", "unknown")
        # Handle both string and enum modes
        if hasattr(mode, "value"):
            mode_str = mode.value.upper()
        else:
            mode_str = str(mode).upper()
        lines.append(f"Analysis Mode: {mode_str}")

        if analysis_mode.get("sampling_threshold"):
            lines.append(
                f"Sampling Threshold: {analysis_mode['sampling_threshold']:,} nodes"
            )
        if analysis_mode.get("max_layout_iterations"):
            lines.append(
                f"Max Layout Iterations: {analysis_mode['max_layout_iterations']:,}"
            )

        lines.append(f"K-Value: {k_value}")

        # Ego username for ego-alter analysis
        if strategy == "ego_alter_k-core":
            ego_username = config.get("ego_username", "Not specified")
            lines.append(f"Ego Username: {ego_username}")

        lines.append(f"Input File: {config.get('input_file', 'Not specified')}")
        lines.append(
            f"Output Prefix: {config.get('output_file_prefix', 'Not specified')}"
        )

        # Pipeline stages
        pipeline_stages = config.get("pipeline_stages", {})
        lines.append("")
        lines.append("ENABLED STAGES:")
        strategy_enabled = pipeline_stages.get("enable_strategy", True)
        analysis_enabled = pipeline_stages.get("enable_analysis", True)
        viz_enabled = pipeline_stages.get("enable_visualization", True)

        strategy_msg = EmojiFormatter.format(
            "success" if strategy_enabled else "error",
            f"Graph Loading & Filtering: {strategy_enabled}",
        )
        analysis_msg = EmojiFormatter.format(
            "success" if analysis_enabled else "error",
            f"Network Analysis: {analysis_enabled}",
        )
        viz_msg = EmojiFormatter.format(
            "success" if viz_enabled else "error", f"Visualization: {viz_enabled}"
        )
        lines.extend([strategy_msg, analysis_msg, viz_msg])

        # Analysis components
        if analysis_enabled:
            lines.append("")
            lines.append("ANALYSIS COMPONENTS:")
            community_enabled = pipeline_stages.get("enable_community_detection", True)
            centrality_enabled = pipeline_stages.get("enable_centrality_analysis", True)
            path_enabled = pipeline_stages.get("enable_path_analysis", True)

            community_msg = EmojiFormatter.format(
                "success" if community_enabled else "error",
                f"Community Detection: {community_enabled}",
            )
            centrality_msg = EmojiFormatter.format(
                "success" if centrality_enabled else "error",
                f"Centrality Analysis: {centrality_enabled}",
            )
            path_msg = EmojiFormatter.format(
                "success" if path_enabled else "error", f"Path Analysis: {path_enabled}"
            )
            lines.extend([community_msg, centrality_msg, path_msg])

        lines.append("")
        return lines

    def _generate_graph_processing_section(
        self,
        graph: nx.DiGraph,
        initial_stats: Dict[str, int],
        strategy: str,
        k_value: int,
    ) -> List[str]:
        """Generate graph processing summary section."""
        lines: List[str] = []

        processing_msg = EmojiFormatter.format("progress", "GRAPH PROCESSING SUMMARY")
        lines.append(processing_msg)
        lines.append("-" * 40)

        # Initial graph statistics
        if initial_stats:
            lines.append(
                f"Initial Graph: {initial_stats.get('nodes', 0):,} nodes, {initial_stats.get('edges', 0):,} edges"
            )

        # Strategy-specific processing
        lines.append(f"Applied Strategy: {strategy}")
        if strategy == "reciprocal_k-core":
            lines.append("  → Filtered for mutual connections only")
        elif strategy == "ego_alter_k-core":
            lines.append("  → Created ego-alter network")
        elif strategy == "k-core":
            lines.append("  → Used full network k-core analysis")

        # K-core pruning
        lines.append(f"K-Core Pruning: k={k_value} (minimum connections required)")

        # Final graph statistics
        final_nodes = graph.number_of_nodes()
        final_edges = graph.number_of_edges()
        lines.append(
            f"Final Processed Graph: {final_nodes:,} nodes, {final_edges:,} edges"
        )

        # Calculate density and average degree
        if final_nodes > 1:
            max_edges = final_nodes * (final_nodes - 1)
            density = final_edges / max_edges
            lines.append(f"Graph Density: {density:.6f}")

        if final_nodes > 0:
            avg_degree = sum(dict(graph.degree()).values()) / final_nodes
            lines.append(f"Average Degree: {avg_degree:.2f}")

        lines.append("")
        return lines

    def _generate_detailed_analysis_section(self, graph: nx.DiGraph) -> List[str]:
        """Generate detailed analysis results section."""
        lines: List[str] = []

        # Check if detailed results are stored in graph attributes
        if not hasattr(graph, "graph") or "detailed_results" not in graph.graph:
            return lines

        detailed_results = graph.graph["detailed_results"]

        analysis_msg = EmojiFormatter.format("chart", "DETAILED ANALYSIS RESULTS")
        lines.append(analysis_msg)
        lines.append("-" * 40)

        # Top nodes by centrality metrics
        if "top_nodes" in detailed_results:
            top_nodes = detailed_results["top_nodes"]

            if "by_degree" in top_nodes:
                lines.append("TOP 10 NODES BY DEGREE CENTRALITY:")
                for i, (node, degree) in enumerate(top_nodes["by_degree"][:10], 1):
                    lines.append(f"  {i:2d}. {node}: {degree}")
                lines.append("")

            if "by_betweenness" in top_nodes:
                lines.append("TOP 10 NODES BY BETWEENNESS CENTRALITY:")
                for i, (node, betweenness) in enumerate(
                    top_nodes["by_betweenness"][:10], 1
                ):
                    lines.append(f"  {i:2d}. {node}: {betweenness:.6f}")
                lines.append("")

            if "by_eigenvector" in top_nodes:
                lines.append("TOP 10 NODES BY EIGENVECTOR CENTRALITY:")
                for i, (node, eigenvector) in enumerate(
                    top_nodes["by_eigenvector"][:10], 1
                ):
                    lines.append(f"  {i:2d}. {node}: {eigenvector:.6f}")
                lines.append("")

        return lines

    def _generate_path_analysis_section(self, graph: nx.DiGraph) -> List[str]:
        """Generate path analysis results section."""
        lines: List[str] = []

        # Check if path analysis results are stored
        if not hasattr(graph, "graph") or "path_analysis" not in graph.graph:
            return lines

        path_data = graph.graph["path_analysis"]

        path_msg = EmojiFormatter.format("search", "PATH ANALYSIS RESULTS")
        lines.append(path_msg)
        lines.append("-" * 40)

        if "average_shortest_path_length" in path_data:
            lines.append(
                f"Average Shortest Path Length: {path_data['average_shortest_path_length']:.2f}"
            )

        if "diameter" in path_data:
            lines.append(f"Network Diameter: {path_data['diameter']}")

        if "connected_components" in path_data:
            lines.append(f"Connected Components: {path_data['connected_components']}")

        # Path length distribution
        if "path_length_distribution" in path_data:
            lines.append("")
            lines.append("PATH LENGTH DISTRIBUTION:")
            distribution = path_data["path_length_distribution"]
            total_paths = sum(distribution.values())

            for length in sorted(distribution.keys()):
                count = distribution[length]
                percentage = (count / total_paths * 100) if total_paths > 0 else 0
                lines.append(f"  Length {length}: {count:,} paths ({percentage:.1f}%)")

        # Degrees of separation
        if "degrees_of_separation" in path_data:
            lines.append("")
            lines.append("DEGREES OF SEPARATION:")
            degrees = path_data["degrees_of_separation"]
            for degree, info in degrees.items():
                lines.append(f"  {degree}: {info}")

        lines.append("")
        return lines

    def _generate_famous_accounts_section(self, graph: nx.DiGraph) -> List[str]:
        """Generate famous accounts analysis section."""
        lines: List[str] = []

        # Check if famous accounts data is stored
        if not hasattr(graph, "graph") or "famous_accounts" not in graph.graph:
            return lines

        famous_data = graph.graph["famous_accounts"]

        famous_msg = EmojiFormatter.format("completion", "FAMOUS ACCOUNTS ANALYSIS")
        lines.append(famous_msg)
        lines.append("-" * 40)

        unreachable = famous_data.get("unreachable_famous", [])
        reachable = famous_data.get("reachable_famous", [])
        total_famous = len(unreachable) + len(reachable)

        if total_famous == 0:
            lines.append("No famous accounts found matching criteria")
            lines.append("")
            return lines

        lines.append(f"Found {total_famous} famous accounts:")
        lines.append(f"  - {len(unreachable)} unreachable (follow nobody)")
        lines.append(f"  - {len(reachable)} reachable (follow others)")
        lines.append("")

        # Top unreachable famous accounts
        if unreachable:
            lines.append("TOP UNREACHABLE FAMOUS ACCOUNTS:")
            for i, account in enumerate(unreachable[:10], 1):
                lines.append(
                    f"  {i:2d}. {account['username']} "
                    f"(followers: {account['followers_in_network']:,}, "
                    f"ratio: {account['ratio']:.1f})"
                )
            lines.append("")

        # Top reachable famous accounts
        if reachable:
            lines.append("TOP REACHABLE FAMOUS ACCOUNTS:")
            for i, account in enumerate(reachable[:10], 1):
                lines.append(
                    f"  {i:2d}. {account['username']} "
                    f"(followers: {account['followers_in_network']:,}, "
                    f"following: {account['following_in_network']:,}, "
                    f"ratio: {account['ratio']:.1f})"
                )
            lines.append("")

        return lines

    def _generate_community_analysis_section(self, graph: nx.DiGraph) -> List[str]:
        """Generate detailed community analysis section."""
        lines: List[str] = []

        communities_attr = nx.get_node_attributes(graph, "community")
        if not communities_attr:
            return lines

        community_msg = EmojiFormatter.format("chart", "COMMUNITY ANALYSIS DETAILS")
        lines.append(community_msg)
        lines.append("-" * 40)

        # Community statistics
        community_counts = {}
        for _node, community in communities_attr.items():
            community_counts[community] = community_counts.get(community, 0) + 1

        num_communities = len(community_counts)
        lines.append(f"Number of Communities: {num_communities}")

        if community_counts:
            largest_community = max(community_counts.values())
            smallest_community = min(community_counts.values())
            avg_community_size = sum(community_counts.values()) / len(community_counts)

            lines.append(f"Largest Community Size: {largest_community:,} nodes")
            lines.append(f"Smallest Community Size: {smallest_community:,} nodes")
            lines.append(f"Average Community Size: {avg_community_size:.1f} nodes")
            lines.append("")

            # All communities by size
            lines.append("ALL COMMUNITIES BY SIZE:")
            sorted_communities = sorted(
                community_counts.items(), key=lambda x: x[1], reverse=True
            )
            for i, (comm_id, size) in enumerate(sorted_communities, 1):
                percentage = size / sum(community_counts.values()) * 100
                lines.append(
                    f"  {i:2d}. Community {comm_id}: {size:,} nodes ({percentage:.1f}%)"
                )

        lines.append("")
        return lines

    def _generate_centrality_analysis_section(self, graph: nx.DiGraph) -> List[str]:
        """Generate detailed centrality analysis section."""
        lines: List[str] = []

        centrality_msg = EmojiFormatter.format("chart", "CENTRALITY ANALYSIS DETAILS")
        lines.append(centrality_msg)
        lines.append("-" * 40)

        # Degree centrality
        degree_centrality = nx.get_node_attributes(graph, "degree")
        if degree_centrality:
            max_degree = max(degree_centrality.values())
            min_degree = min(degree_centrality.values())
            avg_degree = sum(degree_centrality.values()) / len(degree_centrality)
            lines.append("DEGREE CENTRALITY:")
            lines.append(f"  Maximum: {max_degree}")
            lines.append(f"  Minimum: {min_degree}")
            lines.append(f"  Average: {avg_degree:.2f}")
            lines.append("")

        # Betweenness centrality
        betweenness_centrality = nx.get_node_attributes(graph, "betweenness")
        if betweenness_centrality:
            max_betweenness = max(betweenness_centrality.values())
            min_betweenness = min(betweenness_centrality.values())
            avg_betweenness = sum(betweenness_centrality.values()) / len(
                betweenness_centrality
            )
            lines.append("BETWEENNESS CENTRALITY:")
            lines.append(f"  Maximum: {max_betweenness:.6f}")
            lines.append(f"  Minimum: {min_betweenness:.6f}")
            lines.append(f"  Average: {avg_betweenness:.6f}")
            lines.append("")

        # Eigenvector centrality
        eigenvector_centrality = nx.get_node_attributes(graph, "eigenvector")
        if eigenvector_centrality:
            max_eigenvector = max(eigenvector_centrality.values())
            min_eigenvector = min(eigenvector_centrality.values())
            avg_eigenvector = sum(eigenvector_centrality.values()) / len(
                eigenvector_centrality
            )
            lines.append("EIGENVECTOR CENTRALITY:")
            lines.append(f"  Maximum: {max_eigenvector:.6f}")
            lines.append(f"  Minimum: {min_eigenvector:.6f}")
            lines.append(f"  Average: {avg_eigenvector:.6f}")
            lines.append("")

        return lines

    def _generate_complete_timing_section(
        self, timing_data: Dict[str, float]
    ) -> List[str]:
        """Generate complete timing information section."""
        lines: List[str] = []

        if not timing_data:
            return lines

        timing_msg = EmojiFormatter.format("timer", "COMPLETE PERFORMANCE TIMING")
        lines.append(timing_msg)
        lines.append("-" * 40)

        # Filter out 'total' for phase breakdown
        phase_times = {k: v for k, v in timing_data.items() if k != "total"}
        total_time = timing_data.get("total", sum(phase_times.values()))

        from ..utils.math import format_time_duration

        lines.append(f"Total Execution Time: {format_time_duration(total_time)}")
        lines.append("")
        lines.append("PHASE BREAKDOWN:")

        for phase_name, phase_time in phase_times.items():
            percentage = (phase_time / total_time * 100) if total_time > 0 else 0
            phase_msg = EmojiFormatter.format(
                "timer",
                f"{phase_name.replace('_', ' ').title()}: {format_time_duration(phase_time)} ({percentage:.1f}%)",
            )
            lines.append(f"  {phase_msg}")

        lines.append("")
        return lines

    def _generate_output_summary_section(self, config: Dict[str, Any]) -> List[str]:
        """Generate output generation summary section."""
        lines: List[str] = []

        output_control = config.get("output_control", {})

        output_msg = EmojiFormatter.format("completion", "OUTPUT GENERATION SUMMARY")
        lines.append(output_msg)
        lines.append("-" * 40)

        # Output formats
        html_enabled = output_control.get("generate_html", True)
        png_enabled = output_control.get("generate_png", True)
        reports_enabled = output_control.get("generate_reports", True)
        timing_enabled = output_control.get("enable_timing_logs", False)

        html_msg = EmojiFormatter.format(
            "success" if html_enabled else "error", f"Interactive HTML: {html_enabled}"
        )
        png_msg = EmojiFormatter.format(
            "success" if png_enabled else "error", f"Static PNG: {png_enabled}"
        )
        reports_msg = EmojiFormatter.format(
            "success" if reports_enabled else "error",
            f"Text Reports: {reports_enabled}",
        )
        timing_msg = EmojiFormatter.format(
            "success" if timing_enabled else "error", f"Timing Logs: {timing_enabled}"
        )

        lines.extend([html_msg, png_msg, reports_msg, timing_msg])
        lines.append("")

        return lines

    def save_metrics_file(self, report_content: str, output_path: str) -> bool:
        """
        Saves the metrics report to a text file.

        Args:
            report_content: The formatted report content to save
            output_path: Path where the text file should be saved (should end with .txt)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            from ..utils.files import ensure_output_directory

            ensure_output_directory(output_path, create_if_missing=True)

            # Write the report content to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            success_msg = EmojiFormatter.format(
                "success", f"Metrics report saved: {output_path}"
            )
            if self.logger:
                self.logger.log_success(f"Metrics report saved: {output_path}")
            else:
                print(success_msg)
            return True

        except PermissionError as e:
            error_msg = f"Permission denied writing to {output_path}: {e}"
            if self.logger:
                self.logger.log_error(error_msg)
            else:
                print(EmojiFormatter.format("error", error_msg))
            return False
        except OSError as e:
            error_msg = f"Failed to write metrics file {output_path}: {e}"
            if self.logger:
                self.logger.log_error(error_msg)
            else:
                print(EmojiFormatter.format("error", error_msg))
            return False
        except Exception as e:
            error_msg = f"Unexpected error saving metrics file {output_path}: {e}"
            if self.logger:
                self.logger.log_error(error_msg)
            else:
                print(EmojiFormatter.format("error", error_msg))
            return False
