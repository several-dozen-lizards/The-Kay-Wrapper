"""
Sequential Document Reader + Chunked Document Viewer

Two modes:
1. SequentialDocumentReader: Reads entire documents in order (batch processing)
2. DocumentReader: Chunks large documents for the entity to navigate sequentially

SequentialDocumentReader - WHEN TO USE:
- Fresh document uploads
- Explicit "read through this" requests
- Building narrative understanding

DocumentReader - WHEN TO USE:
- Large documents that exceed context window
- the entity needs to read through a document in sections
- User wants to navigate with "continue reading", "jump to section", etc.
"""

from typing import Dict, List, Optional, Any
import json
import time
from pathlib import Path
import re

# Entity-prefixed logging
try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"



class SequentialDocumentReader:
    """
    Reads documents sequentially in batches, generating comprehensive understanding.

    Unlike vector search (which retrieves relevant fragments), this reads
    the ENTIRE document in order like a human would.
    """

    def __init__(self, vector_store, llm_client=None):
        """
        Initialize sequential document reader.

        Args:
            vector_store: ChromaVectorStore instance for accessing documents
            llm_client: Optional LLM client for generating summaries
        """
        self.vector_store = vector_store
        self.llm_client = llm_client

    def read_document_sequentially(self, doc_id: str, batch_size: int = 100) -> Optional[Dict]:
        """
        Read entire document in sequential batches.

        Process:
        1. Load all chunks for doc_id in chronological order (by chunk_index)
        2. Process in batches of 100 chunks
        3. For each batch, generate summary of key points
        4. Combine batch summaries into comprehensive understanding
        5. Return full analysis + summary for memory storage

        TOKEN MANAGEMENT:
        - Batch size 100 = ~63,700 chars per LLM call
        - Large documents processed incrementally
        - Each batch summary ~2000 chars
        - Final comprehensive summary ~5000 chars

        Args:
            doc_id: Document ID from documents.json
            batch_size: Chunks per batch (default 100, ~63k chars)

        Returns:
            {
                'doc_id': str,
                'filename': str,
                'total_chunks': int,
                'batch_summaries': List[str],  # Summary of each batch
                'comprehensive_summary': str,   # Overall document summary
                'key_entities': List[str],      # Characters, places, concepts
                'narrative_arc': str,           # Story flow if applicable
                'timestamp': float
            }
        """
        # Get all chunks for this document in order
        all_chunks = self._get_all_document_chunks(doc_id)

        if not all_chunks:
            print(f"{etag('SEQUENTIAL READ')} No chunks found for doc_id: {doc_id}")
            return None

        filename = all_chunks[0].get('metadata', {}).get('source_file', 'unknown')
        print(f"{etag('SEQUENTIAL READ')} Reading {len(all_chunks)} chunks from {filename} in batches of {batch_size}")

        batch_summaries = []

        # Process in batches
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(all_chunks) + batch_size - 1) // batch_size

            print(f"{etag('SEQUENTIAL READ')} Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")

            # Combine batch chunks into text
            batch_text = "\n\n".join([chunk['text'] for chunk in batch])

            # Generate summary for this batch
            summary = self._summarize_batch(
                batch_text=batch_text,
                batch_num=batch_num,
                total_batches=total_batches,
                filename=filename
            )
            batch_summaries.append(summary)

        # Generate comprehensive summary from batch summaries
        comprehensive_summary = self._generate_comprehensive_summary(
            batch_summaries=batch_summaries,
            filename=filename
        )

        # Extract key entities from comprehensive summary
        key_entities = self._extract_key_entities(comprehensive_summary)

        # Generate narrative arc description
        narrative_arc = self._extract_narrative_arc(batch_summaries, filename)

        result = {
            'doc_id': doc_id,
            'filename': filename,
            'total_chunks': len(all_chunks),
            'batch_summaries': batch_summaries,
            'comprehensive_summary': comprehensive_summary,
            'key_entities': key_entities,
            'narrative_arc': narrative_arc,
            'timestamp': time.time()
        }

        print(f"{etag('SEQUENTIAL READ')} Complete: {filename}")
        print(f"{etag('SEQUENTIAL READ')} Comprehensive summary: {len(comprehensive_summary)} chars")
        print(f"{etag('SEQUENTIAL READ')} Key entities: {len(key_entities)}")

        return result

    def _get_all_document_chunks(self, doc_id: str) -> List[Dict]:
        """
        Retrieve ALL chunks for a document in chronological order.

        Unlike vector search (relevance-ranked), this gets chunks
        sorted by chunk_index for sequential reading.

        Args:
            doc_id: Document ID to retrieve

        Returns:
            List of chunk dicts sorted by chunk_index
        """
        if not self.vector_store:
            print(f"{etag('SEQUENTIAL READ')}  No vector store available")
            return []

        try:
            # Query vector store with high n_results to get all chunks
            # This is a workaround - ideally we'd have a "get_all_by_doc_id" method
            results = self.vector_store.query(
                query_text=doc_id,  # Use doc_id as query
                n_results=1000  # Large number to get all chunks
            )

            # Filter to only chunks from this document
            doc_chunks = []
            for result in results:
                metadata = result.get('metadata', {})
                # Check if this chunk belongs to the document
                if metadata.get('doc_id') == doc_id or metadata.get('source_file', '').startswith(doc_id):
                    doc_chunks.append({
                        'text': result['text'],
                        'metadata': metadata,
                        'chunk_index': metadata.get('chunk_index', 0)
                    })

            # Sort by chunk_index for sequential order
            doc_chunks.sort(key=lambda x: x['chunk_index'])

            return doc_chunks

        except Exception as e:
            print(f"{etag('SEQUENTIAL READ ERROR')} Failed to retrieve chunks: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _summarize_batch(self, batch_text: str, batch_num: int, total_batches: int, filename: str) -> str:
        """
        Generate summary for a batch of text.

        If LLM client is available, uses LLM for intelligent summarization.
        Otherwise, generates a simple structural summary.

        Args:
            batch_text: Combined text from all chunks in batch
            batch_num: Current batch number
            total_batches: Total number of batches
            filename: Document filename for context

        Returns:
            Summary text (2-3 paragraphs)
        """
        # Simple summary without LLM (fallback)
        # In production, you'd use LLM here for better summaries
        char_count = len(batch_text)
        word_count = len(batch_text.split())

        # Extract some content preview
        preview = batch_text[:500].replace('\n', ' ')
        if len(batch_text) > 500:
            preview += "..."

        summary = f"""Batch {batch_num}/{total_batches} of {filename}:
- Content length: {char_count} characters, ~{word_count} words
- Preview: {preview}

[Note: Detailed LLM-based summarization would be generated here in full implementation]"""

        return summary

    def _generate_comprehensive_summary(self, batch_summaries: List[str], filename: str) -> str:
        """
        Combine batch summaries into overall document understanding.

        Args:
            batch_summaries: List of summaries from each batch
            filename: Document filename

        Returns:
            Comprehensive summary (3-5 paragraphs)
        """
        total_batches = len(batch_summaries)

        # Simple comprehensive summary (fallback without LLM)
        summary = f"""Document: {filename}

This document was read in {total_batches} sequential batches, covering the complete content from beginning to end.

Structure:
- Total sections: {total_batches}
- Reading approach: Sequential (chronological order)
- Coverage: Complete document

Key characteristics:
- The document contains structured narrative content
- Content progresses chronologically through sections
- Each section contributes to the overall narrative or informational flow

[Note: In full implementation, this would be an LLM-generated comprehensive analysis combining insights from all batches, identifying themes, characters, key events, and narrative structure]
"""

        return summary

    def _extract_key_entities(self, summary: str) -> List[str]:
        """
        Extract character names, places, concepts from summary.

        Simple implementation: look for capitalized words.
        Better implementation would use LLM or NER.

        Args:
            summary: Comprehensive summary text

        Returns:
            List of entity names
        """
        import re

        # Find capitalized words (potential entities)
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', summary)

        # Filter out common words and deduplicate
        stopwords = {'The', 'This', 'These', 'Those', 'That', 'Document', 'Reading',
                     'Content', 'Note', 'Section', 'Batch', 'Key', 'Structure'}

        entities = [w for w in words if w not in stopwords]

        # Deduplicate while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity not in seen:
                seen.add(entity)
                unique_entities.append(entity)

        return unique_entities[:20]  # Limit to top 20

    def _extract_narrative_arc(self, batch_summaries: List[str], filename: str) -> str:
        """
        Describe story progression across batches.

        Args:
            batch_summaries: List of batch summaries
            filename: Document filename

        Returns:
            Narrative arc description
        """
        num_sections = len(batch_summaries)
        return f"{filename} progresses through {num_sections} major sections, read sequentially from beginning to end"

    def detect_reading_mode(self, user_input: str, recent_uploads: List[str] = None) -> str:
        """
        Determine whether to use SEQUENTIAL or VECTOR mode.

        SEQUENTIAL triggers:
        - Fresh upload detected (doc_id in recent_uploads, < 2 turns old)
        - Explicit phrases: "read through", "read this", "summarize the whole"
        - Overview questions: "what's this about?", "give me an overview"

        VECTOR triggers:
        - Specific questions about document content
        - Default for normal conversation

        Args:
            user_input: User's message
            recent_uploads: List of recently uploaded doc_ids

        Returns: "SEQUENTIAL" or "VECTOR"
        """
        user_lower = user_input.lower()

        # Check for fresh uploads
        if recent_uploads and len(recent_uploads) > 0:
            print(f"{etag('MODE DETECTION')}  Fresh upload detected - suggesting SEQUENTIAL mode")
            # Don't auto-trigger, but make it likely if user asks about the doc
            if any(phrase in user_lower for phrase in [
                "this document", "this file", "what's this", "tell me about this"
            ]):
                return "SEQUENTIAL"

        # Check for explicit reading requests
        reading_phrases = [
            "read through", "read this", "read the",
            "summarize the whole", "summarize the document",
            "give me an overview", "what's this about",
            "what's in this", "tell me about this document",
            "walk me through", "go through the"
        ]

        if any(phrase in user_lower for phrase in reading_phrases):
            print(f"{etag('MODE DETECTION')}  Explicit reading request detected - SEQUENTIAL mode")
            return "SEQUENTIAL"

        # Default to vector search (fast, targeted)
        return "VECTOR"

    def parse_document_reference(self, user_input: str, available_doc_ids: List[str]) -> Optional[str]:
        """
        Parse which document the user wants to read.

        Args:
            user_input: User's message
            available_doc_ids: List of available document IDs

        Returns:
            doc_id if found, None otherwise
        """
        user_lower = user_input.lower()

        # Simple heuristic: check if any doc_id appears in input
        for doc_id in available_doc_ids:
            if doc_id.lower() in user_lower:
                return doc_id

        # If only one document available, assume they mean that one
        if len(available_doc_ids) == 1:
            return available_doc_ids[0]

        return None


class DocumentReader:
    """
    Manages chunked reading of large documents for the entity's navigation.

    Allows the entity to navigate through documents with commands like:
    - "continue reading" / "next section"
    - "previous section" / "go back"
    - "jump to section N"
    - "restart document"

    Unlike SequentialDocumentReader (which batch-processes for summaries),
    this provides real-time navigation through a single loaded document.
    """

    def __init__(self, chunk_size: int = 25000):
        """
        Initialize document reader.

        Args:
            chunk_size: Target chunk size in characters (~6000 tokens)
        """
        self.chunk_size = chunk_size
        self.current_doc = None  # Current document metadata
        self.current_position = 0  # Current chunk index (0-indexed)
        self.chunks = []  # List of text chunks
        self.total_chunks = 0
        self.chunk_comments = {}  # Store the entity's comments by chunk index

    def load_document(self, doc_text: str, doc_name: str, doc_id: str = None) -> bool:
        """
        Load a new document and split it into chunks.

        Args:
            doc_text: Full document text
            doc_name: Display name of document
            doc_id: Optional document ID for persistence

        Returns:
            True if document was loaded successfully
        """
        if not doc_text or not doc_text.strip():
            print(f"{etag('DOC READER')} Cannot load empty document: {doc_name}")
            return False

        # Store document metadata
        self.current_doc = {
            'name': doc_name,
            'id': doc_id,
            'full_length': len(doc_text)
        }

        # Split into chunks
        self.chunks = self._split_into_chunks(doc_text)
        self.total_chunks = len(self.chunks)
        self.current_position = 0

        print(f"{etag('DOC READER')} Loaded {doc_name}: {self.total_chunks} chunks ({len(doc_text):,} chars)")
        return True

    def _split_into_chunks(self, text: str) -> List[str]:
        """
        Split text into chunks at paragraph boundaries.

        Falls back to sentence splitting if a paragraph exceeds chunk size.

        Args:
            text: Full document text

        Returns:
            List of text chunks
        """
        chunks = []
        current_chunk = ""

        # Split on paragraph boundaries
        paragraphs = text.split('\n\n')

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If adding this paragraph would exceed chunk size, finalize current chunk
            if current_chunk and len(current_chunk) + len(paragraph) + 2 > self.chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # If single paragraph exceeds chunk size, split it at sentences
            if len(paragraph) > self.chunk_size:
                sentences = self._split_at_sentences(paragraph)
                for sentence in sentences:
                    if current_chunk and len(current_chunk) + len(sentence) + 1 > self.chunk_size:
                        chunks.append(current_chunk.strip())
                        current_chunk = sentence + " "
                    else:
                        current_chunk += sentence + " "
            else:
                # Add paragraph to current chunk
                current_chunk += paragraph + "\n\n"

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]  # Fallback to whole text if splitting fails

    def _split_at_sentences(self, text: str) -> List[str]:
        """
        Split text at sentence boundaries (. ? !)

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Split on sentence endings followed by space or newline
        sentences = re.split(r'([.?!])\s+', text)

        # Rejoin punctuation with sentences
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])

        # Add last fragment if exists
        if len(sentences) % 2 == 1:
            result.append(sentences[-1])

        return [s.strip() for s in result if s.strip()]

    def get_current_chunk(self) -> Optional[Dict]:
        """
        Get the current chunk with metadata.

        Returns:
            Dict with:
                - text: Current chunk text
                - position: Current position (1-indexed for display)
                - total: Total number of chunks
                - doc_name: Document name
                - progress_percent: Progress as integer percentage
                - previous_comment: the entity's previous comment on this chunk (if any)
                - has_next: Whether there are more chunks after this one
                - has_previous: Whether there are chunks before this one
            Or None if no document is loaded
        """
        if not self.current_doc or not self.chunks:
            return None

        if self.current_position >= len(self.chunks):
            self.current_position = len(self.chunks) - 1

        progress_percent = int((self.current_position + 1) / self.total_chunks * 100)

        return {
            'text': self.chunks[self.current_position],
            'position': self.current_position + 1,  # 1-indexed for display
            'total': self.total_chunks,
            'doc_name': self.current_doc['name'],
            'doc_id': self.current_doc.get('id'),
            'progress_percent': progress_percent,
            'previous_comment': self.get_comment(self.current_position),
            'has_next': self.has_next(),
            'has_previous': self.has_previous()
        }

    def advance(self) -> bool:
        """
        Move to next chunk.

        Returns:
            True if advanced successfully, False if at end of document
        """
        if not self.current_doc:
            return False

        if self.current_position < self.total_chunks - 1:
            self.current_position += 1
            print(f"{etag('DOC READER')} Navigation: advance -> section {self.current_position + 1}/{self.total_chunks}")
            return True
        else:
            print(f"{etag('DOC READER')} Navigation: already at end of document")
            return False

    def previous(self) -> bool:
        """
        Move to previous chunk.

        Returns:
            True if moved successfully, False if at beginning
        """
        if not self.current_doc:
            return False

        if self.current_position > 0:
            self.current_position -= 1
            print(f"{etag('DOC READER')} Navigation: previous -> section {self.current_position + 1}/{self.total_chunks}")
            return True
        else:
            print(f"{etag('DOC READER')} Navigation: already at beginning of document")
            return False

    def jump_to(self, position: int) -> bool:
        """
        Jump to specific chunk number (0-indexed).

        Args:
            position: Target position (0-indexed)

        Returns:
            True if jumped successfully, False if position invalid
        """
        if not self.current_doc:
            return False

        if 0 <= position < self.total_chunks:
            self.current_position = position
            print(f"{etag('DOC READER')} Navigation: jump -> section {self.current_position + 1}/{self.total_chunks}")
            return True
        else:
            print(f"{etag('DOC READER')} Navigation: invalid position {position + 1} (valid: 1-{self.total_chunks})")
            return False

    def get_status(self) -> Optional[Dict]:
        """
        Get reading position info without chunk text.

        Returns:
            Dict with position info, or None if no document loaded
        """
        if not self.current_doc:
            return None

        return {
            'doc_name': self.current_doc['name'],
            'doc_id': self.current_doc.get('id'),
            'position': self.current_position + 1,  # 1-indexed
            'total': self.total_chunks,
            'progress_percent': int((self.current_position + 1) / self.total_chunks * 100)
        }

    def get_state_for_persistence(self) -> Optional[Dict]:
        """
        Get state data for persistence to agent_state.

        Returns:
            Dict with current reading state, or None if no document loaded
        """
        if not self.current_doc:
            return None

        return {
            'doc_id': self.current_doc.get('id'),
            'doc_name': self.current_doc['name'],
            'position': self.current_position,
            'total_chunks': self.total_chunks
        }

    def restore_state(self, state: Dict, doc_text: str = None) -> bool:
        """
        Restore reading state from persistence.

        Args:
            state: State dict from get_state_for_persistence()
            doc_text: Optional document text to reload (if available)

        Returns:
            True if state restored successfully
        """
        if not state:
            return False

        # If document text provided, reload it
        if doc_text:
            success = self.load_document(
                doc_text,
                state['doc_name'],
                state.get('doc_id')
            )

            if success:
                # Restore position
                self.current_position = min(state['position'], self.total_chunks - 1)
                print(f"{etag('DOC READER')} Restored reading position: section {self.current_position + 1}/{self.total_chunks}")
                return True

        return False

    def clear(self):
        """Clear current document and reset state."""
        self.current_doc = None
        self.current_position = 0
        self.chunks = []
        self.total_chunks = 0
        self.chunk_comments = {}
        print(f"{etag('DOC READER')}  Document cleared")

    def add_comment(self, chunk_index: int, comment: str):
        """
        Store the entity's comment about a specific chunk.

        Args:
            chunk_index: Chunk index (0-indexed)
            comment: the entity's comment about the chunk
        """
        if 0 <= chunk_index < self.total_chunks:
            self.chunk_comments[chunk_index] = comment
            print(f"{etag('DOC READER')} Stored comment for section {chunk_index + 1}/{self.total_chunks}")

    def get_comment(self, chunk_index: int) -> str:
        """
        Retrieve the entity's previous comment about a chunk.

        Args:
            chunk_index: Chunk index (0-indexed)

        Returns:
            Comment string if exists, None otherwise
        """
        return self.chunk_comments.get(chunk_index, None)

    def has_next(self) -> bool:
        """Check if there are more chunks after current position."""
        return self.current_position < self.total_chunks - 1

    def has_previous(self) -> bool:
        """Check if there are chunks before current position."""
        return self.current_position > 0
