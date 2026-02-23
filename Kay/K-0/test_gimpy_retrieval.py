"""Detailed test to see if Gimpy is actually in retrieval results"""
from memory_import.emotional_importer import EmotionalMemoryImporter
from engines.memory_engine import MemoryEngine
from agent_state import AgentState
import json

print("Testing Gimpy retrieval in detail...\n")

# Initialize
memory = MemoryEngine()
agent_state = AgentState()

# Get all memories from layers
with open("memory/memory_layers.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

all_memories = data.get('working', []) + data.get('episodic', []) + data.get('semantic', [])
gimpy_memories = [m for m in all_memories if 'Gimpy' in m.get('fact', '')]

print(f"Gimpy memories in storage: {len(gimpy_memories)}")
if gimpy_memories:
    mem = gimpy_memories[0]
    print(f"  doc_id: {mem.get('doc_id')}")
    print(f"  chunk_index: {mem.get('chunk_index')}")
    print(f"  current_layer: {mem.get('current_layer')}")
    print(f"  importance_score: {mem.get('importance_score')}")
    print(f"  current_strength: {mem.get('current_strength')}")
    print(f"  fact: {mem.get('fact')[:80]}...")

# Do a retrieval
print("\nDoing retrieval...")
retrieved = memory.retrieve_multi_factor(
    agent_state.emotional_cocktail,
    "Tell me about Gimpy the pigeon",
    num_memories=100  # Request MORE to see if Gimpy appears further down
)

print(f"Retrieved {len(retrieved)} memories total")

# Check positions of Gimpy
for i, mem in enumerate(retrieved):
    if 'Gimpy' in mem.get('fact', ''):
        print(f"\nFOUND Gimpy at position {i}:")
        print(f"  fact: {mem.get('fact')[:80]}...")
        print(f"  doc_id: {mem.get('doc_id')}")
        print(f"  chunk_index: {mem.get('chunk_index')}")
        print(f"  retrieval_score: {mem.get('retrieval_score', 'N/A')}")
        break
else:
    print("\nGimpy NOT FOUND in retrieval results!")
    print("This means Gimpy's score is too low to beat other memories")

# Check if branch tracking happens with full recall
print("\n\nDoing full recall() to trigger branch tracking...")
memory.recall(agent_state, "Tell me about Gimpy the pigeon", num_memories=100)

print("\nChecking if tree access count increased...")
tree_path = f"data/trees/tree_{gimpy_memories[0].get('doc_id')}.json"
try:
    with open(tree_path, 'r', encoding='utf-8') as f:
        tree_data = json.load(f)
    print(f"Tree access_count: {tree_data.get('access_count')}")
    print(f"Branches:")
    for branch in tree_data.get('branches', []):
        print(f"  - {branch.get('title')}: access_count={branch.get('access_count')}, last_accessed={branch.get('last_accessed')}")
except FileNotFoundError:
    print(f"Tree file not found: {tree_path}")
