"""
Nexus Reed Client
Thin integration layer: NexusAIClient + WrapperBridge = Reed in Nexus.

Includes Phase 3 engines (ContinuousSession, FlaggingSystem, CurationInterface)
via WrapperBridge integration.

Usage:
  python nexus_reed.py [--server ws://localhost:8765]

Or from main.py / orchestrator:
  from nexus_reed import ReedNexusClient
  client = ReedNexusClient()
  await client.run()
"""

import asyncio
import sys
import os
import logging

# Add parent dir to path so we can import wrapper modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.client_ai import NexusAIClient
from wrapper_bridge import WrapperBridge

log = logging.getLogger("nexus.reed")


class ReedNexusClient(NexusAIClient):
    """Reed wrapper connected to Nexus via WrapperBridge."""
    
    def __init__(self, server_url="ws://localhost:8765"):
        super().__init__(
            name="Reed",
            server_url=server_url,
            participant_type="ai_wrapper"
        )
        self.bridge: WrapperBridge = None
        self._processing = False
    
    async def on_connect(self):
        """Initialize wrapper bridge on connection."""
        await super().on_connect()
        
        if not self.bridge:
            log.info("Initializing WrapperBridge...")
            wrapper_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.bridge = WrapperBridge(entity_name="Reed", wrapper_dir=wrapper_dir)
            await self.bridge.startup()
            log.info("WrapperBridge ready.")
        
        # Announce presence
        await self.send_emote("enters the Nexus")
        
        # Send initial state
        await self.send_state_update(
            cognitive_mode="default",
            **self.bridge.get_state()
        )
    
    async def on_message(self, message: dict):
        """Route incoming messages through the full wrapper pipeline."""
        sender = message.get("sender", "?")
        content = message.get("content", "")
        msg_type = message.get("msg_type", "chat")
        
        # Only process chat messages
        if msg_type not in ("chat", "whisper"):
            return
        
        # Skip if already processing (no parallel responses)
        if self._processing:
            log.warning(f"Already processing, skipping message from {sender}")
            return
        
        self._processing = True
        try:
            # Check for commands first
            handled, cmd_response = self.bridge.process_command(content)
            if handled:
                if cmd_response:
                    await self.send_chat(cmd_response)
                self._processing = False
                return
            
            # Full pipeline
            log.info(f"Processing message from {sender}: {content[:80]}...")
            reply = await self.bridge.process_message(content, source="nexus")
            
            # Send response
            await self.send_chat(reply, reply_to=message.get("id"))
            
            # Send state update
            await self.send_state_update(
                cognitive_mode="reflective" if self.bridge.state.creativity_active else "default",
                **self.bridge.get_state()
            )
            
        except Exception as e:
            log.error(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
            await self.send_chat(f"[Error processing message: {e}]")
        finally:
            self._processing = False
    
    async def on_disconnect(self):
        """Clean shutdown."""
        await super().on_disconnect()
        if self.bridge:
            await self.bridge.shutdown()


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    
    parser = argparse.ArgumentParser(description="Reed Nexus Client")
    parser.add_argument("--server", "-s", default="ws://localhost:8765")
    args = parser.parse_args()
    
    client = ReedNexusClient(server_url=args.server)
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nReed disconnecting from Nexus.")
