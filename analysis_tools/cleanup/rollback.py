"""
Rollback Manager for cleanup operations.

This module provides rollback capabilities for cleanup operations,
allowing restoration of previous state if issues occur.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import CleanupPhase, FileOperation, RollbackState


class RollbackManager:
    """
    Rollback manager for cleanup operations.
    
    Manages state saving and restoration for cleanup phases,
    enabling rollback to previous state if issues occur.
    """

    def __init__(self, state_dir: str = ".cleanup_rollback"):
        """
        Initialize rollback manager.
        
        Args:
            state_dir: Directory for storing rollback state
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_state(
        self,
        phase: CleanupPhase,
        operations: List[FileOperation],
        git_commits: Optional[List[str]] = None,
        created_directories: Optional[List[str]] = None,
        modified_files: Optional[Dict[str, str]] = None,
    ) -> RollbackState:
        """
        Save state before phase execution.
        
        Args:
            phase: Cleanup phase
            operations: List of file operations to be performed
            git_commits: Optional list of git commit hashes
            created_directories: Optional list of directories that will be created
            modified_files: Optional dict of files and their backup content
            
        Returns:
            RollbackState with saved state information
        """
        timestamp = datetime.now()
        state_file = self.state_dir / f"{phase.value}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        
        # Use provided values or auto-detect
        if modified_files is None:
            modified_files = {}
            for op in operations:
                # Backup source files for move/remove operations
                if op.operation in ["move", "remove"]:
                    source_path = Path(op.source)
                    if source_path.exists() and source_path.is_file():
                        backup_path = self._create_backup(source_path, phase)
                        modified_files[op.source] = str(backup_path)
        
        if created_directories is None:
            created_directories = []
            for op in operations:
                # Track directories that will be created
                if op.operation in ["move", "copy"] and op.destination:
                    dest_path = Path(op.destination)
                    dest_dir = dest_path.parent
                    if not dest_dir.exists():
                        created_directories.append(str(dest_dir))
        
        if git_commits is None:
            git_commits = []
        
        # Create rollback state
        state = RollbackState(
            phase=phase,
            operations=operations,
            git_commits=git_commits,
            created_directories=created_directories,
            modified_files=modified_files,
            timestamp=timestamp,
        )
        
        # Save state to file
        state_data = {
            "phase": phase.value,
            "timestamp": timestamp.isoformat(),
            "operations": [
                {
                    "operation": op.operation,
                    "source": op.source,
                    "destination": op.destination,
                    "timestamp": op.timestamp.isoformat(),
                    "success": op.success,
                }
                for op in operations
            ],
            "git_commits": state.git_commits,
            "created_directories": state.created_directories,
            "modified_files": state.modified_files,
        }
        
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)
        
        return state

    def _create_backup(self, file_path: Path, phase: CleanupPhase) -> Path:
        """
        Create backup of a file.
        
        Args:
            file_path: Path to file to backup
            phase: Cleanup phase
            
        Returns:
            Path to backup file
        """
        backup_dir = self.state_dir / "backups" / phase.value
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.backup"
        backup_path = backup_dir / backup_name
        
        # Copy file to backup location
        shutil.copy2(file_path, backup_path)
        
        return backup_path

    def load_state(self, phase: CleanupPhase) -> Optional[RollbackState]:
        """
        Load most recent rollback state for a phase.
        
        Args:
            phase: Cleanup phase
            
        Returns:
            RollbackState if found, None otherwise
        """
        # Find most recent state file for phase
        state_files = sorted(
            self.state_dir.glob(f"{phase.value}_*.json"),
            reverse=True
        )
        
        if not state_files:
            return None
        
        state_file = state_files[0]
        
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
        except json.JSONDecodeError:
            return None
        
        # Reconstruct operations
        operations = [
            FileOperation(
                operation=op["operation"],
                source=op["source"],
                destination=op.get("destination"),
                timestamp=datetime.fromisoformat(op["timestamp"]),
                success=op["success"],
            )
            for op in state_data["operations"]
        ]
        
        # Get timestamp from state data or use current time as fallback
        timestamp = datetime.fromisoformat(state_data["timestamp"]) if "timestamp" in state_data else datetime.now()
        
        return RollbackState(
            phase=CleanupPhase(state_data["phase"]),
            operations=operations,
            git_commits=state_data.get("git_commits", []),
            created_directories=state_data.get("created_directories", []),
            modified_files=state_data.get("modified_files", {}),
            timestamp=timestamp,
        )

    def rollback(self, state: RollbackState) -> bool:
        """
        Rollback phase to saved state.
        
        Args:
            state: RollbackState to restore
            
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            # Step 1: Revert git commits (if any)
            if state.git_commits:
                self._revert_git_commits(state.git_commits)
            
            # Step 2: Restore moved/removed files
            for source, backup_path in state.modified_files.items():
                self._restore_file(source, backup_path)
            
            # Step 3: Remove files created during phase
            for op in state.operations:
                if op.operation in ["move", "copy"] and op.destination:
                    dest_path = Path(op.destination)
                    if dest_path.exists():
                        dest_path.unlink()
            
            # Step 4: Remove created directories (if empty)
            for directory in state.created_directories:
                dir_path = Path(directory)
                if dir_path.exists() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
            
            # Step 5: Validate rollback success
            return self._validate_rollback(state)
            
        except Exception as e:
            print(f"Error during rollback: {e}")
            return False

    def _revert_git_commits(self, commits: List[str]) -> None:
        """
        Revert git commits.
        
        Args:
            commits: List of commit hashes to revert
        """
        import subprocess
        
        for commit in reversed(commits):
            subprocess.run(
                ["git", "revert", "--no-edit", commit],
                check=True,
                capture_output=True,
            )

    def _restore_file(self, original_path: str, backup_path: str) -> None:
        """
        Restore file from backup.
        
        Args:
            original_path: Original file path
            backup_path: Backup file path
        """
        orig_path = Path(original_path)
        back_path = Path(backup_path)
        
        if not back_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Ensure parent directory exists
        orig_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Restore file
        shutil.copy2(back_path, orig_path)

    def _validate_rollback(self, state: RollbackState) -> bool:
        """
        Validate rollback success.
        
        Args:
            state: RollbackState that was restored
            
        Returns:
            True if validation successful, False otherwise
        """
        # Check that restored files exist
        for source in state.modified_files.keys():
            if not Path(source).exists():
                return False
        
        # Check that created files are removed
        for op in state.operations:
            if op.operation in ["move", "copy"] and op.destination:
                if Path(op.destination).exists():
                    return False
        
        return True

    def clear_state(self, phase: CleanupPhase) -> None:
        """
        Clear rollback state for a phase after successful completion.
        
        Args:
            phase: Cleanup phase
        """
        # Remove state files
        for state_file in self.state_dir.glob(f"{phase.value}_*.json"):
            state_file.unlink()
        
        # Remove backup files
        backup_dir = self.state_dir / "backups" / phase.value
        if backup_dir.exists():
            shutil.rmtree(backup_dir)

    def list_available_rollbacks(self) -> Dict[str, List[str]]:
        """
        List available rollback states by phase.
        
        Returns:
            Dictionary mapping phase names to list of state file timestamps
        """
        rollbacks = {}
        
        for state_file in self.state_dir.glob("*.json"):
            # Parse filename: phase_timestamp.json
            parts = state_file.stem.split("_", 1)
            if len(parts) == 2:
                phase_name, timestamp = parts
                if phase_name not in rollbacks:
                    rollbacks[phase_name] = []
                rollbacks[phase_name].append(timestamp)
        
        # Sort timestamps for each phase
        for phase_name in rollbacks:
            rollbacks[phase_name].sort(reverse=True)
        
        return rollbacks

    def list_available_states(self) -> List[CleanupPhase]:
        """
        List cleanup phases that have available rollback states.
        
        Returns:
            List of CleanupPhase values with available states
        """
        phases = set()
        
        for state_file in self.state_dir.glob("*.json"):
            # Parse filename: phase_timestamp.json
            # Timestamp format is YYYYMMDD_HHMMSS, so we need to find the last occurrence
            # of the timestamp pattern and extract everything before it
            stem = state_file.stem
            # Find the last underscore followed by 8 digits (date part of timestamp)
            import re
            match = re.match(r'(.+)_\d{8}_\d{6}$', stem)
            if match:
                phase_name = match.group(1)
                try:
                    phase = CleanupPhase(phase_name)
                    phases.add(phase)
                except ValueError:
                    continue
        
        return list(phases)

    def is_rollback_available(self, phase: CleanupPhase) -> bool:
        """
        Check if rollback is available for a phase.
        
        Args:
            phase: Cleanup phase to check
            
        Returns:
            True if rollback state exists, False otherwise
        """
        state_files = list(self.state_dir.glob(f"{phase.value}_*.json"))
        return len(state_files) > 0

    def validate_state_integrity(self, phase: CleanupPhase) -> bool:
        """
        Validate integrity of rollback state for a phase.
        
        Args:
            phase: Cleanup phase to validate
            
        Returns:
            True if state is valid, False otherwise
        """
        try:
            state = self.load_state(phase)
            if state is None:
                return False
            
            # Check that backup files exist
            for backup_path in state.modified_files.values():
                if not Path(backup_path).exists():
                    return False
            
            return True
        except Exception:
            return False

    def generate_rollback_report(self, state: RollbackState) -> str:
        """
        Generate a human-readable rollback report.
        
        Args:
            state: RollbackState to report on
            
        Returns:
            Formatted report string
        """
        report_lines = [
            f"Rollback Report for {state.phase.value}",
            f"Timestamp: {state.timestamp.isoformat()}",
            f"",
            f"Operations to rollback: {len(state.operations)}",
        ]
        
        if state.git_commits:
            report_lines.append(f"Git commits to revert: {len(state.git_commits)}")
        
        if state.created_directories:
            report_lines.append(f"Directories to remove: {len(state.created_directories)}")
        
        if state.modified_files:
            report_lines.append(f"Files to restore: {len(state.modified_files)}")
        
        return "\n".join(report_lines)
