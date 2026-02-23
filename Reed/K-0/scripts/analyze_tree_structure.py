"""
Analyze tree file structure and chunk storage.
"""
import json
from pathlib import Path

# Read tree file
tree_file = Path("data/trees/tree_doc_1762052751.json")
with open(tree_file) as f:
    tree_data = json.load(f)

print("="*80)
print("TREE FILE STRUCTURE")
print("="*80)

# Extract doc
trees = tree_data.get('trees', {})
if trees:
    doc_id = list(trees.keys())[0]
    doc = trees[doc_id]

    print(f"\nDoc ID: {doc_id}")
    print(f"Title: {doc.get('title')}")
    print(f"Total chunks: {doc.get('total_chunks')}")
    print(f"Branches: {len(doc.get('branches', []))}")

    print("\nBranch structure:")
    for branch in doc.get('branches', []):
        print(f"  - {branch.get('title')}: {len(branch.get('chunk_indices', []))} chunks")
        print(f"    Indices: {branch.get('chunk_indices', [])[:5]}...")

# Check memory_layers for actual chunks
print("\n" + "="*80)
print("MEMORY LAYERS - CHUNK STORAGE")
print("="*80)

mem_file = Path("memory/memory_layers.json")
if mem_file.exists():
    with open(mem_file) as f:
        mem_data = json.load(f)

    working = mem_data.get('working_memory', [])
    episodic = mem_data.get('episodic_memory', [])
    semantic = mem_data.get('semantic_memory', [])

    print(f"\nWorking: {len(working)} memories")
    print(f"Episodic: {len(episodic)} memories")
    print(f"Semantic: {len(semantic)} memories")

    # Find memories with doc_id
    all_mems = working + episodic + semantic
    doc_mems = [m for m in all_mems if m.get('doc_id')]

    print(f"\nMemories with doc_id: {len(doc_mems)}")

    if doc_mems:
        # Find memories matching our tree's doc_id
        matching = [m for m in doc_mems if m.get('doc_id') == doc_id]
        print(f"Matching doc_id '{doc_id}': {len(matching)}")

        if matching:
            sample = matching[0]
            print("\nSample chunk structure:")
            print(f"  doc_id: {sample.get('doc_id')}")
            print(f"  chunk_index: {sample.get('chunk_index')}")
            print(f"  fact: {sample.get('fact', '')[:100]}...")
            print(f"  source_file: {sample.get('source_file')}")
            print(f"  type: {sample.get('type')}")
            print(f"  current_layer: {sample.get('current_layer')}")

# Check if there's a documents.json file
doc_file = Path("memory/documents.json")
if doc_file.exists():
    print("\n" + "="*80)
    print("DOCUMENTS.JSON")
    print("="*80)

    with open(doc_file) as f:
        docs_data = json.load(f)

    print(f"\nKeys: {list(docs_data.keys())}")
    if 'documents' in docs_data:
        print(f"Documents count: {len(docs_data['documents'])}")
        if docs_data['documents']:
            first_doc = list(docs_data['documents'].values())[0]
            print(f"\nFirst document structure:")
            print(f"  Keys: {list(first_doc.keys())}")
            if 'chunks' in first_doc:
                print(f"  Chunks: {len(first_doc['chunks'])}")
                if first_doc['chunks']:
                    print(f"\n  Sample chunk:")
                    chunk = first_doc['chunks'][0]
                    print(f"    Keys: {list(chunk.keys())}")
                    print(f"    Content preview: {chunk.get('content', chunk.get('text', ''))[:100]}...")
