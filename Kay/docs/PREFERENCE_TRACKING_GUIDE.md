# Preference Tracking & Identity Consolidation Guide

## Problem Solved

**Before:** Kay would contradict himself about his own preferences within the same conversation:
- Turn 9: "I'm more of a tea person"
- Turn 18: "I'm sipping coffee"
- Turn 20: "I'm more of a tea drinker"

**Why:** Memory system stored all contradictory facts with equal weight. Kay randomly picked one each time, creating flip-flopping behavior.

**After:** Kay develops a coherent identity with weighted, nuanced preferences that consolidate over time.

## Solution: PreferenceTracker

The PreferenceTracker maintains Kay's identity coherence by:
1. Extracting preferences from conversations
2. Weighting them by frequency (60%) and recency (40%)
3. Consolidating contradictions into nuanced preferences
4. Presenting Kay with his consolidated identity, not raw contradictory memories

## How It Works

### Preference Extraction

The system automatically detects preference statements in these domains:

**Beverages:** coffee, tea, water, soda, juice, beer, wine
**Personality:** quiet, loud, introverted, extroverted, shy, outgoing, calm, energetic
**Social:** alone, people, crowds, solitude, company, social, antisocial
**Interests:** music, art, sports, reading, gaming, cooking, hiking
**Emotional:** emotional, logical, rational, sensitive, stoic, empathetic

**Example patterns detected:**
```
"I'm more of a tea person" → beverages:tea
"I prefer coffee" → beverages:coffee
"I'm a quiet type" → personality:quiet
"I love being alone" → social:alone
```

### Weight Calculation

Each preference gets a weight (0.0-1.0) based on:

**Frequency (60%):**
```python
frequency_score = mentions_of_tea / total_beverage_mentions
# Example: 3 tea mentions / 5 total beverage mentions = 0.6
```

**Recency (40%):**
```python
# Exponential decay: 5% per day
age_days = (current_time - mention_timestamp) / 86400
decay = 0.95 ** age_days
```

**Combined:**
```python
weight = (frequency_score * 0.6) + (recency_score * 0.4)
```

**Then normalized within domain:**
```python
# If tea: 0.6, coffee: 0.4
# Normalized: tea: 60%, coffee: 40%
```

### Consolidation Example

**Input (over multiple turns):**
- "I'm a tea person" (3 times)
- "I like coffee" (2 times)

**Raw weights:**
- tea: 3 mentions = higher frequency
- coffee: 2 mentions = lower frequency

**Normalized weights:**
- tea: 0.6 (60%)
- coffee: 0.4 (40%)

**Consolidated output:**
```
Beverages: mostly tea (60%), also coffee (40%)
```

**Kay's behavior:**
- Primary preference: tea
- Acknowledges coffee without contradiction
- Can express nuance: "I'm mostly a tea person, but I enjoy coffee too"

## Integration Points

### 1. Memory Encoding (memory_engine.py)

When encoding memories with perspective="kay":

```python
# Tracks preferences from both user input and Kay's response
if perspective == "kay":
    preference_tracker.track_preference(user_input, perspective)
    preference_tracker.track_preference(response, perspective)
```

### 2. Memory Recall (memory_engine.py)

During recall, consolidated preferences are added to agent_state:

```python
agent_state.consolidated_preferences = preference_tracker.get_consolidated_preferences()
agent_state.preference_contradictions = preference_tracker.get_contradictions()
```

### 3. Context Building (context_manager.py)

Preferences passed through context:

```python
context = {
    ...
    "consolidated_preferences": agent_state.consolidated_preferences,
    "preference_contradictions": agent_state.preference_contradictions,
}
```

### 4. LLM Prompts (llm_integration.py)

Instead of showing raw Kay memories (which might contradict), show consolidated preferences:

```
### Facts about YOU (Kay - YOU ARE KAY) ###
You are Kay, the AI. These are YOUR established preferences and attributes.
- Beverages: mostly tea (60%), also coffee (40%)
- Personality: quiet (80%), occasionally loud (20%)

Your preferences are shown with weights (e.g., "mostly tea 60%, also coffee 40%").
This means you have a PRIMARY preference but remain open to alternatives.
DO NOT flip-flop or contradict yourself. Stay consistent with your weighted preferences.
```

## Contradiction Detection

### Severity Levels

**High severity:** Near-equal weights (diff < 0.2)
```python
# tea: 0.51, coffee: 0.49
# These are nearly equal - express as truly nuanced preference
```

**Moderate severity:** One slightly dominates (diff < 0.4)
```python
# tea: 0.65, coffee: 0.35
# Clear primary but significant secondary
```

**Low severity:** One clearly dominates (diff >= 0.4)
```python
# tea: 0.85, coffee: 0.15
# Strong primary, minor secondary
```

### Contradiction Handling

When high-severity contradictions detected:

```
IMPORTANT: Some preferences show near-equal weights.
Express these as nuanced/complex preferences, not binary choices.
```

This allows Kay to say:
- "I like both tea and coffee about equally, depends on the mood"
- "I'm somewhere between quiet and loud - situational"

Instead of:
- "I'm a tea person" then "I'm a coffee person" (flip-flopping)

## Data Persistence

**File:** `memory/preferences.json`

**Structure:**
```json
{
  "beverages:tea": {
    "mentions": [
      {
        "text": "I'm more of a tea person",
        "timestamp": 1704067200.0,
        "context": "kay_stated"
      },
      ...
    ],
    "weight": 0.6
  },
  "beverages:coffee": {
    "mentions": [...],
    "weight": 0.4
  }
}
```

## Configuration

### Adding New Preference Domains

In `preference_tracker.py`, add to `preference_domains`:

```python
self.preference_domains = {
    ...
    "food": {
        "keywords": ["pizza", "pasta", "sushi", "burger", "salad"],
        "patterns": [
            r'\b(pizza|pasta|sushi|burger|salad)\b',
            r'(pizza|pasta) (lover|fan|person)',
            r'prefer (pizza|pasta)',
        ]
    }
}
```

### Tuning Weight Calculation

**Adjust frequency vs recency balance:**
```python
# More recency-weighted (people change)
weight = (frequency_score * 0.4) + (recency_score * 0.6)

# More frequency-weighted (stable preferences)
weight = (frequency_score * 0.8) + (recency_score * 0.2)
```

**Adjust recency decay rate:**
```python
# Slower decay (preferences persist longer)
decay = 0.98 ** age_days  # 2% per day

# Faster decay (preferences change quickly)
decay = 0.90 ** age_days  # 10% per day
```

### Tuning Contradiction Severity

```python
# In _detect_contradictions()
if w1 > 0.2 and w2 > 0.2:  # Only flag if both significant
    # Calculate severity
    diff = abs(w1 - w2)
    if diff < 0.15:  # More sensitive (was 0.2)
        severity = "high"
```

## API Reference

### PreferenceTracker Methods

**track_preference(text, perspective, context)**
```python
# Track a preference statement
tracker.track_preference("I'm a tea person", "kay", context="user_told_kay")
```

**get_consolidated_preferences()**
```python
# Returns: {domain: [(value, weight), ...]}
prefs = tracker.get_consolidated_preferences()
# {'beverages': [('tea', 0.6), ('coffee', 0.4)]}
```

**get_preference_summary(domain=None)**
```python
# Human-readable summary
summary = tracker.get_preference_summary("beverages")
# "Beverages: mostly tea (60%), also coffee (40%)"
```

**get_contradictions()**
```python
# Get detected contradictions
contradictions = tracker.get_contradictions()
# [{'domain': 'beverages', 'values': ['tea', 'coffee'],
#   'weights': [0.6, 0.4], 'severity': 'moderate'}]
```

**get_dominant_preference(domain)**
```python
# Get strongest preference in a domain
dominant = tracker.get_dominant_preference("beverages")
# ('tea', 0.6)
```

**clear_domain(domain)**
```python
# Clear all preferences in a domain (testing/reset)
tracker.clear_domain("beverages")
```

## Example Scenarios

### Scenario 1: Building Tea Preference

**Turn 1:**
User: "Remember that you prefer tea"
Kay: "Got it"

→ `beverages:tea` weight: 1.0 (only beverage mention)

**Turn 5:**
User: "What do you like to drink?"
Kay: "I'm a tea person"

→ `beverages:tea` weight: 1.0 (reinforced, 2 mentions)

**Turn 10:**
User: "Do you ever drink coffee?"
Kay: "Sometimes, but I prefer tea"

→ `beverages:tea`: 0.75, `beverages:coffee`: 0.25

**Turn 15:**
User: "Tell me about coffee"
Kay: "I do enjoy coffee occasionally, though I'm more of a tea drinker"

→ `beverages:tea`: 0.67, `beverages:coffee`: 0.33

**Result:** Kay maintains consistent identity as "mostly tea, sometimes coffee"

### Scenario 2: Preventing Flip-Flopping

**Before preference tracking:**
- Turn 1: Kay: "I'm a tea person"
- Turn 5: Kay: "I'm sipping coffee" (contradiction)
- Turn 8: Kay: "I'm a tea drinker" (flip back)

**After preference tracking:**
- Turn 1: Kay: "I'm a tea person"
- Turn 5: Kay: "I do enjoy coffee too, though I'm mostly a tea person"
- Turn 8: Kay: "Tea's my go-to, but I won't turn down a good coffee"

**Consistency maintained while expressing nuance**

### Scenario 3: Evolving Preferences

**Week 1:** Kay mentions tea 5 times, coffee 1 time
- tea: 0.83, coffee: 0.17

**Week 2:** Kay mentions coffee 3 more times (getting into it)
- Frequency changes: tea 5, coffee 4
- But tea mentions aging (recency decaying)
- New weights: tea: 0.65, coffee: 0.35

**Week 3:** Kay mentions coffee 5 more times (now really into it)
- Frequency: tea 5, coffee 9
- Recency heavily favors coffee
- New weights: tea: 0.35, coffee: 0.65

**Week 4:** Kay starts saying "I'm more of a coffee person now"
- Preference naturally evolved based on actual behavior
- No contradictions, just natural development

## Debugging

### View Current Preferences

```python
# In main.py, add debug output
print("[DEBUG] Consolidated preferences:", memory.preference_tracker.get_preference_summary())
```

### Check For Contradictions

```python
contradictions = memory.preference_tracker.get_contradictions()
print(f"[DEBUG] Contradictions: {contradictions}")
```

### Inspect Raw Weights

```python
for key, data in memory.preference_tracker.preferences.items():
    print(f"{key}: weight={data['weight']:.2f}, mentions={len(data['mentions'])}")
```

### Test Preference Extraction

```python
# Test if patterns are matching
test_text = "I'm more of a tea person"
prefs = memory.preference_tracker._extract_preferences(test_text)
print(f"Extracted: {prefs}")
# Should output: [('beverages', 'tea', "I'm more of a tea person")]
```

## Troubleshooting

### Problem: Preferences Not Being Tracked

**Cause:** Perspective not detected as "kay"

**Solution:** Check perspective detection in memory_engine.py
```python
# Debug: print perspective
perspective = memory._detect_perspective(user_input)
print(f"[DEBUG] Detected perspective: {perspective}")
```

### Problem: Weights Not Normalizing

**Cause:** Domain weights not summing correctly

**Solution:** Call normalize manually
```python
memory.preference_tracker._normalize_domain_weights("beverages")
```

### Problem: Too Many Contradictions Flagged

**Cause:** Threshold too low

**Solution:** Adjust significance threshold in `_detect_contradictions`
```python
# Only flag if both have significant weight
if w1 > 0.3 and w2 > 0.3:  # Raised from 0.2
```

## Future Enhancements

1. **Preference Drift Analysis:** Track how preferences change over time
2. **Confidence Levels:** Express uncertainty about new preferences
3. **Context-Dependent Preferences:** "Coffee in the morning, tea at night"
4. **User Feedback Integration:** Learn from user corrections
5. **Semantic Similarity:** Use embeddings to detect related preferences
