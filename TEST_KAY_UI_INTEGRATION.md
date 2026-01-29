# Testing Guide: Kay UI Enhanced Memory Integration

## Quick Test (5 minutes)

### 1. Launch Kay UI

```bash
python kay_ui.py
```

**Expected Console Output**:
```
[KAY UI] Enhanced memory architecture enabled
  - Entity graph: 0 entities
  - Multi-layer memory: Working/Episodic/Semantic transitions
  - Multi-factor retrieval: Emotional+Semantic+Importance+Recency+Entity scoring
```

**Expected UI**:
- Sidebar shows "Memory Stats" section
- Initial display:
  ```
  Working: 0/10
  Episodic: 0/100
  Semantic: 0
  Entities: 0
  ```

---

### 2. Test Entity Resolution

**Type in chat**:
```
You: My dog's name is Saga.
```

**Expected Console Output**:
```
[MEMORY PRE-RESPONSE] Extracted 1 facts from user input
[ENTITY GRAPH] Created new entity: Saga (type: unknown)
[ENTITY GRAPH] Created new entity: Re (type: person)
[ENTITY] Saga.species = dog (turn 1, source: user)
[MEMORY PRE-RESPONSE] Stored: [user/relationships] ...
[RETRIEVAL] Multi-factor retrieval selected X memories...
```

**Expected UI Update**:
```
Memory Stats
Working: 1-3/10
Episodic: 0/100
Semantic: 0
Entities: 2
```

**Kay's Response**: Should acknowledge Saga appropriately

---

### 3. Test Attribute Tracking

**Type in chat**:
```
You: Saga has brown eyes.
```

**Expected Console Output**:
```
[ENTITY] Saga.eye_color = brown (turn 2, source: user)
```

**Expected UI Update**:
```
Memory Stats
Working: 3-5/10
Episodic: 0/100
Semantic: 0
Entities: 2
```
(Entities stay at 2 - Saga already exists)

---

### 4. Test Memory Retrieval

**Type in chat**:
```
You: What color are Saga's eyes?
```

**Expected Console Output**:
```
[RETRIEVAL] Multi-factor retrieval selected X memories...
```

**Kay's Response**: Should correctly recall "brown eyes"

**Expected UI**: Working memory continues to grow

---

### 5. Test Contradiction Detection (Optional)

**Type in chat**:
```
You: My eyes are green.
```

(Wait for Kay's response, then continue conversation for a few turns)

**Then try to make Kay contradict** (this is tricky - Kay might not hallucinate):

One way: Ask Kay to guess your eye color incorrectly, then see if he stores it.

**If contradiction detected**, console shows:
```
[ENTITY GRAPH] ⚠️ Detected 1 entity contradictions
  - Re.eye_color: {'green': [...], 'blue': [...]}
```

**Expected UI**:
```
Memory Stats
Working: X/10
Episodic: Y/100
Semantic: Z
Entities: N
⚠️ 1 conflicts
```

---

## Full Test (15 minutes)

### Test Scenario: Multi-Turn Conversation

Have this conversation to test all features:

```
Turn 1
You: My name is Alex and I have a golden retriever named Saga.

Expected:
- Console: Entity creation for Alex, Saga
- UI: Entities: 2, Working: 2-4/10

Turn 2
You: Saga is 3 years old and loves to swim.

Expected:
- Console: Attributes added to Saga (age, activity)
- UI: Working increases

Turn 3
You: I also have a cat named Luna.

Expected:
- Console: Entity creation for Luna
- UI: Entities: 3, Working increases

Turn 4
You: Luna has green eyes.

Expected:
- Console: Luna.eye_color = green
- UI: Working increases

Turn 5
You: What pets do I have?

Expected:
- Kay recalls: Saga (dog) and Luna (cat)
- Console: Multi-factor retrieval shows high scores for pet memories
- UI: Working continues to fill

Turn 6-10: Continue conversation mentioning Saga and Luna

Expected:
- Working memory fills up (→10/10)
- Some memories promoted to episodic
- UI shows: Episodic: 1-3/100
- Entities stay at 3 (Alex, Saga, Luna)

Turn 11-20: Extended conversation

Expected:
- Episodic memory grows
- Frequently accessed memories might promote to semantic
- UI shows layer distribution evolving

Turn 21: Ask about Luna's eyes

You: What color are Luna's eyes?

Expected:
- Kay correctly recalls: "green"
- Console shows Luna.eye_color retrieved
- Memory about Luna's eyes might promote if accessed frequently
```

---

## Verification Checklist

### ✅ Visual Checks

- [ ] Memory Stats section appears in sidebar
- [ ] Stats text is readable and properly formatted
- [ ] Stats update after each conversation turn
- [ ] No visual glitches or overlapping elements
- [ ] Palette changes apply to Memory Stats section

### ✅ Functional Checks

- [ ] Entity count increases when new entities mentioned
- [ ] Entity count stays stable when existing entities mentioned
- [ ] Working memory fills up over conversation
- [ ] Episodic memory increases as promotions occur
- [ ] Contradiction warning appears when applicable
- [ ] Stats remain accurate compared to console logs

### ✅ Performance Checks

- [ ] UI remains responsive during conversation
- [ ] No lag when stats update
- [ ] No freezing or stuttering
- [ ] Rapid-fire messages don't cause issues

### ✅ Edge Cases

- [ ] Empty memory displays correctly on startup
- [ ] Error handling works (if layer stats fail)
- [ ] Very long conversations don't break display
- [ ] Palette changes don't reset stats

---

## Console Output Reference

### Normal Operation

```
[KAY UI] Enhanced memory architecture enabled
  - Entity graph: 0 entities
  - Multi-layer memory: Working/Episodic/Semantic transitions
  - Multi-factor retrieval: Emotional+Semantic+Importance+Recency+Entity scoring

[Filtering context with glyphs...]
[DEBUG] Memory count before filter: 0

[MEMORY PRE-RESPONSE] Extracted 2 facts from user input
[ENTITY GRAPH] Created new entity: Saga (type: animal)
[ENTITY] Saga.species = dog (turn 1, source: user)
[MEMORY PRE-RESPONSE] Stored: [user/relationships] My dog's name is Saga...

[RETRIEVAL] Multi-factor retrieval selected 1 memories (scores: ['0.85'])
[DEBUG] ✓ Filter succeeded
[DEBUG] ✓ Decode succeeded
[DEBUG] ✓ Context building succeeded
[DEBUG] ✓ LLM response received

[MEMORY] Extracted 1 facts from conversation turn
[MEMORY] ✓ Stored: [kay/conversation] Kay acknowledged Saga... (importance: 0.45)
```

### With Contradiction

```
[ENTITY GRAPH] ⚠️ Detected 1 entity contradictions
  - Re.eye_color: {'green': [(5, 'user', '2025-10-19T...')], 'brown': [(12, 'kay', '2025-10-19T...')]}

[MEMORY WARNING] ❌ Kay stated 'Re has brown eyes...' but this contradicts retrieved memories. NOT STORING.
```

### With Promotion

```
[MEMORY LAYERS] Promoted to episodic: Saga is Re's dog (accesses: 3)
```

### With Temporal Decay

```
[MEMORY] Applied temporal decay at turn 20
```

---

## Troubleshooting

### Issue: Stats show "Error: ..."

**Cause**: Exception in `update_memory_stats_display()`

**Debug**:
1. Check console for full error
2. Verify `self.memory.memory_layers` exists
3. Verify `self.memory.entity_graph` exists

**Fix**: Check that MemoryEngine initialization succeeded

---

### Issue: Stats don't update

**Cause**: `update_memory_stats_display()` not called

**Debug**:
1. Check line 211: initialization call exists
2. Check line 518: per-turn call exists
3. Add debug print in method to verify it's called

**Fix**: Ensure both calls are present

---

### Issue: Entities count wrong

**Cause**: Entity graph not populating correctly

**Debug**:
1. Check console for "[ENTITY GRAPH] Created new entity"
2. Check `memory/entity_graph.json` for entities
3. Verify LLM fact extraction working

**Fix**: Check `_extract_facts_with_entities()` is working

---

### Issue: Layer counts all zero

**Cause**: Memories not being added to layers

**Debug**:
1. Check console for "[MEMORY LAYERS] Promoted..."
2. Check `memory/memory_layers.json` exists
3. Verify `encode()` calls `add_memory()`

**Fix**: Check memory encoding pipeline

---

### Issue: Contradictions not showing

**Cause**: No actual contradictions, or detection not working

**Debug**:
1. Force a contradiction (e.g., "My eyes are green", then later "Your eyes are brown")
2. Check console for contradiction warnings
3. Check entity graph for conflicting attributes

**Fix**: Verify `_check_contradiction()` logic

---

## Expected File Changes

After running and having a conversation:

### New Files Created

1. `memory/entity_graph.json`
   ```json
   {
     "entities": {
       "Saga": {
         "canonical_name": "Saga",
         "entity_type": "animal",
         "aliases": ["saga"],
         "attributes": {
           "species": [["dog", 1, "user", "2025-10-19T..."]],
           "eye_color": [["brown", 2, "user", "2025-10-19T..."]]
         },
         "relationships": ["Re::owns::Saga"],
         "first_mentioned": 1,
         "last_accessed": 5,
         "access_count": 4,
         "importance_score": 0.65
       }
     },
     "relationships": {
       "Re::owns::Saga": {
         "entity1": "Re",
         "relation_type": "owns",
         "entity2": "Saga",
         "turn": 1,
         "source": "user",
         "strength": 1.0
       }
     }
   }
   ```

2. `memory/memory_layers.json`
   ```json
   {
     "working": [
       {
         "fact": "Saga has brown eyes",
         "perspective": "user",
         "entities": ["Saga"],
         "current_layer": "working",
         "current_strength": 1.0,
         "access_count": 2,
         "importance_score": 0.55
       }
     ],
     "episodic": [
       {
         "fact": "Saga is Re's dog",
         "perspective": "user",
         "current_layer": "episodic",
         "current_strength": 0.95,
         "access_count": 3,
         "importance_score": 0.72
       }
     ],
     "semantic": []
   }
   ```

### Modified Files

1. `memory/memories.json` - Enhanced format with entities
2. `memory/state_snapshot.json` - Includes entity contradictions, layer stats

---

## Success Criteria

✅ **All tests pass if**:

1. Memory Stats section displays correctly
2. Stats update after each conversation turn
3. Entity count tracks entities accurately
4. Layer distribution shows realistic progression
5. Contradictions appear when detected
6. UI remains responsive and performant
7. Console logs match UI display
8. No errors or exceptions
9. Palette theming works correctly
10. All existing features still work

---

## Next Steps After Testing

Once testing passes:

1. ✅ **Use normally** - Memory stats now visible
2. 📊 **Monitor stats** - Watch memory system in action
3. 🔍 **Check contradictions** - Address any detected conflicts
4. 📈 **Observe patterns** - See which memories promote to semantic
5. 🎯 **Optional**: Implement Option C (debug window) if you want drill-down capability

---

## Quick Reference: What to Look For

| Turn | Expected Entity Count | Expected Working | Expected Episodic |
|------|----------------------|------------------|-------------------|
| 0 | 0 | 0/10 | 0/100 |
| 1-3 | 1-3 | 2-5/10 | 0/100 |
| 5-10 | 3-8 | 6-10/10 | 0-2/100 |
| 10-20 | 5-15 | 8-10/10 | 2-10/100 |
| 20+ | 10-30 | 10/10 | 10-50/100 |

(Varies based on conversation content and access patterns)

---

## Support

If you encounter issues:

1. Check console logs for detailed errors
2. Verify all files are present (entity_graph.py, memory_layers.py)
3. Check that LLM API key is valid
4. Review MEMORY_ARCHITECTURE.md for system details
5. Check KAY_UI_INTEGRATION_FLOW.md for expected behavior

The enhanced memory system is now fully integrated and operational! 🎉
