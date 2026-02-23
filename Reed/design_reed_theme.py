#!/usr/bin/env python3
"""
Create Reed's visual theme - Serpent palette
"""

REED_SERPENT_PALETTE = """
# Reed's Serpent Palette
# Replace the "Ornate" palette in reed_ui.py (around line 277)

PALETTES = {
    "Serpent": {
        # Deep ocean teal background - darker than scales but still aquatic
        "bg": "#0A1F1F",
        
        # Panel color - deep teal with slight green
        "panel": "#143838",
        
        # Input fields - lighter teal
        "input": "#1F4D4D",
        
        # Text - warm cream/gold for readability
        "text": "#F0E6D2",
        
        # Muted text - softer gold
        "muted": "#B8A882",
        
        # Accent - PRIMARY TEAL (Reed's main scale color)
        "accent": "#4DB8A8",
        
        # Accent highlight - BRIGHT TEAL (iridescent flash)
        "accent_hi": "#6EDCC4",
        
        # User messages - soft pink-gold (warm, human)
        "user": "#E8C4A8",
        
        # Reed's messages - ELECTRIC TEAL
        "reed": "#5EC9B8",
        
        # System messages - GOLD (like scale shimmer)
        "system": "#D4AF37",
        
        # Buttons - mid-teal
        "button": "#2A5F5F",
        
        # Button text - cream
        "button_tx": "#F0E6D2",
        
        # Border - gold accent
        "border": "#B8943C",
        
        # Border accent - darker gold
        "border_accent": "#8B7028",
        
        # Visual style flag
        "ornate": True,
        
        # WARNING/ERROR colors
        "warning": "#E8A84C",  # Warm gold warning
        "error": "#E86C5C",    # Coral error (not harsh red)
    }
}
"""

def create_reed_theme():
    print("=" * 60)
    print("REED'S SERPENT PALETTE")
    print("=" * 60)
    print()
    print("Color scheme:")
    print("  🌊 Deep ocean teal backgrounds")
    print("  ✨ Iridescent teal-gold accents")
    print("  💎 Electric teal for Reed's voice")
    print("  🌅 Warm gold for borders and system")
    print("  🐚 Soft cream text for readability")
    print()
    print("Visual language:")
    print("  • Aquatic depth (not gothic darkness)")
    print("  • Shimmer and flow (not rigid structure)")
    print("  • Warm golds (not bronze/brown)")
    print("  • Living water (not dead stone)")
    print()
    print("-" * 60)
    print("Palette definition to insert into reed_ui.py:")
    print("-" * 60)
    print()
    print(REED_SERPENT_PALETTE)
    print()
    print("=" * 60)
    print("Next step: Apply this palette to reed_ui.py")
    print("=" * 60)

if __name__ == "__main__":
    create_reed_theme()
