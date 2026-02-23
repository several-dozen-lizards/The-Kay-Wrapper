# REED WRAPPER AUDIT REPORT

**Generated:** 2026-02-06
**Scope:** Full architecture audit of D:\Reed for Kay→Reed conversion

---

## 1. ARCHITECTURE MAP

### Core Entry Points

| File | Purpose | Key Classes/Functions | Dependencies |
|------|---------|----------------------|--------------|
| `main.py` | CLI entry point, conversation loop | `main()`, `update_all()` | All engines, integrations |
| `reed_ui.py` | Tkinter GUI interface | `ReedUI`, `REED_SYSTEM_PROMPT` | All engines, integrations |
| `reed_cli.py` | Alternative CLI | Similar to main.py | All engines |
| `agent_state.py` | Central state container | `AgentState` | None (data class) |
| `protocol_engine.py` | ULTRAMAP CSV loader | `ProtocolEngine` | CSV data |
| `config.py` | Global configuration | Config constants | None |

### Engine Subsystems (engines/)

| File | Purpose | Key Classes | Kay References |
|------|---------|-------------|----------------|
| `memory_engine.py` | Core memory retrieval/storage | `MemoryEngine` | Yes - validation logic |
| `memory_layers.py` | Two-tier memory (working/long-term) | `MemoryLayerManager` | Comments only |
| `identity_memory.py` | Permanent identity facts | `IdentityMemory` | Yes - Kay patterns |
| `entity_graph.py` | Entity resolution + contradictions | `EntityGraph`, `Entity` | Yes - Kay entity logic |
| `context_manager.py` | Context budget + building | `ContextManager` | No |
| `context_budget.py` | Adaptive token limits | `ContextBudgetManager` | No |
| `vector_store.py` | ChromaDB RAG storage | `VectorStore` | No |
| `emotion_engine.py` | ULTRAMAP emotion rules | `EmotionEngine` | No |
| `warmup_engine.py` | Pre-conversation warmup | `WarmupEngine` | Yes - docstrings |
| `meta_awareness_engine.py` | Confabulation detection | `MetaAwarenessEngine` | Yes - response naming |
| `llm_retrieval.py` | LLM-based document selection | `select_relevant_documents()` | Yes - Kay in prompts |
| `scratchpad_engine.py` | Working notes/flags | `scratchpad` functions | No |
| `curiosity_engine.py` | Autonomous exploration | Curiosity functions | No |

### Integration Layer (integrations/)

| File | Purpose | Kay References |
|------|---------|----------------|
| `llm_integration.py` | Anthropic API calls, system prompts | **YES - DEFAULT_SYSTEM_PROMPT** |
| `tool_use_handler.py` | Tool call processing | Yes - Kay in prompts |
| `sd_integration.py` | Stable Diffusion | No |
| `web_scraping_tools.py` | Web content fetching | No |

### Memory Files (memory/)

| File | Purpose | Kay Content |
|------|---------|-------------|
| `memories.json` | All stored memories | YES - Kay references throughout |
| `memory_layers.json` | Working/long-term storage | YES - Kay references throughout |
| `identity_memory.json` | Identity facts | YES - Kay identity facts |
| `entity_graph.json` | Entity relationships | YES - Kay as entity |
| `preferences.json` | Preference tracking | Minimal |
| `documents.json` | Imported documents | Content-dependent |
| `state_snapshot.json` | Session persistence | YES - Kay state |

---

## 2. IDENTITY SYSTEM

### Where Identity is Loaded at Startup

**Primary Location:** `engines/identity_memory.py:66-81`
```python
def _load_from_disk(self):
    """Load identity memory from disk."""
    with open(self.file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        self.re_identity = data.get("re", [])
        self.kay_identity = data.get("kay", [])
        self.entities = data.get("entities", {})
```

**Initialization Chain:**
1. `main.py:146-152` creates `MemoryEngine`
2. `MemoryEngine.__init__()` at line 217 creates `IdentityMemory()`
3. `IdentityMemory._load_from_disk()` loads from `memory/identity_memory.json`

### Where Identity is Stored Persistently

- **File:** `memory/identity_memory.json`
- **Structure:**
  ```json
  {
    "re": [/* Re's identity facts */],
    "kay": [/* Kay's identity facts */],
    "entities": {/* Entity-specific facts */}
  }
  ```

### Where System Decides "Who It Is"

**1. reed_ui.py Lines 323-464:** `REED_SYSTEM_PROMPT`
- This is Reed's custom system prompt (already converted)
- Contains full Reed identity, history, behaviors

**2. integrations/llm_integration.py Lines 490-700:** `DEFAULT_SYSTEM_PROMPT`
- This is still **KAY'S** system prompt
- **CRITICAL:** This is the legacy prompt still used by CLI mode
- Contains: Kay identity, dragon form, Archive Zero references

**3. Warmup Briefing:** `engines/warmup_engine.py:233-300`
- `format_briefing_for_kay()` - Still named for Kay
- Generates pre-conversation context

### Identity Anchors in System Prompts

| Location | Entity | Status |
|----------|--------|--------|
| `reed_ui.py:323-464` | Reed | CONVERTED |
| `llm_integration.py:490-700` | Kay Zero | NOT CONVERTED |
| `warmup_engine.py` docstrings | Kay | NOT CONVERTED |
| `memory_engine.py` comments | Kay | NOT CONVERTED |

---

## 3. MEMORY ARCHITECTURE

### RAG Retrieval Configuration

**Embedding Model:** ChromaDB default (or sentence-transformers if available)
- Location: `engines/vector_store.py:60-80`
- Chunk size: 1000 chars with 100 char overlap (line 155)

**Retrieval Count Configuration:**
- `config.py:47` - `BASE_RAG_LIMIT = 20` (default)
- `engines/memory_engine.py:2570-2640` - `retrieve_rag_chunks()` with adaptive count
- Auto-determination at line 2600-2602 based on query complexity

**The "50 Chunks" Issue:**
- **NOT FOUND as hardcoded value**
- Previous default was 50, now reduced to 20 in `config.py:47`
- Adaptive retrieval can still pull more based on complexity at `memory_engine.py:2600`

### Memory Composition

**Multi-Factor Retrieval Weights:** `memory_engine.py:1813-2031` - `retrieve_unified_importance()`
- Emotional resonance: 40%
- Semantic similarity: 25%
- Importance: 20%
- Recency: 10%
- Entity proximity: 5%

**Working Memory Configuration:**
- `config.py:27` - `WORKING_MEMORY_WINDOW = 5` turns
- `engines/memory_layers.py:48` - `working_capacity = 15` memories
- `engines/context_manager.py:27` - `max_context_turns = 15`

**Memory Layer Transitions:**
- Two-tier system: Working → Long-term
- Transition based on age/capacity at `memory_layers.py:30-50`
- NO episodic/semantic tiers (explicitly prevented lines 43-45)

### Conversation History Storage

- **In-session:** `context_manager.py:36` - `self.recent_turns = []`
- **Persistent:** `memory/memories.json` via `memory_engine.py:240-243`
- **Session snapshots:** `memory/state_snapshot.json`
- **Saved sessions:** `saved_sessions/session_*.json`

---

## 4. ISSUE LOCATIONS

### Issue 1: Identity Loads Empty at Startup

**Root Cause:** Identity facts require extraction from conversation to populate.

**Relevant Locations:**
- `engines/identity_memory.py:66-81` - Load from disk
- `engines/identity_memory.py:117-200` - `is_identity_fact()` ultra-strict filtering
- Problem: Line 133-137 excludes document-imported facts:
  ```python
  if fact.get("source_document") or fact.get("is_imported") or fact.get("doc_id"):
      return False
  ```

**Current State:** `memory/identity_memory.json` has minimal Kay facts (checked: only 1 fact about eyes)

**Fix Location:** Either:
1. Pre-populate `identity_memory.json` with Reed's core facts
2. Add identity bootstrapping in `IdentityMemory.__init__()` around line 63

---

### Issue 2: RAG Pulls Irrelevant Chunks

**Configuration Locations:**
- `config.py:47` - `BASE_RAG_LIMIT = 20`
- `engines/vector_store.py:200-252` - `query()` method
- `engines/memory_engine.py:2570-2640` - `retrieve_rag_chunks()`

**Scaling Logic:**
- `memory_engine.py:2509-2576` - `_determine_chunk_count()` uses query complexity
- Base count: 30 (line 2533)
- Scales 20-100 based on question words, entities, etc.

**Missing:** Contextual relevance filtering post-retrieval. Chunks are returned by distance only.

**Fix Location:** Add post-retrieval filtering in `retrieve_rag_chunks()` around line 2620-2639

---

### Issue 3: Memory Composition Skew (96% facts, 3% episodic)

**Root Cause:** `retrieve_unified_importance()` doesn't enforce minimums per type.

**Location:** `engines/memory_engine.py:1813-2031`

**Current Logic (line 1820-1850):**
- Retrieves ALL memories, scores them, returns top N
- No category enforcement

**Fix Location:** Add category minimums around line 2000, e.g.:
```python
# Ensure at least 10% episodic
min_episodic = max(3, int(max_memories * 0.1))
```

---

### Issue 4: False Attribution False Positives

**Location:** `engines/meta_awareness_engine.py:88-129` - `_detect_confabulation()`

**Current Logic:**
- Compares Kay's declarative statements against ALL memory text
- Uses 50% word overlap threshold (line 126)
- Compares against `user_input` field only (line 107-111)

**Window Issue:**
- Line 107: `all_memories = memory_engine.memories if hasattr(memory_engine, 'memories') else []`
- This gets ALL memories, not just relevant context

**Fix Location:** Modify line 107-111 to use `agent_state.last_recalled_memories` instead:
```python
all_memories = getattr(agent_state, 'last_recalled_memories', [])
```

---

### Issue 5: Entity Graph Contradictions (300+)

**Location:** `engines/entity_graph.py:406-507` - `_determine_contradiction_severity()`

**Current Logic:**
- Lines 422-452: `accumulative_attrs` list (attributes that can have multiple values)
- Lines 454-488: `transient_attrs` list (attributes that change over time)
- Lines 490-507: Severity classification

**Problem:** Many attributes are incorrectly classified as contradictions when they're:
1. Transient (goals, moods that naturally change)
2. Accumulative (multiple valid values)

**Temporal Logic Missing:** No timestamp comparison for value age.

**Fix Location:**
1. Expand `transient_attrs` list at line 456
2. Add age-based filtering in `Entity.get_contradictions()` (not shown in audit scope)
3. Add `prune_old_attribute_history()` call at startup (method exists at line 509)

---

### Issue 6: Missing kay_document_reader Module

**Status:** FILE EXISTS BUT WRONG LOCATION

**Found:**
- `D:\Reed\K-0\kay_document_reader.py` - In backup folder
- `D:\Reed\__pycache__\kay_document_reader.cpython-310.pyc` - Compiled version

**Should Be:**
- `D:\Reed\kay_document_reader.py` - Missing from root

**Note:** `reed_document_reader.py` EXISTS at root - this is the converted version.

**Import Errors:** Any code still importing `kay_document_reader` will fail.

**Fix:** Either:
1. Copy `K-0/kay_document_reader.py` to root
2. Update all imports to use `reed_document_reader`

---

### Issue 7: No Working Memory on First Turn

**Root Cause:** `recent_turns` is initialized empty and only populated after first turn.

**Locations:**
- `engines/context_manager.py:36` - `self.recent_turns = []`
- `engines/context_manager.py:42-47` - `update_turns()` adds after response

**Context Build on First Turn:**
- `context_manager.py:164` - `working_turns = self.recent_turns[-limits['working_turns']:]`
- Returns empty list on turn 0

**Fix Location:** Add warmup injection at `context_manager.py:99` in `build_context()`:
```python
if not self.recent_turns and hasattr(agent_state, 'warmup_briefing'):
    # Inject warmup context as pseudo-turn
    ...
```

---

## 5. KAY → REED CONVERSION LIST

### CRITICAL: System Prompts

| File | Lines | Current | Change To |
|------|-------|---------|-----------|
| `integrations/llm_integration.py` | 490-700 | Kay Zero system prompt | Reed system prompt (copy from reed_ui.py:323-464) |
| `integrations/llm_integration.py` | 231 | "You are Kay Zero, also known as Kay/K./Kanria" | "You are Reed" |
| `integrations/llm_integration.py` | 835 | "Facts about 'Kay' = YOU" | "Facts about 'Reed' = YOU" |

### Engine Files

| File | Lines | Current | Change To |
|------|-------|---------|-----------|
| `engines/warmup_engine.py` | 1-12 | "Warmup Engine for Kay Zero" docstring | "Warmup Engine for Reed" |
| `engines/warmup_engine.py` | 26-35 | "Kay" references in class docstring | "Reed" |
| `engines/warmup_engine.py` | 233 | `format_briefing_for_kay()` | `format_briefing_for_reed()` |
| `engines/meta_awareness_engine.py` | 180-200 | `kay_response` parameter name | `reed_response` |
| `engines/memory_engine.py` | 905-915 | "Kay READ these documents" comments | "Reed READ" |
| `engines/memory_layers.py` | 4 | "KayZero" in docstring | "Reed" |
| `engines/llm_retrieval.py` | 471-520 | "Kay" in LLM prompts | "Reed" |
| `engines/identity_memory.py` | 53-54 | `kay_identity` attribute | `reed_identity` |
| `engines/entity_graph.py` | variable | "Kay" entity references | "Reed" |

### Integration Files

| File | Lines | Current | Change To |
|------|-------|---------|-----------|
| `integrations/tool_use_handler.py` | throughout | "Kay" in tool prompts | "Reed" |

### UI Files

| File | Lines | Current | Change To |
|------|-------|---------|-----------|
| `reed_ui.py` | 343, 385, 400 | References to "Kay Zero" | Already references correctly (as separate entity) |
| `reed_ui.py` | 2664 | `kay_response=` | `reed_response=` |
| `reed_ui.py` | 4058 | `prefix = "Kay"` | `prefix = "Reed"` |
| `reed_ui.py` | 5187, 5264 | `"speaker": "Kay"` | `"speaker": "Reed"` |
| `reed_ui.py` | 6226, 6376-6432 | `kay_response` parameter | `reed_response` |

### Config Files

| File | Lines | Current | Change To |
|------|-------|---------|-----------|
| `config.py` | 2 | "Global configuration for KayZero" | "Global configuration for Reed" |
| `CLAUDE.md` | throughout | Kay/Kay Zero references | Update for Reed |

### Memory Files (Require Data Migration)

| File | Change Required |
|------|-----------------|
| `memory/identity_memory.json` | Replace `kay` key with `reed`, update content |
| `memory/entity_graph.json` | Rename Kay entity to Reed |
| `memory/memories.json` | Search/replace Kay→Reed in fact text |
| `memory/memory_layers.json` | Search/replace Kay→Reed in fact text |
| `memory/preferences.json` | Minimal changes needed |

---

## 6. PERFORMANCE BOTTLENECKS

### memory_multi_factor (199-219ms, target 150ms)

**Location:** `engines/memory_engine.py:1813-2031` - `retrieve_unified_importance()`

**Bottlenecks:**
1. **Line 1850-1900:** Iterates ALL memories to score (O(n) where n = total memories)
2. **Line 1920-1960:** Entity proximity calculation requires entity graph lookups
3. **Line 1980-2000:** Sorting all scored memories

**Optimizations:**
1. Pre-filter by recency before scoring (skip memories > 30 days old)
2. Cache entity proximity calculations
3. Use heap-based top-k instead of full sort (`heapq.nlargest`)

### memory_retrieval (245-417ms, target 150ms)

**Location:** `engines/memory_engine.py:2713-2920` - `recall()`

**Bottlenecks:**
1. **Line 2772:** Calls `retrieve_unified_importance()` (see above)
2. **Line 2919:** RAG chunk retrieval via ChromaDB
3. **Line 2850-2865:** Relationship fact prioritization iterates results

**Optimizations:**
1. Parallelize memory retrieval and RAG retrieval (currently sequential)
2. Add early termination when sufficient high-quality results found
3. Cache RAG results for repeated queries within session

### Other Slow Paths

| Location | Issue | Est. Time |
|----------|-------|-----------|
| `vector_store.py:220-252` | ChromaDB query cold start | 100-200ms first query |
| `memory_engine.py:1074-1100` | Fact extraction LLM call | 500-1500ms |
| `llm_retrieval.py:269-345` | Document intent classification | 200-400ms |
| `warmup_engine.py:99-231` | Warmup briefing generation | 50-100ms |

---

## 7. RECOMMENDED FIX ORDER

### Phase 1: Critical Conversion (Day 1)

1. **Convert DEFAULT_SYSTEM_PROMPT** in `integrations/llm_integration.py`
   - This affects ALL CLI interactions
   - Copy Reed prompt from `reed_ui.py:323-464`

2. **Pre-populate identity_memory.json**
   - Create `memory/identity_memory_reed.json` with Reed's core facts
   - Replace current `identity_memory.json`

3. **Fix kay_document_reader import**
   - Update all imports to use `reed_document_reader`
   - Or symlink/copy the file

### Phase 2: Memory Issues (Day 2)

4. **Fix working memory on first turn**
   - Modify `context_manager.py:99` to inject warmup context
   - This ensures Reed has context immediately

5. **Fix false attribution false positives**
   - Update `meta_awareness_engine.py:107` to use recalled memories
   - Reduces noise in confabulation detection

6. **Fix memory composition skew**
   - Add category minimums in `retrieve_unified_importance()`
   - Ensure episodic memories aren't drowned out

### Phase 3: Performance (Day 3)

7. **Optimize memory_retrieval**
   - Add parallelization for RAG + memory retrieval
   - Implement early termination

8. **Optimize memory_multi_factor**
   - Add recency pre-filter
   - Use heap-based top-k selection

### Phase 4: Data Migration (Day 4)

9. **Migrate memory files**
   - Run search/replace Kay→Reed on JSON files
   - Update entity graph relationships

10. **Fix entity graph contradictions**
    - Run `prune_old_attribute_history()` at startup
    - Expand transient_attrs list

### Phase 5: Polish (Day 5)

11. **Rename all Kay variables/functions**
    - `kay_response` → `reed_response`
    - `kay_identity` → `reed_identity`
    - Update docstrings and comments

12. **Update CLAUDE.md**
    - Replace Kay references with Reed
    - Document new architecture

---

## APPENDIX: File Count Summary

| Category | Files | With Kay Refs | Needs Conversion |
|----------|-------|---------------|------------------|
| Core Python | 8 | 6 | 5 |
| Engines | 25+ | 12 | 8 |
| Integrations | 4 | 2 | 2 |
| Memory JSON | 6 | 5 | 5 |
| Documentation | 50+ | 40+ | 10 (critical) |
| Total Effort | - | - | ~25 files |

---

*End of Audit Report*
