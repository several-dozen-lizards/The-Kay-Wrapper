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
    """

    # Emotion keywords to look for in entity's response
    # TIGHTENED: Removed overly common words that cause false positives
    # (good, fine, better, great, clear, sharp, focused, solid, lost, refreshed)
    EMOTION_KEYWORDS = [
        # Core emotions (unambiguously emotional)
        'curious', 'curiosity',
        'frustrated', 'frustration',
        'excited', 'excitement',
        'angry', 'anger',
        'confused', 'confusion',
        'interested', 'interest',
        'concerned', 'concern',
        'anxious', 'anxiety',
        'longing',

        # Positive states
        'happy', 'happiness', 'joy', 'joyful',
        'energized', 'motivated',
        'pleased', 'satisfied',
        'calm', 'peaceful', 'serene',
        'grateful', 'appreciative',
        'amused', 'playful',

        # Cognitive/Mental states (only unambiguous ones)
        'foggy', 'scattered', 'hazy', 'clouded',
        'disoriented',

        # Energy states
        'tired', 'exhausted', 'fatigued', 'drained',
        'energetic', 'charged',
        'restless', 'wired',

        # Negative states
        'sad', 'sadness',
        'bored', 'boredom',
        'worried', 'nervous',
        'annoyed', 'irritated',
        'disappointed',
        'melancholy',

        # Complex
        'conflicted', 'ambivalent',
        'uncertain', 'unsure',
        'overwhelmed',
    ]

    # Phrases that indicate self-reporting
    # TIGHTENED: Removed overly broad patterns that match non-emotional text
    SELF_REPORT_PHRASES = [
        # Explicit emotional self-reports
        r"i feel\b",
        r"i'm feeling\b",
        r"feeling\s+(happy|sad|anxious|curious|excited|frustrated|angry|worried|tired|energized|grateful|confused|overwhelmed|calm|peaceful)",
        r"i can feel\b",
        r"i'm experiencing\b",
        r"experiencing\s+(emotion|feeling|anxiety|excitement|curiosity)",
        r"emotion",
        r"emotional",
        r"tracking",  # "I'm tracking curiosity at 0.68"
        r"sitting at",  # "curiosity sitting at 0.68"
        r"running at",  # "running at 0.5"
        r"currently at",  # "currently at 0.6"

        # Intensifiers ONLY when followed by emotion words
        r"fucking\s+(happy|sad|excited|frustrated|tired|anxious|relieved|grateful|angry)",
        r"really\s+(happy|sad|excited|frustrated|tired|anxious|curious|grateful|angry|worried)",
        r"incredibly\s+(happy|sad|excited|frustrated|tired|anxious|curious|grateful)",
        r"extremely\s+(happy|sad|excited|frustrated|tired|anxious|curious|grateful)",

        # Experience descriptions
        r"there's something",
        r"it feels like",
        r"less of that",
        r"more like",
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

    def _extract_emotion_details(self, mentions: List[str]) -> Dict[str, Any]:
        """Extract specific emotions and intensities from mentions."""
        extracted = {}

        for mention in mentions:
            mention_lower = mention.lower()

            # Find emotion keywords
            for keyword in self.EMOTION_KEYWORDS:
                if keyword in mention_lower:
                    # Get base emotion name (remove variations)
                    base_emotion = self._normalize_emotion_name(keyword)

                    if base_emotion not in extracted:
                        extracted[base_emotion] = {
                            'mentioned': True,
                            'context': mention,
                            'intensity': self._extract_intensity(mention, keyword)
                        }

        return extracted

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
