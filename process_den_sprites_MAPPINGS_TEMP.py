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
