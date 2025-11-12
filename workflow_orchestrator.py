"""
Workflow orchestration utility for coordinating Freesound pipeline workflows.

This module provides coordination between the three main workflows:
- Nightly collection (Monday-Saturday)
- Quick validation (Sunday)
- Full validation (1st of month)

Key Features:
- GitHub API integration for workflow status checks
- File-based locking as fallback mechanism
- Exponential backoff for polling
- Comprehensive logging with EmojiFormatter
- Dry-run mode for testing

Example Usage:
    from workflow_orchestrator import WorkflowOrchestrator
    
    orchestrator = WorkflowOrchestrator(
        github_token=os.environ['GITHUB_TOKEN'],
        repository='owner/repo'
    )
    
    # Check if validation is running
    if orchestrator.is_workflow_running('freesound-quick-validation'):
        print("Validation is running, waiting...")
        orchestrator.wait_for_workflow('freesound-quick-validation', timeout=1800)
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from FollowWeb_Visualizor.output.formatters import EmojiFormatter


class WorkflowOrchestrator:
    """
    Orchestrates coordination between multiple GitHub Actions workflows.
    
    Provides methods to check workflow status, wait for completion, and
    implement file-based locking to prevent checkpoint conflicts.
    
    Attributes:
        github_token: GitHub API token for authentication
        repository: Repository in format 'owner/repo'
        logger: Logger instance for output
        api_base_url: GitHub API base URL
        lock_dir: Directory for lock files
        dry_run: If True, simulates coordination without API calls
    """
    
    def __init__(
        self,
        github_token: str,
        repository: str,
        logger: Optional[logging.Logger] = None,
        lock_dir: str = '.workflow_locks',
        dry_run: bool = False
    ):
        """
        Initialize workflow orchestrator.
        
        Args:
            github_token: GitHub API token (GITHUB_TOKEN secret)
            repository: Repository in format 'owner/repo'
            logger: Optional logger instance
            lock_dir: Directory for lock files (default: .workflow_locks)
            dry_run: If True, simulates coordination without API calls
        """
        self.github_token = github_token
        self.repository = repository
        self.logger = logger or logging.getLogger(__name__)
        self.api_base_url = 'https://api.github.com'
        self.lock_dir = Path(lock_dir)
        self.dry_run = dry_run
        
        # Create lock directory if it doesn't exist
        if not dry_run:
            self.lock_dir.mkdir(parents=True, exist_ok=True)
        
        # Workflow conflict matrix (which workflows conflict with each other)
        self.conflict_matrix = {
            'freesound-nightly-pipeline': ['freesound-quick-validation', 'freesound-full-validation'],
            'freesound-quick-validation': ['freesound-nightly-pipeline', 'freesound-full-validation'],
            'freesound-full-validation': ['freesound-nightly-pipeline', 'freesound-quick-validation'],
        }
        
        # Status cache to reduce API calls
        self._status_cache: Dict[str, Tuple[Optional[Dict], datetime]] = {}
        self._cache_ttl = 30  # seconds
    
    def check_workflow_status(self, workflow_name: str) -> Optional[Dict]:
        """
        Check if a specific workflow is currently running.
        
        Uses GitHub API to query workflow runs. Implements caching to reduce
        API calls and exponential backoff for rate limiting.
        
        Args:
            workflow_name: Name of the workflow file (e.g., 'freesound-nightly-pipeline.yml')
        
        Returns:
            Dictionary with workflow run details if running, None otherwise
            Keys: run_id, status, conclusion, created_at, html_url
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would check status of workflow: {workflow_name}")
            return None
        
        # Check cache first
        cache_key = workflow_name
        if cache_key in self._status_cache:
            cached_status, cached_time = self._status_cache[cache_key]
            age = (datetime.now(timezone.utc) - cached_time).total_seconds()
            if age < self._cache_ttl:
                self.logger.debug(f"Using cached status for {workflow_name} (age: {age:.1f}s)")
                return cached_status
        
        # Query GitHub API
        url = f"{self.api_base_url}/repos/{self.repository}/actions/workflows/{workflow_name}.yml/runs"
        headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        params = {
            'status': 'in_progress',
            'per_page': 10
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 429:
                # Rate limited - log and return None (proceed with caution)
                self.logger.warning(
                    EmojiFormatter.format(
                        'warning',
                        f"GitHub API rate limited when checking {workflow_name}"
                    )
                )
                return None
            
            response.raise_for_status()
            data = response.json()
            
            # Check if any runs are in progress
            if data['total_count'] > 0:
                run = data['workflow_runs'][0]
                result = {
                    'run_id': run['id'],
                    'status': run['status'],
                    'conclusion': run['conclusion'],
                    'created_at': run['created_at'],
                    'html_url': run['html_url']
                }
                
                # Cache the result
                self._status_cache[cache_key] = (result, datetime.now(timezone.utc))
                
                return result
            else:
                # No runs in progress
                self._status_cache[cache_key] = (None, datetime.now(timezone.utc))
                return None
        
        except requests.RequestException as e:
            self.logger.warning(f"Failed to check workflow status for {workflow_name}: {e}")
            return None
    
    def is_workflow_running(self, workflow_name: str) -> bool:
        """
        Check if a workflow is currently running.
        
        Args:
            workflow_name: Name of the workflow file
        
        Returns:
            True if workflow is running, False otherwise
        """
        status = self.check_workflow_status(workflow_name)
        return status is not None
    
    def get_conflicting_workflows(self, current_workflow: str) -> List[str]:
        """
        Get list of workflows that conflict with the current workflow.
        
        Args:
            current_workflow: Name of the current workflow
        
        Returns:
            List of conflicting workflow names
        """
        return self.conflict_matrix.get(current_workflow, [])
    
    def wait_for_workflow(
        self,
        workflow_name: str,
        timeout: int = 7200,
        poll_interval: int = 30
    ) -> bool:
        """
        Wait for a specific workflow to complete.
        
        Polls workflow status using exponential backoff until completion
        or timeout is reached.
        
        Args:
            workflow_name: Name of the workflow to wait for
            timeout: Maximum wait time in seconds (default: 7200 = 2 hours)
            poll_interval: Initial polling interval in seconds (default: 30)
        
        Returns:
            True if workflow completed, False if timeout reached
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would wait for workflow: {workflow_name}")
            return True
        
        start_time = time.time()
        current_interval = poll_interval
        
        self.logger.info(
            EmojiFormatter.format(
                'progress',
                f"Waiting for {workflow_name} to complete (timeout: {timeout}s)..."
            )
        )
        
        while time.time() - start_time < timeout:
            if not self.is_workflow_running(workflow_name):
                elapsed = time.time() - start_time
                self.logger.info(
                    EmojiFormatter.format(
                        'success',
                        f"{workflow_name} completed after {elapsed:.1f}s"
                    )
                )
                return True
            
            # Calculate remaining time
            elapsed = time.time() - start_time
            remaining = timeout - elapsed
            
            self.logger.info(
                f"Still waiting for {workflow_name}... "
                f"(elapsed: {elapsed:.1f}s, remaining: {remaining:.1f}s)"
            )
            
            # Sleep with exponential backoff (max 5 minutes)
            time.sleep(min(current_interval, 300))
            current_interval = min(current_interval * 1.5, 300)
        
        # Timeout reached
        self.logger.warning(
            EmojiFormatter.format(
                'warning',
                f"Timeout waiting for {workflow_name} after {timeout}s"
            )
        )
        return False
    
    def check_and_wait_for_conflicts(
        self,
        current_workflow: str,
        timeout: int = 7200
    ) -> Tuple[bool, Optional[str]]:
        """
        Check for conflicting workflows and wait if necessary.
        
        This is the main coordination method that workflows should call
        at startup to ensure safe execution. If a conflict is detected
        and the timeout is reached, returns False to indicate the workflow
        should skip execution and exit gracefully.
        
        Args:
            current_workflow: Name of the current workflow
            timeout: Maximum wait time in seconds (default: 7200 = 2 hours)
        
        Returns:
            Tuple of (can_proceed, reason):
            - can_proceed: True if safe to proceed, False if should skip to next step
            - reason: Explanation of the decision
        """
        conflicting = self.get_conflicting_workflows(current_workflow)
        
        self.logger.info(
            EmojiFormatter.format(
                'info',
                f"Checking for conflicts with: {', '.join(conflicting)}"
            )
        )
        
        for workflow in conflicting:
            if self.is_workflow_running(workflow):
                status = self.check_workflow_status(workflow)
                run_url = status['html_url'] if status else 'unknown'
                
                self.logger.warning(
                    EmojiFormatter.format(
                        'warning',
                        f"Detected running workflow: {workflow} ({run_url})"
                    )
                )
                
                # Wait for completion
                completed = self.wait_for_workflow(workflow, timeout)
                
                if not completed:
                    reason = (
                        f"Timeout (2 hours) waiting for {workflow} to complete. "
                        f"Skipping execution to avoid conflicts. "
                        f"Workflow run: {run_url}"
                    )
                    self.logger.warning(
                        EmojiFormatter.format(
                            'warning',
                            f"SKIPPING EXECUTION: {reason}"
                        )
                    )
                    return False, reason
        
        # No conflicts or all conflicts resolved
        self.logger.info(
            EmojiFormatter.format(
                'success',
                "No workflow conflicts detected, safe to proceed"
            )
        )
        return True, "No conflicts"
    
    def acquire_lock(self, lock_name: str, timeout: int = 300) -> bool:
        """
        Acquire a file-based lock for checkpoint access.
        
        This is a fallback mechanism when GitHub API is unavailable.
        Uses atomic file creation to prevent race conditions.
        
        Args:
            lock_name: Name of the lock (e.g., 'checkpoint')
            timeout: Maximum time to wait for lock in seconds
        
        Returns:
            True if lock acquired, False if timeout
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would acquire lock: {lock_name}")
            return True
        
        lock_file = self.lock_dir / f"{lock_name}.lock"
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to create lock file atomically
                lock_file.touch(exist_ok=False)
                
                # Write lock metadata
                with open(lock_file, 'w') as f:
                    f.write(f"{datetime.now(timezone.utc).isoformat()}\n")
                    f.write(f"{os.environ.get('GITHUB_RUN_ID', 'unknown')}\n")
                
                self.logger.info(
                    EmojiFormatter.format(
                        'success',
                        f"Acquired lock: {lock_name}"
                    )
                )
                return True
            
            except FileExistsError:
                # Lock exists, check if stale
                if self._is_stale_lock(lock_file):
                    self.logger.warning(
                        EmojiFormatter.format(
                            'warning',
                            f"Detected stale lock: {lock_name}, cleaning up..."
                        )
                    )
                    self._cleanup_stale_lock(lock_file)
                    continue
                
                # Wait and retry
                time.sleep(5)
        
        self.logger.error(
            EmojiFormatter.format(
                'error',
                f"Failed to acquire lock: {lock_name} after {timeout}s"
            )
        )
        return False
    
    def release_lock(self, lock_name: str) -> None:
        """
        Release a file-based lock.
        
        Args:
            lock_name: Name of the lock to release
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would release lock: {lock_name}")
            return
        
        lock_file = self.lock_dir / f"{lock_name}.lock"
        
        try:
            if lock_file.exists():
                lock_file.unlink()
                self.logger.info(
                    EmojiFormatter.format(
                        'success',
                        f"Released lock: {lock_name}"
                    )
                )
        except Exception as e:
            self.logger.warning(f"Failed to release lock {lock_name}: {e}")
    
    def _is_stale_lock(self, lock_file: Path, max_age_hours: int = 2) -> bool:
        """
        Check if a lock file is stale (older than max_age_hours).
        
        Args:
            lock_file: Path to lock file
            max_age_hours: Maximum age in hours before considering stale
        
        Returns:
            True if lock is stale, False otherwise
        """
        try:
            mtime = datetime.fromtimestamp(lock_file.stat().st_mtime, tz=timezone.utc)
            age = datetime.now(timezone.utc) - mtime
            return age > timedelta(hours=max_age_hours)
        except Exception:
            return False
    
    def _cleanup_stale_lock(self, lock_file: Path) -> None:
        """
        Remove a stale lock file.
        
        Args:
            lock_file: Path to lock file to remove
        """
        try:
            lock_file.unlink()
            self.logger.info(f"Cleaned up stale lock: {lock_file.name}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup stale lock: {e}")
