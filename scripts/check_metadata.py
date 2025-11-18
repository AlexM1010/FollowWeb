#!/usr/bin/env python3
"""Check what data is available in the metadata cache."""

import sqlite3
import sys
from pathlib import Path

checkpoint_dir = Path("data/freesound_library")
db_path = checkpoint_dir / "metadata_cache.db"

if not db_path.exists():
    print(f"ERROR: Database not found: {db_path}")
    sys.exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables: {tables}")
print()

# Get sample count
cursor.execute("SELECT COUNT(*) FROM samples")
sample_count = cursor.fetchone()[0]
print(f"Total samples: {sample_count}")
print()

# Get column names
cursor.execute("PRAGMA table_info(samples)")
columns = cursor.fetchall()
print("Columns:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")
print()

# Get sample data
cursor.execute("SELECT id, username, pack_id, tags FROM samples LIMIT 5")
samples = cursor.fetchall()
print("Sample data (first 5):")
for sample in samples:
    print(
        f"  ID: {sample[0]}, User: {sample[1]}, Pack: {sample[2]}, Tags: {sample[3][:50] if sample[3] else None}..."
    )
print()

# Check for relationship data
cursor.execute(
    "SELECT id, username, pack_id FROM samples WHERE username IS NOT NULL LIMIT 10"
)
user_samples = cursor.fetchall()
print(f"Samples with username: {len(user_samples)}")

cursor.execute("SELECT id, pack_id FROM samples WHERE pack_id IS NOT NULL LIMIT 10")
pack_samples = cursor.fetchall()
print(f"Samples with pack_id: {len(pack_samples)}")

cursor.execute(
    "SELECT id, tags FROM samples WHERE tags IS NOT NULL AND tags != '' LIMIT 10"
)
tag_samples = cursor.fetchall()
print(f"Samples with tags: {len(tag_samples)}")

conn.close()
