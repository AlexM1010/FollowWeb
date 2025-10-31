#!/usr/bin/env python3
"""
Clean up old test output files from tests/Output directory.

This script removes test output files older than a specified number of days
to keep the test output directory manageable.
"""

import argparse
import time
from pathlib import Path


def cleanup_test_outputs(max_age_days: int = 7, dry_run: bool = False):
    """
    Identify old test output files for cleanup.

    Args:
        max_age_days: Maximum age in days for files to keep
        dry_run: If True, only return what would be deleted without actually deleting

    Returns:
        Dict with files and directories that would be deleted
    """
    output_dir = Path("tests") / "Output"

    if not output_dir.exists():
        return {
            "files": [],
            "directories": [],
            "total_size": 0,
            "error": f"Test output directory {output_dir} does not exist.",
        }

    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60

    files_to_delete = []
    dirs_to_delete = []
    total_size = 0

    # Identify files to clean up
    for file_path in output_dir.rglob("*"):
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime

            if file_age > max_age_seconds:
                file_size = file_path.stat().st_size
                total_size += file_size
                files_to_delete.append(
                    {
                        "path": str(file_path),
                        "relative_path": str(file_path.relative_to(output_dir)),
                        "size": file_size,
                        "age_days": file_age / (24 * 60 * 60),
                    }
                )

    # Identify empty directories to clean up
    for dir_path in output_dir.rglob("*"):
        if dir_path.is_dir() and dir_path != output_dir:
            try:
                if not any(dir_path.iterdir()):
                    dirs_to_delete.append(
                        {
                            "path": str(dir_path),
                            "relative_path": str(dir_path.relative_to(output_dir)),
                        }
                    )
            except OSError:
                pass

    return {
        "files": files_to_delete,
        "directories": dirs_to_delete,
        "total_size": total_size,
        "summary": f"Would delete {len(files_to_delete)} files and {len(dirs_to_delete)} directories, freeing {total_size / 1024:.1f} KB",
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up old test output files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analysis_tools/cleanup_test_outputs.py                    # Clean files older than 7 days
  python analysis_tools/cleanup_test_outputs.py --days 3           # Clean files older than 3 days
  python analysis_tools/cleanup_test_outputs.py --dry-run          # Show what would be deleted
  python analysis_tools/cleanup_test_outputs.py --days 1 --dry-run # Show files older than 1 day
        """,
    )

    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Maximum age in days for files to keep (default: 7)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    cleanup_test_outputs(args.days, args.dry_run)


if __name__ == "__main__":
    main()
