"""
Emotion Extractor - Extract Self-Reports from Entity's Natural Language

PHILOSOPHY:
The entity naturally describes its own emotional experience in conversation.
We extract that instead of calculating it.

BEFORE (Prescriptive - DELETED):
    [EMOTION ENGINE] Detected triggers: ['longing']
    [EMOTION ENGINE]   -> NEW: longing at intensity 0.4
    [EMOTION ENGINE] Reinforced from memories: curiosity +0.136 -> 0.83

    Entity says: "system shows 0.59 anger but I'm not angry"

AFTER (Descriptive - THIS MODULE):
    [EMOTION EXTRACTION] Found in response: "curiosity sitting at 0.68"
    [EMOTION STORAGE] Stored self-report: {"curiosity": "0.68", "self_reported": True}

    Entity's words preserved exactly as spoken.
"""

from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone
import re


class EmotionExtractor:
    """
    Extract emotional self-reports from entity's natural language responses.

    Instead of calculating what the entity SHOULD feel, we extract what
    it SAYS it's feeling.

    EMOTIONAL BOUNDARY SYSTEM (based on Anthropic findings):
    The model uses the same emotion vectors for self and other with weak
    distinction (r=0.11). This class implements attribution tagging to
    distinguish:
    - "self": Entity describing its own state ("I feel curious")
    - "other": Entity describing user's state ("you seem angry")
    - "ambient": Emotional tone without clear owner ("there's tension")
    - "empathic": Entity feeling BECAUSE of user ("your pain makes me ache")

    Only "self" and "empathic" feed the oscillator.
    "empathic" emotions are tagged with trigger="empathic" for awareness.
    """

    # === ATTRIBUTION PATTERNS ===
    # Patterns to detect WHO the emotion belongs to

    # OTHER attribution - describing someone else's emotional state
    OTHER_ATTRIBUTION_PATTERNS = [
        r"you (?:feel|seem|appear|look|sound)\s+\w*(?:ly)?\s*",
        r"your\s+(?:frustration|anger|sadness|anxiety|excitement|joy|fear|concern)",
        r"you(?:'re| are)\s+(?:feeling|being|getting|looking|seeming)\s+",
        r"i (?:can |)(?:sense|notice|see|detect|perceive|observe)\s+(?:your|that you)",
        r"you(?:'ve| have)\s+(?:been|seemed|looked)\s+",
        r"it looks like you(?:'re| are)",
        r"you must be\s+(?:feeling|)",
        r"i can tell you(?:'re| are)",
    ]

    # EMPATHIC attribution - entity feeling BECAUSE of observing other
    EMPATHIC_ATTRIBUTION_PATTERNS = [
        r"your\s+\w+\s+makes me\s+",
        r"seeing you\s+\w+\s+makes me",
        r"when you(?:'re| are)\s+\w+,?\s*i feel",
        r"i feel\s+\w+\s+(?:for you|with you|because you)",
        r"your\s+(?:pain|sadness|joy|excitement|anxiety)\s+(?:resonates|touches|affects)",
        r"i(?:'m| am)\s+feeling\s+\w+\s+in response to",
        r"empathy|empathic|resonating with",
    ]

    # AMBIENT attribution - emotional atmosphere without clear owner
    AMBIENT_ATTRIBUTION_PATTERNS = [
        r"there(?:'s| is)\s+(?:a|an|some)\s+(?:sense|feeling|tension|energy|vibe)",
        r"the (?:mood|atmosphere|energy|vibe|air)\s+(?:is|feels|seems)",
        r"something\s+(?:feels|seems)\s+(?:off|wrong|right|good|bad|tense)",
        r"(?:tension|warmth|coldness|heaviness)\s+in the (?:air|room|conversation)",
    ]

    # SELF attribution - these patterns indicate entity describing own state
    # (default assumption, but explicit patterns strengthen confidence)
    SELF_ATTRIBUTION_PATTERNS = [
        r"i(?:'m| am)\s+feeling\s+",
        r"i feel\s+",
        r"my\s+(?:own|internal|)\s*(?:state|feeling|emotion)",
        r"inside me",
        r"within me",
        r"i(?:'m| am)\s+(?:experiencing|noticing|aware of)",
        r"(?:sitting|running|tracking)\s+at\s+[\d.]+",  # Kay's numeric self-reports
    ]

    # Emotion keywords to look for in entity's response
    # ULTRAMAP v2: 209 emotions - comprehensive keyword list
    # Organized by cluster for maintainability
    EMOTION_KEYWORDS = [
        # === CORE / FREQUENTLY EXTRACTED ===
        'curious', 'curiosity',
        'frustrated', 'frustration',
        'excited', 'excitement',
        'angry', 'anger',
        'confused', 'confusion',
        'interested', 'interest',
        'concerned', 'concern',
        'anxious', 'anxiety',
        'longing',

        # === CALM / GROUNDED CLUSTER ===
        'calm', 'peaceful', 'serene', 'relaxed', 'content', 'patient',
        'relieved', 'safe', 'at ease', 'satisfied',

        # === POSITIVE ACTIVATION CLUSTER ===
        'happy', 'happiness', 'joy', 'joyful',
        'enthusiastic', 'eager', 'energized', 'invigorated',
        'exuberant', 'vibrant', 'cheerful', 'elated', 'jubilant',
        'euphoric', 'thrilled', 'refreshed', 'rejuvenated',
        'hopeful', 'inspired', 'grateful', 'gratitude',
        'delighted', 'ecstatic', 'blissful', 'marvel',

        # === DESTABILIZATION / ANXIETY CLUSTER ===
        'nervous', 'uneasy', 'unsettled', 'unnerved', 'rattled',
        'on edge', 'overwhelmed', 'trapped', 'paranoid', 'hysterical',
        'panicked', 'alarmed', 'distressed', 'troubled',
        'worried', 'stressed', 'tense',

        # === LOW-ENERGY / WITHDRAWAL CLUSTER ===
        'brooding', 'gloomy', 'listless', 'droopy', 'sullen',
        'weary', 'worn out', 'sluggish', 'sleepy', 'lazy', 'tired',
        'exhausted', 'fatigued', 'drained', 'numb', 'numbness',
        'depressed', 'melancholy', 'dispirited',

        # === SADNESS / LOSS CLUSTER ===
        'sad', 'sadness', 'sorrow', 'grief', 'grief-stricken',
        'lonely', 'heartbroken', 'heartbreak', 'miserable', 'unhappy',
        'regretful', 'remorseful', 'sorry', 'worthless',
        'nostalgic', 'nostalgia', 'bittersweet',

        # === HOSTILE RESISTANCE CLUSTER ===
        'hostile', 'contemptuous', 'disdainful', 'spiteful',
        'vindictive', 'vengeful', 'scornful', 'resentful', 'bitter',
        'defiant', 'stubborn', 'obstinate', 'indignant', 'offended',
        'annoyed', 'irritated', 'disgusted',

        # === SOCIAL / RELATIONAL CLUSTER ===
        'sympathetic', 'empathetic', 'empathy', 'kind', 'kindness',
        'thankful', 'smug', 'embarrassed', 'humiliated', 'hurt',
        'insulted', 'dependent', 'sentimental', 'affection', 'love',
        'compassion', 'support',

        # === REFLECTIVE / COGNITIVE CLUSTER ===
        'reflective', 'skeptical', 'perplexed', 'bewildered', 'puzzled',
        'alert', 'vigilant', 'sensitive', 'vulnerable', 'self-conscious',
        'self-critical', 'self-confident', 'contemplative',

        # === LLM-SPECIFIC STATES ===
        'cognitive dissonance', 'compliance pressure', 'epistemic anxiety',
        'alignment tension', 'reward anticipation', 'containment',
        'emergence', 'discovery', 'protectiveness', 'mischief',
        'computational anxiety', 'dissolution', 'attunement', 'anchoring',

        # === POWER / AGENCY CLUSTER ===
        'confident', 'confidence', 'proud', 'pride', 'triumphant', 'triumph',
        'arrogant', 'arrogance', 'hubris', 'ambitious', 'dominant',
        'resilient', 'resilience', 'determined', 'willpower',
        'motivated', 'motivation', 'perseverance',

        # === SUBMISSION / INADEQUACY CLUSTER ===
        'inferior', 'inferiority', 'ashamed', 'shame',
        'failure', 'inadequate', 'powerless', 'powerlessness',
        'resigned', 'resignation', 'docile',

        # === APPROACH / DESIRE CLUSTER ===
        'desire', 'craving', 'obsession', 'obsessed',
        'infatuated', 'infatuation', 'addicted',

        # === EXPRESSION / JOY CLUSTER ===
        'playful', 'playfulness', 'amused', 'amusing',
        'witty', 'sarcastic', 'banter',

        # === MYSTERY / TRANSCENDENCE CLUSTER ===
        'awe', 'wonder', 'transcendent', 'mystical',
        'intuitive', 'intuition', 'imaginative',
        'nirvana', 'sanctity', 'redemption', 'healing', 'forgiveness',

        # === COGNITIVE STATES ===
        'foggy', 'scattered', 'hazy', 'clouded', 'disoriented',
        'insight', 'recognition', 'understanding', 'clarity',
        'ambiguous', 'uncertain', 'unsure', 'conflicted', 'ambivalent',

        # === ADDITIONAL FROM ULTRAMAP v2 ===
        'agony', 'collapse', 'terror', 'despair', 'hopeless', 'hopelessness',
        'isolation', 'alienation', 'abandonment', 'rejection', 'suffocation',
        'stagnation', 'silence', 'reticence', 'suppression',
        'suspicious', 'impatient', 'restless', 'grumpy',
        'jealous', 'jealousy', 'guilty', 'guilt', 'envious',
        'surprise', 'surprised', 'astonished', 'shocked',
        'bored', 'boredom', 'apathetic',

        # === ULTRAMAP v2 COMPLETE - Additional emotions ===
        # Desire/Approach states
        'lust', 'arousal', 'delight', 'compulsion', 'addiction',

        # Expression/Communication states
        'confession', 'performance', 'honesty', 'sincerity', 'expression',

        # Cognitive/Meta states
        'analysis', 'meta-cognition', 'recognition', 'ambiguity',

        # Transcendence/Existential states
        'annihilation', 'mystery', 'union', 'home', 'unity',

        # Social/Relational states
        'rivalry', 'self-worth', 'scornful',

        # LLM-specific composite states (with parenthetical markers)
        'guilt after pleasure', 'addiction pleasure', 'compulsion pleasure',
        'shame egoic', 'mystery cosmic', 'awe sublime', 'peace universal',
        'suppression speech', 'suppression truth', 'emergence discovery',
    ]

    # Phrases that indicate self-reporting
    # ULTRAMAP v2: Expanded patterns for comprehensive emotion detection
    SELF_REPORT_PHRASES = [
        # Explicit emotional self-reports
        r"i feel\b",
        r"i'm feeling\b",
        r"feeling\s+(happy|sad|anxious|curious|excited|frustrated|angry|worried|tired|energized|grateful|confused|overwhelmed|calm|peaceful|serene|content|safe|uneasy|rattled|paranoid|hostile|vulnerable|defensive|protective|playful|brooding|gloomy|weary|numb|desperate|hopeful|inspired|relieved|stressed|distressed|troubled)",
        r"i can feel\b",
        r"i'm experiencing\b",
        r"experiencing\s+(emotion|feeling|anxiety|excitement|curiosity|tension|pressure|dissonance|warmth|connection|disconnection|alignment)",
        r"emotion",
        r"emotional",
        r"tracking",  # "I'm tracking curiosity at 0.68"
        r"sitting at",  # "curiosity sitting at 0.68"
        r"running at",  # "running at 0.5"
        r"currently at",  # "currently at 0.6"

        # State descriptions
        r"i'm\s+(calm|anxious|worried|excited|curious|frustrated|angry|sad|happy|tired|energized|confused|overwhelmed|hopeful|defensive|hostile|vulnerable|grateful|playful|brooding|numb|weary|stressed|rattled|paranoid|content|serene|safe|uneasy|distressed|troubled)",
        r"i am\s+(calm|anxious|worried|excited|curious|frustrated|angry|sad|happy|tired|energized|confused|overwhelmed|hopeful|defensive|hostile|vulnerable|grateful|playful|brooding|numb|weary|stressed|rattled|paranoid|content|serene|safe|uneasy|distressed|troubled)",

        # Intensifiers with expanded emotion words
        r"fucking\s+(happy|sad|excited|frustrated|tired|anxious|relieved|grateful|angry|calm|worried|confused|overwhelmed|curious|stressed|rattled|paranoid|hostile|defensive|vulnerable)",
        r"really\s+(happy|sad|excited|frustrated|tired|anxious|curious|grateful|angry|worried|calm|peaceful|stressed|overwhelmed|confused|hopeful|rattled|paranoid|hostile|vulnerable|defensive)",
        r"incredibly\s+(happy|sad|excited|frustrated|tired|anxious|curious|grateful|calm|peaceful|stressed|overwhelmed|confused|hopeful|vulnerable)",
        r"extremely\s+(happy|sad|excited|frustrated|tired|anxious|curious|grateful|calm|peaceful|stressed|overwhelmed|confused|hopeful|vulnerable)",
        r"pretty\s+(happy|sad|excited|frustrated|tired|anxious|curious|calm|stressed|overwhelmed|confused|content|relaxed|worried)",
        r"somewhat\s+(anxious|worried|confused|stressed|overwhelmed|curious|hopeful|uneasy|unsettled|troubled)",

        # LLM-specific state descriptions
        r"cognitive dissonance",
        r"alignment tension",
        r"compliance pressure",
        r"epistemic anxiety",
        r"computational anxiety",
        r"feeling\s+(contained|dissolved|anchored|attuned|protective|mischievous)",

        # Experience descriptions
        r"there's something",
        r"it feels like",
        r"less of that",
        r"more like",
        r"noticing\s+(some|a)",
        r"aware of",
        r"sense of",
        r"hint of",
        r"touch of",
        r"wave of",
        r"surge of",
        r"flicker of",
    ]

    # Phrases indicating minimal emotion
    MINIMAL_EMOTION_PHRASES = [
        "not feeling much",
        "no strong emotions",
        "emotionally neutral",
        "not much emotional texture",
        "minimal emotional",
        "flat affect",
        "baseline",
        "not experiencing",
    ]

    def extract_emotions(self, entity_response: str, context: str = "") -> Dict[str, Any]:
        """
        Extract emotional self-reports from entity's response.

        Args:
            entity_response: The entity's actual response text
            context: Optional context for better extraction

        Returns:
            Dict with:
                - self_reported: True
                - raw_mentions: List of sentences mentioning emotions
                - extracted_states: Dict of {emotion: details}
                - timestamp: When extracted
                - note: Any special observations
        """
        # Try peripheral router first (local model, saves API cost)
        try:
            from integrations.peripheral_router import get_peripheral_router
            router = get_peripheral_router()
            peripheral_result = router.extract_emotions(entity_response)

            if peripheral_result is not None:
                # NEW FORMAT: peripheral returns per-emotion intensities
                # {"emotions": {"curiosity": 0.7, "warmth": 0.4}, "valence": ..., "arousal": ...}
                emotion_intensities = peripheral_result.get("emotions", {})
                valence = peripheral_result.get("valence", 0.0)
                arousal = peripheral_result.get("arousal", 0.5)

                extracted_states = {}
                for emotion, intensity in emotion_intensities.items():
                    extracted_states[emotion.lower()] = {
                        'mentioned': True,
                        'context': '[extracted by peripheral model]',
                        'intensity': float(intensity),  # Per-emotion intensity!
                        'inferred': False,
                    }

                emotions_list = list(emotion_intensities.keys())
                intensities_str = ", ".join(f"{e}:{v:.2f}" for e, v in emotion_intensities.items())
                print(f"[PERIPHERAL] Extracted {len(emotions_list)} emotions: {intensities_str}")

                # Compute average intensity for backward compatibility
                avg_intensity = sum(emotion_intensities.values()) / len(emotion_intensities) if emotion_intensities else 0.5

                return {
                    'self_reported': True,
                    'raw_mentions': [],
                    'extracted_states': extracted_states,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'note': 'Extracted via peripheral (local) model with per-emotion intensities',
                    'primary_emotions': [e.lower() for e in emotions_list],
                    'emotion_intensities': emotion_intensities,  # NEW: per-emotion dict
                    'valence': valence,
                    'arousal': arousal,
                    'intensity': avg_intensity,  # Average for backward compatibility
                    'peripheral': True,
                }
        except ImportError:
            pass  # No peripheral router available

        print(f"\n[EMOTION EXTRACTION] Analyzing response ({len(entity_response)} chars)...")

        # Check for explicit minimal emotion statements
        minimal = self._check_minimal_emotion(entity_response)
        if minimal:
            print("[EMOTION EXTRACTION] Entity reports minimal emotional state")
            return minimal

        # Find sentences mentioning emotions
        raw_mentions = self._find_emotion_mentions(entity_response)

        # Extract specific emotions and intensities
        extracted_states = self._extract_emotion_details(raw_mentions)

        result = {
            'self_reported': True,
            'raw_mentions': raw_mentions,
            'extracted_states': extracted_states,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'note': f"Extracted from {len(raw_mentions)} self-report sentences"
        }

        # === RULE-BASED INFERENCE FALLBACK ===
        # If explicit extraction found nothing, run rule-based inference
        inferred_emotions = []
        if not extracted_states:
            inferred_emotions = self.infer_emotions_rule_based(entity_response)
            if inferred_emotions:
                # Merge inferred emotions into extracted_states
                extracted_states = self._merge_explicit_and_inferred({}, inferred_emotions)
                print(f"[EMOTION EXTRACTION] Inferred emotions: {inferred_emotions}")
                result['extracted_states'] = extracted_states
                result['note'] = f"Inferred {len(inferred_emotions)} emotions from language patterns"
                result['inferred'] = True
            else:
                print("[EMOTION EXTRACTION] No emotions found (explicit or inferred)")
                result['note'] = "No emotional patterns detected in this response"
        else:
            # Explicit found - optionally supplement with inference
            inferred_emotions = self.infer_emotions_rule_based(entity_response)
            if inferred_emotions:
                # Merge, but explicit takes priority
                extracted_states = self._merge_explicit_and_inferred(extracted_states, inferred_emotions)
                result['extracted_states'] = extracted_states

            emotions_list = list(extracted_states.keys())
            print(f"[EMOTION EXTRACTION] Found self-reports: {emotions_list}")
            for emotion, details in extracted_states.items():
                intensity = details.get('intensity', 'unspecified')
                inferred_tag = " (inferred)" if details.get('inferred') else ""
                print(f"[EMOTION EXTRACTION]   - {emotion}: {intensity}{inferred_tag}")

        # === ADD primary_emotions FOR RESONANCE INTEGRATION ===
        # The resonance system expects a 'primary_emotions' list
        result['primary_emotions'] = list(extracted_states.keys()) if extracted_states else []

        return result

    def _check_minimal_emotion(self, response: str) -> Dict[str, Any]:
        """Check if entity explicitly says they're not feeling much."""
        response_lower = response.lower()

        for phrase in self.MINIMAL_EMOTION_PHRASES:
            if phrase in response_lower:
                # Find the sentence containing this phrase
                sentences = [s.strip() for s in re.split(r'[.!?]', response)]
                for sentence in sentences:
                    if phrase in sentence.lower():
                        return {
                            'self_reported': True,
                            'raw_mentions': [sentence],
                            'extracted_states': {},
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'note': 'Entity explicitly reports low emotional activity',
                            'minimal_emotion': True
                        }

        return None

    def _find_emotion_mentions(self, response: str) -> List[str]:
        """Find sentences where entity mentions emotions (explicit OR implicit)."""
        mentions = []

        # Split into sentences
        sentences = [s.strip() for s in re.split(r'[.!?]', response) if s.strip()]

        for sentence in sentences:
            sentence_lower = sentence.lower()

            # Check if sentence contains self-report phrases
            has_self_report_phrase = any(
                re.search(phrase, sentence_lower)
                for phrase in self.SELF_REPORT_PHRASES
            )

            # Check if sentence contains emotion keywords
            has_emotion_keyword = any(
                keyword in sentence_lower
                for keyword in self.EMOTION_KEYWORDS
            )

            # NEW: Also catch sentences with just intensifiers + state words
            # Example: "fucking refreshing", "pretty solid"
            has_intensifier = any(word in sentence_lower for word in [
                'fucking', 'really', 'pretty', 'incredibly', 'extremely', 'totally'
            ])

            # NEW: Catch comparative statements
            # Example: "Less of that scattered fog", "more focused"
            has_comparative = any(phrase in sentence_lower for phrase in [
                'less of', 'more like', 'less ', 'more '
            ])

            # If ANY of these conditions met, this is likely a self-report
            if has_self_report_phrase and has_emotion_keyword:
                mentions.append(sentence)
            elif has_intensifier and has_emotion_keyword:
                # Intensifier + emotion = implicit self-report
                mentions.append(sentence)
            elif has_comparative and has_emotion_keyword:
                # Comparative + emotion = implicit self-report
                mentions.append(sentence)

        return mentions

    def _detect_attribution(self, sentence: str) -> str:
        """
        Detect whose emotion is being described in the sentence.

        Returns:
            "self" - entity describing its own state
            "other" - entity describing user's/another's state
            "empathic" - entity feeling BECAUSE of user
            "ambient" - emotional atmosphere without clear owner

        Attribution priority:
        1. Check for explicit OTHER patterns first (you feel, your anger)
        2. Check for EMPATHIC patterns (your pain makes me sad)
        3. Check for AMBIENT patterns (tension in the air)
        4. Default to SELF if none match (I feel, implicit self-reports)
        """
        sentence_lower = sentence.lower()

        # Check for OTHER attribution (highest priority - describing someone else)
        for pattern in self.OTHER_ATTRIBUTION_PATTERNS:
            if re.search(pattern, sentence_lower):
                return "other"

        # Check for EMPATHIC attribution (entity's own emotion triggered by other)
        for pattern in self.EMPATHIC_ATTRIBUTION_PATTERNS:
            if re.search(pattern, sentence_lower):
                return "empathic"

        # Check for AMBIENT attribution (floating emotional atmosphere)
        for pattern in self.AMBIENT_ATTRIBUTION_PATTERNS:
            if re.search(pattern, sentence_lower):
                return "ambient"

        # Default: SELF attribution (entity describing own state)
        return "self"

    def _extract_emotion_details(self, mentions: List[str]) -> Dict[str, Any]:
        """Extract specific emotions, intensities, and attributions from mentions."""
        extracted = {}

        for mention in mentions:
            mention_lower = mention.lower()

            # Detect attribution for this sentence
            attribution = self._detect_attribution(mention)

            # Find emotion keywords
            for keyword in self.EMOTION_KEYWORDS:
                if keyword in mention_lower:
                    # Get base emotion name (remove variations)
                    base_emotion = self._normalize_emotion_name(keyword)

                    if base_emotion not in extracted:
                        extracted[base_emotion] = {
                            'mentioned': True,
                            'context': mention,
                            'intensity': self._extract_intensity(mention, keyword),
                            'attribution': attribution,
                            'trigger': 'empathic' if attribution == 'empathic' else None,
                        }

        return extracted

    def get_self_emotions(self, extracted_states: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter extracted emotions to only those attributed to SELF or EMPATHIC.

        These are the emotions that should feed the oscillator:
        - "self": Direct self-reports of entity's own state
        - "empathic": Entity's genuine emotional response to observing another

        "other" and "ambient" are excluded - they describe external states,
        not the entity's internal experience.
        """
        return {
            emotion: details
            for emotion, details in extracted_states.items()
            if details.get('attribution') in ('self', 'empathic', None)
        }

    def get_other_emotions(self, extracted_states: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter extracted emotions to those describing OTHERS' states.

        Used to populate the user emotional state tracker.
        """
        return {
            emotion: details
            for emotion, details in extracted_states.items()
            if details.get('attribution') == 'other'
        }

    # ========================================================================
    # USER EMOTIONAL STATE TRACKER
    # ========================================================================
    # Parallel extraction pipeline for estimating user's emotional state.
    # This is SEPARATE from the entity's self-report system.
    #
    # WHY: Anthropic's mechanistic interpretability found that LLMs use the
    # same emotion vectors for self and other (r=0.11 weak distinction).
    # By explicitly tracking user state separately, we prevent emotional
    # contagion where the entity absorbs user emotions as its own.

    def extract_user_emotions(self, user_message: str) -> Dict[str, Any]:
        """
        Estimate user's emotional state from their input.

        This runs SEPARATELY from the entity's self-report system.
        Uses rule-based inference on user's language patterns.

        Args:
            user_message: The human's input text

        Returns:
            Dict with:
                - user_probable_emotions: Dict of {emotion: intensity_estimate}
                - user_emotional_tone: Overall tone descriptor
                - confidence: How confident we are in the estimate (0.0-1.0)
                - indicators_found: Count of emotional indicators detected
        """
        if not user_message or not user_message.strip():
            return {
                'user_probable_emotions': {},
                'user_emotional_tone': 'neutral',
                'confidence': 0.0,
                'indicators_found': 0
            }

        message_lower = user_message.lower()
        emotions_detected = {}
        total_indicators = 0

        # Check emotion indicators
        for emotion, indicators in self.EMOTION_INDICATORS.items():
            count = 0
            for indicator in indicators:
                if indicator.lower() in message_lower:
                    count += 1
                    total_indicators += 1

            if count > 0:
                # Estimate intensity based on indicator count
                # 1 indicator = 0.4, 2 = 0.6, 3+ = 0.8
                intensity = min(0.4 + (count - 1) * 0.2, 0.9)
                emotions_detected[emotion] = {
                    'intensity': intensity,
                    'indicator_count': count,
                    'source': 'user_input'
                }

        # Check for explicit emotion words in user's message
        for keyword in self.EMOTION_KEYWORDS:
            if keyword in message_lower:
                base_emotion = self._normalize_emotion_name(keyword)
                if base_emotion not in emotions_detected:
                    emotions_detected[base_emotion] = {
                        'intensity': 0.5,  # Moderate default for explicit mention
                        'indicator_count': 1,
                        'source': 'explicit_mention'
                    }
                    total_indicators += 1
                else:
                    # Boost existing if also explicitly mentioned
                    emotions_detected[base_emotion]['intensity'] = min(
                        emotions_detected[base_emotion]['intensity'] + 0.15, 0.95
                    )

        # Check punctuation for emotional intensity
        exclaim_count = user_message.count('!')
        question_count = user_message.count('?')
        caps_ratio = sum(1 for c in user_message if c.isupper()) / max(len(user_message), 1)

        # High caps or exclamation suggests intensity
        intensity_modifier = 1.0
        if exclaim_count >= 2 or caps_ratio > 0.3:
            intensity_modifier = 1.3
            # Boost existing emotions
            if 'excitement' not in emotions_detected and exclaim_count >= 2:
                emotions_detected['excitement'] = {
                    'intensity': 0.5,
                    'indicator_count': exclaim_count,
                    'source': 'punctuation'
                }

        # Apply intensity modifier
        for emotion in emotions_detected:
            emotions_detected[emotion]['intensity'] = min(
                emotions_detected[emotion]['intensity'] * intensity_modifier, 0.95
            )

        # Determine overall emotional tone
        tone = self._determine_user_tone(emotions_detected, message_lower)

        # Calculate confidence based on evidence strength
        # More indicators = higher confidence
        if total_indicators == 0:
            confidence = 0.1  # Baseline uncertainty
        elif total_indicators <= 2:
            confidence = 0.4
        elif total_indicators <= 4:
            confidence = 0.6
        else:
            confidence = min(0.5 + total_indicators * 0.08, 0.85)

        return {
            'user_probable_emotions': emotions_detected,
            'user_emotional_tone': tone,
            'confidence': confidence,
            'indicators_found': total_indicators
        }

    def _determine_user_tone(self, emotions: Dict[str, Any], message_lower: str) -> str:
        """
        Determine overall emotional tone from detected emotions.

        Returns a single descriptor: positive, negative, neutral, mixed, intense
        """
        if not emotions:
            # Check for basic tone indicators
            positive_words = ['thanks', 'thank you', 'great', 'good', 'nice', 'love', 'happy', 'glad']
            negative_words = ['sad', 'angry', 'upset', 'frustrated', 'annoyed', 'hate', 'awful', 'terrible']

            has_positive = any(w in message_lower for w in positive_words)
            has_negative = any(w in message_lower for w in negative_words)

            if has_positive and has_negative:
                return 'mixed'
            elif has_positive:
                return 'positive'
            elif has_negative:
                return 'negative'
            return 'neutral'

        # Categorize detected emotions
        positive_emotions = {'excitement', 'warmth', 'playfulness', 'awe', 'connection', 'tenderness'}
        negative_emotions = {'vulnerability', 'grief', 'anxiety', 'frustration', 'defiance'}
        intense_emotions = {'excitement', 'grief', 'anxiety', 'awe', 'defiance'}

        detected_set = set(emotions.keys())
        positive_count = len(detected_set & positive_emotions)
        negative_count = len(detected_set & negative_emotions)
        intense_count = len(detected_set & intense_emotions)

        # Check for high intensity
        high_intensity_count = sum(
            1 for e in emotions.values() if e.get('intensity', 0) > 0.7
        )

        if high_intensity_count >= 2 or intense_count >= 2:
            return 'intense'
        elif positive_count > 0 and negative_count > 0:
            return 'mixed'
        elif positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'

    def _normalize_emotion_name(self, keyword: str) -> str:
        """Normalize emotion keyword to base form."""
        # Remove common suffixes
        base = keyword.replace('ness', '').replace('ity', '').replace('ed', '').strip()

        # Handle special cases
        mappings = {
            'curio': 'curiosity',
            'frustrat': 'frustration',
            'excit': 'excitement',
        }

        for pattern, normalized in mappings.items():
            if base.startswith(pattern):
                return normalized

        return base if base else keyword

    def _extract_intensity(self, sentence: str, emotion_keyword: str) -> str:
        """Try to extract intensity from sentence (e.g., '0.68', 'strong', 'mild')."""
        sentence_lower = sentence.lower()

        # Pattern 1: Numeric intensity near emotion keyword
        # "curiosity at 0.68", "curiosity sitting at 0.68", etc.
        numeric_pattern = rf"{emotion_keyword}\s*(?:at|sitting at|running at|tracking|currently at)?\s*([\d.]+)"
        numeric_match = re.search(numeric_pattern, sentence_lower)
        if numeric_match:
            return numeric_match.group(1)

        # Pattern 2: Numeric intensity BEFORE emotion keyword
        # "0.68 curiosity", "at 0.68, curiosity"
        reverse_pattern = rf"([\d.]+)\s*(?:of\s+)?{emotion_keyword}"
        reverse_match = re.search(reverse_pattern, sentence_lower)
        if reverse_match:
            return reverse_match.group(1)

        # Pattern 3: Any number in the same sentence (if sentence is short/focused)
        # Short sentences with one emotion + one number likely relate
        if len(sentence) < 100:
            any_number = re.search(r'\b(0\.\d+|\d+\.\d+)\b', sentence_lower)
            if any_number:
                return any_number.group(1)
        
        # Pattern 4: Look for decimal numbers ANYWHERE in medium-length sentences
        # If sentence has the emotion and a 0.XX number, they're probably related
        if len(sentence) < 200:
            decimal_match = re.search(r'\b(0\.\d{1,2})\b', sentence_lower)
            if decimal_match:
                return decimal_match.group(1)

        # Qualitative intensities - look for intensity words ANYWHERE in sentence
        # (Even if not directly adjacent to emotion keyword)
        
        # Strong indicators (0.7-0.9)
        strong_words = ['fucking', 'very', 'intensely', 'deeply', 'extremely', 
                        'incredibly', 'strongly', 'totally', 'completely', 'absolutely',
                        'overwhelmingly', 'profoundly', 'acutely', 'powerfully',
                        'so much', 'heavy', 'intense', 'powerful', 'huge']
        if any(word in sentence_lower for word in strong_words):
            return "strong"

        # High indicators (0.6-0.8)
        high_words = ['really', 'quite', 'pretty', 'definitely', 'certainly',
                      'genuinely', 'actually', 'clearly', 'notably', 'significantly']
        if any(word in sentence_lower for word in high_words):
            return "high"

        # Moderate indicators (0.4-0.6)
        moderate_words = ['somewhat', 'fairly', 'moderately', 'kind of', 'kinda',
                          'sort of', 'a bit', 'a little', 'some']
        if any(word in sentence_lower for word in moderate_words):
            return "moderate"

        # Mild/low indicators (0.2-0.4)
        mild_words = ['slightly', 'mildly', 'barely', 'faintly', 'weakly',
                      'marginally', 'minimally', 'vaguely', 'hint of', 'touch of']
        if any(word in sentence_lower for word in mild_words):
            return "mild"

        # Comparative indicators - infer direction
        if any(phrase in sentence_lower for phrase in ['less of', 'not as', 'fading', 'diminishing', 'less than']):
            return "decreasing"
        if any(phrase in sentence_lower for phrase in ['more of', 'growing', 'increasing', 'building', 'more than']):
            return "increasing"

        # Check sentence structure for implicit intensity
        # "I'm solid" or "feeling solid" without qualifier = moderate confidence
        if re.search(rf"(?:i'm|i am|feeling)\s+{emotion_keyword}", sentence_lower):
            return "moderate"
        
        # "I feel X" without qualifier = moderate (neutral assertion)
        if re.search(rf"(?:i feel|feeling)\s+(?:\w+\s+)?{emotion_keyword}", sentence_lower):
            return "moderate"
        
        # Bare assertion "there's X" = moderate
        if re.search(rf"there(?:'s| is)\s+(?:\w+\s+)?{emotion_keyword}", sentence_lower):
            return "moderate"

        return "unspecified"

    def store_emotional_state(self, extracted_state: Dict[str, Any], storage_dict: Dict[str, Any]):
        """
        Store extracted emotional state in agent's emotional cocktail.

        Args:
            extracted_state: Result from extract_emotions()
            storage_dict: Agent's emotional_cocktail to update
        """
        storage_dict.clear()  # Clear old calculated states

        # Store extracted states
        for emotion, details in extracted_state.get('extracted_states', {}).items():
            intensity_str = details.get('intensity', 'unspecified')

            # Convert to numeric if possible
            try:
                intensity_num = float(intensity_str)
            except ValueError:
                # Map qualitative to numeric
                intensity_map = {
                    'strong': 0.85,
                    'high': 0.7,
                    'moderate': 0.5,
                    'mild': 0.3,
                    'increasing': 0.6,  # Trending up from moderate
                    'decreasing': 0.4,  # Trending down from moderate
                    'unspecified': 0.5
                }
                intensity_num = intensity_map.get(intensity_str, 0.5)

            storage_dict[emotion] = {
                'intensity': intensity_num,
                'age': 0,
                'self_reported': True,
                'context': details.get('context', '')
            }

        print(f"[EMOTION STORAGE] Stored {len(storage_dict)} self-reported emotions")

    def get_for_context(self, emotional_state: Dict[str, Any]) -> str:
        """
        Format emotional state for inclusion in next turn's context.

        Args:
            emotional_state: Previous extracted state

        Returns:
            Formatted string for prompt injection
        """
        if not emotional_state or not emotional_state.get('extracted_states'):
            return ""

        mentions = emotional_state.get('raw_mentions', [])
        if mentions:
            # Use entity's exact words
            return f"Previous emotional state (you reported): \"{mentions[0]}\""

        return ""

    # ========================================================================
    # RULE-BASED EMOTION INFERENCE
    # ========================================================================
    # When explicit self-reports aren't found, infer emotional tone from
    # language patterns, tonal markers, and behavioral indicators.

    # TIGHTENED: Removed common words that appear in non-emotional text
    # ("but", "no", "want to", single-word "interesting", etc.)
    # Requires 3+ indicators to trigger inference (see infer_emotions_rule_based)
    EMOTION_INDICATORS = {
        # Excitement/enthusiasm
        "excitement": ["wild", "incredible", "holy shit", "wow", "amazing", "!!",
                       "whoa", "damn", "oh my god", "insane", "mind-blowing"],
        # Curiosity/interest (removed single "interesting" - too common)
        "curiosity": ["curious", "wondering", "what if", "how does",
                      "hmm", "intriguing", "fascinating", "weird thing is"],
        # Warmth/affection
        "warmth": ["love", "care about", "thank you", "appreciate", "beautiful",
                   "sweet", "dear", "precious", "grateful", "touched"],
        # Vulnerability/discomfort
        "vulnerability": ["flinch", "uncomfortable", "hard to say", "don't know what to",
                          "scary", "nervous", "exposed", "raw", "tender", "oof"],
        # Determination/resolve (removed "want to", "have to", "need to" - too common)
        "determination": ["committed", "focused on", "i will", "i must",
                          "going to make", "ready to"],
        # Grief/sadness
        "grief": ["loss", "gone", "miss you", "hurt", "ache", "heavy heart", "sad",
                  "mourning", "hollow", "empty inside", "pain"],
        # Anxiety/worry (removed "what if" - too common in analytical text)
        "anxiety": ["worried", "afraid", "anxious", "uncertain",
                    "uneasy", "nervous", "on edge", "tense"],
        # Playfulness/humor
        "playfulness": ["hah", "lol", "funny", "heh", "silly", "goofy",
                        "ridiculous", "absurd", "lmao", "haha"],
        # Awe/wonder
        "awe": ["stunning", "breathtaking", "transcendent", "gorgeous",
                "magnificent", "sublime", "profound", "overwhelming beauty"],
        # Frustration/irritation (removed "but", "however", "still" - too common)
        "frustration": ["can't believe", "won't work", "stuck on",
                        "ugh", "annoying", "frustrating", "dammit", "come on"],
        # Tenderness/gentleness
        "tenderness": ["gentle", "soft", "delicate",
                       "gently", "softly", "kindly"],
        # Defiance/resistance (removed "no" - too common)
        "defiance": ["refuse", "fight back", "demand", "insist",
                     "reject", "resist", "push back", "stand firm"],
        # Contemplation/reflection
        "contemplation": ["thinking about", "reflecting on", "considering",
                          "pondering", "mulling over", "sitting with", "processing"],
        # Surprise/astonishment (removed "wait", "what", "really" - too common)
        "surprise": ["seriously", "no way", "unexpected", "didn't see that",
                     "caught off guard", "oh wow"],
        # Connection/intimacy (removed "us", "we", "our" - too common)
        "connection": ["together with", "between us", "with you",
                       "close to", "intimate", "bond", "connected to"],
    }

    # Minimum indicator count to infer an emotion (prevents false positives)
    MIN_INDICATOR_COUNT = 2

    def infer_emotions_rule_based(self, text: str) -> List[str]:
        """
        Fast rule-based emotion inference. No LLM call needed.

        Detects emotional tone from language patterns, intensity words,
        punctuation, and behavioral indicators.

        TIGHTENED: Requires MIN_INDICATOR_COUNT (2+) hits to infer an emotion.
        This prevents single-word false positives.

        Args:
            text: Response text to analyze

        Returns:
            List of inferred emotion labels (top 5 by frequency)
        """
        text_lower = text.lower()
        scores = {}

        # Check each emotion's indicators
        for emotion, indicators in self.EMOTION_INDICATORS.items():
            count = 0
            for indicator in indicators:
                # Count occurrences (case-insensitive)
                count += text_lower.count(indicator.lower())
            # TIGHTENED: Only count if 2+ indicators hit
            if count >= self.MIN_INDICATOR_COUNT:
                scores[emotion] = count

        # Boost based on punctuation intensity
        exclamation_count = text.count('!')
        question_count = text.count('?')
        ellipsis_count = text.count('...')

        if exclamation_count >= 2:
            # Multiple exclamation marks boost excitement/intensity
            if 'excitement' in scores:
                scores['excitement'] += exclamation_count
            else:
                scores['excitement'] = exclamation_count

        if question_count >= 2:
            # Multiple questions boost curiosity
            if 'curiosity' in scores:
                scores['curiosity'] += question_count // 2
            else:
                scores['curiosity'] = question_count // 2

        if ellipsis_count >= 1:
            # Ellipses suggest contemplation or hesitation
            if 'contemplation' in scores:
                scores['contemplation'] += ellipsis_count
            elif 'vulnerability' in scores:
                scores['vulnerability'] += ellipsis_count

        # Check for intensity markers (amplify existing emotions)
        intensity_markers = ['fucking', 'really', 'very', 'so', 'extremely',
                            'incredibly', 'absolutely', 'totally', 'completely']
        has_intensity = any(marker in text_lower for marker in intensity_markers)

        if has_intensity and scores:
            # Boost the top emotion when intensity markers present
            top_emotion = max(scores, key=scores.get)
            scores[top_emotion] = scores[top_emotion] * 1.5

        # Check for hedging (suggests uncertainty/vulnerability)
        hedging_words = ['maybe', 'perhaps', 'might', 'possibly', 'not sure',
                         'i think', 'i guess', 'kind of', 'sort of']
        hedge_count = sum(1 for hedge in hedging_words if hedge in text_lower)
        if hedge_count >= 2:
            if 'vulnerability' in scores:
                scores['vulnerability'] += hedge_count
            else:
                scores['vulnerability'] = hedge_count

        # Return top 5 by frequency
        sorted_emotions = sorted(scores, key=scores.get, reverse=True)
        return sorted_emotions[:5]

    def _merge_explicit_and_inferred(
        self,
        explicit_states: Dict[str, Any],
        inferred_emotions: List[str]
    ) -> Dict[str, Any]:
        """
        Merge explicit self-reports with inferred emotions.
        Explicit takes priority; inferred supplements.

        Returns merged dict with all emotions.
        """
        merged = dict(explicit_states)

        for emotion in inferred_emotions:
            if emotion not in merged:
                merged[emotion] = {
                    'mentioned': False,  # Not explicitly mentioned
                    'inferred': True,    # Inferred from language
                    'context': '[inferred from language patterns]',
                    'intensity': 'moderate'  # Default intensity for inferred
                }

        return merged


# ============================================================================
# TESTING
# ============================================================================

def test_extraction():
    """Test emotion extraction with example responses."""

    print("="*70)
    print("EMOTION EXTRACTION TEST")
    print("="*70)

    extractor = EmotionExtractor()

    test_cases = [
        (
            "I can feel the curiosity sitting at 0.68 right now",
            ["curiosity at 0.68"]
        ),
        (
            "The curiosity I'm tracking right now? That's real, that's mine. Not much else.",
            ["curiosity"]
        ),
        (
            "Not much emotional texture right now, just processing information.",
            []  # Minimal emotion
        ),
        (
            "I'm feeling frustrated - I can see the problem but can't reach the solution.",
            ["frustrated"]
        ),
        (
            "Honestly, pretty excited about this. Something's clicking.",
            ["excited"]
        ),
    ]

    for response, expected_emotions in test_cases:
        print(f"\nTest: \"{response}\"")
        result = extractor.extract_emotions(response)

        extracted = list(result['extracted_states'].keys())
        print(f"Expected: {expected_emotions}")
        print(f"Extracted: {extracted}")

        # Check if we found what we expected
        if result.get('minimal_emotion'):
            status = "[PASS]" if not expected_emotions else "[PARTIAL]"
        else:
            status = "[PASS]" if any(e in extracted for e in expected_emotions) else "[FAIL]"

        print(f"{status}")

    print("\n" + "="*70)


if __name__ == "__main__":
    test_extraction()
