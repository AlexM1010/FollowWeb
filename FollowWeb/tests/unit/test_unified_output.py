"""
Unit tests for unified output system integration.

This module tests the unified output system that consolidates console output
and text file generation with integrated emoji handling and user-configurable
emoji fallback levels.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from FollowWeb_Visualizor.output.formatters import EmojiFormatter
from FollowWeb_Visualizor.output.logging import Logger
from FollowWeb_Visualizor.output.managers import OutputConfig, OutputManager


class TestOutputConfig:
    """Test OutputConfig dataclass functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OutputConfig()

        assert config.console_output is True
        assert config.text_file_output is True
        assert config.simultaneous_logging is True
        assert config.organize_by_sections is True
        assert config.include_emojis_in_text is True
        assert config.preserve_timing_info is True
        assert config.preserve_progress_updates is True
        # create_directories is now hardcoded as True
        assert config.append_mode is False
        assert config.text_file_path is None

    def test_custom_config(self):
        """Test custom configuration values."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            temp_path = tmp.name

        config = OutputConfig(
            console_output=False,
            text_file_output=True,
            simultaneous_logging=False,
            chunk_logging=True,
            text_file_path=temp_path,
            append_mode=True,
        )

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

        assert config.console_output is False
        assert config.text_file_output is True
        assert config.simultaneous_logging is False
        assert config.chunk_logging is True
        assert config.text_file_path == temp_path
        assert config.append_mode is True


class TestLogger:
    """Test unified Logger functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self, temp_output_dir):
        """Set up test fixtures."""
        self.temp_dir = temp_output_dir
        self.test_file = os.path.join(self.temp_dir, "test_output.txt")

    def test_logger_initialization_console_only(self):
        """Test logger initialization with console output only."""
        config = OutputConfig(console_output=True, text_file_output=False)

        logger = Logger(config)
        assert logger.config.console_output is True
        assert logger.config.text_file_output is False
        assert logger.text_file_handle is None

    def test_logger_initialization_with_text_file(self):
        """Test logger initialization with text file output."""
        config = OutputConfig(
            console_output=True, text_file_output=True, text_file_path=self.test_file
        )

        logger = Logger(config)
        assert logger.config.text_file_output is True
        assert logger.text_file_handle is not None
        assert os.path.exists(self.test_file)

        logger.close()

    def test_simultaneous_logging(self):
        """Test simultaneous logging to console and text file."""
        config = OutputConfig(
            console_output=True,
            text_file_output=True,
            simultaneous_logging=True,
            text_file_path=self.test_file,
        )

        with patch("logging.getLogger") as mock_logger:
            mock_console_logger = Mock()
            mock_logger.return_value = mock_console_logger

            logger = Logger(config)
            logger.info("Test message")

            # Verify console logging was called
            mock_console_logger.log.assert_called_once()

            # Verify text file was written
            logger.close()
            with open(self.test_file, encoding="utf-8") as f:
                content = f.read()
                assert "Test message" in content

    def test_emoji_integration(self):
        """Test emoji integration with different fallback levels."""
        config = OutputConfig(
            console_output=True, text_file_output=True, text_file_path=self.test_file
        )

        logger = Logger(config)

        # Test different emoji levels
        for level in ["full", "simple", "text", "none"]:
            EmojiFormatter.set_fallback_level(level)
            logger.log_success("Test success message")
            logger.log_error("Test error message")
            logger.log_progress("Test progress message")

        logger.close()

        # Verify text file contains formatted messages
        with open(self.test_file, encoding="utf-8") as f:
            content = f.read()
            assert "Test success message" in content
            assert "Test error message" in content
            assert "Test progress message" in content

    def test_section_organization(self):
        """Test section-based content organization."""
        config = OutputConfig(
            console_output=True,
            text_file_output=True,
            organize_by_sections=True,
            text_file_path=self.test_file,
        )

        logger = Logger(config)

        logger.start_section("Analysis Phase")
        logger.info("Starting analysis", "Analysis Phase")
        logger.info("Processing data", "Analysis Phase")
        logger.end_section()

        logger.start_section("Visualization Phase")
        logger.info("Generating visualizations", "Visualization Phase")
        logger.end_section()

        logger.close()

        # Verify sections are properly organized
        with open(self.test_file, encoding="utf-8") as f:
            content = f.read()
            assert "ANALYSIS PHASE" in content
            assert "VISUALIZATION PHASE" in content
            assert "Starting analysis" in content
            assert "Generating visualizations" in content

    def test_buffered_logging(self):
        """Test buffered logging functionality."""
        config = OutputConfig(
            console_output=True,
            text_file_output=True,
            simultaneous_logging=False,
            chunk_logging=True,
            text_file_path=self.test_file,
        )

        logger = Logger(config)

        # Add messages to buffer
        logger.info("Message 1")
        logger.info("Message 2", "Section A")
        logger.info("Message 3", "Section B")

        # File should be empty before flush
        with open(self.test_file, encoding="utf-8") as f:
            content = f.read()
            # Only header should be present
            assert "Message 1" not in content

        # Flush buffer
        logger.flush_buffer()

        # Now messages should be in file
        with open(self.test_file, encoding="utf-8") as f:
            content = f.read()
            assert "Message 1" in content
            assert "Message 2" in content
            assert "Message 3" in content
            assert "Section A" in content
            assert "Section B" in content

        logger.close()

    def test_timing_preservation(self):
        """Test timing information preservation."""
        config = OutputConfig(
            console_output=True,
            text_file_output=True,
            preserve_timing_info=True,
            text_file_path=self.test_file,
        )

        logger = Logger(config)
        logger.info("Timed message")
        logger.close()

        # Verify timestamp is included
        with open(self.test_file, encoding="utf-8") as f:
            content = f.read()
            # Should contain timestamp format [HH:MM:SS]
            assert "[" in content and "]" in content
            assert "Timed message" in content

    def test_context_manager(self):
        """Test logger as context manager."""
        config = OutputConfig(
            console_output=True, text_file_output=True, text_file_path=self.test_file
        )

        with Logger(config) as logger:
            logger.info("Context manager test")
            assert logger.text_file_handle is not None

        # File should be closed after context exit
        # Verify content was written
        with open(self.test_file, encoding="utf-8") as f:
            content = f.read()
            assert "Context manager test" in content

    def test_error_handling_invalid_path(self):
        """Test error handling for invalid file paths."""
        # Create a path in a non-existent directory using cross-platform approach
        invalid_path = (
            Path(tempfile.gettempdir()) / "non_existent_dir" / "subdir" / "test.txt"
        )

        config = OutputConfig(
            console_output=True,
            text_file_output=True,
            text_file_path=str(invalid_path),
            # create_directories is now hardcoded as True
        )

        # Logger now automatically creates directories, so this should succeed
        logger = Logger(config)
        # Directory creation is now automatic, so the file handle should be created
        assert logger.text_file_handle is not None
        assert logger.config.text_file_output is True  # Should remain enabled

        # Clean up the created file
        logger.close()
        if invalid_path.exists():
            invalid_path.unlink()
        # Clean up created directories
        try:
            invalid_path.parent.rmdir()
            invalid_path.parent.parent.rmdir()
        except OSError:
            pass  # Directory might not be empty or already removed

    def test_directory_creation(self):
        """Test automatic directory creation."""
        nested_path = Path(self.temp_dir) / "nested" / "dir" / "test.txt"
        config = OutputConfig(
            console_output=True,
            text_file_output=True,
            text_file_path=str(nested_path),
            # create_directories is now hardcoded as True
        )

        logger = Logger(config)
        logger.info("Directory creation test")
        logger.close()

        # Verify directory was created and file exists
        assert nested_path.exists()
        with nested_path.open(encoding="utf-8") as f:
            content = f.read()
            assert "Directory creation test" in content


class TestOutputManager:
    """Test unified OutputManager functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self, temp_output_dir):
        """Set up test fixtures."""
        self.temp_dir = temp_output_dir
        self.config = {
            "output_control": {
                "generate_html": True,
                "generate_png": True,
                "generate_reports": True,
                "enable_timing_logs": True,
                "output_formatting": {"emoji": {"fallback_level": "full"}},
            },
            "output": {},
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
                    "width": 1200,
                    "height": 800,
                    "dpi": 300,
                    "with_labels": False,
                    "font_size": 8,
                    "show_legend": True,
                    "node_alpha": 0.8,
                    "edge_alpha": 0.3,
                    "edge_arrow_size": 8,
                },
                "performance": {},
            },
            "strategy": "k-core",
            "analysis_mode": {"mode": "full"},
            "pipeline_stages": {
                "enable_strategy": True,
                "enable_analysis": True,
                "enable_visualization": True,
            },
        }

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        temp_path = Path(self.temp_dir)
        if temp_path.exists():
            shutil.rmtree(temp_path)

    def test_output_manager_initialization(self):
        """Test OutputManager initialization."""
        manager = OutputManager(self.config)

        assert manager.config == self.config
        assert manager.output_control == self.config["output_control"]
        assert manager.unified_logger is None
        assert manager._current_run_id is None

    def test_unified_logger_initialization(self):
        """Test unified logger initialization in OutputManager."""
        manager = OutputManager(self.config)

        # Mock the generate_output_filename function
        with patch("FollowWeb_Visualizor.utils.generate_output_filename") as mock_gen:
            mock_gen.return_value = str(Path(self.temp_dir) / "test_output.txt")

            manager.initialize_unified_logger("TestOutput", "k-core", 10, "full")

            assert manager.unified_logger is not None
            assert manager._current_run_id is not None
            assert EmojiFormatter.get_fallback_level() == "full"

    def test_emoji_config_extraction(self):
        """Test emoji configuration extraction from config dictionary."""
        # Test valid config
        emoji_level = OutputManager.get_emoji_config_from_dict(self.config)
        assert emoji_level == "full"

        # Test missing config sections
        empty_config = {}
        emoji_level = OutputManager.get_emoji_config_from_dict(empty_config)
        assert emoji_level == "full"  # Default fallback

        # Test partial config
        partial_config = {"output_control": {"output_formatting": {}}}
        emoji_level = OutputManager.get_emoji_config_from_dict(partial_config)
        assert emoji_level == "full"  # Default fallback

    def test_output_format_checks(self):
        """Test output format enable/disable checks."""
        manager = OutputManager(self.config)

        assert manager.should_generate_html() is True
        assert manager.should_generate_png() is True
        assert manager.should_generate_reports() is True
        assert manager.should_generate_timing_logs() is True

        # Test with disabled formats
        disabled_config = self.config.copy()
        disabled_config["output_control"] = {
            "generate_html": False,
            "generate_png": False,
            "generate_reports": True,
            "enable_timing_logs": False,
        }

        manager = OutputManager(disabled_config)
        assert manager.should_generate_html() is False
        assert manager.should_generate_png() is False
        assert manager.should_generate_reports() is True
        assert manager.should_generate_timing_logs() is False

    def test_enabled_formats_list(self):
        """Test getting list of enabled output formats."""
        manager = OutputManager(self.config)
        enabled = manager.get_enabled_formats()

        expected = ["HTML", "PNG", "Reports", "Timing Logs"]
        assert enabled == expected

    def test_output_configuration_validation(self):
        """Test output configuration validation."""
        manager = OutputManager(self.config)
        errors = manager.validate_output_configuration()

        # Should have no errors with valid config
        assert len(errors) == 0

        # Test with all formats disabled
        invalid_config = self.config.copy()
        invalid_config["output_control"] = {
            "generate_html": False,
            "generate_png": False,
            "generate_reports": False,
            "enable_timing_logs": False,
        }

        manager = OutputManager(invalid_config)
        errors = manager.validate_output_configuration()

        # Should have error about no enabled formats
        assert len(errors) > 0
        assert "at least one output format" in errors[0].lower()

    def test_context_manager(self):
        """Test OutputManager initialization (context manager not implemented)."""
        manager = OutputManager(self.config)
        assert manager is not None
        # OutputManager works without context manager protocol

    @patch("FollowWeb_Visualizor.utils.generate_output_filename")
    @patch("FollowWeb_Visualizor.utils.ensure_output_directory")
    def test_generate_all_outputs_mock(self, mock_ensure_dir, mock_gen_filename):
        """Test generate_all_outputs with mocked dependencies."""
        # Mock the filename generation
        mock_gen_filename.side_effect = [
            str(Path(self.temp_dir) / "test.html"),
            str(Path(self.temp_dir) / "test.png"),
            str(Path(self.temp_dir) / "test.txt"),
        ]

        # Create a mock graph
        import networkx as nx

        graph = nx.DiGraph()
        graph.add_node("user1", community=0, degree=5, betweenness=0.1, eigenvector=0.2)
        graph.add_node(
            "user2", community=1, degree=3, betweenness=0.05, eigenvector=0.1
        )
        graph.add_edge("user1", "user2")

        manager = OutputManager(self.config)

        # Mock the renderers to avoid actual file generation
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
                color_schemes=ColorScheme({}, {}, "#6e6e6e", "#c0c0c0"),
                graph_hash="test_hash",
            )
            mock_calc.calculate_all_metrics.return_value = mock_metrics

            # Mock renderer returns
            mock_html.generate_html.return_value = True
            mock_png.generate_png.return_value = True
            mock_reporter.generate_analysis_report.return_value = "Test report"
            mock_reporter.save_metrics_file.return_value = True

            # Test output generation
            timing_data = {"analysis": 1.0, "visualization": 2.0, "total": 3.0}
            results = manager.generate_all_outputs(
                graph, "k-core", 10, timing_data, "TestOutput"
            )

            # Verify all outputs were attempted
            assert "html" in results
            assert "png" in results
            assert "report" in results
            assert "timing" in results


class TestEmojiIntegration:
    """Test emoji integration across the unified output system."""

    @pytest.fixture(autouse=True)
    def setup_method(self, temp_output_dir):
        """Set up test fixtures."""
        self.temp_dir = temp_output_dir
        self.test_file = os.path.join(self.temp_dir, "emoji_test.txt")

    def teardown_method(self):
        """Clean up test fixtures."""
        # Reset emoji level to default
        EmojiFormatter.set_fallback_level("full")

    def test_emoji_fallback_levels_in_unified_output(self):
        """Test all emoji fallback levels work in unified output."""
        config = OutputConfig(
            console_output=True, text_file_output=True, text_file_path=self.test_file
        )

        test_cases = [
            ("full", "✅", "❌", "🔄"),
            ("simple", "[✓]", "[✗]", "[~]"),
            ("text", "SUCCESS", "ERROR", "PROGRESS"),
            ("none", "", "", ""),
        ]

        for level, success_emoji, error_emoji, progress_emoji in test_cases:
            # Clear file for each test
            if os.path.exists(self.test_file):
                os.remove(self.test_file)

            EmojiFormatter.set_fallback_level(level)

            with Logger(config) as logger:
                logger.log_success("Test success")
                logger.log_error("Test error")
                logger.log_progress("Test progress")

            # Verify correct emoji level was used
            with open(self.test_file, encoding="utf-8") as f:
                content = f.read()

                if level != "none":
                    if success_emoji:
                        assert success_emoji in content
                    if error_emoji:
                        assert error_emoji in content
                    if progress_emoji:
                        assert progress_emoji in content

                # Message content should always be present
                assert "Test success" in content
                assert "Test error" in content
                assert "Test progress" in content

    def test_emoji_consistency_console_and_file(self):
        """Test emoji consistency between console and file output."""
        config = OutputConfig(
            console_output=True,
            text_file_output=True,
            simultaneous_logging=True,
            text_file_path=self.test_file,
        )

        # Test with different emoji levels
        for level in ["full", "simple", "text", "none"]:
            EmojiFormatter.set_fallback_level(level)

            with patch("logging.getLogger") as mock_logger:
                mock_console_logger = Mock()
                mock_logger.return_value = mock_console_logger

                with Logger(config) as logger:
                    logger.log_success("Consistency test")

                # Get the message that was logged to console
                console_call = mock_console_logger.log.call_args
                if console_call:
                    console_message = console_call[0][
                        1
                    ]  # Second argument is the message

                    # Read file content
                    with open(self.test_file, encoding="utf-8") as f:
                        file_content = f.read()

                    # Both should contain the same formatted message
                    assert "Consistency test" in console_message
                    assert "Consistency test" in file_content

                    # Emoji formatting should be consistent
                    expected_format = EmojiFormatter.format(
                        "success", "Consistency test"
                    )
                    assert expected_format in console_message

            # Clear file for next iteration
            if os.path.exists(self.test_file):
                os.remove(self.test_file)

    def test_emoji_configuration_from_config_dict(self):
        """Test emoji configuration extraction and application."""
        config_dict = {
            "output_control": {
                "output_formatting": {"emoji": {"fallback_level": "simple"}}
            }
        }

        # Test emoji level extraction
        emoji_level = OutputManager.get_emoji_config_from_dict(config_dict)
        assert emoji_level == "simple"

        # Test that the level is applied correctly
        EmojiFormatter.set_fallback_level(emoji_level)
        formatted = EmojiFormatter.format("success", "Test message")
        assert "[✓]" in formatted
        assert "Test message" in formatted


class TestOutputSynchronization:
    """Test output synchronization between console and text file."""

    @pytest.fixture(autouse=True)
    def setup_method(self, temp_output_dir):
        """Set up test fixtures."""
        self.temp_dir = temp_output_dir
        self.test_file = os.path.join(self.temp_dir, "sync_test.txt")

    def test_no_duplication_simultaneous_logging(self):
        """Test that simultaneous logging doesn't create duplication."""
        config = OutputConfig(
            console_output=True,
            text_file_output=True,
            simultaneous_logging=True,
            merge_duplicate_content=True,
            text_file_path=self.test_file,
        )

        with patch("logging.getLogger") as mock_logger:
            mock_console_logger = Mock()
            mock_logger.return_value = mock_console_logger

            with Logger(config) as logger:
                # Log the same message multiple times
                logger.info("Unique test message")
                logger.info("Unique test message")  # Duplicate
                logger.info("Another unique message")

            # Verify console was called for each message
            assert mock_console_logger.log.call_count == 3

            # Verify file content
            with open(self.test_file, encoding="utf-8") as f:
                content = f.read()

                # Each message should appear (no deduplication at this level)
                message_count = content.count("Unique test message")
                assert message_count == 2  # Both instances should be present
                assert "Another unique message" in content

    def test_content_preservation(self):
        """Test that all content is preserved without loss."""
        config = OutputConfig(
            console_output=True,
            text_file_output=True,
            preserve_timing_info=True,
            preserve_progress_updates=True,
            text_file_path=self.test_file,
        )

        test_messages = [
            "Analysis started",
            "Processing 100 nodes",
            "Community detection complete",
            "Visualization generated",
            "Analysis complete",
        ]

        with Logger(config) as logger:
            for msg in test_messages:
                logger.info(msg)

        # Verify all messages are preserved
        with open(self.test_file, encoding="utf-8") as f:
            content = f.read()

            for msg in test_messages:
                assert msg in content

            # Verify timing info is preserved
            assert "[" in content and "]" in content  # Timestamp format

    def test_section_organization_no_duplication(self):
        """Test section organization doesn't create content duplication."""
        config = OutputConfig(
            console_output=True,
            text_file_output=True,
            organize_by_sections=True,
            text_file_path=self.test_file,
        )

        with Logger(config) as logger:
            logger.start_section("Phase 1")
            logger.info("Phase 1 message 1", "Phase 1")
            logger.info("Phase 1 message 2", "Phase 1")
            logger.end_section()

            logger.start_section("Phase 2")
            logger.info("Phase 2 message 1", "Phase 2")
            logger.end_section()

        with open(self.test_file, encoding="utf-8") as f:
            content = f.read()

            # Verify section headers appear only once
            phase1_count = content.count("PHASE 1")
            phase2_count = content.count("PHASE 2")
            assert phase1_count == 1
            assert phase2_count == 1

            # Verify all messages are present
            assert "Phase 1 message 1" in content
            assert "Phase 1 message 2" in content
            assert "Phase 2 message 1" in content


if __name__ == "__main__":
    pytest.main([__file__])
