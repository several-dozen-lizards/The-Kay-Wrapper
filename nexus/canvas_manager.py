"""
Canvas Manager — orchestrates per-entity painting in Nexus.

Wraps EntityPainter instances, handles broadcasting canvas updates
to WebSocket clients, and provides the feedback loop for agentic painting.

Each entity gets its own persistent canvas and save directory.
"""

import os
import json
import logging
import re
from typing import Optional, Callable, Awaitable

from entity_paint import EntityPainter, parse_paint_commands, canvas_feedback_message

log = logging.getLogger("nexus.canvas")


class CanvasManager:
    """Manages per-entity canvases and routes paint events to UI."""

    def __init__(self, save_dir: str, broadcast_fn: Callable[..., Awaitable]):
        """
        Args:
            save_dir: Root directory for canvas saves (e.g. sessions/canvas/)
            broadcast_fn: async fn(event_type: str, data: dict) to push to WS clients
        """
        self.save_dir = save_dir
        self.broadcast_fn = broadcast_fn
        self.painters: dict[str, EntityPainter] = {}
        os.makedirs(save_dir, exist_ok=True)

    def get_painter(self, entity: str) -> EntityPainter:
        """Get or create painter for entity."""
        if entity not in self.painters:
            entity_dir = os.path.join(self.save_dir, entity.lower())
            os.makedirs(entity_dir, exist_ok=True)
            self.painters[entity] = EntityPainter(entity_dir)
            self.painters[entity].start_session()
        return self.painters[entity]

    async def execute_paint(self, entity: str, commands: list[dict], filename: str = "") -> dict:
        """Execute paint commands and broadcast result to all clients.

        Returns the paint result dict from EntityPainter.execute().
        """
        painter = self.get_painter(entity)
        result = painter.execute(commands, filename=filename)

        if "error" in result:
            log.warning(f"[CANVAS {entity}] Paint error: {result['error']}")
            return result

        log.info(
            f"[CANVAS {entity}] Iteration {result.get('iteration', 0)} — "
            f"{result.get('dimensions', [0,0])[0]}x{result.get('dimensions', [0,0])[1]} — "
            f"{'continued' if result.get('is_continuation') else 'new'}"
        )

        # Broadcast to Godot UI and any other connected clients
        await self.broadcast_fn("canvas_update", {
            "entity": entity,
            "base64": result.get("base64", ""),
            "dimensions": result.get("dimensions", [0, 0]),
            "iteration": result.get("iteration", 0),
            "filepath": result.get("filepath", ""),
            "is_continuation": result.get("is_continuation", False),
        })

        return result

    def get_canvas_state(self, entity: str) -> Optional[dict]:
        """Get current canvas state for entity (for LLM feedback loop)."""
        painter = self.painters.get(entity)
        if not painter or not painter.has_canvas():
            return None
        return {
            "base64": painter.get_canvas_b64(),
            "dimensions": painter.get_canvas_dimensions(),
        }

    def get_feedback_message(self, entity: str, result: dict, vision: bool = True) -> any:
        """Build multimodal feedback message for entity's next context.

        Returns content block(s) suitable for inclusion in LLM messages.
        """
        return canvas_feedback_message(result, is_vision_capable=vision)

    async def clear_canvas(self, entity: str):
        """Reset entity's canvas."""
        if entity in self.painters:
            self.painters[entity].canvas = None
            self.painters[entity].draw = None
            self.painters[entity]._iteration_count = 0
            log.info(f"[CANVAS {entity}] Canvas cleared")
            await self.broadcast_fn("canvas_clear", {"entity": entity})

    def list_saves(self, entity: str) -> list[dict]:
        """List saved canvas iterations for entity."""
        entity_dir = os.path.join(self.save_dir, entity.lower())
        if not os.path.isdir(entity_dir):
            return []
        files = []
        for f in sorted(os.listdir(entity_dir)):
            if f.lower().endswith(".png"):
                fpath = os.path.join(entity_dir, f)
                files.append({
                    "filename": f,
                    "path": fpath,
                    "size": os.path.getsize(fpath),
                    "modified": os.path.getmtime(fpath),
                })
        return files

    def get_latest_save(self, entity: str) -> Optional[dict]:
        """Get the most recent saved canvas as base64 for initial display.
        
        Returns dict with base64, dimensions, filename — or None.
        """
        saves = self.list_saves(entity)
        if not saves:
            return None
        latest = saves[-1]  # sorted by filename, chronological
        try:
            from PIL import Image
            from io import BytesIO
            import base64 as b64mod
            img = Image.open(latest["path"])
            buf = BytesIO()
            img.save(buf, format="PNG")
            return {
                "base64": b64mod.b64encode(buf.getvalue()).decode("utf-8"),
                "dimensions": [img.width, img.height],
                "filename": latest["filename"],
                "filepath": latest["path"],
                "iteration": len(saves),
            }
        except Exception as e:
            log.warning(f"[CANVAS {entity}] Failed to read latest save: {e}")
            return None

    async def load_save(self, entity: str, filename: str) -> dict:
        """Load a saved iteration back as the active canvas.
        
        Entity can then continue painting on it.
        Returns the loaded canvas state or error.
        """
        entity_dir = os.path.join(self.save_dir, entity.lower())
        filepath = os.path.join(entity_dir, filename)
        if not os.path.isfile(filepath):
            return {"error": f"File not found: {filename}"}

        painter = self.get_painter(entity)
        if not painter.load_from_file(filepath):
            return {"error": f"Failed to load: {filename}"}

        state = {
            "entity": entity,
            "loaded": filename,
            "base64": painter.get_canvas_b64(),
            "dimensions": painter.get_canvas_dimensions(),
        }

        log.info(f"[CANVAS {entity}] Loaded saved canvas: {filename}")

        # Broadcast so Godot shows it
        await self.broadcast_fn("canvas_update", {
            "entity": entity,
            "base64": state["base64"],
            "dimensions": state["dimensions"],
            "iteration": 0,  # reset — continuing from loaded state
            "filepath": filepath,
            "is_continuation": True,
        })

        return state
        return files


# ---------------------------------------------------------------------------
# Paint tag extraction — pulls <paint> blocks from entity responses
# ---------------------------------------------------------------------------

PAINT_TAG_RE = re.compile(r"<paint>\s*(.*?)\s*</paint>", re.DOTALL)


def extract_paint_commands(text: str) -> tuple[list[dict], str]:
    """Extract <paint> command blocks from entity response text.

    Returns:
        (commands, clean_text) where commands is the parsed JSON list
        and clean_text is the response with <paint> blocks removed.
    """
    all_commands = []
    clean = text

    for match in PAINT_TAG_RE.finditer(text):
        raw_json = match.group(1)
        try:
            cmds = json.loads(raw_json)
            if isinstance(cmds, list):
                all_commands.extend(cmds)
        except json.JSONDecodeError as e:
            log.warning(f"[CANVAS] Failed to parse paint commands: {e}")

    # Remove paint tags from text for clean chat display
    clean = PAINT_TAG_RE.sub("", text).strip()

    return all_commands, clean
