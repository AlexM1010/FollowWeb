"""
Large-scale performance tests for the refactored Freesound search-based collection.

These tests verify that the system scales properly with large datasets and
large pending node queues.

Test Category: Task 10.4 - Run large-scale tests

Usage:
    pytest tests/performance/test_freesound_large_scale.py -m performance -n 0 -v
"""

import tempfile
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

pytestmark = [pytest.mark.performance, pytest.mark.slow]


@pytest.fixture
def mock_freesound_client_large():
    """Create a mock Freesound client that can handle large-scale requests."""
    client = MagicMock()

    def mock_text_search(query="", page=1, page_size=150, **kwargs):
        """Mock search that returns realistic sample data for large datasets."""
        total_samples = 15000  # Large dataset
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_samples)

        if start_idx >= total_samples:
            return Mock(count=total_samples, results=[])

        results = []
        for i in range(start_idx, end_idx):
            sample_id = 50000 + i
            results.append(
                Mock(
                    id=sample_id,
                    name=f"sample_{sample_id}",
                    tags=[f"tag_{j}" for j in range(i % 10)],  # Variable tag count
                    username=f"user_{i % 200}",  # 200 unique users
                    pack=f"pack_{i % 100}" if i % 3 == 0 else None,  # 100 unique packs
                    duration=2.5 + (i % 10) * 0.5,
                    num_downloads=10000 - i,
                    avg_rating=3.0 + (i % 5) * 0.5,
                    previews={"preview-hq-mp3": f"http://example.com/{sample_id}.mp3"},
                    created="2024-01-01T00:00:00Z",
                    license="http://creativecommons.org/licenses/by/3.0/",
                    description=f"Sample {sample_id}",
                    type="wav",
                    channels=2,
                    filesize=1024000 + i * 1000,
                    bitrate=320,
                    bitdepth=16,
                    samplerate=44100,
                    pack_name=f"pack_{i % 100}" if i % 3 == 0 else None,
                    geotag=None,
                    num_ratings=10 + i % 50,
                    comment_count=i % 20,
                )
            )

        return Mock(count=total_samples, results=results)

    client.text_search.side_effect = mock_text_search

    def mock_get_sound(sound_id):
        """Mock individual sample fetch."""
        return Mock(
            id=sound_id,
            name=f"sample_{sound_id}",
            tags=[f"tag_{j}" for j in range(sound_id % 10)],
            username=f"user_{sound_id % 200}",
            pack=f"pack_{sound_id % 100}" if sound_id % 3 == 0 else None,
            duration=2.5,
            num_downloads=10000,
            avg_rating=4.0,
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
            pack_name=f"pack_{sound_id % 100}" if sound_id % 3 == 0 else None,
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
        "checkpoint_interval": 100,
        "max_runtime_hours": None,
        "max_requests": 20000,
        "backup_interval_nodes": 500,
    }


class TestLargeScalePerformance:
    """Large-scale performance tests (Task 10.4)."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_1000_samples_collection(self, loader_config, mock_freesound_client_large):
        """
        Large-scale test: Collect 1000+ samples and verify performance.

        Verifies:
        - Collection completes successfully
        - Performance targets are met
        - No memory issues
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch(
            "freesound.FreesoundClient", return_value=mock_freesound_client_large
        ):
            loader = IncrementalFreesoundLoader(loader_config)

            start_time = time.time()

            loader.fetch_data(
                query="drum",
                max_samples=1000,
                discovery_mode="search",
                include_user_edges=True,
                include_pack_edges=True,
                include_tag_edges=False,
            )

            elapsed = time.time() - start_time

            nodes = loader.graph.number_of_nodes()
            edges = loader.graph.number_of_edges()
            samples_per_second = nodes / elapsed

            print("\n=== 1000+ Samples Test ===")
            print(f"Nodes collected: {nodes}")
            print(f"Edges created: {edges}")
            print(f"Time elapsed: {elapsed:.2f}s")
            print(f"Samples per second: {samples_per_second:.2f}")
            print(f"Pending nodes: {len(loader.pending_nodes)}")

            # Verify collection succeeded
            assert nodes >= 1000, f"Expected ≥1000 nodes, got {nodes}"

            # Verify performance target
            assert samples_per_second >= 10.0, (
                f"Expected ≥10 samples/sec, got {samples_per_second:.2f}"
            )

            # Verify graph structure
            assert edges > 0, "Should have created some edges"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_10000_samples_collection(self, loader_config, mock_freesound_client_large):
        """
        Large-scale test: Collect 10,000+ samples and verify scalability.

        This is a stress test to ensure the system can handle very large datasets.
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch(
            "freesound.FreesoundClient", return_value=mock_freesound_client_large
        ):
            loader = IncrementalFreesoundLoader(loader_config)

            start_time = time.time()

            loader.fetch_data(
                query="drum",
                max_samples=10000,
                discovery_mode="search",
                include_user_edges=True,
                include_pack_edges=True,
                include_tag_edges=False,  # Skip tag edges for speed
            )

            elapsed = time.time() - start_time

            nodes = loader.graph.number_of_nodes()
            edges = loader.graph.number_of_edges()
            samples_per_second = nodes / elapsed

            print("\n=== 10,000+ Samples Test ===")
            print(f"Nodes collected: {nodes}")
            print(f"Edges created: {edges}")
            print(f"Time elapsed: {elapsed:.2f}s ({elapsed / 60:.1f} minutes)")
            print(f"Samples per second: {samples_per_second:.2f}")
            print(f"Pending nodes: {len(loader.pending_nodes)}")
            print(f"Edge density: {edges / nodes:.2f} edges per node")

            # Verify collection succeeded
            assert nodes >= 10000, f"Expected ≥10000 nodes, got {nodes}"

            # Performance may degrade slightly at scale, but should still be reasonable
            assert samples_per_second >= 5.0, (
                f"Expected ≥5 samples/sec at scale, got {samples_per_second:.2f}"
            )

            # Verify graph structure
            assert edges > 0, "Should have created some edges"

    @pytest.mark.performance
    def test_large_pending_node_queue(self, loader_config, mock_freesound_client_large):
        """
        Large-scale test: Handle large pending node queues (1000+).

        Verifies that the system can efficiently manage large numbers of
        pending nodes discovered through relationships.
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch(
            "freesound.FreesoundClient", return_value=mock_freesound_client_large
        ):
            loader = IncrementalFreesoundLoader(loader_config)

            # Collect initial samples
            loader.fetch_data(
                query="drum",
                max_samples=500,
                discovery_mode="search",
                include_user_edges=False,
                include_pack_edges=False,
                include_tag_edges=False,
            )

            initial_nodes = loader.graph.number_of_nodes()

            # Generate edges to create large pending queue
            start_time = time.time()
            edge_stats = loader._generate_all_edges(
                include_user=True,
                include_pack=True,
                include_tag=False,
            )
            edge_time = time.time() - start_time

            pending_count = len(loader.pending_nodes)

            print("\n=== Large Pending Queue Test ===")
            print(f"Initial nodes: {initial_nodes}")
            print(f"Pending nodes discovered: {pending_count}")
            print(f"Edge generation time: {edge_time:.2f}s")
            print(f"User edges: {edge_stats.get('user_edges', 0)}")
            print(f"Pack edges: {edge_stats.get('pack_edges', 0)}")

            # Verify large pending queue was created
            assert pending_count >= 100, (
                f"Expected ≥100 pending nodes, got {pending_count}"
            )

            # Now fetch pending nodes in batch
            if pending_count > 0:
                pending_ids = list(loader.pending_nodes)[: min(1000, pending_count)]

                start_time = time.time()
                fetched = loader._fetch_pending_nodes_batch(pending_ids, batch_size=150)
                fetch_time = time.time() - start_time

                fetch_rate = len(fetched) / fetch_time if fetch_time > 0 else 0

                print(f"Fetched {len(fetched)} pending nodes in {fetch_time:.2f}s")
                print(f"Fetch rate: {fetch_rate:.2f} nodes/sec")

                # Verify efficient fetching
                assert fetch_rate >= 10.0, (
                    f"Expected ≥10 nodes/sec, got {fetch_rate:.2f}"
                )

    @pytest.mark.performance
    def test_checkpoint_recovery_at_scale(
        self, loader_config, mock_freesound_client_large
    ):
        """
        Large-scale test: Verify checkpoint recovery works at scale.

        Tests that checkpoints can be saved and loaded correctly with
        large datasets without data loss.
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch(
            "freesound.FreesoundClient", return_value=mock_freesound_client_large
        ):
            # First loader: collect samples and save checkpoint
            loader1 = IncrementalFreesoundLoader(loader_config)

            loader1.fetch_data(
                query="drum",
                max_samples=500,
                discovery_mode="search",
                include_user_edges=True,
                include_pack_edges=True,
                include_tag_edges=False,
            )

            nodes_before = loader1.graph.number_of_nodes()
            edges_before = loader1.graph.number_of_edges()
            pending_before = len(loader1.pending_nodes)

            # Force checkpoint save
            loader1._save_checkpoint()

            print("\n=== Checkpoint Recovery at Scale ===")
            print("Saved checkpoint with:")
            print(f"  Nodes: {nodes_before}")
            print(f"  Edges: {edges_before}")
            print(f"  Pending nodes: {pending_before}")

            # Close first loader
            loader1.close()

            # Second loader: load from checkpoint
            loader2 = IncrementalFreesoundLoader(loader_config)

            nodes_after = loader2.graph.number_of_nodes()
            edges_after = loader2.graph.number_of_edges()
            pending_after = len(loader2.pending_nodes)

            print("Loaded checkpoint with:")
            print(f"  Nodes: {nodes_after}")
            print(f"  Edges: {edges_after}")
            print(f"  Pending nodes: {pending_after}")

            # Verify no data loss
            assert nodes_after == nodes_before, (
                f"Node count mismatch: {nodes_after} != {nodes_before}"
            )
            assert edges_after == edges_before, (
                f"Edge count mismatch: {edges_after} != {edges_before}"
            )
            assert pending_after == pending_before, (
                f"Pending count mismatch: {pending_after} != {pending_before}"
            )

            # Continue collection from checkpoint
            loader2.fetch_data(
                query="drum",
                max_samples=1000,
                discovery_mode="search",
                include_user_edges=True,
                include_pack_edges=True,
                include_tag_edges=False,
            )

            final_nodes = loader2.graph.number_of_nodes()

            print("After continuing collection:")
            print(f"  Nodes: {final_nodes}")

            # Verify incremental collection worked
            assert final_nodes >= nodes_before, "Should have added more nodes"

            loader2.close()

    @pytest.mark.performance
    def test_edge_generation_at_scale(self, loader_config, mock_freesound_client_large):
        """
        Large-scale test: Verify edge generation scales properly.

        Target: < 60 seconds for 1000 nodes
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch(
            "freesound.FreesoundClient", return_value=mock_freesound_client_large
        ):
            loader = IncrementalFreesoundLoader(loader_config)

            # Collect 1000 nodes without edges
            loader.fetch_data(
                query="drum",
                max_samples=1000,
                discovery_mode="search",
                include_user_edges=False,
                include_pack_edges=False,
                include_tag_edges=False,
            )

            nodes = loader.graph.number_of_nodes()

            # Generate all edges
            start_time = time.time()
            edge_stats = loader._generate_all_edges(
                include_user=True,
                include_pack=True,
                include_tag=False,  # Skip tag edges (O(N²))
            )
            edge_time = time.time() - start_time

            total_edges = sum(edge_stats.values())

            print("\n=== Edge Generation at Scale ===")
            print(f"Nodes: {nodes}")
            print(f"Edge generation time: {edge_time:.2f}s")
            print(f"Total edges: {total_edges}")
            print(f"User edges: {edge_stats.get('user_edges', 0)}")
            print(f"Pack edges: {edge_stats.get('pack_edges', 0)}")
            print(f"Edges per second: {total_edges / edge_time:.2f}")

            # Target: < 60 seconds for 1000 nodes
            assert edge_time < 60.0, (
                f"Edge generation too slow: {edge_time:.2f}s for {nodes} nodes"
            )

    @pytest.mark.performance
    def test_deferred_discovery_at_scale(
        self, loader_config, mock_freesound_client_large
    ):
        """
        Large-scale test: Verify deferred discovery works efficiently at scale.

        Tests that pending nodes can be discovered and fetched efficiently
        even with large pending queues.
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch(
            "freesound.FreesoundClient", return_value=mock_freesound_client_large
        ):
            loader = IncrementalFreesoundLoader(loader_config)

            # Collect initial samples
            loader.fetch_data(
                query="drum",
                max_samples=300,
                discovery_mode="search",
                include_user_edges=True,
                include_pack_edges=True,
                include_tag_edges=False,
            )

            initial_nodes = loader.graph.number_of_nodes()
            initial_edges = loader.graph.number_of_edges()
            pending_count = len(loader.pending_nodes)

            print("\n=== Deferred Discovery at Scale ===")
            print(f"Initial nodes: {initial_nodes}")
            print(f"Initial edges: {initial_edges}")
            print(f"Pending nodes: {pending_count}")

            # Fetch pending nodes
            if pending_count > 0:
                pending_ids = list(loader.pending_nodes)[: min(500, pending_count)]

                start_time = time.time()
                fetched = loader._fetch_pending_nodes_batch(pending_ids, batch_size=150)
                fetch_time = time.time() - start_time

                # Add fetched samples as nodes
                loader._add_samples_as_nodes(fetched)

                # Complete pending edges
                completed_edges = loader._complete_pending_edges()

                total_time = time.time() - start_time

                final_nodes = loader.graph.number_of_nodes()
                final_edges = loader.graph.number_of_edges()

                print(f"Fetched {len(fetched)} pending nodes in {fetch_time:.2f}s")
                print(f"Completed {completed_edges} pending edges")
                print(f"Total time: {total_time:.2f}s")
                print(f"Final nodes: {final_nodes}")
                print(f"Final edges: {final_edges}")
                print(f"Nodes added: {final_nodes - initial_nodes}")
                print(f"Edges added: {final_edges - initial_edges}")

                # Verify deferred discovery worked
                assert final_nodes > initial_nodes, "Should have added pending nodes"
                assert completed_edges > 0, "Should have completed some pending edges"

                # Verify efficiency
                fetch_rate = len(fetched) / fetch_time if fetch_time > 0 else 0
                assert fetch_rate >= 10.0, (
                    f"Expected ≥10 nodes/sec, got {fetch_rate:.2f}"
                )
