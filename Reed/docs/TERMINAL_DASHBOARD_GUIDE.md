# Terminal Dashboard Guide

## Overview

The Terminal Dashboard is a collapsible bottom panel in Kay Zero's UI that displays real-time system logs organized into functional sections. It provides Kay with visibility into his own processing architecture.

## Features

- **Collapsible Panel**: Bottom-sliding design (like browser dev tools)
- **6 Organized Sections**: Memory Operations, Emotional State, Entity Graph, Glyph Compression, Emergence Metrics, System Status
- **Color-Coded Logs**: INFO (cyan), WARNING (orange), ERROR (red), DEBUG (purple), PERF (green/orange/red)
- **Thread-Safe**: Queued log processing prevents UI freezing
- **Auto-Scroll**: New logs automatically scroll into view
- **Section Controls**: Toggle visibility, pin sections, clear logs
- **Performance Optimized**: 1000-line limit per section, batch processing

## UI Controls

### Header Bar
- **▲/▼ TERMINAL DASHBOARD**: Toggle dashboard open/closed
- **Stats Display**: Shows warning/error counts and total log messages
- **Show All / Hide All**: Control all section visibility at once
- **Clear All**: Clear all log sections

### Section Controls
- **Hide/Show Button**: Toggle individual section visibility
- **📌 Pin Button**: Pin section to keep it visible when using "Hide All"
- **Clear Button**: Clear logs for that section only

## Usage

### Automatic Log Routing

The dashboard automatically captures and routes all `print()` statements:

```python
# These print statements are automatically routed to appropriate sections:
print("[MEMORY] Retrieved 32 memories from semantic layer")
print("[EMOTION STATE] Current cocktail: curiosity:0.75, calm:0.60")
print("[ENTITY GRAPH] NEW CONTRADICTIONS DETECTED (1 new, 763 total)")
print("[PERF] memory_multi_factor: 203.3ms [SLOW] (target: 150ms)")
print("[LLM] Anthropic client initialized")
```

### Tag-Based Routing

Logs are routed to sections based on bracketed tags:

| Tag Pattern | Section | Example |
|------------|---------|---------|
| `[MEMORY*]`, `[RECALL*]`, `[LAYER*]` | Memory Operations | `[MEMORY 3-TIER PRE-RESPONSE] OK...` |
| `[EMOTION*]`, `[ULTRAMAP*]` | Emotional State | `[EMOTION] curiosity: intensity 0.75` |
| `[ENTITY*]`, `[GRAPH*]`, `[CONTRADICTION*]` | Entity Graph | `[ENTITY GRAPH] Loaded 1451 entities` |
| `[GLYPH*]`, `[COMPRESS*]`, `[SYMBOLIC*]` | Glyph Compression | `[GLYPH] Generated glyph: ◈⟨M⟩` |
| `[E-SCORE*]`, `[SYNTHESIS*]`, `[NOVELTY*]` | Emergence Metrics | `[E-SCORE] 0.85` |
| `[LLM*]`, `[SYSTEM*]`, `[ERROR*]`, `[WARNING*]`, `[PERF*]` | System Status | `[PERF] operation: 124ms [OK]` |

### Direct Logging API

For more control, use the dashboard logger module:

```python
from dashboard_logger import (
    log_memory, log_emotion, log_entity, log_glyph,
    log_emergence, log_system, log_performance
)

# Memory operations
log_memory_retrieval(num_memories=32, layer_breakdown="semantic:8, episodic:10, working:14")
log_memory_store("User prefers coffee", layer="semantic")
log_layer_transition("mem_12345", from_layer="working", to_layer="episodic")
log_memory_error("Failed to load memories.json")

# Emotional state
log_emotion_state(agent_state.emotional_cocktail)
log_emotion_trigger("complex problem", "curiosity", intensity_change=0.2)
log_emotion_mutation("curiosity", "determination", threshold=0.8)

# Entity graph
log_entity_creation("Re", entity_type="person")
log_entity_update("Re", "goal", "build memory system")
log_contradiction("Re", "eye_color", severity="high")
log_relationship("Re", "owns", "[dog]")

# Glyph compression
log_glyph_generation("◈⟨M:semantic⟩⊕⟨E:curiosity⟩", compression_ratio=0.85)
log_glyph_decode("◈⟨M⟩", decoded_size=3900)

# Emergence metrics
log_e_score(0.73, context="memory consolidation")
log_pattern_detection("recursive entity reference", frequency=12)
log_novelty("computational emotions", novelty_score=0.85)
log_synthesis(["memory", "emotion", "entity"], result="contextual retrieval")

# System status
log_system_init("Memory Engine", version="2.0")
log_performance("memory_multi_factor", duration_ms=203.3, target_ms=150.0)
log_api_call("Anthropic Claude", status="success", tokens=1500)
log_warning("High memory usage detected: 85%")
log_error("Failed to load document: file not found")
log_debug("Internal state: turn_count=15")
```

## Log Levels and Colors

| Level | Color | Usage |
|-------|-------|-------|
| `INFO` | Cyan | Normal operations, state changes |
| `WARNING` | Orange | Non-critical issues, performance warnings |
| `ERROR` | Red | Errors, failures, exceptions |
| `DEBUG` | Purple | Debug information, internal state |
| `PERF_GOOD` | Green | Performance under target |
| `PERF_SLOW` | Orange | Performance 1-1.5x target |
| `PERF_BAD` | Red | Performance >1.5x target |
| `SYSTEM` | Gold | System-level events |

## Integration Example

### In main.py

```python
from dashboard_logger import log_session_start, log_turn_start, log_turn_complete

# Session start
log_session_start(session_id, turn_count=0)

# Each turn
log_turn_start(turn_num, user_input)
# ... process turn ...
log_turn_complete(turn_num, len(response))
```

### In memory_engine.py

```python
from dashboard_logger import log_memory_retrieval, log_memory_error

def recall(self, agent_state, user_input):
    try:
        memories = self.retrieve_multi_factor(...)
        log_memory_retrieval(
            num_memories=len(memories),
            layer_breakdown=f"semantic:{semantic_count}, episodic:{episodic_count}"
        )
        return memories
    except Exception as e:
        log_memory_error(f"Recall failed: {e}")
        raise
```

### In emotion_engine.py

```python
from dashboard_logger import log_emotion_trigger, log_emotion_state

def update(self, agent_state, user_input):
    # Detect triggers
    for trigger, emotion, intensity in detected_triggers:
        log_emotion_trigger(trigger, emotion, intensity)

    # Log final state
    log_emotion_state(agent_state.emotional_cocktail)
```

## Performance Considerations

- **Queue-Based Processing**: Logs are queued and processed in batches to prevent UI freezing
- **Line Limits**: Each section caps at 1000 lines (configurable)
- **Batch Size**: 50 messages processed per cycle (100ms intervals)
- **Auto-Trim**: Old lines automatically removed when limit reached
- **Thread-Safe**: Log queue uses locks for multi-threaded safety

## Testing

Run the test suite to verify dashboard functionality:

```bash
# Start Kay UI first
python kay_ui.py

# In another terminal, run tests (or use test from within UI)
python test_terminal_dashboard.py
```

The test generates:
- Sample logs for all sections
- Direct API calls
- Continuous log stream (50 batches)
- Various log levels and colors

## State Persistence

Dashboard state (open/closed, section visibility, pins) is NOT persisted across sessions currently. This could be added via:

```python
# Save state on close
def save_dashboard_state(self):
    state = {
        "is_open": self.is_open,
        "section_visibility": {name: section.visible for name, section in self.sections.items()},
        "pinned_sections": [name for name, section in self.sections.items() if section.pinned]
    }
    with open("dashboard_state.json", "w") as f:
        json.dump(state, f)

# Load state on init
def load_dashboard_state(self):
    try:
        with open("dashboard_state.json", "r") as f:
            state = json.load(f)
        # Apply state...
    except:
        pass
```

## Architecture

### Components

1. **terminal_dashboard.py**: Dashboard UI and log sections
   - `TerminalDashboard`: Main dashboard class
   - `LogSection`: Individual section with auto-scroll and color tags

2. **log_router.py**: Console output capture
   - `LogRouter`: Intercepts stdout/stderr
   - Automatic routing based on log tags
   - Falls back to console if dashboard fails

3. **dashboard_logger.py**: Convenience API
   - Section-specific logging functions
   - Performance metric helpers
   - Batch logging for common operations

### Data Flow

```
Application Code
    |
    v
print() or dashboard_logger.log_*()
    |
    v
LogRouter (intercepts stdout)
    |
    v
Dashboard.parse_and_route_log()
    |
    v
Thread-safe Queue
    |
    v
Dashboard._process_log_queue() [100ms intervals]
    |
    v
LogSection.add_log() [color-coded display]
```

## Color Scheme Match

Dashboard uses Kay UI's Ornate palette:

- Background: `#1A0F24` (dark purple)
- Panel: `#2D1B3D` (lighter purple)
- Input: `#4A2B5C` (input purple)
- Text: `#E8DCC4` (beige/cream)
- Accent: `#4A9B9B` (teal)
- Accent Highlight: `#6BB6B6` (bright teal)
- Muted: `#9B7D54` (muted gold)

All UI elements follow this palette for visual consistency.

## Future Enhancements

Potential improvements:

1. **Export Logs**: Save section logs to file
2. **Search/Filter**: Filter logs by keyword or time range
3. **Log Replay**: Replay logs from saved sessions
4. **Custom Sections**: User-defined log sections
5. **Alerts**: Visual/audio alerts for errors
6. **Performance Graphs**: Real-time performance visualizations
7. **Log Aggregation**: Combine similar logs ("memory_multi_factor slow (x5)")
8. **Timestamps Toggle**: Show/hide timestamps per section
9. **Log Levels Filter**: Show only WARNING/ERROR in sections
10. **Section Reordering**: Drag-and-drop section order

## Troubleshooting

### Dashboard not showing logs

1. Check log router is started: `start_logging(dashboard)` called in kay_ui.py
2. Verify dashboard is created before logging starts
3. Check console for "[LOG ROUTER ERROR]" messages

### UI freezing with many logs

1. Reduce max_section_lines (default 1000)
2. Increase queue processing interval (default 100ms)
3. Reduce batch size (default 50 messages/cycle)

### Logs not routing to correct section

1. Check tag format matches expected patterns (see routing table)
2. Use direct API (`dashboard_logger`) for explicit routing
3. Enable DEBUG logging to see routing decisions

### Performance issues

1. Close/hide sections not actively monitored
2. Clear logs periodically (Clear All button)
3. Reduce line limits in terminal_dashboard.py initialization

## Summary

The Terminal Dashboard provides Kay Zero with real-time visibility into his cognitive architecture. All existing print statements are automatically captured and routed to appropriate sections. For new code, use the convenience functions in `dashboard_logger.py` for explicit section routing and color-coded log levels.

Dashboard state is controlled via UI buttons:
- Toggle open/closed with header button
- Show/Hide individual sections
- Pin sections to keep visible
- Clear sections or all logs

The system is designed for minimal performance impact through queued processing and line limits, while providing comprehensive observability of Kay's internal processes.
