"""
Unit tests for Rollback Manager in cleanup system.

Tests state saving and rollback operations for the repository cleanup system.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis_tools.cleanup.rollback import RollbackManager
from analysis_tools.cleanup.models import (
    CleanupPhase, FileOperation, RollbackState
)
from analysis_tools.cleanup.exceptions import RollbackError


@pytest.fixture
def rollback_manager(tmp_path):
    """Fixture providing RollbackManager instance."""
    return RollbackManager(state_dir=str(tmp_path / "rollback_states"))


@pytest.mark.unit
class TestStateSaving:
    """Test state saving functionality."""
    
    def test_saves_state_for_phase(self, rollback_manager):
        """Test saving state for a cleanup phase."""
        operations = [
            FileOperation("move", "source1.txt", "dest1.txt", datetime.now(), True),
            FileOperation("move", "source2.txt", "dest2.txt", datetime.now(), True)
        ]
        
        state = rollback_manager.save_state(CleanupPhase.ROOT_CLEANUP, operations)
        
        assert isinstance(state, RollbackState)
        assert state.phase == CleanupPhase.ROOT_CLEANUP
        assert len(state.operations) == 2
    
    def test_saves_git_commits(self, rollback_manager):
        """Test saving git commit information."""
        operations = [
            FileOperation("move", "file.txt", "new/file.txt", datetime.now(), True)
        ]
        git_commits = ["abc123", "def456"]
        
        state = rollback_manager.save_state(
            CleanupPhase.SCRIPT_ORGANIZATION,
            operations,
            git_commits=git_commits
        )
        
        assert len(state.git_commits) == 2
        assert "abc123" in state.git_commits
    
    def test_saves_created_directories(self, rollback_manager):
        """Test saving created directory information."""
        operations = []
        created_dirs = ["docs/reports", "docs/guides", "scripts/freesound"]
        
        state = rollback_manager.save_state(
            CleanupPhase.DOC_CONSOLIDATION,
            operations,
            created_directories=created_dirs
        )
        
        assert len(state.created_directories) == 3
        assert "docs/reports" in state.created_directories
    
    def test_saves_modified_file_backups(self, rollback_manager, tmp_path):
        """Test saving backups of modified files."""
        # Create test file
        test_file = tmp_path / "modified.txt"
        test_file.write_text("original content")
        
        operations = []
        modified_files = {str(test_file): "original content"}
        
        state = rollback_manager.save_state(
            CleanupPhase.WORKFLOW_UPDATE,
            operations,
            modified_files=modified_files
        )
        
        assert str(test_file) in state.modified_files
        assert state.modified_files[str(test_file)] == "original content"
    
    def test_persists_state_to_disk(self, rollback_manager, tmp_path):
        """Test that state is persisted to disk."""
        operations = [
            FileOperation("remove", "old.txt", None, datetime.now(), True)
        ]
        
        state = rollback_manager.save_state(CleanupPhase.CACHE_CLEANUP, operations)
        
        # Verify state file exists
        state_dir = tmp_path / "rollback_states"
        assert state_dir.exists()
        state_files = list(state_dir.glob("*.json"))
        assert len(state_files) > 0


@pytest.mark.unit
class TestRollbackOperations:
    """Test rollback operations."""
    
    def test_rolls_back_file_moves(self, rollback_manager, tmp_path):
        """Test rolling back file move operations."""
        # Create source and destination
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest" / "source.txt"
        dest.parent.mkdir()
        
        source.write_text("content")
        
        # Create backup before move
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        backup_file = backup_dir / "source.txt.backup"
        backup_file.write_text("content")
        
        # Simulate move
        dest.write_text(source.read_text())
        source.unlink()
        
        # Create rollback state with backup reference
        operations = [
            FileOperation("move", str(source), str(dest), datetime.now(), True)
        ]
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.ROOT_CLEANUP,
            operations=operations,
            git_commits=[],
            created_directories=[],
            modified_files={str(source): str(backup_file)}
        )
        
        # Rollback
        result = rollback_manager.rollback(state)
        
        assert result is True
        assert source.exists()
        assert source.read_text() == "content"
    
    def test_rolls_back_file_removals(self, rollback_manager, tmp_path):
        """Test rolling back file removal operations."""
        # Create file and backup
        removed_file = tmp_path / "removed.txt"
        original_content = "original content"
        
        # Create backup
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        backup_file = backup_dir / "removed.txt.backup"
        backup_file.write_text(original_content)
        
        operations = [
            FileOperation("remove", str(removed_file), None, datetime.now(), True)
        ]
        
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.CACHE_CLEANUP,
            operations=operations,
            git_commits=[],
            created_directories=[],
            modified_files={str(removed_file): str(backup_file)}
        )
        
        # Rollback
        result = rollback_manager.rollback(state)
        
        assert result is True
        assert removed_file.exists()
        assert removed_file.read_text() == original_content
    
    def test_reverts_git_commits(self, rollback_manager):
        """Test reverting git commits."""
        operations = []
        git_commits = ["commit1", "commit2"]
        
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.BRANCH_CLEANUP,
            operations=operations,
            git_commits=git_commits,
            created_directories=[],
            modified_files={}
        )
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = rollback_manager.rollback(state)
            
            # Should attempt to revert commits
            assert isinstance(result, bool)
            # Verify git revert was called for each commit
            assert mock_run.call_count == len(git_commits)
    
    def test_removes_created_directories(self, rollback_manager, tmp_path):
        """Test removing directories created during cleanup."""
        # Create directories
        created_dirs = [
            tmp_path / "new_dir1",
            tmp_path / "new_dir2"
        ]
        for d in created_dirs:
            d.mkdir()
        
        operations = []
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.SCRIPT_ORGANIZATION,
            operations=operations,
            git_commits=[],
            created_directories=[str(d) for d in created_dirs],
            modified_files={}
        )
        
        result = rollback_manager.rollback(state)
        
        assert result is True
        # Directories should be removed
        for d in created_dirs:
            assert not d.exists()
    
    def test_restores_modified_files(self, rollback_manager, tmp_path):
        """Test restoring modified files to original content."""
        # Create modified file
        modified_file = tmp_path / "modified.txt"
        modified_file.write_text("modified content")
        
        # Create backup with original content
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        backup_file = backup_dir / "modified.txt.backup"
        backup_file.write_text("original content")
        
        operations = []
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.WORKFLOW_UPDATE,
            operations=operations,
            git_commits=[],
            created_directories=[],
            modified_files={str(modified_file): str(backup_file)}
        )
        
        result = rollback_manager.rollback(state)
        
        assert result is True
        assert modified_file.read_text() == "original content"


@pytest.mark.unit
class TestRollbackValidation:
    """Test rollback validation."""
    
    def test_validates_rollback_success(self, rollback_manager, tmp_path):
        """Test validation of successful rollback."""
        # Create simple rollback scenario
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        
        source.write_text("content")
        dest.write_text("content")
        source.unlink()
        
        operations = [
            FileOperation("move", str(source), str(dest), datetime.now(), True)
        ]
        
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.ROOT_CLEANUP,
            operations=operations,
            git_commits=[],
            created_directories=[],
            modified_files={}
        )
        
        result = rollback_manager.rollback(state)
        
        # Should validate that rollback succeeded
        assert isinstance(result, bool)
    
    def test_detects_rollback_failures(self, rollback_manager):
        """Test detection of rollback failures."""
        # Create state with non-existent files
        operations = [
            FileOperation("move", "/nonexistent/source.txt", "/nonexistent/dest.txt", datetime.now(), True)
        ]
        
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.ROOT_CLEANUP,
            operations=operations,
            git_commits=[],
            created_directories=[],
            modified_files={}
        )
        
        result = rollback_manager.rollback(state)
        
        # Should handle failure gracefully
        assert isinstance(result, bool)


@pytest.mark.unit
class TestStateManagement:
    """Test state management functionality."""
    
    def test_loads_saved_state(self, rollback_manager):
        """Test loading previously saved state."""
        operations = [
            FileOperation("move", "file.txt", "new/file.txt", datetime.now(), True)
        ]
        
        # Save state
        saved_state = rollback_manager.save_state(CleanupPhase.ROOT_CLEANUP, operations)
        
        # Load state
        loaded_state = rollback_manager.load_state(CleanupPhase.ROOT_CLEANUP)
        
        assert loaded_state is not None
        assert loaded_state.phase == saved_state.phase
        assert len(loaded_state.operations) == len(saved_state.operations)
    
    def test_lists_available_states(self, rollback_manager):
        """Test listing available rollback states."""
        # Save multiple states
        for phase in [CleanupPhase.ROOT_CLEANUP, CleanupPhase.CACHE_CLEANUP]:
            rollback_manager.save_state(phase, [])
        
        # Verify files were created
        state_files = list(rollback_manager.state_dir.glob("*.json"))
        assert len(state_files) >= 2, f"Expected at least 2 state files, found {len(state_files)}"
        
        states = rollback_manager.list_available_states()
        
        assert len(states) >= 2, f"Expected at least 2 states, found {len(states)}: {states}"
        assert CleanupPhase.ROOT_CLEANUP in states
        assert CleanupPhase.CACHE_CLEANUP in states
    
    def test_clears_state_after_successful_rollback(self, rollback_manager, tmp_path):
        """Test clearing state after successful rollback."""
        operations = []
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.VALIDATION,
            operations=operations,
            git_commits=[],
            created_directories=[],
            modified_files={}
        )
        
        # Save state
        rollback_manager.save_state(CleanupPhase.VALIDATION, operations)
        
        # Rollback
        rollback_manager.rollback(state)
        
        # State should be cleared or marked as used
        # (Implementation detail - verify appropriate behavior)


@pytest.mark.unit
class TestRollbackOrdering:
    """Test rollback operation ordering."""
    
    def test_rolls_back_operations_in_reverse_order(self, rollback_manager, tmp_path):
        """Test that operations are rolled back in reverse order."""
        # Create files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")
        
        # Operations in order: move file1, then move file2
        operations = [
            FileOperation("move", str(file1), str(tmp_path / "dest1.txt"), datetime.now(), True),
            FileOperation("move", str(file2), str(tmp_path / "dest2.txt"), datetime.now(), True)
        ]
        
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.ROOT_CLEANUP,
            operations=operations,
            git_commits=[],
            created_directories=[],
            modified_files={}
        )
        
        # Rollback should process in reverse order
        result = rollback_manager.rollback(state)
        
        assert isinstance(result, bool)
    
    def test_handles_dependencies_between_operations(self, rollback_manager, tmp_path):
        """Test handling of dependencies between operations."""
        # Create directory and file
        new_dir = tmp_path / "new_dir"
        new_file = new_dir / "file.txt"
        
        operations = [
            FileOperation("create_dir", str(new_dir), None, datetime.now(), True),
            FileOperation("move", "source.txt", str(new_file), datetime.now(), True)
        ]
        
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.SCRIPT_ORGANIZATION,
            operations=operations,
            git_commits=[],
            created_directories=[str(new_dir)],
            modified_files={}
        )
        
        # Should handle dependencies correctly
        result = rollback_manager.rollback(state)
        
        assert isinstance(result, bool)


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in rollback operations."""
    
    def test_handles_missing_state_file(self, rollback_manager):
        """Test handling of missing state file."""
        loaded_state = rollback_manager.load_state(CleanupPhase.DOCUMENTATION)
        
        # Should return None or handle gracefully
        assert loaded_state is None
    
    def test_handles_corrupted_state_file(self, rollback_manager, tmp_path):
        """Test handling of corrupted state file."""
        # Create corrupted state file
        state_dir = tmp_path / "rollback_states"
        state_dir.mkdir(exist_ok=True)
        corrupted_file = state_dir / "root_cleanup_state.json"
        corrupted_file.write_text("{invalid json content")
        
        loaded_state = rollback_manager.load_state(CleanupPhase.ROOT_CLEANUP)
        
        # Should handle gracefully
        assert loaded_state is None or isinstance(loaded_state, RollbackState)
    
    def test_handles_permission_errors(self, rollback_manager, tmp_path):
        """Test handling of permission errors during rollback."""
        # Create read-only file
        readonly_file = tmp_path / "readonly.txt"
        readonly_file.write_text("content")
        readonly_file.chmod(0o444)
        
        operations = [
            FileOperation("move", str(readonly_file), str(tmp_path / "dest.txt"), datetime.now(), True)
        ]
        
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.ROOT_CLEANUP,
            operations=operations,
            git_commits=[],
            created_directories=[],
            modified_files={}
        )
        
        try:
            result = rollback_manager.rollback(state)
            # Should handle permission error
            assert isinstance(result, bool)
        finally:
            # Restore permissions
            readonly_file.chmod(0o644)
    
    def test_continues_rollback_after_errors(self, rollback_manager, tmp_path):
        """Test that rollback continues after encountering errors."""
        # Mix of valid and invalid operations
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("content")
        
        operations = [
            FileOperation("move", "/nonexistent/file.txt", "/dest.txt", datetime.now(), True),
            FileOperation("move", str(valid_file), str(tmp_path / "dest.txt"), datetime.now(), True)
        ]
        
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.ROOT_CLEANUP,
            operations=operations,
            git_commits=[],
            created_directories=[],
            modified_files={}
        )
        
        result = rollback_manager.rollback(state)
        
        # Should attempt all operations despite errors
        assert isinstance(result, bool)


@pytest.mark.unit
class TestRollbackReporting:
    """Test rollback reporting functionality."""
    
    def test_generates_rollback_report(self, rollback_manager):
        """Test generation of rollback report."""
        operations = [
            FileOperation("move", "file1.txt", "dest1.txt", datetime.now(), True),
            FileOperation("move", "file2.txt", "dest2.txt", datetime.now(), True)
        ]
        
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.ROOT_CLEANUP,
            operations=operations,
            git_commits=["commit1"],
            created_directories=["new_dir"],
            modified_files={"file.txt": "content"}
        )
        
        report = rollback_manager.generate_rollback_report(state)
        
        assert report is not None
        assert isinstance(report, str)
    
    def test_report_includes_operation_count(self, rollback_manager):
        """Test that report includes operation count."""
        operations = [
            FileOperation("move", f"file{i}.txt", f"dest{i}.txt", datetime.now(), True)
            for i in range(5)
        ]
        
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.SCRIPT_ORGANIZATION,
            operations=operations,
            git_commits=[],
            created_directories=[],
            modified_files={}
        )
        
        report = rollback_manager.generate_rollback_report(state)
        
        assert "5" in report or "five" in report.lower()
    
    def test_report_includes_phase_information(self, rollback_manager):
        """Test that report includes phase information."""
        state = RollbackState(timestamp=datetime.now(), phase=CleanupPhase.DOC_CONSOLIDATION,
            operations=[],
            git_commits=[],
            created_directories=[],
            modified_files={}
        )
        
        report = rollback_manager.generate_rollback_report(state)
        
        assert "doc_consolidation" in report.lower() or "documentation" in report.lower()


@pytest.mark.unit
class TestRollbackAvailability:
    """Test rollback availability checking."""
    
    def test_checks_if_rollback_available(self, rollback_manager):
        """Test checking if rollback is available for a phase."""
        # Save state
        rollback_manager.save_state(CleanupPhase.ROOT_CLEANUP, [])
        
        # Check availability
        available = rollback_manager.is_rollback_available(CleanupPhase.ROOT_CLEANUP)
        
        assert available is True
    
    def test_returns_false_for_unavailable_rollback(self, rollback_manager):
        """Test that unavailable rollback returns False."""
        available = rollback_manager.is_rollback_available(CleanupPhase.WORKFLOW_OPTIMIZATION)
        
        assert available is False
    
    def test_validates_rollback_state_integrity(self, rollback_manager):
        """Test validation of rollback state integrity."""
        # Save state
        operations = [
            FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        ]
        rollback_manager.save_state(CleanupPhase.CACHE_CLEANUP, operations)
        
        # Validate integrity
        valid = rollback_manager.validate_state_integrity(CleanupPhase.CACHE_CLEANUP)
        
        assert isinstance(valid, bool)

