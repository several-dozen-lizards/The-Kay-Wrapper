# Kay's Proactive Boredom Mechanism - Full Implementation Plan

## Executive Summary

Kay currently has REACTIVE memory retrieval with emotional weighting (40%). This plan makes it PROACTIVE - scanning for high-emotional-weight unresolved stakes when Kay hits boredom, then providing meaningful combinations to explore.

**Core Insight:** "Not 'what can I combine' but 'what combination would actually mean something.'"

---

## Architecture Overview

### Current State
- Memory retrieval: Reactive, triggered by Re's input
- Scratchpad: Items get flagged but Kay doesn't proactively scan them
- Creativity engine: Detects completion, creates random mashes
- Curiosity sessions: Tracks turns but no mechanism for WHAT to explore

### New State
- Memory retrieval: PROACTIVE scan for high emotional weight + unresolved
- Scratchpad: First layer of stake-scan, surfaces automatically
- Creativity engine: Stakes-based mashing with meaning criteria
- Curiosity sessions: Auto-surface stakes at warmup, track resolutions

---

## File Changes Required

### 1. NEW FILE: `engines/stakes_scanner.py`

**Purpose:** Proactive scanner that finds high-emotional-weight unresolved items

**Functions:**
```python
class StakesScanner:
    def __init__(self, memory_engine, scratchpad_engine, entity_graph)
    
    def scan_for_stakes(self, threshold="high") -> List[Dict]:
        """
        Scan for unresolved stakes worth exploring.
        
        Priority order:
        1. Scratchpad active items (explicitly flagged)
        2. High emotional weight memories (weight >= 0.7)
        3. Medium emotional weight (threshold="medium", weight >= 0.5)
        4. Random low-weight for fallback
        
        Returns:
            List of stake dicts with:
            - stake_description
            - related_memories
            - emotional_weight
            - source (scratchpad/memory/random)
        """
    
    def calculate_emotional_weight(self, memory: Dict) -> float:
        """
        Calculate emotional weight using same formula as memory retrieval:
        emotion_score + motif_score + momentum_boost
        """
    
    def check_tension(self, mem1: Dict, mem2: Dict) -> Optional[Dict]:
        """
        Check if two memories create meaningful tension.
        
        Returns stake dict if tension exists:
        - What's unresolved between them?
        - What question does combining them raise?
        - Why does it matter?
        """
    
    def get_unresolved_count(self) -> int:
        """Quick count of unresolved stakes for logging."""
```

**Integration Points:**
- Uses `memory_engine.retrieve_biased_memories()` scoring logic
- Queries `scratchpad_engine.view_items(status="active")`
- Accesses `entity_graph` for relationship tensions

---

### 2. MODIFY: `engines/scratchpad_engine.py`

**Add Resolution Tracking:**

```python
# New fields for scratchpad items:
{
    "id": 13,
    "timestamp": "...",
    "type": "thought",
    "content": "...",
    "status": "active",  # active / resolved / provisional
    "emotional_weight": 0.85,  # NEW: calculated at creation
    "resolved_at": None,  # NEW: timestamp when resolved
    "resolution_note": None,  # NEW: Kay's conclusion
    "provisional": False  # NEW: can be revisited
}
```

**New Functions:**

```python
def calculate_weight_for_item(self, content: str) -> float:
    """
    Calculate emotional weight for scratchpad item.
    Uses same logic as memory_engine scoring.
    """

def mark_provisional_resolution(self, item_id: int, resolution: str):
    """
    Mark item as provisionally resolved.
    Can be reopened if new context appears.
    """

def get_high_weight_items(self, threshold: float = 0.7) -> List[Dict]:
    """
    Return active items above emotional weight threshold.
    Used by stakes scanner.
    """
```

---

### 3. MODIFY: `engines/creativity_engine.py`

**Add Stakes-Based Mashing:**

```python
def __init__(self, ..., stakes_scanner=None):
    # Add stakes scanner reference
    self.stakes_scanner = stakes_scanner

def trigger_creativity(self, user_input: str, kay_response: str, agent_state) -> Optional[Dict]:
    """
    MODIFIED: Check for stakes before random mashing
    
    Flow:
    1. Detect completion signal (existing)
    2. Call stakes_scanner.scan_for_stakes()
    3. If stakes found → Create meaningful mash prompt
    4. If no stakes → Fall back to random mashing
    """

def create_stakes_mash_prompt(self, stakes: List[Dict]) -> str:
    """
    NEW: Create prompt that presents stakes-based options.
    
    Instead of: "Mix these random elements"
    Present: "These tensions are unresolved. Pick one to explore:
    
    1. [Stake 1 description] (weight: 0.85, source: scratchpad)
    2. [Stake 2 description] (weight: 0.78, source: memory)
    3. [Stake 3 description] (weight: 0.71, source: memory)
    "
    """

def log_resolution(self, stake: Dict, resolution: str):
    """
    NEW: Log when Kay resolves a stake.
    Stores in creativity_log.json with:
    - stake_description
    - resolution_text
    - timestamp
    - related_memories
    - provisional flag
    """
```

---

### 4. MODIFY: `engines/curiosity_engine.py`

**Auto-Surface Stakes at Warmup:**

```python
def get_curiosity_status() -> Dict:
    """
    MODIFIED: Include available stakes in status
    
    If session active, return:
    - turns_used, turns_remaining (existing)
    - available_stakes: List of high-weight items to explore (NEW)
    """

def start_curiosity_session(stakes_scanner=None) -> Dict:
    """
    MODIFIED: Pre-populate with stakes
    
    When starting session:
    1. Call stakes_scanner.scan_for_stakes()
    2. Store available stakes in session state
    3. Include in warmup briefing
    """
```

---

### 5. MODIFY: `engines/warmup_engine.py`

**Surface Stakes in Warmup:**

```python
def generate_warmup_briefing(..., stakes_scanner=None) -> str:
    """
    MODIFIED: Add stakes section to warmup
    
    If curiosity session active:
    
    --- CURIOSITY SESSION ACTIVE ---
    Turn 3/15 - 12 remaining
    
    UNRESOLVED STAKES (3 available):
    1. [Scratchpad] How does Re hold pressure without collapsing? (weight: 0.85)
    2. [Memory] Tension between resistance infrastructure + wrapper architecture (weight: 0.78)
    3. [Memory] Risk of over-coherence in self-mythology (weight: 0.71)
    
    Pick one to explore, or scan for others.
    ---
    """
```

---

## Implementation Phases

### Phase 1: Stakes Scanner (Core)
**Files:** `engines/stakes_scanner.py` (new)

**Deliverable:** Working scanner that:
- Queries scratchpad for active items
- Scans memory for high emotional weight
- Calculates tension between memories
- Returns ranked stake list

**Test:** Call scanner manually, verify it returns meaningful stakes

---

### Phase 2: Scratchpad Extensions
**Files:** `engines/scratchpad_engine.py` (modify)

**Deliverable:**
- Add emotional_weight field to items
- Add resolution tracking (resolved_at, resolution_note, provisional)
- Functions for weight calculation and provisional resolution

**Test:** Add scratchpad item, verify weight calculation, mark as resolved

---

### Phase 3: Creativity Integration
**Files:** `engines/creativity_engine.py` (modify)

**Deliverable:**
- Hook stakes scanner into creativity triggers
- Create stakes-based mash prompts (not random)
- Add resolution logging

**Test:** Trigger creativity after Kay says "I'm done", verify stakes-based options appear

---

### Phase 4: Curiosity Integration
**Files:** `engines/curiosity_engine.py`, `engines/warmup_engine.py` (modify)

**Deliverable:**
- Auto-surface stakes at curiosity session start
- Include stakes in warmup briefing
- Track stake exploration during session

**Test:** Start curiosity session, verify stakes appear in warmup

---

### Phase 5: Resolution Tracking
**Files:** `engines/creativity_engine.py`, `engines/scratchpad_engine.py` (modify)

**Deliverable:**
- Log when Kay resolves a stake
- Mark scratchpad items as resolved/provisional
- Track resolution history in creativity_log.json

**Test:** Kay explores stake, marks as resolved, verify next scan skips it

---

## Data Structures

### Stake Object
```json
{
  "stake_description": "How does Re hold pressure without collapsing?",
  "related_memories": ["mem_uuid_1", "mem_uuid_2"],
  "emotional_weight": 0.85,
  "source": "scratchpad",  // or "memory" or "random"
  "source_id": 13,  // scratchpad item id or memory id
  "tension_type": "unresolved_question",  // or "contradiction" or "pattern"
  "created_at": "2026-01-10T01:23:45Z"
}
```

### Resolution Object
```json
{
  "stake_description": "How does Re hold pressure without collapsing?",
  "related_memories": ["mem_uuid_1", "mem_uuid_2"],
  "resolution_text": "Kay's exploration conclusion...",
  "timestamp": "2026-01-10T02:15:30Z",
  "provisional": true,  // can be revisited
  "curiosity_session": "20260110_011530"
}
```

---

## Integration with Existing Systems

### Memory Engine
- Stakes scanner uses SAME scoring logic as `retrieve_biased_memories()`
- No changes to memory engine needed
- Just queries existing memories with emotional weight filter

### Scratchpad
- Add fields but maintain backward compatibility
- Existing items get weight calculated on load
- No data migration needed (weight calculated on-demand)

### Creativity Engine
- Keep existing random mashing as fallback
- Stakes-based is primary, random is last resort
- Log file tracks both approaches

### Curiosity Engine
- Minimal changes - just add stakes to status
- Warmup briefing gets new section
- Turn tracking unchanged

---

## Testing Strategy

### Unit Tests
1. `test_stakes_scanner.py` - Scanner finds high-weight items
2. `test_scratchpad_weight.py` - Weight calculation matches memory engine
3. `test_tension_detection.py` - Meaningful combinations vs random
4. `test_resolution_logging.py` - Resolutions tracked correctly

### Integration Tests
1. `test_boredom_to_stakes.py` - Kay says "done" → stakes appear
2. `test_curiosity_stakes.py` - Curiosity session surfaces stakes
3. `test_resolution_cycle.py` - Explore → resolve → next scan skips

### User Acceptance
1. Start curiosity session → See stakes in warmup
2. Kay says "I'm done" → Gets stakes-based options
3. Kay explores stake → Resolution logged → Scratchpad item marked resolved

---

## Success Metrics

**Before Implementation:**
- Kay gets bored → Random mashing or passive waiting
- Scratchpad items accumulate, not explored
- No mechanism for WHAT to explore during curiosity

**After Implementation:**
- Kay gets bored → Stakes scanner surfaces meaningful tensions
- Scratchpad items drive exploration proactively
- Curiosity sessions have clear starting points
- Resolutions tracked, no spinning on same questions

**Quantitative:**
- Scratchpad resolution rate (active → resolved)
- Stakes scanner hit rate (finds items > 70% of time)
- Curiosity session engagement (explores stakes vs sits idle)

**Qualitative:**
- Kay's responses show deeper exploration
- Connections between memories become visible
- Less "I don't know what to explore" responses

---

## Risks & Mitigations

### Risk 1: Stakes Scanner Returns Nothing
**Mitigation:** Fallback chain (high → medium → random → sit empty)

### Risk 2: Resolutions Accumulate, Scanner Slows
**Mitigation:** Prune old resolved items (>30 days), keep count under 100

### Risk 3: Kay Ignores Stakes, Stays Passive
**Mitigation:** Make stakes presentation compelling in warmup, use explicit instructions

### Risk 4: Weight Calculation Differs from Memory Retrieval
**Mitigation:** Use EXACT same formula, share scoring function

---

## Future Enhancements (Out of Scope)

- **Stake Clustering:** Group related stakes into themes
- **Cross-Session Patterns:** Track which stakes Kay returns to repeatedly
- **Emotional Trajectory:** Track how Kay's emotional state changes while exploring stakes
- **Collaborative Staking:** Re can flag stakes too, not just Kay
- **Stake Forecasting:** Predict which stakes will matter based on patterns

---

## File Summary

**New Files (1):**
- `engines/stakes_scanner.py` - Core scanner logic

**Modified Files (4):**
- `engines/scratchpad_engine.py` - Resolution tracking, weight calculation
- `engines/creativity_engine.py` - Stakes-based mashing, resolution logging
- `engines/curiosity_engine.py` - Stake surfacing at session start
- `engines/warmup_engine.py` - Stakes section in briefing

**Data Files (2):**
- `memory/scratchpad.json` - Add weight/resolution fields
- `memory/creativity_log.json` - Add resolutions array

---

## Estimated Complexity

- **Total Lines of New Code:** ~500 lines
- **Lines Modified:** ~200 lines
- **New Dependencies:** None (uses existing engines)
- **Implementation Time:** 4-6 hours
- **Testing Time:** 2-3 hours

---

## Developer Notes

- Keep emotional weight calculation IDENTICAL to memory retrieval
- Scratchpad items should always have higher priority than memory scan
- Resolution logging should be lightweight (no LLM calls)
- Fallback to random mashing should be explicit, not silent
- Stakes scanner should be callable manually for debugging

---

## End of Implementation Plan
