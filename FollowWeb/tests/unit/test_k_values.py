"""
Comprehensive k-value testing module.

This module contains all k-value related tests, allowing other test modules
to focus on their core functionality without redundant k-value testing.
Users can run this module specifically when they need thorough k-value testing,
or skip it for faster test execution.

Usage:
- Run all tests: pytest Package/tests/
- Run without k-value tests: pytest Package/tests/ -k "not test_k_values"
- Run only k-value tests: pytest Package/tests/unit/test_k_values.py
"""

from typing import Any, Dict

import pytest

from FollowWeb_Visualizor.core.config import KValueConfig, get_configuration_manager
from FollowWeb_Visualizor.main import PipelineOrchestrator


class TestKValueConfiguration:
    """Test k-value configuration and validation."""

    def test_fast_config_uses_appropriate_k_values(self, fast_config: Dict[str, Any]):
        """Test that fast config uses k-values appropriate for the dataset size."""
        k_values = fast_config.get("k_values", {}).get("strategy_k_values", {})
        default_k = fast_config.get("k_values", {}).get("default_k_value", 1)

        # Fast operations should use k-values appropriate for small test dataset
        # Values should be positive and reasonable for the dataset size
        for strategy, k_value in k_values.items():
            assert k_value >= 1, (
                f"Fast config k-value for {strategy} should be >= 1, got {k_value}"
            )
            assert k_value <= 10, (
                f"Fast config k-value for {strategy} should be <= 10 for small dataset, got {k_value}"
            )

        assert default_k >= 1, (
            f"Fast config default k-value should be >= 1, got {default_k}"
        )
        assert default_k <= 10, (
            f"Fast config default k-value should be <= 10 for small dataset, got {default_k}"
        )

    def test_default_config_k_values(self):
        """Test that default config uses production k-values."""
        config_manager = get_configuration_manager()
        config_obj = config_manager.load_configuration()
        k_values = config_obj.k_values.strategy_k_values
        default_k = config_obj.k_values.default_k_value

        # Production config should use reasonable k-values
        for strategy, k_value in k_values.items():
            assert k_value >= 0, (
                f"Production k-value for {strategy} should be >= 0, got {k_value}"
            )

        assert default_k >= 0, (
            f"Production default k-value should be >= 0, got {default_k}"
        )

    def test_k_value_consistency_within_config(self, fast_config: Dict[str, Any]):
        """Test that k-values are consistent within a configuration."""
        k_values = fast_config.get("k_values", {}).get("strategy_k_values", {})

        # All strategies should use reasonable k-values for the dataset
        k_value_list = list(k_values.values())
        if len(k_value_list) > 1:
            max_k = max(k_value_list)
            min_k = min(k_value_list)
            # Allow reasonable variation based on strategy differences
            # Reciprocal and ego strategies typically use lower k-values due to filtering
            assert max_k - min_k <= 5, (
                f"K-values should be reasonably consistent, range: {min_k}-{max_k}"
            )
            assert max_k <= min_k * 3, (
                f"K-values should not vary excessively, max={max_k}, min={min_k}"
            )


class TestKValueGraphPruning:
    """Test k-value graph pruning functionality."""

    @pytest.mark.unit
    def test_k_value_zero_handling(
        self, sample_data_file: str, sample_data_exists: bool
    ):
        """Test that k=0 returns the original graph."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.data.loaders import GraphLoader

        loader = GraphLoader()
        original_graph = loader.load_from_json(sample_data_file)
        pruned_graph = loader.prune_graph(original_graph, 0)

        # k=0 should return the original graph
        assert pruned_graph.number_of_nodes() == original_graph.number_of_nodes()
        assert pruned_graph.number_of_edges() == original_graph.number_of_edges()

    @pytest.mark.unit
    def test_k_value_boundary_conditions(
        self, sample_data_file: str, sample_data_exists: bool
    ):
        """Test k-value boundary conditions."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.data.loaders import GraphLoader

        loader = GraphLoader()
        original_graph = loader.load_from_json(sample_data_file)

        if original_graph.number_of_nodes() == 0:
            pytest.skip("Need non-empty graph for boundary testing")

        # Test very high k-value (should result in empty or very small graph)
        very_high_k = original_graph.number_of_nodes() + 100
        pruned_graph = loader.prune_graph(original_graph, very_high_k)

        # Very high k should result in smaller or equal graph
        assert pruned_graph.number_of_nodes() <= original_graph.number_of_nodes()

        # Test negative k-value (should return original graph)
        negative_k_graph = loader.prune_graph(original_graph, -5)
        assert negative_k_graph.number_of_nodes() == original_graph.number_of_nodes()


class TestKValueValidation:
    """Test k-value configuration validation."""

    def test_valid_k_value_ranges(self):
        """Test that valid k-value ranges are accepted."""
        from tests.conftest import calculate_appropriate_k_values

        # Test various valid k-value configurations based on dataset sizes
        test_datasets = ["small_real", "medium_real", "full_anonymized"]

        for dataset_name in test_datasets:
            k_values_config = calculate_appropriate_k_values(dataset_name)
            k_values = k_values_config["strategy_k_values"]

            config = KValueConfig(
                strategy_k_values=k_values,
                default_k_value=k_values_config["default_k_value"],
            )
            assert config.default_k_value >= 0
            for _strategy, k_value in config.strategy_k_values.items():
                assert k_value >= 0

    def test_k_value_edge_cases(self):
        """Test k-value edge cases."""
        # Test minimum valid k-value (0)
        min_config = KValueConfig(strategy_k_values={"k-core": 0}, default_k_value=0)
        assert min_config.default_k_value == 0

        # Test high k-values (but realistic for scalability testing)
        from tests.conftest import get_scalability_k_values

        scalability_k_values = get_scalability_k_values("full_anonymized")
        high_k = scalability_k_values["strategy_k_values"]["k-core"]

        high_config = KValueConfig(
            strategy_k_values={"k-core": high_k}, default_k_value=high_k
        )
        assert high_config.default_k_value == high_k

    def test_invalid_k_values_rejected(self):
        """Test that invalid k-values are rejected."""
        # Test negative k-values in dictionary
        with pytest.raises(ValueError, match="K-value must be non-negative"):
            KValueConfig(strategy_k_values={"k-core": -1})

        # Test negative default k-value
        with pytest.raises(ValueError, match="default_k_value must be non-negative"):
            KValueConfig(default_k_value=-1)


class TestKValuePipelineIntegration:
    """Test k-value integration with pipeline execution."""

    @pytest.mark.integration
    def test_basic_k_value_pipeline_execution(
        self, fast_config: Dict[str, Any], sample_data_exists: bool
    ):
        """Test pipeline execution with basic k-values."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["k_values"] = {
            "strategy_k_values": {"k-core": 1},
            "default_k_value": 1,
        }

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success, "Pipeline should succeed with basic k-value"
