"""
Integration tests for unified output system.

This module tests the unified output system integration with the actual
FollowWeb pipeline, ensuring that console output and text file content
are properly synchronized with emoji handling in real-world scenarios.
"""

import json
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch

import networkx as nx
import pytest

from FollowWeb_Visualizor.output.formatters import EmojiFormatter
from FollowWeb_Visualizor.output.managers import OutputManager


class TestUnifiedOutputIntegration:
    """Integration tests for unified output system with real pipeline components."""

    @pytest.fixture(autouse=True)
    def setup_method(self, temp_output_dir):
        """Set up test fixtures."""
        self.temp_dir = Path(temp_output_dir)
        self.test_data_file = self.temp_dir / "test_data.json"
        self.output_dir = self.temp_dir / "output"
        self.output_dir.mkdir(exist_ok=True)

        # Create test data
        test_data = [
            {
                "username": "user1",
                "followers": ["user2", "user3"],
                "following": ["user2", "user4"],
            },
            {
                "username": "user2",
                "followers": ["user1", "user3"],
                "following": ["user1", "user3"],
            },
            {
                "username": "user3",
                "followers": ["user1", "user2"],
                "following": ["user2", "user4"],
            },
            {
                "username": "user4",
                "followers": ["user1", "user3"],
                "following": ["user1"],
            },
        ]

        with open(self.test_data_file, "w") as f:
            json.dump(test_data, f)

    def teardown_method(self):
        """Clean up test fixtures."""
        import gc
        import shutil
        import time

        # Force garbage collection to close any open file handles
        gc.collect()

        # Reset emoji level
        EmojiFormatter.set_fallback_level("full")

        if os.path.exists(self.temp_dir):
            # Windows-specific robust cleanup with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    shutil.rmtree(self.temp_dir)
                    break
                except PermissionError:
                    if attempt < max_retries - 1:
                        # Wait a bit and try again
                        time.sleep(0.1)
                        gc.collect()  # Force garbage collection again
                        continue
                    else:
                        # On final attempt, try to make files writable first
                        try:
                            for root, _dirs, files in os.walk(self.temp_dir):
                                for file in files:
                                    file_path = Path(root) / file
                                    try:
                                        file_path.chmod(0o777)
                                    except BaseException:
                                        pass
                            shutil.rmtree(self.temp_dir)
                        except BaseException:
                            # If all else fails, just pass - the temp directory will be cleaned up eventually
                            pass

    def create_test_config(self, emoji_level="full"):
        """Create test configuration with unified output enabled."""
        return {
            "input_file": str(self.test_data_file),
            "output_file_prefix": str(self.output_dir / "TestOutput"),
            "strategy": "k-core",
            "pipeline_stages": {
                "enable_strategy": True,
                "enable_analysis": True,
                "enable_visualization": True,
                "enable_community_detection": True,
                "enable_centrality_analysis": True,
                "enable_path_analysis": True,
            },
            "analysis_mode": {
                "mode": "fast",
                "sampling_threshold": 1000,
                "enable_fast_algorithms": True,
            },
            "output_control": {
                "generate_html": True,
                "generate_png": True,
                "generate_reports": True,
                "enable_timing_logs": True,
                "output_formatting": {"emoji": {"fallback_level": emoji_level}},
            },
            "output": {},
            "k_values": {
                "strategy_k_values": {
                    "k-core": 2,
                    "reciprocal_k-core": 2,
                    "ego_alter_k-core": 2,
                },
                "default_k_value": 2,
            },
            "visualization": {
                "node_size_metric": "degree",
                "base_node_size": 10.0,
                "node_size_multiplier": 2.0,
                "scaling_algorithm": "logarithmic",
                "base_edge_width": 0.5,
                "edge_width_multiplier": 1.5,
                "edge_width_scaling": "logarithmic",
                "bridge_color": "#6e6e6e",
                "intra_community_color": "#c0c0c0",
                "static_image": {
                    "generate": True,
                    "layout": "spring",
                    "width": 800,
                    "height": 600,
                    "dpi": 150,
                    "with_labels": False,
                    "font_size": 8,
                    "show_legend": True,
                    "node_alpha": 0.8,
                    "edge_alpha": 0.3,
                    "edge_arrow_size": 8,
                },
                "png_layout": {
                    "force_spring_layout": False,
                    "align_with_html": True,
                    "spring_iterations": 20,
                    "spring_k": 0.15,
                },
                "performance": {"max_layout_iterations": 20, "fast_mode": True},
            },
        }

    def create_test_graph(self):
        """Create a test graph with analysis attributes."""
        graph = nx.DiGraph()

        # Add nodes with analysis attributes
        nodes_data = [
            (
                "user1",
                {"community": 0, "degree": 3, "betweenness": 0.2, "eigenvector": 0.3},
            ),
            (
                "user2",
                {"community": 0, "degree": 3, "betweenness": 0.3, "eigenvector": 0.4},
            ),
            (
                "user3",
                {"community": 1, "degree": 3, "betweenness": 0.2, "eigenvector": 0.2},
            ),
            (
                "user4",
                {"community": 1, "degree": 2, "betweenness": 0.1, "eigenvector": 0.1},
            ),
        ]

        for node, attrs in nodes_data:
            graph.add_node(node, **attrs)

        # Add edges
        edges = [
            ("user1", "user2"),
            ("user2", "user1"),
            ("user1", "user3"),
            ("user2", "user3"),
            ("user3", "user2"),
            ("user3", "user4"),
        ]
        graph.add_edges_from(edges)

        return graph

    def test_unified_output_with_real_components(self):
        """Test unified output system with real pipeline components."""
        config_dict = self.create_test_config("full")

        # Create output manager
        manager = OutputManager(config_dict)

        # Initialize unified logger
        output_prefix = config_dict.get("output_file_prefix", "TestOutput")
        manager.initialize_unified_logger(output_prefix, "k-core", 2, "full")

        # Verify unified logger was created
        assert manager.unified_logger is not None
        assert manager._current_run_id is not None

        # Test logging with emoji integration
        manager.unified_logger.log_progress("Starting integration test")
        manager.unified_logger.log_success("Test setup complete")

        # Create test graph and generate outputs
        graph = self.create_test_graph()
        timing_data = {
            "strategy": 0.1,
            "analysis": 0.5,
            "visualization": 1.0,
            "total": 1.6,
        }

        # Mock the actual file generation to avoid complex dependencies
        with patch.object(manager, "metrics_calculator") as mock_calc, patch.object(
            manager, "interactive_renderer"
        ) as mock_html, patch.object(
            manager, "static_renderer"
        ) as mock_png, patch.object(manager, "metrics_reporter") as mock_reporter:
            # Mock metrics calculation
            from FollowWeb_Visualizor.visualization import (
                ColorScheme,
                VisualizationMetrics,
            )

            mock_metrics = VisualizationMetrics(
                node_metrics={},
                edge_metrics={},
                layout_positions={},
                color_schemes=ColorScheme(
                    {0: "#ff0000", 1: "#00ff00"},
                    {0: (1.0, 0.0, 0.0, 1.0), 1: (0.0, 1.0, 0.0, 1.0)},
                    "#6e6e6e",
                    "#c0c0c0",
                ),
                graph_hash="integration_test_hash",
            )
            mock_calc.calculate_all_metrics.return_value = mock_metrics

            # Mock successful generation
            mock_html.generate_html.return_value = True
            mock_png.generate_png.return_value = True
            mock_reporter.generate_analysis_report.return_value = (
                "Integration test report"
            )
            mock_reporter.save_metrics_file.return_value = True

            # Generate outputs
            results = manager.generate_all_outputs(
                graph, "k-core", 2, timing_data, "TestOutput"
            )

            # Verify all outputs were generated
            assert results.get("html") is True
            assert results.get("png") is True
            assert results.get("report") is True
            assert results.get("timing") is True

        # Close unified logger and verify text file was created
        manager.unified_logger.close()

        # Find the generated text file
        text_files = list(Path(self.output_dir).glob("*.txt"))
        assert len(text_files) > 0

        # Verify text file content
        text_file = text_files[0]
        with open(text_file, encoding="utf-8") as f:
            content = f.read()

            # Should contain emoji-formatted messages
            assert "Starting integration test" in content
            assert "Test setup complete" in content
            assert "✅" in content or "SUCCESS" in content  # Emoji or fallback
            assert "🔄" in content or "PROGRESS" in content  # Emoji or fallback

            # Should contain header and footer
            assert "FollowWeb Network Analysis - Unified Output Log" in content
            assert "Log completed:" in content

    def test_emoji_fallback_levels_integration(self):
        """Test different emoji fallback levels in integrated environment."""
        test_levels = ["full", "simple", "text", "none"]

        for level in test_levels:
            # Create config with specific emoji level
            config_dict = self.create_test_config(level)
            manager = OutputManager(config_dict)

            # Initialize unified logger
            output_prefix = config_dict.get("output_file_prefix", "EmojiTest")
            manager.initialize_unified_logger(output_prefix, "k-core", 2, level)

            # Verify emoji level was set correctly
            assert EmojiFormatter.get_fallback_level() == level

            # Test logging with different message types
            manager.unified_logger.log_success("Success message")
            manager.unified_logger.log_error("Error message")
            manager.unified_logger.log_progress("Progress message")
            manager.unified_logger.log_timer("Timer message")

            # Close logger
            manager.unified_logger.close()

            # Find and verify text file
            text_files = list(Path(self.output_dir).glob("*.txt"))
            if text_files:
                with open(text_files[-1], encoding="utf-8") as f:
                    content = f.read()

                    # Verify messages are present
                    assert "Success message" in content
                    assert "Error message" in content
                    assert "Progress message" in content
                    assert "Timer message" in content

                    # Verify correct emoji level formatting
                    if level == "full":
                        assert "✅" in content
                        assert "❌" in content
                        assert "🔄" in content
                        assert "⏱️" in content
                    elif level == "simple":
                        assert "[✓]" in content
                        assert "[✗]" in content
                        assert "[~]" in content
                        assert "[T]" in content
                    elif level == "text":
                        assert "SUCCESS" in content
                        assert "ERROR" in content
                        assert "PROGRESS" in content
                        assert "TIME" in content
                    elif level == "none":
                        # Should not contain emoji indicators
                        assert "✅" not in content
                        assert "[✓]" not in content
                        assert "SUCCESS" not in content

            # Clean up for next iteration
            for f in text_files:
                f.unlink()

    def test_output_synchronization_integration(self):
        """Test output synchronization between console and file in integrated environment."""
        config_dict = self.create_test_config("simple")
        manager = OutputManager(config_dict)

        # Capture console output
        console_messages = []

        with patch("logging.getLogger") as mock_logger:
            mock_console_logger = Mock()
            mock_logger.return_value = mock_console_logger

            # Track console log calls
            def capture_console(level, message):
                console_messages.append(message)

            mock_console_logger.log.side_effect = capture_console

            # Initialize unified logger
            output_prefix = config_dict.get("output_file_prefix", "SyncTest")
            manager.initialize_unified_logger(output_prefix, "k-core", 2, "simple")

            # Log various message types
            test_messages = [
                ("success", "Synchronization test success"),
                ("error", "Synchronization test error"),
                ("progress", "Synchronization test progress"),
                ("info", "Regular info message"),
            ]

            for msg_type, message in test_messages:
                if msg_type == "success":
                    manager.unified_logger.log_success(message)
                elif msg_type == "error":
                    manager.unified_logger.log_error(message)
                elif msg_type == "progress":
                    manager.unified_logger.log_progress(message)
                else:
                    manager.unified_logger.info(message)

            # Close logger
            manager.unified_logger.close()

            # Verify console messages were captured
            assert len(console_messages) >= len(test_messages)

            # Find text file
            text_files = list(Path(self.output_dir).glob("*.txt"))
            assert len(text_files) > 0

            with open(text_files[0], encoding="utf-8") as f:
                file_content = f.read()

                # Verify all messages appear in both console and file
                for _msg_type, message in test_messages:
                    # Check file content
                    assert message in file_content

                    # Check console messages
                    console_found = any(
                        message in console_msg for console_msg in console_messages
                    )
                    assert console_found, (
                        f"Message '{message}' not found in console output"
                    )

                # Verify emoji formatting is consistent
                assert "[✓]" in file_content  # Simple emoji level
                assert "[✗]" in file_content
                assert "[~]" in file_content

    def test_section_organization_integration(self):
        """Test section organization in integrated environment."""
        config_dict = self.create_test_config("text")
        manager = OutputManager(config_dict)

        # Initialize unified logger
        output_prefix = config_dict.get("output_file_prefix", "SectionTest")
        manager.initialize_unified_logger(output_prefix, "k-core", 2, "text")

        # Test organized logging with sections
        manager.unified_logger.start_section("Initialization")
        manager.unified_logger.log_progress("Setting up analysis environment")
        manager.unified_logger.info("Loading configuration")
        manager.unified_logger.end_section()

        manager.unified_logger.start_section("Analysis")
        manager.unified_logger.log_progress("Processing graph data")
        manager.unified_logger.log_success("Community detection complete")
        manager.unified_logger.end_section()

        manager.unified_logger.start_section("Visualization")
        manager.unified_logger.log_progress("Generating outputs")
        manager.unified_logger.log_success("All outputs generated successfully")
        manager.unified_logger.end_section()

        # Close logger
        manager.unified_logger.close()

        # Verify section organization in text file
        text_files = list(Path(self.output_dir).glob("*.txt"))
        assert len(text_files) > 0

        with open(text_files[0], encoding="utf-8") as f:
            content = f.read()

            # Verify section headers
            assert "INITIALIZATION" in content
            assert "ANALYSIS" in content
            assert "VISUALIZATION" in content

            # Verify section content
            assert "Setting up analysis environment" in content
            assert "Processing graph data" in content
            assert "Generating outputs" in content

            # Verify text-level emoji formatting
            assert "PROGRESS" in content
            assert "SUCCESS" in content

    def test_timing_preservation_integration(self):
        """Test timing information preservation in integrated environment."""
        config_dict = self.create_test_config("full")
        manager = OutputManager(config_dict)

        # Initialize unified logger with timing preservation
        output_prefix = config_dict.get("output_file_prefix", "TimingTest")
        manager.initialize_unified_logger(output_prefix, "k-core", 2, "full")

        # Log messages with delays to create distinct timestamps
        manager.unified_logger.log_timer("Starting timing test")
        time.sleep(0.1)  # Small delay
        manager.unified_logger.info("Middle message")
        time.sleep(0.1)  # Small delay
        manager.unified_logger.log_timer("Ending timing test")

        # Close logger
        manager.unified_logger.close()

        # Verify timing information in text file
        text_files = list(Path(self.output_dir).glob("*.txt"))
        assert len(text_files) > 0

        with open(text_files[0], encoding="utf-8") as f:
            content = f.read()

            # Should contain timestamp format [HH:MM:SS]
            import re

            timestamp_pattern = r"\[\d{2}:\d{2}:\d{2}\]"
            timestamps = re.findall(timestamp_pattern, content)

            # Should have timestamps for each message
            assert len(timestamps) >= 3

            # Verify messages are present
            assert "Starting timing test" in content
            assert "Middle message" in content
            assert "Ending timing test" in content

            # Verify emoji formatting
            assert "⏱️" in content or "TIME" in content

    def test_error_handling_integration(self):
        """Test error handling in integrated environment."""
        # Create config with invalid output directory
        config_dict = self.create_test_config("full")
        config_dict["output_file_prefix"] = (
            "/invalid/path/that/does/not/exist/TestOutput"
        )

        manager = OutputManager(config_dict)

        # Should handle invalid path gracefully
        output_prefix = config_dict.get("output_file_prefix", "ErrorTest")
        manager.initialize_unified_logger(output_prefix, "k-core", 2, "full")

        # Logger should still work for console output even if file fails
        if manager.unified_logger:
            manager.unified_logger.log_error("Error handling test")
            manager.unified_logger.close()

        # Should not raise exceptions
        assert True  # Test passes if no exceptions were raised

    def test_configuration_validation_integration(self):
        """Test configuration validation in integrated environment."""
        # Test valid configuration
        valid_config = self.create_test_config("simple")
        manager = OutputManager(valid_config)
        errors = manager.validate_output_configuration()
        assert len(errors) == 0

        # Test invalid configuration (all outputs disabled)
        invalid_config = self.create_test_config("simple")
        invalid_config["output_control"] = {
            "generate_html": False,
            "generate_png": False,
            "generate_reports": False,
            "enable_timing_logs": False,
        }

        manager = OutputManager(invalid_config)
        errors = manager.validate_output_configuration()
        assert len(errors) > 0
        assert "at least one output format" in errors[0].lower()


if __name__ == "__main__":
    pytest.main([__file__])
