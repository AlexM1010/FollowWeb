# Freesound Metadata Storage Optimization

## Problem

Freesound sample metadata includes a `description` field that often contains lengthy license text, attribution instructions, and HTML formatting. This can be 2-3KB per sample, significantly increasing storage requirements.

## Current Storage

Based on analysis of 1,043 samples:
- **Total metadata size**: 1.50 MB
- **Samples with description**: 593 (56.8%)
- **Average description size**: 237 bytes
- **Maximum description size**: 2.17 KB
- **Potential savings**: 151 KB (9.8%)

## Solution

Remove the `description` field from stored metadata while keeping the `license` field which contains the license URL (e.g., `"https://creativecommons.org/licenses/by/4.0/"`).

### What We Keep
- `license`: License URL (sufficient for attribution)
- `name`: Sample name
- `tags`: Tags for categorization
- `user`/`username`: Creator information
- All other metadata fields

### What We Remove
- `description`: Often contains:
  - Lengthy license text
  - Attribution instructions in multiple formats (plaintext, HTML)
  - Recording equipment details
  - Usage instructions

## Implementation

### For Existing Data

Run the cleanup script on existing checkpoints:

```bash
# Dry run to see what would change
python scripts/remove_description_field.py --checkpoint-dir data/freesound_library --dry-run

# Apply changes
python scripts/remove_description_field.py --checkpoint-dir data/freesound_library
```

### For Future Collections

The Freesound API doesn't allow excluding specific fields in the request, so we need to strip the description field after receiving the data but before storing it.

**Option 1: Modify the loader** (recommended)
Add a post-processing step in the Freesound loader to remove description before storing.

**Option 2: Modify metadata cache**
Add a filter in `MetadataCache.set()` to automatically strip description fields.

**Option 3: API field selection** (if supported)
Configure the Freesound API client to request only needed fields (check if freesound-python library supports this).

## Benefits

1. **Storage reduction**: ~10% smaller metadata database
2. **Faster I/O**: Less data to read/write
3. **Smaller backups**: Reduced backup file sizes
4. **Faster cache operations**: Less JSON parsing overhead
5. **GitHub cache efficiency**: More samples fit within 10GB limit

## Impact on Functionality

**No impact** - The description field is not used for:
- Network analysis
- Visualization
- Community detection
- Similarity calculations
- Audio playback

The `license` URL field provides sufficient information for attribution requirements.

## Example

### Before (4.4 KB)
```json
{
  "name": "Man Crying.flac",
  "description": "Crying as a reaction...\n\nRecorded with Zoom H2...\n\n<strong>This is not public domain.</strong>...\n\nWhen using this sound, you must include attribution...\n\n[2KB+ of license text and HTML]",
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "tags": ["cry", "emotion", "sad"],
  ...
}
```

### After (1.5 KB - 66% smaller)
```json
{
  "name": "Man Crying.flac",
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "tags": ["cry", "emotion", "sad"],
  ...
}
```

## Recommendation

1. ✅ Run cleanup script on existing checkpoints
2. ✅ Modify loader to strip description before storage
3. ✅ Update backup workflow to run cleanup before backup
4. ✅ Document this optimization in tech.md

This optimization is safe, reversible (we can always fetch descriptions again if needed), and provides immediate storage benefits.
