# Proposed Integration: Smart List Validation & Attribute Normalization

## Integration Architecture (3-Stage Flow)

```
USER INPUT: "HIGH-FIVE, K-MAN, YOU FUCKING DID IT YOU GLORIOUS MANIAC"
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: Python Heuristics (Fast Layer) - memory_engine.py     │
│ LINE 195-417: _extract_facts_with_entities()                   │
└─────────────────────────────────────────────────────────────────┘
    │
    ├─→ Extraction LLM (line 359-375)
    │   Input: user_input + response
    │   Output: [
    │       {
    │           "fact": "...",
    │           "entities": ["HIGH-FIVE", "K-MAN", "YOU", "FUCKING", "DID"],
    │           "attributes": [...]
    │       }
    │   ]
    │
    ├─→ Python Entity Count (line 771)
    │   entity_list = ["HIGH-FIVE", "K-MAN", "YOU", "FUCKING", "DID"]
    │   potential_list_flag = len(entity_list) >= 3  # = True
    │   ⚠️ DON'T apply importance boost yet!
    │
    └─→ Flag potential list, pass to Stage 2
        metadata = {
            "potential_list": True,
            "entity_count": 5,
            "entities": ["HIGH-FIVE", "K-MAN", "YOU", "FUCKING", "DID"]
        }
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: Filter LLM (Smart Layer) - NEW FUNCTION               │
│ NEW: _validate_and_normalize_extraction()                      │
└─────────────────────────────────────────────────────────────────┘
    │
    ├─→ Filter LLM Call (NEW)
    │   Prompt: "Is this a real entity list or emphatic speech?"
    │   Input: user_input + extracted_entities + metadata
    │   Output: {
    │       "list_validated": False,  # ← LLM says NO
    │       "list_type": "emphatic_exclamation",
    │       "reason": "Capitalized words are emphatic expression, not entities",
    │       "actual_entities": [],
    │       "normalized_attributes": {}
    │   }
    │
    └─→ Attribute Normalization (ALSO in LLM prompt)
        Prompt: "Normalize attributes to consistent format"
        Examples: "5 cats" → "5", "green and purple" → ["green", "purple"]
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: Post-LLM Processing - memory_engine.py                │
│ MODIFIED: _calculate_turn_importance() + _process_entities()   │
└─────────────────────────────────────────────────────────────────┘
    │
    ├─→ Apply Importance Boost (line 94-96, MODIFIED)
    │   if metadata["list_validated"] == True:
    │       importance = 0.9  # ← Only boost if LLM confirmed
    │   else:
    │       importance = 0.5  # ← Normal importance
    │       print(f"[LIST OVERRIDE] LLM rejected list flag: {metadata['reason']}")
    │
    ├─→ Use Normalized Attributes (line 462-467, ENHANCED)
    │   for attr_data in metadata["normalized_attributes"]:
    │       entity.add_attribute(attr, normalized_value, ...)
    │       # Normalization already done by LLM + entity_graph layer
    │
    └─→ Store to THREE-TIER system (existing, lines 783-891)
    ↓
STORED MEMORIES (with correct importance, normalized attributes)
```

## Code Integration Points

### Integration Point 1: Add Validation Stage (NEW FUNCTION)

**Location:** `memory_engine.py` - Insert AFTER line 417 (after _extract_facts_with_entities)

```python
def _validate_and_normalize_extraction(
    self,
    user_input: str,
    response: str,
    extracted_facts: List[Dict],
    entity_list: List[str],
    potential_list_flag: bool
) -> Dict[str, Any]:
    """
    STAGE 2: Filter LLM validates potential lists and normalizes attributes.

    Returns metadata with:
    - list_validated: bool (True if real entity list, False if emphatic/error)
    - list_type: str (entity_list, name_list, emphatic_expression, etc.)
    - reason: str (explanation for validation decision)
    - actual_entities: List[str] (corrected entity list)
    - normalized_attributes: Dict (attribute normalization mappings)
    """

    if not client or not MODEL:
        # Fallback: trust Python heuristic
        return {
            "list_validated": potential_list_flag,
            "list_type": "unknown",
            "reason": "LLM unavailable, using heuristic",
            "actual_entities": entity_list,
            "normalized_attributes": {},
            "llm_override": False
        }

    # Build validation prompt
    validation_prompt = f"""Analyze this extracted data and determine if it's a real entity list or a false positive.

USER INPUT: "{user_input}"
KAY'S RESPONSE: "{response}"

EXTRACTED ENTITIES: {entity_list}
PYTHON HEURISTIC: {"Flagged as list (3+ entities)" if potential_list_flag else "Not flagged as list"}

TASK 1: LIST VALIDATION
Is this a REAL list of discrete entities (people, pets, places)?
Or is it a FALSE POSITIVE (emphatic speech, capitalized words, random capitalization)?

Examples:
- REAL LIST: "My cats are Dice, Chrome, Luna" → ["Dice", "Chrome", "Luna"] ✓
- REAL LIST: "I have 5 pets: Saga, Finn, Luna" → ["Saga", "Finn", "Luna"] ✓
- FALSE POSITIVE: "HIGH-FIVE, K-MAN, YOU DID IT" → emphatic expression, not entities ✗
- FALSE POSITIVE: "WOW, THAT'S CRAZY, DUDE" → capitalized exclamation, not entities ✗

TASK 2: ATTRIBUTE NORMALIZATION
For any attributes in the extracted facts, normalize to consistent format:
- Count attributes: Extract number only ("5 cats" → "5", "3 years old" → "3")
- List attributes: Convert to sorted list ("green and purple" → ["green", "purple"])
- Text attributes: Trim whitespace ("  John  " → "John")

OUTPUT FORMAT (JSON):
{{
    "list_validated": true/false,
    "list_type": "entity_list" | "emphatic_expression" | "capitalized_words" | "unknown",
    "reason": "Brief explanation why this is/isn't a list",
    "actual_entities": ["corrected", "entity", "list"],
    "normalized_attributes": {{
        "original_value": "normalized_value",
        "5 cats": "5",
        "green and purple": ["green", "purple"]
    }},
    "confidence": 0.0-1.0
}}

Analyze now:"""

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=800,
            temperature=0.2,  # Low temp for consistent validation
            system="You are a validation system. Determine if extracted entities form a real list or are false positives. Normalize attributes to consistent formats. Output valid JSON only.",
            messages=[{"role": "user", "content": validation_prompt}],
        )

        text = resp.content[0].text.strip()

        # Clean markdown
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

        # Parse JSON
        validation_result = json.loads(text)

        # Add override flag
        validation_result["llm_override"] = (validation_result["list_validated"] != potential_list_flag)

        # Log if LLM overrode heuristic
        if validation_result["llm_override"]:
            override_direction = "rejected" if not validation_result["list_validated"] else "confirmed"
            print(f"[LIST VALIDATION] LLM {override_direction} Python heuristic: {validation_result['reason']}")

        return validation_result

    except Exception as e:
        print(f"[WARNING] List validation failed: {e}")
        # Fallback: trust Python heuristic
        return {
            "list_validated": potential_list_flag,
            "list_type": "unknown",
            "reason": f"Validation failed: {e}",
            "actual_entities": entity_list,
            "normalized_attributes": {},
            "llm_override": False
        }
```

### Integration Point 2: Modify encode_memory() Flow

**Location:** `memory_engine.py` line 747-900 (encode_memory function)

**CURRENT CODE (line 760-781):**
```python
# Extract facts FIRST (to get entity information)
extracted_facts = self._extract_facts(user_input, clean_response)

print(f"[MEMORY] Extracted {len(extracted_facts)} facts from conversation turn")

# Collect all unique entities from extracted facts
all_entities = set()
for fact_data in extracted_facts:
    all_entities.update(fact_data.get("entities", []))

entity_list = sorted(list(all_entities))
is_list_statement = len(entity_list) >= 3  # 3+ entities = list

# Get what was retrieved for validation (hallucination checking)
retrieved_memories = getattr(agent_state, 'last_recalled_memories', []) if agent_state else []

# ===== TIER 1: FULL CONVERSATION TURN (never truncated) =====
turn_importance = self._calculate_turn_importance(
    emotional_cocktail or {},
    emotion_tags or [],
    len(entity_list)  # ← This triggers the boost
)
```

**MODIFIED CODE:**
```python
# Extract facts FIRST (to get entity information)
extracted_facts = self._extract_facts(user_input, clean_response)

print(f"[MEMORY] Extracted {len(extracted_facts)} facts from conversation turn")

# Collect all unique entities from extracted facts
all_entities = set()
for fact_data in extracted_facts:
    all_entities.update(fact_data.get("entities", []))

entity_list = sorted(list(all_entities))
potential_list_flag = len(entity_list) >= 3  # ← Flag, don't boost yet

# ===== NEW: STAGE 2 - VALIDATE WITH FILTER LLM =====
validation_metadata = self._validate_and_normalize_extraction(
    user_input=user_input,
    response=clean_response,
    extracted_facts=extracted_facts,
    entity_list=entity_list,
    potential_list_flag=potential_list_flag
)

# Use validated list status
is_list_statement = validation_metadata["list_validated"]
actual_entities = validation_metadata.get("actual_entities", entity_list)

# Get what was retrieved for validation (hallucination checking)
retrieved_memories = getattr(agent_state, 'last_recalled_memories', []) if agent_state else []

# ===== TIER 1: FULL CONVERSATION TURN (never truncated) =====
turn_importance = self._calculate_turn_importance(
    emotional_cocktail or {},
    emotion_tags or [],
    len(actual_entities),
    is_validated_list=is_list_statement  # ← NEW parameter
)
```

### Integration Point 3: Modify Importance Calculation

**Location:** `memory_engine.py` line 88-103 (_calculate_turn_importance)

**CURRENT CODE:**
```python
def _calculate_turn_importance(self, emotional_cocktail: Dict, emotion_tags: List[str], entity_count: int) -> float:
    """Calculate importance score for a full conversation turn."""
    # Base importance
    importance = 0.5

    # Strong boost for lists (3+ entities)
    if entity_count >= 3:
        importance = 0.9
        print(f"[MEMORY] List detected ({entity_count} entities) - importance boosted to {importance}")

    # Emotional intensity boost
    if emotional_cocktail:
        avg_intensity = sum(e.get("intensity", 0) for e in emotional_cocktail.values()) / max(len(emotional_cocktail), 1)
        importance += avg_intensity * 0.1

    return min(importance, 1.0)
```

**MODIFIED CODE:**
```python
def _calculate_turn_importance(
    self,
    emotional_cocktail: Dict,
    emotion_tags: List[str],
    entity_count: int,
    is_validated_list: bool = False  # ← NEW parameter
) -> float:
    """Calculate importance score for a full conversation turn."""
    # Base importance
    importance = 0.5

    # Strong boost for VALIDATED lists only
    if is_validated_list and entity_count >= 3:
        importance = 0.9
        print(f"[MEMORY] Validated list ({entity_count} entities) - importance boosted to {importance}")
    elif entity_count >= 3 and not is_validated_list:
        # Python heuristic flagged it, but LLM rejected
        print(f"[MEMORY] List rejected by validation ({entity_count} entities) - keeping base importance {importance}")

    # Emotional intensity boost
    if emotional_cocktail:
        avg_intensity = sum(e.get("intensity", 0) for e in emotional_cocktail.values()) / max(len(emotional_cocktail), 1)
        importance += avg_intensity * 0.1

    return min(importance, 1.0)
```

### Integration Point 4: Enhanced Attribute Processing

**Location:** `memory_engine.py` line 447-467 (_process_entities)

**CURRENT CODE:**
```python
# Add attributes to entities
for attr_data in fact_data.get("attributes", []):
    entity_name = attr_data.get("entity")
    attribute_name = attr_data.get("attribute")
    value = attr_data.get("value")

    if entity_name and attribute_name and value:
        entity = self.entity_graph.get_or_create_entity(
            entity_name,
            turn=self.current_turn
        )

        # CRITICAL: Source is based on who said this (speaker)
        source = speaker

        entity.add_attribute(
            attribute_name,
            value,
            turn=self.current_turn,
            source=source
        )
```

**MODIFIED CODE:**
```python
# Add attributes to entities WITH NORMALIZATION METADATA
normalized_attrs = fact_data.get("normalized_attributes", {})

for attr_data in fact_data.get("attributes", []):
    entity_name = attr_data.get("entity")
    attribute_name = attr_data.get("attribute")
    value = attr_data.get("value")

    if entity_name and attribute_name and value:
        entity = self.entity_graph.get_or_create_entity(
            entity_name,
            turn=self.current_turn
        )

        # CRITICAL: Source is based on who said this (speaker)
        source = speaker

        # Check if LLM provided normalized version
        if str(value) in normalized_attrs:
            normalized_value = normalized_attrs[str(value)]
            print(f"[ATTR NORM] LLM normalized '{value}' → '{normalized_value}'")
            value = normalized_value

        # Add attribute (entity_graph.py normalization also applies)
        entity.add_attribute(
            attribute_name,
            value,
            turn=self.current_turn,
            source=source
        )
```

### Integration Point 5: Enhanced Extraction Prompt

**Location:** `memory_engine.py` line 212-356 (extraction_prompt in _extract_facts_with_entities)

**ADD TO EXTRACTION PROMPT (after line 234):**
```python
7. For attributes, use CONSISTENT FORMATS:
   - Count/number attributes: Provide just the number ("5", not "5 cats")
   - Multi-value attributes: Provide as array (["green", "purple"], not "green and purple")
   - Text attributes: Trim whitespace

ATTRIBUTE FORMAT EXAMPLES:
✓ GOOD: {{"entity": "Re", "attribute": "pet_count", "value": "5"}}
✗ BAD:  {{"entity": "Re", "attribute": "pet_count", "value": "5 cats"}}

✓ GOOD: {{"entity": "Re", "attribute": "favorite_colors", "value": ["green", "purple"]}}
✗ BAD:  {{"entity": "Re", "attribute": "favorite_colors", "value": "green and purple"}}
```

## Preservation of Existing Systems

### ✅ Hallucination Blocking (Line 594-653)
**No changes needed** - validation happens BEFORE this check
- Hallucination blocking still validates Kay's facts against sources
- Filter LLM operates on extraction output, doesn't affect validation

### ✅ Contradiction Detection (Line 655-745)
**No changes needed** - operates independently
- Entity-aware contradiction checking still works
- Filter LLM doesn't affect contradiction logic

### ✅ Ownership Ground Truth (Line 469-536)
**No changes needed** - operates on relationships
- Filter LLM validates lists, not ownership
- Ownership verification still checks against identity layer

### ✅ Identity Memory (Line 860-871)
**No changes needed** - operates on fact records
- Identity facts still marked with maximum importance
- Filter LLM doesn't affect identity classification

### ✅ Memory Layers (Line 801, 855, 1078-1081)
**No changes needed** - operates on stored memories
- Working → Episodic → Semantic promotion still works
- Temporal decay still applies
- Filter LLM operates BEFORE storage

### ✅ Entity Normalization (entity_graph.py)
**Enhanced, not replaced**
- LLM provides FIRST normalization layer (consistent format from extraction)
- Entity_graph.py provides SECOND normalization layer (catch remaining variations)
- Two-layer approach is more robust

## Debug Logging

**New log messages:**
```
[LIST VALIDATION] LLM rejected Python heuristic: Capitalized words are emphatic expression, not entities
[LIST VALIDATION] LLM confirmed Python heuristic: Real list of pet names detected
[ATTR NORM] LLM normalized '5 cats' → '5'
[ATTR NORM] LLM normalized 'green and purple' → ['green', 'purple']
[MEMORY] Validated list (3 entities) - importance boosted to 0.9
[MEMORY] List rejected by validation (5 entities) - keeping base importance 0.5
```

## Example Scenarios

### Scenario 1: False Positive (Emphatic Expression)

**Input:** "HIGH-FIVE, K-MAN, YOU FUCKING DID IT YOU GLORIOUS MANIAC"

**Stage 1 (Python Heuristic):**
```
entity_list = ["HIGH-FIVE", "K-MAN", "YOU", "FUCKING", "DID"]
potential_list_flag = True (5 entities)
```

**Stage 2 (Filter LLM):**
```json
{
    "list_validated": false,
    "list_type": "emphatic_expression",
    "reason": "Capitalized words are emphatic exclamation, not discrete entities",
    "actual_entities": [],
    "normalized_attributes": {},
    "llm_override": true
}
```

**Stage 3 (Post-Processing):**
```
[LIST VALIDATION] LLM rejected Python heuristic: Capitalized words are emphatic expression, not discrete entities
is_list_statement = False
importance = 0.5 (no boost applied)
```

### Scenario 2: True Positive (Real List)

**Input:** "My cats are Dice, Chrome, Luna, Finn, and Shadow"

**Stage 1 (Python Heuristic):**
```
entity_list = ["Dice", "Chrome", "Luna", "Finn", "Shadow"]
potential_list_flag = True (5 entities)
```

**Stage 2 (Filter LLM):**
```json
{
    "list_validated": true,
    "list_type": "entity_list",
    "reason": "User explicitly lists 5 cat names",
    "actual_entities": ["Dice", "Chrome", "Luna", "Finn", "Shadow"],
    "normalized_attributes": {},
    "llm_override": false
}
```

**Stage 3 (Post-Processing):**
```
is_list_statement = True
importance = 0.9 (boost applied - validated list)
[MEMORY] Validated list (5 entities) - importance boosted to 0.9
```

### Scenario 3: Attribute Normalization

**Input:** "I have 5 cats and my favorite colors are green and purple"

**Stage 1 (Python Heuristic):**
```
extracted_facts = [
    {
        "fact": "Re has 5 cats",
        "attributes": [{"entity": "Re", "attribute": "pet_count", "value": "5 cats"}]
    },
    {
        "fact": "Re's favorite colors are green and purple",
        "attributes": [{"entity": "Re", "attribute": "favorite_colors", "value": "green and purple"}]
    }
]
```

**Stage 2 (Filter LLM):**
```json
{
    "list_validated": false,
    "list_type": "not_a_list",
    "reason": "Attributes mentioned, but not an entity list",
    "actual_entities": ["Re"],
    "normalized_attributes": {
        "5 cats": "5",
        "green and purple": ["green", "purple"]
    },
    "llm_override": false
}
```

**Stage 3 (Post-Processing):**
```
[ATTR NORM] LLM normalized '5 cats' → '5'
[ATTR NORM] LLM normalized 'green and purple' → ['green', 'purple']

Stored attributes:
- Re.pet_count = "5" (normalized)
- Re.favorite_colors = ["green", "purple"] (normalized)
```

## Benefits

1. **No False Positives:** LLM validates before applying importance boost
2. **Debuggable:** Clear logging when LLM overrides heuristics
3. **Preserves Safety:** All existing systems (hallucination, contradiction, ownership) untouched
4. **Two-Layer Normalization:** LLM + entity_graph.py for maximum consistency
5. **Backward Compatible:** Falls back to heuristic if LLM fails
6. **Original Context Preserved:** Memories still store full user text
