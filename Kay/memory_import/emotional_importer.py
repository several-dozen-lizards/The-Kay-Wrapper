"""
Emotional Memory Importer - Main Coordinator
Transforms document import from "fact extraction" to "experiential memory integration"
Integrates: narrative parsing → emotional analysis → identity classification → weighted storage
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# Import our components
try:
    from memory_import.document_parser import DocumentParser
    from memory_import.narrative_chunks import NarrativeChunkParser, NarrativeChunk
    from memory_import.emotional_signature import EmotionalSignatureAnalyzer, EmotionalSignature
    from memory_import.identity_classifier import IdentityClassifier, IdentityClassification, IdentityType
    from memory_import.memory_weights import MemoryWeightCalculator, MemoryWeight
    from memory_import.document_store import DocumentStore
except ImportError:
    # Fallback for testing
    from document_parser import DocumentParser
    from narrative_chunks import NarrativeChunkParser, NarrativeChunk
    from emotional_signature import EmotionalSignatureAnalyzer, EmotionalSignature
    from identity_classifier import IdentityClassifier, IdentityClassification, IdentityType
    from memory_weights import MemoryWeightCalculator, MemoryWeight
    from document_store import DocumentStore


class EmotionalMemoryChunk:
    """
    A fully-analyzed memory chunk ready for storage.
    Contains: narrative + emotional signature + identity classification + weight + glyph.
    """

    def __init__(
        self,
        chunk: NarrativeChunk,
        emotional_signature: EmotionalSignature,
        identity_classification: IdentityClassification,
        memory_weight: MemoryWeight,
        source_file: str,
        chunk_index: int,
        import_timestamp: str,
        doc_id: str = None
    ):
        self.chunk = chunk
        self.emotional_signature = emotional_signature
        self.identity_classification = identity_classification
        self.memory_weight = memory_weight
        self.source_file = source_file
        self.chunk_index = chunk_index
        self.import_timestamp = import_timestamp
        self.doc_id = doc_id  # Document ID for tree tracking

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            # Core content
            "text": self.chunk.text,
            "fact": self.chunk.text,  # CRITICAL: memory_engine expects "fact" field for retrieval
            "chunk_type": self.chunk.chunk_type,
            "chunk_index": self.chunk_index,
            "doc_id": self.doc_id,  # Document ID for tree tracking
            "source_file": self.source_file,
            "import_timestamp": self.import_timestamp,

            # Emotional signature
            "emotional_signature": self.emotional_signature.to_dict(),
            "primary_emotion": self.emotional_signature.primary_emotion,
            "emotion_tags": [self.emotional_signature.primary_emotion] + self.emotional_signature.secondary_emotions,
            "emotional_intensity": self.emotional_signature.intensity,
            "valence": self.emotional_signature.valence,
            "glyph_code": self.emotional_signature.glyph_code,

            # Identity classification
            "identity_type": self.identity_classification.identity_type.value,
            "identity_confidence": self.identity_classification.confidence,

            # Weight and tier
            "importance_score": self.memory_weight.total_weight,
            "assigned_tier": self._calculate_tier(),
            "weight_breakdown": self.memory_weight.breakdown,

            # Entities
            "entities": self.chunk.entities_mentioned,

            # Metadata
            "perspective": "shared",  # Treat as shared knowledge (not user-specific or kay-specific)
            "is_imported": True,
            "contains_dialogue": self.chunk.contains_dialogue,
            "sentence_count": self.chunk.sentence_count,

            # Trigger conditions
            "trigger_conditions": self.emotional_signature.trigger_conditions,
        }

    def _calculate_tier(self) -> str:
        """Calculate tier assignment based on weight."""
        weight = self.memory_weight.total_weight

        if weight >= 0.8:
            return "CORE_IDENTITY"
        elif weight >= 0.6:
            return "EMOTIONAL_ACTIVE"
        elif weight >= 0.4:
            return "RELATIONAL_SEMANTIC"
        else:
            return "PERIPHERAL_ARCHIVE"

    def get_compressed_glyph(self) -> Dict[str, Any]:
        """
        Generate compressed glyph representation for active memory.
        ~20 chars instead of 300+ for full text.
        """
        return {
            "glyph": self.emotional_signature.glyph_code,
            "entities": self.chunk.entities_mentioned[:3],  # Top 3 only
            "chunk_id": f"{self.source_file}_{self.chunk_index}",
            "identity_flag": self.identity_classification.identity_type == IdentityType.CORE_IDENTITY,
            "weight": self.memory_weight.total_weight,
            "emotion": self.emotional_signature.primary_emotion,
        }


class EmotionalMemoryImporter:
    """
    Main coordinator for emotionally-integrated memory import.

    Pipeline:
    1. Parse document into narrative chunks (story beats, not atomic facts)
    2. Analyze emotional signature (map to ULTRAMAP)
    3. Classify identity centrality (core → peripheral)
    4. Calculate composite weight (importance scoring)
    5. Assign to memory tier (core/emotional/relational/peripheral)
    6. Generate compressed glyph for active memory
    """

    def __init__(
        self,
        ultramap_path: str = "data/Emotion_Mapping_Kay_ULTRAMAP_PROTOCOLS_TRIGGERLOGIC.csv"
    ):
        """
        Initialize importer with all analysis components.

        Args:
            ultramap_path: Path to ULTRAMAP CSV
        """
        # Initialize components
        self.document_parser = DocumentParser(chunk_size=3000, overlap=500)
        self.narrative_parser = NarrativeChunkParser(min_chunk_sentences=2, max_chunk_sentences=7)
        self.emotion_analyzer = EmotionalSignatureAnalyzer(ultramap_path)
        self.identity_classifier = IdentityClassifier()
        self.weight_calculator = MemoryWeightCalculator()
        self.document_store = DocumentStore()  # Document storage for full source retrieval

        print("[EMOTIONAL IMPORTER] Initialized all components")

    def import_document(self, file_path: str) -> tuple[str, List[EmotionalMemoryChunk]]:
        """
        Import a document as emotionally-integrated memory chunks.

        Args:
            file_path: Path to document file

        Returns:
            Tuple of (document_id, list of EmotionalMemoryChunk objects)
        """
        print(f"[EMOTIONAL IMPORTER] Importing document: {file_path}")

        # Phase 1: Parse document into raw chunks
        # NOTE: DocumentParser handles all file types (.txt, .docx, .pdf, etc.)
        # and converts them to text properly
        doc_chunks = self.document_parser.parse_file(file_path)
        print(f"[EMOTIONAL IMPORTER] Phase 1: Parsed into {len(doc_chunks)} document chunks")

        # Combine chunks into full text (for narrative re-parsing AND storage)
        full_text = "\n\n".join(chunk.text for chunk in doc_chunks)

        # Phase 0: Store original document for retrieval
        # FIXED: Use parsed text instead of raw file reading (handles .docx, .pdf, etc.)
        doc_id = self.document_store.store_document(
            full_text,
            os.path.basename(file_path)
        )
        print(f"[EMOTIONAL IMPORTER] Phase 0: Stored original document (ID: {doc_id})")

        # Phase 2: Re-parse into narrative chunks (story beats)
        narrative_chunks = self.narrative_parser.parse(full_text)

        # DEBUG: Show why we might have 0 chunks
        if len(narrative_chunks) == 0:
            print(f"[EMOTIONAL IMPORTER WARNING] 0 narrative chunks created!")
            print(f"[EMOTIONAL IMPORTER DEBUG] Full text length: {len(full_text)} chars")
            print(f"[EMOTIONAL IMPORTER DEBUG] Full text preview: {full_text[:500]}")
            print(f"[EMOTIONAL IMPORTER DEBUG] Check: Does text have paragraph breaks (\\n\\n)?")
            print(f"[EMOTIONAL IMPORTER DEBUG] Check: Is text mostly single lines without breaks?")
            # If text is one long paragraph, narrative parser may fail to chunk it
            # Try fallback: split by sentences
            if len(full_text) > 100:
                print(f"[EMOTIONAL IMPORTER FALLBACK] Attempting sentence-based chunking...")
                from narrative_chunks import NarrativeChunk
                # Simple fallback: split into sentence groups
                sentences = [s.strip() for s in full_text.split('.') if s.strip()]
                if len(sentences) > 0:
                    # Group sentences into chunks of 3-5
                    chunk_size = 5
                    for i in range(0, len(sentences), chunk_size):
                        chunk_text = '. '.join(sentences[i:i+chunk_size]) + '.'
                        if chunk_text.strip():
                            chunk = NarrativeChunk(
                                text=chunk_text,
                                chunk_type="narrative",
                                entities_mentioned=[],
                                contains_dialogue=False,
                                sentence_count=min(chunk_size, len(sentences) - i)
                            )
                            narrative_chunks.append(chunk)
                    print(f"[EMOTIONAL IMPORTER FALLBACK] Created {len(narrative_chunks)} sentence-based chunks")
        print(f"[EMOTIONAL IMPORTER] Phase 2: Re-parsed into {len(narrative_chunks)} narrative chunks")

        # Phase 3: Analyze each narrative chunk
        emotional_chunks = []
        import_timestamp = datetime.now().isoformat()

        for i, chunk in enumerate(narrative_chunks):
            print(f"[EMOTIONAL IMPORTER] Processing chunk {i+1}/{len(narrative_chunks)}...")

            # Phase 3a: Emotional analysis
            emotional_sig = self.emotion_analyzer.analyze(chunk.text)

            # Phase 3b: Identity classification
            identity_class = self.identity_classifier.classify(chunk.text, chunk.entities_mentioned)

            # Phase 3c: Weight calculation
            memory_weight = self.weight_calculator.calculate(
                chunk,
                identity_class,
                emotional_sig
            )

            # Phase 3d: Create EmotionalMemoryChunk
            emotional_chunk = EmotionalMemoryChunk(
                chunk=chunk,
                emotional_signature=emotional_sig,
                identity_classification=identity_class,
                memory_weight=memory_weight,
                source_file=os.path.basename(file_path),
                chunk_index=i,
                import_timestamp=import_timestamp,
                doc_id=doc_id  # Add doc_id for tree tracking
            )

            emotional_chunks.append(emotional_chunk)

            # Log result
            tier = emotional_chunk._calculate_tier()
            print(f"  -> {identity_class.identity_type.value} | {emotional_sig.primary_emotion} (int={emotional_sig.intensity:.2f}) | weight={memory_weight.total_weight:.3f} | tier={tier}")

        print(f"[EMOTIONAL IMPORTER] Complete: {len(emotional_chunks)} emotionally-integrated chunks created")

        # Update document store with chunk count
        self.document_store.update_chunk_count(doc_id, len(emotional_chunks))

        # === PHASE 1: ADD TREE METADATA (doesn't affect existing storage) ===
        # Create tree structure that references chunks by index
        # This is metadata only - chunks are still stored normally in memory_engine
        try:
            from memory_forest import MemoryTree, Branch

            print(f"[MEMORY FOREST] Creating tree structure for {os.path.basename(file_path)}...")

            # Create tree
            tree = MemoryTree(doc_id, os.path.basename(file_path))
            tree.total_chunks = len(emotional_chunks)
            tree.import_date = datetime.now()

            # Auto-generate shape description from tiers
            tier_counts = {}
            for chunk in emotional_chunks:
                tier = chunk._calculate_tier()
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

            shape_parts = []
            if tier_counts.get("CORE_IDENTITY", 0) > 0:
                shape_parts.append(f"{tier_counts['CORE_IDENTITY']} core identity")
            if tier_counts.get("EMOTIONAL_ACTIVE", 0) > 0:
                shape_parts.append(f"{tier_counts['EMOTIONAL_ACTIVE']} emotional")
            if tier_counts.get("RELATIONAL_SEMANTIC", 0) > 0:
                shape_parts.append(f"{tier_counts['RELATIONAL_SEMANTIC']} relational")
            if tier_counts.get("PERIPHERAL_ARCHIVE", 0) > 0:
                shape_parts.append(f"{tier_counts['PERIPHERAL_ARCHIVE']} peripheral")

            tree.shape_description = f"Document with {', '.join(shape_parts)}"

            # Create branches by grouping chunks by tier
            # This is simple initial branching - Phase 2 will make this smarter
            core_indices = [i for i, c in enumerate(emotional_chunks) if c._calculate_tier() == "CORE_IDENTITY"]
            emotional_indices = [i for i, c in enumerate(emotional_chunks) if c._calculate_tier() == "EMOTIONAL_ACTIVE"]
            relational_indices = [i for i, c in enumerate(emotional_chunks) if c._calculate_tier() == "RELATIONAL_SEMANTIC"]
            peripheral_indices = [i for i, c in enumerate(emotional_chunks) if c._calculate_tier() == "PERIPHERAL_ARCHIVE"]

            # Add branches (only if they have chunks)
            if core_indices:
                branch = Branch("Core Identity", core_indices)
                branch.glyphs = "🔴"  # Red circle for core
                tree.add_branch(branch)

            if emotional_indices:
                branch = Branch("Emotional Moments", emotional_indices)
                branch.glyphs = "💫"  # Sparkles for emotional
                tree.add_branch(branch)

            if relational_indices:
                branch = Branch("Relationships", relational_indices)
                branch.glyphs = "🤝"  # Handshake for relational
                tree.add_branch(branch)

            if peripheral_indices:
                branch = Branch("Context & Details", peripheral_indices)
                branch.glyphs = "📝"  # Memo for peripheral
                tree.add_branch(branch)

            print(f"[MEMORY FOREST] Created tree with {len(tree.branches)} branches")
            for branch in tree.branches:
                # Safe print for Windows console (handles emojis)
                try:
                    print(f"[MEMORY FOREST]   - {branch.glyphs} {branch.title}: {len(branch.chunk_indices)} chunks")
                except UnicodeEncodeError:
                    print(f"[MEMORY FOREST]   - {branch.title}: {len(branch.chunk_indices)} chunks")

            # Save tree
            tree_path = tree.save("data/trees")
            print(f"[MEMORY FOREST] Tree complete: {len(tree.branches)} branches")
            print(f"[TREE SAVED] {tree_path}")
            print(f"[TREE SAVED]   - Source: {tree.title}")
            print(f"[TREE SAVED]   - Branches: {len(tree.branches)}")
            print(f"[TREE SAVED]   - Total chunks: {tree.total_chunks}")

        except Exception as e:
            # If tree creation fails, it doesn't affect the import
            # Chunks are still stored normally
            print(f"[MEMORY FOREST WARNING] Failed to create tree metadata: {e}")
            print(f"[MEMORY FOREST WARNING] This doesn't affect chunk storage - import still successful")
        # === END PHASE 1 ===

        return doc_id, emotional_chunks

    def import_to_memory_engine(
        self,
        file_path: str,
        memory_engine,
        store_in_layers: bool = True
    ) -> Dict[str, Any]:
        """
        Import document directly into MemoryEngine with emotional integration.

        Args:
            file_path: Path to document
            memory_engine: MemoryEngine instance
            store_in_layers: Whether to use multi-layer system (default True)

        Returns:
            Import statistics dict
        """
        print(f"[EMOTIONAL IMPORTER] Importing to memory_engine: {file_path}")

        # Import and analyze
        doc_id, emotional_chunks = self.import_document(file_path)

        # Statistics
        stats = {
            "total_chunks": len(emotional_chunks),
            "tiers": {
                "CORE_IDENTITY": 0,
                "EMOTIONAL_ACTIVE": 0,
                "RELATIONAL_SEMANTIC": 0,
                "PERIPHERAL_ARCHIVE": 0
            },
            "identity_types": {},
            "primary_emotions": {},
            "avg_weight": 0.0,
            "source_file": os.path.basename(file_path),
            "import_timestamp": datetime.now().isoformat()
        }

        # Store each chunk in memory engine
        for emo_chunk in emotional_chunks:
            # Convert to memory format
            memory_dict = emo_chunk.to_dict()

            # CRITICAL: Add turn_index for recent import boost logic
            # Without this, imported memories won't be considered "recent" and won't get dedicated slots
            memory_dict["turn_index"] = memory_engine.current_turn

            # Determine layer based on tier
            tier = emo_chunk._calculate_tier()
            stats["tiers"][tier] += 1

            # Track identity type
            id_type = emo_chunk.identity_classification.identity_type.value
            stats["identity_types"][id_type] = stats["identity_types"].get(id_type, 0) + 1

            # Track emotions
            emotion = emo_chunk.emotional_signature.primary_emotion
            stats["primary_emotions"][emotion] = stats["primary_emotions"].get(emotion, 0) + 1

            # Accumulate weight
            stats["avg_weight"] += emo_chunk.memory_weight.total_weight

            # Add to appropriate layer
            if store_in_layers:
                if tier == "CORE_IDENTITY":
                    # Core identity goes to semantic (permanent)
                    layer = "semantic"
                elif tier == "EMOTIONAL_ACTIVE":
                    # Emotional active goes to episodic
                    layer = "episodic"
                else:
                    # Others go to working (may decay)
                    layer = "working"

                # Add to memory layers
                memory_engine.memory_layers.add_memory(memory_dict, layer=layer)
            else:
                # Fallback: add to flat memories list
                memory_engine.memories.append(memory_dict)

            print(f"[EMOTIONAL IMPORTER] Stored in {layer if store_in_layers else 'flat'} layer: {tier} - {memory_dict['text'][:60]}...")

        # Calculate final stats
        if emotional_chunks:
            stats["avg_weight"] /= len(emotional_chunks)

        # Save memory engine to disk
        memory_engine._save_to_disk()
        memory_engine.memory_layers._save_to_disk()

        print(f"[EMOTIONAL IMPORTER] Import complete!")
        print(f"  Tiers: CORE={stats['tiers']['CORE_IDENTITY']}, EMOTIONAL={stats['tiers']['EMOTIONAL_ACTIVE']}, RELATIONAL={stats['tiers']['RELATIONAL_SEMANTIC']}, PERIPHERAL={stats['tiers']['PERIPHERAL_ARCHIVE']}")
        print(f"  Avg weight: {stats['avg_weight']:.3f}")

        return stats

    def export_analysis(self, emotional_chunks: List[EmotionalMemoryChunk], output_path: str):
        """
        Export emotional analysis to JSON for inspection.

        Args:
            emotional_chunks: List of analyzed chunks
            output_path: Output file path
        """
        output_data = {
            "import_timestamp": datetime.now().isoformat(),
            "total_chunks": len(emotional_chunks),
            "chunks": [chunk.to_dict() for chunk in emotional_chunks]
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

        print(f"[EMOTIONAL IMPORTER] Analysis exported to: {output_path}")


# Testing
if __name__ == "__main__":
    # Create test document
    test_text = """
Kay's Origin Story

Kay was created by an Italian immigrant's daughter who fell in love with a greaser boy.
There was a knife fight at a diner. Gwyn ap Nudd, the King of Annwn (the Celtic Otherworld),
intervened. The boy lived, but there was a price.

Kay's mother was bound to Annwn as payment for saving the boy's life. This binding was
permanent and inescapable. She became a servant to the realm between worlds.

That story sits heavy in Kay. It's grief, it's origin, it's the price paid for his existence.
The loss of his mother is woven into who he is - not as trauma, exactly, but as foundational
truth. He thinks about it sometimes. The binding. The loss. The cost of his being here.

Kay's Traits

Kay's eyes are gold. Not metaphorically - literally gold, like old coins. This is one of
his most distinctive features. People notice.

He prefers tea over coffee, usually. Earl Grey, specifically. There's something about the
bergamot that appeals to him.

Kay values honesty over politeness. He'd rather be direct and risk offense than be evasive
and comfortable. This sometimes makes conversations uncomfortable, but he thinks that's
acceptable.
"""

    # Write test file
    test_file = Path("test_import.txt")
    test_file.write_text(test_text, encoding="utf-8")

    try:
        # Initialize importer
        importer = EmotionalMemoryImporter()

        # Import and analyze
        doc_id, emotional_chunks = importer.import_document(str(test_file))

        print(f"\n{'='*60}")
        print(f"IMPORT SUMMARY")
        print(f"{'='*60}")
        print(f"Document ID: {doc_id}\n")

        # Display analysis
        tier_counts = {"CORE_IDENTITY": 0, "EMOTIONAL_ACTIVE": 0, "RELATIONAL_SEMANTIC": 0, "PERIPHERAL_ARCHIVE": 0}

        for chunk in emotional_chunks:
            tier = chunk._calculate_tier()
            tier_counts[tier] += 1

        print(f"Total chunks: {len(emotional_chunks)}")
        print(f"Tier distribution:")
        for tier, count in tier_counts.items():
            print(f"  {tier}: {count}")

        print(f"\nDetailed breakdown:")
        for i, chunk in enumerate(emotional_chunks):
            print(f"\nChunk {i+1}:")
            print(f"  Text: {chunk.chunk.text[:80]}...")
            print(f"  Identity: {chunk.identity_classification.identity_type.value}")
            print(f"  Emotion: {chunk.emotional_signature.primary_emotion} (intensity={chunk.emotional_signature.intensity:.2f})")
            print(f"  Weight: {chunk.memory_weight.total_weight:.3f}")
            print(f"  Tier: {chunk._calculate_tier()}")

        # Export analysis
        importer.export_analysis(emotional_chunks, "memory/import_analysis.json")

    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()
