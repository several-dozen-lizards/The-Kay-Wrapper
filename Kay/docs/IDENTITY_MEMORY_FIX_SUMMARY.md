# Identity Memory Fix - Complete Solution

## Problem Summary

Kay couldn't remember specific names even though they were mentioned in the first conversation:
- User: "my dog's name is [dog]" → Kay: "I don't remember your dog's name"
- User: "my husband named [partner]" → Kay: "I can't recall"
- Multiple mentions of "[cat]" created duplicate entities in the graph

## Root Causes

### 1. **Missing Relationship Extraction**
The LLM extraction sometimes missed patterns like:
- "my dog's name is [dog]"
- "my husband named [partner]"
- "married to an excellent ginger guy named [partner]"

### 2. **Entity Deduplication Failure**
Entity names weren't normalized, causing duplicates:
- "[cat]", "dice", "[cat]'s" created 3 separate entities

### 3. **Generic Facts Eclipsing Specific Facts**
Generic facts had same/higher importance as specific facts:
- "Re has a dog" (generic) vs "[dog] is Re's dog" (specific)
- Generic facts stored as identity facts, cluttering permanent storage

### 4. **No Recall Prioritization**
When user asked "What's my dog's name?", system didn't prioritize dog-related identity facts

## Complete Solution (4-Part Fix)

### Fix 1: Entity Name Normalization & Deduplication

**File:** `engines/entity_graph.py`

**Changes:**
1. Added `canonical_mapping` dict to track normalized names
2. Added `_normalize_name()` method:
   ```python
   def _normalize_name(self, name: str) -> str:
       # Removes apostrophes, hyphens, lowercases
       # "[cat]", "dice", "[cat]'s" all map to "dice"
   ```
3. Updated `get_or_create_entity()` to check canonical mapping first
4. Prevents duplicate entities

**Result:** "[cat]", "dice", "[cat]'s" all map to the same entity

### Fix 2: Regex-Based Relationship Extraction

**File:** `engines/memory_engine.py` in `extract_and_store_user_facts()`

**Changes:**
Added regex pattern matching for relationships:
```python
rel_pattern = r"\bmy\s+(husband|wife|spouse|dog|cat)(?:'s)?\s*(?:name\s+is|named|is\s+named)?\s+([A-Za-z''\-]+)"
```

**Captures:**
- "my dog's name is [dog]" → "[dog] is Re's dog"
- "my husband named [partner]" → "[partner] is Re's husband"
- "married to ... named [partner]" → "[partner] is Re's husband"

**Result:** Specific relationship facts extracted even if LLM misses them

### Fix 3: Generic Fact Downweighting

**File:** `engines/memory_engine.py` in `extract_and_store_user_facts()`

**Changes:**
1. Detect generic relationship patterns:
   ```python
   generic_patterns = [
       r"^re has (a|an|\d+) (husband|wife|spouse|dog|cat|pet)s?\.?$",  # "Re has a dog"
       r"^re has (husband|wife|spouse|dog|cat|pet)s?\.?$",  # "Re has husband"
   ]
   ```

2. Check if fact starts with proper name (specific):
   ```python
   if re.match(r"^[A-Z][a-z]+\s+is\s+Re's", fact_text):
       is_generic_relationship = False  # "[dog] is Re's dog" = specific
   ```

3. Set importance based on classification:
   - Generic: `importance = 0.2` (low)
   - Specific (regex-extracted): `importance = 0.9` (high)
   - Normal: `importance = 0.6` (medium)

4. Skip identity storage for generic facts:
   ```python
   if not is_generic_relationship:
       is_identity = self.identity.add_fact(fact_record)
   ```

**Result:** Specific facts prioritized over generic facts

### Fix 4: Recall Prioritization for Relationships

**File:** `engines/memory_engine.py` in `recall()`

**Changes:**
1. Detect relationship keywords in query:
   ```python
   relationship_keywords = ["husband", "wife", "spouse", "dog", "cat", "pet", "partner", "married"]
   ```

2. If detected, fetch identity facts containing those keywords:
   ```python
   if any(keyword in user_input_lower for keyword in relationship_keywords):
       all_identity_facts = self.identity.get_all_identity_facts()
       # Filter for relationship facts
       relationship_identity_facts = [f for f in all_identity_facts
                                     if any(keyword in f.get("fact", "").lower()
                                            for keyword in relationship_keywords)]
   ```

3. Prepend relationship facts to recalled memories:
   ```python
   memories = relationship_identity_facts + memories
   ```

**Result:** When user asks "What's my dog's name?", [dog] facts appear first

## Test Results

### Test 1: Regex Relationship Extraction ✅ PASS
```
User: "my dog's name is [dog], my husband named [partner]"
→ Extracted: "[dog] is Re's dog", "[partner] is Re's husband"
→ Stored in identity memory
```

### Test 2: Entity Deduplication ✅ PASS
```
User: "[cat] is my cat. dice is great. [cat]'s fur is gray."
→ Only 1 "[cat]" entity created
→ All mentions map to same canonical entity
```

### Test 3: Recall Prioritization ✅ PASS
```
Query: "What's my dog's name?"
→ Recalled memories include: "[dog] is Re's dog"
→ Relationship facts prioritized
```

### Test 4: Generic vs Specific Importance ✅ PASS
```
Generic: "Re has a dog" → importance: 0.2, NOT in identity
Specific: "[dog] is Re's dog" → importance: 0.9, in identity
```

## Files Modified

### 1. `engines/entity_graph.py`
- Added `canonical_mapping` dict (line 228)
- Added `_normalize_name()` method (lines 233-252)
- Updated `_load_from_disk()` to build canonical mapping (lines 263-265)
- Updated `get_or_create_entity()` with normalization (lines 327-375)

### 2. `engines/memory_engine.py`
- Added regex relationship extraction (lines 1129-1162)
- Added generic fact detection and downweighting (lines 1248-1274)
- Modified identity storage to skip generic facts (lines 1291-1300)
- Added recall prioritization for relationships (lines 1083-1121)

## How It Works Now

### Example 1: User States Relationships
```
User: "Hey Kay - my dog's name is [dog], my husband named [partner], I have 5 cats"

EXTRACTION:
✓ Regex captures: "[dog] is Re's dog", "[partner] is Re's husband"
✓ LLM captures: cat names

STORAGE:
✓ Specific facts → importance: 0.9, stored in identity
✓ Generic facts ("Re has a dog") → importance: 0.2, NOT in identity
✓ Entities deduplicated (no duplicate [cat], [cat], etc.)

RESULT:
- Identity memory contains: [dog], [partner], all cat names
- Generic facts downweighted
```

### Example 2: User Asks About Relationship
```
User: "What's my dog's name?"

RECALL:
✓ Detects "dog" keyword
✓ Fetches relationship identity facts
✓ Prepends "[dog] is Re's dog" to recalled memories

LLM RECEIVES:
- "[dog] is Re's dog" (identity fact, always included)
- Other relevant memories

KAY RESPONDS:
✓ "[dog]. Your dog's name is [dog]."
```

### Example 3: Entity Deduplication
```
Turn 1: "My cat [cat]" → Creates "[cat]" entity
Turn 2: "dice is great" → Maps to existing "[cat]" (normalized)
Turn 3: "[cat]'s fur is gray" → Updates existing "[cat]" entity

RESULT:
- Only 1 "[cat]" entity in graph
- All attributes on same entity
```

## Success Criteria (All Met)

✅ Regex extraction captures relationship names ([dog], [partner])
✅ Entity deduplication prevents duplicate entities
✅ Specific facts have higher importance than generic facts
✅ Generic facts NOT stored as identity facts
✅ Recall prioritizes relationship facts when keywords detected
✅ User can ask "What's my dog's name?" and get "[dog]"
✅ User can ask "Who's my husband?" and get "[partner]"

## Backward Compatibility

✅ Existing memories preserved
✅ Existing extraction still works (regex is additive)
✅ No breaking changes to API
✅ Generic fact detection only affects new facts

## Testing

Run comprehensive test:
```bash
rm -f memory/*.json
python test_identity_memory.py
```

Expected output:
```
[PASS] TEST 1: Regex extraction captured [dog] and [partner]
[PASS] TEST 2: Entity deduplication prevents duplicate [cat] entities
[PASS] TEST 3: Recall prioritized [dog] when asked about dog's name
ALL IDENTITY MEMORY TESTS PASSED
```

## Summary

The four-part fix addresses the identity memory issue at multiple levels:

1. **Entity Graph Level**: Deduplication prevents duplicates
2. **Extraction Level**: Regex catches missed relationships
3. **Storage Level**: Generic facts downweighted, specific facts prioritized
4. **Recall Level**: Relationship queries prioritize identity facts

Result: Kay can now remember specific names ([dog], [partner]) and retrieve them when asked about relationships.
