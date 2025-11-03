# Contributing Guide

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Git for version control
- Basic understanding of network analysis concepts

### 1. Fork and Clone
```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/yourusername/followweb.git
cd followweb
```

### 2. Install Dependencies

**Using Make (Linux/macOS/Windows with Make installed):**
```bash
make install-dev
```

**Manual Installation (All platforms, including Windows):**
```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-test.txt

# Install package in editable mode
pip install -e .
```

**Alternative using pyproject.toml (Modern approach):**
```bash
# Install with development dependencies
pip install -e ".[dev]"

# Or install with test dependencies only
pip install -e ".[test]"
```

### 3. Verify Setup

**Using Make (Linux/macOS):**
```bash
make check
```

**Manual Commands (All platforms, including Windows):**
```bash
# Run fast tests
python -m pytest -m "not slow"

# Run code quality checks
python -m ruff check FollowWeb/FollowWeb_Visualizor tests
python -m ruff format --check FollowWeb/FollowWeb_Visualizor tests
python -m mypy FollowWeb/FollowWeb_Visualizor
```

**Full Test Suite:**
```bash
# Run all tests (parallel by default)
make test

# Run specific test categories
make test-unit          # Fast unit tests
make test-integration   # Integration tests
make test-performance   # Performance tests
```

## Code Standards

### Style Guidelines
- **Formatting**: Ruff (88 characters line length), PEP 8 compliance
- **Naming Conventions**: 
  - Classes: `PascalCase`
  - Functions/variables: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
- **Type Hints**: Required for all public functions and methods
- **Docstrings**: Google-style for all public APIs
- **Import Organization**: ruff with isort-compatible rules (configured in pyproject.toml)

### Code Quality Commands

**Using Make (Linux/macOS):**
```bash
make format      # Ruff formatting
make lint        # Ruff linting
make type-check  # Mypy type checking
make check       # All quality checks
```

**Manual Commands (All platforms, including Windows):**
```bash
# Format code
python -m ruff format FollowWeb/FollowWeb_Visualizor tests
python -m ruff check --fix FollowWeb/FollowWeb_Visualizor tests

# Lint code
python -m ruff check FollowWeb/FollowWeb_Visualizor tests

# Type checking
python -m mypy FollowWeb/FollowWeb_Visualizor

# Run all checks (Windows - use & instead of &&)
python -m ruff check FollowWeb/FollowWeb_Visualizor tests & python -m ruff format --check FollowWeb/FollowWeb_Visualizor tests & python -m mypy FollowWeb/FollowWeb_Visualizor
```

### Error Handling Standards
- Use specific exception types with clear, actionable messages
- Implement graceful degradation where possible
- Provide helpful error context and remediation suggestions

```python
# Good: Specific exception with helpful message
if not os.path.exists(filepath):
    raise DataProcessingError(
        f"Input file not found: {filepath}. "
        f"Please check the file path and ensure the file exists."
    )

# Bad: Generic exception with minimal information
if not os.path.exists(filepath):
    raise Exception("File not found")
```

## Testing Guidelines

### Test Structure
```
tests/
├── unit/                    # Fast, isolated component tests
├── integration/             # Cross-module functionality tests  
├── performance/             # Timing and resource usage tests
├── test_data/              # Test datasets for different scenarios
├── conftest.py             # Shared fixtures and configuration
├── run_tests.py            # Test runner
└── README.md               # Test documentation
```

### Test Organization Principles
- Each test has a single, clear purpose
- Tests focus on package-specific code, not external libraries
- Tests grouped by module and functionality
- Parallel execution where appropriate, sequential for timing tests

### Running Tests

**Using Make (Linux/macOS):**
```bash
make test              # All tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-performance  # Performance tests only
make test-coverage     # Tests with coverage report
make test-fast         # Exclude slow tests
make test-sequential   # Sequential execution (debugging)
```

**Using Test Runner (All platforms):**
```bash
python tests/run_tests.py all          # All tests
python tests/run_tests.py unit         # Unit tests
python tests/run_tests.py integration  # Integration tests
python tests/run_tests.py performance  # Performance tests
python tests/run_tests.py sequential   # Sequential execution (debugging)
python tests/run_tests.py debug        # Debug mode with verbose output
```

**Manual Commands (All platforms, including Windows):**
```bash
# All tests
python -m pytest -n auto

# Test categories
python -m pytest -m unit -n auto          # Unit tests
python -m pytest -m integration -n auto   # Integration tests  
python -m pytest -m slow -n auto          # Performance tests

# Sequential execution (for debugging)
python -m pytest -n 0

# With coverage (parallel)
python -m pytest --cov=FollowWeb_Visualizor --cov-report=html -n auto

# Fast tests only (exclude slow)
python -m pytest -m "not slow" -n auto

# Specific test files
python -m pytest tests/unit/test_config.py -v
```

### Writing Tests

**Unit Test Example:**
```python
import pytest
from FollowWeb_Visualizor.utils.math import format_time_duration

class TestTimeFormatting:
    """Test time formatting utilities."""
    
    def test_seconds_formatting(self):
        """Test formatting of seconds."""
        assert format_time_duration(1.5) == "1.5s"
        assert format_time_duration(65.0) == "1m 5.0s"
    
    def test_negative_duration_rejection(self):
        """Test rejection of negative duration."""
        with pytest.raises(ValueError, match="Duration cannot be negative"):
            format_time_duration(-1.0)
```

**Integration Test Example:**
```python
@pytest.mark.integration
def test_pipeline_execution(self, fast_config, sample_data_exists):
    """Test complete pipeline execution."""
    if not sample_data_exists:
        pytest.skip("Sample data not available")
    
    orchestrator = PipelineOrchestrator(fast_config)
    success = orchestrator.execute_pipeline()
    assert success is True
```

### Test Markers and Categories
- `@pytest.mark.unit` - Fast unit tests (parallel execution)
- `@pytest.mark.integration` - Integration tests (parallel execution)
- `@pytest.mark.slow` - Performance/timing tests (sequential execution)
- `@pytest.mark.benchmark` - Performance profiling with pytest-benchmark

### Test File Organization
**Unit Tests** (`tests/unit/`):
- `test_config.py` - Configuration management
- `test_utils.py` - Utility functions
- `test_analysis.py` - Graph analysis algorithms
- `test_visualization.py` - Visualization components
- `test_main.py` - Pipeline orchestration
- Additional test modules for specific components

**Integration Tests** (`tests/integration/`):
- `test_pipeline.py` - End-to-end pipeline execution
- `test_ui_ux_integration.py` - UI/UX consistency testing
- `test_unified_output_integration.py` - Output system integration

**Performance Tests** (`tests/performance/`):
- `test_benchmarks.py` - Performance benchmarking
- `test_timing_benchmarks.py` - Timing validation

## Pull Request Process

### Before Submitting
1. **Run Quality Checks:**
   ```bash
   # Using Make (Linux/macOS)
   make check
   
   # Manual (all platforms)
   python -m ruff check FollowWeb/FollowWeb_Visualizor tests
   python -m ruff format --check FollowWeb_Visualizor tests
   python -m mypy FollowWeb_Visualizor
   python -m pytest -m "not slow" -n auto
   ```

2. **Update Documentation:**
   - Add/update docstrings for new code
   - Update relevant user documentation
   - Add changelog entry if significant

3. **Write Tests:**
   - Unit tests for new functions/classes
   - Integration tests for new features
   - Performance tests if applicable

### PR Template
Include in your pull request:
- **Description**: Brief description of changes and motivation
- **Type of Change**: Bug fix, new feature, breaking change, or documentation
- **Testing**: Confirmation that tests pass and new tests added
- **Checklist**: Code follows guidelines, documentation updated, etc.

## Development Workflow

### Branch Naming
- `feature/add-new-visualization-option`
- `bugfix/fix-memory-leak-community-detection`
- `docs/update-api-reference`

### Commit Messages
Follow conventional commit format:
```bash
feat(analysis): add support for weighted graphs
fix(visualization): resolve memory leak in PNG generation
docs(api): update NetworkAnalyzer documentation
test(integration): add tests for ego-alter analysis
```

### Development Cycle
1. Create issue describing problem/feature
2. Create branch with descriptive name
3. Develop following code standards
4. Write/update tests
5. Update documentation
6. Submit pull request
7. Address review feedback
8. Merge after approval

## Issue Reporting

### Bug Reports
Include:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, package version)
- Error messages and stack traces

### Feature Requests
Include:
- Clear description of proposed feature
- Motivation and use cases
- Proposed implementation approach
- Alternatives considered

## Getting Help

### Resources
- **Documentation**: Start with README.md and USER_GUIDE.md
- **API Reference**: Detailed function documentation
- **Test Examples**: Look at existing tests for patterns
- **Code Examples**: Check existing code for style and patterns

### Communication
- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Code Review**: For technical discussions during PR review

## Development Environment Tips

### IDE Setup
- Configure your IDE to use ruff for formatting and linting
- Enable type checking with mypy
- Set up pytest integration for running tests

### Pre-commit Hooks (Optional)
```bash
pip install pre-commit
pre-commit install
```

This will automatically run code quality checks before each commit.

### Performance Testing
When working on performance-critical code:
- Use the performance test suite to detect regressions
- Profile code with appropriate tools
- Consider memory usage for large networks
- Test with various network sizes
- **Centralized Caching System**: Be aware of the caching system in `utils.py` that provides:
  - 90% reduction in graph hash calculations
  - 95% reduction in graph conversion overhead
  - 80% reduction in graph traversal time
  - Automatic memory management with size limits and timeouts
- Use `get_cache_manager().clear_all_caches()` in tests to ensure clean state
- Monitor cache performance with `get_cache_manager().get_cache_stats()`

Thank you for contributing to FollowWeb!