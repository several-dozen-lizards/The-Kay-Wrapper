#!/usr/bin/env python3
"""
Organize Reed-assets into proper structure and create Reed theme
"""
import shutil
from pathlib import Path

def organize_reed_assets():
    """Organize flat Reed-assets into subdirectory structure"""
    
    source = Path("Reed-assets")
    dest = Path("reed_assets")  # New organized directory
    
    # Create subdirectories
    (dest / "borders").mkdir(parents=True, exist_ok=True)
    (dest / "corners").mkdir(parents=True, exist_ok=True)
    (dest / "panels").mkdir(parents=True, exist_ok=True)
    (dest / "backgrounds").mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("ORGANIZING REED ASSETS")
    print("=" * 60)
    print()
    
    # Categorize files by name
    for file in source.glob("*.png"):
        name = file.name.lower()
        
        if "line" in name or "horizontal" in name or "vertical" in name:
            category = "borders"
        elif "panel" in name:
            category = "panels"
        elif "corner" in name:
            category = "corners"
        else:
            category = "panels"  # Default to panels for uncategorized
        
        dest_file = dest / category / file.name
        shutil.copy2(file, dest_file)
        print(f"  ✓ {file.name} → {category}/")
    
    print()
    print("=" * 60)
    print("ASSET ORGANIZATION COMPLETE")
    print("=" * 60)
    print()
    
    # Count assets
    borders = list((dest / "borders").glob("*.png"))
    panels = list((dest / "panels").glob("*.png"))
    corners = list((dest / "corners").glob("*.png"))
    
    print(f"Organized into reed_assets/:")
    print(f"  📏 borders/ : {len(borders)} files")
    print(f"  🎨 panels/  : {len(panels)} files")
    print(f"  📐 corners/ : {len(corners)} files")
    print()
    
    return True

if __name__ == "__main__":
    organize_reed_assets()
    print("Ready for theme application!")
