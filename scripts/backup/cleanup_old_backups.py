#!/usr/bin/env python3
"""
Cleanup old backup files for Freesound library checkpoints.

This script manages backup retention by:
- Keeping only the N most recent backups
- Deleting backups older than the retention period
- Using safe file operations with retry logic
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add FollowWeb to path
sys.path.insert(0, str(Path(__file__).parent / "FollowWeb"))

from FollowWeb_Visualizor.utils.files import safe_file_cleanup
from FollowWeb_Visualizor.output.formatters import EmojiFormatter


def setup_logging():
    """Configure logging with emoji support."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger(__name__)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Cleanup old backup files for Freesound library checkpoints",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        required=True,
        help="Directory containing checkpoint and backup files",
    )

    parser.add_argument(
        "--max-backups",
        type=int,
        default=5,
        help="Maximum number of recent backups to keep",
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=7,
        help="Delete backups older than this many days",
    )

    return parser.parse_args()


def cleanup_old_backups(
    checkpoint_dir: str, max_backups: int, retention_days: int, logger: logging.Logger
) -> int:
    """
    Remove old backup files based on retention policy.

    Args:
        checkpoint_dir: Directory containing backup files
        max_backups: Maximum number of recent backups to keep
        retention_days: Delete backups older than this many days
        logger: Logger instance

    Returns:
        Number of backups deleted
    """
    backup_dir = Path(checkpoint_dir)

    if not backup_dir.exists():
        logger.warning(
            EmojiFormatter.format(
                "warning", f"Checkpoint directory does not exist: {checkpoint_dir}"
            )
        )
        return 0

    # Find all backup files
    backup_pattern = "freesound_library_backup_*.pkl"
    backup_files = sorted(
        backup_dir.glob(backup_pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,  # Newest first
    )

    if not backup_files:
        logger.info(EmojiFormatter.format("info", "No backup files found"))
        return 0

    logger.info(f"Found {len(backup_files)} backup files")

    # Keep only the most recent N backups
    backups_to_keep = backup_files[:max_backups]
    backups_to_delete = backup_files[max_backups:]

    # Also check age-based retention
    cutoff_time = time.time() - (retention_days * 86400)

    deleted_count = 0
    for backup_file in backups_to_delete:
        # Delete if older than retention period
        if backup_file.stat().st_mtime < cutoff_time:
            logger.info(f"Deleting old backup: {backup_file.name}")

            # Use FollowWeb's safe file cleanup with retry logic
            if safe_file_cleanup(str(backup_file)):
                deleted_count += 1
            else:
                warning_msg = EmojiFormatter.format(
                    "warning", f"Failed to delete backup: {backup_file.name}"
                )
                logger.warning(warning_msg)

    # Log summary with emoji
    summary_msg = EmojiFormatter.format(
        "success",
        f"Backup cleanup: {deleted_count} deleted, {len(backups_to_keep)} retained",
    )
    logger.info(summary_msg)

    return deleted_count


def main():
    """Main execution function."""
    logger = setup_logging()
    args = parse_arguments()

    logger.info("=" * 70)
    logger.info(EmojiFormatter.format("rocket", "Freesound Backup Cleanup"))
    logger.info("=" * 70)
    logger.info(f"Checkpoint directory: {args.checkpoint_dir}")
    logger.info(f"Max backups to keep: {args.max_backups}")
    logger.info(f"Retention period: {args.retention_days} days")
    logger.info("=" * 70)

    try:
        deleted_count = cleanup_old_backups(
            checkpoint_dir=args.checkpoint_dir,
            max_backups=args.max_backups,
            retention_days=args.retention_days,
            logger=logger,
        )

        logger.info("=" * 70)
        logger.info(EmojiFormatter.format("completion", "Cleanup Complete!"))
        logger.info(f"Total backups deleted: {deleted_count}")
        logger.info("=" * 70)

        return 0

    except Exception as e:
        logger.error(EmojiFormatter.format("error", f"Cleanup failed: {e}"))
        logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
