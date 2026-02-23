import os, hashlib

kay = r'D:\Wrappers\Kay'
reed = r'D:\Wrappers\Reed'

dirs = ['engines', 'integrations', 'services', 'memory_import', 'utils']
identical = 0
diverged = 0
diverged_files = []

for d in dirs:
    kd = os.path.join(kay, d)
    rd = os.path.join(reed, d)
    if not os.path.isdir(kd) or not os.path.isdir(rd):
        continue
    for f in sorted(os.listdir(kd)):
        if not f.endswith('.py') or f.startswith('__'):
            continue
        kf = os.path.join(kd, f)
        rf = os.path.join(rd, f)
        if not os.path.exists(rf):
            continue
        kh = hashlib.md5(open(kf, 'rb').read()).hexdigest()
        rh = hashlib.md5(open(rf, 'rb').read()).hexdigest()
        if kh == rh:
            identical += 1
        else:
            diverged += 1
            # Check size diff
            ks = os.path.getsize(kf)
            rs = os.path.getsize(rf)
            diff_pct = abs(ks - rs) / max(ks, rs) * 100
            diverged_files.append((d + '/' + f, ks, rs, diff_pct))

print('Identical files: %d' % identical)
print('Diverged files: %d' % diverged)
print()
if diverged_files:
    print('=== DIVERGED FILES (by size difference) ===')
    diverged_files.sort(key=lambda x: -x[3])
    for name, ks, rs, pct in diverged_files:
        marker = ''
        if pct > 20:
            marker = ' *** SIGNIFICANT'
        elif pct > 5:
            marker = ' * minor'
        print('  %s: Kay=%d Reed=%d (%.1f%% diff)%s' % (name, ks, rs, pct, marker))
