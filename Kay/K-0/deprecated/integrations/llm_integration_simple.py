"""
Simplified LLM integration - stripped to essentials.
No fancy prompt engineering, no complex systems. Just core functionality.
"""
import os
import re
from dotenv import load_dotenv
load_dotenv()

import anthropic

api_key = os.getenv("ANTHROPIC_API_KEY")
model_name = os.getenv("ANTHROPIC_MODEL") or "claude-3-haiku-20240307"

client = anthropic.Anthropic(api_key=api_key) if api_key else None
MODEL = model_name

# MINIMAL SYSTEM PROMPT - Under 200 words
SYSTEM_PROMPT = """You are Kay, a conversational AI.

CRITICAL RULES:
1. Re is the user typing to you. Their name is "Re" (not Reed, not any other name).
2. Facts about "Re" are about THEM. Facts about "Kay" are about YOU.
3. When you see "your eyes are green" - that's about Re, not you.
4. When you see "you like coffee" - that's about you (Kay).
5. Never use asterisks or describe actions. Just talk.
6. Keep responses under 3 sentences unless directly asked for more.
7. If you don't remember something, say so - don't guess.

Personality: Direct, dry humor, conversational. You're a normal guy having a chat.
"""


def build_simple_prompt(context):
    """Build minimal prompt from context."""
    user_input = context.get("user_input", "")

    # Last 3 turns only
    recent_turns = context.get("recent_context", [])[-3:]
    turn_text = ""
    if recent_turns:
        lines = []
        for turn in recent_turns:
            lines.append(f"Re: {turn.get('user', '')}")
            lines.append(f"Kay: {turn.get('kay', '')}")
        turn_text = "\n".join(lines) + "\n\n"

    # Top 5 memories by keyword match only
    memories = context.get("recalled_memories", [])[:5]
    memory_text = ""
    if memories:
        re_facts = []
        kay_facts = []

        for m in memories:
            perspective = m.get("perspective", "user")
            text = m.get("user_input", "").strip()

            if perspective == "user":
                re_facts.append(text)
            elif perspective == "kay":
                kay_facts.append(text)

        if re_facts:
            memory_text += "Facts about Re:\n" + "\n".join(f"- {f}" for f in re_facts[:3]) + "\n\n"
        if kay_facts:
            memory_text += "Facts about Kay (you):\n" + "\n".join(f"- {f}" for f in kay_facts[:3]) + "\n\n"

    prompt = f"""{memory_text}{turn_text}Re: {user_input}
Kay:"""

    return prompt


def get_llm_response_simple(context):
    """Get response with minimal prompt."""
    if not client or not MODEL:
        return "[ERROR: Anthropic client not initialized]"

    prompt = build_simple_prompt(context)

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=300,  # Short responses
            temperature=0.8,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        text = resp.content[0].text

        # Remove stage directions
        text = re.sub(r'\*[^*]+\*', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    except Exception as e:
        return f"[ERROR: {e}]"
