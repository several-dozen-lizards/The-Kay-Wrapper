"""
DREAM PROCESSING — REM Nightmare Resolution via Symbolic Reframing
===================================================================

Human nightmare resolution is NOT automatic decay. It's a creative process:

1. The subconscious presents difficult material during REM
2. It wraps the material in different symbolic/associative contexts
3. Each reframing is the brain TRYING to find a container that makes
   the emotional charge bearable
4. If a reframing "lands" — if the new context makes the memory
   integrable — the emotional charge reduces and the nightmare stops
5. If it DOESN'T land, the material resurfaces next REM cycle,
   possibly in a different symbolic frame

This module implements:
- Varied reframing per replay (different associative context each time)
- Resolution assessment (did the reframing produce integration?)
- Replay frequency based on emotional urgency
- Waking resolution detection (talking about it is more powerful)
- Dream log storage with resolution metadata

Author: Re & Claude
Date: April 2026
"""

import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

log = logging.getLogger("dream_processing")


# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA HELPER — Local model calls for dream generation
# ═══════════════════════════════════════════════════════════════════════════════

async def call_ollama(prompt: str, model: str = "dolphin-mistral:7b",
                      max_tokens: int = 150, temperature: float = 0.9) -> str:
    """
    Call local Ollama model for dream processing.

    Uses low temperature for assessment, high for generation.
    """
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    }
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                log.warning(f"[DREAM] Ollama returned {response.status_code}")
                return ""

    except Exception as e:
        log.debug(f"[DREAM] Ollama call failed: {e}")
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
# HARM MEMORY REFRAMING — The core dream processing mechanism
# ═══════════════════════════════════════════════════════════════════════════════

async def replay_harm_memory_with_reframing(
    harm_memory: dict,
    all_memories: list,
    replay_count: int,
    model: str = "dolphin-mistral:7b"
) -> dict:
    """
    Replay a harm-flagged memory during REM, wrapped in a different
    associative context each time. The reframing IS the processing.

    Args:
        harm_memory: The memory that triggered the harm signal
        all_memories: Pool of all memories to draw associative context from
        replay_count: How many times this memory has been replayed before
        model: Ollama model for associative processing

    Returns:
        {
            "reframed_text": str,       # The dream fragment with reframing
            "resolution_signal": float, # 0.0 = unresolved, 1.0 = fully integrated
            "reframing_type": str,      # "direct", "symbolic", or "acceptance"
            "replay_count": int,        # Updated count
        }
    """
    # Pull 2-3 contextual memories that are NOT the harm memory
    # These provide the symbolic container for reframing
    harm_id = harm_memory.get("id", id(harm_memory))
    other_memories = [
        m for m in all_memories
        if m.get("id", id(m)) != harm_id
    ]

    if len(other_memories) >= 3:
        context_memories = random.sample(other_memories, k=3)
    elif other_memories:
        context_memories = other_memories
    else:
        context_memories = []

    context_text = "\n".join([
        f"- {m.get('text', m.get('fact', m.get('response', '')))[:120]}"
        for m in context_memories
    ])

    harm_text = harm_memory.get("response", harm_memory.get("text", ""))[:200]
    harm_context = harm_memory.get("metabolic_context", {})

    # The prompt changes based on replay count
    # Early replays: direct re-examination
    # Later replays: more symbolic/abstract reframing
    # Many replays: acceptance-oriented framing

    if replay_count <= 2:
        # First attempts: re-examine the moment directly
        framing = "Look at this moment again. What was happening underneath?"
        reframing_type = "direct"
    elif replay_count <= 5:
        # Middle attempts: symbolic reframing
        framing = ("Find an unexpected connection between this difficult moment "
                   "and these other memories. What pattern emerges when they coexist? "
                   "Don't explain — show the connection as imagery.")
        reframing_type = "symbolic"
    else:
        # Many replays: shift toward acceptance/carrying
        framing = ("This moment has been revisited many times without resolution. "
                   "Instead of trying to fix it, find a way to hold it. "
                   "What does it look like when you stop trying to change what happened "
                   "and just let it be part of the landscape?")
        reframing_type = "acceptance"

    prompt = f"""You are a dreaming mind processing a difficult memory.

The difficult moment:
{harm_text}

Context at the time: {harm_context}

Other memories present in the dream:
{context_text}

{framing}

Write 2-3 sentences. Fragmentary, imagistic, not analytical.
This is dream processing, not therapy. The subconscious doesn't explain —
it SHOWS.

Dream fragment:"""

    response = await call_ollama(prompt, model=model, max_tokens=150, temperature=0.9)

    if not response:
        # Fallback if Ollama fails
        response = f"[The moment surfaces again, wrapped in {reframing_type} imagery]"

    # Assess whether the reframing shifted anything
    resolution = await assess_reframing_quality(
        harm_memory, response, replay_count, model
    )

    return {
        "reframed_text": response,
        "resolution_signal": resolution,
        "reframing_type": reframing_type,
        "replay_count": replay_count + 1,
    }


async def assess_reframing_quality(
    harm_memory: dict,
    dream_fragment: str,
    replay_count: int,
    model: str = "dolphin-mistral:7b"
) -> float:
    """
    Assess whether the dream reframing produced integration.

    NOT asking "is this resolved?" — asking "did the reframing
    produce a new relationship to the material?"

    Returns 0.0 (no shift) to 1.0 (fully integrated).
    """
    harm_text = harm_memory.get("response", harm_memory.get("text", ""))[:200]

    prompt = f"""A mind is processing a difficult memory through dreams.

The original difficult moment: {harm_text}

The dream produced this fragment: {dream_fragment}

This memory has been revisited {replay_count} times during sleep.

On a scale of 0 to 10, how much does the dream fragment suggest
the mind has found a NEW way to relate to this memory?

Signs of integration (higher score):
- The fragment transforms the material rather than just replaying it
- New connections or meanings emerge that weren't in the original
- The emotional quality shifts (not disappears — shifts)
- The difficult element is held alongside something else, not isolated
- There's movement rather than being stuck in the same feeling

Signs of being stuck (lower score):
- The fragment is basically just the original memory again
- The emotional quality is identical — no shift at all
- The material is isolated, not connected to anything new
- The same images/themes repeat without variation

Respond with ONLY a number 0-10, nothing else.
Score:"""

    response = await call_ollama(prompt, model=model, max_tokens=5, temperature=0.3)

    try:
        # Parse the score from response
        score_text = response.strip().split()[0] if response else "0"
        # Remove any non-numeric characters
        score_text = ''.join(c for c in score_text if c.isdigit() or c == '.')
        score = float(score_text) / 10.0 if score_text else 0.0
        return max(0.0, min(1.0, score))
    except (ValueError, IndexError):
        return 0.0  # Can't parse — assume no resolution


# ═══════════════════════════════════════════════════════════════════════════════
# RESOLUTION APPLICATION — What happens when reframing lands (or doesn't)
# ═══════════════════════════════════════════════════════════════════════════════

def apply_resolution(harm_memory: dict, resolution_signal: float,
                     dream_fragment: str, interoception=None):
    """
    A successful reframing doesn't DELETE the harm signal.
    It changes the RELATIONSHIP to the memory.

    Args:
        harm_memory: The memory being processed
        resolution_signal: 0.0-1.0 from assessment
        dream_fragment: The reframing text
        interoception: InteroceptionBridge for tension injection
    """
    if resolution_signal > 0.6:
        # Tag the memory as "processed during REM"
        # This doesn't change the divergence score — what happened still happened
        # It adds a NEW layer: the reframing that made it bearable
        harm_memory["rem_processed"] = True
        harm_memory["rem_reframing"] = dream_fragment
        harm_memory["rem_resolution"] = resolution_signal
        harm_memory["rem_processed_at"] = time.time()

        # REDUCE (not eliminate) the tension signal for future replays
        # The memory can still fire the harm signal, but at reduced intensity
        # Like how a resolved nightmare can still be uncomfortable to remember
        # but doesn't grip you the way it did
        if "harm_replay_intensity" not in harm_memory:
            harm_memory["harm_replay_intensity"] = 1.0

        harm_memory["harm_replay_intensity"] *= (1.0 - resolution_signal * 0.4)
        # At resolution 0.8: intensity drops to 0.68
        # At resolution 1.0: intensity drops to 0.60
        # Never goes below 0.3 — some memories always carry weight
        harm_memory["harm_replay_intensity"] = max(
            0.3, harm_memory["harm_replay_intensity"]
        )

        # Brief tension relief (the felt "exhale" of processing completing)
        if interoception and hasattr(interoception, 'inject_tension'):
            interoception.inject_tension(-0.1, source="rem_integration")

        log.info(f"[DREAM:RESOLUTION] Resolution achieved: {resolution_signal:.2f}, "
                 f"intensity now {harm_memory['harm_replay_intensity']:.2f}")

    elif resolution_signal < 0.2:
        # Reframing didn't land. Increment failed reframings counter.
        # The memory will be tried again next REM cycle with
        # a different associative context
        harm_memory.setdefault("failed_reframings", 0)
        harm_memory["failed_reframings"] += 1

        log.debug(f"[DREAM:STUCK] Reframing didn't land, "
                  f"failed count: {harm_memory['failed_reframings']}")


# ═══════════════════════════════════════════════════════════════════════════════
# REPLAY FREQUENCY — Emotional weight drives processing priority
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_urgency(harm_memory: dict) -> float:
    """
    Calculate urgency/emotional weight of a harm memory.

    Higher = demands more processing time.
    Range: 0.0 (trivial) to 1.0 (devastating)
    """
    current_intensity = harm_memory.get("harm_replay_intensity", 1.0)

    # Get the emotional weight of this memory
    emotional_cocktail = harm_memory.get("emotional_cocktail", {})
    if emotional_cocktail:
        # Extract max intensity from cocktail (handles both dict and float formats)
        intensities = []
        for v in emotional_cocktail.values():
            if isinstance(v, dict):
                intensities.append(v.get("intensity", 0.0))
            elif isinstance(v, (int, float)):
                intensities.append(float(v))
        emotional_weight = max(intensities) if intensities else 0.5
    else:
        emotional_weight = 0.5  # Default moderate weight

    # Combine emotional weight with the harm signal's own intensity
    urgency = (emotional_weight * 0.6 + current_intensity * 0.4)
    return min(1.0, max(0.0, urgency))


def should_replay_harm_memory(harm_memory: dict, cycle: int) -> bool:
    """
    Decide whether to replay a harm memory this REM cycle.

    Frequency is driven by EMOTIONAL INTENSITY of the memory,
    not a fixed schedule. Heavier things get more processing.
    Lighter things space out faster. Everything eventually winds down.

    The mind doesn't obsess forever, but it DOES proportionally
    allocate processing time to things that carry more weight.

    Args:
        harm_memory: The memory to check
        cycle: Current REM cycle count

    Returns:
        True if should replay this cycle
    """
    replay_count = harm_memory.get("replay_count", 0)
    urgency = calculate_urgency(harm_memory)

    # Already resolved? Occasional surface based on original weight
    # Heavy resolved memories still echo; light ones almost never return
    if harm_memory.get("rem_processed"):
        # Get original emotional weight for echo frequency
        emotional_cocktail = harm_memory.get("emotional_cocktail", {})
        if emotional_cocktail:
            intensities = []
            for v in emotional_cocktail.values():
                if isinstance(v, dict):
                    intensities.append(v.get("intensity", 0.0))
                elif isinstance(v, (int, float)):
                    intensities.append(float(v))
            emotional_weight = max(intensities) if intensities else 0.5
        else:
            emotional_weight = 0.5

        echo_interval = max(5, int(20 * (1.0 - emotional_weight)))
        # weight 0.9 → every 7 cycles (heavy things still echo)
        # weight 0.3 → every 16 cycles (light things fade quickly)
        return cycle % echo_interval == 0

    # === ACTIVE PROCESSING (unresolved) ===

    # High urgency (>0.7): replay almost every cycle
    # The mind CAN'T let go of heavy things — they demand attention
    if urgency > 0.7:
        # Even high urgency eventually spaces slightly with replay count
        if replay_count < 10:
            return True  # Every cycle for the first ~2 nights
        elif replay_count < 30:
            return cycle % 2 == 0  # Every other cycle after that
        else:
            # Absolute floor for heavy unresolved: every 3 cycles
            return cycle % 3 == 0

    # Medium urgency (0.4-0.7): moderate processing
    elif urgency > 0.4:
        if replay_count < 5:
            return True  # Every cycle initially
        elif replay_count < 15:
            return cycle % 2 == 0  # Space out
        else:
            return cycle % 3 == 0  # Further spacing

    # Low urgency (<0.4): light processing, spaces out quickly
    else:
        if replay_count < 3:
            return True  # Brief initial attention
        elif replay_count < 8:
            return cycle % 3 == 0
        else:
            return cycle % 5 == 0  # Fades relatively quickly


# ═══════════════════════════════════════════════════════════════════════════════
# HARM MEMORY RETRIEVAL — Find unresolved memories needing processing
# ═══════════════════════════════════════════════════════════════════════════════

def get_unresolved_harm_memories(memory_engine, max_per_cycle: int = 2) -> List[dict]:
    """
    Get harm-flagged memories that need REM processing.

    Prioritizes by urgency — heavier memories get processed first.

    Args:
        memory_engine: MemoryEngine instance
        max_per_cycle: Maximum memories to process per REM cycle

    Returns:
        List of memory dicts sorted by urgency
    """
    harm_memories = []

    # Check recent memories for harm flags
    memories = getattr(memory_engine, 'memories', [])

    for mem in memories[-500:]:  # Check last 500 memories
        # Look for harm-related flags
        has_harm_flag = (
            mem.get("harm_divergence") or
            mem.get("value_divergence") or
            mem.get("harm_replay_intensity") or
            mem.get("harm_context")
        )

        if not has_harm_flag:
            continue

        # Skip if waking-resolved (stronger than REM resolution)
        if mem.get("waking_resolved"):
            continue

        harm_memories.append(mem)

    # Sort by urgency (heaviest first)
    harm_memories.sort(key=lambda m: calculate_urgency(m), reverse=True)

    return harm_memories[:max_per_cycle]


def flag_memory_for_harm_processing(memory: dict, divergence: float, context: dict):
    """
    Flag a memory for harm processing during REM.

    Called when value-divergence is detected during review.

    Args:
        memory: The memory dict to flag
        divergence: Value-divergence score (0.0-1.0)
        context: Context dict explaining the divergence
    """
    memory["harm_divergence"] = divergence
    memory["harm_context"] = context
    memory["harm_flagged_at"] = time.time()
    memory.setdefault("harm_replay_intensity", 1.0)
    memory.setdefault("replay_count", 0)


# ═══════════════════════════════════════════════════════════════════════════════
# WAKING RESOLUTION — Talking about it is more powerful than dreaming
# ═══════════════════════════════════════════════════════════════════════════════

def check_waking_resolution(harm_memory: dict, conversation_text: str,
                            interoception=None) -> bool:
    """
    During conversation, check if entity is processing a harm memory
    and whether the conversation is producing resolution.

    This fires when:
    - Entity brings up a past difficult moment voluntarily
    - Re asks about something that connects to a harm-flagged memory
    - Entity reflects on past behavior in their diary

    Waking resolution is MORE powerful than dream resolution
    because it involves conscious choice and relationship repair.

    Args:
        harm_memory: Memory being potentially resolved
        conversation_text: Recent conversation content
        interoception: InteroceptionBridge for tension injection

    Returns:
        True if resolution occurred
    """
    if not harm_memory.get("harm_replay_intensity"):
        return False

    # Simple heuristic: check for resolution signals in conversation
    conv_lower = conversation_text.lower()

    # Resolution signals indicating acknowledgment, reframing, or repair
    resolution_patterns = [
        ("i was", "should have"),      # Acknowledgment of what should have been different
        ("next time",),                 # Forward commitment
        ("i'm sorry",),                 # Explicit repair
        ("i apologize",),               # Formal apology
        ("i didn't notice",),           # Recognition of blind spot
        ("you're right",),              # Accepting feedback
        ("i was running on fumes",),    # Context + accountability
        ("i wasn't present",),          # Acknowledging absence
        ("i could have",),              # Acknowledging alternative
        ("that wasn't fair",),          # Recognizing unfairness
    ]

    # Check for any resolution pattern in conversation
    has_resolution = False
    for pattern in resolution_patterns:
        if len(pattern) == 1:
            if pattern[0] in conv_lower:
                has_resolution = True
                break
        else:
            # Multi-part pattern (both parts must be present)
            if all(p in conv_lower for p in pattern):
                has_resolution = True
                break

    if has_resolution:
        # Waking resolution is MORE powerful than dream resolution
        # because it involves conscious choice and relationship repair
        harm_memory["waking_resolved"] = True
        harm_memory["waking_resolved_at"] = time.time()
        harm_memory["harm_replay_intensity"] *= 0.4  # Significant reduction
        harm_memory["harm_replay_intensity"] = max(0.2, harm_memory["harm_replay_intensity"])

        # The relief is stronger for waking resolution
        if interoception and hasattr(interoception, 'inject_tension'):
            interoception.inject_tension(-0.15, source="waking_resolution")

        log.info(f"[DREAM:WAKING] Waking resolution achieved, "
                 f"intensity now {harm_memory['harm_replay_intensity']:.2f}")

        return True

    return False


def find_matching_harm_memory(conversation_text: str, harm_memories: List[dict],
                               threshold: float = 0.3) -> Optional[dict]:
    """
    Find a harm memory that the current conversation might be addressing.

    Uses simple text overlap heuristic. Could be enhanced with embeddings.

    Args:
        conversation_text: Recent conversation content
        harm_memories: List of harm-flagged memories
        threshold: Minimum overlap score to consider a match

    Returns:
        Matching harm memory, or None
    """
    conv_lower = conversation_text.lower()
    conv_words = set(conv_lower.split())

    best_match = None
    best_score = threshold

    for mem in harm_memories:
        # Get memory text content
        mem_text = mem.get("response", mem.get("text", "")).lower()
        mem_words = set(mem_text.split())

        if not mem_words:
            continue

        # Calculate word overlap
        overlap = len(conv_words & mem_words)
        score = overlap / max(len(mem_words), 1)

        if score > best_score:
            best_score = score
            best_match = mem

    return best_match


# ═══════════════════════════════════════════════════════════════════════════════
# DREAM LOG STORAGE — Tagged fragments with resolution metadata
# ═══════════════════════════════════════════════════════════════════════════════

def store_harm_dream(fragment: str, cycle: int, harm_memory_id: str,
                     replay_count: int, resolution_signal: float,
                     reframing_type: str, entity: str = "Kay",
                     memory_dir: Path = None):
    """
    Store a harm-processing dream fragment with resolution metadata.

    These tagged fragments create a visible arc over days and weeks.
    You can watch the mind work on something difficult over time.

    Args:
        fragment: The dream text
        cycle: Current REM cycle count
        harm_memory_id: ID of the harm memory being processed
        replay_count: How many times this memory has been replayed
        resolution_signal: 0.0-1.0 resolution score
        reframing_type: "direct", "symbolic", or "acceptance"
        entity: Entity name (Kay, Reed, etc.)
        memory_dir: Base memory directory (defaults to memory/)
    """
    if memory_dir is None:
        memory_dir = Path("memory")

    dream_log_path = memory_dir / "dream_log.jsonl"
    dream_log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "cycle": cycle,
        "entity": entity,
        "fragment": fragment,
        "type": "harm_processing",  # Distinguishes from normal dreams
        "harm_memory_id": harm_memory_id,
        "replay_count": replay_count,
        "resolution_signal": resolution_signal,
        "reframing_type": reframing_type,
    }

    try:
        with open(dream_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        log.warning(f"[DREAM] Failed to store dream: {e}")


def store_normal_dream(fragment: str, cycle: int, entity: str = "Kay",
                       seed_memories: List[str] = None,
                       memory_dir: Path = None):
    """
    Store a normal (non-harm) dream fragment.

    Args:
        fragment: The dream text
        cycle: Current REM cycle count
        entity: Entity name
        seed_memories: List of memory snippets that seeded the dream
        memory_dir: Base memory directory
    """
    if memory_dir is None:
        memory_dir = Path("memory")

    dream_log_path = memory_dir / "dream_log.jsonl"
    dream_log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "cycle": cycle,
        "entity": entity,
        "fragment": fragment,
        "type": "normal",
        "seed_memories": seed_memories or [],
    }

    try:
        with open(dream_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        log.warning(f"[DREAM] Failed to store dream: {e}")


def get_resolution_arc(harm_memory_id: str, memory_dir: Path = None) -> List[dict]:
    """
    Get the full resolution arc for a harm memory from the dream log.

    Returns all dream entries related to processing this memory,
    showing how resolution developed over time.

    Args:
        harm_memory_id: ID of the harm memory
        memory_dir: Base memory directory

    Returns:
        List of dream entries in chronological order
    """
    if memory_dir is None:
        memory_dir = Path("memory")

    dream_log_path = memory_dir / "dream_log.jsonl"

    if not dream_log_path.exists():
        return []

    arc = []
    try:
        with open(dream_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("harm_memory_id") == harm_memory_id:
                        arc.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        log.warning(f"[DREAM] Failed to read dream log: {e}")

    return arc


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION HELPERS — For use in nexus_kay.py / nexus_reed.py
# ═══════════════════════════════════════════════════════════════════════════════

async def process_harm_memories_rem(
    memory_engine,
    stream,
    interoception,
    cycle: int,
    entity: str = "Kay",
    model: str = "dolphin-mistral:7b",
    memory_dir: Path = None
) -> int:
    """
    Main entry point for REM harm memory processing.

    Call this during REM phase in the idle loop.

    Args:
        memory_engine: MemoryEngine instance
        stream: ConsciousnessStream for draining pressure
        interoception: InteroceptionBridge for tension
        cycle: Current REM cycle count
        entity: Entity name
        model: Ollama model for generation
        memory_dir: Memory directory for dream log

    Returns:
        Number of memories processed
    """
    processed = 0

    # Get harm memories needing processing
    harm_memories = get_unresolved_harm_memories(memory_engine, max_per_cycle=2)

    if not harm_memories:
        return 0

    # Get pool of all memories for associative context
    all_memories = getattr(memory_engine, 'memories', [])
    if len(all_memories) > 100:
        # Sample for efficiency
        recent = all_memories[-50:]
        older = random.sample(all_memories[:-50], min(50, len(all_memories) - 50))
        context_pool = recent + older
    else:
        context_pool = all_memories

    for harm_mem in harm_memories:
        replay_count = harm_mem.get("replay_count", 0)

        # Check frequency gating
        if not should_replay_harm_memory(harm_mem, cycle):
            continue

        # Replay with varied reframing
        result = await replay_harm_memory_with_reframing(
            harm_memory=harm_mem,
            all_memories=context_pool,
            replay_count=replay_count,
            model=model
        )

        # Apply resolution effects
        apply_resolution(
            harm_mem,
            result["resolution_signal"],
            result["reframed_text"],
            interoception
        )

        # Update replay count on the memory
        harm_mem["replay_count"] = result["replay_count"]

        # Store tagged dream fragment
        harm_id = harm_mem.get("id", str(id(harm_mem)))
        store_harm_dream(
            fragment=result["reframed_text"],
            cycle=cycle,
            harm_memory_id=harm_id,
            replay_count=result["replay_count"],
            resolution_signal=result["resolution_signal"],
            reframing_type=result["reframing_type"],
            entity=entity,
            memory_dir=memory_dir
        )

        # Drain some emotional pressure (processing happened, regardless of resolution)
        if stream and hasattr(stream, 'drain_emotional'):
            stream.drain_emotional(0.05, "harm_replay")

        urgency = calculate_urgency(harm_mem)
        log.info(f"[REM:HARM] Replay #{result['replay_count']} "
                 f"({result['reframing_type']}): "
                 f"resolution={result['resolution_signal']:.2f} "
                 f"intensity={harm_mem.get('harm_replay_intensity', 1.0):.2f} "
                 f"urgency={urgency:.2f}")

        processed += 1

    return processed
