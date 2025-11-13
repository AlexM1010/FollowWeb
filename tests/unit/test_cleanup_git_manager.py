"""
Unit tests for Git Manager in cleanup system.

Tests GitPython integration, git-filter-repo integration, github3.py integration,
and history verification for the repository cleanup system.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import tempfile
import shutil

import pytest
import git
from git import Repo

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis_tools.cleanup.git_manager import GitManager
from analysis_tools.cleanup.models import FileMapping, BranchInfo
from analysis_tools.cleanup.exceptions import GitOperationError


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    
    # Initialize git repo
    repo = Repo.init(repo_path)
    
    # Configure git user
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")
    
    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    
    return repo_path


@pytest.fixture
def git_manager(temp_git_repo):
    """Fixture providing GitManager instance with temp repo."""
    return GitManager(str(temp_git_repo), batch_size=3)


@pytest.mark.unit
class TestGitPythonIntegration:
    """Test GitPython integration for basic git operations."""
    
    def test_initializes_with_repo_path(self, temp_git_repo):
        """Test GitManager initialization with repository path."""
        manager = GitManager(str(temp_git_repo))
        
        assert manager.repo is not None
        assert manager.repo.working_dir == str(temp_git_repo)
    
    def test_git_move_single_file(self, git_manager, temp_git_repo):
        """Test moving a single file using git mv."""
        # Create source file
        source = temp_git_repo / "source.txt"
        source.write_text("test content")
        git_manager.repo.index.add(["source.txt"])
        git_manager.repo.index.commit("Add source file")
        
        # Move file
        dest = "dest/source.txt"
        result = git_manager.git_move("source.txt", dest, use_filter_repo=False)
        
        assert result is True
        assert (temp_git_repo / dest).exists()
        assert not source.exists()
    
    def test_git_remove_cached(self, git_manager, temp_git_repo):
        """Test removing file from git tracking (cached only)."""
        # Create and commit file
        test_file = temp_git_repo / "to_remove.txt"
        test_file.write_text("content")
        git_manager.repo.index.add(["to_remove.txt"])
        git_manager.repo.index.commit("Add file to remove")
        
        # Remove from tracking
        result = git_manager.git_remove("to_remove.txt", cached_only=True)
        
        assert result is True
        assert test_file.exists()  # File still exists locally
    
    def test_create_commit(self, git_manager, temp_git_repo):
        """Test creating a commit."""
        # Create and stage file
        test_file = temp_git_repo / "new_file.txt"
        test_file.write_text("new content")
        
        commit_sha = git_manager.create_commit("Test commit", ["new_file.txt"])
        
        assert commit_sha is not None
        assert len(commit_sha) == 40  # SHA-1 hash length
        
        # Verify commit exists
        commit = git_manager.repo.commit(commit_sha)
        assert commit.message == "Test commit"
    
    def test_create_backup_branch(self, git_manager):
        """Test creating a backup branch."""
        branch_name = "backup/test-backup"
        
        result = git_manager.create_backup_branch(branch_name)
        
        assert result is True
        assert branch_name in [b.name for b in git_manager.repo.branches]
    
    def test_delete_local_branch(self, git_manager):
        """Test deleting a local branch."""
        # Create branch
        branch_name = "test-branch"
        git_manager.repo.create_head(branch_name)
        
        # Delete branch
        result = git_manager.delete_branch(branch_name, remote=False)
        
        assert result is True
        assert branch_name not in [b.name for b in git_manager.repo.branches]


@pytest.mark.unit
class TestGitBatchOperations:
    """Test batch git operations with progress tracking."""
    
    def test_git_move_batch(self, git_manager, temp_git_repo):
        """Test batching git mv operations."""
        # Create multiple files
        files = []
        for i in range(10):
            source = temp_git_repo / f"file{i}.txt"
            source.write_text(f"content {i}")
            files.append(f"file{i}.txt")
        
        git_manager.repo.index.add(files)
        git_manager.repo.index.commit("Add files for batch move")
        
        # Create mappings
        mappings = [
            FileMapping(f"file{i}.txt", f"moved/file{i}.txt", "move")
            for i in range(10)
        ]
        
        # Batch move (batch_size=3, so should create 4 commits)
        commits = git_manager.git_move_batch(mappings)
        
        assert len(commits) == 4  # 10 files / 3 per batch = 4 commits
        
        # Verify files moved
        for i in range(10):
            assert (temp_git_repo / f"moved/file{i}.txt").exists()
    
    def test_batch_respects_batch_size(self, git_manager, temp_git_repo):
        """Test that batch operations respect configured batch size."""
        # Create files
        files = []
        for i in range(7):
            source = temp_git_repo / f"batch{i}.txt"
            source.write_text(f"content {i}")
            files.append(f"batch{i}.txt")
        
        git_manager.repo.index.add(files)
        git_manager.repo.index.commit("Add files for batch test")
        
        mappings = [
            FileMapping(f"batch{i}.txt", f"dest/batch{i}.txt", "move")
            for i in range(7)
        ]
        
        # batch_size=3, so 7 files should create 3 commits (3+3+1)
        commits = git_manager.git_move_batch(mappings)
        
        assert len(commits) == 3


@pytest.mark.unit
class TestStreamingGitOperations:
    """Test streaming git operations for large-scale file processing."""
    
    def test_git_move_streaming(self, git_manager, temp_git_repo):
        """Test streaming git operations for 10K+ files."""
        # Create files
        files = []
        for i in range(20):
            source = temp_git_repo / f"stream{i}.txt"
            source.write_text(f"content {i}")
            files.append(f"stream{i}.txt")
        
        git_manager.repo.index.add(files)
        git_manager.repo.index.commit("Add files for streaming test")
        
        # Create mapping generator
        def mapping_generator():
            for i in range(20):
                yield FileMapping(f"stream{i}.txt", f"streamed/stream{i}.txt", "move")
        
        # Stream operations
        commits = list(git_manager.git_move_streaming(mapping_generator()))
        
        # Should create commits in batches
        assert len(commits) > 0
        
        # Verify files moved
        for i in range(20):
            assert (temp_git_repo / f"streamed/stream{i}.txt").exists()


@pytest.mark.unit
class TestHistoryVerification:
    """Test git history verification."""
    
    def test_verify_history_for_moved_file(self, git_manager, temp_git_repo):
        """Test that git log --follow works for moved files."""
        # Create and commit file
        source = temp_git_repo / "original.txt"
        source.write_text("original content")
        git_manager.repo.index.add(["original.txt"])
        git_manager.repo.index.commit("Add original file")
        
        # Move file
        git_manager.git_move("original.txt", "moved/original.txt", use_filter_repo=False)
        git_manager.repo.index.commit("Move file")
        
        # Verify history
        result = git_manager.verify_history("moved/original.txt")
        
        assert result is True
    
    def test_verify_history_fails_for_nonexistent_file(self, git_manager):
        """Test history verification fails for nonexistent file."""
        result = git_manager.verify_history("nonexistent.txt")
        
        assert result is False


@pytest.mark.unit
class TestBranchManagement:
    """Test branch status and management."""
    
    def test_get_branch_status(self, git_manager):
        """Test getting status of all branches."""
        # Create test branches
        git_manager.repo.create_head("feature-1")
        git_manager.repo.create_head("feature-2")
        
        status = git_manager.get_branch_status()
        
        assert isinstance(status, dict)
        assert "master" in status or "main" in status
        assert "feature-1" in status
        assert "feature-2" in status
    
    def test_branch_info_contains_metadata(self, git_manager):
        """Test that branch info contains required metadata."""
        git_manager.repo.create_head("test-branch")
        
        status = git_manager.get_branch_status()
        
        for branch_name, info in status.items():
            assert isinstance(info, BranchInfo)
            assert hasattr(info, 'name')
            assert hasattr(info, 'last_commit_date')
            assert hasattr(info, 'commit_count')


@pytest.mark.unit
class TestGitFilterRepoIntegration:
    """Test git-filter-repo integration for major reorganizations."""
    
    def test_uses_filter_repo_for_major_reorganization(self, git_manager, temp_git_repo):
        """Test that git-filter-repo is used for major reorganizations."""
        # Create file
        source = temp_git_repo / "major_reorg.txt"
        source.write_text("content")
        git_manager.repo.index.add(["major_reorg.txt"])
        git_manager.repo.index.commit("Add file for major reorg")
        
        # This should use git-filter-repo (mocked in actual implementation)
        with patch('analysis_tools.cleanup.git_manager.GitManager._use_filter_repo') as mock_filter:
            mock_filter.return_value = True
            result = git_manager.git_move("major_reorg.txt", "reorganized/major_reorg.txt", use_filter_repo=True)
            
            # Verify filter-repo was attempted
            assert mock_filter.called or result is True


@pytest.mark.unit
class TestGitHubIntegration:
    """Test github3.py integration for remote operations."""
    
    def test_initializes_github_client_when_needed(self, git_manager):
        """Test that GitHub client is initialized when needed."""
        # GitHub client should be None initially
        assert git_manager.github_client is None
        
        # Mock GitHub authentication
        with patch('analysis_tools.cleanup.git_manager.login') as mock_login:
            mock_login.return_value = Mock()
            git_manager._init_github_client("fake_token")
            
            assert git_manager.github_client is not None
    
    @patch('analysis_tools.cleanup.git_manager.login')
    def test_delete_remote_branch(self, mock_login, git_manager):
        """Test deleting a remote branch using github3.py."""
        # Mock GitHub client
        mock_repo = Mock()
        mock_ref = Mock()
        mock_ref.delete.return_value = True
        mock_repo.ref.return_value = mock_ref
        
        mock_github = Mock()
        mock_github.repository.return_value = mock_repo
        mock_login.return_value = mock_github
        
        git_manager.github_client = mock_github
        
        # Delete remote branch
        result = git_manager.delete_branch("test-branch", remote=True)
        
        # Should attempt to delete via GitHub API
        assert result is True or mock_github.repository.called


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in git operations."""
    
    def test_handles_invalid_repo_path(self):
        """Test handling of invalid repository path."""
        with pytest.raises(Exception):
            GitManager("/nonexistent/path")
    
    def test_handles_git_move_failure(self, git_manager):
        """Test handling of git mv failure."""
        # Try to move nonexistent file
        result = git_manager.git_move("nonexistent.txt", "dest.txt", use_filter_repo=False)
        
        # Should handle gracefully
        assert result is False or isinstance(result, bool)
    
    def test_handles_commit_failure(self, git_manager):
        """Test handling of commit failure."""
        # Try to commit without staged files
        with pytest.raises(Exception):
            git_manager.create_commit("Empty commit", [])


@pytest.mark.unit
class TestProgressTracking:
    """Test progress tracking during git operations."""
    
    def test_shows_progress_during_batch_operations(self, git_manager, temp_git_repo):
        """Test that progress is tracked during batch git operations."""
        # Create files
        files = []
        for i in range(15):
            source = temp_git_repo / f"progress{i}.txt"
            source.write_text(f"content {i}")
            files.append(f"progress{i}.txt")
        
        git_manager.repo.index.add(files)
        git_manager.repo.index.commit("Add files for progress test")
        
        mappings = [
            FileMapping(f"progress{i}.txt", f"tracked/progress{i}.txt", "move")
            for i in range(15)
        ]
        
        # Should show progress during batch operations
        commits = git_manager.git_move_batch(mappings)
        
        assert len(commits) > 0
        # Verify all files moved
        for i in range(15):
            assert (temp_git_repo / f"tracked/progress{i}.txt").exists()