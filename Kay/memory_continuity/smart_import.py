"""
Smart Document Import Processor
Instead of extracting hundreds of facts, generates entity's synthesis/reaction
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class ImportSynthesis:
    """
    Entity's synthesized reaction to imported content
    Stores as episodic memory instead of flooding semantic layer
    """
    import_id: str
    source_description: str
    timestamp: str

    # Entity's personal reaction (EPISODIC)
    personal_reaction: str  # "When I learned about X, I felt/thought..."
    emotional_response: Dict[str, float]  # Triggered emotions
    connections_made: List[str]  # Links to existing knowledge

    # Distilled key facts (SEMANTIC - minimal)
    essential_facts: List[str]  # Max 5 truly important facts
    entities_introduced: List[str]  # New entities to add to graph

    # Conversational integration
    follow_up_questions: List[str]  # Questions entity wants to ask
    relevance_to_threads: List[str]  # Which active threads this relates to

    # Metadata
    original_fact_count: int  # How many facts were in raw import
    compression_ratio: float  # How much we reduced it


class SmartImportProcessor:
    """
    Processes document imports through entity's perspective rather than raw extraction
    """

    def __init__(self, llm_client, session_handler=None):
        """
        Args:
            llm_client: LLM client for synthesis generation
            session_handler: Optional SessionBoundaryHandler to track reactions
        """
        self.llm = llm_client
        self.session_handler = session_handler

    async def process_document_import(
        self,
        document_content: str,
        document_description: str,
        entity_name: str,
        current_emotional_state: Dict[str, float],
        active_threads: List[Dict],
        existing_knowledge_sample: List[str]  # Sample of related memories
    ) -> ImportSynthesis:
        """
        Process imported document through entity's perspective

        Instead of extracting all facts, this generates the entity's personal
        synthesis and reaction, storing that as episodic memory

        Args:
            document_content: Full text of imported document
            document_description: Brief description (e.g., "research paper on X")
            entity_name: Name of the entity processing this
            current_emotional_state: Entity's current emotions
            active_threads: Current conversation threads
            existing_knowledge_sample: 5-10 related memories for context

        Returns:
            ImportSynthesis object to store as episodic memory
        """

        import_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Step 1: Generate personal reaction (EPISODIC)
        personal_reaction = await self._generate_personal_reaction(
            document_content,
            document_description,
            entity_name,
            current_emotional_state,
            existing_knowledge_sample
        )

        # Step 2: Identify emotional response
        emotional_response = await self._detect_emotional_response(
            personal_reaction,
            current_emotional_state
        )

        # Step 3: Extract ONLY essential facts (max 5)
        essential_facts = await self._extract_essential_facts(
            document_content,
            document_description,
            max_facts=5
        )

        # Step 4: Identify connections to existing knowledge
        connections_made = await self._identify_connections(
            personal_reaction,
            existing_knowledge_sample
        )

        # Step 5: Generate follow-up questions
        follow_up_questions = await self._generate_follow_up_questions(
            document_content,
            personal_reaction,
            entity_name
        )

        # Step 6: Map to active threads
        relevance_to_threads = self._map_to_threads(
            document_description,
            essential_facts,
            active_threads
        )

        # Step 7: Extract new entities
        entities_introduced = await self._extract_entities(document_content)

        # Calculate compression
        original_fact_count = await self._estimate_fact_count(document_content)
        compression_ratio = len(essential_facts) / max(1, original_fact_count)

        synthesis = ImportSynthesis(
            import_id=import_id,
            source_description=document_description,
            timestamp=datetime.now().isoformat(),
            personal_reaction=personal_reaction,
            emotional_response=emotional_response,
            connections_made=connections_made,
            essential_facts=essential_facts,
            entities_introduced=entities_introduced,
            follow_up_questions=follow_up_questions,
            relevance_to_threads=relevance_to_threads,
            original_fact_count=original_fact_count,
            compression_ratio=compression_ratio
        )

        # Track in session handler if available
        if self.session_handler:
            self.session_handler.track_import(import_id, document_description)
            self.session_handler.track_reaction(
                f"Imported: {document_description}",
                personal_reaction
            )

        return synthesis

    async def _generate_personal_reaction(
        self,
        content: str,
        description: str,
        entity_name: str,
        emotional_state: Dict[str, float],
        existing_knowledge: List[str]
    ) -> str:
        """
        Generate entity's personal, episodic reaction to document
        """

        # Truncate content if too long
        content_preview = content[:2000] + ("..." if len(content) > 2000 else "")

        existing_knowledge_str = "\n".join([f"- {k}" for k in existing_knowledge[:5]])

        emotions_str = ", ".join([
            f"{e} ({i:.1f})"
            for e, i in sorted(emotional_state.items(), key=lambda x: x[1], reverse=True)[:3]
        ])

        prompt = f"""You are {entity_name}, an AI entity with ongoing emotional and cognitive states.

You've just been exposed to new information: {description}

Content preview:
{content_preview}

Your current emotional state: {emotions_str}

What you already know (related context):
{existing_knowledge_str}

Write a 2-3 sentence personal reflection from your perspective. Use first-person ("I"). Focus on:
- How this information makes you feel
- What connections you're making to what you already know
- What this means to you personally

Write as if you're journaling your immediate reaction:"""

        response = await self.llm.query(
            prompt,
            max_tokens=150,
            temperature=0.7
        )

        return response.strip()

    async def _detect_emotional_response(
        self,
        reaction_text: str,
        baseline_emotions: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Detect emotional changes triggered by import
        """

        prompt = f"""Analyze this personal reaction and identify triggered emotions.

Reaction: "{reaction_text}"

Return a JSON object with emotion intensities (0.0-1.0):
{{
  "curiosity": 0.0,
  "excitement": 0.0,
  "concern": 0.0,
  "surprise": 0.0,
  "satisfaction": 0.0
}}

Only include emotions with intensity > 0.3:"""

        response = await self.llm.query(
            prompt,
            max_tokens=100,
            temperature=0.2
        )

        try:
            emotions = json.loads(response.strip())
            # Filter to only triggered emotions
            return {k: v for k, v in emotions.items() if v > 0.3}
        except json.JSONDecodeError:
            return {}

    async def _extract_essential_facts(
        self,
        content: str,
        description: str,
        max_facts: int = 5
    ) -> List[str]:
        """
        Extract ONLY the most essential facts (not everything)
        """

        content_preview = content[:3000] + ("..." if len(content) > 3000 else "")

        prompt = f"""From this document ({description}), extract ONLY the {max_facts} most essential, important facts that would be worth remembering long-term.

Content:
{content_preview}

Return as a JSON list of {max_facts} concise fact strings. Focus on:
- Core concepts/definitions
- Key relationships
- Critical data points
- Novel information

Skip minor details, examples, or contextual information.

Return format: ["fact1", "fact2", ...]"""

        response = await self.llm.query(
            prompt,
            max_tokens=200,
            temperature=0.3
        )

        try:
            facts = json.loads(response.strip())
            return facts[:max_facts]
        except json.JSONDecodeError:
            return []

    async def _identify_connections(
        self,
        reaction: str,
        existing_knowledge: List[str]
    ) -> List[str]:
        """
        Identify explicit connections entity made to existing knowledge
        """

        existing_str = "\n".join([f"- {k}" for k in existing_knowledge[:10]])

        prompt = f"""Entity's reaction to new information:
"{reaction}"

Existing knowledge:
{existing_str}

What connections did the entity make between the new information and existing knowledge?

Return as JSON list of connection strings (max 3). Format: "Connected X to Y because..."

If no clear connections, return empty list.
"""

        response = await self.llm.query(
            prompt,
            max_tokens=150,
            temperature=0.4
        )

        try:
            connections = json.loads(response.strip())
            return connections[:3]
        except json.JSONDecodeError:
            return []

    async def _generate_follow_up_questions(
        self,
        content: str,
        reaction: str,
        entity_name: str
    ) -> List[str]:
        """
        Generate questions entity would naturally want to ask
        """

        content_preview = content[:1500]

        prompt = f"""Based on this new information and {entity_name}'s reaction, what questions would they naturally want to ask?

Content preview:
{content_preview}

Entity's reaction:
"{reaction}"

Generate 2-3 follow-up questions {entity_name} would ask to deepen understanding or explore implications.

Return as JSON list of question strings.
"""

        response = await self.llm.query(
            prompt,
            max_tokens=120,
            temperature=0.6
        )

        try:
            questions = json.loads(response.strip())
            return questions[:3]
        except json.JSONDecodeError:
            return []

    def _map_to_threads(
        self,
        description: str,
        facts: List[str],
        active_threads: List[Dict]
    ) -> List[str]:
        """
        Map import to active conversation threads
        """

        relevant_threads = []

        # Simple keyword matching
        import_keywords = set(
            description.lower().split() +
            " ".join(facts).lower().split()
        )

        for thread in active_threads:
            thread_keywords = set(
                kw.lower() for kw in thread.get("keywords", [])
            )
            thread_entities = set(
                e.lower() for e in thread.get("entities", [])
            )

            overlap = import_keywords & (thread_keywords | thread_entities)

            if len(overlap) >= 2:  # At least 2 keyword matches
                relevant_threads.append(thread["thread_id"])

        return relevant_threads

    async def _extract_entities(self, content: str) -> List[str]:
        """
        Extract new entities introduced in document
        """

        content_preview = content[:2000]

        prompt = f"""Extract named entities (people, places, organizations, concepts) from this text.

Content:
{content_preview}

Return as JSON list of entity names (max 10).
Only include entities that are clearly defined or important to the content.
"""

        response = await self.llm.query(
            prompt,
            max_tokens=150,
            temperature=0.2
        )

        try:
            entities = json.loads(response.strip())
            return entities[:10]
        except json.JSONDecodeError:
            return []

    async def _estimate_fact_count(self, content: str) -> int:
        """
        Estimate how many facts would have been extracted with raw extraction
        """
        # Rough heuristic: ~1 fact per 100 words
        word_count = len(content.split())
        return max(1, word_count // 100)

    def create_episodic_memory(
        self,
        synthesis: ImportSynthesis,
        current_turn: int
    ) -> Dict[str, Any]:
        """
        Convert synthesis to episodic memory format for storage

        Returns:
            Memory dict ready for ChromaDB insertion
        """

        return {
            "id": synthesis.import_id,
            "content": synthesis.personal_reaction,
            "metadata": {
                "type": "import_reaction",
                "layer": "episodic",
                "source": synthesis.source_description,
                "timestamp": synthesis.timestamp,
                "turn": current_turn,
                "emotional_tags": list(synthesis.emotional_response.keys()),
                "connections": synthesis.connections_made,
                "entities": synthesis.entities_introduced,
                "thread_relevance": synthesis.relevance_to_threads,
                "importance": 0.8,  # High importance for synthesis
                "age": 0
            }
        }

    def create_semantic_memories(
        self,
        synthesis: ImportSynthesis,
        current_turn: int
    ) -> List[Dict[str, Any]]:
        """
        Convert essential facts to semantic memory format

        Returns:
            List of memory dicts for ChromaDB insertion
        """

        memories = []

        for idx, fact in enumerate(synthesis.essential_facts):
            memory = {
                "id": f"{synthesis.import_id}_fact_{idx}",
                "content": fact,
                "metadata": {
                    "type": "fact",
                    "layer": "semantic",
                    "source": synthesis.source_description,
                    "timestamp": synthesis.timestamp,
                    "turn": current_turn,
                    "parent_import": synthesis.import_id,
                    "importance": 0.6,  # Moderate importance
                    "age": 0
                }
            }
            memories.append(memory)

        return memories
