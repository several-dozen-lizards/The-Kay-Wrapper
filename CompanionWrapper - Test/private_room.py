"""
Private Room Server
Lightweight WebSocket server for 1:1 conversations between the user and an AI entity.

Each wrapper process runs one of these alongside its Nexus client.
The private room is independent of the Nexus - messages stay here.

Protocol:
  Client → Server:
    {"type": "chat", "content": "hello"}
    {"type": "command", "command": "warmup"}
    {"type": "command", "command": "set_affect", "value": 4.0}
  
  Server → Client:
    {"type": "chat", "sender": "other_entity", "content": "hey"}
    {"type": "emote", "sender": "other_entity", "content": "coils closer"}
    {"type": "status", "status": "thinking"}
    {"type": "system", "content": "Connected to the room"}
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Callable, Awaitable

try:
    import websockets
    from websockets.server import serve
except ImportError:
    import subprocess, sys
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "websockets", "--break-system-packages", "-q"
    ])
    import websockets
    from websockets.server import serve

log = logging.getLogger("private_room")


class PrivateRoom:
    """
    WebSocket server for private 1:1 conversation.
    
    The wrapper subclass provides callbacks:
      on_private_message(content: str) -> str   -- generate a response
      on_private_command(data: dict) -> None     -- handle commands
    """
    
    def __init__(
        self,
        entity_name: str,
        port: int,
        host: str = "localhost",
        on_message: Callable[[str], Awaitable[str]] = None,
        on_command: Callable[[dict], Awaitable[None]] = None,
    ):
        self.entity_name = entity_name
        self.port = port
        self.host = host
        self._on_message = on_message
        self._on_command = on_command
        self._client: Optional[websockets.WebSocketServerProtocol] = None
        self._server = None
        self._running = False
        self._history_provider: Optional[Callable[[], list[dict]]] = None

        # Log batching (50ms window to prevent flooding)
        self._log_buffer: list[dict] = []
        self._flush_task: Optional[asyncio.Task] = None
    
    def set_history_provider(self, provider: Callable[[], list[dict]]):
        """Set a callback that returns recent messages for history replay."""
        self._history_provider = provider
    
    @property
    def has_client(self) -> bool:
        return self._client is not None
    
    # ------------------------------------------------------------------
    # Sending to the connected UI client
    # ------------------------------------------------------------------
    
    async def send_chat(self, text: str):
        """Send a chat message to the UI."""
        await self._send({"type": "chat", "sender": self.entity_name, "content": text})
    
    async def send_emote(self, text: str):
        """Send an emote to the UI."""
        await self._send({"type": "emote", "sender": self.entity_name, "content": text})
    
    async def send_status(self, status: str):
        """Send a status update (thinking, typing, online, etc.)."""
        await self._send({"type": "status", "status": status})
    
    async def send_system(self, text: str):
        """Send a system message to the UI."""
        await self._send({"type": "system", "content": text})

    async def send_log(self, data: dict):
        """Queue a log entry for batched broadcast to UI."""
        self._log_buffer.append(data)
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_logs())

    async def _flush_logs(self):
        """Wait briefly then send all queued logs as a batch."""
        await asyncio.sleep(0.5)  # 500ms batch window to prevent flooding
        if self._log_buffer:
            batch = self._log_buffer[:50]
            self._log_buffer = self._log_buffer[50:]
            await self._send({"type": "log_batch", "logs": batch})
            # Continue flushing if more logs queued
            if self._log_buffer:
                self._flush_task = asyncio.create_task(self._flush_logs())
    
    @staticmethod
    def _sanitize_str(s: str) -> str:
        """Strip surrogates and other bytes that break Godot's JSON parser."""
        # Encode with surrogateescape to catch lone surrogates, then decode
        # with replace to turn them into safe replacement characters
        return s.encode('utf-8', errors='surrogateescape') \
                .decode('utf-8', errors='replace')

    @classmethod
    def _sanitize(cls, obj):
        """Recursively sanitize all strings in a dict/list for safe WebSocket JSON."""
        if isinstance(obj, str):
            return cls._sanitize_str(obj)
        if isinstance(obj, dict):
            return {cls._sanitize(k): cls._sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [cls._sanitize(v) for v in obj]
        return obj

    async def _send(self, data: dict):
        """Send JSON to connected client, if any."""
        if self._client:
            try:
                safe = self._sanitize(data)
                await self._client.send(json.dumps(safe, ensure_ascii=True))
            except websockets.ConnectionClosed:
                log.info(f"Client disconnected from {self.entity_name}'s room")
                self._client = None
            except Exception as e:
                log.error(f"Send error: {e}")
    
    async def _replay_history(self):
        """Send recent messages to the UI so it has context on reconnect."""
        if not self._history_provider:
            return
        try:
            messages = self._history_provider()
            if not messages:
                return
            # Send as a batch so UI knows it's history, not live
            await self._send({
                "type": "history",
                "messages": messages
            })
            log.info(f"Replayed {len(messages)} messages to UI")
        except Exception as e:
            log.error(f"History replay error: {e}")
    
    # ------------------------------------------------------------------
    # WebSocket server
    # ------------------------------------------------------------------
    
    async def _handle_connection(self, websocket):
        """Handle a single client connection."""
        # Only one client at a time (the user)
        if self._client is not None:
            try:
                old = self._client
                self._client = None
                await old.close()
            except:
                pass
        
        self._client = websocket
        remote = websocket.remote_address
        log.info(f"{self.entity_name}'s room: client connected from {remote}")
        
        await self.send_system(f"Connected to {self.entity_name}'s room — private mode")
        
        # Replay recent history so UI has context
        await self._replay_history()
        
        await self.send_status("online")
        
        try:
            async for raw in websocket:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                
                msg_type = data.get("type", "")
                
                if msg_type == "chat":
                    content = data.get("content", "").strip()
                    if content and self._on_message:
                        # Process in background so we don't block the WS
                        asyncio.create_task(
                            self._handle_chat(content)
                        )
                
                elif msg_type == "command":
                    if self._on_command:
                        asyncio.create_task(
                            self._on_command(data)
                        )
                
                elif msg_type == "ping":
                    await self._send({"type": "pong"})
        
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            log.error(f"Connection error: {e}")
        finally:
            if self._client == websocket:
                self._client = None
            log.info(f"{self.entity_name}'s room: client disconnected")
    
    async def _handle_chat(self, content: str):
        """Process a chat message and send response."""
        try:
            reply = await self._on_message(content)
            if reply:
                await self.send_chat(reply)
        except Exception as e:
            log.error(f"Message handling error: {e}")
            await self.send_system(f"Error: {e}")
        finally:
            await self.send_status("online")
    
    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    
    async def start(self):
        """Start the private room server."""
        self._running = True
        self._server = await serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=120,
            ping_timeout=300,
        )
        log.info(f"{self.entity_name}'s room listening on ws://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the server."""
        self._running = False
        if self._client:
            try:
                await self._client.close()
            except:
                pass
            self._client = None
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            log.info(f"{self.entity_name}'s room closed")
