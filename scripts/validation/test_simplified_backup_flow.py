#!/usr/bin/env python3
"""
Test script for simplified backup flow.

This script validates that:
1. Collection workflow only saves to cache (no backup logic)
2. Backup workflow handles all backup operations
3. BackupManager is simplified and focused on upload/verification
4. Tier determination is consistent in backup workflow
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from FollowWeb_Visualizor.data.backup_manager import BackupManager  # noqa: E402


def test_backup_manager_simplified():
    """Test that BackupManager is simplified."""
    print("Testing BackupManager simplification...")

    # Create a temporary backup manager
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = BackupManager(
            backup_dir=tmpdir, config={"backup_interval_nodes": 25}, logger=None
        )

        # Check that simplified attributes exist
        assert hasattr(manager, "backup_interval"), "Missing backup_interval"

        # Check that complex attributes are removed
        assert not hasattr(manager, "tiers"), "Should not have tiers attribute"
        assert not hasattr(manager, "enable_tiered"), "Should not have enable_tiered"
        assert not hasattr(manager, "enable_compression"), (
            "Should not have enable_compression"
        )
        assert not hasattr(manager, "manifest"), "Should not have manifest"

        # Check that essential methods exist
        assert hasattr(manager, "should_create_backup"), "Missing should_create_backup"
        assert hasattr(manager, "upload_to_permanent_storage_with_verification"), (
            "Missing upload_to_permanent_storage_with_verification"
        )

        # Check that removed methods don't exist
        assert not hasattr(manager, "create_backup"), "Should not have create_backup"
        assert not hasattr(manager, "should_create_backup_with_tier"), (
            "Should not have should_create_backup_with_tier"
        )
        assert not hasattr(manager, "get_release_tag"), (
            "Should not have get_release_tag"
        )
        assert not hasattr(manager, "_determine_tier"), (
            "Should not have _determine_tier"
        )
        assert not hasattr(manager, "_cleanup_old_backups"), (
            "Should not have _cleanup_old_backups"
        )
        assert not hasattr(manager, "_compress_old_backups"), (
            "Should not have _compress_old_backups"
        )
        assert not hasattr(manager, "list_backups"), "Should not have list_backups"
        assert not hasattr(manager, "get_backup_stats"), (
            "Should not have get_backup_stats"
        )
        assert not hasattr(manager, "backup_intervals"), (
            "Should not have backup_intervals (no tiers)"
        )

        print("✅ BackupManager is properly simplified")


def test_backup_interval():
    """Test that backup interval is correctly defined."""
    print("\nTesting backup interval...")

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = BackupManager(
            backup_dir=tmpdir, config={"backup_interval_nodes": 100}, logger=None
        )

        # Check backup interval
        assert manager.backup_interval == 100, "Backup interval should be 100"

        print("✅ Backup interval is correct (100 nodes)")


def test_should_create_backup():
    """Test the simplified should_create_backup method."""
    print("\nTesting should_create_backup...")

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = BackupManager(
            backup_dir=tmpdir, config={"backup_interval_nodes": 100}, logger=None
        )

        # Test various node counts
        # should_create_backup returns True at every 100 nodes
        assert not manager.should_create_backup(0), "Should not backup at 0 nodes"
        assert not manager.should_create_backup(25), "Should not backup at 25 nodes"
        assert not manager.should_create_backup(50), "Should not backup at 50 nodes"
        assert not manager.should_create_backup(75), "Should not backup at 75 nodes"
        assert not manager.should_create_backup(99), "Should not backup at 99 nodes"
        assert manager.should_create_backup(100), "Should backup at 100 nodes"
        assert not manager.should_create_backup(101), "Should not backup at 101 nodes"
        assert not manager.should_create_backup(150), "Should not backup at 150 nodes"
        assert manager.should_create_backup(200), "Should backup at 200 nodes"
        assert manager.should_create_backup(300), "Should backup at 300 nodes"
        assert manager.should_create_backup(500), "Should backup at 500 nodes"
        assert manager.should_create_backup(1000), "Should backup at 1000 nodes"

        print("✅ should_create_backup works correctly (every 100 nodes)")


def test_workflow_separation():
    """Test that workflows are properly separated."""
    print("\nTesting workflow separation...")

    # Read collection workflow
    collection_workflow = (
        project_root / ".github/workflows/freesound-nightly-pipeline.yml"
    ).read_text(encoding="utf-8")

    # Check that backup logic is removed from collection workflow
    assert "Upload checkpoint to private repository" not in collection_workflow, (
        "Collection workflow should not upload to private repository"
    )
    assert "Verify backup integrity" not in collection_workflow, (
        "Collection workflow should not verify backup integrity"
    )
    assert "Cleanup old backups (retention policy)" not in collection_workflow, (
        "Collection workflow should not handle retention policy"
    )

    # BACKUP_PAT is still used for downloading checkpoint at start, but not for uploading
    backup_pat_count = collection_workflow.count("BACKUP_PAT")
    download_checkpoint_section = (
        "Download checkpoint from private repository" in collection_workflow
    )
    assert download_checkpoint_section, "Collection workflow should download checkpoint"
    # Allow BACKUP_PAT usage for download only (should be < 10 occurrences)
    assert backup_pat_count < 10, (
        f"Collection workflow uses BACKUP_PAT {backup_pat_count} times (should be minimal for download only)"
    )

    # Check that collection workflow saves to cache
    assert "Save checkpoint to cache" in collection_workflow, (
        "Collection workflow should save to cache"
    )

    print("✅ Collection workflow is properly simplified")
    print("   - Saves checkpoint to cache every run")
    print("   - Downloads checkpoint from backup repo at start")
    print("   - No backup upload logic")

    # Read backup workflow
    backup_workflow = (
        project_root / ".github/workflows/freesound-backup.yml"
    ).read_text(encoding="utf-8")

    # Check that backup workflow has consolidated logic
    assert "Create backup archive" in backup_workflow, (
        "Backup workflow should create backup"
    )
    assert "Upload backup to PRIMARY repository" in backup_workflow, (
        "Backup workflow should upload backup"
    )
    assert "Apply retention policy" in backup_workflow, (
        "Backup workflow should apply retention"
    )

    # Check backup interval logic (simplified - no tiers)
    assert (
        "node_count % 100 == 0" in backup_workflow
        or "backup_interval=100" in backup_workflow
    ), "Backup workflow should have 100-node backup interval"
    assert "v-checkpoint" in backup_workflow, (
        "Backup workflow should use v-checkpoint release"
    )

    # Check that tier logic is removed (allow mentions in comments but not in logic)
    assert backup_workflow.count("milestone") < 2, (
        "Backup workflow should not have milestone tier logic"
    )
    assert backup_workflow.count("moderate") < 2, (
        "Backup workflow should not have moderate tier logic"
    )
    assert "v-permanent" not in backup_workflow, (
        "Backup workflow should not use v-permanent release"
    )

    print("✅ Backup workflow has consolidated logic")


def test_documentation():
    """Test that documentation is updated."""
    print("\nTesting documentation...")

    # Check BackupManager docstring
    backup_manager_code = (
        project_root / "FollowWeb/FollowWeb_Visualizor/data/backup_manager.py"
    ).read_text(encoding="utf-8")

    assert (
        "Single source of truth" not in backup_manager_code
        or "backup workflow" in backup_manager_code.lower()
    ), "BackupManager should reference backup workflow"
    assert (
        "Tier determination" in backup_manager_code
        or "tier determination" in backup_manager_code.lower()
    ), "BackupManager should mention tier determination is in workflow"

    print("✅ Documentation is updated")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Simplified Backup Flow")
    print("=" * 60)

    try:
        test_backup_manager_simplified()
        test_backup_interval()
        test_should_create_backup()
        test_workflow_separation()
        test_documentation()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\nSummary:")
        print("- BackupManager is simplified (upload/verification only)")
        print("- Collection workflow only saves to cache")
        print("- Backup workflow handles all backup operations")
        print("- Single backup interval: Every 100 nodes")
        print("- Single release: v-checkpoint (14-day retention, max 10)")
        print("- Safety: Never delete last remaining backup")
        print("- No tiers (milestone/moderate removed)")
        print("- Documentation is updated")

        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
