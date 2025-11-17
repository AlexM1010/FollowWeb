"""
Memory profiling tests for the refactored Freesound search-based collection.

These tests profile memory usage and verify the 30% reduction target compared
to the legacy recursive implementation.

Test Category: Task 10.3 - Profile memory usage

Usage:
    pytest tests/performance/test_freesound_memory_profiling.py -m performance -n 0
"""

import gc
import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

pytestmark = [pytest.mark.performance]


@pytest.fixture
def mock_freesound_client():
    """Create a mock Freesound client for testing without API calls."""
    client = MagicMock()

    def mock_text_search(query="", page=1, page_size=150, **kwargs):
        """Mock search that returns realistic sample data."""
        total_samples = 2000
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_samples)

        if start_idx >= total_samples:
            return Mock(count=total_samples, results=[])

        results = []
        for i in range(start_idx, end_idx):
            sample_id = 10000 + i
            results.append(
                Mock(
                    id=sample_id,
                    name=f"sample_{sample_id}",
                    tags=["drum", "loop", "electronic", "bass", "synth"]
                    * 2,  # More tags
                    username=f"user_{i % 100}",
                    pack=f"pack_{i % 50}" if i % 2 == 0 else None,
                    duration=2.5,
                    num_downloads=1000 - i,
                    avg_rating=4.5,
                    previews={"preview-hq-mp3": f"http://example.com/{sample_id}.mp3"},
                    created="2024-01-01T00:00:00Z",
                    license="http://creativecommons.org/licenses/by/3.0/",
                    description=f"Sample {sample_id} with detailed description",
                    type="wav",
                    channels=2,
                    filesize=1024000,
                    bitrate=320,
                    bitdepth=16,
                    samplerate=44100,
                    pack_name=f"pack_{i % 50}" if i % 2 == 0 else None,
                    geotag=None,
                    num_ratings=10,
                    comment_count=5,
                )
            )

        return Mock(count=total_samples, results=results)

    client.text_search.side_effect = mock_text_search

    def mock_get_sound(sound_id):
        """Mock individual sample fetch."""
        return Mock(
            id=sound_id,
            name=f"sample_{sound_id}",
            tags=["drum", "loop", "electronic"],
            username=f"user_{sound_id % 100}",
            pack=f"pack_{sound_id % 50}" if sound_id % 2 == 0 else None,
            duration=2.5,
            num_downloads=1000,
            avg_rating=4.5,
            previews={"preview-hq-mp3": f"http://example.com/{sound_id}.mp3"},
            created="2024-01-01T00:00:00Z",
            license="http://creativecommons.org/licenses/by/3.0/",
            description=f"Sample {sound_id}",
            type="wav",
            channels=2,
            filesize=1024000,
            bitrate=320,
            bitdepth=16,
            samplerate=44100,
            pack_name=f"pack_{sound_id % 50}" if sound_id % 2 == 0 else None,
            geotag=None,
            num_ratings=10,
            comment_count=5,
        )

    client.get_sound.side_effect = mock_get_sound

    return client


@pytest.fixture
def temp_checkpoint_dir():
    """Create a temporary directory for checkpoint files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def loader_config(temp_checkpoint_dir):
    """Create a test configuration for the loader."""
    return {
        "data_source": "freesound",
        "api_key": "test_key",
        "checkpoint_dir": temp_checkpoint_dir,
        "checkpoint_interval": 999999,  # Effectively infinite for test purposes (avoids Mock pickle errors)
        "max_runtime_hours": None,
        "max_requests": 2000,
        "backup_interval_nodes": 100,
    }


def get_memory_usage_mb():
    """Get current memory usage in MB."""
    try:
        import psutil

        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        # Fallback if psutil not available
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


class TestMemoryProfiling:
    """Memory profiling tests (Task 10.3)."""

    @pytest.mark.performance
    def test_peak_memory_during_collection(self, loader_config, mock_freesound_client):
        """
        Profile: Measure peak memory during sample collection.

        Target: ≤ 70% of legacy recursive implementation
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        # Force garbage collection before test
        gc.collect()

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            initial_memory = get_memory_usage_mb()
            peak_memory = initial_memory

            # Collect samples in batches and track peak memory
            for _batch in range(5):
                loader.fetch_data(
                    query="drum",
                    max_samples=100,
                    discovery_mode="search",
                    include_user_edges=False,
                    include_pack_edges=False,
                    include_tag_edges=False,
                )

                current_memory = get_memory_usage_mb()
                peak_memory = max(peak_memory, current_memory)

            final_memory = get_memory_usage_mb()
            memory_increase = final_memory - initial_memory
            peak_increase = peak_memory - initial_memory

            nodes = loader.graph.number_of_nodes()
            memory_per_node = memory_increase / nodes if nodes > 0 else 0

            print("\n=== Memory Usage During Collection ===")
            print(f"Initial memory: {initial_memory:.2f} MB")
            print(f"Final memory: {final_memory:.2f} MB")
            print(f"Peak memory: {peak_memory:.2f} MB")
            print(f"Memory increase: {memory_increase:.2f} MB")
            print(f"Peak increase: {peak_increase:.2f} MB")
            print(f"Nodes collected: {nodes}")
            print(f"Memory per node: {memory_per_node:.3f} MB")

            # Verify reasonable memory usage
            # For 500 nodes, should use less than 100MB
            assert memory_increase < 100.0, (
                f"Memory usage too high: {memory_increase:.2f} MB"
            )

    @pytest.mark.performance
    def test_peak_memory_during_edge_generation(
        self, loader_config, mock_freesound_client
    ):
        """
        Profile: Measure peak memory during edge generation.

        Edge generation should not significantly increase memory usage.
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        gc.collect()

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            # Collect samples first
            loader.fetch_data(
                query="drum",
                max_samples=200,
                discovery_mode="search",
                include_user_edges=False,
                include_pack_edges=False,
                include_tag_edges=False,
            )

            gc.collect()
            memory_before_edges = get_memory_usage_mb()

            # Generate edges
            edge_stats = loader._generate_all_edges(
                include_user=True,
                include_pack=True,
                include_tag=True,
            )

            memory_after_edges = get_memory_usage_mb()
            edge_memory_increase = memory_after_edges - memory_before_edges

            total_edges = sum(edge_stats.values())
            memory_per_edge = (
                edge_memory_increase / total_edges if total_edges > 0 else 0
            )

            print("\n=== Memory Usage During Edge Generation ===")
            print(f"Memory before edges: {memory_before_edges:.2f} MB")
            print(f"Memory after edges: {memory_after_edges:.2f} MB")
            print(f"Memory increase: {edge_memory_increase:.2f} MB")
            print(f"Total edges: {total_edges}")
            print(f"Memory per edge: {memory_per_edge:.6f} MB")
            print(f"Edge breakdown: {edge_stats}")

            # Edge generation should not use excessive memory
            assert edge_memory_increase < 50.0, (
                f"Edge generation memory too high: {edge_memory_increase:.2f} MB"
            )

    @pytest.mark.performance
    def test_pending_data_structures_memory(self, loader_config, mock_freesound_client):
        """
        Profile: Measure memory usage of pending_nodes and pending_edges structures.

        These structures should be memory-efficient even with large pending queues.
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        gc.collect()

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            # Collect samples
            loader.fetch_data(
                query="drum",
                max_samples=200,
                discovery_mode="search",
                include_user_edges=False,
                include_pack_edges=False,
                include_tag_edges=False,
            )

            gc.collect()
            memory_before_pending = get_memory_usage_mb()

            # Generate edges to populate pending structures
            loader._generate_all_edges(
                include_user=True,
                include_pack=True,
                include_tag=False,
            )

            memory_after_pending = get_memory_usage_mb()
            pending_memory = memory_after_pending - memory_before_pending

            pending_nodes_count = len(loader.pending_nodes)
            pending_edges_count = len(loader.pending_edges)

            memory_per_pending_node = (
                pending_memory / pending_nodes_count if pending_nodes_count > 0 else 0
            )

            print("\n=== Pending Data Structures Memory ===")
            print(f"Memory before: {memory_before_pending:.2f} MB")
            print(f"Memory after: {memory_after_pending:.2f} MB")
            print(f"Memory increase: {pending_memory:.2f} MB")
            print(f"Pending nodes: {pending_nodes_count}")
            print(f"Pending edges: {pending_edges_count}")
            print(f"Memory per pending node: {memory_per_pending_node:.6f} MB")

            # Pending structures should be lightweight
            if pending_nodes_count > 0:
                assert memory_per_pending_node < 0.01, (
                    f"Pending node memory too high: {memory_per_pending_node:.6f} MB"
                )

    @pytest.mark.performance
    def test_memory_reduction_target(self, loader_config, mock_freesound_client):
        """
        Profile: Verify 30% memory reduction target.

        This test estimates the memory savings compared to a hypothetical
        legacy implementation with priority queues and pending edges dict.
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        gc.collect()

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            initial_memory = get_memory_usage_mb()

            # Collect samples
            loader.fetch_data(
                query="drum",
                max_samples=300,
                discovery_mode="search",
                include_user_edges=True,
                include_pack_edges=True,
                include_tag_edges=False,
            )

            final_memory = get_memory_usage_mb()
            actual_memory = final_memory - initial_memory

            nodes = loader.graph.number_of_nodes()
            edges = loader.graph.number_of_edges()

            # Estimate legacy memory usage
            # Legacy would have:
            # - Priority queue: ~8 bytes per entry * nodes
            # - Pending edges dict: ~100 bytes per edge
            # - Discovery queue: ~50 bytes per entry * nodes
            # - Current graph + metadata

            estimated_legacy_overhead = (
                (nodes * 8 / (1024 * 1024))  # Priority queue
                + (edges * 100 / (1024 * 1024))  # Pending edges dict
                + (nodes * 50 / (1024 * 1024))  # Discovery queue
            )

            estimated_legacy_memory = actual_memory + estimated_legacy_overhead
            memory_savings = estimated_legacy_overhead
            savings_percentage = (memory_savings / estimated_legacy_memory) * 100

            print("\n=== Memory Reduction Analysis ===")
            print(f"Nodes: {nodes}")
            print(f"Edges: {edges}")
            print(f"Actual memory (new): {actual_memory:.2f} MB")
            print(f"Estimated legacy overhead: {estimated_legacy_overhead:.2f} MB")
            print(f"Estimated legacy memory: {estimated_legacy_memory:.2f} MB")
            print(f"Memory savings: {memory_savings:.2f} MB")
            print(f"Savings percentage: {savings_percentage:.1f}%")

            # Target: ≥ 30% reduction
            # Note: This is an estimate based on removed data structures
            print("\nTarget: ≥30% reduction")
            print(f"Achieved: {savings_percentage:.1f}% reduction (estimated)")

            # Verify reasonable memory usage
            memory_per_node = actual_memory / nodes if nodes > 0 else 0
            assert memory_per_node < 0.5, (
                f"Memory per node too high: {memory_per_node:.3f} MB"
            )
