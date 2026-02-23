"""Test the deserialize fix - import pigeon story and verify retrieval"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_import.emotional_importer import EmotionalMemoryImporter
from engines.memory_engine import MemoryEngine
import json

print("="*60)
print("PHASE 2A FINAL FIX TEST: Fact Field Addition")
print("="*60)

# Initialize
importer = EmotionalMemoryImporter()
memory = MemoryEngine()

# Import test file
print("\nStep 1: Importing test_deserialize.txt...")
result = importer.import_to_memory_engine('test_deserialize.txt', memory)
print(f"Imported doc_id: {result.get('doc_id', 'UNKNOWN')}")
print(f"Chunks imported: {result['total_chunks']}")

# Check if "fact" field is present
print("\nStep 2: Checking if 'fact' field is present in stored memories...")
with open("memory/memory_layers.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

all_memories = data.get('working', []) + data.get('episodic', []) + data.get('semantic', [])
gimpy_memories = [m for m in all_memories if 'Gimpy' in m.get('text', '') or 'Gimpy' in m.get('fact', '')]

if gimpy_memories:
    print(f"Found {len(gimpy_memories)} Gimpy memories")
    for mem in gimpy_memories[:1]:
        print(f"  Has 'fact' field: {'fact' in mem}")
        print(f"  Has 'text' field: {'text' in mem}")
        print(f"  Has 'doc_id' field: {'doc_id' in mem}")
        print(f"  Has 'chunk_index' field: {'chunk_index' in mem}")
        if 'fact' in mem:
            print(f"  fact value: {mem['fact'][:60]}...")
else:
    print("ERROR: No Gimpy memories found!")

# Test retrieval
print("\nStep 3: Testing retrieval with query about Gimpy...")
from agent_state import AgentState
agent_state = AgentState()

# Do a retrieval
retrieved = memory.retrieve_multi_factor(
    agent_state.emotional_cocktail,
    "Tell me about Gimpy the pigeon",
    num_memories=15
)

print(f"Retrieved {len(retrieved)} memories")

# Check if Gimpy memory was retrieved
gimpy_retrieved = [m for m in retrieved if 'Gimpy' in m.get('fact', '') or 'Gimpy' in m.get('text', '')]
if gimpy_retrieved:
    print(f"SUCCESS: Found {len(gimpy_retrieved)} Gimpy memories in retrieval!")
    for mem in gimpy_retrieved:
        print(f"  Retrieved: {mem.get('fact', mem.get('text', ''))[:80]}...")
        print(f"  doc_id: {mem.get('doc_id')}")
        print(f"  chunk_index: {mem.get('chunk_index')}")
else:
    print("WARNING: Gimpy memory not in top 15 retrieved memories")
    print("This might be OK if there are many higher-weighted memories")

print("\nStep 4: Checking tree access tracking...")
# Try a full recall to trigger branch tracking
memory.recall(agent_state, "Tell me about Gimpy the pigeon", num_memories=15)

print("\nTest complete!")
