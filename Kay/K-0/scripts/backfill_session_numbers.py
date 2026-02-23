"""
Migration Script: Backfill Session Numbers to Old Memories

Problem: Memories created before session tagging fix don't have session_order.
Solution: Use session snapshots to map timestamps → session_order, then update memories.

Run this ONCE after implementing session tagging to update historical memories.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def parse_timestamp(ts_str) -> Optional[datetime]:
    """Parse various timestamp formats into datetime."""
    if not ts_str:
        return None
    
    # Handle Unix timestamp (float or int)
    if isinstance(ts_str, (int, float)):
        try:
            return datetime.fromtimestamp(ts_str)
        except:
            return None
    
    # Handle string timestamps
    if not isinstance(ts_str, str):
        return None
    
    # Remove 'Z' suffix if present
    ts_str = ts_str.replace('Z', '+00:00')
    
    try:
        # Try ISO format with timezone
        return datetime.fromisoformat(ts_str)
    except:
        pass
    
    try:
        # Try ISO format without timezone
        dt = datetime.fromisoformat(ts_str.split('+')[0].split('Z')[0])
        return dt
    except:
        pass
    
    return None


def load_session_snapshots(snapshots_path: Path) -> List[Dict]:
    """Load and sort session snapshots by session_order."""
    try:
        with open(snapshots_path, 'r', encoding='utf-8') as f:
            snapshots = json.load(f)
        
        # Sort by session_order (most reliable)
        snapshots.sort(key=lambda s: s.get('session_order', 0))
        
        print(f"[MIGRATION] Loaded {len(snapshots)} session snapshots")
        return snapshots
    
    except FileNotFoundError:
        print(f"[MIGRATION] No snapshots file found at {snapshots_path}")
        return []
    except Exception as e:
        print(f"[MIGRATION] Error loading snapshots: {e}")
        return []


def build_session_timeline(snapshots: List[Dict]) -> List[Dict]:
    """
    Build timeline mapping session_order to time ranges.
    
    Returns list of dicts: {
        "session_order": 10,
        "start_time": datetime,
        "end_time": datetime
    }
    """
    timeline = []
    
    for i, snapshot in enumerate(snapshots):
        session_order = snapshot.get('session_order')
        end_time_str = snapshot.get('timestamp')
        
        if not session_order or not end_time_str:
            continue
        
        end_time = parse_timestamp(end_time_str)
        if not end_time:
            continue
        
        # Start time = previous session's end time (or very old for first session)
        if i > 0:
            prev_end_str = snapshots[i-1].get('timestamp')
            start_time = parse_timestamp(prev_end_str) if prev_end_str else datetime(2020, 1, 1)
        else:
            start_time = datetime(2020, 1, 1)  # Very old
        
        timeline.append({
            'session_order': session_order,
            'start_time': start_time,
            'end_time': end_time
        })
    
    print(f"[MIGRATION] Built timeline for {len(timeline)} sessions")
    return timeline


def find_session_for_timestamp(ts_str: str, timeline: List[Dict]) -> Optional[int]:
    """Find which session a timestamp belongs to."""
    ts = parse_timestamp(ts_str)
    if not ts:
        return None
    
    # Find session where start_time <= ts <= end_time
    for session in timeline:
        if session['start_time'] <= ts <= session['end_time']:
            return session['session_order']
    
    # If timestamp is after all sessions, assign to most recent
    if timeline and ts > timeline[-1]['end_time']:
        return timeline[-1]['session_order']
    
    return None


def backfill_memories(memory_file: Path, timeline: List[Dict]) -> Dict[str, int]:
    """
    Backfill session_order into memories that don't have it.
    
    Returns stats: {
        "total_memories": int,
        "already_tagged": int,
        "newly_tagged": int,
        "failed": int
    }
    """
    stats = {
        'total_memories': 0,
        'already_tagged': 0,
        'newly_tagged': 0,
        'failed': 0
    }
    
    # Load memory layers
    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[MIGRATION] Memory file not found: {memory_file}")
        return stats
    except Exception as e:
        print(f"[MIGRATION] Error loading memory file: {e}")
        return stats
    
    working = data.get('working', [])
    long_term = data.get('long_term', [])
    all_memories = working + long_term
    
    stats['total_memories'] = len(all_memories)
    
    # Backfill session_order
    for mem in all_memories:
        # Skip if already has session_order
        if mem.get('session_order') is not None:
            stats['already_tagged'] += 1
            continue
        
        # Try multiple timestamp fields
        timestamp = (
            mem.get('timestamp') or 
            mem.get('added_timestamp') or 
            mem.get('last_accessed')
        )
        
        if not timestamp:
            stats['failed'] += 1
            continue
        
        # Find session for this timestamp
        session_order = find_session_for_timestamp(timestamp, timeline)
        
        if session_order is not None:
            mem['session_order'] = session_order
            stats['newly_tagged'] += 1
        else:
            stats['failed'] += 1
    
    # Save updated memories
    try:
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"[MIGRATION] Saved updated memories to {memory_file}")
    except Exception as e:
        print(f"[MIGRATION] Error saving memories: {e}")
        return stats
    
    return stats


def main():
    """Run the migration."""
    print("=" * 60)
    print("SESSION NUMBER BACKFILL MIGRATION")
    print("=" * 60)
    
    # Paths
    base_dir = Path(__file__).parent.parent
    snapshots_path = base_dir / "data" / "emotional_snapshots.json"
    memory_file = base_dir / "memory" / "memory_layers.json"
    
    print(f"\nSnapshot file: {snapshots_path}")
    print(f"Memory file: {memory_file}")
    print()
    
    # Load session snapshots
    snapshots = load_session_snapshots(snapshots_path)
    if not snapshots:
        print("[MIGRATION] No snapshots found - nothing to do")
        return
    
    # Build timeline
    timeline = build_session_timeline(snapshots)
    if not timeline:
        print("[MIGRATION] Could not build session timeline")
        return
    
    print(f"\nSession timeline spans:")
    print(f"  First: Session #{timeline[0]['session_order']} "
          f"({timeline[0]['end_time'].strftime('%Y-%m-%d %H:%M')})")
    print(f"  Last:  Session #{timeline[-1]['session_order']} "
          f"({timeline[-1]['end_time'].strftime('%Y-%m-%d %H:%M')})")
    print()
    
    # Backfill memories
    print("Backfilling session numbers into memories...")
    stats = backfill_memories(memory_file, timeline)
    
    # Print results
    print()
    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"Total memories:        {stats['total_memories']}")
    print(f"Already tagged:        {stats['already_tagged']}")
    print(f"Newly tagged:          {stats['newly_tagged']}")
    print(f"Failed (no timestamp): {stats['failed']}")
    print()
    
    if stats['newly_tagged'] > 0:
        print(f"✅ Successfully tagged {stats['newly_tagged']} memories!")
    else:
        print("ℹ️  All memories already had session numbers")
    
    if stats['failed'] > 0:
        print(f"⚠️  {stats['failed']} memories could not be tagged (missing timestamps)")


if __name__ == "__main__":
    main()
