# engines/room/action_parser.py
"""
Action Parser - Extracts spatial actions from LLM responses.

The LLM includes action tags in its response text:
    [ACTION: move_to couch]
    [ACTION: emote wave]
    [ACTION: interact fishtank]
    [ACTION: face left]

This parser:
1. Finds and extracts all action tags
2. Returns cleaned dialogue text (tags stripped)
3. Returns structured action list for RoomEngine.apply_actions()

The LLM doesn't need special training for this - the room context
prompt tells it the available actions and tag format.
"""

import re
from typing import List, Tuple, Dict

# Pattern matches [ACTION: command target] or [ACTION: command]
ACTION_PATTERN = re.compile(
    r'\[ACTION:\s*(\w+)(?:\s+(.+?))?\]',
    re.IGNORECASE
)

# Also catch more natural variants the LLM might produce
NATURAL_PATTERNS = [
    # *moves to the couch*
    re.compile(r'\*moves?\s+to\s+(?:the\s+)?(\w+)\*', re.IGNORECASE),
    # *walks over to the fishtank*
    re.compile(r'\*walks?\s+(?:over\s+)?to\s+(?:the\s+)?(\w+)\*', re.IGNORECASE),
    # *sits on the couch*
    re.compile(r'\*sits?\s+(?:on|at|in)\s+(?:the\s+)?(\w+)\*', re.IGNORECASE),
    # *drifts toward the center* / *moves to the gol*
    re.compile(r'\*(?:drifts?|moves?|walks?|approaches?)\s+(?:to(?:ward)?|toward)\s+(?:the\s+)?(center|gol)\*', re.IGNORECASE),
    # *heads north* / *moves east*
    re.compile(r'\*(?:heads?|moves?|drifts?|walks?)\s+(north|south|east|west|northeast|northwest|southeast|southwest)\*', re.IGNORECASE),
]

EMOTE_PATTERNS = [
    # *waves* or *smiles* or *laughs*
    re.compile(r'\*(\w+s)\*', re.IGNORECASE),
]


class ActionParser:
    """
    Parses LLM responses for spatial action tags.
    
    Usage:
        parser = ActionParser()
        actions, clean_text = parser.parse("Let me check the fish. [ACTION: move_to fishtank] They look hungry!")
        # actions = [{"action": "move_to", "target": "fishtank"}]
        # clean_text = "Let me check the fish. They look hungry!"
    """
    
    def __init__(self, known_objects: List[str] = None, 
                 known_entities: List[str] = None,
                 parse_natural: bool = True):
        """
        Args:
            known_objects: List of valid object IDs (for natural language matching)
            known_entities: List of valid entity IDs
            parse_natural: Whether to also parse *moves to X* style actions
        """
        self.known_objects = set(known_objects or [])
        self.known_entities = set(known_entities or [])
        self.parse_natural = parse_natural
    
    def update_known(self, objects: List[str] = None, entities: List[str] = None):
        """Update known objects/entities (call when room changes)."""
        if objects is not None:
            self.known_objects = set(objects)
        if entities is not None:
            self.known_entities = set(entities)
    
    def parse(self, response_text: str) -> Tuple[List[Dict], str]:
        """
        Parse a response for actions.
        
        Returns:
            (actions, clean_text) where:
            - actions: List of {"action": str, "target": str} dicts
            - clean_text: Response with action tags removed
        """
        actions = []
        clean = response_text
        
        # 1. Parse explicit [ACTION: ...] tags (highest priority)
        for match in ACTION_PATTERN.finditer(response_text):
            command = match.group(1).lower()
            target = (match.group(2) or "").strip().lower()
            
            # Normalize target - strip articles
            target = re.sub(r'^(the|a|an)\s+', '', target)
            # Try to match to known object/entity
            target = self._resolve_target(target)
            
            actions.append({
                "action": command,
                "target": target
            })
        
        # Remove explicit tags from text
        clean = ACTION_PATTERN.sub('', clean).strip()
        # Clean up double spaces left by removal
        clean = re.sub(r'  +', ' ', clean)
        clean = re.sub(r'\n\s*\n\s*\n', '\n\n', clean)
        
        # 2. Parse natural language movement (if enabled and no explicit actions found)
        if self.parse_natural and not actions:
            for pattern in NATURAL_PATTERNS:
                match = pattern.search(response_text)
                if match:
                    target = match.group(1).lower()
                    resolved = self._resolve_target(target)
                    if resolved in self.known_objects or resolved in self.known_entities:
                        actions.append({
                            "action": "move_to",
                            "target": resolved
                        })
                        break  # Only take first natural movement
        
        return actions, clean
    
    def _resolve_target(self, target: str) -> str:
        """
        Resolve a target string to a known object/entity ID.
        Handles fuzzy matching for natural language.
        """
        if not target:
            return target
        
        # Exact match
        if target in self.known_objects or target in self.known_entities:
            return target
        
        # Try without spaces/underscores
        normalized = target.replace(" ", "_").replace("-", "_")
        if normalized in self.known_objects or normalized in self.known_entities:
            return normalized
        
        # Try partial match (target contains or is contained in a known name)
        all_known = self.known_objects | self.known_entities
        for known in all_known:
            if target in known or known in target:
                return known
        
        # Try matching display names would go here if we had them
        # For now, return as-is and let RoomEngine handle unknown targets
        return target
    
    def format_action_hint(self) -> str:
        """
        Generate the instruction text telling the LLM how to use actions.
        Include in system prompt or room context.
        """
        return (
            "To perform spatial actions, include tags in your response:\n"
            "  [ACTION: move_to <target>]  - Move to an object, entity, cardinal direction, or 'center'/'gol'\n"
            "  [ACTION: emote <expression>] - Show an expression (wave, smile, think, etc.)\n"
            "  [ACTION: interact <object>]  - Interact with a nearby object\n"
            "  [ACTION: face <left/right>]  - Turn to face a direction\n"
            "  [ACTION: approach_gol]       - Move to the center axis\n"
            "Targets can be object names, entity names, or cardinal directions (north, east, south, west, etc.)\n"
            "You can include multiple actions. Actions happen alongside your dialogue.\n"
            "Example: 'The fish are doing their loops again. [ACTION: move_to fishtank] Mesmerizing.'"
        )
