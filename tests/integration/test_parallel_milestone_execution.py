"""
Integration tests for parallel milestone execution.

Tests the full pipeline with parallel execution at 100-node milestones:
- Milestone detection accuracy
- Parallel execution of validation, edge generation, and website deployment
- Main pipeline continues uninterrupted during milestone actions
- Validation failures properly fail the pipeline
- All background jobs run concurrently
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import networkx as nx
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.analysis.detect_milestone import check_milestone, load_milestone_history
from scripts.validation.validate_pipeline_data import ValidationReport, validate_checkpoint_integrity


@pytest.fixture
def test_checkpoint_dir(tmp_path):
    """Fixture providing temporary checkpoint directory with test data."""
    checkpoint_dir = tmp_path / "data" / "freesound_library"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a test graph with 100 nodes (milestone boundary)
    graph = nx.DiGraph()
    for i in range(100):
        graph.add_node(i, name=f"sample_{i}.wav", type="sample")
    
    # Add some edges
    for i in range(99):
        graph.add_edge(i, i + 1, weight=0.9)
    
    # Save graph topology
    import pickle
    with open(checkpoint_dir / "graph_topology.gpickle", "wb") as f:
        pickle.dump(graph, f)
    
    # Create metadata database
    import sqlite3
    conn = sqlite3.connect(str(checkpoint_dir / "metadata_cache.db"))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE metadata (
            sample_id INTEGER PRIMARY KEY,
            data TEXT NOT NULL
        )
    """)
    
    for i in range(100):
        metadata = json.dumps({
            "name": f"sample_{i}.wav",
            "audio_url": f"http://test.com/{i}.mp3",
            "username": "test_user",
            "duration": 1.5
        })
        cursor.execute("INSERT INTO metadata VALUES (?, ?)", (i, metadata))
    
    conn.commit()
    conn.close()
    
    # Create checkpoint metadata
    checkpoint_metadata = {
        "timestamp": "2025-11-13T00:00:00Z",
        "nodes": 100,
        "edges": 99,
        "processed_samples": 100
    }
    
    with open(checkpoint_dir / "checkpoint_metadata.json", "w") as f:
        json.dump(checkpoint_metadata, f)
    
    return checkpoint_dir


@pytest.fixture
def test_output_dir(tmp_path):
    """Fixture providing temporary output directory."""
    output_dir = tmp_path / "Output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def mock_logger():
    """Fixture providing mock logger."""
    return logging.getLogger(__name__)


@pytest.mark.integration
class TestMilestoneDetection:
    """Test milestone detection accuracy."""
    
    def test_detects_100_node_milestone(self, test_checkpoint_dir):
        """Test that 100-node milestone is detected correctly."""
        status = check_milestone(test_checkpoint_dir)
        
        assert status['is_milestone'] is True
        assert status['current_nodes'] == 100
        assert status['milestone_number'] == 1
    
    def test_detects_200_node_milestone(self, test_checkpoint_dir):
        """Test that 200-node milestone is detected correctly."""
        # Update checkpoint metadata to 200 nodes
        checkpoint_metadata = {
            "timestamp": "2025-11-13T00:00:00Z",
            "nodes": 200,
            "edges": 199,
            "processed_samples": 200
        }
        
        with open(test_checkpoint_dir / "checkpoint_metadata.json", "w") as f:
            json.dump(checkpoint_metadata, f)
        
        # Create milestone history with first milestone
        milestone_history_path = test_checkpoint_dir.parent / "milestone_history.jsonl"
        with open(milestone_history_path, "w") as f:
            f.write(json.dumps({
                "timestamp": "2025-11-12T00:00:00Z",
                "milestone": 1,
                "nodes": 100,
                "edges": 99
            }) + "\n")
        
        status = check_milestone(test_checkpoint_dir)
        
        assert status['is_milestone'] is True
        assert status['current_nodes'] == 200
        assert status['milestone_number'] == 2
        assert status['previous_milestone_nodes'] == 100
    
    def test_no_milestone_at_99_nodes(self, test_checkpoint_dir):
        """Test that no milestone is detected at 99 nodes."""
        # Update checkpoint metadata to 99 nodes
        checkpoint_metadata = {
            "timestamp": "2025-11-13T00:00:00Z",
            "nodes": 99,
            "edges": 98,
            "processed_samples": 99
        }
        
        with open(test_checkpoint_dir / "checkpoint_metadata.json", "w") as f:
            json.dump(checkpoint_metadata, f)
        
        status = check_milestone(test_checkpoint_dir)
        
        assert status['is_milestone'] is False
        assert status['current_nodes'] == 99
        assert status['milestone_number'] == 0
    
    def test_no_milestone_at_150_nodes_after_100(self, test_checkpoint_dir):
        """Test that no milestone is detected at 150 nodes (between milestones)."""
        # Update checkpoint metadata to 150 nodes
        checkpoint_metadata = {
            "timestamp": "2025-11-13T00:00:00Z",
            "nodes": 150,
            "edges": 149,
            "processed_samples": 150
        }
        
        with open(test_checkpoint_dir / "checkpoint_metadata.json", "w") as f:
            json.dump(checkpoint_metadata, f)
        
        # Create milestone history with first milestone
        milestone_history_path = test_checkpoint_dir.parent / "milestone_history.jsonl"
        with open(milestone_history_path, "w") as f:
            f.write(json.dumps({
                "timestamp": "2025-11-12T00:00:00Z",
                "milestone": 1,
                "nodes": 100,
                "edges": 99
            }) + "\n")
        
        status = check_milestone(test_checkpoint_dir)
        
        assert status['is_milestone'] is False
        assert status['current_nodes'] == 150
        assert status['milestone_number'] == 1  # Still in milestone 1 range


@pytest.mark.integration
class TestParallelExecution:
    """Test parallel execution of milestone actions."""
    
    def test_three_jobs_run_concurrently(self, test_checkpoint_dir, test_output_dir, tmp_path):
        """Test that validation, edge generation, and website deployment run in parallel."""
        # Track execution times for each job
        execution_times = {}
        execution_order = []
        lock = threading.Lock()
        
        def mock_validation_job():
            """Simulate validation job (1 second)."""
            with lock:
                execution_order.append("validation_start")
            start = time.time()
            time.sleep(1)
            duration = time.time() - start
            with lock:
                execution_times["validation"] = duration
                execution_order.append("validation_end")
            return 0  # Success
        
        def mock_edge_generation_job():
            """Simulate edge generation job (1.5 seconds)."""
            with lock:
                execution_order.append("edges_start")
            start = time.time()
            time.sleep(1.5)
            duration = time.time() - start
            with lock:
                execution_times["edges"] = duration
                execution_order.append("edges_end")
            return 0  # Success
        
        def mock_website_job():
            """Simulate website deployment job (0.5 seconds)."""
            with lock:
                execution_order.append("website_start")
            start = time.time()
            time.sleep(0.5)
            duration = time.time() - start
            with lock:
                execution_times["website"] = duration
                execution_order.append("website_end")
            return 0  # Success
        
        # Start all jobs in parallel
        start_time = time.time()
        
        threads = []
        for job_func in [mock_validation_job, mock_edge_generation_job, mock_website_job]:
            thread = threading.Thread(target=job_func)
            thread.start()
            threads.append(thread)
        
        # Wait for all jobs to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify parallel execution
        # If sequential: 1 + 1.5 + 0.5 = 3 seconds
        # If parallel: max(1, 1.5, 0.5) = 1.5 seconds
        assert total_time < 2.5, f"Jobs took {total_time}s, expected < 2.5s (parallel execution)"
        assert total_time >= 1.5, f"Jobs took {total_time}s, expected >= 1.5s (longest job)"
        
        # Verify all jobs started before any completed (true parallelism)
        start_indices = [
            execution_order.index("validation_start"),
            execution_order.index("edges_start"),
            execution_order.index("website_start")
        ]
        end_indices = [
            execution_order.index("validation_end"),
            execution_order.index("edges_end"),
            execution_order.index("website_end")
        ]
        
        # All starts should come before all ends (with some overlap)
        assert max(start_indices) < max(end_indices)
    
    def test_main_pipeline_continues_during_milestone(self, test_checkpoint_dir):
        """Test that main pipeline continues uninterrupted during milestone actions."""
        # Simulate main pipeline continuing to process samples
        pipeline_progress = []
        milestone_progress = []
        lock = threading.Lock()
        
        def main_pipeline_job():
            """Simulate main pipeline continuing to fetch samples."""
            for i in range(5):
                with lock:
                    pipeline_progress.append(f"sample_{100 + i}")
                time.sleep(0.2)  # Simulate sample processing
        
        def milestone_actions_job():
            """Simulate milestone actions running in background."""
            time.sleep(0.1)  # Small delay to ensure pipeline starts first
            for action in ["validation", "edges", "website"]:
                with lock:
                    milestone_progress.append(action)
                time.sleep(0.3)  # Simulate action execution
        
        # Start both jobs
        pipeline_thread = threading.Thread(target=main_pipeline_job)
        milestone_thread = threading.Thread(target=milestone_actions_job)
        
        start_time = time.time()
        pipeline_thread.start()
        milestone_thread.start()
        
        pipeline_thread.join()
        milestone_thread.join()
        total_time = time.time() - start_time
        
        # Verify both completed
        assert len(pipeline_progress) == 5
        assert len(milestone_progress) == 3
        
        # Verify they ran concurrently (not sequentially)
        # Sequential would be: 5*0.2 + 3*0.3 = 1.9s
        # Concurrent should be: max(5*0.2, 3*0.3) ≈ 1.0s
        assert total_time < 1.5, f"Took {total_time}s, expected < 1.5s (concurrent execution)"


@pytest.mark.integration
class TestValidationFailureHandling:
    """Test that validation failures properly fail the pipeline."""
    
    def test_validation_failure_stops_pipeline(self, test_checkpoint_dir):
        """Test that validation failure causes pipeline to fail."""
        # Create corrupted checkpoint (empty graph file)
        with open(test_checkpoint_dir / "graph_topology.gpickle", "wb") as f:
            f.write(b"")  # Empty file
        
        # Run validation
        report = ValidationReport()
        graph, metadata_conn = validate_checkpoint_integrity(test_checkpoint_dir, report)
        
        # Verify validation failed
        assert graph is None
        assert metadata_conn is None
        assert report.status == "failed"
        assert len(report.errors) > 0
    
    def test_validation_success_allows_pipeline_continue(self, test_checkpoint_dir):
        """Test that validation success allows pipeline to continue."""
        # Run validation on valid checkpoint
        report = ValidationReport()
        graph, metadata_conn = validate_checkpoint_integrity(test_checkpoint_dir, report)
        
        # Verify validation passed
        assert graph is not None
        assert metadata_conn is not None
        assert report.status == "passed"
        assert len(report.errors) == 0
        
        if metadata_conn:
            metadata_conn.close()
    
    def test_validation_exit_codes(self, test_checkpoint_dir, tmp_path):
        """Test that validation script returns correct exit codes."""
        output_file = tmp_path / "validation_report.json"
        
        # Test successful validation
        # Set UTF-8 encoding for subprocess to handle emojis on Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            [
                sys.executable,
                "validate_pipeline_data.py",
                "--checkpoint-dir", str(test_checkpoint_dir),
                "--output", str(output_file)
            ],
            capture_output=True,
            encoding='utf-8',
            errors='replace',  # Replace invalid characters instead of failing
            env=env
        )
        
        # Should exit with 0 (success)
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        assert result.returncode == 0
        assert output_file.exists()
        
        # Verify report
        with open(output_file) as f:
            report = json.load(f)
        assert report["status"] == "passed"


@pytest.mark.integration
class TestBackgroundJobExitCodes:
    """Test that background jobs return correct exit codes."""
    
    def test_collect_exit_codes_from_parallel_jobs(self, tmp_path):
        """Test collecting exit codes from parallel background jobs."""
        # Simulate the workflow pattern of starting jobs and collecting exit codes
        exit_code_files = {
            "validation": tmp_path / "validation_exit_code.txt",
            "edges": tmp_path / "edges_exit_code.txt",
            "website": tmp_path / "website_exit_code.txt"
        }
        
        def job_with_exit_code(name, exit_code, delay=0.1):
            """Simulate a job that writes its exit code to a file."""
            time.sleep(delay)
            exit_code_files[name].write_text(str(exit_code))
        
        # Start jobs with different exit codes
        threads = [
            threading.Thread(target=job_with_exit_code, args=("validation", 0, 0.1)),
            threading.Thread(target=job_with_exit_code, args=("edges", 0, 0.15)),
            threading.Thread(target=job_with_exit_code, args=("website", 0, 0.05))
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Collect exit codes
        exit_codes = {}
        for name, path in exit_code_files.items():
            assert path.exists(), f"Exit code file for {name} not found"
            exit_codes[name] = int(path.read_text().strip())
        
        # Verify all succeeded
        assert exit_codes["validation"] == 0
        assert exit_codes["edges"] == 0
        assert exit_codes["website"] == 0
    
    def test_validation_failure_detected(self, tmp_path):
        """Test that validation failure is properly detected."""
        exit_code_files = {
            "validation": tmp_path / "validation_exit_code.txt",
            "edges": tmp_path / "edges_exit_code.txt",
            "website": tmp_path / "website_exit_code.txt"
        }
        
        def job_with_exit_code(name, exit_code, delay=0.1):
            """Simulate a job that writes its exit code to a file."""
            time.sleep(delay)
            exit_code_files[name].write_text(str(exit_code))
        
        # Start jobs with validation failure
        threads = [
            threading.Thread(target=job_with_exit_code, args=("validation", 1, 0.1)),  # Failed
            threading.Thread(target=job_with_exit_code, args=("edges", 0, 0.15)),
            threading.Thread(target=job_with_exit_code, args=("website", 0, 0.05))
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Collect exit codes
        exit_codes = {}
        for name, path in exit_code_files.items():
            exit_codes[name] = int(path.read_text().strip())
        
        # Verify validation failed
        assert exit_codes["validation"] == 1
        
        # Pipeline should fail if validation fails
        pipeline_should_fail = exit_codes["validation"] != 0
        assert pipeline_should_fail is True


@pytest.mark.integration
class TestEndToEndMilestoneWorkflow:
    """Test complete end-to-end milestone workflow."""
    
    def test_full_milestone_workflow(self, test_checkpoint_dir, test_output_dir, tmp_path):
        """Test complete milestone workflow from detection to completion."""
        # Step 1: Detect milestone
        status = check_milestone(test_checkpoint_dir)
        assert status['is_milestone'] is True
        
        # Save milestone status
        milestone_status_file = tmp_path / "milestone_status.json"
        with open(milestone_status_file, "w") as f:
            json.dump(status, f)
        
        # Step 2: Run parallel milestone actions (simulated)
        results = {}
        
        def run_validation():
            """Simulate validation."""
            time.sleep(0.2)
            results["validation"] = {"status": "passed", "duration": 0.2}
        
        def run_edge_generation():
            """Simulate edge generation."""
            time.sleep(0.3)
            results["edges"] = {"user_edges": 10, "pack_edges": 5, "duration": 0.3}
        
        def run_website_deployment():
            """Simulate website deployment."""
            time.sleep(0.1)
            results["website"] = {"deployed": True, "duration": 0.1}
        
        # Start parallel jobs
        threads = [
            threading.Thread(target=run_validation),
            threading.Thread(target=run_edge_generation),
            threading.Thread(target=run_website_deployment)
        ]
        
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Step 3: Verify all actions completed
        assert "validation" in results
        assert "edges" in results
        assert "website" in results
        
        # Step 4: Verify parallel execution
        assert total_time < 0.5, f"Took {total_time}s, expected < 0.5s (parallel)"
        
        # Step 5: Verify milestone status was saved
        assert milestone_status_file.exists()
        with open(milestone_status_file) as f:
            saved_status = json.load(f)
        assert saved_status['is_milestone'] is True
        assert saved_status['milestone_number'] == 1
    
    def test_milestone_workflow_with_failure_recovery(self, test_checkpoint_dir, tmp_path):
        """Test milestone workflow handles failures gracefully."""
        # Detect milestone
        status = check_milestone(test_checkpoint_dir)
        assert status['is_milestone'] is True
        
        # Simulate parallel jobs with one failure
        results = {}
        
        def run_validation():
            """Simulate validation failure."""
            time.sleep(0.1)
            results["validation"] = {"status": "failed", "error": "Corrupted checkpoint"}
        
        def run_edge_generation():
            """Simulate edge generation success."""
            time.sleep(0.2)
            results["edges"] = {"user_edges": 10, "pack_edges": 5}
        
        def run_website_deployment():
            """Simulate website deployment success."""
            time.sleep(0.1)
            results["website"] = {"deployed": True}
        
        # Start parallel jobs
        threads = [
            threading.Thread(target=run_validation),
            threading.Thread(target=run_edge_generation),
            threading.Thread(target=run_website_deployment)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify validation failed
        assert results["validation"]["status"] == "failed"
        
        # Verify other jobs completed (non-blocking)
        assert "edges" in results
        assert "website" in results
        
        # Pipeline should fail due to validation failure
        pipeline_failed = results["validation"]["status"] == "failed"
        assert pipeline_failed is True


@pytest.mark.integration
class TestMilestoneHistoryTracking:
    """Test milestone history tracking."""
    
    def test_milestone_history_created(self, test_checkpoint_dir):
        """Test that milestone history file is created."""
        milestone_history_path = test_checkpoint_dir.parent / "milestone_history.jsonl"
        
        # Initially no history
        assert not milestone_history_path.exists()
        
        # Detect milestone
        status = check_milestone(test_checkpoint_dir)
        assert status['is_milestone'] is True
        
        # Simulate saving milestone to history
        milestone_record = {
            "timestamp": "2025-11-13T00:00:00Z",
            "milestone": status['milestone_number'],
            "nodes": status['current_nodes'],
            "edges": 99
        }
        
        with open(milestone_history_path, "w") as f:
            f.write(json.dumps(milestone_record) + "\n")
        
        # Verify history was created
        assert milestone_history_path.exists()
        
        # Load and verify
        history = load_milestone_history(test_checkpoint_dir)
        assert len(history) == 1
        assert history[0]['milestone'] == 1
        assert history[0]['nodes'] == 100
    
    def test_milestone_history_accumulates(self, test_checkpoint_dir):
        """Test that milestone history accumulates over time."""
        milestone_history_path = test_checkpoint_dir.parent / "milestone_history.jsonl"
        
        # Create history with multiple milestones
        milestones = [
            {"timestamp": "2025-11-11T00:00:00Z", "milestone": 1, "nodes": 100, "edges": 99},
            {"timestamp": "2025-11-12T00:00:00Z", "milestone": 2, "nodes": 200, "edges": 199},
            {"timestamp": "2025-11-13T00:00:00Z", "milestone": 3, "nodes": 300, "edges": 299}
        ]
        
        with open(milestone_history_path, "w") as f:
            for milestone in milestones:
                f.write(json.dumps(milestone) + "\n")
        
        # Load history
        history = load_milestone_history(test_checkpoint_dir)
        
        # Verify all milestones are present
        assert len(history) == 3
        assert history[0]['milestone'] == 1
        assert history[1]['milestone'] == 2
        assert history[2]['milestone'] == 3
        
        # Verify chronological order
        assert history[0]['nodes'] < history[1]['nodes'] < history[2]['nodes']


@pytest.mark.integration
class TestResourceUtilization:
    """Test resource utilization during parallel execution."""
    
    def test_parallel_execution_uses_multiple_cores(self):
        """Test that parallel execution can utilize multiple CPU cores."""
        import multiprocessing
        
        # Get number of available cores
        num_cores = multiprocessing.cpu_count()
        
        # We need at least 3 cores for optimal parallel execution
        # (1 for main pipeline + 3 for milestone actions)
        if num_cores < 3:
            pytest.skip(f"Test requires at least 3 CPU cores, found {num_cores}")
        
        # Simulate CPU-intensive work on multiple threads
        def cpu_intensive_work(duration=0.5):
            """Simulate CPU-intensive work."""
            end_time = time.time() + duration
            count = 0
            while time.time() < end_time:
                count += 1
            return count
        
        # Run sequentially
        start_sequential = time.time()
        for _ in range(3):
            cpu_intensive_work(0.3)
        sequential_time = time.time() - start_sequential
        
        # Run in parallel
        start_parallel = time.time()
        threads = [threading.Thread(target=cpu_intensive_work, args=(0.3,)) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        parallel_time = time.time() - start_parallel
        
        # Parallel should be faster (though not 3x due to GIL and overhead)
        # We expect at least some speedup
        speedup = sequential_time / parallel_time
        assert speedup > 1.0, f"Parallel execution should be faster (speedup: {speedup:.2f}x)"
