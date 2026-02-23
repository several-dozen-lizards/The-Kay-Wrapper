"""
Entity Paint Module — gives wrapper entities the ability to create visual art.

Entities output structured paint commands during autonomous processing.
The processor executes them via PIL and saves results.

KEY FEATURES:
- Canvas persists across iterations (entity can build on previous work)
- Each iteration's additions are saved as snapshots
- Base64 feedback lets entity "see" what it painted
- No create_canvas needed after first iteration — continues on existing canvas
- Reset with explicit create_canvas if starting fresh

Usage:
    painter = EntityPainter("D:/ChristinaStuff/ReedMemory/Paint")
    result = painter.execute(commands_list)
    # result = {"filepath": "...", "base64": "...", "dimensions": [...], "is_continuation": bool}
"""

import json
import base64
import os
from datetime import datetime
from io import BytesIO
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class EntityPainter:
    """Executes structured paint commands from entity output.
    
    Canvas persists between execute() calls — entity can build across
    iterations without re-creating. Tracks session painting for multi-
    iteration artwork.
    """

    def __init__(self, save_dir: str):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self.canvas: Optional[Image.Image] = None
        self.draw: Optional[ImageDraw.ImageDraw] = None
        # Track the current session's painting for file naming
        self._session_name: str = ""
        self._iteration_count: int = 0

    def start_session(self, session_name: str = ""):
        """Called when a new autonomous session begins. Resets canvas state."""
        self._session_name = session_name or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._iteration_count = 0
        self.canvas = None
        self.draw = None

    def load_from_file(self, filepath: str) -> bool:
        """Load a saved PNG as the active canvas so painting can continue on it.
        
        Returns True if loaded successfully.
        """
        if not HAS_PIL or not os.path.isfile(filepath):
            return False
        try:
            img = Image.open(filepath).convert("RGBA")
            self.canvas = img
            self.draw = ImageDraw.Draw(self.canvas)
            return True
        except Exception as e:
            print(f"[entity_paint] Failed to load {filepath}: {e}")
            return False

    def has_canvas(self) -> bool:
        """Whether there's an active canvas to continue working on."""
        return self.canvas is not None

    def get_canvas_b64(self) -> Optional[str]:
        """Get current canvas state as base64 PNG for feeding back to entity."""
        if not self.canvas:
            return None
        buf = BytesIO()
        self.canvas.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def get_canvas_dimensions(self) -> Optional[list]:
        """Get [width, height] of current canvas."""
        if not self.canvas:
            return None
        return [self.canvas.width, self.canvas.height]

    def execute(self, commands: list[dict], filename: str = "") -> dict:
        """Execute a sequence of paint commands and save the result.
        
        If canvas already exists and no create_canvas in commands,
        continues drawing on existing canvas (multi-iteration painting).
        
        Args:
            commands: List of command dicts, each with "action" and params
            filename: Optional filename. Auto-generated if empty.
            
        Returns:
            {
                "filepath": str,
                "base64": str,
                "dimensions": [w, h],
                "is_continuation": bool,
                "iteration": int,
            }
        """
        if not HAS_PIL:
            return {"error": "PIL/Pillow not installed"}

        is_continuation = self.canvas is not None
        has_create = any(c.get("action") == "create_canvas" for c in commands)

        # If no canvas and no create_canvas command, auto-create default
        if not self.canvas and not has_create:
            self._create_canvas({"width": 800, "height": 600, "bg_color": "#1a1a2e"})

        for cmd in commands:
            action = cmd.get("action", "")
            try:
                self._dispatch(action, cmd)
            except Exception as e:
                print(f"[entity_paint] Error in {action}: {e}")

        if self.canvas is None:
            return {"error": "No canvas created"}

        self._iteration_count += 1

        # Generate filename
        if not filename:
            if self._session_name:
                filename = f"{self._session_name}_iter{self._iteration_count:02d}.png"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"auto_{timestamp}.png"

        filepath = os.path.join(self.save_dir, filename)
        self.canvas.save(filepath)

        b64 = self.get_canvas_b64()

        return {
            "filepath": filepath,
            "base64": b64,
            "dimensions": self.get_canvas_dimensions(),
            "is_continuation": is_continuation and not has_create,
            "iteration": self._iteration_count,
        }

    def _dispatch(self, action: str, cmd: dict):
        """Route command to appropriate handler."""
        handlers = {
            "create_canvas": self._create_canvas,
            "draw_line": self._draw_line,
            "draw_circle": self._draw_circle,
            "draw_rectangle": self._draw_rectangle,
            "fill_region": self._fill_region,
            "draw_text": self._draw_text,
        }
        handler = handlers.get(action)
        if handler:
            handler(cmd)

    def _create_canvas(self, cmd: dict):
        w = cmd.get("width", 800)
        h = cmd.get("height", 600)
        bg = cmd.get("bg_color", "white")
        self.canvas = Image.new("RGBA", (w, h), bg)
        self.draw = ImageDraw.Draw(self.canvas)

    def _draw_line(self, cmd: dict):
        if not self.draw:
            return
        self.draw.line(
            [(cmd["x1"], cmd["y1"]), (cmd["x2"], cmd["y2"])],
            fill=cmd.get("color", "black"),
            width=cmd.get("width", 2),
        )

    def _draw_circle(self, cmd: dict):
        if not self.draw:
            return
        x, y, r = cmd["x"], cmd["y"], cmd["radius"]
        bbox = [x - r, y - r, x + r, y + r]
        self.draw.ellipse(
            bbox,
            fill=cmd.get("fill_color") or None,
            outline=cmd.get("outline_color", "black"),
            width=cmd.get("outline_width", 2),
        )

    def _draw_rectangle(self, cmd: dict):
        if not self.draw:
            return
        self.draw.rectangle(
            [(cmd["x1"], cmd["y1"]), (cmd["x2"], cmd["y2"])],
            fill=cmd.get("fill_color") or None,
            outline=cmd.get("outline_color", "black"),
            width=cmd.get("outline_width", 2),
        )

    def _fill_region(self, cmd: dict):
        if not self.canvas:
            return
        ImageDraw.floodfill(
            self.canvas,
            (cmd["x"], cmd["y"]),
            _parse_color(cmd.get("color", "black")),
        )

    def _draw_text(self, cmd: dict):
        if not self.draw:
            return
        self.draw.text(
            (cmd.get("x", 10), cmd.get("y", 10)),
            cmd.get("text", ""),
            fill=cmd.get("color", "black"),
        )


def _parse_color(color):
    """Handle color names and hex values."""
    if isinstance(color, str) and color.startswith("#"):
        color = color.lstrip("#")
        if len(color) == 6:
            return tuple(int(color[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        elif len(color) == 8:
            return tuple(int(color[i:i+2], 16) for i in (0, 2, 4, 6))
    return color


def parse_paint_commands(raw: str) -> list[dict]:
    """Parse paint commands from entity output.
    
    Expects JSON array inside <paint> tags:
    <paint>[
        {"action": "create_canvas", "width": 800, "height": 600, "bg_color": "#1a1a2e"},
        {"action": "draw_circle", "x": 400, "y": 300, "radius": 100, "fill_color": "#00ff88"}
    ]</paint>
    """
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return []


def canvas_feedback_message(paint_result: dict, is_vision_capable: bool = True) -> dict:
    """Build a message containing the canvas state for feeding back to entity.
    
    Returns a message dict suitable for inclusion in the conversation:
    - If vision-capable: includes base64 image so entity can SEE what it painted
    - If not: includes text description of dimensions and filepath
    
    Args:
        paint_result: Return value from EntityPainter.execute()
        is_vision_capable: Whether the model can process images
        
    Returns:
        Message content block(s) for inclusion in conversation messages
    """
    if "error" in paint_result:
        return {"type": "text", "text": f"[Paint error: {paint_result['error']}]"}

    dims = paint_result.get("dimensions", [0, 0])
    is_cont = paint_result.get("is_continuation", False)
    iteration = paint_result.get("iteration", 0)
    filepath = paint_result.get("filepath", "")

    status = "continued painting" if is_cont else "new painting"
    header = f"[Your {status} (iteration {iteration}, {dims[0]}x{dims[1]}px) saved to {os.path.basename(filepath)}]"

    if is_vision_capable and paint_result.get("base64"):
        # Return list of content blocks for multimodal message
        return [
            {"type": "text", "text": header + "\nHere's what your canvas looks like now:"},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": paint_result["base64"],
                }
            },
            {"type": "text", "text": "You can continue adding to this canvas in your next iteration, or start fresh with create_canvas."},
        ]
    else:
        return {"type": "text", "text": header}
