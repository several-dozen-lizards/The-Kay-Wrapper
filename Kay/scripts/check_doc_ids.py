import json
import os

file_path = "memory/memory_layers.json"

if not os.path.exists(file_path):
    print("File not found:", file_path)
else:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    working = data.get('working', [])
    episodic = data.get('episodic', [])
    semantic = data.get('semantic', [])

    print(f"Working memories: {len(working)}")
    print(f"Episodic memories: {len(episodic)}")
    print(f"Semantic memories: {len(semantic)}")

    all_memories = working + episodic + semantic
    with_doc_id = [m for m in all_memories if 'doc_id' in m and m['doc_id'] is not None]

    print(f"\nMemories with doc_id field: {len(with_doc_id)}")

    if with_doc_id:
        sample = with_doc_id[0]
        print(f"\nSample memory with doc_id:")
        print(f"  doc_id: {sample.get('doc_id')}")
        print(f"  chunk_index: {sample.get('chunk_index')}")
        print(f"  Keys present: {list(sample.keys())[:20]}")

        # Check if it has 'text' or 'fact' field
        if 'text' in sample:
            print(f"  Content field: 'text' (value: {sample['text'][:60]}...)")
        elif 'fact' in sample:
            print(f"  Content field: 'fact' (value: {sample['fact'][:60]}...)")
        elif 'user_input' in sample:
            print(f"  Content field: 'user_input' (value: {sample['user_input'][:60]}...)")
        else:
            print(f"  WARNING: No content field found!")
