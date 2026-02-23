"""
Import Manager for Reed
Coordinates document parsing, memory extraction, and integration
"""

import asyncio
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .document_parser import DocumentParser, DocumentChunk
from .memory_extractor import MemoryExtractor, ExtractedMemory
from .emotional_importer import EmotionalMemoryImporter
from .semantic_extractor import SemanticFactExtractor

# DEPRECATED: semantic_knowledge was moved to deprecated/engines/
# Import is optional - semantic extraction still works but doesn't save to knowledge base
try:
    from engines.semantic_knowledge import get_semantic_knowledge
    SEMANTIC_KNOWLEDGE_AVAILABLE = True
except ImportError:
    SEMANTIC_KNOWLEDGE_AVAILABLE = False
    get_semantic_knowledge = None
    print("[IMPORT MANAGER] semantic_knowledge not available (deprecated) - semantic extraction disabled")


@dataclass
class ImportProgress:
    """Tracks progress of import operation."""
    total_files: int = 0
    processed_files: int = 0
    total_chunks: int = 0
    processed_chunks: int = 0
    facts_extracted: int = 0
    semantic_facts_extracted: int = 0  # NEW: Semantic facts for knowledge base
    entities_created: int = 0
    entities_updated: int = 0
    memories_imported: int = 0
    tier_distribution: Dict[str, int] = field(default_factory=lambda: {
        "working": 0,
        "episodic": 0,
        "semantic": 0
    })
    errors: List[str] = field(default_factory=list)
    current_file: str = ""
    status: str = "idle"  # idle, parsing, extracting, integrating, complete, error
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "total_chunks": self.total_chunks,
            "processed_chunks": self.processed_chunks,
            "facts_extracted": self.facts_extracted,
            "semantic_facts_extracted": self.semantic_facts_extracted,
            "entities_created": self.entities_created,
            "entities_updated": self.entities_updated,
            "memories_imported": self.memories_imported,
            "tier_distribution": self.tier_distribution,
            "errors": self.errors,
            "current_file": self.current_file,
            "status": self.status,
            "elapsed_time": self.get_elapsed_time()
        }

    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


class ImportManager:
    """
    Manages the complete import pipeline:
    1. Parse documents
    2. Extract memories via LLM
    3. Integrate into memory system
    """

    def __init__(
        self,
        memory_engine=None,
        entity_graph=None,
        chunk_size: int = 3000,
        overlap: int = 500,
        batch_size: int = 5,
        use_emotional_integration: bool = True,  # NEW: Enable emotionally-integrated memory by default
        debug_mode: bool = False  # NEW: Skip expensive operations for testing (7x cheaper)
    ):
        """
        Args:
            memory_engine: Reed's MemoryEngine instance
            entity_graph: Reed's EntityGraph instance
            chunk_size: Document chunk size
            overlap: Chunk overlap for context
            batch_size: LLM batch size for rate limiting
            use_emotional_integration: Use emotionally-integrated memory system (default True)
            debug_mode: Skip semantic extraction for faster, cheaper testing (default False)
        """
        self.memory_engine = memory_engine
        self.entity_graph = entity_graph
        self.use_emotional_integration = use_emotional_integration
        self.debug_mode = debug_mode  # NEW: Debug mode flag

        self.parser = DocumentParser(chunk_size=chunk_size, overlap=overlap)
        self.extractor = None  # Will initialize with existing entities
        self.emotional_importer = None  # NEW: Emotional memory importer
        self.semantic_extractor = SemanticFactExtractor()  # NEW: Semantic fact extractor

        # DEPRECATED: semantic_knowledge moved to deprecated/engines/
        # Only initialize if available
        if SEMANTIC_KNOWLEDGE_AVAILABLE and get_semantic_knowledge:
            self.semantic_knowledge = get_semantic_knowledge()
        else:
            self.semantic_knowledge = None

        # Initialize emotional importer if enabled
        if use_emotional_integration:
            self.emotional_importer = EmotionalMemoryImporter()
            print("[IMPORT MANAGER] Emotionally-integrated memory system ENABLED")
        else:
            print("[IMPORT MANAGER] Using legacy fact extraction system")

        if debug_mode:
            print("[IMPORT MANAGER] ⚡ DEBUG MODE - Semantic extraction DISABLED (7x cost reduction)")
        else:
            print("[IMPORT MANAGER] Semantic knowledge extraction ENABLED")

        self.batch_size = batch_size
        self.progress = ImportProgress()
        self.progress_callback: Optional[Callable] = None  # UI callback for progress updates

    def set_progress_callback(self, callback: Callable):
        """
        Set callback function for progress updates.

        Callback signature: callback(progress: ImportProgress)
        """
        self.progress_callback = callback

    async def import_files(
        self,
        file_paths: List[str],
        dry_run: bool = False,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> ImportProgress:
        """
        Import memories from file paths.

        Args:
            file_paths: List of file or directory paths
            dry_run: If True, extract but don't save to memory
            start_date: Optional filter (ISO format YYYY-MM-DD)
            end_date: Optional filter (ISO format YYYY-MM-DD)

        Returns:
            ImportProgress object with results
        """
        self.progress = ImportProgress()
        self.progress.start_time = datetime.now()
        self.progress.status = "parsing"

        try:
            # Step 1: Parse all documents
            all_chunks = []
            for path in file_paths:
                path_obj = Path(path)

                if path_obj.is_dir():
                    chunks = self.parser.parse_directory(str(path))
                else:
                    chunks = self.parser.parse_file(str(path))

                all_chunks.extend(chunks)
                self.progress.total_files += 1
                self.progress.processed_files += 1
                self._update_progress()

            self.progress.total_chunks = len(all_chunks)

            # Filter by date if specified
            if start_date or end_date:
                all_chunks = self._filter_by_date(all_chunks, start_date, end_date)

            # Step 2: Extract/Import memories
            if self.use_emotional_integration:
                # NEW PATH: Emotionally-integrated memory import
                await self._import_emotional_memories(file_paths, dry_run)
            else:
                # OLD PATH: Legacy fact extraction
                self.progress.status = "extracting"
                self._update_progress()

                # Initialize extractor with existing entities
                existing_entities = []
                if self.entity_graph:
                    existing_entities = list(self.entity_graph.entities.keys())

                self.extractor = MemoryExtractor(existing_entities=existing_entities)

                # Prepare chunks for extraction
                chunk_data = [
                    {"text": chunk.text, "metadata": chunk.metadata}
                    for chunk in all_chunks
                ]

                # Extract in batches
                extraction_results = await self.extractor.extract_batch(
                    chunk_data,
                    batch_size=self.batch_size,
                    delay=1.0
                )

                # Process extraction results
                all_extracted_facts = []
                for result in extraction_results:
                    if "error" in result:
                        self.progress.errors.append(result["error"])
                    else:
                        all_extracted_facts.extend(result.get("facts", []))

                    self.progress.processed_chunks += 1
                    self._update_progress()

                self.progress.facts_extracted = len(all_extracted_facts)

                # Step 3: Integrate into memory system
                if not dry_run:
                    self.progress.status = "integrating"
                    self._update_progress()

                    await self._integrate_memories(all_extracted_facts)

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

    async def _import_emotional_memories(self, file_paths: List[str], dry_run: bool):
        """
        Import using emotionally-integrated memory system.

        This is the NEW PATH that replaces legacy fact extraction.
        Creates narrative chunks with emotional signatures instead of atomized facts.

        Args:
            file_paths: List of files to import
            dry_run: If True, don't save to memory system
        """
        if not self.emotional_importer:
            raise ValueError("EmotionalMemoryImporter not initialized")

        self.progress.status = "emotional_import"
        self._update_progress()

        print(f"[EMOTIONAL IMPORT] Processing {len(file_paths)} file(s) with emotional integration...")

        for file_path in file_paths:
            try:
                self.progress.current_file = str(file_path)
                print(f"[EMOTIONAL IMPORT] Importing: {file_path}")

                # Import document with emotional integration
                # Returns: (doc_id, list of EmotionalMemoryChunk objects)
                doc_id, emotional_chunks = self.emotional_importer.import_document(str(file_path))

                print(f"[EMOTIONAL IMPORT] Created {len(emotional_chunks)} narrative chunks (doc_id: {doc_id})")
                self.progress.processed_chunks += len(emotional_chunks)

                # === SEMANTIC FACT EXTRACTION (DEPRECATED) ===
                # Extract discrete facts for semantic knowledge base (parallel to emotional chunks)
                # SKIP if semantic_knowledge not available (deprecated) or DEBUG MODE
                if not self.debug_mode and self.semantic_knowledge:
                    print(f"[SEMANTIC EXTRACT] Extracting facts from {file_path}...")
                    try:
                        # Read file and parse into chunks for extraction
                        file_chunks = self.parser.parse_file(str(file_path))
                        chunk_texts = [chunk.text for chunk in file_chunks]

                        # Extract semantic facts
                        semantic_facts = await self.semantic_extractor.extract_from_chunks(
                            chunks=chunk_texts,
                            source=Path(file_path).name,
                            batch_size=3,
                            delay=1.0
                        )

                        # Store semantic facts (if not dry run)
                        if not dry_run and semantic_facts:
                            print(f"[SEMANTIC EXTRACT] Storing {len(semantic_facts)} facts in knowledge base...")
                            for fact in semantic_facts:
                                self.semantic_knowledge.add_fact(
                                    text=fact["text"],
                                    entities=fact["entities"],
                                    source=Path(file_path).name,
                                    category=fact.get("category", "general"),
                                    metadata={"confidence": fact.get("confidence", 0.8)}
                                )
                                self.progress.semantic_facts_extracted += 1

                            print(f"[SEMANTIC EXTRACT] Stored {len(semantic_facts)} facts")
                        else:
                            print(f"[SEMANTIC EXTRACT] Dry run - extracted {len(semantic_facts)} facts (not stored)")

                    except Exception as e:
                        error_msg = f"Semantic extraction failed for {file_path}: {str(e)}"
                        self.progress.errors.append(error_msg)
                        print(f"[SEMANTIC EXTRACT ERROR] {error_msg}")
                elif self.debug_mode:
                    print(f"[DEBUG MODE] Skipping semantic extraction (7x cost reduction)")
                else:
                    # semantic_knowledge not available (deprecated)
                    pass
                # === END SEMANTIC EXTRACTION ===

                # Store in memory engine if not dry run
                if not dry_run and self.memory_engine:
                    print(f"[EMOTIONAL IMPORT] Storing chunks in memory layers...")

                    for chunk in emotional_chunks:
                        try:
                            # Convert to memory dict format
                            memory_dict = {
                                # Core content
                                "fact": chunk.chunk.text,
                                "user_input": chunk.chunk.text,
                                "response": "",

                                # Classification
                                "type": "emotional_narrative",
                                "perspective": "kay",  # Imported background about Kay

                                # Emotional signature
                                "emotional_signature": {
                                    "primary": chunk.emotional_signature.primary_emotion,
                                    "glyph": chunk.emotional_signature.glyph_code,
                                    "intensity": chunk.emotional_signature.intensity,
                                    "valence": chunk.emotional_signature.valence
                                },

                                # Identity classification
                                "identity_type": chunk.identity_classification.identity_type.value,
                                "identity_confidence": chunk.identity_classification.confidence,

                                # Composite weight
                                "importance": chunk.memory_weight.total_weight,
                                "importance_score": chunk.memory_weight.total_weight,
                                "weight_components": {
                                    "identity": chunk.memory_weight.identity_component,
                                    "emotional": chunk.memory_weight.emotional_component,
                                    "entity": chunk.memory_weight.entity_component,
                                    "narrative": chunk.memory_weight.narrative_component
                                },

                                # Tier assignment
                                "tier": chunk._calculate_tier(),
                                "current_layer": chunk._calculate_tier(),
                                "current_strength": 1.0,

                                # Turn tracking
                                "turn_index": self.memory_engine.current_turn if self.memory_engine else 0,
                                "turn_number": self.memory_engine.current_turn if self.memory_engine else 0,

                                # Timestamps
                                "added_timestamp": datetime.now().isoformat(),
                                "date": datetime.now().strftime("%Y-%m-%d"),

                                # Access tracking
                                "access_count": 0,
                                "last_accessed": None,

                                # Import provenance - FIXED: Use doc_id/chunk_index/source_file for clustering
                                "doc_id": doc_id,
                                "chunk_index": chunk.chunk_index,
                                "source_file": chunk.source_file,
                                "is_imported": True,
                                "is_emotional_narrative": True
                            }

                            # Determine storage layer based on tier
                            tier = chunk._calculate_tier()
                            if tier == "CORE_IDENTITY":
                                layer = "semantic"
                                self.progress.tier_distribution["semantic"] += 1
                            elif tier == "EMOTIONAL_ACTIVE":
                                layer = "episodic"
                                self.progress.tier_distribution["episodic"] += 1
                            elif tier == "RELATIONAL_SEMANTIC":
                                layer = "episodic"
                                self.progress.tier_distribution["episodic"] += 1
                            else:  # PERIPHERAL_ARCHIVE
                                layer = "working"
                                self.progress.tier_distribution["working"] += 1

                            # Add to memory layers
                            self.memory_engine.memory_layers.add_memory(memory_dict, layer=layer)

                            # CRITICAL: Also add to main memories array
                            self.memory_engine.memories.append(memory_dict)

                            self.progress.memories_imported += 1

                        except Exception as e:
                            error_msg = f"Failed to store chunk from {file_path}: {str(e)}"
                            self.progress.errors.append(error_msg)
                            print(f"[EMOTIONAL IMPORT ERROR] {error_msg}")
                            continue

                    print(f"[EMOTIONAL IMPORT] Stored {len(emotional_chunks)} chunks")
                    print(f"[EMOTIONAL IMPORT] Distribution: CORE={self.progress.tier_distribution['semantic']}, " +
                          f"EMOTIONAL/RELATIONAL={self.progress.tier_distribution['episodic']}, " +
                          f"PERIPHERAL={self.progress.tier_distribution['working']}")

                self._update_progress()

            except Exception as e:
                error_msg = f"Error importing {file_path}: {str(e)}"
                self.progress.errors.append(error_msg)
                print(f"[EMOTIONAL IMPORT ERROR] {error_msg}")
                continue

        # Save to disk if not dry run
        if not dry_run and self.memory_engine:
            print(f"[EMOTIONAL IMPORT] Saving to disk...")
            self.memory_engine._save_to_disk()
            self.memory_engine.memory_layers._save_to_disk()
            if self.entity_graph:
                self.entity_graph._save_to_disk()

            # Save semantic knowledge base (if available and facts were extracted)
            if self.semantic_knowledge and self.progress.semantic_facts_extracted > 0:
                print(f"[SEMANTIC EXTRACT] Saving {self.progress.semantic_facts_extracted} facts to knowledge base...")
                self.semantic_knowledge.save()
                print(f"[SEMANTIC EXTRACT] Knowledge base saved")

            print(f"[EMOTIONAL IMPORT] Complete! Imported {self.progress.memories_imported} narrative chunks")

            # Refresh document index to include newly imported documents
            if hasattr(self.memory_engine, 'document_index') and self.memory_engine.document_index:
                self.memory_engine.document_index.refresh()

    async def _integrate_memories(self, facts: List[ExtractedMemory]):
        """
        Integrate extracted memories into Reed's memory system.

        CRITICAL FIX: Memories must be added to BOTH:
        1. memory_layers (tier management)
        2. self.memories[] (retrieval searches this array)

        Args:
            facts: List of ExtractedMemory objects
        """
        if not self.memory_engine:
            raise ValueError("No memory_engine provided")

        # Deduplicate facts
        unique_facts = self._deduplicate_facts(facts)

        for fact in unique_facts:
            try:
                # Convert to memory format
                memory = self._convert_to_memory_format(fact)

                # CRITICAL FIX: Add to BOTH memory_layers AND self.memories[]
                # This ensures imported memories are retrievable!

                # 1. Add to memory_layers (tier management)
                # FIX: Enforce tier based on importance (prevent over-promotion)
                tier = fact.tier.lower()
                importance = fact.importance

                # Override tier if it doesn't match importance thresholds
                if importance >= 0.8:
                    tier = "semantic"  # Only truly important facts
                elif importance >= 0.4:
                    tier = "episodic"  # Most facts
                else:
                    tier = "working"  # Temporary context

                if tier == "semantic":
                    self.memory_engine.memory_layers.add_memory(memory, layer="semantic")
                    self.progress.tier_distribution["semantic"] += 1
                elif tier == "working":
                    self.memory_engine.memory_layers.add_memory(memory, layer="working")
                    self.progress.tier_distribution["working"] += 1
                else:  # Default to episodic
                    self.memory_engine.memory_layers.add_memory(memory, layer="episodic")
                    self.progress.tier_distribution["episodic"] += 1

                # 2. CRITICAL: Also add to main memories array (retrieval searches here!)
                self.memory_engine.memories.append(memory)

                # Update entity graph with entities and relationships
                for entity_name in fact.entities:
                    entity = self.entity_graph.get_or_create_entity(
                        entity_name,
                        turn=self.memory_engine.current_turn
                    )

                    # Track if entity was newly created
                    if entity.first_mentioned == self.memory_engine.current_turn:
                        self.progress.entities_created += 1
                    else:
                        self.progress.entities_updated += 1

                    # Process entity attributes if present
                    if hasattr(fact, 'attributes') and fact.attributes:
                        for attr in fact.attributes:
                            if isinstance(attr, dict):
                                entity_name_attr = attr.get('entity', '')
                                attribute_name = attr.get('attribute', '')
                                value = attr.get('value', '')

                                if entity_name_attr and attribute_name:
                                    # Update entity with attribute
                                    target_entity = self.entity_graph.get_or_create_entity(
                                        entity_name_attr,
                                        turn=self.memory_engine.current_turn
                                    )
                                    target_entity.set_attribute(
                                        attribute_name,
                                        value,
                                        turn=self.memory_engine.current_turn,
                                        source="import"
                                    )

                self.progress.memories_imported += 1
                self._update_progress()

            except Exception as e:
                self.progress.errors.append(f"Failed to import fact '{fact.text[:50]}...': {e}")
                continue

        # CRITICAL: Save memories to disk after importing
        print(f"[IMPORT] Saving {len(unique_facts)} imported memories to disk...")
        self.memory_engine._save_to_disk()
        self.memory_engine.memory_layers._save_to_disk()
        self.entity_graph._save_to_disk()
        print(f"[IMPORT] Save complete!")

    def _deduplicate_facts(self, facts: List[ExtractedMemory]) -> List[ExtractedMemory]:
        """
        Remove duplicate facts based on text similarity.

        ENHANCED: Checks against BOTH:
        1. Other facts in this import batch
        2. Existing memories already in database

        This prevents re-importing the same content multiple times.

        Args:
            facts: List of ExtractedMemory objects

        Returns:
            Deduplicated list
        """
        if not facts:
            return []

        # Get existing memories for comparison
        existing_facts = set()
        if self.memory_engine and hasattr(self.memory_engine, 'memories'):
            for mem in self.memory_engine.memories:
                # Normalize existing fact text
                fact_text = mem.get("fact", "") or mem.get("user_input", "")
                if fact_text:
                    normalized = self._normalize_text(fact_text)
                    existing_facts.add(normalized)

        print(f"[DEDUP] Checking {len(facts)} new facts against {len(existing_facts)} existing memories")

        # Deduplicate
        seen_texts = set()
        unique_facts = []
        duplicates_in_batch = 0
        duplicates_in_database = 0

        for fact in facts:
            # Normalize text for comparison
            normalized = self._normalize_text(fact.text)

            # Check if duplicate of existing memory
            if normalized in existing_facts:
                duplicates_in_database += 1
                continue

            # Check if duplicate within this batch
            if normalized in seen_texts:
                duplicates_in_batch += 1
                continue

            # It's unique!
            seen_texts.add(normalized)
            unique_facts.append(fact)

        total_removed = duplicates_in_batch + duplicates_in_database

        if total_removed > 0:
            print(f"[DEDUP] Removed {total_removed} duplicates:")
            print(f"  - {duplicates_in_batch} duplicates within import batch")
            print(f"  - {duplicates_in_database} already in database")
            print(f"  - {len(unique_facts)} unique facts will be imported")

        return unique_facts

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for duplicate detection.

        Removes:
        - Extra whitespace
        - Punctuation variations
        - Case differences

        Args:
            text: Raw text

        Returns:
            Normalized text for comparison
        """
        # Convert to lowercase
        normalized = text.lower().strip()

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        # Remove trailing punctuation
        normalized = normalized.rstrip('.,!?;:')

        # Remove common filler words that don't change meaning
        # (e.g., "Chrome is a dog" vs "Chrome is dog" should match)
        filler_words = [" a ", " an ", " the "]
        for filler in filler_words:
            normalized = normalized.replace(filler, " ")

        # Normalize spacing again after filler removal
        normalized = " ".join(normalized.split())

        return normalized

    def _convert_to_memory_format(self, fact: ExtractedMemory) -> Dict:
        """
        Convert ExtractedMemory to Reed's memory format.

        CRITICAL: Must match format of live conversation memories for retrieval compatibility.

        Args:
            fact: ExtractedMemory object

        Returns:
            Memory dict compatible with memory_engine
        """
        return {
            # Core content
            "fact": fact.text,
            "user_input": fact.text,  # Some retrieval code checks this field
            "response": "",  # Imported facts have no Kay response

            # Classification
            "type": "extracted_fact",  # Mark as extracted fact (vs full_turn)
            "perspective": fact.perspective,
            "topic": fact.topic,

            # Entities and relationships
            "entities": fact.entities,
            "emotion_tags": fact.emotion_tags or [],

            # Scoring
            "importance": fact.importance,  # Used by retrieval scoring
            "importance_score": fact.importance,  # Alternate field name

            # Tier metadata
            "tier": fact.tier,  # "working", "episodic", "semantic"
            "current_layer": fact.tier,
            "current_strength": 1.0,

            # Turn tracking
            "turn_index": self.memory_engine.current_turn if self.memory_engine else 0,
            "turn_number": self.memory_engine.current_turn if self.memory_engine else 0,

            # Timestamps
            "added_timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),

            # Access tracking
            "access_count": 0,
            "last_accessed": None,

            # Import provenance - FIXED: Use doc_id for clustering compatibility
            "doc_id": fact.source_document,
            "chunk_index": fact.chunk_index,
            "source_file": getattr(fact, 'source_file', 'unknown'),  # Some facts may not have source_file
            "is_imported": True,  # Flag to distinguish from live conversation
        }

    def _filter_by_date(
        self,
        chunks: List[DocumentChunk],
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> List[DocumentChunk]:
        """
        Filter chunks by date range.

        Args:
            chunks: List of DocumentChunk objects
            start_date: ISO format YYYY-MM-DD
            end_date: ISO format YYYY-MM-DD

        Returns:
            Filtered list of chunks
        """
        filtered = []

        for chunk in chunks:
            chunk_date = chunk.metadata.get("extracted_date")

            if not chunk_date:
                # If no date, include it
                filtered.append(chunk)
                continue

            # Check date range
            if start_date and chunk_date < start_date:
                continue
            if end_date and chunk_date > end_date:
                continue

            filtered.append(chunk)

        return filtered

    def _update_progress(self):
        """Notify callback of progress update."""
        if self.progress_callback:
            self.progress_callback(self.progress)


# Testing
if __name__ == "__main__":
    manager = ImportManager()

    # Test progress tracking
    def progress_callback(progress: ImportProgress):
        print(f"[PROGRESS] Status: {progress.status}, Files: {progress.processed_files}/{progress.total_files}")

    manager.set_progress_callback(progress_callback)

    # Would need actual memory_engine and entity_graph to test fully
    print("ImportManager initialized successfully")
