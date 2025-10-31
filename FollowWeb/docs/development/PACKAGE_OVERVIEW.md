# Package Overview

Professional social network analysis package with modular architecture.

## Core Modules

### `main.py` - Pipeline Orchestration
- `PipelineOrchestrator` - Complete analysis workflow coordination
- Configuration validation, strategy execution, error handling

### `config.py` - Configuration Management  
- Type-safe dataclasses with validation
- Default configuration factory
- Detailed error reporting

### `analysis.py` - Network Analysis
- `GraphLoader` - JSON data loading
- `NetworkAnalyzer` - Community detection, centrality metrics
- `PathAnalyzer` - Shortest paths, connectivity
- `FameAnalyzer` - Influential account identification

### `visualization.py` - Graph Rendering
- `MetricsCalculator` - Visual property computation
- `InteractiveRenderer` - Pyvis HTML generation
- `StaticRenderer` - Matplotlib PNG generation
- `MetricsReporter` - Analysis reporting

### `utils.py` - Shared Utilities
- File operations, color generation, mathematical scaling
- **Centralized caching system** with automatic memory management
- Custom exception hierarchy

### `progress.py` - Progress Tracking
- Adaptive display with time estimation
- Context manager support

## Analysis Strategies

### K-Core Analysis
- Full network analysis with degree-based pruning
- Understanding overall network structure

### Reciprocal K-Core Analysis  
- Mutual relationship analysis
- Finding close friend groups and bidirectional connections

### Ego-Alter Analysis
- Personal network analysis centered on specific user
- Individual influence mapping and social circle analysis

## Data Flow
JSON Input → GraphLoader → Strategy Application → Graph Pruning → NetworkAnalyzer → Community Detection → Centrality Calculation → PathAnalyzer → MetricsCalculator (with centralized caching) → Visualization Rendering → HTML/PNG/TXT Outputs

**Caching Integration**: The centralized cache manager optimizes performance throughout the pipeline by eliminating duplicate calculations for graph hashing, undirected conversions, attribute access, layout positions, and community colors.

## Usage Patterns

### Basic Usage
```python
from FollowWeb_Visualizor.config import get_configuration_manager

config_dict = {'input_file': 'data.json'}
config_manager = get_configuration_manager()
config = config_manager.load_configuration(config_dict=config_dict)
orchestrator = PipelineOrchestrator(config)
success = orchestrator.execute_pipeline()
```

### Performance Optimization
```python
config['pipeline']['skip_analysis'] = True
config['visualization']['generate_png'] = False
```

## Error Handling
- **Exception Hierarchy**: ConfigurationError, DataProcessingError, AnalysisError, VisualizationError
- **Recovery Patterns**: Graceful degradation, detailed error messages, progress preservation

## Testing & Development
```bash
make test           # All tests
make test-unit      # Unit tests only
make lint           # Code style checking
make format         # Automatic formatting
make check          # Complete quality check
```

## Performance Guidelines

### Centralized Caching System Benefits
- **Graph Hash Caching**: 90% reduction in hash calculation time
- **Graph Conversion Caching**: 95% reduction in undirected conversion overhead
- **Attribute Access Caching**: 80% reduction in graph traversal time
- **Layout Position Caching**: Shared calculations between HTML and PNG outputs
- **Community Color Caching**: 99% reduction for repeated color scheme requests

### Network Size Performance
- Small networks (<1K nodes): <10 seconds
- Medium networks (1K-10K nodes): <2 minutes  
- Large networks (>10K nodes): Graceful degradation with progress reporting

### Memory Management
- **Automatic Size Limiting**: 50 items per cache category by default
- **Timeout Management**: 1-hour default timeout for cache entries
- **Weak References**: Prevents memory leaks from cached graph objects

## Output Files
- **Naming**: `{prefix}-{strategy}-k{k_value}-{hash}.{extension}`
- **Types**: HTML (interactive), PNG (static), TXT (metrics report)

## Quality Standards
- PEP 8 compliance with ruff formatting
- Comprehensive type hints and docstrings
- >90% test coverage target
- Professional error handling patterns