# engines/momentum_engine.py
import re
from typing import Dict, List, Optional, Set


class MomentumEngine:
    """
    Tracks cognitive momentum based on:
    1. Unresolved conversational threads (unanswered questions)
    2. Escalating emotional states (emotions growing turn-over-turn)
    3. Motif recurrence (same entities appearing consecutively)

    Produces a momentum score (0.0-1.0) that influences memory, emotion, and context.
    """

    def __init__(self):
        self.unresolved_questions: List[Dict] = []  # {"question": str, "turn": int, "entity": str}
        self.emotion_history: List[Dict[str, float]] = []  # Recent emotion intensities
        self.recent_motifs: List[Set[str]] = []  # Motifs from recent turns
        self.turn_counter = 0
        self.max_history = 5  # Track last 5 turns for momentum

    def _detect_questions_from_kay(self, kay_response: str) -> List[str]:
        """Extract questions Kay asked that need answers."""
        questions = []

        # Direct question marks
        sentences = re.split(r'[.!]', kay_response)
        for sent in sentences:
            if '?' in sent:
                questions.append(sent.strip())

        # Indirect questions/prompts (e.g., "Tell me about...", "What do you think...")
        indirect_patterns = [
            r"tell me (about|more)",
            r"what (do you|did you)",
            r"how (do you|did you)",
            r"why (do you|did you)",
            r"can you (tell|explain|describe)",
        ]
        for pattern in indirect_patterns:
            if re.search(pattern, kay_response.lower()):
                match = re.search(pattern + r"[^.!?]*", kay_response.lower())
                if match:
                    questions.append(match.group(0))

        return questions

    def _check_if_answered(self, question: str, user_input: str) -> bool:
        """Heuristic: check if user input addresses the question."""
        # Extract key words from question
        question_words = set(re.findall(r'\b\w{4,}\b', question.lower()))
        user_words = set(re.findall(r'\b\w{4,}\b', user_input.lower()))

        # If significant overlap, consider it answered
        overlap = len(question_words & user_words)

        # Also check for direct response indicators
        response_indicators = ['yes', 'no', 'because', 'well', 'actually', 'basically']
        has_indicator = any(ind in user_input.lower() for ind in response_indicators)

        return overlap >= 2 or has_indicator

    def _calculate_thread_momentum(self) -> float:
        """Score based on unresolved threads (0.0-1.0)."""
        if not self.unresolved_questions:
            return 0.0

        # Weight by recency
        total_weight = 0.0
        for q in self.unresolved_questions:
            age = self.turn_counter - q['turn']
            recency_weight = max(0.0, 1.0 - (age / 10.0))  # Decay over 10 turns
            total_weight += recency_weight

        # Normalize to 0-1 (cap at 3 unresolved questions)
        return min(1.0, total_weight / 3.0)

    def _calculate_emotion_momentum(self, current_emotions: Dict[str, Dict]) -> float:
        """Score based on escalating emotions (0.0-1.0)."""
        if len(self.emotion_history) < 2:
            return 0.0

        escalation_score = 0.0
        current_intensities = {k: v.get('intensity', 0) for k, v in current_emotions.items()}

        # Compare current emotions with previous turn
        prev_emotions = self.emotion_history[-1] if self.emotion_history else {}

        for emotion, intensity in current_intensities.items():
            prev_intensity = prev_emotions.get(emotion, 0.0)
            if intensity > prev_intensity:
                # Emotion is escalating
                escalation_score += (intensity - prev_intensity)

        # Check for sustained high emotions (intensity > 0.6 for 2+ turns)
        sustained_emotions = 0
        for emotion, intensity in current_intensities.items():
            if intensity > 0.6:
                # Check if it was also high last turn
                if prev_emotions.get(emotion, 0) > 0.6:
                    sustained_emotions += 1

        escalation_score += sustained_emotions * 0.3

        return min(1.0, escalation_score)

    def _calculate_motif_momentum(self, current_motifs: List[Dict]) -> float:
        """Score based on recurring motifs in consecutive turns (0.0-1.0)."""
        if not current_motifs or not self.recent_motifs:
            return 0.0

        # Extract current motif entities
        current_entities = {m['entity'] for m in current_motifs if m.get('weight', 0) > 0.2}

        if not current_entities:
            return 0.0

        # Check overlap with recent turns
        recurrence_score = 0.0
        for i, past_motifs in enumerate(reversed(self.recent_motifs[-3:])):  # Last 3 turns
            overlap = len(current_entities & past_motifs)
            if overlap > 0:
                # Weight by recency (more recent = higher weight)
                recency_weight = 1.0 - (i * 0.25)
                recurrence_score += overlap * recency_weight

        # Normalize (cap at 5 recurring entities)
        return min(1.0, recurrence_score / 5.0)

    def update(self, agent_state, user_input: str, kay_response: Optional[str] = None):
        """
        Update momentum based on current turn.
        Call this AFTER response generation, during post-turn updates.
        """
        self.turn_counter += 1

        # --- 1. Update unresolved threads ---
        if kay_response:
            # Add new questions from Kay's response
            new_questions = self._detect_questions_from_kay(kay_response)
            for q in new_questions:
                # Extract entity if present
                entity = None
                words = re.findall(r'\b[A-Z][a-z]+\b', q)
                if words:
                    entity = words[0].lower()

                self.unresolved_questions.append({
                    'question': q,
                    'turn': self.turn_counter,
                    'entity': entity
                })

        # Check if user answered any pending questions
        answered_indices = []
        for i, q_data in enumerate(self.unresolved_questions):
            if self._check_if_answered(q_data['question'], user_input):
                answered_indices.append(i)

        # Remove answered questions (reverse order to maintain indices)
        for i in reversed(answered_indices):
            self.unresolved_questions.pop(i)

        # Prune old questions (>10 turns)
        self.unresolved_questions = [
            q for q in self.unresolved_questions
            if self.turn_counter - q['turn'] < 10
        ]

        # --- 2. Update emotion history ---
        current_emotions = agent_state.emotional_cocktail or {}
        current_intensities = {k: v.get('intensity', 0) for k, v in current_emotions.items()}
        self.emotion_history.append(current_intensities)

        # Keep only recent history
        if len(self.emotion_history) > self.max_history:
            self.emotion_history.pop(0)

        # --- 3. Update motif recurrence ---
        current_motifs = agent_state.meta.get('motifs', [])
        current_entities = {m['entity'] for m in current_motifs if m.get('weight', 0) > 0.2}
        self.recent_motifs.append(current_entities)

        if len(self.recent_motifs) > self.max_history:
            self.recent_motifs.pop(0)

        # --- 4. Calculate combined momentum ---
        thread_momentum = self._calculate_thread_momentum()
        emotion_momentum = self._calculate_emotion_momentum(current_emotions)
        motif_momentum = self._calculate_motif_momentum(current_motifs)

        # Weighted combination
        total_momentum = (
            thread_momentum * 0.4 +
            emotion_momentum * 0.35 +
            motif_momentum * 0.25
        )

        # Store in agent state
        agent_state.momentum = max(0.0, min(1.0, total_momentum))

        # Store detailed breakdown for debugging
        agent_state.momentum_breakdown = {
            'total': agent_state.momentum,
            'threads': round(thread_momentum, 3),
            'emotions': round(emotion_momentum, 3),
            'motifs': round(motif_momentum, 3),
            'unresolved_count': len(self.unresolved_questions)
        }

    def get_high_momentum_motifs(self) -> List[str]:
        """Return motifs that are part of unresolved threads."""
        motifs = []
        for q in self.unresolved_questions:
            if q.get('entity'):
                motifs.append(q['entity'])
        return list(set(motifs))

    def get_high_momentum_emotions(self) -> List[str]:
        """Return emotions that are escalating."""
        if len(self.emotion_history) < 2:
            return []

        current = self.emotion_history[-1]
        previous = self.emotion_history[-2]

        escalating = []
        for emotion, intensity in current.items():
            prev_intensity = previous.get(emotion, 0.0)
            if intensity > prev_intensity and intensity > 0.5:
                escalating.append(emotion)

        return escalating

    def get_momentum_context_notes(self, agent_state) -> List[str]:
        """Generate meta-notes for high momentum situations (>0.7)."""
        momentum = agent_state.momentum
        if momentum < 0.7:
            return []

        notes = []

        # Thread-based notes
        if self.unresolved_questions:
            recent_q = self.unresolved_questions[-1]
            entity = recent_q.get('entity', 'something')
            notes.append(f"Kay is still waiting to hear more about {entity}")

        # Emotion-based notes
        escalating_emotions = self.get_high_momentum_emotions()
        if escalating_emotions:
            emotion_str = ', '.join(escalating_emotions)
            notes.append(f"Kay's {emotion_str} is intensifying")

        # Motif-based notes
        if self.recent_motifs and len(self.recent_motifs) >= 2:
            recent = self.recent_motifs[-1]
            prev = self.recent_motifs[-2]
            recurring = recent & prev
            if recurring:
                entity = list(recurring)[0] if recurring else None
                if entity:
                    notes.append(f"Kay keeps thinking about {entity}")

        return notes
