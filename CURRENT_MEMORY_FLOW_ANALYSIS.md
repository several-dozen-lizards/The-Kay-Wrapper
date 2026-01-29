# Current Memory Architecture Flow Analysis

## Flow Diagram

```
USER INPUT
    ↓
[1] extract_and_store_user_facts() (line 1159)
    OR encode_memory() (line 747)
    ↓
[2] _extract_facts_with_entities() (line 195)
    → Calls LLM for fact extraction
    → LLM returns: facts, entities, attributes, relationships
    → Fallback: _extract_entities_simple() (line 105) if LLM fails
    ↓
[3] Python Heuristics (IMMEDIATE - NO LLM VALIDATION)
    → Line 771: entity_list = collect all entities from extracted facts
    → Line 771: is_list_statement = len(entity_list) >= 3
    → Line 777-781: _calculate_turn_importance()
        → Line 94-96: if entity_count >= 3: importance = 0.9 (BOOST APPLIED)
    ↓
[4] _process_entities() (line 419)
    → Creates/updates entities in entity_graph
    → Line 462-467: entity.add_attribute() (uses NEW normalization)
    → Line 530-536: entity_graph.add_relationship()
    ↓
[5] THREE-TIER STORAGE
    → Tier 1: full_turn (line 783-801)
    → Tier 2: extracted_facts (line 806-858)
    → Tier 3: glyph_summary (line 873-891)
    ↓
[6] _generate_glyph_summary() (line 1460)
    → Creates compressed representation
    → Uses entity counts, emotions, types
    → NO validation, just formatting
```

## Problem Points Identified

### Problem 1: Aggressive List Detection (Lines 771, 94-96)

**Where it happens:**
```python
# Line 771 in encode_memory():
entity_list = sorted(list(all_entities))
is_list_statement = len(entity_list) >= 3  # ← PYTHON HEURISTIC, NO LLM VALIDATION

# Line 94-96 in _calculate_turn_importance():
if entity_count >= 3:
    importance = 0.9  # ← BOOST APPLIED IMMEDIATELY
    print(f"[MEMORY] List detected ({entity_count} entities) - importance boosted to {importance}")
```

**The Issue:**
- "HIGH-FIVE, K-MAN, YOU FUCKING DID IT" gets split into 5 capitalized words
- Python heuristic: 5 entities → is_list_statement = True
- Importance boost to 0.9 happens BEFORE any validation
- LLM never validates whether this is actually a list

### Problem 2: Entity Attribute Duplication (Line 462-467)

**Where it happens:**
```python
# Line 462-467 in _process_entities():
entity.add_attribute(
    attribute_name,
    value,  # ← RAW VALUE from LLM extraction
    turn=self.current_turn,
    source=source
)
```

**Current State:**
- NEW normalization system (just implemented) handles this at add_attribute() level
- Normalization converts "5 cats" → "5", "green and purple" → ['green', 'purple']
- But LLM extraction might produce inconsistent formats in the first place

## Key Components

### Component 1: Extraction LLM (Line 212-356)

**Current prompt:**
```python
extraction_prompt = f"""Extract ONLY the factual statements EXPLICITLY present in the input below.

USER INPUT: "{user_input}"
KAY'S RESPONSE: "{response}"

RULES:
1. Extract only factual statements, not questions or opinions
2. Each fact should be a complete, standalone statement
3. **CRITICAL FOR LISTS**: If user provides a list (e.g., "My cats are A, B, C, D, E"), extract:
   - ONE fact for the complete list: "Re has 5 cats: A, B, C, D, E"
   - SEPARATE facts for EACH item: "A is Re's cat", "B is Re's cat", etc.
   - DO NOT bundle everything into a single generic fact
4. Determine perspective for each fact:
   - "user" = facts about Re (the person typing)
   - "kay" = facts about Kay (the AI)
   - "shared" = facts about both or shared experiences
...
OUTPUT FORMAT (JSON array):
[
  {
    "fact": "Saga is Re's dog",
    "perspective": "user",
    "topic": "pets",
    "entities": ["Saga", "Re"],
    "attributes": [{"entity": "Saga", "attribute": "species", "value": "dog"}],
    "relationships": [{"entity1": "Re", "relation": "owns", "entity2": "Saga"}]
  }
]
```

**System prompt (line 363):**
```python
system="You are a fact extraction system. Extract discrete facts from conversations. For lists, extract EACH item separately. Output valid JSON only."
```

**Key Observation:**
- This is ONE LLM call that does BOTH extraction AND structure
- NO separate "filter LLM" exists currently
- LLM outputs entities directly, Python heuristic counts them

### Component 2: Simple Entity Fallback (Line 105-140)

```python
def _extract_entities_simple(self, text: str) -> List[str]:
    """
    Simple entity extraction fallback when LLM fails.
    Looks for capitalized words but filters out common words.
    """
    stop_words = {
        'i', 'my', 'your', 'the', 'and', 'are', 'is', ...
    }

    entities = []
    words = text.split()

    for word in words:
        clean_word = word.strip('.,!?;:()"\'')
        # Capitalized and not in stop words
        if (clean_word and
            clean_word[0].isupper() and
            len(clean_word) > 1 and
            clean_word.lower() not in stop_words):
            entities.append(clean_word)

    return entities
```

**The Problem:**
- "HIGH-FIVE, K-MAN, YOU FUCKING DID IT" → extracts: HIGH-FIVE, K-MAN, YOU, FUCKING, DID
- All are capitalized, none in stop_words
- Result: 5 entities → triggers list boost

### Component 3: Importance Calculation (Line 88-103)

```python
def _calculate_turn_importance(self, emotional_cocktail: Dict, emotion_tags: List[str], entity_count: int) -> float:
    """Calculate importance score for a full conversation turn."""
    # Base importance
    importance = 0.5

    # Strong boost for lists (3+ entities)
    if entity_count >= 3:
        importance = 0.9  # ← IMMEDIATE BOOST, NO VALIDATION
        print(f"[MEMORY] List detected ({entity_count} entities) - importance boosted to {importance}")

    # Emotional intensity boost
    if emotional_cocktail:
        avg_intensity = sum(e.get("intensity", 0) for e in emotional_cocktail.values()) / max(len(emotional_cocktail), 1)
        importance += avg_intensity * 0.1

    return min(importance, 1.0)
```

**Line 77-79 in _calculate_fact_importance():**
```python
# Boost for multiple entities (part of a list)
entity_count = len(fact_data.get("entities", []))
if entity_count > 1:
    importance += 0.1 * entity_count  # ← Linear boost per entity
```

### Component 4: Entity Storage (Line 419-467)

```python
def _process_entities(self, fact_data: Dict[str, Any]):
    """
    Process extracted entities and attributes, adding them to the entity graph.
    """
    # Create/update entities
    for entity_name in fact_data.get("entities", []):
        entity = self.entity_graph.get_or_create_entity(
            entity_name,
            entity_type=entity_type,
            turn=self.current_turn
        )

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

            entity.add_attribute(  # ← Normalization happens HERE (new system)
                attribute_name,
                value,
                turn=self.current_turn,
                source=source
            )
```

### Component 5: Glyph Generation (Line 1460-1515)

```python
def _generate_glyph_summary(self, emotional_cocktail: dict, extracted_facts: list, is_list: bool) -> str:
    """
    Generate compressed glyph representation of a conversation turn.

    Returns:
        Glyph string (e.g., "📋!!! 🔮(0.8) 🐱(5x) 🐕(1x)")
    """
    components = []

    # List indicator (if applicable)
    if is_list:
        components.append("📋!!!")  # ← Just marks it, doesn't validate

    # Emotional glyphs (top 3 emotions by intensity)
    # Entity type counting
    # ...

    return " ".join(components) if components else "💭"
```

**Key Observation:**
- Glyph generation is FORMATTING only
- NO validation or filtering
- Just creates compressed representation

## NO "Filter LLM" Currently Exists

**Critical Finding:**
- There is NO separate "filter LLM" step in the current architecture
- The extraction LLM (line 195) does BOTH extraction AND structuring in one call
- Python heuristics (line 771, 94-96) apply boosts IMMEDIATELY after extraction
- NO validation step between extraction and storage

## Existing Safety Systems (Must Preserve)

### 1. Hallucination Blocking (Line 594-653)
```python
def _validate_fact_against_sources(self, fact: str, fact_perspective: str, retrieved_memories: List[Dict]) -> bool:
    """
    Validate that Kay's claimed facts about the user were actually stated by the user.
    Returns True if fact is VALID, False if HALLUCINATION.
    """
    # Only validate Kay's statements about the user
    if fact_perspective != "kay":
        return True

    # Validate eye color, preferences, etc.
    # Block if Kay adds details user never mentioned
```

### 2. Contradiction Detection (Line 655-745)
```python
def _check_contradiction(self, new_fact: str, retrieved_memories: List[Dict]) -> bool:
    """
    Check if new fact contradicts what was retrieved.
    CRITICAL: Only check contradictions WITHIN THE SAME ENTITY.
    """
    # Entity-aware contradiction checking
    # "Kay's eyes are gold" does NOT contradict "Re's eyes are green"
```

### 3. Ownership Ground Truth (Line 469-536)
```python
# CRITICAL FIX: Verify ownership relationships against identity layer
if relation_type == "owns":
    if speaker == "kay":
        conflict_check = self.entity_graph.check_ownership_conflict(
            entity=entity2,
            claimed_owner=entity1,
            identity_memory=self.identity
        )

        if conflict_check["should_block"]:
            print(f"[OWNERSHIP BLOCKED] {conflict_check['message']}")
            continue  # DON'T create the relationship
```

### 4. Identity Memory (Permanent Facts)
```python
# Line 860-871: Identity facts marked with maximum importance
is_identity = self.identity.add_fact(fact_record)
if is_identity:
    fact_record["is_identity"] = True
    fact_record["importance_score"] = 0.95  # Maximum importance
```

### 5. Memory Layers (Episodic/Semantic Promotion)
```python
# Line 801, 855: Facts added to memory layers
self.memory_layers.add_memory(full_turn_record, layer="working")
self.memory_layers.add_memory(fact_record, layer="working")

# Line 1078-1081: Temporal decay applied periodically
if self.current_turn % 10 == 0:
    self.memory_layers.apply_temporal_decay()
```

## Summary: Where Things Break

1. **Line 771**: Python heuristic counts entities (no validation)
2. **Line 94-96**: Importance boost applied immediately (no LLM check)
3. **Line 195-417**: Extraction LLM returns entities, but doesn't validate if they're a real list
4. **Line 462-467**: Attributes stored (normalization helps, but extraction format still varies)
5. **NO filter LLM exists** - need to add validation stage between extraction and storage

## What Needs to Change

1. **Add validation stage AFTER extraction, BEFORE importance boost**
2. **Separate entity counting (heuristic) from list validation (LLM)**
3. **Apply importance boost ONLY if LLM validates the list**
4. **Normalize attributes in extraction prompt (guide LLM to consistent format)**
5. **Log when LLM overrides Python heuristics**
