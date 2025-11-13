"""
Checkpoint management for large-scale cleanup operations.

This module provides checkpoint functionality to enable resumption of
interrupted cleanup operations. Designed for 10K+ file operations where
long-running processes may be interrupted.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import CleanupPhase, FileOperation


class CheckpointManager:
    """
    Checkpoint manager for resumable cleanup operations.

    Features:
    - JSON-based checkpoint storage
    - Save progress every 5,000 files (configurable)
    - Resume from last checkpoint after interruption
    - Automatic checkpoint cleanup after success
    - Progress tracking with timestamps

    Usage:
        manager = CheckpointManager()
        manager.save_checkpoint(phase, 5000, 10000, last_operation)
        checkpoint = manager.load_checkpoint(phase)
        if checkpoint:
            # Resume from checkpoint
            start_index = checkpoint['completed_count']
    """

    def __init__(
        self,
        checkpoint_dir: str = ".cleanup_rollback/checkpoints",
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory for checkpoint files
            logger: Optional logger instance
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.logger = logger or logging.getLogger(__name__)

        # Ensure checkpoint directory exists
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Initialized checkpoint manager at {self.checkpoint_dir}")

    def save_checkpoint(
        self,
        phase: CleanupPhase,
        completed_count: int,
        total_count: int,
        last_operation: FileOperation,
    ) -> str:
        """
        Save progress checkpoint every 5,000 files.

        Args:
            phase: Cleanup phase
            completed_count: Number of operations completed
            total_count: Total number of operations
            last_operation: Last completed operation

        Returns:
            Path to checkpoint file
        """
        checkpoint = {
            "phase": phase.value,
            "completed_count": completed_count,
            "total_count": total_count,
            "last_operation": {
                "source": last_operation.source,
                "destination": last_operation.destination,
                "operation": last_operation.operation,
                "timestamp": last_operation.timestamp.isoformat(),
            },
            "checkpoint_timestamp": datetime.now(timezone.utc).isoformat(),
            "progress_percent": (
                (completed_count / total_count * 100) if total_count > 0 else 0
            ),
        }

        checkpoint_file = self.checkpoint_dir / f"{phase.value}_checkpoint.json"

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint, f, indent=2)

        self.logger.info(
            f"Saved checkpoint for {phase.value}: {completed_count}/{total_count} "
            f"({checkpoint['progress_percent']:.1f}%)"
        )

        return str(checkpoint_file)

    def load_checkpoint(self, phase: CleanupPhase) -> Optional[dict]:
        """
        Load checkpoint to resume from saved state.

        Args:
            phase: Cleanup phase to load

        Returns:
            Checkpoint dictionary or None if no checkpoint exists
        """
        checkpoint_file = self.checkpoint_dir / f"{phase.value}_checkpoint.json"

        if not checkpoint_file.exists():
            self.logger.debug(f"No checkpoint found for phase: {phase.value}")
            return None

        try:
            with open(checkpoint_file, "r") as f:
                checkpoint = json.load(f)

            self.logger.info(
                f"Loaded checkpoint for {phase.value}: {checkpoint['completed_count']}/{checkpoint['total_count']} "
                f"({checkpoint['progress_percent']:.1f}%)"
            )

            return checkpoint

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to load checkpoint for {phase.value}: {e}")
            return None

    def clear_checkpoint(self, phase: CleanupPhase) -> None:
        """
        Clear checkpoint after successful completion.

        Args:
            phase: Cleanup phase to clear
        """
        checkpoint_file = self.checkpoint_dir / f"{phase.value}_checkpoint.json"

        if checkpoint_file.exists():
            checkpoint_file.unlink()
            self.logger.info(f"Cleared checkpoint for phase: {phase.value}")
        else:
            self.logger.debug(f"No checkpoint to clear for phase: {phase.value}")

    def has_checkpoint(self, phase: CleanupPhase) -> bool:
        """
        Check if checkpoint exists for phase.

        Args:
            phase: Cleanup phase to check

        Returns:
            True if checkpoint exists, False otherwise
        """
        checkpoint_file = self.checkpoint_dir / f"{phase.value}_checkpoint.json"
        exists = checkpoint_file.exists()

        if exists:
            self.logger.debug(f"Checkpoint exists for phase: {phase.value}")
        else:
            self.logger.debug(f"No checkpoint for phase: {phase.value}")

        return exists

    def list_checkpoints(self) -> list[dict]:
        """
        List all existing checkpoints.

        Returns:
            List of checkpoint summaries with phase, progress, and timestamp
        """
        checkpoints = []

        for checkpoint_file in self.checkpoint_dir.glob("*_checkpoint.json"):
            try:
                with open(checkpoint_file, "r") as f:
                    checkpoint = json.load(f)

                checkpoints.append(
                    {
                        "phase": checkpoint["phase"],
                        "completed_count": checkpoint["completed_count"],
                        "total_count": checkpoint["total_count"],
                        "progress_percent": checkpoint["progress_percent"],
                        "checkpoint_timestamp": checkpoint["checkpoint_timestamp"],
                        "file": str(checkpoint_file),
                    }
                )

            except (json.JSONDecodeError, KeyError) as e:
                self.logger.warning(f"Skipping invalid checkpoint {checkpoint_file}: {e}")
                continue

        return checkpoints

    def clear_all_checkpoints(self) -> int:
        """
        Clear all checkpoints.

        Returns:
            Number of checkpoints cleared
        """
        count = 0

        for checkpoint_file in self.checkpoint_dir.glob("*_checkpoint.json"):
            checkpoint_file.unlink()
            count += 1

        self.logger.info(f"Cleared {count} checkpoint(s)")

        return count

    def get_checkpoint_info(self, phase: CleanupPhase) -> Optional[dict]:
        """
        Get checkpoint information without loading full checkpoint.

        Args:
            phase: Cleanup phase to query

        Returns:
            Checkpoint summary or None if no checkpoint exists
        """
        checkpoint_file = self.checkpoint_dir / f"{phase.value}_checkpoint.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, "r") as f:
                checkpoint = json.load(f)

            return {
                "phase": checkpoint["phase"],
                "completed_count": checkpoint["completed_count"],
                "total_count": checkpoint["total_count"],
                "progress_percent": checkpoint["progress_percent"],
                "checkpoint_timestamp": checkpoint["checkpoint_timestamp"],
            }

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to read checkpoint info for {phase.value}: {e}")
            return None

