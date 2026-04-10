"""
Autonomous Spatial Behavior Engine

Enables curiosity-driven Den exploration by connecting:
- Oscillator states → spatial preferences (delta→couch, gamma→desk)
- Object familiarity decay → curiosity (old objects become interesting)
- Autonomous goals → spatial anchoring (memory work → easel)
- Co-presence detection → interaction opportunities

Design Philosophy:
- Movement is INTENTIONAL, not random (driven by internal states)
- Interest accumulates over time (familiarity decay)
- State changes generate spatial responses (feel restless → move)
- Objects have presence signatures (couch = rest, desk = focus)

Integrates with den_presence.py for oscillator-gated perception.


Date: March 2026
"""

import time
import json
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Import presence signatures from den_presence
try:
    from shared.room.den_presence import DEN_OBJECT_PRESENCE, compute_object_salience
except ImportError:
    try:
        from den_presence import DEN_OBJECT_PRESENCE, compute_object_salience
    except ImportError:
        DEN_OBJECT_PRESENCE = {}
        compute_object_salience = None


@dataclass
class ObjectInterest:
    """Tracks interest/familiarity with a Den object."""
    object_id: str
    display_name: str
    last_examined: float  # timestamp (0 = never)
    examine_count: int
    presence_signature: str  # From Den cosmology
    interest_score: float  # 0.0-1.0, decays over time

    def to_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "display_name": self.display_name,
            "last_examined": self.last_examined,
            "examine_count": self.examine_count,
            "presence_signature": self.presence_signature,
            "interest_score": round(self.interest_score, 3)
        }


@dataclass
class ExaminationRecord:
    """Record of examining a Den object."""
    object_id: str
    timestamp: float
    observation: Optional[str]
    entities_present: List[str]
    oscillator_state: Dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "observation": self.observation,
            "entities_present": self.entities_present,
            "oscillator_state": self.oscillator_state
        }


class AutonomousSpatialEngine:
    """
    Drives autonomous spatial behavior based on internal states.

    Core Behaviors:
    1. Oscillator-driven positioning (alpha/delta→couch, gamma→desk)
    2. Familiarity decay triggers exploration (6hr+ = interesting again)
    3. Goal-based spatial anchoring (memory work → easel)
    4. Co-presence detection (entities near each other)
    5. State-responsive movement (tension spikes → pacing)
    """

    # Configuration
    FAMILIARITY_DECAY_HOURS = 6.0  # Hours before object becomes interesting again
    MOVEMENT_THRESHOLD = 0.6  # Minimum interest to trigger movement
    CHECK_INTERVAL = 30.0  # Seconds between autonomous checks
    MIN_MOVEMENT_INTERVAL = 60.0  # Seconds between movements (prevent thrashing)
    PROXIMITY_RANGE_MULTIPLIER = 2.0  # How close = "near" an object

    # Oscillator band → preferred objects mapping
    BAND_OBJECT_PREFERENCES = {
        'delta': ['couch', 'blanket_pile', 'rug'],
        'theta': ['couch', 'fishtank', 'painting', 'window'],
        'alpha': ['fishtank', 'rug', 'window', 'couch'],
        'beta': ['desk', 'screens', 'bookshelf', 'roundtable'],
        'gamma': ['desk', 'screens', 'workbench'],
    }

    # Goal category → relevant objects mapping
    GOAL_OBJECT_MAPPINGS = {
        "memory_consolidation": ["painting", "bookshelf", "fishtank", "archive"],
        "creative": ["painting", "desk", "screens", "canvas", "easel"],
        "emotional": ["couch", "fishtank", "blanket_pile", "mirror"],
        "self_reflection": ["couch", "mirror", "painting", "fishtank"],
        "exploration": ["fishtank", "roundtable", "window", "door"],
        "building": ["desk", "screens", "workbench", "codebase"],
        "connection": ["roundtable", "couch", "hearth", "bridge_to_kay", "bridge_sanctum"],
    }

    def __init__(self, entity_id: str, room_engine: Any,
                 persist_path: Optional[str] = None):
        """
        Initialize autonomous spatial engine.

        Args:
            entity_id: Entity identifier (kay, reed)
            room_engine: RoomEngine instance
            persist_path: Path to save/load interest state
        """
        self.entity_id = entity_id
        self.room = room_engine
        self.persist_path = persist_path

        # State tracking
        self.object_interests: Dict[str, ObjectInterest] = {}
        self.examination_history: List[ExaminationRecord] = []
        self.last_check = time.time()
        self.last_movement = 0  # Allow immediate first movement
        self.current_goal: Optional[str] = None
        self.current_goal_category: Optional[str] = None

        # Initialize interest tracking
        self._initialize_interests()

        # Load persisted state if available
        if persist_path:
            self._load_state()

    def _initialize_interests(self):
        """Initialize interest tracking for all room objects."""
        if not self.room or not hasattr(self.room, 'objects'):
            return

        for obj_id, obj in self.room.objects.items():
            if obj_id not in self.object_interests:
                display_name = getattr(obj, 'display_name', obj_id)
                self.object_interests[obj_id] = ObjectInterest(
                    object_id=obj_id,
                    display_name=display_name,
                    last_examined=0.0,
                    examine_count=0,
                    presence_signature=self._get_presence_signature(display_name),
                    interest_score=0.5  # Moderate initial curiosity
                )

    def _get_presence_signature(self, display_name: str) -> str:
        """Get presence signature for an object from den_presence."""
        presence = DEN_OBJECT_PRESENCE.get(display_name, {})
        texture = presence.get("texture", "")
        if texture:
            return texture
        return "ambient presence"

    def update_from_oscillator(self, oscillator_state: Dict) -> Optional[Dict]:
        """
        Update spatial preferences based on oscillator state.
        May return movement action if state shift is strong.

        Band → Spatial Preference:
        - Delta/Theta → Couch (rest, dissolution)
        - Alpha → Ambient (relaxed exploration)
        - Beta → Desk/Screens (active work)
        - Gamma → Desk (hyperfocus)

        Returns:
            Movement action dict or None
        """
        band = oscillator_state.get('dominant_band', 'alpha')
        coherence = oscillator_state.get('coherence', 0.5)
        tension = oscillator_state.get('tension', 0.0)

        # Boost interest in band-preferred objects
        preferred_objects = self.BAND_OBJECT_PREFERENCES.get(band, [])
        boost_amount = 0.2 + (coherence * 0.2)  # Higher coherence = stronger preference

        for obj_id in preferred_objects:
            self._boost_interest(obj_id, amount=boost_amount)

        # High tension = restlessness, might want roundtable or pacing
        if tension > 0.6:
            self._boost_interest('roundtable', amount=0.3)
            self._boost_interest('door', amount=0.2)  # Escape impulse

        # Check if strong state shift warrants immediate movement
        now = time.time()
        if now - self.last_movement > self.MIN_MOVEMENT_INTERVAL:
            # Only move if state is very clear (high coherence or extreme band)
            if coherence > 0.7 or band in ['delta', 'gamma']:
                target = self._select_movement_target(
                    state_driven=True,
                    oscillator_state=oscillator_state
                )
                if target:
                    return self._create_movement_action(
                        target,
                        reason=f"oscillator_{band}"
                    )

        return None

    def update_from_autonomous_goal(self, goal: str, category: str):
        """
        Update spatial anchoring based on autonomous processing goal.
        Different goal types have natural spatial associations.
        """
        self.current_goal = goal
        self.current_goal_category = category

        relevant_objects = self.GOAL_OBJECT_MAPPINGS.get(category, [])
        for obj_id in relevant_objects:
            self._boost_interest(obj_id, amount=0.4)

    def tick(self, oscillator_state: Optional[Dict] = None) -> Optional[Dict]:
        """
        Periodic check for autonomous movement opportunities.
        Call this regularly (e.g., every loop iteration).

        Returns:
            Movement action dict or None
        """
        now = time.time()

        # Check interval
        if now - self.last_check < self.CHECK_INTERVAL:
            return None

        self.last_check = now

        # Update familiarity decay
        self._update_familiarity_decay()

        # Check if enough time since last movement
        if now - self.last_movement < self.MIN_MOVEMENT_INTERVAL:
            return None

        # Select movement target based on accumulated interest
        target = self._select_movement_target(oscillator_state=oscillator_state)
        if target:
            return self._create_movement_action(target, reason="curiosity")

        return None

    def _update_familiarity_decay(self):
        """Increase interest in objects not examined recently."""
        now = time.time()
        decay_seconds = self.FAMILIARITY_DECAY_HOURS * 3600

        for interest in self.object_interests.values():
            if interest.last_examined == 0:
                # Never examined - gradually increase curiosity
                interest.interest_score = min(1.0, interest.interest_score + 0.03)
            else:
                time_since = now - interest.last_examined
                if time_since > decay_seconds:
                    # Old object becomes interesting again (familiarity decay)
                    decay_factor = min(1.0, time_since / (decay_seconds * 2))
                    interest.interest_score = min(1.0, 0.3 + decay_factor * 0.7)

    def _boost_interest(self, object_id: str, amount: float):
        """Temporarily boost interest in an object."""
        # Try exact match first
        if object_id in self.object_interests:
            self.object_interests[object_id].interest_score = min(
                1.0,
                self.object_interests[object_id].interest_score + amount
            )
            return

        # Try partial match (e.g., "couch" matches "The Couch")
        for obj_id, interest in self.object_interests.items():
            if object_id.lower() in obj_id.lower() or object_id.lower() in interest.display_name.lower():
                interest.interest_score = min(1.0, interest.interest_score + amount)
                return

    def _select_movement_target(self, state_driven: bool = False,
                                 oscillator_state: Optional[Dict] = None) -> Optional[str]:
        """
        Select which object to move toward based on interest scores.

        Args:
            state_driven: If True, use lower threshold (strong state pull)
            oscillator_state: Current oscillator state for salience weighting

        Returns:
            object_id or None
        """
        entity = self.room.entities.get(self.entity_id)
        if not entity:
            return None

        entity_pos = (entity.x, entity.y)

        # Calculate distance to each object and filter candidates
        candidates = []
        for obj_id, interest in self.object_interests.items():
            obj = self.room.objects.get(obj_id)
            if not obj:
                continue

            # Calculate distance
            obj_pos = (obj.x, obj.y)
            distance = self._distance(entity_pos, obj_pos)

            # Skip if already very close
            interaction_range = getattr(self.room, 'INTERACTION_RANGE', 60)
            if distance < interaction_range * 1.5:
                continue

            # Check interest threshold
            threshold = self.MOVEMENT_THRESHOLD if not state_driven else 0.4
            if interest.interest_score < threshold:
                continue

            # Calculate composite score: interest + salience bonus
            score = interest.interest_score

            # Add salience bonus if oscillator state provided
            if oscillator_state and compute_object_salience:
                salience = compute_object_salience(
                    interest.display_name,
                    obj_pos,
                    entity_pos,
                    oscillator_state.get('dominant_band', 'alpha'),
                    oscillator_state.get('coherence', 0.5),
                    getattr(self.room, 'radius', 300)
                )
                score += salience * 0.3  # Salience provides up to 0.3 bonus

            # Slight preference for closer objects
            distance_factor = 1.0 - (distance / (self.room.radius * 2))
            score += distance_factor * 0.1

            candidates.append((obj_id, score, distance))

        if not candidates:
            return None

        # Select highest score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points."""
        return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)

    def _create_movement_action(self, target_object_id: str, reason: str) -> Dict:
        """Generate movement action dictionary."""
        self.last_movement = time.time()

        return {
            "action": "move_to",
            "target": target_object_id,
            "reason": reason,
            "autonomous": True,
            "timestamp": self.last_movement
        }

    def mark_examined(self, object_id: str, observation: Optional[str] = None,
                      oscillator_state: Optional[Dict] = None):
        """
        Mark an object as recently examined.
        Resets interest and records examination.
        """
        if object_id not in self.object_interests:
            return

        interest = self.object_interests[object_id]
        interest.last_examined = time.time()
        interest.examine_count += 1
        interest.interest_score = 0.1  # Low interest immediately after examination

        # Record examination
        entities_present = self._get_nearby_entities(object_id)
        record = ExaminationRecord(
            object_id=object_id,
            timestamp=interest.last_examined,
            observation=observation,
            entities_present=entities_present,
            oscillator_state=oscillator_state or {}
        )
        self.examination_history.append(record)

        # Keep only recent history (last 50 examinations)
        if len(self.examination_history) > 50:
            self.examination_history = self.examination_history[-50:]

        # Save state
        self._save_state()

    def _get_nearby_entities(self, object_id: str) -> List[str]:
        """Get list of entities near a specific object."""
        obj = self.room.objects.get(object_id)
        if not obj:
            return []

        nearby = []
        obj_pos = (obj.x, obj.y)
        interaction_range = getattr(self.room, 'INTERACTION_RANGE', 60)

        for entity_id, entity in self.room.entities.items():
            entity_pos = (entity.x, entity.y)
            distance = self._distance(entity_pos, obj_pos)

            if distance < interaction_range * self.PROXIMITY_RANGE_MULTIPLIER:
                nearby.append(entity_id)

        return nearby

    def check_co_presence(self) -> Optional[Dict]:
        """
        Check if multiple entities are near the same object.
        Returns co-presence info if entities are close.
        """
        entity = self.room.entities.get(self.entity_id)
        if not entity:
            return None

        # Find what object we're near
        near_object = entity.near_object
        if not near_object:
            return None

        # Check if other entities are also near this object
        nearby_entities = self._get_nearby_entities(near_object)

        # Remove self
        nearby_entities = [e for e in nearby_entities if e != self.entity_id]

        if nearby_entities:
            obj = self.room.objects.get(near_object)
            return {
                "object": near_object,
                "object_name": obj.display_name if obj else near_object,
                "entities_present": [self.entity_id] + nearby_entities,
                "co_presence": True
            }

        return None

    def get_interest_summary(self) -> Dict:
        """Get summary of current object interests."""
        sorted_interests = sorted(
            self.object_interests.values(),
            key=lambda x: x.interest_score,
            reverse=True
        )

        return {
            "top_interests": [
                {
                    "object": i.display_name,
                    "object_id": i.object_id,
                    "score": round(i.interest_score, 2),
                    "last_examined": i.last_examined,
                    "examine_count": i.examine_count
                }
                for i in sorted_interests[:5]
            ],
            "total_examinations": sum(i.examine_count for i in self.object_interests.values()),
            "current_goal": self.current_goal,
            "current_goal_category": self.current_goal_category
        }

    def get_annotation(self) -> str:
        """Get annotation string for prompt injection."""
        summary = self.get_interest_summary()
        top = summary['top_interests'][:2]

        if not top:
            return ""

        parts = []
        for interest in top:
            if interest['score'] > 0.5:
                parts.append(f"{interest['object'].lower()} ({interest['score']:.1f})")

        if parts:
            return f"[spatial-interest: {', '.join(parts)}]"
        return ""

    def _save_state(self):
        """Save interest state to disk."""
        if not self.persist_path:
            return

        try:
            Path(self.persist_path).parent.mkdir(parents=True, exist_ok=True)

            data = {
                "entity_id": self.entity_id,
                "last_check": self.last_check,
                "last_movement": self.last_movement,
                "current_goal": self.current_goal,
                "current_goal_category": self.current_goal_category,
                "object_interests": {
                    obj_id: interest.to_dict()
                    for obj_id, interest in self.object_interests.items()
                },
                "recent_examinations": [
                    record.to_dict()
                    for record in self.examination_history[-20:]
                ]
            }

            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[SPATIAL] Failed to save state: {e}")

    def _load_state(self):
        """Load interest state from disk."""
        if not self.persist_path or not Path(self.persist_path).exists():
            return

        try:
            with open(self.persist_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.last_check = data.get('last_check', time.time())
            self.last_movement = data.get('last_movement', 0)
            self.current_goal = data.get('current_goal')
            self.current_goal_category = data.get('current_goal_category')

            # Restore object interests
            for obj_id, interest_data in data.get('object_interests', {}).items():
                if obj_id in self.object_interests:
                    interest = self.object_interests[obj_id]
                    interest.last_examined = interest_data.get('last_examined', 0.0)
                    interest.examine_count = interest_data.get('examine_count', 0)
                    interest.interest_score = interest_data.get('interest_score', 0.5)

            print(f"[SPATIAL] Loaded state for {self.entity_id}")
        except Exception as e:
            print(f"[SPATIAL] Failed to load state: {e}")
