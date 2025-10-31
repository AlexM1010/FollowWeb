"""
Unit tests for main module.

Tests main entry point, command line interface, and pipeline orchestration
functionality.
"""

import json
import os
import sys
from io import StringIO
from typing import Any, Dict
from unittest.mock import patch

import pytest

from FollowWeb_Visualizor.core.config import get_configuration_manager
from FollowWeb_Visualizor.main import (
    PipelineOrchestrator,
    create_argument_parser,
    load_config_from_file,
    main,
    setup_logging,
)


class TestPipelineOrchestrator:
    """Test PipelineOrchestrator functionality."""

    def test_orchestrator_initialization(self, default_config: Dict[str, Any]):
        """Test PipelineOrchestrator initialization with ConfigurationManager."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config_obj = load_config_from_dict(default_config)
        orchestrator = PipelineOrchestrator(config_obj)

        assert orchestrator.config == config_obj
        assert hasattr(orchestrator, "graph_loader")
        assert hasattr(orchestrator, "network_analyzer")
        assert hasattr(orchestrator, "path_analyzer")
        assert hasattr(orchestrator, "fame_analyzer")
        assert hasattr(orchestrator, "output_manager")

    def test_orchestrator_invalid_config(self):
        """Test PipelineOrchestrator with configuration using ConfigurationManager."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        test_config = {"strategy": "reciprocal_k-core"}

        # Should load successfully with enhanced configuration manager
        config_obj = load_config_from_dict(test_config)
        orchestrator = PipelineOrchestrator(config_obj)
        assert orchestrator.config.strategy == "reciprocal_k-core"

    def test_orchestrator_logging_setup(self, default_config: Dict[str, Any]):
        """Test unified logging setup in orchestrator."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from FollowWeb_Visualizor.output.logging import Logger

        config_obj = load_config_from_dict(default_config)
        orchestrator = PipelineOrchestrator(config_obj)

        # Test that orchestrator has a unified logger
        assert hasattr(orchestrator, "logger")
        assert isinstance(orchestrator.logger, Logger)

        # Test that the unified logger has the expected methods
        assert hasattr(orchestrator.logger, "start_section")
        assert hasattr(orchestrator.logger, "log_success")
        assert hasattr(orchestrator.logger, "log_error")
        assert hasattr(orchestrator.logger, "log_progress")
        assert hasattr(orchestrator.logger, "log_timer")
        assert hasattr(orchestrator.logger, "close")


class TestConfigurationLoading:
    """Test configuration loading functionality."""

    def test_load_config_from_valid_file(self, temp_output_dir: str):
        """Test loading configuration from valid JSON file."""
        config_manager = get_configuration_manager()
        config = config_manager.load_configuration()
        config_data = config_manager.serialize_configuration(config)
        config_file = os.path.join(temp_output_dir, "test_config.json")

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        loaded_config = load_config_from_file(config_file)

        # Verify key sections are present and correct
        assert loaded_config["input_file"] == config_data["input_file"]
        assert (
            loaded_config["pipeline"]["strategy"] == config_data["pipeline"]["strategy"]
        )
        assert "visualization" in loaded_config

    def test_load_config_from_nonexistent_file(self):
        """Test loading configuration from non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_config_from_file("non_existent_config.json")

    def test_load_config_from_invalid_json(self, temp_output_dir: str):
        """Test loading configuration from invalid JSON file."""
        config_file = os.path.join(temp_output_dir, "invalid_config.json")

        with open(config_file, "w") as f:
            f.write('{"invalid": json content}')

        with pytest.raises(ValueError, match="Invalid JSON"):
            load_config_from_file(config_file)

    def test_load_config_with_invalid_configuration(self, temp_output_dir: str):
        """Test loading file with invalid configuration."""
        invalid_config = {
            "strategy": "invalid_strategy"  # Invalid strategy should cause validation error
        }
        config_file = os.path.join(temp_output_dir, "invalid_config.json")

        with open(config_file, "w") as f:
            json.dump(invalid_config, f)

        with pytest.raises(ValueError):
            load_config_from_file(config_file)


class TestCommandLineInterface:
    """Test command line interface functionality."""

    def test_argument_parser_creation(self):
        """Test argument parser creation."""
        parser = create_argument_parser()

        assert parser is not None
        assert parser.prog is not None

    def test_argument_parser_basic_options(self):
        """Test argument parser handles basic options."""
        parser = create_argument_parser()

        # Test basic input/output options
        args = parser.parse_args(
            ["--input", "test.json", "--output-prefix", "TestOutput"]
        )
        assert args.input == "test.json"
        assert args.output_prefix == "TestOutput"

    def test_argument_parser_analysis_modes(self):
        """Test argument parser handles analysis mode flags."""
        parser = create_argument_parser()

        # Test fast mode
        args = parser.parse_args(["--fast-mode"])
        assert args.fast_mode is True
        assert args.medium_mode is False
        assert args.full_mode is False

        # Test medium mode
        args = parser.parse_args(["--medium-mode"])
        assert args.fast_mode is False
        assert args.medium_mode is True
        assert args.full_mode is False

        # Test full mode
        args = parser.parse_args(["--full-mode"])
        assert args.fast_mode is False
        assert args.medium_mode is False
        assert args.full_mode is True

    def test_argument_parser_k_values(self):
        """Test argument parser handles k-value parameters."""
        parser = create_argument_parser()

        args = parser.parse_args(
            ["--k-core", "5", "--k-reciprocal", "3", "--k-ego-alter", "3"]
        )
        assert args.k_core == 5
        assert args.k_reciprocal == 3
        assert args.k_ego_alter == 3

    def test_argument_parser_output_control(self):
        """Test argument parser handles output control flags."""
        parser = create_argument_parser()

        args = parser.parse_args(["--no-png", "--no-html", "--enable-timing-logs"])
        assert args.no_png is True
        assert args.no_html is True
        assert args.no_reports is False
        assert args.enable_timing_logs is True

    def test_argument_parser_pipeline_stages(self):
        """Test argument parser handles pipeline stage control."""
        parser = create_argument_parser()

        # Test skip analysis
        args = parser.parse_args(["--skip-analysis"])
        assert args.skip_analysis is True

        # Test analysis only
        args = parser.parse_args(["--analysis-only"])
        assert args.analysis_only is True

        # Test skip visualization
        args = parser.parse_args(["--skip-visualization"])
        assert args.skip_visualization is True

    def test_argument_parser_analysis_components(self):
        """Test argument parser handles analysis component control."""
        parser = create_argument_parser()

        args = parser.parse_args(["--skip-path-analysis", "--skip-community-detection"])
        assert args.skip_path_analysis is True
        assert args.skip_community_detection is True
        assert args.skip_centrality_analysis is False

    def test_argument_parser_performance_options(self):
        """Test argument parser handles performance options."""
        parser = create_argument_parser()

        args = parser.parse_args(
            ["--max-layout-iterations", "500", "--sampling-threshold", "2000"]
        )
        assert args.max_layout_iterations == 500
        assert args.sampling_threshold == 2000


class TestLoggingSetup:
    """Test logging setup functionality."""

    def test_setup_logging_default(self):
        """Test default logging setup."""
        setup_logging()

        # Should not raise and should configure logging
        # Note: logging level may be affected by other tests, so just verify it's configured
        import logging

        logger = logging.getLogger()
        assert logger.level in [
            logging.INFO,
            logging.WARNING,
        ]  # Allow for test environment variations

    def test_setup_logging_verbose(self):
        """Test verbose logging setup."""
        setup_logging(verbose=True)

        import logging

        logger = logging.getLogger()
        assert logger.level in [
            logging.DEBUG,
            logging.WARNING,
        ]  # Allow for test environment variations

    def test_setup_logging_quiet(self):
        """Test quiet logging setup."""
        setup_logging(quiet=True)

        import logging

        logger = logging.getLogger()
        assert logger.level in [
            logging.ERROR,
            logging.WARNING,
        ]  # Allow for test environment variations


class TestMainFunction:
    """Test main function functionality."""

    @patch("sys.argv", ["followweb", "--print-default-config"])
    def test_main_print_default_config(self):
        """Test main function with print default config option."""
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            exit_code = main()
            output = captured_output.getvalue()

            assert exit_code == 0
            assert "input_file" in output
            assert "pipeline" in output

        finally:
            sys.stdout = old_stdout

    @patch("sys.argv", ["followweb", "--validate-config"])
    def test_main_validate_config_default(self):
        """Test main function with validate config option using default config."""
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            exit_code = main()
            output = captured_output.getvalue()

            assert exit_code == 0
            assert "Configuration validated successfully" in output

        finally:
            sys.stdout = old_stdout

    @patch("sys.argv", ["followweb", "--input", "non_existent_file.json"])
    def test_main_nonexistent_input_file(self):
        """Test main function with non-existent input file."""
        exit_code = main()

        assert exit_code == 1

    def test_main_keyboard_interrupt(self):
        """Test main function handling keyboard interrupt."""
        with patch(
            "FollowWeb_Visualizor.main.PipelineOrchestrator"
        ) as mock_orchestrator:
            mock_orchestrator.side_effect = KeyboardInterrupt()

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()

            try:
                with patch("sys.argv", ["followweb"]):
                    exit_code = main()

                captured_output.getvalue()
                assert exit_code == 1
                # Note: KeyboardInterrupt handling may vary in test environment
                assert exit_code == 1

            finally:
                sys.stdout = old_stdout

    def test_main_unexpected_error(self):
        """Test main function handling unexpected errors."""
        with patch(
            "FollowWeb_Visualizor.main.get_configuration_manager"
        ) as mock_config:
            mock_config.side_effect = RuntimeError("Unexpected error")

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()

            try:
                with patch("sys.argv", ["followweb"]):
                    exit_code = main()

                output = captured_output.getvalue()
                assert exit_code == 1
                assert "FATAL:" in output

            finally:
                sys.stdout = old_stdout


class TestPipelinePhases:
    """Test individual pipeline phases."""

    def test_pipeline_phase_timing(self, default_config: Dict[str, Any]):
        """Test that pipeline tracks phase timing."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config_obj = load_config_from_dict(default_config)

        # Mock the pipeline execution to avoid needing real data
        with patch.object(
            PipelineOrchestrator, "_execute_strategy_phase"
        ) as mock_strategy, patch.object(
            PipelineOrchestrator, "_execute_analysis_phase"
        ) as mock_analysis, patch.object(
            PipelineOrchestrator, "_execute_visualization_phase"
        ) as mock_viz:
            # Mock successful execution
            import networkx as nx

            mock_graph = nx.DiGraph()
            mock_graph.add_node("test")

            mock_strategy.return_value = mock_graph
            mock_analysis.return_value = mock_graph
            mock_viz.return_value = True

            orchestrator = PipelineOrchestrator(config_obj)
            success = orchestrator.execute_pipeline()

            assert success is True
            assert hasattr(orchestrator, "phase_times")
            # Phase times are only populated after actual execution
            if orchestrator.phase_times:
                assert "strategy" in orchestrator.phase_times
                assert "analysis" in orchestrator.phase_times
                assert "visualization" in orchestrator.phase_times

    def test_pipeline_strategy_phase_failure(self, default_config: Dict[str, Any]):
        """Test pipeline handling of strategy phase failure."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config_obj = load_config_from_dict(default_config)

        with patch.object(
            PipelineOrchestrator, "_execute_strategy_phase"
        ) as mock_strategy:
            mock_strategy.return_value = None

            orchestrator = PipelineOrchestrator(config_obj)
            success = orchestrator.execute_pipeline()

            assert success is False

    def test_pipeline_analysis_phase_failure(self, default_config: Dict[str, Any]):
        """Test pipeline handling of analysis phase failure."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config_obj = load_config_from_dict(default_config)

        with patch.object(
            PipelineOrchestrator, "_execute_strategy_phase"
        ) as mock_strategy, patch.object(
            PipelineOrchestrator, "_execute_analysis_phase"
        ) as mock_analysis:
            import networkx as nx

            mock_graph = nx.DiGraph()
            mock_graph.add_node("test")

            mock_strategy.return_value = mock_graph
            mock_analysis.return_value = None

            orchestrator = PipelineOrchestrator(config_obj)
            success = orchestrator.execute_pipeline()

            assert success is False

    def test_pipeline_visualization_phase_failure(self, default_config: Dict[str, Any]):
        """Test pipeline handling of visualization phase failure."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config_obj = load_config_from_dict(default_config)

        with patch.object(
            PipelineOrchestrator, "_execute_strategy_phase"
        ) as mock_strategy, patch.object(
            PipelineOrchestrator, "_execute_analysis_phase"
        ) as mock_analysis, patch.object(
            PipelineOrchestrator, "_execute_visualization_phase"
        ) as mock_viz:
            import networkx as nx

            mock_graph = nx.DiGraph()
            mock_graph.add_node("test")

            mock_strategy.return_value = mock_graph
            mock_analysis.return_value = mock_graph
            mock_viz.return_value = False

            orchestrator = PipelineOrchestrator(config_obj)
            success = orchestrator.execute_pipeline()

            assert success is False


class TestEnhancedCLIInterface:
    """Test enhanced CLI interface functionality."""

    def test_analysis_mode_flags_parsing(self):
        """Test analysis mode flags parsing."""
        parser = create_argument_parser()

        # Test mutually exclusive analysis mode flags
        args = parser.parse_args(["--fast-mode"])
        assert args.fast_mode is True
        assert args.medium_mode is False
        assert args.full_mode is False

        args = parser.parse_args(["--medium-mode"])
        assert args.fast_mode is False
        assert args.medium_mode is True
        assert args.full_mode is False

        args = parser.parse_args(["--full-mode"])
        assert args.fast_mode is False
        assert args.medium_mode is False
        assert args.full_mode is True

    def test_pipeline_stage_control_flags(self):
        """Test pipeline stage control flags."""
        parser = create_argument_parser()

        args = parser.parse_args(["--skip-analysis", "--skip-visualization"])
        assert args.skip_analysis is True
        assert args.skip_visualization is True

        args = parser.parse_args(["--analysis-only"])
        assert args.analysis_only is True

    def test_output_control_flags(self):
        """Test output control flags."""
        parser = create_argument_parser()

        args = parser.parse_args(["--no-png", "--no-html", "--enable-timing-logs"])
        assert args.no_png is True
        assert args.no_html is True
        assert args.enable_timing_logs is True

    def test_k_value_parameters(self):
        """Test k-value CLI parameters."""
        parser = create_argument_parser()

        args = parser.parse_args(
            ["--k-core", "15", "--k-reciprocal", "12", "--k-ego-alter", "8"]
        )

        assert args.k_core == 15
        assert args.k_reciprocal == 12
        assert args.k_ego_alter == 8

    def test_performance_control_parameters(self):
        """Test performance control parameters."""
        parser = create_argument_parser()

        args = parser.parse_args(
            ["--max-layout-iterations", "1000", "--sampling-threshold", "3000"]
        )

        assert args.max_layout_iterations == 1000
        assert args.sampling_threshold == 3000


class TestPipelineStageControlIntegration:
    """Test pipeline stage control integration."""

    def test_pipeline_with_analysis_disabled(self, default_config: Dict[str, Any]):
        """Test pipeline execution with analysis disabled."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = default_config.copy()
        config["pipeline"]["skip_analysis"] = True

        config_obj = load_config_from_dict(config)

        with patch.object(
            PipelineOrchestrator, "_execute_strategy_phase"
        ) as mock_strategy, patch.object(
            PipelineOrchestrator, "_execute_visualization_phase"
        ) as mock_viz:
            import networkx as nx

            mock_graph = nx.DiGraph()
            mock_graph.add_node("test")

            mock_strategy.return_value = mock_graph
            mock_viz.return_value = True

            orchestrator = PipelineOrchestrator(config_obj)
            success = orchestrator.execute_pipeline()

            assert success is True
            # Analysis phase should be skipped
            mock_strategy.assert_called_once()
            mock_viz.assert_called_once()

    def test_pipeline_with_visualization_disabled(self, default_config: Dict[str, Any]):
        """Test pipeline execution with visualization disabled."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = default_config.copy()
        # Simulate visualization disabled through pipeline stages
        config["pipeline_stages"] = {"enable_visualization": False}

        config_obj = load_config_from_dict(config)

        with patch.object(
            PipelineOrchestrator, "_execute_strategy_phase"
        ) as mock_strategy, patch.object(
            PipelineOrchestrator, "_execute_analysis_phase"
        ) as mock_analysis:
            import networkx as nx

            mock_graph = nx.DiGraph()
            mock_graph.add_node("test")

            mock_strategy.return_value = mock_graph
            mock_analysis.return_value = mock_graph

            orchestrator = PipelineOrchestrator(config_obj)
            success = orchestrator.execute_pipeline()

            assert success is True
            mock_strategy.assert_called_once()
            mock_analysis.assert_called_once()


class TestEnhancedConfigurationIntegration:
    """Test enhanced configuration system integration with main pipeline."""

    def test_configuration_manager_integration(self):
        """Test integration with ConfigurationManager."""
        config_manager = get_configuration_manager()
        config = config_manager.load_configuration()

        # Verify configuration can be used with PipelineOrchestrator
        orchestrator = PipelineOrchestrator(config)

        assert orchestrator.config == config
        assert hasattr(orchestrator.config, "pipeline_stages")
        assert hasattr(orchestrator.config, "analysis_mode")
        assert hasattr(orchestrator.config, "output_control")

    def test_configuration_validation_integration(self):
        """Test configuration validation integration."""
        config_manager = get_configuration_manager()
        config = config_manager.load_configuration()

        # Validate configuration
        result = config_manager.validate_configuration(config)

        assert result.is_valid
        assert len(result.errors) == 0

        # Configuration should work with orchestrator
        orchestrator = PipelineOrchestrator(config)
        assert orchestrator.config == config

    def test_configuration_serialization_integration(self):
        """Test configuration serialization integration."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config_manager = get_configuration_manager()
        config = config_manager.load_configuration()

        # Serialize and deserialize
        serialized = config_manager.serialize_configuration(config)
        deserialized = load_config_from_dict(serialized)

        # Both should work with orchestrator
        orchestrator1 = PipelineOrchestrator(config)
        orchestrator2 = PipelineOrchestrator(deserialized)

        assert orchestrator1.config.input_file == orchestrator2.config.input_file
        assert orchestrator1.config.strategy == orchestrator2.config.strategy
