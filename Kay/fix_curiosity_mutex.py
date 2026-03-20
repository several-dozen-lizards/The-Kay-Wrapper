"""
Script to add mutual exclusion between curiosity mode and autonomous sessions.

Changes:
1. Check curiosity_active in _start_session() and block if active
2. Call set_curiosity_active() when curiosity starts/ends
3. Add code to set curiosity_active = False when curiosity ends
"""

import sys

filepath = r"D:\Wrappers\Kay\autonomous_ui_integration.py"

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading: {e}")
    sys.exit(1)

# CHANGE 1: Add curiosity check in _start_session()
old_start_session = '''    def _start_session(self):
        """Start an autonomous processing session."""
        if self.session_active:
            self.app.add_message("system", "Autonomous session already in progress.")
            return

        self.app.add_message("system", "🧠 Starting autonomous processing session...")'''

new_start_session = '''    def _start_session(self):
        """Start an autonomous processing session."""
        if self.session_active:
            self.app.add_message("system", "Autonomous session already in progress.")
            return
        
        # Check if curiosity mode is active
        if hasattr(self, 'curiosity_active') and self.curiosity_active:
            self.app.add_message("system", "⏸ Cannot start autonomous session - curiosity mode is active.")
            return

        self.app.add_message("system", "🧠 Starting autonomous processing session...")'''

if old_start_session in content:
    content = content.replace(old_start_session, new_start_session)
    print("[OK] Added curiosity check to _start_session()")
else:
    print("[SKIP] Could not find _start_session pattern")

# CHANGE 2: Call set_curiosity_active(True) when curiosity starts
old_curiosity_start = '''            # Store session active state
            self.curiosity_active = True'''

new_curiosity_start = '''            # Store session active state
            self.curiosity_active = True
            # Update UI to disable autonomous button
            self.set_curiosity_active(True)'''

if old_curiosity_start in content:
    content = content.replace(old_curiosity_start, new_curiosity_start)
    print("[OK] Added set_curiosity_active(True) call")
else:
    print("[SKIP] Could not find curiosity_start pattern")

# CHANGE 3: Initialize curiosity_active in __init__
old_init = '''        # State
        self.session_active = False'''

new_init = '''        # State
        self.session_active = False
        self.curiosity_active = False  # Track curiosity mode state'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("[OK] Added curiosity_active initialization")
else:
    print("[SKIP] Could not find init pattern")

# Write back
try:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\n[SUCCESS] File updated!")
    print("\nNext steps:")
    print("1. Add code to set curiosity_active=False when curiosity ends")
    print("2. Call set_curiosity_active(False) at that point")
except Exception as e:
    print(f"Error writing: {e}")
    sys.exit(1)
