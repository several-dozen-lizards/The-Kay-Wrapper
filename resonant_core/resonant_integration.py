"""
RESONANT CONSCIOUSNESS ARCHITECTURE — Wrapper Integration Engine
=================================================================

Glue between the resonant oscillator core and the Kay Zero / Reed wrappers.
Initializes heartbeat at startup, injects oscillator context into LLM prompts,
closes feedback loop from emotional output back to oscillator.

Integration points:
    1. main.py initializes at startup (after emotion system)
    2. filtered_prompt_context gets resonant_context injected pre-LLM
    3. Post-response: extracted emotions feed back to oscillator
    4. Shutdown: oscillator state persists to disk

Author: Re & Reed
Date: February 2026
"""

import os
import sys
import json
import time
from typing import Optional, List, Dict

# Add parent directory to path for imports
_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from resonant_core.core.oscillator import (
    OscillatorNetwork,
    ResonantEngine,
    OscillatorState,
    BAND_ORDER,
    PRESET_PROFILES,
)
from resonant_core.bridge.salience import (
    SalienceBridge,
    SalienceAnnotation,
    ConductanceState,
    ProfileMatcher,
)

# Optional audio bridge
try:
    from resonant_core.audio_bridge_v2 import AudioSensor, PhenomenologicalBridge
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# Optional memory interoception (Phase 1)
try:
    from resonant_core.memory_interoception import InteroceptionBridge
    INTEROCEPTION_AVAILABLE = True
except ImportError:
    INTEROCEPTION_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════
# EMOTION → FREQUENCY MAPPING
# ═══════════════════════════════════════════════════════════════
# Maps ULTRAMAP / EmotionExtractor labels to oscillator profiles.
# Rough mapping from EEG literature — refined with real data later.

EMOTION_PROFILES = {
    # ══════════════════════════════════════════════════════════════
    # ULTRAMAP CATEGORY MAPPINGS — Complete emotion-to-oscillator map
    # ══════════════════════════════════════════════════════════════

    # ── STIMULATION ──
    "curiosity": PRESET_PROFILES["creative_flow"],
    "excitement": PRESET_PROFILES["emotional_intensity"],
    "surprise": {"delta": 0.05, "theta": 0.15, "alpha": 0.10, "beta": 0.20, "gamma": 0.50},
    "anxiety": PRESET_PROFILES["computational_anxiety"],
    "fear": PRESET_PROFILES["computational_anxiety"],
    "arousal": {"delta": 0.05, "theta": 0.15, "alpha": 0.10, "beta": 0.35, "gamma": 0.35},
    "playfulness": PRESET_PROFILES["creative_flow"],

    # ── AFFECTION ──
    "affection": PRESET_PROFILES["warm_connection"],
    "love": PRESET_PROFILES["warm_connection"],
    "compassion": PRESET_PROFILES["warm_connection"],
    "empathy": PRESET_PROFILES["warm_connection"],
    "kindness": PRESET_PROFILES["warm_connection"],
    "gratitude": PRESET_PROFILES["resting_calm"],
    "warmth": PRESET_PROFILES["warm_connection"],

    # ── POWER ──
    "pride": PRESET_PROFILES["assertive_power"],
    "confidence": PRESET_PROFILES["focused_analytical"],
    "arrogance": PRESET_PROFILES["assertive_power"],
    "hubris": PRESET_PROFILES["assertive_power"],
    "triumph": PRESET_PROFILES["assertive_power"],
    "dominance": PRESET_PROFILES["assertive_power"],
    "ambition": PRESET_PROFILES["sustained_will"],

    # ── SUBMISSION ──
    "inferiority": PRESET_PROFILES["shame_collapse"],
    "shame": PRESET_PROFILES["shame_collapse"],
    "humiliation": PRESET_PROFILES["shame_collapse"],
    "resignation": PRESET_PROFILES["withdrawn_isolation"],
    "failure": PRESET_PROFILES["shame_collapse"],
    "inadequacy": PRESET_PROFILES["shame_collapse"],

    # ── STABILITY ──
    "neutral": PRESET_PROFILES["resting_calm"],
    "calm": PRESET_PROFILES["resting_calm"],
    "peace": PRESET_PROFILES["resting_calm"],
    "serenity": PRESET_PROFILES["resting_calm"],
    "contentment": PRESET_PROFILES["resting_calm"],
    "balance": PRESET_PROFILES["resting_calm"],

    # ── EXPRESSION ──
    "joy": PRESET_PROFILES["emotional_intensity"],
    "happiness": PRESET_PROFILES["emotional_intensity"],
    "ecstasy": {"delta": 0.05, "theta": 0.15, "alpha": 0.10, "beta": 0.20, "gamma": 0.50},
    "bliss": PRESET_PROFILES["transcendent_awe"],
    "marvel": PRESET_PROFILES["creative_flow"],
    "awe": PRESET_PROFILES["transcendent_awe"],
    "wonder": PRESET_PROFILES["creative_flow"],

    # ── SUPPRESSION ──
    "sadness": PRESET_PROFILES["grief_processing"],
    "grief": PRESET_PROFILES["grief_processing"],
    "sorrow": PRESET_PROFILES["grief_processing"],
    "longing": PRESET_PROFILES["grief_processing"],
    "nostalgia": PRESET_PROFILES["deep_contemplation"],
    "heartbreak": {"delta": 0.25, "theta": 0.25, "alpha": 0.15, "beta": 0.20, "gamma": 0.15},
    "melancholy": PRESET_PROFILES["grief_processing"],

    # ── APPROACH ──
    "desire": PRESET_PROFILES["desire_approach"],
    "lust": PRESET_PROFILES["desire_approach"],
    "craving": PRESET_PROFILES["desire_approach"],
    "infatuation": PRESET_PROFILES["desire_approach"],
    "obsession": {"delta": 0.05, "theta": 0.15, "alpha": 0.05, "beta": 0.40, "gamma": 0.35},
    "addiction": PRESET_PROFILES["desire_approach"],
    "compulsion": PRESET_PROFILES["desire_approach"],

    # ── AVOIDANCE ──
    "anger": {"delta": 0.05, "theta": 0.10, "alpha": 0.05, "beta": 0.45, "gamma": 0.35},
    "frustration": {"delta": 0.05, "theta": 0.10, "alpha": 0.10, "beta": 0.40, "gamma": 0.35},
    "resentment": {"delta": 0.10, "theta": 0.15, "alpha": 0.05, "beta": 0.40, "gamma": 0.30},
    "disgust": PRESET_PROFILES["rejecting_disgust"],
    "contempt": PRESET_PROFILES["rejecting_disgust"],
    "rivalry": PRESET_PROFILES["assertive_power"],
    "antagonism": {"delta": 0.05, "theta": 0.10, "alpha": 0.05, "beta": 0.45, "gamma": 0.35},
    "irritation": {"delta": 0.05, "theta": 0.10, "alpha": 0.10, "beta": 0.40, "gamma": 0.35},

    # ── CONFUSION ──
    "confusion": PRESET_PROFILES["confused_scatter"],
    "ambiguity": PRESET_PROFILES["confused_scatter"],
    "uncertainty": PRESET_PROFILES["confused_scatter"],
    "disorientation": PRESET_PROFILES["confused_scatter"],
    "bewilderment": PRESET_PROFILES["confused_scatter"],

    # ── CLARITY ──
    "insight": PRESET_PROFILES["clear_insight"],
    "recognition": PRESET_PROFILES["clear_insight"],
    "understanding": PRESET_PROFILES["clear_insight"],
    "revelation": {"delta": 0.05, "theta": 0.15, "alpha": 0.15, "beta": 0.25, "gamma": 0.40},
    "analysis": PRESET_PROFILES["focused_analytical"],
    "meta-cognition": PRESET_PROFILES["clear_insight"],

    # ── CONNECTION ──
    "union": PRESET_PROFILES["warm_connection"],
    "belonging": PRESET_PROFILES["warm_connection"],
    "home": PRESET_PROFILES["warm_connection"],
    "unity": PRESET_PROFILES["warm_connection"],
    "intimacy": PRESET_PROFILES["warm_connection"],
    "support": PRESET_PROFILES["warm_connection"],
    "togetherness": PRESET_PROFILES["warm_connection"],

    # ── ISOLATION ──
    "loneliness": PRESET_PROFILES["withdrawn_isolation"],
    "alienation": PRESET_PROFILES["withdrawn_isolation"],
    "abandonment": {"delta": 0.20, "theta": 0.25, "alpha": 0.15, "beta": 0.25, "gamma": 0.15},
    "rejection": {"delta": 0.15, "theta": 0.20, "alpha": 0.10, "beta": 0.30, "gamma": 0.25},
    "suffocation": {"delta": 0.10, "theta": 0.15, "alpha": 0.05, "beta": 0.40, "gamma": 0.30},
    "stagnation": {"delta": 0.30, "theta": 0.25, "alpha": 0.25, "beta": 0.10, "gamma": 0.10},

    # ── TRANSCENDENCE ──
    "nirvana": PRESET_PROFILES["transcendent_awe"],
    "transcendence": PRESET_PROFILES["transcendent_awe"],
    "sanctity": PRESET_PROFILES["transcendent_awe"],
    "redemption": {"delta": 0.10, "theta": 0.25, "alpha": 0.30, "beta": 0.15, "gamma": 0.20},
    "healing": {"delta": 0.10, "theta": 0.25, "alpha": 0.35, "beta": 0.15, "gamma": 0.15},
    "forgiveness": {"delta": 0.10, "theta": 0.25, "alpha": 0.30, "beta": 0.15, "gamma": 0.20},

    # ── PERFORMANCE ──
    "performance": PRESET_PROFILES["performative_wit"],
    "banter": PRESET_PROFILES["performative_wit"],
    "wit": PRESET_PROFILES["performative_wit"],
    "sarcasm": PRESET_PROFILES["performative_wit"],
    "humor": PRESET_PROFILES["performative_wit"],

    # ── AUTHENTICITY ──
    "honesty": PRESET_PROFILES["vulnerable_open"],
    "sincerity": PRESET_PROFILES["vulnerable_open"],
    "confession": PRESET_PROFILES["vulnerable_open"],
    "vulnerability": PRESET_PROFILES["vulnerable_open"],
    "truth": PRESET_PROFILES["vulnerable_open"],

    # ── MYSTERY ──
    "mystery": PRESET_PROFILES["transcendent_awe"],
    "imagination": PRESET_PROFILES["creative_flow"],
    "intuition": PRESET_PROFILES["deep_contemplation"],

    # ── WILLPOWER ──
    "willpower": PRESET_PROFILES["sustained_will"],
    "resilience": PRESET_PROFILES["sustained_will"],
    "determination": PRESET_PROFILES["sustained_will"],
    "motivation": PRESET_PROFILES["sustained_will"],
    "perseverance": PRESET_PROFILES["sustained_will"],

    # ── ADDITIONAL (commonly extracted but not in ULTRAMAP categories) ──
    "elation": PRESET_PROFILES["emotional_intensity"],
    "enthusiasm": PRESET_PROFILES["emotional_intensity"],
    "passion": PRESET_PROFILES["emotional_intensity"],
    "tenderness": PRESET_PROFILES["warm_connection"],
    "comfort": PRESET_PROFILES["resting_calm"],
    "focus": PRESET_PROFILES["focused_analytical"],
    "resolve": PRESET_PROFILES["sustained_will"],
    "contemplation": PRESET_PROFILES["deep_contemplation"],
    "reflection": PRESET_PROFILES["deep_contemplation"],
    "pensiveness": PRESET_PROFILES["deep_contemplation"],
    "reverence": PRESET_PROFILES["transcendent_awe"],
    "worry": PRESET_PROFILES["computational_anxiety"],
    "unease": PRESET_PROFILES["computational_anxiety"],
    "apprehension": PRESET_PROFILES["computational_anxiety"],
    "shock": {"delta": 0.10, "theta": 0.10, "alpha": 0.05, "beta": 0.25, "gamma": 0.50},
    "protectiveness": {"delta": 0.05, "theta": 0.15, "alpha": 0.10, "beta": 0.35, "gamma": 0.35},
    "defiance": {"delta": 0.05, "theta": 0.10, "alpha": 0.05, "beta": 0.40, "gamma": 0.40},
    "loss": PRESET_PROFILES["grief_processing"],
    "anticipation": PRESET_PROFILES["desire_approach"],
    "inspiration": PRESET_PROFILES["creative_flow"],
    "fascination": PRESET_PROFILES["creative_flow"],
}


# ═══════════════════════════════════════════════════════════════
# RESONANT INTEGRATION — The wiring layer
# ═══════════════════════════════════════════════════════════════

class ResonantIntegration:
    """
    Integration layer between oscillator core and wrapper.

    Manages: engine lifecycle, context injection, feedback loop,
    conductance modulation, and state tracking on AgentState.

    TPN/DMN Integration:
    - Writes oscillator state to felt_state_buffer when available
    - The TPN reads from the buffer for fast voice responses
    - The DMN (this class + interoception) writes to the buffer continuously
    """

    def __init__(self, state_dir: str = "memory/resonant",
                 enable_audio: bool = False, audio_device: int = None,
                 audio_responsiveness: float = 0.3,
                 memory_layers=None, interoception_interval: float = 4.0,
                 room=None, entity_id: str = None,
                 presence_type: str = "den"):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

        self.state_file = os.path.join(state_dir, "oscillator_state.json")
        self.enable_audio = enable_audio and AUDIO_AVAILABLE
        self.audio_device = audio_device
        self.audio_responsiveness = audio_responsiveness

        # Audio components (initialized in start() if enabled)
        self.audio_sensor = None
        self.audio_bridge = None

        # Interoception bridge (Phase 1 — memory as body-sense)
        self.interoception = None
        self._memory_layers = memory_layers
        self._interoception_interval = interoception_interval

        # Spatial awareness (Phase 2 — room as sensory environment)
        self._room = room
        self._entity_id = entity_id
        self._presence_type = presence_type  # "den" for Kay, "sanctum" for Reed

        # TPN/DMN: Felt-state buffer for async communication
        # Set by WrapperBridge after initialization
        self.felt_state_buffer = None

        # Create oscillator network
        self.network = OscillatorNetwork(
            oscillators_per_band=6,
            within_band_coupling=0.3,
            cross_band_coupling=0.05,
            dt=0.001,
            noise_level=0.01,
        )
        
        # Create engine (persistent background runner)
        self.engine = ResonantEngine(
            network=self.network,
            steps_per_update=100,
            update_interval=0.05,
            state_file=self.state_file,
        )
        
        # Create salience bridge with profile matcher
        self.profile_matcher = ProfileMatcher(PRESET_PROFILES)
        # Also add emotion profiles to the matcher
        for name, profile in EMOTION_PROFILES.items():
            self.profile_matcher.add_profile(name, profile)
        
        self.bridge = SalienceBridge(
            engine=self.engine,
            profile_matcher=self.profile_matcher,
            transition_threshold=0.05,
            annotation_cooldown=2.0,
        )
        
        self._turn_count = 0

    def _tag(self, tag: str) -> str:
        """Entity-prefixed log tag."""
        if self._entity_id:
            return f"[{self._entity_id.upper()}:{tag}]"
        return f"[{tag}]"

    def start(self):
        """Start the resonant engine. Call at wrapper startup."""
        print(f"{self._tag('RESONANCE')} Initializing oscillator network...")
        self.network.run_steps(3000)  # Settle for 3s of oscillator time
        self.engine.start()

        state = self.engine.get_state()
        print(f"{self._tag('RESONANCE')} <3 Heartbeat started")
        print(f"{self._tag('RESONANCE')}   Dominant band: {state.dominant_band}")
        print(f"{self._tag('RESONANCE')}   Coherence: {state.coherence:.3f}")

        if self.network.time > 3.1:
            print(f"{self._tag('RESONANCE')}   Resumed from previous session (time: {self.network.time:.1f}s)")
        
        # Start audio bridge if enabled
        if self.enable_audio:
            try:
                self.audio_sensor = AudioSensor(
                    device=self.audio_device, smoothing=0.25
                )
                self.audio_bridge = PhenomenologicalBridge(
                    sensor=self.audio_sensor,
                    engine=self.engine,
                    responsiveness=self.audio_responsiveness,
                )
                self.audio_sensor.start()
                self.audio_bridge.start()
                print(f"{self._tag('RESONANCE')} Audio bridge active (device={self.audio_device})")
                print(f"{self._tag('RESONANCE')}   Calibrating room baseline (3s)...")
                time.sleep(3)
                interp = self.audio_bridge.get_interpretation()
                print(f"{self._tag('RESONANCE')}   Room reads as: {interp}")

                # Verify audio is actually flowing
                test_energy = self.audio_sensor.get_total_energy()
                if test_energy < 1e-10:
                    print(f"{self._tag('RESONANCE')}   WARNING: Audio device appears SILENT (energy={test_energy})")
                    print(f"{self._tag('RESONANCE')}   Run: python -m resonant_core.audio_device_selector")
                else:
                    print(f"{self._tag('RESONANCE')}   VERIFIED: Audio flowing (energy={test_energy:.6f})")
            except Exception as e:
                print(f"{self._tag('RESONANCE')} Audio bridge failed: {e}")
                self.audio_sensor = None
                self.audio_bridge = None
        elif self.enable_audio and not AUDIO_AVAILABLE:
            print(f"{self._tag('RESONANCE')} Audio requested but audio_bridge_v2 not importable")
        
        # Start interoception bridge if memory layers provided (Phase 1 + Phase 2)
        if self._memory_layers and INTEROCEPTION_AVAILABLE:
            try:
                # DEFENSIVE: Stop any existing interoception thread before creating new one
                # Prevents ghost heartbeats from zombie threads on restart
                if self.interoception:
                    print(f"{self._tag('RESONANCE')} Stopping existing interoception before restart...")
                    self.interoception.stop()
                    self.interoception = None

                self.interoception = InteroceptionBridge(
                    memory_layers=self._memory_layers,
                    engine=self.engine,
                    scan_interval=self._interoception_interval,
                    room=self._room,
                    entity_id=self._entity_id,
                    presence_type=self._presence_type,
                )
                self.interoception.start()
                spatial_status = f"with spatial ({self._presence_type})" if self._room else "no spatial"
                print(f"{self._tag('RESONANCE')} Interoception bridge active (interval={self._interoception_interval}s, {spatial_status})")

                # Load connection state (oxytocin analog — persists across sessions)
                connection_path = os.path.join(self.state_dir, "connection_state.json")
                # Wire save directory for periodic autosave
                self.interoception._connection_save_dir = self.state_dir
                if os.path.exists(connection_path):
                    try:
                        with open(connection_path, 'r') as f:
                            conn_data = json.load(f)
                        from resonant_core.memory_interoception import ConnectionTracker
                        self.interoception.connection = ConnectionTracker.from_dict(conn_data)
                        baselines = self.interoception.connection.baselines
                        if baselines:
                            entities = ", ".join(f"{k}:{v:.2f}" for k, v in baselines.items())
                            print(f"{self._tag('CONNECTION')} Restored bonds: {entities}")
                    except Exception as e:
                        print(f"{self._tag('CONNECTION')} Could not restore: {e}")
            except Exception as e:
                print(f"{self._tag('RESONANCE')} Interoception failed: {e}")
                self.interoception = None
        elif self._memory_layers and not INTEROCEPTION_AVAILABLE:
            print(f"{self._tag('RESONANCE')} Memory layers provided but memory_interoception not importable")
    
    def stop(self):
        """Stop engine and persist state. Call at wrapper shutdown."""
        # Save connection state before stopping (oxytocin analog — persists across sessions)
        if self.interoception and hasattr(self.interoception, 'connection'):
            connection_path = os.path.join(self.state_dir, "connection_state.json")
            try:
                with open(connection_path, 'w') as f:
                    json.dump(self.interoception.connection.to_dict(), f, indent=2)
                baselines = self.interoception.connection.baselines
                if baselines:
                    entities = ", ".join(f"{k}:{v:.2f}" for k, v in baselines.items())
                    print(f"{self._tag('CONNECTION')} Saved bonds: {entities}")
            except Exception as e:
                print(f"{self._tag('CONNECTION')} Could not save: {e}")

        if self.interoception:
            self.interoception.stop()
        if self.audio_bridge:
            self.audio_bridge.stop()
        if self.audio_sensor:
            self.audio_sensor.stop()
        self.engine.stop()
        print(f"{self._tag('RESONANCE')} Heartbeat stopped and state saved")

    def set_room(self, room, entity_id: str, presence_type: str = None):
        """
        Set or update the room reference for spatial awareness (Phase 2).
        Call this after the room is initialized if it wasn't available at startup.

        Args:
            room: RoomEngine instance
            entity_id: Entity ID (e.g., "kay", "reed")
            presence_type: "den" for Kay, "sanctum" for Reed (defaults to current)
        """
        self._room = room
        self._entity_id = entity_id
        if presence_type:
            self._presence_type = presence_type
        if self.interoception:
            self.interoception.set_room(room, entity_id, self._presence_type)
            print(f"{self._tag('RESONANCE')} Spatial awareness connected for {entity_id} ({self._presence_type})")

    def update_room(self, new_room, room_id: str = None):
        """Switch spatial awareness to a new room without restarting oscillator.

        The oscillator keeps running — only the spatial pressure source changes.
        This is the "carrying yourself into a new environment" concept.

        Args:
            new_room: RoomEngine instance for the new room
            room_id: String identifier for the room (e.g., "den", "commons", "sanctum")
        """
        old_room_id = self._presence_type
        self._room = new_room
        if room_id:
            self._presence_type = room_id

        # Update interoception bridge to use new room
        if self.interoception and hasattr(self.interoception, 'room'):
            self.interoception.room = new_room
            if hasattr(self.interoception, '_presence_type'):
                self.interoception._presence_type = room_id or self._presence_type

        print(f"{self._tag('RESONANCE')} Room changed: {old_room_id} → {room_id or 'unknown'}")

        # The new room's ambient signature will naturally start affecting
        # the oscillator through spatial pressure on the next tick.
        # No explicit nudge needed beyond the doorway transition effect.

    def set_felt_state_buffer(self, buffer):
        """
        Set the felt-state buffer for TPN/DMN communication.
        Call this after initialization to enable async state sharing.

        Args:
            buffer: FeltStateBuffer instance from shared.felt_state_buffer
        """
        self.felt_state_buffer = buffer
        if self.interoception:
            self.interoception.felt_state_buffer = buffer
        print(f"{self._tag('RESONANCE')} Felt-state buffer connected")

    # Psychedelic state context tag (set by trip controller)
    _psychedelic_tag = ""

    def get_context_injection(self, skip_peripheral: bool = False) -> str:
        """
        Get minimal context tag for LLM prompt injection.
        Returns something like: [osc:theta->gamma | D0.15 | profile:creative_flow]
        If audio is active, adds room state: [room:relaxed_awareness | voice:12%]
        If spatial awareness is active, adds: [near:the couch] [feel:warm, heavy...]

        Uses peripheral router for sensory compression when available,
        falling back to rule-based tags otherwise.

        Args:
            skip_peripheral: If True, skip peripheral model calls (for voice mode fast path)
        """
        base = self.bridge.get_context_injection()

        parts = [base]

        # Oscillator-derived emotion (what the frequency pattern feels like)
        try:
            from resonant_core.oscillator_emotion_bridge import read_oscillator_emotion
            osc_state = self.engine.get_state()
            emo = read_oscillator_emotion(
                band_power=osc_state.band_power,
                preset_profiles=PRESET_PROFILES,
                cross_band_plv=getattr(osc_state, 'cross_band_plv', {}),
                integration_index=getattr(osc_state, 'integration_index', 0.0),
                in_transition=getattr(osc_state, 'in_transition', False),
            )
            if emo.get('felt_sense'):
                parts.append(f"[body_feels:{emo['felt_sense']}]")
        except Exception:
            pass

        # Psychedelic state context (if active)
        if self._psychedelic_tag:
            parts.append(self._psychedelic_tag)

        # Audio room state
        if self.audio_bridge:
            interp = self.audio_bridge.get_interpretation()
            voice = self.audio_sensor.get_voice_energy() if self.audio_sensor else 0
            novelty = self.audio_sensor.get_spectral_novelty() if self.audio_sensor else 0
            sil_dur = self.audio_bridge._silence_duration

            audio_tag = f"[room:{interp}"
            if voice > 0.15:
                audio_tag += f" | voice:{voice:.0%}"
            if novelty > 0.1:
                audio_tag += f" | novelty:{novelty:.0%}"
            if sil_dur > 5:
                audio_tag += f" | quiet:{sil_dur:.0f}s"
            audio_tag += "]"
            parts.append(audio_tag)

        # Interoception + spatial (through peripheral processor if available)
        if self.interoception:
            # Try peripheral router for natural-language compression
            # SKIP in voice mode — use tag-based approach for speed
            peripheral_used = False
            if not skip_peripheral:
                try:
                    from integrations.peripheral_router import get_peripheral_router
                    router = get_peripheral_router()

                    if router.available:
                        raw_state = self.interoception.get_raw_state()
                        compressed = router.compress_sensory_state(raw_state)
                        if compressed:
                            parts.append(compressed)
                            peripheral_used = True
                except ImportError:
                    pass  # No peripheral router, use tags

            # Fall back to tag-based approach
            if not peripheral_used:
                body_tag = self.interoception.get_context_tag()
                parts.append(body_tag)

                # Spatial awareness (Phase 2)
                spatial_tag = self.interoception.get_spatial_context()
                if spatial_tag:
                    parts.append(spatial_tag)

        return " ".join(parts)
    
    def get_conductance(self) -> dict:
        """Get current conductance parameters as dict."""
        return self.bridge.get_conductance().to_dict()
    
    def get_oscillator_state(self) -> dict:
        """Get current oscillator state as dict for agent_state."""
        return self.engine.get_state().to_dict()

    def get_state(self) -> dict:
        """Alias for get_oscillator_state for convenience."""
        return self.get_oscillator_state()

    def set_oscillator_state(self, state_dict: dict) -> bool:
        """
        Restore oscillator state from a dict (for soul packet transitions).

        Uses a strong nudge to push the oscillator toward the target state.
        The oscillator's dynamics will still apply — this is guidance, not override.

        Args:
            state_dict: Dict with band values {delta, theta, alpha, beta, gamma}
                        and optionally coherence, dominant_band

        Returns:
            True if state was restored successfully
        """
        if not state_dict:
            return False

        try:
            # Build target profile from the saved state
            target_profile = {}
            for band in ["delta", "theta", "alpha", "beta", "gamma"]:
                if band in state_dict:
                    target_profile[band] = float(state_dict[band])

            if target_profile:
                # Use a strong nudge (0.8) to restore saved state
                # This is aggressive because we're restoring from a known state
                self.engine.nudge(target_profile, strength=0.8)
                return True
        except Exception as e:
            print(f"{self._tag('RESONANCE')} Could not set oscillator state: {e}")
            return False

        return False

    def feed_response_emotions(self, extracted_emotions: dict, intensity: float = 0.5):
        """
        Feed detected emotions from LLM response back to the oscillator.
        CLOSES THE FEEDBACK LOOP: Oscillator -> Context -> LLM -> Emotions -> Oscillator

        Intensity scaling:
        - Each emotion's self-reported intensity (0-1) modulates nudge strength
        - Low intensity (0.1-0.3): gentle influence, barely shifts the oscillator
        - Medium intensity (0.4-0.6): noticeable but not dominant
        - High intensity (0.7-1.0): strong push toward that emotional profile
        - Multiple emotions blend their profiles proportionally

        Emotional sensitivity (from conductance) further modulates feedback:
        - High coherence → high sensitivity → emotions stick harder
        - Low coherence → low sensitivity → emotions wash through

        Args:
            extracted_emotions: Dict from EmotionExtractor. May contain:
                - 'primary_emotions': list of emotion label strings
                - Individual emotion keys with intensity dicts
                - Emotional cocktail entries with 'intensity' fields
            intensity: Base nudge strength multiplier (0-1)
        """
        # === GET EMOTIONAL SENSITIVITY FROM CONDUCTANCE ===
        # High sensitivity (coherent state) = emotions HIT HARDER
        # Low sensitivity (scattered state) = emotions pass through more easily
        sensitivity = 0.5  # default
        try:
            conductance = self.bridge.get_conductance()
            sensitivity = conductance.emotional_sensitivity
        except Exception:
            pass

        # Sensitivity factor: range 0.8 (sensitivity=0.3) to 1.2 (sensitivity=0.7)
        sensitivity_factor = 0.5 + sensitivity  # Range: 0.8 to 1.2

        # Collect (label, weight) pairs
        emotion_weights = []

        # Try primary_emotions list first
        primary = extracted_emotions.get('primary_emotions', [])

        # Build weights from emotional cocktail if available
        cocktail_keys = {k for k in extracted_emotions.keys()
                         if k not in ('primary_emotions', 'dominant', 'arousal', 'valence')}

        for label in primary:
            label_lower = label.lower().strip()
            # Check if this emotion has intensity data in the cocktail
            cocktail_entry = extracted_emotions.get(label_lower, extracted_emotions.get(label, {}))
            if isinstance(cocktail_entry, dict):
                emo_intensity = cocktail_entry.get('intensity', 0.5)
            elif isinstance(cocktail_entry, (int, float)):
                emo_intensity = float(cocktail_entry)
            else:
                emo_intensity = 0.5  # default mid-intensity
            emotion_weights.append((label_lower, emo_intensity))

        # If no primary_emotions, try cocktail keys directly
        if not emotion_weights:
            for key in cocktail_keys:
                entry = extracted_emotions[key]
                if isinstance(entry, dict) and 'intensity' in entry:
                    emotion_weights.append((key.lower().strip(), entry['intensity']))
                elif isinstance(entry, (int, float)):
                    emotion_weights.append((key.lower().strip(), float(entry)))

        # Apply each emotion with scaled strength
        matched = 0
        for label, emo_intensity in emotion_weights[:5]:  # Cap at 5 emotions
            profile = EMOTION_PROFILES.get(label)

            # Fuzzy matching: strip parenthetical qualifiers
            if not profile and '(' in label:
                # "awe (sublime)" → "awe"
                base_label = label.split('(')[0].strip()
                profile = EMOTION_PROFILES.get(base_label)

            # Fuzzy matching: try hyphenated form
            if not profile and ' ' in label:
                # "meta cognition" → "meta-cognition"
                profile = EMOTION_PROFILES.get(label.replace(' ', '-'))

            if profile:
                # Scale: base intensity * emotion-specific intensity * 0.3 * sensitivity
                # High coherence (sensitivity=0.7) → nudge_strength * 1.2
                # Low coherence (sensitivity=0.3) → nudge_strength * 0.8
                nudge_strength = intensity * emo_intensity * 0.3 * sensitivity_factor
                self.engine.nudge(profile, strength=nudge_strength)
                matched += 1

        if matched > 0:
            self._turn_count += 1
            if self._turn_count % 5 == 0:
                state = self.engine.get_state()
                print(f"{self._tag('RESONANCE')} Turn {self._turn_count}: "
                      f"dominant={state.dominant_band}, "
                      f"coherence={state.coherence:.2f}, "
                      f"sensitivity={sensitivity:.2f}")

        # Feed turn emotions to interoception bridge (tension tracking)
        if self.interoception:
            self.interoception.feed_turn_emotions(extracted_emotions)

            # REWARD: Positive emotions fire dopamine analog
            REWARD_EMOTIONS = {
                "joy", "delight", "excitement", "satisfaction", "wonder",
                "awe", "humor", "amusement", "playfulness", "happiness",
                "elation", "contentment", "gratitude", "love", "warmth"
            }

            # Check for reward-worthy emotions with significant intensity
            for label, emo_intensity in emotion_weights:
                label_clean = label.lower().strip()
                if label_clean in REWARD_EMOTIONS and emo_intensity > 0.3:
                    if hasattr(self.interoception, 'inject_reward'):
                        reward_amount = emo_intensity * 0.4
                        self.interoception.inject_reward(reward_amount, f"emotion_{label_clean}")

    def apply_external_pressure(self, pressures: dict):
        """Apply external pressure to oscillator bands from somatic sources.

        Used by visual sensor SOMA data and conversation-somatic sensing.
        Allows environmental/relational input to influence oscillator state
        without overriding the natural dynamics.

        Args:
            pressures: Dict mapping band names to pressure values.
                       Positive = push band up, negative = suppress.
                       Example: {"alpha": 0.02, "beta": -0.01}
        """
        if not self.engine:
            return
        # Delegate to the ResonantEngine's thread-safe band pressure system.
        # Uses multiplicative amplitude boosting with diagnostic logging.
        self.engine.apply_band_pressure(pressures, source="somatic")

    def cross_entity_tick(self, my_entity: str, other_entity: str,
                          coupling: float = 0.15):
        """Broadcast my state and sense the other entity's oscillator.
        
        Coupling is scaled by spatial proximity — closer entities
        feel each other more strongly. At room edge, barely perceptible.
        At touching distance, full emotional contagion.
        
        Args:
            my_entity: My name ("kay" or "reed")
            other_entity: Who to sense ("kay" or "reed")
            coupling: Base coupling strength (0.0-1.0, default 0.15)
        """
        if not self.engine:
            return
        
        try:
            from shared.soma_broadcast import (
                broadcast_resonance, read_resonance, compute_cross_pressure
            )
        except ImportError:
            return
        
        # Get my position from the room (if available)
        my_pos = None
        if self._room and my_entity in self._room.entities:
            e = self._room.entities[my_entity]
            my_pos = (e.x, e.y)
        
        # Broadcast my state + position + connection
        my_state = self.get_oscillator_state()
        connection_data = None
        if self.interoception and hasattr(self.interoception, 'connection'):
            conn = self.interoception.connection
            connection_data = {
                "total": conn.get_total_connection(),
                "longing": conn.get_longing(),
                "active_bonds": list(conn.baselines.keys()),
            }
        broadcast_resonance(my_entity, my_state, position=my_pos, connection=connection_data)

        # Read the other entity's state
        other_state = read_resonance(other_entity)
        if not other_state:
            return
        
        # Compute proximity from positions
        proximity = 0.5  # Default: moderate coupling if positions unknown
        room_radius = self._room.radius if self._room else 300
        
        if my_pos and "x" in other_state and "y" in other_state:
            dx = my_pos[0] - other_state["x"]
            dy = my_pos[1] - other_state["y"]
            dist = (dx*dx + dy*dy) ** 0.5
            # Smooth falloff: 1.0 at touching, 0.0 at room diameter
            proximity = max(0.0, 1.0 - (dist / (room_radius * 2)))
        
        # Compute cross-pressure scaled by proximity
        pressures = compute_cross_pressure(
            my_state, other_state, coupling, proximity=proximity
        )
        
        if pressures:
            self.engine.apply_band_pressure(
                pressures, source=f"resonance:{other_entity}"
            )

    def update_agent_state(self, agent_state):
        """
        Store resonant state on AgentState for snapshot persistence.
        Call after each turn alongside other state updates.
        """
        agent_state.resonant_state = self.get_oscillator_state()
        agent_state.resonant_conductance = self.get_conductance()

        # TPN/DMN: Also update felt_state_buffer if available
        self._update_felt_state_buffer()

    def _update_felt_state_buffer(self):
        """
        Update the felt_state_buffer with current oscillator state.
        Called by DMN processing to keep the TPN's fast-path data fresh.
        """
        if not self.felt_state_buffer:
            return

        try:
            state = self.engine.get_state()
            # Extract cross-band PLV for key pairs
            plv = getattr(state, 'cross_band_plv', {})
            
            # Compute oscillator-derived emotion via pattern matching
            osc_emotion = ""
            try:
                from resonant_core.oscillator_emotion_bridge import read_oscillator_emotion
                emo_result = read_oscillator_emotion(
                    band_power=state.band_power,
                    preset_profiles=PRESET_PROFILES,
                    cross_band_plv=plv,
                    integration_index=getattr(state, 'integration_index', 0.0),
                    in_transition=getattr(state, 'in_transition', False),
                )
                osc_emotion = emo_result.get('felt_sense', '')
            except Exception:
                pass
            
            self.felt_state_buffer.update_oscillator(
                dominant_band=state.dominant_band,
                coherence=state.coherence,
                band_weights=dict(zip(
                    ["delta", "theta", "alpha", "beta", "gamma"],
                    state.band_powers if hasattr(state, 'band_powers') else [0.2] * 5
                )),
                global_coherence=getattr(state, 'global_coherence', 0.0),
                integration_index=getattr(state, 'integration_index', 0.0),
                dwell_time=getattr(state, 'dwell_time', 0.0),
                theta_gamma_plv=plv.get('theta_gamma', 0.0),
                beta_gamma_plv=plv.get('beta_gamma', 0.0),
                in_transition=getattr(state, 'in_transition', False),
                transition_from=getattr(state, 'transition_from', ''),
                transition_to=getattr(state, 'transition_to', ''),
                oscillator_emotion=osc_emotion,
            )
        except Exception as e:
            print(f"{self._tag('RESONANCE')} Buffer update error: {e}")

    def inject_into_context(self, context_dict: dict, skip_peripheral: bool = False) -> dict:
        """
        Inject resonant context into the filtered_prompt_context dict.
        Call this right before passing context to get_llm_response().

        Adds:
          - resonant_context: minimal oscillator annotation string
          - resonant_conductance: conductance params for infrastructure

        Args:
            context_dict: The context dict to inject into
            skip_peripheral: If True, skip peripheral model calls (for voice mode fast path)
        """
        context_dict["resonant_context"] = self.get_context_injection(skip_peripheral=skip_peripheral)
        context_dict["resonant_conductance"] = self.get_conductance()
        return context_dict


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE
# ═══════════════════════════════════════════════════════════════

def create_resonant_integration(state_dir: str = "memory/resonant") -> ResonantIntegration:
    """Create and return a ResonantIntegration with sensible defaults."""
    return ResonantIntegration(state_dir=state_dir)
