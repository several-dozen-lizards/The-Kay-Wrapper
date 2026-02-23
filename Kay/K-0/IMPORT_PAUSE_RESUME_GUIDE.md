# Import Pause/Resume System - User Guide

## Overview

The import system now supports pausing/resuming imports and automatic duplicate detection. This prevents re-importing the same documents and allows you to safely interrupt long-running imports.

## Features

### 1. Pause/Resume Functionality
- **Pause at any time**: Click "Pause" during import to stop after the current file
- **Resume later**: Imports can be resumed after pausing, closing the app, or even crashes
- **Auto-recovery**: On startup, you'll be asked if you want to resume incomplete imports
- **Progress tracking**: See exactly how many files completed, failed, and remain

### 2. Duplicate Detection
- **Automatic checking**: Before importing, the system checks if files were already imported
- **Two types of duplicates**:
  - **Exact duplicates**: Same filename and content (file unchanged)
  - **Updated files**: Same filename but different content (file modified)
- **Three actions for each duplicate**:
  - **Skip**: Don't re-import (recommended for exact duplicates)
  - **Replace**: Delete old memories and re-import (for updated files)
  - **Import as Copy**: Keep both versions (creates new doc_id)

### 3. Crash Recovery
- All progress is saved after each file
- If the app crashes, you'll see a "Resume Import?" dialog on next startup
- State persisted to: `memory/import_state.json`

## How to Use

### Starting an Import

1. Click "Import" button in main UI
2. Select files or directory
3. Configure options (batch size, date filters, dry run)
4. Click "Start Import"
5. System checks for duplicates automatically

### Handling Duplicates

When duplicates are found, you'll see a dialog for each duplicate file:

**For Exact Duplicates:**
```
File "example.pdf" was already imported.

Originally imported: 2025-01-10 14:30
Memories created: 47

This is an exact duplicate (same content).

What would you like to do?
```

Recommended: **Skip** (no need to re-import identical content)

**For Updated Files:**
```
File "example.pdf" was previously imported.

Originally imported: 2025-01-10 14:30
Memories created: 47

The file content has CHANGED since last import.

What would you like to do?
```

Recommended: **Replace** (update memories with new content)

### Pausing an Import

1. During import, click "Pause" button
2. Import stops after current file completes
3. Progress is saved to disk
4. Button changes to "Resume Import"

### Resuming an Import

**After manual pause:**
1. Click "Resume Import" button
2. Import continues from where it stopped

**After app restart:**
1. Reopen Import window
2. System detects incomplete import
3. Dialog shows progress and asks to resume
4. Click "Yes" to continue

**After crash:**
1. Restart app
2. Open Import window
3. Dialog shows incomplete import found
4. Click "Yes" to resume from last completed file

### Canceling an Import

1. Click "Cancel" button
2. Dialog asks: "Save progress to resume later?"
   - **Yes**: State saved, can resume later
   - **No**: Progress discarded, fresh start next time

## File Locations

- **Import state**: `memory/import_state.json`
- **Documents registry**: `memory/documents.json`
- **Duplicate detection**: Uses SHA-256 hash of file content

## Technical Details

### State Tracking

Each import session tracks:
- `session_id`: Unique identifier
- `total_files`: Total number of files to import
- `completed_files`: List of successfully imported files
- `failed_files`: List of files that encountered errors
- `current_index`: Position in file list
- `paused`: Whether session is paused
- `completed`: Whether session finished

### Duplicate Detection Algorithm

1. Calculate SHA-256 hash of file content
2. Check `documents.json` for matching filename
3. If filename matches:
   - Compare content hash
   - If hash matches → **Exact duplicate**
   - If hash differs → **Updated file**
4. If filename doesn't match → **New file**

### File-by-File Processing

Unlike the original batch import, the new system processes files one at a time:
- **Advantage**: Can pause between files, not mid-file
- **Advantage**: More granular progress tracking
- **Advantage**: State saved after each file
- **Trade-off**: Slightly slower than batch (negligible for most use cases)

## Troubleshooting

### "Resume Import?" dialog appears but no incomplete import

The state file may be corrupted. Delete `memory/import_state.json` to reset.

### Duplicate not detected

The file may have been imported before the document registry system was added. Check `memory/documents.json` to verify.

### Import stuck on "Paused"

Click "Resume Import" or restart the app and choose "No" when asked to resume.

### Want to re-import everything

1. Use "Replace" action for each duplicate
2. OR delete `memory/documents.json` to reset document registry (WARNING: loses all import history)

## Testing

Run the test suite to verify everything works:

```bash
python test_import_pause_resume.py
```

This tests:
- State persistence and recovery
- Pause/resume functionality
- Duplicate detection (exact and updated)
- Crash recovery
- Progress tracking

## Implementation Files

- `import_state_manager.py` - State persistence and session management
- `duplicate_detector.py` - Duplicate detection and user dialogs
- `kay_ui.py` (ImportWindow class) - UI integration

## Notes

- The "Replace" action is partially implemented (marks for re-import but doesn't delete old memories yet)
- The "Import as Copy" action is partially implemented (imports but doesn't generate unique doc_id yet)
- Both of these will import successfully but may create duplicate memories
- Future enhancement: Add progress percentage and ETA to UI
- Future enhancement: Background imports (continue using app while importing)
