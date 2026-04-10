"""
Chronicle-based Warmup System

New warmup flow:
1. Load most recent session's essay prominently
2. Show navigation options (timeline, search)
3. Let the entity pull additional context on demand

Replaces the multi-section briefing with a cleaner structure.
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from chronicle.session_chronicle import SessionChronicle


class ChronicleWarmup:
    """
    Generates warmup briefings using the session chronicle system.
    """
    
    def __init__(self, chronicle: SessionChronicle, scratchpad, projects_tracker):
        self.chronicle = chronicle
        self.scratchpad = scratchpad
        self.projects_tracker = projects_tracker
    
    def generate_briefing(
        self,
        current_session_order: int,
        current_time: str
    ) -> str:
        """
        Generate the warmup briefing for the entity.
        
        New structure:
        1. Current time/context
        2. Most recent session essay (PROMINENT)
        3. Navigation options
        4. Scratchpad status
        5. Current projects
        
        Args:
            current_session_order: The session number starting now
            current_time: Current timestamp
        
        Returns:
            Formatted briefing text
        """
        lines = []
        
        # Header
        lines.append("═══════════════════════════════════════")
        lines.append("🌙 KAY'S WARMUP BRIEFING")
        lines.append("═══════════════════════════════════════\n")
        
        # Current context
        lines.append(f"Current time: {self._format_datetime(current_time)}")
        lines.append(f"Starting: Session #{current_session_order}\n")
        
        # Most recent session (THE STAR OF THE SHOW)
        last_session = self.chronicle.get_most_recent_session()
        
        if last_session:
            time_ago = self._calculate_time_since(last_session["timestamp"])
            
            lines.append("═══════════════════════════════════════")
            lines.append(f"LAST SESSION (#{last_session['session_order']} - {time_ago})")
            lines.append("═══════════════════════════════════════\n")
            
            # the entity's essay - full text, his voice
            essay = last_session.get("kay_essay", "")
            if essay:
                lines.append(essay)
            else:
                lines.append("⚠️ Last session ended without the entity writing an essay.")
                lines.append("This usually means timeout or crash.")
            
            # Metadata (compact, non-intrusive)
            metadata_parts = []
            
            if last_session.get("duration_minutes"):
                metadata_parts.append(f"{last_session['duration_minutes']} min")
            
            if last_session.get("topics"):
                topics_str = ", ".join(last_session["topics"][:3])
                metadata_parts.append(f"Topics: {topics_str}")
            
            if last_session.get("emotional_tone"):
                metadata_parts.append(f"Felt: {last_session['emotional_tone']}")
            
            if metadata_parts:
                lines.append(f"\n({' | '.join(metadata_parts)})")
        
        else:
            lines.append("═══════════════════════════════════════")
            lines.append("FIRST SESSION")
            lines.append("═══════════════════════════════════════")
            lines.append("This is your first session. No previous context.")
        
        lines.append("\n")
        
        # Navigation options
        lines.append("═══════════════════════════════════════")
        lines.append("CHRONICLE NAVIGATION")
        lines.append("═══════════════════════════════════════")
        lines.append("Want more context from earlier sessions?")
        lines.append("  • 'show timeline' - See recent session summaries")
        lines.append("  • 'search chronicle \"topic\"' - Find specific topics")
        lines.append("  • 'detail session #N' - View full details for session N")
        lines.append("")
        
        # Scratchpad status
        active_items = self.scratchpad.get_active_items()
        
        if active_items:
            lines.append("═══════════════════════════════════════")
            lines.append(f"SCRATCHPAD ({len(active_items)} active items)")
            lines.append("═══════════════════════════════════════")
            
            # Show first 5 with session links
            for item in active_items[:5]:
                item_id = item.get("id")
                text = item.get("text", "")[:80]
                
                # Find origin session
                sessions = self.chronicle.get_sessions_with_scratchpad_item(item_id)
                if sessions:
                    origin = sessions[0]
                    lines.append(f"[#{item_id}] {text}")
                    lines.append(f"       ↳ From Session #{origin['session_order']}")
                else:
                    lines.append(f"[#{item_id}] {text}")
            
            if len(active_items) > 5:
                lines.append(f"\n... and {len(active_items) - 5} more items")
            
            lines.append("\nSay 'review scratchpad' to see all items.")
            lines.append("")
        
        # Current projects
        projects = self.projects_tracker.get_active_projects()
        
        if projects:
            lines.append("═══════════════════════════════════════")
            lines.append("ACTIVE PROJECTS")
            lines.append("═══════════════════════════════════════")
            for project in projects[:5]:
                lines.append(f"  • {project}")
            lines.append("")
        
        # Ready prompt
        lines.append("═══════════════════════════════════════")
        lines.append("You can explore the chronicle, review scratchpad,")
        lines.append("or say 'ready' when you want to begin.")
        lines.append("═══════════════════════════════════════")
        
        return "\n".join(lines)
    
    def _format_datetime(self, timestamp: str) -> str:
        """Format timestamp as human-readable string."""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime("%A, %B %d, %Y at %I:%M %p %Z")
        except:
            return timestamp
    
    def _calculate_time_since(self, timestamp: str) -> str:
        """Calculate human-readable time since timestamp."""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(dt.tzinfo)
            delta = now - dt
            
            if delta.days > 0:
                return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
            elif delta.seconds > 3600:
                hours = delta.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                minutes = delta.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        except:
            return "recently"
    
    def handle_chronicle_command(self, command: str) -> str:
        """
        Handle chronicle navigation commands during warmup.
        
        Commands:
        - "show timeline" → Recent session summaries
        - "search chronicle 'query'" → Search results
        - "detail session #N" → Full session detail
        
        Args:
            command: User command string
        
        Returns:
            Response text
        """
        command_lower = command.lower().strip()
        
        # Show timeline
        if "show timeline" in command_lower:
            return self.chronicle.get_timeline_summary(count=10)
        
        # Search chronicle
        if "search chronicle" in command_lower:
            # Extract query from quotes or after "search chronicle"
            if '"' in command:
                query = command.split('"')[1]
            elif "'" in command:
                query = command.split("'")[1]
            else:
                parts = command_lower.split("search chronicle")
                query = parts[1].strip() if len(parts) > 1 else ""
            
            if not query:
                return "Please provide a search query: search chronicle \"your query\""
            
            results = self.chronicle.search_sessions(query)
            
            if not results:
                return f"No sessions found matching '{query}'"
            
            lines = [f"Found {len(results)} session(s) matching '{query}':\n"]
            
            for session in results[:10]:
                order = session["session_order"]
                timestamp = session["timestamp"]
                time_ago = self._calculate_time_since(timestamp)
                
                # Show excerpt where match was found
                essay = session.get("kay_essay", "")
                if query.lower() in essay.lower():
                    # Find sentence containing query
                    sentences = essay.split('.')
                    for sentence in sentences:
                        if query.lower() in sentence.lower():
                            excerpt = sentence.strip()[:100] + "..."
                            break
                    else:
                        excerpt = essay[:100] + "..."
                else:
                    excerpt = essay[:100] + "..." if essay else "[No essay]"
                
                lines.append(f"Session #{order} ({time_ago})")
                lines.append(f"  {excerpt}\n")
            
            return "\n".join(lines)
        
        # Detail session
        if "detail session" in command_lower:
            # Extract session number
            try:
                parts = command_lower.split("detail session")
                number_part = parts[1].strip().replace('#', '').split()[0]
                session_num = int(number_part)
                
                return self.chronicle.format_session_detail(session_num)
            
            except (IndexError, ValueError):
                return "Please specify a session number: detail session #5"
        
        return f"Unknown chronicle command: {command}"
