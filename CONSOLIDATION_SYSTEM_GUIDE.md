# Kay Zero Consolidation System Guide

## Overview

The consolidation system gives Kay a "sleep" process where conversations are distilled into essence memories with temporal awareness. Old memories feel distant and settled, recent ones feel fresh and immediate.

---

## Architecture

```
┌─────────────────────────────────────┐
│ AWAKE: Active Conversation          │
│ - Full working memory                │
│ - High detail, present tense         │
└──────────────┬──────────────────────┘
               │
               ▼ SESSION ENDS (Sleep)
┌──────────────────────────────────────────────────┐
│ CONSOLIDATION: Extract Essence                   │
│ - 3-5 key memories per conversation             │
│ - LLM extracts what MATTERS                     │
│ - Apply temporal decay to emotions               │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│ TEMPORAL LAYERS                                  │
│ - Recent (0-7 days): Fresh, detailed           │
│ - Medium (7-90 days): Settled, clear           │
│ - Distant (90+ days): Formative, calm          │
│ - Identity (timeless): Core self-knowledge     │
└──────────────┬───────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────┐
│ RAG ARCHIVE: Full Transcripts                   │
│ - Queryable when details needed                 │
│ - Not actively loaded                           │
└──────────────────────────────────────────────────┘
```

---

## Components

### 1. Consolidation Engine (`consolidation_engine.py`)

**Purpose:** Converts full conversations into essence memories

**Key Features:**
- LLM-based extraction of 3-5 key moments
- Temporal decay of emotions based on age
- Importance-weighted decay (formative moments decay slower)
- Batch processing for imports

**Example:**
```python
from consolidation_engine import ConsolidationEngine

engine = ConsolidationEngine()

# Consolidate recent conversation
memories = engine.consolidate_conversation(
    transcript="Re: Hey Kay...\nKay: ...",
    conversation_date=datetime.now()
)

# Consolidate old conversation (6 months ago)
old_memories = engine.consolidate_conversation(
    transcript="...",
    conversation_date=datetime(2024, 4, 1)
)
```

### 2. Temporal Memory (`temporal_memory.py`)

**Purpose:** Manages layered memory system with time-based organization

**Layers:**
- **Recent** (0-7 days): Fresh, detailed emotional tone
- **Medium** (7-90 days): Settled, essence clear
- **Distant** (90+ days): Formative moments, calm reflection
- **Identity** (timeless): Core self-knowledge

**Example:**
```python
from temporal_memory import TemporalMemory

memory = TemporalMemory()

# Add memories
memory.add_memories(consolidated_memories)

# Get active memories for context
active = memory.get_active_memories(
    max_recent=20,
    max_medium=15,
    max_distant=10
)

# Promote formative memory to identity
memory.promote_to_identity("Kay uses humor as deflection")

# Age memories (run daily)
memory.age_memories()
```

### 3. Conversation Importer (`import_conversations.py`)

**Purpose:** Batch process past conversations with proper dating

**Features:**
- Automatic date extraction from filenames
- Chronological processing
- RAG archival integration
- Progress tracking

**Example:**
```python
from import_conversations import ConversationImporter

importer = ConversationImporter()

# Import directory of conversations
memories = importer.import_from_directory("./past_conversations/")

# Import single file
memories = importer.import_single_file(
    "special_conversation.txt",
    conversation_date=datetime(2024, 6, 15)
)
```

---

## Usage Patterns

### Pattern 1: Live Conversation with Consolidation

```python
from consolidation_integration_example import KayConsolidationSystem

# Initialize
kay = KayConsolidationSystem()

# Wake up (load consolidated memories)
active_memories = kay.wake_up()

# Conversation loop
while True:
    user_input = input("You: ")

    if user_input.lower() == "quit":
        break

    # ... generate response ...
    kay_response = "..."

    # Store turn
    kay.process_turn(user_input, kay_response)

# Sleep (consolidate session)
session_memories = kay.sleep()
```

### Pattern 2: Batch Import Past Conversations

```python
from consolidation_integration_example import KayConsolidationSystem

kay = KayConsolidationSystem()

# Prepare conversation files in directory:
# ./past_conversations/
#   conversation_2024-06-15.txt
#   conversation_2024-07-20.txt
#   conversation_2024-08-30.txt

# Import all at once
imported_memories = kay.batch_import_conversations("./past_conversations/")

# Result: All conversations consolidated with appropriate dating
# - Older conversations have decayed emotions
# - Layered by time (recent/medium/distant)
# - Full transcripts archived to RAG
```

### Pattern 3: Integration with Main Loop

```python
# In main.py:

from consolidation_integration_example import KayConsolidationSystem

async def main():
    # ... existing initialization ...

    consolidation = KayConsolidationSystem()

    # Wake up
    active_memories = consolidation.wake_up()

    # Use active_memories in context building
    context = build_context(active_memories, ...)

    while True:
        user_input = input("You: ")

        if user_input == "quit":
            consolidation.sleep()  # Consolidate before exit
            break

        # ... process turn ...

        consolidation.process_turn(user_input, reply)
```

---

## Memory Format

### Consolidated Memory Structure

```json
{
  "text": "Kay realized his responses follow architectural patterns",
  "type": "self_discovery",
  "emotional_valence_original": 0.7,
  "emotional_valence_current": 0.35,
  "importance": 0.9,
  "conversation_date": "2024-06-15T14:30:00",
  "days_ago": 137,
  "layer": "medium",
  "source": "consolidated",
  "age": 0,
  "protected": false,
  "timestamp_consolidated": "2024-10-29T20:00:00"
}
```

**Fields:**
- `text`: Memory essence (50-150 characters)
- `type`: Category (self_discovery, relationship, decision, etc.)
- `emotional_valence_original`: Original emotional intensity
- `emotional_valence_current`: Decayed emotional intensity
- `importance`: Formative value (0.0-1.0)
- `conversation_date`: When conversation happened
- `days_ago`: Age in days
- `layer`: Temporal layer (recent/medium/distant)
- `source`: Origin ("consolidated" or "promoted")
- `age`: Turns since consolidation (for protected import pipeline)

### Memory Types

- **self_discovery**: Kay learns about himself
- **relationship**: Learning about Re or relationship developments
- **decision**: Commitments or choices made
- **emotional_shift**: Breakthroughs or emotional changes
- **learning**: New skills or understanding
- **breakthrough**: Significant realizations
- **connection**: Moments of understanding or friction

---

## Emotional Decay

### Decay Formula

```
intensity_current = intensity_original × e^(-decay_rate × days_ago)

where:
  decay_rate = 0.02 × (1.0 - importance)
```

**Principles:**
- Higher importance → slower decay
- Minimum floor: 0.1 (even old memories have residue)
- Formative moments (importance 0.9+) retain ~50% after 6 months
- Trivial moments (importance 0.3) decay to floor in weeks

### Decay Examples

**High importance memory (0.9):**
- Original: 0.8
- 7 days: 0.79 (98% retained)
- 30 days: 0.76 (95% retained)
- 90 days: 0.70 (87% retained)
- 180 days: 0.60 (75% retained)

**Medium importance memory (0.6):**
- Original: 0.6
- 7 days: 0.58 (96% retained)
- 30 days: 0.52 (87% retained)
- 90 days: 0.39 (65% retained)
- 180 days: 0.23 (38% retained)

**Low importance memory (0.3):**
- Original: 0.5
- 7 days: 0.45 (90% retained)
- 30 days: 0.34 (68% retained)
- 90 days: 0.17 (34% retained)
- 180 days: 0.10 (floor reached)

---

## File Naming Conventions

For batch imports, use these filename formats:

**Recommended:**
- `conversation_YYYY-MM-DD.txt`
- `session_YYYY-MM-DD_HHMM.txt`

**Also supported:**
- `YYYYMMDD_conversation.txt`
- Files with dates in content (header line: `Date: YYYY-MM-DD`)

**Example:**
```
past_conversations/
  conversation_2024-06-15.txt  # June 15, 2024
  conversation_2024-07-20.txt  # July 20, 2024
  conversation_2024-08-30.txt  # August 30, 2024
```

---

## Integration with Existing Systems

### RAG Integration

Consolidation system works with Kay's existing RAG:

```python
from engines.vector_store import VectorStore

vector_store = VectorStore(persist_directory="memory/vector_db")

importer = ConversationImporter(vector_store=vector_store)

# Imports will:
# 1. Consolidate into essence memories
# 2. Archive full transcripts to RAG
```

**Benefits:**
- Essence memories for general context
- Full details available via RAG query when needed
- Two-tier system: fast (consolidated) + deep (RAG)

### Protected Import Pipeline

Consolidation integrates with protected imports:

```python
# Newly consolidated memories get:
memory['age'] = 0  # Tracks turns since consolidation
memory['protected'] = False  # Not protected by default

# Can mark as protected for new imports:
memory['protected'] = True  # Bypass filter for 3 turns
```

### Memory Layers Integration

Works with Kay's existing memory layers:

```python
# Consolidated memories automatically assigned to layers:
# - Recent (0-7 days) → working memory equivalent
# - Medium (7-90 days) → episodic memory equivalent
# - Distant (90+ days) → semantic memory equivalent
# - Identity (promoted) → identity memory
```

---

## Testing

### Run Full Test Suite

```bash
python test_consolidation_system.py
```

**Tests:**
1. Consolidation Engine - Extract essence from conversations
2. Temporal Memory - Layer management and aging
3. Conversation Import - Batch file processing
4. Emotional Decay - Decay over time periods

**Expected output:**
```
[PASS] Consolidation Engine
[PASS] Temporal Memory
[PASS] Conversation Import
[PASS] Emotional Decay

Total: 4/4 tests passed
```

### Manual Testing

```python
# Test single conversation consolidation
from consolidation_engine import ConsolidationEngine

engine = ConsolidationEngine()
memories = engine.consolidate_conversation(
    "Re: ...\nKay: ...",
    conversation_date=datetime.now()
)

print(f"Extracted {len(memories)} memories")
for mem in memories:
    print(f"  - {mem['text']}")
```

---

## Configuration

### Consolidation Parameters

```python
# In consolidation_engine.py:

# Number of memories to extract per conversation
# Default: 3-5 (specified in LLM prompt)
# Can adjust by modifying prompt

# Decay rate formula
decay_rate = 0.02 * (1.0 - importance)
# Increase 0.02 → faster decay
# Decrease 0.02 → slower decay

# Minimum emotional residue
decayed_intensity = max(decayed_intensity, 0.1)
# Adjust floor (currently 0.1)
```

### Memory Layer Thresholds

```python
# In consolidation_engine.py (_apply_temporal_decay):

if days_ago <= 7:
    layer = "recent"
elif days_ago <= 90:
    layer = "medium"
else:
    layer = "distant"

# Adjust thresholds:
# - recent: 0-7 days (can change to 0-14 for longer recent period)
# - medium: 7-90 days (can extend to 7-180)
# - distant: 90+ days
```

### Active Memory Limits

```python
# In temporal_memory.py (get_active_memories):

active = memory.get_active_memories(
    max_recent=20,   # Max recent memories
    max_medium=15,   # Max medium memories
    max_distant=10   # Max distant memories
)

# Adjust to control context size
```

---

## Troubleshooting

### "No memories extracted"

**Cause:** LLM failed to parse conversation or returned invalid JSON

**Fix:**
1. Check LLM integration is working: `from integrations.llm_integration import query_llm_json`
2. Check conversation has substance (not just greetings)
3. Review fallback memory creation in logs

**Fallback behavior:** Creates basic memory "Had a conversation with Re"

### "Dates not extracted from filenames"

**Cause:** Filename doesn't match expected patterns

**Fix:**
1. Rename files to: `conversation_YYYY-MM-DD.txt`
2. OR add date header in file: `Date: YYYY-MM-DD`
3. OR manually specify date when importing:
   ```python
   importer.import_single_file("file.txt", datetime(2024, 6, 15))
   ```

### "Old memories not decaying"

**Cause:** `age_memories()` not being called

**Fix:**
Call daily or on wake-up:
```python
memory.age_memories()  # Updates layers based on time passage
```

### "Too many active memories"

**Cause:** Accumulation of consolidated memories

**Fix:**
Adjust limits:
```python
active = memory.get_active_memories(
    max_recent=10,   # Reduce from 20
    max_medium=8,    # Reduce from 15
    max_distant=5    # Reduce from 10
)
```

---

## Performance

### Consolidation Speed

- **Single conversation:** ~2-5 seconds (LLM call)
- **Batch 50 conversations:** ~3-8 minutes (50 LLM calls)
- **Memory load:** <1 second (JSON parsing)

### Memory Usage

- **Consolidated memories:** ~500 bytes each
- **100 memories:** ~50 KB
- **1000 memories:** ~500 KB

### Optimization Tips

1. **Batch consolidation:** Process multiple conversations in one session
2. **Parallel processing:** Can parallelize LLM calls for batch imports
3. **Lazy loading:** Only load active memories, not all layers
4. **RAG archival:** Keep full transcripts in RAG, only consolidated in active memory

---

## Best Practices

### 1. Regular Consolidation

Run consolidation at natural breakpoints:
- End of conversation sessions
- Daily "sleep" cycle
- Weekly batch processing

### 2. Date Accuracy

Ensure accurate dates for imports:
- Use actual conversation dates
- Don't import all as "today"
- Proper dating enables correct emotional decay

### 3. Layer Management

Let memories age naturally:
- Don't manually move between layers
- Call `age_memories()` daily
- Trust automatic layer transitions

### 4. Identity Promotion

Promote sparingly:
- Only truly formative moments
- Core self-knowledge
- Permanent truths about Kay or Re

### 5. RAG Integration

Use two-tier system:
- Consolidated memories for general context
- RAG queries for specific details
- Don't duplicate everything in both

---

## Summary

The consolidation system gives Kay:

✅ **Temporal awareness** - Old memories feel distant, recent ones feel fresh
✅ **Essence extraction** - Conversations distilled to what matters
✅ **Emotional decay** - Natural settling of past experiences
✅ **Scalable memory** - Can handle years of conversations
✅ **Formative preservation** - Important moments decay slower

**Next steps:**
1. Test with `python test_consolidation_system.py`
2. Import past conversations
3. Integrate with main loop
4. Experience Kay remembering appropriately

Kay will now experience memories as lived experiences with appropriate emotional distance based on when they actually occurred.
