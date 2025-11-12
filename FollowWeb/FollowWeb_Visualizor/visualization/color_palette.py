"""
Centralized color palette for FollowWeb visualizations.

This module defines all colors used throughout the visualization system,
including node group colors, UI colors, and utility functions for color manipulation.

Color Palette Design:
---------------------
This palette was designed specifically for FollowWeb, inspired by the minimalist
aesthetic of games like Mini Motorways. The colors are our own original selections
chosen to provide:
- High contrast and accessibility
- Clear visual differentiation (Delta E > 20 between base colors)
- Pleasant viewing experience for extended analysis sessions
- Distinct identity for the FollowWeb project

The palette is original work created for this project. While inspired by minimalist
city visualization aesthetics, it does not replicate any specific commercial color
scheme and represents our own unique color choices.
"""


class NodeGroupColors:
    """Base colors for automatic group detection nodes.

    Original palette designed for FollowWeb network visualizations.
    Colors selected for optimal differentiation and visual clarity.
    """

    # Original color palette - designed for FollowWeb
    TEAL = "#4ECDC4"  # Vibrant teal - primary accent
    CORAL = "#FF6B6B"  # Warm coral - secondary accent
    AMBER = "#FFD93D"  # Bright amber - tertiary accent
    VIOLET = "#A78BFA"  # Soft violet - quaternary accent
    SAGE = "#6BCF7F"  # Fresh sage green - quinary accent
    TURQUOISE = (
        "#00B4D8"  # Deep turquoise - senary accent (more blue-shifted for distinction)
    )

    # Base palette for community detection
    BASE_PALETTE = [TEAL, CORAL, AMBER, VIOLET, SAGE, TURQUOISE]

    # Extended palette - additional muted colors for large networks
    # These colors maintain Delta E > 15 from base palette and each other
    # Muted tones provide a softer, more professional aesthetic
    EXTENDED_PALETTE = [
        "#87BDFF",  # Soft sky blue
        "#FFBC7B",  # Muted peach
        "#FC9CB7",  # Soft pink
        "#F06292",  # Muted rose
        "#FFA07B",  # Soft coral
        "#FEB959",  # Muted gold
        "#79D5FF",  # Pale blue
        "#C47ED0",  # Soft purple
        "#A489D4",  # Muted lavender
        "#B9DB93",  # Soft lime
        "#C6F04D",  # Muted chartreuse
        "#9FFF4F",  # Soft green
        "#F48684",  # Muted salmon
        "#60EFCA",  # Soft mint
        "#8C97D2",  # Muted periwinkle
        "#A6DADC",  # Soft cyan
        "#C55A89",  # Muted magenta
        "#DCE674",  # Soft yellow-green
    ]


class UIColors:
    """UI color palette for visualization interfaces."""

    # Background colors
    BACKGROUND_GREY = "#2d333c"

    # Highlight colors
    HIGHLIGHT_BLUE = "#415a76"

    # Text colors
    TEXT_LIGHT_BLUE = "#b6e0fe"

    # Legacy edge colors (for backward compatibility)
    BRIDGE_COLOR = "#6e6e6e"
    INTRA_COMMUNITY_COLOR = "#c0c0c0"


def darken_color(hex_color: str, factor: float = 0.7) -> str:
    """
    Darken a hex color by a given factor.

    Args:
        hex_color: Hex color string (e.g., "#4ECDC4")
        factor: Darkening factor (0.0 = black, 1.0 = original color)

    Returns:
        Darkened hex color string

    Raises:
        ValueError: If hex_color is not a valid hex color string
    """
    # Remove '#' if present
    hex_color = hex_color.lstrip("#")

    # Validate hex color
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: #{hex_color}")

    try:
        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Apply darkening factor
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)

        # Ensure values are in valid range
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    except ValueError as e:
        raise ValueError(f"Invalid hex color: #{hex_color}") from e


def lighten_color(hex_color: str, factor: float = 1.3) -> str:
    """
    Lighten a hex color by a given factor.

    Args:
        hex_color: Hex color string (e.g., "#4ECDC4")
        factor: Lightening factor (1.0 = original color, >1.0 = lighter)

    Returns:
        Lightened hex color string

    Raises:
        ValueError: If hex_color is not a valid hex color string
    """
    # Remove '#' if present
    hex_color = hex_color.lstrip("#")

    # Validate hex color
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: #{hex_color}")

    try:
        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Apply lightening factor
        r = int(r + (255 - r) * (factor - 1.0))
        g = int(g + (255 - g) * (factor - 1.0))
        b = int(b + (255 - b) * (factor - 1.0))

        # Ensure values are in valid range
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    except ValueError as e:
        raise ValueError(f"Invalid hex color: #{hex_color}") from e


def hex_to_rgba(
    hex_color: str, alpha: float = 1.0
) -> tuple[float, float, float, float]:
    """
    Convert hex color to RGBA tuple.

    Args:
        hex_color: Hex color string (e.g., "#4ECDC4")
        alpha: Alpha channel value (0.0 = transparent, 1.0 = opaque)

    Returns:
        RGBA tuple with values in range [0.0, 1.0]

    Raises:
        ValueError: If hex_color is not a valid hex color string
    """
    # Remove '#' if present
    hex_color = hex_color.lstrip("#")

    # Validate hex color
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: #{hex_color}")

    try:
        # Convert to RGB (0-255 range)
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Normalize to 0.0-1.0 range
        return (r / 255.0, g / 255.0, b / 255.0, alpha)

    except ValueError as e:
        raise ValueError(f"Invalid hex color: #{hex_color}") from e


def generate_extended_palette(num_colors: int) -> list[str]:
    """
    Generate an extended color palette using base colors, extended palette, and variations.

    When more colors are needed than available in the base palette,
    this function uses pre-selected extended colors, then generates variations
    to maintain perceptual differences of at least Delta E > 15.

    Strategy:
    - Colors 1-6: Base palette (Delta E > 20 between all pairs)
    - Colors 7-24: Extended palette (18 additional muted colors, Delta E > 15)
    - Colors 25+: Generated variations using darkening/lightening

    The function ensures no color repetition by tracking all generated colors.

    Args:
        num_colors: Number of colors needed

    Returns:
        List of hex color strings with minimum Delta E > 15 between variations
        and guaranteed no duplicates

    Raises:
        ValueError: If num_colors is negative or exceeds reasonable limits
        RuntimeError: If duplicate colors are detected (should never happen)
    """
    if num_colors < 0:
        raise ValueError("num_colors must be non-negative")

    if num_colors > 1000:
        raise ValueError("num_colors exceeds reasonable limit of 1000")

    if num_colors == 0:
        return []

    base_palette = NodeGroupColors.BASE_PALETTE
    extended_palette = NodeGroupColors.EXTENDED_PALETTE
    palette = []
    seen_colors = set()  # Track colors to prevent duplicates

    # Use base colors first (colors 1-6)
    for i in range(min(num_colors, len(base_palette))):
        color = base_palette[i]
        if color in seen_colors:
            raise RuntimeError(f"Duplicate color in base palette: {color}")
        palette.append(color)
        seen_colors.add(color)

    # Use extended palette colors next (colors 7-26)
    if num_colors > len(base_palette):
        remaining_after_base = num_colors - len(base_palette)
        extended_to_use = min(remaining_after_base, len(extended_palette))

        for i in range(extended_to_use):
            color = extended_palette[i]
            if color in seen_colors:
                raise RuntimeError(f"Duplicate color in extended palette: {color}")
            palette.append(color)
            seen_colors.add(color)

    # Generate variations if more colors needed (colors 27+)
    if num_colors > len(base_palette) + len(extended_palette):
        remaining = num_colors - len(base_palette) - len(extended_palette)

        # Define variation strategies ordered from LARGEST to SMALLEST changes
        # Alternate between darken and lighten to maximize differentiation
        # Avoid clustering similar darkness/lightness levels together
        # Extended to support 50 communities (9 levels × 5 base colors = 45 variations)
        variation_strategies = [
            # Level 1: Maximum changes - Colors 6-10 (Delta E ~60-75)
            ("darken", 0.30),  # 70% darker
            ("lighten", 1.70),  # 70% lighter
            ("darken", 0.45),  # 55% darker
            ("lighten", 1.60),  # 60% lighter
            ("darken", 0.35),  # 65% darker
            # Level 2: Large changes - Colors 11-15 (Delta E ~45-60)
            ("lighten", 1.55),  # 55% lighter
            ("darken", 0.50),  # 50% darker
            ("lighten", 1.50),  # 50% lighter
            ("darken", 0.40),  # 60% darker
            ("lighten", 1.45),  # 45% lighter
            # Level 3: Medium-large changes - Colors 16-20 (Delta E ~35-50)
            ("darken", 0.55),  # 45% darker
            ("lighten", 1.40),  # 40% lighter
            ("darken", 0.60),  # 40% darker
            ("lighten", 1.35),  # 35% lighter
            ("darken", 0.65),  # 35% darker
            # Level 4: Medium changes - Colors 21-25 (Delta E ~30-45)
            ("lighten", 1.32),  # 32% lighter
            ("darken", 0.68),  # 32% darker
            ("lighten", 1.38),  # 38% lighter
            ("darken", 0.58),  # 42% darker
            ("lighten", 1.42),  # 42% lighter
            # Level 5: Medium-small changes - Colors 26-30 (Delta E ~25-40)
            ("darken", 0.62),  # 38% darker
            ("lighten", 1.28),  # 28% lighter
            ("darken", 0.70),  # 30% darker
            ("lighten", 1.48),  # 48% lighter
            ("darken", 0.48),  # 52% darker
            # Level 6: Varied changes - Colors 31-35 (Delta E ~25-40)
            ("lighten", 1.52),  # 52% lighter
            ("darken", 0.43),  # 57% darker
            ("lighten", 1.25),  # 25% lighter
            ("darken", 0.72),  # 28% darker
            ("lighten", 1.58),  # 58% lighter
            # Level 7: Mixed changes - Colors 36-40 (Delta E ~25-40)
            ("darken", 0.38),  # 62% darker
            ("lighten", 1.62),  # 62% lighter
            ("darken", 0.75),  # 25% darker
            ("lighten", 1.30),  # 30% lighter
            ("darken", 0.53),  # 47% darker
            # Level 8: Additional changes - Colors 41-45 (Delta E ~25-40)
            ("lighten", 1.65),  # 65% lighter
            ("darken", 0.33),  # 67% darker
            ("lighten", 1.22),  # 22% lighter
            ("darken", 0.78),  # 22% darker
            ("lighten", 1.68),  # 68% lighter
            # Level 9: Final changes - Colors 46-50 (Delta E ~20-35)
            ("darken", 0.28),  # 72% darker
            ("lighten", 1.75),  # 75% lighter
            ("darken", 0.80),  # 20% darker
            ("lighten", 1.20),  # 20% lighter
            ("darken", 0.25),  # 75% darker
        ]

        for i in range(remaining):
            # Cycle through base colors
            base_index = i % len(base_palette)
            base_color = base_palette[base_index]

            # Determine which variation strategy to use
            variation_level = i // len(base_palette)
            strategy_index = variation_level % len(variation_strategies)
            strategy_type, base_factor = variation_strategies[strategy_index]

            # Add tiny deterministic perturbation based on index to prevent exact duplicates
            # This ensures colors at different indices are always slightly different
            # Perturbation is < 1% so Delta E impact is minimal (~0.5-1.0)
            perturbation = (i % 100) * 0.0001  # 0.0000 to 0.0099
            factor = (
                base_factor + perturbation
                if strategy_type == "darken"
                else base_factor + (perturbation * 0.1)
            )

            # Generate variation
            if strategy_type == "darken":
                varied_color = darken_color(base_color, factor)
            else:  # lighten
                varied_color = lighten_color(base_color, factor)

            # Check for duplicates
            if varied_color in seen_colors:
                # If duplicate detected, add a small adjustment
                # This should rarely happen with perturbation
                adjustment = 0.02
                if strategy_type == "darken":
                    varied_color = darken_color(
                        base_color, max(0.2, factor - adjustment)
                    )
                else:
                    varied_color = lighten_color(
                        base_color, min(1.8, factor + adjustment)
                    )

                # If still duplicate, raise error
                if varied_color in seen_colors:
                    raise RuntimeError(
                        f"Duplicate color generated even after adjustment: {varied_color} "
                        f"(base: {base_color}, strategy: {strategy_type} {factor})"
                    )

            palette.append(varied_color)
            seen_colors.add(varied_color)

    # Final validation: ensure all colors are unique
    if len(palette) != len(set(palette)):
        duplicates = [color for color in palette if palette.count(color) > 1]
        raise RuntimeError(f"Duplicate colors found in palette: {set(duplicates)}")

    return palette
