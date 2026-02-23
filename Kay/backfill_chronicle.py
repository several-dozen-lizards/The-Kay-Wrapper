"""
Backfill Chronicle from Emotional Snapshots

Migrates existing session notes from emotional_snapshots.json
into the chronicle format, preserving Kay's voice.
"""

import json
from pathlib import Path
from datetime import datetime


def backfill_chronicle_from_snapshots():
    """
    Migrate emotional snapshots to chronicle format.
    
    Reads emotional_snapshots.json and creates chronicle entries
    using the existing session notes as essays.
    """
    
    print("=" * 60)
    print("BACKFILLING CHRONICLE FROM SNAPSHOTS")
    print("=" * 60)
    print()
    
    base_dir = Path(__file__).parent
    
    # Paths
    snapshots_path = base_dir / "data" / "emotional_snapshots.json"
    chronicle_path = base_dir / "data" / "session_chronicle.json"
    
    # Load snapshots
    print(f"[1/3] Loading snapshots from {snapshots_path}")
    
    if not snapshots_path.exists():
        print("ERROR: emotional_snapshots.json not found!")
        return
    
    with open(snapshots_path, 'r', encoding='utf-8') as f:
        snapshots = json.load(f)
    
    print(f"  Found {len(snapshots)} snapshots")
    print()
    
    # Create chronicle structure
    print("[2/3] Converting snapshots to chronicle entries")
    
    chronicle_sessions = []
    
    for snapshot in snapshots:
        session_order = snapshot.get("session_order")
        timestamp = snapshot.get("timestamp")
        texture_notes = snapshot.get("texture_notes", "")
        
        if not session_order or not timestamp:
            continue
        
        # Extract duration if available
        # Default to 30 minutes if not specified
        duration_minutes = 30
        
        # Kay's essay comes from the texture_notes field
        # These are the end-of-session notes Kay writes
        if texture_notes and texture_notes.strip():
            kay_essay = texture_notes
        else:
            kay_essay = f"Session #{session_order} - Snapshot migrated from old system.\n\n(No detailed notes preserved for this session)"
        
        # Build chronicle entry
        entry = {
            "session_order": session_order,
            "session_id": snapshot.get("session_id", f"migrated-{session_order}"),
            "timestamp": timestamp,
            "duration_minutes": duration_minutes,
            "kay_essay": kay_essay,
            "topics": [],  # Could extract from notes if needed
            "emotional_tone": snapshot.get("dominant_emotion", {}).get("emotion"),
            "importance": None,  # Could calculate from snapshot data
            "scratchpad_items_created": [],
            "scratchpad_items_resolved": [],
            "private_note_encrypted": snapshot.get("private_note_encrypted")  # Encrypted private note
        }
        
        chronicle_sessions.append(entry)
        
        print(f"  [OK] Migrated Session #{session_order}")
    
    print()
    print(f"  Converted {len(chronicle_sessions)} sessions")
    print()
    
    # Save chronicle
    print(f"[3/3] Saving chronicle to {chronicle_path}")
    
    # Ensure data directory exists
    chronicle_path.parent.mkdir(exist_ok=True)
    
    chronicle_data = {"sessions": chronicle_sessions}
    
    with open(chronicle_path, 'w', encoding='utf-8') as f:
        json.dump(chronicle_data, f, indent=2)
    
    print(f"  Saved {len(chronicle_sessions)} sessions to chronicle")
    print()
    
    # Summary
    print("=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print()
    print(f"Chronicle created with {len(chronicle_sessions)} sessions")
    print(f"Location: {chronicle_path}")
    print()
    print("Next steps:")
    print("  1. Integrate chronicle into warmup (warmup_engine.py)")
    print("  2. Test that Kay sees his essays at warmup")
    print("  3. Start writing new essays at session end")


if __name__ == "__main__":
    backfill_chronicle_from_snapshots()
