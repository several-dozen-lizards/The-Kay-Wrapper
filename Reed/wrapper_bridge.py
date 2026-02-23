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

# Phase 3 engine imports - Continuous session & curation
from engines.real_time_flagging import FlaggingSystem
from engines.curation_interface import CurationInterface
from engines.chronicle_integration import add_chronicle_to_briefing
from engines.continuous_session import ContinuousSession, ConversationTurn

from integrations.llm_integration import get_llm_response
from context_filter import GlyphFilter
from glyph_decoder import GlyphDecoder

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
        
        # Phase 3: Continuous session state
        self.continuous_mode = True
        self.curation_pending = False
        self.pending_curation_prompt = None
        
        # Context filter
        self.context_filter = GlyphFilter()
        self.glyph_decoder = GlyphDecoder()
        
        # Initialize engines
        self._init_engines()
        
        print(f"[BRIDGE] {entity_name} WrapperBridge initialized")
    
    def _init_engines(self):
        """Initialize all processing engines."""
        # Momentum & meta engines (needed by others)
        self.momentum = MomentumEngine()
        self.motif = MotifEngine()
        self.meta_awareness = MetaAwarenessEngine()
        
        # Conversation monitor
        self.conversation_monitor = ConversationMonitor(config_path="config.json")
        print(f"[SPIRAL] Conversation monitor ready (embeddings: {self.conversation_monitor.get_stats()['embeddings_available']})")
        
        # Vector store
        print("[STARTUP] Initializing vector store for RAG...")
        try:
            self.vector_store = VectorStore(persist_directory="memory/vector_db")
            print(f"[STARTUP] Vector store ready: {self.vector_store.get_stats()['total_chunks']} chunks available")
        except Exception as e:
            print(f"[WARNING] Vector store initialization failed: {e}")
            self.vector_store = None
        
        # Document reader
        print("[STARTUP] Initializing document reader...")
        self.doc_reader = DocumentReader(chunk_size=25000)
        print("[STARTUP] Document reader ready")
        
        # Auto-reader
        print("[STARTUP] Initializing auto-reader...")
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
        print("[STARTUP] Auto-reader ready")
        
        # Web reader
        print("[STARTUP] Initializing web reader...")
        self.web_reader = WebReader(max_chars=15000)
        print("[STARTUP] Web reader ready")

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
        print(f"[RELATIONSHIP] Landmarks: {rel_stats['landmarks']}, Patterns: {sum([rel_stats['re_states_tracked'], rel_stats['topics_tracked'], rel_stats['rhythms_tracked']])}")
        
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
        print(f"[FOREST] Loaded {len(self.forest.trees)} document trees")
        
        # Memory deletion
        self.memory_deletion = MemoryDeletion(self.memory)
        
        # Memory engine stats
        print(f"[MEMORY] Entity graph: {len(self.memory.entity_graph.entities)} entities")
        print(f"[MEMORY] Multi-layer memory + multi-factor retrieval enabled")
        
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
        print("[CREATIVITY] Baseline always active; amplification triggers ready")
        
        # Initialize creativity state
        self.state.creativity_context = None
        self.state.creativity_active = False
        
        # Emotional pattern engine (behavioral tracking)
        data_dir = os.path.join(self.wrapper_dir, "data/emotions")
        self.emotional_patterns = EmotionalPatternEngine(data_dir=data_dir)
        self.state.emotional_patterns = self.emotional_patterns.get_current_state()
        print(f"[EMOTION PATTERNS] {self.emotional_patterns.get_stats()['emotions_tracked']} tracked emotions")
        
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
                print(f"[MEDIA] Orchestrator ready: {self.media_orchestrator.get_stats()['total_songs']} songs cached")
                
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
                            print(f"[MEDIA] Processed {len(existing)} existing files")
            except Exception as e:
                print(f"[WARNING] Media system init failed: {e}")

        # Auto-reader LLM wrapper (needs memory recall per segment)
        self._setup_auto_reader_llm()
        
        # Session summary system
        self.session_summary_storage = SessionSummary()
        self.session_summary_generator = SessionSummaryGenerator(
            llm_func=get_llm_response,
            summary_storage=self.session_summary_storage
        )
        
        summary_stats = self.session_summary_generator.get_stats()
        print(f"[SESSION SUMMARY] {summary_stats['total_summaries']} past summaries loaded")
        
        # Phase 3: Continuous session, flagging, curation
        print("[STARTUP] Initializing continuous session system...")
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
        
        print(f"[BRIDGE] {self.entity_name} ready for conversation.\n")
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
        
        return False, None

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
        # This is a "lol", "nice", "omg Chrome", "that's hilarious" type message
        return word_count <= 25 or (word_count <= 40 and '?' not in text)

    async def process_message(self, user_input, source="terminal"):
        """
        Full processing pipeline: pre-processing → LLM call → post-processing.
        
        Args:
            user_input: The user's message text
            source: "terminal" or "nexus" (for logging/routing)
        
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
                print(f"[ERROR] Fast-twitch LLM call failed: {e}")
                reply = "[Error: Could not generate response]"
            
            reply = self.body.embody_text(reply, self.state)
            
            # Light post-processing: emotion extraction + turn tracking (skip memory encoding, reflection, etc.)
            extracted_emotions = self.emotion_extractor.extract_emotions(reply)
            self.emotion_extractor.store_emotional_state(extracted_emotions, self.state.emotional_cocktail)
            
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
                print(f"[MEDIA] Context injection ready ({len(injection_text)} chars)")
        
        # Fact extraction & memory recall
        self.memory.extract_and_store_user_facts(self.state, user_input)
        self.memory.recall(self.state, user_input)
        await _update_all(self.state, [self.social, self.temporal, self.body, self.motif], user_input)

        # LLM document retrieval
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
            print(f"[ERROR] Filter system failed: {e}")
            import traceback
            traceback.print_exc()
            filtered_prompt_context = self.context_manager.build_context(self.state, user_input)
        
        # Spiral detection
        spiral_analysis = self.conversation_monitor.add_turn("user", user_input)
        if spiral_analysis:
            spiral_injection = self.conversation_monitor.get_disengagement_prompt(spiral_analysis)
            print(f"[SPIRAL] Detected! Confidence: {spiral_analysis.confidence:.2f}")
            filtered_prompt_context["spiral_context"] = spiral_injection
        
        # Creativity injection (from previous turn)
        if hasattr(self.state, 'creativity_context') and self.state.creativity_context:
            filtered_prompt_context["creativity_context"] = self.state.creativity_context
            self.state.creativity_active = True
            self.state.creativity_context = None
        else:
            self.state.creativity_active = False
        
        self.creativity_engine.update_turn(self.turn_count)
        
        # Phase 3: Inject curation prompt if pending
        if self.curation_pending and self.pending_curation_prompt:
            filtered_prompt_context["curation_context"] = self.pending_curation_prompt
            print("[CURATION] Injected curation review prompt into context")
        
        # === LLM CALL ===
        session_context = {"turn_count": self.turn_count, "session_id": self.session_id}
        
        try:
            reply = get_llm_response(
                filtered_prompt_context,
                affect=self.affect_level,
                session_context=session_context,
                use_cache=True
            )
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            reply = "[Error: Could not generate response]"
        
        reply = self.body.embody_text(reply, self.state)

        # === POST-PROCESSING ===
        
        # Emotion extraction (self-reported from response)
        extracted_emotions = self.emotion_extractor.extract_emotions(reply)
        self.emotion_extractor.store_emotional_state(extracted_emotions, self.state.emotional_cocktail)
        
        # Emotional patterns
        if extracted_emotions.get('primary_emotions'):
            self.emotional_patterns.set_current_state(
                emotions=extracted_emotions['primary_emotions'],
                intensity=extracted_emotions.get('intensity'),
                valence=extracted_emotions.get('valence'),
                arousal=extracted_emotions.get('arousal')
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
            print(f"[PERF WARNING] Turn {self.turn_count} took {turn_elapsed:.1f}s")
        
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
        print(f"[BRIDGE] {self.entity_name} shutdown complete.")
