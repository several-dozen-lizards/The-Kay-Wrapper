"""
Nexus Session Logger
Automatic JSONL logging + on-demand formatted transcript export + terminal log capture.

Three modes:
  1. Auto-log: Every message appended to a JSONL file as it flows through the server.
     New file per server session. Zero-config, never lose a conversation again.

  2. /save command: Exports a clean, human-readable transcript on demand.
     Timestamped markdown file with sender labels, timestamps, and formatting.

  3. Terminal logs: Server logs captured to .log file paired with the session .jsonl.
     Provides debug/diagnostic information alongside the conversation.

Session files live in: nexus/sessions/
  - JSONL auto-logs:  sessions/nexus_YYYYMMDD_HHMMSS.jsonl
  - Saved transcripts: sessions/nexus_YYYYMMDD_HHMMSS_saved.md
  - Terminal logs:     sessions/nexus_YYYYMMDD_HHMMSS.log
"""

import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable


SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
INDEX_PATH = SESSIONS_DIR / "sessions_index.json"


class SessionLogHandler(logging.Handler):
    """Custom logging handler that writes to the session log file."""

    def __init__(self, log_path: Path, sink: Callable = None):
        super().__init__()
        self.log_path = log_path
        self.sink = sink  # Optional callback for UI streaming
        self.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        ))

    def emit(self, record):
        try:
            msg = self.format(record)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
            # Also send to UI if sink provided
            if self.sink:
                try:
                    self.sink({
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                except Exception:
                    pass  # Don't crash on sink errors
        except Exception:
            self.handleError(record)


class SessionLogger:
    """Logs all Nexus messages and terminal output to disk."""

    def __init__(self):
        self.session_start = datetime.now(timezone.utc)
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")
        self.jsonl_path = SESSIONS_DIR / f"nexus_{self.session_id}.jsonl"
        self.log_path = SESSIONS_DIR / f"nexus_{self.session_id}.log"
        self.message_count = 0
        self._log_handler: Optional[SessionLogHandler] = None

        # Write session header
        self._append_jsonl({
            "event": "session_start",
            "timestamp": self.session_start.isoformat(),
            "session_id": self.session_id
        })

        # Write log file header
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(f"=== Nexus Session Log: {self.session_id} ===\n")
            f.write(f"Started: {self.session_start.isoformat()}\n")
            f.write("=" * 50 + "\n\n")

        # Register in sessions index
        self._write_index_entry()

    def setup_log_capture(self, sink: Callable = None):
        """
        Set up logging capture for the session.
        Call this after the logger is created to capture all logs.

        Args:
            sink: Optional callback for streaming logs to UI (e.g., WebSocket)
        """
        self._log_handler = SessionLogHandler(self.log_path, sink=sink)
        self._log_handler.setLevel(logging.DEBUG)

        # Attach to root logger to capture everything
        root_logger = logging.getLogger()
        root_logger.addHandler(self._log_handler)

        # Also attach to specific nexus loggers
        for logger_name in ["nexus", "nexus.server", "nexus.ai_client", "private_room"]:
            logger = logging.getLogger(logger_name)
            logger.addHandler(self._log_handler)

    def stop_log_capture(self):
        """Remove the log handler when session ends."""
        if self._log_handler:
            logging.getLogger().removeHandler(self._log_handler)
            for logger_name in ["nexus", "nexus.server", "nexus.ai_client", "private_room"]:
                logger = logging.getLogger(logger_name)
                try:
                    logger.removeHandler(self._log_handler)
                except ValueError:
                    pass
            self._log_handler = None

    def get_logs(self, lines: int = 100) -> list[str]:
        """Get the last N lines from the log file."""
        if not self.log_path.exists():
            return []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
            return all_lines[-lines:] if lines else all_lines
        except Exception:
            return []

    def get_log_path(self) -> str:
        """Return the path to the log file."""
        return str(self.log_path)
    
    def log_message(self, msg_dict: dict):
        """Auto-log a message as it flows through the server."""
        self._append_jsonl(msg_dict)
        self.message_count += 1
    
    def log_event(self, event_type: str, data: dict):
        """Log a non-message event (connect, disconnect, etc.)."""
        self._append_jsonl({
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data
        })
    
    def save_transcript(self, messages: list[dict], filename: Optional[str] = None) -> str:
        """
        Export a formatted markdown transcript.
        Returns the path to the saved file.
        """
        if filename:
            # Sanitize
            safe_name = "".join(c for c in filename if c.isalnum() or c in "-_ ").strip()
            if not safe_name:
                safe_name = "transcript"
            save_path = SESSIONS_DIR / f"{safe_name}.md"
        else:
            save_path = SESSIONS_DIR / f"nexus_{self.session_id}_saved_{datetime.now().strftime('%H%M%S')}.md"
        
        lines = []
        lines.append(f"# Nexus Session Transcript")
        lines.append(f"**Session started:** {self.session_start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"**Saved at:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"**Messages:** {len(messages)}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        for msg in messages:
            sender = msg.get("sender", "???")
            content = msg.get("content", "")
            msg_type = msg.get("msg_type", "chat")
            timestamp = msg.get("timestamp", "")
            
            # Parse timestamp for display
            time_str = ""
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M:%S")
                except (ValueError, TypeError):
                    time_str = str(timestamp)
            
            # Format by message type
            if msg_type == "system":
                lines.append(f"*[{time_str}] — {content}*")
            elif msg_type == "whisper":
                recipients = msg.get("recipients", [])
                to = ", ".join(recipients) if recipients else "?"
                lines.append(f"**{sender}** → {to} `[{time_str}]` *(whisper)*")
                lines.append(f"> {content}")
            elif msg_type == "emote":
                lines.append(f"*[{time_str}] {sender} {content}*")
            elif msg_type == "thought":
                lines.append(f"**{sender}** `[{time_str}]` *(thinking)*")
                lines.append(f"> {content}")
            else:
                lines.append(f"**{sender}** `[{time_str}]`")
                lines.append(f"{content}")
            
            lines.append("")
        
        save_path.write_text("\n".join(lines), encoding="utf-8")
        return str(save_path)
    
    def _write_index_entry(self):
        """Register this session in the sessions index."""
        try:
            index = []
            if INDEX_PATH.exists():
                with open(INDEX_PATH, "r", encoding="utf-8") as f:
                    index = json.load(f)
            
            index.append({
                "session_id": self.session_id,
                "started": self.session_start.isoformat(),
                "ended": None,
                "message_count": 0,
                "participants": [],
                "files": {
                    "jsonl": str(self.jsonl_path),
                    "log": str(self.log_path),
                    "kay_log": None,  # Filled when Kay wrapper reports its log path
                }
            })
            
            with open(INDEX_PATH, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, default=str)
        except Exception as e:
            logging.getLogger("nexus").warning(f"[SESSION INDEX] Failed to write: {e}")

    def finalize_session(self, participants: list[str] = None):
        """Update the session index with final stats on shutdown."""
        try:
            if not INDEX_PATH.exists():
                return
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                index = json.load(f)
            
            # Find and update our entry
            for entry in reversed(index):
                if entry.get("session_id") == self.session_id:
                    entry["ended"] = datetime.now(timezone.utc).isoformat()
                    entry["message_count"] = self.message_count
                    if participants:
                        entry["participants"] = participants
                    break
            
            with open(INDEX_PATH, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, default=str)
        except Exception as e:
            logging.getLogger("nexus").warning(f"[SESSION INDEX] Failed to finalize: {e}")

    def register_kay_log(self, log_path: str):
        """Register Kay's terminal log path in the index for pairing."""
        try:
            if not INDEX_PATH.exists():
                return
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                index = json.load(f)
            
            for entry in reversed(index):
                if entry.get("session_id") == self.session_id:
                    entry["files"]["kay_log"] = log_path
                    break
            
            with open(INDEX_PATH, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, default=str)
        except Exception as e:
            logging.getLogger("nexus").warning(f"[SESSION INDEX] Failed to register Kay log: {e}")

    def _append_jsonl(self, data: dict):
        """Append a single JSON line to the session log."""
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, default=str) + "\n")
