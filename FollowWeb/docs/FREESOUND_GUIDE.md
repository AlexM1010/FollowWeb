# Freesound Audio Network Analysis Guide

Complete guide to analyzing audio sample networks from Freesound using FollowWeb.

## Table of Contents

1. [Introduction](#introduction)
2. [Setup and Authentication](#setup-and-authentication)
3. [Quick Start](#quick-start)
4. [Configuration Reference](#configuration-reference)
5. [Usage Examples](#usage-examples)
6. [Audio Playback](#audio-playback)
7. [Incremental Building](#incremental-building)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

## Introduction

FollowWeb's Freesound integration allows you to:
- Explore audio sample similarity networks
- Discover related sounds for music production
- Analyze sound design patterns
- Play audio samples directly in network visualizations
- Build large networks incrementally with crash recovery

### What is Freesound?

[Freesound](https://freesound.org/) is a collaborative database of Creative Commons licensed audio samples. It provides:
- Over 500,000 audio samples
- Acoustic similarity analysis
- Rich metadata (tags, packs, users)
- High-quality audio previews

## Setup and Authentication

### Step 1: Create Freesound Account

1. Visit [https://freesound.org/](https://freesound.org/)
2. Click "Sign up" and create a free account
3. Verify your email address

### Step 2: Get API Key

1. Go to [https://freesound.org/apiv2/apply](https://freesound.org/apiv2/apply)
2. Fill out the API application form:
   - **Name**: Your application name (e.g., "FollowWeb Analysis")
   - **Description**: Brief description (e.g., "Network analysis of audio samples")
   - **Accepted terms**: Check the box
3. Click "Apply for a key"
4. You'll receive your API key immediately

### Step 3: Configure Authentication

**Option 1: Environment Variable (Recommended)**

```bash
# Linux/Mac
export FREESOUND_API_KEY="your_api_key_here"

# Add to ~/.bashrc or ~/.zshrc for persistence
echo 'export FREESOUND_API_KEY="your_api_key_here"' >> ~/.bashrc

# Windows (Command Prompt)
set FREESOUND_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:FREESOUND_API_KEY="your_api_key_here"

# Add to PowerShell profile for persistence
Add-Content $PROFILE "`n`$env:FREESOUND_API_KEY='your_api_key_here'"
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

**Option 3: Python Code**

```python
import os
os.environ['FREESOUND_API_KEY'] = 'your_api_key_here'
```

### Step 4: Verify Setup

```python
from FollowWeb_Visualizor.data.loaders.freesound import FreesoundLoader
import os

api_key = os.getenv('FREESOUND_API_KEY')
if not api_key:
    print("❌ API key not found")
else:
    print(f"✓ API key found: {api_key[:10]}...")
    
    # Test connection
    try:
        loader = FreesoundLoader({'api_key': api_key})
        print("✓ FreesoundLoader initialized successfully")
    except Exception as e:
        print(f"❌ Error: {e}")
```

## Quick Start

### Basic Freesound Analysis

```python
from FollowWeb_Visualizor.main import PipelineOrchestrator
from FollowWeb_Visualizor.core.config import get_configuration_manager

# Simple configuration
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
    print("✓ Analysis complete! Open the HTML file to explore.")
```

### Command Line Usage

```bash
# Quick analysis
followweb --data-source freesound --renderer-type sigma --freesound-query "ambient"

# With configuration file
followweb --config configs/freesound_sigma_config.json
```

## Configuration Reference

### Complete Configuration Example

```json
{
  "data_source": {
    "type": "freesound",
    "freesound": {
      "api_key": "${FREESOUND_API_KEY}",
      "query": "jungle drum",
      "tags": ["loop", "percussion"],
      "max_samples": 500,
      "checkpoint_dir": "./checkpoints/jungle_drums",
      "checkpoint_interval": 100,
      "max_runtime_hours": 2.0,
      "verify_existing_sounds": true,
      "verification_age_days": 7
    }
  },
  "renderer_type": "sigma",
  "sigma_interactive": {
    "enable_webgl": true,
    "enable_search": true,
    "audio_player": {
      "enabled": true,
      "show_controls": true,
      "enable_loop": true
    }
  },
  "strategy": "k-core",
  "k_values": {
    "strategy_k_values": {
      "k-core": 3
    }
  },
  "output_file_prefix": "JungleDrums",
  "output_control": {
    "generate_html": true,
    "generate_png": false,
    "generate_reports": true
  }
}
```

### Freesound Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | string | `$FREESOUND_API_KEY` | Freesound API key |
| `query` | string | Required | Search query for audio samples |
| `tags` | list[string] | `[]` | Filter by tags (AND logic) |
| `max_samples` | int | `1000` | Maximum samples to fetch |
| `checkpoint_dir` | string | `./checkpoints/freesound` | Checkpoint directory |
| `checkpoint_interval` | int | `100` | Save checkpoint every N samples |
| `max_runtime_hours` | float | `null` | Maximum runtime before stopping |
| `verify_existing_sounds` | bool | `false` | Check for deleted samples |
| `verification_age_days` | int | `7` | Verify samples older than N days |

### Sigma.js Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_webgl` | bool | `true` | Use WebGL rendering |
| `enable_search` | bool | `true` | Enable node search |
| `audio_player.enabled` | bool | `true` | Enable audio playback |
| `audio_player.show_controls` | bool | `true` | Show player controls |
| `audio_player.enable_loop` | bool | `true` | Enable loop toggle |

## Usage Examples

### Example 1: Sound Design Exploration

Find related ambient sounds:

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
    'k_values': {'strategy_k_values': {'k-core': 2}},
    'output_file_prefix': 'AmbientPads'
}
```

### Example 2: Drum Sample Analysis

Analyze drum loops and one-shots:

```python
config_dict = {
    'data_source': {
        'type': 'freesound',
        'freesound': {
            'query': 'drum',
            'tags': ['loop', 'percussion'],
            'max_samples': 500
        }
    },
    'renderer_type': 'sigma',
    'strategy': 'k-core',
    'k_values': {'strategy_k_values': {'k-core': 3}},
    'output_file_prefix': 'DrumSamples'
}
```

### Example 3: Genre Exploration

Explore techno sound palette:

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
    'k_values': {'strategy_k_values': {'k-core': 5}},
    'output_file_prefix': 'TechnoSounds'
}
```

### Example 4: Sample Pack Analysis

Analyze a specific sample pack:

```python
config_dict = {
    'data_source': {
        'type': 'freesound',
        'freesound': {
            'query': 'pack:12345',  # Replace with actual pack ID
            'max_samples': 200
        }
    },
    'renderer_type': 'sigma',
    'output_file_prefix': 'SamplePack_12345'
}
```

### Example 5: User's Sounds

Analyze sounds from a specific user:

```python
config_dict = {
    'data_source': {
        'type': 'freesound',
        'freesound': {
            'query': 'username:johndoe',  # Replace with actual username
            'max_samples': 300
        }
    },
    'renderer_type': 'sigma',
    'output_file_prefix': 'User_JohnDoe'
}
```

## Audio Playback

### Using the Audio Player

The Sigma.js visualization includes an integrated audio player:

1. **Click any node** to play its audio sample
2. **Audio player appears** in the bottom-right corner
3. **Controls available**:
   - Play/Pause button
   - Loop toggle button
   - Timeline scrubber for seeking
   - Time display (current / total)
   - Sample name display

### Audio Player Features

- **Visual Highlighting**: Currently playing node highlighted in distinct color
- **Automatic Loading**: Audio loads automatically when node is clicked
- **Error Handling**: Graceful handling of missing or invalid audio URLs
- **High-Quality Audio**: Uses HQ MP3 previews from Freesound

### Keyboard Shortcuts

Currently, keyboard shortcuts are not implemented (planned for future release).

### Browser Compatibility

Audio playback works best in:
- ✓ Chrome/Chromium (recommended)
- ✓ Firefox
- ✓ Safari
- ✓ Edge

## Incremental Building

### Why Use Incremental Building?

For large audio networks (1000+ samples), incremental building provides:
- **Crash Recovery**: Resume after interruptions
- **Time-Limited Execution**: Perfect for scheduled jobs
- **Progress Tracking**: Detailed logging and ETA
- **Deleted Sample Cleanup**: Remove samples that no longer exist

### Basic Incremental Building

```python
from FollowWeb_Visualizor.data.loaders.freesound import IncrementalFreesoundLoader

config = {
    'api_key': 'your_api_key_here',
    'checkpoint_dir': './checkpoints/large_network',
    'checkpoint_interval': 100,
    'max_runtime_hours': 2.0
}

loader = IncrementalFreesoundLoader(config)

# First run: Build for 2 hours
graph = loader.build_graph()
print(f"Session 1: {graph.number_of_nodes()} nodes")

# Second run: Continue for another 2 hours
graph = loader.build_graph()
print(f"Session 2: {graph.number_of_nodes()} nodes")
```

### Checkpoint Management

```python
from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint

checkpoint = GraphCheckpoint('./checkpoints/my_network')

# Check if checkpoint exists
if checkpoint.exists():
    print("Checkpoint found, will resume from last save")
else:
    print("No checkpoint found, starting fresh")

# Clear checkpoint to start over
checkpoint.clear()
```

### Nightly Scheduled Jobs

Perfect for building large networks over multiple nights:

```python
# nightly_freesound_job.py
from FollowWeb_Visualizor.data.loaders.freesound import IncrementalFreesoundLoader
import logging

logging.basicConfig(level=logging.INFO)

config = {
    'api_key': 'your_api_key_here',
    'checkpoint_dir': './checkpoints/nightly_build',
    'checkpoint_interval': 100,
    'max_runtime_hours': 4.0,  # Run for 4 hours each night
    'verify_existing_sounds': True
}

loader = IncrementalFreesoundLoader(config)
graph = loader.build_graph()

print(f"Nightly job complete: {graph.number_of_nodes()} nodes total")
```

Schedule with cron (Linux/Mac):
```bash
# Run every night at 2 AM
0 2 * * * cd /path/to/project && python nightly_freesound_job.py
```

Schedule with Task Scheduler (Windows):
```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute "python" -Argument "nightly_freesound_job.py" -WorkingDirectory "C:\path\to\project"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "FreesoundNightly"
```

## Troubleshooting

### API and Authentication Issues

#### "Invalid API key" Error

**Symptoms**: Error message about invalid or missing API key

**Solutions**:
1. Verify API key is set:
   ```python
   import os
   print(os.getenv('FREESOUND_API_KEY'))
   ```

2. Check API key on Freesound:
   - Visit [https://freesound.org/apiv2/apply](https://freesound.org/apiv2/apply)
   - Verify your API key is active

3. Test API connection:
   ```python
   import freesound
   client = freesound.FreesoundClient()
   client.set_token('your_api_key_here')
   # If no error, key is valid
   ```

#### "Rate limit exceeded" Error

**Symptoms**: Error about too many requests

**Solutions**:
1. The loader automatically handles rate limiting, but you can:
   - Reduce `checkpoint_interval` to save more frequently
   - Use shorter `max_runtime_hours` sessions
   - Wait a few minutes before retrying

2. Check rate limit status:
   ```python
   # Rate limit: 60 requests per minute
   # The loader automatically throttles requests
   ```

### Data Collection Issues

#### "No audio samples found" Warning

**Symptoms**: Search returns zero results

**Solutions**:
1. Verify search on Freesound.org:
   - Visit [https://freesound.org/search/](https://freesound.org/search/)
   - Try your query and tags
   - Adjust query if needed

2. Broaden search criteria:
   ```python
   # Too restrictive
   config = {
       'query': 'very specific rare sound',
       'tags': ['tag1', 'tag2', 'tag3']
   }
   
   # Better
   config = {
       'query': 'drum',
       'tags': ['loop']
   }
   ```

3. Remove tag filters:
   ```python
   config = {
       'query': 'ambient',
       'tags': []  # No tag filtering
   }
   ```

#### Slow Data Collection

**Symptoms**: Data collection takes too long

**Solutions**:
1. Reduce sample count:
   ```python
   config = {'max_samples': 200}  # Instead of 1000
   ```

2. Use incremental building:
   ```python
   config = {
       'checkpoint_interval': 50,
       'max_runtime_hours': 1.0
   }
   ```

3. Skip verification:
   ```python
   config = {'verify_existing_sounds': False}
   ```

### Checkpoint Issues

#### "Checkpoint corrupted" Error

**Symptoms**: Error loading checkpoint file

**Solutions**:
1. Clear corrupted checkpoint:
   ```python
   from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint
   checkpoint = GraphCheckpoint('./checkpoints/freesound')
   checkpoint.clear()
   ```

2. Check disk space:
   ```bash
   df -h  # Linux/Mac
   ```

3. Verify checkpoint directory permissions:
   ```bash
   ls -la ./checkpoints/
   ```

#### Checkpoint Not Resuming

**Symptoms**: Starts from beginning despite checkpoint

**Solutions**:
1. Verify checkpoint exists:
   ```python
   from FollowWeb_Visualizor.data.checkpoint import GraphCheckpoint
   checkpoint = GraphCheckpoint('./checkpoints/freesound')
   print(f"Checkpoint exists: {checkpoint.exists()}")
   ```

2. Check checkpoint directory path:
   ```python
   import os
   checkpoint_dir = './checkpoints/freesound'
   print(f"Absolute path: {os.path.abspath(checkpoint_dir)}")
   print(f"Directory exists: {os.path.exists(checkpoint_dir)}")
   ```

### Visualization Issues

#### Audio Playback Not Working

**Symptoms**: Clicking nodes doesn't play audio

**Solutions**:
1. Verify using Sigma.js renderer:
   ```python
   config = {'renderer_type': 'sigma'}  # Not 'pyvis'
   ```

2. Check audio player is enabled:
   ```python
   config = {
       'sigma_interactive': {
           'audio_player': {
               'enabled': True
           }
       }
   }
   ```

3. Verify nodes have audio URLs:
   ```python
   for node_id in list(graph.nodes())[:5]:
       node_data = graph.nodes[node_id]
       print(f"Node {node_id}: {node_data.get('audio_url', 'NO URL')}")
   ```

4. Check browser console for errors:
   - Open browser developer tools (F12)
   - Check Console tab for errors
   - Try different browser (Chrome recommended)

#### Visualization Too Slow

**Symptoms**: Laggy or unresponsive visualization

**Solutions**:
1. Reduce network size with higher k-value:
   ```python
   config = {
       'strategy': 'k-core',
       'k_values': {'strategy_k_values': {'k-core': 5}}
   }
   ```

2. Disable WebGL (fallback to canvas):
   ```python
   config = {
       'sigma_interactive': {
           'enable_webgl': False
       }
   }
   ```

3. Use modern browser with hardware acceleration

### Memory Issues

#### "Out of memory" Error

**Symptoms**: Process crashes with memory error

**Solutions**:
1. Reduce sample count:
   ```python
   config = {'max_samples': 500}
   ```

2. Use incremental building with shorter sessions:
   ```python
   config = {
       'checkpoint_interval': 50,
       'max_runtime_hours': 0.5
   }
   ```

3. Increase system swap space (Linux/Mac):
   ```bash
   # Check current swap
   swapon --show
   ```

## Best Practices

### Search Query Optimization

1. **Start Broad, Then Narrow**:
   ```python
   # First: Broad search
   config = {'query': 'drum'}
   
   # Then: Add tags to narrow
   config = {'query': 'drum', 'tags': ['loop']}
   ```

2. **Use Specific Tags**:
   ```python
   # Good tags
   tags = ['loop', 'percussion', 'synthesizer']
   
   # Avoid vague tags
   tags = ['sound', 'audio', 'music']
   ```

3. **Test Queries on Freesound.org First**:
   - Visit [https://freesound.org/search/](https://freesound.org/search/)
   - Test your query and tags
   - Verify results before running analysis

### Performance Optimization

1. **Use Appropriate Sample Counts**:
   - Small exploration: 100-300 samples
   - Medium analysis: 500-1000 samples
   - Large network: 1000+ samples (use incremental building)

2. **Checkpoint Frequently for Large Networks**:
   ```python
   config = {
       'checkpoint_interval': 50,  # Save every 50 samples
       'max_runtime_hours': 2.0    # 2-hour sessions
   }
   ```

3. **Skip Verification for Initial Builds**:
   ```python
   config = {
       'verify_existing_sounds': False  # Enable later for maintenance
   }
   ```

### Network Analysis Tips

1. **Adjust K-Values Based on Network Density**:
   - Dense networks (many connections): Higher k-values (5-10)
   - Sparse networks (few connections): Lower k-values (2-3)

2. **Use Sigma.js for Large Networks**:
   ```python
   # For 1000+ nodes
   config = {'renderer_type': 'sigma'}
   
   # For < 500 nodes, either works
   config = {'renderer_type': 'pyvis'}  # or 'sigma'
   ```

3. **Generate Reports for Analysis**:
   ```python
   config = {
       'output_control': {
           'generate_reports': True
       }
   }
   ```

### Maintenance and Updates

1. **Periodic Verification**:
   ```python
   # Run weekly to remove deleted samples
   config = {
       'verify_existing_sounds': True,
       'verification_age_days': 7
   }
   ```

2. **Backup Checkpoints**:
   ```bash
   # Backup checkpoint directory
   cp -r ./checkpoints/freesound ./checkpoints/freesound_backup_$(date +%Y%m%d)
   ```

3. **Monitor API Usage**:
   - Freesound API: 60 requests/minute
   - Plan accordingly for large networks
   - Use checkpoints to spread collection over time

### Workflow Recommendations

1. **Exploration Workflow**:
   ```python
   # Step 1: Small sample for exploration
   config = {'max_samples': 100}
   
   # Step 2: Analyze results
   # Step 3: Expand if interesting
   config = {'max_samples': 500}
   ```

2. **Production Workflow**:
   ```python
   # Use incremental building
   config = {
       'checkpoint_interval': 100,
       'max_runtime_hours': 2.0,
       'verify_existing_sounds': True
   }
   ```

3. **Research Workflow**:
   ```python
   # Comprehensive analysis
   config = {
       'max_samples': 2000,
       'strategy': 'k-core',
       'k_values': {'strategy_k_values': {'k-core': 5}},
       'output_control': {
           'generate_html': True,
           'generate_png': True,
           'generate_reports': True
       }
   }
   ```

## Additional Resources

### Freesound API Documentation
- [Freesound API v2 Documentation](https://freesound.org/docs/api/)
- [freesound-python Library](https://github.com/MTG/freesound-python)

### FollowWeb Documentation
- [User Guide](USER_GUIDE.md)
- [Configuration Guide](CONFIGURATION_GUIDE.md)
- [API Reference](development/API_REFERENCE.md)

### Community and Support
- [FollowWeb GitHub Issues](https://github.com/alexmeckes/FollowWeb/issues)
- [Freesound Forums](https://freesound.org/forum/)

## Example Configuration Files

See `configs/freesound_sigma_config.json` for a complete working example.

---

**Happy sound exploring!** 🎵
