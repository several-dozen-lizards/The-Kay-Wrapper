"""
Fix AttributeError: 'AutonomousUIIntegration' object has no attribute 'set_curiosity_active'

PROBLEM:
The integration class calls self.set_curiosity_active() but that method doesn't exist
on AutonomousUIIntegration. It exists on the control_panel UI object.

FIX:
Change all calls from self.set_curiosity_active() to self.control_panel.set_curiosity_active()
"""

import sys

filepath = "D:\\Wrappers\\AlphaKayZero\\autonomous_ui_integration.py"

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading: {e}")
    sys.exit(1)

# Fix all calls to set_curiosity_active
count = content.count('self.set_curiosity_active(')
content = content.replace('self.set_curiosity_active(', 'self.control_panel.set_curiosity_active(')

print(f"[OK] Fixed {count} calls to set_curiosity_active")

try:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[SUCCESS] Fixed set_curiosity_active calls")
except Exception as e:
    print(f"Error writing: {e}")
    sys.exit(1)
