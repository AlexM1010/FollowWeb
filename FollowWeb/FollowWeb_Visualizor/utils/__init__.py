"""
Utility components for FollowWeb Network Analysis.

This module provides shared utility functions and helpers:
- Input validation and error checking
- Parallel processing utilities and NetworkX configuration
- Mathematical operations and scaling algorithms
- File system operations and I/O utilities

Modules:
    validation: Input validation functions and parameter validation
    parallel: Parallel processing utilities and NetworkX parallel configuration
    math: Mathematical utility functions and scaling algorithms
    files: File system operations and path handling utilities
"""

# Import all utility functions to maintain backward compatibility
from .files import (
    ErrorRecoveryManager,
    FileOperationHandler,
    ensure_output_directory,
    error_context,
    generate_output_filename,
    handle_common_exceptions,
    safe_file_cleanup,
)
from .math import (
    clamp_value,
    format_number_clean,
    format_time_duration,
    get_scaled_size,
    safe_divide,
    scale_value,
)
from .parallel import (
    ParallelConfig,
    ParallelProcessingManager,
    detect_ci_environment,
    get_analysis_parallel_config,
    get_nx_parallel_status_message,
    get_optimal_worker_count,
    get_parallel_manager,
    get_testing_parallel_config,
    get_visualization_parallel_config,
    is_nx_parallel_available,
    log_parallel_usage,
)
from .progress import ProgressTracker
from .validation import (
    ConfigurationErrorHandler,
    ValidationErrorHandler,
    validate_at_least_one_enabled,
    validate_choice,
    validate_ego_strategy_requirements,
    validate_file_path,
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

# Export all utility functions
__all__ = [
    # Validation functions
    "ValidationErrorHandler",
    "ConfigurationErrorHandler",
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
    "validate_file_path",
    # Parallel processing functions
    "ParallelConfig",
    "ParallelProcessingManager",
    "get_parallel_manager",
    "get_analysis_parallel_config",
    "get_testing_parallel_config",
    "get_visualization_parallel_config",
    "log_parallel_usage",
    "is_nx_parallel_available",
    "get_nx_parallel_status_message",
    "detect_ci_environment",
    "get_optimal_worker_count",
    # Mathematical functions
    "scale_value",
    "get_scaled_size",
    "safe_divide",
    "clamp_value",
    "format_number_clean",
    "format_time_duration",
    # File operations
    "ErrorRecoveryManager",
    "FileOperationHandler",
    "error_context",
    "handle_common_exceptions",
    "generate_output_filename",
    "ensure_output_directory",
    "safe_file_cleanup",
    # Progress tracking
    "ProgressTracker",
]
