"""Check color similarity for new palette additions."""


def rgb_to_lab(r, g, b):
    """Convert RGB to LAB color space."""
    r = r / 255.0
    g = g / 255.0
    b = b / 255.0

    r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
    g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
    b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92

    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

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


def delta_e(color1, color2):
    """Calculate Delta E between two hex colors."""
    r1 = int(color1[1:3], 16)
    g1 = int(color1[3:5], 16)
    b1 = int(color1[5:7], 16)

    r2 = int(color2[1:3], 16)
    g2 = int(color2[3:5], 16)
    b2 = int(color2[5:7], 16)

    L1, a1, b1_val = rgb_to_lab(r1, g1, b1)
    L2, a2, b2_val = rgb_to_lab(r2, g2, b2)

    return ((L2 - L1) ** 2 + (a2 - a1) ** 2 + (b2_val - b1_val) ** 2) ** 0.5


# Base palette
base_colors = {
    "TEAL": "#4ECDC4",
    "CORAL": "#FF6B6B",
    "AMBER": "#FFD93D",
    "VIOLET": "#A78BFA",
    "SAGE": "#6BCF7F",
    "TURQUOISE": "#00B4D8",
}

# Muted colors - new proposed set
proposed = [
    "#87BDFF",
    "#FFBC7B",
    "#FC9CB7",
    "#F591B3",
    "#F06292",
    "#FF79A7",
    "#FFC97F",
    "#FFA07B",
    "#FD9C5B",
    "#FEB959",
    "#7AC0F8",
    "#69CBF9",
    "#4EC3F7",
    "#4CD0FF",
    "#4CC0DE",
    "#79D5FF",
    "#C47ED0",
    "#B968C8",
    "#CE95D8",
    "#A489D4",
    "#B49EEB",
    "#B9DB93",
    "#ADD580",
    "#C6F04D",
    "#D7FF4D",
    "#9FFF4F",
    "#F48684",
    "#EC7471",
    "#F77B72",
    "#67C0B8",
    "#4CC4D3",
    "#4CD2C0",
    "#60EFCA",
    "#92FFE5",
    "#7885CB",
    "#8C97D2",
    "#A1AACF",
    "#4CB5AB",
    "#82CBCA",
    "#A6DADC",
    "#E06D6D",
    "#D76868",
    "#C55A89",
    "#AF65C3",
    "#9475CC",
    "#7885CB",
    "#63B5F6",
    "#4EC3F7",
    "#4CD0E0",
    "#4CB5AB",
    "#81C784",
    "#ADD580",
    "#DCE674",
    "#FFF175",
    "#FFD351",
    "#FFB64D",
    "#FF8964",
    "#F77B72",
    "#F06292",
    "#B968C8",
]

# Remove duplicates
proposed = list(dict.fromkeys(proposed))

print(f"Total proposed colors (after removing duplicates): {len(proposed)}")
print()

# Check against base palette
MIN_DELTA_E = 15
approved = []
rejected = []

for color in proposed:
    min_delta = float("inf")
    closest_base = None

    # Check against base colors
    for name, base_color in base_colors.items():
        de = delta_e(color, base_color)
        if de < min_delta:
            min_delta = de
            closest_base = name

    # Check against already approved colors
    for approved_color in approved:
        de = delta_e(color, approved_color)
        if de < min_delta:
            min_delta = de
            closest_base = f"approved {approved_color}"

    if min_delta >= MIN_DELTA_E:
        approved.append(color)
        print(f"✓ {color} - Delta E: {min_delta:.1f} (closest: {closest_base})")
    else:
        rejected.append((color, min_delta, closest_base))

print()
print(f"\nAPPROVED: {len(approved)} colors")
print(f"REJECTED: {len(rejected)} colors (too similar)")
print()

print("\nREJECTED COLORS:")
for color, de, closest in rejected:
    print(f"✗ {color} - Delta E: {de:.1f} (too close to {closest})")

print()
print("\nFINAL APPROVED LIST:")
print(approved)
