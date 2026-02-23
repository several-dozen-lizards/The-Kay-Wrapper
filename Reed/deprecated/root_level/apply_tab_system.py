"""
Automatically apply tab system changes to reed_ui.py

This script modifies reed_ui.py to use the new resizable tab system
instead of popup windows.

Usage: python apply_tab_system.py
"""

import os
import shutil
from datetime import datetime


def backup_file(filepath):
    """Create backup of file before modifying."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"[BACKUP] Created: {backup_path}")
    return backup_path


def apply_changes():
    """Apply all tab system changes to reed_ui.py."""
    filepath = "reed_ui.py"

    if not os.path.exists(filepath):
        print(f"[ERROR] {filepath} not found!")
        return False

    # Backup original
    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print("[APPLY] Applying changes...")

    # Track changes
    changes = []

    # Change 1: Add import (after line 36)
    for i, line in enumerate(lines):
        if 'from glyph_decoder import GlyphDecoder' in line:
            lines.insert(i + 2, '\n# === Tab System ===\n')
            lines.insert(i + 3, 'from tab_system import TabContainer\n')
            changes.append(f"Line {i+2}: Added tab_system import")
            break

    # Change 2: Update grid layout (around line 1492)
    for i, line in enumerate(lines):
        if '# Layout' in line and 'self.grid_columnconfigure(1, weight=1)' in lines[i+1]:
            # Replace layout section
            lines[i] = '        # Layout - 3 columns now: sidebar | tab_container | output\n'
            lines[i+1] = '        self.grid_columnconfigure(0, weight=0, minsize=260)  # Sidebar (fixed)\n'
            lines.insert(i+2, '        self.grid_columnconfigure(1, weight=0)                # Tab container (dynamic)\n')
            lines.insert(i+3, '        self.grid_columnconfigure(2, weight=1)                # Output area (flexible)\n')
            changes.append(f"Line {i}: Updated grid layout to 3 columns")
            break

    # Change 3: Add tab container (after sidebar creation, around line 1498)
    for i, line in enumerate(lines):
        if 'self.sidebar.grid(row=0, column=0, sticky="nswe", padx=10, pady=10)' in line:
            lines.insert(i + 2, '\n')
            lines.insert(i + 3, '        # Tab container (sits between sidebar and output)\n')
            lines.insert(i + 4, '        self.tab_container = TabContainer(self, on_layout_change=self._on_tabs_changed)\n')
            lines.insert(i + 5, '        self.tab_container.grid(row=0, column=1, sticky="nsew", padx=0, pady=10)\n')
            lines.insert(i + 6, '\n')
            lines.insert(i + 7, '        # Track tab state\n')
            lines.insert(i + 8, '        self.tab_widths = {}  # Store tab widths for session persistence\n')
            changes.append(f"Line {i+2}: Added tab container")
            break

    # Change 4: Update chat_log column (around line 1568)
    for i, line in enumerate(lines):
        if 'self.chat_log.grid(row=0, column=1, sticky="nsew"' in line:
            lines[i] = line.replace('column=1', 'column=2')
            changes.append(f"Line {i}: Moved chat_log to column 2")
            break

    # Change 5: Update input_frame columnspan (around line 1572)
    for i, line in enumerate(lines):
        if 'self.input_frame.grid(row=1, column=0, columnspan=2' in line:
            lines[i] = line.replace('columnspan=2', 'columnspan=3')
            changes.append(f"Line {i}: Updated input_frame columnspan to 3")
            break

    # Change 6: Update nav_button_frame columnspan (around line 1590)
    for i, line in enumerate(lines):
        if 'self.nav_button_frame.grid(row=2, column=0, columnspan=2' in line:
            lines[i] = line.replace('columnspan=2', 'columnspan=3')
            changes.append(f"Line {i}: Updated nav_button_frame columnspan to 3")
            break

    # Change 7: Add _on_tabs_changed method (after __init__, find on_quit method)
    for i, line in enumerate(lines):
        if 'def on_quit(self):' in line:
            # Insert before on_quit
            tab_callback = '''    def _on_tabs_changed(self):
        """Called when tabs are opened/closed/resized."""
        # Save current tab widths
        self.tab_widths = self.tab_container.get_tab_widths()
        # Force layout update
        self.update_idletasks()

'''
            lines.insert(i, tab_callback)
            changes.append(f"Line {i}: Added _on_tabs_changed callback")
            break

    # Save modified file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"\n[SUCCESS] Applied {len(changes)} changes:")
    for change in changes:
        print(f"  ✓ {change}")

    print(f"\n[INFO] You still need to manually add:")
    print("  1. Tab toggle methods (toggle_import_tab, toggle_documents_tab, etc.)")
    print("  2. Update menu button commands to use toggle methods")
    print("  3. Add settings tab button to sidebar")
    print("\nSee TAB_SYSTEM_INTEGRATION.md for complete instructions.")

    return True


if __name__ == "__main__":
    print("="*70)
    print("TAB SYSTEM INTEGRATION - Automatic Patch")
    print("="*70)
    print()

    success = apply_changes()

    if success:
        print("\n[DONE] Basic structure changes applied successfully!")
        print("Next steps:")
        print("  1. Review TAB_SYSTEM_INTEGRATION.md for remaining manual changes")
        print("  2. Test with: python reed_ui.py")
        print("  3. Restore from backup if needed")
    else:
        print("\n[FAILED] Changes could not be applied")

    print("="*70)
