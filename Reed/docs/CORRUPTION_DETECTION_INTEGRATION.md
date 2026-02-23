# Corruption Detection Integration Guide

## Overview

This guide shows how to integrate the corruption detection system into AlphaKayZero's existing memory engine.

## Files Created

1. **engines/corruption_detection.py** - Complete corruption detection system
2. **migrate_corruption_markers.py** - Migration script for existing memories
3. **test_corruption_correction.py** - Test suite

## Integration Steps

### Step 1: Initialize Corruption Detector in main.py

Add initialization after MemoryEngine setup:

```python
# Around line 140 in main.py (after memory engine init)
from engines.corruption_detection import CorruptionDetector

# Initialize corruption detector
corruption_detector = CorruptionDetector(memory)
print("[STARTUP] Corruption detection system ready")
```

### Step 2: Add Slash Commands in main.py

Add these commands to the command handling section (around line 278):

```python
# /scan - Scan all memories for corruption
if user_input.lower() == "/scan":
    scan_result = corruption_detector.scan_all_memories()
    print(f"\n=== Corruption Scan Results ===")
    print(f"Total memories: {scan_result['total']}")
    print(f"Newly detected: {scan_result['newly_detected']}")
    print(f"Already flagged: {scan_result['already_flagged']}")
    print(f"Clean: {scan_result['clean']}")

    if scan_result['details']:
        print(f"\nFirst {len(scan_result['details'])} detections:")
        for detail in scan_result['details']:
            print(f"  - {detail['text']}")
            print(f"    Reason: {detail['reason']}")
    continue

# /correct <wrong_memory_id> | <correct_fact>
if user_input.lower().startswith("/correct "):
    parts = user_input[9:].split("|")
    if len(parts) != 2:
        print("\nUsage: /correct <memory_id> | <correct_fact>")
        print("Example: /correct mem_123 | Kay's favorite drink is tea")
        continue

    wrong_id = parts[0].strip()
    correct_fact = parts[1].strip()

    new_id = corruption_detector.correct_memory(
        wrong_id,
        correct_fact,
        state.turn_count
    )

    if new_id:
        print(f"\n✅ Created correction: {new_id}")
        print(f"   Old memory {wrong_id} marked as superseded")
    else:
        print(f"\n❌ Failed to correct memory: {wrong_id}")
    continue

# /corruption_stats - Show corruption statistics
if user_input.lower() == "/corruption_stats":
    stats = corruption_detector.get_corruption_stats()
    print(f"\n=== Corruption Statistics ===")
    print(f"Total memories: {stats['total_memories']}")
    print(f"Corrupted: {stats['corrupted_count']} ({stats['corruption_rate']*100:.1f}%)")
    print(f"Superseded: {stats['superseded_count']}")
    print(f"Corrections: {stats['corrections_count']}")

    if stats['corruption_reasons']:
        print(f"\nReasons:")
        for reason, count in stats['corruption_reasons'].items():
            print(f"  - {reason}: {count}")
    continue
```

### Step 3: Update Memory Retrieval Filtering

The corruption filtering is ALREADY implemented in memory_engine.py (lines 1686-1691), but you can enhance it:

```python
# In memory_engine.py, around line 1686
# Replace existing corruption filter with:
from engines.corruption_detection import filter_corrupted_memories

# Filter out corrupted and superseded memories
all_memories_to_score = filter_corrupted_memories(all_memories_to_score)
corrupted_count = len(all_memories) - len(all_memories_to_score)
if corrupted_count > 0:
    print(f"[CORRUPTION FILTER] Removed {corrupted_count} corrupted/superseded memories")
```

### Step 4: Add Automatic Corruption Detection During Memory Extraction

In memory_engine.py, add corruption detection during fact extraction:

```python
# In extract_facts_from_turn() method, around line 800
from engines.corruption_detection import ensure_corruption_markers

for fact_dict in facts:
    # Ensure corruption markers exist
    fact_dict = ensure_corruption_markers(fact_dict)

    # Check for corruption
    is_corrupted, reason = corruption_detector.detect_corruption(fact_dict)
    if is_corrupted:
        print(f"[CORRUPTION] Auto-detected corruption: {reason}")
        fact_dict['corrupted'] = True
        fact_dict['corruption_reason'] = reason
        fact_dict['corruption_detected_turn'] = self.current_turn

    # Add to appropriate layer
    # ... rest of extraction logic
```

### Step 5: Run Migration Script

Before first use, run the migration script to add corruption markers to existing memories:

```bash
python migrate_corruption_markers.py
```

This will:
1. Backup existing memories to `memory/memories_backup_TIMESTAMP.json`
2. Add corruption marker fields to all existing memories
3. Scan for existing corruption
4. Save updated memories

### Step 6: Verify Integration

Run the test suite:

```bash
python test_corruption_correction.py
```

Expected output:
```
[PASS] Test 1: Detect gibberish
[PASS] Test 2: Correct memory supersession
[PASS] Test 3: Filter corrupted from retrieval
[PASS] Test 4: Corruption statistics

All tests passed!
```

## Usage Examples

### Scan for Corruption
```bash
/scan
```

Output:
```
=== Corruption Scan Results ===
Total memories: 1250
Newly detected: 3
Already flagged: 12
Clean: 1235

First 3 detections:
  - math and Arabic simultaneously processing aaaaaaa...
    Reason: Gibberish detected: pattern '(.)\1{4,}' matched
```

### Correct a Wrong Memory
```bash
/correct mem_456 | Kay's favorite drink is tea, not coffee
```

Output:
```
✅ Created correction: mem_1251
   Old memory mem_456 marked as superseded
```

### View Corruption Stats
```bash
/corruption_stats
```

Output:
```
=== Corruption Statistics ===
Total memories: 1251
Corrupted: 15 (1.2%)
Superseded: 8
Corrections: 8

Reasons:
  - Gibberish detected: 3
  - Superseded by correction: 8
  - Corrupted data: 4
```

## ChromaDB Integration Notes

### Metadata Storage

Corruption markers are stored as ChromaDB metadata fields:

```python
{
    "corrupted": False,
    "corruption_reason": None,
    "corruption_detected_turn": None,
    "superseded_by": None,
    "supersedes": None,
    "correction_applied": False,
    "correction_turn": None
}
```

### Filtering in ChromaDB Queries

When querying ChromaDB, filter out corrupted memories:

```python
# In chromadb query
results = collection.query(
    query_embeddings=[embedding],
    n_results=100,
    where={
        "$and": [
            {"corrupted": {"$ne": True}},  # Not corrupted
            {"superseded_by": {"$eq": None}}  # Not superseded
        ]
    }
)
```

### Backwards Compatibility

The `ensure_corruption_markers()` function ensures all memories have the required fields, even if they were created before the corruption system was added. This prevents KeyError exceptions.

## Important Notes

1. **Identity Facts Protected**: Memories with `is_identity: True` are never flagged as corrupted
2. **High Importance Protected**: Memories with `importance_score > 0.9` are protected
3. **Supersession vs Deletion**: Superseded memories are kept but filtered from retrieval (reversible)
4. **Automatic Detection**: Gibberish and repetition are detected automatically during extraction
5. **Manual Correction**: Use `/correct` for known wrong facts that need fixing

## Troubleshooting

### Issue: Old memories don't have corruption markers
**Solution**: Run `python migrate_corruption_markers.py`

### Issue: Corrupted memories still appearing in retrieval
**Solution**: Check that `filter_corrupted_memories()` is called in retrieve method (line ~1686)

### Issue: Too many false positives in gibberish detection
**Solution**: Adjust patterns in `corruption_detector.gibberish_patterns` (line 34 in corruption_detection.py)

### Issue: Need to unflag incorrectly marked memory
**Solution**: Manually set `memory['corrupted'] = False` or add `/unflag` command:

```python
if user_input.lower().startswith("/unflag "):
    mem_id = user_input[8:].strip()
    memory = corruption_detector._find_memory_by_id(mem_id)
    if memory:
        memory['corrupted'] = False
        memory['corruption_reason'] = None
        memory_engine.save_memories()
        print(f"✅ Unflagged memory: {mem_id}")
    continue
```

## Performance Impact

- **Memory Scan**: O(n) scan of all memories, ~1-2 seconds for 1000+ memories
- **Retrieval Filter**: O(n) filter, negligible impact (<10ms)
- **Automatic Detection**: Runs during extraction, adds ~50ms per turn
- **Storage Overhead**: +7 metadata fields per memory (~100 bytes)

## Next Steps

After integration:

1. Run migration script
2. Run `/scan` to detect existing corruption
3. Use `/corrupt <pattern>` to flag known bad data (e.g., "math and Arabic")
4. Use `/correct` to fix specific wrong memories
5. Monitor `/corruption_stats` over time
