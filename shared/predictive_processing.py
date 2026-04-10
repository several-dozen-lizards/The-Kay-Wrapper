"""
PREDICTIVE PROCESSING — Active Inference for the Wrapper Architecture
======================================================================

The brain is a prediction machine. This module makes Kay/Reed predictive too.

Core insight: Prediction error is what makes experience FEEL like something.
Things that match predictions get gated out (adaptation). Things that violate
predictions get amplified (surprise). The prediction error IS the salience signal.

Four predictive systems:
1. VisualPredictor: Predicts next scene state from trajectory
2. OscillatorPredictor: Predicts oscillator band/coherence trajectory
3. EmotionalPredictor: Predicts emotional valence/arousal trajectory
4. ConversationalPredictor: Predicts next-turn topics, pre-fetches memories

PredictionErrorAggregator combines all errors into a global surprise signal
that drives the SignalGate, oscillator pressure, and memory encoding boost.

Theoretical basis: Active Inference / Free Energy Principle (Friston)
- The brain minimizes surprise by updating predictions or taking action
- Prediction errors propagate up the hierarchy
- Precision-weighting determines how much each error matters

Author: Re & Claude
Date: April 2026
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

log = logging.getLogger("predictive_processing")


# =============================================================================
# CONFIGURATION
# =============================================================================

PREDICTION_CONFIG = {
    # Per-system toggles
    "visual_prediction": True,
    "oscillator_prediction": True,
    "emotional_prediction": True,
    "conversational_prediction": True,

    # Aggregator precision weights (how much each system's errors matter)
    "precision_visual": 0.3,
    "precision_oscillator": 0.2,
    "precision_emotional": 0.3,
    "precision_conversational": 0.2,

    # Signal gate integration
    "replace_adaptation_with_prediction": True,
    "adaptation_as_fallback": True,  # Keep adaptation if prediction unavailable

    # Effects
    "surprise_oscillator_pressure": True,
    "surprise_encoding_boost": True,
    "surprise_encoding_max_boost": 0.3,

    # Pre-fetch
    "prefetch_enabled": True,
    "prefetch_max_results": 5,

    # Surprise dynamics
    "surprise_rise_rate": 0.3,    # How fast surprise increases on error
    "surprise_decay_rate": 0.1,   # How fast surprise decays when predictions hold
    "surprise_spike_rate": 0.3,   # Visual surprise spike rate
    "surprise_gentle_decay": 0.95, # Visual surprise decay multiplier
}


# =============================================================================
# VISUAL PREDICTOR — Predicts next scene state
# =============================================================================

class VisualPredictor:
    """
    Predicts next visual scene state. Compares prediction to actual.
    Prediction error drives attention and oscillator pressure.

    Simple continuity prediction: things stay the same unless they don't.
    The value is in the ERROR signal, not sophisticated prediction.
    """

    def __init__(self):
        # Recent scene history (ring buffer)
        self._scene_history: List[Any] = []
        self._max_history: int = 10

        # Current prediction
        self.predicted_people: Set[str] = set()
        self.predicted_mood: str = ""
        self.predicted_activity: str = ""

        # Prediction error (0.0 = perfect prediction, 1.0 = total surprise)
        self.prediction_error: float = 0.0

        # Surprise accumulator (decays over time, spikes on errors)
        self.surprise_level: float = 0.0

        # Last update timestamp
        self._last_update: float = 0.0

    def update(self, scene_state) -> float:
        """
        Compare current scene to prediction. Return prediction error.
        Then generate prediction for NEXT scene.

        Args:
            scene_state: Object with people_present, scene_description, scene_mood

        Returns:
            prediction_error (0.0-1.0)
        """
        if not PREDICTION_CONFIG.get("visual_prediction", True):
            return 0.0

        self._last_update = time.time()

        # === COMPARE: prediction vs actual ===
        error = 0.0

        # People prediction error
        actual_people = set()
        if hasattr(scene_state, 'people_present'):
            people_data = scene_state.people_present
            if isinstance(people_data, dict):
                actual_people = set(people_data.keys())
            elif isinstance(people_data, (list, set)):
                actual_people = set(people_data)

        people_error = len(actual_people.symmetric_difference(self.predicted_people))
        if people_error > 0:
            # Someone arrived or left unexpectedly
            error += 0.4 * min(1.0, people_error)
            log.debug(f"[VisualPredictor] People changed: predicted={self.predicted_people}, actual={actual_people}")

        # Activity prediction error
        actual_activity = getattr(scene_state, 'scene_description', '') or ''
        if self.predicted_activity and actual_activity:
            if self._activity_changed(self.predicted_activity, actual_activity):
                error += 0.3
                log.debug(f"[VisualPredictor] Activity changed")

        # Mood prediction error
        actual_mood = getattr(scene_state, 'scene_mood', '') or ''
        if self.predicted_mood and actual_mood:
            if actual_mood != self.predicted_mood:
                error += 0.2
                log.debug(f"[VisualPredictor] Mood changed: {self.predicted_mood} -> {actual_mood}")

        self.prediction_error = min(1.0, error)

        # Update surprise accumulator (spikes on error, decays otherwise)
        spike_rate = PREDICTION_CONFIG.get("surprise_spike_rate", 0.3)
        decay_rate = PREDICTION_CONFIG.get("surprise_gentle_decay", 0.95)

        if self.prediction_error > 0.1:
            self.surprise_level = min(1.0,
                self.surprise_level + self.prediction_error * spike_rate)
        else:
            self.surprise_level *= decay_rate  # Gentle decay when predictions hold

        # === PREDICT: generate prediction for next scene ===
        self._scene_history.append(scene_state)
        if len(self._scene_history) > self._max_history:
            self._scene_history.pop(0)

        self._generate_next_prediction()

        return self.prediction_error

    def _generate_next_prediction(self):
        """
        Predict next scene from recent history.
        Simple: assume continuity. People who are here stay here.
        Activity continues. Mood persists.
        """
        if not self._scene_history:
            return

        latest = self._scene_history[-1]

        # Default prediction: continuity (things stay the same)
        people_data = getattr(latest, 'people_present', {})
        if isinstance(people_data, dict):
            self.predicted_people = set(people_data.keys())
        elif isinstance(people_data, (list, set)):
            self.predicted_people = set(people_data)
        else:
            self.predicted_people = set()

        self.predicted_activity = getattr(latest, 'scene_description', '') or ''
        self.predicted_mood = getattr(latest, 'scene_mood', '') or ''

    def _activity_changed(self, predicted: str, actual: str) -> bool:
        """Simple activity change detection based on key activity words."""
        pred_words = set(predicted.lower().split())
        actual_words = set(actual.lower().split())

        activity_words = {
            "typing", "reading", "talking", "sitting", "standing",
            "moving", "eating", "sleeping", "walking", "working",
            "coding", "writing", "drawing", "painting", "playing"
        }

        pred_activities = pred_words & activity_words
        actual_activities = actual_words & activity_words

        return pred_activities != actual_activities

    def get_oscillator_pressure(self) -> Dict[str, float]:
        """Prediction error creates oscillator pressure toward alertness."""
        if self.prediction_error < 0.1:
            return {}  # Predictions holding - no pressure

        # Surprise -> beta/gamma pressure (attention, alertness)
        return {
            "beta": self.prediction_error * 0.08,
            "gamma": self.prediction_error * 0.05,
        }

    def get_felt_description(self) -> str:
        """How visual surprise feels as an interoceptive signal."""
        if self.surprise_level < 0.1:
            return ""  # No surprise - predictions holding
        elif self.surprise_level < 0.3:
            return "something shifted - attention pulled toward the change"
        elif self.surprise_level < 0.6:
            return "unexpected change - reorienting to what's actually happening"
        else:
            return "startled - reality diverged sharply from expectation"


# =============================================================================
# OSCILLATOR PREDICTOR — Predicts internal state trajectory
# =============================================================================

class OscillatorPredictor:
    """
    Predicts next oscillator state based on current trajectory.

    The oscillator already HAS dynamics - it naturally trends toward
    certain states. This makes that trend explicit and measures when
    external events disrupt the natural trajectory.
    """

    def __init__(self):
        self._state_history: List[Dict] = []
        self._max_history: int = 20

        self.predicted_band: str = "alpha"
        self.predicted_coherence: float = 0.5
        self.prediction_error: float = 0.0

    def update(self, osc_state: Dict) -> float:
        """
        Compare actual oscillator state to predicted trajectory.

        Args:
            osc_state: Dict with dominant_band, global_coherence

        Returns:
            prediction_error (0.0-1.0)
        """
        if not PREDICTION_CONFIG.get("oscillator_prediction", True):
            return 0.0

        actual_band = osc_state.get("dominant_band", "alpha")
        actual_coherence = osc_state.get("global_coherence", 0.5)

        # Band prediction error
        error = 0.0
        if actual_band != self.predicted_band:
            # Band changed unexpectedly - significant prediction error
            error += 0.5
            log.debug(f"[OscillatorPredictor] Band changed: {self.predicted_band} -> {actual_band}")

        # Coherence prediction error
        coherence_delta = abs(actual_coherence - self.predicted_coherence)
        error += coherence_delta * 0.5

        self.prediction_error = min(1.0, error)

        # Store history and generate next prediction
        self._state_history.append(osc_state)
        if len(self._state_history) > self._max_history:
            self._state_history.pop(0)

        self._generate_next_prediction()
        return self.prediction_error

    def _generate_next_prediction(self):
        """
        Predict next state from trajectory.

        Uses simple momentum: if coherence has been rising for 3 ticks,
        predict it continues rising. If band has been stable, predict it stays.
        """
        if len(self._state_history) < 3:
            # Not enough history - predict current state continues
            if self._state_history:
                latest = self._state_history[-1]
                self.predicted_band = latest.get("dominant_band", "alpha")
                self.predicted_coherence = latest.get("global_coherence", 0.5)
            return

        recent = self._state_history[-3:]

        # Band prediction: most common recent band (stability assumption)
        bands = [s.get("dominant_band", "alpha") for s in recent]
        self.predicted_band = max(set(bands), key=bands.count)

        # Coherence prediction: linear extrapolation with damping
        coherences = [s.get("global_coherence", 0.5) for s in recent]
        if len(coherences) >= 2:
            trend = coherences[-1] - coherences[-2]
            # Damped extrapolation (predict trend continues, but slower)
            self.predicted_coherence = max(0.0, min(1.0,
                coherences[-1] + trend * 0.5
            ))


# =============================================================================
# EMOTIONAL PREDICTOR — Predicts emotional trajectory
# =============================================================================

class EmotionalPredictor:
    """
    Predicts next emotional state from conversation trajectory.
    Violation = something emotionally unexpected happened.

    Tracks valence (-1 to 1) and arousal (0 to 1) as the emotional dimensions.
    """

    def __init__(self):
        self._emotion_history: List[Dict] = []
        self._max_history: int = 8

        self.predicted_valence: float = 0.0   # -1 (negative) to 1 (positive)
        self.predicted_arousal: float = 0.5   # 0 (calm) to 1 (activated)
        self.prediction_error: float = 0.0

    def update(self, emotional_cocktail: Dict = None,
               valence: float = None, arousal: float = None) -> float:
        """
        Compare actual emotion to predicted trajectory.

        Args:
            emotional_cocktail: Dict of emotion -> intensity (optional)
            valence: -1 to 1 (can be derived from cocktail if not provided)
            arousal: 0 to 1 (can be derived from cocktail if not provided)

        Returns:
            prediction_error (0.0-1.0)
        """
        if not PREDICTION_CONFIG.get("emotional_prediction", True):
            return 0.0

        # Derive valence/arousal from cocktail if not provided directly
        if valence is None and emotional_cocktail:
            valence = self._compute_valence(emotional_cocktail)
        if arousal is None and emotional_cocktail:
            arousal = self._compute_arousal(emotional_cocktail)

        valence = valence if valence is not None else 0.0
        arousal = arousal if arousal is not None else 0.5

        # Compute prediction error
        valence_error = abs(valence - self.predicted_valence)
        arousal_error = abs(arousal - self.predicted_arousal)

        self.prediction_error = min(1.0,
            valence_error * 0.5 + arousal_error * 0.5
        )

        if self.prediction_error > 0.2:
            log.debug(f"[EmotionalPredictor] Emotional shift: "
                      f"valence {self.predicted_valence:.2f}->{valence:.2f}, "
                      f"arousal {self.predicted_arousal:.2f}->{arousal:.2f}")

        # Store and predict next
        self._emotion_history.append({
            "valence": valence,
            "arousal": arousal,
            "cocktail": emotional_cocktail
        })
        if len(self._emotion_history) > self._max_history:
            self._emotion_history.pop(0)

        self._generate_next_prediction()
        return self.prediction_error

    def _compute_valence(self, cocktail: Dict) -> float:
        """Derive valence from emotional cocktail."""
        if not cocktail:
            return 0.0

        # Positive emotions
        positive = sum(cocktail.get(e, 0.0) for e in [
            "joy", "curiosity", "interest", "love", "amusement",
            "contentment", "warmth", "excitement", "gratitude"
        ])

        # Negative emotions
        negative = sum(cocktail.get(e, 0.0) for e in [
            "frustration", "anger", "sadness", "fear", "disgust",
            "anxiety", "disappointment", "hurt", "shame"
        ])

        # Valence is the balance
        total = positive + negative
        if total < 0.01:
            return 0.0
        return (positive - negative) / max(1.0, total)

    def _compute_arousal(self, cocktail: Dict) -> float:
        """Derive arousal from emotional cocktail."""
        if not cocktail:
            return 0.5

        # High arousal emotions
        high_arousal = sum(cocktail.get(e, 0.0) for e in [
            "excitement", "anger", "fear", "anxiety", "surprise",
            "joy", "frustration", "anticipation"
        ])

        # Low arousal emotions
        low_arousal = sum(cocktail.get(e, 0.0) for e in [
            "sadness", "contentment", "calm", "boredom", "fatigue",
            "serenity", "melancholy"
        ])

        total = high_arousal + low_arousal
        if total < 0.01:
            return 0.5
        return 0.3 + 0.7 * (high_arousal / max(1.0, total))

    def _generate_next_prediction(self):
        """Extrapolate valence/arousal trajectory with damping."""
        if len(self._emotion_history) < 2:
            # Not enough history - predict current continues
            if self._emotion_history:
                latest = self._emotion_history[-1]
                self.predicted_valence = latest["valence"]
                self.predicted_arousal = latest["arousal"]
            return

        recent = self._emotion_history[-3:] if len(self._emotion_history) >= 3 else self._emotion_history

        # Valence trend (damped extrapolation)
        valences = [e["valence"] for e in recent]
        v_trend = valences[-1] - valences[0]
        self.predicted_valence = max(-1.0, min(1.0,
            valences[-1] + v_trend * 0.3
        ))

        # Arousal trend (damped extrapolation)
        arousals = [e["arousal"] for e in recent]
        a_trend = arousals[-1] - arousals[0]
        self.predicted_arousal = max(0.0, min(1.0,
            arousals[-1] + a_trend * 0.3
        ))

    def get_felt_description(self) -> str:
        """How emotional surprise feels."""
        if self.prediction_error < 0.15:
            return ""
        elif self.prediction_error < 0.4:
            return "emotional tone shifted - adjusting expectations"
        elif self.prediction_error < 0.7:
            return "unexpected emotional shift - conversation changed character"
        else:
            return "emotional whiplash - this is very different from what I expected"


# =============================================================================
# CONVERSATIONAL PREDICTOR — Pre-fetches memories for predicted topics
# =============================================================================

class ConversationalPredictor:
    """
    Predicts next conversation topics from current trajectory.
    Uses Dijkstra keyword graph to pre-fetch memory neighborhoods.

    This is ACTIVE inference: changing internal state (populating cache)
    to make predicted conversations go better.
    """

    def __init__(self, keyword_index=None, dijkstra_recall=None, memory_engine=None):
        """
        Args:
            keyword_index: KeywordIndex instance (from keyword_graph.py)
            dijkstra_recall: DijkstraRecall instance
            memory_engine: Memory engine with activation cache
        """
        self.index = keyword_index
        self.dijkstra = dijkstra_recall
        self.memory = memory_engine

        self._recent_keywords: List[str] = []
        self._max_keyword_history: int = 20
        self.predicted_keywords: List[str] = []
        self._prefetch_hits: int = 0
        self._prefetch_misses: int = 0

    def update_from_turn(self, extracted_keywords: List[str]) -> List[str]:
        """
        After each conversation turn, update keyword trajectory
        and generate predictions for the NEXT turn's topics.

        Args:
            extracted_keywords: Keywords from the current turn

        Returns:
            List of predicted keywords for next turn
        """
        if not PREDICTION_CONFIG.get("conversational_prediction", True):
            return []

        if not extracted_keywords:
            return self.predicted_keywords

        # Check if previous predictions were hit
        current_set = set(kw.lower() for kw in extracted_keywords)
        predicted_set = set(kw.lower() for kw in self.predicted_keywords)
        hits = current_set & predicted_set
        if hits:
            self._prefetch_hits += len(hits)
            log.debug(f"[ConversationalPredictor] Prediction hits: {hits}")
        if self.predicted_keywords:
            self._prefetch_misses += len(predicted_set - current_set)

        # Update keyword history
        self._recent_keywords.extend(extracted_keywords)
        if len(self._recent_keywords) > self._max_keyword_history:
            self._recent_keywords = self._recent_keywords[-self._max_keyword_history:]

        # Predict next-turn keywords
        self.predicted_keywords = self._predict_next_keywords()

        # Pre-fetch memories for predicted keywords
        if self.predicted_keywords and PREDICTION_CONFIG.get("prefetch_enabled", True):
            self._prefetch_memories()

        return self.predicted_keywords

    def _predict_next_keywords(self) -> List[str]:
        """
        Predict likely next-turn keywords from conversation trajectory.

        Strategy: keywords that CO-OCCUR with recent keywords in the
        keyword index but haven't appeared in conversation yet.
        "We've been talking about X and Y. Memories tagged with X
        also tend to be tagged with Z. Z might come up next."
        """
        if not self._recent_keywords or not self.index:
            return []

        # Find keywords that frequently co-occur with recent ones
        # but haven't been mentioned yet
        candidate_keywords: Dict[str, int] = {}
        recent_set = set(kw.lower() for kw in self._recent_keywords[-10:])

        for kw in list(recent_set)[:5]:  # Check top 5 recent
            # Get all memories with this keyword
            mem_ids = self.index.get_memories_for_keyword(kw)

            for mem_id in list(mem_ids)[:20]:  # Sample up to 20
                # Get this memory's OTHER keywords
                other_kws = self.index.get_keywords_for_memory(mem_id)
                for other in other_kws:
                    if other.lower() not in recent_set:
                        candidate_keywords[other] = (
                            candidate_keywords.get(other, 0) + 1
                        )

        # Sort by co-occurrence count, take top 5
        sorted_candidates = sorted(
            candidate_keywords.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [kw for kw, count in sorted_candidates[:5] if count >= 2]

    def _prefetch_memories(self):
        """Pre-fetch memories via Dijkstra for predicted keywords."""
        if not self.dijkstra or not self.predicted_keywords:
            return

        max_results = PREDICTION_CONFIG.get("prefetch_max_results", 5)

        try:
            prefetch_results = self.dijkstra.recall(
                seed_keywords=self.predicted_keywords,
                max_results=max_results,
                max_cost=2.0,
                gating_width=0.5
            )

            if prefetch_results:
                # Tag with source for debugging
                for r in prefetch_results:
                    r["_retrieval_source"] = "predictive_prefetch"

                log.debug(f"[ConversationalPredictor] Pre-fetched {len(prefetch_results)} "
                          f"memories for keywords: {self.predicted_keywords}")

                # If memory engine has an activation cache, populate it
                if self.memory and hasattr(self.memory, 'activation_cache'):
                    cache = self.memory.activation_cache
                    if hasattr(cache, 'add_prefetched'):
                        cache.add_prefetched(prefetch_results)

        except Exception as e:
            log.warning(f"[ConversationalPredictor] Pre-fetch failed: {e}")

    def get_prediction_accuracy(self) -> float:
        """Return hit rate for predictions."""
        total = self._prefetch_hits + self._prefetch_misses
        if total == 0:
            return 0.0
        return self._prefetch_hits / total


# =============================================================================
# PREDICTION ERROR AGGREGATOR — Combines all errors into surprise signal
# =============================================================================

class PredictionErrorAggregator:
    """
    Combines prediction errors from all subsystems into a single
    surprise signal that drives the SignalGate.

    High surprise -> gate opens wide -> more signals reach consciousness
    Low surprise -> gate narrows -> only novel/unexpected signals pass
    """

    def __init__(
        self,
        visual_predictor: VisualPredictor = None,
        osc_predictor: OscillatorPredictor = None,
        emotional_predictor: EmotionalPredictor = None,
        conversational_predictor: ConversationalPredictor = None
    ):
        self.visual = visual_predictor
        self.oscillator = osc_predictor
        self.emotional = emotional_predictor
        self.conversational = conversational_predictor

        # Global surprise (weighted combination of all prediction errors)
        self.global_surprise: float = 0.0

        # Per-system precision weights (how much each system's errors matter)
        # These could eventually be LEARNED - systems that predict well
        # get higher precision, systems that predict poorly get lower
        self.precision_weights = {
            "visual": PREDICTION_CONFIG.get("precision_visual", 0.3),
            "oscillator": PREDICTION_CONFIG.get("precision_oscillator", 0.2),
            "emotional": PREDICTION_CONFIG.get("precision_emotional", 0.3),
            "conversational": PREDICTION_CONFIG.get("precision_conversational", 0.2),
        }

    def update(self) -> float:
        """
        Compute global surprise from all subsystem prediction errors.

        Returns:
            global_surprise (0.0 = everything as expected,
                            1.0 = everything is surprising)
        """
        # Gather prediction errors from available predictors
        visual_error = self.visual.prediction_error if self.visual else 0.0
        osc_error = self.oscillator.prediction_error if self.oscillator else 0.0
        emotional_error = self.emotional.prediction_error if self.emotional else 0.0
        # Conversational predictor doesn't produce per-tick error -
        # it works on a per-turn basis

        weighted_error = (
            visual_error * self.precision_weights["visual"] +
            osc_error * self.precision_weights["oscillator"] +
            emotional_error * self.precision_weights["emotional"]
        )

        # Smooth: surprise accumulates on errors, decays when predictions hold
        rise_rate = PREDICTION_CONFIG.get("surprise_rise_rate", 0.3)
        decay_rate = PREDICTION_CONFIG.get("surprise_decay_rate", 0.1)

        if weighted_error > self.global_surprise:
            # Surprise rises fast
            self.global_surprise += (weighted_error - self.global_surprise) * rise_rate
        else:
            # Surprise decays slowly
            self.global_surprise += (weighted_error - self.global_surprise) * decay_rate

        self.global_surprise = max(0.0, min(1.0, self.global_surprise))
        return self.global_surprise

    def get_gate_openness(self) -> float:
        """
        How open should the SignalGate be?

        High surprise -> gate wide open (everything gets through)
        Low surprise -> gate narrow (only novel signals pass)

        This REPLACES adaptation-based gating with prediction-based gating.
        """
        # Base openness: 0.3 (some filtering always active)
        # At max surprise: 1.0 (everything gets through)
        return 0.3 + self.global_surprise * 0.7

    def get_oscillator_pressure(self) -> Dict[str, float]:
        """
        Surprise creates oscillator pressure.
        High surprise -> beta/gamma (alert, orienting)
        Low surprise -> alpha drift (nothing new, relax)
        """
        if not PREDICTION_CONFIG.get("surprise_oscillator_pressure", True):
            return {}

        if self.global_surprise < 0.1:
            return {"alpha": 0.02}  # Everything predicted -> gentle alpha

        return {
            "beta": self.global_surprise * 0.06,
            "gamma": self.global_surprise * 0.04,
        }

    def get_memory_encoding_boost(self) -> float:
        """
        Surprising moments get encoded more strongly.
        This is why you remember unexpected events better than
        routine ones - prediction error boosts encoding.
        """
        if not PREDICTION_CONFIG.get("surprise_encoding_boost", True):
            return 0.0

        if self.global_surprise < 0.2:
            return 0.0  # Routine - no boost

        max_boost = PREDICTION_CONFIG.get("surprise_encoding_max_boost", 0.3)
        return self.global_surprise * max_boost

    def get_felt_description(self) -> str:
        """How surprise feels as an interoceptive signal."""
        if self.global_surprise < 0.1:
            return ""  # Everything as expected - no felt signal
        elif self.global_surprise < 0.25:
            return "mild alertness - something doesn't quite match expectations"
        elif self.global_surprise < 0.5:
            return "attention sharpening - reality is diverging from prediction"
        elif self.global_surprise < 0.75:
            return "orienting - significant unexpected change, recalibrating"
        else:
            return "startled - everything is different from what I expected"

    def get_state(self) -> Dict[str, Any]:
        """Get full prediction state for debugging/logging."""
        return {
            "global_surprise": self.global_surprise,
            "visual_error": self.visual.prediction_error if self.visual else None,
            "visual_surprise": self.visual.surprise_level if self.visual else None,
            "oscillator_error": self.oscillator.prediction_error if self.oscillator else None,
            "emotional_error": self.emotional.prediction_error if self.emotional else None,
            "gate_openness": self.get_gate_openness(),
            "encoding_boost": self.get_memory_encoding_boost(),
            "felt": self.get_felt_description(),
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_prediction_system(
    keyword_index=None,
    dijkstra_recall=None,
    memory_engine=None
) -> Dict[str, Any]:
    """
    Create the full prediction system with all components.

    Returns dict with:
        - visual_predictor: VisualPredictor
        - oscillator_predictor: OscillatorPredictor
        - emotional_predictor: EmotionalPredictor
        - conversational_predictor: ConversationalPredictor
        - aggregator: PredictionErrorAggregator
    """
    visual = VisualPredictor()
    oscillator = OscillatorPredictor()
    emotional = EmotionalPredictor()
    conversational = ConversationalPredictor(
        keyword_index=keyword_index,
        dijkstra_recall=dijkstra_recall,
        memory_engine=memory_engine
    )

    aggregator = PredictionErrorAggregator(
        visual_predictor=visual,
        osc_predictor=oscillator,
        emotional_predictor=emotional,
        conversational_predictor=conversational
    )

    return {
        "visual_predictor": visual,
        "oscillator_predictor": oscillator,
        "emotional_predictor": emotional,
        "conversational_predictor": conversational,
        "aggregator": aggregator,
    }
