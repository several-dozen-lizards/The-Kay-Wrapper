#!/usr/bin/env python3
"""
Fix the visual header in Reed UI
"""

def fix_header():
    print("Fixing Reed UI header...")
    
    with open('reed_ui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the header
    content = content.replace(
        'text="⟨ KAY ZERO INTERFACE ⟩"',
        'text="⟨ REED — SERPENT INTERFACE ⟩"'
    )
    
    with open('reed_ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Updated header: ⟨ REED — SERPENT INTERFACE ⟩")

if __name__ == "__main__":
    fix_header()
    print()
    print("Header updated! Relaunch with: python reed_ui.py")
