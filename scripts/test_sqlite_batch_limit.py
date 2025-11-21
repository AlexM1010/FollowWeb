#!/usr/bin/env python3
"""
Test script to find the actual SQLite batch size limit.

This script tests different batch sizes to find the maximum number of rows
that can be inserted in a single executemany() call with our schema.

Our schema uses 6 parameters per row:
- sample_id (INTEGER)
- data (JSON)
- last_updated (TEXT)
- priority_score (REAL)
- is_dormant (INTEGER)
- dormant_since (TEXT)

SQLite has SQLITE_MAX_VARIABLE_NUMBER limit (default 999, max 32766).
"""

import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def test_batch_size(batch_size: int, verbose: bool = False) -> tuple[bool, str]:
    """
    Test if a specific batch size works.
    
    Args:
        batch_size: Number of rows to insert
        verbose: Print detailed information
        
    Returns:
        Tuple of (success, error_message)
    """
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Create table (same schema as MetadataCache)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                sample_id INTEGER PRIMARY KEY,
                data JSON NOT NULL,
                last_updated TEXT NOT NULL,
                priority_score REAL,
                is_dormant INTEGER DEFAULT 0,
                dormant_since TEXT
            )
        """)
        
        # Prepare test data (realistic Freesound metadata size)
        # Real Freesound samples have ~300-400 metadata entries per sample
        # Each entry includes: sample data, user data, pack data, tags, analysis
        timestamp = datetime.now(timezone.utc).isoformat()
        rows = []
        
        for i in range(batch_size):
            # Simulate realistic Freesound metadata with nested structures
            metadata = {
                "id": i,
                "name": f"test_sample_{i}.wav",
                "tags": [f"tag{j}" for j in range(20)],  # ~20 tags per sample
                "description": "A" * 500,  # ~500 char description
                "username": f"user_{i % 100}",
                "pack": f"pack_{i % 50}" if i % 3 == 0 else None,
                "num_downloads": i * 100,
                "avg_rating": 4.5,
                "num_ratings": 42,
                "duration": 3.14159,
                "channels": 2,
                "filesize": 1024000,
                "bitrate": 320000,
                "samplerate": 44100,
                "license": "Creative Commons 0",
                "type": "wav",
                "previews": {
                    "preview-hq-mp3": f"https://example.com/{i}.mp3",
                    "preview-lq-mp3": f"https://example.com/{i}_lq.mp3",
                },
                "images": {
                    "waveform_m": f"https://example.com/waveform_{i}.png",
                    "spectral_m": f"https://example.com/spectral_{i}.png",
                },
                "analysis": {
                    "lowlevel": {
                        "pitch": [440.0 + i] * 10,
                        "mfcc": [float(j) for j in range(13)],
                    },
                    "rhythm": {
                        "bpm": 120.0 + (i % 60),
                        "beats_position": [0.5, 1.0, 1.5, 2.0],
                    },
                },
                "similar_sounds": [i + j for j in range(1, 6)],  # 5 similar sounds
            }
            
            rows.append((
                i,  # sample_id
                json.dumps(metadata),  # data (realistic size ~2-3KB)
                timestamp,  # last_updated
                float(i),  # priority_score
                0,  # is_dormant
                None,  # dormant_since
            ))
        
        # Try to insert
        conn.executemany(
            """
            INSERT OR REPLACE INTO metadata
            (sample_id, data, last_updated, priority_score, is_dormant, dormant_since)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        
        conn.commit()
        
        # Verify insertion
        cursor = conn.execute("SELECT COUNT(*) FROM metadata")
        count = cursor.fetchone()[0]
        
        if count != batch_size:
            return False, f"Expected {batch_size} rows, got {count}"
        
        if verbose:
            print(f"✅ Batch size {batch_size}: SUCCESS ({batch_size * 6} parameters)")
        
        return True, ""
        
    except sqlite3.OperationalError as e:
        error_msg = str(e)
        if verbose:
            print(f"❌ Batch size {batch_size}: FAILED - {error_msg}")
        return False, error_msg
        
    except Exception as e:
        if verbose:
            print(f"❌ Batch size {batch_size}: ERROR - {e}")
        return False, str(e)
        
    finally:
        try:
            conn.close()
            Path(db_path).unlink(missing_ok=True)
        except Exception:
            pass


def find_max_batch_size(start: int = 100, end: int = 5000, step: int = 100) -> int:
    """
    Binary search to find maximum batch size.
    
    Args:
        start: Starting batch size
        end: Ending batch size
        step: Step size for initial scan
        
    Returns:
        Maximum working batch size
    """
    print("=" * 70)
    print("SQLite Batch Size Limit Test")
    print("=" * 70)
    print()
    print("Testing with 6 parameters per row:")
    print("  - sample_id (INTEGER)")
    print("  - data (JSON)")
    print("  - last_updated (TEXT)")
    print("  - priority_score (REAL)")
    print("  - is_dormant (INTEGER)")
    print("  - dormant_since (TEXT)")
    print()
    
    # First, do a quick scan to find approximate range
    print("Phase 1: Quick scan to find approximate limit...")
    print()
    
    last_working = start
    for batch_size in range(start, end + 1, step):
        success, error = test_batch_size(batch_size, verbose=True)
        if success:
            last_working = batch_size
        else:
            # Found failure point, narrow down
            print()
            print(f"Found failure at {batch_size}, narrowing down...")
            print()
            break
    else:
        # All tests passed
        print()
        print(f"All tests up to {end} passed!")
        return end
    
    # Binary search between last_working and batch_size
    print("Phase 2: Binary search for exact limit...")
    print()
    
    low = last_working
    high = batch_size
    
    while low < high - 1:
        mid = (low + high) // 2
        success, error = test_batch_size(mid, verbose=True)
        
        if success:
            low = mid
        else:
            high = mid
    
    print()
    print("=" * 70)
    print("Results")
    print("=" * 70)
    print()
    print(f"Maximum working batch size: {low} rows")
    print(f"Total parameters: {low * 6}")
    print(f"First failing batch size: {high} rows")
    print(f"Total parameters: {high * 6}")
    print()
    
    # Test some common sizes
    print("Testing common batch sizes:")
    print()
    
    common_sizes = [50, 100, 150, 166, 200, 250, 300, 500]
    for size in common_sizes:
        if size <= low:
            success, _ = test_batch_size(size, verbose=False)
            status = "✅ SAFE" if success else "❌ FAILS"
            params = size * 6
            print(f"  {size:4d} rows ({params:5d} params): {status}")
    
    print()
    print("Recommendations:")
    print()
    
    if low >= 500:
        print("  ✅ Your SQLite supports large batches (500+ rows)")
        print("  ✅ Safe to use batch_size=500 (3000 parameters)")
        print("  ✅ Default batch_size=200 is very safe")
    elif low >= 200:
        print("  ✅ Your SQLite supports medium batches (200+ rows)")
        print("  ✅ Default batch_size=200 is safe")
        print("  ⚠️  Consider capping max to", low)
    elif low >= 166:
        print("  ⚠️  Your SQLite has default limit (999 parameters)")
        print("  ⚠️  Max safe batch: ~166 rows (996 parameters)")
        print("  ⚠️  Reduce DEFAULT_BATCH_SIZE to 150")
        print("  ⚠️  Reduce SAFE_MAX_BATCH_SIZE to 166")
    else:
        print("  ❌ Your SQLite has very low limit")
        print("  ❌ Max safe batch:", low, "rows")
        print("  ❌ Reduce DEFAULT_BATCH_SIZE to", max(50, low - 10))
        print("  ❌ Reduce SAFE_MAX_BATCH_SIZE to", low)
    
    print()
    
    return low


def test_specific_sizes():
    """Test specific batch sizes of interest."""
    print("=" * 70)
    print("Testing Specific Batch Sizes")
    print("=" * 70)
    print()
    
    test_sizes = [
        (50, "Old default"),
        (166, "Theoretical max (999 ÷ 6)"),
        (200, "New default"),
        (500, "Safe max"),
        (1000, "Large batch"),
    ]
    
    for size, description in test_sizes:
        success, error = test_batch_size(size, verbose=False)
        status = "✅ PASS" if success else "❌ FAIL"
        params = size * 6
        
        print(f"{status} | {size:4d} rows ({params:5d} params) | {description}")
        if not success and error:
            print(f"       Error: {error}")
    
    print()


if __name__ == "__main__":
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            print("Quick test mode: Testing specific sizes only")
            print()
            test_specific_sizes()
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python test_sqlite_batch_limit.py          # Full test with binary search")
            print("  python test_sqlite_batch_limit.py --quick  # Quick test of specific sizes")
            print("  python test_sqlite_batch_limit.py --help   # Show this help")
        else:
            try:
                batch_size = int(sys.argv[1])
                print(f"Testing single batch size: {batch_size}")
                print()
                success, error = test_batch_size(batch_size, verbose=True)
                if not success:
                    print()
                    print(f"Error: {error}")
                    sys.exit(1)
            except ValueError:
                print(f"Invalid argument: {sys.argv[1]}")
                print("Use --help for usage information")
                sys.exit(1)
    else:
        # Full test
        max_size = find_max_batch_size(start=100, end=1000, step=50)
        sys.exit(0)
