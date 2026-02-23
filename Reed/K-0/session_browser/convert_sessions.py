"""
Session Format Converter
Converts Reed's existing session format to Session Browser format

Your sessions use:
[
  {"you": "...", "kay": "..."},
  {"you": "...", "kay": "..."}
]

Session Browser expects:
{
  "session_id": "...",
  "start_time": "...",
  "conversation": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ]
}

Run this to convert all sessions:
    python session_browser/convert_sessions.py
"""

import json
import os
from pathlib import Path
from datetime import datetime
import shutil


def convert_session_file(input_path: Path, output_dir: Path) -> bool:
    """
    Convert a single session file

    Args:
        input_path: Path to existing session file
        output_dir: Directory to save converted session

    Returns:
        True if successful
    """

    print(f"Converting: {input_path.name}")

    try:
        # Load existing session
        with open(input_path, 'r', encoding='utf-8') as f:
            old_format = json.load(f)

        # Extract session_id from filename
        # Format: session_20251027_164612.json -> 20251027_164612
        filename = input_path.stem

        if filename.startswith("session_"):
            session_id = filename.replace("session_", "")
        elif filename.startswith("test_session_"):
            session_id = filename.replace("test_session_", "")
        else:
            session_id = filename

        # Parse datetime from session_id if possible
        try:
            # Format: YYYYMMDD_HHMMSS
            if "_" in session_id:
                date_part, time_part = session_id.split("_")
                year = date_part[:4]
                month = date_part[4:6]
                day = date_part[6:8]
                hour = time_part[:2]
                minute = time_part[2:4]
                second = time_part[4:6]

                start_time = f"{year}-{month}-{day}T{hour}:{minute}:{second}"
            else:
                start_time = datetime.now().isoformat()
        except:
            start_time = datetime.now().isoformat()

        # Convert conversation format
        conversation = []

        for turn in old_format:
            # User turn
            if "you" in turn:
                conversation.append({
                    "role": "user",
                    "content": turn["you"],
                    "timestamp": start_time  # We don't have per-turn timestamps
                })

            # Kay turn
            if "kay" in turn:
                conversation.append({
                    "role": "assistant",
                    "content": turn["kay"],
                    "timestamp": start_time
                })

        # Build new format
        new_format = {
            "session_id": session_id,
            "start_time": start_time,
            "conversation": conversation,
            "entity_graph": {},  # Placeholder
            "emotional_state": {}  # Placeholder
        }

        # Save converted session
        output_path = output_dir / f"{session_id}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(new_format, f, indent=2, ensure_ascii=False)

        print(f"  -> Saved to: {output_path.name}")
        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def convert_all_sessions(
    input_dir: str = "sessions",
    output_dir: str = "saved_sessions",
    backup: bool = True
):
    """
    Convert all sessions from old format to new format

    Args:
        input_dir: Directory with existing sessions
        output_dir: Directory for converted sessions
        backup: Whether to backup original sessions first
    """

    print("=" * 70)
    print("SESSION FORMAT CONVERTER")
    print("=" * 70)
    print()

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Check input directory
    if not input_path.exists():
        print(f"ERROR: Input directory not found: {input_path}")
        return

    # Create output directory
    output_path.mkdir(exist_ok=True)
    print(f"Input directory: {input_path.absolute()}")
    print(f"Output directory: {output_path.absolute()}")
    print()

    # Backup if requested
    if backup:
        backup_dir = Path(f"{input_dir}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print(f"Creating backup: {backup_dir}")
        shutil.copytree(input_path, backup_dir)
        print(f"  Backup created successfully")
        print()

    # Find session files
    json_files = list(input_path.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {input_path}")
        return

    print(f"Found {len(json_files)} session files")
    print()

    # Convert each file
    successful = 0
    failed = 0

    for file_path in json_files:
        if convert_session_file(file_path, output_path):
            successful += 1
        else:
            failed += 1

    print()
    print("=" * 70)
    print("CONVERSION COMPLETE")
    print("=" * 70)
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {len(json_files)}")
    print()
    print(f"Converted sessions saved to: {output_path.absolute()}")
    print()

    if successful > 0:
        print("Next steps:")
        print("1. Test the session browser:")
        print("   python session_browser/demo_browser.py")
        print()
        print("2. In your reed_ui.py, make sure session_dir points to 'saved_sessions':")
        print("   session_dir='saved_sessions'")
        print()
        print("3. From now on, save new sessions in the new format")


def quick_convert():
    """Quick conversion with defaults"""

    # Check what directories exist
    sessions_dir = Path("sessions")
    k0_sessions_dir = Path("K-0/sessions")

    if sessions_dir.exists():
        print("Found sessions in: ./sessions")
        convert_all_sessions(
            input_dir="sessions",
            output_dir="saved_sessions",
            backup=True
        )
    elif k0_sessions_dir.exists():
        print("Found sessions in: ./K-0/sessions")
        convert_all_sessions(
            input_dir="K-0/sessions",
            output_dir="saved_sessions",
            backup=True
        )
    else:
        print("ERROR: No sessions directory found")
        print()
        print("Looking for one of:")
        print("  - ./sessions")
        print("  - ./K-0/sessions")
        print()
        print("Please specify the correct directory:")
        print('  convert_all_sessions(input_dir="your/session/dir")')


if __name__ == "__main__":
    quick_convert()
