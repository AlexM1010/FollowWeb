# FollowWeb Network Analysis Package - Dependencies Attribution

## Core Production Dependencies

### Network Analysis and Graph Processing
- **NetworkX** (>=2.8.0)
  - Purpose: Graph creation, analysis algorithms, community detection, centrality calculations
  - License: BSD-3-Clause
  - Homepage: https://networkx.org/
  - Repository: https://github.com/networkx/networkx
  - Key Features Used: Graph construction, k-core decomposition, community detection algorithms, centrality metrics

- **nx-parallel** (>=0.3.0)
  - Purpose: Parallel processing backend for NetworkX performance optimization
  - License: BSD-3-Clause
  - Homepage: https://github.com/networkx/nx-parallel
  - Repository: https://github.com/networkx/nx-parallel
  - Key Features Used: Parallel execution of NetworkX algorithms for improved performance

### Data Manipulation and Analysis
- **pandas** (>=1.5.0)
  - Purpose: Data manipulation, CSV/JSON processing, metrics display and analysis
  - License: BSD-3-Clause
  - Homepage: https://pandas.pydata.org/
  - Repository: https://github.com/pandas-dev/pandas
  - Key Features Used: DataFrame operations, data processing, metrics calculations

### Visualization Libraries
- **matplotlib** (>=3.5.0)
  - Purpose: Static PNG image generation, graph plotting, and scientific visualization
  - License: PSF (Python Software Foundation License)
  - Homepage: https://matplotlib.org/
  - Repository: https://github.com/matplotlib/matplotlib
  - Key Features Used: PNG graph rendering, plot customization, color management, patches for visual elements

- **pyvis** (>=0.3.0)
  - Purpose: Interactive HTML network visualizations with physics simulation
  - License: BSD-3-Clause
  - Homepage: https://pyvis.readthedocs.io/
  - Repository: https://github.com/WestHealth/pyvis
  - Key Features Used: Interactive network graphs, physics simulation, HTML export, hover tooltips

## Development and Testing Dependencies

### Core Testing Framework
- **pytest** (>=7.0.0)
  - Purpose: Primary testing framework for unit, integration, and performance tests
  - License: MIT
  - Homepage: https://pytest.org/
  - Repository: https://github.com/pytest-dev/pytest
  - Key Features Used: Test discovery, fixtures, parametrization, test execution

### Testing Extensions and Utilities
- **pytest-cov** (>=4.0.0)
  - Purpose: Coverage reporting and analysis
  - License: MIT
  - Repository: https://github.com/pytest-dev/pytest-cov
  - Key Features Used: Code coverage measurement, HTML/XML report generation

- **pytest-xdist** (>=3.0.0)
  - Purpose: Parallel test execution for improved performance
  - License: MIT
  - Repository: https://github.com/pytest-dev/pytest-xdist
  - Key Features Used: Distributed testing, parallel execution, worker management

- **pytest-timeout** (>=2.1.0)
  - Purpose: Test timeout handling to prevent hanging tests
  - License: MIT
  - Repository: https://github.com/pytest-dev/pytest-timeout
  - Key Features Used: Test execution timeouts, hanging test prevention

- **pytest-mock** (>=3.10.0)
  - Purpose: Mocking utilities for testing
  - License: MIT
  - Repository: https://github.com/pytest-dev/pytest-mock
  - Key Features Used: Mock objects, test isolation, dependency mocking

- **pytest-benchmark** (>=4.0.0)
  - Purpose: Performance benchmarking and timing analysis
  - License: BSD-2-Clause
  - Repository: https://github.com/ionelmc/pytest-benchmark
  - Key Features Used: Performance testing, benchmark comparisons, timing analysis

- **pytest-doctestplus** (>=0.12.0)
  - Purpose: Enhanced doctest support for documentation testing
  - License: BSD-3-Clause
  - Repository: https://github.com/astropy/pytest-doctestplus
  - Key Features Used: Docstring testing, documentation validation

### Test Data Generation
- **faker** (>=18.0.0)
  - Purpose: Test data generation for realistic testing scenarios
  - License: MIT
  - Repository: https://github.com/joke2k/faker
  - Key Features Used: Synthetic data generation, test fixtures

- **factory-boy** (>=3.2.0)
  - Purpose: Test object factories for consistent test data
  - License: MIT
  - Repository: https://github.com/FactoryBoy/factory_boy
  - Key Features Used: Object factories, test data management

- **numpy** (>=1.21.0)
  - Purpose: Numerical computing support for test data generation
  - License: BSD-3-Clause
  - Homepage: https://numpy.org/
  - Repository: https://github.com/numpy/numpy
  - Key Features Used: Array operations, mathematical functions in tests

### Code Quality Tools
- **ruff** (>=0.1.0)
  - Purpose: Code formatting, linting, and import sorting
  - License: MIT
  - Repository: https://github.com/astral-sh/ruff
  - Key Features Used: Automatic code formatting, style enforcement, linting, import organization

- **mypy** (>=1.0.0)
  - Purpose: Static type checking for Python
  - License: MIT
  - Repository: https://github.com/python/mypy
  - Key Features Used: Type annotation validation, static analysis

### Build and Distribution Tools
- **build** (>=0.10.0)
  - Purpose: Modern Python build tool for package creation
  - License: MIT
  - Repository: https://github.com/pypa/build
  - Key Features Used: Wheel and source distribution building

- **twine** (>=4.0.0)
  - Purpose: Package uploading to PyPI
  - License: Apache-2.0
  - Repository: https://github.com/pypa/twine
  - Key Features Used: Secure package uploading, distribution management

- **wheel** (>=0.40.0)
  - Purpose: Wheel building for Python packages
  - License: MIT
  - Repository: https://github.com/pypa/wheel
  - Key Features Used: Binary distribution creation

### Multi-Environment Testing
- **tox** (>=4.0.0)
  - Purpose: Testing across multiple Python versions and environments
  - License: MIT
  - Repository: https://github.com/tox-dev/tox
  - Key Features Used: Multi-version testing, environment isolation

## Optional Documentation Dependencies
- **sphinx** (>=5.0.0)
  - Purpose: Documentation generation
  - License: BSD-2-Clause
  - Repository: https://github.com/sphinx-doc/sphinx
  - Key Features Used: API documentation, user guides

- **sphinx-rtd-theme** (>=1.0.0)
  - Purpose: Read the Docs theme for Sphinx
  - License: MIT
  - Repository: https://github.com/readthedocs/sphinx_rtd_theme
  - Key Features Used: Documentation styling

- **myst-parser** (>=0.18.0)
  - Purpose: Markdown support for Sphinx
  - License: MIT
  - Repository: https://github.com/executablebooks/MyST-Parser
  - Key Features Used: Markdown documentation parsing

## Security and Quality Assurance (Optional)
- **bandit** (>=1.7.0)
  - Purpose: Security vulnerability scanning
  - License: Apache-2.0
  - Repository: https://github.com/PyCQA/bandit
  - Key Features Used: Security issue detection

- **safety** (>=2.0.0)
  - Purpose: Dependency vulnerability checking
  - License: MIT
  - Repository: https://github.com/pyupio/safety
  - Key Features Used: Known vulnerability detection

## Standard Library Dependencies
The package also makes extensive use of Python's standard library, including:
- **argparse**: Command-line argument parsing
- **json**: JSON data processing
- **logging**: Application logging and debugging
- **os**: Operating system interface
- **sys**: System-specific parameters and functions
- **time**: Time-related functions
- **threading**: Thread-based parallelism
- **hashlib**: Secure hash algorithms
- **datetime**: Date and time handling
- **math**: Mathematical functions
- **typing**: Type hints and annotations
- **dataclasses**: Data class decorators

## Acknowledgments

We gratefully acknowledge the contributions of all the open-source projects and their maintainers that make FollowWeb possible. The network analysis capabilities are built on the excellent foundation provided by NetworkX, the data processing leverages pandas' powerful DataFrame operations, and the visualizations are made possible through matplotlib and pyvis.

Special thanks to:
- The NetworkX development team for providing comprehensive graph analysis algorithms
- The pandas development team for robust data manipulation tools
- The matplotlib development team for flexible plotting capabilities
- The pyvis development team for interactive network visualization
- The pytest development team and ecosystem for comprehensive testing tools
- All contributors to the Python packaging ecosystem that enables modern Python development

## License Compliance

All dependencies are compatible with the MIT License used by FollowWeb. The package respects all license requirements and includes appropriate attribution where required by dependency licenses.