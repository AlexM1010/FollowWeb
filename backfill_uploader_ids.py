#!/usr/bin/env python3
"""
Backfill uploader IDs into existing checkpoint database.

Instead of storing full preview URLs (~75 bytes each), we extract and store
only the uploader ID (~7 bytes) which is the missing piece needed to reconstruct URLs.

URL Pattern: https://freesound.org/data/previews/[folder]/[sound_id]_[uploader_id]-hq.mp3
- folder: sound_id // 1000 (calculable)
- sound_id: already have
- uploader_id: EXTRACT from API and store

This saves ~90% storage space while maintaining full URL reconstruction capability.
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

# No external dependencies needed - just extract from existing data

# Configuration
BACKUP_REPO = "AlexM1010/freesound-backup"
RELEASE_TAG = "v-checkpoint"
MOST_RECENT_BACKUP = "checkpoint_backup_3479nodes_19590816027.tar.gz"

# Regex to extract uploader ID from preview URL
# Matches: 335860_5121236-hq.mp3 -> captures 5121236
UPLOADER_ID_PATTERN = re.compile(r'_(\d+)-')


def run_command(cmd, check=True):
    """Run shell command and return output."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
    return result.stdout.strip()


def download_checkpoint():
    """Download the most recent checkpoint from GitHub releases."""
    print(f"\n📥 Downloading checkpoint: {MOST_RECENT_BACKUP}")
    
    run_command(f'gh release download {RELEASE_TAG} --repo {BACKUP_REPO} --pattern "{MOST_RECENT_BACKUP}" --clobber')
    
    print(f"✓ Downloaded {MOST_RECENT_BACKUP}")
    return MOST_RECENT_BACKUP


def extract_checkpoint(tar_path, extract_dir):
    """Extract checkpoint tar.gz file."""
    print(f"\n📦 Extracting checkpoint to {extract_dir}")
    
    with tarfile.open(tar_path, 'r:gz') as tar:
        tar.extractall(extract_dir)
    
    print(f"✓ Extracted checkpoint")
    return extract_dir


# No API calls needed - we extract from existing preview URLs in the database


def backfill_database(db_path):
    """Extract uploader IDs from existing preview URLs in database (no API calls needed)."""
    print(f"\n🔄 Extracting uploader IDs from existing preview URLs in {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all sample IDs and their data
    cursor.execute("SELECT sample_id, data FROM metadata")
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} samples to process")
    
    updated = 0
    skipped = 0
    failed = 0
    
    for sample_id, data_json in rows:
        data = json.loads(data_json)
        
        # Skip if already has uploader_id
        if 'uploader_id' in data:
            skipped += 1
            continue
        
        # Extract uploader ID from existing preview URLs
        if 'previews' in data and isinstance(data['previews'], dict):
            preview_url = data['previews'].get('preview-hq-mp3', '')
            
            if preview_url:
                match = UPLOADER_ID_PATTERN.search(preview_url)
                if match:
                    # Store only the uploader ID (saves ~90% space vs full URL)
                    data['uploader_id'] = int(match.group(1))
                    
                    # Remove the full previews dict to save space
                    del data['previews']
                    
                    # Update database
                    cursor.execute(
                        "UPDATE metadata SET data = ? WHERE sample_id = ?",
                        (json.dumps(data), sample_id)
                    )
                    updated += 1
                    
                    if updated % 100 == 0:
                        print(f"  Processed {updated} samples...")
                        conn.commit()
                else:
                    failed += 1
                    print(f"  Sample {sample_id}: ✗ Could not extract uploader ID from URL: {preview_url}")
            else:
                failed += 1
                print(f"  Sample {sample_id}: ✗ No preview URL found")
        else:
            failed += 1
            print(f"  Sample {sample_id}: ✗ No previews field in data")
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Extraction complete:")
    print(f"  - Updated: {updated}")
    print(f"  - Skipped: {skipped}")
    print(f"  - Failed: {failed}")
    print(f"  - Total: {len(rows)}")
    print(f"  - Space saved: ~{updated * 68} bytes (~{updated * 68 / 1024:.1f} KB)")
    print(f"  - No API calls needed!")
    
    return updated, failed


def repackage_checkpoint(extract_dir, output_path):
    """Repackage checkpoint as tar.gz."""
    print(f"\n📦 Repackaging checkpoint to {output_path}")
    
    with tarfile.open(output_path, 'w:gz') as tar:
        for item in Path(extract_dir).iterdir():
            tar.add(item, arcname=item.name)
    
    print(f"✓ Repackaged checkpoint")


def upload_checkpoint(tar_path):
    """Upload updated checkpoint to GitHub releases."""
    print(f"\n📤 Uploading updated checkpoint to GitHub releases")
    
    # Delete old asset
    run_command(
        f'gh release delete-asset {RELEASE_TAG} "{MOST_RECENT_BACKUP}" '
        f'--repo {BACKUP_REPO} --yes',
        check=False
    )
    
    # Upload new asset
    run_command(
        f'gh release upload {RELEASE_TAG} "{tar_path}" '
        f'--repo {BACKUP_REPO} --clobber'
    )
    
    print(f"✓ Uploaded updated checkpoint")


def main():
    """Main execution."""
    print("=" * 60)
    print("Backfill Uploader IDs - Space-Efficient URL Storage")
    print("=" * 60)
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Download checkpoint
        tar_path = download_checkpoint()
        
        # Extract checkpoint
        extract_dir = temp_path / "checkpoint"
        extract_dir.mkdir()
        extract_checkpoint(tar_path, extract_dir)
        
        # Find database file
        db_path = extract_dir / "freesound_library" / "metadata_cache.db"
        if not db_path.exists():
            print(f"✗ Database not found: {db_path}")
            sys.exit(1)
        
        # Backfill database
        updated, failed = backfill_database(db_path)
        
        if updated == 0:
            print("\n⚠️  No samples were updated. Skipping upload.")
            return
        
        # Repackage checkpoint
        output_tar = temp_path / MOST_RECENT_BACKUP
        repackage_checkpoint(extract_dir, output_tar)
        
        # Upload to GitHub
        upload_checkpoint(output_tar)
    
    print("\n" + "=" * 60)
    print("✓ Backfill complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
