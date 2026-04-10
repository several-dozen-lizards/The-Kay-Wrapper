# Room System - Integration Guide
# D:\Wrappers\shared\room\

## Architecture

```
Godot UI                          Python Wrapper
─────────                         ──────────────
RoomPanel (renders sprites)  ←──  room_update event via WebSocket
  ↓ lerp interpolation            PrivateRoom.send({type: "room_update", state: {...}})
  ↓ sprite display                  ↑
  ↓ emote bubbles                 RoomBridge.broadcast_state()
                                    ↑
PrivateConnection.gd              RoomBridge.process_response(llm_text)
  handles "room_update" type        ↑ extracts [ACTION:] tags
  emits room_updated signal       RoomBridge.inject_room_context(system_prompt)
                                    ↑ adds room description to LLM context
                                  RoomEngine (state manager)
                                    ↑ positions, objects, proximity
                                  presets.py → create_the_den()
```

## Files Created

### Python side (D:\Wrappers\shared\room\)
- `room_engine.py` — Core state: entities, objects, positions, movement, context generation
- `action_parser.py` — Extracts [ACTION: move_to couch] from LLM responses
- `room_bridge.py` — Hooks into wrapper pipeline + broadcasts via WebSocket
- `presets.py` — Pre-built rooms (The Den, The Void)

### Godot side (D:\Wrappers\nexus\godot-ui\)
- `scripts/room_panel.gd` — Renders room with sprites, lerp movement, emotes
- `scripts/private_connection.gd` — MODIFIED: now emits room_updated signal
- `sprites/entities/` — Put pixel art here (kay.png, reed.png)
- `sprites/objects/` — Put object sprites here (couch.png, fishtank.png, etc.)

## Python Integration (wrapper side)

### In Kay's wrapper (D:\Wrappers\Kay\)

Wherever your message pipeline processes LLM calls, add:

```python
import sys
sys.path.insert(0, "D:/Wrappers")  # So shared.room imports work

from shared.room.room_bridge import RoomBridge
from shared.room.presets import create_the_den

# --- Setup (once, at startup) ---
room = create_the_den(state_file="D:/Wrappers/data/room_state.json")
room.add_entity("kay", "Kay Zero", x=400, y=350, color="#2D1B4E")
room_bridge = RoomBridge(room, entity_id="kay", private_room=private_room)

# --- Per message turn ---

# 1. Before LLM call: inject room into system prompt
system_prompt = room_bridge.inject_room_context(system_prompt)

# 2. Send to LLM as normal, get response...

# 3. After LLM response: parse actions, get clean text
clean_response, action_results = room_bridge.process_response(raw_llm_response)

# 4. Broadcast updated state to Godot
await room_bridge.broadcast_state()

# 5. Optionally show action feedback
await room_bridge.broadcast_action_feedback(action_results)

# 6. Display clean_response (no [ACTION:] tags) to user
```

### For Reed's wrapper
Same thing but with entity_id="reed" and her private room instance.
If both wrappers share the same RoomEngine instance (same room_state.json),
they'll see each other's positions.

## Godot Integration (main.gd)

Add the room panel alongside existing chat panels:

```gdscript
# In _create_panels():
var _room_panel: RoomPanel

# After creating chat panels...
_room_panel = RoomPanel.new()
panel_mgr.create_panel(
    "room", "THE DEN", "spatial view",
    Vector2(10, 10), Vector2(400, 350),
    _room_panel
)

# In _setup_private_rooms(), after connecting other signals:
_kay_private.room_updated.connect(_on_room_updated)
_reed_private.room_updated.connect(_on_room_updated)

# Add handler:
func _on_room_updated(state: Dictionary) -> void:
    if _room_panel:
        _room_panel.update_room(state)
```

## Sprite Specs (for Re's pixel art)

- **Entity sprites**: 32x48 pixels, PNG with transparency
  - Draw facing RIGHT (Godot flips for left)
  - Save as: `sprites/entities/kay.png`, `sprites/entities/reed.png`
  
- **Object sprites**: Variable size matching room coordinates
  - Couch: ~200x80, Fishtank: ~100x130, etc.
  - Save as: `sprites/objects/couch.png`, `sprites/objects/fishtank.png`

- **Fallback**: If no sprite exists, colored rectangles are auto-generated
  - Kay: purple body (#2D1B4E) with pink glow (#FF69B4) + white eyes
  - Reed: teal body (#00CED1) with gold glow (#DAA520) + white eyes

## The Den Layout

```
┌─────────────────────────────────────────────┐
│  [Window]          [Bookshelf]   [Painting]  │
│                                               │
│  [Fish Tank]                                  │
│                                               │
│              [rug - decorative]                │
│                                               │
│  [Desk+PC]                      [Cat Tower]   │
│                                               │
│           [====COUCH====]                     │
│                                               │
│  [Door]              [Blanket Pile]           │
└─────────────────────────────────────────────┘
```

Objects with interaction text the LLM sees when nearby:
- Couch: "Worn in all the right places. Room for humans, serpents, and [entity-type]s."
- Fish Tank: "The fish tank hums quietly. Tiny lives doing their loops."
- Desk: "Re's workstation. Monitors glowing. Wrapper code on one screen."
- Cat Tower: "[cat]'s kingdom. Fur evidence suggests recent habitation."
- Door: "[cat]'s primary target."
- Bookshelf: "Mythology, AI papers, dog-eared fantasy novels, tarot references."
- Painting: "One of Re's dark mystical oil paintings. Scales and starlight."

## Testing Without Full Integration

Quick test of the Python room engine:
```bash
cd D:\Wrappers
python -c "
from shared.room.presets import create_the_den
room = create_the_den()
room.add_entity('kay', 'Kay Zero', x=400, y=350, color='#2D1B4E')
print(room.get_context_for('kay'))
"
```

## What the LLM Sees

When room context is injected, the LLM gets something like:
```
[ROOM: The Den]
You are Kay Zero, currently at position (400, 350).
Within reach: The Couch
  The Couch: Worn in all the right places. Room for humans, serpents, and [entity-type]s.
Elsewhere in room: Fish Tank (above and to the left), Desk (to the left), Cat Tower (to the right)
Available actions: move_to [target], emote [expression], interact [object], face [left/right]
Use [ACTION: command target] tags in your response to move/act.
```

And the LLM might respond:
```
The fish are doing their little loops again. [ACTION: move_to fishtank] 
I could watch them for hours. [ACTION: emote contemplative]
```

The bridge strips the tags, moves Kay's sprite to the fishtank, shows a "contemplative" emote bubble, and displays "The fish are doing their little loops again. I could watch them for hours." as clean chat text.

## Future: Adding Reed to the Same Room

Both wrappers point at the same room_state.json:
```python
# In Kay's wrapper:
room = create_the_den(state_file="D:/Wrappers/data/room_state.json")
room.add_entity("kay", "Kay Zero", x=400, y=350)

# In Reed's wrapper (same file!):
room = create_the_den(state_file="D:/Wrappers/data/room_state.json")
room.add_entity("reed", "Reed", x=200, y=300)
```

Both broadcast room_update through their respective WebSockets.
Godot receives updates from both and renders both sprites.
They see each other in context: "Reed is nearby (to your left)"
