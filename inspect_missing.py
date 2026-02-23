import os
files = [
    (r'D:\Wrappers\Kay\engines\continuous_session.py', 'CONTINUOUS SESSION'),
    (r'D:\Wrappers\Kay\engines\chronicle_integration.py', 'CHRONICLE INTEGRATION'),
    (r'D:\Wrappers\Kay\engines\curation_interface.py', 'CURATION INTERFACE'),
    (r'D:\Wrappers\Kay\engines\real_time_flagging.py', 'REAL-TIME FLAGGING'),
    (r'D:\Wrappers\Kay\utils\encryption.py', 'ENCRYPTION'),
]
for fp, name in files:
    lines = open(fp, 'r', encoding='utf-8', errors='ignore').readlines()
    print('=== %s === (%d lines)' % (name, len(lines)))
    in_doc = False
    for i, line in enumerate(lines[:30]):
        if '"""' in line:
            if in_doc:
                print(line.rstrip())
                break
            in_doc = True
        if in_doc:
            print(line.rstrip())
    # Print class/function names
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('class ') or stripped.startswith('def '):
            if not stripped.startswith('def _'):
                print('  ' + stripped.split('(')[0].split(':')[0])
    print()
