"""
Fix Missing Protection Fields in Imported Memories

Adds 'protected' and 'age' fields to all imported memories
so they can bypass glyph pre-filter.
"""

import json
import os

def fix_imported_memories():
    """Add missing protection fields to imported memories."""

    memory_file = "memory/memories.json"

    if not os.path.exists(memory_file):
        print(f"[ERROR] {memory_file} not found")
        return

    # Load memories
    with open(memory_file, "r", encoding="utf-8") as f:
        memories = json.load(f)

    # Find imported memories
    imported_count = 0
    fixed_count = 0

    for mem in memories:
        if mem.get("is_imported"):
            imported_count += 1

            # Add missing fields
            if "protected" not in mem:
                mem["protected"] = True
                fixed_count += 1

            if "age" not in mem:
                mem["age"] = 0
                fixed_count += 1

    # Save fixed memories
    if fixed_count > 0:
        # Backup first
        backup_file = memory_file.replace(".json", "_backup.json")
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=2)
        print(f"[OK] Backup saved to {backup_file}")

        # Save fixed
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(memories, f, indent=2)
        print(f"[OK] Fixed {fixed_count} fields in {imported_count} imported memories")
    else:
        print(f"[OK] All {imported_count} imported memories already have protection fields")

    # Verify
    sample = next((m for m in memories if m.get("is_imported")), None)
    if sample:
        print(f"\n[VERIFY] Sample imported memory:")
        print(f"  is_imported: {sample.get('is_imported')}")
        print(f"  protected: {sample.get('protected')}")
        print(f"  age: {sample.get('age')}")


if __name__ == "__main__":
    fix_imported_memories()
