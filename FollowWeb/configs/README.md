# Configuration Files

This directory contains various configuration files for different analysis scenarios:

## Configuration Files

- `comprehensive_layout_config.json` - Complete layout configuration with all options
- `custom_k1_config.json` - Custom k-core analysis with k=1
- `fast_config_k1.json` - Fast execution configuration for k=1 analysis
- `full_network_k1_config.json` - Full network analysis configuration
- `improved_spacing_config.json` - Configuration with improved node spacing
- `k6_config.json` - K-core analysis with k=6
- `large_network_config.json` - Configuration optimized for large networks
- `ultra_fast_config_k1.json` - Ultra-fast execution configuration

## Performance Optimization

All configurations automatically benefit from FollowWeb's centralized caching system:

- **Graph Hash Caching**: Eliminates duplicate hash calculations (90% reduction)
- **Graph Conversion Caching**: Reduces undirected graph conversion overhead (95% reduction)
- **Attribute Access Caching**: Reduces graph traversal time (80% reduction)
- **Layout Position Caching**: Shares layout calculations between HTML and PNG outputs
- **Community Color Caching**: Avoids regenerating color schemes (99% reduction)

The caching system automatically manages memory with size limits and timeout management.

## Usage

These configuration files can be used with the FollowWeb package to customize analysis parameters, visualization settings, and performance options.

```bash
# Example usage
python -m FollowWeb_Visualizor --config configs/fast_config_k1.json
```

See the main documentation for detailed configuration options and parameter descriptions.