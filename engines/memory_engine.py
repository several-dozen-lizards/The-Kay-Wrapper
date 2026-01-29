# engines/memory_engine.py
import json
import math
import os
import re
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from engines.preference_tracker import PreferenceTracker
from engines.entity_graph import EntityGraph
from engines.memory_layers import MemoryLayerManager
from engines.identity_memory import IdentityMemory, IdentitySourceType
from engines.memory_layer_rebalancing import (
    apply_layer_weights,
    get_layer_multiplier,
    should_store_claim,
    create_entity_observation,
    validate_memory_composition
)
from utils.performance import measure_performance
from config import VERBOSE_DEBUG
# DEPRECATED: Old complex document index with entity extraction
# from engines.document_index import DocumentIndex

# NEW: Simple LLM-based document selection
from engines.llm_retrieval import select_relevant_documents, load_full_documents

# Import LLM for fact extraction
try:
    from integrations.llm_integration import client, MODEL
except ImportError:
    client = None
    MODEL = None


# ===== TEMPORAL FACT VERSIONING SYSTEM =====
"""
VERSIONED FACT STRUCTURE:

Instead of storing duplicate facts (e.g., "Saga is orange" 38 times),
we store each fact ONCE with version history:

{
    'fact': 'Saga has color = orange',
    'entity': 'Saga',
    'attribute': 'color',
    'current_value': 'orange',
    'created_at': '2025-11-17T12:00:00Z',
    'last_confirmed': '2025-11-17T14:30:00Z',
    'version': 1,
    'history': [],  # Empty if never changed
    # ... other fields
}

When value changes:
{
    'current_value': 'brown',  # New value
    'version': 2,
    'history': [
        {
            'value': 'orange',
            'valid_from': '2025-11-17T12:00:00Z',
            'valid_until': '2025-11-17T14:30:00Z',
            'turn': 10
        }
    ]
}

Benefits:
- No duplicates (38 facts → 1 fact)
- No contradiction resolution needed (current_value is authoritative)
- Temporal awareness (Kay knows when facts changed)
- Memory savings (50-70% reduction)
"""

def find_existing_fact(new_fact: Dict, all_memories: List[Dict]) -> Optional[Dict]:
    """
    Find if a semantically identical fact already exists.

    Args:
        new_fact: Dict with 'entity', 'attribute'
        all_memories: List of all stored memories

    Returns:
        Existing fact dict if found, None otherwise
    """
    entity = new_fact.get('entity')
    attribute = new_fact.get('attribute')

    if not entity or not attribute:
        return None

    # Search for matching entity + attribute
    for mem in all_memories:
        if (mem.get('entity') == entity and
            mem.get('attribute') == attribute and
            mem.get('type') == 'extracted_fact'):
            return mem

    return None


def should_update_fact(existing_fact: Optional[Dict], new_value: Any) -> str:
    """
    Determine if a fact needs updating.

    Returns:
        'skip': Same value, just update last_confirmed
        'amend': Different value, create history entry
        'new': No existing fact, create new
    """
    if not existing_fact:
        return 'new'

    current_value = existing_fact.get('current_value')

    # Same value - just confirm it's still true
    if current_value == new_value:
        return 'skip'

    # Different value - needs amendment
    return 'amend'


def amend_fact(existing_fact: Dict, new_value: Any, turn_count: int) -> Dict:
    """
    Create a history entry and update current value.

    Args:
        existing_fact: The fact dict to amend
        new_value: New value for this attribute
        turn_count: Current turn number

    Returns:
        Updated fact dict
    """
    now = datetime.now(timezone.utc).isoformat()

    # Initialize history if it doesn't exist
    if 'history' not in existing_fact:
        existing_fact['history'] = []

    # Add current value to history (it's now the "old" value)
    old_entry = {
        'value': existing_fact.get('current_value'),
        'valid_from': existing_fact.get('created_at', now),
        'valid_until': now,
        'turn': existing_fact.get('parent_turn', 0)
    }
    existing_fact['history'].append(old_entry)

    # Update to new value
    existing_fact['current_value'] = new_value
    existing_fact['last_confirmed'] = now
    existing_fact['version'] = existing_fact.get('version', 1) + 1
    existing_fact['parent_turn'] = turn_count

    # Update human-readable fact string
    entity = existing_fact.get('entity', '')
    attribute = existing_fact.get('attribute', '')
    existing_fact['fact'] = f"{entity} has {attribute} = {new_value}"

    print(f"[FACT AMENDED] {entity}.{attribute}: {old_entry['value']} -> {new_value} (version {existing_fact['version']})")

    return existing_fact


def confirm_fact(existing_fact: Dict) -> Dict:
    """
    Update last_confirmed timestamp for unchanged fact.
    """
    now = datetime.now(timezone.utc).isoformat()
    existing_fact['last_confirmed'] = now

    entity = existing_fact.get('entity', '')
    attribute = existing_fact.get('attribute', '')

    # Only log if VERBOSE_DEBUG (reduce noise)
    if VERBOSE_DEBUG:
        print(f"[FACT CONFIRMED] {entity}.{attribute} = {existing_fact.get('current_value')} (unchanged)")

    return existing_fact


class MemoryEngine:
    """
    Handles both storage and cognitive use of memory, with on-disk persistence,
    emotional tagging, perspective tagging ("user", "kay", or "shared"),
    motif-based weighting, entity resolution, and multi-layer memory system.

    NEW FEATURES:
    - Entity resolution: Links mentions to canonical entities with attribute tracking
    - Multi-layer memory: Working → Episodic → Semantic transitions
    - Multi-factor retrieval: Combines emotional, semantic, importance, recency, entity proximity
    - ULTRAMAP-based importance: Uses pressure × recursion for memory persistence
    - TWO-TIER storage: Episodic (full_turn) + Semantic (extracted_fact)
    - IDENTITY MEMORY: Permanent facts that never decay
    """

    def __init__(self, semantic_memory: Optional[Any] = None, file_path: str = "memory/memories.json", motif_engine: Optional[Any] = None, momentum_engine: Optional[Any] = None, emotion_engine: Optional[Any] = None, vector_store: Optional[Any] = None):
        self.semantic_memory = semantic_memory
        self.file_path = file_path
        self.motif_engine = motif_engine
        self.momentum_engine = momentum_engine
        self.emotion_engine = emotion_engine  # NEW: For ULTRAMAP rule queries
        self.preference_tracker = PreferenceTracker()

        # SESSION CONTEXT TRACKING - for RAG temporal tagging
        self.current_session_order = None
        self.current_session_id = None

        # DEPRECATED: Old complex document index with entity extraction
        # self.document_index = DocumentIndex()
        # NOW: Use llm_retrieval functions instead (select_relevant_documents, load_full_documents)

        # NEW: Entity resolution and multi-layer memory
        self.entity_graph = EntityGraph()
        self.memory_layers = MemoryLayerManager()

        # NEW: Identity memory system (permanent facts)
        self.identity = IdentityMemory()
        print(f"[MEMORY] Identity memory initialized: {self.identity.get_summary()}")

        # NEW: Vector store for RAG (hybrid memory system)
        self.vector_store = vector_store
        self.last_rag_chunks = []  # NEW: Store last RAG retrieval for context building
        if vector_store:
            print(f"[MEMORY] RAG enabled: Vector store connected ({vector_store.get_stats()['total_chunks']} chunks)")

        # NEW: Semantic usage tracking (for cost optimization analysis)
        self._semantic_extraction_warned = False  # Track if we've warned about unused semantic facts

        # Track current turn for recency calculations
        self.current_turn = 0

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.memories: List[Dict[str, Any]] = json.load(f)
        except Exception:
            self.memories = []

        self.facts = [m.get("response") or m.get("user_input") for m in self.memories if m]

    def set_session_context(self, session_order: int, session_id: str):
        """
        Update current session context for memory tagging.
        
        Args:
            session_order: Sequential session number (e.g., 1, 2, 3...)
            session_id: Unique session identifier (timestamp-based)
        """
        self.current_session_order = session_order
        self.current_session_id = session_id
        print(f"[MEMORY] Session context set: #{session_order} ({session_id})")

    def _save_to_disk(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, indent=2)

    def increment_memory_ages(self):
        """
        Increment age of all memories by 1 turn.

        NEW: Required for protected import pipeline.
        Call this at the END of each conversation turn.

        Protected imported facts lose protection after 3 turns (age >= 3).
        """
        aged_count = 0
        unprotected_count = 0

        for mem in self.memories:
            # Only increment if age field exists
            if "age" in mem:
                mem["age"] += 1
                aged_count += 1

                # Unprotect facts older than 3 turns
                if mem.get("protected") and mem.get("age", 0) >= 3:
                    mem["protected"] = False
                    unprotected_count += 1

        if aged_count > 0:
            print(f"[MEMORY] Aged {aged_count} memories (+1 turn), unprotected {unprotected_count} old imports")

    def _calculate_fact_importance(self, fact_data: Dict, emotional_cocktail: Dict = None) -> float:
        """Calculate importance score for an extracted fact."""
        # Base importance
        importance = 0.5

        # Boost for certain topics
        topic = fact_data.get("topic", "")
        if topic in ["appearance", "identity", "relationships", "family", "pets"]:
            importance += 0.2

        # Boost for multiple entities (part of a list)
        entity_count = len(fact_data.get("entities", []))
        if entity_count > 1:
            importance += 0.1 * entity_count

        # Emotional intensity boost
        if emotional_cocktail:
            avg_intensity = sum(e.get("intensity", 0) for e in emotional_cocktail.values()) / max(len(emotional_cocktail), 1)
            importance += avg_intensity * 0.2

        return min(importance, 1.0)

    def _calculate_turn_importance(self, emotional_cocktail: Dict, emotion_tags: List[str], entity_count: int) -> float:
        """Calculate importance score for a full conversation turn."""
        # Base importance
        importance = 0.5

        # Strong boost for lists (3+ entities)
        if entity_count >= 3:
            importance = 0.9
            print(f"[MEMORY] List detected ({entity_count} entities) - importance boosted to {importance}")

        # Emotional intensity boost
        if emotional_cocktail:
            avg_intensity = sum(e.get("intensity", 0) for e in emotional_cocktail.values()) / max(len(emotional_cocktail), 1)
            importance += avg_intensity * 0.1

        return min(importance, 1.0)

    def _extract_entities_simple(self, text: str) -> List[str]:
        """
        Simple entity extraction fallback when LLM fails.
        Looks for capitalized words but filters out common words.
        """
        # Comprehensive stop words to exclude
        stop_words = {
            # Pronouns & common words
            'i', 'my', 'your', 'the', 'and', 'are', 'is', 'it', 'this', 'that',
            'these', 'those', 'we', 'you', 'they', 'he', 'she', 'him', 'her',
            # Sentence starters & fillers
            'yeah', 'yes', 'no', 'okay', 'ok', 'well', 'so', 'but', 'or', 'if',
            'when', 'where', 'what', 'how', 'why', 'who', 'which', 'do', 'did',
            # Contractions (base forms)
            "i'm", "i've", "i'd", "it's", "that's", "there's", "here's",
            # Intensity words
            'still', 'very', 'really', 'just', 'now', 'then', 'also',
            # Common verbs as sentence starters
            'got', 'get', 'have', 'has', 'had', 'was', 'were', 'been', 'being',
            # Generic words
            'human', 'ai', 'thing', 'things', 'stuff', 'one', 'two', 'three'
        }

        entities = []
        words = text.split()

        for word in words:
            clean_word = word.strip('.,!?;:()"\'')
            # Capitalized and not in stop words
            if (clean_word and
                clean_word[0].isupper() and
                len(clean_word) > 1 and
                clean_word.lower() not in stop_words):
                entities.append(clean_word)

        return entities

    def retrieve_biased_memories(self, bias_cocktail, user_input, num_memories: int = 7, relevance_floor: float = 0.3):
        if not self.memories:
            return []

        search_words = set(re.findall(r"\w+", user_input.lower()))
        if not search_words:
            return []

        # Get all user corrections to check memories against
        user_corrections = self.entity_graph.get_all_corrections() if self.entity_graph else []

        def _memory_contains_corrected_value(mem, corrections):
            """Check if a memory contains a value that was corrected by the user."""
            if not corrections:
                return None

            fact_text = mem.get("fact", "").lower()
            context_text = (mem.get("user_input", "") + " " + mem.get("response", "")).lower()
            full_text = fact_text + " " + context_text

            for correction in corrections:
                wrong_value = str(correction.get("wrong_value", "")).lower()
                if wrong_value and wrong_value in full_text:
                    # Check if the memory ALSO contains the correct value (then it's fine)
                    correct_value = str(correction.get("correct_value", "")).lower()
                    if correct_value and correct_value in full_text:
                        continue  # Has both values, likely updated - OK
                    return correction
            return None

        def score_and_filter(mem):
            tags = mem.get("emotion_tags") or []
            emotion_score = sum(bias_cocktail.get(tag, {}).get("intensity", 0.0) for tag in tags)

            # Search in the discrete fact field (primary) + original context (secondary)
            fact_text = mem.get("fact", "")
            context_text = (mem.get("user_input", "") + " " + mem.get("response", ""))
            text_blob = (fact_text + " " + context_text).lower()

            text_score = sum(1 for w in search_words if w in text_blob)

            # Calculate keyword overlap ratio
            keyword_overlap = text_score / len(search_words) if search_words else 0.0

            # FIX #1: Recency exemption for keyword overlap threshold
            # Recent memories (last 5 turns) don't get killed by low keyword overlap
            turns_old = self.current_turn - mem.get("turn_index", 0)
            is_recent = turns_old <= 5

            # Filter: require minimum keyword overlap, BUT exempt recent memories
            if keyword_overlap < relevance_floor:
                if not is_recent:
                    # Non-recent low-overlap memory: kill it
                    return None
                else:
                    # Recent but low overlap: boost to minimum threshold instead of killing
                    # This ensures "What else?" after "Tell me about Saga" still surfaces Saga facts
                    keyword_overlap = max(keyword_overlap, 0.3)

            # Add motif scoring if motif engine is available
            motif_score = 0.0
            if self.motif_engine:
                # Score based on fact + original context
                memory_text = fact_text + " " + context_text
                motif_score = self.motif_engine.score_memory_by_motifs(memory_text)

            # Add momentum boost for high-momentum motifs
            momentum_boost = 0.0
            if self.momentum_engine:
                high_momentum_motifs = self.momentum_engine.get_high_momentum_motifs()
                memory_text_lower = (fact_text + " " + context_text).lower()
                for hm_motif in high_momentum_motifs:
                    if hm_motif in memory_text_lower:
                        momentum_boost += 0.5  # Significant boost for momentum-relevant memories

            # FIX #1 ENHANCEMENT: Add recency boost to scoring
            # Recent memories should score HIGHER than old memories, not just avoid being killed
            recency_boost = 0.0
            if is_recent:
                if turns_old <= 2:
                    recency_boost = 10.0  # VERY recent (last 2 turns) - massive priority
                elif turns_old <= 5:
                    recency_boost = 5.0   # Recent (last 5 turns) - high priority
                print(f"[RECENCY BOOST] Memory from {turns_old} turns ago gets +{recency_boost} score boost")

            # USER CORRECTION CHECK: Heavily penalize memories containing corrected values
            correction_penalty = 0.0
            correction_info = _memory_contains_corrected_value(mem, user_corrections)
            if correction_info:
                # This memory contains a value the user corrected - severely deprioritize it
                correction_penalty = -50.0  # Large negative score
                print(f"[CORRECTION FILTER] Penalizing memory with corrected value '{correction_info.get('wrong_value')}' -> '{correction_info.get('correct_value')}'")

            # Combined score: emotion + keyword + motif + momentum + RECENCY - CORRECTION PENALTY
            total_score = emotion_score + text_score * 0.5 + motif_score * 0.8 + momentum_boost + recency_boost + correction_penalty
            return (total_score, mem)

        # Score all memories and filter out None results
        scored = [result for result in (score_and_filter(m) for m in self.memories) if result is not None]

        # EDGE CASE FIX: Always include identity layer memories regardless of keyword overlap
        # This ensures Kay never loses his core identity facts even with zero keyword overlap
        # BUT: Still check for user corrections on identity memories!
        identity_memories = [
            mem for mem in self.memories
            if mem.get("layer") == "identity"
        ]
        # Add identity memories with very high score (100.0) if not already in scored list
        # UNLESS they contain a corrected value - then penalize them
        scored_mem_ids = set(id(mem) for _, mem in scored)
        for identity_mem in identity_memories:
            if id(identity_mem) not in scored_mem_ids:
                # Check for corrections on identity memories too
                correction_info = _memory_contains_corrected_value(identity_mem, user_corrections)
                if correction_info:
                    # Identity memory with corrected value - lower priority but still include
                    scored.append((10.0, identity_mem))  # Reduced from 100.0 to 10.0
                    print(f"[CORRECTION FILTER] Deprioritized identity memory with corrected value '{correction_info.get('wrong_value')}'")
                else:
                    scored.append((100.0, identity_mem))

        # Sort by score and return top N memories
        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:num_memories]]

    def _extract_facts_with_entities(self, user_input: str, response: str) -> List[Dict[str, str]]:
        """
        Extract discrete facts with entity resolution.

        CRITICAL: If extraction fails, return FULL user_input (no truncation).
        """
        if not client or not MODEL:
            # Fallback: return FULL user_input as single fact (NO TRUNCATION)
            return [{
                "fact": user_input,  # COMPLETE, not truncated
                "perspective": self._detect_perspective(user_input),
                "topic": "conversation",
                "entities": self._extract_entities_simple(user_input),
                "attributes": [],
                "is_extraction_fallback": True
            }]

        # Build extraction prompt with entity detection
        extraction_prompt = f"""Extract ONLY the factual statements EXPLICITLY present in the input below.

USER INPUT: "{user_input}"
KAY'S RESPONSE: "{response}"

RULES:
1. Extract only factual statements, not questions or opinions
2. Each fact should be a complete, standalone statement
3. **CRITICAL FOR LISTS**: If user provides a list (e.g., "My cats are A, B, C, D, E"), extract:
   - ONE fact for the complete list: "Re has 5 cats: A, B, C, D, E"
   - SEPARATE facts for EACH item: "A is Re's cat", "B is Re's cat", etc.
   - DO NOT bundle everything into a single generic fact
4. Determine perspective for each fact:
   - "user" = facts about Re (the person typing)
   - "kay" = facts about Kay (the AI)
   - "shared" = facts about both or shared experiences
5. Categorize each fact by topic (appearance, identity, pets, relationships, events, goals, etc.)
   - Use "pets" for animal ownership
   - Use "appearance" for physical traits (eyes, hair, clothing)
   - Use "identity" for names
   - Use "goals" for desires, goals, fears, aspirations
6. Extract entities mentioned (people, places, things, pet names)
7. Extract attributes (entity properties like "eye_color", "species", "name", etc.)
8. **NEW: Detect desires, goals, fears, and aspirations**:
   - "I want X" → extract as desire attribute
   - "I'm trying to X" / "I need to X" → extract as goal attribute
   - "I hope X" / "I wish X" → extract as aspiration attribute
   - "I'm worried about X" / "I fear X" → extract as fear attribute
   - Track progression: "still not working", "making progress", "gave up" → goal_progression attribute

CRITICAL PERSPECTIVE RULES:
- Re is the USER (the person typing)
- Kay is the AI (being addressed)

FROM USER INPUT:
- "I/my/me" in user input = Re (user perspective)
- "you/your" in user input = Kay (kay perspective)
- Entities mentioned = Re's entities

FROM KAY'S RESPONSE:
- "your/you" in Kay's response = about Re (USER perspective, NOT Kay)
- "my/I/me" in Kay's response = about Kay ONLY if DIRECT SELF-ASSERTION
  - Direct self-assertion: "My eyes are gold", "I prefer coffee", "I am a dragon"
  - NOT self-assertion: "my memory says...", "my understanding...", "my cats - [known Re entities]"
- When Kay mentions entities that are known to belong to Re, DO NOT create Kay ownership
- Conversational references to Re's life = Re's facts, not Kay's facts

CRITICAL: When Kay says things like "your cats", "your dog", "you have", extract these as REINFORCING Re's ownership, NOT creating Kay ownership.

DOCUMENT/READING CONTEXT:
When conversation involves documents, files, or imported content:
- Kay READS documents, doesn't EXPERIENCE them
- "Kay examined Archive Zero" → WRONG (implies lived experience)
- "Kay read documents about Archive Zero" → CORRECT (reading activity)
- If Kay is reading about something, use: "Kay read about X", "Kay learned about X from document"
- Characters/events IN documents are NOT Kay's experiences - they are content Kay READ ABOUT
- Activity attributes for Kay + document content should use "reading" language, not "examining/exploring/investigating"

OUTPUT FORMAT (JSON array):

EXAMPLE 1 - User states ownership:
User: "My dog is Saga"
Kay: "That's a great name!"
→ Extract:
[
  {{
    "fact": "Saga is Re's dog",
    "perspective": "user",
    "topic": "pets",
    "entities": ["Saga", "Re"],
    "attributes": [{{"entity": "Saga", "attribute": "species", "value": "dog"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "Saga"}}]
  }}
]
Note: Kay's response "That's a great name!" contains NO factual claims, so nothing extracted from it.

EXAMPLE 2 - Kay makes conversational reference to Re's pets:
User: "My cats are Dice, Chrome, Luna"
Kay: "Your cats - Dice, Chrome, Luna - sound wonderful!"
→ Extract:
[
  {{
    "fact": "Re has 3 cats: Dice, Chrome, Luna",
    "perspective": "user",
    "topic": "pets",
    "entities": ["Re", "Dice", "Chrome", "Luna"],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "cats"}}]
  }},
  {{
    "fact": "Dice is Re's cat",
    "perspective": "user",
    "topic": "pets",
    "entities": ["Dice", "Re"],
    "attributes": [{{"entity": "Dice", "attribute": "species", "value": "cat"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "Dice"}}]
  }},
  {{
    "fact": "Chrome is Re's cat",
    "perspective": "user",
    "topic": "pets",
    "entities": ["Chrome", "Re"],
    "attributes": [{{"entity": "Chrome", "attribute": "species", "value": "cat"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "Chrome"}}]
  }},
  {{
    "fact": "Luna is Re's cat",
    "perspective": "user",
    "topic": "pets",
    "entities": ["Luna", "Re"],
    "attributes": [{{"entity": "Luna", "attribute": "species", "value": "cat"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "Luna"}}]
  }}
]
Note: Kay says "Your cats" - this is about Re's cats, NOT Kay's. Do NOT create "Kay owns X".

EXAMPLE 3 - Kay makes direct self-assertion:
User: "What color are your eyes?"
Kay: "My eyes are gold."
→ Extract:
[
  {{
    "fact": "Kay's eyes are gold",
    "perspective": "kay",
    "topic": "appearance",
    "entities": ["Kay"],
    "attributes": [{{"entity": "Kay", "attribute": "eye_color", "value": "gold"}}]
  }}
]
Note: This IS a direct self-assertion about Kay, so extract as kay perspective.

EXAMPLE 4 - Kay confused but describing Re's entities (DO NOT EXTRACT):
User: "My cats are Dice and Chrome"
Kay: "Yeah, my cats - Dice and Chrome - are great!"
→ Extract:
[
  {{
    "fact": "Dice is Re's cat",
    "perspective": "user",
    "topic": "pets",
    "entities": ["Dice", "Re"],
    "attributes": [{{"entity": "Dice", "attribute": "species", "value": "cat"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "Dice"}}]
  }},
  {{
    "fact": "Chrome is Re's cat",
    "perspective": "user",
    "topic": "pets",
    "entities": ["Chrome", "Re"],
    "attributes": [{{"entity": "Chrome", "attribute": "species", "value": "cat"}}],
    "relationships": [{{"entity1": "Re", "relation": "owns", "entity2": "Chrome"}}]
  }}
]
Note: Even though Kay says "my cats", the context shows these are Re's cats (user just stated it).
Do NOT create "Kay owns Dice/Chrome". Kay is confused/echoing. Only extract from user input.

EXAMPLE 5 - User expresses desire/goal:
User: "I want to fix this wrapper persistence issue"
Kay: "What have you tried so far?"
→ Extract:
[
  {{
    "fact": "Re desires to fix wrapper persistence",
    "perspective": "user",
    "topic": "goals",
    "entities": ["Re", "wrapper"],
    "attributes": [{{"entity": "Re", "attribute": "desire", "value": "fix wrapper persistence"}}, {{"entity": "Re", "attribute": "goal_status", "value": "active"}}]
  }}
]

EXAMPLE 6 - User expresses frustration (progression update):
User: "Still not working. Third approach failed."
Kay: "That's frustrating."
→ Extract:
[
  {{
    "fact": "Re's wrapper fix attempts are stuck (3 failures)",
    "perspective": "user",
    "topic": "goals",
    "entities": ["Re", "wrapper"],
    "attributes": [{{"entity": "Re", "attribute": "goal_progression", "value": "stuck"}}, {{"entity": "Re", "attribute": "attempt_count", "value": "3"}}]
  }}
]

EXAMPLE 7 - User expresses fear:
User: "I'm worried Chrome might get out through the broken window"
Kay: "That's a valid concern."
→ Extract:
[
  {{
    "fact": "Re fears Chrome escaping through broken window",
    "perspective": "user",
    "topic": "goals",
    "entities": ["Re", "Chrome", "window"],
    "attributes": [{{"entity": "Re", "attribute": "fear", "value": "Chrome escaping"}}, {{"entity": "window", "attribute": "condition", "value": "broken"}}]
  }}
]

EXAMPLE 8 - User CORRECTS Kay about a fact:
User: "No, those ChatGPT conversations were from 2024-2025, not 2020"
Kay: "Oh, you're right - I had the dates wrong."
→ Extract:
[
  {{
    "fact": "ChatGPT conversations occurred in 2024-2025",
    "perspective": "user",
    "topic": "events",
    "entities": ["ChatGPT conversations", "Zero"],
    "attributes": [{{"entity": "ChatGPT conversations", "attribute": "year", "value": "2024-2025"}}, {{"entity": "Zero", "attribute": "emergence_year", "value": "2024-2025"}}],
    "is_correction": true,
    "corrects": {{
      "entity": "Zero",
      "wrong_value": "2020",
      "correct_value": "2024-2025",
      "attribute_pattern": "year"
    }}
  }}
]
Note: When user says "not X" or "X is wrong", this is a CORRECTION. Mark is_correction=true and include the corrects block.

EXAMPLE 9 - User corrects Kay's mistake:
User: "Actually, Saga is 3 years old, not 5"
Kay: "Got it, my mistake."
→ Extract:
[
  {{
    "fact": "Saga is 3 years old",
    "perspective": "user",
    "topic": "pets",
    "entities": ["Saga"],
    "attributes": [{{"entity": "Saga", "attribute": "age", "value": "3"}}],
    "is_correction": true,
    "corrects": {{
      "entity": "Saga",
      "wrong_value": "5",
      "correct_value": "3",
      "attribute_pattern": "age"
    }}
  }}
]

If no facts are present, return: []

REMEMBER:
- Break down lists! Extract EACH item separately + one summary fact for the whole list.
- Detect CORRECTIONS when user says "not X", "actually X", "X is wrong", "you're wrong about X"

Extract facts now:"""

        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=1500,  # Increased to handle lists with many items (e.g., 5 cats = ~10 facts)
                temperature=0.3,  # Low temp for consistent extraction
                system="You are a fact extraction system. Extract discrete facts from conversations. For lists, extract EACH item separately. Output valid JSON only.",
                messages=[{"role": "user", "content": extraction_prompt}],
            )

            text = resp.content[0].text.strip()

            # Clean potential markdown formatting
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            text = text.strip()

            # Parse JSON with robust extraction (handles Haiku's extra text)
            facts = self._extract_json_from_response(text)

            if facts is None:
                # Fallback: Create simple fact from response text to prevent losing content
                print(f"[MEMORY] JSON extraction failed, using simple fallback")
                # Determine perspective from context
                fallback_perspective = "kay" if response and not user_input else "user"
                source_text = response if response else user_input
                facts = [{
                    "fact": source_text[:200] if source_text else "Content processed",
                    "perspective": fallback_perspective,
                    "topic": "exploration"
                }]

            if not isinstance(facts, list):
                # Fallback: Wrap non-list in a list
                print(f"[MEMORY] Expected list, got {type(facts).__name__}, wrapping")
                facts = [facts] if isinstance(facts, dict) else [{"fact": str(facts)[:200], "perspective": "kay", "topic": "exploration"}]

            # Validate structure and process entities
            validated_facts = []

            # CRITICAL FIX: Determine source speaker
            # If user_input is empty and response exists, facts are from Kay's response
            # If user_input exists and response is empty, facts are from user input
            source_speaker = "user" if user_input and not response else "kay"

            for fact in facts:
                if isinstance(fact, dict) and "fact" in fact:
                    perspective = fact.get("perspective", "user")

                    # CRITICAL BUG FIX: Detect Kay's claims about the user
                    # When Kay makes a statement about the user (perspective="user"),
                    # it should NOT be stored as ground truth - mark for confirmation
                    needs_confirmation = False
                    if source_speaker == "kay" and perspective == "user":
                        # Kay is making a claim about the user (Re)
                        # This needs confirmation - not authoritative
                        needs_confirmation = True

                    fact_data = {
                        "fact": fact.get("fact", ""),
                        "perspective": perspective,
                        "topic": fact.get("topic", "general"),
                        "entities": fact.get("entities", []),
                        "attributes": fact.get("attributes", []),
                        "relationships": fact.get("relationships", []),
                        "source_speaker": source_speaker,  # NEW: Track who said this
                        "needs_confirmation": needs_confirmation,  # NEW: Flag unconfirmed claims
                        "is_correction": fact.get("is_correction", False),
                        "corrects": fact.get("corrects", None)
                    }

                    # Process entities: add to entity graph
                    # IMPORTANT: Pass source_speaker to prevent Kay's claims from becoming truth
                    self._process_entities(fact_data, source_speaker=source_speaker)

                    # NEW: Handle user corrections to entity attributes
                    if fact_data.get("is_correction") and fact_data.get("corrects"):
                        self._apply_user_correction(fact_data["corrects"])

                    validated_facts.append(fact_data)

            return validated_facts if validated_facts else [{
                "fact": user_input,  # COMPLETE fallback
                "perspective": self._detect_perspective(user_input),
                "topic": "conversation",
                "entities": self._extract_entities_simple(user_input),
                "attributes": [],
                "is_extraction_fallback": True
            }]

        except Exception as e:
            print(f"[WARNING] Fact extraction failed: {e}")
            # CRITICAL: Return FULL user_input, not truncated
            return [{
                "fact": user_input,  # COMPLETE, never truncated
                "perspective": self._detect_perspective(user_input),
                "topic": "conversation",
                "entities": self._extract_entities_simple(user_input),
                "attributes": [],
                "is_extraction_fallback": True
            }]

    def _process_entities(self, fact_data: Dict[str, Any], source_speaker: str = None):
        """
        Process extracted entities and attributes, adding them to the entity graph.

        CRITICAL FIX: Before creating ownership relationships, verify against identity layer.
        Prevents Kay from creating false relationships when confused about ownership.

        CRITICAL FIX #2: Use source_speaker to track WHO SAID this, not perspective.
        Perspective = about whom (user/kay), source_speaker = who said it (user/kay).
        When Kay says "Your eyes are brown", perspective=user but source_speaker=kay.

        Args:
            fact_data: Fact dict with entities, attributes, and relationships
            source_speaker: Who said this fact ("user" or "kay")
        """
        # FIXED: Use source_speaker if provided, otherwise derive from perspective
        if source_speaker is not None:
            speaker = source_speaker
        else:
            # Fallback to old behavior for compatibility
            perspective = fact_data.get("perspective", "user")
            speaker = "user" if perspective == "user" else "kay"

        # Create/update entities
        for entity_name in fact_data.get("entities", []):
            # Determine entity type based on context (simplified)
            entity_type = "unknown"
            if entity_name in ["Re", "Kay"]:
                entity_type = "person"

            # Get or create entity
            entity = self.entity_graph.get_or_create_entity(
                entity_name,
                entity_type=entity_type,
                turn=self.current_turn
            )

        # Add attributes to entities
        for attr_data in fact_data.get("attributes", []):
            entity_name = attr_data.get("entity")
            attribute_name = attr_data.get("attribute")
            value = attr_data.get("value")

            if entity_name and attribute_name and value:
                entity = self.entity_graph.get_or_create_entity(
                    entity_name,
                    turn=self.current_turn
                )

                # CRITICAL: Source is based on who said this (speaker)
                source = speaker

                # CRITICAL FIX: Correct language for document-related activities
                # Kay READS documents, doesn't EXPERIENCE them
                if entity_name == "Kay" and attribute_name == "activity":
                    value_lower = value.lower()
                    # Detect document-reading activities that should be reframed
                    experience_words = ["examining", "investigating", "exploring", "navigating",
                                       "working through", "going through", "processing", "analyzing"]
                    document_indicators = ["archive", "document", "section", "log", "file", "text",
                                          "chapter", "entry", "record", "zero"]

                    has_experience_word = any(w in value_lower for w in experience_words)
                    has_document_indicator = any(d in value_lower for d in document_indicators)

                    if has_experience_word and has_document_indicator:
                        # Reframe: Kay READ these documents, didn't experience them
                        original_value = value
                        value = value.replace("examining", "reading about")
                        value = value.replace("investigating", "reading about")
                        value = value.replace("exploring", "reading about")
                        value = value.replace("navigating", "reading through")
                        value = value.replace("working through", "reading through")
                        value = value.replace("going through", "reading through")
                        value = value.replace("processing", "reading")
                        value = value.replace("analyzing", "reading about")
                        print(f"[ACTIVITY CORRECTION] '{original_value}' → '{value}' (Kay reads, doesn't experience)")

                entity.add_attribute(
                    attribute_name,
                    value,
                    turn=self.current_turn,
                    source=source
                )

        # Add relationships WITH OWNERSHIP VERIFICATION
        for rel_data in fact_data.get("relationships", []):
            entity1 = rel_data.get("entity1")
            relation_type = rel_data.get("relation")
            entity2 = rel_data.get("entity2")

            if entity1 and relation_type and entity2:
                source = speaker

                # CRITICAL FIX: Verify ownership relationships against identity layer
                if relation_type == "owns":
                    # IMPORTANT: Only verify Kay's statements, not user's
                    # User statements are ALWAYS authoritative (ground truth)

                    if speaker == "kay":
                        # Kay is making an ownership claim - verify against identity layer
                        conflict_check = self.entity_graph.check_ownership_conflict(
                            entity=entity2,
                            claimed_owner=entity1,
                            identity_memory=self.identity
                        )

                        if conflict_check["should_block"]:
                            # BLOCK: Kay is confused about ownership
                            print(f"[OWNERSHIP BLOCKED] {conflict_check['message']}")

                            # Add to fact metadata for tracking
                            fact_data["ownership_conflict"] = True
                            fact_data["ownership_confusion"] = conflict_check["message"]
                            fact_data["confidence"] = "contradiction"

                            # DON'T create the relationship
                            continue

                        elif conflict_check["conflict"]:
                            # Conflict but not blocking (lower confidence)
                            print(f"[OWNERSHIP WARNING] {conflict_check['message']}")
                            fact_data["confidence"] = "inferred"
                        else:
                            # No conflict - but still inferred since Kay said it
                            fact_data["confidence"] = "inferred"

                    else:
                        # User is making the ownership claim - ALWAYS ground truth
                        fact_data["confidence"] = "ground_truth"

                        # Check if this CORRECTS a previous Kay confusion
                        conflict_check = self.entity_graph.check_ownership_conflict(
                            entity=entity2,
                            claimed_owner=entity1,
                            identity_memory=self.identity
                        )

                        if conflict_check["conflict"]:
                            # User is correcting Kay's previous confusion
                            print(f"[OWNERSHIP CORRECTION] User establishes ground truth: {entity1} owns {entity2} (corrects previous Kay confusion)")
                        else:
                            # New ground truth established
                            print(f"[OWNERSHIP GROUND_TRUTH] User establishes: {entity1} owns {entity2}")

                # Create relationship (only if not blocked)
                self.entity_graph.add_relationship(
                    entity1,
                    relation_type,
                    entity2,
                    turn=self.current_turn,
                    source=source
                )

    def _apply_user_correction(self, correction_data: Dict[str, Any]):
        """
        Apply a user correction to the entity graph.

        When the user corrects Kay about a fact, this propagates that correction
        to all related entity attributes.

        Args:
            correction_data: Dict with:
                - entity: Entity name to correct
                - wrong_value: The incorrect value
                - correct_value: The correct value
                - attribute_pattern: Attribute name pattern (e.g., "year", "age")
        """
        if not correction_data:
            return

        entity = correction_data.get("entity", "")
        wrong_value = correction_data.get("wrong_value", "")
        correct_value = correction_data.get("correct_value", "")
        attribute_pattern = correction_data.get("attribute_pattern", "")

        if not entity or not wrong_value or not correct_value:
            print(f"[USER CORRECTION] Missing required fields in correction: {correction_data}")
            return

        print(f"[USER CORRECTION] Processing: {entity}.{attribute_pattern} = '{wrong_value}' → '{correct_value}'")

        # Apply the correction to the entity graph
        result = self.entity_graph.apply_user_correction(
            entity_name=entity,
            attribute_pattern=attribute_pattern,
            wrong_value=wrong_value,
            correct_value=correct_value,
            turn=self.current_turn
        )

        if result["corrections_applied"] > 0:
            print(f"[USER CORRECTION] Successfully applied {result['corrections_applied']} corrections")
            for corr in result["attributes_corrected"]:
                print(f"  - {corr['entity']}.{corr['attribute']}: '{corr['old_value']}' → '{corr['new_value']}'")
        else:
            # Try broader search - maybe the entity name is different
            print(f"[USER CORRECTION] No direct match found, trying broader search...")

            # Search for any attributes with the wrong value
            matches = self.entity_graph.find_attributes_with_value(wrong_value)
            if matches:
                print(f"[USER CORRECTION] Found {len(matches)} attributes with value '{wrong_value}':")
                for match in matches[:5]:  # Show first 5
                    print(f"  - {match['entity']}.{match['attribute']} = '{match['value']}' (source: {match['source']})")

                # Apply correction to each matching entity
                for match in matches:
                    self.entity_graph.apply_user_correction(
                        entity_name=match['entity'],
                        attribute_pattern=match['attribute'],
                        wrong_value=wrong_value,
                        correct_value=correct_value,
                        turn=self.current_turn
                    )

        # PROPAGATE TO MEMORY LAYERS: Mark memories with wrong value as stale
        if self.layer_manager:
            layer_result = self.layer_manager.apply_user_correction(
                wrong_value=wrong_value,
                correct_value=correct_value,
                entity=entity
            )
            if layer_result["working_marked"] + layer_result["longterm_marked"] > 0:
                print(f"[USER CORRECTION] Memory layers: marked {layer_result['working_marked']} working + {layer_result['longterm_marked']} long-term memories")

        # PROPAGATE TO IDENTITY MEMORY: Check and invalidate identity facts with wrong value
        if self.identity_memory:
            identity_result = self.identity_memory.apply_user_correction(
                wrong_value=wrong_value,
                correct_value=correct_value
            )
            if identity_result.get("facts_invalidated", 0) > 0:
                print(f"[USER CORRECTION] Identity memory: invalidated {identity_result['facts_invalidated']} facts")

    def _extract_facts(self, user_input: str, response: str) -> List[Dict[str, str]]:
        """
        LEGACY METHOD: Kept for backward compatibility.
        Calls new _extract_facts_with_entities() method.
        """
        return self._extract_facts_with_entities(user_input, response)

    def _extract_json_from_response(self, text: str):
        """
        Extract JSON from LLM response that might have extra text.

        Handles cases where Haiku adds explanatory text before/after JSON.

        Args:
            text: Response text that should contain JSON

        Returns:
            Parsed JSON object/array, or None if extraction fails
        """
        import json
        import re

        # First try direct parse (fast path for well-formed responses)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON array or object in the text
        # Look for outermost brackets/braces
        json_match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # If still failing, try to find just the array content
        # (in case there's text between the brackets)
        bracket_match = re.search(r'\[(.*)\]', text, re.DOTALL)
        if bracket_match:
            try:
                return json.loads(f'[{bracket_match.group(1)}]')
            except json.JSONDecodeError:
                pass

        return None

    def _detect_perspective(self, user_input: str) -> str:
        """
        Detect whose perspective this memory is about.
        - "user" = facts about the user (Re - the person typing)
        - "kay" = facts about Kay (the agent - the AI)
        - "shared" = facts about both or shared experiences

        CRITICAL RULES:
        1. The USER is ALWAYS the person typing (Re)
        2. "I/my/me" = the speaker (the user Re)
        3. "you/your" = the addressee (Kay, the AI)
        4. Mentioned names (Reed, Sarah, etc.) are THIRD PARTIES, not the user
        5. The user's name is "Re" - any other name is someone else

        Grammar-based detection ONLY. No name pattern matching.
        """
        text = user_input.lower().strip()

        # Explicit memory directives
        if text.startswith("remember that you") or text.startswith("kay, remember that you"):
            return "kay"
        if text.startswith("remember that i") or text.startswith("remember i"):
            return "user"
        if text.startswith("remember that we") or text.startswith("remember we"):
            return "shared"

        # First-person pronouns = user (Re, the person typing)
        # Check for these at word boundaries to avoid partial matches
        first_person = [r'\bi\s', r'\bmy\s', r'\bme\s', r'\bi\'m\b', r'\bi\'ve\b', r'\bi\'ll\b']
        for pattern in first_person:
            if re.search(pattern, text):
                return "user"

        # Second-person pronouns = Kay (the AI being addressed)
        second_person = [r'\byou\s', r'\byour\s', r'\byou\'re\b', r'\byou\'ve\b', r'\byou\'ll\b']
        for pattern in second_person:
            if re.search(pattern, text):
                return "kay"

        # "We/us/our" = shared
        shared_pronouns = [r'\bwe\s', r'\bus\s', r'\bour\s', r'\bwe\'re\b', r'\bwe\'ve\b']
        for pattern in shared_pronouns:
            if re.search(pattern, text):
                return "shared"

        # Default: neutral/user
        # Simple statements with no pronouns are usually about the user's world
        return "user"

    def _validate_fact_against_sources(self, fact: str, fact_perspective: str, retrieved_memories: List[Dict]) -> bool:
        """
        Validate that Kay's claimed facts about the user were actually stated by the user.

        Returns True if fact is VALID (should be stored), False if HALLUCINATION (should be blocked).

        CRITICAL: Prevents Kay from inventing/fabricating details that weren't mentioned.
        """
        # Only validate Kay's statements about the user
        if fact_perspective != "kay":
            return True  # User's own statements are always valid

        fact_lower = fact.lower()

        # Check if Kay is claiming a fact about the user (contains "you/your" or user entities)
        is_about_user = any(word in fact_lower for word in ["you", "your", "re's", "re "])

        if not is_about_user:
            return True  # Kay's statements about himself are not validated here

        # Kay is making a claim about the user - verify it was actually mentioned
        # STRATEGY: Only block if we can PROVE fabrication (specific validation patterns)
        # Otherwise allow (can't validate everything)

        # Collect all user memories for validation
        user_memories_text = []
        for mem in retrieved_memories:
            if mem.get("perspective") == "user":
                mem_text = (mem.get("fact", "") + " " + mem.get("user_input", "")).lower()
                user_memories_text.append(mem_text)

        # If no user memories retrieved, we can't validate - allow by default
        if not user_memories_text:
            return True

        combined_user_text = " ".join(user_memories_text)

        # SPECIFIC VALIDATION PATTERNS (block if proven false)

        # Pattern 1: Eye color fabrication
        if "eye" in fact_lower:
            colors = ["gold", "brown", "green", "blue", "hazel", "amber", "copper", "grey", "gray", "forest", "jade", "emerald", "sapphire"]
            fact_colors = [c for c in colors if c in fact_lower]

            if fact_colors and "eye" in combined_user_text:
                # User mentioned eyes - validate color details
                mem_colors = [c for c in colors if c in combined_user_text]

                for fact_color in fact_colors:
                    if fact_color not in mem_colors:
                        # Kay is adding a color detail user never mentioned
                        print(f"[HALLUCINATION DETAIL] Kay added color '{fact_color}' but user only mentioned {mem_colors}")
                        return False  # Block fabricated color details

        # Pattern 2: Add more specific patterns here as needed
        # (hair color, pet names, preferences, etc.)

        # DEFAULT: If no specific validation pattern triggered, allow the fact
        # We can't validate everything, so we trust Kay unless we can prove fabrication
        return True

    def _extract_attribute_type(self, fact_text: str) -> str:
        """
        Extract what KIND of attribute this fact is describing.
        This enables comparing only facts about the SAME attribute type.
        """
        fact_lower = fact_text.lower()

        # Physical attributes (immutable or slow-changing)
        if any(word in fact_lower for word in ["eye", "eyes", "hair", "height", "weight", "skin"]):
            return "physical_appearance"

        # Location (can't be two places at once)
        if any(word in fact_lower for word in ["lives in", "located in", "at home", "in the city", "from"]):
            return "location"

        # Species/type (mutually exclusive)
        if any(word in fact_lower for word in ["is a cat", "is a dog", "is a bird", "is a dragon"]):
            return "species"

        # Strong preferences (like vs hate for SAME thing)
        if any(word in fact_lower for word in ["loves", "hates", "prefers", "favorite", "never", "always"]):
            # Check what the preference is ABOUT
            if any(word in fact_lower for word in ["coffee", "tea"]):
                return "beverage_preference"
            if any(word in fact_lower for word in ["cats", "dogs"]):
                return "pet_preference"
            if any(word in fact_lower for word in ["morning", "night", "evening"]):
                return "time_preference"
            return "strong_preference"

        # Mental states (can coexist - NOT contradictory)
        if any(word in fact_lower for word in ["steady", "clear-headed", "sharp", "focused", "alert"]):
            return "mental_state_positive"
        if any(word in fact_lower for word in ["confused", "scrambling", "anxious", "uncertain"]):
            return "mental_state_negative"

        # Physical states (can coexist - NOT contradictory)
        if any(word in fact_lower for word in ["hungry", "tired", "thirsty", "exhausted", "energized"]):
            return "physical_state"

        # Activities/actions (temporal, can change freely)
        if any(word in fact_lower for word in ["is doing", "working on", "remembers", "thinking", "building"]):
            return "activity"

        # Emotional states (can coexist - NOT contradictory)
        if any(word in fact_lower for word in ["curious", "happy", "sad", "excited", "grateful"]):
            return "emotional_state"

        # If can't determine, assume it's unique and not worth comparing
        return "unknown"

    def _are_attributes_comparable(self, attr_type1: str, attr_type2: str) -> bool:
        """
        Determine if two attribute types should be compared for contradictions.

        Returns True only if they are the EXACT same attribute type AND
        that type can actually have contradictory values.
        """
        # Different attribute types = NEVER compare
        if attr_type1 != attr_type2:
            return False

        # These can have contradictions (mutually exclusive values)
        contradictable_types = {
            "physical_appearance",  # eye color, etc.
            "location",            # can't be two places
            "species",             # can't be cat AND dog
            "beverage_preference", # like coffee vs hate coffee
            "pet_preference",
            "time_preference",
            "strong_preference"
        }

        # These can coexist and should NOT be checked for contradictions
        coexisting_types = {
            "mental_state_positive",   # can be steady AND sharp
            "mental_state_negative",   # can be confused AND anxious
            "physical_state",          # can be hungry AND tired
            "activity",                # activities change freely
            "emotional_state",         # can feel multiple things
            "unknown"                  # don't compare unknowns
        }

        if attr_type1 in coexisting_types:
            return False

        return attr_type1 in contradictable_types

    def _extract_entity(self, fact_text: str) -> str:
        """Extract which entity a fact is about (kay/re/unknown)."""
        fact_lower = fact_text.lower()

        if any(pattern in fact_lower for pattern in ["kay's", "kay is", "kay has", "kay "]):
            return "kay"
        if any(pattern in fact_lower for pattern in ["re's", "re is", "re has", "re ", "your", "you "]):
            return "re"
        if any(pattern in fact_lower for pattern in ["i ", "my ", "i'm", "i am"]):
            # First person - depends on context, but often Kay speaking
            return "kay"

        # Check for entity names in the text (for pets, etc.)
        # These are about entities but might have ownership patterns
        known_entities = ["chrome", "saga", "bob", "pigeon"]
        for entity in known_entities:
            if entity in fact_lower:
                return entity

        return "unknown"

    def _is_coherent_fact(self, text: str) -> bool:
        """
        Check if text is a coherent fact statement worth comparing.
        Filters out random fragments and partial text.
        """
        # Too short = probably fragment
        if len(text) < 10:
            return False

        # No verb-like structure = probably not a fact
        # Include common action verbs and negations
        has_verb = any(word in text.lower() for word in
                      ["is", "are", "has", "have", "was", "were", "likes", "hates",
                       "prefers", "loves", "lives", "works", "does", "feels",
                       "drinks", "eats", "says", "knows", "thinks", "wants",
                       "never", "always", "can", "will", "should"])

        if not has_verb:
            return False

        return True

    def _check_contradiction(self, new_fact: str, retrieved_memories: List[Dict]) -> bool:
        """
        Check if new fact contradicts what was retrieved.

        SMART CONTRADICTION DETECTION:
        1. Only compare SAME entity (Kay vs Kay, Re vs Re)
        2. Only compare SAME attribute type (eye_color vs eye_color)
        3. Skip coexisting states (tired + hungry are NOT contradictory)
        4. Require coherent fact statements (skip fragments)
        5. Check for actual opposing values, not just difference

        Returns True only for REAL contradictions.
        """
        new_fact_lower = new_fact.lower()

        # Skip incoherent text fragments
        if not self._is_coherent_fact(new_fact):
            return False  # Not worth checking

        # Extract metadata about new fact
        new_entity = self._extract_entity(new_fact)
        new_attr_type = self._extract_attribute_type(new_fact)

        # Unknown entity or attribute = skip comparison
        if new_entity == "unknown" or new_attr_type == "unknown":
            return False  # Can't determine, don't block

        for mem in retrieved_memories:
            mem_fact = mem.get("fact", mem.get("user_input", "")).lower()

            # Skip incoherent memories
            if not self._is_coherent_fact(mem_fact):
                continue

            # Extract metadata about memory
            mem_entity = self._extract_entity(mem_fact)
            mem_attr_type = self._extract_attribute_type(mem_fact)

            # CRITICAL: Only compare if SAME ENTITY
            if mem_entity != new_entity or mem_entity == "unknown":
                continue  # Different people, not a contradiction

            # CRITICAL: Only compare if SAME ATTRIBUTE TYPE
            if not self._are_attributes_comparable(new_attr_type, mem_attr_type):
                continue  # Different attribute types, not a contradiction

            # Now we have: same entity, same attribute type, both coherent
            # Check for actual opposing values

            # Eye color check
            if new_attr_type == "physical_appearance" and "eye" in new_fact_lower and "eye" in mem_fact:
                colors = ["gold", "brown", "green", "blue", "hazel", "amber", "copper", "grey", "gray"]
                new_colors = [c for c in colors if c in new_fact_lower]
                mem_colors = [c for c in colors if c in mem_fact]

                if new_colors and mem_colors and set(new_colors) != set(mem_colors):
                    print(f"[CONTRADICTION FLAGGED] {new_entity.upper()}'s eye color: '{new_colors}' vs '{mem_colors}' (same attribute, conflicting values)")
                    return True

            # Strong preference check (like X vs hate X)
            if new_attr_type in ["beverage_preference", "pet_preference", "time_preference", "strong_preference"]:
                # Check for opposing sentiment on SAME subject
                # Note: "drinks" is neutral, not positive - "never drinks" is negative
                like_words = ["loves", "likes", "prefers", "enjoys", "favorite"]
                hate_words = ["hates", "dislikes", "never", "avoids", "despises", "don't", "doesn't"]

                new_positive = any(w in new_fact_lower for w in like_words)
                new_negative = any(w in new_fact_lower for w in hate_words)
                mem_positive = any(w in mem_fact for w in like_words)
                mem_negative = any(w in mem_fact for w in hate_words)

                # Opposite sentiment = contradiction
                if (new_positive and mem_negative) or (new_negative and mem_positive):
                    # Verify they're about the SAME subject
                    subjects = ["coffee", "tea", "cats", "dogs", "morning", "night", "evening"]
                    new_subjects = [s for s in subjects if s in new_fact_lower]
                    mem_subjects = [s for s in subjects if s in mem_fact]

                    # Only contradict if same subject
                    if new_subjects and mem_subjects and set(new_subjects) & set(mem_subjects):
                        shared_subject = list(set(new_subjects) & set(mem_subjects))[0]
                        print(f"[CONTRADICTION FLAGGED] {new_entity.upper()}'s preference on '{shared_subject}': opposing sentiments")
                        return True

            # Location check
            if new_attr_type == "location":
                # Only flag if clearly different locations mentioned
                locations = ["ohio", "california", "new york", "texas", "home", "work", "office"]
                new_locs = [l for l in locations if l in new_fact_lower]
                mem_locs = [l for l in locations if l in mem_fact]

                if new_locs and mem_locs and set(new_locs) != set(mem_locs):
                    print(f"[CONTRADICTION FLAGGED] {new_entity.upper()}'s location: '{new_locs}' vs '{mem_locs}'")
                    return True

            # Species check
            if new_attr_type == "species":
                species = ["cat", "dog", "bird", "dragon", "human"]
                new_species = [s for s in species if s in new_fact_lower]
                mem_species = [s for s in species if s in mem_fact]

                if new_species and mem_species and set(new_species) != set(mem_species):
                    print(f"[CONTRADICTION FLAGGED] {new_entity.upper()}'s species: '{new_species}' vs '{mem_species}'")
                    return True

        return False  # No real contradiction found

    def encode_memory(self, user_input, response, emotional_cocktail, emotion_tags, perspective=None, agent_state=None):
        """
        TWO-TIER MEMORY STORAGE:

        EPISODIC (full_turn): Complete conversation turns with context, emotions
        SEMANTIC (extracted_fact): Discrete facts extracted from conversations

        Storage layers: working → episodic → semantic (automatic promotion)
        CRITICAL: NO TRUNCATION. Store complete text in both tiers.
        """
        import time

        clean_response = re.sub(r"\*[^*\n]{0,200}\*", "", response or "")

        # FIX: Extract facts from Kay's response ONLY
        # User facts already extracted in pre-response phase (extract_and_store_user_facts)
        # Extracting from user_input again would create duplicates
        extracted_facts = self._extract_facts("", clean_response)

        print(f"[MEMORY] Extracted {len(extracted_facts)} facts from Kay's response (user facts already stored in pre-response)")

        # Collect all unique entities from extracted facts
        all_entities = set()
        for fact_data in extracted_facts:
            all_entities.update(fact_data.get("entities", []))

        entity_list = sorted(list(all_entities))
        is_list_statement = len(entity_list) >= 3  # 3+ entities = list

        # Get what was retrieved for validation (hallucination checking)
        retrieved_memories = getattr(agent_state, 'last_recalled_memories', []) if agent_state else []

        # ===== EPISODIC: FULL CONVERSATION TURN (never truncated) =====
        # CRITICAL: Filter to salient emotions only before storing
        # This breaks the 77-emotion feedback loop
        filtered_emotion_tags = emotion_tags or []
        if self.emotion_engine and emotional_cocktail and len(emotion_tags or []) > 7:
            salient_emotions = self.emotion_engine.detect_salient_emotions(emotional_cocktail)
            filtered_emotion_tags = [e for e in (emotion_tags or []) if e in salient_emotions]
            if len(filtered_emotion_tags) < len(emotion_tags or []):
                print(f"[MEMORY] Filtered emotion tags: {len(emotion_tags)} -> {len(filtered_emotion_tags)} (salient only)")

        turn_importance = self._calculate_turn_importance(
            emotional_cocktail or {},
            filtered_emotion_tags,
            len(entity_list)
        )

        full_turn_record = {
            "type": "full_turn",
            "user_input": user_input,  # COMPLETE - no truncation
            "response": clean_response,  # COMPLETE - no truncation
            "turn_number": self.current_turn,
            "timestamp": time.time(),
            "perspective": "conversation",
            "topic": "conversation_turn",
            "entities": entity_list,
            "is_list": is_list_statement,
            "emotional_cocktail": emotional_cocktail or {},
            "emotion_tags": filtered_emotion_tags,  # FILTERED to salient only
            "importance_score": turn_importance,
            "current_layer": "working"  # For memory_layers compatibility
        }

        # Store full turn
        self.memories.append(full_turn_record)
        self.memory_layers.add_memory(full_turn_record, layer="working", session_order=self.current_session_order, session_id=self.current_session_id)

        print(f"[MEMORY 2-TIER] OK EPISODIC - Full turn stored (user:{len(user_input)}chars, response:{len(clean_response)}chars, entities:{len(entity_list)})")

        # ===== SEMANTIC: EXTRACTED FACTS (structured) =====
        stored_fact_count = 0

        for fact_data in extracted_facts:
            fact_text = fact_data.get("fact", "")
            fact_perspective = fact_data.get("perspective", "user")
            fact_topic = fact_data.get("topic", "general")
            needs_confirmation = fact_data.get("needs_confirmation", False)
            source_speaker = fact_data.get("source_speaker", "user")

            # CRITICAL: Distinguish Kay's observations from false attributions
            if needs_confirmation:
                # Use smart filtering - allow observations, block false attributions
                should_store, storage_type = should_store_claim(
                    fact_text=fact_text,
                    source_speaker=source_speaker,
                    perspective=fact_perspective,
                    user_input=user_input  # Pass user's actual input for validation
                )

                if not should_store:
                    # False attribution (Kay claiming user SAID something) - BLOCK
                    print(f"[FALSE ATTRIBUTION] X Kay claimed: '{fact_text[:60]}...' - NOT STORING.")
                    print(f"[FALSE ATTRIBUTION]   Reason: False attribution (user didn't say this)")
                    print(f"[FALSE ATTRIBUTION]   Source: Kay | Perspective: {fact_perspective} | Topic: {fact_topic}")
                    continue  # Skip this fact

                if storage_type == "entity_observation":
                    # Valid observation (Kay's inference about user state) - ALLOW with tagging
                    print(f"[ENTITY OBSERVATION] ✓ Storing Kay's observation: '{fact_text[:60]}...'")
                    print(f"[ENTITY OBSERVATION]   Type: {fact_topic} | Observer: Kay → {fact_perspective}")

                    # Tag as entity observation for retrieval filtering
                    fact_data = create_entity_observation(fact_data, observer="kay", observed="re")
                    # IMPORTANT: Don't skip - continue to storage below

            # Validate Kay's statements against retrieved memories (prevent hallucination)
            if fact_perspective == "kay" and retrieved_memories:
                is_valid_fact = self._validate_fact_against_sources(fact_text, fact_perspective, retrieved_memories)

                if not is_valid_fact:
                    print(f"[HALLUCINATION BLOCKED] X Kay fabricated '{fact_text[:60]}...' - NOT STORING.")
                    continue

                is_contradictory = self._check_contradiction(fact_text, retrieved_memories)

                if is_contradictory:
                    # CHANGED: Flag instead of block - still store but mark for review
                    # Kay's reality can change (was confused → now clear-headed = growth)
                    # Don't block legitimate state changes, just log the potential conflict
                    print(f"[CONTRADICTION FLAGGED] ! Kay stated '{fact_text[:60]}...' may conflict with memory")
                    print(f"[CONTRADICTION FLAGGED]   Storing anyway - temporal changes are valid. Flag for Re's review.")
                    # Add flag to fact_data so it can be tracked
                    fact_data["has_potential_conflict"] = True
                    # DON'T continue - allow storage to proceed

            # Track preferences
            if fact_perspective == "kay":
                self.preference_tracker.track_preference(fact_text, fact_perspective, context="extracted_fact")

            # Calculate importance
            fact_importance = self._calculate_fact_importance(fact_data, emotional_cocktail)

            # Build fact record
            fact_record = {
                "type": "extracted_fact",
                "fact": fact_text,  # COMPLETE - no truncation
                "user_input": user_input,  # Original context (COMPLETE)
                "response": clean_response,  # Original context (COMPLETE)
                "perspective": fact_perspective,
                "topic": fact_topic,
                "emotion_tags": filtered_emotion_tags,  # Use filtered tags (salient only)
                "emotional_cocktail": emotional_cocktail or {},
                "entities": fact_data.get("entities", []),
                "attributes": fact_data.get("attributes", []),
                "relationships": fact_data.get("relationships", []),
                "parent_turn": self.current_turn,  # Link back to full turn
                "importance_score": fact_importance,
                "current_layer": "working"
            }

            # === TEMPORAL VERSIONING: Check for existing fact ===
            # Extract entity and attribute for versioning
            entities = fact_data.get("entities", [])
            attributes = fact_data.get("attributes", [])

            # Try to extract entity.attribute pattern
            # Extract entity - handle both string and dict formats
            if entities:
                entity_item = entities[0]
                if isinstance(entity_item, dict):
                    entity = entity_item.get('entity')
                else:
                    entity = entity_item
            else:
                entity = None

            # Extract attribute - handle both string and dict formats
            if attributes:
                attr_item = attributes[0]
                if isinstance(attr_item, dict):
                    attribute = attr_item.get('attribute')
                else:
                    attribute = attr_item
            else:
                attribute = None

            # If we have entity + attribute, check for existing fact
            if entity and attribute:
                fact_record['entity'] = entity
                fact_record['attribute'] = attribute

                # Try to extract value from fact text
                # Common patterns: "X is Y", "X has Y", "X's Y is Z"
                value = None
                fact_lower = fact_text.lower()
                if " is " in fact_lower:
                    # "Saga is orange" → value = "orange"
                    value = fact_text.split(" is ")[-1].strip()
                elif " has " in fact_lower:
                    # "Saga has color orange" → value = "orange"
                    value = fact_text.split(" has ")[-1].strip()

                if value:
                    fact_record['current_value'] = value

                    # Check if this fact already exists
                    existing_fact = find_existing_fact(fact_record, self.memories)
                    update_type = should_update_fact(existing_fact, value)

                    if update_type == 'skip':
                        # Same value - just confirm
                        confirm_fact(existing_fact)
                        # Don't store duplicate, skip to next fact
                        continue

                    elif update_type == 'amend':
                        # Value changed - create history
                        amend_fact(existing_fact, value, self.current_turn)
                        # Fact is already in memories, just updated
                        stored_fact_count += 1
                        continue

                    else:  # update_type == 'new'
                        # New fact - add versioning fields
                        now = datetime.now(timezone.utc).isoformat()
                        fact_record['created_at'] = now
                        fact_record['last_confirmed'] = now
                        fact_record['version'] = 1
                        fact_record['history'] = []

                        print(f"[FACT CREATED] {entity}.{attribute} = {value} (version 1)")

            # Store fact (either new versioned fact or non-entity fact)
            self.memories.append(fact_record)
            self.facts.append(fact_text)
            self.memory_layers.add_memory(fact_record, layer="working", session_order=self.current_session_order, session_id=self.current_session_id)

            stored_fact_count += 1
            if not (entity and attribute):
                # Non-entity fact, use standard logging
                print(f"[MEMORY 2-TIER] OK SEMANTIC - Fact [{fact_perspective}/{fact_topic}]: {fact_text[:60]}...")

        # ===== CHECK FOR IDENTITY FACTS (permanent storage) =====
        # CRITICAL FIX: Only check extracted_fact type, NOT full_turn
        # Full turns are conversations (questions, events) - not identity

        for fact_record in [mem for mem in self.memories
                           if mem.get("type") == "extracted_fact"
                           and mem.get("parent_turn") == self.current_turn]:

            # CRITICAL: Document-imported facts should NEVER be Kay's identity
            # They are things Kay READ ABOUT, not things Kay IS
            # NOTE: identity_memory.py now handles routing document content to fictional_knowledge
            if fact_record.get("source_document") or fact_record.get("is_imported") or fact_record.get("doc_id"):
                # The identity system will route this to fictional_knowledge
                source_doc = fact_record.get("source_document", fact_record.get("source_file", "unknown"))
                print(f"[IDENTITY SKIP] Document fact routed to fictional_knowledge (source: {source_doc}): {fact_record.get('fact', '')[:60]}...")
                # Still try to add - identity_memory will route it appropriately
                self.identity.add_fact(fact_record)
                continue

            is_identity = self.identity.add_fact(fact_record)
            if is_identity:
                fact_record["is_identity"] = True
                fact_record["importance_score"] = 0.95  # Maximum importance
                # Logging is now handled in identity_memory.py with proper source_type attribution

        # Save to disk
        self._save_to_disk()

        # Summary log
        print(f"[MEMORY 2-TIER] === Turn {self.current_turn} complete: 1 episodic + {stored_fact_count} semantic ===")
        if filtered_emotion_tags:
            print(f"[MEMORY 2-TIER] Emotions stored: {filtered_emotion_tags[:5]}")

    def _score_identity_facts(self, identity_facts: List[Dict[str, Any]], query: str) -> List[tuple]:
        """
        Score identity facts by relevance to query.

        Returns list of (score, fact) tuples sorted by score descending.
        """
        import re

        query_lower = query.lower()
        search_words = set(re.findall(r"\w+", query_lower))

        scored = []
        for fact in identity_facts:
            fact_text = fact.get("fact", "").lower()

            # Keyword matching
            keyword_matches = sum(1 for w in search_words if w in fact_text)
            keyword_score = keyword_matches / max(len(search_words), 1)

            # Entity matching
            fact_entities = set([e.lower() for e in fact.get("entities", [])])
            query_entities = set([w for w in search_words if len(w) > 2])
            entity_matches = len(fact_entities.intersection(query_entities))
            entity_score = entity_matches * 0.5

            # Combine scores
            total_score = keyword_score + entity_score

            scored.append((total_score, fact))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _retrieve_document_tree_chunks(self, query: str, max_docs: int = 3) -> List[Dict[str, Any]]:
        """
        Search document index and load complete documents for matched queries.

        DEPRECATED: This method relied on the old document_index system.
        Document retrieval is now handled by llm_retrieval.py in main.py conversation loop.

        Args:
            query: User query text
            max_docs: Maximum number of matching documents to load (default 3)

        Returns:
            Empty list (documents now retrieved at conversation loop level)
        """
        # DEPRECATED: Old document index system disabled
        # Document retrieval now happens in main.py using llm_retrieval.py
        return []

    def _load_active_chunks_from_memory(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Load chunks from memory_layers if they exist (recently accessed documents).

        Returns:
            List of chunk dicts from memory_layers, or empty list if none found
        """
        active_chunks = []

        # Search all memory layers for chunks with matching doc_id
        for layer_name, layer_memories in [
            ('working', self.memory_layers.working_memory),
            ('long_term', self.memory_layers.long_term_memory)
        ]:
            for mem in layer_memories:
                if mem.get('doc_id') == doc_id:
                    # Mark as document_tree type for consistent handling
                    mem_copy = mem.copy()
                    mem_copy['type'] = 'document_tree'
                    mem_copy['from_memory_layer'] = layer_name
                    active_chunks.append(mem_copy)

        return active_chunks

    @measure_performance("memory_multi_factor", target=0.150)
    def retrieve_unified_importance(self, bias_cocktail, user_input, max_memories: int = 250, conversational_mode: bool = False) -> List[Dict[str, Any]]:
        """
        UNIFIED IMPORTANCE-BASED RETRIEVAL - Single-pool architecture.

        PHILOSOPHY: No category wars. Natural scoring determines what surfaces.

        RETRIEVAL PRIORITY (not storage tiers):
        - BEDROCK: Identity facts + current session (always included)
        - DYNAMIC: Everything else scored by composite metric:
          * Recency: Exponential decay over time
          * Relevance: Keyword similarity to query
          * Importance: Manual weight (1.0 default, 1.5-2.0 for landmarks)
          * Access boost: Log(access_count + 1)

        STORAGE MODEL:
        - Episodic (full_turn): Complete conversation exchanges
        - Semantic (extracted_fact): Discrete facts
        - Storage layers: working → episodic → semantic (auto-promotion)

        Args:
            bias_cocktail: Emotional state for biasing
            user_input: User's query
            max_memories: Maximum memories to return (default 250)
            conversational_mode: If True, prioritize speed over thoroughness.
                                 Used for voice chat where latency matters.
                                 Limits semantic search to recent/high-importance only.

        Returns ~250 memories total (50 bedrock + 200 dynamic).
        """
        # === BEDROCK (always included, no scoring) ===

        bedrock = []

        # 1.1: Identity facts (Kay's core identity)
        identity_facts = self.identity.get_all_identity_facts()
        for mem in identity_facts:
            mem['relevance_score'] = 0.05  # Low relevance for emotion weighting
            mem['is_bedrock'] = True
            mem['confidence'] = 'bedrock'  # 🔵 Solid, definitely real
        bedrock.extend(identity_facts)

        # 1.2: Working memory (current session)
        # Working layer is the current conversation context - always include it
        # COST FIX: Cap working memory to last 20 turns to prevent bedrock overflow
        current_session = []
        if hasattr(self, 'memory_layers'):
            working_pool = self.memory_layers.working_memory
            # Take only the last 20 working memory items (most recent conversation)
            recent_working = working_pool[-20:] if len(working_pool) > 20 else working_pool
            for mem in recent_working:
                mem['relevance_score'] = 0.1  # Session memories have low base relevance
                mem['is_bedrock'] = True
                mem['confidence'] = 'bedrock'  # 🔵 This conversation is solid
                current_session.append(mem)

        bedrock.extend(current_session)

        if VERBOSE_DEBUG:
            print(f"[UNIFIED MEMORY] Bedrock: {len(identity_facts)} identity + {len(current_session)} working = {len(bedrock)} total")

        # === DYNAMIC (everything else, scored) ===

        # Collect non-bedrock memories from layers
        all_other = []

        if hasattr(self, 'memory_layers'):
            # TWO-TIER ARCHITECTURE: working + long-term only
            # Working memory is already included in bedrock (current session)

            if conversational_mode:
                # CONVERSATIONAL MODE: Speed over thoroughness
                # STRICT LIMITS for voice chat:
                # - Max 60 long-term memories (instead of hundreds)
                # - Only include high-importance OR very recent
                longterm_pool = self.memory_layers.long_term_memory

                # Limit to recent or high-importance long-term memories
                # This drastically reduces the pool for voice chat
                filtered_longterm = []
                current_time = time.time()
                three_days_ago = current_time - (3 * 24 * 60 * 60)  # 3 days (stricter)

                for mem in longterm_pool:
                    # Hard cap: max 60 long-term memories in voice mode
                    if len(filtered_longterm) >= 60:
                        break

                    # Include if high importance (identity facts, landmarks)
                    if mem.get('importance', 1.0) >= 1.3:
                        filtered_longterm.append(mem)
                        continue

                    # Include if very recent (within last 3 days)
                    mem_ts = mem.get('timestamp', 0)
                    if isinstance(mem_ts, (int, float)) and mem_ts > three_days_ago:
                        filtered_longterm.append(mem)
                        continue

                    # Include if frequently accessed (high access_count)
                    if mem.get('access_count', 0) >= 5:  # Stricter threshold
                        filtered_longterm.append(mem)
                        continue

                all_other.extend(filtered_longterm)

                if VERBOSE_DEBUG:
                    print(f"[UNIFIED MEMORY] Voice mode: {len(filtered_longterm)}/{len(longterm_pool)} long-term, {len(all_other)} total")
            else:
                # Normal mode: include all long-term memories
                all_other.extend(self.memory_layers.long_term_memory)

        if VERBOSE_DEBUG:
            print(f"[UNIFIED MEMORY] Candidate pool: {len(all_other)} memories to score")

        # Parse query for keyword matching
        search_words = set(re.findall(r"\w+", user_input.lower()))
        if not search_words:
            return bedrock  # No query words, just return bedrock

        # === COMPOSITE SCORING ===

        scored = []
        current_date = datetime.now()

        for mem in all_other:
            # Skip corrupted memories
            if mem.get('corrupted', False):
                continue

            # === 1. RECENCY SCORE (exponential decay) ===
            # Uses timestamp for absolute dating, falls back to turn-based if missing
            mem_timestamp = mem.get('timestamp')
            if mem_timestamp:
                if isinstance(mem_timestamp, (int, float)):
                    mem_date = datetime.fromtimestamp(mem_timestamp)
                else:
                    mem_date = current_date  # Fallback
            else:
                # Fallback: estimate from turn_index
                turn_age = self.current_turn - mem.get('turn_index', 0)
                days_old = turn_age * 0.1  # Rough estimate: 10 turns ≈ 1 day
                mem_date = current_date - timedelta(days=days_old)

            days_old = (current_date - mem_date).days
            recency_score = 1.0 / (1.0 + days_old * 0.1)  # Exponential decay

            # === 2. RELEVANCE SCORE (keyword overlap) ===
            # Extract text blob from memory
            mem_type = mem.get('type', 'unknown')
            if mem_type == 'full_turn':
                text_blob = (mem.get('user_input', '') + ' ' + mem.get('response', '')).lower()
            elif mem_type == 'structured_turn':
                text_blob = (mem.get('raw_text', '') + ' ' + mem.get('parsed_meaning', '')).lower()
            elif mem_type in ['imported_section', 'section_analysis', 'document_summary', 'document_import_complete', 'document_import_start']:
                # LEGACY Import-related memories: search Kay's analysis, emotional observations, and shared context
                text_blob = (
                    mem.get('fact', '') + ' ' +
                    mem.get('Kay_analysis', '') + ' ' +
                    mem.get('Kay_impression', '') + ' ' +
                    mem.get('emotional_tone', '') + ' ' +
                    mem.get('source_document', '') + ' ' +
                    mem.get('document_name', '') + ' ' +
                    mem.get('shared_by', '') + ' shared ' +  # Enable "what did Re share" queries
                    ' '.join(mem.get('key_points', [])) + ' ' +
                    ' '.join(mem.get('key_discoveries', [])) + ' ' +
                    ' '.join(mem.get('takeaways', []))
                ).lower()
            elif mem_type == 'document_content':
                # NEW V2: Contextual document content with relational fields
                text_blob = (
                    mem.get('fact', '') + ' ' +
                    mem.get('document_name', '') + ' ' +
                    mem.get('reveals_about_re', '') + ' ' +
                    mem.get('connects_to', '') + ' ' +
                    mem.get('shared_by', '') + ' shared ' +
                    ' '.join(mem.get('relates_to', [])) + ' ' +
                    ' '.join(mem.get('explains', [])) + ' ' +
                    ' '.join(mem.get('key_insights', [])) + ' ' +
                    ' '.join(mem.get('section_connections', [])) + ' ' +
                    ' '.join(mem.get('entities', []))
                ).lower()
            elif mem_type == 'shared_understanding_moment':
                # NEW V2: Relational understanding - why shared, what changed
                text_blob = (
                    mem.get('fact', '') + ' ' +
                    mem.get('document_name', '') + ' ' +
                    mem.get('why_shared', '') + ' ' +
                    mem.get('what_changed', '') + ' ' +
                    mem.get('future_implications', '') + ' ' +
                    mem.get('pre_read_hypothesis', '') + ' ' +
                    mem.get('conversation_context', '') + ' ' +
                    mem.get('shared_by', '') + ' shared '
                ).lower()
            else:
                # extracted_fact or other
                text_blob = (mem.get('fact', '') + ' ' + mem.get('text', '') + ' ' + mem.get('user_input', '')).lower()

            # OPTIMIZED: Use set intersection instead of substring matching
            # This is O(n) instead of O(n*m) for keyword matching
            mem_words = set(re.findall(r"\w+", text_blob))
            keyword_matches = len(search_words & mem_words)  # Set intersection
            relevance_score = keyword_matches / len(search_words) if search_words else 0.0

            # Early exit: Skip memories with zero relevance (no keyword matches)
            if relevance_score == 0.0:
                continue

            # === 3. IMPORTANCE WEIGHT (manually set) ===
            importance = mem.get('importance', 1.0)  # Default 1.0
            # High-importance events: 1.5-2.0 (emotional landmarks, explicit "remember this")
            # Normal: 1.0

            # === 4. ACCESS PATTERN BOOST ===
            access_count = mem.get('access_count', 0)
            access_boost = 0.1 * math.log(access_count + 1)  # Logarithmic boost

            # === 5. DOCUMENT PROVENANCE BOOST ===
            # Heavily boost memories from recently imported documents
            # This enables "spatial memory" - Kay can recall WHERE he read information
            provenance_boost = 0.0
            source_document = mem.get('source_document')
            import_timestamp = mem.get('import_timestamp')

            if source_document and import_timestamp:
                # Calculate hours since import
                if isinstance(import_timestamp, (int, float)):
                    hours_since_import = (current_date.timestamp() - import_timestamp) / 3600
                else:
                    hours_since_import = 24  # Fallback if format unknown

                # Boost based on recency of import
                if hours_since_import < 1:
                    # Imported within last hour - massive boost (3x)
                    provenance_boost = 2.0
                elif hours_since_import < 6:
                    # Imported within 6 hours - strong boost (2x)
                    provenance_boost = 1.0
                elif hours_since_import < 24:
                    # Imported today - moderate boost (1.5x)
                    provenance_boost = 0.5
                elif hours_since_import < 72:
                    # Imported within 3 days - small boost
                    provenance_boost = 0.2

                # Add provenance info to memory for context building
                mem['_provenance'] = {
                    'source': source_document,
                    'hours_ago': hours_since_import,
                    'boost': provenance_boost
                }

            # === COMPOSITE SCORE ===
            final_score = (recency_score * relevance_score * importance) + access_boost + provenance_boost

            # Store breakdown for debugging
            mem['_score_breakdown'] = {
                'recency': recency_score,
                'relevance': relevance_score,
                'importance': importance,
                'access_boost': access_boost,
                'provenance_boost': provenance_boost,
                'source_document': source_document,
                'final': final_score
            }

            scored.append({
                'memory': mem,
                'score': final_score
            })

        # === SORT AND SELECT TOP N ===

        scored.sort(key=lambda x: x['score'], reverse=True)

        dynamic_limit = max_memories - len(bedrock)
        dynamic_context = [s['memory'] for s in scored[:dynamic_limit]]

        # Set relevance_score for emotion weighting (normalize scores to 0-1 range)
        # Also tag confidence level for dynamic memories
        if scored:
            max_score = scored[0]['score']
            for item in scored[:dynamic_limit]:
                normalized = item['score'] / max_score if max_score > 0 else 0.0
                item['memory']['relevance_score'] = normalized

                # === CONFIDENCE DETERMINATION ===
                # Dynamic memories are 'inferred' unless marked as landmarks
                mem = item['memory']
                importance = mem.get('importance', 1.0)

                if importance >= 1.5:
                    # High-importance events are bedrock (landmarks, explicit "remember this")
                    mem['confidence'] = 'bedrock'  # 🔵 Manually marked significant
                else:
                    # Everything else is reconstructed from context
                    mem['confidence'] = 'inferred'  # 🟡 Probably accurate but reconstructed

        # === COMBINE AND RETURN ===

        final_memories = bedrock + dynamic_context

        # === COST FIX: SMART TRUNCATION ===
        # Previous comment said "DO NOT TRUNCATE" but that was breaking cost control
        # The real issue was truncating BEFORE bedrock was added. Now we truncate AFTER.
        MAX_TOTAL_MEMORIES = 250  # Reasonable limit to prevent $50/week API costs
        
        if len(final_memories) > MAX_TOTAL_MEMORIES:
            # Keep ALL identity facts (core identity should never be truncated)
            identity_mems = [m for m in final_memories if m.get('category') == 'identity']
            other_mems = [m for m in final_memories if m.get('category') != 'identity']
            
            # Fill remaining space with highest-relevance non-identity memories
            remaining_space = MAX_TOTAL_MEMORIES - len(identity_mems)
            truncated = identity_mems + other_mems[:remaining_space]
            
            print(f"[RECALL TRUNCATION] Reduced {len(final_memories)} -> {len(truncated)} memories (saved ~{(len(final_memories) - len(truncated)) * 20} tokens)")
            final_memories = truncated

        # === SMART GAP DETECTION ===
        # When very few relevant memories found, classify the reason
        GAP_THRESHOLD = 5  # If fewer than 5 relevant memories, investigate
        relevant_dynamic = [m for m in dynamic_context if m.get('relevance_score', 0) > 0.3]

        if len(relevant_dynamic) < GAP_THRESHOLD and len(search_words) > 2:
            # Sparse result - but is it a TRUE gap?
            gap_type = self._classify_sparse_result(user_input, search_words)

            if VERBOSE_DEBUG:
                print(f"[GAP DETECTION] Query: '{user_input}' | Relevant: {len(relevant_dynamic)} | Type: {gap_type}")

            if gap_type == 'true_gap':
                # Topic was discussed before but memories missing - true continuity break
                gap_marker = {
                    'type': 'gap_marker',
                    'confidence': 'unknown',  # Continuity break
                    'fact': f"[MEMORY GAP] '{user_input}' was discussed before but details are missing. Only {len(relevant_dynamic)} relevant memories found.",
                    'is_gap_marker': True,
                    'gap_type': 'true_gap',
                    'timestamp': datetime.now(),
                    'relevance_score': 0.0,
                    'importance': 0.5
                }
                # Insert at front so Kay sees it first
                final_memories.insert(0, gap_marker)

                if VERBOSE_DEBUG:
                    print(f"[MEMORY GAP] TRUE GAP detected - topic was important but memories missing")

            elif gap_type == 'never_discussed':
                # Topic hasn't come up - no gap marker, just a soft info note
                # This helps Kay understand it's new territory, not a continuity break
                info_marker = {
                    'type': 'info_marker',
                    'confidence': 'inferred',
                    'fact': f"[INFO] '{user_input}' hasn't been discussed before. {len(relevant_dynamic)} potentially related memories found.",
                    'is_info_marker': True,
                    'gap_type': 'never_discussed',
                    'timestamp': datetime.now(),
                    'relevance_score': 0.0,
                    'importance': 0.3
                }
                # Insert at front so Kay sees it
                final_memories.insert(0, info_marker)

                if VERBOSE_DEBUG:
                    print(f"[GAP DETECTION] Never discussed - new territory, not a gap")

            # 'low_salience' - don't mark anything, natural fade is fine
            # These were mentioned but weren't important enough to retain strongly
            elif VERBOSE_DEBUG:
                print(f"[GAP DETECTION] Low salience - natural memory fade, no marker needed")

        # === CONFIDENCE BREAKDOWN LOGGING ===
        if VERBOSE_DEBUG:
            # Count by confidence level
            bedrock_count = len([m for m in final_memories if m.get('confidence') == 'bedrock'])
            inferred_count = len([m for m in final_memories if m.get('confidence') == 'inferred'])
            unknown_count = len([m for m in final_memories if m.get('confidence') == 'unknown'])

            print(f"[UNIFIED MEMORY] Final: {len(bedrock)} bedrock + {len(dynamic_context)} dynamic = {len(final_memories)} total")
            print(f"[MEMORY CONFIDENCE] Bedrock: {bedrock_count} | Inferred: {inferred_count}" +
                  (f" | Gap: {unknown_count}" if unknown_count > 0 else ""))
            if scored:
                top_5_scores = [f"{s['score']:.3f}" for s in scored[:5]]
                print(f"[TOP SCORES] {top_5_scores}")

        return final_memories

    def _extract_key_terms(self, query: str) -> List[str]:
        """
        Extract meaningful terms from query for entity/history checking.
        Filters out stopwords and short words.

        Args:
            query: User query string

        Returns:
            List of key terms
        """
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'how',
            'when', 'where', 'why', 'do', 'does', 'did', 'about', 'with',
            'tell', 'me', 'your', 'you', 'my', 'i', 'we', 'us', 'our',
            'that', 'this', 'it', 'to', 'for', 'of', 'in', 'on', 'at'
        }
        words = query.lower().split()
        return [w.strip('?.,!') for w in words if w not in stopwords and len(w) > 2]

    def _check_entity_graph(self, terms: List[str]) -> List[str]:
        """
        Check if any query terms appear in entity graph.

        Args:
            terms: List of query terms to check

        Returns:
            List of terms that were found in entity graph
        """
        if not hasattr(self, 'entity_graph') or not self.entity_graph:
            return []

        mentions = []
        entity_names_lower = {e.lower() for e in self.entity_graph.entities.keys()}

        for term in terms:
            term_lower = term.lower()
            # Check if term matches any entity name
            if term_lower in entity_names_lower:
                mentions.append(term)
            # Check if term is in any entity's aliases
            else:
                for entity_name, entity_obj in self.entity_graph.entities.items():
                    if term_lower in {alias.lower() for alias in entity_obj.aliases}:
                        mentions.append(term)
                        break

        return mentions

    def _check_historical_mentions(self, terms: List[str]) -> List[Dict]:
        """
        Check episodic/semantic layers for any historical mentions of terms.

        Args:
            terms: List of query terms to check

        Returns:
            List of memories that contain the terms
        """
        mentions = []

        # Check all memory layers (TWO-TIER: working + long-term)
        all_memories = (
            self.memory_layers.working_memory +
            self.memory_layers.long_term_memory
        )

        for memory in all_memories:
            fact = memory.get('fact', '').lower()
            content = memory.get('content', '').lower()
            combined = fact + ' ' + content

            # Check if any term appears in this memory
            for term in terms:
                if term.lower() in combined:
                    mentions.append(memory)
                    break  # Don't count same memory multiple times

        return mentions

    def _get_avg_importance(self, memories: List[Dict]) -> float:
        """
        Get average importance of a set of memories.

        Args:
            memories: List of memory dicts

        Returns:
            Average importance score
        """
        if not memories:
            return 0.0
        importances = [m.get('importance', 1.0) for m in memories]
        return sum(importances) / len(importances)

    def get_document_provenance(self, query: str) -> Optional[Dict]:
        """
        Find which document(s) contain information matching the query.
        Enables "spatial memory" - Kay can answer "where did you read about X?"

        Args:
            query: Search query (e.g., "whale song", "Re's favorite color")

        Returns:
            Dict with provenance info if found, None otherwise:
            {
                'source_document': 'biology_notes.txt',
                'source_sections': [1, 3, 5],
                'import_time': '2 hours ago',
                'matching_facts': ['whales sing complex songs', 'songs can last 20 minutes'],
                'confidence': 'high'  # based on number of matches
            }
        """
        search_words = set(re.findall(r"\w+", query.lower()))
        if not search_words:
            return None

        # Collect all memories with provenance data (TWO-TIER: working + long-term)
        all_memories = (
            self.memory_layers.working_memory +
            self.memory_layers.long_term_memory
        )

        # Group matches by source document
        doc_matches = {}  # source_document -> list of matching memories

        for mem in all_memories:
            source_doc = mem.get('source_document')
            if not source_doc:
                continue

            # Check if memory matches query
            fact_text = mem.get('fact', '').lower()
            mem_words = set(re.findall(r"\w+", fact_text))
            overlap = len(search_words & mem_words)

            if overlap >= 1:  # At least 1 word match
                if source_doc not in doc_matches:
                    doc_matches[source_doc] = {
                        'memories': [],
                        'sections': set(),
                        'import_timestamp': mem.get('import_timestamp'),
                        'total_matches': 0
                    }

                doc_matches[source_doc]['memories'].append(mem)
                doc_matches[source_doc]['total_matches'] += overlap

                # Track section numbers
                section = mem.get('source_section')
                if section:
                    doc_matches[source_doc]['sections'].add(section)

        if not doc_matches:
            return None

        # Find the document with most matches
        best_doc = max(doc_matches.keys(), key=lambda d: doc_matches[d]['total_matches'])
        best_info = doc_matches[best_doc]

        # Format time since import
        import_ts = best_info.get('import_timestamp')
        if import_ts and isinstance(import_ts, (int, float)):
            hours_ago = (datetime.now().timestamp() - import_ts) / 3600
            if hours_ago < 1:
                time_str = f"{int(hours_ago * 60)} minutes ago"
            elif hours_ago < 24:
                time_str = f"{int(hours_ago)} hours ago"
            else:
                days = int(hours_ago / 24)
                time_str = f"{days} day{'s' if days != 1 else ''} ago"
        else:
            time_str = "recently"

        # Determine confidence based on match count
        match_count = len(best_info['memories'])
        if match_count >= 5:
            confidence = 'high'
        elif match_count >= 2:
            confidence = 'medium'
        else:
            confidence = 'low'

        return {
            'source_document': best_doc,
            'source_sections': sorted(best_info['sections']),
            'import_time': time_str,
            'matching_facts': [m.get('fact', '')[:100] for m in best_info['memories'][:5]],
            'match_count': match_count,
            'confidence': confidence
        }

    def get_recent_imports(self, hours: int = 24) -> List[Dict]:
        """
        Get documents imported within the last N hours.
        Useful for session continuity - "what have we been reading?"

        Args:
            hours: How far back to look (default 24 hours)

        Returns:
            List of document summaries with counts
        """
        cutoff = datetime.now().timestamp() - (hours * 3600)

        # Collect all memories with provenance data (TWO-TIER: working + long-term)
        all_memories = (
            self.memory_layers.working_memory +
            self.memory_layers.long_term_memory
        )

        # Group by document
        recent_docs = {}

        for mem in all_memories:
            source_doc = mem.get('source_document')
            import_ts = mem.get('import_timestamp')

            if not source_doc or not import_ts:
                continue

            if isinstance(import_ts, (int, float)) and import_ts >= cutoff:
                if source_doc not in recent_docs:
                    recent_docs[source_doc] = {
                        'document': source_doc,
                        'import_timestamp': import_ts,
                        'fact_count': 0,
                        'sections': set()
                    }

                recent_docs[source_doc]['fact_count'] += 1
                section = mem.get('source_section')
                if section:
                    recent_docs[source_doc]['sections'].add(section)

        # Convert to list and format
        result = []
        for doc_name, info in recent_docs.items():
            hours_ago = (datetime.now().timestamp() - info['import_timestamp']) / 3600
            if hours_ago < 1:
                time_str = f"{int(hours_ago * 60)} minutes ago"
            elif hours_ago < 24:
                time_str = f"{int(hours_ago)} hours ago"
            else:
                days = int(hours_ago / 24)
                time_str = f"{days} day{'s' if days != 1 else ''} ago"

            result.append({
                'document': doc_name,
                'imported': time_str,
                'fact_count': info['fact_count'],
                'sections': len(info['sections'])
            })

        # Sort by most recent
        result.sort(key=lambda x: recent_docs[x['document']]['import_timestamp'], reverse=True)

        return result

    def _classify_sparse_result(self, query: str, search_words: List[str]) -> str:
        """
        Classify why memory results are sparse.
        Distinguishes between true gaps, never-discussed topics, and natural fade.

        Args:
            query: Original user query
            search_words: Extracted search terms from query

        Returns:
            'true_gap' - topic was discussed before but memories missing
            'never_discussed' - topic hasn't come up, no memory expected
            'low_salience' - came up briefly, wasn't important, naturally faded
        """
        # Extract key terms from query
        query_terms = self._extract_key_terms(query)

        if not query_terms:
            # Can't classify without terms
            return 'never_discussed'

        # Check entity graph for mentions
        entity_mentions = self._check_entity_graph(query_terms)

        # Check episodic/semantic layers for any historical mentions
        historical_mentions = self._check_historical_mentions(query_terms)

        if VERBOSE_DEBUG:
            print(f"[GAP CLASSIFICATION] Query terms: {query_terms}")
            print(f"[GAP CLASSIFICATION] Entity mentions: {len(entity_mentions)} ({entity_mentions[:3]})")
            print(f"[GAP CLASSIFICATION] Historical mentions: {len(historical_mentions)}")

        if entity_mentions or len(historical_mentions) >= 3:
            # Topic WAS discussed before (either in entity graph or 3+ memory mentions)
            # Check importance of past mentions
            avg_importance = self._get_avg_importance(historical_mentions)

            if VERBOSE_DEBUG:
                print(f"[GAP CLASSIFICATION] Avg importance: {avg_importance:.2f}")

            # True gap criteria:
            # 1. High importance (>= 1.2) OR
            # 2. Entity exists (discussed enough to create entity) with avg importance >= 1.0
            if avg_importance >= 1.2 or (entity_mentions and avg_importance >= 1.0):
                # Was important, now missing = true gap
                return 'true_gap'
            else:
                # Was mentioned but low importance = natural fade
                return 'low_salience'
        else:
            # Fewer than 3 mentions and not in entity graph = never seriously discussed
            return 'never_discussed'

    def _determine_chunk_count(self, query: str) -> int:
        """
        Determine optimal chunk count based on query complexity.

        PHILOSOPHY: Not all queries need 100 chunks. Simple questions
        get fast answers with fewer chunks. Complex analysis gets more.

        RELEVANCE DEGRADATION: Vector search ranks by similarity.
        - Chunks 1-10: Highly relevant (core answer)
        - Chunks 11-30: Relevant context
        - Chunks 31-60: Related material
        - Chunks 61-100: Marginally related

        TOKEN BUDGET: Kay's context already uses ~95k chars before documents.
        Leaving 105k chars available. Smart allocation prevents waste.

        Args:
            query: User's query text

        Returns:
            Number of chunks to retrieve (20-100)
        """
        query_lower = query.lower()

        # Simple factual questions - just need the answer
        if any(pattern in query_lower for pattern in [
            "what is", "who is", "when did", "where is",
            "how many", "which", "name"
        ]):
            return 20  # ~12,740 chars, fast retrieval

        # Character/entity description - need context
        elif any(pattern in query_lower for pattern in [
            "tell me about", "describe", "explain",
            "what does", "who are"
        ]):
            return 50  # ~31,850 chars, good coverage

        # Relationship/interaction queries - need multiple contexts
        elif any(pattern in query_lower for pattern in [
            "relationship", "interact", "between",
            "connect", "related", "together"
        ]):
            return 75  # ~47,775 chars, comprehensive

        # Complex analytical questions - need broad view
        elif any(pattern in query_lower for pattern in [
            "analyze", "compare", "contrast", "theme",
            "why", "how come", "summarize", "overall"
        ]):
            return 100  # ~63,700 chars, maximum depth

        # Default - balanced approach
        else:
            return 50

    def retrieve_rag_chunks(self, query: str, n_results: int = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks from vector store (RAG).

        This allows Kay to "remember" uploaded documents without storing
        thousands of facts in structured memory.

        ADAPTIVE RETRIEVAL: Automatically determines optimal chunk count
        based on query complexity unless explicitly overridden.

        Args:
            query: User's query text
            n_results: Number of chunks (optional, auto-determined if None)

        Returns:
            List of RAG chunk dicts with keys: {
                "text": str,
                "source_file": str,
                "chunk_index": int,
                "distance": float
            }
        """
        if not self.vector_store:
            print("[RAG] Vector store not initialized - skipping RAG retrieval")
            return []

        if not query or not query.strip():
            return []

        # Adaptive chunk count determination
        if n_results is None:
            n_results = self._determine_chunk_count(query)
            print(f"[RAG] Adaptive retrieval: {n_results} chunks for query complexity")

        try:
            # Log query with chunk count
            print(f"[RAG] Query: \"{query[:60]}{'...' if len(query) > 60 else ''}\"")
            print(f"[RAG] Retrieving {n_results} chunks")

            # Query vector store with adaptive count
            results = self.vector_store.query(
                query_text=query,
                n_results=n_results
            )

            # Format for context building
            formatted_chunks = []
            for result in results:
                formatted_chunks.append({
                    "text": result["text"],
                    "source_file": result["metadata"].get("source_file", "unknown"),
                    "chunk_index": result["metadata"].get("chunk_index", 0),
                    "distance": result["distance"],
                    "type": "rag_chunk"  # Mark as RAG content
                })

            if formatted_chunks:
                # Log retrieval with scores
                scores = [f"{c['distance']:.2f}" for c in formatted_chunks[:3]]
                sources = set(c['source_file'] for c in formatted_chunks)
                print(f"[RAG] Retrieved {len(formatted_chunks)} chunks (scores: {', '.join(scores)})")
                print(f"[RAG] Sources: {', '.join(sources)}")

            # Store for context building
            self.last_rag_chunks = formatted_chunks

            return formatted_chunks

        except Exception as e:
            print(f"[RAG ERROR] Failed to retrieve chunks: {e}")
            import traceback
            traceback.print_exc()
            return []

    def store_document_summary(self, doc_id: str, filename: str, summary: str, entities: List[str]):
        """
        Store comprehensive document summary in semantic memory.

        This allows Kay to remember the "big picture" of a document
        without re-reading it every time. Stored summary can be
        retrieved alongside vector chunks for complete understanding.

        Args:
            doc_id: Document ID
            filename: Document filename
            summary: Comprehensive summary from sequential reading
            entities: Key characters/places/concepts extracted
        """
        import time

        # Create semantic memory entry
        summary_fact = {
            "type": "document_summary",
            "doc_id": doc_id,
            "filename": filename,
            "fact": f"Kay read '{filename}': {summary}",
            "user_input": f"[SEQUENTIAL READ] {filename}",
            "perspective": "shared",
            "importance": 0.95,  # High importance - comprehensive understanding
            "entities": entities,
            "tier": "long_term",  # Store in long-term memory
            "age": 0,
            "timestamp": time.time(),
            "turn": self.current_turn
        }

        # Store in long-term layer (TWO-TIER architecture)
        if hasattr(self, 'memory_layers') and self.memory_layers:
            self.memory_layers.long_term_memory.append(summary_fact)
        else:
            # Fallback if memory_layers not initialized
            self.memories.append(summary_fact)

        # Also store entities in entity graph if available
        if hasattr(self, 'entity_graph') and self.entity_graph:
            for entity in entities:
                try:
                    # Add entity to graph
                    self.entity_graph.add_entity(
                        entity_name=entity,
                        entity_type="document_entity",
                        source=f"document_summary:{filename}",
                        turn=self.current_turn
                    )

                    # Link entity to document
                    self.entity_graph.add_relationship(
                        entity1=entity,
                        relationship="appears_in",
                        entity2=filename,
                        turn=self.current_turn
                    )
                except Exception as e:
                    print(f"[MEMORY] Warning: Could not add entity {entity} to graph: {e}")

        # Save to disk
        self._save_to_disk()

        print(f"[MEMORY] Stored comprehensive summary for {filename}")
        print(f"[MEMORY] Summary length: {len(summary)} chars")
        print(f"[MEMORY] Tracked {len(entities)} entities from document")

    @measure_performance("memory_retrieval", target=0.150)
    def recall(self, agent_state, user_input, bias_cocktail=None, num_memories=30, use_multi_factor=True, include_rag=True, conversational_mode=False):
        """
        Recall memories for current turn.

        Args:
            agent_state: Current agent state
            user_input: User's message
            bias_cocktail: Emotional cocktail for biasing (defaults to agent_state.emotional_cocktail)
            num_memories: Number of memories to retrieve
            use_multi_factor: Use new multi-factor retrieval (True) or legacy retrieval (False)
            include_rag: Include RAG document chunks
            conversational_mode: If True, optimize for speed (voice chat).
                                 Reduces memory pool to 60-80 total for fast response.
                                 Working: all, Episodic: max 30-40, Semantic: max 15-20
        """
        bias_cocktail = bias_cocktail or agent_state.emotional_cocktail

        # Increment turn counter
        self.current_turn += 1

        # Apply temporal decay to memory layers (every 10 turns)
        # Skip in conversational mode for speed
        if not conversational_mode and self.current_turn % 10 == 0:
            self.memory_layers.apply_temporal_decay()
            print(f"[MEMORY] Applied temporal decay at turn {self.current_turn}")

        # PRIORITIZE IDENTITY FACTS: When user asks about relationships, fetch identity facts first
        # Skip heavy relationship search in conversational mode
        relationship_identity_facts = []
        if not conversational_mode:
            relationship_keywords = ["husband", "wife", "spouse", "dog", "cat", "pet", "partner", "married"]
            user_input_lower = user_input.lower()

            if any(keyword in user_input_lower for keyword in relationship_keywords):
                # User is asking about a relationship - prioritize identity facts
                all_identity_facts = self.identity.get_all_identity_facts()

                # Filter for relationship facts
                for fact in all_identity_facts:
                    fact_text = fact.get("fact", "").lower()
                    # Check if this identity fact contains any relationship keyword
                    if any(keyword in fact_text for keyword in relationship_keywords):
                        relationship_identity_facts.append(fact)

                if relationship_identity_facts:
                    print(f"[RECALL PRIORITY] Found {len(relationship_identity_facts)} relationship identity facts for query")

        # Use unified importance-based retrieval
        # VOICE MODE OPTIMIZATION:
        # - Total target: 60-80 memories instead of 190-228
        # - Working: all (current session) - typically 10-20
        # - Episodic: max 40 (recent context)
        # - Semantic: max 20 (most relevant only)
        if conversational_mode:
            effective_max = 60  # Hard cap for voice mode
            print(f"[RECALL] Voice mode: limiting to {effective_max} memories")
        else:
            effective_max = num_memories

        memories = self.retrieve_unified_importance(
            bias_cocktail,
            user_input,
            max_memories=effective_max,
            conversational_mode=conversational_mode
        )

        print(f"[RECALL CHECKPOINT 1] After retrieval: {len(memories)} memories (conversational={conversational_mode})")

        # === MEMORY LAYER TRACKING (TWO-TIER: working + long_term) ===
        # Track what types of memories are actually being used
        working_count = 0
        longterm_count = 0
        fact_count = 0  # Extracted facts (discrete knowledge)
        episodic_count = 0  # Full conversation turns
        imported_count = 0  # Imported from documents
        emotional_narrative_count = 0  # Emotional narrative chunks from imports

        for mem in memories:
            layer = mem.get("current_layer", "")
            mem_type = mem.get("type", "")
            is_imported = mem.get("is_imported", False)
            is_emotional_narrative = mem.get("is_emotional_narrative", False)

            # Count by layer (TWO-TIER: working + long_term)
            if layer == "working":
                working_count += 1
            elif layer in ["long_term", "longterm", "semantic", "episodic"]:
                # All non-working memories are long-term in two-tier architecture
                # Also catch legacy "semantic" and "episodic" labels from old data
                longterm_count += 1

            # Count by type
            if mem_type == "extracted_fact":
                fact_count += 1
            elif mem_type in ["conversation_turn", "full_turn"]:
                episodic_count += 1

            # Count imported content types
            if is_imported:
                imported_count += 1
                if is_emotional_narrative:
                    emotional_narrative_count += 1

        # Log usage statistics
        if len(memories) > 0:
            print(f"[MEMORY USAGE] Composition ({len(memories)} total):")
            print(f"  - Working layer: {working_count} ({working_count/len(memories)*100:.1f}%)")
            print(f"  - Long-term layer: {longterm_count} ({longterm_count/len(memories)*100:.1f}%)")
            print(f"  - Extracted facts: {fact_count} ({fact_count/len(memories)*100:.1f}%)")
            print(f"  - Conversation turns: {episodic_count} ({episodic_count/len(memories)*100:.1f}%)")
            if imported_count > 0:
                print(f"  - Imported: {imported_count}")
                if emotional_narrative_count > 0:
                    print(f"  - Emotional narratives: {emotional_narrative_count}")
        # === END MEMORY LAYER TRACKING ===

        # PRIORITIZE relationship identity facts (move to front, don't remove from list)
        if relationship_identity_facts:
            # Instead of deduplicating, REORDER memories to put relationship facts first
            memory_texts_to_facts = {m.get("fact", "").lower().strip(): m for m in memories}

            # Identify relationship facts that are in memories
            relationship_fact_texts = {f.get("fact", "").lower().strip() for f in relationship_identity_facts}

            # Separate memories into relationship and non-relationship
            prioritized = []
            non_prioritized = []

            for mem in memories:
                mem_text = mem.get("fact", "").lower().strip()
                if mem_text in relationship_fact_texts:
                    prioritized.append(mem)
                else:
                    non_prioritized.append(mem)

            # Reorder: relationship facts first, then others
            memories = prioritized + non_prioritized

            print(f"[RECALL PRIORITY] Prioritized {len(prioritized)} relationship facts to front of recall")

        # CRITICAL FIX: DO NOT TRUNCATE - retrieve_multi_factor already returns appropriate count
        # Old code: memories = memories[:num_memories + min(3, len(prioritized))]
        # This was cutting 498 memories → 33 memories
        print(f"[RECALL CHECKPOINT 2] Before storage in state: {len(memories)} memories (NO TRUNCATION)")

        grouped = {
            "user": [m for m in memories if m.get("perspective") == "user"],
            "kay": [m for m in memories if m.get("perspective") == "kay"],
            "shared": [m for m in memories if m.get("perspective") == "shared"],
        }
        agent_state.last_recalled_memories = memories
        agent_state.last_recalled_grouped = grouped

        # Add consolidated preferences to agent state
        agent_state.consolidated_preferences = self.preference_tracker.get_consolidated_preferences()
        agent_state.preference_contradictions = self.preference_tracker.get_contradictions()

        # NEW: Add entity contradictions to agent state (with resolution tracking)
        # NOTE: Logging suppressed since system now uses versioned facts instead
        entity_contradictions = self.entity_graph.get_all_contradictions(
            current_turn=self.current_turn,
            resolution_threshold=3,  # Require 3 consecutive consistent turns
            suppress_logging=True  # Suppress [CONTRADICTION RESOLVED] spam
        )
        agent_state.entity_contradictions = entity_contradictions

        # Only print NEW contradictions (not repeated warnings)
        if entity_contradictions:
            # Track previously logged contradictions
            if not hasattr(self, '_logged_contradictions'):
                self._logged_contradictions = set()

            # Find new contradictions
            current_contradiction_keys = set()
            new_contradictions = []

            for c in entity_contradictions:
                key = f"{c['entity']}.{c['attribute']}"
                current_contradiction_keys.add(key)
                if key not in self._logged_contradictions:
                    new_contradictions.append(c)

            # Print only new contradictions
            if new_contradictions:
                try:
                    print(f"[ENTITY GRAPH] NEW CONTRADICTIONS DETECTED ({len(new_contradictions)} new, {len(entity_contradictions)} total active)")
                    for contradiction in new_contradictions[:3]:  # Show first 3 new ones
                        print(f"  - {contradiction['entity']}.{contradiction['attribute']}: {contradiction['values']}")
                        if len(new_contradictions) > 3:
                            print(f"  ... and {len(new_contradictions) - 3} more")
                except UnicodeEncodeError:
                    print(f"[ENTITY GRAPH] NEW CONTRADICTIONS DETECTED ({len(new_contradictions)} new)")

                # Update logged contradictions
                self._logged_contradictions.update(current_contradiction_keys)
            elif VERBOSE_DEBUG:
                # In verbose mode, show that contradictions still exist
                print(f"[ENTITY GRAPH] {len(entity_contradictions)} active contradictions (no new ones this turn)")

            # Clean up resolved contradictions from tracking
            self._logged_contradictions = current_contradiction_keys

        # NEW: Retrieve RAG chunks from vector store (if enabled)
        # ADAPTIVE RETRIEVAL: n_results=None triggers auto-determination based on query complexity
        rag_chunks = []
        if include_rag and self.vector_store:
            rag_chunks = self.retrieve_rag_chunks(user_input, n_results=None)
            agent_state.rag_chunks = rag_chunks
        else:
            agent_state.rag_chunks = []

        # === PHASE 2A: TREE ACCESS TRACKING - DEPRECATED ===
        # Document retrieval now handled by llm_retrieval.py in main.py
        # Tree loading is no longer needed for document retrieval
        print("[TREE ACCESS TRACKING] DEPRECATED - Documents retrieved via llm_retrieval.py")

        # DISABLED: Tree access tracking
        return memories

    def extract_and_store_user_facts(self, agent_state, user_input: str) -> List[Dict[str, str]]:
        """
        Extract facts from user input BEFORE Kay responds.
        Uses TWO-TIER MEMORY STORAGE:

        EPISODIC (full_turn): Complete conversation turns with context
        SEMANTIC (extracted_fact): Discrete facts extracted from conversations

        Storage layers: working → episodic → semantic (automatic promotion)

        CRITICAL: This prevents Kay from hallucinating when user provides facts.
        """
        import time

        # Extract discrete facts from user input only
        extracted_facts = self._extract_facts(user_input, "")  # No response yet

        # ADDITIONAL: Regex-based relationship extraction for names
        # Catches patterns like "my dog's name is Saga", "my husband named John"
        user_text_lower = user_input.lower()

        # Pattern 1: "my [relation]'s name is [Name]" or "my [relation] named [Name]"
        rel_pattern = r"\bmy\s+(husband|wife|spouse|dog|cat)(?:'s)?\s*(?:name\s+is|named|is\s+named)?\s+([A-Za-z''\-]+)"
        rel_matches = re.finditer(rel_pattern, user_input, re.IGNORECASE)

        for match in rel_matches:
            relation = match.group(1).lower()
            person_name = match.group(2).strip()

            # Capitalize the name
            obj_name = person_name.capitalize()

            # Create relationship fact
            fact_text = f"{obj_name} is Re's {relation}"

            # Add to extracted facts with high importance
            relationship_fact = {
                "fact": fact_text,
                "perspective": "user",
                "topic": "relationships",
                "entities": ["Re", obj_name],
                "attributes": [{"entity": obj_name, "attribute": "relation_to_re", "value": relation}],
                "relationships": [{"entity1": "Re", "relation": "has_" + relation, "entity2": obj_name}],
                "is_regex_extracted": True  # Flag for tracking
            }

            # Check if this fact isn't already in extracted_facts
            if not any(f.get("fact", "").lower() == fact_text.lower() for f in extracted_facts):
                extracted_facts.append(relationship_fact)
                if VERBOSE_DEBUG:
                    print(f"[REGEX EXTRACTION] Caught relationship: {fact_text}")

        if VERBOSE_DEBUG:
            print(f"[MEMORY 2-TIER] Extracted {len(extracted_facts)} semantic facts from user input")

        # Collect all entities from extracted facts
        all_entities = set()
        for fact in extracted_facts:
            all_entities.update(fact.get('entities', []))

        # Determine if this is a list statement
        is_list_statement = len(all_entities) >= 3

        # Calculate importance
        if is_list_statement:
            importance_score = 0.9  # Very high importance for lists
            if VERBOSE_DEBUG:
                print(f"[MEMORY 2-TIER] List detected with {len(all_entities)} entities ({', '.join(list(all_entities)[:5])}) - boosting importance")
        else:
            importance_score = 0.5  # Default importance (no emotions yet)

        # === EPISODIC: FULL TURN (partial - response will be added in encode_memory) ===
        full_turn = {
            "type": "full_turn",
            "user_input": user_input,  # COMPLETE - never truncated
            "response": "",  # Will be filled in by encode_memory
            "turn_number": self.current_turn,
            "timestamp": time.time(),
            "emotional_cocktail": {},  # Will be filled later
            "emotion_tags": [],  # Will be filled later
            "entities": list(all_entities),
            "is_list": is_list_statement,
            "importance_score": importance_score,
            "is_partial": True,  # Flag indicating this needs response to be added
        }

        # CRITICAL FIX: Don't check full_turn for identity here
        # Identity checking happens in encode_memory() after facts are extracted
        # Full turns are conversations, not identity declarations

        self.memories.append(full_turn)
        self.memory_layers.add_memory(
            full_turn, 
            layer="working",
            session_order=self.current_session_order,  # SESSION TAGGING FIX
            session_id=self.current_session_id          # SESSION TAGGING FIX
        )

        if VERBOSE_DEBUG:
            print(f"[MEMORY 2-TIER] OK EPISODIC (full_turn partial): {len(user_input)} chars user (importance: {importance_score:.2f})")

        # === SEMANTIC: EXTRACTED FACTS ===
        for fact_data in extracted_facts:
            fact_text = fact_data.get("fact", "")
            fact_perspective = fact_data.get("perspective", "user")
            fact_topic = fact_data.get("topic", "general")

            # Track preferences if this is about Kay
            if fact_perspective == "kay":
                self.preference_tracker.track_preference(fact_text, fact_perspective, context="user_told_kay")

            # DOWNWEIGHT GENERIC RELATIONSHIP SUMMARIES
            # Generic: "Re has a husband", "Re has a dog" (no specific name)
            # Specific: "John is Re's husband", "Saga is Re's dog" (has specific name)
            is_generic_relationship = False
            fact_text_lower = fact_text.lower()

            # Detect generic relationship patterns (no specific name)
            # Generic pattern: starts with "Re has" or ends with "Re's [relation]" without a name
            generic_patterns = [
                r"^re has (a|an|\d+) (husband|wife|spouse|dog|cat|pet)s?\.?$",  # "Re has a dog"
                r"^re has (husband|wife|spouse|dog|cat|pet)s?\.?$",  # "Re has husband"
            ]

            for pattern in generic_patterns:
                if re.search(pattern, fact_text_lower):
                    is_generic_relationship = True
                    break

            # If it starts with a proper name (capitalized word), it's specific, not generic
            if re.match(r"^[A-Z][a-z]+\s+is\s+Re's", fact_text):
                is_generic_relationship = False

            # Calculate importance based on whether it's generic or specific
            if is_generic_relationship:
                fact_importance = 0.2  # Low importance for generic facts
                print(f"[MEMORY] Downweighting generic relationship: {fact_text[:60]}...")
            elif fact_data.get("is_regex_extracted"):
                # Regex-extracted specific relationships get high importance
                fact_importance = 0.9
            else:
                # Normal facts
                fact_importance = importance_score * 0.6

            fact_record = {
                "type": "extracted_fact",
                "fact": fact_text,  # COMPLETE - never truncated
                "perspective": fact_perspective,
                "topic": fact_topic,
                "entities": fact_data.get("entities", []),
                "attributes": fact_data.get("attributes", []),
                "relationships": fact_data.get("relationships", []),
                "parent_turn": self.current_turn,
                "importance_score": fact_importance,
                "emotion_tags": [],  # Will be filled later
            }

            # CRITICAL FIX: Check if this is an identity fact (permanent storage)
            # BUT: Do NOT store generic relationship summaries as identity facts
            if not is_generic_relationship:
                is_identity = self.identity.add_fact(fact_record)
                if is_identity:
                    fact_record["is_identity"] = True
                    fact_record["importance_score"] = 0.95  # Maximum importance
                    print(f"[IDENTITY] Stored identity fact: {fact_text[:60]}...")
            else:
                # Generic relationship - skip identity storage
                is_identity = False
                print(f"[IDENTITY] Skipping identity storage for generic fact: {fact_text[:60]}...")

            self.memories.append(fact_record)
            self.facts.append(fact_text)  # Backward compatibility
            self.memory_layers.add_memory(
                fact_record, 
                layer="working",
                session_order=self.current_session_order,  # SESSION TAGGING FIX
                session_id=self.current_session_id          # SESSION TAGGING FIX
            )

            print(f"[MEMORY 2-TIER] OK SEMANTIC (fact): [{fact_perspective}/{fact_topic}] {fact_text[:60]}...")

        # Summary log
        print(f"[MEMORY 2-TIER] === Turn {self.current_turn}: 1 episodic (full_turn) + {len(extracted_facts)} semantic (facts) ===")

        self._save_to_disk()
        return extracted_facts

    def encode(self, agent_state, user_input, response, emotion_tags=None, extra_metadata=None):
        active_emotions = [
            k for k, v in (agent_state.emotional_cocktail or {}).items()
            if v.get("intensity", 0) > 0.2
        ]
        self.encode_memory(user_input, response, agent_state.emotional_cocktail, active_emotions, agent_state=agent_state)
        return True

    def store_visual_memory(
        self,
        image_description: str,
        kay_response: str,
        emotional_response: Optional[List[str]] = None,
        entities_detected: Optional[List[str]] = None,
        image_filename: Optional[str] = None,
        agent_state=None
    ) -> Dict:
        """
        Store a memory of seeing an image.

        Integrates with behavioral emotion patterns (NOT neurochemicals).
        Visual memories are deliberate sharing and get slight importance boost.

        Args:
            image_description: Description of what Kay saw
            kay_response: Kay's full response to the image
            emotional_response: List of emotions Kay reported feeling
            entities_detected: List of entities visible in image
            image_filename: Original filename (for reference)
            agent_state: Current agent state for emotional context

        Returns:
            The created memory entry dict
        """
        # Build memory content
        memory_content = f"[Visual] {image_description}"

        # Calculate emotional valence from behavioral patterns
        valence = 0.0
        if emotional_response:
            positive = {'joy', 'curiosity', 'wonder', 'tenderness', 'delight', 'warmth', 'love'}
            negative = {'unease', 'sadness', 'anger', 'fear', 'disgust', 'discomfort'}
            pos_count = sum(1 for e in emotional_response if e.lower() in positive)
            neg_count = sum(1 for e in emotional_response if e.lower() in negative)
            if pos_count + neg_count > 0:
                valence = (pos_count - neg_count) / (pos_count + neg_count)

        # Create memory entry with visual metadata
        memory_entry = {
            'fact': memory_content,
            'type': 'visual',
            'is_visual': True,
            'source_file': image_filename or 'unknown',
            'entities': entities_detected or [],
            'importance': 1.2,  # Visual memories get slight boost - deliberate sharing
            'confidence': 'bedrock',  # Current session visual - definitely happened
            'perspective': 'shared',  # Visual shared between Re and Kay
            'emotional_context': emotional_response or [],
            'valence': valence,
            'kay_response_excerpt': kay_response[:200] if kay_response else '',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'turn': agent_state.turn_count if agent_state and hasattr(agent_state, 'turn_count') else 0
        }

        # Store in working memory (current session = high priority)
        self.memory_layers.add_memory(memory_entry, layer='working')

        # Track entities in entity graph
        if entities_detected and self.entity_graph:
            visual_entity_id = f"visual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.entity_graph.add_entity(visual_entity_id, entity_type='visual_memory')
            self.entity_graph.set_attribute(visual_entity_id, 'description', image_description[:100])
            self.entity_graph.set_attribute(visual_entity_id, 'emotional_valence', valence)

            # Track relationships
            self.entity_graph.add_relationship('Kay', 'witnessed', visual_entity_id)
            self.entity_graph.add_relationship('Re', 'shared', visual_entity_id)

            # Connect detected entities to visual
            for entity in entities_detected:
                self.entity_graph.add_relationship(visual_entity_id, 'contains', entity)

        # Add to main memory store
        self.memories.append(memory_entry)
        self._save_to_disk()

        print(f"[VISUAL MEMORY] Stored: {image_description[:50]}...")
        print(f"[VISUAL MEMORY] Emotional context: {emotional_response}")
        print(f"[VISUAL MEMORY] Entities: {entities_detected}")

        return memory_entry

    def consolidate(self, agent_state):
        pass

    def _calculate_ultramap_importance(self, emotional_cocktail: dict, emotion_tags: list) -> float:
        """
        Calculate memory importance using ULTRAMAP rules from emotion_engine.

        Combines:
        - Priority: How important this emotion type is
        - Temporal Weight: How long this emotion's influence lasts
        - Duration Sensitivity: How much time affects this emotion
        - Intensity: Current emotional intensity

        Returns:
            Importance score (0.0 to 2.0+)
        """
        if not emotion_tags or not self.emotion_engine:
            return 0.1  # Baseline for neutral memories

        total_priority = 0.0
        total_temporal = 0.0
        total_duration = 0.0
        total_intensity = 0.0
        count = 0

        for emotion_name in emotion_tags:
            # Get ULTRAMAP memory rules for this emotion
            rules = self.emotion_engine.get_memory_rules(emotion_name)

            # Get current intensity from cocktail
            intensity = 0.0
            if emotion_name in emotional_cocktail:
                intensity = emotional_cocktail[emotion_name].get("intensity", 0.0)

            # Accumulate weighted factors
            total_priority += rules.get("priority", 0.5)
            total_temporal += rules.get("temporal_weight", 1.0)
            total_duration += rules.get("duration_sensitivity", 1.0)
            total_intensity += intensity
            count += 1

        if count == 0:
            return 0.1

        # Calculate averages
        avg_priority = total_priority / count
        avg_temporal = total_temporal / count
        avg_duration = total_duration / count
        avg_intensity = total_intensity / count

        # Combined importance score
        # Priority sets baseline, temporal/duration extend it, intensity amplifies
        importance = (avg_priority * avg_temporal * avg_duration) * (1.0 + avg_intensity)

        return min(importance, 2.0)  # Cap at 2.0

    def _emotion_to_glyph(self, emotion_name: str) -> str:
        """
        Convert emotion name to glyph representation.

        Args:
            emotion_name: Name of emotion (e.g., "curiosity", "affection")

        Returns:
            Glyph representation (e.g., "🔮" for curiosity, "💗" for affection)
        """
        emotion_glyphs = {
            "curiosity": "🔮",
            "affection": "💗",
            "joy": "😊",
            "excitement": "⚡",
            "contentment": "😌",
            "gratitude": "🙏",
            "amusement": "😄",
            "pride": "🌟",
            "relief": "😮‍💨",
            "hope": "🌈",
            "interest": "👀",
            "surprise": "😲",
            "confusion": "🤔",
            "concern": "😟",
            "anxiety": "😰",
            "frustration": "😤",
            "disappointment": "😞",
            "sadness": "😢",
            "guilt": "😔",
            "shame": "😳",
            "anger": "😠",
            "fear": "😨",
            "disgust": "🤢",
            "contempt": "😒",
            "loneliness": "🥀",
            "boredom": "😑",
            "restlessness": "🌀",
            "overwhelm": "🌊",
            "numbness": "🧊",
        }

        return emotion_glyphs.get(emotion_name.lower(), "💭")  # Default to thought bubble

    def _generate_glyph_summary(self, emotional_cocktail: dict, extracted_facts: list, is_list: bool) -> str:
        """
        Generate compressed glyph representation of a conversation turn.

        Args:
            emotional_cocktail: Current emotional state
            extracted_facts: List of extracted fact dictionaries
            is_list: Whether this turn contains a list (3+ entities)

        Returns:
            Glyph string (e.g., "📋!!! 🔮(0.8) 🐱(5x) 🐕(1x)")
        """
        components = []

        # List indicator (if applicable)
        if is_list:
            components.append("📋!!!")

        # Emotional glyphs (top 3 emotions by intensity)
        if emotional_cocktail:
            sorted_emotions = sorted(
                emotional_cocktail.items(),
                key=lambda x: x[1].get("intensity", 0),
                reverse=True
            )

            for emotion, data in sorted_emotions[:3]:
                intensity = data.get("intensity", 0)
                if intensity > 0.3:
                    glyph = self._emotion_to_glyph(emotion)
                    components.append(f"{glyph}({intensity:.1f})")

        # Entity type counting
        entity_types = {}
        for fact in extracted_facts:
            # Count entity types from attributes
            for attr in fact.get("attributes", []):
                attr_name = attr.get("attribute", "")
                if attr_name in ["species", "type"]:
                    entity_type = attr.get("value", "unknown")
                    entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

        # Entity glyphs
        type_to_glyph = {
            "cat": "🐱",
            "dog": "🐕",
            "person": "👤",
            "place": "📍",
            "thing": "📦"
        }

        for entity_type, count in entity_types.items():
            glyph = type_to_glyph.get(entity_type.lower(), "•")
            components.append(f"{glyph}({count}x)")

        return " ".join(components) if components else "💭"

    def log_memory_entry(self, conversation_turn: dict, agent_state, memory_stack: list = None) -> Dict[str, Any]:
        """
        Create a structured memory entry with subjective meaning and emotional context.

        This refactored approach captures not just surface text and facts, but also:
        - Parsed meaning (interpretation in context)
        - Affect signature (primary/secondary emotions with intensities)
        - Emotional context (why this matters emotionally)
        - Semantic facts (entities, relationships, attributes)

        Args:
            conversation_turn: Dict with keys:
                - "speaker": "user" or "kay"
                - "raw_text": The verbatim utterance
                - "context": Optional previous context for interpretation
            agent_state: Current AgentState with emotional_cocktail
            memory_stack: List of previous structured_turn records for context

        Returns:
            Structured memory entry dict
        """
        import time
        from datetime import datetime

        speaker = conversation_turn.get("speaker", "user")
        raw_text = conversation_turn.get("raw_text", "")
        prev_context = conversation_turn.get("context", "")

        # Extract semantic facts using existing helper
        if speaker == "user":
            # User utterance - extract facts
            extracted_facts = self._extract_facts_with_entities(raw_text, "")
        else:
            # Kay's response - extract from perspective of Kay speaking
            extracted_facts = self._extract_facts_with_entities("", raw_text)

        # Extract affect signature from emotional cocktail
        affect_signature = self._extract_affect_signature(agent_state.emotional_cocktail)

        # Generate parsed meaning and emotional context using LLM
        parsed_meaning, emotional_context = self._generate_meaning_and_context(
            raw_text,
            speaker,
            affect_signature,
            prev_context,
            memory_stack or []
        )

        # Calculate importance score
        importance = self._calculate_turn_importance(
            agent_state.emotional_cocktail,
            list(affect_signature.get("secondary", {}).keys()) + [affect_signature.get("primary", "")],
            len(extracted_facts)
        )

        # Build structured memory entry
        memory_entry = {
            "type": "structured_turn",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "speaker": speaker,
            "raw_text": raw_text,
            "parsed_meaning": parsed_meaning,
            "affect_signature": affect_signature,
            "emotional_context": emotional_context,
            "semantic_facts": [
                {
                    "fact": f.get("fact", ""),
                    "entities": f.get("entities", []),
                    "relationships": f.get("relationships", []),
                    "attributes": f.get("attributes", []),
                    "topic": f.get("topic", "general")
                }
                for f in extracted_facts
            ],
            "turn_number": self.current_turn,
            "importance_score": importance,
            "current_layer": "working",

            # Backward compatibility fields
            "emotion_tags": [affect_signature.get("primary", "")] + list(affect_signature.get("secondary", {}).keys()),
            "emotional_cocktail": agent_state.emotional_cocktail,
            "entities": list(set(e for f in extracted_facts for e in f.get("entities", []))),
        }

        # Add to working layer
        self.memory_layers.add_memory(memory_entry, layer="working")
        self.memories.append(memory_entry)

        print(f"[MEMORY STRUCTURED] Logged {speaker} turn: '{raw_text[:50]}...'")
        print(f"  - Meaning: {parsed_meaning[:60]}...")
        print(f"  - Affect: {affect_signature.get('primary')} (primary)")
        print(f"  - Context: {emotional_context[:60]}...")
        print(f"  - Facts: {len(extracted_facts)}")

        return memory_entry

    def _extract_affect_signature(self, emotional_cocktail: dict) -> Dict[str, Any]:
        """
        Extract affect signature from emotional cocktail.

        Returns dict with:
        - primary: Strongest emotion name
        - secondary: Dict of {emotion: intensity} for other active emotions
        - valence: Overall positive/negative (-1.0 to 1.0)
        - arousal: Overall activation level (0.0 to 1.0)
        """
        if not emotional_cocktail:
            return {
                "primary": "neutral",
                "secondary": {},
                "valence": 0.0,
                "arousal": 0.0
            }

        # Sort emotions by intensity
        sorted_emotions = sorted(
            emotional_cocktail.items(),
            key=lambda x: x[1].get("intensity", 0),
            reverse=True
        )

        primary_emotion = sorted_emotions[0][0] if sorted_emotions else "neutral"
        primary_intensity = sorted_emotions[0][1].get("intensity", 0) if sorted_emotions else 0

        # Secondary emotions (intensity > 0.2, excluding primary)
        secondary = {
            emotion: data.get("intensity", 0)
            for emotion, data in sorted_emotions[1:]
            if data.get("intensity", 0) > 0.2
        }

        # Calculate valence (positive/negative) - simplified mapping
        positive_emotions = {"joy", "affection", "contentment", "gratitude", "pride", "hope", "excitement", "amusement", "relief"}
        negative_emotions = {"sadness", "anger", "fear", "anxiety", "frustration", "disappointment", "guilt", "shame", "loneliness"}

        valence_sum = 0.0
        for emotion, data in emotional_cocktail.items():
            intensity = data.get("intensity", 0)
            if emotion.lower() in positive_emotions:
                valence_sum += intensity
            elif emotion.lower() in negative_emotions:
                valence_sum -= intensity

        # Normalize valence to -1.0 to 1.0
        valence = max(-1.0, min(1.0, valence_sum / len(emotional_cocktail) if emotional_cocktail else 0))

        # Calculate arousal (activation level)
        arousal = sum(data.get("intensity", 0) for data in emotional_cocktail.values()) / len(emotional_cocktail) if emotional_cocktail else 0
        arousal = min(1.0, arousal)

        return {
            "primary": primary_emotion,
            "primary_intensity": primary_intensity,
            "secondary": secondary,
            "valence": round(valence, 2),
            "arousal": round(arousal, 2)
        }

    def _generate_meaning_and_context(
        self,
        raw_text: str,
        speaker: str,
        affect_signature: dict,
        prev_context: str,
        memory_stack: list
    ) -> tuple:
        """
        Generate parsed meaning and emotional context using LLM.

        Args:
            raw_text: The utterance to interpret
            speaker: "user" or "kay"
            affect_signature: Affect signature dict
            prev_context: Previous conversation context
            memory_stack: List of recent structured_turn records

        Returns:
            Tuple of (parsed_meaning, emotional_context)
        """
        if not client or not MODEL:
            # Fallback if no LLM available
            return (
                f"{speaker} said: {raw_text[:50]}...",
                "Context unavailable (no LLM)"
            )

        # Build context from memory stack (last 3 turns)
        recent_context = ""
        if memory_stack:
            for turn in memory_stack[-3:]:
                recent_context += f"\n{turn.get('speaker')}: {turn.get('raw_text', '')[:80]}..."

        # Build prompt for interpretation
        interpretation_prompt = f"""You are analyzing a conversation turn to extract its subjective meaning and emotional significance.

CONVERSATION CONTEXT (recent turns):
{recent_context if recent_context else "(first turn)"}

CURRENT TURN:
Speaker: {speaker.upper()}
Raw text: "{raw_text}"
Emotional state: {affect_signature.get('primary')} (primary), valence={affect_signature.get('valence')}, arousal={affect_signature.get('arousal')}

YOUR TASK:
1. PARSED MEANING: Write a concise interpretation of what this utterance MEANS in context (not just what was said, but the intent, implication, or significance). Focus on the "why" and "what for" behind the words.

2. EMOTIONAL CONTEXT: Explain why this turn matters emotionally - what feelings are at play, what relational dynamics are present, or what psychological significance this has.

GUIDELINES:
- Be concise (1-2 sentences per section)
- Capture subjective meaning, not just surface content
- Consider speaker's emotional state
- Think about continuity with previous turns

OUTPUT FORMAT (JSON):
{{
  "parsed_meaning": "...",
  "emotional_context": "..."
}}

Generate interpretation now:"""

        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=300,
                temperature=0.4,
                system="You are a conversational memory analyst. Extract meaning and emotional context from conversation turns. Output valid JSON only.",
                messages=[{"role": "user", "content": interpretation_prompt}],
            )

            text = resp.content[0].text.strip()

            # Clean potential markdown
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            text = text.strip()

            # Parse JSON
            result = json.loads(text)
            parsed_meaning = result.get("parsed_meaning", raw_text[:100] + "...")
            emotional_context = result.get("emotional_context", "Emotional context unavailable")

            return (parsed_meaning, emotional_context)

        except Exception as e:
            print(f"[WARNING] Meaning/context generation failed: {e}")
            # Fallback
            return (
                f"{speaker} said: {raw_text[:80]}..." if len(raw_text) > 80 else raw_text,
                f"Emotional state: {affect_signature.get('primary')}"
            )

    def detect_threads(self, recent_turns: int = 20) -> List[Dict[str, Any]]:
        """
        Detect ongoing conversation threads (Flamekeeper integration).

        Threads are clusters of memories sharing entities and topics.
        Useful for identifying ongoing sagas like "wrapper debugging" or "Chrome stories".

        Args:
            recent_turns: How many recent turns to analyze

        Returns:
            List of detected threads with metadata:
            [{
                "thread_id": "wrapper_persistence_saga",
                "thread_label": "Goals - Re, wrapper",
                "thread_status": "open",  # "open", "dormant", "resolved"
                "thread_coherence": 0.85,  # 0-1 score
                "thread_start_turn": 45,
                "thread_last_turn": 67,
                "thread_message_count": 12,
                "thread_entities": ["Re", "wrapper", "persistence"]
            }]
        """
        # Get recent memories
        recent_memories = sorted(
            [m for m in self.memories if m.get("turn_number", 0) > self.current_turn - recent_turns],
            key=lambda m: m.get("turn_number", 0)
        )

        if not recent_memories:
            return []

        # Cluster by entities and topics
        threads = {}

        for mem in recent_memories:
            entities = mem.get("entities", [])
            topic = mem.get("topic", "general")

            # Skip glyph summaries
            if mem.get("type") == "glyph_summary":
                continue

            # Generate thread key from entities + topic
            # Sort entities for consistent key generation
            entity_key = '-'.join(sorted(entities[:2])) if entities else "general"
            thread_key = f"{topic}_{entity_key}"

            if thread_key not in threads:
                threads[thread_key] = {
                    "thread_id": thread_key,
                    "thread_label": f"{topic.title()} - {', '.join(entities[:3]) if entities else 'general'}",
                    "memories": [],
                    "entities": set(),
                    "topics": set(),
                    "turn_range": [float('inf'), 0]
                }

            threads[thread_key]["memories"].append(mem)
            threads[thread_key]["entities"].update(entities)
            threads[thread_key]["topics"].add(topic)

            turn = mem.get("turn_number", 0)
            threads[thread_key]["turn_range"][0] = min(threads[thread_key]["turn_range"][0], turn)
            threads[thread_key]["turn_range"][1] = max(threads[thread_key]["turn_range"][1], turn)

        # Filter to multi-turn threads (≥ 3 messages)
        significant_threads = []

        for thread_data in threads.values():
            if len(thread_data["memories"]) >= 3:
                # Calculate coherence (fewer topics = higher coherence)
                # Coherence = 1.0 - (topic_diversity)
                topic_diversity = len(thread_data["topics"]) / max(len(thread_data["memories"]), 1)
                coherence = 1.0 - min(topic_diversity, 1.0)

                # Detect status
                latest_turn = thread_data["turn_range"][1]
                if latest_turn >= self.current_turn - 3:
                    status = "open"  # Active in last 3 turns
                elif latest_turn >= self.current_turn - 10:
                    status = "dormant"  # Not recent but not old
                else:
                    status = "resolved"  # Old thread

                significant_threads.append({
                    "thread_id": thread_data["thread_id"],
                    "thread_label": thread_data["thread_label"],
                    "thread_status": status,
                    "thread_coherence": round(coherence, 2),
                    "thread_start_turn": thread_data["turn_range"][0],
                    "thread_last_turn": thread_data["turn_range"][1],
                    "thread_message_count": len(thread_data["memories"]),
                    "thread_entities": list(thread_data["entities"])[:5]
                })

        # Sort by recency (most recent threads first)
        significant_threads.sort(key=lambda t: t["thread_last_turn"], reverse=True)

        return significant_threads

    def _calculate_base_score(self, mem: Dict[str, Any], bias_cocktail: dict, user_input: str) -> float:
        """
        Calculate base retrieval score for a memory using existing multi-factor logic.

        This is extracted from the original calculate_multi_factor_score logic.

        Args:
            mem: Memory record
            bias_cocktail: Current emotional cocktail
            user_input: User's query

        Returns:
            Base score (0.0 to ~2.0)
        """
        search_words = set(re.findall(r"\w+", user_input.lower()))
        if not search_words:
            return 0.0

        # === 1. EMOTIONAL RESONANCE (40%) ===
        tags = mem.get("emotion_tags") or []
        emotion_score = sum(bias_cocktail.get(tag, {}).get("intensity", 0.0) for tag in tags)
        emotional_weight = 0.4

        # === 2. SEMANTIC SIMILARITY (25%) ===
        # For full_turn type, search in user_input + response
        # For extracted_fact type, search in fact
        # For structured_turn type, search in raw_text + parsed_meaning
        if mem.get("type") == "full_turn":
            text_blob = (mem.get("user_input", "") + " " + mem.get("response", "")).lower()
        elif mem.get("type") == "structured_turn":
            text_blob = (mem.get("raw_text", "") + " " + mem.get("parsed_meaning", "")).lower()
        elif mem.get("type") == "extracted_fact":
            text_blob = mem.get("fact", "").lower()
        else:
            text_blob = (mem.get("fact", "") + " " + mem.get("user_input", "") + " " + mem.get("response", "")).lower()

        keyword_matches = sum(1 for w in search_words if w in text_blob)
        keyword_overlap = keyword_matches / len(search_words) if search_words else 0.0
        semantic_weight = 0.25

        # === 3. IMPORTANCE (20%) ===
        importance = mem.get("importance_score", 0.0)
        importance_weight = 0.20

        # === 4. RECENCY (10%) ===
        access_count = mem.get("access_count", 0)
        recency_score = min(access_count / 10.0, 1.0)
        recency_weight = 0.10

        # === 5. ENTITY PROXIMITY (5%) ===
        query_entities = [word for word in search_words if word[0].isupper() or word in ["re", "kay"]]
        mem_entities = set(mem.get("entities", []))
        query_entity_set = set(query_entities)
        shared_entities = mem_entities.intersection(query_entity_set)
        entity_score = len(shared_entities) / max(len(query_entity_set), 1) if query_entity_set else 0.0
        entity_weight = 0.05

        # === COMBINED SCORE ===
        total_score = (
            emotion_score * emotional_weight +
            keyword_overlap * semantic_weight +
            importance * importance_weight +
            recency_score * recency_weight +
            entity_score * entity_weight
        )

        return total_score