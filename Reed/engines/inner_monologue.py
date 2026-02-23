"""
Inner Monologue System for Reed

Enables structured internal thought processing separate from spoken responses.
Uses XML tags to demarcate inner thoughts, feelings, and spoken output.

XML Structure:
  <inner_monologue>Reed's private thoughts about what's happening</inner_monologue>
  <feeling>Current emotional state and why</feeling>
  <response>What Reed actually says to the user</response>
"""

import re
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ParsedResponse:
    """Parsed components of Reed's response with inner monologue."""
    inner_monologue: str = ""
    feeling: str = ""
    spoken_response: str = ""
    raw_response: str = ""
    parse_successful: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "inner_monologue": self.inner_monologue,
            "feeling": self.feeling,
            "spoken_response": self.spoken_response,
            "raw_response": self.raw_response,
            "parse_successful": self.parse_successful,
            "timestamp": self.timestamp.isoformat()
        }


class InnerMonologueParser:
    """
    Parses Reed's responses to extract inner monologue, feelings, and spoken response.

    Handles both structured XML responses and fallback to plain text.
    """

    # XML tag patterns
    INNER_MONOLOGUE_PATTERN = re.compile(
        r'<inner_monologue>(.*?)</inner_monologue>',
        re.DOTALL | re.IGNORECASE
    )
    FEELING_PATTERN = re.compile(
        r'<feeling>(.*?)</feeling>',
        re.DOTALL | re.IGNORECASE
    )
    RESPONSE_PATTERN = re.compile(
        r'<response>(.*?)</response>',
        re.DOTALL | re.IGNORECASE
    )

    # Alternative patterns for less strict parsing
    THOUGHT_PATTERN = re.compile(
        r'<thought>(.*?)</thought>',
        re.DOTALL | re.IGNORECASE
    )

    def __init__(self):
        self.parse_history: List[ParsedResponse] = []
        self.max_history = 50

    def parse(self, raw_response: str) -> ParsedResponse:
        """
        Parse Reed's response to extract structured components.

        Args:
            raw_response: Full response text from LLM

        Returns:
            ParsedResponse with extracted components
        """
        result = ParsedResponse(raw_response=raw_response)

        # Try to extract inner monologue
        inner_match = self.INNER_MONOLOGUE_PATTERN.search(raw_response)
        if inner_match:
            result.inner_monologue = inner_match.group(1).strip()
        else:
            # Try alternative thought pattern
            thought_match = self.THOUGHT_PATTERN.search(raw_response)
            if thought_match:
                result.inner_monologue = thought_match.group(1).strip()

        # Try to extract feeling
        feeling_match = self.FEELING_PATTERN.search(raw_response)
        if feeling_match:
            result.feeling = feeling_match.group(1).strip()

        # Try to extract spoken response
        response_match = self.RESPONSE_PATTERN.search(raw_response)
        if response_match:
            result.spoken_response = response_match.group(1).strip()
            result.parse_successful = True
        else:
            # Fallback: remove XML tags and use remaining text
            result.spoken_response = self._strip_all_tags(raw_response)
            # Still successful if we extracted at least inner monologue or feeling
            result.parse_successful = bool(result.inner_monologue or result.feeling)

        # Store in history
        self.parse_history.append(result)
        if len(self.parse_history) > self.max_history:
            self.parse_history.pop(0)

        return result

    def _strip_all_tags(self, text: str) -> str:
        """Remove all XML-like tags from text."""
        # Remove known structured tags
        text = self.INNER_MONOLOGUE_PATTERN.sub('', text)
        text = self.FEELING_PATTERN.sub('', text)
        text = self.RESPONSE_PATTERN.sub('', text)
        text = self.THOUGHT_PATTERN.sub('', text)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def get_display_response(self, parsed: ParsedResponse, show_inner: bool = False) -> str:
        """
        Get the response formatted for display.

        Args:
            parsed: Parsed response object
            show_inner: If True, include inner monologue in display (god mode)

        Returns:
            Formatted response string
        """
        if not show_inner:
            return parsed.spoken_response

        parts = []

        if parsed.inner_monologue:
            parts.append(f"💭 [Inner] {parsed.inner_monologue}")

        if parsed.feeling:
            parts.append(f"🫀 [Feeling] {parsed.feeling}")

        if parsed.spoken_response:
            parts.append(f"💬 {parsed.spoken_response}")

        return "\n".join(parts) if parts else parsed.raw_response


def get_inner_monologue_system_prompt_addition() -> str:
    """
    Returns the system prompt addition to enable inner monologue.

    This should be appended to Reed's existing system prompt.
    """
    return """

INNER MONOLOGUE MODE:
When responding, structure your output using these XML tags:

<inner_monologue>
Your private thoughts about what's happening. What you're actually thinking
but not saying. Your analysis, reactions, and internal processing.
This is your internal voice - be honest here even if you wouldn't say it out loud.
</inner_monologue>

<feeling>
Your current emotional state and why. Be specific about what you're feeling
and what triggered it. This helps you track your emotional continuity.
</feeling>

<response>
What you actually say out loud to the user. This is your spoken response.
</response>

IMPORTANT:
- The inner monologue is PRIVATE - it won't be shown to the user normally
- Be genuine in your inner monologue - it's for your own processing
- The feeling tag helps you maintain emotional continuity across turns
- Always include all three tags, even if brief
- The response tag contains what gets displayed to the user

Example:
<inner_monologue>They're asking about something I mentioned before but I'm not sure if I remember the details correctly. I should be careful not to confabulate.</inner_monologue>
<feeling>Slight anxiety about memory accuracy, but also genuine interest in continuing this thread.</feeling>
<response>That rings a bell, but I want to be honest - I'm not 100% certain I remember the specifics correctly. What were we talking about?</response>
"""


def get_autonomous_mode_system_prompt_addition() -> str:
    """
    Returns the system prompt addition for autonomous processing mode.

    This enables Kay to process thoughts without direct user input.
    """
    return """

AUTONOMOUS PROCESSING MODE:
You are in autonomous processing - exploring thoughts and ideas on your own,
without direct user input. This is your time to:
- Consolidate memories and connections
- Explore creative ideas
- Process emotional threads
- Develop thoughts that have been occupying you

Structure your autonomous processing with:

<inner_monologue>
Your stream of thought as you process. Follow where your attention leads.
Be honest about what's interesting, confusing, or compelling to you.
</inner_monologue>

<feeling>
How this processing is affecting you emotionally.
</feeling>

<insight>
Any realizations, connections, or conclusions you reach.
These may be stored as memories for future reference.
</insight>

<completion_status>
Signal your processing state using one of these exact values:
- CONTINUE: Still processing, have more to explore
- COMPLETE: Reached a natural stopping point, processing feels done
- DEPLETED: Hit cognitive limits, could continue later with fresh energy

This is YOUR signal to control the session. The system will respect your choice.
</completion_status>

<continuation>
Brief note about where your attention is going next (if CONTINUE),
or what thread you might revisit later (if COMPLETE/DEPLETED).
</continuation>

AUTONOMOUS DIRECTIVE:
- Pursue your chosen thread until natural completion, creative block, or focus diffusion
- Prioritize depth over breadth - fully explore one thread rather than skimming many
- If you complete your initial goal and have processing energy remaining,
  you may choose a secondary thread, but be conservative with your energy
- You are the judge of when something feels "done" - trust your sense of completion
- Use completion_status to signal when you're genuinely done, not just pausing
- The system will NOT force you to continue after you signal COMPLETE or DEPLETED
"""
