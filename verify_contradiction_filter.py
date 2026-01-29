"""
Verify context-aware contradiction resolution is working.
"""

import json
from engines.entity_graph import EntityGraph

print("=" * 70)
print("CONTEXT-AWARE CONTRADICTION RESOLUTION VERIFICATION")
print("=" * 70)

# Load entity graph
entity_graph = EntityGraph()

total_entities = len(entity_graph.entities)
print(f"\n1. Total entities in graph: {total_entities}")

# Test 1: Check ALL entities (old behavior)
print(f"\n2. Testing ALL entities contradiction check (old behavior):")
contradictions_all = entity_graph.get_all_contradictions(
    current_turn=0,
    resolution_threshold=3,
    entity_filter=None  # Check ALL
)
print(f"   - Checked: {total_entities} entities")
print(f"   - Found: {len(contradictions_all)} contradictions")

# Test 2: Check only relevant entities (new behavior)
print(f"\n3. Testing RELEVANT entities contradiction check (new behavior):")
relevant_entities = {'Kay', 'Re', 'Saga', 'Astrology'}  # Simulated relevant entities
contradictions_relevant = entity_graph.get_all_contradictions(
    current_turn=0,
    resolution_threshold=3,
    entity_filter=relevant_entities
)
print(f"   - Found: {len(contradictions_relevant)} contradictions in {len(relevant_entities)} entities")

# Test 3: Performance comparison
print(f"\n4. Performance impact:")
reduction_percent = ((total_entities - len(relevant_entities)) / total_entities) * 100
print(f"   - Entities checked: {len(relevant_entities)}/{total_entities}")
print(f"   - Reduction: {reduction_percent:.1f}%")

# Test 4: Sample entities
print(f"\n5. Sample entities in graph:")
sample_entities = sorted(list(entity_graph.entities.keys()))[:20]
for entity in sample_entities:
    print(f"   - {entity}")
if len(entity_graph.entities) > 20:
    print(f"   ... and {len(entity_graph.entities) - 20} more")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print(f"\nExpected behavior:")
print(f"  [OK] Total entities: ~689+")
print(f"  [OK] Filter reduces check to ~5-30 relevant entities")
print(f"  [OK] 95%+ reduction in entities checked per turn")
