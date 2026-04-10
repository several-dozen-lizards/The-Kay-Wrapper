"""
Vector Store for Kay Zero
Handles document storage and retrieval using ChromaDB with sentence-transformers
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except (ImportError, Exception):
    CHROMADB_AVAILABLE = False
    print("[WARNING] ChromaDB not available. Run: pip install chromadb")

try:
    from engines.shared_embedder import get_embedder, is_embedder_available
    EMBEDDER_AVAILABLE = is_embedder_available()
except ImportError:
    # Fallback for direct import
    try:
        from sentence_transformers import SentenceTransformer
        EMBEDDER_AVAILABLE = True
        get_embedder = None  # Will use local instantiation
    except ImportError:
        EMBEDDER_AVAILABLE = False
        get_embedder = None
        print("[WARNING] sentence-transformers not installed. Run: pip install sentence-transformers")
        print("[INFO] Will use ChromaDB's default embeddings")

# Entity-prefixed logging
try:
    from shared.entity_log import etag
except ImportError:
    def etag(tag): return f"[{tag}]"



class VectorStore:
    """
    Vector database for document storage and RAG retrieval.

    Stores uploaded documents as chunks with embeddings for semantic search.
    Separate from structured memory (which stores identity/state/working memory).

    Storage format:
    - Documents chunked into 500-1000 char chunks with 100 char overlap
    - Each chunk embedded with default ChromaDB embeddings
    - Metadata: source_file, chunk_id, timestamp, document_type
    """

    def __init__(self, persist_directory: str = None, use_sentence_transformers: bool = True):
        """
        Initialize vector store.

        Args:
            persist_directory: Path to ChromaDB persistence directory
            use_sentence_transformers: Use sentence-transformers for embeddings (default: True)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB not installed. Run: pip install chromadb")

        if persist_directory is None:
            persist_directory = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "memory", "vector_db"
            )
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        # Initialize sentence-transformers embedder
        self.embedder = None
        self.use_custom_embeddings = use_sentence_transformers and EMBEDDER_AVAILABLE

        if self.use_custom_embeddings:
            # Use shared embedder singleton to avoid duplicate model loading
            if get_embedder is not None:
                print(f"{etag('VECTOR_DB')} Using shared embedder singleton...")
                self.embedder = get_embedder()
            else:
                # Fallback: load directly (shouldn't happen normally)
                print(f"{etag('VECTOR_DB')} Loading sentence-transformer model 'all-MiniLM-L6-v2'...")
                from sentence_transformers import SentenceTransformer
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            if self.embedder:
                print(f"{etag('VECTOR_DB')} Embedder ready (CPU mode)")

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection for documents
        self.collection = self.client.get_or_create_collection(
            name="kay_documents",
            metadata={
                "description": "Uploaded documents for RAG retrieval",
                "hnsw:space": "cosine"
            }
        )

        embedder_type = "sentence-transformers" if self.use_custom_embeddings else "ChromaDB default"
        print(f"{etag('VECTOR_DB')} Initialized at {persist_directory} ({self.collection.count()} chunks, {embedder_type})")

    def add_document(
        self,
        text: str,
        source_file: str,
        chunk_size: int = 800,
        overlap: int = 100,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a document to the vector store.

        IMPORTANT: This chunks the document and stores it for RAG retrieval.
        Does NOT extract thousands of facts into structured memory.

        Args:
            text: Full document text
            source_file: Source filename
            chunk_size: Characters per chunk (default 800)
            overlap: Overlap between chunks (default 100)
            metadata: Additional metadata to attach to all chunks

        Returns:
            Dict with stats: {
                "chunks_created": int,
                "document_id": str,
                "timestamp": str
            }
        """
        # Generate document ID
        doc_id = self._generate_doc_id(source_file, text)

        # Check if already exists
        existing = self.collection.get(
            where={"document_id": doc_id},
            limit=1
        )

        if existing and existing['ids']:
            print(f"{etag('VECTOR_DB')} Document already exists: {source_file} (skipping)")
            return {
                "chunks_created": 0,
                "document_id": doc_id,
                "timestamp": datetime.now().isoformat(),
                "status": "duplicate"
            }

        # Chunk the document
        chunks = self._chunk_text(text, chunk_size, overlap)

        if not chunks:
            print(f"{etag('VECTOR_DB')} No chunks created from {source_file}")
            return {
                "chunks_created": 0,
                "document_id": doc_id,
                "timestamp": datetime.now().isoformat(),
                "status": "empty"
            }

        # Prepare data for ChromaDB
        chunk_ids = []
        chunk_texts = []
        chunk_metadata = []
        timestamp = datetime.now().isoformat()

        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            chunk_texts.append(chunk_text)

            # Build chunk metadata
            chunk_meta = {
                "document_id": doc_id,
                "source_file": source_file,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "timestamp": timestamp,
                "char_count": len(chunk_text)
            }

            # Merge additional metadata
            if metadata:
                chunk_meta.update(metadata)

            chunk_metadata.append(chunk_meta)

        # Add to ChromaDB with embeddings
        if self.use_custom_embeddings:
            # Use sentence-transformers for embeddings
            embeddings = self.embedder.encode(chunk_texts).tolist()
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=chunk_texts,
                metadatas=chunk_metadata
            )
        else:
            # Use ChromaDB's automatic embedding generation
            self.collection.add(
                ids=chunk_ids,
                documents=chunk_texts,
                metadatas=chunk_metadata
            )

        print(f"{etag('VECTOR_DB')} Added {len(chunks)} chunks from {source_file}")

        return {
            "chunks_created": len(chunks),
            "document_id": doc_id,
            "timestamp": timestamp,
            "status": "success"
        }

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query vector store for relevant document chunks.

        Args:
            query_text: Query string
            n_results: Number of chunks to return
            filter_metadata: Optional metadata filter (e.g., {"source_file": "notes.txt"})

        Returns:
            List of dicts with keys: {
                "text": str,
                "metadata": dict,
                "distance": float (similarity score)
            }
        """
        if not query_text or not query_text.strip():
            return []

        # Query ChromaDB
        if self.use_custom_embeddings:
            # Use sentence-transformers for query embedding
            query_embedding = self.embedder.encode([query_text])[0].tolist()
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata
            )
        else:
            # Use ChromaDB's automatic embedding
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=filter_metadata
            )

        # Format results
        formatted_results = []

        if results and results['documents'] and results['documents'][0]:
            for i, doc_text in enumerate(results['documents'][0]):
                formatted_results.append({
                    "text": doc_text,
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else 0.0
                })

        return formatted_results

    def delete_document(self, document_id: str) -> bool:
        """
        Delete all chunks of a document.

        Args:
            document_id: Document ID to delete

        Returns:
            True if deleted, False if not found
        """
        # Get all chunks for this document
        existing = self.collection.get(
            where={"document_id": document_id}
        )

        if not existing or not existing['ids']:
            print(f"{etag('VECTOR_DB')} Document not found: {document_id}")
            return False

        # Delete all chunks
        self.collection.delete(ids=existing['ids'])

        print(f"{etag('VECTOR_DB')} Deleted {len(existing['ids'])} chunks for document {document_id}")
        return True

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all documents in the vector store.

        Returns:
            List of dicts with: {
                "document_id": str,
                "source_file": str,
                "chunk_count": int,
                "timestamp": str
            }
        """
        # Get all chunks
        all_chunks = self.collection.get()

        if not all_chunks or not all_chunks['ids']:
            return []

        # Group by document_id
        documents = {}

        for i, chunk_id in enumerate(all_chunks['ids']):
            metadata = all_chunks['metadatas'][i] if all_chunks['metadatas'] else {}
            doc_id = metadata.get("document_id", "unknown")

            if doc_id not in documents:
                documents[doc_id] = {
                    "document_id": doc_id,
                    "source_file": metadata.get("source_file", "unknown"),
                    "chunk_count": 0,
                    "timestamp": metadata.get("timestamp", "unknown")
                }

            documents[doc_id]["chunk_count"] += 1

        return list(documents.values())

    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics.

        Returns:
            Dict with: {
                "total_chunks": int,
                "total_documents": int,
                "storage_path": str
            }
        """
        all_chunks = self.collection.get()

        # Count unique documents
        unique_docs = set()
        if all_chunks and all_chunks['metadatas']:
            for metadata in all_chunks['metadatas']:
                doc_id = metadata.get("document_id")
                if doc_id:
                    unique_docs.add(doc_id)

        return {
            "total_chunks": len(all_chunks['ids']) if all_chunks and all_chunks['ids'] else 0,
            "total_documents": len(unique_docs),
            "storage_path": self.persist_directory
        }

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Chunk text into overlapping segments.

        Args:
            text: Full text to chunk
            chunk_size: Characters per chunk
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if not text or len(text) <= chunk_size:
            return [text] if text else []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # If not at the end, try to break at a sentence/paragraph boundary
            if end < len(text):
                # Look for paragraph break first
                paragraph_break = text.rfind('\n\n', start, end)
                if paragraph_break > start:
                    end = paragraph_break + 2
                else:
                    # Look for sentence break
                    sentence_break = max(
                        text.rfind('. ', start, end),
                        text.rfind('! ', start, end),
                        text.rfind('? ', start, end)
                    )
                    if sentence_break > start:
                        end = sentence_break + 2

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start forward, accounting for overlap
            # CRITICAL: Ensure start always advances to prevent infinite loops
            if end < len(text):
                # Calculate new start with overlap
                new_start = end - overlap
                # Ensure we advance at least 1 character to prevent infinite loop
                # This can happen when a sentence break is found early in the chunk
                if new_start <= start:
                    new_start = start + max(chunk_size // 2, 100)  # Advance by at least half chunk size
                start = min(new_start, len(text))
            else:
                start = len(text)

        return chunks

    def _generate_doc_id(self, source_file: str, text: str) -> str:
        """
        Generate unique document ID.

        Args:
            source_file: Source filename
            text: Document text

        Returns:
            Unique document ID (hash-based)
        """
        # Use hash of filename + first 1000 chars for uniqueness
        content_sample = text[:1000] if len(text) > 1000 else text
        hash_input = f"{source_file}:{content_sample}"

        doc_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]

        # Clean filename for ID
        clean_filename = Path(source_file).stem[:30]  # Max 30 chars
        clean_filename = "".join(c if c.isalnum() or c in "-_" else "_" for c in clean_filename)

        return f"{clean_filename}_{doc_hash}"


# Testing
if __name__ == "__main__":
    if not CHROMADB_AVAILABLE:
        print(f"{etag('TEST SKIPPED')}  ChromaDB not available")
    else:
        # Test vector store
        store = VectorStore(persist_directory="memory/vector_db_test")

        # Add test document
        test_doc = """
        Kay is a dragon with gold eyes and a dry sense of humor. He prefers coffee over tea.
        Re is Kay's conversation partner who has several cats: [cat], [cat], and [cat].
        [cat] is a gray tabby who likes to door-dash. [cat] is a tuxedo cat.
        """

        result = store.add_document(
            text=test_doc,
            source_file="test_notes.txt",
            metadata={"document_type": "notes"}
        )

        print(f"{etag('TEST')} Add result: {result}")

        # Query
        query_results = store.query("What cats does Re have?", n_results=3)
        print(f"{etag('TEST')} Query results: {len(query_results)}")
        for i, result in enumerate(query_results):
            print(f"  [{i}] {result['text'][:100]}... (distance: {result['distance']:.4f})")

        # Stats
        stats = store.get_stats()
        print(f"{etag('TEST')} Stats: {stats}")

        print(f"{etag('TEST')}  Vector store test complete!")
