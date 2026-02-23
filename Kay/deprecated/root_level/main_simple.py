"""
Simplified main loop - CORE FUNCTIONALITY ONLY.

No emotions, no social modeling, no momentum, no meta-awareness.
Just: memory storage, memory retrieval, conversation turns, LLM response.

Test this first. Add complexity ONLY if this works perfectly.
"""
import os
from engines.memory_engine_simple import SimpleMemoryEngine
from integrations.llm_integration_simple import get_llm_response_simple


def main():
    memory = SimpleMemoryEngine()
    recent_turns = []  # Keep last 3 turns
    max_turns = 3

    print("KayZero SIMPLIFIED - Core functionality only")
    print("Type 'quit' to exit\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        # Retrieve relevant memories
        recalled_memories = memory.retrieve(user_input, limit=5)

        # Build context
        context = {
            "user_input": user_input,
            "recent_context": recent_turns[-max_turns:],
            "recalled_memories": recalled_memories
        }

        # Get response
        reply = get_llm_response_simple(context)
        print(f"Kay: {reply}\n")

        # Store memory
        memory.store(user_input, reply)

        # Update recent turns
        recent_turns.append({"user": user_input, "kay": reply})
        if len(recent_turns) > max_turns:
            recent_turns.pop(0)


if __name__ == "__main__":
    main()
