"""
Fix curiosity state persistence bug.

PROBLEM:
Curiosity state persists from previous sessions. If Kay shuts down with an active
curiosity session, the state file stays "active": true. When Kay restarts, the 
button thinks a session is already running and refuses to start a new one.

FIX:
Reset curiosity state to inactive when Kay starts up (in kay_ui.py __init__).
"""

import sys

filepath = "D:\\ChristinaStuff\\AlphaKayZero\\kay_ui.py"

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"Error reading: {e}")
    sys.exit(1)

# Find where to insert the reset code - right after TIME and EMOTION ENGINE init
old_init_section = '''        # Emotion engine
        self.emotional_patterns = EmotionEngine()
        print("[EMOTION ENGINE] Initialized as ULTRAMAP rule provider (no calculation)")'''

new_init_section = '''        # Emotion engine
        self.emotional_patterns = EmotionEngine()
        print("[EMOTION ENGINE] Initialized as ULTRAMAP rule provider (no calculation)")
        
        # Reset curiosity state on startup (clear any stuck "active" state from previous session)
        try:
            from engines.curiosity_engine import reset_curiosity_state
            reset_curiosity_state()
            print("[CURIOSITY] State reset on startup")
        except Exception as e:
            print(f"[CURIOSITY] Could not reset state: {e}")'''

if old_init_section in content:
    content = content.replace(old_init_section, new_init_section)
    print("[OK] Added curiosity state reset to startup")
else:
    print("[ERROR] Could not find insertion point")
    sys.exit(1)

try:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\n[SUCCESS] Kay will now reset curiosity state on startup")
    print("\nNext: Add reset_curiosity_state() function to curiosity_engine.py")
except Exception as e:
    print(f"Error writing: {e}")
    sys.exit(1)
