"""
Unit tests for SigmaRenderer.

Tests Sigma.js HTML generation, data format conversion, and configuration handling.
"""

import json
import os
import tempfile
from pathlib import Path

import networkx as nx
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.visualization]

from FollowWeb_Visualizor.visualization.renderers.sigma import SigmaRenderer


class TestSigmaRendererBasics:
    """Test SigmaRenderer basic functionality."""

    def test_sigma_renderer_instantiation(self):
        """Test that SigmaRenderer can be instantiated."""
        config = {"sigma_interactive": {"show_labels": True}}
        renderer = SigmaRenderer(config)

        assert renderer is not None
        assert hasattr(renderer, "generate_visualization")
        assert hasattr(renderer, "jinja_env")

    def test_sigma_renderer_file_extension(self):
        """Test that SigmaRenderer returns correct file extension."""
        renderer = SigmaRenderer({})

        extension = renderer.get_file_extension()

        assert extension == ".html"

    def test_sigma_renderer_supports_large_graphs(self):
        """Test that SigmaRenderer supports large graphs."""
        renderer = SigmaRenderer({})

        supports = renderer.supports_large_graphs()

        assert supports is True


class TestSigmaRendererDataConversion:
    """Test SigmaRenderer data format conversion."""

    def test_convert_simple_graph(self):
        """Test conversion of simple graph to Sigma format."""
        config = {"sigma_interactive": {}}
        renderer = SigmaRenderer(config)

        graph = nx.DiGraph()
        graph.add_node(1, name="Node 1")
        graph.add_node(2, name="Node 2")
        graph.add_edge(1, 2, type="similar", weight=0.8)

        # Create minimal metrics
        node_metrics = {
            1: {"size": 10, "color_hex": "#ff0000", "community": 0, "degree": 1, "betweenness": 0.0, "eigenvector": 0.5},
            2: {"size": 10, "color_hex": "#00ff00", "community": 0, "degree": 1, "betweenness": 0.0, "eigenvector": 0.5},
        }
        edge_metrics = {
            (1, 2): {"width": 2, "color": "#cccccc", "is_mutual": False}
        }

        # Create mock metrics object
        from FollowWeb_Visualizor.core.types import VisualizationMetrics, ColorScheme
        metrics = VisualizationMetrics(
            node_metrics={},
            edge_metrics={},
            layout_positions={1: (0, 0), 2: (1, 1)},
            color_schemes=ColorScheme({}, {}, "#6e6e6e", "#c0c0c0"),
            graph_hash="test_hash"
        )

        sigma_data = renderer._convert_to_sigma_format(graph, node_metrics, edge_metrics, metrics)

        assert "nodes" in sigma_data
        assert "edges" in sigma_data
        assert len(sigma_data["nodes"]) == 2
        assert len(sigma_data["edges"]) == 1

    def test_convert_node_attributes(self):
        """Test that node attributes are correctly converted."""
        config = {"sigma_interactive": {}}
        renderer = SigmaRenderer(config)

        graph = nx.DiGraph()
        graph.add_node(1, name="Sample 1", tags=["tag1", "tag2"], duration=5.5, user="testuser", audio_url="http://example.com/audio.mp3")

        node_metrics = {
            1: {"size": 15, "color_hex": "#ff0000", "community": 1, "degree": 5, "betweenness": 0.2, "eigenvector": 0.8}
        }
        edge_metrics = {}

        from FollowWeb_Visualizor.core.types import VisualizationMetrics, ColorScheme
        metrics = VisualizationMetrics(
            node_metrics={},
            edge_metrics={},
            layout_positions={1: (10, 20)},
            color_schemes=ColorScheme({}, {}, "#6e6e6e", "#c0c0c0"),
            graph_hash="test_hash"
        )

        sigma_data = renderer._convert_to_sigma_format(graph, node_metrics, edge_metrics, metrics)

        node = sigma_data["nodes"][0]
        assert node["key"] == "1"
        assert node["attributes"]["name"] == "Sample 1"
        assert node["attributes"]["tags"] == ["tag1", "tag2"]
        assert node["attributes"]["duration"] == 5.5
        assert node["attributes"]["user"] == "testuser"
        assert node["attributes"]["audio_url"] == "http://example.com/audio.mp3"
        assert node["attributes"]["x"] == 10.0
        assert node["attributes"]["y"] == 20.0
        assert node["attributes"]["size"] == 15.0
        assert node["attributes"]["color"] == "#ff0000"

    def test_convert_edge_attributes(self):
        """Test that edge attributes are correctly converted."""
        config = {"sigma_interactive": {}}
        renderer = SigmaRenderer(config)

        graph = nx.DiGraph()
        graph.add_node(1)
        graph.add_node(2)
        graph.add_edge(1, 2, type="similar", weight=0.9)

        node_metrics = {
            1: {"size": 10, "color_hex": "#ff0000", "community": 0, "degree": 1, "betweenness": 0.0, "eigenvector": 0.5},
            2: {"size": 10, "color_hex": "#00ff00", "community": 0, "degree": 1, "betweenness": 0.0, "eigenvector": 0.5},
        }
        edge_metrics = {
            (1, 2): {"width": 3, "color": "#0000ff", "is_mutual": False}
        }

        from FollowWeb_Visualizor.core.types import VisualizationMetrics, ColorScheme
        metrics = VisualizationMetrics(
            node_metrics={},
            edge_metrics={},
            layout_positions={1: (0, 0), 2: (1, 1)},
            color_schemes=ColorScheme({}, {}, "#6e6e6e", "#c0c0c0"),
            graph_hash="test_hash"
        )

        sigma_data = renderer._convert_to_sigma_format(graph, node_metrics, edge_metrics, metrics)

        edge = sigma_data["edges"][0]
        assert edge["source"] == "1"
        assert edge["target"] == "2"
        assert edge["attributes"]["size"] == 3.0
        assert edge["attributes"]["color"] == "#0000ff"
        assert edge["attributes"]["type"] == "arrow"
        assert edge["attributes"]["edge_type"] == "similar"
        assert edge["attributes"]["weight"] == 0.9


class TestSigmaRendererHTMLGeneration:
    """Test SigmaRenderer HTML generation."""

    def test_generate_html_file(self):
        """Test that HTML file is generated."""
        config = {
            "sigma_interactive": {"show_labels": True, "show_tooltips": True},
            "node_size_metric": "degree"
        }
        renderer = SigmaRenderer(config)

        graph = nx.DiGraph()
        graph.add_node(1, name="Node 1", community=0, degree=2)
        graph.add_node(2, name="Node 2", community=0, degree=2)
        graph.add_edge(1, 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_sigma.html")
            result = renderer.generate_visualization(graph, output_file)

            assert result is True
            assert os.path.exists(output_file)

    def test_html_contains_sigma_js(self):
        """Test that generated HTML contains Sigma.js references."""
        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        graph = nx.DiGraph()
        graph.add_node(1, community=0, degree=1)
        graph.add_edge(1, 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_sigma.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            assert "sigma" in html_content.lower()
            assert "graphology" in html_content.lower()
            assert "howler" in html_content.lower()

    def test_html_contains_graph_data(self):
        """Test that generated HTML contains graph data."""
        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        graph = nx.DiGraph()
        graph.add_node("test_node", name="Test Node", community=0, degree=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_sigma.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            assert "test_node" in html_content
            assert "Test Node" in html_content

    def test_empty_graph_handling(self):
        """Test handling of empty graph."""
        config = {"sigma_interactive": {}}
        renderer = SigmaRenderer(config)

        graph = nx.DiGraph()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "empty_sigma.html")
            result = renderer.generate_visualization(graph, output_file)

            # Should return False for empty graph
            assert result is False


class TestSigmaRendererConfiguration:
    """Test SigmaRenderer configuration handling."""

    def test_default_configuration(self):
        """Test renderer with default configuration."""
        renderer = SigmaRenderer({})

        assert renderer.vis_config == {}

    def test_custom_configuration(self):
        """Test renderer with custom configuration."""
        config = {
            "sigma_interactive": {
                "show_labels": False,
                "show_tooltips": True,
                "enable_audio": True,
            }
        }
        renderer = SigmaRenderer(config)

        assert renderer.vis_config["sigma_interactive"]["show_labels"] is False
        assert renderer.vis_config["sigma_interactive"]["enable_audio"] is True

    def test_configuration_passed_to_template(self):
        """Test that configuration is passed to template."""
        config = {
            "sigma_interactive": {"show_labels": False},
            "node_size_metric": "degree"
        }
        renderer = SigmaRenderer(config)

        graph = nx.DiGraph()
        graph.add_node(1, community=0, degree=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_sigma.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check that config is embedded in HTML
            assert "show_labels" in html_content


class TestSigmaRendererErrorHandling:
    """Test SigmaRenderer error handling."""

    def test_invalid_output_path(self):
        """Test handling of invalid output path."""
        renderer = SigmaRenderer({})
        graph = nx.DiGraph()
        graph.add_node(1)

        # Try to write to invalid path
        result = renderer.generate_visualization(graph, "/invalid/path/output.html")

        # Should handle error gracefully
        assert result is False

    def test_missing_node_attributes(self):
        """Test handling of missing node attributes."""
        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        # Graph with minimal attributes
        graph = nx.DiGraph()
        graph.add_node(1)  # No name, tags, etc.
        graph.add_node(2, community=0, degree=1)
        graph.add_edge(1, 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_sigma.html")
            result = renderer.generate_visualization(graph, output_file)

            # Should handle missing attributes gracefully
            assert result is True
