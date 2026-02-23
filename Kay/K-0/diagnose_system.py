"""
Kay Zero System Diagnostic Script
Verifies all critical files, paths, and system components
"""

import os
import json
from pathlib import Path


def safe_print(text: str):
    """Print text with Unicode fallback for Windows console"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Remove Unicode characters for Windows console
        print(text.encode('ascii', 'ignore').decode('ascii'))

print("=" * 70)
print("KAY ZERO SYSTEM DIAGNOSTIC")
print("=" * 70)

# Test 1: Current Working Directory
print("\n[TEST 1] Current Working Directory")
cwd = os.getcwd()
expected_cwd = "F:\\AlphaKayZero"
print(f"  Current: {cwd}")
print(f"  Expected: {expected_cwd}")
if cwd == expected_cwd:
    safe_print("  [OK] PASS")
else:
    print(f"  [FAIL] Wrong directory! cd to {expected_cwd}")

# Test 2: Critical Directories
print("\n[TEST 2] Critical Directories")
dirs_to_check = ["memory", "data", "engines", "memory_import", "integrations", "utils"]
all_dirs_exist = True
for dir_name in dirs_to_check:
    exists = os.path.exists(dir_name) and os.path.isdir(dir_name)
    status = "[OK]" if exists else "[FAIL]"
    print(f"  {status} {dir_name}/")
    if not exists:
        all_dirs_exist = False

if all_dirs_exist:
    print("  [OK] PASS - All directories exist")
else:
    print("  [FAIL] FAIL - Missing directories")

# Test 3: ULTRAMAP File
print("\n[TEST 3] ULTRAMAP File")
ultramap_path = "data/Emotion_Mapping_Kay_ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv"
if os.path.exists(ultramap_path):
    size = os.path.getsize(ultramap_path)
    print(f"  [OK] PASS - Found at {ultramap_path} ({size} bytes)")
else:
    print(f"  [FAIL] FAIL - Missing: {ultramap_path}")
    print("    This file is CRITICAL for emotional system!")

# Test 4: Memory Files
print("\n[TEST 4] Memory System Files")
memory_files = {
    "memories.json": "Main memory store",
    "entity_graph.json": "Entity resolution",
    "memory_layers.json": "Multi-layer memory",
    "forest.json": "Memory forest",
    "documents.json": "Document store",
    "motifs.json": "Motif tracking",
    "preferences.json": "Preference tracking"
}

all_memory_files_exist = True
for filename, description in memory_files.items():
    path = f"memory/{filename}"
    exists = os.path.exists(path)
    status = "[OK]" if exists else "[WARN]"

    if exists:
        # Try to load and get count
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if filename == "memories.json":
                count = len(data) if isinstance(data, list) else "N/A"
            elif filename == "entity_graph.json":
                count = len(data.get("entities", {})) if isinstance(data, dict) else "N/A"
            elif filename == "memory_layers.json":
                working = len(data.get("working", [])) if isinstance(data, dict) else 0
                episodic = len(data.get("episodic", [])) if isinstance(data, dict) else 0
                semantic = len(data.get("semantic", [])) if isinstance(data, dict) else 0
                count = f"{working}W+{episodic}E+{semantic}S"
            elif filename == "forest.json":
                count = len(data.get("trees", {})) if isinstance(data, dict) else "N/A"
            elif filename == "documents.json":
                count = len(data) if isinstance(data, dict) else "N/A"
            else:
                count = len(data) if isinstance(data, (list, dict)) else "N/A"

            print(f"  {status} {filename} - {description} ({count} entries)")
        except Exception as e:
            print(f"  [WARN] {filename} - {description} (parse error: {e})")
    else:
        print(f"  {status} {filename} - {description} (will be created on first use)")
        # Only mark as fail if it's a critical file that should exist
        if filename in ["memories.json", "entity_graph.json", "memory_layers.json"]:
            all_memory_files_exist = False

if all_memory_files_exist:
    print("  [OK] PASS - Critical memory files exist")
else:
    print("  [WARN] WARNING - Some memory files missing (may be first run)")

# Test 5: Path Utilities
print("\n[TEST 5] Path Utilities")
try:
    from utils.paths import verify_critical_paths, PROJECT_ROOT, MEMORY_DIR, ULTRAMAP_CSV
    print(f"  [OK] Path utilities imported")
    print(f"  PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"  MEMORY_DIR: {MEMORY_DIR}")
    print(f"  ULTRAMAP: {ULTRAMAP_CSV}")

    if verify_critical_paths():
        print("  [OK] PASS - Path verification successful")
    else:
        print("  [FAIL] FAIL - Path verification failed")
except Exception as e:
    print(f"  [FAIL] FAIL - Error importing path utilities: {e}")

# Test 6: Main Engines Import
print("\n[TEST 6] Core Engine Imports")
engines_to_test = [
    ("protocol_engine", "ProtocolEngine"),
    ("engines.memory_engine", "MemoryEngine"),
    ("engines.emotion_engine", "EmotionEngine"),
    ("engines.memory_forest", "MemoryForest"),
    ("memory_import.document_store", "DocumentStore"),
]

all_imports_ok = True
for module_name, class_name in engines_to_test:
    try:
        module = __import__(module_name, fromlist=[class_name])
        cls = getattr(module, class_name)
        print(f"  [OK] {module_name}.{class_name}")
    except Exception as e:
        print(f"  [FAIL] {module_name}.{class_name} - {e}")
        all_imports_ok = False

if all_imports_ok:
    print("  [OK] PASS - All core imports successful")
else:
    print("  [FAIL] FAIL - Some imports failed")

# Test 7: Document Store Initialization
print("\n[TEST 7] Document Store Initialization")
try:
    from memory_import.document_store import DocumentStore
    store = DocumentStore()
    doc_count = len(store.documents)
    print(f"  [OK] DocumentStore initialized")
    print(f"  Documents in store: {doc_count}")
    print("  [OK] PASS")
except Exception as e:
    print(f"  [FAIL] FAIL - Error: {e}")
    import traceback
    traceback.print_exc()

# Test 8: Memory Forest Initialization
print("\n[TEST 8] Memory Forest Initialization")
try:
    from engines.memory_forest import MemoryForest
    forest = MemoryForest.load_from_file("memory/forest.json")
    tree_count = len(forest.trees)
    print(f"  [OK] MemoryForest loaded")
    print(f"  Trees in forest: {tree_count}")
    print("  [OK] PASS")
except Exception as e:
    print(f"  [FAIL] FAIL - Error: {e}")
    import traceback
    traceback.print_exc()

# Final Summary
print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)

print("\nIf all tests passed:")
print("  [OK] System is healthy and ready to use")
print("\nIf tests failed:")
print("  1. Ensure you're in F:\\AlphaKayZero directory")
print("  2. Check that all critical files exist")
print("  3. Run: python main.py")
