import sys

filepath = r"D:\ChristinaStuff\AlphaKayZero\K-0\autonomous_ui_integration.py"

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
except Exception as e:
    print(f"Error reading: {e}")
    sys.exit(1)

# Find the line with "def _update_iteration"
target_line = None
for i, line in enumerate(lines):
    if line.strip().startswith("def _update_iteration"):
        target_line = i
        break

if target_line is None:
    print("Could not find target line")
    sys.exit(1)

# Insert new method before _update_iteration
new_method = '''
    def set_curiosity_active(self, active: bool):
        """Update UI when curiosity mode state changes."""
        if self.control_panel:
            if active:
                # Disable autonomous session button when curiosity is active
                self.control_panel.start_session_btn.configure(
                    text="⏸ Curiosity Mode Active",
                    state="disabled",
                    fg_color=self.control_panel.palette.get("muted", "#9B7D54")
                )
                self.control_panel.status_label.configure(
                    text="Status: Curiosity session in progress",
                    text_color=self.control_panel.palette.get("accent_hi", "#6BB6B6")
                )
            else:
                # Re-enable if no autonomous session running
                if not self.session_active:
                    self.control_panel.start_session_btn.configure(
                        text="🧠 Begin Autonomous Session",
                        state="normal",
                        fg_color=self.control_panel.palette.get("accent", "#4A9B9B")
                    )
                    self.control_panel.status_label.configure(
                        text="Status: Idle",
                        text_color=self.control_panel.palette.get("muted", "#9B7D54")
                    )

'''

lines.insert(target_line, new_method)

try:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("[OK] File updated successfully!")
    print(f"Inserted new method at line {target_line}")
except Exception as e:
    print(f"Error writing: {e}")
    sys.exit(1)
