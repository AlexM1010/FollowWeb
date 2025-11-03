"""
Unit tests for utility functions module.

Tests utility functions for file operations, validation, color generation,
mathematical scaling, and error handling.
"""

import os
from pathlib import Path

import pytest

from FollowWeb_Visualizor.core.exceptions import (
    ConfigurationError,
    DataProcessingError,
    FollowWebError,
    VisualizationError,
)
from FollowWeb_Visualizor.utils.files import (
    ensure_output_directory,
    generate_output_filename,
)
from FollowWeb_Visualizor.utils.math import (
    clamp_value,
    format_time_duration,
    get_scaled_size,
    safe_divide,
    scale_value,
)
from FollowWeb_Visualizor.utils.validation import validate_file_path
from FollowWeb_Visualizor.visualization.colors import get_community_colors


class TestOutputFilenameGeneration:
    """Test output filename generation functionality."""

    def test_valid_filename_generation(self):
        """Test generation of valid output filename."""
        # Use pathlib for cross-platform path handling
        prefix = Path("Output") / "FollowWeb"
        filename = generate_output_filename(str(prefix), "k-core", 10, "html")

        # Use pathlib for cross-platform path comparison
        expected_prefix = str(Path("Output") / "FollowWeb-k-core-k10-")
        assert filename.startswith(expected_prefix)
        assert filename.endswith(".html")
        assert len(filename.split("-")) >= 4  # prefix-strategy-k-value-hash.ext

    def test_empty_prefix_rejection(self):
        """Test rejection of empty prefix."""
        with pytest.raises(ValueError, match="prefix must be a non-empty string"):
            generate_output_filename("", "k-core", 10, "html")

    def test_empty_strategy_rejection(self):
        """Test rejection of empty strategy."""
        prefix = str(Path("Output") / "FollowWeb")
        with pytest.raises(ValueError, match="strategy must be a non-empty string"):
            generate_output_filename(prefix, "", 10, "html")

    def test_empty_extension_rejection(self):
        """Test rejection of empty extension."""
        prefix = str(Path("Output") / "FollowWeb")
        with pytest.raises(ValueError, match="extension must be a non-empty string"):
            generate_output_filename(prefix, "k-core", 10, "")

    def test_negative_k_value_rejection(self):
        """Test rejection of negative k-value."""
        prefix = str(Path("Output") / "FollowWeb")
        with pytest.raises(ValueError, match="k_value cannot be negative"):
            generate_output_filename(prefix, "k-core", -1, "html")

    def test_invalid_characters_rejection(self):
        """Test rejection of invalid filesystem characters."""
        # Use platform-agnostic path construction with invalid character
        prefix = str(Path("Output") / "Follow<Web")
        with pytest.raises(ValueError, match="contains invalid filesystem characters"):
            generate_output_filename(prefix, "k-core", 10, "html")


class TestCommunityColors:
    """Test community color generation functionality."""

    def test_positive_communities_color_generation(self):
        """Test color generation for positive number of communities."""
        colors = get_community_colors(5)

        assert "hex" in colors
        assert "rgba" in colors
        assert len(colors["hex"]) == 5
        assert len(colors["rgba"]) == 5

        # Check color format
        for i in range(5):
            hex_color = colors["hex"][i]
            rgba_color = colors["rgba"][i]

            assert hex_color.startswith("#")
            assert len(hex_color) == 7
            assert len(rgba_color) >= 3  # At least RGB

    def test_zero_communities_handling(self):
        """Test handling of zero communities."""
        colors = get_community_colors(0)

        assert "hex" in colors
        assert "rgba" in colors
        assert 0 in colors["hex"]
        assert colors["hex"][0] == "#808080"  # Default gray

    def test_negative_communities_rejection(self):
        """Test rejection of negative number of communities."""
        with pytest.raises(ValueError, match="num_communities must be between"):
            get_community_colors(-1)

    def test_excessive_communities_rejection(self):
        """Test rejection of excessive number of communities."""
        with pytest.raises(ValueError, match="num_communities must be between"):
            get_community_colors(1001)


class TestValueScaling:
    """Test value scaling functionality."""

    def test_logarithmic_scaling(self):
        """Test logarithmic scaling algorithm."""
        result = scale_value(10.0, 5.0, 2.0, "logarithmic")
        # Just test that logarithmic scaling produces reasonable results
        assert result > 5.0  # Should be greater than base
        assert result < 50.0  # Should be reasonable

    def test_linear_scaling(self):
        """Test linear scaling algorithm."""
        result = scale_value(10.0, 5.0, 2.0, "linear")
        expected = 5.0 + 10.0 * 2.0
        assert result == expected

    def test_zero_value_scaling(self):
        """Test scaling with zero value."""
        log_result = scale_value(0.0, 5.0, 2.0, "logarithmic")
        linear_result = scale_value(0.0, 5.0, 2.0, "linear")

        assert log_result >= 5.0
        assert linear_result == 5.0

    def test_invalid_algorithm_rejection(self):
        """Test rejection of invalid scaling algorithm."""
        with pytest.raises(ValueError, match="Invalid scaling algorithm"):
            scale_value(10.0, 5.0, 2.0, "invalid_algorithm")

    def test_negative_values_rejection(self):
        """Test rejection of negative input values."""
        with pytest.raises(ValueError, match="value cannot be negative"):
            scale_value(-1.0, 5.0, 2.0, "linear")


class TestDirectoryOperations:
    """Test directory operation utilities with cross-platform support."""

    def test_ensure_output_directory_creation(self, temp_output_dir: str):
        """Test creation of output directory."""
        test_file = Path(temp_output_dir) / "subdir" / "test.html"

        result_dir = ensure_output_directory(str(test_file))

        assert test_file.parent.exists()
        assert Path(result_dir).is_absolute()  # Should return absolute path

    def test_ensure_output_directory_existing(self, temp_output_dir: str):
        """Test handling of existing output directory."""
        test_file = Path(temp_output_dir) / "test.html"

        # Should not raise for existing directory
        result_dir = ensure_output_directory(str(test_file))
        assert Path(result_dir).exists()

    def test_absolute_path_handling(self, temp_output_dir: str):
        """Test handling of absolute paths."""
        abs_path = Path(temp_output_dir).resolve() / "absolute_test"

        result_dir = ensure_output_directory(str(abs_path))

        assert Path(result_dir).exists()
        assert Path(result_dir).is_absolute()

    @pytest.mark.skipif(
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("RUNNER_OS") == "Windows",
        reason="Windows GitHub Actions runners have strict permission controls that prevent working directory changes, causing test failures due to path resolution conflicts",
    )
    def test_relative_path_handling(self, temp_output_dir: str):
        """Test handling of relative paths."""
        # Change to temp directory for relative path test
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_output_dir)
            relative_path = "relative_test_dir"

            result_dir = ensure_output_directory(relative_path)

            assert os.path.exists(result_dir)
            assert os.path.isabs(result_dir)
        finally:
            os.chdir(original_cwd)

    def test_nested_directory_creation(self, temp_output_dir: str):
        """Test creation of nested directories."""
        nested_path = (
            Path(temp_output_dir) / "level1" / "level2" / "level3" / "test.html"
        )

        result_dir = ensure_output_directory(str(nested_path))

        assert nested_path.parent.exists()
        assert Path(result_dir).is_absolute()

    def test_directory_vs_file_path(self, temp_output_dir: str):
        """Test handling of both directory and file paths."""
        # Test with file path
        file_path = Path(temp_output_dir) / "subdir" / "file.html"
        result_dir = ensure_output_directory(str(file_path))
        assert Path(result_dir).exists()

        # Test with directory path
        dir_path = Path(temp_output_dir) / "another_subdir"
        result_dir = ensure_output_directory(str(dir_path))
        assert Path(result_dir).exists()

    def test_create_if_missing_false(self, temp_output_dir: str):
        """Test behavior when create_if_missing=False."""
        non_existent_path = Path(temp_output_dir) / "non_existent" / "test.html"

        with pytest.raises(ValueError, match="Output directory does not exist"):
            ensure_output_directory(str(non_existent_path), create_if_missing=False)

    @pytest.mark.skipif(
        os.name != "nt",
        reason='Windows filesystem restricts characters <, >, *, |, ", which are valid on Unix systems - test validates Windows-specific path validation logic',
    )
    def test_invalid_path_characters(self):
        """Test rejection of invalid path characters on Windows."""
        invalid_paths = [
            "path<with>invalid*chars",
            "path|with|pipes",
            'path"with"quotes',
        ]
        for invalid_path in invalid_paths:
            with pytest.raises(ValueError, match="invalid.*characters"):
                ensure_output_directory(invalid_path)

    def test_empty_filepath_rejection(self):
        """Test rejection of empty filepath."""
        with pytest.raises(ValueError, match="output path cannot be empty"):
            ensure_output_directory("")

    @pytest.mark.skipif(
        os.name != "nt",
        reason="Windows has 260-character path length limit (MAX_PATH) while Unix systems typically allow much longer paths - test validates Windows-specific length validation",
    )
    def test_path_length_limits(self):
        """Test handling of very long paths on Windows."""
        # Create a very long path that exceeds Windows limits
        long_path = str(Path("C:") / ("a" * 300))  # Exceeds Windows limit
        with pytest.raises(ValueError, match="path exceeds maximum length"):
            ensure_output_directory(long_path)

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific reserved names")
    def test_windows_reserved_names(self):
        """Test rejection of Windows reserved names."""
        reserved_names = ["CON", "PRN", "AUX", "COM1", "LPT1"]
        for name in reserved_names:
            # Use pathlib for cross-platform path construction
            test_path = str(Path("C:") / name / "test.html")
            with pytest.raises(ValueError, match="reserved name"):
                ensure_output_directory(test_path)


class TestTimeFormatting:
    """Test time formatting utilities in human-readable format."""

    def test_seconds_formatting_under_threshold(self):
        """Test formatting of seconds under 60-second threshold."""
        assert format_time_duration(0.5) == "0.5 seconds"
        assert format_time_duration(1.0) == "1.0 seconds"
        assert (
            format_time_duration(30.25) == "30.2 seconds"
        )  # Banker's rounding: .25 rounds down to even
        assert format_time_duration(59.9) == "59.9 seconds"
        assert format_time_duration(59.4) == "59.4 seconds"

    def test_minutes_formatting_over_threshold(self):
        """Test formatting of minutes over 60-second threshold."""
        assert format_time_duration(60.0) == "1 minute"
        assert format_time_duration(68.0) == "1 minute 8 seconds"
        assert format_time_duration(120.0) == "2 minutes"
        assert format_time_duration(125.0) == "2 minutes 5 seconds"
        assert format_time_duration(3600.0) == "60 minutes"

    def test_fixed_threshold_boundary(self):
        """Test 60-second threshold boundary behavior."""
        # Just under threshold - should be seconds with decimal
        assert format_time_duration(59.4) == "59.4 seconds"

        # Exactly at threshold - should be minutes
        assert format_time_duration(60.0) == "1 minute"

        # Just over threshold - should be minutes and seconds
        assert format_time_duration(61.0) == "1 minute 1 seconds"

    def test_edge_cases_formatting(self):
        """Test formatting of edge cases."""
        assert format_time_duration(0.0) == "0.0 seconds"
        assert format_time_duration(0.1) == "0.1 seconds"
        assert format_time_duration(0.6) == "0.6 seconds"

        # Large values
        assert format_time_duration(7200.0) == "120 minutes"
        assert format_time_duration(7268.0) == "121 minutes 8 seconds"

    def test_singular_plural_handling(self):
        """Test correct singular/plural handling."""
        # Singular cases
        assert (
            format_time_duration(1.0) == "1.0 seconds"
        )  # Note: still "seconds" for consistency
        assert format_time_duration(60.0) == "1 minute"
        assert format_time_duration(61.0) == "1 minute 1 seconds"

        # Plural cases
        assert format_time_duration(2.0) == "2.0 seconds"
        assert format_time_duration(120.0) == "2 minutes"
        assert format_time_duration(122.0) == "2 minutes 2 seconds"

    def test_exact_minutes_formatting(self):
        """Test formatting when seconds divide evenly into minutes."""
        assert format_time_duration(60.0) == "1 minute"
        assert format_time_duration(120.0) == "2 minutes"
        assert format_time_duration(180.0) == "3 minutes"
        assert format_time_duration(600.0) == "10 minutes"

    def test_negative_time_rejection(self):
        """Test rejection of negative time."""
        with pytest.raises(ValueError, match="duration cannot be negative"):
            format_time_duration(-1.0)

        with pytest.raises(ValueError, match="duration cannot be negative"):
            format_time_duration(-0.1)


class TestFileValidation:
    """Test file validation utilities."""

    def test_valid_file_path(self, sample_data_file: str, sample_data_exists: bool):
        """Test validation of valid file path."""
        if sample_data_exists:
            assert validate_file_path(sample_data_file, must_exist=True) is True

    def test_non_existent_file_with_must_exist(self):
        """Test validation of non-existent file when must_exist=True."""
        with pytest.raises(FileNotFoundError):
            validate_file_path("non_existent_file.json", must_exist=True)

    def test_non_existent_file_without_must_exist(self):
        """Test validation of non-existent file when must_exist=False."""
        assert validate_file_path("non_existent_file.json", must_exist=False) is True

    def test_empty_filepath_rejection(self):
        """Test rejection of empty filepath."""
        with pytest.raises(ValueError, match="filepath cannot be empty"):
            validate_file_path("")


class TestMathUtilities:
    """Test mathematical utility functions."""

    def test_safe_divide_normal(self):
        """Test safe division with normal values."""
        assert safe_divide(10.0, 2.0) == 5.0
        assert safe_divide(7.0, 3.0) == pytest.approx(2.333, rel=1e-2)

    def test_safe_divide_by_zero(self):
        """Test safe division by zero."""
        assert safe_divide(10.0, 0.0) == 0.0
        assert safe_divide(10.0, 0.0, default=99.0) == 99.0

    def test_clamp_value_normal(self):
        """Test value clamping with normal values."""
        assert clamp_value(5.0, 0.0, 10.0) == 5.0
        assert clamp_value(-5.0, 0.0, 10.0) == 0.0
        assert clamp_value(15.0, 0.0, 10.0) == 10.0

    def test_clamp_value_invalid_bounds(self):
        """Test value clamping with invalid bounds."""
        with pytest.raises(
            ValueError, match="Minimum value cannot be greater than maximum"
        ):
            clamp_value(5.0, 10.0, 0.0)

    def test_get_scaled_size_logarithmic(self):
        """Test get_scaled_size with logarithmic scaling."""
        result = get_scaled_size(10.0, 5.0, 2.0, "logarithmic")
        assert result > 5.0

    def test_get_scaled_size_linear(self):
        """Test get_scaled_size with linear scaling."""
        result = get_scaled_size(10.0, 5.0, 2.0, "linear")
        assert result == 25.0  # 5.0 + 10.0 * 2.0


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_followweb_error(self):
        """Test FollowWebError base exception."""
        with pytest.raises(FollowWebError):
            raise FollowWebError("Test error")

    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Configuration test error")

        # Should also be caught as FollowWebError
        with pytest.raises(FollowWebError):
            raise ConfigurationError("Configuration test error")

    def test_data_processing_error(self):
        """Test DataProcessingError exception."""
        with pytest.raises(DataProcessingError):
            raise DataProcessingError("Data processing test error")

        # Should also be caught as FollowWebError
        with pytest.raises(FollowWebError):
            raise DataProcessingError("Data processing test error")

    def test_visualization_error(self):
        """Test VisualizationError exception."""
        with pytest.raises(VisualizationError):
            raise VisualizationError("Visualization test error")

        # Should also be caught as FollowWebError
        with pytest.raises(FollowWebError):
            raise VisualizationError("Visualization test error")

    def test_invalid_characters_in_strategy(self):
        """Test rejection of invalid characters in strategy parameter."""
        invalid_chars = ["<", ">", '"', "|", "?", "*", ":"]
        for char in invalid_chars:
            with pytest.raises(
                ValueError, match="strategy contains invalid filesystem characters"
            ):
                generate_output_filename("test", f"strat{char}egy", 5, "html")

    def test_invalid_characters_in_extension(self):
        """Test rejection of invalid characters in extension parameter."""
        invalid_chars = ["<", ">", '"', "|", "?", "*", ":"]
        for char in invalid_chars:
            with pytest.raises(
                ValueError, match="extension contains invalid filesystem characters"
            ):
                generate_output_filename("test", "strategy", 5, f"ht{char}ml")

    def test_invalid_characters_in_prefix_general(self):
        """Test rejection of general invalid characters in prefix."""
        invalid_chars = ["<", ">", '"', "|", "?", "*"]
        for char in invalid_chars:
            with pytest.raises(
                ValueError, match="prefix contains invalid filesystem characters"
            ):
                generate_output_filename(f"te{char}st", "strategy", 5, "html")

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific colon validation")
    def test_invalid_colon_positions_windows(self):
        """Test rejection of invalid colon positions on Windows."""
        # Colon not at position 1 (drive letter position)
        with pytest.raises(
            ValueError, match="prefix contains invalid colon at position"
        ):
            generate_output_filename("te:st", "strategy", 5, "html")

        # Multiple colons
        with pytest.raises(
            ValueError, match="prefix contains invalid colon at position"
        ):
            generate_output_filename("C:te:st", "strategy", 5, "html")

    @pytest.mark.skipif(os.name == "nt", reason="Unix-specific colon validation")
    def test_colon_rejection_non_windows(self):
        """Test rejection of colons on non-Windows systems."""
        with pytest.raises(
            ValueError, match="prefix contains invalid filesystem character: :"
        ):
            generate_output_filename("te:st", "strategy", 5, "html")
