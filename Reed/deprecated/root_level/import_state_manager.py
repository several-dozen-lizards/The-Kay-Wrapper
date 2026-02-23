"""
Import State Manager - Pause/Resume Support for Document Imports

Tracks import progress and enables:
- Pausing imports mid-process
- Resuming after interruption
- Recovering from crashes
- API rate limit handling
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class ImportStateManager:
    """Manages import session state for pause/resume functionality."""

    def __init__(self, state_file: str = "memory/import_state.json"):
        self.state_file = state_file
        self.current_session: Optional[Dict] = None

    def start_import(self, file_paths: List[str]) -> str:
        """
        Start a new import session.

        Args:
            file_paths: List of file paths to import

        Returns:
            session_id: Unique identifier for this import session
        """
        session_id = f"import_{int(datetime.now().timestamp())}"

        self.current_session = {
            "session_id": session_id,
            "started_at": datetime.now().isoformat(),
            "total_files": len(file_paths),
            "files": file_paths,
            "completed_files": [],
            "failed_files": [],
            "current_index": 0,
            "paused": False,
            "paused_at": None,
            "completed": False
        }

        self._save_state()
        return session_id

    def mark_file_completed(self, file_path: str, success: bool = True):
        """
        Mark a file as completed (successfully or failed).

        Args:
            file_path: Path of the completed file
            success: True if import succeeded, False if failed
        """
        if not self.current_session:
            return

        if success:
            self.current_session["completed_files"].append(file_path)
        else:
            self.current_session["failed_files"].append(file_path)

        self.current_session["current_index"] += 1
        self._save_state()

    def pause_import(self):
        """Pause the current import session."""
        if not self.current_session:
            return

        self.current_session["paused"] = True
        self.current_session["paused_at"] = datetime.now().isoformat()
        self._save_state()

    def resume_import(self):
        """Resume a paused import session."""
        if not self.current_session:
            return

        self.current_session["paused"] = False
        self.current_session["paused_at"] = None
        self._save_state()

    def complete_import(self):
        """Mark the import session as completed."""
        if not self.current_session:
            return

        self.current_session["completed"] = True
        self.current_session["completed_at"] = datetime.now().isoformat()
        self._save_state()

    def cancel_import(self, save_state: bool = False):
        """
        Cancel the current import session.

        Args:
            save_state: If True, save state for potential resume. If False, delete state.
        """
        if not save_state:
            self._clear_state()
        else:
            self.pause_import()

        self.current_session = None

    def get_incomplete_import(self) -> Optional[Dict]:
        """
        Check if there's an incomplete import session.

        Returns:
            Session data if found, None otherwise
        """
        state = self._load_state()

        if not state:
            return None

        # Check if session is incomplete
        if state.get("completed"):
            return None

        # Verify files still exist
        remaining_files = state["files"][state["current_index"]:]
        if not remaining_files:
            return None

        return state

    def get_remaining_files(self) -> List[str]:
        """
        Get list of files remaining to be imported.

        Returns:
            List of file paths not yet processed
        """
        if not self.current_session:
            state = self._load_state()
            if not state:
                return []
            self.current_session = state

        current_idx = self.current_session.get("current_index", 0)
        return self.current_session["files"][current_idx:]

    def get_progress(self) -> Dict:
        """
        Get current import progress.

        Returns:
            Dict with completed, total, percentage, failed counts
        """
        if not self.current_session:
            return {
                "completed": 0,
                "total": 0,
                "percentage": 0.0,
                "failed": 0,
                "remaining": 0
            }

        completed = len(self.current_session["completed_files"])
        failed = len(self.current_session["failed_files"])
        total = self.current_session["total_files"]
        remaining = total - completed - failed

        return {
            "completed": completed,
            "total": total,
            "percentage": (completed / total * 100) if total > 0 else 0,
            "failed": failed,
            "remaining": remaining
        }

    def is_paused(self) -> bool:
        """Check if current session is paused."""
        if not self.current_session:
            return False
        return self.current_session.get("paused", False)

    def _save_state(self):
        """Save current session state to disk."""
        if not self.current_session:
            return

        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_session, f, indent=2)

    def _load_state(self) -> Optional[Dict]:
        """Load session state from disk."""
        if not os.path.exists(self.state_file):
            return None

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[STATE MANAGER] Error loading state: {e}")
            return None

    def _clear_state(self):
        """Delete state file."""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
