#!/usr/bin/env python3
"""
Rebuild metadata cache from graph topology.

This script is used by the freesound-data-remediation workflow to rebuild
the SQLite metadata cache from graph node data.
"""

import pickle
import sqlite3
from pathlib import Path

def main():
    checkpoint_dir = Path("data/freesound_library")
    graph_file = checkpoint_dir / "graph_topology.gpickle"
    cache_file = checkpoint_dir / "metadata_cache.db"
    
    # Load graph
    with open(graph_file, 'rb') as f:
        graph = pickle.load(f)
    
    # Create SQLite cache
    conn = sqlite3.connect(cache_file)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sample_metadata (
            sample_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            pack TEXT,
            num_downloads INTEGER,
            created TEXT,
            last_validated TEXT
        )
    ''')
    
    # Insert node data
    inserted = 0
    for node_id, data in graph.nodes(data=True):
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO sample_metadata 
                (sample_id, name, username, pack, num_downloads, created)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                node_id,
                data.get('name', 'Unknown'),
                data.get('username', 'Unknown'),
                data.get('pack', None),
                data.get('num_downloads', 0),
                data.get('created', None)
            ))
            inserted += 1
        except Exception as e:
            print(f"Warning: Could not insert node {node_id}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"✅ Rebuilt metadata cache: {inserted} entries")

if __name__ == "__main__":
    main()
