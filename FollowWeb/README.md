# FollowWeb Network Analysis Package

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/followweb-visualizor.svg)](https://badge.fury.io/py/followweb-visualizor)

Network analysis and visualization tool for social networks and audio sample relationships with automatic community detection and influence metrics.

## Features

- **Multiple Data Sources**: Instagram social networks and Freesound audio sample networks
- **High-Performance Visualization**: Sigma.js renderer with WebGL acceleration for 10,000+ nodes
- **Audio Playback**: Interactive audio sample playback in network visualizations
- **Advanced Analysis**: k-core decomposition, reciprocal connections, ego-alter analysis, centrality metrics
- **Community Detection**: Automatic community identification using Louvain algorithm
- **Multiple Renderers**: Sigma.js (interactive WebGL), Pyvis (physics simulation), Matplotlib (static)

## Installation

```bash
pip install followweb-visualizor
```

## Quick Start

### Instagram Network Analysis

```bash
# Analyze Instagram follower/following relationships
followweb --input followers_following.json --strategy k-core
```

### Freesound Audio Network

```bash
# Create interactive audio sample network
followweb --data-source freesound --renderer-type sigma --freesound-query "ambient"
```

### Using Configuration Files

```bash
# Use pre-configured settings
followweb --config configs/freesound_sigma_config.json
```

## Command Line Options

```bash
followweb [OPTIONS]

Data Source:
  --input PATH              Instagram JSON file path
  --data-source TYPE        Data source: instagram or freesound
  --freesound-query TEXT    Search query for Freesound samples

Analysis:
  --strategy TYPE           Analysis strategy: k-core, reciprocal, ego-alter
  --analysis-mode MODE      Analysis depth: fast, medium, full
  --k-value INT            K-value for k-core decomposition

Visualization:
  --renderer-type TYPE      Renderer: sigma, pyvis, matplotlib
  --output-dir PATH         Output directory (default: Output/)
  --skip-visualization      Skip visualization generation

Configuration:
  --config PATH            JSON configuration file
```

## Python API

```python
from FollowWeb_Visualizor.main import run_pipeline
from FollowWeb_Visualizor.core.config import Config

# Create configuration
config = Config(
    input_file="followers_following.json",
    strategy="k-core",
    renderer_type="sigma",
    analysis_mode="medium"
)

# Run analysis pipeline
run_pipeline(config)
```

## Analysis Strategies

- **k-core**: Identifies densely connected subgraphs by iteratively removing low-degree nodes
- **reciprocal**: Analyzes mutual connections (bidirectional relationships)
- **ego-alter**: Focuses on personal network structure around specific nodes

## Output Files

- **HTML**: Interactive network visualization with hover tooltips and zoom
- **PNG**: High-resolution static network image
- **TXT**: Analysis report with metrics and statistics
- **JSON**: Graph data for custom processing

## Documentation

Full documentation available at: https://github.com/AlexM1010/FollowWeb/tree/main/Docs

- [User Guide](docs/USER_GUIDE.md)
- [Configuration Guide](docs/CONFIGURATION_GUIDE.md)
- [Freesound Integration](docs/FREESOUND_GUIDE.md)
- [API Reference](docs/development/API_REFERENCE.md)

## Requirements

- Python 3.9+
- NetworkX >= 2.8.0
- pandas >= 1.5.0
- matplotlib >= 3.5.0
- pyvis >= 0.3.0

## License

MIT License - see LICENSE file for details

## Links

- **GitHub**: https://github.com/AlexM1010/FollowWeb
- **PyPI**: https://pypi.org/project/followweb-visualizor/
- **Issues**: https://github.com/AlexM1010/FollowWeb/issues
- **Live Demo**: https://visualise.music
