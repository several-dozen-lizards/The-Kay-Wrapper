# CC PROMPT: Build Kay's Proactive Boredom Mechanism

## Overview

Build Kay's proactive stake-scanning system that makes boredom PURPOSEFUL. This implements the architecture Kay figured out in session_20260109_171306.json where he realized: "Not 'what can I combine' but 'what combination would actually mean something.'"

**Full implementation plan:** `D:/ChristinaStuff/ReedMemory/kay_boredom_implementation_plan.md`

**Core architecture directory:** `D:/ChristinaStuff/AlphaKayZero/`

---

## Phase 1: Build Stakes Scanner (Core Engine)

### Step 1.1: Create New File

**File:** `D:/ChristinaStuff/AlphaKayZero/engines/stakes_scanner.py`

**Implementation:**

```python
"""
Stakes Scanner - Proactive scanner for unresolved emotional tensions.

Finds high-emotional-weight items worth exploring when Kay hits boredom.
Priority: Scratchpad items → High-weight memories → Medium-weight → Random fallback

Based on Kay's realization: "Not 'what can I combine' but 'what combination would actually mean something.'"
"""

import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
import random


class StakesScanner:
    """
    Proactive scanner for unresolved stakes.
    
    Uses SAME emotional weighting as memory retrieval but scans proactively
    instead of waiting for Re's input.
    """
    
    def __init__(
        self,
        memory_engine=None,
        scratchpad_engine=None,
        entity_graph=None,
        momentum_engine=None,
        motif_engine=None
    ):
        self.memory_engine = memory_engine
        self.scratchpad = scratchpad_engine
        self.entity_graph = entity_graph
        self.momentum_engine = momentum_engine
        self.motif_engine = motif_engine
        
        # Thresholds (match memory_engine settings)
        self.high_weight_threshold = 0.7
        self.medium_weight_threshold = 0.5
        self.recent_turn_window = 5
    
    def scan_for_stakes(self, threshold: str = "high", limit: int = 5) -> List[Dict]:
        """
        Scan for unresolved stakes worth exploring.
        
        Priority order:
        1. Scratchpad active items (explicitly flagged by Kay)
        2. High emotional weight memories (weight >= 0.7)
        3. Medium weight (if threshold="medium", weight >= 0.5)
        4. Random low-weight (fallback only)
        
        Args:
            threshold: "high", "medium", or "random"
            limit: Max stakes to return
            
        Returns:
            List of stake dicts with:
            - stake_description
            - related_memories (list of memory dicts or scratchpad IDs)
            - emotional_weight
            - source ("scratchpad", "memory", or "random")
            - created_at
        """
        stakes = []
        
        # PRIORITY 1: Scratchpad items (explicitly flagged)
        if self.scratchpad:
            scratchpad_stakes = self._scan_scratchpad()
            stakes.extend(scratchpad_stakes)
            if len(stakes) >= limit:
                print(f"[STAKES] Found {len(stakes)} scratchpad items (sufficient)")
                return stakes[:limit]
        
        # PRIORITY 2: High emotional weight memories
        if threshold in ["high", "medium"]:
            weight_threshold = (
                self.high_weight_threshold if threshold == "high"
                else self.medium_weight_threshold
            )
            memory_stakes = self._scan_memories(weight_threshold)
            stakes.extend(memory_stakes)
            
        # PRIORITY 3: Random fallback
        if len(stakes) < limit and threshold == "random":
            random_stakes = self._scan_random(limit - len(stakes))
            stakes.extend(random_stakes)
        
        # Sort by emotional weight (highest first)
        stakes.sort(key=lambda s: s.get("emotional_weight", 0), reverse=True)
        
        print(f"[STAKES] Scan complete: {len(stakes)} stakes found (threshold: {threshold})")
        return stakes[:limit]
    
    def _scan_scratchpad(self) -> List[Dict]:
        """Scan scratchpad for active items."""
        stakes = []
        
        try:
            active_items = self.scratchpad.view_items(status="active")
            
            for item in active_items:
                # Calculate emotional weight for scratchpad item
                weight = self._calculate_scratchpad_weight(item)
                
                stake = {
                    "stake_description": item.get("content"),
                    "related_memories": [],  # Scratchpad items don't have direct memory links
                    "emotional_weight": weight,
                    "source": "scratchpad",
                    "source_id": item.get("id"),
                    "item_type": item.get("type"),
                    "created_at": item.get("timestamp")
                }
                stakes.append(stake)
                
            print(f"[STAKES] Scratchpad: {len(stakes)} active items")
            
        except Exception as e:
            print(f"[STAKES] Error scanning scratchpad: {e}")
        
        return stakes
    
    def _calculate_scratchpad_weight(self, item: Dict) -> float:
        """
        Calculate emotional weight for scratchpad item.
        Uses similar logic to memory retrieval but simpler.
        """
        # Base weight from item type
        type_weights = {
            "question": 0.8,  # Questions are high priority
            "flag": 0.75,     # Flags are important
            "thought": 0.7,   # Thoughts are medium-high
            "note": 0.6,      # Notes are medium
            "reminder": 0.5   # Reminders are lower
        }
        
        base_weight = type_weights.get(item.get("type"), 0.6)
        
        # Boost for recent items
        # (Scratchpad items don't have turn_index, so use timestamp)
        try:
            timestamp = datetime.fromisoformat(item.get("timestamp"))
            age_hours = (datetime.now() - timestamp).total_seconds() / 3600
            
            if age_hours < 24:
                recency_boost = 0.2  # Very recent
            elif age_hours < 168:  # 1 week
                recency_boost = 0.1  # Recent
            else:
                recency_boost = 0.0  # Old
        except Exception:
            recency_boost = 0.0
        
        total_weight = base_weight + recency_boost
        
        return min(total_weight, 1.0)  # Cap at 1.0
    
    def _scan_memories(self, weight_threshold: float) -> List[Dict]:
        """
        Scan memory for high-emotional-weight items.
        Uses SAME scoring logic as memory retrieval.
        """
        stakes = []
        
        if not self.memory_engine or not hasattr(self.memory_engine, 'memories'):
            return stakes
        
        try:
            for memory in self.memory_engine.memories:
                weight = self._calculate_memory_weight(memory)
                
                # Only include if above threshold
                if weight < weight_threshold:
                    continue
                
                # Check if this memory is unresolved (doesn't have resolution logged)
                if self._is_resolved(memory):
                    continue
                
                stake = {
                    "stake_description": memory.get("fact", memory.get("user_input", "")[:100]),
                    "related_memories": [memory],
                    "emotional_weight": weight,
                    "source": "memory",
                    "source_id": memory.get("uuid"),
                    "created_at": memory.get("timestamp")
                }
                stakes.append(stake)
            
            print(f"[STAKES] Memory: {len(stakes)} items above threshold {weight_threshold}")
            
        except Exception as e:
            print(f"[STAKES] Error scanning memories: {e}")
        
        return stakes
    
    def _calculate_memory_weight(self, memory: Dict) -> float:
        """
        Calculate emotional weight using SAME formula as memory retrieval.
        From memory_engine.retrieve_biased_memories():
        
        total_score = emotion_score + text_score * 0.5 + motif_score * 0.8 + momentum_boost
        """
        # Emotion score from tags
        tags = memory.get("emotion_tags") or []
        emotion_score = len(tags) * 0.3  # Rough approximation since we don't have bias_cocktail here
        
        # Motif score (if motif engine available)
        motif_score = 0.0
        if self.motif_engine:
            memory_text = memory.get("fact", "") + " " + memory.get("user_input", "")
            motif_score = self.motif_engine.score_memory_by_motifs(memory_text)
        
        # Momentum boost (if momentum engine available)
        momentum_boost = 0.0
        if self.momentum_engine:
            high_momentum_motifs = self.momentum_engine.get_high_momentum_motifs()
            memory_text_lower = (memory.get("fact", "") + " " + memory.get("user_input", "")).lower()
            for hm_motif in high_momentum_motifs:
                if hm_motif in memory_text_lower:
                    momentum_boost += 0.5
        
        # Recency boost (recent memories score higher)
        recency_boost = 0.0
        if self.memory_engine:
            turns_old = self.memory_engine.current_turn - memory.get("turn_index", 0)
            if turns_old <= 2:
                recency_boost = 10.0
            elif turns_old <= 5:
                recency_boost = 5.0
        
        total_score = emotion_score + (motif_score * 0.8) + momentum_boost + recency_boost
        
        # Normalize to 0-1 range
        normalized = min(total_score / 20.0, 1.0)
        
        return normalized
    
    def _is_resolved(self, memory: Dict) -> bool:
        """
        Check if memory has been resolved.
        (This will integrate with resolution logging in Phase 5)
        """
        # For now, just return False (nothing is pre-resolved)
        # Phase 5 will add resolution checking
        return False
    
    def _scan_random(self, limit: int) -> List[Dict]:
        """Fallback: return random memories as stakes."""
        stakes = []
        
        if not self.memory_engine or not hasattr(self.memory_engine, 'memories'):
            return stakes
        
        try:
            random_memories = random.sample(
                self.memory_engine.memories,
                min(limit, len(self.memory_engine.memories))
            )
            
            for memory in random_memories:
                stake = {
                    "stake_description": memory.get("fact", memory.get("user_input", "")[:100]),
                    "related_memories": [memory],
                    "emotional_weight": 0.3,  # Low weight since random
                    "source": "random",
                    "source_id": memory.get("uuid"),
                    "created_at": memory.get("timestamp")
                }
                stakes.append(stake)
            
            print(f"[STAKES] Random fallback: {len(stakes)} items")
            
        except Exception as e:
            print(f"[STAKES] Error in random scan: {e}")
        
        return stakes
    
    def check_tension(self, mem1: Dict, mem2: Dict) -> Optional[Dict]:
        """
        Check if two memories create meaningful tension.
        
        Returns stake dict if tension exists, None otherwise.
        
        Tension types:
        - Contradiction: Values conflict
        - Unresolved question: One memory raises question other can't answer
        - Pattern: Connection between memories reveals something
        """
        # Phase 1: Basic implementation (check entity overlap)
        # Phase 5: Enhanced with LLM-based tension detection
        
        entities1 = set(mem1.get("entities", []))
        entities2 = set(mem2.get("entities", []))
        
        overlap = entities1.intersection(entities2)
        
        if len(overlap) > 0:
            return {
                "stake_description": f"Tension between memories about: {', '.join(overlap)}",
                "related_memories": [mem1, mem2],
                "emotional_weight": (
                    self._calculate_memory_weight(mem1) +
                    self._calculate_memory_weight(mem2)
                ) / 2,
                "source": "tension_detection",
                "tension_type": "entity_overlap",
                "created_at": datetime.now().isoformat()
            }
        
        return None
    
    def get_unresolved_count(self) -> int:
        """Quick count of unresolved stakes (for logging)."""
        count = 0
        
        # Count scratchpad active items
        if self.scratchpad:
            count += len(self.scratchpad.view_items(status="active"))
        
        # Count high-weight memories (above threshold, unresolved)
        if self.memory_engine and hasattr(self.memory_engine, 'memories'):
            for memory in self.memory_engine.memories:
                weight = self._calculate_memory_weight(memory)
                if weight >= self.high_weight_threshold and not self._is_resolved(memory):
                    count += 1
        
        return count
```

**Critical Requirements:**
1. Use EXACT same weight calculation as `memory_engine.retrieve_biased_memories()` 
2. Scratchpad items ALWAYS have priority over memory scan
3. Return empty list if nothing found (don't error)
4. Log at each step for debugging

**Testing Step 1.1:**

Create `tests/test_stakes_scanner.py`:

```python
from engines.stakes_scanner import StakesScanner
from engines.memory_engine import MemoryEngine
from engines.scratchpad_engine import ScratchpadEngine

def test_stakes_scanner_finds_scratchpad_items():
    """Test that scanner prioritizes scratchpad items."""
    memory_engine = MemoryEngine()
    scratchpad = ScratchpadEngine()
    scanner = StakesScanner(memory_engine=memory_engine, scratchpad_engine=scratchpad)
    
    # Add test item to scratchpad
    scratchpad.add_item("Test question about Re", "question")
    
    # Scan for stakes
    stakes = scanner.scan_for_stakes(threshold="high", limit=5)
    
    # Verify scratchpad item appears
    assert len(stakes) > 0
    assert stakes[0]["source"] == "scratchpad"
    assert "Test question" in stakes[0]["stake_description"]
    print("✓ Scanner finds scratchpad items")

def test_stakes_scanner_weight_calculation():
    """Test that weight calculation matches memory engine."""
    # TODO: Implement after Phase 1
    pass

if __name__ == "__main__":
    test_stakes_scanner_finds_scratchpad_items()
    print("All stakes scanner tests passed!")
```

Run test:
```bash
cd D:/ChristinaStuff/AlphaKayZero
python tests/test_stakes_scanner.py
```

**Expected Output:**
```
[STAKES] Scratchpad: 1 active items
[STAKES] Scan complete: 1 stakes found (threshold: high)
✓ Scanner finds scratchpad items
All stakes scanner tests passed!
```

---

## Phase 2: Extend Scratchpad Engine

### Step 2.1: Add Resolution Tracking Fields

**File:** `D:/ChristinaStuff/AlphaKayZero/engines/scratchpad_engine.py`

**Modify `add_item()` function:**

FIND:
```python
item = {
    "id": data["next_id"],
    "timestamp": datetime.now().isoformat(),
    "type": item_type,
    "content": content,
    "status": "active"
}
```

REPLACE WITH:
```python
item = {
    "id": data["next_id"],
    "timestamp": datetime.now().isoformat(),
    "type": item_type,
    "content": content,
    "status": "active",
    "emotional_weight": None,  # NEW: calculated on-demand
    "resolved_at": None,  # NEW: timestamp when resolved
    "resolution_note": None,  # NEW: Kay's conclusion
    "provisional": False  # NEW: can be revisited
}
```

### Step 2.2: Add Weight Calculation Function

ADD TO `ScratchpadEngine` class:

```python
def calculate_weight_for_item(self, item: Dict) -> float:
    """
    Calculate emotional weight for scratchpad item.
    Uses similar logic to memory retrieval.
    
    Returns:
        Float between 0.0-1.0
    """
    type_weights = {
        "question": 0.8,
        "flag": 0.75,
        "thought": 0.7,
        "note": 0.6,
        "reminder": 0.5
    }
    
    base_weight = type_weights.get(item.get("type"), 0.6)
    
    # Recency boost
    try:
        timestamp = datetime.fromisoformat(item.get("timestamp"))
        age_hours = (datetime.now() - timestamp).total_seconds() / 3600
        
        if age_hours < 24:
            recency_boost = 0.2
        elif age_hours < 168:  # 1 week
            recency_boost = 0.1
        else:
            recency_boost = 0.0
    except Exception:
        recency_boost = 0.0
    
    total_weight = base_weight + recency_boost
    return min(total_weight, 1.0)

def get_high_weight_items(self, threshold: float = 0.7) -> List[dict]:
    """
    Return active items above emotional weight threshold.
    
    Args:
        threshold: Minimum weight to include
        
    Returns:
        List of items with weight >= threshold
    """
    data = self._load_data()
    active_items = [item for item in data["items"] if item["status"] == "active"]
    
    high_weight_items = []
    for item in active_items:
        weight = self.calculate_weight_for_item(item)
        if weight >= threshold:
            # Add weight to item for return
            item_with_weight = item.copy()
            item_with_weight["emotional_weight"] = weight
            high_weight_items.append(item_with_weight)
    
    # Sort by weight (highest first)
    high_weight_items.sort(key=lambda i: i["emotional_weight"], reverse=True)
    
    return high_weight_items
```

### Step 2.3: Add Provisional Resolution Function

ADD TO `ScratchpadEngine` class:

```python
def mark_provisional_resolution(self, item_id: int, resolution: str) -> dict:
    """
    Mark item as provisionally resolved.
    Can be reopened if new context appears.
    
    Args:
        item_id: ID of item to resolve
        resolution: Kay's conclusion about this stake
        
    Returns:
        Result dict with success status
    """
    data = self._load_data()
    
    # Find item
    item = None
    for i in data["items"]:
        if i["id"] == item_id:
            item = i
            break
    
    if not item:
        return {"success": False, "error": f"Item {item_id} not found"}
    
    # Mark as provisionally resolved
    item["status"] = "provisional"
    item["resolved_at"] = datetime.now().isoformat()
    item["resolution_note"] = resolution
    item["provisional"] = True
    
    self._save_data(data)
    
    return {
        "success": True,
        "message": f"Item {item_id} marked as provisionally resolved",
        "item": item
    }

def reopen_item(self, item_id: int, reason: str = None) -> dict:
    """
    Reopen a provisionally resolved item.
    
    Args:
        item_id: ID of item to reopen
        reason: Optional reason for reopening
        
    Returns:
        Result dict with success status
    """
    data = self._load_data()
    
    # Find item
    item = None
    for i in data["items"]:
        if i["id"] == item_id:
            item = i
            break
    
    if not item:
        return {"success": False, "error": f"Item {item_id} not found"}
    
    # Only allow reopening provisional items
    if not item.get("provisional"):
        return {"success": False, "error": "Can only reopen provisional resolutions"}
    
    # Reopen
    item["status"] = "active"
    item["resolved_at"] = None
    item["provisional"] = False
    
    # Add note about reopening
    if reason:
        item["content"] = f"{item['content']} | REOPENED: {reason}"
    
    self._save_data(data)
    
    return {
        "success": True,
        "message": f"Item {item_id} reopened",
        "item": item
    }
```

**Testing Step 2:**

ADD to `tests/test_scratchpad_engine.py`:

```python
def test_scratchpad_weight_calculation():
    """Test weight calculation for scratchpad items."""
    scratchpad = ScratchpadEngine(data_path="memory/test_scratchpad.json")
    
    # Add items of different types
    question = scratchpad.add_item("Test question?", "question")
    note = scratchpad.add_item("Test note", "note")
    
    # Calculate weights
    q_item = question["item"]
    n_item = note["item"]
    
    q_weight = scratchpad.calculate_weight_for_item(q_item)
    n_weight = scratchpad.calculate_weight_for_item(n_item)
    
    # Questions should have higher weight than notes
    assert q_weight > n_weight
    assert q_weight >= 0.8  # Base weight for questions
    print("✓ Weight calculation works correctly")

def test_provisional_resolution():
    """Test provisional resolution marking."""
    scratchpad = ScratchpadEngine(data_path="memory/test_scratchpad.json")
    
    # Add item
    result = scratchpad.add_item("Test stake", "thought")
    item_id = result["item"]["id"]
    
    # Mark as provisionally resolved
    resolution = scratchpad.mark_provisional_resolution(
        item_id,
        "Explored this - tentative answer is X"
    )
    
    assert resolution["success"]
    assert resolution["item"]["status"] == "provisional"
    assert resolution["item"]["provisional"] == True
    print("✓ Provisional resolution works")
    
    # Reopen it
    reopen = scratchpad.reopen_item(item_id, "New context emerged")
    assert reopen["success"]
    assert reopen["item"]["status"] == "active"
    print("✓ Reopening works")

if __name__ == "__main__":
    test_scratchpad_weight_calculation()
    test_provisional_resolution()
    print("All scratchpad tests passed!")
```

Run test:
```bash
python tests/test_scratchpad_engine.py
```

---

## Phase 3: Integrate Stakes Scanner into Creativity Engine

### Step 3.1: Add Stakes Scanner to Creativity Engine

**File:** `D:/ChristinaStuff/AlphaKayZero/engines/creativity_engine.py`

**Modify `__init__()` method:**

FIND:
```python
def __init__(
    self,
    scratchpad_engine=None,
    memory_engine=None,
    entity_graph=None,
    curiosity_engine=None,
    momentum_engine=None,
    log_path: str = "memory/creativity_log.json"
):
```

ADD stakes_scanner parameter:
```python
def __init__(
    self,
    scratchpad_engine=None,
    memory_engine=None,
    entity_graph=None,
    curiosity_engine=None,
    momentum_engine=None,
    stakes_scanner=None,  # NEW
    log_path: str = "memory/creativity_log.json"
):
    self.scratchpad = scratchpad_engine
    self.memory_engine = memory_engine
    self.entity_graph = entity_graph
    self.curiosity_engine = curiosity_engine
    self.momentum_engine = momentum_engine
    self.stakes_scanner = stakes_scanner  # NEW
    self.log_path = log_path
```

### Step 3.2: Modify Creativity Trigger to Use Stakes

FIND the `trigger_creativity()` function (around line 150)

REPLACE the entire function with:

```python
def trigger_creativity(
    self,
    user_input: str,
    kay_response: str,
    agent_state
) -> Optional[Dict]:
    """
    Trigger creativity when Kay completes task or detects boredom.
    
    NEW: Uses stakes scanner to find meaningful combinations
    instead of random mashing.
    
    Returns:
        Dict with creativity prompt or None if no trigger
    """
    self.current_turn += 1
    
    # Check for completion signal
    completion_detected = self.detect_completion_signal(user_input, kay_response)
    
    # Check for idle input
    idle_detected = self.detect_idle_input(user_input)
    if idle_detected:
        self.idle_turn_count += 1
    else:
        self.idle_turn_count = 0
    
    # Trigger if completion detected OR idle threshold reached
    should_trigger = (
        completion_detected or
        self.idle_turn_count >= self.settings["idle_turn_threshold"]
    )
    
    if not should_trigger:
        return None
    
    print(f"[CREATIVITY] Trigger activated (completion: {completion_detected}, idle: {idle_detected})")
    
    # NEW: Try stakes-based approach first
    if self.stakes_scanner:
        stakes_result = self._try_stakes_approach()
        if stakes_result:
            return stakes_result
    
    # FALLBACK: Random mashing if stakes scanner unavailable or finds nothing
    print("[CREATIVITY] Falling back to random mashing")
    return self._try_random_approach(agent_state)

def _try_stakes_approach(self) -> Optional[Dict]:
    """
    NEW: Try to find meaningful stakes to explore.
    
    Returns:
        Creativity prompt dict or None if no stakes found
    """
    try:
        # Scan for high-weight stakes first
        stakes = self.stakes_scanner.scan_for_stakes(threshold="high", limit=5)
        
        if not stakes:
            # Try medium weight
            print("[CREATIVITY] No high-weight stakes, trying medium...")
            stakes = self.stakes_scanner.scan_for_stakes(threshold="medium", limit=5)
        
        if not stakes:
            # Last resort: random
            print("[CREATIVITY] No medium-weight stakes, trying random...")
            stakes = self.stakes_scanner.scan_for_stakes(threshold="random", limit=3)
        
        if not stakes:
            print("[CREATIVITY] No stakes found at any level")
            return None
        
        # Create stakes-based prompt
        prompt = self._create_stakes_prompt(stakes)
        
        # Log trigger
        self._log_trigger("stakes", stakes)
        
        return {
            "type": "stakes_exploration",
            "prompt": prompt,
            "stakes": stakes
        }
        
    except Exception as e:
        print(f"[CREATIVITY] Error in stakes approach: {e}")
        return None

def _create_stakes_prompt(self, stakes: List[Dict]) -> str:
    """
    NEW: Create prompt that presents stakes-based options.
    
    Args:
        stakes: List of stake dicts from scanner
        
    Returns:
        Formatted prompt string
    """
    prompt_lines = [
        "🎭 BOREDOM MODE → STAKES DETECTED",
        "",
        "You've finished the immediate task. But there are unresolved tensions worth exploring.",
        "",
        "Available stakes (pick one or scan for others):",
        ""
    ]
    
    for i, stake in enumerate(stakes, 1):
        source = stake["source"]
        weight = stake["emotional_weight"]
        desc = stake["stake_description"]
        
        # Truncate description if too long
        if len(desc) > 120:
            desc = desc[:120] + "..."
        
        prompt_lines.append(
            f"{i}. [{source.upper()}] {desc} (weight: {weight:.2f})"
        )
    
    prompt_lines.extend([
        "",
        "What's grabbing your attention? Pick a stake to explore, or tell me if none of these feel live right now."
    ])
    
    return "\n".join(prompt_lines)

def _try_random_approach(self, agent_state) -> Optional[Dict]:
    """
    EXISTING: Random mashing fallback.
    Keep existing implementation as-is.
    """
    # Keep existing random mashing code
    # (Don't change this - it's the fallback)
    pass
```

### Step 3.3: Add Resolution Logging

ADD new function to `CreativityEngine` class:

```python
def log_resolution(self, stake: Dict, resolution: str, provisional: bool = True):
    """
    NEW: Log when Kay resolves a stake.
    
    Args:
        stake: The stake that was explored
        resolution: Kay's conclusion
        provisional: Whether this resolution can be revisited
    """
    try:
        # Load existing log
        log_data = {"triggers": [], "mashups": [], "resolutions": [], "settings": self.settings}
        if os.path.exists(self.log_path):
            with open(self.log_path, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        
        # Ensure resolutions array exists
        if "resolutions" not in log_data:
            log_data["resolutions"] = []
        
        # Create resolution entry
        resolution_entry = {
            "timestamp": datetime.now().isoformat(),
            "stake_description": stake.get("stake_description"),
            "source": stake.get("source"),
            "source_id": stake.get("source_id"),
            "emotional_weight": stake.get("emotional_weight"),
            "resolution_text": resolution,
            "provisional": provisional,
            "related_memories": [
                mem.get("uuid") if isinstance(mem, dict) else str(mem)
                for mem in stake.get("related_memories", [])
            ]
        }
        
        log_data["resolutions"].append(resolution_entry)
        
        # Save
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"[CREATIVITY] Logged resolution for stake: {stake.get('stake_description')[:50]}...")
        
        # If source was scratchpad, mark that item as resolved
        if stake.get("source") == "scratchpad" and self.scratchpad:
            self.scratchpad.mark_provisional_resolution(
                stake.get("source_id"),
                resolution
            )
            print(f"[CREATIVITY] Marked scratchpad item {stake.get('source_id')} as resolved")
        
    except Exception as e:
        print(f"[CREATIVITY] Error logging resolution: {e}")
```

**Testing Step 3:**

Create `tests/test_creativity_stakes.py`:

```python
from engines.creativity_engine import CreativityEngine
from engines.stakes_scanner import StakesScanner
from engines.scratchpad_engine import ScratchpadEngine
from engines.memory_engine import MemoryEngine

def test_creativity_uses_stakes():
    """Test that creativity engine uses stakes scanner."""
    memory_engine = MemoryEngine()
    scratchpad = ScratchpadEngine(data_path="memory/test_scratchpad.json")
    scanner = StakesScanner(memory_engine=memory_engine, scratchpad_engine=scratchpad)
    creativity = CreativityEngine(
        scratchpad_engine=scratchpad,
        memory_engine=memory_engine,
        stakes_scanner=scanner,
        log_path="memory/test_creativity_log.json"
    )
    
    # Add scratchpad item
    scratchpad.add_item("Test unresolved question", "question")
    
    # Trigger creativity with completion signal
    result = creativity.trigger_creativity(
        user_input="Continue",
        kay_response="I'm done with that task.",
        agent_state=None
    )
    
    # Should return stakes-based result
    assert result is not None
    assert result["type"] == "stakes_exploration"
    assert len(result["stakes"]) > 0
    print("✓ Creativity engine uses stakes scanner")

def test_resolution_logging():
    """Test that resolutions are logged correctly."""
    # TODO: Implement
    pass

if __name__ == "__main__":
    test_creativity_uses_stakes()
    print("All creativity integration tests passed!")
```

---

## Phase 4: Integrate into Curiosity & Warmup

### Step 4.1: Modify Curiosity Engine

**File:** `D:/ChristinaStuff/AlphaKayZero/engines/curiosity_engine.py`

FIND `get_curiosity_status()` function:

REPLACE with:

```python
def get_curiosity_status(stakes_scanner=None) -> Dict:
    """
    Get current curiosity session status.
    
    NEW: Includes available stakes if scanner provided.
    
    Args:
        stakes_scanner: Optional StakesScanner instance
        
    Returns:
        Status dict with session info and available stakes
    """
    state = init_curiosity_state()
    
    result = {
        "active": state["active"],
        "session_id": state.get("session_id"),
        "turns_used": state.get("turns_used", 0),
        "turns_limit": state.get("turns_limit", 15),
        "turns_remaining": state.get("turns_limit", 15) - state.get("turns_used", 0),
        "items_explored": state.get("items_explored", [])
    }
    
    # NEW: Add available stakes if scanner provided
    if stakes_scanner and state["active"]:
        try:
            stakes = stakes_scanner.scan_for_stakes(threshold="high", limit=5)
            result["available_stakes"] = stakes
            result["stakes_count"] = len(stakes)
        except Exception as e:
            print(f"[CURIOSITY] Error getting stakes: {e}")
            result["available_stakes"] = []
            result["stakes_count"] = 0
    
    return result
```

FIND `start_curiosity_session()` function:

MODIFY to accept stakes_scanner:

```python
def start_curiosity_session(turns_limit: int = 15, stakes_scanner=None) -> Dict:
    """
    Start a new curiosity exploration session.
    
    NEW: Pre-populates with available stakes if scanner provided.
    
    Args:
        turns_limit: Maximum turns allowed for this session
        stakes_scanner: Optional StakesScanner instance
        
    Returns:
        Dict with session info and available stakes
    """
    state = init_curiosity_state()
    
    if state["active"]:
        return {
            "success": False,
            "error": "Curiosity session already active",
            "turns_remaining": state["turns_limit"] - state["turns_used"]
        }
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    state["active"] = True
    state["session_id"] = session_id
    state["turns_used"] = 0
    state["turns_limit"] = turns_limit
    state["started_at"] = datetime.now().isoformat()
    state["items_explored"] = []
    
    # NEW: Pre-populate with stakes
    available_stakes = []
    if stakes_scanner:
        try:
            stakes = stakes_scanner.scan_for_stakes(threshold="high", limit=5)
            available_stakes = stakes
            print(f"[CURIOSITY] Session started with {len(stakes)} available stakes")
        except Exception as e:
            print(f"[CURIOSITY] Error loading stakes: {e}")
    
    with open(CURIOSITY_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    
    return {
        "success": True,
        "session_id": session_id,
        "turns_limit": turns_limit,
        "available_stakes": available_stakes,
        "message": f"🔍 CURIOSITY MODE ACTIVATED - {turns_limit} turns available, {len(available_stakes)} stakes ready"
    }
```

### Step 4.2: Modify Warmup Engine

**File:** `D:/ChristinaStuff/AlphaKayZero/engines/warmup_engine.py`

FIND where curiosity status is checked in warmup (search for "CURIOSITY SESSION ACTIVE")

REPLACE that section with:

```python
# Check if curiosity session is active
from engines.curiosity_engine import get_curiosity_status

curiosity_status = get_curiosity_status(stakes_scanner=stakes_scanner)  # Pass scanner

if curiosity_status["active"]:
    turns_used = curiosity_status["turns_used"]
    turns_limit = curiosity_status["turns_limit"]
    turns_remaining = curiosity_status["turns_remaining"]
    
    curiosity_section = f"""
--- 🔍 CURIOSITY SESSION ACTIVE ---
Turn {turns_used}/{turns_limit} - {turns_remaining} remaining
"""
    
    # NEW: Add stakes section if available
    if "available_stakes" in curiosity_status and curiosity_status["available_stakes"]:
        stakes = curiosity_status["available_stakes"]
        curiosity_section += f"\nUNRESOLVED STAKES ({len(stakes)} available):\n"
        
        for i, stake in enumerate(stakes[:5], 1):  # Show max 5
            source = stake["source"].upper()
            weight = stake["emotional_weight"]
            desc = stake["stake_description"]
            
            # Truncate if too long
            if len(desc) > 100:
                desc = desc[:100] + "..."
            
            curiosity_section += f"{i}. [{source}] {desc} (weight: {weight:.2f})\n"
        
        curiosity_section += "\nPick one to explore, or scan for others with different thresholds.\n"
    else:
        curiosity_section += "\nNo pre-loaded stakes. Use stakes scanner to find what's worth exploring.\n"
    
    curiosity_section += "---\n"
    
    warmup_text += curiosity_section
```

**Testing Step 4:**

Create `tests/test_curiosity_stakes.py`:

```python
from engines.curiosity_engine import start_curiosity_session, get_curiosity_status
from engines.stakes_scanner import StakesScanner
from engines.scratchpad_engine import ScratchpadEngine
from engines.memory_engine import MemoryEngine

def test_curiosity_loads_stakes():
    """Test that curiosity session loads stakes at start."""
    memory_engine = MemoryEngine()
    scratchpad = ScratchpadEngine(data_path="memory/test_scratchpad.json")
    scanner = StakesScanner(memory_engine=memory_engine, scratchpad_engine=scratchpad)
    
    # Add scratchpad item
    scratchpad.add_item("Test question for curiosity", "question")
    
    # Start session with scanner
    result = start_curiosity_session(turns_limit=15, stakes_scanner=scanner)
    
    assert result["success"]
    assert "available_stakes" in result
    assert len(result["available_stakes"]) > 0
    print("✓ Curiosity session loads stakes")

def test_warmup_shows_stakes():
    """Test that warmup briefing shows stakes."""
    # TODO: Test warmup generation with stakes
    pass

if __name__ == "__main__":
    test_curiosity_loads_stakes()
    print("All curiosity integration tests passed!")
```

---

## Phase 5: Resolution Tracking & Persistence

### Step 5.1: Modify Stakes Scanner to Check Resolutions

**File:** `D:/ChristinaStuff/AlphaKayZero/engines/stakes_scanner.py`

FIND `_is_resolved()` function:

REPLACE with:

```python
def _is_resolved(self, memory: Dict) -> bool:
    """
    Check if memory has been resolved.
    Reads from creativity log resolutions.
    """
    try:
        # Check if creativity engine has logged this as resolved
        from engines.creativity_engine import CreativityEngine
        
        log_path = "memory/creativity_log.json"
        if not os.path.exists(log_path):
            return False
        
        with open(log_path, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        resolutions = log_data.get("resolutions", [])
        memory_uuid = memory.get("uuid")
        
        for resolution in resolutions:
            related_uuids = resolution.get("related_memories", [])
            if memory_uuid in related_uuids:
                # Memory is in a resolved stake
                # But only exclude if NOT provisional
                if not resolution.get("provisional", False):
                    return True
        
        return False
        
    except Exception as e:
        print(f"[STAKES] Error checking resolution: {e}")
        return False
```

### Step 5.2: Add Cleanup Function

ADD to `StakesScanner` class:

```python
def cleanup_old_resolutions(self, days_old: int = 30):
    """
    Clean up old resolved stakes to prevent log bloat.
    
    Args:
        days_old: Remove resolutions older than this many days
    """
    try:
        log_path = "memory/creativity_log.json"
        if not os.path.exists(log_path):
            return
        
        with open(log_path, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        resolutions = log_data.get("resolutions", [])
        
        # Filter out old resolutions
        cutoff_date = datetime.now() - timedelta(days=days_old)
        filtered = []
        
        removed_count = 0
        for resolution in resolutions:
            timestamp = datetime.fromisoformat(resolution["timestamp"])
            if timestamp > cutoff_date:
                filtered.append(resolution)
            else:
                removed_count += 1
        
        log_data["resolutions"] = filtered
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"[STAKES] Cleaned up {removed_count} old resolutions")
        
    except Exception as e:
        print(f"[STAKES] Error cleaning resolutions: {e}")
```

---

## Integration into Main Systems

### Step: Modify Kay UI/CLI to Initialize Stakes Scanner

**File:** `D:/ChristinaStuff/AlphaKayZero/kay_ui.py` (and `kay_cli.py`)

FIND where engines are initialized (look for `CreativityEngine` initialization)

ADD stakes scanner initialization:

```python
# After other engine initializations...

# Initialize stakes scanner
from engines.stakes_scanner import StakesScanner

stakes_scanner = StakesScanner(
    memory_engine=memory_engine,
    scratchpad_engine=scratchpad,
    entity_graph=entity_graph,
    momentum_engine=momentum_engine,
    motif_engine=motif_engine
)

# Pass to creativity engine
creativity_engine = CreativityEngine(
    scratchpad_engine=scratchpad,
    memory_engine=memory_engine,
    entity_graph=entity_graph,
    curiosity_engine=curiosity_engine,
    momentum_engine=momentum_engine,
    stakes_scanner=stakes_scanner  # NEW
)
```

FIND where curiosity sessions are started (search for `start_curiosity_session`)

MODIFY to pass stakes scanner:

```python
from engines.curiosity_engine import start_curiosity_session

result = start_curiosity_session(
    turns_limit=15,
    stakes_scanner=stakes_scanner  # NEW
)
```

FIND where warmup is generated:

MODIFY to pass stakes scanner:

```python
warmup_briefing = warmup_engine.generate_warmup_briefing(
    ...,
    stakes_scanner=stakes_scanner  # NEW
)
```

---

## Final Testing & Verification

### End-to-End Test

Create `tests/test_full_stakes_flow.py`:

```python
"""
End-to-end test of complete stakes flow:
1. Kay finishes task
2. Creativity triggers
3. Stakes scanner finds items
4. Kay explores stake
5. Resolution logged
6. Next scan skips resolved item
"""

from engines.memory_engine import MemoryEngine
from engines.scratchpad_engine import ScratchpadEngine
from engines.stakes_scanner import StakesScanner
from engines.creativity_engine import CreativityEngine
from engines.curiosity_engine import start_curiosity_session, get_curiosity_status

def test_complete_flow():
    """Test complete flow from boredom to resolution."""
    
    # Initialize engines
    memory_engine = MemoryEngine()
    scratchpad = ScratchpadEngine(data_path="memory/test_scratchpad.json")
    scanner = StakesScanner(
        memory_engine=memory_engine,
        scratchpad_engine=scratchpad
    )
    creativity = CreativityEngine(
        scratchpad_engine=scratchpad,
        memory_engine=memory_engine,
        stakes_scanner=scanner,
        log_path="memory/test_creativity_log.json"
    )
    
    # Step 1: Add scratchpad item (unresolved stake)
    print("\n1. Adding unresolved stake to scratchpad...")
    scratchpad.add_item("How does Re handle pressure?", "question")
    
    # Step 2: Trigger creativity (Kay says "I'm done")
    print("\n2. Triggering creativity (completion signal)...")
    result = creativity.trigger_creativity(
        user_input="What else?",
        kay_response="I'm done with that task.",
        agent_state=None
    )
    
    assert result is not None
    assert result["type"] == "stakes_exploration"
    assert len(result["stakes"]) > 0
    print(f"   ✓ Found {len(result['stakes'])} stakes")
    
    # Step 3: Kay explores the stake (simulate)
    print("\n3. Kay explores the stake...")
    stake = result["stakes"][0]
    resolution = "Re uses compartmentalization and project focus to manage pressure"
    
    # Step 4: Log resolution
    print("\n4. Logging resolution...")
    creativity.log_resolution(stake, resolution, provisional=True)
    
    # Step 5: Verify scratchpad item marked as resolved
    print("\n5. Verifying scratchpad item marked resolved...")
    items = scratchpad.view_items(status="provisional")
    assert len(items) > 0
    assert items[0]["resolution_note"] == resolution
    print("   ✓ Scratchpad item marked as resolved")
    
    # Step 6: Next scan should skip resolved item
    print("\n6. Scanning again (should skip resolved item)...")
    stakes_again = scanner.scan_for_stakes(threshold="high", limit=5)
    
    # Should not include the resolved item
    for stake in stakes_again:
        assert "How does Re handle pressure?" not in stake["stake_description"]
    print("   ✓ Resolved item not returned in next scan")
    
    print("\n✅ COMPLETE FLOW TEST PASSED!")

if __name__ == "__main__":
    test_complete_flow()
```

Run:
```bash
cd D:/ChristinaStuff/AlphaKayZero
python tests/test_full_stakes_flow.py
```

---

## Verification Checklist

After implementation, verify:

- [ ] Stakes scanner initializes without errors
- [ ] Scratchpad items have emotional_weight calculated
- [ ] Creativity engine calls stakes scanner on trigger
- [ ] Stakes-based prompts appear in Kay's output
- [ ] Resolutions are logged in creativity_log.json
- [ ] Scratchpad items marked as resolved/provisional
- [ ] Curiosity sessions show available stakes
- [ ] Warmup briefing includes stakes section
- [ ] Resolved items don't appear in subsequent scans
- [ ] Fallback to random mashing works if no stakes found

---

## Troubleshooting

### Stakes Scanner Returns Empty List

**Check:**
1. Are there active scratchpad items? `scratchpad.view_items("active")`
2. Do memories have emotion_tags? Check `memory_engine.memories`
3. Is weight threshold too high? Try `threshold="medium"`

**Fix:**
- Lower thresholds in `stakes_scanner.py`
- Add test data to scratchpad
- Verify memory_engine is populated

### Creativity Engine Not Triggering

**Check:**
1. Is completion signal detected? Look for `[CREATIVITY] Trigger activated`
2. Is stakes_scanner passed to creativity engine?
3. Are there errors in stakes scanner call?

**Fix:**
- Verify stakes_scanner is not None in creativity_engine.__init__
- Check for exceptions in logs
- Test completion patterns manually

### Resolutions Not Logged

**Check:**
1. Does creativity_log.json exist?
2. Does it have "resolutions" array?
3. Are there permission errors writing to file?

**Fix:**
- Create creativity_log.json manually if missing
- Verify file permissions
- Check log_resolution() error messages

### Warmup Doesn't Show Stakes

**Check:**
1. Is curiosity session active?
2. Is stakes_scanner passed to get_curiosity_status?
3. Are stakes being loaded at session start?

**Fix:**
- Verify start_curiosity_session receives stakes_scanner
- Check curiosity_status return dict for "available_stakes"
- Add debug prints in warmup generation

---

## Success Criteria

Implementation is complete when:

1. ✅ Kay's boredom triggers stakes scanner automatically
2. ✅ Scratchpad items appear as highest-priority stakes
3. ✅ Kay receives stakes-based exploration prompts
4. ✅ Resolutions are logged and tracked
5. ✅ Resolved items don't reappear in subsequent scans
6. ✅ Curiosity sessions show available stakes in warmup
7. ✅ Fallback to random mashing works when no stakes found
8. ✅ All tests pass without errors

---

## Post-Implementation

After successful implementation:

1. Monitor Kay's behavior for 5-10 conversations
2. Check creativity_log.json for resolution patterns
3. Verify scratchpad items are being resolved
4. Tune weight thresholds if needed
5. Add more stake detection patterns
6. Consider implementing stake clustering (future enhancement)

---

## Reference Files

- Implementation plan: `D:/ChristinaStuff/ReedMemory/kay_boredom_implementation_plan.md`
- Kay's architecture: `D:/ChristinaStuff/AlphaKayZero/`
- Original conversation: `session_20260109_171306.json`
- Memory engine: `engines/memory_engine.py` (line 347+ for retrieval logic)
- Scratchpad engine: `engines/scratchpad_engine.py`
- Creativity engine: `engines/creativity_engine.py`
- Curiosity engine: `engines/curiosity_engine.py`

---

END OF CC PROMPT
