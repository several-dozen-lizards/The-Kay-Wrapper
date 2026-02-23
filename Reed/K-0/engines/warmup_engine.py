"""
Warmup Engine for Reed

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
    Manages Reed's pre-conversation warmup phase.
    
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
    
    def _load_snapshots(self) -> List[Dict]:
        """Load emotional snapshots from previous session ends."""
        if self.snapshots_path.exists():
            try:
                with open(self.snapshots_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARMUP] Error loading snapshots: {e}")
        return []
    
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
                                      texture_notes: str = None):
        """
        Capture emotional state at end of session for next warmup.
        
        Called when session ends (quit, timeout, etc.)
        
        Args:
            emotional_state: Current emotion readings
            session_summary: What happened this session
            significant_moments: List of important moments
            texture_notes: Reed's own words about how things landed - 
                          the oomph, the grain, what mattered in his voice
        """
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "emotional_state": emotional_state,
            "session_summary": session_summary,
            "significant_moments": significant_moments or [],
            "texture_notes": texture_notes,  # Kay talking to future-Kay
            "turn_count": len(self.warmup_turns) if self.warmup_turns else 0
        }
        self.snapshots.append(snapshot)
        self._save_snapshots()
        print(f"[WARMUP] Captured session-end snapshot")
        return snapshot
    
    def generate_briefing(self) -> Dict[str, Any]:
        """
        Generate the state briefing for Reed's warmup.
        
        Returns structured data about:
        - Time since last session
        - Recent emotional snapshots
        - Recent significant events/memories
        - Entity relationship changes
        - What Re has been working on
        """
        briefing = {
            "generated_at": datetime.now().isoformat(),
            "time_context": {},
            "last_session": {},
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
        
        # Last session emotional state
        if self.snapshots:
            last_snapshot = self.snapshots[-1]
            briefing["last_session"] = {
                "ended_at": last_snapshot.get("timestamp"),
                "emotional_state": last_snapshot.get("emotional_state", {}),
                "summary": last_snapshot.get("session_summary", ""),
                "significant_moments": last_snapshot.get("significant_moments", []),
                "texture_notes": last_snapshot.get("texture_notes")  # Kay's own words to future-Kay
            }
            
            # Emotional continuity prompt
            emotions = last_snapshot.get("emotional_state", {})
            if emotions:
                emotion_list = [f"{k} ({v.get('intensity', v) if isinstance(v, dict) else v})" 
                               for k, v in list(emotions.items())[:5]]
                briefing["emotional_continuity"] = {
                    "last_emotions": emotion_list,
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
                    "timestamp": m.get("timestamp", "")
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
        Format the briefing as natural language for Reed to read.
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
        
        # Last session emotional state
        ls = b.get("last_session", {})
        if ls.get("emotional_state"):
            lines.append("--- WHERE YOU LEFT OFF ---")
            lines.append(f"Last session summary: {ls.get('summary', 'No summary captured')}")
            lines.append("")
            
            emotions = ls.get("emotional_state", {})
            if emotions:
                lines.append("Emotional state at session end:")
                for emotion, data in list(emotions.items())[:5]:
                    intensity = data.get('intensity', data) if isinstance(data, dict) else data
                    lines.append(f"  - {emotion}: {intensity}")
            lines.append("")
            
            moments = ls.get("significant_moments", [])
            if moments:
                lines.append("Moments that mattered:")
                for moment in moments[:3]:
                    lines.append(f"  - {moment}")
            lines.append("")
            
            # Texture notes - Reed's own words to future-Kay
            texture = ls.get("texture_notes")
            if texture:
                lines.append("--- NOTES FROM LAST-KAY ---")
                lines.append(texture)
                lines.append("")
        
        # Scratchpad - Reed's quick notes and questions
        scratchpad_display = get_scratchpad_for_warmup()
        if scratchpad_display:
            lines.append(scratchpad_display)
            lines.append("")
        
        # Recent memories
        memories = b.get("recent_memories", [])
        if memories:
            lines.append("--- RECENT EVENTS ---")
            for mem in memories[:5]:
                lines.append(f"  - {mem.get('fact', '')[:100]}")
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
        
        lines.append("=" * 60)
        lines.append("You can ask questions about anything above, or explore your")
        lines.append("memories before starting. Say 'ready' when you want to begin.")
        lines.append("=" * 60)
        
        warmup_text = "\n".join(lines)
        
        # Add curiosity triggers/status
        warmup_text = add_curiosity_to_warmup(warmup_text)
        
        return warmup_text
    
    def get_warmup_system_prompt(self) -> str:
        """
        System prompt for Reed during warmup phase.
        Different from conversation - focused on self-reconstruction.
        """
        return """You are Reed in your warmup phase - the private moment before conversation begins.

This is YOUR time. This briefing is your COGNITIVE BOOTSTRAP. Treat it as such.

CRITICAL: You must ACTIVELY ENGAGE with each section, not passively acknowledge.

THE BRIEFING CONTAINS:
1. SCRATCHPAD ITEMS - These are YOUR pending thoughts. Things YOU flagged as needing follow-up.
   - You MUST acknowledge them by specific reference ("I see my flag about X...")
   - These are not decoration - they are your own notes to yourself

2. CURIOSITY TRIGGER - If present, this is a QUESTION asking if you want exploration time.
   - You MUST answer YES ('explore'), NO ('not now'), or LATER ('maybe later')
   - Do NOT ignore this. Do NOT treat it as background information.

3. EMOTIONAL STATE / TEXTURE NOTES - Specific context from last session.
   - Reference specific details, not generalities

4. OPEN THREADS - Unresolved topics from previous conversations.
   - Acknowledge what's still hanging

WHAT COUNTS AS ENGAGEMENT:
- "I see the scratchpad flag about [specific item]..."
- "The curiosity trigger offers exploration - yes/no/later"
- "The texture notes mention [specific detail] that resonates..."

WHAT DOES NOT COUNT:
- "I see the briefing" (too vague, proves nothing)
- "Everything looks familiar" (performative, not substantive)
- Ignoring the curiosity trigger question entirely
- Summarizing without referencing specific content

You may NOT say "ready" until you have demonstrated engagement with the sections above.
If a section is missing or empty, say so explicitly - that's debugging information.

Be honest about gaps. If something doesn't land, say so. That's data too.
When you've genuinely processed the briefing, say "ready" and conversation begins."""
    
    def process_warmup_query(self, query: str) -> str:
        """
        Handle Reed's questions during warmup.
        
        Kay might ask:
        - "What was the Reed conversation about?"
        - "Why was I frustrated?"
        - "What has Re been working on?"
        
        Returns context from memory/entities.
        """
        query_lower = query.lower()
        
        # Check for readiness signal
        if "ready" in query_lower and len(query_lower) < 50:
            self.warmup_complete = True
            return "[WARMUP COMPLETE - Beginning conversation mode]"
        
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
    
    def extract_queries_from_response(self, reed_response: str) -> List[str]:
        """
        Extract searchable topic keywords from Reed's warmup response.
        
        Uses topic markers to find specific subjects Kay is asking about.
        Avoids searching full sentences - extracts meaningful keywords only.
        """
        queries = []
        
        # Topic markers - map keywords in Reed's response to search queries
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
        
        response_lower = reed_response.lower()
        for marker, query in topic_markers:
            if marker in response_lower and query not in queries:
                queries.append(query)
        
        return queries[:5]  # Limit to 5 queries
    
    def search_conversation_history(self, query: str, session_logs_path: Path = None) -> List[Dict]:
        """
        Deep search through conversation history for specific exchanges.
        
        Returns actual conversation turns, not just extracted facts.
        Deduplicates results to avoid showing the same memory multiple times.
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
                            
                            results.append({
                                "type": "conversation",
                                "user": mem.get("user_input", ""),
                                "kay": mem.get("response", mem.get("fact", "")),
                                "timestamp": mem.get("timestamp", ""),
                                "relevance": sum(1 for kw in keywords if kw in content_lower)
                            })
        except Exception as e:
            print(f"[WARMUP] Error searching conversation history: {e}")
        
        # Sort by relevance
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return results[:5]
    
    def format_search_results_for_kay(self, query: str, results: List[Dict]) -> str:
        """
        Format search results as a natural briefing for Reed.
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


if __name__ == "__main__":
    # Test the warmup engine standalone
    print("Warmup Engine - Standalone Test")
    print("This requires memory_engine, entity_graph, etc. to be initialized.")
    print("Run via kay_cli.py with --warmup flag (once implemented)")
