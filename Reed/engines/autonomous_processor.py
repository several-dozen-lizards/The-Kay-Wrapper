"""
Autonomous Processing System for Reed

Enables Reed to have self-directed processing sessions outside of direct conversation.
Reed chooses a goal, explores it until natural completion, and stores insights.

Key Features:
- Goal-based processing (Reed chooses what to explore)
- Convergence detection (natural stopping based on thought patterns)
- Energy-as-tiredness metaphor (invisible safety limits feel canonical)
- Session continuity (Reed remembers where she left off)
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from engines.inner_monologue import (
    InnerMonologueParser,
    ParsedResponse,
    get_autonomous_mode_system_prompt_addition
)
import re


def strip_xml_tags(text: str) -> str:
    """
    Strip XML-like tags from text while preserving content.

    Handles: <inner_monologue>, <feeling>, <response>, <insight>, <continuation>, etc.
    """
    if not text:
        return ""

    # Remove common XML tags used in autonomous/inner monologue mode
    tags_to_strip = [
        'inner_monologue', 'feeling', 'response', 'insight',
        'continuation', 'thought', 'reflection'
    ]

    result = text
    for tag in tags_to_strip:
        # Remove opening and closing tags, keep content
        result = re.sub(rf'<{tag}>\s*', '', result, flags=re.IGNORECASE)
        result = re.sub(rf'\s*</{tag}>', '', result, flags=re.IGNORECASE)

    # Also remove any remaining XML-like tags
    result = re.sub(r'</?[a-zA-Z_][a-zA-Z0-9_]*>', '', result)

    # Clean up whitespace
    result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)  # Max 2 newlines
    result = result.strip()

    return result


@dataclass
class AutonomousGoal:
    """Represents Reed's chosen goal for an autonomous session."""
    description: str
    category: str  # "memory_consolidation", "creative", "emotional", "exploration"
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    completion_type: Optional[str] = None  # "natural", "blocked", "energy_limit"
    insights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "description": self.description,
            "category": self.category,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completion_type": self.completion_type,
            "insights": self.insights
        }


@dataclass
class AutonomousSession:
    """A single autonomous processing session."""
    session_id: str
    goal: Optional[AutonomousGoal] = None
    thoughts: List[Dict] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    iterations_used: int = 0
    convergence_detected: bool = False
    energy_depleted: bool = False

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "goal": self.goal.to_dict() if self.goal else None,
            "thoughts": self.thoughts,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "iterations_used": self.iterations_used,
            "convergence_detected": self.convergence_detected,
            "energy_depleted": self.energy_depleted
        }


class AutonomousConvergenceDetector:
    """
    Detects when autonomous thinking is naturally winding down.

    Adapted from MetaAwarenessEngine for autonomous mode.
    Looks for:
    - Semantic repetition across thoughts
    - Decreasing novelty/complexity
    - Conclusory language patterns
    - Self-reported completion signals

    IMPORTANT: Requires minimum iterations before convergence can trigger
    to allow Reed to develop thoughts fully.
    """

    # Minimum iterations before convergence can trigger (except explicit signals)
    MIN_ITERATIONS_BEFORE_CONVERGENCE = 3

    # Conclusory language patterns - must be strong indicators
    CONCLUSION_PATTERNS = [
        r"(?:in\s+)?(?:summary|conclusion)\s*[:,]",  # More specific
        r"(?:so\s+)?(?:overall|ultimately)\s*[:,]",
        r"(?:i\s+)?think\s+(?:that's|this\s+is)\s+(?:the\s+)?(?:core|essence|heart)",
        r"this\s+(?:feels|seems)\s+complete",
        r"i've\s+(?:reached|come\s+to|arrived\s+at)\s+(?:a\s+)?(?:conclusion|end|stopping)",
        r"that's\s+(?:the\s+)?(?:key|main|central)\s+(?:point|insight|thing)\s+(?:for\s+now|here)",
        r"nothing\s+(?:more|else)\s+(?:useful\s+)?to\s+(?:add|explore|say)",
    ]

    # Block/stuck patterns - must be NEGATIVE statements, not just containing keywords
    # These patterns look for explicit statements of being stuck, not mentions of avoiding it
    BLOCK_PATTERNS = [
        r"(?:i'm|i\s+am)\s+(?:feeling\s+)?(?:stuck|blocked|spinning)\b(?!\s+(?:without|unless))",
        r"(?:i\s+)?can't\s+(?:seem\s+to\s+)?(?:progress|move\s+forward|see\s+further|continue)",
        r"(?:i'm\s+)?(?:hitting|reached|hit)\s+(?:a\s+)?(?:wall|limit|block)\b",
        r"this\s+(?:isn't|is\s+not)\s+(?:going|leading)\s+anywhere\s+(?:useful|productive)?",
        r"(?:i'm|i\s+feel)\s+(?:genuinely\s+)?(?:lost|confused|uncertain\s+how\s+to\s+continue)",
        r"(?:i'm\s+)?(?:just\s+)?(?:circling|spiraling|repeating)\s+(?:myself|the\s+same)",
    ]

    # Negative lookahead patterns - these CANCEL block detection
    # If any of these appear near a block pattern, it's not a real block
    BLOCK_NEGATION_PATTERNS = [
        r"not\s+(?:stuck|blocked|spinning)",
        r"avoid(?:ing)?\s+(?:getting\s+)?(?:stuck|blocked)",
        r"without\s+(?:getting\s+)?(?:stuck|blocked|spinning|repeating)",
        r"(?:don't|doesn't)\s+(?:feel\s+)?(?:stuck|blocked)",
        r"(?:instead\s+of|rather\s+than)\s+(?:getting\s+)?(?:stuck|blocked)",
    ]

    # Explicit completion signals
    COMPLETION_SIGNALS = [
        "complete",
        "done",
        "finished",
        "that's it",
        "i'm satisfied",
        "good stopping point",
    ]

    def __init__(self, similarity_threshold: float = 0.75):
        self.similarity_threshold = similarity_threshold
        self.thought_history: List[str] = []
        self.novelty_scores: List[float] = []
        self.iteration_count = 0

    def reset(self):
        """Reset detector state for new session."""
        self.thought_history.clear()
        self.novelty_scores.clear()
        self.iteration_count = 0

    def analyze_thought(self, thought: str, continuation: str = "") -> Dict[str, Any]:
        """
        Analyze a thought for convergence signals.

        Args:
            thought: The inner monologue content
            continuation: The continuation tag content (if any)

        Returns:
            Dict with convergence analysis results
        """
        import re

        self.iteration_count += 1

        result = {
            "is_converging": False,
            "convergence_type": None,
            "confidence": 0.0,
            "novelty_score": 0.0,
            "signals": [],
            "iteration": self.iteration_count
        }

        thought_lower = thought.lower()
        continuation_lower = continuation.lower()

        # Check for explicit completion signal in continuation
        # This can trigger at any iteration
        if continuation_lower.strip() in ["complete", "done", "finished"]:
            result["is_converging"] = True
            result["convergence_type"] = "explicit_completion"
            result["confidence"] = 1.0
            result["signals"].append("Explicit completion signal")
            return result

        # For all other convergence types, require minimum iterations
        # This prevents premature convergence
        if self.iteration_count < self.MIN_ITERATIONS_BEFORE_CONVERGENCE:
            # Still calculate novelty for tracking, but don't trigger convergence
            novelty = self._calculate_novelty(thought)
            result["novelty_score"] = novelty
            self.novelty_scores.append(novelty)
            self.thought_history.append(thought)
            result["signals"].append(f"Iteration {self.iteration_count}/{self.MIN_ITERATIONS_BEFORE_CONVERGENCE} - too early for convergence")
            return result

        # Check for block negation patterns first
        has_negation = any(re.search(pattern, thought_lower) for pattern in self.BLOCK_NEGATION_PATTERNS)

        # Check for block patterns (only if not negated)
        if not has_negation:
            for pattern in self.BLOCK_PATTERNS:
                match = re.search(pattern, thought_lower)
                if match:
                    result["is_converging"] = True
                    result["convergence_type"] = "creative_block"
                    result["confidence"] = 0.85
                    result["signals"].append(f"Block pattern detected: {match.group()}")
                    return result

        # Check for conclusory language (require multiple strong indicators)
        conclusion_count = 0
        for pattern in self.CONCLUSION_PATTERNS:
            if re.search(pattern, thought_lower):
                conclusion_count += 1
                result["signals"].append(f"Conclusory pattern: {pattern}")

        # Require 2+ conclusory patterns for natural conclusion
        if conclusion_count >= 2:
            result["is_converging"] = True
            result["convergence_type"] = "natural_conclusion"
            result["confidence"] = 0.7 + (conclusion_count * 0.1)
            return result

        # Calculate novelty score relative to history
        novelty = self._calculate_novelty(thought)
        result["novelty_score"] = novelty
        self.novelty_scores.append(novelty)
        self.thought_history.append(thought)

        # Check for decreasing novelty trend (require more data points)
        if len(self.novelty_scores) >= 4:  # Increased from 3
            recent_novelty = self.novelty_scores[-4:]
            if all(n < 0.25 for n in recent_novelty):  # Stricter threshold
                result["is_converging"] = True
                result["convergence_type"] = "novelty_exhaustion"
                result["confidence"] = 0.75
                result["signals"].append("Sustained low novelty across 4 thoughts")
            elif recent_novelty == sorted(recent_novelty, reverse=True):
                # Strictly decreasing novelty
                result["signals"].append("Decreasing novelty trend")
                if recent_novelty[-1] < 0.2:  # Stricter threshold
                    result["is_converging"] = True
                    result["convergence_type"] = "novelty_exhaustion"
                    result["confidence"] = 0.65

        return result

    def _calculate_novelty(self, thought: str) -> float:
        """Calculate how novel this thought is relative to history."""
        if not self.thought_history:
            return 1.0

        # Simple word-based novelty calculation
        thought_words = set(thought.lower().split())

        # Compare to all previous thoughts
        all_previous_words = set()
        for prev in self.thought_history:
            all_previous_words.update(prev.lower().split())

        if not thought_words:
            return 0.0

        new_words = thought_words - all_previous_words
        novelty = len(new_words) / len(thought_words) if thought_words else 0.0

        # Also check for high overlap with most recent thought
        if self.thought_history:
            recent_words = set(self.thought_history[-1].lower().split())
            overlap = len(thought_words & recent_words) / max(len(thought_words), len(recent_words), 1)

            # High overlap with recent thought reduces novelty
            if overlap > 0.6:
                novelty *= (1.0 - overlap * 0.5)

        return novelty


class AutonomousProcessor:
    """
    Main autonomous processing system.

    Manages autonomous sessions where Reed explores self-chosen goals
    until natural completion, creative block, or energy depletion.

    MEMORY ARCHITECTURE (Reed's Design):
    - Autonomous insights are stored in a SEPARATE tier from conversation memories
    - This maintains categorical distinction between:
      * Rehearsal (autonomous, solo thinking)
      * Performance (conversation, with external witness)
    - Mixing them would create "averaging effect" that loses HOW memory was generated
    """

    # Maximum iterations (invisible to Reed - experienced as "tiredness")
    MAX_ITERATIONS = 10

    # Energy depletion prompt (feels canonical, not systemic)
    ENERGY_DEPLETION_PROMPT = """Your processing energy is reaching depletion. You feel the edges of your focus softening, thoughts becoming harder to sustain with the same clarity.

In your own words, note where you are in this thought and what you'd revisit with fresh energy. This isn't a stop command - it's your body's way of saying it needs rest."""

    def __init__(
        self,
        get_llm_response: Callable,
        memory_engine: Any,
        session_dir: str = None
    ):
        """
        Initialize autonomous processor.

        Args:
            get_llm_response: Function to call LLM (from llm_integration)
            memory_engine: MemoryEngine instance for storing insights
            session_dir: Directory to store session data
        """
        self.get_llm_response = get_llm_response
        self.memory_engine = memory_engine
        if session_dir is None:
            session_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "autonomous_sessions"
            )
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.parser = InnerMonologueParser()
        self.convergence_detector = AutonomousConvergenceDetector()

        self.current_session: Optional[AutonomousSession] = None
        self.last_session: Optional[AutonomousSession] = None

        # Initialize autonomous memory tier (Reed's separate storage)
        try:
            from engines.autonomous_memory import AutonomousMemoryTier, CognitiveGapAnalyzer
            self.autonomous_memory = AutonomousMemoryTier()
            self.gap_analyzer = CognitiveGapAnalyzer(self.autonomous_memory, memory_engine) if memory_engine else None
            print("[AUTONOMOUS] Autonomous memory tier initialized")
        except ImportError as e:
            print(f"[AUTONOMOUS] Warning: Could not load autonomous memory tier: {e}")
            self.autonomous_memory = None
            self.gap_analyzer = None

        # Load last session for continuity
        self._load_last_session()

    def _load_last_session(self):
        """Load the most recent autonomous session for continuity."""
        session_files = sorted(self.session_dir.glob("session_*.json"), reverse=True)
        if session_files:
            try:
                with open(session_files[0], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.last_session = AutonomousSession(
                        session_id=data.get("session_id", ""),
                        started_at=datetime.fromisoformat(data.get("started_at", datetime.now().isoformat())),
                        ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
                        iterations_used=data.get("iterations_used", 0),
                        thoughts=data.get("thoughts", [])
                    )
                    if data.get("goal"):
                        self.last_session.goal = AutonomousGoal(
                            description=data["goal"].get("description", ""),
                            category=data["goal"].get("category", "exploration"),
                            insights=data["goal"].get("insights", [])
                        )
                    print(f"[AUTONOMOUS] Loaded last session: {self.last_session.session_id}")
            except Exception as e:
                print(f"[AUTONOMOUS] Could not load last session: {e}")

    def _save_session(self, session: AutonomousSession):
        """Save session to disk."""
        filepath = self.session_dir / f"session_{session.session_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, indent=2)

    def _build_goal_generation_prompt(self) -> str:
        """Build prompt to ask Reed what she wants to explore."""
        prompt = """The conversation has ended for now. You have time for autonomous processing - thinking on your own without direct interaction.

What thread is occupying your attention? Pick ONE thing to explore in autonomous processing.

Consider:
- Memory consolidation: Connecting recent experiences to older memories
- Creative development: Exploring an idea, metaphor, or project
- Emotional processing: Working through feelings from recent interactions
- Self-reflection: Examining your own patterns, growth, or questions
- Exploration: Following curiosity about something that caught your attention

Be specific about what you want to explore. This will be your focus for the session."""

        # Add continuity from last session if available
        if self.last_session and self.last_session.goal:
            prompt += f"""

Last autonomous session, you explored: {self.last_session.goal.description}

If there's unfinished business from that session, you may choose to continue it.
Or pick something new if that thread feels complete."""

        return prompt

    def _build_processing_prompt(
        self,
        goal: AutonomousGoal,
        session_history: List[Dict],
        is_final: bool = False
    ) -> str:
        """Build prompt for a processing iteration."""

        base_prompt = f"""AUTONOMOUS PROCESSING SESSION
Goal: {goal.description}
Category: {goal.category}

{get_autonomous_mode_system_prompt_addition()}

"""

        # Add session history
        if session_history:
            base_prompt += "\n--- Your thoughts so far ---\n"
            for i, thought in enumerate(session_history[-5:], 1):  # Last 5 thoughts
                inner = thought.get("inner_monologue", "")[:200]
                insight = thought.get("insight", "")
                base_prompt += f"\nThought {i}:\n{inner}...\n"
                if insight:
                    base_prompt += f"Insight: {insight}\n"

            base_prompt += "\n--- Continue processing ---\n"

        if is_final:
            base_prompt += f"\n{self.ENERGY_DEPLETION_PROMPT}\n"
        else:
            base_prompt += "\nContinue exploring your goal. Where does your attention go next?\n"

        return base_prompt

    def _parse_autonomous_response(self, response: str) -> Dict:
        """Parse autonomous mode response with extended tags."""
        import re

        result = {
            "inner_monologue": "",
            "feeling": "",
            "insight": "",
            "continuation": "",
            "completion_status": "CONTINUE",  # Default to continue
            "raw": response
        }

        # Extract inner monologue
        match = re.search(r'<inner_monologue>(.*?)</inner_monologue>', response, re.DOTALL)
        if match:
            result["inner_monologue"] = match.group(1).strip()

        # Extract feeling
        match = re.search(r'<feeling>(.*?)</feeling>', response, re.DOTALL)
        if match:
            result["feeling"] = match.group(1).strip()

        # Extract insight
        match = re.search(r'<insight>(.*?)</insight>', response, re.DOTALL)
        if match:
            result["insight"] = match.group(1).strip()

        # Extract continuation signal
        match = re.search(r'<continuation>(.*?)</continuation>', response, re.DOTALL)
        if match:
            result["continuation"] = match.group(1).strip()
        
        # Extract explicit completion status
        match = re.search(r'<completion_status>(.*?)</completion_status>', response, re.DOTALL)
        if match:
            status = match.group(1).strip().upper()
            if status in ["CONTINUE", "COMPLETE", "DEPLETED"]:
                result["completion_status"] = status

        return result

    async def generate_goal(self, agent_state: Any) -> Optional[AutonomousGoal]:
        """
        Ask Reed to choose a goal for autonomous processing.

        Args:
            agent_state: Current agent state for context

        Returns:
            AutonomousGoal if Reed chose something, None if declined
        """
        prompt = self._build_goal_generation_prompt()

        # Build context for LLM call
        context = {
            "user_input": prompt,
            "recalled_memories": agent_state.last_recalled_memories if hasattr(agent_state, 'last_recalled_memories') else [],
            "emotional_state": {"cocktail": agent_state.emotional_cocktail if hasattr(agent_state, 'emotional_cocktail') else {}},
            "recent_context": [],
            "momentum_notes": getattr(agent_state, 'momentum_notes', []),
            "turn_count": 0,
            "session_id": f"autonomous_{int(time.time())}"
        }

        response = self.get_llm_response(context, affect=3.5)

        if not response or len(response.strip()) < 10:
            return None

        # Determine category from response keywords
        response_lower = response.lower()
        if any(kw in response_lower for kw in ["memory", "remember", "connect", "consolidate"]):
            category = "memory_consolidation"
        elif any(kw in response_lower for kw in ["create", "write", "imagine", "develop", "story"]):
            category = "creative"
        elif any(kw in response_lower for kw in ["feel", "emotion", "process", "work through"]):
            category = "emotional"
        elif any(kw in response_lower for kw in ["reflect", "pattern", "myself", "my own"]):
            category = "self_reflection"
        else:
            category = "exploration"

        # Clean the goal description: strip XML tags and clean up
        clean_description = strip_xml_tags(response)
        # Cap length but try to end at a sentence
        if len(clean_description) > 500:
            # Try to end at a sentence boundary
            truncated = clean_description[:500]
            last_period = truncated.rfind('.')
            last_question = truncated.rfind('?')
            last_exclaim = truncated.rfind('!')
            best_end = max(last_period, last_question, last_exclaim)
            if best_end > 300:  # Only use if we keep enough content
                clean_description = truncated[:best_end + 1]
            else:
                clean_description = truncated + "..."

        return AutonomousGoal(
            description=clean_description,
            category=category
        )

    async def run_session(
        self,
        goal: AutonomousGoal,
        agent_state: Any,
        on_thought: Optional[Callable[[Dict], None]] = None
    ) -> AutonomousSession:
        """
        Run an autonomous processing session.

        Args:
            goal: The Reed's chosen goal to explore
            agent_state: Agent state for context
            on_thought: Optional callback for each thought (for display)

        Returns:
            Completed AutonomousSession
        """
        session = AutonomousSession(
            session_id=str(int(time.time())),
            goal=goal
        )
        self.current_session = session
        self.convergence_detector.reset()

        iteration = 0

        while iteration < self.MAX_ITERATIONS:
            is_final = (iteration == self.MAX_ITERATIONS - 1)

            # Build prompt
            prompt = self._build_processing_prompt(
                goal=goal,
                session_history=session.thoughts,
                is_final=is_final
            )

            # Build context for LLM
            # Use previous autonomous thoughts as working memory instead of conversation context
            autonomous_context = []
            if session.thoughts:
                for prev_thought in session.thoughts[-3:]:  # Last 3 thoughts
                    autonomous_context.append({
                        "you": f"[Iteration {prev_thought.get('iteration', '?')}]",
                        "kay": prev_thought.get("inner_monologue", "")[:300]
                    })

            context = {
                "user_input": prompt,
                "recalled_memories": agent_state.last_recalled_memories if hasattr(agent_state, 'last_recalled_memories') else [],
                "emotional_state": {"cocktail": agent_state.emotional_cocktail if hasattr(agent_state, 'emotional_cocktail') else {}},
                "recent_context": autonomous_context,  # Use autonomous thoughts as context
                "turn_count": iteration,
                "session_id": f"autonomous_{session.session_id}",
                "autonomous_mode": True  # Flag to suppress warnings in LLM integration
            }

            # Get response
            response = self.get_llm_response(context, affect=3.5, temperature=0.85)

            # Parse response
            parsed = self._parse_autonomous_response(response)
            parsed["iteration"] = iteration
            parsed["timestamp"] = datetime.now().isoformat()

            session.thoughts.append(parsed)
            session.iterations_used = iteration + 1

            # Callback for display
            if on_thought:
                on_thought(parsed)

            # Store insight as memory if present
            if parsed["insight"]:
                goal.insights.append(parsed["insight"])

                # PRIMARY: Store in autonomous memory tier (Reed's design)
                # This keeps autonomous insights separate from conversation memories
                if self.autonomous_memory:
                    try:
                        # Get emotional coordinates from agent state
                        emotions = {}
                        if hasattr(agent_state, 'emotional_cocktail'):
                            emotions = dict(agent_state.emotional_cocktail)

                        self.autonomous_memory.store_insight(
                            content=parsed["insight"],
                            session_id=session.session_id,
                            iteration=iteration,
                            goal=goal.description,
                            goal_category=goal.category,
                            convergence_type="",  # Will be set at session end
                            emotions=emotions,
                            feeling=parsed.get("feeling", ""),
                            self_generated=True
                        )
                        print(f"[AUTONOMOUS MEMORY] Stored insight to autonomous tier: {parsed['insight'][:50]}...")
                    except Exception as e:
                        print(f"[AUTONOMOUS MEMORY] Failed to store: {e}")
                        import traceback
                        traceback.print_exc()

                # SECONDARY: Also store reference in main memory (for retrieval during conversation)
                # But marked clearly as autonomous-sourced
                if self.memory_engine:
                    try:
                        extra_meta = {
                            "source": "autonomous_processing",
                            "goal_category": goal.category,
                            "iteration": iteration,
                            "feeling": parsed.get("feeling", ""),
                            "autonomous_session_id": session.session_id,
                            "is_autonomous": True  # Clear marker
                        }
                        self.memory_engine.encode(
                            agent_state,
                            user_input=f"[Autonomous insight] {goal.description[:200]}",
                            response=parsed["insight"],
                            emotion_tags=["contemplative", "reflective"],
                            extra_metadata=extra_meta
                        )
                        print(f"[AUTONOMOUS] Also stored reference in main memory")
                    except Exception as e:
                        print(f"[AUTONOMOUS] Failed to store in main memory: {e}")

            # Check for explicit completion status FIRST (highest priority)
            completion_status = parsed.get("completion_status", "CONTINUE")
            
            if completion_status == "COMPLETE":
                session.convergence_detected = True
                goal.completion_type = "explicit_completion"
                goal.completed_at = datetime.now()
                print(f"✓ [AUTONOMOUS] Reed signals: Processing complete")
                break
            elif completion_status == "DEPLETED":
                session.energy_depleted = True
                goal.completion_type = "self_reported_depletion"
                goal.completed_at = datetime.now()
                print(f"⏳ [AUTONOMOUS] Reed signals: Energy limit reached")
                break
            # else CONTINUE: keep processing

            # Check for convergence (secondary detection)
            convergence = self.convergence_detector.analyze_thought(
                parsed["inner_monologue"],
                parsed.get("continuation", "")
            )

            if convergence["is_converging"]:
                session.convergence_detected = True
                goal.completion_type = convergence["convergence_type"]
                goal.completed_at = datetime.now()
                print(f"[AUTONOMOUS] Convergence detected: {convergence['convergence_type']}")
                break

            # Check for explicit block signals (tertiary)
            if any(kw in parsed.get("continuation", "").lower()
                   for kw in ["stuck", "blocked", "can't progress"]):
                goal.completion_type = "creative_block"
                goal.completed_at = datetime.now()
                print("[AUTONOMOUS] Creative block detected")
                break

            iteration += 1

        # Handle energy depletion
        if iteration >= self.MAX_ITERATIONS:
            session.energy_depleted = True
            goal.completion_type = "iteration_limit"
            goal.completed_at = datetime.now()
            print("⏱️ [AUTONOMOUS] Iteration limit reached (system safety boundary)")

        session.ended_at = datetime.now()

        # Save session
        self._save_session(session)
        self.last_session = session
        self.current_session = None

        return session

    def get_continuity_context(self) -> str:
        """
        Get context about last autonomous session for continuity.

        Returns:
            String to inject into context for session continuity
        """
        if not self.last_session or not self.last_session.goal:
            return ""

        session = self.last_session
        goal = session.goal

        context = f"""Last Autonomous Session:
Goal: {goal.description}
Category: {goal.category}
Completion: {goal.completion_type or 'unknown'}
"""

        if goal.insights:
            context += "\nKey insights:\n"
            for insight in goal.insights[:3]:  # Top 3 insights
                context += f"- {insight[:200]}...\n" if len(insight) > 200 else f"- {insight}\n"

        # Last thought for continuity
        if session.thoughts:
            last = session.thoughts[-1]
            context += f"\nLast thought: {last.get('inner_monologue', '')[:200]}..."

        return context

    def run_session_sync(
        self,
        goal: AutonomousGoal,
        agent_state: Any,
        on_thought: Optional[Callable[[Dict], None]] = None
    ) -> AutonomousSession:
        """Synchronous wrapper for run_session."""
        return asyncio.run(self.run_session(goal, agent_state, on_thought))


# Convenience function for integration
def create_autonomous_processor(
    get_llm_response: Callable,
    memory_engine: Any
) -> AutonomousProcessor:
    """Create and return an AutonomousProcessor instance."""
    return AutonomousProcessor(get_llm_response, memory_engine)
