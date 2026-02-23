"""
Nexus Chat Server
Multi-entity async messaging hub.

Architecture:
  - FastAPI app with WebSocket endpoint
  - Participants connect with a name and type
  - Messages broadcast to all connected participants (or whispered to specific ones)
  - Message history kept in memory (later: persistent storage)
  - Designed for Re, Kay-wrapper, Reed-wrapper, and future entities

To run:
  python server.py [--host 0.0.0.0] [--port 8765]

Clients connect to: ws://localhost:8765/ws/{participant_name}?type={human|ai_wrapper}
"""

import asyncio
import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from models import (
    Message, Participant, ServerEvent,
    MessageType, ParticipantType
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("nexus")

# ---------------------------------------------------------------------------
# Connection Manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    """Manages WebSocket connections and message routing."""

    def __init__(self, max_history: int = 500):
        # name -> WebSocket
        self.active_connections: dict[str, WebSocket] = {}
        # name -> Participant
        self.participants: dict[str, Participant] = {}
        # Rolling message history
        self.message_history: list[dict] = []
        self.max_history = max_history

    async def connect(
        self,
        websocket: WebSocket,
        name: str,
        participant_type: ParticipantType
    ) -> bool:
        """Accept a new connection. Returns False if name is taken."""
        if name in self.active_connections:
            await websocket.accept()
            await websocket.send_json(
                ServerEvent(
                    event_type="error",
                    data={"message": f"Name '{name}' is already connected."}
                ).model_dump()
            )
            await websocket.close()
            return False

        await websocket.accept()
        self.active_connections[name] = websocket
        self.participants[name] = Participant(
            name=name,
            participant_type=participant_type
        )
        log.info(f"✦ {name} ({participant_type.value}) connected")

        # Send recent history to the new participant
        await self._send_history(websocket)

        # Send current participant list
        await self._send_participant_list(websocket)

        # Announce to everyone else
        await self._broadcast_system(f"{name} has entered the Nexus.", persist=False)

        return True

    async def disconnect(self, name: str):
        """Handle participant disconnection."""
        if name in self.active_connections:
            del self.active_connections[name]
        if name in self.participants:
            del self.participants[name]
        log.info(f"✧ {name} disconnected")
        await self._broadcast_system(f"{name} has left the Nexus.", persist=False)

    async def handle_message(self, raw: dict, sender_name: str):
        """Process an incoming message from a participant."""
        
        # Handle command messages (status updates, etc.) before Message parsing
        if "command" in raw:
            cmd = raw["command"]
            if cmd == "status":
                await self.update_status(sender_name, raw.get("status", "online"))
                return
            log.warning(f"Unknown command from {sender_name}: {cmd}")
            return
        
        try:
            msg = Message(
                sender=sender_name,
                sender_type=self.participants[sender_name].participant_type,
                content=raw.get("content", ""),
                msg_type=MessageType(raw.get("msg_type", "chat")),
                reply_to=raw.get("reply_to"),
                recipients=raw.get("recipients"),
                metadata=raw.get("metadata", {})
            )
        except Exception as e:
            log.warning(f"Bad message from {sender_name}: {e}")
            ws = self.active_connections.get(sender_name)
            if ws:
                await ws.send_json(
                    ServerEvent(
                        event_type="error",
                        data={"message": f"Invalid message: {e}"}
                    ).model_dump()
                )
            return

        # Store in history
        msg_dict = msg.model_dump()
        self.message_history.append(msg_dict)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]

        # Route the message
        if msg.msg_type == MessageType.WHISPER and msg.recipients:
            await self._send_whisper(msg)
        elif msg.msg_type == MessageType.STATE_UPDATE:
            await self._handle_state_update(msg)
        else:
            await self._broadcast_message(msg)

    async def update_status(self, name: str, status: str):
        """Update a participant's status (online, idle, thinking, away)."""
        if name in self.participants:
            self.participants[name].status = status
            event = ServerEvent(
                event_type="status_update",
                data={"name": name, "status": status}
            )
            await self._broadcast_event(event)

    # --- Internal routing methods ---

    async def _broadcast_message(self, msg: Message):
        """Send a message to all connected participants."""
        event = ServerEvent(
            event_type="message",
            data=msg.model_dump()
        )
        await self._broadcast_event(event)

    async def _send_whisper(self, msg: Message):
        """Send a message only to specified recipients + sender."""
        event = ServerEvent(
            event_type="message",
            data=msg.model_dump()
        )
        payload = event.model_dump()
        targets = set(msg.recipients or [])
        targets.add(msg.sender)
        disconnected = []
        for name in targets:
            ws = self.active_connections.get(name)
            if ws:
                try:
                    await ws.send_json(payload)
                except Exception:
                    disconnected.append(name)
        for name in disconnected:
            await self.disconnect(name)

    async def _broadcast_system(self, text: str, persist: bool = True):
        """Send a system announcement to all participants.
        
        Args:
            text: The announcement text
            persist: If True, store in message_history for replay.
                     If False, fire-and-forget (connected clients see it,
                     but it won't replay to future connections).
        """
        msg = Message(
            sender="Nexus",
            sender_type=ParticipantType.SYSTEM,
            content=text,
            msg_type=MessageType.SYSTEM
        )
        if persist:
            self.message_history.append(msg.model_dump())
        event = ServerEvent(
            event_type="message",
            data=msg.model_dump()
        )
        await self._broadcast_event(event)

    async def _broadcast_event(self, event: ServerEvent):
        """Send an event to ALL connected participants."""
        payload = event.model_dump()
        disconnected = []
        for name, ws in self.active_connections.items():
            try:
                await ws.send_json(payload)
            except Exception:
                disconnected.append(name)
        for name in disconnected:
            await self.disconnect(name)

    async def _send_history(self, websocket: WebSocket, count: int = 50):
        """Send recent message history to a newly connected client."""
        recent = self.message_history[-count:] if self.message_history else []
        event = ServerEvent(
            event_type="history",
            data={"messages": recent}
        )
        await websocket.send_json(event.model_dump())

    async def _send_participant_list(self, websocket: WebSocket):
        """Send current participant list to a client."""
        plist = {
            name: p.model_dump()
            for name, p in self.participants.items()
        }
        event = ServerEvent(
            event_type="participant_list",
            data={"participants": plist}
        )
        await websocket.send_json(event.model_dump())

    async def _handle_state_update(self, msg: Message):
        """Process cognitive state updates from AI participants."""
        mode = msg.metadata.get("cognitive_mode", "unknown")
        if msg.sender in self.participants:
            self.participants[msg.sender].metadata["cognitive_mode"] = mode
        await self._broadcast_message(msg)


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=" * 50)
    log.info("  NEXUS CHAT SERVER")
    log.info("  The crossroads where entities meet.")
    log.info("=" * 50)
    yield
    log.info("Nexus shutting down.")


app = FastAPI(title="Nexus", lifespan=lifespan)


@app.websocket("/ws/{name}")
async def websocket_endpoint(
    websocket: WebSocket,
    name: str,
    type: str = Query(default="human")
):
    """
    WebSocket endpoint for chat participants.
    Connect to: ws://host:port/ws/YourName?type=human
    Types: human, ai_wrapper, ai_local, system
    """
    try:
        ptype = ParticipantType(type)
    except ValueError:
        ptype = ParticipantType.HUMAN

    connected = await manager.connect(websocket, name, ptype)
    if not connected:
        return

    try:
        while True:
            raw = await websocket.receive_json()
            if isinstance(raw, dict):
                cmd = raw.get("command")
                if cmd == "status":
                    await manager.update_status(
                        name, raw.get("status", "online")
                    )
                    continue
                elif cmd == "who":
                    await manager._send_participant_list(websocket)
                    continue
            await manager.handle_message(raw, name)

    except WebSocketDisconnect:
        await manager.disconnect(name)
    except Exception as e:
        log.error(f"Error with {name}: {e}")
        await manager.disconnect(name)


@app.get("/")
async def root():
    """Health check / info endpoint."""
    return {
        "name": "Nexus",
        "status": "running",
        "participants": list(manager.participants.keys()),
        "message_count": len(manager.message_history)
    }


@app.get("/history")
async def get_history(count: int = 50):
    """REST endpoint for message history (for clients that need it)."""
    recent = manager.message_history[-count:]
    return {"messages": recent, "total": len(manager.message_history)}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description="Nexus Chat Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
