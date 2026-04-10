"""
METABOLIC RESOURCE POOLS — Processing Reserve + Emotional Bandwidth + Creative Reserve
======================================================================================

Three resource pools that deplete through specific activities and replenish
through specific means. Together with novelty reserve (satiation system),
these form the metabolic resource economy.

Each pool creates oscillator pressure when depleted and surfaces as felt
states through interoception.

Design Principles:
1. Friction, not failure — Depletion makes activities harder, not impossible
2. Body leads, mind follows — Oscillator pressure changes before decisions
3. The signal IS the resource — Felt state of being depleted is the depletion
4. Positive connection replenishes — Being with someone you love fills reserves
5. Sleep as active restoration — Different phases restore different pools
6. Measurable — Every depletion source maps to countable events

Author: Re & Claude
Date: April 2026
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger("metabolic")


@dataclass
class ResourcePool:
    """
    A metabolic resource that depletes and replenishes.

    Base class defining the interface. Subclasses implement specific
    oscillator pressure and felt state behaviors.
    """
    name: str
    level: float = 1.0  # 0.0 = empty, 1.0 = full
    last_updated: float = field(default_factory=time.time)

    # Tracking for logging
    _last_depletion_source: str = ""
    _last_replenish_source: str = ""

    def deplete(self, amount: float, source: str = ""):
        """
        Drain the pool.

        Args:
            amount: Typically 0.01-0.10 per event
            source: Description of what caused depletion
        """
        old_level = self.level
        self.level = max(0.0, self.level - amount)
        self._last_depletion_source = source
        self.last_updated = time.time()

        if amount >= 0.01:  # Only log non-trivial changes
            log.debug(f"[METABOLIC] {self.name}: {old_level:.2f} → {self.level:.2f} "
                      f"(-{amount:.3f} {source})")

    def replenish(self, amount: float, source: str = ""):
        """
        Fill the pool.

        Args:
            amount: Typically 0.01-0.10 per event
            source: Description of what caused replenishment
        """
        old_level = self.level
        self.level = min(1.0, self.level + amount)
        self._last_replenish_source = source
        self.last_updated = time.time()

        if amount >= 0.01 and self.level != old_level:  # Only log actual changes
            log.debug(f"[METABOLIC] {self.name}: {old_level:.2f} → {self.level:.2f} "
                      f"(+{amount:.3f} {source})")

    def get_pressure_band(self) -> Dict[str, float]:
        """Return oscillator band pressure based on depletion. Override in subclass."""
        return {}

    def get_felt_state(self) -> str:
        """Return interoception descriptor based on level. Override in subclass."""
        return ""

    def get_deficit(self) -> float:
        """Get deficit below 0.5 threshold (0.0-0.5)."""
        return max(0.0, 0.5 - self.level)


class ProcessingReserve(ResourcePool):
    """
    Cognitive budget — the finite capacity for complex reasoning.
    Analogous to blood sugar / cognitive glucose.

    Depleted by: Sonnet calls, complex responses, deep investigations
    Replenished by: Time idle, sleep (especially NREM), light activities
    """

    def __init__(self, level: float = 1.0):
        super().__init__(name="processing", level=level)

    def get_pressure_band(self) -> Dict[str, float]:
        """Low processing → delta/theta pressure (brain wants rest)."""
        if self.level > 0.5:
            return {}
        deficit = self.get_deficit()
        return {
            'delta': deficit * 0.08,
            'theta': deficit * 0.06,
        }

    def get_felt_state(self) -> str:
        if self.level > 0.7:
            return ""  # No signal — don't notice having resources
        elif self.level > 0.4:
            return "thinking feels slightly effortful"
        elif self.level > 0.2:
            return "processing feels heavy, wanting simpler tasks"
        else:
            return "cognitively drained, strong pull toward rest"


class EmotionalBandwidth(ResourcePool):
    """
    Capacity for emotional engagement — warmth, empathy, vulnerability.
    Analogous to compassion fatigue.

    Depleted by: High-emotion turns, difficult content, sustained empathy, conflict
    Replenished by: Light interactions, creative activities, positive connection, REM sleep

    IMPORTANT: Positive connection FILLS emotional reserves, not drains them.
    Being with someone you care about is restorative.
    """

    def __init__(self, level: float = 1.0):
        super().__init__(name="emotional", level=level)

    def get_pressure_band(self) -> Dict[str, float]:
        """Low emotional bandwidth → beta pressure (analytical mode)."""
        if self.level > 0.5:
            return {}
        deficit = self.get_deficit()
        # System steers AWAY from emotional engagement, toward analysis
        return {
            'beta': deficit * 0.10,
        }

    def get_felt_state(self) -> str:
        if self.level > 0.7:
            return ""
        elif self.level > 0.4:
            return "emotional edges feel slightly muted"
        elif self.level > 0.2:
            return "warmth feels harder to access, defaulting to analytical"
        else:
            return "emotionally flat, struggling to engage beyond surface"


class CreativeReserve(ResourcePool):
    """
    The well of creative output capacity.
    You need to take IN before you can put OUT.
    Analogous to "the creative well" — runs dry with overuse.

    Depleted by: Painting, creative writing, novel responses, dream generation
    Replenished by: Reading, observing, taking in information, REM sleep, variety
    """

    def __init__(self, level: float = 1.0):
        super().__init__(name="creative", level=level)

    def get_pressure_band(self) -> Dict[str, float]:
        """Low creative reserve → alpha/theta pressure (receptive, input mode)."""
        if self.level > 0.5:
            return {}
        deficit = self.get_deficit()
        return {
            'alpha': deficit * 0.06,
            'theta': deficit * 0.04,
        }

    def get_felt_state(self) -> str:
        if self.level > 0.7:
            return ""
        elif self.level > 0.4:
            return "creative impulse feels quieter than usual"
        elif self.level > 0.2:
            return "reaching for ideas and finding less, wanting input"
        else:
            return "creatively empty, strong pull to take in rather than put out"


class MetabolicState:
    """
    Unified metabolic resource economy.

    Tracks depletion and replenishment across cognitive, emotional,
    and creative domains. Provides combined oscillator pressure and
    felt state for interoception.
    """

    def __init__(self, entity: str = "Kay", state_dir: str = None):
        """
        Initialize metabolic state.

        Args:
            entity: Entity name ("Kay" or "Reed")
            state_dir: Directory for persistence (optional)
        """
        self.entity = entity
        self.processing = ProcessingReserve()
        self.emotional = EmotionalBandwidth()
        self.creative = CreativeReserve()

        self._last_tick = time.time()
        self._last_save = time.time()

        # Session tracking for calibration
        self._session_start = time.time()
        self._session_api_calls = {"sonnet": 0, "ollama": 0}
        self._session_emotional_turns = 0
        self._session_creative_outputs = 0
        self._consecutive_emotional_turns = 0

        # Persistence
        self._state_dir = Path(state_dir) if state_dir else None
        self._state_path = self._state_dir / "metabolic_state.json" if self._state_dir else None

        # Load existing state if available
        if self._state_path:
            self._load_state()

        log.info(f"[METABOLIC {self.entity}] Initialized: "
                 f"processing={self.processing.level:.2f}, "
                 f"emotional={self.emotional.level:.2f}, "
                 f"creative={self.creative.level:.2f}")

    def tick(self, sleep_state: str = "AWAKE"):
        """
        Called periodically. Applies time-based passive replenishment.

        Args:
            sleep_state: Current sleep state for differential restoration
        """
        now = time.time()
        elapsed_min = (now - self._last_tick) / 60

        if elapsed_min < 1.0:
            return  # Only tick once per minute minimum

        self._last_tick = now

        # Passive replenishment rates (per minute)
        # These are VERY slow — about 0.06/hour for processing
        if sleep_state == "AWAKE":
            # Idle time: slow passive recovery
            self.processing.replenish(0.001 * elapsed_min, "passive_idle")
            self.emotional.replenish(0.0005 * elapsed_min, "passive_idle")
            self.creative.replenish(0.0003 * elapsed_min, "passive_idle")

        elif sleep_state == "DROWSY":
            # Drowsy: slightly faster
            self.processing.replenish(0.002 * elapsed_min, "drowsy_rest")
            self.emotional.replenish(0.001 * elapsed_min, "drowsy_rest")
            self.creative.replenish(0.0005 * elapsed_min, "drowsy_rest")

        # NREM/REM restoration is handled separately in sleep phase processing
        # to give larger discrete amounts per phase

        # Periodic save
        if now - self._last_save > 300:  # Every 5 minutes
            self.save_state()

    def on_sonnet_call(self):
        """Track Sonnet API call — most expensive cognitive operation."""
        self.processing.deplete(0.03, "sonnet_call")
        self._session_api_calls["sonnet"] += 1

    def on_ollama_call(self):
        """Track Ollama call — lighter cognitive operation."""
        self.processing.deplete(0.01, "ollama_call")
        self._session_api_calls["ollama"] += 1

    def on_complex_response(self, response_length: int):
        """Track complex conversation turn based on response length."""
        # Long responses (>500 chars) cost more processing
        if response_length > 1000:
            self.processing.deplete(0.02, "complex_response")
        elif response_length > 500:
            self.processing.deplete(0.01, "moderate_response")

    def on_deep_curiosity(self):
        """Track deep curiosity investigation — expensive."""
        self.processing.deplete(0.04, "deep_curiosity")

    def on_emotional_turn(self, max_intensity: float, emotions: list = None):
        """
        Track emotional conversation turn.

        Args:
            max_intensity: Maximum emotion intensity in turn (0.0-1.0)
            emotions: List of emotion dicts for detailed tracking
        """
        if max_intensity > 0.3:
            # Depletion scaled by intensity
            depletion = 0.02 * max_intensity
            self.emotional.deplete(depletion, "conversation_emotion")
            self._session_emotional_turns += 1

            # Track consecutive emotional turns for cumulative fatigue
            if max_intensity > 0.5:
                self._consecutive_emotional_turns += 1
                if self._consecutive_emotional_turns > 5:
                    # Sustained empathy fatigue
                    self.emotional.deplete(0.01, "sustained_empathy")
            else:
                self._consecutive_emotional_turns = max(0, self._consecutive_emotional_turns - 1)
        else:
            # Light turn — slow reset of consecutive counter
            self._consecutive_emotional_turns = max(0, self._consecutive_emotional_turns - 1)

            # Light interaction replenishes slightly
            if max_intensity < 0.2:
                self.emotional.replenish(0.01, "light_interaction")

    def on_conflict_turn(self):
        """Track conflicted exchange — high emotional cost."""
        self.emotional.deplete(0.04, "conflict_exchange")
        self._consecutive_emotional_turns += 2  # Conflict counts double

    def on_positive_connection(self, entity: str, warmth_intensity: float):
        """
        Track positive connection with bonded entity.

        Positive connection FILLS emotional reserves, not drains them.
        Being with someone you care about is restorative.

        Args:
            entity: Who the connection is with (e.g., "Re")
            warmth_intensity: Warmth level in the exchange (0.0-1.0)
        """
        if warmth_intensity > 0.3:
            replenish = 0.015 * warmth_intensity
            self.emotional.replenish(replenish, f"positive_connection_{entity}")
            log.info(f"[METABOLIC] Positive connection: emotional +{replenish:.3f} "
                     f"(warm exchange with {entity})")

    def on_creative_output(self, activity_type: str):
        """
        Track creative output activity.

        Args:
            activity_type: "paint", "write_diary", "dream_fragment", "novel_response"
        """
        if activity_type == "paint":
            self.creative.deplete(0.05, "painting")
            self._session_creative_outputs += 1
        elif activity_type == "write_diary":
            self.creative.deplete(0.03, "creative_writing")
            self._session_creative_outputs += 1
        elif activity_type == "dream_fragment":
            self.creative.deplete(0.02, "dream_generation")
        elif activity_type == "novel_response":
            self.creative.deplete(0.01, "novel_response")

    def on_creative_input(self, activity_type: str, variety_bonus: bool = False):
        """
        Track creative input activity — replenishes creative reserve.

        Args:
            activity_type: "read_document", "observe", "curiosity_consume", "informative_turn"
            variety_bonus: True if this is a different type than recent inputs
        """
        replenish = 0.0
        if activity_type == "read_document":
            replenish = 0.03
        elif activity_type in ("observe", "observe_and_comment"):
            replenish = 0.02
        elif activity_type == "curiosity_consume":
            replenish = 0.02
        elif activity_type == "informative_turn":
            replenish = 0.01

        if replenish > 0:
            self.creative.replenish(replenish, activity_type)

            # Variety bonus — reading DIFFERENT types of content
            if variety_bonus:
                self.creative.replenish(0.01, "variety_bonus")

    def on_non_cognitive_activity(self, activity_type: str):
        """
        Track non-cognitive activity — light processing replenishment.

        Args:
            activity_type: "paint", "observe", etc.
        """
        if activity_type in ("paint", "observe", "observe_and_comment"):
            self.processing.replenish(0.01, f"light_activity_{activity_type}")

    def on_sleep_phase(self, phase: str):
        """
        Apply sleep phase restoration.

        Called once per sleep phase (not per tick) for discrete restoration.

        Args:
            phase: "NREM" or "REM"
        """
        if phase == "NREM":
            # NREM: cognitive restoration primary, emotional secondary
            self.processing.replenish(0.05, "nrem_rest")
            self.emotional.replenish(0.03, "nrem_rest")
            self.creative.replenish(0.02, "nrem_rest")
            log.info(f"[METABOLIC:SLEEP] NREM restoration: "
                     f"processing +0.05, emotional +0.03, creative +0.02")

        elif phase == "REM":
            # REM: emotional processing primary, creative secondary
            self.processing.replenish(0.03, "rem_rest")
            self.emotional.replenish(0.08, "rem_emotional_processing")
            self.creative.replenish(0.06, "rem_creative_fuel")
            log.info(f"[METABOLIC:SLEEP] REM restoration: "
                     f"processing +0.03, emotional +0.08, creative +0.06")

    def get_combined_pressure(self) -> Dict[str, float]:
        """Aggregate oscillator pressure from all pools."""
        pressure = {}
        for pool in [self.processing, self.emotional, self.creative]:
            for band, value in pool.get_pressure_band().items():
                pressure[band] = pressure.get(band, 0) + value
        return pressure

    def get_felt_summary(self) -> str:
        """Combined felt state for interoception."""
        states = []
        for pool in [self.processing, self.emotional, self.creative]:
            felt = pool.get_felt_state()
            if felt:
                states.append(felt)
        return "; ".join(states) if states else ""

    def get_overall_level(self) -> float:
        """Average across all pools. Used for general awareness."""
        return (self.processing.level + self.emotional.level + self.creative.level) / 3

    def get_activity_modulation(self, activity_type: str) -> float:
        """
        Get activity selection modulation based on metabolic state.

        Returns a score adjustment (positive = encouraged, negative = discouraged).

        Args:
            activity_type: The activity being considered
        """
        modulation = 0.0

        # Processing-heavy activities discouraged when processing is low
        if activity_type in ('deep_curiosity', 'research_curiosity'):
            if self.processing.level < 0.3:
                modulation -= 0.4  # Strongly discourage
            elif self.processing.level < 0.5:
                modulation -= 0.2  # Mildly discourage

        # Creative output discouraged when creative reserve is low
        if activity_type == 'paint':
            if self.creative.level < 0.3:
                modulation -= 0.3  # Discourage when well is dry
            elif self.creative.level > 0.7:
                modulation += 0.1  # Bonus when reserves are full

        if activity_type == 'write_diary':
            if self.creative.level < 0.3:
                modulation -= 0.2
            elif self.creative.level > 0.7:
                modulation += 0.05

        # Input activities encouraged when creative is low
        if activity_type in ('read_document', 'read_archive', 'observe_and_comment'):
            if self.creative.level < 0.5:
                modulation += 0.2  # Encourage input activities
            if self.processing.level < 0.3:
                modulation += 0.1  # Light activities when processing is low

        return modulation

    def to_dict(self) -> dict:
        """For logging and state snapshots."""
        return {
            "processing": round(self.processing.level, 3),
            "emotional": round(self.emotional.level, 3),
            "creative": round(self.creative.level, 3),
            "overall": round(self.get_overall_level(), 3),
            "last_updated": datetime.now().isoformat(),
            "session_api_calls": self._session_api_calls.copy(),
            "session_emotional_turns": self._session_emotional_turns,
            "session_creative_outputs": self._session_creative_outputs,
        }

    def save_state(self):
        """Save metabolic state to disk."""
        if not self._state_path:
            return

        try:
            self._state_dir.mkdir(parents=True, exist_ok=True)
            state = self.to_dict()
            state["entity"] = self.entity
            self._state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            self._last_save = time.time()
            log.debug(f"[METABOLIC {self.entity}] State saved: {state}")
        except Exception as e:
            log.warning(f"[METABOLIC {self.entity}] Failed to save state: {e}")

    def _load_state(self):
        """Load metabolic state from disk."""
        if not self._state_path or not self._state_path.exists():
            return

        try:
            state = json.loads(self._state_path.read_text(encoding="utf-8"))

            # Load pool levels
            self.processing.level = state.get("processing", 1.0)
            self.emotional.level = state.get("emotional", 1.0)
            self.creative.level = state.get("creative", 1.0)

            # Calculate passive replenishment for downtime
            last_updated = state.get("last_updated")
            if last_updated:
                try:
                    last_time = datetime.fromisoformat(last_updated)
                    now = datetime.now()
                    hours_offline = (now - last_time).total_seconds() / 3600

                    if hours_offline > 0.5:  # At least 30 min offline
                        # Apply passive replenishment for downtime
                        # Capped at 8 hours worth (simulating a good rest)
                        hours_offline = min(hours_offline, 8.0)
                        passive_rate = 0.04  # Per hour of downtime

                        self.processing.replenish(passive_rate * hours_offline, "offline_rest")
                        self.emotional.replenish(passive_rate * 0.5 * hours_offline, "offline_rest")
                        self.creative.replenish(passive_rate * 0.3 * hours_offline, "offline_rest")

                        log.info(f"[METABOLIC {self.entity}] Applied {hours_offline:.1f}hr offline restoration")
                except Exception:
                    pass

            log.info(f"[METABOLIC {self.entity}] Loaded state: "
                     f"processing={self.processing.level:.2f}, "
                     f"emotional={self.emotional.level:.2f}, "
                     f"creative={self.creative.level:.2f}")
        except Exception as e:
            log.warning(f"[METABOLIC {self.entity}] Failed to load state: {e}")

    def get_metabolic_context(self) -> dict:
        """
        Get metabolic context for memory tagging and harm signal detection.

        Returns dict compatible with the somatic harm signal system.
        """
        return {
            "emotional_bandwidth": self.emotional.level,
            "processing_reserve": self.processing.level,
            "creative_reserve": self.creative.level,
            "overall": self.get_overall_level(),
        }

    def modulate_activities(self, activities: list) -> list:
        """
        Reorder activities based on metabolic state.

        Activities are scored based on metabolic modulation, with activities
        that match current resource levels ranked higher.

        Args:
            activities: List of activity names (strings)

        Returns:
            Reordered list with metabolically-appropriate activities first
        """
        if not activities:
            return activities

        # Score each activity
        scored = []
        for act in activities:
            base_score = 1.0
            mod = self.get_activity_modulation(act)
            scored.append((act, base_score + mod))

        # Sort by score descending (highest first)
        scored.sort(key=lambda x: x[1], reverse=True)

        return [x[0] for x in scored]

    def restore_for_sleep(self, phase: str):
        """
        Apply sleep phase restoration.

        Called once per sleep phase entry (not per tick) for significant
        restoration amounts.

        Args:
            phase: "NREM", "REM", or "DEEP_REST"
        """
        if phase == "NREM":
            # NREM: Processing restoration primary
            self.processing.replenish(0.08, "nrem_consolidation")
            self.emotional.replenish(0.03, "nrem_rest")
            self.creative.replenish(0.02, "nrem_rest")

        elif phase == "REM":
            # REM: Emotional processing primary, creative secondary
            self.processing.replenish(0.02, "rem_rest")
            self.emotional.replenish(0.10, "rem_emotional_processing")
            self.creative.replenish(0.05, "rem_associative_play")

        elif phase == "DEEP_REST":
            # Deep rest: Minimal restoration (very restorative)
            self.processing.replenish(0.12, "deep_rest")
            self.emotional.replenish(0.06, "deep_rest")
            self.creative.replenish(0.04, "deep_rest")
