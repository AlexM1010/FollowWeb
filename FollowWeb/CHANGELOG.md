# Changelog

All notable changes to FollowWeb Network Analysis Package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2024-11-03

### Fixed
- **Update Package Command Line Arguments** - Updated documented python calls to followweb calls
- **Package Publishing**: Resolved PyPI publishing issue by incrementing version number
- **Release Workflow**: Fixed duplicate version conflict preventing successful package upload

## [1.0.0] - 2024-11-03

### Package Release - Complete Transformation from Script to Professional Package

### Added
- **Package Installation**: Full pip-installable package with console script entry point
  - `followweb` command available after installation via `pip install followweb-visualizor`
  - Fallback support for `python -m FollowWeb_Visualizor` execution method
- **Comprehensive CLI Interface**: Complete command-line interface with extensive options
  - Multiple analysis strategies: k-core, reciprocal k-core, ego-alter analysis
  - Analysis mode selection: fast, medium, full modes with performance optimization
  - Pipeline stage control: ability to skip analysis or visualization phases
  - Output format control: HTML, PNG, and text report generation options
- **Modular Architecture**: Professional package structure with separated concerns
  - Core pipeline orchestration in `main.py`
  - Configuration management system with validation
  - Separate modules for analysis, visualization, data processing, and utilities
  - Unified output management with centralized logging
- **Advanced Analysis Features**:
  - K-core decomposition with customizable k-values
  - Reciprocal relationship analysis (mutual connections only)
  - Ego-alter network analysis for personal network exploration
  - Community detection using Louvain algorithm
  - Centrality analysis (degree, betweenness, eigenvector, closeness)
  - Path analysis with shortest path calculations
  - Fame analysis for identifying influential accounts
- **Interactive Visualizations**:
  - HTML interactive networks with hover tooltips and physics simulation
  - High-resolution PNG static exports suitable for presentations
  - Customizable node sizing based on centrality metrics
  - Community-based color coding with legend
  - Physics controls and layout optimization
- **Performance Optimization**:
  - Parallel processing support with automatic core detection
  - NetworkX parallel backend integration (nx-parallel)
  - Intelligent sampling for large networks
  - Caching system for improved performance
  - Progress tracking with dynamic loading bars
- **Configuration System**:
  - JSON-based configuration files with validation
  - CLI parameter override capabilities
  - Multiple pre-built configuration templates
  - Analysis mode management (fast/medium/full)
  - Pipeline stage control and component selection
- **Comprehensive Testing**:
  - 343+ focused tests organized by category (unit, integration, performance)
  - Parallel test execution with pytest-xdist
  - Coverage reporting and benchmarking
  - Cross-platform compatibility testing
- **Professional Documentation**:
  - Complete user guide with examples and tutorials
  - API reference documentation
  - Configuration guide with detailed parameter explanations
  - Installation guide with troubleshooting
  - Development and contribution guidelines

### Changed
- **Command Interface**: Updated all examples from `python -m FollowWeb_Visualizor.main` to `followweb`
- **File Paths**: Standardized example paths to use `examples/followers_following.json`
- **Import Paths**: Corrected all import statements to use proper package structure
- **Documentation**: Updated all documentation to reflect pip-installable package structure

### Technical Details
- **Dependencies**: NetworkX ≥2.8.0, pandas ≥1.5.0, matplotlib ≥3.5.0, pyvis ≥0.3.0
- **Python Support**: Python 3.8+ (3.9+ recommended for nx-parallel support)
- **Build System**: Modern pyproject.toml configuration with setuptools backend
- **Development Tools**: Integrated ruff, mypy, pytest with comprehensive tooling
- **Cross-Platform**: Full Windows, macOS, and Linux compatibility