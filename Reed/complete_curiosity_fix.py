"""
Complete curiosity mutual exclusion fix:
1. Add _end_curiosity() method
2. Make button toggle (wire up toggle logic)  
3. Update button in set_curiosity_active()
"""

import sys

filepath = r"D:\ChristinaStuff\AlphaKayZero\autonomous_ui_integration.py"

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading: {e}")
    sys.exit(1)

# CHANGE 1: Add _end_curiosity method after _start_curiosity
old_run_session = '''    def _run_session_thread(self):
        """Run autonomous session in background thread."""'''

new_end_curiosity_and_run_session = '''    def _end_curiosity(self):
        """Handle ending curiosity session."""
        from engines.curiosity_engine import end_curiosity_session, get_curiosity_status
        
        # Check if session is actually active
        status = get_curiosity_status()
        if not status["active"]:
            self.app.add_message("system", "⚠ No active curiosity session to end.")
            return
        
        # End the session in the engine
        result = end_curiosity_session(summary="Session ended by user")
        
        if result["success"]:
            self.app.add_message("system", f"🔍 {result['message']}")
            
            # Update UI state
            self.curiosity_active = False
            self.set_curiosity_active(False)
        else:
            self.app.add_message("system", f"⚠ Failed to end curiosity session: {result.get('error', 'Unknown error')}")

    def _run_session_thread(self):
        """Run autonomous session in background thread."""'''

if old_run_session in content:
    content = content.replace(old_run_session, new_end_curiosity_and_run_session)
    print("[OK] Added _end_curiosity() method")
else:
    print("[SKIP] Could not find _run_session_thread pattern")

# CHANGE 2: Wire up toggle in __init__
old_setup = '''        # Wire up integration layer callbacks
        self.control_panel.on_start_session = self._start_session
        self.control_panel.on_run_warmup = self._run_warmup
        self.control_panel.on_start_curiosity = self._start_curiosity'''

new_setup = '''        # Wire up integration layer callbacks
        self.control_panel.on_start_session = self._start_session
        self.control_panel.on_run_warmup = self._run_warmup
        self.control_panel.on_start_curiosity = self._toggle_curiosity  # Changed to toggle
        self.control_panel.on_end_curiosity = self._end_curiosity'''

if old_setup in content:
    content = content.replace(old_setup, new_setup)
    print("[OK] Wired up toggle callbacks")
else:
    print("[SKIP] Could not find callback setup pattern")

# CHANGE 3: Add _toggle_curiosity method before _start_curiosity
old_start_curiosity_def = '''    def _start_curiosity(self):
        """Handle curiosity session button."""'''

new_toggle_and_start = '''    def _toggle_curiosity(self):
        """Toggle curiosity session (start or end based on current state)."""
        if hasattr(self, 'curiosity_active') and self.curiosity_active:
            self._end_curiosity()
        else:
            self._start_curiosity()
    
    def _start_curiosity(self):
        """Handle curiosity session button."""'''

if old_start_curiosity_def in content:
    content = content.replace(old_start_curiosity_def, new_toggle_and_start)
    print("[OK] Added _toggle_curiosity() method")
else:
    print("[SKIP] Could not find _start_curiosity pattern")

# Write back
try:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\n[SUCCESS] Integration file updated!")
except Exception as e:
    print(f"Error writing: {e}")
    sys.exit(1)

# Now update the UI file to make button toggle
print("\n[PHASE 2] Updating autonomous_ui.py...")

ui_filepath = r"D:\ChristinaStuff\AlphaKayZero\autonomous_ui.py"

try:
    with open(ui_filepath, 'r', encoding='utf-8') as f:
        ui_content = f.read()
except Exception as e:
    print(f"Error reading UI: {e}")
    sys.exit(1)

# Update set_curiosity_active to change button text
old_set_curiosity = '''    def set_curiosity_active(self, active: bool):
        """Update UI when curiosity mode state changes."""
        if active:
            # Disable autonomous session button when curiosity is active
            self.start_session_btn.configure(
                text="⏸ Curiosity Mode Active",
                state="disabled",
                fg_color=self.palette.get("muted", "#9B7D54")
            )
            self.status_label.configure(
                text="Status: Curiosity session in progress",
                text_color=self.palette.get("accent_hi", "#6BB6B6")
            )
        else:
            # Re-enable if no autonomous session running
            if not self.session_active:'''

new_set_curiosity = '''    def set_curiosity_active(self, active: bool):
        """Update UI when curiosity mode state changes."""
        if active:
            # Update curiosity button to show "End"
            self.curiosity_btn.configure(
                text="⏹ End Curiosity Session",
                fg_color=self.palette.get("muted", "#9B7D54"),
                hover_color=self.palette.get("accent", "#4A9B9B")
            )
            # Disable autonomous session button when curiosity is active
            self.start_session_btn.configure(
                text="⏸ Curiosity Mode Active",
                state="disabled",
                fg_color=self.palette.get("muted", "#9B7D54")
            )
            self.status_label.configure(
                text="Status: Curiosity session in progress",
                text_color=self.palette.get("accent_hi", "#6BB6B6")
            )
        else:
            # Update curiosity button back to "Start"
            self.curiosity_btn.configure(
                text="🔍 Start Curiosity Session",
                fg_color=self.palette.get("button", "#4A2B5C"),
                hover_color=self.palette.get("accent", "#4A9B9B")
            )
            # Re-enable if no autonomous session running
            if not self.session_active:'''

if old_set_curiosity in ui_content:
    ui_content = ui_content.replace(old_set_curiosity, new_set_curiosity)
    print("[OK] Updated set_curiosity_active() to toggle button text")
else:
    print("[SKIP] Could not find set_curiosity_active pattern")

try:
    with open(ui_filepath, 'w', encoding='utf-8') as f:
        f.write(ui_content)
    print("[SUCCESS] UI file updated!")
    print("\n=== ALL CHANGES COMPLETE ===")
    print("Curiosity mode now has full mutual exclusion with autonomous sessions!")
    print("Button toggles between Start/End based on state.")
except Exception as e:
    print(f"Error writing UI: {e}")
    sys.exit(1)
