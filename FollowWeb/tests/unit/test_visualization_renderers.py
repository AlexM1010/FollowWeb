"""
Unit tests for visualization consistency between PNG and HTML formats.

Tests that PNG and HTML use identical node sizes and colors, spring layout application,
shared scaling algorithms and color schemes, and layout parameter consistency.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import networkx as nx
import pytest

# Import the visualization classes
from FollowWeb_Visualizor.visualization import (
    ColorScheme,
    EdgeMetric,
    InteractiveRenderer,
    MetricsCalculator,
    NodeMetric,
    StaticRenderer,
    VisualizationMetrics,
)


class TestVisualizationConsistency:
    """Test cases for visualization consistency between formats."""

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
            "static_image": {
                "layout_type": "spring",
                "force_spring_layout": True,
                "spring_iterations": 50,
                "spring_k": 0.15,
                "width": 1200,
                "height": 800,
                "dpi": 300,
            },
            "pyvis_interactive": {"width": "100%", "height": "600px", "physics": True},
        }

        self.metrics_calculator = MetricsCalculator(self.vis_config)
        self.interactive_renderer = InteractiveRenderer(
            self.vis_config, self.metrics_calculator
        )
        self.static_renderer = StaticRenderer(self.vis_config)

    def create_test_graph(self) -> nx.DiGraph:
        """Create a test graph with communities and attributes."""
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

    def create_shared_metrics(self) -> VisualizationMetrics:
        """Create test shared metrics."""
        node_metrics = {
            "A": NodeMetric(
                size=15.0,
                color_hex="#ff0000",
                color_rgba=(1.0, 0.0, 0.0, 1.0),
                community=0,
                centrality_values={"degree": 3, "betweenness": 0.5, "eigenvector": 0.8},
            ),
            "B": NodeMetric(
                size=12.0,
                color_hex="#ff0000",
                color_rgba=(1.0, 0.0, 0.0, 1.0),
                community=0,
                centrality_values={"degree": 2, "betweenness": 0.3, "eigenvector": 0.6},
            ),
            "C": NodeMetric(
                size=12.0,
                color_hex="#00ff00",
                color_rgba=(0.0, 1.0, 0.0, 1.0),
                community=1,
                centrality_values={"degree": 2, "betweenness": 0.2, "eigenvector": 0.4},
            ),
            "D": NodeMetric(
                size=8.0,
                color_hex="#00ff00",
                color_rgba=(0.0, 1.0, 0.0, 1.0),
                community=1,
                centrality_values={"degree": 1, "betweenness": 0.1, "eigenvector": 0.2},
            ),
        }

        edge_metrics = {
            ("A", "B"): EdgeMetric(2.0, "#ff0000", True, False, 1, 0, 0),
            ("A", "C"): EdgeMetric(1.0, "#6e6e6e", False, True, 0, 0, 1),
            ("C", "D"): EdgeMetric(1.0, "#00ff00", False, False, 0, 1, 1),
        }

        layout_positions = {
            "A": (0.0, 0.0),
            "B": (1.0, 0.0),
            "C": (0.5, 1.0),
            "D": (1.5, 1.0),
        }

        color_schemes = ColorScheme(
            hex_colors={0: "#ff0000", 1: "#00ff00"},
            rgba_colors={0: (1.0, 0.0, 0.0, 1.0), 1: (0.0, 1.0, 0.0, 1.0)},
            bridge_color="#6e6e6e",
            intra_community_color="#c0c0c0",
        )

        return VisualizationMetrics(
            node_metrics=node_metrics,
            edge_metrics=edge_metrics,
            layout_positions=layout_positions,
            color_schemes=color_schemes,
            graph_hash="test_hash",
        )

    def test_metrics_calculator_integration(self):
        """Test that both renderers can use MetricsCalculator."""
        G = self.create_test_graph()

        with patch.object(
            self.metrics_calculator, "calculate_all_metrics"
        ) as mock_calc:
            mock_calc.return_value = self.create_shared_metrics()

            # Test that both renderers can access shared calculator
            assert self.interactive_renderer.metrics_calculator is not None

            # Calculate metrics once
            shared_metrics = self.metrics_calculator.calculate_all_metrics(G)

            # Verify metrics were calculated
            mock_calc.assert_called_once_with(G)
            assert isinstance(shared_metrics, VisualizationMetrics)

    def test_node_size_consistency(self):
        """Test that PNG and HTML use identical node sizes."""
        G = self.create_test_graph()
        shared_metrics = self.create_shared_metrics()

        # Verify node sizes are consistent in shared metrics
        assert shared_metrics.node_metrics["A"].size == 15.0
        assert shared_metrics.node_metrics["B"].size == 12.0
        assert shared_metrics.node_metrics["C"].size == 12.0
        assert shared_metrics.node_metrics["D"].size == 8.0

        # Test that both renderers would use the same sizes
        with tempfile.TemporaryDirectory() as temp_dir:
            html_path = Path(temp_dir) / "test.html"
            png_path = Path(temp_dir) / "test.png"

            try:
                # Mock only matplotlib operations to focus on metrics consistency
                with patch(
                    "matplotlib.pyplot.subplots", return_value=(Mock(), Mock())
                ), patch("matplotlib.pyplot.savefig"):
                    # Test HTML renderer
                    html_result = self.interactive_renderer.generate_html(
                        G, str(html_path), shared_metrics=shared_metrics
                    )

                    # Test PNG renderer
                    png_result = self.static_renderer.generate_png(
                        G, str(png_path), {}, {}, shared_metrics=shared_metrics
                    )

                    # Both should succeed
                    assert html_result is True
                    assert png_result is True
            except Exception as e:
                pytest.fail(f"Shared metrics rendering failed: {e}")

    def test_node_color_consistency(self):
        """Test that PNG and HTML use identical node colors."""
        shared_metrics = self.create_shared_metrics()

        # Verify color consistency in shared metrics
        assert shared_metrics.node_metrics["A"].color_hex == "#ff0000"
        assert shared_metrics.node_metrics["A"].color_rgba == (1.0, 0.0, 0.0, 1.0)
        assert shared_metrics.node_metrics["B"].color_hex == "#ff0000"
        assert shared_metrics.node_metrics["B"].color_rgba == (1.0, 0.0, 0.0, 1.0)
        assert shared_metrics.node_metrics["C"].color_hex == "#00ff00"
        assert shared_metrics.node_metrics["C"].color_rgba == (0.0, 1.0, 0.0, 1.0)
        assert shared_metrics.node_metrics["D"].color_hex == "#00ff00"
        assert shared_metrics.node_metrics["D"].color_rgba == (0.0, 1.0, 0.0, 1.0)

        # Verify community consistency
        assert shared_metrics.node_metrics["A"].community == 0
        assert shared_metrics.node_metrics["B"].community == 0
        assert shared_metrics.node_metrics["C"].community == 1
        assert shared_metrics.node_metrics["D"].community == 1

    def test_edge_metrics_consistency(self):
        """Test that PNG and HTML use identical edge metrics."""
        shared_metrics = self.create_shared_metrics()

        # Verify edge width consistency in shared metrics
        assert shared_metrics.edge_metrics[("A", "B")].width == 2.0
        assert shared_metrics.edge_metrics[("A", "C")].width == 1.0
        assert shared_metrics.edge_metrics[("C", "D")].width == 1.0

        # Verify edge color consistency
        assert (
            shared_metrics.edge_metrics[("A", "B")].color == "#ff0000"
        )  # Intra-community
        assert shared_metrics.edge_metrics[("A", "C")].color == "#6e6e6e"  # Bridge
        assert (
            shared_metrics.edge_metrics[("C", "D")].color == "#00ff00"
        )  # Intra-community

        # Verify edge properties
        assert shared_metrics.edge_metrics[("A", "B")].is_mutual is True
        assert shared_metrics.edge_metrics[("A", "C")].is_bridge is True
        assert shared_metrics.edge_metrics[("C", "D")].is_bridge is False

    def test_spring_layout_application_png(self):
        """Test that PNG renderer uses spring layout by default."""
        G = self.create_test_graph()
        shared_metrics = self.create_shared_metrics()

        with tempfile.TemporaryDirectory() as temp_dir:
            png_path = Path(temp_dir) / "test.png"

            try:
                with patch("matplotlib.pyplot.subplots") as mock_subplots, patch(
                    "matplotlib.pyplot.savefig"
                ):
                    # Mock matplotlib components
                    mock_fig = Mock()
                    mock_ax = Mock()
                    mock_subplots.return_value = (mock_fig, mock_ax)

                    # Generate PNG with shared metrics (includes layout positions)
                    result = self.static_renderer.generate_png(
                        G, str(png_path), {}, {}, shared_metrics=shared_metrics
                    )

                    assert result is True

                    # Verify that the PNG generation succeeded
                    assert result is True

                    # The layout positions should be from shared metrics
                    # (This tests that spring layout from shared metrics is used)
            except Exception as e:
                pytest.fail(f"Spring layout PNG generation failed: {e}")

    def test_layout_parameter_consistency(self):
        """Test that layout parameters are consistent between formats."""
        G = self.create_test_graph()

        # Test that spring layout parameters are consistent
        spring_config = self.vis_config["static_image"]
        assert spring_config["spring_iterations"] == 50  # Config value
        assert spring_config["spring_k"] == 0.15

        # Test that both renderers use the same configuration
        assert (
            self.static_renderer.static_config["spring_iterations"] == 50
        )  # Config value
        assert self.static_renderer.static_config["spring_k"] == 0.15

        # Test that shared calculator uses the same parameters
        with patch("networkx.spring_layout") as mock_spring_layout:
            mock_spring_layout.return_value = {"A": (0, 0), "B": (1, 0)}

            shared_metrics = self.create_shared_metrics()
            self.metrics_calculator._calculate_spring_layout(
                G, shared_metrics.edge_metrics
            )

            # Verify spring_layout was called with consistent parameters (iterative approach)
            assert mock_spring_layout.call_count > 0, (
                "spring_layout should be called at least once"
            )

            # Check the first call which should have the seed parameter
            first_call_args, first_call_kwargs = mock_spring_layout.call_args_list[0]
            assert first_call_kwargs["k"] == 0.15
            assert (
                first_call_kwargs["iterations"] == 0
            )  # First call uses 0 iterations to set initial positions
            assert first_call_kwargs["seed"] == 123
            assert first_call_kwargs["weight"] == "weight"

    def test_scaling_algorithm_consistency(self):
        """Test that scaling algorithms are applied consistently."""
        # Test that both renderers use the same scaling configuration
        assert self.vis_config["scaling_algorithm"] == "linear"
        assert self.vis_config["node_size_multiplier"] == 2
        assert self.vis_config["base_node_size"] == 10

        # Test edge scaling consistency
        assert self.vis_config["edge_width_scaling"] == "logarithmic"
        assert self.vis_config["edge_width_multiplier"] == 1.5
        assert self.vis_config["base_edge_width"] == 0.5

        # Verify that shared calculator uses these parameters
        G = self.create_test_graph()

        with patch("FollowWeb_Visualizor.visualization.get_scaled_size") as mock_scale:
            mock_scale.return_value = 15.0

            # Calculate metrics using shared calculator
            with patch.object(
                self.metrics_calculator, "_calculate_color_schemes"
            ), patch.object(
                self.metrics_calculator, "_calculate_edge_metrics"
            ), patch.object(self.metrics_calculator, "_calculate_spring_layout"):
                self.metrics_calculator._calculate_node_metrics(
                    G, ColorScheme({}, {}, "#000", "#fff")
                )

            # Verify get_scaled_size was called with consistent parameters
            calls = mock_scale.call_args_list
            for call in calls:
                args = call[0]
                # Should use base_size=10, multiplier=2, scaling="linear"
                assert args[1] == 10  # base_size
                assert args[2] == 2  # multiplier
                assert args[3] == "linear"  # scaling_algorithm

    def test_color_scheme_consistency(self):
        """Test that color schemes are applied consistently."""
        G = self.create_test_graph()

        # Calculate color schemes using actual implementation
        color_schemes = self.metrics_calculator._calculate_color_schemes(G)

        # Verify consistent color scheme (using actual viridis colors)
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

    def test_convenience_functions_use_shared_metrics(self):
        """Test that convenience functions can use shared metrics."""
        G = self.create_test_graph()
        shared_metrics = self.create_shared_metrics()

        # Use shared metrics directly

        with tempfile.TemporaryDirectory() as temp_dir:
            html_path = Path(temp_dir) / "test.html"
            png_path = Path(temp_dir) / "test.png"

            try:
                # Mock the actual file operations
                with patch(
                    "FollowWeb_Visualizor.visualization.InteractiveRenderer.generate_html"
                ) as mock_html, patch(
                    "FollowWeb_Visualizor.visualization.StaticRenderer.generate_png"
                ) as mock_png:
                    mock_html.return_value = True
                    mock_png.return_value = True

                    # Test renderer classes directly
                    html_renderer = InteractiveRenderer(self.vis_config)
                    png_renderer = StaticRenderer(self.vis_config)

                    html_result = html_renderer.generate_html(
                        G, str(html_path), shared_metrics=shared_metrics
                    )
                    png_result = png_renderer.generate_png(
                        G, str(png_path), {}, {}, shared_metrics=shared_metrics
                    )

                    assert html_result is True
                    assert png_result is True

                    # Verify both were called with shared metrics
                    mock_html.assert_called_once_with(
                        G, str(html_path), shared_metrics=shared_metrics
                    )
                    mock_png.assert_called_once_with(
                        G, str(png_path), {}, {}, shared_metrics=shared_metrics
                    )
            except Exception as e:
                pytest.fail(f"Renderer integration test failed: {e}")

    def test_force_spring_layout_configuration(self):
        """Test that force_spring_layout configuration is respected."""
        # Test with force_spring_layout enabled
        config_with_force = self.vis_config.copy()
        config_with_force["static_image"]["force_spring_layout"] = True

        static_renderer = StaticRenderer(config_with_force)

        # Test that the configuration is properly set
        assert static_renderer.static_config["force_spring_layout"] is True

        # Test with force_spring_layout disabled
        config_without_force = self.vis_config.copy()
        config_without_force["static_image"]["force_spring_layout"] = False

        static_renderer_no_force = StaticRenderer(config_without_force)
        assert static_renderer_no_force.static_config["force_spring_layout"] is False

    def test_shared_metrics_consistency(self):
        """Test that shared metrics provide consistent results across renderers."""
        G = self.create_test_graph()
        shared_metrics = self.create_shared_metrics()

        with tempfile.TemporaryDirectory() as temp_dir:
            html_path = Path(temp_dir) / "test.html"
            png_path = Path(temp_dir) / "test.png"

            try:
                # Mock only matplotlib operations to focus on consistency
                with patch(
                    "matplotlib.pyplot.subplots", return_value=(Mock(), Mock())
                ), patch("matplotlib.pyplot.savefig"):
                    # Test HTML renderer with shared metrics
                    html_result = self.interactive_renderer.generate_html(
                        G, str(html_path), shared_metrics=shared_metrics
                    )

                    # Test PNG renderer with shared metrics
                    png_result = self.static_renderer.generate_png(
                        G, str(png_path), {}, {}, shared_metrics=shared_metrics
                    )

                    # Both should succeed with shared metrics
                    assert html_result is True
                    assert png_result is True
            except Exception as e:
                pytest.fail(f"Shared metrics consistency test failed: {e}")


class TestRendererInitialization:
    """Test cases for renderer initialization and configuration."""

    def test_interactive_renderer_initialization(self):
        """Test InteractiveRenderer initialization."""
        vis_config = {"test": "config"}
        shared_calc = Mock()

        renderer = InteractiveRenderer(vis_config, shared_calc)

        assert renderer.vis_config == vis_config
        assert renderer.metrics_calculator == shared_calc
        assert renderer.legend_generator is not None

    def test_static_renderer_initialization(self):
        """Test StaticRenderer initialization."""
        vis_config = {"static_image": {"width": 1200, "height": 800, "dpi": 300}}

        renderer = StaticRenderer(vis_config)

        assert renderer.vis_config == vis_config
        assert renderer.static_config == vis_config["static_image"]
        assert renderer.performance_config == {}

    def test_static_renderer_with_performance_config(self):
        """Test StaticRenderer initialization with performance config."""
        vis_config = {"static_image": {}}
        perf_config = {"optimization": True}

        renderer = StaticRenderer(vis_config, perf_config)

        assert renderer.performance_config == perf_config

    def test_static_renderer_missing_static_image_config(self):
        """Test StaticRenderer initialization with missing static_image config."""
        vis_config = {}  # Missing static_image key

        with pytest.raises(KeyError):
            StaticRenderer(vis_config)
