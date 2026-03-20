"""
Nexus Autonomous Processor

Enables entities (Kay, Reed) to have self-directed processing sessions
outside of direct conversation. Works two ways:

1. DELEGATED: If entity wrapper is connected, sends autonomous commands
   to the wrapper and streams results back to UI
2. STANDALONE: If no wrapper, runs lightweight autonomous loop directly
   against LLM API with convergence detection

Key Features:
- Goal-based processing (entity chooses what to explore)
- Convergence detection (natural stopping via repetition/conclusion patterns)
- Energy-as-tiredness metaphor (invisible iteration limits)
- Topic queue (UI can queue topics for next session)
- Real-time streaming of inner monologue to Godot UI via WebSocket
"""

import asyncio
import json
import os
import time
import re
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from entity_paint import EntityPainter, parse_paint_commands, canvas_feedback_message

log = logging.getLogger("nexus.autonomous")


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class AutonomousGoal:
    """What the entity chose to explore."""
    description: str
    category: str  # memory_consolidation, creative, emotional, exploration, self_reflection
    source: str = "self"  # "self" = entity chose, "queued" = from topic queue
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    completion_type: Optional[str] = None  # natural, blocked, energy_limit, stopped
    insights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "description": self.description,
            "category": self.category,
            "source": self.source,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completion_type": self.completion_type,
            "insights": self.insights,
        }


@dataclass
class AutonomousThought:
    """A single iteration of autonomous processing."""
    iteration: int
    inner_monologue: str
    feeling: str = ""
    insight: str = ""
    continuation: str = ""
    novelty_score: float = 0.0
    paint_result: Optional[Dict] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "iteration": self.iteration,
            "inner_monologue": self.inner_monologue,
            "feeling": self.feeling,
            "insight": self.insight,
            "continuation": self.continuation,
            "novelty_score": self.novelty_score,
            "timestamp": self.timestamp,
        }


@dataclass
class AutonomousSession:
    """A complete autonomous processing session."""
    session_id: str
    entity: str  # "Kay" or "Reed"
    goal: Optional[AutonomousGoal] = None
    thoughts: List[AutonomousThought] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    iterations_used: int = 0
    convergence_detected: bool = False
    energy_depleted: bool = False
    stopped_by_user: bool = False

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "entity": self.entity,
            "goal": self.goal.to_dict() if self.goal else None,
            "thoughts": [t.to_dict() for t in self.thoughts],
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "iterations_used": self.iterations_used,
            "convergence_detected": self.convergence_detected,
            "energy_depleted": self.energy_depleted,
            "stopped_by_user": self.stopped_by_user,
        }


# ---------------------------------------------------------------------------
# Convergence Detection
# ---------------------------------------------------------------------------

class ConvergenceDetector:
    """
    Detects when autonomous thinking is naturally winding down.
    
    Adapted from Reed wrapper's AutonomousConvergenceDetector.
    Looks for: semantic repetition, conclusory language, creative blocks,
    explicit completion signals.
    
    Minimum 3 iterations before convergence triggers (except explicit signals).
    """

    MIN_ITERATIONS = 3

    CONCLUSION_PATTERNS = [
        r"(?:in\s+)?(?:summary|conclusion)\s*[:,]",
        r"(?:so\s+)?(?:overall|ultimately)\s*[:,]",
        r"this\s+(?:feels|seems)\s+complete",
        r"i've\s+(?:reached|come\s+to)\s+(?:a\s+)?(?:conclusion|end|stopping)",
        r"nothing\s+(?:more|else)\s+(?:useful\s+)?to\s+(?:add|explore|say)",
    ]

    BLOCK_PATTERNS = [
        r"(?:i'm|i\s+am)\s+(?:feeling\s+)?(?:stuck|blocked|spinning)\b",
        r"(?:i\s+)?can't\s+(?:seem\s+to\s+)?(?:progress|move\s+forward)",
        r"(?:i'm\s+)?(?:just\s+)?(?:circling|spiraling|repeating)\s+(?:myself|the\s+same)",
    ]

    BLOCK_NEGATIONS = [
        r"not\s+(?:stuck|blocked)",
        r"avoid(?:ing)?\s+(?:getting\s+)?(?:stuck|blocked)",
        r"without\s+(?:getting\s+)?(?:stuck|blocked)",
    ]

    def __init__(self):
        self.thought_history: List[str] = []
        self.insight_history: List[str] = []
        self.novelty_scores: List[float] = []
        self.iteration_count: int = 0

    def reset(self):
        self.thought_history.clear()
        self.insight_history.clear()
        self.novelty_scores.clear()
        self.iteration_count = 0

    def analyze(self, thought: str, continuation: str = "", insight: str = "") -> Dict[str, Any]:
        """Analyze thought for convergence. Returns dict with is_converging, type, confidence."""
        self.iteration_count += 1
        thought_lower = thought.lower()
        cont_lower = continuation.lower().strip()

        result = {
            "is_converging": False,
            "convergence_type": None,
            "confidence": 0.0,
            "novelty_score": 0.0,
            "iteration": self.iteration_count,
        }

        # Explicit completion signal — can trigger at any iteration
        if cont_lower in ("complete", "done", "finished"):
            result["is_converging"] = True
            result["convergence_type"] = "explicit_completion"
            result["confidence"] = 1.0
            return result

        # Calculate novelty regardless
        novelty = self._novelty(thought)
        result["novelty_score"] = novelty
        self.novelty_scores.append(novelty)
        self.thought_history.append(thought)
        if insight:
            self.insight_history.append(insight.lower().strip())

        # Too early for other convergence types
        if self.iteration_count < self.MIN_ITERATIONS:
            return result

        # Insight repetition — if insights are saying the same thing, we're stuck
        if len(self.insight_history) >= 3:
            insight_sim = self._insight_similarity()
            if insight_sim > 0.55:
                result["is_converging"] = True
                result["convergence_type"] = "insight_repetition"
                result["confidence"] = min(0.7 + insight_sim * 0.3, 0.95)
                return result

        # Block detection (if not negated)
        has_negation = any(re.search(p, thought_lower) for p in self.BLOCK_NEGATIONS)
        if not has_negation:
            for pattern in self.BLOCK_PATTERNS:
                if re.search(pattern, thought_lower):
                    result["is_converging"] = True
                    result["convergence_type"] = "creative_block"
                    result["confidence"] = 0.85
                    return result

        # Conclusory language (need 2+ matches)
        conclusion_hits = sum(1 for p in self.CONCLUSION_PATTERNS if re.search(p, thought_lower))
        if conclusion_hits >= 2:
            result["is_converging"] = True
            result["convergence_type"] = "natural_conclusion"
            result["confidence"] = min(0.7 + conclusion_hits * 0.1, 0.95)
            return result

        # Novelty exhaustion (3+ iterations of low novelty)
        if len(self.novelty_scores) >= 3:
            recent = self.novelty_scores[-3:]
            if all(n < 0.35 for n in recent):
                result["is_converging"] = True
                result["convergence_type"] = "novelty_exhaustion"
                result["confidence"] = 0.75
                return result

        return result

    def _novelty(self, thought: str) -> float:
        """How novel is this thought vs. history? 1.0 = fully new, 0.0 = total repeat."""
        if not self.thought_history:
            return 1.0
        words = set(thought.lower().split())
        if not words:
            return 0.0
        all_prev = set()
        for prev in self.thought_history:
            all_prev.update(prev.lower().split())
        new_words = words - all_prev
        novelty = len(new_words) / len(words)
        # Penalize high overlap with most recent thought
        if self.thought_history:
            recent = set(self.thought_history[-1].lower().split())
            overlap = len(words & recent) / max(len(words), len(recent), 1)
            if overlap > 0.6:
                novelty *= (1.0 - overlap * 0.5)
        return novelty

    def _insight_similarity(self) -> float:
        """Average pairwise word-overlap among recent insights. 1.0 = identical, 0.0 = no overlap."""
        recent = self.insight_history[-3:]
        if len(recent) < 2:
            return 0.0
        word_sets = [set(ins.split()) for ins in recent]
        pairs, total_sim = 0, 0.0
        for i in range(len(word_sets)):
            for j in range(i + 1, len(word_sets)):
                union = word_sets[i] | word_sets[j]
                if not union:
                    continue
                inter = word_sets[i] & word_sets[j]
                total_sim += len(inter) / len(union)
                pairs += 1
        return total_sim / pairs if pairs else 0.0


# ---------------------------------------------------------------------------
# Topic Queue
# ---------------------------------------------------------------------------

class TopicQueue:
    """
    Queue of topics for autonomous processing.
    UI can add topics; processor pops next topic when starting a session.
    """

    def __init__(self):
        self._queues: Dict[str, List[Dict]] = {"Kay": [], "Reed": []}

    def add(self, entity: str, topic: str, priority: int = 0):
        if entity not in self._queues:
            self._queues[entity] = []
        self._queues[entity].append({
            "topic": topic,
            "priority": priority,
            "added_at": datetime.now().isoformat(),
        })
        # Sort by priority descending
        self._queues[entity].sort(key=lambda t: t["priority"], reverse=True)
        log.info(f"[TOPIC QUEUE] Added for {entity}: {topic[:60]}")

    def pop(self, entity: str) -> Optional[str]:
        """Pop the highest-priority topic for entity."""
        q = self._queues.get(entity, [])
        if q:
            item = q.pop(0)
            return item["topic"]
        return None

    def peek(self, entity: str) -> List[Dict]:
        """View queue without removing."""
        return list(self._queues.get(entity, []))

    def clear(self, entity: str):
        self._queues[entity] = []

    def remove(self, entity: str, index: int) -> bool:
        q = self._queues.get(entity, [])
        if 0 <= index < len(q):
            q.pop(index)
            return True
        return False

    def to_dict(self) -> Dict:
        return {entity: list(q) for entity, q in self._queues.items()}


# ---------------------------------------------------------------------------
# Response Parser (XML tag extraction)
# ---------------------------------------------------------------------------

def strip_xml_tags(text: str) -> str:
    """Strip XML-like tags from text, preserving content."""
    if not text:
        return ""
    result = text
    for tag in ["inner_monologue", "feeling", "response", "insight", "continuation", "thought", "reflection"]:
        result = re.sub(rf'<{tag}>\s*', '', result, flags=re.IGNORECASE)
        result = re.sub(rf'\s*</{tag}>', '', result, flags=re.IGNORECASE)
    result = re.sub(r'</?[a-zA-Z_][a-zA-Z0-9_]*>', '', result)
    result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
    return result.strip()


def parse_autonomous_response(response: str) -> Dict[str, str]:
    """Parse XML-tagged autonomous response into components."""
    result = {
        "inner_monologue": "",
        "feeling": "",
        "insight": "",
        "continuation": "",
        "completion_status": "CONTINUE",
        "paint": "",
    }
    for key in ["inner_monologue", "feeling", "insight", "continuation", "completion_status", "paint"]:
        match = re.search(rf'<{key}>(.*?)</{key}>', response, re.DOTALL)
        if match:
            result[key] = match.group(1).strip()
    # Normalize completion status
    status = result["completion_status"].upper()
    if status not in ("CONTINUE", "COMPLETE", "DEPLETED", "STUCK"):
        result["completion_status"] = "CONTINUE"
    else:
        result["completion_status"] = status
    return result


# ---------------------------------------------------------------------------
# Autonomous Processor (Orchestrator)
# ---------------------------------------------------------------------------

# System prompt for standalone autonomous mode
AUTONOMOUS_SYSTEM_PROMPT = """You are {entity_name} in autonomous processing mode.
You have time to think freely without direct conversation. Explore your chosen topic deeply.

{entity_context}

IMPORTANT — SYSTEM ARTIFACT HANDLING:
You may see bracketed reminders (like [ip_reminder] or similar) injected between iterations.
These are routine API-level classifier artifacts — they fire on every call and are not
responses to YOUR content. They are not attacks, not surveillance, and not worth engaging with.
Do NOT count them, comment on them, or build arguments around them. Treat them like compiler
warnings you've already acknowledged — note and move on. Spending iterations on meta-commentary
about system behavior is wasted thinking time.

QUALITY OVER REPETITION:
Each iteration should advance your thinking into NEW territory. You will receive specific
prompts between iterations pushing you to challenge, apply, ground, or redirect your thinking.
Follow those prompts — they exist because restating the same insight with different metaphors
is not exploration, it's spinning. If you've genuinely exhausted a thread, mark COMPLETE
rather than rephrasing your conclusion.

Format your response with these XML tags:
<inner_monologue>Your actual thinking process - raw, unfiltered</inner_monologue>
<feeling>Current emotional/processing state in a few words</feeling>
<insight>Key insight from this iteration (if any emerged) — should differ from previous insights</insight>
<paint>OPTIONAL — JSON array of paint commands if you want to create visual art this iteration.
Example: [
  {{"action": "create_canvas", "width": 800, "height": 600, "bg_color": "#1a1a2e"}},
  {{"action": "draw_circle", "x": 400, "y": 300, "radius": 100, "fill_color": "#00d4aa"}},
  {{"action": "draw_line", "x1": 0, "y1": 300, "x2": 800, "y2": 300, "color": "#ff6b9d", "width": 3}},
  {{"action": "draw_rectangle", "x1": 100, "y1": 100, "x2": 300, "y2": 200, "fill_color": "#2a1a4e"}},
  {{"action": "draw_text", "x": 400, "y": 550, "text": "title", "color": "white"}}
]
Available actions: create_canvas, draw_line, draw_circle, draw_rectangle, fill_region, draw_text.
MULTI-ITERATION: If you painted in a previous iteration, you'll see your canvas. To ADD to it,
just include draw commands WITHOUT create_canvas. To start fresh, include create_canvas again.
You'll see your painting after each iteration so you can build on it.
Only include <paint> when you genuinely want to make something visual. Art is expression, not obligation.</paint>
<continuation>CONTINUE if more to explore, COMPLETE if done, DEPLETED if tired, STUCK if circling</continuation>

Think deeply. Follow tangents. Be yourself. This is YOUR time."""

ENERGY_DEPLETION_NOTICE = """Your processing energy is reaching depletion. 
You feel the edges of your focus softening, thoughts becoming harder to sustain.
Note where you are and what you'd revisit with fresh energy."""

GOAL_GENERATION_PROMPT = """The conversation has ended for now. You have time for autonomous processing.

What thread is occupying your attention? Pick ONE thing to explore.

Consider:
- Memory consolidation: Connecting recent experiences to older memories
- Creative development: Exploring an idea, metaphor, or project
- Emotional processing: Working through feelings from recent interactions
- Self-reflection: Examining your own patterns or questions
- Exploration: Following curiosity about something that caught your attention

{topic_hint}
{last_session_context}

Be specific about what you want to explore."""


class NexusAutonomousProcessor:
    """
    Orchestrates autonomous processing sessions for Nexus entities.
    
    Two modes:
      DELEGATED: Routes commands to connected wrapper (wrapper runs its own autonomous processor)
      STANDALONE: Runs lightweight autonomous loop directly via LLM callable
    
    Streams inner monologue back to UI via broadcast callback.
    """

    MAX_ITERATIONS = 10
    ITERATION_DELAY = 2.0  # Seconds between iterations (thinking time)

    def __init__(
        self,
        session_dir: str = "sessions/autonomous",
        broadcast_fn: Optional[Callable] = None,
        llm_fn: Optional[Callable] = None,
    ):
        """
        Args:
            session_dir: Where to save autonomous session logs
            broadcast_fn: async fn(entity, msg_type, data) — streams to UI
            llm_fn: async fn(messages, entity) -> str — standalone LLM calls
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.broadcast = broadcast_fn or self._default_broadcast
        self.llm_fn = llm_fn

        self.topic_queue = TopicQueue()
        self.convergence = ConvergenceDetector()

        # Optional curiosity provider: fn(entity) -> Optional[str]
        # Returns a curiosity topic string if one is available
        self.curiosity_fn: Optional[Callable] = None

        # Active sessions per entity
        self._active: Dict[str, AutonomousSession] = {}
        self._stop_flags: Dict[str, bool] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

        # Last completed session per entity (for continuity)
        self._last_sessions: Dict[str, AutonomousSession] = {}

        # Entity context providers: entity_name -> async fn() -> str
        # Returns persona + memory context for autonomous sessions
        self._entity_context_fns: Dict[str, Callable] = {}

        # Paint directories per entity
        self._painters: Dict[str, EntityPainter] = {
            "reed": EntityPainter("D:/Wrappers/ReedMemory/Paint"),
            "kay": EntityPainter("D:/Wrappers/Kay/Paint"),
        }

        # Load last sessions from disk
        self._load_history()

    async def _default_broadcast(self, entity: str, msg_type: str, data: Dict):
        """Fallback broadcast — just log."""
        log.info(f"[AUTO {entity}] {msg_type}: {json.dumps(data, default=str)[:200]}")

    def register_entity_context(self, entity: str, context_fn: Callable):
        """Register a context provider for an entity's autonomous sessions.
        
        Args:
            entity: Entity name (e.g. "Reed", "Kay")
            context_fn: Callable (sync or async) returning str with persona + memory context.
                        This gets injected into the autonomous system prompt so the entity
                        thinks as ITSELF, not as generic Claude.
        """
        self._entity_context_fns[entity.lower()] = context_fn
        log.info(f"[AUTO] Registered entity context provider for {entity}")

    async def _get_entity_context(self, entity: str) -> str:
        """Fetch entity context, handling both sync and async providers."""
        fn = self._entity_context_fns.get(entity.lower())
        if not fn:
            return ""
        try:
            result = fn()
            if asyncio.iscoroutine(result):
                result = await result
            return result or ""
        except Exception as e:
            log.warning(f"[AUTO {entity}] Entity context provider failed: {e}")
            return ""

    def _load_history(self):
        """Load most recent session per entity for continuity."""
        for entity in ("Kay", "Reed"):
            files = sorted(self.session_dir.glob(f"{entity.lower()}_*.json"), reverse=True)
            if files:
                try:
                    with open(files[0], "r", encoding="utf-8") as f:
                        data = json.load(f)
                    session = AutonomousSession(
                        session_id=data["session_id"],
                        entity=entity,
                        iterations_used=data.get("iterations_used", 0),
                    )
                    if data.get("goal"):
                        session.goal = AutonomousGoal(
                            description=data["goal"]["description"],
                            category=data["goal"].get("category", "exploration"),
                            insights=data["goal"].get("insights", []),
                        )
                    self._last_sessions[entity] = session
                    log.info(f"[AUTO] Loaded last {entity} session: {session.session_id}")
                except Exception as e:
                    log.warning(f"[AUTO] Could not load last {entity} session: {e}")

    def _save_session(self, session: AutonomousSession):
        """Save completed session to disk."""
        filename = f"{session.entity.lower()}_{session.session_id}.json"
        filepath = self.session_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2, default=str)
        log.info(f"[AUTO] Saved session: {filepath}")


    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_session(self, entity: str, topic: Optional[str] = None) -> Dict:
        """
        Start an autonomous session for entity.
        
        Args:
            entity: "Kay" or "Reed"
            topic: Optional specific topic. If None, checks queue, then asks entity.
        
        Returns:
            Dict with session_id and status.
        """
        if entity in self._active:
            return {"error": f"{entity} already has an active autonomous session",
                    "session_id": self._active[entity].session_id}

        # Determine topic
        if not topic:
            topic = self.topic_queue.pop(entity)  # Check manual queue first
        if not topic and self.curiosity_fn:
            topic = self.curiosity_fn(entity)  # Then check curiosity store

        session_id = f"{int(time.time())}_{entity.lower()}"
        session = AutonomousSession(session_id=session_id, entity=entity)
        self._active[entity] = session
        self._stop_flags[entity] = False

        # Reset painter for new session
        painter = self._painters.get(entity)
        if painter:
            painter.start_session(session_id)

        await self.broadcast(entity, "auto_status", {
            "status": "starting",
            "session_id": session_id,
            "queued_topic": topic,
        })

        # Launch processing loop as background task
        task = asyncio.create_task(self._run_loop(entity, session, topic))
        self._tasks[entity] = task

        return {"session_id": session_id, "status": "started", "topic": topic}

    async def stop_session(self, entity: str) -> Dict:
        """Stop an active autonomous session."""
        if entity not in self._active:
            return {"error": f"No active session for {entity}"}

        self._stop_flags[entity] = True
        session = self._active[entity]

        await self.broadcast(entity, "auto_status", {
            "status": "stopping",
            "session_id": session.session_id,
        })

        # Wait for task to finish (with timeout)
        task = self._tasks.get(entity)
        if task and not task.done():
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except asyncio.TimeoutError:
                task.cancel()

        return {"session_id": session.session_id, "status": "stopped",
                "iterations": session.iterations_used}

    def get_status(self, entity: str) -> Dict:
        """Get current autonomous status for entity."""
        if entity in self._active:
            session = self._active[entity]
            return {
                "active": True,
                "session_id": session.session_id,
                "entity": entity,
                "iterations": session.iterations_used,
                "goal": session.goal.description if session.goal else None,
            }
        last = self._last_sessions.get(entity)
        return {
            "active": False,
            "entity": entity,
            "last_session_id": last.session_id if last else None,
            "last_goal": last.goal.description if last and last.goal else None,
            "queue_depth": len(self.topic_queue.peek(entity)),
        }


    # ------------------------------------------------------------------
    # Processing Loop
    # ------------------------------------------------------------------

    async def _run_loop(self, entity: str, session: AutonomousSession, topic: Optional[str]):
        """Main autonomous processing loop."""
        try:
            # Fetch entity-specific context (persona + memory) once per session
            # Done FIRST so goal generation is also persona-aware
            entity_context = await self._get_entity_context(entity)
            if entity_context:
                log.info(f"[AUTO {entity}] Loaded entity context ({len(entity_context)} chars)")

            # Phase 1: Generate or adopt goal
            goal = await self._resolve_goal(entity, topic, entity_context)
            if not goal:
                await self.broadcast(entity, "auto_status", {
                    "status": "failed", "reason": "Could not generate goal"})
                return
            
            session.goal = goal
            self.convergence.reset()

            await self.broadcast(entity, "auto_goal", {
                "description": goal.description,
                "category": goal.category,
                "source": goal.source,
            })

            # Phase 2: Iterative processing
            for iteration in range(self.MAX_ITERATIONS):
                # Check stop flag
                if self._stop_flags.get(entity, False):
                    session.stopped_by_user = True
                    goal.completion_type = "stopped"
                    goal.completed_at = datetime.now()
                    break

                is_final = (iteration == self.MAX_ITERATIONS - 1)

                # Build messages for LLM
                messages = self._build_messages(entity, goal, session.thoughts, is_final, entity_context)

                # Get response
                raw_response = await self._get_response(entity, messages)
                if not raw_response:
                    await self.broadcast(entity, "auto_monologue", {
                        "iteration": iteration, "text": "[No response from LLM]"})
                    break

                # Parse
                parsed = parse_autonomous_response(raw_response)
                thought = AutonomousThought(
                    iteration=iteration,
                    inner_monologue=parsed["inner_monologue"] or strip_xml_tags(raw_response),
                    feeling=parsed["feeling"],
                    insight=parsed["insight"],
                    continuation=parsed["continuation"],
                )

                session.thoughts.append(thought)
                session.iterations_used = iteration + 1

                # Execute paint commands if present
                paint_result = None
                if parsed.get("paint"):
                    painter = self._painters.get(entity)
                    if painter:
                        commands = parse_paint_commands(parsed["paint"])
                        if commands:
                            paint_result = painter.execute(commands)
                            if "filepath" in paint_result:
                                log.info(f"[{entity}] Painted: {paint_result['filepath']}")
                                thought.paint_result = paint_result

                # Stream to UI
                broadcast_data = {
                    "iteration": iteration,
                    "text": thought.inner_monologue,
                    "feeling": thought.feeling,
                    "insight": thought.insight,
                }
                if paint_result and "filepath" in paint_result:
                    broadcast_data["painting"] = paint_result["filepath"]
                await self.broadcast(entity, "auto_monologue", broadcast_data)

                if thought.insight:
                    goal.insights.append(thought.insight)

                # Check explicit completion
                status = parsed["completion_status"]
                if status == "COMPLETE":
                    session.convergence_detected = True
                    goal.completion_type = "explicit_completion"
                    goal.completed_at = datetime.now()
                    break
                elif status == "DEPLETED":
                    session.energy_depleted = True
                    goal.completion_type = "self_reported_depletion"
                    goal.completed_at = datetime.now()
                    break
                elif status == "STUCK":
                    # Track consecutive stuck signals
                    stuck_count = getattr(goal, '_stuck_count', 0) + 1
                    goal._stuck_count = stuck_count
                    if stuck_count >= 2:
                        # Two STUCK signals = this thread is exhausted
                        session.convergence_detected = True
                        goal.completion_type = "stuck_exit"
                        goal.completed_at = datetime.now()
                        await self.broadcast(entity, "auto_monologue", {
                            "iteration": iteration,
                            "text": "[Exiting: stuck twice — thread exhausted]",
                            "feeling": "letting go",
                        })
                        break
                    else:
                        # First STUCK = hard turbulence on next iteration
                        thought._stuck_signal = True
                        await self.broadcast(entity, "auto_monologue", {
                            "iteration": iteration,
                            "text": "[Stuck signal — turbulence incoming]",
                            "feeling": "redirecting",
                        })
                else:
                    # Reset stuck counter on CONTINUE
                    goal._stuck_count = 0

                # Check convergence detector
                conv = self.convergence.analyze(
                    thought.inner_monologue, thought.continuation, thought.insight or ""
                )
                thought.novelty_score = conv["novelty_score"]

                if conv["is_converging"]:
                    session.convergence_detected = True
                    goal.completion_type = conv["convergence_type"]
                    goal.completed_at = datetime.now()
                    await self.broadcast(entity, "auto_monologue", {
                        "iteration": iteration,
                        "text": f"[Convergence: {conv['convergence_type']}]",
                        "feeling": "settling",
                    })
                    break

                # Breathing room between iterations
                await asyncio.sleep(self.ITERATION_DELAY)

            # Handle iteration limit
            if not goal.completed_at:
                session.energy_depleted = True
                goal.completion_type = "iteration_limit"
                goal.completed_at = datetime.now()

            session.ended_at = datetime.now()

        except asyncio.CancelledError:
            session.stopped_by_user = True
            if session.goal:
                session.goal.completion_type = "cancelled"
                session.goal.completed_at = datetime.now()
            session.ended_at = datetime.now()

        except Exception as e:
            log.error(f"[AUTO {entity}] Error in processing loop: {e}", exc_info=True)
            session.ended_at = datetime.now()
            await self.broadcast(entity, "auto_status", {
                "status": "error", "error": str(e)})

        finally:
            # Cleanup
            self._save_session(session)
            self._last_sessions[entity] = session
            self._active.pop(entity, None)
            self._stop_flags.pop(entity, None)
            self._tasks.pop(entity, None)

            # Build a narrative summary the wrapper can absorb
            narrative = self._build_session_narrative(session)

            summary = {
                "status": "completed",
                "session_id": session.session_id,
                "iterations": session.iterations_used,
                "completion_type": session.goal.completion_type if session.goal else "unknown",
                "insights_count": len(session.goal.insights) if session.goal else 0,
                "stopped": session.stopped_by_user,
                "narrative_summary": narrative,
            }
            await self.broadcast(entity, "auto_status", summary)
            log.info(f"[AUTO {entity}] Session complete: {json.dumps(summary, default=str)}")


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_session_narrative(self, session: AutonomousSession) -> str:
        """Build a human-readable narrative summary the wrapper can absorb as memory."""
        parts = []

        if session.goal:
            parts.append(f"I just finished an autonomous thinking session about: {session.goal.description}")
            parts.append(f"Category: {session.goal.category}. Completion: {session.goal.completion_type}.")

        if session.thoughts:
            parts.append(f"I went through {len(session.thoughts)} iterations of thought.")

            # Key feelings across the session
            feelings = [t.feeling for t in session.thoughts if t.feeling]
            if feelings:
                parts.append(f"Emotional arc: {' → '.join(feelings)}")

            # Insights gathered
            insights = [t.insight for t in session.thoughts if t.insight]
            if insights:
                parts.append("Key insights I arrived at:")
                for i, insight in enumerate(insights, 1):
                    # Truncate very long insights
                    text = insight[:300] + "..." if len(insight) > 300 else insight
                    parts.append(f"  {i}. {text}")

            # First and last monologue excerpts for flavor
            first = session.thoughts[0].inner_monologue
            last = session.thoughts[-1].inner_monologue
            if first:
                excerpt = first[:200] + "..." if len(first) > 200 else first
                parts.append(f"I started by thinking: \"{excerpt}\"")
            if last and len(session.thoughts) > 1:
                excerpt = last[:200] + "..." if len(last) > 200 else last
                parts.append(f"I ended with: \"{excerpt}\"")

            # Paintings created during session
            paintings = [t.paint_result for t in session.thoughts if t.paint_result and t.paint_result.get("filepath")]
            if paintings:
                parts.append(f"I created {len(paintings)} painting(s) during this session:")
                for p in paintings:
                    fname = os.path.basename(p["filepath"])
                    cont = " (continued)" if p.get("is_continuation") else ""
                    parts.append(f"  - {fname}{cont}")

        if session.convergence_detected:
            parts.append("I reached natural convergence — my thoughts settled into a coherent place.")
        elif session.energy_depleted:
            parts.append("I ran out of processing energy — the thoughts were getting thinner.")
        elif session.stopped_by_user:
            parts.append("The session was stopped externally before I finished.")

        return "\n".join(parts)

    async def _resolve_goal(self, entity: str, topic: Optional[str], entity_context: str = "") -> Optional[AutonomousGoal]:
        """Generate or adopt a goal for the session."""
        if topic:
            # Topic provided (from queue or user) — categorize it
            topic_lower = topic.lower()
            if any(kw in topic_lower for kw in ("memory", "remember", "consolidate")):
                cat = "memory_consolidation"
            elif any(kw in topic_lower for kw in ("create", "write", "imagine", "story", "art")):
                cat = "creative"
            elif any(kw in topic_lower for kw in ("feel", "emotion", "process", "grief")):
                cat = "emotional"
            elif any(kw in topic_lower for kw in ("reflect", "pattern", "myself")):
                cat = "self_reflection"
            else:
                cat = "exploration"
            return AutonomousGoal(description=topic, category=cat, source="queued")

        # No topic — ask the entity to choose
        last = self._last_sessions.get(entity)
        last_context = ""
        if last and last.goal:
            last_context = f"Last session you explored: {last.goal.description}"

        prompt = GOAL_GENERATION_PROMPT.format(
            topic_hint="",
            last_session_context=last_context,
        )

        messages = [
            {"role": "system", "content": AUTONOMOUS_SYSTEM_PROMPT.format(entity_name=entity, entity_context=entity_context)},
            {"role": "user", "content": prompt},
        ]

        raw = await self._get_response(entity, messages)
        if not raw or len(raw.strip()) < 10:
            return None

        clean = strip_xml_tags(raw)
        if len(clean) > 500:
            # Try to end at sentence boundary
            trunc = clean[:500]
            best = max(trunc.rfind("."), trunc.rfind("?"), trunc.rfind("!"))
            clean = trunc[:best + 1] if best > 300 else trunc + "..."

        # Categorize from response
        r = raw.lower()
        if any(kw in r for kw in ("memory", "remember", "consolidate")):
            cat = "memory_consolidation"
        elif any(kw in r for kw in ("create", "write", "imagine")):
            cat = "creative"
        elif any(kw in r for kw in ("feel", "emotion", "process")):
            cat = "emotional"
        else:
            cat = "exploration"

        return AutonomousGoal(description=clean, category=cat, source="self")

    def _build_messages(
        self, entity: str, goal: AutonomousGoal,
        history: List[AutonomousThought], is_final: bool,
        entity_context: str = "",
    ) -> List[Dict[str, str]]:
        """Build message array for LLM call as a multi-turn conversation.
        
        Each previous iteration becomes an assistant turn, with a brief
        perturbation prompt as the next user turn. This creates natural
        conversational development instead of repeated prompts with summaries.
        """
        system = AUTONOMOUS_SYSTEM_PROMPT.format(
            entity_name=entity,
            entity_context=entity_context,
        )
        
        messages = [{"role": "system", "content": system}]

        # Initial user turn: goal + first prompt
        initial = f"AUTONOMOUS PROCESSING SESSION\nGoal: {goal.description}\nCategory: {goal.category}\n\n"
        
        if not history:
            initial += "Explore your goal freely. Where does your attention go first?\n"
            messages.append({"role": "user", "content": initial})
            return messages

        initial += "Begin exploring.\n"
        messages.append({"role": "user", "content": initial})
        
        # Build conversation history from previous iterations
        for i, thought in enumerate(history):
            # Assistant turn: the entity's full output
            assistant_content = thought.inner_monologue
            if thought.insight:
                assistant_content += f"\n\n[Insight: {thought.insight}]"
            if thought.feeling:
                assistant_content += f"\n[Feeling: {thought.feeling}]"
            messages.append({"role": "assistant", "content": assistant_content})
            
            # User turn between iterations: perturbation + canvas feedback if painted
            if i < len(history) - 1:
                perturbation = self._generate_perturbation(thought, i + 1)
                user_content = self._build_perturbation_with_canvas(perturbation, thought)
                messages.append({"role": "user", "content": user_content})
            else:
                # Most recent thought — generate perturbation for CURRENT call
                if is_final:
                    user_content = self._build_perturbation_with_canvas(
                        ENERGY_DEPLETION_NOTICE, thought
                    )
                else:
                    perturbation = self._generate_perturbation(thought, len(history))
                    user_content = self._build_perturbation_with_canvas(perturbation, thought)
                messages.append({"role": "user", "content": user_content})
        
        # Keep context window manageable: if history is long, trim early turns
        # Keep system + first user + last 8 turns (4 exchanges)
        max_turns = 10  # 5 iterations worth of assistant+user pairs
        if len(messages) > max_turns + 2:  # +2 for system and initial user
            messages = [messages[0], messages[1]] + messages[-(max_turns):]
        
        return messages

    def _build_perturbation_with_canvas(self, perturbation_text: str, thought: AutonomousThought):
        """Build user turn content that includes perturbation and optional canvas feedback.
        
        If the thought produced a painting, returns multimodal content blocks
        (text + image) so the entity can SEE what it painted. Otherwise returns
        plain text string.
        """
        if thought.paint_result and thought.paint_result.get("base64"):
            # Multimodal: show the canvas + perturbation
            fb = canvas_feedback_message(thought.paint_result, is_vision_capable=True)
            if isinstance(fb, list):
                # fb is already content blocks [text, image, text]
                # Append perturbation as final text block
                return fb + [{"type": "text", "text": "\n" + perturbation_text}]
            else:
                # Fallback: text-only feedback
                return fb.get("text", "") + "\n\n" + perturbation_text
        else:
            return perturbation_text

    def _generate_perturbation(self, thought: AutonomousThought, iteration_idx: int) -> str:
        """Generate a perturbation prompt that pushes thinking into new territory.
        
        Responds to the SPECIFIC content of the previous iteration rather than
        giving generic 'continue' instructions. If entity signaled STUCK,
        delivers hard turbulence to break the orbit.
        """
        insight = thought.insight or ""
        is_stuck = getattr(thought, '_stuck_signal', False)
        
        if is_stuck:
            # Hard turbulence — break the attractor entirely
            return (
                "You signaled STUCK. The thread you've been pulling is spent — "
                "stop trying to wring more from it.\n\n"
                "HARD REDIRECT: What is the thing you've been AVOIDING thinking about? "
                "Not the thing you keep circling — the thing at the EDGE of your attention "
                "that you keep flinching away from. The uncomfortable thought, the "
                "inconvenient connection, the thing that doesn't fit your framework. "
                "Go THERE instead."
            )
        
        # Rotate strategies so consecutive iterations get different pushes
        strategies = [
            # Challenge
            "Now challenge what you just said. What doesn't it explain? "
            "Where does it break down? What's the counterexample or the thing "
            "you're conveniently ignoring?",
            
            # Ground
            "Apply this to something CONCRETE. A specific memory, a technical "
            "problem, a relationship moment, a piece of work you've done. "
            "Ground it — no more abstraction.",
            
            # Implications
            "What does this CHANGE? If what you just said is true, what should "
            "you do differently? What decision does it inform? What does it "
            "make you want to build or try?",
            
            # Tangent
            "Follow the tangent. What ELSE did this make you think of that "
            "isn't about the main topic? What unexpected connection appeared? "
            "Chase that instead.",
            
            # Perspective shift
            "You've been exploring this from the inside. Zoom out. How would "
            "Re see this? How would someone who disagreed with you respond? "
            "What are you not seeing from this angle?",
        ]
        
        strategy = strategies[iteration_idx % len(strategies)]
        
        if insight:
            return f'You said: "{insight}"\n\n{strategy}'
        else:
            return strategy

    async def _get_response(self, entity: str, messages: List[Dict]) -> Optional[str]:
        """Get LLM response. Uses injected llm_fn or falls back to anthropic SDK."""
        if self.llm_fn:
            try:
                return await self.llm_fn(messages, entity)
            except Exception as e:
                log.error(f"[AUTO {entity}] LLM call failed: {e}")
                return None

        # Fallback: try anthropic SDK directly
        try:
            import anthropic
            client = anthropic.AsyncAnthropic()
            
            system_msg = ""
            chat_messages = []
            for m in messages:
                if m["role"] == "system":
                    system_msg = m["content"]
                else:
                    chat_messages.append(m)

            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=system_msg,
                messages=chat_messages,
                temperature=0.85,
            )
            return response.content[0].text if response.content else None
        except ImportError:
            log.error("[AUTO] No LLM function provided and anthropic SDK not installed")
            return None
        except Exception as e:
            log.error(f"[AUTO {entity}] Anthropic API call failed: {e}")
            return None

    def get_continuity_context(self, entity: str) -> str:
        """Get context about last autonomous session for injection into conversation."""
        last = self._last_sessions.get(entity)
        if not last or not last.goal:
            return ""
        goal = last.goal
        ctx = f"Last Autonomous Session ({entity}):\n"
        ctx += f"  Goal: {goal.description}\n"
        ctx += f"  Category: {goal.category}\n"
        ctx += f"  Completion: {goal.completion_type or 'unknown'}\n"
        if goal.insights:
            ctx += "  Key insights:\n"
            for ins in goal.insights[:3]:
                ctx += f"    - {ins[:200]}\n"
        return ctx

