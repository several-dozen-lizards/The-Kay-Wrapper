content = open(r'D:\Wrappers\nexus\nexus_kay.py', encoding='utf-8').read()
lines = content.split('\n')

call_sites = [1416, 1621, 1642, 1664, 1829, 1955, 2555, 2777]

for site in call_sites:
    # Search backwards for meaningful context
    print(f"=== Line {site} ===")
    for j in range(max(0, site-30), site):
        l = lines[j-1].strip()
        if l.startswith('async def ') or l.startswith('def ') or '# ---' in l or 'ACTIVITY' in l.upper() or l.startswith('"""'):
            print(f"  L{j}: {l[:100]}")
    # Show the model line and max_tokens
    print(f"  >> {lines[site-1].strip()[:60]}")
    print(f"  >> {lines[site].strip()[:60]}")
    print()
