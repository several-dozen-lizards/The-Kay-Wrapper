"""
Copy missing files from Kay to Reed wrapper, fixing identity references.
"""
import os
import shutil

KAY = r'D:\Wrappers\Kay'
REED = r'D:\Wrappers\Reed'

# Identity replacements
REPLACEMENTS = [
    ('Kay Zero', 'Reed'),
    ('kay zero', 'reed'),
    ('KAY ZERO', 'REED'),
    ('Kay\'s', 'Reed\'s'),
    ('kay\'s', 'reed\'s'),
    ('KayZero', 'Reed'),
    ('for Kay', 'for Reed'),
    ('Kay-0', 'Reed'),
]

def copy_with_fixes(src, dst):
    """Copy file, fixing Kay references."""
    with open(src, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    changes = 0
    for old, new in REPLACEMENTS:
        count = content.count(old)
        if count:
            content = content.replace(old, new)
            changes += count
    
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  Copied: {os.path.basename(src)} ({changes} identity fixes)")

# 1. Backend files
print("=== BACKEND FILES ===")
for fn in ['ai4chat_backend.py', 'openrouter_backend.py', 'together_backend.py']:
    src = os.path.join(KAY, 'integrations', fn)
    dst = os.path.join(REED, 'integrations', fn)
    if os.path.exists(src) and not os.path.exists(dst):
        copy_with_fixes(src, dst)
    elif os.path.exists(dst):
        print(f"  SKIP (exists): {fn}")
    else:
        print(f"  SKIP (missing src): {fn}")

# 2. Services directory
print("\n=== SERVICES ===")
services_dir = os.path.join(REED, 'services')
os.makedirs(services_dir, exist_ok=True)

# __init__.py
init_src = os.path.join(KAY, 'services', '__init__.py')
init_dst = os.path.join(REED, 'services', '__init__.py')
if os.path.exists(init_src):
    copy_with_fixes(init_src, init_dst)
else:
    with open(init_dst, 'w') as f:
        f.write('# Reed services\n')
    print("  Created: __init__.py (empty)")

# github_service.py
gh_src = os.path.join(KAY, 'services', 'github_service.py')
gh_dst = os.path.join(REED, 'services', 'github_service.py')
copy_with_fixes(gh_src, gh_dst)

print("\nDone!")
