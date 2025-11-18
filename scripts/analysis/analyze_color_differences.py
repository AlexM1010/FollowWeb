"""Analyze color differences and ensure sufficient visual distinction."""

import math
from typing import List, Tuple


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex to RGB."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert RGB to LAB color space for perceptual difference calculation."""
    # Normalize RGB to 0-1
    r, g, b = r / 255.0, g / 255.0, b / 255.0

    # Convert to linear RGB
    def to_linear(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = to_linear(r), to_linear(g), to_linear(b)

    # Convert to XYZ
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    # Normalize for D65 illuminant
    x, y, z = x / 0.95047, y / 1.00000, z / 1.08883

    # Convert to LAB
    def f(t):
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16 / 116)

    fx, fy, fz = f(x), f(y), f(z)

    L = (116 * fy) - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)

    return L, a, b


def delta_e_cie76(color1: str, color2: str) -> float:
    """Calculate CIE76 Delta E (perceptual color difference)."""
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)

    L1, a1, b1_lab = rgb_to_lab(r1, g1, b1)
    L2, a2, b2_lab = rgb_to_lab(r2, g2, b2)

    return math.sqrt((L2 - L1) ** 2 + (a2 - a1) ** 2 + (b2_lab - b1_lab) ** 2)


def analyze_palette(colors: List[Tuple[str, str]]) -> None:
    """Analyze color palette for sufficient differentiation."""
    print("=" * 80)
    print("COLOR PALETTE ANALYSIS")
    print("=" * 80)
    print()

    # Display colors
    print("COLORS IN PALETTE:")
    print("-" * 80)
    for name, hex_color in colors:
        r, g, b = hex_to_rgb(hex_color)
        print(f"{name:20} {hex_color:8} RGB({r:3}, {g:3}, {b:3})")
    print()

    # Calculate all pairwise differences
    print("PERCEPTUAL DIFFERENCES (Delta E CIE76):")
    print("-" * 80)
    print("Delta E < 2.3:  Not perceptible by human eyes")
    print("Delta E 2.3-5:  Perceptible through close observation")
    print("Delta E 5-10:   Perceptible at a glance")
    print("Delta E 10-50:  Colors are more similar than opposite")
    print("Delta E > 50:   Colors are exact opposite")
    print()

    min_diff = float("inf")
    min_pair = None

    print(f"{'Color 1':<20} {'Color 2':<20} {'Delta E':>10} {'Status'}")
    print("-" * 80)

    for i, (name1, color1) in enumerate(colors):
        for name2, color2 in colors[i + 1 :]:
            diff = delta_e_cie76(color1, color2)

            if diff < 10:
                status = "⚠️  TOO SIMILAR"
            elif diff < 20:
                status = "⚡ ACCEPTABLE"
            else:
                status = "✓  DISTINCT"

            print(f"{name1:<20} {name2:<20} {diff:>10.2f} {status}")

            if diff < min_diff:
                min_diff = diff
                min_pair = (name1, name2)

    print()
    print("=" * 80)
    print(f"MINIMUM DIFFERENCE: {min_diff:.2f} between {min_pair[0]} and {min_pair[1]}")

    if min_diff < 10:
        print("❌ WARNING: Some colors are too similar (Delta E < 10)")
        print("   Recommendation: Increase color separation")
    elif min_diff < 20:
        print("⚠️  CAUTION: Some colors are marginally distinct (Delta E < 20)")
        print("   Recommendation: Consider increasing separation for better visibility")
    else:
        print("✓  EXCELLENT: All colors are sufficiently distinct (Delta E > 20)")
    print("=" * 80)


def generate_improved_palette() -> List[Tuple[str, str]]:
    """Generate an improved palette with better color separation."""
    # Tuned palette with maximum perceptual separation
    return [
        ("Green", "#2ECC71"),  # Bright green (hue 145°)
        ("Blue", "#3498DB"),  # Bright blue (hue 204°)
        ("Orange", "#E67E22"),  # Bright orange (hue 28°)
        ("Red", "#E74C3C"),  # Bright red (hue 6°)
        ("Purple", "#9B59B6"),  # Bright purple (hue 283°)
        ("Cyan", "#1ABC9C"),  # Bright cyan (hue 168°)
        ("Yellow", "#F1C40F"),  # Bright yellow (hue 48°)
        ("Pink", "#FF6B9D"),  # Bright pink (hue 340°)
    ]


if __name__ == "__main__":
    # Current palette
    print("\n")
    print("CURRENT PALETTE:")
    current_colors = [
        ("Teal", "#4ECDC4"),
        ("Coral", "#FF6B6B"),
        ("Amber", "#FFD93D"),
        ("Violet", "#A78BFA"),
        ("Sage", "#6BCF7F"),
        ("Turquoise", "#00B4D8"),
    ]
    analyze_palette(current_colors)

    print("\n\n")
    print("SUGGESTED IMPROVED PALETTE:")
    improved_colors = generate_improved_palette()
    analyze_palette(improved_colors[:5])  # First 5 colors

    print("\n\n")
    print("EXTENDED PALETTE (8 colors):")
    analyze_palette(improved_colors)

    # Test darkened variations
    print("\n\n")
    print("DARKENED VARIATIONS TEST:")
    from FollowWeb.FollowWeb_Visualizor.visualization import darken_color

    darkened = []
    for name, color in current_colors:
        dark_color = darken_color(color, 0.7)
        darkened.append((f"{name} (70%)", dark_color))

    # Check if darkened colors are distinct from originals
    all_colors = current_colors + darkened
    print(f"\nChecking {len(all_colors)} colors (original + darkened)...")

    min_diff = float("inf")
    for i, (name1, color1) in enumerate(all_colors):
        for name2, color2 in all_colors[i + 1 :]:
            diff = delta_e_cie76(color1, color2)
            if diff < min_diff:
                min_diff = diff
                min_pair = (name1, name2)

    print(f"Minimum difference in extended palette: {min_diff:.2f}")
    print(f"Between: {min_pair[0]} and {min_pair[1]}")
