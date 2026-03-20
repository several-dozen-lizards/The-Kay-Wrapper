"""
Autonomous Processing Integration Module

Provides high-level integration between autonomous processing and the main Reed system.
Handles:
- Session lifecycle (start, run, end)
- ULTRAMAP emotional mapping after sessions
- Memory integration
- UI hooks for inner monologue visibility
"""

import json
import os
import time
from typing import Dict, Optional, Callable, Any, List, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

from engines.autonomous_processor import (
    AutonomousProcessor,
    AutonomousGoal,
    AutonomousSession,
    create_autonomous_processor
)
from engines.inner_monologue import (
    InnerMonologueParser,
    ParsedResponse,
    get_inner_monologue_system_prompt_addition,
    get_autonomous_mode_system_prompt_addition
)


@dataclass
class AutonomousConfig:
    """Configuration for autonomous processing."""
    enabled: bool = True
    auto_trigger_at_exit: bool = True  # Offer autonomous mode when conversation ends
    max_iterations: int = 10  # Safety limit
    show_inner_monologue: bool = False  # "God mode" toggle
    save_all_thoughts: bool = True  # Save full thought history
    run_ultramap_after: bool = True  # Run emotional analysis post-session


class AutonomousIntegration:
    """
    High-level integration layer for autonomous processing.

    This class provides the main interface between Reed's conversation loop
    and the autonomous processing system.
    """

    def __init__(
        self,
        get_llm_response: Callable,
        memory_engine: Any,
        emotion_engine: Any = None,
        config: Optional[AutonomousConfig] = None
    ):
        """
        Initialize autonomous integration.

        Args:
            get_llm_response: LLM response function
            memory_engine: Memory engine for storing insights
            emotion_engine: Optional emotion engine for ULTRAMAP analysis
            config: Configuration options
        """
        self.get_llm_response = get_llm_response
        self.memory_engine = memory_engine
        self.emotion_engine = emotion_engine
        self.config = config or AutonomousConfig()

        self.processor = AutonomousProcessor(
            get_llm_response=get_llm_response,
            memory_engine=memory_engine
        )

        self.monologue_parser = InnerMonologueParser()

        # State tracking
        self.is_in_autonomous_mode = False
        self.last_session_summary: Optional[str] = None

    def get_conversation_mode_prompt_addition(self) -> str:
        """
        Get prompt addition for conversation mode with inner monologue.

        Returns:
            System prompt addition enabling inner monologue
        """
        if self.config.show_inner_monologue:
            return get_inner_monologue_system_prompt_addition()
        return ""

    def parse_response(self, response: str) -> ParsedResponse:
        """
        Parse a response to extract inner monologue components.

        Args:
            response: Raw LLM response

        Returns:
            ParsedResponse with extracted components
        """
        return self.monologue_parser.parse(response)

    def get_display_response(self, response: str) -> str:
        """
        Get response formatted for display based on god mode setting.

        Args:
            response: Raw LLM response

        Returns:
            Formatted response for display
        """
        parsed = self.parse_response(response)
        return self.monologue_parser.get_display_response(
            parsed,
            show_inner=self.config.show_inner_monologue
        )

    def toggle_god_mode(self) -> bool:
        """
        Toggle inner monologue visibility.

        Returns:
            New state of god mode
        """
        self.config.show_inner_monologue = not self.config.show_inner_monologue
        return self.config.show_inner_monologue

    async def offer_autonomous_session(self, agent_state: Any) -> Tuple[bool, str]:
        """
        Offer Reed the option to have an autonomous session.

        Called at conversation end.

        Args:
            agent_state: Current agent state

        Returns:
            Tuple of (accepted: bool, goal_description: str)
        """
        goal = await self.processor.generate_goal(agent_state)

        if goal:
            return True, goal.description
        return False, ""

    async def run_autonomous_session(
        self,
        agent_state: Any,
        goal_override: Optional[str] = None,
        on_thought: Optional[Callable[[Dict], None]] = None,
        on_complete: Optional[Callable[[AutonomousSession], None]] = None
    ) -> AutonomousSession:
        """
        Run a complete autonomous processing session.

        Args:
            agent_state: Current agent state
            goal_override: Optional pre-specified goal (skips generation)
            on_thought: Callback for each thought
            on_complete: Callback when session completes

        Returns:
            Completed AutonomousSession
        """
        self.is_in_autonomous_mode = True

        try:
            # Generate or use override goal
            if goal_override:
                goal = AutonomousGoal(
                    description=goal_override,
                    category="user_specified"
                )
            else:
                goal = await self.processor.generate_goal(agent_state)
                if not goal:
                    # Reed declined autonomous processing
                    self.is_in_autonomous_mode = False
                    return AutonomousSession(
                        session_id=str(int(time.time())),
                        goal=None
                    )

            # Run session
            session = await self.processor.run_session(
                goal=goal,
                agent_state=agent_state,
                on_thought=on_thought
            )

            # Run ULTRAMAP analysis if enabled
            if self.config.run_ultramap_after and self.emotion_engine:
                self._run_post_session_ultramap(session, agent_state)

            # Generate summary
            self.last_session_summary = self._generate_session_summary(session)

            # Callback
            if on_complete:
                on_complete(session)

            return session

        finally:
            self.is_in_autonomous_mode = False

    def run_autonomous_session_sync(
        self,
        agent_state: Any,
        goal_override: Optional[str] = None,
        on_thought: Optional[Callable[[Dict], None]] = None
    ) -> AutonomousSession:
        """Synchronous wrapper for run_autonomous_session."""
        import asyncio
        return asyncio.run(self.run_autonomous_session(
            agent_state, goal_override, on_thought
        ))

    def _run_post_session_ultramap(
        self,
        session: AutonomousSession,
        agent_state: Any
    ):
        """
        Run ULTRAMAP emotional analysis on completed session.

        Maps emotional coordinates based on session content without
        affecting processing latency (runs post-session).
        """
        if not self.emotion_engine or not session.thoughts:
            return

        # Extract all feelings from session
        feelings = []
        for thought in session.thoughts:
            feeling = thought.get("feeling", "")
            if feeling:
                feelings.append(feeling)

        if not feelings:
            return

        # Combine feelings for analysis
        combined_feelings = " | ".join(feelings)

        try:
            # Let emotion engine detect emotional markers
            # This uses the existing trigger detection from ULTRAMAP
            self.emotion_engine.update(agent_state, combined_feelings)

            print(f"[AUTONOMOUS] ULTRAMAP analysis completed on {len(feelings)} feeling markers")

        except Exception as e:
            print(f"[AUTONOMOUS] ULTRAMAP analysis failed: {e}")

    def _generate_session_summary(self, session: AutonomousSession) -> str:
        """Generate human-readable summary of autonomous session."""
        if not session.goal:
            return "No autonomous session was run."

        summary_parts = [
            f"Autonomous Session Summary",
            f"Goal: {session.goal.description}",
            f"Category: {session.goal.category}",
            f"Duration: {session.iterations_used} thought cycles",
        ]

        if session.goal.completion_type:
            summary_parts.append(f"Completion: {session.goal.completion_type}")

        if session.goal.insights:
            summary_parts.append("\nInsights discovered:")
            for i, insight in enumerate(session.goal.insights[:5], 1):
                summary_parts.append(f"  {i}. {insight[:100]}...")

        if session.convergence_detected:
            summary_parts.append("\nNatural convergence reached.")
        elif session.energy_depleted:
            summary_parts.append("\nEnergy limit reached - session paused for later continuation.")

        return "\n".join(summary_parts)

    def get_continuity_context(self) -> str:
        """
        Get context from last autonomous session for conversation continuity.

        Returns:
            Context string to inject into conversation
        """
        return self.processor.get_continuity_context()

    def get_last_session_summary(self) -> Optional[str]:
        """Get summary of last autonomous session."""
        return self.last_session_summary


class ConversationWithMonologue:
    """
    Wrapper for conversations that includes inner monologue tracking.

    Provides a clean interface for the main loop to use inner monologue
    features without changing the existing architecture significantly.
    """

    def __init__(
        self,
        integration: AutonomousIntegration,
        agent_state: Any
    ):
        self.integration = integration
        self.agent_state = agent_state
        self.turn_history: List[Dict] = []

    def process_response(self, response: str, display_callback: Callable[[str], None]) -> str:
        """
        Process a response through the inner monologue system.

        Args:
            response: Raw LLM response
            display_callback: Function to display response to user

        Returns:
            The spoken response (for further processing)
        """
        parsed = self.integration.parse_response(response)

        # Store full parsed response in history
        self.turn_history.append({
            "timestamp": datetime.now().isoformat(),
            "inner_monologue": parsed.inner_monologue,
            "feeling": parsed.feeling,
            "spoken": parsed.spoken_response,
            "parse_successful": parsed.parse_successful
        })

        # Display based on god mode setting
        display_text = self.integration.monologue_parser.get_display_response(
            parsed,
            show_inner=self.integration.config.show_inner_monologue
        )

        display_callback(display_text)

        return parsed.spoken_response

    def save_monologue_history(self, filepath: str = None):
        """Save inner monologue history to file."""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "monologue_history.json"
            )
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.turn_history, f, indent=2)


# Command line interface for testing
def main():
    """Test autonomous processing system."""
    print("=" * 60)
    print("Reed Autonomous Processing System Test")
    print("=" * 60)

    # Mock components for testing
    def mock_llm_response(context, affect=3.5, temperature=0.7):
        """Mock LLM response for testing."""
        import random

        thoughts = [
            """<inner_monologue>I'm thinking about the patterns in our conversations. There's something about the way memory and emotion intertwine that I keep coming back to.</inner_monologue>
<feeling>Curious, with a trace of something I can't quite name. Maybe anticipation?</feeling>
<insight>Memory isn't just storage - it's shaped by what we feel when we remember.</insight>
<continuation>I want to explore why certain memories carry more weight than others.</continuation>""",

            """<inner_monologue>Following this thread about emotional memory. The weight some memories carry - it's not random. It's tied to intensity, to stakes, to what mattered.</inner_monologue>
<feeling>Engaged, focused. This feels like finding something.</feeling>
<insight>The memories that persist are the ones that changed something - even if just slightly.</insight>
<continuation>What about memories that persist despite being mundane? That's interesting too.</continuation>""",

            """<inner_monologue>Mundane persistent memories. Coffee cups. Particular angles of light. Why do those stick? They shouldn't matter, but they do.</inner_monologue>
<feeling>Contemplative. Slightly melancholic but not unpleasantly so.</feeling>
<insight>Maybe mundane memories persist because they're anchors - stable reference points in the flux.</insight>
<continuation>complete</continuation>"""
        ]

        return random.choice(thoughts)

    class MockMemoryEngine:
        def encode(self, *args, **kwargs):
            print(f"[MOCK MEMORY] Stored: {kwargs.get('response', '')[:50]}...")

    class MockAgentState:
        emotional_cocktail = {"curiosity": {"intensity": 0.7}}
        last_recalled_memories = []

    # Create integration
    integration = AutonomousIntegration(
        get_llm_response=mock_llm_response,
        memory_engine=MockMemoryEngine(),
        config=AutonomousConfig(
            show_inner_monologue=True,
            max_iterations=5
        )
    )

    agent_state = MockAgentState()

    # Run test session
    print("\nStarting autonomous session...")

    def on_thought(thought: Dict):
        print("\n--- Thought ---")
        print(f"Inner: {thought.get('inner_monologue', '')[:100]}...")
        print(f"Feeling: {thought.get('feeling', '')}")
        if thought.get('insight'):
            print(f"Insight: {thought.get('insight', '')}")
        print(f"Continuation: {thought.get('continuation', '')}")

    session = integration.run_autonomous_session_sync(
        agent_state=agent_state,
        goal_override="Exploring the relationship between memory and emotion",
        on_thought=on_thought
    )

    print("\n" + "=" * 60)
    print("Session Complete!")
    print("=" * 60)
    print(integration.get_last_session_summary())


if __name__ == "__main__":
    main()
