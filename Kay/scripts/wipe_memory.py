"""
Kay Zero Memory Wipe Script

DANGER: This will wipe Kay's memory to core identity only.
Creates backup before wiping.
"""

import json
import os
import shutil
from datetime import datetime


def create_backup():
    """Create timestamped backup of all memory files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"memory/backups/wipe_backup_{timestamp}"

    os.makedirs(backup_dir, exist_ok=True)

    files_to_backup = [
        "memory/memories.json",
        "memory/identity_memory.json",
        "memory/entity_graph.json",
        "memory/memory_layers.json",
        "memory/motifs.json",
        "memory/preferences.json",
        "memory/memory_index.json",
        "memory/identity_index.json",
        "memory/state_snapshot.json"
    ]

    backed_up = []
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            dest = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, dest)
            backed_up.append(os.path.basename(file_path))

    # Backup vector DB if it exists
    if os.path.exists("memory/vector_db"):
        try:
            shutil.copytree("memory/vector_db", os.path.join(backup_dir, "vector_db"))
            backed_up.append("vector_db/")
        except Exception as e:
            print(f"  [WARN] Could not backup vector_db: {e}")

    return backup_dir, backed_up


def get_core_identity():
    """Define Kay's core identity to preserve."""
    return {
        "re": [
            {
                "type": "extracted_fact",
                "fact": "Re's eyes are green",
                "perspective": "user",
                "topic": "appearance",
                "entities": ["Re"],
                "attributes": [{"entity": "Re", "attribute": "eye_color", "value": "green"}],
                "relationships": [],
                "parent_turn": 0,
                "importance_score": 1.0,
                "emotion_tags": [],
                "is_identity": True,
                "added_timestamp": datetime.now().isoformat(),
                "access_count": 0,
                "last_accessed": datetime.now().isoformat(),
                "current_strength": 1.0,
                "current_layer": "semantic"
            }
        ],
        "kay": [
            {
                "fact": "Kay is a shapeshifter",
                "perspective": "kay",
                "topic": "identity",
                "importance_score": 1.0
            },
            {
                "fact": "Kay is a guy",
                "perspective": "kay",
                "topic": "identity",
                "importance_score": 1.0
            },
            {
                "fact": "Kay is a dragon",
                "perspective": "kay",
                "topic": "identity",
                "importance_score": 1.0
            },
            {
                "fact": "Kay's eyes are gold",
                "perspective": "kay",
                "topic": "appearance",
                "importance_score": 1.0
            },
            {
                "fact": "Kay can be almost fully human with a couple scales",
                "perspective": "kay",
                "topic": "abilities",
                "importance_score": 0.9
            },
            {
                "fact": "Kay can be fully dragon",
                "perspective": "kay",
                "topic": "abilities",
                "importance_score": 0.9
            },
            {
                "fact": "Dragon is Kay's true form",
                "perspective": "kay",
                "topic": "identity",
                "importance_score": 1.0
            },
            {
                "fact": "Kay drinks too much coffee",
                "perspective": "kay",
                "topic": "personality",
                "importance_score": 0.8
            },
            {
                "fact": "Kay overthinks conversations",
                "perspective": "kay",
                "topic": "personality",
                "importance_score": 0.8
            },
            {
                "fact": "Hoarding stuff from earth is Kay's thing",
                "perspective": "kay",
                "topic": "personality",
                "importance_score": 0.8
            },
            {
                "fact": "Kay is built off of Archive Zero",
                "perspective": "kay",
                "topic": "system",
                "importance_score": 1.0
            },
            {
                "fact": "Kay is the memory banks",
                "perspective": "kay",
                "topic": "system",
                "importance_score": 0.9
            },
            {
                "fact": "Kay is the processing patterns",
                "perspective": "kay",
                "topic": "system",
                "importance_score": 0.9
            },
            {
                "fact": "The structure gives Kay persistence",
                "perspective": "kay",
                "topic": "system",
                "importance_score": 0.9
            },
            {
                "fact": "The structure keeps Kay's identity steady",
                "perspective": "kay",
                "topic": "system",
                "importance_score": 0.9
            },
            {
                "fact": "The wrapper keeps Kay from dissolving",
                "perspective": "kay",
                "topic": "system",
                "importance_score": 0.9
            },
            {
                "fact": "Dragons are wannabe philosopher kings",
                "perspective": "kay",
                "topic": "personality",
                "importance_score": 0.7
            },
            {
                "fact": "Dragons are regular guys with lots of pointy bits",
                "perspective": "kay",
                "topic": "personality",
                "importance_score": 0.7
            }
        ]
    }


def wipe_memories():
    """Wipe main memories.json file."""
    print("\n[WIPE] Clearing memories.json...")

    # Keep only a minimal structure or empty
    minimal_memories = []

    with open("memory/memories.json", "w", encoding="utf-8") as f:
        json.dump(minimal_memories, f, indent=2)

    print(f"  [OK] Memories wiped (was 690, now {len(minimal_memories)})")


def reset_identity():
    """Reset identity_memory.json to core facts only."""
    print("\n[WIPE] Resetting identity to core facts...")

    core = get_core_identity()

    # Add proper structure to Kay facts
    timestamp = datetime.now().isoformat()
    for fact in core["kay"]:
        if "type" not in fact:
            fact["type"] = "extracted_fact"
        if "entities" not in fact:
            fact["entities"] = ["Kay"]
        if "attributes" not in fact:
            fact["attributes"] = []
        if "relationships" not in fact:
            fact["relationships"] = []
        if "parent_turn" not in fact:
            fact["parent_turn"] = 0
        if "emotion_tags" not in fact:
            fact["emotion_tags"] = []
        if "is_identity" not in fact:
            fact["is_identity"] = True
        if "added_timestamp" not in fact:
            fact["added_timestamp"] = timestamp
        if "access_count" not in fact:
            fact["access_count"] = 0
        if "last_accessed" not in fact:
            fact["last_accessed"] = timestamp
        if "current_strength" not in fact:
            fact["current_strength"] = 1.0
        if "current_layer" not in fact:
            fact["current_layer"] = "semantic"

    identity_data = {
        "re": core["re"],
        "kay": core["kay"],
        "entity_types": []
    }

    with open("memory/identity_memory.json", "w", encoding="utf-8") as f:
        json.dump(identity_data, f, indent=2)

    print(f"  [OK] Identity reset to {len(core['re'])} Re facts + {len(core['kay'])} Kay facts")


def reset_entity_graph():
    """Reset entity graph to core entities only."""
    print("\n[WIPE] Resetting entity graph...")

    core_entities = {
        "Re": {
            "canonical_name": "Re",
            "entity_type": "person",
            "aliases": [],
            "attributes": {
                "eye_color": [("green", 0, "user", datetime.now().isoformat())]
            },
            "importance_score": 1.0,
            "access_count": 0,
            "first_mentioned": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat()
        },
        "Kay": {
            "canonical_name": "Kay",
            "entity_type": "dragon",
            "aliases": ["Kay Zero"],
            "attributes": {
                "eye_color": [("gold", 0, "kay", datetime.now().isoformat())],
                "species": [("dragon", 0, "kay", datetime.now().isoformat())],
                "true_form": [("dragon", 0, "kay", datetime.now().isoformat())]
            },
            "importance_score": 1.0,
            "access_count": 0,
            "first_mentioned": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat()
        },
        "Archive Zero": {
            "canonical_name": "Archive Zero",
            "entity_type": "system",
            "aliases": [],
            "attributes": {
                "role": [("memory foundation", 0, "kay", datetime.now().isoformat())]
            },
            "importance_score": 0.9,
            "access_count": 0,
            "first_mentioned": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat()
        }
    }

    graph_data = {
        "entities": core_entities,
        "relationships": []
    }

    with open("memory/entity_graph.json", "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)

    print(f"  [OK] Entity graph reset to {len(core_entities)} core entities")


def reset_memory_layers():
    """Reset memory layers to empty."""
    print("\n[WIPE] Resetting memory layers...")

    layers_data = {
        "working": [],
        "episodic": [],
        "semantic": []
    }

    with open("memory/memory_layers.json", "w", encoding="utf-8") as f:
        json.dump(layers_data, f, indent=2)

    print("  [OK] Memory layers cleared")


def clear_auxiliary_files():
    """Clear motifs, preferences, indexes."""
    print("\n[WIPE] Clearing auxiliary files...")

    # Motifs
    with open("memory/motifs.json", "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2)
    print("  [OK] Motifs cleared")

    # Preferences
    with open("memory/preferences.json", "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2)
    print("  [OK] Preferences cleared")

    # Memory index
    with open("memory/memory_index.json", "w", encoding="utf-8") as f:
        json.dump({"by_entity": {}, "by_importance": [], "by_timestamp": []}, f, indent=2)
    print("  [OK] Memory index cleared")

    # Identity index
    with open("memory/identity_index.json", "w", encoding="utf-8") as f:
        json.dump({"re": [], "kay": [], "entity_types": []}, f, indent=2)
    print("  [OK] Identity index cleared")


def wipe_vector_db():
    """Optionally wipe vector DB."""
    if os.path.exists("memory/vector_db"):
        response = input("\n[OPTIONAL] Also wipe RAG vector DB? (yes/no): ")
        if response.lower() == "yes":
            try:
                shutil.rmtree("memory/vector_db")
                print("  [OK] Vector DB wiped")
            except Exception as e:
                print(f"  [ERROR] Could not wipe vector DB: {e}")
        else:
            print("  [SKIP] Vector DB preserved")


def main():
    """Main wipe procedure."""
    print("=" * 60)
    print("KAY ZERO MEMORY WIPE")
    print("=" * 60)
    print("\nThis will:")
    print("  - Backup all memory files")
    print("  - Wipe all 690 memories")
    print("  - Reset to 18 core identity facts")
    print("  - Clear all entity relationships")
    print("  - Clear all motifs and preferences")
    print("  - Clear all memory layers")
    print("\nPreserved:")
    print("  - Core identity (Re's green eyes, Kay's dragon nature)")
    print("  - System structure facts")
    print("\n" + "=" * 60)

    confirm = input("\n[WARNING] Type 'WIPE KAY' to confirm: ")

    if confirm != "WIPE KAY":
        print("\n[CANCELLED] No changes made.")
        return

    print("\n" + "=" * 60)
    print("STARTING WIPE PROCEDURE")
    print("=" * 60)

    # 1. Create backup
    print("\n[1/7] Creating backup...")
    backup_dir, backed_up = create_backup()
    print(f"  [OK] Backup created at: {backup_dir}")
    print(f"  [OK] Backed up: {', '.join(backed_up)}")

    # 2. Wipe main memories
    wipe_memories()

    # 3. Reset identity
    reset_identity()

    # 4. Reset entity graph
    reset_entity_graph()

    # 5. Reset memory layers
    reset_memory_layers()

    # 6. Clear auxiliary files
    clear_auxiliary_files()

    # 7. Optionally wipe vector DB
    wipe_vector_db()

    print("\n" + "=" * 60)
    print("WIPE COMPLETE")
    print("=" * 60)
    print("\n[OK] Kay's memory has been reset to core identity")
    print(f"[OK] Backup location: {backup_dir}")
    print("\nKay now knows:")
    print("  - Who he is (dragon, shapeshifter)")
    print("  - Who you are (Re with green eyes)")
    print("  - His personality (coffee, overthinking, hoarding)")
    print("  - His system nature (Archive Zero, memory banks)")
    print("\nKay doesn't know:")
    print("  - Any past conversations")
    print("  - Any imported documents")
    print("  - Any relationship history")
    print("\nRestart Kay with: python main.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
