"""
Dashboard Logger - Convenience functions for logging to terminal dashboard sections.

Provides easy-to-use functions for logging to specific dashboard sections with appropriate levels.
Falls back to console if dashboard not available.
"""

from log_router import log_to_dashboard


# === Memory Operations ===

def log_memory(message: str, level: str = "INFO"):
    """Log to Memory Operations section."""
    log_to_dashboard(message, "Memory Operations", level)


def log_memory_retrieval(num_memories: int, layer_breakdown: str = ""):
    """Log memory retrieval event."""
    msg = f"Retrieved {num_memories} memories"
    if layer_breakdown:
        msg += f" ({layer_breakdown})"
    log_memory(msg, "INFO")


def log_memory_store(fact: str, layer: str = "working"):
    """Log memory storage event."""
    log_memory(f"Stored {layer} memory: {fact[:50]}...", "INFO")


def log_layer_transition(memory_id: str, from_layer: str, to_layer: str):
    """Log memory layer transition."""
    log_memory(f"Layer transition: {from_layer} -> {to_layer} (mem: {memory_id[:20]}...)", "INFO")


def log_memory_error(error: str):
    """Log memory system error."""
    log_memory(f"ERROR: {error}", "ERROR")


# === Emotional State ===

def log_emotion(message: str, level: str = "INFO"):
    """Log to Emotional State section."""
    log_to_dashboard(message, "Emotional State", level)


def log_emotion_state(emotions: dict):
    """Log current emotional cocktail state."""
    emotion_str = ", ".join([f"{k}:{v.get('intensity', 0):.2f}" for k, v in emotions.items() if isinstance(v, dict)])
    log_emotion(f"Current state: {emotion_str}", "INFO")


def log_emotion_trigger(trigger: str, emotion: str, intensity_change: float):
    """Log emotion trigger event."""
    change_str = f"+{intensity_change:.2f}" if intensity_change > 0 else f"{intensity_change:.2f}"
    log_emotion(f"Trigger '{trigger}' -> {emotion} ({change_str})", "INFO")


def log_emotion_mutation(from_emotion: str, to_emotion: str, threshold: float):
    """Log emotion mutation event."""
    log_emotion(f"Mutation: {from_emotion} -> {to_emotion} (threshold: {threshold:.2f})", "INFO")


# === Entity Graph ===

def log_entity(message: str, level: str = "INFO"):
    """Log to Entity Graph section."""
    log_to_dashboard(message, "Entity Graph", level)


def log_entity_creation(entity_name: str, entity_type: str = "unknown"):
    """Log new entity creation."""
    log_entity(f"Created entity: {entity_name} (type: {entity_type})", "INFO")


def log_entity_update(entity_name: str, attribute: str, value: str):
    """Log entity attribute update."""
    log_entity(f"Updated {entity_name}.{attribute} = {value[:30]}...", "INFO")


def log_contradiction(entity_name: str, attribute: str, severity: str = "moderate"):
    """Log entity contradiction detection."""
    log_entity(f"CONTRADICTION [{severity}]: {entity_name}.{attribute}", "WARNING")


def log_relationship(subject: str, relationship: str, target: str):
    """Log relationship creation/update."""
    log_entity(f"Relationship: {subject} --[{relationship}]-> {target}", "INFO")


# === Glyph Compression ===

def log_glyph(message: str, level: str = "DEBUG"):
    """Log to Glyph Compression section."""
    log_to_dashboard(message, "Glyph Compression", level)


def log_glyph_generation(glyph: str, compression_ratio: float):
    """Log glyph generation event."""
    log_glyph(f"Generated glyph: {glyph} (compression: {compression_ratio:.1%})", "DEBUG")


def log_glyph_decode(glyph: str, decoded_size: int):
    """Log glyph decoding event."""
    log_glyph(f"Decoded glyph: {glyph} -> {decoded_size} items", "DEBUG")


# === Emergence Metrics ===

def log_emergence(message: str, level: str = "INFO"):
    """Log to Emergence Metrics section."""
    log_to_dashboard(message, "Emergence Metrics", level)


def log_e_score(score: float, context: str = ""):
    """Log E-score calculation."""
    msg = f"E-score: {score:.3f}"
    if context:
        msg += f" ({context})"
    log_emergence(msg, "INFO")


def log_pattern_detection(pattern: str, frequency: int):
    """Log pattern detection event."""
    log_emergence(f"Pattern detected: '{pattern}' (freq: {frequency})", "INFO")


def log_novelty(concept: str, novelty_score: float):
    """Log novelty detection."""
    log_emergence(f"Novel concept: '{concept}' (score: {novelty_score:.3f})", "INFO")


def log_synthesis(components: list, result: str):
    """Log synthesis event."""
    comp_str = " + ".join(components[:3])
    log_emergence(f"Synthesis: {comp_str} -> {result}", "INFO")


# === System Status ===

def log_system(message: str, level: str = "INFO"):
    """Log to System Status section."""
    log_to_dashboard(message, "System Status", level)


def log_system_init(component: str, version: str = ""):
    """Log system component initialization."""
    msg = f"Initialized: {component}"
    if version:
        msg += f" v{version}"
    log_system(msg, "INFO")


def log_performance(operation: str, duration_ms: float, target_ms: float = None):
    """Log performance metric."""
    if target_ms:
        if duration_ms <= target_ms:
            level = "PERF_GOOD"
            status = "[OK]"
        elif duration_ms <= target_ms * 1.5:
            level = "PERF_SLOW"
            status = "[SLOW]"
        else:
            level = "PERF_BAD"
            status = "[BAD]"
        msg = f"{operation}: {duration_ms:.1f}ms {status} (target: {target_ms}ms)"
    else:
        level = "INFO"
        msg = f"{operation}: {duration_ms:.1f}ms"

    log_system(msg, level)


def log_api_call(api: str, status: str, tokens: int = None):
    """Log API call event."""
    msg = f"API call: {api} [{status}]"
    if tokens:
        msg += f" ({tokens} tokens)"
    log_system(msg, "INFO")


def log_warning(message: str):
    """Log system warning."""
    log_system(message, "WARNING")


def log_error(message: str):
    """Log system error."""
    log_system(message, "ERROR")


def log_debug(message: str):
    """Log debug information."""
    log_system(message, "DEBUG")


# === Convenience Batch Logging ===

def log_session_start(session_id: str, turn_count: int = 0):
    """Log session start with initialization of all sections."""
    log_system(f"Session started: {session_id} (turn: {turn_count})", "INFO")
    log_memory("Memory system online", "INFO")
    log_emotion("Emotion tracking active", "INFO")
    log_entity("Entity graph loaded", "INFO")
    log_glyph("Glyph compression ready", "DEBUG")
    log_emergence("Emergence metrics initialized", "INFO")


def log_turn_start(turn_num: int, user_input: str):
    """Log turn start."""
    log_system(f"Turn {turn_num} started", "INFO")
    log_memory(f"Processing input: {user_input[:50]}...", "INFO")


def log_turn_complete(turn_num: int, response_length: int):
    """Log turn completion."""
    log_system(f"Turn {turn_num} complete (response: {response_length} chars)", "INFO")
