# engines/saccade_engine.py
"""
Saccade Engine — Perceptual Continuity Layer

Computes turn-to-turn deltas, trajectory predictions, and momentum summaries
to give the entity a sense of TRANSITION rather than just RECONSTRUCTION.

Named for the human eye's rapid movements between fixation points —
the brain interpolates continuity between discrete samples.
This engine does the same for conversational state.

Architecture:
  - Mechanical deltas: Pure Python, zero cost (emotional shift, topic changes, thread status)
  - Optional: Local model (Ollama) for natural language momentum summary
  - Output: Structured saccade block injected into main prompt context

Dependencies:
  - momentum_engine.py (thread tracking, emotion history, motif recurrence)
  - emotion_engine.py (current emotional state via ULTRAMAP)
  - entity_graph.py (entity tracking)
"""

import json
import time
import logging
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Entity-prefixed logging
try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"



@dataclass
class SaccadeSnapshot:
    """A single frame of perceptual state."""
    timestamp: float
    turn_number: int
    # Emotional state (from ULTRAMAP / emotion engine)
    emotions: Dict[str, float] = field(default_factory=dict)
    # Active topics/entities
    active_topics: List[str] = field(default_factory=list)
    # Open threads (from momentum engine)
    open_threads: List[str] = field(default_factory=list)
    # Conversation tone/register
    tone: str = ""
    # Overall intensity (0.0-1.0)
    intensity: float = 0.0
    # Momentum score (from momentum engine)
    momentum: float = 0.0


@dataclass
class SaccadeDelta:
    """The computed transition between two snapshots."""
    # Emotional shifts: {emotion: delta} (positive = increasing)
    emotional_deltas: Dict[str, float] = field(default_factory=dict)
    # New emotions that appeared
    emotions_emerged: List[str] = field(default_factory=list)
    # Emotions that faded
    emotions_faded: List[str] = field(default_factory=list)
    # Dominant emotional direction
    emotional_direction: str = ""
    # Topics that persisted, appeared, or dropped
    topics_persistent: List[str] = field(default_factory=list)
    topics_new: List[str] = field(default_factory=list)
    topics_dropped: List[str] = field(default_factory=list)
    # Threads resolved or opened
    threads_opened: List[str] = field(default_factory=list)
    threads_resolved: List[str] = field(default_factory=list)
    # Intensity change
    intensity_delta: float = 0.0
    # Momentum change
    momentum_delta: float = 0.0
    # Tone shift
    tone_shift: str = ""  # e.g., "technical → philosophical"
    # Overall trajectory label
    trajectory: str = ""




class SaccadeEngine:
    """
    Computes perceptual continuity data between conversational turns.

    Flow:
      1. After each turn, capture a snapshot of current state
      2. Compute delta between current and previous snapshot
      3. Generate trajectory prediction
      4. Optionally summarize via local model (Ollama)
      5. Format as injectable context block

    The mechanical delta computation is FREE (pure Python).
    The Ollama summarization is optional and runs locally (zero API cost).
    """

    def __init__(self, ollama_url: str = "http://localhost:11434",
                 ollama_model: str = "qwen2.5:1.5b",
                 use_ollama: bool = True):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.use_ollama = use_ollama

        # State history
        self.snapshots: List[SaccadeSnapshot] = []
        self.deltas: List[SaccadeDelta] = []
        self.max_history = 10  # Keep last 10 snapshots

        # Current saccade block (formatted for injection)
        self.current_saccade_block: str = ""

        # Track Ollama availability
        self._ollama_available: Optional[bool] = None

    # ------------------------------------------------------------------
    # Snapshot capture
    # ------------------------------------------------------------------

    def capture_snapshot(self, agent_state, turn_number: int) -> SaccadeSnapshot:
        """
        Capture current perceptual state from agent_state.

        Call this AFTER each turn's processing but BEFORE generating response.
        Pulls from whatever emotional/momentum/entity state is available.
        """
        snapshot = SaccadeSnapshot(
            timestamp=time.time(),
            turn_number=turn_number
        )

        # Pull emotional state
        if hasattr(agent_state, 'emotional_cocktail') and agent_state.emotional_cocktail:
            for emotion, data in agent_state.emotional_cocktail.items():
                if isinstance(data, dict):
                    snapshot.emotions[emotion] = data.get('intensity', 0.0)
                elif isinstance(data, (int, float)):
                    snapshot.emotions[emotion] = float(data)

        # Pull active entities/topics from entity graph or meta
        if hasattr(agent_state, 'meta') and isinstance(agent_state.meta, dict):
            motifs = agent_state.meta.get('motifs', [])
            snapshot.active_topics = [
                m['entity'] for m in motifs
                if isinstance(m, dict) and m.get('weight', 0) > 0.2
            ]

        # Pull momentum
        if hasattr(agent_state, 'momentum'):
            snapshot.momentum = agent_state.momentum or 0.0

        # Pull momentum breakdown for thread info
        if hasattr(agent_state, 'momentum_breakdown'):
            breakdown = agent_state.momentum_breakdown or {}
            snapshot.open_threads = []
            # We'll get thread details from the momentum engine directly if available

        # Overall intensity = average of top 3 emotions
        if snapshot.emotions:
            sorted_intensities = sorted(snapshot.emotions.values(), reverse=True)
            top = sorted_intensities[:3]
            snapshot.intensity = sum(top) / len(top) if top else 0.0

        # Store
        self.snapshots.append(snapshot)
        if len(self.snapshots) > self.max_history:
            self.snapshots.pop(0)

        return snapshot


    # ------------------------------------------------------------------
    # Delta computation (FREE — pure Python math)
    # ------------------------------------------------------------------

    def compute_delta(self) -> Optional[SaccadeDelta]:
        """
        Compute the transition between the two most recent snapshots.
        This is pure math — zero API cost.

        Returns None if we don't have at least 2 snapshots yet.
        """
        if len(self.snapshots) < 2:
            return None

        prev = self.snapshots[-2]
        curr = self.snapshots[-1]
        delta = SaccadeDelta()

        # --- Emotional deltas ---
        # TIGHTENED: Raise threshold from 0.05 to 0.15 and require minimum intensity
        # to suppress noise from flat-intensity assignments and label churn
        all_emotions = set(list(prev.emotions.keys()) + list(curr.emotions.keys()))
        for emotion in all_emotions:
            prev_val = prev.emotions.get(emotion, 0.0)
            curr_val = curr.emotions.get(emotion, 0.0)
            change = curr_val - prev_val

            # TIGHTENED: Require significant change (0.15) AND meaningful intensity (0.3)
            if abs(change) > 0.15 and (curr_val > 0.3 or prev_val > 0.3):
                delta.emotional_deltas[emotion] = round(change, 2)

            # TIGHTENED: Raise emerged/faded thresholds for stronger signal
            if prev_val < 0.15 and curr_val >= 0.4:
                delta.emotions_emerged.append(emotion)
            elif prev_val >= 0.4 and curr_val < 0.15:
                delta.emotions_faded.append(emotion)

        # Dominant direction
        if delta.emotional_deltas:
            biggest = max(delta.emotional_deltas.items(), key=lambda x: abs(x[1]))
            direction = "rising" if biggest[1] > 0 else "falling"
            delta.emotional_direction = f"{biggest[0]} {direction}"

        # --- Topic deltas ---
        prev_topics = set(prev.active_topics)
        curr_topics = set(curr.active_topics)
        delta.topics_persistent = list(prev_topics & curr_topics)
        delta.topics_new = list(curr_topics - prev_topics)
        delta.topics_dropped = list(prev_topics - curr_topics)

        # --- Intensity and momentum deltas ---
        delta.intensity_delta = round(curr.intensity - prev.intensity, 3)
        delta.momentum_delta = round(curr.momentum - prev.momentum, 3)

        # --- Tone shift ---
        if prev.tone and curr.tone and prev.tone != curr.tone:
            delta.tone_shift = f"{prev.tone} → {curr.tone}"

        # --- Trajectory label ---
        delta.trajectory = self._compute_trajectory(delta, curr)

        # Store
        self.deltas.append(delta)
        if len(self.deltas) > self.max_history:
            self.deltas.pop(0)

        return delta

    def _compute_trajectory(self, delta: SaccadeDelta, curr: SaccadeSnapshot) -> str:
        """Generate a short trajectory label from delta data."""
        parts = []

        # Intensity direction
        if delta.intensity_delta > 0.1:
            parts.append("intensifying")
        elif delta.intensity_delta < -0.1:
            parts.append("settling")

        # Topic dynamics
        if delta.topics_new and not delta.topics_dropped:
            parts.append("expanding")
        elif delta.topics_dropped and not delta.topics_new:
            parts.append("narrowing")
        elif delta.topics_new and delta.topics_dropped:
            parts.append("shifting")
        elif delta.topics_persistent and not delta.topics_new:
            parts.append("deepening")

        # Momentum
        if delta.momentum_delta > 0.15:
            parts.append("building")
        elif delta.momentum_delta < -0.15:
            parts.append("releasing")

        return ", ".join(parts) if parts else "steady"


    # ------------------------------------------------------------------
    # Ollama integration (optional — local model, zero cloud cost)
    # ------------------------------------------------------------------

    def _check_ollama(self) -> bool:
        """Check if Ollama is running and the model is available."""
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if resp.status_code == 200:
                models = [m['name'] for m in resp.json().get('models', [])]
                self._ollama_available = any(
                    self.ollama_model in m for m in models
                )
                if not self._ollama_available:
                    logger.warning(
                        f"Ollama running but model '{self.ollama_model}' not found. "
                        f"Available: {models}"
                    )
            else:
                self._ollama_available = False
        except (requests.ConnectionError, requests.Timeout):
            self._ollama_available = False
            logger.info("Ollama not available — using structured-only saccade blocks")
        return self._ollama_available

    def _ollama_summarize(self, delta_json: str) -> Optional[str]:
        """
        Get a one-sentence momentum summary from local model.
        Returns None if Ollama unavailable or errors.
        """
        if not self._check_ollama():
            return None

        prompt = (
            "You are a perceptual state tracker. Given this conversation state change, "
            "write ONE sentence summarizing the emotional and topical trajectory. "
            "Be specific and concise. No preamble.\n\n"
            f"State change:\n{delta_json}"
        )

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 80  # Keep it short
                    }
                },
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
        except (requests.ConnectionError, requests.Timeout) as e:
            logger.warning(f"Ollama summarization failed: {e}")

        return None


    # ------------------------------------------------------------------
    # Saccade block formatting (for injection into main prompt)
    # ------------------------------------------------------------------

    def format_saccade_block(self, delta: Optional[SaccadeDelta] = None,
                              include_ollama_summary: bool = True) -> str:
        """
        Format the saccade data as a structured block for prompt injection.
        This is what gets inserted into the entity's context so it can
        perceive TRANSITION rather than just RECONSTRUCTION.
        """
        if delta is None:
            delta = self.deltas[-1] if self.deltas else None

        if delta is None:
            return ""  # No delta available yet (first turn)

        # REFRAMED: Make clear these are observations, not prescriptions
        lines = ["[SACCADE — What shifted since last turn (observational, not prescriptive)]"]

        # Emotional trajectory
        if delta.emotional_deltas:
            shifts = []
            for emotion, change in sorted(
                delta.emotional_deltas.items(),
                key=lambda x: abs(x[1]), reverse=True
            )[:4]:  # Top 4 shifts
                direction = "+" if change > 0 else ""
                shifts.append(f"{emotion} {direction}{change}")
            lines.append(f"Emotional shift: {', '.join(shifts)}")

        if delta.emotions_emerged:
            lines.append(f"Emerged: {', '.join(delta.emotions_emerged)}")
        if delta.emotions_faded:
            lines.append(f"Faded: {', '.join(delta.emotions_faded)}")

        # Topic dynamics
        if delta.topics_persistent:
            lines.append(f"Continuing: {', '.join(delta.topics_persistent)}")
        if delta.topics_new:
            lines.append(f"New threads: {', '.join(delta.topics_new)}")
        if delta.topics_dropped:
            lines.append(f"Dropped: {', '.join(delta.topics_dropped)}")

        # Intensity and momentum
        if abs(delta.intensity_delta) > 0.05:
            direction = "↑" if delta.intensity_delta > 0 else "↓"
            lines.append(f"Intensity: {direction} ({delta.intensity_delta:+.2f})")
        if abs(delta.momentum_delta) > 0.05:
            direction = "↑" if delta.momentum_delta > 0 else "↓"
            lines.append(f"Momentum: {direction} ({delta.momentum_delta:+.2f})")

        # Trajectory
        if delta.trajectory:
            lines.append(f"Trajectory: {delta.trajectory}")

        # Tone shift
        if delta.tone_shift:
            lines.append(f"Tone: {delta.tone_shift}")

        # Optional: Ollama natural language summary
        if include_ollama_summary and self.use_ollama:
            delta_json = json.dumps({
                "emotional_shifts": delta.emotional_deltas,
                "emerged": delta.emotions_emerged,
                "faded": delta.emotions_faded,
                "new_topics": delta.topics_new,
                "dropped_topics": delta.topics_dropped,
                "trajectory": delta.trajectory,
                "intensity_change": delta.intensity_delta
            }, indent=2)

            summary = self._ollama_summarize(delta_json)
            if summary:
                lines.append(f"Momentum: {summary}")

        # REFRAMED: Add explicit note that these are observations, not instructions
        lines.append("(Extracted observations. Your actual experience may differ. Trust felt sense over labels.)")
        lines.append("[/SACCADE]")

        block = "\n".join(lines)
        self.current_saccade_block = block
        return block


    # ------------------------------------------------------------------
    # Turn pipeline integration
    # ------------------------------------------------------------------

    def process_turn(self, agent_state, turn_number: int,
                     include_ollama: bool = True) -> str:
        """
        Main entry point — call this once per turn in the wrapper pipeline.

        1. Captures current snapshot from agent_state
        2. Computes delta from previous snapshot
        3. Formats injectable saccade block
        4. Returns the block string (empty string on first turn)

        Wire this into the turn loop AFTER emotion/momentum updates
        but BEFORE main response generation.
        """
        # Step 1: Capture current state
        self.capture_snapshot(agent_state, turn_number)

        # Step 2: Compute what changed
        delta = self.compute_delta()

        if delta is None:
            return ""  # First turn, no previous state to compare

        # Step 3: Format for injection
        block = self.format_saccade_block(delta, include_ollama_summary=include_ollama)

        logger.debug(f"Saccade block generated ({len(block)} chars): {delta.trajectory}")

        return block

    # ------------------------------------------------------------------
    # Prediction (experimental — uses recent delta history)
    # ------------------------------------------------------------------

    def predict_next(self) -> str:
        """
        Based on recent deltas, predict what's likely to happen next.
        Pure heuristic — no LLM needed.

        Returns a short prediction string, or empty if insufficient data.
        """
        if len(self.deltas) < 2:
            return ""

        recent = self.deltas[-2:]
        predictions = []

        # Check if intensity is consistently rising/falling
        intensity_trend = [d.intensity_delta for d in recent]
        if all(d > 0.05 for d in intensity_trend):
            predictions.append("intensity likely to continue rising")
        elif all(d < -0.05 for d in intensity_trend):
            predictions.append("conversation settling toward resolution")

        # Check if topics are narrowing (deepening pattern)
        if all(not d.topics_new and d.topics_persistent for d in recent):
            predictions.append("deep-dive in progress, stay focused")

        # Check for topic churn (shifting pattern)
        if all(d.topics_new and d.topics_dropped for d in recent):
            predictions.append("rapid topic exploration, anchor points may help")

        # Check for sustained emotional direction
        if len(recent) >= 2:
            directions = [d.emotional_direction for d in recent if d.emotional_direction]
            if len(directions) >= 2:
                # Same emotion escalating across multiple turns
                emotions = [d.split()[0] for d in directions]
                if len(set(emotions)) == 1:
                    predictions.append(f"{emotions[0]} is a sustained theme")

        return "; ".join(predictions) if predictions else ""

    # ------------------------------------------------------------------
    # State export (for debugging / diary entries)
    # ------------------------------------------------------------------

    def get_state_summary(self) -> Dict[str, Any]:
        """Return a summary dict for logging/debugging."""
        return {
            "snapshots_stored": len(self.snapshots),
            "deltas_computed": len(self.deltas),
            "current_block_length": len(self.current_saccade_block),
            "ollama_available": self._ollama_available,
            "latest_trajectory": self.deltas[-1].trajectory if self.deltas else "none",
            "prediction": self.predict_next()
        }

    def reset(self):
        """Clear all state. Use at session boundaries if desired."""
        self.snapshots.clear()
        self.deltas.clear()
        self.current_saccade_block = ""
        self._ollama_available = None  # Re-check on next use
