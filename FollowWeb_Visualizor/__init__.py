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
from .main import PipelineOrchestrator
from .config import FollowWebConfig, get_configuration_manager
from .progress import ProgressTracker

# Analysis components
try:
    from .analysis import GraphLoader, NetworkAnalyzer, PathAnalyzer, FameAnalyzer
except ImportError:
    # Graceful handling if analysis module is not fully implemented
    pass

# Visualization components  
try:
    from .visualization import MetricsCalculator, InteractiveRenderer, StaticRenderer, MetricsReporter
except ImportError:
    # Graceful handling if visualization module is not fully implemented
    pass

# Utility functions
from .utils import (
    generate_output_filename,
    get_community_colors, 
    get_scaled_size,
    format_time_duration,
    ensure_output_directory
)

# Custom exceptions
from .utils import (
    ConfigurationError,
    DataProcessingError,
    VisualizationError
)

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
    "MetricsReporter",
    
    # Utility functions
    "generate_output_filename",
    "get_community_colors",
    "get_scaled_size", 
    "format_time_duration",
    "ensure_output_directory",
    
    # Exceptions
    "ConfigurationError",
    "DataProcessingError",
    "VisualizationError",
]