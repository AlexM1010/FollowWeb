# FollowWeb

[![Freesound Nightly Pipeline](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-nightly-pipeline.yml/badge.svg)](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-nightly-pipeline.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Network analysis and visualization tool that transforms connection data into interactive visualizations with automatic community detection, influence metrics, and audio playback capabilities.

**🎵 [Live Demo: Freesound Network Explorer](https://alexm1010.github.io/FollowWeb/)** - Interactive network of 1000+ audio samples with click-to-play audio, automatically updated nightly.

---

## Features

- **Multiple Data Sources**: Instagram social networks and Freesound audio sample networks
- **High-Performance Visualization**: Sigma.js renderer with WebGL acceleration supporting 10,000+ nodes
- **Audio Playback**: Click-to-play audio samples directly in network visualizations (Freesound)
- **Advanced Analysis**: k-core decomposition, reciprocal connections, ego-alter analysis, centrality metrics
- **Automated Pipeline**: Nightly data collection with parallel milestone execution and validation
- **Production Ready**: 337 passing tests with 73.95% code coverage

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/AlexM1010/FollowWeb.git
cd FollowWeb

# Install the package
cd FollowWeb
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### Basic Usage

```bash
# Analyze Instagram network
followweb --input examples/followers_following.json

# Analyze Freesound audio samples
followweb --data-source freesound --renderer-type sigma --freesound-query "jungle"

# Use a configuration file
followweb --config configs/freesound_sigma_config.json
```

## Use Cases

### 1. Instagram Social Networks
Analyze follower/following relationships from Instagram JSON exports:
- Identify influential users and community structures
- Discover reciprocal connections and mutual relationships
- Visualize your personal network with ego-alter analysis

### 2. Freesound Audio Networks
Explore audio sample similarity networks from the Freesound API:
- Interactive visualization with click-to-play audio
- Discover related sounds through network connections
- Automated nightly collection building a growing audio library

## Architecture Highlights

### Split Checkpoint System
Scalable architecture for handling large networks:
- **Graph Topology**: NetworkX graph with edges only (.gpickle)
- **SQLite Metadata**: Indexed database for sample metadata (.db)
- **Checkpoint Metadata**: Processing state and metrics (.json)

**Benefits**: 50x faster I/O, 20-30% speed improvement, scales to millions of nodes

### Automated Freesound Pipeline
Nightly data collection with advanced features:
- **Parallel Milestone Execution**: 4-core processing at every 100-node milestone
- **Automated Validation**: Checkpoint integrity verification and anomaly detection
- **Network Enrichment**: User and pack relationship edges
- **Public Deployment**: GitHub Pages with growth metrics dashboard
- **Tiered Backup Retention**: Intelligent retention policy (14-day to permanent)

### Visualization Engines
Three rendering options for different needs:
- **Sigma.js**: High-performance WebGL for large networks (10,000+ nodes) with audio playback
- **Pyvis**: Interactive HTML with physics simulation and hover tooltips
- **Matplotlib**: Static PNG images for presentations and papers

## Project Structure

```
FollowWeb/
├── FollowWeb/                      # Main Python package
│   ├── FollowWeb_Visualizor/       # Core package code
│   │   ├── analysis/               # Network analysis algorithms
│   │   ├── data/                   # Data loading and storage
│   │   ├── visualization/          # Rendering engines
│   │   └── utils/                  # Utilities and helpers
│   ├── tests/                      # Comprehensive test suite
│   ├── configs/                    # Configuration presets
│   ├── examples/                   # Sample data
│   └── docs/                       # Documentation
├── scripts/                        # Pipeline and utility scripts
├── Output/                         # Generated visualizations
├── data/                           # Pipeline data (gitignored)
└── Docs/                           # Project documentation
```

## Documentation

### Getting Started
- **[Installation Guide](FollowWeb/docs/INSTALL_GUIDE.md)** - Detailed setup instructions
- **[User Guide](FollowWeb/docs/USER_GUIDE.md)** - Tutorials and workflows
- **[Quick Start: Freesound](FollowWeb/docs/QUICK_START_FREESOUND.md)** - 5-minute Freesound guide
- **[Configuration Guide](FollowWeb/docs/CONFIGURATION_GUIDE.md)** - Configuration options

### Advanced Topics
- **[Freesound Pipeline](Docs/FREESOUND_PIPELINE.md)** - Complete pipeline documentation
- **[API Reference](FollowWeb/docs/development/API_REFERENCE.md)** - Complete API documentation
- **[Contributing](FollowWeb/docs/development/CONTRIBUTING.md)** - Development guidelines

## Testing

Comprehensive test suite with 337 passing tests:

```bash
# Run all tests with coverage
pytest --cov=FollowWeb_Visualizor --cov-report=term-missing

# Run specific test categories
pytest tests/unit/          # Unit tests (fast, parallel)
pytest tests/integration/   # Integration tests (cross-module)
pytest tests/performance/   # Performance benchmarks (sequential)

# Run tests in parallel
pytest -n auto
```

See **[tests/README.md](FollowWeb/tests/README.md)** for detailed testing procedures.

## Technology Stack

- **Python**: 3.9+ (supports 3.9, 3.10, 3.11, 3.12)
- **Core Libraries**: NetworkX, NumPy, pandas, matplotlib
- **Visualization**: Sigma.js (WebGL), Pyvis, matplotlib
- **Audio**: Tone.js for synchronized multi-sample playback
- **Data Storage**: SQLite with WAL mode, pickle for graph topology
- **Testing**: pytest with xdist for parallel execution
- **CI/CD**: GitHub Actions with automated workflows

## Performance

- **Caching System**: 80-95% reduction in hash/conversion overhead
- **Parallel Processing**: nx-parallel for graph operations (Python 3.11+)
- **SQLite Optimizations**: Batch writes, WAL mode, indexed queries
- **Worker Auto-Detection**: Optimal parallelization based on CPU cores and memory

## Current Statistics

Visit the [Freesound Network Explorer](https://alexm1010.github.io/FollowWeb/) to see:
- Total nodes and edges in the network
- Growth metrics over time
- Latest interactive visualization
- Milestone history

## Contributing

Contributions are welcome! Please see **[CONTRIBUTING.md](FollowWeb/docs/development/CONTRIBUTING.md)** for:
- Development setup
- Code style guidelines
- Testing requirements
- Pull request process

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

Built with excellent open-source libraries:
- **[NetworkX](https://networkx.org/)** - Graph analysis algorithms
- **[Sigma.js](https://www.sigmajs.org/)** - High-performance WebGL visualization
- **[Tone.js](https://tonejs.github.io/)** - Web Audio framework
- **[Freesound API](https://github.com/MTG/freesound-api)** - Official Freesound client

See **[docs/attribution/CONTRIBUTORS.md](FollowWeb/docs/attribution/CONTRIBUTORS.md)** for complete acknowledgments.

## Links

- **[Live Demo](https://alexm1010.github.io/FollowWeb/)** - Freesound Network Explorer
- **[Documentation](FollowWeb/docs/)** - Complete documentation
- **[Package Source](FollowWeb/)** - Main Python package
- **[Issue Tracker](https://github.com/AlexM1010/FollowWeb/issues)** - Report bugs or request features
