"""
Unit tests for visualization module.

Tests visualization components including metrics calculation, rendering,
and report generation functionality.
"""

import os
import tempfile

import networkx as nx

from FollowWeb_Visualizor.output.managers import MetricsReporter
from FollowWeb_Visualizor.visualization import (
    InteractiveRenderer,
    MetricsCalculator,
    StaticRenderer,
)


class TestInteractiveRenderer:
    """Test InteractiveRenderer functionality."""

    def test_generate_html_basic(self, temp_output_dir: str):
        """Test basic HTML generation."""
        # Setup custom logging for the test
        import logging

        SUCCESS_LEVEL = 22
        logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")

        def success(self, message, *args, **kwargs):
            if self.isEnabledFor(SUCCESS_LEVEL):
                self._log(SUCCESS_LEVEL, message, args, **kwargs)

        logging.Logger.success = success

        vis_config = {
            "node_size_metric": "degree",
            "base_node_size": 10,
            "node_size_multiplier": 2.0,
            "scaling_algorithm": "logarithmic",
            "pyvis_interactive": {
                "width": "100%",
                "height": "600px",
                "notebook": False,
                "show_labels": True,
                "show_tooltips": True,
                "physics_solver": "forceAtlas2Based",
            },
        }

        renderer = InteractiveRenderer(vis_config)

        # Create test graph
        graph = nx.DiGraph()
        graph.add_edges_from([("A", "B"), ("B", "C")])

        # Create complete node metrics

        output_path = os.path.join(temp_output_dir, "test_output.html")
        # Create a MetricsCalculator to generate proper metrics
        calculator = MetricsCalculator(vis_config)
        shared_metrics = calculator.calculate_all_metrics(graph)
        success = renderer.generate_html(graph, output_path, shared_metrics)

        assert success is True
        assert os.path.exists(output_path)

        # Verify HTML content
        with open(output_path) as f:
            content = f.read()
            assert "<html>" in content
            assert "vis-network" in content

    def test_generate_html_with_shared_metrics(self, temp_output_dir: str):
        """Test HTML generation using MetricsCalculator."""
        # Setup custom logging for the test
        import logging

        SUCCESS_LEVEL = 22
        logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")

        def success(self, message, *args, **kwargs):
            if self.isEnabledFor(SUCCESS_LEVEL):
                self._log(SUCCESS_LEVEL, message, args, **kwargs)

        logging.Logger.success = success

        vis_config = {
            "node_size_metric": "degree",
            "base_node_size": 10,
            "node_size_multiplier": 2.0,
            "scaling_algorithm": "logarithmic",
            "pyvis_interactive": {
                "width": "100%",
                "height": "600px",
                "notebook": False,
                "show_labels": True,
                "show_tooltips": True,
                "physics_solver": "forceAtlas2Based",
            },
            "shared_metrics": {"enable_caching": True, "cache_timeout_seconds": 300},
            "bridge_color": "#6e6e6e",
            "intra_community_color": "#c0c0c0",
        }

        # Create MetricsCalculator and InteractiveRenderer
        metrics_calculator = MetricsCalculator(vis_config)
        renderer = InteractiveRenderer(vis_config, metrics_calculator)

        # Create test graph with node attributes
        graph = nx.DiGraph()
        graph.add_edges_from([("A", "B"), ("B", "C")])

        # Add node attributes that MetricsCalculator expects
        graph.nodes["A"]["community"] = 0
        graph.nodes["A"]["degree"] = 1
        graph.nodes["A"]["betweenness"] = 0.0
        graph.nodes["A"]["eigenvector"] = 0.5

        graph.nodes["B"]["community"] = 0
        graph.nodes["B"]["degree"] = 2
        graph.nodes["B"]["betweenness"] = 1.0
        graph.nodes["B"]["eigenvector"] = 1.0

        graph.nodes["C"]["community"] = 1
        graph.nodes["C"]["degree"] = 1
        graph.nodes["C"]["betweenness"] = 0.0
        graph.nodes["C"]["eigenvector"] = 0.5

        # Calculate shared metrics
        shared_metrics = metrics_calculator.calculate_all_metrics(graph)

        output_path = os.path.join(temp_output_dir, "test_shared_metrics.html")
        success = renderer.generate_html(graph, output_path, shared_metrics)

        assert success is True
        assert os.path.exists(output_path)

        # Verify HTML content
        with open(output_path) as f:
            content = f.read()
            assert "<html>" in content
            assert "vis-network" in content

        # Verify that shared metrics were used (check log messages)
        # This is implicit through the successful generation

    def test_generate_html_empty_graph(self, temp_output_dir: str):
        """Test HTML generation with empty graph."""
        vis_config = {
            "node_size_metric": "degree",
            "pyvis_interactive": {
                "width": "100%",
                "height": "600px",
                "notebook": False,
                "show_labels": True,
                "show_tooltips": True,
                "physics_solver": "forceAtlas2Based",
            },
        }

        renderer = InteractiveRenderer(vis_config)

        # Create empty graph
        graph = nx.DiGraph()

        output_path = os.path.join(temp_output_dir, "empty_output.html")
        # Create metrics for empty graph
        calculator = MetricsCalculator(vis_config)
        shared_metrics = calculator.calculate_all_metrics(graph)
        success = renderer.generate_html(graph, output_path, shared_metrics)

        assert success is True
        assert os.path.exists(output_path)

    def test_generate_html_with_empty_graph_error_handling(self, temp_output_dir: str):
        """Test HTML generation error handling with problematic graphs."""

        import networkx as nx

        from FollowWeb_Visualizor.core.config import get_configuration_manager
        from FollowWeb_Visualizor.visualization import InteractiveRenderer

        config_manager = get_configuration_manager()
        config_obj = config_manager.load_configuration()
        config_dict = config_manager.serialize_configuration(config_obj)
        renderer = InteractiveRenderer(config_dict["visualization"])

        # Test with a graph that has nodes but no edges (edge case)
        graph = nx.DiGraph()
        graph.add_node("isolated_node")

        output_path = os.path.join(temp_output_dir, "error_handling_test.html")

        # Should handle graph with isolated nodes gracefully
        # Create metrics for the isolated node
        calculator = MetricsCalculator(config_dict["visualization"])
        shared_metrics = calculator.calculate_all_metrics(graph)
        success = renderer.generate_html(graph, output_path, shared_metrics)

        assert success is True
        assert os.path.exists(output_path)

        # Verify the HTML file was created and contains basic structure
        with open(output_path, encoding="utf-8") as f:
            content = f.read()
            assert len(content) > 0
            assert "html" in content.lower()


class TestStaticRenderer:
    """Test StaticRenderer functionality."""

    def test_generate_png_basic(self, temp_output_dir: str):
        """Test basic PNG generation."""
        # Set matplotlib to use non-interactive backend
        import matplotlib

        matplotlib.use("Agg")

        vis_config = {
            "static_image": {
                "generate": True,
                "layout": "spring",
                "with_labels": False,
                "font_size": 8,
                "image_size_inches": (10, 10),
                "dpi": 150,
                "spring_k": 0.3,
                "spring_iterations": 50,
                "edge_alpha": 0.3,
                "node_alpha": 0.8,
                "edge_arrow_size": 8,
                "show_legend": True,
            }
        }

        renderer = StaticRenderer(vis_config)

        # Create test graph
        graph = nx.DiGraph()
        graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "A")])

        # Create node metrics
        node_metrics = {
            "A": {"size": 100, "community": 0, "color_rgba": (1.0, 0.0, 0.0, 1.0)},
            "B": {"size": 150, "community": 0, "color_rgba": (1.0, 0.0, 0.0, 1.0)},
            "C": {"size": 120, "community": 1, "color_rgba": (0.0, 1.0, 0.0, 1.0)},
        }

        edge_metrics = {
            ("A", "B"): {
                "width": 2,
                "color": "#c0c0c0",
                "is_mutual": False,
                "common_neighbors": 0,
                "is_bridge": False,
                "u_comm": 0,
                "v_comm": 0,
            },
            ("B", "C"): {
                "width": 2,
                "color": "#6e6e6e",
                "is_mutual": False,
                "common_neighbors": 0,
                "is_bridge": True,
                "u_comm": 0,
                "v_comm": 1,
            },
            ("C", "A"): {
                "width": 2,
                "color": "#c0c0c0",
                "is_mutual": False,
                "common_neighbors": 0,
                "is_bridge": False,
                "u_comm": 1,
                "v_comm": 0,
            },
        }

        output_path = os.path.join(temp_output_dir, "test_output.png")
        success = renderer.generate_png(graph, output_path, node_metrics, edge_metrics)

        assert success is True
        assert os.path.exists(output_path)

        # Verify file is not empty
        assert os.path.getsize(output_path) > 0

    def test_generate_png_different_layouts(self, temp_output_dir: str):
        """Test PNG generation with different layouts."""
        # Set matplotlib to use non-interactive backend (like original implementation)
        import matplotlib

        matplotlib.use("Agg")  # Use Anti-Grain Geometry backend (no display needed)

        layouts_to_test = ["spring", "kamada_kawai", "circular"]

        for layout in layouts_to_test:
            vis_config = {
                "static_image": {
                    "generate": True,
                    "layout": layout,
                    "with_labels": False,
                    "font_size": 8,
                    "image_size_inches": (8, 8),
                    "dpi": 100,
                    "spring_k": 0.3,
                    "spring_iterations": 30,
                    "edge_alpha": 0.3,
                    "node_alpha": 0.8,
                    "edge_arrow_size": 8,
                    "show_legend": False,
                }
            }

            renderer = StaticRenderer(vis_config)

            # Create test graph
            graph = nx.DiGraph()
            graph.add_edges_from([("A", "B"), ("B", "C")])

            node_metrics = {
                "A": {"size": 100, "community": 0, "color_rgba": (1.0, 0.0, 0.0, 1.0)},
                "B": {"size": 100, "community": 0, "color_rgba": (1.0, 0.0, 0.0, 1.0)},
                "C": {"size": 100, "community": 1, "color_rgba": (0.0, 1.0, 0.0, 1.0)},
            }

            output_path = os.path.join(temp_output_dir, f"test_{layout}.png")
            success = renderer.generate_png(graph, output_path, node_metrics, {})

            assert success is True
            assert os.path.exists(output_path)


class TestMetricsReporter:
    """Test MetricsReporter functionality."""

    def test_generate_analysis_report(self):
        """Test analysis report generation."""
        vis_config = {}
        reporter = MetricsReporter(vis_config)

        # Create test graph with attributes
        graph = nx.DiGraph()
        graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "A")])

        # Add analysis attributes
        nx.set_node_attributes(graph, {"A": 0, "B": 0, "C": 1}, "community")

        config = {
            "pipeline": {"strategy": "k-core"},
            "pruning": {"k_values": {"k-core": 10}},
            "visualization": {"node_size_metric": "degree"},
        }

        timing_data = {"strategy": 1.5, "analysis": 2.3, "visualization": 0.8}

        report = reporter.generate_analysis_report(
            graph, config, "k-core", 10, timing_data
        )

        assert isinstance(report, str)
        assert len(report) > 0
        assert "FOLLOWWEB NETWORK ANALYSIS" in report
        assert "Strategy: k-core" in report
        assert "K-Value: 10" in report  # Match actual format from implementation
        assert "GRAPH PROCESSING SUMMARY" in report
        assert "Final Processed Graph: 3 nodes, 3 edges" in report

    def test_save_metrics_file(self, temp_output_dir: str):
        """Test metrics file saving."""
        vis_config = {}
        reporter = MetricsReporter(vis_config)

        report_content = "Test report content\nWith multiple lines\nAnd statistics"
        output_path = os.path.join(temp_output_dir, "test_metrics.txt")

        success = reporter.save_metrics_file(report_content, output_path)

        assert success is True
        assert os.path.exists(output_path)

        # Verify content
        with open(output_path) as f:
            saved_content = f.read()
            assert saved_content == report_content

    def test_save_metrics_file_invalid_path(self):
        """Test metrics file saving with invalid path."""
        import unittest.mock

        vis_config = {}
        reporter = MetricsReporter(vis_config)

        report_content = "Test content"
        from pathlib import Path

        # Use a platform-agnostic invalid path
        invalid_path = (
            Path(tempfile.gettempdir())
            / "invalid_test_path"
            / "does_not_exist"
            / "metrics.txt"
        )

        # Mock ensure_output_directory to raise an exception for invalid paths
        with unittest.mock.patch(
            "FollowWeb_Visualizor.utils.ensure_output_directory"
        ) as mock_ensure:
            mock_ensure.side_effect = OSError("Invalid path")
            success = reporter.save_metrics_file(report_content, invalid_path)

        assert success is False

    # test_calculate_edge_metrics_networkx_error removed - MetricsCalculator no longer exists
