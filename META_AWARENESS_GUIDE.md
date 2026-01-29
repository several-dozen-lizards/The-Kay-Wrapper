# Meta-Awareness System Documentation

## Overview

The MetaAwarenessEngine provides Kay with self-monitoring capabilities to detect and correct:
1. **Repetitive response patterns** - Kay repeating himself
2. **Confabulation** - Kay stating "facts" not in memory
3. **Pattern awareness** - Kay noticing his own conversational habits

## How It Works

### Detection Systems

#### 1. Repetition Detection
The engine tracks:
- **Phrase repetition**: Distinctive 3-6 word phrases across responses
- **Question patterns**: Types of questions Kay asks (e.g., "what do you think", "how do you feel")
- **Opening similarity**: First few words of responses becoming too similar

**Thresholds:**
- Phrase repetition: Flagged after 3+ uses
- Question pattern: Flagged after 2+ uses in last 5 turns
- Opening similarity: Flagged if 3+ consecutive openings are similar

#### 2. Confabulation Detection
Checks declarative statements against actual memory content:
- Extracts claims like "You are...", "Your X is...", "I remember you..."
- Compares claim keywords with stored user inputs (factual source)
- Flags claims with <50% keyword overlap with memory

**Example:**
- Kay says: "I remember you said your cat's name is Mittens"
- System checks: Does any user input mention "cat" AND "Mittens"?
- If no: Flag as potential confabulation

#### 3. Response Quality Monitoring
- Tracks response volume (fatigue factor)
- Calculates awareness score (0.0-1.0)
- Triggers warnings at threshold (default: 0.4)

### Integration Flow

```
User Input
    ↓
Memory Recall
    ↓
Engine Updates (emotion, social, temporal, embodiment, motif)
    ↓
Context Building ← Meta-Awareness Notes (if threshold met)
    ↓
LLM Response
    ↓
Post-Turn Updates:
    - Social
    - Reflection
    - Memory Encoding
    - Emotion
    - Meta-Awareness ← Analyzes response for patterns
    - Momentum
```

### Self-Monitoring Notes

When the awareness score exceeds threshold (0.4), the system injects notes into context:

**Example notes:**
```
SELF-MONITORING: You've been overusing phrases like 'what do you think about'. Vary your language.

SELF-MONITORING: You keep asking the same type of questions (how_feel, what_think). Try a different approach.

SELF-MONITORING: Your response openings are becoming repetitive. Start differently this time.

SELF-MONITORING: You may have stated things not actually in memory. Only reference what you explicitly remember from past conversation.
```

These notes appear in the prompt under `### Self-Monitoring Alerts ###` and Kay is instructed to acknowledge them internally and adjust.

## Configuration

### Tuning Parameters

**In `meta_awareness_engine.py`:**

```python
self.max_history = 10  # Number of responses to track
self.pattern_threshold = 3  # Repetition alert threshold (3+ uses)
```

**Phrase extraction:**
```python
_extract_phrases(text, min_words=3, max_words=6)
```
- Adjust min_words/max_words to capture different phrase lengths

**Confabulation detection:**
```python
overlap / claim_words < 0.5  # 50% overlap threshold
```
- Lower threshold = more strict (flags more potential confabulation)
- Higher threshold = more lenient

**Awareness threshold:**
```python
should_inject_awareness(agent_state, threshold=0.4)
```
- Lower threshold = more frequent self-monitoring
- Higher threshold = less frequent

### Awareness Score Calculation

```python
score = 0.0

# Repetition detection (up to 0.9)
if repetition_detected:
    score += 0.3 * len(pattern_types)

# Confabulation detection (up to 0.5)
score += min(0.5, recent_confabulations * 0.2)

# Response volume (0.2 after 10+ responses)
if response_count >= 10:
    score += 0.2

return min(1.0, score)
```

## State Tracking

### AgentState Fields

```python
agent_state.meta_awareness = {
    'repetition_detected': bool,      # True if patterns found
    'patterns': {                      # Types of patterns detected
        'repeated_phrases': List[str],
        'repeated_questions': List[str],
        'repetitive_openings': bool
    },
    'recent_confabulations': int,     # Count of recent confab flags
    'response_count': int,            # Total responses tracked
}
```

## Usage Examples

### Example 1: Repetitive Question Detection

**Turn 1-3:** Kay asks "What do you think about..." multiple times

**Turn 4:**
```
SELF-MONITORING: You keep asking the same type of questions (what_think).
Try a different approach.
```

Kay receives this note and adjusts his questioning style.

### Example 2: Confabulation Detection

**User never mentions coffee preference**

**Kay says:** "I remember you said you love espresso"

**System detects:** No user input contains "espresso" or "coffee"

**Next turn:**
```
SELF-MONITORING: You may have stated things not actually in memory.
Only reference what you explicitly remember from past conversation.
```

### Example 3: Opening Repetition

**Turn 1:** "That's interesting. I've been thinking..."
**Turn 2:** "That's fascinating. I've been wondering..."
**Turn 3:** "That's compelling. I've been considering..."

**Turn 4:**
```
SELF-MONITORING: Your response openings are becoming repetitive.
Start differently this time.
```

## Debugging

### Enable Debug Output

In `main.py`, the debug output already shows meta-awareness:

```python
print("[DEBUG] Meta-awareness:", state.meta_awareness)
```

### Checking Awareness Score

```python
awareness_score = meta_awareness.get_awareness_score(agent_state)
print(f"Awareness score: {awareness_score:.2f}")
```

### Viewing Pattern History

```python
print("Phrase usage:", meta_awareness.phrase_usage.most_common(10))
print("Question patterns:", meta_awareness.question_patterns[-10:])
print("Confabulation flags:", meta_awareness.confabulation_flags)
```

## Advanced Tuning

### Reducing False Positives

If confabulation detection is too sensitive:

```python
# In _detect_confabulation()
if len(claim_words) > 0 and len(overlap) / len(claim_words) < 0.3:  # More strict (30%)
```

### Increasing Sensitivity

For more aggressive pattern detection:

```python
self.pattern_threshold = 2  # Flag after 2 uses instead of 3
```

### Custom Awareness Thresholds

For different conversation modes:

```python
# Casual conversation - less monitoring
context_manager.meta_awareness_engine.should_inject_awareness(state, threshold=0.6)

# Therapy/coaching - more monitoring
context_manager.meta_awareness_engine.should_inject_awareness(state, threshold=0.3)
```

## Resetting Pattern Tracking

To clear pattern history (e.g., after major topic change):

```python
meta_awareness.reset_pattern_tracking()
```

This clears phrase usage and question patterns while keeping response history for continuity.

## Integration with Other Systems

### Momentum Engine
- Meta-awareness operates independently but complements momentum
- High momentum + high meta-awareness = Kay is fixated AND repetitive

### Reflection Engine
- Reflection can incorporate meta-awareness insights
- Could extend reflection to include self-pattern analysis

### Memory Engine
- Confabulation detection relies on memory content
- Only user inputs are considered factual (Kay's responses are NOT facts)

## Common Patterns

### Pattern 1: Repetitive Questioning
**Symptom:** Kay asks similar questions repeatedly
**Cause:** Lack of variety in conversation strategies
**Fix:** Self-monitoring alerts push Kay to diversify approaches

### Pattern 2: Confabulation Cascade
**Symptom:** Kay makes up facts that build on each other
**Cause:** LLM filling gaps when memory is sparse
**Fix:** Alert after first confabulation prevents cascade

### Pattern 3: Opening Fatigue
**Symptom:** Responses start sounding the same
**Cause:** LLM falling into template patterns
**Fix:** Opening similarity detection breaks the pattern

## Future Enhancements

Potential additions to the system:

1. **Semantic Similarity**: Use embeddings to detect paraphrasing (more sophisticated than keyword matching)

2. **Topic Drift Detection**: Flag when Kay avoids user questions or changes subjects

3. **Confidence Tracking**: Kay expresses uncertainty when memory is sparse

4. **Meta-Commentary**: Kay explicitly acknowledges when he catches himself repeating

5. **Learning from Corrections**: Track when users correct Kay to improve confabulation detection
