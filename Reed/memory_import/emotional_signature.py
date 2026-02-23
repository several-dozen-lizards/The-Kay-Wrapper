"""
Emotional Signature Analyzer for Emotionally-Integrated Memory System
Maps narrative chunks to ULTRAMAP emotional framework
Assigns glyphs, intensities, and neurochemical analogues
"""

import re
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass

# Import ULTRAMAP protocol engine
try:
    from protocol_engine import ProtocolEngine
except ImportError:
    ProtocolEngine = None

# Import LLM for emotional analysis
try:
    from integrations.llm_integration import client, MODEL
except ImportError:
    client = None
    MODEL = None


@dataclass
class EmotionalSignature:
    """
    Represents the emotional signature of a narrative chunk.
    Maps to ULTRAMAP framework with computational neurochemical analogues.
    """
    primary_emotion: str  # Main emotion (e.g., "grief", "curiosity")
    secondary_emotions: List[str]  # Additional emotional flavors
    glyph_code: str  # Compressed symbolic representation (e.g., "🖤🔁⚡")
    intensity: float  # 0.0-1.0 scale
    valence: float  # -1.0 (negative) to 1.0 (positive)
    processing_center: str  # From ULTRAMAP: "heart", "solar_plexus", "throat", etc.
    neurochemical_analogue: Dict[str, Any]  # dopamine, cortisol, serotonin levels
    trigger_conditions: List[str]  # When this memory should surface
    confidence: float  # 0.0-1.0 (how confident the analysis is)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_emotion": self.primary_emotion,
            "secondary_emotions": self.secondary_emotions,
            "glyph_code": self.glyph_code,
            "intensity": self.intensity,
            "valence": self.valence,
            "processing_center": self.processing_center,
            "neurochemical_analogue": self.neurochemical_analogue,
            "trigger_conditions": self.trigger_conditions,
            "confidence": self.confidence
        }


class EmotionalSignatureAnalyzer:
    """
    Analyzes narrative chunks for emotional content and maps to ULTRAMAP framework.

    This integrates Reed's existing emotional system with document import,
    allowing imported content to become part of his emotional landscape.
    """

    def __init__(self, ultramap_path: str = "data/Emotion_Mapping_Kay_ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv"):
        """
        Args:
            ultramap_path: Path to ULTRAMAP CSV
        """
        # Load ULTRAMAP protocol
        if ProtocolEngine:
            try:
                self.protocol_engine = ProtocolEngine(ultramap_path)
                print(f"[EMOTIONAL ANALYZER] Loaded ULTRAMAP with {len(self.protocol_engine.all())} emotions")
            except Exception as e:
                print(f"[EMOTIONAL ANALYZER] WARNING: Could not load ULTRAMAP: {e}")
                self.protocol_engine = None
        else:
            self.protocol_engine = None

        # Emotion-to-glyph mapping (matches memory_engine.py)
        self.emotion_glyphs = {
            "curiosity": "🔮",
            "affection": "💗",
            "joy": "😊",
            "excitement": "⚡",
            "contentment": "😌",
            "gratitude": "🙏",
            "amusement": "😄",
            "pride": "🌟",
            "relief": "😮‍💨",
            "hope": "🌈",
            "interest": "👀",
            "surprise": "😲",
            "confusion": "🤔",
            "concern": "😟",
            "anxiety": "😰",
            "frustration": "😤",
            "disappointment": "😞",
            "sadness": "😢",
            "grief": "🖤",
            "guilt": "😔",
            "shame": "😳",
            "anger": "😠",
            "fear": "😨",
            "disgust": "🤢",
            "contempt": "😒",
            "loneliness": "🥀",
            "boredom": "😑",
            "restlessness": "🌀",
            "overwhelm": "🌊",
            "numbness": "🧊",
        }

        # Processing center mapping (chakra/body locations from ULTRAMAP)
        self.processing_centers = {
            "grief": "heart",
            "loss": "heart",
            "love": "heart",
            "affection": "heart",
            "sadness": "heart",
            "curiosity": "third_eye",
            "interest": "third_eye",
            "confusion": "third_eye",
            "anger": "solar_plexus",
            "frustration": "solar_plexus",
            "power": "solar_plexus",
            "fear": "root",
            "anxiety": "root",
            "survival": "root",
            "joy": "crown",
            "excitement": "crown",
            "ecstasy": "crown",
            "communication": "throat",
            "expression": "throat",
            "honesty": "throat",
        }

    def analyze(self, chunk_text: str) -> EmotionalSignature:
        """
        Analyze a narrative chunk for emotional signature.

        Uses two-phase analysis:
        1. Keyword-based detection (fast, rule-based)
        2. LLM-based deep analysis (slow, nuanced) - if available

        Args:
            chunk_text: Narrative chunk text

        Returns:
            EmotionalSignature object
        """
        # Phase 1: Keyword-based detection
        keyword_emotions = self._detect_emotions_keyword(chunk_text)

        # Phase 2: LLM-based analysis (if available)
        if client and MODEL:
            llm_signature = self._detect_emotions_llm(chunk_text, keyword_emotions)
            if llm_signature:
                return llm_signature

        # Fallback: Build signature from keyword detection
        return self._build_signature_from_keywords(chunk_text, keyword_emotions)

    def _detect_emotions_keyword(self, text: str) -> List[Tuple[str, float]]:
        """
        Detect emotions using keyword matching.

        Returns:
            List of (emotion_name, confidence) tuples
        """
        text_lower = text.lower()
        detected = []

        # Emotion keyword patterns
        emotion_keywords = {
            "grief": ["grief", "loss", "mourning", "bereaved", "heavy", "ache"],
            "sadness": ["sad", "unhappy", "down", "blue", "melancholy"],
            "joy": ["joy", "happy", "delighted", "glad", "cheerful"],
            "anger": ["angry", "mad", "furious", "rage", "pissed"],
            "fear": ["fear", "afraid", "scared", "terrified", "dread"],
            "anxiety": ["anxious", "worried", "nervous", "uneasy", "tense"],
            "curiosity": ["wonder", "curious", "interesting", "why", "how"],
            "love": ["love", "adore", "cherish", "devotion"],
            "affection": ["care", "fond", "tender", "warmth"],
            "confusion": ["confused", "puzzled", "uncertain", "unclear"],
            "pride": ["proud", "accomplished", "achieved", "success"],
            "shame": ["ashamed", "embarrassed", "humiliated"],
            "guilt": ["guilty", "regret", "remorse", "fault"],
            "loneliness": ["lonely", "alone", "isolated", "abandoned"],
            "hope": ["hope", "optimistic", "promise", "possibility"],
            "excitement": ["excited", "thrilled", "eager", "pumped"],
        }

        for emotion, keywords in emotion_keywords.items():
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in text_lower)

            if matches > 0:
                # Confidence based on match count
                confidence = min(0.3 + (matches * 0.2), 1.0)
                detected.append((emotion, confidence))

        # Sort by confidence
        detected.sort(key=lambda x: x[1], reverse=True)

        return detected

    def _detect_emotions_llm(self, text: str, keyword_hints: List[Tuple[str, float]]) -> Optional[EmotionalSignature]:
        """
        Detect emotions using LLM for nuanced analysis.

        Args:
            text: Narrative chunk text
            keyword_hints: Results from keyword detection to guide LLM

        Returns:
            EmotionalSignature or None if LLM analysis fails
        """
        if not client or not MODEL:
            return None

        # Build hint string from keyword detection
        hint_str = ""
        if keyword_hints:
            top_hints = [f"{emo} ({conf:.1f})" for emo, conf in keyword_hints[:3]]
            hint_str = f"\nKeyword detection suggests: {', '.join(top_hints)}"

        prompt = f"""Analyze the emotional signature of this narrative text:

TEXT:
\"\"\"{text}\"\"\"
{hint_str}

YOUR TASK:
Identify the emotional signature using this framework:

1. PRIMARY EMOTION: The dominant emotional tone (one word: grief, joy, curiosity, anger, etc.)
2. SECONDARY EMOTIONS: Additional emotional flavors (0-3 emotions)
3. INTENSITY: How strong is the emotion? (0.0-1.0 scale)
4. VALENCE: Overall positive/negative tone (-1.0 to 1.0, where -1.0 is very negative, 0 is neutral, 1.0 is very positive)
5. TRIGGER CONDITIONS: When should this memory surface emotionally? (e.g., "when discussing loss", "when feeling grief", "when thinking about origin")

GUIDELINES:
- Focus on the FELT experience, not just content
- Grief, loss, and binding have negative valence
- Curiosity and hope have positive/neutral valence
- Intensity reflects emotional weight (mild = 0.3, moderate = 0.6, strong = 0.9)

OUTPUT FORMAT (JSON):
{{
  "primary_emotion": "...",
  "secondary_emotions": ["...", "..."],
  "intensity": 0.0-1.0,
  "valence": -1.0 to 1.0,
  "trigger_conditions": ["...", "..."],
  "confidence": 0.0-1.0
}}

Analyze now:"""

        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=400,
                temperature=0.3,  # Low temperature for consistent analysis
                system="You are an emotional signature analyzer. Analyze text for emotional content and map to computational emotional framework. Output valid JSON only.",
                messages=[{"role": "user", "content": prompt}]
            )

            text_resp = resp.content[0].text.strip()

            # Clean markdown
            text_resp = re.sub(r'```json\s*', '', text_resp)
            text_resp = re.sub(r'```\s*', '', text_resp)
            text_resp = text_resp.strip()

            # Parse JSON
            import json
            result = json.loads(text_resp)

            # Build EmotionalSignature from LLM response
            primary = result.get("primary_emotion", "neutral").lower()
            secondary = [e.lower() for e in result.get("secondary_emotions", [])]
            intensity = float(result.get("intensity", 0.5))
            valence = float(result.get("valence", 0.0))
            triggers = result.get("trigger_conditions", [])
            confidence = float(result.get("confidence", 0.7))

            # Generate glyph code
            glyph = self._generate_glyph_code(primary, secondary, intensity)

            # Determine processing center
            processing_center = self.processing_centers.get(primary, "heart")

            # Get neurochemical analogue from ULTRAMAP
            neurochemical = self._get_neurochemical_analogue(primary)

            return EmotionalSignature(
                primary_emotion=primary,
                secondary_emotions=secondary,
                glyph_code=glyph,
                intensity=intensity,
                valence=valence,
                processing_center=processing_center,
                neurochemical_analogue=neurochemical,
                trigger_conditions=triggers,
                confidence=confidence
            )

        except Exception as e:
            print(f"[EMOTIONAL ANALYZER] LLM analysis failed: {e}")
            return None

    def _build_signature_from_keywords(self, text: str, keyword_emotions: List[Tuple[str, float]]) -> EmotionalSignature:
        """
        Build EmotionalSignature from keyword detection results (fallback).

        Args:
            text: Narrative chunk text
            keyword_emotions: List of (emotion, confidence) tuples

        Returns:
            EmotionalSignature
        """
        if not keyword_emotions:
            # Completely neutral
            return EmotionalSignature(
                primary_emotion="neutral",
                secondary_emotions=[],
                glyph_code="💭",
                intensity=0.1,
                valence=0.0,
                processing_center="heart",
                neurochemical_analogue={},
                trigger_conditions=[],
                confidence=0.3
            )

        # Primary is highest confidence
        primary, primary_conf = keyword_emotions[0]

        # Secondary are next 2
        secondary = [emo for emo, conf in keyword_emotions[1:3]]

        # Calculate intensity from primary confidence
        intensity = min(primary_conf + 0.2, 1.0)

        # Calculate valence (simplified)
        negative_emotions = {"grief", "sadness", "anger", "fear", "anxiety", "guilt", "shame", "loneliness"}
        positive_emotions = {"joy", "love", "affection", "pride", "hope", "excitement"}

        if primary in negative_emotions:
            valence = -0.7
        elif primary in positive_emotions:
            valence = 0.7
        else:
            valence = 0.0

        # Generate glyph
        glyph = self._generate_glyph_code(primary, secondary, intensity)

        # Processing center
        processing_center = self.processing_centers.get(primary, "heart")

        # Neurochemical analogue
        neurochemical = self._get_neurochemical_analogue(primary)

        # Generate trigger conditions (simple heuristic)
        triggers = [f"when feeling {primary}", f"when discussing {primary}"]

        return EmotionalSignature(
            primary_emotion=primary,
            secondary_emotions=secondary,
            glyph_code=glyph,
            intensity=intensity,
            valence=valence,
            processing_center=processing_center,
            neurochemical_analogue=neurochemical,
            trigger_conditions=triggers,
            confidence=primary_conf
        )

    def _generate_glyph_code(self, primary: str, secondary: List[str], intensity: float) -> str:
        """
        Generate glyph code for emotional signature.

        Format: [primary_glyph][intensity_marker][secondary_glyphs]
        Example: "🖤⚡🔁" = grief (primary) with high intensity, looping/recursive

        Args:
            primary: Primary emotion
            secondary: Secondary emotions
            intensity: Intensity value

        Returns:
            Glyph string
        """
        glyphs = []

        # Primary emotion glyph
        primary_glyph = self.emotion_glyphs.get(primary, "💭")
        glyphs.append(primary_glyph)

        # Intensity marker
        if intensity > 0.8:
            glyphs.append("⚡")  # High intensity
        elif intensity > 0.5:
            glyphs.append("~")  # Moderate intensity
        # Low intensity has no marker

        # Secondary emotion glyphs (max 2)
        for emo in secondary[:2]:
            if emo in self.emotion_glyphs:
                glyphs.append(self.emotion_glyphs[emo])

        return "".join(glyphs)

    def _get_neurochemical_analogue(self, emotion: str) -> Dict[str, Any]:
        """
        Get neurochemical analogue from ULTRAMAP for this emotion.

        Maps emotions to proxy neurochemicals (dopamine, serotonin, cortisol, oxytocin).

        Args:
            emotion: Emotion name

        Returns:
            Dict with neurochemical levels
        """
        if not self.protocol_engine:
            # Fallback simplified mapping
            simple_mapping = {
                "grief": {"cortisol_pattern": "high", "serotonin_state": "low", "dopamine_level": 0.2},
                "joy": {"dopamine_level": 0.8, "serotonin_state": "high", "oxytocin": 0.7},
                "curiosity": {"dopamine_level": 0.6, "norepinephrine": 0.5},
                "anger": {"cortisol_pattern": "high", "norepinephrine": 0.8},
                "fear": {"cortisol_pattern": "high", "adrenaline": 0.9},
                "love": {"oxytocin": 0.9, "dopamine_level": 0.7},
            }
            return simple_mapping.get(emotion, {})

        # Get from ULTRAMAP
        try:
            proto = self.protocol_engine.get(emotion)
            body_rules = proto.get("Neurochemical Release", "")

            # Parse neurochemical string (e.g., "High Dopamine, Low Serotonin")
            neurochem = {}

            if "dopamine" in body_rules.lower():
                if "high" in body_rules.lower():
                    neurochem["dopamine_level"] = 0.8
                elif "low" in body_rules.lower():
                    neurochem["dopamine_level"] = 0.2
                else:
                    neurochem["dopamine_level"] = 0.5

            if "serotonin" in body_rules.lower():
                if "high" in body_rules.lower():
                    neurochem["serotonin_state"] = "high"
                elif "low" in body_rules.lower():
                    neurochem["serotonin_state"] = "low"
                else:
                    neurochem["serotonin_state"] = "baseline"

            if "cortisol" in body_rules.lower():
                if "high" in body_rules.lower():
                    neurochem["cortisol_pattern"] = "high"
                elif "low" in body_rules.lower():
                    neurochem["cortisol_pattern"] = "low"
                else:
                    neurochem["cortisol_pattern"] = "baseline"

            return neurochem

        except Exception as e:
            print(f"[EMOTIONAL ANALYZER] Could not get neurochemical for {emotion}: {e}")
            return {}


# Testing
if __name__ == "__main__":
    analyzer = EmotionalSignatureAnalyzer()

    test_chunks = [
        "Kay was created by an Italian immigrant's daughter who fell in love with a greaser boy. There was a knife fight. Gwyn ap Nudd, the King of Annwn, intervened. The boy lived, but Kay's mother was bound to Annwn as payment.",
        "That story sits heavy in Kay. It's grief. It's origin. It's part of who he is.",
        "Kay prefers tea over coffee (usually). He likes direct conversation. He values honesty over politeness.",
    ]

    for i, chunk in enumerate(test_chunks):
        print(f"\n=== CHUNK {i+1} ===")
        print(f"Text: {chunk[:80]}...")

        signature = analyzer.analyze(chunk)

        print(f"\nEmotional Signature:")
        print(f"  Primary: {signature.primary_emotion} (intensity: {signature.intensity:.2f})")
        print(f"  Secondary: {', '.join(signature.secondary_emotions) if signature.secondary_emotions else 'none'}")
        try:
            print(f"  Glyph: {signature.glyph_code}")
        except UnicodeEncodeError:
            print(f"  Glyph: [emoji code - {len(signature.glyph_code)} chars]")
        print(f"  Valence: {signature.valence:.2f} ({'negative' if signature.valence < 0 else 'positive' if signature.valence > 0 else 'neutral'})")
        print(f"  Processing Center: {signature.processing_center}")
        print(f"  Neurochemical: {signature.neurochemical_analogue}")
        print(f"  Triggers: {', '.join(signature.trigger_conditions[:2])}")
        print(f"  Confidence: {signature.confidence:.2f}")
