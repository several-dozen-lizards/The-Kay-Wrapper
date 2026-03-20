# shared/room/room_bridge.py
"""
Room Bridge - Connects the room engine to the wrapper's message pipeline
and broadcasts state updates via the PrivateRoom WebSocket.

This is the integration layer. It:
1. Injects room state into the LLM system prompt
2. Parses [ACTION:] tags from the LLM response
3. Broadcasts updated room state via WebSocket to Godot

Usage in a wrapper's main_bridge.py or equivalent:

    from shared.room.room_bridge import RoomBridge
    from shared.room.presets import create_the_den
    
    room = create_the_den()
    bridge = RoomBridge(room, entity_id="kay", private_room=my_private_room)
    
    # In your message pipeline:
    system_prompt = bridge.inject_room_context(system_prompt)
    # ... LLM call ...
    clean_text, actions = bridge.process_response(raw_response)
    await bridge.broadcast_state()  # Push to Godot
"""

import json
import os
import asyncio
from typing import Tuple, List, Optional
from shared.room.room_engine import RoomEngine
from shared.room.action_parser import ActionParser


class RoomBridge:
    """
    Bridges the room engine to a wrapper's LLM pipeline and WebSocket output.
    """
    
    def __init__(self, room: RoomEngine, entity_id: str, private_room=None):
        """
        Args:
            room: The RoomEngine instance (shared across entities if in same room)
            entity_id: Which entity this wrapper controls ("kay" or "reed")
            private_room: The PrivateRoom WebSocket server instance (for broadcasting)
        """
        self.room = room
        self.entity_id = entity_id
        self.private_room = private_room
        self.parser = ActionParser(
            known_objects=list(room.objects.keys()),
            known_entities=list(room.entities.keys())
        )
        self.enabled = True
        self.last_actions = []
    
    def inject_room_context(self, system_prompt: str) -> str:
        """
        Add room state to the system prompt before sending to LLM.
        Call this right before your LLM API call.
        """
        if not self.enabled:
            return system_prompt
        
        # Refresh known targets
        self.parser.update_known(
            objects=list(self.room.objects.keys()),
            entities=list(self.room.entities.keys())
        )
        
        room_context = self.room.get_context_for(self.entity_id)
        if not room_context:
            return system_prompt
        
        room_block = (
            "\n\n--- SPATIAL EMBODIMENT ---\n"
            f"{room_context}\n"
            f"{self.parser.format_action_hint()}\n"
            "--- END SPATIAL ---\n"
        )
        
        return system_prompt + room_block
    
    def _inject_cross_entities(self):
        """Read other entities' positions from resonance broadcast files.
        
        Each entity broadcasts its oscillator state + position to
        D:\\Wrappers\\shared\\resonance_{entity}.json. We read those files
        to show ALL entities in the same room view, not just our own.
        """
        import time
        # D:\Wrappers\shared\room\room_bridge.py -> D:\Wrappers\shared
        RESONANCE_DIR = os.path.normpath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        )
        
        ENTITY_CONFIGS = {
            "kay": {"display_name": "Kay", "color": "#2D1B4E"},
            "reed": {"display_name": "Reed", "color": "#00CED1"},
        }
        MAX_AGE = 120.0
        
        for eid, cfg in ENTITY_CONFIGS.items():
            if eid == self.entity_id:
                continue
            
            res_file = os.path.join(RESONANCE_DIR, f"resonance_{eid}.json")
            try:
                with open(res_file, 'r') as f:
                    data = json.load(f)
                
                age = time.time() - data.get("timestamp", 0)
                if age > MAX_AGE:
                    if eid in self.room.entities:
                        self.room.remove_entity(eid)
                    continue
                
                x = data.get("x", 0)
                y = data.get("y", 0)
                
                if eid in self.room.entities:
                    ent = self.room.entities[eid]
                    ent.x = x
                    ent.y = y
                else:
                    self.room.add_entity(
                        eid, cfg["display_name"],
                        x=x, y=y,
                        color=cfg["color"],
                    )
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                pass
    
    def process_response(self, response_text: str) -> Tuple[str, List[str]]:
        """
        Process LLM response: extract [ACTION:] tags, apply to room, return clean text.
        Call this after receiving the LLM response.
        
        Returns:
            (clean_text, action_results)
        """
        if not self.enabled:
            return response_text, []
        
        actions, clean_text = self.parser.parse(response_text)
        
        results = []
        if actions:
            results = self.room.apply_actions(self.entity_id, actions)
        
        self.last_actions = actions
        return clean_text, results
    
    async def broadcast_state(self):
        """
        Send current room state to Godot via the private room WebSocket.
        Call this after process_response().
        """
        if not self.private_room or not self.enabled:
            return

        # Check if client is connected
        if not self.private_room.has_client:
            # Log occasionally to help debug connection issues
            if not hasattr(self, '_no_client_warn_count'):
                self._no_client_warn_count = 0
            self._no_client_warn_count += 1
            if self._no_client_warn_count <= 3:
                print(f"[ROOM] No UI client connected (warn {self._no_client_warn_count}/3)")
            return

        # Inject other entities from their resonance broadcast files
        self._inject_cross_entities()

        state = self.room.get_full_state()

        # Get entity position for logging
        entity_data = state.get("entities", {}).get(self.entity_id, {})
        if entity_data:
            sx = entity_data.get("screen_x", "?")
            sy = entity_data.get("screen_y", "?")
            print(f"[ROOM] → Godot: {self.entity_id} at ({sx}, {sy})")

        await self.private_room._send({
            "type": "room_update",
            "state": state
        })
    
    async def broadcast_action_feedback(self, results: List[str]):
        """
        Optionally send action results as a system message so the UI can show them.
        """
        if not self.private_room or not results:
            return
        
        feedback = " • ".join(results)
        await self.private_room.send_system(f"🏠 {feedback}")
    
    def toggle(self, enabled: bool = None) -> bool:
        """Enable/disable the room system."""
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = not self.enabled
        return self.enabled
