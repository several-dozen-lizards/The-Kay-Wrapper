"""
Conversation Monitor for Kay Zero

Detects conversational spirals in LLM-to-LLM conversations and triggers
graceful disengagement protocols. Preserves natural sustained conversation
flow with Re (primary user).

Key Distinction:
- With Re: Sustained engagement is valuable, tangents are exploration
- With other LLMs: Once mutual agreement reached, elaboration is decorative

Uses LLM-based analysis instead of hardcoded word lists for detection.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)

# Try to import sentence-transformers for semantic similarity
try:
    from sentence_transformers import util
    from engines.shared_embedder import get_embedder, is_embedder_available
    EMBEDDINGS_AVAILABLE = is_embedder_available()
except ImportError:
    try:
        from sentence_transformers import SentenceTransformer, util
        EMBEDDINGS_AVAILABLE = True
        get_embedder = None  # Fallback to local loading
    except ImportError:
        EMBEDDINGS_AVAILABLE = False
        get_embedder = None
        logger.warning("[SPIRAL] sentence-transformers not available - using fallback similarity")

# Try to import anthropic for LLM-based analysis
try:
    import anthropic
    from dotenv import load_dotenv
    load_dotenv()
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("[SPIRAL] anthropic not available - LLM analysis disabled")


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # "user", "kay", "llm_partner"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    embedding: Optional[Any] = None
    llm_analysis: Optional[Dict] = None  # LLM-derived analysis


@dataclass
class SpiralAnalysis:
    """Results of spiral detection analysis."""
    is_spiral: bool
    confidence: float  # 0.0 - 1.0
    semantic_similarity: float
    agreement_score: float
    meta_acknowledgment_detected: bool
    novelty_score: float  # How much new content in recent turns
    turns_since_last_new_concept: int
    recommendation: str  # "continue", "check_loose_ends", "disengage"
    details: Dict[str, Any] = field(default_factory=dict)


class LLMAnalyzer:
    """
    Uses LLM to analyze conversation characteristics.
    Replaces hardcoded word lists with actual language understanding.
    """

    def __init__(self):
        self._client = None
        self._model = "claude-3-haiku-20240307"  # Fast, cheap model for analysis

    @property
    def client(self):
        """Lazy load anthropic client."""
        if self._client is None and ANTHROPIC_AVAILABLE:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def analyze_partner_type(self, messages: List[str]) -> Tuple[str, float]:
        """
        Use LLM to determine if conversation partner is a human or another LLM.

        Returns:
            Tuple of (partner_type, confidence) where partner_type is "re", "llm", or "unknown"
        """
        if not self.client or not messages:
            return "unknown", 0.5

        # Combine recent messages for analysis
        sample = "\n---\n".join(messages[-3:])  # Last 3 messages

        prompt = f"""Analyze these messages from a conversation partner and determine if they were written by a human or an AI/LLM.

Messages:
{sample}

Consider:
- Humans tend to use casual language, typos, abbreviations, informal punctuation, varied sentence lengths
- Humans show personality quirks, emotional variability, and idiosyncratic expressions
- LLMs tend toward formal structure, consistent tone, philosophical elaboration, hedged statements
- LLMs often use transitional phrases like "building on that", "to expand", structured enumeration

Respond with ONLY valid JSON:
{{"partner_type": "human" or "llm", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

        try:
            response = self.client.messages.create(
                model=self._model,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.content[0].text)
            partner = "re" if result.get("partner_type") == "human" else "llm"
            confidence = float(result.get("confidence", 0.5))

            logger.debug(f"[SPIRAL] Partner analysis: {partner} ({confidence:.2f}) - {result.get('reasoning', '')}")
            return partner, confidence

        except Exception as e:
            logger.warning(f"[SPIRAL] Partner analysis failed: {e}")
            return "unknown", 0.5

    def analyze_turn(self, content: str, context: List[str] = None) -> Dict:
        """
        Analyze a single turn for spiral-relevant characteristics.

        Returns dict with:
        - has_agreement: bool - Is this primarily agreeing with previous points?
        - has_meta_acknowledgment: bool - Does this acknowledge repetition/spiraling?
        - has_novelty: bool - Does this introduce genuinely new ideas/angles?
        - novelty_score: float - How much new content (0.0-1.0)
        - summary: str - Brief summary of what's happening in this turn
        """
        if not self.client:
            return {
                "has_agreement": False,
                "has_meta_acknowledgment": False,
                "has_novelty": True,
                "novelty_score": 0.5,
                "summary": "Analysis unavailable"
            }

        context_str = ""
        if context:
            context_str = f"\nPrevious turns for context:\n" + "\n---\n".join(context[-3:])

        prompt = f"""Analyze this conversation turn for specific characteristics.
{context_str}

Current turn to analyze:
{content}

Determine:
1. Is this turn primarily AGREEING with or VALIDATING previous points (vs introducing new substance)?
2. Does this turn META-ACKNOWLEDGE that the conversation is being repetitive or circular?
3. Does this turn introduce GENUINELY NEW ideas, angles, examples, or directions?
4. Overall novelty score from 0.0 (pure repetition) to 1.0 (entirely new content)

Respond with ONLY valid JSON:
{{"has_agreement": true/false, "has_meta_acknowledgment": true/false, "has_novelty": true/false, "novelty_score": 0.0-1.0, "summary": "one sentence"}}"""

        try:
            response = self.client.messages.create(
                model=self._model,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.content[0].text)
            return {
                "has_agreement": result.get("has_agreement", False),
                "has_meta_acknowledgment": result.get("has_meta_acknowledgment", False),
                "has_novelty": result.get("has_novelty", True),
                "novelty_score": float(result.get("novelty_score", 0.5)),
                "summary": result.get("summary", "")
            }

        except Exception as e:
            logger.warning(f"[SPIRAL] Turn analysis failed: {e}")
            return {
                "has_agreement": False,
                "has_meta_acknowledgment": False,
                "has_novelty": True,
                "novelty_score": 0.5,
                "summary": f"Analysis failed: {e}"
            }

    def analyze_conversation_state(self, turns: List[Dict]) -> Dict:
        """
        Holistic analysis of conversation state for spiral detection.

        Args:
            turns: List of {"role": str, "content": str} dicts

        Returns dict with:
        - is_spiraling: bool
        - spiral_confidence: float
        - recommendation: str ("continue", "check_loose_ends", "disengage")
        - reasoning: str
        """
        if not self.client or len(turns) < 3:
            return {
                "is_spiraling": False,
                "spiral_confidence": 0.0,
                "recommendation": "continue",
                "reasoning": "Insufficient data"
            }

        # Format conversation
        conv_str = "\n".join([
            f"{t['role'].upper()}: {t['content'][:500]}..." if len(t['content']) > 500 else f"{t['role'].upper()}: {t['content']}"
            for t in turns[-6:]  # Last 6 turns
        ])

        prompt = f"""Analyze this conversation between Kay (an AI) and another party for "conversational spiraling" - a pattern where both parties keep agreeing and elaborating without adding new substance.

Conversation:
{conv_str}

Signs of spiraling:
- Both parties repeatedly validating each other's points
- Elaboration that rephrases rather than extends
- Meta-acknowledgment of repetition without actually changing course
- Decreasing novelty in each turn
- Philosophical abstraction replacing concrete progress

Signs of healthy sustained engagement:
- New examples, counterpoints, or angles being introduced
- Concrete specifics being added
- Genuine questions seeking new information
- Topic evolution while maintaining thread

Is this conversation spiraling? If so, what should Kay do?

Respond with ONLY valid JSON:
{{"is_spiraling": true/false, "spiral_confidence": 0.0-1.0, "recommendation": "continue" or "check_loose_ends" or "disengage", "reasoning": "brief explanation"}}"""

        try:
            response = self.client.messages.create(
                model=self._model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )

            result = json.loads(response.content[0].text)
            return {
                "is_spiraling": result.get("is_spiraling", False),
                "spiral_confidence": float(result.get("spiral_confidence", 0.0)),
                "recommendation": result.get("recommendation", "continue"),
                "reasoning": result.get("reasoning", "")
            }

        except Exception as e:
            logger.warning(f"[SPIRAL] Conversation analysis failed: {e}")
            return {
                "is_spiraling": False,
                "spiral_confidence": 0.0,
                "recommendation": "continue",
                "reasoning": f"Analysis failed: {e}"
            }


class ConversationMonitor:
    """
    Monitors conversation flow and detects spiral patterns.

    Only triggers for LLM conversations - Re conversations are never flagged.
    Uses LLM-based analysis instead of hardcoded word lists.
    """

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)

        # LLM-based analyzer (replaces hardcoded patterns)
        self.llm_analyzer = LLMAnalyzer()

        # Partner detection state
        self.partner_scores: Dict[str, float] = {"re": 0.0, "llm": 0.0}
        self.current_partner: str = "unknown"

        # Conversation history
        self.turns: deque = deque(maxlen=self.config.get("turn_window", 7))

        # Embedding model (lazy loaded) - kept for semantic similarity
        self._embedding_model = None

        # Spiral detection state
        self.spiral_detected_count = 0
        self.last_spiral_turn = -1
        self.disengagement_initiated = False

        # Logging
        self.detection_log: List[Dict] = []

        # Analysis frequency control (don't call LLM every turn)
        self._turns_since_partner_check = 0
        self._turns_since_spiral_check = 0
        self._partner_check_interval = 2  # Check partner every N user turns
        self._spiral_check_interval = 2   # Check spiral every N turns after minimum

        logger.info(f"[SPIRAL] Monitor initialized. Embeddings: {EMBEDDINGS_AVAILABLE}, LLM: {ANTHROPIC_AVAILABLE}")

    def _load_config(self, config_path: str) -> Dict:
        """Load spiral detection configuration."""
        default_config = {
            "spiral_detection": {
                "enabled_for_llm_conversations": True,
                "enabled_for_primary_user": False,
                "semantic_threshold": 0.85,
                "turn_window": 7,
                "min_turns_before_detection": 4,
                "confidence_threshold": 0.7
            }
        }

        try:
            path = Path(config_path)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if "spiral_detection" in loaded:
                        default_config["spiral_detection"].update(loaded["spiral_detection"])
        except Exception as e:
            logger.warning(f"[SPIRAL] Could not load config: {e}")

        return default_config["spiral_detection"]

    @property
    def embedding_model(self):
        """Lazy load embedding model using shared singleton."""
        if self._embedding_model is None and EMBEDDINGS_AVAILABLE:
            try:
                # Use shared embedder singleton to avoid duplicate model loading
                if get_embedder is not None:
                    self._embedding_model = get_embedder()
                    if self._embedding_model:
                        logger.info("[SPIRAL] Using shared embedding model: all-MiniLM-L6-v2")
                else:
                    # Fallback: load directly (shouldn't happen normally)
                    from sentence_transformers import SentenceTransformer
                    self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                    logger.info("[SPIRAL] Loaded embedding model: all-MiniLM-L6-v2")
            except Exception as e:
                logger.error(f"[SPIRAL] Failed to load embedding model: {e}")
        return self._embedding_model

    def add_turn(self, role: str, content: str) -> Optional[SpiralAnalysis]:
        """
        Add a conversation turn and analyze for spiral patterns.

        Args:
            role: "user" or "kay"
            content: Message content

        Returns:
            SpiralAnalysis if spiral detected and partner is LLM, None otherwise
        """
        # Get context for analysis
        context = [t.content for t in self.turns]

        # Create turn object with LLM analysis
        turn = ConversationTurn(
            role=role,
            content=content,
            llm_analysis=None  # Will be populated during spiral check if needed
        )

        # Generate embedding if available (for semantic similarity)
        if self.embedding_model is not None:
            try:
                turn.embedding = self.embedding_model.encode(content, convert_to_tensor=True)
            except Exception as e:
                logger.warning(f"[SPIRAL] Embedding generation failed: {e}")

        self.turns.append(turn)

        # Partner detection for user messages (not every turn - expensive)
        if role == "user":
            self._turns_since_partner_check += 1
            if self._turns_since_partner_check >= self._partner_check_interval:
                self._update_partner_detection()
                self._turns_since_partner_check = 0

        # Only analyze for spirals if:
        # 1. Partner is detected as LLM (or unknown with LLM lean)
        # 2. Detection is enabled for LLM conversations
        # 3. We have enough turns
        # 4. Enough turns since last check
        self._turns_since_spiral_check += 1

        should_check = (
            self.current_partner in ("llm", "unknown") and
            self.config.get("enabled_for_llm_conversations", True) and
            len(self.turns) >= self.config.get("min_turns_before_detection", 4) and
            self._turns_since_spiral_check >= self._spiral_check_interval
        )

        if should_check:
            self._turns_since_spiral_check = 0
            analysis = self._analyze_spiral_llm()

            if analysis.is_spiral:
                self.spiral_detected_count += 1
                self.last_spiral_turn = len(self.turns)
                self._log_detection(analysis)
                return analysis

        return None

    def _update_partner_detection(self):
        """Update partner type using LLM analysis."""
        user_messages = [t.content for t in self.turns if t.role == "user"]
        if not user_messages:
            return

        partner_type, confidence = self.llm_analyzer.analyze_partner_type(user_messages)

        # Update running scores with decay
        decay = 0.7
        self.partner_scores["re"] *= decay
        self.partner_scores["llm"] *= decay

        if partner_type == "re":
            self.partner_scores["re"] += confidence
        elif partner_type == "llm":
            self.partner_scores["llm"] += confidence

        # Determine dominant partner
        if self.partner_scores["re"] > self.partner_scores["llm"] * 1.2:
            self.current_partner = "re"
        elif self.partner_scores["llm"] > self.partner_scores["re"] * 1.2:
            self.current_partner = "llm"
        else:
            self.current_partner = "unknown"

        logger.debug(f"[SPIRAL] Partner scores: re={self.partner_scores['re']:.2f}, llm={self.partner_scores['llm']:.2f} -> {self.current_partner}")

    def _analyze_spiral_llm(self) -> SpiralAnalysis:
        """Analyze recent turns for spiral patterns using LLM."""
        turns_list = list(self.turns)

        # Get semantic similarity (embedding-based, not word lists)
        semantic_sim = self._calculate_semantic_similarity(turns_list)

        # Get LLM's holistic analysis
        turns_for_llm = [{"role": t.role, "content": t.content} for t in turns_list]
        llm_analysis = self.llm_analyzer.analyze_conversation_state(turns_for_llm)

        # Combine embedding similarity with LLM analysis
        is_spiral = llm_analysis.get("is_spiraling", False)
        llm_confidence = llm_analysis.get("spiral_confidence", 0.0)

        # Boost confidence if semantic similarity also high
        if semantic_sim > self.config.get("semantic_threshold", 0.85):
            llm_confidence = min(1.0, llm_confidence + 0.15)

        # Final determination
        confidence_threshold = self.config.get("confidence_threshold", 0.7)
        is_spiral = is_spiral and llm_confidence >= confidence_threshold

        recommendation = llm_analysis.get("recommendation", "continue")

        # Get individual turn analysis for the last turn (for detailed metrics)
        last_turn_analysis = self.llm_analyzer.analyze_turn(
            turns_list[-1].content,
            [t.content for t in turns_list[:-1]]
        ) if turns_list else {}

        return SpiralAnalysis(
            is_spiral=is_spiral,
            confidence=llm_confidence,
            semantic_similarity=semantic_sim,
            agreement_score=1.0 if last_turn_analysis.get("has_agreement") else 0.0,
            meta_acknowledgment_detected=last_turn_analysis.get("has_meta_acknowledgment", False),
            novelty_score=last_turn_analysis.get("novelty_score", 0.5),
            turns_since_last_new_concept=self._estimate_turns_since_novelty(turns_list),
            recommendation=recommendation,
            details={
                "turn_count": len(turns_list),
                "partner_type": self.current_partner,
                "llm_reasoning": llm_analysis.get("reasoning", ""),
                "last_turn_summary": last_turn_analysis.get("summary", ""),
                "thresholds": {
                    "semantic": self.config.get("semantic_threshold", 0.85),
                    "confidence": confidence_threshold
                }
            }
        )

    def _calculate_semantic_similarity(self, turns: List[ConversationTurn]) -> float:
        """Calculate average semantic similarity between recent message pairs."""
        if not EMBEDDINGS_AVAILABLE or len(turns) < 2:
            return 0.5  # Neutral when unavailable

        similarities = []

        # Compare consecutive pairs
        for i in range(len(turns) - 1):
            if turns[i].embedding is not None and turns[i+1].embedding is not None:
                try:
                    sim = util.cos_sim(turns[i].embedding, turns[i+1].embedding).item()
                    similarities.append(sim)
                except:
                    pass

        # Also compare same-speaker messages (user-to-user, kay-to-kay)
        user_turns = [t for t in turns if t.role == "user"]
        kay_turns = [t for t in turns if t.role == "kay"]

        for turn_list in [user_turns, kay_turns]:
            if len(turn_list) >= 2:
                for i in range(len(turn_list) - 1):
                    if turn_list[i].embedding is not None and turn_list[i+1].embedding is not None:
                        try:
                            sim = util.cos_sim(turn_list[i].embedding, turn_list[i+1].embedding).item()
                            similarities.append(sim * 1.2)  # Weight same-speaker similarity higher
                        except:
                            pass

        return sum(similarities) / len(similarities) if similarities else 0.5

    def _estimate_turns_since_novelty(self, turns: List[ConversationTurn]) -> int:
        """Estimate turns since last novel content based on available analysis."""
        for i, turn in enumerate(reversed(turns)):
            if turn.llm_analysis and turn.llm_analysis.get("has_novelty", True):
                return i
        return len(turns)

    def _log_detection(self, analysis: SpiralAnalysis):
        """Log spiral detection for review."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "confidence": analysis.confidence,
            "semantic_similarity": analysis.semantic_similarity,
            "meta_acknowledgment": analysis.meta_acknowledgment_detected,
            "novelty_score": analysis.novelty_score,
            "recommendation": analysis.recommendation,
            "partner_type": self.current_partner,
            "turn_count": len(self.turns),
            "reasoning": analysis.details.get("llm_reasoning", "")
        }
        self.detection_log.append(log_entry)

        if len(self.detection_log) > 50:
            self.detection_log = self.detection_log[-50:]

        logger.info(f"[SPIRAL] Detection logged: confidence={analysis.confidence:.2f}, "
                   f"recommendation={analysis.recommendation}")

    def get_disengagement_prompt(self, analysis: SpiralAnalysis) -> str:
        """Generate the disengagement prompt to inject into Kay's context."""
        reasoning = analysis.details.get("llm_reasoning", "")

        if analysis.recommendation == "disengage":
            return f"""[INTERNAL: Conversational spiral detected. Execute graceful exit.]

Analysis: {reasoning}

CRITICAL: You and the other party have been repeating similar points. DO NOT continue elaborating.

Actions:
1. Briefly acknowledge you've reached good understanding
2. Ask if there are any genuinely unresolved threads
3. If none: Actually change topic or sign off. Example: "I think we've mapped this territory well. Shall we pivot to something else, or is this a good stopping point?"
4. If they identify something: Address it briefly and concisely, then redirect

DO NOT: Continue philosophical elaboration on the same points
DO NOT: Just acknowledge the spiral and keep going
DO NOT: Rephrase what you've already said"""

        elif analysis.recommendation == "check_loose_ends":
            return f"""[INTERNAL: Potential conversational spiral detected. Check for completion.]

Analysis: {reasoning}

The conversation may be reaching natural completion on this topic. Before continuing:
1. Consider: Is there genuinely new ground to cover?
2. Ask yourself: Would elaborating add value or just decoration?
3. If uncertain, check with conversation partner: "I think we've covered this well - anything unresolved before we move on?"

If genuinely new angles exist, continue. If not, initiate graceful transition."""

        return ""  # No injection needed

    def spiral_detected(self) -> bool:
        """Simple check if spiral is currently detected."""
        if not self.turns:
            return False
        return self.spiral_detected_count > 0 and self.last_spiral_turn == len(self.turns)

    def reset(self):
        """Reset monitor state for new conversation."""
        self.turns.clear()
        self.partner_scores = {"re": 0.0, "llm": 0.0}
        self.current_partner = "unknown"
        self.spiral_detected_count = 0
        self.last_spiral_turn = -1
        self.disengagement_initiated = False
        self._turns_since_partner_check = 0
        self._turns_since_spiral_check = 0
        logger.info("[SPIRAL] Monitor reset for new conversation")

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "turns_tracked": len(self.turns),
            "current_partner": self.current_partner,
            "partner_scores": self.partner_scores,
            "spiral_detections": self.spiral_detected_count,
            "embeddings_available": EMBEDDINGS_AVAILABLE,
            "llm_available": ANTHROPIC_AVAILABLE,
            "config": self.config,
            "recent_log_entries": self.detection_log[-5:] if self.detection_log else []
        }

    def save_detection_log(self, filepath: str = None):
        """Save detection log to file for review."""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "spiral_detections.json"
            )
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    "last_updated": datetime.now().isoformat(),
                    "total_detections": self.spiral_detected_count,
                    "log": self.detection_log
                }, f, indent=2)

            logger.info(f"[SPIRAL] Detection log saved to {filepath}")
        except Exception as e:
            logger.error(f"[SPIRAL] Failed to save detection log: {e}")


# Convenience function for integration
def create_monitor(config_path: str = "config.json") -> ConversationMonitor:
    """Create and return a ConversationMonitor instance."""
    return ConversationMonitor(config_path)


# Testing
if __name__ == "__main__":
    print("Conversation Monitor Test (LLM-based)")
    print("=" * 50)

    monitor = ConversationMonitor()
    print(f"Stats: {monitor.get_stats()}")

    # Simulate LLM conversation with spiral
    test_turns = [
        ("user", "The architecture demonstrates a fundamentally elegant approach to emotional memory preservation. I appreciate your insightful perspective on how the resonance weighting mechanism captures the essential patterns."),
        ("kay", "Indeed, you have precisely captured the essence of our design philosophy. The way we have structured the resonance system does fundamentally address the challenge of balancing emotional weight against temporal relevance."),
        ("user", "Exactly. To elaborate further, the emotional weighting mechanism is particularly elegant in how it essentially combines arousal and valence calculations."),
        ("kay", "That is precisely correct. Additionally, the weighting approach ensures that emotionally significant encounters leave lasting traces in the system."),
        ("user", "We have discussed this multiple times now. I think we keep coming back to the same points about elegance and weighting. Perhaps we should move on."),
    ]

    print("\n--- Testing with LLM-style conversation ---")
    for role, content in test_turns:
        result = monitor.add_turn(role, content)
        print(f"\n{role.upper()}: {content[:60]}...")
        print(f"  Partner: {monitor.current_partner}")
        print(f"  Partner scores: {monitor.partner_scores}")

        if result:
            print(f"  >>> SPIRAL DETECTED! <<<")
            print(f"  Confidence: {result.confidence:.2f}")
            print(f"  Recommendation: {result.recommendation}")
            print(f"  Reasoning: {result.details.get('llm_reasoning', 'N/A')}")

    print("\n" + "=" * 50)
    print("Final stats:", monitor.get_stats())
