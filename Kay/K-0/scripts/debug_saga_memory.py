"""
Debug script to check if Saga is being stored correctly.
"""

import json
import os

print("=" * 80)
print("DEBUGGING SAGA MEMORY STORAGE")
print("=" * 80)

# Check memories.json
if os.path.exists("memory/memories.json"):
    with open("memory/memories.json", "r", encoding="utf-8") as f:
        memories = json.load(f)

    print(f"\nTotal memories: {len(memories)}")

    # Search for Saga
    saga_memories = []
    dog_memories = []

    for i, mem in enumerate(memories):
        mem_text = str(mem).lower()

        if "saga" in mem_text:
            saga_memories.append((i, mem))

        if "dog" in mem_text:
            dog_memories.append((i, mem))

    print(f"\nMemories containing 'saga': {len(saga_memories)}")
    for i, mem in saga_memories[:5]:  # First 5
        print(f"\n[Memory {i}]")
        print(f"  Type: {mem.get('type', 'N/A')}")
        print(f"  Fact: {mem.get('fact', 'N/A')[:100]}")
        print(f"  Entities: {mem.get('entities', [])}")
        print(f"  Perspective: {mem.get('perspective', 'N/A')}")
        if mem.get('attributes'):
            print(f"  Attributes: {mem['attributes']}")
        if mem.get('relationships'):
            print(f"  Relationships: {mem['relationships']}")

    print(f"\n\nMemories containing 'dog': {len(dog_memories)}")
    for i, mem in dog_memories[:5]:
        print(f"\n[Memory {i}]")
        print(f"  Type: {mem.get('type', 'N/A')}")
        print(f"  Fact: {mem.get('fact', 'N/A')[:100]}")
        print(f"  Entities: {mem.get('entities', [])}")
        print(f"  Perspective: {mem.get('perspective', 'N/A')}")

else:
    print("\n[ERROR] memories.json not found")

# Check identity_memory.json
if os.path.exists("memory/identity_memory.json"):
    with open("memory/identity_memory.json", "r", encoding="utf-8") as f:
        identity = json.load(f)

    print("\n\n" + "=" * 80)
    print("IDENTITY MEMORY")
    print("=" * 80)

    # Check entities
    entities = identity.get("entities", {})

    if "Saga" in entities:
        print("\n✓ Saga found in identity memory!")
        print(f"  Facts: {len(entities['Saga'])}")
        for fact in entities['Saga']:
            print(f"    - {fact.get('fact', 'N/A')[:100]}")
    else:
        print("\n✗ Saga NOT found in identity memory")

    # Check Re's facts for Saga
    re_facts = identity.get("re", [])
    saga_in_re = [f for f in re_facts if "saga" in str(f).lower()]

    print(f"\n\nRe's facts mentioning Saga: {len(saga_in_re)}")
    for fact in saga_in_re:
        print(f"  - {fact.get('fact', 'N/A')[:100]}")

else:
    print("\n[ERROR] identity_memory.json not found")

# Check entity_graph.json
if os.path.exists("memory/entity_graph.json"):
    with open("memory/entity_graph.json", "r", encoding="utf-8") as f:
        entity_graph = json.load(f)

    print("\n\n" + "=" * 80)
    print("ENTITY GRAPH")
    print("=" * 80)

    entities = entity_graph.get("entities", {})

    if "Saga" in entities:
        saga_entity = entities["Saga"]
        print("\n✓ Saga found in entity graph!")
        print(f"  Type: {saga_entity.get('entity_type', 'N/A')}")
        print(f"  Aliases: {saga_entity.get('aliases', [])}")
        print(f"  Attributes: {saga_entity.get('attributes', {})}")
        print(f"  Relationships: {saga_entity.get('relationships', [])}")
        print(f"  Access count: {saga_entity.get('access_count', 0)}")
    else:
        print("\n✗ Saga NOT found in entity graph")

    # Check relationships for Saga
    relationships = entity_graph.get("relationships", {})
    saga_rels = {k: v for k, v in relationships.items() if "Saga" in k}

    print(f"\n\nRelationships involving Saga: {len(saga_rels)}")
    for rel_id, rel in saga_rels.items():
        print(f"  - {rel.get('entity1')} {rel.get('relation_type')} {rel.get('entity2')}")

else:
    print("\n[ERROR] entity_graph.json not found")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
