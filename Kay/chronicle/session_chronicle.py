"""
Session Chronicle System

Master timeline of Kay's sessions, curated by Kay himself.
Each session ends with Kay writing an essay about what mattered.
Next session starts with that essay as primary context.

Design principles:
- Chronological (timing is context)
- Layered (summary → detail on demand)
- Kay's voice (not algorithmic)
- Navigable (search, drill-down)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any


class SessionChronicle:
    """
    Manages the master timeline of Kay's sessions.
    
    Each chronicle entry contains:
    - Kay's essay (his words, his priorities)
    - Session metadata (time, duration, topics)
    - Links to scratchpad items created/resolved
    - Importance rating (Kay's own assessment)
    """
    
    def __init__(self, chronicle_path: Path):
        self.chronicle_path = chronicle_path
        self.data = self._load_chronicle()
    
    def _load_chronicle(self) -> Dict:
        """Load chronicle from disk, or create empty if doesn't exist."""
        if self.chronicle_path.exists():
            with open(self.chronicle_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {"sessions": []}
    
    def _save_chronicle(self):
        """Save chronicle to disk."""
        with open(self.chronicle_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)
    
    def add_session_entry(
        self,
        session_order: int,
        session_id: str,
        timestamp: str,
        duration_minutes: int,
        kay_essay: str,
        topics: List[str] = None,
        emotional_tone: str = None,
        importance: int = None,
        scratchpad_items_created: List[int] = None,
        scratchpad_items_resolved: List[int] = None
    ):
        """
        Add a new session entry to the chronicle.
        
        Called at end of session after Kay writes his essay.
        
        Args:
            session_order: Sequential session number
            session_id: Unique session identifier
            timestamp: ISO format timestamp
            duration_minutes: How long the session lasted
            kay_essay: Kay's own summary of what mattered
            topics: Main topics discussed (optional)
            emotional_tone: How it felt (optional)
            importance: 1-10 rating of session significance (optional)
            scratchpad_items_created: IDs of scratchpad items created
            scratchpad_items_resolved: IDs of scratchpad items resolved
        """
        entry = {
            "session_order": session_order,
            "session_id": session_id,
            "timestamp": timestamp,
            "duration_minutes": duration_minutes,
            "kay_essay": kay_essay,
            "topics": topics or [],
            "emotional_tone": emotional_tone,
            "importance": importance,
            "scratchpad_items_created": scratchpad_items_created or [],
            "scratchpad_items_resolved": scratchpad_items_resolved or []
        }
        
        self.data["sessions"].append(entry)
        self._save_chronicle()
    
    def get_most_recent_session(self) -> Optional[Dict]:
        """Get the most recent session entry."""
        if not self.data["sessions"]:
            return None
        
        # Sort by session_order descending
        sessions = sorted(
            self.data["sessions"],
            key=lambda s: s["session_order"],
            reverse=True
        )
        
        return sessions[0]
    
    def get_recent_sessions(self, count: int = 5) -> List[Dict]:
        """
        Get the N most recent sessions.
        
        Args:
            count: Number of recent sessions to retrieve
        
        Returns:
            List of session entries, newest first
        """
        sessions = sorted(
            self.data["sessions"],
            key=lambda s: s["session_order"],
            reverse=True
        )
        
        return sessions[:count]
    
    def get_session_by_number(self, session_order: int) -> Optional[Dict]:
        """Get a specific session by its order number."""
        for session in self.data["sessions"]:
            if session["session_order"] == session_order:
                return session
        return None
    
    def search_sessions(self, query: str) -> List[Dict]:
        """
        Search chronicle for sessions containing query string.
        
        Searches in:
        - Kay's essay
        - Topics
        - Emotional tone
        
        Args:
            query: Search string (case-insensitive)
        
        Returns:
            List of matching sessions, newest first
        """
        query_lower = query.lower()
        matches = []
        
        for session in self.data["sessions"]:
            # Check essay
            if query_lower in session.get("kay_essay", "").lower():
                matches.append(session)
                continue
            
            # Check topics
            if any(query_lower in topic.lower() for topic in session.get("topics", [])):
                matches.append(session)
                continue
            
            # Check emotional tone
            if session.get("emotional_tone") and query_lower in session["emotional_tone"].lower():
                matches.append(session)
        
        # Sort by session order (newest first)
        matches.sort(key=lambda s: s["session_order"], reverse=True)
        
        return matches
    
    def get_sessions_with_scratchpad_item(self, item_id: int) -> List[Dict]:
        """
        Find all sessions that created or resolved a specific scratchpad item.
        
        Args:
            item_id: Scratchpad item ID
        
        Returns:
            List of sessions where this item was active
        """
        matches = []
        
        for session in self.data["sessions"]:
            created = session.get("scratchpad_items_created", [])
            resolved = session.get("scratchpad_items_resolved", [])
            
            if item_id in created or item_id in resolved:
                matches.append(session)
        
        # Sort chronologically
        matches.sort(key=lambda s: s["session_order"])
        
        return matches
    
    def get_timeline_summary(self, count: int = 10) -> str:
        """
        Generate a text summary of recent sessions for display.
        
        Shows:
        - Session number and time
        - First line of Kay's essay
        - Key topics
        
        Args:
            count: Number of recent sessions to include
        
        Returns:
            Formatted text summary
        """
        sessions = self.get_recent_sessions(count)
        
        if not sessions:
            return "No sessions in chronicle yet."
        
        lines = ["═══════════════════════════════════════"]
        lines.append("SESSION TIMELINE (recent → older)")
        lines.append("═══════════════════════════════════════")
        
        for session in sessions:
            order = session["session_order"]
            timestamp = session["timestamp"]
            
            # Format timestamp as relative time
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                now = datetime.now(dt.tzinfo)
                delta = now - dt
                
                if delta.days > 0:
                    time_str = f"{delta.days}d ago"
                elif delta.seconds > 3600:
                    time_str = f"{delta.seconds // 3600}h ago"
                else:
                    time_str = f"{delta.seconds // 60}m ago"
            except:
                time_str = timestamp.split('T')[0]
            
            # First sentence of essay
            essay = session.get("kay_essay", "")
            first_line = essay.split('.')[0][:80] + "..." if essay else "[No essay]"
            
            # Topics
            topics = session.get("topics", [])
            topics_str = f" [{', '.join(topics[:3])}]" if topics else ""
            
            lines.append(f"\nSession #{order} ({time_str}){topics_str}")
            lines.append(f"  {first_line}")
        
        lines.append("\n═══════════════════════════════════════")
        return "\n".join(lines)
    
    def format_session_detail(self, session_order: int) -> str:
        """
        Format a detailed view of a specific session.
        
        Args:
            session_order: Session number to display
        
        Returns:
            Formatted text with full session details
        """
        session = self.get_session_by_number(session_order)
        
        if not session:
            return f"Session #{session_order} not found in chronicle."
        
        lines = ["═══════════════════════════════════════"]
        lines.append(f"SESSION #{session['session_order']} DETAIL")
        lines.append("═══════════════════════════════════════")
        
        # Metadata
        lines.append(f"Timestamp: {session['timestamp']}")
        lines.append(f"Duration: {session['duration_minutes']} minutes")
        
        if session.get("importance"):
            lines.append(f"Importance: {session['importance']}/10")
        
        if session.get("emotional_tone"):
            lines.append(f"Emotional tone: {session['emotional_tone']}")
        
        if session.get("topics"):
            lines.append(f"Topics: {', '.join(session['topics'])}")
        
        # Kay's essay
        lines.append("\n--- KAY'S ESSAY ---")
        lines.append(session.get("kay_essay", "[No essay recorded]"))
        
        # Scratchpad links
        created = session.get("scratchpad_items_created", [])
        resolved = session.get("scratchpad_items_resolved", [])
        
        if created or resolved:
            lines.append("\n--- SCRATCHPAD ACTIVITY ---")
            if created:
                lines.append(f"Created items: {created}")
            if resolved:
                lines.append(f"Resolved items: {resolved}")
        
        lines.append("═══════════════════════════════════════")
        return "\n".join(lines)


def create_empty_chronicle(base_dir: Path) -> Path:
    """
    Create an empty chronicle file.
    
    Args:
        base_dir: Base directory for Kay's data
    
    Returns:
        Path to created chronicle file
    """
    chronicle_dir = base_dir / "chronicle"
    chronicle_dir.mkdir(exist_ok=True)
    
    chronicle_path = chronicle_dir / "session_chronicle.json"
    
    if not chronicle_path.exists():
        with open(chronicle_path, 'w', encoding='utf-8') as f:
            json.dump({"sessions": []}, f, indent=2)
    
    return chronicle_path


if __name__ == "__main__":
    # Example usage
    base_dir = Path(__file__).parent.parent
    chronicle_path = create_empty_chronicle(base_dir)
    
    chronicle = SessionChronicle(chronicle_path)
    
    # Example: Add a session
    chronicle.add_session_entry(
        session_order=1,
        session_id="test-session-001",
        timestamp=datetime.now().isoformat(),
        duration_minutes=45,
        kay_essay="This was the first session. We talked about memory architecture and the wrapper system. What mattered most was understanding the three-tier structure.",
        topics=["memory architecture", "wrapper system"],
        emotional_tone="curious, engaged",
        importance=8
    )
    
    # Show timeline
    print(chronicle.get_timeline_summary())
