# FollowWeb Color Palette

## Overview

FollowWeb uses an original color palette designed specifically for network visualization. The palette was inspired by minimalist aesthetics found in games like Mini Motorways, but uses completely distinct color values to give FollowWeb its own unique visual identity.

## Design Philosophy

The color palette is designed to provide:
- **High contrast and accessibility** - Colors are easily distinguishable
- **Clear visual differentiation** - Delta E > 20 between all base colors
- **Pleasant viewing experience** - Optimized for extended analysis sessions
- **Distinct identity** - Original colors that represent FollowWeb

## Base Color Palette

### Node Group Colors

These 6 colors are used for community detection and node grouping:

| Color Name | Hex Code | RGB | Usage |
|------------|----------|-----|-------|
| **Teal** | `#4ECDC4` | (78, 205, 196) | Primary community color |
| **Coral** | `#FF6B6B` | (255, 107, 107) | Secondary community color |
| **Amber** | `#FFD93D` | (255, 217, 61) | Tertiary community color |
| **Violet** | `#A78BFA` | (167, 139, 250) | Quaternary community color |
| **Sage** | `#6BCF7F` | (107, 207, 127) | Quinary community color |
| **Turquoise** | `#00B4D8` | (0, 180, 216) | Senary community color |

**Base Palette Order**: Teal → Coral → Amber → Violet → Sage → Turquoise

### Extended Palette (18 Additional Muted Colors)

For networks with more than 6 communities, an extended palette of 18 additional muted colors is available. These softer tones provide a more professional aesthetic while maintaining Delta E > 15 from the base palette and each other:

`#87BDFF` `#FFBC7B` `#FC9CB7` `#F06292` `#FFA07B` `#FEB959` `#79D5FF` `#C47ED0` `#A489D4` `#B9DB93` `#C6F04D` `#9FFF4F` `#F48684` `#60EFCA` `#8C97D2` `#A6DADC` `#C55A89` `#DCE674`

These colors are automatically used by `generate_extended_palette()` when more than 6 colors are needed, providing excellent visual distinction for networks with up to 24 communities before variations are generated.

### UI Colors

These colors are used for interface elements:

| Color Name | Hex Code | RGB | Usage |
|------------|----------|-----|-------|
| **Background Grey** | `#2d333c` | (45, 51, 60) | Panel backgrounds, control backgrounds |
| **Highlight Blue** | `#415a76` | (65, 90, 118) | Button backgrounds, active states |
| **Text Light Blue** | `#b6e0fe` | (182, 224, 254) | Text, labels, icons |

### Edge Colors

| Color Name | Hex Code | RGB | Usage |
|------------|----------|-----|-------|
| **Bridge Color** | `#6e6e6e` | (110, 110, 110) | Edges between different communities |
| **Intra Community Color** | `#c0c0c0` | (192, 192, 192) | Edges within the same community |

## Color Manipulation Functions

### darken_color(hex_color, factor=0.7)

Darkens a hex color by multiplying RGB values by the factor.

```python
from FollowWeb_Visualizor.visualization.color_palette import darken_color

# Darken teal by 30%
dark_teal = darken_color("#4ECDC4", 0.7)  # Returns: #368f89
```

**Parameters:**
- `hex_color` (str): Hex color string (e.g., "#4ECDC4")
- `factor` (float): Darkening factor (0.0 = black, 1.0 = original color)

### lighten_color(hex_color, factor=1.3)

Lightens a hex color by interpolating towards white.

```python
from FollowWeb_Visualizor.visualization.color_palette import lighten_color

# Lighten teal by 30%
light_teal = lighten_color("#4ECDC4", 1.3)  # Returns: #8eddd8
```

**Parameters:**
- `hex_color` (str): Hex color string (e.g., "#4ECDC4")
- `factor` (float): Lightening factor (1.0 = original color, >1.0 = lighter)

### hex_to_rgba(hex_color, alpha=1.0)

Converts hex color to RGBA tuple for matplotlib and other libraries.

```python
from FollowWeb_Visualizor.visualization.color_palette import hex_to_rgba

# Convert to RGBA
rgba = hex_to_rgba("#4ECDC4")  # Returns: (0.306, 0.804, 0.769, 1.0)
rgba_transparent = hex_to_rgba("#4ECDC4", 0.5)  # 50% opacity
```

**Parameters:**
- `hex_color` (str): Hex color string (e.g., "#4ECDC4")
- `alpha` (float): Alpha channel value (0.0 = transparent, 1.0 = opaque)

**Returns:** Tuple of (r, g, b, a) with values in range [0.0, 1.0]

### generate_extended_palette(num_colors)

Generates an extended color palette for large numbers of communities.

```python
from FollowWeb_Visualizor.visualization.color_palette import generate_extended_palette

# Generate palette for 10 communities
palette = generate_extended_palette(10)
# Returns: ['#4ECDC4', '#FF6B6B', '#FFD93D', '#A78BFA', '#6BCF7F', '#00B4D8',
#           '#54A0FF', '#FF9F43', '#FA7298', '#E91E63']

# Generate palette for 30 communities
palette = generate_extended_palette(30)
# Returns: 6 base colors + 18 extended colors + 6 generated variations
```

**Behavior:**
- Uses base palette colors first (6 colors)
- Uses extended palette colors next (18 additional muted colors)
- Generates darkened and lightened variations when more than 24 colors are needed
- Ensures no duplicate colors
- Maintains minimum Delta E > 15 between all colors

**Parameters:**
- `num_colors` (int): Number of colors needed (0-1000)

**Returns:** List of hex color strings

## Usage Examples

### In Python Code

```python
from FollowWeb_Visualizor.visualization.color_palette import (
    NodeGroupColors,
    UIColors,
    generate_extended_palette
)

# Access base colors
primary_color = NodeGroupColors.TEAL
background = UIColors.BACKGROUND_GREY

# Generate palette for communities
num_communities = 8
palette = generate_extended_palette(num_communities)
```

### In Configuration Files

```json
{
  "ui_background_color": "#2d333c",
  "ui_highlight_color": "#415a76",
  "ui_text_color": "#b6e0fe",
  "bridge_color": "#6e6e6e",
  "intra_community_color": "#c0c0c0"
}
```

### In HTML Templates

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
    
    #controls button.active {
        background: #FFD93D;  /* Amber for active state */
    }
</style>
```

## Color Accessibility

All colors are chosen for optimal visibility and differentiation:

- **Teal (#4ECDC4)**: Vibrant, modern, high visibility
- **Coral (#FF6B6B)**: Warm, attention-grabbing, distinct
- **Amber (#FFD93D)**: Bright, energetic, clear
- **Violet (#A78BFA)**: Soft, distinctive, pleasant
- **Sage (#6BCF7F)**: Fresh, natural, balanced
- **Turquoise (#00B4D8)**: Deep, professional, clear

**Perceptual Differentiation**: All base colors maintain Delta E > 20, ensuring excellent visual distinction even for users with color vision deficiencies.

## Integration with Existing Systems

The color palette integrates seamlessly with the `get_community_colors()` function:

```python
from FollowWeb_Visualizor.visualization.colors import get_community_colors

# Get colors for 6 communities
colors = get_community_colors(6)
# Returns: {
#   'hex': {0: '#4ECDC4', 1: '#FF6B6B', 2: '#FFD93D', 3: '#A78BFA', 4: '#6BCF7F', 5: '#00B4D8'},
#   'rgba': {0: (0.306, 0.804, 0.769, 1.0), ...}
# }
```

## Extending the Palette

To add new base colors, edit `color_palette.py`:

```python
class NodeGroupColors:
    TEAL = "#4ECDC4"
    CORAL = "#FF6B6B"
    AMBER = "#FFD93D"
    VIOLET = "#A78BFA"
    SAGE = "#6BCF7F"
    TURQUOISE = "#00B4D8"
    # Add new colors here
    NEW_COLOR = "#XXXXXX"
    
    BASE_PALETTE = [TEAL, CORAL, AMBER, VIOLET, SAGE, TURQUOISE, NEW_COLOR]
```

**Important**: Ensure new colors maintain Delta E > 20 from existing colors for optimal differentiation.

## Testing

Run the color palette test suite:

```bash
cd FollowWeb
python -m pytest tests/unit/visualization/test_color_palette.py -v
```

This validates:
- Base color definitions
- UI color definitions
- Color manipulation functions (darken, lighten, hex_to_rgba)
- Extended palette generation
- No duplicate colors
- Minimum Delta E requirements

## Attribution

This color palette was designed specifically for FollowWeb, inspired by the minimalist aesthetic of games like Mini Motorways. The colors are our own original selections and do not replicate any specific commercial color scheme.

## API Reference

### Classes

#### NodeGroupColors
Static class containing base node group color definitions.

**Attributes:**
- `TEAL`: Primary community color (#4ECDC4)
- `CORAL`: Secondary community color (#FF6B6B)
- `AMBER`: Tertiary community color (#FFD93D)
- `VIOLET`: Quaternary community color (#A78BFA)
- `SAGE`: Quinary community color (#6BCF7F)
- `TURQUOISE`: Senary community color (#00B4D8)
- `BASE_PALETTE`: List of all base colors in order

#### UIColors
Static class containing UI color definitions.

**Attributes:**
- `BACKGROUND_GREY`: Panel backgrounds (#2d333c)
- `HIGHLIGHT_BLUE`: Button backgrounds (#415a76)
- `TEXT_LIGHT_BLUE`: Text and labels (#b6e0fe)
- `BRIDGE_COLOR`: Inter-community edges (#6e6e6e)
- `INTRA_COMMUNITY_COLOR`: Intra-community edges (#c0c0c0)

### Functions

All functions are available from the visualization module:

```python
from FollowWeb_Visualizor.visualization.color_palette import (
    darken_color,
    lighten_color,
    hex_to_rgba,
    generate_extended_palette,
)
```

See function descriptions above for detailed usage.
