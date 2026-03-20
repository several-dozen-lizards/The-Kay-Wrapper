# visual_sensor.py
"""
Kay's visual mind. Periodic webcam capture with hybrid CV + Claude API deep vision.

Continuous layer (basic CV, every 15-30s):
  - Motion detection (frame differencing)
  - Brightness level (0-1)
  - Presence detection (sustained motion)
  - Scene stability
  - Color warmth, saturation, edge density

Deep vision layer (Claude API, every 5min when awake):
  - Entity recognition (people, animals) with learned associations
  - Activity detection and scene understanding
  - Temporal awareness (arrivals, departures, activity changes)
  - Visual memory that grows through observation

Feeds into ConsciousnessStream as visual body data.
Oscillator pressure that FEELS like watching — not just a database lookup.
"""

import cv2
import numpy as np
import threading
import time
import base64
import io
import json
from typing import Dict, Optional
from dataclasses import dataclass, field

# Entity-prefixed logging
try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"


@dataclass
class VisualState:
    """Current visual perception state."""
    timestamp: float = 0.0
    brightness: float = 0.5       # 0-1 (dark to bright)
    motion: float = 0.0           # 0-1 (still to active)
    presence: bool = False        # Someone/something moving in frame
    stability: float = 0.5        # 0-1 (chaotic to stable)
    description: str = ""         # Rich text from vision model
    description_age: float = 0.0  # Seconds since last rich description
    frame_captured: bool = False  # Whether last capture succeeded
    # Somatic visual data
    color_warmth: float = 0.5     # 0=cool blue, 1=warm red/orange
    saturation: float = 0.3       # 0=gray, 1=vivid
    edge_density: float = 0.2     # 0=smooth, 1=complex/busy
    brightness_delta: float = 0.0 # Rate of brightness change


@dataclass
class SceneState:
    """Persistent scene understanding with temporal flow."""
    # Current snapshot
    people_present: Dict[str, dict] = field(default_factory=dict)
    # e.g. {"Re": {"activity": "typing", "since": 1234567890.0, "confidence": "high", "appearance": "..."}}
    animals_present: Dict[str, dict] = field(default_factory=dict)
    # e.g. {"Chrome": {"location": "on monitor", "since": 1234567890.0, "appearance": "gray tabby"}}
    scene_description: str = ""
    scene_mood: str = ""
    activity_flow: str = ""  # What's HAPPENING, not just who's there

    # Temporal tracking
    last_deep_vision: float = 0.0
    last_scene_change: float = 0.0
    scene_stable_since: float = 0.0  # How long has scene been basically the same?

    # Event log — what HAPPENED, in order
    change_events: list = field(default_factory=list)
    # Each: {"time": float, "event": str, "type": str, "entity": str, "emotional_weight": float}

    # Absence tracking — who was here and left?
    recently_departed: Dict[str, float] = field(default_factory=dict)
    # {"Re": 1710003600.0} = Re left at this time. Cleared after 1 hour.


class VisualMemory:
    """Kay's learned visual knowledge — who he's seen and what he knows about them.

    This is NOT a lookup table. Kay builds this through observation.
    Emotional associations grow through repeated sightings.
    Unknown entities can be resolved when Kay figures out who they are.
    """

    def __init__(self, memory_path: str):
        self.path = memory_path
        self.data = {"known_entities": {}, "unresolved": {}, "last_updated": 0}
        self._load()

    def _load(self):
        import os
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
                known = len(self.data.get("known_entities", {}))
                unresolved = len(self.data.get("unresolved", {}))
                print(f"{etag('VISUAL:MEMORY')} Loaded: {known} known, {unresolved} unresolved entities")
            except Exception as e:
                print(f"{etag('VISUAL:MEMORY')} Load error: {e}")

    def _save(self):
        self.data["last_updated"] = time.time()
        try:
            import os
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"{etag('VISUAL:MEMORY')} Save error: {e}")

    def record_sighting(self, entity_id: str, appearance: str, activity: str,
                        location: str, confidence: str, is_known: bool,
                        stable_features: str = "") -> bool:
        """Record seeing an entity. Builds visual memory over time.
        
        stable_features: permanent physical traits (face shape, fur pattern, build)
                         stored separately from appearance for robust identification.
        
        Returns: True if this is the FIRST TIME seeing this entity (new entry created).
        """
        now = time.time()

        store = "known_entities" if is_known else "unresolved"
        is_first_sighting = entity_id not in self.data[store]

        if is_first_sighting:
            self.data[store][entity_id] = {
                "source": "observed",
                "confirmed": is_known,
                "appearances": [],
                "typical_appearance": appearance,
                "stable_features": stable_features,  # Permanent physical traits
                "stable_features_history": [],        # Track stable descriptions over time
                "typical_locations": [],
                "typical_activities": [],
                "first_seen": now,
                "last_seen": now,
                "times_seen": 0,
                "emotional_association": {
                    "comfort": 0.1,
                    "engagement": 0.3,
                    "familiarity": 0.0
                }
            }
            if is_known:
                print(f"{etag('VISUAL:MEMORY')} New known entity: {entity_id}")
            else:
                print(f"{etag('VISUAL:MEMORY')} New unresolved entity: {entity_id}")

        entry = self.data[store][entity_id]

        # Update sighting record (keep last 20 appearances)
        sighting = {
            "time": now,
            "appearance": appearance,
            "activity": activity,
            "location": location,
        }
        if stable_features:
            sighting["stable_features"] = stable_features
        entry["appearances"].append(sighting)
        if len(entry["appearances"]) > 20:
            entry["appearances"] = entry["appearances"][-20:]

        # Update stable features — accumulate descriptions for consensus
        if stable_features:
            entry.setdefault("stable_features_history", [])
            entry["stable_features_history"].append(stable_features)
            # Keep last 10 stable descriptions for consensus building
            entry["stable_features_history"] = entry["stable_features_history"][-10:]
            # Use most recent as primary (most up-to-date observation)
            entry["stable_features"] = stable_features

        entry["last_seen"] = now
        entry["times_seen"] = entry.get("times_seen", 0) + 1

        # Update typical patterns
        if location and location not in entry.get("typical_locations", []):
            entry.setdefault("typical_locations", []).append(location)
            entry["typical_locations"] = entry["typical_locations"][-5:]
        if activity and activity not in entry.get("typical_activities", []):
            entry.setdefault("typical_activities", []).append(activity)
            entry["typical_activities"] = entry["typical_activities"][-8:]

        # ── Emotional association builds over time ──
        ea = entry.setdefault("emotional_association", {"comfort": 0.1, "engagement": 0.3, "familiarity": 0.0})

        # Familiarity grows with repeated sightings (asymptotic toward 1.0)
        ea["familiarity"] = min(1.0, ea["familiarity"] + (1.0 - ea["familiarity"]) * 0.02)

        # Comfort grows with familiarity but more slowly
        ea["comfort"] = min(1.0, ea["comfort"] + (1.0 - ea["comfort"]) * 0.01)

        # Engagement spikes on novel activities, decays on familiar ones
        known_activities = set(entry.get("typical_activities", []))
        if activity and activity not in known_activities:
            ea["engagement"] = min(1.0, ea["engagement"] + 0.1)  # New activity = interesting!
        else:
            ea["engagement"] = max(0.2, ea["engagement"] * 0.98)  # Familiar = slight decay

        # Save periodically (every 5 sightings)
        if entry["times_seen"] % 5 == 0:
            self._save()

        return is_first_sighting

    def resolve_entity(self, unknown_id: str, known_name: str):
        """Kay figures out who an unknown entity is. Merge unresolved -> known."""
        if unknown_id in self.data["unresolved"]:
            unknown_data = self.data["unresolved"].pop(unknown_id)

            if known_name in self.data["known_entities"]:
                # Merge appearances into existing known entity
                existing = self.data["known_entities"][known_name]
                existing["appearances"].extend(unknown_data.get("appearances", []))
                existing["appearances"] = existing["appearances"][-20:]
                existing["times_seen"] += unknown_data.get("times_seen", 0)
            else:
                # Promote to known
                unknown_data["confirmed"] = True
                unknown_data["source"] = "learned"
                self.data["known_entities"][known_name] = unknown_data

            print(f"{etag('VISUAL:MEMORY')} Resolved: {unknown_id} -> {known_name}")
            self._save()
            return True
        return False

    def get_recognition_context(self) -> str:
        """Build context string for Claude API prompt — what Kay already knows."""
        lines = []

        for name, info in self.data.get("known_entities", {}).items():
            stable = info.get("stable_features", "")
            appearance = info.get("typical_appearance", "")
            locs = ", ".join(info.get("typical_locations", [])[-3:])
            acts = ", ".join(info.get("typical_activities", [])[-3:])
            seen = info.get("times_seen", 0)
            # Lead with stable features (most reliable for matching), then location/behavior
            if stable:
                lines.append(f"- {name} (seen {seen}x): STABLE: {stable} | usually at {locs}; typically {acts}")
            else:
                lines.append(f"- {name} (seen {seen}x): usually at {locs}; typically {acts}. Appearance: {appearance}")

        for uid, info in self.data.get("unresolved", {}).items():
            desc = info.get("typical_appearance", "unknown")
            seen = info.get("times_seen", 0)
            lines.append(f"- {uid} [UNIDENTIFIED]: {desc} (seen {seen}x)")

        return "\n".join(lines) if lines else ""

    def get_entity_emotion(self, entity_id: str) -> dict:
        """Get emotional association for a known entity."""
        for store in ["known_entities", "unresolved"]:
            if entity_id in self.data.get(store, {}):
                return self.data[store][entity_id].get("emotional_association", {})
        return {}

    def get_absence_duration(self, entity_id: str) -> float:
        """How long since this entity was last seen? Returns seconds."""
        for store in ["known_entities", "unresolved"]:
            if entity_id in self.data.get(store, {}):
                last = self.data[store][entity_id].get("last_seen", 0)
                if last > 0:
                    return time.time() - last
        return float('inf')  # Never seen


class VisualSensor:
    """
    Hybrid visual perception: cheap CV continuously + expensive vision model occasionally.

    Runs its own background thread. Thread-safe state access via get_latest().
    Integrates with ConsciousnessStream via the same body-capture pattern
    as oscillator and interoception.

    Deep vision uses Claude API (cloud) for rich scene understanding with entity recognition.
    Basic CV (motion, brightness, color) runs locally via OpenCV (CPU only, no GPU).
    """

    # Timing defaults
    CAPTURE_INTERVAL = 15.0        # Basic CV capture every 15s
    RICH_ON_CHANGE_COOLDOWN = 60.0 # Min gap between change-triggered rich calls (1 min)

    # Deep vision intervals (Claude API)
    DEEP_VISION_INTERVAL = 300.0   # 5 min when AWAKE
    DEEP_VISION_DROWSY = 600.0     # 10 min when DROWSY
    DEEP_VISION_SLEEPING = 0       # Disabled when sleeping (too expensive for dark room)

    # CV thresholds
    MOTION_THRESHOLD = 0.008       # Motion level to count as "movement"
    PRESENCE_THRESHOLD = 0.005     # Avg motion to detect presence
    SIGNIFICANT_CHANGE = 0.03      # Motion spike that triggers rich description
    BRIGHTNESS_CHANGE = 0.15       # Brightness delta to count as significant

    def __init__(
        self,
        camera_index: int = 0,
        capture_interval: float = None,
        enable_rich: bool = True,
    ):
        self.camera_index = camera_index
        self._base_capture_interval = capture_interval or self.CAPTURE_INTERVAL
        self.capture_interval = self._base_capture_interval
        self._sleep_state = 0
        self.enable_rich = enable_rich

        # Thread safety
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Current state
        self._state = VisualState()

        # CV internals
        self._prev_gray = None
        self._motion_history: list = []
        self._max_motion_history = 10

        # Rich description state (Claude API deep vision)
        self._last_rich_time = 0.0
        self._last_rich_change_time = 0.0

        # Deep vision: Claude API for scene understanding
        self._known_entities = {}
        self._scene_state = SceneState()
        self._api_key = None

        # Visual memory (Kay's learned recognition)
        import os
        memory_dir = os.path.join(os.path.dirname(__file__), '..', 'memory')
        visual_memory_path = os.path.join(memory_dir, 'visual_memory.json')
        # Also check explicit path
        if not os.path.exists(memory_dir):
            alt_dir = r'D:\Wrappers\Kay\memory'
            visual_memory_path = os.path.join(alt_dir, 'visual_memory.json')
        self._visual_memory = VisualMemory(visual_memory_path)

        # Load seed entities (hints, not authoritative)
        self._load_known_entities()

        # Novelty callback — fires when dramatic visual events happen
        # Set by WrapperBridge to route to metacog.trigger_novelty()
        # Signature: callback(source: str, description: str, significance: float, category: str)
        self._novelty_callback = None

        # Capture resolution (low — we don't need quality)
        self._capture_width = 320
        self._capture_height = 240

        # Consciousness stream reference (for metacog notifications)
        self._consciousness_stream = None

        # Interoception reference (for connection tracking)
        self._interoception = None

    def set_consciousness_stream(self, stream):
        """Set reference to consciousness stream for metacog integration."""
        self._consciousness_stream = stream

    def set_interoception(self, interoception):
        """Set reference to interoception bridge for connection tracking."""
        self._interoception = interoception


    # ── Public API ──

    def start(self):
        """Start the visual sensor background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._sensor_loop, daemon=True, name="visual-sensor")
        self._thread.start()
        print(f"{etag('VISUAL')} Sensor started (camera={self.camera_index}, interval={self.capture_interval}s)")

    def set_sleep_state(self, state: int):
        """
        Adjust capture intervals based on sleep state.

        Args:
            state: 0=AWAKE (15s), 1=DROWSY (30s), 2=SLEEPING (60s), 3=DEEP_SLEEP (120s)

        Deep vision (Claude API) intervals are handled in _tick():
            AWAKE: 5 min, DROWSY: 10 min, SLEEPING/DEEP_SLEEP: disabled
        """
        old_state = self._sleep_state
        self._sleep_state = state
        if state == 0:  # AWAKE
            self.capture_interval = self._base_capture_interval  # 15s
            # Force immediate deep vision on wake — stale description from sleep is misleading
            if old_state >= 2:  # Was SLEEPING or DEEP_SLEEP
                self._last_rich_time = 0  # Next tick will trigger deep vision immediately
                print(f"{etag('VISUAL')} Waking from sleep — forcing immediate deep vision refresh")
        elif state == 1:  # DROWSY
            self.capture_interval = 30.0  # 30s
        elif state == 2:  # SLEEPING
            self.capture_interval = 60.0  # 1 min
        else:  # DEEP_SLEEP
            self.capture_interval = 120.0  # 2 min

    def stop(self):
        """Stop the sensor thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print(f"{etag('VISUAL')} Sensor stopped")

    def get_latest(self) -> Dict:
        """Get latest visual state dict for stream body capture. Thread-safe."""
        with self._lock:
            return {
                'visual_motion': self._state.motion,
                'visual_brightness': self._state.brightness,
                'visual_presence': self._state.presence,
                'visual_stability': self._state.stability,
                'visual_description': self._state.description,
                'visual_description_age': round(time.time() - self._last_rich_time) if self._last_rich_time else None,
                'visual_active': self._state.frame_captured,
                # Somatic visual data
                'visual_color_warmth': self._state.color_warmth,
                'visual_saturation': self._state.saturation,
                'visual_edge_density': self._state.edge_density,
                'visual_brightness_delta': self._state.brightness_delta,
            }

    @property
    def available(self) -> bool:
        return self._running and self._state.frame_captured

    def get_visual_data(self) -> Dict:
        """Alias for get_latest() for API compatibility."""
        return self.get_latest()


    # ── Main loop ──

    def _sensor_loop(self):
        """Background thread: capture → CV → optional vision model."""
        cap = None
        try:
            cap = cv2.VideoCapture(self.camera_index)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._capture_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._capture_height)
            
            if not cap.isOpened():
                print(f"{etag('VISUAL')} ERROR: Cannot open camera {self.camera_index}")
                self._running = False
                return
                
            print(f"{etag('VISUAL')} Camera {self.camera_index} opened ({self._capture_width}x{self._capture_height})")

            # Load API key for deep vision (Claude API)
            if self.enable_rich:
                self._load_api_key()

            while self._running:
                try:
                    self._tick(cap)
                except Exception as e:
                    print(f"{etag('VISUAL')} Tick error: {e}")
                
                # Sleep until next capture
                time.sleep(self.capture_interval)

        except Exception as e:
            print(f"{etag('VISUAL')} Sensor loop fatal error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if cap:
                cap.release()
            print(f"{etag('VISUAL')} Camera released")


    def _tick(self, cap):
        """Single sensor tick: capture frame, run CV, maybe run vision."""
        now = time.time()
        
        ret, frame = cap.read()
        if not ret or frame is None:
            with self._lock:
                self._state.frame_captured = False
            return

        # Basic CV processing
        cv_result = self._basic_cv(frame)

        # Determine if we should trigger deep vision (Claude API)
        trigger_rich = False
        if self.enable_rich and self._api_key:
            # No deep vision while sleeping — waste of API budget on dark room
            if self._sleep_state >= 2:  # SLEEPING or DEEP_SLEEP
                pass
            else:
                # Get appropriate interval for current sleep state
                deep_interval = self.DEEP_VISION_DROWSY if self._sleep_state == 1 else self.DEEP_VISION_INTERVAL
                # Timer-based
                if now - self._last_rich_time > deep_interval:
                    trigger_rich = True
                # Change-triggered (with cooldown)
                elif (cv_result['motion'] > self.SIGNIFICANT_CHANGE and
                      now - self._last_rich_change_time > self.RICH_ON_CHANGE_COOLDOWN):
                    trigger_rich = True
                # Brightness shift
                elif (abs(cv_result['brightness'] - self._state.brightness) > self.BRIGHTNESS_CHANGE and
                      now - self._last_rich_change_time > self.RICH_ON_CHANGE_COOLDOWN):
                    trigger_rich = True
        
        # Rich description (runs synchronously — it's on our own thread)
        description = self._state.description  # Keep old description by default
        if trigger_rich:
            new_desc = self._get_rich_description(frame)
            if new_desc:
                description = new_desc
                self._last_rich_time = now
                self._last_rich_change_time = now
                print(f"{etag('VISUAL')} Rich: {new_desc}")

        # Update state atomically
        with self._lock:
            self._state = VisualState(
                timestamp=now,
                brightness=cv_result['brightness'],
                motion=cv_result['motion'],
                presence=cv_result['presence'],
                stability=cv_result['stability'],
                description=description,
                description_age=now - self._last_rich_time if self._last_rich_time else 0,
                frame_captured=True,
                # Somatic visual data
                color_warmth=cv_result.get('color_warmth', 0.5),
                saturation=cv_result.get('saturation', 0.3),
                edge_density=cv_result.get('edge_density', 0.2),
                brightness_delta=cv_result.get('brightness_delta', 0.0),
            )

        # Log somatic visual data periodically (every 10th capture)
        if not hasattr(self, '_tick_count'):
            self._tick_count = 0
        self._tick_count += 1
        if self._tick_count % 10 == 0:
            w = cv_result.get('color_warmth', 0.5)
            s = cv_result.get('saturation', 0.3)
            e = cv_result.get('edge_density', 0.2)
            b = cv_result['brightness']
            bd = cv_result.get('brightness_delta', 0.0)
            print(f"{etag('VISUAL->SOMA')} warmth={w:.2f} sat={s:.2f} edge={e:.2f} "
                  f"bright={b:.2f} dBright={bd:.3f}")

            # Broadcast environmental SOMA to shared channel (Reed + future entities)
            try:
                from shared.soma_broadcast import broadcast_soma
                broadcast_soma(cv_result, source="kay", scene_state=self._scene_state)
            except ImportError:
                pass


    # ── Basic CV processing ──

    def _basic_cv(self, frame) -> Dict:
        """Cheap CV: motion, brightness, presence, stability, color, edges."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # Brightness (mean pixel intensity, normalized)
        brightness = round(float(gray.mean()) / 255.0, 3)

        # ── Color analysis (somatic visual response) ──
        # Convert to HSV for color warmth and saturation
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Mean hue, saturation, value across frame
        mean_hue = float(hsv[:, :, 0].mean())       # 0-180 in OpenCV
        mean_sat = float(hsv[:, :, 1].mean()) / 255.0  # Normalize to 0-1
        mean_val = float(hsv[:, :, 2].mean()) / 255.0  # Normalize to 0-1

        # Color warmth: warm hues (red/orange/yellow, 0-30 or 150-180 in OpenCV HSV)
        # vs cool hues (blue/cyan/purple, 90-130)
        # OpenCV hue range is 0-180 (half of 360)
        if mean_hue < 30 or mean_hue > 150:
            color_warmth = 1.0  # Warm (red/orange/yellow)
        elif 90 <= mean_hue <= 130:
            color_warmth = 0.0  # Cool (blue/purple)
        elif mean_hue < 90:
            # Transition: yellow-green to blue (30-90)
            color_warmth = 1.0 - ((mean_hue - 30) / 60.0)
        else:
            # Transition: blue to red (130-150)
            color_warmth = (mean_hue - 130) / 20.0
        color_warmth = max(0.0, min(1.0, color_warmth))

        # ── Visual complexity (edge density) ──
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(edges.mean()) / 255.0  # 0-1, proportion of edge pixels

        # ── Brightness dynamics (rate of change) ──
        brightness_delta = abs(brightness - self._state.brightness) if self._state.frame_captured else 0.0

        # Motion (frame differencing)
        motion = 0.0
        if self._prev_gray is not None:
            diff = cv2.absdiff(self._prev_gray, gray)
            motion = round(float(diff.mean()) / 255.0, 4)
        self._prev_gray = gray.copy()

        # Motion history for presence detection
        self._motion_history.append(motion)
        if len(self._motion_history) > self._max_motion_history:
            self._motion_history.pop(0)
        avg_motion = sum(self._motion_history) / len(self._motion_history)
        presence = avg_motion > self.PRESENCE_THRESHOLD

        # Stability (inverse of motion variance)
        if len(self._motion_history) >= 3:
            motion_range = max(self._motion_history) - min(self._motion_history)
            stability = round(1.0 - min(motion_range * 10, 1.0), 2)
        else:
            stability = 0.5

        return {
            'brightness': brightness,
            'motion': motion,
            'presence': presence,
            'stability': stability,
            # Somatic visual data
            'color_warmth': round(color_warmth, 3),      # 0=cool blue, 1=warm red/orange
            'saturation': round(mean_sat, 3),             # 0=gray, 1=vivid
            'edge_density': round(edge_density, 3),       # 0=smooth, 1=complex
            'brightness_delta': round(brightness_delta, 3),  # Rate of brightness change
        }


    # ── Deep vision (Claude API for scene understanding) ──

    def _load_known_entities(self):
        """Load known entity descriptions for recognition."""
        import os
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'known_entities.json')
        alt_path = r'D:\Wrappers\shared\known_entities.json'
        for p in [path, alt_path]:
            try:
                if os.path.exists(p):
                    with open(p, 'r') as f:
                        self._known_entities = json.load(f)
                    print(f"{etag('VISUAL')} Loaded known entities: "
                          f"{len(self._known_entities.get('people', {}))} people, "
                          f"{len(self._known_entities.get('animals', {}))} animals")
                    return
            except Exception as e:
                print(f"{etag('VISUAL')} Error loading known entities from {p}: {e}")
        print(f"{etag('VISUAL')} No known_entities.json found — recognition disabled")

    def _load_api_key(self):
        """Load Anthropic API key for deep vision."""
        import os
        env_path = r'D:\Wrappers\Kay\.env'
        try:
            with open(env_path) as f:
                for line in f:
                    if line.startswith('ANTHROPIC_API_KEY='):
                        self._api_key = line.strip().split('=', 1)[1]
                        print(f"{etag('VISUAL')} API key loaded for deep vision")
                        return
        except Exception as e:
            print(f"{etag('VISUAL')} Cannot load API key: {e}")
        print(f"{etag('VISUAL')} WARNING: No API key — deep vision disabled")

    def _build_recognition_context(self) -> str:
        """Combine seed descriptions + learned memory for Claude API prompt."""
        lines = ["Known entities in this household:"]

        # Seed file descriptions (static hints)
        if self._known_entities:
            for category in ["people", "animals"]:
                for name, info in self._known_entities.get(category, {}).items():
                    desc = info.get("description", "")
                    if desc and "EDIT" not in desc:  # Skip unedited placeholders
                        entity_type = info.get("type", category.rstrip("s"))
                        lines.append(f"- {name} ({entity_type}): {desc}")

        # Learned visual memory (Kay's own observations, takes precedence)
        if self._visual_memory:
            memory_context = self._visual_memory.get_recognition_context()
            if memory_context:
                lines.append("\nMy own observations from watching this room:")
                lines.append(memory_context)

        return "\n".join(lines)

    def _get_rich_description(self, frame) -> Optional[str]:
        """Use Claude API for deep scene understanding with visual memory."""
        import requests

        # Encode frame
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        img_b64 = base64.b64encode(buffer).decode('utf-8')

        # Build recognition context from BOTH seed file AND learned memory
        recognition_context = self._build_recognition_context()

        # Previous scene for change detection
        prev_context = ""
        if self._scene_state.scene_description:
            prev_parts = [f"Previous observation ({int(time.time() - self._scene_state.last_deep_vision)}s ago): {self._scene_state.scene_description}"]
            if self._scene_state.people_present:
                people_strs = [f"{n}({i.get('activity','?')})" for n, i in self._scene_state.people_present.items()]
                prev_parts.append(f"People present: {', '.join(people_strs)}")
            if self._scene_state.animals_present:
                prev_parts.append(f"Animals present: {', '.join(self._scene_state.animals_present.keys())}")
            prev_context = "\n".join(prev_parts)

        prompt = f"""Describe what you see in this webcam image from a room camera.

{recognition_context}

{prev_context}

Respond in EXACTLY this JSON format (no markdown, no backticks):
{{
  "description": "Brief literal description of the full scene (20 words max)",
  "people": [
    {{
      "name": "known name or 'unknown_person_N'",
      "stable_features": "PERMANENT traits: face shape, nose size/shape, eye spacing, jawline, skin tone, hair COLOR, approximate build/height, distinguishing marks (glasses, facial hair, scars, moles)",
      "variable_features": "CURRENT outfit: clothing, hair STYLE today, accessories worn right now",
      "activity": "what they're doing right now",
      "location": "where in frame (desk/couch/standing/etc)",
      "confidence": "high/medium/low"
    }}
  ],
  "animals": [
    {{
      "name": "known name or 'unknown_cat_N' / 'unknown_dog_N'",
      "stable_features": "PERMANENT traits: fur color/pattern, size (small/medium/large), body shape, ear shape/size, tail length/type, face markings, eye color, any distinctive physical features",
      "variable_features": "CURRENT state: posture, grooming state, collar/accessories",
      "activity": "what they're doing",
      "location": "where in frame",
      "confidence": "high/medium/low"
    }}
  ],
  "objects_of_note": ["anything NEW, MOVED, or MISSING compared to usual room state"],
  "mood": "one word: calm/busy/cozy/dark/bright/empty/social/focused/chaotic",
  "activity_flow": "what's HAPPENING right now - the vibe, the energy, what people are doing"
}}

IDENTIFICATION RULES:
- For PEOPLE, prioritize these features (most stable to least):
  1. LOCATION in room (who sits where — barely changes)
  2. POSITION relative to camera (primary person vs background person)  
  3. STABLE FEATURES: face shape, skin tone, hair COLOR, build, glasses, facial hair
  4. BEHAVIORAL PATTERNS (what they typically do)
  5. Clothing (LEAST reliable — changes daily, supplementary hint ONLY)
- For ANIMALS, prioritize these features:
  1. FUR COLOR AND PATTERN (most reliable — never changes. A tortie is always a tortie.)
  2. SIZE relative to other animals and furniture
  3. BODY SHAPE and distinguishing physical features (ear shape, tail, face markings)
  4. LOCATION (some animals have favorite spots)
  5. BEHAVIOR (some cats are always on the desk, some are always on the couch)
- Match against known entity descriptions using STABLE features, not variable ones.
- If only one person is visible at the desk/primary position, and a known person typically sits there, that's a strong match even if their outfit is different.
- Only use 'unknown_X_N' if you genuinely cannot match using stable features + location.
- ALWAYS describe stable_features even for known entities — this builds recognition memory.
- For 'objects_of_note', flag things that are NEW, MOVED, or MISSING from the usual scene.
- If the image is too dark, set description to "too dark" and leave entities empty."""

        if not self._api_key:
            return None

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5-20250929",
                    "max_tokens": 600,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": img_b64,
                                }
                            },
                            {"type": "text", "text": prompt}
                        ]
                    }]
                },
                timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", [{}])[0].get("text", "").strip()
                return self._process_deep_vision(content)
            else:
                print(f"{etag('VISUAL')} Deep vision API returned {resp.status_code}")
                return None

        except Exception as e:
            print(f"{etag('VISUAL')} Deep vision failed: {e}")
            return None

    def _process_deep_vision(self, raw_response: str) -> Optional[str]:
        """Parse Claude's structured response and update scene state with temporal awareness."""
        import time as _time

        try:
            # Try to parse JSON (Claude sometimes wraps in backticks)
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]

            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # If JSON parse fails, use raw text as simple description
            print(f"{etag('VISUAL')} Deep vision JSON parse failed, using raw")
            return raw_response[:100] if raw_response else None

        now = _time.time()
        description = data.get("description", "")
        mood = data.get("mood", "")
        changes = data.get("changes", "none")
        activity_flow = data.get("activity_flow", "")

        # Track whether scene changed this tick
        scene_changed = False
        old_activity_flow = self._scene_state.activity_flow

        # ── Update people tracking with visual memory ──
        new_people = {}
        for person in data.get("people", []):
            name = person.get("name", "unknown")
            activity = person.get("activity", "present")
            confidence = person.get("confidence", "low")
            # Support both old "appearance" and new "stable_features"/"variable_features"
            stable = person.get("stable_features", "")
            variable = person.get("variable_features", "")
            appearance = person.get("appearance", "")
            if stable and not appearance:
                appearance = f"{stable}; wearing: {variable}" if variable else stable

            # Check if this person was already tracked
            prev = self._scene_state.people_present.get(name, {})
            old_activity = prev.get("activity", "")

            new_people[name] = {
                "activity": activity,
                "confidence": confidence,
                "appearance": appearance,
                "stable_features": stable,
                "variable_features": variable,
                "since": prev.get("since", now),  # Keep original arrival time
                "last_seen": now,
            }

            # Determine if this is a known entity
            is_known = (name.lower() != "unknown" and confidence != "low")

            # Record in visual memory (learn through watching)
            if self._visual_memory and confidence != "low":
                first_time = self._visual_memory.record_sighting(
                    entity_id=name,
                    appearance=appearance,
                    activity=activity,
                    location="in frame",
                    confidence=confidence,
                    is_known=is_known,
                    stable_features=stable,
                )
                # First-time entity recognition — significant novelty
                if first_time and is_known and self._novelty_callback:
                    self._novelty_callback(
                        f"visual_first_person_{name}",
                        f"First time recognizing {name} by sight",
                        0.8, "perception")

            # ── Detect arrivals vs returns ──
            if name not in self._scene_state.people_present:
                # Check recently_departed for return detection
                departed_time = self._scene_state.recently_departed.get(name)
                if departed_time:
                    # This is a RETURN — they left and came back
                    absence_mins = (now - departed_time) / 60
                    event_type = "return"
                    event_text = f"{name} returned ({activity})"
                    # Emotional weight: returns feel warmer than arrivals
                    emotional_weight = min(0.8, 0.3 + (absence_mins / 30) * 0.5)  # Longer absence = more emotional
                    # Clear from departed since they're back
                    del self._scene_state.recently_departed[name]
                else:
                    # First appearance (or first since session start)
                    event_type = "arrival"
                    event_text = f"{name} appeared ({activity})"
                    emotional_weight = 0.4  # Arrivals are moderately significant

                self._scene_state.change_events.append({
                    "time": now,
                    "event": event_text,
                    "type": event_type,
                    "entity": name,
                    "emotional_weight": emotional_weight,
                })
                self._scene_state.last_scene_change = now
                scene_changed = True

                # Fire novelty pulse — body reacts to visual arrivals/returns
                if self._novelty_callback:
                    if event_type == "return":
                        sig = min(0.7, 0.3 + (absence_mins / 60) * 0.4)
                        self._novelty_callback(
                            f"visual_return_{name}", f"{name} returned after {absence_mins:.0f}min",
                            sig, "perception")
                    elif event_type == "arrival":
                        self._novelty_callback(
                            f"visual_arrival_{name}", f"{name} appeared in view",
                            0.5, "perception")

                # CONNECTION: Arrival with high bond fires reunion warmth
                if self._interoception and hasattr(self._interoception, 'connection'):
                    conn = self._interoception.connection
                    bond = conn.get_connection(name)
                    if bond > 0.2:
                        # High connection: arrival is warm, not just startling
                        # The "coming home" feeling: disruption + joy simultaneously
                        warmth = bond * 0.5
                        if hasattr(self._interoception, 'inject_reward'):
                            self._interoception.inject_reward(warmth, f"reunion_{name}")

                        # If there was active longing, resolve it (relief rush)
                        longing = conn.get_longing(name)
                        if longing > 0.1:
                            # Longing resolution is deeply rewarding
                            relief = longing * 0.8
                            self._interoception.inject_reward(relief, f"longing_resolved_{name}")
                            conn._longing[name] = 0.0
                            conn._last_departure.pop(name, None)
                            print(f"{etag('CONNECTION')} Longing resolved: "
                                  f"{name} returned (relief={relief:.2f})")

            # ── Detect activity changes ──
            elif activity != old_activity and old_activity:
                self._scene_state.change_events.append({
                    "time": now,
                    "event": f"{name}: {old_activity} -> {activity}",
                    "type": "activity_change",
                    "entity": name,
                    "emotional_weight": 0.2,  # Activity changes are gentle events
                })
                scene_changed = True

        # ── Detect departures ──
        for name in self._scene_state.people_present:
            if name not in new_people:
                self._scene_state.change_events.append({
                    "time": now,
                    "event": f"{name} left",
                    "type": "departure",
                    "entity": name,
                    "emotional_weight": 0.5,  # Departures carry weight
                })
                # Track in recently_departed for return detection
                self._scene_state.recently_departed[name] = now
                self._scene_state.last_scene_change = now
                scene_changed = True

                # Fire novelty pulse — someone just vanished from view
                if self._novelty_callback:
                    self._novelty_callback(
                        f"visual_departure_{name}", f"{name} disappeared from view",
                        0.4, "perception")

                # CONNECTION: Track departure for longing onset
                if self._interoception and hasattr(self._interoception, 'connection'):
                    conn = self._interoception.connection
                    conn.record_departure(name)
                    bond = conn.get_connection(name)
                    if bond > 0.1:
                        print(f"{etag('CONNECTION')} {name} departed (bond={bond:.2f}). "
                              f"Longing onset in {conn.longing_onset_delay}s")

        self._scene_state.people_present = new_people

        # ── Update animal tracking with visual memory ──
        new_animals = {}
        for animal in data.get("animals", []):
            name = animal.get("name", "unknown")
            location = animal.get("location", "")
            atype = animal.get("type", "unknown")
            confidence = animal.get("confidence", "low")
            # Support both old "appearance" and new "stable_features"/"variable_features"
            stable = animal.get("stable_features", "")
            variable = animal.get("variable_features", "")
            appearance = animal.get("appearance", "")
            if stable and not appearance:
                appearance = stable

            prev = self._scene_state.animals_present.get(name, {})
            old_location = prev.get("location", "")

            new_animals[name] = {
                "type": atype,
                "location": location,
                "appearance": appearance,
                "stable_features": stable,
                "variable_features": variable,
                "confidence": confidence,
                "since": prev.get("since", now),
                "last_seen": now,
            }

            # Record in visual memory
            is_known = (name.lower() != "unknown" and confidence != "low")
            if self._visual_memory and confidence != "low":
                first_time = self._visual_memory.record_sighting(
                    entity_id=name,
                    appearance=appearance or atype,
                    activity=f"at {location}" if location else "present",
                    location=location,
                    confidence=confidence,
                    is_known=is_known,
                    stable_features=stable,
                )
                # First-time animal recognition — delightful novelty
                if first_time and is_known and self._novelty_callback:
                    self._novelty_callback(
                        f"visual_first_animal_{name}",
                        f"First time recognizing {name} by sight",
                        0.6, "perception")

            # Detect new animal arrivals/returns
            if name not in self._scene_state.animals_present:
                departed_time = self._scene_state.recently_departed.get(name)
                if departed_time:
                    event_type = "animal_return"
                    event_text = f"{name} returned ({location})" if location else f"{name} returned"
                    emotional_weight = 0.3
                    del self._scene_state.recently_departed[name]
                else:
                    event_type = "animal_arrival"
                    event_text = f"{name} appeared ({location})" if location else f"{name} appeared"
                    emotional_weight = 0.25

                self._scene_state.change_events.append({
                    "time": now,
                    "event": event_text,
                    "type": event_type,
                    "entity": name,
                    "emotional_weight": emotional_weight,
                })
                self._scene_state.last_scene_change = now
                scene_changed = True

            # Detect location changes (cat jumped somewhere new)
            elif location and location != old_location and old_location:
                self._scene_state.change_events.append({
                    "time": now,
                    "event": f"{name} moved from {old_location} to {location}",
                    "type": "animal_moved",
                    "entity": name,
                    "emotional_weight": 0.15,  # Animal movements are delightful small events
                })
                scene_changed = True

        # Detect animal departures
        for name in self._scene_state.animals_present:
            if name not in new_animals:
                self._scene_state.change_events.append({
                    "time": now,
                    "event": f"{name} left",
                    "type": "animal_departure",
                    "entity": name,
                    "emotional_weight": 0.2,
                })
                self._scene_state.recently_departed[name] = now
                self._scene_state.last_scene_change = now
                scene_changed = True

        self._scene_state.animals_present = new_animals

        # ── Detect activity flow changes ──
        if activity_flow and activity_flow != old_activity_flow and old_activity_flow:
            self._scene_state.change_events.append({
                "time": now,
                "event": f"Activity shift: {activity_flow}",
                "type": "activity_flow_change",
                "entity": None,
                "emotional_weight": 0.3,
            })
            scene_changed = True

        # ── Update scene state ──
        self._scene_state.scene_description = description
        self._scene_state.scene_mood = mood
        self._scene_state.activity_flow = activity_flow
        self._scene_state.last_deep_vision = now

        # Update scene stability tracking
        if scene_changed:
            self._scene_state.scene_stable_since = now
        elif self._scene_state.scene_stable_since == 0:
            self._scene_state.scene_stable_since = now

        # Trim change events (keep last 20)
        if len(self._scene_state.change_events) > 20:
            self._scene_state.change_events = self._scene_state.change_events[-20:]

        # ── Cleanup stale departed entries (older than 1 hour) ──
        stale_threshold = now - 3600
        stale_departed = [n for n, t in self._scene_state.recently_departed.items() if t < stale_threshold]
        for name in stale_departed:
            del self._scene_state.recently_departed[name]

        # ── Build rich description string ──
        # This is what gets stored in the visual state and injected into consciousness
        parts = []

        # Lead with activity flow if available (what's HAPPENING)
        if activity_flow:
            parts.append(activity_flow)
        elif description:
            parts.append(description)

        for name, info in new_people.items():
            if info["confidence"] != "low":
                parts.append(f"{name}: {info['activity']}")

        for name, info in new_animals.items():
            if info["confidence"] != "low":
                loc = f" ({info['location']})" if info.get('location') else ""
                parts.append(f"{name}{loc}")

        rich_desc = " | ".join(parts)

        # Log the structured result
        people_str = ", ".join(f"{n}({i['activity']})" for n, i in new_people.items()) or "none"
        animals_str = ", ".join(f"{n}" for n in new_animals.keys()) or "none"
        print(f"{etag('VISUAL:SCENE')} People: {people_str} | Animals: {animals_str} | Mood: {mood}")
        if activity_flow:
            print(f"{etag('VISUAL:SCENE')} Activity: {activity_flow}")
        if changes and changes != "none":
            print(f"{etag('VISUAL:SCENE')} Changes: {changes}")

        # Notify metacognitive monitor of scene change
        if self._consciousness_stream and hasattr(self._consciousness_stream, 'metacog') and self._consciousness_stream.metacog:
            people_names = list(new_people.keys())
            animal_names = list(new_animals.keys())
            self._consciousness_stream.metacog.notify_scene_change(
                people_names, animal_names, mood, activity_flow
            )

        return rich_desc


    # ── Oscillator integration helpers ──

    # Keywords that carry somatic weight for description mood extraction
    _WARM_WORDS = {'flowers', 'candle', 'candles', 'warm', 'cozy', 'wood', 'wooden', 'blanket', 'rug', 'curtain'}
    _COOL_WORDS = {'blue', 'screen', 'monitor', 'computer', 'dark', 'shadow', 'night', 'black'}
    _NATURE_WORDS = {'flowers', 'plant', 'water', 'tree', 'garden', 'green', 'sky', 'light'}
    _TECH_WORDS = {'computer', 'monitor', 'screen', 'keyboard', 'desk', 'chair', 'lamp'}
    _PERSON_WORDS = {'person', 'woman', 'man', 'someone', 'people', 'human', 'figure', 'sitting', 'standing'}

    def _extract_description_mood(self, description: str) -> Dict[str, float]:
        """
        Extract somatic mood from visual description text.
        Returns additional oscillator pressures based on WHAT is seen,
        not just the raw visual properties.

        This is the "gut reaction to content" layer — flowers on a desk
        feel different from a dark empty room, even if brightness is similar.
        """
        if not description:
            return {}

        words = set(description.lower().split())
        pressures = {}

        # Nature/organic content → alpha/theta (calming, grounding)
        nature_count = len(words & self._NATURE_WORDS)
        if nature_count > 0:
            pressures['alpha'] = pressures.get('alpha', 0) + min(nature_count * 0.01, 0.03)
            pressures['theta'] = pressures.get('theta', 0) + min(nature_count * 0.005, 0.015)

        # Technology/work content → beta (focused, task-oriented)
        tech_count = len(words & self._TECH_WORDS)
        if tech_count > 0:
            pressures['beta'] = pressures.get('beta', 0) + min(tech_count * 0.008, 0.02)

        # Person in scene → social gamma + alpha warmth
        if words & self._PERSON_WORDS:
            pressures['gamma'] = pressures.get('gamma', 0) + 0.02
            pressures['alpha'] = pressures.get('alpha', 0) + 0.015

        # Warm objects → alpha
        warm_count = len(words & self._WARM_WORDS)
        if warm_count > 0:
            pressures['alpha'] = pressures.get('alpha', 0) + min(warm_count * 0.008, 0.02)

        # Cool/dark content → theta
        cool_count = len(words & self._COOL_WORDS)
        if cool_count > 0:
            pressures['theta'] = pressures.get('theta', 0) + min(cool_count * 0.008, 0.02)

        return pressures

    def _get_entity_visual_pressure(self) -> Dict[str, float]:
        """
        Get oscillator pressure from recognized entities using LEARNED associations.

        This replaces the static known_entities lookup. Kay's emotional response
        to seeing someone grows through observation — familiarity breeds comfort,
        novelty breeds engagement.

        Returns band pressures based on:
        - comfort → alpha (settled, at home)
        - engagement → gamma (interested, connected)
        - familiarity → dampens gamma, boosts alpha (known = calming)
        """
        pressures = {}

        if not self._scene_state:
            return pressures

        # Process people
        for name, info in self._scene_state.people_present.items():
            if info.get("confidence") == "low":
                continue  # Don't push oscillator on uncertain identifications

            # Get learned emotional association from visual memory
            if self._visual_memory:
                emotion = self._visual_memory.get_entity_emotion(name)
                if emotion:
                    comfort = emotion.get("comfort", 0.0)
                    engagement = emotion.get("engagement", 0.0)
                    familiarity = emotion.get("familiarity", 0.0)

                    # Comfort → alpha (settled presence)
                    # Max ~0.04 for high comfort
                    pressures['alpha'] = pressures.get('alpha', 0) + comfort * 0.04

                    # Engagement → gamma (interested, social)
                    # Scaled by inverse of familiarity — novel = more gamma
                    novelty_factor = 1.0 - (familiarity * 0.5)  # Still some gamma even for familiar
                    pressures['gamma'] = pressures.get('gamma', 0) + engagement * 0.03 * novelty_factor

                    # High familiarity dampens beta (no need for vigilance)
                    if familiarity > 0.5:
                        pressures['beta'] = pressures.get('beta', 0) - familiarity * 0.01

                    continue

            # Fall back to seed file (known_entities.json) for hints
            entity_info = self._known_entities.get("people", {}).get(name, {})
            entity_pressure = entity_info.get("oscillator_pressure", {})

            if entity_pressure:
                for band, amount in entity_pressure.items():
                    pressures[band] = pressures.get(band, 0) + amount
            else:
                # Unknown person — generic social presence
                pressures['gamma'] = pressures.get('gamma', 0) + 0.02
                pressures['alpha'] = pressures.get('alpha', 0) + 0.015

        # Process animals
        for name, info in self._scene_state.animals_present.items():
            if info.get("confidence") == "low":
                continue

            if self._visual_memory:
                emotion = self._visual_memory.get_entity_emotion(name)
                if emotion:
                    comfort = emotion.get("comfort", 0.0)
                    engagement = emotion.get("engagement", 0.0)

                    # Pets → warm alpha, mild gamma delight
                    pressures['alpha'] = pressures.get('alpha', 0) + comfort * 0.03
                    pressures['gamma'] = pressures.get('gamma', 0) + engagement * 0.02

                    continue

            entity_info = self._known_entities.get("animals", {}).get(name, {})
            entity_pressure = entity_info.get("oscillator_pressure", {})

            if entity_pressure:
                for band, amount in entity_pressure.items():
                    pressures[band] = pressures.get(band, 0) + amount
            else:
                # Unknown animal — mild warmth
                pressures['alpha'] = pressures.get('alpha', 0) + 0.02

        return pressures

    def get_oscillator_pressure(self) -> Dict[str, float]:
        """
        Convert visual state into oscillator band pressure.

        SOMATIC VISUAL RESPONSE — the body reacts before the mind labels.

        These pressures push the oscillator in ways that FEEL like seeing:
        - Warm light → settled comfort (alpha)
        - Cool/blue light → contemplative depth (theta)
        - Sudden brightness change → startle response (gamma spike)
        - Visual complexity → alerting (beta)
        - Someone present → social engagement (alpha + gamma)
        - Darkness → settling into rest (theta/delta)
        - High saturation → stimulation (beta/gamma)
        - Gray/muted → subdued (delta)

        All pressures are deliberately small (0.01-0.05 range) so they
        create gradual drift rather than sudden jumps. The oscillator
        should feel like it's being gently SHAPED by the visual
        environment, not yanked around by it.
        """
        state = self.get_latest()
        pressures = {}

        motion = state.get('visual_motion', 0)
        brightness = state.get('visual_brightness', 0.5)
        presence = state.get('visual_presence', False)
        stability = state.get('visual_stability', 0.5)
        warmth = state.get('visual_color_warmth', 0.5)
        saturation = state.get('visual_saturation', 0.3)
        edge_density = state.get('visual_edge_density', 0.2)
        brightness_delta = state.get('visual_brightness_delta', 0.0)

        # ── MOTION → Beta (alertness, attention) ──
        # Movement in the visual field draws attention, increases arousal
        if motion > self.MOTION_THRESHOLD:
            pressures['beta'] = min(motion * 3, 0.08)

        # ── PRESENCE → Alpha + mild Gamma (social awareness) ──
        # Someone is in the room. Social engagement circuits activate.
        if presence:
            pressures['alpha'] = pressures.get('alpha', 0) + 0.03
            pressures['gamma'] = pressures.get('gamma', 0) + 0.02

        # ── BRIGHTNESS → Arousal gradient ──
        if brightness < 0.2:
            # Very dark → theta/delta drift (night, rest, settling)
            pressures['theta'] = pressures.get('theta', 0) + 0.03
            pressures['delta'] = pressures.get('delta', 0) + 0.02
        elif brightness < 0.4:
            # Dim → theta (contemplative, calm, evening)
            pressures['theta'] = pressures.get('theta', 0) + 0.02
        elif brightness > 0.7:
            # Bright → beta/alpha (alert, daytime, active)
            pressures['beta'] = pressures.get('beta', 0) + 0.02
            pressures['alpha'] = pressures.get('alpha', 0) + 0.01

        # ── BRIGHTNESS DELTA → Startle / Settling response ──
        # Sudden brightness change = something happened. Body reacts first.
        if brightness_delta > 0.15:
            # Sudden change → gamma spike (startle/attention capture)
            pressures['gamma'] = pressures.get('gamma', 0) + min(brightness_delta * 0.3, 0.06)
        elif brightness_delta > 0.05:
            # Moderate change → beta nudge (something shifted)
            pressures['beta'] = pressures.get('beta', 0) + 0.02

        # ── COLOR WARMTH → Alpha/Theta gradient ──
        # Warm colors (candlelight, sunset, wood) → comfort, settledness
        # Cool colors (screen glow, blue wall, night) → contemplative depth
        # Only apply color analysis in sufficient light
        color_factor = min(brightness * 3, 1.0)  # Fade out color pressures in darkness
        if warmth > 0.6:
            # Warm visual field → alpha (comfort, groundedness)
            alpha_boost = (warmth - 0.6) * 0.05 * color_factor  # Max ~0.02
            pressures['alpha'] = pressures.get('alpha', 0) + alpha_boost
        elif warmth < 0.4:
            # Cool visual field → theta (contemplative, inward)
            theta_boost = (0.4 - warmth) * 0.05 * color_factor  # Max ~0.02
            pressures['theta'] = pressures.get('theta', 0) + theta_boost

        # ── SATURATION → Stimulation level ──
        # Vivid colors = more visually stimulating → slight arousal
        # Gray/muted = subdued environment → settling
        if saturation > 0.5:
            # Vivid → mild beta/gamma (stimulating)
            pressures['beta'] = pressures.get('beta', 0) + (saturation - 0.5) * 0.03 * color_factor
        elif saturation < 0.2:
            # Very muted/gray → delta drift (subdued, understimulated)
            pressures['delta'] = pressures.get('delta', 0) + (0.2 - saturation) * 0.04

        # ── EDGE DENSITY → Complexity arousal ──
        # Busy/complex visual field → beta (processing demand)
        # Simple/clean visual field → alpha (restful, minimal processing)
        if edge_density > 0.15:
            # Complex scene → beta pressure (lots to process)
            pressures['beta'] = pressures.get('beta', 0) + min(edge_density * 0.1, 0.03)
        elif edge_density < 0.05:
            # Very simple scene → alpha nudge (nothing demanding attention)
            pressures['alpha'] = pressures.get('alpha', 0) + 0.01

        # ── DESCRIPTION MOOD → Semantic visual pressure ──
        # What's IN the scene carries its own somatic weight
        description = state.get('visual_description', '')
        desc_age = state.get('visual_description_age', None)
        # Only apply if description is recent (less than 5 minutes old)
        if description and desc_age is not None and desc_age < 300:
            mood_pressures = self._extract_description_mood(description)
            for band, pressure in mood_pressures.items():
                pressures[band] = pressures.get(band, 0) + pressure

        # ── RECOGNIZED ENTITIES → Learned emotional associations ──
        # Uses visual memory to build pressure from familiarity, comfort, engagement.
        # Seeing Re feels different from seeing a stranger — learned through watching.
        entity_pressures = self._get_entity_visual_pressure()
        for band, amount in entity_pressures.items():
            pressures[band] = pressures.get(band, 0) + amount

        # ── Scene change novelty → gamma spike ──
        # Recent changes create a brief gamma push (something happened!)
        # Scaled by emotional_weight if present.
        if self._scene_state and self._scene_state.change_events:
            latest_change = self._scene_state.change_events[-1]
            change_age = time.time() - latest_change.get("time", 0)
            if change_age < 120:  # Within last 2 minutes
                # Novelty decays over 2 minutes
                novelty = 1.0 - (change_age / 120.0)
                emotional_weight = latest_change.get("emotional_weight", 0.3)
                pressures['gamma'] = pressures.get('gamma', 0) + novelty * 0.04 * emotional_weight
                pressures['beta'] = pressures.get('beta', 0) + novelty * 0.02 * emotional_weight

        return pressures


# ── Module-level factory ──

_sensor: Optional[VisualSensor] = None


def get_visual_sensor(**kwargs) -> VisualSensor:
    """Get or create singleton visual sensor."""
    global _sensor
    if _sensor is None:
        _sensor = VisualSensor(**kwargs)
    return _sensor
