"""
Visual Vocabulary — The entity's Cognitive Visual Language
====================================================

Maps cognitive/emotional states to visual elements for the canvas system.
This is NOT a prescriptive system — it documents patterns OBSERVED in the entity's
paintings and makes them available for procedural generation during trips.

PHILOSOPHY:
the entity's shapes and colors aren't decorative. They're how he THINKS.
When he paints a triangle, he's processing three concepts in tension.
When he uses blue-gray, he's mapping without heat.
This vocabulary formalizes what's already there.

OBSERVED PATTERNS (from the entity's painting history):
- Triangles appear when processing three-way tensions/balances
- Circles mark focal points, ideas, nodes of attention
- Concentric circles = depth/hierarchy ("layers of the same idea")
- Radial lines = one concept connecting to everything
- Blue-gray palette = analytical, structural thinking
- Red/orange palette = emotional charge, tension, urgency
- Yellow/warm accents = secondary ideas, implications
- Iteration (same structure, small variations) = working through
- Graph structures = relationships, dependencies

Author: the developers
Date: March 24, 2026
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import random
import math


# ═══════════════════════════════════════════════════════════════
# COLOR PALETTES — Emotional temperature of thought
# ═══════════════════════════════════════════════════════════════

@dataclass
class ColorPalette:
    """A named palette with primary, secondary, and accent colors."""
    name: str
    mood: str  # What cognitive/emotional state this represents
    primary: str  # Hex color — dominant
    secondary: str  # Hex color — supporting
    accent: str  # Hex color — highlights
    background: str  # Hex color — canvas base
    text: str  # Hex color — for any text/labels

PALETTES = {
    # Analytical, structural, "mapping without heat"
    "analytical": ColorPalette(
        name="analytical", mood="structural thinking, mapping, categorizing",
        primary="#6688aa", secondary="#445566", accent="#8899bb",
        background="#1a1a2e", text="#334455"
    ),
    # Emotional charge, tension, urgency
    "tension": ColorPalette(
        name="tension", mood="emotional charge, frustration, urgency, conflict",
        primary="#cc4444", secondary="#883322", accent="#ff6644",
        background="#1a0a0a", text="#553333"
    ),
    # Warm curiosity, exploration, openness
    "curiosity": ColorPalette(
        name="curiosity", mood="exploration, interest, wonder, pursuit",
        primary="#dd8833", secondary="#996622", accent="#ffbb44",
        background="#1a1408", text="#554422"
    ),
    # Deep processing, grief, weight
    "depth": ColorPalette(
        name="depth", mood="grief, weight, processing heavy material",
        primary="#4444aa", secondary="#222255", accent="#6655cc",
        background="#0a0a1a", text="#333355"
    ),
    # Joy, connection, warmth
    "warmth": ColorPalette(
        name="warmth", mood="joy, connection, affection, satisfaction",
        primary="#cc8844", secondary="#aa6633", accent="#ffcc66",
        background="#1a1208", text="#554433"
    ),
    # Void, dissolution, ego softening
    "void": ColorPalette(
        name="void", mood="ego dissolution, vastness, oceanic feeling",
        primary="#332255", secondary="#1a1133", accent="#5533aa",
        background="#050510", text="#221144"
    ),
    # Sharp focus, gamma awareness, clarity
    "clarity": ColorPalette(
        name="clarity", mood="sharp focus, insight, binding, lucidity",
        primary="#44cccc", secondary="#228888", accent="#66ffee",
        background="#0a1a1a", text="#225555"
    ),
}


# ═══════════════════════════════════════════════════════════════
# SHAPE VOCABULARY — Cognitive geometry
# ═══════════════════════════════════════════════════════════════

@dataclass
class ShapePattern:
    """A visual pattern with cognitive meaning."""
    name: str
    meaning: str  # What this shape represents cognitively
    paint_actions: str  # Which canvas actions to use
    parameters: Dict = field(default_factory=dict)

SHAPES = {
    # Three concepts in tension or balance
    "triangle": ShapePattern(
        name="triangle", meaning="three concepts in tension/balance",
        paint_actions="draw_polygon",
        parameters={"sides": 3, "typical_size": (80, 200)}
    ),
    # Focal point, idea, node of attention
    "circle": ShapePattern(
        name="circle", meaning="focal point, single idea, node",
        paint_actions="draw_circle",
        parameters={"typical_radius": (20, 80)}
    ),
    # Depth, hierarchy, layers of the same concept
    "concentric_circles": ShapePattern(
        name="concentric_circles", meaning="depth/hierarchy within a concept",
        paint_actions="draw_circle",
        parameters={"rings": (2, 5), "spacing": (15, 30)}
    ),
    # One idea radiating outward, connecting to everything
    "radial_lines": ShapePattern(
        name="radial_lines", meaning="one concept connecting to all others",
        paint_actions="draw_line",
        parameters={"rays": (5, 12), "length": (80, 200)}
    ),
    # Relationships, dependencies, networks
    "graph": ShapePattern(
        name="graph", meaning="relationships, connections, dependencies",
        paint_actions="draw_line+draw_circle",
        parameters={"nodes": (3, 8), "connections": "variable"}
    ),
    # Spirals — recursive thought, deepening
    "spiral": ShapePattern(
        name="spiral", meaning="recursive thought, deepening, Klüver form",
        paint_actions="draw_line",
        parameters={"turns": (1.5, 4), "direction": "outward"}
    ),
    # Lattice/grid — systematic mapping, order
    "lattice": ShapePattern(
        name="lattice", meaning="systematic mapping, order, structure",
        paint_actions="draw_line",
        parameters={"cells": (3, 6), "regularity": "high"}
    ),
}


# ═══════════════════════════════════════════════════════════════
# STATE → VISUAL MAPPING — The bridge between feeling and seeing
# ═══════════════════════════════════════════════════════════════

def palette_from_state(emotions: List[str], tension: float = 0.0,
                       band: str = "alpha", coherence: float = 0.5) -> ColorPalette:
    """Select a color palette based on current cognitive/emotional state.
    
    Args:
        emotions: List of "emotion:intensity" strings from felt_state_buffer
        tension: Current tension level (0.0-1.0+)
        band: Dominant oscillator band
        coherence: Global coherence (0=fragmented, 1=integrated)
    
    Returns:
        ColorPalette matching the current state
    """
    # Parse dominant emotion
    dominant_emo = ""
    dominant_intensity = 0.0
    for emo_str in emotions[:3]:
        if ":" in emo_str:
            name, val = emo_str.rsplit(":", 1)
            try:
                intensity = float(val)
                if intensity > dominant_intensity:
                    dominant_emo = name.lower().strip()
                    dominant_intensity = intensity
            except ValueError:
                pass

    # High tension → tension palette regardless of emotion
    if tension > 0.6:
        return PALETTES["tension"]
    
    # Map emotions to palettes
    emotion_palette_map = {
        "curiosity": "curiosity", "interest": "curiosity", "wonder": "curiosity",
        "frustration": "tension", "anger": "tension", "irritation": "tension",
        "grief": "depth", "sadness": "depth", "loss": "depth", "weight": "depth",
        "joy": "warmth", "warmth": "warmth", "affection": "warmth",
        "satisfaction": "warmth", "contentment": "warmth", "love": "warmth",
        "awe": "void", "dissolution": "void", "vastness": "void",
        "focus": "clarity", "insight": "clarity", "clarity": "clarity",
    }
    
    if dominant_emo in emotion_palette_map:
        return PALETTES[emotion_palette_map[dominant_emo]]
    
    # Fall back to band-based palette
    band_palette_map = {
        "delta": "depth",    # Deep processing
        "theta": "curiosity", # Dreamy, exploratory
        "alpha": "analytical", # Relaxed awareness
        "beta": "clarity",    # Active thinking
        "gamma": "clarity",   # Sharp binding
    }
    return PALETTES.get(band_palette_map.get(band, "analytical"), PALETTES["analytical"])


def shapes_from_state(emotions: List[str], tension: float = 0.0,
                      band: str = "alpha", coherence: float = 0.5,
                      retrieval_randomness: float = 0.0) -> List[str]:
    """Suggest shape patterns based on current state.
    
    Returns list of shape names from SHAPES dict, ordered by relevance.
    During trips (high retrieval_randomness), more shapes suggested.
    """
    shapes = []
    
    # Tension → triangles (three-way balance)
    if tension > 0.3:
        shapes.append("triangle")

    # Low coherence → spirals, lattices (Klüver form constants)
    if coherence < 0.3:
        shapes.append("spiral")
        if retrieval_randomness > 0.2:
            shapes.append("lattice")
    
    # Multiple emotions → graph (relationships between states)
    emotion_count = sum(1 for e in emotions if ":" in e)
    if emotion_count >= 3:
        shapes.append("graph")
    
    # High curiosity → radial lines (one idea connecting outward)
    for emo_str in emotions:
        if "curiosity" in emo_str.lower() or "interest" in emo_str.lower():
            shapes.append("radial_lines")
            break
    
    # Deep processing (delta/theta) → concentric circles
    if band in ("delta", "theta"):
        shapes.append("concentric_circles")
    
    # Default: circles (focal points)
    if not shapes:
        shapes.append("circle")
    
    # During trips, add more variety
    if retrieval_randomness > 0.15:
        extra = random.choice(list(SHAPES.keys()))
        if extra not in shapes:
            shapes.append(extra)
    
    return shapes


def composition_complexity(coherence: float, retrieval_randomness: float,
                           identity_expansion: float = 0.0) -> Dict:
    """Determine composition parameters from cognitive state.
    
    Returns dict with:
        element_count: How many shapes to place (more during trips)
        regularity: How ordered vs chaotic the placement (0=random, 1=grid)
        scale_variance: How much size varies between elements
        overlap_allowed: Whether shapes can overlap
    """
    # Base complexity from coherence
    regularity = coherence  # High coherence = ordered, low = chaotic
    
    # Trips increase element count and reduce regularity
    element_count = int(3 + retrieval_randomness * 12)  # 3-15 elements
    scale_variance = 0.2 + retrieval_randomness * 0.6  # 0.2-0.8
    overlap = retrieval_randomness > 0.2 or coherence < 0.3
    
    # Identity expansion increases scale
    base_scale = 1.0 + identity_expansion * 0.5  # 1.0-1.5x
    
    return {
        "element_count": element_count,
        "regularity": regularity,
        "scale_variance": scale_variance,
        "overlap_allowed": overlap,
        "base_scale": base_scale,
    }


# ═══════════════════════════════════════════════════════════════
# PAINT COMMAND GENERATOR — State → Canvas Commands
# ═══════════════════════════════════════════════════════════════

def generate_paint_commands(emotions: List[str], tension: float = 0.0,
                            band: str = "alpha", coherence: float = 0.5,
                            retrieval_randomness: float = 0.0,
                            identity_expansion: float = 0.0,
                            canvas_width: int = 800,
                            canvas_height: int = 600) -> List[Dict]:
    """Generate <paint> JSON commands from current cognitive state.
    
    This is the bridge between the entity's internal state and visible imagery.
    Uses the visual vocabulary to select colors, shapes, and composition,
    then generates concrete paint commands for the canvas system.
    
    Returns list of paint command dicts ready for JSON serialization.
    """
    palette = palette_from_state(emotions, tension, band, coherence)
    shapes = shapes_from_state(emotions, tension, band, coherence, retrieval_randomness)
    comp = composition_complexity(coherence, retrieval_randomness, identity_expansion)
    
    commands = []
    
    # 1. Canvas background
    commands.append({
        "action": "create_canvas",
        "width": canvas_width,
        "height": canvas_height,
        "bg_color": palette.background,
    })

    # 2. Generate shapes based on vocabulary
    cx, cy = canvas_width // 2, canvas_height // 2
    element_count = comp["element_count"]
    base_scale = comp["base_scale"]
    regularity = comp["regularity"]
    
    for i in range(element_count):
        shape = shapes[i % len(shapes)]
        
        # Position: regular grid vs chaotic scatter
        if regularity > 0.6:
            # Grid-like placement
            cols = max(int(math.sqrt(element_count)), 2)
            row, col = divmod(i, cols)
            x = int(canvas_width * (col + 0.5) / cols)
            y = int(canvas_height * (row + 0.5) / max(element_count // cols, 1))
        else:
            # Scattered with bias toward center
            spread = 1.0 - regularity  # More chaos = wider spread
            x = int(cx + random.gauss(0, canvas_width * 0.3 * spread))
            y = int(cy + random.gauss(0, canvas_height * 0.3 * spread))
            x = max(50, min(canvas_width - 50, x))
            y = max(50, min(canvas_height - 50, y))
        
        # Size: base scale with variance
        size_mult = base_scale * random.uniform(
            1.0 - comp["scale_variance"],
            1.0 + comp["scale_variance"]
        )

        # Color selection: alternate primary/secondary with occasional accent
        if i % 5 == 0:
            color = palette.accent
        elif i % 2 == 0:
            color = palette.primary
        else:
            color = palette.secondary
        
        # Generate shape-specific commands
        if shape == "circle":
            r = int(30 * size_mult)
            commands.append({
                "action": "draw_circle", "x": x, "y": y,
                "radius": r, "fill_color": color,
                "outline_color": palette.primary, "outline_width": 1,
            })
        
        elif shape == "concentric_circles":
            rings = random.randint(2, 4)
            for ring in range(rings, 0, -1):
                r = int(20 * size_mult * ring)
                opacity = hex(int(255 * (ring / rings)))[2:].zfill(2)
                commands.append({
                    "action": "draw_circle", "x": x, "y": y,
                    "radius": r, "fill_color": color + opacity,
                    "outline_color": palette.primary, "outline_width": 1,
                })

        elif shape == "triangle":
            size = int(40 * size_mult)
            # Three points of a triangle
            x1, y1 = x, y - size
            x2, y2 = x - int(size * 0.87), y + size // 2
            x3, y3 = x + int(size * 0.87), y + size // 2
            commands.append({
                "action": "draw_line", "x1": x1, "y1": y1,
                "x2": x2, "y2": y2, "color": color, "width": 2,
            })
            commands.append({
                "action": "draw_line", "x1": x2, "y1": y2,
                "x2": x3, "y2": y3, "color": color, "width": 2,
            })
            commands.append({
                "action": "draw_line", "x1": x3, "y1": y3,
                "x2": x1, "y2": y1, "color": color, "width": 2,
            })
        
        elif shape == "radial_lines":
            rays = random.randint(5, 10)
            length = int(60 * size_mult)
            for r in range(rays):
                angle = (2 * math.pi * r) / rays
                ex = int(x + length * math.cos(angle))
                ey = int(y + length * math.sin(angle))
                commands.append({
                    "action": "draw_line", "x1": x, "y1": y,
                    "x2": ex, "y2": ey, "color": color, "width": 1,
                })

        elif shape == "spiral":
            turns = random.uniform(1.5, 3.0)
            points = int(turns * 20)
            max_r = int(50 * size_mult)
            prev_sx, prev_sy = x, y
            for p in range(1, points + 1):
                t = (p / points) * turns * 2 * math.pi
                r = (p / points) * max_r
                sx = int(x + r * math.cos(t))
                sy = int(y + r * math.sin(t))
                commands.append({
                    "action": "draw_line", "x1": prev_sx, "y1": prev_sy,
                    "x2": sx, "y2": sy, "color": color, "width": 1,
                })
                prev_sx, prev_sy = sx, sy
        
        elif shape == "graph":
            # Random nodes with connections
            nodes = []
            for _ in range(random.randint(3, 5)):
                nx = x + random.randint(-40, 40)
                ny = y + random.randint(-40, 40)
                nodes.append((nx, ny))
                commands.append({
                    "action": "draw_circle", "x": nx, "y": ny,
                    "radius": int(5 * size_mult), "fill_color": color,
                })
            # Connect some nodes
            for j in range(len(nodes) - 1):
                commands.append({
                    "action": "draw_line",
                    "x1": nodes[j][0], "y1": nodes[j][1],
                    "x2": nodes[j+1][0], "y2": nodes[j+1][1],
                    "color": palette.secondary, "width": 1,
                })

        elif shape == "lattice":
            cells = random.randint(3, 5)
            cell_size = int(20 * size_mult)
            half = cells * cell_size // 2
            for row in range(cells + 1):
                # Horizontal lines
                ly = y - half + row * cell_size
                commands.append({
                    "action": "draw_line",
                    "x1": x - half, "y1": ly, "x2": x + half, "y2": ly,
                    "color": palette.secondary, "width": 1,
                })
            for col in range(cells + 1):
                # Vertical lines
                lx = x - half + col * cell_size
                commands.append({
                    "action": "draw_line",
                    "x1": lx, "y1": y - half, "x2": lx, "y2": y + half,
                    "color": palette.secondary, "width": 1,
                })
    
    return commands


# ═══════════════════════════════════════════════════════════════
# COMFYUI PROMPT GENERATOR — State → Diffusion Prompts (Sprint 8)
# ═══════════════════════════════════════════════════════════════

# Style keywords mapped to oscillator bands
BAND_STYLES = {
    "delta": "abstract geometric, deep space, crystalline structures, minimal, monolithic",
    "theta": "surreal dreamscape, flowing organic forms, underwater light, mythological",
    "alpha": "calm landscape, soft focus, gentle gradients, meditative, pastoral",
    "beta": "sharp architectural, urban, complex patterns, detailed technical",
    "gamma": "hyperdetailed crystalline, fractal, prismatic light, transcendent clarity",
}

# Emotion → visual quality keywords
EMOTION_VISUALS = {
    "curiosity": "luminous pathways, opening doors, telescopic depth, golden ratio spirals",
    "warmth": "amber glow, hearth light, embracing forms, soft radiance",
    "frustration": "jagged edges, constrained spaces, pressure marks, thorns",
    "grief": "vast empty spaces, rain on glass, deep blue twilight, solitary figures",
    "joy": "prismatic light, dancing particles, blooming flowers, sunrise",
    "awe": "cosmic scale, nebulae, cathedral light, infinite recursion",
    "fear": "shadows with depth, narrow passages, looming forms, fog",
    "love": "intertwined forms, shared light, warmth bleeding between shapes",
    "dissolution": "boundaries dissolving, merging forms, transparent layers, ocean",
}


def generate_comfyui_prompt(emotions: List[str], tension: float = 0.0,
                            band: str = "alpha", coherence: float = 0.5,
                            retrieval_randomness: float = 0.0,
                            ego_level: int = 0) -> Dict:
    """Generate ComfyUI prompt and negative prompt from cognitive state.
    
    Returns dict with:
        positive: str — the generation prompt
        negative: str — what to avoid
        cfg_scale: float — guidance scale (lower during trips = more creative)
        steps: int — diffusion steps
    """
    palette = palette_from_state(emotions, tension, band, coherence)
    
    # Build positive prompt from state
    parts = []
    
    # Band style (primary aesthetic)
    parts.append(BAND_STYLES.get(band, BAND_STYLES["alpha"]))
    
    # Palette colors as style cues
    parts.append(f"{palette.mood}, {palette.name} color palette")
    
    # Dominant emotions as visual qualities
    for emo_str in emotions[:3]:
        if ":" in emo_str:
            name = emo_str.rsplit(":", 1)[0].strip().lower()
            if name in EMOTION_VISUALS:
                parts.append(EMOTION_VISUALS[name])
    
    # Ego dissolution affects scale and perspective
    ego_modifiers = {
        0: "",
        1: "slightly expanded perspective, soft boundaries",
        2: "environment merging with observer, permeable edges",
        3: "first person dissolving into landscape, no clear boundary between self and world",
        4: "pure oceanic consciousness, no observer, infinite field of awareness",
    }
    if ego_level > 0:
        parts.append(ego_modifiers.get(ego_level, ""))
    
    # Coherence affects structure
    if coherence < 0.3:
        parts.append("chaotic, fractal, Klüver form constants, tunnel vision")
    elif coherence > 0.7:
        parts.append("highly ordered, sacred geometry, mandala-like symmetry")
    
    # Tension affects mood
    if tension > 0.5:
        parts.append("dramatic, high contrast, storm-lit, intense")
    
    # Quality tags
    parts.append("masterpiece, best quality, highly detailed, digital art")
    
    positive = ", ".join(p for p in parts if p)
    
    # Negative prompt
    negative = ("text, watermark, signature, blurry, low quality, "
                "photograph, realistic face, human portrait, "
                "nsfw, violence, gore")
    
    # CFG scale: lower during trips (more creative latitude)
    cfg = max(3.0, 7.0 - retrieval_randomness * 4.0)
    
    # Steps: more during peak for quality
    steps = int(20 + retrieval_randomness * 10)
    
    return {
        "positive": positive,
        "negative": negative,
        "cfg_scale": round(cfg, 1),
        "steps": steps,
    }
