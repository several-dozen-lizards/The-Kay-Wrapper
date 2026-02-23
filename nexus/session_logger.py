"""
Nexus Session Logger
Automatic JSONL logging + on-demand formatted transcript export.

Two modes:
  1. Auto-log: Every message appended to a JSONL file as it flows through the server.
     New file per server session. Zero-config, never lose a conversation again.
  
  2. /save command: Exports a clean, human-readable transcript on demand.
     Timestamped markdown file with sender labels, timestamps, and formatting.

Session files live in: nexus/sessions/
  - JSONL auto-logs:  sessions/nexus_YYYYMMDD_HHMMSS.jsonl
  - Saved transcripts: sessions/nexus_YYYYMMDD_HHMMSS_saved.md
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


class SessionLogger:
    """Logs all Nexus messages to disk."""

    def __init__(self):
        self.session_start = datetime.now(timezone.utc)
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")
        self.jsonl_path = SESSIONS_DIR / f"nexus_{self.session_id}.jsonl"
        self.message_count = 0
        
        # Write session header
        self._append_jsonl({
            "event": "session_start",
            "timestamp": self.session_start.isoformat(),
            "session_id": self.session_id
        })
    
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
    
    def _append_jsonl(self, data: dict):
        """Append a single JSON line to the session log."""
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, default=str) + "\n")
