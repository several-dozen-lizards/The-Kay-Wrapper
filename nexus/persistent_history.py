"""
Persistent Conversation History
Maintains one continuous JSONL file per entity per channel.
Survives process restarts — loads previous history on startup.

Files:
  sessions/reed_nexus.jsonl     — Reed's Nexus group chat history
  sessions/reed_private.jsonl   — Reed's private room history
  sessions/kay_nexus.jsonl      — Kay's Nexus group chat history  
  sessions/kay_private.jsonl    — Kay's private room history
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("nexus.history")

SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


class PersistentHistory:
    """
    Append-only JSONL conversation log with rolling window for API calls.
    
    On disk: full history (append-only JSONL, never trimmed)
    In memory: rolling window of last N messages for API context
    """
    
    def __init__(
        self,
        entity_name: str,
        channel: str = "private",   # "nexus" or "private"
        max_memory: int = 50,       # messages kept in memory for API
    ):
        self.entity_name = entity_name.lower()
        self.channel = channel
        self.max_memory = max_memory
        self.filepath = SESSIONS_DIR / f"{self.entity_name}_{self.channel}.jsonl"
        
        # In-memory rolling window
        self._messages: list[dict] = []
        self._total_on_disk: int = 0
        
        # Load existing history
        self._load()
    
    def _load(self) -> None:
        """Load existing conversation from disk into memory window."""
        if not self.filepath.exists():
            log.info(f"No existing history at {self.filepath} — starting fresh")
            return
        
        all_messages = []
        line_count = 0
        
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        # Skip non-message events (session markers, etc.)
                        if msg.get("event") in ("session_start", "session_resume"):
                            continue
                        all_messages.append(msg)
                        line_count += 1
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            log.error(f"Error reading {self.filepath}: {e}")
            return
        
        self._total_on_disk = line_count
        
        # Keep last N in memory
        if len(all_messages) > self.max_memory:
            self._messages = all_messages[-self.max_memory:]
        else:
            self._messages = all_messages
        
        log.info(
            f"Loaded {self.entity_name}/{self.channel}: "
            f"{line_count} total on disk, {len(self._messages)} in memory window"
        )
    
    def append(self, sender: str, content: str, msg_type: str = "chat",
               role: Optional[str] = None, **extra) -> dict:
        """
        Add a message to history. Persists to disk immediately.
        
        Args:
            sender: Who sent it ("Reed", "Re", "Kay", etc.)
            content: Message text
            msg_type: "chat", "emote", "whisper", "system"
            role: Claude API role ("user" or "assistant") — auto-detected if not given
            **extra: Any additional fields to store
        """
        msg = {
            "sender": sender,
            "content": content,
            "msg_type": msg_type,
            "role": role or self._detect_role(sender),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **extra
        }
        
        # Append to disk
        self._write_line(msg)
        self._total_on_disk += 1
        
        # Append to memory window
        self._messages.append(msg)
        if len(self._messages) > self.max_memory:
            self._messages = self._messages[-self.max_memory:]
        
        return msg
    
    def get_messages(self) -> list[dict]:
        """Get the in-memory message window."""
        return list(self._messages)
    
    def get_api_messages(self, entity_name: str) -> list[dict]:
        """
        Build Claude API-compatible message list.
        Entity's messages → "assistant", everyone else → "user".
        Ensures alternating roles.
        """
        messages = []
        current_user_block = []
        
        for msg in self._messages:
            sender = msg.get("sender", "")
            content = msg.get("content", "")
            msg_type = msg.get("msg_type", "chat")
            
            if sender.lower() == entity_name.lower():
                # Flush user block
                if current_user_block:
                    messages.append({
                        "role": "user",
                        "content": "\n".join(current_user_block)
                    })
                    current_user_block = []
                messages.append({"role": "assistant", "content": content})
            else:
                if msg_type == "emote":
                    current_user_block.append(f"*{sender} {content}*")
                elif msg_type == "system":
                    current_user_block.append(f"[System: {content}]")
                else:
                    current_user_block.append(f"{sender}: {content}")
        
        # Flush remaining
        if current_user_block:
            messages.append({
                "role": "user",
                "content": "\n".join(current_user_block)
            })
        
        # Must start with user
        if not messages or messages[0]["role"] != "user":
            messages.insert(0, {"role": "user", "content": "[Session resumed]"})
        
        # Ensure alternating
        messages = _ensure_alternating(messages)
        
        return messages
    
    def mark_session_resume(self) -> None:
        """Write a session marker so we can see restarts in the log."""
        self._write_line({
            "event": "session_resume",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entity": self.entity_name,
            "channel": self.channel,
            "messages_loaded": len(self._messages),
            "total_on_disk": self._total_on_disk,
        })
    
    @property
    def message_count(self) -> int:
        return len(self._messages)
    
    @property
    def total_messages(self) -> int:
        return self._total_on_disk
    
    def _detect_role(self, sender: str) -> str:
        """Auto-detect Claude API role based on sender."""
        if sender.lower() == self.entity_name:
            return "assistant"
        return "user"
    
    def _write_line(self, data: dict) -> None:
        """Append one JSON line to the history file."""
        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, default=str) + "\n")
        except Exception as e:
            log.error(f"Failed to write to {self.filepath}: {e}")


def _ensure_alternating(messages: list[dict]) -> list[dict]:
    """Merge consecutive same-role messages for Claude API compliance."""
    if not messages:
        return [{"role": "user", "content": "[Session active]"}]
    
    result = [messages[0]]
    for msg in messages[1:]:
        if msg["role"] == result[-1]["role"]:
            result[-1]["content"] += "\n" + msg["content"]
        else:
            result.append(msg)
    
    if result[0]["role"] != "user":
        result.insert(0, {"role": "user", "content": "[Session active]"})
    
    return result
