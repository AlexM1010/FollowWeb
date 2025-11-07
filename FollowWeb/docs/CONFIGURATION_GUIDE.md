# FollowWeb Enhanced Configuration Guide

## Overview

The FollowWeb pipeline uses an enhanced configuration system that provides centralized, modular control over all aspects of network analysis. This guide covers the new configuration options, CLI parameters, and usage examples.

## Key Features

- **Modular Pipeline Control**: Enable/disable individual stages (strategy, analysis, visualization)
- **Analysis Modes**: Fast, Medium, Full modes with automatic performance optimization
- **Flexible Output Control**: Independent control of HTML, PNG, reports, and timing logs
- **Advanced K-Value Management**: Strategy-specific k-values with CLI override support
- **Component-Level Control**: Fine-grained control over analysis components

## Configuration Structure

### Pipeline Stages Configuration

Control which major phases of the pipeline are executed:

```json
{
  "pipeline_stages": {
    "enable_strategy": true,      // Graph loading and filtering (required)
    "enable_analysis": true,      // Network analysis algorithms
    "enable_visualization": true, // HTML/PNG generation
    "enable_community_detection": true,  // Community detection within analysis
    "enable_centrality_analysis": true,  // Centrality calculations within analysis
    "enable_path_analysis": true        // Path analysis within analysis
  }
}
```

**Stage Dependencies:**
- Visualization requires Analysis to be enabled
- At least one analysis component must be enabled if Analysis is enabled
- Strategy stage cannot be disabled (required for pipeline execution)

### Analysis Modes

Choose analysis depth and performance optimization:

```json
{
  "analysis_mode": {
    "mode": "full",                    // "fast", "medium", or "full"
    "sampling_threshold": 5000,        // Node count for enabling sampling
    "max_layout_iterations": null,     // Layout algorithm iterations (null = mode default)
    "enable_fast_algorithms": false    // Use approximate algorithms
  }
}
```

**Mode Characteristics:**

| Mode | Sampling Threshold | Layout Iterations | Fast Algorithms | Best For |
|------|-------------------|-------------------|-----------------|----------|
| Fast | 1000 | 100 | Yes | Large networks (>10K nodes), quick exploration |
| Medium | 5000 | 500 | Selective | Medium networks (1K-10K nodes), balanced analysis |
| Full | 10000 | 1000 | No | Research, publication-quality results |

### Output Control

Fine-grained control over output file generation:

```json
{
  "output_control": {
    "generate_html": true,        // Interactive Pyvis visualization
    "generate_png": true,         // Static matplotlib image
    "generate_reports": true,     // Text metrics and statistics
    "enable_timing_logs": false,  // Detailed timing information
    "output_formatting": {
      "indent_size": 2,
      "group_related_settings": true,
      "highlight_key_values": true,
      "use_human_readable_labels": true
    }
  }
}
```

### K-Value Configuration

Strategy-specific k-values for graph pruning:

```json
{
  "k_values": {
    "strategy_k_values": {
      "k-core": 10,
      "reciprocal_k-core": 10,
      "ego_alter_k-core": 10
    },
    "default_k_value": 10,
    "allow_cli_override": true
  }
}
```

**K-Value Guidelines:**
- **k-core**: 1-50 (1=include all nodes, 20+=very dense cores only)
- **reciprocal_k-core**: 1-30 (higher values = stronger mutual connections)
- **ego_alter_k-core**: 1-20 (depends on ego user's network size)

## CLI Parameter Reference

### Configuration Management
```bash
--config FILE                 # Load configuration from JSON file
--validate-config             # Validate configuration and exit
--print-default-config        # Print default configuration as JSON
```

### Analysis Modes
```bash
--fast-mode                   # Fast mode with aggressive optimizations
--medium-mode                 # Balanced analysis and performance
--full-mode                   # Comprehensive analysis (default)
```

### Pipeline Stage Control
```bash
--skip-analysis               # Skip analysis phase (visualization only)
--skip-visualization          # Skip visualization phase (analysis only)
--analysis-only               # Equivalent to --skip-visualization
```

### Analysis Component Control
```bash
--skip-path-analysis          # Skip path analysis (significant speedup)
--skip-community-detection    # Skip community detection
--skip-centrality-analysis    # Skip centrality calculations
```

### K-Value Parameters
```bash
--k-core K                    # K-value for k-core strategy
--k-reciprocal K              # K-value for reciprocal_k-core strategy
--k-ego-alter K               # K-value for ego_alter_k-core strategy
```

### Output Control
```bash
--no-png                      # Disable PNG generation
--no-html                     # Disable HTML generation
--no-reports                  # Disable text reports
--enable-timing-logs          # Enable timing logs
```

### Performance Options
```bash
--sampling-threshold N        # Sampling threshold for large graphs
--max-layout-iterations N     # Maximum layout iterations
```

## Usage Examples

### Basic Usage

```bash
# Default configuration (full mode)
followweb

# Load custom configuration
followweb --config my_config.json

# Validate configuration
followweb --config my_config.json --validate-config
```

### Analysis Mode Examples

```bash
# Fast mode for large networks
followweb --fast-mode --input large_network.json

# Medium mode with custom sampling
followweb --medium-mode --sampling-threshold 3000

# Full mode with high-quality layout
followweb --full-mode --max-layout-iterations 1500
```

### Pipeline Control Examples

```bash
# Analysis only (no visualization)
followweb --analysis-only

# Visualization only (skip analysis)
followweb --skip-analysis

# Skip expensive path analysis
followweb --skip-path-analysis
```

### Strategy and K-Value Examples

```bash
# Reciprocal k-core with custom k-value
followweb --strategy reciprocal_k-core --k-reciprocal 15

# Ego-alter analysis
followweb --strategy ego_alter_k-core --ego-username john_doe --k-ego-alter 5
```

### Output Control Examples

```bash
# HTML only (no PNG or reports)
followweb --no-png --no-reports

# Enable timing logs
followweb --enable-timing-logs

# Custom output location
followweb --output-prefix Results/MyAnalysis
```

## Configuration File Examples

See the `docs/config_examples/` directory for complete configuration examples:

- `enhanced_default_config.json` - Complete default configuration
- `fast_mode_config.json` - Fast mode for large networks
- `research_config.json` - Research-grade comprehensive analysis
- `ego_network_config.json` - Personal network analysis
- `batch_processing_config.json` - Automated batch processing
- `visualization_only_config.json` - Visualization-only mode

## Error Messages and Troubleshooting

### Common Configuration Errors

**"At least one output format must be enabled"**
- Solution: Enable at least one of `generate_html`, `generate_png`, or `generate_reports`

**"Visualization stage requires analysis stage to be enabled"**
- Solution: Enable analysis stage or disable visualization stage

**"ego_username must be set for ego_alter_k-core strategy"**
- Solution: Set `ego_username` when using `ego_alter_k-core` strategy

**"At least one analysis component must be enabled when analysis stage is enabled"**
- Solution: Enable at least one of community detection, centrality analysis, or path analysis

### Performance Optimization Tips

1. **Large Networks (>10K nodes)**: Use `--fast-mode` and `--skip-path-analysis`
2. **Memory Constraints**: Lower `--sampling-threshold` and `--max-layout-iterations`
3. **Batch Processing**: Use `--analysis-only` and `--no-html --no-png`
4. **Quick Exploration**: Use `--fast-mode --skip-path-analysis --no-png`

## Layout Configuration

### Overview
FollowWeb supports comprehensive layout configuration with full control over physics parameters, layout algorithms, and visual spacing.

### Layout Configuration Structure
```json
{
  "visualization": {
    "png_layout": {
      "force_spring_layout": true,
      "align_with_html": false,
      
      "spring": { /* Spring layout physics */ },
      "kamada_kawai": { /* Kamada-Kawai parameters */ },
      "circular": { /* Circular arrangement options */ },
      "shell": { /* Shell layout configuration */ }
    }
  }
}
```

### Spring Layout Configuration
```json
"spring": {
  "k": 0.8,                    // Spring constant (node repulsion)
  "iterations": 300,           // Number of layout iterations
  "spring_length": 1.2,        // Natural length of springs (edges)
  "repulsion_strength": 1.2,   // Node-to-node repulsion force
  "attraction_strength": 0.8,  // Edge attraction force
  "center_gravity": 0.02,      // Pull toward center
  "damping": 0.85,             // Velocity damping
  "enable_multistage": true,   // Use 3-stage refinement
  "initial_k_multiplier": 2.0, // Stage 1: k multiplier for separation
  "final_k_multiplier": 0.7    // Stage 3: k multiplier for fine-tuning
}
```

### Other Layout Types
```json
// Kamada-Kawai Layout
"kamada_kawai": {
  "max_iterations": 1500,
  "tolerance": 1e-7,
  "distance_scale": 1.2
}

// Circular Layout
"circular": {
  "radius": null,              // Auto-calculate radius
  "group_by_community": true,  // Group communities together
  "community_separation": 0.3  // Angular gap between communities
}

// Shell Layout
"shell": {
  "shell_spacing": 1.5,        // Distance between shells
  "arrange_by_centrality": true, // Arrange by node importance
  "centrality_metric": "degree"  // "degree", "betweenness", "eigenvector"
}
```

### Layout Parameter Guidelines

| Parameter | Effect | Recommended Range |
|-----------|--------|-------------------|
| `spring.k` | Node repulsion | 0.1-2.0 (0.8 for good spacing) |
| `spring.iterations` | Layout precision | 50-500 (300 for high quality) |
| `spring.repulsion_strength` | Repulsion multiplier | 0.5-2.0 (1.2 for dense graphs) |

### Layout Examples

**High-Quality Spacing:**
```json
{
  "visualization": {
    "png_layout": {
      "spring": {
        "k": 1.0,
        "iterations": 500,
        "repulsion_strength": 1.3,
        "enable_multistage": true
      }
    }
  }
}
```

**Fast Generation:**
```json
{
  "visualization": {
    "png_layout": {
      "spring": {
        "k": 0.8,
        "iterations": 150,
        "repulsion_strength": 1.5
      }
    }
  }
}
```

## Configuration Best Practices

The configuration system provides comprehensive validation and error reporting. Key features:

- **Enhanced Validation**: Comprehensive configuration validation with detailed error messages
- **Modular Pipeline Control**: Fine-grained control over pipeline stages
- **Analysis Mode Management**: Performance optimization through analysis modes
- **Output Control**: Precise control over generated output formats
- **Layout Optimization**: Advanced layout algorithms with physics-based parameters

Follow the examples in this guide to configure your analysis workflows effectively.