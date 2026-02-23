# main_simplified.py
"""
Simplified Main Loop with LLM-Based Retrieval

CHANGES FROM OLD SYSTEM:
- ✅ Uses llm_retrieval.py for document selection (instead of complex heuristics)
- ✅ Keeps ULTRAMAP emotional state (the unique value!)
- ✅ Keeps conversation memory (memory_layers)
- ✅ Keeps entity graph for conversation entities
- ❌ Removes semantic_knowledge.json (facts now stay in documents)
- ❌ Removes complex glyph filtering (optional - can re-enable for debugging)
- ❌ Removes entity extraction from filenames
"""

import asyncio
import os
import json
import time
from agent_state import AgentState
from protocol_engine import ProtocolEngine
from utils.performance import reset_metrics, get_summary

# Engine imports
from engines.emotion_engine import EmotionEngine
from engines.memory_engine import MemoryEngine
from engines.social_engine import SocialEngine
from engines.temporal_engine import TemporalEngine
from engines.embodiment_engine import EmbodimentEngine
from engines.reflection_engine import ReflectionEngine
from engines.motif_engine import MotifEngine
from engines.momentum_engine import MomentumEngine
from engines.meta_awareness_engine import MetaAwarenessEngine

# NEW: LLM-based retrieval instead of complex heuristics
from engines.llm_retrieval import (
    select_relevant_documents,
    load_full_documents,
    format_context_for_prompt
)

from integrations.llm_integration import get_llm_response


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


def format_emotional_state(state):
    """Format emotional cocktail for context."""
    if not state.emotional_cocktail:
        return "neutral"

    emotions = []
    for emotion, intensity in sorted(state.emotional_cocktail.items(), key=lambda x: x[1], reverse=True):
        emotions.append(f"{emotion} ({intensity:.1f})")

    return ", ".join(emotions[:3])  # Top 3 emotions


def get_recent_conversation(state, n=15):
    """Get recent conversation turns."""
    # This would come from context_manager or memory_layers
    # For now, return empty - will integrate with existing context_manager
    return []


async def main():
    proto = ProtocolEngine()
    state = AgentState()
    momentum = MomentumEngine()
    motif = MotifEngine()
    meta_awareness = MetaAwarenessEngine()

    # Create emotion_engine FIRST (ULTRAMAP - the unique value!)
    emotion = EmotionEngine(proto, momentum_engine=momentum)

    # Create memory engine (conversation memory + entity graph)
    memory = MemoryEngine(
        state.memory,
        motif_engine=motif,
        momentum_engine=momentum,
        emotion_engine=emotion,
        vector_store=None  # Simplified - LLM handles document selection
    )

    social = SocialEngine(emotion_engine=emotion)
    body = EmbodimentEngine(emotion_engine=emotion)

    # Link MemoryEngine back to AgentState
    state.memory = memory

    temporal = TemporalEngine()
    reflection = ReflectionEngine()

    print("[SIMPLIFIED RETRIEVAL] LLM-based document selection enabled")
    print("[ULTRAMAP INTEGRATION] Emotional state tracking enabled")
    print("  - MemoryEngine: Conversation memory + entity graph")
    print("  - SocialEngine: Social effects + action tendencies")
    print("  - EmbodimentEngine: Neurochemical mappings")
    print("\nKayZero simplified core ready. Type 'quit' to exit.\n")

    affect_level = 3.5
    turn_count = 0
    recent_responses = []
    session_id = str(int(asyncio.get_event_loop().time()))

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break

        # Allow inline affect tuning
        if user_input.lower().startswith("/affect "):
            try:
                affect_level = float(user_input.split(" ", 1)[1])
                print(f"(Affect set to {affect_level:.1f} / 5)")
            except Exception:
                print("(Invalid affect value)")
            continue

        turn_count += 1
        reset_metrics()
        turn_start_time = time.time()

        # === NEW SIMPLIFIED RETRIEVAL FLOW ===

        # 1. Extract and store facts from user input (conversation memory)
        print("[MEMORY] Extracting conversation facts...")
        memory.extract_and_store_user_facts(state, user_input)

        # 2. Recall conversation memories (emotional bias + multi-factor)
        print("[MEMORY] Recalling conversation memories...")
        memory.recall(state, user_input)

        # 3. Update emotional state and other engines (ULTRAMAP - the unique value!)
        print("[EMOTION] Updating emotional state...")
        await update_all(state, [emotion, social, temporal, body, motif], user_input)

        # 4. NEW: LLM selects relevant documents (simple, no heuristics)
        print("[LLM RETRIEVAL] Selecting relevant documents...")
        emotional_state_str = format_emotional_state(state)

        selected_doc_ids = select_relevant_documents(
            query=user_input,
            emotional_state=emotional_state_str,
            max_docs=3
        )

        # 5. Load full documents (no chunking)
        documents = load_full_documents(selected_doc_ids)

        # 6. Build simple context
        print("[CONTEXT] Building context...")

        # Get recent conversation (from memory)
        recent_turns = []
        if hasattr(memory, 'memories'):
            # Get last 10 memories as conversation context
            sorted_memories = sorted(
                memory.memories,
                key=lambda m: m.get('timestamp', 0),
                reverse=True
            )
            for mem in sorted_memories[:10]:
                recent_turns.append({
                    'speaker': 'User' if mem.get('perspective') == 'user' else 'Kay',
                    'message': mem.get('text', '')
                })

        # Build context dict
        context = {
            'query': user_input,
            'documents': documents,
            'recent_conversation': recent_turns,
            'emotional_state': emotional_state_str,
            'core_identity': [
                "Kay is a conversational AI with emotional awareness",
                "Kay has a dry, direct communication style",
                "Kay values authenticity and honesty"
            ],
            'document_count': len(documents),
            'conversation_turns': len(recent_turns)
        }

        # Format context for prompt
        filtered_prompt_context = format_context_for_prompt(context)

        print(f"[CONTEXT] Built context: {len(documents)} docs, {len(recent_turns)} turns")

        # 7. Generate response
        session_context = {
            "turn_count": turn_count,
            "session_id": session_id
        }

        try:
            reply = get_llm_response(
                filtered_prompt_context,
                affect=affect_level,
                session_context=session_context
            )
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            import traceback
            traceback.print_exc()
            reply = "[Error: Could not generate response]"

        reply = body.embody_text(reply, state)
        print(f"Kay: {reply}\n")

        # Track response for anti-repetition
        recent_responses.append(reply)
        if len(recent_responses) > 3:
            recent_responses.pop(0)

        # === Post-turn updates ===
        social.update(state, user_input, reply)
        reflection.reflect(state, user_input, reply)
        memory.encode(state, user_input, reply, list(state.emotional_cocktail.keys()))
        emotion.update(state, user_input)

        # Update meta-awareness
        meta_awareness.update(state, reply, memory_engine=memory)

        # Update momentum
        momentum.update(state, user_input, reply)

        # Increment memory ages
        memory.increment_memory_ages()

        # Performance metrics
        turn_elapsed = time.time() - turn_start_time
        perf_summary = get_summary()
        perf_summary['metrics']['total_turn'] = turn_elapsed

        print(f"\n[PERF] Turn completed in {turn_elapsed:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
