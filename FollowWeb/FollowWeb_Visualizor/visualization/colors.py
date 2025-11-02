"""
Color scheme generation module for FollowWeb visualization.

This module handles community color generation and scaling utilities for visualization components.
"""

import math
from typing import Dict, Tuple, Union

import matplotlib.pyplot as plt

from ..core.exceptions import VisualizationError
from ..data.cache import get_cache_manager
from ..utils.validation import (
    validate_choice,
    validate_multiple_non_negative,
    validate_range,
)


def get_community_colors(
    num_communities: int,
) -> Dict[str, Dict[int, Union[str, Tuple[float, ...]]]]:
    """
    Generates a color map for communities with caching.

    Args:
        num_communities: Number of communities to generate colors for

    Returns:
        dict: Dictionary with 'hex' and 'rgba' keys, each mapping community_id -> color
              - 'hex': Maps community_id to hex color string (for HTML)
              - 'rgba': Maps community_id to RGBA tuple (for matplotlib)

    Raises:
        ValueError: If num_communities is negative or exceeds reasonable limits
        VisualizationError: If color generation fails due to matplotlib issues
    """
    if not isinstance(num_communities, int):
        raise ValueError("num_communities must be an integer")

    validate_range(num_communities, "num_communities", 0, 1000)

    # Check cache first
    cache_manager = get_cache_manager()
    cached_colors = cache_manager.get_cached_community_colors(num_communities)
    if cached_colors is not None:
        return cached_colors

    try:
        if num_communities > 0:
            # Use matplotlib colormap with error handling
            try:
                palette = plt.colormaps.get_cmap("viridis").resampled(num_communities)
                colors = palette(range(num_communities))
            except Exception as e:
                raise VisualizationError(
                    f"Failed to generate colormap for {num_communities} communities: {e}"
                ) from e

            # Generate color dictionaries with validation
            hex_colors = {}
            rgba_colors = {}

            for i, color in enumerate(colors):
                try:
                    # Validate color tuple has at least 3 components (RGB)
                    if len(color) < 3:
                        raise VisualizationError(
                            f"invalid color format for community {i}"
                        )

                    # Convert to hex with bounds checking
                    r, g, b = color[0], color[1], color[2]
                    if not all(0 <= val <= 1 for val in [r, g, b]):
                        raise VisualizationError(
                            f"color values out of range for community {i}"
                        )

                    hex_color = (
                        f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
                    )
                    hex_colors[i] = hex_color
                    rgba_colors[i] = color

                except Exception as e:
                    raise VisualizationError(
                        f"Failed to process color for community {i}: {e}"
                    ) from e

            result = {"hex": hex_colors, "rgba": rgba_colors}
        else:
            # Default case for zero communities
            result = {"hex": {0: "#808080"}, "rgba": {0: (0.5, 0.5, 0.5, 1.0)}}

        # Cache the result before returning
        cache_manager.cache_community_colors(num_communities, result)

        return result

    except Exception as e:
        if isinstance(e, (ValueError, VisualizationError)):
            raise
        raise VisualizationError(
            f"Unexpected error generating community colors: {e}"
        ) from e


def get_scaled_size(
    value: float, base_size: float, multiplier: float, algorithm: str
) -> float:
    """
    Helper to calculate node/edge size based on a metric's value.

    Args:
        value: The metric value to scale
        base_size: Base size to add to the scaled result
        multiplier: Scaling multiplier
        algorithm: Scaling algorithm - 'logarithmic' or 'linear'

    Returns:
        float: Scaled size value

    Raises:
        ValueError: If algorithm is not 'logarithmic' or 'linear'
    """
    validate_multiple_non_negative(
        (value, "value"), (base_size, "base_size"), (multiplier, "multiplier")
    )

    if algorithm == "logarithmic":
        # Use log1p (log(1+x)) to handle 0 values gracefully
        return base_size + math.log1p(value) * multiplier
    elif algorithm == "linear":
        return base_size + value * multiplier
    else:
        validate_choice(algorithm, "scaling algorithm", ["logarithmic", "linear"])


def scale_value(
    value: float, base_size: float, multiplier: float, algorithm: str
) -> float:
    """
    Applies logarithmic or linear scaling to numeric values.

    Args:
        value: The value to scale
        base_size: Base size to add to the scaled result
        multiplier: Scaling multiplier
        algorithm: Scaling algorithm - 'logarithmic' or 'linear'

    Returns:
        float: Scaled value

    Raises:
        ValueError: If algorithm is not 'logarithmic' or 'linear'
        ValueError: If value, base_size, or multiplier is negative
    """
    return get_scaled_size(value, base_size, multiplier, algorithm)
