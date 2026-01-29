"""
Complete diagnostic of document storage and retrieval system.
"""
import json
from pathlib import Path

print("="*80)
print("DOCUMENT STORAGE SYSTEM DIAGNOSTIC")
print("="*80)

# 1. Check tree file structure
print("\n1. TREE FILE STRUCTURE")
print("-" * 40)

tree_file = Path("data/trees/tree_doc_1762052751.json")
with open(tree_file) as f:
    tree_data = json.load(f)

trees = tree_data.get('trees', {})
doc_id = list(trees.keys())[0]
tree = trees[doc_id]

print(f"Doc ID: {doc_id}")
print(f"Source: {tree.get('title')}")
print(f"Total chunks: {tree.get('total_chunks')}")
print(f"Branches: {len(tree.get('branches', []))}")

print("\nBranch details:")
for branch in tree.get('branches', []):
    print(f"  {branch.get('title')}: {len(branch.get('chunk_indices', []))} chunks")
    print(f"    Indices: {branch.get('chunk_indices')}")
    print(f"    Tier: {branch.get('access_tier')}")

# 2. Check documents.json structure
print("\n2. DOCUMENTS.JSON STRUCTURE")
print("-" * 40)

docs_file = Path("memory/documents.json")
with open(docs_file) as f:
    docs_data = json.load(f)

doc = docs_data.get(doc_id)
if doc:
    print(f"Document found: {doc.get('filename')}")
    print(f"Full text length: {len(doc.get('full_text', ''))}")
    print(f"Word count: {doc.get('word_count')}")
    print(f"Chunk count: {doc.get('chunk_count')}")
    print(f"Topic tags: {doc.get('topic_tags', [])}")

    # Show first 500 chars of full_text
    full_text = doc.get('full_text', '')
    print(f"\nFull text preview (first 500 chars):")
    print(full_text[:500])

# 3. Check memory_layers for chunks
print("\n3. MEMORY LAYERS")
print("-" * 40)

mem_file = Path("memory/memory_layers.json")
with open(mem_file) as f:
    mem_data = json.load(f)

working = mem_data.get('working_memory', [])
episodic = mem_data.get('episodic_memory', [])
semantic = mem_data.get('semantic_memory', [])

print(f"Working: {len(working)}")
print(f"Episodic: {len(episodic)}")
print(f"Semantic: {len(semantic)}")

all_mems = working + episodic + semantic
doc_mems = [m for m in all_mems if m.get('doc_id') == doc_id]

print(f"\nMemories with matching doc_id: {len(doc_mems)}")

if doc_mems:
    print("\nSample chunk from memory:")
    chunk = doc_mems[0]
    print(f"  chunk_index: {chunk.get('chunk_index')}")
    print(f"  fact: {chunk.get('fact', '')[:200]}...")
    print(f"  type: {chunk.get('type')}")
    print(f"  layer: {chunk.get('current_layer')}")

# 4. CRITICAL ISSUE DIAGNOSIS
print("\n4. CRITICAL ISSUE DIAGNOSIS")
print("-" * 40)

print("\nPROBLEM IDENTIFIED:")
print("  - Tree files store chunk_indices but NOT chunk content")
print("  - Documents.json stores full_text but NOT individual chunks")
print("  - Memory_layers stores active chunks but is currently EMPTY")

print("\nIMPLICATIONS:")
print("  - DocumentIndex.load_tree() cannot retrieve chunk content from tree files")
print("  - Chunks must be reconstructed from full_text OR retrieved from memory_layers")
print("  - Current implementation will fail because trees don't have 'chunks' with 'content'")

print("\nSOLUTION NEEDED:")
print("  1. Update DocumentIndex to load from documents.json + tree metadata")
print("  2. OR: Update tree files to include chunk content (not just indices)")
print("  3. OR: Update _retrieve_document_tree_chunks() to query memory_layers first")

# 5. Check what DocumentIndex currently does
print("\n5. CURRENT DocumentIndex BEHAVIOR")
print("-" * 40)

from engines.document_index import DocumentIndex

idx = DocumentIndex()
print(f"Indexed {len(idx.index)} documents")

# Try to load the tree
loaded_tree = idx.load_tree(doc_id)
if loaded_tree:
    print(f"\nLoaded tree structure:")
    print(f"  Keys: {list(loaded_tree.keys())}")
    print(f"  Trees: {list(loaded_tree.get('trees', {}).keys())}")

    # Check if branches have content
    tree_doc = loaded_tree.get('trees', {}).get(doc_id, {})
    branches = tree_doc.get('branches', [])
    if branches:
        first_branch = branches[0]
        print(f"\nFirst branch structure:")
        print(f"  Keys: {list(first_branch.keys())}")
        print(f"  Has 'chunks' field: {'chunks' in first_branch}")
        print(f"  Has 'content' field: {'content' in first_branch}")
        print(f"  Has 'chunk_indices' field: {'chunk_indices' in first_branch}")
else:
    print("  Failed to load tree")

print("\n" + "="*80)
print("END DIAGNOSTIC")
print("="*80)
