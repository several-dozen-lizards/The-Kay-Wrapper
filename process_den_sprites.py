"""
Den & Commons Sprite Processing Script

Processes sprite images for all rooms:
1. Removes white backgrounds (makes transparent)
2. Copies to Godot UI sprite directories
3. Creates sprite manifest for room system

Usage:
    python process_den_sprites.py

Requires: Pillow (pip install Pillow)
"""

import os
import json
from pathlib import Path
from PIL import Image
import shutil

# Configuration - D:\Wrappers paths
SOURCE_DIR = Path("D:/Wrappers/Graphics/Room")
GODOT_SPRITES_DIR = Path("D:/Wrappers/nexus/godot-ui/sprites")

# White background threshold (how close to white = transparent)
WHITE_THRESHOLD = 235  # Lower = more aggressive (was 240)

# Object sprite mappings (source filename -> object_id)
# Based on actual files in D:/Wrappers/Graphics/Room
OBJECT_MAPPINGS = {
    # ── DEN FURNITURE ──
    "Couch-front.png": "couch",
    "Desk-front.png": "desk",
    "Desk-top.png": "desk_top",
    "Bookshelf-front.png": "bookshelf",
    
    # ── DEN DECORATIVE ──
    "Blankets-front.png": "blankets",
    "Rug-front.png": "rug",
    
    # ── COMMONS OBJECTS ──
    "gol.png": "gol",
    "codebase.png": "codebase",
    "research.png": "research",
    "roundtable.png": "roundtable",
    "Hearth.png": "hearth",
    "Portal.png": "portal",
    "Easel.png": "easel",
    "Scratchpad.png": "scratchpad",
    
    # ── FLOOR TILES (keep backgrounds) ──
    "Floor-Rectangle.png": "floor",
    "Floor1-copper.png": "floor_copper_1",
    "Floor2-copper.png": "floor_copper_2",
    "Floor1-LED.png": "floor_led",
}

# Objects that should NOT have background removed (floor tiles)
KEEP_BACKGROUND = ["floor", "floor_copper_1", "floor_copper_2", "floor_led"]


def remove_white_background(image_path: Path, output_path: Path, 
                            threshold: int = WHITE_THRESHOLD) -> bool:
    """
    Remove white background from image and save as transparent PNG.
    
    Uses IMPROVED logic: checks if pixel is "bright and neutral"
    (all RGB values are high AND similar to each other = white-ish)
    
    Args:
        image_path: Source image path
        output_path: Destination path
        threshold: RGB value threshold (0-255) - pixels brighter than this become transparent
    
    Returns:
        True if successful
    """
    try:
        # Open image
        img = Image.open(image_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Get pixel data
        pixels = img.load()
        width, height = img.size
        
        # Process each pixel
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                
                # IMPROVED: Check if pixel is white-ish
                # Must be: bright (average >= threshold) AND neutral (low color variation)
                avg = (r + g + b) / 3
                color_range = max(r, g, b) - min(r, g, b)
                
                # If average brightness is high AND colors are similar = white-ish
                if avg >= threshold and color_range < 15:
                    pixels[x, y] = (r, g, b, 0)  # Set alpha to 0 (transparent)
        
        # Save as PNG with transparency
        img.save(output_path, 'PNG')
        print(f"  ✓ Processed: {image_path.name} -> {output_path.name}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error processing {image_path.name}: {e}")
        return False


def copy_with_background(image_path: Path, output_path: Path) -> bool:
    """Copy image without background removal (for floors, etc.)."""
    try:
        shutil.copy2(image_path, output_path)
        print(f"  ✓ Copied: {image_path.name} -> {output_path.name}")
        return True
    except Exception as e:
        print(f"  ✗ Error copying {image_path.name}: {e}")
        return False


def process_sprites():
    """Main processing function."""
    print("="*70)
    print("DEN & COMMONS SPRITE PROCESSING")
    print("="*70)
    
    # Check source directory
    if not SOURCE_DIR.exists():
        print(f"\n✗ Source directory not found: {SOURCE_DIR}")
        print("  Please check the path and try again.")
        return
    
    # List available images
    source_images = list(SOURCE_DIR.glob("*.png"))
    if not source_images:
        print(f"\n✗ No PNG images found in {SOURCE_DIR}")
        return
    
    print(f"\nFound {len(source_images)} images in source directory:")
    for img_path in source_images:
        print(f"  - {img_path.name}")
    
    # Create sprite directories
    (GODOT_SPRITES_DIR / "objects").mkdir(parents=True, exist_ok=True)
    (GODOT_SPRITES_DIR / "entities").mkdir(parents=True, exist_ok=True)
    (GODOT_SPRITES_DIR / "environment").mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("Processing images...")
    print(f"{'='*70}\n")
    
    processed_manifest = {
        "objects": {},
        "entities": {},
        "environment": {},
        "processed_at": None
    }
    
    # Process each image
    for source_path in source_images:
        filename = source_path.name
        
        # Determine object type and ID
        object_id = OBJECT_MAPPINGS.get(filename)
        if not object_id:
            # Try without extension
            base_name = source_path.stem
            object_id = OBJECT_MAPPINGS.get(f"{base_name}.png", base_name)
        
        # Determine category
        if object_id in ["kay", "reed"]:
            category = "entities"
        elif object_id in KEEP_BACKGROUND:
            category = "environment"
        else:
            category = "objects"
        
        # Process for Godot
        print(f"\nProcessing {filename} (object_id: {object_id}, category: {category})")
        print(f"  Godot UI sprites:")
        
        output = GODOT_SPRITES_DIR / category / f"{object_id}.png"
        
        if category == "environment" or object_id in KEEP_BACKGROUND:
            # Keep background for floors
            copy_with_background(source_path, output)
        else:
            # Remove white background
            remove_white_background(source_path, output)
        
        # Add to manifest
        processed_manifest[category][object_id] = {
            "source_file": filename,
            "sprite_path": f"{category}/{object_id}.png",
            "has_transparency": category != "environment" and object_id not in KEEP_BACKGROUND
        }
    
    # Save manifest
    from datetime import datetime
    processed_manifest["processed_at"] = datetime.now().isoformat()
    
    manifest_path = GODOT_SPRITES_DIR / "sprite_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(processed_manifest, f, indent=2)
    print(f"\n✓ Saved manifest: {manifest_path}")
    
    print(f"\n{'='*70}")
    print("PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"\nProcessed {len(source_images)} images")
    print(f"  Objects: {len(processed_manifest['objects'])}")
    print(f"  Entities: {len(processed_manifest['entities'])}")
    print(f"  Environment: {len(processed_manifest['environment'])}")
    print(f"\nSprites deployed to:")
    print(f"  - {GODOT_SPRITES_DIR / 'objects'}")
    print(f"  - {GODOT_SPRITES_DIR / 'entities'}")
    print(f"  - {GODOT_SPRITES_DIR / 'environment'}")
    print(f"\nNext steps:")
    print(f"  1. Check processed sprites in Godot UI sprites directory")
    print(f"  2. Restart Godot to reimport assets")
    print(f"  3. Launch Nexus to see your beautiful sprites in The Commons!")


if __name__ == "__main__":
    try:
        from PIL import Image
    except ImportError:
        print("ERROR: Pillow is required for image processing")
        print("Install with: pip install Pillow")
        exit(1)
    
    process_sprites()
