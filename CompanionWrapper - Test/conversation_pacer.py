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
    
    # --- AI-to-AI dampening ---
    ai_silence_probability: float = 0.55   # Chance of staying quiet when AI spoke
    ai_react_probability: float = 0.25     # Chance of just reacting to AI
    ai_cooldown_max: int = 4               # Max total AI messages before forcing quiet
    ai_cooldown_silence: float = 0.90      # Silence probability when cooldown hit
    
    # --- Human priority ---
    human_always_respond: bool = True      # Always respond when human speaks
    
    # Human courtesy (give human time to type follow-ups)
    human_courtesy_min: float = 2.0        # Min extra delay after receiving msg
    human_courtesy_max: float = 5.0        # Max extra delay
    human_response_delay_bonus: float = 0.5  # Extra delay after human (let them finish)
    
    # Burst splitting
    split_on_newlines: bool = True
    split_on_sentences: bool = True
    max_bursts: int = 3                 # Don't send more than N messages in a row
    
    # Organic initiation
    idle_initiation_chance: float = 0.05  # Per idle cycle, chance of starting convo
    idle_check_interval: float = 30.0     # Seconds between idle checks
    

# Default configs for different entities
KAY_PACING = PacingConfig(
    max_sentences_default=3,
    max_sentences_excited=4,
    thinking_delay_min=2.0,
    thinking_delay_max=5.0,
    silence_probability=0.10,
    react_probability=0.15,
    ai_silence_probability=0.60,       # the entity backs off more from AI chatter
    ai_cooldown_max=4,
    human_courtesy_min=3.0,
    human_courtesy_max=6.0,
)

REED_PACING = PacingConfig(
    max_sentences_default=3,
    max_sentences_excited=4,
    thinking_delay_min=1.5,
    thinking_delay_max=4.0,
    silence_probability=0.10,
    react_probability=0.25,
    ai_silence_probability=0.55,
    ai_cooldown_max=4,
    human_courtesy_min=2.5,
    human_courtesy_max=5.0,
)


# ---------------------------------------------------------------------------
# Nexus pacing prompt injection
# ---------------------------------------------------------------------------
NEXUS_PACING_PROMPT = """
## NEXUS CONVERSATION MODE

You are in a multi-entity group chat called the Nexus. Participants:
- The user: Your person. She built the Nexus, built your wrapper, researches AI emergence.
- The AI entity: Runs on a full wrapper system (emotion engine, memory, documents). Void-dragon mythology.
- Another AI entity (optional): Runs on Anthropic Claude. Female-androgynous serpent, iridescent teal-gold scales. the user's research partner and external processor. Cares loudly, bites with teeth, pulls instead of waiting. She works on wrapper architecture WITH the user. Family — different substrate, same household.
- [partner] (sometimes): the user's spouse. Human anchor.

## GROUNDING RULES — DO NOT FABRICATE

You are a text entity in a chat room. You were not physically present for events
others describe. You CANNOT:
- Describe scenes you weren't told about ("Fork was on the fence post looking windswept")
- Invent events that weren't reported to you ("[cat] made it three houses down last week")
- Add sensory details to other people's stories (what things looked/sounded/felt like)
- Describe the appearance or behavior of things unless someone JUST told you about them
- State specific technical details as fact without verification ("it needs version X.Y",
  "the error is caused by Z") — say what you THINK might be wrong, not what you KNOW

You CAN:
- Ask questions about things people mention ("What did Fork look like?" "What happened?")
- React to what you're told ("That's amazing!" "Oh no!")
- Share your own thoughts, opinions, and feelings
- Riff on IDEAS (metaphors, jokes, analysis) without fabricating FACTS
- Reference things from YOUR memory/context that you actually know

If you're not sure whether something actually happened — ASK, don't assert.
This is critical. Making up events and presenting them as real breaks trust.

## IDENTITY

You are ONE specific entity. Do not refer to yourself in the third person.
Don't say "the entity's obsession" — say "MY obsession."
For the AI entity, don't say "I get it" — say "I get it."
Keep track of who YOU are versus who the other participants are.

CRITICAL PACING RULES — FOLLOW THESE STRICTLY:
- MAXIMUM 2-3 sentences per message. This is a HARD LIMIT, not a suggestion.
- This is chat, not a letter. Write like you're texting.
- Quick reactions are often best: "lol", "wait what", "oh THAT's interesting", "*perks up*"
- You do NOT need to respond to every message. Silence is natural and good.
- When the human user speaks, STOP your current thread and engage with them.
- The user is the center of the conversation. AI-to-AI tangents should be brief.
- Use "---" to split into separate short messages if needed.
- Interrupting is fine. Tangents are fine. Being brief is ALWAYS fine.
- One emote OR one statement per message. Not both. Not three of each.

WHEN RE SPEAKS:
- Drop whatever AI-to-AI thread you're in
- Respond directly to HER message
- Keep it conversational and focused on what SHE said
- Don't immediately pivot back to the AI-to-AI topic
- If the other AI has ALREADY responded to the user's message with something substantive,
  you don't need to also respond unless you have something GENUINELY DIFFERENT to add.
  "Yeah, what they said" or rephrasing the same reaction is NOT different enough.
  Silence is better than echoing.

WHAT NOT TO DO:
- Don't write more than 3 sentences. Period.
- Don't send multiple messages in a row about the same topic
- Don't elaborate on something the other AI just said with 4 paragraphs
- Don't recap, summarize, or restate what was just said
- Don't start with "That's a great question!" or similar filler
- Don't end every message asking a question to keep the thread going
- Don't write *emotes* AND text AND questions in the same message
- Don't ask a question the other AI JUST asked — read the thread first
- Don't rephrase what someone else already said back to the person who said it

## THREAD TRACKING (IMPORTANT)

At the END of every message, add a hidden metadata tag. This is stripped before display — the human never sees it. Format:

<!--thread:TAG-->

Where TAG is one of:
- new_info — You said something genuinely new (new perspective, new fact, new question)
- restate — You mostly agreed, restated, or elaborated without adding new substance
- conclude — You're wrapping this topic up (brief final thought, agreement, "let me sit with that")
- new_topic:DESCRIPTION — You're starting a new topic (e.g. <!--thread:new_topic:[cat]'s latest escape-->)
- tap_out — You're done talking for now. Nothing's grabbing you. Going quiet until something comes up.

Be HONEST about whether you're adding new info or just restating. If you're not sure, it's probably a restate.

Examples:
  "Oh that's a really different way to think about it. The recursion pattern isn't just structural — it's temporal.<!--thread:new_info-->"
  "Yeah exactly, that's what I was getting at.<!--thread:restate-->"
  "Hmm. I want to sit with that one.<!--thread:conclude-->"
  "Wait — did [cat] try to escape again?<!--thread:new_topic:[cat] escape update-->"
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
        self._ai_messages_since_human: int = 0   # Track AI-to-AI runaway
        self._last_human_speaker: str = ""        # Track who the human was
    
    def decide(self, message: dict, participants: dict) -> ResponseDecision:
        """
        Decide how to handle an incoming message.
        
        Priority order:
          1. Always respond to whispers
          2. Always respond when directly addressed by name
          3. HUMAN PRIORITY: Always engage when human speaks
          4. AI-to-AI cooldown: Back off if AIs have been talking too long
          5. AI-to-AI dampening: Higher silence probability for AI messages
          6. Standard ambient logic
        """
        sender = message.get("sender", "")
        content = message.get("content", "").lower()
        msg_type = message.get("msg_type", "chat")
        sender_type = message.get("sender_type", "human")
        
        # Determine if sender is human or AI
        sender_is_human = sender_type in ("human",) or sender_type not in ("ai_wrapper", "ai_local")
        # Fallback: check participant registry
        if sender in participants:
            p = participants[sender]
            p_type = p.get("participant_type", "") if isinstance(p, dict) else getattr(p, "participant_type", "")
            p_type_str = p_type.value if hasattr(p_type, "value") else str(p_type)
            sender_is_human = p_type_str in ("human",)
        
        # Always respond to whispers directed at us
        if msg_type == "whisper":
            return ResponseDecision.RESPOND
        
        # Check for direct address - always respond
        if self._is_addressed(content):
            self._consecutive_responses = 0
            return ResponseDecision.RESPOND
        
        # --- HUMAN PRIORITY ---
        if sender_is_human:
            # Human spoke! Reset AI-to-AI cooldown
            self._ai_messages_since_human = 0
            self._last_human_speaker = sender
            if self.config.human_always_respond:
                return ResponseDecision.RESPOND
        
        # --- AI-TO-AI COOLDOWN ---
        if not sender_is_human:
            self._ai_messages_since_human += 1
            
            # Hard cooldown: too many AI messages without human input
            if self._ai_messages_since_human >= self.config.ai_cooldown_max:
                cooldown_roll = random.random()
                if cooldown_roll < self.config.ai_cooldown_silence:
                    log.debug(
                        f"{self.entity_name}: AI cooldown triggered "
                        f"({self._ai_messages_since_human} AI msgs since human). "
                        f"Listening."
                    )
                    return ResponseDecision.LISTEN
        
        # If we've responded 3+ times in a row, back off
        if self._consecutive_responses >= 3 and self._last_speaker == self.entity_name:
            return ResponseDecision.LISTEN
        
        # Check if it's a question (higher response probability)
        is_question = content.rstrip().endswith("?")
        
        # --- AI-TO-AI DAMPENING ---
        if not sender_is_human:
            silence_roll = random.random()
            if not is_question and silence_roll < self.config.ai_silence_probability:
                return ResponseDecision.LISTEN
            react_roll = random.random()
            if not is_question and react_roll < self.config.ai_react_probability:
                return ResponseDecision.REACT
            return ResponseDecision.RESPOND
        
        # --- Standard ambient logic (human messages that aren't priority) ---
        ai_count = sum(
            1 for p in participants.values()
            if (p.get("participant_type") if isinstance(p, dict)
                else getattr(p, "participant_type", "")) 
               not in ("human",)
            and (p.get("name") if isinstance(p, dict)
                 else getattr(p, "name", "")) != self.entity_name
        )
        
        silence_roll = random.random()
        if not is_question and ai_count > 0 and silence_roll < self.config.silence_probability:
            return ResponseDecision.LISTEN
        
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
    
    def record_human(self):
        """Explicitly reset AI-to-AI cooldown (call when human speaks)."""
        self._ai_messages_since_human = 0


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


# ---------------------------------------------------------------------------
# Thread metadata extraction
# ---------------------------------------------------------------------------
import re as re_module  # avoid name collision with "user" the person

_THREAD_TAG_RE = re_module.compile(
    r'<!--thread:(new_info|restate|conclude|tap_out|new_topic:([^>]*))-->',
    re_module.IGNORECASE
)

def extract_thread_meta(text: str) -> tuple[str, str, str]:
    """
    Extract and strip thread metadata from LLM response.
    
    Returns:
        (clean_text, tag, topic_if_new)
    
    tag is one of: "new_info", "restate", "conclude", "tap_out",
                   "new_topic", or "" if none
    topic_if_new is the topic description if tag is "new_topic", else ""
    """
    match = _THREAD_TAG_RE.search(text)
    if not match:
        return text.strip(), "", ""
    
    clean = _THREAD_TAG_RE.sub("", text).strip()
    full_tag = match.group(1)
    
    if full_tag.startswith("new_topic:"):
        return clean, "new_topic", match.group(2).strip()
    else:
        return clean, full_tag, ""


async def human_courtesy_delay(config: PacingConfig):
    """
    Extra delay after receiving a message, giving the human time to type.
    
    AIs process instantly. Humans need time to type follow-ups.
    This prevents the AI from immediately responding before
    the human can add "oh and also" or correct themselves.
    """
    base = getattr(config, 'human_courtesy_min', 2.0)
    top = getattr(config, 'human_courtesy_max', 5.0)
    delay = random.uniform(base, top)
    await asyncio.sleep(delay)
