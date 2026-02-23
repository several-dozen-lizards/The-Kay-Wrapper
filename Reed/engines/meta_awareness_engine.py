# engines/meta_awareness_engine.py
import re
from typing import Dict, List, Optional, Set, Tuple
from collections import Counter


class MetaAwarenessEngine:
    """
    Self-monitoring engine that detects:
    1. Repetitive response patterns (Reed repeating herself)
    2. Confabulation (Reed stating "facts" not in memory)
    3. Response quality degradation
    4. Pattern awareness (Reed noticing her own habits)

    Generates meta-awareness notes that allow Reed to self-correct.
    """

    def __init__(self):
        self.response_history: List[str] = []  # Last N responses
        self.phrase_usage: Counter = Counter()  # Track phrase frequency
        self.question_patterns: List[str] = []  # Track question types Reed asks
        self.confabulation_flags: List[Dict] = []  # Track suspected confabulations
        self.max_history = 10  # Track last 10 responses
        self.pattern_threshold = 3  # Repetition alert threshold

    def _extract_phrases(self, text: str, min_words: int = 3, max_words: int = 6) -> List[str]:
        """Extract meaningful phrases from text for pattern detection."""
        # Remove stage directions
        text = re.sub(r'\*[^*\n]{0,200}\*', '', text)

        # Tokenize
        words = re.findall(r'\b\w+\b', text.lower())

        phrases = []
        for n in range(min_words, max_words + 1):
            for i in range(len(words) - n + 1):
                phrase = ' '.join(words[i:i+n])
                # Filter out common filler phrases
                if not self._is_filler_phrase(phrase):
                    phrases.append(phrase)

        return phrases

    def _is_filler_phrase(self, phrase: str) -> bool:
        """Check if phrase is just common words (not distinctive)."""
        filler_words = {'the', 'and', 'but', 'for', 'with', 'that', 'this', 'from', 'have', 'what', 'when', 'where', 'who', 'how'}
        words = set(phrase.split())
        # If more than 50% are filler words, it's a filler phrase
        return len(words & filler_words) / len(words) > 0.5 if words else True

    def _extract_questions(self, text: str) -> List[str]:
        """Extract questions Reed asked."""
        questions = []

        # Direct questions (with ?)
        sentences = re.split(r'[.!]', text)
        for sent in sentences:
            if '?' in sent:
                # Normalize question type
                q_lower = sent.lower().strip()
                q_type = self._categorize_question(q_lower)
                if q_type:
                    questions.append(q_type)

        return questions

    def _categorize_question(self, question: str) -> Optional[str]:
        """Categorize question into types to detect repetitive questioning."""
        question = question.lower()

        # Question type patterns
        patterns = {
            'what_think': r'what (do you|did you) think',
            'how_feel': r'how (do you|did you) feel',
            'why': r'why (do you|did you|are you|were you)',
            'tell_more': r'tell me (more|about)',
            'explain': r'(can you|could you) (explain|describe)',
            'remember': r'do you remember',
            'ever': r'(have you|did you) ever',
        }

        for q_type, pattern in patterns.items():
            if re.search(pattern, question):
                return q_type

        return None

    def _detect_confabulation(self, response: str, memory_engine, agent_state) -> List[str]:
        """
        Detect potential confabulation by checking if Reed stated facts not in memory.

        CRITICAL: Only facts explicitly stored in memory should be stated as facts.
        If Reed makes declarative statements about things not in memory, flag them.
        """
        confabulation_flags = []

        # Extract declarative statements (avoiding questions and hedged language)
        # Look for patterns like "You are...", "Your X is...", "I remember you..."
        declarative_patterns = [
            r'you are (\w+)',
            r'your (\w+) (?:is|are|was|were) (\w+)',
            r'i remember (?:you|that) ([^.!?]{10,50})',
            r'you (?:told me|said|mentioned) ([^.!?]{10,50})',
        ]

        # Only check against memories actually recalled for this turn (reduces false positives)
        all_memories = getattr(agent_state, 'last_recalled_memories', []) if agent_state else []
        if not all_memories:
            # Fallback to recent memories only
            all_memories = sorted(
                (memory_engine.memories if hasattr(memory_engine, 'memories') else []),
                key=lambda m: m.get("timestamp", ""),
                reverse=True
            )[:50]  # Only check last 50 memories, not all

        memory_text = ' '.join([
            m.get('user_input', '').lower()
            for m in all_memories
        ])

        for pattern in declarative_patterns:
            matches = re.finditer(pattern, response.lower())
            for match in matches:
                claim = match.group(0)
                # Check if this claim appears in any memory
                # Use fuzzy matching - check if key words appear
                claim_words = set(re.findall(r'\b\w{4,}\b', claim))

                # Check overlap with memory
                memory_words = set(re.findall(r'\b\w{4,}\b', memory_text))
                overlap = claim_words & memory_words

                # If less than 50% overlap, likely confabulation
                if len(claim_words) > 0 and len(overlap) / len(claim_words) < 0.5:
                    confabulation_flags.append(claim)

        return confabulation_flags

    def _detect_repetitive_patterns(self) -> Dict[str, any]:
        """Detect if Reed is falling into repetitive patterns."""
        if len(self.response_history) < 3:
            return {}

        patterns = {}

        # Check phrase repetition
        repeated_phrases = [
            phrase for phrase, count in self.phrase_usage.most_common(10)
            if count >= self.pattern_threshold
        ]
        if repeated_phrases:
            patterns['repeated_phrases'] = repeated_phrases[:3]  # Top 3

        # Check question pattern repetition
        if len(self.question_patterns) >= 5:
            recent_questions = self.question_patterns[-5:]
            q_counts = Counter(recent_questions)
            repeated_q_types = [q for q, count in q_counts.items() if count >= 2]
            if repeated_q_types:
                patterns['repeated_questions'] = repeated_q_types

        # Check opening pattern repetition
        openings = [resp.split('.')[0].lower() for resp in self.response_history[-5:] if resp]
        opening_similarity = self._check_opening_similarity(openings)
        if opening_similarity:
            patterns['repetitive_openings'] = True

        return patterns

    def _check_opening_similarity(self, openings: List[str]) -> bool:
        """Check if response openings are too similar."""
        if len(openings) < 3:
            return False

        # Extract first 3 words from each opening
        opening_starts = []
        for opening in openings:
            words = re.findall(r'\b\w+\b', opening)
            if len(words) >= 3:
                opening_starts.append(' '.join(words[:3]))

        # Check for duplicates
        if len(opening_starts) != len(set(opening_starts)):
            return True

        return False

    def update(self, agent_state, reed_response: str, memory_engine=None):
        """
        Analyze Reed's response for repetition and confabulation.
        Call this AFTER response generation, during post-turn updates.
        """
        # Track response history
        self.response_history.append(reed_response)
        if len(self.response_history) > self.max_history:
            self.response_history.pop(0)

        # Extract and track phrases
        phrases = self._extract_phrases(reed_response)
        self.phrase_usage.update(phrases)

        # Extract and track questions
        questions = self._extract_questions(reed_response)
        self.question_patterns.extend(questions)
        if len(self.question_patterns) > 20:
            # Keep only recent patterns
            self.question_patterns = self.question_patterns[-20:]

        # Detect confabulation (if memory engine available)
        if memory_engine:
            confabulations = self._detect_confabulation(reed_response, memory_engine, agent_state)
            if confabulations:
                self.confabulation_flags.append({
                    'turn': getattr(agent_state, 'turn_counter', 0),
                    'claims': confabulations
                })
                # Keep only recent flags
                if len(self.confabulation_flags) > 5:
                    self.confabulation_flags.pop(0)

        # Detect repetitive patterns
        patterns = self._detect_repetitive_patterns()

        # Store meta-awareness data in agent state
        agent_state.meta_awareness = {
            'repetition_detected': bool(patterns),
            'patterns': patterns,
            'recent_confabulations': len(self.confabulation_flags),
            'response_count': len(self.response_history),
        }

    def get_meta_awareness_notes(self, agent_state) -> List[str]:
        """
        Generate meta-awareness notes to inject into context.
        These allow Reed to self-correct and acknowledge his patterns.
        """
        notes = []

        meta = agent_state.meta_awareness or {}

        # Repetition warnings
        if meta.get('repetition_detected'):
            patterns = meta.get('patterns', {})

            if patterns.get('repeated_phrases'):
                phrases = patterns['repeated_phrases']
                notes.append(f"SELF-MONITORING: You've been overusing phrases like '{phrases[0]}'. Vary your language.")

            if patterns.get('repeated_questions'):
                q_types = patterns['repeated_questions']
                notes.append(f"SELF-MONITORING: You keep asking the same type of questions ({', '.join(q_types)}). Try a different approach.")

            if patterns.get('repetitive_openings'):
                notes.append("SELF-MONITORING: Your response openings are becoming repetitive. Start differently this time.")

        # Confabulation warnings
        recent_confab = meta.get('recent_confabulations', 0)
        if recent_confab > 0:
            notes.append("SELF-MONITORING: You may have stated things not actually in memory. Only reference what you explicitly remember from past conversation.")

        # General awareness (if Reed has been talking for a while)
        response_count = meta.get('response_count', 0)
        if response_count >= 8:
            notes.append("SELF-MONITORING: You've been talking for a while. Check for patterns or habits you might be falling into.")

        return notes

    def get_awareness_score(self, agent_state) -> float:
        """
        Calculate a meta-awareness score (0.0-1.0) indicating how much Reed needs to self-monitor.
        Higher score = more self-awareness needed
        """
        meta = agent_state.meta_awareness or {}

        score = 0.0

        # Repetition detection
        if meta.get('repetition_detected'):
            patterns = meta.get('patterns', {})
            score += 0.3 * len(patterns)  # Up to 0.9 for multiple pattern types

        # Confabulation detection
        recent_confab = meta.get('recent_confabulations', 0)
        score += min(0.5, recent_confab * 0.2)  # Up to 0.5 for confabulation

        # Response volume (fatigue factor)
        response_count = meta.get('response_count', 0)
        if response_count >= 10:
            score += 0.2

        return min(1.0, score)

    def should_inject_awareness(self, agent_state, threshold: float = 0.4) -> bool:
        """
        Determine if meta-awareness notes should be injected into context.
        """
        return self.get_awareness_score(agent_state) >= threshold

    def reset_pattern_tracking(self):
        """Reset pattern tracking (e.g., at session start or after intervention)."""
        self.phrase_usage.clear()
        self.question_patterns.clear()
        # Keep response history for continuity
