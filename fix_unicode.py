"""Fix Unicode arrows in all CC-modified files."""
import os

files = [
    r"D:\Wrappers\Kay\wrapper_bridge.py",
    r"D:\Wrappers\Kay\engines\memory_engine.py",
    r"D:\Wrappers\Kay\integrations\llm_integration.py",
    r"D:\Wrappers\Kay\engines\memory_layers.py",
    r"D:\Wrappers\Kay\engines\session_summary_generator.py",
    r"D:\Wrappers\Kay\engines\memory_curator.py",
    r"D:\Wrappers\resonant_core\memory_interoception.py",
]

total = 0
for path in files:
    if not os.path.exists(path):
        print(f"  SKIP (not found): {path}")
        continue
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    count = content.count("\u2192")
    if count > 0:
        content = content.replace("\u2192", "->")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  FIXED: {path} ({count} arrows)")
        total += count
    else:
        print(f"  OK: {path} (no arrows)")

print(f"\nTotal: {total} Unicode arrows replaced with '->'")
