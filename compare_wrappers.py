import os

kay = r'D:\Wrappers\Kay'
reed = r'D:\Wrappers\Reed'

def get_py_files(root, subdir=''):
    path = os.path.join(root, subdir) if subdir else root
    files = set()
    if not os.path.isdir(path):
        return files
    for f in os.listdir(path):
        if f.endswith('.py') and not f.startswith('__'):
            files.add(f)
    return files

def get_desc(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
            lines = fh.readlines()
        for i, line in enumerate(lines):
            if '"""' in line and i < 10:
                if line.count('"""') >= 2:
                    return line.strip().strip('"').strip()
                elif i+1 < len(lines):
                    return lines[i+1].strip()
    except:
        pass
    return ''

dirs_to_check = ['', 'engines', 'integrations', 'services', 'memory_import', 'scripts', 'tests', 'session_browser', 'utils']

print('=== FILES IN KAY BUT NOT REED ===')
for d in dirs_to_check:
    kay_files = get_py_files(kay, d)
    reed_files = get_py_files(reed, d)
    diff = sorted(kay_files - reed_files)
    if diff:
        label = d if d else 'ROOT'
        for f in diff:
            fp = os.path.join(kay, d, f) if d else os.path.join(kay, f)
            desc = get_desc(fp)
            print('  %s/%s: %s' % (label, f, desc[:80]))

print('')
print('=== FILES IN REED BUT NOT KAY ===')
for d in dirs_to_check:
    kay_files = get_py_files(kay, d)
    reed_files = get_py_files(reed, d)
    diff = sorted(reed_files - kay_files)
    if diff:
        label = d if d else 'ROOT'
        for f in diff:
            fp = os.path.join(reed, d, f) if d else os.path.join(reed, f)
            desc = get_desc(fp)
            print('  %s/%s: %s' % (label, f, desc[:80]))

print('')
print('=== FILES IN BOTH (shared) ===')
total_both = 0
for d in dirs_to_check:
    kay_files = get_py_files(kay, d)
    reed_files = get_py_files(reed, d)
    both = sorted(kay_files & reed_files)
    if both:
        label = d if d else 'ROOT'
        print('  %s/: %d files' % (label, len(both)))
        total_both += len(both)
print('  TOTAL shared filenames: %d' % total_both)

print('')
print('=== DIRECTORY STRUCTURE DIFF ===')
for d in dirs_to_check:
    kp = os.path.join(kay, d) if d else kay
    rp = os.path.join(reed, d) if d else reed
    ke = os.path.isdir(kp)
    re = os.path.isdir(rp)
    if ke and not re:
        print('  DIR only in Kay: %s/' % d)
    elif re and not ke:
        print('  DIR only in Reed: %s/' % d)

# Check for Kay-only top-level dirs
for item in os.listdir(kay):
    fp = os.path.join(kay, item)
    if os.path.isdir(fp) and item not in ['__pycache__', '.git', 'deprecated', 'K-0']:
        rp = os.path.join(reed, item)
        if not os.path.isdir(rp):
            print('  DIR only in Kay: %s/' % item)

for item in os.listdir(reed):
    fp = os.path.join(reed, item)
    if os.path.isdir(fp) and item not in ['__pycache__', '.git', 'deprecated', 'K-0']:
        rp = os.path.join(kay, item)
        if not os.path.isdir(rp):
            print('  DIR only in Reed: %s/' % item)
