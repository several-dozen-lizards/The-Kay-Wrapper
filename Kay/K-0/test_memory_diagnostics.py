"""
Test script to trigger memory recall with diagnostic logging.
Shows memory composition by layer with detailed scoring diagnostics.
"""

import os
import sys

# Set verbose debug before importing config
os.environ['VERBOSE_DEBUG'] = 'true'

from engines.memory_engine import MemoryEngine
from agent_state import AgentState

print("=" * 80)
print("MEMORY COMPOSITION DIAGNOSTIC TEST")
print("=" * 80)

# Initialize components
print("\n[SETUP] Initializing memory engine...")

# Initialize memory engine (it creates entity graph, layers, etc internally)
memory_engine = MemoryEngine()

print(f"[SETUP] Memory engine initialized")
print(f"[SETUP] Total memories: {len(memory_engine.memories)}")
print(f"[SETUP] Working layer: {len(memory_engine.memory_layers.working_memory)} memories")
print(f"[SETUP] Episodic layer: {len(memory_engine.memory_layers.episodic_memory)} memories")
print(f"[SETUP] Semantic layer: {len(memory_engine.memory_layers.semantic_memory)} memories")

# Create agent state
agent_state = AgentState()
agent_state.emotional_cocktail = {"curiosity": {"intensity": 0.7, "age": 1}}

# Test query
user_input = "Tell me about Saga"
print(f"\n[TEST QUERY] '{user_input}'")
print(f"[TEST QUERY] Emotional cocktail: {agent_state.emotional_cocktail}")

# Trigger recall with diagnostic logging
print("\n" + "=" * 80)
print("TRIGGERING MEMORY RECALL (VERBOSE DEBUG ENABLED)")
print("=" * 80 + "\n")

result = memory_engine.recall(
    agent_state=agent_state,
    user_input=user_input,
    num_memories=30
)

# Show final composition
print("\n" + "=" * 80)
print("FINAL MEMORY COMPOSITION")
print("=" * 80)

total = len(result)
if total > 0:
    # Count by layer
    layer_counts = {
        'working': 0,
        'episodic': 0,
        'semantic': 0,
        'identity': 0,
        'entity': 0,
        'unknown': 0
    }

    for mem in result:
        layer = mem.get('layer', 'unknown')
        if layer in layer_counts:
            layer_counts[layer] += 1
        else:
            layer_counts['unknown'] += 1

    print(f"\nTotal memories retrieved: {total}")
    print("\nBreakdown by layer:")
    print(f"  - Identity: {layer_counts['identity']} ({layer_counts['identity']/total*100:.1f}%)")
    print(f"  - Working:  {layer_counts['working']} ({layer_counts['working']/total*100:.1f}%)")
    print(f"  - Episodic: {layer_counts['episodic']} ({layer_counts['episodic']/total*100:.1f}%)")
    print(f"  - Semantic: {layer_counts['semantic']} ({layer_counts['semantic']/total*100:.1f}%)")
    print(f"  - Entity:   {layer_counts['entity']} ({layer_counts['entity']/total*100:.1f}%)")
    if layer_counts['unknown'] > 0:
        print(f"  - Unknown:  {layer_counts['unknown']} ({layer_counts['unknown']/total*100:.1f}%)")

    # Compare to target
    print("\nComparison to target allocation:")
    print(f"  Working:  {layer_counts['working']/total*100:.1f}% (target: 20.0%)")
    print(f"  Episodic: {layer_counts['episodic']/total*100:.1f}% (target: 35.0%)")
    print(f"  Semantic: {layer_counts['semantic']/total*100:.1f}% (target: 45.0%)")
else:
    print("No memories retrieved!")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
