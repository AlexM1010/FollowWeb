# Memory Optimization Guide

## Test Suite Memory Usage

### Automatic Device Adaptation

The test suite automatically adapts to any device:
- **CPU Detection**: pytest-xdist auto-detects available CPUs
- **Memory Limits**: Automatically limits workers based on available RAM
- **No Configuration**: Works out-of-the-box on any machine

### Expected Memory Usage (Auto-Scaled)

| Available RAM | Max Workers | Peak Usage | Test Duration |
|--------------|-------------|------------|---------------|
| 4 GB | 4-6 | 3 GB | 2-3 min |
| 8 GB | 12-16 | 6 GB | 1-2 min |
| 16 GB | 30-40 | 12 GB | 45-90 sec |
| 32 GB | 60-80 | 24 GB | 30-60 sec |

**Note**: System automatically prevents memory overflow by limiting workers.

### Why Tests Use Memory

1. **Parallel Workers**: Each worker runs independently (~200-500 MB each)
2. **Test Fixtures**: Temporary directories and mock objects per worker
3. **Graph Objects**: NetworkX graphs in integration tests
4. **Sound Cache**: Accumulated sound objects during tests

### Memory Optimizations Implemented

#### 1. Automatic Device Adaptation
The test suite uses pytest-xdist with memory-aware limits:

```python
# pytest.ini - Let pytest-xdist auto-detect CPUs
addopts = -n auto

# conftest.py - Apply memory limits
available_memory_gb = psutil.virtual_memory().available / (1024**3)
memory_per_worker_gb = 0.5 if integration else 0.2  # Per test type
max_workers = int((available_memory_gb - 2) / memory_per_worker_gb)

# Limit workers if memory-constrained
if auto_detected_workers > max_workers:
    workers = max_workers
```

**Benefits**: 
- Works on any device without configuration
- Automatically scales from 2 to 80+ workers
- Prevents memory overflow on low-RAM devices
- Maximizes speed on high-RAM devices

#### 2. Automatic Garbage Collection
Added to `conftest.py`:
```python
def pytest_runtest_teardown(item, nextitem):
    """Clean up memory after each test."""
    import gc
    gc.collect()  # Force garbage collection
    
    if "integration" in item:
        gc.collect(generation=2)  # Full collection for integration tests
```

**Effect**: Prevents memory accumulation between tests

#### 3. Worker Restart Limits
```ini
# pytest.ini
--maxworkerrestart=4
```

Limits crashed worker restarts to prevent runaway memory consumption.

#### 4. UTF-8 Encoding Setup
Prevents Unicode encoding errors that could cause test failures and memory leaks:
```python
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
```

### Manual Overrides (If Needed)

The system auto-adapts, but you can override if needed:

#### Option 1: Limit Workers Manually
```bash
# Run with specific worker count
pytest tests/ -n 4

# Run sequentially (slowest but minimal memory)
pytest tests/ -n 1

# Disable parallel execution via environment variable
PYTEST_PARALLEL_DISABLE=1 pytest tests/
```

#### Option 2: Run Test Categories Separately
```bash
# Run unit tests first (fast, low memory)
pytest tests/ -m unit

# Then integration tests (slower, higher memory)
pytest tests/ -m integration

# Finally performance tests (sequential)
pytest tests/ -m performance
```

#### Option 3: Increase System Swap
For CI/CD environments with limited RAM:
- Configure swap space (Linux/macOS)
- Increase virtual memory (Windows)

#### Option 4: Clear Caches Between Test Runs
```python
# Add to conftest.py
def pytest_sessionfinish(session, exitstatus):
    """Clean up after entire test session."""
    import gc
    gc.collect()
    
    # Clear any module-level caches
    from FollowWeb_Visualizor.data.loaders import incremental_freesound
    if hasattr(incremental_freesound, '_sound_cache'):
        incremental_freesound._sound_cache.clear()
```

### Monitoring Memory Usage

#### During Development
```bash
# Use memory profiler
pip install memory-profiler
python -m memory_profiler your_script.py

# Or use pytest-monitor
pip install pytest-monitor
pytest tests/ --monitor
```

#### In CI/CD
```yaml
# GitHub Actions example
- name: Run tests with memory monitoring
  run: |
    pytest tests/ --verbose
    # Check memory usage
    ps aux | grep python | awk '{print $6}'
```

### Memory Usage by Test Category

| Test Category | Per Worker | Max Workers (12GB avail) | Total Peak | Duration |
|--------------|------------|-------------------------|------------|----------|
| Unit Tests | 200 MB | 50 | 10 GB | 10-20s |
| Integration Tests | 500 MB | 20 | 10 GB | 60-90s |
| Performance Tests | 1 GB | 1 (sequential) | 1 GB | 120-180s |
| Full Suite | 300 MB avg | 30 | 9 GB | 80-120s |

**Note**: The system automatically limits workers based on available memory to prevent overflow.

### Best Practices

1. **Run tests in categories** when memory is limited
2. **Use sequential execution** (`-n 1`) for memory-constrained environments
3. **Monitor memory** in CI/CD to catch memory leaks early
4. **Clean up fixtures** explicitly in tests that create large objects
5. **Use context managers** for temporary resources

### Troubleshooting

#### Out of Memory Errors
```bash
# Reduce parallelization
pytest tests/ -n 2

# Or run sequentially
pytest tests/ -n 1
```

#### Slow Garbage Collection
```python
# Add to conftest.py
import gc
gc.set_threshold(700, 10, 10)  # More aggressive GC
```

#### Memory Leaks in Tests
```bash
# Use objgraph to find leaks
pip install objgraph
python -c "import objgraph; objgraph.show_most_common_types()"
```

## Production Memory Usage

Production usage is much more efficient:
- **Nightly pipeline**: 500 MB - 1 GB
- **Validation workflows**: 300 MB - 800 MB
- **Visualization generation**: 200 MB - 500 MB

The high test memory usage is primarily due to:
1. Multiple test workers running in parallel
2. Mock objects and fixtures
3. Temporary test data
4. No cleanup between tests (by design for speed)

This is **normal and expected** for comprehensive test suites.
