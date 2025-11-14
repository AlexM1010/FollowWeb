"""
Integration tests for data loader integration in the pipeline.

Tests that the pipeline correctly selects and initializes data loaders
based on configuration.
"""

import pytest

from FollowWeb_Visualizor.core.config import load_config_from_dict
from FollowWeb_Visualizor.main import PipelineOrchestrator

pytestmark = [pytest.mark.integration, pytest.mark.data]


class TestDataLoaderIntegration:
    """Test data loader integration in pipeline."""

    @pytest.mark.integration
    def test_instagram_loader_selection(self, fast_config):
        """Test that Instagram loader is selected when data_source is instagram."""
        config = fast_config.copy()
        config["data_source"] = {"source": "instagram"}

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        # Verify config is set correctly
        assert orchestrator.config.data_source.source == "instagram"

        # Loader should be None until strategy phase
        assert orchestrator.graph_loader is None

    @pytest.mark.integration
    def test_freesound_loader_selection(self, fast_config):
        """Test that Freesound loader is selected when data_source is freesound."""
        config = fast_config.copy()
        config["data_source"] = {
            "source": "freesound",
            "freesound": {"api_key": "test_key", "query": "test", "max_samples": 100},
        }

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        # Verify config is set correctly
        assert orchestrator.config.data_source.source == "freesound"
        assert orchestrator.config.data_source.freesound.api_key == "test_key"

        # Loader should be None until strategy phase
        assert orchestrator.graph_loader is None

    @pytest.mark.integration
    def test_invalid_data_source_error(self, fast_config):
        """Test that invalid data source raises error during strategy phase."""
        config = fast_config.copy()
        config["data_source"] = {"source": "invalid_source"}

        # This should fail validation
        with pytest.raises(ValueError, match="data_source.source"):
            load_config_from_dict(config)


class TestRendererIntegration:
    """Test renderer integration in pipeline."""

    @pytest.mark.integration
    def test_pyvis_renderer_selection(self, fast_config):
        """Test that Pyvis renderer is selected when renderer_type is pyvis."""
        config = fast_config.copy()
        config["renderer"] = {"renderer_type": "pyvis"}

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        # Verify config is set correctly
        assert orchestrator.config.renderer.renderer_type == "pyvis"

    @pytest.mark.integration
    def test_sigma_renderer_selection(self, fast_config):
        """Test that Sigma renderer is selected when renderer_type is sigma."""
        config = fast_config.copy()
        config["renderer"] = {"renderer_type": "sigma"}

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        # Verify config is set correctly
        assert orchestrator.config.renderer.renderer_type == "sigma"

    @pytest.mark.integration
    def test_all_renderers_selection(self, fast_config):
        """Test that all renderers are selected when renderer_type is all."""
        config = fast_config.copy()
        config["renderer"] = {"renderer_type": "all"}

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        # Verify config is set correctly
        assert orchestrator.config.renderer.renderer_type == "all"

    @pytest.mark.integration
    def test_invalid_renderer_type_error(self, fast_config):
        """Test that invalid renderer type raises error."""
        config = fast_config.copy()
        config["renderer"] = {"renderer_type": "invalid_renderer"}

        # This should fail validation
        with pytest.raises(ValueError, match="renderer_type"):
            load_config_from_dict(config)
