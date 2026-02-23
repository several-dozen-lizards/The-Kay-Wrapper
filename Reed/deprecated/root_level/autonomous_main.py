"""
Reed Main Loop with Autonomous Processing

This is an alternative main.py that integrates:
- Inner monologue parsing (with optional god mode display)
- Autonomous processing sessions at conversation end
- Session continuity across autonomous spaces

Usage:
  python autonomous_main.py

Commands:
  /auto - Start an autonomous processing session manually
  /godmode - Toggle inner monologue visibility
  /lastthought - Show summary of last autonomous session
  quit/exit - Exit (offers autonomous session first)
"""

import asyncio
import os
import json
import time
from agent_state import AgentState
from protocol_engine import ProtocolEngine
from config import VERBOSE_DEBUG

# Engine imports
from engines.emotion_engine import EmotionEngine
from engines.emotion_extractor import EmotionExtractor
from engines.memory_engine import MemoryEngine
from engines.social_engine import SocialEngine
from engines.temporal_engine import TemporalEngine
from engines.embodiment_engine import EmbodimentEngine
from engines.reflection_engine import ReflectionEngine
from engines.context_manager import ContextManager
from engines.summarizer import Summarizer
from engines.motif_engine import MotifEngine
from engines.momentum_engine import MomentumEngine
from engines.meta_awareness_engine import MetaAwarenessEngine

# Autonomous processing imports
from engines.autonomous_integration import (
    AutonomousIntegration,
    AutonomousConfig,
    ConversationWithMonologue
)
from engines.inner_monologue import (
    InnerMonologueParser,
    get_inner_monologue_system_prompt_addition
)

from integrations.llm_integration import get_llm_response, DEFAULT_SYSTEM_PROMPT


async def update_all(state, engines, user_input, response=None):
    """Run all subsystem updates concurrently."""
    tasks = []
    for eng in engines:
        params = eng.update.__code__.co_varnames[:eng.update.__code__.co_argcount]
        if "user_input" in params and "response" in params:
            tasks.append(asyncio.to_thread(eng.update, state, user_input, response))
        elif "user_input" in params:
            tasks.append(asyncio.to_thread(eng.update, state, user_input))
        else:
            tasks.append(asyncio.to_thread(eng.update, state))
    await asyncio.gather(*tasks)


async def main():
    """Main conversation loop with autonomous processing."""

    print("=" * 60)
    print("Kay Zero - Autonomous Processing Enabled")
    print("=" * 60)
    print("\nCommands:")
    print("  /auto     - Start autonomous processing session")
    print("  /godmode  - Toggle inner monologue visibility")
    print("  /lastthought - Show last autonomous session summary")
    print("  quit/exit - Exit (offers autonomous session first)")
    print("=" * 60 + "\n")

    # Initialize core systems
    proto = ProtocolEngine()
    state = AgentState()
    momentum = MomentumEngine()
    motif = MotifEngine()
    meta_awareness = MetaAwarenessEngine()

    # Initialize engines
    emotion = EmotionEngine(proto, momentum_engine=momentum)
    emotion_extractor = EmotionExtractor()
    memory = MemoryEngine(state.memory, motif_engine=motif, momentum_engine=momentum, emotion_engine=emotion)
    social = SocialEngine(emotion_engine=emotion)
    body = EmbodimentEngine(emotion_engine=emotion)
    state.memory = memory

    temporal = TemporalEngine()
    reflection = ReflectionEngine()
    summarizer = Summarizer()
    context_manager = ContextManager(memory, summarizer, momentum_engine=momentum, meta_awareness_engine=meta_awareness)

    # Initialize autonomous processing
    autonomous_config = AutonomousConfig(
        enabled=True,
        auto_trigger_at_exit=True,
        show_inner_monologue=False,  # Start with god mode off
        run_ultramap_after=True
    )

    autonomous = AutonomousIntegration(
        get_llm_response=get_llm_response,
        memory_engine=memory,
        emotion_engine=emotion,
        config=autonomous_config
    )

    # Inner monologue parser for conversation mode
    monologue_parser = InnerMonologueParser()

    print("[STARTUP] Kay Zero with autonomous processing ready.")
    print("[STARTUP] God mode:", "ON" if autonomous_config.show_inner_monologue else "OFF")

    # Check for continuity from last autonomous session
    continuity = autonomous.get_continuity_context()
    if continuity:
        print("\n[CONTINUITY] Found previous autonomous session:")
        print(continuity[:200] + "..." if len(continuity) > 200 else continuity)
        print()

    affect_level = 3.5
    turn_count = 0
    recent_responses = []
    session_id = str(int(asyncio.get_event_loop().time()))

    while True:
        user_input = input("You: ").strip()

        # --- Command handling ---

        # Exit commands
        if user_input.lower() in ("quit", "exit"):
            print("\n[EXIT] Conversation ending...")

            if autonomous_config.auto_trigger_at_exit:
                print("\n[AUTONOMOUS] Would you like Kay to have autonomous processing time?")
                print("This lets Kay explore thoughts and consolidate memories independently.")
                choice = input("Start autonomous session? (y/n): ").strip().lower()

                if choice == 'y':
                    print("\n[AUTONOMOUS] Starting session...")
                    await _run_autonomous_session(autonomous, state)

            print("\nGoodbye!")
            break

        # Affect tuning
        if user_input.lower().startswith("/affect "):
            try:
                affect_level = float(user_input.split(" ", 1)[1])
                print(f"(Affect set to {affect_level:.1f} / 5)")
            except Exception:
                print("(Invalid affect value)")
            continue

        # God mode toggle
        if user_input.lower() == "/godmode":
            new_state = autonomous.toggle_god_mode()
            print(f"[GOD MODE] Inner monologue visibility: {'ON' if new_state else 'OFF'}")
            continue

        # Manual autonomous session
        if user_input.lower() == "/auto":
            print("\n[AUTONOMOUS] Starting manual session...")
            await _run_autonomous_session(autonomous, state)
            continue

        # Show last autonomous session
        if user_input.lower() == "/lastthought":
            summary = autonomous.get_last_session_summary()
            if summary:
                print("\n" + summary)
            else:
                print("\n[AUTONOMOUS] No previous session found.")
            continue

        # --- Normal conversation processing ---
        turn_count += 1

        # Extract facts and recall memories
        memory.extract_and_store_user_facts(state, user_input)
        memory.recall(state, user_input)

        # Pre-response engine updates
        await update_all(state, [social, temporal, body, motif], user_input)

        # Build context
        context = context_manager.build_context(state, user_input)
        context["turn_count"] = turn_count
        context["recent_responses"] = recent_responses
        context["session_id"] = session_id

        # Add autonomous continuity if available
        auto_continuity = autonomous.get_continuity_context()
        if auto_continuity:
            context["autonomous_continuity"] = auto_continuity

        # Build session context
        session_context = {
            "turn_count": turn_count,
            "session_id": session_id
        }

        # Get response
        reply = get_llm_response(context, affect=affect_level, session_context=session_context)

        # Parse for inner monologue
        parsed = monologue_parser.parse(reply)

        # Display based on god mode
        if autonomous.config.show_inner_monologue:
            display = monologue_parser.get_display_response(parsed, show_inner=True)
        else:
            display = parsed.spoken_response if parsed.spoken_response else reply

        # Apply embodiment
        display = body.embody_text(display, state)
        print(f"Kay: {display}\n")

        # Use spoken response for further processing
        spoken = parsed.spoken_response if parsed.spoken_response else reply

        # Extract emotions from response
        extracted_emotions = emotion_extractor.extract_emotions(spoken)
        emotion_extractor.store_emotional_state(extracted_emotions, state.emotional_cocktail)

        # Post-turn updates
        social.update(state, user_input, spoken)
        reflection.reflect(state, user_input, spoken)
        memory.encode(state, user_input, spoken, list(state.emotional_cocktail.keys()))
        context_manager.update_turns(user_input, spoken)

        # Update meta systems
        meta_awareness.update(state, spoken, memory_engine=memory)
        momentum.update(state, user_input, spoken)

        # Track for anti-repetition
        recent_responses.append(spoken)
        if len(recent_responses) > 3:
            recent_responses.pop(0)

        # Autosave state
        try:
            os.makedirs("memory", exist_ok=True)
            snapshot_data = {
                "emotions": state.emotional_cocktail,
                "social_needs": state.social,
                "momentum": state.momentum,
                "meta_awareness": state.meta_awareness,
                "turn_count": turn_count,
            }
            with open("memory/state_snapshot.json", "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=2)
        except Exception as e:
            print(f"(Warning: could not save snapshot: {e})")


async def _run_autonomous_session(autonomous: AutonomousIntegration, state: AgentState):
    """Run an autonomous processing session with display."""

    def on_thought(thought: dict):
        """Display each thought as it occurs."""
        print("\n" + "-" * 40)
        if thought.get("inner_monologue"):
            print(f"💭 {thought['inner_monologue'][:300]}...")
        if thought.get("feeling"):
            print(f"🫀 {thought['feeling']}")
        if thought.get("insight"):
            print(f"💡 Insight: {thought['insight']}")
        if thought.get("continuation"):
            cont = thought["continuation"]
            if cont.lower() in ["complete", "done", "finished"]:
                print(f"✓ Natural completion")
            else:
                print(f"→ {cont[:100]}...")

    try:
        session = await autonomous.run_autonomous_session(
            agent_state=state,
            on_thought=on_thought
        )

        print("\n" + "=" * 40)
        print("AUTONOMOUS SESSION COMPLETE")
        print("=" * 40)

        if session.goal:
            print(f"\nGoal: {session.goal.description}")
            print(f"Iterations: {session.iterations_used}")
            print(f"Completion: {session.goal.completion_type or 'unknown'}")

            if session.goal.insights:
                print(f"\nInsights stored: {len(session.goal.insights)}")
                for i, insight in enumerate(session.goal.insights[:3], 1):
                    print(f"  {i}. {insight[:100]}...")

        if session.convergence_detected:
            print("\n[Natural convergence reached]")
        elif session.energy_depleted:
            print("\n[Session paused - energy limit reached]")

        print()

    except Exception as e:
        print(f"\n[AUTONOMOUS] Session error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
