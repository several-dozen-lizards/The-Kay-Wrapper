# Performance Analysis and Optimization Plan

## Date: 2024-12-04

## Executive Summary

Profiling identified three main performance issues:

1. **LLM Response Time**: 2-6 seconds per call (target: 500ms)
2. **Entity Graph Bloat**: 473+ "contradictions" from goal accumulation
3. **Semantic Layer Underutilization**: Only 4-8% of retrieved memories are semantic

---

## Issue 1: LLM Response Time

### Root Cause Analysis

Profiling results from `profile_llm_latency.py`:

| Test | Input Tokens | Output Tokens | Time (ms) | ms/token |
|------|-------------|---------------|-----------|----------|
| Minimal | 20 | 4 | 1,654 | 413.5 |
| Voice Mode | 360 | 44 | 2,287 | 52.0 |
| Cached (creation) | 2,393 | 81 | 2,614 | 32.3 |
| Cached (hit) | 2,391 | 348 | 6,697 | 19.2 |
| Large Output | 30 | 349 | 5,106 | 14.6 |
| Streaming TTFT | - | - | 1,301 | - |

**Key Findings:**

1. **OUTPUT TOKENS ARE THE BOTTLENECK**
   - Generation time scales linearly with output tokens
   - ~15-50ms per output token depending on prompt complexity
   - A 350-token response takes 5-7 seconds regardless of caching

2. **CACHE IS NOT WORKING**
   - `cache_created: 0 tokens` and `cache_hit: 0 tokens`
   - Minimum cacheable length for Haiku 3.5 is **2048 tokens**
   - Our cached content (~2,264 tokens) is split across 2 blocks
   - Each block must independently exceed 2048 tokens to be cached

3. **TIME-TO-FIRST-TOKEN (TTFT) is acceptable**
   - 1,301ms for streaming
   - This means users could see "thinking" or first words within ~1.3s

### Recommendations

#### A. Fix Prompt Caching (CRITICAL)

Current structure (BROKEN):
```
Block 1: instructions (1,331 tokens) + cache_control
Block 2: identity (933 tokens) + cache_control
Block 3: dynamic content (no cache)
```

Neither block exceeds 2048 tokens, so cache is never created.

**FIX**: Combine cached content into ONE block ≥2048 tokens:
```
Block 1: instructions + identity (2,264 tokens) + cache_control
Block 2: dynamic content (no cache)
```

**Expected Impact**:
- First call: Same speed
- Subsequent calls: 10-50% faster (90% token cost reduction)

#### B. Reduce Output Length for Voice Mode

Current: `max_tokens=400` generates up to 400 tokens (8 seconds)

**FIX**: `max_tokens=150` for voice mode (3 seconds max)
- 2-4 sentences = 40-80 tokens typically
- Leave headroom for longer responses when needed

**Expected Impact**: 30-50% latency reduction in voice mode

#### C. Use Streaming + Sentence-Level TTS

Instead of waiting for full response:
1. Stream LLM response
2. Buffer until sentence boundary (., !, ?)
3. Send sentence to TTS immediately
4. Play audio while next sentence generates

**Expected Impact**:
- Perceived latency drops to TTFT (~1.3s)
- User hears Kay speaking within 2 seconds

#### D. Add "Thinking" Indicator

During LLM generation:
- Visual: Animated dots or "Kay is thinking..."
- Audio: Subtle ambient sound (if voice mode)

**Expected Impact**: Better UX perception (doesn't reduce actual latency)

---

## Issue 2: Entity Graph Contradiction Bloat

### Root Cause Analysis

From test output:
```
[ENTITY GRAPH] NEW CONTRADICTIONS DETECTED (473 new, 473 total active)
  - Re.goal: {"import things to Kay's memory": [...], "fix Kay": [...], ...}
  - Re.goal_progression: {"making progress": [...], "stuck": [...], ...}
  - Re.planned_action: {...}
```

**Problem**: Goals are being tracked as "attributes" that create contradictions when they change, but goals are SUPPOSED to change. This isn't a contradiction—it's normal goal progression.

### Recommendations

#### A. Exempt Transient Attributes from Contradiction Tracking

Goals, moods, and status attributes should NOT create contradictions:

```python
TRANSIENT_ATTRIBUTES = [
    "goal", "planned_action", "goal_progression",
    "current_mood", "current_activity", "status",
    "intention", "desire", "want"
]

def _determine_contradiction_severity(self, attribute, unique_values):
    # Transient attributes are never contradictions
    if any(trans in attribute.lower() for trans in TRANSIENT_ATTRIBUTES):
        return "transient"  # New severity level = ignore
    ...
```

**Expected Impact**: ~90% reduction in contradiction count

#### B. Implement Goal Archival

Goals older than 7 days should be archived, not deleted:
- Mark as "historical"
- Don't count in active contradictions
- Still available for query ("what were Re's past goals?")

```python
def archive_old_goals(self, max_age_days: int = 7):
    """Move old goals to archive, keeping them queryable but out of contradiction tracking."""
```

#### C. Goal Completion Detection

When a goal reappears with "completed", "done", or "finished", mark previous versions as resolved:

```python
COMPLETION_MARKERS = ["completed", "done", "finished", "resolved", "fixed"]
```

---

## Issue 3: Semantic Layer Underutilization

### Root Cause Analysis

From test output:
```
[SEMANTIC USAGE] Memory composition:
  - Semantic layer: 4 (9.5%)
  - Episodic layer: 17 (40.5%)
  - Working layer: 19 (45.2%)
[SEMANTIC USAGE WARNING] No semantic facts retrieved
```

**Problem**: Semantic facts ARE being stored, but the retrieval system isn't surfacing them. This creates wasted storage and processing with no benefit.

### Potential Causes

1. **Scoring bias**: Multi-factor retrieval may weight episodic/working too heavily
2. **Relevance floor**: Semantic facts may be filtered out by keyword matching
3. **Layer assignment**: Facts may be stored in wrong layer

### Recommendations

#### A. Audit Retrieval Weights

Current weights in `retrieve_unified_importance()`:
```python
emotional_weight = 0.4   # 40%
semantic_weight = 0.25   # 25% - keyword overlap
importance_weight = 0.20 # 20%
recency_weight = 0.10    # 10%
entity_weight = 0.05     # 5%
```

**Investigation needed**: Are semantic layer memories getting lower scores because:
- They lack emotional associations?
- They're older (lower recency)?
- They have fewer entity matches?

#### B. Add Diagnostic Mode

Create `DEBUG_SEMANTIC=true` mode that:
- Logs every semantic fact considered
- Shows why it was/wasn't selected
- Tracks semantic retrieval rate over time

#### C. Consider Simplification

If semantic layer continues to underperform, consider:
- Merging into long-term (already done in two-tier refactor)
- Removing distinction and treating all facts equally
- Adding semantic boost for identity-related queries

---

## Implementation Priority

1. **HIGH**: Fix prompt caching (Issue 1A) - Immediate cost/latency benefit
2. **HIGH**: Reduce voice mode max_tokens (Issue 1B) - Quick win
3. **HIGH**: Exempt transient attributes (Issue 2A) - Fixes contradiction explosion
4. **MEDIUM**: Implement streaming TTS (Issue 1C) - Significant UX improvement
5. **MEDIUM**: Goal archival (Issue 2B) - Prevents future bloat
6. **LOW**: Semantic layer audit (Issue 3) - Requires investigation first

---

## Files to Modify

1. `integrations/llm_integration.py` - Cache fix, max_tokens adjustment
2. `engines/entity_graph.py` - Transient attributes, archival
3. `voice_handler.py` / `voice_ui_integration.py` - Streaming TTS
4. `engines/memory_engine.py` - Semantic retrieval audit

---

## Implementation Status (Updated 2024-12-04)

### ✅ COMPLETED:

1. **Prompt Caching Fix** (`llm_integration.py`)
   - Combined cached blocks into single ≥2048 token block
   - Cache is now eligible for Haiku 3.5 (2,265 tokens)
   - Added cache debug logging on first call

2. **Voice Mode max_tokens** (`llm_integration.py`)
   - Reduced from 400 to 200 tokens
   - Expected 50% reduction in voice response latency
   - Applied to both sync and streaming modes

3. **Transient Attributes** (`entity_graph.py`)
   - Added "transient" severity level for goals, moods, intentions
   - Transient attributes are now SKIPPED in contradiction detection
   - Tested: Goals correctly excluded from contradictions

4. **Memory Layer Tracking** (`memory_engine.py`)
   - Updated tracking to use two-tier labels (working + long_term)
   - Fixed incorrect "semantic" layer references
   - Added extracted fact vs conversation turn breakdown

### 🔄 ALREADY IMPLEMENTED (Found during audit):

1. **Streaming TTS** (`voice_engine.py`, `kay_ui.py`)
   - Sentence-by-sentence TTS already implemented
   - LLM streaming response already implemented
   - "Thinking..." indicator already in UI state machine

2. **Voice State Machine** (`kay_ui.py`)
   - States: idle, listening, recording, transcribing, processing, speaking, error
   - "💭 Thinking..." displayed during LLM processing
   - Proper state transitions in place

---

## Success Metrics

- Voice mode latency < 2.5s (from 3-6s) → **EXPECTED: Yes (max_tokens reduced 50%)**
- Entity graph contradictions < 50 (from 473) → **EXPECTED: Yes (transient fix)**
- Semantic retrieval rate > 15% (from 4-8%) → **UPDATED: Now tracks by memory type**
- Prompt cache hit rate > 80% → **EXPECTED: Yes (cache now eligible)**

---

## Voice Latency Optimization (Added 2024-12-04)

### Problem
Voice mode had 15-25 second roundtrip latency. Environmental detection was taking ~3 seconds per exchange.

### Solution: Environmental Detection Modes

Added three modes for environmental sound detection:

| Mode | Latency | Detection Method | Use Case |
|------|---------|-----------------|----------|
| `off` | +0s | None | Fastest response, no sound detection |
| `light` | +0.3s | Spectral only | Good balance, catches obvious sounds |
| `full` | +2-3s | Hybrid (PANNs + spectral) | Best accuracy, slower |

### Changes Made

1. **Config** (`kay_ui.py:3964-3974`)
   - Added `environmental_mode` to voice config
   - Default: `"light"` for better latency

2. **Voice Engine** (`voice_engine.py:448-473, 1311-1350`)
   - Added `environmental_mode` attribute
   - Routes detection to appropriate method based on mode
   - `off`: Skips detection entirely
   - `light`: Calls `detect_light()` (spectral only)
   - `full`: Calls `detect_sounds_with_speech_filter()` (hybrid)

3. **Environmental Detector** (`environmental_sound_detector.py:296-338`)
   - Added `detect_light()` method for fast spectral-only detection
   - Higher confidence threshold (85%) to reduce false positives without PANNs

4. **PANNs Optimization** (`environmental_sound_detector.py:815-843`)
   - Increased onset gap filter (0.5s → 0.8s)
   - Reduced max onsets (20 → 10)
   - Sort by amplitude to prioritize strongest sounds

5. **UI Controls** (`kay_ui.py:2569-2596`)
   - Added "Env Detection" dropdown in voice settings
   - Shows latency estimate for each mode

### Expected Performance

| Mode | Total Voice Roundtrip |
|------|----------------------|
| `off` | ~10-12s |
| `light` | ~12-15s |
| `full` | ~15-18s (optimized from 20-25s) |

---

## Remaining Work (Future)

1. **Goal Archival**: Auto-archive old goals after 7 days
2. **Goal Completion Detection**: Mark resolved when "completed" mentioned
3. **Production Cache Verification**: Verify cache hits in production logs
4. **Streaming TTS Verification**: Ensure sentences queue during LLM streaming
