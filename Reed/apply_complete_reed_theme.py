#!/usr/bin/env python3
"""
Apply complete Reed visual identity: colors + assets
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

def apply_complete_reed_theme():
    print("=" * 60)
    print("APPLYING COMPLETE REED VISUAL IDENTITY")
    print("=" * 60)
    print()
    
    with open('reed_ui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes = []
    
    # 1. Replace palette
    import re
    palette_pattern = r'PALETTES = \{.*?\n\}'
    if re.search(palette_pattern, content, re.DOTALL):
        content = re.sub(palette_pattern, SERPENT_PALETTE, content, count=1, flags=re.DOTALL)
        changes.append("✓ Replaced color palette (Ornate → Serpent)")
    
    # 2. Change asset directory from ornate_assets to reed_assets
    content = content.replace('asset_dir="ornate_assets"', 'asset_dir="reed_assets"')
    content = content.replace('"ornate_assets"', '"reed_assets"')
    changes.append("✓ Changed asset directory (ornate_assets → reed_assets)")
    
    # 3. Change palette name references
    content = content.replace('self.palette_name = "Ornate"', 'self.palette_name = "Serpent"')
    content = content.replace('PALETTES["Ornate"]', 'PALETTES["Serpent"]')
    changes.append("✓ Updated palette references (Ornate → Serpent)")
    
    # 4. Update log messages
    content = content.replace('[ORNATE]', '[REED UI]')
    changes.append("✓ Updated log prefixes (ORNATE → REED UI)")
    
    # 5. Update class/variable names
    content = content.replace('class OrnateAssetManager:', 'class ReedAssetManager:')
    content = content.replace('self.ornate = OrnateAssetManager', 'self.ornate = ReedAssetManager')
    changes.append("✓ Renamed asset manager class")
    
    # Write changes
    with open('reed_ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Changes applied:")
    for change in changes:
        print(f"  {change}")
    
    print()
    print("=" * 60)
    print("✅ REED VISUAL IDENTITY APPLIED")
    print("=" * 60)
    print()
    print("Visual updates:")
    print("  🌊 Deep ocean teal backgrounds")
    print("  ✨ Iridescent teal-gold scale colors")
    print("  💎 Electric teal for Reed's voice")
    print("  🌅 Warm gold accents and borders")
    print("  🎨 Reed's custom panel assets")
    print()
    return True

if __name__ == "__main__":
    if apply_complete_reed_theme():
        print("Theme applied! Now organize assets and launch.")
    else:
        print("Failed to apply theme")
