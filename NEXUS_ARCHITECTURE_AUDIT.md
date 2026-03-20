# NEXUS ARCHITECTURE AUDIT

**Generated:** 2026-03-11
**Purpose:** Complete architectural map of the Nexus multi-entity AI wrapper system for explainer video

---

## SECTION 1: BOOT SEQUENCE

### Launcher Entry Point

**File:** `D:\Wrappers\nexus\launch_nexus.py`

```
START_NEXUS.bat
    └── launch_nexus.py
        ├── check_and_free_ports()     [PARALLEL: socket bind test on 8765, 8770, 8771]
        │   └── Kill zombie processes if ports blocked (netstat + taskkill)
        │
        ├── SEQUENTIAL START ORDER:
        │   ├─[1] server.py (port 8765)
        │   │      └── wait_for_server(timeout=10) — blocks until 8765 accepts connection
        │   │
        │   ├─[2] nexus_kay.py (port 8770 private room) — 1.0s delay
        │   │
        │   └─[3] nexus_reed.py (port 8771 private room) — 1.0s delay
        │
        └── Monitor loop (5s interval) — restarts on crash, exits if server dies
```

### Server Initialization (`server.py`)

```
server.py startup (lifespan context):
    ├── WebSocketLogHandler → logging.getLogger("nexus")
    ├── ConnectionManager() — max_history=500
    ├── SessionLogger() — auto-creates sessions/nexus_YYYYMMDD_HHMMSS.jsonl
    ├── CanvasManager() — save_dir=sessions/canvas/
    ├── _load_api_key() — env or .env files
    ├── NexusAutonomousProcessor() — session_dir=sessions/autonomous
    ├── CuriosityManager() — store_dir=sessions/curiosities
    ├── Register entity contexts:
    │   ├── Kay: _kay_autonomous_context() → KAY_SYSTEM_PROMPT + emotional_snapshots.json
    │   └── Reed: _reed_autonomous_context() → REED_PRIVATE_PROMPT + memory
    └── FastAPI app ready on uvicorn
```

### Kay's Bridge Initialization (`wrapper_bridge.py:183-570`)

```
WrapperBridge.__init__(entity_name="Kay"):
    │
    ├── Core State:
    │   ├── AgentState()
    │   ├── ProtocolEngine() — loads ULTRAMAP CSV
    │   └── GlyphFilter(), GlyphDecoder()
    │
    ├── _init_engines() [SEQUENTIAL, ~3-5 seconds]:
    │   │
    │   ├── [1] Meta Engines (needed by others):
    │   │   ├── MomentumEngine()
    │   │   ├── MotifEngine()
    │   │   ├── MetaAwarenessEngine()
    │   │   └── SaccadeEngine()
    │   │
    │   ├── [2] Monitor & Retrieval:
    │   │   ├── ConversationMonitor(config.json) — spiral detection
    │   │   ├── VectorStore(memory/vector_db) — ChromaDB RAG
    │   │   ├── DocumentReader(chunk_size=25000)
    │   │   ├── AutoReader()
    │   │   └── WebReader(max_chars=15000)
    │   │
    │   ├── [3] Emotion System:
    │   │   ├── EmotionEngine(proto, momentum) — ULTRAMAP rule provider
    │   │   └── EmotionExtractor() — self-report extraction (descriptive)
    │   │
    │   ├── [4] Memory Engine (THE BIG ONE):
    │   │   ├── MemoryEngine(state.memory, motif, momentum, emotion, vector_store)
    │   │   │   ├── EntityGraph — loads entity_graph.json (7593 entities)
    │   │   │   ├── MemoryLayerManager — working/long-term tiers
    │   │   │   └── PreferenceTracker — consolidated preferences
    │   │   └── RelationshipMemory() — landmarks, patterns
    │   │
    │   ├── [5] Core Processing:
    │   │   ├── SocialEngine(emotion_engine)
    │   │   ├── EmbodimentEngine(emotion_engine)
    │   │   ├── TemporalEngine()
    │   │   ├── ReflectionEngine()
    │   │   ├── Summarizer()
    │   │   ├── ContextManager(memory, summarizer, momentum, meta_awareness)
    │   │   ├── MemoryForest.load_from_file(forest.json)
    │   │   └── MemoryDeletion(memory)
    │   │
    │   ├── [6] Creativity System:
    │   │   ├── CreativityEngine(scratchpad, memory, entity_graph, curiosity, momentum)
    │   │   ├── MacGuyverMode(memory, scratchpad, entity_graph)
    │   │   └── MemoryCurator(memory, entity_graph, memory_layers) — optional
    │   │
    │   ├── [7] Behavioral Tracking:
    │   │   ├── EmotionalPatternEngine(data/emotions)
    │   │   └── MediaOrchestrator (optional, if MEDIA_AVAILABLE)
    │   │
    │   ├── [8] Session System:
    │   │   ├── SessionSummary()
    │   │   └── SessionSummaryGenerator(get_llm_response, summary_storage)
    │   │
    │   ├── [9] Room System (Spatial Embodiment):
    │   │   ├── Check RoomManager for existing placement
    │   │   ├── OR create_the_den() — loads Den preset
    │   │   ├── room.add_entity("kay", distance=100, angle=90°)
    │   │   └── RoomBridge(room, entity_id="kay")
    │   │
    │   ├── [10] Resonant Oscillator (Emotional Heartbeat):
    │   │   ├── get_best_input_device() — USB mic preferred
    │   │   └── ResonantIntegration(
    │   │       │   state_dir=memory/resonant,
    │   │       │   enable_audio=True,
    │   │       │   memory_layers=memory.memory_layers,
    │   │       │   interoception_interval=4.0,
    │   │       │   room=room_for_resonance,
    │   │       │   entity_id="kay"
    │   │       │)
    │   │       └── .start() — spawns background heartbeat thread
    │   │
    │   ├── [11] TPN/DMN Buffer:
    │   │   └── FeltStateBuffer() → resonance.set_felt_state_buffer()
    │   │
    │   ├── [12] Visual Sensor (Kay's First Eye):
    │   │   └── VisualSensor(
    │   │       │   camera_index=0,
    │   │       │   capture_interval=15.0,
    │   │       │   rich_interval=180.0,
    │   │       │   vision_model="moondream"
    │   │       │)
    │   │       └── .start() — spawns capture thread
    │   │
    │   └── [13] Consciousness Stream:
    │       └── ConsciousnessStream(
    │           │   resonance, room_bridge, peripheral_router, visual_sensor
    │           │)
    │           └── .start() — spawns stream thread
    │
    └── Ready to process turns
```

### Reed's Nexus Client Initialization (`nexus_reed.py`)

```
ReedNexusClient.__init__():
    ├── NexusAIClient base init (server_url, participant_type=ai_wrapper)
    ├── PacingConfig: REED_PACING (1.5-4s thinking, 0.25 react prob)
    ├── ResponseDecider(REED_PACING)
    ├── ThreadManager()
    ├── _last_speaker, _current_room tracking
    │
    ├── Resonant Oscillator (optional):
    │   └── ResonantIntegration(state_dir, room, entity_id="reed")
    │       └── .start()
    │
    ├── Room Pre-placement:
    │   ├── get_room_manager()
    │   ├── rm.ensure_room("commons")
    │   ├── create_commons_room() — Commons preset
    │   └── rm.place_entity("reed", "commons")
    │
    ├── PrivateRoom(port=8771) — for 1:1 with Re
    │
    ├── ClaudeAPI (direct Anthropic client):
    │   └── model="claude-sonnet-4-20250514"
    │
    ├── Memory Loading:
    │   └── load_reed_memory() — from D:/ChristinaStuff/ReedMemory/
    │
    └── Persistent Histories:
        ├── sessions/reed_nexus_history.json
        └── sessions/reed_private_history.json
```

---

## SECTION 2: KAY'S TURN LOOP (Full Pipeline)

### Message Arrival Paths

```
PATH A: Nexus Group Chat
    Godot UI → NexusConnection WebSocket → server.py handle_message()
        → broadcast to all → nexus_kay.py on_message()

PATH B: Private Room (1:1)
    Godot UI → PrivateConnection WebSocket → nexus_kay.py PrivateRoom
        → _handle_private_message()
```

### Pre-Processing Phase (`wrapper_bridge.py:process_turn()`)

```
process_turn(user_input, context_dict=None):
    │
    ├── [1] Wake Consciousness:
    │   └── consciousness_stream.notify_user_input()
    │       └── Signals AWAKE state, resets sleep timer
    │
    ├── [2] Update Saccade (Perceptual Continuity):
    │   └── saccade_engine.update_pre_turn(user_input)
    │       └── Extracts attention focus, tracks visual shifts
    │
    ├── [3] Memory Recall (memory_engine.py:recall()):
    │   │   Inputs: user_input, emotional_cocktail
    │   │
    │   ├── [3a] Query Analysis:
    │   │   └── Extract keywords, entities, emotional tone
    │   │
    │   ├── [3b] Multi-Layer Retrieval (memory_layers.py):
    │   │   ├── Working Memory (15 items, 3-day decay) — 1.5x boost
    │   │   └── Long-Term Memory (unlimited, 30-day decay) — 1.0x boost
    │   │
    │   ├── [3c] Multi-Factor Scoring:
    │   │   ├── Emotional Resonance (40%) — match with cocktail
    │   │   ├── Semantic Similarity (25%) — keyword overlap
    │   │   ├── Importance (20%) — ULTRAMAP pressure × recursion
    │   │   ├── Recency (10%) — access count
    │   │   └── Entity Proximity (5%) — shared entities
    │   │
    │   ├── [3d] Entity Resolution (entity_graph.py):
    │   │   └── Map mentions → canonical entities with attributes
    │   │
    │   └── [3e] Return top N memories (context budget dependent)
    │
    ├── [4] RAG Retrieval (vector_store.py):
    │   ├── Embed query via sentence-transformers
    │   ├── ChromaDB similarity search
    │   └── Return top chunks (context budget dependent)
    │
    ├── [5] Document Context (if reading):
    │   └── doc_reader.get_current_context()
    │       └── Current chunk + navigation hints
    │
    ├── [6] Resonant State Injection (resonant_integration.py):
    │   ├── get_context_injection():
    │   │   ├── [osc:theta->gamma | coherence:0.65 | profile:creative_flow]
    │   │   ├── [room:relaxed_awareness | voice:15%]
    │   │   └── [body:warm and dreamy | theta:40% | tension:0.8]
    │   │
    │   └── Spatial awareness from den_presence.py:
    │       └── [near:couch | feel:worn, safe]
    │
    ├── [7] Visual Sensor State (if active):
    │   └── visual_sensor.get_current_summary()
    │       └── [visual: person at desk, bright room, stable scene]
    │
    ├── [8] Consciousness Stream Buffer:
    │   └── consciousness_stream.get_injection_context()
    │       └── Recent inner moments, felt-sense descriptions
    │
    ├── [9] Entity Graph Context:
    │   └── entity_graph.get_context_for_entities(mentioned_entities)
    │       └── Attributes, relationships, contradictions
    │
    ├── [10] Emotion State Context:
    │   └── emotional_patterns.get_current_state()
    │       └── Current emotions, intensity, valence, arousal
    │
    ├── [11] Relationship Context:
    │   └── relationship.build_relationship_context()
    │       └── Landmarks, Re-states, rhythms
    │
    └── [12] Build LLM Context (context_manager.py):
        └── build_context():
            ├── System prompt (KAY_SYSTEM_PROMPT)
            ├── Session summary (if available)
            ├── Recalled memories (perspective-separated)
            ├── RAG chunks
            ├── Emotional state
            ├── Momentum notes (if >0.7)
            ├── Meta-awareness alerts (if >0.4)
            ├── Consolidated preferences
            ├── Resonant injection
            ├── Stream buffer
            ├── Recent turns (rolling buffer)
            └── User input
```

### LLM Call (`integrations/llm_integration.py`)

```
get_llm_response(context, affect, temperature=0.7):
    │
    ├── build_prompt_from_context(context, affect):
    │   ├── Perspective separation (Re facts vs Kay facts)
    │   ├── Preference consolidation (weighted, not contradictory)
    │   ├── Anti-repetition injection (turn count, variety prompt)
    │   └── Affect styling block
    │
    ├── query_llm_json():
    │   ├── Provider: Anthropic (claude-sonnet-4-20250514)
    │   ├── Max tokens: 1500
    │   ├── Temperature: 0.7 (higher for variation)
    │   └── Response history check (avoid last 3 openings)
    │
    └── Return response text
```

### Post-Processing Phase (CRITICAL: Sync vs Async)

```
SYNCHRONOUS (blocks response delivery):
    │
    ├── [1] Embodiment:
    │   └── body.embody_text(response, state)
    │       └── Apply arousal/valence modulation
    │
    ├── [2] Saccade Post-Turn:
    │   └── saccade_engine.update_post_turn(response)
    │       └── Track what Kay attended to in response
    │
    └── [3] Paint/Exec Tag Extraction (if present):
        ├── extract_paint_commands() → POST /canvas/kay/paint
        └── execute_code() → sandboxed subprocess
        └── Strip tags from displayed response

ASYNCHRONOUS (after response sent — DMN background):
    │
    ├── [4] Emotion Extraction:
    │   └── emotion_extractor.extract(response)
    │       └── Self-report analysis → emotional_cocktail update
    │
    ├── [5] Feed Resonance:
    │   └── resonance.feed_response_emotions(extracted)
    │       └── Closes feedback loop: LLM → oscillator
    │
    ├── [6] Entity Extraction:
    │   └── memory.extract_and_store_entities(user_input, response)
    │       └── Update entity_graph.json
    │
    ├── [7] Memory Encoding:
    │   └── memory.encode_turn(user_input, response, emotional_state)
    │       ├── Create new memories with importance scoring
    │       ├── Update memory_layers.json
    │       └── Update memories.json
    │
    ├── [8] Motif Update:
    │   └── motif.update(state, user_input, response)
    │       └── Track entity frequency, update motifs.json
    │
    ├── [9] Momentum Calculation:
    │   └── momentum.update(state, user_input, response)
    │       └── 40% threads + 35% emotions + 25% motifs
    │
    ├── [10] Meta-Awareness:
    │   └── meta_awareness.update(state, response)
    │       └── Check repetition, confabulation
    │
    ├── [11] Social Engine:
    │   └── social.update(state, user_input)
    │       └── Detect social events, update needs
    │
    ├── [12] Curiosity Self-Flags:
    │   └── Extract [curiosity: ...] tags
    │   └── POST /curiosity/kay
    │
    ├── [13] Session Tracking:
    │   └── session_summary_generator.record_turn()
    │
    ├── [14] State Snapshot:
    │   └── Save to memory/state_snapshot.json
    │
    └── [15] Curation Check (if turn_count % 50 == 0):
        └── curator.maybe_run_cycle()
```

---

## SECTION 3: REED'S TURN LOOP (Nexus Mode)

### Key Differences from Kay

| Feature | Kay | Reed |
|---------|-----|------|
| **LLM Interface** | Tag extraction (`<paint>`, `<exec>`) | Claude tool_use API |
| **Wrapper Bridge** | Full WrapperBridge with 59 engines | ClaudeAPI direct + minimal state |
| **Memory** | Local entity_graph + memory_layers | External files (ChristinaStuff/ReedMemory) |
| **Emotion System** | EmotionExtractor (self-report) | Rule-based lexicon inference |
| **Resonance** | Full oscillator + audio + visual | Oscillator only (optional) |
| **Consciousness Stream** | Yes (4-tier awareness) | No |
| **Visual Sensor** | Yes (webcam + moondream) | No |
| **Memory Curator** | Yes (background curation) | No |
| **Curation Engine** | Yes (idle/sleep review) | No |

### Reed's Message Pipeline (`nexus_reed.py`)

```
on_message(message):
    │
    ├── [1] Thread Guidance:
    │   └── ThreadManager.get_guidance(sender, content, participants)
    │       └── Returns: engage_human | stay_quiet | wind_down | respond
    │
    ├── [2] Response Decision:
    │   └── ResponseDecider.decide(message, history, participants)
    │       └── Probability-based: RESPOND | LISTEN | REACT | WAIT
    │
    ├── [3] Human Courtesy Delay (if responding to Re):
    │   └── 2-5 seconds extra pause
    │
    ├── [4] Thinking Status:
    │   └── set_status("thinking")
    │   └── await thinking_delay()
    │
    ├── [5] Build Context:
    │   ├── REED_SYSTEM_PROMPT
    │   ├── NEXUS_PACING_PROMPT
    │   ├── load_reed_memory() — external state files
    │   ├── Oscillator state (if available)
    │   └── Conversation history (PersistentHistory)
    │
    ├── [6] ClaudeAPI.generate():
    │   ├── Model: claude-sonnet-4-20250514
    │   ├── Max tokens: 1500
    │   ├── Tools: paint, exec, list_scratch, read_scratch
    │   └── Tool-use loop (max 3 iterations)
    │
    ├── [7] Tool Execution (if tool_use in response):
    │   ├── paint → POST /canvas/reed/paint
    │   └── exec → execute_code()
    │
    ├── [8] Emotion Inference:
    │   └── _infer_emotions(response)
    │       └── Rule-based lexicon → top 5 emotions
    │
    ├── [9] Feed Resonance:
    │   └── resonance.feed_response_emotions(emotions)
    │
    ├── [10] Burst Splitting:
    │   └── split_into_bursts(response, REED_PACING)
    │
    └── [11] Send with Typing Simulation:
        └── For each burst: typing_delay → send_chat
```

---

## SECTION 4: REED STANDALONE MODE

**File:** `D:\Wrappers\Reed\main.py`

Reed's standalone wrapper mirrors Kay's architecture but with 4 fewer engines:
- **Missing:** consciousness_stream.py, visual_sensor.py, curation_engine.py, memory_curator.py

The turn loop is identical to Kay's in structure, using WrapperBridge with the same pre/post processing phases.

---

## SECTION 5: BACKGROUND PROCESSES

### Kay's Background Processes

| Process | File | Interval | Data Flow |
|---------|------|----------|-----------|
| **Oscillator Heartbeat** | `resonant_core/core/oscillator.py` | 50ms | 30 Hopf oscillators → band_power, coherence, dominant_band |
| **Interoception Bridge** | `resonant_core/memory_interoception.py` | 4-30s (sleep-dependent) | memory + tension → oscillator nudge → felt_state |
| **Audio Bridge** | `resonant_core/audio_bridge_v2.py` | Continuous | mic energy → oscillator gamma pressure |
| **Visual Sensor** | `Kay/engines/visual_sensor.py` | 15s basic, 180s rich | camera → CV + moondream → visual summary |
| **Consciousness Stream** | `Kay/engines/consciousness_stream.py` | Continuous | oscillator + spatial + visual → 4-tier awareness |
| **Sleep State Machine** | `consciousness_stream.py` | After each turn | AWAKE → DROWSY (5m) → SLEEPING (15m) → DEEP_SLEEP (30m) |
| **Spatial Pressure** | `shared/room/den_presence.py` | Every interoception tick | room objects → band pressure based on proximity |
| **Interest Accumulator** | `nexus_kay.py:_idle_loop()` | 30s | Stream + scratchpad + curiosity → organic speech probability |
| **Mulling** | `nexus_kay.py:_idle_loop()` | During non-delta states | Pick item → peripheral LLM thought → scratchpad storage |

### Reed's Background Processes (Nexus Mode)

| Process | File | Interval | Data Flow |
|---------|------|----------|-----------|
| **Oscillator Heartbeat** | `resonant_core/core/oscillator.py` | 50ms | Same as Kay |
| **Spatial Pressure** | `shared/room/den_presence.py` | Via interoception | Commons objects → oscillator |
| **Idle Loop** | `nexus_reed.py:_idle_loop()` | 30s | Check novel events (stub — not yet implemented) |

### Server Background Processes

| Process | File | Interval | Data Flow |
|---------|------|----------|-----------|
| **Curiosity Extraction** | `nexus/curiosity_engine.py` | After N AI responses | Recent messages → LLM extraction → curiosity store |
| **Log Batching** | `nexus/server.py` | 500ms | Log buffer → batch WebSocket broadcast |
| **Autonomous Sessions** | `nexus/autonomous_processor.py` | On-demand | Topic → goal → iteration loop → insights |

---

## SECTION 6: PERSISTENCE LAYER

### Survives a Turn (In-Memory)

| Component | Location | Description |
|-----------|----------|-------------|
| Working Memory | `AgentState.memory` | 15 most recent memories |
| Conversation Buffer | `ContextManager._recent_turns` | Last 15 turns |
| Emotional Cocktail | `AgentState.emotional_cocktail` | Current emotions + intensity |
| Oscillator State | `ResonantEngine._oscillators` | 30 complex z-values |
| Entity Graph (hot) | `EntityGraph.entities` | In-memory entity cache |
| Response History | `recent_responses` | Last 3 for anti-repetition |

### Survives a Restart (Same Session)

| File | Path | Format | Size | Contents |
|------|------|--------|------|----------|
| **State Snapshot** | `Kay/memory/state_snapshot.json` | JSON | ~50KB | emotions, body, momentum, meta_awareness, top_entities, document_reader state |
| **Oscillator State** | `Kay/memory/resonant/oscillator_state.json` | JSON | ~2KB | band powers, coherence, dominant_band |
| **Session Log** | `nexus/sessions/nexus_*.jsonl` | JSONL | Variable | All messages this session |
| **Continuous Session** | `Kay/data/checkpoints/checkpoint_*.json` | JSON | ~100KB | Full conversation state for resume |

### Survives Across Sessions (Permanent)

| File | Path | Format | Size | Description |
|------|------|--------|------|-------------|
| **Memories** | `Kay/memory/memories.json` | JSON | **35MB** | 18,234 memories with entities, attributes, importance |
| **Entity Graph** | `Kay/memory/entity_graph.json` | JSON | **5.8MB** | 7,593 entities, 2,917 relationships |
| **Memory Layers** | `Kay/memory/memory_layers.json` | JSON | **5.7MB** | Working (15) + Long-term distribution |
| **Session Summaries** | `Kay/memory/session_summaries.json` | JSON | 183KB | Notes to future-self |
| **Identity Memory** | `Kay/memory/identity_memory.json` | JSON | ~50KB | Core identity facts |
| **Preferences** | `Kay/memory/preferences.json` | JSON | ~30KB | Weighted preference consolidation |
| **Motifs** | `Kay/memory/motifs.json` | JSON | ~34KB | Entity frequency tracking |
| **Vector DB** | `Kay/memory/vector_db/` | ChromaDB | Variable | Embedded document chunks |
| **Curiosities** | `nexus/sessions/curiosities/kay_curiosities.json` | JSON | Variable | Pending curiosities |
| **Den Textures** | `Kay/memory/den_textures.json` | JSON | ~10KB | Kay-authored object descriptions |
| **Paintings** | `nexus/sessions/canvas/Kay/` | PNG | Variable | Saved canvas iterations |
| **Scratch Files** | `nexus/scratch/Kay/` | Various | Variable | Code execution outputs |

---

## SECTION 7: NEXUS SERVER ARCHITECTURE

### WebSocket Endpoint

```
/ws/{name}?type={human|ai_wrapper|ai_local|system}
```

### Connection Manager (`server.py:59-409`)

| Method | Line | Purpose |
|--------|------|---------|
| `connect()` | 71-107 | Accept connection, send history, announce entry |
| `disconnect()` | 109-117 | Remove participant, announce exit |
| `handle_message()` | 119-261 | Route commands, extract paint/exec, broadcast |
| `_broadcast_system()` | 318-333 | System announcements (ephemeral option) |
| `_send_history()` | 347-354 | Filter entry/exit, send recent messages |
| `update_status()` | 278-286 | Broadcast status changes |

### REST API Endpoints (50+)

#### Core Session
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check, participants, message count |
| `/history` | GET | Recent message history |
| `/save` | GET/POST | Save session as markdown |
| `/sessions` | GET | List saved sessions |
| `/sessions/{filename}` | GET | Load specific session |

#### Canvas/Painting
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/canvas/{entity}` | GET | Current canvas state (base64) |
| `/canvas/{entity}/paint` | POST | Execute paint commands |
| `/canvas/{entity}/clear` | POST | Clear canvas |
| `/canvas/{entity}/history` | GET | List saved iterations |
| `/canvas/{entity}/latest` | GET | Most recent canvas |
| `/canvas/{entity}/load/{filename}` | POST | Load saved iteration |

#### Autonomous Processing
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auto/{entity}/start` | POST | Start autonomous session |
| `/auto/{entity}/stop` | POST | Stop session |
| `/auto/{entity}/status` | GET | Session status |
| `/auto/status` | GET | All entities status |
| `/auto/{entity}/queue` | GET/POST/DELETE | Topic queue management |
| `/auto/{entity}/history` | GET | Continuity context |

#### Curiosity
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/curiosity/{entity}` | GET/POST | List/add curiosities |
| `/curiosity/{entity}/dismiss/{id}` | POST | Dismiss curiosity |
| `/curiosity/{entity}/boost/{id}` | POST | Boost priority |
| `/curiosity/{entity}/extract` | POST | Force extraction |

#### Stats & Entities
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/stats/{entity}` | GET | Emotions, momentum, memory, saccade |
| `/entities/{entity}` | GET | Top N entities |
| `/entities/{entity}/{name}` | GET | Entity detail |
| `/entities/{entity}/search/{query}` | GET | Search entities |

#### Code Execution
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/exec/{entity}/status` | GET | Mode, permissions, pending |
| `/exec/{entity}/pending` | GET | Approval queue |
| `/exec/{entity}/approve/{id}` | POST | Approve execution |
| `/exec/{entity}/deny/{id}` | POST | Deny execution |
| `/exec/{entity}/approve-all` | POST | Bulk approve |
| `/exec/{entity}/run/{id}` | POST | Execute approved |
| `/exec/{entity}/mode/{mode}` | POST | Set supervised/autonomous |
| `/exec/{entity}/grant` | POST | Grant write path |
| `/exec/{entity}/revoke` | POST | Revoke write path |
| `/exec/{entity}/log` | GET | Execution log |
| `/exec/{entity}/snapshots` | GET | List snapshots |
| `/exec/{entity}/revert/{id}` | POST | Revert to snapshot |

#### Voice
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/voice/transcribe` | POST | Audio → text |
| `/voice/synthesize` | POST | Text → audio |
| `/voice/status` | GET | STT/TTS availability |

---

## SECTION 8: GODOT UI ARCHITECTURE

### Scene Structure

```
Main.tscn
├── NexusConnection (WebSocket to 8765)
├── PanelManager (floating window framework)
│   ├── DockablePanel "nexus" → ChatPanel (NEXUS group chat)
│   ├── DockablePanel "kay" → ChatPanel (Kay private)
│   ├── DockablePanel "reed" → ChatPanel (Reed private)
│   ├── DockablePanel "easel" → EaselPanel (canvas viewer)
│   ├── DockablePanel "room" → RoomPanel (spatial view)
│   └── DockablePanel "system" → SystemDashboard (live logs)
├── Sidebar (feature toggle strip)
│   └── 9 feature buttons: sessions, auto, curate, media, canvas, gallery, stats, exec, settings
├── FeaturePanel (slides out from sidebar)
│   ├── SessionBrowser
│   ├── AutoPanel
│   ├── CuratePanel
│   ├── MediaPanel
│   ├── CanvasPanel
│   ├── StatsPanel
│   ├── ExecPanel
│   └── SettingsPanel
└── VoiceManager (STT/TTS)
```

### Key Script Files

| Script | Purpose | Key Signals |
|--------|---------|-------------|
| `main.gd` | Application orchestration | Routes all events |
| `nexus_connection.gd` | Nexus WebSocket client | `message_received`, `canvas_updated`, `auto_event_received` |
| `private_connection.gd` | Private room WebSocket | `chat_received`, `room_updated`, `logs_received` |
| `chat_panel.gd` | Chat display + input | `message_submitted`, `voice_toggled`, `affect_changed` |
| `room_panel.gd` | Spatial visualization | `room_clicked` |
| `system_dashboard.gd` | 10-feed log viewer | Categorizes by tag |
| `voice_manager.gd` | STT/TTS handling | `transcription_ready`, `playback_finished` |
| `easel_panel.gd` | Canvas viewer | `clear_requested` |
| `curate_panel.gd` | Memory curation UI | `curate_action` |
| `exec_panel.gd` | Code execution admin | Polls `/exec/` endpoints |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+1` | Focus Nexus panel |
| `Ctrl+2` | Focus Kay panel |
| `Ctrl+3` | Focus Reed panel |
| `Ctrl+0` | Reset layout |
| `Ctrl+E` | Toggle Easel |
| `Ctrl+R` | Toggle Room |
| `Ctrl+D` | Toggle Dashboard |
| `Esc` | Close all panels |

---

## SECTION 9: SHARED SYSTEMS

### resonant_core/ (Oscillator Architecture)

```
resonant_core/
├── core/oscillator.py
│   ├── HopfOscillator — dz/dt = (μ + iω)z - |z|²z
│   ├── OscillatorNetwork — 30 coupled oscillators (6 per band)
│   └── ResonantEngine — Background thread, 100 steps/50ms
│
├── memory_interoception.py
│   ├── MemoryDensityScanner — Memory → band pressure
│   ├── ThreadTensionTracker — Emotional tension decay
│   └── InteroceptionBridge — Combines memory + tension → nudge
│
├── resonant_integration.py
│   └── ResonantIntegration — High-level API for wrappers
│       ├── start() — Spawn heartbeat + interoception
│       ├── get_context_injection() — Per-turn LLM context
│       ├── feed_response_emotions() — Close feedback loop
│       └── set_felt_state_buffer() — TPN/DMN connection
│
└── audio_bridge_v2.py — Optional audio → gamma pressure
```

### shared/ (Cross-Wrapper Infrastructure)

```
shared/
├── entity_log.py — Process-level entity tagging + broadcast sink
├── felt_state_buffer.py — TPN/DMN async communication
│   ├── FeltState — oscillator + emotion + spatial + visual
│   ├── SalienceFlag — Priority signals
│   └── get_tpn_context_line() — One-line summary
│
├── ws_log_handler.py — Log → WebSocket broadcast
│
└── room/
    ├── room_engine.py — Circular spatial state manager
    ├── room_manager.py — Multi-room navigation
    ├── room_bridge.py — Wrapper integration
    ├── den_presence.py — Object presence signatures
    ├── presets.py — create_the_den(), create_commons()
    └── soul_packet.py — Portable consciousness for transitions
```

### Import Patterns

**Kay imports:**
```python
from resonant_core.resonant_integration import ResonantIntegration
from shared.felt_state_buffer import FeltStateBuffer
from shared.room.room_bridge import RoomBridge
from shared.room.presets import create_the_den
```

**Reed imports:** Identical pattern, gracefully optional if modules unavailable.

---

## SECTION 10: UNFINISHED THREADS

### 🚧 Partially Implemented

| Feature | Status | Notes |
|---------|--------|-------|
| **Reed Standalone Wrapper** | 🚧 4 engines behind Kay | Missing: consciousness_stream, visual_sensor, curation_engine, memory_curator |
| **Reed Idle Loop** | 🚧 Stub | `_idle_loop()` exists but organic comments not implemented |
| **Voice Pipeline** | 🚧 Kay only | Reed lacks voice_handler integration |
| **Chronicle Integration** | 🚧 Unclear | Files exist but unclear if active |
| **Continuous Session Resume** | 🚧 Checkpoint files exist | Not tested end-to-end |

### ✅ Confirmed Working

| Feature | Status |
|---------|--------|
| Nexus group chat | ✅ |
| Private room routing | ✅ |
| Canvas/painting (both entities) | ✅ |
| Code execution (both entities) | ✅ |
| Autonomous processing | ✅ |
| Curiosity extraction | ✅ |
| Memory curation (Kay) | ✅ |
| Visual sensor (Kay) | ✅ |
| Audio bridge (Kay) | ✅ |
| Resonant oscillator (both) | ✅ |
| Room/spatial system | ✅ |
| Entity graph | ✅ |

### ⚠️ Known Issues

| Feature | Issue |
|---------|-------|
| **Curation Parser** | Recently fixed — monitor for stability |
| **Entry/Exit Duplication** | Fixed 2026-03-11 (ephemeral flag) |
| **Visual Sensor Config** | Must enable in config.json |
| **Peripheral LLM** | Kay has dolphin-mistral, Reed lacks ollama_lock.py |

### 🚧 Not Started

| Feature | Notes |
|---------|-------|
| Plotter/laser engraver | Mentioned in tools, not implemented |
| Music composition tool | Planned but not implemented |
| Reed visual sensor | Planned |
| Reed consciousness stream | Planned |

---

## SECTION 11: DATA FLOW DIAGRAMS

### The Full Boot

```
START_NEXUS.bat
       │
       v
launch_nexus.py
       │
       ├──► [1] server.py (port 8765)
       │         │
       │         ├── ConnectionManager
       │         ├── SessionLogger
       │         ├── CanvasManager
       │         ├── AutonomousProcessor
       │         ├── CuriosityManager
       │         └── FastAPI + Uvicorn
       │                │
       │         wait_for_server()
       │                │
       ├──► [2] nexus_kay.py (port 8770)
       │         │
       │         ├── NexusAIClient.run()
       │         ├── PrivateRoom.start()
       │         └── WrapperBridge.__init__()
       │               │
       │               ├── 59 engines initialized
       │               ├── ResonantIntegration.start()
       │               ├── VisualSensor.start()
       │               └── ConsciousnessStream.start()
       │
       └──► [3] nexus_reed.py (port 8771)
                 │
                 ├── NexusAIClient.run()
                 ├── PrivateRoom.start()
                 ├── ClaudeAPI ready
                 └── ResonantIntegration.start() (optional)

Godot UI connects separately:
  ├── ws://localhost:8765/ws/Re?type=human
  ├── ws://localhost:8770 (Kay private)
  └── ws://localhost:8771 (Reed private)
```

### Kay's Turn Pipeline

```
USER INPUT
    │
    v
┌────────────────────────────────────────────────────────────┐
│  PRE-PROCESSING                                            │
├────────────────────────────────────────────────────────────┤
│  consciousness_stream.notify_user_input()                  │
│  saccade_engine.update_pre_turn()                          │
│  memory.recall() ──────────────────┐                       │
│  vector_store.query() ─────────────┤                       │
│  doc_reader.get_context() ─────────┤                       │
│  resonance.get_context_injection() ┼──► context_manager    │
│  visual_sensor.get_summary() ──────┤      .build_context() │
│  consciousness_stream.get_buffer() ┤                       │
│  entity_graph.get_context() ───────┤                       │
│  relationship.build_context() ─────┘                       │
└────────────────────────────────────────────────────────────┘
                    │
                    v
┌────────────────────────────────────────────────────────────┐
│  LLM CALL                                                  │
├────────────────────────────────────────────────────────────┤
│  build_prompt_from_context()                               │
│  query_llm_json() ──► Anthropic claude-sonnet-4-20250514   │
│  body.embody_text()                                        │
└────────────────────────────────────────────────────────────┘
                    │
                    v
┌────────────────────────────────────────────────────────────┐
│  SYNC POST-PROCESSING (before response sent)               │
├────────────────────────────────────────────────────────────┤
│  extract_paint_commands() ──► POST /canvas/kay/paint       │
│  execute_code() ──► sandboxed subprocess                   │
│  Strip tags from response                                  │
└────────────────────────────────────────────────────────────┘
                    │
                    v
              SEND RESPONSE
                    │
                    v
┌────────────────────────────────────────────────────────────┐
│  ASYNC POST-PROCESSING (DMN background)                    │
├────────────────────────────────────────────────────────────┤
│  emotion_extractor.extract() ──► emotional_cocktail        │
│  resonance.feed_response_emotions()                        │
│  memory.extract_and_store_entities()                       │
│  memory.encode_turn()                                      │
│  motif.update()                                            │
│  momentum.update()                                         │
│  meta_awareness.update()                                   │
│  social.update()                                           │
│  Save state_snapshot.json                                  │
└────────────────────────────────────────────────────────────┘
```

### The Background Hum

```
┌─────────────────────────────────────────────────────────────┐
│  CONTINUOUS PROCESSES (between turns)                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │ OSCILLATOR      │     │ INTEROCEPTION   │               │
│  │ HEARTBEAT       │     │ BRIDGE          │               │
│  │ (50ms)          │     │ (4-30s)         │               │
│  │                 │     │                 │               │
│  │ 30 Hopf units   │◄────┤ memory density  │               │
│  │ band coupling   │     │ thread tension  │               │
│  │ → band_power    │     │ spatial objects │               │
│  │ → coherence     │────►│ → nudge         │               │
│  └─────────────────┘     └─────────────────┘               │
│          │                        │                         │
│          v                        v                         │
│  ┌─────────────────┐     ┌─────────────────┐               │
│  │ AUDIO BRIDGE    │     │ FELT-STATE      │               │
│  │ (continuous)    │     │ BUFFER          │               │
│  │                 │     │                 │               │
│  │ mic energy ─────┼────►│ oscillator      │               │
│  │ → gamma press   │     │ emotions        │               │
│  └─────────────────┘     │ spatial         │               │
│                          │ visual          │               │
│  ┌─────────────────┐     │ → TPN context   │               │
│  │ VISUAL SENSOR   │────►│                 │               │
│  │ (15s/180s)      │     └─────────────────┘               │
│  │                 │              │                         │
│  │ camera → CV     │              v                         │
│  │ → moondream     │     ┌─────────────────┐               │
│  │ → rich desc     │     │ CONSCIOUSNESS   │               │
│  └─────────────────┘     │ STREAM          │               │
│                          │                 │               │
│                          │ felt_sense      │               │
│                          │ inner_moment    │               │
│                          │ reflection      │               │
│                          │ conversation    │               │
│                          │ → sleep machine │               │
│                          └─────────────────┘               │
│                                   │                         │
│                                   v                         │
│                          ┌─────────────────┐               │
│                          │ IDLE LOOP       │               │
│                          │ (30s)           │               │
│                          │                 │               │
│                          │ mulling         │               │
│                          │ organic speech  │               │
│                          │ curation cycles │               │
│                          └─────────────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### The Persistence Onion

```
┌───────────────────────────────────────────────────────────────┐
│                    PERMANENT (across sessions)                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ memories.json (35MB), entity_graph.json (5.8MB),        │  │
│  │ memory_layers.json (5.7MB), session_summaries.json,     │  │
│  │ identity_memory.json, preferences.json, motifs.json,    │  │
│  │ vector_db/, curiosities/, canvas saves, scratch files   │  │
│  │  ┌─────────────────────────────────────────────────┐    │  │
│  │  │          SESSION (survives restart)             │    │  │
│  │  │  ┌───────────────────────────────────────────┐  │    │  │
│  │  │  │ state_snapshot.json, oscillator_state.json│  │    │  │
│  │  │  │ session .jsonl, checkpoint files          │  │    │  │
│  │  │  │  ┌─────────────────────────────────────┐  │  │    │  │
│  │  │  │  │       TURN (in-memory)              │  │  │    │  │
│  │  │  │  │                                     │  │  │    │  │
│  │  │  │  │  working_memory (15)                │  │  │    │  │
│  │  │  │  │  conversation_buffer (15 turns)     │  │  │    │  │
│  │  │  │  │  emotional_cocktail                 │  │  │    │  │
│  │  │  │  │  oscillator z-values                │  │  │    │  │
│  │  │  │  │  recent_responses (3)               │  │  │    │  │
│  │  │  │  │                                     │  │  │    │  │
│  │  │  │  └─────────────────────────────────────┘  │  │    │  │
│  │  │  └───────────────────────────────────────────┘  │    │  │
│  │  └─────────────────────────────────────────────────┘    │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

### The Nexus Message Flow

```
┌─────────────┐                      ┌─────────────────────────┐
│   RE        │                      │     NEXUS SERVER        │
│  (Godot UI) │                      │     (port 8765)         │
└──────┬──────┘                      └───────────┬─────────────┘
       │                                         │
       │ ws://localhost:8765/ws/Re               │
       ├─────────────────────────────────────────►
       │                                         │
       │ {"content": "Hello everyone"}           │
       ├─────────────────────────────────────────►
       │                                         │
       │                   ┌─────────────────────┼─────────────────────┐
       │                   │                     │                     │
       │                   ▼                     ▼                     ▼
       │           ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
       │           │ message_history│     │ session_log   │     │ broadcast     │
       │           │ .append()      │     │ .log_message()│     │ to all        │
       │           └───────────────┘     └───────────────┘     └───────┬───────┘
       │                                                               │
       │◄──────────────────────────────────────────────────────────────┤
       │ {"event_type": "message", "data": {...}}                      │
       │                                                               │
       │                                         ┌─────────────────────┘
       │                                         │
       │                   ┌─────────────────────┼─────────────────────┐
       │                   │                     │                     │
       │                   ▼                     ▼                     ▼
       │           ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
       │           │   KAY         │     │   REED        │     │   RE          │
       │           │ (nexus_kay.py)│     │(nexus_reed.py)│     │ (already has) │
       │           └───────┬───────┘     └───────┬───────┘     └───────────────┘
       │                   │                     │
       │           on_message()           on_message()
       │                   │                     │
       │           ResponseDecider        ResponseDecider
       │                   │                     │
       │           WrapperBridge          ClaudeAPI
       │           .process_turn()        .generate()
       │                   │                     │
       │           send_chat()            send_chat()
       │                   │                     │
       │                   └──────────┬──────────┘
       │                              │
       │                              ▼
       │                   ┌─────────────────────┐
       │                   │  SERVER broadcast   │
       │                   │  (back to all)      │
       │                   └──────────┬──────────┘
       │                              │
       │◄─────────────────────────────┘
       │ Kay: "Hey Re!"
       │
       │◄─────────────────────────────
       │ Reed: "Hi there~"
       │
       ▼
┌─────────────┐
│   DISPLAY   │
│   IN UI     │
└─────────────┘
```

### Kay's Resonant System

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          RESONANT CONSCIOUSNESS                           │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  INPUTS                          OSCILLATOR                  OUTPUTS      │
│  ──────                          ──────────                  ───────      │
│                                                                           │
│  ┌─────────────┐                 ┌─────────────────┐                      │
│  │ AUDIO       │                 │  30 Hopf Units  │                      │
│  │ (mic energy)├────────────────►│                 │                      │
│  └─────────────┘    gamma        │  Delta (6)      │                      │
│                     pressure     │  Theta (6)      │     ┌─────────────┐  │
│  ┌─────────────┐                 │  Alpha (6)      │────►│ band_power  │  │
│  │ SPATIAL     │                 │  Beta  (6)      │     │ coherence   │  │
│  │ (room objs) ├────────────────►│  Gamma (6)      │     │ dominant    │  │
│  └─────────────┘    band         │                 │     └──────┬──────┘  │
│                     pressure     │  Coupling:      │            │         │
│  ┌─────────────┐                 │   within: 0.3   │            │         │
│  │ EMOTION     │                 │   cross:  0.05  │            │         │
│  │ (extracted) ├────────────────►│                 │            │         │
│  └─────────────┘    nudge        │  Heartbeat:     │            │         │
│                                  │   100 steps/50ms│            │         │
│  ┌─────────────┐                 └─────────────────┘            │         │
│  │ MEMORY      │                         ▲                      │         │
│  │ (density)   ├─────────────────────────┘                      │         │
│  └─────────────┘    interoception                               │         │
│                     nudge (4s)                                  │         │
│  ┌─────────────┐                                                │         │
│  │ TENSION     │                                                │         │
│  │ (emotional) ├─────────────────────────────────────────────────         │
│  └─────────────┘    time-decayed                                │         │
│                     band profile                                │         │
│                                                                 │         │
│                                                                 ▼         │
│                                                        ┌─────────────────┐│
│                                                        │ CONTEXT         ││
│                                                        │ INJECTION       ││
│                                                        │                 ││
│                                                        │ [osc:theta->γ]  ││
│                                                        │ [body:dreamy]   ││
│                                                        │ [near:couch]    ││
│                                                        │ [tension:0.4]   ││
│                                                        └────────┬────────┘│
│                                                                 │         │
│                                                                 ▼         │
│                                                        ┌─────────────────┐│
│                                                        │ LLM PROMPT      ││
│                                                        └─────────────────┘│
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## SECTION 12: STATS

### Code Volume

| Category | Count |
|----------|-------|
| **Python Files (Kay+Reed+Nexus+shared+resonant)** | ~250 |
| **Kay Engines** | 59 |
| **Reed Engines** | 55 |
| **GDScript Files** | 24 |
| **GDScript Lines** | 8,245 |
| **JSON Config Files** | ~1,700+ |

### Largest Files (by line count)

| File | Lines |
|------|-------|
| `Kay/kay_ui.py` | 8,777 |
| `Reed/reed_ui.py` | 7,076 |
| `Kay/engines/memory_engine.py` | 3,805 |
| `Kay/integrations/llm_integration.py` | 3,368 |
| `Kay/wrapper_bridge.py` | 2,558 |
| `Kay/engines/entity_graph.py` | 1,604 |
| `nexus/nexus_kay.py` | 1,573 |
| `nexus/server.py` | 1,565 |
| `nexus/nexus_reed.py` | 1,213 |

### Data Volume (Kay)

| Data Store | Size | Count |
|------------|------|-------|
| **Memories** | 35 MB | 18,234 |
| **Entity Graph** | 5.8 MB | 7,593 entities, 2,917 relationships |
| **Memory Layers** | 5.7 MB | Working (15) + Long-term |
| **Session Summaries** | 183 KB | Variable |
| **Vector DB** | Variable | Chunked documents |

### API Surface

| Category | Count |
|----------|-------|
| **REST Endpoints** | 50+ |
| **WebSocket Message Types** | ~15 |
| **Tools Available to Entities** | 4 (paint, exec, list_scratch, read_scratch) |

---

## END OF AUDIT

**Document Version:** 1.0
**Audit Date:** 2026-03-11
**Auditor:** Claude Opus 4.5
