"""
Retroactive Co-Activation Migration
====================================
Adds co-activation links to existing memories by matching timestamps.
Memories stored within a time window were almost certainly in the same
context window — they were co-active.

Run ONCE with the Nexus server STOPPED:
    cd D:\\Wrappers\\Kay
    python migrate_coactivation.py

Safe to re-run — overwrites coactive fields with fresh links each time.
Only ADDS coactive fields, never modifies existing data.
"""

import json
import os
import hashlib
import time
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# === CONFIGURATION ===
COACTIVE_WINDOW_SECONDS = 60   # Memories within 60s were co-active
MAX_LINKS_PER_MEMORY = 10      # Cap co-activation links per item
MEMORY_DIR = Path(__file__).parent / "memory"
LAYERS_PATH = MEMORY_DIR / "memory_layers.json"
VECTOR_DB_PATH = MEMORY_DIR / "vector_db"


def generate_id(mem, index, layer):
    """Generate a stable ID for a memory entry."""
    # Use content hash + timestamp for stability across runs
    content = mem.get("user_input", "") or mem.get("fact", "") or mem.get("text", "")
    ts = str(mem.get("timestamp", mem.get("added_timestamp", index)))
    raw = f"{layer}:{index}:{ts}:{content[:100]}"
    h = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:10]
    return f"mem_{layer[:2]}_{index}_{h}"


def parse_timestamp(mem):
    """Extract epoch timestamp from a memory entry."""
    # Try direct epoch timestamp first
    ts = mem.get("timestamp")
    if isinstance(ts, (int, float)) and ts > 1_000_000_000:
        return float(ts)
    
    # Try ISO string
    ts_str = mem.get("added_timestamp") or mem.get("timestamp")
    if isinstance(ts_str, str):
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ]:
            try:
                dt = datetime.strptime(ts_str.split("+")[0].split("Z")[0], fmt)
                return dt.timestamp()
            except ValueError:
                continue
    return None


def load_memory_layers():
    """Load all memories from working + long-term layers, assign IDs."""
    if not LAYERS_PATH.exists():
        print(f"  ✗ memory_layers.json not found at {LAYERS_PATH}")
        return [], None
    
    with open(LAYERS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    items = []
    for layer_name in ["working", "long_term"]:
        layer = data.get(layer_name, [])
        for i, mem in enumerate(layer):
            ts = parse_timestamp(mem)
            if ts is None:
                continue
            
            mem_id = generate_id(mem, i, layer_name)
            mem_type = mem.get("type", "unknown")
            
            # Get a snippet for cross-reference
            if mem_type == "full_turn":
                snippet = (mem.get("user_input", "") or "")[:60]
            elif mem_type == "extracted_fact":
                snippet = (mem.get("fact", "") or "")[:60]
            else:
                snippet = (mem.get("text", "") or mem.get("fact", "") or "")[:60]
            
            items.append({
                "id": mem_id,
                "type": mem_type,
                "source": "memory_layer",
                "layer": layer_name,
                "timestamp": ts,
                "snippet": snippet,
                "index": i,           # Position in layer array
                "layer_name": layer_name,
                "ref": mem,           # Direct reference for writing back
            })
    
    return items, data


def load_rag_chunks():
    """Load RAG chunk metadata from ChromaDB."""
    chunks = []
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
        
        # Get the collection — try common names
        collection = None
        for name in ["documents", "kay_documents", "rag"]:
            try:
                collection = client.get_collection(name)
                break
            except Exception:
                continue
        
        if not collection:
            colls = client.list_collections()
            if colls:
                collection = colls[0]
                print(f"  → Using collection: {collection.name}")
            else:
                print("  ⚠ No ChromaDB collections found")
                return []
        
        # Get all documents with metadata
        all_data = collection.get(include=["metadatas", "documents"])
        
        ids = all_data.get("ids", [])
        metas = all_data.get("metadatas") or [{}] * len(ids)
        docs = all_data.get("documents") or [""] * len(ids)
        
        for doc_id, meta, doc in zip(ids, metas, docs):
            ts = parse_timestamp(meta) if meta else None
            if ts is None and meta:
                # Try other timestamp fields
                for key in ["added_at", "indexed_at", "created_at"]:
                    if key in meta:
                        ts = parse_timestamp({key: meta[key], "added_timestamp": meta[key]})
                        if ts:
                            break
            
            if ts:
                chunks.append({
                    "id": doc_id,
                    "type": "rag_chunk",
                    "source": "vector_store",
                    "source_file": (meta or {}).get("source_file", "unknown"),
                    "timestamp": ts,
                    "snippet": (doc or "")[:60],
                    "metadata": meta or {},
                })
        
        print(f"  → Collection '{collection.name}': {len(chunks)} chunks with timestamps")
        
    except ImportError:
        print("  ⚠ chromadb not installed — skipping RAG chunks")
    except Exception as e:
        print(f"  ⚠ Could not load RAG chunks: {e}")
    
    return chunks


def build_coactivation_links(all_items):
    """Build co-activation links by timestamp proximity."""
    # Sort by timestamp
    sorted_items = sorted(all_items, key=lambda x: x["timestamp"])
    n = len(sorted_items)
    
    links_map = defaultdict(list)  # id -> list of co-active item summaries
    
    for i, item in enumerate(sorted_items):
        t = item["timestamp"]
        
        # Scan forward within window (backward links are symmetric)
        j = i + 1
        while j < n and sorted_items[j]["timestamp"] - t <= COACTIVE_WINDOW_SECONDS:
            other = sorted_items[j]
            
            # Only link CROSS-TYPE items
            # (episodic ↔ fact, episodic ↔ rag, fact ↔ rag)
            same_type = (item["type"] == other["type"] and 
                        item["source"] == other["source"])
            if not same_type:
                link_fwd = {
                    "id": other["id"],
                    "type": other["type"],
                    "source": other["source"],
                    "snippet": other["snippet"],
                }
                link_bwd = {
                    "id": item["id"],
                    "type": item["type"],
                    "source": item["source"],
                    "snippet": item["snippet"],
                }
                links_map[item["id"]].append(link_fwd)
                links_map[other["id"]].append(link_bwd)
            j += 1
    
    # Cap links per item
    for item_id in links_map:
        if len(links_map[item_id]) > MAX_LINKS_PER_MEMORY:
            links_map[item_id] = links_map[item_id][:MAX_LINKS_PER_MEMORY]
    
    return links_map


def apply_to_memory_layers(links_map, memory_items, raw_data):
    """Write co-activation links and IDs back to memory layer items."""
    updated = 0
    for item in memory_items:
        mem = item["ref"]
        mem_id = item["id"]
        
        # Always write the ID (needed for future cross-referencing)
        mem["id"] = mem_id
        
        # Write co-activation links if any exist
        if mem_id in links_map and links_map[mem_id]:
            mem["coactive"] = links_map[mem_id]
            updated += 1
    
    # Save back
    with open(LAYERS_PATH, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, indent=2, default=str, ensure_ascii=False)
    
    return updated


def apply_to_rag_chunks(links_map, chunks):
    """Write co-activation links to ChromaDB chunk metadata."""
    updated = 0
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
        
        collection = None
        for name in ["documents", "kay_documents", "rag"]:
            try:
                collection = client.get_collection(name)
                break
            except Exception:
                continue
        if not collection:
            colls = client.list_collections()
            if colls:
                collection = colls[0]
        
        if not collection:
            print("  ⚠ No collection found for RAG update")
            return 0

        
        batch_ids = []
        batch_metadatas = []
        
        for chunk in chunks:
            chunk_id = chunk["id"]
            if chunk_id in links_map and links_map[chunk_id]:
                meta = chunk["metadata"].copy()
                meta["coactive"] = json.dumps(links_map[chunk_id])
                batch_ids.append(chunk_id)
                batch_metadatas.append(meta)
        
        if batch_ids:
            # Process in batches of 100
            for start in range(0, len(batch_ids), 100):
                end = min(start + 100, len(batch_ids))
                collection.update(
                    ids=batch_ids[start:end],
                    metadatas=batch_metadatas[start:end]
                )
            updated = len(batch_ids)
    
    except Exception as e:
        print(f"  ⚠ Could not update RAG chunks: {e}")
    
    return updated


def main():
    print("=" * 60)
    print("  CO-ACTIVATION MIGRATION")
    print(f"  Window: {COACTIVE_WINDOW_SECONDS}s | Max links: {MAX_LINKS_PER_MEMORY}")
    print("=" * 60)
    print()
    
    # Load everything
    print("[1/5] Loading memory layers...")
    memories, raw_data = load_memory_layers()
    if raw_data is None:
        return
    
    working_count = sum(1 for m in memories if m["layer"] == "working")
    lt_count = sum(1 for m in memories if m["layer"] == "long_term")
    print(f"  → {len(memories)} memories ({working_count} working, {lt_count} long-term)")
    
    # Count types
    type_counts = defaultdict(int)
    for m in memories:
        type_counts[m["type"]] += 1
    print(f"  → Types: {dict(type_counts)}")
    
    print()
    print("[2/5] Loading RAG chunks...")
    chunks = load_rag_chunks()
    print(f"  → {len(chunks)} chunks with timestamps")
    
    all_items = memories + chunks
    print(f"\n  Total items: {len(all_items)}")
    
    if len(all_items) < 2:
        print("  ✗ Not enough items to build links. Exiting.")
        return
    
    # Build links
    print()
    print("[3/5] Building co-activation links...")
    t0 = time.time()
    links_map = build_coactivation_links(all_items)
    elapsed = time.time() - t0
    
    linked_count = sum(1 for v in links_map.values() if v)
    total_links = sum(len(v) for v in links_map.values())
    print(f"  → {linked_count} items got co-activation links")
    print(f"  → {total_links} total links ({elapsed:.1f}s)")

    
    # Show sample links
    if links_map:
        sample_id = next(iter(links_map))
        sample_links = links_map[sample_id]
        print(f"\n  Sample: {sample_id}")
        for link in sample_links[:3]:
            print(f"    → {link['type']}:{link['source']} \"{link['snippet'][:40]}...\"")
    
    # Apply
    print()
    print("[4/5] Writing to memory layers...")
    mem_updated = apply_to_memory_layers(links_map, memories, raw_data)
    print(f"  → Updated {mem_updated} memory entries (+ IDs on all {len(memories)})")
    print(f"  → Saved {LAYERS_PATH}")
    
    print()
    print("[5/5] Writing to RAG chunks...")
    rag_updated = apply_to_rag_chunks(links_map, chunks)
    print(f"  → Updated {rag_updated} RAG chunks")
    
    print()
    print("=" * 60)
    print("  MIGRATION COMPLETE")
    print(f"  Memory layers: {mem_updated} items linked, {len(memories)} IDs assigned")
    print(f"  RAG chunks: {rag_updated} items linked")
    print(f"  Total cross-references: {total_links}")
    print("=" * 60)


if __name__ == "__main__":
    main()
