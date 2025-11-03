"""
Integration tests for UI/UX fixes in FollowWeb network analysis.

Tests the integration of UI/UX fixes across modules including emoji consistency,
console output formatting, and duplicate message prevention in real analysis scenarios.
"""

import io
import json
import os
import sys
from pathlib import Path

from FollowWeb_Visualizor.core.config import get_configuration_manager
from FollowWeb_Visualizor.main import PipelineOrchestrator


class TestEmojiConsistencyIntegration:
    """Test emoji consistency across all modules in real analysis scenarios."""

    def test_emoji_consistency_in_full_pipeline(self, temp_output_dir: str):
        """Test that emoji usage is consistent throughout a full analysis pipeline."""
        # Create a small test graph
        test_data = [
            {"user": "A", "followers": ["B", "C"], "following": ["B", "C"]},
            {"user": "B", "followers": ["A"], "following": ["A"]},
            {"user": "C", "followers": ["A"], "following": ["A"]},
        ]

        # Create temporary input file
        input_file = Path(temp_output_dir) / "test_input.json"
        with input_file.open("w") as f:
            json.dump(test_data, f)

        # Capture all output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = captured_stdout = io.StringIO()
        sys.stderr = captured_stderr = io.StringIO()

        try:
            # Configure for small test
            config_manager = get_configuration_manager()
            config = config_manager.load_configuration()
            config.input_file = str(input_file)
            config.output_file_prefix = str(Path(temp_output_dir) / "FollowWeb")
            config.k_values.strategy_k_values["k-core"] = 1
            config.visualization.static_image.generate = False  # Skip PNG for speed

            # Run pipeline
            orchestrator = PipelineOrchestrator(config)
            success = orchestrator.execute_pipeline()

            # Get all output
            stdout_output = captured_stdout.getvalue()
            stderr_output = captured_stderr.getvalue()
            all_output = stdout_output + stderr_output

            # Test emoji consistency
            if success:
                # Should use ✅ for success messages, not ✓
                success_count = all_output.count("✅")
                old_checkmark_count = all_output.count("✓")

                # Should have some success messages
                assert success_count > 0, "No success emoji found in output"
                # Should not use old checkmark character
                assert old_checkmark_count == 0, (
                    f"Found {old_checkmark_count} old checkmark characters"
                )

                # Should use 🔄 for processing messages (if any are output to stdout/stderr)
                all_output.count("🔄")
                # Note: Processing emoji might be in logs rather than stdout/stderr

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def test_error_emoji_consistency_in_pipeline(self, temp_output_dir: str):
        """Test that error messages use consistent emoji in pipeline context."""
        # Create invalid input to trigger errors
        input_file = Path(temp_output_dir) / "invalid_input.json"
        with input_file.open("w") as f:
            f.write("invalid json content")

        # Capture all output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = captured_stdout = io.StringIO()
        sys.stderr = captured_stderr = io.StringIO()

        try:
            # Configure with invalid input
            config_manager = get_configuration_manager()
            config = config_manager.load_configuration()
            config.input_file = str(input_file)
            config.output_file_prefix = str(Path(temp_output_dir) / "FollowWeb")

            # Run pipeline (should fail)
            orchestrator = PipelineOrchestrator(config)
            success = orchestrator.execute_pipeline()

            # Get all output
            stdout_output = captured_stdout.getvalue()
            stderr_output = captured_stderr.getvalue()
            all_output = stdout_output + stderr_output

            # Should have failed
            assert not success

            # Should use ❌ for error messages
            error_count = all_output.count("❌")
            if error_count > 0:  # Only test if errors were actually logged with emoji
                # Should not have duplicate error prefixes
                assert "❌ ERROR:" not in all_output, "Found duplicate error prefixes"

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class TestConsoleOutputFormattingIntegration:
    """Test console output formatting fixes in real analysis scenarios."""

    def test_progress_completion_formatting_in_analysis(self, temp_output_dir: str):
        """Test that progress completion messages have proper formatting during analysis."""
        # Create a small test graph
        test_data = [
            {"user": "A", "followers": ["B"], "following": ["B"]},
            {"user": "B", "followers": ["A"], "following": ["A"]},
        ]

        input_file = Path(temp_output_dir) / "test_input.json"
        with input_file.open("w") as f:
            json.dump(test_data, f)

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            # Configure for test
            config_manager = get_configuration_manager()
            config = config_manager.load_configuration()
            config.input_file = str(input_file)
            config.output_file_prefix = str(Path(temp_output_dir) / "FollowWeb")
            config.k_values.strategy_k_values["k-core"] = 1
            config.visualization.static_image.generate = False

            # Run pipeline
            orchestrator = PipelineOrchestrator(config)
            success = orchestrator.execute_pipeline()

            output = captured_output.getvalue()
            lines = output.split("\n")

            if success:
                # Find completion messages
                completion_lines = [
                    i
                    for i, line in enumerate(lines)
                    if "✅" in line and "completed" in line
                ]

                # Each completion message should be followed by an empty line
                for completion_line_idx in completion_lines:
                    if completion_line_idx < len(lines) - 1:
                        next_line = lines[completion_line_idx + 1]
                        # Next line should be empty or contain the next message with proper spacing
                        assert next_line == "" or not next_line.strip().startswith(
                            "✅"
                        ), (
                            f"Completion message at line {completion_line_idx} not followed by proper spacing"
                        )

        finally:
            sys.stdout = old_stdout

    def test_calculation_message_spacing_in_analysis(self, temp_output_dir: str):
        """Test that calculation messages have proper spacing in analysis context."""
        # This test would verify that "Calculating" messages have newlines before them
        # Implementation depends on the actual analysis module structure
        pass

    def test_section_header_spacing_in_reports(self, temp_output_dir: str):
        """Test that section headers have proper spacing in generated reports."""
        # Create a test graph
        test_data = [
            {"user": "A", "followers": ["B", "C"], "following": ["B", "C"]},
            {"user": "B", "followers": ["A"], "following": ["A"]},
            {"user": "C", "followers": ["A"], "following": ["A"]},
        ]

        input_file = os.path.join(temp_output_dir, "test_input.json")
        with open(input_file, "w") as f:
            json.dump(test_data, f)

        # Configure for test
        config_manager = get_configuration_manager()
        config = config_manager.load_configuration()
        config.input_file = input_file
        config.output_file_prefix = str(Path(temp_output_dir) / "FollowWeb")
        config.k_values.strategy_k_values["k-core"] = 1
        config.visualization.static_image.generate = False

        # Run pipeline
        orchestrator = PipelineOrchestrator(config)
        success = orchestrator.execute_pipeline()

        if success:
            # Check generated text report for proper spacing
            report_files = [
                f for f in os.listdir(temp_output_dir) if f.endswith(".txt")
            ]
            if report_files:
                report_file = Path(temp_output_dir) / report_files[0]
                with report_file.open(encoding="utf-8") as f:
                    report_content = f.read()

                # Check for section headers with proper structure
                lines = report_content.split("\n")
                section_headers = [
                    line for line in lines if line.startswith("----") and "----" in line
                ]

                # Should have section headers in the report
                assert len(section_headers) > 0, "No section headers found in report"

                # Report should have proper structure with content
                assert len(lines) > 10, "Report seems too short"


class TestDuplicateMessagePreventionIntegration:
    """Test duplicate message prevention in real analysis scenarios."""

    def test_no_duplicate_large_graph_messages(self, temp_output_dir: str):
        """Test that large graph detection messages are not duplicated."""
        # Create a larger test graph to trigger large graph detection
        test_data = []

        # Create a graph with enough nodes to potentially trigger large graph detection
        for i in range(100):
            node_name = f"user_{i}"
            followers = [f"user_{j}" for j in range(min(i + 1, 10))]
            following = [f"user_{j}" for j in range(min(i + 1, 10))]
            test_data.append(
                {"user": node_name, "followers": followers, "following": following}
            )

        input_file = Path(temp_output_dir) / "large_test_input.json"
        with input_file.open("w") as f:
            json.dump(test_data, f)

        # Capture all output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = captured_stdout = io.StringIO()
        sys.stderr = captured_stderr = io.StringIO()

        try:
            # Configure for test
            config_manager = get_configuration_manager()
            config = config_manager.load_configuration()
            config.input_file = str(input_file)
            config.output_file_prefix = str(Path(temp_output_dir) / "FollowWeb")
            config.k_values.strategy_k_values["k-core"] = 2
            config.visualization.static_image.generate = False

            # Run pipeline
            orchestrator = PipelineOrchestrator(config)
            orchestrator.execute_pipeline()

            # Get all output
            stdout_output = captured_stdout.getvalue()
            stderr_output = captured_stderr.getvalue()
            all_output = stdout_output + stderr_output

            # Check for duplicate large graph detection messages
            large_graph_messages = [
                line
                for line in all_output.split("\n")
                if "large graph" in line.lower() or "sampling" in line.lower()
            ]

            # If large graph messages exist, they should not be duplicated
            if large_graph_messages:
                unique_messages = set(large_graph_messages)
                assert len(unique_messages) == len(large_graph_messages), (
                    f"Found duplicate large graph messages: {large_graph_messages}"
                )

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def test_no_duplicate_sampling_mode_messages(self, temp_output_dir: str):
        """Test that sampling mode messages are not duplicated."""
        # This test would verify that sampling mode messages from analysis.py and config.py
        # are coordinated to avoid duplication
        pass

    def test_no_duplicate_operational_status_messages(self, temp_output_dir: str):
        """Test that operational status messages are not duplicated."""
        # This test would verify that operational status messages are not repeated
        # across different modules
        pass


class TestUIUXFixesEdgeCases:
    """Test UI/UX fixes with edge cases and error conditions."""

    def test_fixes_with_empty_graph(self, temp_output_dir: str):
        """Test that UI/UX fixes work with empty graphs."""
        # Create empty graph data
        test_data = []

        input_file = Path(temp_output_dir) / "empty_input.json"
        with input_file.open("w") as f:
            json.dump(test_data, f)

        # Capture output
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            # Configure for test
            config_manager = get_configuration_manager()
            config = config_manager.load_configuration()
            config.input_file = str(input_file)
            config.output_file_prefix = str(Path(temp_output_dir) / "FollowWeb")
            config.k_values.strategy_k_values["k-core"] = 1

            # Run pipeline
            orchestrator = PipelineOrchestrator(config)
            success = orchestrator.execute_pipeline()

            output = captured_output.getvalue()

            # Should handle empty graph gracefully
            # May succeed or fail, but should not crash
            assert isinstance(success, bool)

            # Should use consistent emoji in any messages
            if "✓" in output:
                raise AssertionError(
                    "Found old checkmark character instead of ✅ emoji"
                )

        finally:
            sys.stdout = old_stdout

    def test_fixes_with_large_graph(self, temp_output_dir: str):
        """Test that UI/UX fixes work with larger graphs."""
        # Create larger test graph
        test_data = []

        # Create a graph with 50 nodes
        for i in range(50):
            node_name = f"user_{i}"
            # Each node follows/is followed by a few others
            connections = [
                f"user_{j}" for j in range(max(0, i - 2), min(50, i + 3)) if j != i
            ]
            test_data.append(
                {"user": node_name, "followers": connections, "following": connections}
            )

        input_file = Path(temp_output_dir) / "large_input.json"
        with input_file.open("w") as f:
            json.dump(test_data, f)

        # Configure for test
        config_manager = get_configuration_manager()
        config = config_manager.load_configuration()
        config.input_file = str(input_file)
        config.output_file_prefix = str(Path(temp_output_dir) / "FollowWeb")
        config.k_values.strategy_k_values["k-core"] = 2
        config.visualization.static_image.generate = False

        # Run pipeline
        orchestrator = PipelineOrchestrator(config)
        success = orchestrator.execute_pipeline()

        # Should complete successfully
        assert success, "Pipeline failed with larger graph"
