"""
Unit tests for cleanup_old_backups script.

Tests backup file discovery, age-based retention, and count-based retention
with mocked file operations to avoid actual file system changes.
"""

import logging
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add cleanup script to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.backup.cleanup_old_backups import cleanup_old_backups


class TestBackupFileDiscovery:
    """Test backup file discovery with glob patterns."""

    def test_discovers_backup_files_with_pattern(self, tmp_path):
        """Test that backup files matching the pattern are discovered."""
        # Create test backup files
        backup_files = [
            "freesound_library_backup_100nodes_20231101_120000.pkl",
            "freesound_library_backup_200nodes_20231102_120000.pkl",
            "freesound_library_backup_300nodes_20231103_120000.pkl",
        ]
        
        for filename in backup_files:
            (tmp_path / filename).touch()
        
        # Create non-backup files that should be ignored
        (tmp_path / "freesound_library.pkl").touch()
        (tmp_path / "other_file.txt").touch()
        
        logger = logging.getLogger(__name__)
        
        with patch('scripts.backup.cleanup_old_backups.safe_file_cleanup', return_value=True):
            # Set retention to 0 days so all backups are candidates for deletion
            # But keep max_backups=1 so only 2 oldest are deleted
            deleted_count = cleanup_old_backups(
                checkpoint_dir=str(tmp_path),
                max_backups=1,
                retention_days=0,
                logger=logger
            )
        
        # Should find 3 backup files, keep 1 newest, delete 2 oldest
        assert deleted_count == 2

    def test_handles_empty_directory(self, tmp_path):
        """Test handling of directory with no backup files."""
        logger = logging.getLogger(__name__)
        
        deleted_count = cleanup_old_backups(
            checkpoint_dir=str(tmp_path),
            max_backups=5,
            retention_days=7,
            logger=logger
        )
        
        assert deleted_count == 0

    def test_handles_nonexistent_directory(self, tmp_path):
        """Test handling of nonexistent directory."""
        nonexistent_dir = tmp_path / "does_not_exist"
        logger = logging.getLogger(__name__)
        
        deleted_count = cleanup_old_backups(
            checkpoint_dir=str(nonexistent_dir),
            max_backups=5,
            retention_days=7,
            logger=logger
        )
        
        assert deleted_count == 0


class TestAgeBasedRetention:
    """Test age-based retention with mocked file timestamps."""

    def test_deletes_backups_older_than_retention_period(self, tmp_path):
        """Test that backups older than retention period are deleted."""
        logger = logging.getLogger(__name__)
        
        # Create backup files with different ages
        current_time = time.time()
        
        # Old backup (10 days old)
        old_backup = tmp_path / "freesound_library_backup_100nodes_old.pkl"
        old_backup.touch()
        old_time = current_time - (10 * 86400)  # 10 days ago
        
        # Recent backup (3 days old)
        recent_backup = tmp_path / "freesound_library_backup_200nodes_recent.pkl"
        recent_backup.touch()
        recent_time = current_time - (3 * 86400)  # 3 days ago
        
        # Get the real stat objects and modify their mtime
        import os
        real_old_stat = old_backup.stat()
        real_recent_stat = recent_backup.stat()
        
        # Mock file modification times
        original_stat = Path.stat
        
        def mock_stat_method(path_self, *args, **kwargs):
            # Call original for directory checks
            if path_self == tmp_path:
                return original_stat(path_self)
            
            # Mock for backup files
            if 'old' in str(path_self):
                stat_obj = Mock()
                stat_obj.st_mtime = old_time
                stat_obj.st_mode = real_old_stat.st_mode
                return stat_obj
            elif 'recent' in str(path_self):
                stat_obj = Mock()
                stat_obj.st_mtime = recent_time
                stat_obj.st_mode = real_recent_stat.st_mode
                return stat_obj
            else:
                return original_stat(path_self)
        
        with patch.object(Path, 'stat', mock_stat_method):
            with patch('scripts.backup.cleanup_old_backups.safe_file_cleanup', return_value=True) as mock_cleanup:
                deleted_count = cleanup_old_backups(
                    checkpoint_dir=str(tmp_path),
                    max_backups=1,  # Keep only 1, so old backup is beyond max_backups
                    retention_days=7,  # 7 day retention
                    logger=logger
                )
        
        # Only the old backup (10 days) should be deleted (beyond max_backups AND older than retention)
        assert deleted_count == 1

    def test_keeps_backups_within_retention_period(self, tmp_path):
        """Test that backups within retention period are kept."""
        logger = logging.getLogger(__name__)
        
        # Create backup files all within retention period
        current_time = time.time()
        
        backup1 = tmp_path / "freesound_library_backup_100nodes_1.pkl"
        backup1.touch()
        backup2 = tmp_path / "freesound_library_backup_200nodes_2.pkl"
        backup2.touch()
        
        # Both backups are 3 days old (within 7 day retention)
        recent_time = current_time - (3 * 86400)
        
        real_stat = backup1.stat()
        original_stat = Path.stat
        
        def mock_stat_method(path_self, *args, **kwargs):
            if path_self == tmp_path:
                return original_stat(path_self)
            
            if 'backup' in str(path_self):
                stat_obj = Mock()
                stat_obj.st_mtime = recent_time
                stat_obj.st_mode = real_stat.st_mode
                return stat_obj
            else:
                return original_stat(path_self)
        
        with patch.object(Path, 'stat', mock_stat_method):
            with patch('scripts.backup.cleanup_old_backups.safe_file_cleanup', return_value=True):
                deleted_count = cleanup_old_backups(
                    checkpoint_dir=str(tmp_path),
                    max_backups=10,
                    retention_days=7,
                    logger=logger
                )
        
        # No backups should be deleted
        assert deleted_count == 0


class TestCountBasedRetention:
    """Test count-based retention (keep N most recent)."""

    def test_keeps_n_most_recent_backups(self, tmp_path):
        """Test that only N most recent backups are kept."""
        logger = logging.getLogger(__name__)
        
        # Create 7 backup files
        current_time = time.time()
        backup_files = []
        
        for i in range(7):
            backup = tmp_path / f"freesound_library_backup_{i}00nodes_{i}.pkl"
            backup.touch()
            backup_files.append(backup)
        
        real_stat = backup_files[0].stat()
        original_stat = Path.stat
        
        # Mock file modification times (older to newer)
        def mock_stat_method(path_self, *args, **kwargs):
            if path_self == tmp_path:
                return original_stat(path_self)
            
            filename = str(path_self.name)
            for i in range(7):
                if f"_{i}00nodes_" in filename:
                    stat_obj = Mock()
                    # Older files have older timestamps
                    stat_obj.st_mtime = current_time - ((6 - i) * 86400)
                    stat_obj.st_mode = real_stat.st_mode
                    return stat_obj
            
            return original_stat(path_self)
        
        with patch.object(Path, 'stat', mock_stat_method):
            with patch('scripts.backup.cleanup_old_backups.safe_file_cleanup', return_value=True):
                deleted_count = cleanup_old_backups(
                    checkpoint_dir=str(tmp_path),
                    max_backups=3,  # Keep only 3 most recent
                    retention_days=0,  # Set to 0 to test count-based only
                    logger=logger
                )
        
        # Should delete 4 oldest backups (7 total - 3 kept = 4 deleted)
        assert deleted_count == 4

    def test_keeps_all_when_below_max_backups(self, tmp_path):
        """Test that all backups are kept when count is below max."""
        logger = logging.getLogger(__name__)
        
        # Create only 3 backup files
        for i in range(3):
            backup = tmp_path / f"freesound_library_backup_{i}00nodes.pkl"
            backup.touch()
        
        current_time = time.time()
        real_stat = (tmp_path / "freesound_library_backup_000nodes.pkl").stat()
        original_stat = Path.stat
        
        def mock_stat_method(path_self, *args, **kwargs):
            if path_self == tmp_path:
                return original_stat(path_self)
            
            if 'backup' in str(path_self):
                stat_obj = Mock()
                stat_obj.st_mtime = current_time - (3 * 86400)  # 3 days old
                stat_obj.st_mode = real_stat.st_mode
                return stat_obj
            else:
                return original_stat(path_self)
        
        with patch.object(Path, 'stat', mock_stat_method):
            with patch('scripts.backup.cleanup_old_backups.safe_file_cleanup', return_value=True):
                deleted_count = cleanup_old_backups(
                    checkpoint_dir=str(tmp_path),
                    max_backups=5,  # Max is higher than actual count
                    retention_days=7,
                    logger=logger
                )
        
        # No backups should be deleted
        assert deleted_count == 0


class TestSafeFileCleanupMocking:
    """Test that safe_file_cleanup is properly mocked to avoid actual deletions."""

    def test_mocks_safe_file_cleanup(self, tmp_path):
        """Test that safe_file_cleanup is called but doesn't delete files."""
        logger = logging.getLogger(__name__)
        
        # Create backup files
        backup1 = tmp_path / "freesound_library_backup_100nodes_1.pkl"
        backup1.touch()
        backup2 = tmp_path / "freesound_library_backup_200nodes_2.pkl"
        backup2.touch()
        
        current_time = time.time()
        old_time = current_time - (10 * 86400)  # 10 days old
        
        real_stat = backup1.stat()
        original_stat = Path.stat
        
        def mock_stat_method(path_self, *args, **kwargs):
            if path_self == tmp_path:
                return original_stat(path_self)
            
            if 'backup' in str(path_self):
                stat_obj = Mock()
                stat_obj.st_mtime = old_time
                stat_obj.st_mode = real_stat.st_mode
                return stat_obj
            else:
                return original_stat(path_self)
        
        with patch.object(Path, 'stat', mock_stat_method):
            with patch('scripts.backup.cleanup_old_backups.safe_file_cleanup', return_value=True) as mock_cleanup:
                deleted_count = cleanup_old_backups(
                    checkpoint_dir=str(tmp_path),
                    max_backups=1,
                    retention_days=7,
                    logger=logger
                )
        
        # Verify safe_file_cleanup was called
        assert mock_cleanup.called
        assert deleted_count == 1
        
        # Verify files still exist (not actually deleted)
        assert backup1.exists()
        assert backup2.exists()

    def test_handles_failed_cleanup(self, tmp_path):
        """Test handling when safe_file_cleanup fails."""
        logger = logging.getLogger(__name__)
        
        # Create backup files
        for i in range(3):
            backup = tmp_path / f"freesound_library_backup_{i}00nodes.pkl"
            backup.touch()
        
        current_time = time.time()
        old_time = current_time - (10 * 86400)
        
        real_stat = (tmp_path / "freesound_library_backup_000nodes.pkl").stat()
        original_stat = Path.stat
        
        def mock_stat_method(path_self, *args, **kwargs):
            if path_self == tmp_path:
                return original_stat(path_self)
            
            if 'backup' in str(path_self):
                stat_obj = Mock()
                stat_obj.st_mtime = old_time
                stat_obj.st_mode = real_stat.st_mode
                return stat_obj
            else:
                return original_stat(path_self)
        
        with patch.object(Path, 'stat', mock_stat_method):
            # Mock safe_file_cleanup to return False (failure)
            with patch('scripts.backup.cleanup_old_backups.safe_file_cleanup', return_value=False):
                deleted_count = cleanup_old_backups(
                    checkpoint_dir=str(tmp_path),
                    max_backups=1,
                    retention_days=7,
                    logger=logger
                )
        
        # No files should be counted as deleted when cleanup fails
        assert deleted_count == 0


class TestCorrectFileSelection:
    """Test that correct files are selected for deletion."""

    def test_selects_oldest_files_for_deletion(self, tmp_path):
        """Test that the oldest files are selected when exceeding max_backups."""
        logger = logging.getLogger(__name__)
        
        # Create 5 backup files with known timestamps
        current_time = time.time()
        
        backup_newest = tmp_path / "freesound_library_backup_500nodes_newest.pkl"
        backup_newest.touch()
        
        backup_new = tmp_path / "freesound_library_backup_400nodes_new.pkl"
        backup_new.touch()
        
        backup_mid = tmp_path / "freesound_library_backup_300nodes_mid.pkl"
        backup_mid.touch()
        
        backup_old = tmp_path / "freesound_library_backup_200nodes_old.pkl"
        backup_old.touch()
        
        backup_oldest = tmp_path / "freesound_library_backup_100nodes_oldest.pkl"
        backup_oldest.touch()
        
        # Track which files were attempted to be deleted
        deleted_files = []
        
        def mock_cleanup(filepath):
            deleted_files.append(Path(filepath).name)
            return True
        
        real_stat = backup_newest.stat()
        original_stat = Path.stat
        
        def mock_stat_method(path_self, *args, **kwargs):
            if path_self == tmp_path:
                return original_stat(path_self)
            
            filename = str(path_self.name)
            stat_obj = Mock()
            stat_obj.st_mode = real_stat.st_mode
            
            if 'newest' in filename:
                stat_obj.st_mtime = current_time - (1 * 86400)
            elif 'new' in filename:
                stat_obj.st_mtime = current_time - (2 * 86400)
            elif 'mid' in filename:
                stat_obj.st_mtime = current_time - (5 * 86400)
            elif 'old' in filename and 'oldest' not in filename:
                stat_obj.st_mtime = current_time - (10 * 86400)
            elif 'oldest' in filename:
                stat_obj.st_mtime = current_time - (15 * 86400)
            else:
                stat_obj.st_mtime = current_time
            
            return stat_obj
        
        with patch.object(Path, 'stat', mock_stat_method):
            with patch('scripts.backup.cleanup_old_backups.safe_file_cleanup', side_effect=mock_cleanup):
                deleted_count = cleanup_old_backups(
                    checkpoint_dir=str(tmp_path),
                    max_backups=2,  # Keep only 2 newest
                    retention_days=7,  # 7 day retention
                    logger=logger
                )
        
        # Should delete 2 files (5 total - 2 kept = 3 beyond max, but only 2 are older than 7 days)
        # Files beyond max_backups: mid (5 days), old (10 days), oldest (15 days)
        # Files older than 7 days: old (10 days), oldest (15 days)
        # Intersection: old and oldest
        assert deleted_count == 2
        
        # Verify the correct files were selected (oldest ones beyond retention)
        assert 'oldest' in ' '.join(deleted_files).lower()
        assert 'old' in ' '.join(deleted_files).lower()

    def test_preserves_main_checkpoint_file(self, tmp_path):
        """Test that the main checkpoint file is never deleted."""
        logger = logging.getLogger(__name__)
        
        # Create main checkpoint file (should never be deleted)
        main_checkpoint = tmp_path / "freesound_library.pkl"
        main_checkpoint.touch()
        
        # Create backup files
        backup1 = tmp_path / "freesound_library_backup_100nodes.pkl"
        backup1.touch()
        
        current_time = time.time()
        old_time = current_time - (10 * 86400)
        
        deleted_files = []
        
        def mock_cleanup(filepath):
            deleted_files.append(Path(filepath).name)
            return True
        
        real_stat = backup1.stat()
        original_stat = Path.stat
        
        def mock_stat_method(path_self, *args, **kwargs):
            if path_self == tmp_path:
                return original_stat(path_self)
            
            if 'backup' in str(path_self):
                stat_obj = Mock()
                stat_obj.st_mtime = old_time
                stat_obj.st_mode = real_stat.st_mode
                return stat_obj
            else:
                return original_stat(path_self)
        
        with patch.object(Path, 'stat', mock_stat_method):
            with patch('scripts.backup.cleanup_old_backups.safe_file_cleanup', side_effect=mock_cleanup):
                cleanup_old_backups(
                    checkpoint_dir=str(tmp_path),
                    max_backups=0,  # Delete all backups
                    retention_days=7,
                    logger=logger
                )
        
        # Main checkpoint should not be in deleted files
        assert "freesound_library.pkl" not in deleted_files
        
        # Only backup files should be deleted
        assert all("backup" in f for f in deleted_files)

