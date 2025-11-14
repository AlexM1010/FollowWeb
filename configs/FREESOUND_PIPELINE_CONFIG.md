# Freesound Pipeline Configuration

This document explains the configuration parameters for the Freesound nightly pipeline system defined in `freesound_pipeline_defaults.json`.

## Configuration File

**Location**: `configs/freesound_pipeline_defaults.json`

This configuration file defines the default parameters for the automated nightly pipeline that continuously grows the Freesound sample library using a simplified search-based approach with batch edge generation.

## Core Concepts

The refactored pipeline uses a **search-based collection strategy** with three discovery modes:

1. **Search Mode**: Discovers samples through Freesound API search queries (sorted by popularity)
2. **Relationships Mode**: Discovers samples from pending nodes found during edge generation
3. **Mixed Mode**: Combines both strategies based on a configurable priority ratio

During edge generation, the pipeline discovers additional samples through user/pack relationships and stores them as "pending nodes" for future collection.

## Parameters

### `seed_sample_id` (Pipeline Script Only)

**Type**: `integer` or `null`  
**Default**: `null`  
**Description**: The Freesound sample ID to use as the starting point for search queries. This parameter is used by the pipeline script for checkpoint-aware seed selection.

**Note**: This parameter is NOT part of the loader's `fetch_data()` method. It's only used by the pipeline script (`scripts/freesound/generate_freesound_visualization.py`) to determine the initial search query.

**Example values**:
```json
"seed_sample_id": null          // Use checkpoint-aware selection (recommended)
"seed_sample_id": 2523          // Use specific sample ID
```

**Notes**:
- When `null`, the script uses checkpoint-aware seed selection (saves 1 API request/day)
- If checkpoint exists, uses the most connected node as seed
- If no checkpoint, fetches the most downloaded sample from Freesound
- This is a pipeline-level parameter, not a loader configuration parameter

### `discovery_mode`

**Type**: `string`  
**Default**: `"search"`  
**Options**: `"search"`, `"relationships"`, `"mixed"`  
**Description**: The strategy for discovering new samples.

- **search**: Discovers samples through Freesound API search queries
- **relationships**: Discovers samples from pending relationship queue (similar sounds, user/pack connections)
- **mixed**: Combines both strategies based on `relationship_priority` ratio

**Example values**:
```json
"discovery_mode": "search"           // Pure search-based discovery (recommended for initial collection)
"discovery_mode": "relationships"    // Pure relationship-based discovery (for expanding existing network)
"discovery_mode": "mixed"            // Balanced approach (uses relationship_priority)
```

**Notes**:
- `search` mode is recommended for initial data collection
- `relationships` mode is useful for expanding an existing network
- `mixed` mode balances between search and relationships based on `relationship_priority`

### `include_user_edges`

**Type**: `boolean`  
**Default**: `true`  
**Description**: Create edges between samples uploaded by the same user.

**Example values**:
```json
"include_user_edges": true      // Enable user relationship edges (recommended)
"include_user_edges": false     // Disable user edges
```

### `include_pack_edges`

**Type**: `boolean`  
**Default**: `true`  
**Description**: Create edges between samples in the same pack.

**Example values**:
```json
"include_pack_edges": true      // Enable pack relationship edges (recommended)
"include_pack_edges": false     // Disable pack edges
```

### `include_tag_edges`

**Type**: `boolean`  
**Default**: `true`  
**Description**: Create edges between samples with similar tags based on Jaccard similarity.

**Example values**:
```json
"include_tag_edges": true       // Enable tag similarity edges (recommended)
"include_tag_edges": false      // Disable tag edges
```

### `tag_similarity_threshold`

**Type**: `float`  
**Default**: `0.3`  
**Range**: `0.0` to `1.0`  
**Description**: Minimum Jaccard similarity coefficient for creating tag-based edges.

**Example values**:
```json
"tag_similarity_threshold": 0.1     // Very loose similarity (more edges)
"tag_similarity_threshold": 0.3     // Moderate similarity (recommended)
"tag_similarity_threshold": 0.5     // Strict similarity (fewer edges)
```

**Notes**:
- Lower values create more edges but may include less meaningful connections
- Higher values create fewer but more meaningful edges
- 0.3 provides a good balance for most use cases

### `relationship_priority`

**Type**: `float`  
**Default**: `0.7`  
**Range**: `0.0` to `1.0`  
**Description**: For `mixed` discovery mode, the ratio of relationship-based vs search-based discovery.

**Example values**:
```json
"relationship_priority": 0.0        // Pure search (equivalent to search mode)
"relationship_priority": 0.5        // Equal mix of relationships and search
"relationship_priority": 0.7        // Favor relationships (recommended for mixed mode)
"relationship_priority": 1.0        // Pure relationships (equivalent to relationships mode)
```

**Notes**:
- Only used when `discovery_mode` is `"mixed"`
- Higher values favor exploring existing relationships
- Lower values favor discovering new samples through search

### `max_requests`

**Type**: `integer`  
**Default**: `1950`  
**Maximum**: `2000`  
**Description**: The maximum number of API requests to make per pipeline execution.

- Corresponds to the Freesound API daily request limit (2000 requests/day)
- Set slightly below the limit (1950) to provide safety margin
- The pipeline stops when this limit is reached

**Example values**:
```json
"max_requests": 100             // Testing/development (quick runs)
"max_requests": 500             // Partial daily allowance
"max_requests": 1950            // Safe daily allowance (recommended)
```

**Notes**:
- Cannot exceed 2000 due to Freesound API daily limits
- Lower values are useful for testing or when API quota needs to be preserved
- The pipeline respects the 60 requests/minute rate limit regardless of this setting

### `page_size`

**Type**: `integer`  
**Default**: `150`  
**Range**: `1` to `150`  
**Description**: Number of samples to fetch per API search request.

**Example values**:
```json
"page_size": 50                 // Smaller pages (more requests, more granular progress)
"page_size": 150                // Maximum page size (fewer requests, recommended)
```

**Notes**:
- Freesound API maximum is 150 samples per page
- Larger page sizes are more efficient (fewer API calls)
- 150 is recommended for production use

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

### `max_pending_nodes`

**Type**: `integer`  
**Default**: `10000`  
**Description**: Maximum number of pending nodes to store in checkpoint.

**Example values**:
```json
"max_pending_nodes": 1000       // Small queue (for testing)
"max_pending_nodes": 10000      // Medium queue (recommended)
"max_pending_nodes": 50000      // Large queue (for large-scale collection)
```

**Notes**:
- Pending nodes are discovered during edge generation but not yet fetched
- Used in "relationships" and "mixed" discovery modes
- Larger values allow deeper relationship exploration

### `fetch_pending_batch_size`

**Type**: `integer`  
**Default**: `100`  
**Description**: Batch size for fetching pending nodes from API.

**Example values**:
```json
"fetch_pending_batch_size": 20  // Small batches (for testing)
"fetch_pending_batch_size": 100 // Medium batches (recommended)
"fetch_pending_batch_size": 200 // Large batches (for large-scale collection)
```

**Notes**:
- Larger batches are more efficient but may hit API limits
- 100 provides good balance between efficiency and safety

## Usage

### Command Line

The pipeline script can override these defaults via command-line arguments:

```bash
# Use defaults from config file
python scripts/freesound/generate_freesound_visualization.py

# Override discovery mode
python scripts/freesound/generate_freesound_visualization.py --discovery-mode relationships

# Override max requests
python scripts/freesound/generate_freesound_visualization.py --max-requests 500

# Control edge generation
python scripts/freesound/generate_freesound_visualization.py \
  --include-user-edges \
  --include-pack-edges \
  --no-include-tag-edges

# Set tag similarity threshold
python scripts/freesound/generate_freesound_visualization.py \
  --include-tag-edges \
  --tag-similarity-threshold 0.5

# Combine multiple overrides
python scripts/freesound/generate_freesound_visualization.py \
  --discovery-mode mixed \
  --relationship-priority 0.8 \
  --max-requests 1000 \
  --include-user-edges \
  --include-pack-edges
```

### Environment Variables

Configuration can also be provided via environment variables:

```bash
# Set API key (required)
export FREESOUND_API_KEY=your_api_key_here

# Set discovery mode
export FREESOUND_DISCOVERY_MODE=search

# Set max requests
export FREESOUND_MAX_REQUESTS=1950

# Set seed sample ID (pipeline script only)
export FREESOUND_SEED_SAMPLE_ID=12345

# Run pipeline
python scripts/freesound/generate_freesound_visualization.py
```

### GitHub Actions

The GitHub Actions workflow uses these defaults but allows manual override via workflow dispatch inputs:

1. Navigate to Actions tab in GitHub
2. Select "Freesound Nightly Pipeline" workflow
3. Click "Run workflow"
4. Optionally override parameters:
   - `discovery_mode`: Default "search" (options: search, relationships, mixed)
   - `max_requests`: Default 1950
   - `include_user_edges`: Default true
   - `include_pack_edges`: Default true
   - `include_tag_edges`: Default true
   - `tag_similarity_threshold`: Default 0.3

## Configuration Validation

The pipeline validates all configuration parameters at startup:

- **API Key**: Must be non-empty string
- **Numeric Parameters**: Must be non-negative integers
- **Max Requests**: Cannot exceed 2000 (API limit)
- **Discovery Mode**: Must be one of "search", "relationships", or "mixed"
- **Relationship Priority**: Must be between 0.0 and 1.0
- **Tag Similarity Threshold**: Must be between 0.0 and 1.0
- **Paths**: Must be valid path strings

Invalid configurations will cause the pipeline to exit with detailed error messages.

## Best Practices

1. **Start with Search Mode**: Use `discovery_mode: "search"` for initial data collection to gather popular samples
2. **Maximize Daily Collection**: Use `max_requests: 1950` to fully utilize the API allowance with safety margin
3. **Optimize for Crash Recovery**: Keep `checkpoint_interval: 1` for GitHub Actions deployment
4. **Enable User and Pack Edges**: Set both `include_user_edges` and `include_pack_edges` to `true` for rich network structure
5. **Use Tag Edges Sparingly**: Enable `include_tag_edges` only for smaller networks (< 1000 nodes) due to O(N²) complexity
6. **Moderate Tag Threshold**: Use `tag_similarity_threshold: 0.3` for balanced connectivity
7. **Test with Lower Values**: Use smaller `max_requests` values during development and testing
8. **Switch to Mixed Mode**: After initial collection, use `discovery_mode: "mixed"` to balance breadth and depth

## Discovery Mode Strategies

### Initial Collection (Days 1-7)
```json
{
  "discovery_mode": "search",
  "max_requests": 1950,
  "include_user_edges": true,
  "include_pack_edges": true,
  "include_tag_edges": false
}
```
Focus on gathering popular samples through search.

### Network Expansion (Days 8-30)
```json
{
  "discovery_mode": "mixed",
  "relationship_priority": 0.7,
  "max_requests": 1950,
  "include_user_edges": true,
  "include_pack_edges": true,
  "include_tag_edges": false
}
```
Balance search with relationship discovery to expand existing clusters.

### Deep Exploration (Days 30+)
```json
{
  "discovery_mode": "relationships",
  "max_requests": 1950,
  "include_user_edges": true,
  "include_pack_edges": true,
  "include_tag_edges": false
}
```
Focus on completing user and pack collections discovered earlier.

## Migration Guide from Legacy Parameters

If you have existing configurations using the old recursive approach, here's how to migrate:

### Removed Parameters

| Legacy Parameter | Replacement | Notes |
|-----------------|-------------|-------|
| `recursive_depth` | `discovery_mode` | Use "search" for initial collection, "mixed" for exploration |
| `include_similar` | `include_user_edges`, `include_pack_edges` | Similar sounds API is non-functional; use user/pack relationships instead |
| `max_total_samples` | `max_requests` | Now controls API requests instead of total samples |
| `priority_weight_*` | N/A | Priority queue removed; samples sorted by popularity in search |
| `dormant_penalty_multiplier` | N/A | Dormant node tracking removed |
| `fetch_similar_threshold_*` | N/A | Similar sounds API removed |
| `max_samples_mode` | N/A | Simplified to single mode |

### Migration Examples

**Old Configuration (Recursive):**
```json
{
  "seed_sample_id": 12345,
  "recursive_depth": 2,
  "max_total_samples": 1000,
  "include_similar": true,
  "priority_weight_downloads": 0.5,
  "priority_weight_degree": 0.3,
  "priority_weight_age": 0.2
}
```

**New Configuration (Search-Based):**
```json
{
  "discovery_mode": "search",
  "max_requests": 1950,
  "include_user_edges": true,
  "include_pack_edges": true,
  "include_tag_edges": false,
  "checkpoint_interval": 50
}
```

**Old Configuration (Deep Exploration):**
```json
{
  "recursive_depth": 3,
  "max_total_samples": 2000,
  "include_similar": true
}
```

**New Configuration (Deep Exploration):**
```json
{
  "discovery_mode": "mixed",
  "relationship_priority": 0.8,
  "max_requests": 1950,
  "include_user_edges": true,
  "include_pack_edges": true
}
```

## Related Documentation

- **Pipeline Documentation**: See `Docs/FREESOUND_PIPELINE.md` for complete pipeline documentation
- **GitHub Actions Setup**: See `.github/workflows/freesound-nightly-pipeline.yml` for workflow configuration
- **Refactor Spec**: See `.kiro/specs/freesound-search-refactor/` for detailed refactor requirements and design
- **User Guide**: See `FollowWeb/docs/FREESOUND_GUIDE.md` for usage examples
