"""
Semantic Fact Extractor

Extracts discrete factual statements from documents for storage in SemanticKnowledge.
Different from emotional narrative chunks - these are atomic facts Kay should "know".

Example:
- Input: "Gimpy is a one-legged pigeon who visits the park daily"
- Output: [
    {"text": "Gimpy is a one-legged pigeon", "entities": ["Gimpy", "pigeon"], "category": "animals"},
    {"text": "Gimpy visits the park daily", "entities": ["Gimpy", "park"], "category": "animals"}
  ]
"""

import asyncio
from typing import List, Dict, Any
from integrations.llm_integration import query_llm_json
import json


class SemanticFactExtractor:
    """
    Extracts semantic facts from text using LLM.
    These are discrete, atomic facts that Kay should know.
    """

    def __init__(self, model: str = "claude-3-5-haiku-20241022"):
        """
        Args:
            model: LLM model to use for extraction
        """
        self.model = model

    async def extract_facts(self, text: str, source: str) -> List[Dict[str, Any]]:
        """
        Extract semantic facts from a text chunk.

        Args:
            text: Document text or chunk
            source: Source identifier (filename, URL, etc.)

        Returns:
            List of fact dicts with keys: text, entities, category, confidence
        """
        # Build extraction prompt
        prompt = self._build_extraction_prompt(text, source)

        # Query LLM
        try:
            response = query_llm_json(
                prompt=prompt,
                temperature=0.3,  # Consistent extraction
                model=self.model,
                system_prompt=self._get_system_prompt()
            )

            # Parse response
            facts = self._parse_extraction_response(response)

            print(f"[SEMANTIC EXTRACT] Extracted {len(facts)} facts from {len(text)} chars")

            return facts

        except Exception as e:
            print(f"[SEMANTIC EXTRACT ERROR] Failed to extract facts: {e}")
            return []

    def _build_extraction_prompt(self, text: str, source: str) -> str:
        """Build prompt for fact extraction"""
        return f"""Extract discrete factual statements from this text.

Focus on:
- Facts about people, animals, places, objects
- Relationships between entities
- Attributes and properties
- Events and actions

DO NOT include:
- Narrative descriptions
- Emotional interpretations
- Vague statements
- Temporal events (those go in episodic memory)

For each fact, provide:
1. text: The fact as a concise statement (1 sentence max)
2. entities: List of entities mentioned (people, animals, places, objects, concepts)
3. category: Broad category (people/animals/objects/places/concepts/relationships)
4. confidence: How confident you are this is a factual statement (0.0-1.0)

Return as JSON array:
[
  {{"text": "Gimpy is a one-legged pigeon", "entities": ["Gimpy", "pigeon"], "category": "animals", "confidence": 0.95}},
  {{"text": "Chrome steals burritos from delivery drivers", "entities": ["Chrome", "burritos"], "category": "animals", "confidence": 0.9}}
]

SOURCE: {source}

TEXT:
{text}

IMPORTANT: Return ONLY the JSON array, no other text.
"""

    def _get_system_prompt(self) -> str:
        """System prompt for extraction"""
        return """You are a fact extraction specialist.

Your job is to extract discrete, atomic facts from text - these are things Kay should "know".

Guidelines:
- Extract specific facts about entities (people, animals, places, objects)
- Each fact should be self-contained and atomic
- Focus on permanent or semi-permanent attributes
- Avoid temporal events (those go in episodic memory)
- Be conservative - only extract clear, factual statements
- Do not infer or speculate

Categories:
- people: Facts about humans
- animals: Facts about animals
- objects: Facts about things
- places: Facts about locations
- concepts: Facts about abstract ideas
- relationships: Facts about connections between entities

Return valid JSON only.
"""

    def _parse_extraction_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into fact dictionaries"""
        try:
            # Extract JSON array from response
            # Handle potential markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()

            # Find JSON array in string
            if "[" in json_str:
                start = json_str.find("[")
                end = json_str.rfind("]") + 1
                json_str = json_str[start:end]

            facts = json.loads(json_str)

            # Validate and normalize
            normalized = []
            for fact in facts:
                # Require minimum fields
                if "text" not in fact or "entities" not in fact:
                    continue

                # Normalize
                normalized_fact = {
                    "text": fact["text"].strip(),
                    "entities": [e.strip() for e in fact.get("entities", []) if e.strip()],
                    "category": fact.get("category", "general").lower().strip(),
                    "confidence": float(fact.get("confidence", 0.8))
                }

                # Filter low confidence
                if normalized_fact["confidence"] < 0.5:
                    continue

                # Require at least one entity
                if not normalized_fact["entities"]:
                    continue

                normalized.append(normalized_fact)

            return normalized

        except json.JSONDecodeError as e:
            print(f"[SEMANTIC EXTRACT ERROR] Failed to parse JSON: {e}")
            print(f"[SEMANTIC EXTRACT ERROR] Response: {response[:200]}...")
            return []
        except Exception as e:
            print(f"[SEMANTIC EXTRACT ERROR] Unexpected error: {e}")
            return []

    async def extract_from_chunks(
        self,
        chunks: List[str],
        source: str,
        batch_size: int = 3,
        delay: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Extract facts from multiple chunks with batching and rate limiting.

        Args:
            chunks: List of text chunks
            source: Source identifier
            batch_size: Number of concurrent extractions
            delay: Delay between batches (seconds)

        Returns:
            Combined list of all extracted facts
        """
        all_facts = []

        # Process in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            print(f"[SEMANTIC EXTRACT] Processing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1} ({len(batch)} chunks)...")

            # Extract from each chunk concurrently
            tasks = [self.extract_facts(chunk, source) for chunk in batch]
            batch_results = await asyncio.gather(*tasks)

            # Combine results
            for facts in batch_results:
                all_facts.extend(facts)

            # Rate limiting
            if i + batch_size < len(chunks):
                await asyncio.sleep(delay)

        # Deduplicate facts (by text similarity)
        all_facts = self._deduplicate_facts(all_facts)

        return all_facts

    def _deduplicate_facts(self, facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate or very similar facts.
        Simple deduplication based on exact text match.
        More sophisticated would use embedding similarity.
        """
        seen_texts = set()
        unique_facts = []

        for fact in facts:
            # Normalize text for comparison
            normalized_text = fact["text"].lower().strip()

            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                unique_facts.append(fact)

        if len(facts) != len(unique_facts):
            print(f"[SEMANTIC EXTRACT] Deduplicated {len(facts)} -> {len(unique_facts)} facts")

        return unique_facts


# Test function
async def test_extractor():
    """Test the semantic fact extractor"""
    extractor = SemanticFactExtractor()

    test_text = """
    Gimpy is a one-legged pigeon who visits the park daily. He's missing his right leg
    but moves around just fine. Chrome is a cat who steals burritos from delivery drivers.
    Re is a researcher studying AI persistence and memory systems.
    """

    facts = await extractor.extract_facts(test_text, "test_document.txt")

    print("\n" + "=" * 80)
    print("EXTRACTED FACTS:")
    print("=" * 80)

    for i, fact in enumerate(facts, 1):
        print(f"\n{i}. {fact['text']}")
        print(f"   Entities: {fact['entities']}")
        print(f"   Category: {fact['category']}")
        print(f"   Confidence: {fact['confidence']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_extractor())
