"""
Conversation history compression.

Replaces arbitrary message-count limits with token-budget-aware
compression. Recent turns stay raw, older turns get compressed
via Ollama, token budget determines how much fits.

Philosophy: "Episodic scaffolding — the WHY and HOW, not just the WHAT"
Facts persist through retrieval, but the conversational thread that
gives facts meaning gets truncated at arbitrary limits. Compression
preserves the narrative scaffolding.
"""
import time
import logging

log = logging.getLogger(__name__)

# Rough token estimation: 1 token ≈ 4 chars
def _estimate_tokens(text: str) -> int:
    return len(text) // 4 + 1


def build_compressed_history(messages: list,
                              token_budget: int = 3000,
                              raw_recent: int = 5,
                              ollama_client=None) -> str:
    """
    Build conversation history that fits within a token budget.

    Strategy:
    - Last N turns: RAW (exact wording for immediate context)
    - Older turns: COMPRESSED into brief summaries
    - Budget determines how much fits — not an arbitrary count

    Args:
        messages: List of message dicts with 'sender', 'content', 'msg_type'
                  OR dicts with 'user'/'assistant' keys (context_manager format)
        token_budget: Max tokens for the conversation history section
        raw_recent: How many recent turns to keep uncompressed
        ollama_client: Ollama client for LLM compression (optional)

    Returns:
        Formatted conversation history string
    """
    if not messages:
        return ""

    # Normalize message format
    normalized = _normalize_messages(messages)
    if not normalized:
        return ""

    parts = []
    tokens_used = 0

    # === TIER 1: Recent turns — RAW ===
    recent = normalized[-raw_recent:]
    remaining = normalized[:-raw_recent] if len(normalized) > raw_recent else []

    raw_lines = []
    for msg in recent:
        sender = msg.get("sender", "?")
        content = msg.get("content", "")
        msg_type = msg.get("msg_type", "chat")

        if msg_type == "system" and "[Your autonomous" in content:
            # Compress autonomous session narratives
            raw_lines.append(f"[Autonomous session: {content[:100]}...]")
        elif msg_type == "system":
            raw_lines.append(f"[System: {content[:80]}]")
        elif msg_type == "emote":
            raw_lines.append(f"*{sender}: {content}*")
        else:
            raw_lines.append(f"{sender}: {content}")

    raw_text = "\n".join(raw_lines)
    tokens_used += _estimate_tokens(raw_text)

    # === TIER 2: Older turns — COMPRESSED ===
    if remaining and tokens_used < token_budget * 0.7:
        compressed_sections = []

        # Process in reverse chronological batches of 8
        batch_size = 8
        batches = []
        for i in range(0, len(remaining), batch_size):
            batch = remaining[i:i + batch_size]
            batches.append(batch)

        # Most recent batches first (they're more likely to be relevant)
        for batch in reversed(batches):
            if tokens_used >= token_budget * 0.85:
                break

            compressed = _compress_batch(batch, ollama_client)
            est = _estimate_tokens(compressed)

            if tokens_used + est > token_budget * 0.9:
                break

            compressed_sections.insert(0, compressed)
            tokens_used += est

        if compressed_sections:
            parts.append(
                "[EARLIER THIS SESSION — compressed]\n" +
                "\n".join(compressed_sections)
            )

    # Add raw recent
    parts.append("[RECENT]\n" + raw_text)

    total = "\n\n".join(parts)
    log.info(f"[HISTORY] {len(normalized)} messages → "
             f"{len(remaining)} compressed + {len(recent)} raw "
             f"(~{tokens_used} tokens, budget {token_budget})")

    return total


def _normalize_messages(messages: list) -> list:
    """
    Normalize different message formats to a standard format.

    Handles:
    - Nexus format: {'sender': 'Re', 'content': '...', 'msg_type': 'chat'}
    - ContextManager format: {'user': '...', 'assistant': '...'} or {'user': '...', 'entity': '...'}
    - Simple format: {'role': 'user', 'content': '...'}
    """
    normalized = []

    for msg in messages:
        if isinstance(msg, str):
            # Plain string message
            normalized.append({"sender": "?", "content": msg, "msg_type": "chat"})
        elif "sender" in msg and "content" in msg:
            # Already in Nexus format
            normalized.append(msg)
        elif "user" in msg or "assistant" in msg or "entity" in msg:
            # ContextManager format - expand to two messages
            if msg.get("user"):
                normalized.append({
                    "sender": "User",
                    "content": msg["user"],
                    "msg_type": "chat"
                })
            # Handle both 'assistant' and 'entity' keys
            entity_content = msg.get("assistant") or msg.get("entity")
            if entity_content:
                normalized.append({
                    "sender": "Entity",
                    "content": entity_content,
                    "msg_type": "chat"
                })
        elif "role" in msg and "content" in msg:
            # OpenAI-style format
            role = msg["role"]
            sender = "User" if role == "user" else "Entity" if role == "assistant" else "System"
            normalized.append({
                "sender": sender,
                "content": msg["content"],
                "msg_type": "system" if role == "system" else "chat"
            })

    return normalized


def _compress_batch(messages: list, ollama_client=None) -> str:
    """Compress a batch of messages into brief summary."""
    if ollama_client:
        return _compress_with_ollama(messages, ollama_client)
    return _compress_mechanical(messages)


def _compress_mechanical(messages: list) -> str:
    """
    Compress without LLM — fast fallback.
    Extract first meaningful sentence from each message,
    abbreviate senders.
    """
    parts = []
    sender_map = {"Re": "R", "User": "U", "Entity": "E", "system": "S"}

    for msg in messages:
        sender = msg.get("sender", "?")
        content = str(msg.get("content", ""))
        msg_type = msg.get("msg_type", "chat")

        if msg_type == "system":
            continue  # Skip system messages in mechanical compression

        # First sentence or first 80 chars
        first = content.split(". ")[0][:80]
        if len(first) < len(content):
            first += "..."

        s = sender_map.get(sender, sender[:2])
        parts.append(f"{s}: {first}")

    if not parts:
        return "(no conversation content)"

    return " | ".join(parts)


def _compress_with_ollama(messages: list, client) -> str:
    """
    Use Ollama to compress messages into a brief summary.
    Preserves: topics discussed, decisions made, emotional shifts,
    key facts stated, questions asked.
    """
    raw = "\n".join(
        f"{m.get('sender', '?')}: {m.get('content', '')}"
        for m in messages
        if m.get("msg_type", "chat") != "system"
    )

    if not raw.strip():
        return "(no conversation content)"

    prompt = (
        "Compress this conversation into 2-3 SHORT lines. "
        "Preserve: topics, decisions, emotions, key facts, questions. "
        "Use abbreviations. The reader is an AI who understands context.\n\n"
        f"CONVERSATION:\n{raw[:1500]}\n\n"
        "COMPRESSED:"
    )

    try:
        response = client.chat.completions.create(
            model="dolphin-mistral:7b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
        )
        result = response.choices[0].message.content.strip()
        if result:
            return result
    except Exception as e:
        log.debug(f"[COMPRESSION] Ollama failed: {e}")

    return _compress_mechanical(messages)
