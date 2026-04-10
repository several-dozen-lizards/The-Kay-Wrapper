"""
Dynamic Context Layer - "What the entity needs to know RIGHT NOW"

Assembles a compact context block (~150 tokens) from:
1. Entity graph: current attributes of key entities
2. High-importance recent memories: what happened lately
3. Temporal urgency: what's happening today/tomorrow/this week
4. Active emotional context: colors the current conversation

This goes into every system prompt, providing a skeleton of the user's life.
Retrieval adds depth when specific topics come up.

The dynamic context is self-maintaining:
- New facts flow in automatically through entity graph updates
- Old facts age out through timestamps and valid_until dates
- No manual curation required
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import re


def build_dynamic_context(entity_graph, memory_layers,
                          current_time: Optional[datetime] = None) -> str:
    """
    Build a compact context block of what the entity needs to know RIGHT NOW.

    Injected into every system prompt. ~100-200 tokens.
    Updated every turn - not static.

    Args:
        entity_graph: The EntityGraph instance with entity attributes
        memory_layers: The MemoryLayerManager with working/long-term memories
        current_time: Optional override for testing (defaults to now)

    Returns:
        Formatted context block string, or empty string if no context
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    parts = []

    # === 1. Key entity current state ===
    # Pull current attributes for entities with high importance
    if entity_graph is not None:
        key_entities = _get_key_entities(entity_graph)

        for entity_name, attrs in key_entities.items():
            facts = []
            for attr_name, attr_data in attrs.items():
                # Only include CURRENT (not expired) attributes
                if _is_current(attr_data, current_time):
                    value = attr_data.get("value", "")
                    if value and len(str(value)) < 100:  # Skip very long values
                        facts.append(f"{attr_name}: {value}")

            if facts:
                # Limit to most important facts per entity
                parts.append(f"[{entity_name}] {'; '.join(facts[:5])}")

    # === 2. Temporally urgent items ===
    # Anything happening today, tomorrow, or this week
    if memory_layers is not None:
        urgent = _get_temporal_urgency(memory_layers, current_time)
        if urgent:
            parts.append(f"[UPCOMING] {'; '.join(urgent)}")

    # === 3. Recent significant events ===
    # High-importance memories from last 24-48 hours
    if memory_layers is not None:
        recent_significant = _get_recent_significant(
            memory_layers, current_time, hours=48, min_importance=0.7
        )
        if recent_significant:
            parts.append(f"[RECENT] {'; '.join(recent_significant)}")

    # === 4. Active emotional context ===
    # If the user was stressed/upset/excited recently, that colors everything
    if memory_layers is not None:
        emotional_context = _get_emotional_context(memory_layers, current_time)
        if emotional_context:
            parts.append(f"[MOOD] {emotional_context}")

    if not parts:
        return ""

    header = "[CURRENT CONTEXT - always available, updates every turn]"
    return header + "\n" + "\n".join(parts)


def _get_key_entities(entity_graph) -> Dict[str, Dict]:
    """
    Get entities that should always be in context.

    Not a fixed list - determined by the entity graph itself:
    - Entities with bedrock facts
    - Entities mentioned frequently
    - Entities with recent activity
    - Entities with high importance attributes

    Returns: {entity_name: {attr: data, ...}, ...}
    """
    key_entities = {}

    if not hasattr(entity_graph, 'entities'):
        return key_entities

    for entity_name, entity_data in entity_graph.entities.items():
        # Skip the canonical entity reference
        if entity_name.startswith('[') and entity_name.endswith(']'):
            # This is a canonical form like [cat] - get the display name
            display_name = entity_name[1:-1].title()
        else:
            display_name = entity_name

        attrs = entity_data.get("attributes", {})
        if not attrs:
            continue

        # Include if: has bedrock facts, or high confidence attributes
        has_bedrock = any(
            a.get("is_bedrock") or a.get("confidence") == "bedrock"
            for a in attrs.values() if isinstance(a, dict)
        )

        # Include if: frequently mentioned (entity has many memory associations)
        mention_count = entity_data.get("mention_count", 0)

        # Include if: has recent activity (confirmed in last 7 days)
        has_recent = any(
            _is_recent(a.get("last_confirmed") if isinstance(a, dict) else None, days=7)
            for a in attrs.values()
        )

        # Include if: high importance entity (from importance score)
        importance = entity_data.get("importance", 0)

        if has_bedrock or mention_count > 10 or has_recent or importance > 0.5:
            key_entities[display_name] = attrs

    # Limit to top 8 entities to keep context compact
    if len(key_entities) > 8:
        # Sort by importance/mention count and take top 8
        sorted_entities = sorted(
            key_entities.items(),
            key=lambda x: (
                -sum(1 for a in x[1].values() if isinstance(a, dict) and a.get("is_bedrock")),
                -len(x[1])
            )
        )
        key_entities = dict(sorted_entities[:8])

    return key_entities


def _is_current(attr_data: dict, current_time: datetime) -> bool:
    """Check if an attribute is currently valid (not expired)."""
    if not isinstance(attr_data, dict):
        return False

    valid_until = attr_data.get("valid_until")
    if valid_until:
        try:
            if isinstance(valid_until, str):
                end = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))
            else:
                end = valid_until
            if end < current_time:
                return False  # Expired
        except (ValueError, TypeError):
            pass
    return True


def _is_recent(timestamp_str, days: int = 7) -> bool:
    """Check if a timestamp is within the last N days."""
    if not timestamp_str:
        return False
    try:
        if isinstance(timestamp_str, str):
            ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        elif isinstance(timestamp_str, (int, float)):
            ts = datetime.fromtimestamp(timestamp_str, tz=timezone.utc)
        else:
            ts = timestamp_str

        # Ensure timezone-aware comparison
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age = now - ts
        return age.total_seconds() < (days * 86400)
    except (ValueError, TypeError):
        return False


def _get_temporal_urgency(memory_layers, current_time: datetime,
                          window_days: int = 3) -> List[str]:
    """
    Find items with temporal urgency - things happening soon.

    Scans recent memories for temporal markers:
    - "tomorrow", "today", "this week", specific days
    - "trial", "hearing", "appointment", "deadline", "due"

    High-importance memory + temporal language = urgent.
    """
    urgent = []
    temporal_markers = {
        "tomorrow", "today", "tonight", "this week", "this weekend",
        "monday", "tuesday", "wednesday", "thursday", "friday",
        "saturday", "sunday", "hearing", "trial", "appointment",
        "deadline", "due", "scheduled", "coming up"
    }

    # Check recent high-importance memories for temporal language
    working = getattr(memory_layers, 'working_memory', []) or []
    long_term = getattr(memory_layers, 'long_term_memory', []) or []
    recent = working + long_term[-100:]

    for mem in recent:
        importance = mem.get("importance_score", mem.get("importance", 0))
        if importance < 0.6:
            continue

        # Get the text content
        text = str(mem.get("fact", mem.get("user_input", ""))).lower()
        if not text:
            continue

        # Check for temporal markers
        has_temporal = any(marker in text for marker in temporal_markers)

        if has_temporal:
            # Compact representation - truncate to key info
            snippet = text[:80].strip()
            if len(text) > 80:
                snippet += "..."
            urgent.append(snippet)

    return urgent[:5]  # Top 5 urgent items


def _get_recent_significant(memory_layers, current_time: datetime,
                            hours: int = 48, min_importance: float = 0.7) -> List[str]:
    """
    Get high-importance memories from the last N hours.

    These are things that JUST happened and are likely to be
    referenced in conversation. Not bedrock facts - recent events.
    """
    cutoff = current_time - timedelta(hours=hours)
    significant = []

    long_term = getattr(memory_layers, 'long_term_memory', []) or []

    for mem in reversed(long_term[-200:]):
        ts = mem.get("added_timestamp") or mem.get("timestamp") or mem.get("created_at")
        if not ts:
            continue

        try:
            if isinstance(ts, (int, float)):
                mem_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            elif isinstance(ts, str):
                mem_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            else:
                mem_time = ts

            # Ensure timezone-aware
            if mem_time.tzinfo is None:
                mem_time = mem_time.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue

        if mem_time < cutoff:
            continue

        importance = mem.get("importance_score", mem.get("importance", 0))
        if importance < min_importance:
            continue

        text = str(mem.get("fact", mem.get("user_input", "")))[:60]
        if text:
            significant.append(text)

    return significant[:5]


def _get_emotional_context(memory_layers, current_time: datetime) -> str:
    """
    If the last few interactions had strong emotions, note them.

    "The user was stressed about X last time we talked" is
    important context that colors the entire next conversation.
    """
    working = getattr(memory_layers, 'working_memory', []) or []

    # Get recent turns with emotional data
    recent_turns = [m for m in working
                    if m.get("memory_type") in ("full_turn", "episodic")][-3:]

    if not recent_turns:
        return ""

    emotions = []
    for turn in recent_turns:
        cocktail = turn.get("emotional_cocktail", {})
        for emo, data in cocktail.items():
            if isinstance(data, dict):
                intensity = data.get("intensity", 0)
            else:
                intensity = data if isinstance(data, (int, float)) else 0

            if isinstance(intensity, (int, float)) and intensity > 0.5:
                emotions.append(f"{emo}:{intensity:.1f}")

    if emotions:
        return f"Recent emotional tone: {', '.join(emotions[:5])}"
    return ""


# === Integration helper ===

def inject_dynamic_context(context: dict) -> str:
    """
    Helper to extract entity_graph and memory_layers from context dict
    and build the dynamic context.

    Usage in build_prompt_from_context:
        dynamic_block = inject_dynamic_context(context)
        if dynamic_block:
            prompt += dynamic_block
    """
    entity_graph = context.get("entity_graph")
    memory_layers = context.get("memory_layers")

    if entity_graph is None and memory_layers is None:
        return ""

    return build_dynamic_context(entity_graph, memory_layers)
