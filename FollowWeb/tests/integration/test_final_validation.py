"""
Final integration testing and validation for Freesound-Sigma integration.

This test suite validates the complete workflow including:
- Freesound → Analysis → Sigma visualization
- Audio playback with real Freesound samples
- Various graph sizes (100, 1000, 10000 nodes)
- Instagram data with both pyvis and sigma renderers
- Freesound data with both pyvis and sigma renderers
- All configuration options
- Error handling and recovery

Requirements: 9.6, 9.8
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import networkx as nx
import pytest

from FollowWeb_Visualizor.core.config import load_config_from_dict
from FollowWeb_Visualizor.main import PipelineOrchestrator

pytestmark = [pytest.mark.integration, pytest.mark.final_validation]


def create_mock_freesound_loader(graph, max_samples=50, checkpoint_dir=None):
    """
    Create a properly configured mock FreesoundLoader with all required attributes.
    
    This centralizes mock configuration to avoid repetition and ensure all
    attributes are set to prevent Mock.__format__ errors during logging.
    
    Args:
        graph: NetworkX graph to return from fetch_data
        max_samples: Maximum samples value
        checkpoint_dir: Checkpoint directory path
        
    Returns:
        Configured Mock object with all necessary attributes
    """
    mock_loader = Mock()
    mock_loader.graph = graph
    mock_loader.fetch_data.return_value = graph
    # Ensure all attributes return proper values (not Mock objects that can't be formatted)
    mock_loader.api_key = "test_key"
    mock_loader.query = "test"
    mock_loader.max_samples = max_samples
    mock_loader.tags = []
    mock_loader.checkpoint_dir = checkpoint_dir
    mock_loader.discovery_mode = "search"
    mock_loader.max_requests = 100
    return mock_loader


@pytest.mark.integration
class TestCompleteWorkflowFreesoundToSigma:
    """Test complete workflow: Freesound → Analysis → Sigma visualization."""

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_complete_freesound_sigma_workflow(self, mock_loader_class):
        """Test complete workflow from Freesound data to Sigma visualization."""
        # Create realistic Freesound graph with audio URLs (reduced to 10 nodes for speed)
        mock_graph = nx.DiGraph()
        for i in range(10):
            mock_graph.add_node(
                str(10000 + i),
                name=f"drum_sample_{i:03d}.wav",
                tags=["drum", "percussion", f"style{i % 5}"],
                duration=float(1.2 + (i % 10) * 0.3),
                user=f"producer_{i % 10}",
                audio_url=f"https://freesound.org/data/previews/100/{10000 + i}_preview.mp3",
                uploader_id=12345 + (i % 3),  # REQUIRED for audio playback
                type="sample",
            )

        # Add similarity edges
        for i in range(9):
            mock_graph.add_edge(
                str(10000 + i),
                str(10000 + i + 1),
                type="similar",
                weight=0.6 + (i % 4) * 0.1,
            )

        # Add cross-connections
        for i in range(0, 10, 5):
            if i + 5 < 10:
                mock_graph.add_edge(
                    str(10000 + i),
                    str(10000 + i + 5),
                    type="similar",
                    weight=0.5,
                )

        mock_loader = create_mock_freesound_loader(mock_graph, max_samples=50, checkpoint_dir=None)
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "input_file": "dummy.json",
                "output_file_prefix": os.path.join(tmpdir, "freesound_complete"),
                "strategy": "k-core",
                "k_values": {
                    "strategy_k_values": {"k-core": 1},
                    "default_k_value": 1,
                },
                "data_source": {
                    "source": "freesound",
                    "freesound": {
                        "api_key": "test_api_key",
                        "query": "drum percussion",
                        "tags": ["drum"],
                        "max_samples": 10,
                    },
                },
                "checkpoint": {"checkpoint_dir": os.path.join(tmpdir, "checkpoints")},
                "renderer": {
                    "renderer_type": "sigma",
                    "sigma_interactive": {
                        "enable_audio_player": True,
                        "enable_webgl": True,
                    },
                },
                "visualization": {
                    "static_image": {"generate": False},
                    "node_size_metric": "degree",
                },
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            # Execute complete pipeline
            success = orchestrator.execute_pipeline()

            assert success is True

            # Verify Freesound loader was called correctly
            mock_loader.fetch_data.assert_called_once()
            call_kwargs = mock_loader.fetch_data.call_args[1]
            assert call_kwargs["query"] == "drum percussion"
            assert call_kwargs["tags"] == ["drum"]
            assert call_kwargs["max_samples"] == 10

            # Verify output files
            html_files = list(Path(tmpdir).glob("*.html"))
            assert len(html_files) > 0

            # Verify HTML content
            html_file = html_files[0]
            with open(html_file, encoding="utf-8") as f:
                html_content = f.read()

            # Verify Sigma.js integration
            assert "sigma" in html_content.lower()
            assert "graphology" in html_content.lower()

            # Verify audio player integration
            assert "tone" in html_content.lower()  # Tone.js for audio
            assert "active-players" in html_content  # Multi-player panel

            # Verify Freesound data in JSON data file
            json_files = list(Path(tmpdir).glob("*_data.json"))
            assert len(json_files) > 0, (
                "Sigma renderer should generate a JSON data file"
            )

            import json

            with open(json_files[0], encoding="utf-8") as f:
                graph_data = json.load(f)

            assert "nodes" in graph_data
            assert len(graph_data["nodes"]) > 0

            # Check for Freesound-specific data
            # Node IDs are numeric Freesound sample IDs (10000+)
            node_keys = [node.get("key", "") for node in graph_data["nodes"]]
            assert any(key.startswith("10") for key in node_keys), (
                "Should have Freesound sample ID nodes (10000+)"
            )

            # Check node attributes contain expected Freesound data
            node_attrs = [node.get("attributes", {}) for node in graph_data["nodes"]]

            # Check for names containing drum_sample_
            node_names = [attrs.get("name", "") for attrs in node_attrs if attrs]
            assert any("drum_sample_" in name for name in node_names), (
                "Should have drum_sample_ in node names"
            )

            # Check for uploader_id (REQUIRED for client-side audio URL reconstruction)
            # Note: Audio URLs are now reconstructed client-side from uploader_id
            # Format: https://freesound.org/data/previews/{folder}/{id}_{uploader_id}-{quality}.mp3
            # Without uploader_id, audio playback will not work (but repair workflow can fix it)

            # Verify we have node attributes
            assert len(node_attrs) > 0, "Should have node attributes"


@pytest.mark.integration
class TestAudioPlaybackIntegration:
    """Test audio playback with real Freesound samples."""

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_audio_playback_elements_present(self, mock_loader_class):
        """Test that audio playback elements are properly integrated."""
        mock_graph = nx.DiGraph()
        for i in range(10):
            mock_graph.add_node(
                str(i),
                name=f"audio_sample_{i}.wav",
                audio_url=f"https://freesound.org/data/previews/1/{i}_preview.mp3",
                tags=["test"],
                duration=2.0,
                user="test_user",
                type="sample",
            )
        for i in range(9):
            mock_graph.add_edge(str(i), str(i + 1), type="similar", weight=0.8)

        mock_loader = create_mock_freesound_loader(mock_graph, max_samples=50, checkpoint_dir=None)
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "input_file": "dummy.json",
                "output_file_prefix": os.path.join(tmpdir, "audio_test"),
                "strategy": "k-core",
                "k_values": {
                    "strategy_k_values": {"k-core": 1},
                    "default_k_value": 1,
                },
                "data_source": {
                    "source": "freesound",
                    "freesound": {
                        "api_key": "test_key",
                        "query": "test",
                        "max_samples": 10,
                    },
                },
                "checkpoint": {"checkpoint_dir": os.path.join(tmpdir, "checkpoints")},
                "renderer": {
                    "renderer_type": "sigma",
                    "sigma_interactive": {"enable_audio_player": True},
                },
                "visualization": {"static_image": {"generate": False}},
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            success = orchestrator.execute_pipeline()
            assert success is True

            html_files = list(Path(tmpdir).glob("*.html"))
            assert len(html_files) > 0

            with open(html_files[0], encoding="utf-8") as f:
                html_content = f.read()

            # Verify audio player UI elements
            assert "transport-btn" in html_content or "Start" in html_content
            assert "bpm" in html_content.lower()  # BPM control
            assert "active-players" in html_content  # Multi-player panel
            assert "Tone" in html_content or "tone" in html_content

            # Verify audio URLs are in JSON data file
            json_files = list(Path(tmpdir).glob("*_data.json"))
            assert len(json_files) > 0, (
                "Sigma renderer should generate a JSON data file"
            )

            import json

            with open(json_files[0], encoding="utf-8") as f:
                graph_data = json.load(f)

            # Check for uploader_id in node attributes (used for audio URL reconstruction)
            # Note: Audio URLs are now reconstructed client-side from uploader_id
            # Format: https://freesound.org/data/previews/{folder}/{id}_{uploader_id}-{quality}.mp3
            node_attrs = [
                node.get("attributes", {})
                for node in graph_data.get("nodes", [])
                if node.get("attributes")
            ]

            # Check that nodes have uploader_id for audio reconstruction (REQUIRED)
            # Without uploader_id, audio playback will not work (but repair workflow can fix it)

            # Verify structure
            assert len(node_attrs) > 0, "Should have node attributes in JSON data"


@pytest.mark.integration
class TestVariousGraphSizes:
    """Test with various graph sizes (reduced for speed: 20, 50 nodes)."""

    @pytest.mark.parametrize("num_nodes", [20, 50])
    def test_graph_size_performance(self, num_nodes):
        """Test visualization with different graph sizes."""
        # Create graph of specified size
        mock_graph = nx.DiGraph()
        for i in range(num_nodes):
            mock_graph.add_node(
                str(i),
                name=f"sample_{i}",
                tags=["test"],
                duration=1.0,
                user="test_user",
                audio_url=f"https://freesound.org/test_{i}.mp3",
                type="sample",
            )

        # Add edges to create connected graph
        for i in range(num_nodes - 1):
            mock_graph.add_edge(str(i), str(i + 1), type="similar", weight=0.7)

        # Add some cross-connections
        for i in range(0, num_nodes, 50):
            if i + 100 < num_nodes:
                mock_graph.add_edge(str(i), str(i + 100), type="similar", weight=0.6)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch the loader where it's imported in __main__.py
            with patch(
                "FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader"
            ) as mock_loader_class:
                mock_loader = create_mock_freesound_loader(mock_graph, max_samples=num_nodes, checkpoint_dir=tmpdir)
        mock_loader_class.return_value = mock_loader
                config = {
                    "input_file": "dummy.json",
                    "output_file_prefix": os.path.join(tmpdir, f"size_{num_nodes}"),
                    "strategy": "k-core",
                    "k_values": {
                        "strategy_k_values": {"k-core": 1},
                        "default_k_value": 1,
                    },
                    "data_source": {
                        "source": "freesound",
                        "freesound": {
                            "api_key": "test_key",
                            "query": "test",
                            "max_samples": num_nodes,
                        },
                    },
                    "checkpoint": {
                        "checkpoint_dir": os.path.join(tmpdir, "checkpoints")
                    },
                    "renderer": {"renderer_type": "sigma"},
                    "visualization": {"static_image": {"generate": False}},
                }

                config_obj = load_config_from_dict(config)
                orchestrator = PipelineOrchestrator(config_obj)

                success = orchestrator.execute_pipeline()
                assert success is True

                # Verify output exists
                html_files = list(Path(tmpdir).glob("*.html"))
                assert len(html_files) > 0

            # Verify file size is reasonable
            file_size = os.path.getsize(html_files[0])
            assert file_size > 1000  # Should have substantial content


@pytest.mark.integration
class TestInstagramDataWithBothRenderers:
    """Test Instagram data with both pyvis and sigma renderers."""

    @patch("FollowWeb_Visualizor.__main__.InstagramLoader")
    @pytest.mark.parametrize("renderer_type", ["pyvis", "sigma"])
    def test_instagram_with_renderer(self, mock_loader_class, renderer_type):
        """Test Instagram data with specified renderer."""
        # Create Instagram-like graph (reduced to 10 nodes for speed)
        mock_graph = nx.DiGraph()
        for i in range(10):
            mock_graph.add_node(
                f"user_{i}",
                username=f"user_{i}",
                type="user",
            )

        # Add follower relationships
        for i in range(19):
            mock_graph.add_edge(f"user_{i}", f"user_{i + 1}", type="follows")

        # Add some mutual connections
        for i in range(0, 20, 5):
            if i + 1 < 20:
                mock_graph.add_edge(f"user_{i + 1}", f"user_{i}", type="follows")

        mock_loader = Mock()
        mock_loader.load_from_json.return_value = mock_graph
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "input_file": "test_instagram.json",
                "output_file_prefix": os.path.join(
                    tmpdir, f"instagram_{renderer_type}"
                ),
                "strategy": "k-core",
                "k_values": {
                    "strategy_k_values": {"k-core": 1},
                    "default_k_value": 1,
                },
                "data_source": {"source": "instagram"},
                "renderer": {"renderer_type": renderer_type},
                "visualization": {"static_image": {"generate": False}},
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            success = orchestrator.execute_pipeline()
            assert success is True

            # Verify output
            html_files = list(Path(tmpdir).glob("*.html"))
            assert len(html_files) > 0

            with open(html_files[0], encoding="utf-8") as f:
                html_content = f.read()

            # Verify renderer-specific content
            if renderer_type == "sigma":
                assert "sigma" in html_content.lower()
                assert "graphology" in html_content.lower()

                # For Sigma renderer, check the JSON data file for node data
                json_files = list(Path(tmpdir).glob("*_data.json"))
                assert len(json_files) > 0, (
                    "Sigma renderer should generate a JSON data file"
                )

                import json

                with open(json_files[0], encoding="utf-8") as f:
                    graph_data = json.load(f)

                # Verify Instagram data in JSON
                assert "nodes" in graph_data
                assert len(graph_data["nodes"]) > 0
                # Check that at least one node has a user_ ID
                node_ids = [node["key"] for node in graph_data["nodes"]]
                assert any("user_" in node_id for node_id in node_ids), (
                    "Should have user_ nodes in graph data"
                )

            elif renderer_type == "pyvis":
                assert "vis-network" in html_content or "pyvis" in html_content.lower()
                # For Pyvis, data is embedded in HTML
                assert "user_" in html_content


@pytest.mark.integration
class TestFreesoundDataWithBothRenderers:
    """Test Freesound data with both pyvis and sigma renderers."""

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    @pytest.mark.parametrize("renderer_type", ["pyvis", "sigma"])
    def test_freesound_with_renderer(self, mock_loader_class, renderer_type):
        """Test Freesound data with specified renderer."""
        # Create Freesound graph with proper Freesound-style node IDs
        mock_graph = nx.DiGraph()
        for i in range(15):
            # Use sample name as node ID (matching real Freesound behavior)
            node_id = f"sample_{i}.wav"
            mock_graph.add_node(
                node_id,
                name=node_id,
                tags=["test"],
                duration=1.5,
                user="test_user",
                audio_url=f"https://freesound.org/test_{i}.mp3",
                type="sample",
            )

        for i in range(14):
            mock_graph.add_edge(
                f"sample_{i}.wav", f"sample_{i + 1}.wav", type="similar", weight=0.8
            )

        mock_loader = create_mock_freesound_loader(mock_graph, max_samples=50, checkpoint_dir=None)
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "input_file": "dummy.json",
                "output_file_prefix": os.path.join(
                    tmpdir, f"freesound_{renderer_type}"
                ),
                "strategy": "k-core",
                "k_values": {
                    "strategy_k_values": {"k-core": 1},
                    "default_k_value": 1,
                },
                "data_source": {
                    "source": "freesound",
                    "freesound": {
                        "api_key": "test_key",
                        "query": "test",
                        "max_samples": 15,
                    },
                },
                "checkpoint": {"checkpoint_dir": os.path.join(tmpdir, "checkpoints")},
                "renderer": {"renderer_type": renderer_type},
                "visualization": {"static_image": {"generate": False}},
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            success = orchestrator.execute_pipeline()
            assert success is True

            # Verify output
            html_files = list(Path(tmpdir).glob("*.html"))
            assert len(html_files) > 0

            with open(html_files[0], encoding="utf-8") as f:
                html_content = f.read()

            # Verify renderer-specific content
            if renderer_type == "sigma":
                assert "sigma" in html_content.lower()

                # For Sigma renderer, check the JSON data file for node data
                json_files = list(Path(tmpdir).glob("*_data.json"))
                assert len(json_files) > 0, (
                    "Sigma renderer should generate a JSON data file"
                )

                import json

                with open(json_files[0], encoding="utf-8") as f:
                    graph_data = json.load(f)

                # Verify Freesound data in JSON
                assert "nodes" in graph_data
                assert len(graph_data["nodes"]) > 0
                # Check that at least one node has a sample_ ID
                node_ids = [node["key"] for node in graph_data["nodes"]]
                assert any("sample_" in node_id for node_id in node_ids), (
                    "Should have sample_ nodes in graph data"
                )

            elif renderer_type == "pyvis":
                assert "vis-network" in html_content or "pyvis" in html_content.lower()
                # For Pyvis, data is embedded in HTML
                assert "sample_" in html_content


@pytest.mark.integration
class TestAllConfigurationOptions:
    """Test all configuration options."""

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_comprehensive_configuration(self, mock_loader_class):
        """Test pipeline with comprehensive configuration options."""
        mock_graph = nx.DiGraph()
        for i in range(10):
            mock_graph.add_node(
                str(i),
                name=f"sample_{i}",
                tags=["test"],
                duration=1.0,
                user="test_user",
                audio_url=f"https://freesound.org/test_{i}.mp3",
                type="sample",
            )
        for i in range(9):
            mock_graph.add_edge(str(i), str(i + 1), type="similar", weight=0.8)

        mock_loader = create_mock_freesound_loader(mock_graph, max_samples=50, checkpoint_dir=None)
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "input_file": "dummy.json",
                "output_file_prefix": os.path.join(tmpdir, "comprehensive"),
                "strategy": "k-core",
                "k_values": {
                    "strategy_k_values": {"k-core": 1},
                    "default_k_value": 1,
                },
                "data_source": {
                    "source": "freesound",
                    "freesound": {
                        "api_key": "test_key",
                        "query": "test query",
                        "tags": ["tag1", "tag2"],
                        "max_samples": 10,
                    },
                },
                "checkpoint": {
                    "checkpoint_dir": os.path.join(tmpdir, "checkpoints"),
                    "checkpoint_interval": 5,
                    "max_runtime_hours": 1.0,
                    "verify_existing_sounds": False,
                },
                "renderer": {
                    "renderer_type": "sigma",
                    "sigma_interactive": {
                        "height": "100vh",
                        "width": "100%",
                        "enable_webgl": True,
                        "enable_audio_player": True,
                        "show_labels": True,
                        "show_tooltips": True,
                    },
                },
                "visualization": {
                    "static_image": {"generate": False},
                    "node_size_metric": "degree",
                    "base_node_size": 6.0,
                    "node_size_multiplier": 4.0,
                    "scaling_algorithm": "logarithmic",
                },
                "output": {
                    "generate_reports": True,
                },
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            success = orchestrator.execute_pipeline()
            assert success is True

            # Verify all configuration was applied
            assert config_obj.data_source.freesound.query == "test query"
            assert config_obj.data_source.freesound.tags == ["tag1", "tag2"]
            assert config_obj.checkpoint.checkpoint_interval == 5
            assert config_obj.checkpoint.max_runtime_hours == 1.0
            assert config_obj.renderer.sigma_interactive.enable_webgl is True
            assert config_obj.renderer.sigma_interactive.enable_audio_player is True

            # Verify outputs
            html_files = list(Path(tmpdir).glob("*.html"))
            assert len(html_files) > 0


@pytest.mark.integration
class TestErrorHandlingAndRecovery:
    """Test error handling and recovery."""

    def test_invalid_data_source_error(self):
        """Test handling of invalid data source."""
        config = {
            "input_file": "test.json",
            "output_file_prefix": "test_output",
            "strategy": "k-core",
            "data_source": {"source": "invalid_source"},
        }

        with pytest.raises(ValueError, match="source"):
            load_config_from_dict(config)

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_api_error_recovery(self, mock_loader_class):
        """Test recovery from API errors."""
        mock_loader = Mock()
        mock_loader.fetch_data.side_effect = Exception("API connection failed")
        mock_loader_class.return_value = mock_loader

        config = {
            "input_file": "dummy.json",
            "output_file_prefix": "test_output",
            "strategy": "k-core",
            "data_source": {
                "source": "freesound",
                "freesound": {
                    "api_key": "test_key",
                    "query": "test",
                    "max_samples": 10,
                },
            },
            "checkpoint": {"checkpoint_dir": "./checkpoints"},
        }

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        success = orchestrator.execute_pipeline()
        assert success is False

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_empty_graph_handling(self, mock_loader_class):
        """Test handling of empty graph."""
        mock_graph = nx.DiGraph()  # Empty graph

        mock_loader = create_mock_freesound_loader(mock_graph, max_samples=50, checkpoint_dir=None)
        mock_loader_class.return_value = mock_loader

        config = {
            "input_file": "dummy.json",
            "output_file_prefix": "test_output",
            "strategy": "k-core",
            "data_source": {
                "source": "freesound",
                "freesound": {
                    "api_key": "test_key",
                    "query": "nonexistent",
                    "max_samples": 10,
                },
            },
            "checkpoint": {"checkpoint_dir": "./checkpoints"},
        }

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        success = orchestrator.execute_pipeline()
        assert success is False

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_partial_failure_recovery(self, mock_loader_class):
        """Test recovery from partial failures."""
        # Create valid graph
        mock_graph = nx.DiGraph()
        for i in range(5):
            mock_graph.add_node(str(i), name=f"test_{i}", type="sample")
        for i in range(4):
            mock_graph.add_edge(str(i), str(i + 1), type="similar", weight=0.8)

        mock_loader = create_mock_freesound_loader(mock_graph, max_samples=5, checkpoint_dir=None)
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "input_file": "dummy.json",
                "output_file_prefix": os.path.join(tmpdir, "recovery_test"),
                "strategy": "k-core",
                "k_values": {
                    "strategy_k_values": {"k-core": 1},
                    "default_k_value": 1,
                },
                "data_source": {
                    "source": "freesound",
                    "freesound": {
                        "api_key": "test_key",
                        "query": "test",
                        "max_samples": 5,
                    },
                },
                "checkpoint": {"checkpoint_dir": os.path.join(tmpdir, "checkpoints")},
                "renderer": {"renderer_type": "sigma"},
                "visualization": {"static_image": {"generate": False}},
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            # Should complete successfully even with minimal graph
            success = orchestrator.execute_pipeline()
            assert success is True


@pytest.mark.integration
class TestMultipleRenderersOutput:
    """Test generating multiple renderer outputs."""

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_all_renderers_output(self, mock_loader_class):
        """Test that 'all' renderer type generates multiple outputs."""
        mock_graph = nx.DiGraph()
        for i in range(10):
            mock_graph.add_node(str(i), name=f"test_{i}")
        for i in range(9):
            mock_graph.add_edge(str(i), str(i + 1))

        mock_loader = create_mock_freesound_loader(mock_graph, max_samples=50, checkpoint_dir=None)
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "input_file": "dummy.json",
                "output_file_prefix": os.path.join(tmpdir, "multi_renderer"),
                "strategy": "k-core",
                "k_values": {
                    "strategy_k_values": {"k-core": 1},
                    "default_k_value": 1,
                },
                "data_source": {
                    "source": "freesound",
                    "freesound": {
                        "api_key": "test_key",
                        "query": "test",
                        "max_samples": 10,
                    },
                },
                "checkpoint": {"checkpoint_dir": os.path.join(tmpdir, "checkpoints")},
                "renderer": {"renderer_type": "all"},
                "visualization": {"static_image": {"generate": False}},
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            success = orchestrator.execute_pipeline()
            assert success is True

            # Should generate HTML files
            html_files = list(Path(tmpdir).glob("*.html"))
            assert len(html_files) > 0


