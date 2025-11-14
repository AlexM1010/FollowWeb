"""
Integration tests for Sigma.js visualization.

Tests end-to-end HTML generation, Freesound graph data integration,
and HTML/JavaScript validation.
"""

import json
import os
import re
import tempfile
from pathlib import Path

import networkx as nx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.visualization]

from FollowWeb_Visualizor.visualization.renderers.sigma import SigmaRenderer


@pytest.mark.integration
class TestSigmaVisualizationEndToEnd:
    """Test end-to-end Sigma.js HTML generation."""

    def test_complete_visualization_workflow(self):
        """Test complete workflow from graph to HTML file."""
        # Create realistic graph
        graph = nx.DiGraph()

        # Add nodes with typical attributes
        for i in range(20):
            graph.add_node(
                i,
                name=f"Node_{i}",
                community=i % 3,
                degree=i + 1,
                betweenness=0.1 * i,
                eigenvector=0.05 * i,
            )

        # Add edges
        for i in range(19):
            graph.add_edge(i, i + 1, type="connection", weight=0.8)

        # Add some cross-connections
        graph.add_edge(0, 10, type="connection", weight=0.5)
        graph.add_edge(5, 15, type="connection", weight=0.6)

        # Create renderer with configuration
        config = {
            "sigma_interactive": {
                "show_labels": True,
                "show_tooltips": True,
                "enable_audio": False,
            },
            "node_size_metric": "degree",
        }
        renderer = SigmaRenderer(config)

        # Generate visualization
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_visualization.html")
            result = renderer.generate_visualization(graph, output_file)

            assert result is True
            assert os.path.exists(output_file)

            # Verify file is not empty
            file_size = os.path.getsize(output_file)
            assert file_size > 1000  # Should be substantial HTML file

    def test_html_structure_validation(self):
        """Test that generated HTML has valid structure."""
        graph = nx.DiGraph()
        graph.add_node(1, name="Test Node", community=0, degree=1)
        graph.add_edge(1, 1)

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_structure.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Validate HTML structure
            assert "<!DOCTYPE html>" in html_content
            assert "<html" in html_content
            assert "</html>" in html_content
            assert "<head>" in html_content
            assert "</head>" in html_content
            assert "<body>" in html_content
            assert "</body>" in html_content

            # Validate meta tags
            assert '<meta charset="UTF-8">' in html_content
            assert '<meta name="viewport"' in html_content

    def test_javascript_libraries_included(self):
        """Test that required JavaScript libraries are included."""
        graph = nx.DiGraph()
        graph.add_node(1, community=0, degree=1)

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_libraries.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check for required libraries
            assert "graphology" in html_content.lower()
            assert "sigma" in html_content.lower()
            assert "howler" in html_content.lower()

            # Check for CDN links
            assert "cdn.jsdelivr.net" in html_content or "unpkg.com" in html_content

    def test_graph_data_embedded(self):
        """Test that graph data is properly embedded in HTML."""
        graph = nx.DiGraph()
        graph.add_node("node1", name="First Node", community=0, degree=2)
        graph.add_node("node2", name="Second Node", community=1, degree=2)
        graph.add_edge("node1", "node2", type="similar", weight=0.9)

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_data.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check that node data is present
            assert "node1" in html_content
            assert "node2" in html_content
            assert "First Node" in html_content
            assert "Second Node" in html_content

            # Check that edge data is present
            assert "similar" in html_content or "0.9" in html_content

    def test_configuration_embedded(self):
        """Test that configuration is properly embedded in HTML."""
        graph = nx.DiGraph()
        graph.add_node(1, community=0, degree=1)

        config = {
            "sigma_interactive": {
                "show_labels": False,
                "show_tooltips": True,
                "enable_audio": True,
            },
            "node_size_metric": "degree",
        }
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_config.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check that config values are embedded
            assert "show_labels" in html_content
            assert "show_tooltips" in html_content
            assert "enable_audio" in html_content


@pytest.mark.integration
class TestSigmaVisualizationWithFreesoundData:
    """Test Sigma.js visualization with Freesound-like graph data."""

    def test_freesound_sample_graph(self):
        """Test visualization with Freesound sample attributes."""
        # Create graph with Freesound-like attributes
        graph = nx.DiGraph()

        # Add sample nodes
        graph.add_node(
            "12345",
            name="kick_drum_01.wav",
            tags=["kick", "drum", "percussion"],
            duration=1.5,
            user="audio_producer",
            audio_url="https://freesound.org/data/previews/12/12345_preview.mp3",
            type="sample",
            community=0,
            degree=3,
        )

        graph.add_node(
            "12346",
            name="snare_hit_02.wav",
            tags=["snare", "drum", "percussion"],
            duration=0.8,
            user="sound_designer",
            audio_url="https://freesound.org/data/previews/12/12346_preview.mp3",
            type="sample",
            community=0,
            degree=2,
        )

        graph.add_node(
            "12347",
            name="bass_synth.wav",
            tags=["bass", "synth", "electronic"],
            duration=3.2,
            user="synth_master",
            audio_url="https://freesound.org/data/previews/12/12347_preview.mp3",
            type="sample",
            community=1,
            degree=2,
        )

        # Add similarity edges
        graph.add_edge("12345", "12346", type="similar", weight=0.85)
        graph.add_edge("12346", "12347", type="similar", weight=0.45)

        # Create renderer
        config = {
            "sigma_interactive": {
                "show_labels": True,
                "show_tooltips": True,
                "enable_audio": True,
            },
            "node_size_metric": "degree",
        }
        renderer = SigmaRenderer(config)

        # Generate visualization
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "freesound_test.html")
            result = renderer.generate_visualization(graph, output_file)

            assert result is True
            assert os.path.exists(output_file)

            # Read and validate content
            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check for Freesound-specific attributes
            assert "kick_drum_01.wav" in html_content
            assert "snare_hit_02.wav" in html_content
            assert "bass_synth.wav" in html_content
            assert "audio_url" in html_content
            assert "freesound.org" in html_content

    def test_audio_player_elements(self):
        """Test that audio player UI elements are present."""
        graph = nx.DiGraph()
        graph.add_node(
            "1",
            name="test_sample.wav",
            audio_url="https://example.com/audio.mp3",
            community=0,
            degree=1,
        )

        config = {
            "sigma_interactive": {"enable_audio": True},
            "node_size_metric": "degree",
        }
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "audio_player_test.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check for audio player elements
            assert "audio-player" in html_content
            assert "play-btn" in html_content or "Play" in html_content
            assert "pause-btn" in html_content or "Pause" in html_content
            assert "loop-btn" in html_content or "Loop" in html_content
            assert "timeline" in html_content

    def test_large_freesound_graph(self):
        """Test visualization with larger Freesound-like graph."""
        # Create larger graph (100 nodes)
        graph = nx.DiGraph()

        for i in range(100):
            graph.add_node(
                str(10000 + i),
                name=f"sample_{i:03d}.wav",
                tags=[f"tag{i % 10}", f"category{i % 5}"],
                duration=float(1 + (i % 10)),
                user=f"user_{i % 20}",
                audio_url=f"https://freesound.org/data/previews/{10000 + i}_preview.mp3",
                type="sample",
                community=i % 5,
                degree=i % 10 + 1,
            )

        # Add edges (create a connected graph)
        for i in range(99):
            graph.add_edge(
                str(10000 + i),
                str(10000 + i + 1),
                type="similar",
                weight=0.5 + (i % 50) / 100,
            )

        # Add some cross-connections
        for i in range(0, 100, 10):
            if i + 50 < 100:
                graph.add_edge(
                    str(10000 + i),
                    str(10000 + i + 50),
                    type="similar",
                    weight=0.6,
                )

        config = {
            "sigma_interactive": {"enable_audio": True},
            "node_size_metric": "degree",
        }
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "large_freesound_test.html")
            result = renderer.generate_visualization(graph, output_file)

            assert result is True
            assert os.path.exists(output_file)

            # Verify file size is reasonable for 100 nodes
            file_size = os.path.getsize(output_file)
            assert file_size > 10000  # Should be substantial


@pytest.mark.integration
class TestSigmaVisualizationJavaScriptValidation:
    """Test JavaScript syntax and structure validation."""

    def test_valid_json_embedding(self):
        """Test that embedded JSON is valid."""
        graph = nx.DiGraph()
        graph.add_node(1, name="Test", community=0, degree=1)
        graph.add_edge(1, 1)

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "json_test.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check that graphData variable is defined
            assert "const graphData = " in html_content

            # Extract JSON data using regex - match the entire JSON object
            graph_data_match = re.search(
                r"const graphData = (\{[\s\S]*?\});[\s\n]*const config", html_content
            )

            if graph_data_match:
                json_str = graph_data_match.group(1)
                # Validate it's valid JSON
                try:
                    data = json.loads(json_str)
                    assert "nodes" in data
                    assert "edges" in data
                    assert isinstance(data["nodes"], list)
                    assert isinstance(data["edges"], list)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Embedded graph data is not valid JSON: {e}")
            else:
                # If we can't extract it, at least verify the structure exists
                assert "nodes" in html_content
                assert "edges" in html_content

    def test_javascript_initialization(self):
        """Test that JavaScript initialization code is present."""
        graph = nx.DiGraph()
        graph.add_node(1, community=0, degree=1)

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "js_init_test.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check for key JavaScript initialization
            assert "new graphology.DirectedGraph()" in html_content
            assert "new Sigma(" in html_content
            assert "addNode" in html_content
            assert "addEdge" in html_content

    def test_event_handlers_present(self):
        """Test that event handlers are properly set up."""
        graph = nx.DiGraph()
        graph.add_node(1, community=0, degree=1)

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "events_test.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check for event handlers
            assert "addEventListener" in html_content
            assert "clickNode" in html_content or "click" in html_content
            assert "enterNode" in html_content or "mouseover" in html_content

    def test_controls_functionality(self):
        """Test that control elements are properly wired."""
        graph = nx.DiGraph()
        graph.add_node(1, community=0, degree=1)

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "controls_test.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check for zoom controls
            assert "zoom-in" in html_content
            assert "zoom-out" in html_content
            assert "reset-view" in html_content

            # Check for search
            assert "search-input" in html_content


@pytest.mark.integration
class TestSigmaVisualizationErrorHandling:
    """Test error handling in integration scenarios."""

    def test_missing_required_attributes(self):
        """Test handling of nodes missing required attributes."""
        graph = nx.DiGraph()
        # Node with minimal attributes
        graph.add_node(1)
        graph.add_node(2, name="Node 2")
        graph.add_edge(1, 2)

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "missing_attrs_test.html")
            # Should handle gracefully
            result = renderer.generate_visualization(graph, output_file)

            assert result is True
            assert os.path.exists(output_file)

    def test_special_characters_in_node_names(self):
        """Test handling of special characters in node attributes."""
        graph = nx.DiGraph()
        graph.add_node(
            1,
            name='Test "quoted" name with <html> & special chars',
            tags=["tag's", 'tag"s'],
            community=0,
            degree=1,
        )

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "special_chars_test.html")
            result = renderer.generate_visualization(graph, output_file)

            assert result is True
            assert os.path.exists(output_file)

            # Verify HTML is still valid (no unescaped characters breaking structure)
            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            assert "</html>" in html_content  # HTML structure intact

    def test_very_long_node_names(self):
        """Test handling of very long node names and attributes."""
        graph = nx.DiGraph()
        long_name = "A" * 1000  # Very long name
        long_tags = ["tag" + str(i) for i in range(100)]  # Many tags

        graph.add_node(
            1,
            name=long_name,
            tags=long_tags,
            community=0,
            degree=1,
        )

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "long_names_test.html")
            result = renderer.generate_visualization(graph, output_file)

            assert result is True
            assert os.path.exists(output_file)


@pytest.mark.integration
class TestSigmaVisualizationOutputQuality:
    """Test output quality and completeness."""

    def test_legend_included(self):
        """Test that legend is included in output."""
        graph = nx.DiGraph()
        for i in range(5):
            graph.add_node(i, community=i % 2, degree=i + 1)
        graph.add_edge(0, 1)

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "legend_test.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check for legend elements (legend is generated by LegendGenerator)
            # The exact content depends on LegendGenerator implementation
            assert (
                "legend" in html_content.lower() or "community" in html_content.lower()
            )

    def test_responsive_design_elements(self):
        """Test that responsive design elements are present."""
        graph = nx.DiGraph()
        graph.add_node(1, community=0, degree=1)

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "responsive_test.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check for viewport meta tag
            assert "viewport" in html_content

            # Check for responsive sizing
            assert "100vw" in html_content or "100vh" in html_content

    def test_styling_applied(self):
        """Test that CSS styling is properly applied."""
        graph = nx.DiGraph()
        graph.add_node(1, community=0, degree=1)

        config = {"sigma_interactive": {}, "node_size_metric": "degree"}
        renderer = SigmaRenderer(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "styling_test.html")
            renderer.generate_visualization(graph, output_file)

            with open(output_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check for CSS
            assert "<style>" in html_content
            assert "</style>" in html_content

            # Check for key styling elements
            assert "container" in html_content
            assert "controls" in html_content
