# Changelog

All notable changes to FollowWeb Network Analysis Package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **BREAKING CHANGE**: CI/CD pipelines now strictly enforce type checking
  - `mypy` type checking failures will now fail the entire pipeline
  - Previously, type errors were allowed with `continue-on-error: true`
  - This ensures type safety is maintained across all releases

### Fixed
- **Type Safety**: Significantly improved type safety across the codebase
  - Fixed critical type errors in core modules (utils, analysis foundations)
  - Added proper type annotations for Optional, Union, and container types
  - Fixed missing return statements and exception handling
  - Eliminated `# type: ignore` usage in favor of proper Optional typing for imports
  - Added targeted mypy overrides for complex architectural issues requiring future refactoring
  - Reduced mypy errors from 308+ to manageable levels with documented technical debt
- **CI/CD Pipeline**: Improved release workflow reliability
  - Split monolithic build-and-publish into focused stages (build → test-pypi → production-pypi)
  - Fixed artifact path inconsistencies that could cause silent failures
  - Added retry logic with exponential backoff for package verification
  - Improved post-publication verification with version-specific installation checks
- **Exception Handling**: Improved error handling patterns in utility modules
  - Replaced defensive programming patterns with proper assertions
  - Enhanced retry logic in file operations

### Added
- **Production Dependencies**: Added missing explicit dependency
  - `numpy>=1.21.0` - Now explicitly listed (required by matplotlib and used directly in `core/types.py` and `visualization/renderers.py`)

### Removed
- **Production Dependencies**: Removed unused dependencies (41% reduction in total dependencies)
  - `scipy>=1.9.0` - Not used anywhere in the codebase
- **Development Dependencies**: Removed unused test dependencies to streamline development setup
  - `faker>=18.0.0` - Not imported or used in any tests
  - `factory-boy>=3.2.0` - Not used (fixture name was misleading)
  - `pytest-doctestplus>=0.12.0` - Not used (no doctest configuration)
  - `pytest-timeout>=2.1.0` - Not actively used (no timeout markers)
  - `pytest-mock>=3.10.0` - Not used (no mocker fixture usage)
  - `tox>=4.0.0` - No tox configuration exists
- **Type Stubs**: Removed unused type stubs from CI/minimal requirements
  - `types-python-dateutil` - dateutil not used
  - `types-PyYAML` - PyYAML not used
  - `types-decorator` - decorator not used
  - `types-requests` - requests not used
  - `types-setuptools` - Not needed for runtime
- **Documentation Dependencies**: Removed unused documentation build tools
  - `sphinx>=5.0.0` - Documentation not currently using Sphinx
  - `sphinx-rtd-theme>=1.0.0` - Not needed without Sphinx
  - `myst-parser>=0.18.0` - Not needed without Sphinx

### Impact
- **Dependency Count**: Reduced from 66 to 39 total dependencies across all requirement files
- **CI Performance**: Faster builds with fewer packages to install
- **Security**: Reduced attack surface with fewer dependencies to monitor
- **Verification**: All remaining dependencies verified as actively used via ruff analysis (F401, F841 checks)

### Migration Guide
If your development workflow depends on type checking being non-blocking:
1. Ensure your code passes `mypy FollowWeb_Visualizor --show-error-codes` before pushing
2. Use local development tools to catch type errors early
3. Consider using `mypy --ignore-missing-imports` for rapid prototyping (not recommended for production)

If you need any of the removed dependencies for your specific use case:
1. Install them manually: `pip install faker factory-boy pytest-doctestplus`
2. Or add them back to your local `requirements-dev.txt` file

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