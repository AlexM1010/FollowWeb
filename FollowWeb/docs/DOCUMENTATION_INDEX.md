# FollowWeb Documentation Index

Complete index of all FollowWeb documentation.

## Quick Start

- **[QUICK_START_FREESOUND.md](QUICK_START_FREESOUND.md)** - Get started with Freesound in 5 minutes
- **[INSTALL_GUIDE.md](INSTALL_GUIDE.md)** - Installation and setup instructions

## User Guides

### General Usage
- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete user guide with tutorials and workflows
  - Getting started
  - Data preparation (Instagram and Freesound)
  - Configuration options
  - Analysis strategies
  - Visualization options
  - Advanced usage
  - Troubleshooting

### Freesound-Specific
- **[FREESOUND_GUIDE.md](FREESOUND_GUIDE.md)** - Complete Freesound audio network analysis guide
  - Setup and authentication
  - Configuration reference
  - Usage examples
  - Audio playback
  - Incremental building
  - Troubleshooting
  - Best practices

### Configuration
- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** - Configuration guide with layout options
  - Pipeline stages configuration
  - Analysis modes
  - Output control
  - K-value configuration
  - Layout configuration
  - CLI parameter reference

## Developer Documentation

### API Reference
- **[development/API_REFERENCE.md](development/API_REFERENCE.md)** - Complete API documentation
  - Main module (PipelineOrchestrator)
  - Configuration module
  - Data loaders (DataLoader, InstagramLoader, FreesoundLoader, IncrementalFreesoundLoader)
  - Analysis module (NetworkAnalyzer, PathAnalyzer)
  - Visualization renderers (Renderer, SigmaRenderer, PyvisRenderer)
  - Utilities and helpers

### Development Guides
- **[development/CONTRIBUTING.md](development/CONTRIBUTING.md)** - Development guidelines and contribution process
- **[development/PACKAGE_OVERVIEW.md](development/PACKAGE_OVERVIEW.md)** - High-level package architecture overview
- **[development/PARALLEL_PROCESSING_GUIDE.md](development/PARALLEL_PROCESSING_GUIDE.md)** - Centralized parallel processing system guide

## Testing

- **[../tests/README.md](../tests/README.md)** - Testing procedures and guidelines
  - Test categories (unit, integration, performance)
  - Running tests
  - Test infrastructure
  - Coverage reporting

## Pipeline Documentation

- **[../Docs/FREESOUND_PIPELINE.md](../Docs/FREESOUND_PIPELINE.md)** - Complete Freesound pipeline documentation
- **[../Docs/VALIDATION_COORDINATION.md](../Docs/VALIDATION_COORDINATION.md)** - Validation system overview
- **[../configs/FREESOUND_PIPELINE_CONFIG.md](../configs/FREESOUND_PIPELINE_CONFIG.md)** - Pipeline configuration parameters

## Attribution

- **[attribution/CONTRIBUTORS.md](attribution/CONTRIBUTORS.md)** - Contributors and contribution guidelines
- **[attribution/DEPENDENCIES.md](attribution/DEPENDENCIES.md)** - Dependency acknowledgments and licenses

## Documentation by Topic

### Data Sources

#### Instagram
- [USER_GUIDE.md - Instagram Data Format](USER_GUIDE.md#instagram-data-format)
- [USER_GUIDE.md - Data Validation](USER_GUIDE.md#data-validation)
- [API_REFERENCE.md - InstagramLoader](development/API_REFERENCE.md#instagramloader)

#### Freesound
- [FREESOUND_GUIDE.md](FREESOUND_GUIDE.md) - Complete guide
- [QUICK_START_FREESOUND.md](QUICK_START_FREESOUND.md) - Quick start
- [USER_GUIDE.md - Freesound Data Source](USER_GUIDE.md#freesound-data-source)
- [API_REFERENCE.md - FreesoundLoader](development/API_REFERENCE.md#freesoundloader)
- [API_REFERENCE.md - IncrementalFreesoundLoader](development/API_REFERENCE.md#incrementalfreesoundloader)

### Visualization

#### Sigma.js Renderer
- [USER_GUIDE.md - Sigma.js Renderer](USER_GUIDE.md#sigmajs-renderer-high-performance)
- [API_REFERENCE.md - SigmaRenderer](development/API_REFERENCE.md#sigmarenderer)
- [FREESOUND_GUIDE.md - Audio Playback](FREESOUND_GUIDE.md#audio-playback)

#### Pyvis Renderer
- [USER_GUIDE.md - Pyvis Renderer](USER_GUIDE.md#pyvis-renderer-interactive-html)
- [API_REFERENCE.md - PyvisRenderer](development/API_REFERENCE.md#pyvisrenderer)

#### Static PNG
- [USER_GUIDE.md - Static PNG Images](USER_GUIDE.md#static-png-images)
- [CONFIGURATION_GUIDE.md - Layout Configuration](CONFIGURATION_GUIDE.md#layout-configuration)

### Analysis

#### Strategies
- [USER_GUIDE.md - Analysis Strategies](USER_GUIDE.md#analysis-strategies)
- [USER_GUIDE.md - K-Core Analysis](USER_GUIDE.md#1-k-core-analysis)
- [USER_GUIDE.md - Reciprocal K-Core Analysis](USER_GUIDE.md#2-reciprocal-k-core-analysis)
- [USER_GUIDE.md - Ego-Alter Analysis](USER_GUIDE.md#3-ego-alter-analysis)

#### Configuration
- [CONFIGURATION_GUIDE.md - K-Value Configuration](CONFIGURATION_GUIDE.md#k-value-configuration)
- [CONFIGURATION_GUIDE.md - Analysis Modes](CONFIGURATION_GUIDE.md#analysis-modes)
- [CONFIGURATION_GUIDE.md - Pipeline Stage Control](CONFIGURATION_GUIDE.md#pipeline-stages-configuration)

### Advanced Features

#### Incremental Building
- [FREESOUND_GUIDE.md - Incremental Building](FREESOUND_GUIDE.md#incremental-building)
- [USER_GUIDE.md - Incremental Graph Building](USER_GUIDE.md#incremental-graph-building)
- [API_REFERENCE.md - IncrementalFreesoundLoader](development/API_REFERENCE.md#incrementalfreesoundloader)

#### Audio Playback
- [FREESOUND_GUIDE.md - Audio Playback](FREESOUND_GUIDE.md#audio-playback)
- [USER_GUIDE.md - Audio Playback (Freesound Networks)](USER_GUIDE.md#audio-playback-freesound-networks)

#### Checkpoints
- [FREESOUND_GUIDE.md - Checkpoint Management](FREESOUND_GUIDE.md#checkpoint-management)
- [USER_GUIDE.md - Incremental Large Network Building](USER_GUIDE.md#4-incremental-large-network-building)

### Troubleshooting

#### General
- [USER_GUIDE.md - Troubleshooting](USER_GUIDE.md#troubleshooting)
- [USER_GUIDE.md - Common Issues and Solutions](USER_GUIDE.md#common-issues-and-solutions)

#### Freesound-Specific
- [FREESOUND_GUIDE.md - Troubleshooting](FREESOUND_GUIDE.md#troubleshooting)
- [FREESOUND_GUIDE.md - API and Authentication Issues](FREESOUND_GUIDE.md#api-and-authentication-issues)
- [FREESOUND_GUIDE.md - Data Collection Issues](FREESOUND_GUIDE.md#data-collection-issues)
- [FREESOUND_GUIDE.md - Visualization Issues](FREESOUND_GUIDE.md#visualization-issues)

## Documentation by User Type

### New Users
1. [INSTALL_GUIDE.md](INSTALL_GUIDE.md) - Install FollowWeb
2. [QUICK_START_FREESOUND.md](QUICK_START_FREESOUND.md) - Try Freesound in 5 minutes
3. [USER_GUIDE.md - Quick Start](USER_GUIDE.md#quick-start) - Basic usage

### Researchers
1. [USER_GUIDE.md](USER_GUIDE.md) - Complete user guide
2. [FREESOUND_GUIDE.md](FREESOUND_GUIDE.md) - Freesound analysis
3. [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) - Advanced configuration
4. [USER_GUIDE.md - Output Interpretation](USER_GUIDE.md#output-interpretation) - Understanding results

### Developers
1. [development/API_REFERENCE.md](development/API_REFERENCE.md) - API documentation
2. [development/CONTRIBUTING.md](development/CONTRIBUTING.md) - Development guidelines
3. [development/PACKAGE_OVERVIEW.md](development/PACKAGE_OVERVIEW.md) - Architecture overview
4. [../tests/README.md](../tests/README.md) - Testing guide

### System Administrators
1. [FREESOUND_GUIDE.md - Nightly Scheduled Jobs](FREESOUND_GUIDE.md#nightly-scheduled-jobs) - Automated jobs
2. [CONFIGURATION_GUIDE.md - Pipeline Control](CONFIGURATION_GUIDE.md#pipeline-stages-configuration) - Pipeline management
3. [../Docs/FREESOUND_PIPELINE.md](../Docs/FREESOUND_PIPELINE.md) - Pipeline documentation

## Example Workflows

### Sound Design Exploration
1. [QUICK_START_FREESOUND.md - Example 1](QUICK_START_FREESOUND.md#example-1-simple-audio-network-5-minutes)
2. [FREESOUND_GUIDE.md - Example 1](FREESOUND_GUIDE.md#example-1-sound-design-exploration)
3. [USER_GUIDE.md - Sound Design Exploration](USER_GUIDE.md#1-sound-design-exploration)

### Music Production
1. [FREESOUND_GUIDE.md - Example 2](FREESOUND_GUIDE.md#example-2-drum-sample-analysis)
2. [USER_GUIDE.md - Complete Freesound Workflow](USER_GUIDE.md#complete-freesound-workflow)

### Social Network Analysis
1. [USER_GUIDE.md - Quick Start](USER_GUIDE.md#quick-start)
2. [USER_GUIDE.md - Analysis Strategies](USER_GUIDE.md#analysis-strategies)
3. [CONFIGURATION_GUIDE.md - Usage Examples](CONFIGURATION_GUIDE.md#usage-examples)

### Large Network Building
1. [FREESOUND_GUIDE.md - Incremental Building](FREESOUND_GUIDE.md#incremental-building)
2. [FREESOUND_GUIDE.md - Nightly Scheduled Jobs](FREESOUND_GUIDE.md#nightly-scheduled-jobs)
3. [USER_GUIDE.md - Incremental Large Network Building](USER_GUIDE.md#4-incremental-large-network-building)

## Configuration Examples

### Example Files
- `../configs/fast_config.json` - Quick analysis
- `../configs/comprehensive_layout_config.json` - Full features
- `../configs/freesound_sigma_config.json` - Freesound with Sigma.js

### Configuration Topics
- [CONFIGURATION_GUIDE.md - Configuration Structure](CONFIGURATION_GUIDE.md#configuration-structure)
- [CONFIGURATION_GUIDE.md - Configuration File Examples](CONFIGURATION_GUIDE.md#configuration-file-examples)
- [FREESOUND_GUIDE.md - Configuration Reference](FREESOUND_GUIDE.md#configuration-reference)

## External Resources

### Freesound
- [Freesound Website](https://freesound.org/)
- [Freesound API Documentation](https://freesound.org/docs/api/)
- [freesound-api Library](https://github.com/MTG/freesound-api)

### Visualization Libraries
- [Sigma.js Documentation](https://www.sigmajs.org/)
- [Pyvis Documentation](https://pyvis.readthedocs.io/)
- [NetworkX Documentation](https://networkx.org/)

### FollowWeb
- [GitHub Repository](https://github.com/alexmeckes/FollowWeb)
- [Live Freesound Visualization](https://alexmeckes.github.io/FollowWeb/)
- [GitHub Issues](https://github.com/alexmeckes/FollowWeb/issues)

---

**Last Updated**: November 2025
