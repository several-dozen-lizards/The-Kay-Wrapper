# Bulk Delete Feature - Session Browser

## Overview

Added checkbox-based bulk deletion functionality to the Session Browser UI, allowing users to select and delete multiple sessions at once instead of deleting them one by one.

## Features Added

### 1. **Checkbox Selection**
- Each session card now has a checkbox for selection
- Current session cannot be selected (checkbox not shown for active session)
- Individual checkboxes update the selected count in real-time

### 2. **Bulk Actions Toolbar**
Located at the top of the session list, includes:
- **Select All checkbox**: Toggle all session checkboxes on/off
- **Delete Selected button**: Delete all checked sessions (disabled when no selections)
- **Selected count label**: Shows "X selected" (green when > 0, gray when 0)

### 3. **Smart Deletion**
- Prevents deletion of current/active session
- Confirmation dialog shows exact count before deletion
- Batch processing with success/failure tracking
- Automatic cleanup of stale checkbox references
- Refreshes session list after deletion

## UI Changes

### Bulk Actions Toolbar (session_browser_ui.py:142-181)
```python
# Select All checkbox
select_all_cb = tk.Checkbutton(
    bulk_frame,
    text="Select All",
    variable=self.select_all_var,
    command=self._toggle_select_all,
    ...
)

# Delete Selected button (initially disabled)
self.delete_selected_btn = tk.Button(
    bulk_frame,
    text="🗑 Delete Selected",
    command=self._delete_selected,
    bg="#5c3030",  # Red background
    state=tk.DISABLED,
    ...
)

# Selected count label
self.selected_count_label = tk.Label(
    bulk_frame,
    text="0 selected",
    fg="#888888",  # Gray when 0, green when > 0
    ...
)
```

### Individual Session Checkboxes (session_browser_ui.py:342-355)
```python
# Only show checkbox for non-current sessions
if not is_current:
    if session_id not in self.session_checkboxes:
        self.session_checkboxes[session_id] = tk.BooleanVar(value=False)

    checkbox = tk.Checkbutton(
        title_row,
        variable=self.session_checkboxes[session_id],
        command=self._update_selected_count,
        ...
    )
    checkbox.pack(side=tk.LEFT, padx=(0, 5))
```

## New Methods

### `_toggle_select_all()` (session_browser_ui.py:759-769)
- Checks/unchecks all visible session checkboxes
- Skips current session (can't delete active session)
- Updates selected count after toggling

### `_delete_selected()` (session_browser_ui.py:771-823)
- Collects all selected session IDs
- Shows warning if no selections
- Confirmation dialog with exact count
- Batch deletes all selected sessions
- Tracks successful vs failed deletions
- Shows result summary dialog
- Refreshes session list and resets "Select All"

### `_update_selected_count()` (session_browser_ui.py:825-842)
- Counts checked sessions
- Updates label text ("X selected")
- Changes label color (green if > 0, gray if 0)
- Enables/disables delete button based on selection count

## State Management

### Checkbox Tracking
```python
# In __init__:
self.session_checkboxes = {}  # {session_id: BooleanVar}
self.select_all_var = tk.BooleanVar(value=False)
```

### Cleanup on Refresh
When sessions are refreshed or searched:
1. Identifies stale session IDs (deleted sessions still in checkbox dict)
2. Removes stale checkbox references
3. Preserves checkbox state for existing sessions
4. Updates selected count

## User Workflow

### Delete Multiple Sessions:
1. Check individual sessions OR click "Select All"
2. Review selected count label ("X selected")
3. Click "🗑 Delete Selected" button
4. Confirm deletion in dialog
5. View success/failure summary
6. Session list refreshes automatically

### Visual Feedback:
- **Label color**: Gray (0 selected) → Green (1+ selected)
- **Delete button**: Disabled (0 selected) → Enabled (1+ selected)
- **Confirmation dialog**: Shows exact count before deletion
- **Result dialog**: Reports successful vs failed deletions

## Safety Features

1. **Current Session Protection**: Active session cannot be selected or deleted
2. **Confirmation Dialog**: Warns user before deletion with exact count
3. **Batch Error Handling**: Continues deleting even if some fail, reports final count
4. **Stale Reference Cleanup**: Automatically removes checkbox tracking for deleted sessions
5. **Cannot Undo Warning**: Clearly states "This cannot be undone"

## Files Modified

- **session_browser/session_browser_ui.py**:
  - Added checkbox tracking variables (lines 50-52)
  - Added bulk actions toolbar (lines 142-181)
  - Added checkbox to each session widget (lines 342-355)
  - Added stale checkbox cleanup in _render_sessions() (lines 254-275)
  - Added _toggle_select_all() method (lines 759-769)
  - Added _delete_selected() method (lines 771-823)
  - Added _update_selected_count() method (lines 825-842)

## Integration

This feature is fully integrated into the Session Browser UI. No additional setup required.

When using Session Browser via `kay_ui.py`:
- Bulk delete works seamlessly
- Current session is always protected
- Deleted sessions removed from both UI and disk

When using `demo_browser.py`:
- Bulk delete works the same way
- All features functional in demo mode

## Testing

To test the bulk delete feature:

1. **Start Session Browser**:
   ```bash
   python session_browser/demo_browser.py
   ```

2. **Test Individual Selection**:
   - Check 2-3 sessions
   - Verify count updates ("3 selected")
   - Verify delete button enables
   - Verify label turns green

3. **Test Select All**:
   - Click "Select All" checkbox
   - Verify all sessions (except current) get checked
   - Verify count shows total
   - Uncheck "Select All" to clear all

4. **Test Deletion**:
   - Select a few sessions
   - Click "🗑 Delete Selected"
   - Verify confirmation dialog shows correct count
   - Confirm deletion
   - Verify success message
   - Verify sessions removed from list

5. **Test Edge Cases**:
   - Try deleting with no selection (should warn)
   - Try selecting current session (checkbox shouldn't appear)
   - Refresh list while sessions selected (state should persist)
   - Search while sessions selected (state should persist)

## Future Enhancements

Potential improvements:
- Keyboard shortcuts (Ctrl+A for select all, Delete key for delete)
- Shift+click for range selection
- Filter selected sessions (show only selected)
- Export selected sessions
- Bulk tagging/note-adding for selected sessions
- Undo last bulk deletion (restore from trash)
