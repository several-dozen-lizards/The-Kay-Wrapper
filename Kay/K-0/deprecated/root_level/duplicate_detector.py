"""
Duplicate Detector - Prevents Re-importing Existing Documents

Detects:
- Exact duplicates (same filename + content)
- Updated files (same filename, different content)
- New files (never imported before)
"""

import json
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from tkinter import messagebox


class DuplicateDetector:
    """Detects duplicate documents before import."""

    def __init__(self, documents_file: str = "memory/documents.json"):
        self.documents_file = documents_file

    def calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            Hex string of SHA-256 hash
        """
        sha256_hash = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"[DUPLICATE DETECTOR] Error hashing {file_path}: {e}")
            return ""

    def get_existing_documents(self) -> Dict:
        """
        Load existing documents from storage.

        Returns:
            Dict mapping doc_id to document metadata
        """
        if not os.path.exists(self.documents_file):
            return {}

        try:
            with open(self.documents_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

                # Handle empty file
                if not content:
                    print(f"[DUPLICATE DETECTOR] Warning: {self.documents_file} is empty")
                    return {}

                docs_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"[DUPLICATE DETECTOR] Error: {self.documents_file} is corrupted: {e}")
            return {}
        except Exception as e:
            print(f"[DUPLICATE DETECTOR] Error loading documents: {e}")
            return {}

        # Handle both list and dict formats
        if isinstance(docs_data, list):
            print(f"[DUPLICATE DETECTOR] Converting list format to dict ({len(docs_data)} documents)")
            # Convert list to dict using doc_id, memory_id, or filename as key
            docs_dict = {}
            for i, doc in enumerate(docs_data):
                if not isinstance(doc, dict):
                    continue

                # Priority: doc_id > memory_id > filename > generated key
                doc_id = (doc.get('doc_id') or
                         doc.get('memory_id') or
                         doc.get('filename', f'doc_{i}'))
                docs_dict[doc_id] = doc

            return docs_dict

        elif isinstance(docs_data, dict):
            return docs_data

        else:
            print(f"[DUPLICATE DETECTOR] Error: Unexpected format (type: {type(docs_data)})")
            return {}

    def check_duplicate(self, file_path: str) -> Optional[Dict]:
        """
        Check if a file is a duplicate of an existing document.

        Args:
            file_path: Path to file to check

        Returns:
            Dict with duplicate info if found, None if new file:
            {
                "is_duplicate": bool,
                "duplicate_type": "exact" | "updated" | None,
                "existing_doc_id": str,
                "existing_doc": dict,
                "imported_at": str,
                "memory_count": int
            }
        """
        filename = Path(file_path).name
        new_hash = self.calculate_file_hash(file_path)

        existing_docs = self.get_existing_documents()

        for doc_id, doc_data in existing_docs.items():
            existing_filename = doc_data.get("filename", "")

            # Check for filename match
            if existing_filename.lower() == filename.lower():
                existing_hash = doc_data.get("content_hash", "")

                if existing_hash and existing_hash == new_hash:
                    # Exact duplicate
                    return {
                        "is_duplicate": True,
                        "duplicate_type": "exact",
                        "existing_doc_id": doc_id,
                        "existing_doc": doc_data,
                        "imported_at": doc_data.get("import_date", "unknown"),
                        "memory_count": doc_data.get("chunk_count", 0)
                    }
                else:
                    # Same filename, different content (updated file)
                    return {
                        "is_duplicate": True,
                        "duplicate_type": "updated",
                        "existing_doc_id": doc_id,
                        "existing_doc": doc_data,
                        "imported_at": doc_data.get("import_date", "unknown"),
                        "memory_count": doc_data.get("chunk_count", 0)
                    }

        # No duplicate found
        return None

    def get_duplicate_summary(self, file_paths: List[str]) -> Dict:
        """
        Analyze a list of files for duplicates.

        Args:
            file_paths: List of file paths to check

        Returns:
            Summary dict:
            {
                "new_files": [file_path, ...],
                "exact_duplicates": [(file_path, dup_info), ...],
                "updated_files": [(file_path, dup_info), ...],
                "has_duplicates": bool
            }
        """
        new_files = []
        exact_duplicates = []
        updated_files = []

        for file_path in file_paths:
            dup_info = self.check_duplicate(file_path)

            if not dup_info:
                new_files.append(file_path)
            elif dup_info["duplicate_type"] == "exact":
                exact_duplicates.append((file_path, dup_info))
            elif dup_info["duplicate_type"] == "updated":
                updated_files.append((file_path, dup_info))

        return {
            "new_files": new_files,
            "exact_duplicates": exact_duplicates,
            "updated_files": updated_files,
            "has_duplicates": len(exact_duplicates) + len(updated_files) > 0
        }


def duplicate_dialog_tk(title: str, filename: str, dup_info: Dict) -> str:
    """
    Show a dialog asking user what to do with a duplicate.

    Args:
        title: Dialog title
        filename: Name of the duplicate file
        dup_info: Duplicate information dict

    Returns:
        User action: "skip", "replace", "new_copy", or "cancel"
    """
    dup_type = dup_info.get("duplicate_type", "exact")
    imported_at = dup_info.get("imported_at", "unknown")
    memory_count = dup_info.get("memory_count", 0)

    if dup_type == "exact":
        message = (
            f'File "{filename}" was already imported.\n\n'
            f"Originally imported: {imported_at}\n"
            f"Memories created: {memory_count}\n\n"
            f"This is an exact duplicate (same content).\n\n"
            f"What would you like to do?"
        )
    else:  # updated
        message = (
            f'File "{filename}" was previously imported.\n\n'
            f"Originally imported: {imported_at}\n"
            f"Memories created: {memory_count}\n\n"
            f"The file content has CHANGED since last import.\n\n"
            f"What would you like to do?"
        )

    # Custom dialog with multiple options
    from tkinter import Toplevel, Label, Button, Frame

    dialog = Toplevel()
    dialog.title(title)
    dialog.geometry("500x300")
    dialog.resizable(False, False)

    # Message
    Label(dialog, text=message, justify="left", padx=20, pady=20).pack()

    # Result variable
    result = {"action": "skip"}

    def set_action(action):
        result["action"] = action
        dialog.destroy()

    # Buttons
    button_frame = Frame(dialog)
    button_frame.pack(pady=20)

    Button(button_frame, text="Skip (don't import)", command=lambda: set_action("skip"), width=20).pack(side="left", padx=5)
    Button(button_frame, text="Replace (delete old)", command=lambda: set_action("replace"), width=20).pack(side="left", padx=5)
    Button(button_frame, text="Import as Copy", command=lambda: set_action("new_copy"), width=20).pack(side="left", padx=5)

    cancel_btn = Button(dialog, text="Cancel All", command=lambda: set_action("cancel"), width=20, bg="red", fg="white")
    cancel_btn.pack(pady=10)

    # Make modal
    dialog.transient()
    dialog.grab_set()
    dialog.wait_window()

    return result["action"]
