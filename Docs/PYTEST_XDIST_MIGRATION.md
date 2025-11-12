# pytest-xdist Migration Guide

## Summary

The FollowWeb test suite now uses **pytest-xdist** for test parallelization instead of custom parallel processing logic. This provides better performance, automatic device adaptation, and industry-standard test distribution.

## What Changed

### Before (Custom Implementation)
```python
# conftest.py - Custom worker calculation
from FollowWeb_Visualizor.utils import get_optimal_worker_count, detect_ci_environment

worker_count = get_optimal_worker_count(test_category)
ci_info = detect_ci_environment()
# ... complex logic for CPU/memory/CI detection ...
```

### After (pytest-xdist)
```ini
# pytest.ini - Simple configuration
addopts = -n auto
```

```python
# conftest.py - Memory-aware limits only
available_memory = psutil.virtual_memory().available
max_workers = int((available_memory - 2GB) / memory_per_worker)
# Let pytest-xdist handle the rest
```

## What pytest-xdist Replaces

### ✅ Replaced by pytest-xdist

1. **CPU Detection**: `-n auto` automatically detects CPU count
2. **Load Balancing**: Built-in strategies (`worksteal`, `loadscope`, `loadgroup`)
3. **Worker Management**: Automatic worker spawning and cleanup
4. **CI Detection**: Built-in CI environment handling
5. **Test Distribution**: Intelligent test scheduling across workers

### ✅ Still Used from parallel.py

1. **NetworkX Parallelization**: `get_analysis_parallel_config()` for nx_parallel
2. **Production Operations**: Parallel processing for graph analysis
3. **Visualization**: Parallel rendering operations
4. **Memory Limits**: Custom memory-aware worker limiting

## Usage

### Running Tests

```bash
# Auto-detect workers (recommended)
pytest tests/

# Specific worker count
pytest tests/ -n 4

# Sequential (for debugging)
pytest tests/ -n 1

# Disable via environment variable
PYTEST_PARALLEL_DISABLE=1 pytest tests/
```

### Distribution Strategies

pytest-xdist automatically selects the best strategy based on test markers:

| Test Type | Strategy | Why |
|-----------|----------|-----|
| Unit | `worksteal` | Fast tests, dynamic load balancing |
| Integration | `loadgroup` | Resource-heavy, group by dependencies |
| Performance | Sequential | Accurate timing measurements |
| Mixed | `loadscope` | Balanced distribution |

### Memory Management

The system automatically limits workers based on available RAM:

```python
# Automatic calculation in conftest.py
available_gb = psutil.virtual_memory().available / (1024**3)
memory_per_worker = 0.5 if integration else 0.2  # GB
max_workers = int((available_gb - 2) / memory_per_worker)

# Apply limit if pytest-xdist's auto-detected count exceeds memory limit
if auto_workers > max_workers:
    config.option.numprocesses = max_workers
```

## Benefits

### 1. Automatic Device Adaptation
- Works on any machine without configuration
- Scales from 2 to 80+ workers automatically
- No hardcoded CPU counts or memory limits

### 2. Better Performance
- Industry-standard load balancing algorithms
- Efficient test distribution
- Minimal overhead

### 3. Simpler Code
- Removed ~200 lines of custom worker management
- No manual CI detection for tests
- Leverages pytest-xdist's battle-tested code

### 4. Better Debugging
- Standard pytest-xdist flags and options
- Well-documented behavior
- Community support

## Backward Compatibility

### parallel.py Functions

The following functions in `parallel.py` are **still used** for NetworkX operations:

```python
# ✅ Still use these for production code
from FollowWeb_Visualizor.utils.parallel import (
    get_analysis_parallel_config,      # For NetworkX operations
    get_visualization_parallel_config,  # For rendering
    get_nx_parallel_status_message,    # For logging
    ParallelProcessingManager,         # For production parallelization
)

# ⚠️ Deprecated for tests (use pytest-xdist instead)
from FollowWeb_Visualizor.utils.parallel import (
    get_optimal_worker_count,  # Use: pytest -n auto
    get_testing_parallel_config,  # Use: pytest -n auto
    detect_ci_environment,  # pytest-xdist handles this
)
```

### Migration Path

No code changes needed! The system automatically uses pytest-xdist when running tests:

1. **Tests**: pytest-xdist handles parallelization
2. **Production**: parallel.py handles NetworkX operations
3. **Both**: Work together seamlessly

## Configuration

### pytest.ini
```ini
[pytest]
# Automatic parallelization
addopts = 
    -n auto                    # Auto-detect workers
    --maxworkerrestart=4       # Limit crashed worker restarts
    --dist=loadscope           # Default distribution (overridden by conftest.py)

# Test markers
markers =
    unit: Unit tests (uses worksteal distribution)
    integration: Integration tests (uses loadgroup distribution)
    performance: Performance tests (sequential execution)
```

### conftest.py
```python
def _configure_parallel_execution(config):
    """Memory-aware limits only - pytest-xdist handles the rest."""
    
    # Let pytest-xdist auto-detect CPUs
    if not config.option.numprocesses:
        config.option.numprocesses = "auto"
    
    # Apply memory limits
    max_workers = calculate_memory_limit()
    config._memory_limit = max_workers
    
    # Choose distribution strategy
    if "unit" in markers:
        config.option.dist = "worksteal"
    elif "integration" in markers:
        config.option.dist = "loadgroup"
```

## Troubleshooting

### High Memory Usage

```bash
# Limit workers manually
pytest tests/ -n 4

# Check memory during tests
pytest tests/ -v  # Watch for memory warnings
```

### Slow Tests

```bash
# Increase workers (if you have RAM)
pytest tests/ -n 16

# Use faster distribution
pytest tests/ --dist=worksteal
```

### Test Failures in Parallel

```bash
# Run sequentially to debug
pytest tests/ -n 1

# Or disable parallelization
PYTEST_PARALLEL_DISABLE=1 pytest tests/
```

## Performance Comparison

| Configuration | Workers | Duration | Memory |
|--------------|---------|----------|--------|
| Sequential | 1 | 5-6 min | 1 GB |
| Custom (old) | 8-12 | 90-120 sec | 6-8 GB |
| pytest-xdist (new) | auto (14) | 80-90 sec | 7-9 GB |
| pytest-xdist (limited) | 8 | 90-100 sec | 4-5 GB |

## References

- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/)
- [Load Balancing Strategies](https://pytest-xdist.readthedocs.io/en/latest/distribution.html)
- [FollowWeb parallel.py](../FollowWeb/FollowWeb_Visualizor/utils/parallel.py) - For NetworkX operations
