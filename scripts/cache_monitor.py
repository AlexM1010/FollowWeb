#!/usr/bin/env python3
"""
Cache Size Monitor for GitHub Actions

Monitors the size of checkpoint data and triggers early backup if approaching
GitHub's 10GB cache limit. This prevents cache eviction and data loss.

GitHub Actions Cache Limits:
- Maximum size per cache entry: 10GB
- Retention: 7 days (or until evicted by size limit)
- Total cache size: 10GB across ALL caches in repository (CRITICAL)

IMPORTANT: The 10GB limit is shared across ALL caches in the repository.
If multiple caches exist, they compete for the same 10GB quota.

Usage:
    python scripts/cache_monitor.py --checkpoint-dir data/freesound_library

Exit Codes:
    0: Cache size is safe
    1: Cache size approaching limit (trigger early backup)
    2: Cache size exceeded limit (critical)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Tuple


# Cache size thresholds
CACHE_LIMIT_GB = 10.0
CACHE_WARNING_THRESHOLD = 0.80  # 80% of limit (8GB)
CACHE_CRITICAL_THRESHOLD = 0.95  # 95% of limit (9.5GB)

# Convert to bytes
CACHE_LIMIT_BYTES = int(CACHE_LIMIT_GB * 1024 * 1024 * 1024)
CACHE_WARNING_BYTES = int(CACHE_LIMIT_BYTES * CACHE_WARNING_THRESHOLD)
CACHE_CRITICAL_BYTES = int(CACHE_LIMIT_BYTES * CACHE_CRITICAL_THRESHOLD)


def get_directory_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total_size = 0
    
    if not path.exists():
        return 0
    
    for item in path.rglob('*'):
        if item.is_file():
            try:
                total_size += item.stat().st_size
            except (OSError, PermissionError):
                # Skip files we can't access
                pass
    
    return total_size


def format_bytes(bytes_value: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def get_file_sizes(checkpoint_dir: Path) -> Dict[str, int]:
    """Get sizes of individual checkpoint files."""
    files = {
        'graph_topology': checkpoint_dir / 'graph_topology.gpickle',
        'metadata_cache': checkpoint_dir / 'metadata_cache.db',
        'checkpoint_metadata': checkpoint_dir / 'checkpoint_metadata.json',
    }
    
    sizes = {}
    for name, path in files.items():
        if path.exists():
            sizes[name] = path.stat().st_size
        else:
            sizes[name] = 0
    
    return sizes


def check_cache_size(checkpoint_dir: Path) -> Tuple[int, str, int]:
    """
    Check cache size and determine status.
    
    Returns:
        Tuple of (exit_code, status_message, total_size_bytes)
    """
    total_size = get_directory_size(checkpoint_dir)
    file_sizes = get_file_sizes(checkpoint_dir)
    
    # Calculate percentages
    percent_used = (total_size / CACHE_LIMIT_BYTES) * 100
    
    # Determine status
    if total_size >= CACHE_CRITICAL_BYTES:
        status = "CRITICAL"
        exit_code = 2
        message = f"⚠️ CRITICAL: Cache size {format_bytes(total_size)} ({percent_used:.1f}%) exceeds {CACHE_CRITICAL_THRESHOLD*100:.0f}% threshold"
    elif total_size >= CACHE_WARNING_BYTES:
        status = "WARNING"
        exit_code = 1
        message = f"⚠️ WARNING: Cache size {format_bytes(total_size)} ({percent_used:.1f}%) exceeds {CACHE_WARNING_THRESHOLD*100:.0f}% threshold"
    else:
        status = "OK"
        exit_code = 0
        message = f"✅ OK: Cache size {format_bytes(total_size)} ({percent_used:.1f}%) is within safe limits"
    
    # Print detailed report
    print("=" * 70)
    print("GitHub Actions Cache Size Monitor")
    print("=" * 70)
    print()
    print(f"Status: {status}")
    print(f"Checkpoint Size: {format_bytes(total_size)} ({percent_used:.1f}% of {CACHE_LIMIT_GB}GB limit)")
    print()
    print("⚠️  IMPORTANT: GitHub's 10GB limit is shared across ALL caches in repository")
    print("   Multiple caches will compete for the same 10GB quota")
    print()
    print("File Breakdown:")
    print(f"  - graph_topology.gpickle: {format_bytes(file_sizes['graph_topology'])}")
    print(f"  - metadata_cache.db: {format_bytes(file_sizes['metadata_cache'])}")
    print(f"  - checkpoint_metadata.json: {format_bytes(file_sizes['checkpoint_metadata'])}")
    print()
    print("Thresholds:")
    print(f"  - Warning: {format_bytes(CACHE_WARNING_BYTES)} ({CACHE_WARNING_THRESHOLD*100:.0f}%)")
    print(f"  - Critical: {format_bytes(CACHE_CRITICAL_BYTES)} ({CACHE_CRITICAL_THRESHOLD*100:.0f}%)")
    print(f"  - Limit: {format_bytes(CACHE_LIMIT_BYTES)} (100%)")
    print()
    print(message)
    print()
    
    if exit_code > 0:
        print("Recommendation:")
        if exit_code == 2:
            print("  - IMMEDIATE ACTION REQUIRED: Trigger backup and clear ALL caches")
            print("  - Cache may be evicted by GitHub if total exceeds 10GB")
            print("  - Remember: 10GB limit is shared across ALL repository caches")
            print("  - Consider reducing checkpoint interval or data collection rate")
        else:
            print("  - Trigger early backup to prevent cache eviction")
            print("  - Clear old caches after backup to free space")
            print("  - Monitor cache growth rate")
            print("  - Consider optimizing checkpoint size if growth continues")
        print()
    
    # Output for GitHub Actions
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.getenv('GITHUB_OUTPUT'), 'a') as f:
            f.write(f"cache_size_bytes={total_size}\n")
            f.write(f"cache_size_human={format_bytes(total_size)}\n")
            f.write(f"cache_percent={percent_used:.1f}\n")
            f.write(f"cache_status={status}\n")
            f.write(f"trigger_backup={'true' if exit_code > 0 else 'false'}\n")
    
    # Output for GitHub Actions step summary
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.getenv('GITHUB_STEP_SUMMARY'), 'a') as f:
            f.write("## 📊 Cache Size Monitor\n\n")
            f.write(f"**Status:** {status}\n\n")
            f.write(f"**Total Size:** {format_bytes(total_size)} ({percent_used:.1f}% of {CACHE_LIMIT_GB}GB limit)\n\n")
            f.write("### File Breakdown\n\n")
            f.write("| File | Size |\n")
            f.write("|------|------|\n")
            f.write(f"| graph_topology.gpickle | {format_bytes(file_sizes['graph_topology'])} |\n")
            f.write(f"| metadata_cache.db | {format_bytes(file_sizes['metadata_cache'])} |\n")
            f.write(f"| checkpoint_metadata.json | {format_bytes(file_sizes['checkpoint_metadata'])} |\n")
            f.write(f"| **Total** | **{format_bytes(total_size)}** |\n\n")
            
            if exit_code > 0:
                f.write("### ⚠️ Action Required\n\n")
                if exit_code == 2:
                    f.write("**CRITICAL:** Cache size exceeds 95% threshold!\n\n")
                    f.write("- Immediate backup required\n")
                    f.write("- Clear ALL caches after backup (10GB limit is shared)\n")
                    f.write("- Cache may be evicted by GitHub\n")
                    f.write("- Consider reducing data collection rate\n\n")
                else:
                    f.write("**WARNING:** Cache size exceeds 80% threshold\n\n")
                    f.write("- Early backup recommended\n")
                    f.write("- Clear old caches after backup\n")
                    f.write("- Monitor cache growth rate\n\n")
            
            f.write("**Note:** GitHub's 10GB cache limit is shared across ALL caches in the repository.\n\n")
    
    return exit_code, message, total_size


def main():
    parser = argparse.ArgumentParser(
        description="Monitor GitHub Actions cache size and trigger early backup if needed"
    )
    parser.add_argument(
        '--checkpoint-dir',
        type=Path,
        default=Path('data/freesound_library'),
        help='Path to checkpoint directory (default: data/freesound_library)'
    )
    
    args = parser.parse_args()
    
    if not args.checkpoint_dir.exists():
        print(f"Error: Checkpoint directory not found: {args.checkpoint_dir}")
        sys.exit(2)
    
    exit_code, message, total_size = check_cache_size(args.checkpoint_dir)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
