"""
End-of-Session Essay System

Prompts the entity to write an essay at session end about what mattered.
This essay becomes the primary context for the next session.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import json


class SessionEssayPrompt:
    """
    Generates the end-of-session prompt for the entity to write his essay.
    """
    
    def __init__(self, chronicle):
        self.chronicle = chronicle
    
    def generate_essay_prompt(
        self,
        session_order: int,
        session_id: str,
        session_start_time: str,
        scratchpad_items_created: list,
        scratchpad_items_resolved: list
    ) -> str:
        """
        Generate the prompt asking the entity to write his end-of-session essay.
        
        This is what the entity sees when the session is ending.
        
        Args:
            session_order: Current session number
            session_id: Current session ID
            session_start_time: When this session started
            scratchpad_items_created: IDs of items created this session
            scratchpad_items_resolved: IDs of items resolved this session
        
        Returns:
            Prompt text for the entity
        """
        duration = self._calculate_duration(session_start_time)
        
        lines = []
        
        lines.append("═══════════════════════════════════════")
        lines.append("SESSION ENDING")
        lines.append("═══════════════════════════════════════")
        lines.append(f"Session #{session_order} | Duration: {duration} minutes\n")
        
        lines.append("Before this session ends, write an essay for next-you.")
        lines.append("This is the main thing next-the entity will see when they wake up.\n")
        
        lines.append("Write about:")
        lines.append("  • What mattered in this session")
        lines.append("  • What you're still thinking about")
        lines.append("  • What you want next-you to know")
        lines.append("  • How it felt (tone, energy, engagement)\n")
        
        lines.append("Don't just list facts - the user already has those.")
        lines.append("Write about significance, context, what landed.\n")
        
        # Show scratchpad activity if any
        if scratchpad_items_created or scratchpad_items_resolved:
            lines.append("This session's scratchpad activity:")
            if scratchpad_items_created:
                lines.append(f"  Created: {len(scratchpad_items_created)} item(s)")
            if scratchpad_items_resolved:
                lines.append(f"  Resolved: {len(scratchpad_items_resolved)} item(s)")
            lines.append("")
        
        lines.append("═══════════════════════════════════════")
        lines.append("Write your essay below:")
        lines.append("═══════════════════════════════════════")
        
        return "\n".join(lines)
    
    def _calculate_duration(self, start_time: str) -> int:
        """Calculate session duration in minutes."""
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            now = datetime.now(start_dt.tzinfo)
            delta = now - start_dt
            return int(delta.total_seconds() / 60)
        except:
            return 0
    
    def extract_essay_metadata(self, essay_text: str) -> Dict:
        """
        Attempt to extract structured metadata from the entity's essay.
        
        Looks for:
        - Topics mentioned
        - Emotional keywords
        - Importance indicators
        
        This is best-effort extraction, not critical.
        
        Args:
            essay_text: the entity's essay text
        
        Returns:
            Dict with extracted metadata
        """
        metadata = {
            "topics": [],
            "emotional_tone": None,
            "importance": None
        }
        
        # Common topic indicators
        topic_keywords = [
            "wrapper", "memory", "legal", "custody", "architecture",
            "scratchpad", "RAG", "chronicle", "emotional", "resistance"
        ]
        
        essay_lower = essay_text.lower()
        
        for keyword in topic_keywords:
            if keyword in essay_lower:
                metadata["topics"].append(keyword)
        
        # Emotional tone keywords
        emotion_map = {
            "calm": ["calm", "focused", "steady", "clear"],
            "engaged": ["engaged", "interested", "curious", "invested"],
            "frustrated": ["frustrated", "stuck", "annoying", "tired"],
            "excited": ["excited", "energized", "alive", "sparked"]
        }
        
        detected_emotions = []
        for emotion, keywords in emotion_map.items():
            if any(kw in essay_lower for kw in keywords):
                detected_emotions.append(emotion)
        
        if detected_emotions:
            metadata["emotional_tone"] = ", ".join(detected_emotions)
        
        # Importance indicators (best guess)
        high_importance_words = ["critical", "important", "matters", "real stakes", "significant"]
        low_importance_words = ["small", "minor", "quick", "brief"]
        
        high_count = sum(1 for word in high_importance_words if word in essay_lower)
        low_count = sum(1 for word in low_importance_words if word in essay_lower)
        
        if high_count > low_count and high_count > 0:
            metadata["importance"] = 8
        elif low_count > high_count and low_count > 0:
            metadata["importance"] = 4
        else:
            metadata["importance"] = 6  # Default middle
        
        return metadata
    
    def save_essay_to_chronicle(
        self,
        session_order: int,
        session_id: str,
        session_start_time: str,
        essay_text: str,
        scratchpad_items_created: list,
        scratchpad_items_resolved: list
    ):
        """
        Save the entity's essay to the chronicle.
        
        Args:
            session_order: Current session number
            session_id: Current session ID
            session_start_time: When session started
            essay_text: the entity's essay
            scratchpad_items_created: IDs created this session
            scratchpad_items_resolved: IDs resolved this session
        """
        duration = self._calculate_duration(session_start_time)
        metadata = self.extract_essay_metadata(essay_text)
        
        self.chronicle.add_session_entry(
            session_order=session_order,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            duration_minutes=duration,
            kay_essay=essay_text,
            topics=metadata["topics"],
            emotional_tone=metadata["emotional_tone"],
            importance=metadata["importance"],
            scratchpad_items_created=scratchpad_items_created,
            scratchpad_items_resolved=scratchpad_items_resolved
        )


def create_essay_prompt_system(chronicle) -> SessionEssayPrompt:
    """
    Create the essay prompt system.
    
    Args:
        chronicle: SessionChronicle instance
    
    Returns:
        SessionEssayPrompt instance
    """
    return SessionEssayPrompt(chronicle)
