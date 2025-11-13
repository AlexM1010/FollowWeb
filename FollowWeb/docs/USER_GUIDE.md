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

3. **Install Freesound Support (Optional)**
   ```bash
   # Install Freesound API client and additional dependencies
   pip install freesound-python joblib Jinja2
   ```

4. **Verify Installation**
   ```bash
   python -c "from FollowWeb_Visualizor.main import PipelineOrchestrator; print('Installation successful!')"
   
   # Test the module entry point
   followweb --print-default-config
   
   # Verify Freesound support
   python -c "from FollowWeb_Visualizor.data.loaders.freesound import FreesoundLoader; print('Freesound support available!')"
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

## Data Sources

FollowWeb supports multiple data sources for network analysis:

1. **Instagram Networks**: Social follower/following relationships
2. **Freesound Audio Networks**: Audio sample similarity relationships with playback

### Choosing a Data Source

- **Instagram**: Best for social network analysis, influence mapping, community detection
- **Freesound**: Best for audio sample exploration, music research, sound design workflows

## Data Preparation

### Instagram Data Format

FollowWeb expects Instagram JSON data with the following structure:

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

Before analysis, validate your Instagram data:

```python
from FollowWeb_Visualizor.data.loaders import InstagramLoader

loader = InstagramLoader()
try:
    graph = loader.load(filepath='your_data.json')
    print(f"Successfully loaded {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
except Exception as e:
    print(f"Data validation failed: {e}")
```

### Freesound Data Source

#### Freesound API Setup

1. **Create a Freesound Account**
   - Visit [https://freesound.org/](https://freesound.org/)
   - Sign up for a free account

2. **Get Your API Key**
   - Go to [https://freesound.org/apiv2/apply](https://freesound.org/apiv2/apply)
   - Fill out the API application form
   - You'll receive an API key immediately

3. **Set Up Authentication**

   **Option 1: Environment Variable (Recommended)**
   ```bash
   # Linux/Mac
   export FREESOUND_API_KEY="your_api_key_here"
   
   # Windows (Command Prompt)
   set FREESOUND_API_KEY=your_api_key_here
   
   # Windows (PowerShell)
   $env:FREESOUND_API_KEY="your_api_key_here"
   ```

   **Option 2: Configuration File**
   ```json
   {
     "data_source": {
       "type": "freesound",
       "freesound": {
         "api_key": "your_api_key_here"
       }
     }
   }
   ```

#### Freesound Data Collection

The FreesoundLoader fetches audio sample data from the Freesound API:

```python
from FollowWeb_Visualizor.data.loaders.freesound import FreesoundLoader

# Configure loader
config = {
    'api_key': 'your_api_key_here',  # Or use FREESOUND_API_KEY env var
    'checkpoint_dir': './checkpoints/freesound',
    'checkpoint_interval': 100,
    'max_runtime_hours': 2.0
}

# Create loader
loader = FreesoundLoader(config)

# Fetch data and build graph
graph = loader.load(
    query='jungle',           # Search query
    tags=['drum', 'loop'],    # Filter by tags (optional)
    max_samples=1000,         # Maximum samples to fetch
    include_similar=True      # Include similarity relationships
)

print(f"Loaded {graph.number_of_nodes()} audio samples")
print(f"Found {graph.number_of_edges()} similarity relationships")
```

#### Incremental Graph Building

For large audio networks, use incremental building with checkpoints:

```python
from FollowWeb_Visualizor.data.loaders.freesound import IncrementalFreesoundLoader

# Configure incremental loader
config = {
    'api_key': 'your_api_key_here',
    'checkpoint_dir': './checkpoints/freesound',
    'checkpoint_interval': 100,        # Save every 100 samples
    'max_runtime_hours': 2.0,          # Stop after 2 hours
    'verify_existing_sounds': True,    # Check for deleted samples
    'verification_age_days': 7         # Verify samples older than 7 days
}

loader = IncrementalFreesoundLoader(config)

# Build graph incrementally (resumes from checkpoint if exists)
graph = loader.build_graph()

# Run again to continue building
graph = loader.build_graph()  # Picks up where it left off
```

**Key Features:**
- **Crash Recovery**: Automatically resumes from last checkpoint after interruption
- **Time-Limited Execution**: Perfect for nightly scheduled jobs
- **Deleted Sample Cleanup**: Removes samples that no longer exist on Freesound
- **Progress Tracking**: Detailed logging of processing progress and ETA

#### Freesound Graph Structure

Freesound graphs have the following structure:

**Nodes (Audio Samples):**
- `id`: Freesound sample ID
- `name`: Sample name/title
- `tags`: List of tags describing the sound
- `duration`: Length in seconds
- `user`: Username of uploader
- `audio_url`: High-quality MP3 preview URL for playback
- `type`: Always 'sample'

**Edges (Relationships):**
- `type`: 'similar' (acoustically similar sounds)
- `weight`: Similarity score (0.0-1.0)

**Example:**
```python
# Access node attributes
for node_id in graph.nodes():
    node_data = graph.nodes[node_id]
    print(f"Sample: {node_data['name']}")
    print(f"Tags: {', '.join(node_data['tags'])}")
    print(f"Duration: {node_data['duration']}s")
    print(f"Audio URL: {node_data['audio_url']}")

# Access edge attributes
for source, target in graph.edges():
    edge_data = graph.edges[source, target]
    print(f"Similarity: {edge_data['weight']:.2f}")
```

#### Freesound API Rate Limits

The Freesound API has rate limits:
- **60 requests per minute** for standard API keys
- **Automatic rate limiting** built into FreesoundLoader
- **Response caching** to minimize redundant requests

The loader automatically handles rate limiting with exponential backoff.

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

#### Data Source Settings

- **`data_source.type`**: Data source type
  - `'instagram'`: Instagram follower/following networks
  - `'freesound'`: Freesound audio sample networks

- **`data_source.freesound`**: Freesound-specific settings
  - `api_key`: Freesound API key (or use FREESOUND_API_KEY env var)
  - `query`: Search query for audio samples
  - `tags`: List of tags to filter by
  - `max_samples`: Maximum number of samples to fetch
  - `checkpoint_dir`: Directory for checkpoint files
  - `checkpoint_interval`: Save checkpoint every N samples
  - `max_runtime_hours`: Maximum runtime before stopping gracefully
  - `verify_existing_sounds`: Check for deleted samples
  - `verification_age_days`: Verify samples older than N days

#### Renderer Settings

- **`renderer_type`**: Visualization engine
  - `'pyvis'`: Interactive HTML with physics simulation
  - `'sigma'`: High-performance WebGL visualization
  - `'all'`: Generate both Pyvis and Sigma outputs

- **`sigma_interactive`**: Sigma.js-specific settings
  - `enable_webgl`: Use WebGL rendering (default: true)
  - `enable_search`: Enable node search functionality
  - `audio_player.enabled`: Enable audio playback for Freesound
  - `audio_player.show_controls`: Show audio player controls
  - `audio_player.enable_loop`: Enable loop toggle button

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

FollowWeb supports multiple visualization engines optimized for different use cases:

### Sigma.js Renderer (High-Performance)

**Best for**: Large networks (10,000+ nodes), Freesound audio networks, modern browsers

The Sigma.js renderer uses WebGL for high-performance visualization:

```python
from FollowWeb_Visualizor.visualization.renderers.sigma import SigmaRenderer

config = {
    'node_size_metric': 'degree',
    'base_node_size': 10.0,
    'audio_player': {
        'enabled': True,
        'show_controls': True,
        'enable_loop': True
    }
}

renderer = SigmaRenderer(config)
renderer.generate_visualization(graph, 'output.html')
```

**Features:**
- **WebGL Acceleration**: Smooth rendering of 10,000+ nodes
- **Audio Playback**: Click nodes to play Freesound audio samples
- **Interactive Controls**: Zoom, pan, search by label/tags
- **Hover Tooltips**: Display node metadata on hover
- **Audio Player Panel**: Play/pause, loop, timeline scrubber, time display
- **Visual Highlighting**: Currently playing node highlighted

**Audio Playback (Freesound Networks):**
- Click any node to play its audio sample
- Audio player appears in bottom-right corner
- Controls: Play, Pause, Loop toggle, Timeline scrubber
- Currently playing node highlighted in distinct color
- Automatic audio loading with error handling

### Pyvis Renderer (Interactive HTML)

**Best for**: Small to medium networks (< 5,000 nodes), Instagram networks

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

## Freesound Audio Network Analysis

### Complete Freesound Workflow

Here's a complete example of analyzing Freesound audio samples:

```python
from FollowWeb_Visualizor.main import PipelineOrchestrator
from FollowWeb_Visualizor.core.config import get_configuration_manager

# Configure Freesound analysis
config_dict = {
    'data_source': {
        'type': 'freesound',
        'freesound': {
            'api_key': 'your_api_key_here',  # Or use FREESOUND_API_KEY env var
            'query': 'jungle drum',
            'tags': ['loop', 'percussion'],
            'max_samples': 500,
            'checkpoint_dir': './checkpoints/jungle_drums',
            'checkpoint_interval': 50,
            'max_runtime_hours': 1.0
        }
    },
    'renderer_type': 'sigma',
    'sigma_interactive': {
        'enable_webgl': True,
        'enable_search': True,
        'audio_player': {
            'enabled': True,
            'show_controls': True,
            'enable_loop': True
        }
    },
    'strategy': 'k-core',
    'k_values': {
        'strategy_k_values': {
            'k-core': 3
        }
    },
    'output_file_prefix': 'JungleDrums'
}

# Load and validate configuration
config_manager = get_configuration_manager()
config = config_manager.load_configuration(config_dict=config_dict)

# Execute pipeline
orchestrator = PipelineOrchestrator(config)
success = orchestrator.execute_pipeline()

if success:
    print("Analysis complete! Open the HTML file to explore the audio network.")
    print("Click on nodes to play audio samples.")
```

### Freesound Use Cases

#### 1. Sound Design Exploration

Find related sounds for music production:

```python
config_dict = {
    'data_source': {
        'type': 'freesound',
        'freesound': {
            'query': 'ambient pad',
            'tags': ['synthesizer', 'atmospheric'],
            'max_samples': 300
        }
    },
    'renderer_type': 'sigma',
    'strategy': 'k-core',
    'k_values': {'strategy_k_values': {'k-core': 2}}
}
```

#### 2. Sample Pack Analysis

Analyze relationships within a sample pack:

```python
config_dict = {
    'data_source': {
        'type': 'freesound',
        'freesound': {
            'query': 'pack:12345',  # Specific pack ID
            'max_samples': 200
        }
    },
    'renderer_type': 'sigma'
}
```

#### 3. Genre Exploration

Explore a music genre's sound palette:

```python
config_dict = {
    'data_source': {
        'type': 'freesound',
        'freesound': {
            'query': 'techno',
            'tags': ['kick', 'bass', 'synth'],
            'max_samples': 1000
        }
    },
    'renderer_type': 'sigma',
    'strategy': 'k-core',
    'k_values': {'strategy_k_values': {'k-core': 5}}
}
```

#### 4. Incremental Large Network Building

Build a large audio network over multiple sessions:

```python
from FollowWeb_Visualizor.data.loaders.freesound import IncrementalFreesoundLoader

config = {
    'api_key': 'your_api_key_here',
    'checkpoint_dir': './checkpoints/large_network',
    'checkpoint_interval': 100,
    'max_runtime_hours': 2.0,  # Run for 2 hours, then stop
    'verify_existing_sounds': True
}

loader = IncrementalFreesoundLoader(config)

# Day 1: Build for 2 hours
graph = loader.build_graph()
print(f"Day 1: {graph.number_of_nodes()} nodes")

# Day 2: Continue building for another 2 hours
graph = loader.build_graph()
print(f"Day 2: {graph.number_of_nodes()} nodes")

# Day 3: Continue building
graph = loader.build_graph()
print(f"Day 3: {graph.number_of_nodes()} nodes")
```

## Advanced Usage

### Custom Analysis Workflows

For more control, use individual components:

```python
from FollowWeb_Visualizor.data.loaders import InstagramLoader
from FollowWeb_Visualizor.analysis.network import NetworkAnalyzer
from FollowWeb_Visualizor.visualization.metrics import MetricsCalculator
from FollowWeb_Visualizor.visualization.renderers import PyvisRenderer

# Load and analyze
loader = InstagramLoader()
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

renderer = PyvisRenderer(vis_config)
renderer.generate_visualization(graph, 'custom_output.html')
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
    'pipeline': {
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
from FollowWeb_Visualizor.data.loaders import InstagramLoader
import networkx as nx

# Load graph
loader = InstagramLoader()
graph = loader.load_from_json('data.json')

# Export to various formats
nx.write_gexf(graph, 'network.gexf')  # For Gephi
nx.write_graphml(graph, 'network.graphml')  # For Cytoscape
nx.write_edgelist(graph, 'network.txt')  # Simple edge list
```

## Troubleshooting

### Common Issues and Solutions

#### Freesound-Specific Issues

##### 1. "Invalid API key" Error

**Problem**: Freesound API key is missing or invalid
**Solution**: 
```python
import os

# Check if API key is set
api_key = os.getenv('FREESOUND_API_KEY')
if not api_key:
    print("FREESOUND_API_KEY environment variable not set")
else:
    print(f"API key found: {api_key[:10]}...")

# Test API connection
from FollowWeb_Visualizor.data.loaders.freesound import FreesoundLoader
loader = FreesoundLoader({'api_key': api_key})
# If no error, API key is valid
```

##### 2. "Rate limit exceeded" Error

**Problem**: Too many API requests in short time
**Solution**: The loader automatically handles rate limiting, but you can adjust:
```python
config = {
    'api_key': 'your_key',
    'checkpoint_interval': 50,  # Save more frequently
    'max_runtime_hours': 0.5    # Shorter sessions
}
```

##### 3. "No audio samples found" Warning

**Problem**: Search query returned no results
**Solution**: 
- Broaden your search query
- Remove restrictive tags
- Check Freesound.org to verify samples exist

```python
# Too restrictive
config = {'query': 'very specific rare sound', 'tags': ['tag1', 'tag2', 'tag3']}

# Better
config = {'query': 'drum', 'tags': ['loop']}
```

##### 4. "Checkpoint corrupted" Error

**Problem**: Checkpoint file was corrupted during save
**Solution**: 
```python
from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint

checkpoint = GraphCheckpoint('./checkpoints/freesound')
checkpoint.clear()  # Delete corrupted checkpoint and start fresh
```

##### 5. Audio Playback Not Working

**Problem**: Audio doesn't play when clicking nodes
**Solution**:
- Ensure you're using Sigma.js renderer (not Pyvis)
- Check that audio_player is enabled in configuration
- Verify nodes have `audio_url` attribute
- Check browser console for errors
- Try a different browser (Chrome/Firefox recommended)

```python
# Verify audio URLs in graph
for node_id in list(graph.nodes())[:5]:
    node_data = graph.nodes[node_id]
    print(f"Node {node_id}: {node_data.get('audio_url', 'NO URL')}")
```

##### 6. Slow Freesound Data Collection

**Problem**: Data collection takes too long
**Solution**:
- Reduce `max_samples` parameter
- Use incremental building with `max_runtime_hours`
- Increase `checkpoint_interval` to save less frequently
- Skip deleted sample verification

```python
# Fast configuration
config = {
    'max_samples': 200,
    'checkpoint_interval': 200,
    'verify_existing_sounds': False
}
```

#### General Issues

##### 1. "File not found" Error

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
    'pipeline': {
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