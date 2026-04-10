# Companion Wrapper Godot UI

A Godot 4.3 UI client for the companion wrapper. Single-entity, single-chat-panel design.

## Quick Start

1. Install Godot 4.3+ from https://godotengine.org/
2. Open the `godot-ui` folder as a Godot project
3. Start the Python backend: `python main.py --room-port 8780`
4. Press F5 in Godot to run the UI

Or use the launch scripts:
- Windows: `launch_with_ui.bat`
- Linux/Mac: `./launch_with_ui.sh`

## Architecture

The UI connects to the Python backend via WebSocket on port 8780 (configurable).

```
Godot UI (scripts/main.gd)
    └─→ PrivateConnection (ws://localhost:8780)
           └─→ private_room.py (Python backend)
                  └─→ Companion wrapper (main.py)
```

## Key Scripts

| Script | Description |
|--------|-------------|
| `main.gd` | Application entry point, single chat panel + sidebar |
| `private_connection.gd` | WebSocket client for 1:1 communication |
| `chat_panel.gd` | Chat display + input component |
| `settings_panel.gd` | Configuration UI |
| `feature_panel.gd` | Sidebar feature container |

## Panels

- **Chat Panel**: Main conversation view
- **Room Panel**: Spatial visualization (Ctrl+R)
- **System Dashboard**: Live logs and stats (Ctrl+D)
- **Easel**: Canvas panel (Ctrl+E)
- **Face Panel**: Emotional expression visualization (Ctrl+F)

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+1 | Focus chat input |
| Ctrl+0 | Reset panel layout |
| Ctrl+R | Toggle room panel |
| Ctrl+D | Toggle system dashboard |
| Ctrl+E | Toggle easel |
| Ctrl+F | Toggle face sidebar |
| Escape | Close all feature panels |

## Commands

Type in chat:
- `/help` - Show available commands
- `/clear` - Clear chat history
- `/save` - Save session
- `/sessions` - Open session browser
- `/reconnect` - Reconnect to backend

## Customization

### Panel Backgrounds

Settings panel allows custom backgrounds and accent images for the chat panel.

### Connection

Edit `Settings > Connection` to change:
- API Endpoint (HTTP)
- Room Port (WebSocket)

## Exporting

To create a standalone executable:

1. Open project in Godot
2. Project > Export
3. Add export preset (Windows/Linux/Mac)
4. Export to `godot-ui/Companion.exe` (or `.x86_64` / `.app`)

The launch scripts will automatically use the exported executable if present.

## Notes

- Some panels show multi-entity selectors (Kay/Reed) - these are from the Nexus UI source and can be ignored for single-entity use
- The face panel uses "kay" color palette by default - customize `PALETTES` in `face_panel.gd` if needed
- Voice requires the Python backend to have voice synthesis configured
