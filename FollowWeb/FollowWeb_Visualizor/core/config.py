"""
Configuration management module for FollowWeb network analysis system.

This module provides configuration management with validation,
default values, and clear error messages for analysis parameters.
"""

# Standard library imports
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# Note: These imports will be updated when the respective modules are created
# For now, we'll comment them out to avoid import errors
# from ..utils.validation import (
#     validate_at_least_one_enabled,
#     validate_choice,
#     validate_ego_strategy_requirements,
#     validate_image_dimensions,
#     validate_k_value_dict,
#     validate_non_negative_integer,
#     validate_positive_integer,
#     validate_positive_number,
#     validate_range,
#     validate_string_format,
# )

# Local imports
# from ..output.formatters import EmojiFormatter
# from ..utils.math import format_time_duration


# Temporary placeholder functions to avoid import errors
def validate_at_least_one_enabled(options: Dict[str, bool], name: str) -> None:
    if not any(options.values()):
        raise ValueError(f"At least one {name} must be enabled")


def validate_choice(value: Any, name: str, choices: List[Any]) -> None:
    if value not in choices:
        raise ValueError(f"{name} must be one of {choices}, got {value}")


def validate_ego_strategy_requirements(
    strategy: str, ego_username: Optional[str]
) -> None:
    if strategy == "ego_alter_k-core" and not ego_username:
        raise ValueError("ego_username is required for ego_alter_k-core strategy")


def validate_image_dimensions(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive")


def validate_k_value_dict(
    k_values: Dict[str, int], name: str, valid_strategies: List[str]
) -> None:
    for strategy, k_val in k_values.items():
        if strategy not in valid_strategies:
            raise ValueError(f"Invalid strategy in {name}: {strategy}")
        if not isinstance(k_val, int) or k_val < 0:
            raise ValueError(f"K-value must be non-negative integer, got {k_val}")


def validate_non_negative_integer(value: Any, name: str) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be non-negative integer, got {value}")


def validate_positive_integer(value: Any, name: str) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be positive integer, got {value}")


def validate_positive_number(value: Any, name: str) -> None:
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} must be positive number, got {value}")


def validate_range(
    value: Union[int, float],
    name: str,
    min_val: Union[int, float],
    max_val: Union[int, float],
) -> None:
    if not (min_val <= value <= max_val):
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {value}")


def validate_string_format(value: str, name: str, valid_suffixes: List[str]) -> None:
    if not any(value.endswith(suffix) for suffix in valid_suffixes):
        raise ValueError(f"{name} must end with one of {valid_suffixes}, got {value}")


def format_time_duration(seconds: float) -> str:
    """Format time duration in human readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"


class EmojiFormatter:
    """Placeholder emoji formatter."""

    @staticmethod
    def format(emoji_type: str, message: str) -> str:
        return message


def _get_default_output_prefix() -> str:
    """Get the default output prefix based on environment (test vs production)."""
    import sys

    # Detect if we're running in a test environment
    is_testing = (
        "pytest" in sys.modules
        or "unittest" in sys.modules
        or "test" in sys.argv[0]
        or any("test" in arg for arg in sys.argv)
    )

    if is_testing:
        return "tests/Output/FollowWeb"
    else:
        return "Output/FollowWeb"


class AnalysisMode(Enum):
    """Analysis depth modes with different performance characteristics."""

    FAST = "fast"  # Optimized algorithms, reduced precision
    MEDIUM = "medium"  # Balanced analysis and performance
    FULL = "full"  # Detailed analysis, maximum precision


@dataclass
class PipelineStagesConfig:
    """Configuration for pipeline stage execution control."""

    enable_strategy: bool = True
    enable_analysis: bool = True
    enable_visualization: bool = True
    enable_community_detection: bool = True
    enable_centrality_analysis: bool = True
    enable_path_analysis: bool = True

    def __post_init__(self) -> None:
        """Validate pipeline stages configuration after initialization."""
        # Note: Stage dependency validation is handled by validate_stage_dependencies()
        # to allow for more flexible validation during configuration loading
        pass


@dataclass
class AnalysisModeConfig:
    """Configuration for analysis depth and performance modes."""

    mode: AnalysisMode = AnalysisMode.FULL
    sampling_threshold: int = 5000
    max_layout_iterations: Optional[Optional[int]] = None
    enable_fast_algorithms: bool = False

    def __post_init__(self) -> None:
        """Validate analysis mode configuration after initialization."""
        if not isinstance(self.mode, AnalysisMode):
            raise ValueError(
                f"mode must be an AnalysisMode enum value, got {type(self.mode)}"
            )

        if self.sampling_threshold < 100:
            raise ValueError("sampling_threshold must be at least 100")

        if self.max_layout_iterations is not None:
            validate_positive_integer(
                self.max_layout_iterations, "max_layout_iterations"
            )

        # Auto-configure fast algorithms based on mode
        if self.mode == AnalysisMode.FAST:
            self.enable_fast_algorithms = True
        elif self.mode == AnalysisMode.FULL:
            self.enable_fast_algorithms = False


@dataclass
class EmojiConfig:
    """Configuration for emoji display and fallback handling."""

    fallback_level: str = "full"  # "full", "simple", "text", "none"

    def __post_init__(self) -> None:
        """Validate emoji configuration after initialization."""
        valid_levels = ["full", "simple", "text", "none"]
        validate_choice(self.fallback_level, "fallback_level", valid_levels)


@dataclass
class OutputFormattingConfig:
    """Configuration for output display formatting."""

    indent_size: int = 2
    group_related_settings: bool = True
    highlight_key_values: bool = True
    use_human_readable_labels: bool = True
    emoji: EmojiConfig = field(default_factory=EmojiConfig)

    def __post_init__(self) -> None:
        """Validate output formatting configuration after initialization."""
        validate_non_negative_integer(self.indent_size, "indent_size")


@dataclass
class OutputControlConfig:
    """Configuration for output generation control."""

    generate_html: bool = True
    generate_png: bool = True
    generate_reports: bool = True
    enable_timing_logs: bool = False
    output_formatting: OutputFormattingConfig = field(
        default_factory=OutputFormattingConfig
    )

    def __post_init__(self) -> None:
        """Validate output control configuration after initialization."""
        # Ensure at least one output format is enabled
        output_options = {
            "generate_html": self.generate_html,
            "generate_png": self.generate_png,
            "generate_reports": self.generate_reports,
        }
        try:
            validate_at_least_one_enabled(output_options, "output format")
        except ValueError as e:
            raise ValueError(
                "At least one output format must be enabled. "
                "Set generate_html, generate_png, or generate_reports to true in output_control section, "
                "or use CLI flags: --no-png, --no-html, --no-reports (but keep at least one enabled)"
            ) from e


@dataclass
class KValueConfig:
    """Configuration for k-core analysis parameters."""

    strategy_k_values: Dict[str, int] = field(
        default_factory=lambda: {
            "k-core": 10,
            "reciprocal_k-core": 10,
            "ego_alter_k-core": 10,
        }
    )
    default_k_value: int = 10
    allow_cli_override: bool = True

    def __post_init__(self) -> None:
        """Validate k-value configuration after initialization."""
        # Validate all k-values and strategy names
        valid_strategies = ["k-core", "reciprocal_k-core", "ego_alter_k-core"]
        validate_k_value_dict(
            self.strategy_k_values, "strategy_k_values", valid_strategies
        )
        validate_non_negative_integer(self.default_k_value, "default_k_value")


@dataclass
class SpringLayoutConfig:
    """Spring layout physics configuration."""

    # Basic spring parameters
    k: float = 0.15  # Spring constant (node repulsion)
    iterations: int = 50  # Number of layout iterations

    # Advanced physics parameters
    spring_length: float = 1.0  # Natural length of springs (edges)
    spring_constant: float = 1.0  # Spring stiffness coefficient
    repulsion_strength: float = 1.0  # Node-to-node repulsion force
    attraction_strength: float = 1.0  # Edge attraction force

    # Gravity and centering
    center_gravity: float = 0.01  # Pull toward center (0=none, 1=strong)
    gravity_x: float = 0.0  # Horizontal gravity bias
    gravity_y: float = 0.0  # Vertical gravity bias

    # Damping and convergence
    damping: float = 0.9  # Velocity damping (0=no damping, 1=full)
    min_velocity: float = 0.01  # Stop when all nodes move less than this
    max_displacement: float = 10.0  # Maximum node movement per iteration

    # Multi-stage refinement
    enable_multistage: bool = True  # Use 3-stage refinement process
    initial_k_multiplier: float = 1.5  # Stage 1: k multiplier for separation
    final_k_multiplier: float = 0.8  # Stage 3: k multiplier for fine-tuning

    def __post_init__(self) -> None:
        """Validate spring layout configuration."""
        validate_positive_number(self.k, "spring_k")
        validate_positive_integer(self.iterations, "spring_iterations")
        validate_positive_number(self.spring_length, "spring_length")
        validate_positive_number(self.spring_constant, "spring_constant")
        validate_positive_number(self.repulsion_strength, "repulsion_strength")
        validate_positive_number(self.attraction_strength, "attraction_strength")
        validate_range(self.damping, "damping", 0, 1)
        validate_positive_number(self.min_velocity, "min_velocity")
        validate_positive_number(self.max_displacement, "max_displacement")


@dataclass
class KamadaKawaiLayoutConfig:
    """Kamada-Kawai layout configuration."""

    # Basic parameters
    max_iterations: int = 1000  # Maximum iterations
    tolerance: float = 1e-6  # Convergence tolerance

    # Distance and positioning
    distance_scale: float = 1.0  # Scale factor for ideal distances
    spring_strength: float = 1.0  # Spring strength coefficient

    # Convergence control
    pos_tolerance: float = 1e-4  # Position change tolerance
    weight_function: str = "path"  # "path", "weight", or "uniform"

    def __post_init__(self) -> None:
        """Validate Kamada-Kawai configuration."""
        validate_positive_integer(self.max_iterations, "max_iterations")
        validate_positive_number(self.tolerance, "tolerance")
        validate_positive_number(self.distance_scale, "distance_scale")
        validate_positive_number(self.spring_strength, "spring_strength")
        validate_choice(
            self.weight_function, "weight_function", ["path", "weight", "uniform"]
        )


@dataclass
class CircularLayoutConfig:
    """Circular layout configuration."""

    # Basic parameters
    radius: Optional[Optional[float]] = None  # Circle radius (None = auto)
    center: Optional[Optional[Tuple[float, float]]] = (
        None  # Center position (None = origin)
    )

    # Arrangement
    start_angle: float = 0.0  # Starting angle in radians
    angular_spacing: str = "uniform"  # "uniform", "degree", or "weight"

    # Community-based arrangement
    group_by_community: bool = True  # Group communities together
    community_separation: float = 0.2  # Angular gap between communities

    def __post_init__(self) -> None:
        """Validate circular layout configuration."""
        if self.radius is not None:
            validate_positive_number(self.radius, "radius")
        validate_range(self.start_angle, "start_angle", 0, 2 * 3.14159)
        validate_choice(
            self.angular_spacing, "angular_spacing", ["uniform", "degree", "weight"]
        )
        validate_range(self.community_separation, "community_separation", 0, 1)


@dataclass
class ShellLayoutConfig:
    """Shell layout configuration."""

    # Shell arrangement
    shell_spacing: float = 1.0  # Distance between shells
    center_shell_radius: float = 0.5  # Radius of innermost shell

    # Community-based shells
    arrange_by_community: bool = True  # Put communities in different shells
    arrange_by_centrality: bool = False  # Arrange by node importance
    centrality_metric: str = "degree"  # "degree", "betweenness", "eigenvector"

    # Shell assignment
    max_shells: int = 10  # Maximum number of shells
    nodes_per_shell: Optional[Optional[int]] = None  # Max nodes per shell (None = auto)

    def __post_init__(self) -> None:
        """Validate shell layout configuration."""
        validate_positive_number(self.shell_spacing, "shell_spacing")
        validate_positive_number(self.center_shell_radius, "center_shell_radius")
        validate_positive_integer(self.max_shells, "max_shells")
        validate_choice(
            self.centrality_metric,
            "centrality_metric",
            ["degree", "betweenness", "eigenvector"],
        )
        if self.nodes_per_shell is not None:
            validate_positive_integer(self.nodes_per_shell, "nodes_per_shell")


@dataclass
class PngLayoutConfig:
    """Configuration for PNG layout alignment and layout options."""

    force_spring_layout: bool = False
    align_with_html: bool = True

    # Layout-specific configurations
    spring: SpringLayoutConfig = field(default_factory=SpringLayoutConfig)
    kamada_kawai: KamadaKawaiLayoutConfig = field(
        default_factory=KamadaKawaiLayoutConfig
    )
    circular: CircularLayoutConfig = field(default_factory=CircularLayoutConfig)
    shell: ShellLayoutConfig = field(default_factory=ShellLayoutConfig)


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
    show_legend: bool = True
    node_alpha: float = 0.8
    edge_alpha: float = 0.3
    edge_arrow_size: int = 8

    def __post_init__(self) -> None:
        """Validate static image configuration after initialization."""
        valid_layouts = ["spring", "circular", "kamada_kawai", "random"]
        validate_choice(self.layout, "layout", valid_layouts)
        validate_image_dimensions(self.width, self.height)
        validate_positive_integer(self.dpi, "DPI")
        validate_positive_integer(self.font_size, "font_size")
        validate_range(self.node_alpha, "node_alpha", 0, 1)
        validate_range(self.edge_alpha, "edge_alpha", 0, 1)
        validate_positive_integer(self.edge_arrow_size, "edge_arrow_size")


@dataclass
class PyvisInteractiveConfig:
    """Configuration for Pyvis interactive HTML generation."""

    height: str = "600px"
    width: str = "100%"
    bgcolor: str = "#ffffff"
    font_color: str = "#000000"

    def __post_init__(self) -> None:
        """Validate Pyvis configuration after initialization."""
        # Basic validation for height and width format
        validate_string_format(self.height, "height", ["px", "%", "vh", "vw"])
        validate_string_format(self.width, "width", ["px", "%", "vh", "vw"])


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution control."""

    strategy: str = "k-core"
    skip_analysis: bool = False
    ego_username: Optional[Optional[str]] = None

    def __post_init__(self) -> None:
        """Validate pipeline configuration after initialization."""
        valid_strategies = ["k-core", "reciprocal_k-core", "ego_alter_k-core"]
        validate_choice(self.strategy, "strategy", valid_strategies)
        validate_ego_strategy_requirements(self.strategy, self.ego_username)


@dataclass
class AnalysisConfig:
    """Configuration for analysis parameters."""

    min_followers_in_network: int = 50
    min_fame_ratio: float = 5.0

    def __post_init__(self) -> None:
        """Validate analysis configuration after initialization."""
        validate_non_negative_integer(
            self.min_followers_in_network, "min_followers_in_network"
        )
        validate_positive_number(self.min_fame_ratio, "min_fame_ratio")


@dataclass
class FameAnalysisConfig:
    """Configuration for fame analysis parameters."""

    find_paths_to_all_famous: bool = True
    contact_path_target: Optional[Optional[str]] = None
    min_followers_in_network: int = 5
    min_fame_ratio: float = 5.0

    def __post_init__(self) -> None:
        """Validate fame analysis configuration after initialization."""
        validate_non_negative_integer(
            self.min_followers_in_network, "min_followers_in_network"
        )
        validate_positive_number(self.min_fame_ratio, "min_fame_ratio")


@dataclass
class OutputConfig:
    """Configuration for output generation."""

    custom_output_directory: Optional[Optional[str]] = None
    enable_time_logging: bool = False

    def __post_init__(self) -> None:
        """Validate output configuration after initialization."""
        if self.custom_output_directory and not isinstance(
            self.custom_output_directory, str
        ):
            raise ValueError("custom_output_directory must be a string")


@dataclass
class VisualizationConfig:
    """Configuration for visualization generation."""

    node_size_metric: str = "degree"
    base_node_size: float = 10.0
    node_size_multiplier: float = 2.0
    scaling_algorithm: str = "logarithmic"
    edge_thickness_metric: str = "weight"
    base_edge_thickness: float = 1.0
    base_edge_width: float = 0.5
    edge_width_multiplier: float = 1.5
    edge_width_scaling: str = "logarithmic"
    bridge_color: str = "#6e6e6e"
    intra_community_color: str = "#c0c0c0"
    static_image: StaticImageConfig = field(default_factory=StaticImageConfig)
    pyvis_interactive: PyvisInteractiveConfig = field(
        default_factory=PyvisInteractiveConfig
    )
    png_layout: PngLayoutConfig = field(default_factory=PngLayoutConfig)

    def __post_init__(self) -> None:
        """Validate visualization configuration after initialization."""
        valid_node_metrics = ["degree", "betweenness", "eigenvector", "closeness"]
        validate_choice(self.node_size_metric, "node_size_metric", valid_node_metrics)

        valid_edge_metrics = ["weight", "betweenness"]
        validate_choice(
            self.edge_thickness_metric, "edge_thickness_metric", valid_edge_metrics
        )

        valid_scaling_algorithms = ["logarithmic", "linear"]
        validate_choice(
            self.scaling_algorithm, "scaling_algorithm", valid_scaling_algorithms
        )

        validate_positive_number(self.base_node_size, "base_node_size")
        validate_positive_number(self.node_size_multiplier, "node_size_multiplier")

        validate_positive_number(self.base_edge_thickness, "base_edge_thickness")
        validate_positive_number(self.base_edge_width, "base_edge_width")
        validate_positive_number(self.edge_width_multiplier, "edge_width_multiplier")


@dataclass
class FollowWebConfig:
    """Main configuration class containing all FollowWeb analysis settings."""

    input_file: str = "examples/followers_following.json"
    output_file_prefix: str = field(
        default_factory=lambda: _get_default_output_prefix()
    )

    # Core configuration sections
    pipeline_stages: PipelineStagesConfig = field(default_factory=PipelineStagesConfig)
    analysis_mode: AnalysisModeConfig = field(default_factory=AnalysisModeConfig)
    output_control: OutputControlConfig = field(default_factory=OutputControlConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    k_values: KValueConfig = field(default_factory=KValueConfig)
    fame_analysis: FameAnalysisConfig = field(default_factory=FameAnalysisConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)

    # Essential analysis settings
    strategy: str = "k-core"
    ego_username: Optional[Optional[str]] = None

    def __post_init__(self) -> None:
        """Validate main configuration after initialization."""
        # Validate strategy
        valid_strategies = ["k-core", "reciprocal_k-core", "ego_alter_k-core"]
        validate_choice(self.strategy, "strategy", valid_strategies)
        validate_ego_strategy_requirements(self.strategy, self.ego_username)


def load_config_from_dict(config_dict: Dict[str, Any]) -> FollowWebConfig:
    """
    Creates a FollowWebConfig instance from a dictionary.

    Args:
        config_dict: Configuration dictionary.

    Returns:
        FollowWebConfig: Validated configuration instance.

    Raises:
        ValueError: If configuration validation fails.
    """
    try:
        # Extract configuration sections
        pipeline_stages_dict = config_dict.get("pipeline_stages", {})
        analysis_mode_dict = config_dict.get("analysis_mode", {})
        output_control_dict = config_dict.get("output_control", {})
        output_dict = config_dict.get("output", {})
        k_values_dict = config_dict.get("k_values", {})

        # Create pipeline stages config
        pipeline_stages_config = PipelineStagesConfig(
            enable_strategy=pipeline_stages_dict.get("enable_strategy", True),
            enable_analysis=pipeline_stages_dict.get("enable_analysis", True),
            enable_visualization=pipeline_stages_dict.get("enable_visualization", True),
            enable_community_detection=pipeline_stages_dict.get(
                "enable_community_detection", True
            ),
            enable_centrality_analysis=pipeline_stages_dict.get(
                "enable_centrality_analysis", True
            ),
            enable_path_analysis=pipeline_stages_dict.get("enable_path_analysis", True),
        )

        # Handle analysis mode - convert string to enum if needed
        mode_value = analysis_mode_dict.get("mode", "full")
        if isinstance(mode_value, str):
            try:
                analysis_mode = AnalysisMode(mode_value.lower())
            except ValueError as e:
                raise ValueError(
                    f"Invalid analysis mode '{mode_value}'. Must be one of: fast, medium, full. "
                    "Use --fast-mode, --medium-mode, or --full-mode CLI flags, "
                    "or set analysis_mode.mode in configuration file"
                ) from e
        elif isinstance(mode_value, AnalysisMode):
            analysis_mode = mode_value
        else:
            raise ValueError(f"Invalid analysis mode type: {type(mode_value)}")

        analysis_mode_config = AnalysisModeConfig(
            mode=analysis_mode,
            sampling_threshold=analysis_mode_dict.get("sampling_threshold", 5000),
            max_layout_iterations=analysis_mode_dict.get("max_layout_iterations"),
            enable_fast_algorithms=analysis_mode_dict.get(
                "enable_fast_algorithms", False
            ),
        )

        # Create output formatting config
        output_formatting_dict = output_control_dict.get("output_formatting", {})

        # Create emoji config
        emoji_dict = output_formatting_dict.get("emoji", {})
        emoji_config = EmojiConfig(
            fallback_level=emoji_dict.get("fallback_level", "full")
        )
        output_formatting_config = OutputFormattingConfig(
            indent_size=output_formatting_dict.get("indent_size", 2),
            group_related_settings=output_formatting_dict.get(
                "group_related_settings", True
            ),
            highlight_key_values=output_formatting_dict.get(
                "highlight_key_values", True
            ),
            use_human_readable_labels=output_formatting_dict.get(
                "use_human_readable_labels", True
            ),
            emoji=emoji_config,
        )

        output_control_config = OutputControlConfig(
            generate_html=output_control_dict.get("generate_html", True),
            generate_png=output_control_dict.get("generate_png", True),
            generate_reports=output_control_dict.get("generate_reports", True),
            enable_timing_logs=output_control_dict.get("enable_timing_logs", False),
            output_formatting=output_formatting_config,
        )

        # Create output config
        output_config = OutputConfig(
            custom_output_directory=output_dict.get("custom_output_directory"),
            enable_time_logging=output_dict.get("enable_time_logging", False),
        )

        k_values_config = KValueConfig(
            strategy_k_values=k_values_dict.get(
                "strategy_k_values",
                {"k-core": 10, "reciprocal_k-core": 10, "ego_alter_k-core": 10},
            ),
            default_k_value=k_values_dict.get("default_k_value", 10),
            allow_cli_override=k_values_dict.get("allow_cli_override", True),
        )

        # Create visualization config
        visualization_dict = config_dict.get("visualization", {})

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
            show_legend=static_image_dict.get("show_legend", True),
            node_alpha=static_image_dict.get("node_alpha", 0.8),
            edge_alpha=static_image_dict.get("edge_alpha", 0.3),
            edge_arrow_size=static_image_dict.get("edge_arrow_size", 8),
        )

        # Create PNG layout config with layout options
        png_layout_dict = visualization_dict.get("png_layout", {})

        # Spring layout configuration
        spring_dict = png_layout_dict.get("spring", {})
        spring_config = SpringLayoutConfig(
            k=spring_dict.get("k", 0.15),
            iterations=spring_dict.get("iterations", 50),
            spring_length=spring_dict.get("spring_length", 1.0),
            spring_constant=spring_dict.get("spring_constant", 1.0),
            repulsion_strength=spring_dict.get("repulsion_strength", 1.0),
            attraction_strength=spring_dict.get("attraction_strength", 1.0),
            center_gravity=spring_dict.get("center_gravity", 0.01),
            gravity_x=spring_dict.get("gravity_x", 0.0),
            gravity_y=spring_dict.get("gravity_y", 0.0),
            damping=spring_dict.get("damping", 0.9),
            min_velocity=spring_dict.get("min_velocity", 0.01),
            max_displacement=spring_dict.get("max_displacement", 10.0),
            enable_multistage=spring_dict.get("enable_multistage", True),
            initial_k_multiplier=spring_dict.get("initial_k_multiplier", 1.5),
            final_k_multiplier=spring_dict.get("final_k_multiplier", 0.8),
        )

        # Kamada-Kawai layout configuration
        kamada_dict = png_layout_dict.get("kamada_kawai", {})
        kamada_config = KamadaKawaiLayoutConfig(
            max_iterations=kamada_dict.get("max_iterations", 1000),
            tolerance=kamada_dict.get("tolerance", 1e-6),
            distance_scale=kamada_dict.get("distance_scale", 1.0),
            spring_strength=kamada_dict.get("spring_strength", 1.0),
            pos_tolerance=kamada_dict.get("pos_tolerance", 1e-4),
            weight_function=kamada_dict.get("weight_function", "path"),
        )

        # Circular layout configuration
        circular_dict = png_layout_dict.get("circular", {})
        circular_config = CircularLayoutConfig(
            radius=circular_dict.get("radius"),
            center=(
                tuple(circular_dict["center"])
                if "center" in circular_dict and circular_dict["center"] is not None
                else None
            ),
            start_angle=circular_dict.get("start_angle", 0.0),
            angular_spacing=circular_dict.get("angular_spacing", "uniform"),
            group_by_community=circular_dict.get("group_by_community", True),
            community_separation=circular_dict.get("community_separation", 0.2),
        )

        # Shell layout configuration
        shell_dict = png_layout_dict.get("shell", {})
        shell_config = ShellLayoutConfig(
            shell_spacing=shell_dict.get("shell_spacing", 1.0),
            center_shell_radius=shell_dict.get("center_shell_radius", 0.5),
            arrange_by_community=shell_dict.get("arrange_by_community", True),
            arrange_by_centrality=shell_dict.get("arrange_by_centrality", False),
            centrality_metric=shell_dict.get("centrality_metric", "degree"),
            max_shells=shell_dict.get("max_shells", 10),
            nodes_per_shell=shell_dict.get("nodes_per_shell"),
        )

        png_layout_config = PngLayoutConfig(
            force_spring_layout=png_layout_dict.get("force_spring_layout", False),
            align_with_html=png_layout_dict.get("align_with_html", True),
            spring=spring_config,
            kamada_kawai=kamada_config,
            circular=circular_config,
            shell=shell_config,
        )

        # Create pyvis interactive config
        pyvis_dict = visualization_dict.get("pyvis_interactive", {})
        pyvis_config = PyvisInteractiveConfig(
            height=pyvis_dict.get("height", "600px"),
            width=pyvis_dict.get("width", "100%"),
            bgcolor=pyvis_dict.get("bgcolor", "#ffffff"),
            font_color=pyvis_dict.get("font_color", "#000000"),
        )

        visualization_config = VisualizationConfig(
            node_size_metric=visualization_dict.get("node_size_metric", "degree"),
            base_node_size=visualization_dict.get("base_node_size", 10.0),
            node_size_multiplier=visualization_dict.get("node_size_multiplier", 2.0),
            scaling_algorithm=visualization_dict.get(
                "scaling_algorithm", "logarithmic"
            ),
            edge_thickness_metric=visualization_dict.get(
                "edge_thickness_metric", "weight"
            ),
            base_edge_thickness=visualization_dict.get("base_edge_thickness", 1.0),
            base_edge_width=visualization_dict.get("base_edge_width", 0.5),
            edge_width_multiplier=visualization_dict.get("edge_width_multiplier", 1.5),
            edge_width_scaling=visualization_dict.get(
                "edge_width_scaling", "logarithmic"
            ),
            bridge_color=visualization_dict.get("bridge_color", "#6e6e6e"),
            intra_community_color=visualization_dict.get(
                "intra_community_color", "#c0c0c0"
            ),
            static_image=static_image_config,
            pyvis_interactive=pyvis_config,
            png_layout=png_layout_config,
        )

        # Create fame analysis config
        fame_analysis_dict = config_dict.get("fame_analysis", {})
        fame_analysis_config = FameAnalysisConfig(
            find_paths_to_all_famous=fame_analysis_dict.get(
                "find_paths_to_all_famous", True
            ),
            contact_path_target=fame_analysis_dict.get("contact_path_target"),
            min_followers_in_network=fame_analysis_dict.get(
                "min_followers_in_network", 5
            ),
            min_fame_ratio=fame_analysis_dict.get("min_fame_ratio", 5.0),
        )

        # Create main config
        config = FollowWebConfig(
            input_file=config_dict.get(
                "input_file", "examples/followers_following.json"
            ),
            output_file_prefix=config_dict.get(
                "output_file_prefix", _get_default_output_prefix()
            ),
            pipeline_stages=pipeline_stages_config,
            analysis_mode=analysis_mode_config,
            output_control=output_control_config,
            output=output_config,
            k_values=k_values_config,
            fame_analysis=fame_analysis_config,
            visualization=visualization_config,
            strategy=config_dict.get("strategy", "k-core"),
            ego_username=config_dict.get("ego_username"),
        )

        return config

    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}") from e


# All validation is consolidated in ConfigurationManager.validate_configuration()


@dataclass
class ValidationResult:
    """Result of configuration validation with errors and warnings."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class DuplicateParameter:
    """Information about a duplicate parameter found during validation."""

    parameter_name: str
    locations: List[str]
    values: List[Any]


class ConfigurationManager:
    """
    Configuration management with validation and merging capabilities.

    This class provides configuration management including:
    - Loading from files and CLI arguments
    - Configuration validation with error reporting
    - Configuration merging with proper precedence
    - Duplicate parameter detection and consolidation
    - Configuration display formatting
    """

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self._parameter_aliases = {
            # Map of canonical parameter names to their aliases
            "k_values.default_k_value": ["pruning.default_k_value", "default_k"],
            "k_values.strategy_k_values": ["pruning.k_values", "strategy_k_values"],
            "pipeline_stages.enable_analysis": [
                "pipeline.enable_analysis",
                "enable_analysis",
            ],
            "pipeline_stages.enable_visualization": [
                "pipeline.enable_visualization",
                "enable_visualization",
            ],
            "output_control.generate_html": ["output.generate_html", "html_output"],
            "output_control.generate_png": ["output.generate_png", "png_output"],
            "output_control.generate_reports": [
                "output.generate_reports",
                "text_output",
            ],
        }

    def load_configuration(
        self,
        config_file: Optional[Optional[str]] = None,
        cli_args: Optional[Optional[Dict]] = None,
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
        base_config = self.serialize_configuration(default_config)

        # Load from file if specified
        if config_file:
            if not os.path.exists(config_file):
                raise FileNotFoundError(f"Configuration file not found: {config_file}")

            try:
                with open(config_file, encoding="utf-8") as f:
                    file_config = json.load(f)

                # Merge file configuration with defaults
                base_config = self.merge_configurations(base_config, file_config)

            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON in configuration file {config_file}: {e}"
                ) from e
            except Exception as e:
                raise ValueError(
                    f"Failed to load configuration from {config_file}: {e}"
                ) from e

        # Apply CLI overrides if provided
        if cli_args:
            base_config = self.merge_configurations(base_config, cli_args)

        # Detect and consolidate duplicate parameters
        base_config = self.consolidate_duplicates(base_config)

        # Create and validate configuration object
        config = load_config_from_dict(base_config)

        # Perform validation
        validation_result = self.validate_configuration(config)
        if not validation_result.is_valid:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {error}" for error in validation_result.errors
            )
            raise ValueError(error_msg)

        return config

    def validate_configuration(self, config: FollowWebConfig) -> ValidationResult:
        """
        Perform configuration validation.

        Args:
            config: Configuration instance to validate

        Returns:
            ValidationResult: Validation result with errors and warnings
        """
        errors = []
        warnings = []

        try:
            # Validate stage dependencies
            dependency_errors = self._validate_stage_dependencies(config)
            errors.extend(dependency_errors)

            # Check parameter consistency (warnings)
            consistency_warnings = self._validate_parameter_consistency(config)
            warnings.extend(consistency_warnings)

            # Additional validation for new configuration options
            self._validate_analysis_mode_config(config, errors, warnings)
            self._validate_output_control_config(config, errors, warnings)
            self._validate_k_value_config(config, errors, warnings)

        except Exception as e:
            errors.append(f"Unexpected validation error: {e}")

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def merge_configurations(self, base_config: Dict, overrides: Dict) -> Dict:
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
            if (
                isinstance(value, dict)
                and key in merged
                and isinstance(merged[key], dict)
            ):
                # Recursively merge nested dictionaries
                merged[key] = self.merge_configurations(merged[key], value)
            else:
                # Override value
                merged[key] = value

        return merged

    def format_configuration_display(self, config: FollowWebConfig) -> str:
        """
        Format configuration for human-readable display.

        Args:
            config: Configuration instance to format

        Returns:
            str: Formatted configuration string
        """
        formatting_config = config.output_control.output_formatting
        indent = " " * formatting_config.indent_size

        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("FOLLOWWEB CONFIGURATION")
        lines.append("=" * 60)

        if formatting_config.group_related_settings:
            # Group related settings logically
            self._add_input_output_section(config, lines, indent, formatting_config)
            self._add_pipeline_section(config, lines, indent, formatting_config)
            self._add_analysis_section(config, lines, indent, formatting_config)
            self._add_output_section(config, lines, indent, formatting_config)
        else:
            # Simple flat display
            config_dict = asdict(config)
            for key, value in config_dict.items():
                lines.append(f"{key}: {value}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def detect_duplicate_parameters(self, config: Dict) -> List[DuplicateParameter]:
        """
        Detect duplicate parameters across configuration sections.

        Args:
            config: Configuration dictionary to analyze

        Returns:
            List[DuplicateParameter]: List of detected duplicates
        """
        duplicates = []

        # Check for known aliases
        for canonical, aliases in self._parameter_aliases.items():
            found_locations = []
            found_values = []

            # Check canonical location
            canonical_parts = canonical.split(".")
            canonical_value = self._get_nested_value(config, canonical_parts)
            if canonical_value is not None:
                found_locations.append(canonical)
                found_values.append(canonical_value)

            # Check alias locations
            for alias in aliases:
                alias_parts = alias.split(".")
                alias_value = self._get_nested_value(config, alias_parts)
                if alias_value is not None:
                    found_locations.append(alias)
                    found_values.append(alias_value)

            # If multiple locations found, it's a duplicate
            if len(found_locations) > 1:
                duplicates.append(
                    DuplicateParameter(
                        parameter_name=canonical,
                        locations=found_locations,
                        values=found_values,
                    )
                )

        return duplicates

    def consolidate_duplicates(self, config: Dict) -> Dict:
        """
        Consolidate duplicate parameters into canonical locations.

        Args:
            config: Configuration dictionary with potential duplicates

        Returns:
            Dict: Configuration with duplicates consolidated
        """
        consolidated = config.copy()
        duplicates = self.detect_duplicate_parameters(consolidated)

        for duplicate in duplicates:
            canonical_parts = duplicate.parameter_name.split(".")

            # Use the first non-None value as the canonical value
            canonical_value = None
            for value in duplicate.values:
                if value is not None:
                    canonical_value = value
                    break

            if canonical_value is not None:
                # Set canonical value
                self._set_nested_value(consolidated, canonical_parts, canonical_value)

                # Remove duplicate locations
                for location in duplicate.locations:
                    if location != duplicate.parameter_name:
                        location_parts = location.split(".")
                        self._remove_nested_value(consolidated, location_parts)

        return consolidated

    def get_parameter_aliases(self) -> Dict[str, List[str]]:
        """
        Get the parameter alias registry.

        Returns:
            Dict[str, List[str]]: Mapping of canonical names to aliases
        """
        return self._parameter_aliases.copy()

    def serialize_configuration(self, config: FollowWebConfig) -> Dict[str, Any]:
        """
        Serialize configuration to JSON-compatible dictionary.

        Args:
            config: Configuration instance to serialize

        Returns:
            Dict[str, Any]: JSON-serializable configuration dictionary
        """
        # Serialize configuration to JSON-compatible dictionary
        return {
            "input_file": config.input_file,
            "output_file_prefix": config.output_file_prefix,
            "pipeline": {
                "strategy": config.strategy,
                "ego_username": config.ego_username,
                "skip_analysis": not config.pipeline_stages.enable_analysis,
            },
            "fame_analysis": {
                "find_paths_to_all_famous": config.fame_analysis.find_paths_to_all_famous,
                "contact_path_target": config.fame_analysis.contact_path_target,
                "min_followers_in_network": config.fame_analysis.min_followers_in_network,
                "min_fame_ratio": config.fame_analysis.min_fame_ratio,
            },
            "pipeline_stages": {
                "enable_strategy": config.pipeline_stages.enable_strategy,
                "enable_analysis": config.pipeline_stages.enable_analysis,
                "enable_visualization": config.pipeline_stages.enable_visualization,
                "enable_community_detection": config.pipeline_stages.enable_community_detection,
                "enable_centrality_analysis": config.pipeline_stages.enable_centrality_analysis,
                "enable_path_analysis": config.pipeline_stages.enable_path_analysis,
            },
            "analysis_mode": {
                "mode": config.analysis_mode.mode.value,  # Convert enum to string
                "sampling_threshold": config.analysis_mode.sampling_threshold,
                "max_layout_iterations": config.analysis_mode.max_layout_iterations,
                "enable_fast_algorithms": config.analysis_mode.enable_fast_algorithms,
            },
            "output_control": {
                "generate_html": config.output_control.generate_html,
                "generate_png": config.output_control.generate_png,
                "generate_reports": config.output_control.generate_reports,
                "enable_timing_logs": config.output_control.enable_timing_logs,
                "output_formatting": {
                    "indent_size": config.output_control.output_formatting.indent_size,
                    "group_related_settings": config.output_control.output_formatting.group_related_settings,
                    "highlight_key_values": config.output_control.output_formatting.highlight_key_values,
                    "use_human_readable_labels": config.output_control.output_formatting.use_human_readable_labels,
                    "emoji": {
                        "fallback_level": config.output_control.output_formatting.emoji.fallback_level,
                    },
                },
            },
            "k_values": {
                "strategy_k_values": config.k_values.strategy_k_values.copy(),
                "default_k_value": config.k_values.default_k_value,
                "allow_cli_override": config.k_values.allow_cli_override,
            },
            "visualization": {
                "node_size_metric": config.visualization.node_size_metric,
                "base_node_size": config.visualization.base_node_size,
                "node_size_multiplier": config.visualization.node_size_multiplier,
                "scaling_algorithm": config.visualization.scaling_algorithm,
                "edge_thickness_metric": config.visualization.edge_thickness_metric,
                "base_edge_thickness": config.visualization.base_edge_thickness,
                "base_edge_width": config.visualization.base_edge_width,
                "edge_width_multiplier": config.visualization.edge_width_multiplier,
                "edge_width_scaling": config.visualization.edge_width_scaling,
                "bridge_color": config.visualization.bridge_color,
                "intra_community_color": config.visualization.intra_community_color,
                "static_image": {
                    "generate": config.visualization.static_image.generate,
                    "layout": config.visualization.static_image.layout,
                    "width": config.visualization.static_image.width,
                    "height": config.visualization.static_image.height,
                    "dpi": config.visualization.static_image.dpi,
                },
                "pyvis_interactive": {
                    "height": config.visualization.pyvis_interactive.height,
                    "width": config.visualization.pyvis_interactive.width,
                    "bgcolor": config.visualization.pyvis_interactive.bgcolor,
                    "font_color": config.visualization.pyvis_interactive.font_color,
                },
            },
        }

    def _validate_analysis_mode_config(
        self, config: FollowWebConfig, errors: List[str], warnings: List[str]
    ) -> None:
        """Validate analysis mode configuration."""
        mode_config = config.analysis_mode

        # Check sampling threshold for fast mode
        if (
            mode_config.mode == AnalysisMode.FAST
            and mode_config.sampling_threshold > 10000
        ):
            warnings.append(
                "High sampling threshold in FAST mode may reduce performance benefits"
            )

        # Check layout iterations
        if (
            mode_config.max_layout_iterations is not None
            and mode_config.max_layout_iterations > 1000
        ):
            warnings.append(
                "High layout iteration count may cause slow visualization generation"
            )

    def _validate_output_control_config(
        self, config: FollowWebConfig, errors: List[str], warnings: List[str]
    ) -> None:
        """Validate output control configuration."""
        output_config = config.output_control

        # Check that at least one output format is enabled
        if not any(
            [
                output_config.generate_html,
                output_config.generate_png,
                output_config.generate_reports,
            ]
        ):
            errors.append("At least one output format must be enabled")

        # Check output directory permissions
        output_dir = os.path.dirname(config.output_file_prefix)
        if output_dir and not os.access(output_dir, os.W_OK):
            if os.path.exists(output_dir):
                errors.append(f"Output directory is not writable: {output_dir}")
            else:
                # Directory doesn't exist - this is handled elsewhere
                pass

    def _validate_k_value_config(
        self, config: FollowWebConfig, errors: List[str], warnings: List[str]
    ) -> None:
        """Validate k-value configuration."""
        k_config = config.k_values

        # Check for extremely high k-values
        for strategy, k_value in k_config.strategy_k_values.items():
            if k_value > 50:
                warnings.append(
                    f"High k-value for {strategy} ({k_value}) may result in empty graphs"
                )

    def _validate_stage_dependencies(self, config: FollowWebConfig) -> List[str]:
        """
        Validate pipeline stage dependencies and return any validation errors.

        Args:
            config: Configuration instance to validate.

        Returns:
            List[str]: List of validation error messages. Empty if no errors.
        """
        errors = []

        # Check visualization dependency on analysis
        if (
            config.pipeline_stages.enable_visualization
            and not config.pipeline_stages.enable_analysis
        ):
            errors.append(
                "Visualization stage requires analysis stage to be enabled. "
                "Enable analysis in pipeline_stages section or use --skip-visualization CLI flag"
            )

        # Check that at least one analysis component is enabled if analysis is enabled
        if config.pipeline_stages.enable_analysis:
            analysis_components = [
                config.pipeline_stages.enable_community_detection,
                config.pipeline_stages.enable_centrality_analysis,
                config.pipeline_stages.enable_path_analysis,
            ]
            if not any(analysis_components):
                errors.append(
                    "At least one analysis component must be enabled when analysis stage is enabled. "
                    "Enable community_detection, centrality_analysis, or path_analysis in pipeline_stages section, "
                    "or use CLI flags: --skip-community-detection, --skip-centrality-analysis, --skip-path-analysis"
                )

        # Check strategy compatibility with ego_alter analysis
        if (
            config.strategy == "ego_alter_k-core"
            and not config.pipeline_stages.enable_path_analysis
        ):
            errors.append(
                "ego_alter_k-core strategy requires path analysis to be enabled"
            )

        # Check output generation - at least one format must be enabled
        if not any(
            [
                config.output_control.generate_html,
                config.output_control.generate_png,
                config.output_control.generate_reports,
            ]
        ):
            errors.append("At least one output format must be enabled")

        return errors

    def _validate_parameter_consistency(self, config: FollowWebConfig) -> List[str]:
        """
        Validate consistency between different configuration parameters.

        Args:
            config: Configuration instance to validate.

        Returns:
            List[str]: List of validation warning messages. Empty if no issues.
        """
        warnings = []

        # Check analysis mode consistency
        if config.analysis_mode.mode == AnalysisMode.FAST:
            if config.pipeline_stages.enable_path_analysis:
                warnings.append(
                    "Path analysis is enabled in FAST mode, which may impact performance. "
                    "Consider disabling path analysis for optimal speed."
                )

            if config.analysis_mode.sampling_threshold > 10000:
                warnings.append(
                    "High sampling threshold in FAST mode may reduce performance benefits. "
                    "Consider lowering sampling_threshold for better speed."
                )

        return warnings

    def _add_input_output_section(
        self,
        config: FollowWebConfig,
        lines: List[str],
        indent: str,
        formatting_config: OutputFormattingConfig,
    ) -> None:
        """Add input/output section to configuration display."""
        lines.append("")
        lines.append("INPUT/OUTPUT:")
        lines.append(
            f"{indent}Input file: {self._format_value(config.input_file, formatting_config)}"
        )
        lines.append(
            f"{indent}Output prefix: {self._format_value(config.output_file_prefix, formatting_config)}"
        )

    def _add_pipeline_section(
        self,
        config: FollowWebConfig,
        lines: List[str],
        indent: str,
        formatting_config: OutputFormattingConfig,
    ) -> None:
        """Add pipeline section to configuration display."""
        lines.append("")
        lines.append("PIPELINE:")
        lines.append(
            f"{indent}Strategy: {self._format_value(config.strategy, formatting_config)}"
        )

        if config.ego_username:
            lines.append(
                f"{indent}Ego username: {self._format_value(config.ego_username, formatting_config)}"
            )

        # Pipeline stages
        stages = config.pipeline_stages
        lines.append(f"{indent}Stages enabled:")
        lines.append(f"{indent}{indent}Strategy: {stages.enable_strategy}")
        lines.append(f"{indent}{indent}Analysis: {stages.enable_analysis}")
        lines.append(f"{indent}{indent}Visualization: {stages.enable_visualization}")

    def _add_analysis_section(
        self,
        config: FollowWebConfig,
        lines: List[str],
        indent: str,
        formatting_config: OutputFormattingConfig,
    ) -> None:
        """Add analysis section to configuration display."""
        lines.append("")
        lines.append("ANALYSIS:")

        # Analysis mode
        mode_config = config.analysis_mode
        lines.append(
            f"{indent}Mode: {self._format_value(mode_config.mode.value, formatting_config)}"
        )
        lines.append(f"{indent}Sampling threshold: {mode_config.sampling_threshold:,}")

        # K-values
        k_config = config.k_values
        current_k = k_config.strategy_k_values.get(
            config.strategy, k_config.default_k_value
        )
        lines.append(
            f"{indent}K-value (current): {self._format_value(current_k, formatting_config)}"
        )

    def _add_output_section(
        self,
        config: FollowWebConfig,
        lines: List[str],
        indent: str,
        formatting_config: OutputFormattingConfig,
    ) -> None:
        """Add output section to configuration display."""
        lines.append("")
        lines.append("OUTPUT:")

        output_config = config.output_control
        lines.append(f"{indent}HTML: {output_config.generate_html}")
        lines.append(f"{indent}PNG: {output_config.generate_png}")
        lines.append(f"{indent}Reports: {output_config.generate_reports}")
        lines.append(f"{indent}Timing logs: {output_config.enable_timing_logs}")

    def _format_value(
        self, value: Any, formatting_config: OutputFormattingConfig
    ) -> str:
        """Format a value for display based on formatting configuration."""
        if formatting_config.highlight_key_values and isinstance(value, str):
            return f"'{value}'"
        return str(value)

    def _get_nested_value(self, config: Dict, path: List[str]) -> Any:
        """Get a nested value from configuration dictionary."""
        current = config
        for part in path:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _set_nested_value(self, config: Dict, path: List[str], value: Any) -> None:
        """Set a nested value in configuration dictionary."""
        current = config
        for part in path[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[path[-1]] = value

    def _remove_nested_value(self, config: Dict, path: List[str]) -> None:
        """Remove a nested value from configuration dictionary."""
        current = config
        for part in path[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return

        if isinstance(current, dict) and path[-1] in current:
            del current[path[-1]]


class PipelineStagesController:
    """
    Controls execution of individual pipeline stages based on configuration.

    This controller provides stage execution control with dependency validation
    and execution logging for the FollowWeb pipeline.
    """

    def __init__(self, config: FollowWebConfig) -> None:
        """
        Initialize the pipeline stages controller.

        Args:
            config: FollowWebConfig instance containing pipeline stage configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Track stage execution status
        self.stage_status = {
            "strategy": "not_started",
            "analysis": "not_started",
            "visualization": "not_started",
        }

        # Track analysis component status
        self.analysis_components_status = {
            "community_detection": "not_started",
            "centrality_analysis": "not_started",
            "path_analysis": "not_started",
        }

    def should_execute_stage(self, stage_name: str) -> bool:
        """
        Determine if a pipeline stage should be executed based on configuration.

        Args:
            stage_name: Name of the stage ('strategy', 'analysis', 'visualization')

        Returns:
            bool: True if stage should be executed, False otherwise
        """
        stage_config = self.config.pipeline_stages

        stage_mapping = {
            "strategy": stage_config.enable_strategy,
            "analysis": stage_config.enable_analysis,
            "visualization": stage_config.enable_visualization,
        }

        if stage_name not in stage_mapping:
            self.logger.warning(f"Unknown stage name: {stage_name}")
            return False

        enabled = stage_mapping[stage_name]

        if enabled:
            self.logger.debug(f"Stage '{stage_name}' is enabled and will be executed")
        else:
            self.logger.info(f"Stage '{stage_name}' is disabled and will be skipped")

        return enabled

    def should_execute_analysis_component(self, component_name: str) -> bool:
        """
        Determine if an analysis component should be executed.

        Args:
            component_name: Name of the component ('community_detection', 'centrality_analysis', 'path_analysis')

        Returns:
            bool: True if component should be executed, False otherwise
        """
        # First check if analysis stage is enabled
        if not self.should_execute_stage("analysis"):
            return False

        stage_config = self.config.pipeline_stages

        component_mapping = {
            "community_detection": stage_config.enable_community_detection,
            "centrality_analysis": stage_config.enable_centrality_analysis,
            "path_analysis": stage_config.enable_path_analysis,
        }

        if component_name not in component_mapping:
            self.logger.warning(f"Unknown analysis component: {component_name}")
            return False

        enabled = component_mapping[component_name]

        if enabled:
            self.logger.debug(f"Analysis component '{component_name}' is enabled")
        else:
            self.logger.info(
                f"Analysis component '{component_name}' is disabled and will be skipped"
            )

        return enabled

    def get_stage_configuration(self, stage_name: str) -> Dict[str, Any]:
        """
        Get configuration specific to a pipeline stage.

        Args:
            stage_name: Name of the stage

        Returns:
            Dict[str, Any]: Stage-specific configuration
        """
        if stage_name == "strategy":
            return {
                "strategy": self.config.strategy,
                "k_values": self.config.k_values.strategy_k_values,
                "default_k_value": self.config.k_values.default_k_value,
                "ego_username": self.config.ego_username,
            }
        elif stage_name == "analysis":
            return {
                "analysis_mode": self.config.analysis_mode,
                "enable_community_detection": self.config.pipeline_stages.enable_community_detection,
                "enable_centrality_analysis": self.config.pipeline_stages.enable_centrality_analysis,
                "enable_path_analysis": self.config.pipeline_stages.enable_path_analysis,
                "contact_path_target": self.config.fame_analysis.contact_path_target,
                "min_followers_in_network": self.config.fame_analysis.min_followers_in_network,
                "min_fame_ratio": self.config.fame_analysis.min_fame_ratio,
                "find_paths_to_all_famous": self.config.fame_analysis.find_paths_to_all_famous,
            }
        elif stage_name == "visualization":
            return {
                "output_control": self.config.output_control,
                "visualization": self.config.visualization,
                "output_file_prefix": self.config.output_file_prefix,
            }
        else:
            self.logger.warning(f"Unknown stage name: {stage_name}")
            return {}

    def validate_stage_dependencies(self) -> List[str]:
        """
        Validate stage dependencies and return validation errors.

        Returns:
            List[str]: List of validation error messages. Empty if no errors.
        """
        errors = []

        # Check visualization dependency on analysis
        if (
            self.config.pipeline_stages.enable_visualization
            and not self.config.pipeline_stages.enable_analysis
        ):
            errors.append(
                "Visualization stage requires analysis stage to be enabled. "
                "Enable analysis in pipeline_stages section or use --skip-visualization CLI flag"
            )

        # Check that at least one analysis component is enabled if analysis is enabled
        if self.config.pipeline_stages.enable_analysis:
            analysis_components = [
                self.config.pipeline_stages.enable_community_detection,
                self.config.pipeline_stages.enable_centrality_analysis,
                self.config.pipeline_stages.enable_path_analysis,
            ]
            if not any(analysis_components):
                errors.append(
                    "At least one analysis component must be enabled when analysis stage is enabled. "
                    "Enable community_detection, centrality_analysis, or path_analysis in pipeline_stages section, "
                    "or use CLI flags: --skip-community-detection, --skip-centrality-analysis, --skip-path-analysis"
                )

        # Check strategy compatibility with ego_alter analysis
        if (
            self.config.strategy == "ego_alter_k-core"
            and not self.config.pipeline_stages.enable_path_analysis
        ):
            errors.append(
                "ego_alter_k-core strategy requires path analysis to be enabled"
            )

        # Check that strategy stage is always enabled (required for pipeline)
        if not self.config.pipeline_stages.enable_strategy:
            errors.append(
                "Strategy stage cannot be disabled - it is required for pipeline execution"
            )

        return errors

    def log_stage_start(self, stage_name: str) -> None:
        """
        Log the start of a pipeline stage.

        Args:
            stage_name: Name of the stage being started
        """
        self.stage_status[stage_name] = "in_progress"
        self.logger.info(f"STAGE START: {stage_name.upper()} phase beginning")

    def log_stage_completion(
        self, stage_name: str, success: bool, duration: Optional[float] = None
    ) -> None:
        """
        Log the completion of a pipeline stage.

        Args:
            stage_name: Name of the stage that completed
            success: Whether the stage completed successfully
            duration: Optional duration in seconds
        """
        if success:
            self.stage_status[stage_name] = "completed"
            status_msg = EmojiFormatter.format(
                "success", f"{stage_name.upper()} phase completed successfully"
            )
            if duration is not None:
                status_msg += f" in {format_time_duration(duration)}"
            self.logger.info(status_msg)
        else:
            self.stage_status[stage_name] = "failed"
            self.logger.error(f"STAGE FAILURE: {stage_name.upper()} phase failed")

    def log_stage_skip(self, stage_name: str, reason: Optional[str] = None) -> None:
        """
        Log that a pipeline stage was skipped.

        Args:
            stage_name: Name of the stage being skipped
            reason: Optional reason for skipping
        """
        self.stage_status[stage_name] = "skipped"
        skip_msg = f"STAGE SKIP: {stage_name.upper()} phase skipped"
        if reason:
            skip_msg += f" - {reason}"
        self.logger.info(skip_msg)

    def log_analysis_component_start(self, component_name: str) -> None:
        """
        Log the start of an analysis component.

        Args:
            component_name: Name of the analysis component
        """
        self.analysis_components_status[component_name] = "in_progress"
        self.logger.debug(f"Analysis component '{component_name}' starting")

    def log_analysis_component_completion(
        self, component_name: str, success: bool
    ) -> None:
        """
        Log the completion of an analysis component.

        Args:
            component_name: Name of the analysis component
            success: Whether the component completed successfully
        """
        if success:
            self.analysis_components_status[component_name] = "completed"
            self.logger.debug(
                f"Analysis component '{component_name}' completed successfully"
            )
        else:
            self.analysis_components_status[component_name] = "failed"
            self.logger.warning(f"Analysis component '{component_name}' failed")

    def log_analysis_component_skip(
        self, component_name: str, reason: Optional[str] = None
    ) -> None:
        """
        Log that an analysis component was skipped.

        Args:
            component_name: Name of the analysis component
            reason: Optional reason for skipping
        """
        self.analysis_components_status[component_name] = "skipped"
        skip_msg = f"Analysis component '{component_name}' skipped"
        if reason:
            skip_msg += f" - {reason}"
        self.logger.debug(skip_msg)

    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get a summary of stage execution status.

        Returns:
            Dict[str, Any]: Summary of execution status for all stages and components
        """
        return {
            "stages": self.stage_status.copy(),
            "analysis_components": self.analysis_components_status.copy(),
            "configuration": {
                "strategy_enabled": self.config.pipeline_stages.enable_strategy,
                "analysis_enabled": self.config.pipeline_stages.enable_analysis,
                "visualization_enabled": self.config.pipeline_stages.enable_visualization,
                "community_detection_enabled": self.config.pipeline_stages.enable_community_detection,
                "centrality_analysis_enabled": self.config.pipeline_stages.enable_centrality_analysis,
                "path_analysis_enabled": self.config.pipeline_stages.enable_path_analysis,
            },
        }


class AnalysisModeManager:
    """
    Manages analysis depth and performance optimization settings.

    This class provides mode-specific configuration mapping and performance
    optimization logic for FAST, MEDIUM, and FULL analysis modes.
    """

    def __init__(self, config: FollowWebConfig) -> None:
        """
        Initialize the analysis mode manager.

        Args:
            config: FollowWebConfig instance containing analysis mode configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Define mode-specific parameter mappings
        self._mode_configurations = {
            AnalysisMode.FAST: {
                "sampling_threshold": 1000,
                "max_layout_iterations": 100,
                "enable_fast_algorithms": True,
                "centrality_sample_size_factor": 0.1,  # Use 10% of nodes for centrality sampling
                "path_analysis_sample_size": 500,
                "community_detection_resolution": 1.5,  # Higher resolution for faster detection
                "skip_eigenvector_centrality": True,
                "use_approximate_betweenness": True,
            },
            AnalysisMode.MEDIUM: {
                "sampling_threshold": 5000,
                "max_layout_iterations": 500,
                "enable_fast_algorithms": False,
                "centrality_sample_size_factor": 0.3,  # Use 30% of nodes for centrality sampling
                "path_analysis_sample_size": 2000,
                "community_detection_resolution": 1.0,  # Default resolution
                "skip_eigenvector_centrality": False,
                "use_approximate_betweenness": True,
            },
            AnalysisMode.FULL: {
                "sampling_threshold": 10000,
                "max_layout_iterations": 1000,
                "enable_fast_algorithms": False,
                "centrality_sample_size_factor": 1.0,  # Use all nodes for centrality calculations
                "path_analysis_sample_size": None,  # No sampling limit
                "community_detection_resolution": 1.0,  # Default resolution
                "skip_eigenvector_centrality": False,
                "use_approximate_betweenness": False,
            },
        }

    def get_mode_configuration(
        self, mode: Optional[AnalysisMode] = None
    ) -> Dict[str, Any]:
        """
        Get mode-specific configuration parameters.

        Args:
            mode: Analysis mode to get configuration for. If None, uses config mode.

        Returns:
            Dict[str, Any]: Mode-specific configuration parameters
        """
        if mode is None:
            mode = self.config.analysis_mode.mode

        if mode not in self._mode_configurations:
            self.logger.warning(
                f"Unknown analysis mode: {mode}. Using FULL mode configuration."
            )
            mode = AnalysisMode.FULL

        # Start with mode defaults
        mode_config = self._mode_configurations[mode].copy()

        # Override with user configuration where specified
        user_config = self.config.analysis_mode

        # Apply user overrides
        if user_config.sampling_threshold != 5000:  # User has customized
            mode_config["sampling_threshold"] = user_config.sampling_threshold

        if user_config.max_layout_iterations is not None:
            mode_config["max_layout_iterations"] = user_config.max_layout_iterations

        if (
            hasattr(user_config, "enable_fast_algorithms")
            and user_config.enable_fast_algorithms is not None
        ):
            mode_config["enable_fast_algorithms"] = user_config.enable_fast_algorithms

        return mode_config

    def apply_performance_optimizations(
        self, config: Dict, mode: Optional[AnalysisMode] = None
    ) -> Dict:
        """
        Apply performance optimizations based on analysis mode.

        Args:
            config: Base configuration dictionary to optimize
            mode: Analysis mode to apply optimizations for

        Returns:
            Dict: Optimized configuration dictionary
        """
        if mode is None:
            mode = self.config.analysis_mode.mode

        mode_config = self.get_mode_configuration(mode)
        optimized_config = config.copy()

        # Apply mode-specific optimizations
        optimized_config.update(mode_config)

        self.logger.debug(f"Applied {mode.value} mode optimizations to configuration")

        return optimized_config

    def get_sampling_parameters(
        self, graph_size: int, mode: Optional[AnalysisMode] = None
    ) -> Dict[str, Any]:
        """
        Calculate sampling parameters based on graph size and analysis mode.

        Args:
            graph_size: Number of nodes in the graph
            mode: Analysis mode to calculate parameters for

        Returns:
            Dict[str, Any]: Sampling parameters for analysis algorithms
        """
        if mode is None:
            mode = self.config.analysis_mode.mode

        mode_config = self.get_mode_configuration(mode)

        # Calculate centrality sampling size
        centrality_sample_factor = mode_config.get("centrality_sample_size_factor", 1.0)
        centrality_sample_size = max(1, int(graph_size * centrality_sample_factor))
        centrality_sample_size = min(centrality_sample_size, graph_size)

        # Calculate path analysis sampling
        path_sample_size = mode_config.get("path_analysis_sample_size")
        if path_sample_size is None:
            path_sample_size = graph_size  # No sampling
        else:
            path_sample_size = min(path_sample_size, graph_size)

        # Determine if sampling should be used
        sampling_threshold = mode_config.get("sampling_threshold", 5000)
        use_sampling = graph_size > sampling_threshold

        sampling_params = {
            "use_sampling": use_sampling,
            "centrality_sample_size": centrality_sample_size,
            "path_analysis_sample_size": path_sample_size,
            "sampling_threshold": sampling_threshold,
            "graph_size": graph_size,
            "mode": mode.value,
            "skip_eigenvector_centrality": mode_config.get(
                "skip_eigenvector_centrality", False
            ),
            "use_approximate_betweenness": mode_config.get(
                "use_approximate_betweenness", False
            ),
            "community_detection_resolution": mode_config.get(
                "community_detection_resolution", 1.0
            ),
        }

        # No logging here - sampling details are logged once in analysis.py

        return sampling_params

    def get_performance_config_for_component(
        self, component_name: str, graph_size: int
    ) -> Dict[str, Any]:
        """
        Get performance configuration for a specific analysis component.

        Args:
            component_name: Name of the analysis component
            graph_size: Size of the graph being analyzed

        Returns:
            Dict[str, Any]: Component-specific performance configuration
        """
        mode = self.config.analysis_mode.mode
        mode_config = self.get_mode_configuration(mode)
        sampling_params = self.get_sampling_parameters(graph_size, mode)

        if component_name == "community_detection":
            return {
                "resolution": mode_config.get("community_detection_resolution", 1.0),
                "use_sampling": sampling_params["use_sampling"],
                "mode": mode.value,
            }

        elif component_name == "centrality_analysis":
            return {
                "sample_size": sampling_params["centrality_sample_size"],
                "skip_eigenvector": sampling_params["skip_eigenvector_centrality"],
                "use_approximate_betweenness": sampling_params[
                    "use_approximate_betweenness"
                ],
                "use_sampling": sampling_params["use_sampling"],
                "mode": mode.value,
            }

        elif component_name == "path_analysis":
            return {
                "sample_size": sampling_params["path_analysis_sample_size"],
                "use_sampling": sampling_params["use_sampling"],
                "skip_path_analysis": mode == AnalysisMode.FAST and graph_size > 10000,
                "mode": mode.value,
            }

        else:
            self.logger.warning(f"Unknown component name: {component_name}")
            return {"mode": mode.value}

    def log_mode_configuration(self) -> None:
        """Log the current analysis mode configuration."""
        mode = self.config.analysis_mode.mode
        mode_config = self.get_mode_configuration(mode)

        self.logger.info(f"Analysis Mode: {mode.value.upper()}")
        self.logger.info(
            f"  - Sampling threshold: {mode_config['sampling_threshold']:,} nodes"
        )
        self.logger.info(
            f"  - Max layout iterations: {mode_config['max_layout_iterations']}"
        )
        self.logger.info(
            f"  - Fast algorithms: {mode_config['enable_fast_algorithms']}"
        )

        if mode == AnalysisMode.FAST:
            self.logger.info("  - Optimized for speed with reduced precision")
        elif mode == AnalysisMode.MEDIUM:
            self.logger.info("  - Balanced analysis depth and performance")
        elif mode == AnalysisMode.FULL:
            self.logger.info("  - Detailed analysis with maximum precision")


def get_configuration_manager() -> ConfigurationManager:
    """
    Get an instance of the ConfigurationManager.

    Returns:
        ConfigurationManager: Manager instance
    """
    return ConfigurationManager()


def get_analysis_mode_manager(config: FollowWebConfig) -> AnalysisModeManager:
    """
    Get an instance of the AnalysisModeManager.

    Args:
        config: FollowWebConfig instance

    Returns:
        AnalysisModeManager: Manager instance
    """
    return AnalysisModeManager(config)
