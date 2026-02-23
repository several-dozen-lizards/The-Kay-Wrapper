"""
Semantic Knowledge Store for Reed

Stores factual knowledge separately from episodic memory.
These are FACTS Kay knows, not EVENTS that happened.

Examples:
- "Gimpy is a pigeon with one leg" (semantic fact)
- "Re uploaded pigeon document yesterday" (episodic event)

The first goes here, the second goes in memory_layers.
"""

import json
import os
import time
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


class SemanticKnowledge:
    """
    Storage and retrieval for factual knowledge.
    Separate from episodic memory - these are FACTS Kay knows, not EVENTS that happened.
    """

    def __init__(self, storage_path: str = "memory/semantic_knowledge.json", document_store=None):
        """
        Initialize semantic knowledge store.

        Args:
            storage_path: Path to JSON file for persistence
            document_store: DocumentStore instance for fact verification (optional)
        """
        self.storage_path = storage_path
        self.facts = {}  # fact_id → {text, entities, source, timestamp, category, access_count}
        self.entity_index = defaultdict(set)  # entity_name → {fact_ids}
        self.category_index = defaultdict(set)  # category → {fact_ids}
        self.next_id = 0
        self.document_store = document_store  # For verification against documents
        self.load()

    def add_fact(
        self,
        text: str,
        entities: List[str],
        source: str,
        category: str = "general",
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Add a semantic fact to the knowledge base.

        IMPORTANT: Document-sourced facts are REJECTED - they stay in RAG only.
        Only conversational and inferred facts are stored here.

        Args:
            text: The fact text (e.g., "Gimpy is a pigeon with one leg")
            entities: List of entities this fact relates to (e.g., ["Gimpy", "pigeon"])
            source: Fact source type or filename
                - 'conversation': From user-Kay discussion (stored with high confidence)
                - 'inference': Kay inferred/generated (stored with low confidence)
                - 'phase4_migration': From identity memory migration (stored as conversation)
                - File names (e.g., 'pigeon_names.txt'): REJECTED - document content stays in RAG
            category: Broad category (e.g., "animals", "people", "concepts")
            metadata: Optional additional data (e.g., confidence score, context)

        Returns:
            fact_id if stored, None if rejected
        """
        # Classify source type
        source_type = self._classify_source(source)

        # REJECT document-sourced facts (they stay in RAG only)
        if source_type == "document":
            print(f"[SEMANTIC] REJECTED document fact (stays in RAG): {text[:60]}... (source: {source})")
            return None

        # VERIFY fact against document content (prevent contradictions and duplicates)
        is_verified, verification_type = self.verify_fact_against_documents(text, entities)

        # REJECT facts that contradict documents
        if is_verified == False and verification_type == 'contradicts_document':
            print(f"[SEMANTIC VERIFY] REJECTED contradictory fact: {text[:60]}...")
            print(f"[SEMANTIC VERIFY] Entities {entities} mentioned in documents but fact contradicts content")
            return None

        # DON'T STORE facts that match documents (they're already in RAG)
        if is_verified == True and verification_type == 'matches_document':
            print(f"[SEMANTIC VERIFY] Skipped duplicate fact (already in RAG): {text[:60]}...")
            return None

        # Determine confidence and verification based on source type and document verification
        if source_type == "conversation":
            # If unverified against documents, lower confidence
            if verification_type == 'unverified':
                confidence = 0.3  # Unverified conversational facts get low confidence
                verified = False
                print(f"[SEMANTIC VERIFY] Warning: Conversational fact not found in documents (conf=0.3)")
            else:
                confidence = 0.9
                verified = True
        elif source_type == "inference":
            confidence = 0.5
            verified = False
        else:
            # Unknown sources default to low confidence
            confidence = 0.3
            verified = False

        # Generate unique ID
        fact_id = f"fact_{self.next_id}"
        self.next_id += 1

        # Normalize entities (lowercase for matching)
        normalized_entities = [e.lower().strip() for e in entities if e.strip()]

        # Store fact with source tracking and confidence
        self.facts[fact_id] = {
            "text": text,
            "entities": normalized_entities,
            "source": source,
            "source_type": source_type,  # NEW: conversation, inference, or document
            "confidence": confidence,     # NEW: 0.9 for conversation, 0.5 for inference
            "verified": verified,         # NEW: True if from conversation, False if inferred
            "category": category.lower(),
            "timestamp": time.time(),
            "access_count": 0,
            "metadata": metadata or {}
        }

        # Update entity index
        for entity in normalized_entities:
            self.entity_index[entity].add(fact_id)

        # Update category index
        self.category_index[category.lower()].add(fact_id)

        print(f"[SEMANTIC] Added fact (type={source_type}, conf={confidence:.1f}): {text[:60]}... (entities: {normalized_entities})")

        return fact_id

    def _classify_source(self, source: str) -> str:
        """
        Classify the source type of a fact.

        Args:
            source: Source string (e.g., 'conversation', 'pigeon_names.txt', 'phase4_migration')

        Returns:
            Source type: 'conversation', 'inference', or 'document'
        """
        source_lower = source.lower()

        # Explicit source types
        if source_lower == "conversation":
            return "conversation"
        elif source_lower == "inference":
            return "inference"
        elif source_lower in ["phase4_migration", "identity_memory", "migration"]:
            # Migration from identity memory = conversational facts
            return "conversation"

        # File extensions indicate document sources
        if any(source_lower.endswith(ext) for ext in ['.txt', '.md', '.pdf', '.doc', '.docx', '.json', '.csv']):
            return "document"

        # If source looks like a filename (contains dots or slashes)
        if '.' in source or '/' in source or '\\' in source:
            return "document"

        # Default to conversation for safety
        return "conversation"

    def verify_fact_against_documents(self, fact_text: str, entities: List[str]) -> Tuple[Optional[bool], str]:
        """
        Verify a fact against document content to detect contradictions.

        Args:
            fact_text: The fact to verify
            entities: Entities mentioned in the fact

        Returns:
            Tuple of (is_verified, verification_type):
            - (True, 'matches_document'): Fact matches document content (don't store - it's in RAG)
            - (False, 'contradicts_document'): Fact contradicts document (REJECT)
            - (None, 'unverified'): Entity not found in documents (store with low confidence)
        """
        # If no document store available, can't verify
        if not self.document_store:
            return (None, 'unverified')

        # Search documents for each entity
        document_mentions = []
        for entity in entities:
            matches = self.document_store.search_documents(entity)
            if matches:
                document_mentions.extend(matches)

        # No documents mention these entities
        if not document_mentions:
            return (None, 'unverified')

        # Check if fact text appears verbatim or very similar in documents
        fact_lower = fact_text.lower()
        fact_words = set(fact_lower.split())

        for doc_match in document_mentions:
            doc_text = doc_match.get('preview', '').lower()

            # Exact match or very close - fact is already in document
            if fact_lower in doc_text:
                return (True, 'matches_document')

            # Check for significant word overlap (>70% of fact words in document)
            doc_words = set(doc_text.split())
            overlap = len(fact_words & doc_words) / len(fact_words) if fact_words else 0

            if overlap > 0.7:
                return (True, 'matches_document')

        # Check for contradictions (entity mentioned but fact doesn't match)
        # Only check specific entities, not generic ones like "pigeon", "person", etc.
        generic_entities = {'pigeon', 'pigeons', 'bird', 'birds', 'person', 'people', 'animal', 'animals'}
        specific_entities = [e for e in entities if e.lower() not in generic_entities]

        # If no specific entities, can't verify (too generic)
        if not specific_entities:
            return (None, 'unverified')

        for doc_match in document_mentions:
            doc_text = doc_match.get('preview', '').lower()

            # Check if any SPECIFIC entity is in the document
            # (e.g., "Gimpy", not just "pigeon")
            for entity in specific_entities:
                entity_lower = entity.lower()
                if entity_lower in doc_text:
                    # Recalculate overlap for this specific document
                    doc_words = set(doc_text.split())
                    fact_overlap = len(fact_words & doc_words) / len(fact_words) if fact_words else 0

                    # Specific entity is in document but fact text has very little overlap
                    # This suggests a potential contradiction
                    if fact_overlap < 0.3:  # Less than 30% overlap = likely contradiction
                        return (False, 'contradicts_document')

        # Entity in documents but can't determine match/contradiction
        return (None, 'unverified')

    def query(
        self,
        query_text: str,
        entities: Optional[List[str]] = None,
        category: Optional[str] = None,
        top_k: int = 20
    ) -> List[Dict]:
        """
        Retrieve facts relevant to query using hybrid pre-filter + LLM selection.

        This replaces the old fragile scoring system with:
        1. Fast keyword pre-filter (reduces 100s of facts to ~50 candidates)
        2. LLM selection (Haiku picks the most relevant facts)

        Args:
            query_text: User's question/statement
            entities: Explicitly mentioned entities (used for pre-filter boost)
            category: Filter by category (optional)
            top_k: Number of facts to return

        Returns:
            List of relevant fact dicts
        """
        import re

        if len(self.facts) == 0:
            print("[SEMANTIC QUERY] No facts in knowledge base")
            return []

        print(f"[SEMANTIC QUERY] Query: '{query_text[:80]}...'")

        # STEP 1: Fast keyword pre-filter
        query_lower = query_text.lower()
        query_words = set(re.findall(r'\b\w{3,}\b', query_lower))  # Words 3+ chars

        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'about', 'into', 'through', 'over',
            'this', 'that', 'these', 'those', 'me', 'you', 'your', 'their', 'them'
        }
        query_keywords = query_words - stop_words

        # Expand query keywords to include singular/plural variants
        expanded_keywords = set(query_keywords)
        for word in query_keywords:
            if word.endswith('s') and len(word) > 3:
                expanded_keywords.add(word[:-1])  # Add singular (pigeons -> pigeon)
            else:
                expanded_keywords.add(word + 's')  # Add plural (pigeon -> pigeons)

        query_keywords = expanded_keywords

        # Score facts by keyword overlap
        candidates = []
        for fact_id, fact in self.facts.items():
            # Skip if category filter doesn't match
            if category and fact["category"] != category.lower():
                continue

            fact_lower = fact['text'].lower()
            fact_words = set(re.findall(r'\b\w{3,}\b', fact_lower))

            # Calculate keyword overlap
            overlap = len(query_keywords & fact_words)

            # Boost if entities match (lightweight check)
            if entities:
                for entity in entities:
                    if entity.lower() in fact_lower:
                        overlap += 2  # Small boost for entity presence

            if overlap > 0:
                candidates.append({
                    'fact_id': fact_id,
                    'fact': fact,
                    'overlap_score': overlap
                })

        # Sort by overlap, take top 50 candidates
        candidates.sort(key=lambda x: x['overlap_score'], reverse=True)
        top_candidates = candidates[:50]

        print(f"[SEMANTIC PRE-FILTER] Filtered {len(self.facts)} facts -> {len(top_candidates)} candidates")

        if len(top_candidates) == 0:
            print("[SEMANTIC QUERY] No matching candidates found")
            return []

        # STEP 2: LLM selection from candidates
        selected_facts = self._llm_select_facts(query_text, top_candidates, top_k)

        print(f"[SEMANTIC LLM] Selected {len(selected_facts)} facts")

        # Increment access count for selected facts
        for fact in selected_facts:
            fact_id = fact.get('fact_id')
            if fact_id and fact_id in self.facts:
                self.facts[fact_id]["access_count"] = self.facts[fact_id].get("access_count", 0) + 1

        return selected_facts

    def _llm_select_facts(self, query_text: str, candidates: List[Dict], top_k: int) -> List[Dict]:
        """
        Use LLM to select most relevant facts from candidates.

        Args:
            query_text: User's query
            candidates: List of pre-filtered candidate dicts with 'fact' and 'fact_id' keys
            top_k: Maximum facts to return

        Returns:
            List of selected fact dicts
        """
        import anthropic
        import re
        import os

        # Format candidates for LLM
        facts_text = ""
        for i, candidate in enumerate(candidates):
            fact = candidate['fact']
            facts_text += f"{i+1}. {fact['text']}\n"

        # Build prompt
        prompt = f"""You are helping select relevant facts to answer a question.

Question: "{query_text}"

Available facts:
{facts_text}

Which facts are relevant to answering this question?

Instructions:
- Return ONLY the numbers of relevant facts (e.g., "1,5,12,18")
- Select facts that directly answer or relate to the question
- Prioritize facts containing specific names/details over general statements
- Return up to {top_k} facts
- If asking for names, prioritize facts that contain actual names
- Return numbers only, comma-separated, no other text

Relevant fact numbers:"""

        try:
            # Get API key from environment
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                print("[SEMANTIC LLM] No API key found, falling back to keyword ranking")
                return [c['fact'] for c in candidates[:top_k]]

            # Call Anthropic API with Haiku (fast + cheap)
            client = anthropic.Anthropic(api_key=api_key)

            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=200,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = response.content[0].text.strip()
            print(f"[SEMANTIC LLM] Raw response: {response_text}")

            # Parse numbers from response
            # Handle formats like "1,5,12" or "1, 5, 12" or even "1 5 12"
            numbers_str = re.sub(r'[^\d,]', '', response_text)  # Keep only digits and commas
            if numbers_str:
                selected_indices = [int(n.strip())-1 for n in numbers_str.split(',') if n.strip()]
            else:
                selected_indices = []

            # Validate indices and return selected facts
            selected_facts = []
            for idx in selected_indices:
                if 0 <= idx < len(candidates):
                    fact = candidates[idx]['fact'].copy()
                    fact['fact_id'] = candidates[idx]['fact_id']
                    selected_facts.append(fact)

            # If no valid selections, fall back to top candidates by keyword overlap
            if len(selected_facts) == 0:
                print("[SEMANTIC LLM] No valid selections, falling back to top keyword matches")
                selected_facts = []
                for c in candidates[:top_k]:
                    fact = c['fact'].copy()
                    fact['fact_id'] = c['fact_id']
                    selected_facts.append(fact)

            return selected_facts[:top_k]

        except Exception as e:
            print(f"[SEMANTIC LLM] Error during selection: {e}")
            # Fallback: return top candidates by keyword overlap
            fallback_facts = []
            for c in candidates[:top_k]:
                fact = c['fact'].copy()
                fact['fact_id'] = c['fact_id']
                fallback_facts.append(fact)
            return fallback_facts

    def get_facts_by_entity(self, entity_name: str) -> List[Dict]:
        """
        Get all facts related to a specific entity.

        Args:
            entity_name: Entity to search for

        Returns:
            List of facts containing this entity
        """
        entity_name = entity_name.lower().strip()
        fact_ids = self.entity_index.get(entity_name, set())

        facts = []
        for fact_id in fact_ids:
            if fact_id in self.facts:
                fact = self.facts[fact_id].copy()
                fact["fact_id"] = fact_id
                facts.append(fact)

        # Sort by access count (most accessed first)
        facts.sort(key=lambda f: f.get("access_count", 0), reverse=True)

        return facts

    def get_all_entity_names(self) -> set:
        """
        Get all unique entity names in the knowledge base.
        Used for entity extraction to match against known entities.

        Returns:
            Set of entity name strings (lowercase)
        """
        all_entities = set()

        # Collect from entity index
        all_entities.update(self.entity_index.keys())

        # Also collect from facts themselves (in case index is incomplete)
        for fact in self.facts.values():
            if 'entities' in fact and isinstance(fact['entities'], list):
                all_entities.update([e.lower() for e in fact['entities'] if e])

        return all_entities

    def get_facts_by_category(self, category: str) -> List[Dict]:
        """
        Get all facts in a category.

        Args:
            category: Category to filter by

        Returns:
            List of facts in this category
        """
        category = category.lower().strip()
        fact_ids = self.category_index.get(category, set())

        facts = []
        for fact_id in fact_ids:
            if fact_id in self.facts:
                fact = self.facts[fact_id].copy()
                fact["fact_id"] = fact_id
                facts.append(fact)

        # Sort by timestamp (newest first)
        facts.sort(key=lambda f: f.get("timestamp", 0), reverse=True)

        return facts

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base.

        Returns:
            Dict with stats (total facts, entities, categories, etc.)
        """
        return {
            "total_facts": len(self.facts),
            "total_entities": len(self.entity_index),
            "total_categories": len(self.category_index),
            "categories": {
                cat: len(fact_ids)
                for cat, fact_ids in self.category_index.items()
            },
            "most_accessed_facts": self._get_most_accessed(5),
            "newest_facts": self._get_newest(5)
        }

    def _get_most_accessed(self, n: int) -> List[Dict]:
        """Get top N most accessed facts"""
        sorted_facts = sorted(
            self.facts.items(),
            key=lambda x: x[1].get("access_count", 0),
            reverse=True
        )

        return [
            {"fact_id": fid, "text": f["text"], "access_count": f.get("access_count", 0)}
            for fid, f in sorted_facts[:n]
        ]

    def _get_newest(self, n: int) -> List[Dict]:
        """Get N newest facts"""
        sorted_facts = sorted(
            self.facts.items(),
            key=lambda x: x[1].get("timestamp", 0),
            reverse=True
        )

        return [
            {"fact_id": fid, "text": f["text"], "timestamp": f.get("timestamp", 0)}
            for fid, f in sorted_facts[:n]
        ]

    def delete_fact(self, fact_id: str) -> bool:
        """
        Delete a fact from the knowledge base.

        Args:
            fact_id: ID of fact to delete

        Returns:
            True if deleted, False if not found
        """
        if fact_id not in self.facts:
            return False

        fact = self.facts[fact_id]

        # Remove from entity index
        for entity in fact["entities"]:
            if entity in self.entity_index:
                self.entity_index[entity].discard(fact_id)
                if not self.entity_index[entity]:
                    del self.entity_index[entity]

        # Remove from category index
        category = fact["category"]
        if category in self.category_index:
            self.category_index[category].discard(fact_id)
            if not self.category_index[category]:
                del self.category_index[category]

        # Delete fact
        del self.facts[fact_id]

        print(f"[SEMANTIC] Deleted fact: {fact_id}")

        return True

    def save(self):
        """Persist knowledge base to disk"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

        # Convert sets to lists for JSON serialization
        data = {
            "facts": self.facts,
            "entity_index": {k: list(v) for k, v in self.entity_index.items()},
            "category_index": {k: list(v) for k, v in self.category_index.items()},
            "next_id": self.next_id
        }

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[SEMANTIC] Saved {len(self.facts)} facts to {self.storage_path}")

    def load(self):
        """Load knowledge base from disk"""
        if not os.path.exists(self.storage_path):
            print(f"[SEMANTIC] No existing knowledge base at {self.storage_path}, starting fresh")
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.facts = data.get("facts", {})

            # Convert lists back to sets
            self.entity_index = defaultdict(
                set,
                {k: set(v) for k, v in data.get("entity_index", {}).items()}
            )
            self.category_index = defaultdict(
                set,
                {k: set(v) for k, v in data.get("category_index", {}).items()}
            )

            self.next_id = data.get("next_id", len(self.facts))

            print(f"[SEMANTIC] Loaded {len(self.facts)} facts from {self.storage_path}")

        except Exception as e:
            print(f"[SEMANTIC ERROR] Failed to load knowledge base: {e}")
            print("[SEMANTIC] Starting with empty knowledge base")
            self.facts = {}
            self.entity_index = defaultdict(set)
            self.category_index = defaultdict(set)
            self.next_id = 0


# Singleton instance for global access
_semantic_knowledge_instance = None


def get_semantic_knowledge(storage_path: str = "memory/semantic_knowledge.json", document_store=None) -> SemanticKnowledge:
    """
    Get the global semantic knowledge instance.

    Args:
        storage_path: Path to knowledge base file
        document_store: DocumentStore instance for fact verification (optional)

    Returns:
        SemanticKnowledge instance
    """
    global _semantic_knowledge_instance

    if _semantic_knowledge_instance is None:
        _semantic_knowledge_instance = SemanticKnowledge(storage_path, document_store)

    return _semantic_knowledge_instance


def reset_semantic_knowledge():
    """Reset the global instance (mainly for testing)"""
    global _semantic_knowledge_instance
    _semantic_knowledge_instance = None
