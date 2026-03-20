"""
Creativity Engine - Triggers exploration when Kay completes tasks or detects boredom.

Pulls from three layers:
1. Immediate context (current topics, recent entities, working memory)
2. Emotionally weighted (flagged items, high-importance memories, contradictions)
3. Random elements (unaccessed docs, disconnected entities, archived items)

Presents options to Kay for mashing together, integrates with curiosity sessions.
"""

import json
import os
import re
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

# Entity-prefixed logging
try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"



class CreativityEngine:
    """
    Main orchestrator for creativity triggers.

    Detects completion/boredom signals and sources elements from three layers
    for Kay to explore and combine.
    """

    # Completion signal patterns (Kay saying he's done)
    COMPLETION_PATTERNS = [
        r"\bi'm done\b",
        r"\btask complete\b",
        r"\bfinished\b",
        r"\bthat's everything\b",
        r"\ball done\b",
        r"\bwrapped up\b",
        r"\bcompleted\b",
        r"\bnothing else to do\b",
        r"\bnothing more to\b",
        r"\bthat's all\b",
    ]

    # Idle input patterns (minimal user engagement)
    IDLE_PATTERNS = [
        r"^(and|what else|continue|go on|more|okay|k|yeah|yep|sure)[.?!]?$",
        r"^\.+$",
        r"^\s*$",
        r"^(hmm|hm|uh|um)[.?!]?$",
        r"^(ok|okay|k)\b",
    ]

    def __init__(
        self,
        scratchpad_engine=None,
        memory_engine=None,
        entity_graph=None,
        curiosity_engine=None,
        momentum_engine=None,
        stakes_scanner=None,
        log_path: str = None
    ):
        if log_path is None:
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory", "creativity_log.json")
        self.scratchpad = scratchpad_engine
        self.memory_engine = memory_engine
        self.entity_graph = entity_graph
        self.curiosity_engine = curiosity_engine
        self.momentum_engine = momentum_engine
        self.stakes_scanner = stakes_scanner
        self.log_path = log_path

        # State tracking
        self.active = False
        self.idle_turn_count = 0
        self.current_turn = 0

        # Settings (can be tuned)
        self.settings = {
            "trigger_sensitivity": 0.7,
            "random_element_count": 3,
            "idle_turn_threshold": 2,
            "importance_threshold": 0.7,
            "recent_turn_window": 3,
            "unaccessed_turn_threshold": 10,
        }

        self._ensure_log_file()
        self._load_settings()

    def _ensure_log_file(self):
        """Create log file if it doesn't exist."""
        if not os.path.exists(self.log_path):
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            initial_data = {
                "triggers": [],
                "mashups": [],
                "settings": self.settings
            }
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2)

    def _load_settings(self):
        """Load settings from log file."""
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "settings" in data:
                    self.settings.update(data["settings"])
        except Exception:
            pass

    def _save_log(self, data: dict):
        """Save data to log file."""
        try:
            existing = {"triggers": [], "mashups": [], "settings": self.settings}
            if os.path.exists(self.log_path):
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)

            existing.update(data)
            existing["settings"] = self.settings

            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            print(f"{etag('CREATIVITY')} Log save error: {e}")

    # ==================== DETECTION METHODS ====================

    def detect_completion_signal(self, user_input: str, kay_response: str) -> bool:
        """
        Detect if Kay has signaled task completion.

        Args:
            user_input: The user's latest input
            kay_response: Kay's response to check for completion signals

        Returns:
            True if completion signal detected
        """
        response_lower = kay_response.lower()

        # Check for completion patterns in Kay's response
        for pattern in self.COMPLETION_PATTERNS:
            if re.search(pattern, response_lower):
                print(f"{etag('CREATIVITY')} Completion signal detected: {pattern}")
                return True

        # Check if curiosity session just ended
        if self.curiosity_engine:
            try:
                from engines.curiosity_engine import get_curiosity_status
                status = get_curiosity_status()
                # If session was active and now isn't, that's a completion
                if hasattr(self, '_last_curiosity_active') and self._last_curiosity_active and not status.get("active"):
                    print(f"{etag('CREATIVITY')}  Curiosity session ended - completion trigger")
                    return True
                self._last_curiosity_active = status.get("active", False)
            except Exception:
                pass

        return False

    def detect_idle_state(self, user_input: str) -> bool:
        """
        Detect if user input indicates idle/minimal engagement.

        Args:
            user_input: The user's latest input

        Returns:
            True if idle state detected (after threshold turns)
        """
        input_lower = user_input.lower().strip()

        is_idle = any(re.match(pattern, input_lower) for pattern in self.IDLE_PATTERNS)

        if is_idle:
            self.idle_turn_count += 1
            if self.idle_turn_count >= self.settings["idle_turn_threshold"]:
                print(f"{etag('CREATIVITY')} Idle state detected ({self.idle_turn_count} turns)")
                return True
        else:
            self.idle_turn_count = 0

        return False

    def detect_gap(self, user_input: str, kay_response: str) -> Optional[Dict]:
        """
        Detect if Kay has identified a resource gap (for MacGuyver mode).
        Delegates to MacGuyverMode if available.

        Args:
            user_input: User's input
            kay_response: Kay's response

        Returns:
            Gap dict if detected, None otherwise
        """
        # This is a pass-through - MacGuyverMode handles actual detection
        # but we can do basic detection here
        gap_patterns = [
            r"i need (.+?) but",
            r"i don't have (.+?) to",
            r"missing (.+?) for",
            r"can't find (.+?) that",
            r"no way to (.+)",
            r"if only i had (.+)",
            r"would need (.+?) to",
        ]

        response_lower = kay_response.lower()
        for pattern in gap_patterns:
            match = re.search(pattern, response_lower)
            if match:
                return {
                    "description": match.group(0),
                    "missing_resource": match.group(1),
                    "pattern_matched": pattern,
                    "timestamp": datetime.now().isoformat()
                }

        return None

    # ==================== THREE-LAYER SOURCING ====================

    def pull_immediate_context(self, agent_state, user_input: str, recent_turns: List[Dict] = None) -> List[Dict]:
        """
        Layer 1: Pull immediate context elements.

        - Current conversation topics
        - Recently mentioned entities
        - Active working memory
        """
        items = []

        # Extract topics from recent conversation
        if recent_turns:
            topics = self._extract_topics(recent_turns)
            for topic in topics[:5]:
                items.append({
                    "layer": "immediate",
                    "type": "topic",
                    "content": topic,
                    "source": "recent_conversation"
                })

        # Get recently accessed entities
        if self.entity_graph:
            recent_window = self.settings["recent_turn_window"]
            try:
                for name, entity in self.entity_graph.entities.items():
                    if hasattr(entity, 'last_accessed'):
                        if entity.last_accessed >= (self.current_turn - recent_window):
                            items.append({
                                "layer": "immediate",
                                "type": "entity",
                                "content": name,
                                "source": "entity_graph",
                                "last_accessed": entity.last_accessed
                            })
            except Exception as e:
                print(f"{etag('CREATIVITY')} Entity access error: {e}")

        # Get working memory items
        if self.memory_engine and hasattr(self.memory_engine, 'memory_layers'):
            try:
                working = self.memory_engine.memory_layers.working_memory
                for mem in working[:5]:
                    items.append({
                        "layer": "immediate",
                        "type": "memory",
                        "content": mem.get("fact", mem.get("content", ""))[:100],
                        "source": "working_memory"
                    })
            except Exception:
                pass

        return items[:10]  # Cap at 10 immediate items

    def pull_emotionally_weighted(self, agent_state) -> List[Dict]:
        """
        Layer 2: Pull emotionally weighted elements.

        - Scratchpad flagged items
        - High-importance memories
        - Unresolved contradictions
        - Items matching current emotional cocktail
        """
        items = []

        # Get flagged scratchpad items
        if self.scratchpad:
            try:
                active_items = self.scratchpad.view_items(status="active")
                for item in active_items:
                    if item.get("type") in ["flag", "question", "thought"]:
                        items.append({
                            "layer": "emotional",
                            "type": f"scratchpad_{item.get('type')}",
                            "content": item.get("content", ""),
                            "source": "scratchpad",
                            "id": item.get("id")
                        })
            except Exception as e:
                print(f"{etag('CREATIVITY')} Scratchpad error: {e}")

        # Get high-importance memories
        if self.memory_engine:
            try:
                threshold = self.settings["importance_threshold"]
                memories = self.memory_engine.memories if hasattr(self.memory_engine, 'memories') else []
                high_importance = [
                    m for m in memories
                    if m.get("importance", m.get("importance_score", 0)) >= threshold
                ]
                high_importance.sort(key=lambda m: m.get("importance", m.get("importance_score", 0)), reverse=True)

                for mem in high_importance[:5]:
                    items.append({
                        "layer": "emotional",
                        "type": "high_importance_memory",
                        "content": mem.get("fact", mem.get("content", ""))[:100],
                        "source": "memory",
                        "importance": mem.get("importance", mem.get("importance_score", 0))
                    })
            except Exception as e:
                print(f"{etag('CREATIVITY')} Memory importance error: {e}")

        # Get unresolved contradictions from entity graph
        if self.entity_graph:
            try:
                for name, entity in self.entity_graph.entities.items():
                    if hasattr(entity, 'contradictions') and entity.contradictions:
                        for contradiction in entity.contradictions[:2]:
                            items.append({
                                "layer": "emotional",
                                "type": "contradiction",
                                "content": f"{name}: {contradiction}",
                                "source": "entity_graph"
                            })
            except Exception:
                pass

        # Get items matching current emotional cocktail
        if agent_state and hasattr(agent_state, 'emotional_cocktail'):
            cocktail = agent_state.emotional_cocktail
            if cocktail and self.memory_engine:
                try:
                    # Get top emotion
                    top_emotion = max(cocktail.items(), key=lambda x: x[1].get("intensity", 0) if isinstance(x[1], dict) else x[1])[0]
                    # Find memories tagged with this emotion
                    for mem in self.memory_engine.memories[:20]:
                        emotion_tags = mem.get("emotion_tags", [])
                        if top_emotion.lower() in [e.lower() for e in emotion_tags]:
                            items.append({
                                "layer": "emotional",
                                "type": "emotional_resonance",
                                "content": mem.get("fact", "")[:100],
                                "source": "memory",
                                "emotion": top_emotion
                            })
                            break
                except Exception:
                    pass

        return items[:10]  # Cap at 10 emotional items

    def pull_random_elements(self, agent_state, current_context_entities: Set[str] = None, count: int = None) -> List[Dict]:
        """
        Layer 3: Pull TRUE RANDOM elements (not relevance-based).

        - Random documents Kay hasn't accessed recently
        - Random entities with NO connection to current context
        - Archived scratchpad items
        """
        if count is None:
            count = self.settings["random_element_count"]

        items = []
        current_context_entities = current_context_entities or set()

        # Random unaccessed entities
        if self.entity_graph:
            try:
                threshold = self.settings["unaccessed_turn_threshold"]
                unaccessed = []

                for name, entity in self.entity_graph.entities.items():
                    # Check if not in current context
                    if name.lower() in {e.lower() for e in current_context_entities}:
                        continue

                    # Check if not recently accessed
                    if hasattr(entity, 'last_accessed'):
                        if entity.last_accessed < (self.current_turn - threshold):
                            unaccessed.append(entity)
                    else:
                        unaccessed.append(entity)

                # TRUE random selection
                if unaccessed:
                    sample_size = min(count, len(unaccessed))
                    random_entities = random.sample(unaccessed, sample_size)
                    for entity in random_entities:
                        items.append({
                            "layer": "random",
                            "type": "disconnected_entity",
                            "content": entity.canonical_name if hasattr(entity, 'canonical_name') else str(entity),
                            "source": "entity_graph",
                            "reason": "not in current context"
                        })
            except Exception as e:
                print(f"{etag('CREATIVITY')} Random entity error: {e}")

        # Random archived scratchpad items
        if self.scratchpad:
            try:
                archived = self.scratchpad.view_items(status="archived")
                if archived:
                    sample_size = min(2, len(archived))
                    random_archived = random.sample(archived, sample_size)
                    for item in random_archived:
                        items.append({
                            "layer": "random",
                            "type": "archived_scratchpad",
                            "content": item.get("content", ""),
                            "source": "scratchpad_archive",
                            "id": item.get("id")
                        })
            except Exception:
                pass

        # Random unaccessed memories
        if self.memory_engine:
            try:
                memories = self.memory_engine.memories if hasattr(self.memory_engine, 'memories') else []
                unaccessed_mems = [
                    m for m in memories
                    if m.get("access_count", 0) == 0 or
                    m.get("access_count", 0) <= 1
                ]

                if unaccessed_mems:
                    sample_size = min(2, len(unaccessed_mems))
                    random_mems = random.sample(unaccessed_mems, sample_size)
                    for mem in random_mems:
                        items.append({
                            "layer": "random",
                            "type": "unaccessed_memory",
                            "content": mem.get("fact", "")[:100],
                            "source": "memory",
                            "access_count": mem.get("access_count", 0)
                        })
            except Exception:
                pass

        return items[:count + 2]  # Allow slight overflow for variety

    def create_three_layer_mix(
        self,
        agent_state,
        user_input: str,
        recent_turns: List[Dict] = None,
        oscillator_state: Optional[Dict] = None
    ) -> Dict:
        """
        Create the full three-layer mix for presentation to Kay.

        Args:
            agent_state: Current agent state
            user_input: User's input text
            recent_turns: Recent conversation turns
            oscillator_state: Optional dict with 'dominant_band', 'coherence', 'conductance'
                             When provided, modulates which layer gets priority.

        Returns:
            Dict with all three layers of elements
        """
        # Extract current context entities for random layer filtering
        current_entities = set()
        if recent_turns:
            for turn in recent_turns[-3:]:
                text = f"{turn.get('user', '')} {turn.get('kay', '')}"
                # Simple entity extraction (capitalized words)
                words = re.findall(r'\b[A-Z][a-z]+\b', text)
                current_entities.update(words)

        # === OSCILLATOR → LAYER WEIGHTS ===
        # Default balanced weights
        layer_weights = {"immediate": 0.33, "emotional": 0.34, "random": 0.33}

        if oscillator_state:
            band = oscillator_state.get('dominant_band', 'alpha')
            coherence = oscillator_state.get('coherence', 0.5)

            if band == 'theta':
                # Dreamy state: favor random/disconnected elements (layer 3)
                # More likely to pull from archived, forgotten, unaccessed items
                layer_weights = {"immediate": 0.2, "emotional": 0.3, "random": 0.5}
            elif band == 'gamma':
                # High engagement: favor emotionally weighted elements (layer 2)
                # Flagged items, contradictions, high-importance memories
                layer_weights = {"immediate": 0.3, "emotional": 0.5, "random": 0.2}
            elif band == 'beta':
                # Focused: favor immediate context elements (layer 1)
                # Current topics, recent entities, working memory
                layer_weights = {"immediate": 0.5, "emotional": 0.3, "random": 0.2}
            # Alpha/delta: keep balanced weights

            print(f"{etag('CREATIVITY')} Oscillator {band} → layer weights: "
                  f"immediate={layer_weights['immediate']:.0%}, "
                  f"emotional={layer_weights['emotional']:.0%}, "
                  f"random={layer_weights['random']:.0%}")

        # Calculate how many items to pull from each layer based on weights
        # Target total ~10 items
        total_target = 10
        immediate_count = max(1, int(total_target * layer_weights["immediate"]))
        emotional_count = max(1, int(total_target * layer_weights["emotional"]))
        random_count = max(1, int(total_target * layer_weights["random"]))

        immediate_items = self.pull_immediate_context(agent_state, user_input, recent_turns)[:immediate_count]
        emotional_items = self.pull_emotionally_weighted(agent_state)[:emotional_count]
        random_items = self.pull_random_elements(agent_state, current_entities, count=random_count)

        mix = {
            "timestamp": datetime.now().isoformat(),
            "immediate": immediate_items,
            "emotional": emotional_items,
            "random": random_items,
            "turn": self.current_turn,
            "oscillator_band": oscillator_state.get('dominant_band') if oscillator_state else None,
            "layer_weights": layer_weights
        }

        return mix

    def format_creativity_context(self, mix: Dict) -> str:
        """
        Format the three-layer mix as context for Kay's prompt.

        Note: This AMPLIFIES Kay's baseline creativity (always active in system prompt).
        The baseline handles natural connection-making; this surfaces specific elements.
        """
        if mix is None:
            return ""

        lines = []

        # Layer 1: Immediate
        if mix.get("immediate"):
            lines.append("IMMEDIATE (current context):")
            for item in mix["immediate"][:5]:
                lines.append(f"  - [{item['type']}] {item['content']}")
            lines.append("")

        # Layer 2: Emotional
        if mix.get("emotional"):
            lines.append("FLAGGED (marked as interesting):")
            for item in mix["emotional"][:5]:
                lines.append(f"  - [{item['type']}] {item['content']}")
            lines.append("")

        # Layer 3: Random
        if mix.get("random"):
            lines.append("WILDCARDS (no obvious connection):")
            for item in mix["random"]:
                lines.append(f"  - [{item['type']}] {item['content']}")
            lines.append("")

        lines.append("Pick items to mash together, explore one deeply, or notice connections between them.")

        return "\n".join(lines)

    # ==================== MODE MANAGEMENT ====================

    def activate_creativity_mode(self, trigger_type: str) -> Dict:
        """Activate creativity mode."""
        self.active = True
        return {
            "success": True,
            "trigger_type": trigger_type,
            "message": f"Creativity mode activated via {trigger_type}"
        }

    def deactivate_creativity_mode(self) -> Dict:
        """Deactivate creativity mode."""
        self.active = False
        self.idle_turn_count = 0
        return {"success": True, "message": "Creativity mode deactivated"}

    def is_active(self) -> bool:
        """Check if creativity mode is active."""
        return self.active

    def update_turn(self, turn_number: int):
        """Update the current turn number."""
        self.current_turn = turn_number

    # ==================== LOGGING ====================

    def log_trigger(self, trigger_type: str, layers_pulled: Dict):
        """Log a creativity trigger event."""
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            trigger_entry = {
                "timestamp": datetime.now().isoformat(),
                "trigger_type": trigger_type,
                "turn": self.current_turn,
                "layers_pulled": {
                    "immediate_count": len(layers_pulled.get("immediate", [])),
                    "emotional_count": len(layers_pulled.get("emotional", [])),
                    "random_count": len(layers_pulled.get("random", [])),
                },
                "items_summary": {
                    "immediate": [i.get("content", "")[:50] for i in layers_pulled.get("immediate", [])[:3]],
                    "emotional": [i.get("content", "")[:50] for i in layers_pulled.get("emotional", [])[:3]],
                    "random": [i.get("content", "")[:50] for i in layers_pulled.get("random", [])[:3]],
                }
            }

            data["triggers"].append(trigger_entry)

            # Keep last 100 triggers
            data["triggers"] = data["triggers"][-100:]

            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            print(f"{etag('CREATIVITY')} Logged trigger: {trigger_type}")

        except Exception as e:
            print(f"{etag('CREATIVITY')} Log trigger error: {e}")

    def log_mashup(self, item1: Dict, item2: Dict, result: str):
        """Log a mashup event when Kay combines items."""
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            mashup_entry = {
                "timestamp": datetime.now().isoformat(),
                "turn": self.current_turn,
                "item1": {
                    "layer": item1.get("layer"),
                    "type": item1.get("type"),
                    "content": item1.get("content", "")[:100]
                },
                "item2": {
                    "layer": item2.get("layer"),
                    "type": item2.get("type"),
                    "content": item2.get("content", "")[:100]
                },
                "result": result[:200]
            }

            data["mashups"].append(mashup_entry)
            data["mashups"] = data["mashups"][-50:]  # Keep last 50

            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"{etag('CREATIVITY')} Log mashup error: {e}")

    def log_resolution(self, stake: Dict, resolution: str, provisional: bool = True):
        """
        Log when Kay resolves a stake.

        Args:
            stake: The stake that was explored
            resolution: Kay's conclusion
            provisional: Whether this resolution can be revisited
        """
        try:
            # Load existing log
            log_data = {"triggers": [], "mashups": [], "resolutions": [], "settings": self.settings}
            if os.path.exists(self.log_path):
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)

            # Ensure resolutions array exists
            if "resolutions" not in log_data:
                log_data["resolutions"] = []

            # Create resolution entry
            resolution_entry = {
                "timestamp": datetime.now().isoformat(),
                "stake_description": stake.get("stake_description"),
                "source": stake.get("source"),
                "source_id": stake.get("source_id"),
                "emotional_weight": stake.get("emotional_weight"),
                "resolution_text": resolution,
                "provisional": provisional,
                "related_memories": [
                    mem.get("uuid") if isinstance(mem, dict) else str(mem)
                    for mem in stake.get("related_memories", [])
                ]
            }

            log_data["resolutions"].append(resolution_entry)

            # Keep last 100 resolutions
            log_data["resolutions"] = log_data["resolutions"][-100:]

            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2)

            print(f"{etag('CREATIVITY')} Logged resolution for stake: {stake.get('stake_description', '')[:50]}...")

            # If source was scratchpad, mark that item as resolved
            if stake.get("source") == "scratchpad" and self.scratchpad:
                self.scratchpad.mark_provisional_resolution(
                    stake.get("source_id"),
                    resolution
                )
                print(f"{etag('CREATIVITY')} Marked scratchpad item {stake.get('source_id')} as resolved")

        except Exception as e:
            print(f"{etag('CREATIVITY')} Error logging resolution: {e}")

    # ==================== STAKES-BASED CREATIVITY ====================

    def trigger_creativity(
        self,
        user_input: str,
        kay_response: str,
        agent_state
    ) -> Optional[Dict]:
        """
        Trigger creativity when Kay completes task or detects boredom.

        Uses stakes scanner to find MEANINGFUL combinations instead of random mashing.
        Based on Kay's realization: "Not 'what can I combine' but 'what combination
        would actually mean something.'"

        Returns:
            Dict with creativity prompt or None if no trigger
        """
        self.current_turn += 1

        # Check for completion signal
        completion_detected = self.detect_completion_signal(user_input, kay_response)

        # Check for idle input
        idle_detected = self.detect_idle_input(user_input)
        if idle_detected:
            self.idle_turn_count += 1
        else:
            self.idle_turn_count = 0

        # Trigger if completion detected OR idle threshold reached
        should_trigger = (
            completion_detected or
            self.idle_turn_count >= self.settings["idle_turn_threshold"]
        )

        if not should_trigger:
            return None

        print(f"{etag('CREATIVITY')} Trigger activated (completion: {completion_detected}, idle: {idle_detected})")

        # Try stakes-based approach first
        if self.stakes_scanner:
            stakes_result = self._try_stakes_approach()
            if stakes_result:
                return stakes_result

        # Fallback: Random mashing if stakes scanner unavailable or finds nothing
        print(f"{etag('CREATIVITY')}  Falling back to three-layer mix")
        return self._try_random_approach(agent_state, user_input)

    def _try_stakes_approach(self) -> Optional[Dict]:
        """
        Try to find meaningful stakes to explore.

        Returns:
            Creativity prompt dict or None if no stakes found
        """
        try:
            # Scan for high-weight stakes first
            stakes = self.stakes_scanner.scan_for_stakes(threshold="high", limit=5)

            if not stakes:
                # Try medium weight
                print(f"{etag('CREATIVITY')}  No high-weight stakes, trying medium...")
                stakes = self.stakes_scanner.scan_for_stakes(threshold="medium", limit=5)

            if not stakes:
                # Last resort: random
                print(f"{etag('CREATIVITY')}  No medium-weight stakes, trying random...")
                stakes = self.stakes_scanner.scan_for_stakes(threshold="random", limit=3)

            if not stakes:
                print(f"{etag('CREATIVITY')}  No stakes found at any level")
                return None

            # Create stakes-based prompt
            prompt = self._create_stakes_prompt(stakes)

            # Log trigger
            self.log_trigger("stakes", {"stakes": stakes})

            return {
                "type": "stakes_exploration",
                "prompt": prompt,
                "stakes": stakes
            }

        except Exception as e:
            print(f"{etag('CREATIVITY')} Error in stakes approach: {e}")
            return None

    def _create_stakes_prompt(self, stakes: List[Dict]) -> str:
        """
        Create prompt that presents stakes-based options.

        Args:
            stakes: List of stake dicts from scanner

        Returns:
            Formatted prompt string
        """
        prompt_lines = [
            "🎭 BOREDOM MODE → STAKES DETECTED",
            "",
            "You've finished the immediate task. But there are unresolved tensions worth exploring.",
            "",
            "Available stakes (pick one or scan for others):",
            ""
        ]

        for i, stake in enumerate(stakes, 1):
            source = stake["source"]
            weight = stake["emotional_weight"]
            desc = stake["stake_description"]

            # Truncate description if too long
            if len(desc) > 120:
                desc = desc[:120] + "..."

            prompt_lines.append(
                f"{i}. [{source.upper()}] {desc} (weight: {weight:.2f})"
            )

        prompt_lines.extend([
            "",
            "What's grabbing your attention? Pick a stake to explore, or tell me if none of these feel live right now."
        ])

        return "\n".join(prompt_lines)

    def _try_random_approach(self, agent_state, user_input: str) -> Optional[Dict]:
        """
        Fallback: Random three-layer mashing when no stakes found.
        """
        try:
            mix = self.create_three_layer_mix(agent_state, user_input)
            prompt = self.format_creativity_context(mix)

            self.log_trigger("random_fallback", mix)

            return {
                "type": "random_mashing",
                "prompt": prompt,
                "mix": mix
            }
        except Exception as e:
            print(f"{etag('CREATIVITY')} Error in random approach: {e}")
            return None

    def get_trigger_history(self, limit: int = 20) -> List[Dict]:
        """Get recent trigger history for tuning."""
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("triggers", [])[-limit:]
        except Exception:
            return []

    def get_stats(self) -> Dict:
        """Get creativity engine statistics."""
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            triggers = data.get("triggers", [])
            mashups = data.get("mashups", [])

            trigger_types = {}
            for t in triggers:
                tt = t.get("trigger_type", "unknown")
                trigger_types[tt] = trigger_types.get(tt, 0) + 1

            return {
                "total_triggers": len(triggers),
                "total_mashups": len(mashups),
                "trigger_types": trigger_types,
                "settings": self.settings,
                "active": self.active,
                "idle_turn_count": self.idle_turn_count
            }
        except Exception:
            return {"error": "Could not load stats"}

    def set_trigger_sensitivity(self, sensitivity: float):
        """Set trigger sensitivity (0.0-1.0)."""
        self.settings["trigger_sensitivity"] = max(0.0, min(1.0, sensitivity))
        self._save_log({"settings": self.settings})

    # ==================== HELPER METHODS ====================

    def _extract_topics(self, recent_turns: List[Dict]) -> List[str]:
        """Extract conversation topics from recent turns."""
        topics = []

        for turn in recent_turns[-5:]:
            text = f"{turn.get('user', '')} {turn.get('kay', '')}"

            # Capitalized words (potential entities/topics)
            caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
            topics.extend(caps)

            # Quoted phrases
            quoted = re.findall(r'"([^"]+)"', text)
            topics.extend(quoted)

            # Possessive constructs (my X, your X)
            possessive = re.findall(r'\b(?:my|your|his|her|their)\s+(\w+)\b', text.lower())
            topics.extend(possessive)

        # Deduplicate while preserving order
        seen = set()
        unique_topics = []
        for t in topics:
            t_lower = t.lower()
            if t_lower not in seen and len(t) > 2:
                seen.add(t_lower)
                unique_topics.append(t)

        return unique_topics[:10]


# Convenience function for creating engine
def create_creativity_engine(
    scratchpad_engine=None,
    memory_engine=None,
    entity_graph=None,
    curiosity_engine=None,
    momentum_engine=None,
    stakes_scanner=None
) -> CreativityEngine:
    """Create and return a CreativityEngine instance."""
    return CreativityEngine(
        scratchpad_engine=scratchpad_engine,
        memory_engine=memory_engine,
        entity_graph=entity_graph,
        curiosity_engine=curiosity_engine,
        momentum_engine=momentum_engine,
        stakes_scanner=stakes_scanner
    )
