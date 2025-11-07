# FollowWeb Configuration Examples

5 configuration files for different network analysis scenarios. Includes complete reference and ready-to-use configurations.

---

## Quick Reference

- **`complete_config.json`** - ALL available parameters with explanations (reference)
- **`enhanced_default_config.json`** - General purpose, medium networks (1K-5K nodes)
- **`fast_mode_config.json`** - Large networks (>10K nodes), quick analysis
- **`research_config.json`** - Publication quality, detailed analysis
- **`ego_network_config.json`** - Personal networks, specific user focus

## Usage
```bash
followweb --config docs/config_examples/[filename].json
```

---

## Configuration Files

### 1. `complete_config.json` - Complete Reference
Shows ALL available parameters with explanations and default values.

**Use for:**
- Understanding all configuration options
- Reference when creating custom configurations
- Learning advanced layout and analysis settings

**Settings:**
- Every available parameter documented
- All layout algorithms (spring, kamada-kawai, circular, shell)
- Complete emoji, output, and analysis options
- Advanced physics parameters for layouts

### 2. `enhanced_default_config.json` - General Purpose
Shows all available parameters with default values.

**Use for:**
- Starting point for custom configurations
- Medium networks (1K-5K nodes)
- Learning all available options

**Settings:**
- All analysis stages enabled
- HTML, PNG, and text reports
- Balanced performance and quality

### 3. `fast_mode_config.json` - Large Networks
Optimized for speed with large datasets.

**Use for:**
- Networks >10K nodes
- Quick exploration
- Batch processing

**Settings:**
- Path analysis disabled
- PNG generation disabled
- Lower k-values for speed
- Timing logs enabled

### 4. `research_config.json` - Publication Quality
Maximum precision for academic work.

**Use for:**
- Academic research
- Publications and presentations
- Detailed analysis

**Settings:**
- PNG output (2400x1800, 600 DPI)
- Maximum layout iterations
- Higher k-values for precision
- Detailed timing logs

### 5. `ego_network_config.json` - Personal Networks
Analysis centered on a specific user.

**Use for:**
- Personal network analysis
- Social influence studies
- Contact path analysis

**Settings:**
- Ego-alter k-core strategy
- Contact path analysis enabled
- Lower k-values for personal networks
- **Note:** Set `ego_username` before running

## Configuration Structure

All configuration files follow the same hierarchical structure:

```json
{
  "_comment": "Brief description of configuration purpose",
  "_description": "Detailed explanation of use cases and features",
  
  "input_file": "path/to/data.json",
  "output_file_prefix": "Output/Prefix",
  "strategy": "k-core|reciprocal_k-core|ego_alter_k-core",
  
  "pipeline_stages": {
    "enable_strategy": true,
    "enable_analysis": true,
    "enable_visualization": true,
    "enable_community_detection": true,
    "enable_centrality_analysis": true,
    "enable_path_analysis": true
  },
  
  "analysis_mode": {
    "mode": "fast|medium|full",
    "sampling_threshold": 5000,
    "max_layout_iterations": 1000,
    "enable_fast_algorithms": false
  },
  
  "output_control": {
    "generate_html": true,
    "generate_png": true,
    "generate_reports": true,
    "enable_timing_logs": false
  },
  
  "k_values": {
    "strategy_k_values": {
      "k-core": 10,
      "reciprocal_k-core": 10,
      "ego_alter_k-core": 3
    },
    "default_k_value": 10
  },
  
  "visualization": {
    "node_size_metric": "degree|betweenness|eigenvector",
    "base_node_size": 10.0,
    "scaling_algorithm": "linear|logarithmic",
    "static_image": {
      "generate": true,
      "layout": "spring|kamada_kawai|circular",
      "width": 1200,
      "height": 800,
      "dpi": 300
    }
  }
}
```

## Key Configuration Parameters

### Analysis Strategies
- **`k-core`**: Full network analysis identifying densely connected subgraphs
- **`reciprocal_k-core`**: Focus on mutual connections and bidirectional relationships
- **`ego_alter_k-core`**: Personal network analysis centered on specific users

### Analysis Modes
- **`fast`**: Optimized for speed with reduced precision (large networks)
- **`medium`**: Balanced performance and accuracy (most use cases)
- **`full`**: Maximum precision and detailed analysis (research)

### Output Formats
- **HTML**: Interactive visualizations with hover tooltips and physics simulation
- **PNG**: High-resolution static images for presentations and publications
- **TXT**: Detailed metrics reports with network statistics and parameters

## Customizing Configurations

### 1. Start with Base Configuration
Choose the configuration that best matches your use case:
- **General analysis**: `enhanced_default_config.json`
- **Large networks**: `fast_mode_config.json`
- **Research/publications**: `research_config.json`
- **Personal networks**: `ego_network_config.json`

### 2. Common Customizations

#### Performance Optimization
```json
{
  "analysis_mode": {
    "mode": "fast",
    "sampling_threshold": 1000,
    "max_layout_iterations": 100
  },
  "pipeline_stages": {
    "enable_path_analysis": false
  }
}
```

#### Publication Quality Output
```json
{
  "analysis_mode": {
    "mode": "full",
    "sampling_threshold": 15000,
    "max_layout_iterations": 2000
  },
  "visualization": {
    "static_image": {
      "width": 2400,
      "height": 1800,
      "dpi": 600
    }
  }
}
```

#### Minimal Output for Batch Processing
```json
{
  "output_control": {
    "generate_html": false,
    "generate_png": false,
    "generate_reports": true
  },
  "pipeline_stages": {
    "enable_path_analysis": false
  }
}
```

### 3. Validation and Testing
Always validate your configuration before running analysis:
```bash
followweb --config my_config.json --validate-config
```

## CLI Override Examples

You can override any configuration file setting using CLI parameters:

```bash
# Override analysis mode
followweb --config my_config.json --fast-mode

# Override k-values
followweb --config my_config.json --k-core 15

# Override output settings
followweb --config my_config.json --no-png --enable-timing-logs

# Override input/output files
followweb --config my_config.json --input large_network.json --output-prefix Results/Analysis
```

## Performance Guidelines

| Network Size | Recommended Config | Expected Time | Memory Usage |
|-------------|-------------------|---------------|--------------|
| Any size | `complete_config.json` (reference only) | - | - |
| < 1K nodes | `enhanced_default_config.json` | < 30 seconds | < 500MB |
| 1K-5K nodes | `enhanced_default_config.json` | 1-5 minutes | 500MB-2GB |
| 5K-10K nodes | `fast_mode_config.json` | 2-10 minutes | 1-4GB |
| > 10K nodes | `fast_mode_config.json` with higher k-values | 5-30 minutes | 2-8GB |

## Troubleshooting

### Common Configuration Errors

1. **"At least one output format must be enabled"**
   - Solution: Enable at least one of `generate_html`, `generate_png`, `generate_reports`

2. **"ego_username must be set for ego_alter_k-core strategy"**
   - Solution: Set `ego_username` when using `ego_alter_k-core` strategy

3. **"Visualization stage requires analysis stage to be enabled"**
   - Solution: Enable analysis stage or disable visualization stage

4. **Memory issues with large networks**
   - Solution: Use `fast_mode_config.json` and increase k-values

### Getting Help

- **Configuration Guide**: See [../CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md) for detailed parameter documentation
- **User Guide**: See [../USER_GUIDE.md](../USER_GUIDE.md) for usage examples and tutorials
- **API Reference**: See [../API_REFERENCE.md](../API_REFERENCE.md) for programmatic usage

For additional support, validate your configuration and check the error messages for specific guidance.