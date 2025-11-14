"""
Unit tests for WorkflowOrchestrator.

Tests workflow coordination, GitHub API integration, file-based locking,
cache management, and dry-run mode functionality.
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from workflow_orchestrator import WorkflowOrchestrator


@pytest.fixture
def mock_logger():
    """Fixture providing mock logger."""
    return logging.getLogger(__name__)


@pytest.fixture
def temp_lock_dir(tmp_path):
    """Fixture providing temporary lock directory."""
    lock_dir = tmp_path / ".workflow_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    return str(lock_dir)


@pytest.fixture
def orchestrator(mock_logger, temp_lock_dir):
    """Fixture providing WorkflowOrchestrator instance."""
    return WorkflowOrchestrator(
        github_token="test_token",
        repository="owner/repo",
        logger=mock_logger,
        lock_dir=temp_lock_dir,
        dry_run=False
    )


@pytest.fixture
def dry_run_orchestrator(mock_logger, temp_lock_dir):
    """Fixture providing WorkflowOrchestrator in dry-run mode."""
    return WorkflowOrchestrator(
        github_token="test_token",
        repository="owner/repo",
        logger=mock_logger,
        lock_dir=temp_lock_dir,
        dry_run=True
    )


@pytest.mark.unit
class TestWorkflowOrchestratorInit:
    """Test WorkflowOrchestrator initialization."""
    
    def test_init_creates_lock_directory(self, mock_logger, tmp_path):
        """Test that initialization creates lock directory."""
        lock_dir = tmp_path / ".test_locks"
        
        orchestrator = WorkflowOrchestrator(
            github_token="token",
            repository="owner/repo",
            logger=mock_logger,
            lock_dir=str(lock_dir),
            dry_run=False
        )
        
        assert lock_dir.exists()
        assert orchestrator.lock_dir == lock_dir
    
    def test_init_dry_run_no_directory(self, mock_logger, tmp_path):
        """Test that dry-run mode doesn't create lock directory."""
        lock_dir = tmp_path / ".test_locks_dry"
        
        orchestrator = WorkflowOrchestrator(
            github_token="token",
            repository="owner/repo",
            logger=mock_logger,
            lock_dir=str(lock_dir),
            dry_run=True
        )
        
        # Directory should not be created in dry-run mode
        assert not lock_dir.exists()
    
    def test_init_conflict_matrix(self, orchestrator):
        """Test that conflict matrix is properly initialized."""
        assert 'freesound-nightly-pipeline' in orchestrator.conflict_matrix
        assert 'freesound-quick-validation' in orchestrator.conflict_matrix
        assert 'freesound-full-validation' in orchestrator.conflict_matrix
        
        # Check conflicts are bidirectional
        assert 'freesound-quick-validation' in orchestrator.conflict_matrix['freesound-nightly-pipeline']
        assert 'freesound-nightly-pipeline' in orchestrator.conflict_matrix['freesound-quick-validation']
    
    def test_init_cache_empty(self, orchestrator):
        """Test that status cache is initialized empty."""
        assert orchestrator._status_cache == {}
        assert orchestrator._cache_ttl == 30


@pytest.mark.unit
class TestCheckWorkflowStatus:
    """Test check_workflow_status method."""
    
    @patch('workflow_orchestrator.requests.get')
    def test_check_status_running_workflow(self, mock_get, orchestrator):
        """Test checking status of running workflow."""
        # Mock successful API response with running workflow
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_count': 1,
            'workflow_runs': [{
                'id': 12345,
                'status': 'in_progress',
                'conclusion': None,
                'created_at': '2025-11-11T10:00:00Z',
                'html_url': 'https://github.com/owner/repo/actions/runs/12345'
            }]
        }
        mock_get.return_value = mock_response
        
        status = orchestrator.check_workflow_status('freesound-nightly-pipeline')
        
        assert status is not None
        assert status['run_id'] == 12345
        assert status['status'] == 'in_progress'
        assert status['conclusion'] is None
        assert status['html_url'] == 'https://github.com/owner/repo/actions/runs/12345'
    
    @patch('workflow_orchestrator.requests.get')
    def test_check_status_no_running_workflow(self, mock_get, orchestrator):
        """Test checking status when no workflow is running."""
        # Mock API response with no running workflows
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_count': 0,
            'workflow_runs': []
        }
        mock_get.return_value = mock_response
        
        status = orchestrator.check_workflow_status('freesound-nightly-pipeline')
        
        assert status is None
    
    @patch('workflow_orchestrator.requests.get')
    def test_check_status_rate_limited(self, mock_get, orchestrator):
        """Test handling of 429 rate limit response."""
        # Mock 429 rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response
        
        status = orchestrator.check_workflow_status('freesound-nightly-pipeline')
        
        # Should return None and log warning
        assert status is None
    
    @patch('workflow_orchestrator.requests.get')
    def test_check_status_404_not_found(self, mock_get, orchestrator):
        """Test handling of 404 not found response."""
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        status = orchestrator.check_workflow_status('nonexistent-workflow')
        
        # Should return None and log warning
        assert status is None
    
    @patch('workflow_orchestrator.requests.get')
    def test_check_status_server_error(self, mock_get, orchestrator):
        """Test handling of 5xx server error."""
        # Mock 500 server error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_response
        
        status = orchestrator.check_workflow_status('freesound-nightly-pipeline')
        
        # Should return None and log warning
        assert status is None
    
    @patch('workflow_orchestrator.requests.get')
    def test_check_status_uses_cache(self, mock_get, orchestrator):
        """Test that status cache is used to reduce API calls."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_count': 1,
            'workflow_runs': [{
                'id': 12345,
                'status': 'in_progress',
                'conclusion': None,
                'created_at': '2025-11-11T10:00:00Z',
                'html_url': 'https://github.com/owner/repo/actions/runs/12345'
            }]
        }
        mock_get.return_value = mock_response
        
        # First call - should hit API
        status1 = orchestrator.check_workflow_status('freesound-nightly-pipeline')
        assert mock_get.call_count == 1
        
        # Second call within TTL - should use cache
        status2 = orchestrator.check_workflow_status('freesound-nightly-pipeline')
        assert mock_get.call_count == 1  # No additional API call
        
        assert status1 == status2
    
    @patch('workflow_orchestrator.requests.get')
    def test_check_status_cache_expiration(self, mock_get, orchestrator):
        """Test that cache expires after TTL."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_count': 0,
            'workflow_runs': []
        }
        mock_get.return_value = mock_response
        
        # First call
        orchestrator.check_workflow_status('freesound-nightly-pipeline')
        assert mock_get.call_count == 1
        
        # Manually expire cache
        cache_key = 'freesound-nightly-pipeline'
        cached_status, cached_time = orchestrator._status_cache[cache_key]
        expired_time = cached_time - timedelta(seconds=orchestrator._cache_ttl + 1)
        orchestrator._status_cache[cache_key] = (cached_status, expired_time)
        
        # Second call after expiration - should hit API again
        orchestrator.check_workflow_status('freesound-nightly-pipeline')
        assert mock_get.call_count == 2
    
    def test_check_status_dry_run(self, dry_run_orchestrator):
        """Test that dry-run mode doesn't make API calls."""
        status = dry_run_orchestrator.check_workflow_status('freesound-nightly-pipeline')
        
        # Should return None without making API call
        assert status is None


@pytest.mark.unit
class TestIsWorkflowRunning:
    """Test is_workflow_running method."""
    
    @patch.object(WorkflowOrchestrator, 'check_workflow_status')
    def test_is_running_true(self, mock_check, orchestrator):
        """Test is_workflow_running returns True when workflow is running."""
        mock_check.return_value = {'run_id': 12345, 'status': 'in_progress'}
        
        assert orchestrator.is_workflow_running('freesound-nightly-pipeline') is True
    
    @patch.object(WorkflowOrchestrator, 'check_workflow_status')
    def test_is_running_false(self, mock_check, orchestrator):
        """Test is_workflow_running returns False when workflow is not running."""
        mock_check.return_value = None
        
        assert orchestrator.is_workflow_running('freesound-nightly-pipeline') is False


@pytest.mark.unit
class TestGetConflictingWorkflows:
    """Test get_conflicting_workflows method."""
    
    def test_get_conflicts_nightly_pipeline(self, orchestrator):
        """Test getting conflicts for nightly pipeline."""
        conflicts = orchestrator.get_conflicting_workflows('freesound-nightly-pipeline')
        
        assert 'freesound-quick-validation' in conflicts
        assert 'freesound-full-validation' in conflicts
    
    def test_get_conflicts_quick_validation(self, orchestrator):
        """Test getting conflicts for quick validation."""
        conflicts = orchestrator.get_conflicting_workflows('freesound-quick-validation')
        
        assert 'freesound-nightly-pipeline' in conflicts
        assert 'freesound-full-validation' in conflicts
    
    def test_get_conflicts_unknown_workflow(self, orchestrator):
        """Test getting conflicts for unknown workflow."""
        conflicts = orchestrator.get_conflicting_workflows('unknown-workflow')
        
        assert conflicts == []


@pytest.mark.unit
class TestWaitForWorkflow:
    """Test wait_for_workflow method."""
    
    @patch.object(WorkflowOrchestrator, 'is_workflow_running')
    def test_wait_completes_immediately(self, mock_is_running, orchestrator):
        """Test waiting when workflow completes immediately."""
        mock_is_running.return_value = False
        
        result = orchestrator.wait_for_workflow('freesound-nightly-pipeline', timeout=60)
        
        assert result is True
    
    @patch.object(WorkflowOrchestrator, 'is_workflow_running')
    @patch('workflow_orchestrator.time.sleep')
    def test_wait_completes_after_polling(self, mock_sleep, mock_is_running, orchestrator):
        """Test waiting when workflow completes after polling."""
        # Simulate workflow running for 2 polls, then completing
        mock_is_running.side_effect = [True, True, False]
        
        result = orchestrator.wait_for_workflow('freesound-nightly-pipeline', timeout=120, poll_interval=10)
        
        assert result is True
        assert mock_sleep.call_count == 2
    
    @patch.object(WorkflowOrchestrator, 'is_workflow_running')
    @patch('workflow_orchestrator.time.sleep')
    @patch('workflow_orchestrator.time.time')
    def test_wait_timeout(self, mock_time, mock_sleep, mock_is_running, orchestrator):
        """Test waiting when timeout is reached."""
        # Simulate workflow still running after timeout
        mock_is_running.return_value = True
        
        # Mock time to simulate timeout (need extra values for logging calls)
        # Each iteration needs: start_time check, elapsed calc, remaining calc, and logging calls
        mock_time.side_effect = [0] + [i for i in range(10, 100, 10) for _ in range(5)]
        
        result = orchestrator.wait_for_workflow('freesound-nightly-pipeline', timeout=60, poll_interval=10)
        
        assert result is False
    
    def test_wait_dry_run(self, dry_run_orchestrator):
        """Test that dry-run mode returns True immediately."""
        result = dry_run_orchestrator.wait_for_workflow('freesound-nightly-pipeline', timeout=60)
        
        assert result is True


@pytest.mark.unit
class TestCheckAndWaitForConflicts:
    """Test check_and_wait_for_conflicts method."""
    
    @patch.object(WorkflowOrchestrator, 'is_workflow_running')
    def test_no_conflicts(self, mock_is_running, orchestrator):
        """Test when no conflicting workflows are running."""
        mock_is_running.return_value = False
        
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-nightly-pipeline')
        
        assert can_proceed is True
        assert reason == "No conflicts"
    
    @patch.object(WorkflowOrchestrator, 'is_workflow_running')
    @patch.object(WorkflowOrchestrator, 'check_workflow_status')
    @patch.object(WorkflowOrchestrator, 'wait_for_workflow')
    def test_conflict_resolves(self, mock_wait, mock_check, mock_is_running, orchestrator):
        """Test when conflicting workflow resolves within timeout."""
        # First check: validation is running
        # Second check (after wait): validation is not running
        mock_is_running.side_effect = [True, False]
        mock_check.return_value = {'html_url': 'https://github.com/owner/repo/actions/runs/12345'}
        mock_wait.return_value = True
        
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-nightly-pipeline')
        
        assert can_proceed is True
        assert reason == "No conflicts"
    
    @patch.object(WorkflowOrchestrator, 'is_workflow_running')
    @patch.object(WorkflowOrchestrator, 'check_workflow_status')
    @patch.object(WorkflowOrchestrator, 'wait_for_workflow')
    def test_conflict_timeout(self, mock_wait, mock_check, mock_is_running, orchestrator):
        """Test when conflicting workflow doesn't resolve within timeout."""
        mock_is_running.return_value = True
        mock_check.return_value = {'html_url': 'https://github.com/owner/repo/actions/runs/12345'}
        mock_wait.return_value = False  # Timeout
        
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-nightly-pipeline', timeout=60)
        
        assert can_proceed is False
        assert "Timeout" in reason
        assert "freesound-quick-validation" in reason or "freesound-full-validation" in reason


@pytest.mark.unit
class TestAcquireLock:
    """Test acquire_lock method."""
    
    def test_acquire_lock_success(self, orchestrator, temp_lock_dir):
        """Test successful lock acquisition."""
        result = orchestrator.acquire_lock('test_lock', timeout=10)
        
        assert result is True
        
        # Verify lock file exists
        lock_file = Path(temp_lock_dir) / "test_lock.lock"
        assert lock_file.exists()
        
        # Verify lock file contains metadata
        content = lock_file.read_text()
        assert len(content) > 0
    
    def test_acquire_lock_already_locked(self, orchestrator, temp_lock_dir):
        """Test lock acquisition when lock already exists."""
        # Create existing lock
        lock_file = Path(temp_lock_dir) / "test_lock.lock"
        lock_file.write_text(f"{datetime.now(timezone.utc).isoformat()}\ntest_run_id\n")
        
        # Try to acquire with short timeout
        result = orchestrator.acquire_lock('test_lock', timeout=2)
        
        assert result is False
    
    def test_acquire_lock_stale_cleanup(self, orchestrator, temp_lock_dir):
        """Test that stale locks are cleaned up."""
        # Create stale lock (3 hours old)
        lock_file = Path(temp_lock_dir) / "test_lock.lock"
        lock_file.write_text(f"{datetime.now(timezone.utc).isoformat()}\ntest_run_id\n")
        
        # Make it stale by modifying mtime
        stale_time = time.time() - (3 * 3600)  # 3 hours ago
        os.utime(lock_file, (stale_time, stale_time))
        
        # Should clean up stale lock and acquire
        result = orchestrator.acquire_lock('test_lock', timeout=10)
        
        assert result is True
    
    def test_acquire_lock_dry_run(self, dry_run_orchestrator, temp_lock_dir):
        """Test that dry-run mode doesn't create lock files."""
        result = dry_run_orchestrator.acquire_lock('test_lock', timeout=10)
        
        assert result is True
        
        # Verify no lock file was created
        lock_file = Path(temp_lock_dir) / "test_lock.lock"
        assert not lock_file.exists()


@pytest.mark.unit
class TestReleaseLock:
    """Test release_lock method."""
    
    def test_release_lock_success(self, orchestrator, temp_lock_dir):
        """Test successful lock release."""
        # Create lock
        lock_file = Path(temp_lock_dir) / "test_lock.lock"
        lock_file.write_text("test content")
        
        orchestrator.release_lock('test_lock')
        
        # Verify lock file is removed
        assert not lock_file.exists()
    
    def test_release_lock_nonexistent(self, orchestrator, temp_lock_dir):
        """Test releasing nonexistent lock (should not error)."""
        # Should not raise exception
        orchestrator.release_lock('nonexistent_lock')
    
    def test_release_lock_dry_run(self, dry_run_orchestrator, temp_lock_dir):
        """Test that dry-run mode doesn't remove lock files."""
        # Create lock
        lock_file = Path(temp_lock_dir) / "test_lock.lock"
        lock_file.write_text("test content")
        
        dry_run_orchestrator.release_lock('test_lock')
        
        # Verify lock file still exists (dry-run doesn't actually release)
        assert lock_file.exists()


@pytest.mark.unit
class TestStaleLockDetection:
    """Test stale lock detection and cleanup."""
    
    def test_is_stale_lock_fresh(self, orchestrator, temp_lock_dir):
        """Test that fresh locks are not considered stale."""
        lock_file = Path(temp_lock_dir) / "test_lock.lock"
        lock_file.write_text("test content")
        
        is_stale = orchestrator._is_stale_lock(lock_file, max_age_hours=2)
        
        assert is_stale is False
    
    def test_is_stale_lock_old(self, orchestrator, temp_lock_dir):
        """Test that old locks are considered stale."""
        lock_file = Path(temp_lock_dir) / "test_lock.lock"
        lock_file.write_text("test content")
        
        # Make it 3 hours old
        stale_time = time.time() - (3 * 3600)
        os.utime(lock_file, (stale_time, stale_time))
        
        is_stale = orchestrator._is_stale_lock(lock_file, max_age_hours=2)
        
        assert is_stale is True
    
    def test_is_stale_lock_nonexistent(self, orchestrator, temp_lock_dir):
        """Test handling of nonexistent lock file."""
        lock_file = Path(temp_lock_dir) / "nonexistent.lock"
        
        is_stale = orchestrator._is_stale_lock(lock_file)
        
        # Should return False (not raise exception)
        assert is_stale is False
    
    def test_cleanup_stale_lock(self, orchestrator, temp_lock_dir):
        """Test cleanup of stale lock."""
        lock_file = Path(temp_lock_dir) / "test_lock.lock"
        lock_file.write_text("test content")
        
        orchestrator._cleanup_stale_lock(lock_file)
        
        # Verify lock file is removed
        assert not lock_file.exists()
    
    def test_cleanup_stale_lock_nonexistent(self, orchestrator, temp_lock_dir):
        """Test cleanup of nonexistent lock (should not error)."""
        lock_file = Path(temp_lock_dir) / "nonexistent.lock"
        
        # Should not raise exception
        orchestrator._cleanup_stale_lock(lock_file)


@pytest.mark.unit
class TestDryRunMode:
    """Test dry-run mode functionality."""
    
    def test_dry_run_check_workflow_status(self, dry_run_orchestrator):
        """Test that dry-run mode doesn't make API calls."""
        status = dry_run_orchestrator.check_workflow_status('freesound-nightly-pipeline')
        
        assert status is None
    
    def test_dry_run_wait_for_workflow(self, dry_run_orchestrator):
        """Test that dry-run mode returns immediately."""
        result = dry_run_orchestrator.wait_for_workflow('freesound-nightly-pipeline', timeout=60)
        
        assert result is True
    
    def test_dry_run_acquire_lock(self, dry_run_orchestrator, temp_lock_dir):
        """Test that dry-run mode doesn't create lock files."""
        result = dry_run_orchestrator.acquire_lock('test_lock', timeout=10)
        
        assert result is True
        
        lock_file = Path(temp_lock_dir) / "test_lock.lock"
        assert not lock_file.exists()
    
    def test_dry_run_release_lock(self, dry_run_orchestrator, temp_lock_dir):
        """Test that dry-run mode doesn't remove lock files."""
        # Create lock
        lock_file = Path(temp_lock_dir) / "test_lock.lock"
        lock_file.write_text("test content")
        
        dry_run_orchestrator.release_lock('test_lock')
        
        # Lock should still exist
        assert lock_file.exists()
