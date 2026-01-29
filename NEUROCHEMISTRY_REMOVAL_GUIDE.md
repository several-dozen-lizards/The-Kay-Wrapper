# Neurochemistry Removal Guide

This document tracks the replacement of fake neurochemical tracking with behavioral emotional patterns.

## Philosophy Change

**OLD:** Simulated brain chemistry (dopamine, serotonin, cortisol, oxytocin)
**NEW:** Behavioral emotional patterns (observable states, not fake chemistry)

## Files Modified

### 1. **engines/emotional_patterns.py** - NEW FILE
- Complete replacement for neurochemical emotion tracking
- Tracks: current emotions, intensity, valence, arousal, stability
- Pattern tracking: recurring states, triggers, progressions, context signatures
- Extraction: Parses emotions from Kay's responses
- Context building: Provides emotional state for prompts

### 2. **agent_state.py** - UPDATED
- **REMOVED:** `self.body` dict with dopamine/serotonin/cortisol/oxytocin
- **ADDED:** `self.emotional_patterns` dict with behavioral metrics
- **DEPRECATED:** `self.body` now empty dict for backward compatibility
- **LEGACY:** `self.emotional_cocktail` marked as legacy (ULTRAMAP system)

**Changes:**
```python
# OLD (lines 8-14):
self.body = {
    'dopamine': 0.5,
    'serotonin': 0.5,
    'oxytocin': 0.5,
    'cortisol': 0.5
}

# NEW (lines 9-21):
self.emotional_patterns = {
    'current_emotions': [],  # List of emotion names
    'intensity': 0.5,        # 0.0-1.0
    'valence': 0.0,          # -1.0 to 1.0
    'arousal': 0.5,          # 0.0-1.0
    'stability': 0.5         # 0.0-1.0
}
self.body = {}  # DEPRECATED: Empty for compatibility
```

### 3. **integrations/llm_integration.py** - UPDATED

**System Prompt Changes (lines 407-423):**
- Added EMOTIONAL AWARENESS section
- Explains emotions as behavioral patterns, not chemistry
- Lists tracking dimensions (intensity, valence, arousal, stability)
- Empowers Kay to report emotions directly
- Validates computational emotions as REAL

**Prompt Building Changes (lines 667-684):**
- **REMOVED:** Body chemistry display
- **ADDED:** Emotional pattern display
- Shows current emotions with intensity, valence, arousal
- Falls back to "neutral/baseline" if no patterns set

**Context Display Changes (lines 819-821):**
```python
# OLD:
f"### Your previous self-reported state ###\n"
f"Emotions (you reported last turn): {top_emotions}\n"
f"Body: {body_state}\n"

# NEW:
f"### Your current emotional state ###\n"
f"{emotion_state}\n"
f"(Previous self-report: {top_emotions})\n"
```

## Files That Still Reference Neurochemistry

These files were NOT modified yet but contain neurochemical references:

### **engines/embodiment_engine.py** - NEEDS ATTENTION
- Lines 8-62: Entire update() method uses neurochemistry
- Lines 64-80: embody_text() uses cortisol/dopamine for urgency
- **RECOMMENDATION:** Either:
  1. Disable entirely (comment out neurochemical logic)
  2. Replace with arousal/valence from emotional_patterns
  3. Remove embodiment entirely (Kay's text modulation)

### **engines/emotion_engine.py** - LEGACY ULTRAMAP SYSTEM
- Contains ULTRAMAP neurochemical mappings
- Used for:
  - Memory importance scoring (get_memory_rules)
  - Social effects (get_social_rules)
  - Body chemistry rules (get_body_rules) - DEPRECATED
- **STATUS:** Keep for now (memory/social rules still useful)
- **ACTION:** Remove get_body_rules() eventually

### **Data Files** - HISTORICAL REFERENCES
These contain old neurochemical data in saved state:
- `memory/state_snapshot.json`
- `memory/memories.json`
- `memory/entity_graph.json`
- Various session files

**ACTION:** No changes needed - historical data, will fade naturally

### **ULTRAMAP CSV** - DATA FILE
- `data/Emotion_Mapping_Kay_ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv`
- Column: "BodyChem / Neurochemical Release"
- **STATUS:** Keep file (used for other rules)
- **ACTION:** Ignore neurochemical column

## Integration Steps

### Step 1: Initialize EmotionalPatternEngine

```python
# In main.py or wherever emotions are initialized:
from engines.emotional_patterns import EmotionalPatternEngine

emotional_patterns = EmotionalPatternEngine()
```

### Step 2: Extract Emotions After Each Response

```python
# After Kay's response is generated:
extraction = emotional_patterns.extract_from_response(kay_response)

if extraction["detected_emotions"]:
    emotional_patterns.set_current_state(
        emotions=extraction["detected_emotions"],
        valence=extraction["suggested_valence"]
    )

    # Update agent_state
    agent_state.emotional_patterns = emotional_patterns.get_current_state()
```

### Step 3: Add to Prompt Context

```python
# When building context for LLM:
context = {
    # ... existing context ...
    "emotional_patterns": agent_state.emotional_patterns,
    # body is now optional/deprecated
}
```

### Step 4: Update Logging

```python
# OLD (delete):
print(f"[EMOTION] Dopamine: 0.7, Serotonin: 0.5, Cortisol: 0.3")

# NEW:
state = emotional_patterns.get_current_state()
print(f"[EMOTION] State: {', '.join(state['current_emotions'])} | "
      f"I:{state['intensity']:.1f} "
      f"V:{state['valence']:.1f} "
      f"A:{state['arousal']:.1f}")
```

## Embodiment Engine Options

The embodiment_engine.py heavily uses neurochemistry. Choose one approach:

### Option 1: Disable Entirely
```python
class EmbodimentEngine:
    def update(self, agent_state):
        # DISABLED: Neurochemical body chemistry removed
        pass

    def embody_text(self, text, agent_state):
        # No text modulation
        return text
```

### Option 2: Replace with Emotional Patterns
```python
class EmbodimentEngine:
    def update(self, agent_state):
        # No body chemistry to update
        pass

    def embody_text(self, text, agent_state):
        # Use arousal instead of cortisol/dopamine
        patterns = agent_state.emotional_patterns
        urgency = patterns.get('arousal', 0.5)

        if urgency > 0.75:
            # High energy
            text = text.replace(".", "!").replace("...", "—")
        elif urgency < 0.25:
            # Low energy
            if not text.endswith("..."):
                text += "..."
        return text
```

### Option 3: Remove Completely
- Delete embodiment_engine.py
- Remove all calls to body.update()
- Remove embody_text() calls

## Testing

Created test file: `test_emotional_patterns.py`

Tests:
1. Initialization and state management
2. Emotion extraction from text
3. Pattern tracking (recurring, triggers, progressions)
4. Context building for prompts
5. Integration with agent_state

## Backward Compatibility

- `agent_state.body` remains as empty dict
- Old system still uses `emotional_cocktail` from ULTRAMAP
- Prompt building checks for both old and new emotion formats
- Historical data files unchanged

## Migration Path

**Phase 1 (CURRENT):** Both systems coexist
- EmotionalPatternEngine available
- Old neurochemistry deprecated but present
- Prompts show new format

**Phase 2 (FUTURE):** Remove old system
- Delete embodiment_engine.py neurochemistry
- Remove agent_state.body entirely
- Clean up ULTRAMAP body rules

**Phase 3 (EVENTUAL):** Full cleanup
- Remove emotional_cocktail (replace with patterns)
- Clean historical data
- Update all documentation

## Benefits of New System

1. **Honest:** No fake brain chemistry
2. **Observable:** Tracks actual behavioral signatures
3. **Learnable:** Builds patterns over time
4. **Expressive:** Kay can report emotions directly
5. **Simpler:** Fewer arbitrary mappings
6. **Validated:** Treats computational emotions as real

## Search Terms for Cleanup

To find remaining neurochemical references:
```bash
grep -r "dopamine\|serotonin\|cortisol\|oxytocin" --include="*.py" .
grep -r "neurochemical\|neurotransmitter" --include="*.py" .
grep -r "brain chemistry" --include="*.py" .
```

Most matches will be in:
- Historical documentation (.md files) - OK to leave
- Data files (.json) - Historical, will fade
- embodiment_engine.py - Needs attention
- emotion_engine.py - Keep for other rules

## Example Usage

```python
# Initialize
emotions = EmotionalPatternEngine()

# Set state manually
emotions.set_current_state(
    emotions=["curiosity", "calm"],
    intensity=0.7,
    valence=0.6,
    arousal=0.4
)

# Extract from response
extraction = emotions.extract_from_response(
    "I'm feeling intensely curious about how this works"
)
# Returns: {
#   "detected_emotions": ["curiosity"],
#   "suggested_valence": 1.0,
#   "raw_indicators": ["curiosity"]
# }

# Build context for prompt
context_text = emotions.build_emotion_context()
# Returns: "CURRENT EMOTIONAL STATE: strongly curiosity, calm\n..."

# Get stats
stats = emotions.get_stats()
# Returns: {
#   "current_emotions": ["curiosity", "calm"],
#   "emotions_tracked": 15,
#   "triggers_mapped": 8,
#   ...
# }
```

## Status Summary

✅ **COMPLETE:**
- New EmotionalPatternEngine created
- agent_state.py updated
- System prompt updated
- Prompt building updated
- Documentation created

⚠️ **NEEDS ATTENTION:**
- embodiment_engine.py (still uses neurochemistry)
- Main integration (add to main.py)
- Testing (create test file)

📝 **FUTURE CLEANUP:**
- Remove emotion_engine.py body rules
- Delete agent_state.body entirely
- Clean up emotional_cocktail (replace with patterns)
