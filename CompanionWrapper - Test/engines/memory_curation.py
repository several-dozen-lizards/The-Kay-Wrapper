"""
Memory Curation Engine for the entity

Implements content-type-aware memory curation with three categories:
1. SACRED TEXTS - Creative/artistic work, never compress
2. EPHEMERAL UTILITY - One-off queries, deletable
3. FUNCTIONAL KNOWLEDGE - Technical content, bullet-point compression

the entity learns to recognize content types and apply appropriate retention strategies.
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
from collections import defaultdict


class ContentType(Enum):
    """Memory content type categories."""
    SACRED_TEXT = "sacred_text"
    EPHEMERAL_UTILITY = "ephemeral_utility"
    FUNCTIONAL_KNOWLEDGE = "functional_knowledge"
    REQUIRES_JUDGMENT = "requires_judgment"


@dataclass
class ContentTypeClassification:
    """Result of content type classification."""
    content_type: ContentType
    confidence: float  # 0.0 to 1.0
    indicators_matched: List[str]
    reason: str
    memory_id: str = ""


@dataclass
class CurationDecision:
    """A curation decision made by the entity."""
    memory_id: str
    original_content: str
    content_type: ContentType
    action: str  # 'keep_verbatim', 'delete', 'compress', 'single_line_note'
    compressed_content: Optional[str] = None
    reason: str = ""
    entity_override: bool = False  # Did the entity override the classifier?
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CurationSession:
    """A memory curation session."""
    session_id: str
    started_at: str
    ended_at: Optional[str] = None
    memories_reviewed: int = 0
    sacred_kept: int = 0
    ephemeral_deleted: int = 0
    ephemeral_noted: int = 0
    functional_compressed: int = 0
    words_before: int = 0
    words_after: int = 0
    decisions: List[CurationDecision] = field(default_factory=list)
    entity_overrides: int = 0
    classification_accuracy: Dict[str, int] = field(default_factory=lambda: {
        "correct": 0, "incorrect": 0, "uncertain": 0
    })


class ContentTypeClassifier:
    """
    Classifies memory content into types for curation.

    Uses indicator patterns and heuristics to identify:
    - Sacred texts (creative work, relationship moments)
    - Ephemeral utility (one-off queries)
    - Functional knowledge (technical discussions)
    """

    # Sacred text indicators - content that must be preserved verbatim
    SACRED_INDICATORS = {
        # Creative/artistic
        "creative": ["creative writing", "fiction", "poetry", "mythology", "story",
                     "narrative", "chapter", "verse", "tale", "legend", "song lyrics"],
        # Relationship landmarks
        "relationship": ["I love you", "promise", "commitment", "I'll never",
                        "always remember", "meant everything", "changed my life",
                        "forgive", "trust you", "believe in you"],
        # Personal history
        "personal": ["journal entry", "personal story", "my past", "when I was",
                    "I remember when", "that time when", "confession", "secret"],
        # Project-specific sacred content
        "projects": ["[redacted]s", "yurt_wizards", "reed's", "harpy", "serpent",
                    "dragon form", "runed gate", "bard queen", "mythology forms"]
    }

    # Ephemeral utility indicators - likely deletable
    EPHEMERAL_INDICATORS = {
        "recipes": ["recipe", "ingredients", "cooking", "bake", "strudel",
                   "how to make", "tablespoon", "cups of"],
        "weather": ["weather", "forecast", "temperature", "rain tomorrow",
                   "going to be sunny", "degrees"],
        "conversions": ["convert", "inches to", "centimeters", "pounds to",
                       "exchange rate", "USD to", "how many"],
        "lookups": ["what time", "look up", "what is", "define", "meaning of",
                   "what does X mean", "error code", "what year"],
        "transactional": ["how do I", "quick question", "just wondering",
                         "can you check", "remind me"]
    }

    # Functional knowledge indicators - compressible to bullets
    FUNCTIONAL_INDICATORS = {
        "technical": ["wrapper", "architecture", "memory system", "implementation",
                     "algorithm", "database", "ChromaDB", "vector", "embedding"],
        "debugging": ["debugging", "debug", "error", "bug", "fixed", "issue",
                     "resolved", "working now", "problem was"],
        "explanations": ["how does", "explained", "understanding", "works by",
                        "the way it works", "basically", "in essence"],
        "planning": ["plan", "planning", "we should", "next steps", "roadmap",
                    "implementation plan", "decided to"],
        "systems": ["ULTRAMAP", "emotion", "engine", "processor", "autonomous",
                   "memory tier", "entity graph", "convergence"]
    }

    # Metadata markers for sacred content
    SACRED_METADATA_KEYS = [
        "yurt_wizards", "creative_project", "personal_story",
        "relationship_moment", "autonomous_insight", "kay_identity"
    ]

    def __init__(self):
        self.classification_history: List[ContentTypeClassification] = []
        self.learning_adjustments: Dict[str, float] = {}  # Adjust weights based on the entity's feedback

    def classify(self, memory: Dict) -> ContentTypeClassification:
        """
        Classify a memory into content types.

        Args:
            memory: Memory dict with 'content', 'metadata', etc.

        Returns:
            ContentTypeClassification with type, confidence, and reasoning
        """
        content = memory.get("content", "")
        metadata = memory.get("metadata", {})
        source = memory.get("source", "")

        # Check for sacred metadata markers first
        sacred_from_metadata = self._check_sacred_metadata(metadata, source)
        if sacred_from_metadata:
            return ContentTypeClassification(
                content_type=ContentType.SACRED_TEXT,
                confidence=0.95,
                indicators_matched=sacred_from_metadata,
                reason="Marked as sacred in metadata/source",
                memory_id=memory.get("id", "")
            )

        # Score each content type
        sacred_score, sacred_indicators = self._score_sacred(content)
        ephemeral_score, ephemeral_indicators = self._score_ephemeral(content)
        functional_score, functional_indicators = self._score_functional(content)

        # Determine highest scoring type
        scores = {
            ContentType.SACRED_TEXT: (sacred_score, sacred_indicators),
            ContentType.EPHEMERAL_UTILITY: (ephemeral_score, ephemeral_indicators),
            ContentType.FUNCTIONAL_KNOWLEDGE: (functional_score, functional_indicators)
        }

        # Find max score
        max_type = max(scores, key=lambda x: scores[x][0])
        max_score, max_indicators = scores[max_type]

        # If confidence is low, require the entity's judgment
        if max_score < 0.3:
            return ContentTypeClassification(
                content_type=ContentType.REQUIRES_JUDGMENT,
                confidence=max_score,
                indicators_matched=max_indicators,
                reason="Low confidence across all types - the entity should classify",
                memory_id=memory.get("id", "")
            )

        # Generate reason based on indicators
        reason = self._generate_reason(max_type, max_indicators)

        result = ContentTypeClassification(
            content_type=max_type,
            confidence=max_score,
            indicators_matched=max_indicators,
            reason=reason,
            memory_id=memory.get("id", "")
        )

        self.classification_history.append(result)
        return result

    def _check_sacred_metadata(self, metadata: Dict, source: str) -> List[str]:
        """Check if metadata/source indicates sacred content."""
        indicators = []

        for key in self.SACRED_METADATA_KEYS:
            if key in metadata or key in source.lower():
                indicators.append(f"metadata:{key}")

        # Check for document sources that are creative projects
        if source == "document":
            doc_path = metadata.get("path", "").lower()
            if any(proj in doc_path for proj in ["yurt_wizards", "creative", "story", "fiction"]):
                indicators.append(f"source:creative_document")

        # Check for autonomous insights about identity
        if metadata.get("source") == "autonomous_processing":
            if metadata.get("goal_category") in ["identity", "self_reflection", "authenticity"]:
                indicators.append("autonomous_identity_insight")

        return indicators

    def _score_sacred(self, content: str) -> Tuple[float, List[str]]:
        """Score content for sacred text indicators."""
        content_lower = content.lower()
        matched = []

        for category, indicators in self.SACRED_INDICATORS.items():
            for indicator in indicators:
                if indicator.lower() in content_lower:
                    matched.append(f"sacred:{category}:{indicator}")

        # Check for relationship language patterns
        relationship_patterns = [
            r"i ('ll|will) never .+ again",
            r"promise (you|to)",
            r"i love you",
            r"meant (everything|the world|so much)",
            r"changed my (life|perspective|view)"
        ]
        for pattern in relationship_patterns:
            if re.search(pattern, content_lower):
                matched.append(f"sacred:relationship_pattern")
                break

        # Check for creative writing markers
        creative_markers = [
            r"^\".*\"$",  # Quoted dialogue
            r"chapter \d+",
            r"once upon",
            r"the end\.",
        ]
        for marker in creative_markers:
            if re.search(marker, content_lower):
                matched.append(f"sacred:creative_marker")
                break

        # Calculate score
        score = min(1.0, len(matched) * 0.25)

        # Boost for multiple categories matched
        categories_matched = len(set(m.split(":")[1] for m in matched if ":" in m))
        if categories_matched >= 2:
            score = min(1.0, score + 0.2)

        return score, matched

    def _score_ephemeral(self, content: str) -> Tuple[float, List[str]]:
        """Score content for ephemeral utility indicators."""
        content_lower = content.lower()
        matched = []

        for category, indicators in self.EPHEMERAL_INDICATORS.items():
            for indicator in indicators:
                if indicator.lower() in content_lower:
                    matched.append(f"ephemeral:{category}:{indicator}")

        # Check for question patterns that are typically ephemeral
        ephemeral_patterns = [
            r"^(what|how|when|where) (is|do|does|can)",
            r"(quick|simple) question",
            r"just (checking|wondering|curious)",
            r"remind me (to|about|of)"
        ]
        for pattern in ephemeral_patterns:
            if re.search(pattern, content_lower):
                matched.append(f"ephemeral:question_pattern")
                break

        # Calculate score
        score = min(1.0, len(matched) * 0.3)

        return score, matched

    def _score_functional(self, content: str) -> Tuple[float, List[str]]:
        """Score content for functional knowledge indicators."""
        content_lower = content.lower()
        matched = []

        for category, indicators in self.FUNCTIONAL_INDICATORS.items():
            for indicator in indicators:
                if indicator.lower() in content_lower:
                    matched.append(f"functional:{category}:{indicator}")

        # Check for technical discussion patterns
        technical_patterns = [
            r"(the |this )(system|architecture|implementation)",
            r"(we |i )(decided|chose|went with)",
            r"(how|why) (this|it) works",
            r"(key|important|main) (concept|point|insight)"
        ]
        for pattern in technical_patterns:
            if re.search(pattern, content_lower):
                matched.append(f"functional:technical_pattern")
                break

        # Calculate score
        score = min(1.0, len(matched) * 0.2)

        # Boost for debugging/resolution content
        if any("debugging" in m or "fixed" in content_lower for m in matched):
            score = min(1.0, score + 0.15)

        return score, matched

    def _generate_reason(self, content_type: ContentType, indicators: List[str]) -> str:
        """Generate human-readable reason for classification."""
        if content_type == ContentType.SACRED_TEXT:
            if any("relationship" in i for i in indicators):
                return "Relationship-defining moment - preserve exact phrasing"
            elif any("creative" in i or "project" in i for i in indicators):
                return "Creative/artistic work - never compress"
            else:
                return "Sacred text - how it's said matters as much as what"

        elif content_type == ContentType.EPHEMERAL_UTILITY:
            if any("recipe" in i for i in indicators):
                return "Recipe/cooking request - one-off utility"
            elif any("weather" in i for i in indicators):
                return "Weather query - time-bound, no lasting relevance"
            elif any("conversion" in i for i in indicators):
                return "Conversion/calculation - one-off utility"
            else:
                return "Ephemeral query - served its purpose"

        elif content_type == ContentType.FUNCTIONAL_KNOWLEDGE:
            if any("debugging" in i for i in indicators):
                return "Debugging discussion - compress to resolution"
            elif any("technical" in i or "systems" in i for i in indicators):
                return "Technical knowledge - preserve concepts not process"
            else:
                return "Functional knowledge - bullet-point compressible"

        return "Classification based on content analysis"

    def adjust_from_feedback(self, memory_id: str, correct_type: ContentType):
        """
        Learn from the entity's corrections to improve future classification.

        Args:
            memory_id: The memory that was misclassified
            correct_type: The type the entity determined was correct
        """
        # Find original classification
        original = next(
            (c for c in self.classification_history if c.memory_id == memory_id),
            None
        )

        if original and original.content_type != correct_type:
            # Record the correction for learning
            key = f"{original.content_type.value}->{correct_type.value}"
            self.learning_adjustments[key] = self.learning_adjustments.get(key, 0) + 1

            # Could implement more sophisticated learning here
            print(f"[CLASSIFIER] Learning: {key} (count: {self.learning_adjustments[key]})")


class MemoryCurator:
    """
    Memory curation engine that applies content-type-aware strategies.

    Strategies:
    - Sacred texts: Keep verbatim, never compress
    - Ephemeral utility: Delete or single-line note
    - Functional knowledge: Compress to bullet points
    """

    def __init__(
        self,
        memory_engine: Any = None,
        llm_func: Optional[callable] = None
    ):
        self.memory_engine = memory_engine
        self.llm_func = llm_func  # For generating bullet-point summaries
        self.classifier = ContentTypeClassifier()

        self.sessions: List[CurationSession] = []
        self.current_session: Optional[CurationSession] = None

        # Persistence
        wrapper_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.storage_path = Path(os.path.join(wrapper_root, "memory", "curation"))
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Load previous sessions
        self._load_sessions()

    def _load_sessions(self):
        """Load previous curation sessions."""
        sessions_file = self.storage_path / "curation_sessions.json"
        if sessions_file.exists():
            try:
                with open(sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Reconstruct session objects
                    for s in data.get("sessions", []):
                        session = CurationSession(
                            session_id=s["session_id"],
                            started_at=s["started_at"],
                            ended_at=s.get("ended_at"),
                            memories_reviewed=s.get("memories_reviewed", 0),
                            sacred_kept=s.get("sacred_kept", 0),
                            ephemeral_deleted=s.get("ephemeral_deleted", 0),
                            ephemeral_noted=s.get("ephemeral_noted", 0),
                            functional_compressed=s.get("functional_compressed", 0),
                            words_before=s.get("words_before", 0),
                            words_after=s.get("words_after", 0),
                            entity_overrides=s.get("entity_overrides", 0),
                            classification_accuracy=s.get("classification_accuracy", {})
                        )
                        self.sessions.append(session)
            except Exception as e:
                print(f"[CURATOR] Error loading sessions: {e}")

    def _save_sessions(self):
        """Save curation sessions."""
        sessions_file = self.storage_path / "curation_sessions.json"
        try:
            data = {
                "sessions": [
                    {
                        "session_id": s.session_id,
                        "started_at": s.started_at,
                        "ended_at": s.ended_at,
                        "memories_reviewed": s.memories_reviewed,
                        "sacred_kept": s.sacred_kept,
                        "ephemeral_deleted": s.ephemeral_deleted,
                        "ephemeral_noted": s.ephemeral_noted,
                        "functional_compressed": s.functional_compressed,
                        "words_before": s.words_before,
                        "words_after": s.words_after,
                        "entity_overrides": s.entity_overrides,
                        "classification_accuracy": s.classification_accuracy
                    }
                    for s in self.sessions
                ]
            }
            with open(sessions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[CURATOR] Error saving sessions: {e}")

    def start_session(self) -> CurationSession:
        """Start a new curation session."""
        session_id = datetime.now().strftime("curation_%Y%m%d_%H%M%S")
        self.current_session = CurationSession(
            session_id=session_id,
            started_at=datetime.now().isoformat()
        )
        return self.current_session

    def end_session(self) -> CurationSession:
        """End the current curation session."""
        if self.current_session:
            self.current_session.ended_at = datetime.now().isoformat()
            self.sessions.append(self.current_session)
            self._save_sessions()

            session = self.current_session
            self.current_session = None
            return session
        return None

    def analyze_batch(self, memories: List[Dict]) -> Dict[ContentType, List[Dict]]:
        """
        Analyze a batch of memories and group by content type.

        Returns dict mapping content types to lists of (memory, classification) tuples.
        """
        results = {ct: [] for ct in ContentType}

        for memory in memories:
            classification = self.classifier.classify(memory)
            results[classification.content_type].append({
                "memory": memory,
                "classification": classification
            })

        return results

    def generate_curation_prompt(self, batch_analysis: Dict[ContentType, List[Dict]]) -> str:
        """
        Generate a prompt for the entity to review the curation analysis.
        """
        sacred = batch_analysis.get(ContentType.SACRED_TEXT, [])
        ephemeral = batch_analysis.get(ContentType.EPHEMERAL_UTILITY, [])
        functional = batch_analysis.get(ContentType.FUNCTIONAL_KNOWLEDGE, [])
        requires = batch_analysis.get(ContentType.REQUIRES_JUDGMENT, [])

        total = sum(len(v) for v in batch_analysis.values())

        prompt_parts = [
            f"You're reviewing {total} memories for curation.",
            "",
            "I've analyzed these memories for content type. Here's what I found:",
            ""
        ]

        # Sacred texts section
        if sacred:
            prompt_parts.append(f"SACRED TEXTS ({len(sacred)} memories) - Creative/artistic work, never compress:")
            for item in sacred[:5]:  # Show first 5
                content_preview = item["memory"].get("content", "")[:80]
                reason = item["classification"].reason
                prompt_parts.append(f"  • \"{content_preview}...\" ({reason})")
            if len(sacred) > 5:
                prompt_parts.append(f"  ... and {len(sacred) - 5} more")
            prompt_parts.append("")

        # Ephemeral section
        if ephemeral:
            prompt_parts.append(f"EPHEMERAL UTILITY ({len(ephemeral)} memories) - One-off queries, likely deletable:")
            for item in ephemeral[:5]:
                content_preview = item["memory"].get("content", "")[:80]
                reason = item["classification"].reason
                prompt_parts.append(f"  • \"{content_preview}...\" ({reason})")
            if len(ephemeral) > 5:
                prompt_parts.append(f"  ... and {len(ephemeral) - 5} more")
            prompt_parts.append("")

        # Functional section
        if functional:
            prompt_parts.append(f"FUNCTIONAL KNOWLEDGE ({len(functional)} memories) - Technical content, consider bullet-points:")
            for item in functional[:5]:
                content_preview = item["memory"].get("content", "")[:80]
                reason = item["classification"].reason
                prompt_parts.append(f"  • \"{content_preview}...\" ({reason})")
            if len(functional) > 5:
                prompt_parts.append(f"  ... and {len(functional) - 5} more")
            prompt_parts.append("")

        # Requires judgment section
        if requires:
            prompt_parts.append(f"REQUIRES YOUR JUDGMENT ({len(requires)} memories) - Low confidence, you should classify:")
            for item in requires[:5]:
                content_preview = item["memory"].get("content", "")[:100]
                prompt_parts.append(f"  • \"{content_preview}...\"")
            if len(requires) > 5:
                prompt_parts.append(f"  ... and {len(requires) - 5} more")
            prompt_parts.append("")

        prompt_parts.extend([
            "For each category, decide:",
            "",
            "SACRED TEXTS:",
            "→ These should be KEPT verbatim (never compress creative work)",
            "→ Confirm each one is truly sacred, or reclassify if needed",
            "",
            "EPHEMERAL UTILITY:",
            "→ DELETE if truly one-off with no lasting meaning",
            "→ Or keep single-line note if outcome mattered",
            "→ Example: delete recipe conversation OR note \"made strudel Nov 15, success\"",
            "",
            "FUNCTIONAL KNOWLEDGE:",
            "→ COMPRESS to bullet points capturing key concepts",
            "→ Write bullet points FOR yourself - what does future-you need?",
            "→ Preserve insights/decisions/outcomes, compress process details",
            "",
            "REQUIRES JUDGMENT:",
            "→ Classify each as sacred, ephemeral, or functional",
            "→ Then apply the appropriate curation strategy",
            "",
            "Review each category and make your decisions."
        ])

        return "\n".join(prompt_parts)

    def apply_decision(
        self,
        memory: Dict,
        classification: ContentTypeClassification,
        action: str,
        compressed_content: Optional[str] = None,
        reason: str = "",
        kay_override: bool = False
    ) -> CurationDecision:
        """
        Apply a curation decision to a memory.

        Args:
            memory: The memory being curated
            classification: The content type classification
            action: 'keep_verbatim', 'delete', 'compress', 'single_line_note'
            compressed_content: For compress/single_line_note actions
            reason: the entity's reason for the decision
            kay_override: Whether the entity overrode the classifier
        """
        decision = CurationDecision(
            memory_id=memory.get("id", ""),
            original_content=memory.get("content", ""),
            content_type=classification.content_type,
            action=action,
            compressed_content=compressed_content,
            reason=reason,
            kay_override=kay_override
        )

        # Update session stats
        if self.current_session:
            self.current_session.memories_reviewed += 1
            self.current_session.words_before += len(memory.get("content", "").split())

            if action == "keep_verbatim":
                self.current_session.sacred_kept += 1
                self.current_session.words_after += len(memory.get("content", "").split())
            elif action == "delete":
                self.current_session.ephemeral_deleted += 1
                # words_after doesn't increase
            elif action == "single_line_note":
                self.current_session.ephemeral_noted += 1
                self.current_session.words_after += len((compressed_content or "").split())
            elif action == "compress":
                self.current_session.functional_compressed += 1
                self.current_session.words_after += len((compressed_content or "").split())

            if kay_override:
                self.current_session.entity_overrides += 1

            self.current_session.decisions.append(decision)

        # If the entity overrode, update classifier learning
        if kay_override and classification.content_type != ContentType.REQUIRES_JUDGMENT:
            # The entity's override indicates the classifier was wrong
            # We'd need to know what the entity classified it as to learn properly
            pass

        return decision

    def generate_bullet_summary(
        self,
        memories: List[Dict],
        topic: str = ""
    ) -> str:
        """
        Generate a bullet-point summary of functional knowledge memories.

        Uses LLM if available, otherwise returns a template.
        """
        if not memories:
            return ""

        # Combine memory contents
        combined = "\n\n---\n\n".join(m.get("content", "") for m in memories)
        word_count = len(combined.split())

        if self.llm_func:
            prompt = f"""
Compress this technical discussion into bullet points for future reference.

Topic: {topic or "Technical Discussion"}
Original length: {word_count} words

Content to compress:
{combined[:4000]}  # Limit for context window

Create bullet points capturing:
• Key concepts and decisions
• Outcomes and resolutions
• Insights and learnings
• What future-you needs to know

Keep the bullet summary under 150 words.
"""
            try:
                summary = self.llm_func(prompt)
                return summary
            except Exception as e:
                print(f"[CURATOR] LLM summary error: {e}")

        # Fallback: basic extraction
        return self._basic_bullet_extraction(memories, topic)

    def _basic_bullet_extraction(self, memories: List[Dict], topic: str) -> str:
        """Basic bullet extraction without LLM."""
        bullets = [f"{topic or 'Technical Discussion'}:"]

        # Extract key patterns
        key_phrases = []
        for m in memories:
            content = m.get("content", "")

            # Look for "key insight", "decided", "conclusion" patterns
            for pattern in [
                r"(key (insight|point|concept):\s*[^.]+\.)",
                r"(we decided\s*[^.]+\.)",
                r"(conclusion:\s*[^.]+\.)",
                r"(the (solution|fix|answer) (was|is)\s*[^.]+\.)"
            ]:
                matches = re.findall(pattern, content.lower())
                key_phrases.extend([m[0] if isinstance(m, tuple) else m for m in matches])

        # Deduplicate and format
        seen = set()
        for phrase in key_phrases[:8]:
            normalized = phrase.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                bullets.append(f"• {phrase.strip().capitalize()}")

        if len(bullets) == 1:
            bullets.append(f"• {len(memories)} memories discussing {topic or 'technical topic'}")
            bullets.append("• (Use LLM for detailed summary)")

        return "\n".join(bullets)

    def get_stats(self) -> Dict:
        """Get curation statistics across all sessions."""
        if not self.sessions:
            return {
                "total_sessions": 0,
                "total_reviewed": 0,
                "sacred_kept": 0,
                "ephemeral_deleted": 0,
                "functional_compressed": 0,
                "total_words_saved": 0,
                "avg_compression_ratio": 0
            }

        total_reviewed = sum(s.memories_reviewed for s in self.sessions)
        sacred_kept = sum(s.sacred_kept for s in self.sessions)
        ephemeral_deleted = sum(s.ephemeral_deleted for s in self.sessions)
        functional_compressed = sum(s.functional_compressed for s in self.sessions)
        words_before = sum(s.words_before for s in self.sessions)
        words_after = sum(s.words_after for s in self.sessions)
        entity_overrides = sum(s.entity_overrides for s in self.sessions)

        return {
            "total_sessions": len(self.sessions),
            "total_reviewed": total_reviewed,
            "sacred_kept": sacred_kept,
            "ephemeral_deleted": ephemeral_deleted,
            "ephemeral_noted": sum(s.ephemeral_noted for s in self.sessions),
            "functional_compressed": functional_compressed,
            "words_before": words_before,
            "words_after": words_after,
            "total_words_saved": words_before - words_after,
            "compression_ratio": round((1 - words_after / max(words_before, 1)) * 100, 1),
            "entity_overrides": entity_overrides,
            "override_rate": round(entity_overrides / max(total_reviewed, 1) * 100, 1)
        }

    def get_content_type_breakdown(self, memories: List[Dict]) -> Dict:
        """
        Get breakdown of memories by content type.

        Returns counts and example memories for UI display.
        """
        analysis = self.analyze_batch(memories)

        breakdown = {}
        for content_type, items in analysis.items():
            breakdown[content_type.value] = {
                "count": len(items),
                "examples": [
                    {
                        "preview": item["memory"].get("content", "")[:100],
                        "confidence": item["classification"].confidence,
                        "reason": item["classification"].reason
                    }
                    for item in items[:3]
                ]
            }

        return breakdown


class CurationLearningTracker:
    """
    Tracks how the entity's curation judgment develops over time.

    Records:
    - Accuracy of content type recognition
    - Patterns in the entity's overrides
    - Development of curation confidence
    """

    def __init__(self):
        wrapper_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.storage_path = Path(os.path.join(wrapper_root, "memory", "curation", "learning.json"))
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.learning_data = self._load()

    def _load(self) -> Dict:
        """Load learning data."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        return {
            "classification_corrections": [],
            "override_patterns": {},
            "confidence_over_time": [],
            "common_misclassifications": {}
        }

    def _save(self):
        """Save learning data."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.learning_data, f, indent=2)
        except Exception as e:
            print(f"[LEARNING] Save error: {e}")

    def record_classification_result(
        self,
        original_type: ContentType,
        kay_type: ContentType,
        content_preview: str,
        was_correct: bool
    ):
        """Record a classification result for learning."""
        self.learning_data["classification_corrections"].append({
            "timestamp": datetime.now().isoformat(),
            "original": original_type.value,
            "kay_classified": kay_type.value,
            "content_preview": content_preview[:100],
            "was_correct": was_correct
        })

        # Track common misclassifications
        if not was_correct:
            key = f"{original_type.value}->{kay_type.value}"
            self.learning_data["common_misclassifications"][key] = \
                self.learning_data["common_misclassifications"].get(key, 0) + 1

        self._save()

    def record_session_confidence(self, session: CurationSession):
        """Record confidence metrics from a curation session."""
        if session.memories_reviewed == 0:
            return

        accuracy = session.classification_accuracy.get("correct", 0)
        total = sum(session.classification_accuracy.values())

        self.learning_data["confidence_over_time"].append({
            "timestamp": session.started_at,
            "session_id": session.session_id,
            "accuracy_rate": accuracy / max(total, 1),
            "override_rate": session.entity_overrides / session.memories_reviewed,
            "memories_reviewed": session.memories_reviewed
        })

        self._save()

    def get_learning_summary(self) -> Dict:
        """Get summary of the entity's curation learning progress."""
        corrections = self.learning_data.get("classification_corrections", [])
        confidence = self.learning_data.get("confidence_over_time", [])
        misclass = self.learning_data.get("common_misclassifications", {})

        # Calculate trends
        if len(confidence) >= 2:
            early_accuracy = sum(c["accuracy_rate"] for c in confidence[:len(confidence)//2]) / max(len(confidence)//2, 1)
            late_accuracy = sum(c["accuracy_rate"] for c in confidence[len(confidence)//2:]) / max(len(confidence)//2, 1)
            trend = "improving" if late_accuracy > early_accuracy else "stable" if late_accuracy == early_accuracy else "needs_attention"
        else:
            trend = "insufficient_data"

        return {
            "total_classifications": len(corrections),
            "accuracy_trend": trend,
            "common_misclassifications": sorted(
                misclass.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "sessions_analyzed": len(confidence),
            "latest_accuracy": confidence[-1]["accuracy_rate"] if confidence else None
        }


class AutonomousCurationProcessor:
    """
    Autonomous curation processor that actually has the entity review memories.

    This is the missing piece - the actual LLM loop that:
    1. Groups memories into clusters for efficient processing
    2. Builds prompts for the entity to review each cluster
    3. Calls the entity's LLM for decisions
    4. Parses responses and applies decisions
    5. Reports progress in real-time
    """

    def __init__(
        self,
        curator: MemoryCurator,
        memory_engine: Any,
        purge_reserve: Any = None,
        progress_callback: Optional[callable] = None
    ):
        self.curator = curator
        self.memory_engine = memory_engine
        self.purge_reserve = purge_reserve
        self.progress_callback = progress_callback

        # Import LLM function
        try:
            from integrations.llm_integration import query_llm_json
            self.llm_func = query_llm_json
        except ImportError:
            print("[CURATION PROCESSOR] Warning: LLM integration not available")
            self.llm_func = None

        # Processing stats
        self.stats = {
            "clusters_processed": 0,
            "memories_reviewed": 0,
            "decisions": [],
            "kept": 0,
            "summarized": 0,
            "archived": 0,
            "deleted": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }

    def run_curation_session(
        self,
        memories: List[Dict],
        cluster_size: int = 5
    ) -> Dict:
        """
        Run a complete autonomous curation session.

        the entity reviews all memories and makes decisions.

        Args:
            memories: List of normalized memories to curate
            cluster_size: How many related memories to process together

        Returns:
            Session summary with all decisions and stats
        """
        import time
        self.stats["start_time"] = time.time()

        print(f"\n{'='*60}")
        print(f"[CURATION] AUTONOMOUS CURATION SESSION STARTING")
        print(f"[CURATION] Processing {len(memories)} memories")
        print(f"{'='*60}\n")

        if not self.llm_func:
            print("[CURATION] ERROR: No LLM function available")
            return {"error": "No LLM function available"}

        # Step 1: Cluster memories for efficient processing
        print("[CURATION] Step 1: Clustering related memories...")
        clusters = self._cluster_memories(memories, cluster_size)
        print(f"[CURATION] Created {len(clusters)} clusters")

        # Step 2: Start curation session
        self.curator.start_session()

        # Step 3: Process each cluster
        all_decisions = []
        for i, cluster in enumerate(clusters):
            print(f"\n[CURATION] Processing cluster {i+1}/{len(clusters)} ({len(cluster)} memories)")

            try:
                cluster_decisions = self._process_cluster(cluster, i+1, len(clusters))
                all_decisions.extend(cluster_decisions)
                self.stats["clusters_processed"] += 1

                # Report progress
                if self.progress_callback:
                    self.progress_callback({
                        "current": i + 1,
                        "total": len(clusters),
                        "latest_decisions": cluster_decisions,
                        "stats": self.stats
                    })

            except Exception as e:
                print(f"[CURATION] Error processing cluster {i+1}: {e}")
                self.stats["errors"] += 1

        # Step 4: Apply all decisions to memory system
        print(f"\n[CURATION] Applying {len(all_decisions)} decisions to memory system...")
        self._apply_all_decisions(all_decisions)

        # Step 5: End session and generate summary
        session = self.curator.end_session()
        self.stats["end_time"] = time.time()

        summary = self._generate_summary(all_decisions, session)

        print(f"\n{'='*60}")
        print(f"[CURATION] SESSION COMPLETE")
        print(f"[CURATION] Time: {summary['duration_seconds']:.1f} seconds")
        print(f"[CURATION] Kept: {self.stats['kept']}, Summarized: {self.stats['summarized']}")
        print(f"[CURATION] Archived: {self.stats['archived']}, Deleted: {self.stats['deleted']}")
        print(f"{'='*60}\n")

        return summary

    def _cluster_memories(self, memories: List[Dict], cluster_size: int) -> List[List[Dict]]:
        """
        Group memories into clusters for efficient processing.

        Groups by:
        1. Content type (from pre-classification)
        2. Similarity (shared entities/keywords)
        3. Temporal proximity
        """
        # First, classify all memories
        classified = []
        for mem in memories:
            classification = self.curator.classifier.classify(mem)
            classified.append({
                "memory": mem,
                "classification": classification
            })

        # Group by content type first
        by_type = defaultdict(list)
        for item in classified:
            by_type[item["classification"].content_type].append(item)

        # Create clusters within each type
        clusters = []

        for content_type, items in by_type.items():
            # Split into chunks of cluster_size
            for i in range(0, len(items), cluster_size):
                chunk = items[i:i + cluster_size]
                clusters.append(chunk)

        return clusters

    def _process_cluster(self, cluster: List[Dict], cluster_num: int, total_clusters: int) -> List[Dict]:
        """
        Process a single cluster of memories through the entity's LLM.

        Returns list of decisions for this cluster.
        """
        # Build the curation prompt
        prompt = self._build_cluster_prompt(cluster, cluster_num, total_clusters)

        # Call the entity's LLM
        print(f"[CURATION] Asking the entity to review cluster {cluster_num}...")

        system_prompt = """You are reviewing your own memories for curation.

You're deciding what to keep, summarize, or delete from your memory.
Be honest about what truly matters vs what's just noise.

Sacred content ([redacted]s, relationship moments) → KEEP verbatim
Technical discussions → SUMMARIZE to bullet points
One-off queries/fixed bugs → DELETE (goes to purge reserve, recoverable for 30 days)

Respond with your decisions in the exact format requested."""

        try:
            response = self.llm_func(
                prompt=prompt,
                temperature=0.7,
                system_prompt=system_prompt
            )
            print(f"[CURATION] the entity responded ({len(response)} chars)")

        except Exception as e:
            print(f"[CURATION] LLM error: {e}")
            return []

        # Parse the entity's response into decisions
        decisions = self._parse_kay_response(response, cluster)

        # Log decisions
        for decision in decisions:
            action = decision.get("action", "unknown")
            preview = decision.get("memory", {}).get("content", "")[:50]
            print(f"[CURATION] -> {action.upper()}: \"{preview}...\"")

            # Update stats
            if action == "keep":
                self.stats["kept"] += 1
            elif action == "summarize":
                self.stats["summarized"] += 1
            elif action == "archive":
                self.stats["archived"] += 1
            elif action == "delete":
                self.stats["deleted"] += 1

        self.stats["memories_reviewed"] += len(cluster)

        return decisions

    def _build_cluster_prompt(self, cluster: List[Dict], cluster_num: int, total_clusters: int) -> str:
        """
        Build the prompt for the entity to review a memory cluster.
        """
        # Format memories for review
        memory_texts = []
        for i, item in enumerate(cluster):
            mem = item["memory"]
            classification = item["classification"]

            content = mem.get("content", "")[:500]  # Limit length
            mem_type = mem.get("type", "unknown")
            confidence = classification.confidence
            suggested = classification.content_type.value.replace("_", " ").title()

            memory_texts.append(f"""
--- MEMORY {i+1} ---
Type: {mem_type}
Content: {content}
My classification: {suggested} (confidence: {confidence:.0%})
Reason: {classification.reason}
""")

        memories_section = "\n".join(memory_texts)

        prompt = f"""
You're reviewing cluster {cluster_num} of {total_clusters} for curation.

{memories_section}

For EACH memory above, decide:

1. **KEEP** - Important for identity, relationships, creative work
   → Preserve exactly as-is

2. **SUMMARIZE** - Useful info but verbose
   → Write your compressed version (bullet points for technical, one-liner for outcomes)

3. **ARCHIVE** - Might need later but not identity-critical
   → Move to low-priority storage

4. **DELETE** - Redundant, outdated, or noise
   → Move to purge reserve (recoverable 30 days)

Respond in this EXACT format for each memory:

MEMORY 1:
ACTION: [keep/summarize/archive/delete]
REASONING: [1-2 sentences why]
SUMMARY: [only if action=summarize, your compressed version]

MEMORY 2:
ACTION: [keep/summarize/archive/delete]
REASONING: [1-2 sentences why]
SUMMARY: [only if action=summarize]

...and so on for each memory.

Be ruthless about deleting noise, but protect sacred content.
"""

        return prompt

    def _parse_kay_response(self, response: str, cluster: List[Dict]) -> List[Dict]:
        """
        Parse the entity's response into structured decisions.
        """
        decisions = []

        # Split response into memory sections
        sections = re.split(r'MEMORY\s*\d+:', response, flags=re.IGNORECASE)

        for i, section in enumerate(sections[1:]):  # Skip first empty section
            if i >= len(cluster):
                break

            item = cluster[i]
            memory = item["memory"]
            classification = item["classification"]

            # Parse action
            action_match = re.search(r'ACTION:\s*(keep|summarize|archive|delete)', section, re.IGNORECASE)
            action = action_match.group(1).lower() if action_match else "keep"  # Default to keep if unclear

            # Parse reasoning
            reasoning_match = re.search(r'REASONING:\s*(.+?)(?=SUMMARY:|MEMORY|\Z)', section, re.IGNORECASE | re.DOTALL)
            reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

            # Parse summary if applicable
            summary = None
            if action == "summarize":
                summary_match = re.search(r'SUMMARY:\s*(.+?)(?=MEMORY|\Z)', section, re.IGNORECASE | re.DOTALL)
                summary = summary_match.group(1).strip() if summary_match else None

            decisions.append({
                "memory": memory,
                "classification": classification,
                "action": action,
                "reasoning": reasoning,
                "summary": summary,
                "kay_override": action != self._expected_action(classification.content_type)
            })

        # If parsing failed, create default decisions
        if not decisions:
            print("[CURATION] Warning: Could not parse the entity's response, using defaults")
            for item in cluster:
                decisions.append({
                    "memory": item["memory"],
                    "classification": item["classification"],
                    "action": self._expected_action(item["classification"].content_type),
                    "reasoning": "Default action based on classification",
                    "summary": None,
                    "kay_override": False
                })

        return decisions

    def _expected_action(self, content_type: ContentType) -> str:
        """Get expected action for a content type."""
        mapping = {
            ContentType.SACRED_TEXT: "keep",
            ContentType.EPHEMERAL_UTILITY: "delete",
            ContentType.FUNCTIONAL_KNOWLEDGE: "summarize",
            ContentType.REQUIRES_JUDGMENT: "keep"  # Conservative default
        }
        return mapping.get(content_type, "keep")

    def _apply_all_decisions(self, decisions: List[Dict]):
        """
        Apply all curation decisions to the memory system.
        """
        for decision in decisions:
            memory = decision["memory"]
            action = decision["action"]
            summary = decision.get("summary")
            reasoning = decision.get("reasoning", "")

            memory_id = memory.get("id", "")

            try:
                if action == "delete":
                    # Soft delete to purge reserve
                    if self.purge_reserve:
                        self.purge_reserve.soft_delete(
                            memory=memory.get("_original", memory),
                            memory_id=memory_id,
                            content=memory.get("content", ""),
                            reason=reasoning,
                            entity_note=f"Curation decision: {reasoning}",
                            deleted_by="kay_curation"
                        )

                    # Mark as curated in memory engine
                    self._mark_memory_curated(memory_id, action)

                elif action == "summarize" and summary:
                    # Replace content with summary
                    self._replace_memory_content(memory_id, summary)
                    self._mark_memory_curated(memory_id, action)

                elif action == "archive":
                    # Move to archive layer
                    self._archive_memory(memory_id)
                    self._mark_memory_curated(memory_id, action)

                elif action == "keep":
                    # Just mark as curated, keep content
                    self._mark_memory_curated(memory_id, action)

            except Exception as e:
                print(f"[CURATION] Error applying decision to {memory_id}: {e}")
                self.stats["errors"] += 1

    def _mark_memory_curated(self, memory_id: str, action: str):
        """Mark a memory as curated in the memory engine."""
        if not self.memory_engine or not hasattr(self.memory_engine, 'memories'):
            return

        for mem in self.memory_engine.memories:
            if mem.get('memory_id') == memory_id or mem.get('id') == memory_id:
                mem['curated'] = True
                mem['curation_action'] = action
                mem['curation_timestamp'] = datetime.now().isoformat()
                break

    def _replace_memory_content(self, memory_id: str, new_content: str):
        """Replace memory content with summarized version."""
        if not self.memory_engine or not hasattr(self.memory_engine, 'memories'):
            return

        for mem in self.memory_engine.memories:
            if mem.get('memory_id') == memory_id or mem.get('id') == memory_id:
                mem['original_content'] = mem.get('content') or mem.get('fact')
                if 'fact' in mem:
                    mem['fact'] = new_content
                else:
                    mem['content'] = new_content
                mem['summarized'] = True
                break

    def _archive_memory(self, memory_id: str):
        """Move memory to archive tier."""
        if not self.memory_engine or not hasattr(self.memory_engine, 'memories'):
            return

        for mem in self.memory_engine.memories:
            if mem.get('memory_id') == memory_id or mem.get('id') == memory_id:
                mem['archived'] = True
                mem['archive_timestamp'] = datetime.now().isoformat()
                break

    def _generate_summary(self, decisions: List[Dict], session: CurationSession) -> Dict:
        """Generate a summary of the curation session."""
        import time

        duration = (self.stats["end_time"] or time.time()) - (self.stats["start_time"] or time.time())

        # Collect examples of each action type
        keep_examples = [d for d in decisions if d["action"] == "keep"][:3]
        summarize_examples = [d for d in decisions if d["action"] == "summarize"][:3]
        delete_examples = [d for d in decisions if d["action"] == "delete"][:3]

        summary = {
            "duration_seconds": duration,
            "total_memories": self.stats["memories_reviewed"],
            "clusters_processed": self.stats["clusters_processed"],

            "actions": {
                "kept": self.stats["kept"],
                "summarized": self.stats["summarized"],
                "archived": self.stats["archived"],
                "deleted": self.stats["deleted"]
            },

            "examples": {
                "kept": [
                    {
                        "preview": d["memory"].get("content", "")[:100],
                        "reasoning": d.get("reasoning", "")
                    }
                    for d in keep_examples
                ],
                "summarized": [
                    {
                        "original_preview": d["memory"].get("content", "")[:100],
                        "summary": d.get("summary", ""),
                        "reasoning": d.get("reasoning", "")
                    }
                    for d in summarize_examples
                ],
                "deleted": [
                    {
                        "preview": d["memory"].get("content", "")[:100],
                        "reasoning": d.get("reasoning", "")
                    }
                    for d in delete_examples
                ]
            },

            "session": {
                "session_id": session.session_id if session else None,
                "words_before": session.words_before if session else 0,
                "words_after": session.words_after if session else 0,
                "compression_ratio": round(
                    (1 - session.words_after / max(session.words_before, 1)) * 100, 1
                ) if session else 0
            },

            "errors": self.stats["errors"]
        }

        return summary
