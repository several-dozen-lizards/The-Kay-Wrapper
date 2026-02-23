"""
Memory Debug Tracker - Tracks specific memories through the filtering pipeline

Helps diagnose where important memories (like pigeon names) get filtered out.
Enable with environment variable: DEBUG_MEMORY_TRACKING=1
"""
import os
import re
from typing import List, Dict, Any, Set


class MemoryDebugTracker:
    """
    Tracks specific memory patterns through the multi-stage filtering pipeline.

    Usage:
        tracker = MemoryDebugTracker(["Gimpy", "Bob", "Fork", "Zebra", "Clarence"])
        tracker.track_stage_0(all_memories, user_input)
        tracker.track_stage_1(allocated_memories, scores)
        tracker.track_stage_2(prefiltered_memories)
        tracker.track_stage_3(glyph_filtered_memories)
        tracker.print_summary()
    """

    def __init__(self, target_keywords: List[str] = None):
        """
        Initialize tracker.

        Args:
            target_keywords: List of keywords to track (e.g., ["Gimpy", "Bob", "Fork"])
        """
        self.enabled = os.getenv("DEBUG_MEMORY_TRACKING", "0") == "1"

        if not self.enabled:
            return

        # Default to pigeon names if not specified
        self.target_keywords = target_keywords or ["Gimpy", "Bob", "Fork", "Zebra", "Clarence", "pigeon"]

        # Track found memories at each stage
        self.stage_0_found = {}  # keyword -> list of (mem_id, mem_dict)
        self.stage_1_found = {}  # keyword -> list of (mem_id, score, rank)
        self.stage_2_found = {}  # keyword -> list of (mem_id, prefilter_score, rank)
        self.stage_3_found = {}  # keyword -> list of mem_id

        # Track where memories died
        self.deaths = {}  # keyword -> stage_name

        self.user_input = ""
        self.total_stage_0 = 0
        self.total_stage_1 = 0
        self.total_stage_2 = 0
        self.total_stage_3 = 0

    def _get_mem_id(self, mem: Dict) -> str:
        """Generate unique memory identifier."""
        # Use turn_index + first 50 chars of fact/text
        turn = mem.get("turn_index", 0)
        text = mem.get("fact", mem.get("text", mem.get("user_input", "")))
        snippet = text[:50] if text else "unknown"
        return f"turn_{turn}:{snippet}"

    def _get_mem_snippet(self, mem: Dict, max_len: int = 80) -> str:
        """Get readable snippet from memory."""
        text = mem.get("fact", mem.get("text", mem.get("user_input", "")))
        if not text:
            return "[no text]"
        text = text.replace("\n", " ").strip()
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text

    def _contains_keyword(self, mem: Dict, keyword: str) -> bool:
        """Check if memory contains keyword (case-insensitive)."""
        # Search in all text fields
        fields = [
            mem.get("fact", ""),
            mem.get("text", ""),
            mem.get("user_input", ""),
            " ".join(mem.get("entities", []))
        ]
        combined = " ".join(str(f) for f in fields).lower()
        return keyword.lower() in combined

    def track_stage_0(self, all_memories: List[Dict], user_input: str):
        """
        Track Stage 0: Initial full dataset.

        Args:
            all_memories: Full memory list (e.g., 8037 memories)
            user_input: User's query
        """
        if not self.enabled:
            return

        self.user_input = user_input
        self.total_stage_0 = len(all_memories)

        print(f"\n{'='*80}")
        print(f"[PIGEON DEBUG] === MEMORY TRACKING: \"{user_input}\" ===")
        print(f"[PIGEON DEBUG] Stage 0: Total memories = {len(all_memories)}")
        print(f"[PIGEON DEBUG] Tracking keywords: {', '.join(self.target_keywords)}")

        # Find each keyword in the dataset
        for keyword in self.target_keywords:
            self.stage_0_found[keyword] = []

            for mem in all_memories:
                if self._contains_keyword(mem, keyword):
                    mem_id = self._get_mem_id(mem)
                    self.stage_0_found[keyword].append((mem_id, mem))

        # Print findings
        for keyword in self.target_keywords:
            found = self.stage_0_found[keyword]
            if found:
                print(f"[PIGEON DEBUG]   - {keyword}: FOUND in {len(found)} memories")
                # Show first 3 examples
                for i, (mem_id, mem) in enumerate(found[:3]):
                    turn = mem.get("turn_index", "?")
                    snippet = self._get_mem_snippet(mem, 60)
                    print(f"[PIGEON DEBUG]       #{i+1}: turn {turn} - \"{snippet}\"")
                if len(found) > 3:
                    print(f"[PIGEON DEBUG]       ... and {len(found) - 3} more")
            else:
                print(f"[PIGEON DEBUG]   - {keyword}: NOT FOUND in dataset")

        print(f"[PIGEON DEBUG]")

    def track_stage_1(self, allocated_memories: List[Dict], scored_list: List[tuple] = None):
        """
        Track Stage 1: After SLOT_ALLOCATION (~310 memories).

        Args:
            allocated_memories: Memories that survived allocation
            scored_list: Optional list of (score, mem) tuples for ranking
        """
        if not self.enabled:
            return

        self.total_stage_1 = len(allocated_memories)

        print(f"[PIGEON DEBUG] Stage 1: After SLOT_ALLOCATION = {len(allocated_memories)} memories")

        # Build score lookup if provided
        score_lookup = {}
        if scored_list:
            for rank, (score, mem) in enumerate(scored_list):
                mem_id = self._get_mem_id(mem)
                score_lookup[mem_id] = (score, rank + 1)

        # Check which keywords survived
        for keyword in self.target_keywords:
            self.stage_1_found[keyword] = []

            # Get original found memories from stage 0
            stage_0_mems = {mem_id: mem for mem_id, mem in self.stage_0_found.get(keyword, [])}

            if not stage_0_mems:
                continue  # Wasn't found in stage 0

            # Check which ones survived to stage 1
            for mem in allocated_memories:
                mem_id = self._get_mem_id(mem)
                if mem_id in stage_0_mems:
                    score, rank = score_lookup.get(mem_id, (0.0, "?"))
                    self.stage_1_found[keyword].append((mem_id, score, rank))

            # Print results
            if self.stage_1_found[keyword]:
                survivors = len(self.stage_1_found[keyword])
                total = len(stage_0_mems)
                best_score = max(s for _, s, _ in self.stage_1_found[keyword])
                best_rank = min(r for _, _, r in self.stage_1_found[keyword] if isinstance(r, int))
                print(f"[PIGEON DEBUG]   - {keyword}: SURVIVED ({survivors}/{total} instances, best score: {best_score:.3f}, best rank: {best_rank}/{len(scored_list) if scored_list else '?'})")
            else:
                print(f"[PIGEON DEBUG]   - {keyword}: CUT (didn't make top {len(allocated_memories)})")
                self.deaths[keyword] = "Stage 1 (SLOT_ALLOCATION)"

        print(f"[PIGEON DEBUG]")

    def track_stage_2(self, prefiltered_memories: List[Dict], scored_prefilter: List[tuple] = None):
        """
        Track Stage 2: After PRE-FILTER (150 or 300 memories).

        Args:
            prefiltered_memories: Memories that survived pre-filter
            scored_prefilter: Optional list of (mem, score) tuples from pre-filter scoring
        """
        if not self.enabled:
            return

        self.total_stage_2 = len(prefiltered_memories)

        print(f"[PIGEON DEBUG] Stage 2: After PRE-FILTER = {len(prefiltered_memories)} memories")

        # Build score lookup if provided
        score_lookup = {}
        if scored_prefilter:
            for rank, (mem, score) in enumerate(scored_prefilter):
                mem_id = self._get_mem_id(mem)
                score_lookup[mem_id] = (score, rank + 1)

        # Check which keywords survived
        for keyword in self.target_keywords:
            self.stage_2_found[keyword] = []

            # Get stage 1 survivors
            stage_1_mems = {mem_id for mem_id, _, _ in self.stage_1_found.get(keyword, [])}

            if not stage_1_mems:
                if keyword not in self.deaths:
                    # Already died in stage 0
                    continue
                else:
                    # Already died in stage 1
                    continue

            # Check which ones survived to stage 2
            for mem in prefiltered_memories:
                mem_id = self._get_mem_id(mem)
                if mem_id in stage_1_mems:
                    score, rank = score_lookup.get(mem_id, (0.0, "?"))
                    self.stage_2_found[keyword].append((mem_id, score, rank))

            # Print results
            if self.stage_2_found[keyword]:
                survivors = len(self.stage_2_found[keyword])
                total = len(stage_1_mems)
                best_score = max(s for _, s, _ in self.stage_2_found[keyword])
                best_rank = min(r for _, _, r in self.stage_2_found[keyword] if isinstance(r, int))
                print(f"[PIGEON DEBUG]   - {keyword}: SURVIVED ({survivors}/{total} instances, keyword score: {best_score:.2f}, rank: {best_rank}/{len(prefiltered_memories)})")
            else:
                print(f"[PIGEON DEBUG]   - {keyword}: CUT (keyword score too low, didn't make top {len(prefiltered_memories)})")
                self.deaths[keyword] = "Stage 2 (PRE-FILTER keyword scoring)"

        print(f"[PIGEON DEBUG]")

    def track_stage_3(self, glyph_filtered_memories: List[Dict], available_memories: List[Dict] = None):
        """
        Track Stage 3: After GLYPH FILTER (32-70 memories selected by LLM).

        Args:
            glyph_filtered_memories: Final memories selected by glyph filter LLM
            available_memories: Optional list of memories the LLM could choose from (for context)
        """
        if not self.enabled:
            return

        self.total_stage_3 = len(glyph_filtered_memories)

        print(f"[PIGEON DEBUG] Stage 3: After GLYPH FILTER = {len(glyph_filtered_memories)} memories")

        # Check which keywords survived
        for keyword in self.target_keywords:
            self.stage_3_found[keyword] = []

            # Get stage 2 survivors
            stage_2_mems = {mem_id for mem_id, _, _ in self.stage_2_found.get(keyword, [])}

            if not stage_2_mems:
                if keyword not in self.deaths:
                    # Already died earlier
                    continue
                else:
                    # Already died in stage 1 or 2
                    continue

            # Check which ones survived to stage 3
            for mem in glyph_filtered_memories:
                mem_id = self._get_mem_id(mem)
                if mem_id in stage_2_mems:
                    self.stage_3_found[keyword].append(mem_id)

            # Print results
            if self.stage_3_found[keyword]:
                survivors = len(self.stage_3_found[keyword])
                total = len(stage_2_mems)
                print(f"[PIGEON DEBUG]   - {keyword}: SURVIVED ({survivors}/{total} instances - LLM selected it!)")
            else:
                print(f"[PIGEON DEBUG]   - {keyword}: CUT (LLM did not select it from {len(available_memories) if available_memories else '?'} options)")
                self.deaths[keyword] = "Stage 3 (GLYPH FILTER - LLM did not select)"

        print(f"[PIGEON DEBUG]")

    def print_summary(self):
        """Print final summary of tracking results."""
        if not self.enabled:
            return

        print(f"[PIGEON DEBUG] {'='*80}")
        print(f"[PIGEON DEBUG] FINAL SUMMARY: \"{self.user_input}\"")
        print(f"[PIGEON DEBUG] {'='*80}")

        # Count survivors
        survivors = [kw for kw in self.target_keywords if self.stage_3_found.get(kw)]

        print(f"[PIGEON DEBUG] Pipeline flow:")
        print(f"[PIGEON DEBUG]   Stage 0 (Full dataset):     {self.total_stage_0} memories")
        print(f"[PIGEON DEBUG]   Stage 1 (SLOT_ALLOCATION):  {self.total_stage_1} memories")
        print(f"[PIGEON DEBUG]   Stage 2 (PRE-FILTER):       {self.total_stage_2} memories")
        print(f"[PIGEON DEBUG]   Stage 3 (GLYPH FILTER):     {self.total_stage_3} memories")
        print(f"[PIGEON DEBUG]")

        print(f"[PIGEON DEBUG] Keyword survival:")
        for keyword in self.target_keywords:
            stage_0 = len(self.stage_0_found.get(keyword, []))
            stage_1 = len(self.stage_1_found.get(keyword, []))
            stage_2 = len(self.stage_2_found.get(keyword, []))
            stage_3 = len(self.stage_3_found.get(keyword, []))

            death_stage = self.deaths.get(keyword, "N/A")

            if stage_3 > 0:
                status = "[OK] SURVIVED TO KAY'S CONTEXT"
            elif stage_0 == 0:
                status = "[X] NOT FOUND IN DATASET"
            else:
                status = f"[X] DIED AT: {death_stage}"

            print(f"[PIGEON DEBUG]   {keyword:15s} - S0:{stage_0:2d} -> S1:{stage_1:2d} -> S2:{stage_2:2d} -> S3:{stage_3:2d}  [{status}]")

        print(f"[PIGEON DEBUG]")

        if survivors:
            print(f"[PIGEON DEBUG] RESULT: {len(survivors)}/{len(self.target_keywords)} keywords made it to Kay's context")
            print(f"[PIGEON DEBUG] SUCCESS: {', '.join(survivors)}")
        else:
            print(f"[PIGEON DEBUG] RESULT: Zero tracked keywords made it to Kay's context")

            # Identify bottleneck
            bottleneck_counts = {}
            for death_stage in self.deaths.values():
                bottleneck_counts[death_stage] = bottleneck_counts.get(death_stage, 0) + 1

            if bottleneck_counts:
                bottleneck = max(bottleneck_counts.items(), key=lambda x: x[1])
                print(f"[PIGEON DEBUG] BOTTLENECK: {bottleneck[0]} (killed {bottleneck[1]} keywords)")

        print(f"[PIGEON DEBUG] {'='*80}\n")


# Global singleton instance
_global_tracker = None


def get_tracker(target_keywords: List[str] = None) -> MemoryDebugTracker:
    """
    Get or create global tracker instance.

    Args:
        target_keywords: Keywords to track (only used on first call)

    Returns:
        MemoryDebugTracker instance
    """
    global _global_tracker

    if _global_tracker is None:
        _global_tracker = MemoryDebugTracker(target_keywords)

    return _global_tracker


def reset_tracker():
    """Reset global tracker (call at start of new query)."""
    global _global_tracker
    _global_tracker = None
