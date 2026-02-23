#!/usr/bin/env python3
"""
FINAL comprehensive fix for all Kay->Reed references
"""

def fix_file(filepath, replacements):
    """Apply replacements to a file"""
    print(f"Fixing {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old, new in replacements:
        if old in content:
            count = content.count(old)
            content = content.replace(old, new)
            print(f"  ✓ Replaced '{old}' -> '{new}' ({count}x)")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Saved {filepath}\n")

def main():
    print("=" * 60)
    print("FINAL KAY->REED FIX - ALL REFERENCES")
    print("=" * 60)
    print()
    
    # Fix reed_ui.py
    reed_ui_fixes = [
        # Function calls
        ('get_kay_document_tools', 'get_reed_document_tools'),
        ('get_kay_scratchpad_tools', 'get_reed_scratchpad_tools'),
        # Class instantiation
        ('app = KayApp()', 'app = ReedApp()'),
        # Just in case any imports slipped through
        ('from kay_document_reader', 'from reed_document_reader'),
        ('from kay_scratchpad_tools', 'from reed_scratchpad_tools'),
        ('import kay_document_reader', 'import reed_document_reader'),
        ('import kay_scratchpad_tools', 'import reed_scratchpad_tools'),
    ]
    fix_file('reed_ui.py', reed_ui_fixes)
    
    # Fix reed_cli.py
    reed_cli_fixes = [
        ('get_kay_document_tools', 'get_reed_document_tools'),
        ('get_kay_scratchpad_tools', 'get_reed_scratchpad_tools'),
        ('from kay_document_reader', 'from reed_document_reader'),
        ('from kay_scratchpad_tools', 'from reed_scratchpad_tools'),
        ('KAY_SYSTEM_PROMPT', 'REED_SYSTEM_PROMPT'),
        ('class KayCLI:', 'class ReedCLI:'),
        ('KayCLI()', 'ReedCLI()'),
    ]
    fix_file('reed_cli.py', reed_cli_fixes)
    
    print("=" * 60)
    print("✅ ALL FIXES APPLIED")
    print("=" * 60)
    print()
    print("Now try: python reed_ui.py")

if __name__ == "__main__":
    main()
