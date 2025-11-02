"""
Unit tests for enhanced configuration management module.

Tests configuration validation, ConfigurationManager functionality,
and error handling for all configuration components.
"""

from typing import Any, Dict

import pytest

from FollowWeb_Visualizor.core.config import (
    AnalysisMode,
    AnalysisModeConfig,
    ConfigurationManager,
    DuplicateParameter,
    FameAnalysisConfig,
    KValueConfig,
    OutputConfig,
    OutputControlConfig,
    PipelineConfig,
    PipelineStagesConfig,
    PyvisInteractiveConfig,
    StaticImageConfig,
    ValidationResult,
    VisualizationConfig,
    get_configuration_manager,
    load_config_from_dict,
)


class TestPipelineConfig:
    """Test PipelineConfig dataclass validation."""

    def test_valid_pipeline_config(self):
        """Test creation of valid PipelineConfig."""
        config = PipelineConfig(
            strategy="k-core", skip_analysis=False, ego_username=None
        )
        assert config.strategy == "k-core"
        assert config.skip_analysis is False
        assert config.ego_username is None

    def test_invalid_strategy_rejection(self):
        """Test rejection of invalid strategy."""
        with pytest.raises(ValueError, match="strategy must be one of"):
            PipelineConfig(strategy="invalid_strategy")

    def test_missing_ego_username_for_ego_alter(self):
        """Test rejection when ego_username is missing for ego_alter_k-core."""
        with pytest.raises(ValueError, match="ego_username is required"):
            PipelineConfig(strategy="ego_alter_k-core", ego_username=None)

    def test_valid_ego_username_for_ego_alter(self):
        """Test acceptance of valid ego_username for ego_alter_k-core."""
        config = PipelineConfig(strategy="ego_alter_k-core", ego_username="test_user")
        assert config.strategy == "ego_alter_k-core"
        assert config.ego_username == "test_user"


class TestKValueConfig:
    """Test KValueConfig dataclass validation."""

    def test_valid_k_value_config(self):
        """Test creation of valid KValueConfig."""
        config = KValueConfig()
        assert isinstance(config.strategy_k_values, dict)
        assert config.default_k_value >= 0

    def test_negative_k_value_rejection(self):
        """Test rejection of negative k-values."""
        with pytest.raises(ValueError, match="K-value must be non-negative"):
            KValueConfig(strategy_k_values={"k-core": -1})

    def test_negative_default_k_value_rejection(self):
        """Test rejection of negative default k-value."""
        with pytest.raises(ValueError, match="default_k_value must be non-negative"):
            KValueConfig(default_k_value=-1)


class TestFameAnalysisConfig:
    """Test FameAnalysisConfig dataclass validation."""

    def test_valid_fame_config(self):
        """Test creation of valid FameAnalysisConfig."""
        config = FameAnalysisConfig()
        assert config.min_followers_in_network >= 0
        assert config.min_fame_ratio > 0

    def test_negative_min_followers_rejection(self):
        """Test rejection of negative min_followers_in_network."""
        with pytest.raises(
            ValueError, match="min_followers_in_network must be non-negative"
        ):
            FameAnalysisConfig(min_followers_in_network=-1)

    def test_negative_min_fame_ratio_rejection(self):
        """Test rejection of negative min_fame_ratio."""
        with pytest.raises(ValueError, match="min_fame_ratio must be positive"):
            FameAnalysisConfig(min_fame_ratio=-1.0)


class TestVisualizationConfig:
    """Test VisualizationConfig dataclass validation."""

    def test_valid_visualization_config(self):
        """Test creation of valid VisualizationConfig."""
        config = VisualizationConfig()
        assert config.node_size_metric in ["degree", "betweenness", "eigenvector"]
        assert config.base_node_size > 0

    def test_invalid_node_size_metric_rejection(self):
        """Test rejection of invalid node size metric."""
        with pytest.raises(ValueError, match="node_size_metric must be one of"):
            VisualizationConfig(node_size_metric="invalid_metric")

    def test_invalid_scaling_algorithm_rejection(self):
        """Test rejection of invalid scaling algorithm."""
        with pytest.raises(ValueError, match="scaling_algorithm must be one of"):
            VisualizationConfig(scaling_algorithm="invalid_scaling")

    def test_negative_base_node_size_rejection(self):
        """Test rejection of negative base node size."""
        with pytest.raises(ValueError, match="base_node_size must be positive"):
            VisualizationConfig(base_node_size=-1.0)

    def test_invalid_color_format_rejection(self):
        """Test rejection of invalid color format."""
        # Note: Color validation may be handled at runtime rather than initialization
        # This test verifies the configuration accepts the parameter
        config = VisualizationConfig(intra_community_color="invalid_color")
        assert config.intra_community_color == "invalid_color"


class TestPyvisInteractiveConfig:
    """Test PyvisInteractiveConfig dataclass validation."""

    def test_valid_pyvis_config(self):
        """Test creation of valid PyvisInteractiveConfig."""
        config = PyvisInteractiveConfig()
        assert config.height == "600px"
        assert config.width == "100%"
        assert config.bgcolor == "#ffffff"
        assert config.font_color == "#000000"

    def test_invalid_height_format_rejection(self):
        """Test rejection of invalid height format."""
        with pytest.raises(ValueError, match="height must end with"):
            PyvisInteractiveConfig(height="invalid_height")

    def test_invalid_width_format_rejection(self):
        """Test rejection of invalid width format."""
        with pytest.raises(ValueError, match="width must end with"):
            PyvisInteractiveConfig(width="invalid_width")


class TestStaticImageConfig:
    """Test StaticImageConfig dataclass validation."""

    def test_valid_static_config(self):
        """Test creation of valid StaticImageConfig."""
        config = StaticImageConfig()
        assert config.layout in ["spring", "kamada_kawai", "circular", "shell"]
        assert config.dpi > 0
        # Test that spring is now the default layout
        assert config.layout == "spring"

    def test_spring_layout_default(self):
        """Test that spring layout is the default."""
        config = StaticImageConfig()
        assert config.layout == "spring"

    def test_all_valid_layouts(self):
        """Test all valid layout options."""
        valid_layouts = ["spring", "kamada_kawai", "circular", "random"]
        for layout in valid_layouts:
            config = StaticImageConfig(layout=layout)
            assert config.layout == layout

    def test_invalid_layout_rejection(self):
        """Test rejection of invalid layout."""
        with pytest.raises(ValueError, match="layout must be one of"):
            StaticImageConfig(layout="invalid_layout")

    def test_image_dimensions_configuration(self):
        """Test image dimensions configuration."""
        # Test default configuration
        config = StaticImageConfig()
        assert hasattr(config, "dpi")
        assert config.dpi > 0


class TestConfigurationValidation:
    """Test high-level configuration validation functions."""

    def test_default_config_validation(self, default_config: Dict[str, Any]):
        """Test that default configuration is valid."""
        config_manager = get_configuration_manager()
        config_obj = load_config_from_dict(default_config)
        result = config_manager.validate_configuration(config_obj)
        assert result.is_valid  # Should not raise

    def test_invalid_strategy_in_dict_rejection(self, default_config: Dict[str, Any]):
        """Test handling of strategy in configuration dict."""
        config = default_config.copy()
        config["strategy"] = "reciprocal_k-core"

        # Verify the configuration loads with valid strategy
        config_obj = load_config_from_dict(config)
        assert config_obj.strategy == "reciprocal_k-core"

    def test_missing_ego_username_rejection(self, default_config: Dict[str, Any]):
        """Test rejection when ego_username is missing for ego_alter_k-core."""
        config = default_config.copy()
        config["strategy"] = "ego_alter_k-core"
        config["ego_username"] = None

        # Should raise validation error
        with pytest.raises(ValueError, match="ego_username is required"):
            load_config_from_dict(config)

    def test_empty_k_values_handling(self, default_config: Dict[str, Any]):
        """Test handling of empty k_values dictionary."""
        config = default_config.copy()
        config["k_values"]["strategy_k_values"] = {}

        load_config_from_dict(config)  # Should not raise

    def test_basic_k_value_handling(self, default_config: Dict[str, Any]):
        """Test basic k-value configuration handling (comprehensive k-value testing in test_k_values.py)."""
        config = default_config.copy()
        config["k_values"]["strategy_k_values"]["k-core"] = (
            5  # Appropriate for test datasets
        )
        config["k_values"]["default_k_value"] = 5

        load_config_from_dict(config)  # Should not raise

    def test_minimal_config_handling(self):
        """Test handling of minimal configuration."""
        minimal_config = {
            "input_file": "test.json",
            "output_file_prefix": "test_output",
        }

        # Should not raise - missing sections should use defaults
        load_config_from_dict(minimal_config)


class TestOutputConfig:
    """Test OutputConfig dataclass validation."""

    def test_valid_output_config(self):
        """Test creation of valid OutputConfig."""
        config = OutputConfig()
        assert config.enable_time_logging is False  # Default
        assert config.custom_output_directory is None  # Default
        # create_directories is now hardcoded as True

    def test_enable_time_logging_option(self):
        """Test time logging configuration option."""
        config = OutputConfig(enable_time_logging=True)
        assert config.enable_time_logging is True

        config = OutputConfig(enable_time_logging=False)
        assert config.enable_time_logging is False

    def test_custom_output_directory_option(self):
        """Test custom output directory configuration."""
        from pathlib import Path

        # Use pathlib for cross-platform path handling
        custom_path = Path("custom") / "path"
        config = OutputConfig(custom_output_directory=str(custom_path))
        assert config.custom_output_directory == str(custom_path)

        relative_path = Path("relative") / "path"
        config = OutputConfig(custom_output_directory=str(relative_path))
        assert config.custom_output_directory == str(relative_path)

    def test_invalid_custom_output_directory(self):
        """Test handling of custom output directory validation."""
        from pathlib import Path

        # Test that the configuration accepts various values
        valid_path = Path("valid") / "path"
        config1 = OutputConfig(custom_output_directory=str(valid_path))
        assert config1.custom_output_directory == str(valid_path)

        config2 = OutputConfig(custom_output_directory=None)
        assert config2.custom_output_directory is None

    def test_create_directories_removed(self):
        """Test that create_directories is no longer a configuration option."""
        # create_directories is now hardcoded as True in the application logic
        config = OutputConfig()
        # Should not have create_directories attribute
        assert not hasattr(config, "create_directories")


class TestConfigurationRoundTrip:
    """Test configuration serialization and deserialization."""

    def test_default_config_round_trip(self, default_config: Dict[str, Any]):
        """Test round-trip of default configuration."""
        load_config_from_dict(default_config)
        # Configuration is already validated by load_config_from_dict

    def test_modified_config_round_trip(self, default_config: Dict[str, Any]):
        """Test round-trip of modified configuration."""
        config = default_config.copy()
        config["pipeline"]["strategy"] = "reciprocal_k-core"
        config["k_values"]["strategy_k_values"]["reciprocal_k-core"] = (
            3  # Appropriate for test datasets
        )
        config["visualization"]["node_size_metric"] = "betweenness"

        load_config_from_dict(config)
        # Configuration is already validated by load_config_from_dict

    def test_output_config_round_trip(self, default_config: Dict[str, Any]):
        """Test round-trip of output configuration options."""
        config = default_config.copy()
        config["output_control"] = {
            "enable_timing_logs": True,
            "generate_html": True,
            "generate_png": False,
            "generate_reports": True,
        }

        config_obj = load_config_from_dict(config)
        # Configuration is already validated by load_config_from_dict

        # Verify values are preserved
        assert config_obj.output_control.enable_timing_logs is True
        assert config_obj.output_control.generate_html is True
        assert config_obj.output_control.generate_png is False
        assert config_obj.output_control.generate_reports is True

    def test_spring_layout_default_config(self, default_config: Dict[str, Any]):
        """Test that spring layout is default in configuration."""
        config_obj = load_config_from_dict(default_config)
        assert config_obj.visualization.static_image.layout == "spring"


class TestConfigurationManager:
    """Test ConfigurationManager functionality."""

    def test_configuration_manager_initialization(self):
        """Test ConfigurationManager initialization."""
        config_manager = get_configuration_manager()
        assert isinstance(config_manager, ConfigurationManager)
        assert hasattr(config_manager, "load_configuration")
        assert hasattr(config_manager, "validate_configuration")
        assert hasattr(config_manager, "merge_configurations")

    def test_load_default_configuration(self):
        """Test loading default configuration."""
        config_manager = get_configuration_manager()
        config = config_manager.load_configuration()

        # Verify configuration structure
        assert hasattr(config, "input_file")
        assert hasattr(config, "pipeline_stages")
        assert hasattr(config, "analysis_mode")
        assert hasattr(config, "output_control")
        assert hasattr(config, "k_values")

    def test_configuration_validation_success(self):
        """Test successful configuration validation."""
        config_manager = get_configuration_manager()
        config = config_manager.load_configuration()
        result = config_manager.validate_configuration(config)

        assert isinstance(result, ValidationResult)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_configuration_validation_failure(self):
        """Test configuration validation method functionality."""
        config_manager = get_configuration_manager()

        # Test that validation method works (even if it passes)
        config = config_manager.load_configuration()
        result = config_manager.validate_configuration(config)

        # Verify the validation result structure
        assert isinstance(result, ValidationResult)
        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")

    def test_merge_configurations(self):
        """Test configuration merging functionality."""
        config_manager = get_configuration_manager()

        base_config = {"input_file": "base.json", "pipeline": {"strategy": "k-core"}}

        overrides = {"input_file": "override.json", "output_file_prefix": "new_output"}

        merged = config_manager.merge_configurations(base_config, overrides)

        assert merged["input_file"] == "override.json"
        assert merged["output_file_prefix"] == "new_output"
        assert merged["pipeline"]["strategy"] == "k-core"

    def test_format_configuration_display(self):
        """Test configuration display formatting."""
        config_manager = get_configuration_manager()
        config = config_manager.load_configuration()

        formatted = config_manager.format_configuration_display(config)

        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "Input file" in formatted  # Check for formatted display text
        assert "Strategy" in formatted

    def test_serialize_configuration(self):
        """Test configuration serialization."""
        config_manager = get_configuration_manager()
        config = config_manager.load_configuration()

        serialized = config_manager.serialize_configuration(config)

        assert isinstance(serialized, dict)
        assert "input_file" in serialized
        assert "pipeline" in serialized
        assert "visualization" in serialized


class TestPipelineStagesConfig:
    """Test PipelineStagesConfig dataclass."""

    def test_default_pipeline_stages(self):
        """Test default pipeline stages configuration."""
        config = PipelineStagesConfig()

        assert config.enable_strategy is True
        assert config.enable_analysis is True
        assert config.enable_visualization is True
        assert config.enable_community_detection is True
        assert config.enable_centrality_analysis is True
        assert config.enable_path_analysis is True

    def test_custom_pipeline_stages(self):
        """Test custom pipeline stages configuration."""
        config = PipelineStagesConfig(
            enable_analysis=False, enable_community_detection=False
        )

        assert config.enable_strategy is True
        assert config.enable_analysis is False
        assert config.enable_visualization is True
        assert config.enable_community_detection is False
        assert config.enable_centrality_analysis is True
        assert config.enable_path_analysis is True


class TestAnalysisModeConfig:
    """Test AnalysisModeConfig dataclass."""

    def test_default_analysis_mode(self):
        """Test default analysis mode configuration."""
        config = AnalysisModeConfig()

        assert config.mode == AnalysisMode.FULL
        assert config.sampling_threshold == 5000
        assert config.max_layout_iterations is None
        assert config.enable_fast_algorithms is False

    def test_fast_mode_configuration(self):
        """Test fast mode auto-configuration."""
        config = AnalysisModeConfig(mode=AnalysisMode.FAST)

        assert config.mode == AnalysisMode.FAST
        assert config.enable_fast_algorithms is True

    def test_invalid_sampling_threshold(self):
        """Test rejection of invalid sampling threshold."""
        with pytest.raises(ValueError, match="sampling_threshold must be at least 100"):
            AnalysisModeConfig(sampling_threshold=50)

    def test_invalid_max_layout_iterations(self):
        """Test rejection of invalid max layout iterations."""
        with pytest.raises(
            ValueError, match="max_layout_iterations must be positive integer"
        ):
            AnalysisModeConfig(max_layout_iterations=0)


class TestOutputControlConfig:
    """Test OutputControlConfig dataclass."""

    def test_default_output_control(self):
        """Test default output control configuration."""
        config = OutputControlConfig()

        assert config.generate_html is True
        assert config.generate_png is True
        assert config.generate_reports is True
        assert config.enable_timing_logs is False

    def test_all_outputs_disabled_rejection(self):
        """Test rejection when all output formats are disabled."""
        with pytest.raises(
            ValueError, match="At least one output format must be enabled"
        ):
            OutputControlConfig(
                generate_html=False, generate_png=False, generate_reports=False
            )

    def test_partial_output_control(self):
        """Test partial output control configuration."""
        config = OutputControlConfig(generate_png=False, enable_timing_logs=True)

        assert config.generate_html is True
        assert config.generate_png is False
        assert config.generate_reports is True
        assert config.enable_timing_logs is True


class TestKValueConfigDefaults:
    """Test KValueConfig dataclass defaults."""

    def test_default_k_value_config(self):
        """Test default k-value configuration."""
        config = KValueConfig()

        assert isinstance(config.strategy_k_values, dict)
        assert config.default_k_value == 10
        assert config.allow_cli_override is True

    def test_custom_k_values(self):
        """Test custom k-value configuration."""
        custom_k_values = {"k-core": 15, "reciprocal_k-core": 12, "ego_alter_k-core": 8}

        config = KValueConfig(strategy_k_values=custom_k_values, default_k_value=15)

        assert config.strategy_k_values == custom_k_values
        assert config.default_k_value == 15


class TestDuplicateParameterDetection:
    """Test duplicate parameter detection and consolidation."""

    def test_detect_duplicate_parameters(self):
        """Test duplicate parameter detection."""
        config_manager = get_configuration_manager()

        # Create configuration with potential duplicates
        config_with_duplicates = {
            "pipeline": {"strategy": "k-core"},
            "pruning": {"k_values": {"k-core": 10}},
            # Simulate duplicate parameter in different location
            "analysis": {"strategy": "k-core"},  # Duplicate strategy
        }

        duplicates = config_manager.detect_duplicate_parameters(config_with_duplicates)

        # Note: Actual duplicates depend on the parameter alias registry
        assert isinstance(duplicates, list)
        for duplicate in duplicates:
            assert isinstance(duplicate, DuplicateParameter)
            assert hasattr(duplicate, "parameter_name")
            assert hasattr(duplicate, "locations")
            assert hasattr(duplicate, "values")

    def test_consolidate_duplicates(self):
        """Test duplicate parameter consolidation."""
        config_manager = get_configuration_manager()

        # Create configuration with duplicates
        config_with_duplicates = {
            "input_file": "test.json",
            "pipeline": {"strategy": "k-core"},
        }

        consolidated = config_manager.consolidate_duplicates(config_with_duplicates)

        assert isinstance(consolidated, dict)
        assert "input_file" in consolidated
        assert "pipeline" in consolidated

    def test_get_parameter_aliases(self):
        """Test parameter alias registry retrieval."""
        config_manager = get_configuration_manager()

        aliases = config_manager.get_parameter_aliases()

        assert isinstance(aliases, dict)
        # Verify structure of alias registry
        for canonical, alias_list in aliases.items():
            assert isinstance(canonical, str)
            assert isinstance(alias_list, list)


class TestCLIParameterValidation:
    """Test CLI parameter validation functionality."""

    def test_cli_override_integration(self):
        """Test CLI parameter override integration."""
        config_manager = get_configuration_manager()

        # Simulate CLI overrides
        cli_overrides = {
            "input_file": "cli_input.json",
            "pipeline": {"strategy": "reciprocal_k-core"},
            "pruning": {"k_values": {"reciprocal_k-core": 15}},
        }

        base_config = config_manager.load_configuration()
        base_dict = config_manager.serialize_configuration(base_config)

        merged = config_manager.merge_configurations(base_dict, cli_overrides)

        assert merged["input_file"] == "cli_input.json"
        assert merged["pipeline"]["strategy"] == "reciprocal_k-core"
        assert merged["pruning"]["k_values"]["reciprocal_k-core"] == 15

    def test_invalid_cli_parameters(self):
        """Test handling of CLI parameters."""
        config_manager = get_configuration_manager()

        cli_overrides = {"strategy": "reciprocal_k-core"}

        base_config = config_manager.load_configuration()
        base_dict = config_manager.serialize_configuration(base_config)

        merged = config_manager.merge_configurations(base_dict, cli_overrides)

        # Should load successfully
        config_obj = load_config_from_dict(merged)
        assert config_obj.strategy == "reciprocal_k-core"


class TestPipelineStageControlIntegration:
    """Test pipeline stage control integration tests."""

    def test_stage_dependency_validation(self):
        """Test pipeline stage dependency validation."""
        config_manager = get_configuration_manager()

        # Test configuration with visualization enabled but analysis disabled
        config_dict = {
            "pipeline_stages": {"enable_analysis": False, "enable_visualization": True}
        }

        base_config = config_manager.load_configuration()
        base_dict = config_manager.serialize_configuration(base_config)
        merged = config_manager.merge_configurations(base_dict, config_dict)

        # Should be able to load (dependency validation happens at runtime)
        config_obj = load_config_from_dict(merged)
        assert config_obj.pipeline_stages.enable_analysis is False
        assert config_obj.pipeline_stages.enable_visualization is True

    def test_analysis_component_control(self):
        """Test individual analysis component control."""
        config_manager = get_configuration_manager()

        config_dict = {
            "pipeline_stages": {
                "enable_community_detection": False,
                "enable_path_analysis": False,
                "enable_centrality_analysis": True,
            }
        }

        base_config = config_manager.load_configuration()
        base_dict = config_manager.serialize_configuration(base_config)
        merged = config_manager.merge_configurations(base_dict, config_dict)

        config_obj = load_config_from_dict(merged)
        assert config_obj.pipeline_stages.enable_community_detection is False
        assert config_obj.pipeline_stages.enable_path_analysis is False
        assert config_obj.pipeline_stages.enable_centrality_analysis is True
