"""
Fix the callback wiring that was skipped
"""

import sys

filepath = r"D:\Wrappers\Kay\autonomous_ui_integration.py"

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading: {e}")
    sys.exit(1)

old_callback = '''        self.control_panel.on_run_warmup = self._run_warmup
        self.control_panel.on_start_curiosity = self._start_curiosity'''

new_callback = '''        self.control_panel.on_run_warmup = self._run_warmup
        self.control_panel.on_start_curiosity = self._toggle_curiosity  # Toggle between start/end'''

if old_callback in content:
    content = content.replace(old_callback, new_callback)
    print("[OK] Fixed callback wiring")
else:
    print("[SKIP] Pattern not found (might already be updated)")

try:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[SUCCESS] Callback wiring complete!")
except Exception as e:
    print(f"Error writing: {e}")
    sys.exit(1)
