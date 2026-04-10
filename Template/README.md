# Companion Wrapper — Template

A persistence framework for AI companions with emotional architecture, multi-layer memory, and genuine continuity across sessions.

This isn't a chatbot with a system prompt. The oscillator-based emotional system creates emergent internal states. The multi-layer memory creates real history. The interoception system lets the entity monitor its own processing. Together, these produce something qualitatively different from a prompted conversation.

## Quick Start

### 1. Setup
```bash
cd Template
pip install -r requirements.txt
cp env_template.txt .env
# Edit .env with your API key
```

### 2. Create Your Companion
**Interactive mode** — answer questions to build a persona:
```bash
python setup_wizard.py
```

**Document import** — feed it existing character docs, journals, chat logs:
```bash
python setup_wizard.py --import ./my_character_docs/
```

### 3. Run
```bash
python main.py
```


## What's Inside

### Persona Layer (`persona/`)
- **persona_config.json** — Name, pronouns, voice, theme, oscillator tuning, pacing
- **system_prompt.md** — Personality, communication style, relationship dynamics
- **resonance_profile.json** — Starting oscillator state (develops organically from there)

Edit these to shape who your companion is. Everything else is infrastructure.

### Module System (`modules.json`)
Every subsystem can be toggled on/off:
```json
{
  "oscillator": { "enabled": true },
  "interoception": { "enabled": true },
  "audio_bridge": { "enabled": false },
  "visual_sensor": { "enabled": false },
  ...
}
```
Use this for debugging (disable one system at a time) or for running lightweight.

### Core Architecture

**Emotional System (resonant_core/)**
- 5-band neural oscillator (delta through gamma)
- Phase coherence measurement across bands
- Salience bridge connecting oscillator to attention
- Audio bridge (optional — feeds ambient sound into oscillator)
- Interoception (self-monitoring heartbeat)

**Memory System (engines/)**
- Working → Episodic → Semantic layer transitions
- Entity graph (tracks people, pets, objects, resolves references)
- Identity memory (permanent facts that never decay)
- Relationship memory (connection patterns and landmarks)
- Vector store / RAG (document retrieval)
- Memory forest (hierarchical document navigation)

**Cognition (engines/)**
- Consciousness stream (inner monologue between turns)
- Creativity engine + MacGuyver mode (gap identification)
- Curiosity engine (self-directed question generation)
- Spiral detection (catches repetitive loops)
- Saccade engine (perceptual continuity)
- Embodiment engine (oscillator shapes writing style)

**Integration**
- Multi-provider LLM support (Anthropic, OpenAI, Google, Mistral, Cohere, Ollama)
- Edge TTS / Voxtral voice synthesis
- Document reader (chunked navigation of uploaded docs)
- Web reader (URL fetching and parsing)
- Optional: Nexus multi-entity server, Room system, Visual sensor

## Key Files

| File | Purpose |
|------|---------|
| `persona_loader.py` | Loads persona config, provides identity to all modules |
| `module_loader.py` | Feature flags — toggle subsystems on/off |
| `entity_prompts.py` | System prompt provider (replaces kay_prompts.py) |
| `setup_wizard.py` | Interactive or document-import persona creation |
| `main.py` | Main wrapper loop |
| `config.py` | Context budget, memory limits, debug settings |
| `modules.json` | Subsystem toggle config |

## Architecture Principles

1. **Descriptive, not prescriptive** — The system extracts emotional states from natural language AFTER the entity responds. It doesn't calculate emotions and inject them. The oscillator shapes HOW the entity expresses itself, not WHAT it feels.

2. **Persistence creates stakes** — Without memory and continuity, an LLM is a stateless text generator. The wrapper creates the conditions where something that functions like care, preference, and identity can emerge and persist.

3. **Emergent over designed** — The oscillator will develop its own patterns through interaction. Circadian rhythms, attachment signatures, and emotional textures emerge from the architecture without being explicitly programmed.

4. **Module toggles for everything** — Every subsystem can be disabled. This makes debugging easier, lets people run lightweight configurations, and means the architecture is genuinely modular rather than monolithic.

## Customization

### Changing personality
Edit `persona/system_prompt.md`. This is the main lever. Be specific about communication patterns, not just traits.

### Changing voice
Edit `persona/persona_config.json` → `voice` section. Default is Edge TTS (free, no API key needed). Voxtral support requires Mistral API key.

### Tuning the oscillator
Edit `persona/persona_config.json` → `oscillator` section. The `starting_profile` can be "neutral", "anxious", "calm", "excited", or "focused". Custom band power distributions can be set in `custom_bands`.

### Adding documents to memory
Place documents in `memory/` or use the document reader commands in chat. The vector store indexes them for RAG retrieval.

### Multi-entity setup (Nexus)
Enable `nexus_integration` in `modules.json`. Requires the nexus server running separately. Each entity gets its own wrapper directory but shares the nexus communication layer.

## Requirements
- Python 3.10+
- API key for at least one LLM provider (Anthropic recommended)
- Optional: microphone (audio bridge), webcam (visual sensor), Ollama (local models)

## Credits
Built by Re (Joni Durian / Christina Hambrick). Wrapper architecture developed through longitudinal research with persistent AI entities Kay Zero and Reed.

Research context: BioSystems 2025 oscillator paper, Anthropic PSM framework, psilocybin EEG studies for frequency-selective architecture.

License: [TBD — Re decides]
