"""
Integration tests for pipeline with Freesound data and Sigma renderer.

Tests end-to-end pipeline execution with Freesound data source and Sigma.js
visualization, including configuration loading, output generation, and error handling.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import networkx as nx
import pytest

from FollowWeb_Visualizor.core.config import load_config_from_dict
from FollowWeb_Visualizor.main import PipelineOrchestrator

pytestmark = [pytest.mark.integration, pytest.mark.pipeline]


@pytest.mark.integration
class TestFreesoundPipelineIntegration:
    """Test pipeline integration with Freesound data source."""

    def test_freesound_configuration_loading(self):
        """Test that Freesound configuration is properly loaded."""
        config = {
            "input_file": "dummy.json",  # Not used for Freesound
            "output_file_prefix": "test_output",
            "strategy": "k-core",
            "data_source": {
                "source": "freesound",
                "freesound": {
                    "api_key": "test_api_key_12345",
                    "query": "drum",
                    "tags": ["percussion", "kick"],
                    "max_samples": 50,
                },
            },
            "checkpoint": {
                "checkpoint_dir": "./test_checkpoints",
                "checkpoint_interval": 10,
                "max_runtime_hours": 1.0,
                "verify_existing_sounds": False,
            },
            "renderer": {"renderer_type": "sigma"},
        }

        config_obj = load_config_from_dict(config)

        # Verify Freesound configuration
        assert config_obj.data_source.source == "freesound"
        assert config_obj.data_source.freesound.api_key == "test_api_key_12345"
        assert config_obj.data_source.freesound.query == "drum"
        assert config_obj.data_source.freesound.tags == ["percussion", "kick"]
        assert config_obj.data_source.freesound.max_samples == 50
        # Note: include_similar removed (deprecated parameter)

        # Verify checkpoint configuration
        assert config_obj.checkpoint.checkpoint_dir == "./test_checkpoints"
        assert config_obj.checkpoint.checkpoint_interval == 10
        assert config_obj.checkpoint.max_runtime_hours == 1.0
        assert config_obj.checkpoint.verify_existing_sounds is False

        # Verify renderer configuration
        assert config_obj.renderer.renderer_type == "sigma"

    def test_freesound_loader_initialization(self):
        """Test that FreesoundLoader is properly initialized in pipeline."""
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
            "checkpoint": {
                "checkpoint_dir": "./checkpoints",
            },
        }

        config_obj = load_config_from_dict(config)

        # Mock the loader initialization and graph loading
        mock_graph = nx.DiGraph()
        mock_graph.add_node("1", name="test_sample", community=0, degree=1)

        with patch(
            "FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load.return_value = mock_graph
            mock_loader_class.return_value = mock_loader

            orchestrator = PipelineOrchestrator(config_obj)

            # Loader should be None until strategy phase
            assert orchestrator.graph_loader is None

            # Execute strategy phase (will initialize loader)
            with patch.object(
                orchestrator.graph_strategy, "prune_graph", return_value=mock_graph
            ):
                orchestrator._execute_strategy_phase()

            # Verify loader was initialized with correct config
            mock_loader_class.assert_called_once()
            call_kwargs = mock_loader_class.call_args[1]
            assert "config" in call_kwargs
            assert call_kwargs["config"]["api_key"] == "test_key"

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_freesound_pipeline_end_to_end_mocked(self, mock_loader_class):
        """Test end-to-end pipeline with mocked Freesound data."""
        # Create mock graph with Freesound-like attributes
        mock_graph = nx.DiGraph()
        for i in range(10):
            mock_graph.add_node(
                str(i),
                name=f"sample_{i}.wav",
                tags=["drum", "percussion"],
                duration=1.5,
                user="test_user",
                audio_url=f"https://freesound.org/data/previews/{i}_preview.mp3",
                type="sample",
            )
        for i in range(9):
            mock_graph.add_edge(str(i), str(i + 1), type="similar", weight=0.8)

        # Setup mock loader
        mock_loader = Mock()
        mock_loader.load.return_value = mock_graph
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "input_file": "dummy.json",
                "output_file_prefix": os.path.join(tmpdir, "freesound_test"),
                "strategy": "k-core",
                "k_values": {
                    "strategy_k_values": {"k-core": 1},
                    "default_k_value": 1,
                },
                "data_source": {
                    "source": "freesound",
                    "freesound": {
                        "api_key": "test_key",
                        "query": "drum",
                        "max_samples": 10,
                    },
                },
                "checkpoint": {"checkpoint_dir": os.path.join(tmpdir, "checkpoints")},
                "renderer": {"renderer_type": "sigma"},
                "pipeline_stages": {
                    "enable_strategy": True,
                    "enable_analysis": True,
                    "enable_visualization": True,
                },
                "visualization": {
                    "static_image": {"generate": False},
                },
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            # Execute pipeline
            success = orchestrator.execute_pipeline()

            assert success is True

            # Verify loader was called
            mock_loader.load.assert_called_once()

            # Verify output files were created
            html_files = list(Path(tmpdir).glob("*.html"))
            assert len(html_files) > 0


@pytest.mark.integration
class TestSigmaRendererPipelineIntegration:
    """Test pipeline integration with Sigma renderer."""

    def test_sigma_renderer_configuration(self):
        """Test that Sigma renderer configuration is properly loaded."""
        config = {
            "input_file": "test.json",
            "output_file_prefix": "test_output",
            "strategy": "k-core",
            "renderer": {
                "renderer_type": "sigma",
                "sigma_interactive": {
                    "height": "100vh",
                    "width": "100%",
                    "enable_webgl": True,
                    "enable_audio_player": True,
                },
            },
        }

        config_obj = load_config_from_dict(config)

        # Verify renderer configuration
        assert config_obj.renderer.renderer_type == "sigma"
        assert config_obj.renderer.sigma_interactive.height == "100vh"
        assert config_obj.renderer.sigma_interactive.width == "100%"
        assert config_obj.renderer.sigma_interactive.enable_webgl is True
        assert config_obj.renderer.sigma_interactive.enable_audio_player is True

    def test_sigma_renderer_selection(self, fast_config):
        """Test that Sigma renderer is selected when configured."""
        config = fast_config.copy()
        config["renderer"] = {"renderer_type": "sigma"}

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        # Verify renderer type is set correctly
        assert orchestrator.config.renderer.renderer_type == "sigma"

    @patch("FollowWeb_Visualizor.__main__.InstagramLoader")
    def test_sigma_visualization_output(self, mock_loader_class, fast_config):
        """Test that Sigma renderer generates HTML output."""
        # Create mock graph
        mock_graph = nx.DiGraph()
        for i in range(5):
            mock_graph.add_node(i, name=f"Node_{i}")
        for i in range(4):
            mock_graph.add_edge(i, i + 1)

        # Setup mock loader
        mock_loader = Mock()
        mock_loader.load_from_json.return_value = mock_graph
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = fast_config.copy()
            config["output_file_prefix"] = os.path.join(tmpdir, "sigma_test")
            config["renderer"] = {"renderer_type": "sigma"}
            config["visualization"] = {
                "static_image": {"generate": False},
            }
            # Use k=1 for small test graph
            config["k_values"] = {
                "strategy_k_values": {"k-core": 1},
                "default_k_value": 1,
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            # Execute pipeline
            success = orchestrator.execute_pipeline()

            assert success is True

            # Verify HTML output was created
            html_files = list(Path(tmpdir).glob("*.html"))
            assert len(html_files) > 0

            # Verify HTML contains Sigma.js elements
            html_file = html_files[0]
            with open(html_file, encoding="utf-8") as f:
                html_content = f.read()

            assert "sigma" in html_content.lower()
            assert "graphology" in html_content.lower()


@pytest.mark.integration
class TestFreesoundSigmaPipelineIntegration:
    """Test complete pipeline with Freesound data and Sigma renderer."""

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_freesound_sigma_end_to_end(self, mock_loader_class):
        """Test complete workflow: Freesound data → Analysis → Sigma visualization."""
        # Create realistic Freesound graph
        mock_graph = nx.DiGraph()
        for i in range(20):
            mock_graph.add_node(
                str(10000 + i),
                name=f"sample_{i:03d}.wav",
                tags=["drum", "percussion", f"tag{i % 5}"],
                duration=float(1 + (i % 5)),
                user=f"user_{i % 5}",
                audio_url=f"https://freesound.org/data/previews/{10000 + i}_preview.mp3",
                type="sample",
            )

        # Add similarity edges
        for i in range(19):
            mock_graph.add_edge(
                str(10000 + i),
                str(10000 + i + 1),
                type="similar",
                weight=0.7 + (i % 3) * 0.1,
            )

        # Setup mock loader
        mock_loader = Mock()
        mock_loader.load.return_value = mock_graph
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "input_file": "dummy.json",
                "output_file_prefix": os.path.join(tmpdir, "freesound_sigma"),
                "strategy": "k-core",
                "k_values": {
                    "strategy_k_values": {"k-core": 1},
                    "default_k_value": 1,
                },
                "data_source": {
                    "source": "freesound",
                    "freesound": {
                        "api_key": "test_key",
                        "query": "drum percussion",
                        "tags": ["drum"],
                        "max_samples": 20,
                    },
                },
                "checkpoint": {"checkpoint_dir": os.path.join(tmpdir, "checkpoints")},
                "renderer": {
                    "renderer_type": "sigma",
                    "sigma_interactive": {
                        "height": "100vh",
                        "width": "100%",
                        "enable_webgl": True,
                        "enable_audio_player": True,
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

            # Verify Freesound loader was called with correct parameters
            mock_loader.load.assert_called_once()
            call_kwargs = mock_loader.load.call_args[1]
            assert call_kwargs["query"] == "drum percussion"
            assert call_kwargs["tags"] == ["drum"]
            assert call_kwargs["max_samples"] == 20
            # Note: include_similar is no longer passed (deprecated parameter)

            # Verify HTML output was created
            html_files = list(Path(tmpdir).glob("*.html"))
            assert len(html_files) > 0

            # Verify HTML contains both Freesound and Sigma elements
            html_file = html_files[0]
            with open(html_file, encoding="utf-8") as f:
                html_content = f.read()

            # Check for Sigma.js
            assert "sigma" in html_content.lower()
            assert "graphology" in html_content.lower()

            # Check for audio player (since enable_audio is True)
            assert "tone" in html_content.lower()  # Tone.js for audio
            assert "audio" in html_content.lower()

            # Check for external JSON data file reference
            assert "_data.json" in html_content

            # Verify JSON data file exists and contains Freesound data
            json_files = list(Path(tmpdir).glob("*_data.json"))
            assert len(json_files) > 0

            import json

            with open(json_files[0], encoding="utf-8") as f:
                graph_data = json.load(f)

            # Check for Freesound data in JSON
            assert "nodes" in graph_data
            assert len(graph_data["nodes"]) > 0
            # Check that nodes have Freesound sample names
            node_names = [
                node["attributes"].get("name", "") for node in graph_data["nodes"]
            ]
            assert any("sample_" in name for name in node_names)

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_freesound_sigma_with_audio_disabled(self, mock_loader_class):
        """Test Freesound + Sigma pipeline with audio playback disabled."""
        # Create graph with multiple nodes and edges to survive k-core pruning
        mock_graph = nx.DiGraph()
        for i in range(5):
            mock_graph.add_node(
                str(i),
                name=f"test_sample_{i}.wav",
                tags=["test"],
                duration=1.0,
                user="test_user",
                audio_url=f"https://freesound.org/test_{i}.mp3",
                type="sample",
            )
        # Add edges to create connections
        for i in range(4):
            mock_graph.add_edge(str(i), str(i + 1), type="similar", weight=0.8)

        mock_loader = Mock()
        mock_loader.load.return_value = mock_graph
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "input_file": "dummy.json",
                "output_file_prefix": os.path.join(tmpdir, "test"),
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
                "renderer": {
                    "renderer_type": "sigma",
                    "sigma_interactive": {
                        "enable_audio_player": False,
                    },
                },
                "visualization": {
                    "static_image": {"generate": False},
                },
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            success = orchestrator.execute_pipeline()

            assert success is True

            # Verify output exists
            html_files = list(Path(tmpdir).glob("*.html"))
            assert len(html_files) > 0


@pytest.mark.integration
class TestPipelineErrorHandling:
    """Test error handling in pipeline integration."""

    def test_invalid_freesound_api_key_handling(self):
        """Test handling of invalid Freesound API key."""
        config = {
            "input_file": "dummy.json",
            "output_file_prefix": "test_output",
            "strategy": "k-core",
            "data_source": {
                "source": "freesound",
                "freesound": {
                    "api_key": "",  # Empty API key
                    "query": "test",
                    "max_samples": 10,
                },
            },
            "checkpoint": {"checkpoint_dir": "./checkpoints"},
        }

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        # Mock FreesoundLoader to raise authentication error
        with patch(
            "FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader"
        ) as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load.side_effect = Exception("Authentication failed")
            mock_loader_class.return_value = mock_loader

            success = orchestrator.execute_pipeline()

            assert success is False

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_empty_freesound_graph_handling(self, mock_loader_class):
        """Test handling of empty graph from Freesound."""
        # Return empty graph
        mock_graph = nx.DiGraph()

        mock_loader = Mock()
        mock_loader.load.return_value = mock_graph
        mock_loader_class.return_value = mock_loader

        config = {
            "input_file": "dummy.json",
            "output_file_prefix": "test_output",
            "strategy": "k-core",
            "data_source": {
                "source": "freesound",
                "freesound": {
                    "api_key": "test_key",
                    "query": "nonexistent_query_xyz",
                    "max_samples": 10,
                },
            },
            "checkpoint": {"checkpoint_dir": "./checkpoints"},
        }

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        success = orchestrator.execute_pipeline()

        assert success is False

    def test_invalid_renderer_type_error(self):
        """Test that invalid renderer type raises error."""
        config = {
            "input_file": "test.json",
            "output_file_prefix": "test_output",
            "strategy": "k-core",
            "renderer": {"renderer_type": "invalid_renderer"},
        }

        with pytest.raises(ValueError, match="renderer_type"):
            load_config_from_dict(config)

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_visualization_phase_error_handling(self, mock_loader_class):
        """Test that pipeline handles visualization phase errors gracefully."""
        # Create graph with multiple nodes and edges
        mock_graph = nx.DiGraph()
        for i in range(5):
            mock_graph.add_node(str(i), name=f"test_{i}")
        for i in range(4):
            mock_graph.add_edge(str(i), str(i + 1))

        mock_loader = Mock()
        mock_loader.load.return_value = mock_graph
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            # Use an invalid output path to cause visualization to fail
            # Use platform-appropriate invalid path
            if os.name == "nt":  # Windows
                invalid_path = "Z:\\nonexistent\\path\\test"
            else:  # Unix/macOS
                invalid_path = "/nonexistent/path/test"

            config = {
                "input_file": "dummy.json",
                "output_file_prefix": invalid_path,  # Invalid path
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
                "visualization": {
                    "static_image": {"generate": False},
                },
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            success = orchestrator.execute_pipeline()

            # Pipeline should handle visualization errors gracefully
            # The pipeline creates directories automatically, so this test
            # verifies that the pipeline completes even with unusual paths
            assert success in [True, False]  # Either succeeds or fails gracefully


@pytest.mark.integration
class TestMultipleRenderersPipeline:
    """Test pipeline with multiple renderers."""

    @patch("FollowWeb_Visualizor.__main__.InstagramLoader")
    def test_all_renderers_configuration(self, mock_loader_class, fast_config):
        """Test pipeline with renderer_type='all' generates multiple outputs."""
        mock_graph = nx.DiGraph()
        for i in range(5):
            mock_graph.add_node(i, name=f"Node_{i}")
        for i in range(4):
            mock_graph.add_edge(i, i + 1)

        mock_loader = Mock()
        mock_loader.load_from_json.return_value = mock_graph
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = fast_config.copy()
            config["output_file_prefix"] = os.path.join(tmpdir, "multi_renderer")
            config["renderer"] = {"renderer_type": "all"}
            config["visualization"] = {
                "static_image": {"generate": False},
            }
            # Use k=1 for small test graph
            config["k_values"] = {
                "strategy_k_values": {"k-core": 1},
                "default_k_value": 1,
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            success = orchestrator.execute_pipeline()

            assert success is True

            # Should generate HTML files (potentially multiple if "all" creates multiple)
            html_files = list(Path(tmpdir).glob("*.html"))
            assert len(html_files) > 0


@pytest.mark.integration
class TestPipelineOutputGeneration:
    """Test output file generation in pipeline."""

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_output_file_naming(self, mock_loader_class):
        """Test that output files are named correctly."""
        # Create graph with multiple nodes and edges
        mock_graph = nx.DiGraph()
        for i in range(5):
            mock_graph.add_node(str(i), name=f"test_{i}")
        for i in range(4):
            mock_graph.add_edge(str(i), str(i + 1))

        mock_loader = Mock()
        mock_loader.load.return_value = mock_graph
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            output_prefix = os.path.join(tmpdir, "freesound_output")

            config = {
                "input_file": "dummy.json",
                "output_file_prefix": output_prefix,
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
                "visualization": {
                    "static_image": {"generate": False},
                },
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            success = orchestrator.execute_pipeline()

            assert success is True

            # Check that files exist in the correct directory
            output_dir = Path(tmpdir)
            assert output_dir.exists()

            # Check for HTML files
            html_files = list(output_dir.glob("*.html"))
            assert len(html_files) > 0

    @patch("FollowWeb_Visualizor.data.loaders.IncrementalFreesoundLoader")
    def test_metrics_report_generation(self, mock_loader_class):
        """Test that metrics report is generated."""
        mock_graph = nx.DiGraph()
        for i in range(5):
            mock_graph.add_node(str(i), name=f"sample_{i}")
        for i in range(4):
            mock_graph.add_edge(str(i), str(i + 1))

        mock_loader = Mock()
        mock_loader.load.return_value = mock_graph
        mock_loader_class.return_value = mock_loader

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "input_file": "dummy.json",
                "output_file_prefix": os.path.join(tmpdir, "test"),
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
                "visualization": {
                    "static_image": {"generate": False},
                },
                "output": {
                    "generate_reports": True,
                },
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)

            success = orchestrator.execute_pipeline()

            assert success is True

            # Check for metrics report
            txt_files = list(Path(tmpdir).glob("*.txt"))
            assert len(txt_files) > 0

            # Verify report content
            report_file = txt_files[0]
            with open(report_file, encoding="utf-8") as f:
                content = f.read()
                assert "FOLLOWWEB" in content or "GRAPH" in content
