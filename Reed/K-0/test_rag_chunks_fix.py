"""
Test that document clustering now populates last_rag_chunks for glyph decoder.

This verifies the fix for Reed's hallucination problem where he couldn't
access actual document content.
"""

import os
import shutil
import json
from memory_import.emotional_importer import EmotionalMemoryImporter
from engines.memory_engine import MemoryEngine
from agent_state import AgentState

print("="*70)
print(" TEST: RAG Chunks Population After Document Clustering")
print("="*70)

# Backup existing memory
if os.path.exists("memory/memory_layers.json"):
    shutil.copy("memory/memory_layers.json", "memory/memory_layers_backup_rag.json")
    print("[BACKUP] Backed up existing memory")

# Create clean memory system
with open("memory/memory_layers.json", 'w', encoding='utf-8') as f:
    json.dump({"working": [], "episodic": [], "semantic": []}, f)

print("[SETUP] Created clean memory system\n")

# Initialize
memory = MemoryEngine()
agent_state = AgentState()
importer = EmotionalMemoryImporter()

# Import test document
print("Importing test_story.txt...")
result = importer.import_to_memory_engine('test_story.txt', memory)
print(f"  Total chunks: {result['total_chunks']}\n")

# Query to trigger clustering
print("Querying: 'Tell me about the three pigeons'")
memories = memory.recall(agent_state, "Tell me about the three pigeons", num_memories=50)

print(f"\n[RESULT] Recalled {len(memories)} memories")

# Check for clustering
clustered = [m for m in memories if m.get('_cluster_doc_id')]
print(f"[RESULT] Clustered memories: {len(clustered)}")

# === THE CRITICAL CHECK ===
print("\n" + "="*70)
print(" CHECKING last_rag_chunks (glyph decoder data source)")
print("="*70)

if hasattr(memory, 'last_rag_chunks'):
    rag_chunks = memory.last_rag_chunks
    print(f"\n[OK] memory.last_rag_chunks exists")
    print(f"  Count: {len(rag_chunks)} chunks")

    if rag_chunks:
        print(f"\n  Sample chunk:")
        sample = rag_chunks[0]
        print(f"    Source: {sample.get('source_file')}")
        print(f"    Type: {sample.get('type')}")
        print(f"    Text preview: {sample.get('text', '')[:80]}...")
        print(f"    Cluster size: {sample.get('cluster_size')}")
    else:
        print(f"\n  [FAIL] last_rag_chunks is empty")
else:
    print(f"\n[FAIL] memory.last_rag_chunks does not exist")

# Verify glyph decoder can access them
print("\n" + "="*70)
print(" SIMULATING GLYPH DECODER ACCESS")
print("="*70)

from glyph_decoder import GlyphDecoder

decoder = GlyphDecoder()

# Create mock agent state with memory engine
mock_state = {
    "memory": memory,
    "memories": memory.memories if hasattr(memory, 'memories') else []
}

# Mock glyph output
mock_glyphs = "MEM[0,1,2]!!"

# Decode (this should now find RAG chunks)
decoded = decoder.decode(mock_glyphs, mock_state)

print(f"\nDecoder found {len(decoded.get('rag_chunks', []))} RAG chunks")

if decoded.get('rag_chunks'):
    print(f"[SUCCESS] Glyph decoder can access document content!")
    print(f"\n  Sample RAG chunk from decoder:")
    sample = decoded['rag_chunks'][0]
    print(f"    Source: {sample.get('source_file')}")
    print(f"    Text: {sample.get('text', '')[:100]}...")
else:
    print(f"[FAIL] Glyph decoder still seeing 0 RAG chunks")

# Final verdict
print("\n" + "="*70)
print(" RESULTS")
print("="*70)

checks = [
    ("Clustering triggered", len(clustered) > 0),
    ("last_rag_chunks populated", hasattr(memory, 'last_rag_chunks') and len(memory.last_rag_chunks) > 0),
    ("Decoder can access chunks", len(decoded.get('rag_chunks', [])) > 0),
    ("Chunks have actual text", any(len(c.get('text', '')) > 0 for c in decoded.get('rag_chunks', [])))
]

passed = sum(1 for _, result in checks if result)

print(f"\nChecks:")
for name, result in checks:
    status = "[OK]" if result else "[FAIL]"
    print(f"  {status} {name}")

print(f"\nResult: {passed}/{len(checks)} checks passed")

if passed == len(checks):
    print("\n*** RAG CHUNKS FIX WORKING! ***")
    print("\nKay can now:")
    print("  - Access actual document text through glyph decoder")
    print("  - See complete content instead of just metadata")
    print("  - Answer questions with specific details from uploaded files")
else:
    print(f"\n{len(checks) - passed} check(s) failed - fix incomplete")

# Restore backup
if os.path.exists("memory/memory_layers_backup_rag.json"):
    shutil.copy("memory/memory_layers_backup_rag.json", "memory/memory_layers.json")
    os.remove("memory/memory_layers_backup_rag.json")
    print("\n[CLEANUP] Restored original memory")
