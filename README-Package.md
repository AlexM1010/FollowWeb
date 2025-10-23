# FollowWeb Network Analysis Package

A comprehensive social network analysis tool for visualizing Instagram follower/following relationships using graph theory and network analysis techniques.

## Overview

FollowWeb transforms social media connection data into interactive network visualizations with advanced analytics. The package provides multiple analysis strategies, community detection, centrality metrics, and professional-quality outputs suitable for research, presentations, and social media analysis.

## Key Features

### Analysis Strategies
- **K-Core Analysis**: Full network analysis identifying densely connected subgraphs
- **Reciprocal K-Core**: Focus on mutual connections and bidirectional relationships  
- **Ego-Alter Analysis**: Personal network analysis centered on specific users

### Visualization Outputs
- **Interactive HTML**: Network graphs with hover tooltips, physics simulation, and dynamic controls
- **Static PNG**: High-resolution images (up to 300 DPI) for presentations and publications
- **Metrics Reports**: Detailed text reports with network statistics and configuration parameters

### Advanced Analytics
- **Community Detection**: Louvain algorithm for identifying social clusters and groups
- **Centrality Metrics**: Degree, betweenness, and eigenvector centrality calculations
- **Path Analysis**: Six degrees of separation analysis and contact path finding
- **Fame Analysis**: Identification of influential accounts with customizable criteria

## Installation

### From PyPI (Recommended)
```bash
pip install followweb-visualizor
```

### Development Installation
```bash
git clone <repository-url>
cd followweb-visualizor
pip install -e .
```

### With Development Dependencies
```bash
pip install followweb-visualizor[dev]
```

## Quick Start

### Basic Usage
```python
from FollowWeb_Visualizor.main import PipelineOrchestrator
from FollowWeb_Visualizor.config import get_configuration_manager

# Load configuration
config_manager = get_configuration_manager()
config = config_manager.load_configuration(
    config_dict={'input_file': 'your_data.json'}
)

# Execute analysis pipeline
orchestrator = PipelineOrchestrator(config)
success = orchestrator.execute_pipeline()
```

### Command Line Interface
```bash
# Basic analysis
followweb --input data.json --strategy k-core

# With custom configuration
followweb --config my_config.json

# Ego-alter analysis
followweb --input data.json --strategy ego_alter_k-core --ego-username target_user
```

## Data Format

### JSON Input Format
```json
[
  {
    "user": "username1",
    "followers": ["user2", "user3", "user4"],
    "following": ["user5", "user6", "user7"]
  }
]
```

### Legacy TXT Format (3-line pattern)
```
username
follower1,follower2,follower3
following1,following2,following3
```

## Configuration

The package supports flexible configuration through:
- JSON configuration files
- Command-line arguments
- Python dictionary configuration
- Environment variables

### Example Configuration
```python
config = {
    'input_file': 'followers_following.json',
    'pipeline': {
        'strategy': 'k-core',
        'skip_analysis': False
    },
    'pruning': {
        'k_values': {
            'k-core': 1,
            'reciprocal_k-core': 2,
            'ego_alter_k-core': 5
        }
    },
    'visualization': {
        'static_image': {
            'generate': True,
            'dpi': 300
        }
    }
}
```

## Output Files

### File Naming Convention
- **Pattern**: `FollowWeb-{strategy}-k{value}-{hash}.{extension}`
- **Extensions**: `.html` (interactive), `.png` (static), `.txt` (reports)

### Example Outputs
- `FollowWeb-k-core-k1-a1b2c3.html` - Interactive visualization
- `FollowWeb-k-core-k1-a1b2c3.png` - Static high-resolution image
- `FollowWeb-k-core-k1-a1b2c3.txt` - Detailed metrics report

## Requirements

- **Python**: 3.8 or higher
- **Core Dependencies**: NetworkX, pandas, matplotlib, pyvis
- **Optional**: pytest, black, mypy (for development)

## Architecture

### Modular Design
- **main.py**: Pipeline orchestration and entry points
- **config.py**: Configuration management with validation
- **analysis.py**: Network analysis algorithms and graph processing
- **visualization.py**: Graph rendering for HTML and PNG outputs
- **utils.py**: Shared utilities and helper functions
- **progress.py**: Progress tracking for long-running operations

### Professional Standards
- Full type annotation throughout codebase
- Comprehensive error handling with custom exceptions
- Extensive test coverage with unit, integration, and performance tests
- Code quality enforcement with linting and formatting
- Detailed documentation and API reference

## Development

### Setup Development Environment
```bash
git clone <repository-url>
cd followweb-visualizor
pip install -e .[dev]
```

### Run Tests
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# With coverage
pytest --cov=FollowWeb_Visualizor
```

### Code Quality
```bash
# Format code
black FollowWeb_Visualizor/
isort FollowWeb_Visualizor/

# Lint code
flake8 FollowWeb_Visualizor/

# Type checking
mypy FollowWeb_Visualizor/
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for guidelines on:
- Setting up development environment
- Running tests and quality checks
- Submitting pull requests
- Code style and standards

## Support

- **Documentation**: See `docs/` directory for detailed guides
- **Issues**: Report bugs and feature requests via GitHub issues
- **API Reference**: Complete function documentation in `docs/API_REFERENCE.md`

## Acknowledgments

This package was developed with assistance from Kiro AI for package architecture, testing infrastructure, and documentation creation.