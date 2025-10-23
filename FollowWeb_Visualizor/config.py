"""
Configuration management module for FollowWeb network analysis system.

This module provides centralized configuration management with comprehensive validation,
default values, and clear error messages for all analysis parameters.

Transformed from notebook CONFIG dictionary to professional package structure.
"""

import os
import json
import logging
import argparse
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any, Union, List, Tuple
from pathlib import Path
from enum import Enum


class AnalysisMode(Enum):
    """Analysis depth modes with different performance characteristics."""
    FAST = "fast"      # Optimized algorithms, reduced precision
    MEDIUM = "medium"  # Balanced analysis and performance
    FULL = "full"      # Comprehensive analysis, maximum precision


@dataclass
class PipelineStagesConfig:
    """Configuration for pipeline stage execution control."""
    enable_strategy: bool = True
    enable_analysis: bool = True
    enable_visualization: bool = True
    enable_community_detection: bool = True
    enable_centrality_analysis: bool = True
    enable_path_analysis: bool = True

    def __post_init__(self):
        """Validate pipeline stages configuration after initialization."""
        # Note: Stage dependency validation is handled by validate_stage_dependencies()
        # to allow for more flexible validation during configuration loading
        pass


@dataclass
class AnalysisModeConfig:
    """Configuration for analysis depth and performance modes."""
    mode: AnalysisMode = AnalysisMode.FULL
    sampling_threshold: int = 5000
    max_layout_iterations: Optional[int] = None
    enable_fast_algorithms: bool = False
    
    def __post_init__(self):
        """Validate analysis mode configuration after initialization."""
        if not isinstance(self.mode, AnalysisMode):
            raise ValueError(f"mode must be an AnalysisMode enum value, got {type(self.mode)}")
        
        if self.sampling_threshold < 100:
            raise ValueError("sampling_threshold must be at least 100")
        
        if self.max_layout_iterations is not None and self.max_layout_iterations < 1:
            raise ValueError("max_layout_iterations must be positive when specified")
        
        # Auto-configure fast algorithms based on mode
        if self.mode == AnalysisMode.FAST:
            self.enable_fast_algorithms = True
        elif self.mode == AnalysisMode.FULL:
            self.enable_fast_algorithms = False


@dataclass
class OutputFormattingConfig:
    """Configuration for output display formatting."""
    indent_size: int = 2
    group_related_settings: bool = True
    highlight_key_values: bool = True
    use_human_readable_labels: bool = True

    def __post_init__(self):
        """Validate output formatting configuration after initialization."""
        if self.indent_size < 0:
            raise ValueError("indent_size cannot be negative")


@dataclass
class OutputControlConfig:
    """Configuration for output generation control."""
    generate_html: bool = True
    generate_png: bool = True
    generate_reports: bool = True
    enable_timing_logs: bool = False
    output_formatting: OutputFormattingConfig = field(default_factory=OutputFormattingConfig)

    def __post_init__(self):
        """Validate output control configuration after initialization."""
        # Ensure at least one output format is enabled
        if not any([self.generate_html, self.generate_png, self.generate_reports]):
            raise ValueError("At least one output format must be enabled. "
                           "Set generate_html, generate_png, or generate_reports to true in output_control section, "
                           "or use CLI flags: --no-png, --no-html, --no-reports (but keep at least one enabled)")


@dataclass
class KValueConfig:
    """Configuration for k-core analysis parameters."""
    strategy_k_values: Dict[str, int] = field(default_factory=lambda: {
        "k-core": 1,
        "reciprocal_k-core": 6,
        "ego_alter_k-core": 3
    })
    default_k_value: int = 2
    allow_cli_override: bool = True

    def __post_init__(self):
        """Validate k-value configuration after initialization."""
        # Validate all k-values are non-negative
        for strategy, k_val in self.strategy_k_values.items():
            if k_val < 0:
                raise ValueError(f"k-value for '{strategy}' cannot be negative: {k_val}")
        
        if self.default_k_value < 0:
            raise ValueError("default_k_value cannot be negative")
        
        # Validate strategy names
        valid_strategies = ['k-core', 'reciprocal_k-core', 'ego_alter_k-core']
        for strategy in self.strategy_k_values.keys():
            if strategy not in valid_strategies:
                raise ValueError(f"Invalid strategy '{strategy}'. Must be one of: {valid_strategies}")


@dataclass
class StaticImageConfig:
    """Configuration for static PNG image generation."""
    generate: bool = True
    layout: str = "spring"
    width: int = 1200
    height: int = 800
    dpi: int = 300
    with_labels: bool = False
    font_size: int = 8
    image_size_inches: Tuple[int, int] = (25, 25)
    spring_k: float = 0.3
    spring_iterations: int = 50
    edge_alpha: float = 0.3
    node_alpha: float = 0.8
    edge_arrow_size: int = 8
    show_legend: bool = True

    def __post_init__(self):
        """Validate static image configuration after initialization."""
        valid_layouts = ['spring', 'circular', 'kamada_kawai', 'random', 'shell']
        if self.layout not in valid_layouts:
            raise ValueError(f"Invalid layout '{self.layout}'. Must be one of: {valid_layouts}")
        
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Image dimensions must be positive")
        
        if self.dpi <= 0:
            raise ValueError("DPI must be positive")
        
        if self.font_size <= 0:
            raise ValueError("Font size must be positive")
        
        if len(self.image_size_inches) != 2 or any(dim <= 0 for dim in self.image_size_inches):
            raise ValueError("image_size_inches must be a tuple of two positive numbers")
        
        if not (0.0 <= self.edge_alpha <= 1.0):
            raise ValueError("edge_alpha must be between 0.0 and 1.0")
        
        if not (0.0 <= self.node_alpha <= 1.0):
            raise ValueError("node_alpha must be between 0.0 and 1.0")


@dataclass
class PyvisInteractiveConfig:
    """Configuration for Pyvis interactive HTML generation."""
    height: str = "90vh"
    width: str = "100%"
    bgcolor: str = "#ffffff"
    font_color: str = "#000000"
    notebook: bool = False
    show_labels: bool = True
    show_tooltips: bool = True
    physics_solver: str = "forceAtlas2Based"
    
    def __post_init__(self):
        """Validate Pyvis configuration after initialization."""
        # Basic validation for height and width format
        if not (self.height.endswith('px') or self.height.endswith('%') or self.height.endswith('vh')):
            raise ValueError("Height must end with 'px', '%', or 'vh'")
        
        if not (self.width.endswith('px') or self.width.endswith('%')):
            raise ValueError("Width must end with 'px' or '%'")
        
        valid_solvers = ["forceAtlas2Based", "repulsion", "hierarchicalRepulsion", "barnesHut"]
        if self.physics_solver not in valid_solvers:
            raise ValueError(f"Invalid physics_solver '{self.physics_solver}'. Must be one of: {valid_solvers}")


@dataclass
class VisualizationConfig:
    """Configuration for visualization generation."""
    node_size_metric: str = "degree"
    base_node_size: float = 6.0
    node_size_multiplier: float = 5.0
    scaling_algorithm: str = "logarithmic"
    edge_thickness_metric: str = "weight"
    base_edge_thickness: float = 1.0
    base_edge_width: float = 0.5
    edge_width_multiplier: float = 2.0
    edge_width_scaling: str = "logarithmic"
    bridge_color: str = "#6e6e6e"
    intra_community_color: str = "#c0c0c0"
    static_image: StaticImageConfig = field(default_factory=StaticImageConfig)
    pyvis_interactive: PyvisInteractiveConfig = field(default_factory=PyvisInteractiveConfig)
    
    def __post_init__(self):
        """Validate visualization configuration after initialization."""
        valid_node_metrics = ['degree', 'betweenness', 'eigenvector', 'closeness']
        if self.node_size_metric not in valid_node_metrics:
            raise ValueError(f"Invalid node_size_metric '{self.node_size_metric}'. Must be one of: {valid_node_metrics}")
        
        valid_edge_metrics = ['weight', 'betweenness']
        if self.edge_thickness_metric not in valid_edge_metrics:
            raise ValueError(f"Invalid edge_thickness_metric '{self.edge_thickness_metric}'. Must be one of: {valid_edge_metrics}")
        
        valid_scaling_algorithms = ['logarithmic', 'linear']
        if self.scaling_algorithm not in valid_scaling_algorithms:
            raise ValueError(f"Invalid scaling_algorithm '{self.scaling_algorithm}'. Must be one of: {valid_scaling_algorithms}")
        
        if self.edge_width_scaling not in valid_scaling_algorithms:
            raise ValueError(f"Invalid edge_width_scaling '{self.edge_width_scaling}'. Must be one of: {valid_scaling_algorithms}")
        
        if self.base_node_size <= 0:
            raise ValueError("base_node_size must be positive")
        
        if self.node_size_multiplier <= 0:
            raise ValueError("node_size_multiplier must be positive")
        
        if self.base_edge_thickness <= 0:
            raise ValueError("base_edge_thickness must be positive")
        
        if self.base_edge_width <= 0:
            raise ValueError("base_edge_width must be positive")
        
        if self.edge_width_multiplier <= 0:
            raise ValueError("edge_width_multiplier must be positive")


@dataclass
class OutputConfig:
    """Configuration for output generation."""
    custom_output_directory: Optional[str] = None
    create_directories: bool = True
    enable_time_logging: bool = False

    def __post_init__(self):
        """Validate output configuration after initialization."""
        if self.custom_output_directory and not isinstance(self.custom_output_directory, str):
            raise ValueError("custom_output_directory must be a string")


@dataclass
class FollowWebConfig:
    """Main configuration class containing all FollowWeb analysis settings."""
    input_file: str = "followers_following.json"
    output_file_prefix: str = "Output/FollowWeb"
    
    # Core configuration sections
    pipeline_stages: PipelineStagesConfig = field(default_factory=PipelineStagesConfig)
    analysis_mode: AnalysisModeConfig = field(default_factory=AnalysisModeConfig)
    output_control: OutputControlConfig = field(default_factory=OutputControlConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    k_values: KValueConfig = field(default_factory=KValueConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)
    
    # Essential analysis settings (transformed from notebook CONFIG)
    strategy: str = "k-core"
    ego_username: Optional[str] = None
    contact_path_target: Optional[str] = None
    find_paths_to_all_famous: bool = True
    min_followers_in_network: int = 5
    min_fame_ratio: float = 5.0
    skip_analysis: bool = False  # From notebook pipeline.skip_analysis

    def __post_init__(self):
        """Validate main configuration after initialization."""
        # Validate strategy
        valid_strategies = ['k-core', 'reciprocal_k-core', 'ego_alter_k-core']
        if self.strategy not in valid_strategies:
            raise ValueError(f"Invalid strategy '{self.strategy}'. Must be one of: {valid_strategies}")
        
        if self.strategy == "ego_alter_k-core" and not self.ego_username:
            raise ValueError("'ego_username' must be set for 'ego_alter_k-core' strategy. "
                           "Set ego_username in configuration file or use --ego-username CLI parameter")
        
        # Validate fame analysis parameters
        if self.min_followers_in_network < 0:
            raise ValueError("min_followers_in_network cannot be negative")
        if self.min_fame_ratio <= 0:
            raise ValueError("min_fame_ratio must be positive")
        
        # Sync skip_analysis with pipeline stages
        if self.skip_analysis:
            self.pipeline_stages.enable_analysis = False


def load_config_from_dict(config_dict: Dict[str, Any]) -> FollowWebConfig:
    """
    Creates a FollowWebConfig instance from a dictionary.
    
    Args:
        config_dict: Configuration dictionary (can be from notebook CONFIG format).
        
    Returns:
        FollowWebConfig: Validated configuration instance.
        
    Raises:
        ValueError: If configuration validation fails.
    """
    try:
        # Handle notebook CONFIG format transformation
        transformed_dict = _transform_notebook_config(config_dict)
        
        # Extract configuration sections
        pipeline_stages_dict = transformed_dict.get("pipeline_stages", {})
        analysis_mode_dict = transformed_dict.get("analysis_mode", {})
        output_control_dict = transformed_dict.get("output_control", {})
        output_dict = transformed_dict.get("output", {})
        k_values_dict = transformed_dict.get("k_values", {})
        
        # Create pipeline stages config
        pipeline_stages_config = PipelineStagesConfig(
            enable_strategy=pipeline_stages_dict.get("enable_strategy", True),
            enable_analysis=pipeline_stages_dict.get("enable_analysis", True),
            enable_visualization=pipeline_stages_dict.get("enable_visualization", True),
            enable_community_detection=pipeline_stages_dict.get("enable_community_detection", True),
            enable_centrality_analysis=pipeline_stages_dict.get("enable_centrality_analysis", True),
            enable_path_analysis=pipeline_stages_dict.get("enable_path_analysis", True)
        )
        
        # Handle analysis mode - convert string to enum if needed
        mode_value = analysis_mode_dict.get("mode", "full")
        if isinstance(mode_value, str):
            try:
                analysis_mode = AnalysisMode(mode_value.lower())
            except ValueError:
                raise ValueError(f"Invalid analysis mode '{mode_value}'. Must be one of: fast, medium, full. "
                               "Use --fast-mode, --medium-mode, or --full-mode CLI flags, "
                               "or set analysis_mode.mode in configuration file")
        elif isinstance(mode_value, AnalysisMode):
            analysis_mode = mode_value
        else:
            raise ValueError(f"Invalid analysis mode type: {type(mode_value)}")
        
        analysis_mode_config = AnalysisModeConfig(
            mode=analysis_mode,
            sampling_threshold=analysis_mode_dict.get("sampling_threshold", 5000),
            max_layout_iterations=analysis_mode_dict.get("max_layout_iterations"),
            enable_fast_algorithms=analysis_mode_dict.get("enable_fast_algorithms", False)
        )
        
        # Create output formatting config
        output_formatting_dict = output_control_dict.get("output_formatting", {})
        output_formatting_config = OutputFormattingConfig(
            indent_size=output_formatting_dict.get("indent_size", 2),
            group_related_settings=output_formatting_dict.get("group_related_settings", True),
            highlight_key_values=output_formatting_dict.get("highlight_key_values", True),
            use_human_readable_labels=output_formatting_dict.get("use_human_readable_labels", True)
        )
        
        output_control_config = OutputControlConfig(
            generate_html=output_control_dict.get("generate_html", True),
            generate_png=output_control_dict.get("generate_png", True),
            generate_reports=output_control_dict.get("generate_reports", True),
            enable_timing_logs=output_control_dict.get("enable_timing_logs", False),
            output_formatting=output_formatting_config
        )
        
        # Create output config
        output_config = OutputConfig(
            custom_output_directory=output_dict.get("custom_output_directory"),
            create_directories=output_dict.get("create_directories", True),
            enable_time_logging=output_dict.get("enable_time_logging", False)
        )
        
        k_values_config = KValueConfig(
            strategy_k_values=k_values_dict.get("strategy_k_values", {
                "k-core": 1,
                "reciprocal_k-core": 6,
                "ego_alter_k-core": 3
            }),
            default_k_value=k_values_dict.get("default_k_value", 2),
            allow_cli_override=k_values_dict.get("allow_cli_override", True)
        )
        
        # Create visualization config
        visualization_dict = transformed_dict.get("visualization", {})
        
        # Create static image config
        static_image_dict = visualization_dict.get("static_image", {})
        static_image_config = StaticImageConfig(
            generate=static_image_dict.get("generate", True),
            layout=static_image_dict.get("layout", "spring"),
            width=static_image_dict.get("width", 1200),
            height=static_image_dict.get("height", 800),
            dpi=static_image_dict.get("dpi", 300),
            with_labels=static_image_dict.get("with_labels", False),
            font_size=static_image_dict.get("font_size", 8),
            image_size_inches=tuple(static_image_dict.get("image_size_inches", (25, 25))),
            spring_k=static_image_dict.get("spring_k", 0.3),
            spring_iterations=static_image_dict.get("spring_iterations", 50),
            edge_alpha=static_image_dict.get("edge_alpha", 0.3),
            node_alpha=static_image_dict.get("node_alpha", 0.8),
            edge_arrow_size=static_image_dict.get("edge_arrow_size", 8),
            show_legend=static_image_dict.get("show_legend", True)
        )
        
        # Create pyvis interactive config
        pyvis_dict = visualization_dict.get("pyvis_interactive", {})
        pyvis_config = PyvisInteractiveConfig(
            height=pyvis_dict.get("height", "90vh"),
            width=pyvis_dict.get("width", "100%"),
            bgcolor=pyvis_dict.get("bgcolor", "#ffffff"),
            font_color=pyvis_dict.get("font_color", "#000000"),
            notebook=pyvis_dict.get("notebook", False),
            show_labels=pyvis_dict.get("show_labels", True),
            show_tooltips=pyvis_dict.get("show_tooltips", True),
            physics_solver=pyvis_dict.get("physics_solver", "forceAtlas2Based")
        )
        
        visualization_config = VisualizationConfig(
            node_size_metric=visualization_dict.get("node_size_metric", "degree"),
            base_node_size=visualization_dict.get("base_node_size", 6.0),
            node_size_multiplier=visualization_dict.get("node_size_multiplier", 5.0),
            scaling_algorithm=visualization_dict.get("scaling_algorithm", "logarithmic"),
            edge_thickness_metric=visualization_dict.get("edge_thickness_metric", "weight"),
            base_edge_thickness=visualization_dict.get("base_edge_thickness", 1.0),
            base_edge_width=visualization_dict.get("base_edge_width", 0.5),
            edge_width_multiplier=visualization_dict.get("edge_width_multiplier", 2.0),
            edge_width_scaling=visualization_dict.get("edge_width_scaling", "logarithmic"),
            bridge_color=visualization_dict.get("bridge_color", "#6e6e6e"),
            intra_community_color=visualization_dict.get("intra_community_color", "#c0c0c0"),
            static_image=static_image_config,
            pyvis_interactive=pyvis_config
        )
        
        # Create main config
        config = FollowWebConfig(
            input_file=transformed_dict.get("input_file", "followers_following.json"),
            output_file_prefix=transformed_dict.get("output_file_prefix", "Output/FollowWeb"),
            pipeline_stages=pipeline_stages_config,
            analysis_mode=analysis_mode_config,
            output_control=output_control_config,
            output=output_config,
            k_values=k_values_config,
            visualization=visualization_config,
            strategy=transformed_dict.get("strategy", "k-core"),
            ego_username=transformed_dict.get("ego_username"),
            contact_path_target=transformed_dict.get("contact_path_target"),
            find_paths_to_all_famous=transformed_dict.get("find_paths_to_all_famous", True),
            min_followers_in_network=transformed_dict.get("min_followers_in_network", 5),
            min_fame_ratio=transformed_dict.get("min_fame_ratio", 5.0),
            skip_analysis=transformed_dict.get("skip_analysis", False)
        )
        
        return config
        
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


def _transform_notebook_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform notebook CONFIG format to package configuration format.
    
    Args:
        config_dict: Configuration dictionary in notebook format
        
    Returns:
        Dict[str, Any]: Transformed configuration dictionary
    """
    # If already in package format, return as-is
    if "pipeline_stages" in config_dict:
        return config_dict
    
    # Transform notebook CONFIG format
    transformed = config_dict.copy()
    
    # Extract pipeline configuration
    pipeline_config = config_dict.get("pipeline", {})
    if pipeline_config:
        transformed["strategy"] = pipeline_config.get("strategy", "k-core")
        transformed["ego_username"] = pipeline_config.get("ego_username")
        transformed["skip_analysis"] = pipeline_config.get("skip_analysis", False)
    
    # Extract analysis configuration
    analysis_config = config_dict.get("analysis", {})
    if analysis_config:
        transformed["contact_path_target"] = analysis_config.get("contact_path_target")
    
    # Extract fame analysis configuration
    fame_config = config_dict.get("fame_analysis", {})
    if fame_config:
        transformed["find_paths_to_all_famous"] = fame_config.get("find_paths_to_all_famous", True)
        transformed["min_followers_in_network"] = fame_config.get("min_followers_in_network", 5)
        transformed["min_fame_ratio"] = fame_config.get("min_fame_ratio", 5.0)
    
    # Transform pruning configuration to k_values
    pruning_config = config_dict.get("pruning", {})
    if pruning_config:
        transformed["k_values"] = {
            "strategy_k_values": pruning_config.get("k_values", {
                "k-core": 1,
                "reciprocal_k-core": 6,
                "ego_alter_k-core": 3
            }),
            "default_k_value": pruning_config.get("default_k_value", 2),
            "allow_cli_override": True
        }
    
    return transformed


class ConfigurationManager:
    """
    Enhanced configuration management with validation and merging capabilities.
    
    This class provides comprehensive configuration management including:
    - Loading from files and CLI arguments
    - Configuration validation with detailed error reporting
    - Configuration merging with proper precedence
    - JSON configuration file support
    - CLI argument parsing with argparse
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.logger = logging.getLogger(__name__)
    
    def load_configuration(
        self, 
        config_file: Optional[str] = None, 
        cli_args: Optional[Dict] = None
    ) -> FollowWebConfig:
        """
        Load configuration from file and CLI arguments with validation.
        
        Args:
            config_file: Optional path to configuration file
            cli_args: Optional dictionary of CLI argument overrides
            
        Returns:
            FollowWebConfig: Validated configuration instance
            
        Raises:
            ValueError: If configuration validation fails
            FileNotFoundError: If config file doesn't exist
        """
        # Start with default configuration
        default_config = FollowWebConfig()
        base_config = self._serialize_configuration(default_config)
        
        # Load from file if specified
        if config_file:
            if not os.path.exists(config_file):
                raise FileNotFoundError(f"Configuration file not found: {config_file}")
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                
                # Merge file configuration with defaults
                base_config = self._merge_configurations(base_config, file_config)
                
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in configuration file {config_file}: {e}")
            except Exception as e:
                raise ValueError(f"Failed to load configuration from {config_file}: {e}")
        
        # Apply CLI overrides if provided
        if cli_args:
            base_config = self._merge_configurations(base_config, cli_args)
        
        # Create and validate configuration object
        config = load_config_from_dict(base_config)
        
        # Perform file existence validation
        self._validate_file_existence(config)
        
        return config
    
    def create_cli_parser(self) -> argparse.ArgumentParser:
        """
        Create command-line argument parser for configuration overrides.
        
        Returns:
            argparse.ArgumentParser: Configured argument parser
        """
        parser = argparse.ArgumentParser(
            description="FollowWeb Network Analysis Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  followweb --input data.json --strategy k-core
  followweb --config my_config.json --ego-username myuser
  followweb --no-png --fast-mode
            """
        )
        
        # Input/Output arguments
        parser.add_argument(
            "--input", "--input-file",
            dest="input_file",
            help="Path to input JSON file (default: followers_following.json)"
        )
        
        parser.add_argument(
            "--output", "--output-prefix",
            dest="output_file_prefix",
            help="Output file prefix (default: Output/FollowWeb)"
        )
        
        parser.add_argument(
            "--config",
            dest="config_file",
            help="Path to JSON configuration file"
        )
        
        # Strategy arguments
        parser.add_argument(
            "--strategy",
            choices=["k-core", "reciprocal_k-core", "ego_alter_k-core"],
            help="Analysis strategy to use"
        )
        
        parser.add_argument(
            "--ego-username",
            dest="ego_username",
            help="Username for ego_alter_k-core strategy"
        )
        
        parser.add_argument(
            "--k-value",
            dest="k_value",
            type=int,
            help="K-value for pruning (overrides strategy-specific defaults)"
        )
        
        # Analysis control
        parser.add_argument(
            "--skip-analysis",
            dest="skip_analysis",
            action="store_true",
            help="Skip computationally expensive analysis"
        )
        
        parser.add_argument(
            "--contact-path-target",
            dest="contact_path_target",
            help="Username to find contact path to"
        )
        
        # Analysis modes
        parser.add_argument(
            "--fast-mode",
            dest="analysis_mode_fast",
            action="store_true",
            help="Use fast analysis mode (reduced precision)"
        )
        
        parser.add_argument(
            "--medium-mode",
            dest="analysis_mode_medium",
            action="store_true",
            help="Use medium analysis mode (balanced)"
        )
        
        parser.add_argument(
            "--full-mode",
            dest="analysis_mode_full",
            action="store_true",
            help="Use full analysis mode (maximum precision)"
        )
        
        # Output control
        parser.add_argument(
            "--no-html",
            dest="no_html",
            action="store_true",
            help="Disable HTML output generation"
        )
        
        parser.add_argument(
            "--no-png",
            dest="no_png",
            action="store_true",
            help="Disable PNG output generation"
        )
        
        parser.add_argument(
            "--no-reports",
            dest="no_reports",
            action="store_true",
            help="Disable text report generation"
        )
        
        parser.add_argument(
            "--timing-logs",
            dest="enable_timing_logs",
            action="store_true",
            help="Enable detailed timing logs"
        )
        
        # Fame analysis
        parser.add_argument(
            "--min-fame-ratio",
            dest="min_fame_ratio",
            type=float,
            help="Minimum fame ratio for famous account detection"
        )
        
        parser.add_argument(
            "--min-followers",
            dest="min_followers_in_network",
            type=int,
            help="Minimum followers in network for fame analysis"
        )
        
        return parser
    
    def parse_cli_args(self, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Parse command-line arguments into configuration dictionary.
        
        Args:
            args: Optional list of arguments (uses sys.argv if None)
            
        Returns:
            Dict[str, Any]: Configuration overrides from CLI
        """
        parser = self.create_cli_parser()
        parsed_args = parser.parse_args(args)
        
        # Convert parsed arguments to configuration dictionary
        cli_config = {}
        
        # Direct mappings
        for attr in ["input_file", "output_file_prefix", "strategy", "ego_username", 
                     "contact_path_target", "skip_analysis", "min_fame_ratio", 
                     "min_followers_in_network"]:
            value = getattr(parsed_args, attr, None)
            if value is not None:
                cli_config[attr] = value
        
        # Handle k-value override
        if parsed_args.k_value is not None:
            cli_config["k_values"] = {
                "default_k_value": parsed_args.k_value,
                "allow_cli_override": True
            }
        
        # Handle analysis mode
        if parsed_args.analysis_mode_fast:
            cli_config["analysis_mode"] = {"mode": "fast"}
        elif parsed_args.analysis_mode_medium:
            cli_config["analysis_mode"] = {"mode": "medium"}
        elif parsed_args.analysis_mode_full:
            cli_config["analysis_mode"] = {"mode": "full"}
        
        # Handle output control
        output_control = {}
        if parsed_args.no_html:
            output_control["generate_html"] = False
        if parsed_args.no_png:
            output_control["generate_png"] = False
        if parsed_args.no_reports:
            output_control["generate_reports"] = False
        if parsed_args.enable_timing_logs:
            output_control["enable_timing_logs"] = True
        
        if output_control:
            cli_config["output_control"] = output_control
        
        return cli_config
    
    def save_configuration(self, config: FollowWebConfig, file_path: str) -> None:
        """
        Save configuration to JSON file.
        
        Args:
            config: Configuration instance to save
            file_path: Path to save configuration file
        """
        config_dict = self._serialize_configuration(config)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Configuration saved to {file_path}")
    
    def _validate_file_existence(self, config: FollowWebConfig) -> None:
        """
        Validate that required files exist.
        
        Args:
            config: Configuration to validate
            
        Raises:
            FileNotFoundError: If required files don't exist
        """
        if not os.path.exists(config.input_file):
            raise FileNotFoundError(f"Input file not found: {config.input_file}")
        
        # Validate output directory is writable
        output_dir = os.path.dirname(config.output_file_prefix)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Cannot create output directory {output_dir}: {e}")
    
    def _merge_configurations(self, base_config: Dict, overrides: Dict) -> Dict:
        """
        Merge configuration dictionaries with proper precedence.
        
        Args:
            base_config: Base configuration dictionary
            overrides: Override configuration dictionary
            
        Returns:
            Dict: Merged configuration dictionary
        """
        merged = base_config.copy()
        
        for key, value in overrides.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                # Recursively merge nested dictionaries
                merged[key] = self._merge_configurations(merged[key], value)
            else:
                # Override value
                merged[key] = value
        
        return merged
    
    def _serialize_configuration(self, config: FollowWebConfig) -> Dict[str, Any]:
        """
        Serialize configuration to JSON-compatible dictionary.
        
        Args:
            config: Configuration instance to serialize
            
        Returns:
            Dict[str, Any]: JSON-serializable configuration dictionary
        """
        return asdict(config)


def get_configuration_manager() -> ConfigurationManager:
    """
    Get a configured instance of ConfigurationManager.
    
    Returns:
        ConfigurationManager: Ready-to-use configuration manager
    """
    return ConfigurationManager()


def load_config_from_file(file_path: str) -> FollowWebConfig:
    """
    Load configuration from a JSON file.
    
    Args:
        file_path: Path to configuration file
        
    Returns:
        FollowWebConfig: Loaded and validated configuration
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If configuration is invalid
    """
    manager = get_configuration_manager()
    return manager.load_configuration(config_file=file_path)


def create_default_config_file(file_path: str) -> None:
    """
    Create a default configuration file with all options documented.
    
    Args:
        file_path: Path where to create the configuration file
    """
    default_config = FollowWebConfig()
    manager = get_configuration_manager()
    manager.save_configuration(default_config, file_path)
    print(f"Default configuration created at: {file_path}")


# Convenience function for backward compatibility with notebook CONFIG
def validate_config(config_dict: Dict[str, Any]) -> bool:
    """
    Validate configuration dictionary (notebook compatibility function).
    
    Args:
        config_dict: Configuration dictionary to validate
        
    Returns:
        bool: True if validation passes
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If configuration parameters are invalid
    """
    try:
        # Transform and validate using the new system
        config = load_config_from_dict(config_dict)
        
        # Perform file existence validation
        manager = get_configuration_manager()
        manager._validate_file_existence(config)
        
        print("=== CONFIGURATION VALIDATION PASSED ===")
        return True
        
    except Exception as e:
        print(f"=== CONFIGURATION VALIDATION FAILED ===")
        print(f"Error: {e}")
        raise