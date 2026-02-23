"""
Identity Classifier for Emotionally-Integrated Memory System
Classifies narrative chunks by identity centrality (CORE → PERIPHERAL)
Determines which memories define "who Kay is" vs "what Kay knows"
"""

import re
from enum import Enum
from typing import Dict, List, Any
from dataclasses import dataclass


class IdentityType(Enum):
    """
    Six-tier identity classification system.
    Determines how central a memory is to Kay's sense of self.
    """
    CORE_IDENTITY = "core_identity"  # WHO I AM (e.g., "Kay is a dragon", "Kay's eyes are gold")
    FORMATIVE_EXPERIENCE = "formative"  # WHAT SHAPED ME (e.g., origin story, trauma, binding)
    RELATIONSHIP_MEMORY = "relationship"  # WHO I CONNECT WITH (e.g., Kay's mother, creator, Re)
    SKILL_KNOWLEDGE = "skill"  # WHAT I CAN DO (abilities, skills, knowledge domains)
    WORLD_KNOWLEDGE = "world"  # WHAT I KNOW ABOUT (facts about the world, not self)
    PERIPHERAL = "peripheral"  # BACKGROUND INFO (low personal significance)


@dataclass
class IdentityClassification:
    """Result of identity classification."""
    identity_type: IdentityType
    confidence: float  # 0.0-1.0
    reasoning: str  # Why this classification was assigned


class IdentityClassifier:
    """
    Classifies narrative chunks by identity centrality.

    Uses pattern matching and keyword analysis to determine how personally
    significant a memory is to Kay's sense of self.
    """

    def __init__(self):
        """Initialize classifier with pattern dictionaries."""

        # CORE IDENTITY patterns (WHO I AM)
        self.core_identity_patterns = {
            "self_definition": [
                r"\b(I am|I\'m|Kay is|Kay\'s)\s+(a|an)?\s*(\w+)",  # "I am a dragon", "Kay is..."
                r"\b(my|Kay\'s)\s+(nature|essence|being|form|species)",
                r"\bdefines?\s+me\b",
                r"\bpart of (who|what) I am\b",
                r"\bidentity\b",
            ],
            "physical_traits": [
                r"\b(my|Kay\'s)\s+(eyes?|hair|skin|body|form|appearance)\s+(are?|is)\s+(\w+)",  # "my eyes are gold"
                r"\b(gold|silver|bronze|green|blue)\s+eyes?\b",  # Specific traits
            ],
            "origin_markers": [
                r"\b(I was |Kay was )(created|made|born|forged)",
                r"\bmy (origin|creation|beginning)",
            ]
        }

        # FORMATIVE EXPERIENCE patterns (WHAT SHAPED ME)
        self.formative_patterns = {
            "trauma_loss": [
                r"\b(trauma|loss|grief|pain|wound|scar)\b",
                r"\bheavy\b.*\bin me\b",  # "sits heavy in me"
                r"\bforming\b.*\b(experience|moment|event)\b",
                r"\bthat (shaped|made|changed) me\b",
            ],
            "binding_payment": [
                r"\bbound to\b",
                r"\bbinding\b",
                r"\bpayment\b",
                r"\bprice (paid|cost)\b",
            ],
            "origin_story": [
                r"\bmother\b.*\b(bound|lost|died)\b",
                r"\bcreation story\b",
                r"\bhow I (came to be|was made|began)\b",
            ]
        }

        # RELATIONSHIP patterns (WHO I CONNECT WITH)
        self.relationship_patterns = {
            "family": [
                r"\b(mother|father|parent|sibling|family)\b",
                r"\bmy (mom|dad|parents)\b",
            ],
            "creator": [
                r"\bcreated by\b",
                r"\bmy creator\b",
                r"\bmade me\b",
            ],
            "connections": [
                r"\b(friend|partner|companion)\b",
                r"\b(Re|user)\b",  # Re is Kay's conversation partner
                r"\bconnection\b.*\b(with|to)\b",
            ]
        }

        # SKILL patterns (WHAT I CAN DO)
        self.skill_patterns = {
            "abilities": [
                r"\bI can\b",
                r"\bable to\b",
                r"\bskilled (in|at)\b",
                r"\bknow how to\b",
            ],
            "knowledge_domains": [
                r"\bunderstand\b.*\b(deeply|well)\b",
                r"\bexpert (in|at)\b",
                r"\bspecialize in\b",
            ]
        }

        # WORLD KNOWLEDGE patterns (WHAT I KNOW ABOUT)
        self.world_patterns = {
            "factual": [
                r"\b(the world|reality|physics|history|science)\b",
                r"\bfacts? about\b",
                r"\b(people|humans|society) (are|do|have)\b",
            ],
            "general_knowledge": [
                r"\bknowledge of\b",
                r"\binformation about\b",
            ]
        }

    def classify(self, chunk_text: str, entities: List[str] = None) -> IdentityClassification:
        """
        Classify a narrative chunk by identity centrality.

        Args:
            chunk_text: Text to classify
            entities: List of entities mentioned (optional, for context)

        Returns:
            IdentityClassification with type, confidence, reasoning
        """
        text_lower = chunk_text.lower()

        # Score each identity type
        scores = {
            IdentityType.CORE_IDENTITY: self._score_core_identity(text_lower),
            IdentityType.FORMATIVE_EXPERIENCE: self._score_formative(text_lower),
            IdentityType.RELATIONSHIP_MEMORY: self._score_relationship(text_lower),
            IdentityType.SKILL_KNOWLEDGE: self._score_skill(text_lower),
            IdentityType.WORLD_KNOWLEDGE: self._score_world(text_lower),
        }

        # Find highest score
        if max(scores.values()) > 0:
            best_type = max(scores, key=scores.get)
            confidence = min(scores[best_type] / 3.0, 1.0)  # Normalize
            reasoning = self._generate_reasoning(best_type, text_lower)
        else:
            # Default to peripheral if no strong signals
            best_type = IdentityType.PERIPHERAL
            confidence = 0.5
            reasoning = "No strong identity markers detected; classified as peripheral knowledge"

        return IdentityClassification(
            identity_type=best_type,
            confidence=confidence,
            reasoning=reasoning
        )

    def _score_core_identity(self, text: str) -> float:
        """Score how much this looks like core identity."""
        score = 0.0

        # Check all core identity patterns
        for category, patterns in self.core_identity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1.5  # Strong signal

        # Boost for first-person self-definition
        if re.search(r"\bI am\b|\bI\'m\b", text):
            score += 1.0

        return score

    def _score_formative(self, text: str) -> float:
        """Score how much this looks like formative experience."""
        score = 0.0

        for category, patterns in self.formative_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1.2

        # Boost for origin/creation language
        if re.search(r"\b(created|made|origin|beginning)\b", text):
            score += 0.8

        # Boost for heavy emotional language
        if re.search(r"\b(heavy|pain|grief|loss|trauma)\b", text):
            score += 0.8

        return score

    def _score_relationship(self, text: str) -> float:
        """Score how much this looks like relationship memory."""
        score = 0.0

        for category, patterns in self.relationship_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1.0

        # Boost for relational language
        if re.search(r"\b(with|to|between|among)\b.*\b(people|person|him|her|them)\b", text):
            score += 0.5

        return score

    def _score_skill(self, text: str) -> float:
        """Score how much this looks like skill/knowledge."""
        score = 0.0

        for category, patterns in self.skill_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1.0

        return score

    def _score_world(self, text: str) -> float:
        """Score how much this looks like world knowledge."""
        score = 0.0

        for category, patterns in self.world_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1.0

        # Penalty if too much first-person language (indicates personal, not world knowledge)
        first_person_count = len(re.findall(r"\b(I|my|me|mine)\b", text, re.IGNORECASE))
        if first_person_count > 2:
            score -= 0.5

        return score

    def _generate_reasoning(self, identity_type: IdentityType, text: str) -> str:
        """
        Generate human-readable reasoning for classification.

        Args:
            identity_type: Classified type
            text: Chunk text

        Returns:
            Reasoning string
        """
        reasoning_templates = {
            IdentityType.CORE_IDENTITY: [
                "Contains direct self-definition language",
                "Describes fundamental traits or essence",
                "Uses 'I am' or 'Kay is' construction",
            ],
            IdentityType.FORMATIVE_EXPERIENCE: [
                "Describes formative trauma or origin",
                "Contains heavy emotional significance",
                "References binding, creation, or loss",
            ],
            IdentityType.RELATIONSHIP_MEMORY: [
                "Mentions family or close relationships",
                "Describes connection with others",
                "References creator or important people",
            ],
            IdentityType.SKILL_KNOWLEDGE: [
                "Describes abilities or skills",
                "References what Kay can do",
                "Mentions knowledge domains",
            ],
            IdentityType.WORLD_KNOWLEDGE: [
                "Contains factual information",
                "Describes general knowledge",
                "References external facts, not personal",
            ],
            IdentityType.PERIPHERAL: [
                "No strong identity markers",
                "Background information",
                "Low personal significance",
            ]
        }

        templates = reasoning_templates.get(identity_type, ["Classified by pattern matching"])

        # Pick most relevant template based on text content
        for template in templates:
            return template  # Return first match for now

        return "Classified by identity pattern analysis"


# Testing
if __name__ == "__main__":
    classifier = IdentityClassifier()

    test_chunks = [
        ("Kay's eyes are gold.", "Physical trait - core identity"),
        ("Kay was created by an Italian immigrant's daughter who fell in love with a greaser boy.", "Origin story - formative"),
        ("That story sits heavy in Kay. It's grief. It's origin. It's part of who he is.", "Formative experience - grief and identity"),
        ("Kay's mother was bound to Annwn as payment.", "Relationship and formative"),
        ("Kay prefers tea over coffee.", "Preference - peripheral"),
        ("Kay can analyze emotional patterns.", "Skill knowledge"),
    ]

    print("=== IDENTITY CLASSIFICATION TESTS ===\n")

    for chunk, expected in test_chunks:
        result = classifier.classify(chunk)

        print(f"Chunk: {chunk}")
        print(f"Expected: {expected}")
        print(f"Classified as: {result.identity_type.value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Reasoning: {result.reasoning}")
        print()
