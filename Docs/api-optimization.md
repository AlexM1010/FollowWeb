# Freesound API Request Optimization

## Problem

The original implementation made **2 API calls per sample:**
1. **Search API** - Get list of sample IDs
2. **get_sound()** - Fetch full metadata for each sample individually

**Example:** Collecting 150 samples = 1 search + 150 individual calls = **151 API requests**

## Solution

The Freesound search API supports a `fields` parameter that returns ALL metadata we need in a single call. We can eliminate the individual `get_sound()` calls entirely.

### Before (Inefficient)
```python
# Step 1: Search for sample IDs (1 API call)
results = client.text_search(query="drum", fields="id,name,tags")

# Step 2: Fetch full metadata for each sample (N API calls)
for sample_id in sample_ids:
    full_sound = client.get_sound(sample_id)  # 1 API call per sample!
    metadata = extract_metadata(full_sound)
```

**API Requests:** 1 + N (where N = number of samples)

### After (Optimized)
```python
# Single search with all fields (1 API call, or pagination calls only)
results = client.text_search(
    query="drum",
    fields="id,name,tags,duration,username,pack,license,created,url,"
          "type,channels,filesize,samplerate,previews,images,"
          "num_downloads,avg_rating,num_ratings,num_comments,category"
)

# Extract metadata directly from search results (0 additional API calls!)
for sound in results:
    metadata = extract_metadata(sound)
```

**API Requests:** Only pagination calls (1 call per 150 samples)

## Impact

### API Request Reduction

| Samples | Before | After | Reduction |
|---------|--------|-------|-----------|
| 150 | 151 requests | 1 request | **99.3%** |
| 300 | 301 requests | 2 requests | **99.3%** |
| 1,500 | 1,501 requests | 10 requests | **99.3%** |

### Time Savings

With 60 requests/minute rate limit:
- **Before:** 150 samples = 151 requests = **2.5 minutes**
- **After:** 150 samples = 1 request = **1 second**
- **Speedup:** **150x faster!**

### Nightly Collection Impact

Current nightly collection (max 1,950 requests):
- **Before:** Could collect ~1,949 samples (1 search + 1,949 get_sound calls)
- **After:** Could collect **292,500 samples** (1,950 pages × 150 samples/page)
- **Increase:** **150x more samples per run!**

## Implementation

### Changes Made

1. **Updated `_search_samples()` in freesound.py:**
   - Added comprehensive `fields` parameter to search API
   - Extract metadata directly from search results
   - Removed individual `get_sound()` calls
   - Process samples during pagination (no separate loop)

2. **Fields Requested:**
   ```
   id, name, tags, duration, username, pack, license, created, url,
   type, channels, filesize, samplerate, previews, images,
   num_downloads, avg_rating, num_ratings, num_comments, category
   ```

3. **Excluded Fields:**
   - `description` - Removed for storage optimization
   - `comments` - Not needed for network analysis
   - `similar_sounds` - Fetched separately if needed
   - `analysis` - Not needed for basic metadata

### Backward Compatibility

The `_extract_sample_metadata()` function works with both:
- Search result objects (new, optimized)
- Full sound objects from `get_sound()` (old, for compatibility)

## Benefits

1. **99.3% fewer API requests** - Dramatically reduced API usage
2. **150x faster collection** - From minutes to seconds
3. **150x more samples** - Can collect 292K samples vs 1.9K per nightly run
4. **Lower rate limit risk** - Much less likely to hit API limits
5. **Simpler code** - Removed complex two-step fetching logic

## Rate Limit Considerations

Freesound API limits:
- **Standard:** 60 requests/minute, 2,000 requests/day
- **With optimization:** Can collect 9,000 samples/minute (60 pages × 150 samples)

Daily collection potential:
- **Before:** ~2,000 samples/day (limited by request count)
- **After:** ~300,000 samples/day (limited by request count, but each request gets 150 samples)

## Testing

To verify the optimization works:

```bash
# Test with small collection
python generate_freesound_visualization.py --max-requests 5 --skip-visualization

# Check logs for:
# - No "get_sound" API calls
# - Only pagination requests
# - Faster execution time
```

## Future Optimizations

1. **Increase page_size to 150** (already done) - Maximum allowed by API
2. **Parallel pagination** - Fetch multiple pages simultaneously (if API allows)
3. **Conditional requests** - Use ETags to skip unchanged samples
4. **Batch similar sounds** - If we re-enable similar sounds, batch those requests

## Conclusion

By using the search API's `fields` parameter effectively, we've reduced API requests by **99.3%** and increased collection speed by **150x**. This allows us to collect far more samples within the same API rate limits while maintaining all functionality.

The nightly collection can now gather **150x more samples** per run, dramatically accelerating the growth of our audio sample network!
