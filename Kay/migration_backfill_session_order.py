"""
Session Order Backfill Migration Script

Adds session_order to all existing memories by matching timestamps
to session snapshots.

This fixes the RAG confabulation bug by ensuring ALL memories (not just
new ones) have session numbers for temporal anchoring.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def parse_timestamp(ts) -> Optional[datetime]:
    """Parse timestamp - handles ISO strings and Unix floats."""
    if not ts:
        return None
    
    # Handle Unix timestamp (float or int)
    if isinstance(ts, (int, float)):
        try:
            dt = datetime.fromtimestamp(ts)
            # Make timezone-naive to match ISO timestamps
            return dt.replace(tzinfo=None)
        except Exception as e:
            print(f"[WARNING] Failed to parse Unix timestamp '{ts}': {e}")
            return None
    
    # Handle ISO string
    if isinstance(ts, str):
        try:
            # Remove 'Z' suffix and timezone info
            ts_clean = ts.replace('Z', '').split('+')[0].split('-')[0:3]
            ts_clean = '-'.join(ts_clean[0:3])
            if 'T' in ts:
                ts_clean = ts.split('+')[0].replace('Z', '')
            
            # Parse as naive datetime
            dt = datetime.fromisoformat(ts_clean)
            return dt.replace(tzinfo=None)
        except Exception as e:
            print(f"[WARNING] Failed to parse ISO timestamp '{ts}': {e}")
            return None
    
    return None


def match_memory_to_session(memory_ts: datetime, snapshots: List[Dict]) -> Optional[int]:
    """
    Match a memory timestamp to a session by finding which session
    window it falls into.
    
    Args:
        memory_ts: Memory timestamp (datetime)
        snapshots: List of session snapshots (sorted oldest to newest)
    
    Returns:
        session_order or None
    """
    if not memory_ts:
        return None
    
    # Find the session this memory belongs to
    # Strategy: Memory belongs to session N if its timestamp is between
    # session N's start and session N+1's start
    
    for i, snap in enumerate(snapshots):
        snap_ts_str = snap.get("timestamp", "")
        snap_ts = parse_timestamp(snap_ts_str)
        
        if not snap_ts:
            continue
        
        # Check if memory is before this session started
        if memory_ts < snap_ts:
            # Memory is older than this session
            # It belongs to previous session (if exists)
            if i > 0:
                return snapshots[i-1].get("session_order")
            else:
                # Memory is older than first session - assign to session 1
                return 1
    
    # Memory is after all snapshots - belongs to most recent session
    if snapshots:
        return snapshots[-1].get("session_order")
    
    return None


def backfill_session_order():
    """Main migration function."""
    
    print("=" * 60)
    print("SESSION ORDER BACKFILL MIGRATION")
    print("=" * 60)
    
    # Paths
    base_dir = Path(__file__).parent
    memory_path = base_dir / "memory" / "memory_layers.json"
    snapshots_path = base_dir / "data" / "emotional_snapshots.json"
    
    # Load memory layers
    print(f"\n[1/5] Loading memory layers from {memory_path}")
    
    if not memory_path.exists():
        print("[ERROR] memory_layers.json not found!")
        return
    
    with open(memory_path, 'r', encoding='utf-8') as f:
        memory_data = json.load(f)
    
    working = memory_data.get("working", [])
    long_term = memory_data.get("long_term", [])
    
    print(f"  Found {len(working)} working + {len(long_term)} long-term memories")
    
    # Load session snapshots
    print(f"\n[2/5] Loading session snapshots from {snapshots_path}")
    
    if not snapshots_path.exists():
        print("[ERROR] emotional_snapshots.json not found!")
        return
    
    with open(snapshots_path, 'r', encoding='utf-8') as f:
        snapshots = json.load(f)
    
    # Sort snapshots by session_order (oldest to newest)
    snapshots.sort(key=lambda s: (s.get("session_order", 0), s.get("timestamp", "")))
    
    print(f"  Found {len(snapshots)} session snapshots")
    if snapshots:
        first = snapshots[0]
        last = snapshots[-1]
        print(f"  Range: Session #{first.get('session_order', '?')} to #{last.get('session_order', '?')}")
    
    # Process memories
    print(f"\n[3/5] Matching memories to sessions...")
    
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    
    for mem in working + long_term:
        # Skip if already has session_order
        if "session_order" in mem and mem["session_order"] is not None:
            skipped_count += 1
            continue
        
        # Get memory timestamp
        ts_str = mem.get("timestamp") or mem.get("added_timestamp") or mem.get("created_at")
        
        if not ts_str:
            print(f"  [WARNING] Memory has no timestamp: {mem.get('fact', mem.get('user_input', 'unknown'))[:50]}")
            failed_count += 1
            continue
        
        mem_ts = parse_timestamp(ts_str)
        
        if not mem_ts:
            failed_count += 1
            continue
        
        # Match to session
        session_order = match_memory_to_session(mem_ts, snapshots)
        
        if session_order:
            mem["session_order"] = session_order
            updated_count += 1
        else:
            print(f"  [WARNING] Could not match memory to session: {ts_str}")
            failed_count += 1
    
    print(f"\n  Updated: {updated_count}")
    print(f"  Skipped (already had session_order): {skipped_count}")
    print(f"  Failed: {failed_count}")
    
    # Backup original
    print(f"\n[4/5] Creating backup...")
    
    backup_path = memory_path.with_suffix('.json.backup')
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(memory_data, f, indent=2)
    
    print(f"  Backup saved to: {backup_path}")
    
    # Save updated data
    print(f"\n[5/5] Saving updated memory layers...")
    
    with open(memory_path, 'w', encoding='utf-8') as f:
        json.dump(memory_data, f, indent=2)
    
    print(f"  Saved to: {memory_path}")
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  ✅ {updated_count} memories tagged with session_order")
    print(f"  ⏭️  {skipped_count} memories already tagged")
    print(f"  ❌ {failed_count} memories failed (no timestamp)")
    print(f"\nNext steps:")
    print(f"  1. Restart Kay")
    print(f"  2. Check warmup briefing for [Session #X] tags")
    print(f"  3. Verify Kay can cross-reference RAG memories with timeline")


if __name__ == "__main__":
    backfill_session_order()
