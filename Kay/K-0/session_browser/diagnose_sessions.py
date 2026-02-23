"""
Session Browser Diagnostic Tool
Helps identify why sessions aren't showing up

Run this to diagnose the issue:
    python session_browser/diagnose_sessions.py
"""

import os
import json
from pathlib import Path
import traceback


def diagnose():
    """Run diagnostics on session files"""

    print("="*70)
    print("SESSION BROWSER DIAGNOSTIC TOOL")
    print("="*70)
    print()

    # Check 1: Directory exists
    print("CHECK 1: Session Directory")
    print("-" * 70)

    session_dir = Path("saved_sessions")
    print(f"Looking for directory: {session_dir.absolute()}")

    if not session_dir.exists():
        print("❌ PROBLEM: Directory does not exist!")
        print()
        print("SOLUTION: Create the directory or check the path")
        print(f"  mkdir {session_dir}")
        return
    else:
        print(f"✓ Directory exists: {session_dir.absolute()}")

    print()

    # Check 2: Files in directory
    print("CHECK 2: Files in Directory")
    print("-" * 70)

    all_files = list(session_dir.glob("*"))
    json_files = list(session_dir.glob("*.json"))

    print(f"Total files: {len(all_files)}")
    print(f"JSON files: {len(json_files)}")

    if len(json_files) == 0:
        print("❌ PROBLEM: No .json files found in directory!")
        print()
        print("Files found:")
        for f in all_files[:10]:
            print(f"  - {f.name}")
        if len(all_files) > 10:
            print(f"  ... and {len(all_files) - 10} more")
        print()
        print("SOLUTION: Session files should be .json format")
        return
    else:
        print(f"✓ Found {len(json_files)} JSON files")
        print()
        print("Session files:")
        for f in json_files[:5]:
            print(f"  - {f.name}")
        if len(json_files) > 5:
            print(f"  ... and {len(json_files) - 5} more")

    print()

    # Check 3: File structure
    print("CHECK 3: File Structure")
    print("-" * 70)

    valid_sessions = 0
    invalid_sessions = 0
    errors = []

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check required fields
            has_session_id = "session_id" in data
            has_conversation = "conversation" in data
            has_start_time = "start_time" in data

            if has_session_id and has_conversation:
                valid_sessions += 1
            else:
                invalid_sessions += 1
                errors.append({
                    "file": file_path.name,
                    "issue": f"Missing fields - session_id:{has_session_id} conversation:{has_conversation} start_time:{has_start_time}"
                })

        except json.JSONDecodeError as e:
            invalid_sessions += 1
            errors.append({
                "file": file_path.name,
                "issue": f"Invalid JSON: {e}"
            })
        except Exception as e:
            invalid_sessions += 1
            errors.append({
                "file": file_path.name,
                "issue": f"Error: {e}"
            })

    print(f"Valid sessions: {valid_sessions}")
    print(f"Invalid sessions: {invalid_sessions}")

    if invalid_sessions > 0:
        print()
        print("❌ PROBLEMS FOUND:")
        for error in errors[:5]:
            print(f"  - {error['file']}: {error['issue']}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")
    else:
        print("✓ All sessions are valid")

    print()

    # Check 4: Sample session structure
    if valid_sessions > 0:
        print("CHECK 4: Sample Session Structure")
        print("-" * 70)

        sample_file = json_files[0]
        print(f"Examining: {sample_file.name}")
        print()

        with open(sample_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print("Structure:")
        print(f"  session_id: {data.get('session_id', 'MISSING')}")
        print(f"  start_time: {data.get('start_time', 'MISSING')}")
        print(f"  conversation: {len(data.get('conversation', []))} turns")

        if "metadata" in data:
            metadata = data["metadata"]
            print(f"  metadata:")
            print(f"    title: {metadata.get('title', 'MISSING')}")
            print(f"    summary: {metadata.get('summary', 'MISSING')[:50]}...")
            print(f"    turn_count: {metadata.get('turn_count', 'MISSING')}")
        else:
            print("  metadata: NOT PRESENT (will auto-generate on display)")

        print()

        # Show first conversation turn
        conversation = data.get("conversation", [])
        if conversation:
            print("First conversation turn:")
            first_turn = conversation[0]
            print(f"  role: {first_turn.get('role', 'MISSING')}")
            print(f"  content: {first_turn.get('content', 'MISSING')[:80]}...")
            print(f"  timestamp: {first_turn.get('timestamp', 'MISSING')}")

    print()

    # Check 5: Test SessionManager
    print("CHECK 5: Test SessionManager")
    print("-" * 70)

    try:
        # Add parent directory to path
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from session_browser.session_manager import SessionManager

        manager = SessionManager("saved_sessions")
        sessions = manager.list_sessions()

        print(f"SessionManager loaded: {len(sessions)} sessions")

        if len(sessions) == 0 and valid_sessions > 0:
            print("❌ PROBLEM: SessionManager isn't loading sessions!")
            print()
            print("This is likely a code issue. Let me check...")

            # Try loading one manually
            try:
                session_info = manager._load_session_info(json_files[0])
                print(f"Manual load test: {session_info}")
            except Exception as e:
                print(f"Manual load failed: {e}")
                traceback.print_exc()

        elif len(sessions) > 0:
            print("✓ SessionManager working correctly")
            print()
            print("Sample session info:")
            sample = sessions[0]
            print(f"  session_id: {sample.get('session_id')}")
            print(f"  title: {sample.get('title')}")
            print(f"  start_time: {sample.get('start_time')}")
            print(f"  turn_count: {sample.get('turn_count')}")

    except Exception as e:
        print(f"❌ ERROR: Failed to load SessionManager")
        print(f"Error: {e}")
        traceback.print_exc()

    print()

    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)

    if valid_sessions > 0 and len(sessions) > 0:
        print("✓ Everything looks good!")
        print(f"✓ {valid_sessions} valid sessions found")
        print(f"✓ SessionManager loaded {len(sessions)} sessions")
        print()
        print("If sessions still don't show in browser:")
        print("1. Check that session_dir parameter matches: 'saved_sessions'")
        print("2. Check for JavaScript/UI errors in console")
        print("3. Try running demo_browser.py to test UI")
    elif valid_sessions > 0 and len(sessions) == 0:
        print("⚠️  Sessions exist but SessionManager can't load them")
        print()
        print("This is a code issue. Check:")
        print("1. SessionManager import path")
        print("2. session_dir parameter")
        print("3. File permissions")
    elif valid_sessions == 0:
        print("❌ No valid sessions found")
        print()
        print("Check session file format. Sessions should look like:")
        print("""
{
  "session_id": "1763530042",
  "start_time": "2025-11-19T00:28:15.228014",
  "conversation": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ]
}
        """)

    print()
    print("="*70)


if __name__ == "__main__":
    diagnose()
