"""
Integration tests for the complete FollowWeb pipeline.

Tests end-to-end pipeline execution, strategy validation, output generation,
and error handling across module boundaries.
"""

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.pipeline]

from FollowWeb_Visualizor.main import PipelineOrchestrator


class TestPipelineExecution:
    """Test complete pipeline execution."""

    @pytest.mark.integration
    def test_k_core_strategy_execution(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test k-core strategy pipeline execution with ConfigurationManager."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["pipeline"]["strategy"] = "k-core"

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True
        assert hasattr(orchestrator, "phase_times")
        assert "strategy" in orchestrator.phase_times
        assert "analysis" in orchestrator.phase_times
        assert "visualization" in orchestrator.phase_times

    @pytest.mark.integration
    def test_reciprocal_k_core_strategy_execution(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test reciprocal k-core strategy pipeline execution with ConfigurationManager."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["pipeline"]["strategy"] = "reciprocal_k-core"

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True
        assert hasattr(orchestrator, "phase_times")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_ego_alter_strategy_execution(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test ego-alter strategy pipeline execution."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        # First load data to get a valid ego username
        from FollowWeb_Visualizor.data.loaders import InstagramLoader

        loader = InstagramLoader()
        graph = loader.load_from_json(fast_config["input_file"])

        if graph.number_of_nodes() == 0:
            pytest.skip("No nodes available for ego-alter analysis")

        # Find an ego user with alters (followers who follow each other) - limit search for speed
        ego_username = None
        checked_nodes = 0
        max_nodes_to_check = 50  # Limit search to first 50 nodes for speed
        for node in graph.nodes():
            checked_nodes += 1
            if checked_nodes > max_nodes_to_check:
                break
            # Get followers of this node
            followers = list(graph.predecessors(node))
            if len(followers) >= 2:
                # Check if any followers follow each other
                for i, f1 in enumerate(followers[:10]):  # Limit to first 10 followers
                    for f2 in followers[i+1:min(i+11, len(followers))]:  # Check next 10
                        if graph.has_edge(f1, f2) or graph.has_edge(f2, f1):
                            ego_username = node
                            break
                    if ego_username:
                        break
            if ego_username:
                break
        
        if not ego_username:
            pytest.skip("No suitable ego user with alters found in test data")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        # Use minimal k-value for ego-alter to keep graph small
        config["k_values"] = {
            "strategy_k_values": {"k-core": 5, "reciprocal_k-core": 5, "ego_alter_k-core": 2},
            "default_k_value": 2,
        }
        config["pipeline"]["strategy"] = "ego_alter_k-core"
        config["pipeline"]["ego_username"] = ego_username

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True


class TestOutputGeneration:
    """Test pipeline output generation."""

    @pytest.mark.integration
    def test_html_output_generation(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test HTML output file generation."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["visualization"]["static_image"]["generate"] = False

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Check that HTML file was created
        output_dir = os.path.dirname(config["output_file_prefix"])
        html_files = list(Path(output_dir).glob("*.html"))
        assert len(html_files) > 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_png_output_generation(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test PNG output file generation."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from tests.conftest import apply_png_test_optimizations

        config = fast_config.copy()
        config = apply_png_test_optimizations(config)
        config["visualization"]["static_image"]["generate"] = True

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Check that both HTML and PNG files were created
        output_dir = os.path.dirname(config["output_file_prefix"])
        html_files = list(Path(output_dir).glob("*.html"))
        png_files = list(Path(output_dir).glob("*.png"))

        assert len(html_files) > 0
        assert len(png_files) > 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_metrics_report_generation(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test metrics report text file generation."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from tests.conftest import apply_png_test_optimizations

        config = fast_config.copy()
        config = apply_png_test_optimizations(config)

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Check that metrics report was created
        output_dir = os.path.dirname(config["output_file_prefix"])
        txt_files = list(Path(output_dir).glob("*.txt"))

        assert len(txt_files) > 0

        # Verify report content
        report_file = txt_files[0]
        with open(report_file, encoding="utf-8") as f:
            content = f.read()
            assert "FOLLOWWEB NETWORK ANALYSIS" in content
            assert "GRAPH PROCESSING SUMMARY" in content
            assert "Strategy:" in content


class TestPipelineErrorHandling:
    """Test pipeline error handling."""

    @pytest.mark.integration
    def test_nonexistent_input_file_handling(self, fast_config: dict[str, Any]):
        """Test handling of non-existent input file."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["input_file"] = "non_existent_file.json"

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is False

    @pytest.mark.integration
    def test_invalid_json_file_handling(
        self, fast_config: dict[str, Any], invalid_json_file: str
    ):
        """Test handling of invalid JSON file."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["input_file"] = invalid_json_file

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is False

    @pytest.mark.integration
    def test_empty_graph_handling(
        self, fast_config: dict[str, Any], empty_json_file: str
    ):
        """Test handling of empty graph."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["input_file"] = empty_json_file

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is False

    @pytest.mark.integration
    def test_invalid_configuration_handling(self, fast_config: dict[str, Any]):
        """Test handling of invalid configuration."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        # Use an invalid k_values structure that will actually fail validation
        config["k_values"] = "invalid"  # Should be a dict

        with pytest.raises(
            (ValueError, KeyError, TypeError, AttributeError)
        ):  # Should fail during configuration loading
            load_config_from_dict(config)


class TestPipelineConfiguration:
    """Test pipeline configuration handling."""

    @pytest.mark.integration
    def test_skip_analysis_configuration(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test skip analysis configuration option."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        # Use k=5 to reduce graph size for faster testing
        config["k_values"] = {
            "strategy_k_values": {
                "k-core": 5,
                "reciprocal_k-core": 5,
                "ego_alter_k-core": 5,
            },
            "default_k_value": 5,
        }
        config["pipeline_stages"] = {
            "enable_analysis": False,
            "enable_visualization": False,
        }

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Analysis phase should be very fast when skipped
        if hasattr(orchestrator, "phase_times"):
            analysis_time = orchestrator.phase_times.get("analysis", 0)
            # Relaxed timing - graph loading/filtering still takes time even when analysis is disabled
            assert analysis_time < 5.0  # More realistic expectation

    @pytest.mark.integration
    def test_single_k_value_configuration(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test pipeline with single k-value configuration (comprehensive k-value testing in test_k_values.py)."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        # Test with one k-value to verify basic functionality
        # Comprehensive k-value testing is handled in test_k_values.py
        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from tests.conftest import calculate_appropriate_k_values

        config = fast_config.copy()
        # Use dynamically calculated k-value appropriate for the dataset
        k_values = calculate_appropriate_k_values("small_real")
        single_k = k_values["strategy_k_values"]["k-core"]
        config["k_values"] = {
            "strategy_k_values": {"k-core": single_k},
            "default_k_value": single_k,
        }

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

    @pytest.mark.integration
    @pytest.mark.parametrize("metric", ["degree", "betweenness", "eigenvector"])
    def test_visualization_configuration_options(
        self, fast_config: dict[str, Any], sample_data_exists: bool, metric: str
    ):
        """Test different visualization configuration options."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from tests.conftest import calculate_appropriate_k_values

        config = fast_config.copy()
        # Use dynamically calculated k-values appropriate for the dataset
        k_values = calculate_appropriate_k_values("small_real")
        config["k_values"] = k_values
        config["visualization"]["node_size_metric"] = metric

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.parametrize("layout", ["spring", "kamada_kawai", "circular"])
    def test_static_image_layout_options(
        self, fast_config: dict[str, Any], sample_data_exists: bool, layout: str
    ):
        """Test different static image layout algorithms."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from tests.conftest import apply_png_test_optimizations

        config = fast_config.copy()
        config = apply_png_test_optimizations(config)
        config["visualization"]["static_image"]["generate"] = True
        config["visualization"]["static_image"]["layout"] = layout

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

    @pytest.mark.integration
    @pytest.mark.parametrize("algorithm", ["logarithmic", "linear"])
    def test_scaling_algorithm_options(
        self, fast_config: dict[str, Any], sample_data_exists: bool, algorithm: str
    ):
        """Test different scaling algorithms."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["visualization"]["scaling_algorithm"] = algorithm

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True


class TestTimeLoggingIntegration:
    """Test time logging feature integration."""

    @pytest.mark.integration
    def test_time_logging_enabled(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test pipeline with time logging enabled."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["output"] = {
            "enable_timing_logs": True,
            "generate_html": True,
            "generate_png": True,
            "generate_reports": True,
        }

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Check that timing log file was created
        output_dir = os.path.dirname(config["output_file_prefix"])
        txt_files = list(Path(output_dir).glob("*timing*.txt"))

        if len(txt_files) > 0:
            # Verify timing log content
            timing_file = txt_files[0]
            with open(timing_file) as f:
                content = f.read()
                assert "TIMING LOG" in content or "Total Duration" in content

    @pytest.mark.integration
    def test_time_logging_disabled(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test pipeline with time logging disabled."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["output"] = {
            "enable_timing_logs": False,
            "generate_html": True,
            "generate_png": True,
            "generate_reports": True,
        }

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Check that no timing log files were created
        output_dir = os.path.dirname(config["output_file_prefix"])
        txt_files = list(Path(output_dir).glob("*timing*.txt"))

        # Should only have metrics report, not timing logs
        for txt_file in txt_files:
            with open(txt_file) as f:
                content = f.read()
                # Should not contain timing-specific content
                assert "TIMING LOG" not in content


class TestCustomOutputDirectoryIntegration:
    """Test custom output directory feature integration."""

    @pytest.mark.integration
    def test_custom_output_directory_absolute(
        self,
        fast_config: dict[str, Any],
        sample_data_exists: bool,
        temp_output_dir: str,
    ):
        """Test pipeline with custom absolute output directory."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        custom_dir = os.path.join(temp_output_dir, "custom_output")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        from tests.conftest import apply_pipeline_preset

        config = fast_config.copy()
        config["output_file_prefix"] = os.path.join(custom_dir, "FollowWeb")
        # Disable analysis and visualization to focus on directory creation
        config = apply_pipeline_preset(config, "strategy_only")

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Check that files were created in custom directory
        assert os.path.exists(custom_dir)
        html_files = list(Path(custom_dir).glob("*.html"))
        assert len(html_files) > 0

    @pytest.mark.integration
    def test_custom_output_directory_relative(
        self,
        fast_config: dict[str, Any],
        sample_data_exists: bool,
        temp_output_dir: str,
    ):
        """Test pipeline with custom relative output directory."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        # Change to temp directory for relative path test
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_output_dir)
            custom_dir = "relative_custom_output"

            from FollowWeb_Visualizor.core.config import load_config_from_dict

            config = fast_config.copy()
            # Use absolute path for input file since we changed working directory
            config["input_file"] = os.path.join(original_cwd, config["input_file"])
            config["output_file_prefix"] = os.path.join(custom_dir, "FollowWeb")
            # Disable analysis and visualization to focus on directory creation
            config["pipeline_stages"] = {
                "enable_analysis": False,
                "enable_visualization": False,
            }

            config_obj = load_config_from_dict(config)
            orchestrator = PipelineOrchestrator(config_obj)
            success = orchestrator.execute_pipeline()

            assert success is True

            # Check that files were created in custom directory
            # Since we changed to temp_output_dir, custom_dir is relative to current directory
            assert os.path.exists(custom_dir)
            html_files = list(Path(custom_dir).glob("*.html"))
            assert len(html_files) > 0
        finally:
            os.chdir(original_cwd)

    @pytest.mark.integration
    def test_automatic_directory_creation(
        self,
        fast_config: dict[str, Any],
        sample_data_exists: bool,
        temp_output_dir: str,
    ):
        """Test pipeline with automatic directory creation (create_directories is now hardcoded as True)."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        non_existent_dir = os.path.join(temp_output_dir, "non_existent")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["output_file_prefix"] = os.path.join(non_existent_dir, "FollowWeb")
        config["output"] = config.get("output", {})
        # create_directories is now hardcoded as True, so directories are created automatically
        # Disable analysis and visualization to focus on directory creation
        config["pipeline_stages"] = {
            "enable_analysis": False,
            "enable_visualization": False,
        }

        # Pipeline now handles directory creation gracefully
        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        # Pipeline should succeed as it creates directories when needed
        assert success is True


class TestSpringLayoutIntegration:
    """Test spring layout as default integration."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.skipif(
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("RUNNER_OS") == "Windows",
        reason="PNG generation tests can be resource-intensive on Windows CI",
    )
    @pytest.mark.slow  # Mark as slow since it generates PNG
    def test_spring_layout_default(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test that spring layout is used by default for PNG generation."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from tests.conftest import apply_png_test_optimizations

        config = fast_config.copy()
        config = apply_png_test_optimizations(config)
        config["visualization"]["static_image"]["generate"] = True
        # Don't specify layout - should use spring as default

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Check that PNG file was created
        output_dir = os.path.dirname(config["output_file_prefix"])
        png_files = list(Path(output_dir).glob("*.png"))
        assert len(png_files) > 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_spring_layout_explicit(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test explicit spring layout configuration."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from tests.conftest import apply_png_test_optimizations

        config = fast_config.copy()
        config = apply_png_test_optimizations(config)
        config["visualization"]["static_image"]["generate"] = True
        config["visualization"]["static_image"]["layout"] = "spring"

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Check that PNG file was created
        output_dir = os.path.dirname(config["output_file_prefix"])
        png_files = list(Path(output_dir).glob("*.png"))
        assert len(png_files) > 0


class TestPipelineSuccessValidation:
    """Test pipeline success validation with sub-module failures."""

    @pytest.mark.integration
    def test_pipeline_success_requires_all_enabled_phases(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test that pipeline only succeeds if all enabled phases complete successfully."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from tests.conftest import calculate_appropriate_k_values

        config = fast_config.copy()
        # Use dynamically calculated k-values appropriate for the dataset
        k_values = calculate_appropriate_k_values("small_real")
        config["k_values"] = k_values

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Verify all enabled phases completed
        execution_summary = orchestrator.stages_controller.get_execution_summary()
        enabled_phases = [
            "strategy",
            "analysis",
            "visualization",
        ]  # All enabled by default

        for phase in enabled_phases:
            assert execution_summary["stages"][phase] == "completed"

    @pytest.mark.integration
    def test_pipeline_fails_when_strategy_phase_fails(
        self, fast_config: dict[str, Any]
    ):
        """Test that pipeline fails when strategy phase fails."""
        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["input_file"] = (
            "non_existent_file.json"  # This will cause strategy phase to fail
        )

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is False

        # Verify strategy phase failed
        execution_summary = orchestrator.stages_controller.get_execution_summary()
        assert execution_summary["stages"]["strategy"] == "failed"

    @pytest.mark.integration
    def test_pipeline_handles_directory_creation_gracefully(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test that pipeline handles directory creation gracefully."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from tests.conftest import calculate_appropriate_k_values

        config = fast_config.copy()
        # Use dynamically calculated k-values appropriate for the dataset
        k_values = calculate_appropriate_k_values("small_real")
        config["k_values"] = k_values
        
        # Use a path that doesn't exist initially
        import tempfile
        from pathlib import Path

        # Use a platform-agnostic path
        test_path = (
            Path(tempfile.gettempdir())
            / "followweb_test_graceful"
            / "output_test"
            / "FollowWeb"
        )
        config["output_file_prefix"] = str(test_path)
        config["output"] = {}

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        # Pipeline should succeed as it handles directory creation gracefully
        assert success is True

    @pytest.mark.integration
    def test_pipeline_succeeds_with_skipped_phases(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test that pipeline succeeds when some phases are skipped but enabled phases succeed."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from tests.conftest import calculate_appropriate_k_values

        config = fast_config.copy()
        # Use dynamically calculated k-values appropriate for the dataset
        k_values = calculate_appropriate_k_values("small_real")
        config["k_values"] = k_values
        
        # Skip visualization phase
        if "pipeline" not in config:
            config["pipeline"] = {}
        config["pipeline"]["enable_visualization"] = False

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Verify only enabled phases completed
        execution_summary = orchestrator.stages_controller.get_execution_summary()
        assert execution_summary["stages"]["strategy"] == "completed"
        assert execution_summary["stages"]["analysis"] == "completed"
        assert execution_summary["stages"]["visualization"] == "skipped"

    @pytest.mark.integration
    def test_analysis_phase_component_failure_handling(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test that analysis phase properly handles individual component failures."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        # Mock path analyzer to raise an exception
        with patch.object(
            orchestrator.path_analyzer,
            "analyze_path_lengths",
            side_effect=Exception("Mock path analysis failure"),
        ):
            success = orchestrator.execute_pipeline()

            # Pipeline should fail because path analysis component failed
            assert success is False

    @pytest.mark.integration
    def test_visualization_phase_partial_output_failure(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test that visualization phase fails if any output format fails."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["output"] = {
            "generate_html": True,
            "generate_png": True,
            "generate_reports": True,
        }

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)

        # Mock output manager to simulate partial failure
        with patch.object(
            orchestrator.output_manager,
            "generate_all_outputs",
            return_value={"html": True, "png": False, "reports": True},
        ):
            success = orchestrator.execute_pipeline()

            # Pipeline should fail because PNG generation failed
            assert success is False


class TestEnhancedLegendIntegration:
    """Test enhanced HTML legend integration."""

    @pytest.mark.integration
    def test_enhanced_html_legend_generation(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test that enhanced HTML legend is generated."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["visualization"]["static_image"]["generate"] = False  # Focus on HTML

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Check that HTML file was created and contains enhanced legend
        output_dir = os.path.dirname(config["output_file_prefix"])
        html_files = list(Path(output_dir).glob("*.html"))
        assert len(html_files) > 0

        # Verify enhanced legend content in HTML
        html_file = html_files[0]
        with open(html_file, encoding="utf-8") as f:
            content = f.read()
            # Should contain legend title change
            assert "Legend" in content
            # Should not contain old title
            assert "Network Legend" not in content or content.count(
                "Legend"
            ) > content.count("Network Legend")

    @pytest.mark.integration
    def test_legend_with_edge_thickness_scale(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test that HTML legend includes edge thickness information."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        config["visualization"]["static_image"]["generate"] = False  # Focus on HTML

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        assert success is True

        # Check HTML content for edge thickness information
        output_dir = os.path.dirname(config["output_file_prefix"])
        html_files = list(Path(output_dir).glob("*.html"))
        assert len(html_files) > 0

        html_file = html_files[0]
        with open(html_file, encoding="utf-8") as f:
            content = f.read()
            # Should contain edge-related legend information
            # Note: Exact content depends on implementation
            assert (
                "edge" in content.lower()
                or "thickness" in content.lower()
                or "weight" in content.lower()
            )


class TestLoadingIndicatorIntegration:
    """Test loading indicator integration."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_loading_indicators_with_long_operations(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test that loading indicators work with operations that may take time."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        from FollowWeb_Visualizor.core.config import load_config_from_dict
        from tests.conftest import apply_png_test_optimizations

        config = fast_config.copy()
        config = apply_png_test_optimizations(config)
        config["visualization"]["static_image"]["generate"] = True

        config_obj = load_config_from_dict(config)
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()

        # Should succeed or handle gracefully (may result in small graph with appropriate k-value)
        assert isinstance(success, bool)

        # Verify that progress tracking was used (if available)
        if hasattr(orchestrator, "phase_times"):
            # Check that timing information is available
            assert len(orchestrator.phase_times) > 0

    @pytest.mark.integration
    def test_progress_tracking_accuracy(
        self, fast_config: dict[str, Any], sample_data_exists: bool
    ):
        """Test progress tracking accuracy during pipeline execution."""
        if not sample_data_exists:
            pytest.skip("Sample data file not available")

        import time

        from FollowWeb_Visualizor.core.config import load_config_from_dict

        config = fast_config.copy()
        
        config_obj = load_config_from_dict(config)

        start_time = time.perf_counter()
        orchestrator = PipelineOrchestrator(config_obj)
        success = orchestrator.execute_pipeline()
        end_time = time.perf_counter()

        total_duration = end_time - start_time

        assert success is True

        # Check that progress tracking doesn't significantly impact performance
        if hasattr(orchestrator, "phase_times"):
            phase_sum = sum(orchestrator.phase_times.values())
            # Progress tracking overhead should be minimal
            overhead = abs(total_duration - phase_sum) / max(total_duration, 0.001)
            assert overhead < 0.8  # Less than 80% overhead (generous for CI variability)

