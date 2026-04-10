"""
Memory Deletion System

Provides mechanisms to forget/delete corrupted or irrelevant memories.
Entity requested: "There's no natural decay, no way to let irrelevant shit fall away"

Features:
1. Manual deletion by pattern matching
2. Corruption flagging with filtering
3. Time-based auto-pruning
4. Safe deletion (never removes identity facts)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re


class MemoryDeletion:
    """
    Handles memory deletion, corruption flagging, and auto-pruning.

    Philosophy: Let irrelevant data fall away naturally.
    """

    def __init__(self, memory_engine):
        """
        Initialize memory deletion system.

        Args:
            memory_engine: Reference to main MemoryEngine
        """
        self.memory_engine = memory_engine
        self.deletion_log = []  # Track what was deleted and why

    def forget_memory(self, pattern: str, reason: str = "User requested",
                     delete_type: str = "pattern") -> Dict[str, Any]:
        """
        Delete memories matching a pattern.

        Args:
            pattern: Text pattern to match (substring search)
            reason: Why this is being deleted
            delete_type: 'pattern' (substring), 'exact' (exact match), or 'regex'

        Returns:
            Dict with deletion stats
        """
        print(f"\n[MEMORY DELETION] Starting deletion...")
        print(f"[MEMORY DELETION] Pattern: '{pattern}'")
        print(f"[MEMORY DELETION] Reason: {reason}")
        print(f"[MEMORY DELETION] Type: {delete_type}")

        # Find matching memories
        matches = self._find_matching_memories(pattern, delete_type)

        print(f"[MEMORY DELETION] Found {len(matches)} potential matches")

        # Filter out protected memories
        deletable, protected = self._filter_protected_memories(matches)

        if protected:
            print(f"[MEMORY DELETION] Skipping {len(protected)} protected memories (identity facts)")

        # Delete from all layers
        deleted_count = 0
        deleted_memories = []

        for memory in deletable:
            success = self._delete_memory_from_layers(memory)
            if success:
                deleted_count += 1
                deleted_memories.append({
                    'preview': self._get_memory_preview(memory),
                    'layer': memory.get('current_layer', 'unknown'),
                    'timestamp': datetime.now().isoformat()
                })
                print(f"[MEMORY DELETION]   Deleted: {self._get_memory_preview(memory)}")

        # Log the deletion
        deletion_record = {
            'pattern': pattern,
            'reason': reason,
            'count': deleted_count,
            'timestamp': datetime.now().isoformat(),
            'deleted': deleted_memories
        }
        self.deletion_log.append(deletion_record)

        print(f"[MEMORY DELETION] Total deleted: {deleted_count}")
        print(f"[MEMORY DELETION] Protected (not deleted): {len(protected)}")

        # Save updated memory state
        self.memory_engine.memory_layers._save_to_disk()

        return {
            'deleted': deleted_count,
            'protected': len(protected),
            'pattern': pattern,
            'reason': reason
        }

    def flag_as_corrupted(self, pattern: str, reason: str = "Corrupted data") -> int:
        """
        Flag memories as corrupted without deleting them.
        They'll be filtered from retrieval.

        Args:
            pattern: Text pattern to match
            reason: Why this is corrupted

        Returns:
            Number of memories flagged
        """
        print(f"\n[CORRUPTION FLAG] Flagging corrupted memories...")
        print(f"[CORRUPTION FLAG] Pattern: '{pattern}'")

        matches = self._find_matching_memories(pattern, 'pattern')
        flagged_count = 0

        for memory in matches:
            # Skip identity facts
            if memory.get('is_identity', False):
                continue

            # Add corruption flag
            memory['corrupted'] = True
            memory['corruption_reason'] = reason
            memory['corruption_timestamp'] = datetime.now().isoformat()
            flagged_count += 1

            print(f"[CORRUPTION FLAG]   Flagged: {self._get_memory_preview(memory)}")

        print(f"[CORRUPTION FLAG] Total flagged: {flagged_count}")

        # Save updated memory state
        self.memory_engine.memory_layers._save_to_disk()

        return flagged_count

    def prune_old_memories(self, max_age_days: int = 90,
                          min_access_count: int = 0,
                          layer_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Auto-prune old memories that haven't been accessed recently.

        Args:
            max_age_days: Only prune memories older than this
            min_access_count: Only prune if accessed fewer times than this
            layer_filter: Only prune from specific layer ('semantic', 'episodic', 'working')

        Returns:
            Dict with pruning stats
        """
        print(f"\n[AUTO-PRUNE] Starting auto-pruning...")
        print(f"[AUTO-PRUNE] Age threshold: {max_age_days} days")
        print(f"[AUTO-PRUNE] Access threshold: {min_access_count} accesses")
        if layer_filter:
            print(f"[AUTO-PRUNE] Layer filter: {layer_filter}")

        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        # Get all memories from specified layers
        candidates = self._get_pruning_candidates(layer_filter)

        pruned = []
        protected = []

        for memory in candidates:
            # Never prune identity facts
            if memory.get('is_identity', False):
                protected.append(memory)
                continue

            # Check age
            mem_date = self._get_memory_date(memory)
            if mem_date and mem_date > cutoff_date:
                continue  # Too recent

            # Check access count
            access_count = memory.get('access_count', 0)
            if access_count > min_access_count:
                continue  # Accessed too often

            # Check importance
            importance = memory.get('importance_score', 0)
            if importance > 0.8:
                protected.append(memory)
                continue  # Too important

            # Prune this memory
            success = self._delete_memory_from_layers(memory)
            if success:
                pruned.append({
                    'preview': self._get_memory_preview(memory),
                    'layer': memory.get('current_layer', 'unknown'),
                    'age_days': (datetime.now() - mem_date).days if mem_date else 'unknown',
                    'access_count': access_count
                })

        print(f"[AUTO-PRUNE] Pruned: {len(pruned)} memories")
        print(f"[AUTO-PRUNE] Protected: {len(protected)} memories")

        # Save updated memory state
        self.memory_engine.memory_layers._save_to_disk()

        return {
            'pruned': len(pruned),
            'protected': len(protected),
            'details': pruned[:10]  # Show first 10
        }

    def get_deletion_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent deletion history."""
        return self.deletion_log[-limit:]

    # Private helper methods

    def _find_matching_memories(self, pattern: str, match_type: str) -> List[Dict[str, Any]]:
        """Find memories matching the pattern."""
        matches = []
        pattern_lower = pattern.lower()

        # Search in all memory layers
        all_memories = []
        if hasattr(self.memory_engine, 'memory_layers'):
            all_memories.extend(self.memory_engine.memory_layers.working_memory)
            all_memories.extend(self.memory_engine.memory_layers.long_term_memory)
        else:
            # Fallback to flat memories
            all_memories = self.memory_engine.memories

        for memory in all_memories:
            mem_text = self._get_memory_text(memory).lower()

            if match_type == 'pattern':
                # Substring match
                if pattern_lower in mem_text:
                    matches.append(memory)
            elif match_type == 'exact':
                # Exact match
                if pattern_lower == mem_text:
                    matches.append(memory)
            elif match_type == 'regex':
                # Regex match
                try:
                    if re.search(pattern_lower, mem_text):
                        matches.append(memory)
                except re.error:
                    print(f"[MEMORY DELETION] Invalid regex: {pattern}")

        return matches

    def _filter_protected_memories(self, memories: List[Dict[str, Any]]) -> tuple:
        """Separate deletable from protected memories."""
        deletable = []
        protected = []

        for memory in memories:
            # Protect identity facts
            if memory.get('is_identity', False):
                protected.append(memory)
                continue

            # Protect memories marked as important
            if memory.get('importance_score', 0) > 0.9:
                protected.append(memory)
                continue

            # Protect very recent working memory
            if memory.get('current_layer') == 'working':
                age = self.memory_engine.current_turn - memory.get('turn_index', 0)
                if age < 3:  # Last 3 turns
                    protected.append(memory)
                    continue

            deletable.append(memory)

        return deletable, protected

    def _delete_memory_from_layers(self, memory: Dict[str, Any]) -> bool:
        """Delete memory from all storage locations."""
        try:
            # Remove from layered memory
            if hasattr(self.memory_engine, 'memory_layers'):
                # Two-tier: try working first, then long-term
                if memory in self.memory_engine.memory_layers.working_memory:
                    self.memory_engine.memory_layers.working_memory.remove(memory)
                elif memory in self.memory_engine.memory_layers.long_term_memory:
                    self.memory_engine.memory_layers.long_term_memory.remove(memory)

            # Remove from flat memories (if present)
            if memory in self.memory_engine.memories:
                self.memory_engine.memories.remove(memory)

            return True
        except Exception as e:
            print(f"[MEMORY DELETION] Error deleting memory: {e}")
            return False

    def _get_pruning_candidates(self, layer_filter: Optional[str]) -> List[Dict[str, Any]]:
        """Get memories that could be pruned."""
        candidates = []

        if hasattr(self.memory_engine, 'memory_layers'):
            if not layer_filter or layer_filter == 'working':
                candidates.extend(self.memory_engine.memory_layers.working_memory)
            if not layer_filter or layer_filter in ('long_term', 'episodic', 'semantic', None):
                candidates.extend(self.memory_engine.memory_layers.long_term_memory)
        else:
            candidates = self.memory_engine.memories

        return candidates

    def _get_memory_text(self, memory: Dict[str, Any]) -> str:
        """Extract searchable text from memory."""
        # Try different fields
        text = memory.get('fact', '')
        if not text:
            text = memory.get('text', '')
        if not text:
            text = memory.get('user_input', '')
        if not text:
            text = memory.get('response', '')

        return str(text)

    def _get_memory_preview(self, memory: Dict[str, Any]) -> str:
        """Get short preview of memory for logging."""
        text = self._get_memory_text(memory)
        return text[:80] + '...' if len(text) > 80 else text

    def _get_memory_date(self, memory: Dict[str, Any]) -> Optional[datetime]:
        """Get date when memory was created."""
        # Try timestamp field
        if 'timestamp' in memory:
            try:
                return datetime.fromisoformat(memory['timestamp'].replace('Z', '+00:00'))
            except:
                pass

        # Try turn_index (approximate)
        if 'turn_index' in memory:
            turn_age = self.memory_engine.current_turn - memory['turn_index']
            return datetime.now() - timedelta(days=turn_age * 0.1)  # Rough estimate

        return None
