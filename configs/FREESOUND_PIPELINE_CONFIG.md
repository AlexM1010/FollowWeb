# Freesound Pipeline Configuration

This document explains the configuration parameters for the Freesound nightly pipeline system defined in `freesound_pipeline_defaults.json`.

## Configuration File

**Location**: `configs/freesound_pipeline_defaults.json`

This configuration file defines the default parameters for the automated nightly pipeline that continuously grows the Freesound sample library.

## Parameters

### `seed_sample_id`

**Type**: `integer` or `null`  
**Default**: `null`  
**Description**: The Freesound sample ID to use as the starting point for recursive discovery.

- **`null`** (recommended): Automatically fetches the most downloaded sample from Freesound as the seed. This ensures the network grows from high-quality, widely-used content.
- **Specific ID** (e.g., `12345`): Uses the specified sample ID as the seed. Useful for targeted exploration or resuming from a specific sample.

**Example values**:
```json
"seed_sample_id": null          // Use most downloaded sample (automatic)
"seed_sample_id": 2523          // Use specific sample ID
```

**Notes**:
- When `null` and no checkpoint exists, the pipeline queries the Freesound API for the most downloaded sample
- If the API query fails, falls back to a known popular sample ID (2523)
- When a checkpoint exists, this parameter is ignored and the pipeline resumes from the checkpoint's priority queue

### `recursive_depth`

**Type**: `integer`  
**Default**: `2`  
**Description**: The depth of recursive exploration when discovering similar samples.

- **Depth 1**: Only fetches samples directly similar to the seed sample
- **Depth 2**: Fetches samples similar to the seed, then samples similar to those samples
- **Depth 3+**: Continues the recursive pattern for deeper exploration

**Example values**:
```json
"recursive_depth": 1            // Shallow exploration (faster)
"recursive_depth": 2            // Balanced exploration (recommended)
"recursive_depth": 3            // Deep exploration (slower, more comprehensive)
```

**Notes**:
- Higher depths discover more samples but consume more API requests
- Depth 2 provides a good balance between coverage and API efficiency
- The actual depth achieved may be limited by the `max_samples` constraint

### `max_samples`

**Type**: `integer`  
**Default**: `2000`  
**Maximum**: `2000`  
**Description**: The maximum number of samples to collect per pipeline execution.

- Corresponds to the Freesound API daily request limit (2000 requests/day)
- Each sample fetch consumes one API request
- The pipeline stops when this limit is reached or no more samples are discoverable

**Example values**:
```json
"max_samples": 100              // Testing/development (quick runs)
"max_samples": 500              // Partial daily allowance
"max_samples": 2000             // Full daily allowance (recommended)
```

**Notes**:
- Cannot exceed 2000 due to Freesound API daily limits
- Lower values are useful for testing or when API quota needs to be preserved
- The pipeline respects the 60 requests/minute rate limit regardless of this setting

### `checkpoint_interval`

**Type**: `integer`  
**Default**: `1`  
**Description**: How frequently to save the checkpoint file during data collection (in number of samples).

- **1**: Saves checkpoint after every sample (maximum crash resistance, recommended)
- **10**: Saves checkpoint every 10 samples (slightly faster, less I/O)
- **50**: Saves checkpoint every 50 samples (faster, but more data loss risk on crash)

**Example values**:
```json
"checkpoint_interval": 1        // Maximum safety (recommended)
"checkpoint_interval": 10       // Balanced safety/performance
"checkpoint_interval": 50       // Performance-focused
```

**Notes**:
- Lower values provide better crash recovery but increase disk I/O
- The checkpoint is always saved at the end of execution regardless of this setting
- Automatic backups are created every 100 nodes regardless of this setting
- For GitHub Actions deployment, `1` is recommended to ensure no data loss on timeout

## Usage

### Command Line

The pipeline script can override these defaults via command-line arguments:

```bash
# Use defaults from config file
python generate_freesound_visualization.py

# Override seed sample ID
python generate_freesound_visualization.py --seed-sample-id 12345

# Override max samples
python generate_freesound_visualization.py --max-samples 500

# Override recursive depth
python generate_freesound_visualization.py --depth 3

# Combine multiple overrides
python generate_freesound_visualization.py --seed-sample-id 12345 --max-samples 1000 --depth 2
```

### Environment Variables

Configuration can also be provided via environment variables:

```bash
# Set seed sample ID
export FREESOUND_SEED_SAMPLE_ID=12345

# Set API key (required)
export FREESOUND_API_KEY=your_api_key_here

# Run pipeline
python generate_freesound_visualization.py
```

### GitHub Actions

The GitHub Actions workflow uses these defaults but allows manual override via workflow dispatch inputs:

1. Navigate to Actions tab in GitHub
2. Select "Freesound Nightly Pipeline" workflow
3. Click "Run workflow"
4. Optionally override parameters:
   - `seed_sample_id`: Leave empty for automatic selection
   - `max_samples`: Default 2000
   - `recursive_depth`: Default 2

## Configuration Validation

The pipeline validates all configuration parameters at startup:

- **API Key**: Must be non-empty string
- **Numeric Parameters**: Must be non-negative integers
- **Max Samples**: Cannot exceed 2000 (API limit)
- **Paths**: Must be valid path strings

Invalid configurations will cause the pipeline to exit with detailed error messages.

## Best Practices

1. **Use Default Seed Selection**: Set `seed_sample_id` to `null` to automatically start from the most popular sample
2. **Maximize Daily Collection**: Use `max_samples: 2000` to fully utilize the API allowance
3. **Optimize for Crash Recovery**: Keep `checkpoint_interval: 1` for GitHub Actions deployment
4. **Balance Exploration Depth**: Use `recursive_depth: 2` for good coverage without excessive API usage
5. **Test with Lower Values**: Use smaller `max_samples` values during development and testing

## Related Documentation

- **Pipeline Documentation**: See `docs/FREESOUND_PIPELINE.md` for complete pipeline documentation
- **GitHub Actions Setup**: See `.github/workflows/freesound-nightly-pipeline.yml` for workflow configuration
- **Requirements**: See `.kiro/specs/freesound-nightly-pipeline/requirements.md` for detailed requirements
- **Design**: See `.kiro/specs/freesound-nightly-pipeline/design.md` for architecture details
