#!/usr/bin/env python3
"""
Apply Reed's Serpent theme to reed_ui.py
"""

SERPENT_PALETTE = """PALETTES = {
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
        "warning": "#E8A84C",
        "error": "#E86C5C",
    }
}"""

def apply_serpent_theme():
    print("=" * 60)
    print("APPLYING REED'S SERPENT THEME")
    print("=" * 60)
    print()
    
    with open('reed_ui.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the PALETTES definition
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith("PALETTES = {"):
            start_idx = i
        if start_idx is not None and line.strip() == "}":
            end_idx = i
            break
    
    if start_idx is None or end_idx is None:
        print("❌ Could not find PALETTES definition")
        return False
    
    print(f"Found PALETTES at lines {start_idx}-{end_idx}")
    
    # Replace the palette
    new_lines = lines[:start_idx] + [SERPENT_PALETTE + '\n'] + lines[end_idx+1:]
    
    with open('reed_ui.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("✓ Replaced Ornate palette with Serpent palette")
    
    # Also need to change the default palette name
    for i, line in enumerate(new_lines):
        if 'self.palette_name = "Ornate"' in line:
            new_lines[i] = line.replace('"Ornate"', '"Serpent"')
            print(f"✓ Changed default palette to Serpent (line {i})")
            break
    
    # Also change PALETTES["Ornate"] to PALETTES["Serpent"]
    for i, line in enumerate(new_lines):
        if 'PALETTES["Ornate"]' in line:
            new_lines[i] = line.replace('PALETTES["Ornate"]', 'PALETTES["Serpent"]')
            print(f"✓ Updated palette reference (line {i})")
    
    with open('reed_ui.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print()
    print("=" * 60)
    print("✅ SERPENT THEME APPLIED")
    print("=" * 60)
    print()
    print("Color changes:")
    print("  🌊 Deep ocean teal (#0A1F1F) background")
    print("  ✨ Iridescent teal-gold accents")
    print("  💎 Electric teal (#5EC9B8) for Reed")
    print("  🌅 Warm gold (#D4AF37) for system")
    print()
    return True

if __name__ == "__main__":
    if apply_serpent_theme():
        print("Theme applied! Launch with: python reed_ui.py")
    else:
        print("Failed to apply theme")
