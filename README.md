# FollowWeb

[![CI Pipeline](https://github.com/AlexM1010/FollowWeb/actions/workflows/ci.yml/badge.svg)](https://github.com/AlexM1010/FollowWeb/actions/workflows/ci.yml)
[![Freesound Nightly Pipeline](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-nightly-pipeline.yml/badge.svg)](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-nightly-pipeline.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Network analysis and visualization tool that transforms connection data into interactive visualizations with automatic community detection, influence metrics, and audio playback capabilities.

**🎵 [visualise.music](https://visualise.music)** *- Interactive network of 1000+ audio samples from the freesound.org API with click-to-play audio, updated/expanded nightly.*

![FollowWeb Package Demo](FollowWeb/docs/demo/FollowWeb2xSpeedDemo.gif)
*Instagram network visualization (2x speed)*

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

## Technical Highlights

### Scalable Architecture

**Split Checkpoint System** - Designed for handling large-scale networks efficiently:
- **Graph Topology**: NetworkX graph serialized with pickle for fast I/O
- **SQLite Metadata**: Indexed database with WAL mode for concurrent access
- **Checkpoint Metadata**: JSON state tracking for recovery and metrics

This architecture delivers 50x faster I/O operations and 20-30% overall speed improvement compared to monolithic pickle files, enabling the system to scale to millions of nodes without performance degradation.

### Performance Optimizations

- **Batch Processing**: SQLite writes batched at 50 samples to minimize I/O overhead
- **Centralized Caching**: 80-95% reduction in hash/conversion overhead through intelligent caching
- **Parallel Processing**: nx-parallel integration for graph operations on Python 3.11+
- **Worker Auto-Detection**: Dynamic parallelization based on CPU cores and available memory
- **Space-Efficient Audio URLs**: Stores `uploader_id` (~7 bytes) instead of full URLs (~200 bytes), enabling client-side reconstruction for 96.5% storage reduction

### Automated CI/CD Pipeline

Multi-stage workflow architecture for continuous data collection and validation:

**Five-Pipeline Architecture**:
1. **Collection Pipeline**: [![Freesound Nightly Pipeline](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-nightly-pipeline.yml/badge.svg)](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-nightly-pipeline.yml)
   - Nightly data gathering (Mon-Sat 2 AM UTC) with circuit breaker (1,950 requests/day)
2. **Repair Pipeline**: [![Freesound Data Repair](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-data-repair.yml/badge.svg)](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-data-repair.yml)
   - Validates and repairs data integrity issues
3. **Validation Pipeline**: [![Freesound Quick Validation](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-quick-validation.yml/badge.svg)](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-quick-validation.yml) [![Freesound Full Validation](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-full-validation.yml/badge.svg)](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-full-validation.yml)
   - Weekly quick validation (300 samples, Sunday) and monthly full validation
4. **Backup Pipeline**: [![Freesound Backup](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-backup.yml/badge.svg)](https://github.com/AlexM1010/FollowWeb/actions/workflows/freesound-backup.yml)
   - Creates and manages tiered backups
5. **Publish Pipeline**: [![Deploy Pages](https://github.com/AlexM1010/FollowWeb/actions/workflows/pages.yml/badge.svg)](https://github.com/AlexM1010/FollowWeb/actions/workflows/pages.yml)
   - Deploys visualizations to GitHub Pages

**Key Design Decisions**:
- **Ephemeral Cache Strategy**: Workflow cache populated from private repo at start, wiped at end
- **Fail-Fast Backup**: Pipeline fails if backup fails (no data collection without successful backup)
- **Parallel Milestone Execution**: 4-core processing at every 100-node milestone
- **TOS-Compliant Storage**: Private GitHub repository for checkpoint backups (graph topology only)
- **Tiered Retention**: Frequent (14-day) → Moderate → Milestone → Permanent backups

### Visualization Engines

Three specialized rendering engines with a consistent interface pattern:
- **SigmaRenderer**: WebGL-accelerated visualization using Jinja2 templates for 10,000+ node networks
- **PyvisRenderer**: Physics-based interactive HTML with hover tooltips for exploratory analysis
- **MatplotlibRenderer**: Static PNG generation for presentations and publications

Each renderer implements a common base interface, enabling easy extension and consistent behavior across visualization types.

### Production-Grade Testing

Comprehensive test suite with 337 passing tests organized by execution profile:
- **Unit Tests**: Fast, isolated tests with maximum parallelization
- **Integration Tests**: Cross-module tests with controlled parallelization
- **Performance Tests**: Sequential execution for accurate timing benchmarks
- **Benchmark Tests**: Regression detection for performance-critical paths

Test infrastructure includes worker isolation, CI-optimized configurations, and intelligent dataset selection based on test requirements.

## Design Decisions

### Modular Architecture

Clear architectural boundaries between components:
- **Data Layer**: Loaders (Instagram, Freesound), storage (SQLite metadata cache), and checkpoint management
- **Analysis Layer**: Network algorithms (k-core, centrality) and metrics calculation
- **Visualization Layer**: Rendering engines (Sigma.js, Pyvis, matplotlib) and output formatting
- **Utility Layer**: Progress tracking, validation, rate limiting, and parallel processing

This separation enables independent testing, easier maintenance, and flexible composition of pipeline stages.

### Incremental Data Collection

The Freesound loader implements a pagination-based incremental collection strategy:
- **Checkpoint Recovery**: Automatic resume from last successful state
- **Duplicate Detection**: SQLite-based deduplication before API requests
- **Rate Limiting**: Tenacity-based retry logic with exponential backoff
- **Circuit Breaker**: Configurable request limits to prevent API quota exhaustion

### Intelligent Test Configuration

Test fixtures use dataset-aware k-value calculation:
- **Dynamic K-Values**: Calculated based on degree distribution, density, and reciprocity
- **Dataset Scaling**: Appropriate values for tiny (5% sample) through full (100%) datasets
- **CI Optimization**: Reduced complexity for fast CI execution without sacrificing coverage
- **Performance Isolation**: Worker-specific temporary directories and memory cleanup

## Project Structure

```
FollowWeb/
├── FollowWeb/                      # Main Python package
│   ├── FollowWeb_Visualizor/       # Core package code
│   │   ├── analysis/               # Network analysis algorithms
│   │   ├── data/                   # Data loading and storage
│   │   │   ├── loaders/            # Data source loaders
│   │   │   ├── storage/            # SQLite metadata cache
│   │   │   └── checkpoint.py       # Checkpoint management
│   │   ├── visualization/          # Rendering engines
│   │   │   └── renderers/          # Sigma.js, Pyvis, matplotlib
│   │   └── utils/                  # Utilities and helpers
│   ├── tests/                      # Comprehensive test suite
│   │   ├── unit/                   # Unit tests (fast, parallel)
│   │   ├── integration/            # Integration tests
│   │   ├── performance/            # Performance benchmarks
│   │   └── conftest.py             # Shared fixtures
│   └── docs/                       # Documentation
├── .github/workflows/              # CI/CD workflows
├── Output/                         # Generated visualizations
└── data/                           # Pipeline data
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

Comprehensive test suite with 337 passing tests and 73.95% code coverage:

```bash
# Run all tests with coverage
pytest --cov=FollowWeb_Visualizor --cov-report=term-missing

# Run specific test categories
pytest -m unit -n auto              # Unit tests (fast, parallel)
pytest -m integration -n auto       # Integration tests (cross-module)
pytest -m performance               # Performance benchmarks (sequential)
pytest -m benchmark                 # Regression detection

# Run full CI pipeline locally
python FollowWeb/tests/run_tests.py all
```

**Test Infrastructure Features**:
- Worker isolation with parallel execution
- Dataset-aware configuration with intelligent k-value calculation
- CI optimization with platform-specific timeouts
- Performance isolation with memory cleanup
- Fixture caching to avoid repeated file reads

See **[tests/README.md](FollowWeb/tests/README.md)** for detailed testing procedures.

## Technology Stack

### Core Technologies
- **Python**: 3.9-3.12 with gradual typing (mypy)
- **NetworkX**: Graph analysis with nx-parallel backend for Python 3.11+
- **NumPy/pandas**: Numerical computing and data manipulation
- **SQLite**: Metadata storage with WAL mode and batch writes

### Visualization Stack
- **Sigma.js**: WebGL-accelerated rendering via CDN
- **Pyvis**: Interactive HTML with physics simulation
- **matplotlib**: Static image generation
- **Jinja2**: Template engine for HTML generation
- **Tone.js**: Web Audio framework for synchronized playback

### Development Tools
- **pytest**: Testing framework with xdist for parallelization
- **ruff**: Fast linting and formatting (replaces black, isort, flake8)
- **mypy**: Static type checking with gradual typing
- **GitHub Actions**: CI/CD with multi-stage workflows

### Data Management
- **joblib**: Atomic checkpoint serialization with compression
- **tenacity**: Retry logic with exponential backoff
- **freesound-api**: Official Freesound API client

## Performance Characteristics

- **I/O Operations**: 50x reduction through split checkpoint architecture
- **Caching**: 80-95% reduction in hash/conversion overhead
- **Parallel Processing**: Automatic worker detection based on system resources
- **Database**: Batch writes (50 samples), WAL mode, composite indexes for O(1) seed selection
- **Memory Management**: Aggressive garbage collection after integration tests

## Current Statistics

Visit the [Freesound Network Explorer](https://visualise.music) to see:
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

- **[Live Demo](https://visualise.music)** - Freesound Network Explorer
- **[Documentation](FollowWeb/docs/)** - Complete documentation
- **[Package Source](FollowWeb/)** - Main Python package
- **[Issue Tracker](https://github.com/AlexM1010/FollowWeb/issues)** - Report bugs or request features
