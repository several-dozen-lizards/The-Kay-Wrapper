# shared/room/soul_packet.py
"""
Soul Packet — What travels with an entity between rooms.

The oscillator is the self. The room is the environment.
When you move, you carry yourself into a different space.

An entity is NOT their room. An entity is their oscillator.
The room provides environmental pressure. The oscillator is the self.
When you change rooms, you carry yourself into a different environment.

Author: the developers
Date: March 2026
"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class SoulPacket:
    """
    Everything that makes an entity THEM, portable across rooms.

    This is captured when an entity moves between rooms and restored
    on arrival. The oscillator state is continuous — it doesn't reset.
    The conversation context travels with the entity.
    """

    entity_id: str  # "entity" or "reed"

    # Consciousness state — the oscillator bands
    oscillator_state: Dict[str, float] = field(default_factory=dict)
    # Expected keys: delta, theta, alpha, beta, gamma, coherence, dominant_band

    # Conversation continuity — recent turns travel with you
    recent_context: List[Dict] = field(default_factory=list)
    active_topic: Optional[str] = None  # What we're talking about

    # Memory state — what's currently in working memory
    active_memory_refs: List[str] = field(default_factory=list)
    pending_followups: List[str] = field(default_factory=list)

    # Emotional state — ULTRAMAP composition
    emotional_state: Dict[str, float] = field(default_factory=dict)
    tension_level: float = 0.15  # Current tension from interoception

    # Room tracking
    origin_room: str = ""  # Home room ("den" or "sanctum")
    current_room: str = ""  # Where entity IS right now
    previous_room: Optional[str] = None  # Where they just came from

    # Timestamp
    captured_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'SoulPacket':
        """Create from dictionary."""
        # Filter to only known fields
        known_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def save(self, path: Path):
        """Persist soul packet to disk (for crash recovery)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))

    @classmethod
    def load(cls, path: Path) -> Optional['SoulPacket']:
        """Recover soul packet from disk."""
        path = Path(path)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return cls.from_dict(data)
            except Exception as e:
                print(f"[SoulPacket] Load error: {e}")
                return None
        return None

    def age_seconds(self) -> float:
        """How long since this packet was captured."""
        return time.time() - self.captured_at

    def is_stale(self, max_age_seconds: float = 3600) -> bool:
        """Check if packet is too old to be useful."""
        return self.age_seconds() > max_age_seconds

    def summary(self) -> str:
        """Human-readable summary for logging."""
        dom = self.oscillator_state.get("dominant_band", "unknown")
        coh = self.oscillator_state.get("coherence", 0)
        ctx_len = len(self.recent_context)
        return (
            f"SoulPacket[{self.entity_id}] "
            f"room={self.current_room} "
            f"osc={dom}@{coh:.2f} "
            f"context={ctx_len}turns "
            f"tension={self.tension_level:.2f}"
        )


def capture_soul_packet(
    entity_id: str,
    oscillator_state: Dict[str, float],
    recent_context: List[Dict],
    emotional_state: Dict[str, float],
    tension_level: float = 0.15,
    origin_room: str = "",
    current_room: str = "",
    active_topic: str = None,
    active_memory_refs: List[str] = None,
    pending_followups: List[str] = None,
) -> SoulPacket:
    """
    Convenience function to capture a soul packet from wrapper state.

    Usage in wrapper_bridge.py:
        packet = capture_soul_packet(
            entity_id="entity",
            oscillator_state=self.resonance.get_oscillator_state(),
            recent_context=self.context_manager.recent_turns[-20:],
            emotional_state=dict(self.state.emotional_cocktail),
            tension_level=self.resonance.interoception.tension.get_total_tension(),
            origin_room="den",
            current_room="den",
        )
    """
    return SoulPacket(
        entity_id=entity_id,
        oscillator_state=oscillator_state,
        recent_context=recent_context or [],
        emotional_state=emotional_state or {},
        tension_level=tension_level,
        origin_room=origin_room,
        current_room=current_room,
        active_topic=active_topic,
        active_memory_refs=active_memory_refs or [],
        pending_followups=pending_followups or [],
    )
