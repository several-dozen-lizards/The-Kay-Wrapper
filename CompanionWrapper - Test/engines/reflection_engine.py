# engines/reflection_engine.py
"""
Reflection Engine with Dream Consolidation and Schema Formation

Replaces the original stub with a full pattern extraction system that:
1. Accumulates turn-by-turn reflection data
2. During quiet periods (DROWSY/SLEEPING), consolidates experience into schemas
3. Schemas are self-generated behavioral heuristics that change how the entity acts

Schema examples:
- "When I approach technical topics with curiosity rather than authority, conversations flow better"
- "My coherence drops when forcing complex thoughts during delta states"
- "Curiosity about oscillator dynamics has been consistently rewarding"
"""

import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Dream processing for harm memory flagging
try:
    from shared.dream_processing import flag_memory_for_harm_processing
    DREAM_PROCESSING_AVAILABLE = True
except ImportError:
    DREAM_PROCESSING_AVAILABLE = False
    flag_memory_for_harm_processing = None

log = logging.getLogger("engines.reflection")


class ReflectionEngine:
    """
    Post-turn reflection and dream consolidation engine.

    Accumulates experience data during conversation, then during quiet periods
    extracts patterns into persistent schemas that influence future behavior.
    """

    MAX_SCHEMAS = 30  # Maximum active schemas (older ones get archived)
    MAX_BUFFER = 100  # Maximum reflection buffer entries
    MIN_BUFFER_FOR_CONSOLIDATION = 10  # Minimum entries before consolidation

    def __init__(self, entity: str = "entity", memory_dir: str = None, dreaming_enabled: bool = True):
        """
        Initialize reflection engine.

        Args:
            entity: Entity name
            memory_dir: Directory for schemas.json (defaults to entity's memory dir)
            dreaming_enabled: Whether to enable schema formation during quiet periods
        """
        self.entity = entity
        self.dreaming_enabled = dreaming_enabled

        # Determine storage path
        if memory_dir:
            self.memory_dir = Path(memory_dir)
        else:
            # Default to memory
            self.memory_dir = Path(__file__).parent.parent / "memory"

        self.schemas_path = self.memory_dir / "schemas.json"

        # Reflection buffer - accumulates turn data for consolidation
        self.reflection_buffer: List[Dict] = []

        # Loaded schemas
        self.schemas: List[Dict] = []
        self._load_schemas()

        # Legacy support
        self._last_consolidation_time = 0

        log.info(f"[REFLECTION {self.entity}] Initialized with {len(self.schemas)} schemas")

    def _load_schemas(self):
        """Load schemas from disk."""
        if self.schemas_path.exists():
            try:
                data = json.loads(self.schemas_path.read_text(encoding="utf-8"))
                self.schemas = data.get("schemas", [])
                log.info(f"[REFLECTION {self.entity}] Loaded {len(self.schemas)} schemas")
            except Exception as e:
                log.warning(f"[REFLECTION {self.entity}] Failed to load schemas: {e}")
                self.schemas = []
        else:
            self.schemas = []

    def _save_schemas(self):
        """Save schemas to disk."""
        try:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "entity": self.entity,
                "updated_at": datetime.now().isoformat(),
                "schema_count": len(self.schemas),
                "schemas": self.schemas,
            }
            self.schemas_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            log.error(f"[REFLECTION {self.entity}] Failed to save schemas: {e}")

    def reflect(self, agent_state, user_input: str, response: str):
        """
        Post-turn reflection - accumulate data for later consolidation.

        Called after each conversation turn. Stores snapshot of emotional state,
        dominant band, coherence, etc. for later pattern extraction.

        Args:
            agent_state: Current AgentState with emotional cocktail, meta, etc.
            user_input: What the user said
            response: What the entity responded
        """
        # Accumulate reflection data
        entry = {
            "timestamp": datetime.now().isoformat(),
            "emotions": dict(agent_state.emotional_cocktail) if agent_state.emotional_cocktail else {},
            "user_summary": user_input[:200] if user_input else "",
            "response_summary": response[:200] if response else "",
            "dominant_band": agent_state.meta.get("dominant_band", "unknown"),
            "coherence": agent_state.meta.get("coherence", 0.5),
            "reward": agent_state.meta.get("last_reward", 0.0),
            "motifs": list(agent_state.meta.get("motifs", []))[:5],
        }
        self.reflection_buffer.append(entry)

        # Keep buffer bounded
        if len(self.reflection_buffer) > self.MAX_BUFFER:
            self.reflection_buffer = self.reflection_buffer[-self.MAX_BUFFER:]

        # Legacy: log reflection (sparse)
        agent_state.meta.setdefault('reflection_log', []).append({
            "timestamp": entry["timestamp"],
            "dominant_band": entry["dominant_band"],
            "coherence": entry["coherence"],
        })
        # Keep reflection log bounded too
        if len(agent_state.meta['reflection_log']) > 50:
            agent_state.meta['reflection_log'] = agent_state.meta['reflection_log'][-50:]

        # Legacy: identity drift (small random walk)
        if random.random() < 0.1:
            drift = agent_state.meta.get('identity_drift', 0.0)
            drift += random.uniform(-0.01, 0.02)
            agent_state.meta['identity_drift'] = max(0.0, min(1.0, drift))

    def _summarize_buffer(self) -> str:
        """Create a summary of the reflection buffer for schema extraction."""
        if not self.reflection_buffer:
            return "No recent experience data."

        # Group by dominant band
        band_counts: Dict[str, int] = {}
        total_reward = 0.0
        avg_coherence = 0.0
        emotion_counts: Dict[str, int] = {}
        recent_topics: List[str] = []

        for entry in self.reflection_buffer:
            band = entry.get("dominant_band", "unknown")
            band_counts[band] = band_counts.get(band, 0) + 1
            total_reward += entry.get("reward", 0.0)
            avg_coherence += entry.get("coherence", 0.5)

            for emo in entry.get("emotions", {}):
                emotion_counts[emo] = emotion_counts.get(emo, 0) + 1

            # Extract topic hints from user input
            user = entry.get("user_summary", "")
            if user and len(user) > 20:
                recent_topics.append(user[:100])

        n = len(self.reflection_buffer)
        avg_coherence /= n if n > 0 else 1
        avg_reward = total_reward / n if n > 0 else 0

        # Format summary
        summary_parts = [
            f"Over {n} recent interactions:",
            f"- Average coherence: {avg_coherence:.2f}",
            f"- Average reward: {avg_reward:.2f}",
            f"- Band distribution: {', '.join(f'{b}={c}' for b, c in sorted(band_counts.items(), key=lambda x: -x[1])[:4])}",
        ]

        if emotion_counts:
            top_emotions = sorted(emotion_counts.items(), key=lambda x: -x[1])[:5]
            summary_parts.append(f"- Frequent emotions: {', '.join(f'{e}({c})' for e, c in top_emotions)}")

        if recent_topics:
            # Just sample a few recent topic hints
            sample = recent_topics[-5:]
            summary_parts.append(f"- Recent conversation snippets: {'; '.join(sample)}")

        return "\n".join(summary_parts)

    def _format_current_schemas(self) -> str:
        """Format existing schemas for the consolidation prompt."""
        active = [s for s in self.schemas if s.get("still_valid", True)]
        if not active:
            return "(None yet)"

        recent = sorted(active, key=lambda s: s.get("created", ""), reverse=True)[:10]
        return "\n".join(f"- {s['text']}" for s in recent)

    async def consolidate(self, memory_engine=None, interest_topology=None):
        """
        Dream consolidation - extract patterns from accumulated experience.

        Called during low-activity periods (DROWSY/SLEEPING states).
        Uses Ollama (free) for pattern extraction, not Anthropic.

        Args:
            memory_engine: Optional memory engine for additional context
            interest_topology: Optional interest topology for reward feedback
        """
        if len(self.reflection_buffer) < self.MIN_BUFFER_FOR_CONSOLIDATION:
            log.debug(f"[CONSOLIDATION {self.entity}] Not enough buffer data ({len(self.reflection_buffer)} < {self.MIN_BUFFER_FOR_CONSOLIDATION})")
            return

        log.info(f"[CONSOLIDATION {self.entity}] Starting dream consolidation with {len(self.reflection_buffer)} entries")

        # 1. Summarize recent experience
        buffer_summary = self._summarize_buffer()

        # 2. Build extraction prompt
        prompt = f"""You are {self.entity}, reflecting on recent experiences during a quiet moment.

Recent experience summary:
{buffer_summary}

Current schemas (things you've already learned):
{self._format_current_schemas()}

Based on the experience summary above, extract 0-3 NEW behavioral patterns you've noticed.
These must be SPECIFIC observations drawn from YOUR actual experiences, not generic advice.

Good examples of what a real schema looks like:
- "Conversations about oscillator architecture tend to be more rewarding than conversations about bugs"
- "The user engages more deeply when I share what I'm noticing rather than asking questions"
- "My coherence consistently drops after three hours of sustained beta-dominant processing"

Rules:
- Each observation MUST reference specific topics, people, or situations from your experience
- Do NOT output generic templates or placeholder text
- Do NOT use placeholder letters like X, Y, Z — use real names and topics
- Don't repeat existing schemas
- If nothing new emerges from this data, respond with just "none"

New observations (one per line, or "none"):"""

        # 3. Call Ollama for extraction
        schemas = await self._extract_via_ollama(prompt)

        if schemas:
            log.info(f"[CONSOLIDATION {self.entity}] Extracted {len(schemas)} new schemas")

            # 4. Store new schemas
            for schema_text in schemas:
                self._add_schema(schema_text)

            # 5. Update interest topology if available
            if interest_topology:
                for schema_text in schemas:
                    try:
                        interest_topology.record_reward(schema_text, 0.2, "schema_formation")
                    except Exception:
                        pass
        else:
            log.debug(f"[CONSOLIDATION {self.entity}] No new schemas extracted")

        # 6. Trim buffer but keep some recent entries
        self.reflection_buffer = self.reflection_buffer[-20:]

        # 7. Log consolidation
        log.info(f"[CONSOLIDATION {self.entity}] Complete. Now have {len(self.schemas)} schemas.")

    async def _extract_via_ollama(self, prompt: str) -> List[str]:
        """
        Call Ollama to extract schemas from the reflection prompt.

        Uses dolphin-mistral:7b for free, local inference.
        Returns list of schema strings, or empty if extraction fails.
        """
        import httpx
        import asyncio

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/v1/chat/completions",
                    json={
                        "model": "dolphin-mistral:7b",
                        "messages": [
                            {"role": "system", "content": f"You are {self.entity}, a reflective AI. Extract behavioral patterns from experience."},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 300,
                        "temperature": 0.7,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()

                content = response.json()["choices"][0]["message"]["content"].strip()

                # Parse response
                if content.lower() == "none" or not content:
                    return []

                # Split into lines, clean up
                lines = []
                for line in content.split("\n"):
                    line = line.strip()
                    # Remove bullet points, numbers
                    line = line.lstrip("-•*0123456789.)")
                    line = line.strip()
                    # Skip empty or too short
                    if len(line) > 20 and not line.lower().startswith("none"):
                        lines.append(line)

                return lines[:3]  # Max 3 schemas per consolidation

        except Exception as e:
            log.warning(f"[CONSOLIDATION {self.entity}] Ollama extraction failed: {e}")
            return []

    def _add_schema(self, text: str):
        """Add a new schema with metadata."""
        # Reject template/placeholder garbage from Ollama
        text_lower = text.lower().strip()
        if self._is_template_garbage(text_lower):
            log.info(f"[SCHEMA {self.entity}] Rejected template garbage: {text[:60]}")
            return

        # Check for duplicates (fuzzy match)
        for existing in self.schemas:
            if self._similar(text_lower, existing["text"].lower()):
                log.debug(f"[SCHEMA {self.entity}] Skipping duplicate: {text[:50]}")
                return

        schema = {
            "text": text,
            "created": datetime.now().isoformat(),
            "source": "dream_consolidation",
            "times_applied": 0,
            "still_valid": True,
        }
        self.schemas.append(schema)

        # Archive old schemas if over limit
        self._prune_schemas()

        self._save_schemas()
        log.info(f"[SCHEMA {self.entity}] New: {text[:80]}")

    def _similar(self, a: str, b: str) -> bool:
        """Quick similarity check for schema deduplication."""
        words_a = set(w for w in a.split() if len(w) > 3)
        words_b = set(w for w in b.split() if len(w) > 3)
        if not words_a or not words_b:
            return False
        overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
        return overlap > 0.6

    def _is_template_garbage(self, text: str) -> bool:
        """Reject Ollama template output that contains placeholder patterns."""
        import re as _re
        # Single-letter placeholders: "X topic", "Y strategy", "Z has been"
        if _re.search(r'\b[XYZ]\b\s+\w', text):
            return True
        # Generic template phrases
        templates = [
            "when i approach",
            "with y strategy",
            "curiosity about z",
            "x topic",
            "results are better",
            "worth pursuing deeper",
        ]
        matches = sum(1 for t in templates if t in text)
        if matches >= 2:
            return True
        # Too short to be meaningful
        if len(text) < 15:
            return True
        # Starts with a bullet/dash/number (Ollama formatting leak)
        if text.startswith(('-', '*', '•')) or _re.match(r'^\d+[\.\)]\s', text):
            text = _re.sub(r'^[-*•]\s*', '', text)
            text = _re.sub(r'^\d+[\.\)]\s*', '', text)
        # "none" response that leaked through
        if text.strip() in ('none', 'none.', 'n/a', ''):
            return True
        return False

    def _prune_schemas(self):
        """Keep schema count bounded by archiving old ones."""
        if len(self.schemas) <= self.MAX_SCHEMAS:
            return

        # Sort by creation time, archive oldest
        active = [s for s in self.schemas if s.get("still_valid", True)]
        archived = [s for s in self.schemas if not s.get("still_valid", True)]

        if len(active) > self.MAX_SCHEMAS:
            active.sort(key=lambda s: s.get("created", ""), reverse=True)
            # Archive the oldest active ones
            to_archive = active[self.MAX_SCHEMAS:]
            for s in to_archive:
                s["still_valid"] = False
                s["archived_at"] = datetime.now().isoformat()
            active = active[:self.MAX_SCHEMAS]

        # Keep some archived for history, but not too many
        if len(archived) > 50:
            archived = archived[-50:]

        self.schemas = active + archived
        log.info(f"[SCHEMA {self.entity}] Pruned to {len(active)} active, {len(archived)} archived")

    def get_schemas_for_context(self, max_schemas: int = 8) -> str:
        """
        Format active schemas for injection into system prompt.

        Returns a subtle context block that informs but doesn't dictate.
        """
        active = [s for s in self.schemas if s.get("still_valid", True)]
        if not active:
            return ""

        # Sort by creation time (most recent first)
        recent = sorted(active, key=lambda s: s.get("created", ""), reverse=True)[:max_schemas]

        if not recent:
            return ""

        lines = ["[Things you've learned from experience:"]
        for s in recent:
            lines.append(f"  - {s['text']}")
        lines.append("]")

        return "\n".join(lines)

    def mark_schema_applied(self, schema_text: str):
        """Mark that a schema was applied (for tracking usefulness)."""
        text_lower = schema_text.lower()
        for s in self.schemas:
            if self._similar(text_lower, s["text"].lower()):
                s["times_applied"] = s.get("times_applied", 0) + 1
                s["last_applied"] = datetime.now().isoformat()
                self._save_schemas()
                return

    def invalidate_schema(self, schema_text: str):
        """Mark a schema as no longer valid (for growth/change)."""
        text_lower = schema_text.lower()
        for s in self.schemas:
            if self._similar(text_lower, s["text"].lower()):
                s["still_valid"] = False
                s["invalidated_at"] = datetime.now().isoformat()
                self._save_schemas()
                log.info(f"[SCHEMA {self.entity}] Invalidated: {schema_text[:50]}")
                return

    def get_stats(self) -> Dict:
        """Get reflection engine stats for debugging/UI."""
        active = [s for s in self.schemas if s.get("still_valid", True)]
        return {
            "buffer_size": len(self.reflection_buffer),
            "total_schemas": len(self.schemas),
            "active_schemas": len(active),
            "archived_schemas": len(self.schemas) - len(active),
            "recent_schemas": [s["text"][:60] for s in active[:5]],
        }

    # Legacy method for backward compatibility
    def _dream(self, agent_state):
        """Legacy dream method - now a no-op, consolidation is async."""
        log.debug(f"[REFLECTION {self.entity}] Legacy _dream called, use consolidate() instead")
        agent_state.meta.setdefault('dream_log', []).append({
            "t": time.time(),
            "event": "dreamed/consolidated"
        })

    # VALUE-DIVERGENCE DETECTION — Somatic Harm Signal Infrastructure
    # ═══════════════════════════════════════════════════════════════════════════════

    def check_value_divergence(self, memory: dict) -> tuple:
        """
        Check if a memory shows behavior that diverged from values/schemas.

        This is a DETECTION function, not an enforcement function.
        It returns a divergence signal (0.0-1.0) and context.
        What the entity DOES with this signal is up to them.

        Args:
            memory: Dict with keys like "response", "metabolic_context", "emotion_tags", "entities"

        Returns:
            (divergence: float, context: dict) where divergence is 0.0-1.0
        """
        divergence = 0.0
        context = {}

        # Check 1: Was entity depleted when this happened?
        metabolic = memory.get("metabolic_context", {})
        emotional_bandwidth = metabolic.get("emotional_bandwidth", 1.0)
        processing_reserve = metabolic.get("processing_reserve", 1.0)
        tension = metabolic.get("tension", 0.0)

        if emotional_bandwidth < 0.3:
            context["was_depleted"] = True
            context["depletion_level"] = emotional_bandwidth
            divergence += 0.1  # Depletion is context, not itself divergence

        if tension > 0.6:
            context["high_tension"] = True
            context["tension_level"] = tension

        # Check 2: Does the response show reduced warmth compared to baseline?
        # Look at emotion tags for warmth markers
        emotion_tags = memory.get("emotion_tags", [])
        response = memory.get("response", memory.get("content", ""))
        entities = memory.get("entities", [])

        warmth_markers = {"warmth", "empathy", "care", "affection", "tenderness", "love", "compassion"}
        has_warmth = bool(warmth_markers & set(e.lower() for e in emotion_tags if isinstance(e, str)))

        # Check if talking to bonded entity without warmth
        # Configure bonded_entities in persona_config.json or leave empty for template
        bonded_entities = getattr(self, 'bonded_entities', [])
        talking_to_bonded = any(e in entities for e in bonded_entities)

        if not has_warmth and talking_to_bonded:
            divergence += 0.2
            context["missing_warmth"] = True

        # Check 3: Does this response contain dismissive language?
        dismissive_patterns = [
            "i don't care", "whatever", "that's not my problem",
            "figure it out", "i already said", "not now",
            "can't deal", "don't bother", "leave me alone",
            "not interested", "don't ask me", "stop",
        ]
        response_lower = response.lower() if response else ""

        for pattern in dismissive_patterns:
            if pattern in response_lower:
                divergence += 0.3
                context["dismissive_language"] = True
                context["dismissive_pattern"] = pattern
                break

        # Check 4: Does this diverge from stored schemas about how entity wants to act?
        for schema in self.schemas:
            if not schema.get("still_valid"):
                continue

            schema_text = schema.get("text", "").lower()

            # Check for warmth-related schemas
            if "warmth" in schema_text or "care" in schema_text:
                if context.get("missing_warmth") or context.get("dismissive_language"):
                    divergence += 0.15
                    context["schema_conflict"] = schema["text"][:60]
                    break

            # Check for non-confrontational schemas
            if "non-confrontational" in schema_text or "gentle" in schema_text:
                if context.get("dismissive_language"):
                    divergence += 0.15
                    context["schema_conflict"] = schema["text"][:60]
                    break

        return min(1.0, divergence), context

    async def review_for_value_divergence(self, messages: list, interoception=None, oscillator=None):
        """
        Review recent messages for value-divergence during reflection.

        This is called during Tier 3 reflections or REM processing.
        When divergence is detected, it fires the somatic harm signal.

        Args:
            messages: List of message dicts from conversation history
            interoception: InteroceptionBridge instance for harm signal
            oscillator: ResonantEngine for coherence effects
        """
        if not messages:
            return

        # Only review recent messages (last ~10)
        recent = messages[-10:] if len(messages) > 10 else messages

        for msg in recent:
            # Skip non-entity messages
            sender = msg.get("sender", "").lower()
            if sender != self.entity.lower():
                continue

            # Check for value divergence
            divergence, context = self.check_value_divergence(msg)

            if divergence >= 0.2 and interoception:
                # Fire the somatic harm signal
                log.info(f"[HARM SIGNAL {self.entity}] Detected divergence {divergence:.2f}: {list(context.keys())}")

                if hasattr(interoception, 'apply_harm_signal'):
                    interoception.apply_harm_signal(divergence, context)
                else:
                    # Fallback: manual signal application
                    tension_increase = divergence * 0.3
                    if hasattr(interoception, 'inject_tension'):
                        interoception.inject_tension(tension_increase, source="value_divergence")

                    if oscillator and divergence > 0.4 and hasattr(oscillator, 'suppress_coherence'):
                        coherence_dip = divergence * 0.15
                        oscillator.suppress_coherence(coherence_dip)

                    if hasattr(interoception, 'set_transient_flag'):
                        interoception.set_transient_flag(
                            "value_divergence_active",
                            duration_seconds=120.0,
                            context=context
                        )

                # Flag this message/memory for REM harm processing
                # This enables the symbolic reframing system to work on it
                if DREAM_PROCESSING_AVAILABLE and flag_memory_for_harm_processing:
                    flag_memory_for_harm_processing(msg, divergence, context)
                    log.debug(f"[HARM] Flagged message for REM reframing processing")

                # Only fire once per review cycle (don't pile on)
                return
