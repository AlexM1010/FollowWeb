"""
Unit tests for color palette functionality.

Tests the centralized color palette system including:
- Base color definitions
- Color manipulation functions (darken, lighten, hex_to_rgba)
- Extended palette generation with no duplicates
- Color differentiation (Delta E > 15)
"""

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.visualization]
from FollowWeb_Visualizor.visualization.color_palette import (
    NodeGroupColors,
    UIColors,
    darken_color,
    lighten_color,
    hex_to_rgba,
    generate_extended_palette,
)


class TestNodeGroupColors:
    """Test NodeGroupColors class and base palette."""

    def test_base_colors_defined(self):
        """Test that all base colors are defined."""
        assert NodeGroupColors.TEAL == "#4ECDC4"
        assert NodeGroupColors.CORAL == "#FF6B6B"
        assert NodeGroupColors.AMBER == "#FFD93D"
        assert NodeGroupColors.VIOLET == "#A78BFA"
        assert NodeGroupColors.SAGE == "#6BCF7F"
        assert NodeGroupColors.TURQUOISE == "#00B4D8"

    def test_base_palette_length(self):
        """Test that base palette has expected number of colors."""
        assert len(NodeGroupColors.BASE_PALETTE) == 6

    def test_base_palette_no_duplicates(self):
        """Test that base palette has no duplicate colors."""
        palette = NodeGroupColors.BASE_PALETTE
        assert len(palette) == len(set(palette))


class TestUIColors:
    """Test UIColors class."""

    def test_ui_colors_defined(self):
        """Test that all UI colors are defined."""
        assert UIColors.BACKGROUND_GREY == "#1E2530"
        assert UIColors.HIGHLIGHT_BLUE == "#4A6B8A"
        assert UIColors.TEXT_LIGHT_BLUE == "#A8D5F2"
        assert UIColors.BRIDGE_COLOR == "#6e6e6e"
        assert UIColors.INTRA_COMMUNITY_COLOR == "#c0c0c0"


class TestDarkenColor:
    """Test darken_color function."""

    def test_darken_basic(self):
        """Test basic darkening operation."""
        result = darken_color("#ffffff", 0.5)
        assert result == "#7f7f7f"

    def test_darken_with_hash(self):
        """Test darkening with # prefix."""
        result = darken_color("#4ECDC4", 0.7)
        assert result.startswith("#")
        assert len(result) == 7

    def test_darken_without_hash(self):
        """Test darkening without # prefix."""
        result = darken_color("4ECDC4", 0.7)
        assert result.startswith("#")
        assert len(result) == 7

    def test_darken_zero_factor(self):
        """Test darkening with factor 0 produces black."""
        result = darken_color("#ffffff", 0.0)
        assert result == "#000000"

    def test_darken_one_factor(self):
        """Test darkening with factor 1.0 produces original color."""
        original = "#4ECDC4"
        result = darken_color(original, 1.0)
        assert result.lower() == original.lower()

    def test_darken_invalid_hex(self):
        """Test that invalid hex color raises ValueError."""
        with pytest.raises(ValueError):
            darken_color("#invalid", 0.5)

    def test_darken_invalid_length(self):
        """Test that invalid length hex color raises ValueError."""
        with pytest.raises(ValueError):
            darken_color("#fff", 0.5)


class TestLightenColor:
    """Test lighten_color function."""

    def test_lighten_basic(self):
        """Test basic lightening operation."""
        result = lighten_color("#000000", 1.5)
        assert result == "#7f7f7f"

    def test_lighten_with_hash(self):
        """Test lightening with # prefix."""
        result = lighten_color("#4ECDC4", 1.3)
        assert result.startswith("#")
        assert len(result) == 7

    def test_lighten_without_hash(self):
        """Test lightening without # prefix."""
        result = lighten_color("4ECDC4", 1.3)
        assert result.startswith("#")
        assert len(result) == 7

    def test_lighten_one_factor(self):
        """Test lightening with factor 1.0 produces original color."""
        original = "#4ECDC4"
        result = lighten_color(original, 1.0)
        assert result.lower() == original.lower()

    def test_lighten_caps_at_white(self):
        """Test that lightening caps at white (#ffffff)."""
        result = lighten_color("#ffffff", 2.0)
        assert result == "#ffffff"

    def test_lighten_invalid_hex(self):
        """Test that invalid hex color raises ValueError."""
        with pytest.raises(ValueError):
            lighten_color("#invalid", 1.5)

    def test_lighten_invalid_length(self):
        """Test that invalid length hex color raises ValueError."""
        with pytest.raises(ValueError):
            lighten_color("#fff", 1.5)


class TestHexToRgba:
    """Test hex_to_rgba function."""

    def test_hex_to_rgba_basic(self):
        """Test basic hex to RGBA conversion."""
        result = hex_to_rgba("#ffffff")
        assert result == (1.0, 1.0, 1.0, 1.0)

    def test_hex_to_rgba_black(self):
        """Test black color conversion."""
        result = hex_to_rgba("#000000")
        assert result == (0.0, 0.0, 0.0, 1.0)

    def test_hex_to_rgba_with_alpha(self):
        """Test conversion with custom alpha."""
        result = hex_to_rgba("#ffffff", 0.5)
        assert result == (1.0, 1.0, 1.0, 0.5)

    def test_hex_to_rgba_without_hash(self):
        """Test conversion without # prefix."""
        result = hex_to_rgba("ffffff")
        assert result == (1.0, 1.0, 1.0, 1.0)

    def test_hex_to_rgba_teal(self):
        """Test teal color conversion."""
        result = hex_to_rgba("#4ECDC4")
        r, g, b, a = result
        assert 0.30 < r < 0.31  # 78/255 ≈ 0.306
        assert 0.80 < g < 0.81  # 205/255 ≈ 0.804
        assert 0.76 < b < 0.77  # 196/255 ≈ 0.769
        assert a == 1.0

    def test_hex_to_rgba_invalid_hex(self):
        """Test that invalid hex color raises ValueError."""
        with pytest.raises(ValueError):
            hex_to_rgba("#invalid")

    def test_hex_to_rgba_invalid_length(self):
        """Test that invalid length hex color raises ValueError."""
        with pytest.raises(ValueError):
            hex_to_rgba("#fff")


class TestGenerateExtendedPalette:
    """Test generate_extended_palette function."""

    def test_generate_zero_colors(self):
        """Test generating zero colors returns empty list."""
        result = generate_extended_palette(0)
        assert result == []

    def test_generate_one_color(self):
        """Test generating one color."""
        result = generate_extended_palette(1)
        assert len(result) == 1
        assert result[0] == NodeGroupColors.TEAL

    def test_generate_base_palette_size(self):
        """Test generating exactly base palette size."""
        result = generate_extended_palette(6)
        assert len(result) == 6
        assert result == NodeGroupColors.BASE_PALETTE

    def test_generate_extended_palette_size(self):
        """Test generating more than base palette size."""
        result = generate_extended_palette(10)
        assert len(result) == 10

    def test_generate_large_palette(self):
        """Test generating large palette (50 colors for 50 communities)."""
        result = generate_extended_palette(50)
        assert len(result) == 50

    def test_no_duplicates_small(self):
        """Test that small palette has no duplicates."""
        result = generate_extended_palette(10)
        assert len(result) == len(set(result))

    def test_no_duplicates_medium(self):
        """Test that medium palette has no duplicates."""
        result = generate_extended_palette(25)
        assert len(result) == len(set(result))

    def test_no_duplicates_large(self):
        """Test that large palette has no duplicates."""
        result = generate_extended_palette(50)
        assert len(result) == len(set(result))

    def test_all_valid_hex_colors(self):
        """Test that all generated colors are valid hex colors."""
        result = generate_extended_palette(20)
        for color in result:
            assert color.startswith("#")
            assert len(color) == 7
            # Verify it's valid hex
            int(color[1:], 16)

    def test_negative_colors_raises_error(self):
        """Test that negative num_colors raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            generate_extended_palette(-1)

    def test_excessive_colors_raises_error(self):
        """Test that excessive num_colors raises ValueError."""
        with pytest.raises(ValueError, match="reasonable limit"):
            generate_extended_palette(1001)

    def test_first_colors_match_base(self):
        """Test that first N colors match base palette."""
        result = generate_extended_palette(12)
        for i in range(6):
            assert result[i] == NodeGroupColors.BASE_PALETTE[i]
        # Verify the new base colors are present
        assert NodeGroupColors.TEAL in result[:6]
        assert NodeGroupColors.CORAL in result[:6]
        assert NodeGroupColors.AMBER in result[:6]
        assert NodeGroupColors.VIOLET in result[:6]
        assert NodeGroupColors.SAGE in result[:6]
        assert NodeGroupColors.TURQUOISE in result[:6]

    def test_variations_are_different(self):
        """Test that color variations are different from base colors."""
        result = generate_extended_palette(12)
        # Colors 7-12 should be variations, not exact matches
        for i in range(6, 12):
            assert result[i] not in NodeGroupColors.BASE_PALETTE


class TestColorDifferentiation:
    """Test that colors have sufficient perceptual difference."""

    def _rgb_to_lab(self, r: float, g: float, b: float) -> tuple[float, float, float]:
        """Convert RGB to LAB color space for Delta E calculation."""
        # Convert RGB to XYZ
        r = r / 255.0
        g = g / 255.0
        b = b / 255.0

        # Apply gamma correction
        r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
        g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
        b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92

        # Convert to XYZ (D65 illuminant)
        x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
        y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
        z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

        # Convert XYZ to LAB
        x = x / 0.95047
        y = y / 1.00000
        z = z / 1.08883

        x = x ** (1 / 3) if x > 0.008856 else (7.787 * x) + (16 / 116)
        y = y ** (1 / 3) if y > 0.008856 else (7.787 * y) + (16 / 116)
        z = z ** (1 / 3) if z > 0.008856 else (7.787 * z) + (16 / 116)

        L = (116 * y) - 16
        a = 500 * (x - y)
        b_val = 200 * (y - z)

        return (L, a, b_val)

    def _delta_e(self, color1: str, color2: str) -> float:
        """Calculate Delta E (CIE76) between two hex colors."""
        # Convert hex to RGB
        r1 = int(color1[1:3], 16)
        g1 = int(color1[3:5], 16)
        b1 = int(color1[5:7], 16)

        r2 = int(color2[1:3], 16)
        g2 = int(color2[3:5], 16)
        b2 = int(color2[5:7], 16)

        # Convert to LAB
        L1, a1, b1_val = self._rgb_to_lab(r1, g1, b1)
        L2, a2, b2_val = self._rgb_to_lab(r2, g2, b2)

        # Calculate Delta E
        return ((L2 - L1) ** 2 + (a2 - a1) ** 2 + (b2_val - b1_val) ** 2) ** 0.5

    def test_base_palette_differentiation(self):
        """Test that base palette colors have Delta E > 20."""
        palette = NodeGroupColors.BASE_PALETTE
        min_delta_e = float("inf")

        for i in range(len(palette)):
            for j in range(i + 1, len(palette)):
                delta_e = self._delta_e(palette[i], palette[j])
                min_delta_e = min(min_delta_e, delta_e)

        # Base palette should have excellent differentiation
        assert min_delta_e > 20, f"Base palette min Delta E: {min_delta_e}"

    def test_extended_palette_differentiation(self):
        """Test that extended palette variations have Delta E > 15."""
        palette = generate_extended_palette(15)

        # Check variations (colors 6-15) against their base colors
        for i in range(5, 15):
            base_index = i % 5
            base_color = palette[base_index]
            varied_color = palette[i]

            delta_e = self._delta_e(base_color, varied_color)
            # Variations should have minimum Delta E > 15
            assert delta_e > 15, (
                f"Variation {i} (base {base_index}): Delta E {delta_e:.1f} < 15"
            )
