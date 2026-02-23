"""
Session Boundary Handler
Generates session summaries and ensures continuity across session restarts
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


@dataclass
class SessionSummary:
    """
    Captures critical state at session end for guaranteed restoration
    """
    session_id: str
    timestamp: str

    # Last exchange (guaranteed to load)
    last_user_message: str
    last_agent_response: str

    # Entity's reactions to new information this session
    key_reactions: List[Dict[str, str]]  # [{"trigger": "...", "reaction": "..."}]

    # Active threads
    open_threads: List[Dict[str, Any]]  # From ThreadMomentumTracker

    # Emotional/cognitive state
    emotional_state: Dict[str, float]  # emotion -> intensity
    cognitive_state: str  # LLM-generated description

    # Plans and unresolved items
    open_questions: List[str]
    future_intentions: List[str]  # Things the entity wants to explore

    # Core identity anchors (to prevent drift)
    core_preferences: List[str]  # Top 5 most stable preferences

    # Import tracking
    recent_imports: List[str]  # Document/memory IDs imported this session
    import_reactions: Dict[str, str]  # import_id -> reaction summary

    # Metadata
    total_turns: int
    memory_stats: Dict[str, int]  # Layer distribution


class SessionBoundaryHandler:
    """
    Manages session transitions - creates summaries at end, ensures loading at start
    """

    def __init__(self, llm_client):
        """
        Args:
            llm_client: LLM client for generating summaries (must have .query() method)
        """
        self.llm = llm_client
        self.current_session_reactions = []
        self.current_session_imports = []

    def track_reaction(self, trigger: str, reaction: str):
        """
        Track entity's reaction to new information during session

        Args:
            trigger: What caused the reaction (e.g., "learned owner has a dog named Saga")
            reaction: Entity's response/feeling about it
        """
        self.current_session_reactions.append({
            "trigger": trigger,
            "reaction": reaction,
            "timestamp": datetime.now().isoformat()
        })

    def track_import(self, import_id: str, import_description: str):
        """
        Track document/memory import during session

        Args:
            import_id: Unique ID for the imported content
            import_description: Brief description of what was imported
        """
        self.current_session_imports.append({
            "id": import_id,
            "description": import_description,
            "timestamp": datetime.now().isoformat()
        })

    async def generate_session_end_summary(
        self,
        session_id: str,
        conversation_history: List[Dict[str, str]],
        thread_tracker,  # ThreadMomentumTracker instance
        emotional_state: Dict[str, float],
        memory_store,  # Access to memory retrieval
        entity_graph  # Access to entity preferences
    ) -> SessionSummary:
        """
        Generate comprehensive session summary at session end

        Args:
            session_id: Unique session identifier
            conversation_history: List of {"role": "user"/"assistant", "content": "..."}
            thread_tracker: ThreadMomentumTracker instance
            emotional_state: Current emotional cocktail
            memory_store: Access to memory system for stats
            entity_graph: Access to core preferences

        Returns:
            SessionSummary object ready for persistence
        """

        # Extract last exchange
        last_user = ""
        last_agent = ""
        for msg in reversed(conversation_history):
            if msg["role"] == "user" and not last_user:
                last_user = msg["content"]
            if msg["role"] == "assistant" and not last_agent:
                last_agent = msg["content"]
            if last_user and last_agent:
                break

        # Generate cognitive state summary using LLM
        cognitive_state = await self._generate_cognitive_state(
            conversation_history[-10:],  # Last 10 turns
            emotional_state,
            self.current_session_reactions
        )

        # Extract open questions
        open_questions = []
        for msg in reversed(conversation_history):
            if msg["role"] == "assistant" and "?" in msg["content"]:
                # Extract questions from agent responses
                questions = [
                    q.strip() + "?"
                    for q in msg["content"].split("?")[:-1]
                    if len(q.strip()) > 10
                ]
                open_questions.extend(questions[:2])  # Max 2 per response
                if len(open_questions) >= 5:
                    break

        # Extract future intentions from recent agent responses
        future_intentions = await self._extract_future_intentions(
            conversation_history[-5:]  # Last 5 turns
        )

        # Get thread summary
        thread_summary = thread_tracker.get_thread_summary()

        # Get memory stats
        memory_stats = memory_store.get_layer_distribution()

        # Get core preferences (top 5 most stable)
        core_preferences = entity_graph.get_top_preferences(limit=5)

        # Generate import reactions
        import_reactions = {}
        for import_data in self.current_session_imports:
            reaction = await self._generate_import_reaction(
                import_data,
                conversation_history
            )
            import_reactions[import_data["id"]] = reaction

        summary = SessionSummary(
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            last_user_message=last_user,
            last_agent_response=last_agent,
            key_reactions=self.current_session_reactions[-10:],  # Last 10 reactions
            open_threads=thread_summary["active_threads"],
            emotional_state=emotional_state,
            cognitive_state=cognitive_state,
            open_questions=open_questions[:5],
            future_intentions=future_intentions,
            core_preferences=[p["description"] for p in core_preferences],
            recent_imports=[imp["id"] for imp in self.current_session_imports],
            import_reactions=import_reactions,
            total_turns=len(conversation_history) // 2,
            memory_stats=memory_stats
        )

        # Reset session tracking
        self.current_session_reactions = []
        self.current_session_imports = []

        return summary

    async def _generate_cognitive_state(
        self,
        recent_turns: List[Dict[str, str]],
        emotional_state: Dict[str, float],
        reactions: List[Dict[str, str]]
    ) -> str:
        """
        Use LLM to generate natural language description of cognitive state
        """

        # Build prompt
        emotions_str = ", ".join([
            f"{emotion} ({intensity:.2f})"
            for emotion, intensity in sorted(
                emotional_state.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
        ])

        reactions_str = "\n".join([
            f"- {r['trigger']}: {r['reaction']}"
            for r in reactions[-5:]
        ])

        prompt = f"""Based on this conversation excerpt, describe the entity's current cognitive state in 1-2 sentences.

Recent conversation:
{self._format_conversation(recent_turns)}

Current emotions: {emotions_str}

Recent reactions:
{reactions_str}

Generate a brief, natural description of the entity's mental state (what they're focused on, how they're feeling, what they're processing):"""

        response = await self.llm.query(
            prompt,
            max_tokens=100,
            temperature=0.3
        )

        return response.strip()

    async def _extract_future_intentions(
        self,
        recent_turns: List[Dict[str, str]]
    ) -> List[str]:
        """
        Extract things the entity mentioned wanting to explore/do later
        """

        prompt = f"""Extract any future intentions or things the entity wants to explore later from this conversation.

Conversation:
{self._format_conversation(recent_turns)}

List any statements about:
- Things they want to learn more about
- Topics they want to revisit
- Actions they plan to take
- Questions they want to explore

Return as a JSON list of strings (max 5 items). If none, return empty list.
"""

        response = await self.llm.query(
            prompt,
            max_tokens=150,
            temperature=0.2
        )

        try:
            intentions = json.loads(response.strip())
            return intentions[:5]
        except json.JSONDecodeError:
            return []

    async def _generate_import_reaction(
        self,
        import_data: Dict,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Generate summary of entity's reaction to imported document
        """

        # Find conversation around import time
        import_time = datetime.fromisoformat(import_data["timestamp"])

        # Get ~5 turns of context around import
        context_turns = conversation_history[-10:]

        prompt = f"""An entity was exposed to new information: "{import_data['description']}"

Conversation context:
{self._format_conversation(context_turns)}

In 1-2 sentences, summarize how the entity reacted to or integrated this new information:"""

        response = await self.llm.query(
            prompt,
            max_tokens=80,
            temperature=0.3
        )

        return response.strip()

    def _format_conversation(self, turns: List[Dict[str, str]]) -> str:
        """Format conversation turns for prompts"""
        formatted = []
        for turn in turns:
            role = "User" if turn["role"] == "user" else "Entity"
            formatted.append(f"{role}: {turn['content']}")
        return "\n".join(formatted)

    def save_summary(self, summary: SessionSummary, filepath: str):
        """Persist summary to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(asdict(summary), f, indent=2)

    def load_summary(self, filepath: str) -> Optional[SessionSummary]:
        """Load summary from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return SessionSummary(**data)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def generate_session_start_context(
        self,
        summary: SessionSummary,
        max_length: int = 1000
    ) -> str:
        """
        Generate guaranteed context block to inject at session start

        This ensures continuity by loading critical information regardless of
        retrieval scoring

        Args:
            summary: Previous session summary
            max_length: Max characters for context block

        Returns:
            Formatted context string for LLM prompt
        """

        parts = []

        # Last exchange
        parts.append("=== LAST SESSION EXCHANGE ===")
        parts.append(f"User: {summary.last_user_message[:200]}")
        parts.append(f"You: {summary.last_agent_response[:200]}")
        parts.append("")

        # Cognitive state
        parts.append("=== YOUR MENTAL STATE ===")
        parts.append(summary.cognitive_state)
        if summary.emotional_state:
            top_emotions = sorted(
                summary.emotional_state.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            emotions_str = ", ".join([f"{e} ({i:.2f})" for e, i in top_emotions])
            parts.append(f"Emotions: {emotions_str}")
        parts.append("")

        # Open threads
        if summary.open_threads:
            parts.append("=== ACTIVE CONVERSATION THREADS ===")
            for thread in summary.open_threads[:3]:
                parts.append(f"• {', '.join(thread['entities'][:3])}")
                if thread['open_questions']:
                    parts.append(f"  Unresolved: {thread['open_questions'][0]}")
            parts.append("")

        # Key reactions
        if summary.key_reactions:
            parts.append("=== YOUR RECENT REACTIONS ===")
            for reaction in summary.key_reactions[-3:]:
                parts.append(f"• {reaction['trigger']}")
                parts.append(f"  → {reaction['reaction']}")
            parts.append("")

        # Import reactions
        if summary.import_reactions:
            parts.append("=== NEW INFORMATION PROCESSED ===")
            for import_id, reaction in list(summary.import_reactions.items())[:3]:
                parts.append(f"• {reaction}")
            parts.append("")

        # Open questions
        if summary.open_questions:
            parts.append("=== QUESTIONS YOU ASKED ===")
            for q in summary.open_questions[:3]:
                parts.append(f"• {q}")
            parts.append("")

        # Future intentions
        if summary.future_intentions:
            parts.append("=== THINGS YOU WANTED TO EXPLORE ===")
            for intention in summary.future_intentions[:3]:
                parts.append(f"• {intention}")
            parts.append("")

        # Core identity
        if summary.core_preferences:
            parts.append("=== YOUR CORE PREFERENCES ===")
            for pref in summary.core_preferences[:3]:
                parts.append(f"• {pref}")

        # Join and truncate
        context = "\n".join(parts)
        if len(context) > max_length:
            context = context[:max_length] + "\n\n[Context truncated]"

        return context
