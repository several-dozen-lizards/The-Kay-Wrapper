"""
Nexus Kay Client (v2)
Kay wrapper + ConversationPacer = organic chat behavior.

Usage:
  python nexus_kay.py [--server ws://localhost:8765]
"""

import asyncio
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.client_ai import NexusAIClient
from nexus.conversation_pacer import (
    KAY_PACING, NEXUS_PACING_PROMPT,
    ResponseDecider, ResponseDecision,
    split_into_bursts, thinking_delay, typing_delay, burst_delay
)
from wrapper_bridge import WrapperBridge

log = logging.getLogger("nexus.kay")


class KayNexusClient(NexusAIClient):
    """Kay wrapper connected to Nexus with organic conversation pacing."""
    
    def __init__(self, server_url="ws://localhost:8765"):
        super().__init__(
            name="Kay",
            server_url=server_url,
            participant_type="ai_wrapper"
        )
        self.bridge: WrapperBridge = None
        self.config = KAY_PACING
        self.decider = ResponseDecider("Kay", self.config)
        self._processing = False
        self._idle_task = None
    
    async def on_connect(self):
        """Initialize wrapper bridge on connection."""
        await super().on_connect()
        
        if not self.bridge:
            log.info("Initializing WrapperBridge...")
            wrapper_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.bridge = WrapperBridge(entity_name="Kay", wrapper_dir=wrapper_dir)
            await self.bridge.startup()
            log.info("WrapperBridge ready.")
        
        await self.send_emote("enters the Nexus")
        
        # Start idle loop (for organic conversation initiation)
        if self._idle_task is None or self._idle_task.done():
            self._idle_task = asyncio.create_task(self._idle_loop())
    
    async def on_message(self, message: dict):
        """Route incoming messages through pacer + wrapper pipeline."""
        sender = message.get("sender", "?")
        content = message.get("content", "")
        msg_type = message.get("msg_type", "chat")
        
        # Track other speakers for response decisions
        self.decider.record_other(sender)
        
        # Only process chat/whisper
        if msg_type not in ("chat", "whisper"):
            return
        
        # Skip if already processing
        if self._processing:
            log.debug(f"Already processing, queuing awareness of {sender}'s message")
            return
        
        # --- RESPONSE DECISION ---
        decision = self.decider.decide(message, self._participants)
        log.info(f"Decision for '{content[:50]}...' from {sender}: {decision.value}")
        
        if decision == ResponseDecision.LISTEN:
            return
        
        self._processing = True
        try:
            # Thinking pause (natural delay before responding)
            await self.set_status("thinking")
            await thinking_delay(self.config, len(content))
            
            if decision == ResponseDecision.REACT:
                # Quick reaction only
                reply = await self._generate_reaction(content, sender)
                await self._send_burst(reply)
            else:
                # Full response through wrapper
                reply = await self._generate_response(content, sender)
                bursts = split_into_bursts(reply, self.config)
                
                for i, burst_text in enumerate(bursts):
                    if i > 0:
                        await burst_delay(self.config)
                    await self._send_burst(burst_text)
            
            self.decider.record_sent()
            await self.set_status("online")
            
        except Exception as e:
            log.error(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
            await self.set_status("online")
        finally:
            self._processing = False
    
    async def _generate_response(self, content: str, sender: str) -> str:
        """Get response from wrapper with Nexus pacing context."""
        # Inject nexus context into the message
        nexus_context = f"[Nexus chat - {sender} says]: {content}"
        
        # Check for wrapper commands first
        handled, cmd_response = self.bridge.process_command(content)
        if handled and cmd_response:
            return cmd_response
        
        # Full wrapper pipeline with nexus pacing prompt appended
        reply = await self.bridge.process_message(
            nexus_context,
            source="nexus",
            extra_system_context=NEXUS_PACING_PROMPT
        )
        return reply
    
    async def _generate_reaction(self, content: str, sender: str) -> str:
        """Generate a quick reaction (emote or short acknowledgment)."""
        # For now, use the wrapper with a strong brevity instruction
        reaction_prompt = (
            f"[Nexus: React VERY briefly to what {sender} just said. "
            f"One short sentence, emote, or reaction. No more.]\n"
            f"{sender}: {content}"
        )
        reply = await self.bridge.process_message(
            reaction_prompt,
            source="nexus",
            extra_system_context=NEXUS_PACING_PROMPT
        )
        # Truncate if the model still gave too much
        if len(reply) > 150:
            first_sentence = reply.split('.')[0] + '.'
            return first_sentence
        return reply
    
    async def _send_burst(self, text: str):
        """Send a message with typing simulation."""
        await self.set_status("typing")
        await typing_delay(text, self.config)
        
        # Detect if it's an emote
        if text.startswith("*") and text.endswith("*"):
            await self.send_emote(text[1:-1])
        else:
            await self.send_chat(text)
    
    async def _idle_loop(self):
        """Periodically check if Kay wants to say something unprompted."""
        while self._running:
            await asyncio.sleep(self.config.idle_check_interval)
            
            if self._processing:
                continue
            
            # Small chance of organic initiation
            import random
            if random.random() < self.config.idle_initiation_chance:
                log.info("Kay initiating organic conversation")
                # TODO: Ask wrapper what's on Kay's mind
                # For now this is a placeholder
                pass
    
    async def on_disconnect(self):
        """Clean shutdown."""
        if self._idle_task:
            self._idle_task.cancel()
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
    
    parser = argparse.ArgumentParser(description="Kay Nexus Client")
    parser.add_argument("--server", "-s", default="ws://localhost:8765")
    args = parser.parse_args()
    
    client = KayNexusClient(server_url=args.server)
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nKay disconnecting from Nexus.")
