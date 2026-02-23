"""
Migrate documents.json from list format to dict format.

PROBLEM:
Some versions of documents.json are stored as a list, but all systems expect a dict.
This causes crashes: AttributeError: 'list' object has no attribute 'items'

SOLUTION:
Convert list format to dict format using doc_id/memory_id/filename as keys.

BEFORE (list format):
[
  {"filename": "doc1.txt", "full_text": "..."},
  {"filename": "doc2.txt", "full_text": "..."}
]

AFTER (dict format):
{
  "doc1.txt": {"filename": "doc1.txt", "full_text": "..."},
  "doc2.txt": {"filename": "doc2.txt", "full_text": "..."}
}

USAGE:
    python migrate_documents_format.py

SAFETY:
- Creates backup before modifying
- Shows preview of changes
- Asks for confirmation
- Can be run multiple times safely (idempotent)
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


DOCUMENTS_FILE = "memory/documents.json"
BACKUP_DIR = "memory/backups"


def create_backup(file_path: str) -> str:
    """Create timestamped backup of documents.json."""
    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"documents_{timestamp}.json")

    shutil.copy2(file_path, backup_path)
    return backup_path


def load_documents() -> tuple:
    """
    Load documents.json.

    Returns:
        Tuple of (data, is_list_format, error_message)
    """
    if not os.path.exists(DOCUMENTS_FILE):
        return None, False, "File does not exist"

    try:
        with open(DOCUMENTS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()

            if not content:
                return None, False, "File is empty"

            data = json.loads(content)

        is_list = isinstance(data, list)
        return data, is_list, None

    except json.JSONDecodeError as e:
        return None, False, f"JSON decode error: {e}"
    except Exception as e:
        return None, False, f"Error reading file: {e}"


def convert_list_to_dict(docs_list: list) -> dict:
    """
    Convert list format to dict format.

    Args:
        docs_list: List of document dicts

    Returns:
        Dict with doc_id as keys
    """
    docs_dict = {}

    for i, doc in enumerate(docs_list):
        if not isinstance(doc, dict):
            print(f"  [WARNING] Skipping non-dict item at index {i}: {type(doc)}")
            continue

        # Priority: id > doc_id > memory_id > filename > generated key
        doc_id = (doc.get('id') or
                 doc.get('doc_id') or
                 doc.get('memory_id') or
                 doc.get('filename', f'doc_{i}'))

        # Add doc_id to document if not present
        if 'doc_id' not in doc and 'id' not in doc:
            doc['doc_id'] = doc_id

        docs_dict[doc_id] = doc

    return docs_dict


def save_documents(docs_dict: dict):
    """Save documents in dict format."""
    with open(DOCUMENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(docs_dict, f, indent=2)


def main():
    print("="*60)
    print("Documents.json Format Migration")
    print("="*60)
    print()

    # Load current documents
    print(f"Loading {DOCUMENTS_FILE}...")
    data, is_list, error = load_documents()

    if error:
        print(f"[ERROR] {error}")
        return

    if not is_list:
        print("[OK] File is already in dict format")
        print(f"     Contains {len(data)} documents")
        print()
        print("No migration needed!")
        return

    # File is in list format, needs migration
    print(f"[FOUND] File is in LIST format")
    print(f"        Contains {len(data)} documents")
    print()

    # Convert to dict
    print("Converting to dict format...")
    docs_dict = convert_list_to_dict(data)

    print(f"[OK] Converted {len(data)} list items to {len(docs_dict)} dict entries")
    print()

    # Show preview
    print("Preview of converted format:")
    print("-" * 60)

    sample_count = min(3, len(docs_dict))
    for i, (doc_id, doc) in enumerate(list(docs_dict.items())[:sample_count]):
        filename = doc.get('filename', 'unknown')
        print(f"  Key: {doc_id}")
        print(f"  Filename: {filename}")
        if i < sample_count - 1:
            print()

    if len(docs_dict) > sample_count:
        print(f"  ... and {len(docs_dict) - sample_count} more")

    print("-" * 60)
    print()

    # Confirm
    response = input("Proceed with migration? (yes/no): ").strip().lower()

    if response != 'yes':
        print()
        print("[CANCELLED] Migration cancelled by user")
        return

    # Create backup
    print()
    print("Creating backup...")
    backup_path = create_backup(DOCUMENTS_FILE)
    print(f"[OK] Backup created: {backup_path}")

    # Save migrated format
    print()
    print("Saving migrated format...")
    save_documents(docs_dict)
    print(f"[OK] Saved: {DOCUMENTS_FILE}")

    print()
    print("="*60)
    print("MIGRATION COMPLETE")
    print("="*60)
    print()
    print(f"[OK] Converted from list format to dict format")
    print(f"[OK] {len(docs_dict)} documents migrated")
    print(f"[OK] Backup saved to: {backup_path}")
    print()
    print("All systems should now work correctly!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("[CANCELLED] Migration cancelled by user")
    except Exception as e:
        print()
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
