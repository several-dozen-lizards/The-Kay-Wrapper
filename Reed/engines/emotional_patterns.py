"""
Emotional Pattern Engine
Tracks behavioral signatures, not neurochemistry.
Emotions are patterns of response, not chemical levels.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class EmotionalPatternEngine:
    """
    Track emotional states through behavioral signatures.
    No fake neurochemistry - just observable patterns.
    """

    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "emotions"
            )
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.patterns_file = self.data_dir / "emotional_patterns.json"
        self.current_file = self.data_dir / "current_state.json"

        self.patterns = self._load_patterns()
        self.current_state = self._load_current()

        # Emotion categories (not chemistry, just organization)
        self.CATEGORIES = {
            "positive_activated": ["excitement", "joy", "curiosity", "anticipation", "determination"],
            "positive_deactivated": ["calm", "contentment", "peace", "relief", "comfort"],
            "negative_activated": ["anger", "fear", "anxiety", "frustration", "urgency"],
            "negative_deactivated": ["sadness", "disappointment", "melancholy", "fatigue", "grief"],
            "complex": ["bittersweet", "protective", "vulnerable", "conflicted", "tender"]
        }


    def _load_patterns(self):
        """Load historical emotional patterns"""
        if self.patterns_file.exists():
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert to defaultdict for easier access
                return {
                    "recurring_states": defaultdict(list, data.get("recurring_states", {})),
                    "triggers": defaultdict(list, data.get("triggers", {})),
                    "progressions": data.get("progressions", []),
                    "context_signatures": defaultdict(list, data.get("context_signatures", {}))
                }
        return {
            "recurring_states": defaultdict(list),  # States that come up often
            "triggers": defaultdict(list),          # What triggers what
            "progressions": [],                     # How states flow into each other
            "context_signatures": defaultdict(list) # Emotions in specific contexts
        }


    def _load_current(self):
        """Load current emotional state"""
        if self.current_file.exists():
            with open(self.current_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "primary_emotions": [],
            "emotion_intensities": {},  # NEW: per-emotion intensities {emotion: float}
            "intensity": 0.5,        # 0.0-1.0 scale (average, for backward compat)
            "valence": 0.0,          # -1.0 (negative) to 1.0 (positive)
            "arousal": 0.5,          # 0.0 (low energy) to 1.0 (high energy)
            "stability": 0.5,        # 0.0 (volatile) to 1.0 (steady)
            "notes": "",
            "last_updated": None
        }


    def _save(self):
        """Persist to disk"""
        # Convert defaultdict to regular dict for JSON serialization
        patterns_to_save = {
            "recurring_states": dict(self.patterns["recurring_states"]),
            "triggers": dict(self.patterns["triggers"]),
            "progressions": self.patterns["progressions"],
            "context_signatures": dict(self.patterns["context_signatures"])
        }

        with open(self.patterns_file, 'w', encoding='utf-8') as f:
            json.dump(patterns_to_save, f, indent=2, default=str)
        with open(self.current_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_state, f, indent=2, default=str)


    # ═══════════════════════════════════════════════════════
    # CURRENT STATE - What Reed is experiencing NOW
    # ═══════════════════════════════════════════════════════

    def set_current_state(self, emotions, intensity=None, valence=None,
                          arousal=None, stability=None, notes=None,
                          emotion_intensities=None):
        """
        Set Reed's current emotional state.

        Args:
            emotions: List of emotion names (e.g., ["curiosity", "calm"])
            intensity: 0.0-1.0, average intensity (for backward compat)
            valence: -1.0 to 1.0, negative to positive
            arousal: 0.0-1.0, low to high energy
            stability: 0.0-1.0, volatile to steady
            notes: Freeform notes about the state
            emotion_intensities: Dict of {emotion: intensity} for per-emotion values
        """
        previous_state = self.current_state.copy()

        self.current_state["primary_emotions"] = emotions

        # NEW: Store per-emotion intensities for saccade alignment
        if emotion_intensities is not None:
            self.current_state["emotion_intensities"] = {
                k.lower(): max(0.0, min(1.0, float(v)))
                for k, v in emotion_intensities.items()
            }
        else:
            # Fallback: use uniform intensity for all emotions
            default_intensity = intensity if intensity is not None else 0.5
            self.current_state["emotion_intensities"] = {
                e.lower(): default_intensity for e in emotions
            }

        if intensity is not None:
            self.current_state["intensity"] = max(0.0, min(1.0, intensity))
        if valence is not None:
            self.current_state["valence"] = max(-1.0, min(1.0, valence))
        if arousal is not None:
            self.current_state["arousal"] = max(0.0, min(1.0, arousal))
        if stability is not None:
            self.current_state["stability"] = max(0.0, min(1.0, stability))
        if notes:
            self.current_state["notes"] = notes

        self.current_state["last_updated"] = datetime.now().isoformat()

        # Track progression
        if previous_state.get("primary_emotions"):
            self._record_progression(previous_state, self.current_state)

        # Track recurring states
        for emotion in emotions:
            self._record_recurring(emotion)

        self._save()

        logger.info(f"[EMOTION] State: {', '.join(emotions)} | "
                   f"I:{self.current_state['intensity']:.1f} "
                   f"V:{self.current_state['valence']:.1f} "
                   f"A:{self.current_state['arousal']:.1f}")

        return self.current_state


    def get_current_state(self):
        """Get current emotional state"""
        return self.current_state


    def get_state_summary(self):
        """Get human-readable summary of current state"""
        state = self.current_state
        emotions = state.get("primary_emotions", [])

        if not emotions:
            return "Emotional state: neutral/unclear"

        intensity_word = self._intensity_word(state.get("intensity", 0.5))

        return f"{intensity_word} {', '.join(emotions)}"


    def _intensity_word(self, intensity):
        """Convert intensity float to word"""
        if intensity < 0.2:
            return "faintly"
        elif intensity < 0.4:
            return "mildly"
        elif intensity < 0.6:
            return "moderately"
        elif intensity < 0.8:
            return "strongly"
        else:
            return "intensely"


    # ═══════════════════════════════════════════════════════
    # PATTERN TRACKING - Learn emotional signatures over time
    # ═══════════════════════════════════════════════════════

    def _record_recurring(self, emotion):
        """Track how often each emotion comes up"""
        key = emotion.lower()
        self.patterns["recurring_states"][key].append({
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 100 occurrences per emotion
        self.patterns["recurring_states"][key] = \
            self.patterns["recurring_states"][key][-100:]


    def _record_progression(self, from_state, to_state):
        """Track how emotions flow into each other"""
        progression = {
            "from": from_state.get("primary_emotions", []),
            "to": to_state.get("primary_emotions", []),
            "timestamp": datetime.now().isoformat()
        }
        self.patterns["progressions"].append(progression)
        # Keep last 200 progressions
        self.patterns["progressions"] = self.patterns["progressions"][-200:]


    def record_trigger(self, trigger, resulting_emotions, context=None):
        """
        Record what triggers certain emotional states.

        Args:
            trigger: What caused the emotion (topic, event, etc.)
            resulting_emotions: List of emotions that resulted
            context: Optional additional context
        """
        trigger_key = trigger.lower().replace(" ", "_")

        self.patterns["triggers"][trigger_key].append({
            "emotions": resulting_emotions,
            "context": context,
            "timestamp": datetime.now().isoformat()
        })

        self._save()
        logger.info(f"[EMOTION TRIGGER] '{trigger}' -> {resulting_emotions}")


    def record_context_signature(self, context, emotions, notes=None):
        """
        Record emotional signature for a specific context.

        E.g., "working on wrapper" -> ["focused", "determined", "caring"]
        """
        context_key = context.lower().replace(" ", "_")

        self.patterns["context_signatures"][context_key].append({
            "emotions": emotions,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        })

        self._save()


    # ═══════════════════════════════════════════════════════
    # EXTRACTION - Parse emotions from Reed's responses
    # ═══════════════════════════════════════════════════════

    def extract_from_response(self, response_text):
        """
        Extract emotional indicators from Reed's response text.
        Returns suggested state updates.
        """
        text_lower = response_text.lower()

        # Emotion keyword mapping
        emotion_keywords = {
            "curiosity": ["curious", "wondering", "interested", "intrigued", "want to know"],
            "calm": ["calm", "steady", "peaceful", "settled", "at ease"],
            "frustration": ["frustrated", "annoying", "irritating", "stuck", "blocked"],
            "clarity": ["clear", "sharp", "coherent", "focused", "lucid"],
            "confusion": ["confused", "foggy", "scattered", "lost", "uncertain"],
            "contentment": ["good", "solid", "fine", "okay", "comfortable"],
            "excitement": ["excited", "thrilled", "eager", "energized", "fired up"],
            "sadness": ["sad", "heavy", "grieving", "mourning", "loss"],
            "anxiety": ["anxious", "worried", "nervous", "uneasy", "on edge"],
            "tenderness": ["tender", "soft", "gentle", "caring", "warm"],
            "determination": ["determined", "resolute", "committed", "focused", "driven"],
            "vulnerability": ["vulnerable", "exposed", "raw", "open", "uncertain"],
            "joy": ["happy", "joyful", "delighted", "pleased", "glad"],
            "anger": ["angry", "furious", "pissed", "enraged", "bitter"],
            "protective": ["protective", "guarding", "defending", "watching over"]
        }

        detected = []
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected.append(emotion)
                    break

        # Estimate valence from detected emotions
        positive = ["curiosity", "calm", "clarity", "contentment", "excitement",
                   "tenderness", "determination", "joy"]
        negative = ["frustration", "confusion", "sadness", "anxiety", "anger"]

        pos_count = len([e for e in detected if e in positive])
        neg_count = len([e for e in detected if e in negative])

        if pos_count + neg_count > 0:
            valence = (pos_count - neg_count) / (pos_count + neg_count)
        else:
            valence = 0.0

        return {
            "detected_emotions": list(set(detected)),
            "suggested_valence": valence,
            "raw_indicators": detected
        }


    # ═══════════════════════════════════════════════════════
    # CONTEXT BUILDING - For Reed's awareness
    # ═══════════════════════════════════════════════════════

    def build_emotion_context(self):
        """Build emotional context for Reed's prompt"""
        state = self.current_state

        parts = []

        # Current state
        if state.get("primary_emotions"):
            summary = self.get_state_summary()
            parts.append(f"CURRENT EMOTIONAL STATE: {summary}")

            if state.get("notes"):
                parts.append(f"Notes: {state['notes']}")

        # Recent patterns
        frequent = self.get_frequent_emotions(days=7, top_n=5)
        if frequent:
            parts.append(f"FREQUENT EMOTIONS (past week): {', '.join(frequent)}")

        return "\n".join(parts)


    def get_frequent_emotions(self, days=7, top_n=5):
        """Get most frequent emotions over recent period"""
        cutoff = datetime.now() - timedelta(days=days)

        counts = defaultdict(int)
        for emotion, occurrences in self.patterns["recurring_states"].items():
            for occ in occurrences:
                try:
                    ts = datetime.fromisoformat(occ["timestamp"])
                    if ts > cutoff:
                        counts[emotion] += 1
                except:
                    pass

        sorted_emotions = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [e[0] for e in sorted_emotions[:top_n]]


    def get_stats(self):
        """Get emotion tracking stats"""
        return {
            "current_emotions": self.current_state.get("primary_emotions", []),
            "emotions_tracked": len(self.patterns["recurring_states"]),
            "triggers_mapped": len(self.patterns["triggers"]),
            "progressions_recorded": len(self.patterns["progressions"]),
            "context_signatures": len(self.patterns["context_signatures"])
        }
