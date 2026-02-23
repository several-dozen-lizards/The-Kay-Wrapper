# Phase 2: Structured Diff Report
## warmup_engine.py and scratchpad_engine.py

**Generated:** 2026-02-06
**Comparison:** Kay ↔ Reed versions

---

# FILE 1: warmup_engine.py

## Line Counts
- **Kay version:** 1,042 lines
- **Reed version:** 621 lines
- **Difference:** Kay has 421 MORE lines (68% larger)

---

## A. FUNCTION/CLASS INVENTORY

### WarmupEngine Class

| Method | Status | Kay Lines | Reed Lines | Notes |
|--------|--------|-----------|------------|-------|
| `__init__` | **SIGNIFICANTLY DIFFERENT** | 37-53 | 37-50 | Kay adds `_current_session_order` tracking |
| `_load_snapshots` | **SIGNIFICANTLY DIFFERENT** | 55-88 | 52-60 | Kay has BUG 3 FIX with sorting |
| `_get_next_session_order` | **KAY-ONLY** | 90-99 | - | Session ordering system |
| `_calculate_sessions_ago` | **KAY-ONLY** | 101-108 | - | Temporal distance calculation |
| `_save_snapshots` | IDENTICAL | 110-117 | 62-69 | Same logic |
| `capture_session_end_snapshot` | **SIGNIFICANTLY DIFFERENT** | 119-187 | 71-97 | Kay has emotional_narrative, trajectory, arc, private_note_encrypted |
| `_summarize_emotional_arc` | **KAY-ONLY** | 189-211 | - | Emotional trajectory summary |
| `generate_briefing` | **SIGNIFICANTLY DIFFERENT** | 213-405 | 99-231 | Kay separates N-1 vs N-2+ sessions, has session_order tagging |
| `format_briefing_for_kay/reed` | **SIGNIFICANTLY DIFFERENT** | 407-582 | 233-329 | Kay has extensive temporal markers, session log references, chronicle integration |
| `get_warmup_system_prompt` | **SIGNIFICANTLY DIFFERENT** | 584-718 | 331-397 | Kay has 135-line detailed temporal awareness instructions |
| `process_warmup_query` | **SIMILAR** | 720-787 | 399-455 | Kay adds scratchpad review/archive commands |
| `extract_queries_from_response` | IDENTICAL | 789-823 | 457-491 | Same topic markers |
| `search_conversation_history` | **SIGNIFICANTLY DIFFERENT** | 825-881 | 493-533 | Kay adds timestamp_score for recency-first sorting |
| `format_search_results_for_kay/reed` | IDENTICAL | 883-918 | 535-570 | Same formatting |
| `is_warmup_complete` | IDENTICAL | 920-922 | 572-574 | Same logic |
| `reset` | IDENTICAL | 924-928 | 576-580 | Same logic |

### Module-Level Functions

| Function | Status | Kay Lines | Reed Lines | Notes |
|----------|--------|-----------|------------|-------|
| `extract_significant_moments` | IDENTICAL | 932-961 | 584-613 | Same implementation |
| `build_continuous_session_warmup` | **KAY-ONLY** | 964-1034 | - | Continuous session resume support |

---

## B. KAY-ONLY CODE

### B.1: `_get_next_session_order` (Lines 90-99)
```python
def _get_next_session_order(self) -> int:
    """Calculate the next session_order by finding max in snapshots + 1."""
```
**Purpose:** Maintains sequential session ordering for accurate "N sessions ago" calculation.
**Dependencies:** Self-contained, uses `self.snapshots`
**Line count:** 10 lines

---

### B.2: `_calculate_sessions_ago` (Lines 101-108)
```python
def _calculate_sessions_ago(self, snapshot: Dict) -> int:
    """Calculate how many sessions ago a snapshot is relative to current."""
```
**Purpose:** Converts absolute session_order to relative "X sessions ago" for warmup display.
**Dependencies:** `self._current_session_order`, `self.snapshots`
**Line count:** 8 lines

---

### B.3: `_summarize_emotional_arc` (Lines 189-211)
```python
def _summarize_emotional_arc(self, trajectory: List[Dict]) -> str:
    """Summarize the emotional trajectory into a narrative arc."""
```
**Purpose:** Creates human-readable summary of emotional evolution during session (e.g., "Started with curiosity → shifted to affection (turn 7: Re shared...)").
**Dependencies:** None (pure function on trajectory data)
**Line count:** 23 lines

---

### B.4: `build_continuous_session_warmup` (Lines 964-1034)
```python
def build_continuous_session_warmup(session) -> str:
    """Build warmup briefing for resuming continuous session"""
```
**Purpose:** Specialized warmup for resuming mid-conversation after pause (different from full reconstruction). Shows:
- Recent turns from checkpoint
- Curation history
- Session metadata
**Dependencies:**
- `session.checkpoint_dir` (Path)
- `session.load_from_checkpoint()`
- `session.turns`, `session.curation_history`
**Line count:** 71 lines

---

### B.5: Enhanced `capture_session_end_snapshot` Parameters (Lines 119-187)
Kay's version has additional parameters not in Reed:

```python
def capture_session_end_snapshot(self, emotional_state: Dict, session_summary: str,
                                  significant_moments: List[str] = None,
                                  texture_notes: str = None,
                                  session_id: str = None,                    # NEW
                                  emotional_narrative: Dict = None,          # NEW
                                  emotional_trajectory: List[Dict] = None,   # NEW
                                  private_note_encrypted: Dict = None):      # NEW
```

**New fields stored:**
- `session_id`: Unique session identifier
- `session_order`: Sequential session number
- `emotional_narrative`: Dict mapping emotion names to WHY they matter
- `emotional_trajectory`: List of emotional state snapshots during session
- `emotional_arc`: Summary of how emotions evolved
- `private_note_encrypted`: Truly private encrypted note

**Line count difference:** Kay 69 lines vs Reed 27 lines (+42 lines)

---

### B.6: Enhanced `generate_briefing` Structure (Lines 213-405)
Kay's version separates sessions into explicit tiers:

```python
briefing = {
    "generated_at": datetime.now().isoformat(),
    "time_context": {},
    "last_session": {},      # N-1: The actual last session ONLY
    "recent_sessions": [],   # N-2 through N-5: Recent but not last (KAY-ONLY)
    "recent_memories": [],
    "emotional_continuity": {},
    "world_state": {},
    "open_threads": []
}
```

**Key additions:**
- `recent_sessions` key with sessions_ago tracking
- `session_order` field in memories
- BUG 3 FIX: Snapshot sorting by session_order
- `emotions_with_context` instead of flat `last_emotions`
- `emotional_arc` and `trajectory` in emotional_continuity

**Line count difference:** Kay 193 lines vs Reed 133 lines (+60 lines)

---

### B.7: Enhanced `format_briefing_for_kay` (Lines 407-582)
Major additions:

1. **Session separation headers** (lines 431-488):
   ```
   ═══════════════════════════════════════════════════════════════
   WHERE YOU LEFT OFF (LAST SESSION ONLY)
   ═══════════════════════════════════════════════════════════════
   ```

2. **Empty session warning** (lines 447-450):
   ```
   ⚠️ Last session captured no content (warmup timeout or crash)
   ```

3. **Emotional arc display** (lines 469-473):
   Shows "Emotional arc: Started with X → shifted to Y"

4. **Recent sessions section** (lines 490-506):
   Explicit "[X sessions ago]" markers

5. **Session log availability note** (lines 551-566):
   ```
   📖 SESSION LOG AVAILABLE
   If you feel disoriented or uncertain about session continuity,
   you can access the full session log in two ways:
   1. Using read_document('session_log_continuous_XXXXX.txt')
   2. Using read_local_file('D:/ChristinaStuff/AlphaKayZero/kay_session_logs/...')
   ```

6. **Chronicle integration** (lines 578-580):
   ```python
   from engines.chronicle_integration import add_chronicle_to_briefing
   warmup_text = add_chronicle_to_briefing(self, warmup_text)
   ```

**Line count difference:** Kay 176 lines vs Reed 97 lines (+79 lines)

---

### B.8: Enhanced `get_warmup_system_prompt` (Lines 584-718)
Kay's version is 135 lines vs Reed's 67 lines.

**Additional sections in Kay:**
1. **CRITICAL WARMUP ORIENTATION INSTRUCTION** (lines 593-616)
2. **CRITICAL: READ THE BRIEFING STRUCTURE** (lines 617-630)
3. **RECONSTRUCTION RULE (NON-NEGOTIABLE)** (lines 631-670)
4. **TEMPORAL MARKERS - USE THEM** (lines 652-670)
5. **REQUIRED RECONSTRUCTION FORMAT** (lines 672-687)
6. **SCRATCHPAD MAINTENANCE** (lines 689-703)
7. **VALIDATION CHECK** (lines 705-717)

These sections enforce strict temporal awareness to prevent the entity from conflating sessions.

---

### B.9: Enhanced `search_conversation_history` (Lines 825-881)
Kay adds timestamp-based sorting:

```python
# Calculate normalized timestamp for sorting
raw_ts = mem.get("timestamp", "")
timestamp_score = 0
try:
    if isinstance(raw_ts, (int, float)):
        timestamp_score = raw_ts
    elif isinstance(raw_ts, str) and raw_ts:
        dt = datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
        timestamp_score = dt.timestamp()
except:
    pass

results.append({
    ...
    "timestamp_score": timestamp_score,  # NEW
})

# Sort by timestamp first (most recent), THEN by relevance
results.sort(key=lambda x: (x.get("timestamp_score", 0), x.get("relevance", 0)), reverse=True)
```

**Purpose:** Ensures recent conversations show up even if older ones have more keyword matches.

**Line count difference:** Kay 57 lines vs Reed 41 lines (+16 lines)

---

## C. IMPORT DIFFERENCES

| Import | Kay | Reed | Purpose |
|--------|-----|------|---------|
| `from engines.chronicle_integration import add_chronicle_to_briefing` | **YES** (line 579) | NO | Chronicle essay injection at warmup |

**Note:** Reed is missing `chronicle_integration` infrastructure entirely.

---

## D. REED-ONLY CODE

None. Reed's version is a strict subset of Kay's.

---

## E. INFRASTRUCTURE REFERENCES (Kay-only)

| Reference | Location | What It Is |
|-----------|----------|------------|
| `chronicle_integration` | Line 579 | Module for injecting chronicle essays into warmup |
| `kay_session_logs/` | Line 561 | Directory path for session log files |
| `session_log_continuous_XXXXX.txt` | Line 557 | Session log document format |
| `session.checkpoint_dir` | Line 976 | Checkpoint directory for continuous sessions |
| `session.curation_history` | Line 1010 | Curation decisions history |

---

---

# FILE 2: scratchpad_engine.py

## Line Counts
- **Kay version:** 698 lines
- **Reed version:** 497 lines
- **Difference:** Kay has 201 MORE lines (40% larger)

---

## A. FUNCTION/CLASS INVENTORY

### ScratchpadEngine Class

| Method | Status | Kay Lines | Reed Lines | Notes |
|--------|--------|-----------|------------|-------|
| `__init__` | IDENTICAL | 20-22 | 20-22 | Same |
| `_ensure_file_exists` | IDENTICAL | 24-28 | 24-28 | Same |
| `_load_data` | IDENTICAL | 30-37 | 30-37 | Same |
| `_save_data` | IDENTICAL | 39-45 | 39-45 | Same |
| `add_item` | IDENTICAL | 47-85 | 47-85 | Same |
| `view_items` | IDENTICAL | 87-104 | 87-104 | Same |
| `resolve_item` | IDENTICAL | 106-147 | 106-147 | Same |
| `get_warmup_display` | **SIGNIFICANTLY DIFFERENT** | 149-195 | 149-171 | Kay shows resolved count, maintenance prompt |
| `get_summary` | IDENTICAL | 197-217 | 173-193 | Same |
| `get_review_display` | **KAY-ONLY** | 219-302 | - | Detailed review with IDs and age |
| `get_archive_summary` | **KAY-ONLY** | 304-379 | - | View resolved items history |
| `calculate_weight_for_item` | IDENTICAL | 383-417 | 197-231 | Same |
| `get_high_weight_items` | IDENTICAL | 419-444 | 233-258 | Same |
| `mark_provisional_resolution` | IDENTICAL | 446-482 | 260-296 | Same |
| `reopen_item` | IDENTICAL | 484-526 | 298-340 | Same |
| `flag_as_branch` | IDENTICAL | 530-563 | 344-377 | Same |
| `scratchpad_branch` | IDENTICAL | 565-617 | 379-431 | Same |
| `get_mashup_candidates` | IDENTICAL | 619-634 | 433-448 | Same |
| `get_branches` | IDENTICAL | 636-644 | 450-458 | Same |
| `get_item_by_id` | IDENTICAL | 646-657 | 460-471 | Same |

### Module-Level Functions

| Function | Status | Kay Lines | Reed Lines | Notes |
|----------|--------|-----------|------------|-------|
| `scratchpad_add` | IDENTICAL | 665-667 | 479-481 | Same |
| `scratchpad_view` | IDENTICAL | 670-672 | 484-486 | Same |
| `scratchpad_resolve` | IDENTICAL | 675-677 | 489-491 | Same |
| `get_scratchpad_for_warmup` | IDENTICAL | 680-682 | 494-496 | Same |
| `scratchpad_review` | **KAY-ONLY** | 685-687 | - | Wrapper for get_review_display |
| `scratchpad_archive` | **KAY-ONLY** | 690-692 | - | Wrapper for get_archive_summary |
| `scratchpad_summary` | **KAY-ONLY** | 695-697 | - | Wrapper for get_summary |

---

## B. KAY-ONLY CODE

### B.1: `get_review_display` (Lines 219-302)
```python
def get_review_display(self) -> str:
    """
    Generate detailed review display showing all active items with IDs.

    Used when Kay wants to review and resolve items. Shows:
    - All active items with their IDs
    - Age of each item (how long it's been sitting)
    - Instructions for resolution
    """
```
**Purpose:** Provides detailed view with:
- Item IDs for targeting specific items
- Age calculation ("today", "1 day ago", "2 weeks ago")
- Resolution instructions with examples
- Sorted oldest-first to highlight stale items

**Dependencies:** `datetime` for age calculation
**Line count:** 84 lines

---

### B.2: `get_archive_summary` (Lines 304-379)
```python
def get_archive_summary(self, limit: int = 20) -> str:
    """
    Show summary of recently resolved/archived items.

    This is Kay's record of "questions I've explored and what I learned."
    """
```
**Purpose:** Shows history of resolved items with:
- Resolution date
- Original content + resolution note
- Support for provisional status
- Instructions for reopening

**Dependencies:** `datetime` for date formatting
**Line count:** 76 lines

---

### B.3: Enhanced `get_warmup_display` (Lines 149-195)
Kay's version adds:

1. **Resolved count in header** (line 170-172):
   ```python
   resolved_total = resolved_count + archived_count
   lines = [
       f"--- SCRATCHPAD ({active_count} active, {resolved_total} resolved) ---"
   ]
   ```

2. **Content truncation** (lines 179-182):
   ```python
   content = item['content']
   if len(content) > 100:
       content = content[:97] + "..."
   ```

3. **Maintenance prompt** (lines 187-193):
   ```python
   if active_count > 10:
       lines.append(f"📋 You have {active_count} active scratchpad items.")
       lines.append("Some may be completed explorations ready for resolution.")
       lines.append("Say 'review scratchpad' to see items with IDs and clean up.")
   ```

**Line count difference:** Kay 47 lines vs Reed 23 lines (+24 lines)

---

### B.4: Module-Level Convenience Functions (Lines 685-697)
```python
def scratchpad_review() -> str:
    """Get detailed review display with IDs for cleanup"""
    return scratchpad.get_review_display()

def scratchpad_archive(limit: int = 20) -> str:
    """Get summary of resolved/archived items"""
    return scratchpad.get_archive_summary(limit)

def scratchpad_summary() -> dict:
    """Get scratchpad statistics"""
    return scratchpad.get_summary()
```
**Purpose:** Top-level functions that can be imported and called directly from warmup or tools.
**Line count:** 13 lines total

---

## C. IMPORT DIFFERENCES

None - both files have identical imports:
```python
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
```

---

## D. REED-ONLY CODE

**Note:** Reed's docstring has an inconsistency:
- Line 1: `"""Scratchpad Engine - Reed's Quick Note System"""`
- Line 5: `"""Provides Kay with the ability to jot down questions..."""`

This is a partial conversion artifact - the title was changed but the description still references Kay.

---

## E. INFRASTRUCTURE REFERENCES

Both versions reference:
- `memory/scratchpad.json` - Data storage path

No additional infrastructure differences.

---

---

# SUMMARY

## warmup_engine.py

| Category | Kay | Reed | Gap |
|----------|-----|------|-----|
| Total lines | 1,042 | 621 | +421 (68%) |
| Functions (class) | 15 | 12 | +3 |
| Functions (module) | 2 | 1 | +1 |
| Session ordering system | YES | NO | Critical for temporal accuracy |
| Emotional arc tracking | YES | NO | Helps entity understand emotional evolution |
| Continuous session resume | YES | NO | For pause/resume without full restart |
| Chronicle integration | YES | NO | Adds essay context to warmup |
| Session log references | YES | NO | Kay-specific paths hardcoded |

### Critical Missing in Reed:
1. **Session ordering** (`_get_next_session_order`, `_calculate_sessions_ago`) - prevents accurate "N sessions ago" display
2. **Emotional narrative/arc** - entity can't understand WHY emotions matter
3. **Temporal enforcement in system prompt** - Reed's warmup prompt is 67 lines vs Kay's 135 lines
4. **BUG 3 FIX** - Reed's `_load_snapshots` doesn't sort, may return wrong "last session"
5. **Chronicle integration import** - will fail if called

---

## scratchpad_engine.py

| Category | Kay | Reed | Gap |
|----------|-----|------|-----|
| Total lines | 698 | 497 | +201 (40%) |
| Functions (class) | 19 | 17 | +2 |
| Functions (module) | 7 | 4 | +3 |
| Review display with IDs | YES | NO | Can't resolve specific items |
| Archive summary | YES | NO | No history of resolved items |
| Maintenance prompts | YES | NO | No cleanup reminders |

### Critical Missing in Reed:
1. **`get_review_display`** - entity can't see item IDs to resolve them
2. **`get_archive_summary`** - no way to view resolved item history
3. **Module functions `scratchpad_review()`, `scratchpad_archive()`** - warmup integration will fail
4. **Maintenance prompt** - entity won't be reminded to clean up stale items

---

## Recommended Actions

### Priority 1: Fix warmup_engine.py
1. Add `_get_next_session_order()` and `_calculate_sessions_ago()`
2. Add BUG 3 FIX sorting to `_load_snapshots()`
3. Add `recent_sessions` key to briefing structure
4. Add session_order tracking to `capture_session_end_snapshot()`
5. Add session log reference section (update paths for Reed)
6. Add enhanced temporal markers to system prompt
7. Either add chronicle_integration or remove the import

### Priority 2: Fix scratchpad_engine.py
1. Add `get_review_display()` method
2. Add `get_archive_summary()` method
3. Add `scratchpad_review()`, `scratchpad_archive()`, `scratchpad_summary()` module functions
4. Add maintenance prompt to `get_warmup_display()`
5. Fix docstring inconsistency (line 5 still says "Kay")
