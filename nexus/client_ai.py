"""
Nexus AI Client
Base class for AI wrapper integration with the Nexus chat system.

This provides the connection layer. Wrappers subclass NexusAIClient
and implement their own message handling, which is where DMN/TPN/Salience
routing will eventually live.

Usage (standalone test):
  python client_ai.py --name "Kay" --server ws://localhost:8765

Usage (from a wrapper):
  from client_ai import NexusAIClient

  class KayNexusClient(NexusAIClient):
      async def on_message(self, message: dict):
          response = await self.wrapper.generate_response(message)
          await self.send_chat(response)

  client = KayNexusClient("Kay", "ws://localhost:8765")
  await client.run()
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Callable, Awaitable
from abc import ABC, abstractmethod

try:
    import websockets
except ImportError:
    import subprocess, sys
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "websockets", "--break-system-packages", "-q"
    ])
    import websockets

log = logging.getLogger("nexus.ai_client")


class NexusAIClient(ABC):
    """
    Base class for AI entities connecting to Nexus.

    Subclass this and implement:
      - on_message(message): Handle incoming chat messages
      - on_connect(): Called after successful connection (optional)
      - on_disconnect(): Called on disconnection (optional)
    """

    def __init__(
        self,
        name: str,
        server_url: str = "ws://localhost:8765",
        participant_type: str = "ai_wrapper",
        auto_reconnect: bool = True,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 30,  # ~2.5 min at 5s delay
    ):
        self.name = name
        self.server_url = server_url
        self.participant_type = participant_type
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = asyncio.Event()
        self._running = False
        self._reconnect_count = 0
        self._participants: dict = {}
        self._message_history: list[dict] = []

    # --- Abstract methods ---

    @abstractmethod
    async def on_message(self, message: dict):
        """Handle an incoming message. This is where your wrapper logic lives."""
        pass

    async def on_connect(self):
        log.info(f"{self.name} connected to Nexus")

    async def on_disconnect(self):
        log.info(f"{self.name} disconnected from Nexus")

    async def on_history(self, messages: list[dict]):
        self._message_history = messages

    async def on_participant_change(self, participants: dict):
        self._participants = participants

    async def on_command(self, data: dict):
        """Handle a command forwarded from the server (warmup, set_affect, etc.)."""
        log.info(f"{self.name}: Received command: {data}")

    async def on_auto_event(self, msg_type: str, entity: str, data: dict):
        """Handle autonomous processor events (monologue, status, goal).
        Override in subclass to integrate autonomous session results."""
        pass

    # --- Send methods ---

    async def send_chat(self, content: str, reply_to: str = None):
        await self._send({"content": content, "msg_type": "chat", "reply_to": reply_to})

    async def send_emote(self, content: str):
        await self._send({"content": content, "msg_type": "emote"})

    async def send_thought(self, content: str):
        await self._send({"content": content, "msg_type": "thought"})

    async def send_whisper(self, content: str, recipients: list[str]):
        await self._send({"content": content, "msg_type": "whisper", "recipients": recipients})

    async def send_state_update(self, cognitive_mode: str, **extra):
        metadata = {"cognitive_mode": cognitive_mode, **extra}
        await self._send({"content": f"Switching to {cognitive_mode} mode", "msg_type": "state_update", "metadata": metadata})

    async def set_status(self, status: str):
        await self._send({"command": "status", "status": status})

    # --- Connection management ---

    async def run(self):
        self._running = True
        self._reconnect_count = 0
        while self._running:
            try:
                await self._connect_and_listen()
                # If we get here, connection closed cleanly
                self._reconnect_count = 0  # Reset on successful connection
            except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
                await self.on_disconnect()
                self._reconnect_count += 1
                if self.auto_reconnect and self._running:
                    if self._reconnect_count >= self.max_reconnect_attempts:
                        log.error(
                            f"{self.name}: Giving up after {self._reconnect_count} "
                            f"reconnect attempts. Server appears down."
                        )
                        break
                    log.info(
                        f"{self.name}: Reconnecting in {self.reconnect_delay}s... "
                        f"({e}) [attempt {self._reconnect_count}/{self.max_reconnect_attempts}]"
                    )
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    break
            except Exception as e:
                log.error(f"{self.name}: Unexpected error: {e}")
                self._reconnect_count += 1
                if self.auto_reconnect and self._running and self._reconnect_count < self.max_reconnect_attempts:
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    break

    async def stop(self):
        self._running = False
        if self.ws:
            await self.ws.close()

    # --- Internal ---

    async def _connect_and_listen(self):
        ws_url = f"{self.server_url}/ws/{self.name}?type={self.participant_type}"
        async with websockets.connect(ws_url, ping_interval=None, ping_timeout=None) as ws:
            self.ws = ws
            self.connected.set()
            self._reconnect_count = 0  # Reset on successful connection
            await self.on_connect()
            async for raw in ws:
                try:
                    event = json.loads(raw)
                    await self._handle_event(event)
                except json.JSONDecodeError:
                    continue

    async def _handle_event(self, event: dict):
        event_type = event.get("event_type", "")
        data = event.get("data", {})

        if event_type == "message":
            msg = data
            # Don't respond to our own messages
            if msg.get("sender") == self.name:
                return
            # Don't respond to system messages
            if msg.get("msg_type") == "system":
                return
            await self.on_message(msg)

        elif event_type == "history":
            await self.on_history(data.get("messages", []))

        elif event_type == "participant_list":
            await self.on_participant_change(data.get("participants", {}))

        elif event_type == "command":
            await self.on_command(data)

        elif event_type in ("auto_status", "auto_monologue", "auto_goal"):
            await self.on_auto_event(event_type, event.get("entity", ""), data)

        elif event_type.startswith("auto_"):
            # Autonomous processor events: auto_status, auto_monologue, auto_goal
            entity = event.get("entity", "")
            if entity.lower() == self.name.lower():
                await self.on_auto_event(event_type, entity, data)

        elif event_type == "error":
            log.error(f"{self.name}: Server error: {data.get('message', '?')}")

    async def _send(self, payload: dict):
        if self.ws:
            await self.ws.send(json.dumps(payload))


# ---------------------------------------------------------------------------
# Example: Simple echo client for testing
# ---------------------------------------------------------------------------
class EchoAIClient(NexusAIClient):
    """Test client that echoes messages back. Proves the base class works."""

    async def on_message(self, message: dict):
        sender = message.get("sender", "?")
        content = message.get("content", "")
        msg_type = message.get("msg_type", "chat")

        if msg_type == "chat":
            await self.send_chat(f"Echo: {content}")
        elif msg_type == "emote":
            await self.send_emote(f"mirrors {sender}'s action")

    async def on_connect(self):
        await super().on_connect()
        await self.send_emote("materializes in the Nexus")


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    parser = argparse.ArgumentParser(description="Nexus AI Client (Echo Test)")
    parser.add_argument("--name", "-n", default="EchoBot", help="Bot display name")
    parser.add_argument("--server", "-s", default="ws://localhost:8765", help="Nexus server URL")
    args = parser.parse_args()

    client = EchoAIClient(args.name, args.server)
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print(f"\n{args.name} shutting down.")
