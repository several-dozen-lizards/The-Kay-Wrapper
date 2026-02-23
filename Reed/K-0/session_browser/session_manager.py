"""
Session Manager
Core operations for managing, searching, and manipulating sessions
"""

import json
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import shutil


class SessionManager:
    """
    Manages session files: loading, saving, searching, filtering, exporting
    """

    def __init__(self, session_dir: str = "saved_sessions"):
        """
        Args:
            session_dir: Directory where session JSON files are stored
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)

        # Cache for session list (invalidate on changes)
        self._session_cache = None
        self._cache_timestamp = None

    def list_sessions(self, force_reload: bool = False) -> List[Dict[str, Any]]:
        """
        List all sessions with basic info

        Returns:
            List of session info dicts sorted by start_time (newest first)
        """

        # Use cache if available and recent
        if not force_reload and self._session_cache is not None:
            cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
            if cache_age < 5:  # Cache valid for 5 seconds
                return self._session_cache

        sessions = []

        for file_path in self.session_dir.glob("*.json"):
            try:
                session_info = self._load_session_info(file_path)
                if session_info:
                    sessions.append(session_info)
            except Exception as e:
                print(f"Warning: Failed to load session {file_path.name}: {e}")
                continue

        # Sort by start_time (newest first)
        sessions.sort(key=lambda s: s.get("start_time", ""), reverse=True)

        # Update cache
        self._session_cache = sessions
        self._cache_timestamp = datetime.now()

        return sessions

    def _load_session_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load basic session info without full conversation content

        Returns dict with:
        - session_id
        - filepath
        - start_time
        - turn_count
        - title (from metadata or preview)
        - summary
        - tags
        - duration_minutes
        - file_size_kb
        """

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        session_id = data.get("session_id", file_path.stem)
        conversation = data.get("conversation", [])
        metadata = data.get("metadata", {})

        # Get title (from metadata or generate preview)
        title = metadata.get("title")
        if not title:
            # Fallback: first user message preview
            first_msg = next(
                (msg["content"] for msg in conversation if msg["role"] == "user"),
                None
            )
            if first_msg:
                title = (first_msg[:40] + "...") if len(first_msg) > 40 else first_msg
            else:
                title = f"Session {session_id}"

        # Calculate turn count
        turn_count = metadata.get("turn_count")
        if turn_count is None:
            turn_count = len([msg for msg in conversation if msg["role"] == "user"])

        # Get file size
        file_size_kb = file_path.stat().st_size / 1024

        return {
            "session_id": session_id,
            "filepath": str(file_path),
            "start_time": data.get("start_time", ""),
            "turn_count": turn_count,
            "title": title,
            "summary": metadata.get("summary", ""),
            "tags": metadata.get("tags", []),
            "key_topics": metadata.get("key_topics", []),
            "emotional_arc": metadata.get("emotional_arc", ""),
            "duration_minutes": metadata.get("duration_minutes", 0.0),
            "file_size_kb": round(file_size_kb, 1),
            "has_metadata": bool(metadata)
        }

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load full session data

        Args:
            session_id: Session ID to load

        Returns:
            Complete session data dict or None if not found
        """

        file_path = self.session_dir / f"{session_id}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    def save_session(
        self,
        session_data: Dict[str, Any],
        overwrite: bool = True
    ) -> bool:
        """
        Save session data to file

        Args:
            session_data: Session data dict (must include session_id)
            overwrite: Whether to overwrite existing file

        Returns:
            True if successful
        """

        session_id = session_data.get("session_id")
        if not session_id:
            raise ValueError("session_data must include session_id")

        file_path = self.session_dir / f"{session_id}.json"

        if file_path.exists() and not overwrite:
            raise FileExistsError(f"Session {session_id} already exists")

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            # Invalidate cache
            self._session_cache = None

            return True
        except Exception as e:
            print(f"Error saving session {session_id}: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session file

        Args:
            session_id: Session ID to delete

        Returns:
            True if successful
        """

        file_path = self.session_dir / f"{session_id}.json"

        if not file_path.exists():
            return False

        try:
            file_path.unlink()

            # Invalidate cache
            self._session_cache = None

            return True
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False

    def search_sessions(
        self,
        query: str,
        search_content: bool = True,
        search_metadata: bool = True
    ) -> List[Tuple[Dict[str, Any], List[str]]]:
        """
        Search sessions by text query

        Args:
            query: Search query string
            search_content: Whether to search conversation content
            search_metadata: Whether to search metadata (title, summary, tags)

        Returns:
            List of (session_info, context_snippets) tuples
        """

        query_lower = query.lower()
        results = []

        for file_path in self.session_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                matches = []

                # Search metadata
                if search_metadata:
                    metadata = data.get("metadata", {})

                    if query_lower in metadata.get("title", "").lower():
                        matches.append(f"Title: {metadata.get('title', '')}")

                    if query_lower in metadata.get("summary", "").lower():
                        matches.append(f"Summary: {metadata.get('summary', '')}")

                    tags = metadata.get("tags", [])
                    if any(query_lower in tag.lower() for tag in tags):
                        matches.append(f"Tags: {', '.join(tags)}")

                # Search content
                if search_content:
                    conversation = data.get("conversation", [])
                    for idx, turn in enumerate(conversation):
                        content = turn.get("content", "")
                        if query_lower in content.lower():
                            # Extract context snippet
                            start = max(0, content.lower().index(query_lower) - 50)
                            end = min(len(content), start + 150)
                            snippet = content[start:end]
                            if start > 0:
                                snippet = "..." + snippet
                            if end < len(content):
                                snippet = snippet + "..."

                            role = "User" if turn["role"] == "user" else "Kay"
                            matches.append(f"Turn {idx+1} ({role}): {snippet}")

                            # Limit context snippets
                            if len(matches) >= 5:
                                break

                if matches:
                    session_info = self._load_session_info(file_path)
                    results.append((session_info, matches[:5]))  # Max 5 snippets

            except Exception as e:
                print(f"Error searching session {file_path.name}: {e}")
                continue

        # Sort by relevance (number of matches)
        results.sort(key=lambda x: len(x[1]), reverse=True)

        return results

    def filter_sessions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        min_turns: Optional[int] = None,
        max_turns: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter sessions by criteria

        Args:
            start_date: Filter sessions after this date
            end_date: Filter sessions before this date
            tags: Filter sessions with any of these tags
            min_turns: Minimum turn count
            max_turns: Maximum turn count

        Returns:
            Filtered list of session info dicts
        """

        all_sessions = self.list_sessions()
        filtered = []

        for session_info in all_sessions:
            # Date filter
            if start_date or end_date:
                try:
                    session_time = datetime.fromisoformat(session_info["start_time"])

                    if start_date and session_time < start_date:
                        continue
                    if end_date and session_time > end_date:
                        continue
                except (ValueError, KeyError):
                    continue

            # Tag filter
            if tags:
                session_tags = set(session_info.get("tags", []))
                if not any(tag in session_tags for tag in tags):
                    continue

            # Turn count filter
            turn_count = session_info.get("turn_count", 0)
            if min_turns and turn_count < min_turns:
                continue
            if max_turns and turn_count > max_turns:
                continue

            filtered.append(session_info)

        return filtered

    def export_session_text(
        self,
        session_id: str,
        include_metadata: bool = True
    ) -> Optional[str]:
        """
        Export session as readable text

        Args:
            session_id: Session to export
            include_metadata: Whether to include metadata in export

        Returns:
            Formatted text string or None if session not found
        """

        session_data = self.load_session(session_id)
        if not session_data:
            return None

        lines = []

        # Header
        lines.append("=" * 70)
        lines.append(f"SESSION: {session_data.get('session_id', 'Unknown')}")
        lines.append("=" * 70)
        lines.append("")

        # Metadata
        if include_metadata:
            metadata = session_data.get("metadata", {})

            if metadata.get("title"):
                lines.append(f"Title: {metadata['title']}")
            if session_data.get("start_time"):
                lines.append(f"Date: {self._format_datetime(session_data['start_time'])}")
            if metadata.get("turn_count"):
                lines.append(f"Turns: {metadata['turn_count']}")
            if metadata.get("duration_minutes"):
                lines.append(f"Duration: {metadata['duration_minutes']} minutes")

            if metadata.get("summary"):
                lines.append(f"\nSummary: {metadata['summary']}")

            if metadata.get("key_topics"):
                lines.append(f"Topics: {', '.join(metadata['key_topics'])}")

            if metadata.get("emotional_arc"):
                lines.append(f"Emotional Arc: {metadata['emotional_arc']}")

            lines.append("")
            lines.append("-" * 70)
            lines.append("")

        # Conversation
        conversation = session_data.get("conversation", [])

        for idx, turn in enumerate(conversation):
            role = "USER" if turn["role"] == "user" else "KAY"
            timestamp = turn.get("timestamp", "")

            if timestamp:
                time_str = self._format_datetime(timestamp, include_date=False)
                lines.append(f"[{time_str}] {role}:")
            else:
                lines.append(f"{role}:")

            lines.append(turn["content"])
            lines.append("")

        # Footer
        lines.append("-" * 70)
        lines.append(f"End of session {session_id}")
        lines.append("=" * 70)

        return "\n".join(lines)

    def export_session_file(
        self,
        session_id: str,
        output_path: str,
        format: str = "txt"
    ) -> bool:
        """
        Export session to file

        Args:
            session_id: Session to export
            output_path: Path to save export
            format: Export format ("txt", "json", "md")

        Returns:
            True if successful
        """

        if format == "txt":
            content = self.export_session_text(session_id, include_metadata=True)
            if not content:
                return False

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True

        elif format == "json":
            session_data = self.load_session(session_id)
            if not session_data:
                return False

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            return True

        elif format == "md":
            content = self._export_markdown(session_id)
            if not content:
                return False

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True

        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_markdown(self, session_id: str) -> Optional[str]:
        """Export session as Markdown"""

        session_data = self.load_session(session_id)
        if not session_data:
            return None

        lines = []
        metadata = session_data.get("metadata", {})

        # Title
        title = metadata.get("title", f"Session {session_id}")
        lines.append(f"# {title}\n")

        # Metadata
        if session_data.get("start_time"):
            lines.append(f"**Date:** {self._format_datetime(session_data['start_time'])}\n")

        if metadata.get("summary"):
            lines.append(f"**Summary:** {metadata['summary']}\n")

        if metadata.get("key_topics"):
            topics = ", ".join([f"`{t}`" for t in metadata['key_topics']])
            lines.append(f"**Topics:** {topics}\n")

        lines.append("---\n")

        # Conversation
        conversation = session_data.get("conversation", [])

        for turn in conversation:
            role = "**User**" if turn["role"] == "user" else "**Kay**"
            lines.append(f"{role}:\n")
            lines.append(f"{turn['content']}\n")

        return "\n".join(lines)

    def add_note_to_session(
        self,
        session_id: str,
        note: str,
        author: str = "User"
    ) -> bool:
        """
        Add a note/annotation to a session

        Args:
            session_id: Session to annotate
            note: Note text
            author: Note author

        Returns:
            True if successful
        """

        session_data = self.load_session(session_id)
        if not session_data:
            return False

        # Add note to metadata
        if "metadata" not in session_data:
            session_data["metadata"] = {}

        if "notes" not in session_data["metadata"]:
            session_data["metadata"]["notes"] = []

        session_data["metadata"]["notes"].append({
            "text": note,
            "author": author,
            "timestamp": datetime.now().isoformat()
        })

        return self.save_session(session_data)

    def add_tags_to_session(
        self,
        session_id: str,
        tags: List[str]
    ) -> bool:
        """
        Add tags to a session

        Args:
            session_id: Session to tag
            tags: List of tag strings

        Returns:
            True if successful
        """

        session_data = self.load_session(session_id)
        if not session_data:
            return False

        if "metadata" not in session_data:
            session_data["metadata"] = {}

        existing_tags = set(session_data["metadata"].get("tags", []))
        new_tags = existing_tags | set(tags)
        session_data["metadata"]["tags"] = list(new_tags)

        return self.save_session(session_data)

    def get_sessions_by_month(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group sessions by month for UI display

        Returns:
            Dict mapping "YYYY-MM" to list of session info dicts
        """

        all_sessions = self.list_sessions()
        by_month = {}

        for session_info in all_sessions:
            try:
                start_time = datetime.fromisoformat(session_info["start_time"])
                month_key = start_time.strftime("%Y-%m")

                if month_key not in by_month:
                    by_month[month_key] = []

                by_month[month_key].append(session_info)
            except (ValueError, KeyError):
                # Put in "Unknown" category
                if "Unknown" not in by_month:
                    by_month["Unknown"] = []
                by_month["Unknown"].append(session_info)

        return by_month

    def _format_datetime(
        self,
        dt_string: str,
        include_date: bool = True
    ) -> str:
        """Format datetime string for display"""

        try:
            dt = datetime.fromisoformat(dt_string)
            if include_date:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            return dt_string

    def backup_session(self, session_id: str) -> bool:
        """Create backup copy of session"""

        file_path = self.session_dir / f"{session_id}.json"
        if not file_path.exists():
            return False

        backup_dir = self.session_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        backup_path = backup_dir / f"{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            shutil.copy2(file_path, backup_path)
            return True
        except Exception as e:
            print(f"Error backing up session {session_id}: {e}")
            return False
