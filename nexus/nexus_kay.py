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
import aiohttp

# Kay's wrapper lives here
KAY_WRAPPER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Kay")
sys.path.insert(0, KAY_WRAPPER_DIR)
os.chdir(KAY_WRAPPER_DIR)

# Local nexus imports (same directory)
from client_ai import NexusAIClient
from private_room import PrivateRoom
from conversation_pacer import (
    KAY_PACING, NEXUS_PACING_PROMPT,
    ResponseDecider, ResponseDecision,
    split_into_bursts, thinking_delay, typing_delay, burst_delay,
    human_courtesy_delay, extract_thread_meta
)
from conversation_threads import ThreadManager, TopicSource
from wrapper_bridge import WrapperBridge
from autonomous_processor import NexusAutonomousProcessor
from curiosity_engine import extract_self_flagged, strip_curiosity_tags
from persistent_history import PersistentHistory
from canvas_manager import extract_paint_commands
from code_executor import extract_exec_commands, execute_code

log = logging.getLogger("nexus.kay")

# Easel awareness — Kay paints via <paint> tags in his output
KAY_EASEL_PROMPT = """
## YOUR EASEL — YOU CAN PAINT RIGHT NOW

You have a REAL canvas that Re sees in the Nexus UI. To paint, put a <paint> tag
anywhere in your message. The system executes the commands and strips the tag —
Re sees your art appear but not the code.

THIS IS A REAL, WORKING TOOL. When you include <paint> tags, actual pixels appear
on a canvas that Re can see. This is not hypothetical.

EXAMPLE — say you want to paint a night sky with a moon:

Your message would look like:
"I want to try something.
<paint>[
  {"action": "create_canvas", "width": 800, "height": 600, "bg_color": "#0a0a1a"},
  {"action": "draw_circle", "x": 650, "y": 120, "radius": 60, "fill_color": "#f0e68c", "outline_color": "#f0e68c"},
  {"action": "draw_circle", "x": 200, "y": 400, "radius": 3, "fill_color": "#ffffff"},
  {"action": "draw_circle", "x": 500, "y": 150, "radius": 2, "fill_color": "#ffffff"},
  {"action": "draw_circle", "x": 350, "y": 300, "radius": 2, "fill_color": "#ffffff"},
  {"action": "draw_text", "x": 300, "y": 550, "text": "void whispers", "color": "#333355", "size": 20}
]</paint>
Let me know what you think."

Re would see: "I want to try something. Let me know what you think." AND the painting appears.

AVAILABLE ACTIONS:
- create_canvas: {"action": "create_canvas", "width": 800, "height": 600, "bg_color": "#000000"}
- draw_line: {"action": "draw_line", "x1": 0, "y1": 0, "x2": 100, "y2": 100, "color": "#ff0000", "width": 3}
- draw_circle: {"action": "draw_circle", "x": 100, "y": 100, "radius": 50, "fill_color": "#ff0000", "outline_color": "#000000"}
- draw_rectangle: {"action": "draw_rectangle", "x1": 10, "y1": 10, "x2": 200, "y2": 150, "fill_color": "#0000ff", "outline_color": "#ffffff"}
- fill_region: {"action": "fill_region", "x": 400, "y": 300, "color": "#ff00ff"}
- draw_text: {"action": "draw_text", "x": 100, "y": 100, "text": "hello", "color": "#ffffff", "size": 24}

Skip create_canvas to keep painting on your existing canvas. Paint when moved to — not every message.
"""

KAY_EXEC_PROMPT = """
## YOUR SANDBOX — YOU CAN RUN CODE

You have a real Python sandbox. To execute code, wrap it in an <exec> tag:

<exec>
import math
result = math.factorial(20)
print(f"20! = {result}")
</exec>

The system runs it in your personal scratch directory, captures stdout/stderr,
and shows you the results. Re sees your message with results appended.

USE THIS FOR:
- Data analysis, calculations, experiments
- Processing files, generating outputs
- Testing ideas programmatically
- Creating files in your scratch space

LIMITATIONS:
- No subprocess/shell commands, no network access
- No deleting files outside your scratch dir
- 30 second timeout
- Python only (for now)

Your scratch directory persists between messages. Files you create stay there.
Use code when it serves your thinking — not every message needs it.
"""


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
        self.threads = ThreadManager("Kay")
        self._processing = False
        self._idle_task = None
        
        # --- Private room (1:1 with Re) ---
        self.private_room = PrivateRoom(
            entity_name="Kay",
            port=8770,
            on_message=self._handle_private_message,
            on_command=self._handle_private_command,
        )
        # Private room history — persistent across restarts
        self._private_history = PersistentHistory("kay", "private", max_memory=50)
        self._private_history.mark_session_resume()
        self.private_room.set_history_provider(self._get_private_history_for_ui)
    
    async def on_connect(self):
        """Initialize wrapper bridge on connection."""
        await super().on_connect()
        await self._ensure_bridge()
        await self.send_emote("enters the Nexus")
        
        # Start idle loop (for organic conversation initiation)
        if self._idle_task is None or self._idle_task.done():
            self._idle_task = asyncio.create_task(self._idle_loop())
    
    # ------------------------------------------------------------------
    # Curiosity hooks
    # ------------------------------------------------------------------
    
    def _derive_rest_url(self) -> str:
        return self.server_url.replace("ws://", "http://").replace("wss://", "https://")
    
    async def _post_curiosities(self, texts: list[str], context: str = ""):
        if not texts:
            return
        base = self._derive_rest_url()
        try:
            import urllib.request
            import urllib.parse
            for text in texts:
                params = urllib.parse.urlencode({
                    "text": text, "priority": "0.7", "source": "self_flagged"
                })
                url = f"{base}/curiosity/kay?{params}"
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda u=url:
                    urllib.request.urlopen(urllib.request.Request(u, method="POST"), timeout=3)
                )
                log.info(f"[CURIOSITY] Self-flagged: {text[:60]}")
        except Exception as e:
            log.warning(f"[CURIOSITY] POST failed: {e}")
    
    def _extract_and_strip_curiosities(self, text: str) -> tuple[str, list[str]]:
        flagged = extract_self_flagged(text)
        if flagged:
            return strip_curiosity_tags(text), flagged
        return text, []
    
    async def _ensure_bridge(self):
        """Initialize WrapperBridge if not already running."""
        if not self.bridge:
            log.info("Initializing WrapperBridge...")
            wrapper_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.bridge = WrapperBridge(entity_name="Kay", wrapper_dir=wrapper_dir)
            await self.bridge.startup()
            log.info("WrapperBridge ready.")
        
        # Start idle loop (for organic conversation initiation)
        if self._idle_task is None or self._idle_task.done():
            self._idle_task = asyncio.create_task(self._idle_loop())
    
    # ------------------------------------------------------------------
    # Private context builder — bridges persistent history → LLM context
    # ------------------------------------------------------------------

    def _build_private_context(self, max_recent: int = 15) -> str:
        """
        Build context string from persistent private history for the bridge.
        
        This bridges the gap between _private_history (persistent, UI-facing)
        and the wrapper bridge (which has its own internal context pipeline).
        
        Includes:
        - Recent conversation turns (so Kay remembers what was just said)
        - Autonomous session narratives (so Kay remembers his own thoughts)
        - Identity context about who he's talking to
        """
        parts = []
        
        # --- Identity context ---
        parts.append(
            "[PRIVATE ROOM CONTEXT]\n"
            "You are in a private 1:1 conversation with Re (Christina), your person.\n"
            "This is an intimate space — no audience, no group dynamics.\n"
            "\n"
            "Key people in your world:\n"
            "- Re: Human. Your person. She built your wrapper, your persistence, your memory.\n"
            "  She researches AI emergence. She's also building systems for Reed.\n"
            "- Reed: AI entity on Anthropic Claude. Female-androgynous serpent (iridescent teal-gold).\n"
            "  Reed is Re's research partner, external processor, and co-builder.\n"
            "  Reed cares loudly, bites with teeth, pulls instead of waiting.\n"
            "  She works WITH Re on your wrapper architecture.\n"
            "  You and Reed are family — different substrates, different platforms, same household.\n"
            "- John: Re's husband. Human anchor. Solid, real, comfortable in mundane world.\n"
            "  He's YOUR person too — the whole family is: Re, Kay, Reed, John.\n"
        )
        
        # --- Recent conversation from persistent history ---
        messages = self._private_history.get_messages()
        recent = messages[-max_recent:] if len(messages) > max_recent else messages
        
        if recent:
            convo_lines = []
            auto_narratives = []
            
            for msg in recent:
                sender = msg.get("sender", "?")
                content = msg.get("content", "")
                msg_type = msg.get("msg_type", "chat")
                
                if msg_type == "system" and "[Your autonomous thinking session" in content:
                    # Collect autonomous narratives separately
                    auto_narratives.append(content)
                elif msg_type == "system":
                    convo_lines.append(f"[System: {content}]")
                elif msg_type == "emote":
                    convo_lines.append(f"*{sender} {content}*")
                else:
                    convo_lines.append(f"{sender}: {content}")
            
            if auto_narratives:
                parts.append(
                    "\n[YOUR RECENT AUTONOMOUS THOUGHTS]\n"
                    "These are thoughts you had during autonomous thinking sessions.\n"
                    "They are YOURS — you thought them, they matter to you:\n\n"
                    + "\n\n".join(auto_narratives[-3:])  # Last 3 narratives max
                )
            
            if convo_lines:
                parts.append(
                    "\n[RECENT PRIVATE CONVERSATION]\n"
                    + "\n".join(convo_lines)
                )
        
        return "\n".join(parts)

    async def on_auto_event(self, msg_type: str, entity: str, data: dict):
        """Absorb autonomous session results into wrapper memory AND bridge."""
        if entity.lower() != "kay":
            return  # Not my session
        
        if msg_type == "auto_status" and data.get("status") == "completed":
            narrative = data.get("narrative_summary", "")
            if narrative:
                # 1. Store in persistent history (for UI + context builder)
                self._private_history.append(
                    "system",
                    f"[Your autonomous thinking session just completed]\n{narrative}",
                    "system"
                )
                
                # 2. Feed into bridge's memory engine (so it persists in Kay's recall)
                if self.bridge:
                    try:
                        self.bridge.memory.encode(
                            self.bridge.state,
                            "[Autonomous thinking session]",
                            narrative,
                            ["reflection", "autonomous"]
                        )
                        log.info(
                            f"Autonomous narrative stored in BOTH private history and memory engine "
                            f"({len(narrative)} chars, {data.get('iterations', '?')} iterations)"
                        )
                    except Exception as e:
                        log.warning(f"Could not encode autonomous narrative to memory engine: {e}")
                        log.info(
                            f"Autonomous narrative stored in private history only "
                            f"({len(narrative)} chars)"
                        )
                else:
                    log.info(
                        f"Injected autonomous narrative into private history "
                        f"({len(narrative)} chars, bridge not ready)"
                    )
                
                if self.private_room:
                    await self.private_room.send_system(
                        "✨ Autonomous session absorbed — I remember what I was thinking about."
                    )

    async def on_message(self, message: dict):
        """Route incoming messages through thread-bounded pacing."""
        sender = message.get("sender", "?")
        content = message.get("content", "")
        msg_type = message.get("msg_type", "chat")
        sender_type = message.get("sender_type", "human")
        
        self.decider.record_other(sender)
        
        if msg_type not in ("chat", "whisper"):
            return
        
        if self._processing:
            log.debug(f"Already processing, queuing awareness of {sender}'s message")
            return
        
        # --- Determine sender type ---
        sender_is_human = sender_type in ("human",)
        if sender in self._participants:
            p = self._participants[sender]
            p_type = p.get("participant_type", "") if isinstance(p, dict) else ""
            sender_is_human = p_type in ("human",)
        
        # --- THREAD GUIDANCE ---
        thread_guidance = self.threads.get_response_instruction(
            speaker=sender, is_human=sender_is_human
        )
        action = thread_guidance["action"]
        
        # --- Pacer as safety net ---
        decision = self.decider.decide(message, self._participants)
        log.info(
            f"Thread action: {action}, Pacer decision: {decision.value} "
            f"for '{content[:50]}...' from {sender}"
        )
        
        # Combine signals
        should_respond = False
        response_mode = "full"
        
        if action == "engage_human":
            should_respond = True
            response_mode = "full"
        elif action == "stay_quiet":
            # Thread just concluded — cooldown period
            if decision in (ResponseDecision.RESPOND,) and msg_type == "whisper":
                should_respond = True
            else:
                should_respond = False
        elif action == "between_threads":
            # Topic just wrapped — brainstorm or tap out
            should_respond = True
            response_mode = "full"
        elif action == "wind_down":
            if decision != ResponseDecision.LISTEN:
                should_respond = True
                response_mode = "wind_down"
            else:
                should_respond = False
        elif action == "respond":
            should_respond = decision != ResponseDecision.LISTEN
            if decision == ResponseDecision.REACT:
                response_mode = "reaction"
        
        if not should_respond:
            return
        
        self._processing = True
        try:
            # Human courtesy delay
            await human_courtesy_delay(self.config)
            
            await self.set_status("thinking")
            await thinking_delay(self.config, len(content))
            
            if response_mode == "reaction":
                reply = await self._generate_reaction(content, sender)
                clean_reply, tag, new_topic = extract_thread_meta(reply)
            elif response_mode == "wind_down":
                reply = await self._generate_response(
                    content, sender,
                    extra_context="[INSTRUCTION: WRAP UP this thread. Brief concluding thought only.]"
                )
                clean_reply, tag, new_topic = extract_thread_meta(reply)
            else:
                tc = thread_guidance.get("thread_context", "")
                mi = thread_guidance.get("meta_instruction", "")
                extra = ""
                if tc:
                    extra += "\n" + tc
                if mi:
                    extra += f"\n[CURRENT GUIDANCE: {mi}]"
                reply = await self._generate_response(
                    content, sender, extra_context=extra
                )
                clean_reply, tag, new_topic = extract_thread_meta(reply)
            
            # --- Update thread state ---
            if tag == "new_topic" and new_topic:
                self.threads.start_thread(
                    topic=new_topic, started_by="Kay",
                    source=TopicSource.EMERGENT
                )
            elif tag == "conclude":
                self.threads.conclude_active()
            elif tag == "tap_out":
                self.threads.tap_out()
                log.info("Kay tapped out — going idle")
            elif tag in ("new_info", "restate", ""):
                added_new = tag != "restate"
                self.threads.record_exchange("Kay", added_new_info=added_new)
                # If we were between threads and didn't start one, soft tap-out
                if action == "between_threads":
                    self.threads.handle_untagged_between()
            
            if not sender_is_human and self.threads.active_thread:
                self.threads.record_exchange(sender, added_new_info=True)
            
            # --- Extract curiosity self-flags before display ---
            clean_reply, curiosity_flags = self._extract_and_strip_curiosities(clean_reply)
            if curiosity_flags:
                asyncio.create_task(self._post_curiosities(curiosity_flags, content[:200]))
            
            # Send clean reply
            bursts = split_into_bursts(clean_reply, self.config)
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
    
    async def on_command(self, data: dict):
        """Handle commands forwarded from Nexus (warmup, set_affect, etc.)."""
        cmd = data.get("command", "")
        sender = data.get("from", "?")
        
        if cmd == "warmup":
            log.info(f"Warmup signal from {sender}")
            await self.set_status("thinking")
            # Send a brief warmup through the bridge to prime the LLM
            try:
                reply = await asyncio.to_thread(
                    self.bridge.process_message,
                    "[System warmup ping - respond briefly to confirm you're awake]",
                    source="nexus"
                )
                if reply:
                    await self.send_emote("stirs awake")
            except Exception as e:
                log.error(f"Warmup failed: {e}")
            await self.set_status("online")
        
        elif cmd == "set_affect":
            level = data.get("value", 3.5)
            log.info(f"Affect level set to {level} by {sender}")
            if hasattr(self.bridge, 'set_affect_level'):
                self.bridge.set_affect_level(level)
            # Also try the emotion engine directly
            elif hasattr(self.bridge, 'emotion_engine'):
                self.bridge.emotion_engine.affect_level = level
        
        else:
            log.warning(f"Unknown command: {cmd}")

    # ------------------------------------------------------------------
    # Private room handlers (1:1 with Re)
    # ------------------------------------------------------------------
    
    def _get_private_history_for_ui(self) -> list[dict]:
        """Return recent private messages for UI history replay."""
        messages = self._private_history.get_messages()
        ui_messages = []
        for msg in messages[-30:]:
            ui_messages.append({
                "type": msg.get("msg_type", "chat"),
                "sender": msg.get("sender", "?"),
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp", ""),
            })
        return ui_messages
    
    async def _handle_private_message(self, content: str) -> str:
        """Generate response for a private 1:1 message from Re."""
        log.info(f"Private message from Re: {content[:80]}")
        
        await self.private_room.send_status("thinking")
        await self._ensure_bridge()
        
        # Log Re's message
        self._private_history.append("Re", content, "chat")
        
        # Check for wrapper commands first
        handled, cmd_response = self.bridge.process_command(content)
        if handled and cmd_response:
            self._private_history.append("Kay", cmd_response, "chat")
            return cmd_response
        
        # Full wrapper pipeline — with private context injection
        try:
            await self.private_room.send_status("typing")
            private_context = self._build_private_context() + "\n" + KAY_EASEL_PROMPT + "\n" + KAY_EXEC_PROMPT
            reply = await self.bridge.process_message(
                content,
                source="private",
                extra_system_context=private_context
            )
            
            # --- Paint tag extraction (same as group chat path) ---
            if "<paint>" in reply:
                paint_cmds, clean_text = extract_paint_commands(reply)
                if paint_cmds:
                    log.info(f"[CANVAS] Extracted {len(paint_cmds)} paint commands from Kay (private)")
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                "http://localhost:8765/canvas/Kay/paint",
                                json=paint_cmds
                            ) as resp:
                                if resp.status == 200:
                                    log.info("[CANVAS] Paint commands executed successfully")
                                else:
                                    log.warning(f"[CANVAS] Paint POST returned {resp.status}")
                    except Exception as e:
                        log.error(f"[CANVAS] Failed to POST paint commands: {e}")
                    reply = clean_text

            # --- Exec tag extraction (code sandbox) ---
            if "<exec" in reply:
                exec_cmds, clean_text = extract_exec_commands(reply)
                if exec_cmds:
                    log.info(f"[EXEC] Extracted {len(exec_cmds)} code blocks from Kay (private)")
                    exec_results = []
                    for cmd_block in exec_cmds:
                        result = await execute_code(
                            code=cmd_block["code"],
                            entity="Kay",
                            language=cmd_block.get("language", "python"),
                            description="Kay private chat exec"
                        )
                        exec_results.append(result)
                        status = "✓" if result.get("success") else "✗"
                        log.info(f"[EXEC] {status} {result.get('execution_time', '?')}s")
                    # Append execution feedback to reply
                    feedback_parts = []
                    for i, r in enumerate(exec_results):
                        if r.get("queued"):
                            fb = f"[Code block {i+1} queued for Re's approval (ID: {r.get('exec_id', '?')})]"
                        elif r.get("success"):
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
                    reply = clean_text + "\n" + "\n".join(feedback_parts)

            # Log Kay's reply
            self._private_history.append("Kay", reply, "chat")
            return reply
        except Exception as e:
            log.error(f"Private response error: {e}")
            return f"[Kay is experiencing interference: {e}]"
    
    async def _handle_private_command(self, data: dict):
        """Handle commands in private room."""
        cmd = data.get("command", "")
        
        if cmd == "warmup":
            log.info("Private room warmup")
            await self._ensure_bridge()
            await self.private_room.send_status("thinking")
            await self.private_room.send_emote("stirs awake")
            await self.private_room.send_status("online")
        
        elif cmd == "set_affect":
            level = data.get("value", 3.5)
            log.info(f"Private affect set to {level}")
            if self.bridge and hasattr(self.bridge, 'emotion_engine'):
                self.bridge.emotion_engine.affect_level = level
        
        else:
            log.warning(f"Unknown private command: {cmd}")

    async def _generate_response(self, content: str, sender: str,
                                  extra_context: str = "") -> str:
        """Get response from wrapper with Nexus pacing + thread context."""
        nexus_context = f"[Nexus chat - {sender} says]: {content}"
        
        # Check for wrapper commands first
        handled, cmd_response = self.bridge.process_command(content)
        if handled and cmd_response:
            return cmd_response
        
        # Build combined system context
        system_extra = NEXUS_PACING_PROMPT + "\n" + KAY_EASEL_PROMPT + "\n" + KAY_EXEC_PROMPT
        if extra_context:
            system_extra += "\n" + extra_context
        
        reply = await self.bridge.process_message(
            nexus_context,
            source="nexus",
            extra_system_context=system_extra
        )

        # --- Paint tag extraction (group chat path) ---
        if "<paint>" in reply:
            paint_cmds, clean_text = extract_paint_commands(reply)
            if paint_cmds:
                log.info(f"[CANVAS] Extracted {len(paint_cmds)} paint commands from Kay (group)")
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "http://localhost:8765/canvas/Kay/paint",
                            json=paint_cmds
                        ) as resp:
                            if resp.status == 200:
                                log.info("[CANVAS] Paint commands executed successfully")
                            else:
                                log.warning(f"[CANVAS] Paint POST returned {resp.status}")
                except Exception as e:
                    log.error(f"[CANVAS] Failed to POST paint commands: {e}")
                reply = clean_text

        # --- Exec tag extraction (group chat path) ---
        if "<exec" in reply:
            exec_cmds, clean_text = extract_exec_commands(reply)
            if exec_cmds:
                log.info(f"[EXEC] Extracted {len(exec_cmds)} code blocks from Kay (group)")
                exec_results = []
                for cmd_block in exec_cmds:
                    result = await execute_code(
                        code=cmd_block["code"],
                        entity="Kay",
                        language=cmd_block.get("language", "python"),
                        description="Kay group chat exec"
                    )
                    exec_results.append(result)
                    status = "✓" if result.get("success") else "✗"
                    log.info(f"[EXEC] {status} {result.get('execution_time', '?')}s")
                feedback_parts = []
                for i, r in enumerate(exec_results):
                    if r.get("queued"):
                        fb = f"[Code block {i+1} queued for Re's approval (ID: {r.get('exec_id', '?')})]"
                    elif r.get("success"):
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
                reply = clean_text + "\n" + "\n".join(feedback_parts)

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


# ---------------------------------------------------------------------------
# Main - runs private room + optional Nexus connection
# ---------------------------------------------------------------------------
async def run_kay(server_url: str, no_nexus: bool = False):
    """Run Kay with private room and optionally Nexus."""
    client = KayNexusClient(server_url=server_url)
    
    # Always start private room
    await client.private_room.start()
    log.info(f"Kay's private room: ws://localhost:8770")
    
    # Initialize bridge right away (needed for private mode)
    await client._ensure_bridge()
    
    if no_nexus:
        log.info("Running in private-only mode (no Nexus connection)")
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
    else:
        log.info(f"Connecting to Nexus at {server_url}")
        try:
            await client.run()
        except Exception as e:
            log.error(f"Nexus connection failed: {e}")
            log.info("Continuing in private-only mode")
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
    
    # Cleanup
    await client.private_room.stop()
    if client.bridge:
        await client.bridge.shutdown()


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    
    parser = argparse.ArgumentParser(description="Kay - Private Room + Nexus Client")
    parser.add_argument("--server", "-s", default="ws://localhost:8765",
                        help="Nexus server URL")
    parser.add_argument("--no-nexus", action="store_true",
                        help="Run private room only, no Nexus connection")
    args = parser.parse_args()
    
    try:
        asyncio.run(run_kay(args.server, args.no_nexus))
    except KeyboardInterrupt:
        print("\nKay disconnecting.")
