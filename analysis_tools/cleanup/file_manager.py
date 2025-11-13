"""
File Manager for cleanup operations.

Handles all file system operations including directory creation, file moves,
file categorization, and reference updates. Integrates with organize-tool for
file operations and analysis_tools for code analysis.
"""

import os
import re
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Iterator, Optional

from ..duplication_detector import DuplicationDetector
from ..code_analyzer import CodeAnalyzer
from .exceptions import FileOperationError
from .models import (
    CleanupPhase,
    FileCategory,
    FileMapping,
    FileOperation,
)


class FileManager:
    """
    Manages file system operations for cleanup.
    
    Provides methods for creating directories, moving files, categorizing
    scripts, and updating file references. Integrates with organize-tool
    for file operations and analysis_tools for code analysis.
    
    Performance optimizations:
    - Parallel file categorization using existing ParallelProcessingManager
    - Disk I/O optimization by sorting operations by directory
    - Progress tracking with existing ProgressTracker
    - Streaming mode for 10K+ files
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize File Manager.
        
        Args:
            max_workers: Maximum parallel workers (None = auto-detect)
        """
        self.max_workers = max_workers
        self.duplication_detector = DuplicationDetector()
        self.code_analyzer = CodeAnalyzer()
        
        # Import parallel manager only when needed
        self._parallel_manager = None
        
    @property
    def parallel_manager(self):
        """Lazy load ParallelProcessingManager to avoid circular imports."""
        if self._parallel_manager is None:
            # Import here to avoid issues during module initialization
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "FollowWeb"))
            from FollowWeb_Visualizor.utils.parallel import ParallelProcessingManager
            self._parallel_manager = ParallelProcessingManager()
        return self._parallel_manager
        
    def create_directory_structure(
        self, structure: dict[str, list[str]]
    ) -> bool:
        """
        Create organized directory structure.
        
        Args:
            structure: Dictionary mapping directory names to subdirectories
            
        Returns:
            True if successful
            
        Raises:
            FileOperationError: If directory creation fails
        """
        try:
            for directory in structure.keys():
                Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            raise FileOperationError(
                phase=CleanupPhase.ROOT_CLEANUP,
                message=f"Failed to create directory structure: {e}",
                recoverable=False,
            )
    
    def move_files(
        self,
        mappings: list[FileMapping],
        dry_run: bool = False,
    ) -> list[FileOperation]:
        """
        Move files with progress tracking and disk I/O optimization.
        
        Args:
            mappings: List of file mappings to execute
            dry_run: If True, simulate without making changes
            
        Returns:
            List of completed file operations
        """
        from datetime import datetime
        
        # Optimize file order to minimize disk seeks
        optimized_mappings = self._optimize_file_order(mappings)
        
        operations = []
        
        # Import ProgressTracker only when needed
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "FollowWeb"))
            from FollowWeb_Visualizor.utils.progress import ProgressTracker
            
            with ProgressTracker(
                total=len(optimized_mappings),
                title="Moving files"
            ) as tracker:
                for i, mapping in enumerate(optimized_mappings):
                    op = self._move_single_file(mapping, dry_run)
                    operations.append(op)
                    tracker.update(i + 1)
        except ImportError:
            # Fallback without progress tracking
            for mapping in optimized_mappings:
                op = self._move_single_file(mapping, dry_run)
                operations.append(op)
        
        return operations
    
    def move_files_streaming(
        self,
        mappings: Iterator[FileMapping],
        batch_size: int = 1000,
        dry_run: bool = False,
    ) -> Iterator[FileOperation]:
        """
        Stream file operations for 10K+ files to minimize memory usage.
        
        Args:
            mappings: Iterator of file mappings
            batch_size: Number of files per batch
            dry_run: If True, simulate without making changes
            
        Yields:
            FileOperation for each completed operation
        """
        batch = []
        for mapping in mappings:
            batch.append(mapping)
            if len(batch) >= batch_size:
                optimized_batch = self._optimize_file_order(batch)
                for m in optimized_batch:
                    yield self._move_single_file(m, dry_run)
                batch = []
        
        # Process remaining files
        if batch:
            optimized_batch = self._optimize_file_order(batch)
            for m in optimized_batch:
                yield self._move_single_file(m, dry_run)
    
    def _move_single_file(
        self, mapping: FileMapping, dry_run: bool = False
    ) -> FileOperation:
        """
        Move a single file.
        
        Args:
            mapping: File mapping to execute
            dry_run: If True, simulate without making changes
            
        Returns:
            FileOperation record
        """
        from datetime import datetime
        
        try:
            if not dry_run:
                source_path = Path(mapping.source)
                dest_path = Path(mapping.destination)
                
                # Create destination directory if needed
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move the file
                source_path.rename(dest_path)
            
            return FileOperation(
                operation=mapping.operation_type,
                source=mapping.source,
                destination=mapping.destination,
                timestamp=datetime.now(),
                success=True,
            )
        except Exception as e:
            return FileOperation(
                operation=mapping.operation_type,
                source=mapping.source,
                destination=mapping.destination,
                timestamp=datetime.now(),
                success=False,
                error_message=str(e),
            )
    
    def categorize_files_parallel(
        self, file_paths: list[str]
    ) -> dict[str, FileCategory]:
        """
        Parallelize file categorization using existing ParallelProcessingManager.
        
        Args:
            file_paths: List of file paths to categorize
            
        Returns:
            Dictionary mapping file paths to categories
        """
        # Get optimal parallel configuration
        parallel_config = self.parallel_manager.get_parallel_config(
            operation_type='analysis',
            min_size_threshold=100,
            graph_size=len(file_paths)
        )
        
        if parallel_config.cores_used > 1:
            with ProcessPoolExecutor(
                max_workers=parallel_config.cores_used
            ) as executor:
                results = executor.map(
                    self._categorize_single_file,
                    file_paths,
                    chunksize=1000
                )
            return dict(zip(file_paths, results))
        else:
            # Sequential processing for small datasets
            return {
                path: self._categorize_single_file(path)
                for path in file_paths
            }
    
    def _categorize_single_file(self, file_path: str) -> FileCategory:
        """
        Categorize a single file based on its name and content.
        
        Args:
            file_path: Path to file
            
        Returns:
            FileCategory for the file
        """
        filename = os.path.basename(file_path).upper()
        
        # Documentation files
        if "_REPORT.MD" in filename:
            return FileCategory.REPORT
        elif "_GUIDE.MD" in filename:
            return FileCategory.GUIDE
        elif "_ANALYSIS.MD" in filename:
            return FileCategory.ANALYSIS
        elif "_SUMMARY.MD" in filename:
            return FileCategory.SUMMARY
        elif "_STATUS.MD" in filename:
            return FileCategory.STATUS
        elif "_COMPLETE.MD" in filename:
            return FileCategory.COMPLETE
        
        # Cache and temp files
        elif any(cache in file_path for cache in [
            ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__"
        ]):
            return FileCategory.CACHE
        elif file_path.startswith("temp_") or file_path.startswith("_temp_"):
            return FileCategory.TEMP
        elif file_path.endswith(".log"):
            return FileCategory.LOG
        
        # Default to obsolete for unknown files
        return FileCategory.OBSOLETE
    
    def _optimize_file_order(
        self, mappings: list[FileMapping]
    ) -> list[FileMapping]:
        """
        Sort file operations by directory to minimize disk seeks.
        
        Args:
            mappings: List of file mappings
            
        Returns:
            Sorted list of file mappings
        """
        return sorted(
            mappings,
            key=lambda m: (
                os.path.dirname(m.source),
                os.path.dirname(m.destination)
            )
        )
    
    def detect_code_duplicates(self, file_path: str) -> dict:
        """
        Detect code duplicates using analysis_tools DuplicationDetector.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Duplication report dictionary
        """
        return self.duplication_detector.analyze_file(file_path)
    
    def remove_files(
        self, files: list[str], dry_run: bool = False
    ) -> list[FileOperation]:
        """
        Remove files and track operations.
        
        Args:
            files: List of file paths to remove
            dry_run: If True, simulate without making changes
            
        Returns:
            List of file operations
        """
        from datetime import datetime
        
        operations = []
        for file_path in files:
            try:
                if not dry_run:
                    Path(file_path).unlink(missing_ok=True)
                
                operations.append(FileOperation(
                    operation="remove",
                    source=file_path,
                    destination=None,
                    timestamp=datetime.now(),
                    success=True,
                ))
            except Exception as e:
                operations.append(FileOperation(
                    operation="remove",
                    source=file_path,
                    destination=None,
                    timestamp=datetime.now(),
                    success=False,
                    error_message=str(e),
                ))
        
        return operations
    
    def categorize_script(self, script_path: str) -> str:
        """
        Determine appropriate category for utility script.
        
        Args:
            script_path: Path to script file
            
        Returns:
            Category name (freesound, backup, validation, etc.)
        """
        filename = os.path.basename(script_path).lower()
        
        # Freesound operations
        if any(keyword in filename for keyword in [
            "freesound", "fetch_freesound", "visualize_freesound"
        ]):
            return "freesound"
        
        # Backup management
        elif any(keyword in filename for keyword in [
            "backup", "restore", "checkpoint"
        ]):
            return "backup"
        
        # Validation
        elif any(keyword in filename for keyword in [
            "validate", "verify", "check"
        ]):
            return "validation"
        
        # Generation
        elif any(keyword in filename for keyword in [
            "generate", "create", "build"
        ]):
            return "generation"
        
        # Testing
        elif any(keyword in filename for keyword in [
            "test_", "testing"
        ]):
            return "testing"
        
        # Analysis
        elif any(keyword in filename for keyword in [
            "analyze", "analysis", "detect", "scan"
        ]):
            return "analysis"
        
        # Default to analysis
        return "analysis"
    
    def update_file_references(
        self,
        file_path: str,
        old_path: str,
        new_path: str,
        dry_run: bool = False,
    ) -> bool:
        """
        Update file path references within a file using pathlib.
        
        Args:
            file_path: Path to file to update
            old_path: Old path to replace
            new_path: New path to use
            dry_run: If True, simulate without making changes
            
        Returns:
            True if successful
        """
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                return False
            
            # Read file content
            content = file_path_obj.read_text(encoding='utf-8')
            
            # Replace old path with new path
            updated_content = content.replace(old_path, new_path)
            
            # Write back if changed and not dry run
            if updated_content != content and not dry_run:
                file_path_obj.write_text(updated_content, encoding='utf-8')
            
            return updated_content != content
        except Exception as e:
            raise FileOperationError(
                phase=CleanupPhase.SCRIPT_ORGANIZATION,
                message=f"Failed to update file references: {e}",
                file_path=file_path,
            )
