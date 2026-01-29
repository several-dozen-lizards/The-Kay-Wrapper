"""
Hybrid RAG + Structured Memory Import Manager
Fixes memory bloat by storing documents in vector DB instead of extracting thousands of facts
"""

import asyncio
import json
import re
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from engines.vector_store import VectorStore
from .document_parser import DocumentParser

# Import LLM routing for KEY fact extraction only (not mass extraction)
try:
    from integrations.llm_integration import get_client_for_model
    import os
    MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
except ImportError:
    get_client_for_model = None
    MODEL = None


@dataclass
class HybridImportProgress:
    """Tracks progress of hybrid import operation."""
    total_files: int = 0
    processed_files: int = 0
    total_chunks_stored: int = 0
    key_facts_extracted: int = 0  # Only 5-10 per document
    summaries_created: int = 0  # 1 per document
    entities_created: int = 0  # Capped at 5 per document
    errors: List[str] = field(default_factory=list)
    current_file: str = ""
    status: str = "idle"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "total_chunks_stored": self.total_chunks_stored,
            "key_facts_extracted": self.key_facts_extracted,
            "summaries_created": self.summaries_created,
            "entities_created": self.entities_created,
            "errors": self.errors,
            "current_file": self.current_file,
            "status": self.status,
            "elapsed_time": self.get_elapsed_time()
        }

    def get_elapsed_time(self) -> float:
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


class HybridImportManager:
    """
    Hybrid import system that combines:
    - RAG (Vector DB): Stores full document content for semantic search
    - Structured Memory: Stores only 5-10 key facts + 1 summary per document

    CRITICAL DIFFERENCE FROM OLD SYSTEM:
    - OLD: Extract EVERY fact → 2000+ structured memories
    - NEW: Store in vector DB → Extract only 5-10 KEY facts
    """

    def __init__(
        self,
        memory_engine=None,
        entity_graph=None,
        vector_store: Optional[VectorStore] = None,
        chunk_size: int = 800,
        overlap: int = 100
    ):
        """
        Args:
            memory_engine: Kay's MemoryEngine instance
            entity_graph: Kay's EntityGraph instance
            vector_store: VectorStore instance (created if not provided)
            chunk_size: Document chunk size for RAG
            overlap: Chunk overlap for context
        """
        self.memory_engine = memory_engine
        self.entity_graph = entity_graph

        # Initialize vector store
        if vector_store is None:
            self.vector_store = VectorStore(persist_directory="memory/vector_db")
        else:
            self.vector_store = vector_store

        self.parser = DocumentParser(chunk_size=chunk_size, overlap=overlap)
        self.progress = HybridImportProgress()
        self.progress_callback: Optional[Callable] = None

        print("[HYBRID_IMPORT] Initialized with RAG + structured memory")

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates."""
        self.progress_callback = callback

    async def import_files(
        self,
        file_paths: List[str],
        dry_run: bool = False
    ) -> HybridImportProgress:
        """
        Import files using hybrid RAG + structured memory approach.

        FLOW:
        1. Store full document in vector DB (for RAG retrieval)
        2. Extract 5-10 KEY facts only (not thousands)
        3. Create 1 SHORT summary (max 200 chars)
        4. Cap entities at 5 per document

        Args:
            file_paths: List of file paths to import
            dry_run: If True, process but don't save

        Returns:
            HybridImportProgress with stats
        """
        self.progress = HybridImportProgress()
        self.progress.start_time = datetime.now()
        self.progress.status = "processing"

        try:
            for file_path in file_paths:
                self.progress.current_file = file_path
                self.progress.total_files += 1
                self._update_progress()

                # Process single file
                await self._process_file(file_path, dry_run)

                self.progress.processed_files += 1
                self._update_progress()

            self.progress.status = "complete"
            self.progress.end_time = datetime.now()
            self._update_progress()

            return self.progress

        except Exception as e:
            self.progress.status = "error"
            self.progress.errors.append(str(e))
            self.progress.end_time = datetime.now()
            self._update_progress()
            raise

    async def _process_file(self, file_path: str, dry_run: bool):
        """
        Process a single file with hybrid approach.

        Args:
            file_path: Path to file
            dry_run: If True, process but don't save
        """
        path_obj = Path(file_path)

        # Parse document
        if path_obj.is_dir():
            print(f"[HYBRID_IMPORT] Skipping directory: {file_path}")
            return

        # Get full text
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
        except Exception as e:
            self.progress.errors.append(f"Failed to read {file_path}: {e}")
            return

        if not full_text or len(full_text) < 50:
            print(f"[HYBRID_IMPORT] Skipping empty/tiny file: {file_path}")
            return

        # === STEP 1: STORE IN VECTOR DB (RAG) ===
        if not dry_run:
            result = self.vector_store.add_document(
                text=full_text,
                source_file=str(path_obj),
                chunk_size=800,
                overlap=100,
                metadata={
                    "document_type": path_obj.suffix,
                    "file_size": len(full_text)
                }
            )

            self.progress.total_chunks_stored += result.get("chunks_created", 0)
            print(f"[HYBRID_IMPORT] Stored {result['chunks_created']} chunks in vector DB")

        # === STEP 2: EXTRACT 5-10 KEY FACTS (NOT THOUSANDS) ===
        key_facts = await self._extract_key_facts(full_text, str(path_obj))

        # Filter to top 10 by importance
        key_facts = sorted(key_facts, key=lambda f: f.get("importance", 0), reverse=True)[:10]

        self.progress.key_facts_extracted += len(key_facts)
        print(f"[HYBRID_IMPORT] Extracted {len(key_facts)} KEY facts (not thousands)")

        # === STEP 3: CREATE SHORT SUMMARY (1 PARAGRAPH) ===
        summary = await self._create_summary(full_text, str(path_obj))

        if summary:
            self.progress.summaries_created += 1
            print(f"[HYBRID_IMPORT] Created summary: {summary[:80]}...")

        # === STEP 4: STORE KEY FACTS IN STRUCTURED MEMORY ===
        if not dry_run:
            await self._store_key_facts(key_facts, summary, str(path_obj))

    async def _extract_key_facts(
        self,
        text: str,
        source_file: str,
        max_facts: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Extract ONLY 5-10 KEY facts from document.

        NOT every fact - only the most important identity-relevant information.

        Args:
            text: Document text
            source_file: Source filename
            max_facts: Maximum facts to extract (default 10)

        Returns:
            List of key fact dicts
        """
        if not client or not MODEL:
            print("[HYBRID_IMPORT] LLM not available - skipping key fact extraction")
            return []

        # Truncate very long documents for extraction (sample from beginning/middle/end)
        if len(text) > 6000:
            sample = text[:2000] + "\n...\n" + text[len(text)//2-1000:len(text)//2+1000] + "\n...\n" + text[-2000:]
        else:
            sample = text

        prompt = f"""Extract the 5-10 MOST IMPORTANT facts from this document.

CRITICAL RULES:
1. Extract ONLY truly important facts (identity, relationships, major events)
2. MAXIMUM {max_facts} facts total
3. NO generic statements
4. NO abstract concepts as entities
5. Create entities ONLY for: named people, pets with names, specific places, named systems
6. NO entities for: emotions, desires, concepts, generic nouns

DOCUMENT:
\"\"\"
{sample[:4000]}
\"\"\"

OUTPUT FORMAT (JSON):
{{
  "key_facts": [
    {{
      "text": "Chrome is Re's gray tabby cat",
      "importance": 0.9,
      "entities": ["Re", "Chrome"],
      "topic": "pets",
      "perspective": "user"
    }}
  ]
}}

Extract {max_facts} key facts ONLY. Return valid JSON."""

        try:
            # Get correct client for model
            if not get_client_for_model or not MODEL:
                return []
            
            active_client, provider_type = get_client_for_model(MODEL)
            
            # Provider-specific API calls
            if provider_type == 'openai':
                resp = await asyncio.to_thread(
                    active_client.chat.completions.create,
                    model=MODEL,
                    max_tokens=1500,
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": "You are a key fact extractor. Extract ONLY the most important facts. Maximum 10 facts. Output valid JSON only."},
                        {"role": "user", "content": prompt}
                    ]
                )
                response_text = resp.choices[0].message.content.strip()
            else:
                resp = await asyncio.to_thread(
                    active_client.messages.create,
                    model=MODEL,
                    max_tokens=1500,
                    temperature=0.3,
                    system="You are a key fact extractor. Extract ONLY the most important facts. Maximum 10 facts. Output valid JSON only.",
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = resp.content[0].text.strip()

            # Clean JSON
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)

            data = json.loads(response_text)
            facts = data.get("key_facts", [])

            # Filter entities (only concrete things)
            for fact in facts:
                fact["entities"] = self._filter_concrete_entities(fact.get("entities", []))

            return facts

        except Exception as e:
            print(f"[HYBRID_IMPORT] Key fact extraction failed: {e}")
            return []

    async def _create_summary(
        self,
        text: str,
        source_file: str,
        max_length: int = 200
    ) -> str:
        """
        Create SHORT summary of document (1 paragraph, max 200 chars).

        NOT full text - just a brief overview.

        Args:
            text: Document text
            source_file: Source filename
            max_length: Max summary length

        Returns:
            Summary string
        """
        if not client or not MODEL:
            return f"Document imported from {Path(source_file).name}"

        # Sample document
        if len(text) > 3000:
            sample = text[:1500] + "\n...\n" + text[-1500:]
        else:
            sample = text

        prompt = f"""Create a 1-sentence summary of this document (max {max_length} chars).

DOCUMENT:
\"\"\"
{sample[:3000]}
\"\"\"

Summary (1 sentence, max {max_length} chars):"""

        try:
            # Get correct client for model
            if not get_client_for_model or not MODEL:
                return f"Document imported from {Path(source_file).name}"
            
            active_client, provider_type = get_client_for_model(MODEL)
            
            # Provider-specific API calls
            if provider_type == 'openai':
                resp = await asyncio.to_thread(
                    active_client.chat.completions.create,
                    model=MODEL,
                    max_tokens=100,
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": "You are a document summarizer. Create brief 1-sentence summaries."},
                        {"role": "user", "content": prompt}
                    ]
                )
                summary = resp.choices[0].message.content.strip()
            else:
                resp = await asyncio.to_thread(
                    active_client.messages.create,
                    model=MODEL,
                    max_tokens=100,
                    temperature=0.3,
                    system="You are a document summarizer. Create brief 1-sentence summaries.",
                    messages=[{"role": "user", "content": prompt}]
                )
                summary = resp.content[0].text.strip()

            # Truncate if too long
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."

            return summary

        except Exception as e:
            print(f"[HYBRID_IMPORT] Summary creation failed: {e}")
            return f"Document imported from {Path(source_file).name}"

    def _filter_concrete_entities(self, entities: List[str]) -> List[str]:
        """
        Filter entities to ONLY concrete things.

        YES: Chrome, Re, Kay, Archive_Zero, Seattle
        NO: desire, contradiction, rumor, glitch, fossil

        Args:
            entities: List of entity names

        Returns:
            Filtered list (concrete entities only)
        """
        # Abstract concepts to EXCLUDE
        abstract_concepts = {
            "desire", "contradiction", "rumor", "glitch", "fossil",
            "emotion", "feeling", "thought", "idea", "concept",
            "fear", "hope", "worry", "dream", "aspiration",
            "goal", "plan", "intention", "wish", "preference",
            "memory", "experience", "event", "moment", "situation",
            "problem", "issue", "challenge", "conflict", "tension"
        }

        filtered = []

        for entity in entities:
            entity_lower = entity.lower().strip()

            # Skip if abstract concept
            if entity_lower in abstract_concepts:
                continue

            # Skip if starts with lowercase (likely not a proper noun)
            if entity and entity[0].islower():
                continue

            # Skip if very short (likely acronym or noise)
            if len(entity) < 2:
                continue

            # Keep if it looks like a proper noun
            filtered.append(entity)

        # Cap at 5 entities per fact
        return filtered[:5]

    async def _store_key_facts(
        self,
        key_facts: List[Dict[str, Any]],
        summary: str,
        source_file: str
    ):
        """
        Store key facts in structured memory.

        Args:
            key_facts: List of key fact dicts
            summary: Document summary
            source_file: Source filename
        """
        if not self.memory_engine:
            print("[HYBRID_IMPORT] No memory engine - skipping storage")
            return

        # Store summary as a single memory
        if summary:
            summary_memory = {
                "type": "extracted_fact",
                "fact": f"Document imported: {summary}",
                "source_file": source_file,
                "perspective": "shared",
                "topic": "imported_document",
                "importance_score": 0.5,
                "entities": [],
                "is_imported": True,
                "is_summary": True,
                "protected": True,  # NEW: Mark as protected from filtering
                "age": 0,  # NEW: Track age in turns
                "turn_index": self.memory_engine.current_turn
            }

            self.memory_engine.memories.append(summary_memory)
            self.memory_engine.memory_layers.add_memory(summary_memory, layer="episodic")

        # Store key facts
        entity_count = 0

        for fact in key_facts:
            fact_memory = {
                "type": "extracted_fact",
                "fact": fact.get("text", ""),
                "source_file": source_file,
                "perspective": fact.get("perspective", "shared"),
                "topic": fact.get("topic", "general"),
                "importance_score": fact.get("importance", 0.5),
                "entities": fact.get("entities", []),
                "is_imported": True,
                "protected": True,  # NEW: Mark as protected from filtering
                "age": 0,  # NEW: Track age in turns
                "turn_index": self.memory_engine.current_turn
            }

            self.memory_engine.memories.append(fact_memory)

            # Add to appropriate tier based on importance
            importance = fact.get("importance", 0.5)
            if importance >= 0.8:
                tier = "semantic"
            elif importance >= 0.4:
                tier = "episodic"
            else:
                tier = "working"

            self.memory_engine.memory_layers.add_memory(fact_memory, layer=tier)

            # Create entities (capped at 5 total per document)
            for entity_name in fact.get("entities", []):
                if entity_count >= 5:
                    break

                entity = self.entity_graph.get_or_create_entity(
                    entity_name,
                    turn=self.memory_engine.current_turn
                )

                if entity.first_mentioned == self.memory_engine.current_turn:
                    self.progress.entities_created += 1
                    entity_count += 1

        # Save to disk
        self.memory_engine._save_to_disk()
        self.memory_engine.memory_layers._save_to_disk()
        self.entity_graph._save_to_disk()

        print(f"[HYBRID_IMPORT] Stored {len(key_facts)} key facts + 1 summary in structured memory")

    def _update_progress(self):
        """Notify callback of progress update."""
        if self.progress_callback:
            self.progress_callback(self.progress)


# Testing
if __name__ == "__main__":
    print("[HYBRID_IMPORT] Test mode")

    # Would need actual memory_engine, entity_graph, and vector_store to test
    manager = HybridImportManager()

    print(f"[HYBRID_IMPORT] Vector store stats: {manager.vector_store.get_stats()}")
    print("[HYBRID_IMPORT] Initialized successfully")
