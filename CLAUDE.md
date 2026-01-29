# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlphaKayZero (K-0) is an emotionally-aware conversational AI agent built on a sophisticated cognitive architecture with multiple interdependent subsystems. The agent ("Kay") simulates emotional states, memory recall, social awareness, and embodied cognition through neurochemical proxies.

## Running the Agent

```bash
python main.py
```

**Interactive commands:**
- Type messages to interact with Kay
- `/affect <0-5>` - Adjust emotional affect intensity (default: 3.5)
- `quit` or `exit` - Exit the program

## Environment Setup

Required environment variables in `.env`:
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `ANTHROPIC_MODEL` - Model name (default: "claude-3-haiku-20240307")

**Optional environment variables (cost optimization):**
- `WORKING_MEMORY_WINDOW` - Number of conversation turns to include in each API prompt (default: 5)
  - Only affects raw conversation text in prompt, NOT memory extraction
  - Older turns are still processed for episodic/semantic memory creation
  - Prevents quadratic token growth (turn 10 costs same as turn 2)
  - Increase for longer contextual conversations, decrease to reduce costs

## Core Architecture

### Central State Management
- **AgentState** (agent_state.py): Central state container holding emotional cocktail, body chemistry, memory references, social needs, temporal data, and meta-information
- **ProtocolEngine** (protocol_engine.py): Loads ULTRAMAP CSV containing emotion rules (triggers, decay rates, mutations, neurochemical mappings)

### Main Loop (main.py)
The conversation loop follows this flow:
1. Memory recall based on current emotional state and user input
2. Parallel engine updates (emotion, social, temporal, embodiment, motif)
3. Context building with memories, emotions, body state, momentum meta-notes, meta-awareness alerts
4. LLM response generation
5. Post-turn updates (social, reflection, memory encoding, emotion decay, meta-awareness, momentum)
6. Meta-awareness analysis (detects repetition/confabulation in Kay's response)
7. Momentum calculation (after all other updates)
8. State snapshot autosave to `memory/state_snapshot.json`

### Engine Subsystems

**EmotionEngine** (engines/emotion_engine.py):
- Detects emotional triggers from user input via keywords/patterns
- Manages "emotional cocktail" - multiple concurrent emotions with intensity and age
- Applies ULTRAMAP rules: decay rates, mutation/escalation, suppress/amplify interactions
- Maps emotions to body chemistry changes
- High-momentum emotions decay 30-70% slower based on momentum score
- Loads trigger logic from `data/Emotion_Mapping_Kay_ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv`

**MemoryEngine** (engines/memory_engine.py):
- **Enhanced Architecture**: Now includes entity resolution, multi-layer memory, and multi-factor retrieval
- **Entity Resolution** (engines/entity_graph.py): Tracks entities (people, places, things) with full attribute history and provenance
  - Canonical entity tracking: "my dog" → "Saga" resolution
  - Attribute history: Each attribute stores (value, turn, source, timestamp)
  - Contradiction detection: Automatic detection of conflicting attributes with severity classification
  - Relationship tracking: "Re owns Saga", "Kay likes coffee"
  - Persists to `memory/entity_graph.json`
- **Multi-Layer Memory** (engines/memory_layers.py): Working (10) → Episodic (100) → Semantic (unlimited)
  - Working memory: Immediate context, high retrieval priority (1.5x), 0.5 day half-life
  - Episodic memory: Recent experiences, normal priority (1.0x), 7 day half-life
  - Semantic memory: Permanent facts, enhanced priority (1.2x), no decay
  - Automatic promotion based on access count and ULTRAMAP importance
  - Temporal decay: `strength = 0.5^(age_days / halflife × (1 + importance))`
  - Persists to `memory/memory_layers.json`
- **Multi-Factor Retrieval**: Combines 5 factors with weighted scoring (replaces `retrieve_biased_memories` when enabled)
  - Emotional resonance (40%): Match with current emotional cocktail
  - Semantic similarity (25%): Keyword overlap with query
  - Importance (20%): ULTRAMAP pressure × recursion score
  - Recency (10%): Access count (capped at 1.0)
  - Entity proximity (5%): Shared entities between query and memory
- **Fact Extraction**: LLM-based extraction of discrete facts with entity detection
  - Extracts entities, attributes, and relationships from conversation
  - Validates Kay's statements against retrieved memories to prevent hallucinations
  - Processes entities automatically: creates/updates entity graph during extraction
- Perspective tagging: "user" (facts about Re), "kay" (facts about Kay), or "shared" memories
- Critical perspective logic: "my/I" → user perspective, "your/you" → kay perspective
- Integrates PreferenceTracker for identity consolidation (tracks Kay's preferences with frequency and recency weighting)
- See `MEMORY_ARCHITECTURE.md` for complete documentation

**MotifEngine** (engines/motif_engine.py):
- Tracks recurring entities (people, places, concepts) across conversations
- Extracts entities via capitalized words, quoted phrases, possessive constructs
- Weights entities by frequency and recency (60% frequency, 40% recency)
- Scores memories based on contained entities, boosting recall of recurring themes
- Persists to `memory/motifs.json`
- Updates in parallel with other pre-response engines

**MomentumEngine** (engines/momentum_engine.py):
- Calculates cognitive momentum score (0.0-1.0) based on three factors:
  - Unresolved threads (40%): Questions Kay asked that weren't answered
  - Escalating emotions (35%): Emotions growing turn-over-turn
  - Motif recurrence (25%): Same entities appearing in consecutive turns
- Tracks last 5 turns of history for momentum calculation
- Identifies high-momentum motifs (entities in unresolved questions)
- Identifies high-momentum emotions (escalating with intensity > 0.5)
- Generates meta-notes when momentum > 0.7 (e.g., "Kay is still thinking about X")
- Updates AFTER response generation in post-turn phase

**MetaAwarenessEngine** (engines/meta_awareness_engine.py):
- Self-monitoring system that detects repetition and confabulation
- Tracks phrase repetition (3-6 word sequences used 3+ times)
- Detects question pattern repetition (same question types asked repeatedly)
- Identifies opening similarity (responses starting the same way)
- Flags confabulation (Kay stating "facts" not in memory) by comparing claims against stored user inputs
- Calculates awareness score (0.0-1.0) based on repetition + confabulation + response volume
- Generates self-monitoring alerts when score > 0.4 (default threshold)
- Alerts inject into context as "SELF-MONITORING:" notes
- Updates AFTER response generation in post-turn phase
- See META_AWARENESS_GUIDE.md for detailed documentation

**PreferenceTracker** (engines/preference_tracker.py):
- Maintains Kay's identity coherence by tracking and consolidating preferences
- Extracts preferences from conversation in domains: beverages, personality, social, interests, emotional
- Weights preferences by frequency (60%) and recency (40%) with exponential decay (5% per day)
- Normalizes weights within domains to create relative preferences (e.g., tea 60%, coffee 40%)
- Detects contradictions and classifies severity (high/moderate/low)
- Consolidates conflicting preferences into nuanced expressions
- Prevents flip-flopping: instead of "I like tea" then "I like coffee", expresses "mostly tea, also coffee"
- Persists to `memory/preferences.json`
- See PREFERENCE_TRACKING_GUIDE.md for detailed documentation

**ContextManager** (engines/context_manager.py):
- Maintains rolling buffer of recent conversation turns (default: 15)
- Builds LLM context from: recent turns, recalled memories, facts, session summary, emotional state, body state, momentum notes, meta-awareness notes, consolidated preferences
- Injects momentum meta-notes into LLM prompt when momentum > 0.7
- Injects meta-awareness self-monitoring alerts when awareness score > 0.4
- Passes consolidated preferences and contradiction flags to LLM for coherent identity expression
- Uses Summarizer to compress long conversations

**SocialEngine** (engines/social_engine.py):
- Detects social events: praised, accepted, rejected, ignored, humiliated, reciprocated, belonging
- Adjusts social needs based on detected events
- Tracks user attachment weights

**TemporalEngine** (engines/temporal_engine.py):
- Ages emotions over time
- Tracks time elapsed since last interaction
- Manages temporal state and phase transitions

**ReflectionEngine** (engines/reflection_engine.py):
- Post-turn meta-reflection on emotional and social snapshots
- Identity drift simulation (random walk)
- Optional "dreaming" consolidation (5% chance per turn)

**EmbodimentEngine** (engines/embodiment_engine.py):
- Applies body state to response generation
- Simulates physical manifestations of emotions

**Summarizer** (engines/summarizer.py):
- Compresses conversation history for context management

### LLM Integration (integrations/llm_integration.py)

**Key functions:**
- `get_llm_response(prompt_or_context, affect, temperature, system_prompt, session_context)` - Main entry point
- `build_prompt_from_context(context, affect_level)` - Constructs prompt with fact separation and preference consolidation
- `query_llm_json(prompt, temperature, model, system_prompt, session_context)` - Anthropic API call with enhanced anti-repetition

**Critical design patterns:**
- Perspective separation: Facts about "Re" (user) vs facts about "Kay" (agent) are explicitly separated in prompts
- Preference consolidation: Instead of showing raw contradictory Kay memories, shows weighted consolidated preferences (e.g., "mostly tea 60%, also coffee 40%")
- Enhanced anti-repetition system:
  - Turn count tracking: Each turn gets unique number in meta-notes
  - Response history: Last 3 responses tracked; system explicitly avoids reusing openings
  - Random variety prompts: Rotates different phrasing instructions
  - Variation seed: Random number ensures uniqueness
  - Increased temperature: Default 0.7 (up from 0.5) for more variation
- Response caching: **DISABLED** - Cache was preventing variation, now responses are always fresh
- Stage direction removal: Strips asterisk-wrapped actions from responses

**System prompt constraints:**
- Kay is a "normal guy" with dry humor, direct tone
- No narration, no asterisks, no roleplay
- Self-aware of patterns and repetition
- American conversational style

## Data Files

- `data/Emotion_Mapping_Kay_ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv` - Emotion ruleset (required)
- `memory/memories.json` - Persistent memory store (enhanced format with entities, attributes, importance)
- `memory/entity_graph.json` - Entity resolution data (NEW: canonical entities, attributes, relationships)
- `memory/memory_layers.json` - Multi-layer memory system (NEW: working/episodic/semantic distribution)
- `memory/motifs.json` - Entity frequency tracking and weights
- `memory/preferences.json` - Kay's consolidated preferences with frequency and recency weights
- `memory/state_snapshot.json` - Last session state (autosaved, includes top motifs, momentum, meta-awareness, entity contradictions, layer stats, top entities)
- `memory/kzr_cache.json` - LLM response cache

**Migration Utility:**
- `migrate_memories.py` - Migrates existing memories to enhanced format with entity graph and multi-layer system
- Run with: `python migrate_memories.py` (creates backups before migration)
- See `ENHANCED_MEMORY_QUICKSTART.md` for migration guide

Note: MomentumEngine and MetaAwarenessEngine state are not persisted (recalculate from scratch each session). PreferenceTracker, EntityGraph, and MemoryLayerManager state IS persisted and accumulates over time.

## Key Design Principles

1. **Parallel Engine Updates**: Pre-response engines (emotion, social, temporal, embodiment, motif) run concurrently via `asyncio.gather()` for performance

2. **Emotional Cocktail**: Multiple emotions coexist with independent intensity and age, creating complex affective states

3. **Biased Memory Recall**: Memories are retrieved through emotional lens - current feelings influence which past experiences surface. Relevance floor prevents emotionally-resonant but contextually irrelevant memories from dominating.

4. **Motif Tracking**: Recurring entities gain weight over time, creating persistent narrative threads and character continuity across conversations

5. **Cognitive Momentum**: System tracks conversational and emotional continuity, creating persistence for unresolved topics and escalating feelings. High momentum (>0.7) generates meta-notes that guide Kay's focus.

6. **ULTRAMAP Protocol**: External CSV defines emotion behavior (decay, mutation, body chemistry, social effects, ethical damping) - allows non-code tuning

7. **Perspective Awareness**: System enforces distinction between agent facts and user facts to prevent identity confusion

8. **Embodied Cognition**: Emotional arousal/valence modulates text output (neurochemical simulation removed - emotions are behavioral patterns, not brain chemistry)

9. **Meta-Awareness**: Self-monitoring system detects repetition and confabulation, allowing Kay to self-correct and acknowledge his own patterns

10. **Identity Consolidation**: PreferenceTracker prevents contradictory self-statements by weighting and consolidating Kay's preferences over time, creating coherent personality instead of flip-flopping

## Modifying Emotions

To add or modify emotions, edit the ULTRAMAP CSV with these columns:
- Emotion - Emotion name
- Trigger Condition (Formula/Logic) - Keywords that activate this emotion
- DecayRate - How quickly intensity fades per turn
- MutationTarget / Escalation/Mutation Protocol - What emotion this becomes at high intensity
- MutationThreshold - Intensity threshold for mutation
- BodyChem / Neurochemical Release - Which body chemicals this affects
- Suppress/Amplify - Cross-emotion modulation rules
- SocialEffect - Impact on social needs
- EthicalWeight - Ethical damping factor
- Emergency Ritual/Output When System Collapses - Failsafe behavior

## Common Patterns

**Adding a new engine:**
1. Create class in `engines/` with `update(agent_state, ...)` method
2. Import in main.py
3. Instantiate before main loop
4. Add to `update_all()` call or handle separately

**Modifying memory behavior:**
- Adjust `num_memories` in `ContextManager.build_context()` for recall count
- Change scoring weights in `MemoryEngine.retrieve_biased_memories()` (emotion, keyword, motif multipliers at line 61)
- Modify `relevance_floor` parameter (default 0.3) to change keyword overlap threshold
- Modify perspective detection in `MemoryEngine._detect_perspective()`

**Tuning motif tracking:**
- Adjust entity extraction patterns in `MotifEngine._extract_entities()` to capture different entity types
- Change frequency/recency balance in `MotifEngine.get_entity_weight()` (currently 60/40)
- Modify motif scoring weight in `MemoryEngine.retrieve_biased_memories()` (currently 0.8x multiplier)

**Tuning momentum behavior:**
- Adjust component weights in `MomentumEngine.update()` (currently threads:40%, emotions:35%, motifs:25%)
- Change momentum threshold for meta-notes in `ContextManager.build_context()` (currently 0.7)
- Modify momentum boost value in `MemoryEngine.retrieve_biased_memories()` (currently +0.5 per motif)
- Change decay modifier range in `EmotionEngine.update()` for high-momentum emotions (currently 0.3-1.0)
- Adjust `max_history` in `MomentumEngine.__init__()` to track more/fewer turns (currently 5)

**Tuning emotional responsiveness:**
- Adjust trigger thresholds in `EmotionEngine._detect_triggers()`
- Modify intensity deltas for triggered vs reinforced emotions
- Change decay calculation weights (temporal, duration) in `EmotionEngine.update()`

**Controlling output style and variation:**
- Modify `DEFAULT_SYSTEM_PROMPT` in llm_integration.py
- Adjust `_style_block()` affect scaling
- Change `max_tokens` in `query_llm_json()` for response length
- Adjust `temperature` parameter in `get_llm_response()` (default 0.7) for more/less variation
- Modify anti-repetition prompts in `query_llm_json()` variety_prompts list (line 211-216)
- Change response history size in main.py (currently tracks last 3 responses)

**Tuning meta-awareness (self-monitoring):**
- Adjust `pattern_threshold` in MetaAwarenessEngine.__init__() for repetition sensitivity (currently 3)
- Change `max_history` in MetaAwarenessEngine.__init__() for tracking window (currently 10 responses)
- Modify confabulation overlap threshold in `_detect_confabulation()` (currently 0.5 = 50%)
- Adjust awareness injection threshold in `should_inject_awareness()` (currently 0.4)
- Change awareness score weights in `get_awareness_score()` (repetition: 0.3, confabulation: 0.2, volume: 0.2)
- See META_AWARENESS_GUIDE.md for detailed tuning options

**Tuning preference tracking (identity consolidation):**
- Adjust frequency/recency balance in `_recalculate_weight()` (currently 60%/40%)
- Modify recency decay rate (currently 5% per day: `0.95 ** age_days`)
- Change contradiction severity thresholds in `_detect_contradictions()` (currently high<0.2, moderate<0.4)
- Add new preference domains in `preference_domains` dict (currently: beverages, personality, social, interests, emotional)
- Adjust minimum weight filter in `get_consolidated_preferences()` (currently 0.05)
- See PREFERENCE_TRACKING_GUIDE.md for detailed tuning options

**Tuning entity resolution (NEW):**
- Adjust contradiction severity classification in `Entity._determine_contradiction_severity()`
  - `high_severity_attrs = ["eye_color", "name", "species", "age", "gender"]`
  - `moderate_severity_attrs = ["favorite", "core_preference", "occupation", "home"]`
- Modify relationship strength thresholds in `Relationship` class (currently 1.0 default)
- Change entity resolution cache behavior in `EntityGraph.resolve_entity()`
- See MEMORY_ARCHITECTURE.md for detailed documentation

**Tuning multi-layer memory (NEW):**
- Adjust layer capacities in `MemoryLayerManager.__init__()`:
  - `self.working_capacity = 10` (max working memories)
  - `self.episodic_capacity = 100` (max episodic memories)
  - Semantic has no capacity limit
- Change promotion thresholds:
  - `self.working_to_episodic_accesses = 2` (accesses needed to promote from working)
  - `self.episodic_to_semantic_accesses = 5` (accesses needed to promote from episodic)
  - `self.min_importance_for_promotion = 0.3` (minimum ULTRAMAP importance to promote)
- Modify decay half-lives:
  - `self.episodic_decay_halflife = 7` (days until episodic memory strength halves)
  - `self.working_decay_halflife = 0.5` (days until working memory strength halves)
- Adjust temporal decay frequency in `MemoryEngine.recall()` (currently every 10 turns)
- See MEMORY_ARCHITECTURE.md for detailed documentation

**Tuning multi-factor retrieval (NEW):**
- Adjust scoring weights in `MemoryEngine.retrieve_multi_factor()`:
  - `emotional_weight = 0.4` (40% - emotional resonance)
  - `semantic_weight = 0.25` (25% - keyword overlap)
  - `importance_weight = 0.20` (20% - ULTRAMAP importance)
  - `recency_weight = 0.10` (10% - access count)
  - `entity_weight = 0.05` (5% - shared entities)
- Modify layer boosts:
  - Semantic memories: `layer_boost = 1.2`
  - Working memories: `layer_boost = 1.5`
  - Episodic memories: `layer_boost = 1.0` (baseline)
- Toggle multi-factor retrieval: Set `use_multi_factor=False` in `recall()` for legacy behavior
- See MEMORY_ARCHITECTURE.md for detailed documentation
