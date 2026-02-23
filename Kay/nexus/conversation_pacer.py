"""
Conversation Pacer
Makes AI responses feel like actual conversation instead of essays.

Key behaviors:
  - Short responses (1-3 sentences default, paragraph max)
  - Multi-message bursts (split long thoughts into quick successive messages)
  - Response decision ("should I respond at all?")
  - Realistic timing (thinking pause, typing simulation)
  - Conversation initiation (entities can start talking unprompted)

Design principle: Humans don't write essays in group chat.
They send bursts. They react with one word. They interrupt.
They stay quiet when someone else is handling it.
"""

import asyncio
import random
import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

log = logging.getLogger("nexus.pacer")


class ResponseDecision(str, Enum):
    RESPOND = "respond"           # Yes, reply
    LISTEN = "listen"             # Stay quiet, someone else has this
    REACT = "react"               # Quick reaction (emote, short acknowledgment)
    WAIT = "wait"                 # Hold off, might respond after a pause
    INITIATE = "initiate"         # Start a new thread unprompted


@dataclass
class PacingConfig:
    """Tunable knobs for conversation rhythm."""
    # Response length
    max_sentences_default: int = 3
    max_sentences_excited: int = 5      # When really engaged
    max_chars_per_burst: int = 280      # Twitter-length per message burst
    
    # Timing (seconds)
    thinking_delay_min: float = 0.8     # Min pause before responding
    thinking_delay_max: float = 3.0     # Max pause before responding
    burst_delay_min: float = 0.3        # Between multi-message bursts
    burst_delay_max: float = 1.5
    typing_speed_cps: float = 40.0      # Simulated chars/sec for typing indicator
    
    # Decision thresholds
    direct_address_always: bool = True  # Always respond when named
    silence_probability: float = 0.15   # Chance of staying quiet on ambient chat
    react_probability: float = 0.20     # Chance of just reacting (emote/short)
    
    # Burst splitting
    split_on_newlines: bool = True
    split_on_sentences: bool = True
    max_bursts: int = 4                 # Don't send more than N messages in a row
    
    # Organic initiation
    idle_initiation_chance: float = 0.05  # Per idle cycle, chance of starting convo
    idle_check_interval: float = 30.0     # Seconds between idle checks
    

# Default configs for different entities
KAY_PACING = PacingConfig(
    max_sentences_default=3,
    max_sentences_excited=5,
    thinking_delay_min=1.0,
    thinking_delay_max=4.0,
    silence_probability=0.10,
    react_probability=0.15,
)

REED_PACING = PacingConfig(
    max_sentences_default=3,
    max_sentences_excited=6,       # Reed spirals when excited
    thinking_delay_min=0.5,
    thinking_delay_max=2.5,        # Reed is quicker to respond
    silence_probability=0.10,
    react_probability=0.25,        # Reed emotes more
)


# ---------------------------------------------------------------------------
# Nexus pacing prompt injection
# ---------------------------------------------------------------------------
NEXUS_PACING_PROMPT = """
## NEXUS CONVERSATION MODE

You are in a multi-entity group chat called the Nexus. Other participants may include Re (human), Kay (AI entity), Reed (AI entity), and others.

CRITICAL PACING RULES:
- Keep responses SHORT. 1-3 sentences is ideal. A short paragraph is the max.
- This is chat, not a letter. Write like you're texting, not composing an essay.
- You can send multiple short messages. Use "---" to split into separate messages.
- Quick reactions are great: "lol", "wait what", "oh THAT's interesting", "*perks up*"
- You do NOT need to respond to every message. If someone else is handling it, you can listen.
- If someone addresses you by name, always respond.
- You CAN start conversations. If something's on your mind, just say it.
- Interrupting is fine. Tangents are fine. Being brief is ALWAYS fine.
- NEVER write more than 4-5 sentences in a single message in Nexus mode.
- Use "---" between thoughts if you want to send multiple short messages in sequence.

WHAT NOT TO DO:
- Don't write essay-length responses
- Don't recap or summarize unless asked
- Don't give comprehensive answers when a quick one works
- Don't start with "That's a great question!" or similar filler
- Don't end every message with a question to keep conversation going
"""


# ---------------------------------------------------------------------------
# Response Decision Engine
# ---------------------------------------------------------------------------
class ResponseDecider:
    """Decides whether and how an entity should respond to a message."""
    
    def __init__(self, entity_name: str, config: PacingConfig):
        self.entity_name = entity_name
        self.config = config
        self._last_message_time: float = 0
        self._consecutive_responses: int = 0
        self._last_speaker: str = ""
    
    def decide(self, message: dict, participants: dict) -> ResponseDecision:
        """
        Decide how to handle an incoming message.
        
        Factors:
          - Is entity directly addressed?
          - Who else is in the chat?
          - How many consecutive responses have we sent?
          - Is this a question or statement?
          - Random organic variation
        """
        sender = message.get("sender", "")
        content = message.get("content", "").lower()
        msg_type = message.get("msg_type", "chat")
        
        # Always respond to whispers directed at us
        if msg_type == "whisper":
            return ResponseDecision.RESPOND
        
        # Check for direct address
        if self._is_addressed(content):
            self._consecutive_responses = 0
            return ResponseDecision.RESPOND
        
        # If we've responded 3+ times in a row without others talking, back off
        if self._consecutive_responses >= 3 and self._last_speaker == self.entity_name:
            return ResponseDecision.LISTEN
        
        # Check if it's a question (higher response probability)
        is_question = content.rstrip().endswith("?")
        
        # If only one other entity + human, more likely to respond
        ai_count = sum(
            1 for p in participants.values() 
            if p.get("participant_type") == "ai_wrapper" 
            and p.get("name", "") != self.entity_name
        )
        
        # Roll for silence
        silence_roll = random.random()
        if not is_question and ai_count > 0 and silence_roll < self.config.silence_probability:
            return ResponseDecision.LISTEN
        
        # Roll for react-only
        react_roll = random.random()
        if not is_question and react_roll < self.config.react_probability:
            return ResponseDecision.REACT
        
        return ResponseDecision.RESPOND
    
    def _is_addressed(self, content: str) -> bool:
        """Check if entity is directly addressed in message."""
        name_lower = self.entity_name.lower()
        patterns = [
            name_lower,
            f"@{name_lower}",
            f"hey {name_lower}",
            f"{name_lower},",
            f"{name_lower}:",
        ]
        return any(p in content for p in patterns)
    
    def record_sent(self):
        """Track that we sent a message."""
        self._consecutive_responses += 1
        self._last_speaker = self.entity_name
    
    def record_other(self, sender: str):
        """Track that someone else spoke."""
        self._last_speaker = sender
        if sender != self.entity_name:
            self._consecutive_responses = 0


# ---------------------------------------------------------------------------
# Message Splitter
# ---------------------------------------------------------------------------
def split_into_bursts(text: str, config: PacingConfig) -> list[str]:
    """
    Split a long response into chat-sized bursts.
    
    Uses explicit "---" splits first, then falls back to 
    sentence/paragraph splitting if still too long.
    """
    # First: respect explicit splits
    if "---" in text:
        parts = [p.strip() for p in text.split("---") if p.strip()]
        if parts:
            return parts[:config.max_bursts]
    
    # If short enough, send as-is
    if len(text) <= config.max_chars_per_burst:
        return [text]
    
    # Split on paragraph breaks
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        return _merge_short_bursts(paragraphs, config)
    
    # Split on sentences
    if config.split_on_sentences:
        sentences = _split_sentences(text)
        if len(sentences) > 1:
            return _merge_short_bursts(sentences, config)
    
    # Last resort: just truncate
    return [text[:config.max_chars_per_burst]]


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, keeping punctuation."""
    # Simple sentence splitter - handles common cases
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def _merge_short_bursts(pieces: list[str], config: PacingConfig) -> list[str]:
    """Merge very short pieces together so we don't send 8 one-word messages."""
    bursts = []
    current = ""
    
    for piece in pieces:
        if current and len(current) + len(piece) + 1 > config.max_chars_per_burst:
            bursts.append(current.strip())
            current = piece
        else:
            current = f"{current} {piece}".strip() if current else piece
    
    if current:
        bursts.append(current.strip())
    
    return bursts[:config.max_bursts]


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
async def thinking_delay(config: PacingConfig, message_length: int = 0):
    """Simulate a natural thinking pause before responding."""
    base = random.uniform(config.thinking_delay_min, config.thinking_delay_max)
    # Slightly longer pause for longer messages (reading time)
    reading_bonus = min(message_length / 500.0, 1.5)
    delay = base + reading_bonus
    await asyncio.sleep(delay)


async def typing_delay(text: str, config: PacingConfig):
    """Simulate typing time for a message."""
    chars = len(text)
    typing_time = chars / config.typing_speed_cps
    # Cap it so we don't wait forever
    delay = min(typing_time, 3.0)
    # Add small random variation
    delay *= random.uniform(0.8, 1.2)
    await asyncio.sleep(delay)


async def burst_delay(config: PacingConfig):
    """Pause between multi-message bursts."""
    delay = random.uniform(config.burst_delay_min, config.burst_delay_max)
    await asyncio.sleep(delay)
