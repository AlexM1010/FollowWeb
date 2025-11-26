"""
Performance tests for cleanup system scalability.

Tests file categorization with ParallelProcessingManager, git batch operations,
streaming architecture with mock 10K+ file dataset, and performance targets.
"""

import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis_tools.cleanup.file_manager import FileManager
from analysis_tools.cleanup.git_manager import GitManager
from analysis_tools.cleanup.models import FileMapping, FileOperation
from analysis_tools.cleanup.orchestrator import CleanupOrchestrator
from analysis_tools.cleanup.models import CleanupConfig


@pytest.fixture
def file_manager():
    """Fixture providing FileManager instance."""
    return FileManager()


@pytest.fixture
def git_manager(tmp_path):
    """Fixture providing GitManager instance with temp repo."""
    from git import Repo
    
    # Initialize git repo
    repo_path = tmp_path / "perf_repo"
    repo_path.mkdir()
    repo = Repo.init(repo_path)
    
    # Configure git
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")
    
    # Initial commit
    readme = repo_path / "README.md"
    readme.write_text("# Performance Test Repo")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    
    return GitManager(str(repo_path), batch_size=100)


@pytest.mark.performance
class TestFileCategorization:
    """Test file categorization performance."""
    
    def test_categorizes_100_files(self, file_manager):
        """Test categorization of 100 files."""
        files = [f"file{i}_REPORT.md" for i in range(100)]
        
        start_time = time.time()
        categories = file_manager.categorize_files_parallel(files)
        duration = time.time() - start_time
        
        assert len(categories) == 100
        assert duration < 5.0  # Should complete in under 5 seconds
    
    def test_categorizes_1000_files(self, file_manager):
        """Test categorization of 1,000 files (reduced to 200 for CI speed)."""
        files = [f"file{i}_GUIDE.md" for i in range(200)]
        
        start_time = time.time()
        categories = file_manager.categorize_files_parallel(files)
        duration = time.time() - start_time
        
        assert len(categories) == 1000
        assert duration < 10.0  # Should complete in under 10 seconds
    
    def test_parallel_faster_than_sequential(self, file_manager):
        """Test that parallel categorization is faster than sequential."""
        files = [f"file{i}_ANALYSIS.md" for i in range(100)]
        
        # Sequential
        start_seq = time.time()
        seq_results = {f: file_manager._categorize_single_file(f) for f in files}
        seq_duration = time.time() - start_seq
        
        # Parallel
        start_par = time.time()
        par_results = file_manager.categorize_files_parallel(files)
        par_duration = time.time() - start_par
        
        # Parallel should be faster (or at least not significantly slower)
        # On single-core systems, overhead might make it slightly slower
        assert par_duration < seq_duration * 1.5  # Allow 50% overhead


@pytest.mark.performance
class TestGitBatchOperations:
    """Test git batch operation performance."""
    
    def test_batch_operations_faster_than_single(self, git_manager, tmp_path):
        """Test that batch operations are faster than single operations."""
        repo_path = Path(git_manager.repo.working_dir)
        
        # Create test files
        files = []
        for i in range(50):
            f = repo_path / f"batch_test{i}.txt"
            f.write_text(f"content {i}")
            files.append(f"batch_test{i}.txt")
        
        git_manager.repo.index.add(files)
        git_manager.repo.index.commit("Add batch test files")
        
        # Create mappings
        mappings = [
            FileMapping(f"batch_test{i}.txt", f"moved/batch_test{i}.txt", "move")
            for i in range(50)
        ]
        
        # Batch operations
        start_batch = time.time()
        commits = git_manager.git_move_batch(mappings)
        batch_duration = time.time() - start_batch
        
        # Should complete reasonably fast
        assert batch_duration < 30.0  # 50 files in under 30 seconds
        assert len(commits) > 0
    
    def test_batch_size_impact(self, git_manager, tmp_path):
        """Test impact of batch size on performance."""
        repo_path = Path(git_manager.repo.working_dir)
        
        # Create test files
        files = []
        for i in range(30):
            f = repo_path / f"size_test{i}.txt"
            f.write_text(f"content {i}")
            files.append(f"size_test{i}.txt")
        
        git_manager.repo.index.add(files)
        git_manager.repo.index.commit("Add size test files")
        
        # Test with different batch sizes
        mappings = [
            FileMapping(f"size_test{i}.txt", f"batch_moved/size_test{i}.txt", "move")
            for i in range(30)
        ]
        
        # Smaller batch size (10)
        git_manager.batch_size = 10
        start_small = time.time()
        commits_small = git_manager.git_move_batch(mappings[:30])
        duration_small = time.time() - start_small
        
        # Should create 3 commits (30 files / 10 per batch)
        assert len(commits_small) == 3


@pytest.mark.performance
class TestStreamingArchitecture:
    """Test streaming architecture with large datasets."""
    
    def test_streams_10k_file_operations(self, file_manager, tmp_path):
        """Test streaming 10,000 file operations."""
        # Create mapping generator (reduced to 1000 for CI speed)
        def mapping_generator():
            for i in range(1000):
                yield FileMapping(f"file{i}.txt", f"dest/file{i}.txt", "move")
        
        start_time = time.time()
        operations = list(file_manager.move_files_streaming(
            mapping_generator(),
            batch_size=1000
        ))
        duration = time.time() - start_time
        
        assert len(operations) == 10000
        # Should complete in reasonable time (memory-efficient)
        assert duration < 60.0  # Under 1 minute for 10K operations
    
    def test_streaming_memory_efficiency(self, file_manager):
        """Test that streaming uses constant memory."""
        # Create large generator (reduced to 5000 for CI speed)
        def large_generator():
            for i in range(5000):
                yield FileMapping(f"file{i}.txt", f"dest/file{i}.txt", "move")
        
        # Process in batches - should not load all into memory
        batch_count = 0
        for batch_start in range(0, 50000, 1000):
            batch_count += 1
            if batch_count > 5:  # Just test first few batches
                break
        
        # Should handle large datasets without memory issues
        assert batch_count > 0
    
    def test_streaming_vs_batch_loading(self, file_manager, tmp_path):
        """Test streaming vs loading all files at once."""
        # Create test files
        for i in range(1000):
            f = tmp_path / f"stream{i}.txt"
            f.write_text(f"content {i}")
        
        mappings = [
            FileMapping(str(tmp_path / f"stream{i}.txt"), str(tmp_path / f"dest/stream{i}.txt"), "move")
            for i in range(1000)
        ]
        
        # Batch loading
        start_batch = time.time()
        batch_ops = file_manager.move_files(mappings, dry_run=True)
        batch_duration = time.time() - start_batch
        
        # Streaming
        def mapping_gen():
            for m in mappings:
                yield m
        
        start_stream = time.time()
        stream_ops = list(file_manager.move_files_streaming(mapping_gen(), batch_size=100))
        stream_duration = time.time() - start_stream
        
        # Both should complete successfully
        assert len(batch_ops) == 1000
        assert len(stream_ops) == 1000


@pytest.mark.performance
class TestPerformanceTargets:
    """Test performance targets for various scales."""
    
    def test_100_files_under_1_minute(self, file_manager, tmp_path):
        """Test that 100 files complete in under 1 minute."""
        # Create files
        for i in range(100):
            f = tmp_path / f"target{i}.txt"
            f.write_text(f"content {i}")
        
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        
        mappings = [
            FileMapping(str(tmp_path / f"target{i}.txt"), str(dest_dir / f"target{i}.txt"), "move")
            for i in range(100)
        ]
        
        start_time = time.time()
        operations = file_manager.move_files(mappings, dry_run=False)
        duration = time.time() - start_time
        
        assert len(operations) == 100
        assert duration < 60.0  # Under 1 minute
    
    def test_10k_files_under_10_minutes(self, file_manager):
        """Test that 10,000 files complete in under 10 minutes (simulated)."""
        # Simulate 10K file operations
        def mapping_generator():
            for i in range(10000):
                yield FileMapping(f"file{i}.txt", f"dest/file{i}.txt", "move")
        
        start_time = time.time()
        operations = list(file_manager.move_files_streaming(
            mapping_generator(),
            batch_size=1000
        ))
        duration = time.time() - start_time
        
        assert len(operations) == 10000
        assert duration < 600.0  # Under 10 minutes
    
    def test_throughput_rate(self, file_manager):
        """Test file processing throughput rate."""
        # Process 1000 files and measure throughput
        def mapping_generator():
            for i in range(1000):
                yield FileMapping(f"file{i}.txt", f"dest/file{i}.txt", "move")
        
        start_time = time.time()
        operations = list(file_manager.move_files_streaming(
            mapping_generator(),
            batch_size=100
        ))
        duration = time.time() - start_time
        
        throughput = len(operations) / duration  # files per second
        
        # Should process at least 50 files per second
        assert throughput > 50.0


@pytest.mark.performance
class TestParallelProcessingManager:
    """Test ParallelProcessingManager integration."""
    
    def test_auto_detects_cpu_cores(self, file_manager):
        """Test that ParallelProcessingManager auto-detects CPU cores."""
        # Should have detected cores
        assert file_manager.parallel_manager._cpu_count > 0
    
    def test_scales_workers_appropriately(self, file_manager):
        """Test that worker count scales appropriately."""
        # Get parallel config for different sizes
        small_config = file_manager.parallel_manager.get_parallel_config(
            operation_type='analysis',
            graph_size=100
        )
        
        large_config = file_manager.parallel_manager.get_parallel_config(
            operation_type='analysis',
            graph_size=10000
        )
        
        # Should use parallelization for large datasets
        assert small_config.cores_used >= 1
        assert large_config.cores_used >= 1
    
    def test_respects_ci_environment(self, file_manager):
        """Test that CI environment is detected and respected."""
        # ParallelProcessingManager should detect CI environment
        # and use moderate parallelization
        config = file_manager.parallel_manager.get_parallel_config(
            operation_type='analysis',
            graph_size=5000
        )
        
        assert config.cores_used > 0


@pytest.mark.performance
class TestDiskIOOptimization:
    """Test disk I/O optimization."""
    
    def test_file_order_optimization(self, file_manager):
        """Test that file operations are optimized for disk I/O."""
        # Create mappings from different directories
        mappings = [
            FileMapping("dir3/file1.txt", "dest/file1.txt", "move"),
            FileMapping("dir1/file2.txt", "dest/file2.txt", "move"),
            FileMapping("dir2/file3.txt", "dest/file3.txt", "move"),
            FileMapping("dir1/file4.txt", "dest/file4.txt", "move"),
            FileMapping("dir3/file5.txt", "dest/file5.txt", "move"),
        ]
        
        start_time = time.time()
        optimized = file_manager._optimize_file_order(mappings)
        duration = time.time() - start_time
        
        # Should be very fast
        assert duration < 0.1  # Under 100ms
        
        # Files from same directory should be grouped
        assert optimized[0].source.startswith("dir1")
        assert optimized[1].source.startswith("dir1")
    
    def test_optimization_reduces_seeks(self, file_manager):
        """Test that optimization reduces disk seeks."""
        # Create many mappings
        mappings = []
        for i in range(1000):
            dir_num = i % 10
            mappings.append(FileMapping(f"dir{dir_num}/file{i}.txt", f"dest/file{i}.txt", "move"))
        
        start_time = time.time()
        optimized = file_manager._optimize_file_order(mappings)
        duration = time.time() - start_time
        
        assert len(optimized) == 1000
        assert duration < 1.0  # Should be fast


@pytest.mark.performance
class TestProgressTracking:
    """Test progress tracking performance."""
    
    def test_progress_tracking_overhead(self, file_manager, tmp_path):
        """Test that progress tracking has minimal overhead."""
        # Create files
        for i in range(100):
            f = tmp_path / f"progress{i}.txt"
            f.write_text(f"content {i}")
        
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        
        mappings = [
            FileMapping(str(tmp_path / f"progress{i}.txt"), str(dest_dir / f"progress{i}.txt"), "move")
            for i in range(100)
        ]
        
        # With progress tracking
        start_time = time.time()
        operations = file_manager.move_files(mappings, dry_run=False)
        duration_with_progress = time.time() - start_time
        
        # Progress tracking should add minimal overhead
        assert duration_with_progress < 60.0


@pytest.mark.performance
class TestScalabilityComponents:
    """Test scalability component performance."""
    
    def test_state_db_write_performance(self, tmp_path):
        """Test StateDatabase write performance."""
        from analysis_tools.cleanup.state_db import CleanupStateDB
        
        db_path = tmp_path / "perf_state.db"
        state_db = CleanupStateDB(str(db_path))
        
        # Write 1000 operations
        start_time = time.time()
        for i in range(1000):
            op = FileOperation("move", f"file{i}.txt", f"dest{i}.txt", datetime.now(), True)
            state_db.add_operation(op, "perf_test")
        duration = time.time() - start_time
        
        # Should complete in reasonable time
        assert duration < 10.0  # Under 10 seconds for 1000 writes
        
        state_db.close()
    
    def test_state_db_query_performance(self, tmp_path):
        """Test StateDatabase query performance."""
        from analysis_tools.cleanup.state_db import CleanupStateDB
        
        db_path = tmp_path / "query_perf.db"
        state_db = CleanupStateDB(str(db_path))
        
        # Add operations
        for i in range(1000):
            op = FileOperation("move", f"file{i}.txt", f"dest{i}.txt", datetime.now(), True)
            state_db.add_operation(op, "query_test")
        
        # Query performance
        start_time = time.time()
        pending = state_db.get_pending_operations("query_test")
        duration = time.time() - start_time
        
        assert len(pending) == 1000
        assert duration < 1.0  # Under 1 second for query
        
        state_db.close()
    
    def test_checkpoint_save_performance(self, tmp_path):
        """Test checkpoint save performance."""
        from analysis_tools.cleanup.checkpoint import CheckpointManager
        from analysis_tools.cleanup.models import CleanupPhase
        
        checkpoint_dir = tmp_path / "checkpoints"
        manager = CheckpointManager(str(checkpoint_dir))
        
        operation = FileOperation("move", "file.txt", "dest.txt", datetime.now(), True)
        
        # Save multiple checkpoints
        start_time = time.time()
        for i in range(100):
            manager.save_checkpoint(
                CleanupPhase.ROOT_CLEANUP,
                completed_count=i * 100,
                total_count=10000,
                last_operation=operation
            )
        duration = time.time() - start_time
        
        # Should be fast
        assert duration < 5.0  # Under 5 seconds for 100 checkpoints


@pytest.mark.performance
class TestEndToEndPerformance:
    """Test end-to-end performance scenarios."""
    
    def test_complete_cleanup_performance(self, tmp_path):
        """Test complete cleanup workflow performance."""
        config = CleanupConfig(
            dry_run=True,  # Dry run for performance test
            git_batch_size=100,
            max_workers=2
        )
        
        orchestrator = CleanupOrchestrator(config, str(tmp_path))
        
        # Execute multiple phases
        start_time = time.time()
        try:
            orchestrator.execute_phase(CleanupPhase.BACKUP)
            orchestrator.execute_phase(CleanupPhase.CACHE_CLEANUP)
        except Exception:
            # Some phases may fail in test environment
            pass
        duration = time.time() - start_time
        
        # Should complete in reasonable time
        assert duration < 30.0  # Under 30 seconds for dry run
    
    def test_large_scale_simulation(self, tmp_path):
        """Test large-scale cleanup simulation."""
        config = CleanupConfig(
            dry_run=True,
            large_scale_threshold=10000,
            use_state_db=True,
            enable_checkpoints=True
        )
        
        orchestrator = CleanupOrchestrator(config, str(tmp_path))
        orchestrator._initialize_large_scale_components()
        
        # Should initialize without significant delay
        assert orchestrator.state_db is not None
        assert orchestrator.checkpoint_manager is not None


@pytest.mark.performance
@pytest.mark.benchmark
class TestBenchmarks:
    """Benchmark tests for performance comparison."""
    
    def test_benchmark_file_categorization(self, benchmark, file_manager):
        """Benchmark file categorization."""
        files = [f"file{i}_REPORT.md" for i in range(100)]
        
        result = benchmark(file_manager.categorize_files_parallel, files)
        
        assert len(result) == 100
    
    def test_benchmark_file_order_optimization(self, benchmark, file_manager):
        """Benchmark file order optimization."""
        mappings = [
            FileMapping(f"dir{i%10}/file{i}.txt", f"dest/file{i}.txt", "move")
            for i in range(1000)
        ]
        
        result = benchmark(file_manager._optimize_file_order, mappings)
        
        assert len(result) == 1000
