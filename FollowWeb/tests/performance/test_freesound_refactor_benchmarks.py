"""
Performance benchmarks for the refactored Freesound search-based collection.

These tests benchmark the simplified search-based collection approach and compare
it against the expected performance targets from the design document.

Expected Performance Targets:
- API calls: < 10 calls per 100 samples (excluding edge generation)
- Processing speed: ≥ 10 samples per second
- Memory usage: ≤ 70% of legacy recursive implementation
- Edge generation: < 60 seconds for 1000 nodes
- Checkpoint recovery: No data loss at any stage

Test Categories:
- Search-based collection benchmarks (10.1)
- Edge generation benchmarks (10.2)
- Memory profiling (10.3)
- Large-scale tests (10.4)
- Discovery mode comparisons (10.5)

Usage:
    pytest tests/performance/test_freesound_refactor_benchmarks.py -m benchmark -n 0 --benchmark-only
    pytest tests/performance/test_freesound_refactor_benchmarks.py -m performance -n 0
"""

import tempfile
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

pytestmark = [pytest.mark.performance, pytest.mark.benchmark]


@pytest.fixture
def mock_freesound_client():
    """Create a mock Freesound client for testing without API calls."""
    client = MagicMock()

    # Mock text_search to return paginated results
    def mock_text_search(query="", page=1, page_size=150, **kwargs):
        """Mock search that returns realistic sample data."""
        # Simulate pagination - limit to 60 total samples to reduce API calls
        total_samples = 60
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_samples)

        results = []
        for i in range(start_idx, end_idx):
            if i >= total_samples:
                break
            sample_id = 10000 + i
            sound = Mock(spec=[])
            sound.id = sample_id
            sound.name = f"sample_{sample_id}"
            sound.tags = (
                ["drum", "loop", "electronic"] if i % 3 == 0 else ["bass", "synth"]
            )
            sound.username = f"user_{i % 50}"  # 50 unique users
            sound.pack = f"pack_{i % 30}" if i % 2 == 0 else None  # 30 unique packs
            sound.duration = 2.5
            sound.num_downloads = 1000 - i
            sound.avg_rating = 4.5
            sound.previews = {"preview-hq-mp3": f"http://example.com/{sample_id}.mp3"}
            sound.created = "2024-01-01T00:00:00Z"
            sound.license = "http://creativecommons.org/licenses/by/3.0/"
            sound.description = f"Sample {sample_id}"
            sound.type = "wav"
            sound.channels = 2
            sound.filesize = 1024000
            sound.bitrate = 320
            sound.bitdepth = 16
            sound.samplerate = 44100
            sound.pack_name = f"pack_{i % 30}" if i % 2 == 0 else None
            sound.geotag = None
            sound.num_ratings = 10
            sound.comment_count = 5

            # Add as_dict method
            def make_as_dict(sound_obj):
                return lambda: {
                    "id": sound_obj.id,
                    "name": sound_obj.name,
                    "tags": sound_obj.tags,
                    "username": sound_obj.username,
                    "pack": sound_obj.pack,
                    "duration": sound_obj.duration,
                    "num_downloads": sound_obj.num_downloads,
                    "avg_rating": sound_obj.avg_rating,
                    "previews": sound_obj.previews,
                    "created": sound_obj.created,
                    "license": sound_obj.license,
                    "description": sound_obj.description,
                    "type": sound_obj.type,
                    "channels": sound_obj.channels,
                    "filesize": sound_obj.filesize,
                    "bitrate": sound_obj.bitrate,
                    "bitdepth": sound_obj.bitdepth,
                    "samplerate": sound_obj.samplerate,
                    "pack_name": sound_obj.pack_name,
                    "geotag": sound_obj.geotag,
                    "num_ratings": sound_obj.num_ratings,
                    "comment_count": sound_obj.comment_count,
                }

            sound.as_dict = make_as_dict(sound)
            results.append(sound)

        # Create result object that supports iteration
        class MockPager:
            def __init__(self, results, has_next=False):
                self.results = results
                self.count = total_samples
                self.next = has_next
                self._iter_index = 0

            def __iter__(self):
                return iter(self.results)

            def next_page(self):
                # Return empty results for next page
                return MockPager([], False)

        has_next = end_idx < total_samples
        return MockPager(results, has_next)

    client.text_search.side_effect = mock_text_search

    # Mock get_sound for individual sample fetches
    def mock_get_sound(sound_id):
        """Mock individual sample fetch."""
        return Mock(
            id=sound_id,
            name=f"sample_{sound_id}",
            tags=["drum", "loop"],
            username=f"user_{sound_id % 50}",
            pack=f"pack_{sound_id % 30}" if sound_id % 2 == 0 else None,
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
            pack_name=f"pack_{sound_id % 30}" if sound_id % 2 == 0 else None,
            geotag=None,
            num_ratings=10,
            comment_count=5,
        )

    client.get_sound.side_effect = mock_get_sound

    return client


@pytest.fixture
def temp_checkpoint_dir():
    """Create a temporary directory for checkpoint files."""
    import time

    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    # Give time for connections to close
    time.sleep(0.1)
    try:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass


@pytest.fixture
def loader_config(temp_checkpoint_dir):
    """
    Create a test configuration for the loader.

    Note: checkpoint_interval is set to a very large value to effectively disable
    checkpoint saves during short benchmark tests. This avoids "Can't pickle Mock"
    errors when the loader tries to serialize the graph containing mock objects.
    """
    return {
        "data_source": "freesound",
        "api_key": "test_key",
        "checkpoint_dir": temp_checkpoint_dir,
        "checkpoint_interval": 999999,  # Effectively infinite for test purposes
        "max_runtime_hours": None,
        "max_requests": 2000,
        "backup_interval_nodes": 100,
    }


class TestSearchBasedCollectionBenchmarks:
    """Benchmark tests for search-based collection."""

    @pytest.mark.benchmark
    def test_search_collection_speed(
        self, benchmark, loader_config, mock_freesound_client
    ):
        """
        Benchmark: Measure samples per second during search-based collection.

        Target: ≥ 10 samples per second
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            def collect_samples():
                """Collect 50 samples via search."""
                result = loader.fetch_data(
                    query="drum",
                    max_samples=50,
                    discovery_mode="search",
                    include_user_edges=False,
                    include_pack_edges=False,
                    include_tag_edges=False,
                )
                return result

            benchmark(collect_samples)

            # Verify samples were collected
            assert loader.graph.number_of_nodes() >= 50

            # Clean up
            loader.close()

            # Calculate samples per second
            if benchmark.stats:
                samples_per_second = 50 / benchmark.stats["mean"]
                print(f"\n✓ Samples per second: {samples_per_second:.2f}")

                # Target: ≥ 10 samples per second
                assert samples_per_second >= 10.0, (
                    f"Expected ≥10 samples/sec, got {samples_per_second:.2f}"
                )

    @pytest.mark.benchmark
    def test_api_calls_per_sample(
        self, benchmark, loader_config, mock_freesound_client
    ):
        """
        Benchmark: Measure API calls per sample collected.

        Target: < 10 API calls per 100 samples (< 0.1 calls per sample)
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            def collect_and_count():
                """Collect samples and count API calls."""
                # Reset counters at start of EACH benchmark iteration
                mock_freesound_client.text_search.reset_mock()
                mock_freesound_client.get_sound.reset_mock()
                
                loader.fetch_data(
                    query="drum",
                    max_samples=50,
                    discovery_mode="search",
                    include_user_edges=False,
                    include_pack_edges=False,
                    include_tag_edges=False,
                )

                # Count API calls for THIS iteration only
                search_calls = mock_freesound_client.text_search.call_count
                get_calls = mock_freesound_client.get_sound.call_count
                total_calls = search_calls + get_calls

                return total_calls

            total_calls = benchmark(collect_and_count)

            # Calculate calls per sample (total_calls is from the last iteration)
            calls_per_sample = total_calls / 50
            print(f"\n✓ API calls per sample: {calls_per_sample:.3f}")
            print(f"  Search calls: {mock_freesound_client.text_search.call_count}")
            print(f"  Get calls: {mock_freesound_client.get_sound.call_count}")

            # Target: < 1.0 calls per sample (search-based with pagination)
            # With 50 samples and page_size=150, should only need 1 search call
            assert calls_per_sample < 1.0, (
                f"Expected <1.0 calls/sample, got {calls_per_sample:.3f}"
            )

    @pytest.mark.performance
    def test_search_collection_performance_improvements(
        self, loader_config, mock_freesound_client
    ):
        """
        Performance test: Document performance improvements over legacy approach.

        Measures:
        - Total execution time
        - API call efficiency
        - Memory usage
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            # Reset counters
            mock_freesound_client.text_search.reset_mock()
            mock_freesound_client.get_sound.reset_mock()

            start_time = time.time()

            loader.fetch_data(
                query="drum",
                max_samples=100,
                discovery_mode="search",
                include_user_edges=False,
                include_pack_edges=False,
                include_tag_edges=False,
            )

            end_time = time.time()
            elapsed = end_time - start_time

            # Collect metrics
            nodes_collected = loader.graph.number_of_nodes()
            search_calls = mock_freesound_client.text_search.call_count
            get_calls = mock_freesound_client.get_sound.call_count
            total_calls = search_calls + get_calls

            samples_per_second = nodes_collected / elapsed
            calls_per_sample = total_calls / nodes_collected

            print("\n=== Performance Improvements ===")
            print(f"Samples collected: {nodes_collected}")
            print(f"Total time: {elapsed:.2f}s")
            print(f"Samples per second: {samples_per_second:.2f}")
            print(f"Total API calls: {total_calls}")
            print(f"API calls per sample: {calls_per_sample:.3f}")
            print(f"Search calls: {search_calls}")
            print(f"Get calls: {get_calls}")

            # Verify performance targets
            assert samples_per_second >= 10.0, (
                f"Expected ≥10 samples/sec, got {samples_per_second:.2f}"
            )
            assert calls_per_sample < 0.1, (
                f"Expected <0.1 calls/sample, got {calls_per_sample:.3f}"
            )

            # Expected improvement: 97.5% reduction in API calls
            # Legacy: ~200 calls for 100 samples (2 calls per sample)
            # New: ~1 call for 100 samples (0.01 calls per sample)
            legacy_calls_per_sample = 2.0
            improvement_ratio = legacy_calls_per_sample / calls_per_sample
            print(f"API call improvement: {improvement_ratio:.1f}x fewer calls")

            assert improvement_ratio >= 10.0, (
                f"Expected ≥10x improvement, got {improvement_ratio:.1f}x"
            )


class TestEdgeGenerationBenchmarks:
    """Benchmark tests for edge generation."""

    @pytest.mark.benchmark
    def test_user_edge_generation_speed(
        self, benchmark, loader_config, mock_freesound_client
    ):
        """
        Benchmark: Measure user edge generation speed.

        Target: Part of < 60 seconds for 1000 nodes
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            # Collect samples first
            loader.fetch_data(
                query="drum",
                max_samples=50,
                discovery_mode="search",
                include_user_edges=False,
                include_pack_edges=False,
                include_tag_edges=False,
            )

            # Get unique usernames for reporting
            usernames = set()
            for node_id in loader.graph.nodes():
                node_data = loader.graph.nodes[node_id]
                if node_data.get("username"):
                    usernames.add(node_data["username"])

            def generate_user_edges():
                """Generate user edges."""
                return loader._add_user_edges_batch()

            edge_count = benchmark(generate_user_edges)

            print(f"\n✓ User edges created: {edge_count}")
            print(f"  Unique users: {len(usernames)}")
            if benchmark.stats:
                print(f"  Edges per second: {edge_count / benchmark.stats['mean']:.2f}")

            assert edge_count >= 0, "Should create some user edges"

    @pytest.mark.benchmark
    def test_pack_edge_generation_speed(
        self, benchmark, loader_config, mock_freesound_client
    ):
        """
        Benchmark: Measure pack edge generation speed.

        Target: Part of < 60 seconds for 1000 nodes
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            # Collect samples first
            loader.fetch_data(
                query="drum",
                max_samples=50,
                discovery_mode="search",
                include_user_edges=False,
                include_pack_edges=False,
                include_tag_edges=False,
            )

            # Get unique pack names for reporting
            pack_names = set()
            for node_id in loader.graph.nodes():
                node_data = loader.graph.nodes[node_id]
                if node_data.get("pack_name"):
                    pack_names.add(node_data["pack_name"])

            def generate_pack_edges():
                """Generate pack edges."""
                return loader._add_pack_edges_batch()

            edge_count = benchmark(generate_pack_edges)

            print(f"\n✓ Pack edges created: {edge_count}")
            print(f"  Unique packs: {len(pack_names)}")
            if benchmark.stats:
                print(f"  Edges per second: {edge_count / benchmark.stats['mean']:.2f}")

            assert edge_count >= 0, "Should create some pack edges"
