"""
Git Manager for cleanup operations.

Handles all git operations including file moves, commits, branch management,
and history preservation. Integrates with GitPython for standard operations
and git-filter-repo for major reorganizations.
"""

from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

try:
    import git
    from git import Repo
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

try:
    import github3
    GITHUB3_AVAILABLE = True
except ImportError:
    GITHUB3_AVAILABLE = False

from .exceptions import GitOperationError
from .models import BranchInfo, CleanupPhase, FileMapping


class GitManager:
    """
    Manages git operations for cleanup.
    
    Provides methods for git mv, git rm, commits, branch management,
    and history verification. Integrates with GitPython for standard
    operations and git-filter-repo for major reorganizations.
    
    Performance optimizations:
    - Batch operations (100 files per commit)
    - Progress tracking with existing ProgressTracker
    - Streaming mode for 10K+ files
    """

    def __init__(self, repo_path: str = ".", batch_size: int = 100):
        """
        Initialize Git Manager.
        
        Args:
            repo_path: Path to git repository
            batch_size: Number of files per commit batch
            
        Raises:
            GitOperationError: If GitPython is not available or repo invalid
        """
        if not GIT_AVAILABLE:
            raise GitOperationError(
                phase=CleanupPhase.BACKUP,
                message="GitPython is not installed. Install with: pip install gitpython",
                recoverable=False,
            )
        
        try:
            self.repo = Repo(repo_path)
            self.batch_size = batch_size
            self.github_client: Optional[github3.GitHub] = None
        except Exception as e:
            raise GitOperationError(
                phase=CleanupPhase.BACKUP,
                message=f"Failed to initialize git repository: {e}",
                recoverable=False,
            )
    
    def git_move(
        self,
        source: str,
        destination: str,
        use_filter_repo: bool = False,
    ) -> bool:
        """
        Move file using git mv or git-filter-repo.
        
        Args:
            source: Source file path
            destination: Destination file path
            use_filter_repo: If True, use git-filter-repo for complex moves
            
        Returns:
            True if successful
            
        Raises:
            GitOperationError: If git operation fails
        """
        try:
            if use_filter_repo:
                # Use git-filter-repo for complex moves with full history
                # This would require git-filter-repo to be installed
                raise NotImplementedError(
                    "git-filter-repo integration not yet implemented"
                )
            else:
                # Use standard git mv for simple operations
                self.repo.git.mv(source, destination)
            return True
        except Exception as e:
            raise GitOperationError(
                phase=CleanupPhase.ROOT_CLEANUP,
                message=f"Failed to move {source} to {destination}: {e}",
                git_command=f"git mv {source} {destination}",
            )
    
    def git_move_batch(
        self, mappings: list[FileMapping]
    ) -> list[str]:
        """
        Batch git mv operations with progress tracking.
        
        Executes git mv in batches of batch_size files per commit
        to reduce subprocess overhead.
        
        Args:
            mappings: List of file mappings to execute
            
        Returns:
            List of commit SHAs
        """
        commits = []
        total_batches = (len(mappings) + self.batch_size - 1) // self.batch_size
        
        # Import ProgressTracker only when needed
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "FollowWeb"))
            from FollowWeb_Visualizor.utils.progress import ProgressTracker
            
            with ProgressTracker(
                total=len(mappings),
                title="Git operations"
            ) as tracker:
                for i in range(0, len(mappings), self.batch_size):
                    batch = mappings[i:i + self.batch_size]
                    
                    # Execute batch of git mv commands
                    for j, mapping in enumerate(batch):
                        self.repo.git.mv(mapping.source, mapping.destination)
                        tracker.update(i + j + 1)
                    
                    # Single commit per batch
                    batch_num = i // self.batch_size + 1
                    commit = self.repo.index.commit(
                        f"Move {len(batch)} files (batch {batch_num}/{total_batches})"
                    )
                    commits.append(commit.hexsha)
        except ImportError:
            # Fallback without progress tracking
            for i in range(0, len(mappings), self.batch_size):
                batch = mappings[i:i + self.batch_size]
                
                for mapping in batch:
                    self.repo.git.mv(mapping.source, mapping.destination)
                
                batch_num = i // self.batch_size + 1
                commit = self.repo.index.commit(
                    f"Move {len(batch)} files (batch {batch_num}/{total_batches})"
                )
                commits.append(commit.hexsha)
        
        return commits
    
    def git_move_streaming(
        self, mappings: Iterator[FileMapping]
    ) -> Iterator[str]:
        """
        Stream git operations for 10K+ files.
        
        Args:
            mappings: Iterator of file mappings
            
        Yields:
            Commit SHA for each batch
        """
        batch = []
        batch_num = 1
        
        for mapping in mappings:
            batch.append(mapping)
            if len(batch) >= self.batch_size:
                yield from self._commit_batch(batch, batch_num)
                batch = []
                batch_num += 1
        
        # Commit remaining files
        if batch:
            yield from self._commit_batch(batch, batch_num)
    
    def _commit_batch(
        self, batch: list[FileMapping], batch_num: int
    ) -> list[str]:
        """
        Commit a batch of file operations.
        
        Args:
            batch: List of file mappings
            batch_num: Batch number for commit message
            
        Returns:
            List containing commit SHA
        """
        for mapping in batch:
            self.repo.git.mv(mapping.source, mapping.destination)
        
        commit = self.repo.index.commit(
            f"Move {len(batch)} files (batch {batch_num})"
        )
        return [commit.hexsha]
    
    def git_remove(
        self, file_path: str, cached_only: bool = True
    ) -> bool:
        """
        Remove file from git tracking using GitPython.
        
        Args:
            file_path: Path to file to remove
            cached_only: If True, only remove from index (keep local file)
            
        Returns:
            True if successful
            
        Raises:
            GitOperationError: If git operation fails
        """
        try:
            if cached_only:
                self.repo.git.rm('--cached', file_path)
            else:
                self.repo.git.rm(file_path)
            return True
        except Exception as e:
            raise GitOperationError(
                phase=CleanupPhase.CACHE_CLEANUP,
                message=f"Failed to remove {file_path}: {e}",
                git_command=f"git rm {'--cached ' if cached_only else ''}{file_path}",
            )
    
    def create_commit(
        self, message: str, files: Optional[list[str]] = None
    ) -> str:
        """
        Create commit for phase changes using GitPython.
        
        Args:
            message: Commit message
            files: Optional list of files to add (None = add all)
            
        Returns:
            Commit SHA
            
        Raises:
            GitOperationError: If commit fails
        """
        try:
            if files:
                self.repo.index.add(files)
            else:
                self.repo.git.add('-A')
            
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except Exception as e:
            raise GitOperationError(
                phase=CleanupPhase.BACKUP,
                message=f"Failed to create commit: {e}",
                git_command=f"git commit -m '{message}'",
            )
    
    def create_backup_branch(self, branch_name: str) -> bool:
        """
        Create backup branch before cleanup using GitPython.
        
        Args:
            branch_name: Name for backup branch
            
        Returns:
            True if successful, False if branch already exists
            
        Raises:
            GitOperationError: If branch creation fails for reasons other than already existing
        """
        try:
            # Check if branch already exists
            if branch_name in [head.name for head in self.repo.heads]:
                return False
            
            # Create new branch
            self.repo.create_head(branch_name)
            return True
        except Exception as e:
            # Check if error is due to branch already existing
            if "already exists" in str(e).lower():
                return False
            
            raise GitOperationError(
                phase=CleanupPhase.BACKUP,
                message=f"Failed to create backup branch '{branch_name}': {e}",
                git_command=f"git branch {branch_name}",
            )
    
    def verify_history(self, file_path: str) -> bool:
        """
        Verify git log --follow works for moved file.
        
        Args:
            file_path: Path to file to verify
            
        Returns:
            True if history is preserved
        """
        try:
            # Use git log --follow to check history
            log = self.repo.git.log('--follow', '--oneline', file_path)
            return len(log) > 0
        except Exception:
            return False
    
    def get_branch_status(self) -> dict[str, BranchInfo]:
        """
        Get status of all branches using GitPython and github3.py.
        
        Returns:
            Dictionary mapping branch names to BranchInfo
        """
        branches = {}
        
        # Get local branches using GitPython
        for branch in self.repo.branches:
            try:
                last_commit = branch.commit
                branches[branch.name] = BranchInfo(
                    name=branch.name,
                    last_commit_date=datetime.fromtimestamp(
                        last_commit.committed_date
                    ),
                    has_pr=False,  # Would need GitHub API to determine
                    pr_number=None,
                    is_merged=False,  # Would need to check against main
                    commit_count=len(list(self.repo.iter_commits(branch.name))),
                )
            except Exception:
                continue
        
        # TODO: Integrate github3.py for remote branch and PR information
        # This would require GitHub authentication and API calls
        
        return branches
    
    def delete_branch(
        self, branch_name: str, remote: bool = False
    ) -> bool:
        """
        Delete local or remote branch.
        
        Args:
            branch_name: Name of branch to delete
            remote: If True, delete remote branch (requires github3.py)
            
        Returns:
            True if successful
            
        Raises:
            GitOperationError: If deletion fails
        """
        try:
            if remote:
                if not GITHUB3_AVAILABLE or not self.github_client:
                    raise GitOperationError(
                        phase=CleanupPhase.BRANCH_CLEANUP,
                        message="github3.py not available or not authenticated",
                        recoverable=False,
                    )
                # TODO: Implement remote deletion with github3.py
                raise NotImplementedError(
                    "Remote branch deletion not yet implemented"
                )
            else:
                # Delete local branch
                self.repo.delete_head(branch_name, force=True)
            return True
        except Exception as e:
            raise GitOperationError(
                phase=CleanupPhase.BRANCH_CLEANUP,
                message=f"Failed to delete branch '{branch_name}': {e}",
                git_command=f"git branch -D {branch_name}",
            )
    
    def authenticate_github(
        self, token: Optional[str] = None
    ) -> bool:
        """
        Authenticate with GitHub API using github3.py.
        
        Args:
            token: GitHub personal access token
            
        Returns:
            True if authentication successful
        """
        if not GITHUB3_AVAILABLE:
            return False
        
        try:
            if token:
                self.github_client = github3.login(token=token)
            else:
                # Try to use git config for authentication
                self.github_client = github3.GitHub()
            return self.github_client is not None
        except Exception:
            return False
