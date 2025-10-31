"""
Benchmark tests for FollowWeb Network Analysis Package.

These tests use pytest-benchmark and must run sequentially (no xdist).
Use: pytest -m benchmark -n 0 --benchmark-only
"""

from typing import Any, Dict

import networkx as nx
import pytest

from FollowWeb_Visualizor.core.config import load_config_from_dict


class TestBenchmarks:
    """Benchmark tests using pytest-benchmark."""

    @pytest.mark.benchmark
    def test_config_loading_benchmark(self, benchmark, default_config: Dict[str, Any]):
        """Benchmark configuration loading performance."""

        def load_config():
            return load_config_from_dict(default_config)

        result = benchmark(load_config)
        assert result is not None

    @pytest.mark.benchmark
    def test_small_graph_creation_benchmark(self, benchmark):
        """Benchmark small graph creation performance."""

        def create_small_graph():
            graph = nx.Graph()
            edges = [(i, i + 1) for i in range(100)]
            graph.add_edges_from(edges)
            return graph

        result = benchmark(create_small_graph)
        assert len(result.nodes()) == 101
        assert len(result.edges()) == 100

    @pytest.mark.benchmark
    def test_centrality_calculation_benchmark(self, benchmark):
        """Benchmark centrality calculation performance."""
        # Setup graph outside benchmark
        graph = nx.Graph()
        edges = [(i, i + 1) for i in range(50)]
        graph.add_edges_from(edges)

        def calculate_centrality():
            return nx.degree_centrality(graph)

        result = benchmark(calculate_centrality)
        assert len(result) == 51

    @pytest.mark.benchmark
    def test_community_detection_benchmark(self, benchmark):
        """Benchmark community detection performance."""
        # Setup graph outside benchmark
        graph = nx.Graph()
        edges = [(i, i + 1) for i in range(30)]
        graph.add_edges_from(edges)

        def detect_communities():
            return list(nx.community.greedy_modularity_communities(graph))

        result = benchmark(detect_communities)
        assert len(result) > 0
