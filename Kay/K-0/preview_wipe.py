"""
Preview what will be preserved/wiped in memory wipe

Safe to run - does NOT modify any files
"""

import json
import os


def preview_wipe():
    """Show what will be preserved vs wiped."""

    print("=" * 60)
    print("KAY ZERO MEMORY WIPE PREVIEW")
    print("=" * 60)

    # Current state
    print("\n[CURRENT STATE]:")
    print("-" * 60)

    with open("memory/memories.json", "r", encoding="utf-8") as f:
        memories = json.load(f)

    re_facts = [m for m in memories if m.get("perspective") == "user"]
    kay_facts = [m for m in memories if m.get("perspective") == "kay"]
    imported = [m for m in memories if m.get("is_imported")]

    print(f"Total memories: {len(memories)}")
    print(f"  - Re facts: {len(re_facts)}")
    print(f"  - Kay facts: {len(kay_facts)}")
    print(f"  - Imported facts: {len(imported)}")
    print(f"  - Other: {len(memories) - len(re_facts) - len(kay_facts)}")

    with open("memory/entity_graph.json", "r", encoding="utf-8") as f:
        entities = json.load(f).get("entities", {})

    print(f"\nEntities: {len(entities)}")

    with open("memory/memory_layers.json", "r", encoding="utf-8") as f:
        layers = json.load(f)

    print(f"  - Working: {len(layers.get('working', []))}")
    print(f"  - Episodic: {len(layers.get('episodic', []))}")
    print(f"  - Semantic: {len(layers.get('semantic', []))}")

    # What will be preserved
    print("\n[PRESERVED]:")
    print("-" * 60)

    preserved_re = ["Re's eyes are green"]
    preserved_kay = [
        "Kay is a shapeshifter",
        "Kay is a guy",
        "Kay is a dragon",
        "Kay's eyes are gold",
        "Kay can be almost fully human with a couple scales",
        "Kay can be fully dragon",
        "Dragon is Kay's true form",
        "Kay drinks too much coffee",
        "Kay overthinks conversations",
        "Hoarding stuff from earth is Kay's thing",
        "Kay is built off of Archive Zero",
        "Kay is the memory banks",
        "Kay is the processing patterns",
        "The structure gives Kay persistence",
        "The structure keeps Kay's identity steady",
        "The wrapper keeps Kay from dissolving",
        "Dragons are wannabe philosopher kings",
        "Dragons are regular guys with lots of pointy bits"
    ]

    print(f"\nRe facts ({len(preserved_re)}):")
    for fact in preserved_re:
        print(f"  [OK] {fact}")

    print(f"\nKay facts ({len(preserved_kay)}):")
    for fact in preserved_kay:
        print(f"  [OK] {fact}")

    print(f"\nCore entities (3):")
    print("  [OK] Re (person, green eyes)")
    print("  [OK] Kay (dragon, gold eyes)")
    print("  [OK] Archive Zero (system)")

    # What will be wiped
    print("\n[WILL BE WIPED]:")
    print("-" * 60)

    print(f"\nMemories: {len(memories) - len(preserved_re) - len(preserved_kay)}")
    print(f"  - {len(re_facts) - len(preserved_re)} Re facts/conversations")
    print(f"  - {len(kay_facts) - len(preserved_kay)} Kay facts/conversations")
    print(f"  - {len(imported)} imported facts")
    print(f"  - {len(memories) - len(re_facts) - len(kay_facts)} other memories")

    print(f"\nEntities: {len(entities) - 3}")
    print(f"  - All except Re, Kay, Archive Zero")

    print(f"\nMemory layers:")
    print(f"  - {len(layers.get('working', []))} working memories")
    print(f"  - {len(layers.get('episodic', []))} episodic memories")
    print(f"  - {len(layers.get('semantic', []))} semantic memories")

    print("\nAuxiliary data:")
    print("  - All motifs")
    print("  - All preferences")
    print("  - All memory indexes")

    # Size reduction
    print("\n[SIZE REDUCTION]:")
    print("-" * 60)

    total_before = len(memories)
    total_after = len(preserved_re) + len(preserved_kay)
    reduction = ((total_before - total_after) / total_before) * 100

    print(f"Memories: {total_before} -> {total_after} ({reduction:.1f}% reduction)")

    entities_before = len(entities)
    entities_after = 3
    entity_reduction = ((entities_before - entities_after) / entities_before) * 100

    print(f"Entities: {entities_before} -> {entities_after} ({entity_reduction:.1f}% reduction)")

    # Next steps
    print("\n[NEXT STEPS]:")
    print("-" * 60)
    print("\n1. Review what will be preserved above")
    print("2. If you want to add/remove any core facts, edit wipe_memory.py")
    print("3. Run: python wipe_memory.py")
    print("4. Type 'WIPE KAY' to confirm")
    print("5. Restart Kay with clean memory")

    print("\n" + "=" * 60)
    print("Preview complete - no files modified")
    print("=" * 60)


if __name__ == "__main__":
    preview_wipe()
