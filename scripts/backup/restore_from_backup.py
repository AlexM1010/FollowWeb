#!/usr/bin/env python3
"""
Restore Freesound checkpoint from backup.

This utility script allows you to:
- List available backups with metadata
- Restore from a specific backup
- Verify backup integrity
- View backup statistics

Usage:
    # List all available backups
    python restore_from_backup.py --list

    # List backups for specific tier
    python restore_from_backup.py --list --tier milestone

    # Show backup statistics
    python restore_from_backup.py --stats

    # Restore from specific backup (by timestamp)
    python restore_from_backup.py --restore 20251113_143022

    # Restore from most recent backup
    python restore_from_backup.py --restore latest

    # Restore from most recent backup of specific tier
    python restore_from_backup.py --restore latest --tier milestone
"""

import argparse
import gzip
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add FollowWeb to path
sys.path.insert(0, str(Path(__file__).parent / "FollowWeb"))

from FollowWeb_Visualizor.data.backup_manager import BackupManager  # noqa: E402
from FollowWeb_Visualizor.output.formatters import EmojiFormatter  # noqa: E402


def list_backups(manager: BackupManager, tier: str | None = None) -> None:
    """
    List available backups with metadata.

    Args:
        manager: BackupManager instance
        tier: Optional tier filter
    """
    backups = manager.list_backups(tier=tier)

    if not backups:
        print(EmojiFormatter.format("warning", "No backups found"))
        return

    print(EmojiFormatter.format("success", f"Found {len(backups)} backup(s)"))
    print("=" * 80)

    for backup in backups:
        timestamp = backup["timestamp"]
        nodes = backup["nodes"]
        edges = backup["edges"]
        tier_name = backup.get("tier", "unknown")
        compressed = backup.get("compressed", False)
        size_mb = backup.get("size_bytes", 0) / 1024 / 1024

        # Parse timestamp for display
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            time_str = timestamp

        # Extract short timestamp for restore command
        short_timestamp = (
            timestamp.split("T")[0].replace("-", "")
            + "_"
            + timestamp.split("T")[1][:6].replace(":", "")
        )

        print(f"\n📦 Backup: {short_timestamp}")
        print(f"   Time: {time_str}")
        print(f"   Tier: {tier_name}")
        print(f"   Nodes: {nodes:,} | Edges: {edges:,}")
        print(f"   Size: {size_mb:.2f} MB")
        print(f"   Compressed: {'Yes' if compressed else 'No'}")
        print(f"   Restore: python restore_from_backup.py --restore {short_timestamp}")

    print("=" * 80)


def show_stats(manager: BackupManager) -> None:
    """
    Show backup statistics.

    Args:
        manager: BackupManager instance
    """
    stats = manager.get_backup_stats()

    print(EmojiFormatter.format("success", "Backup Statistics"))
    print("=" * 80)
    print(f"Total backups: {stats['total_backups']}")
    print(f"Total size: {stats['total_size_mb']:.2f} MB")
    print(f"Compressed: {stats['compressed_count']}")
    print("\nBackups by tier:")
    for tier, count in stats["by_tier"].items():
        print(f"  {tier}: {count}")

    if stats["last_cleanup"]:
        try:
            dt = datetime.fromisoformat(stats["last_cleanup"].replace("Z", "+00:00"))
            cleanup_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            cleanup_str = stats["last_cleanup"]
        print(f"\nLast cleanup: {cleanup_str}")

    print("=" * 80)


def restore_backup(
    manager: BackupManager, timestamp: str, tier: str | None = None, logger: any = None
) -> bool:
    """
    Restore checkpoint from backup.

    Args:
        manager: BackupManager instance
        timestamp: Backup timestamp or 'latest'
        tier: Optional tier filter for 'latest'
        logger: Logger instance

    Returns:
        True if restore successful
    """
    # Get backup to restore
    if timestamp == "latest":
        backups = manager.list_backups(tier=tier)
        if not backups:
            print(EmojiFormatter.format("error", "No backups found"))
            return False
        backup = backups[0]  # Already sorted by timestamp (newest first)
    else:
        # Find backup by timestamp
        backups = manager.list_backups()
        backup = None
        for b in backups:
            if timestamp in b["timestamp"]:
                backup = b
                break

        if not backup:
            print(EmojiFormatter.format("error", f"Backup not found: {timestamp}"))
            return False

    # Display backup info
    print(EmojiFormatter.format("progress", "Restoring from backup:"))
    print(f"  Timestamp: {backup['timestamp']}")
    print(f"  Tier: {backup.get('tier', 'unknown')}")
    print(f"  Nodes: {backup['nodes']:,}")
    print(f"  Edges: {backup['edges']:,}")

    # Confirm restore
    response = input(
        "\nProceed with restore? This will overwrite current checkpoint. (yes/no): "
    )
    if response.lower() not in ["yes", "y"]:
        print("Restore cancelled")
        return False

    try:
        checkpoint_dir = manager.backup_dir

        # Restore each file
        for file_key in ["topology", "metadata"]:
            backup_file = checkpoint_dir / backup["files"][file_key]

            # Determine target filename
            if file_key == "topology":
                target_file = checkpoint_dir / "graph_topology.gpickle"
            else:
                target_file = checkpoint_dir / "metadata_cache.db"

            # Handle compressed files
            if backup.get("compressed", False) and backup_file.suffix == ".gz":
                print(f"Decompressing {file_key}...")
                with gzip.open(backup_file, "rb") as f_in:
                    with open(target_file, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                print(f"Copying {file_key}...")
                shutil.copy2(backup_file, target_file)

        # Restore checkpoint metadata
        import json

        checkpoint_meta = {
            "timestamp": backup["timestamp"],
            "nodes": backup["nodes"],
            "edges": backup["edges"],
            "restored_from_backup": True,
            "backup_tier": backup.get("tier", "unknown"),
        }

        checkpoint_meta_path = checkpoint_dir / "checkpoint_metadata.json"
        with open(checkpoint_meta_path, "w") as f:
            json.dump(checkpoint_meta, f, indent=2)

        print(EmojiFormatter.format("success", "Restore completed successfully!"))
        print(
            f"Checkpoint restored: {backup['nodes']:,} nodes, {backup['edges']:,} edges"
        )
        return True

    except Exception as e:
        print(EmojiFormatter.format("error", f"Restore failed: {e}"))
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Restore Freesound checkpoint from backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--list", action="store_true", help="List available backups")

    parser.add_argument("--stats", action="store_true", help="Show backup statistics")

    parser.add_argument(
        "--restore",
        type=str,
        metavar="TIMESTAMP",
        help='Restore from backup (timestamp or "latest")',
    )

    parser.add_argument(
        "--tier",
        type=str,
        choices=["frequent", "moderate", "milestone", "daily"],
        help="Filter by backup tier",
    )

    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="data/freesound_library",
        help="Checkpoint directory (default: data/freesound_library)",
    )

    args = parser.parse_args()

    # Setup logger
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("restore_backup")

    # Initialize backup manager
    manager = BackupManager(backup_dir=args.checkpoint_dir, config={}, logger=logger)

    # Execute command
    if args.list:
        list_backups(manager, tier=args.tier)
        return 0

    elif args.stats:
        show_stats(manager)
        return 0

    elif args.restore:
        success = restore_backup(manager, args.restore, tier=args.tier, logger=logger)
        return 0 if success else 1

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
