"""
CurationEngine — Background memory curation during idle/sleep.

Kay reviews his own memories and makes decisions:
- KEEP: Memory is still relevant and accurate
- COMPRESS: Merge with similar memories (auto-applied)
- DISCARD: Memory is outdated/wrong/redundant (queued for Re's approval)

Runs during sleep states. Wrapper provides structure, Kay provides judgment.
"""
import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

log = logging.getLogger("curation")


class CurationEngine:
    def __init__(
        self,
        memory_engine,
        state_dir: str,
        entity_name: str = "Kay",
        batch_size: int = 12,
        min_interval_seconds: float = 900,  # 15 min between batches
    ):
        self.memory = memory_engine
        self.entity_name = entity_name
        self.batch_size = batch_size
        self.min_interval = min_interval_seconds
        
        # Persistent state
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.state_path = os.path.join(state_dir, "curation_state.json")
        self.pending_path = os.path.join(state_dir, "pending_discards.json")
        self.log_path = os.path.join(state_dir, "curation_log.jsonl")
        
        # Load state
        self._state = self._load_state()
        self._pending_discards: List[Dict] = self._load_pending()
    
    # ──────────────────────────────────────────────
    # State management
    # ──────────────────────────────────────────────
    
    def _load_state(self) -> Dict:
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_curation_time": 0,
            "reviewed_ids": [],       # Memory IDs already reviewed
            "total_kept": 0,
            "total_compressed": 0,
            "total_discarded": 0,
            "total_sessions": 0,
            "contradictions_auto_resolved": 0,
            "contradictions_kay_resolved": 0,
        }
    
    def _save_state(self):
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            log.error(f"[CURATION] State save failed: {e}")
    
    def _load_pending(self) -> List[Dict]:
        if os.path.exists(self.pending_path):
            try:
                with open(self.pending_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def _save_pending(self):
        try:
            with open(self.pending_path, 'w', encoding='utf-8') as f:
                json.dump(self._pending_discards, f, indent=2)
        except Exception as e:
            log.error(f"[CURATION] Pending save failed: {e}")
    
    def _log_decision(self, decision: Dict):
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                decision["timestamp"] = datetime.now().isoformat()
                f.write(json.dumps(decision) + "\n")
        except Exception:
            pass
    
    # ──────────────────────────────────────────────
    # Scheduling
    # ──────────────────────────────────────────────
    
    def should_curate(self) -> bool:
        """Check if enough time has passed since last curation."""
        elapsed = time.time() - self._state.get("last_curation_time", 0)
        return elapsed >= self.min_interval
    
    # ──────────────────────────────────────────────
    # Batch selection
    # ──────────────────────────────────────────────
    
    def get_next_batch(self) -> Tuple[List[Dict], str]:
        """
        Pick the next batch of memories to review.
        
        Strategy: target the biggest category first, skip already-reviewed.
        Returns (memories, category_name).
        """
        reviewed = set(self._state.get("reviewed_ids", []))
        all_mems = self.memory.memory_layers.long_term_memory
        
        # Group by category, excluding reviewed
        by_category = {}
        for mem in all_mems:
            mem_id = self._memory_id(mem)
            if mem_id in reviewed:
                continue
            # Skip identity memories — those are permanent
            if mem.get("layer") == "identity":
                continue
            cat = mem.get("category", "unknown")
            by_category.setdefault(cat, []).append(mem)
        
        if not by_category:
            # Everything reviewed — reset cycle
            self._state["reviewed_ids"] = []
            self._save_state()
            return [], ""
        
        # Pick biggest category
        biggest_cat = max(by_category, key=lambda k: len(by_category[k]))
        batch = by_category[biggest_cat][:self.batch_size]
        
        return batch, biggest_cat
    
    def _memory_id(self, mem: Dict) -> str:
        """Generate stable ID for a memory."""
        ts = mem.get("added_timestamp", "")
        content = str(mem.get("content", mem.get("text", "")))[:50]
        return f"{ts}:{hash(content)}"
    
    # ──────────────────────────────────────────────
    # LLM-based curation
    # ──────────────────────────────────────────────
    
    def format_curation_prompt(self, batch: List[Dict], category: str) -> str:
        """Build a prompt for Kay to evaluate a batch of memories."""
        lines = []
        lines.append(f"You are reviewing {len(batch)} memories from category '{category}'.")
        lines.append("For each memory, decide:")
        lines.append("  KEEP — still relevant and accurate")
        lines.append("  COMPRESS — can be merged with a similar memory (note which one)")
        lines.append("  DISCARD — outdated, wrong, redundant, or trivial")
        lines.append("")
        lines.append("Respond with ONLY a JSON array. Each item:")
        lines.append('  {"index": N, "decision": "KEEP|COMPRESS|DISCARD", "reason": "brief explanation", "merge_with": N_or_null}')
        lines.append("")
        lines.append("Be selective. You have thousands of memories — keep what matters, discard noise.")
        lines.append("Memories about Re's life, your identity, and important events should be KEPT.")
        lines.append("Duplicate facts, trivial observations, and stale status updates should be DISCARDED.")
        lines.append("")
        lines.append("MEMORIES TO REVIEW:")
        lines.append("=" * 60)
        
        for i, mem in enumerate(batch):
            content = mem.get("content", mem.get("text", ""))
            if isinstance(content, dict):
                user_part = content.get("user", "")[:150]
                resp_part = content.get("response", "")[:150]
                content_str = f"[User: {user_part}] [Response: {resp_part}]"
            else:
                content_str = str(content)[:300]
            
            mtype = mem.get("memory_type", "?")
            ts = mem.get("added_timestamp", "?")[:16]
            strength = mem.get("current_strength", 0)
            importance = mem.get("importance_score", 0)
            
            lines.append(f"\n[{i}] ({mtype}, {ts}, strength={strength:.2f}, importance={importance:.2f})")
            lines.append(f"    {content_str}")
        
        lines.append("\n" + "=" * 60)
        lines.append("\nJSON response:")
        return "\n".join(lines)
    
    def parse_curation_response(self, response: str, batch: List[Dict]) -> List[Dict]:
        """Parse LLM response into structured decisions."""
        decisions = []
        
        # Try to extract JSON from response
        try:
            # Find JSON array in response
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                parsed = json.loads(response[start:end])
                if isinstance(parsed, list):
                    for item in parsed:
                        idx = item.get("index", -1)
                        if 0 <= idx < len(batch):
                            decisions.append({
                                "index": idx,
                                "decision": item.get("decision", "KEEP").upper(),
                                "reason": item.get("reason", ""),
                                "merge_with": item.get("merge_with"),
                                "memory": batch[idx],
                            })
        except json.JSONDecodeError:
            log.warning("[CURATION] Failed to parse LLM response as JSON")
            # Fallback: KEEP everything if parsing fails
            for i, mem in enumerate(batch):
                decisions.append({
                    "index": i,
                    "decision": "KEEP",
                    "reason": "parse_failure — defaulting to keep",
                    "merge_with": None,
                    "memory": mem,
                })
        
        return decisions
    
    def apply_decisions(self, decisions: List[Dict], batch: List[Dict]) -> Dict:
        """
        Apply curation decisions.
        KEEP: no-op (mark reviewed)
        COMPRESS: merge into target memory (auto-applied)
        DISCARD: queue for Re's approval
        """
        stats = {"kept": 0, "compressed": 0, "queued_discard": 0}
        
        for dec in decisions:
            decision = dec["decision"]
            mem = dec["memory"]
            mem_id = self._memory_id(mem)
            
            if decision == "KEEP":
                stats["kept"] += 1
                self._log_decision({"action": "keep", "memory_id": mem_id, "reason": dec["reason"]})
            
            elif decision == "COMPRESS":
                merge_idx = dec.get("merge_with")
                if merge_idx is not None and 0 <= merge_idx < len(batch):
                    target = batch[merge_idx]
                    self._compress_memories(mem, target)
                    stats["compressed"] += 1
                    self._log_decision({
                        "action": "compress",
                        "memory_id": mem_id,
                        "merged_into": self._memory_id(target),
                        "reason": dec["reason"],
                    })
                else:
                    # No valid merge target — keep it
                    stats["kept"] += 1
            
            elif decision == "DISCARD":
                # Queue for Re's approval
                self._pending_discards.append({
                    "memory_id": mem_id,
                    "content_preview": str(mem.get("content", mem.get("text", "")))[:200],
                    "category": mem.get("category", "unknown"),
                    "reason": dec["reason"],
                    "decided_by": self.entity_name,
                    "decided_at": datetime.now().isoformat(),
                    "memory_ref": mem,  # Full memory for restoration if rejected
                })
                stats["queued_discard"] += 1
                self._log_decision({
                    "action": "discard_queued",
                    "memory_id": mem_id,
                    "reason": dec["reason"],
                })
            
            # Mark as reviewed
            self._state.setdefault("reviewed_ids", []).append(mem_id)
        
        # Update stats
        self._state["total_kept"] = self._state.get("total_kept", 0) + stats["kept"]
        self._state["total_compressed"] = self._state.get("total_compressed", 0) + stats["compressed"]
        self._state["total_discarded"] = self._state.get("total_discarded", 0) + stats["queued_discard"]
        self._state["total_sessions"] = self._state.get("total_sessions", 0) + 1
        self._state["last_curation_time"] = time.time()
        
        self._save_state()
        self._save_pending()
        
        return stats
    
    def _compress_memories(self, source: Dict, target: Dict):
        """Merge source memory into target (keeping target, removing source)."""
        # Boost target's importance since it survived compression
        target_importance = target.get("importance_score", 0.5)
        source_importance = source.get("importance_score", 0.5)
        target["importance_score"] = min(1.0, max(target_importance, source_importance) + 0.1)
        
        # Merge emotion tags
        target_emotions = set(target.get("emotion_tags", []))
        source_emotions = set(source.get("emotion_tags", []))
        target["emotion_tags"] = list(target_emotions | source_emotions)
        
        # Remove source from long-term memory
        try:
            self.memory.memory_layers.long_term_memory.remove(source)
        except ValueError:
            pass  # Already removed
    
    # ──────────────────────────────────────────────
    # Entity contradiction auto-resolution
    # ──────────────────────────────────────────────
    
    def auto_resolve_transient_contradictions(self) -> Dict:
        """
        Auto-resolve transient entity contradictions.
        For attrs classified as 'transient' or 'accumulative': newest value wins.
        Contested contradictions are left for Kay.
        
        Returns stats.
        """
        eg = self.memory.entity_graph
        stats = {"resolved": 0, "contested_remaining": 0, "pruned_attrs": 0}
        
        for name, entity in eg.entities.items():
            if not hasattr(entity, 'contradiction_status'):
                continue
            
            for attr, status in list(entity.contradiction_status.items()):
                if status.get("resolved", False):
                    continue
                
                # Check severity — transient and accumulative get auto-resolved
                history = entity.attributes.get(attr, [])
                if len(history) < 2:
                    continue
                
                unique_values = {}
                for value, turn, source, timestamp in history:
                    hashable = entity._make_hashable(value)
                    if hashable not in unique_values:
                        unique_values[hashable] = []
                    unique_values[hashable].append((turn, source, timestamp))
                
                severity = entity._determine_contradiction_severity(attr, unique_values)
                
                if severity in ("transient", "accumulative"):
                    # Auto-resolve: keep only the most recent entry
                    if history:
                        newest = max(history, key=lambda h: h[3] if h[3] else "")
                        entity.attributes[attr] = [newest]
                        entity.contradiction_status[attr] = {
                            "resolved": True,
                            "canonical_value": newest[0],
                            "resolved_at_turn": newest[1],
                            "resolution_method": "auto_transient",
                        }
                        stats["resolved"] += 1
                elif severity in ("high", "moderate", "low"):
                    stats["contested_remaining"] += 1
        
        # Also prune old attribute history (>30 days) across all entities
        for name, entity in eg.entities.items():
            if hasattr(entity, 'prune_old_attribute_history'):
                pruned = entity.prune_old_attribute_history(max_age_days=30)
                stats["pruned_attrs"] += pruned
        
        # Save entity graph
        if stats["resolved"] > 0 or stats["pruned_attrs"] > 0:
            eg.save_to_file()
            self._state["contradictions_auto_resolved"] = (
                self._state.get("contradictions_auto_resolved", 0) + stats["resolved"]
            )
            self._save_state()
        
        log.info(f"[CURATION] Auto-resolved {stats['resolved']} transient contradictions, "
                 f"pruned {stats['pruned_attrs']} old attrs, "
                 f"{stats['contested_remaining']} contested remaining")
        
        return stats
    
    def get_contested_contradictions(self, limit: int = 5) -> List[Dict]:
        """Get contested contradictions for Kay to review."""
        eg = self.memory.entity_graph
        contested = []
        
        for name, entity in eg.entities.items():
            if not hasattr(entity, 'contradiction_status'):
                continue
            for attr, status in entity.contradiction_status.items():
                if status.get("resolved", False):
                    continue
                
                history = entity.attributes.get(attr, [])
                if len(history) < 2:
                    continue
                
                unique_values = {}
                for value, turn, source, timestamp in history:
                    hashable = entity._make_hashable(value)
                    if hashable not in unique_values:
                        unique_values[hashable] = []
                    unique_values[hashable].append((turn, source, timestamp))
                
                severity = entity._determine_contradiction_severity(attr, unique_values)
                if severity not in ("transient", "accumulative"):
                    recent_values = []
                    for v, t, s, ts in history[-5:]:
                        recent_values.append({"value": v, "turn": t, "source": s, "timestamp": ts})
                    
                    contested.append({
                        "entity": name,
                        "attribute": attr,
                        "severity": severity,
                        "values": recent_values,
                    })
        
        # Sort by severity (high first)
        severity_order = {"high": 0, "moderate": 1, "low": 2}
        contested.sort(key=lambda c: severity_order.get(c["severity"], 3))
        
        return contested[:limit]
    
    def format_contradiction_prompt(self, contradictions: List[Dict]) -> str:
        """Build prompt for Kay to resolve contested contradictions."""
        lines = []
        lines.append(f"You have {len(contradictions)} entity contradictions to resolve.")
        lines.append("For each, pick the correct/current value, or note if both are valid.")
        lines.append("")
        lines.append('Respond with ONLY a JSON array:')
        lines.append('  {"index": N, "correct_value": "the right value", "reason": "why"}')
        lines.append("")
        
        for i, c in enumerate(contradictions):
            lines.append(f"[{i}] {c['entity']}.{c['attribute']} (severity: {c['severity']})")
            for v in c["values"]:
                ts = v["timestamp"][:16] if v["timestamp"] else "?"
                lines.append(f"    → {v['value']} (source: {v['source']}, {ts})")
        
        lines.append("\nJSON response:")
        return "\n".join(lines)
    
    def apply_contradiction_resolutions(self, resolutions: List[Dict], contradictions: List[Dict]):
        """Apply Kay's contradiction resolutions."""
        eg = self.memory.entity_graph
        
        for res in resolutions:
            idx = res.get("index", -1)
            if 0 <= idx < len(contradictions):
                c = contradictions[idx]
                entity = eg.entities.get(c["entity"])
                if entity and c["attribute"] in entity.attributes:
                    correct = res.get("correct_value")
                    # Keep only matching entries + the newest
                    history = entity.attributes[c["attribute"]]
                    kept = [h for h in history if h[0] == correct]
                    if not kept:
                        # Value not found verbatim — keep newest
                        kept = [max(history, key=lambda h: h[3] if h[3] else "")]
                    entity.attributes[c["attribute"]] = kept
                    entity.contradiction_status[c["attribute"]] = {
                        "resolved": True,
                        "canonical_value": correct,
                        "resolution_method": "kay_judgment",
                        "reason": res.get("reason", ""),
                    }
                    
                    self._state["contradictions_kay_resolved"] = (
                        self._state.get("contradictions_kay_resolved", 0) + 1
                    )
                    self._log_decision({
                        "action": "contradiction_resolved",
                        "entity": c["entity"],
                        "attribute": c["attribute"],
                        "resolved_to": correct,
                        "reason": res.get("reason", ""),
                    })
        
        eg.save_to_file()
        self._save_state()
    
    # ──────────────────────────────────────────────
    # Approval queue (for Re)
    # ──────────────────────────────────────────────
    
    def get_pending_discards(self) -> List[Dict]:
        """Get memories queued for Re's discard approval."""
        return self._pending_discards
    
    def approve_discard(self, index: int) -> bool:
        """Re approves a discard — actually remove the memory."""
        if 0 <= index < len(self._pending_discards):
            item = self._pending_discards.pop(index)
            mem_ref = item.get("memory_ref")
            if mem_ref and mem_ref in self.memory.memory_layers.long_term_memory:
                self.memory.memory_layers.long_term_memory.remove(mem_ref)
                self.memory.memory_layers._save_to_disk()
            self._log_decision({"action": "discard_approved", "memory_id": item.get("memory_id")})
            self._save_pending()
            return True
        return False
    
    def reject_discard(self, index: int) -> bool:
        """Re rejects a discard — memory stays, remove from queue."""
        if 0 <= index < len(self._pending_discards):
            item = self._pending_discards.pop(index)
            self._log_decision({"action": "discard_rejected", "memory_id": item.get("memory_id")})
            self._save_pending()
            return True
        return False
    
    def approve_all_discards(self) -> int:
        """Approve all pending discards at once."""
        count = 0
        while self._pending_discards:
            if self.approve_discard(0):
                count += 1
        return count
    
    def reject_all_discards(self) -> int:
        """Reject all pending discards."""
        count = len(self._pending_discards)
        for item in self._pending_discards:
            self._log_decision({"action": "discard_rejected", "memory_id": item.get("memory_id")})
        self._pending_discards = []
        self._save_pending()
        return count
    
    # ──────────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────────
    
    def get_stats(self) -> str:
        """Get human-readable curation stats."""
        s = self._state
        pending = len(self._pending_discards)
        total_mems = len(self.memory.memory_layers.long_term_memory)
        reviewed = len(s.get("reviewed_ids", []))
        
        lines = [
            "=" * 50,
            "🧹 CURATION STATUS",
            "=" * 50,
            f"Sessions completed: {s.get('total_sessions', 0)}",
            f"Memories reviewed: {reviewed} / {total_mems}",
            f"Kept: {s.get('total_kept', 0)}  |  Compressed: {s.get('total_compressed', 0)}",
            f"Discards pending Re's approval: {pending}",
            f"Contradictions auto-resolved: {s.get('contradictions_auto_resolved', 0)}",
            f"Contradictions Kay resolved: {s.get('contradictions_kay_resolved', 0)}",
            "=" * 50,
        ]
        return "\n".join(lines)
    
    # Aliases for wrapper_bridge command handler compatibility
    def format_status(self) -> str:
        return self.get_stats()
    
    def format_pending_discards(self) -> str:
        """Format pending discards for display."""
        if not self._pending_discards:
            return "\n✅ No pending discards — nothing awaiting approval."
        lines = ["\n" + "="*60, f"🗑️ PENDING DISCARDS ({len(self._pending_discards)})", "="*60]
        for i, item in enumerate(self._pending_discards):
            lines.append(f"\n  [{i}] ({item.get('category', '?')})")
            lines.append(f"      {item.get('content_preview', '?')[:150]}")
            lines.append(f"      Reason: {item.get('reason', '?')}")
            lines.append(f"      Decided: {item.get('decided_at', '?')[:16]}")
        lines.append(f"\n  Use /memory approve <N> or /memory approve all")
        lines.append(f"  Use /memory reject <N> to keep a memory")
        lines.append("="*60)
        return "\n".join(lines)
