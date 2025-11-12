# FollowWeb Color Palette Guide

This guide documents the centralized color palette system for FollowWeb visualizations.

## Overview

The color palette system provides consistent colors across all visualization components, including:
- Node group colors for community detection
- UI colors for interactive controls
- Utility functions for color manipulation

## Base Colors

### Node Group Colors

These colors are used for automatic group/community detection in network visualizations:

| Color Name | Hex Code | Usage |
|------------|----------|-------|
| Green | `#62CB89` | Primary community color |
| Blue | `#47BEE1` | Secondary community color |
| Blue Alt | `#6C95C1` | Alternative blue for variety |
| Orange | `#FFB242` | Accent community color |
| Purple | `#F15668` | Highlight community color |

**Base Palette Order**: Green → Blue → Orange → Purple → Blue Alt

### UI Colors

These colors are used for visualization interface elements:

| Color Name | Hex Code | Usage |
|------------|----------|-------|
| Background Grey | `#2d333c` | Panel backgrounds, control backgrounds |
| Highlight Blue | `#415a76` | Button backgrounds, active states |
| Text Light Blue | `#b6e0fe` | Text, labels, icons |

### Legacy Edge Colors

For backward compatibility with existing configurations:

| Color Name | Hex Code | Usage |
|------------|----------|-------|
| Bridge Color | `#6e6e6e` | Edges between different communities |
| Intra Community Color | `#c0c0c0` | Edges within the same community |

## Color Manipulation Functions

### `darken_color(hex_color, factor=0.7)`

Darkens a hex color by multiplying RGB values by the factor.

```python
from FollowWeb.FollowWeb_Visualizor.visualization import darken_color

# Darken green by 30%
dark_green = darken_color("#62CB89", 0.7)  # Returns: #448e5f
```

**Parameters:**
- `hex_color` (str): Hex color string (e.g., "#62CB89")
- `factor` (float): Darkening factor (0.0 = black, 1.0 = original color)

### `lighten_color(hex_color, factor=1.3)`

Lightens a hex color by interpolating towards white.

```python
from FollowWeb.FollowWeb_Visualizor.visualization import lighten_color

# Lighten green by 30%
light_green = lighten_color("#62CB89", 1.3)  # Returns: #91daac
```

**Parameters:**
- `hex_color` (str): Hex color string (e.g., "#62CB89")
- `factor` (float): Lightening factor (1.0 = original color, >1.0 = lighter)

### `hex_to_rgba(hex_color, alpha=1.0)`

Converts hex color to RGBA tuple for matplotlib and other libraries.

```python
from FollowWeb.FollowWeb_Visualizor.visualization import hex_to_rgba

# Convert to RGBA
rgba = hex_to_rgba("#62CB89")  # Returns: (0.384, 0.796, 0.537, 1.0)
rgba_transparent = hex_to_rgba("#62CB89", 0.5)  # 50% opacity
```

**Parameters:**
- `hex_color` (str): Hex color string (e.g., "#62CB89")
- `alpha` (float): Alpha channel value (0.0 = transparent, 1.0 = opaque)

**Returns:** Tuple of (r, g, b, a) with values in range [0.0, 1.0]

### `generate_extended_palette(num_colors)`

Generates an extended color palette for large numbers of communities.

```python
from FollowWeb.FollowWeb_Visualizor.visualization import generate_extended_palette

# Generate palette for 10 communities
palette = generate_extended_palette(10)
# Returns: ['#62CB89', '#47BEE1', '#FFB242', '#F15668', '#6C95C1', 
#           '#4ea26d', '#3898b4', '#cc8e34', '#c04453', '#56779a']
```

**Behavior:**
- Uses base palette colors first (5 colors)
- Generates darkened variations when more colors are needed
- Cycles through base colors, darkening progressively (70%, 50%, 30%, etc.)

**Parameters:**
- `num_colors` (int): Number of colors needed (0-1000)

**Returns:** List of hex color strings

## Usage in Configuration

### Adding UI Colors to Config Files

```json
{
  "ui_background_color": "#2d333c",
  "ui_highlight_color": "#415a76",
  "ui_text_color": "#b6e0fe",
  "bridge_color": "#6e6e6e",
  "intra_community_color": "#c0c0c0"
}
```

### Using in Python Code

```python
from FollowWeb.FollowWeb_Visualizor.visualization import (
    NodeGroupColors,
    UIColors,
    generate_extended_palette
)

# Access base colors
primary_color = NodeGroupColors.GREEN
background = UIColors.BACKGROUND_GREY

# Generate palette for communities
num_communities = 8
palette = generate_extended_palette(num_communities)
```

## Integration with Existing Systems

The color palette integrates seamlessly with the existing `get_community_colors()` function:

```python
from FollowWeb.FollowWeb_Visualizor.visualization import get_community_colors

# Get colors for 5 communities
colors = get_community_colors(5)
# Returns: {
#   'hex': {0: '#62CB89', 1: '#47BEE1', 2: '#FFB242', 3: '#F15668', 4: '#6C95C1'},
#   'rgba': {0: (0.384, 0.796, 0.537, 1.0), ...}
# }
```

## HTML Template Integration

The UI colors are automatically passed to HTML templates via the config object:

```html
<style>
    #controls {
        background: {{ config.ui_background_color }}f2;
        border: 1px solid {{ config.ui_highlight_color }};
    }
    
    #controls button {
        background: {{ config.ui_highlight_color }};
        color: {{ config.ui_text_color }};
    }
</style>
```

## Color Accessibility

The chosen colors provide good contrast and are distinguishable for most users:

- **Green (#62CB89)**: Medium saturation, good visibility
- **Blue (#47BEE1)**: Bright, high contrast
- **Orange (#FFB242)**: Warm, attention-grabbing
- **Purple (#F15668)**: Distinct from other colors
- **UI Colors**: High contrast between background (#2d333c) and text (#b6e0fe)

## Extending the Palette

To add new base colors, edit `color_palette.py`:

```python
class NodeGroupColors:
    GREEN = "#62CB89"
    BLUE = "#47BEE1"
    BLUE_ALT = "#6C95C1"
    ORANGE = "#FFB242"
    PURPLE = "#F15668"
    # Add new colors here
    TEAL = "#4ECDC4"
    
    BASE_PALETTE = [GREEN, BLUE, ORANGE, PURPLE, BLUE_ALT, TEAL]
```

## Testing

Run the color palette test script:

```bash
python test_color_palette.py
```

This validates:
- Base color definitions
- UI color definitions
- Color manipulation functions
- Hex to RGBA conversion
- Extended palette generation
- Integration with existing systems

## Migration Notes

### From matplotlib colormap to centralized palette

**Before:**
```python
palette = plt.colormaps.get_cmap("viridis").resampled(num_communities)
colors = palette(range(num_communities))
```

**After:**
```python
from FollowWeb.FollowWeb_Visualizor.visualization import generate_extended_palette
hex_palette = generate_extended_palette(num_communities)
```

### Benefits of centralized palette:
- Consistent colors across all visualizations
- No matplotlib dependency for color generation
- Easier to customize and maintain
- Better performance (no colormap resampling)
- Predictable color assignment

## API Reference

### Classes

#### `NodeGroupColors`
Static class containing base node group color definitions.

**Attributes:**
- `GREEN`: Primary community color
- `BLUE`: Secondary community color
- `BLUE_ALT`: Alternative blue
- `ORANGE`: Accent color
- `PURPLE`: Highlight color
- `BASE_PALETTE`: List of all base colors in order

#### `UIColors`
Static class containing UI color definitions.

**Attributes:**
- `BACKGROUND_GREY`: Panel backgrounds
- `HIGHLIGHT_BLUE`: Button backgrounds
- `TEXT_LIGHT_BLUE`: Text and labels
- `BRIDGE_COLOR`: Inter-community edges
- `INTRA_COMMUNITY_COLOR`: Intra-community edges

### Functions

All functions are available from the visualization module:

```python
from FollowWeb.FollowWeb_Visualizor.visualization import (
    darken_color,
    lighten_color,
    hex_to_rgba,
    generate_extended_palette,
)
```

See function descriptions above for detailed usage.
