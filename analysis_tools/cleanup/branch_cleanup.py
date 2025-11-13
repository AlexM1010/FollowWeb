"""Branch cleanup utilities for repository maintenance."""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .exceptions import CleanupError


@dataclass
class BranchInfo:
    """Information about a git branch."""
    
    name: str
    last_commit_date: datetime
    author: str
    is_merged: bool
    is_remote: bool
    has_open_pr: bool
    pr_number: Optional[int] = None
    pr_state: Optional[str] = None


class BranchCleanupManager:
    """Manages branch cleanup operations."""
    
    def __init__(self, repo_path: Optional[str] = None):
        """Initialize branch cleanup manager.
        
        Args:
            repo_path: Path to git repository (defaults to current directory)
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        
    def list_all_branches(self) -> List[BranchInfo]:
        """List all local and remote branches with metadata.
        
        Returns:
            List of BranchInfo objects
        """
        branches = []
        
        # Get local branches with commit dates
        result = subprocess.run(
            ["git", "for-each-ref", "--sort=-committerdate", "refs/heads/",
             "--format=%(refname:short)|%(committerdate:iso)|%(authorname)"],
            capture_output=True,
            text=True,
            cwd=self.repo_path
        )
        
        if result.returncode != 0:
            raise CleanupError(f"Failed to list branches: {result.stderr}")
        
        # Get merged branches
        merged_result = subprocess.run(
            ["git", "branch", "--merged", "main"],
            capture_output=True,
            text=True,
            cwd=self.repo_path
        )
        merged_branches = {
            line.strip().replace("* ", "")
            for line in merged_result.stdout.splitlines()
            if line.strip()
        }
        
        # Get PR information
        pr_info = self._get_pr_info()
        
        # Parse local branches
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            
            parts = line.split("|")
            if len(parts) != 3:
                continue
            
            name, date_str, author = parts
            commit_date = datetime.fromisoformat(date_str.replace(" +0000", "+00:00"))
            
            branch_pr = pr_info.get(name, {})
            
            branches.append(BranchInfo(
                name=name,
                last_commit_date=commit_date,
                author=author,
                is_merged=name in merged_branches,
                is_remote=False,
                has_open_pr=branch_pr.get("state") == "OPEN",
                pr_number=branch_pr.get("number"),
                pr_state=branch_pr.get("state")
            ))
        
        return branches
    
    def _get_pr_info(self) -> Dict[str, Dict]:
        """Get PR information for all branches.
        
        Returns:
            Dictionary mapping branch names to PR info
        """
        try:
            result = subprocess.run(
                ["gh", "pr", "list", "--state", "all", "--json",
                 "number,title,state,headRefName,mergedAt,createdAt"],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            if result.returncode != 0:
                return {}
            
            prs = json.loads(result.stdout)
            return {
                pr["headRefName"]: {
                    "number": pr["number"],
                    "state": pr["state"],
                    "title": pr["title"],
                    "merged_at": pr.get("mergedAt"),
                    "created_at": pr["createdAt"]
                }
                for pr in prs
            }
        except Exception:
            return {}
    
    def classify_branches(self, branches: List[BranchInfo]) -> Dict[str, List[BranchInfo]]:
        """Classify branches into categories.
        
        Args:
            branches: List of branch information
            
        Returns:
            Dictionary with categories: merged, stale, active, protected
        """
        now = datetime.now(branches[0].last_commit_date.tzinfo)
        stale_threshold = now - timedelta(days=30)
        
        classified = {
            "merged": [],
            "stale": [],
            "active": [],
            "protected": []
        }
        
        for branch in branches:
            # Skip main branch
            if branch.name == "main":
                classified["protected"].append(branch)
                continue
            
            # Skip backup branches
            if branch.name.startswith("backup/"):
                classified["protected"].append(branch)
                continue
            
            # Merged branches
            if branch.is_merged and not branch.has_open_pr:
                classified["merged"].append(branch)
            # Stale branches (no commits in 30 days, no open PR)
            elif branch.last_commit_date < stale_threshold and not branch.has_open_pr:
                classified["stale"].append(branch)
            # Active branches
            else:
                classified["active"].append(branch)
        
        return classified
    
    def delete_merged_branches(self, branches: List[BranchInfo], dry_run: bool = False) -> List[str]:
        """Delete merged branches.
        
        Args:
            branches: List of merged branches to delete
            dry_run: If True, only simulate deletion
            
        Returns:
            List of deleted branch names
        """
        deleted = []
        
        for branch in branches:
            if branch.name == "main" or branch.name.startswith("backup/"):
                continue
            
            if dry_run:
                print(f"Would delete local branch: {branch.name}")
                deleted.append(branch.name)
                continue
            
            # Delete local branch
            try:
                result = subprocess.run(
                    ["git", "branch", "-d", branch.name],
                    capture_output=True,
                    text=True,
                    cwd=self.repo_path
                )
                
                if result.returncode == 0:
                    deleted.append(branch.name)
                    print(f"Deleted local branch: {branch.name}")
                else:
                    print(f"Failed to delete {branch.name}: {result.stderr}")
            except Exception as e:
                print(f"Error deleting {branch.name}: {e}")
            
            # Delete remote branch if it exists
            try:
                result = subprocess.run(
                    ["git", "push", "origin", "--delete", branch.name],
                    capture_output=True,
                    text=True,
                    cwd=self.repo_path
                )
                
                if result.returncode == 0:
                    print(f"Deleted remote branch: origin/{branch.name}")
            except Exception:
                pass  # Remote branch may not exist
        
        return deleted
    
    def generate_cleanup_report(
        self,
        classified: Dict[str, List[BranchInfo]],
        deleted: List[str],
        output_path: Optional[Path] = None
    ) -> Dict:
        """Generate branch cleanup report.
        
        Args:
            classified: Classified branches
            deleted: List of deleted branch names
            output_path: Optional path to save report
            
        Returns:
            Report dictionary
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_branches": sum(len(branches) for branches in classified.values()),
                "merged": len(classified["merged"]),
                "stale": len(classified["stale"]),
                "active": len(classified["active"]),
                "protected": len(classified["protected"]),
                "deleted": len(deleted)
            },
            "merged_branches": [
                {
                    "name": b.name,
                    "last_commit": b.last_commit_date.isoformat(),
                    "author": b.author,
                    "pr_number": b.pr_number,
                    "pr_state": b.pr_state
                }
                for b in classified["merged"]
            ],
            "stale_branches": [
                {
                    "name": b.name,
                    "last_commit": b.last_commit_date.isoformat(),
                    "author": b.author,
                    "days_since_commit": (datetime.now(b.last_commit_date.tzinfo) - b.last_commit_date).days
                }
                for b in classified["stale"]
            ],
            "active_branches": [
                {
                    "name": b.name,
                    "last_commit": b.last_commit_date.isoformat(),
                    "author": b.author,
                    "has_open_pr": b.has_open_pr,
                    "pr_number": b.pr_number
                }
                for b in classified["active"]
            ],
            "protected_branches": [b.name for b in classified["protected"]],
            "deleted_branches": deleted
        }
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)
        
        return report
