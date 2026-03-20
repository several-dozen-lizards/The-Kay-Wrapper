# Entity Attribute Normalization Guide

## Overview

The entity graph now includes automatic attribute normalization to prevent duplicate storage of the same information in different formats. This prevents contradictions like:

- `Re.pet_count: {'5': [...], '5 cats': [...]}`
- `Re.favorite_colors: {('green', 'purple'): [...], 'green and purple': [...]}`

## How It Works

### Normalization Pipeline

When `Entity.add_attribute()` is called, the value goes through automatic normalization before storage:

```python
entity.add_attribute('pet_count', '5 cats', turn=1, source='user')
# Stored as: '5' (number extracted)

entity.add_attribute('favorite_colors', 'green and purple', turn=2, source='user')
# Stored as: ['green', 'purple'] (parsed and sorted)
```

### Normalization Rules

#### Rule 1: Number Extraction (Count Attributes)

**Triggered by keywords:** `count`, `number`, `quantity`, `age`, `weight`, `height`, `size`

**Behavior:**
- Extracts numeric value from text
- `"5 cats"` → `"5"`
- `"25 years old"` → `"25"`
- `"3.5 pounds"` → `"3.5"`

**Example:**
```python
entity.add_attribute('pet_count', '5 cats', 1, 'user')
entity.add_attribute('pet_count', '5', 2, 'user')
# Both stored as '5' - no duplicate!
```

#### Rule 2: Multi-Value Normalization (List Attributes)

**Triggered by keywords:** `favorite`, `color`, `hobby`, `hobbies`, `interest`, `tag`, `skill`

**Behavior:**
- Detects common separators: `and`, `,`, `;`, `/`
- Converts to sorted list for consistent comparison
- `"green and purple"` → `['green', 'purple']`
- `['purple', 'green']` → `['green', 'purple']` (sorted)
- `"tea, coffee"` → `['coffee', 'tea']` (sorted)

**Example:**
```python
entity.add_attribute('favorite_colors', 'green and purple', 1, 'user')
entity.add_attribute('favorite_colors', ['purple', 'green'], 2, 'user')
# Both stored as ['green', 'purple'] - no duplicate!
```

#### Rule 3: General String Normalization

**Applied to all string values:**
- Strips leading/trailing whitespace
- `"  [partner] Doe  "` → `"[partner] Doe"`

**Example:**
```python
entity.add_attribute('name', '  [partner] Doe  ', 1, 'user')
# Stored as '[partner] Doe'
```

## Implementation Details

### Where Normalization Happens

**Location:** `engines/entity_graph.py` → `Entity.add_attribute()`

**Flow:**
1. User/system calls `add_attribute(attr, value, turn, source)`
2. Value passes through `_normalize_attribute_value(attr, value)`
3. Normalized value stored in entity attribute history
4. Original value preserved in memory layers (conversation context)

### Helper Methods

```python
def _extract_number_from_text(text: str) -> Optional[str]
    """Extract numeric value from text like "5 cats" → "5" """

def _normalize_multi_value(value: Any) -> Any
    """Convert "green and purple" → ['green', 'purple'] """

def _normalize_attribute_value(attribute: str, value: Any) -> Any
    """Apply normalization rules based on attribute name"""
```

### Logging

When normalization changes a value, it's logged:

```
[ENTITY] Re.pet_count = 5 (normalized from: 5 cats) (turn 2, source: user)
[ENTITY] Re.favorite_colors = ['green', 'purple'] (normalized from: green and purple) (turn 2, source: user)
```

## Impact on Other Systems

### ✅ Contradiction Detection

**Before normalization:**
```python
contradictions = entity.detect_contradictions()
# Found: Re.pet_count has values '5' AND '5 cats' - contradiction!
```

**After normalization:**
```python
contradictions = entity.detect_contradictions()
# No contradiction - both normalized to '5'
```

### ✅ Relationship Tracking (Ownership System)

**No impact** - relationships use entity names, not attributes:
```python
graph.add_relationship("Re", "owns", "[dog]", turn=1)
# Works exactly the same
```

### ✅ Memory Layers

**Original context preserved** - user input stored verbatim in memory layers:
```python
# Memory layer stores: "I have 5 cats"
# Entity graph stores: pet_count = '5'
# Both preserved for different purposes
```

### ✅ Fact Extraction

**Seamless integration** - fact extraction calls `add_attribute()`, normalization happens transparently:
```python
# User says: "I have 5 cats"
# Extraction creates: entity.add_attribute('pet_count', '5 cats', ...)
# Stored as: '5' (normalized automatically)
```

## Edge Cases Handled

### Single Values

**Input:** `'green'` (single color)
**Output:** `'green'` (not split into list)

### Non-Count Numbers

**Input:** `'123 Main Street'` (address with number)
**Output:** `'123 Main Street'` (preserved - 'address' not a count keyword)

### Empty Lists

**Input:** `[]`
**Output:** `[]` (preserved)

### Nested Lists

**Input:** `[[1, 2], [3, 4]]`
**Output:** `[[1, 2], [3, 4]]` (preserved - no matching keyword)

## Tuning Normalization

### Add New Count Keywords

```python
# In _normalize_attribute_value()
count_keywords = ['count', 'number', 'quantity', 'age', 'weight', 'height', 'size', 'length']
```

### Add New Multi-Value Keywords

```python
# In _normalize_attribute_value()
multi_value_keywords = ['favorite', 'color', 'hobby', 'hobbies', 'interest', 'tag', 'skill', 'language']
```

### Add New Separators

```python
# In _normalize_multi_value()
separators = [
    r'\s+and\s+',      # "green and purple"
    r',\s*',           # "tea, coffee"
    r'\s*;\s*',        # "red; blue"
    r'\s*/\s*',        # "hot/cold"
    r'\s+or\s+',       # "tea or coffee" (new)
]
```

### Disable Normalization for Specific Attributes

```python
# In _normalize_attribute_value()
# Add early return for specific attributes:
if attribute in ['raw_text', 'transcript']:
    return value  # No normalization
```

## Testing

Run the comprehensive test suite:

```bash
python test_attribute_normalization.py
```

Tests cover:
1. Number attribute normalization
2. Multi-value attribute normalization
3. Contradiction detection after normalization
4. Relationship tracking unaffected
5. Edge cases (single values, non-count numbers, empty lists, whitespace)

## Benefits

### Before Normalization
```
Re.pet_count:
  - '5' (turn 1, user)
  - '5 cats' (turn 2, user)
  → Contradiction detected! ❌

Re.favorite_colors:
  - ['green', 'purple'] (turn 3, user)
  - 'green and purple' (turn 4, user)
  → Contradiction detected! ❌
```

### After Normalization
```
Re.pet_count:
  - '5' (turn 1, user)
  - '5' (turn 2, user, normalized from '5 cats')
  → No contradiction ✅

Re.favorite_colors:
  - ['green', 'purple'] (turn 3, user)
  - ['green', 'purple'] (turn 4, user, normalized from 'green and purple')
  → No contradiction ✅
```

## Future Enhancements

Potential improvements:

1. **Unit conversion:** `"5 feet"` vs `"60 inches"` → normalize to same unit
2. **Synonym resolution:** `"car"` vs `"vehicle"` → use entity resolution
3. **Date normalization:** `"Jan 1"` vs `"January 1st"` → ISO format
4. **Case-insensitive comparison:** `"Green"` vs `"green"` → lowercase
5. **Acronym expansion:** `"USA"` vs `"United States"` → canonical form

## See Also

- `engines/entity_graph.py` - Implementation
- `test_attribute_normalization.py` - Test suite
- `MEMORY_ARCHITECTURE.md` - Memory layer documentation
- `OWNERSHIP_FIX_SUMMARY.md` - Relationship tracking documentation
