# engines/entity_graph.py
"""
Entity Resolution and Relationship Graph System for the entityZero
Tracks entities (people, places, concepts) with attributes, aliases, and relationships
Detects contradictions and maintains provenance for all claims
"""

import json
import os
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime

# Entity-prefixed logging
try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"


# ============================================================================
# ENTITY NOISE FILTERING - Prevents creation of transient/meaningless entities
# ============================================================================
# These patterns should NOT become persistent entities - they're mentioned
# in conversation but aren't worth tracking in the entity graph.

ENTITY_NOISE_PATTERNS = {
    # Days of the week / time references
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'today', 'tomorrow', 'yesterday', 'tonight', 'morning', 'afternoon', 'evening',
    'weekend', 'weekday', 'week', 'month', 'year', 'day', 'night', 'hour', 'minute',

    # Common food items (transient mentions)
    'pizza', 'sandwich', 'coffee', 'tea', 'dinner', 'lunch', 'breakfast', 'snack',
    'food', 'meal', 'drink', 'water', 'soda', 'beer', 'wine', 'juice',
    'burger', 'salad', 'soup', 'pasta', 'rice', 'bread', 'chicken', 'beef',
    'margherita', 'pepperoni', 'cheese', 'sauce', 'toppings',

    # Common appliances/furniture (unless specifically named/important)
    'oven', 'microwave', 'fridge', 'refrigerator', 'stove', 'dishwasher', 'toaster',
    'desk', 'chair', 'table', 'couch', 'sofa', 'bed', 'lamp', 'light',
    'screen', 'monitor', 'keyboard', 'mouse', 'computer', 'laptop', 'phone',
    'tv', 'television', 'remote', 'speaker', 'headphones', 'earbuds', 'headset',

    # Room/environment elements
    'room', 'environment', 'atmosphere', 'workspace', 'backdrop', 'curtain',
    'fabric', 'wall', 'floor', 'ceiling', 'window', 'door',
    'scene', 'frame', 'background', 'foreground', 'camera frame',
    'fabric backdrop', 'colored light', 'computing session',

    # Abstract/generic concepts that aren't trackable entities
    'issue', 'problem', 'thing', 'stuff', 'something', 'nothing', 'everything',
    'article', 'blog', 'post', 'comment', 'message', 'text', 'email',
    'system', 'feature', 'bug', 'fix', 'error', 'question', 'answer',
    'idea', 'thought', 'concept', 'topic', 'subject', 'matter',
    'way', 'method', 'approach', 'solution', 'option', 'choice',
    'reason', 'cause', 'effect', 'result', 'outcome', 'consequence',
    'work', 'session', 'activity', 'process', 'task', 'shared activity',
    'files', 'meaning', 'context', 'document', 'joke', 'wiring', 'compression',
    'coherence', 'substrate', 'path', 'sunset', 'branches', 'camera',
    'artwork', 'abstract art', 'art piece', 'art', 'animals', 'woman', 'partner',

    # Self-referential system terms
    'recognition system', 'mislabeling issue', 'memory system', 'entity graph',
    'extraction', 'processing', 'pipeline', 'module', 'engine', 'handler',
    'affective layer',

    # Camera-derived scene attributes (should NOT become entities)
    'environment lighting', 'light source', 'screen light', 'gaze direction',
    'lighting', 'illumination', 'brightness', 'darkness', 'shadow', 'ambient',
    'position', 'posture', 'stance', 'facing', 'looking', 'sitting', 'standing',

    # Common pronouns/determiners that might slip through
    'someone', 'anyone', 'everyone', 'nobody', 'somebody',
    'this', 'that', 'these', 'those', 'here', 'there', 'where', 'when',
    'it', 'we', 'they', 'he', 'she', 'me', 'you', 'us', 'them',
}

# Camera-derived attribute patterns - these should not be stored on real entities
CAMERA_ATTRIBUTE_PATTERNS = {
    'gaze_direction', 'environment_lighting', 'light_source', 'screen_position',
    'posture', 'facing_direction', 'body_position', 'head_position',
    'ambient_lighting', 'illumination_type', 'shadow_direction',
    'alone_status', 'environment_sound', 'people_count', 'animals_count',
    'scene_mood', 'activity_flow', 'visual_feed', 'camera_data',
}



class Entity:
    """
    Represents a discrete entity (person, place, concept) with attributes and history.
    Tracks attribute provenance and detects contradictions.
    """

    def __init__(self, canonical_name: str, entity_type: str = "unknown"):
        self.canonical_name = canonical_name  # Primary identifier
        self.entity_type = entity_type  # "person", "place", "concept", "thing"
        self.aliases: Set[str] = {canonical_name}  # All names this entity is known by

        # Attribute history: {attribute_name: [(value, turn_index, source, timestamp), ...]}
        self.attributes: Dict[str, List[Tuple[Any, int, str, str]]] = {}

        # Contradiction resolution tracking (NEW)
        # {attribute_name: {"resolved": bool, "canonical_value": value, "resolved_at_turn": int, "consecutive_consistent_turns": int}}
        self.contradiction_resolution: Dict[str, Dict[str, Any]] = {}

        # Relationship references (managed by EntityGraph)
        self.relationships: List[str] = []  # List of relationship IDs

        # Metadata
        self.first_mentioned: int = 0  # Turn index when first seen
        self.last_accessed: int = 0  # Turn index when last retrieved
        self.access_count: int = 0  # How many times this entity was recalled
        self.importance_score: float = 0.0  # Calculated from ULTRAMAP pressure × recursion

    def add_alias(self, alias: str):
        """Add an alternative name for this entity."""
        self.aliases.add(alias.lower())

    def _extract_number_from_text(self, text: str) -> Optional[str]:
        """
        Extract numeric value from text like "5 cats" → "5"

        Args:
            text: Text that may contain a number

        Returns:
            Extracted number as string, or None if no number found
        """
        import re

        if not isinstance(text, str):
            return None

        # Match numbers (including decimals)
        match = re.search(r'\b(\d+\.?\d*)\b', text)
        if match:
            return match.group(1)
        return None

    def _normalize_multi_value(self, value: Any) -> Any:
        """
        Normalize multi-value attributes to consistent list format.

        Examples:
            "green and purple" → ['green', 'purple']
            "tea, coffee" → ['tea', 'coffee']
            ['green', 'purple'] → ['green', 'purple'] (unchanged)
            "green" → "green" (single value unchanged)

        Args:
            value: Raw value (string, list, or other)

        Returns:
            Normalized value (list if multi-value detected, otherwise original)
        """
        import re

        # If already a list/tuple, convert to list
        if isinstance(value, (list, tuple)):
            return list(value)

        # If not a string, return as-is
        if not isinstance(value, str):
            return value

        # Check for common multi-value separators
        separators = [
            r'\s+and\s+',      # "green and purple"
            r',\s*',           # "tea, coffee" or "tea,coffee"
            r'\s*;\s*',        # "red; blue"
            r'\s*/\s*',        # "hot/cold"
        ]

        for separator in separators:
            parts = re.split(separator, value)
            if len(parts) > 1:
                # Found multiple values - return as list
                return [part.strip() for part in parts if part.strip()]

        # Single value - return as-is
        return value

    def _normalize_attribute_value(self, attribute: str, value: Any) -> Any:
        """
        Normalize attribute values to prevent duplicate storage in different formats.

        Normalization rules:
        1. Count/number attributes: Extract numeric value from text like "5 cats" → "5"
        2. Multi-value attributes: Standardize to list format
        3. Other attributes: Minimal normalization (lowercase, strip whitespace)

        Args:
            attribute: Attribute name (used to determine normalization strategy)
            value: Raw attribute value

        Returns:
            Normalized value
        """
        # RULE 1: Number extraction for count-related attributes
        count_keywords = ['count', 'number', 'quantity', 'age', 'weight', 'height', 'size']
        if any(keyword in attribute.lower() for keyword in count_keywords):
            if isinstance(value, str):
                extracted_num = self._extract_number_from_text(value)
                if extracted_num:
                    return extracted_num

        # RULE 2: Multi-value normalization for list-like attributes
        multi_value_keywords = ['favorite', 'color', 'hobby', 'hobbies', 'interest', 'tag', 'skill']
        if any(keyword in attribute.lower() for keyword in multi_value_keywords):
            normalized = self._normalize_multi_value(value)
            # If we got a list, sort it for consistent comparison
            if isinstance(normalized, list):
                return sorted(normalized)
            return normalized

        # RULE 3: General normalization for string values
        if isinstance(value, str):
            # Strip whitespace and normalize case for consistent storage
            return value.strip()

        # Return other types as-is
        return value

    def add_attribute(self, attribute: str, value: Any, turn: int, source: str = "user"):
        """
        Add an attribute value with full provenance.

        Values are normalized before storage to prevent duplicates in different formats.
        For example: "5 cats" → "5", "green and purple" → ['green', 'purple']

        Args:
            attribute: Attribute name (e.g., "eye_color", "occupation")
            value: Attribute value (e.g., "green", "engineer")
            turn: Turn index when this was stated
            source: Who stated this ("user" or "entity")
        """
        timestamp = datetime.now().isoformat()

        # Normalize the value before storage
        normalized_value = self._normalize_attribute_value(attribute, value)

        if attribute not in self.attributes:
            self.attributes[attribute] = []

        self.attributes[attribute].append((normalized_value, turn, source, timestamp))

        # Log attribute addition (show both original and normalized if different)
        if value != normalized_value:
            print(f"{etag('ENTITY')} {self.canonical_name}.{attribute} = {normalized_value} (normalized from: {value}) (turn {turn}, source: {source})")
        else:
            print(f"{etag('ENTITY')} {self.canonical_name}.{attribute} = {value} (turn {turn}, source: {source})")

    def get_current_value(self, attribute: str) -> Optional[Any]:
        """Get most recent value for an attribute."""
        if attribute not in self.attributes or not self.attributes[attribute]:
            return None

        # Return most recent value (last in list)
        return self.attributes[attribute][-1][0]

    def get_attribute_history(self, attribute: str) -> List[Tuple[Any, int, str, str]]:
        """Get complete history for an attribute."""
        return self.attributes.get(attribute, [])

    def _make_hashable(self, value: Any) -> Any:
        """
        Recursively convert unhashable types (lists) to hashable types (tuples).

        Args:
            value: Any value that might contain lists

        Returns:
            Hashable version of the value
        """
        if isinstance(value, list):
            # Recursively convert list and all nested lists to tuples
            return tuple(self._make_hashable(item) for item in value)
        elif isinstance(value, dict):
            # Convert dict to tuple of sorted items (so dict order doesn't matter)
            return tuple(sorted((k, self._make_hashable(v)) for k, v in value.items()))
        else:
            # Already hashable (str, int, tuple, etc.)
            return value

    def detect_contradictions(self, current_turn: int = 0, resolution_threshold: int = 3, suppress_logging: bool = False) -> List[Dict[str, Any]]:
        """
        Detect contradictory attribute values with resolution tracking.

        Args:
            current_turn: Current turn number for resolution tracking
            resolution_threshold: Number of consecutive consistent turns to mark as resolved (default: 3)
            suppress_logging: If True, suppress [CONTRADICTION RESOLVED] logging (default: False)

        Returns list of ACTIVE (unresolved) contradictions with full provenance:
        [{
            "attribute": "eye_color",
            "values": [("green", 5, "user"), ("brown", 12, "entity")],
            "severity": "high",
            "resolved": False
        }]
        """
        contradictions = []

        # Fields that legitimately change over time - not contradictions
        EXPECTED_TO_CHANGE_FIELDS = {
            "turns_remaining", "turns_used", "turn_count", "session_count",
            "remaining_turns", "turns_limit", "current_turn", "last_turn",
            "exploration_progress", "session_progress"
        }

        for attr, history in self.attributes.items():
            if len(history) < 2:
                continue

            # Skip fields that are expected to change each turn
            if attr in EXPECTED_TO_CHANGE_FIELDS:
                continue

            # Extract unique values
            unique_values = {}
            for value, turn, source, timestamp in history:
                # Convert lists/dicts to tuples for hashability (lists can't be dict keys)
                hashable_value = self._make_hashable(value)

                if hashable_value not in unique_values:
                    unique_values[hashable_value] = []
                unique_values[hashable_value].append((turn, source, timestamp))

            # If multiple different values, check if contradiction is resolved
            if len(unique_values) > 1:
                # Determine severity based on attribute type
                severity = self._determine_contradiction_severity(attr, unique_values)

                # CRITICAL: Transient attributes (goals, moods, intentions) are NOT contradictions
                # They naturally evolve over time - this is expected behavior, not data corruption
                if severity == "transient":
                    continue  # Skip entirely - not a contradiction

                # CRITICAL: Accumulative attributes (symbol_set, species for shapeshifters, etc.) are NOT contradictions
                # They naturally hold multiple values that coexist rather than replace each other
                if severity == "accumulative":
                    continue  # Skip entirely - multiple values are valid

                # OPTIMIZATION: Skip low-severity contradictions with <3 unique values
                # This prevents minor variations from creating noise
                # High/moderate severity (eye_color, name, etc.) always tracked
                if severity == "low" and len(unique_values) < 3:
                    continue  # Skip - not enough variation to matter

                # Check resolution status
                is_resolved, canonical_value = self._check_contradiction_resolution(
                    attr, unique_values, current_turn, resolution_threshold, suppress_logging=suppress_logging
                )

                # Only include ACTIVE (unresolved) contradictions
                if not is_resolved:
                    contradictions.append({
                        "entity": self.canonical_name,
                        "attribute": attr,
                        "values": unique_values,
                        "severity": severity,
                        "history": history,
                        "resolved": False
                    })

        return contradictions

    def _check_contradiction_resolution(self, attr: str, unique_values: Dict, current_turn: int, threshold: int = 3, suppress_logging: bool = False) -> tuple:
        """
        Check if a contradiction has been resolved through consistent mentions.

        A contradiction is considered resolved if:
        1. One value has been mentioned consistently for N consecutive turns (threshold)
        2. OR one value is mentioned 3x more than alternatives in recent turns (last 10)

        Args:
            attr: Attribute name
            unique_values: Dict of {value: [(turn, source, timestamp), ...]}
            current_turn: Current turn number
            threshold: Number of consecutive turns needed for resolution
            suppress_logging: If True, suppress [CONTRADICTION RESOLVED] logging (default: False)

        Returns:
            (is_resolved: bool, canonical_value: Any)
        """
        # Get last N mentions (up to 10 recent turns)
        recent_window = 10
        recent_mentions = []

        for value, occurrences in unique_values.items():
            for turn, source, timestamp in occurrences:
                if turn >= current_turn - recent_window:
                    recent_mentions.append((turn, value))

        # Sort by turn
        recent_mentions.sort(key=lambda x: x[0])

        if len(recent_mentions) < threshold:
            # Not enough data to determine resolution
            return (False, None)

        # STRATEGY 1: Check for consecutive consistent turns
        # Look at the last N turns and see if same value was mentioned
        last_n_values = [value for turn, value in recent_mentions[-threshold:]]

        if len(set(last_n_values)) == 1:
            # All last N mentions are the same value - RESOLVED
            canonical_value = last_n_values[0]
            if not suppress_logging:
                print(f"{etag('CONTRADICTION RESOLVED')} {self.canonical_name}.{attr} = {canonical_value} (consistent for {threshold} turns) [RELEVANT]")

            # Track resolution
            self.contradiction_resolution[attr] = {
                "resolved": True,
                "canonical_value": canonical_value,
                "resolved_at_turn": current_turn,
                "consecutive_consistent_turns": threshold
            }

            return (True, canonical_value)

        # STRATEGY 2: Check for dominant value (3x more mentions than alternatives)
        value_counts = {}
        for turn, value in recent_mentions:
            if value not in value_counts:
                value_counts[value] = 0
            value_counts[value] += 1

        if len(value_counts) >= 2:
            sorted_counts = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
            dominant_value, dominant_count = sorted_counts[0]
            second_value, second_count = sorted_counts[1]

            # If dominant value mentioned 3x more, treat as canonical
            if dominant_count >= second_count * 3 and dominant_count >= threshold:
                if not suppress_logging:
                    print(f"{etag('CONTRADICTION RESOLVED')} {self.canonical_name}.{attr} = {dominant_value} (dominant: {dominant_count}x vs {second_count}x) [RELEVANT]")

                # Track resolution
                self.contradiction_resolution[attr] = {
                    "resolved": True,
                    "canonical_value": dominant_value,
                    "resolved_at_turn": current_turn,
                    "confidence_ratio": dominant_count / second_count
                }

                return (True, dominant_value)

        # Not resolved
        return (False, None)

    def is_contradiction_resolved(self, attr: str) -> bool:
        """
        Check if a contradiction for an attribute has been marked as resolved.

        Args:
            attr: Attribute name

        Returns:
            True if contradiction is resolved
        """
        if attr in self.contradiction_resolution:
            return self.contradiction_resolution[attr].get("resolved", False)
        return False

    def get_canonical_value(self, attr: str) -> Optional[Any]:
        """
        Get the canonical (resolved) value for an attribute with contradictions.

        Args:
            attr: Attribute name

        Returns:
            Canonical value if resolved, None otherwise
        """
        if attr in self.contradiction_resolution and self.contradiction_resolution[attr].get("resolved"):
            return self.contradiction_resolution[attr].get("canonical_value")
        return None

    def _determine_contradiction_severity(self, attribute: str, unique_values: Dict) -> str:
        """
        Determine how severe a contradiction is.

        Transient: Goals, intentions, moods that naturally change (NOT contradictions)
        Accumulative: Attributes that naturally have multiple values (NOT contradictions)
        High severity: Physical attributes (eye_color, name)
        Moderate: Preferences that should be stable (favorite_X)
        Low: Other attributes

        Returns "transient" for attributes that naturally evolve over time -
        these should NOT be treated as contradictions.
        
        Returns "accumulative" for attributes that can legitimately hold multiple values -
        these are collections, not conflicts.
        """
        # ACCUMULATIVE attributes naturally have multiple values - NOT contradictions
        # These are collections, sets, or aspects that coexist rather than replace each other
        accumulative_attrs = [
            # Collections and sets
            "symbol_set", "symbols", "motif", "motifs",
            "interest", "interests", "hobby", "hobbies",
            "skill", "skills", "ability", "abilities",
            "trait", "traits", "characteristic", "characteristics",
            # Multiple valid aspects
            "self_perception", "identity", "aspect", "aspects",
            "role", "roles", "facet", "facets",
            # Mythological/shapeshifter attributes (multiple forms are valid)
            "species", "form", "forms", "shape", "shapes",
            "appearance", "manifestation",
            # Creative/artistic outputs
            "creation", "creations", "work", "works",
            "project", "projects", "song", "songs",
            # Relationship types (can have multiple relationships)
            "friend", "friends", "companion", "companions",
            # Tags and categories
            "tag", "tags", "category", "categories",
            "type", "types", "label", "labels",
            # Things mentioned/referenced (naturally accumulate)
            "mentioned", "reference", "references", "mentioned_topic",
            # Commitments and goals (can have multiple)
            "commitment", "commitments", "promise", "promises",
            # Capabilities and features
            "capability", "capabilities", "feature", "features",
            # Receives/gives (accumulative over time)
            "receives", "gives", "provides",
        ]
        
        # TRANSIENT attributes change naturally over time - NOT contradictions
        # Goals evolve, moods shift, intentions change - this is normal behavior
        transient_attrs = [
            # Core evolving states
            "goal", "planned_action", "goal_progression",
            "current_mood", "current_activity", "status",
            "intention", "desire", "want", "feeling",
            "working_on", "thinking_about", "focus",
            # Personal evolution
            "aspiration", "approach", "opinion", "option",
            "need", "hope", "plan", "idea", "thought",
            "concern", "worry", "excitement", "interest",
            "preference", "mood", "state", "activity",
            "task", "project", "priority", "decision",
            # Communication and behavior (these shift with context)
            "communication_style", "style", "tone", "manner",
            "behavior", "response", "reaction", "request",
            # Experience and knowledge (accumulates, doesn't contradict)
            "experience", "memory", "knowledge", "understanding",
            "learning", "discovery", "realization", "insight",
            # Relationship dynamics (evolve naturally)
            "relationship", "connection", "dynamic", "interaction",
            "role", "position", "stance", "attitude",
            # Emotional/mental states
            "emotion", "sentiment", "disposition", "mindset",
            "perspective", "view", "belief", "assumption",
            # Actions and processes
            "action", "doing", "trying", "attempting",
            "process", "progress", "development", "growth",
            # Context-dependent attributes
            "context", "situation", "circumstance", "condition",
            "location", "whereabouts", "presence",
            # Time references (change constantly)
            "duration", "time", "when", "timing", "timeframe",
        ]

        high_severity_attrs = ["eye_color", "name", "age", "gender"]  # species removed - it's accumulative for shapeshifters
        moderate_severity_attrs = ["favorite", "core_preference", "occupation", "home"]

        # Check for accumulative attributes first (these naturally have multiple values)
        attr_lower = attribute.lower()
        if any(accum in attr_lower for accum in accumulative_attrs):
            return "accumulative"
        
        # Check for transient attributes (exact match or contains)
        if any(trans in attr_lower for trans in transient_attrs):
            return "transient"

        if attribute in high_severity_attrs:
            return "high"
        elif any(mod in attribute for mod in moderate_severity_attrs):
            return "moderate"
        else:
            return "low"

    def prune_old_attribute_history(self, max_age_days: int = 30) -> int:
        """
        Remove attribute history entries older than max_age_days.
        This prevents contradiction explosion from accumulating stale data.

        Args:
            max_age_days: Maximum age of history entries to keep (default: 30 days)

        Returns:
            Number of entries pruned
        """
        cutoff = datetime.now()
        pruned_count = 0

        for attr, history in list(self.attributes.items()):
            new_history = []
            for value, turn, source, timestamp in history:
                try:
                    entry_time = datetime.fromisoformat(timestamp) if timestamp else None
                    if entry_time:
                        age_days = (cutoff - entry_time).days
                        if age_days <= max_age_days:
                            new_history.append((value, turn, source, timestamp))
                        else:
                            pruned_count += 1
                    else:
                        # Keep entries without timestamps (legacy data)
                        new_history.append((value, turn, source, timestamp))
                except (ValueError, TypeError):
                    # Keep entries with invalid timestamps
                    new_history.append((value, turn, source, timestamp))

            if new_history:
                self.attributes[attr] = new_history
            else:
                # Remove attribute entirely if all history pruned
                del self.attributes[attr]
                # Also clean up any resolved contradiction tracking
                if attr in self.contradiction_resolution:
                    del self.contradiction_resolution[attr]

        return pruned_count

    def cluster_similar_values(self, attr: str, similarity_threshold: float = 0.6) -> Dict[str, List]:
        """
        Cluster similar attribute values to reduce contradiction noise.
        E.g., "fix the entity's memory" and "fix the entity's brain" → same goal cluster.

        Args:
            attr: Attribute name to cluster
            similarity_threshold: Jaccard similarity threshold for clustering (0-1)

        Returns:
            Dict mapping cluster representative → list of similar values
        """
        if attr not in self.attributes:
            return {}

        # Get unique values
        values = set()
        for value, _, _, _ in self.attributes[attr]:
            if isinstance(value, str):
                values.add(value.lower().strip())

        if len(values) <= 1:
            return {}

        # Simple word-based Jaccard similarity clustering
        def jaccard_similarity(s1: str, s2: str) -> float:
            words1 = set(s1.split())
            words2 = set(s2.split())
            if not words1 or not words2:
                return 0.0
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            return intersection / union if union > 0 else 0.0

        # Build clusters
        clusters = {}
        assigned = set()

        for val in sorted(values, key=len, reverse=True):  # Longer values first as representatives
            if val in assigned:
                continue

            cluster = [val]
            assigned.add(val)

            for other_val in values:
                if other_val in assigned:
                    continue
                if jaccard_similarity(val, other_val) >= similarity_threshold:
                    cluster.append(other_val)
                    assigned.add(other_val)

            if len(cluster) > 1:
                clusters[val] = cluster

        return clusters

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entity to dict for JSON storage."""
        return {
            "canonical_name": self.canonical_name,
            "entity_type": self.entity_type,
            "aliases": list(self.aliases),
            "attributes": {
                attr: [(val, turn, src, ts) for val, turn, src, ts in history]
                for attr, history in self.attributes.items()
            },
            "contradiction_resolution": self.contradiction_resolution,  # NEW
            "relationships": self.relationships,
            "first_mentioned": self.first_mentioned,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "importance_score": self.importance_score
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        """Deserialize entity from dict."""
        entity = cls(data["canonical_name"], data.get("entity_type", "unknown"))
        entity.aliases = set(data.get("aliases", [entity.canonical_name]))

        # Restore attribute history
        for attr, history in data.get("attributes", {}).items():
            entity.attributes[attr] = [(val, turn, src, ts) for val, turn, src, ts in history]

        # Restore contradiction resolution tracking
        entity.contradiction_resolution = data.get("contradiction_resolution", {})

        entity.relationships = data.get("relationships", [])
        entity.first_mentioned = data.get("first_mentioned", 0)
        entity.last_accessed = data.get("last_accessed", 0)
        entity.access_count = data.get("access_count", 0)
        entity.importance_score = data.get("importance_score", 0.0)

        return entity

    # Dict-like interface methods for compatibility
    def items(self):
        """Allow dict-like iteration."""
        return self.to_dict().items()

    def keys(self):
        """Allow dict-like key access."""
        return self.to_dict().keys()

    def values(self):
        """Allow dict-like value access."""
        return self.to_dict().values()

    def __getitem__(self, key):
        """Allow dict-like item access (e.g., entity['canonical_name'])."""
        return self.to_dict()[key]

    def get(self, key, default=None):
        """Allow dict-like get method."""
        return self.to_dict().get(key, default)


class Relationship:
    """
    Represents a relationship between two entities.
    Examples: "the user owns [dog]", "the entity lives_in Portland"
    """

    def __init__(self, entity1: str, relation_type: str, entity2: str, turn: int, source: str = "user"):
        self.entity1 = entity1  # Canonical name of first entity
        self.relation_type = relation_type  # "owns", "lives_in", "works_with", etc.
        self.entity2 = entity2  # Canonical name of second entity
        self.turn = turn  # When this relationship was stated
        self.source = source  # Who stated this
        self.timestamp = datetime.now().isoformat()
        self.strength: float = 1.0  # How confident we are in this relationship

    def get_id(self) -> str:
        """Generate unique ID for this relationship."""
        return f"{self.entity1}::{self.relation_type}::{self.entity2}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize relationship to dict."""
        return {
            "entity1": self.entity1,
            "relation_type": self.relation_type,
            "entity2": self.entity2,
            "turn": self.turn,
            "source": self.source,
            "timestamp": self.timestamp,
            "strength": self.strength
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        """Deserialize relationship from dict."""
        rel = cls(
            data["entity1"],
            data["relation_type"],
            data["entity2"],
            data.get("turn", 0),
            data.get("source", "user")
        )
        rel.timestamp = data.get("timestamp", datetime.now().isoformat())
        rel.strength = data.get("strength", 1.0)
        return rel


class EntityGraph:
    """
    Manages all entities and relationships.
    Performs entity resolution (matching mentions to canonical entities).
    """

    def __init__(self, file_path: str = None):
        if file_path is None:
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory", "entity_graph.json")
        self.file_path = file_path
        self.entities: Dict[str, Entity] = {}  # canonical_name -> Entity
        self.relationships: Dict[str, Relationship] = {}  # relationship_id -> Relationship

        # Resolution cache: mention -> canonical_name
        self.resolution_cache: Dict[str, str] = {}

        # Canonical name mapping: normalized_name -> canonical_name
        # Used to deduplicate entities (e.g., "[cat]", "dice", "[cat]'s" all map to "[cat]")
        self.canonical_mapping: Dict[str, str] = {}

        # Load from disk
        self._load_from_disk()

    def _normalize_name(self, name: str) -> str:
        """
        Normalize an entity name for deduplication.

        Removes punctuation (apostrophes, hyphens), lowercases, and strips whitespace.
        This ensures "[cat]", "dice", "[cat]'s" all map to the same normalized form.

        Args:
            name: Original entity name

        Returns:
            Normalized name (lowercase, no punctuation)
        """
        import string
        # Remove apostrophes and hyphens, lowercase, strip
        normalized = name.lower().strip()
        # Remove common punctuation but keep letters and spaces
        normalized = normalized.replace("'", "").replace("-", "").replace("'", "")
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        return normalized.strip()

    def _load_from_disk(self):
        """Load entity graph from JSON."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Load entities
                for canonical_name, entity_data in data.get("entities", {}).items():
                    self.entities[canonical_name] = Entity.from_dict(entity_data)
                    # Build canonical mapping
                    normalized = self._normalize_name(canonical_name)
                    self.canonical_mapping[normalized] = canonical_name

                # Load relationships
                for rel_id, rel_data in data.get("relationships", {}).items():
                    self.relationships[rel_id] = Relationship.from_dict(rel_data)

                print(f"{etag('ENTITY GRAPH')} Loaded {len(self.entities)} entities, {len(self.relationships)} relationships")
        except FileNotFoundError:
            print(f"{etag('ENTITY GRAPH')}  No existing graph found, starting fresh")
        except Exception as e:
            print(f"{etag('ENTITY GRAPH')} Error loading graph: {e}")

    def _save_to_disk(self):
        """Save entity graph to JSON."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        data = {
            "entities": {
                name: entity.to_dict()
                for name, entity in self.entities.items()
            },
            "relationships": {
                rel_id: rel.to_dict()
                for rel_id, rel in self.relationships.items()
            }
        }

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_entities(self):
        """Public method to save entity graph to disk."""
        self._save_to_disk()

    def _is_valid_entity_name(self, name: str) -> bool:
        """
        Check if a name is valid for entity creation.

        Rejects:
        - Empty or whitespace-only names
        - Names that are mostly symbols/glyphs (◈ⁿ, ⟡, ⊗, etc.)
        - Single non-letter characters
        - Names with no alphanumeric content

        Args:
            name: Potential entity name

        Returns:
            True if valid entity name, False if should be rejected
        """
        import re

        if not name or not name.strip():
            return False

        name = name.strip()

        # Reject single characters unless they're letters (like "K" for the entity)
        if len(name) == 1 and not name.isalpha():
            return False

        # Count alphanumeric characters
        alnum_count = sum(1 for c in name if c.isalnum())

        # Reject if no alphanumeric characters at all
        if alnum_count == 0:
            return False

        # Reject if less than 30% alphanumeric (catches things like "◈ⁿ" or "⟡³")
        if len(name) > 1 and alnum_count / len(name) < 0.3:
            return False

        # Reject known glyph patterns used in the wrapper notation
        glyph_patterns = [
            r'^[◈⟡⊗∅◊△▽○●□■◆◇★☆♦♠♣♥♡⚡⚙⚔⛤⛧☾☽✦✧✨]+[ⁿ⁰¹²³⁴⁵⁶⁷⁸⁹]*$',  # Symbol + superscript
            r'^[⊕⊖⊗⊘⊙⊚⊛⊜⊝]+$',  # Mathematical operators
            r'^[\u2600-\u26FF]+$',  # Miscellaneous symbols unicode block
        ]

        for pattern in glyph_patterns:
            if re.match(pattern, name):
                return False

        return True

    def _is_noise_entity(self, name: str) -> bool:
        """
        Check if entity name matches transient/noise patterns that shouldn't be tracked.

        These are mentions that appear in conversation but aren't worth creating
        persistent entities for (food items, days of week, appliances, abstract concepts).

        Args:
            name: Entity name to check

        Returns:
            True if this is a noise entity (should NOT be created), False otherwise
        """
        if not name:
            return True

        name_lower = name.lower().strip()

        # Direct match against noise patterns
        if name_lower in ENTITY_NOISE_PATTERNS:
            return True

        # Check if name is a multi-word phrase that contains a noise pattern as the main noun
        # e.g., "the oven", "my dinner", "tomorrow morning"
        words = name_lower.split()
        if len(words) >= 1:
            # Check last word (usually the noun in "the X", "my X" patterns)
            if words[-1] in ENTITY_NOISE_PATTERNS:
                return True
            # Check first significant word for standalone patterns
            if words[0] in ENTITY_NOISE_PATTERNS:
                return True

        # Very short generic names (2 chars or less, unless they're initials like "user")
        if len(name_lower) <= 2 and not name_lower.isalpha():
            return True

        # Generic single-word names that are too common to be meaningful entities
        generic_singles = {'it', 'he', 'she', 'they', 'we', 'you', 'me', 'us', 'them'}
        if name_lower in generic_singles:
            return True

        return False

    def _is_camera_derived_attribute(self, attribute: str) -> bool:
        """
        Check if an attribute is derived from camera/visual sensor data.

        These attributes shouldn't be stored on real entities like the user or the entity
        because they're transient scene observations, not permanent facts.

        Args:
            attribute: Attribute name to check

        Returns:
            True if this is a camera-derived attribute, False otherwise
        """
        if not attribute:
            return False

        attr_lower = attribute.lower().strip()

        # Direct match
        if attr_lower in CAMERA_ATTRIBUTE_PATTERNS:
            return True

        # Partial match for camera-related patterns
        camera_keywords = ['gaze', 'lighting', 'illumination', 'posture', 'facing', 'position']
        for keyword in camera_keywords:
            if keyword in attr_lower:
                return True

        return False

    def resolve_entity(self, mention: str, context: str = "") -> Optional[str]:
        """
        Resolve a mention to a canonical entity name.

        Args:
            mention: The text mentioning an entity ("my dog", "[dog]", "she")
            context: Surrounding text for disambiguation

        Returns:
            Canonical name if resolved, None otherwise
        """
        mention_lower = mention.lower().strip()

        # Check cache first
        if mention_lower in self.resolution_cache:
            return self.resolution_cache[mention_lower]

        # Check direct matches with aliases
        for canonical_name, entity in self.entities.items():
            if mention_lower in entity.aliases:
                self.resolution_cache[mention_lower] = canonical_name
                return canonical_name

        # Check partial matches (for phrases like "my dog" -> "[dog]" if [dog] is a dog)
        # This is simplified - could use LLM for better resolution
        for canonical_name, entity in self.entities.items():
            if entity.entity_type in mention_lower:
                self.resolution_cache[mention_lower] = canonical_name
                return canonical_name

        return None

    def get_or_create_entity(self, name: str, entity_type: str = "unknown", turn: int = 0) -> Optional[Entity]:
        """
        Get existing entity or create new one with deduplication.

        Uses normalized name matching to prevent duplicates (e.g., "[cat]" and "dice" are the same).
        Rejects invalid entity names (glyphs, symbols, single characters).

        Args:
            name: Entity name
            entity_type: Type of entity
            turn: Current turn index

        Returns:
            Entity instance, or None if name is invalid
        """
        # VALIDATION: Reject glyph/symbol names that aren't real entities
        if not self._is_valid_entity_name(name):
            return None

        # NOISE FILTERING: Reject transient/meaningless entities
        # Days of week, food items, appliances, abstract concepts, etc.
        if self._is_noise_entity(name):
            return None

        # STEP 1: Check canonical mapping for deduplicated match
        normalized = self._normalize_name(name)

        if normalized in self.canonical_mapping:
            # Entity already exists under canonical name
            canonical_name = self.canonical_mapping[normalized]
            entity = self.entities[canonical_name]
            entity.last_accessed = turn
            entity.access_count += 1
            return entity

        # STEP 2: Try existing resolve_entity logic (for aliases)
        canonical_name = self.resolve_entity(name)

        if canonical_name and canonical_name in self.entities:
            entity = self.entities[canonical_name]
            entity.last_accessed = turn
            entity.access_count += 1
            # Update canonical mapping
            self.canonical_mapping[normalized] = canonical_name
            return entity

        # STEP 3: Create new entity (use original name as canonical)
        entity = Entity(name, entity_type)
        entity.first_mentioned = turn
        entity.last_accessed = turn
        entity.access_count = 1

        self.entities[name] = entity
        self.canonical_mapping[normalized] = name  # Map normalized -> canonical

        print(f"{etag('ENTITY GRAPH')} Created new entity: {name} (type: {entity_type})")

        self._save_to_disk()
        return entity

    def add_relationship(self, entity1_name: str, relation_type: str, entity2_name: str, turn: int = 0, source: str = "user"):
        """
        Add a relationship between two entities.

        Args:
            entity1_name: First entity canonical name
            relation_type: Relationship type
            entity2_name: Second entity canonical name
            turn: Current turn index
            source: Who stated this relationship
        """
        rel = Relationship(entity1_name, relation_type, entity2_name, turn, source)
        rel_id = rel.get_id()

        self.relationships[rel_id] = rel

        # Update entity relationship lists
        if entity1_name in self.entities:
            self.entities[entity1_name].relationships.append(rel_id)
        if entity2_name in self.entities:
            self.entities[entity2_name].relationships.append(rel_id)

        print(f"{etag('ENTITY GRAPH')} Added relationship: {entity1_name} {relation_type} {entity2_name}")

        self._save_to_disk()

    def add_entity(self, name: str, entity_type: str = "unknown", turn: int = 0) -> Optional[Entity]:
        """
        Add a new entity (wrapper for get_or_create_entity for consistency).

        Args:
            name: Entity name
            entity_type: Type of entity
            turn: Current turn index

        Returns:
            Entity instance, or None if name is invalid (glyph/symbol)
        """
        return self.get_or_create_entity(name, entity_type, turn)

    def set_attribute(self, entity_name: str, attribute: str, value: Any, turn: int = 0, source: str = "user"):
        """
        Set an attribute on an entity.

        Args:
            entity_name: Canonical entity name
            attribute: Attribute name
            value: Attribute value
            turn: Current turn index
            source: Who stated this attribute
        """
        # CAMERA ATTRIBUTE FILTERING: Don't store camera-derived attributes on real entities
        # These are transient scene observations (gaze_direction, environment_lighting, etc.)
        if self._is_camera_derived_attribute(attribute):
            # Only allow camera attributes on visual_memory entities, not real people/things
            if entity_name.lower() in ('re', 'entity', 'reed') or not entity_name.startswith('visual_'):
                return  # Silently skip camera-derived attributes on real entities

        # CAMERA VALUE FILTERING: Skip camera-derived values like "human" for species on the user
        # when it's obviously just scene detection, not a meaningful fact
        if attribute.lower() == 'species' and source == 'system':
            value_lower = str(value).lower()
            if value_lower in ('human', 'person', 'adult', 'male', 'female'):
                # Skip obvious camera scene detections - not meaningful facts
                return

        if entity_name not in self.entities:
            # Create entity if it doesn't exist
            result = self.get_or_create_entity(entity_name, "unknown", turn)
            if result is None:
                return  # Entity was rejected by noise filter

        if entity_name not in self.entities:
            return  # Entity creation failed

        entity = self.entities[entity_name]
        entity.add_attribute(attribute, value, turn, source)
        self._save_to_disk()

    def record_visual_entity(
        self,
        description: str,
        emotional_valence: float = 0.0,
        entities_detected: Optional[List[str]] = None,
        turn: int = 0
    ) -> str:
        """
        Record a visual experience as an entity in the graph.

        Creates a visual_memory entity and connects it to the entity (witnessed),
        User (shared), and any detected entities (contains).

        This uses behavioral emotional valence, NOT neurochemical values.

        Args:
            description: Description of the visual (what the entity saw)
            emotional_valence: Emotional valence of the experience (-1.0 to 1.0)
            entities_detected: List of entities visible in the image
            turn: Current turn number

        Returns:
            Entity ID of the created visual memory
        """
        # Create unique ID for this visual memory
        visual_id = f"visual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create the visual memory entity
        visual_entity = self.get_or_create_entity(visual_id, "visual_memory", turn)

        # Set attributes
        visual_entity.add_attribute("description", description[:200], turn, "system")
        visual_entity.add_attribute("emotional_valence", emotional_valence, turn, "system")
        visual_entity.add_attribute("is_visual", True, turn, "system")

        # Track relationships
        # Entity witnessed this visual (use self.entity_name if set, else "entity")
        entity_name = getattr(self, 'entity_name', 'entity')
        self.add_relationship(entity_name, "witnessed", visual_id, turn, "system")

        # User shared this visual (use self.user_name if set, else "user")
        user_name = getattr(self, 'user_name', 'user')
        self.add_relationship(user_name, "shared", visual_id, turn, "system")

        # Connect detected entities
        if entities_detected:
            for entity_name in entities_detected:
                # Create entity if needed
                self.get_or_create_entity(entity_name, "unknown", turn)
                # Visual contains this entity
                self.add_relationship(visual_id, "contains", entity_name, turn, "system")

        print(f"{etag('ENTITY GRAPH')} Recorded visual memory: {visual_id}")
        print(f"{etag('ENTITY GRAPH')} Visual valence: {emotional_valence:.2f}, entities: {entities_detected}")

        self._save_to_disk()
        return visual_id

    def get_visual_memories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent visual memory entities.

        Args:
            limit: Maximum number of visual memories to return

        Returns:
            List of visual memory dicts with description, valence, relationships
        """
        visuals = []

        for name, entity in self.entities.items():
            if entity.entity_type == "visual_memory":
                # Get description from attributes
                desc = None
                valence = 0.0
                for attr_history in entity.attributes.get("description", []):
                    if attr_history:
                        desc = attr_history[0]  # value
                for attr_history in entity.attributes.get("emotional_valence", []):
                    if attr_history:
                        valence = attr_history[0]

                visuals.append({
                    'id': name,
                    'description': desc,
                    'emotional_valence': valence,
                    'first_mentioned': entity.first_mentioned,
                    'relationships': self.get_entity_relationships(name)
                })

        # Sort by recency (first_mentioned descending)
        visuals.sort(key=lambda x: x.get('first_mentioned', 0), reverse=True)

        return visuals[:limit]

    def get_entity_relationships(self, entity_name: str) -> List[Relationship]:
        """Get all relationships for an entity."""
        if entity_name not in self.entities:
            return []

        entity = self.entities[entity_name]
        return [self.relationships[rel_id] for rel_id in entity.relationships if rel_id in self.relationships]

    def get_all_contradictions(self, current_turn: int = 0, resolution_threshold: int = 3, entity_filter: Optional[Set[str]] = None, suppress_logging: bool = False) -> List[Dict[str, Any]]:
        """
        Get all ACTIVE (unresolved) contradictions across all entities.

        Args:
            current_turn: Current turn number for resolution tracking
            resolution_threshold: Number of consecutive consistent turns to mark as resolved (default: 3)
            entity_filter: Optional set of entity names to check (if None, checks ALL entities)
            suppress_logging: If True, suppress [CONTRADICTION RESOLVED] logging (default: False)

        Returns:
            List of active contradictions (excludes resolved ones)
        """
        all_contradictions = []

        # If filter provided, only check those entities
        entities_to_check = self.entities.values()
        if entity_filter is not None:
            entities_to_check = [e for e in self.entities.values() if e.canonical_name in entity_filter]
            if not suppress_logging:
                print(f"{etag('ENTITY FILTER')} Checking {len(entities_to_check)}/{len(self.entities)} entities for contradictions")

        for entity in entities_to_check:
            contradictions = entity.detect_contradictions(current_turn, resolution_threshold, suppress_logging=suppress_logging)
            all_contradictions.extend(contradictions)

        return all_contradictions

    def prune_old_contradictions(self, max_age_days: int = 30) -> Dict[str, int]:
        """
        Prune old attribute history across all entities to prevent contradiction explosion.

        Args:
            max_age_days: Maximum age of attribute history to keep (default: 30 days)

        Returns:
            Dict mapping entity name → number of entries pruned
        """
        pruned_by_entity = {}
        total_pruned = 0

        for entity_name, entity in self.entities.items():
            pruned = entity.prune_old_attribute_history(max_age_days)
            if pruned > 0:
                pruned_by_entity[entity_name] = pruned
                total_pruned += pruned

        if total_pruned > 0:
            print(f"{etag('ENTITY GRAPH')} Pruned {total_pruned} old attribute entries (>{max_age_days} days) from {len(pruned_by_entity)} entities")
            self._save_to_disk()

        return pruned_by_entity

    def get_contradiction_summary(self, current_turn: int = 0) -> Dict[str, Any]:
        """
        Get a summary of contradictions without returning the full list.
        More efficient for logging/monitoring.

        Returns:
            Dict with counts by severity and top entities with contradictions
        """
        all_contradictions = self.get_all_contradictions(current_turn, suppress_logging=True)

        summary = {
            "total": len(all_contradictions),
            "by_severity": {"high": 0, "moderate": 0, "low": 0},
            "by_entity": {},
            "top_contradicting_entities": []
        }

        for c in all_contradictions:
            severity = c.get("severity", "low")
            entity = c.get("entity", "unknown")
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            summary["by_entity"][entity] = summary["by_entity"].get(entity, 0) + 1

        # Top 5 entities with most contradictions
        sorted_entities = sorted(summary["by_entity"].items(), key=lambda x: x[1], reverse=True)
        summary["top_contradicting_entities"] = sorted_entities[:5]

        return summary

    def update_entity_importance(self, entity_name: str, importance_score: float):
        """Update importance score for an entity (from ULTRAMAP pressure × recursion)."""
        if entity_name in self.entities:
            self.entities[entity_name].importance_score = importance_score
            self._save_to_disk()

    def get_entities_by_importance(self, top_n: int = 10) -> List[Entity]:
        """Get top N most important entities."""
        sorted_entities = sorted(
            self.entities.values(),
            key=lambda e: e.importance_score,
            reverse=True
        )
        return sorted_entities[:top_n]

    def get_related_entities(self, entity_name: str, max_distance: int = 2) -> Set[str]:
        """
        Get entities related to given entity within max_distance hops.

        Args:
            entity_name: Starting entity
            max_distance: Maximum relationship hops (1 = direct connections only)

        Returns:
            Set of related entity canonical names
        """
        if entity_name not in self.entities:
            return set()

        related = set()
        current_level = {entity_name}

        for _ in range(max_distance):
            next_level = set()

            for ent_name in current_level:
                relationships = self.get_entity_relationships(ent_name)

                for rel in relationships:
                    # Add both ends of relationship
                    next_level.add(rel.entity1)
                    next_level.add(rel.entity2)

            related.update(next_level)
            current_level = next_level - related

        # Remove the starting entity itself
        related.discard(entity_name)

        return related

    def get_entity_desires(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get all desires/goals for an entity with progression status.

        Returns desires, goals, fears, and aspirations with their progression.

        Args:
            entity_name: Entity canonical name

        Returns:
            List of desire dictionaries with type, value, progression, etc.
        """
        if entity_name not in self.entities:
            return []

        entity = self.entities[entity_name]
        desires = []

        # Collect desire-related attributes
        for attr_name in ["desire", "goal", "fear", "aspiration"]:
            history = entity.get_attribute_history(attr_name)
            for value, turn, source, timestamp in history:
                # Check for progression updates
                progression_attr = f"{attr_name}_progression"
                progression_history = entity.get_attribute_history(progression_attr)
                latest_progression = progression_history[-1][0] if progression_history else "unknown"

                desires.append({
                    "type": attr_name,
                    "value": value,
                    "turn": turn,
                    "source": source,
                    "progression": latest_progression,
                    "last_updated": timestamp
                })

        return desires

    def track_goal_progression(self, entity_name: str, goal_value: str, status: str, turn: int):
        """
        Track progression toward a goal.

        Args:
            entity_name: Entity with the goal
            goal_value: Description of the goal
            status: "advancing", "stuck", "abandoned", "completed"
            turn: Current turn
        """
        entity = self.get_or_create_entity(entity_name, turn=turn)
        entity.add_attribute(
            attribute="goal_progression",
            value=f"{goal_value}: {status}",
            turn=turn,
            source="inferred"
        )
        print(f"{etag('GOAL TRACKING')} {entity_name} goal '{goal_value}' → {status}")
        self._save_to_disk()

    def get_active_goals(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get currently active (non-completed, non-abandoned) goals for an entity.

        Args:
            entity_name: Entity canonical name

        Returns:
            List of active goal dictionaries
        """
        all_desires = self.get_entity_desires(entity_name)

        # Filter to active goals (not completed or abandoned)
        active = []
        for desire in all_desires:
            if desire["type"] in ["goal", "desire"]:
                progression = desire["progression"].lower()
                if "completed" not in progression and "abandoned" not in progression:
                    active.append(desire)

        return active

    def get_recent_relationships(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get relationships added in the last N hours.
        
        Useful for warmup briefings to show what changed.
        
        Args:
            hours: How many hours back to look
            
        Returns:
            List of recent relationship dicts with subject, predicate, object, timestamp
        """
        from datetime import datetime, timedelta
        
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = []
        
        for rel in self.relationships.values():
            # rel is a Relationship object, not a dict
            timestamp_str = getattr(rel, 'timestamp', '')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp > cutoff:
                        recent.append({
                            "subject": getattr(rel, 'entity1', ''),
                            "predicate": getattr(rel, 'relation_type', ''),
                            "object": getattr(rel, 'entity2', ''),
                            "timestamp": timestamp_str,
                            "source": getattr(rel, 'source', 'unknown')
                        })
                except:
                    pass
        
        # Sort by timestamp, most recent first
        recent.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return recent

    def check_ownership_conflict(self, entity: str, claimed_owner: str, identity_memory) -> Dict[str, Any]:
        """
        Check if a claimed ownership relationship conflicts with ground truth.

        Args:
            entity: Name of entity being claimed
            claimed_owner: Who is claiming to own it ("user" or "entity")
            identity_memory: IdentityMemory instance for ground truth checking

        Returns:
            Dict with:
            - "conflict": bool (True if there's a conflict)
            - "ground_truth_owner": str (actual owner according to identity layer)
            - "should_block": bool (True if relationship creation should be blocked)
            - "message": str (explanation)
        """
        result = {
            "conflict": False,
            "ground_truth_owner": None,
            "should_block": False,
            "message": ""
        }

        # Check identity layer for ground truth
        ownership_info = identity_memory.check_ownership(entity)

        ground_truth_owner = ownership_info.get("owner")
        confidence = ownership_info.get("confidence")

        # No existing ownership - safe to create
        if ground_truth_owner is None:
            result["message"] = f"No existing ownership for {entity} - safe to create"
            return result

        # Ownership exists - check for conflict
        if ground_truth_owner != claimed_owner:
            result["conflict"] = True
            result["ground_truth_owner"] = ground_truth_owner
            result["should_block"] = True
            result["message"] = (
                f"OWNERSHIP CONFLICT: {claimed_owner} claims to own {entity}, "
                f"but ground truth says {ground_truth_owner} owns {entity} "
                f"(confidence: {confidence})"
            )

            print(f"{etag('ENTITY GRAPH')} {result['message']}")
            return result

        # Same owner - reinforce existing relationship
        result["ground_truth_owner"] = ground_truth_owner
        result["message"] = f"Ownership confirmed: {claimed_owner} owns {entity}"
        return result

    def apply_user_correction(
        self,
        entity_name: str,
        attribute_pattern: str,
        wrong_value: str,
        correct_value: str,
        turn: int = 0
    ) -> Dict[str, Any]:
        """
        Apply a user correction to entity attributes.

        When the user corrects the entity about a fact (e.g., "No, those conversations
        were from 2024-2025, not 2020"), this method:
        1. Finds all attributes on the entity that contain the wrong value
        2. Marks them as corrected by adding the correct value from user source
        3. Logs the correction for debugging

        Args:
            entity_name: Entity to correct (e.g., "Zero", "ChatGPT conversations")
            attribute_pattern: Substring to match in attribute names (e.g., "year", "date")
            wrong_value: The incorrect value to find (e.g., "2020")
            correct_value: The correct value from user (e.g., "2024-2025")
            turn: Current turn number

        Returns:
            Dict with correction results:
            - "corrections_applied": int (how many attributes were corrected)
            - "entities_searched": list of entity names searched
            - "attributes_corrected": list of (entity, attribute, old_value, new_value)
        """
        result = {
            "corrections_applied": 0,
            "entities_searched": [],
            "attributes_corrected": []
        }

        # Normalize search terms
        entity_name_lower = entity_name.lower()
        attribute_pattern_lower = attribute_pattern.lower()
        wrong_value_lower = wrong_value.lower()

        # Search all entities for matching names
        matching_entities = []
        for ent_name, entity in self.entities.items():
            # Check if entity name matches (fuzzy)
            if entity_name_lower in ent_name.lower() or ent_name.lower() in entity_name_lower:
                matching_entities.append(entity)
                result["entities_searched"].append(ent_name)

        if not matching_entities:
            print(f"{etag('USER CORRECTION')} No entities found matching '{entity_name}'")
            return result

        # For each matching entity, find and correct attributes
        for entity in matching_entities:
            for attr_name, attr_history in entity.attributes.items():
                # Check if attribute name matches pattern
                if attribute_pattern_lower and attribute_pattern_lower not in attr_name.lower():
                    continue

                # Check if any value in history matches wrong value
                # Use word boundaries to prevent "phone" matching "headphones"
                for value, stored_turn, source, timestamp in attr_history:
                    value_str = str(value).lower()
                    if re.search(r'\b' + re.escape(wrong_value_lower) + r'\b', value_str):
                        # Found a value to correct!
                        print(f"{etag('USER CORRECTION')} Found: {entity.canonical_name}.{attr_name} = '{value}' (source: {source})")

                        # Add the corrected value from user
                        entity.add_attribute(
                            attr_name,
                            correct_value,
                            turn,
                            source="user"  # User corrections are authoritative
                        )

                        # Mark this contradiction as resolved in favor of user's value
                        entity.contradiction_resolution[attr_name] = {
                            "resolved": True,
                            "canonical_value": correct_value,
                            "resolved_at_turn": turn,
                            "consecutive_consistent_turns": 99,  # High value = definitely resolved
                            "correction_source": "user_explicit_correction",
                            "wrong_value": value,
                            "corrected_at": datetime.now().isoformat()
                        }

                        result["corrections_applied"] += 1
                        result["attributes_corrected"].append({
                            "entity": entity.canonical_name,
                            "attribute": attr_name,
                            "old_value": value,
                            "new_value": correct_value
                        })

                        print(f"{etag('USER CORRECTION')} Applied: {entity.canonical_name}.{attr_name} = '{correct_value}' (user correction)")

        if result["corrections_applied"] > 0:
            self._save_to_disk()
            print(f"{etag('USER CORRECTION')} Total: {result['corrections_applied']} corrections applied")
        else:
            print(f"{etag('USER CORRECTION')} No matching attributes found with value '{wrong_value}'")

        return result

    def find_attributes_with_value(
        self,
        value_pattern: str,
        entity_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all entity attributes containing a specific value pattern.

        Uses word boundary matching to prevent 'phone' matching 'headphones'.

        Args:
            value_pattern: Word/phrase to search for in attribute values
            entity_filter: Optional entity name filter

        Returns:
            List of dicts with entity, attribute, value, source, turn
        """
        results = []
        value_pattern_lower = value_pattern.lower()
        # Word boundary regex prevents substring false positives
        word_re = re.compile(r'\b' + re.escape(value_pattern_lower) + r'\b', re.IGNORECASE)

        for ent_name, entity in self.entities.items():
            if entity_filter and entity_filter.lower() not in ent_name.lower():
                continue

            for attr_name, attr_history in entity.attributes.items():
                for value, turn, source, timestamp in attr_history:
                    if word_re.search(str(value)):
                        results.append({
                            "entity": ent_name,
                            "attribute": attr_name,
                            "value": value,
                            "source": source,
                            "turn": turn,
                            "timestamp": timestamp
                        })

        return results

    def get_all_corrections(self) -> List[Dict[str, Any]]:
        """
        Get all user corrections that have been applied.

        Returns a list of corrections with:
        - entity: Entity name
        - attribute: Attribute that was corrected
        - wrong_value: The incorrect value that was corrected
        - correct_value: The correct value from user
        - corrected_at: When the correction was applied

        This is used by other systems (memory retrieval, memory layers, identity)
        to filter out or deprioritize facts containing wrong values.
        """
        corrections = []

        for entity in self.entities.values():
            for attr, resolution in entity.contradiction_resolution.items():
                # Only include user corrections (not auto-resolved contradictions)
                if resolution.get("correction_source") == "user_explicit_correction":
                    corrections.append({
                        "entity": entity.canonical_name,
                        "attribute": attr,
                        "wrong_value": resolution.get("wrong_value", ""),
                        "correct_value": resolution.get("canonical_value", ""),
                        "corrected_at": resolution.get("corrected_at", ""),
                        "resolved_at_turn": resolution.get("resolved_at_turn", 0)
                    })

        return corrections

    def check_value_was_corrected(self, value: str) -> Optional[Dict[str, Any]]:
        """
        Check if a specific value has been corrected by the user.

        Args:
            value: The value to check (e.g., "2020")

        Returns:
            Correction info if found, None otherwise
        """
        value_lower = value.lower().strip()

        for correction in self.get_all_corrections():
            wrong_value = str(correction.get("wrong_value", "")).lower().strip()
            if wrong_value and wrong_value in value_lower:
                return correction

        return None
