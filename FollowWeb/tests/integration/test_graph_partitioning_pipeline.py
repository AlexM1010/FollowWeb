"""
Integration tests for graph partitioning pipeline.

Tests the complete partitioning workflow from graph partitioning through
analysis to result merging for various graph sizes.
"""

import sys
import tempfile
import time
from pathlib import Path

import networkx as nx
import pytest

from FollowWeb_Visualizor.analysis.partition_merger import PartitionResultsMerger
from FollowWeb_Visualizor.analysis.partition_worker import PartitionAnalysisWorker
from FollowWeb_Visualizor.analysis.partitioning import GraphPartitioner

# Skip all tests in this module on Windows (pymetis not available)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.analysis,
    pytest.mark.skipif(
        sys.platform == "win32",
        reason="pymetis not available on Windows - graph partitioning not supported",
    ),
]
# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def graph_100k() -> nx.DiGraph:
    """Create a 100K node graph for integration testing."""
    graph = nx.DiGraph()

    # Create nodes
    nodes = [f"node_{i}" for i in range(100000)]
    graph.add_nodes_from(nodes)

    # Add edges efficiently (sparse graph)
    for i in range(0, 100000, 1000):
        # Create communities of 1000 nodes
        for j in range(i, min(i + 1000, 100000)):
            # Connect to 3 neighbors within community
            for k in range(1, 4):
                target = i + ((j - i + k) % 1000)
                if target < 100000:
                    graph.add_edge(f"node_{j}", f"node_{target}")

    return graph


@pytest.fixture
def graph_300k() -> nx.DiGraph:
    """Create a 300K node graph for integration testing."""
    graph = nx.DiGraph()

    # Create nodes
    nodes = [f"node_{i}" for i in range(300000)]
    graph.add_nodes_from(nodes)

    # Add edges efficiently (very sparse for speed)
    for i in range(0, 300000, 5000):
        # Create communities of 5000 nodes
        for j in range(i, min(i + 5000, 300000), 10):
            # Connect every 10th node to 2 neighbors
            for k in range(1, 3):
                target = i + ((j - i + k * 10) % 5000)
                if target < 300000:
                    graph.add_edge(f"node_{j}", f"node_{target}")

    return graph


@pytest.fixture
def temp_artifacts_dir():
    """Create temporary directory for partition artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ============================================================================
# Integration tests for full pipeline
# ============================================================================


class TestGraphPartitioningPipeline:
    """Test complete graph partitioning pipeline."""

    def test_100k_node_graph_2_partitions(self, graph_100k, temp_artifacts_dir):
        """Test 100K node graph with 2 partitions."""
        start_time = time.perf_counter()

        # Step 1: Partition the graph
        partitioner = GraphPartitioner()
        partitions = partitioner.partition_graph(graph_100k, num_partitions=2)

        assert len(partitions) == 2
        total_nodes = sum(p.number_of_nodes() for p in partitions)
        assert total_nodes == 100000

        # Step 2: Save partitions
        for i, partition in enumerate(partitions):
            partitioner.save_partition(partition, i, temp_artifacts_dir)

        # Step 3: Analyze each partition
        partition_results = []
        for i in range(2):
            partition = partitioner.load_partition(i, temp_artifacts_dir)
            worker = PartitionAnalysisWorker(partition_id=i)
            results = worker.analyze_partition(partition)
            partition_results.append(results)

            # Save results
            import joblib

            result_file = Path(temp_artifacts_dir) / f"partition-{i}-results.pkl"
            joblib.dump(results, result_file)

        # Step 4: Merge results
        merger = PartitionResultsMerger()
        loaded_results = merger.load_all_results(temp_artifacts_dir)
        merged_results = merger.merge_all(loaded_results, graph_100k)

        # Verify final graph correctness
        assert merged_results.total_nodes == 100000
        assert merged_results.partition_count == 2
        assert len(merged_results.global_communities) == 100000
        assert len(merged_results.global_centrality) == 100000
        assert len(merged_results.global_layout) == 100000

        # Verify graph attributes
        final_graph = merger.create_final_graph(graph_100k, merged_results)
        sample_node = list(final_graph.nodes())[0]
        assert "community" in final_graph.nodes[sample_node]
        assert "betweenness" in final_graph.nodes[sample_node]

        elapsed_time = time.perf_counter() - start_time
        print(f"\n100K nodes (2 partitions) completed in {elapsed_time:.2f}s")

    @pytest.mark.slow
    def test_300k_node_graph_6_partitions(self, graph_300k, temp_artifacts_dir):
        """Test 300K node graph with 6 partitions."""
        start_time = time.perf_counter()

        # Step 1: Partition the graph
        partitioner = GraphPartitioner()
        partitions = partitioner.partition_graph(graph_300k, num_partitions=6)

        assert len(partitions) == 6
        total_nodes = sum(p.number_of_nodes() for p in partitions)
        assert total_nodes == 300000

        # Step 2: Save partitions
        for i, partition in enumerate(partitions):
            partitioner.save_partition(partition, i, temp_artifacts_dir)

        # Step 3: Analyze each partition (simulating parallel execution)
        partition_results = []
        for i in range(6):
            partition = partitioner.load_partition(i, temp_artifacts_dir)
            worker = PartitionAnalysisWorker(partition_id=i)
            results = worker.analyze_partition(partition)
            partition_results.append(results)

            # Save results
            import joblib

            result_file = Path(temp_artifacts_dir) / f"partition-{i}-results.pkl"
            joblib.dump(results, result_file)

        # Step 4: Merge results
        merger = PartitionResultsMerger()
        loaded_results = merger.load_all_results(temp_artifacts_dir)
        merged_results = merger.merge_all(loaded_results, graph_300k)

        # Verify final graph correctness
        assert merged_results.total_nodes == 300000
        assert merged_results.partition_count == 6
        assert len(merged_results.global_communities) == 300000
        assert len(merged_results.global_centrality) == 300000
        assert len(merged_results.global_layout) == 300000

        elapsed_time = time.perf_counter() - start_time
        print(f"\n300K nodes (6 partitions) completed in {elapsed_time:.2f}s")

    @pytest.mark.slow
    def test_600k_node_graph_12_partitions(self, temp_artifacts_dir):
        """Test 600K node graph with 12 partitions."""
        # Create a very sparse 600K node graph for testing
        graph = nx.DiGraph()
        nodes = [f"node_{i}" for i in range(600000)]
        graph.add_nodes_from(nodes)

        # Add minimal edges for speed (very sparse)
        for i in range(0, 600000, 10000):
            for j in range(i, min(i + 10000, 600000), 100):
                target = i + ((j - i + 100) % 10000)
                if target < 600000:
                    graph.add_edge(f"node_{j}", f"node_{target}")

        start_time = time.perf_counter()

        # Step 1: Partition the graph
        partitioner = GraphPartitioner()
        partitions = partitioner.partition_graph(graph, num_partitions=12)

        assert len(partitions) == 12
        total_nodes = sum(p.number_of_nodes() for p in partitions)
        assert total_nodes == 600000

        # Step 2: Save partitions
        for i, partition in enumerate(partitions):
            partitioner.save_partition(partition, i, temp_artifacts_dir)

        # Step 3: Analyze partitions (sample only first 3 for speed)
        partition_results = []
        for i in range(3):  # Only analyze first 3 partitions for test speed
            partition = partitioner.load_partition(i, temp_artifacts_dir)
            worker = PartitionAnalysisWorker(partition_id=i)
            results = worker.analyze_partition(partition)
            partition_results.append(results)

            # Save results
            import joblib

            result_file = Path(temp_artifacts_dir) / f"partition-{i}-results.pkl"
            joblib.dump(results, result_file)

        # Verify partition analysis worked
        assert len(partition_results) == 3
        for results in partition_results:
            assert len(results.communities) > 0
            assert len(results.centrality) > 0
            assert len(results.layout) > 0

        elapsed_time = time.perf_counter() - start_time
        print(
            f"\n600K nodes (12 partitions, 3 analyzed) completed in {elapsed_time:.2f}s"
        )

    @pytest.mark.slow
    def test_1m_node_graph_20_partitions(self, temp_artifacts_dir):
        """Test 1M node graph with 20 partitions."""
        # Create a very sparse 1M node graph for testing
        graph = nx.DiGraph()
        nodes = [f"node_{i}" for i in range(1000000)]
        graph.add_nodes_from(nodes)

        # Add minimal edges for speed (extremely sparse)
        for i in range(0, 1000000, 20000):
            for j in range(i, min(i + 20000, 1000000), 200):
                target = i + ((j - i + 200) % 20000)
                if target < 1000000:
                    graph.add_edge(f"node_{j}", f"node_{target}")

        start_time = time.perf_counter()

        # Step 1: Partition the graph
        partitioner = GraphPartitioner()
        partitions = partitioner.partition_graph(graph, num_partitions=20)

        assert len(partitions) == 20
        total_nodes = sum(p.number_of_nodes() for p in partitions)
        assert total_nodes == 1000000

        # Step 2: Save partitions (sample only first 5 for speed)
        for i in range(5):
            partitioner.save_partition(partitions[i], i, temp_artifacts_dir)

        # Step 3: Analyze partitions (sample only first 2 for speed)
        partition_results = []
        for i in range(2):
            partition = partitioner.load_partition(i, temp_artifacts_dir)
            worker = PartitionAnalysisWorker(partition_id=i)
            results = worker.analyze_partition(partition)
            partition_results.append(results)

        # Verify partition analysis worked
        assert len(partition_results) == 2
        for results in partition_results:
            assert len(results.communities) > 0
            assert len(results.centrality) > 0
            assert len(results.layout) > 0

        elapsed_time = time.perf_counter() - start_time
        print(
            f"\n1M nodes (20 partitions, 2 analyzed) completed in {elapsed_time:.2f}s"
        )

    def test_partition_correctness_verification(self, graph_100k, temp_artifacts_dir):
        """Verify final graph correctness after partitioning."""
        # Partition and analyze
        partitioner = GraphPartitioner()
        partitions = partitioner.partition_graph(graph_100k, num_partitions=2)

        partition_results = []
        for i, partition in enumerate(partitions):
            worker = PartitionAnalysisWorker(partition_id=i)
            results = worker.analyze_partition(partition)
            partition_results.append(results)

        # Merge results
        merger = PartitionResultsMerger()
        merged_results = merger.merge_all(partition_results, graph_100k)
        final_graph = merger.create_final_graph(graph_100k, merged_results)

        # Verify graph structure is preserved
        assert final_graph.number_of_nodes() == graph_100k.number_of_nodes()
        assert final_graph.number_of_edges() == graph_100k.number_of_edges()

        # Verify all nodes have attributes
        for node in final_graph.nodes():
            assert "community" in final_graph.nodes[node]
            assert "betweenness" in final_graph.nodes[node]

        # Verify community assignments are valid
        communities = {
            final_graph.nodes[node]["community"] for node in final_graph.nodes()
        }
        assert len(communities) > 0  # Should have at least one community

        # Verify centrality scores are normalized
        centralities = [
            final_graph.nodes[node]["betweenness"] for node in final_graph.nodes()
        ]
        assert all(0 <= c <= 1 for c in centralities)

    @pytest.mark.slow
    def test_performance_metrics_collection(self, graph_100k, temp_artifacts_dir):
        """Test collection of performance metrics during pipeline execution."""
        start_time = time.perf_counter()

        # Partition
        partition_start = time.perf_counter()
        partitioner = GraphPartitioner()
        partitions = partitioner.partition_graph(graph_100k, num_partitions=2)
        partition_time = time.perf_counter() - partition_start

        # Analyze
        analysis_start = time.perf_counter()
        partition_results = []
        for i, partition in enumerate(partitions):
            worker = PartitionAnalysisWorker(partition_id=i)
            results = worker.analyze_partition(partition)
            partition_results.append(results)
        analysis_time = time.perf_counter() - analysis_start

        # Merge
        merge_start = time.perf_counter()
        merger = PartitionResultsMerger()
        merged_results = merger.merge_all(partition_results, graph_100k)
        merge_time = time.perf_counter() - merge_start

        total_time = time.perf_counter() - start_time

        # Verify metrics
        assert partition_time > 0
        assert analysis_time > 0
        assert merge_time > 0
        assert merged_results.merge_time > 0

        # Print performance breakdown
        print("\nPerformance metrics for 100K nodes:")
        print(f"  Partition time: {partition_time:.2f}s")
        print(f"  Analysis time: {analysis_time:.2f}s")
        print(f"  Merge time: {merge_time:.2f}s")
        print(f"  Total time: {total_time:.2f}s")
