# FollowWeb Network Analysis Package

[![Freesound Nightly Pipeline](https://github.com/alexmeckes/FollowWeb/actions/workflows/freesound-nightly-pipeline.yml/badge.svg)](https://github.com/alexmeckes/FollowWeb/actions/workflows/freesound-nightly-pipeline.yml)

A comprehensive network analysis tool supporting multiple data sources including Instagram social networks and Freesound audio sample relationships. Transform connection data into interactive visualizations with automatic community detection, influence metrics, and audio playback capabilities.

**🎵 Freesound Network Explorer**: [View Live Visualization](https://alexmeckes.github.io/FollowWeb/) - Interactive network of Freesound audio samples with audio playback, automatically updated nightly.

---

## Key Features

- **Multiple Data Sources**: Instagram social networks and Freesound audio sample networks
- **Multiple Analysis Strategies**: k-core decomposition, reciprocal connections, ego-alter analysis
- **High-Performance Visualization**: Sigma.js renderer supporting 10,000+ nodes with WebGL acceleration
- **Audio Playback Integration**: Click-to-play audio samples directly in network visualizations
- **Comprehensive Reporting**: text reports with network statistics and parameters
- **Performance Optimized**: caching system eliminates duplicate calculations and reduces memory usage
- **Automated Pipeline**: Nightly data collection with parallel milestone execution
- **Data Validation**: Automated integrity checks and anomaly detection
- **Public Visualizations**: GitHub Pages deployment with growth metrics dashboard

## Data Sources
1. **Instagram Networks**: Analyze follower/following relationships from Instagram JSON exports
2. **Freesound Audio Networks**: Explore audio sample similarity networks from the Freesound API

## Analysis Strategies
1. **K-Core Analysis**: Full network analysis identifying densely connected subgraphs
2. **Reciprocal K-Core**: Focus on mutual connections and bidirectional relationships  
3. **Ego-Alter Analysis**: Personal network analysis centered on specific users

## Visualization Engines
- **Sigma.js Renderer**: High-performance WebGL visualization for large networks (10,000+ nodes) with audio playback
- **Pyvis Renderer**: Interactive HTML visualizations with physics simulation and hover tooltips
- **Static PNG**: High-resolution matplotlib images suitable for presentations and papers

## Output Formats
- **Interactive HTML**: Network visualizations with hover tooltips, zoom/pan controls, and audio playback (Freesound)
- **Static PNG**: High-resolution images suitable for presentations and papers
- **Metrics Reports**: Detailed analysis statistics, timing, and configuration parameters

## Freesound Pipeline Enhancements

The Freesound nightly pipeline has been enhanced with advanced features for data integrity, network enrichment, and public visibility:

### 🎯 Milestone Achievements

**Parallel Execution Architecture**:
- 4-core parallel processing at every 100-node milestone
- Main pipeline continues uninterrupted during milestone actions
- 30-40% reduction in total workflow time

**Automated Validation System**:
- Checkpoint integrity verification after every run
- Graph structure validation (no orphaned edges)
- Metadata consistency checks (SQLite ↔ graph sync)
- Anomaly detection (sudden drops, zero growth)

**Network Enrichment**:
- User relationship edges (samples by same user)
- Pack relationship edges (samples in same pack)
- Generated automatically at every 100-node milestone
- Adds relationship dimensions beyond similarity

**Public Website Deployment**:
- Automatic deployment to GitHub Pages
- Growth metrics dashboard with Chart.js
- Latest visualization embedded in iframe
- Mobile-responsive design
- Updates within 5 minutes of commit

**Tiered Backup Retention**:
- Frequent tier (25 nodes): 14-day retention
- Moderate tier (100 nodes): Permanent retention
- Milestone tier (500 nodes): Permanent retention
- Automatic compression after 7 days

### 📊 Current Network Statistics

Visit the [Freesound Network Explorer](https://alexmeckes.github.io/FollowWeb/) to see:
- Total nodes and edges
- Growth over time
- Latest interactive visualization
- Milestone history

### 📖 Pipeline Documentation

For detailed information about the Freesound pipeline:
- **[Freesound Pipeline Guide](../Docs/FREESOUND_PIPELINE.md)** - Complete pipeline documentation
- **[Validation Coordination](../Docs/VALIDATION_COORDINATION.md)** - Validation system overview
- **[Pipeline Configuration](../configs/FREESOUND_PIPELINE_CONFIG.md)** - Configuration parameters

---

## Quick Setup

### Installation

#### Basic Installation
```bash
# Install production dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

**Note on pymetis (Optional)**: The package includes optional support for pymetis, which provides fast graph partitioning for very large networks (600K+ nodes). This is primarily used in CI/CD pipelines and is **not required** for normal usage.

- **Linux/macOS**: pymetis will be automatically installed
- **Windows**: pymetis is not supported (requires Unix-specific headers) and will be automatically skipped during installation. All standard features work without it.

If you need graph partitioning features on Linux/macOS and encounter installation issues:

```bash
# Linux (Ubuntu/Debian)
sudo apt-get install libmetis-dev
pip install pymetis

# macOS
brew install metis
pip install pymetis
```

### Basic Usage

#### Instagram Network Analysis
```bash
# Run analysis with Instagram data
followweb --input examples/followers_following.json

# Use a configuration file
followweb --config configs/fast_config.json

# Print default configuration
followweb --print-default-config
```

#### Freesound Audio Network Analysis
```bash
# Analyze Freesound audio samples with Sigma.js visualization
followweb --config configs/freesound_sigma_config.json

# Quick Freesound analysis with default settings
followweb --data-source freesound --renderer-type sigma --freesound-query "jungle"
```

### Example Configuration Files
- **[fast_config.json](configs/fast_config.json)** - Quick analysis optimized for development and testing
- **[comprehensive_layout_config.json](configs/comprehensive_layout_config.json)** - Complete configuration with all available features
- **[freesound_sigma_config.json](configs/freesound_sigma_config.json)** - Freesound audio network analysis with Sigma.js renderer

### Development Setup
For development, see **[docs/development/CONTRIBUTING.md](docs/development/CONTRIBUTING.md)** for detailed setup instructions including dependency installation and code quality tools.

---

## Testing

FollowWeb includes a comprehensive test suite with **337 passing tests** and **73.95% code coverage**, ensuring reliability across all components.

### Test Categories

- **Unit Tests** (280+ tests): Fast, isolated component testing with maximum parallelization
- **Integration Tests** (45+ tests): Cross-module testing with controlled parallelization  
- **Performance Tests** (12+ tests): Benchmarking and timing validation with sequential execution

### Running Tests

```bash
# Run all tests with coverage
python -m pytest --cov=FollowWeb_Visualizor --cov-report=term-missing

# Run specific test categories
python -m pytest tests/unit/          # Unit tests only
python -m pytest tests/integration/   # Integration tests only
python -m pytest tests/performance/   # Performance tests only

# Run tests with detailed output
python -m pytest -v

# Run tests in parallel (automatic)
python -m pytest -n auto
```

For detailed testing procedures, see **[tests/README.md](tests/README.md)**.

---

## Documentation

### User Documentation
- **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** - User guide with tutorials and workflows
- **[docs/FREESOUND_GUIDE.md](docs/FREESOUND_GUIDE.md)** - Complete Freesound audio network analysis guide
- **[docs/QUICK_START_FREESOUND.md](docs/QUICK_START_FREESOUND.md)** - 5-minute Freesound quick start
- **[docs/CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md)** - Configuration guide with layout options
- **[docs/INSTALL_GUIDE.md](docs/INSTALL_GUIDE.md)** - Installation and setup guide
- **[tests/README.md](tests/README.md)** - Testing procedures and guidelines

### Developer Documentation  
- **[docs/development/CONTRIBUTING.md](docs/development/CONTRIBUTING.md)** - Development guidelines and contribution process
- **[docs/development/API_REFERENCE.md](docs/development/API_REFERENCE.md)** - Complete API documentation with examples
- **[docs/development/PACKAGE_OVERVIEW.md](docs/development/PACKAGE_OVERVIEW.md)** - High-level package architecture overview
- **[docs/development/PARALLEL_PROCESSING_GUIDE.md](docs/development/PARALLEL_PROCESSING_GUIDE.md)** - Centralized parallel processing system guide

# Package Structure

```
├── FollowWeb_Visualizor/    # Main package (main.py, config.py, analysis.py, visualization.py, utils.py, progress.py)
├── tests/                   # Test suite (unit/, integration/, performance/)
├── docs/                    # Documentation (API_REFERENCE.md, USER_GUIDE.md, CONTRIBUTING.md, etc.)
│   └── development/         # Development documentation and analysis reports
├── configs/                 # Configuration files for different analysis scenarios
├── examples/                # Sample data and example outputs
├── Output/                  # Default output directory for generated results
├── README.md               # Main documentation
├── setup.py                # Package installation
├── requirements*.txt       # Dependencies
├── Makefile               # Development automation
└── pytest.ini            # Test configuration
```

## Acknowledgments

FollowWeb is built upon excellent open-source libraries and tools. We gratefully acknowledge:

### Core Dependencies
- **[NetworkX](https://networkx.org/)** - Graph analysis algorithms and community detection
- **[NumPy](https://numpy.org/)** - Array operations and numerical computing
- **[pandas](https://pandas.pydata.org/)** - Data manipulation and analysis
- **[matplotlib](https://matplotlib.org/)** - Static graph visualization and plotting
- **[pyvis](https://pyvis.readthedocs.io/)** - Interactive network visualizations
- **[Sigma.js](https://www.sigmajs.org/)** - High-performance WebGL graph visualization (via CDN)
- **[Tone.js](https://tonejs.github.io/)** - Web Audio framework for synchronized multi-sample playback (via CDN)
- **[freesound-api](https://github.com/MTG/freesound-api)** - Official Freesound API client
- **[Jinja2](https://jinja.palletsprojects.com/)** - Template engine for HTML generation
- **[joblib](https://joblib.readthedocs.io/)** - Checkpoint persistence and compression

### Development Tools
- **[pytest](https://pytest.org/)** ecosystem - Comprehensive testing framework
- **[ruff](https://github.com/astral-sh/ruff)**, **[mypy](https://github.com/python/mypy)** - Code quality tools

See [docs/attribution/CONTRIBUTORS.md](docs/attribution/CONTRIBUTORS.md) for detailed acknowledgments and contribution guidelines.

## Links

- **Source Code**: [FollowWeb_Visualizor/](FollowWeb_Visualizor/)
- **Tests**: [tests/](tests/)
- **Documentation**: [docs/](docs/)
- **Attribution**: [docs/attribution/](docs/attribution/) - Contributors, dependencies, and license notices

