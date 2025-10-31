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
# Note: These imports will be updated as modules are implemented in the modular structure
try:
    from .config import FollowWebConfig, get_configuration_manager, load_config_from_dict
except ImportError:
    FollowWebConfig = None
    get_configuration_manager = None
    load_config_from_dict = None

try:
    from .main import PipelineOrchestrator
except ImportError:
    PipelineOrchestrator = None

try:
    from .utils import ProgressTracker
except ImportError:
    ProgressTracker = None

# Analysis components
try:
    from .analysis import FameAnalyzer, GraphLoader, NetworkAnalyzer, PathAnalyzer
except ImportError:
    # Graceful handling if analysis module is not fully implemented
    FameAnalyzer = None
    GraphLoader = None
    NetworkAnalyzer = None
    PathAnalyzer = None

# Visualization components
try:
    from .visualization import (
        ColorScheme,
        EdgeMetric,
        InteractiveRenderer,
        MetricsCalculator,
        NodeMetric,
        StaticRenderer,
        VisualizationMetrics,
        calculate_shared_metrics,
        get_shared_color_schemes,
        get_shared_layout_positions,
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
try:
    from .error_handling import (
        ConfigurationErrorHandler,
        ErrorRecoveryManager,
        FileOperationHandler,
        ValidationErrorHandler,
        create_error_summary,
        error_context,
        handle_common_exceptions,
        log_performance_warning,
    )
except ImportError:
    ConfigurationErrorHandler = None
    ErrorRecoveryManager = None
    FileOperationHandler = None
    ValidationErrorHandler = None
    create_error_summary = None
    error_context = None
    handle_common_exceptions = None
    log_performance_warning = None

# Unified output system
try:
    from .unified_output import (
        Logger,
        OutputConfig,
        OutputManager,
    )
except ImportError:
    Logger = None
    OutputConfig = None
    OutputManager = None

# Parallel processing utilities
try:
    from .utils import (
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
except ImportError:
    ParallelConfig = None
    ParallelProcessingManager = None
    get_analysis_parallel_config = None
    get_nx_parallel_status_message = None
    get_parallel_manager = None
    get_testing_parallel_config = None
    get_visualization_parallel_config = None
    is_nx_parallel_available = None
    log_parallel_usage = None

# Enhanced metrics reporting
try:
    from .unified_output import MetricsReporter
except ImportError:
    MetricsReporter = None

# Utility functions and exceptions
# Validation functions
try:
    from .error_handling import (
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
except ImportError:
    validate_at_least_one_enabled = None
    validate_choice = None
    validate_ego_strategy_requirements = None
    validate_filesystem_safe_string = None
    validate_image_dimensions = None
    validate_k_value_dict = None
    validate_multiple_non_negative = None
    validate_non_empty_string = None
    validate_non_negative_integer = None
    validate_non_negative_number = None
    validate_path_string = None
    validate_positive_integer = None
    validate_positive_number = None
    validate_range = None
    validate_string_format = None

# Emoji formatting functions
try:
    from .unified_output import (
        EmojiFormatter,
        format_completion,
        format_error,
        format_progress,
        format_success,
        format_timer,
        safe_print_error,
        safe_print_success,
    )
except ImportError:
    EmojiFormatter = None
    format_completion = None
    format_error = None
    format_progress = None
    format_success = None
    format_timer = None
    safe_print_error = None
    safe_print_success = None

# Centralized caching system
try:
    from .utils import (
        CentralizedCache,
        ConfigurationError,
        DataProcessingError,
        VisualizationError,
        calculate_graph_hash,
        clear_all_caches,
        ensure_output_directory,
        format_time_duration,
        generate_output_filename,
        get_cache_manager,
        get_cached_community_colors,
        get_cached_node_attributes,
        get_cached_undirected_graph,
        get_community_colors,
        get_scaled_size,
    )
except ImportError:
    CentralizedCache = None
    ConfigurationError = None
    DataProcessingError = None
    VisualizationError = None
    calculate_graph_hash = None
    clear_all_caches = None
    ensure_output_directory = None
    format_time_duration = None
    generate_output_filename = None
    get_cache_manager = None
    get_cached_community_colors = None
    get_cached_node_attributes = None
    get_cached_undirected_graph = None
    get_community_colors = None
    get_scaled_size = None

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
    "create_error_summary",
    "log_performance_warning",
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
