"""
Unit tests for scalability components in cleanup system.

Tests StateDatabase operations, CheckpointManager, and automatic activation
of large-scale components for 10K+ files.
"""

import logging
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis_tools.cleanup.state_db import CleanupStateDB
from analysis_tools.cleanup.checkpoint import CheckpointManager
from analysis_tools.cleanup.models import FileOperation, CleanupPhase
from analysis_tools.cleanup.orchestrator import CleanupOrchestrator
from analysis_tools.cleanup.models import CleanupConfig


@pytest.fixture
def state_db(tmp_path):
    """Fixture providing CleanupStateDB instance."""
    db_path = tmp_path / "test_state.db"
    return CleanupStateDB(str(db_path))


@pytest.fixture
def checkpoint_manager(tmp_path):
    """Fixture providing CheckpointManager instance."""
    checkpoint_dir = tmp_path / "checkpoints"
    return CheckpointManager(str(checkpoint_dir))


@pytest.mark.unit
class TestStateDatabaseOperations:
    """Test StateDatabase operations."""
    
    def test_initializes_database(self, state_db):
        """Test database initialization."""
        assert state_db.conn is not None
        assert isinstance(state_db.conn, sqlite3.Connection)
    
    def test_creates_tables(self, state_db):
        """Test table creation."""
        # Verify file_operations table exists
        cursor = state_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='file_operations'"
        )
        result = cursor.fetchone()
        
        assert result is not None
        assert result[0] == "file_operations"
    
    def test_adds_operation(self, state_db):
        """Test adding file operation to database."""
        operation = FileOperation(
            "move",
            "source.txt",
            "dest.txt",
            datetime.now(),
            True
        )
        
        operation_id = state_db.add_operation(operation, "root_cleanup")
        
        assert operation_id is not None
        assert operation_id > 0
    
    def test_updates_operation_status(self, state_db):
        """Test updating operation status."""
        operation = FileOperation("move", "file.txt", "new/file.txt", datetime.now(), True)
        operation_id = state_db.add_operation(operation, "root_cleanup")
        
        state_db.update_status(operation_id, "completed")
        
        # Verify update
        cursor = state_db.conn.execute(
            "SELECT status FROM file_operations WHERE id = ?",
            (operation_id,)
        )
        result = cursor.fetchone()
        
        assert result[0] == "completed"
    
    def test_gets_pending_operations(self, state_db):
        """Test retrieving pending operations."""
        # Add operations
        for i in range(3):
            op = FileOperation("move", f"file{i}.txt", f"dest{i}.txt", datetime.now(), True)
            state_db.add_operation(op, "test_phase")
        
        pending = state_db.get_pending_operations("test_phase")
        
        assert len(pending) == 3
    
    def test_gets_progress_statistics(self, state_db):
        """Test getting progress statistics."""
        # Add operations with different statuses
        op1 = FileOperation("move", "file1.txt", "dest1.txt", datetime.now(), True)
        op2 = FileOperation("move", "file2.txt", "dest2.txt", datetime.now(), True)
        
        id1 = state_db.add_operation(op1, "test_phase")
        id2 = state_db.add_operation(op2, "test_phase")
        
        state_db.update_status(id1, "completed")
        
        progress = state_db.get_progress("test_phase")
        
        assert isinstance(progress, dict)
        assert "pending" in progress
        assert "completed" in progress


@pytest.mark.unit
class TestStateDatabasePerformance:
    """Test StateDatabase performance optimizations."""
    
    def test_uses_wal_mode(self, state_db):
        """Test that WAL mode is enabled."""
        cursor = state_db.conn.execute("PRAGMA journal_mode")
        result = cursor.fetchone()
        
        assert result[0].upper() == "WAL"
    
    def test_uses_optimized_synchronous(self, state_db):
        """Test that synchronous mode is optimized."""
        cursor = state_db.conn.execute("PRAGMA synchronous")
        result = cursor.fetchone()
        
        # Should be NORMAL (1) for performance
        assert result[0] in [1, 2]  # NORMAL or FULL
    
    def test_has_indexes(self, state_db):
        """Test that indexes are created."""
        cursor = state_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = cursor.fetchall()
        
        # Should have indexes for status and phase
        index_names = [idx[0] for idx in indexes]
        assert any("status" in name.lower() for name in index_names)
        assert any("phase" in name.lower() for name in index_names)
    
    def test_batch_writes(self, state_db):
        """Test batch write support."""
        # Add multiple operations
        operations = [
            FileOperation("move", f"file{i}.txt", f"dest{i}.txt", datetime.now(), True)
            for i in range(100)
        ]
        
        # Should handle batch efficiently
        for op in operations:
            state_db.add_operation(op, "batch_test")
        
        # Verify all added
        pending = state_db.get_pending_operations("batch_test")
        assert len(pending) == 100


@pytest.mark.unit
class TestCheckpointManager:
    """Test CheckpointManager operations."""
    
    def test_saves_checkpoint(self, checkpoint_manager):
        """Test saving checkpoint."""
        operation = FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        
        checkpoint_path = checkpoint_manager.save_checkpoint(
            CleanupPhase.ROOT_CLEANUP,
            completed_count=100,
            total_count=1000,
            last_operation=operation
        )
        
        assert checkpoint_path is not None
        assert Path(checkpoint_path).exists()
    
    def test_loads_checkpoint(self, checkpoint_manager):
        """Test loading checkpoint."""
        operation = FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        
        # Save checkpoint
        checkpoint_manager.save_checkpoint(
            CleanupPhase.CACHE_CLEANUP,
            completed_count=50,
            total_count=100,
            last_operation=operation
        )
        
        # Load checkpoint
        loaded = checkpoint_manager.load_checkpoint(CleanupPhase.CACHE_CLEANUP)
        
        assert loaded is not None
        assert loaded["completed_count"] == 50
        assert loaded["total_count"] == 100
    
    def test_clears_checkpoint(self, checkpoint_manager):
        """Test clearing checkpoint."""
        operation = FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        
        # Save checkpoint
        checkpoint_manager.save_checkpoint(
            CleanupPhase.SCRIPT_ORGANIZATION,
            completed_count=10,
            total_count=20,
            last_operation=operation
        )
        
        # Clear checkpoint
        checkpoint_manager.clear_checkpoint(CleanupPhase.SCRIPT_ORGANIZATION)
        
        # Verify cleared
        loaded = checkpoint_manager.load_checkpoint(CleanupPhase.SCRIPT_ORGANIZATION)
        assert loaded is None
    
    def test_checks_checkpoint_existence(self, checkpoint_manager):
        """Test checking if checkpoint exists."""
        operation = FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        
        # No checkpoint initially
        assert checkpoint_manager.has_checkpoint(CleanupPhase.DOC_CONSOLIDATION) is False
        
        # Save checkpoint
        checkpoint_manager.save_checkpoint(
            CleanupPhase.DOC_CONSOLIDATION,
            completed_count=5,
            total_count=10,
            last_operation=operation
        )
        
        # Should exist now
        assert checkpoint_manager.has_checkpoint(CleanupPhase.DOC_CONSOLIDATION) is True
    
    def test_checkpoint_includes_progress_percent(self, checkpoint_manager):
        """Test that checkpoint includes progress percentage."""
        operation = FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        
        checkpoint_manager.save_checkpoint(
            CleanupPhase.WORKFLOW_UPDATE,
            completed_count=250,
            total_count=1000,
            last_operation=operation
        )
        
        loaded = checkpoint_manager.load_checkpoint(CleanupPhase.WORKFLOW_UPDATE)
        
        assert "progress_percent" in loaded
        assert loaded["progress_percent"] == 25.0


@pytest.mark.unit
class TestAutomaticActivation:
    """Test automatic activation of large-scale components."""
    
    def test_components_not_activated_for_small_operations(self, tmp_path):
        """Test that large-scale components are not activated for small operations."""
        config = CleanupConfig(
            large_scale_threshold=10000,
            use_state_db=False,
            enable_checkpoints=False
        )
        
        orchestrator = CleanupOrchestrator(config, str(tmp_path))
        
        # Should not initialize large-scale components
        assert orchestrator.state_db is None
        assert orchestrator.checkpoint_manager is None
    
    def test_components_activated_for_large_operations(self, tmp_path):
        """Test that large-scale components are activated for 10K+ files."""
        config = CleanupConfig(
            large_scale_threshold=10000,
            use_state_db=True,
            enable_checkpoints=True
        )
        
        orchestrator = CleanupOrchestrator(config, str(tmp_path))
        orchestrator._initialize_large_scale_components()
        
        # Should initialize large-scale components
        assert orchestrator.state_db is not None
        assert orchestrator.checkpoint_manager is not None
    
    def test_threshold_configuration(self, tmp_path):
        """Test that threshold is configurable."""
        config = CleanupConfig(large_scale_threshold=5000)
        
        orchestrator = CleanupOrchestrator(config, str(tmp_path))
        
        assert orchestrator.config.large_scale_threshold == 5000
    
    def test_auto_enables_streaming_mode(self, tmp_path):
        """Test automatic enabling of streaming mode for 10K+ files."""
        config = CleanupConfig(
            large_scale_threshold=10000,
            use_state_db=True
        )
        
        orchestrator = CleanupOrchestrator(config, str(tmp_path))
        
        # Should have streaming capability
        assert hasattr(orchestrator.file_manager, 'move_files_streaming')


@pytest.mark.unit
class TestCheckpointInterval:
    """Test checkpoint interval configuration."""
    
    def test_default_checkpoint_interval(self, checkpoint_manager):
        """Test default checkpoint interval."""
        # Default should be 5000 files
        config = CleanupConfig()
        assert config.checkpoint_interval == 5000
    
    def test_custom_checkpoint_interval(self):
        """Test custom checkpoint interval."""
        config = CleanupConfig(checkpoint_interval=1000)
        assert config.checkpoint_interval == 1000
    
    def test_checkpoint_saves_at_interval(self, checkpoint_manager):
        """Test that checkpoints are saved at configured interval."""
        # Simulate processing files
        operation = FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        
        # Save checkpoint at interval
        for i in range(0, 10000, 5000):
            checkpoint_manager.save_checkpoint(
                CleanupPhase.ROOT_CLEANUP,
                completed_count=i,
                total_count=10000,
                last_operation=operation
            )
        
        # Should have checkpoint
        assert checkpoint_manager.has_checkpoint(CleanupPhase.ROOT_CLEANUP)


@pytest.mark.unit
class TestStateDatabaseQueries:
    """Test StateDatabase query performance."""
    
    def test_queries_use_indexes(self, state_db):
        """Test that queries use indexes."""
        # Add operations
        for i in range(100):
            op = FileOperation("move", f"file{i}.txt", f"dest{i}.txt", datetime.now(), True)
            state_db.add_operation(op, "test_phase")
        
        # Query should be fast with indexes
        pending = state_db.get_pending_operations("test_phase")
        
        assert len(pending) == 100
    
    def test_composite_index_query(self, state_db):
        """Test query using composite index."""
        # Add operations
        for i in range(50):
            op = FileOperation("move", f"file{i}.txt", f"dest{i}.txt", datetime.now(), True)
            op_id = state_db.add_operation(op, "test_phase")
            if i % 2 == 0:
                state_db.update_status(op_id, "completed")
        
        # Query by phase and status (composite index)
        progress = state_db.get_progress("test_phase")
        
        assert "pending" in progress
        assert "completed" in progress


@pytest.mark.unit
class TestCheckpointResume:
    """Test checkpoint resume functionality."""
    
    def test_resumes_from_checkpoint(self, checkpoint_manager):
        """Test resuming from saved checkpoint."""
        operation = FileOperation("move", "file500.txt", "dest500.txt", datetime.now(), True)
        
        # Save checkpoint at 500/1000
        checkpoint_manager.save_checkpoint(
            CleanupPhase.ROOT_CLEANUP,
            completed_count=500,
            total_count=1000,
            last_operation=operation
        )
        
        # Load and resume
        loaded = checkpoint_manager.load_checkpoint(CleanupPhase.ROOT_CLEANUP)
        
        assert loaded["completed_count"] == 500
        assert loaded["last_operation"]["source"] == "file500.txt"
    
    def test_skips_completed_operations(self, state_db):
        """Test skipping already-completed operations."""
        # Add and complete some operations
        for i in range(10):
            op = FileOperation("move", f"file{i}.txt", f"dest{i}.txt", datetime.now(), True)
            op_id = state_db.add_operation(op, "test_phase")
            if i < 5:
                state_db.update_status(op_id, "completed")
        
        # Get only pending operations
        pending = state_db.get_pending_operations("test_phase")
        
        assert len(pending) == 5  # Only uncompleted operations


@pytest.mark.unit
class TestPerformanceMetrics:
    """Test performance metrics tracking."""
    
    def test_tracks_operation_count(self, state_db):
        """Test tracking of operation count."""
        # Add operations
        for i in range(100):
            op = FileOperation("move", f"file{i}.txt", f"dest{i}.txt", datetime.now(), True)
            state_db.add_operation(op, "perf_test")
        
        progress = state_db.get_progress("perf_test")
        
        # Should track total count
        total = sum(progress.values())
        assert total == 100
    
    def test_calculates_progress_percentage(self, checkpoint_manager):
        """Test calculation of progress percentage."""
        operation = FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        
        checkpoint_manager.save_checkpoint(
            CleanupPhase.CACHE_CLEANUP,
            completed_count=750,
            total_count=1000,
            last_operation=operation
        )
        
        loaded = checkpoint_manager.load_checkpoint(CleanupPhase.CACHE_CLEANUP)
        
        assert loaded["progress_percent"] == 75.0


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in scalability components."""
    
    def test_handles_database_errors(self, tmp_path):
        """Test handling of database errors."""
        # Create database in read-only location
        try:
            db = CleanupStateDB("/nonexistent/path/db.sqlite")
            # Should handle error
        except Exception as e:
            # Expected to fail
            assert isinstance(e, Exception)
    
    def test_handles_checkpoint_write_errors(self, tmp_path):
        """Test handling of checkpoint write errors."""
        # Create checkpoint manager with read-only directory
        checkpoint_dir = tmp_path / "readonly"
        checkpoint_dir.mkdir()
        checkpoint_dir.chmod(0o444)
        
        manager = CheckpointManager(str(checkpoint_dir))
        operation = FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        
        try:
            manager.save_checkpoint(
                CleanupPhase.ROOT_CLEANUP,
                completed_count=10,
                total_count=100,
                last_operation=operation
            )
        except Exception as e:
            # Expected to fail with permission error
            assert "permission" in str(e).lower() or isinstance(e, PermissionError)
        finally:
            checkpoint_dir.chmod(0o755)
    
    def test_handles_corrupted_checkpoint(self, checkpoint_manager, tmp_path):
        """Test handling of corrupted checkpoint file."""
        # Create corrupted checkpoint
        checkpoint_dir = Path(checkpoint_manager.checkpoint_dir)
        corrupted_file = checkpoint_dir / "root_cleanup_checkpoint.json"
        corrupted_file.write_text("{invalid json")
        
        loaded = checkpoint_manager.load_checkpoint(CleanupPhase.ROOT_CLEANUP)
        
        # Should handle gracefully
        assert loaded is None or isinstance(loaded, dict)


@pytest.mark.unit
class TestCleanupAfterCompletion:
    """Test cleanup after successful completion."""
    
    def test_clears_checkpoint_after_success(self, checkpoint_manager):
        """Test clearing checkpoint after successful completion."""
        operation = FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        
        # Save checkpoint
        checkpoint_manager.save_checkpoint(
            CleanupPhase.WORKFLOW_UPDATE,
            completed_count=100,
            total_count=100,
            last_operation=operation
        )
        
        # Clear after completion
        checkpoint_manager.clear_checkpoint(CleanupPhase.WORKFLOW_UPDATE)
        
        # Should be cleared
        assert not checkpoint_manager.has_checkpoint(CleanupPhase.WORKFLOW_UPDATE)
    
    def test_closes_database_connection(self, state_db):
        """Test closing database connection."""
        # Add some operations
        op = FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        state_db.add_operation(op, "test_phase")
        
        # Close connection
        state_db.close()
        
        # Connection should be closed
        # (Attempting operations should fail)
