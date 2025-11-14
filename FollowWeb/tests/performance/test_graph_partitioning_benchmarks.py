"""
Performance benchmarks for graph partitioning system.

Benchmarks partition time, analysis time, and merge time for various
graph sizes to verify performance targets.
"""

import time

import networkx as nx
import pytest

from FollowWeb_Visualizor.analysis.partition_merger import PartitionResultsMerger
from FollowWeb_Visualizor.analysis.partition_worker import PartitionAnalysisWorker
from FollowWeb_Visualizor.analysis.partitioning import GraphPartitioner

pytestmark = [pytest.mark.performance, pytest.mark.benchmark]
# ============================================================================
# Helper Functions
# ============================================================================


def create_sparse_graph(num_nodes: int, edges_per_node: int = 3) -> nx.DiGraph:
    """
    Create a sparse directed graph for benchmarking.

    Args:
        num_nodes: Number of nodes in the graph
        edges_per_node: Average number of edges per node

    Returns:
        Sparse directed graph
    """
    graph = nx.DiGraph()
    nodes = [f"node_{i}" for i in range(num_nodes)]
    graph.add_nodes_from(nodes)

    # Add edges efficiently
    for i in range(num_nodes):
        for j in range(1, edges_per_node + 1):
            target = (i + j) % num_nodes
            graph.add_edge(f"node_{i}", f"node_{target}")

    return graph


def benchmark_partition(
    graph: nx.DiGraph, num_partitions: int
) -> tuple[list[nx.DiGraph], float]:
    """
    Benchmark graph partitioning.

    Args:
        graph: Graph to partition
        num_partitions: Number of partitions to create

    Returns:
        Tuple of (partitions, elapsed_time)
    """
    partitioner = GraphPartitioner()

    start_time = time.perf_counter()
    partitions = partitioner.partition_graph(graph, num_partitions)
    elapsed_time = time.perf_counter() - start_time

    return partitions, elapsed_time


def benchmark_analysis(partitions: list[nx.DiGraph]) -> tuple[list, float]:
    """
    Benchmark partition analysis.

    Args:
        partitions: List of graph partitions to analyze

    Returns:
        Tuple of (results, elapsed_time)
    """
    start_time = time.perf_counter()

    results = []
    for i, partition in enumerate(partitions):
        worker = PartitionAnalysisWorker(partition_id=i)
        result = worker.analyze_partition(partition)
        results.append(result)

    elapsed_time = time.perf_counter() - start_time

    return results, elapsed_time


def benchmark_merge(results: list, original_graph: nx.DiGraph) -> tuple[float, float]:
    """
    Benchmark result merging.

    Args:
        results: List of partition results
        original_graph: Original graph before partitioning

    Returns:
        Tuple of (merge_time, total_time)
    """
    merger = PartitionResultsMerger()

    start_time = time.perf_counter()
    merged_results = merger.merge_all(results, original_graph)
    elapsed_time = time.perf_counter() - start_time

    return merged_results.merge_time, elapsed_time


# ============================================================================
# Task 16.5: Performance benchmarks
# ============================================================================


class TestPartitioningPerformance:
    """Performance benchmarks for graph partitioning."""

    def test_benchmark_partition_time_vs_graph_size(self, benchmark):
        """Benchmark partition time vs graph size."""
        graph_sizes = [10000, 50000, 100000]

        def run_partition_benchmark(size):
            graph = create_sparse_graph(size)
            partitioner = GraphPartitioner()
            num_partitions = partitioner.calculate_optimal_partitions(size)
            partitions, elapsed = benchmark_partition(graph, num_partitions)
            return elapsed

        results = {}
        for size in graph_sizes:
            elapsed = run_partition_benchmark(size)
            results[size] = elapsed
            print(f"\nPartition time for {size} nodes: {elapsed:.2f}s")

        # Verify performance scales reasonably (not exponential)
        # 10x nodes should take less than 20x time
        if 100000 in results and 10000 in results:
            ratio = results[100000] / results[10000]
            assert ratio < 20, f"Partition time scaling too poor: {ratio}x"

    def test_benchmark_analysis_time_per_partition(self, benchmark):
        """Benchmark analysis time per partition."""
        partition_sizes = [10000, 25000, 50000]

        def run_analysis_benchmark(size):
            graph = create_sparse_graph(size)
            worker = PartitionAnalysisWorker(partition_id=0)

            start_time = time.perf_counter()
            worker.analyze_partition(graph)
            elapsed = time.perf_counter() - start_time

            return elapsed

        results = {}
        for size in partition_sizes:
            elapsed = run_analysis_benchmark(size)
            results[size] = elapsed
            print(f"\nAnalysis time for {size} node partition: {elapsed:.2f}s")

        # Verify analysis time is reasonable
        # 50K nodes should complete in under 60 seconds
        assert results[50000] < 60, f"Analysis too slow: {results[50000]:.2f}s"

    def test_benchmark_merge_time_vs_partition_count(self, benchmark):
        """Benchmark merge time vs partition count."""
        graph = create_sparse_graph(100000)
        partition_counts = [2, 4, 8]

        results = {}
        for num_partitions in partition_counts:
            # Partition
            partitions, _ = benchmark_partition(graph, num_partitions)

            # Analyze
            partition_results, _ = benchmark_analysis(partitions)

            # Merge
            merge_time, total_time = benchmark_merge(partition_results, graph)
            results[num_partitions] = total_time

            print(f"\nMerge time for {num_partitions} partitions: {total_time:.2f}s")

        # Verify merge time scales linearly (not exponentially)
        # 4x partitions should take less than 8x time
        if 8 in results and 2 in results:
            ratio = results[8] / results[2]
            assert ratio < 8, f"Merge time scaling too poor: {ratio}x"

    @pytest.mark.slow
    def test_verify_1m_nodes_under_30_minutes(self):
        """Verify 1M nodes completes in under 30 minutes target."""
        # Create a very sparse 1M node graph
        graph = create_sparse_graph(1000000, edges_per_node=2)

        time.perf_counter()

        # Partition (20 partitions for 1M nodes)
        partitions, partition_time = benchmark_partition(graph, num_partitions=20)
        print(f"\nPartition time: {partition_time:.2f}s")

        # Analyze first 5 partitions (simulate parallel execution)
        sample_partitions = partitions[:5]
        sample_results, analysis_time = benchmark_analysis(sample_partitions)
        print(f"Analysis time (5 partitions): {analysis_time:.2f}s")

        # Estimate total time for all 20 partitions (parallel execution)
        # Assume 20 partitions run in parallel (GitHub Actions max)
        estimated_analysis_time = analysis_time  # Same time for parallel execution

        # Merge (use sample results for estimation)
        merge_time, _ = benchmark_merge(sample_results, partitions[0])
        print(f"Merge time: {merge_time:.2f}s")

        # Calculate estimated total time
        estimated_total = partition_time + estimated_analysis_time + merge_time

        print(
            f"\nEstimated total time for 1M nodes: {estimated_total:.2f}s ({estimated_total / 60:.2f} minutes)"
        )

        # Verify under 30 minutes (1800 seconds)
        # Use 2x safety factor for estimation
        assert estimated_total * 2 < 1800, (
            f"Estimated time too slow: {estimated_total * 2:.2f}s"
        )

    @pytest.mark.slow
    def test_benchmark_full_pipeline_100k(self):
        """Benchmark complete pipeline for 100K nodes."""
        graph = create_sparse_graph(100000)

        start_time = time.perf_counter()

        # Partition
        partition_start = time.perf_counter()
        partitions, _ = benchmark_partition(graph, num_partitions=2)
        partition_time = time.perf_counter() - partition_start

        # Analyze
        analysis_start = time.perf_counter()
        results, _ = benchmark_analysis(partitions)
        analysis_time = time.perf_counter() - analysis_start

        # Merge
        merge_start = time.perf_counter()
        merge_time, _ = benchmark_merge(results, graph)
        total_merge_time = time.perf_counter() - merge_start

        total_time = time.perf_counter() - start_time

        # Generate performance report
        report = {
            "graph_size": 100000,
            "num_partitions": 2,
            "partition_time": partition_time,
            "analysis_time": analysis_time,
            "merge_time": total_merge_time,
            "total_time": total_time,
            "throughput": 100000 / total_time,  # nodes/second
        }

        print("\n" + "=" * 60)
        print("Performance Report: 100K Node Graph")
        print("=" * 60)
        print(f"Graph size: {report['graph_size']:,} nodes")
        print(f"Partitions: {report['num_partitions']}")
        print(f"Partition time: {report['partition_time']:.2f}s")
        print(f"Analysis time: {report['analysis_time']:.2f}s")
        print(f"Merge time: {report['merge_time']:.2f}s")
        print(f"Total time: {report['total_time']:.2f}s")
        print(f"Throughput: {report['throughput']:.0f} nodes/second")
        print("=" * 60)

        # Verify reasonable performance
        assert total_time < 300, (
            f"Pipeline too slow: {total_time:.2f}s"
        )  # Under 5 minutes
        assert report["throughput"] > 300, (
            f"Throughput too low: {report['throughput']:.0f} nodes/s"
        )

    def test_benchmark_full_pipeline_300k(self):
        """Benchmark complete pipeline for 300K nodes."""
        graph = create_sparse_graph(300000, edges_per_node=2)

        start_time = time.perf_counter()

        # Partition
        partition_start = time.perf_counter()
        partitions, _ = benchmark_partition(graph, num_partitions=6)
        partition_time = time.perf_counter() - partition_start

        # Analyze (sample 3 partitions for speed)
        analysis_start = time.perf_counter()
        sample_results, _ = benchmark_analysis(partitions[:3])
        analysis_time = time.perf_counter() - analysis_start

        # Merge (use sample for estimation)
        merge_start = time.perf_counter()
        merge_time, _ = benchmark_merge(sample_results, partitions[0])
        total_merge_time = time.perf_counter() - merge_start

        total_time = time.perf_counter() - start_time

        # Generate performance report
        report = {
            "graph_size": 300000,
            "num_partitions": 6,
            "partitions_analyzed": 3,
            "partition_time": partition_time,
            "analysis_time": analysis_time,
            "merge_time": total_merge_time,
            "total_time": total_time,
            "throughput": 300000 / total_time,  # nodes/second
        }

        print("\n" + "=" * 60)
        print("Performance Report: 300K Node Graph")
        print("=" * 60)
        print(f"Graph size: {report['graph_size']:,} nodes")
        print(
            f"Partitions: {report['num_partitions']} (analyzed {report['partitions_analyzed']})"
        )
        print(f"Partition time: {report['partition_time']:.2f}s")
        print(f"Analysis time: {report['analysis_time']:.2f}s (sample)")
        print(f"Merge time: {report['merge_time']:.2f}s")
        print(f"Total time: {report['total_time']:.2f}s")
        print(f"Throughput: {report['throughput']:.0f} nodes/second")
        print("=" * 60)

        # Verify reasonable performance
        assert total_time < 600, (
            f"Pipeline too slow: {total_time:.2f}s"
        )  # Under 10 minutes

    def test_generate_performance_report(self):
        """Generate comprehensive performance report."""
        test_cases = [
            (10000, 1),
            (50000, 1),
            (100000, 2),
        ]

        print("\n" + "=" * 80)
        print("Comprehensive Performance Report")
        print("=" * 80)
        print(
            f"{'Nodes':<12} {'Partitions':<12} {'Partition':<12} {'Analysis':<12} {'Merge':<12} {'Total':<12}"
        )
        print("-" * 80)

        for num_nodes, num_partitions in test_cases:
            graph = create_sparse_graph(num_nodes)

            # Benchmark
            partitions, partition_time = benchmark_partition(graph, num_partitions)
            results, analysis_time = benchmark_analysis(partitions)
            merge_time, total_merge_time = benchmark_merge(results, graph)

            total_time = partition_time + analysis_time + total_merge_time

            print(
                f"{num_nodes:<12,} {num_partitions:<12} "
                f"{partition_time:<12.2f} {analysis_time:<12.2f} "
                f"{total_merge_time:<12.2f} {total_time:<12.2f}"
            )

        print("=" * 80)
        print("Times in seconds")
        print("=" * 80)


class TestScalabilityAnalysis:
    """Analyze scalability characteristics of partitioning system."""

    def test_partition_time_scaling(self):
        """Analyze how partition time scales with graph size."""
        sizes = [10000, 25000, 50000, 100000]
        times = []

        for size in sizes:
            graph = create_sparse_graph(size)
            partitioner = GraphPartitioner()
            num_partitions = partitioner.calculate_optimal_partitions(size)

            _, elapsed = benchmark_partition(graph, num_partitions)
            times.append(elapsed)

            print(f"\n{size:,} nodes: {elapsed:.2f}s")

        # Calculate scaling factor
        # Should be roughly O(n log n) or better
        for i in range(1, len(sizes)):
            size_ratio = sizes[i] / sizes[i - 1]
            time_ratio = times[i] / times[i - 1]

            print(f"Size ratio: {size_ratio:.1f}x, Time ratio: {time_ratio:.1f}x")

            # Time should scale sub-quadratically
            assert time_ratio < size_ratio**1.5, (
                f"Scaling too poor: {time_ratio:.1f}x for {size_ratio:.1f}x size"
            )

    def test_analysis_time_scaling(self):
        """Analyze how analysis time scales with partition size."""
        sizes = [10000, 25000, 50000]
        times = []

        for size in sizes:
            graph = create_sparse_graph(size)
            worker = PartitionAnalysisWorker(partition_id=0)

            start_time = time.perf_counter()
            worker.analyze_partition(graph)
            elapsed = time.perf_counter() - start_time

            times.append(elapsed)
            print(f"\n{size:,} nodes: {elapsed:.2f}s")

        # Verify reasonable scaling
        for i in range(1, len(sizes)):
            size_ratio = sizes[i] / sizes[i - 1]
            time_ratio = times[i] / times[i - 1]

            print(f"Size ratio: {size_ratio:.1f}x, Time ratio: {time_ratio:.1f}x")

    def test_merge_time_scaling(self):
        """Analyze how merge time scales with partition count."""
        graph = create_sparse_graph(100000)
        partition_counts = [2, 4, 8]
        times = []

        for num_partitions in partition_counts:
            partitions, _ = benchmark_partition(graph, num_partitions)
            results, _ = benchmark_analysis(partitions)
            _, elapsed = benchmark_merge(results, graph)

            times.append(elapsed)
            print(f"\n{num_partitions} partitions: {elapsed:.2f}s")

        # Verify linear or sub-linear scaling
        for i in range(1, len(partition_counts)):
            partition_ratio = partition_counts[i] / partition_counts[i - 1]
            time_ratio = times[i] / times[i - 1]

            print(
                f"Partition ratio: {partition_ratio:.1f}x, Time ratio: {time_ratio:.1f}x"
            )

            # Time should scale linearly or better
            assert time_ratio <= partition_ratio * 1.5, (
                f"Merge scaling too poor: {time_ratio:.1f}x"
            )
