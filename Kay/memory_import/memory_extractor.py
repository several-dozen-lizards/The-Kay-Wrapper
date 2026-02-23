"""
LLM Memory Extractor for Kay Zero
Uses Anthropic API to extract structured facts from document chunks
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# Import existing LLM integration
try:
    from integrations.llm_integration import client, MODEL
except ImportError:
    client = None
    MODEL = None
    print("[WARNING] LLM client not available - run from Kay Zero root directory")


@dataclass
class ExtractedMemory:
    """Represents a single extracted memory/fact."""
    text: str
    importance: float  # 0.0-1.0
    category: str  # e.g., "kay/identity", "user/pets", "shared/events"
    entities: List[str]
    date: Optional[str]  # ISO format YYYY-MM-DD
    tier: str  # "working", "episodic", or "semantic"
    perspective: str  # "user", "kay", or "shared"
    topic: str  # For categorization
    emotion_tags: List[str] = None
    glyph_summary: str = ""
    emotional_tone: str = ""
    source_document: str = ""
    chunk_index: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


class MemoryExtractor:
    """
    Extracts structured memories from document chunks using LLM.
    """

    def __init__(self, existing_entities: Optional[List[str]] = None):
        """
        Args:
            existing_entities: List of entities already in the graph (for context)
        """
        self.existing_entities = existing_entities or []

        if not client or not MODEL:
            print("[ERROR] Anthropic client not initialized")

    async def extract_memories(
        self,
        text: str,
        metadata: Dict,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Extract memories from a document chunk.

        Args:
            text: Document chunk text
            metadata: Document metadata (filename, date, etc.)
            dry_run: If True, return extraction without saving

        Returns:
            Dict with: {
                "facts": List[ExtractedMemory],
                "relationships": List[Dict],
                "glyph_summary": str,
                "emotional_tone": str
            }
        """
        if not client:
            return {"error": "LLM client not available"}

        prompt = self._build_extraction_prompt(text, metadata)

        try:
            # Call LLM
            response = await asyncio.to_thread(
                client.messages.create,
                model=MODEL,
                max_tokens=4000,  # Increased for longer extractions
                temperature=0.3,  # Lower temperature for consistent extraction
                system=self._build_system_prompt(),
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Parse JSON response
            extracted_data = self._parse_llm_response(response_text, metadata)

            return extracted_data

        except Exception as e:
            # Use repr() to avoid Unicode encoding errors on Windows console
            try:
                print(f"[EXTRACTION ERROR] {e}")
            except UnicodeEncodeError:
                print(f"[EXTRACTION ERROR] {repr(str(e))}")
            return {"error": str(e)}

    def _build_system_prompt(self) -> str:
        """Build system prompt for memory extraction."""
        return """You are a memory extraction system for Kay Zero, an emotionally-aware AI.

Your task: Extract discrete facts, entities, and relationships from documents for persistent memory storage.

EXTRACTION RULES:
1. Extract factual statements only (not opinions or questions unless they reveal preferences)
2. Assign importance scores (0.0-1.0):
   - 0.9-1.0: Critical identity facts (names, relationships, core events)
   - 0.7-0.8: Significant events, preferences, important entities
   - 0.5-0.6: Notable details, secondary relationships
   - 0.3-0.4: Context, minor details
   - 0.0-0.2: Trivial mentions

3. Categorize by perspective:
   - "user" = facts about Re (the person typing to Kay)
   - "kay" = facts about Kay (the AI)
   - "shared" = events involving both or general knowledge

4. Assign memory tier (MUST match importance):
   - "semantic" = ONLY for importance >= 0.8 (timeless facts: names, permanent relationships, core identity)
   - "episodic" = For importance 0.4-0.7 (time-bound events, conversations, experiences)
   - "working" = For importance < 0.4 (recent/temporary context)
   - BE SELECTIVE: Most facts should be episodic, only truly permanent facts are semantic

5. Extract entities (CONCRETE ONLY):
   - YES: Named people, pets (with names), specific places, named objects/systems
   - NO: Abstract concepts (desires, contradictions, feelings, rumors, glitches, fossils, etc.)
   - NO: Generic nouns without specific identity (e.g., "a cat" unless it has a name)
   - ONLY extract if it's a specific, identifiable, concrete thing
6. Detect relationships: "owns", "lives_in", "works_with", etc.
7. Infer emotional tone if present

Output ONLY valid JSON with this structure:
{
  "facts": [
    {
      "text": "Chrome is Re's cat",
      "importance": 0.8,
      "category": "user/pets",
      "entities": ["Re", "Chrome"],
      "date": "2024-10-15",
      "tier": "semantic",
      "perspective": "user",
      "topic": "pets",
      "emotion_tags": [],
      "glyph_summary": "",
      "emotional_tone": "neutral"
    }
  ],
  "relationships": [
    {"entity1": "Re", "relation": "owns", "entity2": "Chrome"}
  ],
  "glyph_summary": "",
  "emotional_tone": "affectionate"
}

IMPORTANT: Output ONLY the JSON, no preamble or explanation."""

    def _build_extraction_prompt(self, text: str, metadata: Dict) -> str:
        """Build extraction prompt for a specific document chunk."""
        # Build entity context
        entity_context = ""
        if self.existing_entities:
            entity_list = ", ".join(self.existing_entities[:20])  # Show first 20
            entity_context = f"\n\nKNOWN ENTITIES (already in memory): {entity_list}"

        # Build metadata context
        meta_context = f"""
DOCUMENT METADATA:
- Filename: {metadata.get('filename', 'unknown')}
- File type: {metadata.get('file_type', 'unknown')}
- Extracted date: {metadata.get('extracted_date', 'unknown')}
- Modified: {metadata.get('modified_date', 'unknown')}
"""

        # Chunk info
        chunk_info = ""
        if metadata.get('chunk_index') is not None:
            chunk_info = f"- Chunk: {metadata['chunk_index'] + 1} of {metadata.get('total_chunks', 1)}\n"

        prompt = f"""{meta_context}{chunk_info}{entity_context}

DOCUMENT TEXT:
\"\"\"
{text[:4000]}
\"\"\"

Extract all factual memories from this document. Return ONLY valid JSON."""

        return prompt

    def _parse_llm_response(self, response_text: str, metadata: Dict) -> Dict[str, Any]:
        """
        Parse LLM response into structured format.

        Args:
            response_text: Raw LLM response
            metadata: Document metadata to attach to memories

        Returns:
            Dict with extracted memories and relationships
        """
        try:
            # Try to extract JSON from response
            # Sometimes LLM wraps JSON in markdown code blocks
            json_match = response_text
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_match = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_match = response_text[start:end].strip()

            data = json.loads(json_match)

            # Convert facts to ExtractedMemory objects
            memories = []
            for fact in data.get("facts", []):
                memory = ExtractedMemory(
                    text=fact.get("text", ""),
                    importance=float(fact.get("importance", 0.5)),
                    category=fact.get("category", "shared/general"),
                    entities=fact.get("entities", []),
                    date=fact.get("date"),
                    tier=fact.get("tier", "episodic"),
                    perspective=fact.get("perspective", "shared"),
                    topic=fact.get("topic", "general"),
                    emotion_tags=fact.get("emotion_tags", []),
                    glyph_summary=fact.get("glyph_summary", ""),
                    emotional_tone=fact.get("emotional_tone", ""),
                    source_document=metadata.get("filename", ""),
                    chunk_index=metadata.get("chunk_index", 0)
                )
                memories.append(memory)

            return {
                "facts": memories,
                "relationships": data.get("relationships", []),
                "glyph_summary": data.get("glyph_summary", ""),
                "emotional_tone": data.get("emotional_tone", "")
            }

        except json.JSONDecodeError as e:
            print(f"[JSON PARSE ERROR] {e}")
            print(f"Response text: {response_text[:500]}")
            return {
                "facts": [],
                "relationships": [],
                "error": f"Failed to parse JSON: {e}"
            }
        except Exception as e:
            print(f"[PARSE ERROR] {e}")
            return {
                "facts": [],
                "relationships": [],
                "error": str(e)
            }

    async def extract_batch(
        self,
        chunks: List[Dict],
        batch_size: int = 5,
        delay: float = 1.0
    ) -> List[Dict]:
        """
        Extract memories from multiple chunks with batching and rate limiting.

        Args:
            chunks: List of document chunks (each with 'text' and 'metadata')
            batch_size: Number of concurrent LLM calls
            delay: Delay between batches (seconds)

        Returns:
            List of extraction results
        """
        results = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            # Process batch concurrently
            tasks = [
                self.extract_memories(chunk['text'], chunk['metadata'])
                for chunk in batch
            ]

            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

            print(f"[EXTRACTOR] Processed batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")

            # Rate limiting delay
            if i + batch_size < len(chunks):
                await asyncio.sleep(delay)

        return results


# Testing
if __name__ == "__main__":
    extractor = MemoryExtractor(existing_entities=["Re", "Kay", "Chrome"])

    test_text = """
    Re told Kay about her cat Chrome who likes to door-dash. Chrome is a gray tabby
    who enjoys causing trouble. Re also mentioned that she likes coffee in the morning.
    """

    test_metadata = {
        "filename": "test.txt",
        "file_type": ".txt",
        "extracted_date": "2024-10-27",
        "chunk_index": 0,
        "total_chunks": 1
    }

    async def test():
        result = await extractor.extract_memories(test_text, test_metadata)
        print(json.dumps(result, indent=2, default=str))

    if client:
        asyncio.run(test())
    else:
        print("[TEST SKIPPED] LLM client not available")
