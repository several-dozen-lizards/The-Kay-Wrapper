"""
LLM Latency Profiler for KayZero
Identifies bottlenecks in LLM response generation.

Run with: python profile_llm_latency.py
"""

import time
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integrations.llm_integration import (
    client, MODEL,
    build_cached_core_identity,
    build_cached_system_instructions,
    build_voice_mode_context,
    VOICE_MODE_SYSTEM_PROMPT,
    DEFAULT_SYSTEM_PROMPT,
    get_cached_identity,
    get_cached_instructions,
)


def profile_section(name: str):
    """Context manager for timing sections."""
    class Timer:
        def __init__(self, name):
            self.name = name
            self.start = None
            self.elapsed = None

        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, *args):
            self.elapsed = time.time() - self.start
            print(f"  [{self.name}] {self.elapsed*1000:.1f}ms")

    return Timer(name)


def count_tokens_approx(text: str) -> int:
    """Approximate token count (1 token ~= 4 chars for English)."""
    return len(text) // 4


def profile_prompt_sizes():
    """Analyze prompt/context sizes to understand token costs."""
    print("\n" + "="*60)
    print("PROMPT SIZE ANALYSIS")
    print("="*60)

    # Cached content
    cached_instructions = build_cached_system_instructions()
    cached_identity = build_cached_core_identity()

    print(f"\n1. CACHED CONTENT (stays hot for 5 min):")
    print(f"   - System Instructions: {len(cached_instructions):,} chars (~{count_tokens_approx(cached_instructions):,} tokens)")
    print(f"   - Core Identity: {len(cached_identity):,} chars (~{count_tokens_approx(cached_identity):,} tokens)")
    print(f"   - TOTAL CACHED: {len(cached_instructions) + len(cached_identity):,} chars (~{count_tokens_approx(cached_instructions + cached_identity):,} tokens)")

    # Default system prompt (legacy)
    print(f"\n2. DEFAULT SYSTEM PROMPT (legacy mode):")
    print(f"   - Length: {len(DEFAULT_SYSTEM_PROMPT):,} chars (~{count_tokens_approx(DEFAULT_SYSTEM_PROMPT):,} tokens)")

    # Voice mode system prompt
    print(f"\n3. VOICE MODE SYSTEM PROMPT:")
    print(f"   - Length: {len(VOICE_MODE_SYSTEM_PROMPT):,} chars (~{count_tokens_approx(VOICE_MODE_SYSTEM_PROMPT):,} tokens)")

    # Simulate dynamic context for a typical turn
    mock_context = {
        "user_input": "What are you thinking about?",
        "recalled_memories": [
            {"fact": "Re has green eyes", "perspective": "user", "type": "extracted_fact"},
            {"fact": "Kay likes coffee", "perspective": "kay", "type": "extracted_fact"},
        ] * 20,  # 40 memories (typical retrieval)
        "emotional_state": {"cocktail": {"curiosity": {"intensity": 0.7}}},
        "recent_context": [
            {"speaker": "Re", "message": "Hey Kay, how are you feeling today?"},
            {"speaker": "Kay", "message": "I'm doing alright. Got a lot on my mind though."},
        ] * 5,  # 10 turns of conversation history
        "time_context": {"current_time": "14:30", "time_of_day": "afternoon"},
    }

    # Build voice mode context
    voice_context = build_voice_mode_context(mock_context, affect_level=3.5)
    print(f"\n4. VOICE MODE CONTEXT (lightweight):")
    print(f"   - Length: {len(voice_context):,} chars (~{count_tokens_approx(voice_context):,} tokens)")

    # Estimate full text mode context
    # This is approximate since we're not importing all the context builders
    estimated_full_context = 15000  # chars - typical with memories + conversation history
    print(f"\n5. ESTIMATED FULL TEXT MODE CONTEXT:")
    print(f"   - Estimated: ~{estimated_full_context:,} chars (~{count_tokens_approx(str('x'*estimated_full_context)):,} tokens)")

    print(f"\n6. TOTAL ESTIMATED INPUT (CACHED mode):")
    total_cached = len(cached_instructions) + len(cached_identity) + estimated_full_context
    print(f"   - Total: ~{total_cached:,} chars (~{count_tokens_approx(str('x'*total_cached)):,} tokens)")

    print(f"\n7. TOTAL ESTIMATED INPUT (VOICE mode):")
    total_voice = len(VOICE_MODE_SYSTEM_PROMPT) + len(voice_context)
    print(f"   - Total: ~{total_voice:,} chars (~{count_tokens_approx(str('x'*total_voice)):,} tokens)")


def profile_api_latency():
    """Profile actual API call latency with different prompt sizes."""
    print("\n" + "="*60)
    print("API LATENCY PROFILING")
    print("="*60)

    if not client or not MODEL:
        print("ERROR: Anthropic client not initialized")
        return

    print(f"\nModel: {MODEL}")

    # Test 1: Minimal prompt (baseline)
    print("\n--- Test 1: Minimal Prompt (baseline) ---")
    minimal_prompt = "Say 'hello' and nothing else."

    with profile_section("API call"):
        start = time.time()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=50,
            temperature=0.5,
            system="Respond briefly.",
            messages=[{"role": "user", "content": minimal_prompt}],
        )
        total_time = time.time() - start

    print(f"  Response: '{resp.content[0].text[:100]}'")
    print(f"  Input tokens: {resp.usage.input_tokens}")
    print(f"  Output tokens: {resp.usage.output_tokens}")
    print(f"  TOTAL TIME: {total_time*1000:.0f}ms")
    print(f"  TIME PER OUTPUT TOKEN: {(total_time*1000)/max(1, resp.usage.output_tokens):.1f}ms")

    # Test 2: Voice mode prompt (lightweight)
    print("\n--- Test 2: Voice Mode Prompt (lightweight) ---")
    mock_context = {
        "user_input": "What are you thinking about?",
        "recalled_memories": [{"fact": f"Fact {i}", "perspective": "user"} for i in range(10)],
        "emotional_state": {"cocktail": {"curiosity": {"intensity": 0.7}}},
        "recent_context": [{"speaker": "Re", "message": "Hi"}, {"speaker": "Kay", "message": "Hey"}],
        "time_context": {"current_time": "14:30", "time_of_day": "afternoon"},
    }
    voice_prompt = build_voice_mode_context(mock_context)

    with profile_section("API call"):
        start = time.time()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=400,
            temperature=0.85,
            system=VOICE_MODE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": voice_prompt}],
        )
        total_time = time.time() - start

    print(f"  Response: '{resp.content[0].text[:100]}...'")
    print(f"  Input tokens: {resp.usage.input_tokens}")
    print(f"  Output tokens: {resp.usage.output_tokens}")
    print(f"  TOTAL TIME: {total_time*1000:.0f}ms")
    print(f"  TIME PER OUTPUT TOKEN: {(total_time*1000)/max(1, resp.usage.output_tokens):.1f}ms")

    # Test 3: Cached mode prompt (with cache_control blocks)
    print("\n--- Test 3: Cached Mode Prompt (first call - cache creation) ---")
    cached_instructions = get_cached_instructions()
    cached_identity = get_cached_identity()

    content_blocks = [
        {"type": "text", "text": cached_instructions, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": cached_identity, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "User says: 'Hello, how are you?'\n\nRespond naturally:"},
    ]

    with profile_section("API call (cache creation)"):
        start = time.time()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=400,
            temperature=0.9,
            system="",
            messages=[{"role": "user", "content": content_blocks}],
        )
        total_time = time.time() - start

    print(f"  Response: '{resp.content[0].text[:100]}...'")
    print(f"  Input tokens: {resp.usage.input_tokens}")
    print(f"  Output tokens: {resp.usage.output_tokens}")
    cache_created = getattr(resp.usage, 'cache_creation_input_tokens', 0)
    cache_hit = getattr(resp.usage, 'cache_read_input_tokens', 0)
    print(f"  Cache created: {cache_created} tokens")
    print(f"  Cache hit: {cache_hit} tokens")
    print(f"  TOTAL TIME: {total_time*1000:.0f}ms")
    print(f"  TIME PER OUTPUT TOKEN: {(total_time*1000)/max(1, resp.usage.output_tokens):.1f}ms")

    # Test 4: Second cached call (should hit cache)
    print("\n--- Test 4: Cached Mode Prompt (second call - cache hit) ---")
    content_blocks_2 = [
        {"type": "text", "text": cached_instructions, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": cached_identity, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "User says: 'Tell me about yourself'\n\nRespond naturally:"},
    ]

    with profile_section("API call (cache hit)"):
        start = time.time()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=400,
            temperature=0.9,
            system="",
            messages=[{"role": "user", "content": content_blocks_2}],
        )
        total_time = time.time() - start

    print(f"  Response: '{resp.content[0].text[:100]}...'")
    print(f"  Input tokens: {resp.usage.input_tokens}")
    print(f"  Output tokens: {resp.usage.output_tokens}")
    cache_created = getattr(resp.usage, 'cache_creation_input_tokens', 0)
    cache_hit = getattr(resp.usage, 'cache_read_input_tokens', 0)
    print(f"  Cache created: {cache_created} tokens")
    print(f"  Cache hit: {cache_hit} tokens")
    print(f"  TOTAL TIME: {total_time*1000:.0f}ms")
    print(f"  TIME PER OUTPUT TOKEN: {(total_time*1000)/max(1, resp.usage.output_tokens):.1f}ms")

    # Test 5: Large output test
    print("\n--- Test 5: Large Output Test (max_tokens=2000) ---")

    with profile_section("API call (long response)"):
        start = time.time()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            temperature=0.9,
            system="You are Kay. Give a detailed, multi-paragraph response.",
            messages=[{"role": "user", "content": "Tell me everything about yourself and your thoughts today."}],
        )
        total_time = time.time() - start

    print(f"  Response length: {len(resp.content[0].text)} chars")
    print(f"  Input tokens: {resp.usage.input_tokens}")
    print(f"  Output tokens: {resp.usage.output_tokens}")
    print(f"  TOTAL TIME: {total_time*1000:.0f}ms")
    print(f"  TIME PER OUTPUT TOKEN: {(total_time*1000)/max(1, resp.usage.output_tokens):.1f}ms")


def profile_streaming():
    """Profile streaming response time-to-first-token."""
    print("\n" + "="*60)
    print("STREAMING LATENCY PROFILING (Time-to-First-Token)")
    print("="*60)

    if not client or not MODEL:
        print("ERROR: Anthropic client not initialized")
        return

    print(f"\nModel: {MODEL}")

    # Test streaming with voice mode
    print("\n--- Streaming Test: Voice Mode ---")

    start = time.time()
    first_chunk_time = None
    total_chunks = 0
    total_chars = 0

    with client.messages.stream(
        model=MODEL,
        max_tokens=400,
        temperature=0.85,
        system=VOICE_MODE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": "Hello, how are you today?"}],
    ) as stream:
        for text in stream.text_stream:
            if first_chunk_time is None:
                first_chunk_time = time.time() - start
            total_chunks += 1
            total_chars += len(text)

    total_time = time.time() - start

    print(f"  Time to First Token (TTFT): {first_chunk_time*1000:.0f}ms")
    print(f"  Total Time: {total_time*1000:.0f}ms")
    print(f"  Total Chunks: {total_chunks}")
    print(f"  Total Chars: {total_chars}")
    print(f"  Chars/second after TTFT: {total_chars / (total_time - first_chunk_time):.0f}")


def analyze_bottlenecks():
    """Analyze where time is being spent."""
    print("\n" + "="*60)
    print("BOTTLENECK ANALYSIS")
    print("="*60)

    print("""
ANALYSIS SUMMARY:

1. LLM GENERATION TIME
   - Haiku is fast but output tokens still take ~20-40ms each
   - A 200-token response takes 4-8 seconds just for generation
   - max_tokens=8192 in full mode allows very long responses

   RECOMMENDATIONS:
   - For voice mode: Keep max_tokens=400 (already set)
   - For text mode: Consider max_tokens=1500 for conversational turns
   - Use streaming to reduce perceived latency

2. PROMPT SIZE
   - Cached content: ~6000 tokens (instructions + identity)
   - Dynamic context: ~4000-15000 tokens (memories + conversation)
   - TOTAL: 10000-21000 input tokens per call

   RECOMMENDATIONS:
   - Voice mode already uses lightweight context (~1000 tokens)
   - Consider aggressive memory pruning for conversational mode
   - Limit recent_context to 5 turns instead of full session

3. CACHE UTILIZATION
   - First call creates cache (slower)
   - Subsequent calls hit cache (90% cost savings)
   - Cache expires after 5 minutes of inactivity

   RECOMMENDATIONS:
   - Pre-warm cache when voice mode starts (already implemented)
   - Keep sessions active to maintain cache
   - Consider reducing cache block size if <1024 tokens

4. NETWORK LATENCY
   - ~50-100ms round-trip to Anthropic API
   - Unavoidable but small compared to generation time

   RECOMMENDATIONS:
   - Use streaming to overlap network with generation

5. OUTPUT LENGTH
   - Voice mode target: 2-4 sentences (~100-200 tokens)
   - Text mode target: 3-5+ sentences (~200-500 tokens)
   - Long responses (500+ tokens) will always be slow

   RECOMMENDATIONS:
   - Voice mode: max_tokens=200 for faster completion
   - Add "thinking" indicator during generation
   - Consider sentence-by-sentence TTS with streaming
""")


def main():
    print("="*60)
    print("KayZero LLM Latency Profiler")
    print("="*60)

    # Profile prompt sizes
    profile_prompt_sizes()

    # Profile API latency
    profile_api_latency()

    # Profile streaming
    profile_streaming()

    # Analyze bottlenecks
    analyze_bottlenecks()

    print("\n" + "="*60)
    print("PROFILING COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
