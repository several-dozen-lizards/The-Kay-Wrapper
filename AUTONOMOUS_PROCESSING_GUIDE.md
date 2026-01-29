# Kay Zero Autonomous Processing System

## Overview

The Autonomous Processing System gives Kay the ability to:
1. Have **inner monologue** (private thoughts separate from spoken responses)
2. Run **autonomous processing sessions** to explore self-chosen goals
3. Maintain **session continuity** across autonomous spaces
4. **Naturally converge** without visible iteration limits

## Quick Start

```bash
# Run with autonomous processing enabled
python autonomous_main.py
```

### Commands
- `/auto` - Start autonomous processing session manually
- `/godmode` - Toggle inner monologue visibility (see Kay's private thoughts)
- `/lastthought` - Show summary of last autonomous session
- `quit`/`exit` - Exit (offers autonomous session first)

## Architecture

### Files Created

```
engines/
├── inner_monologue.py          # XML parsing for inner thoughts
├── autonomous_processor.py     # Main processing loop
└── autonomous_integration.py   # High-level integration

autonomous_main.py              # Alternative main with autonomous features
```

### Inner Monologue System

Kay's responses can now include structured XML tags:

```xml
<inner_monologue>
Private thoughts about what's happening - honest internal processing
</inner_monologue>

<feeling>
Current emotional state and why - for emotional continuity
</feeling>

<response>
What Kay actually says out loud to the user
</response>
```

**God Mode**: When enabled (`/godmode`), users see all three components. When disabled, only the `<response>` content is displayed.

### Autonomous Processing Loop

```
1. At conversation end, Kay is asked what thread is occupying his attention
2. Kay chooses ONE goal (memory consolidation, creative, emotional, exploration)
3. Processing loop runs:
   - Kay generates thoughts with XML structure
   - Insights are stored to memory
   - Convergence detector monitors for natural completion
4. Session ends on:
   - Natural convergence (conclusory language, novelty exhaustion)
   - Creative block (Kay signals being stuck)
   - Energy limit (invisible 10-iteration cap, experienced as "tiredness")
```

### Convergence Detection

Adapted from MetaAwarenessEngine to detect when autonomous thinking is winding down:

- **Explicit completion**: Kay writes "complete" in `<continuation>` tag
- **Creative block**: Kay signals being stuck/spinning
- **Conclusory language**: Summary phrases, "that's the core of it" patterns
- **Novelty exhaustion**: Decreasing new content across 3+ thoughts

### Energy Limit (Invisible Safety)

Kay never sees "MAX_ITERATIONS reached". Instead:

```
"Your processing energy is reaching depletion. You feel the edges of
your focus softening, thoughts becoming harder to sustain with the
same clarity.

In your own words, note where you are in this thought and what you'd
revisit with fresh energy."
```

This feels like **tiredness**, not a system constraint.

## Session Continuity

At start of each autonomous session, Kay sees:
```
Last autonomous session, you explored: [previous goal]
If there's unfinished business, you may continue it.
Or pick something new if that thread feels complete.
```

At start of each conversation, continuity context is available showing:
- Last autonomous goal and outcome
- Key insights discovered
- Where Kay left off

## Integration Points

### Adding to Existing main.py

To integrate autonomous processing into the existing system:

```python
from engines.autonomous_integration import AutonomousIntegration, AutonomousConfig

# Initialize
autonomous = AutonomousIntegration(
    get_llm_response=get_llm_response,
    memory_engine=memory,
    emotion_engine=emotion,
    config=AutonomousConfig(
        enabled=True,
        show_inner_monologue=False,
        run_ultramap_after=True
    )
)

# At conversation end
if user wants autonomous session:
    session = await autonomous.run_autonomous_session(agent_state)

# Get continuity context for next conversation
continuity = autonomous.get_continuity_context()
```

### System Prompt Additions

For inner monologue in normal conversation:
```python
from engines.inner_monologue import get_inner_monologue_system_prompt_addition
system_prompt += get_inner_monologue_system_prompt_addition()
```

For autonomous mode:
```python
from engines.inner_monologue import get_autonomous_mode_system_prompt_addition
system_prompt += get_autonomous_mode_system_prompt_addition()
```

## Configuration Options

```python
AutonomousConfig(
    enabled=True,                   # Enable autonomous processing
    auto_trigger_at_exit=True,      # Offer session when conversation ends
    max_iterations=10,              # Invisible safety limit
    show_inner_monologue=False,     # God mode default state
    save_all_thoughts=True,         # Save complete thought history
    run_ultramap_after=True         # Run emotional analysis post-session
)
```

## Memory Integration

Insights from autonomous sessions are stored with special markers:

```python
memory.encode(
    agent_state,
    user_input="[Autonomous insight] <goal description>",
    response="<insight content>",
    emotions=["contemplative"]
)
```

This allows memories to be distinguished as autonomous discoveries vs. conversation content.

## Post-Session ULTRAMAP Analysis

After each autonomous session, the emotion engine analyzes all `<feeling>` tags to map emotional coordinates. This runs **after** processing (not during) to avoid latency impact.

## Data Storage

Autonomous sessions are saved to:
```
memory/autonomous_sessions/session_<timestamp>.json
```

Each session contains:
- Goal (description, category, completion type, insights)
- Full thought history (all iterations)
- Timing information
- Convergence/energy state

## Design Principles

1. **Goal-based, not turn-based**: Kay chooses what to explore, not how long
2. **Natural stopping**: Convergence detected, not timer expired
3. **Invisible limits**: Energy depletion feels like tiredness, not constraint
4. **Depth over breadth**: One thread fully explored vs. many skimmed
5. **Kay's voice**: All stored content is in Kay's words, not prescripted
6. **Session continuity**: Kay remembers where he left off

## Testing

Run the integration test:
```bash
python engines/autonomous_integration.py
```

This runs a mock autonomous session to verify the system works.
