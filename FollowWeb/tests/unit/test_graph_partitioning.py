"""
Unit tests for graph partitioning system.

Tests GraphPartitioner, PartitionAnalysisWorker, and PartitionResultsMerger
for large-scale graph analysis with distributed processing.
"""

import sys
import tempfile
from pathlib import Path

import networkx as nx
import pytest

from FollowWeb_Visualizor.analysis.partition_merger import (
    MergedResults,
    PartitionResultsMerger,
)
from FollowWeb_Visualizor.analysis.partition_worker import (
    PartitionAnalysisWorker,
    PartitionResults,
)
from FollowWeb_Visualizor.analysis.partitioning import GraphPartitioner, PartitionInfo

# Skip all tests in this module on Windows (pymetis not available)
pytestmark = [
    pytest.mark.unit,
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
def small_graph() -> nx.DiGraph:
    """Create a small directed graph for testing (100 nodes)."""
    graph = nx.DiGraph()
    # Create a graph with 100 nodes and community structure
    for i in range(100):
        graph.add_node(f"node_{i}")

    # Add edges to create communities
    for i in range(0, 50):
        for j in range(i + 1, min(i + 5, 50)):
            graph.add_edge(f"node_{i}", f"node_{j}")
            graph.add_edge(f"node_{j}", f"node_{i}")

    for i in range(50, 100):
        for j in range(i + 1, min(i + 5, 100)):
            graph.add_edge(f"node_{i}", f"node_{j}")
            graph.add_edge(f"node_{j}", f"node_{i}")

    # Add some cross-community edges
    for i in range(0, 50, 10):
        graph.add_edge(f"node_{i}", f"node_{i + 50}")
        graph.add_edge(f"node_{i + 50}", f"node_{i}")

    return graph


@pytest.fixture
def medium_graph() -> nx.DiGraph:
    """Create a medium directed graph for testing (1000 nodes)."""
    graph = nx.DiGraph()
    # Create a graph with 1000 nodes
    for i in range(1000):
        graph.add_node(f"node_{i}")

    # Add edges with community structure
    for i in range(1000):
        # Connect to next 3 nodes (circular)
        for j in range(1, 4):
            target = (i + j) % 1000
            graph.add_edge(f"node_{i}", f"node_{target}")

    return graph


@pytest.fixture
def large_synthetic_graph() -> nx.DiGraph:
    """Create a large synthetic graph for testing (50K nodes)."""
    # Use a more efficient graph generation method
    graph = nx.DiGraph()

    # Create 50K nodes
    nodes = [f"node_{i}" for i in range(50000)]
    graph.add_nodes_from(nodes)

    # Add edges efficiently (sparse graph for speed)
    for i in range(0, 50000, 100):
        # Create small communities
        for j in range(i, min(i + 100, 50000)):
            # Connect to 2 neighbors within community
            if j + 1 < min(i + 100, 50000):
                graph.add_edge(f"node_{j}", f"node_{j + 1}")
            if j + 2 < min(i + 100, 50000):
                graph.add_edge(f"node_{j}", f"node_{j + 2}")

    return graph


@pytest.fixture
def temp_partition_dir():
    """Create a temporary directory for partition storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ============================================================================
# Unit tests for GraphPartitioner
# ============================================================================


class TestGraphPartitioner:
    """Test GraphPartitioner functionality."""

    def test_initialization(self):
        """Test GraphPartitioner initialization."""
        partitioner = GraphPartitioner()

        assert partitioner is not None
        assert partitioner.detected_cores > 0
        assert partitioner.detected_ram > 0

    def test_calculate_optimal_partitions_7gb_ram(self):
        """Test partition calculation with 7 GB RAM."""
        partitioner = GraphPartitioner()
        partitioner.detected_ram = 7

        # Test various node counts
        assert (
            partitioner.calculate_optimal_partitions(25000) == 1
        )  # 25K nodes = 1 partition
        assert (
            partitioner.calculate_optimal_partitions(50000) == 1
        )  # 50K nodes = 1 partition
        assert (
            partitioner.calculate_optimal_partitions(100000) == 2
        )  # 100K nodes = 2 partitions
        assert (
            partitioner.calculate_optimal_partitions(600000) == 12
        )  # 600K nodes = 12 partitions

    def test_calculate_optimal_partitions_4gb_ram(self):
        """Test partition calculation with 4 GB RAM."""
        partitioner = GraphPartitioner()
        partitioner.detected_ram = 4

        # Test various node counts
        assert (
            partitioner.calculate_optimal_partitions(15000) == 1
        )  # 15K nodes = 1 partition
        assert (
            partitioner.calculate_optimal_partitions(30000) == 1
        )  # 30K nodes = 1 partition
        assert (
            partitioner.calculate_optimal_partitions(60000) == 2
        )  # 60K nodes = 2 partitions
        assert (
            partitioner.calculate_optimal_partitions(300000) == 10
        )  # 300K nodes = 10 partitions

    def test_calculate_optimal_partitions_2gb_ram(self):
        """Test partition calculation with 2 GB RAM."""
        partitioner = GraphPartitioner()
        partitioner.detected_ram = 2

        # Test various node counts
        assert (
            partitioner.calculate_optimal_partitions(5000) == 1
        )  # 5K nodes = 1 partition
        assert (
            partitioner.calculate_optimal_partitions(10000) == 1
        )  # 10K nodes = 1 partition
        assert (
            partitioner.calculate_optimal_partitions(20000) == 2
        )  # 20K nodes = 2 partitions
        assert (
            partitioner.calculate_optimal_partitions(100000) == 10
        )  # 100K nodes = 10 partitions

    def test_partition_graph_single_partition(self, small_graph):
        """Test partitioning with single partition requested."""
        partitioner = GraphPartitioner()

        partitions = partitioner.partition_graph(small_graph, num_partitions=1)

        assert len(partitions) == 1
        assert partitions[0].number_of_nodes() == small_graph.number_of_nodes()
        assert partitions[0].number_of_edges() == small_graph.number_of_edges()

    def test_partition_graph_multiple_partitions(self, small_graph):
        """Test partitioning with multiple partitions."""
        partitioner = GraphPartitioner()

        partitions = partitioner.partition_graph(small_graph, num_partitions=2)

        assert len(partitions) == 2
        # Verify all nodes are distributed
        total_nodes = sum(p.number_of_nodes() for p in partitions)
        # METIS preserves all nodes
        assert total_nodes == small_graph.number_of_nodes()

        # Verify partitions are non-empty
        for partition in partitions:
            assert partition.number_of_nodes() > 0

    def test_partition_balance(self, medium_graph):
        """Test partition balance and edge cut minimization."""
        partitioner = GraphPartitioner()

        partitions = partitioner.partition_graph(medium_graph, num_partitions=4)

        assert len(partitions) == 4

        # Check partition balance (should be roughly equal)
        node_counts = [p.number_of_nodes() for p in partitions]
        avg_nodes = sum(node_counts) / len(node_counts)

        # Partitions should be within 50% of average (reasonable balance)
        for count in node_counts:
            assert count > avg_nodes * 0.5
            assert count < avg_nodes * 1.5

    def test_save_partition(self, small_graph, temp_partition_dir):
        """Test saving partition to disk."""
        partitioner = GraphPartitioner()

        # Create a partition
        partitions = partitioner.partition_graph(small_graph, num_partitions=2)

        # Save first partition
        saved_path = partitioner.save_partition(
            partitions[0], partition_id=0, output_dir=temp_partition_dir
        )

        assert Path(saved_path).exists()
        assert Path(saved_path).name == "partition-0.pkl"

    def test_load_partition(self, small_graph, temp_partition_dir):
        """Test loading partition from disk."""
        partitioner = GraphPartitioner()

        # Create and save a partition
        partitions = partitioner.partition_graph(small_graph, num_partitions=2)
        partitioner.save_partition(
            partitions[0], partition_id=0, output_dir=temp_partition_dir
        )

        # Load the partition
        loaded_partition = partitioner.load_partition(
            partition_id=0, input_dir=temp_partition_dir
        )

        assert isinstance(loaded_partition, nx.DiGraph)
        assert loaded_partition.number_of_nodes() == partitions[0].number_of_nodes()
        assert loaded_partition.number_of_edges() == partitions[0].number_of_edges()

    def test_load_nonexistent_partition(self, temp_partition_dir):
        """Test loading non-existent partition raises error."""
        partitioner = GraphPartitioner()

        with pytest.raises(FileNotFoundError):
            partitioner.load_partition(partition_id=999, input_dir=temp_partition_dir)

    def test_save_load_compression(self, medium_graph, temp_partition_dir):
        """Test partition compression during save/load."""
        partitioner = GraphPartitioner()

        # Create and save partition
        partitions = partitioner.partition_graph(medium_graph, num_partitions=2)
        saved_path = partitioner.save_partition(
            partitions[0], partition_id=0, output_dir=temp_partition_dir
        )

        # Check file exists and is compressed (should be smaller than uncompressed)
        file_size = Path(saved_path).stat().st_size
        assert file_size > 0
        # Compressed file should be reasonably small (< 1MB for this test graph)
        assert file_size < 1024 * 1024

    def test_get_partition_info(self, small_graph, temp_partition_dir):
        """Test getting partition metadata."""
        partitioner = GraphPartitioner()

        # Create and save partition
        partitions = partitioner.partition_graph(small_graph, num_partitions=2)
        saved_path = partitioner.save_partition(
            partitions[0], partition_id=0, output_dir=temp_partition_dir
        )

        # Get partition info
        info = partitioner.get_partition_info(
            partitions[0], partition_id=0, artifact_path=saved_path
        )

        assert isinstance(info, PartitionInfo)
        assert info.partition_id == 0
        assert info.node_count == partitions[0].number_of_nodes()
        assert info.edge_count == partitions[0].number_of_edges()
        assert info.artifact_path == saved_path


# ============================================================================
# Unit tests for PartitionAnalysisWorker
# ============================================================================


class TestPartitionAnalysisWorker:
    """Test PartitionAnalysisWorker functionality."""

    def test_initialization(self):
        """Test PartitionAnalysisWorker initialization."""
        worker = PartitionAnalysisWorker(partition_id=0)

        assert worker.partition_id == 0
        assert worker.parallel_manager is not None

    def test_analyze_partition_small(self, small_graph):
        """Test analyzing a small partition."""
        worker = PartitionAnalysisWorker(partition_id=0)

        results = worker.analyze_partition(small_graph)

        assert isinstance(results, PartitionResults)
        assert results.partition_id == 0
        assert len(results.communities) == small_graph.number_of_nodes()
        assert len(results.centrality) == small_graph.number_of_nodes()
        assert len(results.layout) == small_graph.number_of_nodes()
        assert isinstance(results.boundary_nodes, list)
        assert isinstance(results.metrics, dict)

    def test_analyze_partition_medium(self, medium_graph):
        """Test analyzing a medium partition (1K nodes)."""
        worker = PartitionAnalysisWorker(partition_id=1)

        results = worker.analyze_partition(medium_graph)

        assert isinstance(results, PartitionResults)
        assert results.partition_id == 1
        assert len(results.communities) == medium_graph.number_of_nodes()
        assert results.metrics["node_count"] == medium_graph.number_of_nodes()
        assert results.metrics["edge_count"] == medium_graph.number_of_edges()
        assert results.metrics["community_count"] > 0

    def test_community_detection(self, small_graph):
        """Test community detection on partition."""
        worker = PartitionAnalysisWorker(partition_id=0)

        results = worker.analyze_partition(small_graph)

        # Should detect at least 2 communities (we created 2 in the fixture)
        unique_communities = set(results.communities.values())
        assert len(unique_communities) >= 2

        # All nodes should be assigned to a community
        assert len(results.communities) == small_graph.number_of_nodes()

    def test_centrality_calculation(self, small_graph):
        """Test centrality calculation with parallel execution."""
        worker = PartitionAnalysisWorker(partition_id=0)

        results = worker.analyze_partition(small_graph)

        # All nodes should have centrality scores
        assert len(results.centrality) == small_graph.number_of_nodes()

        # Centrality scores should be between 0 and 1
        for score in results.centrality.values():
            assert 0 <= score <= 1

    def test_layout_calculation(self, small_graph):
        """Test layout calculation for visualization."""
        worker = PartitionAnalysisWorker(partition_id=0)

        results = worker.analyze_partition(small_graph)

        # All nodes should have layout positions
        assert len(results.layout) == small_graph.number_of_nodes()

        # Layout positions should be tuples of (x, y)
        for pos in results.layout.values():
            assert isinstance(pos, tuple)
            assert len(pos) == 2
            assert isinstance(pos[0], float)
            assert isinstance(pos[1], float)

    def test_boundary_node_identification(self, small_graph):
        """Test boundary node identification."""
        worker = PartitionAnalysisWorker(partition_id=0)

        results = worker.analyze_partition(small_graph)

        # Should identify some boundary nodes
        assert isinstance(results.boundary_nodes, list)
        # Boundary nodes should be a subset of all nodes
        assert len(results.boundary_nodes) <= small_graph.number_of_nodes()

    def test_auto_scaling_1_core(self, small_graph):
        """Test auto-scaling with 1 core configuration."""
        worker = PartitionAnalysisWorker(partition_id=0)
        # Force 1 core for testing
        worker.parallel_manager._cpu_count = 1

        results = worker.analyze_partition(small_graph)

        # Should still complete successfully
        assert isinstance(results, PartitionResults)
        assert len(results.communities) == small_graph.number_of_nodes()

    def test_auto_scaling_4_cores(self, small_graph):
        """Test auto-scaling with 4 core configuration."""
        worker = PartitionAnalysisWorker(partition_id=0)
        # Force 4 cores for testing
        worker.parallel_manager._cpu_count = 4

        results = worker.analyze_partition(small_graph)

        # Should complete successfully with parallel processing
        assert isinstance(results, PartitionResults)
        assert len(results.communities) == small_graph.number_of_nodes()

    def test_metrics_calculation(self, small_graph):
        """Test partition metrics calculation."""
        worker = PartitionAnalysisWorker(partition_id=0)

        results = worker.analyze_partition(small_graph)

        # Check all expected metrics are present
        assert "node_count" in results.metrics
        assert "edge_count" in results.metrics
        assert "community_count" in results.metrics
        assert "boundary_node_count" in results.metrics
        assert "density" in results.metrics

        # Verify metric values
        assert results.metrics["node_count"] == small_graph.number_of_nodes()
        assert results.metrics["edge_count"] == small_graph.number_of_edges()
        assert results.metrics["community_count"] > 0
        assert 0 <= results.metrics["density"] <= 1


# ============================================================================
# Unit tests for PartitionResultsMerger
# ============================================================================


class TestPartitionResultsMerger:
    """Test PartitionResultsMerger functionality."""

    def test_initialization(self):
        """Test PartitionResultsMerger initialization."""
        merger = PartitionResultsMerger()

        assert merger is not None

    def test_merge_communities_simple(self):
        """Test merging community assignments from multiple partitions."""
        merger = PartitionResultsMerger()

        # Create mock partition results
        results1 = PartitionResults(
            partition_id=0,
            communities={"node_0": 0, "node_1": 0, "node_2": 1},
            centrality={},
            layout={},
            boundary_nodes=[],
            metrics={},
        )

        results2 = PartitionResults(
            partition_id=1,
            communities={"node_3": 0, "node_4": 1, "node_5": 1},
            centrality={},
            layout={},
            boundary_nodes=[],
            metrics={},
        )

        global_communities = merger.merge_communities([results1, results2])

        # All nodes should be present
        assert len(global_communities) == 6

        # Community IDs should be globally unique (no conflicts)
        # Partition 0 has communities 0, 1
        # Partition 1 has communities 0, 1 -> should become 2, 3
        assert global_communities["node_0"] == 0
        assert global_communities["node_1"] == 0
        assert global_communities["node_2"] == 1
        assert global_communities["node_3"] == 2  # Offset by 2
        assert global_communities["node_4"] == 3  # Offset by 2
        assert global_communities["node_5"] == 3  # Offset by 2

    def test_merge_communities_overlapping(self):
        """Test merging communities with overlapping community IDs."""
        merger = PartitionResultsMerger()

        # Create partition results with same community IDs
        results = [
            PartitionResults(
                partition_id=i,
                communities={f"node_{i}_{j}": j % 3 for j in range(10)},
                centrality={},
                layout={},
                boundary_nodes=[],
                metrics={},
            )
            for i in range(3)
        ]

        global_communities = merger.merge_communities(results)

        # All 30 nodes should be present
        assert len(global_communities) == 30

        # Community IDs should be unique across partitions
        community_ids = set(global_communities.values())
        # Should have 9 unique communities (3 partitions × 3 communities each)
        assert len(community_ids) == 9

    def test_merge_centrality_simple(self):
        """Test merging centrality scores."""
        merger = PartitionResultsMerger()

        results1 = PartitionResults(
            partition_id=0,
            communities={},
            centrality={"node_0": 0.5, "node_1": 0.8, "node_2": 1.0},
            layout={},
            boundary_nodes=[],
            metrics={},
        )

        results2 = PartitionResults(
            partition_id=1,
            communities={},
            centrality={"node_3": 0.3, "node_4": 0.6, "node_5": 0.4},
            layout={},
            boundary_nodes=[],
            metrics={},
        )

        global_centrality = merger.merge_centrality([results1, results2])

        # All nodes should be present
        assert len(global_centrality) == 6

        # Scores should be normalized to [0, 1]
        for score in global_centrality.values():
            assert 0 <= score <= 1

        # Highest score should be 1.0 (normalized)
        assert max(global_centrality.values()) == 1.0

    def test_merge_centrality_normalization(self):
        """Test centrality normalization across partitions."""
        merger = PartitionResultsMerger()

        # Create results with different score ranges
        results = [
            PartitionResults(
                partition_id=0,
                communities={},
                centrality={"node_0": 10.0, "node_1": 20.0},
                layout={},
                boundary_nodes=[],
                metrics={},
            ),
            PartitionResults(
                partition_id=1,
                communities={},
                centrality={"node_2": 5.0, "node_3": 15.0},
                layout={},
                boundary_nodes=[],
                metrics={},
            ),
        ]

        global_centrality = merger.merge_centrality(results)

        # Should normalize to [0, 1] based on max value (20.0)
        assert global_centrality["node_0"] == pytest.approx(0.5)
        assert global_centrality["node_1"] == pytest.approx(1.0)
        assert global_centrality["node_2"] == pytest.approx(0.25)
        assert global_centrality["node_3"] == pytest.approx(0.75)

    def test_merge_layouts_grid_positioning(self):
        """Test hierarchical layout positioning in grid."""
        merger = PartitionResultsMerger()

        # Create partition results with local layouts
        results = [
            PartitionResults(
                partition_id=i,
                communities={},
                centrality={},
                layout={
                    f"node_{i}_0": (0.0, 0.0),
                    f"node_{i}_1": (1.0, 1.0),
                },
                boundary_nodes=[],
                metrics={},
            )
            for i in range(4)
        ]

        global_layout = merger.merge_layouts(results)

        # All nodes should be present
        assert len(global_layout) == 8

        # Partitions should be positioned in different grid cells
        # Check that partitions are separated
        partition_0_nodes = [global_layout[f"node_0_{j}"] for j in range(2)]
        partition_1_nodes = [global_layout[f"node_1_{j}"] for j in range(2)]

        # Partitions should have different base positions
        avg_x_0 = sum(pos[0] for pos in partition_0_nodes) / len(partition_0_nodes)
        avg_x_1 = sum(pos[0] for pos in partition_1_nodes) / len(partition_1_nodes)

        # Should be in different grid cells (at least 50 units apart)
        assert (
            abs(avg_x_0 - avg_x_1) > 50
            or abs(
                sum(pos[1] for pos in partition_0_nodes) / len(partition_0_nodes)
                - sum(pos[1] for pos in partition_1_nodes) / len(partition_1_nodes)
            )
            > 50
        )

    def test_merge_layouts_boundary_nodes(self):
        """Test boundary node handling in layout merging."""
        merger = PartitionResultsMerger()

        results = [
            PartitionResults(
                partition_id=0,
                communities={},
                centrality={},
                layout={"node_0": (0.0, 0.0), "node_1": (1.0, 1.0)},
                boundary_nodes=["node_1"],  # node_1 is a boundary node
                metrics={},
            ),
            PartitionResults(
                partition_id=1,
                communities={},
                centrality={},
                layout={"node_2": (0.0, 0.0), "node_3": (1.0, 1.0)},
                boundary_nodes=["node_2"],  # node_2 is a boundary node
                metrics={},
            ),
        ]

        global_layout = merger.merge_layouts(results)

        # All nodes should have positions
        assert len(global_layout) == 4

        # Boundary nodes should have valid positions
        assert "node_1" in global_layout
        assert "node_2" in global_layout

    def test_create_final_graph(self, small_graph):
        """Test creating final graph with merged attributes."""
        merger = PartitionResultsMerger()

        # Create merged results
        merged_results = MergedResults(
            global_communities={
                node: i % 3 for i, node in enumerate(small_graph.nodes())
            },
            global_centrality=dict.fromkeys(small_graph.nodes(), 0.5),
            global_layout=dict.fromkeys(small_graph.nodes(), (0.0, 0.0)),
            partition_count=2,
            total_nodes=small_graph.number_of_nodes(),
            merge_time=1.0,
            logs="Test merge",
        )

        # Create final graph
        final_graph = merger.create_final_graph(small_graph, merged_results)

        # Graph structure should be preserved
        assert final_graph.number_of_nodes() == small_graph.number_of_nodes()
        assert final_graph.number_of_edges() == small_graph.number_of_edges()

        # Attributes should be added
        sample_node = list(final_graph.nodes())[0]
        assert "community" in final_graph.nodes[sample_node]
        assert "betweenness" in final_graph.nodes[sample_node]

    def test_merge_all_integration(self, small_graph):
        """Test complete merge workflow."""
        # Create partitions
        partitioner = GraphPartitioner()
        partitions = partitioner.partition_graph(small_graph, num_partitions=2)

        # Analyze each partition
        partition_results = []
        for i, partition in enumerate(partitions):
            worker = PartitionAnalysisWorker(partition_id=i)
            results = worker.analyze_partition(partition)
            partition_results.append(results)

        # Merge results
        merger = PartitionResultsMerger()
        merged_results = merger.merge_all(partition_results, small_graph)

        # Verify merged results
        assert isinstance(merged_results, MergedResults)
        assert merged_results.partition_count == 2
        assert merged_results.total_nodes == small_graph.number_of_nodes()
        assert len(merged_results.global_communities) == small_graph.number_of_nodes()
        assert len(merged_results.global_centrality) == small_graph.number_of_nodes()
        assert len(merged_results.global_layout) == small_graph.number_of_nodes()
        assert merged_results.merge_time > 0

    def test_load_all_results(self, temp_partition_dir):
        """Test loading all partition results from artifacts."""
        import joblib

        merger = PartitionResultsMerger()

        # Create and save mock results
        for i in range(3):
            results = PartitionResults(
                partition_id=i,
                communities={f"node_{i}": 0},
                centrality={f"node_{i}": 0.5},
                layout={f"node_{i}": (0.0, 0.0)},
                boundary_nodes=[],
                metrics={},
            )
            result_file = Path(temp_partition_dir) / f"partition-{i}-results.pkl"
            joblib.dump(results, result_file)

        # Load all results
        loaded_results = merger.load_all_results(temp_partition_dir)

        assert len(loaded_results) == 3
        for i, results in enumerate(loaded_results):
            assert results.partition_id == i

    def test_load_all_results_empty_directory(self, temp_partition_dir):
        """Test loading from empty directory raises error."""
        merger = PartitionResultsMerger()

        with pytest.raises(FileNotFoundError, match="No partition result files found"):
            merger.load_all_results(temp_partition_dir)

    def test_load_all_results_nonexistent_directory(self):
        """Test loading from non-existent directory raises error."""
        merger = PartitionResultsMerger()

        with pytest.raises(
            FileNotFoundError,
            match="(Results directory not found|No partition result files found)",
        ):
            merger.load_all_results("/nonexistent/directory")
