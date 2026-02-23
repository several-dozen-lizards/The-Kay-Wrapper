import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

root = r'D:\Wrappers\Reed'
fixes = 0

targets = [
    ('reed_cli.py', 367, 'KAY ZERO CLI', 'REED CLI'),
    ('reed_cli.py', 628, 'Kay Zero CLI', 'Reed CLI'),
    ('media_orchestrator.py', 1025, 'full Kay Zero environment', 'full Reed environment'),
    ('engines/user_profiles.py', 321, 'Kay Zero User Profile System', 'Reed User Profile System'),
    ('memory_import/memory_extractor.py', 18, 'run from Kay Zero root directory', 'run from Reed root directory'),
    ('session_browser/INTEGRATION_EXAMPLE.py', 24, 'Kay Zero', 'Reed'),
    ('scripts/benchmark_lazy_loading.py', 231, 'KAY ZERO LAZY LOADING', 'REED LAZY LOADING'),
    ('scripts/cleanup_memory.py', 175, 'KAY ZERO MEMORY CLEANUP', 'REED MEMORY CLEANUP'),
    ('scripts/diagnose_system.py', 20, 'KAY ZERO SYSTEM DIAGNOSTIC', 'REED SYSTEM DIAGNOSTIC'),
    ('scripts/import_memories.py', 48, 'KAY ZERO MEMORY IMPORT', 'REED MEMORY IMPORT'),
    ('scripts/import_memories.py', 52, "Kay's memory system", "Reed's memory system"),
    ('scripts/preview_wipe.py', 15, 'KAY ZERO MEMORY WIPE PREVIEW', 'REED MEMORY WIPE PREVIEW'),
    ('scripts/wipe_memory.py', 360, 'KAY ZERO MEMORY WIPE', 'REED MEMORY WIPE'),
    ('tests/test_consolidation_system.py', 280, 'KAY ZERO CONSOLIDATION', 'REED CONSOLIDATION'),
    ('tests/test_forest_integration.py', 177, 'integrated with Kay Zero', 'integrated with Reed'),
    ('tests/test_terminal_dashboard.py', 44, 'Kay Zero wrapper initialized', 'Reed wrapper initialized'),
    ('tests/test_system_prompt.py', 27, '"Kay Zero"', '"Reed"'),
]

for rel_path, line_num, old, new in targets:
    fp = os.path.join(root, rel_path.replace('/', os.sep))
    if not os.path.exists(fp):
        print(f'  SKIP (missing): {rel_path}')
        continue
    try:
        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        idx = line_num - 1
        if idx < len(lines) and old in lines[idx]:
            lines[idx] = lines[idx].replace(old, new)
            with open(fp, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            fixes += 1
            print(f'  FIXED: {rel_path}:{line_num} [{old[:50]} -> {new[:50]}]')
        else:
            found = False
            for offset in range(-5, 6):
                check = idx + offset
                if 0 <= check < len(lines) and old in lines[check]:
                    lines[check] = lines[check].replace(old, new)
                    with open(fp, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    fixes += 1
                    print(f'  FIXED: {rel_path}:{check+1} (shifted) [{old[:50]} -> {new[:50]}]')
                    found = True
                    break
            if not found:
                print(f'  MISS: {rel_path}:{line_num} - "{old[:60]}" not found nearby')
    except Exception as e:
        print(f'  ERROR: {rel_path} - {e}')

print(f'\nTotal fixes: {fixes}')
