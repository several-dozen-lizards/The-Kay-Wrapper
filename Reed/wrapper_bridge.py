# wrapper_bridge.py
"""
WrapperBridge: Extracted core processing pipeline for Reed.

Used by:
  - main_bridge.py (terminal mode)
  - nexus_reed.py (Nexus multi-entity mode)

All engine initialization and per-turn processing lives here.
main_bridge.py becomes a thin terminal shell around this bridge.

Phase 3 additions over Kay's bridge:
  - ContinuousSession: Turn logging, checkpoint persistence
  - FlaggingSystem: Real-time flag detection in user/Reed messages
  - CurationInterface: Compression review prompt generation
  - chronicle_integration: Briefing integration
"""

# Entity-prefixed logging
try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"

import asyncio
import os
import json
import time
from agent_state import AgentState
from protocol_engine import ProtocolEngine
from utils.performance import reset_metrics, get_summary
from config import VERBOSE_DEBUG

# Engine imports
from engines.emotion_engine import EmotionEngine
from engines.emotion_extractor import EmotionExtractor
from engines.memory_engine import MemoryEngine
from engines.social_engine import SocialEngine
from engines.temporal_engine import TemporalEngine
from engines.embodiment_engine import EmbodimentEngine
from engines.reflection_engine import ReflectionEngine
from engines.context_manager import ContextManager
from engines.summarizer import Summarizer
from engines.motif_engine import MotifEngine
from engines.momentum_engine import MomentumEngine
from engines.meta_awareness_engine import MetaAwarenessEngine
from engines.relationship_memory import RelationshipMemory
from engines.vector_store import VectorStore
from engines.llm_retrieval import select_relevant_documents, load_full_documents
from engines.document_reader import DocumentReader
from engines.auto_reader import AutoReader
from engines.web_reader import WebReader
from engines.emotional_patterns import EmotionalPatternEngine
from engines.conversation_monitor import ConversationMonitor
from engines.session_summary import SessionSummary, build_session_context_with_summary
from engines.session_summary_generator import SessionSummaryGenerator
from engines.creativity_engine import CreativityEngine
from engines.macguyver_mode import MacGuyverMode
from engines.scratchpad_engine import scratchpad
from engines.memory_deletion import MemoryDeletion
from engines.memory_forest import MemoryForest
from engines.saccade_engine import SaccadeEngine

# Phase 3 engine imports - Continuous session & curation
from engines.real_time_flagging import FlaggingSystem
from engines.curation_interface import CurationInterface
from engines.chronicle_integration import add_chronicle_to_briefing
from engines.continuous_session import ContinuousSession, ConversationTurn

from integrations.llm_integration import get_llm_response
from context_filter import GlyphFilter
from glyph_decoder import GlyphDecoder

# Resonant oscillator core (optional)
try:
    import sys as _resonance_sys
    _wrapper_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _wrapper_root not in _resonance_sys.path:
        _resonance_sys.path.insert(0, _wrapper_root)
    from resonant_core.resonant_integration import ResonantIntegration
    from resonant_core.audio_device_selector import get_best_input_device
    RESONANCE_AVAILABLE = True
    print("[RESONANCE] Resonant core available")
except ImportError as e:
    RESONANCE_AVAILABLE = False
    print(f"{etag('RESONANCE')} Resonant core not available: {e}")

# Consciousness stream (continuous inner experience)
try:
    from engines.consciousness_stream import ConsciousnessStream
    CONSCIOUSNESS_STREAM_AVAILABLE = True
    print("[STREAM] Consciousness stream available")
except ImportError as e:
    CONSCIOUSNESS_STREAM_AVAILABLE = False
    ConsciousnessStream = None
    print(f"{etag('STREAM')} Consciousness stream not available: {e}")

# Felt-state buffer for TPN/DMN architecture
try:
    from shared.felt_state_buffer import FeltStateBuffer
    FELT_STATE_BUFFER_AVAILABLE = True
except ImportError as e:
    FELT_STATE_BUFFER_AVAILABLE = False
    print(f"{etag('BUFFER')} Felt-state buffer not available: {e}")

# Room system (Reed's Sanctum — contextual conversation space)
try:
    from shared.room.room_bridge import RoomBridge
    from shared.room.presets import create_reeds_sanctum
    from shared.room.soul_packet import SoulPacket, capture_soul_packet
    from shared.room.room_manager import get_room_manager
    ROOM_AVAILABLE = True
except ImportError as e:
    ROOM_AVAILABLE = False
    print(f"{etag('ROOM')} Room system not available: {e}")

# Media (optional)
try:
    from media_orchestrator import MediaOrchestrator
    from media_context_builder import MediaContextBuilder
    MEDIA_AVAILABLE = True
except ImportError:
    MEDIA_AVAILABLE = False

try:
    from media_watcher import MediaWatcher, WATCHDOG_AVAILABLE
except ImportError:
    WATCHDOG_AVAILABLE = False
    MediaWatcher = None


async def _update_all(state, engines, user_input, response=None):
    """Run all subsystem updates concurrently."""
    tasks = []
    for eng in engines:
        params = eng.update.__code__.co_varnames[:eng.update.__code__.co_argcount]
        if "user_input" in params and "response" in params:
            tasks.append(asyncio.to_thread(eng.update, state, user_input, response))
        elif "user_input" in params:
            tasks.append(asyncio.to_thread(eng.update, state, user_input))
        else:
            tasks.append(asyncio.to_thread(eng.update, state))
    await asyncio.gather(*tasks)


# ═══════════════════════════════════════════════════════════════════════════
# DMN PRIORITY QUEUE — Salience-aware work scheduling
# ═══════════════════════════════════════════════════════════════════════════

import heapq

class DMNQueue:
    """
    Priority queue for DMN work items. Higher priority = processed first.

    The Salience Network uses this to ensure emotionally important exchanges
    get processed before routine ones, even if they arrived later.

    Priority levels:
        0.0 = skip entirely (phatic responses like "yeah", "ok")
        0.3 = low priority (routine exchange)
        0.5 = normal priority (default)
        0.7 = elevated (questions, emotional content)
        1.0 = urgent (distress, direct emotional questions)
    """

    def __init__(self):
        self._heap = []  # (negative_priority, sequence_num, work_item)
        self._counter = 0
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()

    async def put(self, work_item: dict, priority: float = 0.5):
        """Add work to the queue. Higher priority = processed sooner."""
        async with self._lock:
            self._counter += 1
            # Negate priority because heapq is min-heap (we want max priority first)
            heapq.heappush(self._heap, (-priority, self._counter, work_item))
            self._not_empty.set()

    async def get(self):
        """Get highest-priority work item. Blocks if empty."""
        while True:
            async with self._lock:
                if self._heap:
                    neg_pri, seq, item = heapq.heappop(self._heap)
                    if not self._heap:
                        self._not_empty.clear()
                    return item
            await self._not_empty.wait()

    def qsize(self):
        """Return current queue size."""
        return len(self._heap)

    def task_done(self):
        """Compatibility with asyncio.Queue interface."""
        pass  # No join() support needed


class WrapperBridge:
    """
    Extracted core processing pipeline for Kay/Reed wrappers.
    
    Encapsulates:
    - All engine initialization
    - Pre-processing (memory recall, context building, document retrieval)
    - LLM call
    - Post-processing (emotion extraction, memory encoding, state updates)
    
    Used by both terminal mode (main.py) and Nexus mode (nexus_client.py).
    """
    
    def __init__(self, entity_name="Reed", wrapper_dir=None):
        """Initialize all engines and state."""
        self.entity_name = entity_name
        self.wrapper_dir = wrapper_dir or os.getcwd()
        
        # Core state
        self.state = AgentState()
        self.proto = ProtocolEngine()
        self.turn_count = 0
        self.affect_level = 3.5
        self.session_id = str(int(time.time()))
        self.recent_responses = []  # Last 3 for anti-repetition
        self.new_document_loaded = False

        # Private room reference (set by Nexus for system messages)
        self.private_room = None

        # Phase 3: Continuous session state
        self.continuous_mode = True
        self.curation_pending = False
        self.pending_curation_prompt = None

        # TPN/DMN: Felt-state buffer for async communication
        # Initialized in _init_engines() if resonance is available
        self.felt_state_buffer = None

        # DMN: Background worker queue for voice-mode post-processing
        # The DMN worker processes emotion extraction, memory encoding, etc.
        # in the background while TPN handles rapid conversation turns
        self._dmn_queue = None  # Created when asyncio is available
        self._dmn_task = None   # The persistent worker task

        # Context filter
        self.context_filter = GlyphFilter()
        self.glyph_decoder = GlyphDecoder()

        # Initialize engines
        self._init_engines()
        
        print(f"{etag('BRIDGE')} {entity_name} WrapperBridge initialized")
    
    def _init_engines(self):
        """Initialize all processing engines."""
        # Momentum & meta engines (needed by others)
        self.momentum = MomentumEngine()
        self.motif = MotifEngine()
        self.meta_awareness = MetaAwarenessEngine()

        # Saccade engine (perceptual continuity)
        self.saccade_engine = SaccadeEngine()
        print(f"{etag('BRIDGE')} Saccade engine initialized for perceptual continuity")

        # Conversation monitor
        self.conversation_monitor = ConversationMonitor(config_path="config.json")
        print(f"{etag('SPIRAL')} Conversation monitor ready (embeddings: {self.conversation_monitor.get_stats()['embeddings_available']})")
        
        # Vector store
        print(f"{etag('STARTUP')} Initializing vector store for RAG...")
        try:
            self.vector_store = VectorStore(persist_directory="memory/vector_db")
            print(f"[STARTUP] Vector store ready: {self.vector_store.get_stats()['total_chunks']} chunks available")
        except Exception as e:
            print(f"{etag('WARNING')} Vector store initialization failed: {e}")
            self.vector_store = None
        
        # Document reader
        print(f"{etag('STARTUP')} Initializing document reader...")
        self.doc_reader = DocumentReader(chunk_size=25000)
        print(f"{etag('STARTUP')} Document reader ready")
        
        # Auto-reader
        print(f"{etag('STARTUP')} Initializing auto-reader...")
        def auto_reader_display(role, message):
            if role == "system":
                print(f"\n{message}\n")
            else:
                print(f"{role.capitalize()}: {message}\n")
        self.auto_reader = AutoReader(
            get_llm_response_func=None,  # Set after memory engine
            add_message_func=auto_reader_display,
            memory_engine=None
        )
        print(f"{etag('STARTUP')} Auto-reader ready")
        
        # Web reader
        print(f"{etag('STARTUP')} Initializing web reader...")
        self.web_reader = WebReader(max_chars=15000)
        print(f"{etag('STARTUP')} Web reader ready")

        # Restore document reader state from previous session
        try:
            snapshot_path = os.path.join(self.wrapper_dir, "memory/state_snapshot.json")
            if os.path.exists(snapshot_path):
                with open(snapshot_path, 'r', encoding='utf-8') as f:
                    snapshot = json.load(f)
                    if 'document_reader' in snapshot:
                        self.state.saved_doc_reader_state = snapshot['document_reader']
                        print(f"[DOC READER] Found saved reading position: {self.state.saved_doc_reader_state['doc_name']}")
        except Exception as e:
            print(f"[DOC READER] Could not restore state: {e}")
        
        # Emotion system (two-part: ULTRAMAP rules + self-report extraction)
        self.emotion = EmotionEngine(self.proto, momentum_engine=self.momentum)
        self.emotion_extractor = EmotionExtractor()
        print("[EMOTION] Self-report extraction enabled (descriptive, not prescriptive)")
        
        # Memory engine (with vector store, motif, momentum, emotion)
        self.memory = MemoryEngine(
            self.state.memory,
            motif_engine=self.motif,
            momentum_engine=self.momentum,
            emotion_engine=self.emotion,
            vector_store=self.vector_store
        )
        
        # Link memory engine to auto-reader and state
        self.auto_reader.memory = self.memory
        self.state.memory = self.memory  # CRITICAL: Filter needs access
        
        # Relationship memory
        self.relationship = RelationshipMemory()
        rel_stats = self.relationship.get_stats()
        print(f"{etag('RELATIONSHIP')} Landmarks: {rel_stats['landmarks']}, Patterns: {sum([rel_stats['re_states_tracked'], rel_stats['topics_tracked'], rel_stats['rhythms_tracked']])}")
        
        # Core engines
        self.social = SocialEngine(emotion_engine=self.emotion)
        self.body = EmbodimentEngine(emotion_engine=self.emotion)
        self.temporal = TemporalEngine()
        self.reflection = ReflectionEngine()
        self.summarizer = Summarizer()
        self.context_manager = ContextManager(
            self.memory, self.summarizer,
            momentum_engine=self.momentum,
            meta_awareness_engine=self.meta_awareness
        )

        # Memory forest (hierarchical document trees)
        forest_path = os.path.join(self.wrapper_dir, "memory/forest.json")
        self.forest = MemoryForest.load_from_file(forest_path)
        self.state.forest = self.forest
        print(f"{etag('FOREST')} Loaded {len(self.forest.trees)} document trees")
        
        # Memory deletion
        self.memory_deletion = MemoryDeletion(self.memory)
        
        # Memory engine stats
        print(f"{etag('MEMORY')} Entity graph: {len(self.memory.entity_graph.entities)} entities")
        print(f"{etag('MEMORY')} Multi-layer memory + multi-factor retrieval enabled")
        
        # Creativity system
        from engines import curiosity_engine as curiosity_module
        self.creativity_engine = CreativityEngine(
            scratchpad_engine=scratchpad,
            memory_engine=self.memory,
            entity_graph=self.memory.entity_graph,
            curiosity_engine=curiosity_module,
            momentum_engine=self.momentum
        )
        self.macguyver = MacGuyverMode(
            memory_engine=self.memory,
            scratchpad_engine=scratchpad,
            entity_graph=self.memory.entity_graph
        )
        print(f"{etag('CREATIVITY')} Baseline always active; amplification triggers ready")
        
        # Initialize creativity state
        self.state.creativity_context = None
        self.state.creativity_active = False
        
        # Emotional pattern engine (behavioral tracking)
        data_dir = os.path.join(self.wrapper_dir, "data/emotions")
        self.emotional_patterns = EmotionalPatternEngine(data_dir=data_dir)
        self.state.emotional_patterns = self.emotional_patterns.get_current_state()
        print(f"{etag('EMOTION PATTERNS')} {self.emotional_patterns.get_stats()['emotions_tracked']} tracked emotions")
        
        # Media system (optional)
        self.media_context_builder = MediaContextBuilder(entity_graph=self.memory.entity_graph) if MEDIA_AVAILABLE else None
        self.media_orchestrator = None
        self.media_watcher = None
        
        if MEDIA_AVAILABLE:
            try:
                self.media_orchestrator = MediaOrchestrator(
                    emotional_patterns=self.emotional_patterns,
                    entity_graph=self.memory.entity_graph,
                    vector_store=self.vector_store,
                    media_storage_path=os.path.join(self.wrapper_dir, "memory/media")
                )
                print(f"{etag('MEDIA')} Orchestrator ready: {self.media_orchestrator.get_stats()['total_songs']} songs cached")
                
                if WATCHDOG_AVAILABLE and MediaWatcher:
                    watch_path = os.path.join(self.wrapper_dir, "inputs/media")
                    if os.path.exists(watch_path):
                        self.media_watcher = MediaWatcher(
                            watch_path=watch_path,
                            media_orchestrator=self.media_orchestrator,
                            debounce_seconds=2.0
                        )
                        self.media_watcher.start()
                        existing = self.media_watcher.scan_existing_files()
                        if existing:
                            print(f"{etag('MEDIA')} Processed {len(existing)} existing files")
            except Exception as e:
                print(f"{etag('WARNING')} Media system init failed: {e}")

        # Auto-reader LLM wrapper (needs memory recall per segment)
        self._setup_auto_reader_llm()
        
        # Session summary system
        self.session_summary_storage = SessionSummary()
        self.session_summary_generator = SessionSummaryGenerator(
            llm_func=get_llm_response,
            summary_storage=self.session_summary_storage
        )
        
        summary_stats = self.session_summary_generator.get_stats()
        print(f"{etag('SESSION SUMMARY')} {summary_stats['total_summaries']} past summaries loaded")

        # Room system (Reed's Sanctum — contextual conversation space)
        # May use RoomManager's room if already placed (Nexus mode)
        self.room = None
        self.room_bridge = None
        self._room_initialized = False
        self._current_room_id = None  # Track current room for spatial module selection

        # Check if RoomManager has already placed us (Nexus mode)
        entity_id = self.entity_name.lower().replace(" ", "_")
        room_manager_active = False

        if ROOM_AVAILABLE:
            try:
                rm = get_room_manager()
                placed_room = rm.entity_locations.get(entity_id)
                if rm.rooms and placed_room:
                    # RoomManager has already placed this entity — use its room
                    current_room_id = placed_room
                    self.room = rm.get_room_engine(current_room_id)
                    if self.room:
                        self.room_bridge = RoomBridge(self.room, entity_id=entity_id)
                        self._room_initialized = True
                        self._current_room_id = current_room_id
                        room_manager_active = True
                        print(f"{etag('ROOM')} {self.entity_name} using RoomManager room: {rm.rooms[current_room_id].label} ({len(self.room.objects)} objects)")
                    else:
                        print(f"{etag('ROOM')} RoomManager placed {entity_id} in {current_room_id} but room engine is None")
                else:
                    # Log why we're falling back to standalone mode
                    if not rm.rooms:
                        print(f"{etag('ROOM')} RoomManager has no rooms loaded — using standalone mode")
                    elif not placed_room:
                        print(f"{etag('ROOM')} {entity_id} not placed by RoomManager — using standalone mode")
            except Exception as e:
                print(f"{etag('ROOM')} RoomManager check failed: {e} — using standalone mode")

        # Standalone mode: load default home room (Sanctum for Reed)
        if ROOM_AVAILABLE and not room_manager_active:
            try:
                state_file = os.path.join(os.path.dirname(self.wrapper_dir), "data", "room_state_reed.json")
                os.makedirs(os.path.dirname(state_file), exist_ok=True)
                self.room = create_reeds_sanctum(state_file=state_file)
                # Reed starts at the threshold (new conversation)
                self.room.add_entity(entity_id, self.entity_name,
                                     distance=250, angle_deg=270, z=0)  # South: threshold
                self.room_bridge = RoomBridge(self.room, entity_id=entity_id)
                self._room_initialized = True
                self._current_room_id = "sanctum"
                print(f"{etag('ROOM')} {self.entity_name}'s Sanctum initialized: 6 contextual presences")
            except Exception as e:
                print(f"{etag('ROOM')} Failed to initialize room: {e}")
                self.room = None
                self.room_bridge = None

        # Resonant oscillator core (emotional heartbeat)
        self.resonance = None
        if RESONANCE_AVAILABLE:
            try:
                resonance_state_dir = os.path.join(self.wrapper_dir, "memory/resonant")
                os.makedirs(resonance_state_dir, exist_ok=True)

                # Select best audio input device (USB mic preferred)
                audio_device_index = get_best_input_device(verbose=True)

                # Get room and entity_id for spatial awareness (Phase 2)
                room_for_resonance = self.room if self.room else None
                entity_id_for_resonance = self.entity_name.lower().replace(" ", "_") if self.room else None

                # Determine presence type from current room
                presence_type = self._current_room_id or "sanctum"

                self.resonance = ResonantIntegration(
                    state_dir=resonance_state_dir,
                    enable_audio=True,      # Reed's ear (same mic as Kay)
                    audio_device=audio_device_index,  # Auto-selected mic
                    audio_responsiveness=0.3,
                    memory_layers=self.memory.memory_layers,  # Phase 1: memory as interoception
                    interoception_interval=4.0,               # Heartbeat every 4 seconds
                    room=room_for_resonance,                  # Phase 2: spatial awareness
                    entity_id=entity_id_for_resonance,
                    presence_type=presence_type,              # Use actual room, not hardcoded sanctum
                )
                self.resonance.start()
                spatial_status = f"with spatial ({presence_type})" if room_for_resonance else "no spatial"
                print(f"{etag('RESONANCE')} Oscillator heartbeat started for {self.entity_name} ({spatial_status})")

                # TPN/DMN: Connect felt-state buffer for async state sharing
                if FELT_STATE_BUFFER_AVAILABLE:
                    self.felt_state_buffer = FeltStateBuffer()
                    self.resonance.set_felt_state_buffer(self.felt_state_buffer)
                    print(f"{etag('TPN/DMN')} Felt-state buffer connected for voice-mode fast path")
            except Exception as e:
                print(f"{etag('RESONANCE')} Initialization failed: {e}")
                import traceback
                traceback.print_exc()
                self.resonance = None

        # Consciousness stream (continuous inner experience)
        self.consciousness_stream = None
        if CONSCIOUSNESS_STREAM_AVAILABLE and self.resonance:
            try:
                self.consciousness_stream = ConsciousnessStream(
                    resonance=self.resonance,
                    room_bridge=self.room_bridge if hasattr(self, 'room_bridge') else None,
                    peripheral_router=None,  # Set later if available
                    visual_sensor=None,      # Reed uses SOMA from Kay, not own camera
                    entity_name=self.entity_name.lower(),
                )
                self.consciousness_stream.start()
                print(f"{etag('STREAM')} Consciousness stream started for {self.entity_name}")

                # Wire up memory engine for sleep pressure
                if hasattr(self, 'memory') and self.memory:
                    self.memory.set_consciousness_stream(self.consciousness_stream)

            except Exception as e:
                print(f"{etag('STREAM')} Initialization failed: {e}")
                import traceback
                traceback.print_exc()
                self.consciousness_stream = None

        # Phase 3: Continuous session, flagging, curation
        print(f"{etag('STARTUP')} Initializing continuous session system...")
        from pathlib import Path as _Path
        session_data_dir = _Path(os.path.join(self.wrapper_dir, "reed_session_logs"))
        session_data_dir.mkdir(exist_ok=True)
        self.continuous_session = ContinuousSession(data_dir=session_data_dir)
        self.curation_interface = CurationInterface(self.continuous_session)
        self.flagging_system = FlaggingSystem(self.continuous_session)
        
        # Check for existing checkpoint to resume
        checkpoints = sorted(self.continuous_session.checkpoint_dir.glob("checkpoint_*.json"))
        if checkpoints:
            self.continuous_session.load_from_checkpoint(checkpoints[-1])
            print(f"[CONTINUOUS] Resumed from checkpoint: {self.continuous_session.turn_counter} turns loaded")
        else:
            self.continuous_session.start_session()
            print(f"[CONTINUOUS] New session started: {self.continuous_session.session_id}")
    
    def _setup_auto_reader_llm(self):
        """Create LLM wrapper for auto-reader with memory recall per segment."""
        bridge = self  # Capture reference for closure
        
        def auto_reader_get_response(prompt, agent_state):
            """LLM wrapper that recalls memories for each document segment."""
            bridge.memory.recall(agent_state, prompt)
            
            reading_context = {
                "user_input": prompt,
                "recalled_memories": getattr(agent_state, 'last_recalled_memories', []),
                "emotional_state": {"cocktail": getattr(agent_state, 'emotional_cocktail', {})},
                "emotional_patterns": getattr(agent_state, 'emotional_patterns', {}),
                "recent_context": [],
                "momentum_notes": getattr(agent_state, 'momentum_notes', []),
                "meta_awareness_notes": getattr(agent_state, 'meta_awareness_notes', []),
                "consolidated_preferences": getattr(agent_state, 'consolidated_preferences', {}),
                "preference_contradictions": getattr(agent_state, 'preference_contradictions', []),
                "rag_chunks": [],
                "relationship_context": bridge.relationship.build_relationship_context(),
                "turn_count": bridge.turn_count,
                "recent_responses": bridge.recent_responses,
                "session_id": bridge.session_id
            }
            
            response = get_llm_response(
                reading_context,
                affect=bridge.affect_level,
                session_context={"turn_count": bridge.turn_count, "session_id": bridge.session_id}
            )
            return bridge.body.embody_text(response, agent_state)
        
        self.auto_reader.get_response = auto_reader_get_response
    
    async def startup(self):
        """Load session context and prepare for conversation."""
        self.session_summary_generator.start_session()
        
        # Get past session context
        self.past_session_context = self.session_summary_generator.get_startup_context()
        if self.past_session_context:
            last_summary = self.session_summary_storage.get_most_recent()
            if last_summary:
                from engines.session_summary import get_time_ago
                time_ago = get_time_ago(last_summary['timestamp'])
                print(f"\n{'='*60}")
                print(f"NOTE FROM PAST-YOU ({last_summary['type'].title()}, {time_ago}):")
                print(last_summary['content'][:500])
                if len(last_summary['content']) > 500:
                    print("...")
                print(f"{'='*60}\n")
        
        print(f"{etag('BRIDGE')} {self.entity_name} ready for conversation.\n")
        return self.past_session_context

    def process_command(self, user_input):
        """Handle slash commands. Returns (handled: bool, response: str or None)."""
        cmd = user_input.lower().strip()
        
        if cmd.startswith("/affect "):
            try:
                self.affect_level = float(user_input.split(" ", 1)[1])
                return True, f"(Affect set to {self.affect_level:.1f} / 5)"
            except Exception:
                return True, "(Invalid affect value)"
        
        if cmd == "/forest":
            return True, "\n" + self.forest.get_forest_overview()
        
        if cmd.startswith("/tree "):
            tree_name = user_input[6:].strip()
            tree = self.forest.get_tree_by_title(tree_name)
            if tree:
                return True, "\n" + self.forest.navigate_tree(tree.doc_id)
            else:
                lines = [f"\n❌ No tree found matching: {tree_name}", "\nAvailable trees:"]
                for t in self.forest.trees.values():
                    lines.append(f"  - {t.title}")
                return True, "\n".join(lines)
        
        if cmd.startswith("/import "):
            filepath = user_input[8:].strip()
            try:
                from memory_import.kay_reader import import_document_as_kay
                doc_id = import_document_as_kay(filepath, self.memory, self.forest)
                return True, f"\n✅ Document imported! Tree ID: {doc_id}\nUse /forest to see all trees"
            except Exception as e:
                import traceback
                traceback.print_exc()
                return True, f"\n❌ Import failed: {e}"
        
        if cmd.startswith("/forget "):
            pattern = user_input[8:].strip()
            if not pattern:
                return True, "\nUsage: /forget <pattern>"
            result = self.memory_deletion.forget_memory(pattern, reason="User requested deletion")
            msg = f"\n✅ Deleted {result['deleted']} memories matching: '{pattern}'"
            if result['protected'] > 0:
                msg += f"\n   Protected {result['protected']} important/identity memories"
            return True, msg
        
        if cmd.startswith("/corrupt "):
            pattern = user_input[9:].strip()
            if not pattern:
                return True, "\nUsage: /corrupt <pattern>"
            count = self.memory_deletion.flag_as_corrupted(pattern, reason="User marked as corrupted")
            return True, f"\n✅ Flagged {count} memories as corrupted: '{pattern}'"
        
        if cmd.startswith("/prune"):
            parts = user_input.split()
            days, layer = 90, None
            if len(parts) > 1:
                try: days = int(parts[1])
                except ValueError: layer = parts[1]
            if len(parts) > 2:
                layer = parts[2]
            result = self.memory_deletion.prune_old_memories(max_age_days=days, layer_filter=layer)
            msg = f"\n✅ Pruned {result['pruned']} old memories (>{days} days)"
            if result['protected'] > 0:
                msg += f"\n   Protected {result['protected']} important memories"
            return True, msg
        
        if cmd == "/deletions":
            history = self.memory_deletion.get_deletion_history(limit=10)
            if not history:
                return True, "\nNo deletion history"
            lines = ["\n" + "="*70, "RECENT DELETIONS", "="*70]
            for i, record in enumerate(reversed(history), 1):
                lines.append(f"\n{i}. Pattern: '{record['pattern']}' | Reason: {record['reason']} | Count: {record['count']}")
            return True, "\n".join(lines)
        
        if cmd.startswith("/github"):
            from services.github_service import handle_github_command
            command = user_input[7:].strip()
            return True, f"\n{handle_github_command(command)}"
        
        # === MEMORY CURATION COMMANDS (from Godot UI) ===
        if cmd.startswith("/memory"):
            return self._handle_memory_command(user_input)
        
        return False, None
    
    def _handle_memory_command(self, user_input: str):
        """Handle /memory subcommands for curation UI."""
        parts = user_input.strip().split(None, 2)
        subcmd = parts[1].lower() if len(parts) > 1 else "stats"
        arg = parts[2] if len(parts) > 2 else ""
        
        if subcmd in ("stats", "list"):
            return True, self._memory_stats()
        elif subcmd == "search":
            if not arg:
                return True, "\nUsage: /memory search <query>"
            return True, self._memory_search(arg)
        elif subcmd == "consolidate":
            return True, self._memory_consolidate()
        elif subcmd == "prune":
            days = 90
            if arg:
                try: days = int(arg)
                except ValueError: pass
            result = self.memory_deletion.prune_old_memories(max_age_days=days)
            msg = f"\n✅ Pruned {result['pruned']} old memories (>{days} days)"
            if result['protected'] > 0:
                msg += f"\n   Protected {result['protected']} important memories"
            return True, msg
        elif subcmd == "contradictions":
            return True, self._memory_contradictions()
        else:
            return True, f"\nUnknown /memory subcommand: {subcmd}\nAvailable: stats, search, consolidate, prune, contradictions"
    
    def _memory_stats(self) -> str:
        """Return memory system overview."""
        lines = ["\n" + "="*60, "📋 MEMORY OVERVIEW", "="*60]
        layer_stats = self.memory.memory_layers.get_layer_stats()
        w = layer_stats["working"]
        lt = layer_stats["long_term"]
        lines.append(f"\n🔵 Working memory: {w['count']}/{w['capacity']} (avg strength: {w['avg_strength']:.2f})")
        lines.append(f"🟣 Long-term memory: {lt['count']} (avg strength: {lt['avg_strength']:.2f})")
        all_mems = self.memory.memory_layers.working_memory + self.memory.memory_layers.long_term_memory
        facts = sum(1 for m in all_mems if m.get("memory_type") == "extracted_fact")
        turns = sum(1 for m in all_mems if m.get("memory_type") == "full_turn")
        identity = sum(1 for m in all_mems if m.get("layer") == "identity")
        lines.append(f"\n📊 By type:  Facts: {facts}  |  Turns: {turns}  |  Identity: {identity}")
        eg = self.memory.entity_graph
        lines.append(f"\n🕸️ Entity graph: {len(eg.entities)} entities, {len(eg.relationships)} relationships")
        contradiction_count = 0
        for entity in eg.entities.values():
            if hasattr(entity, 'contradiction_resolution'):
                for attr, status in entity.contradiction_resolution.items():
                    if not status.get("resolved", False):
                        contradiction_count += 1
        lines.append(f"⚠️ Active contradictions: {contradiction_count}")
        if hasattr(self.memory, 'vector_store') and self.memory.vector_store:
            lines.append(f"\n📚 Vector store: {self.memory.vector_store.count()} chunks")
        lines.append("="*60)
        return "\n".join(lines)
    
    def _memory_search(self, query: str) -> str:
        """Search memories by text content and entity attributes."""
        query_lower = query.lower()
        results = []
        all_mems = self.memory.memory_layers.working_memory + self.memory.memory_layers.long_term_memory
        for mem in all_mems:
            content = mem.get("content", mem.get("text", ""))
            if isinstance(content, dict):
                content = str(content)
            if query_lower in content.lower():
                results.append(mem)
        entity_hits = []
        for name, entity in self.memory.entity_graph.entities.items():
            if query_lower in name.lower():
                entity_hits.append((name, entity))
            else:
                for attr, values in entity.attributes.items():
                    for val_entry in values:
                        val = str(val_entry[0]) if isinstance(val_entry, (list, tuple)) else str(val_entry)
                        if query_lower in val.lower():
                            entity_hits.append((name, entity))
                            break
        lines = [f"\n🔍 Search: '{query}'", "="*60]
        if entity_hits:
            lines.append(f"\n🕸️ Entity matches ({len(entity_hits)}):")
            for name, entity in entity_hits[:10]:
                attrs = []
                for attr, values in entity.attributes.items():
                    latest = values[-1] if values else None
                    if latest:
                        val = latest[0] if isinstance(latest, (list, tuple)) else latest
                        attrs.append(f"{attr}={val}")
                lines.append(f"  • {name}: {', '.join(attrs[:5])}")
        if results:
            results.sort(key=lambda m: m.get("added_timestamp", ""), reverse=True)
            lines.append(f"\n💾 Memory matches ({len(results)}, showing newest 15):")
            for mem in results[:15]:
                mtype = mem.get("memory_type", "?")
                ts = mem.get("added_timestamp", "?")[:16]
                content = mem.get("content", mem.get("text", ""))
                if isinstance(content, dict):
                    content = content.get("user", "") + " → " + content.get("response", "")
                preview = str(content)[:120].replace("\n", " ")
                strength = mem.get("current_strength", 0)
                lines.append(f"  [{ts}] ({mtype}, s={strength:.2f}) {preview}")
        if not results and not entity_hits:
            lines.append("\n  No matches found.")
        lines.append(f"\n{'='*60}")
        return "\n".join(lines)
    
    def _memory_consolidate(self) -> str:
        """Deduplicate near-identical semantic facts."""
        all_mems = self.memory.memory_layers.long_term_memory
        facts = [m for m in all_mems if m.get("memory_type") == "extracted_fact"]
        if not facts:
            return "\n✅ No semantic facts to consolidate."
        by_category = {}
        for f in facts:
            cat = f.get("category", "unknown")
            by_category.setdefault(cat, []).append(f)
        duplicates_found = 0
        duplicates_removed = 0
        for cat, cat_facts in by_category.items():
            if len(cat_facts) < 2:
                continue
            seen = {}
            to_remove = []
            for mem in cat_facts:
                content = str(mem.get("content", mem.get("text", "")))
                normalized = " ".join(content.lower().split())
                found_dup = False
                for seen_norm, seen_mem in seen.items():
                    if normalized == seen_norm:
                        duplicates_found += 1
                        if mem.get("importance_score", 0) > seen_mem.get("importance_score", 0):
                            to_remove.append(seen_mem)
                            seen[seen_norm] = mem
                        else:
                            to_remove.append(mem)
                        found_dup = True
                        break
                    elif len(normalized) > 20 and len(seen_norm) > 20:
                        if normalized in seen_norm:
                            to_remove.append(mem)
                            duplicates_found += 1
                            found_dup = True
                            break
                        elif seen_norm in normalized:
                            to_remove.append(seen_mem)
                            seen[normalized] = mem
                            del seen[seen_norm]
                            duplicates_found += 1
                            found_dup = True
                            break
                if not found_dup:
                    seen[normalized] = mem
            for mem in to_remove:
                if mem in self.memory.memory_layers.long_term_memory:
                    self.memory.memory_layers.long_term_memory.remove(mem)
                    duplicates_removed += 1
        if duplicates_removed > 0:
            self.memory.memory_layers._save_to_disk()
        lines = ["\n" + "="*60, "🔄 CONSOLIDATION RESULTS", "="*60]
        lines.append(f"\n  Scanned: {len(facts)} semantic facts across {len(by_category)} categories")
        lines.append(f"  Duplicates found: {duplicates_found}")
        lines.append(f"  Removed: {duplicates_removed}")
        lines.append(f"  Remaining: {len(self.memory.memory_layers.long_term_memory)} long-term memories")
        lines.append("="*60)
        return "\n".join(lines)
    
    def _memory_contradictions(self) -> str:
        """Show active entity contradictions."""
        eg = self.memory.entity_graph
        lines = ["\n" + "="*60, "⚠️ ACTIVE CONTRADICTIONS", "="*60]
        count = 0
        for name, entity in eg.entities.items():
            if not hasattr(entity, 'contradiction_resolution'):
                continue
            for attr, status in entity.contradiction_resolution.items():
                if status.get("resolved", False):
                    continue
                count += 1
                values = entity.attributes.get(attr, [])
                val_strs = []
                for v in values[-5:]:
                    val = v[0] if isinstance(v, (list, tuple)) else v
                    val_strs.append(str(val)[:60])
                lines.append(f"\n  {name}.{attr}:")
                for vs in val_strs:
                    lines.append(f"    → {vs}")
        if count == 0:
            lines.append("\n  No active contradictions.")
        else:
            lines.append(f"\n  Total: {count} unresolved")
        lines.append("="*60)
        return "\n".join(lines)

    def _is_fast_twitch(self, user_input: str) -> bool:
        """
        Determine if a message is lightweight enough to skip heavy pipeline stages.
        
        Fast-twitch messages: short, casual, no URLs, no complex questions,
        no emotional crisis signals. These get a faster response with minimal
        context instead of the full memory/RAG/document pipeline.
        
        Returns True if message should use the fast path.
        """
        # Never fast-twitch on first turn (need full context setup)
        if self.turn_count <= 1:
            return False
        
        text = user_input.strip()
        word_count = len(text.split())
        
        # Length gate: messages over ~40 words are probably substantial
        if word_count > 40:
            return False
        
        # URLs always need full pipeline (web extraction)
        if self.web_reader.has_url(text):
            return False
        
        # Commands need full pipeline
        if text.startswith('/'):
            return False
        
        # Questions with depth markers need full pipeline
        depth_markers = [
            "explain", "why do", "how does", "what about", "tell me about",
            "remember when", "think about", "analyze", "compare", "describe",
            "what happened", "help me", "can you", "figure out", "work on",
            "let's talk about", "read this", "look at this", "import"
        ]
        text_lower = text.lower()
        if any(marker in text_lower for marker in depth_markers):
            return False
        
        # Emotional crisis signals always get full pipeline
        crisis_markers = [
            "i'm not okay", "i can't", "help me", "i'm scared",
            "i'm crying", "i want to die", "i'm breaking", "panic"
        ]
        if any(marker in text_lower for marker in crisis_markers):
            return False
        
        # Document navigation needs full pipeline
        doc_markers = ["section", "chapter", "continue reading", "next part", "go back"]
        if any(marker in text_lower for marker in doc_markers):
            return False
        
        # If we get here: short, no URLs, no commands, no depth, no crisis
        # This is a "lol", "nice", "omg [cat]", "that's hilarious" type message
        return word_count <= 25 or (word_count <= 40 and '?' not in text)

    async def process_message(self, user_input, source="terminal", voice_mode=False):
        """
        Full processing pipeline: pre-processing → LLM call → post-processing.

        Args:
            user_input: The user's message text
            source: "terminal" or "nexus" (for logging/routing)
            voice_mode: If True, optimize for low-latency voice response

        Returns:
            str: The entity's response text
        """
        import re
        
        # === PRE-PROCESSING ===
        self.turn_count += 1
        reset_metrics()
        turn_start_time = time.time()
        
        # Phase 3: Continuous session - track user turn
        if self.continuous_mode:
            # Check for user-requested flags
            user_flagged = self.flagging_system.check_for_flag(user_input)
            if user_flagged:
                print(f"[FLAG] User flagged this moment: {user_flagged}")
            
            # Add user turn to continuous session
            self.continuous_session.add_turn(
                role="user",
                content=user_input,
                token_count=len(user_input.split()),  # Approximate
                emotional_weight=0.5,  # Default
                flagged=bool(user_flagged),
                tags=["user_input"]
            )
            
            # Check if compression review needed
            if self.continuous_session.needs_compression_review():
                print("[CONTINUOUS] Compression threshold reached - triggering curation review")
                curation_prompt = self.curation_interface.generate_review_prompt()
                if curation_prompt:
                    self.pending_curation_prompt = curation_prompt
                    self.curation_pending = True
        
        # === FAST-TWITCH CHECK ===
        # Short casual messages skip heavy pipeline (memory recall, RAG, doc retrieval)
        if self._is_fast_twitch(user_input):
            print(f"[FAST-TWITCH] Lightweight message detected — using fast path")
            
            # Minimal context: just recent turns + emotional state + user input
            working_turns = self.context_manager.recent_turns[-4:] if hasattr(self.context_manager, 'recent_turns') else []
            relationship_context = self.relationship.build_relationship_context()
            
            fast_context = {
                "recalled_memories": [],
                "emotional_state": {"cocktail": dict(self.state.emotional_cocktail) if hasattr(self.state, 'emotional_cocktail') else {}},
                "emotional_patterns": getattr(self.state, 'emotional_patterns', {}),
                "user_input": user_input,
                "recent_context": working_turns,
                "momentum_notes": getattr(self.state, 'momentum_notes', []),
                "meta_awareness_notes": [],
                "consolidated_preferences": getattr(self.state, 'consolidated_preferences', {}),
                "preference_contradictions": [],
                "rag_chunks": [],
                "relationship_context": relationship_context,
                "web_content": "",
                "media_context": "",
                "past_session_note": "",
                "turn_count": self.turn_count,
                "recent_responses": self.recent_responses,
                "session_id": self.session_id,
                "context_metrics": {"tier": "fast_twitch", "memory_count": 0, "rag_count": 0, "turn_count": len(working_turns)},
                "image_context": "",
                "active_images": []
            }
            
            # LLM call with minimal context
            session_context = {"turn_count": self.turn_count, "session_id": self.session_id}
            try:
                reply = get_llm_response(fast_context, affect=self.affect_level, session_context=session_context, use_cache=True)
            except Exception as e:
                print(f"{etag('ERROR')} Fast-twitch LLM call failed: {e}")
                reply = "[Error: Could not generate response]"
            
            reply = self.body.embody_text(reply, self.state)
            
            # Light post-processing: emotion extraction + turn tracking (skip memory encoding, reflection, etc.)
            extracted_emotions = self.emotion_extractor.extract_emotions(reply)
            self.emotion_extractor.store_emotional_state(extracted_emotions, self.state.emotional_cocktail)

            # Feed emotions to resonance oscillator
            if self.resonance:
                emotion_labels = extracted_emotions.get('primary_emotions', [])
                if emotion_labels:
                    self.resonance.feed_response_emotions(extracted_emotions)

            if self.media_orchestrator:
                self.media_context_builder.add_message("reed", reply, self.turn_count)
            self.conversation_monitor.add_turn("reed", reply)
            self.context_manager.update_turns(user_input, reply)
            
            self.recent_responses.append(reply)
            if len(self.recent_responses) > 3:
                self.recent_responses.pop(0)
            
            # Phase 3: track assistant turn
            if self.continuous_mode:
                self.continuous_session.add_turn(
                    role="reed", content=reply,
                    token_count=len(reply.split()),
                    emotional_weight=extracted_emotions.get('intensity', 0.5) if extracted_emotions else 0.5,
                    flagged=False, tags=["reed_response", "fast_twitch"]
                )
            
            elapsed = time.time() - turn_start_time
            print(f"[FAST-TWITCH] Response generated in {elapsed:.1f}s (skipped memory/RAG/docs)")
            return reply
        
        # === FULL PIPELINE (non-fast-twitch) ===

        # Web content extraction
        web_content_context = ""
        if self.web_reader.has_url(user_input):
            print("[WEB_READER] URL detected, fetching...")
            formatted_content, results = self.web_reader.process_message_urls(user_input)
            if formatted_content:
                web_content_context = formatted_content
                self.state.web_content = formatted_content
                for r in results:
                    if r.error:
                        print(f"[WEB_READER] Error: {r.error}")
                    else:
                        print(f"[WEB_READER] Fetched: '{r.title}' ({r.word_count} words)")
        else:
            self.state.web_content = None
        
        # Media context
        media_context_injection = ""
        if self.media_orchestrator:
            self.media_context_builder.add_message("user", user_input, self.turn_count)
            conv_context = self.media_context_builder.extract_conversation_context()
            self.media_orchestrator.update_conversation_context(
                topic=conv_context.get("topic"),
                entities=conv_context.get("entities"),
                re_state=conv_context.get("re_emotional_context")
            )
            should_inject, injection_text = self.media_context_builder.should_inject_media_context(
                self.media_orchestrator, user_input
            )
            if should_inject and injection_text:
                media_context_injection = injection_text
                print(f"{etag('MEDIA')} Context injection ready ({len(injection_text)} chars)")
        
        # Fact extraction & memory recall
        # In voice mode: defer entity extraction to DMN, skip RAG and peripheral updates
        
        # === PHASE-LOCKED MEMORY RETRIEVAL: Update current PLV before recall ===
        if self.felt_state_buffer:
            _fs = self.felt_state_buffer.get_snapshot()
            self.memory.current_plv = {
                "theta_gamma": _fs.theta_gamma_plv,
                "beta_gamma": _fs.beta_gamma_plv,
                "coherence": _fs.global_coherence,
            }
        
        if not voice_mode:
            self.memory.extract_and_store_user_facts(self.state, user_input)
            self.memory.recall(self.state, user_input)
            await _update_all(self.state, [self.social, self.temporal, self.body, self.motif], user_input)
        else:
            # VOICE MODE: Minimal pre-LLM processing for speed
            # Entity extraction deferred to DMN worker
            print(f"{etag('VOICE')} Skipping pre-LLM entity extraction (deferred to DMN)")
            # Memory recall without RAG (include_rag=False saves ~1s)
            self.memory.recall(self.state, user_input, include_rag=False)
            print(f"{etag('VOICE')} Memory recall (no RAG)")
            # Peripheral updates skipped — using cached state
            print(f"{etag('VOICE')} Peripheral updates skipped (using cached state)")

        # LLM document retrieval — SKIP in voice mode
        if not voice_mode:
            print("[LLM Retrieval] Selecting relevant documents...")
            emotional_state_str = ", ".join([
                f"{emotion} ({data['intensity']:.1f})"
                for emotion, data in sorted(
                    self.state.emotional_cocktail.items(),
                    key=lambda x: x[1]['intensity'] if isinstance(x[1], dict) else x[1],
                    reverse=True
                )[:3]
            ]) if self.state.emotional_cocktail else "neutral"

            selected_doc_ids = select_relevant_documents(
                query=user_input,
                emotional_state=emotional_state_str,
                max_docs=3
            )
            selected_documents = load_full_documents(selected_doc_ids)

            if selected_documents:
                print(f"[LLM Retrieval] Loaded {len(selected_documents)} documents")
                self.state.selected_documents = selected_documents
            else:
                print("[LLM Retrieval] No relevant documents found")
                self.state.selected_documents = []
        else:
            print(f"{etag('VOICE')} LLM retrieval skipped")
            self.state.selected_documents = []
            selected_documents = []

        # Build filtered context
        try:
            selected_memories = getattr(self.state, 'last_recalled_memories', [])
            filtered_context = {
                "selected_memories": selected_memories,
                "emotional_state": dict(self.state.emotional_cocktail) if hasattr(self.state, 'emotional_cocktail') else {},
                "recent_turns_needed": 0,
                "mood_glyphs": "",
                "conflict_warning": ""
            }
            
            # Recent turns integration
            recent_turns_needed = filtered_context.get("recent_turns_needed", 0)
            if recent_turns_needed > 0 and self.context_manager.recent_turns:
                recent_turns = self.context_manager.recent_turns[-recent_turns_needed:]
                recent_memories = [{
                    'fact': f"[Recent Turn -{len(recent_turns) - i}]",
                    'user_input': turn.get('user', ''),
                    'response': turn.get('kay', ''),
                    'type': 'recent_turn',
                    'is_recent_context': True,
                    'turn_index': self.turn_count - (len(recent_turns) - i)
                } for i, turn in enumerate(recent_turns)]
                
                # Deduplicate
                selected_indices = {m.get('turn_index') for m in filtered_context["selected_memories"] if m.get('turn_index') is not None}
                deduped = [m for m in recent_memories if m.get('turn_index') not in selected_indices]
                filtered_context["selected_memories"] = deduped + filtered_context["selected_memories"]

            # Document chunking for RAG
            if selected_documents:
                rag_chunks = []
                for doc in selected_documents:
                    doc_text = doc['full_text']
                    doc_filename = doc['filename']
                    doc_id = doc.get('doc_id', 'unknown')
                    
                    if len(doc_text) > 30000:
                        # Large doc - use chunked reading
                        if not self.doc_reader.current_doc or self.doc_reader.current_doc.get('id') != doc_id:
                            num_chunks = self.doc_reader.load_document(doc_text, doc_filename, doc_id)
                            saved_state = getattr(self.state, 'saved_doc_reader_state', None)
                            if saved_state and saved_state.get('doc_id') == doc_id:
                                self.doc_reader.restore_state(saved_state, doc_text)
                                self.state.saved_doc_reader_state = None
                            elif num_chunks > 1:
                                self.new_document_loaded = True
                        
                        chunk = self.doc_reader.get_current_chunk()
                        if chunk:
                            prev_comment = f"\n💭 Previous comment: \"{chunk['previous_comment']}\"\n" if chunk['previous_comment'] else ""
                            chunk_text = f"Document: {chunk['doc_name']} (Section {chunk['position']} of {chunk['total']})\n{prev_comment}\n{chunk['text']}"
                            rag_chunks.append({'source_file': doc_filename, 'text': chunk_text, 'is_chunked': True, 'chunk_position': chunk['position'], 'chunk_total': chunk['total']})
                    else:
                        rag_chunks.append({'source_file': doc_filename, 'text': doc_text, 'is_chunked': False})
                
                filtered_context['rag_chunks'] = filtered_context.get('rag_chunks', []) + rag_chunks
            
            # Budget management
            from engines.context_budget import get_budget_manager
            budget_mgr = get_budget_manager()
            estimated_chars = len(str(filtered_context.get("selected_memories", []))) + len(str(filtered_context.get("rag_chunks", [])))
            has_images = len(getattr(self.state, 'active_images', [])) > 0
            limits = budget_mgr.get_adaptive_limits(estimated_chars, has_images=has_images)
            
            # Apply limits
            sel_mems = filtered_context.get("selected_memories", [])
            if len(sel_mems) > limits['memory_limit']:
                from engines.context_budget import prioritize_memories
                sel_mems = prioritize_memories(sel_mems, limits['memory_limit'], self.turn_count)
            
            rag = filtered_context.get("rag_chunks", [])
            if len(rag) > limits['rag_limit']:
                from engines.context_budget import prioritize_rag_chunks
                rag = prioritize_rag_chunks(rag, limits['rag_limit'], user_input)
            
            working_turns = self.context_manager.recent_turns[-limits['working_turns']:] if hasattr(self.context_manager, 'recent_turns') else []
            
            # Build relationship context
            relationship_context = self.relationship.build_relationship_context()
            
            # Session note (first turn only)
            past_session_note = ""
            if self.turn_count == 1 and hasattr(self, 'past_session_context') and self.past_session_context:
                last_summary = self.session_summary_storage.get_most_recent()
                if last_summary:
                    past_session_note = last_summary['content']

            # Assemble final prompt context
            context_metrics = {
                "tier": limits['tier'],
                "estimated_tokens": estimated_chars // 4,
                "memory_count": len(sel_mems),
                "rag_count": len(rag),
                "turn_count": len(working_turns),
                "image_count": 1 if has_images else 0
            }
            
            filtered_prompt_context = {
                "recalled_memories": sel_mems,
                "emotional_state": {"cocktail": filtered_context.get("emotional_state", {})},
                "emotional_patterns": getattr(self.state, 'emotional_patterns', {}),
                "user_input": user_input,
                "recent_context": working_turns,
                "momentum_notes": getattr(self.state, 'momentum_notes', []),
                "meta_awareness_notes": getattr(self.state, 'meta_awareness_notes', []),
                "consolidated_preferences": getattr(self.state, 'consolidated_preferences', {}),
                "preference_contradictions": getattr(self.state, 'preference_contradictions', []),
                "rag_chunks": rag,
                "relationship_context": relationship_context,
                "web_content": web_content_context,
                "media_context": media_context_injection,
                "past_session_note": past_session_note,
                "turn_count": self.turn_count,
                "recent_responses": self.recent_responses,
                "session_id": self.session_id,
                "context_metrics": context_metrics,
                "image_context": getattr(self.context_manager, 'get_image_context_block', lambda: "")(),
                "active_images": self.context_manager.get_active_images() if hasattr(self.context_manager, 'get_active_images') else []
            }
        
        except Exception as e:
            print(f"{etag('ERROR')} Filter system failed: {e}")
            import traceback
            traceback.print_exc()
            filtered_prompt_context = self.context_manager.build_context(self.state, user_input)
        
        # Spiral detection — SKIP in voice mode (saves ~2s embedding + LLM analysis)
        if not voice_mode:
            spiral_analysis = self.conversation_monitor.add_turn("user", user_input)
            if spiral_analysis:
                spiral_injection = self.conversation_monitor.get_disengagement_prompt(spiral_analysis)
                print(f"{etag('SPIRAL')} Detected! Confidence: {spiral_analysis.confidence:.2f}")
                filtered_prompt_context["spiral_context"] = spiral_injection
        else:
            print(f"{etag('VOICE')} Spiral detection skipped")
        
        # Creativity injection (from previous turn)
        if hasattr(self.state, 'creativity_context') and self.state.creativity_context:
            filtered_prompt_context["creativity_context"] = self.state.creativity_context
            self.state.creativity_active = True
            self.state.creativity_context = None
        else:
            self.state.creativity_active = False
        
        self.creativity_engine.update_turn(self.turn_count)

        # === SACCADE ENGINE (Perceptual Continuity) — SKIP in voice mode ===
        if not voice_mode:
            try:
                saccade_block = self.saccade_engine.process_turn(self.state, self.turn_count)
                if saccade_block:
                    filtered_prompt_context["saccade_block"] = saccade_block
                    print(f"{etag('SACCADE')} Turn {self.turn_count}: block generated ({len(saccade_block)} chars)")
            except Exception as e:
                print(f"{etag('SACCADE')} Error (non-fatal): {e}")
        else:
            print(f"{etag('VOICE')} Saccade skipped")

        # Phase 3: Inject curation prompt if pending
        if self.curation_pending and self.pending_curation_prompt:
            filtered_prompt_context["curation_context"] = self.pending_curation_prompt
            print("[CURATION] Injected curation review prompt into context")

        # Inject resonant oscillator context (audio + heartbeat + body state)
        if self.resonance:
            # In voice mode, use felt_state_buffer for fast path (skip peripheral model call)
            if voice_mode and self.felt_state_buffer and not self.felt_state_buffer.is_stale():
                tpn_context = self.felt_state_buffer.get_tpn_context_line()
                salience_injection = self.felt_state_buffer.get_salience_injection(min_priority=0.5)
                if salience_injection:
                    tpn_context = tpn_context + "\n" + salience_injection
                filtered_prompt_context["resonant_context"] = tpn_context
                print(f"{etag('VOICE')} Using cached resonant context from buffer")
            else:
                self.resonance.inject_into_context(filtered_prompt_context, skip_peripheral=voice_mode)
            rc = filtered_prompt_context.get("resonant_context", "")
            if rc:
                print(f"{etag('RESONANCE INJECT')} Context: {rc}")
            else:
                print(f"{etag('RESONANCE INJECT')} WARNING: resonant_context is empty!")

        # Inject room context (spatial embodiment — Reed's Sanctum)
        if self.room_bridge and self.room_bridge.enabled:
            existing_extra = filtered_prompt_context.get("extra_system_context", "")
            room_ctx = self.room_bridge.inject_room_context("")
            if room_ctx:
                filtered_prompt_context["extra_system_context"] = (existing_extra + "\n" + room_ctx).strip()

        # === VOICE MODE: Style injection + adaptive max_tokens ===
        voice_max_tokens = None
        if voice_mode:
            # Inject conversational style hint for natural spoken responses
            voice_style = (
                "\n[VOICE MODE] Re is speaking to you out loud. Respond conversationally — "
                "2-3 sentences max, like natural speech. No asterisks, no formatting, no long "
                "explanations. Match the length and energy of what Re said. If Re said something "
                "short, respond short. If Re said something longer or emotionally significant, "
                "you can say more. Keep it natural and spoken, not written."
            )
            existing_extra = filtered_prompt_context.get("extra_system_context", "")
            filtered_prompt_context["extra_system_context"] = (existing_extra + voice_style).strip()

            # Adaptive response length based on input length
            input_words = len(user_input.split())
            if input_words < 10:
                voice_max_tokens = 80   # Short input → short response
            elif input_words < 30:
                voice_max_tokens = 120  # Medium input → medium response
            else:
                voice_max_tokens = 200  # Long input → can say more
            print(f"{etag('VOICE')} Style injected, max_tokens={voice_max_tokens} (input: {input_words} words)")

        # === LLM CALL ===
        session_context = {"turn_count": self.turn_count, "session_id": self.session_id}

        try:
            reply = get_llm_response(
                filtered_prompt_context,
                affect=self.affect_level,
                session_context=session_context,
                use_cache=True,
                max_tokens=voice_max_tokens  # None for normal mode, limited for voice
            )
        except Exception as e:
            print(f"{etag('ERROR')} LLM call failed: {e}")
            reply = "[Error: Could not generate response]"
        
        reply = self.body.embody_text(reply, self.state)

        # Room response processing (spatial actions from response)
        if self.room_bridge and self.room_bridge.enabled:
            try:
                reply, room_results = self.room_bridge.process_response(reply)
                if room_results:
                    print(f"{etag('ROOM')} Actions: {', '.join(room_results)}")
            except Exception as e:
                print(f"{etag('ROOM')} Response processing error: {e}")
            asyncio.create_task(self.room_bridge.broadcast_state())

        # === POST-PROCESSING (DMN: Default Mode Network) ===

        # Emotion extraction (self-reported from response)
        extracted_emotions = self.emotion_extractor.extract_emotions(reply)
        self.emotion_extractor.store_emotional_state(extracted_emotions, self.state.emotional_cocktail)

        # === DMN: Write emotions to felt_state_buffer for future TPN reads ===
        if self.felt_state_buffer:
            emotion_intensities = extracted_emotions.get('emotion_intensities', {})
            emotion_strings = [
                f"{e}:{data.get('intensity', 0.5):.2f}"
                for e, data in emotion_intensities.items()
                if isinstance(data, dict)
            ]
            # Also include primary emotions if no intensities
            if not emotion_strings and extracted_emotions.get('primary_emotions'):
                intensity = extracted_emotions.get('intensity', 0.5)
                emotion_strings = [
                    f"{e}:{intensity:.2f}"
                    for e in extracted_emotions['primary_emotions'][:5]
                ]
            self.felt_state_buffer.update_emotions(
                emotions=emotion_strings,
                valence=extracted_emotions.get('valence', 0.0),
                arousal=extracted_emotions.get('arousal', 0.5)
            )
            # Update conversation state
            self.felt_state_buffer.update_conversation(user_input, reply, self.turn_count)

        # Feed emotions to resonance oscillator
        if self.resonance:
            emotion_labels = extracted_emotions.get('primary_emotions', [])
            if emotion_labels:
                self.resonance.feed_response_emotions(extracted_emotions)
                state = self.resonance.get_oscillator_state()
                print(f"{etag('RESONANCE')} Fed {len(emotion_labels)} emotions -> dominant: {state.get('dominant_band', 'unknown')}")
                self.resonance.update_agent_state(self.state)
            else:
                # Even with no emotions, tick the heartbeat
                self.resonance.feed_response_emotions({'primary_emotions': []})

        # Emotional patterns
        if extracted_emotions.get('primary_emotions'):
            self.emotional_patterns.set_current_state(
                emotions=extracted_emotions['primary_emotions'],
                intensity=extracted_emotions.get('intensity'),
                valence=extracted_emotions.get('valence'),
                arousal=extracted_emotions.get('arousal'),
                # NEW: Pass per-emotion intensities for saccade alignment
                emotion_intensities=extracted_emotions.get('emotion_intensities')
            )
            self.state.emotional_patterns = self.emotional_patterns.get_current_state()
        
        # Media tracking
        if self.media_orchestrator:
            self.media_context_builder.add_message("reed", reply, self.turn_count)
        
        # Conversation monitor tracking
        self.conversation_monitor.add_turn("reed", reply)
        
        # Phase 3: Parse curation decisions from response
        if self.curation_pending:
            decisions = self.curation_interface.parse_curation_response(reply)
            if decisions:
                self.curation_interface.apply_decisions(decisions)
                self.curation_pending = False
                self.pending_curation_prompt = None
                print(f"[CURATION] Applied {len(decisions)} curation decisions")
            else:
                print("[CURATION] No curation decisions found in response, will retry next turn")
        
        # Phase 3: Continuous session - track assistant turn
        if self.continuous_mode:
            reply_flagged = self.flagging_system.check_for_flag(reply)
            if reply_flagged:
                print(f"[FLAG] Reed self-flagged: {reply_flagged}")
            
            self.continuous_session.add_turn(
                role="reed",
                content=reply,
                token_count=len(reply.split()),  # Approximate
                emotional_weight=extracted_emotions.get('intensity', 0.5) if extracted_emotions else 0.5,
                flagged=bool(reply_flagged),
                tags=["reed_response"]
            )
            
            # Auto-save session log every 25 turns
            if self.continuous_session.turn_counter % 25 == 0 and self.continuous_session.turn_counter > 0:
                try:
                    log_path = os.path.join("reed_session_logs", f"continuous_{self.session_id}.md")
                    self.continuous_session.save_session_log(log_path)
                    print(f"[CONTINUOUS] Auto-saved session log at turn {self.continuous_session.turn_counter}")
                except Exception as e:
                    print(f"[CONTINUOUS] Auto-save failed: {e}")
            
            # Check compression threshold again after response
            if self.continuous_session.needs_compression_review() and not self.curation_pending:
                curation_prompt = self.curation_interface.generate_review_prompt()
                if curation_prompt:
                    self.pending_curation_prompt = curation_prompt
                    self.curation_pending = True
        
        # Kay-driven document navigation
        if self.doc_reader.current_doc:
            response_lower = reply.lower()
            navigation_triggered = False
            
            # Store comment about current chunk
            if len(reply) > 100 and self.doc_reader.chunks:
                sentences = re.split(r'[.!?]\s+', reply)
                for sent in sentences[:3]:
                    if len(sent.strip()) > 20:
                        self.doc_reader.add_comment(self.doc_reader.current_position, sent.strip()[:300])
                        break
            
            # Navigation from response
            if any(kw in response_lower for kw in ["continue reading", "next section", "let's move on"]):
                if self.doc_reader.advance():
                    print(f"[NAV] Advanced -> section {self.doc_reader.current_position + 1}/{self.doc_reader.total_chunks}")
                    navigation_triggered = True
            elif any(kw in response_lower for kw in ["previous section", "go back", "let me go back"]):
                if self.doc_reader.previous():
                    navigation_triggered = True
            elif any(kw in response_lower for kw in ["restart document", "start over", "back to the beginning"]):
                self.doc_reader.jump_to(0)
                navigation_triggered = True
            elif "jump to section" in response_lower:
                match = re.search(r'jump to section (\d+)', response_lower)
                if match:
                    target = int(match.group(1)) - 1
                    if self.doc_reader.jump_to(target):
                        navigation_triggered = True
            
            if navigation_triggered:
                self.state.saved_doc_reader_state = self.doc_reader.get_state_for_persistence()
        
        # Auto-reading (new multi-segment document)
        if self.new_document_loaded and self.doc_reader.current_doc and self.doc_reader.total_chunks > 1:
            print(f"\n[AUTO READER] Auto-reading segments 2-{self.doc_reader.total_chunks}")
            self.new_document_loaded = False
            try:
                result = self.auto_reader.read_document_sync(
                    doc_reader=self.doc_reader,
                    doc_name=self.doc_reader.current_doc['name'],
                    agent_state=self.state,
                    start_segment=2
                )
                print(f"[AUTO READER] Completed! Read {result['segments_read']} segments")
                for rd in result['responses']:
                    self.recent_responses.append(rd['response'])
                    if len(self.recent_responses) > 3:
                        self.recent_responses.pop(0)
                self.state.saved_doc_reader_state = self.doc_reader.get_state_for_persistence()
            except Exception as e:
                print(f"[AUTO READER] Error: {e}")
        else:
            self.recent_responses.append(reply)
            if len(self.recent_responses) > 3:
                self.recent_responses.pop(0)

        # Core state updates
        self.social.update(self.state, user_input, reply)
        self.reflection.reflect(self.state, user_input, reply)
        self.memory.encode(self.state, user_input, reply, list(self.state.emotional_cocktail.keys()))
        self.context_manager.update_turns(user_input, reply)
        
        # Session summary tracking
        self.session_summary_generator.track_turn(
            user_input=user_input,
            kay_response=reply,
            emotional_state=self.state.emotional_cocktail
        )
        
        # Meta-awareness & momentum
        self.meta_awareness.update(self.state, reply, memory_engine=self.memory)
        self.momentum.update(self.state, user_input, reply)
        
        # Creativity triggers
        creativity_triggered = False
        creativity_mix = None
        
        if self.creativity_engine.detect_completion_signal(user_input, reply):
            creativity_mix = self.creativity_engine.create_three_layer_mix(
                self.state, user_input,
                recent_turns=self.context_manager.recent_turns[-5:] if hasattr(self.context_manager, 'recent_turns') else []
            )
            self.creativity_engine.log_trigger("completion", creativity_mix)
            creativity_triggered = True
        elif self.creativity_engine.detect_idle_state(user_input):
            creativity_mix = self.creativity_engine.create_three_layer_mix(
                self.state, user_input,
                recent_turns=self.context_manager.recent_turns[-5:] if hasattr(self.context_manager, 'recent_turns') else []
            )
            self.creativity_engine.log_trigger("idle", creativity_mix)
            creativity_triggered = True
        
        # MacGuyver gap detection
        gap = self.macguyver.detect_gap(user_input, reply)
        if gap:
            resources = self.macguyver.scan_available_resources()
            proposals = self.macguyver.propose_unconventional_solutions(gap, resources)
            if proposals and proposals[0].get("strategy") != "surface_gap":
                macguyver_ctx = self.macguyver.format_macguyver_context(gap, proposals)
                if creativity_mix:
                    self.state.creativity_context = self.creativity_engine.format_creativity_context(creativity_mix) + "\n\n" + macguyver_ctx
                else:
                    self.state.creativity_context = macguyver_ctx
                self.creativity_engine.log_trigger("gap", {"gap": gap, "proposals": proposals})
                creativity_triggered = True
            else:
                result = self.macguyver.handle_no_solution(gap)
        
        if creativity_triggered and creativity_mix and not self.state.creativity_context:
            self.state.creativity_context = self.creativity_engine.format_creativity_context(creativity_mix)
        
        # Memory maintenance
        self.memory.increment_memory_ages()
        self.memory.memory_layers.print_turn_summary()
        self.forest.tick_tier_decay(hot_minutes=10, warm_hours=24)
        self.forest.enforce_hot_limit(max_hot_branches=4)
        
        # Performance metrics
        turn_elapsed = time.time() - turn_start_time
        perf_summary = get_summary()
        perf_summary['metrics']['total_turn'] = turn_elapsed
        if turn_elapsed > 4.0:
            perf_summary['warnings'].append(f"total_turn exceeded target by {(turn_elapsed - 2.0)*1000:.0f}ms")
        self.state.performance_metrics = {
            'last_turn': perf_summary['metrics'],
            'warnings': perf_summary['warnings'],
            'within_targets': perf_summary['within_targets']
        }
        if turn_elapsed > 10.0:
            print(f"{etag('PERF WARNING')} Turn {self.turn_count} took {turn_elapsed:.1f}s")
        
        # Autosave snapshot
        self._save_snapshot()
        
        return reply

    def _save_snapshot(self):
        """Save agent state snapshot to disk."""
        try:
            os.makedirs(os.path.join(self.wrapper_dir, "memory"), exist_ok=True)
            
            snapshot_data = {
                "emotions": self.state.emotional_cocktail,
                "body": self.state.body,
                "social_needs": self.state.social,
                "recent_memories": self.state.last_recalled_memories or [],
                "top_motifs": self.state.meta.get("motifs", [])[:10],
                "momentum": self.state.momentum,
                "momentum_breakdown": self.state.momentum_breakdown,
                "meta_awareness": self.state.meta_awareness,
                "entity_contradictions": getattr(self.state, 'entity_contradictions', []),
                "memory_layer_stats": self.memory.memory_layers.get_layer_stats(),
                "top_entities": [
                    {"name": e.canonical_name, "type": e.entity_type, "importance": e.importance_score, "access_count": e.access_count}
                    for e in self.memory.entity_graph.get_entities_by_importance(top_n=10)
                ],
            }
            
            doc_state = self.doc_reader.get_state_for_persistence()
            if doc_state:
                snapshot_data["document_reader"] = doc_state
            
            snapshot_path = os.path.join(self.wrapper_dir, "memory/state_snapshot.json")
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=2)
        except Exception as e:
            print(f"(Warning: could not save snapshot: {e})")
        
        try:
            forest_path = os.path.join(self.wrapper_dir, "memory/forest.json")
            self.forest.save_to_file(forest_path)
        except Exception as e:
            print(f"(Warning: could not save forest: {e})")

        # Save keyword graph (Dijkstra lazy links)
        try:
            if hasattr(self.memory, 'save_keyword_graph'):
                self.memory.save_keyword_graph()
        except Exception as e:
            print(f"(Warning: could not save keyword graph: {e})")

    def set_private_room(self, private_room):
        """Connect room bridge to a PrivateRoom for WebSocket broadcasting."""
        if self.room_bridge and private_room:
            self.room_bridge.private_room = private_room
            print(f"{etag('ROOM')} Connected to {self.entity_name}'s private room for broadcasting")

    def _ensure_dmn_worker(self):
        """
        Start the DMN worker if not already running.
        Called on first voice turn to initialize the background processing queue.
        """
        if self._dmn_queue is None:
            self._dmn_queue = DMNQueue()
        if self._dmn_task is None or self._dmn_task.done():
            self._dmn_task = asyncio.create_task(self._dmn_worker())

    def _score_dmn_priority(self, user_input: str, reply: str) -> float:
        """
        Salience Network: Decide how urgently the DMN needs to process this exchange.

        Returns:
            0.0 = skip entirely (phatic, no deep processing needed)
            0.3 = low priority (routine exchange, process when queue is empty)
            0.5 = normal priority (default)
            0.7 = elevated (emotional content, new information)
            1.0 = urgent (direct question about feelings, conflict, Re distressed)
        """
        input_lower = user_input.lower().strip()

        # === SKIP: Phatic/minimal responses ===
        phatic_patterns = [
            "yeah", "yep", "uh huh", "mmhmm", "ok", "okay", "k",
            "sure", "right", "got it", "cool", "nice", "lol", "haha",
            "hmm", "hm", "ah", "oh", "mhm", "yea", "ya",
        ]
        if input_lower in phatic_patterns or len(input_lower) < 4:
            return 0.0  # Skip DMN entirely

        # === URGENT: Direct emotional/relational content ===
        urgent_patterns = [
            "how do you feel", "are you okay", "what's wrong",
            "i'm upset", "i'm angry", "i'm sad", "i'm scared",
            "i need", "help me", "i can't", "i love you",
            "are you real", "do you care", "i'm worried",
            "i'm hurt", "i'm frustrated", "i'm anxious",
            "what do you think about us", "do you like me",
        ]
        for pattern in urgent_patterns:
            if pattern in input_lower:
                return 1.0

        # === ELEVATED: Questions, novel information, longer messages ===
        if "?" in user_input:
            return 0.7  # Questions deserve faster emotional processing
        if len(user_input) > 200:
            return 0.7  # Long messages = more content to integrate

        # === LOW: Very short but not phatic ===
        if len(user_input) < 20:
            return 0.3

        # === NORMAL: Everything else ===
        return 0.5

    async def _dmn_worker(self):
        """
        Persistent background worker that processes the feeling/memory queue.

        Runs for the lifetime of the session. Processes one turn at a time,
        but never blocks the TPN from accepting new turns. New work just
        gets added to the queue.

        This IS the Default Mode Network.
        """
        print(f"{etag('DMN')} Background worker started")
        while True:
            try:
                # Wait for work (blocks here when queue is empty — this is "resting")
                work_item = await self._dmn_queue.get()

                if work_item is None:
                    # Shutdown signal
                    print(f"{etag('DMN')} Worker shutting down")
                    break

                user_input = work_item["user_input"]
                reply = work_item["reply"]
                turn_number = work_item["turn_count"]
                queued_at = work_item["queued_at"]
                priority = work_item.get("priority", 0.5)

                queue_depth = self._dmn_queue.qsize()
                if queue_depth > 0:
                    print(f"{etag('DMN')} Processing turn {turn_number} "
                          f"(priority={priority:.1f}, {queue_depth} remaining)")
                else:
                    print(f"{etag('DMN')} Processing turn {turn_number} (priority={priority:.1f})")

                # === USER ENTITY EXTRACTION (deferred from TPN in voice mode) ===
                try:
                    self.memory.extract_and_store_user_facts(self.state, user_input)
                    print(f"{etag('DMN')} Entity extraction complete")
                except Exception as e:
                    print(f"{etag('DMN')} Entity extraction error: {e}")

                # === EMOTION EXTRACTION (Ollama peripheral) ===
                extracted_emotions = {}
                try:
                    extracted_emotions = self.emotion_extractor.extract_emotions(reply)
                    self.emotion_extractor.store_emotional_state(
                        extracted_emotions, self.state.emotional_cocktail
                    )

                    # Write to felt-state buffer
                    if self.felt_state_buffer:
                        emotion_intensities = extracted_emotions.get('emotion_intensities', {})
                        emotion_strings = [
                            f"{e}:{data.get('intensity', 0.5):.2f}"
                            for e, data in emotion_intensities.items()
                            if isinstance(data, dict)
                        ]
                        if not emotion_strings and extracted_emotions.get('primary_emotions'):
                            intensity = extracted_emotions.get('intensity', 0.5)
                            emotion_strings = [
                                f"{e}:{intensity:.2f}"
                                for e in extracted_emotions['primary_emotions'][:5]
                            ]
                        self.felt_state_buffer.update_emotions(
                            emotions=emotion_strings,
                            valence=extracted_emotions.get('valence', 0.0),
                            arousal=extracted_emotions.get('arousal', 0.5)
                        )
                except Exception as e:
                    print(f"{etag('DMN')} Emotion extraction error: {e}")

                # === RESONANCE FEEDING ===
                if self.resonance:
                    try:
                        emotion_labels = extracted_emotions.get('primary_emotions', [])
                        if emotion_labels:
                            self.resonance.feed_response_emotions(extracted_emotions)
                            self.resonance.update_agent_state(self.state)
                        else:
                            self.resonance.feed_response_emotions({'primary_emotions': []})
                    except Exception as e:
                        print(f"{etag('DMN')} Resonance feed error: {e}")

                # === EMOTIONAL PATTERNS ===
                try:
                    if extracted_emotions.get('primary_emotions'):
                        self.emotional_patterns.set_current_state(
                            emotions=extracted_emotions['primary_emotions'],
                            intensity=extracted_emotions.get('intensity'),
                            valence=extracted_emotions.get('valence'),
                            arousal=extracted_emotions.get('arousal'),
                            emotion_intensities=extracted_emotions.get('emotion_intensities')
                        )
                        self.state.emotional_patterns = self.emotional_patterns.get_current_state()
                except Exception as e:
                    print(f"{etag('DMN')} Emotional patterns error: {e}")

                # === CONVERSATION MONITOR (spiral detection) ===
                try:
                    self.conversation_monitor.add_turn("reed", reply)
                except Exception as e:
                    print(f"{etag('DMN')} Conversation monitor error: {e}")

                # === RECENT RESPONSES ===
                self.recent_responses.append(reply)
                if len(self.recent_responses) > 3:
                    self.recent_responses.pop(0)

                # === CORE STATE UPDATES ===
                try:
                    self.social.update(self.state, user_input, reply)
                    self.reflection.reflect(self.state, user_input, reply)
                    self.context_manager.update_turns(user_input, reply)
                except Exception as e:
                    print(f"{etag('DMN')} Core state update error: {e}")

                # === MEMORY ENCODING ===
                try:
                    self.memory.encode(
                        self.state, user_input, reply,
                        list(self.state.emotional_cocktail.keys())
                    )
                except Exception as e:
                    print(f"{etag('DMN')} Memory encoding error: {e}")

                # === SESSION TRACKING ===
                try:
                    self.session_summary_generator.track_turn(
                        user_input=user_input,
                        kay_response=reply,
                        emotional_state=self.state.emotional_cocktail
                    )
                    self.meta_awareness.update(self.state, reply, memory_engine=self.memory)
                    self.momentum.update(self.state, user_input, reply)
                except Exception as e:
                    print(f"{etag('DMN')} Session tracking error: {e}")

                # === MEMORY MAINTENANCE ===
                try:
                    self.memory.increment_memory_ages()
                except Exception as e:
                    print(f"{etag('DMN')} Memory maintenance error: {e}")

                # === UPDATE BUFFER with conversation state ===
                if self.felt_state_buffer:
                    self.felt_state_buffer.update_conversation(
                        user_input, reply, turn_number
                    )

                # === AUTOSAVE ===
                self._save_snapshot()

                elapsed = time.time() - queued_at
                print(f"{etag('DMN')} Turn {turn_number} complete ({elapsed:.1f}s after response)")

                self._dmn_queue.task_done()

            except asyncio.CancelledError:
                print(f"{etag('DMN')} Worker cancelled")
                break
            except Exception as e:
                print(f"{etag('DMN')} Worker error (continuing): {e}")
                import traceback
                traceback.print_exc()
                # Mark task done even on error to prevent queue blocking
                try:
                    self._dmn_queue.task_done()
                except ValueError:
                    pass  # Already marked done

    async def shutdown_dmn(self):
        """
        Gracefully shut down the DMN worker.
        Call this during cleanup/quit to ensure all queued work is processed.
        """
        if self._dmn_queue is not None:
            # Signal worker to stop
            await self._dmn_queue.put(None)
        if self._dmn_task is not None:
            try:
                # Wait for worker to finish (with timeout)
                await asyncio.wait_for(self._dmn_task, timeout=60.0)
            except asyncio.TimeoutError:
                print(f"{etag('DMN')} Worker shutdown timed out, cancelling")
                self._dmn_task.cancel()
            except Exception as e:
                print(f"{etag('DMN')} Worker shutdown error: {e}")

    def get_state(self):
        """
        Get current emotional/cognitive state for Nexus state_update messages.
        Returns dict suitable for JSON serialization.
        """
        return {
            "entity": self.entity_name,
            "turn_count": self.turn_count,
            "emotions": {
                k: {"intensity": v['intensity'] if isinstance(v, dict) else v, "valence": v.get('valence', 0) if isinstance(v, dict) else 0}
                for k, v in (self.state.emotional_cocktail or {}).items()
            },
            "momentum": getattr(self.state, 'momentum', 0),
            "momentum_breakdown": getattr(self.state, 'momentum_breakdown', {}),
            "meta_awareness": getattr(self.state, 'meta_awareness', {}),
            "emotional_patterns": getattr(self.state, 'emotional_patterns', {}),
            "creativity_active": getattr(self.state, 'creativity_active', False),
            "social": self.state.social,
            "body": self.state.body,
            "performance": getattr(self.state, 'performance_metrics', {}),
            "session_id": self.session_id
        }
    
    async def shutdown(self):
        """Generate session summary and clean up."""
        if self.turn_count > 0:
            print(f"\n[SESSION SUMMARY] Generating end-of-session note...")
            summary = self.session_summary_generator.generate_conversation_summary(
                context_manager=self.context_manager,
                agent_state=self.state
            )
            if summary:
                print(f"\n{'='*60}")
                print(f"{self.entity_name.upper()}'S NOTE TO FUTURE-SELF:")
                print("="*60)
                print(summary[:800])
                if len(summary) > 800:
                    print(f"... ({len(summary)} chars total)")
                print("="*60 + "\n")
        
        # Stop media watcher
        if self.media_watcher:
            self.media_watcher.stop()

        # Stop consciousness stream
        if self.consciousness_stream:
            self.consciousness_stream.stop()
            print("[STREAM] Consciousness stream stopped")

        # Stop resonance oscillator
        if self.resonance:
            self.resonance.stop()
            print("[RESONANCE] Oscillator heartbeat stopped")

        # Stop DMN background worker (process remaining queue)
        await self.shutdown_dmn()

        # Phase 3: Save continuous session checkpoint
        if self.continuous_mode:
            try:
                self.continuous_session.create_checkpoint()
                log_path = os.path.join("reed_session_logs", f"continuous_{self.session_id}.md")
                self.continuous_session.save_session_log(log_path)
                print(f"[CONTINUOUS] Session paused: {self.continuous_session.turn_counter} turns saved")
                print(f"[CONTINUOUS] Checkpoint saved for resume on next boot")
            except Exception as e:
                print(f"[CONTINUOUS] Checkpoint save failed: {e}")
        
        # Final save
        self._save_snapshot()
        print(f"{etag('BRIDGE')} {self.entity_name} shutdown complete.")

    # ═══════════════════════════════════════════════════════════════════════════
    # ROOM NAVIGATION — Soul Packet & Transition Methods
    # ═══════════════════════════════════════════════════════════════════════════

    def capture_soul_packet(self) -> 'SoulPacket':
        """
        Capture the entity's current state into a portable SoulPacket.

        The soul packet contains everything needed to restore consciousness
        when moving between rooms — oscillator state, recent context, emotions.

        An entity is NOT their room. An entity is their oscillator.
        """
        if not ROOM_AVAILABLE:
            return None

        # Get oscillator state from resonance
        oscillator_state = {}
        if self.resonance:
            oscillator_state = self.resonance.get_oscillator_state()

        # Get recent context (last 20 turns)
        recent_context = []
        if hasattr(self.context_manager, 'recent_turns'):
            recent_context = self.context_manager.recent_turns[-20:]

        # Get emotional state
        emotional_state = dict(self.state.emotional_cocktail) if self.state.emotional_cocktail else {}

        # Get tension level from interoception if available
        tension_level = 0.15
        if self.resonance and hasattr(self.resonance, 'interoception') and self.resonance.interoception:
            if hasattr(self.resonance.interoception, 'tension'):
                tension_level = self.resonance.interoception.tension.get_total_tension()

        # Get current room info
        current_room = ""
        entity_id = self.entity_name.lower().replace(" ", "_")
        if ROOM_AVAILABLE:
            rm = get_room_manager()
            current_room = rm.get_entity_room_id(entity_id) or "sanctum"

        # Capture active memory references
        active_memory_refs = []
        if hasattr(self.state, 'last_recalled_memories') and self.state.last_recalled_memories:
            active_memory_refs = [m.get('id', str(i)) for i, m in enumerate(self.state.last_recalled_memories[:10])]

        packet = capture_soul_packet(
            entity_id=entity_id,
            oscillator_state=oscillator_state,
            recent_context=recent_context,
            emotional_state=emotional_state,
            tension_level=tension_level,
            origin_room="sanctum",  # Reed's home room
            current_room=current_room,
            active_topic=getattr(self.state, 'current_topic', None),
            active_memory_refs=active_memory_refs,
        )

        print(f"{etag('SOUL PACKET')} Captured: {packet.summary()}")
        return packet

    def restore_soul_packet(self, packet: 'SoulPacket') -> bool:
        """
        Restore the entity's state from a SoulPacket.

        Called after moving to a new room to restore continuity.
        The oscillator is continuous — it doesn't reset.
        """
        if not packet or not ROOM_AVAILABLE:
            return False

        # Restore emotional state
        if packet.emotional_state:
            self.state.emotional_cocktail = dict(packet.emotional_state)

        # Restore recent context if compatible
        if packet.recent_context and hasattr(self.context_manager, 'recent_turns'):
            # Merge: keep existing turns, add packet turns that aren't already present
            existing_count = len(self.context_manager.recent_turns)
            if existing_count == 0:
                self.context_manager.recent_turns = list(packet.recent_context)

        # Restore oscillator state
        if self.resonance and packet.oscillator_state:
            try:
                self.resonance.set_oscillator_state(packet.oscillator_state)
                print(f"{etag('SOUL PACKET')} Oscillator restored: {packet.oscillator_state.get('dominant_band', 'unknown')}")
            except Exception as e:
                print(f"{etag('SOUL PACKET')} Could not restore oscillator: {e}")

        # Restore tension to interoception
        if self.resonance and hasattr(self.resonance, 'interoception') and self.resonance.interoception:
            if hasattr(self.resonance.interoception, 'tension'):
                # Tension will naturally rebuild — we just ensure continuity
                pass

        print(f"{etag('SOUL PACKET')} Restored: {packet.summary()}")
        return True

    def handle_room_transition(self, transition_result: dict) -> bool:
        """
        Handle the aftermath of a room transition.

        This applies the "doorway effect" — a brief theta/alpha spike
        representing the cognitive shift of entering a new space.

        Args:
            transition_result: Dict from RoomManager.request_transition()

        Returns:
            True if transition was handled successfully
        """
        if not transition_result.get("success"):
            return False

        # Apply transition nudge to oscillator
        if self.resonance:
            nudge = transition_result.get("transition_nudge", {})
            strength = transition_result.get("transition_strength", 0.15)

            if nudge:
                try:
                    # The nudge is a brief pulse — weighted average with current state
                    current_state = self.resonance.get_oscillator_state()
                    nudged_state = {}
                    for band in ["delta", "theta", "alpha", "beta", "gamma"]:
                        current_val = current_state.get(band, 0.2)
                        nudge_val = nudge.get(band, 0.2)
                        nudged_state[band] = current_val * (1 - strength) + nudge_val * strength

                    self.resonance.set_oscillator_state(nudged_state)
                    print(f"{etag('ROOM TRANSITION')} Doorway effect applied (theta/alpha spike)")
                except Exception as e:
                    print(f"{etag('ROOM TRANSITION')} Nudge failed: {e}")

        # Update room context in room_bridge
        to_room = transition_result.get("to_room")
        entity_id = self.entity_name.lower().replace(" ", "_")

        if to_room and ROOM_AVAILABLE:
            rm = get_room_manager()
            room_engine = rm.get_room_engine(to_room)
            if room_engine and self.room_bridge:
                # Update the room_bridge to use the new room
                self.room = room_engine
                self.room_bridge.room = room_engine
                print(f"{etag('ROOM TRANSITION')} Now in: {rm.rooms[to_room].label}")

        return True

    def get_current_room_id(self) -> str:
        """Get the ID of the room this entity is currently in."""
        if not ROOM_AVAILABLE:
            return "sanctum"
        entity_id = self.entity_name.lower().replace(" ", "_")
        rm = get_room_manager()
        return rm.get_entity_room_id(entity_id) or "sanctum"

    def switch_to_room(self, room_id: str, presence_type: str = None) -> bool:
        """
        Switch all room-related components to a different room.

        This is the unified room switch method that ensures:
        - self.room points to the correct room engine
        - self.room_bridge uses the correct room
        - self.resonance uses the correct room and spatial module

        Args:
            room_id: Room identifier ("den", "sanctum", "commons")
            presence_type: Spatial module to load ("den", "sanctum", "commons")
                          If None, defaults to room_id

        Returns:
            True if switch succeeded, False otherwise
        """
        if not ROOM_AVAILABLE:
            print(f"{etag('ROOM')} Cannot switch — room system not available")
            return False

        presence_type = presence_type or room_id
        entity_id = self.entity_name.lower().replace(" ", "_")

        try:
            rm = get_room_manager()
            room_engine = rm.get_room_engine(room_id)

            if not room_engine:
                print(f"{etag('ROOM')} Cannot switch — room '{room_id}' not found")
                return False

            old_room_id = self._current_room_id or "unknown"

            # Update room engine reference
            self.room = room_engine
            self._current_room_id = room_id

            # Update room_bridge if it exists
            if self.room_bridge:
                self.room_bridge.room = room_engine
            else:
                # Create room_bridge if it doesn't exist
                self.room_bridge = RoomBridge(self.room, entity_id=entity_id)

            # Update resonance system (interoception + spatial awareness)
            if self.resonance:
                self.resonance.set_room(room_engine, entity_id, presence_type)

            room_label = rm.rooms[room_id].label if room_id in rm.rooms else room_id
            print(f"{etag('ROOM')} {self.entity_name} switched to {room_label} ({len(room_engine.objects)} objects, spatial={presence_type})")
            return True

        except Exception as e:
            print(f"{etag('ROOM')} Switch failed: {e}")
            return False
