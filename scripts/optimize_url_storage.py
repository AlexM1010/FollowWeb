#!/usr/bin/env python3
"""
Optimize URL storage by storing base URLs and reconstructing variants.

Freesound URLs follow predictable patterns:

Previews (4 URLs → 1 base):
  - https://cdn.freesound.org/previews/0/406_196-hq.mp3
  - https://cdn.freesound.org/previews/0/406_196-hq.ogg
  - https://cdn.freesound.org/previews/0/406_196-lq.mp3
  - https://cdn.freesound.org/previews/0/406_196-lq.ogg
  → Store: "previews/0/406_196"

Images (8 URLs → 1 base):
  - https://cdn.freesound.org/displays/0/406_196_wave_M.png
  - https://cdn.freesound.org/displays/0/406_196_wave_L.png
  - https://cdn.freesound.org/displays/0/406_196_spec_M.jpg
  - https://cdn.freesound.org/displays/0/406_196_spec_L.jpg
  - (+ 4 bw versions)
  → Store: "displays/0/406_196"

This reduces storage by ~70% for these fields.
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional


def extract_preview_base(previews: dict) -> Optional[str]:
    """
    Extract base path from preview URLs.
    
    From: https://cdn.freesound.org/previews/0/406_196-hq.mp3
    To: previews/0/406_196
    """
    if not previews or not isinstance(previews, dict):
        return None
    
    # Get any preview URL
    url = previews.get('preview_hq_mp3') or previews.get('preview_lq_mp3')
    if not url:
        return None
    
    # Extract: previews/0/406_196
    match = re.search(r'previews/(\d+/\d+_\d+)', url)
    if match:
        return f"previews/{match.group(1)}"
    
    return None


def extract_image_base(images: dict) -> Optional[str]:
    """
    Extract base path from image URLs.
    
    From: https://cdn.freesound.org/displays/0/406_196_wave_M.png
    To: displays/0/406_196
    """
    if not images or not isinstance(images, dict):
        return None
    
    # Get any image URL
    url = images.get('waveform_m') or images.get('spectral_m')
    if not url:
        return None
    
    # Extract: displays/0/406_196
    match = re.search(r'displays/(\d+/\d+_\d+)', url)
    if match:
        return f"displays/{match.group(1)}"
    
    return None


def reconstruct_previews(base: str) -> dict:
    """
    Reconstruct preview URLs from base path.
    
    From: previews/0/406_196
    To: Full preview dict with 4 URLs
    """
    cdn_base = f"https://cdn.freesound.org/{base}"
    return {
        'preview_hq_mp3': f"{cdn_base}-hq.mp3",
        'preview_hq_ogg': f"{cdn_base}-hq.ogg",
        'preview_lq_mp3': f"{cdn_base}-lq.mp3",
        'preview_lq_ogg': f"{cdn_base}-lq.ogg",
    }


def reconstruct_images(base: str) -> dict:
    """
    Reconstruct image URLs from base path.
    
    From: displays/0/406_196
    To: Full images dict with 8 URLs
    """
    cdn_base = f"https://cdn.freesound.org/{base}"
    return {
        'waveform_m': f"{cdn_base}_wave_M.png",
        'waveform_l': f"{cdn_base}_wave_L.png",
        'spectral_m': f"{cdn_base}_spec_M.jpg",
        'spectral_l': f"{cdn_base}_spec_L.jpg",
        'waveform_bw_m': f"{cdn_base}_wave_bw_M.png",
        'waveform_bw_l': f"{cdn_base}_wave_bw_L.png",
        'spectral_bw_m': f"{cdn_base}_spec_bw_M.jpg",
        'spectral_bw_l': f"{cdn_base}_spec_bw_L.jpg",
    }


def optimize_metadata(db_path: Path, dry_run: bool = False) -> dict:
    """
    Optimize URL storage in metadata.
    
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
        
        # Optimize previews
        if 'previews' in data and isinstance(data['previews'], dict):
            preview_base = extract_preview_base(data['previews'])
            if preview_base:
                data['preview_base'] = preview_base
                del data['previews']
                modified = True
        
        # Optimize images
        if 'images' in data and isinstance(data['images'], dict):
            image_base = extract_image_base(data['images'])
            if image_base:
                data['image_base'] = image_base
                del data['images']
                modified = True
        
        # Remove audio_url since we can reconstruct from preview_base
        if 'audio_url' in data and 'preview_base' in data:
            del data['audio_url']
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
        description="Optimize URL storage in Freesound metadata"
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
    print("Optimize URL Storage in Freesound Metadata")
    print("=" * 70)
    print()
    print(f"Database: {db_path}")
    print(f"Mode: {'Dry run' if args.dry_run else 'Live update'}")
    print()
    print("Optimizations:")
    print("  - previews (4 URLs) → preview_base (1 path)")
    print("  - images (8 URLs) → image_base (1 path)")
    print("  - Remove audio_url (reconstructable from preview_base)")
    print()
    
    stats = optimize_metadata(db_path, dry_run=args.dry_run)
    
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
        print("Note: Update the loader to store base paths instead of full URLs")
    print()


if __name__ == '__main__':
    main()
