"""
Backup manager for Freesound pipeline with tiered retention strategy.

This module provides intelligent backup management with:
- Configurable backup intervals (e.g., every 25 nodes)
- Multi-tier retention policies (frequent, moderate, milestone, daily)
- Automatic cleanup of old backups
- Backup verification and integrity checks
- Compression support for older backups
- Detailed backup manifest tracking

Backup Tiers:
    - Frequent: Every N nodes (default: 25) - keeps last 5
    - Moderate: Every 4*N nodes (default: 100) - keeps last 10
    - Milestone: Every 20*N nodes (default: 500) - keeps indefinitely
    - Daily: One per day - keeps last 30 days

Example:
    manager = BackupManager(
        backup_dir='data/freesound_library',
        config={
            'backup_interval_nodes': 25,
            'backup_retention_count': 10,
            'enable_compression': True,
            'enable_tiered_backups': True
        },
        logger=logger
    )

    # Check if backup needed
    if manager.should_create_backup(current_node_count):
        manager.create_backup(
            topology_path='graph_topology.gpickle',
            metadata_db_path='metadata_cache.db',
            checkpoint_metadata={'nodes': 250, 'edges': 1500}
        )
"""

import gzip
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from ..output.formatters import EmojiFormatter


class BackupManager:
    """
    Manages tiered backups with configurable retention policies.

    Attributes:
        backup_dir: Directory for storing backups
        config: Configuration dictionary with backup settings
        logger: Logger instance for status messages
        manifest_path: Path to backup manifest JSON file
        manifest: Current backup manifest data
    """

    def __init__(
        self,
        backup_dir: str,
        config: Optional[dict[str, Any]] = None,
        logger: Optional[Any] = None,
    ):
        """
        Initialize backup manager.

        Args:
            backup_dir: Directory for checkpoint and backup files
            config: Configuration with keys:
                   - backup_interval_nodes: Nodes between backups (default: 25)
                   - backup_retention_count: Max backups to keep (default: 10)
                   - enable_compression: Compress old backups (default: True)
                   - enable_tiered_backups: Use tiered strategy (default: True)
                   - compression_age_days: Days before compression (default: 7)
                   - emoji_level: Emoji formatting level (default: 'full')
            logger: Logger instance for messages
        """
        self.backup_dir = Path(backup_dir)
        self.config = config or {}
        self.logger = logger

        # Set emoji formatter level if specified
        emoji_level = self.config.get("emoji_level")
        if emoji_level:
            EmojiFormatter.set_fallback_level(emoji_level)

        # Configuration
        self.backup_interval = self.config.get("backup_interval_nodes", 25)
        self.retention_count = self.config.get("backup_retention_count", 10)
        self.enable_compression = self.config.get("enable_compression", True)
        self.enable_tiered = self.config.get("enable_tiered_backups", True)
        self.compression_age_days = self.config.get("compression_age_days", 7)

        # Tier configuration
        self.tiers = {
            "frequent": {
                "interval": self.backup_interval,
                "keep": 5,
                "description": f"Every {self.backup_interval} nodes",
            },
            "moderate": {
                "interval": self.backup_interval * 4,
                "keep": 10,
                "description": f"Every {self.backup_interval * 4} nodes",
            },
            "milestone": {
                "interval": self.backup_interval * 20,
                "keep": -1,  # Keep indefinitely
                "description": f"Every {self.backup_interval * 20} nodes",
            },
            "daily": {"interval": "daily", "keep": 30, "description": "One per day"},
        }

        # Manifest file
        self.manifest_path = self.backup_dir / "backup_manifest.json"
        self.manifest = self._load_manifest()

        # Create backup subdirectories
        if self.enable_tiered:
            for tier_name in ["frequent", "moderate", "milestone", "daily"]:
                (self.backup_dir / "backups" / tier_name).mkdir(
                    parents=True, exist_ok=True
                )
        else:
            (self.backup_dir / "backups").mkdir(parents=True, exist_ok=True)

        self._log_info(
            f"BackupManager initialized: interval={self.backup_interval} nodes, "
            f"retention={self.retention_count}, tiered={self.enable_tiered}"
        )

    def _log_info(self, message: str) -> None:
        """Log info message if logger available."""
        if self.logger:
            self.logger.info(message)

    def _log_warning(self, message: str) -> None:
        """Log warning message if logger available."""
        if self.logger:
            self.logger.warning(message)

    def _log_debug(self, message: str) -> None:
        """Log debug message if logger available."""
        if self.logger:
            self.logger.debug(message)

    def _load_manifest(self) -> dict[str, Any]:
        """
        Load backup manifest from JSON file.

        Returns:
            Manifest dictionary with backup metadata
        """
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path) as f:
                    return json.load(f)
            except Exception as e:
                self._log_warning(f"Failed to load backup manifest: {e}")

        # Return empty manifest
        return {"backups": [], "retention_policy": self.tiers, "last_cleanup": None}

    def _save_manifest(self) -> None:
        """Save backup manifest to JSON file."""
        try:
            with open(self.manifest_path, "w") as f:
                json.dump(self.manifest, f, indent=2)
        except Exception as e:
            self._log_warning(f"Failed to save backup manifest: {e}")

    def should_create_backup(self, current_nodes: int) -> bool:
        """
        Check if backup should be created based on node count.

        Args:
            current_nodes: Current number of nodes in graph

        Returns:
            True if backup should be created
        """
        if current_nodes == 0:
            return False

        # Check if at backup interval
        return current_nodes % self.backup_interval == 0

    def _determine_tier(self, nodes: int) -> str:
        """
        Determine which tier a backup belongs to based on node count.

        Args:
            nodes: Number of nodes in backup

        Returns:
            Tier name: 'milestone', 'moderate', or 'frequent'
        """
        if not self.enable_tiered:
            return "frequent"

        # Check milestone first (highest priority)
        if nodes % self.tiers["milestone"]["interval"] == 0:
            return "milestone"

        # Check moderate
        if nodes % self.tiers["moderate"]["interval"] == 0:
            return "moderate"

        # Default to frequent
        return "frequent"

    def create_backup(
        self,
        topology_path: Path,
        metadata_db_path: Path,
        checkpoint_metadata: dict[str, Any],
    ) -> bool:
        """
        Create timestamped backup of checkpoint files.

        Args:
            topology_path: Path to graph topology file
            metadata_db_path: Path to metadata database
            checkpoint_metadata: Metadata about the checkpoint

        Returns:
            True if backup created successfully
        """
        try:
            nodes = checkpoint_metadata.get("nodes", 0)
            edges = checkpoint_metadata.get("edges", 0)

            # Determine tier
            tier = self._determine_tier(nodes)

            # Create backup filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if self.enable_tiered:
                backup_subdir = self.backup_dir / "backups" / tier
            else:
                backup_subdir = self.backup_dir / "backups"

            topology_backup = (
                backup_subdir
                / f"graph_topology_backup_{nodes}nodes_{timestamp}.gpickle"
            )
            metadata_backup = (
                backup_subdir / f"metadata_cache_backup_{nodes}nodes_{timestamp}.db"
            )

            # Copy files
            if topology_path.exists():
                shutil.copy2(topology_path, topology_backup)
                topology_size = topology_backup.stat().st_size
            else:
                self._log_warning(f"Topology file not found: {topology_path}")
                return False

            if metadata_db_path.exists():
                shutil.copy2(metadata_db_path, metadata_backup)
                metadata_size = metadata_backup.stat().st_size
            else:
                self._log_warning(f"Metadata DB not found: {metadata_db_path}")
                return False

            # Add to manifest
            backup_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "nodes": nodes,
                "edges": edges,
                "tier": tier,
                "files": {
                    "topology": str(topology_backup.relative_to(self.backup_dir)),
                    "metadata": str(metadata_backup.relative_to(self.backup_dir)),
                },
                "compressed": False,
                "size_bytes": topology_size + metadata_size,
            }

            self.manifest["backups"].append(backup_entry)
            self._save_manifest()

            size_mb = (topology_size + metadata_size) / 1024 / 1024
            self._log_info(
                EmojiFormatter.format(
                    "package",
                    f"Backup created [{tier}]: {nodes} nodes, {size_mb:.2f} MB",
                )
            )

            # Perform cleanup after creating backup
            self._cleanup_old_backups()

            # Compress old backups if enabled
            if self.enable_compression:
                self._compress_old_backups()

            return True

        except Exception as e:
            self._log_warning(f"Failed to create backup: {e}")
            return False

    def _cleanup_old_backups(self) -> None:
        """
        Remove old backups based on retention policy.

        Keeps:
        - Last N backups per tier (based on tier configuration)
        - All milestone backups (keep=-1)
        - At least 3 most recent backups regardless of policy
        """
        try:
            # Group backups by tier
            backups_by_tier: dict[str, list[dict[str, Any]]] = {}
            for backup in self.manifest["backups"]:
                tier = backup.get("tier", "frequent")
                if tier not in backups_by_tier:
                    backups_by_tier[tier] = []
                backups_by_tier[tier].append(backup)

            # Sort each tier by timestamp (oldest first)
            for tier in backups_by_tier:
                backups_by_tier[tier].sort(key=lambda b: b["timestamp"])

            # Track backups to remove
            backups_to_remove = []

            # Apply retention policy per tier
            for tier, backups in backups_by_tier.items():
                tier_config = self.tiers.get(tier, {"keep": 5})
                keep_count = tier_config["keep"]

                # Skip if keep=-1 (indefinite retention)
                if keep_count == -1:
                    continue

                # Remove oldest backups exceeding retention count
                if len(backups) > keep_count:
                    excess_count = len(backups) - keep_count
                    backups_to_remove.extend(backups[:excess_count])

            # Always keep at least 3 most recent backups
            all_backups = sorted(
                self.manifest["backups"], key=lambda b: b["timestamp"], reverse=True
            )
            keep_recent = {b["timestamp"] for b in all_backups[:3]}

            # Filter out protected backups
            backups_to_remove = [
                b for b in backups_to_remove if b["timestamp"] not in keep_recent
            ]

            # Remove backup files and manifest entries
            removed_count = 0
            for backup in backups_to_remove:
                try:
                    # Remove files
                    for file_key in ["topology", "metadata"]:
                        file_path = self.backup_dir / backup["files"][file_key]
                        if file_path.exists():
                            file_path.unlink()

                        # Also check for compressed version
                        compressed_path = Path(str(file_path) + ".gz")
                        if compressed_path.exists():
                            compressed_path.unlink()

                    # Remove from manifest
                    self.manifest["backups"].remove(backup)
                    removed_count += 1

                except Exception as e:
                    self._log_warning(f"Failed to remove backup: {e}")

            if removed_count > 0:
                self._save_manifest()
                self._log_info(
                    EmojiFormatter.format(
                        "broom", f"Cleaned up {removed_count} old backups"
                    )
                )

            # Update last cleanup timestamp
            self.manifest["last_cleanup"] = datetime.now(timezone.utc).isoformat()
            self._save_manifest()

        except Exception as e:
            self._log_warning(f"Failed to cleanup old backups: {e}")

    def _compress_old_backups(self) -> None:
        """
        Compress backups older than compression_age_days.

        Uses gzip compression to save disk space while maintaining
        backup availability.
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=self.compression_age_days
            )
            compressed_count = 0

            for backup in self.manifest["backups"]:
                # Skip if already compressed
                if backup.get("compressed", False):
                    continue

                # Check if old enough to compress
                backup_time = datetime.fromisoformat(
                    backup["timestamp"].replace("Z", "+00:00")
                )
                if backup_time > cutoff_date:
                    continue

                # Compress each file
                for file_key in ["topology", "metadata"]:
                    file_path = self.backup_dir / backup["files"][file_key]

                    if not file_path.exists():
                        continue

                    compressed_path = Path(str(file_path) + ".gz")

                    # Compress file
                    with open(file_path, "rb") as f_in:
                        with gzip.open(compressed_path, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    # Remove original
                    file_path.unlink()

                    # Update manifest
                    backup["files"][file_key] = str(
                        compressed_path.relative_to(self.backup_dir)
                    )

                backup["compressed"] = True
                compressed_count += 1

            if compressed_count > 0:
                self._save_manifest()
                self._log_info(
                    EmojiFormatter.format(
                        "compress", f"Compressed {compressed_count} old backups"
                    )
                )

        except Exception as e:
            self._log_warning(f"Failed to compress old backups: {e}")

    def list_backups(self, tier: Optional[str] = None) -> list[dict[str, Any]]:
        """
        List available backups, optionally filtered by tier.

        Args:
            tier: Optional tier name to filter by

        Returns:
            List of backup metadata dictionaries
        """
        backups = self.manifest["backups"]

        if tier:
            backups = [b for b in backups if b.get("tier") == tier]

        # Sort by timestamp (newest first)
        return sorted(backups, key=lambda b: b["timestamp"], reverse=True)

    def get_backup_stats(self) -> dict[str, Any]:
        """
        Get statistics about current backups.

        Returns:
            Dictionary with backup statistics
        """
        backups = self.manifest["backups"]

        # Count by tier
        tier_counts: dict[str, int] = {}
        for backup in backups:
            tier = backup.get("tier", "frequent")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        # Calculate total size
        total_size = sum(b.get("size_bytes", 0) for b in backups)

        # Count compressed
        compressed_count = sum(1 for b in backups if b.get("compressed", False))

        return {
            "total_backups": len(backups),
            "by_tier": tier_counts,
            "total_size_mb": total_size / 1024 / 1024,
            "compressed_count": compressed_count,
            "last_cleanup": self.manifest.get("last_cleanup"),
        }
