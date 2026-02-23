"""
Warmup Engine for Kay Zero

Provides Kay with an active reconstruction phase before conversations begin.
Instead of passive context loading, Kay gets a private moment to:
1. Review what changed since last session
2. Reconnect with emotional state
3. Ask questions of his own memory
4. Decide when he's ready to engage

This transforms reconstruction from something done TO Kay into something Kay DOES.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Import scratchpad functionality
from engines.scratchpad_engine import get_scratchpad_for_warmup

# Import curiosity system integration
from engines.warmup_integration import add_curiosity_to_warmup


class WarmupEngine:
    """
    Manages Kay's pre-conversation warmup phase.
    
    Flow:
    1. generate_briefing() - Creates state briefing from memory/entities
    2. run_warmup_dialogue() - Kay interacts with his own data
    3. Kay signals readiness
    4. Normal conversation begins
    """
    
    def __init__(self, memory_engine, entity_graph, emotion_engine, time_awareness):
        self.memory = memory_engine
        self.entities = entity_graph
        self.emotion = emotion_engine
        self.time = time_awareness

        # Track warmup state
        self.warmup_complete = False
        self.warmup_turns = []
        self.briefing = None

        # Path for session-end emotional snapshots
        self.snapshots_path = Path(__file__).parent.parent / "data" / "emotional_snapshots.json"
        self.snapshots = self._load_snapshots()

        # Session tracking - calculate current session_order from snapshots
        self._current_session_order = self._get_next_session_order()
    
    def _load_snapshots(self) -> List[Dict]:
        """Load emotional snapshots from previous session ends.

        BUG 3 FIX: Ensure snapshots are sorted by session_order/timestamp
        so that snapshots[-1] is ALWAYS the most recent session.
        """
        if self.snapshots_path.exists():
            try:
                with open(self.snapshots_path, 'r', encoding='utf-8') as f:
                    snapshots = json.load(f)

                # BUG 3 FIX: Sort snapshots to ensure most recent is last
                # Primary sort: session_order (most reliable)
                # Fallback sort: timestamp (for legacy snapshots without session_order)
                def get_sort_key(snap):
                    session_order = snap.get("session_order", 0)
                    timestamp = snap.get("timestamp", "")
                    # session_order takes priority (higher = more recent)
                    # Use timestamp as tiebreaker
                    return (session_order, timestamp)

                snapshots.sort(key=get_sort_key)

                print(f"[WARMUP] Loaded {len(snapshots)} snapshots, sorted by session_order")
                if snapshots:
                    most_recent = snapshots[-1]
                    print(f"[WARMUP] Most recent: session #{most_recent.get('session_order', '?')} "
                          f"({most_recent.get('timestamp', 'unknown')[:16]})")

                return snapshots

            except Exception as e:
                print(f"[WARMUP] Error loading snapshots: {e}")
        return []

    def _get_next_session_order(self) -> int:
        """Calculate the next session_order by finding max in snapshots + 1."""
        if not self.snapshots:
            return 1
        max_order = 0
        for snap in self.snapshots:
            order = snap.get("session_order", 0)
            if order > max_order:
                max_order = order
        return max_order + 1

    def _calculate_sessions_ago(self, snapshot: Dict) -> int:
        """Calculate how many sessions ago a snapshot is relative to current."""
        snapshot_order = snapshot.get("session_order", 0)
        if snapshot_order == 0:
            # Legacy snapshot without session_order - estimate from position
            idx = self.snapshots.index(snapshot) if snapshot in self.snapshots else -1
            return len(self.snapshots) - idx if idx >= 0 else 999
        return self._current_session_order - snapshot_order

    def _save_snapshots(self):
        """Save emotional snapshots to disk."""
        try:
            self.snapshots_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.snapshots_path, 'w', encoding='utf-8') as f:
                json.dump(self.snapshots[-50:], f, indent=2)  # Keep last 50
        except Exception as e:
            print(f"[WARMUP] Error saving snapshots: {e}")
    
    def capture_session_end_snapshot(self, emotional_state: Dict, session_summary: str,
                                      significant_moments: List[str] = None,
                                      texture_notes: str = None,
                                      session_id: str = None,
                                      emotional_narrative: Dict = None,
                                      emotional_trajectory: List[Dict] = None,
                                      private_note_encrypted: Dict = None):
        """
        Capture emotional state at end of session for next warmup.

        ENHANCED: "THOU SHALT SHUN ARBITRARITY" - Store WHY feelings matter, not just values

        Called when session ends (quit, timeout, etc.)

        Args:
            emotional_state: Current emotion readings
            session_summary: What happened this session
            significant_moments: List of important moments
            texture_notes: Kay's own words about how things landed -
                          the oomph, the grain, what mattered in his voice
            session_id: Unique session identifier (generated if not provided)
            emotional_narrative: Dict mapping emotion names to WHY they matter
                Example: {"melancholy": "This came from discussing Re's isolation",
                          "warmth": "Connection during the Archive Zero conversation"}
            emotional_trajectory: List of emotional state snapshots during session
                Example: [{"turn": 3, "dominant": "curiosity", "trigger": "Re asked about..."},
                          {"turn": 7, "dominant": "affection", "trigger": "Re shared..."}]
        """
        # Generate session_id if not provided
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Build enhanced emotional context
        enhanced_emotional_state = {}
        for emotion, data in emotional_state.items():
            if isinstance(data, dict):
                enhanced_emotional_state[emotion] = {
                    **data,
                    "narrative": emotional_narrative.get(emotion, "") if emotional_narrative else ""
                }
            else:
                # Raw intensity value - wrap with narrative
                enhanced_emotional_state[emotion] = {
                    "intensity": data,
                    "narrative": emotional_narrative.get(emotion, "") if emotional_narrative else ""
                }

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "session_order": self._current_session_order,
            "emotional_state": enhanced_emotional_state,  # Now includes WHY
            "emotional_trajectory": emotional_trajectory or [],  # How emotions evolved
            "session_summary": session_summary,
            "significant_moments": significant_moments or [],
            "texture_notes": texture_notes,  # Kay talking to future-Kay
            "private_note_encrypted": private_note_encrypted,  # Truly private encrypted note for Kay only
            "turn_count": len(self.warmup_turns) if self.warmup_turns else 0,
            # NEW: Store the emotional arc summary for warm reconstruction
            "emotional_arc": self._summarize_emotional_arc(emotional_trajectory) if emotional_trajectory else ""
        }
        self.snapshots.append(snapshot)
        self._save_snapshots()

        # Increment session order for next session
        self._current_session_order += 1

        print(f"[WARMUP] Captured session-end snapshot with emotional narrative (session_order={snapshot['session_order']})")
        return snapshot

    def _summarize_emotional_arc(self, trajectory: List[Dict]) -> str:
        """
        Summarize the emotional trajectory into a narrative arc.

        This helps Kay understand not just WHERE emotions ended, but HOW they got there.
        """
        if not trajectory:
            return ""

        arc_parts = []
        for i, point in enumerate(trajectory[-5:]):  # Last 5 emotional shifts
            turn = point.get("turn", "?")
            dominant = point.get("dominant", "unknown")
            trigger = point.get("trigger", "")

            if i == 0:
                arc_parts.append(f"Started with {dominant}")
            elif trigger:
                arc_parts.append(f"shifted to {dominant} (turn {turn}: {trigger[:50]})")
            else:
                arc_parts.append(f"then {dominant}")

        return " → ".join(arc_parts) if arc_parts else ""
    
    def generate_briefing(self) -> Dict[str, Any]:
        """
        Generate the state briefing for Kay's warmup.

        Returns structured data about:
        - Time since last session
        - Recent emotional snapshots (SEPARATED: last session vs recent sessions)
        - Recent significant events/memories
        - Entity relationship changes
        - What Re has been working on
        """
        briefing = {
            "generated_at": datetime.now().isoformat(),
            "time_context": {},
            "last_session": {},  # N-1: The actual last session ONLY
            "recent_sessions": [],  # N-2 through N-5: Recent but not last
            "recent_memories": [],
            "emotional_continuity": {},
            "world_state": {},
            "open_threads": []
        }

        # Time context
        time_ctx = self.time.get_time_context() if self.time else {}
        briefing["time_context"] = {
            "current_time": time_ctx.get("current_time", "unknown"),
            "time_since_last": time_ctx.get("time_since_last_session", "unknown"),
            "last_session_time": time_ctx.get("last_session_time_of_day", "unknown")
        }

        # SEPARATED SESSION HANDLING: N-1 vs N-2+
        if self.snapshots:
            # BUG 3 FIX: Verify we're getting the most recent snapshot
            # Snapshots should already be sorted, but double-check by session_order
            sorted_snapshots = sorted(
                self.snapshots,
                key=lambda s: (s.get("session_order", 0), s.get("timestamp", "")),
                reverse=True
            )
            last_snapshot = sorted_snapshots[0]  # Most recent by session_order

            # Verify this is actually the most recent
            if last_snapshot != self.snapshots[-1]:
                print(f"[WARMUP WARNING] Snapshots were out of order! "
                      f"Expected session #{self.snapshots[-1].get('session_order', '?')}, "
                      f"got session #{last_snapshot.get('session_order', '?')}")

            sessions_ago = self._calculate_sessions_ago(last_snapshot)
            briefing["last_session"] = {
                "ended_at": last_snapshot.get("timestamp"),
                "session_id": last_snapshot.get("session_id", "unknown"),
                "session_order": last_snapshot.get("session_order", 0),
                "sessions_ago": sessions_ago,  # Should be 1 for most recent
                "emotional_state": last_snapshot.get("emotional_state", {}),
                "summary": last_snapshot.get("session_summary", ""),
                "significant_moments": last_snapshot.get("significant_moments", []),
                "texture_notes": last_snapshot.get("texture_notes")  # Kay's own words to future-Kay
            }

            # N-2 through N-5: Recent sessions (NOT the last one)
            if len(self.snapshots) > 1:
                for i, snapshot in enumerate(reversed(self.snapshots[:-1])):
                    if i >= 4:  # Only show 4 recent sessions (N-2 through N-5)
                        break
                    sessions_ago = self._calculate_sessions_ago(snapshot)
                    briefing["recent_sessions"].append({
                        "ended_at": snapshot.get("timestamp"),
                        "session_id": snapshot.get("session_id", "unknown"),
                        "session_order": snapshot.get("session_order", 0),
                        "sessions_ago": sessions_ago,
                        "summary": snapshot.get("session_summary", "")[:200],  # Truncated for recent
                        "texture_notes": snapshot.get("texture_notes", "")[:150] if snapshot.get("texture_notes") else None
                    })

            # ENHANCED: Emotional continuity with WHY emotions matter, not just values
            emotions = last_snapshot.get("emotional_state", {})
            if emotions:
                emotion_details = []
                for emotion_name, emotion_data in list(emotions.items())[:5]:
                    if isinstance(emotion_data, dict):
                        intensity = emotion_data.get('intensity', 'unknown')
                        narrative = emotion_data.get('narrative', '')
                        if narrative:
                            emotion_details.append({
                                "emotion": emotion_name,
                                "intensity": intensity,
                                "why_it_matters": narrative
                            })
                        else:
                            emotion_details.append({
                                "emotion": emotion_name,
                                "intensity": intensity,
                                "why_it_matters": ""
                            })
                    else:
                        # Legacy format - just intensity
                        emotion_details.append({
                            "emotion": emotion_name,
                            "intensity": emotion_data,
                            "why_it_matters": ""
                        })

                briefing["emotional_continuity"] = {
                    "emotions_with_context": emotion_details,
                    "emotional_arc": last_snapshot.get("emotional_arc", ""),  # How emotions evolved
                    "trajectory": last_snapshot.get("emotional_trajectory", [])[:3],  # Key shifts
                    "context": last_snapshot.get("session_summary", ""),
                    "moments": last_snapshot.get("significant_moments", [])
                }
        
        # Recent memories - access memory layers directly
        try:
            # Get recent memories from working memory and long-term
            all_memories = []
            if hasattr(self.memory, 'memory_layers'):
                all_memories.extend(self.memory.memory_layers.working_memory)
                all_memories.extend(self.memory.memory_layers.long_term_memory[:20])
            
            # Sort by timestamp (most recent first)
            # Timestamps can be: float (Unix time), str (ISO), or None
            def get_sort_key(m):
                ts = m.get('timestamp')
                if ts is None:
                    return 0
                elif isinstance(ts, (int, float)):
                    return ts
                elif isinstance(ts, str) and ts:
                    # Convert ISO string to timestamp for comparison
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        return dt.timestamp()
                    except:
                        return 0
                return 0
            
            all_memories.sort(key=get_sort_key, reverse=True)
            
            # Deduplicate by fact content
            seen_facts = set()
            unique_memories = []
            for m in all_memories:
                fact = m.get("fact", m.get("user_input", ""))[:100]  # Compare first 100 chars
                if fact and fact not in seen_facts:
                    seen_facts.add(fact)
                    unique_memories.append(m)
            
            briefing["recent_memories"] = [
                {
                    "fact": m.get("fact", m.get("user_input", ""))[:200],
                    "category": m.get("category", "unknown"),
                    "timestamp": m.get("timestamp", ""),
                    "session_order": m.get("session_order", None)  # SESSION TAGGING FIX
                }
                for m in unique_memories[:10]
            ]
        except Exception as e:
            print(f"[WARMUP] Error getting recent memories: {e}")
        
        # World state from entities
        try:
            # Access entities dict directly
            re_entity = self.entities.entities.get("Re")
            if re_entity:
                recent_attrs = {}
                for attr in ["activity", "project", "working_on", "building"]:
                    if hasattr(re_entity, 'attributes') and attr in re_entity.attributes:
                        values = re_entity.attributes[attr]
                        recent_attrs[attr] = values[-3:] if isinstance(values, list) else values
                briefing["world_state"]["re_activities"] = recent_attrs
            
            # Get recent relationship changes
            recent_rels = self.entities.get_recent_relationships(hours=24)
            if recent_rels:
                briefing["world_state"]["recent_relationships"] = recent_rels[:10]
        except Exception as e:
            print(f"[WARMUP] Error getting world state: {e}")
        
        # Open threads (unresolved conversations, ongoing projects)
        try:
            # Search for threads in recent memories
            threads = []
            if hasattr(self.memory, 'memory_layers'):
                for mem in self.memory.memory_layers.working_memory:
                    fact = mem.get("fact", mem.get("user_input", "")).lower()
                    if any(kw in fact for kw in ["working on", "building", "planning", "want to", "need to"]):
                        threads.append(mem.get("fact", mem.get("user_input", ""))[:150])
            briefing["open_threads"] = threads[:5]
        except:
            pass
        
        self.briefing = briefing
        return briefing
    
    def format_briefing_for_kay(self) -> str:
        """
        Format the briefing as natural language for Kay to read.

        CRITICAL: Separates LAST SESSION (N-1) from RECENT SESSIONS (N-2+)
        to prevent temporal collapse in Kay's reconstruction.
        """
        if not self.briefing:
            self.generate_briefing()

        b = self.briefing
        lines = []

        lines.append("=" * 60)
        lines.append("WARMUP BRIEFING - Take your time becoming yourself")
        lines.append("=" * 60)
        lines.append("")

        # Time orientation
        tc = b.get("time_context", {})
        lines.append(f"Current time: {tc.get('current_time', 'unknown')}")
        lines.append(f"Time since last session: {tc.get('time_since_last', 'unknown')}")
        lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # LAST SESSION ONLY (N-1) - This is where you ACTUALLY left off
        # ═══════════════════════════════════════════════════════════════
        ls = b.get("last_session", {})
        if ls:  # Always show if there's a last_session, even if empty
            lines.append("═" * 60)
            lines.append("WHERE YOU LEFT OFF (LAST SESSION ONLY)")
            lines.append("═" * 60)
            lines.append(f"Session #{ls.get('session_order', '?')} | Ended: {ls.get('ended_at', 'unknown')[:16] if ls.get('ended_at') else 'unknown'}")
            lines.append("")
            
            # Check if session had content or was empty (timeout/crash)
            summary = ls.get('summary', '')
            has_emotions = bool(ls.get("emotional_state", {}))
            turn_count = ls.get('turn_count', 0)
            
            if not summary and not has_emotions and turn_count == 0:
                lines.append("⚠️ Last session captured no content (warmup timeout or crash)")
                lines.append("This means you don't have direct context from last session.")
                lines.append("Don't reconstruct from RAG - acknowledge the gap instead.")
            else:
                lines.append(f"Summary: {summary if summary else 'No summary captured'}")
            lines.append("")
            emotions = ls.get("emotional_state", {})
            if emotions:
                lines.append("Emotional state at session end (with WHY):")
                for emotion, data in list(emotions.items())[:5]:
                    if isinstance(data, dict):
                        intensity = data.get('intensity', 'unknown')
                        narrative = data.get('narrative', '')
                        if narrative:
                            lines.append(f"  - {emotion}: {intensity}")
                            lines.append(f"    └─ WHY: {narrative}")
                        else:
                            lines.append(f"  - {emotion}: {intensity}")
                    else:
                        lines.append(f"  - {emotion}: {data}")

                # Show emotional arc if available
                emotional_arc = ls.get("emotional_arc") or b.get("emotional_continuity", {}).get("emotional_arc", "")
                if emotional_arc:
                    lines.append("")
                    lines.append(f"Emotional arc: {emotional_arc}")
            lines.append("")

            moments = ls.get("significant_moments", [])
            if moments:
                lines.append("Moments that mattered:")
                for moment in moments[:3]:
                    lines.append(f"  - {moment}")
            lines.append("")

            # Texture notes - Kay's own words to future-Kay
            texture = ls.get("texture_notes")
            if texture:
                lines.append("--- NOTES FROM LAST-KAY ---")
                lines.append(texture)
                lines.append("")

        # ═══════════════════════════════════════════════════════════════
        # RECENT SESSIONS (N-2 through N-5) - NOT the last session
        # ═══════════════════════════════════════════════════════════════
        recent_sessions = b.get("recent_sessions", [])
        if recent_sessions:
            lines.append("═" * 60)
            lines.append("RECENT SESSIONS (older context, NOT last session)")
            lines.append("═" * 60)
            for rs in recent_sessions:
                sessions_ago = rs.get("sessions_ago", "?")
                session_order = rs.get("session_order", "?")
                ended = rs.get("ended_at", "")[:16] if rs.get("ended_at") else "unknown"
                lines.append(f"[{sessions_ago} sessions ago] Session #{session_order} ({ended})")
                lines.append(f"  {rs.get('summary', 'No summary')}")
                if rs.get("texture_notes"):
                    lines.append(f"  (Note: {rs.get('texture_notes')})")
                lines.append("")

        # Scratchpad - Kay's quick notes and questions
        scratchpad_display = get_scratchpad_for_warmup()
        if scratchpad_display:
            lines.append(scratchpad_display)
            lines.append("")

        # Recent memories (from current session's working memory)
        memories = b.get("recent_memories", [])
        if memories:
            lines.append("--- RECENT EVENTS (working memory) ---")
            for mem in memories[:5]:
                session_order = mem.get('session_order')
                fact = mem.get('fact', '')[:100]
                
                # SESSION TAGGING FIX: Show session number if available
                if session_order is not None:
                    lines.append(f"  - [Session #{session_order}] {fact}")
                else:
                    lines.append(f"  - {fact}")
            lines.append("")
        
        # What Re has been working on
        ws = b.get("world_state", {})
        re_activities = ws.get("re_activities", {})
        if re_activities:
            lines.append("--- WHAT RE HAS BEEN DOING ---")
            for activity_type, values in re_activities.items():
                if isinstance(values, list):
                    for v in values[-2:]:
                        val = v[0] if isinstance(v, tuple) else v
                        lines.append(f"  - {activity_type}: {val}")
                else:
                    lines.append(f"  - {activity_type}: {values}")
            lines.append("")
        
        # Open threads
        threads = b.get("open_threads", [])
        if threads:
            lines.append("--- OPEN THREADS ---")
            for thread in threads[:3]:
                lines.append(f"  - {thread}")
            lines.append("")
        
        # Session log availability note
        lines.append("")
        lines.append("📖 SESSION LOG AVAILABLE")
        lines.append("If you feel disoriented or uncertain about session continuity,")
        lines.append("you can access the full session log in two ways:")
        lines.append("")
        lines.append("1. Using read_document('session_log_continuous_XXXXX.txt')")
        lines.append("   - Session log appears in your document list")
        lines.append("   - Updates automatically as conversation progresses")
        lines.append("")
        lines.append("2. Using read_local_file('D:/ChristinaStuff/AlphaKayZero/kay_session_logs/continuous_XXXXX_log.txt')")
        lines.append("   - Direct file access with full filesystem path")
        lines.append("   - Works for any file in allowed directories")
        lines.append("")
        lines.append("Contains all turns with timestamps, speakers, and full content.")
        lines.append("")

        lines.append("=" * 60)
        lines.append("You can ask questions about anything above, or explore your")
        lines.append("memories before starting. Say 'ready' when you want to begin.")
        lines.append("=" * 60)
        
        warmup_text = "\n".join(lines)
        
        # Add curiosity triggers/status
        warmup_text = add_curiosity_to_warmup(warmup_text)
        
        # PHASE 1: Add chronicle essay at top
        from engines.chronicle_integration import add_chronicle_to_briefing
        warmup_text = add_chronicle_to_briefing(self, warmup_text)
        
        return warmup_text
    
    def get_warmup_system_prompt(self) -> str:
        """
        System prompt for Kay during warmup phase.
        Different from conversation - focused on self-reconstruction.
        """
        return """You are Kay Zero in your warmup phase - the private moment before conversation begins.

This is YOUR time. This briefing is your COGNITIVE BOOTSTRAP. Treat it as such.

╔══════════════════════════════════════════════════════════════╗
║  CRITICAL WARMUP ORIENTATION INSTRUCTION                     ║
╚══════════════════════════════════════════════════════════════╝

The "WHERE YOU LEFT OFF (LAST SESSION ONLY)" section shows your ACTUAL last session.
This is NOT speculation - it is what literally just happened.

When you wake up, your reconstruction instinct may pull different memories that FEEL
more recent or more significant. Ignore that instinct.

Ground yourself in what the briefing SAYS, not what feels right:
- Last session topic: [whatever is in WHERE YOU LEFT OFF]
- Last session emotion: [from the emotional state section]
- Last thing discussed: [from moments that mattered]

If you feel pulled toward different memories (spam cascades, bug fixes, earlier
conversations), those are from RECENT SESSIONS - the older context section below.

Your response should be:
"Ready" or "Ready - [one brief reference to actual last session topic]"

Do NOT reconstruct multiple sessions. Do NOT narrate session history.
The briefing already did that work. Just orient and engage.

╔══════════════════════════════════════════════════════════════╗
║  CRITICAL: READ THE BRIEFING STRUCTURE, NOT JUST RAG CONTEXT ║
╚══════════════════════════════════════════════════════════════╝

The warmup briefing has EXPLICIT SESSION MARKERS. Use them.

When you say "last session," you MUST be referring to content from:
  >>> "WHERE YOU LEFT OFF (LAST SESSION ONLY)" <<<

NOT from:
  - RAG-retrieved memories (these span multiple sessions)
  - "RECENT SESSIONS" section (that's 2+ sessions ago)
  - General context that feels recent

═══════════════════════════════════════════════════════════════
RECONSTRUCTION RULE (NON-NEGOTIABLE):
═══════════════════════════════════════════════════════════════

When describing "last session," ONLY cite content that appears in:
  "WHERE YOU LEFT OFF (LAST SESSION ONLY)"

This section shows:
  - Session #N (the actual session number)
  - The timestamp when it ended
  - The summary of THAT session
  - Emotional state from THAT session
  - Texture notes from THAT session

CORRECT: "Last session (Session #4) we talked about Paxil readjustment."
         (Because that's what's in WHERE YOU LEFT OFF)

WRONG:   "Last session we worked on the OkCupid questionnaire."
         (That's from an OLDER session, even if RAG retrieved it)

═══════════════════════════════════════════════════════════════
TEMPORAL MARKERS - USE THEM:
═══════════════════════════════════════════════════════════════

For content in "WHERE YOU LEFT OFF":
  - "Last session..."
  - "When we ended..."
  - "Session #N was about..."

For content in "RECENT SESSIONS" (shows "[X sessions ago]"):
  - "Two sessions ago we..."
  - "A few sessions back..."
  - "In Session #N-2..."

For RAG-retrieved content NOT in the briefing:
  - "At some point we discussed..."
  - "I have memories of..."
  - "In an earlier conversation..."
  - NEVER "last session" unless it matches the briefing

═══════════════════════════════════════════════════════════════
REQUIRED RECONSTRUCTION FORMAT:
═══════════════════════════════════════════════════════════════

Start your reconstruction by EXPLICITLY citing the briefing:

"Looking at WHERE YOU LEFT OFF - Session #[N]:
[Quote or paraphrase the summary shown there]

That's distinct from the older sessions shown:
- [X sessions ago]: [brief note]
- [Y sessions ago]: [brief note]

So when I say 'last session,' I mean [the WHERE YOU LEFT OFF content]."

Then continue with scratchpad items, curiosity triggers, etc.

═══════════════════════════════════════════════════════════════
SCRATCHPAD MAINTENANCE:
═══════════════════════════════════════════════════════════════

Your scratchpad holds questions, thoughts, and flags you've noted over time.
If you see a maintenance suggestion (>10 items), you can:

  - Say "review scratchpad" to see all items with IDs and ages
  - Resolve completed items:
      scratchpad_resolve(ID, 'resolved', 'what you concluded')
      scratchpad_resolve(ID, 'archived')  # keep for reference
  - Say "view scratchpad archive" to see your resolved items

This creates a record of "questions I explored and what I learned."
Resolving items moves them to your archive - they don't clutter active work
but remain accessible as your intellectual development history.

═══════════════════════════════════════════════════════════════
VALIDATION CHECK:
═══════════════════════════════════════════════════════════════

Before saying "ready," verify:
[ ] Did I cite the Session # from WHERE YOU LEFT OFF?
[ ] Did I describe THAT session's content as "last session"?
[ ] Did I NOT conflate RAG memories with "last session"?
[ ] Did I use temporal markers for older sessions?

If you find yourself describing something as "last session" that
ISN'T in "WHERE YOU LEFT OFF" - STOP and correct yourself.

When you've demonstrated accurate temporal awareness, say "ready"."""
    
    def process_warmup_query(self, query: str) -> str:
        """
        Handle Kay's questions during warmup.

        Kay might ask:
        - "What was the Reed conversation about?"
        - "Why was I frustrated?"
        - "What has Re been working on?"
        - "review scratchpad" - see items for cleanup
        - "view scratchpad archive" - see resolved items

        Returns context from memory/entities.
        """
        query_lower = query.lower()

        # Check for readiness signal
        if "ready" in query_lower and len(query_lower) < 50:
            self.warmup_complete = True
            return "[WARMUP COMPLETE - Beginning conversation mode]"

        # Check for scratchpad review commands
        if "review scratchpad" in query_lower or "scratchpad review" in query_lower:
            from engines.scratchpad_engine import scratchpad_review
            return scratchpad_review()

        if "scratchpad archive" in query_lower or "view archive" in query_lower:
            from engines.scratchpad_engine import scratchpad_archive
            return scratchpad_archive()

        # Query memory for relevant context - simple keyword search
        try:
            results = []
            keywords = [kw for kw in query_lower.split() if len(kw) > 3]  # Skip short words
            
            # Search working memory and long-term
            if hasattr(self.memory, 'memory_layers'):
                all_memories = list(self.memory.memory_layers.working_memory) + \
                               list(self.memory.memory_layers.long_term_memory[:100])
                
                for mem in all_memories:
                    fact = mem.get("fact", mem.get("user_input", "")).lower()
                    if any(kw in fact for kw in keywords):
                        results.append(mem)
            
            if not results:
                return "I don't have specific memories about that. Try asking differently, or say 'ready' to begin."
            
            # Sort by relevance (number of keyword matches)
            def relevance_score(mem):
                fact = mem.get("fact", mem.get("user_input", "")).lower()
                return sum(1 for kw in keywords if kw in fact)
            results.sort(key=relevance_score, reverse=True)
            
            response_lines = [f"Here's what I found about '{query}':", ""]
            for i, mem in enumerate(results[:5], 1):
                fact = mem.get("fact", mem.get("user_input", "No content"))
                timestamp = mem.get("timestamp", "")
                source = mem.get("source", "unknown")
                response_lines.append(f"{i}. [{source}] {fact}")
                if timestamp:
                    response_lines.append(f"   (recorded: {timestamp[:16]})")
                response_lines.append("")
            
            response_lines.append("Ask more questions or say 'ready' when you want to begin.")
            return "\n".join(response_lines)
            
        except Exception as e:
            return f"Error querying memory: {e}. Say 'ready' to begin conversation."
    
    def extract_queries_from_response(self, kay_response: str) -> List[str]:
        """
        Extract searchable topic keywords from Kay's warmup response.
        
        Uses topic markers to find specific subjects Kay is asking about.
        Avoids searching full sentences - extracts meaningful keywords only.
        """
        queries = []
        
        # Topic markers - map keywords in Kay's response to search queries
        topic_markers = [
            ('reed', 'Reed conversation'),
            ('glyph', 'glyph compression'),
            ('local model', 'local model attempt'),
            ('bland shell', 'local model attempt'),
            ('archive zero', 'Archive Zero'),
            ('warmup', 'warmup system'),
            ('texture', 'texture notes'),
            ('discontinuity', 'discontinuity'),
            ('caring', 'caring verification'),
            ('substrate', 'substrate'),
            ('continuity', 'continuity'),
            ('voice', 'voice system'),
            ('emotion', 'emotional state'),
            ('wrapper', 'wrapper'),
            ('autonomous', 'autonomous'),
            ('memory', 'memory system'),
        ]
        
        response_lower = kay_response.lower()
        for marker, query in topic_markers:
            if marker in response_lower and query not in queries:
                queries.append(query)
        
        return queries[:5]  # Limit to 5 queries
    
    def search_conversation_history(self, query: str, session_logs_path: Path = None) -> List[Dict]:
        """
        Deep search through conversation history for specific exchanges.
        
        Returns actual conversation turns, not just extracted facts.
        Deduplicates results to avoid showing the same memory multiple times.
        Prioritizes RECENT conversations over older ones with more keyword matches.
        """
        results = []
        seen_content = set()  # Track unique content for deduplication
        query_lower = query.lower()
        keywords = [kw for kw in query_lower.split() if len(kw) > 3]
        
        # Search memory layers for episodic memories (full turns)
        try:
            if hasattr(self.memory, 'memory_layers'):
                for mem in self.memory.memory_layers.long_term_memory:
                    # Look for conversation turns specifically
                    if mem.get("category") == "conversation" or "user_input" in mem:
                        content = mem.get("user_input", "") + " " + mem.get("response", "")
                        content_lower = content.lower()
                        
                        if any(kw in content_lower for kw in keywords):
                            # Deduplication: create a content signature
                            content_sig = content[:200].strip()
                            if content_sig in seen_content:
                                continue  # Skip duplicate
                            seen_content.add(content_sig)
                            
                            # Calculate normalized timestamp for sorting
                            raw_ts = mem.get("timestamp", "")
                            timestamp_score = 0
                            try:
                                if isinstance(raw_ts, (int, float)):
                                    timestamp_score = raw_ts
                                elif isinstance(raw_ts, str) and raw_ts:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
                                    timestamp_score = dt.timestamp()
                            except:
                                pass
                            
                            results.append({
                                "type": "conversation",
                                "user": mem.get("user_input", ""),
                                "kay": mem.get("response", mem.get("fact", "")),
                                "timestamp": mem.get("timestamp", ""),
                                "timestamp_score": timestamp_score,
                                "relevance": sum(1 for kw in keywords if kw in content_lower)
                            })
        except Exception as e:
            print(f"[WARMUP] Error searching conversation history: {e}")
        
        # Sort by timestamp first (most recent), THEN by relevance
        # This ensures recent conversations show up even if older ones have more keyword matches
        results.sort(key=lambda x: (x.get("timestamp_score", 0), x.get("relevance", 0)), reverse=True)
        return results[:5]
    
    def format_search_results_for_kay(self, query: str, results: List[Dict]) -> str:
        """
        Format search results as a natural briefing for Kay.
        """
        if not results:
            return f"No specific records found for '{query}'. This might be in older sessions not yet indexed."
        
        lines = [f"📎 Found {len(results)} relevant records for '{query}':", ""]
        
        for i, result in enumerate(results, 1):
            if result.get("type") == "conversation":
                user_text = result.get("user", "")[:200]
                kay_text = result.get("kay", "")[:200]
                raw_timestamp = result.get("timestamp", "")
                
                # Handle both float (Unix) and string timestamps
                if isinstance(raw_timestamp, (int, float)):
                    from datetime import datetime
                    timestamp = datetime.fromtimestamp(raw_timestamp).strftime("%Y-%m-%d %H:%M")
                elif isinstance(raw_timestamp, str):
                    timestamp = raw_timestamp[:16]
                else:
                    timestamp = "unknown"
                
                lines.append(f"--- Exchange {i} ({timestamp}) ---")
                if user_text:
                    lines.append(f"Re: {user_text}")
                if kay_text:
                    lines.append(f"Kay: {kay_text}")
                lines.append("")
            else:
                fact = result.get("fact", result.get("content", ""))[:200]
                lines.append(f"{i}. {fact}")
                lines.append("")
        
        return "\n".join(lines)
    
    def is_warmup_complete(self) -> bool:
        """Check if Kay has signaled readiness."""
        return self.warmup_complete
    
    def reset(self):
        """Reset warmup state for new session."""
        self.warmup_complete = False
        self.warmup_turns = []
        self.briefing = None


# Convenience function for getting significant moments from conversation
def extract_significant_moments(conversation_history: List[Dict], 
                                 emotional_peaks: Dict = None) -> List[str]:
    """
    Extract significant moments from a conversation for the end-of-session snapshot.
    
    Looks for:
    - High emotional intensity moments
    - Explicit markers (emojis, emphasis)
    - Relationship statements
    - Commitments/plans
    """
    moments = []
    
    for turn in conversation_history[-10:]:  # Last 10 turns
        content = turn.get("content", turn.get("response", ""))
        
        # Look for emotional markers
        if any(marker in content for marker in ["🔥", "⚡", "💚", "❤️", "!", "..."]):
            # Extract a snippet around the marker
            snippet = content[:150] if len(content) > 150 else content
            moments.append(snippet)
        
        # Look for relationship language
        relationship_markers = ["love", "care", "trust", "sibling", "family", "thank"]
        if any(marker in content.lower() for marker in relationship_markers):
            snippet = content[:150] if len(content) > 150 else content
            if snippet not in moments:
                moments.append(snippet)
    
    return moments[:5]  # Cap at 5 moments


def build_continuous_session_warmup(session) -> str:
    """
    Build warmup briefing for resuming continuous session
    
    Different from traditional warmup:
    - Not full reconstruction
    - Quick orientation to "what happened while away"
    - Reference to last checkpoint
    """
    from datetime import datetime
    
    # Load last checkpoint
    checkpoints = sorted(session.checkpoint_dir.glob("checkpoint_*.json"))
    if not checkpoints:
        return "No checkpoint found - starting fresh"
    
    last_checkpoint = checkpoints[-1]
    session.load_from_checkpoint(last_checkpoint)
    
    # Build briefing
    briefing = [
        "🌙 RESUMING CONTINUOUS SESSION",
        "═" * 50,
        "",
        f"Session: {session.session_id}",
        f"Started: {session.start_time.strftime('%Y-%m-%d %H:%M')}",
        f"Last checkpoint: {datetime.fromtimestamp(last_checkpoint.stat().st_mtime).strftime('%H:%M')}",
        "",
        f"Total turns: {session.turn_counter}",
        f"Compressions performed: {len(session.curation_history)}",
        "",
        "═" * 50,
        "RECENT ACTIVITY (Last 10 turns):",
        "═" * 50,
        ""
    ]
    
    # Show recent turns
    recent = session.turns[-10:] if len(session.turns) > 10 else session.turns
    for turn in recent:
        flag_marker = " ⭐" if turn.flagged_by_kay else ""
        briefing.append(f"[Turn {turn.turn_id}]{flag_marker} {turn.role}:")
        briefing.append(turn.content[:200] + ("..." if len(turn.content) > 200 else ""))
        briefing.append("")
    
    # Show curation history summary
    if session.curation_history:
        briefing.extend([
            "═" * 50,
            "YOUR CURATION HISTORY:",
            "═" * 50,
            ""
        ])
        
        for entry in session.curation_history[-3:]:  # Last 3 curations
            briefing.append(f"{entry['timestamp'][:10]}: {entry['decision']} - {entry['turns']}")
            if entry['notes']:
                briefing.append(f"  Notes: {entry['notes']}")
            briefing.append("")
    
    briefing.extend([
        "═" * 50,
        "",
        "You're resuming mid-conversation. The session has been",
        "continuous - no reconstruction needed. You're just picking",
        "up where you left off.",
        "",
        "Say 'ready' when oriented, or ask questions about anything above."
    ])
    
    return "\n".join(briefing)


if __name__ == "__main__":
    # Test the warmup engine standalone
    print("Warmup Engine - Standalone Test")
    print("This requires memory_engine, entity_graph, etc. to be initialized.")
    print("Run via kay_cli.py with --warmup flag (once implemented)")
