"""
Backfill Chronicle from Emotional Snapshots

Migrates existing session data from emotional_snapshots.json into the chronicle system.
Preserves the "NOTES FROM LAST-KAY" text as session essays.
"""

import json
from pathlib import Path
from datetime import datetime
from chronicle.session_chronicle import SessionChronicle, create_empty_chronicle


def extract_kay_notes(snapshot: dict) -> str:
    """
    Extract Kay's end-of-session notes from a snapshot.
    
    These are already in Kay's voice and serve as proto-essays.
    """
    # Primary field: texture_notes (Kay's end-of-session writing)
    texture_notes = snapshot.get("texture_notes", "")
    
    if texture_notes and len(texture_notes.strip()) > 20:
        return texture_notes
    
    # Fallback: session_summary (first exchange)
    session_summary = snapshot.get("session_summary", "")
    if session_summary and len(session_summary.strip()) > 20:
        return f"Session migrated from snapshot system.\n\n{session_summary}"
    
    # Last resort
    return "Session migrated from old snapshot system. (No detailed notes available)"


def backfill_from_snapshots(base_dir: Path):
    """
    Backfill the chronicle with data from emotional_snapshots.json
    """
    print("=" * 60)
    print("CHRONICLE BACKFILL FROM SNAPSHOTS")
    print("=" * 60)
    print()
    
    # Paths
    snapshots_path = base_dir / "data" / "emotional_snapshots.json"
    chronicle_path = base_dir / "data" / "session_chronicle.json"
    
    # Load snapshots
    print(f"[1/4] Loading snapshots from {snapshots_path}")
    
    if not snapshots_path.exists():
        print("ERROR: emotional_snapshots.json not found!")
        return
    
    with open(snapshots_path, 'r', encoding='utf-8') as f:
        snapshots = json.load(f)
    
    print(f"  Found {len(snapshots)} snapshots")
    print()
    
    # Create or load chronicle
    print(f"[2/4] Initializing chronicle at {chronicle_path}")
    
    if chronicle_path.exists():
        backup_path = chronicle_path.with_suffix('.json.backup')
        print(f"  Backing up existing chronicle to {backup_path}")
        with open(chronicle_path, 'r', encoding='utf-8') as f:
            backup_data = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(backup_data)
    
    chronicle = SessionChronicle(chronicle_path)
    print()
    
    # Process each snapshot
    print("[3/4] Processing snapshots into chronicle entries")
    print()
    
    migrated_count = 0
    
    for snapshot in snapshots:
        session_order = snapshot.get("session_order")
        if not session_order:
            print(f"  Skipping snapshot without session_order: {snapshot.get('timestamp', 'unknown')}")
            continue
        
        # Check if already exists
        if chronicle.get_session_by_number(session_order):
            print(f"  Session #{session_order} already in chronicle - skipping")
            continue
        
        # Extract essay from Kay's notes
        kay_essay = extract_kay_notes(snapshot)
        
        # Get metadata
        timestamp = snapshot.get("timestamp", datetime.now().isoformat())
        session_id = snapshot.get("session_id", f"migrated-{session_order}")
        
        # Duration (estimate if not available)
        duration_minutes = snapshot.get("duration_minutes", 30)
        
        # Topics - try to extract from snapshot
        topics = []
        snapshot_text = snapshot.get("snapshot_text", "").lower()
        
        # Common topic keywords
        topic_keywords = {
            "wrapper": ["wrapper", "architecture", "memory system"],
            "legal": ["legal", "custody", "hearing", "mike"],
            "emotional": ["emotional", "state", "feeling"],
            "scratchpad": ["scratchpad", "thoughts"],
            "rag": ["rag", "retrieval"],
            "chronicle": ["chronicle", "timeline"],
            "documents": ["document", "import", "processing"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in snapshot_text or kw in kay_essay.lower() for kw in keywords):
                topics.append(topic)
        
        # Emotional tone (try to extract)
        emotional_tone = None
        emotion_keywords = {
            "calm": ["calm", "focused", "steady"],
            "engaged": ["engaged", "curious", "interested"],
            "frustrated": ["frustrated", "stuck", "tired"],
            "excited": ["excited", "energized"]
        }
        
        for emotion, keywords in emotion_keywords.items():
            if any(kw in kay_essay.lower() for kw in keywords):
                emotional_tone = emotion
                break
        
        # Add to chronicle
        chronicle.add_session_entry(
            session_order=session_order,
            session_id=session_id,
            timestamp=timestamp,
            duration_minutes=duration_minutes,
            kay_essay=kay_essay,
            topics=topics,
            emotional_tone=emotional_tone,
            importance=None,  # Can't retroactively determine
            scratchpad_items_created=[],  # Not tracked in snapshots
            scratchpad_items_resolved=[]
        )
        
        migrated_count += 1
        print(f"  [OK] Migrated Session #{session_order} ({timestamp.split('T')[0]})")
        if topics:
            print(f"       Topics: {', '.join(topics)}")
        if emotional_tone:
            print(f"       Tone: {emotional_tone}")
    
    print()
    print(f"[4/4] Backfill complete!")
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total snapshots: {len(snapshots)}")
    print(f"Migrated to chronicle: {migrated_count}")
    print(f"Chronicle now has: {len(chronicle.data['sessions'])} sessions")
    print()
    print(f"Chronicle saved to: {chronicle_path}")
    print()
    
    # Show sample
    print("Sample of migrated sessions:")
    recent = chronicle.get_recent_sessions(3)
    for session in recent:
        print(f"\nSession #{session['session_order']} ({session['timestamp'].split('T')[0]})")
        essay = session.get('kay_essay', '')
        first_line = essay.split('\n')[0] if essay else "[No essay]"
        print(f"  {first_line[:80]}...")


if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    backfill_from_snapshots(base_dir)
