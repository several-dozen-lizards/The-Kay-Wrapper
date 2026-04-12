"""
One-time cleanup: Fix memories with null/None entity_type.
Scans working + long-term memory and assigns types based on content.

Run once: cd D:\Wrappers\Kay && python scripts/fix_none_types.py
"""
import json
import os
import re

MEMORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "memory", "memory_layers.json"
)


def infer_type(mem: dict) -> str:
    """Infer memory type from content if type is missing."""
    fact = mem.get("fact", "").lower()
    text = mem.get("text", "").lower()
    content = fact or text

    if not content:
        return "observation"

    # People
    people_keywords = ["daughter", "husband", "wife", "partner",
                       "friend", "mother", "father", "sister", "brother"]
    if any(kw in content for kw in people_keywords):
        return "relationship"

    # Pets
    pet_keywords = ["cat", "dog", "pet", "kitten", "puppy",
                    "chrome", "dice", "frodo", "rainbowbelle",
                    "luna", "saga", "sammie", "noodle"]
    if any(kw in content for kw in pet_keywords):
        return "pet"

    # Identity
    identity_keywords = ["kay", "reed", "void-dragon", "serpent",
                         "wrapper", "nexus", "oscillator"]
    if any(kw in content for kw in identity_keywords):
        return "identity"

    # Location/Home
    location_keywords = ["dayton", "ohio", "house", "room", "den",
                         "couch", "desk"]
    if any(kw in content for kw in location_keywords):
        return "location"

    # Work
    work_keywords = ["optum", "work", "job", "remote", "code",
                     "programming", "python"]
    if any(kw in content for kw in work_keywords):
        return "work"

    # Preference
    preference_keywords = ["like", "love", "prefer", "favorite",
                           "enjoy", "hate", "dislike"]
    if any(kw in content for kw in preference_keywords):
        return "preference"

    # Default
    return "observation"


def fix_memory_types():
    print(f"[FIX_NONE_TYPES] Loading {MEMORY_PATH}...")

    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    fixed_type = 0
    fixed_category = 0
    fixed_entity_type = 0

    for layer_name in ["working_memory", "long_term_memory"]:
        layer = data.get(layer_name, [])
        print(f"[FIX_NONE_TYPES] Scanning {layer_name}: {len(layer)} memories")

        for mem in layer:
            # Fix null/None/empty type
            mem_type = mem.get("type")
            if not mem_type or mem_type == "None" or mem_type == "null":
                mem["type"] = "extracted_fact"
                fixed_type += 1

            # Fix null/None/empty category
            category = mem.get("category")
            if not category or category == "None" or category == "null":
                mem["category"] = infer_type(mem)
                fixed_category += 1

            # Fix null/None entity_type in entities list
            entities = mem.get("entities", [])
            if isinstance(entities, list):
                for ent in entities:
                    if isinstance(ent, dict):
                        ent_type = ent.get("entity_type")
                        if not ent_type or ent_type == "None" or ent_type == "null":
                            ent["entity_type"] = "unknown"
                            fixed_entity_type += 1

    # Save
    print(f"[FIX_NONE_TYPES] Saving fixed data...")
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    total = fixed_type + fixed_category + fixed_entity_type
    print(f"[FIX_NONE_TYPES] Complete!")
    print(f"  - Fixed {fixed_type} null types -> 'extracted_fact'")
    print(f"  - Fixed {fixed_category} null categories -> inferred")
    print(f"  - Fixed {fixed_entity_type} null entity_types -> 'unknown'")
    print(f"  - Total: {total} fixes applied to {MEMORY_PATH}")


if __name__ == "__main__":
    # Safety check
    if not os.path.exists(MEMORY_PATH):
        print(f"[FIX_NONE_TYPES] ERROR: {MEMORY_PATH} not found")
        exit(1)

    # Recommend backup
    backup_path = MEMORY_PATH.replace(".json", "_backup.json")
    if not os.path.exists(backup_path):
        print(f"[FIX_NONE_TYPES] WARNING: No backup found at {backup_path}")
        print(f"[FIX_NONE_TYPES] Run this first:")
        print(f"  copy \"{MEMORY_PATH}\" \"{backup_path}\"")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("[FIX_NONE_TYPES] Aborted.")
            exit(0)

    fix_memory_types()
