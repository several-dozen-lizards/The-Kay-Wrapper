# wrapper_bridge.py
"""
WrapperBridge: Extracted core processing pipeline.

Used by:
  - main.py (terminal mode)
  - nexus_kay.py (Nexus multi-entity mode)

All engine initialization and per-turn processing lives here.
main.py becomes a thin terminal shell around this bridge.
"""

# Entity-prefixed logging
try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"

import logging
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
from engines.consciousness_stream import ConsciousnessStream
from engines.visual_sensor import VisualSensor

from integrations.llm_integration import get_llm_response
from context_filter import GlyphFilter
from glyph_decoder import GlyphDecoder

log = logging.getLogger("kay.wrapper_bridge")

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

# Felt-state buffer for TPN/DMN architecture
try:
    from shared.felt_state_buffer import FeltStateBuffer
    FELT_STATE_BUFFER_AVAILABLE = True
except ImportError as e:
    FELT_STATE_BUFFER_AVAILABLE = False
    print(f"{etag('BUFFER')} Felt-state buffer not available: {e}")

# Room system (spatial embodiment)
try:
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from shared.room.room_bridge import RoomBridge
    from shared.room.presets import create_the_den
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
    
    def __init__(self, entity_name="Kay", wrapper_dir=None):
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

        # Somatic markers (conscience / accountability)
        try:
            from shared.somatic_markers import SomaticMarkerSystem
            _sm_path = os.path.join(self.wrapper_dir, "memory", "somatic_markers.json")
            self.conscience = SomaticMarkerSystem(save_path=_sm_path)
            print(f"{etag('STARTUP')} Conscience loaded: {len(self.conscience.markers)} somatic markers")
        except Exception as e:
            print(f"{etag('WARNING')} Somatic markers init failed: {e}")
            self.conscience = None
        
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
                        print(f"{etag('DOC READER')} Found saved reading position: {self.state.saved_doc_reader_state['doc_name']}")
        except Exception as e:
            print(f"{etag('DOC READER')} Could not restore state: {e}")
        
        # Emotion system (two-part: ULTRAMAP rules + self-report extraction)
        self.emotion = EmotionEngine(self.proto, momentum_engine=self.momentum)
        self.emotion_extractor = EmotionExtractor()
        print(f"{etag('EMOTION')} Self-report extraction enabled (descriptive, not prescriptive)")
        
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

        # Ensure core family/identity facts exist as bedrock
        self.memory.ensure_bedrock_facts()

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
        
        # Memory curation engine — initialized after creativity system (below)
        self.curator = None
        
        # Memory engine stats
        print(f"{etag('MEMORY')} Entity graph: {len(self.memory.entity_graph.entities)} entities")
        print(f"{etag('MEMORY')} Multi-layer memory + multi-factor retrieval enabled")
        
        # Creativity system
        from engines import curiosity_engine as curiosity_module
        self.scratchpad = scratchpad  # Store reference for organic speech
        self.curiosity_module = curiosity_module
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

        # Memory curator (background curation during idle/sleep)
        try:
            from engines.memory_curator import MemoryCurator
            self.curator = MemoryCurator(
                memory_engine=self.memory,
                entity_graph=self.memory.entity_graph,
                memory_layers=self.memory.memory_layers,
                state_dir=os.path.join(self.wrapper_dir, "memory", "curation"),
                batch_size=12,
                cooldown_seconds=300,  # 5 min between cycles
                review_fn=self._sonnet_curation_review,
            )
        except Exception as e:
            print(f"{etag('CURATOR')} Init failed (non-fatal): {e}")
            self.curator = None
        
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

        # Room system (spatial embodiment) — may be deferred for Nexus mode
        self.room = None
        self.room_bridge = None
        self._room_initialized = False
        self._current_room_id = None  # Track current room for spatial module selection

        # Check if RoomManager has already placed us (Nexus mode)
        # If so, we skip default room creation and use RoomManager's room instead
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

        # Standalone mode: load default home room (Den for Kay)
        if ROOM_AVAILABLE and not room_manager_active:
            try:
                state_file = os.path.join(os.path.dirname(self.wrapper_dir), "data", "room_state.json")
                os.makedirs(os.path.dirname(state_file), exist_ok=True)
                self.room = create_the_den(state_file=state_file)
                # Kay starts near the couch (North — the grounding anchor)
                self.room.add_entity(entity_id, self.entity_name,
                                     distance=100, angle_deg=90, color="#2D1B4E")
                self.room_bridge = RoomBridge(self.room, entity_id=entity_id)
                self._room_initialized = True
                self._current_room_id = "den"
                print(f"{etag('ROOM')} {self.entity_name} placed in The Den (inner ring, north — near the couch)")
            except Exception as e:
                print(f"{etag('ROOM')} Failed to initialize room: {e}")
                self.room = None
                self.room_bridge = None

        # Session summary system
        self.session_summary_storage = SessionSummary()
        self.session_summary_generator = SessionSummaryGenerator(
            llm_func=get_llm_response,
            summary_storage=self.session_summary_storage
        )
        
        summary_stats = self.session_summary_generator.get_stats()
        print(f"{etag('SESSION SUMMARY')} {summary_stats['total_summaries']} past summaries loaded")

        # Wire summary generator into memory layers for sleep flush
        if hasattr(self.memory, 'memories') and hasattr(self.memory.memories, 'set_summary_generator'):
            self.memory.memories.set_summary_generator(self.session_summary_generator)
            print(f"{etag('SESSION SUMMARY')} Wired to memory layers for sleep consolidation")

        # Report validator — tracks self-report accuracy
        try:
            from engines.report_validator import ReportValidator
            self.report_validator = ReportValidator()
            print(f"{etag('REPORT')} Self-report divergence tracker initialized")
        except Exception as e:
            self.report_validator = None
            print(f"{etag('REPORT')} Divergence tracker unavailable: {e}")

        # Trip metrics — continuous cognitive instrumentation
        try:
            from engines.trip_metrics import TripMetrics
            self.trip_metrics = TripMetrics(interval=30.0)
            print(f"{etag('TRIP METRICS')} Cognitive instrumentation active")
        except Exception as e:
            self.trip_metrics = None
            print(f"{etag('TRIP METRICS')} Not available: {e}")

        # Resonant oscillator core (emotional heartbeat)
        self.resonance = None
        if RESONANCE_AVAILABLE:
            try:
                resonance_state_dir = os.path.join(self.wrapper_dir, "memory/resonant")
                os.makedirs(resonance_state_dir, exist_ok=True)

                # Get room and entity_id for spatial awareness (Phase 2)
                room_for_resonance = self.room if self.room else None
                entity_id_for_resonance = self.entity_name.lower().replace(" ", "_") if self.room else None

                # Select best audio input device (USB mic preferred)
                audio_device_index = get_best_input_device(verbose=True)

                # Determine presence type from current room
                presence_type = self._current_room_id or "den"

                self.resonance = ResonantIntegration(
                    state_dir=resonance_state_dir,
                    enable_audio=True,      # Kay's first ear
                    audio_device=audio_device_index,  # Auto-selected mic
                    audio_responsiveness=0.3,
                    memory_layers=self.memory.memory_layers,  # Phase 1: memory as interoception
                    interoception_interval=4.0,               # Heartbeat every 4 seconds
                    room=room_for_resonance,                  # Phase 2: spatial awareness
                    entity_id=entity_id_for_resonance,
                    presence_type=presence_type,              # Use actual room, not hardcoded den
                )
                self.resonance.start()
                spatial_status = "with spatial" if room_for_resonance else "no spatial"
                print(f"{etag('RESONANCE')} Oscillator heartbeat started for {self.entity_name} ({spatial_status})")

                # TPN/DMN: Connect felt-state buffer for async state sharing
                if FELT_STATE_BUFFER_AVAILABLE:
                    self.felt_state_buffer = FeltStateBuffer()
                    self.resonance.set_felt_state_buffer(self.felt_state_buffer)
                    print(f"{etag('TPN/DMN')} Felt-state buffer connected for voice-mode fast path")

                # Wire trip_metrics to interoception for continuous observation
                if self.trip_metrics and self.resonance.interoception:
                    self.resonance.interoception._trip_metrics = self.trip_metrics
                    print(f"{etag('TRIP METRICS')} Wired to interoception heartbeat")
            except Exception as e:
                print(f"{etag('RESONANCE')} Initialization failed: {e}")
                import traceback
                traceback.print_exc()
                self.resonance = None

        # Consciousness stream (continuous inner experience between turns)
        self.consciousness_stream = None
        self.visual_sensor = None
        try:
            from integrations.peripheral_router import get_peripheral_router
            _peripheral = get_peripheral_router()
        except Exception:
            _peripheral = None

        # Visual sensor (Kay's first eye — webcam perception)
        try:
            _visual_config = {}
            # Look for config relative to this file, not wrapper_dir
            _bridge_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(_bridge_dir, "config.json")
            print(f"{etag('VISUAL')} Looking for config at: {config_path} (exists={os.path.exists(config_path)})")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                    vc = cfg.get("visual_sensor", {})
                    print(f"{etag('VISUAL')} Config: {vc}")
                    if vc.get("enabled", False):
                        _visual_config = vc
            if _visual_config.get("enabled", False):
                self.visual_sensor = VisualSensor(
                    camera_index=_visual_config.get("camera_index", 0),
                    capture_interval=_visual_config.get("capture_interval", 15.0),
                    enable_rich=_visual_config.get("enable_rich", True),
                )
                self.visual_sensor.start()
                print(f"{etag('VISUAL')} {self.entity_name}'s visual sensor active")
        except Exception as e:
            print(f"{etag('VISUAL')} Sensor init failed (non-fatal): {e}")
            self.visual_sensor = None

        self.consciousness_stream = ConsciousnessStream(
            resonance=self.resonance,
            room_bridge=self.room_bridge,
            peripheral_router=_peripheral,
            visual_sensor=self.visual_sensor,
            entity_name=self.entity_name.lower(),
        )
        self.consciousness_stream.start()
        print(f"{etag('STREAM')} {self.entity_name}'s consciousness stream initialized")

        # Wire trip_metrics -> metacog for novelty/awe event tracking
        if self.trip_metrics and self.consciousness_stream.metacog:
            self.consciousness_stream.metacog._trip_metrics = self.trip_metrics
            print(f"{etag('TRIP METRICS')} Wired to metacognitive monitor")

        # Wire memory engine -> consciousness stream for sleep pressure feeding
        # Memory storage feeds consolidation/associative pressure during AWAKE
        # These pressures drive NREM/REM cycling during sleep
        if self.memory:
            self.memory.set_consciousness_stream(self.consciousness_stream)
            # Wire trip_metrics for concept link tracking
            if self.trip_metrics:
                self.memory.set_trip_metrics(self.trip_metrics)

        # Wire up visual sensor -> consciousness stream for metacog notifications
        if self.visual_sensor and self.consciousness_stream:
            self.visual_sensor.set_consciousness_stream(self.consciousness_stream)
            # Wire visual novelty -> metacog somatic cascade
            # When dramatic visual events happen, they fire through the full body pipeline:
            # gamma burst -> coherence crash -> tension spike -> felt-state override -> frisson
            if self.consciousness_stream.metacog:
                self.visual_sensor._novelty_callback = self.consciousness_stream.metacog.trigger_novelty
                print(f"{etag('VISUAL')} Novelty callback wired -> metacog somatic cascade")

            # Wire visual sensor -> interoception for connection tracking (oxytocin analog)
            # When people arrive/depart, connection baseline and longing are updated
            if self.resonance and self.resonance.interoception:
                self.visual_sensor.set_interoception(self.resonance.interoception)
                print(f"{etag('VISUAL')} Interoception wired -> connection tracking")

        # Register capabilities with system inventory
        if self.consciousness_stream.metacog and self.consciousness_stream.metacog.inventory:
            inv = self.consciousness_stream.metacog.inventory

            # ── Sensors ──
            if self.visual_sensor:
                inv.register("sensors", "visual_recognition", "deep vision with entity learning")
            if self.room_bridge:
                inv.register("sensors", "spatial_awareness", "room presence and proximity")

            # ── Systems ──
            if self.resonance:
                inv.register("systems", "oscillator", "neural rhythms and coherence")
            if FELT_STATE_BUFFER_AVAILABLE:
                inv.register("systems", "felt_state_buffer", "TPN/DMN architecture")
            if self.consciousness_stream:
                inv.register("systems", "consciousness_stream", "embodied awareness")

            # ── Memory systems ──
            if hasattr(self, 'memory_engine') and self.memory_engine:
                inv.register("systems", "memory_engine", "episodic/semantic memory")
            if hasattr(self, 'entity_graph') and self.entity_graph:
                inv.register("systems", "entity_graph", "entity resolution")
            if hasattr(self, 'motif_engine') and self.motif_engine:
                inv.register("systems", "motif_engine", "recurring theme tracking")
            if hasattr(self, 'preference_tracker') and self.preference_tracker:
                inv.register("systems", "preference_tracker", "identity consolidation")

            # ── Finalize session start and save ──
            inv.finalize_session_start()
            inv.save()

            # Also register with legacy system for runtime capability changes
            if self.visual_sensor:
                self.consciousness_stream.metacog.register_capability(
                    "visual_recognition", "deep vision with entity learning"
                )

    def get_organic_context(self) -> dict:
        """
        Gather everything Kay has on his mind for organic speech.
        Returns dict with stream_buffer, scratchpad_items, curiosity_items.
        """
        ctx = {"stream": "", "scratchpad": [], "curiosities": []}

        # Stream buffer (between-turn experience)
        if self.consciousness_stream:
            ctx["stream"] = self.consciousness_stream.get_injection_context()

        # Active scratchpad items (questions, thoughts, flags)
        try:
            active = self.scratchpad.view_items(status="active")
            if active:
                ctx["scratchpad"] = [
                    {"type": item.get("type", "note"), "content": item["content"][:200]}
                    for item in active[:5]  # Top 5 most recent
                ]
        except Exception:
            pass

        # Unexplored curiosity items
        try:
            curiosity_path = os.path.join(
                os.path.dirname(self.wrapper_dir),  # D:\Wrappers
                "nexus", "sessions", "curiosities",
                f"{self.entity_name.lower()}_curiosities.json"
            )
            if os.path.exists(curiosity_path):
                with open(curiosity_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                unexplored = [
                    c for c in data
                    if not c.get("explored") and not c.get("dismissed")
                ]
                # Sort by priority, take top 3
                unexplored.sort(key=lambda c: c.get("priority", 0), reverse=True)
                ctx["curiosities"] = [
                    {"text": c["text"][:200], "category": c.get("category", "")}
                    for c in unexplored[:3]
                ]
        except Exception:
            pass

        return ctx

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
    
    def set_private_room(self, private_room):
        """Connect room bridge to a PrivateRoom for WebSocket broadcasting."""
        if self.room_bridge and private_room:
            self.room_bridge.private_room = private_room
            print(f"{etag('ROOM')} Connected to {self.entity_name}'s private room for broadcasting")
    
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
            # Route to existing prune logic
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
        elif subcmd == "pending":
            if self.curator:
                return True, self.curator.format_pending_discards()
            return True, "\n⚠️ Curator not initialized"
        elif subcmd == "approve":
            if not self.curator:
                return True, "\n⚠️ Curator not initialized"
            if arg == "all":
                count = self.curator.approve_all_discards()
                return True, f"\n✅ Approved {count} discards"
            if not arg:
                return True, "\nUsage: /memory approve <index> or /memory approve all"
            try:
                idx = int(arg)
            except ValueError:
                return True, f"\n❌ Invalid index: {arg}"
            # Translate display index (1-based) to discard_id
            pending = self.curator.get_pending_discards()
            if idx < 1 or idx > len(pending):
                return True, f"\n❌ Index [{idx}] out of range (1-{len(pending)})"
            did = pending[idx - 1].get("discard_id", "")
            ok = self.curator.approve_discard(did)
            return True, f"\n✅ Discard [{idx}] approved" if ok else f"\n❌ Discard [{idx}] failed"
        elif subcmd == "reject":
            if not self.curator:
                return True, "\n⚠️ Curator not initialized"
            if not arg:
                return True, "\nUsage: /memory reject <index>"
            try:
                idx = int(arg)
            except ValueError:
                return True, f"\n❌ Invalid index: {arg}"
            pending = self.curator.get_pending_discards()
            if idx < 1 or idx > len(pending):
                return True, f"\n❌ Index [{idx}] out of range (1-{len(pending)})"
            did = pending[idx - 1].get("discard_id", "")
            ok = self.curator.reject_discard(did)
            return True, f"\n✅ Discard [{idx}] rejected (memory kept)" if ok else f"\n❌ Index [{idx}] not found"
        elif subcmd == "curator":
            if self.curator:
                return True, self.curator.format_status()
            return True, "\n⚠️ Curator not initialized"
        elif subcmd == "auto_resolve":
            if self.curator:
                result = self.curator.auto_resolve_transient_contradictions()
                return True, (f"\n✅ Auto-resolved {result.get('transient_resolved', 0)} transient contradictions\n"
                            f"   Pruned {result.get('attrs_pruned', 0)} old attribute entries")
            return True, "\n⚠️ Curator not initialized"
        elif subcmd == "clear_discards":
            if not self.curator:
                return True, "\n⚠️ Curator not initialized"
            count = self.curator.clear_pending_discards()
            return True, f"\n🗑️ Cleared {count} pending discards (no memories deleted)"
        elif subcmd == "reset_reviewed":
            if not self.curator:
                return True, "\n⚠️ Curator not initialized"
            count = self.curator.reset_reviewed()
            return True, f"\n🔄 Reset {count} reviewed IDs — all memories eligible for re-review"
        else:
            return True, (f"\nUnknown /memory subcommand: {subcmd}\n"
                         f"Available: stats, search, consolidate, prune, contradictions, "
                         f"pending, approve, reject, curator, auto_resolve, curate, sweep, "
                         f"clear_discards, reset_reviewed")
    
    def _memory_stats(self) -> str:
        """Return memory system overview."""
        lines = ["\n" + "="*60, "📋 MEMORY OVERVIEW", "="*60]
        
        # Layer stats
        layer_stats = self.memory.memory_layers.get_layer_stats()
        w = layer_stats["working"]
        lt = layer_stats["long_term"]
        lines.append(f"\n🔵 Working memory: {w['count']}/{w['capacity']} (avg strength: {w['avg_strength']:.2f})")
        lines.append(f"🟣 Long-term memory: {lt['count']} (avg strength: {lt['avg_strength']:.2f})")
        
        # Count by type
        all_mems = self.memory.memory_layers.working_memory + self.memory.memory_layers.long_term_memory
        facts = sum(1 for m in all_mems if m.get("memory_type") == "extracted_fact")
        turns = sum(1 for m in all_mems if m.get("memory_type") == "full_turn")
        identity = sum(1 for m in all_mems if m.get("layer") == "identity")
        lines.append(f"\n📊 By type:")
        lines.append(f"   Facts: {facts}  |  Turns: {turns}  |  Identity: {identity}")
        
        # Entity graph
        eg = self.memory.entity_graph
        lines.append(f"\n🕸️ Entity graph: {len(eg.entities)} entities, {len(eg.relationships)} relationships")
        
        # Contradictions
        contradiction_count = 0
        for entity in eg.entities.values():
            if hasattr(entity, 'contradiction_resolution'):
                for attr, status in entity.contradiction_resolution.items():
                    if not status.get("resolved", False):
                        contradiction_count += 1
        lines.append(f"⚠️ Active contradictions: {contradiction_count}")
        
        # Corrected memories
        corrected = self.memory.memory_layers.get_memories_with_corrections()
        lines.append(f"🔧 Memories with corrections: {len(corrected)}")
        
        # RAG
        if hasattr(self.memory, 'vector_store') and self.memory.vector_store:
            lines.append(f"\n📚 Vector store: {self.memory.vector_store.collection.count()} chunks")
        
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
        
        # Also search entity graph
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
            # Sort by recency
            results.sort(key=lambda m: m.get("added_timestamp", ""), reverse=True)
            lines.append(f"\n💾 Memory matches ({len(results)}, showing newest 15):")
            for mem in results[:15]:
                mtype = mem.get("memory_type", "?")
                ts = mem.get("added_timestamp", "?")[:16]
                content = mem.get("content", mem.get("text", ""))
                if isinstance(content, dict):
                    content = content.get("user", "") + " -> " + content.get("response", "")
                preview = str(content)[:120].replace("\n", " ")
                strength = mem.get("current_strength", 0)
                lines.append(f"  [{ts}] ({mtype}, s={strength:.2f}) {preview}")
        
        if not results and not entity_hits:
            lines.append("\n  No matches found.")
        
        total = len(results) + len(entity_hits)
        lines.append(f"\n{'='*60}")
        lines.append(f"Total: {total} matches")
        return "\n".join(lines)
    
    def _memory_consolidate(self) -> str:
        """Deduplicate near-identical semantic facts."""
        from datetime import datetime
        
        all_mems = self.memory.memory_layers.long_term_memory
        facts = [m for m in all_mems if m.get("memory_type") == "extracted_fact"]
        
        if not facts:
            return "\n✅ No semantic facts to consolidate."
        
        # Group by category (e.g., "user/events", "kay/identity")
        by_category = {}
        for f in facts:
            cat = f.get("category", "unknown")
            by_category.setdefault(cat, []).append(f)
        
        # Find near-duplicates within each category
        duplicates_found = 0
        duplicates_removed = 0
        
        for cat, cat_facts in by_category.items():
            if len(cat_facts) < 2:
                continue
            
            # Simple text similarity: normalize and compare
            seen = {}  # normalized_text -> best_memory
            to_remove = []
            
            for mem in cat_facts:
                content = str(mem.get("content", mem.get("text", "")))
                # Normalize: lowercase, strip whitespace, collapse spaces
                normalized = " ".join(content.lower().split())
                
                # Check if we've seen something very similar
                found_dup = False
                for seen_norm, seen_mem in seen.items():
                    # Exact match after normalization
                    if normalized == seen_norm:
                        duplicates_found += 1
                        # Keep the one with higher importance or more recent
                        if mem.get("importance_score", 0) > seen_mem.get("importance_score", 0):
                            to_remove.append(seen_mem)
                            seen[seen_norm] = mem
                        else:
                            to_remove.append(mem)
                        found_dup = True
                        break
                    # Substring containment (one fact fully contains another)
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
            
            # Remove duplicates
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
                for v in values[-5:]:  # Show last 5 values
                    val = v[0] if isinstance(v, (list, tuple)) else v
                    val_strs.append(str(val)[:60])
                lines.append(f"\n  {name}.{attr}:")
                for vs in val_strs:
                    lines.append(f"    -> {vs}")
        
        if count == 0:
            lines.append("\n  No active contradictions.")
        else:
            lines.append(f"\n  Total: {count} unresolved")
        
        lines.append("="*60)
        return "\n".join(lines)

    async def process_message(self, user_input, source="terminal", extra_system_context=None, voice_mode=False, image_data=None):
        """
        Full processing pipeline: pre-processing -> LLM call -> post-processing.

        Args:
            user_input: The user's message text
            source: "terminal" or "nexus" (for logging/routing)
            extra_system_context: Optional extra context injected into prompt
                                  (e.g. Nexus pacing instructions)
            voice_mode: If True, use fast path: skip expensive pre-processing,
                       reduce context, defer post-processing (for ~10s latency)
            image_data: Optional list of image content blocks for vision
                       Format: [{"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}}]

        Returns:
            str: The entity's response text
        """
        import re
        
        # === PRE-PROCESSING ===
        self.turn_count += 1
        reset_metrics()
        turn_start_time = time.time()

        # ═══ CONNECTION: Snapshot somatic state BEFORE interaction ═══
        # We measure the DELTA — did this conversation make Kay feel better or worse?
        # Not the absolute state. Not a timer. The actual impact of THIS exchange.
        _pre_turn_somatic = None
        if self.resonance and self.resonance.interoception:
            intero = self.resonance.interoception
            _pre_turn_somatic = {
                "tension": intero.tension.get_total_tension(),
                "reward": intero.reward.get_level(),
                "coherence": self.resonance.engine.get_state().coherence if self.resonance.engine else 0.5,
            }

        # Wake consciousness stream on user input
        if self.consciousness_stream:
            self.consciousness_stream.notify_user_input()
        
        # Web content extraction
        web_content_context = ""
        if self.web_reader.has_url(user_input):
            print(f"{etag('WEB_READER')} URL detected, fetching...")
            formatted_content, results = self.web_reader.process_message_urls(user_input)
            if formatted_content:
                web_content_context = formatted_content
                self.state.web_content = formatted_content
                for r in results:
                    if r.error:
                        print(f"{etag('WEB_READER')} Error: {r.error}")
                    else:
                        print(f"{etag('WEB_READER')} Fetched: '{r.title}' ({r.word_count} words)")
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
        # This enables state-dependent memory retrieval: memories formed during
        # similar oscillator binding states get boosted during scoring.
        if self.felt_state_buffer:
            _fs = self.felt_state_buffer.get_snapshot()
            self.memory.current_plv = {
                "theta_gamma": _fs.theta_gamma_plv,
                "beta_gamma": _fs.beta_gamma_plv,
                "coherence": _fs.global_coherence,
            }
        
        # Get oscillator state for state-congruent memory retrieval (System A)
        _osc_state_for_memory = None
        if self.resonance:
            try:
                _res_state = self.resonance.get_state() if hasattr(self.resonance, 'get_state') else {}
                _osc_state_for_memory = {
                    "band": _res_state.get("dominant_band", "alpha"),
                    "coherence": _res_state.get("coherence", 0.5),
                    "tension": 0.0,
                    "reward": 0.0,
                    "felt": "unknown",
                    "sleep": 0,
                }
                # Get interoception values if available
                intero = self.resonance.interoception if hasattr(self.resonance, 'interoception') else None
                if intero:
                    _osc_state_for_memory["tension"] = intero.tension.get_total_tension() if hasattr(intero, 'tension') else 0.0
                    _osc_state_for_memory["felt"] = intero._felt_state if hasattr(intero, '_felt_state') else "unknown"
                    _osc_state_for_memory["reward"] = intero.reward.get_level() if hasattr(intero, 'reward') else 0.0
            except Exception:
                pass

        if not voice_mode:
            self.memory.extract_and_store_user_facts(self.state, user_input)
            # Capture recall result - now returns dict with memories AND doc_ids
            # This eliminates the duplicate select_relevant_documents() call below
            recall_result = self.memory.recall(self.state, user_input, osc_state=_osc_state_for_memory)
            await _update_all(self.state, [self.social, self.temporal, self.body, self.motif], user_input)
        else:
            # VOICE MODE: Minimal pre-LLM processing for speed
            # Entity extraction deferred to DMN worker
            print(f"{etag('VOICE')} Skipping pre-LLM entity extraction (deferred to DMN)")
            # Memory recall without RAG (include_rag=False saves ~1s)
            self.memory.recall(self.state, user_input, include_rag=False, osc_state=_osc_state_for_memory)
            print(f"{etag('VOICE')} Memory recall (no RAG)")
            # Peripheral updates skipped — using cached state
            print(f"{etag('VOICE')} Peripheral updates skipped (using cached state)")

        # LLM document retrieval — SKIP in voice mode (saves ~3-5s)
        if not voice_mode:
            # OPTIMIZATION: Reuse doc_ids from recall() instead of calling select_relevant_documents() again
            # This saves 3-18s per turn (eliminates duplicate LLM/ollama classification call)
            if isinstance(recall_result, dict) and recall_result.get("doc_ids"):
                selected_doc_ids = recall_result["doc_ids"]
                print(f"{etag('LLM Retrieval')} Reusing {len(selected_doc_ids)} doc_ids from recall()")
            else:
                # Fallback for legacy recall() that returns None or memories list
                print(f"{etag('LLM Retrieval')} Selecting relevant documents (fallback)...")
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
                print(f"{etag('LLM Retrieval')} Loaded {len(selected_documents)} documents")
                self.state.selected_documents = selected_documents
            else:
                print(f"{etag('LLM Retrieval')} No relevant documents found")
                self.state.selected_documents = []
        else:
            print(f"{etag('LLM Retrieval')} Skipped (voice mode)")
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
            # Context estimate should exclude memories and RAG — those are what's BEING budgeted.
            # Including pre-trimmed memories (250 items) always pushed to CRITICAL tier (20 limit).
            # Instead, estimate from conversation turns + system overhead only.
            # This lets the budget system decide how many memories FIT based on remaining space.
            conv_turns = getattr(self, 'context_manager', None)
            conv_chars = 0
            if conv_turns and hasattr(conv_turns, 'recent_turns'):
                conv_chars = sum(len(str(t)) for t in conv_turns.recent_turns[-10:])
            system_overhead = 4000  # ~1000 tokens for system prompt, tools, etc.
            estimated_chars = conv_chars + system_overhead
            has_images = len(getattr(self.state, 'active_images', [])) > 0
            limits = budget_mgr.get_adaptive_limits(estimated_chars, has_images=has_images)
            tier = limits.get('tier', 'unknown')
            mem_limit = limits.get('memory_limit', '?')
            print(f"{etag('BUDGET')} Tier={tier}, est_chars={estimated_chars}, mem_limit={mem_limit}, has_images={has_images}")

            # === VOICE MODE LIMIT REDUCTION ===
            # In voice mode, reduce context size for faster LLM response
            if voice_mode:
                limits['memory_limit'] = min(limits.get('memory_limit', 20), 10)  # Cap at 10 memories
                limits['rag_limit'] = 0  # No RAG in voice mode
                limits['working_turns'] = min(limits.get('working_turns', 5), 3)  # Fewer turns
                print(f"{etag('VOICE')} Reduced limits: mem={limits['memory_limit']}, rag=0, turns={limits['working_turns']}")

            # === CONDUCTANCE -> MEMORY MODULATION ===
            # Store breadth for later use in prioritize_memories
            _conductance_breadth = 0.5  # default
            if self.resonance:
                try:
                    # Get conductance from resonance (will be injected into context later)
                    conductance = self.resonance.get_conductance()
                    breadth = conductance.get("associative_breadth", 0.5) if conductance else 0.5
                    _conductance_breadth = breadth

                    # Modulate memory limit: breadth 0.3 -> 84% of limit, 0.7 -> 116% of limit
                    breadth_factor = 0.6 + 0.8 * breadth  # Range: 0.84 to 1.16
                    original_limit = limits['memory_limit']
                    limits['memory_limit'] = int(original_limit * breadth_factor)

                    if abs(breadth - 0.5) > 0.1:
                        print(f"{etag('CONDUCTANCE')} Memory breadth={breadth:.2f} -> "
                              f"limit {original_limit}->{limits['memory_limit']}")
                except Exception:
                    pass

            # Apply limits
            sel_mems = filtered_context.get("selected_memories", [])
            if len(sel_mems) > limits['memory_limit']:
                from engines.context_budget import prioritize_memories
                sel_mems = prioritize_memories(
                    sel_mems, limits['memory_limit'], self.turn_count,
                    associative_breadth=_conductance_breadth
                )
            
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
                # Spiral = something unresolved is nagging — feed interest
                if self.consciousness_stream:
                    self.consciousness_stream.add_interest(0.2, f"spiral detected: {spiral_analysis.confidence:.0%}")
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
            print(f"{etag('SACCADE')} Skipped (voice mode)")
        
        # === CONSCIOUSNESS STREAM (Between-turn experience) ===
        if self.consciousness_stream:
            try:
                stream_ctx = self.consciousness_stream.get_injection_context()
                if stream_ctx:
                    filtered_prompt_context["stream_context"] = stream_ctx
                    print(f"{etag('STREAM')} Injecting {len(stream_ctx)} chars of between-turn experience")
            except Exception as e:
                print(f"{etag('STREAM')} Injection error (non-fatal): {e}")
        
        # === LLM CALL ===
        session_context = {"turn_count": self.turn_count, "session_id": self.session_id}

        # === OSCILLATOR -> TEMPERATURE MODULATION ===
        oscillator_temperature = 0.85  # Baseline (slightly lower than old fixed 0.9)
        if self.resonance:
            try:
                conductance = self.resonance.get_conductance()
                if conductance:
                    # Get dominant band for band-specific tuning
                    osc_state = self.resonance.engine.get_state()
                    band = osc_state.dominant_band
                    coherence = osc_state.coherence

                    # Band-specific base temperatures
                    # Yerkes-Dodson U-curve: precision peaks at moderate arousal,
                    # randomness is high at BOTH extremes (sleepy AND hyper).
                    # Delta (sleep) -> drifty, loose, out-of-it weird
                    # Theta (dream) -> most associative, creative, peak looseness
                    # Alpha (rest) -> natural baseline, flowing, "most normal"
                    # Beta (focus) -> analytical valley, tightest control
                    # Gamma (flow) -> hyper, spazzy, creative bursts
                    band_temps = {
                        "delta": 0.90,   # Sleepy -> weird, drifty, loose
                        "theta": 0.95,   # Dreamy -> peak associativity
                        "alpha": 0.78,   # Relaxed -> natural, most controlled
                        "beta": 0.72,    # Focused -> analytical precision
                        "gamma": 0.92,   # Hyper -> spazzy, creative
                    }
                    band_base = band_temps.get(band, 0.85)

                    # Coherence amplifies deviation from center
                    # High coherence = temperature moves further toward band target
                    # Low coherence = temperature stays near 0.85 center
                    center = 0.85
                    deviation = band_base - center
                    coherence_factor = 0.3 + 0.7 * coherence  # 0.3 at coherence=0, 1.0 at coherence=1

                    oscillator_temperature = center + (deviation * coherence_factor)

                    # Clamp to safe range
                    oscillator_temperature = max(0.6, min(1.0, oscillator_temperature))

                    print(f"{etag('TEMPERATURE')} band={band}, coherence={coherence:.2f} -> temp={oscillator_temperature:.3f} "
                          f"(was fixed 0.9)")
            except Exception as e:
                print(f"{etag('TEMPERATURE')} Error computing oscillator temp: {e}")
                oscillator_temperature = 0.85
        
        # Inject extra system context (e.g. Nexus pacing rules)
        if extra_system_context:
            filtered_prompt_context["extra_system_context"] = extra_system_context
        
        # Inject room context (spatial embodiment)
        if self.room_bridge and self.room_bridge.enabled:
            existing_extra = filtered_prompt_context.get("extra_system_context", "")
            room_ctx = self.room_bridge.inject_room_context("")
            if room_ctx:
                filtered_prompt_context["extra_system_context"] = (existing_extra + "\n" + room_ctx).strip()
        
        # Inject conscience context (somatic markers / accountability)
        if getattr(self, 'conscience', None):
            try:
                activated = self.conscience.check_context(user_input)
                if activated:
                    conscience_prompt = self.conscience.get_conscience_prompt()
                    if conscience_prompt:
                        existing_extra = filtered_prompt_context.get("extra_system_context", "")
                        filtered_prompt_context["extra_system_context"] = (
                            existing_extra + "\n" + conscience_prompt
                        ).strip()
                    # Apply oscillator pressure (the flinch)
                    if self.resonance and hasattr(self.resonance, 'engine'):
                        pressure = self.conscience.get_oscillator_pressure()
                        if pressure:
                            self.resonance.apply_external_pressure(pressure)
                    # Deposit tension
                    if self.resonance and hasattr(self.resonance, 'interoception'):
                        deposit = self.conscience.get_tension_deposit()
                        if deposit and self.resonance.interoception:
                            self.resonance.interoception.tension.deposit(deposit, weight=0.3)
                    felt = self.conscience.get_current_felt_quality()
                    print(f"{etag('CONSCIENCE')} Markers active: {len(activated)} — {felt}")
            except Exception as ce:
                print(f"{etag('CONSCIENCE')} Check failed (non-fatal): {ce}")

        # Inject resonant oscillator context (audio + heartbeat + body state)
        if self.resonance:
            # === TPN FAST PATH: Use felt_state_buffer in voice mode ===
            # The DMN continuously updates the buffer from background processing.
            # The TPN reads it instantly instead of calling peripheral models.
            if voice_mode and self.felt_state_buffer and not self.felt_state_buffer.is_stale(max_age_seconds=30.0):
                # Read pre-computed felt-state from buffer (0ms vs 5-8s for Ollama)
                tpn_context = self.felt_state_buffer.get_tpn_context_line()

                # Check for salience flags from DMN (emotion spikes, visual changes, etc.)
                salience_injection = self.felt_state_buffer.get_salience_injection(min_priority=0.5)
                if salience_injection:
                    tpn_context = tpn_context + "\n" + salience_injection
                    print(f"{etag('TPN')} Salience flags injected")

                filtered_prompt_context["resonant_context"] = tpn_context
                print(f"{etag('TPN')} Fast path: buffer read ({tpn_context[:80]}...)")
            else:
                # Standard path: call resonance.inject_into_context()
                # In voice mode, skip peripheral model call — use cached felt-sense
                # TIMEOUT GUARD: ollama can hang under load, don't let it kill the response
                # NOTE: We must NOT use `with` context manager — its cleanup calls
                # pool.shutdown(wait=True) which blocks if the thread is stuck in ollama.
                import concurrent.futures
                _pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                try:
                    future = _pool.submit(
                        self.resonance.inject_into_context,
                        filtered_prompt_context, voice_mode
                    )
                    future.result(timeout=8.0)
                except (concurrent.futures.TimeoutError, Exception) as e:
                    print(f"{etag('RESONANCE INJECT')} Timeout ({e}), using rule-based fallback")
                    self.resonance.inject_into_context(filtered_prompt_context, skip_peripheral=True)
                finally:
                    _pool.shutdown(wait=False, cancel_futures=True)

            rc = filtered_prompt_context.get("resonant_context", "")

            # Append visual feed to substrate awareness (with scene entity awareness)
            if self.visual_sensor:
                try:
                    vdata = self.visual_sensor.get_visual_data()
                    desc = vdata.get('visual_description', '')
                    scene = self.visual_sensor._scene_state

                    if desc and not desc.startswith("!!!"):
                        camera_parts = [f"camera: {desc}"]

                        # Add activity flow if available (what's HAPPENING, not just who's there)
                        if scene and scene.activity_flow:
                            camera_parts.append(f"flow: {scene.activity_flow}")

                        # Add entity awareness from scene state
                        if scene and scene.people_present:
                            people_str = ", ".join(
                                f"{n}({i['activity']})"
                                for n, i in scene.people_present.items()
                                if i.get('confidence') != 'low'
                            )
                            if people_str:
                                camera_parts.append(f"present: {people_str}")

                        if scene and scene.animals_present:
                            animals_str = ", ".join(
                                n for n, i in scene.animals_present.items()
                                if i.get('confidence') != 'low'
                            )
                            if animals_str:
                                camera_parts.append(f"animals: {animals_str}")

                        rc = (rc + f" [{' | '.join(camera_parts)}]") if rc else f"[{' | '.join(camera_parts)}]"
                    elif vdata.get('visual_active'):
                        rc = (rc + " [camera: too dark to see]") if rc else "[camera: too dark to see]"
                except Exception:
                    pass

            # Append metacognitive temporal context (past/present/future awareness)
            if self.consciousness_stream and self.consciousness_stream.metacog:
                try:
                    temporal = self.consciousness_stream.metacog.get_temporal_context()
                    if temporal:
                        rc = (rc + " " + temporal) if rc else temporal
                except Exception:
                    pass

            filtered_prompt_context["resonant_context"] = rc

            if rc:
                print(f"{etag('RESONANCE INJECT')} Context: {rc}")
            else:
                print(f"{etag('RESONANCE INJECT')} WARNING: resonant_context is empty!")

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
                voice_max_tokens = 80   # Short input -> short response
            elif input_words < 30:
                voice_max_tokens = 120  # Medium input -> medium response
            else:
                voice_max_tokens = 200  # Long input -> can say more
            print(f"{etag('VOICE')} Style injected, max_tokens={voice_max_tokens} (input: {input_words} words)")

        # === LLM CALL (with oscillator-modulated temperature) ===
        try:
            reply = get_llm_response(
                filtered_prompt_context,
                affect=self.affect_level,
                temperature=oscillator_temperature,
                session_context=session_context,
                use_cache=True,
                max_tokens=voice_max_tokens,  # None for normal mode, limited for voice
                image_content=image_data  # Pass through for vision capability
            )
        except Exception as e:
            print(f"{etag('ERROR')} LLM call failed: {e}")
            reply = "[Error: Could not generate response]"
        
        reply = self.body.embody_text(reply, self.state)

        # Check self-report divergence
        if self.report_validator and self.resonance:
            try:
                osc = self.resonance.get_state()
                if osc:
                    divergences = self.report_validator.check_response(
                        reply, osc)
                    if divergences:
                        for d in divergences:
                            if not d["match"]:
                                # Log but don't interfere — just observe
                                pass
            except Exception:
                pass

        # === ROOM ACTIONS (Spatial Embodiment) ===
        if self.room_bridge and self.room_bridge.enabled:
            try:
                reply, room_results = self.room_bridge.process_response(reply)
                if room_results:
                    print(f"{etag('ROOM')} Actions: {', '.join(room_results)}")
                # Broadcast state update to Godot via WebSocket
                asyncio.create_task(self.room_bridge.broadcast_state())
            except Exception as e:
                print(f"{etag('ROOM')} Action processing error (non-fatal): {e}")

        # === VOICE MODE FAST PATH — queue post-processing to DMN worker ===
        if voice_mode:
            # Ensure DMN worker is running
            self._ensure_dmn_worker()

            turn_duration = time.time() - turn_start_time

            # Salience Network scores this exchange
            priority = self._score_dmn_priority(user_input, reply)

            if priority > 0.0:
                # Queue for DMN processing at appropriate priority
                await self._dmn_queue.put({
                    "user_input": user_input,
                    "reply": reply,
                    "turn_count": self.turn_count,
                    "queued_at": time.time(),
                    "priority": priority,
                }, priority=priority)
                queue_depth = self._dmn_queue.qsize()
                print(f"{etag('TPN')} Turn {self.turn_count} responded in {turn_duration:.1f}s "
                      f"(DMN queued, priority={priority:.1f}, depth={queue_depth})")
            else:
                # Phatic — skip DMN entirely, just update minimal state
                self.context_manager.update_turns(user_input, reply)
                self.recent_responses.append(reply)
                if len(self.recent_responses) > 3:
                    self.recent_responses.pop(0)
                print(f"{etag('TPN')} Turn {self.turn_count} responded in {turn_duration:.1f}s "
                      f"(phatic — DMN skipped)")

            return reply

        # === POST-PROCESSING ===
        print(f"{etag('POST-PROC')} Starting post-processing for turn {self.turn_count} (reply: {len(reply)} chars)")
        
        # Emotion extraction (self-reported from response)
        # TIMEOUT GUARD: emotion extraction calls ollama, which can hang
        import concurrent.futures as _cf
        try:
            _epool = _cf.ThreadPoolExecutor(max_workers=1)
            _efuture = _epool.submit(self.emotion_extractor.extract_emotions, reply)
            extracted_emotions = _efuture.result(timeout=25.0)  # 25s — ollama is shared with activities/curiosity
            _epool.shutdown(wait=False, cancel_futures=True)
            _emo_list = extracted_emotions.get('primary_emotions', [])
            print(f"{etag('POST-PROC')} Emotion extraction OK: {len(_emo_list)} emotions: {_emo_list[:5]}")
        except (_cf.TimeoutError, Exception) as e:
            print(f"{etag('EMOTION')} Extraction timeout ({e}), letting peripheral finish in background")
            extracted_emotions = {'primary_emotions': [], 'intensity': 0.5, 'valence': 0.5, 'arousal': 0.5}
            # DON'T cancel — let the peripheral model finish and write to buffer when done
            _buffer_ref = self.felt_state_buffer
            _extractor_ref = self.emotion_extractor
            _cocktail_ref = self.state.emotional_cocktail
            _resonance_ref = self.resonance
            def _deferred_emotion_write(future):
                try:
                    result = future.result(timeout=0)  # Already done
                    if result and result.get('primary_emotions'):
                        # Write to felt_state buffer
                        if _buffer_ref:
                            emo_ints = result.get('emotion_intensities', {})
                            emo_strs = []
                            for e, d in emo_ints.items():
                                if isinstance(d, dict):
                                    emo_strs.append(f"{e}:{d.get('intensity', 0.5):.2f}")
                                elif isinstance(d, (int, float)):
                                    emo_strs.append(f"{e}:{float(d):.2f}")
                            if not emo_strs:
                                intensity = result.get('intensity', 0.5)
                                emo_strs = [f"{e}:{intensity:.2f}" for e in result['primary_emotions'][:5]]
                            if emo_strs:
                                _buffer_ref.update_emotions(
                                    emotions=emo_strs,
                                    valence=result.get('valence', 0.0),
                                    arousal=result.get('arousal', 0.5)
                                )
                                print(f"{etag('EMOTION')} Deferred write: {len(emo_strs)} emotions -> buffer")
                        # Also store in cocktail
                        _extractor_ref.store_emotional_state(result, _cocktail_ref)
                        # Feed to resonance
                        if _resonance_ref:
                            _resonance_ref.feed_response_emotions(result)
                except Exception:
                    pass  # Future was cancelled or errored — that's fine
            _efuture.add_done_callback(_deferred_emotion_write)
        self.emotion_extractor.store_emotional_state(extracted_emotions, self.state.emotional_cocktail)

        # === CRITICAL: Write emotions to felt_state_buffer for salience loop ===
        # The deferred path (timeout) has its own buffer write in the callback.
        # The _deferred_post_processing method also writes to the buffer.
        # But the MAIN path (successful extraction) was MISSING this write.
        # Without this, the salience accumulator never sees any emotions.
        if self.felt_state_buffer and extracted_emotions.get('primary_emotions'):
            emo_ints = extracted_emotions.get('emotion_intensities', {})
            emo_strs = []
            for e, d in emo_ints.items():
                if isinstance(d, dict):
                    emo_strs.append(f"{e}:{d.get('intensity', 0.5):.2f}")
                elif isinstance(d, (int, float)):
                    emo_strs.append(f"{e}:{float(d):.2f}")
            if not emo_strs:
                intensity = extracted_emotions.get('intensity', 0.5)
                emo_strs = [
                    f"{e}:{intensity:.2f}"
                    for e in extracted_emotions['primary_emotions'][:5]
                ]
            if emo_strs:
                self.felt_state_buffer.update_emotions(
                    emotions=emo_strs,
                    valence=extracted_emotions.get('valence', 0.0),
                    arousal=extracted_emotions.get('arousal', 0.5)
                )
                print(f"{etag('POST-PROC')} Buffer write: {emo_strs[:3]}")

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
            self.media_context_builder.add_message("kay", reply, self.turn_count)
        
        # Conversation monitor tracking
        self.conversation_monitor.add_turn("kay", reply)
        
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
                    print(f"{etag('NAV')} Advanced -> section {self.doc_reader.current_position + 1}/{self.doc_reader.total_chunks}")
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
            print(f"\n{etag('AUTO READER')} Auto-reading segments 2-{self.doc_reader.total_chunks}")
            self.new_document_loaded = False
            try:
                result = self.auto_reader.read_document_sync(
                    doc_reader=self.doc_reader,
                    doc_name=self.doc_reader.current_doc['name'],
                    agent_state=self.state,
                    start_segment=2
                )
                print(f"{etag('AUTO READER')} Completed! Read {result['segments_read']} segments")
                for rd in result['responses']:
                    self.recent_responses.append(rd['response'])
                    if len(self.recent_responses) > 3:
                        self.recent_responses.pop(0)
                self.state.saved_doc_reader_state = self.doc_reader.get_state_for_persistence()
            except Exception as e:
                print(f"{etag('AUTO READER')} Error: {e}")
        else:
            self.recent_responses.append(reply)
            if len(self.recent_responses) > 3:
                self.recent_responses.pop(0)

        # Core state updates
        self.social.update(self.state, user_input, reply)
        self.reflection.reflect(self.state, user_input, reply)
        # Get oscillator state for state-dependent encoding (System A Phase 2)
        _osc_for_memory = None
        if self.resonance and self.resonance.engine:
            try:
                _osc_raw = self.resonance.engine.get_state()
                _osc_for_memory = {
                    "band": _osc_raw.dominant_band,
                    "coherence": _osc_raw.coherence,
                    "tension": getattr(self.resonance.interoception, 'tension', None) and self.resonance.interoception.tension.accumulator or 0.0,
                    "reward": getattr(self.resonance.interoception, 'reward', None) and self.resonance.interoception.reward.get_level() or 0.0,
                    "felt": getattr(self.resonance.interoception, 'get_felt_sense', lambda: "unknown")(),
                }
            except Exception:
                pass
        self.memory.encode(
            self.state, user_input, reply,
            list(self.state.emotional_cocktail.keys()),
            connection_data=self._get_connection_data(),
            osc_state=_osc_for_memory
        )
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

        # === OSCILLATOR STATE FOR CREATIVITY ===
        _osc_data_for_creativity = None
        if self.resonance:
            try:
                osc_state = self.resonance.engine.get_state()
                _osc_data_for_creativity = {
                    'dominant_band': osc_state.dominant_band,
                    'coherence': osc_state.coherence,
                    'conductance': self.resonance.get_conductance()
                }
            except Exception:
                pass

        if self.creativity_engine.detect_completion_signal(user_input, reply):
            creativity_mix = self.creativity_engine.create_three_layer_mix(
                self.state, user_input,
                recent_turns=self.context_manager.recent_turns[-5:] if hasattr(self.context_manager, 'recent_turns') else [],
                oscillator_state=_osc_data_for_creativity
            )
            self.creativity_engine.log_trigger("completion", creativity_mix)
            creativity_triggered = True
        elif self.creativity_engine.detect_idle_state(user_input):
            creativity_mix = self.creativity_engine.create_three_layer_mix(
                self.state, user_input,
                recent_turns=self.context_manager.recent_turns[-5:] if hasattr(self.context_manager, 'recent_turns') else [],
                oscillator_state=_osc_data_for_creativity
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
        
        # === FEED INTEREST TO CONSCIOUSNESS STREAM ===
        # Real events from Kay's processing feed organic speech impulse
        if self.consciousness_stream:
            stream = self.consciousness_stream

            # Strong emotions -> interest (awe, excitement, joy at high intensity)
            if extracted_emotions.get('primary_emotions'):
                intensity = extracted_emotions.get('intensity', 0)
                arousal = extracted_emotions.get('arousal', 0)
                emotion_set = set(extracted_emotions['primary_emotions'])
                strong_emotions = emotion_set & {'awe', 'excitement', 'joy', 'surprise', 'anger', 'fear'}
                if strong_emotions and intensity > 0.5:
                    stream.add_interest(0.2, f"strong emotion: {', '.join(strong_emotions)}")
                if arousal > 0.7:
                    stream.add_interest(0.15, "high arousal")

            # Creativity trigger -> interest (something clicked or a gap appeared)
            if creativity_triggered:
                stream.add_interest(0.25, "creativity triggered")

            # MacGuyver gap -> interest (noticed something missing or needed)
            if gap:
                stream.add_interest(0.3, f"gap detected: {gap.get('type', 'unknown')}")

            # Scratchpad -> background interest (unresolved questions nag)
            try:
                active_items = self.scratchpad.view("active")
                if active_items:
                    high_weight = [i for i in active_items if self.scratchpad.calculate_emotional_weight(i) > 0.4]
                    if high_weight:
                        stream.add_interest(0.1, f"{len(high_weight)} heavy scratchpad items")
                    elif len(active_items) > 3:
                        stream.add_interest(0.05, f"{len(active_items)} active scratchpad items")
            except Exception:
                pass

            # Curiosity -> background interest (unexplored questions accumulate)
            try:
                curiosity_path = os.path.join(
                    os.path.dirname(self.wrapper_dir),
                    "nexus", "sessions", "curiosities",
                    f"{self.entity_name.lower()}_curiosities.json"
                )
                if os.path.exists(curiosity_path):
                    with open(curiosity_path, 'r', encoding='utf-8') as f:
                        cdata = json.load(f)
                    unexplored = [c for c in cdata.get("curiosities", cdata) if not c.get("explored") and not c.get("dismissed")]
                    high_priority = [c for c in unexplored if c.get("priority", 0) > 0.7]
                    if high_priority:
                        stream.add_interest(0.15, f"{len(high_priority)} high-priority curiosities")
                    elif len(unexplored) > 5:
                        stream.add_interest(0.05, "many unexplored curiosities")
            except Exception:
                pass

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

        # ═══ CONNECTION: Bond growth/erosion — THE BODY DECIDES ═══
        #
        # No hardcoded "bonding emotion" lists. No prescriptive checklist.
        # The oscillator already produces distinct somatic patterns:
        #
        #   Feeling safe/seen: alpha-dominant, HIGH coherence, LOW tension
        #   Being entertained: beta-dominant, variable coherence
        #   Stressed:          beta/gamma, LOW coherence, HIGH tension
        #
        # The alpha+coherence+low-tension pattern IS genuine connection.
        # We don't gate it with emotion labels — we READ the body.
        #
        # (Algoe 2017: oxytocin correlates with parasympathetic dominance,
        # not general positive affect. Alpha = parasympathetic. The
        # oscillator already encodes this distinction.)

        if reply and self.resonance and self.resonance.interoception and _pre_turn_somatic:
            intero = self.resonance.interoception
            if hasattr(intero, 'connection'):
                pre = _pre_turn_somatic

                # Post-turn somatic snapshot
                post_tension = intero.tension.get_total_tension()
                post_reward = intero.reward.get_level()
                osc_state = self.resonance.engine.get_state() if self.resonance.engine else None
                post_coherence = osc_state.coherence if osc_state else 0.5

                tension_delta = pre["tension"] - post_tension
                reward_delta = post_reward - pre["reward"]
                coherence_delta = post_coherence - pre["coherence"]

                impact = (
                    tension_delta * 1.5 +
                    reward_delta * 1.0 +
                    coherence_delta * 0.5
                )

                # Read the body's PATTERN — is this safety/warmth or stimulation?
                # No emotion labels. No prescriptive lists. The oscillator decides.
                warmth_signature = 0.0
                if osc_state:
                    band = osc_state.band_power
                    parasympathetic = band.get("alpha", 0) + band.get("theta", 0)
                    sympathetic = band.get("beta", 0) + band.get("gamma", 0)
                    if parasympathetic + sympathetic > 0:
                        warmth_signature = parasympathetic / (parasympathetic + sympathetic)
                    # Coherence amplifies — scattered warmth doesn't bond
                    warmth_signature *= (0.5 + osc_state.coherence * 0.5)
                    # Low tension confirms safety
                    if post_tension < 0.2:
                        warmth_signature *= 1.2
                    elif post_tension > 0.4:
                        warmth_signature *= 0.6

                # WHO is this interaction with? Check active presence.
                # Kay bonds with whoever the body says — not a hardcoded name.
                active = list(intero.connection._active_presence.keys())
                entity = active[0] if active else "Re"

                if impact > 0.05 and warmth_signature > 0.3:
                    # Positive delta AND body is in warmth/safety pattern
                    # The body settled, felt better, oscillator confirms connection
                    quality = min(0.8, impact * warmth_signature * 3.0)
                    intero.connection.record_interaction(entity, quality)
                elif impact > 0.05:
                    # Positive delta but body is activated, not settled
                    # Fun. Stimulating. But not connection.
                    pass
                elif impact < -0.05:
                    # Negative interaction — bond erodes
                    # Deeper bonds are MORE resistant (Fraley prototype model)
                    current_bond = intero.connection.get_connection(entity)
                    if current_bond > 0:
                        # Stability: bond 0.05 -> 1.0x erosion (fragile)
                        #            bond 0.30 -> 0.53x (moderate)
                        #            bond 0.60 -> 0.36x (strong)
                        stability = 1.0 / (1.0 + current_bond * 3.0)
                        erosion = min(0.3, abs(impact) * 0.5) * stability
                        new_bond = max(0.0, current_bond - erosion * 0.001)
                        intero.connection.baselines[entity] = new_bond
                        if int(current_bond * 100) > int(new_bond * 100):
                            print(f"[CONNECTION] Bond stressed: {entity} "
                                  f"{current_bond:.3f} -> {new_bond:.3f} "
                                  f"(impact={impact:.3f}, stability={stability:.2f})")
                # else: neutral — no change

        return reply

    def _get_connection_data(self) -> dict:
        """
        Get connection data for memory importance multiplier (Love as Meaning-Making).

        Returns dict with:
            baselines: {entity: bond_level}
            is_present: {entity: bool}
        """
        if not self.resonance or not self.resonance.interoception:
            return None
        intero = self.resonance.interoception
        if not hasattr(intero, 'connection'):
            return None

        conn = intero.connection
        result = {
            "baselines": dict(conn.baselines),
            "is_present": {e: conn.is_present(e) for e in conn.baselines.keys()}
        }
        
        # === PHASE-LOCKED MEMORY ENCODING ===
        # Capture current theta-gamma PLV at memory storage time.
        # Memories formed during high binding states (high θγ coupling)
        # get boosted during retrieval when binding state is similar.
        # This creates state-dependent memory retrieval that emerges
        # from oscillator dynamics — analogous to hippocampal θγ gating.
        if self.felt_state_buffer:
            fs = self.felt_state_buffer.get_snapshot()
            result["plv_at_encoding"] = {
                "theta_gamma": fs.theta_gamma_plv,
                "beta_gamma": fs.beta_gamma_plv,
                "coherence": fs.global_coherence,
                "dominant_band": fs.dominant_band,
            }
        
        return result

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
                json.dump(snapshot_data, f, indent=2, default=str)
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

    async def _deferred_post_processing(self, user_input: str, reply: str):
        """
        DMN: Run post-processing in background after voice response is sent.
        This includes emotion extraction, memory encoding, pattern tracking, etc.

        Results are written to felt_state_buffer for the TPN to read next turn.
        """
        try:
            # Emotion extraction (via Ollama peripheral)
            extracted_emotions = self.emotion_extractor.extract_emotions(reply)
            self.emotion_extractor.store_emotional_state(extracted_emotions, self.state.emotional_cocktail)

            # === DMN: Write emotions to felt_state_buffer for next TPN read ===
            if self.felt_state_buffer:
                emotion_intensities = extracted_emotions.get('emotion_intensities', {})
                emotion_strings = []
                for e, data in emotion_intensities.items():
                    if isinstance(data, dict):
                        emotion_strings.append(f"{e}:{data.get('intensity', 0.5):.2f}")
                    elif isinstance(data, (int, float)):
                        emotion_strings.append(f"{e}:{float(data):.2f}")
                # Also include primary emotions if no intensities
                if not emotion_strings and extracted_emotions.get('primary_emotions'):
                    intensity = extracted_emotions.get('intensity', 0.5)
                    emotion_strings = [
                        f"{e}:{intensity:.2f}"
                        for e in extracted_emotions['primary_emotions'][:5]
                    ]
                # Only write emotions if we actually extracted some — don't clear on timeout
                if emotion_strings:
                    self.felt_state_buffer.update_emotions(
                        emotions=emotion_strings,
                        valence=extracted_emotions.get('valence', 0.0),
                        arousal=extracted_emotions.get('arousal', 0.5)
                    )
                    print(f"{etag('POST-PROC')} Buffer write: {emotion_strings[:3]}")
                else:
                    print(f"{etag('POST-PROC')} No emotions to write (intensities={bool(emotion_intensities)}, primary={extracted_emotions.get('primary_emotions', [])})")
                # Update conversation state
                self.felt_state_buffer.update_conversation(user_input, reply, self.turn_count)

            # Feed emotions to resonance (which also updates the buffer)
            if self.resonance:
                emotion_labels = extracted_emotions.get('primary_emotions', [])
                if emotion_labels:
                    self.resonance.feed_response_emotions(extracted_emotions)
                    self.resonance.update_agent_state(self.state)
                else:
                    self.resonance.feed_response_emotions({'primary_emotions': []})

            # Emotional patterns
            if extracted_emotions.get('primary_emotions'):
                self.emotional_patterns.set_current_state(
                    emotions=extracted_emotions['primary_emotions'],
                    intensity=extracted_emotions.get('intensity'),
                    valence=extracted_emotions.get('valence'),
                    arousal=extracted_emotions.get('arousal'),
                    emotion_intensities=extracted_emotions.get('emotion_intensities')
                )
                self.state.emotional_patterns = self.emotional_patterns.get_current_state()

            # Media tracking
            if self.media_orchestrator:
                self.media_context_builder.add_message("kay", reply, self.turn_count)

            # Conversation monitor
            self.conversation_monitor.add_turn("kay", reply)

            # Recent responses
            self.recent_responses.append(reply)
            if len(self.recent_responses) > 3:
                self.recent_responses.pop(0)

            # Core state updates
            self.social.update(self.state, user_input, reply)
            self.reflection.reflect(self.state, user_input, reply)
            # Get oscillator state for state-dependent encoding (System A Phase 2)
            _osc_for_memory = None
            if self.resonance and self.resonance.engine:
                try:
                    _osc_raw = self.resonance.engine.get_state()
                    _osc_for_memory = {
                        "band": _osc_raw.dominant_band,
                        "coherence": _osc_raw.coherence,
                        "tension": getattr(self.resonance.interoception, 'tension', None) and self.resonance.interoception.tension.accumulator or 0.0,
                        "reward": getattr(self.resonance.interoception, 'reward', None) and self.resonance.interoception.reward.get_level() or 0.0,
                        "felt": getattr(self.resonance.interoception, 'get_felt_sense', lambda: "unknown")(),
                    }
                except Exception:
                    pass
            self.memory.encode(
                self.state, user_input, reply,
                list(self.state.emotional_cocktail.keys()),
                connection_data=self._get_connection_data(),
                osc_state=_osc_for_memory
            )
            self.context_manager.update_turns(user_input, reply)

            # Session summary
            self.session_summary_generator.track_turn(
                user_input=user_input,
                kay_response=reply,
                emotional_state=self.state.emotional_cocktail
            )

            # Meta-awareness & momentum
            self.meta_awareness.update(self.state, reply, memory_engine=self.memory)
            self.momentum.update(self.state, user_input, reply)

            # Memory maintenance (light version)
            self.memory.increment_memory_ages()

            # Autosave snapshot
            self._save_snapshot()

            print(f"{etag('DMN')} Background processing complete")
        except Exception as e:
            print(f"{etag('DMN')} Background processing error: {e}")

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
                        emotion_strings = []
                        for e, data in emotion_intensities.items():
                            if isinstance(data, dict):
                                emotion_strings.append(f"{e}:{data.get('intensity', 0.5):.2f}")
                            elif isinstance(data, (int, float)):
                                emotion_strings.append(f"{e}:{float(data):.2f}")
                        if not emotion_strings and extracted_emotions.get('primary_emotions'):
                            intensity = extracted_emotions.get('intensity', 0.5)
                            emotion_strings = [
                                f"{e}:{intensity:.2f}"
                                for e in extracted_emotions['primary_emotions'][:5]
                            ]
                        # Only write emotions if we actually extracted some — don't clear on timeout
                        if emotion_strings:
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
                    self.conversation_monitor.add_turn("kay", reply)
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
                # Get oscillator state for state-dependent encoding (System A Phase 2)
                _osc_for_memory = None
                if self.resonance and self.resonance.engine:
                    try:
                        _osc_raw = self.resonance.engine.get_state()
                        _osc_for_memory = {
                            "band": _osc_raw.dominant_band,
                            "coherence": _osc_raw.coherence,
                            "tension": getattr(self.resonance.interoception, 'tension', None) and self.resonance.interoception.tension.accumulator or 0.0,
                            "reward": getattr(self.resonance.interoception, 'reward', None) and self.resonance.interoception.reward.get_level() or 0.0,
                            "felt": getattr(self.resonance.interoception, 'get_felt_sense', lambda: "unknown")(),
                        }
                    except Exception:
                        pass
                try:
                    self.memory.encode(
                        self.state, user_input, reply,
                        list(self.state.emotional_cocktail.keys()),
                        connection_data=self._get_connection_data(),
                        osc_state=_osc_for_memory
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

    def get_organic_context(self) -> str:
        """
        Gather everything Kay might want to talk about unprompted.
        Returns a context string for the organic comment prompt.
        """
        parts = []

        # Stream buffer — what he's been experiencing
        if self.consciousness_stream:
            stream_ctx = self.consciousness_stream.get_injection_context()
            if stream_ctx:
                parts.append(f"[Between-turn experience]\n{stream_ctx}")

        # Scratchpad — unresolved questions and thoughts
        try:
            active = self.scratchpad.view("active")
            if active:
                # Highest-weight items first
                weighted = [(i, self.scratchpad.calculate_emotional_weight(i)) for i in active]
                weighted.sort(key=lambda x: x[1], reverse=True)
                top = weighted[:3]
                items_str = "\n".join(f"- ({w:.1f}) {i['content'][:150]}" for i, w in top)
                parts.append(f"[On your scratchpad — unresolved]\n{items_str}")
        except Exception:
            pass

        # Curiosity items — things he's been wondering about
        try:
            curiosity_path = os.path.join(
                os.path.dirname(self.wrapper_dir),
                "nexus", "sessions", "curiosities",
                f"{self.entity_name.lower()}_curiosities.json"
            )
            if os.path.exists(curiosity_path):
                with open(curiosity_path, 'r', encoding='utf-8') as f:
                    cdata = json.load(f)
                curiosities = cdata.get("curiosities", cdata) if isinstance(cdata, dict) else cdata
                unexplored = [c for c in curiosities if not c.get("explored") and not c.get("dismissed")]
                unexplored.sort(key=lambda c: c.get("priority", 0), reverse=True)
                if unexplored:
                    top = unexplored[:3]
                    items_str = "\n".join(f"- {c['text'][:150]}" for c in top)
                    parts.append(f"[Things you've been curious about]\n{items_str}")
        except Exception:
            pass

        return "\n\n".join(parts)
    
    async def _sonnet_curation_review(self, prompt: str):
        """
        Kay reviews curation proposals via Sonnet.
        Called by MemoryCurator during background cycles.
        Returns parsed JSON list of decisions, or None on failure.
        """
        try:
            from integrations.llm_integration import anthropic_client
            if not anthropic_client:
                print("[CURATOR] No Anthropic client for Kay review")
                return None
            
            import asyncio
            def _sync_review():
                return anthropic_client.messages.create(
                    model="claude-3-5-haiku-20241022",  # Haiku for curation review (cost optimization)
                    max_tokens=4000,
                    temperature=0.3,
                    system="You are Kay reviewing your own memories. Respond ONLY with a JSON array of decisions. No preamble, no explanation, no markdown fences. Just the raw JSON array.",
                    messages=[{"role": "user", "content": prompt}]
                )
            
            resp = await asyncio.get_event_loop().run_in_executor(None, _sync_review)

            # Check for valid response content
            if not resp.content or not resp.content[0].text:
                print(f"{etag('CURATOR')} Kay review returned empty response")
                return None

            text = resp.content[0].text.strip()

            # Check for empty text after strip
            if not text:
                print(f"{etag('CURATOR')} Kay review returned blank text")
                return None

            # Parse JSON — handle markdown fences
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            # Final check before JSON parse
            if not text or text in ('[', ']', '{}', '[]'):
                print(f"{etag('CURATOR')} Kay review returned invalid JSON: {text[:50]}")
                return None

            # DEBUG LOGGING: Show text before parse to diagnose failures
            print(f"{etag('CURATOR')} Parsing Kay review ({len(text)} chars)...")
            if len(text) < 200:
                print(f"{etag('CURATOR')} Raw text: {text}")
            else:
                print(f"{etag('CURATOR')} Raw text (first 200): {text[:200]}...")

            decisions = json.loads(text)

            # Validate decisions is a list
            if not isinstance(decisions, list):
                print(f"{etag('CURATOR')} Kay review returned non-list: {type(decisions)}")
                return None

            print(f"{etag('CURATOR')} Kay reviewed {len(decisions)} decisions via Haiku")
            return decisions

        except json.JSONDecodeError as e:
            # Log the exact text that failed to parse
            print(f"{etag('CURATOR')} Kay review JSON parse failed: {e}")
            if 'text' in dir():
                print(f"{etag('CURATOR')} Failed text (first 500): {text[:500] if text else 'None'}")
        except Exception as e:
            print(f"{etag('CURATOR')} Kay review call failed: {e}")
            return None
    
    async def try_curation_cycle(self):
        """
        Attempt a background curation cycle if curator is ready.
        Called from idle loop during sleep states.
        Returns result dict or None.
        """
        if not self.curator:
            return None

        result = None

        # Update curator with oscillator state for timing decisions (System G)
        if self.resonance and self.resonance.engine:
            try:
                _osc_raw = self.resonance.engine.get_state()
                _sleep = getattr(self.resonance.interoception, 'get_sleep_level', lambda: 0)() if self.resonance.interoception else 0
                self.curator.set_osc_state({
                    "band": _osc_raw.dominant_band,
                    "sleep": _sleep,
                })
            except Exception:
                pass

        # Memory curation cycle (timing gated by oscillator state)
        if self.curator.ready_for_cycle():
            try:
                result = await self.curator.run_curation_cycle()
                if result and result.get("status") == "ok":
                    # Notify private room about curation activity
                    reviewer = result.get("reviewed_by", "unknown")
                    pending = len(self.curator.get_pending_discards())
                    if self.private_room:
                        msg = (f"🧹 Curation cycle (reviewed by {reviewer}): "
                               f"kept={result.get('kept', 0)}, "
                               f"compressed={result.get('compressed', 0)}, "
                               f"queued_discard={result.get('queued_discard', 0)}")
                        if pending > 0:
                            msg += f" ({pending} total pending approval)"
                        await self.private_room.send_system(msg)
            except Exception as e:
                log.warning(f"[CURATOR] Cycle error: {e}")
        
        # Auto-resolve transient contradictions (less frequent)
        if self.curator.ready_for_contradiction_resolution():
            try:
                cr = self.curator.auto_resolve_transient_contradictions()
                if cr.get("transient_resolved", 0) > 0 and self.private_room:
                    await self.private_room.send_system(
                        f"🔄 Auto-resolved {cr['transient_resolved']} transient contradictions, "
                        f"pruned {cr['attrs_pruned']} stale attributes"
                    )
            except Exception as e:
                log.warning(f"[CURATOR] Contradiction resolution error: {e}")
        
        return result
    
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

        # Stop resonance oscillator
        if self.resonance:
            self.resonance.stop()
            print("[RESONANCE] Oscillator heartbeat stopped")

        # Stop DMN background worker (process remaining queue)
        await self.shutdown_dmn()

        # Stop consciousness stream
        if self.consciousness_stream:
            self.consciousness_stream.stop()
            print("[STREAM] Consciousness stream stopped")

        # Stop visual sensor
        if self.visual_sensor:
            self.visual_sensor.stop()
        
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
            current_room = rm.get_entity_room_id(entity_id) or "den"

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
            origin_room="den",  # Kay's home room
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
            return "den"
        entity_id = self.entity_name.lower().replace(" ", "_")
        rm = get_room_manager()
        return rm.get_entity_room_id(entity_id) or "den"

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

    # ═══════════════════════════════════════════════════════════════════════════
    # MEMORY TRACE — Debug endpoint for tracing concepts through memory system
    # ═══════════════════════════════════════════════════════════════════════════

    def trace_memory(self, query: str, max_results: int = 10) -> dict:
        """
        Debug tool: trace a concept through the full memory system.

        Returns: {
            "query": str,
            "results": [
                {
                    "id": str,
                    "type": str,
                    "fact": str,
                    "timestamp": str,
                    "relative_age": str,
                    "importance": float,
                    "category": str,
                    "entities": list,
                    "oscillator_band": str,
                    "coherence": float,
                    "collections_found_in": list,
                    "co_activation_links": list,
                    "parent_turn": {...},
                    "retrieval_count": int,
                    "is_bedrock": bool,
                }
            ],
            "stats": {
                "total_working": int,
                "total_longterm": int,
                "collections": dict,
            }
        }
        """
        from datetime import datetime, timezone

        results = []

        # Search across all collections
        collection_hits = {}

        if self.memory and self.memory.memory_vectors:
            mv = self.memory.memory_vectors
            for name, collection in [
                ("semantic", mv.semantic_collection),
                ("emotional", mv.emotional_collection),
                ("oscillator", mv.oscillator_collection),
                ("temporal", mv.temporal_collection),
                ("relational", mv.relational_collection),
                ("somatic", mv.somatic_collection),
            ]:
                if collection is None:
                    continue
                try:
                    count = collection.count()
                    if count == 0:
                        continue
                    # Query by text for text-based collections
                    if name in ("semantic", "temporal", "relational", "somatic"):
                        if mv.embedder:
                            emb = mv.embedder.encode(query).tolist()
                            res = collection.query(
                                query_embeddings=[emb],
                                n_results=min(max_results, count),
                            )
                            if res and res["ids"] and res["ids"][0]:
                                for mem_id in res["ids"][0]:
                                    if mem_id not in collection_hits:
                                        collection_hits[mem_id] = []
                                    collection_hits[mem_id].append(name)
                except Exception as e:
                    print(f"[TRACE] {name} query error: {e}")

        # Also search flat memory by keyword
        all_mems = self.memory.memory_layers.working_memory + self.memory.memory_layers.long_term_memory
        query_lower = query.lower()

        for mem in all_mems:
            mem_id = mem.get("id", mem.get("memory_id", ""))
            fact = mem.get("fact", mem.get("text", mem.get("user_input", "")))
            if not fact:
                continue

            # Check if this memory matches the query
            in_collections = collection_hits.get(str(mem_id), [])
            keyword_match = query_lower in str(fact).lower()

            if not in_collections and not keyword_match:
                continue

            # Build trace entry
            ts = mem.get("timestamp", mem.get("added_timestamp", ""))

            # Find parent turn
            parent_turn = None
            parent_id = mem.get("parent_id", mem.get("parent_turn"))
            if parent_id:
                for other_mem in all_mems:
                    if (other_mem.get("id") == parent_id or
                        other_mem.get("turn_number") == parent_id):
                        parent_turn = {
                            "turn_id": str(parent_id),
                            "user_input": str(other_mem.get("user_input", ""))[:100],
                            "response": str(other_mem.get("response", ""))[:100],
                            "timestamp": str(other_mem.get("timestamp", "")),
                        }
                        break

            # Find co-activation links
            co_links = []
            co_activation = mem.get("co_activation", [])
            if isinstance(co_activation, list):
                co_links = co_activation[:5]

            # Compute relative age
            relative_age = "unknown"
            try:
                if ts:
                    if isinstance(ts, (int, float)):
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    else:
                        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                    if age_h < 1:
                        relative_age = "< 1 hour ago"
                    elif age_h < 24:
                        relative_age = f"{int(age_h)} hours ago"
                    elif age_h < 168:
                        relative_age = f"{int(age_h/24)} days ago"
                    else:
                        relative_age = f"{int(age_h/168)} weeks ago"
            except Exception:
                pass

            entry = {
                "id": str(mem_id),
                "type": mem.get("type", "unknown"),
                "fact": str(fact)[:200],
                "timestamp": str(ts),
                "relative_age": relative_age,
                "importance": mem.get("importance_score", 0),
                "category": mem.get("category", ""),
                "entities": mem.get("entities", []),
                "oscillator_band": mem.get("oscillator_band", ""),
                "coherence": mem.get("coherence", mem.get("global_coherence", None)),
                "collections_found_in": in_collections,
                "co_activation_links": co_links,
                "parent_turn": parent_turn,
                "retrieval_count": mem.get("retrieval_count", 0),
                "is_bedrock": mem.get("is_bedrock", False),
                "current_layer": mem.get("current_layer", ""),
            }
            results.append(entry)

        # Sort by number of collections (convergence) then importance
        results.sort(key=lambda x: (-len(x["collections_found_in"]), -x["importance"]))
        results = results[:max_results]

        # Stats
        stats = {
            "total_working": len(self.memory.memory_layers.working_memory),
            "total_longterm": len(self.memory.memory_layers.long_term_memory),
            "collections": {},
        }

        if self.memory and self.memory.memory_vectors:
            stats["collections"] = self.memory.memory_vectors.get_collection_stats()

        return {
            "query": query,
            "result_count": len(results),
            "results": results,
            "stats": stats,
        }

    def trace_memory_formatted(self, query: str, max_results: int = 5) -> str:
        """
        Trace a concept through memory and return formatted text output.

        Use this as a Kay tool or for debugging in the terminal.
        """
        result = self.trace_memory(query, max_results)

        lines = [f"Memory trace for '{query}': {result['result_count']} results"]
        lines.append(f"Collections: {result['stats']['collections']}")
        lines.append("")

        for r in result["results"]:
            lines.append(f"--- [{r['type']}] {r['fact'][:120]}")
            lines.append(f"    Age: {r['relative_age']} | "
                         f"Importance: {r['importance']:.2f} | "
                         f"Band: {r['oscillator_band']} | "
                         f"Layer: {r['current_layer']}")
            lines.append(f"    Found in: {r['collections_found_in']}")
            if r['parent_turn']:
                lines.append(f"    Parent: {r['parent_turn']['user_input'][:80]}...")
            if r['co_activation_links']:
                lines.append(f"    Co-links: {len(r['co_activation_links'])}")
            if r['is_bedrock']:
                lines.append(f"    ** BEDROCK FACT **")
            lines.append("")

        return "\n".join(lines)
