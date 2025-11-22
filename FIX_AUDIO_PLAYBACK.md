# Fix Audio Playback in Visualization

## Problem

The current visualization shows "⚠️ Audio unavailable" when clicking nodes because the checkpoint data is missing the `uploader_id` field needed to construct Freesound preview URLs.

## Why This Happened

The checkpoint data (3,479 samples) was collected before the `uploader_id` extraction feature was added to the pipeline. The audio panel requires this field to reconstruct preview URLs:

```
URL Pattern: https://freesound.org/data/previews/{folder}/{sound_id}_{uploader_id}-hq.mp3
- folder: sound_id // 1000 (calculable)
- sound_id: node ID (already have)
- uploader_id: MISSING (needs to be fetched)
```

## Solution

Run the `add_uploader_ids.py` script to fetch `uploader_id` for all samples using the Freesound API batch search (150 samples per request).

### Steps

1. **Ensure API key is configured:**
   ```bash
   # Check .env file has your API key
   cat .env
   # Should show: FREESOUND_API_KEY=your_key_here
   ```

2. **Run the batch update script:**
   ```bash
   python add_uploader_ids.py
   ```

   This will:
   - Fetch uploader_id for all 3,479 samples
   - Use batch API (150 samples/request = ~24 requests total)
   - Take ~2 minutes at 60 requests/minute
   - Update the SQLite database with uploader_id fields

3. **Regenerate the visualization:**
   ```bash
   python generate_freesound_visualization.py --max-requests 0
   ```

   This will:
   - Load the updated checkpoint with uploader_id fields
   - Regenerate the HTML visualization
   - Skip data collection (--max-requests 0)

4. **Upload updated checkpoint to backup repo:**
   ```bash
   # Create backup archive
   tar -czf checkpoint_backup_3479nodes_$(python -c "import time; print(int(time.time() * 100))").tar.gz -C data freesound_library
   
   # Upload to GitHub release
   gh release upload v-checkpoint checkpoint_backup_3479nodes_*.tar.gz --repo AlexM1010/freesound-backup --clobber
   ```

5. **Deploy to GitHub Pages:**
   ```bash
   git add Output/*.html
   git commit -m "Fix: Add uploader_id for audio playback"
   git push
   ```

## If Freesound API is Down

If you see errors like `503 Service Temporarily Unavailable` or `504 Gateway Timeout`, the Freesound API is experiencing issues. Wait a few hours and try again.

## Alternative: Collect Fresh Data

Instead of updating existing data, you can collect fresh data with uploader_id included:

```bash
# Backup current checkpoint
mv data/freesound_library data/freesound_library_backup

# Collect fresh data (will include uploader_id automatically)
python generate_freesound_visualization.py --max-requests 100
```

This will start from scratch and collect 100 samples with all correct fields including uploader_id.

## Verification

After running the fix, verify it worked:

```bash
python -c "import sqlite3, json; conn = sqlite3.connect('data/freesound_library/metadata_cache.db'); cursor = conn.cursor(); cursor.execute('SELECT sample_id, data FROM metadata LIMIT 1'); row = cursor.fetchone(); data = json.loads(row[1]); print('Has uploader_id:', 'uploader_id' in data); print('uploader_id value:', data.get('uploader_id', 'MISSING'))"
```

Should output:
```
Has uploader_id: True
uploader_id value: 5121236
```

## Technical Details

The `add_uploader_ids.py` script uses the Freesound batch search API to efficiently fetch preview URLs:

- **Batch size**: 150 samples per request (API maximum)
- **Filter format**: `id:(123 OR 456 OR 789 ...)`
- **Fields requested**: `id,previews`
- **Extraction pattern**: `_(\d+)-` from preview URL
- **Storage**: Only uploader_id (~7 bytes) instead of full URL (~75 bytes)
- **Space savings**: ~90% reduction vs storing full URLs

This approach is 145x faster than fetching samples individually (24 requests vs 3,479 requests).
