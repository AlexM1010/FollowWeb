# FollowWeb Network Analysis Package

A network analysis tool for Instagram follower/following relationships using graph theory and network analysis techniques. Transform social connection data into interactive visualizations with automatic community detection and influence metrics.

---

## Key Features

- **Multiple Analysis Strategies**: k-core decomposition, reciprocal connections, ego-alter analysis
- **Comprehensive Reporting**: text reports with network statistics and parameters
- **Performance Optimized**: caching system eliminates duplicate calculations and reduces memory usage

## Analysis Strategies
1. **K-Core Analysis**: Full network analysis identifying densely connected subgraphs
2. **Reciprocal K-Core**: Focus on mutual connections and bidirectional relationships  
3. **Ego-Alter Analysis**: Personal network analysis centered on specific users

## Output Formats
- **Interactive HTML**: Network visualizations with hover tooltips and physics controls
- **Static PNG**: High-resolution images suitable for presentations and papers
- **Metrics Reports**: Detailed analysis statistics, timing, and configuration parameters

---

## Quick Setup

### Installation
```bash
# Install production dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Basic Usage
```bash
# Run analysis with sample data
followweb --input examples/followers_following.json

# Use a configuration file
followweb --config configs/fast_config.json

# Print default configuration
followweb --print-default-config
```

### Example Configuration Files
- **[fast_config.json](configs/fast_config.json)** - Quick analysis optimized for development and testing
- **[comprehensive_layout_config.json](configs/comprehensive_layout_config.json)** - Complete configuration with all available features

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
- **[pandas](https://pandas.pydata.org/)** - Data manipulation and analysis
- **[matplotlib](https://matplotlib.org/)** - Static graph visualization and plotting
- **[pyvis](https://pyvis.readthedocs.io/)** - Interactive network visualizations

### Development Tools
- **[pytest](https://pytest.org/)** ecosystem - Comprehensive testing framework
- **[ruff](https://github.com/astral-sh/ruff)**, **[mypy](https://github.com/python/mypy)** - Code quality tools

See [docs/attribution/CONTRIBUTORS.md](docs/attribution/CONTRIBUTORS.md) for detailed acknowledgments and contribution guidelines.

## Links

- **Source Code**: [FollowWeb_Visualizor/](FollowWeb_Visualizor/)
- **Tests**: [tests/](tests/)
- **Documentation**: [docs/](docs/)
- **Attribution**: [docs/attribution/](docs/attribution/) - Contributors, dependencies, and license notices

