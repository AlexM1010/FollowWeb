# FollowWeb Configuration Files

This directory contains essential configuration files for FollowWeb network analysis. The configurations follow standard JSON format with comprehensive documentation provided separately.

## Available Configurations

### Core Configuration Files

- **`comprehensive_layout_config.json`** - Complete configuration with all available options enabled
  - Full feature set demonstration
  - High-quality visualization settings
  - All layout algorithms configured
  - Suitable for production use and as a reference

- **`fast_config.json`** - Optimized configuration for quick analysis
  - Fast mode enabled with performance optimizations
  - Lower k-values for faster processing
  - Reduced image resolution for speed
  - Ideal for development and testing

### Documentation

- **`CONFIG_REFERENCE.md`** - Comprehensive documentation for all configuration options
  - Detailed parameter explanations
  - Configuration examples
  - Best practices and usage guidelines
  - Complete reference for all available settings

## Configuration Documentation Approach

Since JSON doesn't support comments, we use a separate documentation approach:

1. **Clean JSON files** - Valid JSON without comments for actual use
2. **Comprehensive documentation** - Detailed explanations in `CONFIG_REFERENCE.md`
3. **Inline examples** - Configuration snippets with explanations in documentation
4. **Template approach** - Well-documented example configurations

## Usage Examples

### Basic Usage
```bash
# Use fast configuration for development
followweb --config configs/fast_config.json

# Use comprehensive configuration for production
followweb --config configs/comprehensive_layout_config.json
```

### Custom Configuration
```bash
# Override specific parameters
followweb --config configs/fast_config.json --k-value 5
```

## Configuration Features

### Performance Optimization
All configurations benefit from FollowWeb's caching system:
- **Graph Hash Caching**: Eliminates duplicate calculations (90% reduction)
- **Layout Position Caching**: Shares calculations between outputs
- **Community Color Caching**: Avoids regenerating color schemes
- **Memory Management**: Automatic cache size limits and cleanup

### Validation
- **Schema Validation**: All configurations are validated against the config schema
- **Error Reporting**: Clear error messages for invalid configurations
- **Default Fallbacks**: Sensible defaults for missing parameters

### Flexibility
- **CLI Overrides**: Command-line arguments can override config file settings
- **Environment Variables**: Support for environment-based configuration
- **Modular Structure**: Configurations can be partially specified

## Best Practices

1. **Start with Templates** - Use provided configurations as starting points
2. **Refer to Documentation** - Check `CONFIG_REFERENCE.md` for parameter details
3. **Test Performance** - Use fast config for development, comprehensive for production
4. **Validate Settings** - Use built-in validation to catch configuration errors
5. **Document Changes** - Keep notes on custom modifications for reproducibility

## Configuration Structure

The configuration files follow a hierarchical structure:
- **Input/Output**: File paths and output settings
- **Pipeline**: Analysis strategy and execution control
- **Analysis**: Network analysis parameters
- **Visualization**: Graph rendering and styling options
- **Performance**: Optimization and caching settings

For detailed information about each configuration section, see `CONFIG_REFERENCE.md`.