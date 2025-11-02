"""
FollowWeb Network Analysis Package

A comprehensive social network analysis tool for visualizing Instagram follower/following
relationships using graph theory and network analysis techniques.

This package provides:
- Multiple analysis strategies (k-core, reciprocal, ego-alter)
- Interactive HTML and static PNG visualizations
- Community detection and centrality analysis
- Comprehensive metrics reporting
- Professional modular architecture

Modules:
    main: Entry point and pipeline orchestration
    config: Configuration management and validation
    analysis: Network analysis algorithms and graph processing
    visualization: Graph rendering for HTML and PNG outputs
    utils: Shared utilities and helper functions
    progress: Progress tracking for long-running operations

Example:
    >>> from FollowWeb_Visualizor.main import PipelineOrchestrator
    >>> from FollowWeb_Visualizor.config import get_configuration_manager
    >>>
    >>> config_manager = get_configuration_manager()
    >>> config = config_manager.load_configuration()
    >>> orchestrator = PipelineOrchestrator(config)
    >>> success = orchestrator.execute_pipeline()
"""

__version__ = "1.0.0"
__author__ = "Alex Marshall - github.com/AlexM1010"
__email__ = ""  # Add if available
__license__ = "MIT"  # Update as appropriate
__url__ = ""  # Add repository URL if available

# Core imports for public API
from .core.config import (
    FollowWebConfig,
    get_configuration_manager,
    load_config_from_dict,
)
from .main import PipelineOrchestrator
from .utils import ProgressTracker

# Analysis components
try:
    from .analysis.fame import FameAnalyzer
    from .analysis.network import NetworkAnalyzer
    from .analysis.paths import PathAnalyzer
    from .data.loaders import GraphLoader
except ImportError:
    # Graceful handling if analysis module is not fully implemented
    FameAnalyzer = None
    GraphLoader = None
    NetworkAnalyzer = None
    PathAnalyzer = None

# Visualization components
try:
    from .core.types import (
        ColorScheme,
        EdgeMetric,
        NodeMetric,
        VisualizationMetrics,
    )
    from .visualization.colors import get_shared_color_schemes
    from .visualization.metrics import (
        MetricsCalculator,
        calculate_shared_metrics,
        get_shared_layout_positions,
    )
    from .visualization.renderers import (
        InteractiveRenderer,
        StaticRenderer,
    )
except ImportError:
    # Graceful handling if visualization module is not fully implemented
    ColorScheme = None
    EdgeMetric = None
    InteractiveRenderer = None
    MetricsCalculator = None
    NodeMetric = None
    StaticRenderer = None
    VisualizationMetrics = None
    calculate_shared_metrics = None
    get_shared_color_schemes = None
    get_shared_layout_positions = None

# Error handling utilities
# Unified output system
from .output.logging import Logger
from .output.managers import OutputConfig, OutputManager
from .utils.files import (
    ErrorRecoveryManager,
    FileOperationHandler,
    error_context,
    handle_common_exceptions,
)

# Parallel processing utilities
from .utils.parallel import (
    ParallelConfig,
    ParallelProcessingManager,
    get_analysis_parallel_config,
    get_nx_parallel_status_message,
    get_parallel_manager,
    get_testing_parallel_config,
    get_visualization_parallel_config,
    is_nx_parallel_available,
    log_parallel_usage,
)
from .utils.validation import (
    ConfigurationErrorHandler,
    ValidationErrorHandler,
)

# Enhanced metrics reporting
try:
    from .output.managers import MetricsReporter
except ImportError:
    MetricsReporter = None

# Utility functions and exceptions
# Validation functions
# Centralized caching system

from .core.exceptions import (
    ConfigurationError,
    DataProcessingError,
    VisualizationError,
)
from .data.cache import (
    CentralizedCache,
    calculate_graph_hash,
    clear_all_caches,
    get_cache_manager,
    get_cached_community_colors,
    get_cached_node_attributes,
    get_cached_undirected_graph,
)

# Emoji formatting functions
from .output.formatters import (
    EmojiFormatter,
    format_completion,
    format_error,
    format_progress,
    format_success,
    format_timer,
    safe_print_error,
    safe_print_success,
)
from .utils.files import (
    ensure_output_directory,
    generate_output_filename,
)
from .utils.math import (
    format_time_duration,
    get_scaled_size,
)
from .utils.validation import (
    validate_at_least_one_enabled,
    validate_choice,
    validate_ego_strategy_requirements,
    validate_filesystem_safe_string,
    validate_image_dimensions,
    validate_k_value_dict,
    validate_multiple_non_negative,
    validate_non_empty_string,
    validate_non_negative_integer,
    validate_non_negative_number,
    validate_path_string,
    validate_positive_integer,
    validate_positive_number,
    validate_range,
    validate_string_format,
)
from .visualization.colors import get_community_colors

# Public API
__all__ = [
    # Main classes
    "PipelineOrchestrator",
    "ProgressTracker",
    # Configuration
    "FollowWebConfig",
    "get_configuration_manager",
    "load_config_from_dict",
    # Analysis classes (if available)
    "GraphLoader",
    "NetworkAnalyzer",
    "PathAnalyzer",
    "FameAnalyzer",
    # Visualization classes (if available)
    "MetricsCalculator",
    "InteractiveRenderer",
    "StaticRenderer",
    # Visualization data structures
    "VisualizationMetrics",
    "NodeMetric",
    "EdgeMetric",
    "ColorScheme",
    # Shared metrics functions
    "calculate_shared_metrics",
    "get_shared_layout_positions",
    "get_shared_color_schemes",
    # Unified output system
    "Logger",
    "OutputConfig",
    "OutputManager",
    # Enhanced metrics reporting
    "MetricsReporter",
    # Emoji utilities
    "EmojiFormatter",
    "format_completion",
    "format_error",
    "format_progress",
    "format_success",
    "format_timer",
    "safe_print_error",
    "safe_print_success",
    # Utility functions
    "generate_output_filename",
    "get_community_colors",
    "get_scaled_size",
    "format_time_duration",
    "ensure_output_directory",
    # Validation functions
    "validate_non_empty_string",
    "validate_positive_integer",
    "validate_non_negative_integer",
    "validate_positive_number",
    "validate_non_negative_number",
    "validate_range",
    "validate_choice",
    "validate_string_format",
    "validate_path_string",
    "validate_filesystem_safe_string",
    "validate_at_least_one_enabled",
    "validate_k_value_dict",
    "validate_ego_strategy_requirements",
    "validate_multiple_non_negative",
    "validate_image_dimensions",
    # Error handling utilities
    "ErrorRecoveryManager",
    "FileOperationHandler",
    "ValidationErrorHandler",
    "ConfigurationErrorHandler",
    "error_context",
    "handle_common_exceptions",
    # Parallel processing
    "ParallelConfig",
    "ParallelProcessingManager",
    "get_parallel_manager",
    "get_analysis_parallel_config",
    "get_testing_parallel_config",
    "get_visualization_parallel_config",
    "log_parallel_usage",
    "is_nx_parallel_available",
    "get_nx_parallel_status_message",
    # Exceptions
    "ConfigurationError",
    "DataProcessingError",
    "VisualizationError",
    # Centralized caching system
    "CentralizedCache",
    "calculate_graph_hash",
    "clear_all_caches",
    "get_cache_manager",
    "get_cached_community_colors",
    "get_cached_node_attributes",
    "get_cached_undirected_graph",
]
