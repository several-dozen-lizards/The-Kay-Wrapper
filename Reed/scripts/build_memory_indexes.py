"""
Build Memory Indexes for Lazy Loading

Run this script to create index files from existing memory data.
This enables fast startup with lazy loading.

Usage:
    python build_memory_indexes.py
"""

import json
import time
from engines.memory_index import MemoryIndex, IdentityIndex


def build_indexes():
    """Build all necessary index files."""
    print("=" * 70)
    print("BUILDING MEMORY INDEXES FOR LAZY LOADING")
    print("=" * 70)

    start_time = time.time()

    # 1. Build memory index
    print("\n[1/2] Building memory index...")
    mem_start = time.time()
    mem_index = MemoryIndex(
        index_path="memory/memory_index.json",
        data_path="memory/memories.json"
    )
    # Force rebuild if exists
    mem_index._build_index_from_data()
    mem_time = time.time() - mem_start
    print(f"      Memory index built in {mem_time:.3f}s")
    print(f"      Indexed: {len(mem_index.indexes)} memories")

    # 2. Build identity index
    print("\n[2/2] Building identity index...")
    id_start = time.time()
    id_index = IdentityIndex(
        index_path="memory/identity_index.json",
        data_path="memory/identity_memory.json"
    )
    # Force rebuild if exists
    id_index._build_index()
    id_time = time.time() - id_start

    critical_count = len(id_index.critical_re) + len(id_index.critical_kay)
    context_count = len(id_index.context_re) + len(id_index.context_kay)
    detail_count = len(id_index.detail_re) + len(id_index.detail_kay)

    print(f"      Identity index built in {id_time:.3f}s")
    print(f"      Critical facts: {critical_count}")
    print(f"      Context facts: {context_count}")
    print(f"      Detail facts: {detail_count}")

    total_time = time.time() - start_time

    print("\n" + "=" * 70)
    print(f"INDEX BUILD COMPLETE in {total_time:.3f}s")
    print("=" * 70)
    print("\nGenerated files:")
    print("  - memory/memory_index.json")
    print("  - memory/identity_index.json")
    print("\nTo use lazy loading:")
    print("  1. Import LazyMemoryEngine instead of MemoryEngine")
    print("  2. Initialize with lazy_mode=True (default)")
    print("  3. Enjoy <1s startup times!")


if __name__ == "__main__":
    build_indexes()
