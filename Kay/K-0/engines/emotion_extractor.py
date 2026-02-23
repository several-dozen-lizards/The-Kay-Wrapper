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

    # Emotion keywords to look for in entity's response (EXPANDED)
    EMOTION_KEYWORDS = [
        # Core emotions
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
        'solid',  # NEW: "feeling solid"
        'good', 'fine', 'better', 'great',  # NEW: common positive descriptors
        'refreshed', 'refreshing',  # NEW: "fucking refreshing"

        # Cognitive/Mental states (NEW)
        'sharp', 'focused', 'clear', 'clarity',  # "sharp and focused"
        'foggy', 'scattered', 'hazy', 'clouded',  # "scattered fog"
        'lost', 'disoriented',

        # Energy states (NEW)
        'tired', 'exhausted', 'fatigued', 'drained',
        'energized', 'energetic', 'charged',
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

    # Phrases that indicate self-reporting (EXPANDED for implicit patterns)
    SELF_REPORT_PHRASES = [
        # Explicit patterns (original)
        r"i feel",
        r"i'm feeling",
        r"feeling",
        r"i can feel",
        r"i'm experiencing",
        r"experiencing",
        r"emotion",
        r"emotional",
        r"tracking",  # "I'm tracking curiosity at 0.68"
        r"sitting at",  # "curiosity sitting at 0.68"
        r"running at",  # "running at 0.5"
        r"currently at",  # "currently at 0.6"

        # NEW: Implicit state descriptions
        r"i'm\s+\w+",  # "I'm solid", "I'm sharp", "I'm foggy"
        r"i am\s+\w+",  # "I am focused"
        r"pretty\s+\w+",  # "pretty solid", "pretty good"
        r"feeling\s+\w+",  # "feeling solid", "feeling better"

        # NEW: Intensifiers (signal strong emotion)
        r"fucking",
        r"really\s+\w+",
        r"incredibly",
        r"extremely",
        r"totally",

        # NEW: Experience descriptions
        r"there's something",
        r"it feels",
        r"less of that",
        r"more like",
        r"the weird",
        r"what's grabbing",
        r"less\s+\w+",  # "less scattered", "less foggy"
        r"more\s+\w+",  # "more focused", "more clear"
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

        if extracted_states:
            emotions_list = list(extracted_states.keys())
            print(f"[EMOTION EXTRACTION] Found self-reports: {emotions_list}")
            for emotion, details in extracted_states.items():
                intensity = details.get('intensity', 'unspecified')
                print(f"[EMOTION EXTRACTION]   - {emotion}: {intensity}")
        else:
            print("[EMOTION EXTRACTION] No explicit emotional self-reports found")
            result['note'] = "No explicit emotional mentions in this response"

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
