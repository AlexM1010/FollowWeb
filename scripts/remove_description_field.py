#!/usr/bin/env python3
"""
Remove description field from Freesound metadata to reduce storage size.

The description field often contains lengthy license text and attribution
instructions that can be 2-3KB per sample. We keep the license URL field
which is sufficient for our needs.

This script:
1. Reads all samples from metadata_cache.db
2. Removes the 'description' field from each sample's JSON data
3. Updates the database with the cleaned data
4. Reports space savings

Usage:
    python scripts/remove_description_field.py --checkpoint-dir data/freesound_library
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def remove_description_from_metadata(db_path: Path, dry_run: bool = False) -> dict:
    """
    Remove description field from all metadata entries.
    
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
    samples_with_description = 0
    total_size_before = 0
    total_size_after = 0
    description_sizes = []
    
    updated_rows = []
    
    for sample_id, data_json in rows:
        data = json.loads(data_json)
        size_before = len(data_json)
        total_size_before += size_before
        
        # Check if description exists
        if 'description' in data:
            samples_with_description += 1
            desc_size = len(data['description'])
            description_sizes.append(desc_size)
            
            # Remove description
            del data['description']
        
        # Re-serialize
        new_data_json = json.dumps(data)
        size_after = len(new_data_json)
        total_size_after += size_after
        
        updated_rows.append((new_data_json, sample_id))
    
    # Calculate statistics
    stats = {
        'total_samples': total_samples,
        'samples_with_description': samples_with_description,
        'total_size_before_bytes': total_size_before,
        'total_size_after_bytes': total_size_after,
        'space_saved_bytes': total_size_before - total_size_after,
        'space_saved_percent': ((total_size_before - total_size_after) / total_size_before * 100) if total_size_before > 0 else 0,
        'avg_description_size': sum(description_sizes) / len(description_sizes) if description_sizes else 0,
        'max_description_size': max(description_sizes) if description_sizes else 0,
        'min_description_size': min(description_sizes) if description_sizes else 0,
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
        description="Remove description field from Freesound metadata"
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
    print("Remove Description Field from Freesound Metadata")
    print("=" * 70)
    print()
    print(f"Database: {db_path}")
    print(f"Mode: {'Dry run' if args.dry_run else 'Live update'}")
    print()
    
    stats = remove_description_from_metadata(db_path, dry_run=args.dry_run)
    
    print()
    print("=" * 70)
    print("Results")
    print("=" * 70)
    print()
    print(f"Total samples: {stats['total_samples']}")
    print(f"Samples with description: {stats['samples_with_description']}")
    print()
    print("Storage:")
    print(f"  Before: {format_bytes(stats['total_size_before_bytes'])}")
    print(f"  After:  {format_bytes(stats['total_size_after_bytes'])}")
    print(f"  Saved:  {format_bytes(stats['space_saved_bytes'])} ({stats['space_saved_percent']:.1f}%)")
    print()
    print("Description field statistics:")
    print(f"  Average size: {format_bytes(stats['avg_description_size'])}")
    print(f"  Maximum size: {format_bytes(stats['max_description_size'])}")
    print(f"  Minimum size: {format_bytes(stats['min_description_size'])}")
    print()
    
    if args.dry_run:
        print("To apply these changes, run without --dry-run flag")
    else:
        print("✅ Changes applied successfully!")
        print()
        print("Note: You should also update the Freesound loader to exclude")
        print("the description field from future API requests.")
    print()


if __name__ == '__main__':
    main()
