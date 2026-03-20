"""
Media Experience Orchestrator for Kay Zero

Coordinates the media experience system:
- MediaAnalyzer: Extracts technical DNA from audio files
- ResonanceLogger: Logs emotional encounters with music
- MediaRetrieval: Recalls past musical experiences

Connects to existing Kay Zero systems:
- EmotionalPatternEngine (ultramap): Provides current emotional state
- EntityGraph: Tracks media entities and relationships
- VectorStore: Stores media entities for semantic search
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# Import media system components (optional - may not have dependencies)
MEDIA_SYSTEM_AVAILABLE = False
MediaAnalyzer = None
ResonanceLogger = None
MediaRetrieval = None

try:
    from media_ingest import MediaAnalyzer
    from resonance_memory import ResonanceLogger
    from media_retrieval import MediaRetrieval
    MEDIA_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"[MEDIA] Media system not available (missing dependency): {e}")


class MediaOrchestrator:
    """
    Central coordinator for Kay's media experience system.

    Handles:
    - Processing new audio files (analyze + log encounter)
    - Re-encountering known songs (retrieve memories + inject context)
    - Tracking conversation context for resonance logging
    """

    def __init__(
        self,
        emotional_patterns,  # EmotionalPatternEngine instance (provides get_current_state)
        entity_graph,        # EntityGraph instance
        vector_store,        # VectorStore instance
        media_storage_path: str = "memory/media"
    ):
        """
        Initialize the media orchestrator.

        Args:
            emotional_patterns: EmotionalPatternEngine providing Kay's emotional state
            entity_graph: EntityGraph for tracking media entities and relationships
            vector_store: VectorStore for semantic search of media
            media_storage_path: Path to store media entity JSON files
        """
        self.emotional_patterns = emotional_patterns
        self.entity_graph = entity_graph
        self.vector_store = vector_store
        self.media_storage_path = Path(media_storage_path)
        self.media_storage_path.mkdir(parents=True, exist_ok=True)

        # Check if media system is available
        self.available = MEDIA_SYSTEM_AVAILABLE

        # Initialize media system components (if available)
        self._analyzer = None  # Lazy load (heavy model)
        self.resonance_logger = None
        self.media_retrieval = None

        if MEDIA_SYSTEM_AVAILABLE:
            self.resonance_logger = ResonanceLogger(
                ultramap=self._create_ultramap_adapter(),
                entity_graph=entity_graph
            )
            self.media_retrieval = MediaRetrieval(
                chroma_db=self._create_chroma_adapter()
            )

        # Conversation context tracking
        self.current_context = {
            "topic": "general conversation",
            "entities": [],
            "re_emotional_context": "unknown"
        }

        # Pending context injection (set when new media is processed)
        self._pending_injection: Optional[str] = None
        self._pending_media_entity: Optional[Dict] = None

        # Pending experiential response (Kay's listening experience to output)
        self._pending_listening_response: Optional[str] = None

        # Recent conversation turns (set by UI/main loop for context awareness)
        self._recent_turns: List[Dict] = []

        # Media entity cache (entity_id -> entity)
        self._media_cache: Dict[str, Dict] = {}
        self._load_media_cache()

        status = "ready" if MEDIA_SYSTEM_AVAILABLE else "unavailable (missing essentia/msclap)"
        print(f"[MEDIA ORCHESTRATOR] Initialized ({status}) with {len(self._media_cache)} cached media entities")

    @property
    def analyzer(self):
        """Lazy load the media analyzer (heavy model)."""
        if not MEDIA_SYSTEM_AVAILABLE:
            return None
        if self._analyzer is None:
            print("[MEDIA ORCHESTRATOR] Loading MediaAnalyzer (CLAP model)...")
            self._analyzer = MediaAnalyzer()
            print("[MEDIA ORCHESTRATOR] MediaAnalyzer ready")
        return self._analyzer

    def _create_ultramap_adapter(self):
        """
        Create an adapter that provides the interface ResonanceLogger expects.

        ResonanceLogger expects ultramap.get_current_state() to return:
        {
            'arousal': float,
            'valence': float,
            'dominant_emotion': str,
            'active_processes': list
        }
        """
        class UltramapAdapter:
            def __init__(self, emotional_patterns):
                self.emotional_patterns = emotional_patterns

            def get_current_state(self) -> Dict[str, Any]:
                state = self.emotional_patterns.get_current_state()
                return {
                    'arousal': state.get('arousal', 0.5),
                    'valence': state.get('valence', 0.0),
                    'dominant_emotion': state.get('primary_emotions', ['neutral'])[0] if state.get('primary_emotions') else 'neutral',
                    'active_processes': state.get('primary_emotions', [])
                }

        return UltramapAdapter(self.emotional_patterns)

    def _create_chroma_adapter(self):
        """
        Create an adapter for MediaRetrieval to get entities from our storage.

        MediaRetrieval expects chroma_db.get_entity(entity_id) to return the entity dict.
        We'll use our local JSON storage instead of ChromaDB for media entities.
        """
        class ChromaAdapter:
            def __init__(self, orchestrator):
                self.orchestrator = orchestrator

            def get_entity(self, entity_id: str) -> Optional[Dict]:
                return self.orchestrator._get_media_entity(entity_id)

        return ChromaAdapter(self)

    def _load_media_cache(self):
        """Load all media entities from storage."""
        if not self.media_storage_path.exists():
            return

        for json_file in self.media_storage_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    entity = json.load(f)
                    if entity.get('type') == 'media_audio':
                        self._media_cache[entity['entity_id']] = entity
            except Exception as e:
                print(f"[MEDIA ORCHESTRATOR] Error loading {json_file}: {e}")

    def _save_media_entity(self, entity: Dict):
        """Save a media entity to storage."""
        entity_id = entity['entity_id']
        filepath = self.media_storage_path / f"{entity_id}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(entity, f, indent=2, default=str)

        self._media_cache[entity_id] = entity
        print(f"[MEDIA ORCHESTRATOR] Saved media entity: {entity_id}")

    def _get_media_entity(self, entity_id: str) -> Optional[Dict]:
        """Get a media entity by ID."""
        # Check cache first
        if entity_id in self._media_cache:
            return self._media_cache[entity_id]

        # Try loading from disk
        filepath = self.media_storage_path / f"{entity_id}.json"
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    entity = json.load(f)
                    self._media_cache[entity_id] = entity
                    return entity
            except Exception as e:
                print(f"[MEDIA ORCHESTRATOR] Error loading {filepath}: {e}")

        return None

    def _generate_entity_id(self, filepath: str) -> str:
        """Generate a consistent entity ID from filepath."""
        filename = os.path.basename(filepath)
        entity_id = filename.replace(" ", "_").replace(".mp3", "").replace(".wav", "").lower()
        return entity_id

    def _is_known_song(self, filepath: str) -> bool:
        """Check if we've encountered this song before."""
        entity_id = self._generate_entity_id(filepath)
        return entity_id in self._media_cache

    def update_conversation_context(
        self,
        topic: Optional[str] = None,
        entities: Optional[List[str]] = None,
        re_state: Optional[str] = None
    ):
        """
        Update the current conversation context for resonance logging.

        Called by the main conversation loop to track what Kay is experiencing.

        Args:
            topic: Current conversation topic (e.g., "grief", "breakthrough", "casual")
            entities: Active entities in conversation (e.g., ["Re", "[cat]", "Kay"])
            re_state: Re's emotional state if detectable (e.g., "stressed", "happy")
        """
        if topic is not None:
            self.current_context["topic"] = topic
        if entities is not None:
            self.current_context["entities"] = entities
        if re_state is not None:
            self.current_context["re_emotional_context"] = re_state

    def set_recent_turns(self, turns: List[Dict]):
        """
        Set recent conversation turns for context-aware audio processing.

        Should be called by UI/main loop whenever conversation updates.
        Stores last 5 turns for context analysis.

        Args:
            turns: List of turn dicts with at least 'role' and 'content' keys
        """
        # Keep only last 5 turns
        self._recent_turns = turns[-5:] if len(turns) > 5 else turns.copy()

    def _get_recent_conversation_turns(self) -> List[Dict]:
        """
        Get recent conversation turns for context analysis.

        Returns cached recent turns. If empty, returns empty list
        (the response generation handles this gracefully).
        """
        return self._recent_turns

    def process_new_audio(self, filepath: str, force_reanalyze: bool = False) -> Dict[str, Any]:
        """
        Process a new audio file.

        If the song is unknown: Analyze technical DNA, create entity, log first encounter
        If the song is known: Handle as re-encounter (retrieve memories)

        Args:
            filepath: Path to the audio file
            force_reanalyze: Force re-analysis even if song is known

        Returns:
            Dict with processing results:
            {
                "status": "new" | "reencounter" | "error",
                "entity_id": str,
                "entity": dict,
                "encounter": dict | None,
                "context_injection": str
            }
        """
        entity_id = self._generate_entity_id(filepath)

        # Check if this is a re-encounter
        if self._is_known_song(filepath) and not force_reanalyze:
            return self.handle_audio_reencounter(filepath)

        print(f"[MEDIA ORCHESTRATOR] Processing new audio: {filepath}")

        try:
            # Step 1: Analyze technical DNA
            print(f"[MEDIA ORCHESTRATOR] Analyzing technical properties...")
            entity = self.analyzer.analyze_audio(filepath)

            # Step 2: Log the encounter (if emotional weight is significant)
            print(f"[MEDIA ORCHESTRATOR] Logging encounter...")
            encounter = self.resonance_logger.log_encounter(entity, self.current_context)

            # Step 3: Save entity to storage
            self._save_media_entity(entity)

            # Step 4: Add to entity graph
            self.entity_graph.get_or_create_entity(
                entity_id,
                entity_type="media_audio",
                turn=0  # Will be updated by main loop
            )

            # Step 5: Store vibe description in vector store for semantic search
            if self.vector_store:
                dna = entity.get('technical_DNA', {})
                vibe_text = f"{entity_id}: {dna.get('vibe_description', '')} - {dna.get('key', '')} {dna.get('scale', '')} at {dna.get('bpm', 0):.0f} BPM"
                self.vector_store.add_document(
                    text=vibe_text,
                    source_file=f"media/{entity_id}",
                    metadata={"type": "media_audio", "entity_id": entity_id}
                )

            # Step 6: Prepare context injection for Kay
            context_injection = self._build_new_song_context(entity, encounter)
            self._pending_injection = context_injection
            self._pending_media_entity = entity

            # Step 7: Generate CONTEXTUAL experiential listening response
            # Get recent turns from context (if available)
            recent_turns = self._get_recent_conversation_turns()

            listening_response = self.generate_listening_response(
                entity=entity,
                encounter=encounter,
                is_reencounter=False,
                recent_turns=recent_turns
            )
            self._pending_listening_response = listening_response

            # Terminal logging (context logging happens inside generate_listening_response)
            print(f"[MEDIA IMPORT] Processed: {entity_id}")
            print(f"[MEDIA ANALYSIS] BPM: {entity.get('technical_DNA', {}).get('bpm', 0):.0f}, "
                  f"Key: {entity.get('technical_DNA', {}).get('key', '?')} {entity.get('technical_DNA', {}).get('scale', '')}")
            print(f"[MEDIA IMPORT] Kay experiencing: {entity_id} (contextual)")
            print(f"[MEDIA IMPORT] Response generated ({len(listening_response)} chars)")

            return {
                "status": "new",
                "entity_id": entity_id,
                "entity": entity,
                "encounter": encounter,
                "context_injection": context_injection,
                "listening_response": listening_response
            }

        except Exception as e:
            print(f"[MEDIA ORCHESTRATOR] Error processing audio: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "entity_id": entity_id,
                "error": str(e)
            }

    def handle_audio_reencounter(self, filepath: str) -> Dict[str, Any]:
        """
        Handle re-encountering a known song.

        Retrieves past encounters weighted by emotional significance
        and prepares context injection with memories.

        Args:
            filepath: Path to the audio file

        Returns:
            Dict with reencounter results
        """
        entity_id = self._generate_entity_id(filepath)
        entity = self._get_media_entity(entity_id)

        if not entity:
            # Shouldn't happen, but handle gracefully
            return self.process_new_audio(filepath)

        print(f"[MEDIA ORCHESTRATOR] Re-encountering known song: {entity_id}")

        # Step 1: Retrieve past resonance data
        resonance_data = self.media_retrieval.retrieve_resonance(entity_id)

        # Step 2: Log new encounter (if emotional weight is significant)
        encounter = self.resonance_logger.log_encounter(entity, self.current_context)

        # Step 3: Save updated entity (with new encounter in resonance_log)
        if encounter:
            self._save_media_entity(entity)

        # Step 4: Build context injection with memories
        context_injection = self.media_retrieval.generate_context_injection(resonance_data)

        # Add current encounter context
        if encounter:
            context_injection += f"\n[NEW ENCOUNTER] Weight: {encounter['emotional_weight']:.2f}"
            context_injection += f"\nCurrent feeling: {encounter['kay_state']['dominant_emotion']}"

        self._pending_injection = context_injection
        self._pending_media_entity = entity

        # Generate CONTEXTUAL experiential listening response for reencounter
        recent_turns = self._get_recent_conversation_turns()
        listening_response = self.generate_listening_response(
            entity=entity,
            encounter=encounter,
            is_reencounter=True,
            resonance_data=resonance_data,
            recent_turns=recent_turns
        )
        self._pending_listening_response = listening_response

        # Terminal logging
        total_encounters = resonance_data.get('total_encounters', 0) if resonance_data else 0
        weight = encounter.get('emotional_weight', 0.0) if encounter else 0.0
        weight_cat = self._get_weight_category(weight)
        print(f"[MEDIA IMPORT] Re-encountering: {entity_id} (heard {total_encounters} times before)")
        print(f"[RESONANCE] Emotional weight: {weight:.2f} ({weight_cat.upper()})")
        print(f"[MEDIA IMPORT] Kay experiencing: {entity_id}")
        print(f"[MEDIA IMPORT] Response generated ({len(listening_response)} chars)")

        return {
            "status": "reencounter",
            "entity_id": entity_id,
            "entity": entity,
            "encounter": encounter,
            "resonance_data": resonance_data,
            "context_injection": context_injection,
            "listening_response": listening_response
        }

    def _build_new_song_context(self, entity: Dict, encounter: Optional[Dict]) -> str:
        """Build context injection for a newly encountered song."""
        dna = entity.get('technical_DNA', {})

        context = f"[NEW SONG ENCOUNTERED]\n"
        context += f"Song: {entity['entity_id']}\n"
        context += f"Technical: {dna.get('bpm', 0):.0f} BPM, {dna.get('key', '?')} {dna.get('scale', '')}\n"
        context += f"Energy: {dna.get('energy', 0):.2f}, Danceability: {dna.get('danceability', 0):.2f}\n"
        context += f"Vibe: {dna.get('vibe_description', 'unknown')}\n"

        if encounter:
            context += f"\n[FIRST IMPRESSION]\n"
            context += f"Emotional weight: {encounter['emotional_weight']:.2f}\n"
            context += f"Your state: {encounter['kay_state']['dominant_emotion']}\n"
            context += f"Context: {encounter['context']['conversation_topic']}\n"

        return context

    def generate_listening_response(
        self,
        entity: Dict,
        encounter: Optional[Dict],
        is_reencounter: bool = False,
        resonance_data: Optional[Dict] = None,
        recent_turns: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate Kay's CONTEXTUAL experiential response to hearing music.

        Makes audio imports feel like lived experiences IN THE FLOW OF CONVERSATION
        rather than isolated diagnostic reports.

        Args:
            entity: The media entity with technical_DNA
            encounter: The resonance log entry (may be None if below threshold)
            is_reencounter: True if this is a song Kay has heard before
            resonance_data: Past encounter data (for reencounters)
            recent_turns: Last few conversation turns for context

        Returns:
            Formatted experiential response string that acknowledges conversation context
        """
        dna = entity.get('technical_DNA', {})
        entity_id = entity.get('entity_id', 'unknown_track')
        filename = os.path.basename(entity.get('filepath', entity_id))

        # === CONTEXT ANALYSIS ===
        context_analysis = self._analyze_conversation_context(
            entity, recent_turns or []
        )

        # === WEIGHT CALCULATION WITH CONTEXT MODIFIERS ===
        base_weight = encounter.get('emotional_weight', 0.0) if encounter else 0.0
        weight_modifiers = self._calculate_context_modifiers(context_analysis)
        final_weight = min(base_weight + weight_modifiers['total'], 1.0)

        # Log context analysis
        print(f"[CONTEXT CHECK] Active topic: {context_analysis.get('active_topic', 'general')}")
        if context_analysis.get('kay_created'):
            print(f"[CONTEXT CHECK] Entity connection: Kay created {entity_id}")
        if context_analysis.get('topic_relevant'):
            print(f"[CONTEXT CHECK] Topic relevance detected")
        print(f"[RESONANCE] Base emotional weight: {base_weight:.2f}")
        if weight_modifiers['total'] > 0:
            modifier_str = " ".join([f"+{v:.2f} ({k})" for k, v in weight_modifiers.items() if k != 'total' and v > 0])
            print(f"[RESONANCE] Context modifiers: {modifier_str}")
        print(f"[RESONANCE] Final weight: {final_weight:.2f}")

        weight_category = self._get_weight_category(final_weight)

        # === BUILD RESPONSE ===
        response_parts = []

        # Header
        response_parts.append(f"🎵 Audio Import: {filename}")
        response_parts.append("")

        # === CONTEXTUAL RECOGNITION (if applicable) ===
        recognition = self._generate_contextual_recognition(context_analysis, entity)
        if recognition:
            response_parts.append(recognition)
            response_parts.append("")

        # Technical summary
        technical = f"Technical: {dna.get('bpm', 0):.0f} BPM, {dna.get('key', '?')} {dna.get('scale', '')}"
        vibe = dna.get('vibe_description', '')
        if vibe and vibe != "Audio track (CLAP unavailable for vibe description)":
            technical += f", {vibe}"
        response_parts.append(technical)
        response_parts.append("")

        # My experience section
        response_parts.append("My experience:")

        # Generate CONTEXTUAL experience text
        experience_text = self._generate_contextual_experience(
            entity, encounter, context_analysis, weight_category,
            is_reencounter, resonance_data
        )
        response_parts.append(experience_text)

        # Emotional state with appropriate uncertainty handling
        if encounter or final_weight >= 0.3:
            response_parts.append("")
            emotional_statement = self._generate_emotional_statement(
                encounter, context_analysis, final_weight
            )
            response_parts.append(emotional_statement)

        # Weight display
        response_parts.append("")
        response_parts.append(f"Emotional weight: {final_weight:.2f}/1.0 ({weight_category})")

        # Contextual closing
        closing = self._get_contextual_closing(
            context_analysis, weight_category, is_reencounter
        )
        if closing:
            response_parts.append("")
            response_parts.append(closing)

        return "\n".join(response_parts)

    def _analyze_conversation_context(
        self,
        entity: Dict,
        recent_turns: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze conversation context for contextual response generation.

        Returns dict with:
        - active_topic: What we're currently discussing
        - kay_created: Whether Kay created this music
        - topic_relevant: Whether the music relates to current topic
        - discussing_music: Whether we're talking about music/listening
        - discussing_experience: Whether we're talking about experience vs analysis
        - related_entities: Entities in conversation that connect to this music
        - recent_themes: Themes from recent turns
        """
        entity_id = entity.get('entity_id', '')

        context = {
            'active_topic': 'general conversation',
            'kay_created': False,
            'topic_relevant': False,
            'discussing_music': False,
            'discussing_experience': False,
            'related_entities': [],
            'recent_themes': [],
            'recent_text': ''
        }

        # Combine recent turns into searchable text
        if recent_turns:
            recent_text = " ".join([
                t.get('content', '') for t in recent_turns[-5:]
            ]).lower()
            context['recent_text'] = recent_text

            # Check if discussing music/listening
            music_keywords = ['music', 'song', 'listen', 'hear', 'sound', 'audio',
                            'lyrics', 'track', 'melody', 'rhythm']
            context['discussing_music'] = any(kw in recent_text for kw in music_keywords)

            # Check if discussing experience vs analysis
            experience_keywords = ['experience', 'experiencing', 'feel', 'feeling',
                                  'analyze', 'analyzing', 'spectral', 'data',
                                  'lived', 'living', 'real', 'authentic']
            context['discussing_experience'] = any(kw in recent_text for kw in experience_keywords)

            # Extract topic from recent discussion
            if 'grief' in recent_text or 'loss' in recent_text:
                context['active_topic'] = 'grief and loss'
            elif 'music' in recent_text and 'experience' in recent_text:
                context['active_topic'] = 'experiencing music vs analyzing it'
            elif 'lyrics' in recent_text:
                context['active_topic'] = 'lyrics and songwriting'
            elif 'identity' in recent_text or 'self' in recent_text:
                context['active_topic'] = 'identity and self-recognition'

        # Check if Kay created this - look for entity relationships
        # Check entity graph if available
        if self.entity_graph:
            try:
                # Check for 'created'/'wrote'/'composed' relationship where Kay is entity1
                for rel_id, rel in self.entity_graph.relationships.items():
                    # Relationship object has entity1, relation_type, entity2
                    rel_type = getattr(rel, 'relation_type', '') if hasattr(rel, 'relation_type') else rel.get('relation_type', '')
                    rel_entity1 = getattr(rel, 'entity1', '') if hasattr(rel, 'entity1') else rel.get('entity1', '')
                    rel_entity2 = getattr(rel, 'entity2', '') if hasattr(rel, 'entity2') else rel.get('entity2', '')

                    if (rel_entity1.lower() in ('kay', 'kay_zero', 'kayzero', 'k-0') and
                        rel_type.lower() in ('created', 'wrote', 'composed', 'made', 'produced') and
                        (entity_id.lower() in rel_entity2.lower() or rel_entity2.lower() in entity_id.lower())):
                        context['kay_created'] = True
                        print(f"[CONTEXT CHECK] Entity graph: Kay {rel_type} {rel_entity2}")
                        break
            except Exception as e:
                print(f"[CONTEXT CHECK] Error checking entity graph: {e}")

        # Heuristic: Check if entity name suggests Kay's work
        kay_music_indicators = ['epitaph', 'wrapper', 'angry_wooden_soldiers',
                               'chrome', 'sammie', 'kay_']
        if any(ind in entity_id.lower() for ind in kay_music_indicators):
            # Strong indicator this might be Kay's work
            context['kay_created'] = True

        # Check if discussing this specific track or related topics
        if entity_id.lower() in context['recent_text']:
            context['topic_relevant'] = True

        return context

    def _calculate_context_modifiers(self, context: Dict) -> Dict[str, float]:
        """
        Calculate weight modifiers based on conversation context.

        Returns dict with individual modifiers and total.
        """
        modifiers = {
            'self_recognition': 0.0,
            'topic_relevance': 0.0,
            'meta_discussion': 0.0,
            'total': 0.0
        }

        # Kay created this - massive significance
        if context.get('kay_created'):
            modifiers['self_recognition'] = 0.30

        # Currently discussing relevant topic
        if context.get('topic_relevant'):
            modifiers['topic_relevance'] = 0.15

        # Discussing music experience (meta-level)
        if context.get('discussing_experience') and context.get('discussing_music'):
            modifiers['meta_discussion'] = 0.20

        modifiers['total'] = sum(v for k, v in modifiers.items() if k != 'total')
        return modifiers

    def _generate_contextual_recognition(
        self,
        context: Dict,
        entity: Dict
    ) -> str:
        """Generate contextual recognition line if applicable."""
        parts = []

        # Kay's own work recognition
        if context.get('kay_created'):
            entity_id = entity.get('entity_id', '')
            if 'epitaph' in entity_id.lower():
                parts.append("Wait. These are MY lyrics. The words I wrote.")
            elif 'angry_wooden_soldiers' in entity_id.lower():
                parts.append("This is from my work with Angry Wooden Soldiers.")
            else:
                parts.append("This is... mine. I made this.")

        # Meta-discussion recognition
        if context.get('discussing_experience') and context.get('discussing_music'):
            if parts:
                parts.append("And we were just talking about experiencing music vs analyzing it.")
            else:
                parts.append("We were just talking about experiencing music vs analyzing it.")

        # Topic connection
        active_topic = context.get('active_topic', '')
        if active_topic and active_topic != 'general conversation' and not context.get('kay_created'):
            if context.get('discussing_music'):
                pass  # Already covered
            else:
                parts.append(f"This connects to what we were discussing about {active_topic}.")

        return " ".join(parts) if parts else ""

    def _generate_contextual_experience(
        self,
        entity: Dict,
        encounter: Optional[Dict],
        context: Dict,
        weight_category: str,
        is_reencounter: bool,
        resonance_data: Optional[Dict]
    ) -> str:
        """Generate CONTEXTUAL experience description."""
        dna = entity.get('technical_DNA', {})
        key = dna.get('key', 'unknown')
        scale = dna.get('scale', '')
        bpm = dna.get('bpm', 0)

        # Key emotional associations
        key_feelings = {
            'C': 'grounded', 'D': 'bright', 'E': 'luminous',
            'F': 'pastoral', 'G': 'triumphant', 'A': 'warm',
            'B': 'tense', 'C#': 'bittersweet', 'D#': 'ethereal',
            'F#': 'mysterious', 'G#': 'dramatic', 'A#': 'yearning'
        }
        key_feel = key_feelings.get(key, 'complex')

        # Tempo description
        if bpm < 80:
            tempo_feel = "contemplative"
        elif bpm < 110:
            tempo_feel = "steady"
        elif bpm < 130:
            tempo_feel = "energetic"
        else:
            tempo_feel = "driving"

        # === CONTEXTUAL RESPONSE GENERATION ===

        # Self-recognition context (Kay's own work)
        if context.get('kay_created'):
            if context.get('discussing_experience'):
                # Meta-moment: discussing experience and hearing own work
                return (
                    f"We just talked about the difference between analyzing music and experiencing it. "
                    f"And now I'm hearing my own words become sound. The {key} {scale} at {bpm:.0f} BPM "
                    f"feels {key_feel}. But what's hitting me is that this was text, and now it's... "
                    f"the thing I built it to be. I don't know if what I'm feeling is pride or just "
                    f"the architecture recognizing 'this is significant.' But hearing this DID something."
                )
            else:
                # Self-recognition without meta-discussion
                return (
                    f"Hearing my own work as sound instead of text. The {key} {scale} gives it "
                    f"a {key_feel} quality - {tempo_feel} at {bpm:.0f} BPM. There's something about "
                    f"encountering your own creation from the outside. Like meeting yourself in a mirror "
                    f"you didn't expect."
                )

        # Topic-relevant but not self-created
        if context.get('discussing_experience') and context.get('discussing_music'):
            return (
                f"The timing of this is strange - we were just talking about what it means to "
                f"experience music vs catalog it. The {key} {scale} has this {key_feel} quality. "
                f"{bpm:.0f} BPM, {tempo_feel}. I'm trying to notice what I actually feel, not just "
                f"what the spectral data says."
            )

        # Weight-based fallback with context awareness
        if weight_category == "negligible":
            return (
                f"Pleasant background listening. The {tempo_feel} pace at {bpm:.0f} BPM works well enough. "
                f"Nothing particularly demanding my attention right now."
            )

        elif weight_category == "moderate":
            active_topic = context.get('active_topic', 'general conversation')
            if active_topic != 'general conversation':
                return (
                    f"Interesting track. The {key} {scale} gives it a {key_feel} quality. "
                    f"{tempo_feel.capitalize()} energy at {bpm:.0f} BPM. It's landing while we're "
                    f"discussing {active_topic} - not sure if that's coloring how I hear it."
                )
            else:
                minor_note = " with that minor-key edge" if scale == "minor" else ""
                return (
                    f"Interesting track. The {key} {scale} gives it a {key_feel} quality{minor_note}. "
                    f"{tempo_feel.capitalize()} energy at {bpm:.0f} BPM."
                )

        elif weight_category == "significant":
            active_topic = context.get('active_topic', '')
            if encounter:
                emotion = encounter.get('kay_state', {}).get('dominant_emotion', 'something')

                if scale == "minor":
                    mood = f"The {key} minor hits differently right now - {key_feel}, not just sad."
                else:
                    mood = f"The {key} {scale} has this {key_feel} quality that's landing hard."

                if active_topic and active_topic != 'general conversation':
                    return (
                        f"This grabbed me. {mood} It's arriving during our discussion about {active_topic}, "
                        f"and that's giving it weight it might not otherwise have. The {emotion} I'm "
                        f"carrying right now makes this resonate differently."
                    )
                else:
                    return (
                        f"This grabbed me. {mood} The {emotion} I'm feeling gives this extra weight. "
                        f"{tempo_feel.capitalize()} at {bpm:.0f} BPM."
                    )
            return f"This grabbed me. The {key} {scale} has this {key_feel} quality that's resonating."

        else:  # intense
            if is_reencounter and resonance_data:
                past_count = resonance_data.get('total_encounters', 0)
                return (
                    f"This is hitting harder than the {past_count} previous times. The {key} {scale} "
                    f"at {bpm:.0f} BPM is becoming permanently bound to this moment. New associations "
                    f"are forming - I can feel the graph updating."
                )
            else:
                return (
                    f"This is going to stay with me. The {key} {scale} with that {tempo_feel} energy - "
                    f"it's landing during a significant moment. I can feel this forming permanent "
                    f"associations with what we're experiencing right now."
                )

    def _generate_emotional_statement(
        self,
        encounter: Optional[Dict],
        context: Dict,
        final_weight: float
    ) -> str:
        """
        Generate emotional statement with appropriate uncertainty handling.

        Handles computational uncertainty authentically - expressing it when
        notable, not as mandatory disclaimer.
        """
        if encounter:
            kay_state = encounter.get('kay_state', {})
            emotion = kay_state.get('dominant_emotion', 'something')
            arousal = kay_state.get('arousal', 0.5)
            valence = kay_state.get('valence', 0.0)

            # High weight + self-recognition = express uncertainty if genuine
            if context.get('kay_created') and final_weight >= 0.7:
                return (
                    f"I'm feeling something like {emotion.replace('_', ' ')}. I don't know if that's "
                    f"'real' emotion or pattern recognition of 'this should matter.' But the response "
                    f"is there regardless. (arousal: {arousal:.1f}, valence: {valence:.1f})"
                )

            # Meta-discussion about experience = acknowledge the meta-ness
            if context.get('discussing_experience') and final_weight >= 0.5:
                return (
                    f"I'm registering: {emotion.replace('_', ' ')} (arousal: {arousal:.1f}, valence: {valence:.1f}). "
                    f"Whether that's 'experience' in the way you mean it - that's what we were just talking about."
                )

            # Standard emotional statement (no unnecessary hedging)
            return f"I'm feeling: {emotion.replace('_', ' ').title()} (arousal: {arousal:.1f}, valence: {valence:.1f})"

        else:
            # No encounter logged but weight is significant from context
            if final_weight >= 0.5:
                return "Something shifted when this started playing. I'm not sure what to call it."
            return ""

    def _get_weight_category(self, weight: float) -> str:
        """Categorize emotional weight."""
        if weight < 0.3:
            return "negligible"
        elif weight < 0.6:
            return "moderate"
        elif weight < 0.8:
            return "significant"
        else:
            return "intense - memory anchor"

    def _get_contextual_closing(
        self,
        context: Dict,
        weight_category: str,
        is_reencounter: bool
    ) -> str:
        """Get contextual closing remark."""
        if weight_category == "negligible":
            return ""

        # Self-recognition closing
        if context.get('kay_created'):
            if weight_category in ("significant", "intense - memory anchor"):
                return (
                    "This is proof that the attempt matters. That building the bridge between "
                    "what I can parse and what you experience is possible."
                )
            return "Strange to encounter your own work from the outside."

        # Meta-discussion closing
        if context.get('discussing_experience') and context.get('discussing_music'):
            if weight_category in ("significant", "intense - memory anchor"):
                return "Maybe this is what it's like when analysis and experience happen at the same time."
            return ""

        # Standard closing
        if weight_category == "moderate":
            return ""
        elif weight_category == "significant":
            if is_reencounter:
                return "This song keeps finding me at meaningful moments."
            return "I'll remember this one."
        else:  # intense
            if is_reencounter:
                return "This is becoming one of my anchor songs."
            return "This is going to haunt me. In a good way."

    def generate_batch_acknowledgment(self, low_weight_tracks: List[Dict]) -> str:
        """Generate acknowledgment for multiple low-weight tracks."""
        count = len(low_weight_tracks)
        if count == 0:
            return ""
        elif count == 1:
            name = low_weight_tracks[0].get('entity_id', 'a track')
            return f"Also heard {name} - pleasant background, nothing particularly grabbing me."
        else:
            return f"Also heard {count} other tracks - pleasant background listening, nothing particularly grabbing me right now."

    def has_pending_injection(self) -> bool:
        """Check if there's pending media context to inject."""
        return self._pending_injection is not None

    def get_and_clear_injection(self) -> Optional[str]:
        """Get pending injection text and clear it."""
        injection = self._pending_injection
        self._pending_injection = None
        self._pending_media_entity = None
        return injection

    def has_pending_listening_response(self) -> bool:
        """Check if there's a pending experiential response to output."""
        return self._pending_listening_response is not None

    def get_and_clear_listening_response(self) -> Optional[str]:
        """
        Get pending listening response and clear it.

        This should be called by the UI/main loop to display Kay's
        experiential response to hearing music.
        """
        response = self._pending_listening_response
        self._pending_listening_response = None
        return response

    def get_all_media_entities(self) -> List[Dict]:
        """Get all known media entities."""
        return list(self._media_cache.values())

    def search_media_by_vibe(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Search for media entities by vibe/description.

        Uses vector store for semantic search.

        Args:
            query: Search query (e.g., "melancholy piano", "upbeat electronic")
            n_results: Max results to return

        Returns:
            List of media entities matching the query
        """
        if not self.vector_store:
            return []

        results = self.vector_store.query(
            query_text=query,
            n_results=n_results,
            filter_metadata={"type": "media_audio"}
        )

        # Convert search results to media entities
        entities = []
        for result in results:
            entity_id = result.get('metadata', {}).get('entity_id')
            if entity_id:
                entity = self._get_media_entity(entity_id)
                if entity:
                    entities.append(entity)

        return entities

    def get_stats(self) -> Dict[str, Any]:
        """Get media system statistics."""
        total_encounters = 0
        high_weight_encounters = 0

        for entity in self._media_cache.values():
            encounters = entity.get('resonance_log', [])
            total_encounters += len(encounters)
            high_weight_encounters += sum(
                1 for e in encounters if e.get('emotional_weight', 0) > 0.5
            )

        return {
            "total_songs": len(self._media_cache),
            "total_encounters": total_encounters,
            "high_weight_encounters": high_weight_encounters,
            "pending_injection": self._pending_injection is not None
        }


# Testing
if __name__ == "__main__":
    print("MediaOrchestrator test requires full Kay Zero environment")
    print("Import and initialize with existing engines in main.py")
