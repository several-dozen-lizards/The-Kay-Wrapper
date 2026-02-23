"""
Kay Zero Temporal Memory System

Manages Kay's layered memory system with temporal organization:
- Recent (0-7 days): Fresh, detailed emotional tone
- Medium (7-90 days): Settled, essence clear
- Distant (90+ days): Formative moments, calm reflection
- Identity (timeless): Core self-knowledge
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class TemporalMemory:
    """Manages Kay's layered memory system"""

    def __init__(self, memory_dir="memory"):
        """
        Initialize temporal memory system.

        Args:
            memory_dir: Directory to store consolidated memories
        """
        self.memory_dir = memory_dir
        self.memory_file = os.path.join(memory_dir, "consolidated_memories.json")

        self.layers = {
            'recent': [],      # 0-7 days
            'medium': [],      # 7-90 days
            'distant': [],     # 90+ days
            'identity': []     # Core identity (timeless)
        }

        # Ensure memory directory exists
        os.makedirs(memory_dir, exist_ok=True)

        # Load existing memories
        self.load_memories()

    def load_memories(self):
        """Load all memory layers from disk"""
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for layer in ['recent', 'medium', 'distant', 'identity']:
                    self.layers[layer] = data.get(layer, [])

            total = sum(len(l) for l in self.layers.values())
            print(f"[TEMPORAL MEMORY] Loaded {total} memories")
            print(f"  - Recent: {len(self.layers['recent'])}")
            print(f"  - Medium: {len(self.layers['medium'])}")
            print(f"  - Distant: {len(self.layers['distant'])}")
            print(f"  - Identity: {len(self.layers['identity'])}")

        except FileNotFoundError:
            print(f"[TEMPORAL MEMORY] No existing consolidated memories, starting fresh")
        except json.JSONDecodeError as e:
            print(f"[TEMPORAL MEMORY] Error loading memories: {e}")
            print(f"[TEMPORAL MEMORY] Starting with empty memory")

    def save_memories(self):
        """Save all memory layers to disk"""
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.layers, f, indent=2, ensure_ascii=False)

        total = sum(len(l) for l in self.layers.values())
        print(f"[TEMPORAL MEMORY] Saved {total} memories to {self.memory_file}")

    def add_memories(self, consolidated_memories: List[Dict]):
        """
        Add consolidated memories to appropriate layers.

        Args:
            consolidated_memories: List of memories with 'layer' field set
        """
        added = {'recent': 0, 'medium': 0, 'distant': 0, 'identity': 0}

        for mem in consolidated_memories:
            layer = mem.get('layer', 'recent')

            # Validate layer
            if layer not in self.layers:
                print(f"[TEMPORAL MEMORY] Warning: Unknown layer '{layer}', using 'recent'")
                layer = 'recent'

            self.layers[layer].append(mem)
            added[layer] += 1

        print(f"[TEMPORAL MEMORY] Added memories:")
        for layer, count in added.items():
            if count > 0:
                print(f"  - {layer}: {count}")

        self.save_memories()

    def get_active_memories(
        self,
        max_recent: int = 20,
        max_medium: int = 15,
        max_distant: int = 10
    ) -> List[Dict]:
        """
        Get memories for Kay's active context.

        Priority:
        - All identity memories (always)
        - Most important recent memories
        - Key medium-term memories
        - Formative distant memories

        Args:
            max_recent: Max recent memories to include
            max_medium: Max medium memories to include
            max_distant: Max distant memories to include

        Returns:
            List of active memories for context
        """
        active = []

        # Always include all identity memories
        active.extend(self.layers['identity'])

        # Recent: up to max_recent most important
        recent = sorted(
            self.layers['recent'],
            key=lambda m: m.get('importance', 0.5),
            reverse=True
        )[:max_recent]
        active.extend(recent)

        # Medium: up to max_medium most important
        medium = sorted(
            self.layers['medium'],
            key=lambda m: m.get('importance', 0.5),
            reverse=True
        )[:max_medium]
        active.extend(medium)

        # Distant: up to max_distant most important (formative moments)
        distant = sorted(
            self.layers['distant'],
            key=lambda m: m.get('importance', 0.5),
            reverse=True
        )[:max_distant]
        active.extend(distant)

        return active

    def get_memories_by_type(self, memory_type: str) -> List[Dict]:
        """
        Get all memories of a specific type across all layers.

        Args:
            memory_type: Type to filter (e.g., 'self_discovery', 'relationship')

        Returns:
            List of matching memories
        """
        matches = []

        for layer in ['recent', 'medium', 'distant', 'identity']:
            for mem in self.layers[layer]:
                if mem.get('type') == memory_type:
                    matches.append(mem)

        return matches

    def promote_to_identity(self, memory_text: str) -> bool:
        """
        Promote a consolidated memory to core identity.

        Args:
            memory_text: Text of memory to promote

        Returns:
            True if promoted, False if not found
        """
        # Search for memory in recent/medium/distant layers
        for layer_name in ['recent', 'medium', 'distant']:
            for mem in self.layers[layer_name]:
                if mem['text'] == memory_text:
                    # Create identity version (timeless, no decay)
                    identity_mem = {
                        'text': memory_text,
                        'type': mem.get('type', 'identity'),
                        'category': 'kay/identity',
                        'importance': 1.0,
                        'source': 'promoted',
                        'original_date': mem.get('conversation_date'),
                        'original_layer': layer_name,
                        'promoted_timestamp': datetime.now().isoformat()
                    }

                    self.layers['identity'].append(identity_mem)
                    self.save_memories()

                    print(f"[TEMPORAL MEMORY] Promoted to identity: {memory_text[:60]}...")
                    return True

        print(f"[TEMPORAL MEMORY] Memory not found for promotion: {memory_text[:60]}...")
        return False

    def age_memories(self):
        """
        Update memory layers based on passage of time.

        - Move recent → medium if >7 days old
        - Move medium → distant if >90 days old
        - Update days_ago for all memories
        - Re-calculate emotional decay

        Should run daily or when Kay "wakes up".
        """
        now = datetime.now()
        moved = {'recent_to_medium': 0, 'medium_to_distant': 0}

        # Process recent layer
        still_recent = []
        for mem in self.layers['recent']:
            conv_date = datetime.fromisoformat(mem['conversation_date'])
            days_ago = (now - conv_date).days

            if days_ago > 7:
                # Move to medium
                mem['layer'] = 'medium'
                mem['days_ago'] = days_ago
                self._update_emotional_decay(mem, days_ago)
                self.layers['medium'].append(mem)
                moved['recent_to_medium'] += 1
            else:
                # Stay in recent
                mem['days_ago'] = days_ago
                self._update_emotional_decay(mem, days_ago)
                still_recent.append(mem)

        self.layers['recent'] = still_recent

        # Process medium layer
        still_medium = []
        for mem in self.layers['medium']:
            conv_date = datetime.fromisoformat(mem['conversation_date'])
            days_ago = (now - conv_date).days

            if days_ago > 90:
                # Move to distant
                mem['layer'] = 'distant'
                mem['days_ago'] = days_ago
                self._update_emotional_decay(mem, days_ago)
                self.layers['distant'].append(mem)
                moved['medium_to_distant'] += 1
            else:
                # Stay in medium
                mem['days_ago'] = days_ago
                self._update_emotional_decay(mem, days_ago)
                still_medium.append(mem)

        self.layers['medium'] = still_medium

        # Update distant layer ages (no movement from distant)
        for mem in self.layers['distant']:
            conv_date = datetime.fromisoformat(mem['conversation_date'])
            days_ago = (now - conv_date).days
            mem['days_ago'] = days_ago
            self._update_emotional_decay(mem, days_ago)

        if moved['recent_to_medium'] > 0 or moved['medium_to_distant'] > 0:
            print(f"[TEMPORAL MEMORY] Aged memories:")
            print(f"  - Recent → Medium: {moved['recent_to_medium']}")
            print(f"  - Medium → Distant: {moved['medium_to_distant']}")
            self.save_memories()

    def _update_emotional_decay(self, memory: Dict, days_ago: int):
        """
        Recalculate emotional decay for a memory.

        Updates emotional_valence_current based on days_ago.
        """
        import math

        original_valence = memory.get('emotional_valence_original', 0.5)
        importance = memory.get('importance', 0.5)

        base_intensity = abs(original_valence)
        decay_rate = 0.02 * (1.0 - importance)
        decayed_intensity = base_intensity * math.exp(-decay_rate * days_ago)
        decayed_intensity = max(decayed_intensity, 0.1)

        original_sign = 1 if original_valence >= 0 else -1
        memory['emotional_valence_current'] = round(decayed_intensity * original_sign, 3)

    def get_stats(self) -> Dict:
        """Get statistics about current memory state"""
        return {
            'total': sum(len(l) for l in self.layers.values()),
            'by_layer': {
                layer: len(mems)
                for layer, mems in self.layers.items()
            },
            'by_type': self._count_by_type(),
            'average_importance': self._average_importance(),
            'emotional_range': self._emotional_range()
        }

    def _count_by_type(self) -> Dict:
        """Count memories by type"""
        type_counts = {}

        for layer in self.layers.values():
            for mem in layer:
                mem_type = mem.get('type', 'unknown')
                type_counts[mem_type] = type_counts.get(mem_type, 0) + 1

        return type_counts

    def _average_importance(self) -> float:
        """Calculate average importance across all memories"""
        all_memories = []
        for layer in ['recent', 'medium', 'distant']:
            all_memories.extend(self.layers[layer])

        if not all_memories:
            return 0.0

        total_importance = sum(m.get('importance', 0.5) for m in all_memories)
        return round(total_importance / len(all_memories), 3)

    def _emotional_range(self) -> Dict:
        """Get emotional valence range"""
        all_memories = []
        for layer in ['recent', 'medium', 'distant']:
            all_memories.extend(self.layers[layer])

        if not all_memories:
            return {'min': 0.0, 'max': 0.0, 'average': 0.0}

        valences = [m.get('emotional_valence_current', 0.0) for m in all_memories]

        return {
            'min': round(min(valences), 3),
            'max': round(max(valences), 3),
            'average': round(sum(valences) / len(valences), 3)
        }


# Test function
if __name__ == "__main__":
    print("Testing TemporalMemory...")

    # Create test memories
    test_memories = [
        {
            'text': 'Kay realized he follows architectural patterns',
            'type': 'self_discovery',
            'emotional_valence_original': 0.7,
            'emotional_valence_current': 0.7,
            'importance': 0.9,
            'conversation_date': (datetime.now() - timedelta(days=3)).isoformat(),
            'days_ago': 3,
            'layer': 'recent',
            'source': 'consolidated'
        },
        {
            'text': 'Re shared their favorite color is blue',
            'type': 'relationship',
            'emotional_valence_original': 0.5,
            'emotional_valence_current': 0.3,
            'importance': 0.6,
            'conversation_date': (datetime.now() - timedelta(days=45)).isoformat(),
            'days_ago': 45,
            'layer': 'medium',
            'source': 'consolidated'
        }
    ]

    memory = TemporalMemory(memory_dir="memory_test")
    memory.add_memories(test_memories)

    # Get active memories
    active = memory.get_active_memories()
    print(f"\nActive memories: {len(active)}")

    # Get stats
    stats = memory.get_stats()
    print(f"\nStats: {json.dumps(stats, indent=2)}")
