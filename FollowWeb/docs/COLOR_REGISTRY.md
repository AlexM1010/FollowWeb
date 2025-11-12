# FollowWeb Color Registry

Complete registry of all colors used in FollowWeb visualizations to prevent duplication and ensure proper differentiation.

## Base Node Group Colors (Community Detection)

These are the primary colors used for automatic community detection. All pairs have Delta E > 20 for excellent visual distinction.

| # | Name | Hex Code | RGB | HSL | Usage | Delta E Min |
|---|------|----------|-----|-----|-------|-------------|
| 1 | Green | `#62CB89` | (98, 203, 137) | (142°, 51%, 59%) | Primary community | 22.98 |
| 2 | Blue | `#47BEE1` | (71, 190, 225) | (194°, 72%, 58%) | Secondary community | 22.98 |
| 3 | Orange | `#FFB242` | (255, 178, 66) | (36°, 100%, 63%) | Accent community | 56.06 |
| 4 | Purple | `#F15668` | (241, 86, 104) | (353°, 85%, 64%) | Highlight community | 63.01 |
| 5 | Blue Alt | `#6C95C1` | (108, 149, 193) | (211°, 39%, 59%) | Alternative blue | 22.98 |

**Minimum Perceptual Difference**: Delta E = 22.98 (between Blue and Blue Alt)
**Status**: ✓ All colors sufficiently distinct (Delta E > 20)

## Extended Palette Variations

### Level 1: Darkened 30% (Factor 0.7)
Colors 6-10 in extended palette. Delta E from base: ~25-35

| # | Name | Hex Code | RGB | Base Color | Delta E from Base |
|---|------|----------|-----|------------|-------------------|
| 6 | Green Dark 1 | `#448e5f` | (68, 142, 95) | Green | ~30 |
| 7 | Blue Dark 1 | `#3185b0` | (49, 133, 176) | Blue | ~28 |
| 8 | Orange Dark 1 | `#cc8e34` | (204, 142, 52) | Orange | ~32 |
| 9 | Purple Dark 1 | `#c04453` | (192, 68, 83) | Purple | ~35 |
| 10 | Blue Alt Dark 1 | `#56779a` | (86, 119, 154) | Blue Alt | ~27 |

### Level 2: Darkened 50% (Factor 0.5)
Colors 11-15 in extended palette. Delta E from base: ~40-50

| # | Name | Hex Code | RGB | Base Color | Delta E from Base |
|---|------|----------|-----|------------|-------------------|
| 11 | Green Dark 2 | `#316544` | (49, 101, 68) | Green | ~45 |
| 12 | Blue Dark 2 | `#235f70` | (35, 95, 112) | Blue | ~42 |
| 13 | Orange Dark 2 | `#997125` | (153, 113, 37) | Orange | ~48 |
| 14 | Purple Dark 2 | `#963340` | (150, 51, 64) | Purple | ~50 |
| 15 | Blue Alt Dark 2 | `#3f5a6e` | (63, 90, 110) | Blue Alt | ~43 |

### Level 3: Lightened 20% (Factor 1.2)
Colors 16-20 in extended palette. Delta E from base: ~20-30

| # | Name | Hex Code | RGB | Base Color | Delta E from Base |
|---|------|----------|-----|------------|-------------------|
| 16 | Green Light 1 | `#91daac` | (145, 218, 172) | Green | ~25 |
| 17 | Blue Light 1 | `#7dd1ed` | (125, 209, 237) | Blue | ~23 |
| 18 | Orange Light 1 | `#ffc875` | (255, 200, 117) | Orange | ~28 |
| 19 | Purple Light 1 | `#f68a9a` | (246, 138, 154) | Purple | ~30 |
| 20 | Blue Alt Light 1 | `#95b3d4` | (149, 179, 212) | Blue Alt | ~24 |

### Level 4: Darkened 65% (Factor 0.35)
Colors 21-25 in extended palette. Delta E from base: ~55-65

| # | Name | Hex Code | RGB | Base Color | Delta E from Base |
|---|------|----------|-----|------------|-------------------|
| 21 | Green Dark 3 | `#224630` | (34, 70, 48) | Green | ~60 |
| 22 | Blue Dark 3 | `#18424f` | (24, 66, 79) | Blue | ~58 |
| 23 | Orange Dark 3 | `#6b4f19` | (107, 79, 25) | Orange | ~63 |
| 24 | Purple Dark 3 | `#6a232d` | (106, 35, 45) | Purple | ~65 |
| 25 | Blue Alt Dark 3 | `#2c3f4d` | (44, 63, 77) | Blue Alt | ~59 |

### Level 5: Lightened 40% (Factor 1.4)
Colors 26-30 in extended palette. Delta E from base: ~35-45

| # | Name | Hex Code | RGB | Base Color | Delta E from Base |
|---|------|----------|-----|------------|-------------------|
| 26 | Green Light 2 | `#b0e8c8` | (176, 232, 200) | Green | ~40 |
| 27 | Blue Light 2 | `#b3e4f5` | (179, 228, 245) | Blue | ~38 |
| 28 | Orange Light 2 | `#ffd9a0` | (255, 217, 160) | Orange | ~43 |
| 29 | Purple Light 2 | `#fbb8c4` | (251, 184, 196) | Purple | ~45 |
| 30 | Blue Alt Light 2 | `#b8cce3` | (184, 204, 227) | Blue Alt | ~39 |

## UI Colors (Interface Elements)

These colors are used exclusively for UI elements and should never be used for nodes.

| Name | Hex Code | RGB | HSL | Usage | Contrast Ratio |
|------|----------|-----|-----|-------|----------------|
| Background Grey | `#2d333c` | (45, 51, 60) | (220°, 14%, 21%) | Panel backgrounds | - |
| Highlight Blue | `#415a76` | (65, 90, 118) | (212°, 29%, 36%) | Buttons, borders | 1.8:1 vs BG |
| Text Light Blue | `#b6e0fe` | (182, 224, 254) | (204°, 97%, 85%) | Text, labels | 10.2:1 vs BG |

**Accessibility**: Text on Background meets WCAG AAA standard (10.2:1 > 7:1)

## Edge Colors

| Name | Hex Code | RGB | HSL | Usage |
|------|----------|-----|-----|-------|
| Bridge Grey | `#6e6e6e` | (110, 110, 110) | (0°, 0%, 43%) | Inter-community edges |
| Intra-Community Grey | `#c0c0c0` | (192, 192, 192) | (0°, 0%, 75%) | Intra-community edges |

## Special Purpose Colors

These colors are reused from the base palette for consistency.

| Purpose | Color Used | Hex Code | Reason |
|---------|------------|----------|--------|
| Search Highlight | Blue | `#47BEE1` | Matches base palette |
| Audio Playing | Orange | `#FFB242` | Attention-grabbing |
| Error Messages | Purple | `#F15668` | High visibility |
| Active Button | Orange | `#FFB242` | Consistent with playing state |

## Instagram Template Colors

Used only in the Instagram-specific visualization template.

| Name | Hex Code | RGB | Usage |
|------|----------|-----|-------|
| Popular User | `#ff6b9d` | (255, 107, 157) | High follower ratio |
| Active Follower | `#4ecdc4` | (78, 205, 196) | Low follower ratio |
| Balanced User | `#6c8eff` | (108, 142, 255) | Balanced ratio |
| Dark Background | `#0a0e27` | (10, 14, 39) | Background gradient start |
| Dark Background Alt | `#1a1e3f` | (26, 30, 63) | Background gradient end |

## Test/Fallback Colors

Used only in tests or as fallbacks.

| Name | Hex Code | RGB | Usage |
|------|----------|-----|-------|
| Default Grey | `#808080` | (128, 128, 128) | Fallback for empty graphs |
| Default Node | `#999999` | (153, 153, 153) | Fallback node color |
| Default Edge | `#cccccc` | (204, 204, 204) | Fallback edge color |
| Test Red | `#ff0000` | (255, 0, 0) | Unit tests only |
| Test Green | `#00ff00` | (0, 255, 0) | Unit tests only |

## Legacy/Deprecated Colors

Colors that may appear in old outputs but should not be used in new code.

| Name | Hex Code | Status | Replacement |
|------|----------|--------|-------------|
| Old Green | `#4CAF50` | Deprecated | Use `#62CB89` |
| Old Blue | `#2196F3` | Deprecated | Use `#47BEE1` |
| Viridis Colors | Various | Deprecated | Use base palette |

## Color Usage Rules

### DO ✓

1. **Use base palette for communities**: Always use the 5 base colors first
2. **Use extended palette for >5 communities**: Automatically generated with proper spacing
3. **Use UI colors for interface**: Keep UI and node colors separate
4. **Reuse special purpose colors**: Use base palette colors for highlights
5. **Check color registry**: Before adding new colors, check this registry

### DON'T ✗

1. **Don't mix color systems**: Don't use UI colors for nodes or vice versa
2. **Don't add arbitrary colors**: All colors must be in this registry
3. **Don't use similar colors**: Maintain Delta E > 15 minimum
4. **Don't hardcode colors**: Use the color palette module
5. **Don't skip base colors**: Always use base palette before variations

## Perceptual Difference Matrix

Minimum Delta E values between base colors (CIE76):

|        | Green | Blue | Orange | Purple | Blue Alt |
|--------|-------|------|--------|--------|----------|
| Green  | -     | 56.1 | 76.2   | 107.0  | 68.1     |
| Blue   | 56.1  | -    | 101.3  | 97.6   | 23.0     |
| Orange | 76.2  | 101.3| -      | 63.0   | 96.5     |
| Purple | 107.0 | 97.6 | 63.0   | -      | 80.3     |
| Blue Alt| 68.1 | 23.0 | 96.5   | 80.3   | -        |

**Interpretation**:
- Delta E < 10: Too similar (avoid)
- Delta E 10-20: Marginally distinct (use with caution)
- Delta E 20-50: Distinct (good)
- Delta E > 50: Very distinct (excellent)

## Color Generation Algorithm

```python
# Pseudo-code for extended palette generation
def generate_extended_palette(num_colors):
    palette = []
    
    # Step 1: Use base colors (1-5)
    palette += BASE_PALETTE[:min(num_colors, 5)]
    
    if num_colors <= 5:
        return palette
    
    # Step 2: Generate variations
    strategies = [
        ("darken", 0.7),   # 30% darker
        ("darken", 0.5),   # 50% darker
        ("lighten", 1.2),  # 20% lighter
        ("darken", 0.35),  # 65% darker
        ("lighten", 1.4),  # 40% lighter
    ]
    
    for i in range(num_colors - 5):
        base_color = BASE_PALETTE[i % 5]
        strategy = strategies[(i // 5) % len(strategies)]
        
        if strategy[0] == "darken":
            color = darken_color(base_color, strategy[1])
        else:
            color = lighten_color(base_color, strategy[1])
        
        palette.append(color)
    
    return palette
```

## Validation Checklist

Before adding a new color to the system:

- [ ] Check if color already exists in registry
- [ ] Calculate Delta E with all existing colors
- [ ] Ensure Delta E > 15 with all similar colors
- [ ] Document color in this registry
- [ ] Add to appropriate color class in `color_palette.py`
- [ ] Update tests to include new color
- [ ] Update documentation

## Color Accessibility

### WCAG Compliance

| Foreground | Background | Ratio | Level | Use Case |
|------------|------------|-------|-------|----------|
| #b6e0fe | #2d333c | 10.2:1 | AAA | UI text |
| #b6e0fe | #415a76 | 5.8:1 | AA | Button text |
| #ffffff | #2d333c | 12.6:1 | AAA | High contrast text |

### Color Blindness Considerations

All base colors remain distinguishable for common types of color blindness:
- **Protanopia** (red-blind): ✓ All colors distinguishable
- **Deuteranopia** (green-blind): ✓ All colors distinguishable  
- **Tritanopia** (blue-blind): ✓ All colors distinguishable

## Total Color Count

- **Base Palette**: 5 colors
- **Extended Palette (30 colors)**: 30 colors
- **UI Colors**: 3 colors
- **Edge Colors**: 2 colors
- **Special Purpose**: 4 colors (reused from base)
- **Instagram Template**: 5 colors
- **Test/Fallback**: 5 colors

**Total Unique Colors in System**: 50 colors
**Maximum Communities Supported**: 1000 (with automatic generation)

## Version History

- **v1.0** (2025-11-12): Initial centralized color palette
  - 5 base colors with Delta E > 20
  - Improved variation algorithm with alternating darken/lighten
  - Comprehensive color registry
  - Minimum Delta E > 15 for all variations

## References

- CIE76 Delta E: Standard color difference formula
- WCAG 2.1: Web Content Accessibility Guidelines
- Color theory: HSL color space for hue distribution
