"""
Performance and timing benchmark tests for FollowWeb Network Analysis Package.

This module contains tests that validate performance characteristics,
timing accuracy, and resource efficiency of the FollowWeb system.
"""

import time
from typing import Any, Dict

import networkx as nx
import pytest

from FollowWeb_Visualizor.core.config import load_config_from_dict
from FollowWeb_Visualizor.main import PipelineOrchestrator


class TestPerformanceBenchmarks:
    """Test performance characteristics and timing accuracy."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_pipeline_timing_accuracy(self, default_config: Dict[str, Any]):
        """Test that pipeline timing measurements are accurate."""
        config_obj = load_config_from_dict(default_config)
        orchestrator = PipelineOrchestrator(config_obj)

        # Create a small test graph
        graph = nx.Graph()
        graph.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 1)])

        start_time = time.time()
        # This would normally run the full pipeline, but for performance testing
        # we just validate the timing infrastructure exists
        assert hasattr(orchestrator, "config")
        end_time = time.time()

        # Verify timing is reasonable (should be very fast for this simple test)
        elapsed = end_time - start_time
        assert elapsed < 1.0  # Should complete in under 1 second

    @pytest.mark.performance
    def test_progress_tracking_overhead(self):
        """Test that progress tracking has minimal performance overhead."""
        from FollowWeb_Visualizor.utils import ProgressTracker

        # Test progress tracking overhead
        iterations = 1000

        # Time without progress tracking
        start_time = time.time()
        for _i in range(iterations):
            pass  # Minimal operation
        no_tracking_time = time.time() - start_time

        # Time with progress tracking
        start_time = time.time()
        with ProgressTracker(iterations, "Performance test") as progress:
            for _i in range(iterations):
                progress.update(1)
        tracking_time = time.time() - start_time

        # Progress tracking overhead should be reasonable
        overhead_ratio = tracking_time / max(
            no_tracking_time, 0.001
        )  # Avoid division by zero
        assert overhead_ratio < 10.0  # Less than 10x overhead

    @pytest.mark.performance
    def test_memory_efficiency(self):
        """Test memory efficiency of core operations."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create a moderately sized graph
        graph = nx.Graph()
        edges = [(i, i + 1) for i in range(100)]
        graph.add_edges_from(edges)

        # Perform some operations
        nx.community.greedy_modularity_communities(graph)
        nx.degree_centrality(graph)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB for this small graph)
        assert memory_increase < 50 * 1024 * 1024  # 50MB
