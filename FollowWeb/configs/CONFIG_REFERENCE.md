# FollowWeb Configuration Reference

This document provides comprehensive documentation for all FollowWeb configuration options. Use this as a reference when creating or modifying configuration files.

## Configuration Files

- **`comprehensive_layout_config.json`** - Complete configuration with all available options enabled
- **`fast_config.json`** - Optimized configuration for quick analysis and visualization
- **`freesound_sigma_config.json`** - Configuration for Freesound audio sample network analysis with Sigma.js visualization

## Configuration Structure

### Input/Output Configuration

```json
{
  "input_file": "examples/followers_following.json",
  "output_file_prefix": "Output/FollowWeb"
}
```

- **`input_file`** - Path to input data file (JSON format with user/followers/following structure). Set to `null` when using Freesound data source.
- **`output_file_prefix`** - Output file prefix for generated files (HTML, PNG, reports)

### Data Source Configuration

```json
{
  "data_source": {
    "source": "instagram",
    "freesound": {
      "api_key": "${FREESOUND_API_KEY}",
      "query": "jungle",
      "tags": ["drum", "loop"],
      "max_samples": 500,
      "include_similar": true
    }
  }
}
```

- **`source`** - Data source type: `"instagram"` or `"freesound"`
- **`freesound`** - Freesound API configuration (used when `source` is `"freesound"`)
  - **`api_key`** - Freesound API key. Use `"${FREESOUND_API_KEY}"` to load from environment variable
  - **`query`** - Text search query for audio samples (e.g., `"jungle"`, `"ambient"`)
  - **`tags`** - List of tags to filter samples (e.g., `["drum", "loop"]`). Set to `null` for no tag filtering
  - **`max_samples`** - Maximum number of samples to fetch from API
  - **`include_similar`** - Include similar sounds relationships for graph edges (recommended: `true`)

### Renderer Configuration

```json
{
  "renderer": {
    "renderer_type": "sigma",
    "template_name": "sigma_visualization.html",
    "sigma_interactive": {
      "height": "100vh",
      "width": "100%",
      "enable_webgl": true,
      "enable_audio_player": true,
      "audio_player": {
        "position": "bottom-right",
        "show_waveform": false,
        "enable_keyboard_shortcuts": false,
        "default_volume": 0.7,
        "enable_loop": true,
        "show_timeline": true,
        "show_time_display": true
      }
    }
  }
}
```

- **`renderer_type`** - Visualization renderer: `"pyvis"`, `"sigma"`, or `"all"` (generates both)
- **`template_name`** - Template file name for Sigma.js renderer
- **`sigma_interactive`** - Sigma.js renderer configuration
  - **`height`** - Canvas height (CSS units, e.g., `"100vh"`, `"800px"`)
  - **`width`** - Canvas width (CSS units, e.g., `"100%"`, `"1200px"`)
  - **`enable_webgl`** - Enable WebGL rendering for better performance with large graphs
  - **`enable_audio_player`** - Enable audio playback for Freesound samples (MVP feature)
  - **`audio_player`** - Audio player configuration (MVP scope)
    - **`position`** - Player position: `"bottom-right"`, `"bottom-left"`, `"top-right"`, `"top-left"`
    - **`show_waveform`** - Show waveform visualization (deferred to future release)
    - **`enable_keyboard_shortcuts`** - Enable keyboard controls (deferred to future release)
    - **`default_volume`** - Default volume level (0.0 to 1.0)
    - **`enable_loop`** - Enable loop toggle button
    - **`show_timeline`** - Show timeline scrubber for seeking
    - **`show_time_display`** - Show current time and duration

### Checkpoint Configuration

```json
{
  "checkpoint": {
    "checkpoint_dir": "checkpoints/freesound",
    "checkpoint_interval": 100,
    "max_runtime_hours": 2.0,
    "verify_existing_sounds": true,
    "verification_age_days": 30,
    "metadata_update_mode": "merge"
  }
}
```

- **`checkpoint_dir`** - Directory to store checkpoint files for incremental graph building
- **`checkpoint_interval`** - Save checkpoint after processing this many samples
- **`max_runtime_hours`** - Maximum runtime in hours before graceful stop (set to `null` for unlimited)
- **`verify_existing_sounds`** - Verify that existing samples still exist on Freesound API
- **`verification_age_days`** - Only verify samples older than this many days
- **`metadata_update_mode`** - Metadata update strategy: `"merge"` (add/update fields) or `"replace"` (replace all fields)

### Pipeline Configuration

```json
{
  "pipeline": {
    "strategy": "k-core",
    "skip_analysis": false,
    "ego_username": null
  }
}
```

- **`strategy`** - Analysis strategy:
  - `"k-core"` - Full network analysis with density-based pruning
  - `"reciprocal_k-core"` - Focus on mutual connections only
  - `"ego_alter_k-core"` - Personal network centered on specific user
- **`skip_analysis`** - Skip analysis phase and only generate visualizations from existing data
- **`ego_username`** - Username for ego-alter analysis (required for `ego_alter_k-core` strategy)

### Pipeline Stages Control

```json
{
  "pipeline": {
    "enable_strategy": true,
    "enable_analysis": true,
    "enable_visualization": true,
    "enable_community_detection": true,
    "enable_centrality_analysis": true,
    "enable_path_analysis": true
  }
}
```

Enable/disable individual pipeline stages for fine-grained control:
- **`enable_strategy`** - Strategy execution
- **`enable_analysis`** - Network analysis algorithms
- **`enable_visualization`** - Graph visualization generation
- **`enable_community_detection`** - Community detection algorithms
- **`enable_centrality_analysis`** - Centrality metrics calculation
- **`enable_path_analysis`** - Path finding and analysis

### Analysis Mode Configuration

```json
{
  "analysis_mode": {
    "mode": "full",
    "sampling_threshold": 5000,
    "max_layout_iterations": null,
    "enable_fast_algorithms": false
  }
}
```

- **`mode`** - Analysis depth:
  - `"fast"` - Optimized algorithms, reduced precision, faster execution
  - `"medium"` - Balanced analysis and performance
  - `"full"` - Detailed analysis, maximum precision, slower execution
- **`sampling_threshold`** - Use sampling for large networks (nodes > threshold)
- **`max_layout_iterations`** - Maximum layout iterations (`null` = unlimited)
- **`enable_fast_algorithms`** - Enable fast algorithms even in full mode

### Fame Analysis Configuration

```json
{
  "fame_analysis": {
    "find_paths_to_all_famous": true,
    "contact_path_target": null,
    "min_followers_in_network": 5,
    "min_fame_ratio": 5.0
  }
}
```

- **`find_paths_to_all_famous`** - Find paths to all famous users in the network
- **`contact_path_target`** - Target username for contact path analysis (`null` = disabled)
- **`min_followers_in_network`** - Minimum followers required to be considered in fame analysis
- **`min_fame_ratio`** - Minimum fame ratio (followers/following) to be considered famous

### K-Values Configuration

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

- **`strategy_k_values`** - K-values for different strategies (minimum connections required)
  - `"k-core"` - Full network k-core value
  - `"reciprocal_k-core"` - Reciprocal connections k-core value
  - `"ego_alter_k-core"` - Ego network k-core value
- **`default_k_value`** - Default k-value when strategy not specified
- **`allow_cli_override`** - Allow CLI arguments to override k-values

### Output Control Configuration

```json
{
  "output_control": {
    "generate_html": true,
    "generate_png": true,
    "generate_reports": true,
    "enable_timing_logs": true,
    "output_formatting": {
      "indent_size": 2,
      "group_related_settings": true,
      "highlight_key_values": true,
      "use_human_readable_labels": true,
      "emoji": {
        "fallback_level": "full"
      }
    }
  }
}
```

- **`generate_html`** - Interactive HTML visualization
- **`generate_png`** - Static PNG image
- **`generate_reports`** - Text reports with metrics
- **`enable_timing_logs`** - Enable detailed timing logs
- **`output_formatting`** - Output formatting options
  - **`indent_size`** - Indentation for formatted output
  - **`group_related_settings`** - Group related config sections
  - **`highlight_key_values`** - Highlight important values
  - **`use_human_readable_labels`** - Use descriptive labels
  - **`emoji.fallback_level`** - Emoji fallback level: `"full"`, `"simple"`, `"text"`, `"none"`

## Visualization Configuration

### Node Sizing

```json
{
  "node_size_metric": "degree",
  "base_node_size": 8.0,
  "node_size_multiplier": 4.0,
  "scaling_algorithm": "logarithmic"
}
```

- **`node_size_metric`** - Metric for node sizing: `"degree"`, `"betweenness"`, `"eigenvector"`, `"closeness"`
- **`base_node_size`** - Base node size (minimum size)
- **`node_size_multiplier`** - Node size multiplier (scaling factor)
- **`scaling_algorithm`** - Scaling algorithm: `"logarithmic"` or `"linear"`

### Edge Styling

```json
{
  "edge_thickness_metric": "weight",
  "base_edge_thickness": 1.0,
  "base_edge_width": 0.4,
  "edge_width_multiplier": 2.0,
  "edge_width_scaling": "logarithmic"
}
```

- **`edge_thickness_metric`** - Edge thickness metric: `"weight"` or `"betweenness"`
- **`base_edge_thickness`** - Base edge thickness
- **`base_edge_width`** - Base edge width
- **`edge_width_multiplier`** - Edge width multiplier
- **`edge_width_scaling`** - Edge width scaling: `"logarithmic"` or `"linear"`

### Colors

```json
{
  "intra_community_color": "#c0c0c0",
  "bridge_color": "#6e6e6e"
}
```

- **`intra_community_color`** - Color for edges within communities
- **`bridge_color`** - Color for edges between communities (bridges)

### Interactive HTML Visualization (Pyvis)

```json
{
  "pyvis_interactive": {
    "width": "100%",
    "height": "90vh",
    "bgcolor": "#ffffff",
    "font_color": "#000000",
    "notebook": false,
    "show_labels": true,
    "show_tooltips": true,
    "physics_solver": "forceAtlas2Based"
  }
}
```

- **`width`** - Canvas width
- **`height`** - Canvas height
- **`bgcolor`** - Background color
- **`font_color`** - Text color
- **`notebook`** - Jupyter notebook mode
- **`show_labels`** - Show node labels
- **`show_tooltips`** - Show hover tooltips
- **`physics_solver`** - Physics solver: `"forceAtlas2Based"`, `"barnesHut"`, `"repulsion"`

### Static PNG Image Configuration

```json
{
  "static_image": {
    "generate": true,
    "layout": "spring",
    "width": 2400,
    "height": 2400,
    "dpi": 300,
    "with_labels": false,
    "font_size": 8,
    "show_legend": true,
    "node_alpha": 0.9,
    "edge_alpha": 0.4,
    "edge_arrow_size": 8
  }
}
```

- **`generate`** - Generate PNG image
- **`layout`** - Layout algorithm: `"spring"`, `"circular"`, `"kamada_kawai"`, `"random"`
- **`width`** - Image width (pixels)
- **`height`** - Image height (pixels)
- **`dpi`** - Image resolution (dots per inch)
- **`with_labels`** - Show node labels
- **`font_size`** - Label font size
- **`show_legend`** - Show color legend
- **`node_alpha`** - Node transparency (0-1)
- **`edge_alpha`** - Edge transparency (0-1)
- **`edge_arrow_size`** - Size of directional arrows

## PNG Layout Configuration

### Spring Layout Physics

```json
{
  "spring": {
    "k": 0.8,
    "iterations": 300,
    "spring_length": 1.2,
    "spring_constant": 1.5,
    "repulsion_strength": 1.2,
    "attraction_strength": 0.8,
    "center_gravity": 0.02,
    "gravity_x": 0.0,
    "gravity_y": 0.0,
    "damping": 0.85,
    "min_velocity": 0.005,
    "max_displacement": 15.0,
    "enable_multistage": true,
    "initial_k_multiplier": 2.0,
    "final_k_multiplier": 0.7
  }
}
```

- **`k`** - Spring constant (node repulsion)
- **`iterations`** - Number of layout iterations
- **`spring_length`** - Natural length of springs (edges)
- **`spring_constant`** - Spring stiffness coefficient
- **`repulsion_strength`** - Node-to-node repulsion force
- **`attraction_strength`** - Edge attraction force
- **`center_gravity`** - Pull toward center (0=none, 1=strong)
- **`gravity_x`** - Horizontal gravity bias
- **`gravity_y`** - Vertical gravity bias
- **`damping`** - Velocity damping (0=none, 1=full)
- **`min_velocity`** - Stop when nodes move less than this
- **`max_displacement`** - Maximum node movement per iteration
- **`enable_multistage`** - Use 3-stage refinement process
- **`initial_k_multiplier`** - Stage 1: k multiplier for separation
- **`final_k_multiplier`** - Stage 3: k multiplier for fine-tuning

### Kamada-Kawai Layout

```json
{
  "kamada_kawai": {
    "max_iterations": 1500,
    "tolerance": 1e-7,
    "distance_scale": 1.2,
    "spring_strength": 1.5,
    "pos_tolerance": 1e-5,
    "weight_function": "path"
  }
}
```

- **`max_iterations`** - Maximum iterations
- **`tolerance`** - Convergence tolerance
- **`distance_scale`** - Scale factor for ideal distances
- **`spring_strength`** - Spring strength coefficient
- **`pos_tolerance`** - Position change tolerance
- **`weight_function`** - Weight function: `"path"`, `"weight"`, or `"uniform"`

### Circular Layout

```json
{
  "circular": {
    "radius": null,
    "center": null,
    "start_angle": 0.0,
    "angular_spacing": "uniform",
    "group_by_community": true,
    "community_separation": 0.3
  }
}
```

- **`radius`** - Circle radius (`null` = auto)
- **`center`** - Center position (`null` = origin)
- **`start_angle`** - Starting angle in radians
- **`angular_spacing`** - Angular spacing: `"uniform"`, `"degree"`, or `"weight"`
- **`group_by_community`** - Group communities together
- **`community_separation`** - Angular gap between communities

### Shell Layout

```json
{
  "shell": {
    "shell_spacing": 1.5,
    "center_shell_radius": 0.3,
    "arrange_by_community": true,
    "arrange_by_centrality": false,
    "centrality_metric": "degree",
    "max_shells": 8,
    "nodes_per_shell": null
  }
}
```

- **`shell_spacing`** - Distance between shells
- **`center_shell_radius`** - Radius of innermost shell
- **`arrange_by_community`** - Put communities in different shells
- **`arrange_by_centrality`** - Arrange by node importance
- **`centrality_metric`** - Centrality metric: `"degree"`, `"betweenness"`, `"eigenvector"`
- **`max_shells`** - Maximum number of shells
- **`nodes_per_shell`** - Max nodes per shell (`null` = auto)

### Performance Settings

```json
{
  "performance": {
    "fast_mode": false,
    "skip_path_analysis": false,
    "max_layout_iterations": null,
    "use_sampling_threshold": 5000
  }
}
```

- **`fast_mode`** - Enable fast mode optimizations
- **`skip_path_analysis`** - Skip path analysis for better performance
- **`max_layout_iterations`** - Maximum layout iterations (`null` = unlimited)
- **`use_sampling_threshold`** - Use sampling for networks larger than threshold

### Output Configuration

```json
{
  "output": {
    "custom_output_directory": null,
    "enable_time_logging": true
  }
}
```

- **`custom_output_directory`** - Custom output directory (`null` = use `output_file_prefix` directory)
- **`enable_time_logging`** - Enable detailed timing logs

**Note:** Directory creation is automatically handled and does not need to be configured.

## Configuration Examples

### Quick Start Configuration (Instagram)

For basic Instagram analysis with minimal settings:

```json
{
  "input_file": "your_data.json",
  "data_source": {
    "source": "instagram"
  },
  "pipeline": {
    "strategy": "k-core"
  },
  "k_values": {
    "strategy_k_values": {
      "k-core": 1
    }
  }
}
```

### Freesound Audio Sample Network

For analyzing audio sample relationships from Freesound:

```json
{
  "input_file": null,
  "output_file_prefix": "Output/Freesound",
  "data_source": {
    "source": "freesound",
    "freesound": {
      "api_key": "${FREESOUND_API_KEY}",
      "query": "ambient",
      "tags": ["pad", "synth"],
      "max_samples": 300,
      "include_similar": true
    }
  },
  "renderer": {
    "renderer_type": "sigma",
    "sigma_interactive": {
      "enable_webgl": true,
      "enable_audio_player": true
    }
  },
  "checkpoint": {
    "checkpoint_dir": "checkpoints/freesound",
    "checkpoint_interval": 50,
    "max_runtime_hours": 1.0
  }
}
```

### Incremental Graph Building with Time Limits

For building large graphs over multiple sessions:

```json
{
  "data_source": {
    "source": "freesound",
    "freesound": {
      "api_key": "${FREESOUND_API_KEY}",
      "query": "techno",
      "max_samples": 5000
    }
  },
  "checkpoint": {
    "checkpoint_dir": "checkpoints/techno_network",
    "checkpoint_interval": 100,
    "max_runtime_hours": 2.0,
    "verify_existing_sounds": true,
    "verification_age_days": 7
  }
}
```

### Flexible Metadata Updates

For updating existing graph metadata without rebuilding:

```json
{
  "checkpoint": {
    "checkpoint_dir": "checkpoints/existing_graph",
    "verify_existing_sounds": true,
    "verification_age_days": 30,
    "metadata_update_mode": "merge"
  }
}
```

### High-Quality Visualization

For publication-ready visualizations:

```json
{
  "visualization": {
    "static_image": {
      "width": 3600,
      "height": 3600,
      "dpi": 300,
      "show_legend": true
    }
  }
}
```

### Performance Optimization

For large networks:

```json
{
  "analysis_mode": {
    "mode": "fast",
    "sampling_threshold": 2000
  },
  "visualization": {
    "performance": {
      "fast_mode": true,
      "max_layout_iterations": 50
    }
  }
}
```

## Best Practices

1. **Start Simple** - Begin with minimal configuration and add options as needed
2. **Test Performance** - Use fast mode for initial testing, then switch to full mode for final results
3. **Backup Configs** - Keep working configurations as templates for future use
4. **Document Changes** - Note any custom modifications for reproducibility
5. **Validate Settings** - Use the configuration validation features to catch errors early
6. **Environment Variables** - Use `"${VAR_NAME}"` syntax for sensitive data like API keys
7. **Checkpoint Strategy** - For large Freesound graphs, use checkpoints with time limits to build incrementally
8. **Metadata Flexibility** - Use `"merge"` mode for metadata updates to preserve custom fields
9. **Audio Player** - Enable audio player only for Freesound data sources with Sigma.js renderer
10. **Verification Schedule** - Set `verification_age_days` based on how often you expect samples to be deleted

## Freesound-Specific Notes

### API Key Setup

Set your Freesound API key as an environment variable:

```bash
# Windows (PowerShell)
$env:FREESOUND_API_KEY="your_api_key_here"

# Windows (CMD)
set FREESOUND_API_KEY=your_api_key_here

# Linux/Mac
export FREESOUND_API_KEY="your_api_key_here"
```

Then use `"${FREESOUND_API_KEY}"` in your configuration file.

### Checkpoint Recovery

If your graph building is interrupted:

1. Keep the same `checkpoint_dir` in your configuration
2. Run the pipeline again - it will automatically resume from the last checkpoint
3. Adjust `max_runtime_hours` if needed for your schedule

### Sample Selection Strategy

- **Broad Query**: Use general terms like `"ambient"` or `"drum"` for diverse networks
- **Tag Filtering**: Add specific tags to focus on particular sound types
- **Max Samples**: Start with 100-500 samples for testing, increase for production
- **Similar Sounds**: Always enable `include_similar: true` for meaningful graph edges

### Performance Tuning

- **Small Networks** (< 500 samples): Use `checkpoint_interval: 50`, no time limit
- **Medium Networks** (500-2000 samples): Use `checkpoint_interval: 100`, `max_runtime_hours: 2`
- **Large Networks** (> 2000 samples): Use `checkpoint_interval: 200`, `max_runtime_hours: 4`, run multiple sessions