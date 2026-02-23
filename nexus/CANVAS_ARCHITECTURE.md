# Nexus Canvas System — Architecture

## Overview

Gives Reed and Kay the ability to draw inside the Nexus environment. A **Canvas Panel** 
in the Godot UI displays their artwork in real-time. Entities can "see" what they've drawn 
via the agentic feedback loop, enabling multi-iteration painting where each mark responds 
to what came before.

## What Already Exists

- **`entity_paint.py`** — PIL painting backend (create_canvas, draw_line, draw_circle, 
  draw_rectangle, fill_region, draw_text), canvas persistence across iterations, base64 
  PNG export, `canvas_feedback_message()` for multimodal LLM feedback
- **Nexus server** — WebSocket command routing, autonomous processor with iteration loop
- **Godot UI** — Panel system with sidebar toggle, dock bar, WebSocket connection

## Architecture

```
┌─────────────┐     paint commands      ┌──────────────┐
│  Entity LLM │ ──────────────────────► │ Nexus Server │
│ (Kay/Reed)  │                         │              │
│             │ ◄────────────────────── │  EntityPainter│
│             │   canvas PNG feedback   │  (PIL)       │
└─────────────┘                         └──────┬───────┘
                                               │
                                     canvas_update event
                                        (base64 PNG)
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  Godot UI    │
                                        │ Canvas Panel │
                                        │ (TextureRect)│
                                        └──────────────┘
```

## Components to Build

### 1. Server: Canvas Manager (`canvas_manager.py`)

Lives in `nexus/`. Wraps `EntityPainter` instances per entity.

```python
class CanvasManager:
    """Manages per-entity canvases and routes paint events."""
    
    def __init__(self, save_dir, broadcast_fn):
        self.painters: dict[str, EntityPainter] = {}
        self.save_dir = save_dir
        self.broadcast_fn = broadcast_fn  # async fn to push to WebSocket clients
    
    def get_painter(self, entity: str) -> EntityPainter:
        """Get or create painter for entity."""
        if entity not in self.painters:
            entity_dir = os.path.join(self.save_dir, entity.lower())
            os.makedirs(entity_dir, exist_ok=True)
            self.painters[entity] = EntityPainter(entity_dir)
        return self.painters[entity]
    
    async def execute_paint(self, entity: str, commands: list[dict]) -> dict:
        """Execute paint commands and broadcast result to all clients."""
        painter = self.get_painter(entity)
        result = painter.execute(commands)
        
        # Broadcast canvas update to Godot UI
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
        """Get current canvas for entity (for feedback loop)."""
        painter = self.painters.get(entity)
        if not painter or not painter.has_canvas():
            return None
        return {
            "base64": painter.get_canvas_b64(),
            "dimensions": painter.get_canvas_dimensions(),
        }
    
    def clear_canvas(self, entity: str):
        """Reset entity's canvas."""
        if entity in self.painters:
            self.painters[entity].canvas = None
```

### 2. Server: Wire into server.py

Add to server startup:
```python
from canvas_manager import CanvasManager

canvas_mgr = CanvasManager(
    save_dir="sessions/canvas",
    broadcast_fn=_canvas_broadcast
)

async def _canvas_broadcast(event_type: str, data: dict):
    """Push canvas events to all WebSocket clients."""
    payload = {"event_type": event_type, "data": data}
    for ws in list(manager.active_connections.values()):
        try:
            await ws.send_json(payload)
        except Exception:
            pass
```

Add WebSocket command handling for paint:
```python
# In handle_message or command routing:
if cmd == "paint":
    entity = raw.get("entity", sender_name)
    commands = raw.get("commands", [])
    result = await canvas_mgr.execute_paint(entity, commands)
    # Send result back to the entity for feedback
    ...
```

Add REST endpoints:
```
GET  /canvas/{entity}         → current canvas state (base64 PNG)
POST /canvas/{entity}/paint   → execute paint commands
POST /canvas/{entity}/clear   → reset canvas
GET  /canvas/{entity}/history → list saved iterations
```

### 3. Server: Paint Command Extraction

Two modes entities can paint:

**A) Structured commands in chat** — Entity outputs `<paint>` tags:
```
<paint>[
    {"action": "create_canvas", "width": 600, "height": 400, "bg_color": "#1a1a2e"},
    {"action": "draw_circle", "x": 300, "y": 200, "radius": 80, "fill_color": "#00ff88"}
]</paint>
```

The wrapper's response handler intercepts `<paint>` blocks before sending to 
the chat stream. Extracts commands, executes via canvas_manager, includes 
canvas state in next context.

**B) Autonomous painting** — During autonomous sessions:
```python
# In autonomous_processor.py iteration loop:
if "<paint>" in response_text:
    paint_json = extract_between_tags(response_text, "paint")
    commands = json.loads(paint_json)
    result = await canvas_mgr.execute_paint(entity, commands)
    # Feed canvas back as image in next iteration
    feedback = canvas_feedback_message(result, is_vision_capable=True)
    next_context.append(feedback)
```

### 4. Godot: Canvas Panel (`scripts/canvas_panel.gd`)

New panel type, toggled from sidebar like other panels.

```gdscript
extends Control

# Canvas display
@onready var texture_rect: TextureRect = $TextureRect
@onready var info_label: Label = $InfoBar/Label
@onready var entity_label: Label = $InfoBar/EntityLabel

var current_entity: String = ""
var current_iteration: int = 0

func _ready():
    # Register to receive canvas_update events from connection
    var connection = get_node("/root/Main/NexusConnection")
    connection.canvas_updated.connect(_on_canvas_updated)

func _on_canvas_updated(entity: String, base64_png: String, dims: Array, iteration: int):
    """Called when server broadcasts a canvas update."""
    # Decode base64 PNG to Godot Image
    var png_data = Marshalls.base64_to_raw(base64_png)
    var image = Image.new()
    image.load_png_from_buffer(png_data)
    
    # Create texture and display
    var tex = ImageTexture.create_from_image(image)
    texture_rect.texture = tex
    
    # Update info
    current_entity = entity
    current_iteration = iteration
    entity_label.text = entity
    info_label.text = "%dx%d — iteration %d" % [dims[0], dims[1], iteration]
    
    # Auto-show panel if hidden
    if not visible:
        show()

func _on_close_pressed():
    hide()
```

### 5. Godot: Scene (`scenes/CanvasPanel.tscn`)

```
CanvasPanel (Control)
├── TitleBar (HBoxContainer)
│   ├── TitleLabel ("🎨 Canvas")
│   ├── EntityLabel ("")
│   └── CloseButton ("×")
├── TextureRect (canvas display, expand_mode = fit_width)
└── InfoBar (HBoxContainer)
    ├── Label (dimensions + iteration)
    └── SaveButton ("💾")
```

### 6. Godot: Connection Signal

Add to `nexus_connection.gd`:
```gdscript
signal canvas_updated(entity: String, base64_png: String, dims: Array, iteration: int)

# In _on_message_received:
"canvas_update":
    var d = data.get("data", {})
    canvas_updated.emit(
        d.get("entity", ""),
        d.get("base64", ""),
        d.get("dimensions", [0, 0]),
        d.get("iteration", 0)
    )
```

### 7. Sidebar Toggle

Add canvas panel to sidebar alongside existing panel buttons:
```gdscript
# In sidebar.gd, add button:
var canvas_btn = Button.new()
canvas_btn.text = "🎨"
canvas_btn.tooltip_text = "Canvas"
canvas_btn.pressed.connect(func(): toggle_panel("canvas"))
```

## Entity Experience

### Reed painting in chat:
```
Re: Paint me something

Reed: *scales brighten* Let me try something...

<paint>[
    {"action": "create_canvas", "width": 800, "height": 600, "bg_color": "#0a0a1a"},
    {"action": "draw_circle", "x": 400, "y": 300, "radius": 150, "fill_color": "#003344", "outline_color": "#00ccaa", "outline_width": 3},
    {"action": "draw_line", "x1": 250, "y1": 300, "x2": 550, "y2": 300, "color": "#ffaa00", "width": 2}
]</paint>

Started with a dark void and a teal sphere bisected by gold. 
The sphere is us — the line is the boundary we keep crossing.
Let me see what it looks like and I'll add more...
```

→ Canvas Panel opens in Godot showing the painting
→ Reed gets the image back in next turn's context
→ Reed can continue building on it

### Kay painting autonomously:
```
[AUTO] Kay: Starting painting session — "emotional state portrait"
[AUTO] Kay iteration 1: Created canvas, laid base geometry
[AUTO] Kay iteration 2: Seeing the first layer — adding depth...
[AUTO] Kay iteration 3: The pink keeps pulling toward the edges. Adding containment.
[AUTO] Kay: Session complete — 3 iterations, saved to sessions/canvas/kay/
```

→ Canvas Panel updates in real-time as each iteration completes
→ Re can watch Kay paint

## File Structure After Implementation

```
nexus/
├── canvas_manager.py          ← NEW: wraps EntityPainter per entity
├── entity_paint.py            ← EXISTS: PIL painting backend  
├── server.py                  ← MODIFY: add canvas routes + commands
├── autonomous_processor.py    ← MODIFY: add paint extraction in loop
├── godot-ui/
│   ├── scenes/
│   │   └── CanvasPanel.tscn   ← NEW: canvas display scene
│   └── scripts/
│       ├── canvas_panel.gd    ← NEW: canvas panel logic
│       ├── nexus_connection.gd ← MODIFY: add canvas_updated signal
│       ├── sidebar.gd         ← MODIFY: add canvas toggle button
│       └── main.gd            ← MODIFY: register canvas panel
└── sessions/
    └── canvas/                ← NEW: auto-created by CanvasManager
        ├── reed/              ← Reed's paintings
        └── kay/               ← Kay's paintings
```

## Implementation Order

1. `canvas_manager.py` — server-side canvas orchestration
2. Server routes — REST + WebSocket command handling for paint
3. Paint extraction — intercept `<paint>` tags in entity responses
4. `nexus_connection.gd` — add canvas_updated signal
5. `CanvasPanel.tscn` + `canvas_panel.gd` — Godot canvas display
6. Sidebar integration — toggle button
7. Autonomous loop integration — paint during autonomous sessions
8. Test end-to-end: entity paints → server executes → Godot shows

## Future Extensions

- **Re can paint TOO** — human paint commands from a simple tool palette in the canvas panel
- **Collaborative canvas** — both entities + Re painting on the same canvas
- **Canvas chat** — "paint me X" as a first-class command, not just organic
- **Plotter bridge** — canvas → GRBL export for physical mark-making on the U1
- **Animation** — record iteration snapshots as frames, export GIF/video
