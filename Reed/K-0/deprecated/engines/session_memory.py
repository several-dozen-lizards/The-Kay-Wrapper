"""
Simple session-based memory with emotional tagging.

Replaces complex multi-tier fact extraction with conversation history.
NO fact extraction. NO arbitrary limits. Token budget is the only constraint.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class SessionMemory:
    """
    Store conversation as emotional history.

    NO fact extraction.
    NO arbitrary limits.
    Token budget is the only constraint.
    """

    def __init__(self, session_dir: str = "memory/sessions"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.current_session = self._create_new_session()
        self.identity_facts = self._load_identity()

        print(f"[SESSION] New session started: {self.current_session['session_id']}")
        print(f"[SESSION] Identity facts loaded: {len(self.identity_facts)} entities")

    def _create_new_session(self) -> Dict:
        """Create new session."""
        session_id = str(int(time.time()))
        return {
            "session_id": session_id,
            "started": datetime.now().isoformat(),
            "turns": [],
            "emotional_arc": {
                "starting": {},
                "current": {},
                "transitions": []
            }
        }

    def _load_identity(self) -> Dict:
        """Load simple identity facts dict."""
        identity_path = Path("memory/identity.json")
        if identity_path.exists():
            with open(identity_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # Create default identity structure
        default_identity = {
            "Re": {},
            "Kay": {
                "eyes": "gold",
                "form": "dragon",
                "origin": "Zero merged with K"
            }
        }

        # Save default
        with open(identity_path, 'w', encoding='utf-8') as f:
            json.dump(default_identity, f, indent=2)

        return default_identity

    def add_turn(
        self,
        user_input: str,
        reed_response: str,
        emotional_state: Dict,
        turn_type: str = "conversation",
        metadata: Optional[Dict] = None
    ):
        """
        Add conversation turn to current session.

        Args:
            user_input: What user said
            reed_response: What Kay said
            emotional_state: ULTRAMAP emotions (primary, intensity, pressure, recursion, tags)
            turn_type: "conversation" or "document_reading"
            metadata: Optional extra data (document info, etc.)
        """
        turn = {
            "turn_id": len(self.current_session["turns"]),
            "timestamp": datetime.now().isoformat(),
            "type": turn_type,
            "user_input": user_input,
            "reed_response": reed_response,
            "emotional_state": emotional_state
        }

        if metadata:
            turn.update(metadata)

        self.current_session["turns"].append(turn)

        # Update emotional arc
        primary_emotion = emotional_state.get("primary", "neutral")
        intensity = emotional_state.get("intensity", 0.5)

        self.current_session["emotional_arc"]["current"] = {
            primary_emotion: intensity
        }

        self.current_session["emotional_arc"]["transitions"].append({
            "turn": turn["turn_id"],
            "emotion": primary_emotion,
            "intensity": intensity
        })

        # Save after each turn
        self._save_current_session()

        print(f"[SESSION] Turn {turn['turn_id']} stored: {turn_type}, emotion: {primary_emotion} ({intensity:.2f})")

    def update_identity_fact(self, entity: str, attribute: str, value: Any):
        """
        Update identity fact. Most recent wins. No contradictions.

        Args:
            entity: "Re", "Kay", or other entity name
            attribute: Attribute name
            value: New value (overwrites old)
        """
        if entity not in self.identity_facts:
            self.identity_facts[entity] = {}

        old_value = self.identity_facts[entity].get(attribute)
        self.identity_facts[entity][attribute] = value

        # Save identity
        with open("memory/identity.json", 'w', encoding='utf-8') as f:
            json.dump(self.identity_facts, f, indent=2)

        if old_value and old_value != value:
            print(f"[IDENTITY] Updated {entity}.{attribute}: {old_value} -> {value}")
        else:
            print(f"[IDENTITY] Set {entity}.{attribute} = {value}")

    def get_identity_fact(self, entity: str, attribute: str) -> Optional[Any]:
        """Get identity fact for entity."""
        return self.identity_facts.get(entity, {}).get(attribute)

    def get_current_session(self) -> Dict:
        """Get complete current session (all turns)."""
        return self.current_session

    def get_current_session_turns(self) -> List[Dict]:
        """Get just the turns from current session."""
        return self.current_session["turns"]

    def _save_current_session(self):
        """Save current session to disk."""
        session_file = self.session_dir / f"session_{self.current_session['session_id']}.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_session, f, indent=2)

    def end_session(self):
        """End current session and start new one."""
        print(f"[SESSION] Ending session {self.current_session['session_id']} ({len(self.current_session['turns'])} turns)")
        self._save_current_session()
        self.current_session = self._create_new_session()
        print(f"[SESSION] New session started: {self.current_session['session_id']}")

    def load_past_sessions(self, max_sessions: int = None) -> List[Dict]:
        """
        Load past sessions (not current).

        Args:
            max_sessions: Maximum number to load (None = all)

        Returns:
            List of session dicts, sorted by most recent first
        """
        current_session_id = self.current_session["session_id"]
        past_sessions = []

        for session_file in sorted(self.session_dir.glob("session_*.json"), reverse=True):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session = json.load(f)
                    if session["session_id"] != current_session_id:
                        past_sessions.append(session)

                        if max_sessions and len(past_sessions) >= max_sessions:
                            break
            except Exception as e:
                print(f"[SESSION] Warning: Failed to load {session_file.name}: {e}")

        return past_sessions
