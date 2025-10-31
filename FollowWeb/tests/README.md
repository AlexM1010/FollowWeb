# FollowWeb Test Suite

This directory contains the test suite for FollowWeb with comprehensive coverage of all system components.

## Directory Structure

```
tests/
├── Output/                          # Test output directory (gitignored)
│   └── test_*_*/                   # Worker-isolated test outputs
├── unit/                           # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_config.py              # Configuration management tests
│   ├── test_utils.py               # Utility function tests
│   ├── test_progress.py            # Progress tracking tests
│   ├── test_analysis.py            # Analysis module tests
│   ├── test_main.py                # Main pipeline tests
│   ├── test_k_values.py            # K-value configuration tests
│   ├── test_shared_metrics.py      # MetricsCalculator and metrics system tests
│   ├── test_unified_output.py      # Unified output system tests
│   ├── test_visualization.py       # Visualization module tests
│   └── test_visualization_renderers.py  # PNG/HTML renderer consistency tests
├── integration/                    # Integration tests (cross-module)
│   ├── __init__.py
│   ├── test_pipeline.py            # End-to-end pipeline tests
│   ├── test_ui_ux_integration.py   # UI/UX integration tests
│   └── test_unified_output_integration.py  # Output system integration tests
├── performance/                    # Performance tests (timing, resources)
│   ├── __init__.py
│   ├── test_benchmarks.py          # Performance benchmarking tests
│   └── test_timing_benchmarks.py   # Performance and timing tests
├── test_data/                      # Test datasets
│   ├── dataset_summary.json        # Dataset statistics and metadata
│   ├── tiny_real.json             # Tiny dataset for fast tests
│   ├── small_real.json            # Small dataset for unit tests
│   ├── medium_real.json           # Medium dataset for integration tests
│   ├── large_real.json            # Large dataset for performance tests
│   └── full_anonymized.json       # Full dataset for comprehensive tests
├── __init__.py                     # Test package initialization
├── conftest.py                     # Shared fixtures and pytest configuration
├── run_tests.py                    # Consolidated test runner
├── test.bat                        # Windows batch script for running tests

└── README.md                       # This file
```

## Test Output Management

All test outputs are centralized in the `tests/Output/` directory to keep the project root clean:

- **Test outputs**: `tests/Output/` - All test-generated files (HTML, PNG, TXT, timing logs)
- **Coverage reports**: `tests/Output/htmlcov/` - HTML coverage reports
- **Coverage data**: `tests/Output/.coverage*` - Coverage database files
- **Worker isolation**: `tests/Output/test_*_*/` - Parallel test worker directories

### Cleaning Test Outputs

```bash
# Clean test outputs older than 7 days
make clean-test-outputs

# Preview what would be cleaned (dry run)
make clean-test-outputs-dry

# Manual cleanup with custom age
python analysis_tools/cleanup_test_outputs.py --days 3
python analysis_tools/cleanup_test_outputs.py --days 1 --dry-run
```

### Test Runner (`run_tests.py`)
The test runner provides a simple interface for running different test categories:

```bash
# Run all tests
python tests/run_tests.py all

# Run specific test categories
python tests/run_tests.py unit
python tests/run_tests.py integration
python tests/run_tests.py performance
python tests/run_tests.py benchmark

# Run tests sequentially (for debugging)
python tests/run_tests.py sequential

# Run tests with debug output
python tests/run_tests.py debug

# Show system resource information
python tests/run_tests.py system-info
```

### Windows Batch Script (`test.bat`)
For Windows users, the batch script provides a convenient interface:

```cmd
# Run all tests
test.bat all

# Run unit tests
test.bat unit

# Run benchmark tests
test.bat benchmark

# Show help
test.bat help
```

## Test Categories and Coverage

### Unit Tests (`-m unit`)
- **Location**: `tests/unit/`
- **Characteristics**: Fast, isolated component testing
- **Worker count**: CPU cores minus one (calculated by `get_safe_worker_count()`)
- **Purpose**: Test individual components and functions

**Key Test Modules:**
- **Configuration Tests**: Dataclass validation, parameter rejection, serialization
- **Utility Tests**: Filename generation, color schemes, mathematical operations, centralized caching system
- **Progress Tracking**: Context managers, adaptive display, time estimation
- **Analysis Tests**: Graph loading, filtering, k-core algorithms, network analysis
- **Pipeline Tests**: Orchestrator functionality, CLI, logging, error handling
- **Visualization Tests**: Metrics calculation, rendering, report generation, shared metrics caching

### Integration Tests (`-m integration`)
- **Location**: `tests/integration/`
- **Characteristics**: Cross-module testing with memory constraints
- **Worker count**: 75% of available workers (calculated by `get_safe_worker_count()`)
- **Purpose**: Test component interactions and workflows

**Key Integration Areas:**
- **End-to-end Pipeline**: Complete workflow execution for all strategies
- **UI/UX Integration**: Emoji consistency, console formatting, progress tracking
- **Output System**: Console and file synchronization, formatting consistency

### Performance Tests (`-m slow` or `-m performance`)
- **Location**: `tests/performance/`
- **Characteristics**: Sequential execution for timing accuracy
- **Worker count**: 1 (sequential only)
- **Purpose**: Performance benchmarking and timing validation

**Performance Monitoring:**
- Pipeline timing accuracy validation
- Progress tracker performance overhead
- Memory efficiency testing with centralized caching system
- Resource usage monitoring
- Scalability testing with different parameters
- Cache performance validation (90% hash reduction, 95% conversion reduction, 80% traversal reduction)

### Benchmark Tests (`-m benchmark`)
- **Location**: `tests/performance/`
- **Characteristics**: Uses pytest-benchmark for statistical analysis
- **Worker count**: 1 (sequential only)
- **Purpose**: Performance profiling with statistical analysis

## Configuration

### Pytest Configuration
- **Main config**: `pytest.ini` - General pytest settings and benchmark configuration
- **Tool config**: `pyproject.toml` - Tool-specific configurations

### Test Fixtures
- **Output directories**: `temp_output_dir` fixture provides isolated test outputs in `tests/Output/`
- **Test data**: Various dataset fixtures for different test scenarios
- **Configuration**: Pre-configured test configurations for different scenarios

## Running Tests

### Via Makefile
```bash
make test              # All tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-performance  # Performance tests only
make test-benchmark    # Benchmark tests only
make test-coverage     # Tests with coverage
make system-info       # Show system resources
```

### Via Test Runner
```bash
python tests/run_tests.py all
python tests/run_tests.py unit
python tests/run_tests.py benchmark
```

### Via Pytest (Direct)
```bash
pytest                 # All tests
pytest -m unit         # Unit tests only
pytest -m integration  # Integration tests only
pytest -m slow         # Performance tests only
pytest -m benchmark    # Benchmark tests only
```

### Development Scenarios

#### Quick Development Testing
```bash
# Run tests with minimal output
pytest --tb=no

# Run tests quietly with only pass/fail status
pytest -q

# Run only failed tests from last run
pytest --lf

# Run failed tests first, then continue
pytest --ff
```

#### Debugging and Troubleshooting
```bash
# Show full traceback for error analysis
pytest --tb=long

# Run with maximum verbosity for debugging
pytest -vv

# Show local variables in tracebacks
pytest --tb=short --showlocals

# Drop into debugger on failures
pytest --pdb
```

#### Performance and Coverage Analysis
```bash
# Run with coverage reporting
pytest --cov=FollowWeb_Visualizor --cov-report=html --cov-report=term

# Run with coverage and missing line reports
pytest --cov=FollowWeb_Visualizor --cov-report=term-missing

# Run performance tests with timing
pytest -m slow --durations=10
```

### Debug Mode
```bash
python tests/run_tests.py debug
# or
make test-debug
```

### Sequential Mode (for debugging)
```bash
python tests/run_tests.py sequential
# or
make test-sequential
```

## CI/CD Integration

### Parallel Execution Strategies
- **Unit tests**: Parallel execution with worksteal distribution
- **Integration tests**: Parallel execution with loadgroup distribution  
- **Performance tests**: Sequential execution for timing accuracy
- **Mixed workloads**: Balanced distribution with loadscope

## Resource Management

### Worker Detection
The test runner calculates worker counts based on:
- CPU core count (logical and physical cores)
- Available memory (500MB per worker baseline)
- Test type (unit/integration/performance)
- Operating system (Windows/Linux/macOS)
- CI environment detection