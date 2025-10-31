# Centralized Parallel Processing Guide

## Overview

FollowWeb now features a centralized parallel processing system that standardizes and optimizes core usage across all components. The system provides intelligent core allocation, user notifications, and environment-aware optimization strategies.

## Key Features

### 🔄 Intelligent Core Allocation
- **Environment Detection**: Automatically detects CI vs local environments
- **Operation-Specific Optimization**: Different strategies for analysis, testing, and visualization
- **Resource-Aware Scaling**: Adapts to available system resources

### 📊 User Notifications
- **Real-time Core Usage**: Shows exactly how many cores are being used for each operation
- **Utilization Percentage**: Displays core utilization efficiency
- **NetworkX Optimization Status**: Reports nx-parallel availability and backends

### ⚙️ Configurable Strategies
- **Aggressive**: Uses 90% of cores (local development)
- **Moderate**: Uses 75% of cores (stable CI environments)
- **Conservative**: Uses 50% of cores (resource-constrained environments)
- **Sequential**: Single-core execution for accuracy-critical operations

## Core Components

### ParallelProcessingManager
Central coordinator for all parallel processing operations:

```python
from FollowWeb_Visualizor.utils import get_parallel_manager

manager = get_parallel_manager()
config = manager.get_parallel_config('analysis', graph_size=1000)
manager.log_parallel_config(config, logger)
```

### ParallelConfig
Configuration dataclass containing:
- `cores_available`: Total system cores
- `cores_used`: Cores allocated for operation
- `strategy`: Allocation strategy used
- `environment`: Detected environment (local/ci)
- `nx_parallel_enabled`: NetworkX optimization status
- `operation_type`: Type of operation (analysis/testing/visualization)

## Usage Examples

### Network Analysis
```python
from FollowWeb_Visualizor.utils import get_analysis_parallel_config, log_parallel_usage

# Get optimized configuration for graph analysis
config = get_analysis_parallel_config(graph_size=5000)
log_parallel_usage(config, logger)

# Output: ⚡ Running analysis in parallel using 14/16 cores (88% utilization) with NetworkX parallel optimization
```

### Testing Operations
```python
from FollowWeb_Visualizor.utils import get_testing_parallel_config

# Get configuration for different test categories
unit_config = get_testing_parallel_config('unit')        # Maximum parallelization
integration_config = get_testing_parallel_config('integration')  # Controlled parallelization  
performance_config = get_testing_parallel_config('performance')  # Sequential execution
```

### Visualization Tasks
```python
from FollowWeb_Visualizor.utils import get_visualization_parallel_config

config = get_visualization_parallel_config(data_size=2000)
# Automatically optimized for visualization workloads
```

## Environment Variables

### Global Configuration
- `FOLLOWWEB_CORES`: Override cores for all operations
- `FOLLOWWEB_ANALYSIS_CORES`: Override cores for analysis operations
- `FOLLOWWEB_VIZ_CORES`: Override cores for visualization operations

### Testing Configuration
- `PYTEST_WORKERS`: Override cores for all test types
- `UNIT_WORKERS`: Override cores for unit tests
- `INTEGRATION_WORKERS`: Override cores for integration tests
- `PERFORMANCE_WORKERS`: Override cores for performance tests

### Examples
```bash
# Use 8 cores for all analysis operations
export FOLLOWWEB_ANALYSIS_CORES=8

# Use 4 cores for integration tests
export INTEGRATION_WORKERS=4

# Disable parallel processing entirely
export FOLLOWWEB_CORES=1
```

## Operation-Specific Behavior

### Network Analysis
- **Threshold**: Parallel processing enabled for graphs > 100 nodes
- **NetworkX Integration**: Automatically uses nx-parallel when available
- **Core Allocation**: 
  - Local: 90% of cores
  - CI: 50-75% based on environment

### Testing
- **Unit Tests**: Maximum parallelization (90% of cores)
- **Integration Tests**: Controlled parallelization (25% of cores)
- **Performance Tests**: Sequential execution (1 core)
- **Mixed Test Suites**: Balanced allocation (50-90% based on environment)

### Visualization
- **Threshold**: Parallel processing for datasets > 100 elements
- **Core Allocation**: 80% of available cores (slightly reduced for memory management)

## CI Environment Detection

The system automatically detects and optimizes for various CI environments:

### Supported CI Providers
- **GitHub Actions**: Moderate strategy (75% cores)
- **GitLab CI**: Moderate strategy (75% cores)
- **Azure Pipelines**: Moderate strategy (75% cores)
- **Travis CI**: Conservative strategy (50% cores)
- **CircleCI**: Conservative strategy (50% cores)
- **Jenkins**: Conservative strategy (50% cores)

### Resource Allocation Strategies
```
Local Development:
├── Aggressive (90% cores)
└── Leave 1 core free for system

CI Environments:
├── Moderate (75% cores)
│   ├── GitHub Actions
│   ├── GitLab CI
│   └── Azure Pipelines
└── Conservative (50% cores)
    ├── Travis CI
    ├── CircleCI
    └── Other CI providers
```

## NetworkX Parallel Integration

### Automatic Detection
The system automatically detects and configures nx-parallel:

```python
from FollowWeb_Visualizor.utils import get_nx_parallel_status_message

status = get_nx_parallel_status_message()
# Returns: "nx-parallel active with backends: parallel"
```

### Status Messages
- `"nx-parallel active with backends: parallel"` - Fully functional
- `"nx-parallel active"` - Working but no backend info
- `"nx-parallel installed but not working"` - Installation issues
- `"nx-parallel not available"` - Not installed

## User Notifications

### Analysis Operations
```
⚡ Running analysis in parallel using 14/16 cores (88% utilization) with NetworkX parallel optimization
```

### Sequential Operations
```
🔄 Running analysis sequentially (1 core) - optimized for accuracy
```

### Testing Operations
```
🔄 Running unit tests in parallel using 14 workers
🔄 Running integration tests in parallel using 4 workers  
🔄 Running performance tests sequentially (parallel execution disabled)
```

## Performance Optimization

### Automatic Thresholds
- **Small Datasets**: Automatically switches to sequential processing
- **Large Datasets**: Enables parallel processing with optimal core allocation
- **Memory Management**: Reduces core usage for memory-intensive operations

### Caching and Efficiency
- **Configuration Caching**: Parallel configurations are cached for performance
- **Environment Detection**: CI environment detection is cached
- **Resource Monitoring**: Automatic adjustment based on system load

## Implementation Details

### Centralized Parallel Processing
The package uses centralized utilities for consistent parallel processing:

```python
# Centralized approach
parallel_config = get_analysis_parallel_config(graph_size)
log_parallel_usage(parallel_config, self.logger)
```

### Key Benefits
1. **Consistent Notifications**: Standardized user feedback across all components
2. **Intelligent Allocation**: Environment-aware core allocation
3. **Centralized Configuration**: Single source of truth for parallel settings
4. **Better Testing**: Unified parallel configuration for all test types

## Troubleshooting

### Common Issues

#### No Parallel Processing
```
🔄 Running analysis sequentially (1 core) - 16 cores available but using sequential mode
```
**Solution**: Check if data size meets minimum threshold or if environment variables disable parallelization.

#### Reduced Performance in CI
```
⚡ Running analysis in parallel using 8/16 cores (50% utilization) [github environment]
```
**Explanation**: This is expected behavior - CI environments use conservative allocation to prevent resource contention.

#### nx-parallel Not Working
```
NetworkX optimization: nx-parallel installed but not working - using standard NetworkX algorithms
```
**Solution**: Reinstall nx-parallel or check for compatibility issues with your NetworkX version.

### Debug Information
Enable debug logging to see detailed parallel processing information:

```python
import logging
logging.getLogger('FollowWeb_Visualizor.utils').setLevel(logging.DEBUG)
```

## Best Practices

### Development
1. **Local Testing**: Use default settings for maximum performance
2. **CI Configuration**: Let the system auto-detect and optimize
3. **Resource Monitoring**: Monitor system resources during parallel operations

### Production
1. **Environment Variables**: Use environment variables for fine-tuning
2. **Monitoring**: Monitor parallel processing efficiency in logs
3. **Scaling**: Adjust core allocation based on system performance

### Performance Tuning
1. **Threshold Adjustment**: Modify size thresholds for your specific use case
2. **Strategy Selection**: Choose appropriate strategy for your environment
3. **Resource Allocation**: Balance parallel processing with system stability

## Implementation Details

### NetworkX Parallel Integration
The system automatically detects and configures nx-parallel for NetworkX operations:

```python
# Automatic nx-parallel detection in analysis.py
try:
    import nx_parallel
    NX_PARALLEL_AVAILABLE = True
except ImportError:
    NX_PARALLEL_AVAILABLE = False
```

### Enhanced Algorithms
- **Betweenness Centrality**: Parallel processing with automatic fallback
- **Community Detection**: Parallel-aware community detection algorithms
- **K-Core Decomposition**: Optimized for large graph processing

### Centralized System Design
The current centralized system provides unified parallel processing:
- Consolidated parallel configuration across all modules
- Standardized user notifications and logging
- Unified environment detection and resource allocation

## API Reference

### Core Functions
- `get_parallel_manager()`: Get global parallel processing manager
- `get_analysis_parallel_config(graph_size)`: Get analysis configuration
- `get_testing_parallel_config(category)`: Get testing configuration
- `get_visualization_parallel_config(data_size)`: Get visualization configuration
- `log_parallel_usage(config, logger)`: Log parallel usage with user notifications
- `is_nx_parallel_available()`: Check nx-parallel availability
- `get_nx_parallel_status_message()`: Get user-friendly nx-parallel status

### Configuration Classes
- `ParallelConfig`: Configuration dataclass
- `ParallelProcessingManager`: Central manager class

This centralized system ensures consistent, efficient, and user-friendly parallel processing across the entire FollowWeb package.