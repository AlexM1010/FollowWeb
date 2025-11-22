# Repair Efficiency Example

## Problem Statement

You asked: "Are we grouping API calls as efficiently as possible?"

**Example scenario:**
- Node 1 missing fields: 1, 5, 6, 7
- Node 2 missing fields: 3
- Node 3 missing fields: 3, 4, 5

**Question:** Should this be 3/150 of our search request queue?

**Answer:** YES! ✅

## Implementation

### Before (Inefficient - Grouped by Field)

```python
# OLD APPROACH: Group by field type
issues_by_field = {
    "field_1": [node_1],
    "field_3": [node_2, node_3],
    "field_4": [node_3],
    "field_5": [node_1, node_3],
    "field_6": [node_1],
    "field_7": [node_1],
}

# Would need multiple API calls per field
# Very inefficient!
```

### After (Efficient - Grouped by Sample ID)

```python
# NEW APPROACH: Group by sample ID
samples_needing_repair = {node_1, node_2, node_3}

# One API call fetches ALL fields for all 3 nodes
batch = [node_1, node_2, node_3]  # 3/150 of one batch
results = client.text_search(
    filter=f"id:({node_1} {node_2} {node_3})",
    fields="id,name,tags,duration,username,uploader_id,..."  # ALL fields
)

# Result: 1 API request gets everything!
```

## Real-World Example

### Scenario: 3,479 samples with missing uploader_id

**Inefficient approach (grouped by field):**
```
Field: uploader_id
  - 3,479 samples need this field
  - Would need: 24 API requests (3,479 / 150)
  
But if we did this per field, and samples have multiple missing fields:
  - Could need 24 requests × number of unique fields
  - Very wasteful!
```

**Efficient approach (grouped by sample ID):**
```
Samples needing repair: 3,479
  - Node 1 missing: uploader_id, description, pack
  - Node 2 missing: uploader_id
  - Node 3 missing: uploader_id, description
  - ... (3,479 total)

API requests needed: 24 (3,479 / 150)
  - Batch 1: Fetch ALL fields for samples 1-150
  - Batch 2: Fetch ALL fields for samples 151-300
  - ...
  - Batch 24: Fetch ALL fields for samples 3,451-3,479

Result: 24 API requests fix ALL issues for ALL samples!
```

## Code Implementation

### Phase 1: Scan (Identify Samples Needing Repair)

```python
def scan_all_samples(self):
    # Track which samples need repair (not which fields)
    samples_needing_repair: Set[int] = set()
    
    for sample_id, data in all_samples:
        issues = check_sample_data_quality(sample_id, data)
        
        if issues:
            # ANY issue = add to repair queue
            samples_needing_repair.add(sample_id)
    
    # Result: Set of sample IDs that need ANY field fixed
    return samples_needing_repair
```

### Phase 2: Batch Repair (Group by Sample ID)

```python
def apply_fixes(self, samples_needing_repair):
    # Process in batches of 150 samples
    for batch_start in range(0, len(samples_needing_repair), 150):
        batch = samples_needing_repair[batch_start:batch_start + 150]
        
        # ONE API call fetches ALL fields for up to 150 samples
        fetched_data = fetch_batch_data(batch)
        
        # Apply ALL fixes for ALL samples in batch
        for sample_id in batch:
            if sample_id in fetched_data:
                # Update ALL missing fields at once
                update_all_fields(sample_id, fetched_data[sample_id])
```

## Efficiency Comparison

### Example: 3,479 samples, average 2.5 missing fields per sample

**Grouped by field (INEFFICIENT):**
```
Total issues: 3,479 × 2.5 = 8,697 field issues
Unique fields with issues: ~10 fields
API requests per field: 24 (3,479 / 150)
Total API requests: 24 × 10 = 240 requests ❌
```

**Grouped by sample ID (EFFICIENT):**
```
Samples needing repair: 3,479
API requests needed: 24 (3,479 / 150)
Total API requests: 24 requests ✅
```

**Efficiency gain: 10x fewer API requests!**

## Visual Example

```
Batch 1 (150 samples):
┌─────────────────────────────────────────────────┐
│ Sample 1: missing [uploader_id, description]   │
│ Sample 2: missing [uploader_id]                │
│ Sample 3: missing [uploader_id, pack]          │
│ Sample 4: missing [description]                │
│ ...                                             │
│ Sample 150: missing [uploader_id, geotag]      │
└─────────────────────────────────────────────────┘
         ↓
    1 API Request
         ↓
┌─────────────────────────────────────────────────┐
│ Fetches ALL fields for ALL 150 samples         │
│ Returns: {                                      │
│   1: {uploader_id: 123, description: "...", ...}│
│   2: {uploader_id: 456, ...}                    │
│   3: {uploader_id: 789, pack: "...", ...}       │
│   ...                                           │
│ }                                               │
└─────────────────────────────────────────────────┘
         ↓
    Apply ALL fixes
         ↓
┌─────────────────────────────────────────────────┐
│ Sample 1: ✅ uploader_id + description fixed   │
│ Sample 2: ✅ uploader_id fixed                 │
│ Sample 3: ✅ uploader_id + pack fixed          │
│ Sample 4: ✅ description fixed                 │
│ ...                                             │
│ Sample 150: ✅ uploader_id + geotag fixed      │
└─────────────────────────────────────────────────┘
```

## Summary

✅ **Correct Implementation:**
- Group by **sample ID**, not field type
- One API call fetches **ALL fields** for up to 150 samples
- Maximum efficiency: 1 request per 150 samples regardless of how many fields are missing

✅ **Your Example:**
- Node 1 missing fields 1, 5, 6, 7
- Node 2 missing field 3
- Node 3 missing fields 3, 4, 5
- **Result:** 3/150 of one batch = 1 API request fixes everything ✅

This is exactly how the new `comprehensive_data_repair.py` script works!
