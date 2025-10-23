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

# Core imports for public API - graceful handling for modules not yet implemented
try:
    from .main import PipelineOrchestrator
except ImportError:
    PipelineOrchestrator = None

try:
    from .config import FollowWebConfig, get_configuration_manager
except ImportError:
    FollowWebConfig = None
    get_configuration_manager = None

try:
    from .progress import ProgressTracker
except ImportError:
    ProgressTracker = None

# Analysis components
try:
    from .analysis import GraphLoader, NetworkAnalyzer, PathAnalyzer, FameAnalyzer
except ImportError:
    # Graceful handling if analysis module is not fully implemented
    GraphLoader = NetworkAnalyzer = PathAnalyzer = FameAnalyzer = None

# Visualization components  
try:
    from .visualization import MetricsCalculator, InteractiveRenderer, StaticRenderer, MetricsReporter
except ImportError:
    # Graceful handling if visualization module is not fully implemented
    MetricsCalculator = InteractiveRenderer = StaticRenderer = MetricsReporter = None

# Utility functions
try:
    from .utils import (
        generate_output_filename,
        get_community_colors, 
        get_scaled_size,
        format_time_duration,
        ensure_output_directory,
        ConfigurationError,
        DataProcessingError,
        VisualizationError
    )
except ImportError:
    # Graceful handling if utils module is not fully implemented
    generate_output_filename = get_community_colors = get_scaled_size = None
    format_time_duration = ensure_output_directory = None
    ConfigurationError = DataProcessingError = VisualizationError = None

# Public API - only include items that are actually available
__all__ = []

# Add available items to __all__
if PipelineOrchestrator is not None:
    __all__.append("PipelineOrchestrator")
if ProgressTracker is not None:
    __all__.append("ProgressTracker")
if FollowWebConfig is not None:
    __all__.append("FollowWebConfig")
if get_configuration_manager is not None:
    __all__.append("get_configuration_manager")

# Analysis classes (if available)
for item in [GraphLoader, NetworkAnalyzer, PathAnalyzer, FameAnalyzer]:
    if item is not None:
        __all__.append(item.__name__)

# Visualization classes (if available)
for item in [MetricsCalculator, InteractiveRenderer, StaticRenderer, MetricsReporter]:
    if item is not None:
        __all__.append(item.__name__)

# Utility functions (if available)
for name, item in [
    ("generate_output_filename", generate_output_filename),
    ("get_community_colors", get_community_colors),
    ("get_scaled_size", get_scaled_size),
    ("format_time_duration", format_time_duration),
    ("ensure_output_directory", ensure_output_directory),
    ("ConfigurationError", ConfigurationError),
    ("DataProcessingError", DataProcessingError),
    ("VisualizationError", VisualizationError),
]:
    if item is not None:
        __all__.append(name)