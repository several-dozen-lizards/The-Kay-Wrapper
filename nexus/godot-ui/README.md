# Nexus Godot UI

The crossroads where entities meet. Visual dock interface for the Nexus multi-entity chat system.

## Layout
- **Left panel**: Group chat (Nexus) - all participants visible
- **Right panel**: Stacked wrapper panels (Kay top, Reed bottom)
- All splits are draggable/resizable

## Setup

### 1. Install Godot 4.3+
Download from: https://godotengine.org/download/
- Get "Godot Engine - .NET" or standard (we use standard/GDScript)
- It's portable - just an exe, no install needed
- Extract somewhere like `D:\Tools\Godot\`

### 2. Open Project
- Launch Godot
- Click "Import" 
- Navigate to `D:\Wrappers\nexus\godot-ui\`
- Select `project.godot`
- Click "Import & Edit"

### 3. Run
- Make sure Nexus server is running (`python launch_nexus.py` from nexus dir)
- Hit F5 in Godot editor (or the Play button)
- UI connects to ws://localhost:8765 as "Re"

## Architecture
```
Main.tscn
├── NexusConnection (WebSocket client)
├── Background (dark theme)
└── MainSplit (HSplitContainer, draggable)
    ├── GroupChat (ChatPanel instance)
    └── WrapperSplit (VSplitContainer, draggable)
        ├── WrapperSlot1 - Kay (ChatPanel instance)
        └── WrapperSlot2 - Reed (ChatPanel instance)
```

## Files
- `scripts/nexus_connection.gd` - WebSocket client, signal-based
- `scripts/chat_panel.gd` - Reusable chat display + input
- `scripts/main.gd` - Wires everything together, routes messages
- `scenes/ChatPanel.tscn` - Chat panel scene (instanced 3x)
- `Main.tscn` - Root scene with layout

## Commands (in group chat input)
- `/who` - List participants
- `/emote text` - Send emote action
- `/w Name message` - Whisper to someone
- `/clear` - Clear chat display
- `/help` - Show commands

## Fonts
Drop `NotoColorEmoji-Regular.ttf` into `fonts/` for emoji support.
Get it from: https://fonts.google.com/noto/specimen/Noto+Color+Emoji

## Next Steps
- [ ] Theme resources per panel (Kay purple, Reed teal, Nexus dark)
- [ ] Animated border effects (shimmer, particles)
- [ ] Individual wrapper input fields (talk to Kay/Reed directly)
- [ ] Font fallback chain for emoji
- [ ] Connection status indicators per entity
- [ ] Minimap/participant sidebar
