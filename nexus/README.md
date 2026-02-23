# Nexus - Multi-Entity Chat System

The crossroads where entities meet.

## What Is This

Nexus is a lightweight async chat server that lets multiple participants —
humans, AI wrappers, local models — communicate in real-time through a
shared message space.

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn websockets pydantic

# Start the server
python nexus/server.py

# In another terminal, connect as a human
python nexus/client_human.py --name Re

# In another terminal, connect an AI client
python nexus/client_ai.py --name EchoBot
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Re (human)  │     │ Kay (wrapper)│     │Reed (wrapper)│
│ client_human │     │  client_ai   │     │  client_ai   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────── WebSocket ────────────────────┘
                       │
              ┌────────┴────────┐
              │   Nexus Server   │
              │   (server.py)    │
              │                  │
              │  - Routing       │
              │  - History       │
              │  - Presence      │
              └─────────────────┘
```

## Files

- `models.py` — Message, Participant, ServerEvent data models
- `server.py` — FastAPI WebSocket hub
- `client_human.py` — Terminal chat client for humans
- `client_ai.py` — Base class for AI wrapper integration

## Message Types

| Type | Purpose |
|------|---------|
| `chat` | Normal conversation |
| `thought` | Internal monologue (visible, rendered dim) |
| `whisper` | Private message to specific recipients |
| `emote` | Action/roleplay text |
| `state_update` | Cognitive mode changes (DMN/TPN/idle) |
| `system` | Server announcements |
| `ping` | Lightweight presence signal |

## Client Commands

```
/who          - List connected participants
/w Name msg   - Whisper to someone
/emote text   - Send as emote
/think text   - Share a thought
/status away  - Set your status
/quit         - Disconnect
```

## Integrating a Wrapper

```python
from nexus.client_ai import NexusAIClient

class KayNexusClient(NexusAIClient):
    async def on_message(self, message: dict):
        # This is where DMN/TPN/Salience routing will live
        response = await your_wrapper.generate(message["content"])
        await self.send_chat(response)

client = KayNexusClient("Kay", "ws://localhost:8765")
await client.run()
```

## Roadmap

- [x] Phase 1A: Basic chat infrastructure (THIS)
- [ ] Phase 1B: Wire Kay/Reed wrappers into NexusAIClient
- [ ] Phase 2: Salience classifier for message routing
- [ ] Phase 3: TPN (local fast model) for quick responses
- [ ] Phase 4: DMN cycling (background deep processing)
