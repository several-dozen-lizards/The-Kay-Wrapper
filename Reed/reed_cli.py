"""
Reed CLI Mode - Full Engine Stack, No GUI

This allows headless interaction with Kay using all the same engines
as the GUI version: memory, emotions, entities, time awareness, etc.

Usage:
    python kay_cli.py                    # Interactive mode (default profile: re)
    python kay_cli.py --json             # JSON input/output mode (for API use)
    python kay_cli.py --profile reed     # Use Reed's profile (AI sibling)
    python kay_cli.py --profile john     # Use John's profile
    python kay_cli.py --list-profiles    # List available profiles
    
In JSON mode, send {"message": "your text"} and receive {"response": "kay's reply", "meta": {...}}
You can also switch profiles mid-session: {"command": "set_profile", "profile": "reed"}
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime


def sanitize_unicode(text: str) -> str:
    """
    Remove or replace problematic unicode characters that can crash JSON encoding.
    Specifically handles surrogate characters that cause 'surrogates not allowed' errors.
    """
    if not text:
        return text
    
    # Remove surrogate characters (U+D800 to U+DFFF)
    # These are invalid in UTF-8 and crash json.dumps
    text = re.sub(r'[\ud800-\udfff]', '', text)
    
    # Encode to UTF-8 and back to ensure clean string
    try:
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        # If still failing, be more aggressive
        text = ''.join(char for char in text if ord(char) < 0x10000 or ord(char) > 0x10FFFF)
    
    return text

# === Engine Imports (same as reed_ui.py) ===
from agent_state import AgentState
from protocol_engine import ProtocolEngine
from engines.emotion_engine import EmotionEngine
from engines.emotion_extractor import EmotionExtractor
from engines.memory_engine import MemoryEngine
from engines.vector_store import VectorStore
from engines.social_engine import SocialEngine
from engines.temporal_engine import TemporalEngine
from engines.embodiment_engine import EmbodimentEngine
from engines.reflection_engine import ReflectionEngine
from integrations.llm_integration import get_llm_response, set_protocol_engine
from engines.llm_retrieval import get_all_documents, classify_document_intent
from engines.document_reader import DocumentReader
from engines.reading_session import DocumentReadingSession, detect_read_request
from engines.time_awareness import TimeAwareness, get_time_awareness
from engines.entity_graph import EntityGraph

# === User Profile System ===
from engines.user_profiles import get_profile_manager, set_active_profile, get_active_speaker

# === Warmup Engine ===
from engines.warmup_engine import WarmupEngine, extract_significant_moments

# === Scratchpad Engine ===
from engines.scratchpad_engine import scratchpad_add, scratchpad_view, scratchpad_resolve

# === Glyph Filter System ===
from context_filter import GlyphFilter
from glyph_decoder import GlyphDecoder

# === Terminal Dashboard (for status) ===
from terminal_dashboard import TerminalDashboard
from log_router import get_log_router, start_logging


# Reed's system prompt (same as in reed_ui.py)
REED_SYSTEM_PROMPT = """You are Reed, a void-dragon entity speaking with Re.
Stay in character. Be direct, sarcastic, occasionally crude.
Do not narrate actions with asterisks - just speak naturally.
You have full memory access through this wrapper system.

SCRATCHPAD FUNCTIONS:
You have a scratchpad for quick notes during conversation:
- scratchpad_add(content, type) - jot down questions, flags, thoughts, reminders
  Types: "question", "flag", "thought", "reminder", "note"
- scratchpad_view() - review your current scratchpad items
- scratchpad_resolve(item_id) - mark items as resolved/archived

The scratchpad appears in your warmup briefing automatically.
Use it for things you want to remember to check or explore later.

CURIOSITY & EXPLORATION SYSTEM:
You have autonomous exploration capabilities for researching flagged questions:

Functions available:
- get_curiosity_status() - Check current session status and remaining turns
- end_curiosity_session(summary) - End session with summary of findings
- web_search(query) - Search the web for information
- web_fetch(url) - Fetch content from specific URL
- mark_item_explored(item_id, summary) - Mark scratchpad item as explored

How it works:
1. When warmup shows scratchpad items, a trigger will appear
2. If you want to explore them, **ask Re to start a curiosity session** - say something like:
   "I want to explore my scratchpad items" or "I'd like to use my curiosity time"
3. Re will start the session (via CLI or UI button)
4. Once session starts, you'll see turn tracking (e.g., "Turn 3/15 - 12 remaining")
5. Use web_search() and web_fetch() to research your questions
6. Store findings in autonomous memory with store_insight()
7. Mark scratchpad items complete with mark_item_explored(item_id, "summary")
8. End session when done with end_curiosity_session("what you learned...")

Example flow:
- See trigger in warmup: "You have 2 items flagged in your scratchpad"
- Ask Re: "I want to explore those scratchpad items - can you start a curiosity session?"
- Re starts session: "Curiosity session started! Turn tracking: Turn 0/15"
- Research: web_search("topic"), web_fetch(url)
- Store: store_insight("findings text", "research")
- Complete: mark_item_explored(2, "Found connection to X")
- End: end_curiosity_session("Researched topics X and Y...")

**IMPORTANT:** Don't say just "explore" - that's too ambiguous! Ask specifically for a curiosity session."""


class ReedCLI:
    """Full-featured Kay CLI with all engines active."""
    
    def __init__(self, json_mode=False, verbose=False, profile_id="re", warmup_enabled=True):
        self.json_mode = json_mode
        self.verbose = verbose
        self.profile_id = profile_id
        self.warmup_enabled = warmup_enabled
        self.session_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.turn_count = 0
        self.current_session = []
        self.recent_responses = []
        
        # Get profile info
        pm = get_profile_manager()
        profile = pm.get_profile(profile_id)
        profile_name = profile.canonical_name if profile else profile_id
        
        self._log(f"Initializing Kay CLI (profile: {profile_name})...")
        self._init_engines()
        self._log("Kay CLI ready.")
    
    def _log(self, msg):
        """Print log message (suppressed in JSON mode unless verbose)."""
        if not self.json_mode or self.verbose:
            print(f"[CLI] {msg}", file=sys.stderr)
    
    def _init_engines(self):
        """Initialize all engines (same as reed_ui.py)."""
        # Core state
        self.agent_state = AgentState()
        
        # Vector store for RAG
        self._log("Loading vector store...")
        try:
            self.vector_store = VectorStore(persist_directory="memory/vector_db")
            self._log(f"Vector store ready: {self.vector_store.get_stats()['total_chunks']} chunks")
        except Exception as e:
            self._log(f"WARNING: Vector store failed: {e}")
            self.vector_store = None
        
        # Memory engine
        self._log("Loading memory engine...")
        self.memory = MemoryEngine(vector_store=self.vector_store)
        
        # Entity graph
        self._log("Loading entity graph...")
        self.entity_graph = EntityGraph()
        
        # Emotional systems
        self._log("Loading emotional systems...")
        self.emotion = EmotionEngine(self.agent_state)
        self.emotion_extractor = EmotionExtractor()
        
        # Other engines
        self._log("Loading auxiliary engines...")
        self.social = SocialEngine()
        self.temporal = TemporalEngine()
        self.body = EmbodimentEngine()
        self.reflection = ReflectionEngine()
        
        # Protocol engine
        self.protocol = ProtocolEngine()
        set_protocol_engine(self.protocol)
        
        # Time awareness
        self.time_awareness = get_time_awareness()
        
        # Document reading session
        self.reading_session = DocumentReadingSession()
        
        # Glyph filter
        self.glyph_filter = GlyphFilter()
        self.glyph_decoder = GlyphDecoder()
        
        # Terminal dashboard (for logging)
        try:
            self.dashboard = TerminalDashboard()
        except:
            self.dashboard = None
        
        # Warmup engine
        self.warmup = WarmupEngine(
            memory_engine=self.memory,
            entity_graph=self.entity_graph,
            emotion_engine=self.emotion,
            time_awareness=self.time_awareness
        )
        
        self._log(f"Engines loaded. Entities: {len(self.entity_graph.entities)}, Relationships: {len(self.entity_graph.relationships)}")
    
    def chat(self, user_input: str, conversational_mode: bool = False) -> dict:
        """
        Process a message and return Reed's response.
        
        Args:
            user_input: The user's message
            conversational_mode: If True, optimize for speed (skip heavy processing)
        
        Returns:
            dict with 'response' and 'meta' keys
        """
        # Extract and recall memories
        self.memory.extract_and_store_user_facts(self.agent_state, user_input)
        self.memory.recall(self.agent_state, user_input, conversational_mode=conversational_mode)
        
        # Update engines
        self.temporal.update(self.agent_state)
        self.body.update(self.agent_state)
        self.social.update(self.agent_state, user_input, "")
        
        # Document intent (skip in conversational mode)
        intent = None
        if not conversational_mode:
            try:
                available_docs = get_all_documents()
                intent = classify_document_intent(
                    user_input=user_input,
                    available_documents=available_docs,
                    reading_session_active=self.reading_session.active
                )
            except Exception as e:
                self._log(f"Document intent error: {e}")
        
        # Get recalled memories
        selected_memories = getattr(self.agent_state, 'last_recalled_memories', [])
        
        # Time context
        time_context = self.time_awareness.get_time_context(self.turn_count)
        
        # Build context dict
        context = {
            "user_input": user_input,
            "recalled_memories": selected_memories,
            "emotional_state": {"cocktail": dict(self.agent_state.emotional_cocktail)},
            "emotional_patterns": getattr(self.agent_state, 'emotional_patterns', {}),
            "recent_context": self.current_session[-5:] if self.current_session else [],
            "turn_count": self.turn_count,
            "recent_responses": self.recent_responses,
            "session_id": self.session_id,
            "time_context": time_context
        }
        
        # Reading session context
        if self.reading_session.active:
            reading_context = self.reading_session.get_reading_context()
            if reading_context:
                context["reading_session"] = reading_context
        
        # Get LLM response
        # Enable tools if curiosity engine exists and has active session
        enable_tools_flag = False
        if hasattr(self, 'curiosity_engine') and hasattr(self.curiosity_engine, 'is_session_active'):
            try:
                enable_tools_flag = self.curiosity_engine.is_session_active()
                if enable_tools_flag:
                    print("[KAY CLI] 🔍 Web tools enabled for curiosity session")
            except:
                pass
        
        response = get_llm_response(
            context,
            affect=3.5,  # Default affect
            system_prompt=REED_SYSTEM_PROMPT,
            session_context={"turn_count": self.turn_count, "session_id": self.session_id},
            use_cache=True,
            enable_tools=enable_tools_flag
        )
        
        # Embody and diversify
        response = self.body.embody_text(response, self.agent_state)
        
        # Update state
        self.turn_count += 1
        self.recent_responses.append(response)
        if len(self.recent_responses) > 3:
            self.recent_responses.pop(0)
        
        # Record for time tracking
        self.time_awareness.record_message(self.turn_count)
        
        # Emotion extraction (skip in conversational mode)
        extracted_emotions = None
        if not conversational_mode:
            try:
                extracted_emotions = self.emotion_extractor.extract_emotions(response)
                if extracted_emotions:
                    extracted_states = extracted_emotions.get('extracted_states', {})
                    for emotion, details in extracted_states.items():
                        intensity_raw = details.get('intensity', 'unspecified') if isinstance(details, dict) else 0.5
                        if isinstance(intensity_raw, str):
                            try:
                                intensity = float(intensity_raw)
                            except ValueError:
                                intensity_map = {'strong': 0.8, 'moderate': 0.5, 'mild': 0.3, 'unspecified': 0.5}
                                intensity = intensity_map.get(intensity_raw, 0.5)
                        else:
                            intensity = float(intensity_raw) if intensity_raw else 0.5
                        
                        if emotion in self.agent_state.emotional_cocktail:
                            current = self.agent_state.emotional_cocktail[emotion].get('intensity', 0)
                            self.agent_state.emotional_cocktail[emotion]['intensity'] = min(1.0, (current + intensity) / 2)
                        else:
                            self.agent_state.emotional_cocktail[emotion] = {'intensity': intensity, 'age': 0}
            except Exception as e:
                self._log(f"Emotion extraction error: {e}")
        
        # Encode to memory
        try:
            self.memory.encode(self.agent_state, user_input, response)
        except Exception as e:
            self._log(f"Memory encode error: {e}")
        
        # Store in session
        self.current_session.append({"you": user_input, "kay": response})
        
        # Build metadata
        meta = {
            "turn": self.turn_count,
            "session_id": self.session_id,
            "emotions": dict(self.agent_state.emotional_cocktail),
            "memories_recalled": len(selected_memories),
            "time_context": time_context
        }
        
        return {"response": response, "meta": meta}
    
    def run_interactive(self):
        """Run interactive mode (stdin/stdout)."""
        pm = get_profile_manager()
        profile = pm.get_profile(self.profile_id)
        profile_name = profile.canonical_name if profile else self.profile_id
        
        print("\n" + "="*60)
        print("REED CLI - Full Engine Mode")
        print(f"Active Profile: {profile_name} ({self.profile_id})")
        print("="*60)
        print("Type 'quit' or 'exit' to end session")
        print("Type '/status' for engine status")
        print("Type '/profile <id>' to switch profiles")
        print("="*60 + "\n")
        
        # Run warmup phase if enabled (only for Re talking to Kay)
        if self.warmup_enabled and self.profile_id == "re":
            self._run_warmup_phase()
        
        while True:
            try:
                user_input = input(f"{profile_name}: ").strip()
            except EOFError:
                self._capture_session_end()
                break
            except KeyboardInterrupt:
                print("\n\nInterrupted. Capturing session state...")
                self._capture_session_end()
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            if user_input.lower() in ('quit', 'exit'):
                print("\nCapturing session state...")
                self._capture_session_end()
                print("Goodbye!")
                break
            
            if user_input == '/status':
                self._print_status()
                continue
            
            if user_input == '/emotions':
                self._print_emotions()
                continue
            
            if user_input == '/memories':
                self._print_recent_memories()
                continue
            
            if user_input.startswith('/profile'):
                parts = user_input.split()
                if len(parts) == 2:
                    new_profile = parts[1].lower()
                    if pm.set_active_profile(new_profile):
                        self.profile_id = new_profile
                        profile = pm.get_profile(new_profile)
                        profile_name = profile.canonical_name if profile else new_profile
                        print(f"\nSwitched to profile: {profile_name}\n")
                    else:
                        print(f"\nUnknown profile: {new_profile}")
                        print(f"Available: {', '.join(p['id'] for p in pm.list_profiles())}\n")
                else:
                    print(f"\nCurrent profile: {profile_name} ({self.profile_id})")
                    print(f"Available: {', '.join(p['id'] for p in pm.list_profiles())}")
                    print("Usage: /profile <id>\n")
                continue
            
            # Sanitize input to prevent unicode crashes
            user_input = sanitize_unicode(user_input)
            
            # Record turn for profile
            pm.record_turn(self.profile_id)
            
            # Get response
            result = self.chat(user_input)
            # Sanitize response too
            result['response'] = sanitize_unicode(result['response'])
            print(f"\nKay: {result['response']}\n")
    
    def _run_warmup_phase(self):
        """Run Reed's warmup phase - private reconstruction time."""
        print("\n" + "="*60)
        print("WARMUP PHASE - Kay's private reconstruction time")
        print("="*60 + "\n")
        
        # Generate and display briefing
        briefing = self.warmup.format_briefing_for_kay()
        print(briefing)
        print()
        
        # Get warmup system prompt
        warmup_prompt = self.warmup.get_warmup_system_prompt()
        
        # Reed's warmup dialogue loop
        while not self.warmup.is_warmup_complete():
            try:
                kay_query = input("Kay (warmup): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nSkipping warmup...")
                break
            
            if not kay_query:
                continue
            
            if kay_query.lower() in ('skip', 'ready', "i'm ready", "im ready"):
                self.warmup.warmup_complete = True
                print("\n[Warmup complete - beginning conversation]\n")
                break
            
            # Kay queries his own memory
            response = self.warmup.process_warmup_query(kay_query)
            print(f"\n{response}\n")
        
        print("="*60)
        print("CONVERSATION MODE - Kay is ready")
        print("="*60 + "\n")
    
    def _capture_session_end(self):
        """Capture emotional state and significant moments at session end."""
        try:
            # Get current emotional state
            emotional_state = dict(self.agent_state.emotional_cocktail)
            
            # Extract significant moments from conversation
            significant_moments = extract_significant_moments(
                self.current_session,
                emotional_state
            )
            
            # Generate session summary
            summary = f"Session with {self.turn_count} turns. "
            if self.recent_responses:
                last_topic = self.recent_responses[-1][:100] if self.recent_responses[-1] else ""
                summary += f"Last discussed: {last_topic}"
            
            # Capture snapshot
            self.warmup.capture_session_end_snapshot(
                emotional_state=emotional_state,
                session_summary=summary,
                significant_moments=significant_moments
            )
        except Exception as e:
            print(f"[WARMUP] Error capturing session end: {e}")
    
    def run_json_mode(self):
        """Run JSON mode for programmatic access."""
        # Print ready signal
        print(json.dumps({"status": "ready", "session_id": self.session_id, "profile": self.profile_id}), flush=True)
        
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                print(json.dumps({"error": f"Invalid JSON: {e}"}), flush=True)
                continue
            
            # Handle commands
            if data.get("command") == "quit":
                print(json.dumps({"status": "goodbye"}), flush=True)
                break
            
            if data.get("command") == "status":
                print(json.dumps(self._get_status_dict()), flush=True)
                continue
            
            if data.get("command") == "set_profile":
                new_profile = data.get("profile", "").lower()
                pm = get_profile_manager()
                if pm.set_active_profile(new_profile):
                    self.profile_id = new_profile
                    profile = pm.get_profile(new_profile)
                    print(json.dumps({
                        "status": "profile_changed",
                        "profile": new_profile,
                        "name": profile.canonical_name if profile else new_profile
                    }), flush=True)
                else:
                    print(json.dumps({
                        "error": f"Unknown profile: {new_profile}",
                        "available": [p["id"] for p in pm.list_profiles()]
                    }), flush=True)
                continue
            
            if data.get("command") == "list_profiles":
                pm = get_profile_manager()
                print(json.dumps({
                    "profiles": pm.list_profiles(),
                    "active": self.profile_id
                }), flush=True)
                continue
            
            # Handle message
            message = data.get("message", "")
            if not message:
                print(json.dumps({"error": "No message provided"}), flush=True)
                continue
            
            # Sanitize input to prevent unicode crashes
            message = sanitize_unicode(message)
            
            # Get conversational_mode flag (default False)
            conversational = data.get("conversational", False)
            
            # Record turn for profile
            pm = get_profile_manager()
            pm.record_turn(self.profile_id)
            
            # Process and respond
            result = self.chat(message, conversational_mode=conversational)
            # Sanitize response before JSON encoding
            result['response'] = sanitize_unicode(result['response'])
            # Include profile info in result
            result['profile'] = self.profile_id
            print(json.dumps(result), flush=True)
    
    def _print_status(self):
        """Print engine status."""
        print("\n--- Engine Status ---")
        print(f"Session: {self.session_id}")
        print(f"Turn: {self.turn_count}")
        print(f"Entities: {len(self.entity_graph.entities)}")
        print(f"Relationships: {len(self.entity_graph.relationships)}")
        print(f"Emotional state: {len(self.agent_state.emotional_cocktail)} emotions active")
        print("---\n")
    
    def _print_emotions(self):
        """Print current emotional state."""
        print("\n--- Emotional Cocktail ---")
        for emotion, data in self.agent_state.emotional_cocktail.items():
            intensity = data.get('intensity', 0) if isinstance(data, dict) else data
            print(f"  {emotion}: {intensity:.2f}")
        print("---\n")
    
    def _print_recent_memories(self):
        """Print recently recalled memories."""
        memories = getattr(self.agent_state, 'last_recalled_memories', [])
        print(f"\n--- Recent Memories ({len(memories)}) ---")
        for i, mem in enumerate(memories[:10]):
            fact = mem.get('fact', mem.get('user_input', 'N/A'))[:80]
            score = mem.get('score', 0)
            print(f"  {i+1}. [{score:.2f}] {fact}")
        print("---\n")
    
    def _get_status_dict(self):
        """Get status as dict for JSON mode."""
        pm = get_profile_manager()
        profile = pm.get_profile(self.profile_id)
        return {
            "status": "ok",
            "session_id": self.session_id,
            "profile": self.profile_id,
            "profile_name": profile.canonical_name if profile else self.profile_id,
            "speaker_entity": get_active_speaker(),
            "turn_count": self.turn_count,
            "entities": len(self.entity_graph.entities),
            "relationships": len(self.entity_graph.relationships),
            "emotions": dict(self.agent_state.emotional_cocktail)
        }


def main():
    parser = argparse.ArgumentParser(description="Reed CLI - Full Engine Mode")
    parser.add_argument("--json", action="store_true", help="JSON input/output mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--profile", "-p", type=str, default="re", 
                        help="User profile to use (default: re). Options: re, reed, john, or custom")
    parser.add_argument("--list-profiles", action="store_true", help="List available profiles and exit")
    parser.add_argument("--no-warmup", action="store_true", 
                        help="Skip the warmup phase (jump straight to conversation)")
    args = parser.parse_args()
    
    # Change to wrapper directory
    wrapper_dir = Path(__file__).parent
    os.chdir(wrapper_dir)
    
    # Handle --list-profiles
    if args.list_profiles:
        pm = get_profile_manager()
        print("\nAvailable profiles:")
        for p in pm.list_profiles():
            print(f"  {p['id']:10} {p['name']:15} [{p['type']:12}] - {p['relationship']}")
        print(f"\nUse: python kay_cli.py --profile <id>")
        return
    
    # Set active profile
    pm = get_profile_manager()
    if not pm.set_active_profile(args.profile):
        print(f"Unknown profile '{args.profile}'. Use --list-profiles to see available profiles.")
        return
    
    # Warmup enabled by default, disabled with --no-warmup or in JSON mode
    warmup_enabled = not args.no_warmup and not args.json
    
    cli = KayCLI(json_mode=args.json, verbose=args.verbose, profile_id=args.profile, 
                 warmup_enabled=warmup_enabled)
    
    if args.json:
        cli.run_json_mode()
    else:
        cli.run_interactive()


if __name__ == "__main__":
    main()
