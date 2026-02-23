"""
Corruption Detection System

Detects and marks corrupted memories with metadata tracking.
Integrates with ChromaDB for persistence and filtering.

Features:
1. Gibberish detection (repeated characters, nonsense patterns)
2. Memory supersession (mark old memory as superseded by corrected version)
3. Correction tracking (link wrong memory to correct memory)
4. ChromaDB metadata integration (backwards compatible)
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import re


class CorruptionDetector:
    """
    Detects and manages memory corruption markers.

    Corruption markers schema:
    {
        'corrupted': bool,
        'corruption_reason': str,
        'corruption_detected_turn': int,
        'superseded_by': Optional[str],  # Memory ID that supersedes this one
        'supersedes': Optional[str],     # Memory ID this one supersedes
        'correction_applied': bool,
        'correction_turn': Optional[int]
    }
    """

    def __init__(self, memory_engine):
        """
        Initialize corruption detector.

        Args:
            memory_engine: Reference to MemoryEngine for accessing memories
        """
        self.memory_engine = memory_engine
        self.gibberish_patterns = [
            r'(.)\1{4,}',  # Repeated character 5+ times: "aaaaa"
            r'\b\w*([a-z])\1{3,}\w*\b',  # Word with character repeated 4+ times
            r'[^a-zA-Z0-9\s]{10,}',  # 10+ consecutive special characters
            r'\b[bcdfghjklmnpqrstvwxyz]{8,}\b',  # 8+ consonants in a row (no vowels)
        ]

    def detect_corruption(self, memory_dict: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Detect if a memory appears corrupted.

        Args:
            memory_dict: Memory to check

        Returns:
            Tuple of (is_corrupted, reason)
        """
        # Get text content from memory
        text = self._extract_memory_text(memory_dict)

        if not text:
            return False, ""

        # Check for gibberish patterns
        for pattern in self.gibberish_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True, f"Gibberish detected: pattern '{pattern}' matched"

        # Check for excessive repetition (same word 5+ times)
        words = text.lower().split()
        if words:
            word_counts = {}
            for word in words:
                if len(word) > 3:  # Only count meaningful words
                    word_counts[word] = word_counts.get(word, 0) + 1

            max_repetition = max(word_counts.values()) if word_counts else 0
            if max_repetition >= 5:
                repeated_word = [w for w, c in word_counts.items() if c == max_repetition][0]
                return True, f"Excessive repetition: '{repeated_word}' appears {max_repetition} times"

        # Check if already marked as corrupted
        if memory_dict.get('corrupted', False):
            return True, memory_dict.get('corruption_reason', 'Previously flagged')

        return False, ""

    def mark_memory_superseded(self, old_memory_id: str, new_memory_id: str,
                              turn_id: int) -> bool:
        """
        Mark an old memory as superseded by a corrected version.

        Args:
            old_memory_id: ID of memory being superseded
            new_memory_id: ID of correcting memory
            turn_id: Turn when correction occurred

        Returns:
            True if successful
        """
        print(f"\n[CORRUPTION] Marking supersession...")
        print(f"[CORRUPTION]   Old memory: {old_memory_id}")
        print(f"[CORRUPTION]   New memory: {new_memory_id}")

        # Find old memory
        old_memory = self._find_memory_by_id(old_memory_id)
        if not old_memory:
            print(f"[CORRUPTION] ERROR: Old memory not found: {old_memory_id}")
            return False

        # Find new memory
        new_memory = self._find_memory_by_id(new_memory_id)
        if not new_memory:
            print(f"[CORRUPTION] ERROR: New memory not found: {new_memory_id}")
            return False

        # Mark old memory as superseded
        old_memory['corrupted'] = True
        old_memory['corruption_reason'] = 'Superseded by correction'
        old_memory['corruption_detected_turn'] = turn_id
        old_memory['superseded_by'] = new_memory_id
        old_memory['correction_applied'] = True
        old_memory['correction_turn'] = turn_id

        # Mark new memory as superseding
        new_memory['supersedes'] = old_memory_id
        new_memory['is_correction'] = True
        new_memory['correction_turn'] = turn_id

        print(f"[CORRUPTION] Successfully marked supersession at turn {turn_id}")

        # Save changes
        self.memory_engine.save_memories()

        return True

    def correct_memory(self, wrong_memory_id: str, correct_fact: str,
                      turn_id: int) -> Optional[str]:
        """
        Create a corrected version of a wrong memory and mark supersession.

        Args:
            wrong_memory_id: ID of memory to correct
            correct_fact: Corrected fact text
            turn_id: Turn when correction occurred

        Returns:
            ID of new corrected memory, or None if failed
        """
        print(f"\n[CORRUPTION] Correcting memory...")
        print(f"[CORRUPTION]   Wrong memory: {wrong_memory_id}")
        print(f"[CORRUPTION]   Correction: {correct_fact[:80]}...")

        # Find wrong memory
        wrong_memory = self._find_memory_by_id(wrong_memory_id)
        if not wrong_memory:
            print(f"[CORRUPTION] ERROR: Memory not found: {wrong_memory_id}")
            return None

        # Create corrected memory (copy metadata from wrong memory)
        corrected_memory = {
            'fact': correct_fact,
            'text': correct_fact,
            'turn_index': turn_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'current_layer': wrong_memory.get('current_layer', 'semantic'),
            'importance_score': wrong_memory.get('importance_score', 0.5),
            'perspective': wrong_memory.get('perspective', 'shared'),
            'access_count': 0,
            'last_access_turn': turn_id,
            'is_correction': True,
            'corrects_memory': wrong_memory_id,
            'correction_turn': turn_id,
            'supersedes': wrong_memory_id
        }

        # Add to memory engine
        if hasattr(self.memory_engine, 'memory_layers'):
            layer = corrected_memory['current_layer']
            if layer == 'working':
                self.memory_engine.memory_layers.working_memory.append(corrected_memory)
            elif layer == 'episodic':
                self.memory_engine.memory_layers.episodic_memory.append(corrected_memory)
            elif layer == 'semantic':
                self.memory_engine.memory_layers.semantic_memory.append(corrected_memory)

        # Also add to flat memories list
        self.memory_engine.memories.append(corrected_memory)

        # Generate ID for new memory (use index as simple ID)
        new_memory_id = f"mem_{len(self.memory_engine.memories)}"
        corrected_memory['memory_id'] = new_memory_id

        # Mark old memory as superseded
        self.mark_memory_superseded(wrong_memory_id, new_memory_id, turn_id)

        print(f"[CORRUPTION] Created corrected memory: {new_memory_id}")

        return new_memory_id

    def flag_corrupted_pattern(self, pattern: str, reason: str = "Corrupted data") -> int:
        """
        Flag all memories matching a pattern as corrupted.

        Args:
            pattern: Text pattern to match (substring search)
            reason: Reason for corruption flag

        Returns:
            Number of memories flagged
        """
        print(f"\n[CORRUPTION] Flagging corrupted pattern...")
        print(f"[CORRUPTION]   Pattern: '{pattern}'")
        print(f"[CORRUPTION]   Reason: {reason}")

        flagged_count = 0
        pattern_lower = pattern.lower()

        # Search all memories
        all_memories = self._get_all_memories()

        for memory in all_memories:
            # Skip if already flagged
            if memory.get('corrupted', False):
                continue

            # Skip identity facts
            if memory.get('is_identity', False):
                continue

            # Check if pattern matches
            text = self._extract_memory_text(memory).lower()
            if pattern_lower in text:
                memory['corrupted'] = True
                memory['corruption_reason'] = reason
                memory['corruption_detected_turn'] = self.memory_engine.current_turn
                flagged_count += 1

                preview = self._extract_memory_text(memory)[:80]
                print(f"[CORRUPTION]   Flagged: {preview}...")

        print(f"[CORRUPTION] Total flagged: {flagged_count}")

        # Save changes
        self.memory_engine.save_memories()

        return flagged_count

    def get_corruption_stats(self) -> Dict[str, Any]:
        """
        Get statistics about corrupted memories.

        Returns:
            Dict with corruption statistics
        """
        all_memories = self._get_all_memories()

        corrupted = [m for m in all_memories if m.get('corrupted', False)]
        superseded = [m for m in all_memories if m.get('superseded_by')]
        corrections = [m for m in all_memories if m.get('is_correction', False)]

        stats = {
            'total_memories': len(all_memories),
            'corrupted_count': len(corrupted),
            'superseded_count': len(superseded),
            'corrections_count': len(corrections),
            'corruption_rate': len(corrupted) / len(all_memories) if all_memories else 0,
        }

        # Group by reason
        reasons = {}
        for mem in corrupted:
            reason = mem.get('corruption_reason', 'Unknown')
            reasons[reason] = reasons.get(reason, 0) + 1

        stats['corruption_reasons'] = reasons

        return stats

    def scan_all_memories(self) -> Dict[str, Any]:
        """
        Scan all memories for corruption and return report.

        Returns:
            Dict with scan results
        """
        print("\n[CORRUPTION] Scanning all memories for corruption...")

        all_memories = self._get_all_memories()
        newly_detected = []
        already_flagged = 0
        clean = 0

        for memory in all_memories:
            is_corrupted, reason = self.detect_corruption(memory)

            if is_corrupted:
                if memory.get('corrupted', False):
                    already_flagged += 1
                else:
                    # Newly detected corruption
                    memory['corrupted'] = True
                    memory['corruption_reason'] = reason
                    memory['corruption_detected_turn'] = self.memory_engine.current_turn
                    newly_detected.append({
                        'text': self._extract_memory_text(memory)[:80],
                        'reason': reason
                    })
            else:
                clean += 1

        if newly_detected:
            print(f"[CORRUPTION] Newly detected: {len(newly_detected)}")
            for det in newly_detected[:5]:  # Show first 5
                print(f"[CORRUPTION]   - {det['text']}...")
                print(f"[CORRUPTION]     Reason: {det['reason']}")

        print(f"[CORRUPTION] Already flagged: {already_flagged}")
        print(f"[CORRUPTION] Clean: {clean}")

        # Save if any new detections
        if newly_detected:
            self.memory_engine.save_memories()

        return {
            'newly_detected': len(newly_detected),
            'already_flagged': already_flagged,
            'clean': clean,
            'total': len(all_memories),
            'details': newly_detected[:10]  # Return first 10
        }

    # Private helper methods

    def _extract_memory_text(self, memory: Dict[str, Any]) -> str:
        """Extract searchable text from memory."""
        text = memory.get('fact', '')
        if not text:
            text = memory.get('text', '')
        if not text:
            text = memory.get('user_input', '')
        if not text:
            text = memory.get('response', '')
        return str(text)

    def _find_memory_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Find memory by ID."""
        all_memories = self._get_all_memories()
        for memory in all_memories:
            if memory.get('memory_id') == memory_id:
                return memory
            # Fallback: use index-based ID
            if f"mem_{all_memories.index(memory)}" == memory_id:
                memory['memory_id'] = memory_id  # Backfill ID
                return memory
        return None

    def _get_all_memories(self) -> List[Dict[str, Any]]:
        """Get all memories from all layers."""
        all_memories = []
        if hasattr(self.memory_engine, 'memory_layers'):
            all_memories.extend(self.memory_engine.memory_layers.working_memory)
            all_memories.extend(self.memory_engine.memory_layers.episodic_memory)
            all_memories.extend(self.memory_engine.memory_layers.semantic_memory)
        else:
            all_memories = self.memory_engine.memories
        return all_memories


def ensure_corruption_markers(memory: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure memory has corruption marker fields (backwards compatibility).

    Args:
        memory: Memory dict to update

    Returns:
        Memory dict with corruption markers
    """
    if 'corrupted' not in memory:
        memory['corrupted'] = False
    if 'corruption_reason' not in memory:
        memory['corruption_reason'] = None
    if 'corruption_detected_turn' not in memory:
        memory['corruption_detected_turn'] = None
    if 'superseded_by' not in memory:
        memory['superseded_by'] = None
    if 'supersedes' not in memory:
        memory['supersedes'] = None
    if 'correction_applied' not in memory:
        memory['correction_applied'] = False
    if 'correction_turn' not in memory:
        memory['correction_turn'] = None

    return memory


def filter_corrupted_memories(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out corrupted and superseded memories.

    Args:
        memories: List of memories to filter

    Returns:
        Filtered list (corrupted memories removed)
    """
    clean = []
    for mem in memories:
        # Skip if corrupted
        if mem.get('corrupted', False):
            continue
        # Skip if superseded
        if mem.get('superseded_by'):
            continue
        clean.append(mem)

    return clean
