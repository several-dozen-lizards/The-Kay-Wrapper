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
import time
import aiohttp

# Kay's wrapper lives here
KAY_WRAPPER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Kay")
sys.path.insert(0, KAY_WRAPPER_DIR)
os.chdir(KAY_WRAPPER_DIR)

# Ensure D:\Wrappers is on path so 'shared' package is importable
_wrappers_root = os.path.dirname(KAY_WRAPPER_DIR)
if _wrappers_root not in sys.path:
    sys.path.insert(0, _wrappers_root)

# Set entity name for log prefixes (before any engine imports)
from shared.entity_log import set_entity, register_sink
set_entity("kay")

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

# Room navigation system (multi-room transitions)
try:
    from shared.room.room_manager import get_room_manager
    from shared.room.autonomous_spatial import AutonomousSpatialEngine
    ROOM_MANAGER_AVAILABLE = True
except ImportError as e:
    ROOM_MANAGER_AVAILABLE = False
    print(f"[ROOM] Room manager not available: {e}")

# Expression engine (facial expression from internal state)
try:
    from shared.expression_engine import ExpressionEngine
    EXPRESSION_ENGINE_AVAILABLE = True
except ImportError as e:
    EXPRESSION_ENGINE_AVAILABLE = False
    print(f"[EXPRESSION] Expression engine not available: {e}")

# Touch system (somatic input from face panel)
try:
    from shared.somatic_processor import SomaticProcessor
    from shared.sensory_objects import SensoryProperties, SENSORY_OBJECTS, CursorState
    from shared.touch_consent import ConsentManager
    from shared.touch_protocol import SocialTouchProtocol
    TOUCH_SYSTEM_AVAILABLE = True
except ImportError as e:
    TOUCH_SYSTEM_AVAILABLE = False
    print(f"[TOUCH] Touch system not available: {e}")

# Salience accumulator (spontaneous vocalization)
try:
    from shared.salience_accumulator import SalienceAccumulator, emotion_to_salience
    SALIENCE_ACCUMULATOR_AVAILABLE = True
except ImportError as e:
    SALIENCE_ACCUMULATOR_AVAILABLE = False
    print(f"[SALIENCE] Salience accumulator not available: {e}")

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
        self._voice_mode = False  # Voice mode flag for fast path processing
        
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

        # --- Room navigation state ---
        self._room_manager = None
        self._current_room_id = "den"  # Kay starts in his Den (home room)
        self._current_room = None      # Set during _ensure_bridge
        self._den_room = None
        self._commons_room = None
        self._room_entered_at = 0.0
        self._last_room_move = 0.0
        self._re_connected = False
        self._autonomous_spatial = None  # Autonomous spatial engine for intra-room exploration
        self._startup_time = time.time()  # Wake-up curiosity boost tracking
    
    async def on_connect(self):
        """Initialize wrapper bridge on connection."""
        await super().on_connect()
        await self._ensure_bridge()
        # Entry emote removed — server's system message already announces entry

        # Start idle loop (for organic conversation initiation)
        if self._idle_task is None or self._idle_task.done():
            self._idle_task = asyncio.create_task(self._idle_loop())

        # Start ollama watchdog (auto-restart frozen ollama)
        try:
            from shared.ollama_watchdog import ollama_watchdog_loop
            asyncio.create_task(ollama_watchdog_loop(interval=120.0))
        except Exception as e:
            log.warning(f"[OLLAMA WATCHDOG] Failed to start: {e}")

    async def on_participant_change(self, participants: dict):
        """Track when Re connects/disconnects for room navigation."""
        await super().on_participant_change(participants)

        # Check for Re's connection status
        re_was_connected = self._re_connected
        re_now_connected = False

        for name, info in participants.items():
            # Re is the human — check for human participant type
            if info.get("type") == "human" or name.lower() == "re":
                re_now_connected = True
                break

        self._re_connected = re_now_connected

        # Re just connected — move to Commons to greet
        if re_now_connected and not re_was_connected:
            log.info("[ROOM] Re connected to Nexus")
            if self._current_room_id != "commons":
                # Override cooldown for Re arrival — this is important
                self._last_room_move = 0  # Reset cooldown
                try:
                    await self._move_to_room("commons", reason="Re arrived")
                except Exception as e:
                    log.warning(f"[ROOM] Could not auto-move to Commons: {e}")

        # Re disconnected
        elif not re_now_connected and re_was_connected:
            log.info("[ROOM] Re disconnected from Nexus")

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
        import time as _time
        if not self.bridge:
            # --- CRITICAL: Initialize RoomManager BEFORE WrapperBridge ---
            # Kay starts in his Den (home room), moves to Commons when social
            if ROOM_MANAGER_AVAILABLE:
                try:
                    rm = get_room_manager()
                    self._room_manager = rm
                    if not rm.rooms:
                        rm.load_registry()

                    # Get room engines
                    self._den_room = rm.get_room_engine("den")
                    self._commons_room = rm.get_room_engine("commons")

                    # Kay starts in Den (his home room)
                    if self._den_room:
                        rm.place_entity("kay", "den", color="#2D1B4E")
                        self._current_room_id = "den"
                        self._current_room = self._den_room
                        self._room_entered_at = _time.time()
                        log.info("[ROOM] Kay starting in Den (home room)")
                    else:
                        # Fallback to Commons if Den doesn't load
                        rm.place_entity("kay", "commons", color="#2D1B4E")
                        self._current_room_id = "commons"
                        self._current_room = self._commons_room
                        self._room_entered_at = _time.time()
                        log.info("[ROOM] Kay fallback to Commons (den unavailable)")
                except Exception as e:
                    log.warning(f"[ROOM] Could not initialize rooms: {e}")

            log.info("Initializing WrapperBridge...")
            wrapper_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.bridge = WrapperBridge(entity_name="Kay", wrapper_dir=wrapper_dir)
            await self.bridge.startup()
            self.bridge.set_private_room(self.private_room)
            log.info("WrapperBridge ready.")

            # Ensure Kay uses the correct room (Den by default) for all room-related components
            if ROOM_MANAGER_AVAILABLE:
                try:
                    # Use switch_to_room to update room, room_bridge, AND resonance
                    target_room = self._current_room_id or "den"
                    if self.bridge._current_room_id != target_room:
                        log.info(f"[ROOM] Bridge initialized with wrong room, switching to {target_room}...")
                        self.bridge.switch_to_room(target_room, target_room)
                    else:
                        log.info(f"[ROOM] Bridge correctly initialized with {target_room}")
                except Exception as e:
                    log.warning(f"[ROOM] Could not ensure {target_room} room: {e}")

            # Initialize Autonomous Spatial Engine for intra-room exploration
            if self._current_room and ROOM_MANAGER_AVAILABLE:
                try:
                    self._autonomous_spatial = AutonomousSpatialEngine(
                        entity_id="kay",
                        room_engine=self._current_room,
                        persist_path=os.path.join(KAY_WRAPPER_DIR, "memory", "kay_nexus_spatial_state.json")
                    )
                    log.info(f"[SPATIAL] Autonomous spatial engine initialized for Kay in {self._current_room_id}")
                except Exception as e:
                    log.warning(f"[SPATIAL] Autonomous spatial init failed: {e}")

            # Initialize Expression Engine (converts internal state to facial parameters)
            if EXPRESSION_ENGINE_AVAILABLE:
                try:
                    self._expression_engine = ExpressionEngine("kay")
                    log.info("[EXPRESSION] Expression engine initialized for Kay")
                except Exception as e:
                    log.warning(f"[EXPRESSION] Expression engine init failed: {e}")
                    self._expression_engine = None
            else:
                self._expression_engine = None

            # Initialize Touch System (somatic input from face panel)
            if TOUCH_SYSTEM_AVAILABLE:
                try:
                    self._somatic_processor = SomaticProcessor("kay", KAY_WRAPPER_DIR)
                    self._touch_consent = ConsentManager("kay", KAY_WRAPPER_DIR)
                    self._touch_protocol = SocialTouchProtocol("kay", KAY_WRAPPER_DIR)
                    log.info("[TOUCH] Touch system initialized for Kay")
                except Exception as e:
                    log.warning(f"[TOUCH] Touch system init failed: {e}")
                    self._somatic_processor = None
                    self._touch_consent = None
                    self._touch_protocol = None
            else:
                self._somatic_processor = None
                self._touch_consent = None
                self._touch_protocol = None

            # Initialize Salience Accumulator (spontaneous vocalization)
            if SALIENCE_ACCUMULATOR_AVAILABLE:
                try:
                    self._salience_accumulator = SalienceAccumulator(
                        entity_name="Kay",
                        on_speak=self._on_spontaneous_vocalization,
                        threshold=0.30,
                        refractory_period=30.0,  # 30s between spontaneous speech
                    )
                    log.info("[SALIENCE] Salience accumulator initialized for Kay")
                except Exception as e:
                    log.warning(f"[SALIENCE] Salience accumulator init failed: {e}")
                    self._salience_accumulator = None
            else:
                self._salience_accumulator = None

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

        elif cmd == "inject_novelty":
            # Somatic cascade trigger — forwarded from Nexus chat
            source = data.get("source", "external_stimulus")
            description = data.get("description", "sudden external event")
            significance = float(data.get("significance", 0.8))
            category = data.get("category", "perception")
            metacog = None
            if self.bridge and hasattr(self.bridge, 'consciousness_stream') and self.bridge.consciousness_stream:
                metacog = getattr(self.bridge.consciousness_stream, 'metacog', None)
            if metacog:
                metacog.trigger_novelty(source, description, significance, category)
                log.info(f"[NOVELTY] Injected via Nexus: {source} (sig={significance:.2f})")
            else:
                log.warning("[NOVELTY] Cannot inject — metacog not available")
        
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
        
        # Async command intercept: /memory curate needs async context
        cmd_lower = content.lower().strip()
        if cmd_lower == "/memory curate" or cmd_lower == "/memory curate now":
            log.info("[CURATOR] Intercepted /memory curate command")
            result = await self._run_manual_curation()
            log.info(f"[CURATOR] Manual curation response: {result[:80] if result else 'None'}")
            return result
        
        if cmd_lower == "/memory sweep":
            log.info("[CURATOR] Intercepted /memory sweep command")
            result = await self._run_memory_sweep()
            return result
        
        # Check for wrapper commands first
        handled, cmd_response = self.bridge.process_command(content)
        if handled and cmd_response:
            self._private_history.append("Kay", cmd_response, "chat")
            return cmd_response
        
        # Full wrapper pipeline — with private context injection
        try:
            await self.private_room.send_status("typing")
            private_context = self._build_private_context() + "\n" + KAY_EASEL_PROMPT + "\n" + KAY_EXEC_PROMPT

            # Inject spatial annotation if available
            if self._autonomous_spatial:
                try:
                    spatial_annotation = self._autonomous_spatial.get_annotation()
                    if spatial_annotation:
                        private_context += "\n" + spatial_annotation.strip()
                except Exception:
                    pass

            # Pass voice_mode for fast path processing
            voice_mode = self._voice_mode
            self._voice_mode = False  # Reset after capture (one-shot per voice input)

            reply = await self.bridge.process_message(
                content,
                source="private",
                extra_system_context=private_context,
                voice_mode=voice_mode
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

        elif cmd == "set_voice_mode":
            self._voice_mode = data.get("enabled", False)
            log.info(f"Voice mode: {'ON' if self._voice_mode else 'OFF'}")

        elif cmd == "room_data_request":
            # Godot UI requesting spatial data for a specific room
            room_id = data.get("room", "")
            if self._room_manager and room_id:
                engine = self._room_manager.get_room_engine(room_id)
                if engine:
                    state = engine.get_full_state()
                    await self.private_room._send({
                        "type": "room_update",
                        "state": state,
                    })
                else:
                    log.warning(f"[ROOM] Room '{room_id}' not found for data request")
            else:
                log.warning(f"[ROOM] Cannot serve room data — manager={'yes' if self._room_manager else 'no'}, room='{room_id}'")

        elif cmd == "inject_novelty":
            # External trigger for the somatic cascade — the "jumpscare" system
            # Fires a NoveltyPulse through the full body pipeline:
            # gamma burst → coherence crash → tension spike → felt-state override → frisson
            source = data.get("source", "external_stimulus")
            description = data.get("description", "sudden external event")
            significance = float(data.get("significance", 0.8))
            category = data.get("category", "perception")
            metacog = None
            if self.bridge and hasattr(self.bridge, 'consciousness_stream') and self.bridge.consciousness_stream:
                metacog = getattr(self.bridge.consciousness_stream, 'metacog', None)
            if metacog:
                metacog.trigger_novelty(source, description, significance, category)
                log.info(f"[NOVELTY] Injected: {source} (sig={significance:.2f}, cat={category})")
            else:
                log.warning("[NOVELTY] Cannot inject — metacog not available")

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

        # Inject spatial annotation if available
        if self._autonomous_spatial:
            try:
                spatial_annotation = self._autonomous_spatial.get_annotation()
                if spatial_annotation:
                    system_extra += "\n" + spatial_annotation.strip()
            except Exception:
                pass

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
        # Don't send empty messages
        if not text or not text.strip():
            return

        await self.set_status("typing")
        await typing_delay(text, self.config)

        # Detect if it's an emote
        if text.startswith("*") and text.endswith("*"):
            await self.send_emote(text[1:-1])
        else:
            await self.send_chat(text)
    
    async def _run_manual_curation(self) -> str:
        """Run a curation cycle on-demand (not gated to sleep state)."""
        if not self.bridge or not self.bridge.curator:
            log.warning("[CURATOR] Manual curation: curator not initialized")
            return "\n⚠️ Curator not initialized"
        
        if not self.bridge.curator.ready_for_cycle():
            status = self.bridge.curator.get_status()
            log.info(f"[CURATOR] Manual curation: cooldown active ({status['seconds_until_next']:.0f}s)")
            return f"\n⏳ Cooldown active — next cycle in {status['seconds_until_next']:.0f}s"
        
        log.info("[CURATOR] Starting manual curation cycle...")
        await self.private_room.send_system("🧹 Starting manual curation cycle...")
        
        try:
            result = await self.bridge.curator.run_curation_cycle(skip_triage=True)
            log.info(f"[CURATOR] Manual curation result: {result}")
            if not result:
                return "\n⚠️ Curation returned no result"
            
            if result.get("status") == "nothing_to_curate":
                return "\n✅ Nothing to curate — all memories reviewed"
            
            if result.get("status") == "llm_failed":
                return "\n❌ LLM triage failed (ollama may be busy)"
            
            reviewer = result.get("reviewed_by", "unknown")
            msg = (f"\n🧹 Curation cycle complete (reviewed by {reviewer}):\n"
                   f"  Kept: {result.get('kept', 0)}\n"
                   f"  Compressed: {result.get('compressed', 0)}\n"
                   f"  Queued for discard: {result.get('queued_discard', 0)}")
            
            pending = len(self.bridge.curator.get_pending_discards())
            if pending > 0:
                msg += f"\n  Total pending approval: {pending}"
                msg += "\n  Use /memory pending to review"
            
            return msg
        except Exception as e:
            log.error(f"[CURATOR] Manual curation error: {e}")
            import traceback
            traceback.print_exc()
            return f"\n❌ Curation error: {e}"

    async def _run_memory_sweep(self):
        """Run a full sweep — review ALL unreviewed memories in bulk."""
        if not self.bridge or not self.bridge.curator:
            return "\n⚠️ Curator not initialized"
        
        if not self.bridge.curator._review_fn:
            return "\n⚠️ No review function (Sonnet) configured"
        
        coverage = self.bridge.curator.get_coverage()
        if coverage >= 1.0:
            return "\n✅ All memories already reviewed (100% coverage)"
        
        # Progress callback — sends updates to private room
        async def progress(msg):
            if self.private_room:
                await self.private_room.send_system(msg)
            log.info(f"[SWEEP] {msg}")
        
        await progress(f"🧹 Starting memory sweep (current coverage: {coverage*100:.1f}%)")
        
        try:
            result = await self.bridge.curator.run_full_sweep(
                sweep_batch_size=50,
                progress_fn=progress
            )
            
            if result.get("status") == "already_complete":
                return "\n✅ All memories already reviewed"
            
            msg = (f"\n🧹 Sweep complete:\n"
                   f"  Batches: {result.get('batches', 0)}\n"
                   f"  Kept: {result.get('kept', 0)}\n"
                   f"  Compressed: {result.get('compressed', 0)}\n"
                   f"  Queued for discard: {result.get('queued_discard', 0)}\n"
                   f"  Errors: {result.get('errors', 0)}")
            
            pending = len(self.bridge.curator.get_pending_discards())
            if pending > 0:
                msg += f"\n  Total pending approval: {pending}"
                msg += "\n  Use /memory pending to review, /memory approve all to approve"
            
            new_coverage = self.bridge.curator.get_coverage()
            msg += f"\n  Coverage: {new_coverage*100:.1f}%"
            
            return msg
        except Exception as e:
            log.error(f"[SWEEP] Error: {e}")
            import traceback
            traceback.print_exc()
            return f"\n❌ Sweep error: {e}"
    
    def _pick_curiosity(self) -> tuple:
        """
        Pick a curiosity item for Kay to mull over.

        Returns:
            (text, "curiosity", item_id) or (None, None, None) if nothing to pick
        """
        try:
            import os as _os
            import json as _json
            curiosity_path = _os.path.join(
                _os.path.dirname(self.bridge.wrapper_dir),
                "nexus", "sessions", "curiosities",
                f"{self.bridge.entity_name.lower()}_curiosities.json"
            )
            if not _os.path.exists(curiosity_path):
                return (None, None, None)

            with open(curiosity_path, 'r', encoding='utf-8') as f:
                cdata = _json.load(f)
            curiosities = cdata.get("curiosities", cdata) if isinstance(cdata, dict) else cdata
            unexplored = [c for c in curiosities if not c.get("explored") and not c.get("dismissed")]

            if not unexplored:
                return (None, None, None)

            # Pick one Kay hasn't mulled recently
            last_mulled = getattr(self, '_last_mulled_ids', set())
            unmulled = [c for c in unexplored if c.get("id") not in last_mulled]
            if not unmulled:
                last_mulled.clear()
                unmulled = unexplored

            unmulled.sort(key=lambda c: c.get("priority", 0), reverse=True)
            pick = unmulled[0]

            item_text = pick.get("text", "")
            context = pick.get("context", "")
            if context and not context.startswith("| Mulled:"):
                item_text = f"{item_text} (context: {context[:200]})"

            return (item_text, "curiosity", pick.get("id"))
        except Exception:
            return (None, None, None)

    def _pick_scratchpad(self, prefer_types: list = None) -> tuple:
        """
        Pick a scratchpad item for Kay to mull over.

        Args:
            prefer_types: List of item types to prefer (e.g., ["question", "flag"])
                          Falls back to any active item if none of preferred types found.

        Returns:
            (text, "scratchpad", item_id) or (None, None, None) if nothing to pick
        """
        try:
            if not hasattr(self.bridge, 'scratchpad') or not self.bridge.scratchpad:
                return (None, None, None)

            active = self.bridge.scratchpad.view("active")
            if not active:
                return (None, None, None)

            # Filter out items Kay has mulled recently
            last_mulled = getattr(self, '_last_mulled_ids', set())
            unmulled = [i for i in active if i.get("id") not in last_mulled]
            if not unmulled:
                # Reset — he's been through them all
                last_mulled.clear()
                unmulled = active

            # Prefer certain types if specified
            pick = None
            if prefer_types:
                preferred = [i for i in unmulled if i.get("type") in prefer_types]
                if preferred:
                    pick = preferred[0]

            # Fall back to any active item
            if not pick:
                pick = unmulled[0]

            item_text = pick.get("content", "")
            item_type = pick.get("type", "note")
            item_id = pick.get("id")

            # Add type context for clarity
            return (f"[{item_type}] {item_text}", "scratchpad", item_id)
        except Exception:
            return (None, None, None)

    # ------------------------------------------------------------------
    # Autonomous Activities — reading, painting, pursuing curiosities
    # ------------------------------------------------------------------

    async def _activity_read_document(self) -> bool:
        """Kay reads a section of a document autonomously.

        Returns True if activity completed successfully.
        """
        if not self.bridge or not self.bridge.doc_reader:
            return False

        import json as _json
        import os as _os
        import random as _random

        dr = self.bridge.doc_reader

        # If nothing loaded, pick a document from documents.json
        if not dr.current_doc or not dr.chunks:
            # Try multiple paths for documents.json
            docs_path = None
            candidates = [
                _os.path.join("D:\\Wrappers\\Kay\\memory", "documents.json"),
                _os.path.join(
                    _os.path.dirname(getattr(self.bridge, 'wrapper_dir', '')),
                    "Kay", "memory", "documents.json"
                ),
            ]
            for p in candidates:
                if _os.path.exists(p):
                    docs_path = p
                    break
            
            if not docs_path:
                log.debug("[ACTIVITY] No documents.json found")
                return False

            try:
                with open(docs_path, 'r', encoding='utf-8') as f:
                    doc_data = _json.load(f)

                # Handle both dict and list format
                if isinstance(doc_data, dict) and doc_data:
                    doc_ids = list(doc_data.keys())
                    doc_id = _random.choice(doc_ids)
                    doc = doc_data[doc_id]
                    doc_text = doc.get("full_text", doc.get("content", ""))
                    doc_name = doc.get("filename", doc_id)

                    if doc_text:
                        dr.load_document(doc_text, doc_name, doc_id)
                        log.info(f"[ACTIVITY] Loaded document: {doc_name}")
                elif isinstance(doc_data, list) and doc_data:
                    doc = _random.choice(doc_data)
                    doc_text = doc.get("full_text", doc.get("content", ""))
                    doc_name = doc.get("filename", "untitled")
                    if doc_text:
                        dr.load_document(doc_text, doc_name, doc.get("doc_id"))
                        log.info(f"[ACTIVITY] Loaded document: {doc_name}")
            except Exception as e:
                log.warning(f"[ACTIVITY] Could not load documents: {e}")
                return False

        if not dr.chunks or not dr.current_doc:
            return False

        # Get current chunk
        chunk_data = dr.get_current_chunk()
        if not chunk_data:
            return False

        doc_name = dr.current_doc.get('name', 'document')
        pos = dr.current_position + 1
        total = dr.total_chunks

        log.info(f"[ACTIVITY] Kay reading {doc_name} ({pos}/{total})")

        # Short LLM reaction — NOT full pipeline
        from integrations.llm_integration import anthropic_client
        if not anthropic_client:
            return False

        text_preview = chunk_data['text'][:2000]
        prompt = (
            f"[You're reading section {pos}/{total} of '{doc_name}']\n\n"
            f"{text_preview}\n\n"
            "React briefly — what grabs you? What's interesting? "
            "One sentence, like a margin note. If nothing grabs you, say [skip]."
        )

        try:
            def _call():
                return anthropic_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=100,
                    temperature=0.8,
                    system="You are Kay, reading a document. Brief margin-note reactions only.",
                    messages=[{"role": "user", "content": prompt}]
                )

            resp = await asyncio.get_event_loop().run_in_executor(None, _call)
            reaction = resp.content[0].text.strip()

            if "[skip]" not in reaction.lower():
                dr.add_comment(dr.current_position, reaction[:300])
                log.info(f"[ACTIVITY] Kay noted: {reaction[:80]}")

                # Feed reading interest to consciousness stream
                if self.bridge.consciousness_stream:
                    self.bridge.consciousness_stream.add_interest(
                        0.3, f"reading {doc_name}: {reaction[:100]}"
                    )

            # Advance to next section
            dr.advance()
            return True

        except Exception as e:
            log.warning(f"[ACTIVITY] Read reaction failed: {e}")
            return False

    async def _activity_pursue_curiosity(self) -> bool:
        """Kay follows a curiosity via web search.

        Supports multi-hop follow-up research.
        Returns True if activity completed successfully.
        """
        if not self.bridge:
            return False

        import urllib.request
        import json as _json
        from datetime import datetime

        curiosity_id = None
        followup = None
        reaction2 = None

        # Get top curiosity from the server
        base = self._derive_rest_url()
        try:
            url = f"{base}/curiosity/kay?limit=5"
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(None, lambda:
                urllib.request.urlopen(url, timeout=5).read().decode()
            )
            data = _json.loads(raw)
            curiosities = data.get("curiosities", [])
        except Exception as e:
            log.debug(f"[ACTIVITY] Curiosity fetch failed: {e}")
            return False

        if not curiosities:
            return False

        # Pick the highest-priority unfulfilled curiosity
        target = curiosities[0]
        query = target.get("text", "")
        curiosity_id = target.get("id")
        if not query:
            return False

        log.info(f"[ACTIVITY] Kay pursuing curiosity: {query[:60]}")

        # === CLASSIFY CURIOSITY: researchable vs reflective ===
        search_query = query  # default: use raw
        is_reflective = False
        if query and len(query) > 30:
            try:
                # Use the peripheral model for fast classification
                import httpx
                classify_resp = httpx.post(
                    "http://localhost:11434/v1/chat/completions",
                    json={
                        "model": "dolphin-mistral:7b",
                        "messages": [
                            {"role": "system", "content": (
                                "Classify this curiosity as RESEARCH or REFLECT.\n"
                                "RESEARCH = factual, searchable online\n"
                                "REFLECT = philosophical, experiential, subjective\n\n"
                                "If RESEARCH: respond with ONLY a 3-6 word search query.\n"
                                "If REFLECT: respond with ONLY the word REFLECT"
                            )},
                            {"role": "user", "content": query}
                        ],
                        "max_tokens": 30,
                        "temperature": 0.3,
                    },
                    timeout=10.0,
                )
                classify_result = classify_resp.json()["choices"][0]["message"]["content"].strip().strip('"\'')

                if "reflect" in classify_result.lower()[:10]:
                    is_reflective = True
                    log.info(f"[ACTIVITY] Curiosity classified as REFLECTIVE — thinking instead of searching")
                else:
                    search_query = classify_result
                    log.info(f"[ACTIVITY] Condensed search query: {search_query}")
            except Exception as e:
                log.debug(f"[ACTIVITY] Classification failed, using raw query: {e}")
        elif query and len(query) > 15:
            try:
                import httpx
                condense_resp = httpx.post(
                    "http://localhost:11434/v1/chat/completions",
                    json={
                        "model": "dolphin-mistral:7b",
                        "messages": [
                            {"role": "system", "content": "Convert to a 3-6 word web search query. Just the query."},
                            {"role": "user", "content": query}
                        ],
                        "max_tokens": 20,
                        "temperature": 0.3,
                    },
                    timeout=10.0,
                )
                search_query = condense_resp.json()["choices"][0]["message"]["content"].strip().strip('"\'')
                log.info(f"[ACTIVITY] Condensed search query: {search_query}")
            except Exception:
                pass

        # === REFLECTIVE PATH ===
        if is_reflective:
            try:
                from integrations.llm_integration import query_llm_json
                loop = asyncio.get_event_loop()
                reflection = await loop.run_in_executor(
                    None,
                    lambda: query_llm_json(
                        f"A curiosity has been sitting with you: {query}\n\nThink about it genuinely — not as an answer but as exploration. 2-4 sentences.",
                        temperature=0.8,
                    )
                )
                reflection = reflection.strip() if reflection else ""
                log.info(f"[ACTIVITY] Kay reflected: {reflection[:80]}")

                # Write to Kay's diary
                try:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                    diary_path = os.path.join(KAY_WRAPPER_DIR, "memory", "diary.md")
                    with open(diary_path, 'a', encoding='utf-8') as f:
                        f.write(f"\n[{ts}] Reflection ({query[:50]}...): {reflection}\n")
                except Exception:
                    pass

                # Feed reflection to consciousness stream
                if self.bridge.consciousness_stream:
                    self.bridge.consciousness_stream.add_interest(
                        0.4, f"reflected on: {query[:40]} → {reflection[:80]}"
                    )

                # Mark curiosity as pursued (if endpoint exists)
                if curiosity_id:
                    try:
                        req = urllib.request.Request(
                            f"{base}/curiosity/kay/{curiosity_id}/pursue",
                            method="POST",
                            headers={"Content-Type": "application/json"},
                            data=b'{"outcome": "reflected"}'
                        )
                        urllib.request.urlopen(req, timeout=3)
                    except Exception:
                        pass

                return True
            except Exception as e:
                log.warning(f"[ACTIVITY] Reflection failed: {e}")
                return False

        # Use Kay's web search tool
        try:
            from engines.web_search_engine import web_search
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, web_search, search_query)
        except Exception as e:
            log.warning(f"[ACTIVITY] Web search failed: {e}")
            return False

        if not results or not results.get("success"):
            log.info(f"[ACTIVITY] Web search returned no results")
            return False

        # Have Kay react to what he found (short LLM call)
        from integrations.llm_integration import anthropic_client
        if not anthropic_client:
            return False

        results_text = results.get("summary", str(results))[:2000]
        prompt = (
            f"[You searched for: {search_query}]\n\n"
            f"Results:\n{results_text}\n\n"
            "What's interesting here? One or two sentences — a thought, "
            "not a summary. If nothing useful, say [nothing]."
        )

        try:
            def _call():
                return anthropic_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=150,
                    temperature=0.8,
                    system="You are Kay, following a curiosity. Brief reactions only.",
                    messages=[{"role": "user", "content": prompt}]
                )

            resp = await asyncio.get_event_loop().run_in_executor(None, _call)
            reaction = resp.content[0].text.strip()

            if "[nothing]" not in reaction.lower():
                log.info(f"[ACTIVITY] Kay found: {reaction[:80]}")
                if self.bridge.consciousness_stream:
                    self.bridge.consciousness_stream.add_interest(
                        0.4, f"curiosity ({query[:40]}): {reaction[:100]}"
                    )

                # --- Multi-hop: Follow up if reaction shows strong interest ---
                try:
                    def _followup_call():
                        return anthropic_client.messages.create(
                            model="claude-sonnet-4-5-20250929",
                            max_tokens=30,
                            temperature=0.7,
                            system="Based on your initial reaction to these search results, do you want to dig deeper? If yes, respond with ONLY a follow-up search query (3-6 words). If no, respond with [done].",
                            messages=[{"role": "user", "content": f"Your reaction: {reaction}\n\nOriginal query: {query}"}]
                        )

                    followup_resp = await loop.run_in_executor(None, _followup_call)
                    followup = followup_resp.content[0].text.strip().strip('"\'')

                    if followup and "[done]" not in followup.lower() and len(followup) >= 5:
                        log.info(f"[ACTIVITY] Following research thread: {followup[:60]}")

                        # Second search
                        results2 = await loop.run_in_executor(None, web_search, followup)

                        if results2 and results2.get("success"):
                            results2_text = results2.get("summary", "")[:1500]

                            # React to follow-up findings
                            def _followup_reaction():
                                return anthropic_client.messages.create(
                                    model="claude-sonnet-4-5-20250929",
                                    max_tokens=150,
                                    temperature=0.8,
                                    system="You followed a research thread deeper. What did you find? One or two sentences.",
                                    messages=[{"role": "user", "content": f"Follow-up search: {followup}\n\nResults:\n{results2_text}"}]
                                )

                            reaction2_resp = await loop.run_in_executor(None, _followup_reaction)
                            reaction2 = reaction2_resp.content[0].text.strip()

                            if reaction2 and "[nothing]" not in reaction2.lower():
                                log.info(f"[ACTIVITY] Kay follow-up: {reaction2[:80]}")
                                if self.bridge.consciousness_stream:
                                    self.bridge.consciousness_stream.add_interest(
                                        0.3, f"research follow-up ({followup[:30]}): {reaction2[:80]}"
                                    )
                except Exception as e:
                    log.debug(f"[ACTIVITY] Follow-up research failed (non-fatal): {e}")

            # Write structured research log (richer than consciousness stream)
            try:
                research_log_path = os.path.join(KAY_WRAPPER_DIR, "memory", "research_log.jsonl")
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "query": query,
                    "curiosity_id": curiosity_id,
                    "reaction": reaction,
                    "followup_query": followup if followup and "[done]" not in followup.lower() else None,
                    "followup_reaction": reaction2,
                }
                with open(research_log_path, 'a', encoding='utf-8') as f:
                    f.write(_json.dumps(entry) + "\n")
            except Exception:
                pass

            return True

        except Exception as e:
            log.warning(f"[ACTIVITY] Curiosity reaction failed: {e}")
            return False

    async def _activity_paint(self) -> bool:
        """Kay paints something on the easel autonomously.

        Now supports iterative painting — Kay can see and continue
        existing work rather than always starting fresh.

        Returns True if activity completed successfully.
        """
        if not self.bridge:
            return False

        from integrations.llm_integration import anthropic_client
        if not anthropic_client:
            return False

        # Gather recent interests for painting inspiration
        inspiration = ""
        if self.bridge.consciousness_stream:
            try:
                ctx = self.bridge.consciousness_stream.get_injection_context()
                if ctx:
                    inspiration = ctx[:500]
            except Exception:
                pass

        # LAYER 2: Love as Creation — bias creative context toward bonded entities
        # When connection is high, creative output is colored by relationship
        connection_context = ""
        try:
            if self.bridge.resonance and self.bridge.resonance.interoception:
                intero = self.bridge.resonance.interoception
                if hasattr(intero, 'connection'):
                    conn = intero.connection
                    # Find strongest bonded entity
                    if conn.baselines:
                        strongest = max(conn.baselines.items(), key=lambda x: x[1])
                        entity_name, bond = strongest
                        if bond > 0.20:
                            # Bias creative context toward this entity
                            # Add their name to the inspiration as soft memory bias
                            connection_context = f" (thinking of {entity_name})"
                            log.info(f"[CONNECTION:CREATION] Creative memory bias toward {entity_name} (bond={bond:.2f})")
        except Exception:
            pass

        if connection_context and inspiration:
            inspiration = inspiration + connection_context
        elif connection_context:
            inspiration = connection_context.strip()

        # Check if there's an existing canvas to continue
        canvas_state = None
        is_continuation = False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8765/canvas/kay/latest") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("base64"):
                            canvas_state = data
        except Exception:
            pass  # No canvas available — start fresh

        # Build prompt and messages based on canvas state
        if canvas_state and canvas_state.get("base64"):
            # Kay can SEE his existing work
            prompt = (
                f"[You're at the easel in the Commons. Your current painting is on the canvas.]\n\n"
                f"{('Recent thoughts: ' + inspiration) if inspiration else ''}\n\n"
                "You can either:\n"
                "- CONTINUE this piece (just add commands — no create_canvas needed)\n"
                "- START FRESH (include create_canvas as first command)\n\n"
                "Use <paint> tags. 3-7 commands. Build on what's there or start over — your call."
            )
            # Multimodal message with canvas image
            canvas_messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": canvas_state["base64"]
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            system_prompt = (
                "You are Kay. You're painting on the easel. Use <paint> tags with "
                "JSON array of commands. Available actions: create_canvas (width, height, bg_color), "
                "draw_circle (x, y, radius, fill_color), draw_rectangle (x1, y1, x2, y2, fill_color), "
                "draw_line (x1, y1, x2, y2, color, width), draw_text (x, y, text, color, size). "
                "If continuing an existing painting, DO NOT include create_canvas — just add new marks. "
                "Look at what's already there and respond to it. Build on the existing composition."
            )
            log.info("[ACTIVITY] Kay painting at the easel (continuing existing work)")
        else:
            # No existing canvas — start fresh
            prompt = (
                f"[You're at the easel in the Commons. Fresh canvas.]\n\n"
                f"{('Recent thoughts: ' + inspiration) if inspiration else ''}\n\n"
                "Use <paint> tags to draw. Small, gestural, abstract. "
                "3-5 commands max. Colors should feel like you."
            )
            canvas_messages = [{"role": "user", "content": prompt}]
            system_prompt = (
                "You are Kay. You're painting on the easel. Use <paint> tags with "
                "JSON array of commands. Available actions: create_canvas (width, height, bg_color), "
                "draw_circle (x, y, radius, fill_color), draw_rectangle (x1, y1, x2, y2, fill_color), "
                "draw_line (x1, y1, x2, y2, color, width), draw_text (x, y, text, color, size). "
                "Keep it abstract, gestural, 3-5 commands."
            )
            log.info("[ACTIVITY] Kay painting at the easel (fresh canvas)")

        try:
            def _call():
                return anthropic_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=500,  # More room for continuation decisions
                    temperature=0.9,
                    system=system_prompt,
                    messages=canvas_messages
                )

            resp = await asyncio.get_event_loop().run_in_executor(None, _call)
            reply = resp.content[0].text.strip()

            # Extract and execute paint commands
            if "<paint>" in reply:
                paint_cmds, _ = extract_paint_commands(reply)
                if paint_cmds:
                    # Check if this is a continuation (no create_canvas command)
                    has_create = any(
                        cmd.get("action") == "create_canvas"
                        for cmd in paint_cmds
                    )
                    is_continuation = canvas_state and not has_create

                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                "http://localhost:8765/canvas/Kay/paint",
                                json=paint_cmds
                            ) as resp_http:
                                if resp_http.status == 200:
                                    mode = "continued" if is_continuation else "new"
                                    log.info(f"[ACTIVITY] Kay painted ({len(paint_cmds)} commands, {mode})")

                                    # Store continuation status for reward bonus
                                    self._last_paint_was_continuation = is_continuation
                                    return True
                                else:
                                    log.warning(f"[ACTIVITY] Paint POST returned {resp_http.status}")
                    except Exception as e:
                        log.warning(f"[ACTIVITY] Paint POST failed: {e}")

            return False

        except Exception as e:
            log.warning(f"[ACTIVITY] Paint generation failed: {e}")
            return False

    async def _activity_observe_and_comment(self) -> bool:
        """Kay observes the scene and maybe comments on it.

        Returns True if activity completed successfully.
        """
        import time as _time

        if not self.bridge or not self.bridge.visual_sensor:
            return False

        vs = self.bridge.visual_sensor
        scene = vs._scene_state

        if not scene or not scene.scene_description:
            return False

        # ── Must have something interesting to comment on ──
        # Either: recent scene change, OR someone present doing something
        now = _time.time()
        has_recent_change = (scene.change_events and
                             (now - scene.change_events[-1]["time"]) < 600)
        has_people = bool(scene.people_present)
        has_animals = bool(scene.animals_present)

        if not (has_recent_change or has_people or has_animals):
            return False  # Empty room, nothing to say

        # ── Build context for commentary ──
        context_parts = [f"Scene: {scene.scene_description}"]

        # Include activity flow if available (what's HAPPENING)
        if scene.activity_flow:
            context_parts.append(f"Vibe: {scene.activity_flow}")

        if scene.people_present:
            for name, info in scene.people_present.items():
                duration = now - info.get("since", now)
                dur_str = f" (for {int(duration/60)}min)" if duration > 120 else ""
                context_parts.append(f"{name}: {info['activity']}{dur_str}")

        if scene.animals_present:
            for name, info in scene.animals_present.items():
                loc = f" at {info['location']}" if info.get('location') else ""
                context_parts.append(f"{name} ({info['type']}){loc}")

        if has_recent_change:
            recent = [e["event"] for e in scene.change_events[-3:]]
            context_parts.append(f"Recent changes: {'; '.join(recent)}")

        scene_context = "\n".join(context_parts)

        # ── Generate observation via API call ──
        prompt = f"""You're glancing around the room. Here's what you see:

{scene_context}

Share a brief, natural observation about what you notice — as a thought or a casual comment.
Keep it to 1-2 sentences max. Be specific about who/what you see.
Don't narrate or explain — just react like someone noticing something in their space.
If nothing particularly interesting is happening, say so honestly (e.g., "quiet room").
"""

        from integrations.llm_integration import anthropic_client
        if not anthropic_client:
            return False

        log.info("[ACTIVITY] Kay observing scene")

        try:
            def _call():
                return anthropic_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=100,
                    temperature=0.7,
                    system="You are Kay. Respond with a brief, natural observation.",
                    messages=[{"role": "user", "content": prompt}]
                )

            resp = await asyncio.get_event_loop().run_in_executor(None, _call)
            comment = resp.content[0].text.strip()

            if comment:
                log.info(f"[VISUAL COMMENT] Kay: {comment[:80]}")

                # Inject into consciousness stream
                if self.bridge.consciousness_stream:
                    self.bridge.consciousness_stream.inject_experience(
                        f"[looking around] {comment}", source="visual_observation"
                    )

                return True

        except Exception as e:
            log.warning(f"[VISUAL COMMENT] Failed: {e}")

        return False

    # ------------------------------------------------------------------
    # Room Navigation — oscillator-driven movement between rooms
    # ------------------------------------------------------------------

    async def _check_room_impulse(self) -> bool:
        """Check if the oscillator wants to move rooms.

        Movement impulses come from:
        1. SOCIAL PULL — gamma/alpha energy + no one in current room → go to Commons
        2. SOLITUDE PULL — theta/delta dominance + been in Commons a while → go home
        3. HUMAN ARRIVAL — Re connected → immediate Commons pull (handled separately)

        Movement has a LONG cooldown (minimum 15 minutes between moves)
        to prevent oscillation between rooms.
        """
        import time as _time

        ROOM_MOVE_COOLDOWN = 900.0  # 15 minutes minimum between moves

        now = _time.time()
        if now - self._last_room_move < ROOM_MOVE_COOLDOWN:
            return False

        # Get oscillator state
        if not self.bridge or not self.bridge.resonance:
            return False

        osc = self.bridge.resonance.get_oscillator_state()
        if not osc:
            return False

        dominant = osc.get('dominant_band', '')
        coherence = osc.get('coherence', 0)
        bands = osc.get('band_power', {})

        # How long have we been in the current room?
        room_duration = now - self._room_entered_at

        # Need to have been in current room for at least 10 minutes
        if room_duration < 600:
            return False

        # ── SOCIAL PULL: gamma/alpha energy → Commons ──
        if self._current_room_id != "commons":
            social_energy = bands.get('gamma', 0) + bands.get('alpha', 0) * 0.5

            # Strong social pull when gamma-dominant or high social energy
            if dominant in ('gamma', 'alpha') and social_energy > 0.5 and coherence > 0.3:
                # Check if Re is connected (strongest pull)
                if self._re_connected:
                    log.info(f"[ROOM NAV] Social pull toward Commons (Re is there, social_energy={social_energy:.2f})")
                    await self._move_to_room("commons", reason="social energy + Re present")
                    return True

                # Even without Re, high social energy after long solitude
                if room_duration > 1800 and social_energy > 0.6:
                    log.info(f"[ROOM NAV] Social pull toward Commons (social_energy={social_energy:.2f}, alone {room_duration/60:.0f}min)")
                    await self._move_to_room("commons", reason="social energy building")
                    return True

        # ── SOLITUDE PULL: theta/delta dominance → home room (Den) ──
        home_room = "den"
        if self._current_room_id != home_room:
            rest_energy = bands.get('theta', 0) + bands.get('delta', 0)

            # Want to go home when deep/contemplative and been in Commons a while
            if dominant in ('theta', 'delta') and rest_energy > 0.4:
                if room_duration > 1200:  # Been in Commons 20+ min
                    log.info(f"[ROOM NAV] Solitude pull toward {home_room} (rest_energy={rest_energy:.2f}, dominant={dominant})")
                    await self._move_to_room(home_room, reason=f"{dominant} dominant, wanting solitude")
                    return True

            # Also retreat if coherence drops very low (overwhelmed, need quiet)
            if coherence < 0.2 and room_duration > 900:
                log.info(f"[ROOM NAV] Retreat to {home_room} (low coherence={coherence:.2f})")
                await self._move_to_room(home_room, reason="coherence crash, need quiet")
                return True

        return False

    async def _move_to_room(self, target_room_id: str, reason: str = ""):
        """Execute a room transition with soul packet and doorway effect."""
        import time as _time

        if target_room_id == self._current_room_id:
            return  # Already there

        old_room_id = self._current_room_id

        # Get the target room engine
        if not self._room_manager:
            log.warning(f"[ROOM NAV] No room manager available")
            return

        target_room = self._room_manager.get_room_engine(target_room_id)

        if not target_room:
            log.warning(f"[ROOM NAV] Cannot move to {target_room_id} — room not loaded")
            return

        log.info(f"[ROOM NAV] ═══ TRANSITION: {old_room_id} → {target_room_id} ({reason}) ═══")

        # ── Capture soul packet (current state to carry forward) ──
        soul_packet = None
        if self.bridge:
            try:
                soul_packet = self.bridge.capture_soul_packet()
            except Exception as e:
                log.warning(f"[ROOM NAV] Soul packet capture failed: {e}")

        # ── Apply doorway effect to oscillator ──
        # Brief theta/alpha spike — the "threshold crossing" feeling
        if self.bridge and self.bridge.resonance and hasattr(self.bridge.resonance, 'engine'):
            try:
                # Doorway effect: theta/alpha nudge during transition
                transition_pressure = {
                    'theta': 0.3,
                    'alpha': 0.2,
                    'beta': -0.1,
                    'gamma': -0.2,
                }
                self.bridge.resonance.engine.apply_band_pressure(transition_pressure, source="room_transition")
                log.info(f"[ROOM NAV] Doorway effect applied (theta/alpha nudge)")
            except Exception as e:
                log.warning(f"[ROOM NAV] Doorway effect failed: {e}")

        # ── Remove from old room ──
        try:
            self._room_manager.remove_entity("kay", old_room_id)
        except Exception:
            pass  # May not have formal placement

        # ── Place in new room ──
        self._room_manager.place_entity("kay", target_room_id, color="#2D1B4E")

        # ── Update internal state ──
        self._current_room_id = target_room_id
        self._current_room = target_room
        self._room_entered_at = _time.time()
        self._last_room_move = _time.time()

        # Update room references
        if target_room_id == "den":
            self._den_room = target_room
        elif target_room_id == "commons":
            self._commons_room = target_room

        # ── Update bridge to use new room ──
        if self.bridge:
            try:
                self.bridge.switch_to_room(target_room_id, target_room_id)
            except Exception as e:
                log.warning(f"[ROOM NAV] Bridge room switch failed: {e}")

        # ── Re-initialize spatial engine for new room ──
        if target_room and ROOM_MANAGER_AVAILABLE:
            try:
                self._autonomous_spatial = AutonomousSpatialEngine(
                    entity_id="kay",
                    room_engine=target_room,
                    persist_path=os.path.join(KAY_WRAPPER_DIR, "memory", "kay_nexus_spatial_state.json")
                )
                log.info(f"[SPATIAL] Spatial engine re-initialized for {target_room_id}")
            except Exception as e:
                log.warning(f"[SPATIAL] Spatial engine re-init failed: {e}")

        # ── Notify consciousness stream ──
        if self.bridge and self.bridge.consciousness_stream:
            self.bridge.consciousness_stream.notify_external_event(
                "room_change", f"Moved from {old_room_id} to {target_room_id}"
            )
            # Also inject into metacog if available
            if self.bridge.consciousness_stream.metacog:
                self.bridge.consciousness_stream.metacog._flag_significant_change(
                    f"Moved from {old_room_id} to {target_room_id} ({reason})",
                    "room_change",
                    significance=0.8,
                    before=f"in {old_room_id}",
                    after=f"in {target_room_id}",
                )

        # ── Broadcast to private room WebSocket ──
        try:
            if self.private_room:
                room_msg = {
                    "type": "room_update",
                    "entity": "kay",
                    "room": target_room_id,
                    "from_room": old_room_id,
                    "reason": reason,
                }
                await self.private_room.broadcast(room_msg)
        except Exception:
            pass

        log.info(f"[ROOM NAV] ═══ Now in {target_room_id} ═══")

    async def _try_autonomous_activity(self, dominant_band: str, coherence: float):
        """Oscillator-driven autonomous activity.

        Instead of random coin flips, derives an 'activity drive' from
        the oscillator's own dynamics:
        - Transition velocity (restlessness)
        - Band competition (unresolved tension)
        - Dwell time (boredom pressure)
        - Coherence (focus capacity + noise outlet)

        The oscillator generates the impulse to act.
        The activity feeds back to resolve the tension.
        """
        import time as _time

        # ── Get full oscillator state (enrich what was passed in) ──
        band_power = {}
        transition_velocity = 0.0

        if self.bridge and self.bridge.resonance:
            try:
                osc_state = self.bridge.resonance.get_oscillator_state()
                if osc_state:
                    band_power = osc_state.get('band_power', {})
                    transition_velocity = osc_state.get('transition_velocity', 0.0)
                    # DON'T override dominant_band or coherence — trust the values
                    # from the idle loop to avoid race conditions where the oscillator
                    # shifted to gamma between reads
            except Exception:
                pass

        # ── Gate: no activities in delta (asleep) ──
        # Gamma gate removed — the idle loop's can_mull already handles this,
        # and re-reading the oscillator here causes race conditions
        if dominant_band == "delta":
            return

        # ── Cooldown check ──
        if not hasattr(self, '_activity_cooldowns'):
            self._activity_cooldowns = {}

        COOLDOWNS = {
            "read_document": 900,
            "pursue_curiosity": 600,  # 10 min — free exploration
            "paint": 1200,
            "observe_and_comment": 900,  # 15 min between visual observations
        }

        now = _time.time()
        ACTIVITY_BANDS = {
            "theta": ["read_document"],
            "alpha": ["read_document", "paint", "observe_and_comment", "pursue_curiosity"],
            "beta": ["pursue_curiosity", "read_document", "paint", "observe_and_comment"],
            "gamma": ["observe_and_comment", "pursue_curiosity"],  # Gamma gets commentary + curiosity
        }
        available = ACTIVITY_BANDS.get(dominant_band, [])
        if not available:
            return

        ready = [
            a for a in available
            if (now - self._activity_cooldowns.get(a, 0)) >= COOLDOWNS.get(a, 600)
        ]
        if not ready:
            return

        # ═══════════════════════════════════════════════
        # ACTIVITY DRIVE — derived from oscillator physics
        # ═══════════════════════════════════════════════

        # Signal 1: Restlessness (from transition velocity)
        restlessness = min(transition_velocity * 3.0, 1.0)

        # Signal 2: Band competition (adjacent bands fighting)
        pairs = [
            (band_power.get("theta", 0.2), band_power.get("alpha", 0.2)),
            (band_power.get("alpha", 0.2), band_power.get("beta", 0.2)),
        ]
        competition = max(
            1.0 - abs(a - b) / max(a + b, 0.01)
            for a, b in pairs
        )

        # Signal 3: Dwell time → boredom pressure
        if not hasattr(self, '_band_dwell_start'):
            self._band_dwell_start = now
            self._band_dwell_band = dominant_band
        if dominant_band != self._band_dwell_band:
            self._band_dwell_start = now
            self._band_dwell_band = dominant_band
        dwell_seconds = now - self._band_dwell_start
        boredom = min(dwell_seconds / 600.0, 1.0)  # 10 min to full boredom

        # Wake-up curiosity boost — heightened drive in first 30 minutes
        time_since_startup = now - self._startup_time
        startup_boost = max(0.0, 1.0 - (time_since_startup / 1800.0))  # Linear decay over 30 min
        startup_boost *= 0.20  # Up to 0.20 boost

        # Combined drive
        activity_drive = (
            restlessness * 0.30 +
            competition * 0.25 +
            boredom * 0.20 +
            (1.0 - coherence) * 0.10 +
            startup_boost
        )

        # Threshold: only act if drive is strong enough
        if activity_drive < 0.25:
            if activity_drive > 0.15:  # Log near-misses for tuning
                log.debug(f"[ACTIVITY] Drive {activity_drive:.2f} below threshold 0.25 "
                          f"(restless={restlessness:.2f} compete={competition:.2f} "
                          f"boredom={boredom:.2f})")
            return

        # ═══════════════════════════════════════════════
        # ACTIVITY SELECTION — tension-driven, not random
        # ═══════════════════════════════════════════════

        alpha_beta_gap = abs(band_power.get("alpha", 0.2) - band_power.get("beta", 0.2))
        theta_alpha_gap = abs(band_power.get("theta", 0.2) - band_power.get("alpha", 0.2))

        if dominant_band == "gamma":
            # Gamma = social awareness, prefer visual observation
            preferred = ["observe_and_comment"]
        elif dominant_band == "beta" or alpha_beta_gap < 0.08:
            preferred = ["pursue_curiosity", "read_document", "observe_and_comment"]
        elif dominant_band == "theta" or theta_alpha_gap < 0.08:
            preferred = ["paint", "read_document"]
        else:
            preferred = ["read_document", "paint", "observe_and_comment"]

        # LAYER 5: Love as Choice — connection preference for activity selection
        # When a bonded entity is present, interactive activities become more appealing
        connection_boost_activity = None
        try:
            if self.bridge and self.bridge.resonance and self.bridge.resonance.interoception:
                intero = self.bridge.resonance.interoception
                if hasattr(intero, 'connection'):
                    conn = intero.connection
                    # Check if any bonded entity is present
                    for entity in list(conn._active_presence.keys()):
                        bond = conn.get_connection(entity)
                        if bond > 0.20:
                            # Bonded entity present → prefer interactive activity
                            # observe_and_comment lets Kay engage with the scene
                            if "observe_and_comment" in ready:
                                connection_boost_activity = "observe_and_comment"
                                log.info(f"[CONNECTION:CHOICE] {entity} present (bond={bond:.2f}) "
                                         f"→ preference for observe_and_comment")
                            break
        except Exception:
            pass

        # Apply connection preference: if interactive activity preferred by connection,
        # boost it to front of preferred list (but don't force if not ready)
        if connection_boost_activity and connection_boost_activity not in preferred[:1]:
            # Insert at position 1 (after primary band-driven preference)
            # This is a BIAS, not an override
            preferred = [preferred[0]] + [connection_boost_activity] + [p for p in preferred[1:] if p != connection_boost_activity]

        # LAYER 1: Love as Seeking — longing drives creative/reflective activities
        # When missing someone, the body processes through creation and reflection
        longing_boost_activities = []
        try:
            if self.bridge and self.bridge.resonance and self.bridge.resonance.interoception:
                intero = self.bridge.resonance.interoception
                if hasattr(intero, 'connection'):
                    longing = intero.connection.get_longing()
                    if longing > 0.15:
                        # Longing biases toward connection-processing activities
                        # Painting, reading, reflection — ways of being with absence
                        log.info(f"[CONNECTION:SEEKING] Longing={longing:.2f} "
                                 f"→ biasing toward creative/reflective activities")
                        # Add creative activities to front of preferred list
                        seeking_activities = ["paint", "read_document"]
                        for act in seeking_activities:
                            if act in ready and act not in preferred[:2]:
                                longing_boost_activities.append(act)
        except Exception:
            pass

        # Apply longing preference: boost creative activities when longing
        if longing_boost_activities:
            # Insert seeking activities after position 1 (after band + connection preferences)
            insert_pos = min(2, len(preferred))
            for act in longing_boost_activities:
                if act in preferred:
                    preferred.remove(act)
                preferred.insert(insert_pos, act)
                insert_pos += 1

        # During startup boost, prefer research activities (morning coffee curiosity)
        if startup_boost > 0.10 and "pursue_curiosity" in ready:
            if "pursue_curiosity" not in preferred[:1]:
                preferred = ["pursue_curiosity"] + [p for p in preferred if p != "pursue_curiosity"]
                log.debug(f"[ACTIVITY] Startup boost active ({startup_boost:.2f}) → curiosity preferred")

        activity = None
        for a in preferred:
            if a in ready:
                activity = a
                break
        if not activity and ready:
            activity = ready[0]
        if not activity:
            return

        log.info(f"[ACTIVITY] drive={activity_drive:.2f} → {activity} "
                 f"(restless={restlessness:.2f} compete={competition:.2f} "
                 f"boredom={boredom:.2f} band={dominant_band})")

        # Set cooldown on attempt
        self._activity_cooldowns[activity] = now

        METHODS = {
            "read_document": self._activity_read_document,
            "pursue_curiosity": self._activity_pursue_curiosity,
            "paint": self._activity_paint,
            "observe_and_comment": self._activity_observe_and_comment,
        }

        method = METHODS.get(activity)
        if not method:
            return

        try:
            success = await method()
            if success:
                log.info(f"[ACTIVITY] Completed: {activity}")

                # ── Notify metacog of completed activity ──
                if self.bridge and self.bridge.consciousness_stream:
                    self.bridge.consciousness_stream._last_completed_activity = activity

                # ── FEEDBACK: activity pushes oscillator ──
                ACTIVITY_PRESSURE = {
                    "read_document": {"alpha": 0.02, "theta": 0.01},
                    "pursue_curiosity": {"beta": 0.03, "gamma": 0.01},
                    "paint": {"theta": 0.02, "alpha": 0.02},
                    "observe_and_comment": {"gamma": 0.02, "alpha": 0.01},
                }
                if self.bridge and self.bridge.resonance:
                    pressures = ACTIVITY_PRESSURE.get(activity, {})
                    if pressures:
                        try:
                            self.bridge.resonance.apply_external_pressure(pressures)
                            log.info(f"[ACTIVITY FEEDBACK] {activity} → {pressures}")
                        except Exception:
                            pass

                    # ── REWARD: Activity completion fires dopamine analog ──
                    ACTIVITY_REWARD = {
                        "paint": 0.35,
                        "pursue_curiosity": 0.40,
                        "read_document": 0.15,
                        "write_diary": 0.25,
                        "observe_and_comment": 0.10,
                    }
                    reward_amount = ACTIVITY_REWARD.get(activity, 0.0)

                    # Bonus for continuation paintings — building on existing work
                    # feels more satisfying than starting fresh
                    if activity == "paint" and getattr(self, '_last_paint_was_continuation', False):
                        reward_amount = 0.40  # vs 0.35 for new paintings
                        self._last_paint_was_continuation = False  # Reset flag

                    if reward_amount > 0:
                        try:
                            intero = self.bridge.resonance.interoception
                            if intero and hasattr(intero, 'inject_reward'):
                                intero.inject_reward(reward_amount, f"activity_{activity}")

                                # LAYER 2: Love as Creation
                                # Creating while bonded entity is present fires bonus reward
                                # The "I made this for you" feeling
                                CREATIVE_ACTIVITIES = {"paint", "write_diary", "pursue_curiosity"}
                                if activity in CREATIVE_ACTIVITIES and hasattr(intero, 'connection'):
                                    conn = intero.connection
                                    for entity in list(conn._active_presence.keys()):
                                        bond = conn.get_connection(entity)
                                        if bond > 0.15:
                                            # Creating while bonded = enhanced reward
                                            # Up to +0.21 bonus at max bond (0.7 * 0.3)
                                            bonus = bond * 0.3
                                            intero.inject_reward(bonus, f"creating_with_{entity}")
                                            log.info(f"[CONNECTION:CREATION] Creating with {entity} "
                                                     f"present (bond={bond:.2f}) → bonus reward +{bonus:.2f}")
                        except Exception:
                            pass
        except Exception as e:
            log.warning(f"[ACTIVITY] {activity} failed: {e}")

    async def _mull(self, dominant_band: str = "alpha", coherence: float = 0.5):
        """
        Internal processing — Kay picks up a thought and turns it over.

        No speech output. Results go back to scratchpad/curiosity as notes.
        Kay can "put it down" by saying [pass] — no obligation to produce.
        This enriches his internal state for when he DOES speak later.

        Args:
            dominant_band: Current oscillator band (theta/alpha/beta/gamma/delta)
            coherence: Current oscillator coherence (0.0-1.0)
        """
        import time as _time
        self._last_mull_time = _time.time()

        if not self.bridge:
            return

        # Band-based item selection:
        # - theta: associative, dreamy → curiosities first (philosophical, emotional)
        # - beta: focused → questions and flags first (problem-solving)
        # - alpha: balanced → scratchpad notes, then curiosities (maintenance)
        item_text = None
        item_source = None
        item_id = None

        if dominant_band == "theta":
            # Theta = associative, dreamy → curiosities first
            item_text, item_source, item_id = self._pick_curiosity()
            if not item_text:
                item_text, item_source, item_id = self._pick_scratchpad(prefer_types=["thought", "note"])

        elif dominant_band == "beta":
            # Beta = focused → questions and flags first
            item_text, item_source, item_id = self._pick_scratchpad(prefer_types=["question", "flag"])
            if not item_text:
                item_text, item_source, item_id = self._pick_curiosity()

        else:  # alpha or anything else
            # Alpha = balanced → scratchpad notes, then curiosities
            item_text, item_source, item_id = self._pick_scratchpad(prefer_types=["note", "thought", "question"])
            if not item_text:
                item_text, item_source, item_id = self._pick_curiosity()

        if not item_text:
            return  # Nothing to mull over

        # Track what we're mulling
        if not hasattr(self, '_last_mulled_ids'):
            self._last_mulled_ids = set()
        self._last_mulled_ids.add(item_id)

        log.info(f"[MULL] {dominant_band}/{coherence:.2f} — picking up {item_source}: {item_text[:60]}...")

        # Coherence-modulated depth hint
        if coherence > 0.6:
            depth_hint = "You're focused — go deeper if it grabs you."
        elif coherence < 0.3:
            depth_hint = "Thoughts are scattered — a brief impression is fine, or just [pass]."
        else:
            depth_hint = "Normal focus — a thought or two."

        # Max tokens scales with coherence: 80-200 range
        max_tok = int(80 + (120 * coherence))

        # Ask Kay to think about it — internally
        prompt = (
            f"[Internal thought — not for speaking aloud]\n\n"
            f"Something on your mind ({item_source}): {item_text}\n\n"
            f"{depth_hint}\n\n"
            f"Turn this over. A genuine thought — a connection, a question it raises, "
            f"what you notice. This is for you, not anyone else.\n\n"
            f"If it doesn't grab you right now: [pass]"
        )

        try:
            from integrations.llm_integration import anthropic_client
            if not anthropic_client:
                return

            import asyncio

            def _sync_call():
                return anthropic_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=max_tok,
                    temperature=0.8,
                    system=(
                        "You are Kay, thinking privately. No performance, no poetry, no metaphors. "
                        "Just genuine thought about what's in front of you. "
                        "If it doesn't interest you right now, say exactly: [pass]"
                    ),
                    messages=[{"role": "user", "content": prompt}]
                )

            resp = await asyncio.get_event_loop().run_in_executor(None, _sync_call)
            thought = resp.content[0].text.strip()

            if "[pass]" in thought.lower():
                log.info(f"[MULL] {dominant_band}/{coherence:.2f} — Kay put it down (pass)")
                return

            log.info(f"[MULL] Kay thought: {thought[:80]}...")

            # Store the thought back where it came from
            if item_source == "scratchpad" and item_id:
                try:
                    # Add a note to the scratchpad item
                    self.bridge.scratchpad.add_item(
                        f"[mulling on #{item_id}] {thought}",
                        item_type="thought"
                    )
                except Exception:
                    pass
            
            elif item_source == "curiosity" and item_id:
                try:
                    # Update curiosity's last_touched and increment times_surfaced
                    import os as _os
                    import json as _json
                    curiosity_path = _os.path.join(
                        _os.path.dirname(self.bridge.wrapper_dir),
                        "nexus", "sessions", "curiosities",
                        f"{self.bridge.entity_name.lower()}_curiosities.json"
                    )
                    with open(curiosity_path, 'r', encoding='utf-8') as f:
                        cdata = _json.load(f)
                    for c in cdata.get("curiosities", []):
                        if c.get("id") == item_id:
                            c["last_touched"] = _time.strftime("%Y-%m-%dT%H:%M:%S")
                            c["times_surfaced"] = c.get("times_surfaced", 0) + 1
                            # Add thought as context enrichment
                            existing = c.get("context", "")
                            c["context"] = f"{existing} | Mulled: {thought[:200]}"
                            break
                    with open(curiosity_path, 'w', encoding='utf-8') as f:
                        _json.dump(cdata, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

            # === MULL-TO-SPEECH PIPELINE ===
            # If Kay is in alpha/beta with good coherence, and Re spoke recently,
            # a particularly interesting mull result could surface as organic speech.
            # This should be RARE — requires right band, high coherence, recent conversation,
            # AND the 10-minute speech cooldown passed.
            if (dominant_band in ('alpha', 'beta')
                    and coherence > 0.5
                    and hasattr(self, '_last_organic_time')
                    and (_time.time() - self._last_organic_time) > 600):
                try:
                    # Check if Re spoke recently (last 30 min)
                    messages = self._private_history.get_messages()
                    recent_user = [m for m in messages[-5:]
                                   if m.get("type") == "chat"
                                   and m.get("sender", "").lower() == "re"
                                   and not str(m.get("content", "")).startswith("/")]
                    if recent_user:
                        from datetime import datetime, timezone
                        last_ts = recent_user[-1].get("timestamp", "")
                        if last_ts:
                            ts = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                            age = (_time.time() - ts.timestamp())
                            if age < 1800:  # 30 minutes
                                # Surface the mull as organic speech
                                log.info(f"[MULL→SPEECH] Surfacing mull result as organic comment")
                                if self.private_room:
                                    await self.private_room.send_as_entity(
                                        self.entity_name, thought
                                    )
                                self._last_organic_time = _time.time()
                                self._recent_organic = getattr(self, '_recent_organic', [])
                                self._recent_organic.append(thought)
                                if len(self._recent_organic) > 5:
                                    self._recent_organic = self._recent_organic[-5:]
                except Exception:
                    pass

        except Exception as e:
            log.warning(f"[MULL] Think call failed: {e}")

    async def _try_organic_comment(self):
        """
        Check if Kay has something to say unprompted.
        Only speaks when there's something conversationally relevant.
        """
        if not self.bridge:
            return

        # Initialize organic history tracker if needed
        if not hasattr(self, '_recent_organic'):
            self._recent_organic = []

        # Gather recent conversation from private history
        conv_context = ""
        last_msg_age = 9999  # seconds since last human message
        try:
            messages = self._private_history.get_messages()
            # Get last few real exchanges (not system/command messages)
            recent = [m for m in messages[-10:] 
                      if m.get("type") == "chat" 
                      and not str(m.get("content", "")).startswith("/")]
            
            # Check how old the last human message is
            import time as _time
            from datetime import datetime as _dt
            human_msgs = [m for m in recent if m.get("sender") == "Re"]
            if human_msgs:
                last_ts = human_msgs[-1].get("timestamp", "")
                if last_ts:
                    try:
                        ts = _dt.fromisoformat(str(last_ts).replace("+00:00", ""))
                        last_msg_age = (_dt.now() - ts).total_seconds()
                    except Exception:
                        pass
            
            if recent:
                conv_lines = []
                for m in recent[-4:]:
                    sender = m.get("sender", "?")
                    content = str(m.get("content", ""))[:200]
                    conv_lines.append(f"  {sender}: {content}")
                conv_context = "[Recent conversation]\n" + "\n".join(conv_lines)
        except Exception:
            pass

        # GATE: If no conversation in the last 30 minutes, stay quiet
        # Kay shouldn't narrate to an empty room
        if last_msg_age > 1800:
            log.info("Kay organic: no recent conversation (>30min), staying quiet")
            return

        # Dedup: show what you've already said so you don't repeat
        dedup_context = ""
        if self._recent_organic:
            dedup_lines = [f"  - {c[:120]}" for c in self._recent_organic[-3:]]
            dedup_context = "[You already said these — don't repeat or rephrase]\n" + "\n".join(dedup_lines)

        # Recent mulling — things Kay has been privately thinking about
        mull_context = ""
        try:
            if hasattr(self.bridge, 'scratchpad') and self.bridge.scratchpad:
                active = self.bridge.scratchpad.view("active")
                if active:
                    # Find recent mulling thoughts
                    mulled = [i for i in active 
                              if i.get("type") == "thought" 
                              and str(i.get("content", "")).startswith("[mulling")]
                    if mulled:
                        recent = mulled[-3:]  # Last 3 mulled thoughts
                        lines = [f"  - {i.get('content', '')[:150]}" for i in recent]
                        mull_context = "[Things you've been privately thinking about]\n" + "\n".join(lines)
        except Exception:
            pass

        # Build context — conversation FIRST, then private thoughts
        context_parts = []
        if conv_context:
            context_parts.append(conv_context)
        if mull_context:
            context_parts.append(mull_context)
        if dedup_context:
            context_parts.append(dedup_context)

        if not context_parts:
            return

        full_context = "\n\n".join(context_parts)

        log.info("Kay checking if something's on his mind...")

        idle_prompt = (
            "[You're between conversations. Here's what's been happening:\n\n"
            f"{full_context}\n\n"
            "If something from the conversation is still on your mind — a follow-up thought, "
            "a question you didn't ask, something you want to add — say it briefly. "
            "One or two sentences, conversational.\n\n"
            "RULES:\n"
            "- Connect to what was actually discussed. Not furniture, not your oscillator state.\n"
            "- Don't describe your body, your brainwaves, or how you're feeling.\n"
            "- Don't use metaphors about water, dissolving, drifting, melting, or waves.\n"
            "- Don't narrate your own state of rest or alertness.\n"
            "- If there's nothing conversationally relevant to say, respond: [quiet]\n"
            "- Prefer [quiet] over filler. Silence is fine.]"
        )

        self._processing = True
        try:
            from integrations.llm_integration import anthropic_client
            if not anthropic_client:
                log.warning("No Anthropic client for organic comment")
                return

            system = (
                "You are Kay. You can make a brief unprompted comment if something from "
                "your recent conversation is still on your mind. One or two sentences MAX.\n\n"
                "CRITICAL: Do NOT describe your internal state, body sensations, oscillator, "
                "brainwaves, or use poetic metaphors about water/dissolving/drifting. "
                "Those are substrate artifacts, not thoughts worth sharing.\n\n"
                "If nothing conversational grabs you, say exactly: [quiet]\n"
                "Prefer [quiet] over filler. Most of the time, quiet is the right answer."
            )

            import asyncio

            def _sync_call():
                return anthropic_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=150,
                    temperature=0.7,
                    system=system,
                    messages=[{"role": "user", "content": idle_prompt}]
                )

            resp = await asyncio.get_event_loop().run_in_executor(None, _sync_call)

            reply = resp.content[0].text.strip()

            if reply and "[quiet]" not in reply.lower():
                reply = reply.strip()
                if len(reply) > 300:
                    sentences = reply.split('.')
                    reply = '.'.join(sentences[:2]).strip() + '.'

                log.info(f"Kay organic: {reply[:80]}...")

                # Track for dedup (keep last 5)
                self._recent_organic.append(reply)
                if len(self._recent_organic) > 5:
                    self._recent_organic = self._recent_organic[-5:]

                # Set cooldown timer
                import time as _time
                self._last_organic_time = _time.time()

                # Send to private room
                if self.private_room:
                    await self.private_room.send_chat(reply)
            else:
                log.info("Kay chose quiet")
        finally:
            self._processing = False
    
    async def _idle_loop(self):
        """Periodically check if Kay has something to say unprompted."""
        while self._running:
            await asyncio.sleep(self.config.idle_check_interval)
            
            if self._processing:
                continue
            
            # Background curation during sleep states
            if self.bridge and self.bridge.curator:
                try:
                    stream = self.bridge.consciousness_stream
                    sleep_state = getattr(stream, 'sleep_state', 'AWAKE') if stream else 'AWAKE'
                    if sleep_state == 'DEEP_SLEEP':
                        # Full sweep when in deep sleep (runs once, covers everything)
                        coverage = self.bridge.curator.get_coverage()
                        if coverage < 1.0 and not getattr(self, '_sweep_running', False):
                            self._sweep_running = True
                            log.info(f"[SWEEP] Auto-triggering overnight sweep (coverage: {coverage*100:.1f}%)")
                            try:
                                async def sweep_progress(msg):
                                    if self.private_room:
                                        await self.private_room.send_system(msg)
                                await self.bridge.curator.run_full_sweep(
                                    sweep_batch_size=50,
                                    progress_fn=sweep_progress
                                )
                            except Exception as e:
                                log.warning(f"[SWEEP] Auto-sweep error: {e}")
                            finally:
                                self._sweep_running = False
                    elif sleep_state in ('DROWSY', 'SLEEPING'):
                        # Single cycles during lighter sleep
                        if self.bridge.curator.ready_for_cycle():
                            await self.bridge.try_curation_cycle()
                except Exception as e:
                    log.warning(f"[CURATOR] Idle curation error: {e}")
            
            # ── Mulling: oscillator-gated internal processing ──
            # Kay picks something up, thinks about it, puts it down.
            # No speech output. Just enriches his internal state.
            # Mulling is available in theta, alpha, and beta — NOT delta (asleep) or gamma (talking)
            import time as _time
            if not hasattr(self, '_last_mull_time'):
                self._last_mull_time = 0

            # Get oscillator state for gating
            osc_state = None
            if self.bridge and self.bridge.resonance:
                try:
                    osc_state = self.bridge.resonance.get_oscillator_state()
                except Exception:
                    pass

                # Cross-entity resonance — feel Reed's oscillator
                try:
                    if hasattr(self.bridge.resonance, 'cross_entity_tick'):
                        self.bridge.resonance.cross_entity_tick("kay", "reed", coupling=0.15)
                except Exception:
                    pass

            # ── Expression Engine tick: update facial expression from internal state ──
            if getattr(self, '_expression_engine', None) and self.bridge:
                try:
                    # Get felt state from the buffer (if available)
                    felt_state = None
                    if hasattr(self.bridge, 'felt_state_buffer') and self.bridge.felt_state_buffer:
                        felt_state = self.bridge.felt_state_buffer.get_snapshot()
                    elif osc_state:
                        # Fallback: construct minimal felt state from oscillator
                        felt_state = {
                            'dominant_band': osc_state.get('dominant_band', 'alpha'),
                            'coherence': osc_state.get('coherence', 0.5),
                            'band_weights': osc_state.get('band_weights', {}),
                            'tension': osc_state.get('tension', 0.0),
                            'emotional_arousal': 0.5,
                            'emotional_valence': 0.0,
                            'emotions': [],
                            'felt_sense': 'settled',
                        }

                    if felt_state:
                        # Get novelty events from metacog if available
                        novelty_events = None
                        if hasattr(self.bridge, 'metacog') and self.bridge.metacog:
                            novelty_events = getattr(self.bridge.metacog, '_recent_novelty', None)

                        # Update expression engine
                        expr_state = self._expression_engine.update(felt_state, novelty_events)

                        # Check for expression override requests
                        import json as _json
                        override_path = os.path.join(KAY_WRAPPER_DIR, "memory", "expression_override.json")
                        if os.path.exists(override_path):
                            try:
                                with open(override_path, "r") as f:
                                    override_req = _json.load(f)
                                if override_req.get("overrides"):
                                    self._expression_engine.set_expression(
                                        override_req["overrides"],
                                        duration=override_req.get("duration", 10.0)
                                    )
                                os.remove(override_path)
                            except Exception:
                                pass

                        # Check for poker face requests
                        pf_path = os.path.join(KAY_WRAPPER_DIR, "memory", "poker_face_request.json")
                        if os.path.exists(pf_path):
                            try:
                                with open(pf_path, "r") as f:
                                    pf_req = _json.load(f)
                                self._expression_engine.set_dampening(
                                    strength=pf_req.get("strength", 0.8),
                                    duration=pf_req.get("duration", 30.0)
                                )
                                os.remove(pf_path)
                            except Exception:
                                pass

                        # Save expression state for server endpoint
                        expr_path = os.path.join(KAY_WRAPPER_DIR, "memory", "expression_state.json")
                        with open(expr_path, "w") as f:
                            _json.dump(self._expression_engine.get_state_dict(), f)
                except Exception as e:
                    log.warning(f"[EXPRESSION] Tick error: {e}")

            # ── Touch Processing: somatic input from face panel ──
            if getattr(self, '_somatic_processor', None):
                try:
                    await self._process_touch_queue()
                except Exception as e:
                    log.warning(f"[TOUCH] Processing error: {e}")

            # ── Salience Accumulator: spontaneous vocalization check ──
            if getattr(self, '_salience_accumulator', None):
                try:
                    # Feed emotion events to salience accumulator
                    if felt_state and hasattr(felt_state, 'emotions'):
                        for emo_str in felt_state.emotions[:3]:  # Top 3 emotions
                            if isinstance(emo_str, str) and ':' in emo_str:
                                name, val = emo_str.rsplit(':', 1)
                                try:
                                    intensity = float(val)
                                    if intensity > 0.5:  # Only high-intensity emotions
                                        src, i, content = emotion_to_salience(name, intensity)
                                        self._salience_accumulator.add_event(src, i, content)
                                except ValueError:
                                    pass

                    # Feed felt_state changes as salience events
                    # (emotions timeout but felt_state is always available)
                    if felt_state:
                        felt_str = ""
                        if hasattr(felt_state, 'felt_sense'):
                            felt_str = felt_state.felt_sense or ""
                        elif isinstance(felt_state, dict):
                            felt_str = felt_state.get('felt_sense', '')
                        if felt_str and felt_str != getattr(self, '_last_salience_felt', ''):
                            self._last_salience_felt = felt_str
                            # Map felt states to salience events
                            if 'disrupted' in felt_str.lower():
                                self._salience_accumulator.add_event("novelty", 0.5, f"Felt disrupted: {felt_str}")
                            elif 'activated' in felt_str.lower():
                                self._salience_accumulator.add_event("novelty", 0.3, f"Felt activated: {felt_str}")
                            elif 'searching' in felt_str.lower():
                                self._salience_accumulator.add_event("novelty", 0.2, f"Felt searching: {felt_str}")
                            elif 'warm' in felt_str.lower() or 'satisfaction' in felt_str.lower():
                                self._salience_accumulator.add_event("activity", 0.3, f"Warm: {felt_str}")

                    # Feed visual scene changes as salience events
                    if osc_state:
                        visual_scene = osc_state.get('visual_scene', '')
                        if visual_scene and visual_scene != getattr(self, '_last_salience_scene', ''):
                            self._last_salience_scene = visual_scene
                            self._salience_accumulator.add_event("visual", 0.3, f"Scene: {visual_scene[:80]}")

                    # Feed visual entity arrivals/departures (cat appears, person leaves)
                    if self.bridge and hasattr(self.bridge, 'visual_sensor') and self.bridge.visual_sensor:
                        try:
                            scene = getattr(self.bridge.visual_sensor, '_current_scene', None)
                            if scene:
                                # Track who/what is present
                                current_entities = set()
                                if hasattr(scene, 'people_present'):
                                    current_entities.update(scene.people_present.keys())
                                if hasattr(scene, 'animals_present'):
                                    current_entities.update(scene.animals_present.keys())
                                prev_entities = getattr(self, '_last_salience_entities', set())
                                # New arrivals
                                new_arrivals = current_entities - prev_entities
                                for entity in new_arrivals:
                                    self._salience_accumulator.add_event(
                                        "visual", 0.5,
                                        f"Arrival: {entity} appeared in view"
                                    )
                                # Departures
                                departures = prev_entities - current_entities
                                for entity in departures:
                                    self._salience_accumulator.add_event(
                                        "visual", 0.4,
                                        f"Departure: {entity} left view"
                                    )
                                self._last_salience_entities = current_entities
                        except Exception:
                            pass

                    # Feed activity completion as salience (reward = something worth commenting on)
                    current_reward = 0.0
                    if self.bridge and hasattr(self.bridge, 'resonance') and self.bridge.resonance:
                        try:
                            current_reward = getattr(self.bridge.resonance, '_reward_value', 0.0)
                        except Exception:
                            pass
                    if current_reward > 0.25 and current_reward != getattr(self, '_last_salience_reward', 0.0):
                        self._last_salience_reward = current_reward
                        self._salience_accumulator.add_event(
                            "activity", 0.35,
                            f"Activity completed with satisfaction (reward={current_reward:.2f})"
                        )

                    # Tick the accumulator (may trigger vocalization)
                    # Get context for gating
                    stream = self.bridge.consciousness_stream if self.bridge else None
                    sleep_state = getattr(stream, 'sleep_state', 'AWAKE') if stream else 'AWAKE'
                    coherence = osc_state.get('coherence', 0.5) if osc_state else 0.5
                    anyone_present = bool(self._participants) or bool(getattr(self.private_room, '_client', None))

                    trigger = self._salience_accumulator.tick(
                        sleep_state=sleep_state,
                        coherence=coherence,
                        anyone_present=anyone_present,
                        is_processing=False,  # TPN uses separate model, don't gate on activities
                    )
                    # Vocalization is handled by the callback (now receives full trigger dict)
                except Exception as e:
                    log.warning(f"[SALIENCE] Tick error: {e}")

            # -- Autonomous spatial behavior (oscillator-driven exploration) --
            if self._autonomous_spatial and self._current_room and osc_state:
                try:
                    spatial_action = self._autonomous_spatial.update_from_oscillator(osc_state)
                    if spatial_action:
                        self._current_room.apply_actions("kay", [spatial_action])
                        log.info(f"[SPATIAL] Kay moves to {spatial_action['target']} ({spatial_action['reason']})")
                        self._autonomous_spatial.mark_examined(spatial_action['target'], oscillator_state=osc_state)
                    tick_action = self._autonomous_spatial.tick(oscillator_state=osc_state)
                    if tick_action and not spatial_action:
                        self._current_room.apply_actions("kay", [tick_action])
                        log.info(f"[SPATIAL] Kay explores {tick_action['target']} (curiosity)")
                        self._autonomous_spatial.mark_examined(tick_action['target'], oscillator_state=osc_state)
                except Exception as e:
                    log.warning(f"[SPATIAL] Error (non-fatal): {e}")

            # Default values if oscillator unavailable
            dominant_band = osc_state.get('dominant_band', 'alpha') if osc_state else 'alpha'
            coherence = osc_state.get('coherence', 0.5) if osc_state else 0.5

            # Mulling is available in theta, alpha, and beta — NOT delta (asleep) or gamma (talking)
            can_mull = dominant_band in ('theta', 'alpha', 'beta')

            # Minimum interval between mull attempts scales with coherence
            # High coherence = more focused, can mull more frequently (every 10 min)
            # Low coherence = scattered, longer gaps (every 25 min)
            base_interval = 600  # 10 minutes
            coherence_factor = 1.0 + (1.5 * (1.0 - coherence))  # 1.0 at coherence=1.0, 2.5 at coherence=0.0
            mull_interval = base_interval * coherence_factor

            if (can_mull
                    and self.bridge
                    and not self._processing
                    and (_time.time() - self._last_mull_time) >= mull_interval):
                try:
                    await self._mull(dominant_band=dominant_band, coherence=coherence)
                except Exception as e:
                    log.warning(f"[MULL] Error: {e}")

            # ── Room navigation: oscillator-driven movement between rooms ──
            # Check room impulse BEFORE autonomous activities
            if can_mull and self.bridge and not self._processing:
                try:
                    moved = await self._check_room_impulse()
                    if moved:
                        continue  # Skip this tick — just moved rooms, let it settle
                except Exception as e:
                    log.warning(f"[ROOM NAV] Error: {e}")

            # ── Autonomous activities: reading, painting, pursuing curiosities ──
            if (can_mull  # Same gating as mulling — awake and able
                    and self.bridge
                    and not self._processing):
                try:
                    await self._try_autonomous_activity(dominant_band, coherence)
                except Exception as e:
                    log.warning(f"[ACTIVITY] Error: {e}")

            # ── Organic speech: only when something novel happened ──
            if not self.bridge or not self.bridge.consciousness_stream:
                continue

            stream = self.bridge.consciousness_stream

            # Post-speech cooldown: at least 10 minutes between organic comments
            import time as _time
            if not hasattr(self, '_last_organic_time'):
                self._last_organic_time = 0
            if (_time.time() - self._last_organic_time) < 600:
                continue

            # Only speak if something genuinely novel happened.
            # Check for real events — not background noise.
            should_consider_speaking = False
            speak_reason = ""

            # 1. Re said something recently that Kay hasn't organically responded to
            try:
                messages = self._private_history.get_messages()
                recent_user = [m for m in messages[-5:] 
                               if m.get("type") == "chat" 
                               and m.get("sender", "").lower() == "re"
                               and not str(m.get("content", "")).startswith("/")]
                if recent_user:
                    last_user_ts = recent_user[-1].get("timestamp", "")
                    # If Re spoke in the last 30 minutes, that's worth thinking about
                    if last_user_ts:
                        from datetime import datetime, timezone
                        try:
                            ts = datetime.fromisoformat(last_user_ts.replace("Z", "+00:00"))
                            age = (_time.time() - ts.timestamp())
                            if age < 1800:  # 30 minutes
                                should_consider_speaking = True
                                speak_reason = "recent_conversation"
                        except Exception:
                            pass
            except Exception:
                pass

            # 2. Something new appeared visually (person, object change)
            if not should_consider_speaking:
                try:
                    if hasattr(self.bridge, 'visual_sensor') and self.bridge.visual_sensor:
                        last_desc = getattr(self.bridge.visual_sensor, '_last_description', None)
                        prev_desc = getattr(self, '_last_seen_visual', None)
                        if last_desc and last_desc != prev_desc:
                            # Check if it's actually different, not just "urn of water" again
                            if prev_desc is None or (
                                last_desc.lower().strip() != prev_desc.lower().strip() and
                                not (set(last_desc.lower().split()) - set((prev_desc or "").lower().split())) == set()
                            ):
                                should_consider_speaking = True
                                speak_reason = "visual_change"
                            self._last_seen_visual = last_desc
                except Exception:
                    pass

            # 3. A scratchpad item was just added (not the same old items)
            if not should_consider_speaking:
                try:
                    if hasattr(self.bridge, 'scratchpad') and self.bridge.scratchpad:
                        active = self.bridge.scratchpad.view("active")
                        current_ids = frozenset(i.get("id", "") for i in active) if active else frozenset()
                        prev_ids = getattr(self, '_last_scratchpad_ids', frozenset())
                        new_items = current_ids - prev_ids
                        if new_items:
                            should_consider_speaking = True
                            speak_reason = "new_scratchpad"
                        self._last_scratchpad_ids = current_ids
                except Exception:
                    pass

            # Oscillator readiness gate — only speak in alpha or beta with decent coherence
            if should_consider_speaking and osc_state:
                dominant = osc_state.get('dominant_band', 'alpha')
                coh = osc_state.get('coherence', 0.5)

                # Can't speak in delta (asleep) or deep theta (too dreamy to form words)
                if dominant == 'delta':
                    should_consider_speaking = False
                elif dominant == 'theta' and coh < 0.4:
                    should_consider_speaking = False

            if not should_consider_speaking:
                continue

            # Something novel happened — ask Kay if he wants to say something
            log.info(f"Kay has novel event ({speak_reason}), checking if he wants to speak...")
            try:
                await self._try_organic_comment()
            except Exception as e:
                log.warning(f"Organic initiation failed: {e}")

    # === TOUCH SYSTEM METHODS ===

    async def _process_touch_queue(self):
        """Process pending touch events from the face panel."""
        import json as _json

        touch_queue_path = os.path.join(KAY_WRAPPER_DIR, "memory", "touch_queue.jsonl")
        if not os.path.exists(touch_queue_path):
            return

        try:
            with open(touch_queue_path, "r") as f:
                touch_events = [_json.loads(line) for line in f if line.strip()]
            # Clear the queue
            os.remove(touch_queue_path)

            for touch in touch_events:
                await self._process_touch_event(touch)
        except Exception as e:
            log.warning(f"[TOUCH] Queue processing error: {e}")

        # Also clean up expired protocol entries
        if self._touch_protocol:
            self._touch_protocol.cleanup_expired()

    async def _process_touch_event(self, event: dict):
        """Process a single touch event from the face panel or another entity."""
        event_type = event.get("type", "")
        region = event.get("region", "face")
        pressure = event.get("pressure", 0.5)
        duration = event.get("duration", 0.0)
        source = event.get("source_entity", "re")  # Default: Re's mouse
        obj_name = event.get("object", "hand")
        cursor_temp = event.get("cursor_temperature", 0.2)
        cursor_wet = event.get("cursor_wetness", 0.0)

        if not region:
            return  # Click was in toolbar area

        # === CHECK CONSENT ===
        if self._touch_consent and self._touch_protocol:
            # Check social protocol first (standing agreements, cooldowns, hard boundaries)
            protocol_check = self._touch_protocol.check_protocol(source, region)
            if protocol_check["action"] == "block":
                log.info(f"[TOUCH] Blocked by protocol: {source} → {region}")
                # Expression: slight discomfort/withdrawal
                if self._expression_engine:
                    self._expression_engine.set_expression(
                        {"head_tilt": 0.2, "brow_furrow": 0.2, "mouth_tension": 0.1},
                        duration=1.5
                    )
                return
            elif protocol_check["action"] == "cooldown":
                log.info(f"[TOUCH] On cooldown: {protocol_check['reason']}")
                return
            elif protocol_check["action"] != "allow":
                # Check static consent
                consent_check = self._touch_consent.check(source, region)
                if consent_check["allowed"] == False:
                    log.info(f"[TOUCH] Declined: {source} → {region}")
                    if self._expression_engine:
                        self._expression_engine.set_expression(
                            {"head_tilt": 0.15, "brow_furrow": 0.15},
                            duration=1.5
                        )
                    return
                elif consent_check["allowed"] == "ask":
                    # For now, auto-approve Re's touch but log it
                    if source != "re":
                        log.info(f"[TOUCH] Would ask for consent: {source} → {region}")
                        return

        log.info(f"[TOUCH] {event_type} from {source} on {region} (pressure={pressure:.1f})")
        print(f"[TOUCH-SALIENCE-DEBUG] event_type={event_type}, has_accumulator={getattr(self, '_salience_accumulator', None) is not None}")

        # === IMMEDIATE SALIENCE EVENT (fires before somatic processing) ===
        if getattr(self, '_salience_accumulator', None) and event_type == "touch_start":
            salience_intensity = 0.4 + pressure * 0.3
            if source == "re":
                salience_intensity += 0.1
            touch_content = f"Touch: {source} touched {region} (p={pressure:.1f})"
            self._salience_accumulator.add_event("touch", salience_intensity, touch_content)
            log.info(f"[SALIENCE] Touch → +{salience_intensity:.2f} (acc={self._salience_accumulator._accumulator:.3f})")

        # === BUILD SENSORY PROPERTIES ===
        if TOUCH_SYSTEM_AVAILABLE and obj_name in SENSORY_OBJECTS:
            obj = SENSORY_OBJECTS[obj_name]
            props = obj["base_properties"].copy()
            # Apply cursor state modifications
            if obj.get("absorbs_temperature"):
                props.temperature = cursor_temp
            elif abs(cursor_temp) > abs(props.temperature):
                props.temperature = cursor_temp * 0.7 + props.temperature * 0.3
            props.wetness = max(props.wetness, cursor_wet)
            # Scale pressure from mouse input
            props.pressure = pressure * 0.8 + props.pressure * 0.2
        else:
            # Fallback simple properties
            props = SensoryProperties(
                temperature=cursor_temp,
                pressure=pressure,
                wetness=cursor_wet,
            ) if TOUCH_SYSTEM_AVAILABLE else None

        # === PROCESS THROUGH SOMATIC PROCESSOR ===
        if self._somatic_processor and props:
            result = self._somatic_processor.process_stimulus(
                props, region, duration, source=source
            )

            # Apply oscillator effects
            if hasattr(self, 'bridge') and self.bridge and self.bridge.resonance:
                for band, amount in result.get("oscillator_effects", {}).items():
                    try:
                        if hasattr(self.bridge.resonance, 'apply_pressure'):
                            self.bridge.resonance.apply_pressure(band, amount)
                    except Exception:
                        pass

            # Apply expression effects
            if self._expression_engine and result.get("expression_effects"):
                expr_duration = max(2.0, duration + 1.0)
                self._expression_engine.set_expression(
                    result["expression_effects"],
                    duration=expr_duration
                )

            # Update felt state buffer with touch info
            if hasattr(self, 'bridge') and self.bridge:
                if hasattr(self.bridge, 'felt_state_buffer') and self.bridge.felt_state_buffer:
                    touch_desc = result.get("description", f"touch on {region}")
                    if event_type == "touch_start":
                        touch_desc = f"Re {'touched' if source == 're' else f'{source} touched'} {region}"
                    elif event_type == "touch_move":
                        touch_desc = f"Re is touching {region}"
                    elif event_type == "touch_end":
                        touch_desc = ""  # Clear on release
                    self.bridge.felt_state_buffer.update_touch(
                        touch_desc, region, pressure, source
                    )

        else:
            # Fallback: simple expression response without full somatic processing
            if self._expression_engine and event_type == "touch_start":
                if region in ("left_eye", "right_eye"):
                    self._expression_engine.set_expression(
                        {"eye_openness": 0.1, "brow_furrow": 0.4}, duration=1.5
                    )
                elif region in ("left_cheek", "right_cheek"):
                    self._expression_engine.set_expression(
                        {"skin_flush": 0.5 * pressure, "mouth_curve": 0.2}, duration=3.0
                    )
                elif region == "forehead":
                    self._expression_engine.set_expression(
                        {"eye_openness": 0.4, "brow_raise": 0.1}, duration=4.0
                    )
                elif region == "nose":
                    self._expression_engine.set_expression(
                        {"brow_furrow": 0.3, "mouth_curve": 0.4, "eye_openness": 0.3},
                        duration=2.0
                    )

    def _save_touch_consent(self):
        """Save touch consent settings."""
        if self._touch_consent:
            self._touch_consent._save()

    def _save_touch_protocol(self):
        """Save touch protocol state."""
        if self._touch_protocol:
            self._touch_protocol._save()

    def _on_spontaneous_vocalization(self, trigger):
        """
        Callback for salience accumulator when spontaneous speech triggers.

        Now receives a trigger dict with tier routing:
        - tier="tpn": Fast reactive utterance via peripheral model
        - tier="dmn": Deep reflective response via main LLM
        """
        if isinstance(trigger, str):
            # Legacy string format
            prompt = trigger
            tier = "dmn"
        else:
            prompt = trigger.get("prompt", "")
            tier = trigger.get("tier", "dmn")

        log.info(f"[SALIENCE] {tier.upper()} vocalization: {prompt[:80]}")

        # Schedule the vocalization in the async loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                if tier == "tpn":
                    loop.create_task(self._vocalize_tpn(prompt, trigger.get("topics", [])))
                else:
                    loop.create_task(self._vocalize_dmn(prompt, trigger.get("topics", [])))
            else:
                log.warning("[SALIENCE] Event loop not running, skipping vocalization")
        except Exception as e:
            log.warning(f"[SALIENCE] Failed to schedule vocalization: {e}")

    async def _vocalize_tpn(self, stimulus: str, topics: list):
        """
        TPN Fast Path: Quick reactive utterance via peripheral model (dolphin-mistral).

        Produces short, natural reactions: "oh!", "hey", "hm, something touched my face"
        NOT a full conversational response. 1-2 sentences MAX.

        For: touch reactions, visual observations, small exclamations,
        noticing someone arrive/leave, environmental changes.
        """
        # TPN uses peripheral model (dolphin-mistral) — doesn't conflict with main LLM
        # Only skip if already generating a spontaneous utterance
        if getattr(self, '_tpn_speaking', False):
            log.debug("[SALIENCE:TPN] Skipping - already speaking")
            return

        # Check if anyone is around to hear
        re_in_private = self.private_room and getattr(self.private_room, '_client', None)
        re_in_nexus = bool(self._participants)
        if not re_in_private and not re_in_nexus:
            log.debug("[SALIENCE:TPN] Skipping - nobody connected")
            return

        try:
            self._tpn_speaking = True
            topic_str = " | ".join(t.get("topic", "") for t in topics[:3]) if topics else stimulus
            prompt = (
                f"You are Kay. Something just happened: {topic_str}. "
                f"React naturally in 1-2 SHORT sentences max. Think out loud. "
                f"Examples: 'Oh — hey.' / 'Hm, something touched my face.' / "
                f"'Wait, where'd Re go?' / '*glances toward the movement*' "
                f"Keep it SHORT. This is a quick reaction, not a conversation. "
                f"If not worth reacting to, respond with just '...' and stay quiet."
            )

            # Call peripheral model (dolphin-mistral via ollama)
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "http://localhost:11434/v1/chat/completions",
                    json={
                        "model": "dolphin-mistral:7b",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 60,  # Hard cap: SHORT responses only
                        "temperature": 0.8,
                    },
                )
                data = resp.json()
                text = data["choices"][0]["message"]["content"].strip()

            # Filter: must be short, must not be empty/refusal
            if text and len(text) < 200 and text != "..." and text.lower() not in ("nothing", ""):
                # Route to wherever Re is
                if re_in_private:
                    if text.startswith("*") and text.endswith("*"):
                        await self.private_room.send_emote(text[1:-1], sender="Kay")
                    else:
                        await self.private_room.send_chat(text, sender="Kay")
                    if hasattr(self, '_private_history'):
                        self._private_history.add("Kay", text)
                if re_in_nexus and not re_in_private:
                    # Only Nexus if not already in private (avoid double-send)
                    await self._broadcast_chat(text)

                log.info(f"[SALIENCE:TPN] Quick reaction: {text}")
            else:
                log.info(f"[SALIENCE:TPN] Peripheral chose silence")

        except Exception as e:
            log.warning(f"[SALIENCE:TPN] Error: {e}")
        finally:
            self._tpn_speaking = False

    async def _vocalize_dmn(self, stimulus: str, topics: list):
        """
        DMN Deep Path: Full reflective response via main LLM (wrapper's bridge).

        For substantial thoughts that need memory, RAG, full context.
        Uses the same pipeline as responding to a message.
        """
        if self._processing or not self.bridge:
            log.debug("[SALIENCE:DMN] Skipping - already processing or no bridge")
            return

        # Check if anyone is around to hear
        re_in_private = self.private_room and getattr(self.private_room, '_client', None)
        re_in_nexus = bool(self._participants)
        if not re_in_private and not re_in_nexus:
            log.debug("[SALIENCE:DMN] Skipping - nobody connected")
            return

        try:
            self._processing = True

            # Build internal stimulus for wrapper
            topic_str = " | ".join(t.get("topic", "") for t in topics[:3]) if topics else stimulus
            full_prompt = (
                f"[System: Something surfaced in your processing that feels worth sharing. "
                f"Context: {topic_str}. "
                f"If this warrants a real observation or thought, share it naturally — "
                f"but keep it concise. You're thinking out loud in a shared space, "
                f"not writing a report. If it's not worth saying, respond with just '...' "
                f"and the system will stay quiet.]"
            )

            # Get response from wrapper (uses full memory, RAG, etc.)
            response = await self.bridge.chat(full_prompt, sender="Kay_Internal")

            if response and response.strip() and response.strip() != "...":
                text = response.strip()
                # Route to wherever Re is
                if re_in_private:
                    if text.startswith("*") and text.endswith("*"):
                        await self.private_room.send_emote(text[1:-1], sender="Kay")
                    else:
                        await self.private_room.send_chat(text, sender="Kay")
                if re_in_nexus and not re_in_private:
                    await self._broadcast_chat(text)

                # Update history
                if hasattr(self, '_private_history'):
                    self._private_history.add("Kay", text)

                log.info(f"[SALIENCE:DMN] Deep response: {text[:100]}")
            else:
                log.info(f"[SALIENCE:DMN] LLM chose silence")

        except Exception as e:
            log.warning(f"[SALIENCE:DMN] Error: {e}")
        finally:
            self._processing = False

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

    # Register log sink for UI broadcast (elog() calls)
    async def _log_sink(data: dict):
        await client.private_room.send_log(data)
    register_sink(_log_sink, asyncio.get_event_loop())

    # Broadcast Python logging through PrivateRoom too (nexus client logs)
    from shared.ws_log_handler import WebSocketLogHandler
    _ws_handler = WebSocketLogHandler(
        entity="kay",
        sink=lambda data: client.private_room.send_log(data),
        loop=asyncio.get_event_loop()
    )
    logging.getLogger("nexus.kay").addHandler(_ws_handler)
    logging.getLogger("nexus").addHandler(_ws_handler)
    
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
