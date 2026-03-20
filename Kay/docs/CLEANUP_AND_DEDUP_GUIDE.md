# Memory Cleanup & Deduplication Guide

## Quick Start

### Clean Kay's Memory (Fresh Start)

```bash
# Show current memory stats
python cleanup_memory.py --stats

# Clean memory (creates automatic backup)
python cleanup_memory.py --clean

# Clean but keep identity facts (recommended)
python cleanup_memory.py --clean --keep-identity

# Preview cleanup without actually doing it
python cleanup_memory.py --clean --dry-run
```

### Restore from Backup

```bash
# List available backups
python cleanup_memory.py --list-backups

# Restore from specific backup
python cleanup_memory.py --restore memory/backups/backup_20241027_150000
```

---

## Memory Cleanup Tool

### Features

✅ **Automatic Backup** - Creates timestamped backup before any deletion
✅ **Safe Deletion** - Requires confirmation before cleaning
✅ **Preserve Identity** - Option to keep Re and Kay's core facts
✅ **Dry Run Mode** - Preview changes without executing
✅ **Statistics** - View memory stats before/after
✅ **Easy Restore** - Restore from any backup with one command

### Commands

#### Show Statistics
```bash
python cleanup_memory.py --stats
```

**Output:**
```
MEMORY STATISTICS
======================================================================

Total memories: 1407
  - Live conversation: 1402
  - Imported: 5

Entities: 76

Identity facts:
  - Re: 25
  - Kay: 16

By type:
  - full_turn: 450
  - extracted_fact: 920
  - glyph_summary: 37
```

#### Clean Memory (Fresh Start)
```bash
python cleanup_memory.py --clean
```

**What it does:**
1. Shows current memory stats
2. Asks for confirmation
3. Creates timestamped backup
4. Deletes all memory files
5. Creates fresh, empty memory files
6. Shows before/after stats

**Output:**
```
[WARNING] This will DELETE all memories and create fresh start!
Type 'yes' to confirm: yes

[BACKUP] Creating backup...
[BACKUP] Complete! Saved to: memory/backups/backup_20241027_152030
[BACKUP] Backed up 6 files

[CLEANUP] Creating fresh memory files...
  [CREATED] memories.json (empty)
  [CREATED] entity_graph.json (empty)
  [CREATED] memory_layers.json (empty)
  [CREATED] identity_memory.json (empty)
  [CREATED] preferences.json (empty)
  [CREATED] motifs.json (empty)

[CLEANUP] Complete!
  Memories: 1407 → 0
  Entities: 76 → 0
```

#### Clean but Keep Identity
```bash
python cleanup_memory.py --clean --keep-identity
```

**Recommended for most users!**

Preserves:
- ✅ Re's identity facts (name, pets, family, etc.)
- ✅ Kay's identity facts (personality, preferences)
- ✅ Entity facts ([cat], [dog], [partner], etc.)

Deletes:
- ❌ All conversation history
- ❌ All imported archives
- ❌ Emotional tags, motifs, preferences

**Best for:** Starting fresh while keeping "who is who" information.

#### Dry Run (Preview)
```bash
python cleanup_memory.py --clean --dry-run
python cleanup_memory.py --clean --keep-identity --dry-run
```

Shows what would be deleted **without actually deleting**.

#### List Backups
```bash
python cleanup_memory.py --list-backups
```

**Output:**
```
AVAILABLE BACKUPS
======================================================================

Found 3 backup(s):

1. backup_20241027_152030
   Path: memory/backups/backup_20241027_152030
   Files: 6

2. backup_20241027_143500
   Path: memory/backups/backup_20241027_143500
   Files: 6

3. backup_20241026_091200
   Path: memory/backups/backup_20241026_091200
   Files: 6
```

#### Restore from Backup
```bash
python cleanup_memory.py --restore memory/backups/backup_20241027_152030
```

**Output:**
```
RESTORE FROM BACKUP
======================================================================

[RESTORE] Found 6 files in backup:
  - memories.json (845.7 KB)
  - entity_graph.json (54.3 KB)
  - memory_layers.json (546.5 KB)
  - identity_memory.json (67.9 KB)
  - preferences.json (18.5 KB)
  - motifs.json (12.1 KB)

Type 'yes' to confirm restore: yes

[RESTORE] Restoring files...
  [RESTORED] memories.json
  [RESTORED] entity_graph.json
  [RESTORED] memory_layers.json
  [RESTORED] identity_memory.json
  [RESTORED] preferences.json
  [RESTORED] motifs.json

[RESTORE] Complete!
```

---

## Enhanced Deduplication

### Features

The import system now **prevents duplicates** automatically!

✅ **Within-Batch Dedup** - Removes duplicates in the import file
✅ **Database Dedup** - Checks against existing memories
✅ **Smart Normalization** - Handles punctuation, case, filler words
✅ **No Manual Cleanup** - Automatic on every import

### How It Works

#### Text Normalization

These are all considered **duplicates**:
- "[cat] is a dog"
- "[cat] is a dog."
- "[cat] is a dog!"
- "chrome is a dog"
- "CHROME IS A DOG"
- "[cat] is **the** dog" ← filler word removed
- "[cat] is **an** dog" ← filler word removed
- "  [cat] is a dog  " ← whitespace trimmed

All normalize to: **"chrome is dog"**

#### Deduplication Process

**Step 1:** Check within import batch
```
Import file contains:
  - "[cat] is a gray husky"
  - "[cat] is a gray husky."
  - "[dog] is a black labrador"

After dedup: 2 facts ([cat], [dog])
Removed: 1 duplicate
```

**Step 2:** Check against database
```
Database already has:
  - "[partner] teaches karate"

Import file contains:
  - "[partner] teaches karate"
  - "[partner] teaches karate."
  - "[partner] is a karate teacher"

After dedup: 1 fact (karate teacher variant)
Removed: 2 already in database
```

### Test Results

```bash
python test_deduplication.py
```

**Output:**
```
[TEST 1] Duplicates within import batch...
  Input: 4 facts
  Output: 2 unique facts
  [PASS] Within-batch deduplication works!

[TEST 2] Duplicates against existing database...
  Input: 3 facts
  Output: 1 unique facts
  [PASS] Database deduplication works!

[TEST 3] Text normalization...
  Tested 8 variations
  Unique normalized forms: 1
  [PASS] All variations normalized to same form!

Results: 3/3 passed
[SUCCESS] All deduplication tests passed!
```

### Import Logs

When importing, you'll see deduplication stats:

```
[DEDUP] Checking 45 new facts against 1402 existing memories
[DEDUP] Removed 12 duplicates:
  - 3 duplicates within import batch
  - 9 already in database
  - 33 unique facts will be imported
```

This means:
- Started with: 45 extracted facts
- Removed: 12 duplicates (3 internal, 9 from database)
- Importing: 33 new unique facts

---

## Typical Workflow

### Scenario: Fresh Start with Archive Import

```bash
# 1. Check current memory state
python cleanup_memory.py --stats

# 2. Clean memory (keep identity if desired)
python cleanup_memory.py --clean --keep-identity

# 3. Import archives (duplicates auto-removed)
python import_memories.py --input ./conversation_archives/

# 4. Rebuild indexes for fast retrieval
python build_memory_indexes.py

# 5. Start Kay
python main.py
```

### Scenario: Re-import Same File (No Duplicates)

```bash
# First import
python import_memories.py --input conversation.txt
# Output: "33 unique facts will be imported"

# Accidentally run again
python import_memories.py --input conversation.txt
# Output: "0 unique facts will be imported"
# "33 already in database"

# No duplicates created!
```

### Scenario: Oops, Need to Restore

```bash
# Made a mistake, want to undo
python cleanup_memory.py --list-backups

# Restore previous state
python cleanup_memory.py --restore memory/backups/backup_20241027_152030

# Everything back to normal!
```

---

## Configuration

### Adjust Deduplication Sensitivity

If you want to change how strict deduplication is, edit `memory_import/import_manager.py`:

```python
def _normalize_text(self, text: str) -> str:
    # Current: Removes a, an, the
    filler_words = [" a ", " an ", " the "]

    # Stricter: Remove more words
    filler_words = [" a ", " an ", " the ", " is ", " was "]

    # Looser: Keep all words
    filler_words = []
```

### Backup Location

Backups are saved to: `memory/backups/backup_YYYYMMDD_HHMMSS/`

To change location, edit `cleanup_memory.py`:

```python
# Default
backup_dir = f"memory/backups/backup_{timestamp}"

# Custom
backup_dir = f"/path/to/custom/backups/backup_{timestamp}"
```

---

## Safety Features

### Automatic Backup
Every cleanup creates a timestamped backup. **You can always restore.**

### Confirmation Required
Cleanup requires typing "yes" to confirm. **No accidental deletions.**

### Dry Run Mode
Preview changes before committing. **Test before executing.**

### Immutable Backups
Backups are never modified. **Safe restore point.**

### Preserve Identity Option
Keep "who is who" while cleaning conversation history. **Don't lose core facts.**

---

## Troubleshooting

### "No backups found"
**Cause:** No backups have been created yet
**Solution:** Run cleanup once to create first backup

### "Backup not found"
**Cause:** Invalid backup path
**Solution:** Use `--list-backups` to see available backups

### "Deduplication not working"
**Cause:** Text too different (legitimate variation)
**Solution:** Facts like "[cat] is a dog" vs "[cat] likes dogs" are correctly treated as different

### "Too many duplicates removed"
**Cause:** Normalization too aggressive
**Solution:** Adjust `filler_words` in `_normalize_text()`

### "Want to keep some memories"
**Cause:** Need selective cleanup
**Solution:** Manually edit `memory/memories.json` before cleanup, or export specific memories first

---

## Advanced: Manual Backup/Restore

### Manual Backup
```bash
# Create backup directory
mkdir -p memory/backups/manual_backup

# Copy memory files
cp memory/*.json memory/backups/manual_backup/
```

### Manual Restore
```bash
# Restore from manual backup
cp memory/backups/manual_backup/*.json memory/
```

### Export Specific Memories
```python
import json

# Load memories
memories = json.load(open('memory/memories.json'))

# Filter (keep only user perspective)
filtered = [m for m in memories if m.get('perspective') == 'user']

# Save
json.dump(filtered, open('memory/memories_user_only.json', 'w'), indent=2)
```

---

## Files Modified

1. **cleanup_memory.py** - New cleanup tool
2. **memory_import/import_manager.py** - Enhanced deduplication
3. **test_deduplication.py** - Deduplication tests

## Files Created

1. **CLEANUP_AND_DEDUP_GUIDE.md** - This guide
2. **memory/backups/** - Backup directory (created on first cleanup)

---

## Summary

**Cleanup Tool:**
- ✅ Safe deletion with automatic backup
- ✅ Preserve identity option
- ✅ Easy restore from any backup
- ✅ Dry run mode

**Enhanced Deduplication:**
- ✅ Prevents duplicate imports automatically
- ✅ Smart text normalization
- ✅ Checks both batch and database
- ✅ Detailed logging

**Ready to use!** Clean Kay's memory and re-import archives without creating duplicates.
