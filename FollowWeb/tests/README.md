# FollowWeb Test Suite

Comprehensive test suite with local CI pipeline replication.

## Quick Start

```bash
# Auto-fix code issues (fastest way to fix formatting/linting)
python tests/run_tests.py fix                    # ONLY fix issues (no checks)
python tests/run_tests.py quality --autofix      # Fix + verify
python tests/run_tests.py all --autofix          # Fix + run all checks

# Run full CI pipeline locally (recommended before pushing)
python tests/run_tests.py all

# Run specific test categories
python tests/run_tests.py unit         # Fast unit tests (parallel)
python tests/run_tests.py integration  # Integration tests (parallel)
python tests/run_tests.py performance  # Performance tests (sequential)
python tests/run_tests.py benchmark    # Benchmark tests (sequential)

# Run quality and security checks
python tests/run_tests.py quality      # Format, lint, type checking
python tests/run_tests.py security     # Security scans
python tests/run_tests.py build        # Package build validation
```

## Test Runner Features

The `run_tests.py` script replicates the full CI pipeline locally:

### Auto-Fix Mode
- **`fix` command**: Apply all fixes without running checks (fastest)
- **`--autofix` flag**: Apply fixes then run checks to verify
- **Fixes applied**:
  - Code formatting: `ruff format`
  - Linting issues: `ruff check --fix`
  - Import sorting: `ruff check --fix --select I`

### Quality Checks
- **Code formatting**: `ruff format --check`
- **Linting**: `ruff check`
- **Import sorting**: `ruff check --select I`
- **Type checking**: `mypy`

### Security Checks
- **Bandit**: Security linting (medium/high severity)
- **pip-audit**: Vulnerability scanning

### Test Execution
- **Unit tests**: Fast, isolated tests (parallel with all CPU cores)
- **Integration tests**: Cross-module tests (parallel)
- **Performance tests**: Timing-sensitive tests (sequential)
- **Benchmark tests**: Performance benchmarks (sequential with pytest-benchmark)

### Package Validation
- **Manifest check**: `check-manifest`
- **Build**: Source distribution and wheel
- **Integrity check**: `twine check`

## Test Organization

```
tests/
├── unit/                  # Fast, isolated unit tests
│   ├── test_config.py
│   ├── test_utils.py
│   ├── test_analysis.py
│   └── test_visualization.py
├── integration/           # Cross-module integration tests
│   ├── test_pipeline.py
│   └── test_ui_ux_integration.py
├── performance/           # Performance and timing tests
│   ├── test_benchmarks.py
│   └── test_timing_benchmarks.py
├── test_data/            # Test datasets
│   ├── tiny_real.json
│   ├── small_real.json
│   └── medium_real.json
├── conftest.py           # Shared fixtures
├── run_tests.py          # Comprehensive test runner
└── README.md             # This file
```

## Test Markers

Tests are categorized using pytest markers:

```python
@pytest.mark.unit          # Fast, isolated unit tests
@pytest.mark.integration   # Cross-module integration tests
@pytest.mark.slow          # Slow tests (>1 second)
@pytest.mark.performance   # Performance-sensitive tests
@pytest.mark.benchmark     # Benchmark tests (pytest-benchmark)

# Category markers
@pytest.mark.core          # Core functionality
@pytest.mark.data          # Data loading/storage
@pytest.mark.analysis      # Network analysis
@pytest.mark.visualization # Visualization rendering
@pytest.mark.output        # Output management
@pytest.mark.utils         # Utility functions
@pytest.mark.pipeline      # Full pipeline tests
```

## Direct pytest Usage

For custom test execution, use pytest directly:

```bash
# Run with coverage
pytest --cov=FollowWeb_Visualizor --cov-report=term-missing

# Run specific markers
pytest -m unit                    # Unit tests only
pytest -m "unit or integration"   # Unit and integration tests
pytest -m "not (slow or benchmark)" # Exclude slow and benchmark tests

# Parallel execution (auto-detect workers)
pytest -n auto

# Parallel execution with specific worker count
pytest -n 4

# Stop on first failure
pytest -x --maxfail=1

# Verbose output
pytest -v

# Show local variables on failure
pytest -l

# Run specific test file
pytest tests/unit/test_config.py

# Run specific test function
pytest tests/unit/test_config.py::test_config_validation
```

## CI Pipeline Equivalence

The local test runner replicates the CI pipeline:

| CI Job | Local Command |
|--------|---------------|
| Quality Check | `python tests/run_tests.py quality` |
| Security Scan | `python tests/run_tests.py security` |
| Unit Tests | `python tests/run_tests.py unit` |
| Integration Tests | `python tests/run_tests.py integration` |
| Performance Tests | `python tests/run_tests.py performance` |
| Benchmark Tests | `python tests/run_tests.py benchmark` |
| Package Build | `python tests/run_tests.py build` |
| **Full Pipeline** | `python tests/run_tests.py all` |

## Best Practices

1. **Before committing**: Run `python tests/run_tests.py all` to catch issues early
2. **During development**: Run `python tests/run_tests.py unit` for fast feedback
3. **Before pushing**: Run `python tests/run_tests.py quality` to ensure code quality
4. **Performance changes**: Run `python tests/run_tests.py benchmark` to check impact
5. **Security updates**: Run `python tests/run_tests.py security` after dependency changes

## Troubleshooting

### Formatting Issues
```bash
# Fix formatting automatically
ruff format FollowWeb_Visualizor tests
```

### Linting Issues
```bash
# Auto-fix linting issues
ruff check --fix FollowWeb_Visualizor tests
```

### Type Checking Issues
```bash
# Run mypy with detailed output
mypy FollowWeb_Visualizor --show-error-codes --show-traceback
```

### Parallel Test Failures
```bash
# Run tests sequentially for debugging
pytest -n 0 -v
```

### Benchmark Plugin Conflicts
```bash
# Disable benchmark plugin for parallel tests
pytest -p no:benchmark -n auto
```

## Coverage Requirements

- **Minimum coverage**: 70% (enforced in CI)
- **Coverage calculation**: Only on ubuntu-latest with Python 3.9 in CI
- **Local coverage**: Run `pytest --cov=FollowWeb_Visualizor --cov-report=html` for detailed report

## Performance Considerations

- **Unit tests**: Run in parallel with all available CPU cores
- **Integration tests**: Run in parallel with controlled worker count
- **Performance tests**: Run sequentially to ensure accurate timing
- **Benchmark tests**: Run sequentially with pytest-benchmark for precise measurements
