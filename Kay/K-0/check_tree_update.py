"""Check if tree was actually updated with access counts"""
import json
import os
from pathlib import Path

# Find all tree files
tree_dir = Path("data/trees")
tree_files = list(tree_dir.glob("tree_doc_*.json"))

if not tree_files:
    print("No tree files found!")
    exit(1)

# Sort by modification time (most recent first)
tree_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

print(f"Found {len(tree_files)} tree files\n")

# Check the 3 most recent
print("Most recent trees:")
for i, tree_file in enumerate(tree_files[:3]):
    with open(tree_file, 'r', encoding='utf-8') as f:
        tree_data = json.load(f)

    doc_id = tree_data.get('doc_id')
    title = tree_data.get('title')
    tree_access = tree_data.get('access_count', 0)
    last_accessed = tree_data.get('last_accessed')

    print(f"\n{i+1}. {title} ({doc_id})")
    print(f"   Tree access_count: {tree_access}")
    print(f"   Last accessed: {last_accessed}")

    for branch in tree_data.get('branches', []):
        branch_title = branch.get('title')
        branch_access = branch.get('access_count', 0)
        branch_last = branch.get('last_accessed')
        print(f"   Branch '{branch_title}': access_count={branch_access}, last_accessed={branch_last}")

print("\n" + "="*60)
print("DIAGNOSIS:")
print("="*60)

# Check if any tree has access_count > 0
any_accessed = any(
    tree_data.get('access_count', 0) > 0
    for tree_file in tree_files
    for tree_data in [json.load(open(tree_file, 'r', encoding='utf-8'))]
)

if any_accessed:
    print("[SUCCESS] At least one tree has been accessed!")
    print("Branch tracking IS working.")
else:
    print("[ISSUE] No trees have access_count > 0")
    print("This means the tree.save() call is not persisting access_count updates")
    print("\nPossible causes:")
    print("1. Tree object not getting updated before save")
    print("2. Save method not writing access_count field")
    print("3. Tree being reloaded from disk after update")
