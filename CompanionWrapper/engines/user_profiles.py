"""
User Profile System for the entity Zero

Allows the entity to interact with multiple users while maintaining correct
entity attribution, memory storage, and relationship tracking.

Each profile defines:
- Who "I/my/me" refers to in that user's messages
- Known attributes about that user
- Relationship to the entity
- Default perspective for fact extraction
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Default profiles directory
PROFILES_DIR = Path(__file__).parent.parent / "data" / "profiles"


class UserProfile:
    """Represents a single user's profile."""
    
    def __init__(self, profile_id: str, data: Dict[str, Any] = None):
        self.profile_id = profile_id
        data = data or {}
        
        # Core identity
        self.name = data.get("name", profile_id)
        self.canonical_name = data.get("canonical_name", profile_id.capitalize())
        self.aliases = data.get("aliases", [])
        
        # What type of entity is this user?
        # "human", "ai_sibling", "ai_external", "pet", etc.
        self.entity_type = data.get("entity_type", "human")
        
        # For fact extraction: what perspective does "I/my" map to?
        self.first_person_entity = data.get("first_person_entity", self.canonical_name)
        
        # Known attributes about this user
        self.attributes = data.get("attributes", {})
        
        # Relationship to the entity
        self.relationship_to_entity = data.get("relationship_to_entity", "user")
        
        # Mythological/roleplay form (optional)
        self.mythological_form = data.get("mythological_form", None)
        
        # Metadata
        self.created_at = data.get("created_at", datetime.now().isoformat())
        self.last_active = data.get("last_active", None)
        self.total_turns = data.get("total_turns", 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize profile to dictionary."""
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "canonical_name": self.canonical_name,
            "aliases": self.aliases,
            "entity_type": self.entity_type,
            "first_person_entity": self.first_person_entity,
            "attributes": self.attributes,
            "relationship_to_entity": self.relationship_to_entity,
            "mythological_form": self.mythological_form,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "total_turns": self.total_turns
        }
    
    def update_activity(self):
        """Update last active timestamp and increment turn count."""
        self.last_active = datetime.now().isoformat()
        self.total_turns += 1
    
    def set_attribute(self, key: str, value: Any):
        """Set a known attribute about this user."""
        self.attributes[key] = value
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get a known attribute about this user."""
        return self.attributes.get(key, default)


class ProfileManager:
    """Manages user profiles for the entity."""
    
    def __init__(self, profiles_dir: Path = None):
        self.profiles_dir = profiles_dir or PROFILES_DIR
        self.profiles: Dict[str, UserProfile] = {}
        self.active_profile_id: Optional[str] = None
        
        # Ensure profiles directory exists
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing profiles
        self._load_profiles()
        
        # Create default profiles if none exist
        if not self.profiles:
            self._create_default_profiles()
    
    def _load_profiles(self):
        """Load all profiles from disk."""
        profiles_file = self.profiles_dir / "profiles.json"
        
        if profiles_file.exists():
            try:
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for profile_id, profile_data in data.items():
                        self.profiles[profile_id] = UserProfile(profile_id, profile_data)
                print(f"[PROFILES] Loaded {len(self.profiles)} user profiles")
            except Exception as e:
                print(f"[PROFILES] Error loading profiles: {e}")
    
    def _save_profiles(self):
        """Save all profiles to disk."""
        profiles_file = self.profiles_dir / "profiles.json"
        
        try:
            data = {pid: p.to_dict() for pid, p in self.profiles.items()}
            with open(profiles_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[PROFILES] Error saving profiles: {e}")
    
    def _create_default_profiles(self):
        """Create the default user profiles from persona config."""

        # Load persona to get user name dynamically
        try:
            from persona_loader import persona
            user_name = persona.user_name if persona else "User"
            entity_name = persona.name if persona else "Companion"
        except ImportError:
            user_name = "User"
            entity_name = "Companion"

        # Primary human user - name comes from persona
        user_id = user_name.lower()
        self.create_profile(user_id, {
            "name": user_name,
            "canonical_name": user_name,
            "aliases": [user_name, user_name.lower()],
            "entity_type": "human",
            "first_person_entity": user_name,
            "relationship_to_entity": "creator",
            "attributes": {}  # Attributes come from memory system, not hardcoded
        })

        print(f"[PROFILES] Created {len(self.profiles)} default profiles (user: {user_name})")
        self._save_profiles()
    
    def create_profile(self, profile_id: str, data: Dict[str, Any] = None) -> UserProfile:
        """Create a new user profile."""
        profile = UserProfile(profile_id, data)
        self.profiles[profile_id] = profile
        self._save_profiles()
        print(f"[PROFILES] Created profile: {profile.canonical_name}")
        return profile
    
    def get_profile(self, profile_id: str) -> Optional[UserProfile]:
        """Get a profile by ID."""
        return self.profiles.get(profile_id.lower())
    
    def set_active_profile(self, profile_id: str) -> bool:
        """Set the active profile for the current session."""
        profile_id = profile_id.lower()
        if profile_id in self.profiles:
            self.active_profile_id = profile_id
            print(f"[PROFILES] Active profile: {self.profiles[profile_id].canonical_name}")
            return True
        else:
            print(f"[PROFILES] Unknown profile: {profile_id}")
            return False
    
    def get_active_profile(self) -> Optional[UserProfile]:
        """Get the currently active profile."""
        if self.active_profile_id:
            return self.profiles.get(self.active_profile_id)
        # Default to first available profile if no profile set
        if self.profiles:
            return next(iter(self.profiles.values()))
        return None

    def get_first_person_entity(self) -> str:
        """Get the entity name that 'I/my/me' should map to."""
        profile = self.get_active_profile()
        if profile:
            return profile.first_person_entity
        # Dynamic fallback from persona
        try:
            from persona_loader import persona
            return persona.user_name if persona else "User"
        except ImportError:
            return "User"
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all available profiles."""
        return [
            {
                "id": pid,
                "name": p.canonical_name,
                "type": p.entity_type,
                "relationship": p.relationship_to_entity,
                "last_active": p.last_active,
                "total_turns": p.total_turns
            }
            for pid, p in self.profiles.items()
        ]
    
    def update_profile(self, profile_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing profile."""
        profile = self.get_profile(profile_id)
        if not profile:
            return False
        
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
            else:
                profile.attributes[key] = value
        
        self._save_profiles()
        return True
    
    def record_turn(self, profile_id: str = None):
        """Record that a turn happened for a profile."""
        pid = profile_id or self.active_profile_id
        if pid and pid in self.profiles:
            self.profiles[pid].update_activity()
            self._save_profiles()


# Global instance (lazy loaded)
_profile_manager: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Get the global profile manager instance."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager


def get_active_speaker() -> str:
    """Get the canonical name of the active speaker (for entity attribution)."""
    return get_profile_manager().get_first_person_entity()


def set_active_profile(profile_id: str) -> bool:
    """Convenience function to set active profile."""
    return get_profile_manager().set_active_profile(profile_id)


# CLI helper for listing profiles
if __name__ == "__main__":
    import sys
    
    pm = get_profile_manager()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "list":
            print("\nAvailable profiles:")
            for p in pm.list_profiles():
                active = " (active)" if p["id"] == pm.active_profile_id else ""
                print(f"  {p['id']}: {p['name']} [{p['type']}] - {p['relationship']}{active}")
        
        elif cmd == "show" and len(sys.argv) > 2:
            profile = pm.get_profile(sys.argv[2])
            if profile:
                print(f"\nProfile: {profile.canonical_name}")
                print(json.dumps(profile.to_dict(), indent=2))
            else:
                print(f"Unknown profile: {sys.argv[2]}")
        
        elif cmd == "create" and len(sys.argv) > 2:
            profile_id = sys.argv[2]
            pm.create_profile(profile_id, {"name": profile_id.capitalize()})
            print(f"Created profile: {profile_id}")
        
        else:
            print("Usage: python user_profiles.py [list|show <id>|create <id>]")
    else:
        print("the entity User Profile System")
        print("Usage: python user_profiles.py [list|show <id>|create <id>]")
