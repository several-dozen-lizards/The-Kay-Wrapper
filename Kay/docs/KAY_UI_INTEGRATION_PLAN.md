# Kay UI Integration Plan: Enhanced Memory Architecture

## Executive Summary

**Goal**: Integrate entity resolution and multi-layer memory into kay_ui.py with **zero breaking changes** to existing functionality.

**Status**: ✅ **ALREADY INTEGRATED** - The enhanced MemoryEngine is already working in kay_ui.py!

**Required Changes**: Minimal - only optional UI enhancements needed for debug/visibility.

---

## Current Integration Status

### ✅ What's Already Working

The enhanced MemoryEngine is **already fully integrated** in kay_ui.py:

1. **Line 104**: `self.memory = MemoryEngine(self.agent_state.memory)`
   - ✅ Creates MemoryEngine with all enhancements (entity_graph, memory_layers)

2. **Line 107**: `self.agent_state.memory = self.memory`
   - ✅ Links MemoryEngine to AgentState for filter access

3. **Lines 110-113**: Initialization logging
   - ✅ Shows entity count, layer status, retrieval mode

4. **Line 364**: `self.memory.extract_and_store_user_facts()`
   - ✅ Pre-response fact extraction with entity resolution

5. **Line 367**: `self.memory.recall()`
   - ✅ Multi-factor retrieval with layer boosting
   - ✅ Temporal decay (every 10 turns)
   - ✅ Entity contradiction detection

6. **Lines 481-486**: `self.memory.encode()`
   - ✅ Post-response fact extraction
   - ✅ Entity/attribute/relationship processing
   - ✅ ULTRAMAP importance calculation
   - ✅ Multi-layer memory storage

### ✅ Conversation Flow (Already Working)

```
User types message
    ↓
Line 364: extract_and_store_user_facts()
    ├─→ LLM extracts entities, attributes, relationships
    ├─→ Creates/updates entities in entity_graph
    ├─→ Stores facts immediately (pre-response)
    └─→ Adds to working memory layer
    ↓
Line 367: recall()
    ├─→ Increments turn counter
    ├─→ Applies temporal decay (every 10 turns)
    ├─→ Multi-factor retrieval (5 factors)
    ├─→ Detects entity contradictions
    └─→ Sets agent_state.entity_contradictions
    ↓
Lines 375-422: Glyph filtering
    ├─→ Filters context using retrieved memories
    ├─→ Includes entity contradictions if detected
    └─→ Builds prompt for Kay
    ↓
Line 455: get_llm_response()
    └─→ Kay generates response using filtered context
    ↓
Lines 481-486: encode()
    ├─→ Extracts facts from Kay's response
    ├─→ Processes entities/attributes/relationships
    ├─→ Validates against retrieved memories (hallucination check)
    ├─→ Calculates ULTRAMAP importance
    └─→ Stores in memory layers
    ↓
User sees Kay's response
```

---

## What's NOT Integrated Yet

### Missing: Optional Debug UI Elements

The enhanced memory system works perfectly, but users can't **see** what's happening without checking console logs.

**Proposed additions** (all optional, non-breaking):

1. **Memory Layer Stats Display** - Show working/episodic/semantic counts
2. **Entity Graph Viewer** - Optional panel showing tracked entities
3. **Contradiction Alerts** - UI notification when contradictions detected
4. **Retrieval Debug Info** - Optional display of retrieved memories + scores

---

## Proposed UI Enhancements

### Option 1: Minimal (Console Logging Only)

**Status**: ✅ Already implemented

The system already logs to console:
```
[KAY UI] Enhanced memory architecture enabled
  - Entity graph: 0 entities
  - Multi-layer memory: Working/Episodic/Semantic transitions
  - Multi-factor retrieval: Emotional+Semantic+Importance+Recency+Entity scoring

[ENTITY GRAPH] Created new entity: [dog] (type: animal)
[ENTITY] Re.eye_color = green (turn 5, source: user)
[MEMORY LAYERS] Promoted to episodic: My dog's name is [dog]...
[RETRIEVAL] Multi-factor retrieval selected 7 memories (scores: ['0.85', '0.72', ...])
[ENTITY GRAPH] ⚠️ Detected 1 entity contradictions
```

**No UI changes needed** - users can monitor console.

---

### Option 2: Sidebar Stats Panel (Recommended)

**Add a collapsible "Memory Stats" section to the sidebar**

**Location**: Between "Emotions" section (row 8-9) and "Style" section (row 10-11)

**Mockup**:
```
┌─────────────────────┐
│ KayZero             │
├─────────────────────┤
│ Sessions            │
│ [Load] [Resume]     │
│ [New] [Export]      │
├─────────────────────┤
│ Emotions            │
│ curiosity: 0.8 ████ │
│ affection: 0.3 █    │
│ [Peek Emotions]     │
├─────────────────────┤
│ Memory Stats     [▼]│  ← NEW SECTION
│ Working: 8/10       │
│ Episodic: 42/100    │
│ Semantic: 15        │
│ Entities: 23        │
│ [View Details]      │  ← Opens debug window
├─────────────────────┤
│ Style               │
│ Affect: 3.5 / 5     │
└─────────────────────┘
```

**Implementation**:
- Add `self.section_memory` label (row 9.5)
- Add `self.memory_stats_label` showing counts
- Add `self.memory_debug_btn` button → opens debug window
- Update stats after each turn in `chat_loop()`

---

### Option 3: Full Debug Window (Advanced)

**Add a "View Details" button that opens a new window**

**Triggered by**: Clicking "View Details" in Memory Stats section

**Debug Window Contents**:

**Tab 1: Memory Layers**
```
┌─────────────────────────────────────────┐
│ Memory Layers                           │
├─────────────────────────────────────────┤
│ [Working] [Episodic] [Semantic]         │ ← Tabs
├─────────────────────────────────────────┤
│ WORKING MEMORY (8/10)                   │
│ Avg Strength: 0.85                      │
│                                         │
│ [5] (user/appearance) Re's eyes are... │
│     Strength: 0.92 | Age: 0.1d         │
│     Entities: Re | Accesses: 3         │
│                                         │
│ [7] (kay/preferences) I prefer coffee  │
│     Strength: 0.88 | Age: 0.2d         │
│     Entities: Kay | Accesses: 2        │
│                                         │
│ ... (6 more)                            │
└─────────────────────────────────────────┘
```

**Tab 2: Entity Graph**
```
┌─────────────────────────────────────────┐
│ Entity Graph                            │
├─────────────────────────────────────────┤
│ Entities: 23 | Relationships: 8         │
│                                         │
│ [Re] (person)                           │
│   eye_color: green (turn 5, user)      │
│   occupation: engineer (turn 12, user) │
│   Relationships:                        │
│     - owns → [dog]                       │
│     - knows → Kay                       │
│                                         │
│ [[dog]] (animal)                         │
│   species: dog (turn 7, user)          │
│   eye_color: brown (turn 15, user)     │
│   Relationships:                        │
│     - owned_by → Re                     │
│                                         │
│ [Kay] (person) ⚠️ 1 contradiction       │
│   eye_color:                            │
│     - gold (turn 3, kay) ✓             │
│     - brown (turn 12, kay) ⚠️          │
│   beverage_preference: coffee (3x)     │
└─────────────────────────────────────────┘
```

**Tab 3: Last Retrieval**
```
┌─────────────────────────────────────────┐
│ Last Retrieval (Turn 47)                │
├─────────────────────────────────────────┤
│ Query: "Tell me about [dog]"             │
│ Retrieved: 7 memories                   │
│                                         │
│ Score  | Fact                           │
│────────┼────────────────────────────────│
│ 0.85   | [episodic] [dog] is Re's dog   │
│        | Emotion:0.32 Sem:0.45 Imp:0.15│
│        | Rec:0.10 Entity:0.20          │
│ 0.72   | [working] [dog] loves fetch    │
│        | Emotion:0.28 Sem:0.50 Imp:0.08│
│ 0.68   | [semantic] Re's eyes are green│
│        | Emotion:0.15 Sem:0.30 Imp:0.22│
│ ... (4 more)                            │
└─────────────────────────────────────────┘
```

---

## Integration Verification Checklist

### ✅ Already Verified (No Changes Needed)

- [x] MemoryEngine initializes with entity_graph and memory_layers
- [x] `extract_and_store_user_facts()` called before response
- [x] `recall()` uses multi-factor retrieval by default
- [x] `encode()` processes entities and stores in layers
- [x] Entity contradictions detected and logged
- [x] Temporal decay applied every 10 turns
- [x] Filter system accesses enhanced memories
- [x] Console logging shows all operations

### ⚠️ To Verify (After Optional UI Changes)

- [ ] Sidebar stats update correctly after each turn
- [ ] Debug window displays current layer counts
- [ ] Debug window shows entity graph with attributes
- [ ] Debug window shows last retrieval with scores
- [ ] Contradictions appear in debug window
- [ ] UI doesn't slow down conversation flow
- [ ] All existing features still work

---

## Proposed Code Changes (Optional UI Only)

### Change 1: Add Memory Stats Section to Sidebar

**File**: `kay_ui.py`
**Location**: After line 170 (emotion_debug_btn)
**Impact**: Non-breaking - adds new UI element

```python
# After line 170:
self.emotion_debug_btn = ctk.CTkButton(...)

# ADD THIS:
self.section_memory = ctk.CTkLabel(
    self.sidebar,
    text="Memory Stats",
    anchor="w",
    font=ctk.CTkFont(size=15)
)
self.section_memory.grid(row=10, column=0, padx=20, pady=(12, 0), sticky="w")

self.memory_stats_label = ctk.CTkLabel(
    self.sidebar,
    text="Loading...",
    justify="left",
    font=ctk.CTkFont(size=13)
)
self.memory_stats_label.grid(row=11, column=0, padx=20, pady=4, sticky="w")

self.memory_debug_btn = ctk.CTkButton(
    self.sidebar,
    text="View Details",
    command=self.open_memory_debug,
    font=ctk.CTkFont(size=14)
)
self.memory_debug_btn.grid(row=12, column=0, padx=20, pady=6, sticky="ew")

# Adjust existing rows: section_style becomes row 13, etc.
```

### Change 2: Add Memory Stats Update Method

**File**: `kay_ui.py`
**Location**: After `update_emotions_display()` (around line 275)
**Impact**: Non-breaking - new method

```python
def update_memory_stats_display(self):
    """Update memory stats sidebar display."""
    try:
        layer_stats = self.memory.memory_layers.get_layer_stats()
        entity_count = len(self.memory.entity_graph.entities)
        contradiction_count = len(self.memory.entity_graph.get_all_contradictions())

        stats_text = (
            f"Working: {layer_stats['working']['count']}/{self.memory.memory_layers.working_capacity}\n"
            f"Episodic: {layer_stats['episodic']['count']}/{self.memory.memory_layers.episodic_capacity}\n"
            f"Semantic: {layer_stats['semantic']['count']}\n"
            f"Entities: {entity_count}"
        )

        if contradiction_count > 0:
            stats_text += f"\n⚠️ {contradiction_count} conflicts"

        self.memory_stats_label.configure(text=stats_text)
    except Exception as e:
        self.memory_stats_label.configure(text=f"Error: {e}")
```

### Change 3: Call Stats Update in chat_loop()

**File**: `kay_ui.py`
**Location**: Line 488 (after `self.memory.encode()`)
**Impact**: Non-breaking - adds one line

```python
# Line 488 - after memory.encode():
self.memory.encode(
    self.agent_state,
    user_input,
    reply,
    list(self.agent_state.emotional_cocktail.keys()),
)

# ADD THIS LINE:
self.update_memory_stats_display()  # Update sidebar stats

return reply
```

### Change 4: Add Debug Window (Optional)

**File**: `kay_ui.py`
**Location**: End of file (new method)
**Impact**: Non-breaking - only called if button clicked

```python
def open_memory_debug(self):
    """Open debug window showing memory details."""
    debug_window = ctk.CTkToplevel(self)
    debug_window.title("Memory System Debug")
    debug_window.geometry("800x600")

    # Create tabview
    tabview = ctk.CTkTabview(debug_window)
    tabview.pack(fill="both", expand=True, padx=10, pady=10)

    # Tab 1: Memory Layers
    tab_layers = tabview.add("Memory Layers")
    self._populate_layers_tab(tab_layers)

    # Tab 2: Entity Graph
    tab_entities = tabview.add("Entity Graph")
    self._populate_entities_tab(tab_entities)

    # Tab 3: Last Retrieval
    tab_retrieval = tabview.add("Last Retrieval")
    self._populate_retrieval_tab(tab_retrieval)

def _populate_layers_tab(self, parent):
    """Populate memory layers debug tab."""
    text_widget = ctk.CTkTextbox(parent, wrap="word")
    text_widget.pack(fill="both", expand=True, padx=10, pady=10)

    # Get layer stats
    layer_stats = self.memory.memory_layers.get_layer_stats()

    # Build display text
    output = []
    output.append("=" * 60)
    output.append("MEMORY LAYERS")
    output.append("=" * 60)
    output.append("")

    for layer_name in ["working", "episodic", "semantic"]:
        layer_data = layer_stats[layer_name]
        memories = getattr(self.memory.memory_layers, f"{layer_name}_memory")

        output.append(f"{layer_name.upper()} MEMORY ({layer_data['count']} memories)")
        output.append(f"Avg Strength: {layer_data['avg_strength']:.2f}")
        output.append("")

        for i, mem in enumerate(memories[-10:]):  # Show last 10
            fact = mem.get('fact', mem.get('user_input', ''))[:60]
            strength = mem.get('current_strength', 1.0)
            perspective = mem.get('perspective', '?')
            topic = mem.get('topic', '?')
            entities = ', '.join(mem.get('entities', []))

            output.append(f"  [{i}] ({perspective}/{topic}) {fact}...")
            output.append(f"      Strength: {strength:.2f} | Entities: {entities or 'none'}")
            output.append("")

    text_widget.insert("1.0", "\n".join(output))
    text_widget.configure(state="disabled")

def _populate_entities_tab(self, parent):
    """Populate entity graph debug tab."""
    text_widget = ctk.CTkTextbox(parent, wrap="word")
    text_widget.pack(fill="both", expand=True, padx=10, pady=10)

    # Get entities
    entities = self.memory.entity_graph.get_entities_by_importance(top_n=50)
    contradictions = self.memory.entity_graph.get_all_contradictions()

    # Build display text
    output = []
    output.append("=" * 60)
    output.append(f"ENTITY GRAPH ({len(entities)} entities)")
    output.append("=" * 60)
    output.append("")

    for entity in entities:
        # Check if entity has contradictions
        entity_contras = [c for c in contradictions if c['entity'] == entity.canonical_name]
        warning = f" ⚠️ {len(entity_contras)} contradictions" if entity_contras else ""

        output.append(f"[{entity.canonical_name}] ({entity.entity_type}){warning}")
        output.append(f"  Importance: {entity.importance_score:.2f} | Accessed: {entity.access_count}x")

        # Show attributes
        for attr_name, history in entity.attributes.items():
            if len(history) == 1:
                value, turn, source, _ = history[0]
                output.append(f"  {attr_name}: {value} (turn {turn}, {source})")
            else:
                # Multiple values - show all
                output.append(f"  {attr_name}:")
                for value, turn, source, _ in history:
                    marker = "⚠️" if len(history) > 1 else "✓"
                    output.append(f"    {marker} {value} (turn {turn}, {source})")

        # Show relationships
        relationships = self.memory.entity_graph.get_entity_relationships(entity.canonical_name)
        if relationships:
            output.append(f"  Relationships:")
            for rel in relationships[:5]:  # Show first 5
                output.append(f"    - {rel.relation_type} → {rel.entity2}")

        output.append("")

    text_widget.insert("1.0", "\n".join(output))
    text_widget.configure(state="disabled")

def _populate_retrieval_tab(self, parent):
    """Populate last retrieval debug tab."""
    text_widget = ctk.CTkTextbox(parent, wrap="word")
    text_widget.pack(fill="both", expand=True, padx=10, pady=10)

    # Get last recalled memories
    recalled = self.agent_state.last_recalled_memories or []

    # Build display text
    output = []
    output.append("=" * 60)
    output.append(f"LAST RETRIEVAL (Turn {self.turn_count})")
    output.append("=" * 60)
    output.append("")
    output.append(f"Retrieved: {len(recalled)} memories")
    output.append("")

    for i, mem in enumerate(recalled):
        fact = mem.get('fact', mem.get('user_input', ''))
        perspective = mem.get('perspective', '?')
        layer = mem.get('current_layer', '?')
        importance = mem.get('importance_score', 0.0)

        output.append(f"[{i+1}] [{layer}] {fact}")
        output.append(f"    Perspective: {perspective} | Importance: {importance:.2f}")

        # Show entities if present
        entities = mem.get('entities', [])
        if entities:
            output.append(f"    Entities: {', '.join(entities)}")

        output.append("")

    text_widget.insert("1.0", "\n".join(output))
    text_widget.configure(state="disabled")
```

---

## Testing Plan

### Test 1: Verify Existing Functionality (No UI Changes)

**Steps**:
1. Run `python kay_ui.py` (or however you launch it)
2. Have a conversation mentioning entities:
   ```
   You: My dog's name is [dog].
   Kay: [responds]

   You: [dog] has brown eyes.
   Kay: [responds]

   You: What color are [dog]'s eyes?
   Kay: [should say "brown" using entity resolution]
   ```

**Expected**:
- Console shows entity creation: `[ENTITY GRAPH] Created new entity: [dog]`
- Console shows attribute addition: `[ENTITY] [dog].eye_color = brown`
- Console shows retrieval: `[RETRIEVAL] Multi-factor retrieval selected X memories`
- Kay correctly recalls [dog]'s eye color

### Test 2: Verify UI Enhancements (After Optional Changes)

**Steps**:
1. Check sidebar shows "Memory Stats" section
2. After conversation, verify stats update:
   ```
   Working: 3/10
   Episodic: 12/100
   Semantic: 2
   Entities: 5
   ```
3. Click "View Details" button
4. Verify debug window opens with tabs
5. Check Entity Graph tab shows "[dog]" with eye_color attribute
6. Check Memory Layers tab shows recent memories
7. Check Last Retrieval tab shows what was recalled

**Expected**:
- Stats update after each turn
- Debug window displays correctly
- All information matches console logs
- UI remains responsive

### Test 3: Verify Contradiction Detection

**Steps**:
1. Have conversation with contradictory information:
   ```
   You: My eyes are green.
   Kay: [responds]

   [Later in conversation]

   Kay: Your eyes are brown. [CONTRADICTION]
   ```

**Expected**:
- Console shows: `[ENTITY GRAPH] ⚠️ Detected 1 entity contradictions`
- Sidebar shows: `⚠️ 1 conflicts`
- Debug window Entity Graph shows both values with ⚠️ markers
- Hallucination prevention blocks Kay from storing "brown" if it contradicts retrieved "green"

---

## Summary

### Current Status

✅ **Enhanced MemoryEngine is FULLY INTEGRATED in kay_ui.py**

All core functionality works:
- Entity resolution
- Multi-layer memory
- Multi-factor retrieval
- Contradiction detection
- Temporal decay
- ULTRAMAP importance

### Proposed Changes

**Only optional UI enhancements for visibility:**

| Change | Impact | Effort | Required? |
|--------|--------|--------|-----------|
| Memory Stats in sidebar | Low | 20 lines | No - nice to have |
| Update stats after turn | None | 1 line | No - nice to have |
| Debug window button | None | 5 lines | No - optional |
| Full debug window | None | 100 lines | No - optional |

**Total breaking changes**: 0
**Total required changes**: 0
**Total optional UI enhancements**: ~130 lines

### Recommendation

**Option A (Minimal)**: Do nothing - system already works, users check console logs

**Option B (Recommended)**: Add sidebar stats + update call (25 lines total)

**Option C (Full)**: Add sidebar stats + full debug window (135 lines total)

---

## Next Steps

**Please review this plan and choose**:

1. ✅ **Approve minimal** - No changes, current integration is sufficient
2. ✅ **Approve sidebar stats** - Add memory stats section (Option B)
3. ✅ **Approve full UI** - Add sidebar stats + debug window (Option C)
4. ❌ **Request modifications** - Specify what you'd like changed

Once approved, I will implement the chosen option with:
- Exact diffs for each file
- Testing verification steps
- Example conversation flow
