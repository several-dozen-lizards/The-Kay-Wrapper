"""Generate placeholder 9-patch border textures for Nexus UI panels."""
from PIL import Image, ImageDraw, ImageFilter

SIZE = 96
MARGIN = 24  # Corner region size
BORDER_W = 3  # Main border thickness
GLOW_PASSES = 3

# Entity colors: (r, g, b)
PANELS = {
    "nexus": (100, 100, 160),   # Muted purple-blue
    "kay":   (160, 50, 170),    # Purple-magenta
    "reed":  (40, 180, 190),    # Teal
}

def make_border(name, color):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    r, g, b = color
    
    # Outer glow layer (drawn first, blurred)
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.rectangle(
        [BORDER_W, BORDER_W, SIZE - BORDER_W - 1, SIZE - BORDER_W - 1],
        outline=(r, g, b, 120), width=BORDER_W + 2
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=4))
    img = Image.alpha_composite(img, glow)
    
    # Main border line
    draw = ImageDraw.Draw(img)
    draw.rectangle(
        [BORDER_W, BORDER_W, SIZE - BORDER_W - 1, SIZE - BORDER_W - 1],
        outline=(r, g, b, 220), width=BORDER_W
    )
    
    # Brighter corners - small accent dots
    corner_color = (min(r + 80, 255), min(g + 80, 255), min(b + 80, 255), 255)
    cs = 6  # corner spot size
    for cx, cy in [(BORDER_W+2, BORDER_W+2), 
                   (SIZE-BORDER_W-cs, BORDER_W+2),
                   (BORDER_W+2, SIZE-BORDER_W-cs), 
                   (SIZE-BORDER_W-cs, SIZE-BORDER_W-cs)]:
        draw.rectangle([cx, cy, cx+cs, cy+cs], fill=corner_color)
    
    # Inner subtle line
    inner_color = (r, g, b, 60)
    draw.rectangle(
        [BORDER_W + 4, BORDER_W + 4, SIZE - BORDER_W - 5, SIZE - BORDER_W - 5],
        outline=inner_color, width=1
    )
    
    # Save
    out_path = f"border_{name}.png"
    img.save(out_path)
    print(f"Saved {out_path} ({SIZE}x{SIZE}, margin={MARGIN})")

for name, color in PANELS.items():
    make_border(name, color)

print("Done! All borders generated.")
