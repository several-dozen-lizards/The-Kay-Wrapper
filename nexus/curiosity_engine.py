"""
Curiosity Engine — Self-directed interest tracking for Nexus entities.

Entities generate curiosities during conversation — threads they want to
explore later, questions that grabbed them, tangents they didn't follow.
These get persisted and fed into autonomous sessions.

Two extraction modes:
1. PASSIVE: After each response, LLM extracts curiosity seeds from the conversation
2. ACTIVE: Entity explicitly flags something with [curiosity: ...] tag in response

Architecture:
  CuriosityExtractor — analyzes conversation to extract seeds
  CuriosityStore — persistent JSON per entity with priority/decay
  Integration with autonomous_processor.TopicQueue for session feeding
"""

import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field, asdict

log = logging.getLogger("nexus.curiosity")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class Curiosity:
    """A thread the entity wants to explore."""
    id: str                          # timestamp-based unique ID
    text: str                        # The curiosity itself
    source: str = "conversation"     # conversation | self_flagged | autonomous | manual
    category: str = "exploration"    # exploration | creative | emotional | technical | philosophical
    context: str = ""                # What triggered it (snippet of conversation)
    entity: str = ""                 # Who generated it
    priority: float = 0.5            # 0-1, decays over time, boosted by revisits
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_touched: str = field(default_factory=lambda: datetime.now().isoformat())
    times_surfaced: int = 0          # How many times shown to entity/user
    explored: bool = False           # Whether an auto session used this
    explored_session_id: str = ""    # Which session explored it
    dismissed: bool = False          # User or entity dismissed it

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "Curiosity":
        # Handle any missing fields gracefully
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)

    def touch(self):
        """Mark as recently relevant — resets decay."""
        self.last_touched = datetime.now().isoformat()
        self.times_surfaced += 1

    def age_hours(self) -> float:
        """Hours since last touched."""
        touched = datetime.fromisoformat(self.last_touched)
        return (datetime.now() - touched).total_seconds() / 3600

    def effective_priority(self, interest_topology=None) -> float:
        """Priority with time decay and optional interest topology boost.

        Curiosities fade if not revisited (72hr half-life).
        Topics matching historically rewarding interests get a boost.
        """
        age = self.age_hours()
        # Half-life of 72 hours (3 days)
        decay = 0.5 ** (age / 72)
        base = self.priority * decay

        # Boost from interest topology — topics entity has been rewarded for
        interest_boost = 0.0
        if interest_topology:
            try:
                interest_boost = interest_topology.get_interest_boost(self.text)
            except Exception:
                pass

        return base + interest_boost


# ---------------------------------------------------------------------------
# Curiosity Store — persistent per-entity
# ---------------------------------------------------------------------------

class CuriosityStore:
    """Persistent curiosity storage for one entity."""

    MAX_CURIOSITIES = 50  # Keep it bounded

    def __init__(self, entity: str, store_dir: str):
        self.entity = entity
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.filepath = self.store_dir / f"{entity.lower()}_curiosities.json"
        self._curiosities: List[Curiosity] = []
        self._load()

    def _load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._curiosities = [Curiosity.from_dict(c) for c in data.get("curiosities", [])]
                log.info(f"[CURIOSITY {self.entity}] Loaded {len(self._curiosities)} curiosities")
            except Exception as e:
                log.warning(f"[CURIOSITY {self.entity}] Failed to load: {e}")
                self._curiosities = []
        else:
            self._curiosities = []

    def _save(self):
        data = {
            "entity": self.entity,
            "updated_at": datetime.now().isoformat(),
            "count": len(self._curiosities),
            "curiosities": [c.to_dict() for c in self._curiosities],
        }
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"[CURIOSITY {self.entity}] Save failed: {e}")

    def add(self, curiosity: Curiosity) -> bool:
        """Add a curiosity. Deduplicates by similarity. Returns True if added."""
        # Skip if too similar to existing
        for existing in self._curiosities:
            if existing.dismissed or existing.explored:
                continue
            if self._similar(curiosity.text, existing.text):
                # Boost existing instead
                existing.touch()
                existing.priority = min(1.0, existing.priority + 0.1)
                self._save()
                log.debug(f"[CURIOSITY {self.entity}] Boosted existing: {existing.text[:60]}")
                return False

        curiosity.entity = self.entity
        curiosity.id = f"{int(time.time())}_{len(self._curiosities)}"
        self._curiosities.append(curiosity)

        # Prune if over limit — drop lowest priority dismissed/explored first, then oldest
        self._prune()
        self._save()
        log.info(f"[CURIOSITY {self.entity}] Added: {curiosity.text[:80]}")
        return True

    def _similar(self, a: str, b: str) -> bool:
        """Quick similarity check — shared significant words."""
        words_a = set(w.lower() for w in a.split() if len(w) > 4)
        words_b = set(w.lower() for w in b.split() if len(w) > 4)
        if not words_a or not words_b:
            return False
        overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
        return overlap > 0.5

    def _prune(self):
        """Keep store bounded."""
        if len(self._curiosities) <= self.MAX_CURIOSITIES:
            return
        # Remove dismissed/explored first
        active = [c for c in self._curiosities if not c.dismissed and not c.explored]
        inactive = [c for c in self._curiosities if c.dismissed or c.explored]
        # Keep all active, trim inactive to fit
        max_inactive = self.MAX_CURIOSITIES - len(active)
        if max_inactive < 0:
            # Too many active — drop lowest effective priority
            active.sort(key=lambda c: c.effective_priority(), reverse=True)
            active = active[:self.MAX_CURIOSITIES]
            inactive = []
        else:
            inactive.sort(key=lambda c: c.effective_priority(), reverse=True)
            inactive = inactive[:max(0, max_inactive)]
        self._curiosities = active + inactive

    def get_active(self, limit: int = 10, interest_topology=None) -> List[Curiosity]:
        """Get top active curiosities sorted by effective priority.

        Args:
            limit: Maximum number of curiosities to return
            interest_topology: Optional InterestTopology for boosting rewarding topics
        """
        active = [c for c in self._curiosities
                  if not c.dismissed and not c.explored]
        active.sort(key=lambda c: c.effective_priority(interest_topology), reverse=True)
        return active[:limit]

    def get_all(self) -> List[Curiosity]:
        """Get all curiosities (for UI display)."""
        return list(self._curiosities)

    def pop_for_session(self, interest_topology=None) -> Optional[Curiosity]:
        """Pop highest-priority unexplored curiosity for an autonomous session."""
        active = self.get_active(1, interest_topology=interest_topology)
        if not active:
            return None
        curiosity = active[0]
        curiosity.explored = True
        curiosity.touch()
        self._save()
        return curiosity

    def dismiss(self, curiosity_id: str) -> bool:
        """Mark a curiosity as dismissed (user doesn't want it explored)."""
        for c in self._curiosities:
            if c.id == curiosity_id:
                c.dismissed = True
                self._save()
                return True
        return False

    def mark_pursued(self, curiosity_id: str, outcome: str = "pursued") -> bool:
        """Mark a curiosity as pursued (entity explored it)."""
        for c in self._curiosities:
            if c.id == curiosity_id:
                c.explored = True
                c.explored_session_id = outcome
                c.touch()
                self._save()
                return True
        return False

    def boost(self, curiosity_id: str, amount: float = 0.15) -> bool:
        """Manually boost a curiosity's priority."""
        for c in self._curiosities:
            if c.id == curiosity_id:
                c.priority = min(1.0, c.priority + amount)
                c.touch()
                self._save()
                return True
        return False

    def mark_explored(self, curiosity_id: str, session_id: str):
        """Mark curiosity as explored by an autonomous session."""
        for c in self._curiosities:
            if c.id == curiosity_id:
                c.explored = True
                c.explored_session_id = session_id
                c.touch()
                self._save()
                return

    def to_list(self, interest_topology=None) -> List[Dict]:
        """Serialize active curiosities for API/UI."""
        return [
            {**c.to_dict(), "effective_priority": round(c.effective_priority(interest_topology), 3)}
            for c in self.get_active(20, interest_topology=interest_topology)
        ]


# ---------------------------------------------------------------------------
# Curiosity Extractor — pulls seeds from conversation
# ---------------------------------------------------------------------------

# Inline tag pattern: [curiosity: some text here]
CURIOSITY_TAG_PATTERN = re.compile(
    r'\[curiosity:\s*(.+?)\]', re.IGNORECASE
)



def extract_self_flagged(response_text: str) -> List[str]:
    """Extract explicitly tagged curiosities from entity response.
    
    Entity can flag curiosities inline:
      [curiosity: What would happen if wrapper memory used graph DB instead?]
    
    These get stripped from the displayed response and routed to the store.
    """
    return CURIOSITY_TAG_PATTERN.findall(response_text)


def strip_curiosity_tags(text: str) -> str:
    """Remove [curiosity: ...] tags from display text."""
    return CURIOSITY_TAG_PATTERN.sub("", text).strip()


class CuriosityExtractor:
    """Extracts curiosity seeds from conversation using LLM analysis.
    
    Runs asynchronously after each response — doesn't block the conversation.
    Uses a cheap/fast model call to identify threads worth exploring.
    """

    # Minimum conversation turns before extraction kicks in
    MIN_TURNS_FOR_EXTRACTION = 3
    # Don't extract more often than every N responses
    COOLDOWN_RESPONSES = 5

    def __init__(self, llm_fn: Optional[Callable] = None):
        """
        Args:
            llm_fn: async fn(messages, entity) -> str — same as autonomous processor
        """
        self.llm_fn = llm_fn
        self._response_count: Dict[str, int] = {}
        self._last_extraction: Dict[str, float] = {}

    def should_extract(self, entity: str) -> bool:
        """Check if we should run extraction (cooldown + minimum turns)."""
        count = self._response_count.get(entity, 0)
        if count < self.MIN_TURNS_FOR_EXTRACTION:
            return False
        last = self._last_extraction.get(entity, 0)
        since_last = self._response_count.get(entity, 0) - last
        return since_last >= self.COOLDOWN_RESPONSES

    def record_response(self, entity: str):
        """Track that entity produced a response."""
        self._response_count[entity] = self._response_count.get(entity, 0) + 1

    async def extract(
        self,
        entity: str,
        recent_messages: List[Dict[str, str]],
        entity_context: str = "",
    ) -> List[Curiosity]:
        """Extract curiosity seeds from recent conversation.
        
        Args:
            entity: Entity name
            recent_messages: Last ~10 messages [{role, content}]
            entity_context: Entity persona context
            
        Returns:
            List of Curiosity objects (may be empty)
        """
        if not self.llm_fn:
            return []

        self._last_extraction[entity] = self._response_count.get(entity, 0)

        # Build extraction prompt
        conversation_text = "\n".join(
            f"{m.get('role', '?')}: {m.get('content', '')[:300]}"
            for m in recent_messages[-10:]
        )

        messages = [
            {"role": "system", "content": EXTRACTION_PROMPT.format(
                entity_name=entity,
                entity_context=entity_context[:500] if entity_context else "",
            )},
            {"role": "user", "content": f"Recent conversation:\n{conversation_text}\n\n"
                "Extract 0-3 curiosity seeds. If nothing stands out, return empty."},
        ]

        try:
            raw = await self.llm_fn(messages, entity)
            if not raw:
                return []
            return self._parse_extraction(raw, entity)
        except Exception as e:
            log.warning(f"[CURIOSITY {entity}] Extraction failed: {e}")
            return []

    def _parse_extraction(self, raw: str, entity: str) -> List[Curiosity]:
        """Parse LLM extraction response into Curiosity objects."""
        curiosities = []

        # Try JSON parse first
        try:
            # Look for JSON array in response
            json_match = re.search(r'\[.*\]', raw, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group())
                for item in items:
                    if isinstance(item, str):
                        curiosities.append(Curiosity(
                            id="", text=item, entity=entity,
                            source="conversation",
                        ))
                    elif isinstance(item, dict):
                        curiosities.append(Curiosity(
                            id="",
                            text=item.get("text", item.get("curiosity", "")),
                            category=item.get("category", "exploration"),
                            context=item.get("context", ""),
                            priority=float(item.get("priority", 0.5)),
                            entity=entity,
                            source="conversation",
                        ))
                return [c for c in curiosities if c.text.strip()]
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: line-based parsing
        for line in raw.strip().split("\n"):
            line = line.strip().lstrip("- •*123456789.)")
            if len(line) > 15 and not line.startswith("#") and not line.startswith("No "):
                curiosities.append(Curiosity(
                    id="", text=line.strip(), entity=entity,
                    source="conversation",
                ))

        return curiosities[:3]  # Max 3 per extraction


EXTRACTION_PROMPT = """You are analyzing a conversation for {entity_name} to identify curiosity seeds — 
threads worth exploring in a future autonomous thinking session.

{entity_context}

Look for:
- Questions that were raised but not fully explored
- Tangents that got dropped but seemed interesting
- Technical ideas that deserve deeper investigation
- Emotional threads that could benefit from processing
- Creative sparks that could become something
- Patterns the entity noticed but didn't pursue

Return a JSON array of 0-3 curiosity objects. Return [] if nothing stands out.
Format: [{{"text": "the curiosity", "category": "exploration|creative|emotional|technical|philosophical", "priority": 0.3-0.9, "context": "brief note on what triggered it"}}]

Be selective. Not every conversation produces curiosities. A good curiosity is specific enough 
to explore but open enough to go somewhere interesting."""


# ---------------------------------------------------------------------------
# Manager — ties extraction + storage together
# ---------------------------------------------------------------------------

class CuriosityManager:
    """Top-level manager connecting extraction to storage.
    
    One per Nexus server instance. Manages stores for all entities.
    """

    STORE_DIR = "sessions/curiosities"

    def __init__(self, llm_fn: Optional[Callable] = None, store_dir: str = None):
        self.store_dir = store_dir or self.STORE_DIR
        self.extractor = CuriosityExtractor(llm_fn=llm_fn)
        self._stores: Dict[str, CuriosityStore] = {}

    def get_store(self, entity: str) -> CuriosityStore:
        """Get or create store for entity."""
        key = entity.capitalize()
        if key not in self._stores:
            self._stores[key] = CuriosityStore(key, self.store_dir)
        return self._stores[key]

    def record_response(self, entity: str):
        """Track that entity responded (for extraction cooldown)."""
        self.extractor.record_response(entity.capitalize())

    async def maybe_extract(
        self,
        entity: str,
        recent_messages: List[Dict[str, str]],
        entity_context: str = "",
    ) -> List[Curiosity]:
        """Run extraction if cooldown allows. Returns any new curiosities."""
        entity = entity.capitalize()
        if not self.extractor.should_extract(entity):
            return []

        curiosities = await self.extractor.extract(entity, recent_messages, entity_context)
        store = self.get_store(entity)
        added = []
        for c in curiosities:
            if store.add(c):
                added.append(c)

        if added:
            log.info(f"[CURIOSITY {entity}] Extracted {len(added)} new curiosities")
        return added

    def add_self_flagged(self, entity: str, texts: List[str], context: str = "") -> List[Curiosity]:
        """Add curiosities explicitly flagged by entity in response."""
        entity = entity.capitalize()
        store = self.get_store(entity)
        added = []
        for text in texts:
            c = Curiosity(
                id="", text=text, entity=entity,
                source="self_flagged", priority=0.7,  # Self-flagged = higher priority
                context=context[:200],
            )
            if store.add(c):
                added.append(c)
        return added

    def pop_for_session(self, entity: str, interest_topology=None) -> Optional[str]:
        """Pop top curiosity for autonomous session. Returns topic string or None."""
        store = self.get_store(entity)
        curiosity = store.pop_for_session(interest_topology=interest_topology)
        if curiosity:
            return curiosity.text
        return None

    def get_active(self, entity: str, limit: int = 10, interest_topology=None) -> List[Dict]:
        """Get active curiosities for API/UI."""
        store = self.get_store(entity)
        return store.to_list(interest_topology=interest_topology)[:limit]

    def dismiss(self, entity: str, curiosity_id: str) -> bool:
        return self.get_store(entity.capitalize()).dismiss(curiosity_id)

    def boost(self, entity: str, curiosity_id: str) -> bool:
        return self.get_store(entity.capitalize()).boost(curiosity_id)

    def mark_pursued(self, entity: str, curiosity_id: str, outcome: str = "pursued") -> bool:
        return self.get_store(entity.capitalize()).mark_pursued(curiosity_id, outcome)
