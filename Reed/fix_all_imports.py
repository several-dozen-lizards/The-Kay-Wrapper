#!/usr/bin/env python3
"""
COMPLETE Kay->Reed conversion fix
Fixes ALL remaining Kay references in all files
"""

def fix_reed_ui():
    """Fix reed_ui.py"""
    print("Fixing reed_ui.py...")
    
    with open('reed_ui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix imports
    content = content.replace('from kay_document_reader import', 'from reed_document_reader import')
    content = content.replace('from kay_scratchpad_tools import', 'from reed_scratchpad_tools import')
    content = content.replace('get_kay_document_tools', 'get_reed_document_tools')
    content = content.replace('get_kay_scratchpad_tools', 'get_reed_scratchpad_tools')
    
    with open('reed_ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Fixed reed_ui.py")

def fix_reed_cli():
    """Fix reed_cli.py"""
    print("Fixing reed_cli.py...")
    
    with open('reed_cli.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    replacements = [
        ('Kay Zero CLI Mode', 'Reed CLI Mode'),
        ('interaction with Kay using', 'interaction with Reed using'),
        ('python kay_cli.py', 'python reed_cli.py'),
        ('same as reed_ui.py', 'same as reed_ui.py'),
        ("Kay's system prompt", "Reed's system prompt"),
        ('KAY_SYSTEM_PROMPT', 'REED_SYSTEM_PROMPT'),
        ('class KayCLI:', 'class ReedCLI:'),
        ('Kay CLI', 'Reed CLI'),
        ('"you": user_input, "kay":', '"you": user_input, "reed":'),
        ('from kay_document_reader import', 'from reed_document_reader import'),
        ('from kay_scratchpad_tools import', 'from reed_scratchpad_tools import'),
        ('get_kay_document_tools', 'get_reed_document_tools'),
        ('get_kay_scratchpad_tools', 'get_reed_scratchpad_tools'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    with open('reed_cli.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Fixed reed_cli.py")

def main():
    print("=" * 60)
    print("COMPLETE KAY->REED FIX")
    print("=" * 60)
    print()
    
    try:
        fix_reed_ui()
        fix_reed_cli()
        
        print()
        print("=" * 60)
        print("✅ ALL FILES FIXED")
        print("=" * 60)
        print()
        print("Now run: python reed_ui.py")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
