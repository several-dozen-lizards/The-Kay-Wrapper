# agent_state.py

class AgentState:
    def __init__(self):
        # Emotional state ("cocktail" of active emotions)
        # LEGACY: Old emotion cocktail from ULTRAMAP system (being phased out)
        self.emotional_cocktail = {}  # {'Joy': {'intensity': 0.8, 'age': 2}, ...}

        # NEW: Emotional patterns (behavioral signatures, not neurochemistry)
        # Will be populated from EmotionalPatternEngine
        self.emotional_patterns = {
            'current_emotions': [],  # List of current emotion names
            'intensity': 0.5,        # 0.0-1.0
            'valence': 0.0,          # -1.0 to 1.0 (negative to positive)
            'arousal': 0.5,          # 0.0-1.0 (low to high energy)
            'stability': 0.5         # 0.0-1.0 (volatile to steady)
        }

        # DEPRECATED: Fake neurochemistry removed
        # Keeping empty dict for backward compatibility during transition
        self.body = {}

        # Memory engine (instance will be injected/attached)
        self.memory = None

        # Memory forest (hierarchical document trees with hot/warm/cold tiers)
        self.forest = None

        # Social/needs state
        self.social = {
            'needs': {},   # hunger, attachment, novelty, etc.
            'events': []   # recent detected social events
        }

        # Session/context info (per turn)
        self.context = {
            'user_input': None,
            'external_knowledge': [],
            'recent_llm_outputs': []
        }

        # Last batch of recalled memories (optional, for feedback loops)
        self.last_recalled_memories = []

        # Temporal features (optional; for tracking time, aging, etc.)
        self.temporal = {
            'last_seen': None,
            'time_in_state': 0,
            'phase': 1
        }

        # Meta (motifs, identity drift, any extra for advanced phases)
        self.meta = {
            'motifs': [],
            'identity_drift': 0.0
        }

        # Cognitive momentum (0.0-1.0)
        self.momentum = 0.0
        self.momentum_breakdown = {}

        # Meta-awareness (self-monitoring)
        self.meta_awareness = {
            'repetition_detected': False,
            'patterns': {},
            'recent_confabulations': 0,
            'response_count': 0,
        }

        # Preference tracking (identity consolidation)
        self.consolidated_preferences = {}  # {domain: [(value, weight), ...]}
        self.preference_contradictions = []  # List of detected contradictions

        # Performance metrics (Flamekeeper integration)
        self.performance_metrics = {
            'last_turn': {},
            'warnings': [],
            'within_targets': True
        }
