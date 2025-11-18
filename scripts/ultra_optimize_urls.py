#!/usr/bin/env python3
"""
Ultra-optimize URL storage by storing only the Freesound ID pattern.

All Freesound URLs share the same ID pattern:
- preview_base: "previews/0/406_196"
- image_base: "displays/0/406_196"  
- url: "https://freesound.org/people/TicTacShutUp/sounds/406/"

We can extract "0/406_196" and reconstruct everything from it.

This saves an additional ~50 KB (11%) on top of previous optimizations.
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional


def extract_fs_id(metadata: dict) -> Optional[str]:
    """
    Extract Freesound ID pattern from any URL field.
    
    Returns: "0/406_196" format
    """
    # Try preview_base first
    if 'preview_base' in metadata:
        # previews/0/406_196 → 0/406_196
        match = re.search(r'previews/(\d+/\d+_\d+)', metadata['preview_base'])
        if match:
            return match.group(1)
    
    # Try image_base
    if 'image_base' in metadata:
        # displays/0/406_196 → 0/406_196
        match = re.search(r'displays/(\d+/\d+_\d+)', metadata['image_base'])
        if match:
            return match.group(1)
    
    # Try url
    if 'url' in metadata:
        # https://freesound.org/people/TicTacShutUp/sounds/406/ → extract 406
        match = re.search(r'/sounds/(\d+)/', metadata['url'])
        if match:
            sound_id = match.group(1)
            # Need to get the folder from preview_base or image_base if available
            # Otherwise we can't reconstruct, so skip
            return None
    
    return None


def ultra_optimize_metadata(db_path: Path, dry_run: bool = False) -> dict:
    """
    Ultra-optimize URL storage by storing only fs_id.
    
    Args:
        db_path: Path to metadata_cache.db
        dry_run: If True, only report what would be done
        
    Returns:
        Dictionary with statistics
    """
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get all samples
    cursor.execute("SELECT sample_id, data FROM metadata")
    rows = cursor.fetchall()
    
    total_samples = len(rows)
    optimized_count = 0
    total_size_before = 0
    total_size_after = 0
    
    updated_rows = []
    
    for sample_id, data_json in rows:
        data = json.loads(data_json)
        size_before = len(data_json)
        total_size_before += size_before
        
        modified = False
        
        # Extract fs_id
        fs_id = extract_fs_id(data)
        
        if fs_id:
            # Store fs_id
            data['fs_id'] = fs_id
            
            # Remove redundant fields
            if 'preview_base' in data:
                del data['preview_base']
                modified = True
            
            if 'image_base' in data:
                del data['image_base']
                modified = True
            
            # Remove url - it's reconstructable from username + sound_id
            # Format: https://freesound.org/people/{username}/sounds/{sound_id}/
            if 'url' in data:
                del data['url']
                modified = True
            
            if modified:
                optimized_count += 1
        
        # Re-serialize
        new_data_json = json.dumps(data)
        size_after = len(new_data_json)
        total_size_after += size_after
        
        updated_rows.append((new_data_json, sample_id))
    
    # Calculate statistics
    stats = {
        'total_samples': total_samples,
        'optimized_samples': optimized_count,
        'total_size_before_bytes': total_size_before,
        'total_size_after_bytes': total_size_after,
        'space_saved_bytes': total_size_before - total_size_after,
        'space_saved_percent': ((total_size_before - total_size_after) / total_size_before * 100) if total_size_before > 0 else 0,
    }
    
    # Update database if not dry run
    if not dry_run:
        print("Updating database...")
        cursor.executemany(
            "UPDATE metadata SET data = ? WHERE sample_id = ?",
            updated_rows
        )
        conn.commit()
        print("✅ Database updated")
    else:
        print("🔍 Dry run - no changes made")
    
    conn.close()
    
    return stats


def format_bytes(bytes_value: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"


def main():
    parser = argparse.ArgumentParser(
        description="Ultra-optimize URL storage in Freesound metadata"
    )
    parser.add_argument(
        '--checkpoint-dir',
        type=Path,
        default=Path('data/freesound_library'),
        help='Path to checkpoint directory (default: data/freesound_library)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    db_path = args.checkpoint_dir / 'metadata_cache.db'
    
    print("=" * 70)
    print("Ultra-Optimize URL Storage in Freesound Metadata")
    print("=" * 70)
    print()
    print(f"Database: {db_path}")
    print(f"Mode: {'Dry run' if args.dry_run else 'Live update'}")
    print()
    print("Optimization:")
    print("  - preview_base + image_base → fs_id (single ID pattern)")
    print("  - Example: 'previews/0/406_196' + 'displays/0/406_196' → '0/406_196'")
    print("  - Saves: ~22 bytes per sample")
    print()
    
    stats = ultra_optimize_metadata(db_path, dry_run=args.dry_run)
    
    print()
    print("=" * 70)
    print("Results")
    print("=" * 70)
    print()
    print(f"Total samples: {stats['total_samples']}")
    print(f"Optimized samples: {stats['optimized_samples']}")
    print()
    print("Storage:")
    print(f"  Before: {format_bytes(stats['total_size_before_bytes'])}")
    print(f"  After:  {format_bytes(stats['total_size_after_bytes'])}")
    print(f"  Saved:  {format_bytes(stats['space_saved_bytes'])} ({stats['space_saved_percent']:.1f}%)")
    print()
    
    if args.dry_run:
        print("To apply these changes, run without --dry-run flag")
    else:
        print("✅ Changes applied successfully!")
        print()
        print("Note: Update url_helpers.py to reconstruct URLs from fs_id")
    print()


if __name__ == '__main__':
    main()
