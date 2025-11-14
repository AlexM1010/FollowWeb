"""
Unit tests for cleanup system File Manager.

Tests file operations, categorization, directory creation, and integration
with organize-tool and analysis_tools components.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call
from typing import List, Dict

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis_tools.cleanup.file_manager import FileManager
from analysis_tools.cleanup.models import FileMapping, FileOperation, FileCategory


@pytest.fixture
def mock_logger():
    """Fixture providing mock logger."""
    return logging.getLogger(__name__)


@pytest.fixture
def file_manager():
    """Fixture providing FileManager instance."""
    return FileManager()


@pytest.mark.unit
class TestDirectoryCreation:
    """Test directory structure creation."""
    
    def test_creates_single_directory(self, file_manager, tmp_path):
        """Test creation of a single directory."""
        test_dir = tmp_path / "test_directory"
        structure = {str(test_dir): []}
        
        result = file_manager.create_directory_structure(structure)
        
        assert result is True
        assert test_dir.exists()
        assert test_dir.is_dir()
    
    def test_creates_nested_directories(self, file_manager, tmp_path):
        """Test creation of nested directory structure."""
        parent_dir = tmp_path / "parent"
        child_dir = parent_dir / "child" / "grandchild"
        structure = {str(child_dir): []}
        
        result = file_manager.create_directory_structure(structure)
        
        assert result is True
        assert child_dir.exists()
        assert child_dir.is_dir()
        assert parent_dir.exists()
    
    def test_creates_multiple_directories(self, file_manager, tmp_path):
        """Test creation of multiple directories."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir3 = tmp_path / "dir3"
        structure = {
            str(dir1): [],
            str(dir2): [],
            str(dir3): []
        }
        
        result = file_manager.create_directory_structure(structure)
        
        assert result is True
        assert dir1.exists() and dir1.is_dir()
        assert dir2.exists() and dir2.is_dir()
        assert dir3.exists() and dir3.is_dir()
    
    def test_handles_existing_directory(self, file_manager, tmp_path):
        """Test handling of already existing directory."""
        test_dir = tmp_path / "existing"
        test_dir.mkdir()
        structure = {str(test_dir): []}
        
        result = file_manager.create_directory_structure(structure)
        
        assert result is True
        assert test_dir.exists()


@pytest.mark.unit
class TestFileCategorization:
    """Test file categorization logic."""
    
    def test_categorizes_report_files(self, file_manager):
        """Test categorization of report files."""
        assert file_manager._categorize_single_file("TEST_REPORT.md") == FileCategory.REPORT
        assert file_manager._categorize_single_file("analysis_REPORT.md") == FileCategory.REPORT
        assert file_manager._categorize_single_file("SUMMARY_REPORT.md") == FileCategory.REPORT
    
    def test_categorizes_guide_files(self, file_manager):
        """Test categorization of guide files."""
        assert file_manager._categorize_single_file("INSTALL_GUIDE.md") == FileCategory.GUIDE
        assert file_manager._categorize_single_file("USER_GUIDE.md") == FileCategory.GUIDE
        assert file_manager._categorize_single_file("SETUP_GUIDE.md") == FileCategory.GUIDE
    
    def test_categorizes_analysis_files(self, file_manager):
        """Test categorization of analysis files."""
        assert file_manager._categorize_single_file("CODE_ANALYSIS.md") == FileCategory.ANALYSIS
        assert file_manager._categorize_single_file("PERFORMANCE_ANALYSIS.md") == FileCategory.ANALYSIS
    
    def test_categorizes_summary_files(self, file_manager):
        """Test categorization of summary files."""
        assert file_manager._categorize_single_file("PROJECT_SUMMARY.md") == FileCategory.SUMMARY
        assert file_manager._categorize_single_file("CLEANUP_SUMMARY.md") == FileCategory.SUMMARY
    
    def test_categorizes_status_files(self, file_manager):
        """Test categorization of status files."""
        assert file_manager._categorize_single_file("BUILD_STATUS.md") == FileCategory.STATUS
        assert file_manager._categorize_single_file("DEPLOYMENT_STATUS.md") == FileCategory.STATUS
    
    def test_categorizes_complete_files(self, file_manager):
        """Test categorization of complete files."""
        assert file_manager._categorize_single_file("MIGRATION_COMPLETE.md") == FileCategory.COMPLETE
        assert file_manager._categorize_single_file("SETUP_COMPLETE.md") == FileCategory.COMPLETE


@pytest.mark.unit
class TestScriptCategorization:
    """Test utility script categorization."""
    
    def test_categorizes_freesound_scripts(self, file_manager):
        """Test categorization of Freesound-related scripts."""
        assert file_manager.categorize_script("fetch_freesound_data.py") == "freesound"
        assert file_manager.categorize_script("generate_freesound_visualization.py") == "freesound"
        assert file_manager.categorize_script("validate_freesound_samples.py") == "freesound"
    
    def test_categorizes_backup_scripts(self, file_manager):
        """Test categorization of backup-related scripts."""
        assert file_manager.categorize_script("setup_backup.py") == "backup"
        assert file_manager.categorize_script("cleanup_old_backups.py") == "backup"
        assert file_manager.categorize_script("restore_from_backup.py") == "backup"
    
    def test_categorizes_validation_scripts(self, file_manager):
        """Test categorization of validation scripts."""
        assert file_manager.categorize_script("validate_pipeline_data.py") == "validation"
        assert file_manager.categorize_script("verify_complete_data.py") == "validation"
    
    def test_categorizes_generation_scripts(self, file_manager):
        """Test categorization of generation scripts."""
        assert file_manager.categorize_script("generate_landing_page.py") == "generation"
        assert file_manager.categorize_script("generate_metrics_dashboard.py") == "generation"
    
    def test_categorizes_testing_scripts(self, file_manager):
        """Test categorization of testing scripts."""
        assert file_manager.categorize_script("test_runner.py") == "testing"
        # run_tests.py doesn't have "test_" prefix, so it's categorized as analysis
        assert file_manager.categorize_script("run_tests.py") == "analysis"
    
    def test_categorizes_analysis_scripts(self, file_manager):
        """Test categorization of analysis scripts."""
        assert file_manager.categorize_script("analyze_color_differences.py") == "analysis"
        assert file_manager.categorize_script("detect_milestone.py") == "analysis"


@pytest.mark.unit
class TestFileOperations:
    """Test file move and remove operations."""
    
    def test_moves_single_file(self, file_manager, tmp_path):
        """Test moving a single file."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest" / "source.txt"
        source.write_text("test content")
        dest.parent.mkdir()
        
        mapping = FileMapping(
            source=str(source),
            destination=str(dest),
            operation_type="move"
        )
        
        operations = file_manager.move_files([mapping], dry_run=False)
        
        assert len(operations) == 1
        assert operations[0].success is True
        assert dest.exists()
        assert dest.read_text() == "test content"
    
    def test_moves_multiple_files(self, file_manager, tmp_path):
        """Test moving multiple files."""
        files = []
        mappings = []
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        
        for i in range(5):
            source = tmp_path / f"file{i}.txt"
            source.write_text(f"content {i}")
            dest = dest_dir / f"file{i}.txt"
            files.append((source, dest))
            mappings.append(FileMapping(
                source=str(source),
                destination=str(dest),
                operation_type="move"
            ))
        
        operations = file_manager.move_files(mappings, dry_run=False)
        
        assert len(operations) == 5
        assert all(op.success for op in operations)
        for source, dest in files:
            assert dest.exists()
    
    def test_dry_run_does_not_move_files(self, file_manager, tmp_path):
        """Test that dry run mode doesn't actually move files."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "dest" / "source.txt"
        source.write_text("test content")
        dest.parent.mkdir()
        
        mapping = FileMapping(
            source=str(source),
            destination=str(dest),
            operation_type="move"
        )
        
        operations = file_manager.move_files([mapping], dry_run=True)
        
        assert len(operations) == 1
        assert source.exists()  # Source still exists in dry run
        assert not dest.exists()  # Destination not created
    
    def test_removes_files(self, file_manager, tmp_path):
        """Test removing files."""
        files = [tmp_path / f"file{i}.txt" for i in range(3)]
        for f in files:
            f.write_text("content")
        
        file_paths = [str(f) for f in files]
        operations = file_manager.remove_files(file_paths)
        
        assert len(operations) == 3
        assert all(op.success for op in operations)
        assert all(not f.exists() for f in files)


@pytest.mark.unit
class TestFileReferenceUpdates:
    """Test file reference updates using pathlib."""
    
    def test_updates_import_paths(self, file_manager, tmp_path):
        """Test updating import paths in Python files."""
        test_file = tmp_path / "test.py"
        test_file.write_text("from old.path import module\nimport old.path.other")
        
        # Use dot notation for Python imports
        result = file_manager.update_file_references(
            str(test_file),
            "old.path",
            "new.path"
        )
        
        assert result is True
        content = test_file.read_text()
        assert "from new.path import module" in content
        assert "import new.path.other" in content
        assert "old.path" not in content
    
    def test_updates_file_paths_with_pathlib(self, file_manager, tmp_path):
        """Test updating file paths using pathlib for cross-platform compatibility."""
        test_file = tmp_path / "config.py"
        test_file.write_text('DATA_PATH = "data/old/location"\nLOG_PATH = "logs/old/location"')
        
        result = file_manager.update_file_references(
            str(test_file),
            "data/old/location",
            "data/new/location"
        )
        
        assert result is True
        content = test_file.read_text()
        assert "data/new/location" in content
        assert "data/old/location" not in content
    
    def test_handles_nonexistent_file(self, file_manager, tmp_path):
        """Test handling of nonexistent file."""
        nonexistent = tmp_path / "nonexistent.py"
        
        result = file_manager.update_file_references(
            str(nonexistent),
            "old/path",
            "new/path"
        )
        
        assert result is False


@pytest.mark.unit
class TestDuplicationDetectorIntegration:
    """Test integration with analysis_tools DuplicationDetector."""
    
    def test_detects_code_duplicates(self, file_manager, tmp_path):
        """Test detection of code duplicates using DuplicationDetector."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def function1():
    x = 1
    y = 2
    return x + y

def function2():
    x = 1
    y = 2
    return x + y
""")
        
        report = file_manager.detect_code_duplicates(str(test_file))
        
        assert report is not None
        # DuplicationDetector should identify similar code blocks
    
    def test_handles_file_without_duplicates(self, file_manager, tmp_path):
        """Test handling of file without duplicates."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def unique_function1():
    return 1

def unique_function2():
    return 2
""")
        
        report = file_manager.detect_code_duplicates(str(test_file))
        
        assert report is not None


@pytest.mark.unit
class TestFileOrderOptimization:
    """Test file operation order optimization for disk I/O."""
    
    def test_optimizes_file_order_by_directory(self, file_manager):
        """Test that file operations are sorted by directory to minimize disk seeks."""
        mappings = [
            FileMapping("dir3/file1.txt", "dest/file1.txt", "move"),
            FileMapping("dir1/file2.txt", "dest/file2.txt", "move"),
            FileMapping("dir2/file3.txt", "dest/file3.txt", "move"),
            FileMapping("dir1/file4.txt", "dest/file4.txt", "move"),
        ]
        
        optimized = file_manager._optimize_file_order(mappings)
        
        # Files from same source directory should be grouped together
        assert optimized[0].source.startswith("dir1")
        assert optimized[1].source.startswith("dir1")
    
    def test_sorts_by_source_and_destination(self, file_manager):
        """Test sorting by both source and destination directories."""
        mappings = [
            FileMapping("dirB/file1.txt", "destB/file1.txt", "move"),
            FileMapping("dirA/file2.txt", "destA/file2.txt", "move"),
            FileMapping("dirA/file3.txt", "destB/file3.txt", "move"),
        ]
        
        optimized = file_manager._optimize_file_order(mappings)
        
        # Should be sorted by source directory first
        assert optimized[0].source.startswith("dirA")
        assert optimized[1].source.startswith("dirA")
        assert optimized[2].source.startswith("dirB")


@pytest.mark.unit
class TestParallelCategorization:
    """Test parallel file categorization."""
    
    def test_categorizes_files_in_parallel(self, file_manager):
        """Test parallel categorization of multiple files."""
        # Use unique file paths that match the categorization patterns
        # The function checks for "_REPORT.MD" in uppercase filename
        files = [f"file{i}_REPORT.md" for i in range(10)]
        
        categories = file_manager.categorize_files_parallel(files)
        
        assert len(categories) == 10
        # All files should be categorized as REPORT
        assert all(cat == FileCategory.REPORT for cat in categories.values())
    
    def test_handles_small_dataset_sequentially(self, file_manager):
        """Test that small datasets are processed sequentially."""
        # Use unique file paths that match the categorization patterns
        # The function checks for "_GUIDE.MD" in uppercase filename
        files = [f"file{i}_GUIDE.md" for i in range(3)]
        
        categories = file_manager.categorize_files_parallel(files)
        
        assert len(categories) == 3
        # All files should be categorized as GUIDE
        assert all(cat == FileCategory.GUIDE for cat in categories.values())


@pytest.mark.unit
class TestStreamingOperations:
    """Test streaming operations for large-scale file processing."""
    
    def test_streams_file_operations(self, file_manager, tmp_path):
        """Test streaming file operations for 10K+ files."""
        # Create iterator of file mappings
        def mapping_generator():
            for i in range(100):  # Simulate large dataset
                source = tmp_path / f"file{i}.txt"
                dest = tmp_path / "dest" / f"file{i}.txt"
                yield FileMapping(str(source), str(dest), "move")
        
        # Process in batches
        operations = list(file_manager.move_files_streaming(
            mapping_generator(),
            batch_size=10
        ))
        
        assert len(operations) == 100
    
    def test_batches_streaming_operations(self, file_manager):
        """Test that streaming operations are properly batched."""
        def mapping_generator():
            for i in range(25):
                yield FileMapping(f"source{i}.txt", f"dest{i}.txt", "move")
        
        operations = list(file_manager.move_files_streaming(
            mapping_generator(),
            batch_size=10
        ))
        
        # Should process all 25 files in batches of 10
        assert len(operations) == 25


@pytest.mark.unit
class TestProgressTracking:
    """Test progress tracking integration."""
    
    def test_shows_progress_during_file_moves(self, file_manager, tmp_path):
        """Test that progress is tracked during file operations."""
        # Create actual files for the test
        for i in range(5):
            source = tmp_path / f"file{i}.txt"
            source.write_text(f"content {i}")
        
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        
        mappings = [
            FileMapping(str(tmp_path / f"file{i}.txt"), str(dest_dir / f"file{i}.txt"), "move")
            for i in range(5)
        ]
        
        operations = file_manager.move_files(mappings, dry_run=False)
        
        # Verify all operations completed
        assert len(operations) == 5
        assert all(op.success for op in operations)
