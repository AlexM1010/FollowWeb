# User Guide

Guide to using FollowWeb for social network analysis and visualization.

## Getting Started

### Installation

1. **Install Dependencies**
   ```bash
   # Install production dependencies
   pip install -r requirements.txt
   
   # Install package in development mode
   pip install -e .
   ```

2. **Alternative Installation (using pyproject.toml)**
   ```bash
   # Install with all dependencies
   pip install -e ".[dev]"
   ```

3. **Verify Installation**
   ```bash
   python -c "from FollowWeb_Visualizor.main import PipelineOrchestrator; print('Installation successful!')"
   
   # Test the module entry point
   followweb --print-default-config
   ```

### Quick Start

The simplest way to get started is with the default configuration:

```python
from FollowWeb_Visualizor.main import PipelineOrchestrator
from FollowWeb_Visualizor.core.config import get_configuration_manager

# Create configuration dictionary
config_dict = {
    'input_file': 'path/to/your/followers_following.json'
}

# Load and validate configuration
config_manager = get_configuration_manager()
config = config_manager.load_configuration(config_dict=config_dict)

# Run analysis
orchestrator = PipelineOrchestrator(config)
success = orchestrator.execute_pipeline()
```

## Data Preparation

### Required Data Format

FollowWeb expects JSON data with the following structure:

```json
[
  {
    "user": "alice",
    "followers": ["bob", "charlie", "diana"],
    "following": ["bob", "eve", "frank"]
  },
  {
    "user": "bob", 
    "followers": ["alice", "charlie"],
    "following": ["alice", "diana"]
  }
]
```

### Data Collection Tips

1. **Instagram Data**: If collecting from Instagram, ensure you comply with their terms of service
2. **Privacy**: Only include public account data or data you have permission to analyze
3. **Data Quality**: Remove inactive accounts and ensure usernames are consistent
4. **Size Considerations**: 
   - Small networks (< 1,000 users): Process quickly
   - Medium networks (1,000-10,000 users): May take several minutes
   - Large networks (> 10,000 users): Consider using higher k-values for pruning

### Data Validation

Before analysis, validate your data:

```python
from FollowWeb_Visualizor.data.loaders import GraphLoader

loader = GraphLoader()
try:
    graph = loader.load_from_json('your_data.json')
    print(f"Successfully loaded {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
except Exception as e:
    print(f"Data validation failed: {e}")
```

## Configuration Guide

### Basic Configuration

The configuration system uses a nested dictionary structure:

```python
config_dict = {
    'input_file': 'followers_following.json',
    'output_file_prefix': 'MyNetwork',
    'strategy': 'k-core',
    'ego_username': None,
    'contact_path_target': None,
    'min_followers_in_network': 50,
    'min_fame_ratio': 2.0,
    'find_paths_to_all_famous': True,
    'k_values': {
        'strategy_k_values': {
            'k-core': 5,
            'reciprocal_k-core': 3,
            'ego_alter_k-core': 2
        }
    },
    'visualization': {
        'node_size_metric': 'degree',
        'base_node_size': 10.0,
        'scaling_algorithm': 'logarithmic'
    },
    'output_control': {
        'generate_html': True,
        'generate_png': True,
        'generate_reports': True
    }
}
```

### Configuration Options Explained

#### Core Settings

- **`strategy`**: Analysis approach
  - `'k-core'`: Full network analysis
  - `'reciprocal_k-core'`: Mutual connections only
  - `'ego_alter_k-core'`: Personal network analysis

- **`ego_username`**: Required for ego-alter analysis
- **`min_followers_in_network`**: Threshold for identifying "famous" accounts
- **`min_fame_ratio`**: Minimum follower-to-following ratio for fame analysis
- **`find_paths_to_all_famous`**: Calculate paths to influential accounts
- **`contact_path_target`**: Find path to specific user

#### K-Values Configuration

- **`k_values.strategy_k_values`**: Minimum connections required for each strategy
  - Higher values = smaller, denser networks
  - Lower values = larger, sparser networks

#### Visualization Settings

- **`visualization.node_size_metric`**: What determines node size
  - `'degree'`: Total connections
  - `'in_degree'`: Followers only
  - `'out_degree'`: Following only
  - `'betweenness'`: Bridge importance
  - `'eigenvector'`: Influence score

- **`visualization.scaling_algorithm`**: How to scale node sizes
  - `'logarithmic'`: Better for networks with high variance
  - `'linear'`: Direct proportional scaling

#### Output Control

- **`output_control.generate_html`**: Generate interactive HTML visualization
- **`output_control.generate_png`**: Generate static PNG image
- **`output_control.generate_reports`**: Generate text metrics report

## Analysis Strategies

### 1. K-Core Analysis

**Best for**: Understanding the overall network structure and identifying core communities.

```python
config_dict = {
    'strategy': 'k-core',
    'k_values': {
        'strategy_k_values': {
            'k-core': 5  # Users with 5+ connections
        }
    }
}
```

**Use cases**:
- Identifying the most connected users
- Finding dense subgroups
- Understanding network hierarchy

**Example output**: A network showing users who have at least 5 connections, revealing the most active participants.

### 2. Reciprocal K-Core Analysis

**Best for**: Analyzing mutual relationships and close friendships.

```python
config_dict = {
    'strategy': 'reciprocal_k-core',
    'k_values': {
        'strategy_k_values': {
            'reciprocal_k-core': 3  # 3+ mutual connections
        }
    }
}
```

**Use cases**:
- Finding close friend groups
- Identifying mutual influence patterns
- Analyzing bidirectional relationships

**Example output**: A network of users who mutually follow each other, showing genuine social connections.

### 3. Ego-Alter Analysis

**Best for**: Understanding one person's social network and their influence patterns.

```python
config_dict = {
    'strategy': 'ego_alter_k-core',
    'ego_username': 'target_user',
    'k_values': {
        'strategy_k_values': {
            'ego_alter_k-core': 2
        }
    }
}
```

**Use cases**:
- Personal network analysis
- Influence mapping for specific individuals
- Understanding social circles around key figures

**Example output**: A network centered on the target user, showing their followers, who they follow, and connections between those people.

## Visualization Options

### Interactive HTML Visualizations

HTML outputs provide interactive exploration:

- **Hover tooltips**: Show user details and metrics
- **Drag and zoom**: Explore network structure
- **Physics simulation**: Nodes arrange naturally
- **Community colors**: Different colors for detected groups

### Static PNG Images

PNG outputs provide publication-ready graphics:

- **High resolution**: Suitable for presentations and papers
- **Fixed layout**: Consistent positioning across runs
- **Legend included**: Color coding explanation
- **Professional appearance**: Clean, academic style

### Customizing Visualizations

#### Node Appearance

```python
config_dict = {
    'visualization': {
        'base_node_size': 20.0,
        'node_size_metric': 'betweenness',
        'scaling_algorithm': 'linear'
    }
}
```

#### Output Control

```python
config_dict = {
    'output_control': {
        'generate_html': True,
        'generate_png': False,
        'generate_reports': True
    }
}
```

## Output Interpretation

### File Naming Convention

Output files follow this pattern:
```
{prefix}-{strategy}-k{k_value}-{hash}.{extension}
```

Example:
```
MyNetwork-reciprocal_k-core-k3-a1b2c3.html
MyNetwork-reciprocal_k-core-k3-a1b2c3.png
MyNetwork-reciprocal_k-core-k3-a1b2c3.txt
```

### Understanding the Visualizations

#### Node Properties

- **Size**: Represents the chosen metric (degree, betweenness, etc.)
- **Color**: Indicates community membership
- **Position**: Determined by network structure and connections

#### Edge Properties

- **Thickness**: May represent connection strength or frequency
- **Color**: Often indicates community relationships
- **Direction**: Shows follower relationships (A → B means A follows B)

#### Community Detection

Communities are groups of densely connected users:

- **Same color nodes**: Belong to the same community
- **Bridge nodes**: Connect different communities (high betweenness)
- **Isolated groups**: Separate clusters with few external connections

### Metrics Report Interpretation

The text file contains detailed statistics:

```
=== NETWORK ANALYSIS REPORT ===
Strategy: reciprocal_k-core
K-value: 3
Execution Time: 45.2 seconds

=== GRAPH STATISTICS ===
Nodes: 1,247
Edges: 3,891
Density: 0.0050
Average Degree: 6.24

=== COMMUNITY ANALYSIS ===
Number of Communities: 12
Modularity Score: 0.73
Largest Community: 234 nodes (18.8%)

=== CENTRALITY METRICS ===
Highest Degree: user123 (degree: 89)
Highest Betweenness: user456 (betweenness: 0.12)
Highest Eigenvector: user789 (eigenvector: 0.34)
```

## Advanced Usage

### Custom Analysis Workflows

For more control, use individual components:

```python
from FollowWeb_Visualizor.data.loaders import GraphLoader
from FollowWeb_Visualizor.analysis.network import NetworkAnalyzer
from FollowWeb_Visualizor.visualization.metrics import MetricsCalculator
from FollowWeb_Visualizor.visualization.renderers import InteractiveRenderer

# Load and analyze
loader = GraphLoader()
graph = loader.load_from_json('data.json')

analyzer = NetworkAnalyzer()
graph = analyzer.detect_communities(graph)
graph = analyzer.calculate_centrality_metrics(graph)

# Custom visualization
vis_config = {
    'node_size_metric': 'eigenvector',
    'base_node_size': 25.0,
    'scaling_algorithm': 'linear'
}

calculator = MetricsCalculator(vis_config)
node_metrics = calculator.calculate_node_metrics(graph)

renderer = InteractiveRenderer(vis_config)
renderer.generate_html(graph, 'custom_output.html', node_metrics, {})
```

### Batch Processing

Process multiple datasets:

```python
import os
from FollowWeb_Visualizor.main import PipelineOrchestrator
from FollowWeb_Visualizor.core.config import get_configuration_manager

data_files = ['network1.json', 'network2.json', 'network3.json']
config_manager = get_configuration_manager()

for data_file in data_files:
    if os.path.exists(data_file):
        config_dict = {
            'input_file': data_file,
            'output_file_prefix': f'Analysis_{os.path.splitext(data_file)[0]}'
        }
        
        config = config_manager.load_configuration(config_dict=config_dict)
        orchestrator = PipelineOrchestrator(config)
        success = orchestrator.execute_pipeline()
        
        print(f"Processed {data_file}: {'Success' if success else 'Failed'}")
```

### Performance Optimization

FollowWeb includes a centralized caching system that automatically optimizes performance by:
- **Graph Hash Caching**: Eliminates 90% of duplicate hash calculations
- **Graph Conversion Caching**: Reduces undirected graph conversion overhead by 95%
- **Attribute Access Caching**: Reduces graph traversal time by 80%
- **Layout Position Caching**: Shares layout calculations between HTML and PNG outputs
- **Community Color Caching**: Avoids regenerating color schemes (99% reduction)

For large networks, additional optimizations:

```python
# Use higher k-values to reduce network size
config_dict = {
    'k_values': {
        'strategy_k_values': {
            'k-core': 10
        }
    },
    'find_paths_to_all_famous': False,
    'output_control': {
        'generate_png': False
    },
    'pipeline_stages': {
        'enable_analysis': False  # Skip detailed analysis
    }
}
```

The caching system automatically manages memory usage with:
- **Size Limits**: 50 items per cache category by default
- **Timeout Management**: 1-hour default timeout for cache entries
- **Automatic Cleanup**: Prevents memory leaks with weak references

### Integration with Other Tools

Export data for external analysis:

```python
from FollowWeb_Visualizor.data.loaders import GraphLoader
import networkx as nx

# Load graph
loader = GraphLoader()
graph = loader.load_from_json('data.json')

# Export to various formats
nx.write_gexf(graph, 'network.gexf')  # For Gephi
nx.write_graphml(graph, 'network.graphml')  # For Cytoscape
nx.write_edgelist(graph, 'network.txt')  # Simple edge list
```

## Troubleshooting

### Common Issues and Solutions

#### 1. "File not found" Error

**Problem**: Input file path is incorrect
**Solution**: 
```python
import os
print(f"Current directory: {os.getcwd()}")
print(f"File exists: {os.path.exists('your_file.json')}")
```

#### 2. "Invalid JSON format" Error

**Problem**: JSON file is malformed
**Solution**: Validate JSON structure
```python
import json
with open('your_file.json', 'r') as f:
    try:
        data = json.load(f)
        print("JSON is valid")
    except json.JSONDecodeError as e:
        print(f"JSON error at line {e.lineno}: {e.msg}")
```

#### 3. "Empty graph after pruning" Warning

**Problem**: K-value is too high, removing all nodes
**Solution**: Reduce k-value or check data quality
```python
# Try lower k-values
config_dict = {
    'k_values': {
        'strategy_k_values': {
            'k-core': 1
        }
    }
}
```

#### 4. Memory Issues with Large Networks

**Problem**: Running out of memory
**Solutions**:
- Increase k-values to reduce network size
- Skip expensive analysis steps
- Process in smaller chunks

```python
# Memory-efficient configuration
config_dict = {
    'k_values': {
        'strategy_k_values': {
            'k-core': 8  # Higher pruning
        }
    },
    'find_paths_to_all_famous': False,  # Skip path analysis
    'pipeline_stages': {
        'enable_analysis': False  # Skip detailed analysis
    }
}
```

#### 5. Slow Performance

**Problem**: Analysis takes too long
**Solutions**:
- Use reciprocal strategy for smaller networks
- Increase k-values
- Disable PNG generation
- Skip path analysis

```python
# Performance-optimized configuration
config_dict = {
    'strategy': 'reciprocal_k-core',
    'k_values': {
        'strategy_k_values': {
            'reciprocal_k-core': 5
        }
    },
    'find_paths_to_all_famous': False,
    'output_control': {
        'generate_png': False
    }
}
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Run analysis with debug output
orchestrator = PipelineOrchestrator(config)
orchestrator.execute_pipeline()
```

### Performance Benchmarks

Typical performance on a modern laptop:

| Network Size | Strategy | K-value | Processing Time |
|-------------|----------|---------|----------------|
| 500 nodes | k-core | 3 | 5-10 seconds |
| 2,000 nodes | k-core | 5 | 30-60 seconds |
| 5,000 nodes | reciprocal_k-core | 3 | 1-2 minutes |
| 10,000 nodes | k-core | 8 | 3-5 minutes |

### Best Practices

1. **Start with small datasets** to understand the output format
2. **Use reciprocal analysis** for friendship networks
3. **Use ego-alter analysis** for individual influence studies
4. **Adjust k-values** based on network density
5. **Generate metrics files** for detailed analysis
6. **Save configurations** for reproducible analysis
7. **Validate data quality** before large-scale processing

### Getting Help

1. **Check the logs**: Error messages usually indicate the problem
2. **Validate your data**: Ensure JSON format is correct
3. **Start simple**: Use default configuration first
4. **Check file paths**: Ensure all paths are correct and accessible
5. **Monitor resources**: Watch memory and CPU usage for large networks