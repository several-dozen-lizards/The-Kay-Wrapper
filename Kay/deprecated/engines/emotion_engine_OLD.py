# engines/emotion_engine.py
import os
import re
import csv

class EmotionEngine:
    """
    Emotion engine that uses ULTRAMAP rules to update intensities,
    decay, mutation, body chemistry, and social feedback.
    Now includes trigger detection to seed emotions from user input.
    """

    # ULTRAMAP Emotion Categories (based on dimensional emotion theory)
    ULTRAMAP_CATEGORIES = {
        "stimulation": ["curiosity", "excitement", "surprise", "anxiety", "fear", "arousal", "playfulness"],
        "affection": ["affection", "love", "compassion", "empathy", "kindness", "gratitude", "warmth"],
        "power": ["pride", "confidence", "arrogance", "hubris", "triumph", "dominance", "ambition"],
        "submission": ["inferiority", "shame", "humiliation", "resignation", "failure", "inadequacy"],
        "stability": ["neutral", "calm", "peace", "serenity", "contentment", "balance"],
        "expression": ["joy", "happiness", "ecstasy", "bliss", "marvel", "awe (sublime)", "wonder"],
        "suppression": ["sadness", "grief", "sorrow", "longing", "nostalgia", "heartbreak", "melancholy"],
        "approach": ["desire", "lust", "craving", "infatuation", "obsession", "addiction (pleasure)", "compulsion (pleasure)"],
        "avoidance": ["anger", "frustration", "resentment", "disgust", "contempt", "rivalry", "antagonism"],
        "confusion": ["confusion", "ambiguity", "uncertainty", "disorientation", "bewilderment"],
        "clarity": ["insight", "recognition", "understanding", "revelation", "analysis", "meta-cognition"],
        "connection": ["union", "belonging", "home", "unity", "intimacy", "support", "togetherness"],
        "isolation": ["loneliness", "alienation", "abandonment", "rejection", "suffocation", "stagnation"],
        "transcendence": ["nirvana", "transcendence", "sanctity", "redemption", "healing", "forgiveness"],
        "performance": ["performance", "banter", "wit", "sarcasm", "playfulness", "humor"],
        "authenticity": ["honesty", "sincerity", "confession", "vulnerability", "expression", "truth"],
        "mystery": ["mystery (cosmic)", "awe", "imagination", "intuition", "ambiguity"],
        "willpower": ["willpower", "resilience", "determination", "motivation", "perseverance"]
    }

    def __init__(self, protocol_engine,
                 trigger_file="data/Emotion_Mapping_Kay_ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv",
                 momentum_engine=None):
        self.protocol = protocol_engine
        self.trigger_file = trigger_file
        self.momentum_engine = momentum_engine
        self.triggers = self._load_triggers()

    # ------------------------------------------------------------------
    # Trigger parsing
    # ------------------------------------------------------------------
    def _load_triggers(self):
        """Load emotion triggers from ULTRAMAP CSV."""
        if not os.path.exists(self.trigger_file):
            return {}
        triggers = {}
        try:
            with open(self.trigger_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    emo = row.get("Emotion") or row.get("emotion") or None
                    logic = row.get("Trigger Condition (Formula/Logic)", "")
                    if emo and logic:
                        triggers[emo.lower()] = logic
        except Exception as e:
            print(f"(Trigger load error: {e})")
        return triggers

    def _detect_triggers(self, user_input: str):
        """Return list of emotions whose trigger keywords appear in input."""
        if not user_input:
            return []
        text = user_input.lower()
        hits = []
        # Look in loaded triggers first
        for emo, cond in self.triggers.items():
            parts = re.split(r"[|,;/]", cond)
            for p in parts:
                tok = p.strip().lower()
                if tok and tok in text:
                    hits.append(emo)
                    break
        # EXPANDED fallback emotion keywords (word-based, not exact phrases)
        fallback = {
            # Positive emotions
            "joy": ["happy", "excited", "wonderful", "great", "amazing", "beautiful", "perfect", "fantastic", "yay", "awesome"],
            "affection": ["love", "like", "miss", "dear", "care", "cherish", "adore", "fond", "appreciate"],
            "gratitude": ["thank", "thanks", "grateful", "appreciate", "blessing", "fortunate"],
            "amusement": ["funny", "funniest", "funnier", "hilarious", "laugh", "haha", "lol", "humor", "joke", "giggle", "chuckle"],
            "curiosity": ["wonder", "how", "why", "what if", "curious", "interesting", "question", "explore"],
            "pride": ["proud", "accomplished", "achieved", "success", "did it", "nailed"],
            "relief": ["relief", "relieved", "phew", "finally", "glad", "whew"],
            "excitement": ["excited", "can't wait", "thrilled", "pumped", "hyped", "stoked"],
            "contentment": ["content", "peaceful", "calm", "serene", "comfortable", "satisfied"],

            # Negative emotions
            "grief": ["miss", "lost", "gone", "died", "death", "mourning", "mourn", "passed", "rip"],
            "longing": ["wish", "want", "need", "crave", "yearn", "desire", "hope"],
            "anger": ["angry", "mad", "furious", "pissed", "rage", "unreasonable", "frustrating", "irritated"],
            "resentment": ["resent", "bitter", "unfair", "why me", "always", "never", "grudge"],
            "anxiety": ["worried", "anxious", "nervous", "scared", "fear", "afraid", "panic", "stress"],
            "frustration": ["frustrated", "frustrating", "annoying", "irritating", "ugh", "stuck", "can't", "won't"],
            "sadness": ["sad", "unhappy", "down", "depressed", "blue", "crying", "tears", "sorrow"],
            "shame": ["ashamed", "embarrassed", "humiliated", "guilty", "regret", "mortified"],
            "confusion": ["confused", "don't understand", "what", "huh", "unclear", "lost"],
            "disappointment": ["disappointed", "let down", "expected", "hoped", "failed"],
            "concern": ["concerned", "worried", "trouble", "problem", "issue", "worry"],
        }

        # Word-based matching: split text into words for better detection
        text_words = set(text.split())

        for emo, keywords in fallback.items():
            for keyword in keywords:
                # Match if keyword is a whole word OR appears as substring
                # This catches "miss" in "miss Sammie" AND "missing"
                if keyword in text_words or keyword in text:
                    hits.append(emo)
                    break  # Only count each emotion once per turn
        return list(set(hits))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _parse_neurochem(self, desc: str):
        mapping = {}
        if not desc or not isinstance(desc, str):
            return mapping
        parts = [p.strip() for p in re.split(r"[;,]", desc)]
        for part in parts:
            m = re.match(r"(High|Low|Baseline|No)\s+(\w+)", part, re.IGNORECASE)
            if m:
                level, chem = m.groups()
                chem = chem.lower()
                delta = {"high": 0.1, "low": -0.1}.get(level.lower(), 0.0)
                mapping[chem] = mapping.get(chem, 0.0) + delta
        return mapping

    def _apply_suppress_amplify(self, cocktail, rule: str):
        if not rule or not isinstance(rule, str):
            return
        for part in rule.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                name, val = part.split(":")
                delta = float(val)
                if name in cocktail:
                    cocktail[name]["intensity"] = max(
                        0.0, min(1.0, cocktail[name]["intensity"] + delta)
                    )
            except Exception:
                continue

    def detect_salient_emotions(self, cocktail):
        """
        Identify statistically salient emotions per category.

        Breaks the 77-emotion feedback loop by filtering to only emotions
        that are statistical outliers within their category.

        Returns:
            List of salient emotion names
        """
        # Calculate global arousal for dynamic k
        total_emotions = len([e for e in cocktail.values() if e.get("intensity", 0) > 0.05])
        if total_emotions == 0:
            return []

        global_arousal = sum(e.get("intensity", 0) for e in cocktail.values()) / max(1, total_emotions)
        k = 1.5 + (global_arousal * 1.5)  # k ranges from 1.5 (low arousal) to 3.0 (high arousal)

        print(f"[SALIENCE] Global arousal: {global_arousal:.2f} (k={k:.2f})")

        salient = []

        for category, emotions in self.ULTRAMAP_CATEGORIES.items():
            # Get active emotions in this category
            active = [e for e in emotions if e in cocktail and cocktail[e].get("intensity", 0) > 0.15]

            if len(active) < 2:  # Skip categories with <2 active emotions
                continue

            # Calculate statistics
            intensities = [cocktail[e].get("intensity", 0) for e in active]
            mean = sum(intensities) / len(intensities)
            variance = sum((x - mean)**2 for x in intensities) / len(intensities)
            std_dev = variance ** 0.5

            # Detect outliers (emotions above threshold)
            threshold = mean + (k * std_dev)
            category_salient = []
            for emotion in active:
                if cocktail[emotion].get("intensity", 0) > threshold:
                    salient.append(emotion)
                    category_salient.append(emotion)

            if category_salient:
                print(f"[SALIENCE] {category.capitalize()}: {len(category_salient)} salient ({', '.join(category_salient)})")

        print(f"[SALIENCE] Total salient: {len(salient)} emotions (statistical)")

        # NEW: Baseline floor - if no salient emotions, keep strongest 1-2
        # This prevents Kay from being pruned to 0 emotions when nothing meets statistical threshold
        if len(salient) == 0 and len(cocktail) > 0:
            # Sort all emotions by intensity
            sorted_emotions = sorted(
                cocktail.items(),
                key=lambda x: x[1].get("intensity", 0),
                reverse=True
            )

            # Keep top 1-2 strongest (whichever are closest in intensity)
            if len(sorted_emotions) >= 2:
                top_two = sorted_emotions[:2]
                # If top two are within 0.1 intensity of each other, keep both
                if abs(top_two[0][1].get("intensity", 0) - top_two[1][1].get("intensity", 0)) <= 0.1:
                    salient = [top_two[0][0], top_two[1][0]]
                else:
                    salient = [top_two[0][0]]
            else:
                salient = [sorted_emotions[0][0]]

            print(f"[SALIENCE] No statistical outliers - keeping baseline: {salient}")

        return salient

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------
    def update(self, agent_state, user_input):
        print("\n[EMOTION ENGINE] ========== UPDATE START ==========")
        print(f"[EMOTION ENGINE] User input: '{user_input[:80]}...'")

        cocktail = agent_state.emotional_cocktail or {}
        print(f"[EMOTION ENGINE] Initial cocktail: {list(cocktail.keys())} ({len(cocktail)} emotions)")
        for emo, data in sorted(cocktail.items(), key=lambda x: x[1].get('intensity', 0), reverse=True):
            print(f"[EMOTION ENGINE]   - {emo}: intensity={data.get('intensity', 0):.2f}, age={data.get('age', 0)}")

        # --- 1. detect new triggers from user input ---
        new_emotions = self._detect_triggers(user_input)
        print(f"[EMOTION ENGINE] Detected triggers: {new_emotions}")
        for emo in new_emotions:
            if emo not in cocktail:
                cocktail[emo] = {"intensity": 0.4, "age": 0}
                print(f"[EMOTION ENGINE]   -> NEW: {emo} at intensity 0.4")
            else:
                old_intensity = cocktail[emo]["intensity"]
                cocktail[emo]["intensity"] = min(1.0, cocktail[emo]["intensity"] + 0.2)
                print(f"[EMOTION ENGINE]   -> REINFORCED: {emo} from {old_intensity:.2f} to {cocktail[emo]['intensity']:.2f}")

        # fallback baseline
        if not cocktail:
            cocktail["neutral"] = {"intensity": 0.1, "age": 0}
            print(f"[EMOTION ENGINE] No emotions detected - adding neutral fallback")

        # --- 2. update existing states ---
        for emo, state in list(cocktail.items()):
            proto = self.protocol.get(emo) or {}
            base_decay = float(proto.get("DecayRate", 0.05))
            temporal = float(proto.get("Temporal Weight", 1.0) or 1.0)
            duration = float(proto.get("Duration Sensitivity", 1.0) or 1.0)
            decay = base_decay / max(0.1, (temporal * duration))

            mutate_to = proto.get("MutationTarget") or proto.get("Escalation/Mutation Protocol")
            mutate_threshold = float(proto.get("MutationThreshold", 0.9))
            social_bias = float(proto.get("SocialEffect", 0))
            body_map = proto.get("BodyChem", {}) or self._parse_neurochem(proto.get("Neurochemical Release", ""))
            ethical_bias = float(proto.get("EthicalWeight", 0))

            # Decay and age (with momentum modifier)
            # High-momentum emotions decay slower
            momentum_modifier = 1.0
            if self.momentum_engine:
                high_momentum_emotions = self.momentum_engine.get_high_momentum_emotions()
                if emo in high_momentum_emotions:
                    # Reduce decay by up to 70% based on momentum
                    momentum_modifier = 0.3 + (0.7 * (1.0 - agent_state.momentum))

            adjusted_decay = decay * momentum_modifier
            old_intensity = state.get("intensity", 0)
            state["intensity"] = max(0.0, state.get("intensity", 0) - adjusted_decay)
            state["age"] = state.get("age", 0) + 1
            print(f"[EMOTION ENGINE] Aged {emo}: {old_intensity:.3f} -> {state['intensity']:.3f} (age {state['age']}, decay={adjusted_decay:.3f})")

            # Mutation
            if mutate_to and state["intensity"] > mutate_threshold:
                cocktail[mutate_to] = {"intensity": state["intensity"] * 0.5, "age": 0}

            # Social influence
            sneed = agent_state.social["needs"].get("social", 0.5) + social_bias * state["intensity"]
            agent_state.social["needs"]["social"] = max(0, min(1, sneed))

            # Body chemistry mapping
            for chem, scale in (body_map or {}).items():
                current = agent_state.body.get(chem, 0.5)
                agent_state.body[chem] = max(0, min(1, current + scale * state["intensity"]))

            # Ethical damping
            state["intensity"] *= max(0, 1 - ethical_bias)

            # Suppress/Amplify
            self._apply_suppress_amplify(cocktail, proto.get("Suppress/Amplify", ""))

            # Emergency ritual
            if state["intensity"] > 0.9 and proto.get("Emergency Ritual/Output When System Collapses"):
                agent_state.context["emergency_ritual"] = proto["Emergency Ritual/Output When System Collapses"]

        # --- 3. reinforce via memory (RELEVANCE-WEIGHTED) ---
        all_memories = agent_state.last_recalled_memories or []

        # STEP 1: Sort by relevance and take top N most relevant
        relevant_memories = sorted(
            all_memories,
            key=lambda m: m.get('relevance_score', 0),
            reverse=True
        )[:150]  # Top 150 memories only (was: all ~310)

        # NOTE: Scores are PRE-NORMALIZED to 0-1 by memory_engine.py
        # No need to normalize again - use relevance_score directly
        if relevant_memories:
            max_score = max(m.get('relevance_score', 0) for m in relevant_memories)
            min_score = min(m.get('relevance_score', 0) for m in relevant_memories)
            print(f"[EMOTION ENGINE] Memory reinforcement: using top {len(relevant_memories)}/{len(all_memories)} most relevant memories")
            print(f"[EMOTION ENGINE] Score range (pre-normalized by memory_engine): {min_score:.3f} to {max_score:.3f}")

        # STEP 2: Boost emotions weighted by relevance
        reinforced_emotions = {}  # Track {emotion: total_boost}
        relevance_threshold = 0.15  # Only boost from relevant memories (15% minimum)
        memories_used = 0

        for mem in relevant_memories:
            # Use pre-normalized relevance score (0-1 range from memory_engine)
            relevance = mem.get('relevance_score', 0)

            # DEBUG: Log first 5 memories to diagnose the bug
            if memories_used < 5:
                mem_preview = str(mem.get('fact', mem.get('text', mem.get('user_input', ''))))[:40]
                is_identity = mem.get('is_identity', False)
                print(f"[DEBUG BOOST] Memory #{memories_used+1}: relevance={relevance:.3f}, identity={is_identity}, threshold={relevance_threshold}, preview='{mem_preview}'")

            # Skip very low relevance memories
            if relevance < relevance_threshold:
                if memories_used < 5:
                    print(f"[DEBUG BOOST]   -> SKIPPED (below threshold)")
                continue

            memories_used += 1

            # Calculate boost amount scaled by relevance (PRE-NORMALIZED to 0-1 by memory_engine)
            # Base boost = 0.05, scaled by relevance (0-1)
            # Example: relevance=0.9 -> boost=0.045, relevance=0.2 -> boost=0.010
            boost_amount = 0.05 * relevance

            if memories_used <= 5:
                print(f"[DEBUG BOOST]   -> PASSED! boost_amount={boost_amount:.4f}")

            for tag in mem.get("emotion_tags", []):
                if tag in cocktail:
                    old_intensity = cocktail[tag]["intensity"]
                    cocktail[tag]["intensity"] = min(1.0,
                        cocktail[tag]["intensity"] + boost_amount)

                    # Track total boost for logging
                    if tag not in reinforced_emotions:
                        reinforced_emotions[tag] = boost_amount
                    else:
                        reinforced_emotions[tag] += boost_amount

        # STEP 3: Enhanced logging
        if reinforced_emotions:
            print(f"[EMOTION ENGINE] Reinforced {len(reinforced_emotions)} emotions from {memories_used} relevant memories:")
            for emotion, total_boost in sorted(reinforced_emotions.items(),
                                               key=lambda x: x[1], reverse=True):
                final_intensity = cocktail[emotion]["intensity"]
                print(f"[EMOTION ENGINE]   - {emotion}: +{total_boost:.3f} boost -> intensity={final_intensity:.2f}")
        else:
            print(f"[EMOTION ENGINE] No emotions reinforced (no relevant memories above threshold)")

        print(f"[EMOTION ENGINE] Used {memories_used}/{len(all_memories)} memories (relevance >= {relevance_threshold:.2f})")

        # CRITICAL: Detect salient emotions to break 77-emotion feedback loop
        # Only keep emotions that are statistical outliers within their category
        salient_emotions = self.detect_salient_emotions(cocktail)

        # Prune non-salient emotions aggressively
        pruned = []
        for emo in list(cocktail.keys()):
            # Keep emotion if it's salient OR has very high intensity (emergency override)
            if emo not in salient_emotions and cocktail[emo]["intensity"] < 0.7:
                pruned.append(emo)
                del cocktail[emo]
        if pruned:
            print(f"[EMOTION ENGINE] Pruned {len(pruned)} non-salient emotions (kept {len(salient_emotions)} salient)")

        agent_state.emotional_cocktail = cocktail

        print(f"[EMOTION ENGINE] Final cocktail: {list(cocktail.keys())} ({len(cocktail)} emotions)")
        for emo, data in sorted(cocktail.items(), key=lambda x: x[1].get('intensity', 0), reverse=True):
            print(f"[EMOTION ENGINE]   - {emo}: intensity={data.get('intensity', 0):.2f}, age={data.get('age', 0)}")
        print("[EMOTION ENGINE] ========== UPDATE END ==========\n")

    # ------------------------------------------------------------------
    # ULTRAMAP Query Methods - For Other Engines
    # ------------------------------------------------------------------

    def get_memory_rules(self, emotion_name: str) -> dict:
        """
        Get memory-related rules for a specific emotion from ULTRAMAP.

        Returns dict with:
        - temporal_weight: How long this emotion's influence on memory lasts
        - priority: How important memories tagged with this emotion are
        - duration_sensitivity: How much duration affects this emotion
        - context_sensitivity: How context-dependent this emotion is

        Used by: memory_engine.py for importance scoring and persistence
        """
        proto = self.protocol.get(emotion_name, {})
        return {
            "temporal_weight": float(proto.get("Temporal Weight", 1.0) or 1.0),
            "priority": float(proto.get("Priority", 0.5) or 0.5) if proto.get("Priority") != "" else 0.5,
            "duration_sensitivity": float(proto.get("Duration Sensitivity", 1.0) or 1.0),
            "context_sensitivity": float(proto.get("Context Sensitivity (0-10)", 5.0) or 5.0) / 10.0,  # Normalize to 0-1
        }

    def get_social_rules(self, emotion_name: str) -> dict:
        """
        Get social-related rules for a specific emotion from ULTRAMAP.

        Returns dict with:
        - social_effect: How this emotion affects social needs
        - action_tendency: What behaviors this emotion encourages
        - feedback_adjustment: How this emotion modifies preferences
        - default_need: What system need this emotion relates to

        Used by: social_engine.py for social need calculations
        """
        proto = self.protocol.get(emotion_name, {})
        return {
            "social_effect": float(proto.get("SocialEffect", 0.0) or 0.0),
            "action_tendency": proto.get("Action/Output Tendency (Examples)", ""),
            "feedback_adjustment": proto.get("Feedback/Preference Adjustment", ""),
            "default_need": proto.get("Default System Need", ""),
        }

    def get_body_rules(self, emotion_name: str) -> dict:
        """
        Get embodiment-related rules for a specific emotion from ULTRAMAP.

        Returns dict with:
        - neurochemical_release: Which neurochemicals this emotion affects
        - body_processes: Physical manifestations
        - temperature: Hot/cold/warm etc.
        - body_parts: Which body parts are affected

        Used by: embodiment_engine.py for body chemistry mapping
        """
        proto = self.protocol.get(emotion_name)
        neurochem_str = proto.get("Neurochemical Release", "")
        neurochem_map = self._parse_neurochem(neurochem_str) if isinstance(neurochem_str, str) else {}

        return {
            "neurochemical_release": neurochem_map,
            "body_processes": proto.get("Human Bodily Processes", ""),
            "temperature": proto.get("Temperature", ""),
            "body_parts": proto.get("Body Part(s)", ""),
        }

    def get_recursion_rules(self, emotion_name: str) -> dict:
        """
        Get recursion/loop protocol rules for a specific emotion from ULTRAMAP.

        Returns dict with:
        - recursion_protocol: How this emotion loops/repeats
        - break_condition: When to break the loop
        - emergency_ritual: What to do if system collapses
        - escalation_protocol: How this emotion escalates

        Used by: momentum_engine.py, meta_awareness_engine.py for pattern tracking
        """
        proto = self.protocol.get(emotion_name, {})
        return {
            "recursion_protocol": proto.get("Recursion/Loop Protocol", ""),
            "break_condition": proto.get("Break Condition/Phase Shift", ""),
            "emergency_ritual": proto.get("Emergency Ritual/Output When System Collapses", ""),
            "escalation_protocol": proto.get("Escalation/Mutation Protocol", ""),
        }

    def get_full_rules(self, emotion_name: str) -> dict:
        """
        Get ALL rules for a specific emotion from ULTRAMAP.

        Returns the complete protocol dict for this emotion.
        Useful for debugging or comprehensive analysis.
        """
        return self.protocol.get(emotion_name, {})
