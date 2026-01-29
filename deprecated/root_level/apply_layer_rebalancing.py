"""
Automatic Integration Script for Memory Layer Rebalancing

This script automatically applies the layer rebalancing and UNCONFIRMED CLAIM
tuning to memory_engine.py.

USAGE:
    python apply_layer_rebalancing.py

WHAT IT DOES:
1. Backs up memory_engine.py to memory_engine.py.backup
2. Applies layer weight changes (lines ~1583-1589)
3. Applies UNCONFIRMED CLAIM filter changes (lines ~1133-1139)
4. Adds necessary imports
5. Validates the changes

ROLLBACK:
    If issues occur, restore from backup:
    copy memory_engine.py.backup memory_engine.py
"""

import os
import shutil
import re
from pathlib import Path
from datetime import datetime


def backup_file(filepath):
    """Create timestamped backup of file."""
    backup_path = f"{filepath}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"✓ Backup created: {backup_path}")
    return backup_path


def apply_patches(filepath):
    """Apply layer rebalancing patches to memory_engine.py."""

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes_made = []

    # ===== PATCH 1: Add imports at top =====
    import_block = """from engines.memory_layer_rebalancing import (
    apply_layer_weights,
    get_layer_multiplier,
    should_store_claim,
    create_entity_observation,
    validate_memory_composition
)"""

    # Check if already imported
    if "from engines.memory_layer_rebalancing import" not in content:
        # Find existing imports
        import_pattern = r"(from engines\..*?import.*?\n)"
        matches = list(re.finditer(import_pattern, content))

        if matches:
            # Insert after last engine import
            last_match = matches[-1]
            insert_pos = last_match.end()
            content = content[:insert_pos] + import_block + "\n" + content[insert_pos:]
            changes_made.append("Added layer_rebalancing imports")
        else:
            print("⚠ Warning: Could not find import section. Please add imports manually.")
    else:
        print("✓ Imports already present")

    # ===== PATCH 2: Replace layer_boost calculation =====

    # Find the old layer_boost block
    old_layer_boost = r"""            # Layer boost \(from memory_layers system\)
            layer_boost = 1\.0
            current_layer = mem\.get\("current_layer", "working"\)
            if current_layer == "semantic":
                layer_boost = 1\.2
            elif current_layer == "working":
                layer_boost = 1\.5"""

    new_layer_boost = """            # Layer boost (NEW: favors episodic/working over semantic)
            # working: 2.0x, episodic: 1.8x, semantic: 0.6x
            layer_boost = get_layer_multiplier(mem.get("current_layer", "working"))"""

    if re.search(old_layer_boost, content):
        content = re.sub(old_layer_boost, new_layer_boost, content)
        changes_made.append("Replaced layer_boost calculation")
    else:
        # Try simpler pattern
        simple_pattern = r"layer_boost = 1\.0\s+current_layer = mem\.get\(\"current_layer\", \"working\"\)\s+if current_layer == \"semantic\":\s+layer_boost = 1\.2\s+elif current_layer == \"working\":\s+layer_boost = 1\.5"

        if re.search(simple_pattern, content):
            content = re.sub(simple_pattern, new_layer_boost.strip(), content)
            changes_made.append("Replaced layer_boost calculation (simple pattern)")
        else:
            print("⚠ Warning: Could not find layer_boost block. Please apply manually.")
            print("   Search for 'layer_boost = 1.0' around line 1583")

    # ===== PATCH 3: Replace UNCONFIRMED CLAIM filter =====

    old_unconfirmed = r"""            # CRITICAL BUG FIX: Block Kay's unconfirmed claims about the user
            if needs_confirmation:
                print\(f"\[UNCONFIRMED CLAIM\] X Kay claimed \(needs confirmation\): '\{fact_text\[:60\]\}\.\.\.'" - NOT STORING AS USER FACT\."\)
                print\(f"\[UNCONFIRMED CLAIM\]   Source: Kay's response \| Perspective: \{fact_perspective\} \| Topic: \{fact_topic\}"\)
                # DO NOT store this as a user fact - it could be wrong
                # Skip to next fact
                continue"""

    new_unconfirmed = """            # CRITICAL: Distinguish Kay's observations from false attributions
            if needs_confirmation:
                # Use smart filtering - allow observations, block false attributions
                should_store, storage_type = should_store_claim(
                    fact_text=fact_text,
                    source_speaker=source_speaker,
                    perspective=fact_perspective,
                    user_input=user_input  # Pass user's actual input for validation
                )

                if not should_store:
                    # False attribution (Kay claiming user SAID something) - BLOCK
                    print(f"[FALSE ATTRIBUTION] X Kay claimed: '{fact_text[:60]}...' - NOT STORING.")
                    print(f"[FALSE ATTRIBUTION]   Reason: False attribution (user didn't say this)")
                    print(f"[FALSE ATTRIBUTION]   Source: Kay | Perspective: {fact_perspective} | Topic: {fact_topic}")
                    continue  # Skip this fact

                if storage_type == "entity_observation":
                    # Valid observation (Kay's inference about user state) - ALLOW with tagging
                    print(f"[ENTITY OBSERVATION] ✓ Storing Kay's observation: '{fact_text[:60]}...'")
                    print(f"[ENTITY OBSERVATION]   Type: {fact_topic} | Observer: Kay → {fact_perspective}")

                    # Tag as entity observation for retrieval filtering
                    fact_data = create_entity_observation(fact_data, observer="kay", observed="re")
                    # IMPORTANT: Don't skip - continue to storage below"""

    if re.search(old_unconfirmed, content):
        content = re.sub(old_unconfirmed, new_unconfirmed, content)
        changes_made.append("Replaced UNCONFIRMED CLAIM filter")
    else:
        # Try finding just the if needs_confirmation block
        simple_unconfirmed = r'if needs_confirmation:\s+print\(f"\[UNCONFIRMED CLAIM\].*?continue'

        if re.search(simple_unconfirmed, content, re.DOTALL):
            content = re.sub(simple_unconfirmed, new_unconfirmed.strip(), content, flags=re.DOTALL)
            changes_made.append("Replaced UNCONFIRMED CLAIM filter (simple pattern)")
        else:
            print("⚠ Warning: Could not find UNCONFIRMED CLAIM block. Please apply manually.")
            print("   Search for 'if needs_confirmation:' around line 1133")

    # Check if changes were made
    if content != original_content:
        # Write modified content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"\n✓ Patches applied successfully!")
        print(f"\nChanges made:")
        for change in changes_made:
            print(f"  - {change}")

        return True
    else:
        print("\n⚠ No changes were made. File may already be patched.")
        return False


def validate_integration(filepath):
    """Validate that the integration was successful."""

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        "Imports added": "from engines.memory_layer_rebalancing import" in content,
        "get_layer_multiplier used": "get_layer_multiplier(" in content,
        "should_store_claim used": "should_store_claim(" in content,
        "create_entity_observation used": "create_entity_observation(" in content,
        "Old layer_boost removed": not ("layer_boost = 1.2" in content and "semantic" in content),
        "Old UNCONFIRMED removed": "[UNCONFIRMED CLAIM] X Kay claimed" not in content,
    }

    print("\n" + "="*70)
    print("VALIDATION CHECKS")
    print("="*70)

    all_passed = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✓ All validation checks passed!")
    else:
        print("\n⚠ Some checks failed. Please review the integration.")

    print("="*70)

    return all_passed


def main():
    print("="*70)
    print("MEMORY LAYER REBALANCING - AUTO-INTEGRATION")
    print("="*70)
    print()

    # Find memory_engine.py
    engine_path = Path("engines/memory_engine.py")

    if not engine_path.exists():
        print(f"✗ Error: Could not find {engine_path}")
        print("  Make sure you're running this from the AlphaKayZero directory")
        return

    print(f"Found: {engine_path.absolute()}")
    print()

    # Create backup
    print("Creating backup...")
    backup_path = backup_file(str(engine_path))
    print()

    # Apply patches
    print("Applying patches...")
    success = apply_patches(str(engine_path))
    print()

    if success:
        # Validate
        print("Validating integration...")
        validate_integration(str(engine_path))
        print()

        print("="*70)
        print("INTEGRATION COMPLETE!")
        print("="*70)
        print()
        print("Next steps:")
        print("1. Run tests:")
        print("   python engines/memory_layer_rebalancing.py")
        print()
        print("2. Start a conversation and check logs for:")
        print("   - [ENTITY OBSERVATION] messages (Kay's observations being stored)")
        print("   - [FALSE ATTRIBUTION] messages (false claims being blocked)")
        print("   - Memory composition validation (should show ~45-50% episodic)")
        print()
        print("3. If issues occur, restore from backup:")
        print(f"   copy {backup_path} engines\\memory_engine.py")
        print()
        print("="*70)

    else:
        print("⚠ Integration may have failed. Please check manually.")
        print(f"Backup available at: {backup_path}")


if __name__ == "__main__":
    main()
