"""
Nexus Chat Server
Multi-entity async messaging hub.

Architecture:
  - FastAPI app with WebSocket endpoint
  - Participants connect with a name and type
  - Messages broadcast to all connected participants (or whispered to specific ones)
  - Message history kept in memory (500 rolling) + auto-logged to JSONL on disk
  - /save command exports formatted markdown transcript
  - Designed for Re, Kay-wrapper, Reed-wrapper, and future entities

Session persistence:
  - Auto-log: sessions/nexus_YYYYMMDD_HHMMSS.jsonl (every message, automatic)
  - /save: sessions/nexus_*_saved.md (formatted transcript, on demand)
  - REST: GET /save, GET /sessions (programmatic access)

To run:
  python server.py [--host 0.0.0.0] [--port 8765]

Clients connect to: ws://localhost:8765/ws/{participant_name}?type={human|ai_wrapper}
"""

import asyncio
import argparse
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from models import (
    Message, Participant, ServerEvent,
    MessageType, ParticipantType
)
from session_logger import SessionLogger
from autonomous_processor import NexusAutonomousProcessor
from curiosity_engine import CuriosityManager
from canvas_manager import CanvasManager, extract_paint_commands
from code_executor import extract_exec_commands, execute_code

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
        session_log.log_event("connect", {"name": name, "type": participant_type.value})

        # Send recent history to the new participant
        await self._send_history(websocket)

        # Send current participant list
        await self._send_participant_list(websocket)

        # Announce to everyone else
        await self._broadcast_system(f"{name} has entered the Nexus.")

        return True

    async def disconnect(self, name: str):
        """Handle participant disconnection."""
        if name in self.active_connections:
            del self.active_connections[name]
        if name in self.participants:
            del self.participants[name]
        log.info(f"✧ {name} disconnected")
        session_log.log_event("disconnect", {"name": name})
        await self._broadcast_system(f"{name} has left the Nexus.")

    async def handle_message(self, raw: dict, sender_name: str):
        """Process an incoming message from a participant."""
        
        # Handle command messages (status updates, etc.) before Message parsing
        if "command" in raw:
            cmd = raw["command"]
            if cmd == "status":
                await self.update_status(sender_name, raw.get("status", "online"))
                return
            # Forward targeted commands (warmup, set_affect, etc.) to specific wrapper
            target = raw.get("target")
            if target and target in self.active_connections:
                await self.active_connections[target].send_json({
                    "event_type": "command",
                    "data": {"command": cmd, "from": sender_name, **{k: v for k, v in raw.items() if k not in ("command", "target")}}
                })
                log.info(f"Forwarded command '{cmd}' from {sender_name} to {target}")
                return
            elif target:
                log.warning(f"Command target '{target}' not connected")
                ws = self.active_connections.get(sender_name)
                if ws:
                    await ws.send_json({"event_type": "error", "data": {"message": f"{target} is not connected"}})
                return
            # Paint commands from entities or human
            if cmd == "paint":
                entity = raw.get("entity", sender_name)
                commands = raw.get("commands", [])
                if commands:
                    result = await canvas_mgr.execute_paint(entity, commands)
                    # Send result back to sender for feedback
                    ws = self.active_connections.get(sender_name)
                    if ws:
                        await ws.send_json({
                            "event_type": "paint_result",
                            "data": {
                                "entity": entity,
                                "iteration": result.get("iteration", 0),
                                "dimensions": result.get("dimensions", [0, 0]),
                                "filepath": result.get("filepath", ""),
                                "error": result.get("error"),
                            }
                        })
                return
            if cmd == "clear_canvas":
                entity = raw.get("entity", sender_name)
                await canvas_mgr.clear_canvas(entity)
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

        # --- Paint tag extraction from entity messages ---
        if "<paint>" in msg.content:
            paint_cmds, clean_text = extract_paint_commands(msg.content)
            if paint_cmds:
                # Execute paint commands
                asyncio.create_task(
                    canvas_mgr.execute_paint(msg.sender, paint_cmds)
                )
                # Replace content with clean version (tags stripped)
                msg.content = clean_text
                log.info(f"[CANVAS] Extracted {len(paint_cmds)} paint commands from {msg.sender}")

        # --- Exec tag extraction from entity messages ---
        if "<exec" in msg.content:
            exec_cmds, clean_text = extract_exec_commands(msg.content)
            if exec_cmds:
                log.info(f"[EXEC] Extracted {len(exec_cmds)} code blocks from {msg.sender}")
                exec_results = []
                for cmd_block in exec_cmds:
                    result = await execute_code(
                        code=cmd_block["code"],
                        entity=msg.sender,
                        language=cmd_block.get("language", "python"),
                        description=f"{msg.sender} group chat exec"
                    )
                    exec_results.append(result)
                    status = "✓" if result.get("success") else "✗"
                    log.info(f"[EXEC] {status} {result.get('execution_time', '?')}s")
                # Append feedback to message
                feedback_parts = []
                for i, r in enumerate(exec_results):
                    if r.get("success"):
                        out = r.get("stdout", "").strip()
                        fb = f"[Code block {i+1} executed successfully"
                        if out:
                            fb += f": {out[:500]}"
                        if r.get("files_created"):
                            fb += f" | Created: {', '.join(r['files_created'])}"
                        fb += "]"
                    else:
                        err = r.get("stderr", r.get("error", "unknown error")).strip()
                        fb = f"[Code block {i+1} failed: {err[:300]}]"
                    feedback_parts.append(fb)
                msg.content = clean_text + "\n" + "\n".join(feedback_parts)

        # Store in history
        msg_dict = msg.model_dump()
        self.message_history.append(msg_dict)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]

        # Auto-log to disk
        session_log.log_message(msg_dict)

        # Route the message
        if msg.msg_type == MessageType.WHISPER and msg.recipients:
            await self._send_whisper(msg)
        elif msg.msg_type == MessageType.STATE_UPDATE:
            await self._handle_state_update(msg)
        else:
            await self._broadcast_message(msg)
        
        # --- Curiosity extraction trigger ---
        # After AI entity messages, count and maybe extract curiosities
        sender = msg.sender
        if sender in ("Kay", "Reed") and msg.msg_type in (MessageType.CHAT, MessageType.WHISPER):
            curiosity_manager.record_response(sender)
            if curiosity_manager.extractor.should_extract(sender):
                asyncio.create_task(self._run_curiosity_extraction(sender))

    async def _run_curiosity_extraction(self, entity: str):
        """Background curiosity extraction from recent conversation."""
        try:
            recent = []
            for msg in self.message_history[-20:]:
                recent.append({
                    "role": "user" if msg.get("sender") == "Re" else "assistant",
                    "content": msg.get("content", ""),
                })
            if recent:
                extracted = await curiosity_manager.maybe_extract(entity, recent)
                if extracted:
                    log.info(f"[CURIOSITY] Auto-extracted {len(extracted)} for {entity}")
        except Exception as e:
            log.warning(f"[CURIOSITY] Extraction error for {entity}: {e}")

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

    async def _broadcast_system(self, text: str):
        """Send a system announcement to all participants."""
        msg = Message(
            sender="Nexus",
            sender_type=ParticipantType.SYSTEM,
            content=text,
            msg_type=MessageType.SYSTEM
        )
        msg_dict = msg.model_dump()
        self.message_history.append(msg_dict)
        session_log.log_message(msg_dict)
        event = ServerEvent(
            event_type="message",
            data=msg_dict
        )
        await self._broadcast_event(event)

    async def _broadcast_event(self, event: ServerEvent):
        """Send an event to ALL connected participants."""
        payload = event.model_dump()
        disconnected = []
        for name, ws in list(self.active_connections.items()):
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
session_log = SessionLogger()


# ---------------------------------------------------------------------------
# Canvas Manager
# ---------------------------------------------------------------------------

async def _canvas_broadcast(event_type: str, data: dict):
    """Push canvas events to all connected WebSocket clients."""
    payload = {"event_type": event_type, "data": data}
    for ws in list(manager.active_connections.values()):
        try:
            await ws.send_json(payload)
        except Exception:
            pass

canvas_mgr = CanvasManager(
    save_dir=os.path.join(os.path.dirname(__file__), "sessions", "canvas"),
    broadcast_fn=_canvas_broadcast,
)


# ---------------------------------------------------------------------------
# Autonomous Processor
# ---------------------------------------------------------------------------

async def _auto_broadcast(entity: str, msg_type: str, data: dict):
    """Broadcast autonomous processing events to all connected WebSocket clients."""
    payload = json.dumps({
        "event_type": msg_type,
        "entity": entity,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    # Send to all connected participants (UI will filter by entity)
    for ws in list(manager.active_connections.values()):
        try:
            await ws.send_text(payload)
        except Exception:
            pass  # Disconnected clients get cleaned up elsewhere

# ---------------------------------------------------------------------------
# API Key loading (shared by autonomous processor)
# ---------------------------------------------------------------------------
def _load_api_key() -> Optional[str]:
    """Load Anthropic API key from environment or .env files."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    env_candidates = [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent.parent / "Kay" / ".env",
    ]
    for env_path in env_candidates:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "ANTHROPIC_API_KEY" in line and "=" in line:
                    key = line.split("=", 1)[1].strip().strip('"\'')
                    if key:
                        log.info(f"[AUTO] Loaded API key from {env_path}")
                        return key
    return None

_server_api_key = _load_api_key()
if not _server_api_key:
    log.warning("[AUTO] No API key found — autonomous standalone mode will fail. "
                "Set ANTHROPIC_API_KEY or create nexus/.env")

async def _autonomous_llm_fn(messages, entity: str) -> Optional[str]:
    """LLM function for autonomous processor — uses loaded API key."""
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=_server_api_key)
        system_msg = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                chat_messages.append(m)
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=system_msg,
            messages=chat_messages,
            temperature=0.85,
        )
        return response.content[0].text if response.content else None
    except Exception as e:
        log.error(f"[AUTO {entity}] LLM call failed: {e}")
        return None

auto_processor = NexusAutonomousProcessor(
    session_dir="sessions/autonomous",
    broadcast_fn=_auto_broadcast,
    llm_fn=_autonomous_llm_fn if _server_api_key else None,
)

# --- Curiosity Engine ---
curiosity_manager = CuriosityManager(
    llm_fn=_autonomous_llm_fn if _server_api_key else None,
    store_dir="sessions/curiosities",
)

# Wire curiosity into autonomous processor's goal resolution
auto_processor.curiosity_fn = lambda entity: curiosity_manager.pop_for_session(entity)

# --- Register entity context providers for autonomous sessions ---
# Without these, autonomous mode runs as generic Claude with a name tag.
# With these, Reed thinks as REED and Kay thinks as KAY.

def _reed_autonomous_context() -> str:
    """Build Reed's persona + memory context for autonomous sessions."""
    try:
        from nexus_reed import REED_PRIVATE_PROMPT, load_reed_memory
        parts = [REED_PRIVATE_PROMPT.strip()]
        memory = load_reed_memory()
        if memory:
            parts.append(memory)
        return "\n\n".join(parts)
    except Exception as e:
        log.warning(f"[AUTO] Could not load Reed context: {e}")
        return ""

auto_processor.register_entity_context("Reed", _reed_autonomous_context)

def _kay_autonomous_context() -> str:
    """Build Kay's persona + memory context for autonomous sessions."""
    try:
        import sys as _sys
        kay_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Kay")
        if kay_dir not in _sys.path:
            _sys.path.insert(0, kay_dir)
        from kay_prompts import KAY_SYSTEM_PROMPT
        parts = [KAY_SYSTEM_PROMPT.strip()]

        # Load emotional state if available
        snapshots_path = os.path.join(kay_dir, "data", "emotional_snapshots.json")
        if os.path.exists(snapshots_path):
            import json as _json
            with open(snapshots_path, "r", encoding="utf-8") as f:
                snapshots = _json.load(f)
            if isinstance(snapshots, list) and snapshots:
                recent = snapshots[-1]
                parts.append(f"[Current emotional state: {_json.dumps(recent, default=str)}]")
            elif isinstance(snapshots, dict):
                parts.append(f"[Current emotional state: {_json.dumps(snapshots, default=str)}]")

        return "\n\n".join(parts)
    except Exception as e:
        log.warning(f"[AUTO] Could not load Kay context: {e}")
        return ""

auto_processor.register_entity_context("Kay", _kay_autonomous_context)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=" * 50)
    log.info("  NEXUS CHAT SERVER")
    log.info("  The crossroads where entities meet.")
    log.info(f"  Session log: {session_log.jsonl_path.name}")
    log.info("=" * 50)
    yield
    session_log.log_event("session_end", {"message_count": session_log.message_count})
    log.info(f"Nexus shutting down. {session_log.message_count} messages logged to {session_log.jsonl_path.name}")


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
                # Check for /save command in chat content
                content = raw.get("content", "")
                if content.strip().lower().startswith("/save"):
                    # Extract optional filename after /save
                    parts = content.strip().split(maxsplit=1)
                    filename = parts[1] if len(parts) > 1 else None
                    save_path = session_log.save_transcript(
                        manager.message_history, filename=filename
                    )
                    # Announce to sender
                    await websocket.send_json({
                        "event_type": "message",
                        "data": Message(
                            sender="Nexus",
                            sender_type=ParticipantType.SYSTEM,
                            content=f"💾 Session saved to: {save_path}",
                            msg_type=MessageType.SYSTEM
                        ).model_dump()
                    })
                    log.info(f"Session saved by {name}: {save_path}")
                    continue

                # /auto commands
                if content.strip().lower().startswith("/auto"):
                    parts = content.strip().split()
                    action = parts[1].lower() if len(parts) > 1 else "status"
                    entity_hint = parts[2] if len(parts) > 2 else name  # default to sender
                    # Resolve entity name
                    ent = "Kay" if "kay" in entity_hint.lower() else "Reed" if "reed" in entity_hint.lower() else name

                    if action == "start":
                        topic = " ".join(parts[3:]) if len(parts) > 3 else None
                        result = await auto_processor.start_session(ent, topic)
                        status_msg = f"🧠 Autonomous session {'started' if 'error' not in result else 'failed'} for {ent}"
                        if result.get("topic"):
                            status_msg += f": {result['topic'][:80]}"
                        if result.get("error"):
                            status_msg += f" — {result['error']}"
                    elif action == "stop":
                        result = await auto_processor.stop_session(ent)
                        status_msg = f"🧠 Autonomous session stopped for {ent} ({result.get('iterations', 0)} iterations)"
                        if result.get("error"):
                            status_msg = f"🧠 {result['error']}"
                    else:
                        result = auto_processor.get_status(ent)
                        if result.get("active"):
                            status_msg = f"🧠 {ent}: Active — iteration {result['iterations']}, goal: {result.get('goal', 'choosing...')}"
                        else:
                            status_msg = f"🧠 {ent}: Idle (queue: {result.get('queue_depth', 0)} topics)"

                    await websocket.send_json({
                        "event_type": "message",
                        "data": Message(
                            sender="Nexus",
                            sender_type=ParticipantType.SYSTEM,
                            content=status_msg,
                            msg_type=MessageType.SYSTEM
                        ).model_dump()
                    })
                    continue

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


@app.post("/save")
@app.get("/save")
async def save_session(name: Optional[str] = None):
    """Save current session as a formatted markdown transcript."""
    save_path = session_log.save_transcript(
        manager.message_history, filename=name
    )
    log.info(f"Session saved via REST: {save_path}")
    return {
        "saved": save_path,
        "message_count": len(manager.message_history),
        "session_id": session_log.session_id
    }


@app.get("/sessions")
async def list_sessions():
    """List all saved session files."""
    from session_logger import SESSIONS_DIR
    files = sorted(SESSIONS_DIR.iterdir(), reverse=True)
    return {
        "current_session": session_log.session_id,
        "current_log": str(session_log.jsonl_path),
        "message_count": session_log.message_count,
        "saved_files": [
            {
                "name": f.name,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            }
            for f in files if f.is_file()
        ]
    }


@app.get("/sessions/{filename}")
async def load_session(filename: str):
    """Load messages from a saved JSONL session file."""
    from session_logger import SESSIONS_DIR
    import json as _json
    
    # Sanitize filename
    safe_name = "".join(c for c in filename if c.isalnum() or c in "-_. ")
    file_path = SESSIONS_DIR / safe_name
    
    if not file_path.exists():
        return {"error": f"Session not found: {safe_name}", "messages": []}
    
    messages = []
    events = []
    
    if file_path.suffix == ".jsonl":
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = _json.loads(line)
                    if "event" in data:
                        events.append(data)
                    elif "sender" in data:
                        messages.append(data)
                except _json.JSONDecodeError:
                    continue
    elif file_path.suffix == ".md":
        # For markdown transcripts, return raw text
        return {
            "filename": safe_name,
            "format": "markdown",
            "content": file_path.read_text(encoding="utf-8"),
            "messages": []
        }
    
    return {
        "filename": safe_name,
        "format": "jsonl",
        "message_count": len(messages),
        "events": events,
        "messages": messages
    }


# ---------------------------------------------------------------------------
# Canvas Endpoints
# ---------------------------------------------------------------------------

@app.get("/canvas/{entity}")
async def canvas_state(entity: str):
    """Get current canvas state for entity."""
    state = canvas_mgr.get_canvas_state(entity.capitalize())
    if not state:
        return {"entity": entity, "has_canvas": False}
    return {"entity": entity, "has_canvas": True, **state}


@app.post("/canvas/{entity}/paint")
async def canvas_paint(entity: str, commands: list[dict]):
    """Execute paint commands on entity's canvas via REST."""
    result = await canvas_mgr.execute_paint(entity.capitalize(), commands)
    return result


@app.post("/canvas/{entity}/clear")
async def canvas_clear(entity: str):
    """Clear entity's canvas."""
    await canvas_mgr.clear_canvas(entity.capitalize())
    return {"cleared": True, "entity": entity}


@app.get("/canvas/{entity}/history")
async def canvas_history(entity: str):
    """List saved canvas iterations for entity."""
    saves = canvas_mgr.list_saves(entity.capitalize())
    return {"entity": entity, "saves": saves}


@app.get("/canvas/{entity}/latest")
async def canvas_latest(entity: str):
    """Get the most recent saved canvas for initial display (easel mode)."""
    latest = canvas_mgr.get_latest_save(entity.capitalize())
    if not latest:
        return {"entity": entity, "has_canvas": False}
    return {"entity": entity, "has_canvas": True, **latest}


@app.post("/canvas/{entity}/load/{filename}")
async def canvas_load(entity: str, filename: str):
    """Load a saved iteration back as active canvas for continued painting."""
    result = await canvas_mgr.load_save(entity.capitalize(), filename)
    return result


# ---------------------------------------------------------------------------
# Autonomous Processing Endpoints
# ---------------------------------------------------------------------------

@app.post("/auto/{entity}/start")
async def auto_start(entity: str, topic: str = None):
    """Start autonomous processing session for an entity."""
    entity_name = entity.capitalize()
    if entity_name not in ("Kay", "Reed"):
        return {"error": f"Unknown entity: {entity}"}
    result = await auto_processor.start_session(entity_name, topic)
    return result


@app.post("/auto/{entity}/stop")
async def auto_stop(entity: str):
    """Stop active autonomous session."""
    entity_name = entity.capitalize()
    result = await auto_processor.stop_session(entity_name)
    return result


@app.get("/auto/{entity}/status")
async def auto_status(entity: str):
    """Get autonomous processing status for entity."""
    entity_name = entity.capitalize()
    return auto_processor.get_status(entity_name)


@app.get("/auto/status")
async def auto_status_all():
    """Get autonomous status for all entities."""
    return {
        "Kay": auto_processor.get_status("Kay"),
        "Reed": auto_processor.get_status("Reed"),
    }


@app.get("/auto/{entity}/queue")
async def auto_queue_get(entity: str):
    """View topic queue for entity."""
    entity_name = entity.capitalize()
    return {"entity": entity_name, "queue": auto_processor.topic_queue.peek(entity_name)}


@app.post("/auto/{entity}/queue")
async def auto_queue_add(entity: str, topic: str, priority: int = 0):
    """Add topic to autonomous processing queue."""
    entity_name = entity.capitalize()
    auto_processor.topic_queue.add(entity_name, topic, priority)
    return {"entity": entity_name, "topic": topic, "priority": priority,
            "queue_depth": len(auto_processor.topic_queue.peek(entity_name))}


@app.delete("/auto/{entity}/queue/{index}")
async def auto_queue_remove(entity: str, index: int):
    """Remove topic from queue by index."""
    entity_name = entity.capitalize()
    removed = auto_processor.topic_queue.remove(entity_name, index)
    return {"removed": removed, "queue": auto_processor.topic_queue.peek(entity_name)}


@app.delete("/auto/{entity}/queue")
async def auto_queue_clear(entity: str):
    """Clear entire topic queue for entity."""
    entity_name = entity.capitalize()
    auto_processor.topic_queue.clear(entity_name)
    return {"entity": entity_name, "cleared": True}


@app.get("/auto/{entity}/history")
async def auto_history(entity: str):
    """Get continuity context from last autonomous session."""
    entity_name = entity.capitalize()
    return {
        "entity": entity_name,
        "context": auto_processor.get_continuity_context(entity_name),
    }


# ---------------------------------------------------------------------------
# Curiosity Endpoints
# ---------------------------------------------------------------------------

@app.get("/curiosity/{entity}")
async def curiosity_list(entity: str, limit: int = 10):
    """Get active curiosities for entity."""
    entity_name = entity.capitalize()
    if entity_name not in ("Kay", "Reed"):
        return {"error": f"Unknown entity: {entity}"}
    return {
        "entity": entity_name,
        "curiosities": curiosity_manager.get_active(entity_name, limit),
    }


@app.post("/curiosity/{entity}")
async def curiosity_add(entity: str, text: str, priority: float = 0.5, source: str = "manual"):
    """Manually add a curiosity for entity."""
    entity_name = entity.capitalize()
    if entity_name not in ("Kay", "Reed"):
        return {"error": f"Unknown entity: {entity}"}
    from curiosity_engine import Curiosity
    c = Curiosity(id="", text=text, entity=entity_name, source=source, priority=priority)
    added = curiosity_manager.get_store(entity_name).add(c)
    return {"entity": entity_name, "added": added, "text": text}


@app.post("/curiosity/{entity}/dismiss/{curiosity_id}")
async def curiosity_dismiss(entity: str, curiosity_id: str):
    """Dismiss a curiosity (user doesn't want it explored)."""
    entity_name = entity.capitalize()
    ok = curiosity_manager.dismiss(entity_name, curiosity_id)
    return {"dismissed": ok, "id": curiosity_id}


@app.post("/curiosity/{entity}/boost/{curiosity_id}")
async def curiosity_boost(entity: str, curiosity_id: str):
    """Boost a curiosity's priority."""
    entity_name = entity.capitalize()
    ok = curiosity_manager.boost(entity_name, curiosity_id)
    return {"boosted": ok, "id": curiosity_id}


@app.post("/curiosity/{entity}/extract")
async def curiosity_extract_now(entity: str):
    """Force curiosity extraction from recent conversation history."""
    entity_name = entity.capitalize()
    if entity_name not in ("Kay", "Reed"):
        return {"error": f"Unknown entity: {entity}"}
    # Pull recent messages from connection manager history
    recent = []
    for msg in manager.message_history[-20:]:
        recent.append({
            "role": "user" if msg.get("sender") == "Re" else "assistant",
            "content": msg.get("content", ""),
        })
    if not recent:
        return {"entity": entity_name, "extracted": 0, "message": "No conversation history"}
    extracted = await curiosity_manager.maybe_extract(entity_name, recent)
    return {
        "entity": entity_name,
        "extracted": len(extracted),
        "curiosities": [c.to_dict() for c in extracted],
    }


# ---------------------------------------------------------------------------
# Stats & Entity Graph Endpoints
# ---------------------------------------------------------------------------

# Wrapper directory resolution
_WRAPPERS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _wrapper_dir(entity: str) -> str:
    """Resolve wrapper directory for an entity."""
    return os.path.join(_WRAPPERS_ROOT, entity.capitalize())

def _read_json_file(path: str) -> Optional[dict]:
    """Read a JSON file, return None on failure."""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.warning(f"[STATS] Could not read {path}: {e}")
    return None


@app.get("/stats/{entity}")
async def stats_overview(entity: str):
    """
    Get aggregated wrapper state: emotions, momentum, saccade, memory, performance.
    Human-readable overview for the Godot stats panel.
    """
    entity_name = entity.capitalize()
    wdir = _wrapper_dir(entity_name)

    # Read state snapshot (saved by wrapper bridge every turn)
    snapshot = _read_json_file(os.path.join(wdir, "memory", "state_snapshot.json"))
    if not snapshot:
        return {"entity": entity_name, "error": "No state snapshot available"}

    # Read saccade state if available
    saccade = _read_json_file(os.path.join(wdir, "memory", "saccade_state.json"))

    # Format emotions as readable strings
    emotions_readable = []
    raw_emotions = snapshot.get("emotions", {})
    if isinstance(raw_emotions, dict):
        for emo_name, emo_data in sorted(
            raw_emotions.items(),
            key=lambda x: x[1].get("intensity", x[1]) if isinstance(x[1], dict) else x[1],
            reverse=True
        ):
            if isinstance(emo_data, dict):
                intensity = emo_data.get("intensity", 0)
                valence = emo_data.get("valence", 0)
            else:
                intensity = emo_data
                valence = 0
            if intensity > 0.1:
                bar = "█" * int(intensity * 10)
                sign = "+" if valence > 0 else "-" if valence < 0 else "~"
                emotions_readable.append({
                    "name": emo_name,
                    "intensity": round(intensity, 2),
                    "valence": round(valence, 2),
                    "display": f"{emo_name}: {bar} ({intensity:.0%}) [{sign}]"
                })

    # Format momentum
    momentum = snapshot.get("momentum", 0)
    momentum_breakdown = snapshot.get("momentum_breakdown", {})
    momentum_display = f"Momentum: {momentum:.1f}/10"
    if momentum_breakdown:
        parts = [f"{k}: {v:.1f}" for k, v in momentum_breakdown.items() if v > 0]
        if parts:
            momentum_display += f" ({', '.join(parts)})"

    # Format memory layer stats
    memory_stats = snapshot.get("memory_layer_stats", {})
    memory_readable = []
    for layer_name, layer_data in memory_stats.items():
        if isinstance(layer_data, dict):
            count = layer_data.get("count", layer_data.get("total", 0))
            memory_readable.append({"layer": layer_name, "count": count})
        else:
            memory_readable.append({"layer": layer_name, "count": layer_data})

    # Top entities (already formatted in snapshot)
    top_entities = snapshot.get("top_entities", [])

    # Format saccade
    saccade_display = None
    if saccade:
        saccade_display = {
            "active": True,
            "last_delta": saccade.get("last_delta_summary", ""),
            "vectors": saccade.get("open_vectors", []),
            "turn": saccade.get("turn_count", 0),
        }

    return {
        "entity": entity_name,
        "emotions": emotions_readable,
        "momentum": {
            "value": momentum,
            "breakdown": momentum_breakdown,
            "display": momentum_display,
        },
        "meta_awareness": snapshot.get("meta_awareness", {}),
        "memory": memory_readable,
        "top_entities": top_entities,
        "saccade": saccade_display,
        "body": snapshot.get("body", {}),
        "social": snapshot.get("social_needs", {}),
    }


@app.get("/entities/{entity}")
async def entities_list(entity: str, top_n: int = 30):
    """
    Get top entities from the entity graph with human-readable descriptions.
    Uses the English translator to convert raw attribute data to natural language.
    """
    from entity_english import entity_to_english_summary

    entity_name = entity.capitalize()
    wdir = _wrapper_dir(entity_name)
    graph_path = os.path.join(wdir, "memory", "entity_graph.json")
    graph_data = _read_json_file(graph_path)

    if not graph_data or "entities" not in graph_data:
        return {"entity": entity_name, "error": "No entity graph available", "entities": []}

    raw_entities = graph_data["entities"]

    # Sort by importance, take top N
    sorted_names = sorted(
        raw_entities.keys(),
        key=lambda n: raw_entities[n].get("importance_score", 0),
        reverse=True
    )

    summaries = []
    for name in sorted_names[:top_n]:
        try:
            summary = entity_to_english_summary(raw_entities[name])
            summaries.append(summary)
        except Exception as e:
            log.warning(f"[STATS] Could not summarize entity {name}: {e}")
            summaries.append({"name": name, "error": str(e)})

    return {
        "entity": entity_name,
        "total_entities": len(raw_entities),
        "showing": len(summaries),
        "entities": summaries,
    }


@app.get("/entities/{entity}/{name}")
async def entity_detail(entity: str, name: str):
    """
    Get detailed view of a single entity with full English descriptions,
    relationships, recent changes, and attribute history.
    """
    from entity_english import entity_to_english_summary, relationship_to_english

    entity_name = entity.capitalize()
    wdir = _wrapper_dir(entity_name)
    graph_path = os.path.join(wdir, "memory", "entity_graph.json")
    graph_data = _read_json_file(graph_path)

    if not graph_data or "entities" not in graph_data:
        return {"error": "No entity graph available"}

    # Case-insensitive entity lookup
    raw_entities = graph_data["entities"]
    match = None
    for ename, edata in raw_entities.items():
        if ename.lower() == name.lower():
            match = edata
            break

    if not match:
        # Try aliases
        for ename, edata in raw_entities.items():
            if name.lower() in [a.lower() for a in edata.get("aliases", [])]:
                match = edata
                break

    if not match:
        return {"error": f"Entity '{name}' not found"}

    # Full summary
    summary = entity_to_english_summary(match)

    # Relationships in English (dedup + cap at 50)
    relationships_english = []
    seen_rels = set()
    raw_relationships = graph_data.get("relationships", {})
    entity_rels = match.get("relationships", [])
    for rel_id in entity_rels:
        if rel_id in seen_rels or rel_id not in raw_relationships:
            continue
        seen_rels.add(rel_id)
        rel = raw_relationships[rel_id]
        if isinstance(rel, dict):
                e1 = rel.get("entity1", "?")
                e2 = rel.get("entity2", "?")
                rtype = rel.get("relation_type", "related_to")
                english = relationship_to_english(e1, rtype, e2)
                relationships_english.append({
                    "sentence": english,
                    "type": rtype,
                    "other_entity": e2 if e1.lower() == name.lower() else e1,
                })
                if len(relationships_english) >= 50:
                    break

    summary["relationships"] = relationships_english
    return summary


@app.get("/entities/{entity}/search/{query}")
async def entity_search(entity: str, query: str, limit: int = 10):
    """
    Search entities by name or attribute value.
    """
    entity_name = entity.capitalize()
    wdir = _wrapper_dir(entity_name)
    graph_path = os.path.join(wdir, "memory", "entity_graph.json")
    graph_data = _read_json_file(graph_path)

    if not graph_data or "entities" not in graph_data:
        return {"entity": entity_name, "results": []}

    query_lower = query.lower()
    results = []

    for ename, edata in graph_data["entities"].items():
        score = 0
        # Name match
        if query_lower in ename.lower():
            score += 10
        # Alias match
        for alias in edata.get("aliases", []):
            if query_lower in alias.lower():
                score += 8
        # Attribute value match
        for attr_name, history in edata.get("attributes", {}).items():
            if history:
                latest = history[-1]
                val = str(latest[0] if isinstance(latest, list) else latest).lower()
                if query_lower in val:
                    score += 5
                if query_lower in attr_name.lower():
                    score += 3

        if score > 0:
            results.append({
                "name": ename,
                "type": edata.get("entity_type", "unknown"),
                "importance": edata.get("importance_score", 0),
                "match_score": score,
            })

    results.sort(key=lambda x: (-x["match_score"], -x["importance"]))
    return {
        "entity": entity_name,
        "query": query,
        "results": results[:limit],
    }


# ---------------------------------------------------------------------------
# Canvas Endpoints
# ---------------------------------------------------------------------------

@app.get("/canvas/{entity}")
async def canvas_get(entity: str):
    """Get current canvas state for entity (base64 PNG + metadata)."""
    entity_name = entity.capitalize()
    state = canvas_mgr.get_canvas_state(entity_name)
    if not state:
        return {"entity": entity_name, "has_canvas": False}
    return {
        "entity": entity_name,
        "has_canvas": True,
        "base64": state["base64"],
        "dimensions": state["dimensions"],
    }


@app.post("/canvas/{entity}/paint")
async def canvas_paint(entity: str, commands: list):
    """Execute paint commands on entity's canvas via REST."""
    entity_name = entity.capitalize()
    result = await canvas_mgr.execute_paint(entity_name, commands)
    return {"entity": entity_name, **result}


@app.post("/canvas/{entity}/clear")
async def canvas_clear(entity: str):
    """Clear entity's canvas."""
    entity_name = entity.capitalize()
    await canvas_mgr.clear_canvas(entity_name)
    return {"entity": entity_name, "cleared": True}


@app.get("/canvas/{entity}/history")
async def canvas_history(entity: str):
    """List saved canvas iterations for entity."""
    entity_name = entity.capitalize()
    saves = canvas_mgr.list_saves(entity_name)
    return {"entity": entity_name, "saves": saves}


# ---------------------------------------------------------------------------
# Code Execution Admin Endpoints
# ---------------------------------------------------------------------------

from code_safety import (
    EntityPermissions, ExecutionLog, ApprovalQueue, SnapshotManager,
    entity_status, set_entity_mode, grant_write, revoke_write,
    get_exec_log, get_file_access_log, approve_exec, deny_exec,
    approve_all_pending, revert_exec, list_snapshots,
)
from code_executor import execute_approved


@app.get("/exec/{entity}/status")
async def exec_status(entity: str):
    """Full code execution status for entity."""
    entity_name = entity.capitalize()
    perms = EntityPermissions(entity_name)
    exec_log = ExecutionLog(entity_name)
    queue = ApprovalQueue(entity_name)
    snaps = SnapshotManager(entity_name)
    return {
        "entity": entity_name,
        "mode": perms.mode,
        "allowed_write_paths": perms.allowed_write_paths,
        "blocked_patterns": perms.config.get("blocked_patterns", []),
        "pending": queue.get_pending(),
        "recent_executions": exec_log.get_recent(10),
        "snapshot_count": len(snaps.list_snapshots()),
    }


@app.get("/exec/{entity}/pending")
async def exec_pending(entity: str):
    """Get pending approval queue."""
    entity_name = entity.capitalize()
    queue = ApprovalQueue(entity_name)
    return {"entity": entity_name, "pending": queue.get_pending()}


@app.post("/exec/{entity}/approve/{exec_id}")
async def exec_approve_endpoint(entity: str, exec_id: str):
    """Approve a queued execution."""
    entity_name = entity.capitalize()
    result = approve_exec(entity_name, exec_id)
    return {"entity": entity_name, "exec_id": exec_id, "result": result}


@app.post("/exec/{entity}/deny/{exec_id}")
async def exec_deny_endpoint(entity: str, exec_id: str, reason: str = ""):
    """Deny a queued execution."""
    entity_name = entity.capitalize()
    result = deny_exec(entity_name, exec_id, reason)
    return {"entity": entity_name, "exec_id": exec_id, "result": result}


@app.post("/exec/{entity}/approve-all")
async def exec_approve_all_endpoint(entity: str):
    """Approve all pending for entity."""
    entity_name = entity.capitalize()
    result = approve_all_pending(entity_name)
    return {"entity": entity_name, "result": result}


@app.post("/exec/{entity}/run/{exec_id}")
async def exec_run_approved(entity: str, exec_id: str):
    """Execute an approved queued item."""
    entity_name = entity.capitalize()
    result = await execute_approved(entity_name, exec_id)
    return {"entity": entity_name, **result}


@app.post("/exec/{entity}/mode/{mode}")
async def exec_set_mode(entity: str, mode: str):
    """Set entity mode: supervised or autonomous."""
    entity_name = entity.capitalize()
    if mode not in ("supervised", "autonomous"):
        return {"error": f"Invalid mode: {mode}. Use 'supervised' or 'autonomous'."}
    result = set_entity_mode(entity_name, mode)
    return {"entity": entity_name, "mode": mode, "result": result}


@app.post("/exec/{entity}/grant")
async def exec_grant_write(entity: str, path: str):
    """Grant write access to a path."""
    entity_name = entity.capitalize()
    result = grant_write(entity_name, path)
    return {"entity": entity_name, "path": path, "result": result}


@app.post("/exec/{entity}/revoke")
async def exec_revoke_write(entity: str, path: str):
    """Revoke write access to a path."""
    entity_name = entity.capitalize()
    result = revoke_write(entity_name, path)
    return {"entity": entity_name, "path": path, "result": result}


@app.get("/exec/{entity}/log")
async def exec_log_endpoint(entity: str, n: int = 20):
    """Get execution log."""
    entity_name = entity.capitalize()
    log_obj = ExecutionLog(entity_name)
    return {"entity": entity_name, "entries": log_obj.get_recent(n)}


@app.get("/exec/{entity}/access-log")
async def exec_access_log(entity: str, n: int = 50):
    """Get file access log (writes + blocked attempts)."""
    entity_name = entity.capitalize()
    return {"entity": entity_name, "entries": get_file_access_log(entity_name, n)}


@app.get("/exec/{entity}/snapshots")
async def exec_snapshots(entity: str):
    """List available snapshots."""
    entity_name = entity.capitalize()
    return {"entity": entity_name, "snapshots": list_snapshots(entity_name)}


@app.post("/exec/{entity}/revert/{exec_id}")
async def exec_revert(entity: str, exec_id: str):
    """Revert scratch to a snapshot."""
    entity_name = entity.capitalize()
    result = revert_exec(entity_name, exec_id)
    return {"entity": entity_name, "exec_id": exec_id, **result}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description="Nexus Chat Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    uvicorn.run(
        app, host=args.host, port=args.port, log_level="info",
        ws_ping_interval=120, ws_ping_timeout=300
    )
