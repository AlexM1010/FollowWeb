#!/usr/bin/env python3
"""
Analyze Freesound metadata field sizes to identify optimization opportunities.

This script analyzes all fields in the metadata to determine which ones
consume the most storage space.
"""

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def analyze_field_sizes(db_path: Path) -> dict[str, Any]:
    """
    Analyze field sizes across all metadata entries.
    
    Args:
        db_path: Path to metadata_cache.db
        
    Returns:
        Dictionary with field size statistics
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
    
    # Track field statistics
    field_stats = defaultdict(lambda: {
        'count': 0,
        'total_size': 0,
        'sizes': [],
        'sample_values': []
    })
    
    for sample_id, data_json in rows:
        data = json.loads(data_json)
        
        for field_name, field_value in data.items():
            # Serialize the field value to get its size
            field_json = json.dumps(field_value)
            field_size = len(field_json)
            
            field_stats[field_name]['count'] += 1
            field_stats[field_name]['total_size'] += field_size
            field_stats[field_name]['sizes'].append(field_size)
            
            # Store a sample value (first occurrence)
            if len(field_stats[field_name]['sample_values']) < 3:
                field_stats[field_name]['sample_values'].append({
                    'sample_id': sample_id,
                    'value': field_value,
                    'size': field_size
                })
    
    # Calculate statistics
    results = []
    for field_name, stats in field_stats.items():
        sizes = stats['sizes']
        results.append({
            'field': field_name,
            'count': stats['count'],
            'presence_percent': (stats['count'] / total_samples * 100),
            'total_size': stats['total_size'],
            'avg_size': stats['total_size'] / stats['count'] if stats['count'] > 0 else 0,
            'min_size': min(sizes) if sizes else 0,
            'max_size': max(sizes) if sizes else 0,
            'sample_values': stats['sample_values']
        })
    
    conn.close()
    
    return {
        'total_samples': total_samples,
        'fields': results
    }


def format_bytes(bytes_value: int) -> str:
    """Format bytes as human-readable string."""
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024 * 1024:
        return f"{bytes_value / 1024:.1f} KB"
    else:
        return f"{bytes_value / (1024 * 1024):.1f} MB"


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Freesound metadata field sizes"
    )
    parser.add_argument(
        '--checkpoint-dir',
        type=Path,
        default=Path('freesound_library'),
        help='Path to checkpoint directory (default: freesound_library)'
    )
    parser.add_argument(
        '--sort-by',
        choices=['total', 'avg', 'max', 'name'],
        default='total',
        help='Sort fields by: total size, average size, max size, or name'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=20,
        help='Show top N fields (default: 20, use 0 for all)'
    )
    parser.add_argument(
        '--show-samples',
        action='store_true',
        help='Show sample values for each field'
    )
    
    args = parser.parse_args()
    
    db_path = args.checkpoint_dir / 'metadata_cache.db'
    
    print("=" * 80)
    print("Freesound Metadata Field Size Analysis")
    print("=" * 80)
    print()
    print(f"Database: {db_path}")
    print()
    
    results = analyze_field_sizes(db_path)
    
    print(f"Total samples analyzed: {results['total_samples']}")
    print()
    
    # Sort fields
    sort_key = {
        'total': lambda x: x['total_size'],
        'avg': lambda x: x['avg_size'],
        'max': lambda x: x['max_size'],
        'name': lambda x: x['field']
    }[args.sort_by]
    
    sorted_fields = sorted(results['fields'], key=sort_key, reverse=(args.sort_by != 'name'))
    
    # Limit to top N
    if args.top > 0:
        sorted_fields = sorted_fields[:args.top]
        print(f"Top {args.top} fields by {args.sort_by} size:")
    else:
        print(f"All fields sorted by {args.sort_by} size:")
    print()
    
    # Print header
    print(f"{'Rank':<5} {'Field':<30} {'Present':<8} {'Total':<12} {'Avg':<10} {'Min':<8} {'Max':<10}")
    print("-" * 80)
    
    # Print fields
    for i, field in enumerate(sorted_fields, 1):
        print(
            f"{i:<5} "
            f"{field['field']:<30} "
            f"{field['presence_percent']:>6.1f}% "
            f"{format_bytes(field['total_size']):<12} "
            f"{format_bytes(int(field['avg_size'])):<10} "
            f"{format_bytes(field['min_size']):<8} "
            f"{format_bytes(field['max_size']):<10}"
        )
        
        # Show sample values if requested
        if args.show_samples and field['sample_values']:
            for sample in field['sample_values'][:2]:  # Show max 2 samples
                value_str = str(sample['value'])
                if len(value_str) > 60:
                    value_str = value_str[:57] + "..."
                print(f"      Sample: {value_str} ({format_bytes(sample['size'])})")
    
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    
    # Calculate total storage
    total_storage = sum(f['total_size'] for f in results['fields'])
    print(f"Total metadata storage: {format_bytes(total_storage)}")
    print()
    
    # Top 5 fields by total size
    top_5_total = sorted(results['fields'], key=lambda x: x['total_size'], reverse=True)[:5]
    top_5_size = sum(f['total_size'] for f in top_5_total)
    top_5_percent = (top_5_size / total_storage * 100) if total_storage > 0 else 0
    
    print(f"Top 5 fields account for: {format_bytes(top_5_size)} ({top_5_percent:.1f}%)")
    for field in top_5_total:
        percent = (field['total_size'] / total_storage * 100) if total_storage > 0 else 0
        print(f"  - {field['field']}: {format_bytes(field['total_size'])} ({percent:.1f}%)")
    
    print()
    
    # Optimization suggestions
    print("Optimization Opportunities:")
    print()
    
    large_fields = [f for f in results['fields'] if f['avg_size'] > 100]
    if large_fields:
        print("Fields with average size > 100 bytes:")
        for field in sorted(large_fields, key=lambda x: x['avg_size'], reverse=True)[:10]:
            print(f"  - {field['field']}: avg {format_bytes(int(field['avg_size']))}, "
                  f"total {format_bytes(field['total_size'])}")
    
    print()


if __name__ == '__main__':
    main()
