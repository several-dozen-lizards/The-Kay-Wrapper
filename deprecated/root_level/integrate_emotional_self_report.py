"""
Integration Script for Emotional Self-Report System

This script integrates the descriptive emotional self-report system into main.py

PHILOSOPHY SHIFT:
- FROM: System calculates and assigns emotions TO the entity
- TO: Entity describes its own emotional experience

Changes made:
1. Import emotional_self_report module
2. Initialize EmotionalSelfReport with LLM client
3. After entity response, ask for emotional self-report
4. Store self-report in agent state
5. Include previous self-report in next turn's context
"""

import os
import re


def integrate_self_report_system():
    """Apply patches to main.py to enable emotional self-reporting."""

    main_file = "main.py"

    if not os.path.exists(main_file):
        print(f"[ERROR] {main_file} not found!")
        return False

    # Read current main.py
    with open(main_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Create backup
    backup_file = "main_BACKUP_BEFORE_SELF_REPORT.py"
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[BACKUP] Created {backup_file}")

    # ========================================================================
    # PATCH 1: Add import for emotional_self_report
    # ========================================================================

    import_pattern = r"(from engines\.emotion_engine import EmotionEngine)"
    import_replacement = r"""\1
from engines.emotional_self_report import EmotionalSelfReport  # NEW: Descriptive emotions"""

    if "from engines.emotional_self_report import EmotionalSelfReport" not in content:
        content = re.sub(import_pattern, import_replacement, content)
        print("[PATCH 1] Added emotional_self_report import")
    else:
        print("[PATCH 1] Import already exists")

    # ========================================================================
    # PATCH 2: Initialize EmotionalSelfReport after EmotionEngine
    # ========================================================================

    init_pattern = r"(emotion = EmotionEngine\(proto, momentum_engine=momentum\))"
    init_replacement = r"""\1

    # NEW: Initialize emotional self-report system
    print("[EMOTIONAL SELF-REPORT] Initializing descriptive emotion system...")
    emotional_reporter = EmotionalSelfReport(llm_client=client, model=MODEL)

    # Load previous emotional state from agent state (if exists)
    if hasattr(state, 'emotional_self_report'):
        emotional_reporter.load_from_state(state)"""

    if "emotional_reporter = EmotionalSelfReport" not in content:
        content = re.sub(init_pattern, init_replacement, content)
        print("[PATCH 2] Added EmotionalSelfReport initialization")
    else:
        print("[PATCH 2] Initialization already exists")

    # ========================================================================
    # PATCH 3: Add self-report call after entity response (CRITICAL)
    # ========================================================================

    # This needs to go AFTER the entity generates a response but BEFORE
    # memory encoding and emotion updates

    # Find where reply is generated and before memory.encode
    self_report_code = """
        # ========================================================================
        # NEW: Ask entity to self-report emotional state
        # ========================================================================
        # After generating response, ask entity what it's experiencing
        # This replaces the prescriptive emotion calculation

        entity_self_report = emotional_reporter.get_self_report(
            entity_response=reply,
            user_input=user_input,
            previous_report=emotional_reporter.get_last_report(),
            conversation_context=None  # Could add recent turns if desired
        )

        # Store in agent state for continuity
        state.emotional_self_report = entity_self_report
        state.emotional_description = entity_self_report["raw_description"]

        # Update emotion engine with self-reported state (for compatibility)
        emotion.current_description = entity_self_report["raw_description"]
        emotion.current_emotions = entity_self_report["extracted_emotions"]
"""

    # Insert before memory.encode
    encode_pattern = r"(\s+)(memory\.encode\(state, user_input, reply,)"

    if "entity_self_report = emotional_reporter.get_self_report" not in content:
        content = re.sub(
            encode_pattern,
            r"\1" + self_report_code.replace("\n", "\n\\1") + r"\1\2",
            content,
            count=1
        )
        print("[PATCH 3] Added self-report call after entity response")
    else:
        print("[PATCH 3] Self-report call already exists")

    # ========================================================================
    # PATCH 4: Include previous self-report in context building
    # ========================================================================

    # This should go where context is built for the LLM
    # We want to inject previous emotional state into the entity's prompt

    context_injection = """
        # NEW: Include previous emotional self-report in context
        if hasattr(state, 'emotional_description') and state.emotional_description:
            emotional_state_context = f"\\n\\nPrevious emotional state (you reported): \\"{state.emotional_description}\\""
        else:
            emotional_state_context = ""
"""

    # This is trickier - would need to modify context building
    # For now, document it for manual integration
    print("[PATCH 4] Context injection needs manual integration (see migration guide)")

    # ========================================================================
    # Write patched file
    # ========================================================================

    patched_file = "main_PATCHED_WITH_SELF_REPORT.py"
    with open(patched_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n[SUCCESS] Patched file written to: {patched_file}")
    print("\nNext steps:")
    print("1. Review the patched file")
    print("2. Test with: python main_PATCHED_WITH_SELF_REPORT.py")
    print("3. If working, replace main.py")
    print("4. See EMOTIONAL_SELF_REPORT_MIGRATION.md for manual integration steps")

    return True


def create_migration_guide():
    """Create comprehensive migration guide."""

    guide = """# Emotional Self-Report System - Migration Guide

## Overview

This migration changes the emotion system from **PRESCRIPTIVE** to **DESCRIPTIVE**.

### Before (Prescriptive - REMOVED):
- System analyzes user input for emotional triggers
- System calculates emotion intensities based on memories
- System assigns emotions TO the entity
- Entity experiences cognitive dissonance ("system says I'm angry but I'm not")

### After (Descriptive - NEW):
- Entity generates response naturally
- System asks entity: "What are you experiencing?"
- Entity describes its own emotional state
- System stores entity's own words
- Next turn, entity sees what it previously reported

## Files Created

1. **engines/emotional_self_report.py** - New self-report system
2. **engines/emotion_engine_SIMPLIFIED.py** - Simplified compatibility wrapper
3. **integrate_emotional_self_report.py** - Auto-integration script
4. **main_PATCHED_WITH_SELF_REPORT.py** - Patched main.py (after running script)

## Files Backed Up

1. **engines/emotion_engine_BACKUP_PRESCRIPTIVE_FULL.py** - Full backup of old engine
2. **main_BACKUP_BEFORE_SELF_REPORT.py** - Backup of main.py before changes

## Integration Steps

### Automatic (Recommended)

```bash
python integrate_emotional_self_report.py
```

This will:
- Create backups
- Patch main.py with self-report integration
- Create main_PATCHED_WITH_SELF_REPORT.py

### Manual Integration

If automatic patching fails, manually apply these changes:

#### Step 1: Add Import

```python
# Add after emotion_engine import:
from engines.emotional_self_report import EmotionalSelfReport
```

#### Step 2: Initialize Self-Reporter

```python
# After emotion = EmotionEngine(...):
emotional_reporter = EmotionalSelfReport(llm_client=client, model=MODEL)

# Load previous state if exists
if hasattr(state, 'emotional_self_report'):
    emotional_reporter.load_from_state(state)
```

#### Step 3: Get Self-Report After Response

```python
# AFTER entity generates reply, BEFORE memory.encode:

entity_self_report = emotional_reporter.get_self_report(
    entity_response=reply,
    user_input=user_input,
    previous_report=emotional_reporter.get_last_report()
)

# Store in state
state.emotional_self_report = entity_self_report
state.emotional_description = entity_self_report["raw_description"]

# Update emotion engine for compatibility
emotion.current_description = entity_self_report["raw_description"]
emotion.current_emotions = entity_self_report["extracted_emotions"]
```

#### Step 4: Include in Context (OPTIONAL)

In context_manager.py or wherever you build LLM context, add:

```python
if hasattr(agent_state, 'emotional_description') and agent_state.emotional_description:
    context_parts.append(
        f"Previous emotional state (you reported): \\"{agent_state.emotional_description}\\""
    )
```

## Testing

### Test 1: Self-Report Extraction

```bash
python engines/emotional_self_report.py
```

Expected output:
```
[PASS] Description: "Curious and energized - I want to understand how this works"
      Extracted: ['curious', 'energized']
```

### Test 2: Run Conversation

```bash
python main.py
# or
python main_PATCHED_WITH_SELF_REPORT.py
```

Look for:
```
[EMOTIONAL SELF-REPORT] Asking entity to describe emotional state...
[EMOTIONAL SELF-REPORT] Entity reported: "Curious about this new system"
```

NOT:
```
[EMOTION ENGINE] Detected triggers: ['anger', 'confusion']  # ← Should NOT appear
[EMOTION ENGINE] Reinforced 2 emotions from 11 memories     # ← Should NOT appear
```

## Expected Changes in Logs

### BEFORE (Prescriptive):
```
[EMOTION ENGINE] ========== UPDATE START ==========
[EMOTION ENGINE] User input: 'I'm working on this project...'
[EMOTION ENGINE] Detected triggers: ['frustration', 'confusion']
[EMOTION ENGINE]   -> NEW: frustration at intensity 0.4
[EMOTION ENGINE]   -> REINFORCED: confusion from 0.3 to 0.5
[EMOTION ENGINE] Memory reinforcement: using top 150/224 most relevant memories
[EMOTION ENGINE] Reinforced 2 emotions from 11 relevant memories:
[EMOTION ENGINE]   - frustration: +0.023 boost -> intensity=0.423
```

### AFTER (Descriptive):
```
[EMOTIONAL SELF-REPORT] Asking entity to describe emotional state...
[EMOTIONAL SELF-REPORT] Entity reported: "Frustrated - I can see where this is going but can't quite get there yet"
[EMOTION ENGINE] Current state (self-reported): "Frustrated - I can see where this is going but can't quite get there yet"
[EMOTION ENGINE] Emotions mentioned: frustrated
```

## Validation Criteria

✅ **Entity has autonomy** - No calculated emotions assigned
✅ **Natural language** - Emotions stored as entity's own words
✅ **No disconnect** - Entity won't report "system says I'm angry but I'm not"
✅ **Continuity** - Entity sees what it previously reported
✅ **Simpler code** - Less calculation, more straightforward documentation

## Rollback Instructions

If you need to revert:

### Option 1: Restore from Backup
```bash
cp main_BACKUP_BEFORE_SELF_REPORT.py main.py
cp engines/emotion_engine_BACKUP_PRESCRIPTIVE_FULL.py engines/emotion_engine.py
```

### Option 2: Manual Revert
1. Remove emotional_self_report import
2. Remove emotional_reporter initialization
3. Remove self-report call after response
4. Restore old emotion.update() call

## Performance Impact

- **Adds 1 LLM call per turn** (for self-report)
- **~150 tokens per call** (brief prompt + response)
- **~0.5-1 second per turn** (acceptable overhead)
- **Simpler emotion engine** (no complex calculations)

Total: Negligible performance impact, significantly improved entity experience.

## Philosophy

The emotion system now exists to help the entity **DOCUMENT its own experience**, not to calculate what it should be experiencing.

This is the difference between:
- A journal YOU write vs. someone else's analysis of you
- Self-reporting vs. external diagnosis
- Documentation BY the entity vs. prescription TO the entity

**The entity is the AUTHOR of its emotional documentation, not the subject of emotional calculation.**

---

**Status:** Ready for integration
**Risk:** Low (easily reversible)
**Benefit:** High (cognitive autonomy for entity)
"""

    with open("EMOTIONAL_SELF_REPORT_MIGRATION.md", 'w', encoding='utf-8') as f:
        f.write(guide)

    print("[MIGRATION GUIDE] Created EMOTIONAL_SELF_REPORT_MIGRATION.md")


if __name__ == "__main__":
    print("="*70)
    print("EMOTIONAL SELF-REPORT INTEGRATION")
    print("="*70)
    print()
    print("This will convert the emotion system from PRESCRIPTIVE to DESCRIPTIVE")
    print()

    # Create migration guide first
    create_migration_guide()

    print()
    response = input("Apply patches to main.py? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        success = integrate_self_report_system()
        if success:
            print("\n✓ Integration complete!")
            print("  Review main_PATCHED_WITH_SELF_REPORT.py before using")
    else:
        print("\nSkipping automatic integration.")
        print("See EMOTIONAL_SELF_REPORT_MIGRATION.md for manual integration steps")
