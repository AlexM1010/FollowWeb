# Freesound Quick Start Guide

Get started with Freesound audio network analysis in 5 minutes.

## Prerequisites

1. **Install FollowWeb**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

2. **Install Freesound dependencies**:
   ```bash
   pip install freesound-python joblib Jinja2
   ```

3. **Get Freesound API Key**:
   - Visit [https://freesound.org/apiv2/apply](https://freesound.org/apiv2/apply)
   - Fill out the form and get your API key immediately

4. **Set API Key**:
   ```bash
   export FREESOUND_API_KEY="your_api_key_here"
   ```

## Quick Examples

### Example 1: Simple Audio Network (5 minutes)

```python
from FollowWeb_Visualizor.main import PipelineOrchestrator
from FollowWeb_Visualizor.core.config import get_configuration_manager

# Configure analysis
config_dict = {
    'data_source': {
        'type': 'freesound',
        'freesound': {
            'query': 'drum loop',
            'max_samples': 100
        }
    },
    'renderer_type': 'sigma',
    'output_file_prefix': 'DrumLoops'
}

# Run analysis
config_manager = get_configuration_manager()
config = config_manager.load_configuration(config_dict=config_dict)
orchestrator = PipelineOrchestrator(config)
success = orchestrator.execute_pipeline()

if success:
    print("✓ Done! Open the HTML file and click nodes to play audio.")
```

### Example 2: Using Configuration File

1. **Create config file** (`my_freesound_config.json`):
   ```json
   {
     "data_source": {
       "type": "freesound",
       "freesound": {
         "query": "ambient pad",
         "tags": ["synthesizer"],
         "max_samples": 200
       }
     },
     "renderer_type": "sigma",
     "strategy": "k-core",
     "k_values": {
       "strategy_k_values": {
         "k-core": 3
       }
     },
     "output_file_prefix": "AmbientPads"
   }
   ```

2. **Run analysis**:
   ```bash
   followweb --config my_freesound_config.json
   ```

### Example 3: Incremental Building (Large Networks)

```python
from FollowWeb_Visualizor.data.loaders.freesound import IncrementalFreesoundLoader

config = {
    'api_key': 'your_api_key_here',
    'checkpoint_dir': './checkpoints/techno',
    'checkpoint_interval': 100,
    'max_runtime_hours': 1.0  # Run for 1 hour
}

loader = IncrementalFreesoundLoader(config)

# First session: Build for 1 hour
graph = loader.build_graph()
print(f"Session 1: {graph.number_of_nodes()} nodes")

# Second session: Continue for another hour
graph = loader.build_graph()
print(f"Session 2: {graph.number_of_nodes()} nodes")
```

## Using the Visualization

1. **Open the HTML file** in your browser (Chrome or Firefox recommended)
2. **Explore the network**:
   - Zoom: Mouse wheel
   - Pan: Click and drag background
   - Search: Use search box to find nodes
3. **Play audio**:
   - Click any node to play its audio sample
   - Audio player appears in bottom-right corner
   - Use play/pause, loop, and timeline controls

## Common Use Cases

### Sound Design
```python
config = {
    'data_source': {
        'type': 'freesound',
        'freesound': {
            'query': 'ambient pad',
            'tags': ['synthesizer', 'atmospheric'],
            'max_samples': 300
        }
    },
    'renderer_type': 'sigma'
}
```

### Music Production
```python
config = {
    'data_source': {
        'type': 'freesound',
        'freesound': {
            'query': 'drum loop',
            'tags': ['percussion', 'loop'],
            'max_samples': 500
        }
    },
    'renderer_type': 'sigma',
    'strategy': 'k-core',
    'k_values': {'strategy_k_values': {'k-core': 3}}
}
```

### Genre Exploration
```python
config = {
    'data_source': {
        'type': 'freesound',
        'freesound': {
            'query': 'techno',
            'tags': ['kick', 'bass'],
            'max_samples': 1000
        }
    },
    'renderer_type': 'sigma',
    'strategy': 'k-core',
    'k_values': {'strategy_k_values': {'k-core': 5}}
}
```

## Troubleshooting

### "Invalid API key" Error
```python
import os
print(os.getenv('FREESOUND_API_KEY'))  # Should print your key
```

### "No audio samples found" Warning
- Try a broader search query
- Remove restrictive tags
- Verify samples exist on Freesound.org

### Audio Not Playing
- Ensure using Sigma.js renderer (not Pyvis)
- Check browser console for errors
- Try Chrome or Firefox

### Slow Performance
- Reduce `max_samples` parameter
- Use higher k-values to prune network
- Use incremental building for large networks

## Next Steps

- **Full Documentation**: [FREESOUND_GUIDE.md](FREESOUND_GUIDE.md)
- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Configuration Guide**: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
- **API Reference**: [development/API_REFERENCE.md](development/API_REFERENCE.md)

## Example Configuration Files

See `configs/freesound_sigma_config.json` for a complete working example.

---

**Happy sound exploring!** 🎵
