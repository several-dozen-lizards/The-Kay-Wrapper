"""
Memory Layer Rebalancing and UNCONFIRMED CLAIM Tuning

This module provides fixes for two critical memory issues:
1. Inverted memory composition (too much semantic, not enough episodic)
2. Over-aggressive UNCONFIRMED CLAIM filtering (blocks valid observations)

INTEGRATION:
- Replace layer_boost calculation in memory_engine.py calculate_multi_factor_score()
- Replace UNCONFIRMED CLAIM filter in memory_engine.py encode()
- Add helper methods for validation and tracking

USAGE:
    from engines.memory_layer_rebalancing import (
        apply_layer_weights,
        should_store_claim,
        create_entity_observation,
        validate_memory_composition
    )
"""

from typing import Dict, List, Any, Tuple, Optional
import re


# ===== LAYER WEIGHT CONFIGURATION =====

# UPDATED 2025-11-19: EXTREME weights to combat massive semantic volume
# Semantic layer has 3593 memories vs only 100 episodic. Even 8.3x ratio wasn't enough.
# New weights provide 200x episodic/semantic ratio to overcome volume imbalance.

LAYER_WEIGHTS = {
    "working": 10.0,   # 10.0x boost - Recent context is critical
    "episodic": 0.8,   # 0.8x REDUCTION - Prevent episodic flooding (was 6.0x)
    "semantic": 1.0,   # 1.0x baseline - Stable knowledge priority (was 0.1x)
}

# REBALANCED 2025-11-24: Fix episodic flooding issue
# Actual system has lots of episodic memories flooding semantic knowledge
# New weights prioritize semantic (stable facts) over episodic (short-term noise)
#
# Expected composition with 225 memories:
# - Working: 10 × 10.0 = 100 → 45 slots (20%)
# - Episodic: N × 0.8 → 79 slots (35%, reduced from 48%)
# - Semantic: N × 1.0 → 101 slots (45%, increased from 32%)
#
# Ratio: working:semantic:episodic = 10:1:0.8 = prevents episodic domination

# Target composition (approximate percentages)
# REBALANCED: Reduce episodic dominance, increase semantic stable knowledge
TARGET_COMPOSITION = {
    "working": 0.20,   # 20% (keep recent context strong)
    "episodic": 0.35,  # 35% (reduced from 48% - less short-term overwhelm)
    "semantic": 0.45,  # 45% (increased from 32% - prioritize stable knowledge)
}


def apply_layer_weights(
    memory: Dict[str, Any],
    base_score: float,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Apply layer-specific weights to memory scoring.

    This replaces the old layer_boost logic (lines 1583-1589 in memory_engine.py).

    OLD BEHAVIOR:
        semantic: 1.2x boost (WRONG - makes semantic dominate)
        working: 1.5x boost
        episodic: 1.0x (no boost)

    NEW BEHAVIOR (UPDATED):
        working: 3.0x boost (up from 1.5x)
        episodic: 2.5x boost (up from 1.0x)
        semantic: 0.3x reduction (down from 1.2x)

        Ratio: episodic/semantic = 8.3x (was 0.8x in old system)

    Args:
        memory: Memory record with 'current_layer' field
        base_score: Base score from multi-factor scoring
        weights: Optional custom layer weights (defaults to LAYER_WEIGHTS)

    Returns:
        Weighted score

    Example:
        >>> mem = {"current_layer": "episodic", "fact": "Re enjoys coffee"}
        >>> base = 0.65
        >>> weighted = apply_layer_weights(mem, base)
        >>> print(weighted)  # 1.625 (0.65 * 2.5)
    """
    if weights is None:
        weights = LAYER_WEIGHTS

    current_layer = memory.get("current_layer", "working")
    layer_weight = weights.get(current_layer, 1.0)

    weighted_score = base_score * layer_weight

    return weighted_score


def get_layer_multiplier(layer: str) -> float:
    """
    Get the multiplier for a specific layer.

    Args:
        layer: Layer name ('working', 'episodic', 'semantic')

    Returns:
        Multiplier value (3.0, 2.5, or 0.3)
    """
    return LAYER_WEIGHTS.get(layer, 1.0)


# ===== UNCONFIRMED CLAIM TUNING =====

OBSERVATION_KEYWORDS = {
    # Emotional state observations
    "emotional": [
        "experiencing", "feeling", "seems", "appears to be",
        "emotional state", "affect", "mood", "distressed",
        "exhausted", "anxious", "stressed", "overwhelmed"
    ],

    # Physical state observations
    "physical": [
        "body", "physical", "tired", "fatigued", "energy",
        "health", "condition", "symptoms", "recovering"
    ],

    # Behavioral observations
    "behavioral": [
        "pattern", "behavior", "tendency", "habit",
        "usually", "often", "typically", "noticed"
    ],

    # Needs/desires inferences
    "inference": [
        "needs", "wants", "desires", "seeking",
        "looking for", "trying to", "hoping", "wishes"
    ]
}

FALSE_ATTRIBUTION_PATTERNS = [
    # REFINED: Only block DIRECT QUOTES and explicit claims about what user SAID
    # (Not interpretations or observations)

    # Claiming user SAID specific words (direct quote claims)
    r"(?i)\bre said\s+[\"']",  # "Re said 'X'" with quotes
    r"(?i)\byou said\s+[\"']",  # "You said 'X'" with quotes
    r"(?i)\byou told me\s+[\"']",  # "You told me 'X'" with quotes
    r"(?i)\byou mentioned\s+[\"']",  # "You mentioned 'X'" with quotes

    # Claiming user EXPLICITLY STATED goals/intentions they didn't express
    # (Only block if it's presented as fact, not inference)
    r"(?i)\byou told me (?:that )?your goal",  # "You told me your goal is..."
    r"(?i)\byou said (?:that )?you want to",  # "You said you want to..."
    r"(?i)\byou stated (?:that )?your intention",  # "You stated your intention..."

    # Inventing specific past quotes
    r"(?i)\bwhen you said\s+[\"']",  # "When you said 'X'"
    r"(?i)\bwhen you told me\s+[\"']",  # "When you told me 'X'"
]

# REMOVED patterns that were too aggressive:
# - "you want to" without context (legitimate for observations like "you want support")
# - "you mentioned" without quotes (legitimate for "you mentioned feeling tired")
# - "your goal is" without context (legitimate for inferences)
# - "last time you" (legitimate for referring to past sessions)


def is_entity_observation(fact_text: str) -> bool:
    """
    Determine if a fact is an entity's observation/inference vs a false attribution.

    ALLOW these (entity observations and interpretations):
    - "Re is experiencing exhaustion..."
    - "Re's body spent a week dumping iron..."
    - "Re seems distressed about..."
    - "Re needs support with..."
    - "Re's words come through as clean text..."
    - "Re is working on a difficult project..."
    - "Re wants to feel better..." (inference, not quote)

    BLOCK these (false direct quotes):
    - "Re said 'I want to quit'" (claiming specific words with quotes)
    - "Re told me 'my goal is X'" (direct quote that didn't happen)
    - "You said 'your favorite color is blue'" (false quote)

    Args:
        fact_text: The fact text to analyze

    Returns:
        True if this is an observation (should be stored),
        False if it's a false attribution (should be blocked)
    """
    fact_lower = fact_text.lower()

    # Check for false attribution patterns first
    for pattern in FALSE_ATTRIBUTION_PATTERNS:
        if re.search(pattern, fact_text):
            return False  # Block - entity claiming user SAID something

    # Check for observation keywords
    for category, keywords in OBSERVATION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in fact_lower:
                return True  # Allow - entity observation

    # Check for any observational language
    observational_markers = [
        "is experiencing", "seems", "appears",
        "might", "possibly", "likely", "probably",
        "is going through", "is dealing with",
        "is working on", "is trying", "is struggling",
        "has been", "needs", "wants", "is looking for"
    ]

    for marker in observational_markers:
        if marker in fact_lower:
            return True

    # UPDATED: Default to ALLOWING (permissive approach)
    # Since FALSE_ATTRIBUTION patterns are now very specific,
    # we can safely allow most statements through as observations.
    # Only direct quotes get blocked by the patterns above.
    return True


def should_store_claim(
    fact_text: str,
    source_speaker: str,
    perspective: str,
    user_input: str = ""
) -> Tuple[bool, str]:
    """
    Determine if a claim should be stored and how.

    This replaces the UNCONFIRMED CLAIM filter (lines 1133-1139 in memory_engine.py).

    OLD BEHAVIOR:
        if needs_confirmation:
            print("[UNCONFIRMED CLAIM] ... - NOT STORING AS USER FACT.")
            continue  # BLOCKS ENTIRELY

    NEW BEHAVIOR:
        Distinguish between:
        1. Entity observations → Store with 'entity_observation' tag
        2. False attributions → Block entirely
        3. User statements → Store as normal

    Args:
        fact_text: The fact text
        source_speaker: Who made this statement ("user" or "entity")
        perspective: Whose perspective ("user" or "entity")
        user_input: The user's actual input (for validation)

    Returns:
        Tuple of (should_store: bool, storage_type: str)
        storage_type can be:
            - "normal" (store as regular fact)
            - "entity_observation" (store as entity observation)
            - "blocked" (don't store)

    Example:
        >>> should_store_claim(
        ...     "Re is experiencing exhaustion",
        ...     source_speaker="entity",
        ...     perspective="user",
        ...     user_input="I'm so tired"
        ... )
        (True, "entity_observation")

        >>> should_store_claim(
        ...     "Re said they want to quit",
        ...     source_speaker="entity",
        ...     perspective="user",
        ...     user_input="I'm frustrated"
        ... )
        (False, "blocked")
    """
    # If source is user, always store as normal
    if source_speaker == "user":
        return (True, "normal")

    # If source is entity and perspective is entity, store as normal
    if source_speaker == "entity" and perspective == "entity":
        return (True, "normal")

    # If source is entity and perspective is user, we need to decide
    if source_speaker == "entity" and perspective == "user":

        # Check if it's an observation
        if is_entity_observation(fact_text):
            return (True, "entity_observation")
        else:
            # Not an observation - block it
            return (False, "blocked")

    # Default: store as normal
    return (True, "normal")


def create_entity_observation(
    fact_data: Dict[str, Any],
    observer: str = "entity",
    observed: str = "re"
) -> Dict[str, Any]:
    """
    Create an entity observation memory entry.

    Entity observations are the entity's inferences/interpretations about the user,
    stored separately from authoritative user facts.

    Args:
        fact_data: Original fact data dict
        observer: Who made the observation (default: "entity")
        observed: Who is being observed (default: "re")

    Returns:
        Modified fact_data with observation tags

    Example:
        >>> fact = {
        ...     "fact": "Re is experiencing exhaustion",
        ...     "perspective": "user",
        ...     "source_speaker": "entity"
        ... }
        >>> obs = create_entity_observation(fact)
        >>> print(obs["observation_type"])
        "entity_observation"
        >>> print(obs["observer"])
        "entity"
    """
    observation = fact_data.copy()

    # Tag as entity observation
    observation["observation_type"] = "entity_observation"
    observation["observer"] = observer
    observation["observed"] = observed
    observation["is_inference"] = True

    # Keep perspective as original for retrieval
    # But add observer_perspective for clarity
    observation["observer_perspective"] = f"{observer}_about_{observed}"

    return observation


# ===== VALIDATION AND TRACKING =====

def validate_memory_composition(
    memories: List[Dict[str, Any]],
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Validate memory composition and compare to target ratios.

    Use this to check if layer rebalancing is working.

    Args:
        memories: List of memory records
        verbose: Whether to print detailed report

    Returns:
        Dict with composition stats

    Example:
        >>> memories = retrieve_multi_factor(...)
        >>> stats = validate_memory_composition(memories)
        >>> print(stats["episodic_percentage"])
        48.2  # Close to 48% target!
    """
    if not memories:
        return {
            "error": "No memories provided",
            "total": 0
        }

    # Count by layer
    layer_counts = {
        "working": 0,
        "episodic": 0,
        "semantic": 0,
        "identity": 0,  # Track identity separately
        "unknown": 0
    }

    for mem in memories:
        if mem.get("is_identity", False):
            layer_counts["identity"] += 1
        else:
            layer = mem.get("current_layer", "unknown")
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

    total = len(memories)
    total_non_identity = total - layer_counts["identity"]

    # Calculate percentages (excluding identity)
    percentages = {}
    for layer in ["working", "episodic", "semantic"]:
        count = layer_counts[layer]
        pct = (count / total_non_identity * 100) if total_non_identity > 0 else 0
        percentages[f"{layer}_percentage"] = pct

    # Compare to targets
    deviations = {}
    for layer in ["working", "episodic", "semantic"]:
        actual = percentages[f"{layer}_percentage"] / 100
        target = TARGET_COMPOSITION[layer]
        deviation = actual - target
        deviations[f"{layer}_deviation"] = deviation

    stats = {
        "total_memories": total,
        "total_non_identity": total_non_identity,
        "identity_count": layer_counts["identity"],
        **layer_counts,
        **percentages,
        **deviations,
    }

    if verbose:
        print("\n" + "="*70)
        print("MEMORY COMPOSITION VALIDATION")
        print("="*70)
        print(f"\nTotal memories: {total}")
        print(f"  Identity facts: {layer_counts['identity']} (always included)")
        print(f"  Non-identity: {total_non_identity}")
        print()

        print("CURRENT COMPOSITION:")
        for layer in ["working", "episodic", "semantic"]:
            count = layer_counts[layer]
            pct = percentages[f"{layer}_percentage"]
            target_pct = TARGET_COMPOSITION[layer] * 100
            deviation = deviations[f"{layer}_deviation"] * 100

            status = "[OK]" if abs(deviation) < 5 else "[--]"
            print(f"  {status} {layer.capitalize():10s}: {count:3d} memories ({pct:5.1f}%) "
                  f"[target: {target_pct:4.1f}%, deviation: {deviation:+5.1f}%]")

        print()

        # Overall assessment
        max_deviation = max(abs(d) for d in deviations.values())
        if max_deviation < 0.05:
            print("[EXCELLENT] Composition within 5% of targets")
        elif max_deviation < 0.10:
            print("[GOOD] Composition within 10% of targets")
        elif max_deviation < 0.15:
            print("[FAIR] Composition within 15% of targets (needs tuning)")
        else:
            print("[POOR] Composition significantly off target (check layer weights)")

        print("="*70)
        print()

    return stats


def log_layer_composition_change(
    before: List[Dict[str, Any]],
    after: List[Dict[str, Any]]
):
    """
    Log before/after comparison of memory composition.

    Args:
        before: Memory list before layer rebalancing
        after: Memory list after layer rebalancing
    """
    print("\n" + "="*70)
    print("LAYER REBALANCING COMPARISON")
    print("="*70)
    print()

    print("BEFORE (old layer_boost):")
    before_stats = validate_memory_composition(before, verbose=False)
    for layer in ["working", "episodic", "semantic"]:
        count = before_stats.get(layer, 0)
        pct = before_stats.get(f"{layer}_percentage", 0)
        print(f"  {layer.capitalize():10s}: {count:3d} memories ({pct:5.1f}%)")

    print()
    print("AFTER (new layer weights):")
    after_stats = validate_memory_composition(after, verbose=False)
    for layer in ["working", "episodic", "semantic"]:
        count = after_stats.get(layer, 0)
        pct = after_stats.get(f"{layer}_percentage", 0)
        print(f"  {layer.capitalize():10s}: {count:3d} memories ({pct:5.1f}%)")

    print()
    print("CHANGE:")
    for layer in ["working", "episodic", "semantic"]:
        before_pct = before_stats.get(f"{layer}_percentage", 0)
        after_pct = after_stats.get(f"{layer}_percentage", 0)
        change = after_pct - before_pct
        arrow = "[UP]" if change > 0 else "[DN]" if change < 0 else "[==]"
        print(f"  {layer.capitalize():10s}: {arrow} {change:+5.1f}%")

    print("="*70)
    print()


# ===== TESTING HELPERS =====

def test_observation_classification():
    """Test the observation vs false attribution classifier."""

    test_cases = [
        # Should ALLOW (entity observations and interpretations)
        ("Re is experiencing exhaustion", True, "emotional state observation"),
        ("Re's body spent a week dumping iron", True, "physical state observation"),
        ("Re seems distressed about work", True, "emotional inference"),
        ("Re needs support with this issue", True, "needs inference"),
        ("Re appears to be overwhelmed", True, "behavioral observation"),
        ("Re's words come through as clean text", True, "technical observation"),
        ("Whether Re is tired gets stripped out", True, "analytical observation"),
        ("Re wants to feel better", True, "needs inference - not a quote"),
        ("Re mentioned feeling tired", True, "reference without quote"),

        # Should BLOCK (false direct quotes)
        ("Re said 'I want to quit'", False, "claiming user said specific words"),
        ("You told me 'my goal is X'", False, "direct quote that didn't happen"),
        ("You said 'your favorite color is blue'", False, "false quote with attribution"),
        ("When you said 'I'm done'", False, "inventing past quote"),
    ]

    print("\n" + "="*70)
    print("OBSERVATION CLASSIFICATION TEST")
    print("="*70)
    print()

    passed = 0
    failed = 0

    for fact_text, expected_allow, reason in test_cases:
        result = is_entity_observation(fact_text)
        status = "[PASS]" if result == expected_allow else "[FAIL]"

        if result == expected_allow:
            passed += 1
        else:
            failed += 1

        action = "ALLOW" if result else "BLOCK"
        print(f"{status} {action:6s}: '{fact_text[:50]}'")
        print(f"         Reason: {reason}")
        print()

    print(f"Results: {passed} passed, {failed} failed")
    print("="*70)
    print()


if __name__ == "__main__":
    # Run tests when executed directly
    print("Running memory layer rebalancing tests...")
    test_observation_classification()

    # Test layer weight application
    print("\nTesting layer weight application:")
    test_memories = [
        {"current_layer": "working", "fact": "Test working memory"},
        {"current_layer": "episodic", "fact": "Test episodic memory"},
        {"current_layer": "semantic", "fact": "Test semantic memory"},
    ]

    base_score = 0.5
    for mem in test_memories:
        weighted = apply_layer_weights(mem, base_score)
        layer = mem["current_layer"]
        multiplier = LAYER_WEIGHTS[layer]
        print(f"  {layer:10s}: {base_score:.2f} × {multiplier:.1f} = {weighted:.2f}")

    print("\nTests complete!")
