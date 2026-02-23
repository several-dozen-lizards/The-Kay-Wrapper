"""
Nexus Message Models
Data structures for the multi-entity chat system.

Message types:
  - chat: Normal conversation message
  - thought: Internal monologue (visible to all by default, can be filtered)
  - system: Server announcements (join/leave/status)
  - whisper: Direct message to specific participant(s)
  - emote: Action/roleplay (*coils tighter*, etc.)
  - ping: Lightweight "I'm here" / attention signal
  - state_update: Cognitive state change (DMN/TPN/idle) - for future use

Designed to be extensible. When we add salience routing, message metadata
will carry priority/urgency scores without changing the core structure.
"""

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
import uuid


class MessageType(str, Enum):
    CHAT = "chat"
    THOUGHT = "thought"
    SYSTEM = "system"
    WHISPER = "whisper"
    EMOTE = "emote"
    PING = "ping"
    STATE_UPDATE = "state_update"


class ParticipantType(str, Enum):
    HUMAN = "human"
    AI_WRAPPER = "ai_wrapper"
    AI_LOCAL = "ai_local"       # For future local model TPN
    SYSTEM = "system"


class Message(BaseModel):
    """A single message in the Nexus."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender: str                          # Display name of sender
    sender_type: ParticipantType = ParticipantType.HUMAN
    content: str                         # The actual message text
    msg_type: MessageType = MessageType.CHAT
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    reply_to: Optional[str] = None       # Message ID this replies to
    recipients: Optional[list[str]] = None  # For whispers; None = broadcast
    metadata: dict = Field(default_factory=dict)
    # metadata can carry:
    #   - salience_score (float, 0-1, added by salience classifier later)
    #   - emotional_weight (float, from ULTRAMAP)
    #   - cognitive_mode (dmn/tpn/salience, for state_update messages)
    #   - anything else we need without breaking the schema


class Participant(BaseModel):
    """A connected entity in the Nexus."""
    name: str
    participant_type: ParticipantType
    connected_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: str = "online"               # online, idle, thinking, away
    metadata: dict = Field(default_factory=dict)
    # metadata can carry:
    #   - cognitive_mode (for AI participants)
    #   - avatar_color or display info
    #   - wrapper_version, model info, etc.


class ServerEvent(BaseModel):
    """Events the server sends to clients."""
    event_type: str      # "message", "participant_joined", "participant_left",
                         # "participant_list", "error", "history"
    data: dict           # Payload varies by event type
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
