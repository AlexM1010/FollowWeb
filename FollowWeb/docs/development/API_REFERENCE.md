# API Reference

Comprehensive API documentation for FollowWeb Network Analysis Package.

## Main Module (`main.py`)

### `PipelineOrchestrator`

Main class for executing the complete analysis pipeline.

```python
class PipelineOrchestrator:
    def __init__(self, config: FollowWebConfig) -> None
    def execute_pipeline() -> bool
```

**Parameters:**
- `config`: FollowWebConfig instance containing all analysis parameters

**Methods:**

#### `execute_pipeline() -> bool`
Execute the complete analysis pipeline with error handling.

**Returns:**
- `bool`: True if pipeline executed successfully, False otherwise

**Raises:**
- `ConfigurationError`: If configuration is invalid
- `DataProcessingError`: If data loading or processing fails
- `AnalysisError`: If network analysis fails
- `VisualizationError`: If visualization generation fails

**Example:**
```python
from FollowWeb_Visualizor.main import PipelineOrchestrator
from FollowWeb_Visualizor.core.config import get_configuration_manager, FollowWebConfig

# Create configuration
config_dict = {
    'input_file': 'my_data.json',
    'output_file_prefix': 'MyAnalysis',
    'strategy': 'k-core'
}

# Load and validate configuration
config_manager = get_configuration_manager()
config = config_manager.load_configuration(config_dict=config_dict)

# Execute pipeline
orchestrator = PipelineOrchestrator(config)
success = orchestrator.execute_pipeline()
```

## Configuration Module (`config.py`)

### Core Functions

#### `load_config_from_dict(config_dict: Dict[str, Any]) -> FollowWebConfig`
Creates a FollowWebConfig instance from a dictionary.

**Parameters:**
- `config_dict`: Configuration dictionary with analysis parameters

**Returns:**
- `FollowWebConfig`: Validated configuration instance

**Raises:**
- `ConfigurationError`: If configuration is invalid with detailed error message

#### `get_configuration_manager() -> EnhancedConfigurationManager`
Get a configured instance of the EnhancedConfigurationManager.

**Returns:**
- `EnhancedConfigurationManager`: Configured manager instance for loading and validating configurations

### Configuration Classes

#### `FollowWebConfig`
Main configuration dataclass containing all analysis parameters.

```python
@dataclass
class FollowWebConfig:
    input_file: str
    output_file_prefix: str = "FollowWeb"
    strategy: str = "k-core"
    ego_username: Optional[str] = None
    contact_path_target: Optional[str] = None
    min_followers_in_network: int = 50
    min_fame_ratio: float = 2.0
    find_paths_to_all_famous: bool = True
    
    # Nested configuration sections
    pipeline: PipelineConfig
    analysis_mode: AnalysisModeConfig
    output: OutputConfig
    k_values: KValueConfig
    visualization: VisualizationConfig
```

#### `EnhancedConfigurationManager`
Manager class for loading, validating, and processing configurations.

```python
class EnhancedConfigurationManager:
    def load_configuration(self, config_file: Optional[str] = None, config_dict: Optional[Dict] = None) -> FollowWebConfig
    def validate_configuration(self, config: FollowWebConfig) -> ValidationResult
    def serialize_configuration(self, config: FollowWebConfig) -> Dict[str, Any]
```

## Analysis Module (`analysis.py`)

Core network analysis algorithms and graph processing operations.

### `DataLoader` (Abstract Base Class)

Abstract base class defining the interface for all data loaders.

**Location**: `FollowWeb_Visualizor/data/loaders/base.py`

```python
class DataLoader(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None
    
    @abstractmethod
    def fetch_data(self, **params) -> Dict[str, Any]:
        """Fetch raw data from source."""
    
    @abstractmethod
    def build_graph(self, data: Dict[str, Any]) -> nx.DiGraph:
        """Convert raw data to NetworkX directed graph."""
    
    def load(self, **params) -> nx.DiGraph:
        """Complete loading workflow: fetch data and build graph."""
```

**Methods:**

#### `__init__(config: Optional[Dict[str, Any]] = None)`
Initialize loader with optional configuration.

**Parameters:**
- `config`: Optional configuration dictionary

#### `fetch_data(**params) -> Dict[str, Any]`
Fetch raw data from source. Must be implemented by subclasses.

**Parameters:**
- `**params`: Source-specific parameters

**Returns:**
- `Dict[str, Any]`: Raw data dictionary

**Raises:**
- `DataProcessingError`: If data fetching fails

#### `build_graph(data: Dict[str, Any]) -> nx.DiGraph`
Convert raw data to NetworkX directed graph. Must be implemented by subclasses.

**Parameters:**
- `data`: Raw data from fetch_data()

**Returns:**
- `nx.DiGraph`: NetworkX directed graph with nodes and edges

**Raises:**
- `DataProcessingError`: If graph construction fails

#### `load(**params) -> nx.DiGraph`
Complete loading workflow: fetch data and build graph.

This is the main entry point for pipeline integration. It orchestrates
fetch_data() and build_graph() methods and validates the result.

**Parameters:**
- `**params`: Source-specific parameters passed to fetch_data()

**Returns:**
- `nx.DiGraph`: Validated directed graph

**Raises:**
- `DataProcessingError`: If loading or validation fails

### `InstagramLoader`

Concrete implementation for loading Instagram follower/following network data.

**Location**: `FollowWeb_Visualizor/data/loaders/instagram.py`

```python
class InstagramLoader(DataLoader):
    def __init__(self) -> None
```

#### `load(filepath: str) -> nx.DiGraph`
Load a directed graph from a JSON file with comprehensive error handling.

This is the main entry point for loading Instagram network data. It orchestrates
the fetch_data() and build_graph() methods defined by the DataLoader interface.

**Parameters:**
- `filepath`: Path to JSON file containing Instagram network data

**Returns:**
- `nx.DiGraph`: Loaded directed graph with node and edge attributes

**Raises:**
- `FileNotFoundError`: If input file doesn't exist
- `JSONDecodeError`: If JSON format is invalid
- `DataProcessingError`: If data structure is invalid

**Expected JSON Format:**
```json
[
  {
    "user": "username1",
    "followers": ["user2", "user3"],
    "following": ["user4", "user5"]
  }
]
```

**Example:**
```python
from FollowWeb_Visualizor.data.loaders.instagram import InstagramLoader

loader = InstagramLoader()
graph = loader.load(filepath='followers_following.json')
print(f"Loaded {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
```

### `FreesoundLoader`

Concrete implementation for loading Freesound audio sample network data.

**Location**: `FollowWeb_Visualizor/data/loaders/freesound.py`

```python
class FreesoundLoader(DataLoader):
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None
```

#### `__init__(config: Optional[Dict[str, Any]] = None)`
Initialize Freesound loader with API client and rate limiter.

**Parameters:**
- `config`: Configuration dictionary with optional keys:
  - `api_key`: Freesound API key (or use FREESOUND_API_KEY env var)

**Raises:**
- `ConfigurationError`: If API key is not provided

#### `load(query: Optional[str] = None, tags: Optional[List[str]] = None, max_samples: int = 1000, include_similar: bool = True) -> nx.DiGraph`
Load audio sample network from Freesound API.

**Parameters:**
- `query`: Text search query (e.g., "drum loop")
- `tags`: List of tags to filter by (AND logic)
- `max_samples`: Maximum number of samples to fetch
- `include_similar`: Include similarity relationships (default: True)

**Returns:**
- `nx.DiGraph`: Graph with audio sample nodes and similarity edges

**Node Attributes:**
- `id`: Freesound sample ID
- `name`: Sample name/title
- `tags`: List of tags
- `duration`: Length in seconds
- `user`: Username of uploader
- `audio_url`: High-quality MP3 preview URL
- `type`: Always 'sample'

**Edge Attributes:**
- `type`: 'similar' (acoustically similar sounds)
- `weight`: Similarity score (0.0-1.0)

**Raises:**
- `DataProcessingError`: If API request fails
- `ConfigurationError`: If API key is invalid

**Example:**
```python
from FollowWeb_Visualizor.data.loaders.freesound import FreesoundLoader
import os

config = {
    'api_key': os.getenv('FREESOUND_API_KEY')
}

loader = FreesoundLoader(config)
graph = loader.load(
    query='ambient pad',
    tags=['synthesizer', 'atmospheric'],
    max_samples=300
)

print(f"Loaded {graph.number_of_nodes()} audio samples")
print(f"Found {graph.number_of_edges()} similarity relationships")

# Access node attributes
for node_id in list(graph.nodes())[:5]:
    node_data = graph.nodes[node_id]
    print(f"Sample: {node_data['name']}")
    print(f"Tags: {', '.join(node_data['tags'])}")
    print(f"Audio URL: {node_data['audio_url']}")
```

### `IncrementalFreesoundLoader`

Extended Freesound loader with incremental building and crash recovery.

**Location**: `FollowWeb_Visualizor/data/loaders/freesound.py`

```python
class IncrementalFreesoundLoader(FreesoundLoader):
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None
```

#### `__init__(config: Optional[Dict[str, Any]] = None)`
Initialize incremental loader with checkpoint support.

**Parameters:**
- `config`: Configuration dictionary with keys:
  - `api_key`: Freesound API key
  - `checkpoint_dir`: Directory for checkpoint files (default: './checkpoints/freesound')
  - `checkpoint_interval`: Save checkpoint every N samples (default: 100)
  - `max_runtime_hours`: Maximum runtime before stopping (default: None)
  - `verify_existing_sounds`: Check for deleted samples (default: False)
  - `verification_age_days`: Verify samples older than N days (default: 7)

#### `build_graph() -> nx.DiGraph`
Build graph incrementally with checkpoint support.

Loads existing checkpoint, processes new samples, saves checkpoints periodically,
and handles time limits gracefully.

**Returns:**
- `nx.DiGraph`: Graph with all processed samples

**Features:**
- Automatic checkpoint loading and saving
- Time-limited execution for scheduled jobs
- Deleted sample detection and cleanup
- Progress tracking with ETA

**Example:**
```python
from FollowWeb_Visualizor.data.loaders.freesound import IncrementalFreesoundLoader

config = {
    'api_key': 'your_api_key_here',
    'checkpoint_dir': './checkpoints/large_network',
    'checkpoint_interval': 100,
    'max_runtime_hours': 2.0,
    'verify_existing_sounds': True
}

loader = IncrementalFreesoundLoader(config)

# First run: Build for 2 hours
graph = loader.build_graph()
print(f"Session 1: {graph.number_of_nodes()} nodes")

# Second run: Continue for another 2 hours
graph = loader.build_graph()
print(f"Session 2: {graph.number_of_nodes()} nodes")
```

### `NetworkAnalyzer`

Class containing network analysis algorithms.

```python
class NetworkAnalyzer:
    def __init__(self) -> None
```

#### `detect_communities(graph: nx.DiGraph) -> nx.DiGraph`
Perform Louvain community detection with progress tracking.

**Parameters:**
- `graph`: Input directed graph

**Returns:**
- `nx.DiGraph`: Graph with community assignments added as node attributes

#### `calculate_centrality_metrics(graph: nx.DiGraph) -> nx.DiGraph`
Calculate degree, betweenness, and eigenvector centrality.

**Parameters:**
- `graph`: Input directed graph

**Returns:**
- `nx.DiGraph`: Graph with centrality metrics added as node attributes

### `PathAnalyzer`

Class for shortest path and connectivity analysis.

## Visualization Module (`visualization/renderers/`)

### `Renderer` (Abstract Base Class)

Abstract base class defining the interface for all visualization renderers.

**Location**: `FollowWeb_Visualizor/visualization/renderers/base.py`

```python
class Renderer(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None
    
    @abstractmethod
    def generate_visualization(self, graph: nx.DiGraph, output_filename: str, metrics: Optional[VisualizationMetrics] = None) -> bool:
        """Generate visualization from graph."""
    
    def get_file_extension(self) -> str:
        """Get file extension for this renderer."""
    
    def supports_large_graphs(self) -> bool:
        """Check if renderer supports large graphs (10,000+ nodes)."""
```

**Methods:**

#### `__init__(config: Optional[Dict[str, Any]] = None)`
Initialize renderer with optional configuration.

**Parameters:**
- `config`: Optional configuration dictionary

#### `generate_visualization(graph: nx.DiGraph, output_filename: str, metrics: Optional[VisualizationMetrics] = None) -> bool`
Generate visualization from graph. Must be implemented by subclasses.

**Parameters:**
- `graph`: NetworkX directed graph to visualize
- `output_filename`: Path for output file
- `metrics`: Optional pre-calculated visualization metrics

**Returns:**
- `bool`: True if visualization generated successfully

**Raises:**
- `VisualizationError`: If visualization generation fails

#### `get_file_extension() -> str`
Get file extension for this renderer.

**Returns:**
- `str`: File extension (e.g., '.html', '.png')

#### `supports_large_graphs() -> bool`
Check if renderer supports large graphs (10,000+ nodes).

**Returns:**
- `bool`: True if renderer can handle large graphs efficiently

### `SigmaRenderer`

High-performance WebGL visualization renderer using Sigma.js.

**Location**: `FollowWeb_Visualizor/visualization/renderers/sigma.py`

```python
class SigmaRenderer(Renderer):
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None
```

#### `__init__(config: Optional[Dict[str, Any]] = None)`
Initialize Sigma.js renderer with configuration.

**Parameters:**
- `config`: Configuration dictionary with optional keys:
  - `node_size_metric`: Metric for node sizing ('degree', 'betweenness', etc.)
  - `base_node_size`: Base size for nodes (default: 10.0)
  - `scaling_algorithm`: Scaling algorithm ('logarithmic' or 'linear')
  - `sigma_interactive.enable_webgl`: Use WebGL rendering (default: True)
  - `sigma_interactive.enable_search`: Enable node search (default: True)
  - `sigma_interactive.audio_player.enabled`: Enable audio playback (default: True)
  - `sigma_interactive.audio_player.show_controls`: Show player controls (default: True)
  - `sigma_interactive.audio_player.enable_loop`: Enable loop toggle (default: True)

#### `generate_visualization(graph: nx.DiGraph, output_filename: str, metrics: Optional[VisualizationMetrics] = None) -> bool`
Generate interactive Sigma.js HTML visualization with audio playback.

**Parameters:**
- `graph`: Network graph to visualize
- `output_filename`: Path for output HTML file
- `metrics`: Optional pre-calculated visualization metrics

**Returns:**
- `bool`: True if visualization generated successfully

**Features:**
- WebGL acceleration for 10,000+ nodes
- Interactive zoom, pan, and search
- Hover tooltips with node metadata
- Audio playback for Freesound networks
- Community-based coloring
- Metric-based node sizing

**Example:**
```python
from FollowWeb_Visualizor.visualization.renderers.sigma import SigmaRenderer
from FollowWeb_Visualizor.data.loaders.freesound import FreesoundLoader
import os

# Load Freesound data
loader = FreesoundLoader({'api_key': os.getenv('FREESOUND_API_KEY')})
graph = loader.load(query='ambient', max_samples=500)

# Configure renderer
config = {
    'node_size_metric': 'degree',
    'base_node_size': 10.0,
    'sigma_interactive': {
        'enable_webgl': True,
        'enable_search': True,
        'audio_player': {
            'enabled': True,
            'show_controls': True,
            'enable_loop': True
        }
    }
}

# Generate visualization
renderer = SigmaRenderer(config)
success = renderer.generate_visualization(graph, 'ambient_network.html')

if success:
    print("Visualization generated! Open ambient_network.html to explore.")
    print("Click nodes to play audio samples.")
```

### `PyvisRenderer`

Interactive HTML visualization renderer using Pyvis.

**Location**: `FollowWeb_Visualizor/visualization/renderers/pyvis.py`

```python
class PyvisRenderer(Renderer):
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None
```

#### `generate_visualization(graph: nx.DiGraph, output_filename: str, metrics: Optional[VisualizationMetrics] = None) -> bool`
Generate interactive Pyvis HTML visualization.

**Parameters:**
- `graph`: Network graph to visualize
- `output_filename`: Path for output HTML file
- `metrics`: Optional pre-calculated visualization metrics

**Returns:**
- `bool`: True if visualization generated successfully

**Features:**
- Physics-based layout simulation
- Drag and drop nodes
- Hover tooltips
- Community-based coloring
- Best for small to medium networks (< 5,000 nodes)

**Example:**
```python
from FollowWeb_Visualizor.visualization.renderers.pyvis import PyvisRenderer
from FollowWeb_Visualizor.data.loaders.instagram import InstagramLoader

# Load Instagram data
loader = InstagramLoader()
graph = loader.load(filepath='followers_following.json')

# Generate visualization
renderer = PyvisRenderer()
success = renderer.generate_visualization(graph, 'instagram_network.html')
```

```python
class PathAnalyzer:
    def __init__(self) -> None
```

#### `find_contact_path(graph: nx.DiGraph, source: str, target: str) -> Optional[List[str]]`
Find shortest path between two nodes.

**Parameters:**
- `graph`: Input directed graph
- `source`: Source node username
- `target`: Target node username

**Returns:**
- `Optional[List[str]]`: Shortest path as list of usernames, None if no path exists

### `FameAnalyzer`

Class for identifying influential accounts.

```python
class FameAnalyzer:
    def __init__(self) -> None
```

#### `identify_famous_accounts(graph: nx.DiGraph, min_followers: int, min_ratio: float) -> Tuple[List[Dict], List[Dict]]`
Identify influential accounts based on follower metrics.

**Parameters:**
- `graph`: Input directed graph
- `min_followers`: Minimum followers in network threshold
- `min_ratio`: Minimum fame ratio threshold

**Returns:**
- `Tuple[List[Dict], List[Dict]]`: (famous_accounts, high_ratio_accounts)

## Visualization Module (`visualization.py`)

Graph rendering functionality for HTML and PNG outputs.

### `OutputManager`

Main interface for managing all output generation with fine-grained control.

```python
class OutputManager:
    def __init__(self, config: Dict[str, Any]) -> None
    def generate_all_outputs(self, graph: nx.DiGraph, strategy: str, k_value: int, timing_data: Dict[str, float], output_prefix: str) -> Dict[str, bool]
```

### `MetricsCalculator`

Calculates and caches visualization metrics for both HTML and PNG outputs with centralized caching integration.

```python
class MetricsCalculator:
    def __init__(self, vis_config: Dict[str, Any]) -> None
    def calculate_all_metrics(self, graph: nx.DiGraph) -> VisualizationMetrics
    def clear_caches(self) -> None
```

**Features:**
- **Centralized Caching**: Uses the global cache manager for optimal performance
- **Shared Metrics**: Calculates metrics once and reuses across HTML and PNG outputs
- **Memory Management**: Automatic cache cleanup and size limiting

#### `calculate_node_metrics(graph: nx.DiGraph) -> Dict[str, Dict[str, Any]]`
Calculate node size, color, and positioning metrics.

**Parameters:**
- `graph`: Analyzed graph with node attributes

**Returns:**
- `Dict[str, Dict[str, Any]]`: Node metrics mapping with size, community, colors, and centrality data

**Node Metrics Structure:**
```python
{
    'username': {
        'size': float,           # Scaled node size
        'community': int,        # Community ID
        'color_hex': str,        # Hex color code
        'degree': int,           # Node degree
        'betweenness': float,    # Betweenness centrality
        'eigenvector': float     # Eigenvector centrality
    }
}
```

### `PyvisRenderer`

Class for Pyvis HTML generation with interactive network visualizations.

```python
class PyvisRenderer(Renderer):
    def __init__(self, vis_config: Dict[str, Any]) -> None
```

#### `generate_visualization(graph: nx.DiGraph, output_filename: str, metrics: Optional[VisualizationMetrics] = None) -> bool`
Generate interactive Pyvis HTML visualization.

**Parameters:**
- `graph`: Network graph to visualize
- `output_filename`: Path for output HTML file
- `metrics`: Optional pre-calculated visualization metrics

**Returns:**
- `bool`: True if generation successful

### `MatplotlibRenderer`

Class for matplotlib PNG generation with static network visualizations.

```python
class MatplotlibRenderer(Renderer):
    def __init__(self, vis_config: Dict[str, Any]) -> None
```

#### `generate_visualization(graph: nx.DiGraph, output_filename: str, metrics: Optional[VisualizationMetrics] = None) -> bool`
Generate static matplotlib PNG visualization.

**Parameters:**
- `graph`: Network graph to visualize
- `output_filename`: Path for output PNG file
- `metrics`: Optional pre-calculated visualization metrics

**Returns:**
- `bool`: True if generation successful

### `MetricsReporter`

Class for generating detailed analysis reports.

```python
class MetricsReporter:
    def __init__(self, vis_config: Dict[str, Any]) -> None
```

#### `generate_analysis_report(graph: nx.DiGraph, config: Dict, strategy: str, k_value: int, timing_data: Dict) -> str`
Generate detailed text report with analysis metrics and parameters.

**Parameters:**
- `graph`: Analyzed network graph
- `config`: Complete configuration dictionary
- `strategy`: Analysis strategy used
- `k_value`: K-value used for pruning
- `timing_data`: Execution timing information

**Returns:**
- `str`: Formatted analysis report

## Utilities Module (`utils.py`)

Shared helper functions, common operations, and centralized caching system.

### Centralized Caching System

FollowWeb includes a comprehensive caching system that eliminates duplicate calculations and optimizes memory usage.

#### `CentralizedCache`

Main caching class that manages all cached data with automatic size limiting and timeout management.

```python
class CentralizedCache:
    def __init__(self) -> None
    def calculate_graph_hash(self, graph: nx.Graph) -> str
    def get_cached_undirected_graph(self, graph: nx.DiGraph) -> nx.Graph
    def get_cached_node_attributes(self, graph: nx.Graph, attribute_name: str) -> Dict[str, Any]
    def get_cached_edge_attributes(self, graph: nx.Graph, attribute_name: str) -> Dict[Tuple[str, str], Any]
    def get_cached_community_colors(self, num_communities: int) -> Optional[Dict[str, Dict[int, Union[str, Tuple[float, ...]]]]]
    def cache_layout_positions(self, graph: nx.Graph, layout_type: str, positions: Dict[str, Tuple[float, float]], params: Dict[str, Any] = None) -> None
    def get_cached_layout_positions(self, graph: nx.Graph, layout_type: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Tuple[float, float]]]
    def clear_all_caches(self) -> None
    def get_cache_stats(self) -> Dict[str, int]
```

#### `get_cache_manager() -> CentralizedCache`
Get the global cache manager instance.

**Returns:**
- `CentralizedCache`: Global cache manager instance

#### `calculate_graph_hash(graph: nx.Graph) -> str`
Centralized graph hashing function with caching.

**Parameters:**
- `graph`: NetworkX graph to hash

**Returns:**
- `str`: Standardized SHA-256 hash string for the graph

#### `get_cached_undirected_graph(graph: nx.DiGraph) -> nx.Graph`
Get cached undirected version of a directed graph.

**Parameters:**
- `graph`: Directed graph to convert

**Returns:**
- `nx.Graph`: Cached undirected version

#### `get_cached_node_attributes(graph: nx.Graph, attribute_name: str) -> Dict[str, Any]`
Get cached node attributes to avoid repeated graph traversals.

**Parameters:**
- `graph`: NetworkX graph
- `attribute_name`: Name of the node attribute to retrieve

**Returns:**
- `Dict[str, Any]`: Cached node attributes

#### `get_cached_community_colors(num_communities: int) -> Dict[str, Dict[int, Union[str, Tuple[float, ...]]]]`
Get cached community colors, generating them if not cached.

**Parameters:**
- `num_communities`: Number of communities to generate colors for

**Returns:**
- `Dict[str, Dict[int, Union[str, Tuple[float, ...]]]]`: Cached color scheme

#### `clear_all_caches() -> None`
Clear all caches - useful for testing and memory management.

**Performance Benefits:**
- **Graph Hashing**: ~90% reduction in hash calculation time
- **Graph Conversion**: ~95% reduction in `to_undirected()` overhead  
- **Attribute Access**: ~80% reduction in graph traversal time
- **Color Generation**: ~99% reduction for repeated color scheme requests

### File Operations

#### `generate_output_filename(prefix: str, strategy: str, k_value: int, extension: str) -> str`
Generate unique output filename with timestamp and hash.

**Parameters:**
- `prefix`: File prefix (e.g., 'FollowWeb')
- `strategy`: Analysis strategy name
- `k_value`: K-value used
- `extension`: File extension (e.g., 'html', 'png', 'txt')

**Returns:**
- `str`: Generated filename

#### `ensure_output_directory(filepath: str) -> None`
Create output directory if it doesn't exist.

**Parameters:**
- `filepath`: Full file path

**Raises:**
- `OSError`: If directory creation fails

### Visual Utilities

#### `get_community_colors(num_communities: int) -> Dict[str, Dict[str, Any]]`
Generate color mappings for community visualization.

**Parameters:**
- `num_communities`: Number of communities to generate colors for

**Returns:**
- `Dict[str, Dict[str, Any]]`: Color mapping dictionary

#### `get_scaled_size(value: float, base_size: float, multiplier: float, algorithm: str) -> float`
Apply logarithmic or linear scaling to numeric values.

**Parameters:**
- `value`: Value to scale
- `base_size`: Base size for scaling
- `multiplier`: Scaling multiplier
- `algorithm`: Scaling algorithm ('logarithmic' or 'linear')

**Returns:**
- `float`: Scaled value

**Raises:**
- `ValueError`: If algorithm is not 'logarithmic' or 'linear'

### Math Utilities

#### `safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float`
Perform safe division with fallback for zero denominator.

**Parameters:**
- `numerator`: Numerator value
- `denominator`: Denominator value  
- `default`: Default value if denominator is zero

**Returns:**
- `float`: Division result or default value

#### `format_time_duration(seconds: float) -> str`
Format duration in human-readable format.

**Parameters:**
- `seconds`: Duration in seconds

**Returns:**
- `str`: Formatted duration string

**Raises:**
- `ValueError`: If duration is negative

## Progress Module (`progress.py`)

Progress tracking for long-running operations.

### `ProgressTracker`

Enhanced progress tracking with time estimation.

```python
class ProgressTracker:
    def __init__(self, total: int, title: str, num_updates: int = 10, threshold_sec: float = 3.0) -> None
```

**Parameters:**
- `total`: Total number of items to process
- `title`: Description of the operation
- `num_updates`: Number of progress updates to display
- `threshold_sec`: Minimum duration before showing progress

#### `update(current_item: int) -> None`
Update progress with current iteration count.

**Parameters:**
- `current_item`: Current item number (0-based)

#### `complete() -> None`
Mark operation as complete and display final statistics.

**Context Manager Usage:**
```python
with ProgressTracker(total=1000, title="Processing items") as tracker:
    for i in range(1000):
        # Do work
        tracker.update(i)
    # Automatically calls complete() on exit
```

## Error Classes

### Custom Exceptions

All custom exceptions inherit from the base `FollowWebError` class for consistent error handling.

#### `FollowWebError`
Base exception class for all FollowWeb-specific errors.

#### `ConfigurationError`
Raised when configuration validation fails.

#### `DataProcessingError`
Raised when data loading or processing fails.

#### `VisualizationError`
Raised when visualization generation fails.

## Usage Examples

### Complete Pipeline Example
```python
from FollowWeb_Visualizor.main import PipelineOrchestrator
from FollowWeb_Visualizor.core.config import get_configuration_manager

# Create configuration dictionary
config_dict = {
    'input_file': 'my_network_data.json',
    'output_file_prefix': 'MyAnalysis',
    'strategy': 'reciprocal_k-core',
    'k_values': {
        'strategy_k_values': {
            'reciprocal_k-core': 3
        }
    }
}

# Load and validate configuration
config_manager = get_configuration_manager()
config = config_manager.load_configuration(config_dict=config_dict)

# Execute pipeline
orchestrator = PipelineOrchestrator(config)
success = orchestrator.execute_pipeline()

if success:
    print("Analysis completed successfully!")
else:
    print("Analysis failed. Check logs for details.")
```

### Custom Analysis Example
```python
from FollowWeb_Visualizor.data.loaders import InstagramLoader
from FollowWeb_Visualizor.analysis.network import NetworkAnalyzer
from FollowWeb_Visualizor.visualization.metrics import MetricsCalculator

# Load graph
loader = InstagramLoader()
graph = loader.load(filepath='data.json')

# Analyze network
analyzer = NetworkAnalyzer()
graph = analyzer.detect_communities(graph)
graph = analyzer.calculate_centrality_metrics(graph)

# Generate visualization metrics
vis_config = {
    'node_size_metric': 'degree', 
    'base_node_size': 15.0,
    'node_size_multiplier': 2.0,
    'scaling_algorithm': 'logarithmic'
}
calculator = MetricsCalculator(vis_config)
node_metrics = calculator.calculate_node_metrics(graph)
```

### Configuration Validation Example
```python
from FollowWeb_Visualizor.core.config import get_configuration_manager, ConfigurationError

config_dict = {
    'input_file': 'data.json',
    'strategy': 'invalid-strategy'
}

try:
    config_manager = get_configuration_manager()
    config = config_manager.load_configuration(config_dict=config_dict)
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    # Handle configuration error
```

## Type Hints

The package uses comprehensive type hints throughout. Key type aliases:

```python
from typing import Dict, List, Optional, Tuple, Any, Union
import networkx as nx

# Common type aliases used in the API
NodeMetrics = Dict[str, Dict[str, Any]]
EdgeMetrics = Dict[Tuple[str, str], Dict[str, Any]]
ConfigDict = Dict[str, Any]
PathList = Optional[List[str]]
CommunityMapping = Dict[str, int]
```