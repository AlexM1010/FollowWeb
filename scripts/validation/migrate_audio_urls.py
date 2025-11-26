#!/usr/bin/env python3
"""
Migrate from audio_urls to uploader_id for space efficiency.

This script:
1. Extracts uploader_id from existing audio_urls
2. Removes the bulky audio_urls field
3. Adds the compact uploader_id field

URL Pattern: https://freesound.org/data/previews/[folder]/[sound_id]_[uploader_id]-[quality].mp3
"""

import json
import re
import sqlite3
import sys
from pathlib import Path

# Pattern to extract uploader_id from preview URL
UPLOADER_ID_PATTERN = re.compile(r"_(\d+)-")


def migrate_checkpoint(checkpoint_dir: Path) -> dict:
    """Migrate audio_urls to uploader_id in metadata cache."""
    metadata_db = checkpoint_dir / "metadata_cache.db"
    
    if not metadata_db.exists():
        print(f"❌ Metadata cache not found: {metadata_db}")
        return {"migrated": 0, "skipped": 0, "errors": 0}
    
    conn = sqlite3.connect(str(metadata_db))
    cursor = conn.cursor()
    
    # Get all samples
    cursor.execute("SELECT sample_id, data FROM metadata")
    rows = cursor.fetchall()
    
    migrated = 0
    skipped = 0
    errors = 0
    
    for sample_id, data_json in rows:
        try:
            data = json.loads(data_json)
            
            # Skip if already has uploader_id
            if "uploader_id" in data and data["uploader_id"] is not None:
                skipped += 1
                continue
            
            # Check if has audio_urls to migrate from
            if "audio_urls" not in data or not data["audio_urls"]:
                skipped += 1
                continue
            
            # Parse audio_urls (might be JSON string or list)
            audio_urls = data["audio_urls"]
            if isinstance(audio_urls, str):
                try:
                    audio_urls = json.loads(audio_urls)
                except json.JSONDecodeError:
                    # Might be a single URL string
                    audio_urls = [audio_urls]
            
            # Extract uploader_id from first URL
            uploader_id = None
            for url in audio_urls:
                match = UPLOADER_ID_PATTERN.search(url)
                if match:
                    uploader_id = int(match.group(1))
                    break
            
            if uploader_id:
                # Update data
                data["uploader_id"] = uploader_id
                # Remove bulky audio_urls field
                del data["audio_urls"]
                
                # Save back to database
                cursor.execute(
                    "UPDATE metadata SET data = ? WHERE sample_id = ?",
                    (json.dumps(data), sample_id)
                )
                migrated += 1
            else:
                print(f"⚠️  Could not extract uploader_id from URLs for sample {sample_id}")
                errors += 1
                
        except Exception as e:
            print(f"❌ Error processing sample {sample_id}: {e}")
            errors += 1
    
    conn.commit()
    conn.close()
    
    return {"migrated": migrated, "skipped": skipped, "errors": errors}


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python migrate_audio_urls.py <checkpoint_dir>")
        sys.exit(1)
    
    checkpoint_dir = Path(sys.argv[1])
    
    if not checkpoint_dir.exists():
        print(f"❌ Checkpoint directory not found: {checkpoint_dir}")
        sys.exit(1)
    
    print(f"🔄 Migrating audio_urls to uploader_id in {checkpoint_dir}")
    print()
    
    results = migrate_checkpoint(checkpoint_dir)
    
    print()
    print("=" * 60)
    print("MIGRATION RESULTS")
    print("=" * 60)
    print(f"✅ Migrated: {results['migrated']} samples")
    print(f"⏭️  Skipped: {results['skipped']} samples (already have uploader_id)")
    print(f"❌ Errors: {results['errors']} samples")
    print("=" * 60)
    
    if results['errors'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
