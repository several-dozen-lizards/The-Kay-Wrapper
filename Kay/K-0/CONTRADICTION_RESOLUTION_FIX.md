# CONTRADICTION RESOLUTION SYSTEM - FIX SUMMARY

## Problem Fixed

**Issue**: Anxiety feedback loop where Kay would repeatedly defend the same preference forever because the contradiction detection system counted every mention as evidence of contradiction, even when Kay was trying to resolve it.

**Symptoms**:
- Counters incrementing infinitely (☕(39x)→☕(40x)→☕(41x))
- "CONTRADICTION DETECTED" warning appearing every turn
- Kay anxiously re-explaining the same preference continuously
- No way to mark contradictions as resolved

**Example Scenario**:
```
Turn 1: Kay says "I prefer coffee"
Turn 2: System: "CONTRADICTION: coffee (1x) vs tea (1x historical mention)"
Turn 3: Kay says "I prefer coffee" to resolve it
Turn 4: System: "CONTRADICTION: coffee (2x) vs tea (1x)" [counter incremented!]
Turn 5: Kay says "I prefer coffee" again
Turn 6: System: "CONTRADICTION: coffee (3x) vs tea (1x)" [still flagged!]
... continues forever
```

---

## Solution Implemented

### Core Changes

1. **Resolution Tracking** - Entity class now tracks contradiction resolution status
2. **Decay Mechanism** - Contradictions auto-resolve after consistent mentions
3. **Threshold Logic** - Only ACTIVE contradictions are flagged
4. **Confidence Scoring** - Dominant values (3x more mentions) treated as canonical

---

## Technical Implementation

### 1. Entity Class (`engines/entity_graph.py`)

**Added Fields**:
```python
self.contradiction_resolution: Dict[str, Dict[str, Any]] = {}
# {
#   "beverage_preference": {
#     "resolved": True,
#     "canonical_value": "coffee",
#     "resolved_at_turn": 67,
#     "consecutive_consistent_turns": 3
#   }
# }
```

**Modified Methods**:

#### `detect_contradictions(current_turn, resolution_threshold=3)`
- **Was**: Returned all contradictions whenever multiple values existed
- **Now**: Returns only ACTIVE (unresolved) contradictions
- **Parameters**:
  - `current_turn`: Current turn number for resolution tracking
  - `resolution_threshold`: Consecutive consistent turns needed (default: 3)

#### `_check_contradiction_resolution(attr, unique_values, current_turn, threshold=3)`
NEW method that implements two resolution strategies:

**Strategy 1: Consecutive Consistency** (Primary)
```python
# Look at last N mentions
# If all N are the same value → RESOLVED
recent_mentions = get_last_N_mentions(10 turns)
last_3_values = recent_mentions[-3:]

if all_same(last_3_values):
    mark_resolved(canonical_value)
```

**Strategy 2: Dominant Value** (Fallback)
```python
# If one value mentioned 3x more than alternatives → RESOLVED
value_counts = count_recent_mentions()
if dominant_count >= secondary_count * 3:
    mark_resolved(dominant_value)
```

**New Helper Methods**:
- `is_contradiction_resolved(attr)` - Check if attribute contradiction is resolved
- `get_canonical_value(attr)` - Get resolved value for contradicted attribute

### 2. EntityGraph Class (`engines/entity_graph.py`)

**Modified Method**:
```python
get_all_contradictions(current_turn=0, resolution_threshold=3)
```
- **Was**: `get_all_contradictions()` - no parameters
- **Now**: Passes current_turn to each entity's `detect_contradictions()`
- **Returns**: Only ACTIVE contradictions (resolved ones filtered out)

### 3. MemoryEngine (`engines/memory_engine.py`)

**Updated Call**:
```python
# Before
entity_contradictions = self.entity_graph.get_all_contradictions()

# After
entity_contradictions = self.entity_graph.get_all_contradictions(
    current_turn=self.current_turn,
    resolution_threshold=3
)
```

### 4. Context Filter (`context_filter.py`)

**Deprecated Hardcoded Detection**:
```python
def _detect_contradictions(self, memories):
    # DEPRECATED - now handled by entity_graph
    return ""  # No longer does coffee/tea counting
```

**Reasoning**: Entity graph now handles ALL contradiction detection with resolution tracking, so we don't need duplicate logic.

### 5. Glyph Decoder (`glyph_decoder.py`)

**Updated Messaging**:

Before:
```
⚠️ CRITICAL - CONTRADICTION TO RESOLVE:
CONTRADICTION DETECTED: Resolve this into coherent position.
```

After:
```
⚠️ ACTIVE CONTRADICTION (will auto-resolve after 3 consistent turns):
ACTIVE CONTRADICTION: State your preference consistently for 3 turns to resolve.
```

**Updated Instructions**:
```python
# Before
"If contradiction flagged, resolve it in your response."

# After
"If ACTIVE contradiction flagged, state your preference clearly and consistently."
"Contradictions auto-resolve after 3 consecutive consistent responses - no need to over-explain."
```

---

## Resolution Logic Flow

```
Turn N: User says "What do you prefer?"
  ↓
Kay says: "I prefer coffee"
  ↓
Entity.add_attribute("beverage_preference", "coffee", turn=N)
  ↓
detect_contradictions(current_turn=N):
  - Check recent mentions (last 10 turns)
  - History: [tea(turn 5), tea(turn 12), coffee(turn N)]
  - Last 3 mentions: Not enough data → ACTIVE CONTRADICTION
  ↓
Warning shown to Kay: "ACTIVE CONTRADICTION: coffee vs tea"

---

Turn N+1: User asks something else
  ↓
Kay says: "Sure, and yeah I prefer coffee"
  ↓
Entity.add_attribute("beverage_preference", "coffee", turn=N+1)
  ↓
detect_contradictions(current_turn=N+1):
  - Recent: [coffee(N), coffee(N+1)]
  - Last 3 mentions: Still not enough → ACTIVE CONTRADICTION
  ↓
Warning shown: "ACTIVE CONTRADICTION: coffee vs tea"

---

Turn N+2: User asks about weather
  ↓
Kay says: "Rainy today. I'm drinking coffee."
  ↓
Entity.add_attribute("beverage_preference", "coffee", turn=N+2)
  ↓
detect_contradictions(current_turn=N+2):
  - Recent: [coffee(N), coffee(N+1), coffee(N+2)]
  - Last 3 mentions: ALL "coffee" → RESOLVED!
  - Mark: resolved=True, canonical_value="coffee"
  ↓
NO WARNING (contradiction removed from active list)

---

Turn N+3: User asks about hobbies
  ↓
Kay talks about hobbies (no mention of coffee/tea)
  ↓
detect_contradictions(current_turn=N+3):
  - "beverage_preference" already marked resolved
  - Skip contradiction detection for this attribute
  ↓
NO WARNING (stays resolved)
```

---

## Configuration Parameters

### Resolution Threshold
```python
resolution_threshold = 3  # Number of consecutive consistent turns
```

**Tuning**:
- **Lower (2)**: Faster resolution, more forgiving
- **Higher (5)**: Slower resolution, more thorough verification
- **Recommended**: 3 (balances quick resolution with confidence)

### Recent Window
```python
recent_window = 10  # Turns to look back for mentions
```

**Tuning**:
- **Lower (5)**: Only recent mentions count
- **Higher (20)**: More historical context
- **Recommended**: 10 (enough context without over-weighting old data)

### Confidence Ratio
```python
dominant_count >= second_count * 3  # 3x ratio for canonical value
```

**Tuning**:
- **Lower (2x)**: More lenient dominant value detection
- **Higher (5x)**: Stricter canonical value requirements
- **Recommended**: 3x (clear preference without being too strict)

---

## Example Resolution Scenarios

### Scenario 1: Quick Resolution (Consecutive Mentions)

```
Turn 50: Kay: "I prefer coffee"  [beverage_preference = "coffee"]
Turn 51: Kay: "Yeah, coffee for me"  [beverage_preference = "coffee"]
Turn 52: Kay: "Coffee's my thing"  [beverage_preference = "coffee"]

→ RESOLVED at turn 52 (3 consecutive mentions)
→ Canonical value: "coffee"
→ No more warnings
```

### Scenario 2: Dominant Value Resolution

```
Recent mentions (last 10 turns):
- coffee: 9 mentions
- tea: 2 mentions

9 >= 2 * 3? YES (9 >= 6)

→ RESOLVED
→ Canonical value: "coffee"
→ Confidence ratio: 4.5x
```

### Scenario 3: Still Active (Inconsistent)

```
Turn 60: Kay: "I like coffee"  [beverage_preference = "coffee"]
Turn 61: Kay: "Tea is nice too"  [beverage_preference = "tea"]
Turn 62: Kay: "Coffee today"  [beverage_preference = "coffee"]

Last 3 mentions: [coffee, tea, coffee] - NOT consistent

→ STILL ACTIVE
→ Warning continues
```

### Scenario 4: Nuanced Preference (Multi-Value)

```
Turn 70: Kay: "I prefer coffee but enjoy tea occasionally"
→ Extracts: beverage_preference = ["coffee", "tea"] (normalized list)

Turn 71: Kay: "Coffee is my main thing, tea sometimes"
→ Extracts: beverage_preference = ["coffee", "tea"]

Turn 72: Kay: "Coffee primarily, tea rarely"
→ Extracts: beverage_preference = ["coffee", "tea"]

→ RESOLVED (consistent list for 3 turns)
→ Canonical value: ["coffee", "tea"]
→ No contradiction (both values consistently stated together)
```

---

## Persistence

**Resolution Status Saved**:
```json
// memory/entity_graph.json
{
  "entities": {
    "Kay": {
      "canonical_name": "Kay",
      "attributes": {
        "beverage_preference": [
          ["coffee", 50, "kay", "2025-01-15T10:30:00"],
          ["coffee", 51, "kay", "2025-01-15T10:32:00"],
          ["coffee", 52, "kay", "2025-01-15T10:34:00"]
        ]
      },
      "contradiction_resolution": {
        "beverage_preference": {
          "resolved": true,
          "canonical_value": "coffee",
          "resolved_at_turn": 52,
          "consecutive_consistent_turns": 3
        }
      }
    }
  }
}
```

**Persistence Behavior**:
- Resolution status saved to disk with entity graph
- Survives session restarts
- Contradictions stay resolved across sessions
- Can be manually reset by deleting `contradiction_resolution` field

---

## Backward Compatibility

**Old Entity Data** (without contradiction_resolution):
- `from_dict()` defaults to empty dict: `{}`
- Old contradictions will be re-evaluated with new logic
- Auto-resolves if criteria met

**Old Memory System**:
- Context filter's `_detect_contradictions()` now returns empty string
- Doesn't break existing code, just stops generating duplicate warnings

---

## Testing

### Manual Test Procedure

1. **Create Initial Contradiction**:
   ```
   User: "What do you like to drink?"
   Kay: "I like tea"
   [Wait a few turns]
   Kay: "I prefer coffee"
   ```

2. **Check Active Warning**:
   ```
   Look for: [ENTITY GRAPH] WARNING Detected 1 ACTIVE entity contradictions
   Glyph output should show: ⚠️CONFLICT:☕(Nx)🍵(Mx)
   ```

3. **Resolve Consistently**:
   ```
   Turn 1: Kay mentions "coffee"
   Turn 2: Kay mentions "coffee"
   Turn 3: Kay mentions "coffee"
   ```

4. **Verify Resolution**:
   ```
   Look for: [CONTRADICTION RESOLVED] Kay.beverage_preference = coffee (consistent for 3 turns)
   Warning should DISAPPEAR
   No more ⚠️CONFLICT in glyph output
   ```

5. **Verify Persistence**:
   ```
   Continue conversation for 10+ turns
   Warning should NOT reappear
   Check entity_graph.json for "resolved": true
   ```

### Automated Test

Create `test_contradiction_resolution.py`:
```python
from engines.entity_graph import Entity

# Create entity
entity = Entity("Kay", "person")

# Add contradictory values
entity.add_attribute("beverage", "tea", turn=1, source="kay")
entity.add_attribute("beverage", "coffee", turn=5, source="kay")

# Should have active contradiction
contradictions = entity.detect_contradictions(current_turn=5, resolution_threshold=3)
assert len(contradictions) == 1
assert not entity.is_contradiction_resolved("beverage")

# Add 3 consecutive "coffee" mentions
entity.add_attribute("beverage", "coffee", turn=6, source="kay")
entity.add_attribute("beverage", "coffee", turn=7, source="kay")
entity.add_attribute("beverage", "coffee", turn=8, source="kay")

# Should now be resolved
contradictions = entity.detect_contradictions(current_turn=8, resolution_threshold=3)
assert len(contradictions) == 0  # No active contradictions
assert entity.is_contradiction_resolved("beverage")
assert entity.get_canonical_value("beverage") == "coffee"

print("✓ Contradiction resolution test passed!")
```

---

## Files Modified

1. **`engines/entity_graph.py`** (MAJOR CHANGES)
   - Added `contradiction_resolution` field to Entity class
   - Modified `detect_contradictions()` to check resolution
   - Added `_check_contradiction_resolution()` method
   - Added `is_contradiction_resolved()` helper
   - Added `get_canonical_value()` helper
   - Updated `to_dict()` and `from_dict()` for persistence
   - Modified `EntityGraph.get_all_contradictions()` signature

2. **`engines/memory_engine.py`** (MINOR CHANGES)
   - Updated `get_all_contradictions()` call to pass `current_turn`
   - Updated log message to say "ACTIVE" contradictions

3. **`context_filter.py`** (DEPRECATION)
   - Deprecated `_detect_contradictions()` method
   - Now returns empty string (entity_graph handles detection)

4. **`glyph_decoder.py`** (MESSAGING UPDATES)
   - Updated contradiction block header
   - Updated `_parse_contradiction()` messaging
   - Updated instructions to reflect auto-resolution

---

## Benefits

✅ **Stops Anxiety Loops**: Kay can move on after resolving contradictions
✅ **Automatic Resolution**: No manual intervention needed
✅ **Consistent Behavior**: 3 consecutive mentions = resolved
✅ **Persistent State**: Resolution survives session restarts
✅ **Nuanced Preferences**: Handles "coffee (primary) + tea (occasional)"
✅ **Confidence Scoring**: Dominant values automatically recognized
✅ **Backward Compatible**: Works with existing entity data

---

## Limitations & Future Enhancements

### Current Limitations

1. **Fixed Threshold**: Resolution threshold is hardcoded to 3
   - Could make this configurable per attribute type

2. **No Re-detection**: Once resolved, contradictions don't resurface
   - Could add logic to re-flag if new conflicting value added

3. **Simple Dominance**: 3x ratio is fixed
   - Could use statistical confidence intervals

### Possible Future Enhancements

1. **Adaptive Thresholds**:
   ```python
   high_severity_attrs = {"eye_color": 5, "name": 5}  # Require 5 turns
   moderate_severity_attrs = {"beverage": 3}  # Require 3 turns
   low_severity_attrs = {"mood": 2}  # Require 2 turns
   ```

2. **Re-detection on New Conflicts**:
   ```python
   if canonical_value == "coffee" and new_value == "tea":
       if source == "kay":  # Kay contradicted himself again
           reset_resolution()
   ```

3. **Confidence Decay**:
   ```python
   # If canonical value not mentioned for 20 turns, reduce confidence
   if turns_since_last_mention > 20:
       confidence_multiplier *= 0.9
   ```

4. **User Override**:
   ```python
   # Allow user to manually resolve contradictions
   entity.force_resolve("beverage", "coffee")
   ```

---

## Conclusion

The contradiction resolution system now properly handles the lifecycle of contradictions:
1. **Detection**: Identifies conflicting attribute values
2. **Resolution**: Marks as resolved after consistent mentions
3. **Decay**: Stops warning about resolved contradictions
4. **Persistence**: Remembers resolution across sessions

Kay can now naturally resolve preferences without infinite anxiety loops. The system differentiates between "coffee (primary) + tea (occasional)" nuanced preferences and actual contradictions, allowing for complex identity expression while still catching genuine conflicts.
