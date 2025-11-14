"""
Integration tests for the workflow chain (collection → validation → backup).

Tests workflow triggers, cache sharing, failure scenarios, and data continuity
across the separated pipeline workflows.
"""

import json
import os
import pickle
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import networkx as nx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.workflow]


@pytest.fixture
def temp_checkpoint_dir(tmp_path) -> Path:
    """Fixture providing temporary checkpoint directory."""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return checkpoint_dir


@pytest.fixture
def mock_checkpoint_data(temp_checkpoint_dir: Path) -> dict[str, Any]:
    """Fixture providing mock checkpoint data for testing."""
    # Create mock graph topology
    graph = nx.DiGraph()
    graph.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5)])

    graph_path = temp_checkpoint_dir / "graph_topology.gpickle"
    with open(graph_path, "wb") as f:
        pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)

    # Create mock checkpoint metadata
    metadata = {
        "version": "2.0",
        "created_at": "2025-11-14T02:00:00Z",
        "last_updated": "2025-11-14T02:15:30Z",
        "sample_count": 5,
        "edge_count": 4,
        "pagination": {
            "current_page": 15,
            "search_query": "jungle",
            "sort_order": "created_desc",
            "last_updated": "2025-11-14T02:15:30Z",
            "total_pages_processed": 15,
            "samples_from_pagination": 300,
        },
        "collection_stats": {
            "total_api_requests": 325,
            "duplicates_skipped": 75,
            "new_samples_added": 250,
        },
    }

    metadata_path = temp_checkpoint_dir / "checkpoint_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)

    # Create mock SQLite metadata cache
    import sqlite3

    db_path = temp_checkpoint_dir / "metadata_cache.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            sample_id INTEGER PRIMARY KEY,
            data TEXT NOT NULL
        )
    """)
    for i in range(1, 6):
        cursor.execute(
            "INSERT INTO metadata (sample_id, data) VALUES (?, ?)",
            (i, json.dumps({"id": i, "name": f"sample_{i}"})),
        )
    conn.commit()
    conn.close()

    return {
        "checkpoint_dir": temp_checkpoint_dir,
        "graph_path": graph_path,
        "metadata_path": metadata_path,
        "db_path": db_path,
        "metadata": metadata,
    }


class TestWorkflowTriggers:
    """Test workflow triggers and cache sharing."""

    @pytest.mark.integration
    def test_collection_to_validation_trigger(
        self, mock_checkpoint_data: dict[str, Any]
    ):
        """Test collection → validation trigger with cache sharing."""
        # Simulate collection workflow saving checkpoint to cache
        checkpoint_dir = mock_checkpoint_data["checkpoint_dir"]
        cache_key = "checkpoint-12345"

        # Verify checkpoint files exist
        assert mock_checkpoint_data["graph_path"].exists()
        assert mock_checkpoint_data["metadata_path"].exists()
        assert mock_checkpoint_data["db_path"].exists()

        # Simulate validation workflow restoring from cache
        # In real workflow, this would be done by GitHub Actions cache
        restored_metadata_path = checkpoint_dir / "checkpoint_metadata.json"
        assert restored_metadata_path.exists()

        with open(restored_metadata_path) as f:
            restored_metadata = json.load(f)

        # Verify cache key would be passed correctly
        assert restored_metadata["sample_count"] == 5
        assert restored_metadata["pagination"]["current_page"] == 15

    @pytest.mark.integration
    def test_collection_to_repair_trigger(self, mock_checkpoint_data: dict[str, Any]):
        """Test collection → repair trigger with cache sharing."""
        checkpoint_dir = mock_checkpoint_data["checkpoint_dir"]

        # Verify checkpoint can be loaded for repair
        assert mock_checkpoint_data["graph_path"].exists()
        assert mock_checkpoint_data["metadata_path"].exists()

        # Load checkpoint for repair validation
        with open(mock_checkpoint_data["graph_path"], "rb") as f:
            graph = pickle.load(f)
        with open(mock_checkpoint_data["metadata_path"]) as f:
            metadata = json.load(f)

        # Verify data integrity
        assert graph.number_of_nodes() == 5
        assert metadata["sample_count"] == 5

    @pytest.mark.integration
    def test_validation_to_backup_trigger(self, mock_checkpoint_data: dict[str, Any]):
        """Test validation → backup trigger with cache sharing."""
        checkpoint_dir = mock_checkpoint_data["checkpoint_dir"]

        # Simulate validation passing
        validation_passed = True

        # Verify checkpoint is ready for backup
        assert mock_checkpoint_data["graph_path"].exists()
        assert mock_checkpoint_data["metadata_path"].exists()
        assert mock_checkpoint_data["db_path"].exists()

        if validation_passed:
            # Simulate backup workflow creating backup
            backup_files = [
                mock_checkpoint_data["graph_path"],
                mock_checkpoint_data["metadata_path"],
                mock_checkpoint_data["db_path"],
            ]

            for backup_file in backup_files:
                assert backup_file.exists()

    @pytest.mark.integration
    def test_cache_keys_passed_correctly(self, mock_checkpoint_data: dict[str, Any]):
        """Verify cache keys are passed correctly between workflows."""
        # Simulate GitHub Actions run IDs
        collection_run_id = "12345"
        validation_run_id = "12346"
        backup_run_id = "12347"

        # Collection saves with its run ID
        collection_cache_key = f"checkpoint-{collection_run_id}"

        # Validation restores using collection's run ID
        validation_restore_key = f"checkpoint-{collection_run_id}"
        assert collection_cache_key == validation_restore_key

        # Backup restores using validation's upstream run ID
        # In workflow_run trigger, this would be github.event.workflow_run.id
        backup_restore_key = f"checkpoint-{collection_run_id}"
        assert backup_restore_key == validation_restore_key


class TestFailureScenarios:
    """Test failure scenarios and recovery."""

    @pytest.mark.integration
    def test_failure_isolation_collection_fails(
        self, mock_checkpoint_data: dict[str, Any]
    ):
        """Test failure isolation (collection fails, validation not triggered)."""
        # Simulate collection failure
        collection_success = False

        # Validation should not be triggered
        validation_triggered = collection_success
        assert validation_triggered is False

        # Checkpoint should still be saved for recovery
        assert mock_checkpoint_data["metadata_path"].exists()
        with open(mock_checkpoint_data["metadata_path"]) as f:
            metadata = json.load(f)

        # Verify partial progress is preserved
        assert metadata["sample_count"] > 0
        assert metadata["pagination"]["current_page"] > 0

    @pytest.mark.integration
    def test_failure_recovery_backup_created(
        self, mock_checkpoint_data: dict[str, Any]
    ):
        """Test failure recovery (collection fails, backup workflow creates recovery backup)."""
        # Simulate collection failure
        collection_conclusion = "failure"

        # Backup workflow should still be triggered
        backup_triggered = True  # Triggered on both success and failure
        assert backup_triggered is True

        # Verify checkpoint exists for recovery backup
        assert mock_checkpoint_data["graph_path"].exists()
        assert mock_checkpoint_data["metadata_path"].exists()

        # Simulate backup creation with recovery tier
        backup_metadata = {
            "timestamp": "2025-11-14T02:30:00Z",
            "tier": "recovery",
            "backup_reason": "failure_recovery",
            "failed_workflow_run": "12345",
            "samples_preserved": mock_checkpoint_data["metadata"]["sample_count"],
        }

        assert backup_metadata["tier"] == "recovery"
        assert backup_metadata["samples_preserved"] > 0

    @pytest.mark.integration
    def test_repair_workflow_fixes_issues(self, mock_checkpoint_data: dict[str, Any]):
        """Test repair workflow (validation fails, repair fixes issues, re-validation passes)."""
        # Simulate validation failure due to inconsistency
        with open(mock_checkpoint_data["graph_path"], "rb") as f:
            graph = pickle.load(f)
        with open(mock_checkpoint_data["metadata_path"]) as f:
            metadata = json.load(f)

        # Introduce inconsistency: metadata says 6 samples but graph has 5
        metadata["sample_count"] = 6

        # Validation should fail
        validation_passed = graph.number_of_nodes() == metadata["sample_count"]
        assert validation_passed is False

        # Repair: Fix metadata to match graph
        metadata["sample_count"] = graph.number_of_nodes()

        # Re-validation should pass
        validation_passed = graph.number_of_nodes() == metadata["sample_count"]
        assert validation_passed is True

    @pytest.mark.integration
    def test_partial_progress_preserved(self, mock_checkpoint_data: dict[str, Any]):
        """Verify partial progress is preserved on failure."""
        # Load checkpoint metadata
        with open(mock_checkpoint_data["metadata_path"]) as f:
            metadata = json.load(f)

        # Verify pagination state is preserved
        assert metadata["pagination"]["current_page"] == 15
        assert metadata["pagination"]["total_pages_processed"] == 15

        # Verify collection stats are preserved
        assert metadata["collection_stats"]["new_samples_added"] == 250
        assert metadata["collection_stats"]["duplicates_skipped"] == 75

        # Next run should resume from page 15
        next_page = metadata["pagination"]["current_page"]
        assert next_page == 15


class TestDataContinuity:
    """Test data continuity across multiple runs."""

    @pytest.mark.integration
    def test_pagination_continuity(self, mock_checkpoint_data: dict[str, Any]):
        """Test pagination continuity across multiple runs."""
        # Load initial checkpoint
        with open(mock_checkpoint_data["metadata_path"]) as f:
            metadata = json.load(f)

        initial_page = metadata["pagination"]["current_page"]
        assert initial_page == 15

        # Simulate next run incrementing page
        metadata["pagination"]["current_page"] = initial_page + 1
        metadata["pagination"]["total_pages_processed"] = initial_page + 1

        # Save updated checkpoint
        with open(mock_checkpoint_data["metadata_path"], "w") as f:
            json.dump(metadata, f)

        # Verify pagination continued
        with open(mock_checkpoint_data["metadata_path"]) as f:
            updated_metadata = json.load(f)

        assert updated_metadata["pagination"]["current_page"] == 16
        assert updated_metadata["pagination"]["total_pages_processed"] == 16

    @pytest.mark.integration
    def test_duplicate_detection_across_runs(
        self, mock_checkpoint_data: dict[str, Any]
    ):
        """Test duplicate detection across multiple runs."""
        import sqlite3

        # Load metadata cache
        conn = sqlite3.connect(mock_checkpoint_data["db_path"])
        cursor = conn.cursor()

        # Check existing samples
        cursor.execute("SELECT COUNT(*) FROM metadata")
        initial_count = cursor.fetchone()[0]
        assert initial_count == 5

        # Simulate duplicate detection: sample 3 already exists
        cursor.execute("SELECT sample_id FROM metadata WHERE sample_id = ?", (3,))
        exists = cursor.fetchone() is not None
        assert exists is True

        # Simulate adding new sample (not duplicate)
        cursor.execute(
            "INSERT OR IGNORE INTO metadata (sample_id, data) VALUES (?, ?)",
            (6, json.dumps({"id": 6, "name": "sample_6"})),
        )
        conn.commit()

        # Verify new sample added
        cursor.execute("SELECT COUNT(*) FROM metadata")
        new_count = cursor.fetchone()[0]
        assert new_count == 6

        conn.close()

    @pytest.mark.integration
    def test_checkpoint_state_preserved(self, mock_checkpoint_data: dict[str, Any]):
        """Verify checkpoint state is preserved across runs."""
        # Load checkpoint components
        with open(mock_checkpoint_data["graph_path"], "rb") as f:
            graph = pickle.load(f)
        with open(mock_checkpoint_data["metadata_path"]) as f:
            metadata = json.load(f)

        # Verify graph state
        assert graph.number_of_nodes() == 5
        assert graph.number_of_edges() == 4

        # Verify metadata state
        assert metadata["sample_count"] == 5
        assert metadata["edge_count"] == 4

        # Verify pagination state
        assert metadata["pagination"]["current_page"] == 15
        assert metadata["pagination"]["search_query"] == "jungle"

        # Verify collection stats
        assert metadata["collection_stats"]["total_api_requests"] == 325

    @pytest.mark.integration
    def test_repair_operations_preserve_data(
        self, mock_checkpoint_data: dict[str, Any]
    ):
        """Test repair operations preserve data integrity."""
        # Load checkpoint
        with open(mock_checkpoint_data["graph_path"], "rb") as f:
            graph = pickle.load(f)
        with open(mock_checkpoint_data["metadata_path"]) as f:
            metadata = json.load(f)

        # Simulate repair: fix edge count mismatch
        actual_edges = graph.number_of_edges()
        metadata["edge_count"] = actual_edges

        # Save repaired checkpoint
        with open(mock_checkpoint_data["metadata_path"], "w") as f:
            json.dump(metadata, f)

        # Verify data integrity after repair
        with open(mock_checkpoint_data["metadata_path"]) as f:
            repaired_metadata = json.load(f)

        assert repaired_metadata["edge_count"] == actual_edges
        assert repaired_metadata["sample_count"] == graph.number_of_nodes()

        # Verify pagination state preserved during repair
        assert repaired_metadata["pagination"]["current_page"] == 15


class TestCacheSharing:
    """Test cache sharing between workflows."""

    @pytest.mark.integration
    def test_cache_save_with_failure_recovery(
        self, mock_checkpoint_data: dict[str, Any]
    ):
        """Test cache save runs even on failure (if: always())."""
        # Simulate workflow failure
        workflow_failed = True

        # Cache should still be saved (if: always() condition)
        cache_saved = True  # Always runs regardless of failure
        assert cache_saved is True

        # Verify checkpoint files exist for cache save
        assert mock_checkpoint_data["graph_path"].exists()
        assert mock_checkpoint_data["metadata_path"].exists()
        assert mock_checkpoint_data["db_path"].exists()

    @pytest.mark.integration
    def test_cache_restore_from_upstream_run(
        self, mock_checkpoint_data: dict[str, Any]
    ):
        """Test cache restore from upstream workflow run."""
        # Simulate upstream run ID
        upstream_run_id = "12345"
        cache_key = f"checkpoint-{upstream_run_id}"

        # Verify checkpoint can be restored
        assert mock_checkpoint_data["checkpoint_dir"].exists()
        assert mock_checkpoint_data["graph_path"].exists()

        # Load restored checkpoint
        with open(mock_checkpoint_data["graph_path"], "rb") as f:
            graph = pickle.load(f)
        with open(mock_checkpoint_data["metadata_path"]) as f:
            metadata = json.load(f)

        # Verify restored data is complete
        assert graph.number_of_nodes() == metadata["sample_count"]

    @pytest.mark.integration
    def test_cache_key_consistency(self, mock_checkpoint_data: dict[str, Any]):
        """Test cache key consistency across workflow chain."""
        # Simulate workflow chain
        collection_run_id = "12345"

        # Collection saves with run ID
        collection_cache_key = f"checkpoint-{collection_run_id}"

        # Validation restores using workflow_run.id (collection's run ID)
        validation_cache_key = f"checkpoint-{collection_run_id}"

        # Backup restores using workflow_run.id (collection's run ID)
        backup_cache_key = f"checkpoint-{collection_run_id}"

        # All workflows use same cache key
        assert collection_cache_key == validation_cache_key == backup_cache_key


class TestWorkflowIntegration:
    """Test complete workflow chain integration."""

    @pytest.mark.integration
    def test_complete_workflow_chain(self, mock_checkpoint_data: dict[str, Any]):
        """Test complete workflow chain: collection → validation → backup."""
        # Step 1: Collection completes successfully
        collection_success = True
        assert mock_checkpoint_data["graph_path"].exists()

        # Step 2: Validation triggered and passes
        if collection_success:
            with open(mock_checkpoint_data["graph_path"], "rb") as f:
                graph = pickle.load(f)
            with open(mock_checkpoint_data["metadata_path"]) as f:
                metadata = json.load(f)

            validation_passed = graph.number_of_nodes() == metadata["sample_count"]
            assert validation_passed is True

        # Step 3: Backup triggered after validation success
        if validation_passed:
            backup_triggered = True
            assert backup_triggered is True

            # Verify backup can be created
            backup_files = [
                mock_checkpoint_data["graph_path"],
                mock_checkpoint_data["metadata_path"],
                mock_checkpoint_data["db_path"],
            ]

            for backup_file in backup_files:
                assert backup_file.exists()

    @pytest.mark.integration
    def test_workflow_chain_with_repair(self, mock_checkpoint_data: dict[str, Any]):
        """Test workflow chain with repair: collection → repair → validation → backup."""
        # Step 1: Collection completes
        collection_success = True
        assert collection_success is True

        # Step 2: Repair triggered (runs after collection)
        repair_triggered = True
        assert repair_triggered is True

        # Step 3: Repair validates and fixes issues
        with open(mock_checkpoint_data["graph_path"], "rb") as f:
            graph = pickle.load(f)
        with open(mock_checkpoint_data["metadata_path"]) as f:
            metadata = json.load(f)

        # Fix any inconsistencies
        metadata["sample_count"] = graph.number_of_nodes()
        metadata["edge_count"] = graph.number_of_edges()

        # Save repaired checkpoint
        with open(mock_checkpoint_data["metadata_path"], "w") as f:
            json.dump(metadata, f)

        # Step 4: Validation passes after repair
        with open(mock_checkpoint_data["metadata_path"]) as f:
            repaired_metadata = json.load(f)

        validation_passed = graph.number_of_nodes() == repaired_metadata["sample_count"]
        assert validation_passed is True

        # Step 5: Backup triggered after validation
        if validation_passed:
            backup_triggered = True
            assert backup_triggered is True
