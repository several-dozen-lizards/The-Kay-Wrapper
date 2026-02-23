"""
Bulk Kay -> Reed reference cleanup for D:\Wrappers\Reed
Only touches docstrings, comments, print statements, and UI strings.
Does NOT touch: verify_conversion.py, transform_to_reed.py, or any .json/.md files
Does NOT touch: references to Kay Zero as an entity (relationship data, entity graphs)
"""
import os
import re

REED_DIR = r"D:\Wrappers\Reed"
SKIP_FILES = {"verify_conversion.py", "transform_to_reed.py"}

# Replacements: (pattern, replacement, description)
# Order matters - more specific patterns first
REPLACEMENTS = [
    # Docstring/comment headers
    (r'for Kay Zero\b', 'for Reed', 'module docstring'),
    (r'Kay Zero\'s', "Reed's", 'possessive'),
    # UI references  
    (r'\[KAY UI\]', '[REED UI]', 'log prefix'),
    (r'kay_ui\.py', 'reed_ui.py', 'filename ref'),
    (r'"Kay"', '"Reed"', 'display name'),
    # Variable names in comments/docstrings
    (r'kay_response', 'reed_response', 'variable name'),
    (r'kay_description', 'reed_description', 'variable name'),
    (r'get_kay_response', 'get_reed_response', 'method name'),
    # Comment-only Kay references (careful - only in comments/docstrings)
    (r'(#.*)Kay Zero', r'\1Reed', 'comment Kay Zero'),
    (r'(#.*)Kay\'s', r"\1Reed's", 'comment possessive'),
]

# These are for lines that are ONLY in docstrings/comments
# We use a simpler approach: replace "Kay" with "Reed" only in docstring lines
DOCSTRING_REPLACEMENTS = [
    ('Kay Zero', 'Reed'),
    ("Kay's", "Reed's"),
    ('for Kay', 'for Reed'),
    ('Kay UI', 'Reed UI'),
    ('Kay generates', 'Reed generates'),
    ('Kay reported', 'Reed reported'),
]

def is_docstring_or_comment(line):
    stripped = line.strip()
    return (stripped.startswith('#') or 
            stripped.startswith('"""') or 
            stripped.startswith("'''") or
            stripped.startswith('Kay') and not '=' in stripped and not '(' in stripped)

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return 0
    
    original = content
    changes = 0
    
    # Simple replacements that are safe everywhere
    safe_replacements = [
        ('for Kay Zero', 'for Reed'),
        ("Kay Zero's", "Reed's"),
        ('[KAY UI]', '[REED UI]'),
        ('kay_ui.py', 'reed_ui.py'),
        ('kay_response', 'reed_response'),
        ('kay_description', 'reed_description'),
        ('get_kay_response', 'get_reed_response'),
    ]
    
    for old, new in safe_replacements:
        if old in content:
            content = content.replace(old, new)
    
    # Line-by-line for context-sensitive replacements
    lines = content.split('\n')
    in_docstring = False
    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Track docstring state
        if '"""' in stripped or "'''" in stripped:
            count = stripped.count('"""') + stripped.count("'''")
            if count == 1:
                in_docstring = not in_docstring
            # If count == 2, it's a single-line docstring, stay same state
        
        if in_docstring or stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            for old, new in DOCSTRING_REPLACEMENTS:
                line = line.replace(old, new)
        
        new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    if content != original:
        changes = sum(1 for a, b in zip(original.split('\n'), content.split('\n')) if a != b)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return changes

total_changes = 0
files_changed = 0

for root, dirs, files in os.walk(REED_DIR):
    for fname in files:
        if not fname.endswith('.py'):
            continue
        if fname in SKIP_FILES:
            continue
        
        filepath = os.path.join(root, fname)
        changes = process_file(filepath)
        if changes > 0:
            print(f"  {os.path.relpath(filepath, REED_DIR)}: {changes} lines changed")
            total_changes += changes
            files_changed += 1

print(f"\n{'='*50}")
print(f"Total: {total_changes} lines changed across {files_changed} files")
