"""
Discovery mode comparison benchmarks for the refactored Freesound collection.

These tests compare the performance characteristics of different discovery modes:
- search: Pure search-based collection
- relationships: Relationship-based discovery (user/pack)
- mixed: Combination of search and relationships

Test Category: Task 10.5 - Benchmark discovery modes

Usage:
    pytest tests/performance/test_freesound_discovery_modes.py -m performance -n 0 -v
"""

import tempfile
import time
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

pytestmark = [pytest.mark.performance]


@pytest.fixture
def mock_freesound_client():
    """Create a mock Freesound client for testing without API calls."""
    client = MagicMock()

    def mock_text_search(query="", page=1, page_size=150, **kwargs):
        """Mock search that returns realistic sample data."""
        total_samples = 5000
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_samples)

        if start_idx >= total_samples:
            return Mock(count=total_samples, results=[])

        results = []
        for i in range(start_idx, end_idx):
            sample_id = 30000 + i
            # Create clusters of related samples
            cluster_id = i // 20  # Groups of 20 samples
            results.append(
                Mock(
                    id=sample_id,
                    name=f"sample_{sample_id}",
                    tags=[f"tag_{cluster_id}", f"tag_{cluster_id % 10}", "common"],
                    username=f"user_{cluster_id % 50}",  # Clustered by user
                    pack=f"pack_{cluster_id % 30}"
                    if i % 2 == 0
                    else None,  # Clustered by pack
                    duration=2.5,
                    num_downloads=5000 - i,
                    avg_rating=4.0,
                    previews={"preview-hq-mp3": f"http://example.com/{sample_id}.mp3"},
                    created="2024-01-01T00:00:00Z",
                    license="http://creativecommons.org/licenses/by/3.0/",
                    description=f"Sample {sample_id}",
                    type="wav",
                    channels=2,
                    filesize=1024000,
                    bitrate=320,
                    bitdepth=16,
                    samplerate=44100,
                    pack_name=f"pack_{cluster_id % 30}" if i % 2 == 0 else None,
                    geotag=None,
                    num_ratings=10,
                    comment_count=5,
                )
            )

        return Mock(count=total_samples, results=results)

    client.text_search.side_effect = mock_text_search

    def mock_get_sound(sound_id):
        """Mock individual sample fetch."""
        cluster_id = (sound_id - 30000) // 20
        return Mock(
            id=sound_id,
            name=f"sample_{sound_id}",
            tags=[f"tag_{cluster_id}", f"tag_{cluster_id % 10}", "common"],
            username=f"user_{cluster_id % 50}",
            pack=f"pack_{cluster_id % 30}" if sound_id % 2 == 0 else None,
            duration=2.5,
            num_downloads=5000,
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
            pack_name=f"pack_{cluster_id % 30}" if sound_id % 2 == 0 else None,
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
        "max_requests": 5000,
        "backup_interval_nodes": 200,
    }


def collect_metrics(loader, elapsed_time: float, api_client) -> dict[str, Any]:
    """Collect comprehensive metrics from a loader run."""
    nodes = loader.graph.number_of_nodes()
    edges = loader.graph.number_of_edges()

    # Calculate graph density
    max_edges = nodes * (nodes - 1)  # Directed graph
    density = edges / max_edges if max_edges > 0 else 0

    # API efficiency
    search_calls = api_client.text_search.call_count
    get_calls = api_client.get_sound.call_count
    total_calls = search_calls + get_calls
    calls_per_sample = total_calls / nodes if nodes > 0 else 0

    # Performance
    samples_per_second = nodes / elapsed_time if elapsed_time > 0 else 0

    # Pending nodes
    pending_count = len(loader.pending_nodes)
    discovery_rate = pending_count / nodes if nodes > 0 else 0

    return {
        "nodes": nodes,
        "edges": edges,
        "density": density,
        "elapsed_time": elapsed_time,
        "samples_per_second": samples_per_second,
        "search_calls": search_calls,
        "get_calls": get_calls,
        "total_calls": total_calls,
        "calls_per_sample": calls_per_sample,
        "pending_nodes": pending_count,
        "discovery_rate": discovery_rate,
    }


class TestDiscoveryModeComparisons:
    """Discovery mode comparison tests (Task 10.5)."""

    @pytest.mark.performance
    def test_search_mode_performance(self, loader_config, mock_freesound_client):
        """
        Benchmark: Pure search-based collection performance.

        Characteristics:
        - Lowest API calls per sample
        - Predictable performance
        - May miss related samples
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            mock_freesound_client.text_search.reset_mock()
            mock_freesound_client.get_sound.reset_mock()

            start_time = time.time()

            loader.fetch_data(
                query="drum",
                max_samples=300,
                discovery_mode="search",
                include_user_edges=True,
                include_pack_edges=True,
                include_tag_edges=False,
            )

            elapsed = time.time() - start_time
            metrics = collect_metrics(loader, elapsed, mock_freesound_client)

            print("\n=== Search Mode Performance ===")
            print(f"Nodes: {metrics['nodes']}")
            print(f"Edges: {metrics['edges']}")
            print(f"Graph density: {metrics['density']:.6f}")
            print(f"Time: {metrics['elapsed_time']:.2f}s")
            print(f"Samples/sec: {metrics['samples_per_second']:.2f}")
            print(
                f"API calls: {metrics['total_calls']} ({metrics['calls_per_sample']:.3f} per sample)"
            )
            print(f"  Search calls: {metrics['search_calls']}")
            print(f"  Get calls: {metrics['get_calls']}")
            print(
                f"Pending nodes: {metrics['pending_nodes']} ({metrics['discovery_rate']:.2f} per node)"
            )

            # Verify search mode characteristics
            assert metrics["samples_per_second"] >= 10.0, "Search mode should be fast"
            assert metrics["calls_per_sample"] < 0.1, (
                "Search mode should be API-efficient"
            )

            return metrics

    @pytest.mark.performance
    def test_relationships_mode_performance(self, loader_config, mock_freesound_client):
        """
        Benchmark: Relationship-based discovery performance.

        Characteristics:
        - Higher API calls (fetching discovered nodes)
        - Discovers related samples
        - Denser graph structure
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            mock_freesound_client.text_search.reset_mock()
            mock_freesound_client.get_sound.reset_mock()

            start_time = time.time()

            loader.fetch_data(
                query="drum",
                max_samples=300,
                discovery_mode="relationships",
                include_user_edges=True,
                include_pack_edges=True,
                include_tag_edges=False,
            )

            elapsed = time.time() - start_time
            metrics = collect_metrics(loader, elapsed, mock_freesound_client)

            print("\n=== Relationships Mode Performance ===")
            print(f"Nodes: {metrics['nodes']}")
            print(f"Edges: {metrics['edges']}")
            print(f"Graph density: {metrics['density']:.6f}")
            print(f"Time: {metrics['elapsed_time']:.2f}s")
            print(f"Samples/sec: {metrics['samples_per_second']:.2f}")
            print(
                f"API calls: {metrics['total_calls']} ({metrics['calls_per_sample']:.3f} per sample)"
            )
            print(f"  Search calls: {metrics['search_calls']}")
            print(f"  Get calls: {metrics['get_calls']}")
            print(
                f"Pending nodes: {metrics['pending_nodes']} ({metrics['discovery_rate']:.2f} per node)"
            )

            # Verify relationships mode characteristics
            assert metrics["nodes"] >= 300, "Should collect target samples"
            assert metrics["get_calls"] > 0, "Should fetch discovered nodes"

            return metrics

    @pytest.mark.performance
    def test_mixed_mode_performance(self, loader_config, mock_freesound_client):
        """
        Benchmark: Mixed search + relationships performance.

        Characteristics:
        - Balanced approach
        - Good graph density
        - Moderate API usage
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
            loader = IncrementalFreesoundLoader(loader_config)

            mock_freesound_client.text_search.reset_mock()
            mock_freesound_client.get_sound.reset_mock()

            start_time = time.time()

            loader.fetch_data(
                query="drum",
                max_samples=300,
                discovery_mode="mixed",
                include_user_edges=True,
                include_pack_edges=True,
                include_tag_edges=False,
            )

            elapsed = time.time() - start_time
            metrics = collect_metrics(loader, elapsed, mock_freesound_client)

            print("\n=== Mixed Mode Performance ===")
            print(f"Nodes: {metrics['nodes']}")
            print(f"Edges: {metrics['edges']}")
            print(f"Graph density: {metrics['density']:.6f}")
            print(f"Time: {metrics['elapsed_time']:.2f}s")
            print(f"Samples/sec: {metrics['samples_per_second']:.2f}")
            print(
                f"API calls: {metrics['total_calls']} ({metrics['calls_per_sample']:.3f} per sample)"
            )
            print(f"  Search calls: {metrics['search_calls']}")
            print(f"  Get calls: {metrics['get_calls']}")
            print(
                f"Pending nodes: {metrics['pending_nodes']} ({metrics['discovery_rate']:.2f} per node)"
            )

            # Verify mixed mode characteristics
            assert metrics["nodes"] >= 300, "Should collect target samples"

            return metrics

    @pytest.mark.performance
    def test_discovery_mode_comparison(self, loader_config, mock_freesound_client):
        """
        Performance test: Compare all discovery modes side-by-side.

        Documents optimal strategies for different use cases.
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        modes = ["search", "relationships", "mixed"]
        results = {}

        for mode in modes:
            with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
                loader = IncrementalFreesoundLoader(loader_config)

                mock_freesound_client.text_search.reset_mock()
                mock_freesound_client.get_sound.reset_mock()

                start_time = time.time()

                loader.fetch_data(
                    query="drum",
                    max_samples=200,
                    discovery_mode=mode,
                    include_user_edges=True,
                    include_pack_edges=True,
                    include_tag_edges=False,
                )

                elapsed = time.time() - start_time
                metrics = collect_metrics(loader, elapsed, mock_freesound_client)
                results[mode] = metrics

        # Print comparison table
        print("\n=== Discovery Mode Comparison ===")
        print(f"{'Metric':<25} {'Search':<15} {'Relationships':<15} {'Mixed':<15}")
        print("-" * 70)

        metrics_to_compare = [
            ("Nodes", "nodes", "d"),
            ("Edges", "edges", "d"),
            ("Graph Density", "density", ".6f"),
            ("Time (s)", "elapsed_time", ".2f"),
            ("Samples/sec", "samples_per_second", ".2f"),
            ("Total API Calls", "total_calls", "d"),
            ("Calls/Sample", "calls_per_sample", ".3f"),
            ("Pending Nodes", "pending_nodes", "d"),
            ("Discovery Rate", "discovery_rate", ".2f"),
        ]

        for label, key, fmt in metrics_to_compare:
            search_val = results["search"][key]
            rel_val = results["relationships"][key]
            mixed_val = results["mixed"][key]

            print(
                f"{label:<25} {search_val:<15{fmt}} {rel_val:<15{fmt}} {mixed_val:<15{fmt}}"
            )

        # Analyze and document optimal strategies
        print("\n=== Optimal Strategy Recommendations ===")

        # Best for speed
        fastest = min(results.items(), key=lambda x: x[1]["elapsed_time"])
        print(
            f"Fastest: {fastest[0]} ({fastest[1]['samples_per_second']:.2f} samples/sec)"
        )

        # Best for API efficiency
        most_efficient = min(results.items(), key=lambda x: x[1]["calls_per_sample"])
        print(
            f"Most API-efficient: {most_efficient[0]} ({most_efficient[1]['calls_per_sample']:.3f} calls/sample)"
        )

        # Best for graph density
        densest = max(results.items(), key=lambda x: x[1]["density"])
        print(f"Densest graph: {densest[0]} (density: {densest[1]['density']:.6f})")

        # Best for discovery
        best_discovery = max(results.items(), key=lambda x: x[1]["discovery_rate"])
        print(
            f"Best discovery: {best_discovery[0]} ({best_discovery[1]['discovery_rate']:.2f} pending/node)"
        )

        # Use case recommendations
        print("\n=== Use Case Recommendations ===")
        print(f"1. Quick exploration: Use '{fastest[0]}' mode")
        print(f"2. API quota limited: Use '{most_efficient[0]}' mode")
        print(f"3. Dense network analysis: Use '{densest[0]}' mode")
        print(f"4. Discovering related content: Use '{best_discovery[0]}' mode")

        # Verify all modes work
        for mode, metrics in results.items():
            assert metrics["nodes"] >= 200, f"{mode} mode should collect target samples"
            assert metrics["samples_per_second"] > 0, (
                f"{mode} mode should have positive throughput"
            )

    @pytest.mark.performance
    def test_graph_density_by_mode(self, loader_config, mock_freesound_client):
        """
        Performance test: Measure graph density achieved by each discovery mode.

        Graph density indicates how well-connected the network is.
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        modes = ["search", "relationships", "mixed"]
        density_results = {}

        for mode in modes:
            with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
                loader = IncrementalFreesoundLoader(loader_config)

                loader.fetch_data(
                    query="drum",
                    max_samples=150,
                    discovery_mode=mode,
                    include_user_edges=True,
                    include_pack_edges=True,
                    include_tag_edges=True,  # Include tag edges for density
                )

                nodes = loader.graph.number_of_nodes()
                edges = loader.graph.number_of_edges()
                max_edges = nodes * (nodes - 1)
                density = edges / max_edges if max_edges > 0 else 0
                avg_degree = (2 * edges) / nodes if nodes > 0 else 0

                density_results[mode] = {
                    "nodes": nodes,
                    "edges": edges,
                    "density": density,
                    "avg_degree": avg_degree,
                }

        print("\n=== Graph Density by Discovery Mode ===")
        for mode, results in density_results.items():
            print(f"\n{mode.upper()} Mode:")
            print(f"  Nodes: {results['nodes']}")
            print(f"  Edges: {results['edges']}")
            print(f"  Density: {results['density']:.6f}")
            print(f"  Avg Degree: {results['avg_degree']:.2f}")

        # Verify reasonable density values
        for mode, results in density_results.items():
            assert results["density"] > 0, f"{mode} mode should create some edges"
            assert results["density"] < 1.0, f"{mode} mode density should be < 1.0"

    @pytest.mark.performance
    def test_api_efficiency_by_mode(self, loader_config, mock_freesound_client):
        """
        Performance test: Measure API efficiency for each discovery mode.

        API efficiency is critical for staying within rate limits and quotas.
        """
        from FollowWeb_Visualizor.data.loaders.incremental_freesound import (
            IncrementalFreesoundLoader,
        )

        modes = ["search", "relationships", "mixed"]
        efficiency_results = {}

        for mode in modes:
            with patch("freesound.FreesoundClient", return_value=mock_freesound_client):
                loader = IncrementalFreesoundLoader(loader_config)

                mock_freesound_client.text_search.reset_mock()
                mock_freesound_client.get_sound.reset_mock()

                loader.fetch_data(
                    query="drum",
                    max_samples=200,
                    discovery_mode=mode,
                    include_user_edges=True,
                    include_pack_edges=True,
                    include_tag_edges=False,
                )

                nodes = loader.graph.number_of_nodes()
                search_calls = mock_freesound_client.text_search.call_count
                get_calls = mock_freesound_client.get_sound.call_count
                total_calls = search_calls + get_calls

                efficiency_results[mode] = {
                    "nodes": nodes,
                    "search_calls": search_calls,
                    "get_calls": get_calls,
                    "total_calls": total_calls,
                    "calls_per_sample": total_calls / nodes if nodes > 0 else 0,
                    "search_ratio": search_calls / total_calls
                    if total_calls > 0
                    else 0,
                }

        print("\n=== API Efficiency by Discovery Mode ===")
        for mode, results in efficiency_results.items():
            print(f"\n{mode.upper()} Mode:")
            print(f"  Nodes: {results['nodes']}")
            print(f"  Search calls: {results['search_calls']}")
            print(f"  Get calls: {results['get_calls']}")
            print(f"  Total calls: {results['total_calls']}")
            print(f"  Calls per sample: {results['calls_per_sample']:.3f}")
            print(f"  Search ratio: {results['search_ratio']:.2%}")

        # Find most efficient mode
        most_efficient = min(
            efficiency_results.items(), key=lambda x: x[1]["calls_per_sample"]
        )
        print(
            f"\nMost API-efficient: {most_efficient[0]} ({most_efficient[1]['calls_per_sample']:.3f} calls/sample)"
        )

        # Verify all modes are reasonably efficient
        for mode, results in efficiency_results.items():
            # Should use fewer than 1 call per sample on average
            assert results["calls_per_sample"] < 1.0, (
                f"{mode} mode should be API-efficient"
            )
