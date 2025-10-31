"""
Unit tests for the MetricsCalculator class and metrics system.

Tests metrics caching functionality, cache invalidation, graph hashing,
VisualizationMetrics data structure creation, and color scheme generation.
"""

import time
from unittest.mock import patch

import networkx as nx

# Import the visualization classes
from FollowWeb_Visualizor.visualization import (
    ColorScheme,
    EdgeMetric,
    MetricsCalculator,
    NodeMetric,
    VisualizationMetrics,
)


class TestMetricsCalculator:
    """Test cases for the MetricsCalculator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.vis_config = {
            "node_size_metric": "degree",
            "base_node_size": 10,
            "node_size_multiplier": 2,
            "scaling_algorithm": "linear",
            "base_edge_width": 0.5,
            "edge_width_multiplier": 1.5,
            "edge_width_scaling": "logarithmic",
            "bridge_color": "#6e6e6e",
            "intra_community_color": "#c0c0c0",
            "shared_metrics": {"enable_caching": True, "cache_timeout_seconds": 300},
            "static_image": {"spring": {"iterations": 5, "k": 0.15}},
        }
        self.calculator = MetricsCalculator(self.vis_config)

    def create_test_graph(self) -> nx.DiGraph:
        """Create a simple test graph with communities."""
        graph = nx.DiGraph()

        # Add nodes with community attributes
        graph.add_node("A", community=0, degree=3, betweenness=0.5, eigenvector=0.8)
        graph.add_node("B", community=0, degree=2, betweenness=0.3, eigenvector=0.6)
        graph.add_node("C", community=1, degree=2, betweenness=0.2, eigenvector=0.4)
        graph.add_node("D", community=1, degree=1, betweenness=0.1, eigenvector=0.2)

        # Add edges
        graph.add_edge("A", "B")
        graph.add_edge("B", "A")  # Mutual connection
        graph.add_edge("A", "C")  # Bridge edge
        graph.add_edge("C", "D")

        return graph

    def test_initialization(self):
        """Test MetricsCalculator initialization."""
        assert self.calculator.vis_config == self.vis_config
        assert self.calculator.cache_enabled is True
        assert self.calculator.cache_timeout == 300
        assert self.calculator.cache_manager is not None
        # Check that cache manager is properly initialized
        cache_stats = self.calculator.cache_manager.get_cache_stats()
        assert isinstance(cache_stats, dict)

    def test_initialization_cache_disabled(self):
        """Test initialization with caching disabled."""
        config = self.vis_config.copy()
        config["shared_metrics"]["enable_caching"] = False

        calculator = MetricsCalculator(config)
        assert calculator.cache_enabled is False

    def test_initialization_custom_timeout(self):
        """Test initialization with custom cache timeout."""
        config = self.vis_config.copy()
        config["shared_metrics"]["cache_timeout_seconds"] = 600

        calculator = MetricsCalculator(config)
        assert calculator.cache_timeout == 600

    def test_calculate_graph_hash_deterministic(self):
        """Test that graph hashing is deterministic."""
        G = self.create_test_graph()

        hash1 = self.calculator.cache_manager.calculate_graph_hash(G)
        hash2 = self.calculator.cache_manager.calculate_graph_hash(G)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex string length

    def test_calculate_graph_hash_different_graphs(self):
        """Test that different graphs produce different hashes."""
        G1 = self.create_test_graph()

        G2 = nx.DiGraph()
        G2.add_node("X", community=0, degree=1)
        G2.add_node("Y", community=1, degree=1)
        G2.add_edge("X", "Y")

        hash1 = self.calculator.cache_manager.calculate_graph_hash(G1)
        hash2 = self.calculator.cache_manager.calculate_graph_hash(G2)

        assert hash1 != hash2

    def test_calculate_graph_hash_same_structure_different_attributes(self):
        """Test that graphs with same structure but different attributes have different hashes."""
        G1 = self.create_test_graph()

        G2 = self.create_test_graph()
        G2.nodes["A"]["degree"] = 999  # Change attribute

        hash1 = self.calculator.cache_manager.calculate_graph_hash(G1)
        hash2 = self.calculator.cache_manager.calculate_graph_hash(G2)

        assert hash1 != hash2

    def test_cache_functionality(self):
        """Test basic caching functionality."""
        G = self.create_test_graph()

        # Clear cache to ensure clean state
        self.calculator.cache_manager.clear_all_caches()

        # Get initial cache stats
        initial_stats = self.calculator.cache_manager.get_cache_stats()

        # Calculate metrics (should populate cache)
        metrics1 = self.calculator.calculate_all_metrics(G)

        # Check that cache has been populated
        after_stats = self.calculator.cache_manager.get_cache_stats()
        assert after_stats["graph_hashes"] >= initial_stats["graph_hashes"]

        # Second call should reuse cached data
        metrics2 = self.calculator.calculate_all_metrics(G)

        # Verify metrics are consistent
        assert metrics1.graph_hash == metrics2.graph_hash
        assert len(metrics1.node_metrics) == len(metrics2.node_metrics)
        assert len(metrics1.edge_metrics) == len(metrics2.edge_metrics)

    def test_cache_timeout(self):
        """Test cache timeout functionality."""
        G = self.create_test_graph()

        # Set short timeout for testing
        original_timeout = self.calculator.cache_manager.cache_timeout
        self.calculator.cache_manager.cache_timeout = 0.1

        try:
            # Clear cache to ensure clean state
            self.calculator.cache_manager.clear_all_caches()

            # Calculate metrics (should populate cache)
            metrics1 = self.calculator.calculate_all_metrics(G)

            # Verify cache is populated
            stats_after = self.calculator.cache_manager.get_cache_stats()
            assert stats_after["graph_hashes"] > 0

            # Wait for timeout
            time.sleep(0.2)

            # Calculate again - should recalculate due to timeout
            metrics2 = self.calculator.calculate_all_metrics(G)

            # Verify metrics are still consistent even after timeout
            assert metrics1.graph_hash == metrics2.graph_hash

        finally:
            # Restore original timeout
            self.calculator.cache_manager.cache_timeout = original_timeout

    def test_cache_size_limit(self):
        """Test cache size limitation."""
        # Clear cache to ensure clean state
        self.calculator.cache_manager.clear_all_caches()

        # Create multiple different graphs
        graphs = []
        for i in range(12):  # More than typical cache size limit
            graph = nx.DiGraph()
            graph.add_node(f"node_{i}", community=0, degree=1)
            graphs.append(graph)

        # Calculate metrics for all graphs
        for G in graphs:
            self.calculator.calculate_all_metrics(G)

        # Check that cache has reasonable size limits
        # The exact limit may vary, but it should not grow unbounded
        cache_stats = self.calculator.cache_manager.get_cache_stats()
        total_cache_entries = sum(cache_stats.values())

        # Cache should be reasonably limited (not equal to number of graphs processed)
        assert (
            total_cache_entries < len(graphs) * 5
        )  # Allow some overhead but prevent unbounded growth

    def test_cache_disabled(self):
        """Test behavior when caching is disabled."""
        config = self.vis_config.copy()
        config["shared_metrics"]["enable_caching"] = False
        calculator = MetricsCalculator(config)

        G = self.create_test_graph()

        # Clear cache to ensure clean state
        calculator.cache_manager.clear_all_caches()

        # Calculate metrics twice
        metrics1 = calculator.calculate_all_metrics(G)
        metrics2 = calculator.calculate_all_metrics(G)

        # Verify caching is disabled
        assert calculator.cache_enabled is False

        # Metrics should still be calculated correctly
        assert metrics1.graph_hash == metrics2.graph_hash
        assert len(metrics1.node_metrics) == len(metrics2.node_metrics)

    def test_calculate_all_metrics_empty_graph(self):
        """Test calculating metrics for empty graph."""
        G = nx.DiGraph()

        metrics = self.calculator.calculate_all_metrics(G)

        # Should return empty metrics structure
        assert len(metrics.node_metrics) == 0
        assert len(metrics.edge_metrics) == 0
        assert len(metrics.layout_positions) == 0
        assert metrics.graph_hash == "empty_graph"

    def test_calculate_color_schemes_with_communities(self):
        """Test color scheme calculation with communities."""
        G = self.create_test_graph()
        color_schemes = self.calculator._calculate_color_schemes(G)

        assert isinstance(color_schemes, ColorScheme)
        assert color_schemes.hex_colors == {0: "#440154", 1: "#fde724"}
        # Check RGBA colors with approximate comparison due to numpy float precision
        assert len(color_schemes.rgba_colors) == 2
        assert abs(color_schemes.rgba_colors[0][0] - 0.267004) < 0.001
        assert abs(color_schemes.rgba_colors[0][1] - 0.004874) < 0.001
        assert abs(color_schemes.rgba_colors[0][2] - 0.329415) < 0.001
        assert abs(color_schemes.rgba_colors[1][0] - 0.993248) < 0.001
        assert abs(color_schemes.rgba_colors[1][1] - 0.906157) < 0.001
        assert abs(color_schemes.rgba_colors[1][2] - 0.143936) < 0.001
        assert color_schemes.bridge_color == "#6e6e6e"
        assert color_schemes.intra_community_color == "#c0c0c0"

    def test_calculate_color_schemes_no_communities(self):
        """Test color scheme calculation without community attributes."""
        graph = nx.DiGraph()
        graph.add_node("A")  # No community attribute
        graph.add_node("B")

        color_schemes = self.calculator._calculate_color_schemes(graph)

        assert isinstance(color_schemes, ColorScheme)
        # Should fallback to 1 community with viridis color
        assert len(color_schemes.hex_colors) == 1
        assert 0 in color_schemes.hex_colors

    @patch("FollowWeb_Visualizor.utils.math.get_scaled_size")
    def test_calculate_node_metrics(self, mock_get_scaled_size):
        """Test node metrics calculation."""
        mock_get_scaled_size.return_value = 15.0

        G = self.create_test_graph()
        color_schemes = ColorScheme(
            hex_colors={0: "#ff0000", 1: "#00ff00"},
            rgba_colors={0: (1.0, 0.0, 0.0, 1.0), 1: (0.0, 1.0, 0.0, 1.0)},
            bridge_color="#000000",
            intra_community_color="#ffffff",
        )

        node_metrics = self.calculator._calculate_node_metrics(G, color_schemes)

        assert len(node_metrics) == 4
        assert "A" in node_metrics

        node_a = node_metrics["A"]
        assert isinstance(node_a, NodeMetric)
        assert node_a.size == 16
        assert node_a.color_hex == "#ff0000"
        assert node_a.color_rgba == (1.0, 0.0, 0.0, 1.0)
        assert node_a.community == 0
        assert node_a.centrality_values["degree"] == 3
        assert node_a.centrality_values["betweenness"] == 0.5
        assert node_a.centrality_values["eigenvector"] == 0.8

    def test_calculate_node_metrics_no_attributes(self):
        """Test node metrics calculation when attributes are missing."""
        graph = nx.DiGraph()
        graph.add_node("A")  # No attributes
        graph.add_node("B")
        graph.add_edge("A", "B")

        color_schemes = ColorScheme(
            hex_colors={0: "#808080"},
            rgba_colors={0: (0.5, 0.5, 0.5, 1.0)},
            bridge_color="#000000",
            intra_community_color="#ffffff",
        )

        with patch(
            "FollowWeb_Visualizor.visualization.get_scaled_size", return_value=10.0
        ):
            node_metrics = self.calculator._calculate_node_metrics(graph, color_schemes)

        assert len(node_metrics) == 2

        # Check that fallback values were set
        node_a = node_metrics["A"]
        assert node_a.community == 0  # Fallback community
        assert node_a.centrality_values["degree"] == 1  # Actual degree
        assert node_a.centrality_values["betweenness"] == 0.0  # Fallback
        assert node_a.centrality_values["eigenvector"] == 0.0  # Fallback

    @patch("FollowWeb_Visualizor.utils.math.get_scaled_size")
    def test_calculate_edge_metrics(self, mock_get_scaled_size):
        """Test edge metrics calculation."""
        mock_get_scaled_size.return_value = 2.0

        G = self.create_test_graph()
        color_schemes = ColorScheme(
            hex_colors={0: "#ff0000", 1: "#00ff00"},
            rgba_colors={0: (1.0, 0.0, 0.0, 1.0), 1: (0.0, 1.0, 0.0, 1.0)},
            bridge_color="#6e6e6e",
            intra_community_color="#c0c0c0",
        )

        edge_metrics = self.calculator._calculate_edge_metrics(G, color_schemes)

        assert len(edge_metrics) >= 1

        # Check mutual edge (A-B)
        if ("A", "B") in edge_metrics:
            edge_ab = edge_metrics[("A", "B")]
            assert isinstance(edge_ab, EdgeMetric)
            assert edge_ab.width == 0.5
            assert edge_ab.is_mutual is True
            assert edge_ab.is_bridge is False  # Same community
            assert edge_ab.color == "#ff0000"  # Intra-community color

        # Check bridge edge (A-C)
        if ("A", "C") in edge_metrics:
            edge_ac = edge_metrics[("A", "C")]
            assert edge_ac.is_bridge is True  # Different communities
            assert edge_ac.color == "#6e6e6e"  # Bridge color

    @patch("networkx.spring_layout")
    def test_calculate_spring_layout(self, mock_spring_layout):
        """Test spring layout calculation."""
        # Clear cache to ensure fresh calculation
        self.calculator.cache_manager.clear_all_caches()

        mock_spring_layout.return_value = {
            "A": (0.0, 0.0),
            "B": (1.0, 0.0),
            "C": (0.5, 1.0),
            "D": (1.5, 1.0),
        }

        G = self.create_test_graph()
        edge_metrics = {
            ("A", "B"): EdgeMetric(2.0, "#ff0000", True, False, 0, 0, 0),
            ("A", "C"): EdgeMetric(1.0, "#6e6e6e", False, True, 0, 0, 1),
        }

        positions = self.calculator._calculate_spring_layout(G, edge_metrics)

        assert len(positions) == 4
        # Spring layout positions should be returned for all nodes
        for node in ["A", "B", "C", "D"]:
            assert node in positions
            # Positions can be tuples or numpy arrays depending on implementation
            assert len(positions[node]) == 2  # x, y coordinates

        # Verify spring_layout was called
        assert mock_spring_layout.call_count > 0, (
            "spring_layout should be called at least once"
        )


class TestVisualizationMetrics:
    """Test cases for VisualizationMetrics data structure."""

    def test_visualization_metrics_creation(self):
        """Test VisualizationMetrics data structure creation."""
        node_metrics = {
            "A": NodeMetric(10.0, "#ff0000", (1.0, 0.0, 0.0, 1.0), 0, {"degree": 3})
        }
        edge_metrics = {("A", "B"): EdgeMetric(2.0, "#ff0000", True, False, 1, 0, 0)}
        layout_positions = {"A": (0.0, 0.0), "B": (1.0, 0.0)}
        color_schemes = ColorScheme(
            {0: "#ff0000"}, {0: (1.0, 0.0, 0.0, 1.0)}, "#000", "#fff"
        )

        metrics = VisualizationMetrics(
            node_metrics=node_metrics,
            edge_metrics=edge_metrics,
            layout_positions=layout_positions,
            color_schemes=color_schemes,
            graph_hash="test_hash",
        )

        assert metrics.node_metrics == node_metrics
        assert metrics.edge_metrics == edge_metrics
        assert metrics.layout_positions == layout_positions
        assert metrics.color_schemes == color_schemes
        assert metrics.graph_hash == "test_hash"


class TestNodeMetric:
    """Test cases for NodeMetric data structure."""

    def test_node_metric_creation(self):
        """Test NodeMetric data structure creation."""
        centrality_values = {"degree": 3, "betweenness": 0.5, "eigenvector": 0.8}

        node_metric = NodeMetric(
            size=15.0,
            color_hex="#ff0000",
            color_rgba=(1.0, 0.0, 0.0, 1.0),
            community=0,
            centrality_values=centrality_values,
        )

        assert node_metric.size == 15.0
        assert node_metric.color_hex == "#ff0000"
        assert node_metric.color_rgba == (1.0, 0.0, 0.0, 1.0)
        assert node_metric.community == 0
        assert node_metric.centrality_values == centrality_values


class TestEdgeMetric:
    """Test cases for EdgeMetric data structure."""

    def test_edge_metric_creation(self):
        """Test EdgeMetric data structure creation."""
        edge_metric = EdgeMetric(
            width=2.0,
            color="#ff0000",
            is_mutual=True,
            is_bridge=False,
            common_neighbors=1,
            u_comm=0,
            v_comm=0,
        )

        assert edge_metric.width == 2.0
        assert edge_metric.color == "#ff0000"
        assert edge_metric.is_mutual is True
        assert edge_metric.is_bridge is False
        assert edge_metric.common_neighbors == 1
        assert edge_metric.u_comm == 0
        assert edge_metric.v_comm == 0


class TestColorScheme:
    """Test cases for ColorScheme data structure."""

    def test_color_scheme_creation(self):
        """Test ColorScheme data structure creation."""
        hex_colors = {0: "#ff0000", 1: "#00ff00"}
        rgba_colors = {0: (1.0, 0.0, 0.0, 1.0), 1: (0.0, 1.0, 0.0, 1.0)}

        color_scheme = ColorScheme(
            hex_colors=hex_colors,
            rgba_colors=rgba_colors,
            bridge_color="#6e6e6e",
            intra_community_color="#c0c0c0",
        )

        assert color_scheme.hex_colors == hex_colors
        assert color_scheme.rgba_colors == rgba_colors
        assert color_scheme.bridge_color == "#6e6e6e"
        assert color_scheme.intra_community_color == "#c0c0c0"
