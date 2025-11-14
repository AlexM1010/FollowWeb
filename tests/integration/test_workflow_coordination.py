"""
Integration tests for workflow coordination.

Tests full coordination flow with multiple workflows, timeout scenarios,
GitHub API rate limiting, file-based locking, and concurrent operations.
"""

import logging
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from workflow_orchestrator import WorkflowOrchestrator


@pytest.fixture
def mock_logger():
    """Fixture providing mock logger."""
    return logging.getLogger(__name__)


@pytest.fixture
def temp_lock_dir():
    """Fixture providing temporary lock directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


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


@pytest.mark.integration
class TestFullCoordinationFlow:
    """Test full coordination flow with multiple workflows."""
    
    @patch('workflow_orchestrator.requests.get')
    def test_coordination_no_conflicts(self, mock_get, orchestrator):
        """Test full coordination when no workflows are running."""
        # Mock API response: no workflows running
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_count': 0,
            'workflow_runs': []
        }
        mock_get.return_value = mock_response
        
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-nightly-pipeline')
        
        assert can_proceed is True
        assert reason == "No conflicts"
    
    @patch('workflow_orchestrator.requests.get')
    @patch('workflow_orchestrator.time.sleep')
    def test_coordination_with_conflict_resolution(self, mock_sleep, mock_get, orchestrator):
        """Test coordination when conflicting workflow completes."""
        # First call: validation is running
        # Subsequent calls: validation completes
        responses = [
            # First check: validation running
            {
                'total_count': 1,
                'workflow_runs': [{
                    'id': 12345,
                    'status': 'in_progress',
                    'conclusion': None,
                    'created_at': '2025-11-11T10:00:00Z',
                    'html_url': 'https://github.com/owner/repo/actions/runs/12345'
                }]
            },
            # Second check (during wait): still running
            {
                'total_count': 1,
                'workflow_runs': [{
                    'id': 12345,
                    'status': 'in_progress',
                    'conclusion': None,
                    'created_at': '2025-11-11T10:00:00Z',
                    'html_url': 'https://github.com/owner/repo/actions/runs/12345'
                }]
            },
            # Third check: completed
            {
                'total_count': 0,
                'workflow_runs': []
            },
            # Fourth check (for other conflicting workflow): not running
            {
                'total_count': 0,
                'workflow_runs': []
            }
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = responses
        mock_get.return_value = mock_response
        
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-nightly-pipeline', timeout=120)
        
        assert can_proceed is True
        assert reason == "No conflicts"
    
    @patch('workflow_orchestrator.requests.get')
    @patch('workflow_orchestrator.time.sleep')
    @patch('workflow_orchestrator.time.time')
    def test_coordination_with_timeout(self, mock_time, mock_sleep, mock_get, orchestrator):
        """Test coordination when conflicting workflow doesn't complete."""
        # Mock workflow always running
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
        
        # Mock time to simulate timeout
        mock_time.side_effect = [0] + [i for i in range(10, 200, 10) for _ in range(5)]
        
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-nightly-pipeline', timeout=60)
        
        assert can_proceed is False
        assert "Timeout" in reason
        assert "12345" in reason or "freesound-quick-validation" in reason or "freesound-full-validation" in reason


@pytest.mark.integration
class TestGitHubAPIRateLimiting:
    """Test GitHub API rate limiting handling."""
    
    @patch('workflow_orchestrator.requests.get')
    def test_rate_limit_handling(self, mock_get, orchestrator):
        """Test handling of rate limit responses."""
        # First call: rate limited
        # Second call: success
        responses = [
            Mock(status_code=429),
            Mock(status_code=200, json=lambda: {'total_count': 0, 'workflow_runs': []})
        ]
        mock_get.side_effect = responses
        
        # First call should return None due to rate limit
        status1 = orchestrator.check_workflow_status('freesound-nightly-pipeline')
        assert status1 is None
        
        # Second call should succeed
        status2 = orchestrator.check_workflow_status('freesound-quick-validation')
        assert status2 is None  # No workflows running
    
    @patch('workflow_orchestrator.requests.get')
    def test_rate_limit_during_coordination(self, mock_get, orchestrator):
        """Test coordination continues when rate limited."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response
        
        # Should proceed with caution when rate limited
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-nightly-pipeline')
        
        # Should still proceed (no conflicts detected due to rate limit)
        assert can_proceed is True


@pytest.mark.integration
class TestFileBasedLocking:
    """Test file-based locking fallback mechanism."""
    
    def test_lock_acquisition_and_release(self, orchestrator, temp_lock_dir):
        """Test full lock lifecycle."""
        # Acquire lock
        acquired = orchestrator.acquire_lock('test_checkpoint', timeout=10)
        assert acquired is True
        
        # Verify lock file exists
        lock_file = Path(temp_lock_dir) / "test_checkpoint.lock"
        assert lock_file.exists()
        
        # Release lock
        orchestrator.release_lock('test_checkpoint')
        
        # Verify lock file removed
        assert not lock_file.exists()
    
    def test_lock_prevents_concurrent_access(self, orchestrator, temp_lock_dir):
        """Test that lock prevents concurrent access."""
        # First orchestrator acquires lock
        acquired1 = orchestrator.acquire_lock('checkpoint', timeout=5)
        assert acquired1 is True
        
        # Second orchestrator cannot acquire same lock
        orchestrator2 = WorkflowOrchestrator(
            github_token="test_token",
            repository="owner/repo",
            lock_dir=temp_lock_dir,
            dry_run=False
        )
        
        acquired2 = orchestrator2.acquire_lock('checkpoint', timeout=2)
        assert acquired2 is False
        
        # Release first lock
        orchestrator.release_lock('checkpoint')
        
        # Now second orchestrator can acquire
        acquired3 = orchestrator2.acquire_lock('checkpoint', timeout=5)
        assert acquired3 is True
        
        orchestrator2.release_lock('checkpoint')
    
    def test_stale_lock_cleanup_integration(self, orchestrator, temp_lock_dir):
        """Test that stale locks are automatically cleaned up."""
        # Create stale lock
        lock_file = Path(temp_lock_dir) / "checkpoint.lock"
        lock_file.write_text(f"{datetime.now(timezone.utc).isoformat()}\ntest_run_id\n")
        
        # Make it stale (3 hours old)
        stale_time = time.time() - (3 * 3600)
        os.utime(lock_file, (stale_time, stale_time))
        
        # Should clean up and acquire
        acquired = orchestrator.acquire_lock('checkpoint', timeout=10)
        assert acquired is True
        
        # Verify new lock exists
        assert lock_file.exists()
        
        # Verify it's fresh (not stale)
        assert not orchestrator._is_stale_lock(lock_file)
        
        orchestrator.release_lock('checkpoint')


@pytest.mark.integration
class TestConcurrentLockAcquisition:
    """Test concurrent lock acquisition attempts."""
    
    def test_concurrent_lock_attempts(self, temp_lock_dir):
        """Test multiple threads attempting to acquire same lock."""
        results = []
        
        def acquire_lock_thread(thread_id):
            """Thread function to acquire lock."""
            orchestrator = WorkflowOrchestrator(
                github_token="test_token",
                repository="owner/repo",
                lock_dir=temp_lock_dir,
                dry_run=False
            )
            
            acquired = orchestrator.acquire_lock('shared_lock', timeout=5)
            results.append((thread_id, acquired))
            
            if acquired:
                # Hold lock briefly
                time.sleep(0.5)
                orchestrator.release_lock('shared_lock')
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=acquire_lock_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify only one thread acquired lock initially
        successful_acquisitions = [r for r in results if r[1] is True]
        
        # At least one should succeed (others may timeout)
        assert len(successful_acquisitions) >= 1
    
    def test_sequential_lock_acquisition(self, temp_lock_dir):
        """Test sequential lock acquisition by multiple orchestrators."""
        orchestrators = [
            WorkflowOrchestrator(
                github_token="test_token",
                repository="owner/repo",
                lock_dir=temp_lock_dir,
                dry_run=False
            )
            for _ in range(3)
        ]
        
        # Each orchestrator should be able to acquire and release
        for i, orch in enumerate(orchestrators):
            acquired = orch.acquire_lock('sequential_lock', timeout=5)
            assert acquired is True, f"Orchestrator {i} failed to acquire lock"
            
            orch.release_lock('sequential_lock')


@pytest.mark.integration
class TestWorkflowStepOutputs:
    """Test that step outputs are set correctly for GitHub Actions."""
    
    @patch('workflow_orchestrator.requests.get')
    def test_step_output_can_proceed(self, mock_get, orchestrator):
        """Test step output when workflow can proceed."""
        # Mock no conflicts
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_count': 0,
            'workflow_runs': []
        }
        mock_get.return_value = mock_response
        
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-nightly-pipeline')
        
        # Verify outputs that would be used in GitHub Actions
        assert can_proceed is True
        assert isinstance(reason, str)
        assert reason == "No conflicts"
    
    @patch('workflow_orchestrator.requests.get')
    @patch('workflow_orchestrator.time.sleep')
    @patch('workflow_orchestrator.time.time')
    def test_step_output_skip(self, mock_time, mock_sleep, mock_get, orchestrator):
        """Test step output when workflow should skip."""
        # Mock conflict that doesn't resolve
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
        
        # Mock time to simulate timeout
        mock_time.side_effect = [0] + [i for i in range(10, 200, 10) for _ in range(5)]
        
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-nightly-pipeline', timeout=60)
        
        # Verify outputs
        assert can_proceed is False
        assert isinstance(reason, str)
        assert len(reason) > 0
        assert "Timeout" in reason


@pytest.mark.integration
class TestMultipleWorkflowScenarios:
    """Test various multi-workflow scenarios."""
    
    @patch('workflow_orchestrator.requests.get')
    def test_nightly_pipeline_checks_both_validations(self, mock_get, orchestrator):
        """Test that nightly pipeline checks both validation workflows."""
        # Mock no workflows running
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_count': 0,
            'workflow_runs': []
        }
        mock_get.return_value = mock_response
        
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-nightly-pipeline')
        
        assert can_proceed is True
        
        # Verify both validation workflows were checked
        calls = mock_get.call_args_list
        urls = [call[0][0] for call in calls]
        
        # Should check both validation workflows
        assert any('freesound-quick-validation' in url for url in urls)
        assert any('freesound-full-validation' in url for url in urls)
    
    @patch('workflow_orchestrator.requests.get')
    def test_validation_checks_nightly_and_other_validation(self, mock_get, orchestrator):
        """Test that validation checks nightly pipeline and other validation."""
        # Mock no workflows running
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_count': 0,
            'workflow_runs': []
        }
        mock_get.return_value = mock_response
        
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-quick-validation')
        
        assert can_proceed is True
        
        # Verify nightly and full validation were checked
        calls = mock_get.call_args_list
        urls = [call[0][0] for call in calls]
        
        assert any('freesound-nightly-pipeline' in url for url in urls)
        assert any('freesound-full-validation' in url for url in urls)


@pytest.mark.integration
class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""
    
    @patch('workflow_orchestrator.requests.get')
    @patch('workflow_orchestrator.time.sleep')
    def test_complete_workflow_lifecycle(self, mock_sleep, mock_get, orchestrator, temp_lock_dir):
        """Test complete workflow from start to finish."""
        # Scenario: Nightly pipeline starts, checks for conflicts, acquires lock, processes, releases lock
        
        # Step 1: Check for conflicts (none running)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_count': 0,
            'workflow_runs': []
        }
        mock_get.return_value = mock_response
        
        can_proceed, reason = orchestrator.check_and_wait_for_conflicts('freesound-nightly-pipeline')
        assert can_proceed is True
        
        # Step 2: Acquire checkpoint lock
        lock_acquired = orchestrator.acquire_lock('checkpoint', timeout=10)
        assert lock_acquired is True
        
        # Step 3: Simulate processing (lock is held)
        lock_file = Path(temp_lock_dir) / "checkpoint.lock"
        assert lock_file.exists()
        
        # Step 4: Release lock
        orchestrator.release_lock('checkpoint')
        assert not lock_file.exists()
    
    @patch('workflow_orchestrator.requests.get')
    @patch('workflow_orchestrator.time.sleep')
    def test_workflow_coordination_with_manual_trigger(self, mock_sleep, mock_get, temp_lock_dir):
        """Test coordination when workflow is manually triggered during scheduled run."""
        # Scenario: Scheduled nightly pipeline is running, user manually triggers validation
        
        # Create orchestrator for nightly pipeline (already running)
        nightly_orch = WorkflowOrchestrator(
            github_token="test_token",
            repository="owner/repo",
            lock_dir=temp_lock_dir,
            dry_run=False
        )
        
        # Nightly acquires lock
        nightly_orch.acquire_lock('checkpoint', timeout=10)
        
        # Mock API: nightly pipeline is running
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
        
        # Create orchestrator for validation (manual trigger)
        validation_orch = WorkflowOrchestrator(
            github_token="test_token",
            repository="owner/repo",
            lock_dir=temp_lock_dir,
            dry_run=False
        )
        
        # Validation checks for conflicts - should detect nightly running
        # Using short timeout for test
        can_proceed, reason = validation_orch.check_and_wait_for_conflicts('freesound-quick-validation', timeout=5)
        
        # Should timeout and skip
        assert can_proceed is False
        assert "Timeout" in reason
        
        # Cleanup
        nightly_orch.release_lock('checkpoint')
