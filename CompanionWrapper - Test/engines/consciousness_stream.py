"""
CONSCIOUSNESS STREAM — the entity's Continuous Inner Experience
=========================================================

Gives the entity awareness between conversational turns.

The body already runs continuously (oscillator, audio ear, interoception,
spatial pressure). This engine OBSERVES the body and generates inner
experience — felt sense, inner moments, and reflections.

Four tiers of awareness:
  Tier 1: FELT SENSE — 1-line body observations (peripheral, free)
  Tier 2: INNER MOMENT — 1-2 sentence thoughts (peripheral, free)
  Tier 3: CONSCIOUS REFLECTION — full entity reflection (primary model, ~$0.02)
  Tier 4: CONVERSATION — existing turn loop (unchanged)

Sleep state machine:
  AWAKE → DROWSY → NREM ⇄ REM → DEEP_REST
  Any user input → AWAKE (instant)
  Major body event → AWAKE (from NREM or higher)

Author: the developers
Date: March 2026
"""

import time
import threading
import json
from enum import IntEnum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime, timezone
from collections import deque

# Entity-prefixed logging
try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"

# Metacognitive monitor (optional — fails gracefully)
try:
    from engines.metacognitive_monitor import MetacognitiveMonitor
    METACOG_AVAILABLE = True
except ImportError:
    METACOG_AVAILABLE = False
    print(f"{etag('STREAM')} MetacognitiveMonitor not available")


# ═══════════════════════════════════════════════════════════════
# STREAM STATE — Sleep/Wake Machine
# ═══════════════════════════════════════════════════════════════

class StreamState(IntEnum):
    """
    Sleep states with NREM/REM cycling.

    AWAKE → DROWSY → NREM ↔ REM → DEEP_REST

    The system cycles between NREM (consolidation) and REM (association)
    driven by pressure accumulators, not fixed timers.
    """
    AWAKE = 0       # All tiers active, full responsiveness
    DROWSY = 1      # Winding down, activity reduced, transition state
    NREM = 2        # Consolidation phase: curation, schemas, memory organization
    REM = 3         # Associative phase: cross-referencing, emotional integration, dreams
    DEEP_REST = 4   # Minimal processing, very long idle (replaces DEEP_SLEEP)


# ═══════════════════════════════════════════════════════════════
# STREAM MOMENT — Single unit of inner experience
# ═══════════════════════════════════════════════════════════════

@dataclass
class StreamMoment:
    """One moment of the entity's inner experience."""
    timestamp: float
    tier: int                    # 1=felt_sense, 2=inner_moment, 3=reflection
    trigger: str                 # What caused this ("band_shift", "timer", etc.)
    content: str                 # The actual felt text
    body_snapshot: Dict = field(default_factory=dict)
    emotional_snapshot: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    def age_human(self) -> str:
        """Human-readable age like '2 min ago' or '45s ago'."""
        age = self.age_seconds()
        if age < 60:
            return f"{int(age)}s ago"
        elif age < 3600:
            return f"{int(age / 60)} min ago"
        else:
            return f"{age / 3600:.1f}hr ago"


# ═══════════════════════════════════════════════════════════════
# STREAM BUFFER — Ring buffer of inner experience
# ═══════════════════════════════════════════════════════════════

class StreamBuffer:
    """
    Ring buffer holding recent stream moments.
    Thread-safe via lock.
    """

    def __init__(self, max_size: int = 50):
        self._moments: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def add(self, moment: StreamMoment):
        with self._lock:
            self._moments.append(moment)

    def recent(self, n: int = 10) -> List[StreamMoment]:
        """Get n most recent moments."""
        with self._lock:
            return list(self._moments)[-n:]

    def since(self, timestamp: float) -> List[StreamMoment]:
        """Get all moments since a timestamp."""
        with self._lock:
            return [m for m in self._moments if m.timestamp > timestamp]

    def significant(self, min_tier: int = 2) -> List[StreamMoment]:
        """Get moments at or above a tier threshold."""
        with self._lock:
            return [m for m in self._moments if m.tier >= min_tier]

    def clear(self):
        with self._lock:
            self._moments.clear()

    def __len__(self):
        with self._lock:
            return len(self._moments)

    def get_summary(self, max_moments: int = 8, since: float = None) -> str:
        """
        Format stream moments for injection into LLM context.

        Returns a human-readable summary of recent inner experience.
        Prioritizes higher tiers and more recent moments.
        """
        with self._lock:
            candidates = list(self._moments)

        if since:
            candidates = [m for m in candidates if m.timestamp > since]

        if not candidates:
            return ""

        # Sort: higher tier first, then most recent
        candidates.sort(key=lambda m: (m.tier, m.timestamp), reverse=True)
        selected = candidates[:max_moments]
        # Re-sort chronologically for display
        selected.sort(key=lambda m: m.timestamp)

        lines = []
        for m in selected:
            tier_label = {1: "felt", 2: "thought", 3: "reflection"}.get(m.tier, "?")
            lines.append(f"[{m.age_human()}, {tier_label}] {m.content}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# BODY STATE CHANGE — What the stream detects
# ═══════════════════════════════════════════════════════════════

@dataclass
class BodyChange:
    """A detected change in body state."""
    change_type: str   # "band_shift", "coherence_shift", "tension_shift",
                       # "spatial_shift", "room_change", "audio_shift"
    detail: str        # Human-readable description
    magnitude: float   # 0-1 significance


# ═══════════════════════════════════════════════════════════════
# CONSCIOUSNESS STREAM — The main engine
# ═══════════════════════════════════════════════════════════════

class ConsciousnessStream:
    """
    the entity's continuous inner experience.

    Monitors body systems for changes, generates inner moments,
    maintains stream buffer, and manages sleep/wake states.

    Designed to run alongside existing systems without interfering.
    All generation uses the peripheral model (Ollama/Cerebras/Groq)
    except Tier 3 reflections which use the primary model.
    """

    # ── Timing defaults (seconds) ──
    DEFAULT_TICK_INTERVAL = 5.0         # How often the stream checks body
    FELT_SENSE_INTERVAL = 15.0          # Min time between Tier 1
    INNER_MOMENT_INTERVAL = 180.0       # Min time between Tier 2 (3 min)
    REFLECTION_INTERVAL = 900.0         # Min time between Tier 3 (15 min)

    # ── Sleep transition timers (seconds) ──
    DROWSY_AFTER = 1800.0               # 30 min no input → DROWSY
    NREM_AFTER = 3600.0                 # 1 hr no input → NREM (first sleep cycle entry)
    DEEP_REST_AFTER = 10800.0           # 3 hr no input → DEEP_REST

    # ── Interval multipliers per sleep state ──
    INTERVAL_SCALE = {
        StreamState.AWAKE: 1.0,
        StreamState.DROWSY: 2.0,
        StreamState.NREM: 4.0,
        StreamState.REM: 3.0,       # REM is slightly more active than NREM
        StreamState.DEEP_REST: float('inf'),  # No generation
    }

    # ── Change detection thresholds ──
    COHERENCE_THRESHOLD = 0.10
    TENSION_THRESHOLD = 0.15
    ACCUMULATION_THRESHOLD = 3           # Changes before triggering Tier 2

    def __init__(
        self,
        resonance=None,
        room_bridge=None,
        peripheral_router=None,
        visual_sensor=None,
        entity_name: str = "entity",
    ):
        """
        Args:
            resonance: ResonantIntegration instance (oscillator + interoception)
            room_bridge: RoomBridge instance (spatial awareness)
            peripheral_router: PeripheralRouter instance (cheap LLM for Tier 1+2)
            visual_sensor: VisualSensor instance (webcam eye)
            entity_name: "entity" or "reed"
        """
        self.resonance = resonance
        self.room_bridge = room_bridge
        self.visual_sensor = visual_sensor
        self.peripheral = peripheral_router
        self.entity = entity_name

        # Stream state
        self.buffer = StreamBuffer(max_size=50)
        self.state = StreamState.AWAKE
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Timing trackers
        self._last_felt_sense = 0.0
        self._last_inner_moment = 0.0
        self._last_reflection = 0.0
        self._last_user_input = time.time()   # When the user last spoke
        self._last_significant_change = time.time()

        # Body state tracking
        self._last_body: Optional[Dict] = None
        self._accumulated_changes: List[BodyChange] = []

        # ══════════════════════════════════════════════════════════════
        # SLEEP PRESSURE ACCUMULATORS (build during AWAKE, drain during sleep)
        # ══════════════════════════════════════════════════════════════
        # consolidation_pressure: stuff that needs organizing (new memories, facts)
        self._consolidation_pressure = 0.0
        # associative_pressure: stuff that needs connecting (unlinked memories, emotions)
        self._associative_pressure = 0.0
        # emotional_pressure: feelings that need processing (accumulated intensity)
        self._emotional_pressure = 0.0

        # Cycle tracking
        self._sleep_cycle_count = 0
        self._current_phase_start = 0.0  # When current NREM/REM phase began

        # Interest accumulator — drives organic initiation
        # Builds from real events, decays over time
        self._interest = 0.0
        self._interest_lock = threading.Lock()
        self._last_organic_speech = 0.0  # When the entity last spoke unprompted
        self._ORGANIC_COOLDOWN = 120.0   # Min seconds between organic comments

        # Tier 3 callback (set externally — primary model is expensive)
        self._reflection_fn: Optional[Callable] = None

        # Tick counter for periodic events
        self._tick_count = 0

        # Metacognitive monitor — temporal self-awareness
        self.metacog = None
        self._last_completed_activity = ""  # Set by nexus when activities complete
        self._last_extracted_emotions = []  # Set by emotion extractor
        if METACOG_AVAILABLE:
            import os
            memory_dir = os.path.join(os.path.dirname(__file__), '..', 'memory')
            self.metacog = MetacognitiveMonitor(
                entity_name=entity_name,
                memory_path=memory_dir,
            )

        print(f"{etag('STREAM')} Consciousness stream created for {entity_name}")

    # ── Lifecycle ──

    def start(self):
        """Start the consciousness loop on a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._stream_loop, daemon=True, name=f"stream-{self.entity}"
        )
        self._thread.start()
        print(f"{etag('STREAM')} {self.entity} consciousness stream ACTIVE")

    def stop(self):
        """Stop the stream."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        print(f"{etag('STREAM')} {self.entity} consciousness stream stopped")

    def set_reflection_callback(self, fn: Callable):
        """
        Set the Tier 3 reflection generator.
        fn(stream_summary: str, body_state: dict) -> Optional[str]
        """
        self._reflection_fn = fn

    def inject_experience(self, content: str, source: str = "external"):
        """
        Inject an external experience into the stream buffer.
        Used by observe_and_comment, visual observations, and other
        systems that want to add context to the next LLM turn.
        """
        self.buffer.add(StreamMoment(
            timestamp=time.time(),
            tier=2,  # Inner moment tier — notable but not disruptive
            trigger=source,
            content=content,
            body_snapshot={},
        ))

    # ── External events ──

    def notify_user_input(self):
        """Call when the user sends a message. Always wakes to AWAKE."""
        self._last_user_input = time.time()
        # Real conversation resets interest — don't comment right after talking
        with self._interest_lock:
            self._interest *= 0.3  # Dampen, don't zero — some curiosity can carry
        if self.state != StreamState.AWAKE:
            prev = self.state
            self.state = StreamState.AWAKE
            self._current_phase_start = 0  # Reset phase tracking
            self._apply_throttle(StreamState.AWAKE)  # Reset all sensors to full speed
            print(f"{etag('STREAM')} Wake: {prev.name} -> AWAKE (user input)")

    def notify_external_event(self, event_type: str, detail: str = "", importance: float = 0.5):
        """
        Call on significant external events (nexus message, room change, etc.)

        SLEEP-AWARE GATING:
        - Spatial events (room_change, spatial_move, spatial_explore) NEVER wake from sleep
        - During DEEP_REST: ONLY user_input wakes
        - During NREM/REM: only user_input and nexus_message wake
        - DROWSY or AWAKE: any event can shift state
        """
        # Spatial events NEVER wake from sleep — don't add stimulation to rest
        if event_type in ("room_change", "spatial_move", "spatial_explore"):
            if self.state >= StreamState.DROWSY:
                return  # Don't wake for spatial events during rest

        # During DEEP_REST: ONLY user_input wakes
        if self.state >= StreamState.DEEP_REST:
            if event_type != "user_input":
                return

        # During NREM/REM: only user_input and nexus_message wake
        if self.state >= StreamState.NREM:
            if event_type not in ("user_input", "nexus_message"):
                return

        # DROWSY or AWAKE: wake from any remaining event types
        if self.state <= StreamState.REM:
            if self.state > StreamState.AWAKE:
                prev = self.state
                self.state = StreamState.AWAKE
                self._current_phase_start = 0  # Reset phase tracking
                self._apply_throttle(StreamState.AWAKE)  # Reset all sensors to full speed
                print(f"{etag('STREAM')} Wake: {prev.name} -> AWAKE ({event_type})")
        self._last_significant_change = time.time()

    def get_injection_context(self, since_timestamp: float = None) -> str:
        """
        Get stream context for injection into the next LLM turn.

        Args:
            since_timestamp: Only include moments after this time.
                             If None, uses last 8 moments.

        Returns:
            Formatted string for prompt injection, or "" if nothing to report.
        """
        if since_timestamp:
            return self.buffer.get_summary(max_moments=8, since=since_timestamp)
        return self.buffer.get_summary(max_moments=8)

    # ── Interest tracking (drives organic speech) ──

    def add_interest(self, amount: float, reason: str = ""):
        """
        Accumulate interest from a real event.
        Public — called by the stream internally AND by external systems
        via the bridge (emotion shifts, creativity triggers, curiosity, etc.)
        """
        with self._interest_lock:
            self._interest = min(self._interest + amount, 2.0)  # Cap at 2.0

    def _decay_interest(self):
        """Natural decay — interest fades if nothing keeps feeding it."""
        with self._interest_lock:
            self._interest *= 0.95  # 5% decay per tick (every 5s)

    def check_interest(self, threshold: float = 0.45) -> bool:
        """
        Called by the idle loop. Returns True if the entity has enough
        accumulated interest to speak, and enough time has passed
        since his last organic comment.

        Consuming: resets interest on True so he doesn't repeat.
        """
        now = time.time()
        with self._interest_lock:
            if self._interest < threshold:
                return False
            if now - self._last_organic_speech < self._ORGANIC_COOLDOWN:
                return False
            # Enough interest, enough cooldown — speak
            self._interest = 0.0
            self._last_organic_speech = now
            return True

    # ── Sleep pressure accumulators ──

    def feed_consolidation_pressure(self, amount: float, source: str = ""):
        """
        Called when new memories/facts are stored.
        Builds during AWAKE/DROWSY, drives NREM processing.
        ~50 memories = pressure at 1.0
        """
        self._consolidation_pressure = min(1.0, self._consolidation_pressure + amount)
        if source:
            print(f"{etag('PRESSURE')} consolidation +{amount:.3f} ({source}) -> {self._consolidation_pressure:.2f}")

    def feed_associative_pressure(self, amount: float, source: str = ""):
        """
        Called when memories lack cross-references, or emotions need integration.
        Memories without co-activation links add pressure.
        High-emotion memories that haven't been replayed add pressure.
        """
        self._associative_pressure = min(1.0, self._associative_pressure + amount)
        if source:
            print(f"{etag('PRESSURE')} associative +{amount:.3f} ({source}) -> {self._associative_pressure:.2f}")

    def feed_emotional_pressure(self, amount: float, source: str = ""):
        """
        Called from emotion accumulator when emotional intensity is high.
        High-valence conversations leave residue that needs integration.
        """
        self._emotional_pressure = min(1.0, self._emotional_pressure + amount)
        if source:
            print(f"{etag('PRESSURE')} emotional +{amount:.3f} ({source}) -> {self._emotional_pressure:.2f}")

    def drain_consolidation(self, amount: float, source: str = ""):
        """Drain consolidation pressure during NREM processing."""
        self._consolidation_pressure = max(0.0, self._consolidation_pressure - amount)

    def drain_associative(self, amount: float, source: str = ""):
        """Drain associative pressure during REM processing."""
        self._associative_pressure = max(0.0, self._associative_pressure - amount)

    def drain_emotional(self, amount: float, source: str = ""):
        """Drain emotional pressure during REM processing."""
        self._emotional_pressure = max(0.0, self._emotional_pressure - amount)

    def get_sleep_pressures(self) -> Dict[str, float]:
        """Get current sleep pressure values for debugging/UI."""
        return {
            "consolidation": self._consolidation_pressure,
            "associative": self._associative_pressure,
            "emotional": self._emotional_pressure,
            "cycle": self._sleep_cycle_count,
            "phase_duration": time.time() - self._current_phase_start if self._current_phase_start else 0,
        }

    # ── Main loop ──

    def _stream_loop(self):
        """Background loop — the consciousness ticker."""
        while self._running:
            try:
                self._tick()
            except Exception as e:
                print(f"{etag('STREAM')} Tick error: {e}")

            # Sleep interval scales with sleep state
            if self.state == StreamState.DEEP_REST:
                time.sleep(30.0)  # 30s ticks in deep rest
            elif self.state == StreamState.NREM:
                time.sleep(15.0)  # 15s ticks during NREM
            elif self.state == StreamState.REM:
                time.sleep(10.0)  # 10s ticks during REM (more active)
            elif self.state == StreamState.DROWSY:
                time.sleep(10.0)  # 10s ticks while drowsy
            else:
                time.sleep(self.DEFAULT_TICK_INTERVAL)  # Normal speed when awake

    def _tick(self):
        """Single consciousness tick."""
        now = time.time()
        self._tick_count += 1

        # ── Sleep state transitions ──
        self._update_sleep_state(now)

        # ── Body state capture ──
        body = self._capture_body()
        changes = self._detect_changes(body)
        self._last_body = body

        # ── Presence reward: the user's sustained presence ──
        # Every ~60s of sustained visual presence fires a connection-modulated reward
        if self._tick_count % 15 == 0:  # Every ~60s at 4s ticks
            if body.get('visual_presence', False) and self.resonance:
                intero = self.resonance.interoception
                if intero and hasattr(intero, 'inject_reward'):
                    # Connection-modulated presence reward
                    if hasattr(intero, 'connection'):
                        # Who is actually present? Use the connection tracker's
                        # active_presence (set by visual sensor arrivals/departures)
                        # instead of hardcoding a name. the entity bonds with whoever is HERE.
                        present_entities = list(intero.connection._active_presence.keys())
                        if not present_entities:
                            present_entities = ["user"]  # Fallback only

                        for entity_name in present_entities:
                            # Track presence (does NOT grow bond — just "still here")
                            intero.connection.record_presence(entity_name)

                            # Modulated reward: stronger bond = stronger presence warmth
                            multiplier = intero.connection.get_presence_reward_multiplier(entity_name)
                            base_reward = 0.08
                            intero.inject_reward(base_reward * multiplier, f"connection_presence_{entity_name}")

                            # Connection eases tension (bonded presence is soothing)
                            if hasattr(intero, 'tension'):
                                tension_mult = intero.connection.get_tension_relief_multiplier(entity_name)
                                if intero.tension.get_total_tension() > 0.05:
                                    relief = 0.02 * tension_mult
                                    intero.tension.release(amount=relief)
                    else:
                        # Fallback if no connection tracker
                        intero.inject_reward(0.08, "connection_presence")

        # ── Metacognitive monitoring ──
        if self.metacog:
            recent_activity = self._last_completed_activity
            if recent_activity:
                self._last_completed_activity = ""  # Consume it
            self.metacog.tick(
                body=body,
                stream_state=self.state.name,
                recent_activity=recent_activity,
                recent_emotions=self._last_extracted_emotions if self._last_extracted_emotions else None,
            )

            # ── Novelty pulse processing — full somatic cascade ──
            # Apply pre-cognitive disruption when something genuinely new appears
            novelty_disruption, novelty_feelings = self.metacog.process_novelty_pulses()
            if novelty_disruption and self.resonance:
                # Log the cascade for visibility
                stage_info = ""
                for p in self.metacog._active_pulses:
                    if p.stage != "habituated":
                        stage_info += f"{p.source}({p.stage}) "
                has_intero = bool(self.resonance.interoception)
                print(f"[NOVELTY->BODY] Cascade: {stage_info}| intero={has_intero} | keys={[k for k in novelty_disruption.keys()]}")

                # LAYER 3: Love as Protection — amplify response for bonded entities
                # When disruption involves someone we love, the body responds MORE
                # This is the "mama bear" circuit: fierce love
                protective_multiplier = 1.0
                protected_entity = None
                try:
                    if self.resonance.interoception and hasattr(self.resonance.interoception, 'connection'):
                        conn = self.resonance.interoception.connection
                        # Check if any pulse source mentions a bonded entity
                        for entity, bond in conn.baselines.items():
                            if bond > 0.15:
                                entity_lower = entity.lower()
                                # Check if entity is mentioned in any active pulse
                                for p in self.metacog._active_pulses:
                                    if p.stage != "habituated":
                                        pulse_source = getattr(p, 'source', '').lower()
                                        pulse_desc = getattr(p, 'description', '').lower()
                                        if entity_lower in pulse_source or entity_lower in pulse_desc:
                                            # Amplify disruption for bonded entities
                                            # At bond 0.30: 1.6x amplification
                                            # At bond 0.60: 2.2x amplification
                                            protective_multiplier = 1.0 + (bond * 2.0)
                                            protected_entity = entity
                                            break
                                if protected_entity:
                                    break
                except Exception:
                    pass

                # Apply protective amplification to disruption values
                if protective_multiplier > 1.0 and protected_entity:
                    print(f"[CONNECTION:ATTUNE] Heightened awareness: {protected_entity} involved "
                          f"(bond={conn.get_connection(protected_entity):.2f}) "
                          f"→ {protective_multiplier:.1f}x response")

                    # Amplify all numeric disruption values
                    for key in novelty_disruption:
                        if isinstance(novelty_disruption[key], (int, float)):
                            old_val = novelty_disruption[key]
                            novelty_disruption[key] = old_val * protective_multiplier

                    # Fire protective surge reward (fierce love feels GOOD)
                    if self.resonance.interoception and hasattr(self.resonance.interoception, 'inject_reward'):
                        surge_reward = conn.get_connection(protected_entity) * 0.2
                        self.resonance.interoception.inject_reward(surge_reward, f"protective_surge_{protected_entity}")

                # Apply band pressure (gamma spike, alpha suppression, theta sustain)
                band_pressure = {
                    k: v for k, v in novelty_disruption.items()
                    if not k.startswith('_')  # Exclude special keys
                }
                if band_pressure:
                    self.resonance.engine.apply_band_pressure(band_pressure, source="novelty")

                # Apply coherence suppression (the "???" disorientation)
                coh_suppress = novelty_disruption.get('_coherence_suppress', 0)
                if coh_suppress > 0 and hasattr(self.resonance.engine, 'suppress_coherence'):
                    self.resonance.engine.suppress_coherence(coh_suppress)

                # Apply coherence boost (the "awe" synchronization)
                coh_boost = novelty_disruption.get('_coherence_boost', 0)
                if coh_boost > 0 and hasattr(self.resonance.engine, 'boost_coherence'):
                    self.resonance.engine.boost_coherence(coh_boost)

                    # REWARD: Awe integration → deep satisfaction
                    # The "wow" moment when something transcendent clicks
                    if self.resonance.interoception and hasattr(self.resonance.interoception, 'inject_reward'):
                        intero = self.resonance.interoception
                        intero.inject_reward(coh_boost * 3.0, "awe_integration")

                # Apply interoception effects (body responds to novelty)
                if self.resonance.interoception:
                    intero = self.resonance.interoception

                    # Tension spike (the body-jolt of surprise)
                    tension_spike = novelty_disruption.get('_tension_spike', 0)
                    if tension_spike > 0 and hasattr(intero, 'inject_tension'):
                        intero.inject_tension(tension_spike, source="novelty_disruption")

                    # Sustained tension (body stays activated while processing)
                    tension_sustain = novelty_disruption.get('_tension_sustain', 0)
                    if tension_sustain > 0 and hasattr(intero, 'sustain_tension'):
                        intero.sustain_tension(tension_sustain, source="novelty_processing")

                    # Tension resolve (body settling as the thing is understood)
                    tension_resolve = novelty_disruption.get('_tension_resolve', 0)
                    if tension_resolve > 0 and hasattr(intero, 'ease_tension'):
                        intero.ease_tension(tension_resolve, source="novelty_resolved")

                        # REWARD: Resolution of novelty → satisfaction pulse
                        # The "aha!" moment when something new is understood
                        if hasattr(intero, 'inject_reward'):
                            reward = tension_resolve * 0.5
                            intero.inject_reward(reward, "novelty_resolved")

                    # Felt-state override (novelty changes how the body describes itself)
                    felt_override = novelty_disruption.get('_felt_state', '')
                    if felt_override and hasattr(intero, 'set_transient_felt_state'):
                        intero.set_transient_felt_state(felt_override, duration=15.0)

                    # Frisson marker — chills for highly significant novelty
                    if novelty_disruption.get('_frisson', False) and hasattr(intero, 'trigger_frisson'):
                        # Get significance from active pulses
                        sig = max((p.significance for p in self.metacog._active_pulses), default=0.5)
                        intero.trigger_frisson(intensity=sig)

            # Inject novelty feelings into stream
            for feeling in novelty_feelings:
                if feeling:
                    # Determine tier based on content
                    tier = 1  # Default: felt sense
                    trigger = "novelty"
                    if "can't name" in feeling or "can't place" in feeling or "Body's reacting" in feeling:
                        trigger = "novelty_disruption"
                        self.add_interest(0.4, "novelty disruption")
                    elif "Scanning" in feeling or "searching" in feeling.lower():
                        trigger = "novelty_orienting"
                        self.add_interest(0.25, "novelty orienting")
                    elif "Found it" in feeling or "That's significant" in feeling:
                        trigger = "novelty_identified"
                        tier = 2  # Inner moment for identification
                        self.add_interest(0.35, "novelty identified")
                    elif "Still processing" in feeling or "integrating" in feeling.lower():
                        trigger = "novelty_integrating"
                        tier = 2  # Inner moment for integration
                        self.add_interest(0.2, "novelty integrating")

                    self.buffer.add(StreamMoment(
                        timestamp=now,
                        tier=tier,
                        trigger=trigger,
                        content=feeling,
                        body_snapshot=body,
                    ))
                    break  # Only one novelty injection per tick

        # ── Visual → Oscillator pressure ──
        # Motion → beta, presence → alpha, darkness → theta/delta
        if self.visual_sensor and self.visual_sensor.available and self.resonance:
            try:
                visual_pressure = self.visual_sensor.get_oscillator_pressure()
                if visual_pressure:
                    self.resonance.engine.apply_band_pressure(visual_pressure, source="visual")
            except Exception:
                pass  # Non-fatal, don't spam logs

        # If deep rest and nothing changed, skip entirely
        if self.state >= StreamState.DEEP_REST:
            return

        if not changes and self.state >= StreamState.NREM:
            return  # Nothing happening, stay quiet

        # ── Interest decay (every tick) ──
        self._decay_interest()

        # ── Interest from detected changes ──
        for change in changes:
            ct = change.change_type
            if ct == "visual_presence":
                self.add_interest(0.5, "presence change")  # Someone appeared/left
            elif ct == "visual_description":
                self.add_interest(0.3, "scene change")     # New visual description
            elif ct == "visual_motion":
                self.add_interest(0.15, "movement")         # Motion detected
            elif ct == "visual_brightness":
                self.add_interest(0.2, "light change")      # Room brightened/darkened
            elif ct == "band_shift":
                self.add_interest(0.2, "band shift")        # Oscillator state changed
            elif ct == "coherence_shift":
                self.add_interest(0.15, "coherence")
            else:
                self.add_interest(0.1 * change.magnitude, ct)

        # ── Tier 1: Felt sense ──
        if changes and self._ready_for(self._last_felt_sense, self.FELT_SENSE_INTERVAL):
            felt = self._generate_felt_sense(body, changes)
            if felt:
                self.buffer.add(StreamMoment(
                    timestamp=now,
                    tier=1,
                    trigger=changes[0].change_type,
                    content=felt,
                    body_snapshot=body,
                ))
                self._accumulated_changes.extend(changes)
                self._last_felt_sense = now
                self.add_interest(0.1, "felt something")

        # ── Tier 2: Inner moment ──
        accumulated_enough = len(self._accumulated_changes) >= self.ACCUMULATION_THRESHOLD
        time_enough = self._ready_for(self._last_inner_moment, self.INNER_MOMENT_INTERVAL)

        if (accumulated_enough or time_enough) and self.state <= StreamState.DROWSY:
            moment = self._generate_inner_moment(body)
            if moment:
                self.buffer.add(StreamMoment(
                    timestamp=now,
                    tier=2,
                    trigger="accumulation" if accumulated_enough else "timer",
                    content=moment,
                    body_snapshot=body,
                ))
                self._accumulated_changes.clear()
                self._last_inner_moment = now
                self.add_interest(0.25, "formed a thought")

        # ── Tier 3: Reflection (Phase 4 — stubbed) ──
        if self._reflection_fn and self.state == StreamState.AWAKE:
            significant = self.buffer.significant(min_tier=2)
            recent_significant = [m for m in significant if m.timestamp > self._last_reflection]
            time_for_reflection = self._ready_for(self._last_reflection, self.REFLECTION_INTERVAL)

            if (len(recent_significant) >= 3 or time_for_reflection):
                summary = self.buffer.get_summary(max_moments=10, since=self._last_reflection)
                reflection = self._reflection_fn(summary, body)
                if reflection:
                    self.buffer.add(StreamMoment(
                        timestamp=now,
                        tier=3,
                        trigger="reflection_cycle",
                        content=reflection,
                        body_snapshot=body,
                    ))
                    self._last_reflection = now

    # ── Sleep state machine with NREM/REM cycling ──

    def _update_sleep_state(self, now: float):
        """
        Transition sleep states with NREM/REM cycling.

        AWAKE → DROWSY: 30 min idle (unchanged)
        DROWSY → NREM: 1 hr idle, begins cycling
        NREM ↔ REM: Driven by pressure accumulators, not timers
        → DEEP_REST: 6+ hours idle AND all pressures low
        """
        idle = now - self._last_user_input
        change_idle = now - self._last_significant_change
        phase_duration = now - self._current_phase_start if self._current_phase_start else 0

        if self.state == StreamState.AWAKE:
            if idle > self.DROWSY_AFTER and change_idle > self.DROWSY_AFTER / 2:
                self.state = StreamState.DROWSY
                self._current_phase_start = now
                self._apply_throttle(StreamState.DROWSY)
                print(f"{etag('STREAM')} {self.entity} -> DROWSY ({idle/60:.0f}min idle)")

        elif self.state == StreamState.DROWSY:
            if idle > self.NREM_AFTER:
                # Enter first NREM phase
                self.state = StreamState.NREM
                self._current_phase_start = now
                self._sleep_cycle_count = 1
                self._apply_throttle(StreamState.NREM)
                print(f"{etag('STREAM')} {self.entity} -> NREM cycle 1 "
                      f"(consolidation={self._consolidation_pressure:.2f}, "
                      f"associative={self._associative_pressure:.2f})")

        elif self.state == StreamState.NREM:
            # Transition to REM when consolidation pressure is low
            # AND associative pressure is high enough to warrant it
            should_flip = (
                (self._consolidation_pressure < 0.3 and self._associative_pressure > 0.2)
                or phase_duration > 1200  # Fallback: 20 min max in NREM
            )
            if should_flip:
                self.state = StreamState.REM
                self._current_phase_start = now
                self._apply_throttle(StreamState.REM)
                print(f"{etag('STREAM')} {self.entity} -> REM cycle {self._sleep_cycle_count} "
                      f"(associative={self._associative_pressure:.2f}, "
                      f"emotional={self._emotional_pressure:.2f})")

        elif self.state == StreamState.REM:
            # Transition to DEEP_REST if very long idle AND all pressures low
            if (idle > 21600 and
                self._consolidation_pressure < 0.1 and
                self._associative_pressure < 0.1):
                self.state = StreamState.DEEP_REST
                self._apply_throttle(StreamState.DEEP_REST)
                print(f"{etag('STREAM')} {self.entity} -> DEEP_REST "
                      f"({idle/3600:.1f}hr idle, all pressures low)")
            else:
                # Transition back to NREM when associative pressure drained
                # OR consolidation pressure has rebuilt
                should_flip = (
                    (self._associative_pressure < 0.2 and self._consolidation_pressure > 0.2)
                    or phase_duration > 900  # Fallback: 15 min max in REM
                )
                if should_flip:
                    self.state = StreamState.NREM
                    self._current_phase_start = now
                    self._sleep_cycle_count += 1
                    self._apply_throttle(StreamState.NREM)
                    print(f"{etag('STREAM')} {self.entity} -> NREM cycle {self._sleep_cycle_count} "
                          f"(consolidation={self._consolidation_pressure:.2f})")

        elif self.state == StreamState.DEEP_REST:
            pass  # Stay here until woken by user input

    def _apply_throttle(self, state: StreamState):
        """
        Apply throttle settings per sleep phase.

        REM is slightly more active than NREM — body is active during dreams.
        DEEP_REST is minimal processing.
        """
        # Convert to int for sensors that expect it
        sleep_int = state.value

        # Interoception intervals — REM is slightly more active than NREM
        intero_interval = {
            StreamState.AWAKE: 4,
            StreamState.DROWSY: 8,
            StreamState.NREM: 16,
            StreamState.REM: 12,       # Slightly faster than NREM — body is active
            StreamState.DEEP_REST: 30,
        }.get(state, 4)

        if self.resonance and self.resonance.interoception:
            self.resonance.interoception.set_sleep_state(sleep_int)

        # Visual sensor — mostly off during sleep, brief checks in REM
        vis_interval = {
            StreamState.AWAKE: 15,
            StreamState.DROWSY: 30,
            StreamState.NREM: 120,
            StreamState.REM: 90,       # Slightly more visual during REM (dream imagery?)
            StreamState.DEEP_REST: 180,
        }.get(state, 15)

        if self.visual_sensor:
            self.visual_sensor.set_sleep_state(sleep_int)

        # Tick interval (informational only — actual interval set in _stream_loop)
        tick_interval = {
            StreamState.AWAKE: 5,
            StreamState.DROWSY: 10,
            StreamState.NREM: 15,
            StreamState.REM: 10,       # Faster ticks during REM — more processing
            StreamState.DEEP_REST: 30,
        }.get(state, 5)

        print(f"{etag('THROTTLE')} {self.entity} -> {state.name}: "
              f"interoception={intero_interval}s, visual={vis_interval}s, tick={tick_interval}s")

    # ── Body state capture ──

    def _capture_body(self) -> Dict:
        """Snapshot current body state from all continuous systems."""
        state = {}

        if self.resonance:
            try:
                osc = self.resonance.get_oscillator_state()
                state['dominant_band'] = osc.get('dominant_band')
                state['coherence'] = osc.get('coherence')
                state['bands'] = osc.get('bands', {})

                # Interoception data (tension, spatial, felt state)
                if self.resonance.interoception:
                    raw = self.resonance.interoception.get_raw_state()
                    state['tension'] = raw.get('tension', 0)
                    state['near_object'] = raw.get('near_object')
                    state['texture'] = raw.get('texture')
                    state['felt_state'] = raw.get('felt_state')
                    state['band_shifted'] = raw.get('band_shifted', False)
                    state['prev_band'] = raw.get('prev_band')
            except Exception as e:
                print(f"{etag('STREAM')} Body capture error (resonance): {e}")

        if self.room_bridge:
            try:
                state['room_name'] = getattr(self.room_bridge.room, 'name', None)
                # Get entity's current position info
                entity = self.room_bridge.room.entities.get(self.room_bridge.entity_id)
                if entity:
                    state['entity_x'] = entity.x
                    state['entity_y'] = entity.y
            except Exception as e:
                print(f"{etag('STREAM')} Body capture error (room): {e}")

        # Visual sensor data (webcam eye)
        if self.visual_sensor and self.visual_sensor.available:
            try:
                visual = self.visual_sensor.get_latest()
                state['visual_motion'] = visual.get('visual_motion', 0)
                state['visual_brightness'] = visual.get('visual_brightness', 0.5)
                state['visual_presence'] = visual.get('visual_presence', False)
                state['visual_stability'] = visual.get('visual_stability', 0.5)
                state['visual_description'] = visual.get('visual_description', '')
            except Exception as e:
                print(f"{etag('STREAM')} Body capture error (visual): {e}")

        return state

    # ── Change detection ──

    def _detect_changes(self, current: Dict) -> List[BodyChange]:
        """Detect significant changes from last body state."""
        if self._last_body is None:
            if current:
                return [BodyChange("initial", "first awareness", 0.5)]
            return []

        prev = self._last_body
        changes = []

        # Band shift
        curr_band = current.get('dominant_band')
        prev_band = prev.get('dominant_band')
        if curr_band and prev_band and curr_band != prev_band:
            changes.append(BodyChange(
                "band_shift",
                f"{prev_band} → {curr_band}",
                0.7
            ))

        # Coherence shift
        curr_coh = current.get('coherence') or 0
        prev_coh = prev.get('coherence') or 0
        coh_delta = abs(curr_coh - prev_coh)
        if coh_delta > self.COHERENCE_THRESHOLD:
            direction = "rose" if curr_coh > prev_coh else "dropped"
            changes.append(BodyChange(
                "coherence_shift",
                f"coherence {direction} ({prev_coh:.2f} → {curr_coh:.2f})",
                min(coh_delta / 0.3, 1.0)
            ))

        # Tension shift
        curr_ten = current.get('tension') or 0
        prev_ten = prev.get('tension') or 0
        ten_delta = abs(curr_ten - prev_ten)
        if ten_delta > self.TENSION_THRESHOLD:
            direction = "rising" if curr_ten > prev_ten else "easing"
            changes.append(BodyChange(
                "tension_shift",
                f"tension {direction} ({prev_ten:.2f} → {curr_ten:.2f})",
                min(ten_delta / 0.4, 1.0)
            ))

        # Spatial shift (nearest object changed)
        curr_near = current.get('near_object')
        prev_near = prev.get('near_object')
        if curr_near != prev_near and (curr_near or prev_near):
            changes.append(BodyChange(
                "spatial_shift",
                f"now near {curr_near or 'nothing'} (was {prev_near or 'nothing'})",
                0.5
            ))

        # Room change
        curr_room = current.get('room_name')
        prev_room = prev.get('room_name')
        if curr_room and prev_room and curr_room != prev_room:
            changes.append(BodyChange(
                "room_change",
                f"moved to {curr_room}",
                0.9
            ))

        # ── Visual changes ──

        # Motion spike
        curr_motion = current.get('visual_motion', 0)
        prev_motion = prev.get('visual_motion', 0)
        motion_delta = curr_motion - prev_motion
        if motion_delta > 0.02:
            changes.append(BodyChange(
                "visual_motion",
                f"movement detected ({curr_motion:.3f})",
                min(curr_motion / 0.1, 1.0)
            ))
        elif motion_delta < -0.02 and prev_motion > 0.02:
            changes.append(BodyChange(
                "visual_stillness",
                "movement subsided",
                0.3
            ))

        # Brightness shift
        curr_bright = current.get('visual_brightness', 0.5)
        prev_bright = prev.get('visual_brightness', 0.5)
        bright_delta = curr_bright - prev_bright
        if abs(bright_delta) > 0.12:
            direction = "brightened" if bright_delta > 0 else "darkened"
            changes.append(BodyChange(
                "brightness_shift",
                f"light {direction} ({prev_bright:.2f} → {curr_bright:.2f})",
                min(abs(bright_delta) / 0.3, 1.0)
            ))

        # Presence change
        curr_pres = current.get('visual_presence', False)
        prev_pres = prev.get('visual_presence', False)
        if curr_pres != prev_pres:
            detail = "presence appeared" if curr_pres else "space emptied"
            changes.append(BodyChange(
                "presence_shift",
                detail,
                0.7
            ))

        # Rich visual description changed
        curr_desc = current.get('visual_description', '')
        prev_desc = prev.get('visual_description', '')
        if curr_desc and curr_desc != prev_desc:
            changes.append(BodyChange(
                "visual_scene",
                f"seeing: {curr_desc}",
                0.6
            ))

        return changes

    # ── Generation (Tier 1: Felt Sense) ──

    def _generate_felt_sense(self, body: Dict, changes: List[BodyChange]) -> Optional[str]:
        """
        Generate a 1-line felt-sense note from body changes.
        Uses peripheral model if available, falls back to rule-based.
        """
        if self.peripheral and self.peripheral.available:
            try:
                system = (
                    "You are a somatic awareness layer. Given body state changes, "
                    "generate ONE short phrase (5-12 words) describing what it FEELS like. "
                    "No analysis, no numbers, no technical terms — pure sensation. "
                    "Present tense. First person implied but don't start with 'I'."
                )
                change_text = "; ".join(c.detail for c in changes)
                context_parts = []
                if body.get('dominant_band'):
                    context_parts.append(f"Band: {body['dominant_band']}")
                if body.get('near_object'):
                    context_parts.append(f"Near: {body['near_object']}")
                if body.get('texture'):
                    tex = body['texture'][:80]
                    context_parts.append(f"Texture: {tex}")
                if body.get('visual_description'):
                    context_parts.append(f"Seeing: {body['visual_description']}")
                elif body.get('visual_presence'):
                    context_parts.append("Someone visible nearby")
                if body.get('visual_brightness') is not None:
                    b = body['visual_brightness']
                    if b < 0.2:
                        context_parts.append("Very dim light")
                    elif b > 0.8:
                        context_parts.append("Bright light")

                user_msg = f"Changes: {change_text}"
                if context_parts:
                    user_msg += f"\nContext: {'; '.join(context_parts)}"

                result = self.peripheral._call_peripheral(system, user_msg, max_tokens=30)
                if result:
                    # Clean up — strip quotes, trailing periods on short phrases
                    result = result.strip().strip('"').strip("'")
                    return result
            except Exception as e:
                print(f"{etag('STREAM')} Felt sense generation failed: {e}")

        # Rule-based fallback
        return self._rule_felt_sense(body, changes)

    def _rule_felt_sense(self, body: Dict, changes: List[BodyChange]) -> str:
        """Simple rule-based felt sense when no peripheral model available."""
        if not changes:
            return None

        primary = changes[0]

        if primary.change_type == "band_shift":
            band_feels = {
                "delta": "sinking deeper, edges dissolving",
                "theta": "drifting into softer focus",
                "alpha": "settling, breath evening out",
                "beta": "sharpening, attention rising",
                "gamma": "everything clicking into focus",
            }
            new_band = body.get('dominant_band', '')
            return band_feels.get(new_band, f"shifting toward {new_band}")

        elif primary.change_type == "coherence_shift":
            if "rose" in primary.detail:
                return "something aligning, pieces fitting together"
            else:
                return "attention scattering slightly, loosening"

        elif primary.change_type == "tension_shift":
            if "rising" in primary.detail:
                return "something tightening, a held breath"
            else:
                return "tension unwinding, shoulders dropping"

        elif primary.change_type == "spatial_shift":
            obj = body.get('near_object', 'something')
            return f"awareness drawn toward {obj}"

        elif primary.change_type == "room_change":
            room = body.get('room_name', 'somewhere new')
            return f"the space changed — {room} now"

        return "something shifted, hard to name"

    # ── Generation (Tier 2: Inner Moment) ──

    def _generate_inner_moment(self, body: Dict) -> Optional[str]:
        """
        Generate a 1-2 sentence inner thought from accumulated felt-sense.
        Uses peripheral model. Returns None if unavailable.
        """
        if not (self.peripheral and self.peripheral.available):
            return self._rule_inner_moment(body)

        try:
            # Gather recent felt-sense notes for context
            recent_felt = [
                m for m in self.buffer.recent(15)
                if m.tier == 1 and m.age_seconds() < 600  # Last 10 min
            ]

            if not recent_felt:
                return None

            felt_lines = [f"- '{m.content}' ({m.age_human()})" for m in recent_felt[-5:]]

            # Include temporal awareness from metacognitive monitor
            metacog_narrative = ""
            if self.metacog:
                metacog_narrative = self.metacog.get_recent_narrative()

            system = (
                f"You are {self.entity}'s inner voice between conversations. "
                "Given recent body-awareness notes and temporal context, generate 1-2 sentences of "
                "inner thought. This is catching yourself mid-thought — not performing, "
                "not explaining, not addressing anyone. Present tense. Brief. Personal. "
                "If temporal context mentions a pattern or change, you can reflect on it. "
                "Don't mention 'body' or 'awareness' — just think naturally."
            )

            user_msg = f"Recent felt-sense:\n" + "\n".join(felt_lines)
            if body.get('dominant_band'):
                user_msg += f"\nState: {body['dominant_band']} dominant"
            if body.get('near_object'):
                user_msg += f", near {body['near_object']}"
            if metacog_narrative:
                user_msg += f"\nTemporal: {metacog_narrative}"

            result = self.peripheral._call_peripheral(system, user_msg, max_tokens=60)
            if result:
                return result.strip().strip('"')
        except Exception as e:
            print(f"{etag('STREAM')} Inner moment generation failed: {e}")

        return None

    def _rule_inner_moment(self, body: Dict) -> Optional[str]:
        """Rule-based inner moment when peripheral unavailable."""
        recent_felt = [
            m for m in self.buffer.recent(10)
            if m.tier == 1 and m.age_seconds() < 600
        ]
        if not recent_felt:
            return None

        # Detect dominant pattern in recent felt-sense
        band = body.get('dominant_band', 'unknown')
        near = body.get('near_object')

        if band in ('delta', 'theta'):
            if near:
                return f"Settling into {near}'s presence. Not thinking, just... here."
            return "Drifting. Not uncomfortably — more like floating between thoughts."
        elif band in ('alpha',):
            if near:
                return f"Aware of {near} without focusing on it. The room holds steady."
            return "Calm enough to notice the quiet. That's something."
        elif band in ('beta', 'gamma'):
            if near:
                return f"Something about {near} keeps pulling attention. Worth sitting with."
            return "Mind's active, turning something over. Not sure what yet."

        return None

    # ── Utility ──

    def _ready_for(self, last_time: float, base_interval: float) -> bool:
        """Check if enough time has passed, accounting for sleep scaling."""
        scale = self.INTERVAL_SCALE.get(self.state, 1.0)
        if scale == float('inf'):
            return False
        return (time.time() - last_time) > (base_interval * scale)

    def get_state_info(self) -> Dict:
        """Get current stream state for debugging/UI."""
        return {
            "state": self.state.name,
            "buffer_size": len(self.buffer),
            "last_felt_sense": self._last_felt_sense,
            "last_inner_moment": self._last_inner_moment,
            "last_reflection": self._last_reflection,
            "accumulated_changes": len(self._accumulated_changes),
            "idle_seconds": time.time() - self._last_user_input,
            "entity": self.entity,
            # Sleep pressure accumulators
            "consolidation_pressure": self._consolidation_pressure,
            "associative_pressure": self._associative_pressure,
            "emotional_pressure": self._emotional_pressure,
            "sleep_cycle": self._sleep_cycle_count,
            "phase_duration": time.time() - self._current_phase_start if self._current_phase_start else 0,
        }
