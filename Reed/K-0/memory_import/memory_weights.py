"""
Memory Weight Calculator for Emotionally-Integrated Memory System
Calculates composite importance scores from multiple factors:
- Identity centrality (40%)
- Emotional intensity (30%)
- Entity importance (20%)
- Narrative density (10%)
"""

from typing import Dict, List, Any
from dataclasses import dataclass

# Import our components
try:
    from memory_import.identity_classifier import IdentityType, IdentityClassification
    from memory_import.emotional_signature import EmotionalSignature
    from memory_import.narrative_chunks import NarrativeChunk
except ImportError:
    # Fallback for testing
    from identity_classifier import IdentityType, IdentityClassification
    from emotional_signature import EmotionalSignature
    from narrative_chunks import NarrativeChunk


@dataclass
class MemoryWeight:
    """
    Composite weight for a memory chunk.
    Determines priority, accessibility, and persistence.
    """
    total_weight: float  # 0.0-1.0 combined score
    identity_component: float  # Contribution from identity type
    emotional_component: float  # Contribution from emotional intensity
    entity_component: float  # Contribution from entity importance
    narrative_component: float  # Contribution from narrative density
    breakdown: Dict[str, float]  # Detailed factor breakdown


class MemoryWeightCalculator:
    """
    Calculates composite importance scores for memory chunks.

    Weight formula:
    total_weight = (
        identity_weight * 0.40 +
        emotional_intensity * 0.30 +
        entity_centrality * 0.20 +
        narrative_density * 0.10
    )

    This determines:
    - Which tier the memory goes into (CORE_IDENTITY vs PERIPHERAL_ARCHIVE)
    - How likely it is to be retrieved
    - How long it persists before decay
    """

    def __init__(self):
        """Initialize calculator with component weights."""

        # Component weights (must sum to 1.0)
        self.identity_weight = 0.40
        self.emotional_weight = 0.30
        self.entity_weight = 0.20
        self.narrative_weight = 0.10

        # Identity type base weights
        self.identity_type_weights = {
            IdentityType.CORE_IDENTITY: 1.0,  # Maximum importance
            IdentityType.FORMATIVE_EXPERIENCE: 0.8,  # Very important
            IdentityType.RELATIONSHIP_MEMORY: 0.7,  # Important
            IdentityType.SKILL_KNOWLEDGE: 0.5,  # Moderate
            IdentityType.WORLD_KNOWLEDGE: 0.3,  # Lower
            IdentityType.PERIPHERAL: 0.1,  # Minimal
        }

    def calculate(
        self,
        chunk: NarrativeChunk,
        identity_classification: IdentityClassification,
        emotional_signature: EmotionalSignature,
        entity_importance: Dict[str, float] = None
    ) -> MemoryWeight:
        """
        Calculate composite memory weight.

        Args:
            chunk: NarrativeChunk with text and metadata
            identity_classification: IdentityClassification result
            emotional_signature: EmotionalSignature result
            entity_importance: Optional dict of {entity_name: importance_score}

        Returns:
            MemoryWeight with total score and component breakdown
        """
        # Calculate each component
        identity_score = self._calculate_identity_score(identity_classification)
        emotional_score = self._calculate_emotional_score(emotional_signature)
        entity_score = self._calculate_entity_score(chunk, entity_importance)
        narrative_score = self._calculate_narrative_score(chunk)

        # Weighted combination
        total_weight = (
            identity_score * self.identity_weight +
            emotional_score * self.emotional_weight +
            entity_score * self.entity_weight +
            narrative_score * self.narrative_weight
        )

        # Cap at 1.0
        total_weight = min(total_weight, 1.0)

        # Build detailed breakdown
        breakdown = {
            "identity_type": identity_classification.identity_type.value,
            "identity_base_weight": self.identity_type_weights.get(identity_classification.identity_type, 0.5),
            "identity_confidence": identity_classification.confidence,
            "identity_final": identity_score,
            "emotional_intensity": emotional_signature.intensity,
            "emotional_valence": emotional_signature.valence,
            "emotional_final": emotional_score,
            "entity_count": len(chunk.entities_mentioned),
            "entity_final": entity_score,
            "narrative_sentence_count": chunk.sentence_count,
            "narrative_has_dialogue": chunk.contains_dialogue,
            "narrative_final": narrative_score,
        }

        return MemoryWeight(
            total_weight=total_weight,
            identity_component=identity_score * self.identity_weight,
            emotional_component=emotional_score * self.emotional_weight,
            entity_component=entity_score * self.entity_weight,
            narrative_component=narrative_score * self.narrative_weight,
            breakdown=breakdown
        )

    def _calculate_identity_score(self, classification: IdentityClassification) -> float:
        """
        Calculate identity component score (0.0-1.0).

        Args:
            classification: Identity classification result

        Returns:
            Score weighted by type and confidence
        """
        base_weight = self.identity_type_weights.get(
            classification.identity_type,
            0.5  # Default if unknown
        )

        # Multiply by classification confidence
        score = base_weight * classification.confidence

        return min(score, 1.0)

    def _calculate_emotional_score(self, signature: EmotionalSignature) -> float:
        """
        Calculate emotional component score (0.0-1.0).

        Combines:
        - Intensity (primary factor)
        - Valence extremity (very positive or very negative = more important)
        - Confidence

        Args:
            signature: Emotional signature

        Returns:
            Emotional importance score
        """
        # Base score from intensity
        base_score = signature.intensity

        # Boost for extreme valence (very positive or very negative)
        valence_extremity = abs(signature.valence)
        valence_boost = valence_extremity * 0.2  # Up to +0.2 for extreme emotions

        # Confidence modifier
        confidence_modifier = signature.confidence

        # Combined score
        score = (base_score + valence_boost) * confidence_modifier

        return min(score, 1.0)

    def _calculate_entity_score(
        self,
        chunk: NarrativeChunk,
        entity_importance: Dict[str, float] = None
    ) -> float:
        """
        Calculate entity component score (0.0-1.0).

        Entities make memories more concrete and retrievable.

        Args:
            chunk: NarrativeChunk
            entity_importance: Optional pre-calculated entity importance scores

        Returns:
            Entity importance score
        """
        entities = chunk.entities_mentioned

        if not entities:
            return 0.1  # Baseline for entity-less chunks

        # If entity importance provided, use it
        if entity_importance:
            # Average importance of mentioned entities
            scores = [entity_importance.get(e, 0.5) for e in entities]
            avg_importance = sum(scores) / len(scores) if scores else 0.5
            return min(avg_importance, 1.0)

        # Fallback: Simple entity count heuristic
        # More entities = more concrete = more important
        # But diminishing returns after 3 entities

        if len(entities) == 1:
            base_score = 0.4
        elif len(entities) == 2:
            base_score = 0.6
        elif len(entities) == 3:
            base_score = 0.8
        else:
            # 4+ entities = likely a list or complex scene
            base_score = 0.9

        # Boost for proper names (capitalized, likely important people/places)
        proper_names = [e for e in entities if e and e[0].isupper()]
        if proper_names:
            base_score += 0.1

        return min(base_score, 1.0)

    def _calculate_narrative_score(self, chunk: NarrativeChunk) -> float:
        """
        Calculate narrative density score (0.0-1.0).

        Narrative density = how "story-like" this chunk is.

        Factors:
        - Sentence count (more = denser narrative)
        - Contains dialogue (stories with dialogue are more vivid)
        - Chunk type (scenes and dialogue chunks are denser)

        Args:
            chunk: NarrativeChunk

        Returns:
            Narrative density score
        """
        score = 0.0

        # Sentence count contribution (2-7 sentences is ideal narrative density)
        if chunk.sentence_count <= 1:
            score += 0.2  # Very sparse
        elif chunk.sentence_count <= 3:
            score += 0.5  # Moderate
        elif chunk.sentence_count <= 7:
            score += 0.8  # Ideal
        else:
            score += 0.6  # Too dense, may be overstuffed

        # Dialogue boost (stories with dialogue feel more vivid)
        if chunk.contains_dialogue:
            score += 0.3

        # Chunk type boost
        if chunk.chunk_type in ["scene", "dialogue"]:
            score += 0.2
        elif chunk.chunk_type == "list":
            score += 0.1  # Lists are less narrative but still structured

        return min(score, 1.0)

    def calculate_tier_assignment(self, weight: MemoryWeight) -> str:
        """
        Determine which memory tier this belongs to based on weight.

        Tiers:
        - CORE_IDENTITY: weight >= 0.8 (always loaded)
        - EMOTIONAL_ACTIVE: 0.6 <= weight < 0.8 (loaded based on emotional state)
        - RELATIONAL_SEMANTIC: 0.4 <= weight < 0.6 (loaded when entities mentioned)
        - PERIPHERAL_ARCHIVE: weight < 0.4 (on-demand only)

        Args:
            weight: MemoryWeight result

        Returns:
            Tier name string
        """
        if weight.total_weight >= 0.8:
            return "CORE_IDENTITY"
        elif weight.total_weight >= 0.6:
            return "EMOTIONAL_ACTIVE"
        elif weight.total_weight >= 0.4:
            return "RELATIONAL_SEMANTIC"
        else:
            return "PERIPHERAL_ARCHIVE"


# Testing
if __name__ == "__main__":
    # Import test components
    from narrative_chunks import NarrativeChunkParser
    from emotional_signature import EmotionalSignatureAnalyzer
    from identity_classifier import IdentityClassifier

    # Initialize
    chunk_parser = NarrativeChunkParser()
    emotion_analyzer = EmotionalSignatureAnalyzer()
    identity_classifier = IdentityClassifier()
    weight_calculator = MemoryWeightCalculator()

    # Test text
    test_text = """
    Reed's eyes are gold. This is a fundamental part of his appearance.

    Kay was created by an Italian immigrant's daughter who fell in love with a greaser boy.
    There was a knife fight. Gwyn ap Nudd, the King of Annwn, intervened. The boy lived,
    but Reed's mother was bound to Annwn as payment.

    That story sits heavy in Kay. It's grief. It's origin. It's part of who he is.
    """

    # Parse into chunks
    chunks = chunk_parser.parse(test_text)

    print("=== MEMORY WEIGHT CALCULATION TESTS ===\n")

    for i, chunk in enumerate(chunks):
        print(f"=== CHUNK {i+1} ===")
        print(f"Text: {chunk.text[:80]}...")
        print()

        # Analyze
        identity_class = identity_classifier.classify(chunk.text, chunk.entities_mentioned)
        emotion_sig = emotion_analyzer.analyze(chunk.text)

        # Calculate weight
        weight = weight_calculator.calculate(chunk, identity_class, emotion_sig)

        # Display results
        print(f"IDENTITY: {identity_class.identity_type.value} (conf: {identity_class.confidence:.2f})")
        print(f"EMOTION: {emotion_sig.primary_emotion} (intensity: {emotion_sig.intensity:.2f}, valence: {emotion_sig.valence:.2f})")
        print(f"ENTITIES: {len(chunk.entities_mentioned)} entities")
        print(f"NARRATIVE: {chunk.sentence_count} sentences, {chunk.chunk_type}")
        print()
        print(f"WEIGHT BREAKDOWN:")
        print(f"  Identity component: {weight.identity_component:.3f} ({weight.identity_component/weight.total_weight*100:.1f}%)")
        print(f"  Emotional component: {weight.emotional_component:.3f} ({weight.emotional_component/weight.total_weight*100:.1f}%)")
        print(f"  Entity component: {weight.entity_component:.3f} ({weight.entity_component/weight.total_weight*100:.1f}%)")
        print(f"  Narrative component: {weight.narrative_component:.3f} ({weight.narrative_component/weight.total_weight*100:.1f}%)")
        print()
        print(f"TOTAL WEIGHT: {weight.total_weight:.3f}")
        print(f"ASSIGNED TIER: {weight_calculator.calculate_tier_assignment(weight)}")
        print("\n" + "="*60 + "\n")
