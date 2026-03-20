# main.py
import asyncio
import os
import json
import time
import sys

# Add parent directory to path so resonant_core can be imported
_wrapper_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _wrapper_root not in sys.path:
    sys.path.insert(0, _wrapper_root)

from agent_state import AgentState
from protocol_engine import ProtocolEngine
from utils.performance import reset_metrics, get_summary
from config import VERBOSE_DEBUG  # Global debug verbosity control

# Engine imports
from engines.emotion_engine import EmotionEngine
from engines.emotion_extractor import EmotionExtractor  # NEW: Descriptive emotion extraction
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
from engines.relationship_memory import RelationshipMemory  # NEW: Relationship pattern tracking
from engines.vector_store import VectorStore  # NEW: RAG support
from engines.llm_retrieval import select_relevant_documents, load_full_documents  # NEW: LLM-based document selection
from engines.document_reader import DocumentReader  # NEW: Chunked document navigation
from engines.auto_reader import AutoReader  # NEW: Automatic document reading
from engines.web_reader import WebReader  # NEW: URL fetching and parsing
from engines.emotional_patterns import EmotionalPatternEngine  # NEW: Behavioral emotion tracking
from engines.conversation_monitor import ConversationMonitor  # NEW: Spiral detection
from engines.session_summary import SessionSummary, build_session_context_with_summary  # NEW: Session summaries
from engines.session_summary_generator import SessionSummaryGenerator  # NEW: Summary generation
from engines.creativity_engine import CreativityEngine  # NEW: Creativity triggers
from engines.macguyver_mode import MacGuyverMode  # NEW: Gap identification
from engines.scratchpad_engine import scratchpad  # NEW: Scratchpad for creativity

# Media experience system imports
from media_orchestrator import MediaOrchestrator
from media_context_builder import MediaContextBuilder
try:
    from media_watcher import MediaWatcher, WATCHDOG_AVAILABLE
except ImportError:
    WATCHDOG_AVAILABLE = False
    MediaWatcher = None
    print("[WARNING] media_watcher import failed - watchdog may not be installed")

from integrations.llm_integration import get_llm_response

from context_filter import GlyphFilter
from glyph_decoder import GlyphDecoder
from engines.memory_forest import MemoryForest  # Import from engines (has load_from_file method)

# Resonant Consciousness Architecture — oscillator heartbeat + audio bridge
try:
    from resonant_core.resonant_integration import ResonantIntegration
    RESONANCE_AVAILABLE = True
except ImportError as e:
    RESONANCE_AVAILABLE = False
    print(f"[WARNING] Resonant core not available: {e}")

# Saccade engine (perceptual continuity between turns)
from engines.saccade_engine import SaccadeEngine

# Consciousness stream (continuous inner experience between turns)
from engines.consciousness_stream import ConsciousnessStream

# Room system (spatial embodiment)
try:
    from shared.room.room_bridge import RoomBridge
    from shared.room.presets import create_the_den
    from shared.room.autonomous_spatial import AutonomousSpatialEngine
    ROOM_AVAILABLE = True
except ImportError as e:
    ROOM_AVAILABLE = False
    print(f"[WARNING] Room system not available: {e}")

context_filter = GlyphFilter()
glyph_decoder = GlyphDecoder()


async def update_all(state, engines, user_input, response=None):
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


async def main():
    proto = ProtocolEngine()
    state = AgentState()
    momentum = MomentumEngine()
    motif = MotifEngine()
    meta_awareness = MetaAwarenessEngine()

    # NEW: Initialize conversation monitor (spiral detection)
    conversation_monitor = ConversationMonitor(config_path="config.json")
    print(f"[SPIRAL] Conversation monitor ready (embeddings: {conversation_monitor.get_stats()['embeddings_available']})")

    # NEW: Initialize vector store for RAG (hybrid memory system)
    print("[STARTUP] Initializing vector store for RAG...")
    try:
        vector_store = VectorStore(persist_directory="memory/vector_db")
        print(f"[STARTUP] Vector store ready: {vector_store.get_stats()['total_chunks']} chunks available")
    except Exception as e:
        print(f"[WARNING] Vector store initialization failed: {e}")
        print("[WARNING] RAG retrieval will be disabled")
        vector_store = None

    # NEW: Initialize document reader for chunked navigation
    print("[STARTUP] Initializing document reader...")
    doc_reader = DocumentReader(chunk_size=25000)  # ~6k tokens per chunk
    print("[STARTUP] Document reader ready")

    # NEW: Initialize auto-reader for seamless document processing
    print("[STARTUP] Initializing auto-reader...")
    def auto_reader_display(role, message):
        """Display function for auto-reader (terminal output)."""
        if role == "system":
            print(f"\n{message}\n")
        else:
            print(f"{role.capitalize()}: {message}\n")
    auto_reader = AutoReader(
        get_llm_response_func=None,  # Will be set later after we define wrapper
        add_message_func=auto_reader_display,
        memory_engine=None  # Will be set after memory engine is created
    )
    print("[STARTUP] Auto-reader ready")

    # NEW: Initialize web reader for URL fetching
    print("[STARTUP] Initializing web reader...")
    web_reader = WebReader(max_chars=15000)  # ~4000 tokens max
    print("[STARTUP] Web reader ready")

    # Attempt to restore document reader state from previous session
    try:
        snapshot_path = "memory/state_snapshot.json"
        if os.path.exists(snapshot_path):
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                snapshot = json.load(f)
                if 'document_reader' in snapshot:
                    doc_reader_state = snapshot['document_reader']
                    print(f"[DOC READER] Found saved reading position: {doc_reader_state['doc_name']} section {doc_reader_state['position'] + 1}/{doc_reader_state['total_chunks']}")
                    # Note: Actual document text will be loaded when user continues reading
                    # Store state for later restoration
                    state.saved_doc_reader_state = doc_reader_state
    except Exception as e:
        print(f"[DOC READER] Could not restore state: {e}")

    # CRITICAL DESIGN: Two-part emotion system
    # 1. EmotionEngine: ULTRAMAP rule provider (NOT used for calculation anymore)
    #    - Provides memory/social/body rules to other engines
    #    - No longer calculates or prescribes emotional states
    # 2. EmotionExtractor: Self-report extraction (ACTIVE system)
    #    - Extracts emotions from Kay's natural language AFTER response
    #    - Descriptive, not prescriptive
    emotion = EmotionEngine(proto, momentum_engine=momentum)
    emotion_extractor = EmotionExtractor()
    print("[EMOTION SYSTEM] Self-report extraction enabled (descriptive, not prescriptive)")
    print("[EMOTION SYSTEM] EmotionEngine serves as ULTRAMAP rule provider only")

    # NEW: Pass emotion_engine AND vector_store to MemoryEngine
    memory = MemoryEngine(
        state.memory,
        motif_engine=motif,
        momentum_engine=momentum,
        emotion_engine=emotion,
        vector_store=vector_store  # NEW: Enable RAG retrieval
    )

    # Link memory engine to auto-reader
    auto_reader.memory = memory

    # NEW: Relationship memory - track patterns and connection texture
    relationship = RelationshipMemory()
    print(f"[RELATIONSHIP] Relationship memory initialized:")
    print(f"  - Landmarks: {relationship.get_stats()['landmarks']}")
    print(f"  - Patterns tracked: {sum([relationship.get_stats()['re_states_tracked'], relationship.get_stats()['topics_tracked'], relationship.get_stats()['rhythms_tracked']])}")

    social = SocialEngine(emotion_engine=emotion)
    body = EmbodimentEngine(emotion_engine=emotion)

    # CRITICAL FIX: Link MemoryEngine back to AgentState so filter can access memories
    state.memory = memory

    # NEW: Initialize Memory Forest (hierarchical document trees)
    print("[STARTUP] Loading memory forest...")
    forest = MemoryForest.load_from_file("memory/forest.json")
    state.forest = forest
    print(f"[FOREST] Loaded {len(forest.trees)} document trees")

    # NEW: Initialize Memory Deletion System
    from engines.memory_deletion import MemoryDeletion
    memory_deletion = MemoryDeletion(memory)
    print("[STARTUP] Memory deletion system ready")

    # NEW: MemoryEngine now includes:
    # - Entity resolution (entity_graph): Links mentions to canonical entities with attribute tracking
    # - Multi-layer memory (memory_layers): Working -> Episodic -> Semantic transitions
    # - Multi-factor retrieval: Emotional (40%) + Semantic (25%) + Importance (20%) + Recency (10%) + Entity (5%)
    # - ULTRAMAP importance scoring: Uses pressure × recursion to determine memory persistence
    # - ULTRAMAP rule integration: Queries emotion_engine for memory rules (temporal weight, priority, duration)
    print("[MEMORY] Enhanced memory architecture enabled:")
    print(f"  - Entity graph initialized ({len(memory.entity_graph.entities)} entities)")
    print(f"  - Multi-layer memory initialized")
    print(f"  - Multi-factor retrieval enabled")
    print(f"  - ULTRAMAP rule integration enabled")

    # NOTE: Memory forest already loaded at line 84-85 and stored in state.forest
    # Removed redundant load_all_trees() call (dead code)

    temporal = TemporalEngine()
    reflection = ReflectionEngine()
    summarizer = Summarizer()
    context_manager = ContextManager(memory, summarizer, momentum_engine=momentum, meta_awareness_engine=meta_awareness)

    print("[ULTRAMAP INTEGRATION] Emotion rules connected to:")
    print("  - MemoryEngine: Importance scoring, temporal weight, priority")
    print("  - SocialEngine: Social effects, action tendencies, default needs")
    print("  - EmbodimentEngine: Energy/valence descriptors (neurochemicals removed)")

    # Initialize Resonant Consciousness Architecture (oscillator heartbeat + audio ear)
    resonance = None
    if RESONANCE_AVAILABLE:
        try:
            resonance = ResonantIntegration(
                state_dir="memory/resonant",
                enable_audio=True,      # Kay's first ear
                audio_device=None,      # Default mic (change to device index if needed)
                audio_responsiveness=0.3,
                memory_layers=memory.memory_layers,  # Phase 1: memory as interoception
                interoception_interval=4.0,           # Heartbeat every 4 seconds
            )
            resonance.start()
        except Exception as e:
            print(f"[WARNING] Resonance initialization failed: {e}")
            resonance = None

    # Initialize Saccade Engine (perceptual continuity between turns)
    saccade_engine = SaccadeEngine()
    print("[STARTUP] Saccade engine initialized for perceptual continuity")

    # Initialize Room Bridge (spatial embodiment - the Den)
    room = None
    room_bridge = None
    if ROOM_AVAILABLE:
        try:
            room_state_file = os.path.join("data", "room_state.json")
            os.makedirs(os.path.dirname(room_state_file), exist_ok=True)
            room = create_the_den(state_file=room_state_file)
            # Kay starts near the couch (North — the grounding anchor)
            room.add_entity("kay", "Kay", distance=100, angle_deg=90, color="#2D1B4E")
            room_bridge = RoomBridge(room, entity_id="kay")
            print("[ROOM] Kay placed in The Den (inner ring, north — near the couch)")
        except Exception as e:
            print(f"[WARNING] Room initialization failed: {e}")
            room = None
            room_bridge = None

    # Initialize Autonomous Spatial Engine (curiosity-driven exploration)
    autonomous_spatial = None
    if ROOM_AVAILABLE and room:
        try:
            autonomous_spatial = AutonomousSpatialEngine(
                entity_id="kay",
                room_engine=room,
                persist_path="memory/autonomous_spatial_state.json"
            )
            print(f"[SPATIAL] Autonomous spatial engine initialized for Kay")
        except Exception as e:
            print(f"[WARNING] Autonomous spatial initialization failed: {e}")
            autonomous_spatial = None

    # Initialize Consciousness Stream (continuous inner experience)
    consciousness_stream = None
    try:
        from integrations.peripheral_router import get_peripheral_router
        _peripheral = get_peripheral_router()
    except Exception:
        _peripheral = None

    consciousness_stream = ConsciousnessStream(
        resonance=resonance,
        room_bridge=room_bridge,
        peripheral_router=_peripheral,
        entity_name="kay",
    )
    consciousness_stream.start()
    print("[STREAM] Kay's consciousness stream initialized")

    # NEW: Initialize creativity AMPLIFICATION system
    # Note: Baseline creativity is baked into Kay's system prompt (always active)
    # This system handles AMPLIFICATION triggers (completion, idle, gaps)
    print("[STARTUP] Initializing creativity amplification system...")
    from engines import curiosity_engine as curiosity_module  # Import curiosity module
    creativity_engine = CreativityEngine(
        scratchpad_engine=scratchpad,
        memory_engine=memory,
        entity_graph=memory.entity_graph,
        curiosity_engine=curiosity_module,
        momentum_engine=momentum
    )
    macguyver = MacGuyverMode(
        memory_engine=memory,
        scratchpad_engine=scratchpad,
        entity_graph=memory.entity_graph
    )
    print("[CREATIVITY] Baseline: Always active in system prompt")
    print("[CREATIVITY] Amplification triggers: completion, idle, gaps")
    print("[CREATIVITY] MacGuyver instinct: Always active; amplified on gap detection")

    # Initialize creativity state on agent
    state.creativity_context = None  # For amplified mode injection
    state.creativity_active = False  # True = amplified mode, False = baseline only

    # NEW: Initialize behavioral emotion tracking (for media system)
    print("[STARTUP] Initializing emotional pattern engine...")
    emotional_patterns = EmotionalPatternEngine(data_dir="data/emotions")
    state.emotional_patterns = emotional_patterns.get_current_state()
    print(f"[EMOTION PATTERNS] Loaded with {emotional_patterns.get_stats()['emotions_tracked']} tracked emotions")

    # NEW: Initialize media experience system
    print("[STARTUP] Initializing media experience system...")
    media_context_builder = MediaContextBuilder(entity_graph=memory.entity_graph)
    media_orchestrator = None
    media_watcher = None

    try:
        media_orchestrator = MediaOrchestrator(
            emotional_patterns=emotional_patterns,
            entity_graph=memory.entity_graph,
            vector_store=vector_store,
            media_storage_path="memory/media"
        )
        print(f"[MEDIA] Orchestrator ready: {media_orchestrator.get_stats()['total_songs']} songs cached")

        # Initialize media watcher (file system monitoring)
        if WATCHDOG_AVAILABLE:
            media_watcher = MediaWatcher(
                watch_path=r"F:\AlphaKayZero\inputs\media",
                media_orchestrator=media_orchestrator,
                debounce_seconds=2.0
            )
            media_watcher.start()
            print(f"[MEDIA] Watcher active: {media_watcher.get_watched_path()}")

            # Scan for any files added while Kay was offline
            existing_files = media_watcher.scan_existing_files()
            if existing_files:
                print(f"[MEDIA] Processed {len(existing_files)} existing files from watch folder")
        else:
            print("[MEDIA] File watcher disabled (watchdog not installed)")

    except Exception as e:
        print(f"[WARNING] Media system initialization failed: {e}")
        print("[WARNING] Media experience features will be disabled")
        import traceback
        traceback.print_exc()

    # Create LLM wrapper for auto-reader
    def auto_reader_get_response(prompt, agent_state):
        """
        Wrapper function for auto-reader to get LLM responses with full context.
        This builds proper context and calls get_llm_response.

        CRITICAL: This MUST recall memories for each segment to prevent
        computational drift and maintain Kay's identity.
        """
        # CRITICAL FIX: Recall memories for THIS segment (not stale memories)
        # This ensures Kay has his identity/core memories/relationship history
        memory.recall(agent_state, prompt)

        # Build context with freshly recalled memories
        reading_context = {
            "user_input": prompt,
            "recalled_memories": agent_state.last_recalled_memories if hasattr(agent_state, 'last_recalled_memories') else [],
            "emotional_state": {"cocktail": agent_state.emotional_cocktail if hasattr(agent_state, 'emotional_cocktail') else {}},
            "emotional_patterns": getattr(agent_state, 'emotional_patterns', {}),  # Behavioral patterns
            # REMOVED: "body" - Neurochemical body state deprecated
            "recent_context": [],
            "momentum_notes": getattr(agent_state, 'momentum_notes', []),
            "meta_awareness_notes": getattr(agent_state, 'meta_awareness_notes', []),
            "consolidated_preferences": getattr(agent_state, 'consolidated_preferences', {}),
            "preference_contradictions": getattr(agent_state, 'preference_contradictions', []),
            "rag_chunks": [],
            "relationship_context": relationship.build_relationship_context(),  # NEW: Relationship patterns
            "turn_count": getattr(agent_state, 'turn_count', 0),
            "recent_responses": getattr(agent_state, 'recent_responses', []),
            "session_id": session_id if 'session_id' in locals() else str(int(time.time()))
        }

        # Debug: Verify memories were recalled
        print(f"[AUTO READER] Memories in context: {len(reading_context['recalled_memories'])}")

        # Get response
        response = get_llm_response(
            reading_context,
            affect=affect_level if 'affect_level' in locals() else 3.5,
            session_context={
                "turn_count": reading_context["turn_count"],
                "session_id": reading_context["session_id"]
            }
        )

        # Apply embodiment
        return body.embody_text(response, agent_state)

    # Set LLM function on auto-reader
    auto_reader.get_response = auto_reader_get_response

    # NEW: Initialize session summary system
    print("[STARTUP] Initializing session summary system...")
    session_summary_storage = SessionSummary()
    session_summary_generator = SessionSummaryGenerator(
        llm_func=get_llm_response,
        summary_storage=session_summary_storage
    )
    session_summary_generator.start_session()

    # Show past session note if available
    past_session_context = session_summary_generator.get_startup_context()
    if past_session_context:
        print("\n" + "="*60)
        print("NOTE FROM PAST-YOU:")
        print("="*60)
        # Display truncated version to console
        last_summary = session_summary_storage.get_most_recent()
        if last_summary:
            from engines.session_summary import get_time_ago
            time_ago = get_time_ago(last_summary['timestamp'])
            print(f"({last_summary['type'].title()} session, {time_ago})")
            # Show first 500 chars of the summary
            content_preview = last_summary['content'][:500]
            if len(last_summary['content']) > 500:
                content_preview += "..."
            print(content_preview)
        print("="*60 + "\n")

    summary_stats = session_summary_generator.get_stats()
    print(f"[SESSION SUMMARY] {summary_stats['total_summaries']} past summaries loaded")
    print(f"[SESSION SUMMARY] ({summary_stats['conversation_summaries']} conversation, {summary_stats['autonomous_summaries']} autonomous)")

    print("KayZero unified emotional core ready. Type 'quit' to exit.\n")

    affect_level = 3.5  # default affect intensity
    turn_count = 0
    recent_responses = []  # Track last 3 responses for anti-repetition
    session_id = str(int(asyncio.get_event_loop().time()))  # Unique session ID
    new_document_loaded = False  # Track when a new multi-segment document is loaded for auto-reading

    while True:
        user_input = input("You: ").strip()

        # Wake consciousness stream on user input
        if consciousness_stream:
            consciousness_stream.notify_user_input()

        if user_input.lower() in ("quit", "exit"):
            # Generate session summary before exiting
            if turn_count > 0:
                print("\n[SESSION SUMMARY] Generating end-of-session note...")
                summary = session_summary_generator.generate_conversation_summary(
                    context_manager=context_manager,
                    agent_state=state
                )
                if summary:
                    print("\n" + "="*60)
                    print("KAY'S NOTE TO FUTURE-SELF:")
                    print("="*60)
                    print(summary[:800])
                    if len(summary) > 800:
                        print(f"... ({len(summary)} chars total, saved to memory/session_summaries.json)")
                    print("="*60 + "\n")
            # Stop resonant oscillator + audio bridge and save state
            if resonance:
                resonance.stop()
            break

        # Allow inline affect tuning
        if user_input.lower().startswith("/affect "):
            try:
                affect_level = float(user_input.split(" ", 1)[1])
                print(f"(Affect set to {affect_level:.1f} / 5)")
            except Exception:
                print("(Invalid affect value)")
            continue

        # DOCUMENT NAVIGATION REMOVED
        # Navigation commands are disabled during normal conversation.
        # Documents load into Kay's context automatically via LLM retrieval but remain invisible to user.
        # Document chunks are ONLY displayed during auto-reading at import time.

        # Forest commands
        if user_input.lower() == "/forest":
            print("\n" + forest.get_forest_overview())
            continue

        if user_input.lower().startswith("/tree "):
            tree_name = user_input[6:].strip()
            tree = forest.get_tree_by_title(tree_name)
            if tree:
                print("\n" + forest.navigate_tree(tree.doc_id))
            else:
                print(f"\n❌ No tree found matching: {tree_name}")
                print("\nAvailable trees:")
                for t in forest.trees.values():
                    print(f"  - {t.title}")
            continue

        if user_input.lower().startswith("/import "):
            filepath = user_input[8:].strip()
            try:
                from memory_import.kay_reader import import_document_as_kay
                doc_id = import_document_as_kay(filepath, memory, forest)
                print(f"\n✅ Document imported successfully!")
                print(f"Tree ID: {doc_id}")
                print("\nUse /forest to see all trees")
            except Exception as e:
                print(f"\n❌ Import failed: {e}")
                import traceback
                traceback.print_exc()
            continue

        # NEW: Memory deletion commands
        if user_input.lower().startswith("/forget "):
            pattern = user_input[8:].strip()
            if not pattern:
                print("\nUsage: /forget <pattern>")
                print("Example: /forget math and Arabic")
                continue

            result = memory_deletion.forget_memory(pattern, reason="User requested deletion")
            print(f"\n✅ Deleted {result['deleted']} memories matching: '{pattern}'")
            if result['protected'] > 0:
                print(f"   Protected {result['protected']} important/identity memories")
            continue

        if user_input.lower().startswith("/corrupt "):
            pattern = user_input[9:].strip()
            if not pattern:
                print("\nUsage: /corrupt <pattern>")
                print("Flags memories as corrupted (filters from retrieval)")
                continue

            count = memory_deletion.flag_as_corrupted(pattern, reason="User marked as corrupted")
            print(f"\n✅ Flagged {count} memories as corrupted: '{pattern}'")
            continue

        if user_input.lower().startswith("/prune"):
            # Parse optional parameters
            parts = user_input.split()
            days = 90
            layer = None
            if len(parts) > 1:
                try:
                    days = int(parts[1])
                except ValueError:
                    layer = parts[1]
            if len(parts) > 2:
                layer = parts[2]

            result = memory_deletion.prune_old_memories(max_age_days=days, layer_filter=layer)
            print(f"\n✅ Pruned {result['pruned']} old memories (>{days} days)")
            if result['protected'] > 0:
                print(f"   Protected {result['protected']} important memories")
            continue

        if user_input.lower() == "/deletions":
            history = memory_deletion.get_deletion_history(limit=10)
            if not history:
                print("\nNo deletion history")
                continue

            print("\n" + "="*70)
            print("RECENT DELETIONS")
            print("="*70)
            for i, record in enumerate(reversed(history), 1):
                print(f"\n{i}. Pattern: '{record['pattern']}'")
                print(f"   Reason: {record['reason']}")
                print(f"   Count: {record['count']}")
                print(f"   Time: {record['timestamp']}")
            continue

        # GitHub commands
        if user_input.lower().startswith("/github"):
            from services.github_service import handle_github_command
            command = user_input[7:].strip()  # Remove "/github" prefix
            result = handle_github_command(command)
            print(f"\n{result}")
            continue

        # === FILTERED CONTEXT SYSTEM ===
        turn_count += 1

        # Reset performance metrics for new turn
        reset_metrics()
        turn_start_time = time.time()

        # NEW: Check for URLs in user input and fetch content
        web_content_context = ""
        if web_reader.has_url(user_input):
            print("[WEB_READER] URL detected in message, fetching...")
            formatted_content, results = web_reader.process_message_urls(user_input)
            if formatted_content:
                web_content_context = formatted_content
                # Store in state for context building
                state.web_content = formatted_content
                for result in results:
                    if result.error:
                        print(f"[WEB_READER] Error: {result.error}")
                    else:
                        print(f"[WEB_READER] Fetched: '{result.title}' ({result.word_count} words)")
        else:
            state.web_content = None

        # NEW: Update media context with current conversation state
        media_context_injection = ""
        if media_orchestrator:
            # Track conversation for resonance logging
            media_context_builder.add_message("user", user_input, turn_count)

            # Update orchestrator with current context
            conv_context = media_context_builder.extract_conversation_context()
            media_orchestrator.update_conversation_context(
                topic=conv_context.get("topic"),
                entities=conv_context.get("entities"),
                re_state=conv_context.get("re_emotional_context")
            )

            # Check for pending media injection (from file watcher or explicit processing)
            should_inject, injection_text = media_context_builder.should_inject_media_context(
                media_orchestrator, user_input
            )
            if should_inject and injection_text:
                media_context_injection = injection_text
                print(f"[MEDIA] Context injection ready ({len(injection_text)} chars)")

        # CRITICAL: Extract and store facts from user input FIRST
        # This ensures Kay sees these facts when generating response
        memory.extract_and_store_user_facts(state, user_input)

        # Now recall memories (including the facts we just stored)
        memory.recall(state, user_input)
        # NOTE: Emotion engine removed from pre-response updates
        # Emotions are now extracted AFTER Kay's response (self-reported, not prescribed)
        await update_all(state, [social, temporal, body, motif], user_input)

        # NEW: LLM-based document retrieval
        print("[LLM Retrieval] Selecting relevant documents...")

        # Format emotional state for document selection
        emotional_state_str = ", ".join([
            f"{emotion} ({data['intensity']:.1f})"
            for emotion, data in sorted(
                state.emotional_cocktail.items(),
                key=lambda x: x[1]['intensity'] if isinstance(x[1], dict) else x[1],
                reverse=True
            )[:3]
        ]) if state.emotional_cocktail else "neutral"

        # LLM selects relevant documents
        selected_doc_ids = select_relevant_documents(
            query=user_input,
            emotional_state=emotional_state_str,
            max_docs=3
        )

        # Load full documents
        selected_documents = load_full_documents(selected_doc_ids)

        if selected_documents:
            print(f"[LLM Retrieval] Loaded {len(selected_documents)} documents")
            for doc in selected_documents:
                print(f"[LLM Retrieval]   - {doc.get('filename', 'unknown')}: {len(doc.get('full_text', '')):,} chars")
            # Store documents in state so glyph filter can access them
            state.selected_documents = selected_documents
        else:
            print("[LLM Retrieval] No relevant documents found")
            state.selected_documents = []

        # Use memories directly from retrieve_multi_factor()
        try:
            # Get memories directly from the last retrieval (stored in state.last_recalled_memories)
            selected_memories = getattr(state, 'last_recalled_memories', [])

            if VERBOSE_DEBUG:
                print(f"[MEMORY] Retrieved {len(selected_memories)} memories directly")
                # Count identity facts
                identity_count = sum(1 for m in selected_memories if m.get("is_identity", False) or m.get("topic") in ["identity", "appearance", "name", "core_preferences", "relationships"])
                print(f"[MEMORY] Identity facts in selected memories: {identity_count}")

            # Build filtered context structure without glyph processing
            filtered_context = {
                "selected_memories": selected_memories,
                "emotional_state": dict(state.emotional_cocktail) if hasattr(state, 'emotional_cocktail') else {},
                "recent_turns_needed": 0,  # No glyph filter decision
                "mood_glyphs": "",
                "conflict_warning": ""
            }

            if VERBOSE_DEBUG:
                print(f"[MEMORY] Memories in filtered_context: {len(filtered_context.get('selected_memories', []))}")
                print(f"[DEBUG] Emotional state: {filtered_context.get('emotional_state')}")

            # FIX #2: Integrate RECENT_TURNS directive from glyph filter
            # LLM decided how many recent conversation turns are needed for context continuity
            recent_turns_needed = filtered_context.get("recent_turns_needed", 0)

            if recent_turns_needed > 0 and context_manager.recent_turns:
                # Get last N turns from conversation history
                recent_turns = context_manager.recent_turns[-recent_turns_needed:]

                # Format as memory objects (similar to kay_ui.py implementation)
                recent_memories = []
                for i, turn in enumerate(recent_turns):
                    turn_memory = {
                        'fact': f"[Recent Turn -{len(recent_turns) - i}]",
                        'user_input': turn.get('user', ''),
                        'response': turn.get('kay', ''),
                        'type': 'recent_turn',
                        'is_recent_context': True,
                        'turn_index': turn_count - (len(recent_turns) - i)  # Track original turn
                    }
                    recent_memories.append(turn_memory)

                # FIX #4: Deduplication - don't include turns that are already in selected_memories
                selected_turn_indices = set(
                    mem.get('turn_index')
                    for mem in filtered_context.get("selected_memories", [])
                    if mem.get('turn_index') is not None
                )

                # Filter out recent turns that are already in selected memories
                deduplicated_recent = [
                    mem for mem in recent_memories
                    if mem.get('turn_index') not in selected_turn_indices
                ]

                duplicates_removed = len(recent_memories) - len(deduplicated_recent)
                if duplicates_removed > 0:
                    print(f"[DEDUP] Removed {duplicates_removed} duplicate turns already in selected memories")

                # Prepend deduplicated recent turns to selected memories (they go FIRST for immediate context)
                filtered_context["selected_memories"] = (
                    deduplicated_recent + filtered_context.get("selected_memories", [])
                )

                if VERBOSE_DEBUG:
                    print(f"[RECENT TURNS] Added {len(deduplicated_recent)} recent turns to context (requested {recent_turns_needed})")

            # NEW: Add selected documents to filtered context as rag_chunks (WITH CHUNKING)
            if selected_documents:
                print(f"[DOC CHUNKING] Processing {len(selected_documents)} documents")
                rag_chunks = []
                for doc in selected_documents:
                    doc_text = doc['full_text']
                    doc_filename = doc['filename']
                    doc_id = doc.get('doc_id', 'unknown')

                    print(f"[DOC CHUNKING] Checking {doc_filename}: {len(doc_text):,} chars")

                    # If document is large (> 30k chars), use chunked reading
                    if len(doc_text) > 30000:
                        print(f"[DOC READER] Large document detected: {doc_filename} ({len(doc_text):,} chars)")

                        # Load into doc_reader if not already loaded
                        if not doc_reader.current_doc or doc_reader.current_doc.get('id') != doc_id:
                            num_chunks = doc_reader.load_document(doc_text, doc_filename, doc_id)

                            # Check if we should restore saved position
                            saved_state = getattr(state, 'saved_doc_reader_state', None)
                            if saved_state and saved_state.get('doc_id') == doc_id:
                                doc_reader.restore_state(saved_state, doc_text)
                                # Clear saved state after restoration
                                state.saved_doc_reader_state = None
                            else:
                                # This is a newly loaded document - flag for auto-reading
                                if num_chunks > 1:
                                    new_document_loaded = True
                                    print(f"[AUTO READER] New multi-segment document loaded ({num_chunks} segments) - will auto-read after segment 1")

                        # Get current chunk
                        chunk = doc_reader.get_current_chunk()
                        if chunk:
                            print(f"[DOC READER] Chunk added to context: {len(chunk['text'])} chars (section {chunk['position']}/{chunk['total']})")

                            # Build navigation hints based on available options
                            nav_hints = []
                            if chunk['has_next']:
                                nav_hints.append("▶ Say 'continue reading' to advance to next section")
                            else:
                                nav_hints.append("✓ Document complete - you have reached the end")

                            if chunk['has_previous']:
                                nav_hints.append("◀ Say 'previous section' to review earlier content")

                            if chunk['position'] > 1:
                                nav_hints.append("🔄 Say 'restart document' to return to beginning")

                            if chunk['total'] > 3:
                                nav_hints.append("🎯 Say 'jump to section N' to skip ahead (e.g., 'jump to section 5')")

                            # Add previous comment if returning to this chunk
                            prev_comment_text = ""
                            if chunk['previous_comment']:
                                prev_comment_text = f"\n💭 Your previous comment on this section: \"{chunk['previous_comment']}\"\n"

                            # Add chunked document WITHOUT navigation instructions (for internal processing only)
                            # The user will NOT see this - only Kay sees it internally
                            chunk_text = f"""Document: {chunk['doc_name']} (Section {chunk['position']} of {chunk['total']})
{prev_comment_text}
{chunk['text']}"""
                            rag_chunks.append({
                                'source_file': doc_filename,
                                'text': chunk_text,
                                'is_chunked': True,
                                'chunk_position': chunk['position'],
                                'chunk_total': chunk['total']
                            })
                    else:
                        # Small document - add full text as before
                        rag_chunks.append({
                            'source_file': doc_filename,
                            'text': doc_text,
                            'is_chunked': False
                        })
                        print(f"[DOC CHUNKING] Small document added whole: {doc_filename} ({len(doc_text)} chars)")

                # Add or extend rag_chunks in filtered_context
                if 'rag_chunks' in filtered_context:
                    filtered_context['rag_chunks'].extend(rag_chunks)
                else:
                    filtered_context['rag_chunks'] = rag_chunks

                # Summary of what was added
                chunked_count = sum(1 for c in rag_chunks if c.get('is_chunked', False))
                whole_count = len(rag_chunks) - chunked_count
                print(f"[DOC CHUNKING] Added to context: {chunked_count} chunked, {whole_count} whole documents")

            # === CRITICAL FIX: Transform filtered_context to format expected by build_prompt_from_context ===
            # Instead of using glyph_decoder.build_context_for_kay (returns string),
            # pass a dict with "recalled_memories" key so build_prompt_from_context() can process all 496 memories

            # Build relationship context
            relationship_context = relationship.build_relationship_context()

            # Inject past session note only on first turn of session
            past_session_note_for_context = ""
            if turn_count == 1 and past_session_context:
                # Extract just the content from the past session summary
                last_summary = session_summary_storage.get_most_recent()
                if last_summary:
                    past_session_note_for_context = last_summary['content']

            # Get adaptive limits from budget manager
            from engines.context_budget import get_budget_manager
            budget_mgr = get_budget_manager()

            # Estimate context size for adaptive limits
            estimated_chars = len(str(filtered_context.get("selected_memories", []))) + len(str(filtered_context.get("rag_chunks", [])))
            has_images = len(getattr(state, 'active_images', [])) > 0
            limits = budget_mgr.get_adaptive_limits(estimated_chars, has_images=has_images)

            # Apply adaptive limits to memories
            selected_memories = filtered_context.get("selected_memories", [])
            if len(selected_memories) > limits['memory_limit']:
                from engines.context_budget import prioritize_memories
                selected_memories = prioritize_memories(selected_memories, limits['memory_limit'], turn_count)
                print(f"[BUDGET] Trimmed memories: {len(filtered_context.get('selected_memories', []))} -> {len(selected_memories)}")

            # Apply adaptive limits to RAG
            rag_chunks = filtered_context.get("rag_chunks", [])
            if len(rag_chunks) > limits['rag_limit']:
                from engines.context_budget import prioritize_rag_chunks
                rag_chunks = prioritize_rag_chunks(rag_chunks, limits['rag_limit'], user_input)
                print(f"[BUDGET] Trimmed RAG: {len(filtered_context.get('rag_chunks', []))} -> {len(rag_chunks)}")

            # Apply adaptive limits to working memory turns
            working_turns = context_manager.recent_turns[-limits['working_turns']:] if hasattr(context_manager, 'recent_turns') else []

            # Build context metrics for monitoring
            context_metrics = {
                "tier": limits['tier'],
                "estimated_tokens": estimated_chars // 4,
                "memory_count": len(selected_memories),
                "rag_count": len(rag_chunks),
                "turn_count": len(working_turns),
                "image_count": 1 if has_images else 0
            }

            # Merge primary retrieval with any secondary retrieval from previous turn
            secondary_buffer = getattr(state, 'secondary_retrieval_buffer', [])
            if secondary_buffer:
                print(f"[SECONDARY RETRIEVAL] Injecting {len(secondary_buffer)} memories from previous turn's topic extraction")
                selected_memories = secondary_buffer + selected_memories
                state.secondary_retrieval_buffer = []

            filtered_prompt_context = {
                "recalled_memories": selected_memories,  # Now with adaptive limits + secondary buffer
                "emotional_state": {"cocktail": filtered_context.get("emotional_state", {})},
                "emotional_patterns": getattr(state, 'emotional_patterns', {}),
                "user_input": user_input,
                "recent_context": working_turns,  # Now with adaptive limits
                "momentum_notes": getattr(state, 'momentum_notes', []),
                "meta_awareness_notes": getattr(state, 'meta_awareness_notes', []),
                "consolidated_preferences": getattr(state, 'consolidated_preferences', {}),
                "preference_contradictions": getattr(state, 'preference_contradictions', []),
                "rag_chunks": rag_chunks,  # Now with adaptive limits
                "relationship_context": relationship_context,
                "web_content": web_content_context,
                "media_context": media_context_injection,
                "past_session_note": past_session_note_for_context,
                # Session metadata for anti-repetition
                "turn_count": turn_count,
                "recent_responses": getattr(state, 'recent_responses', []),
                "session_id": session_id,
                # NEW: Context metrics for monitoring
                "context_metrics": context_metrics,
                # NEW: Image context
                "image_context": getattr(context_manager, 'get_image_context_block', lambda: "")(),
                "active_images": context_manager.get_active_images() if hasattr(context_manager, 'get_active_images') else []
            }

            if VERBOSE_DEBUG:
                print(f"[DEBUG] Context transformation succeeded")
                print(f"[DEBUG] Memories in transformed context: {len(filtered_prompt_context.get('recalled_memories', []))}")

                if filtered_context.get("contradictions"):
                    print(f"[DEBUG] WARNING: {len(filtered_context['contradictions'])} contradictions detected")

                print(f"[DEBUG] Identity state: {filtered_context.get('identity_state')}")

        except Exception as e:
            # If filtering fails, fall back to unfiltered context
            print(f"[ERROR] FAIL Filter system failed: {e}")
            import traceback
            print("[ERROR] Full traceback:")
            traceback.print_exc()
            print("[ERROR] Falling back to unfiltered context...")

            # Build fallback context using original context_manager
            fallback_context = context_manager.build_context(state, user_input)
            filtered_prompt_context = fallback_context  # Use dict for fallback
            print("[DEBUG] Fallback context type:", type(filtered_prompt_context))

        # Build session metadata (for anti-repetition)
        session_context = {
            "turn_count": turn_count,
            "session_id": session_id
        }

        if VERBOSE_DEBUG:
            print(f"[DEBUG] Session context: {session_context}")

        # NEW: Spiral detection for LLM conversations
        spiral_injection = ""
        spiral_analysis = conversation_monitor.add_turn("user", user_input)
        if spiral_analysis:
            # Spiral detected in LLM conversation
            spiral_injection = conversation_monitor.get_disengagement_prompt(spiral_analysis)
            print(f"[SPIRAL] Detected! Confidence: {spiral_analysis.confidence:.2f}")
            print(f"[SPIRAL] Partner: {conversation_monitor.current_partner}")
            print(f"[SPIRAL] Recommendation: {spiral_analysis.recommendation}")

            # Add spiral injection to context
            filtered_prompt_context["spiral_context"] = spiral_injection

        # NEW: Inject AMPLIFIED creativity context if prepared from previous turn
        # Note: Baseline creativity always active in system prompt; this amplifies it
        if hasattr(state, 'creativity_context') and state.creativity_context:
            print("[CREATIVITY] Injecting AMPLIFIED creativity context")
            filtered_prompt_context["creativity_context"] = state.creativity_context
            state.creativity_active = True  # Amplified mode active
            # Clear after injection (one-shot)
            state.creativity_context = None
        else:
            state.creativity_active = False  # Back to baseline only

        # Update creativity engine turn counter
        creativity_engine.update_turn(turn_count)

        # --- Saccade block (perceptual continuity) ---
        try:
            saccade_block = saccade_engine.process_turn(state, turn_count)
            if saccade_block:
                filtered_prompt_context["saccade_block"] = saccade_block
                print(f"[SACCADE] Turn {turn_count}: block generated ({len(saccade_block)} chars)")
        except Exception as e:
            print(f"[SACCADE] Error (non-fatal): {e}")

        # --- Consciousness stream (between-message experience) ---
        if consciousness_stream:
            try:
                stream_ctx = consciousness_stream.get_injection_context()
                if stream_ctx:
                    filtered_prompt_context["stream_context"] = stream_ctx
                    print(f"[STREAM] Injecting {len(stream_ctx)} chars of between-message experience")
            except Exception as e:
                print(f"[STREAM] Injection error (non-fatal): {e}")

        # --- Room bridge (spatial embodiment) ---
        if room_bridge:
            existing_extra = filtered_prompt_context.get("extra_system_context", "")
            room_ctx = room_bridge.inject_room_context("")
            if room_ctx:
                filtered_prompt_context["extra_system_context"] = (existing_extra + "\n" + room_ctx).strip()

        # --- Inject resonant oscillator context (audio + heartbeat state) ---
        if resonance:
            resonance.inject_into_context(filtered_prompt_context)
            rc = filtered_prompt_context.get("resonant_context", "")
            if rc:
                print(f"[RESONANCE INJECT] Context: {rc}")
            else:
                print(f"[RESONANCE INJECT] WARNING: resonant_context is empty!")

        # --- Autonomous spatial behavior (oscillator-driven exploration) ---
        if autonomous_spatial and resonance:
            try:
                osc_state = resonance.get_oscillator_state()
                # Update spatial preferences from oscillator
                spatial_action = autonomous_spatial.update_from_oscillator(osc_state)
                if spatial_action and room:
                    room.apply_actions("kay", [spatial_action])
                    print(f"[SPATIAL] Kay moves to {spatial_action['target']} ({spatial_action['reason']})")
                    autonomous_spatial.mark_examined(
                        spatial_action['target'],
                        oscillator_state=osc_state
                    )
                # Periodic tick for curiosity-driven movement
                tick_action = autonomous_spatial.tick(oscillator_state=osc_state)
                if tick_action and room and not spatial_action:  # Don't double-move
                    room.apply_actions("kay", [tick_action])
                    print(f"[SPATIAL] Kay explores {tick_action['target']} (curiosity)")
                    autonomous_spatial.mark_examined(
                        tick_action['target'],
                        oscillator_state=osc_state
                    )
                # Add spatial interest annotation to context
                spatial_annotation = autonomous_spatial.get_annotation()
                if spatial_annotation:
                    existing_extra = filtered_prompt_context.get("extra_system_context", "")
                    filtered_prompt_context["extra_system_context"] = (existing_extra + "\n" + spatial_annotation).strip()
            except Exception as e:
                print(f"[SPATIAL] Error (non-fatal): {e}")

        # --- Generate response from filtered context ---
        try:
            reply = get_llm_response(
                filtered_prompt_context,
                affect=affect_level,
                session_context=session_context,
                use_cache=True  # Fix echo issue - ensures anti-echo rules are included
            )
            if VERBOSE_DEBUG:
                print(f"[DEBUG] LLM response received, length: {len(reply)}")
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            if VERBOSE_DEBUG:
                import traceback
                traceback.print_exc()
            reply = "[Error: Could not generate response]"
        reply = body.embody_text(reply, state)

        # --- Room action processing (spatial embodiment) ---
        if room_bridge and reply:
            try:
                reply, room_results = room_bridge.process_response(reply)
                if room_results:
                    print(f"[ROOM] Actions: {', '.join(room_results)}")
            except Exception as e:
                print(f"[ROOM] Action processing error (non-fatal): {e}")

        print(f"Kay: {reply}\n")

        # NEW: Extract emotions from Kay's self-reported response (descriptive, not prescriptive)
        extracted_emotions = emotion_extractor.extract_emotions(reply)
        emotion_extractor.store_emotional_state(extracted_emotions, state.emotional_cocktail)

        # ================================================================
        # SECONDARY RETRIEVAL: Topic-based memory re-check
        # ================================================================
        # Kay's response may reference topics not in Re's input.
        # Extract key topics from Kay's response and check if there are
        # relevant memories that weren't retrieved on the first pass.
        #
        # Example: Re says "How you feeling?" -> retrieval finds nothing about
        # local models. Kay responds about spatial offloading -> secondary
        # retrieval finds the episodic memory where Kay originally suggested it.
        # These memories are stored for the NEXT turn's context.
        # ================================================================
        try:
            # Extract topic keywords from Kay's response (simple approach)
            # Skip if response is very short (acknowledgments, etc.)
            if len(reply) > 100:
                import re as re_module

                # Get significant words from Kay's response (4+ chars, not common)
                common_words = {
                    'that', 'this', 'with', 'from', 'have', 'been', 'were', 'they',
                    'their', 'about', 'would', 'could', 'should', 'which', 'there',
                    'what', 'when', 'where', 'some', 'than', 'them', 'then', 'just',
                    'like', 'more', 'also', 'into', 'over', 'such', 'take', 'only',
                    'come', 'each', 'make', 'very', 'after', 'know', 'most', 'back',
                    'much', 'before', 'right', 'think', 'still', 'being', 'thing',
                    'doing', 'going', 'really', 'actually', 'yeah', 'feel', 'feeling',
                    'something', 'because', 'though', 'pretty', 'kind'
                }

                reply_words = set(
                    w.lower() for w in re_module.findall(r'\b[a-zA-Z]{4,}\b', reply)
                    if w.lower() not in common_words
                )
                input_words = set(
                    w.lower() for w in re_module.findall(r'\b[a-zA-Z]{4,}\b', user_input)
                    if w.lower() not in common_words
                )

                # New topics = words Kay used that Re didn't
                new_topics = reply_words - input_words

                if new_topics and len(new_topics) >= 2:
                    # Build a topic query from Kay's novel terms
                    # Sort by length (longer words = more specific)
                    topic_terms = sorted(new_topics, key=len, reverse=True)[:8]
                    topic_query = " ".join(topic_terms)

                    # Run secondary retrieval using existing multi-factor method
                    secondary_memories = memory.retrieve_multi_factor(
                        state,
                        topic_query,
                        num_memories=10
                    )

                    if secondary_memories:
                        # Filter to only memories NOT already in current context
                        existing_facts = set()
                        for m in (getattr(state, 'last_recalled_memories', []) or []):
                            fact_text = m.get('fact', m.get('user_input', ''))
                            if fact_text:
                                existing_facts.add(fact_text[:100])

                        novel_memories = [
                            m for m in secondary_memories
                            if m.get('fact', m.get('user_input', ''))[:100] not in existing_facts
                        ]

                        if novel_memories:
                            # Store for next turn's context injection
                            state.secondary_retrieval_buffer = novel_memories[:5]

                            print(f"[SECONDARY RETRIEVAL] Found {len(novel_memories)} new memories from Kay's response topics")
                            print(f"[SECONDARY RETRIEVAL] Topic query: '{topic_query[:80]}'")
                            for m in novel_memories[:3]:
                                print(f"  - {m.get('fact', m.get('user_input', ''))[:80]}")
                        else:
                            print(f"[SECONDARY RETRIEVAL] No novel memories found (all already in context)")
                    else:
                        print(f"[SECONDARY RETRIEVAL] No memories matched topic query")

        except Exception as e:
            print(f"[SECONDARY RETRIEVAL] Error: {e}")

        # NEW: Update emotional patterns and media context tracking
        if extracted_emotions.get('primary_emotions'):
            emotional_patterns.set_current_state(
                emotions=extracted_emotions['primary_emotions'],
                intensity=extracted_emotions.get('intensity'),
                valence=extracted_emotions.get('valence'),
                arousal=extracted_emotions.get('arousal'),
                # NEW: Pass per-emotion intensities for saccade alignment
                emotion_intensities=extracted_emotions.get('emotion_intensities')
            )
            state.emotional_patterns = emotional_patterns.get_current_state()

        # Feed emotions back to resonant oscillator (closes the feedback loop)
        if resonance and extracted_emotions:
            resonance.feed_response_emotions(extracted_emotions)
            resonance.update_agent_state(state)

        # Track Kay's response in media context builder
        if media_orchestrator:
            media_context_builder.add_message("kay", reply, turn_count)

        # Track Kay's response in conversation monitor (for spiral detection)
        conversation_monitor.add_turn("kay", reply)

        # === KAY-DRIVEN DOCUMENT NAVIGATION ===
        # Parse Kay's response for navigation intent and automatically advance/navigate
        if doc_reader.current_doc:
            response_lower = reply.lower()

            # Extract and store Kay's comment about current chunk (first substantial sentence)
            if len(reply) > 100 and doc_reader.chunks:
                # Extract first 1-2 sentences as comment (max 300 chars)
                import re
                sentences = re.split(r'[.!?]\s+', reply)
                if sentences:
                    # Take first sentence that's substantial (>20 chars)
                    comment = None
                    for sent in sentences[:3]:  # Check first 3 sentences
                        if len(sent.strip()) > 20:
                            comment = sent.strip()[:300]
                            break

                    if comment:
                        doc_reader.add_comment(doc_reader.current_position, comment)

            # Check for navigation commands in Kay's response
            navigation_triggered = False

            if "continue reading" in response_lower or "next section" in response_lower or "let's move on" in response_lower:
                if doc_reader.advance():
                    print(f"[KAY NAV] Kay requested advance -> section {doc_reader.current_position + 1}/{doc_reader.total_chunks}")
                    navigation_triggered = True
                else:
                    print(f"[KAY NAV] Kay requested advance but already at end of document")

            elif "previous section" in response_lower or "go back" in response_lower or "let me go back" in response_lower:
                if doc_reader.previous():
                    print(f"[KAY NAV] Kay requested previous -> section {doc_reader.current_position + 1}/{doc_reader.total_chunks}")
                    navigation_triggered = True
                else:
                    print(f"[KAY NAV] Kay requested previous but already at beginning")

            elif "restart document" in response_lower or "start over" in response_lower or "back to the beginning" in response_lower:
                doc_reader.jump_to(0)
                print(f"[KAY NAV] Kay requested restart -> section 1/{doc_reader.total_chunks}")
                navigation_triggered = True

            elif "jump to section" in response_lower:
                match = re.search(r'jump to section (\d+)', response_lower)
                if match:
                    target = int(match.group(1)) - 1  # Convert to 0-indexed
                    if doc_reader.jump_to(target):
                        print(f"[KAY NAV] Kay requested jump -> section {target + 1}/{doc_reader.total_chunks}")
                        navigation_triggered = True

            # If navigation occurred, save updated position to state
            if navigation_triggered:
                state.saved_doc_reader_state = doc_reader.get_state_for_persistence()

        # === AUTO-READING WITH AutoReader ===
        # After Kay responds to segment 1, automatically process segments 2-N using AutoReader
        if new_document_loaded and doc_reader.current_doc and doc_reader.total_chunks > 1:
            print(f"\n[AUTO READER] Starting automatic reading with AutoReader: segments 2-{doc_reader.total_chunks}")
            new_document_loaded = False  # Reset flag

            # Use AutoReader to process remaining segments (starting from segment 2)
            try:
                result = auto_reader.read_document_sync(
                    doc_reader=doc_reader,
                    doc_name=doc_reader.current_doc['name'],
                    agent_state=state,
                    start_segment=2  # Start from segment 2 (Kay already read segment 1)
                )

                print(f"\n[AUTO READER] Completed! Read {result['segments_read']} additional segments")

                # Track responses for anti-repetition
                for response_data in result['responses']:
                    recent_responses.append(response_data['response'])
                    if len(recent_responses) > 3:
                        recent_responses.pop(0)

                # Save final position
                state.saved_doc_reader_state = doc_reader.get_state_for_persistence()

            except Exception as e:
                print(f"[AUTO READER] Error during auto-reading: {e}")
                import traceback
                traceback.print_exc()

            print()  # Blank line for readability
        else:
            # Track response for anti-repetition (segment 1 only, or non-auto-read turns)
            recent_responses.append(reply)
            if len(recent_responses) > 3:
                recent_responses.pop(0)

        # --- Post-turn updates ---
        social.update(state, user_input, reply)
        reflection.reflect(state, user_input, reply)
        memory.encode(state, user_input, reply, list(state.emotional_cocktail.keys()))
        # REMOVED: emotion.update(state, user_input) - Prescriptive emotion calculation removed
        # Emotions are now extracted from Kay's natural language (line 544-545)
        context_manager.update_turns(user_input, reply)

        # Track turn for session summary (captures topics and emotional journey)
        session_summary_generator.track_turn(
            user_input=user_input,
            kay_response=reply,
            emotional_state=state.emotional_cocktail
        )

        # Update meta-awareness (self-monitoring)
        meta_awareness.update(state, reply, memory_engine=memory)

        # Update momentum AFTER all other systems (needs current state)
        momentum.update(state, user_input, reply)

        # NEW: Creativity AMPLIFICATION triggers
        # Note: Baseline creativity is always active (in system prompt).
        # These triggers AMPLIFY that baseline by surfacing specific elements.
        creativity_triggered = False
        creativity_mix = None

        # Check for completion signal in Kay's response -> AMPLIFY with three-layer mix
        if creativity_engine.detect_completion_signal(user_input, reply):
            print("[CREATIVITY] Completion signal -> AMPLIFYING baseline with three-layer mix")
            creativity_mix = creativity_engine.create_three_layer_mix(
                state, user_input,
                recent_turns=context_manager.recent_turns[-5:] if hasattr(context_manager, 'recent_turns') else []
            )
            creativity_engine.log_trigger("completion", creativity_mix)
            creativity_triggered = True

        # Check for idle state (minimal user engagement) -> AMPLIFY with random elements
        elif creativity_engine.detect_idle_state(user_input):
            print("[CREATIVITY] Idle state -> AMPLIFYING baseline with random elements")
            creativity_mix = creativity_engine.create_three_layer_mix(
                state, user_input,
                recent_turns=context_manager.recent_turns[-5:] if hasattr(context_manager, 'recent_turns') else []
            )
            creativity_engine.log_trigger("idle", creativity_mix)
            creativity_triggered = True

        # Check for gap identification (MacGuyver mode)
        gap = macguyver.detect_gap(user_input, reply)
        if gap:
            print(f"[MACGUYVER] Gap detected: {gap.get('missing_resource', 'unknown')}")
            resources = macguyver.scan_available_resources()
            proposals = macguyver.propose_unconventional_solutions(gap, resources)

            if proposals and proposals[0].get("strategy") != "surface_gap":
                # We have potential solutions
                macguyver_context = macguyver.format_macguyver_context(gap, proposals)
                # Combine with any existing creativity mix
                if creativity_mix:
                    state.creativity_context = creativity_engine.format_creativity_context(creativity_mix)
                    state.creativity_context += "\n\n" + macguyver_context
                else:
                    state.creativity_context = macguyver_context
                creativity_engine.log_trigger("gap", {"gap": gap, "proposals": proposals})
                creativity_triggered = True
            else:
                # No solutions found - surface to user and flag in scratchpad
                result = macguyver.handle_no_solution(gap)
                print(f"[MACGUYVER] No solution found - flagged in scratchpad (ID: {result.get('scratchpad_id')})")

        # Prepare creativity context for next turn if triggered
        if creativity_triggered and creativity_mix and not hasattr(state, 'creativity_context') or not state.creativity_context:
            state.creativity_context = creativity_engine.format_creativity_context(creativity_mix)
            print(f"[CREATIVITY] Context prepared for next turn ({len(state.creativity_context)} chars)")

        # CRITICAL: Increment memory ages for protected import pipeline
        # This must be called at END of each turn to track import age
        memory.increment_memory_ages()

        # Print memory layer operations summary for this turn
        memory.memory_layers.print_turn_summary()

        # Tick forest tier decay (cool hot/warm branches if unused)
        forest.tick_tier_decay(hot_minutes=10, warm_hours=24)
        forest.enforce_hot_limit(max_hot_branches=4)

        # --- Collect performance metrics ---
        turn_elapsed = time.time() - turn_start_time
        perf_summary = get_summary()
        perf_summary['metrics']['total_turn'] = turn_elapsed

        # Check total turn target (only warn if >2x over target = 4 seconds)
        if turn_elapsed > 4.0:
            perf_summary['warnings'].append(f"total_turn significantly exceeded target by {(turn_elapsed - 2.0)*1000:.0f}ms")
            perf_summary['within_targets'] = False

        # Store in agent state
        state.performance_metrics = {
            'last_turn': perf_summary['metrics'],
            'warnings': perf_summary['warnings'],
            'within_targets': perf_summary['within_targets']
        }

        # Log summary only if significantly over target or in verbose mode
        if VERBOSE_DEBUG and not perf_summary['within_targets']:
            print(f"[PERF] Turn {turn_count}: {turn_elapsed*1000:.0f}ms total - {len(perf_summary['warnings'])} warnings")
        elif turn_elapsed > 10.0:
            # Always warn if extremely slow (>10 seconds)
            print(f"[PERF WARNING] Turn {turn_count} took {turn_elapsed:.1f}s (significantly over target)")

        # --- Autosave agent snapshot ---
        try:
            os.makedirs("memory", exist_ok=True)

            # Prepare snapshot data
            snapshot_data = {
                "emotions": state.emotional_cocktail,
                "body": state.body,
                "social_needs": state.social,
                "recent_memories": state.last_recalled_memories or [],
                "top_motifs": state.meta.get("motifs", [])[:10],
                "momentum": state.momentum,
                "momentum_breakdown": state.momentum_breakdown,
                "meta_awareness": state.meta_awareness,
                "entity_contradictions": getattr(state, 'entity_contradictions', []),
                "memory_layer_stats": memory.memory_layers.get_layer_stats(),
                "top_entities": [
                    {
                        "name": e.canonical_name,
                        "type": e.entity_type,
                        "importance": e.importance_score,
                        "access_count": e.access_count
                    }
                    for e in memory.entity_graph.get_entities_by_importance(top_n=10)
                ],
            }

            # Add document reader state if document is loaded
            doc_reader_state = doc_reader.get_state_for_persistence()
            if doc_reader_state:
                snapshot_data["document_reader"] = doc_reader_state
                print(f"[DOC READER] Saved reading position: {doc_reader_state['doc_name']} section {doc_reader_state['position'] + 1}/{doc_reader_state['total_chunks']}")

            with open("memory/state_snapshot.json", "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=2)

        except Exception as e:
            print(f"(Warning: could not save snapshot: {e})")

        # Save forest to file
        try:
            forest.save_to_file("memory/forest.json")
        except Exception as e:
            print(f"(Warning: could not save forest: {e})")


if __name__ == "__main__":
    asyncio.run(main())
