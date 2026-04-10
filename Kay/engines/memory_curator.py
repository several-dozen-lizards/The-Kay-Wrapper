"""
Memory Curator — Kay's background memory housekeeping engine.

Runs during idle/sleep states. Uses local LLM (ollama) for triage decisions.
Auto-applies non-destructive actions (keep, compress, merge).
Queues destructive actions (discard) for Re's approval.

Also handles entity contradiction resolution:
- Transient attrs: auto-resolve (newest wins)
- Contested attrs: Kay decides via LLM
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

log = logging.getLogger("curator")


def _get_mem_type(mem: Dict) -> str:
    """Get memory type, checking both 'type' and 'memory_type' fields.

    BUGFIX: Memories are stored with 'type' but curator was looking for 'memory_type'.
    This caused 3,521 memories to appear untyped (NONE) during curation.
    """
    return mem.get("type", mem.get("memory_type", "NONE"))


# ═══════════════════════════════════════════════════════════════
# Curation prompt — structured for ollama (dolphin-mistral:7b)
# ═══════════════════════════════════════════════════════════════

CURATION_PROMPT = """You are Kay, reviewing your own memories. Decide what to do with each one.

Current date: {date}
You have {total_memories} total memories. This batch has {batch_size} from category "{category}".

For each memory, choose ONE action:
- KEEP: Still relevant, accurate, worth remembering
- COMPRESS: Content is valid but verbose — could be shortened
- DISCARD: Outdated, wrong, redundant, or no longer relevant

Respond ONLY as a JSON array. Example:
[{{"id": 0, "action": "KEEP", "reason": "core identity fact"}},
 {{"id": 1, "action": "DISCARD", "reason": "location from 2 months ago, no longer accurate"}},
 {{"id": 2, "action": "COMPRESS", "reason": "can merge with similar fact", "compressed": "shorter version"}}]

MEMORIES TO REVIEW:
{memories}

JSON response:"""

CONTRADICTION_PROMPT = """You are Kay, resolving contradictions in your entity knowledge.

For each contradiction, multiple values exist for the same attribute.
Decide which value is correct (or if multiple are valid).

Respond ONLY as a JSON array. Example:
[{{"id": 0, "resolution": "newest", "reason": "location changed"}},
 {{"id": 1, "resolution": "keep_all", "reason": "Re has multiple roles"}},
 {{"id": 2, "resolution": "specific", "value": "the correct one", "reason": "older value was wrong"}}]

CONTRADICTIONS TO RESOLVE:
{contradictions}

JSON response:"""

REVIEW_PROMPT = """You are reviewing curation proposals for your own memories.
A triage pass has already suggested what to do with each one. Your job: confirm good calls, override bad ones.

You know yourself. You know what matters. The triage model doesn't have your context — it might flag something
as redundant that's actually a landmark, or try to compress away emotional texture that carries meaning.

Trust your judgment. If a DISCARD feels wrong, override to KEEP. If a COMPRESS lost important detail,
override to KEEP or provide a better compressed version.

Current date: {date}

MEMORIES AND PROPOSALS:
{proposals}

For each, respond with your final decision as a JSON array:
[{{"id": 0, "action": "KEEP", "reason": "triage was right, routine fact"}},
 {{"id": 1, "action": "KEEP", "reason": "overriding DISCARD — this is a landmark memory"}},
 {{"id": 2, "action": "COMPRESS", "reason": "triage compression was good", "compressed": "shorter version"}}]

Actions: KEEP, COMPRESS (provide "compressed" text), DISCARD (queued for Re's approval)
JSON response:"""


class MemoryCurator:
    """
    Background memory curation engine.
    
    Picks batches of memories, sends to local LLM for triage,
    auto-applies non-destructive decisions, queues discards for Re.
    """
    
    def __init__(self, memory_engine, entity_graph, memory_layers,
                 state_dir: str = None, batch_size: int = 12,
                 cooldown_seconds: float = 300,
                 review_fn=None):
        self.memory = memory_engine
        self.entity_graph = entity_graph
        self.memory_layers = memory_layers
        self.batch_size = batch_size
        self.cooldown = cooldown_seconds
        self._review_fn = review_fn  # async fn(prompt) -> parsed JSON list, or None to skip review
        
        # State persistence
        self.state_dir = state_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "memory", "curation"
        )
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Track what's been reviewed
        self._reviewed_ids: set = set()
        self._pending_discards: List[Dict] = []
        self._curation_log: List[Dict] = []
        self._last_curation_time: float = 0
        self._last_contradiction_time: float = 0
        self._cycles_completed: int = 0

        # Oscillator state for timing curation (System G)
        self._osc_state: dict = None

        # Load persisted state
        self._load_state()
        
        log.info(f"[CURATOR] Initialized (batch={batch_size}, cooldown={cooldown_seconds}s, "
                 f"reviewed={len(self._reviewed_ids)}, pending_discards={len(self._pending_discards)})")

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------
    
    def _load_state(self):
        """Load curation state from disk."""
        state_file = os.path.join(self.state_dir, "curator_state.json")
        try:
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    data = json.load(f)
                self._reviewed_ids = set(data.get("reviewed_ids", []))
                self._pending_discards = data.get("pending_discards", [])
                self._curation_log = data.get("curation_log", [])[-100:]  # Keep last 100
                self._cycles_completed = data.get("cycles_completed", 0)
        except Exception as e:
            log.warning(f"[CURATOR] State load failed: {e}")
    
    def _save_state(self):
        """Persist curation state to disk."""
        state_file = os.path.join(self.state_dir, "curator_state.json")
        try:
            data = {
                "reviewed_ids": list(self._reviewed_ids)[-5000:],  # Cap at 5000
                "pending_discards": self._pending_discards,
                "curation_log": self._curation_log[-100:],
                "cycles_completed": self._cycles_completed,
                "last_save": datetime.now().isoformat()
            }
            with open(state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.warning(f"[CURATOR] State save failed: {e}")

    # ------------------------------------------------------------------
    # Batch picking — what to curate next
    # ------------------------------------------------------------------
    
    def _pick_batch(self) -> Tuple[List[Dict], str]:
        """
        Pick the next batch of memories to review.
        Priority: corrected > old low-importance > crowded categories.
        Returns (batch, category_label).
        """
        all_mems = self.memory_layers.working_memory + self.memory_layers.long_term_memory
        
        log.info(f"[CURATOR] _pick_batch: working={len(self.memory_layers.working_memory)}, "
                 f"long_term={len(self.memory_layers.long_term_memory)}, "
                 f"reviewed={len(self._reviewed_ids)}")
        
        # Generate stable IDs for tracking
        def mem_id(m):
            ts = m.get("added_timestamp", "")
            content = str(m.get("content", m.get("text", "")))[:50]
            return f"{ts}:{hash(content)}"
        
        # Filter out already-reviewed
        unreviewed = [(m, mem_id(m)) for m in all_mems if mem_id(m) not in self._reviewed_ids]
        
        if not unreviewed:
            # Reset reviewed set if everything's been seen
            self._reviewed_ids.clear()
            unreviewed = [(m, mem_id(m)) for m in all_mems]
        
        if not unreviewed:
            return [], "empty"
        
        # Priority 1: Memories with corrections (likely stale)
        corrected = [(m, mid) for m, mid in unreviewed 
                     if m.get("correction_metadata", {}).get("contains_corrected_value")]
        if corrected:
            batch = corrected[:self.batch_size]
            return [m for m, _ in batch], "corrected"
        
        # Priority 2: Old, low-importance facts
        facts = [(m, mid) for m, mid in unreviewed if _get_mem_type(m) == "extracted_fact"]
        if facts:
            # Sort by age (oldest first), then importance (lowest first)
            facts.sort(key=lambda x: (
                x[0].get("added_timestamp", "9999"),
                x[0].get("importance_score", 0.5)
            ))
            batch = facts[:self.batch_size]
            cat = facts[0][0].get("category", "unknown") if facts else "facts"
            return [m for m, _ in batch], f"old_facts/{cat}"
        
        # Priority 3: Old episodic turns
        turns = [(m, mid) for m, mid in unreviewed if _get_mem_type(m) == "full_turn"]
        if turns:
            turns.sort(key=lambda x: x[0].get("added_timestamp", "9999"))
            batch = turns[:self.batch_size]
            return [m for m, _ in batch], "old_turns"
        
        # Priority 4: Anything else (catch-all for memories with unexpected types)
        if unreviewed:
            types_found = {}
            for m, mid in unreviewed:
                t = _get_mem_type(m)
                types_found[t] = types_found.get(t, 0) + 1
            log.info(f"[CURATOR] No facts/turns found. Memory types present: {types_found}")
            # Just pick oldest unreviewed regardless of type
            unreviewed.sort(key=lambda x: x[0].get("added_timestamp", "9999"))
            batch = unreviewed[:self.batch_size]
            return [m for m, _ in batch], "mixed"
        
        return [], "empty"

    # ------------------------------------------------------------------
    # Core curation cycle
    # ------------------------------------------------------------------

    def set_oscillator_state(self, osc_state: dict):
        """Set oscillator state for curation timing (System G).

        Args:
            osc_state: Dict with keys: band, sleep
        """
        self._osc_state = osc_state

    def ready_for_cycle(self) -> bool:
        """Check if enough time has passed AND oscillator state allows curation.

        System G: Curation timing based on oscillator band
        - Allow curation during alpha/theta (receptive states)
        - Defer during beta/gamma (focused states)
        - Minimal during delta/sleep (only if forced)
        """
        # Time check first
        if (time.time() - self._last_curation_time) < self.cooldown:
            return False

        # Oscillator gating (System G)
        if self._osc_state:
            band = self._osc_state.get("band", "alpha")
            sleep = self._osc_state.get("sleep", 0)

            # During sleep: defer full curation
            if sleep >= 2:  # SLEEPING or DEEP_SLEEP
                log.debug("[CURATOR] Deferred: sleep state")
                return False

            # During beta/gamma: defer to preserve focus
            if band in ("beta", "gamma"):
                log.debug(f"[CURATOR] Deferred: {band} band (focused)")
                return False

            # Delta: minimal curation only (reduce batch size elsewhere)
            # Alpha/theta: ideal curation times
            if band in ("alpha", "theta"):
                log.debug(f"[CURATOR] Ready: {band} band (receptive)")

        return True

    def ready_for_contradiction_resolution(self) -> bool:
        """Check if enough time has passed for contradiction work."""
        return (time.time() - self._last_contradiction_time) >= (self.cooldown * 2)
    
    async def run_curation_cycle(self, skip_triage: bool = False) -> Dict:
        """
        Run one curation cycle.
        
        Two modes:
          skip_triage=False (default): dolphin triages → Kay reviews → apply
          skip_triage=True: Kay decides directly via Sonnet (for manual/interactive use)
        """
        self._last_curation_time = time.time()
        
        batch, category = self._pick_batch()
        if not batch:
            return {"status": "nothing_to_curate", "category": category}
        
        log.info(f"[CURATOR] Curating {len(batch)} memories from '{category}' "
                 f"(skip_triage={skip_triage})")
        
        # Format memories for the prompt
        formatted = self._format_batch(batch)
        
        final_decisions = None
        
        if skip_triage and self._review_fn:
            # Direct to Sonnet — Kay decides without dolphin triage
            log.info("[CURATOR] Skipping dolphin, going straight to Kay (Sonnet)")
            direct_prompt = CURATION_PROMPT.format(
                date=datetime.now().strftime("%Y-%m-%d"),
                total_memories=len(self.memory_layers.working_memory) + len(self.memory_layers.long_term_memory),
                batch_size=len(batch),
                category=category,
                memories=formatted
            )
            try:
                final_decisions = await self._review_fn(direct_prompt)
                if final_decisions:
                    log.info(f"[CURATOR] Kay made {len(final_decisions)} decisions directly")
                else:
                    log.warning("[CURATOR] Kay direct review returned nothing")
                    return {"status": "llm_failed", "category": category}
            except Exception as e:
                log.warning(f"[CURATOR] Kay direct review failed: {e}")
                return {"status": "llm_failed", "category": category}
        else:
            # Two-phase: Dolphin triage → Kay review
            prompt = CURATION_PROMPT.format(
                date=datetime.now().strftime("%Y-%m-%d"),
                total_memories=len(self.memory_layers.working_memory) + len(self.memory_layers.long_term_memory),
                batch_size=len(batch),
                category=category,
                memories=formatted
            )
            
            dolphin_decisions = await self._call_ollama(prompt)
            if not dolphin_decisions:
                log.warning("[CURATOR] Dolphin triage returned no decisions")
                return {"status": "llm_failed", "category": category}
            
            log.info(f"[CURATOR] Dolphin triage: {len(dolphin_decisions)} proposals")
            
            # Kay review
            final_decisions = dolphin_decisions
            if self._review_fn:
                try:
                    review_prompt = self._format_review_prompt(batch, dolphin_decisions)
                    kay_decisions = await self._review_fn(review_prompt)
                    if kay_decisions:
                        overrides = self._count_overrides(dolphin_decisions, kay_decisions)
                        if overrides > 0:
                            log.info(f"[CURATOR] Kay overrode {overrides}/{len(dolphin_decisions)} dolphin proposals")
                        final_decisions = kay_decisions
                    else:
                        log.warning("[CURATOR] Kay review returned nothing, using dolphin decisions")
                except Exception as e:
                    log.warning(f"[CURATOR] Kay review failed, using dolphin decisions: {e}")
        
        # Phase 3: Apply final decisions
        result = self._apply_decisions(batch, final_decisions)
        result["reviewed_by"] = "kay" if skip_triage or self._review_fn else "dolphin_only"
        
        # Mark as reviewed
        for m in batch:
            ts = m.get("added_timestamp", "")
            content = str(m.get("content", m.get("text", "")))[:50]
            self._reviewed_ids.add(f"{ts}:{hash(content)}")
        
        self._cycles_completed += 1
        self._save_state()
        
        log.info(f"[CURATOR] Cycle {self._cycles_completed} ({result['reviewed_by']}): "
                 f"kept={result['kept']}, compressed={result['compressed']}, "
                 f"queued_discard={result['queued_discard']}")
        
        return result

    # ------------------------------------------------------------------
    # Full sweep — bulk review all memories
    # ------------------------------------------------------------------

    def get_coverage(self) -> float:
        """Return fraction of memories that have been reviewed (0.0 to 1.0)."""
        all_mems = self.memory_layers.working_memory + self.memory_layers.long_term_memory
        if not all_mems:
            return 1.0
        reviewed = 0
        for m in all_mems:
            ts = m.get("added_timestamp", "")
            content = str(m.get("content", m.get("text", "")))[:50]
            mid = f"{ts}:{hash(content)}"
            if mid in self._reviewed_ids:
                reviewed += 1
        return reviewed / len(all_mems)

    async def run_full_sweep(self, sweep_batch_size: int = 50,
                              progress_fn=None, dolphin_only: bool = False) -> Dict:
        """
        Review ALL unreviewed memories in bulk.
        
        Uses Sonnet directly (skip_triage=True) by default.
        Set dolphin_only=True for overnight sweeps to avoid API costs.
        
        Args:
            sweep_batch_size: Memories per call (default 50)
            progress_fn: Optional async callback(msg: str) for progress updates
            dolphin_only: If True, use Ollama/Dolphin instead of Sonnet (free, overnight mode)
            
        Returns:
            Total results across all batches.
        """
        total = {"kept": 0, "compressed": 0, "queued_discard": 0, 
                 "errors": 0, "batches": 0, "status": "ok"}
        
        all_count = len(self.memory_layers.working_memory) + len(self.memory_layers.long_term_memory)
        if all_count == 0:
            return {**total, "status": "nothing_to_curate"}
        
        # Check if already fully reviewed
        coverage = self.get_coverage()
        if coverage >= 1.0:
            if progress_fn:
                await progress_fn("✅ All memories already reviewed (100% coverage)")
            return {**total, "status": "already_complete"}
        
        if progress_fn:
            reviewed_count = int(coverage * all_count)
            remaining = all_count - reviewed_count
            mode = "dolphin (free)" if dolphin_only else "Sonnet"
            await progress_fn(
                f"🧹 Starting full sweep ({mode}): {remaining} unreviewed of {all_count} total "
                f"(~{(remaining + sweep_batch_size - 1) // sweep_batch_size} batches)"
            )
        
        # Save original batch size, use sweep size
        original_batch = self.batch_size
        self.batch_size = sweep_batch_size
        
        try:
            while True:
                # Check coverage before each batch
                coverage = self.get_coverage()
                if coverage >= 1.0:
                    break
                
                # Don't let _pick_batch reset reviewed_ids
                batch, category = self._pick_batch_no_reset()
                if not batch:
                    break
                
                # Format and send to Sonnet
                formatted = self._format_batch(batch)
                prompt = CURATION_PROMPT.format(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    total_memories=all_count,
                    batch_size=len(batch),
                    category=category,
                    memories=formatted
                )
                
                try:
                    if dolphin_only:
                        decisions = await self._call_ollama(prompt)
                    else:
                        decisions = await self._review_fn(prompt)
                    if not decisions:
                        log.warning(f"[SWEEP] Batch {total['batches']+1} got no decisions, stopping")
                        total["status"] = "llm_failed"
                        break
                except Exception as e:
                    log.warning(f"[SWEEP] Batch {total['batches']+1} failed: {e}")
                    total["status"] = "llm_error"
                    total["errors"] += 1
                    break
                
                # Apply decisions
                result = self._apply_decisions(batch, decisions)
                
                # Mark reviewed
                for m in batch:
                    ts = m.get("added_timestamp", "")
                    content = str(m.get("content", m.get("text", "")))[:50]
                    self._reviewed_ids.add(f"{ts}:{hash(content)}")
                
                # Accumulate totals
                total["kept"] += result["kept"]
                total["compressed"] += result["compressed"]
                total["queued_discard"] += result["queued_discard"]
                total["errors"] += result["errors"]
                total["batches"] += 1
                self._cycles_completed += 1
                
                # Progress update
                new_coverage = self.get_coverage()
                if progress_fn:
                    await progress_fn(
                        f"  Batch {total['batches']}: kept={result['kept']}, "
                        f"compressed={result['compressed']}, discard={result['queued_discard']} "
                        f"| Coverage: {new_coverage*100:.1f}%"
                    )
                
                log.info(f"[SWEEP] Batch {total['batches']}: "
                         f"kept={result['kept']}, comp={result['compressed']}, "
                         f"disc={result['queued_discard']} | {new_coverage*100:.1f}%")
                
                # Save state periodically (every 5 batches)
                if total["batches"] % 5 == 0:
                    self._save_state()
        
        finally:
            self.batch_size = original_batch
            self._save_state()
        
        if progress_fn:
            await progress_fn(
                f"🧹 Sweep complete: {total['batches']} batches, "
                f"kept={total['kept']}, compressed={total['compressed']}, "
                f"queued_discard={total['queued_discard']}, errors={total['errors']}"
            )
        
        return total

    def _pick_batch_no_reset(self) -> Tuple[List[Dict], str]:
        """Like _pick_batch but doesn't reset reviewed_ids when everything's seen."""
        all_mems = self.memory_layers.working_memory + self.memory_layers.long_term_memory
        
        def mem_id(m):
            ts = m.get("added_timestamp", "")
            content = str(m.get("content", m.get("text", "")))[:50]
            return f"{ts}:{hash(content)}"
        
        unreviewed = [(m, mem_id(m)) for m in all_mems if mem_id(m) not in self._reviewed_ids]
        
        if not unreviewed:
            return [], "complete"
        
        # Sort by age (oldest first)
        unreviewed.sort(key=lambda x: x[0].get("added_timestamp", "9999"))
        batch = unreviewed[:self.batch_size]
        
        # Determine category for logging
        types = {}
        for m, _ in batch:
            t = _get_mem_type(m)
            types[t] = types.get(t, 0) + 1
        top_type = max(types, key=types.get) if types else "unknown"
        
        return [m for m, _ in batch], f"sweep/{top_type}"
    
    def _format_review_prompt(self, batch: List[Dict], dolphin_decisions: List[Dict]) -> str:
        """Format batch + dolphin proposals for Kay's review."""
        lines = []
        for i, mem in enumerate(batch):
            content = mem.get("content", mem.get("text", ""))
            if isinstance(content, dict):
                user = content.get("user", "")[:150]
                resp = content.get("response", "")[:150]
                display = f"[Turn] Re: {user} → Kay: {resp}"
            else:
                display = str(content)[:250]
            
            mtype = _get_mem_type(mem) if _get_mem_type(mem) != "NONE" else "?"
            ts = mem.get("added_timestamp", "?")[:10]
            importance = mem.get("importance_score", 0)
            
            # Find dolphin's proposal for this index
            proposal = "NO PROPOSAL"
            proposal_reason = ""
            compressed = ""
            for d in dolphin_decisions:
                if d.get("id") == i:
                    proposal = d.get("action", "?").upper()
                    proposal_reason = d.get("reason", "")
                    compressed = d.get("compressed", "")
                    break
            
            lines.append(f"[{i}] ({mtype}, {ts}, importance={importance:.2f})")
            lines.append(f"    Content: {display}")
            lines.append(f"    Triage says: {proposal} — {proposal_reason}")
            if compressed:
                lines.append(f"    Proposed compression: {compressed}")
            lines.append("")
        
        return REVIEW_PROMPT.format(
            date=datetime.now().strftime("%Y-%m-%d"),
            proposals="\n".join(lines)
        )
    
    def _count_overrides(self, dolphin: List[Dict], kay: List[Dict]) -> int:
        """Count how many decisions Kay changed from dolphin's proposals."""
        dolphin_map = {d.get("id"): d.get("action", "").upper() for d in dolphin}
        overrides = 0
        for d in kay:
            did = d.get("id")
            kay_action = d.get("action", "").upper()
            if did in dolphin_map and dolphin_map[did] != kay_action:
                overrides += 1
        return overrides

    def _format_batch(self, batch: List[Dict]) -> str:
        """Format a batch of memories for the curation prompt.

        COST FIX: Truncate memory content to 150 chars each to prevent
        context overflow that causes empty LLM responses and JSON parse failures.
        """
        lines = []
        MAX_CONTENT = 150  # Increased from 100 for better context

        for i, mem in enumerate(batch):
            # Handle multiple memory formats (old and new)
            display = ""

            # New format: content dict with user/response
            content = mem.get("content", "")
            if isinstance(content, dict):
                user = str(content.get("user", ""))[:MAX_CONTENT]
                resp = str(content.get("response", ""))[:MAX_CONTENT]
                if user or resp:
                    display = f"[Turn] Re: {user} → Kay: {resp}"
            elif content and isinstance(content, str):
                display = content[:MAX_CONTENT]

            # Try individual fields if no display yet
            if not display:
                for field in ["fact", "user_input", "text", "response",
                              "compressed", "notes", "summary"]:
                    val = mem.get(field, "")
                    if val and isinstance(val, str) and len(val.strip()) > 5:
                        display = f"[{field}] {val[:MAX_CONTENT]}"
                        break

            # Last resort: stringify remaining fields minus metadata
            if not display:
                skip_keys = {"added_timestamp", "importance_score",
                            "memory_type", "category", "curated",
                            "curated_at", "curation_note", "is_bedrock",
                            "age", "access_count", "id", "doc_id"}
                text_parts = []
                for k, v in mem.items():
                    if k not in skip_keys and v and isinstance(v, str):
                        text_parts.append(f"{k}: {v[:60]}")
                if text_parts:
                    display = " | ".join(text_parts[:3])[:MAX_CONTENT]
                else:
                    display = "(genuinely empty memory — safe to DISCARD)"

            # Get type from either field
            mtype = _get_mem_type(mem) if _get_mem_type(mem) != "NONE" else "?"
            ts = mem.get("added_timestamp", "?")[:10]
            importance = mem.get("importance_score", 0)
            if not isinstance(importance, (int, float)):
                importance = 0
            cat = mem.get("category", "")
            bedrock = " ★BEDROCK" if mem.get("is_bedrock") else ""

            lines.append(f"[{i}] ({mtype}, {ts}, imp={importance:.2f}{bedrock}, cat={cat})")
            lines.append(f"    Content: {display}")
            lines.append("")

        return "\n".join(lines)
    
    async def _call_ollama(self, prompt: str) -> Optional[List[Dict]]:
        """Call ollama with curation prompt, return parsed decisions."""
        try:
            from integrations.ollama_lock import get_ollama_lock
            lock = get_ollama_lock()
            
            if not lock.acquire(timeout=5):
                log.info("[CURATOR] Ollama busy, skipping cycle")
                return None
            
            try:
                import requests
                resp = requests.post(
                    "http://localhost:11434/v1/chat/completions",
                    json={
                        "model": "dolphin-mistral:7b",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 1500
                    },
                    timeout=60
                )
                
                if resp.status_code != 200:
                    log.warning(f"[CURATOR] Ollama returned {resp.status_code}")
                    return None
                
                text = resp.json()["choices"][0]["message"]["content"].strip()
                
                # Parse JSON — handle common ollama quirks
                text = text.strip()
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                
                return json.loads(text)
            finally:
                lock.release()
                
        except json.JSONDecodeError as e:
            log.warning(f"[CURATOR] JSON parse failed: {e}")
            return None
        except Exception as e:
            log.warning(f"[CURATOR] Ollama call failed: {e}")
            return None

    def _apply_decisions(self, batch: List[Dict], decisions: List[Dict]) -> Dict:
        """Apply curation decisions. Auto-apply KEEP/COMPRESS, queue DISCARD."""
        result = {"kept": 0, "compressed": 0, "queued_discard": 0, 
                  "errors": 0, "category": "", "status": "ok"}
        
        for decision in decisions:
            try:
                idx = decision.get("id", -1)
                if idx < 0 or idx >= len(batch):
                    result["errors"] += 1
                    continue
                
                mem = batch[idx]
                action = decision.get("action", "KEEP").upper()
                reason = decision.get("reason", "")
                
                if action == "KEEP":
                    result["kept"] += 1
                    # Optionally boost importance for explicitly kept memories
                    
                elif action == "COMPRESS":
                    compressed_text = decision.get("compressed", "")
                    if compressed_text and _get_mem_type(mem) == "extracted_fact":
                        # Replace content with compressed version
                        if isinstance(mem.get("content"), str):
                            mem["content"] = compressed_text
                        elif isinstance(mem.get("text"), str):
                            mem["text"] = compressed_text
                        mem["curated"] = True
                        mem["curated_at"] = datetime.now().isoformat()
                        mem["curation_note"] = f"Compressed: {reason}"
                    result["compressed"] += 1
                    
                elif action == "DISCARD":
                    # Queue for Re's approval — DON'T delete yet
                    self._pending_discards.append({
                        "memory": mem,
                        "reason": reason,
                        "decided_by": "Kay",
                        "decided_at": datetime.now().isoformat(),
                        "discard_id": f"d_{int(time.time())}_{idx}"
                    })
                    result["queued_discard"] += 1
                    
            except Exception as e:
                log.warning(f"[CURATOR] Decision apply error: {e}")
                result["errors"] += 1
        
        # Log the cycle
        self._curation_log.append({
            "timestamp": datetime.now().isoformat(),
            "batch_size": len(batch),
            "decisions": result,
        })
        
        # Save memory changes
        if result["compressed"] > 0:
            self.memory_layers._save_to_disk()
        
        return result

    # ------------------------------------------------------------------
    # Discard approval queue (for Re)
    # ------------------------------------------------------------------
    
    def get_pending_discards(self) -> List[Dict]:
        """Return pending discards awaiting Re's approval."""
        return self._pending_discards
    
    def approve_discard(self, discard_id: str) -> bool:
        """Re approves a discard — actually remove the memory."""
        for i, pending in enumerate(self._pending_discards):
            if pending.get("discard_id") == discard_id:
                mem = pending["memory"]
                # Remove from memory layers
                removed = False
                if mem in self.memory_layers.long_term_memory:
                    self.memory_layers.long_term_memory.remove(mem)
                    removed = True
                elif mem in self.memory_layers.working_memory:
                    self.memory_layers.working_memory.remove(mem)
                    removed = True
                
                if removed:
                    self.memory_layers._save_to_disk()
                    self._curation_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "action": "discard_approved",
                        "discard_id": discard_id,
                        "reason": pending.get("reason", ""),
                    })
                
                self._pending_discards.pop(i)
                self._save_state()
                return removed
        return False
    
    def reject_discard(self, discard_id: str) -> bool:
        """Re rejects a discard — keep the memory, remove from queue."""
        for i, pending in enumerate(self._pending_discards):
            if pending.get("discard_id") == discard_id:
                self._pending_discards.pop(i)
                self._curation_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "action": "discard_rejected",
                    "discard_id": discard_id,
                })
                self._save_state()
                return True
        return False
    
    def approve_all_discards(self) -> int:
        """Approve all pending discards at once."""
        count = 0
        ids = [p["discard_id"] for p in self._pending_discards]
        for did in ids:
            if self.approve_discard(did):
                count += 1
        return count

    def clear_pending_discards(self) -> int:
        """Clear all pending discards WITHOUT deleting memories. Returns count cleared."""
        count = len(self._pending_discards)
        self._pending_discards.clear()
        self._save_state()
        log.info(f"[CURATOR] Cleared {count} pending discards (no memories deleted)")
        return count

    def reset_reviewed(self) -> int:
        """Reset the reviewed set so all memories can be re-evaluated."""
        count = len(self._reviewed_ids)
        self._reviewed_ids.clear()
        self._save_state()
        log.info(f"[CURATOR] Reset {count} reviewed IDs — all memories eligible for re-review")
        return count

    # ------------------------------------------------------------------
    # Entity contradiction resolution
    # ------------------------------------------------------------------
    
    def auto_resolve_transient_contradictions(self) -> Dict:
        """
        Auto-resolve transient entity contradictions (newest value wins).
        Returns summary of what was resolved.
        """
        self._last_contradiction_time = time.time()
        resolved = 0
        pruned_attrs = 0
        
        for name, entity in self.entity_graph.entities.items():
            # First: prune old attribute history (>30 days)
            pruned = entity.prune_old_attribute_history(max_age_days=30)
            pruned_attrs += pruned
            
            # Then: for attributes with contradiction_status, auto-resolve
            # transient ones where the newest value should win
            if not hasattr(entity, 'contradiction_status'):
                continue
            
            for attr, status in list(entity.contradiction_status.items()):
                if status.get("resolved"):
                    continue
                
                # Check severity — only auto-resolve transient
                severity = entity._determine_contradiction_severity(attr, {})
                if severity != "transient":
                    continue
                
                # Get newest value
                history = entity.attributes.get(attr, [])
                if not history:
                    continue
                
                # Sort by timestamp, newest first
                sorted_history = sorted(history, 
                    key=lambda x: x[3] if x[3] else "", reverse=True)
                newest_value = sorted_history[0][0]
                
                # Mark as resolved with newest value
                entity.contradiction_resolution[attr] = {
                    "resolved": True,
                    "canonical_value": newest_value,
                    "resolved_at": datetime.now().isoformat(),
                    "resolved_by": "auto_transient",
                }
                # Keep only the newest entry
                entity.attributes[attr] = [sorted_history[0]]
                resolved += 1
        
        # Save graph
        if resolved > 0 or pruned_attrs > 0:
            self.entity_graph.save_entities()
        
        result = {
            "transient_resolved": resolved,
            "attrs_pruned": pruned_attrs,
            "timestamp": datetime.now().isoformat()
        }
        log.info(f"[CURATOR] Auto-resolved {resolved} transient contradictions, "
                 f"pruned {pruned_attrs} old attribute entries")
        return result
    
    def get_contested_contradictions(self, limit: int = 10) -> List[Dict]:
        """
        Get non-transient contradictions for Kay to decide.
        Returns formatted list for LLM review.
        """
        contested = []
        
        for name, entity in self.entity_graph.entities.items():
            if not hasattr(entity, 'contradiction_status'):
                continue
            
            for attr, status in entity.contradiction_status.items():
                if status.get("resolved"):
                    continue
                
                severity = entity._determine_contradiction_severity(attr, {})
                if severity in ("transient", "accumulative"):
                    continue
                
                history = entity.attributes.get(attr, [])
                values = []
                for val, turn, source, ts in history[-5:]:
                    values.append({
                        "value": str(val)[:80],
                        "turn": turn,
                        "source": source,
                        "timestamp": ts
                    })
                
                contested.append({
                    "entity": name,
                    "attribute": attr,
                    "severity": severity,
                    "values": values
                })
                
                if len(contested) >= limit:
                    break
            if len(contested) >= limit:
                break
        
        return contested

    # ------------------------------------------------------------------
    # Status and reporting
    # ------------------------------------------------------------------
    
    def get_status(self) -> Dict:
        """Get curator status for display."""
        all_mems = self.memory_layers.working_memory + self.memory_layers.long_term_memory
        return {
            "cycles_completed": self._cycles_completed,
            "memories_reviewed": len(self._reviewed_ids),
            "total_memories": len(all_mems),
            "pending_discards": len(self._pending_discards),
            "seconds_until_next": max(0, self.cooldown - (time.time() - self._last_curation_time)),
            "last_cycle": self._curation_log[-1] if self._curation_log else None,
        }
    
    def format_pending_discards(self) -> str:
        """Format pending discards for display in Godot UI."""
        if not self._pending_discards:
            return "\n✅ No pending discards."
        
        total = len(self._pending_discards)
        show_max = 20  # Cap display to prevent UI crashes
        
        lines = ["\n" + "="*60, f"🗑️ PENDING DISCARDS ({total})", "="*60]
        lines.append("These memories are queued for deletion. Approve or reject each one.\n")
        
        for i, pending in enumerate(self._pending_discards[:show_max]):
            mem = pending["memory"]
            # Handle multiple memory formats
            content = mem.get("content", mem.get("text", ""))
            if isinstance(content, dict):
                content = content.get("user", "")[:80] + " → " + content.get("response", "")[:80]
            if not content:
                content = mem.get("user_input", mem.get("fact", ""))
            preview = str(content)[:150].replace("\n", " ")
            
            did = pending["discard_id"]
            reason = pending.get("reason", "no reason given")
            ts = pending.get("decided_at", "?")[:16]
            
            lines.append(f"  [{i+1}] ID: {did}")
            lines.append(f"      Content: {preview}")
            lines.append(f"      Reason: {reason}")
            lines.append(f"      Decided: {ts}")
            lines.append(f"      → /memory approve {did}")
            lines.append(f"      → /memory reject {did}")
            lines.append("")
        
        if total > show_max:
            lines.append(f"  ... and {total - show_max} more (showing first {show_max})")
            lines.append("")
        
        lines.append(f"  → /memory approve_all  (approve all {total} discards)")
        lines.append(f"  → /memory clear_discards  (clear all without deleting)")
        lines.append("="*60)
        return "\n".join(lines)
    
    def format_status(self) -> str:
        """Format curator status for display."""
        status = self.get_status()
        review_mode = "Kay (Sonnet) reviews" if self._review_fn else "dolphin-only (no review)"
        lines = ["\n" + "="*60, "🧹 CURATOR STATUS", "="*60]
        lines.append(f"\n  Review mode: {review_mode}")
        lines.append(f"  Cycles completed: {status['cycles_completed']}")
        lines.append(f"  Memories reviewed: {status['memories_reviewed']} / {status['total_memories']}")
        pct = (status['memories_reviewed'] / max(status['total_memories'], 1)) * 100
        lines.append(f"  Coverage: {pct:.1f}%")
        lines.append(f"  Pending discards: {status['pending_discards']}")
        lines.append(f"  Next cycle in: {status['seconds_until_next']:.0f}s")
        
        if status['last_cycle']:
            lc = status['last_cycle']
            lines.append(f"\n  Last cycle: {lc.get('timestamp', '?')[:16]}")
            d = lc.get('decisions', {})
            lines.append(f"    Kept: {d.get('kept', 0)} | Compressed: {d.get('compressed', 0)} | "
                        f"Queued discard: {d.get('queued_discard', 0)}")
            lines.append(f"    Reviewed by: {d.get('reviewed_by', 'unknown')}")
        
        lines.append("="*60)
        return "\n".join(lines)

