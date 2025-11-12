# FollowWeb Color Reference

Visual reference for all colors used in FollowWeb visualizations.

## Node Group Colors (Community Detection)

### Base Palette

```
┌─────────────────────────────────────────────────────────────┐
│ #62CB89 - Green                                             │
│ ███████████████████████████████████████████████████████████ │
│ Primary community color - Fresh, natural                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ #47BEE1 - Blue                                              │
│ ███████████████████████████████████████████████████████████ │
│ Secondary community color - Bright, trustworthy             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ #FFB242 - Orange                                            │
│ ███████████████████████████████████████████████████████████ │
│ Accent community color - Warm, energetic                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ #F15668 - Purple/Pink                                       │
│ ███████████████████████████████████████████████████████████ │
│ Highlight community color - Vibrant, distinctive            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ #6C95C1 - Blue Alt                                          │
│ ███████████████████████████████████████████████████████████ │
│ Alternative blue - Muted, professional                      │
└─────────────────────────────────────────────────────────────┘
```

### Extended Palette (Darkened Variations)

When more than 5 communities are detected, the system automatically generates darkened variations:

```
First Variation (70% brightness):
#4ea26d (Green 70%)    #3898b4 (Blue 70%)    #cc8e34 (Orange 70%)
#c04453 (Purple 70%)   #56779a (Blue Alt 70%)

Second Variation (50% brightness):
#316544 (Green 50%)    #2a7287 (Blue 50%)    #997125 (Orange 50%)
#963340 (Purple 50%)   #425c75 (Blue Alt 50%)

Third Variation (30% brightness):
#1d3e29 (Green 30%)    #194351 (Orange 30%)  #5c4316 (Orange 30%)
#5b1f26 (Purple 30%)   #283746 (Blue Alt 30%)
```

## UI Colors (Interface Elements)

### Background

```
┌─────────────────────────────────────────────────────────────┐
│ #2d333c - Background Grey                                   │
│ ███████████████████████████████████████████████████████████ │
│ Used for: Control panels, audio player, search box         │
│ Dark, neutral background for UI elements                    │
└─────────────────────────────────────────────────────────────┘
```

### Highlight/Interactive

```
┌─────────────────────────────────────────────────────────────┐
│ #415a76 - Highlight Blue                                    │
│ ███████████████████████████████████████████████████████████ │
│ Used for: Buttons, borders, active states                   │
│ Medium blue-grey for interactive elements                   │
└─────────────────────────────────────────────────────────────┘
```

### Text

```
┌─────────────────────────────────────────────────────────────┐
│ #b6e0fe - Text Light Blue                                   │
│ ███████████████████████████████████████████████████████████ │
│ Used for: Text, labels, icons                               │
│ Light blue for high contrast on dark backgrounds            │
└─────────────────────────────────────────────────────────────┘
```

## Edge Colors

### Bridge Edges (Between Communities)

```
┌─────────────────────────────────────────────────────────────┐
│ #6e6e6e - Bridge Grey                                       │
│ ███████████████████████████████████████████████████████████ │
│ Used for: Edges connecting different communities            │
│ Neutral grey to distinguish from community colors           │
└─────────────────────────────────────────────────────────────┘
```

### Intra-Community Edges

```
┌─────────────────────────────────────────────────────────────┐
│ #c0c0c0 - Intra-Community Grey                              │
│ ███████████████████████████████████████████████████████████ │
│ Used for: Edges within the same community                   │
│ Light grey for subtle connections                           │
└─────────────────────────────────────────────────────────────┘
```

## Special Purpose Colors

### Search Highlight

```
┌─────────────────────────────────────────────────────────────┐
│ #47BEE1 - Search Highlight (Blue)                           │
│ ███████████████████████████████████████████████████████████ │
│ Used for: Highlighting nodes matching search query          │
│ Same as base Blue for consistency                           │
└─────────────────────────────────────────────────────────────┘
```

### Audio Playing

```
┌─────────────────────────────────────────────────────────────┐
│ #FFB242 - Playing Node (Orange)                             │
│ ███████████████████████████████████████████████████████████ │
│ Used for: Highlighting currently playing audio node         │
│ Same as base Orange for consistency                         │
└─────────────────────────────────────────────────────────────┘
```

### Error Messages

```
┌─────────────────────────────────────────────────────────────┐
│ #F15668 - Error (Purple/Pink)                               │
│ ███████████████████████████████████████████████████████████ │
│ Used for: Error messages and warnings                       │
│ Same as base Purple for consistency                         │
└─────────────────────────────────────────────────────────────┘
```

## Color Combinations

### UI Panel Example

```
┌─────────────────────────────────────────────────────────────┐
│ Background: #2d333c                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Border: #415a76                                         │ │
│ │                                                         │ │
│ │ Text: #b6e0fe                                           │ │
│ │                                                         │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Button: #415a76 with Text: #b6e0fe                 │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Community Visualization Example

```
Network with 3 Communities:

Community 0: #62CB89 (Green)
  ● ─── ● ─── ●
  │           │
  ●           ●

Community 1: #47BEE1 (Blue)
  ● ─── ● ─── ●
  │           │
  ●           ●

Community 2: #FFB242 (Orange)
  ● ─── ● ─── ●
  │           │
  ●           ●

Bridge edges: #6e6e6e (Grey)
  Community 0 ═══ Community 1
  Community 1 ═══ Community 2
```

## Contrast Ratios (WCAG Accessibility)

### UI Colors

| Foreground | Background | Ratio | WCAG Level |
|------------|------------|-------|------------|
| #b6e0fe (Text) | #2d333c (BG) | 10.2:1 | AAA |
| #b6e0fe (Text) | #415a76 (Highlight) | 5.8:1 | AA |
| #415a76 (Highlight) | #2d333c (BG) | 1.8:1 | - |

### Node Colors on White Background

| Color | Hex | Contrast | WCAG Level |
|-------|-----|----------|------------|
| Green | #62CB89 | 2.8:1 | - |
| Blue | #47BEE1 | 2.4:1 | - |
| Orange | #FFB242 | 2.1:1 | - |
| Purple | #F15668 | 4.2:1 | AA (Large) |
| Blue Alt | #6C95C1 | 3.1:1 | - |

Note: Node colors are optimized for visibility on graph backgrounds, not for text contrast.

## RGB Values

For reference, here are the RGB values:

| Color Name | Hex | RGB |
|------------|-----|-----|
| Green | #62CB89 | rgb(98, 203, 137) |
| Blue | #47BEE1 | rgb(71, 190, 225) |
| Blue Alt | #6C95C1 | rgb(108, 149, 193) |
| Orange | #FFB242 | rgb(255, 178, 66) |
| Purple | #F15668 | rgb(241, 86, 104) |
| Background Grey | #2d333c | rgb(45, 51, 60) |
| Highlight Blue | #415a76 | rgb(65, 90, 118) |
| Text Light Blue | #b6e0fe | rgb(182, 224, 254) |
| Bridge Grey | #6e6e6e | rgb(110, 110, 110) |
| Intra-Community Grey | #c0c0c0 | rgb(192, 192, 192) |

## HSL Values

For designers working in HSL:

| Color Name | Hex | HSL |
|------------|-----|-----|
| Green | #62CB89 | hsl(142, 51%, 59%) |
| Blue | #47BEE1 | hsl(194, 72%, 58%) |
| Blue Alt | #6C95C1 | hsl(211, 39%, 59%) |
| Orange | #FFB242 | hsl(36, 100%, 63%) |
| Purple | #F15668 | hsl(353, 85%, 64%) |
| Background Grey | #2d333c | hsl(220, 14%, 21%) |
| Highlight Blue | #415a76 | hsl(212, 29%, 36%) |
| Text Light Blue | #b6e0fe | hsl(204, 97%, 85%) |

## Usage Guidelines

### Do's ✓

- Use base palette colors for the first 5 communities
- Use darkened variations for additional communities
- Use UI colors consistently across all interface elements
- Maintain high contrast between text and backgrounds
- Use Orange (#FFB242) for active/playing states
- Use Purple (#F15668) for errors and warnings

### Don'ts ✗

- Don't mix custom colors with the base palette
- Don't use node colors for UI elements
- Don't use UI colors for nodes
- Don't reduce opacity below 70% for text
- Don't use more than 3 variations of the same base color
- Don't override colors without updating the palette

## Color Psychology

| Color | Emotion/Association |
|-------|---------------------|
| Green (#62CB89) | Growth, harmony, freshness |
| Blue (#47BEE1) | Trust, stability, calm |
| Orange (#FFB242) | Energy, enthusiasm, warmth |
| Purple (#F15668) | Creativity, passion, attention |
| Grey (#2d333c) | Neutral, professional, modern |

## Implementation Notes

- All colors are defined in `color_palette.py`
- Colors are automatically applied via `get_community_colors()`
- UI colors are passed to templates via config
- Darkening uses multiplicative RGB adjustment
- Lightening uses additive interpolation to white
- RGBA conversion normalizes to 0.0-1.0 range
